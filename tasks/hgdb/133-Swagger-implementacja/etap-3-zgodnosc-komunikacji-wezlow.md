# [133] Etap 3 – Zgodność komunikacji między węzłami serwera

Zadanie nadrzędne: [TASK.md](TASK.md). Zależy od: zmian kontraktu XML w `mercury-lib`
(patrz „Stan realizacji”). Etap 1 i 2 nie czekają na ten etap, ale **wydanie** zadania tak.

## Cel zadania
Zniwelować ryzyka, które wprowadziło dopasowanie klas JAXB do XSD (kwalifikowane elementy XML modelu
obiektu MRC): węzły serwera i klienci o różnych wersjach biblioteki mają nadal poprawnie wymieniać dane.
Nie wolno dopuścić do cichej utraty danych (JAXB pomija niedopasowane elementy bez błędu).

## Stan realizacji (zmiany w `mercury-lib`, 2026-10-17, gałąź `hgdb-133`)

Powód: klasy JAXB zapisywały elementy w pustej przestrzeni nazw, a XSD
(`mercury-ws-dto-api/src/main/resources/xml-schemas/hgdb-mrc-object-3.0.xsd`) wymaga
`elementFormDefault="qualified"` w `http://business.dto.ws.hgdb.io/mrcObject`. Przykłady z `dto-samples/`
były zgodne z XSD i nie dawały się wczytać (odczyt zwracał puste obiekty, bez wyjątku).

| Zmiana | Moduł | Skutek |
|---|---|---|
| `namespace` w `@XmlRootElement` i `@XmlElement` klas `DtoMrcList`, `DtoMrcListItems`, `DtoMrcObject`, `DtoMrcProperty`, `DtoMrcPropertyNames`, `DtoPropertyMap`, `DtoPropertyMapEntry`. Stała `MrcNamespaces.MRC_OBJECT` z `mercury-srv-api` (publiczna) | `mercury-ws-dto-api` | Elementy tych klas są kwalifikowane. Koperty `WsStatus*` bez zmian (nie użyto `@XmlSchema` na pakiecie) |
| `namespace` w `@XmlElement` klas `CaseHeader` (31 pól) i `MrcObjectMetadata` (2 pola). Stała w publicznym `MrcNamespaces`, wspólna dla obu modułów | `mercury-srv-api` | Nagłówek sprawy jest kwalifikowany w całym SOAP |
| `DtoPropertyMap` nie implementuje już `Map`. Pole `keys` jest wyliczane leniwie z `entries` | `mercury-ws-dto-api` | JAXB nie gubi `propertyMap`. Znika `NullPointerException` w `put` |
| `DtoPropertyMap.readObject` odtwarza `transient initLock` po deserializacji | `mercury-ws-dto-api` | Bez tego `get`/`put` po deserializacji rzucały NPE (wykryte testem stary ↔ nowy). Format serializacji i `serialVersionUID` bez zmian |
| Nowy `DtoXmlContractTest` i `DtoSerializationTest`. `DtoListMarshallerTest` czyta `dto-samples/` do `target/` | `mercury-ws-dto-api` | Kontrakt XML sprawdzany na MOXy i RI, razem z walidacją XSD. Serializacja Javy sprawdzana w obie strony |

Weryfikacja: `mvn install` w `mercury-lib` przechodzi z testami (8 modułów). `hgdb-client-open`
kompiluje się na `3.0.4-SNAPSHOT` bez zmian kodu (testy klienta wymagają serwera i nie były uruchamiane).

## Kontekst i Wymagania

### Kanały między węzłami (z kodu `mercury`)

