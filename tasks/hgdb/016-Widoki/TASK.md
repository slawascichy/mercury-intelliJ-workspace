# [16] Widoki

https://github.com/slawascichy/hgdb/issues/16
https://github.com/slawascichy/hgdb/issues/17
Obsługa widoków jest bardzo istotna. Trzeba opracować koncepcję jak to w końcu zaimplementować. Na pewno trzeba zrobić:

1. Obsługa widoków relacyjnych utworzonych w bazie danych, są problemy z ich w relacyjnej bazie danych, gdy sam 
   widok jest w zależności od innych widoków/pakietów. W Oracle jest coś takiego jak status `invalid`, kompilujesz 
   przy pierwszym użyciu, w PosthreSQL pojawiają się lock, i błędy.
2. Wykorzystanie mechanizmów dynamicznych jakie już są zaimplementowane
3. Wynik widoków:
   - Prezentacja w standardzie Excel
   - Prezentacja w standardzie listy parametrów?
4. Integracja z mechanizmami raportowania i eksportu danych z Iron Server
5. Sprawdź ze zmianami Github `17: Raporty - integracja z IRON Poi Server - obsługa widoków`.

## Rozpoznanie stanu w kodzie (2026-10-27)

Wszystko poniżej wynika z lektury kodu (`mercury`, `mercury-lib`); niczego nie uruchamiano. Commity zadania 17 (2019, `mercury` i `mercury-lib`) nie zostały jeszcze przejrzane.

### Co już jest

| Element | Gdzie | Co robi |
|---|---|---|
| `CaseViewDefinition` | `mercury-lib/mercury-entities` (tabela `IGO_DA_CASE_VIEW_DEFS`) | Definicja widoku generowanego z typów spraw: nazwa, lista parametrów (`metadataInfo`, JSON), zakres dat typów, `skipHeaderFields`, `credentialsMode`, `ignoreAlternateFields`, `baseTypeCodes`, wersje (`generatedVersion`, `publishVersion`) |
| `PublishedCaseViewDefinition` | `mercury-lib/mercury-entities` (tabela `COM_PUB_CVIEW_DEFINITIONS`) | Informacja, jaką wersję widoku opublikował który węzeł (`viewName`, `version`, `nodeName`, `status`) |
| `CaseViewDefinitionLogic` | `mercury-srv` | `generateView`, `createView`, `updateView`, `dropView`; wymaga uprawnień „all RO” |
| `CaseViewQueryBuilder` | `mercury-srv` | Buduje SQL widoku z typów. Limit 250 kolumn, pola stałe sprawy z prefiksem `M_` |
| `CaseViewDefinitionDAO` | `mercury-dao` | Wykonuje `CREATE VIEW ... AS`; przy `force` najpierw `DROP` |
| Kolejka JMS | `mercury-srv` (`CaseViewCreatorSender`, `Receiver`, `Listener`) | Asynchroniczne generowanie widoków na węzłach |
| Usługa SOAP | `ICaseViewDefinitionAction` | CRUD definicji widoków |
| Eksport do Excela | `ExportGenerator`, `PoiServerWriter`, klienci RMI `PoiServerWriterClient`/`PoiServerLoaderClient` | Eksport **spraw** (`Case` → `ExcelRow`), import z Excela, praca z serwerem POI (Iron) |

### Czego nie znalazłem

1. Usługi odczytu zawartości widoku: `viewName` nie jest używane w usługach wyszukiwania ani w REST. Widok jest tylko tworzony w bazie, a odczytuje go kod spoza Mercury.
2. Obsługi widoków relacyjnych utworzonych ręcznie w bazie (punkt 1 zadania): brak rejestru, odczytu metadanych kolumn, sprawdzania statusu (`INVALID` w Oracle) i zależności.
3. Usługi REST (`I*ExtRest`) dla widoków. W `mercury-ws-app/src/main/java` nie ma odwołań do definicji widoków.
4. Eksportu wierszy widoku do Excela. Istniejący eksport przetwarza obiekty `Case`, a nie dowolne wiersze.

## Propozycja koncepcji (przypuszczenie, do uzgodnienia z autorem)

Podział na etapy, bo punkty 1–5 różnią się wielkością i ryzykiem:

