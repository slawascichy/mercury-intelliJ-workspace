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

## Pytania do autora

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
