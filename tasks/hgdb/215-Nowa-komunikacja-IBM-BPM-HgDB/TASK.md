# [215] Nowa komunikacja IBM BPM -> HgDB (projekt `hgdb-ibm-bpm-client`)

**Status (2026-10-27):** **not now** (decyzja autora, 2026-10-27); wróci po decyzji autora. Zakres: nowe rozwiązanie komunikacji IBM BPM -> HgDB w miejsce zamrożonego `mercury-client`.

Zadanie założone przez autora 2026-10-27 (stan analizy z tego dnia). Powiązane: zadanie 214 (migracja logowania) i osobne zadanie dla SecurityProvidera (stos cache).

## Przyczyna

`mercury-client` przestaje być rozwijany. Decyzja autora (2026-10-27): repozytorium zostaje w postaci zgodnej z `D:\workspace\git\mercury-v3.0.1.20210709` i nie jest prowadzone dla Mercury 3.0.4 i nowszych. Powody, które da się zweryfikować:

1. **Nie buduje się na `master`.** W POM-ach nie ma definicji właściwości `hgdb-client.version`, `httpclient.version` i `servlet-api.version` (Maven kończy na czytaniu POM-ów).
2. **Rozjechało się z API serwera i bibliotek.** Po zadaniu 169 (identyfikator sprawy jako `String`) przestają się kompilować m.in. `TLoggerEventProvider` w `mercury-client-mock`. W `mercury-bpm` co najmniej dziesięć klas używa `pl.slawas.twl4j`, interfejsów `_IObjectCache*` albo pakietu `...cache.config`, których nie ma w `sccommon-cache` 2.0.0.1 (ehcache 3.6.1).
3. **Stos bibliotek w BPM jest wspólny z SecurityProviderem.** Oba produkty instalują `sccommon-utils`, `sccommon-cache` i `ehcache` do tego samego katalogu BPM. `hgdb-client-open` zostaje na `sccommon` 2.0.0.1 i ehcache 3.6.1 (decyzja autora), a SecurityProvider na `sccommon` 2.0.0.1 się nie kompiluje (siedem klas cache). Utrzymywanie `mercury-client` na starym stosie wymagałoby dwóch wersji tych samych klas w jednym BPM-ie.
4. **Migracja logowania na Logback (zadanie 214)** usuwa log4j z serwera Mercury; `mercury-client` jest dodatkowym, trudnym do zbudowania (biblioteki IBM, Spring 4.1.9) repozytorium w tej zmianie.
5. **W IBM BPM jest już narzędzie czytające dokumentację Swagger/OpenAPI**, więc większość funkcji `mercury-client` (klient usług, mappery, akcje) można zastąpić wywołaniami REST serwera.

## Co jest naprawdę potrzebne

Jedyna funkcja, która musi przetrwać, to `mercury-bpm/src/main/java/pro/ibpm/mercury/bpm/dao` (14 klas, 1843 linie). Jak działa:

- `MrcTaskDAO`, `MrcBpdInstanceDAO` i `MrcTaskNarrativeDAO` nadpisują DAO samego BPM (`TaskDAO` itd.; podmiana w `registry.persistence.xml`, osobno dla BPM 8.5.0, 8.5.5 i 8.5.6).
- Po zapisie zadania, instancji procesu albo narracji w BPM klasy `BpmTaskBufferDAO`, `BpmBPDInstanceBufferDAO` i `BpmTaskNarrativeBufferDAO` budują rekordy buforowe (`Transformer`) i w puli wątków (20–200 wątków; zadanie czeka 2 s na połączenie z narracją) wstawiają je `INSERT`-em JDBC (`AbstractDAO`, źródło danych z JNDI) do tabel bufora w bazie Mercury (encje `MBpmTaskBuffer` itd. w `mercury-lib`).
- Przy błędzie zapisu zrzucają dane do pliku (`dumpErrorLog`). Serwer Mercury przetwarza bufor po swojej stronie.

Obecnie BPM pisze więc wprost do bazy Mercury i zna jej schemat. Zależność od IBM jest tylko w klasach nadpisujących DAO; reszta modułu nie jest potrzebna.

## Cel

Nowe rozwiązanie komunikacji IBM BPM -> HgDB, w którym:

1. zdarzenia zadań, instancji procesów i narracji z BPM docierają do HgDB bez bezpośredniego zapisu do bazy Mercury,
2. awaria albo niedostępność HgDB nie blokuje zapisu w BPM i nie gubi zdarzeń,
3. projekt `hgdb-ibm-bpm-client` zawiera tylko to, co działa w BPM (klasy nadpisujące DAO i wysyłkę), bez reszty `mercury-client`.

