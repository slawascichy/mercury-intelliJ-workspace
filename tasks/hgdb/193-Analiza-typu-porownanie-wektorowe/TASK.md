# [193] Analiza typu sprawy z porównaniem wektorowym (odległość nowej definicji od istniejącej)

> Zadanie wydzielone z [133 – Swagger](../133-Swagger-implementacja/TASK.md) (obserwacja 55, decyzja autora z 2026-10-20).
> Zadanie 133 nie zależy od tego zadania. Zadanie jest propozycją do rozważenia, nie ma jeszcze decyzji o realizacji.

## Cel zadania
Ograniczyć powstawanie przypadkowych wersji typu sprawy podczas zapisu (`save`), w którym typ jest ustalany z przesłanych danych.
Zamiast dopasowania „zgadza się albo nowa wersja” ocenić **odległość** nowej definicji typu od definicji istniejącej i utworzyć nową
wersję tylko wtedy, gdy zmiana jest istotna. Zasada autora: minimalizujemy nowe wersje, ale każda definicja (ręczna lub wygenerowana)
może zostać nadpisana.

## Problem (stan na 2026-10-20)

Typ sprawy jest ustalany z danych (`RestVariableReader` dla REST, czytniki XML dla SOAP). Nowa wersja typu powstaje, gdy definicja
wyliczona z danych różni się od istniejącej. Zaobserwowane przypadki (test w obie strony z zadania 133, obserwacja 55):

| Przypadek | Przykład | Skutek |
|---|---|---|
| (a) Dokument bez części pól | `TstMigB` tylko z `nazwa`, bez `kod` | nowa wersja z jednym polem, typ traci pole `kod` |
| (b) Typ wartości inny niż w definicji | klucz jako tekst zamiast liczby (`GeoAddressRegister`, `BpmBPDInstance` przy podtypie `Long`) | nowa wersja o tej samej liczbie pól |
| (c) Typ predefiniowany | `CalendarUserEvent` (id `-2`) | po zapisie dostaje wersję w bazie |
| (d) Różnice tylko w metadanych | tytuły, opisy, parametry GUI (`arg3` 256 → 64) | nowa wersja, a typy pól i podtypy identyczne (16 typów w teście) |

## Stan obecny w kodzie (do zweryfikowania w trakcie zadania)

Wszystko w `mercury-srv`, `org.mercury.business.data.internal.api.CaseBusinessSupport` i `org.mercury.single.node.business.data.CaseBusiness`.

- **Identyfikacja typu:** `step1TryReadCaseHeader` liczy sumę kontrolną nazw pól (`MTypeCaseUtils.calculateSumControl`), a
  `step2TryIdentifyType` szuka typu po `typeId`, po nazwie klasy i sumie, po kodzie i sumie, a na końcu po samym kodzie (ostatnia wersja).
  To jest dopasowanie dokładne, bez miary podobieństwa.
- **Zmiana definicji:** `prepareTypeParam` i `updateParamDefinition` ustawiają `isChanged` m.in. gdy brakuje opisu lub etykiety, zmienia się
  `htmlControlName`, `paramType` albo podtyp. `addParams` w `CaseBusiness` składa listę parametrów z danych.
- **Istniejące narzędzia ograniczania wersji:**
  - parametr kontekstu `saveRequestContext.forceChangeType` (`context.requestProperties`, domyślnie z
    `mercury.saveRequestContext.forceChangeType.default`, a gdy brak, `true`). Sprawdzone: z `false` zapis przykładów 76 typów nie tworzy
    żadnej nowej wersji, a nowe pole jest pomijane,
  - `CaseBusinessSupport.IGNORED_TYPE_FIELDS`: dziś tylko do porównania z repozytorium CMIS (`refreshTypeCase`), a wpisywanie całej listy
    do kontekstu nie jest praktyczne,
  - pomijanie pustych list i `null` oraz typ z poprzedniej wersji dla pustej listy (poprawka obserwacji 54).

## Pomysł rozwiązania (do rozważenia)

1. **Wektor cech definicji typu.** Każde pole to wektor cech, np. nazwa, typ atrybutu (`AttributeType`), podtyp, lista czy wartość pojedyncza,
   kod typu zależnego, istotne parametry (długość, format). Typ to zbiór takich wektorów.