| Etap | Zakres | Szac. | Wynik |
|---|---|---|---|
| 0. Rozpoznanie | Przegląd commitów zadania 17, czytanie `generateView` pod kątem blokad w PostgreSQL (drop/create pod obciążeniem), test na kopii bazy; odpowiedzi na pytania poniżej | 1–2 d | Notatka z koncepcją i decyzjami |
| 1. Odczyt widoków (punkt 2) | Usługa REST: lista widoków (z definicji i z katalogu bazy), metadane kolumn, odczyt stronicowany z filtrem i sortowaniem po kolumnach z metadanych (parametryzowane zapytania, bez składania SQL z danych klienta), uprawnienia, limity i timeout | 4–6 d | REST `I*ExtRest` w `mercury-ws-app`, OpenAPI w 6 językach |
| 2. Odporność (punkt 1) | Oracle: wykrycie `INVALID` i `ALTER VIEW ... COMPILE`. PostgreSQL: `lock_timeout`, ponowienie, kolejność zależności (`pg_depend`) przy przebudowie | 3–4 d | Widoki zależne od innych widoków nie blokują odczytu |
| 3. Wynik (punkt 3) | JSON (kolumny + wiersze), Excel przez istniejący mechanizm POI (strumieniowo), „lista parametrów” jako obiekt par nazwa–wartość | 3–4 d | Eksport wiersza widoku do Excela |
| 4. Iron Server (punkty 4–5) | Eksport asynchroniczny przez klienta RMI do serwera POI, status zadania, zgodność ze zmianami z zadania 17 | 2–3 d | Raport z widoku jako zadanie w tle |

Razem ok. 2–3 tygodnie (przypuszczenie). Etapy 1–3 można wydać bez etapu 4.

## Pytania do autora (odpowiedzi w sekcji „Decyzje autora”)

1. Które bazy obsługujemy dla widoków: PostgreSQL i Oracle (stan z punktu 1), czy tylko PostgreSQL?
2. Czy „widok” ma być wyłącznie definicją z `CaseViewDefinition` (generowany z typów), czy także dowolny widok relacyjny z bazy (rejestrowany przez administratora)?
3. Kto ma prawo odczytu widoku: ten sam model uprawnień co sprawy (typy i pola), czy osobne uprawnienie do widoku?
4. Czym jest „prezentacja w standardzie listy parametrów”: lista par nazwa–wartość dla wiersza (jak `MrcSimplePropertyMap`), czy tabela kolumn z metadanymi?
5. Czy eksport do Excela ma być synchroniczny (limit wierszy), czy tylko asynchroniczny przez Iron Server?
6. Czy zmiana wymaga nowych DTO w `mercury-lib` (a więc kolejnego wydania biblioteki), czy zostajemy przy `mercury-ws-app`?

## Definicja Gotowości (propozycja)

- Decyzje do pytań 1–6 zapisane w tym pliku (etap 0).
- Etapy 1–3 zrealizowane i przetestowane na kopii bazy z widokami zależnymi od innych widoków.
- Po zmianie API: `openapi-doc-report.txt`, klucze `openapi-docs_*` w 6 językach (tłumaczenia przez translator Gemini), dokumentacja w `docusaurus-hgdb`.
- Obserwacje wynikłe z rozpoznania dopisane do `docs/obserwacje.md`.

## Decyzje autora (2026-10-27)

| # | Pytanie | Decyzja |
|---|---|---|
| 1 | Bazy | Implementacja dla PostgreSQL, Oracle, MySQL i MSSQL, wszystkie cztery |
| 2 | Czym jest widok | `CaseViewDefinition` plus widoki generowane automatycznie dla typów spraw i dokumentów (autor nie pamięta, czy trafiają do `CaseViewDefinition`: sprawdzone niżej) |
| 3 | Uprawnienia | Model uprawnień jak dla spraw |
| 4 | „Lista parametrów” | Standard prezentacji „Excel” zaimplementowany w Iron POI Server (`D:\workspace\git\poi-toolkit`) |
| 5 | Eksport | Gotowe mechanizmy eksportu danych rozszerzamy o widoki (bez budowy nowego eksportu) |
| 6 | DTO | Nowe DTO trafiają do `mercury-lib` (kolejne wydanie biblioteki) |