## Warianty kanału (do rozstrzygnięcia)

| Wariant | Uwagi |
|---|---|
| A. JDBC do tabel bufora (stan obecny) | BPM zna schemat bazy Mercury i musi mieć do niej dostęp; sprzężenie z bazą |
| B. REST z OAuth | REST serwera ma tylko OAuth 2.0 (`/rest/token`, grant `password` i `refresh_token`). Basic jest tylko w `RemoteBasicAuthFilter` dla RMI i CMIS, więc może trzeba go dodać do REST. Do sprawdzenia: czy narzędzie Swagger w BPM obsłuży token z odświeżaniem. Wywołanie synchroniczne wiąże zapis w BPM z dostępnością Mercury, więc i tak potrzebny jest bufor z ponawianiem |
| C. DAO -> JMS/MQ/Kafka -> odbiorca w Mercury | Oddziela dostępność, daje kolejkowanie i ponawianie. Po stronie Mercury nowy komponent (`org.mercury`) zapisujący bufor. JMS jest natywny w WebSphere; precedens: `security-mq-client` w SecurityProviderze (ActiveMQ i Spring JMS). Klient Kafki w BPM ma wymagania co do wersji Javy i bibliotek |

Rekomendacja z analizy (2026-10-27): wariant C z JMS, bo hak działa w zapisie BPM. B jest dobrą alternatywą, jeśli narzędzie Swagger w BPM poradzi sobie z OAuth.

## Wymagania i ograniczenia

- **Logowanie w BPM dostarcza BPM** (`log4j.jar`, `slf4j-api`; wersje zależą od BPM, 8.6.8 i nowsze mają `slf4j-api` 2.0.1). Kod po stronie BPM używa wyłącznie API SLF4J; nie wolno dodawać Logbacka ani `log4j-over-slf4j`.
- **Zgodność ze stosem w BPM:** nowy projekt nie może wnosić własnych wersji `sccommon-*` ani ehcache, dopóki SecurityProvider nie przejdzie na ten sam stos (osobne zadanie). Najlepiej bez zależności od `sccommon`.
- **Wersje BPM:** ustalić, które wersje obsługujemy (`mercury-client` ma rejestry dla 8.5.0, 8.5.5 i 8.5.6; POM wskazuje 8.6.3.21030; biblioteki IBM w `D:\workspace\lib\TeamWorks-*` i `WebSphere-*`).
- **Java:** poziom Javy zgodny z BPM.
- **Zgodność wsteczna:** `mercury-client` zostaje dla serwera w wersji `v3.0.1.20210709`; nowy projekt dotyczy Mercury 3.0.4 i nowszych.
- **Bezpieczeństwo:** poświadczenia kanału poza kodem, w konfiguracji BPM.

## Do ustalenia

1. Wybór wariantu A/B/C (patrz wyżej) i ewentualne dodanie Basic do REST.
2. Lokalizacja i możliwości narzędzia Swagger w BPM (OAuth, odświeżanie tokenów, tryb ponawiania).
3. Czy bufor (tabele `MBpmTaskBuffer` itd.) zostaje, czy odbiorca zapisuje wprost do modelu Mercury.
4. Obsługiwane wersje IBM BPM i Java.
5. Sposób instalacji w BPM (podmiana DAO w `registry.persistence.xml`) i wycofania zmian.

## Poza zakresem

- Dalszy rozwój `mercury-client` (poza utrzymaniem zgodności z `v3.0.1.20210709`).
- Przejście SecurityProvidera na `sccommon` 2.0.0.1 (osobne zadanie).
- Migracja logowania serwera na Logback (zadanie 214).

## Kroki

1. Rozstrzygnąć wariant kanału i zakres z autorem.
2. Utworzyć repozytorium `hgdb-ibm-bpm-client` (nowe klasy w `org.mercury`, zgodnie z zasadą dla nowych komponentów).
3. Przenieść klasy nadpisujące DAO i wymienić zapis JDBC na wybrany kanał.
4. Jeśli wariant C: dodać odbiorcę po stronie serwera Mercury.
5. Testy na BPM (zadanie, instancja procesu, narracja; niedostępność HgDB i ponowienia).
6. Dokumentacja instalacji i wycofania; aktualizacja `docs/moduly`.

## Kryteria ukończenia

- Zdarzenia z BPM docierają do HgDB wybranym kanałem, bez zapisu do bazy Mercury z BPM.
- Przy niedostępności HgDB żadne zdarzenie nie ginie, a zapis w BPM się nie blokuje.
- Projekt buduje się na bibliotekach IBM z `D:\workspace\lib` i nie zależy od `mercury-client`.
- Opisane wersje BPM, Javy i instalacja.