2. **Miara odległości** nowej definicji od definicji najnowszej wersji (np. liczba różnic ważona istotnością cechy, podobieństwo Jaccarda
   zbiorów pól, odległość edycyjna). Cechy czysto metadanowe (tytuł, opis, GUI) mają wagę zerową.
3. **Reguła decyzji z progami:** odległość 0 lub tylko metadane: ta sama wersja. Dodanie pola: opcjonalnie rozszerzenie. Zmiana typu pola
   albo usunięcie pola: nowa wersja (lub odrzucenie zapisu przy `forceChangeType=false`). Progi konfigurowalne.
4. **Pole brakujące w dokumencie** nie oznacza usunięcia z typu (przypadek a): odległość liczona tylko dla pól przesłanych, chyba że
   jawnie wymuszono inaczej.

## Podział na etapy (propozycja)

| Etap | Zakres | Wynik |
|---|---|---|
| 1 | Analiza: zebrać wszystkie przypadki powstawania nowych wersji (testy, scenariusze SoapUI, obserwacja 55) i zmierzyć, które są „istotne” | tabela przypadków z oczekiwaną decyzją |
| 2 | Projekt: wektor cech, miara odległości, progi, miejsce w kodzie (`step2TryIdentifyType` albo `addParams`) | opis w dokumentacji i decyzje do uzgodnienia |
| 3 | Implementacja za przełącznikiem w konfiguracji (domyślnie wyłączona, zachowanie dotychczasowe) | kod i testy jednostkowe |
| 4 | Test porównawczy na bazie testowej (76 typów z zadania 133): liczba nowych wersji przed i po | raport |

## Ryzyka i pytania otwarte

| # | Pytanie | Uwagi |
|---|---|---|
| Q1 | Gdzie ma działać porównanie: tylko przy `save` z REST/JSON, czy także w SOAP i XML? | W SOAP typ listy niesie atrybut `type`, w JSON go nie ma |
| Q2 | Czy zmiana `htmlControlName` bez zmiany typu ma tworzyć wersję? | Dziś `updateParamDefinition` ustawia `isChanged` |
| Q3 | Jak zachować zgodność wsteczną z istniejącymi instalacjami i sumą kontrolną nazw pól? | Suma jest używana do identyfikacji typu |
| Q4 | Jak traktować typy predefiniowane (BPM, kalendarz), których definicje wstawia kod tylko wtedy, gdy ich nie ma? | Istniejące bazy zachowują stare definicje (obserwacja 52) |
| Q5 | Czy progi mają być globalne, per typ czy per żądanie (`requestProperties`)? | |

## Definicja Gotowości (DoD)
- Etap 1 i 2 zakończone i zatwierdzone przez autora (decyzja o realizacji etapów 3 i 4 jest osobna).
- Jeżeli realizowane etapy 3 i 4: przełącznik w konfiguracji, testy jednostkowe miary odległości i regresji, raport z liczby nowych wersji
  na 76 typach testowych (wynik nie gorszy niż `forceChangeType=false` dla zmian nieistotnych i niezmieniony dla zmian istotnych).
- Dokumentacja workspace zaktualizowana (`docs/moduly/mercury.md`, `docs/obserwacje.md`).

## Kluczowe Pliki w Projekcie

Ścieżki względne do `D:\workspace\git`.

- `mercury/mercury-srv/src/main/java/org/mercury/business/data/internal/api/CaseBusinessSupport.java`: `step1TryReadCaseHeader`,
  `step2TryIdentifyType`, `prepareTypeParam`, `updateParamDefinition`, `IGNORED_TYPE_FIELDS`.
- `mercury/mercury-srv/src/main/java/org/mercury/single/node/business/data/CaseBusiness.java`: `transform2Cases`, `addParams`.
- `mercury-lib/mercury-core/src/main/java/pro/ibpm/mercury/context/ContextRequestProperties.java`: `SaveRequestContext.FORCE_CHANGE_TYPE`.
- `mercury/mercury-ws-app/src/main/java/pro/ibpm/mercury/rest/server/utils/RestVariableReader.java`: typ pola z wartości JSON.
- `tasks/hgdb/133-Swagger-implementacja/etap-2-openapi-typy-spraw.md` i `docs/obserwacje.md` (wpisy 51–55): wyniki testu w obie strony.