| Kanał | Gdzie w kodzie | Dotyczy zmienionych klas |
|---|---|---|
| SOAP (CXF), węzeł slave → master | `mercury-srv-slave/.../org/mercury/slave/server/client/cxf/WsClient`, `ClientCaseBusiness` (używa `CaseHeader`, `ICaseBusiness`) | **Tak** (XML JAXB) |
| JMS (kolejki per węzeł) | `mercury-srv/.../org/mercury/logic/jms/*Sender` (np. `CaseRegistryChangesSender` wysyła `CaseLastUpdatedBuffer`) | Przypuszczenie: nie. Przenoszą encje i bufory, nie `Dto*`. Sprawdzić rodzaj komunikatu (obiekt serializowany czy tekst) |
| RMI | `hgdb-rmi-server-api` (`org.spring4hgdb.remoting.rmi`) | Do sprawdzenia (serializacja Javy) |
| HTTP invoker (Spring) | punkty `/remoting/*` (widoczne w testach `hgdb-client-open`), `mercury-spring-remoting` | Do sprawdzenia (serializacja Javy) |

`DtoMrcObject`, `DtoMrcList` i `DtoPropertyMap` są używane w modułach `mercury-srv`, `mercury-srv-slave`
i `mercury-ws-server`. `mercury` nie ma `hgdb-client-open` w żadnym POM-ie. Klient `hgdb-client-open` służy
zewnętrznym integracjom (`JaxWsProxyFactoryBean` na interfejsach z `mercury-ws-server-api`).

### Ryzyka

| # | Ryzyko | Pewność |
|---|---|---|
| R1 | **Wersje mieszane, XML.** Odbiorca ze starą biblioteką czyta elementy kwalifikowane jako nieznane i pomija je. Dane (`DtoMrcObject`, `DtoMrcList`, `CaseHeader`) są puste, bez błędu. Działa w obie strony (nowy odbiorca, stary nadawca) | Pewne dla nowego odbiorcy i starego nadawcy (eksperyment: wariant A odczytywał kwalifikowane próbki jako puste). Kierunek odwrotny: przypuszczenie |
| R2 | **Serializacja Javy.** Dotyczyła `DtoPropertyMap` (`implements Map` dodano po wydaniu `3.0.4.1`, ten sam `serialVersionUID`) | ✅ **Zamknięte w `mercury-lib`.** Wydana `3.0.4.1` ma `DtoPropertyMap implements Serializable`, a poprawka wraca do tego kształtu. Strumień `DtoMrcObject`, `DtoMrcList` i `CaseHeader` odczytuje się w obie strony (`3.0.4.1` ↔ `3.0.4-SNAPSHOT`) |
| R3 | **Klienci zewnętrzni** (`hgdb-client-open`, IBM BPM) ze starymi stubami | Przypuszczenie |
| R4 | **Rozbieżność z XSD poza zakresem.** Inne klasy `Mrc*` w `mercury-srv-api` (`MrcObject`, `MrcList`, `MrcSimpleProperty`…) mają ten sam wzorzec bez namespace | Do sprawdzenia, czy leżą na ścieżce SOAP |

### Opcje zniwelowania (do decyzji)

| Opcja | Opis | Ocena |
|---|---|---|
| A. Wspólne wdrożenie | Wszystkie węzły i klienci na nowej wersji naraz. Węzeł sprawdza wersję biblioteki przy rejestracji (heartbeat) i odmawia pracy z niezgodnym | Najtańsze. Wymaga pewnego mechanizmu wersji i okna wdrożenia |
| B. Czytnik tolerancyjny | Odbiór przyjmuje oba formaty: niekwalifikowany i kwalifikowany (filtr StAX dopisujący namespace do elementów modelu przed JAXB, np. w interceptorze CXF) | Pozwala na aktualizację stopniową. Dodatkowa warstwa do utrzymania, wymaga testów w obu implementacjach JAXB |
| C. Zapis w starym formacie | Nadawca wybiera format według wersji partnera | Najbardziej złożone. Wymaga negocjacji wersji |
| D. Zostawić niekwalifikowane | Poprawić XSD i próbki zamiast klas | Odrzucone: wcześniej wybrano zgodność z XSD |