### Wnioski z rozpoznania po decyzjach

**Ad. 2. Widoki typów trafiają do `CaseViewDefinition`.** `CaseViewCreatorReceiver` dla każdego kodu typu wylicza nazwę widoku `T_<kod typu>` (`CaseBusinessSupport.VIEW_PREFIX`), a potem wywołuje `createView` (albo `updateView`, gdy definicja już jest)
i `generateView`. Definicja jest więc zapisana w `IGO_DA_CASE_VIEW_DEFS` (zakres dat 2000–4000, tryb uprawnień `AND`, bez pomijania pól stałych). Generowanie po zmianie typu włącza parametr
`mercury.view.createAfterTypeChange` (`CaseBusiness.newViewIsNeeded`), a kolejkę zasilają `CaseBusiness` oraz bufory BPM (`BpmBPDInstanceBufferSecretarySingleton`, `BpmTaskBufferSecretarySingleton`).
Do ustalenia przy rozpoznaniu: domyślna wartość tego parametru i to, czy widoki istnieją na środowiskach klientów.

**Ad. 1. Cztery bazy.** `CaseViewDefinitionDAO` i `CaseViewQueryBuilder` nie zawierają kodu zależnego od dialektu (brak odwołań do Oracle, PostgreSQL, MySQL, MSSQL). Kod w DAO zawiera komentarz,
że `CREATE OR REPLACE` nie działa w PostgreSQL przy zmianie liczby kolumn, więc przy `force` jest `DROP` i `CREATE`, co oznacza chwilową niedostępność widoku. Odczyt metadanych widoku (kolumny, status, zależności)
wymaga osobnej implementacji na każdą z czterech baz (przypuszczenie: `information_schema` w PostgreSQL, MySQL i MSSQL; `ALL_TAB_COLUMNS`/`ALL_OBJECTS` w Oracle). Testy na czterech bazach to główny koszt etapu 2.

**Ad. 4 i 5. Format wyniku z Iron POI Server.** Model „Excel” (`org.iron.poi.excel.core`): `IExcelData` zwraca wiersze `ExcelRow` (numer wiersza, mapa numer kolumny → `ExcelColumnValue` z tekstem `value` i `searchValue`),
nagłówek `Map<Integer, String>`, typy kolumn `Map<Integer, String>` i stronicowanie `ExcelPage`. Widok powinien więc być mapowany na ten sam model (kolumny widoku → numerowane kolumny, nazwy → nagłówek, typy SQL → typy kolumn),
a istniejący eksport (`ExportGenerator`, `PoiServerWriter`) dostanie drugie źródło wierszy obok obiektów `Case`.

**Ad. 6. DTO w `mercury-lib`.** Nowe obiekty (definicja kolumny widoku, wynik stronicowany widoku, status widoku) powstają w `mercury-lib`, więc po etapie 1 potrzebne jest wydanie biblioteki, a potem podbicie wersji w `mercury`.
Zalecenie: jedno wydanie po zamknięciu projektu DTO w etapie 0, a nie po każdym etapie.

### Zmiany w etapach (wersja 2)

| Etap | Zmiana względem propozycji |
|---|---|
| 0 | Dochodzi: ustalenie wartości `mercury.view.createAfterTypeChange` i stanu widoków `T_*` na środowisku testowym, przegląd `poi-toolkit` (`IExcelData`, `ExcelRow`) pod mapowanie wiersza widoku, projekt DTO |
| 1 | Odczyt widoków z uprawnieniami jak dla spraw (typ i pola widoku wynikają z `baseTypeCodes` i listy parametrów definicji) |
| 2 | Metadane i status widoku dla czterech baz, `lock_timeout` i ponowienia w PostgreSQL, `ALTER VIEW ... COMPILE` w Oracle; przebudowa bez okna niedostępności tam, gdzie baza na to pozwala |
| 3 | Wynik w modelu `IExcelData` przez istniejące mechanizmy eksportu |
| 4 | Eksport asynchroniczny przez klienta RMI; bez nowych mechanizmów, rozszerzenie istniejących |

Szacunek (przypuszczenie) rośnie do ok. 3 tygodni z powodu czterech baz.