**Decyzja (D7): A.** Klienci mogą i powinni aktualizować się razem z serwerem, więc czytnik tolerancyjny (B)
i negocjacja formatu (C) nie są potrzebne. Warunek: klienci pozostają na Javie 1.8 (nie zmieniać bajtkodu
bibliotek). Wersje mieszane są dopuszczalne tylko w oknie wdrożenia. Zapis w [TASK.md](TASK.md#decyzje).

## Zakres prac

1. **Inwentaryzacja kanałów.** Uzupełnić tabelę „Kanały między węzłami” o rodzaj komunikatu i klasy
   przenoszone w każdym kanale (JMS, RMI, HTTP invoker, SOAP).
2. ✅ **Test serializacji Javy** (zrobione w `mercury-lib`, patrz „Stan realizacji” i R2). Pozostaje sprawdzić
   kanały RMI i HTTP invoker w `mercury` (czy przenoszą te klasy).
3. **Test zgodności XML między wersjami.** Dodać próbki w starym formacie (niekwalifikowane) i zbadać,
   co dostaje nowy odbiorca. Test ma wykrywać pustą zawartość, a nie tylko brak wyjątku.
4. **Mechanizm wersji (opcja A).** Ustalić, gdzie węzeł przekazuje wersję biblioteki (heartbeat,
   `NodeStatus`), i jak reaguje na niezgodność. Udokumentować kolejność wdrożenia węzłów.
5. ~~Czytnik tolerancyjny (opcja B)~~ — poza zakresem (decyzja D7 = A).
6. **Wydanie.** Podbić wersję `mercury-lib`, zaktualizować `mercury.project.version` w `hgdb-client-open`
   i w `mercury`, opisać zmianę formatu w dokumentacji wydania.
7. **R4:** zdecydować, czy dopasować pozostałe klasy `Mrc*` do XSD (osobne zadanie, jeśli tak).

## Definicja Gotowości (DoD)

- Tabela kanałów jest kompletna i oparta na kodzie. Każdy kanał ma ocenę wpływu zmiany.
- Test serializacji Javy stary ↔ nowy przechodzi, albo zgodność przywrócono.
- Test zgodności XML wykrywa pustą zawartość przy formacie niezgodnym i przechodzi dla formatu wybranej opcji.
- Wybrana opcja (D7) jest wdrożona, a węzeł o niezgodnej wersji nie pracuje po cichu na pustych danych.
- Opis kolejności wdrożenia i zmiany formatu w `docs/moduly/mercury.md` oraz notatkach wydania.

## Kluczowe Pliki w Projekcie

| Plik | Rola |
|---|---|
| `mercury-lib/mercury-ws-dto-api/src/main/java/pro/ibpm/mercury/ws/server/api/returns/Dto*.java` | Klasy modelu mrcObject |
| `mercury-lib/mercury-srv-api/src/main/java/pro/ibpm/mercury/business/data/api/CaseHeader.java`, `MrcObjectMetadata.java`, `MrcNamespaces.java` | Nagłówek sprawy |
| `mercury-lib/mercury-ws-dto-api/src/test/java/.../DtoXmlContractTest.java` | Test kontraktowy |
| `mercury-lib/mercury-ws-dto-api/dto-samples/*.xml`, `src/main/resources/xml-schemas/hgdb-mrc-object-3.0.xsd` | Próbki i XSD |
| `mercury/mercury-srv-slave/src/main/java/org/mercury/slave/server/client/cxf/WsClient.java` | Klient SOAP węzła slave |
| `mercury/mercury-srv/src/main/java/org/mercury/logic/jms/` | Wysyłanie komunikatów JMS |
| `mercury/mercury-core-server/src/main/java/org/mercury/cluster/internal/api/` | Stan węzła (`NodeStatus`, `INodeStatusMonitor`) |
| `mercury/hgdb-rmi-server-api/`, `mercury-lib/mercury-spring-remoting/` | RMI i HTTP invoker |
| `hgdb-client-open/pom.xml` | `mercury.project.version` |

## Słownik / Zasady

- Element kwalifikowany: element XML w przestrzeni nazw `http://business.dto.ws.hgdb.io/mrcObject`.
- Wersje mieszane: węzły lub klienci z różnymi wersjami `mercury-lib` w jednym klastrze.
- Cicha utrata danych: odczyt bez wyjątku, w którym JAXB pomija elementy spoza oczekiwanej przestrzeni nazw.
- Kod ma wyższy priorytet niż dokumentacja. Wnioski niepotwierdzone w kodzie oznaczono jako przypuszczenie.
