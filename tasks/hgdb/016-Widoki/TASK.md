# [16] Widoki

**Status (2026-10-28, koniec dnia):** etapy 0, 1 i 2 zamknięte (poza testem na kopii bazy z widokami zależnymi od innych widoków); etap 3 w rozpoznaniu (sekcja „Etap 3: przegląd”). Podzadanie 217 zamknięte po stronie kodu REST, zadanie 218 (czyściciel starych wersji) założone. Kolejność autora: 016, 049, 191. Plan: `plan-najblizszych-dzialan-2026-10-26.md`

**Podzadanie:** 217 „Reprezentowanie użytkowników” (`../217-Reprezentowanie-użytkowników-w-kontekście/TASK.md`), realizowane na gałęzi `hgdb-016`. Dotyczy tożsamości i ról w `Context`, od których zależy kontrola uprawnień widoków..

https://github.com/slawascichy/hgdb/issues/16
https://github.com/slawascichy/hgdb/issues/17
Obsługa widoków jest bardzo istotna. Trzeba opracować koncepcję jak to w końcu zaimplementować. Na pewno trzeba zrobić:

1. Obsługa widoków relacyjnych utworzonych w bazie danych. Są problemy z nimi w relacyjnej bazie danych, gdy sam 
   widok jest w zależności od innych widoków/pakietów. W Oracle jest coś takiego jak status `invalid`, kompilujesz 
   przy pierwszym użyciu, w PostgreSQL pojawiają się lock, i błędy.
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

## Wyniki rozpoznania etapu 0 (2026-10-28)

Czytano kod i historię git; niczego nie uruchamiano. Pytania 1–6 z sekcji „Pytania do autora” mają decyzje (patrz wyżej), nie ma nowych pytań blokujących etap 1.

1. **`mercury.view.createAfterTypeChange` nie ma wartości domyślnej w kodzie.** `CaseBusiness.newViewIsNeeded()` zwraca `false`, gdy parametru brak. Wartość `true` jest w `mercury-server/IBPM/mercury/config/mercury.properties`, w `mercury-docker/mercury-3.0/docker-init-config/config/mercury.properties` i w pakietach instalacyjnych. Widoki `T_<kod typu>` istnieją więc tam, gdzie konfiguracja pochodzi z tych szablonów. Czy istnieją na konkretnym środowisku klienta, rozstrzygnie zapytanie o `IGO_DA_CASE_VIEW_DEFS` (do wykonania na serwerze testowym).
2. **Commity zadania 17 (czerwiec–sierpień 2019, ok. 20 w `mercury`, kilka w `mercury-lib`) dotyczą głównie Lucene.** Najwięcej zmian jest w `mercury-lucene-indexes` (kolektory, zapytania, wyniki), a nie w eksporcie widoków. Z widokami wiążą się tylko dwa commity (2019-07-02 i 2019-07-30, pliki `*CaseView*`/`*ViewDef*`) oraz zmiany encji definicji widoku w `mercury-lib` (lista `baseTypeCodes`, rozszerzony kontekst z polami definicji widoku). Integracji z Iron POI Server dla widoków w tych commitach nie znalazłem (przypuszczenie: zadanie 17 nie zostało dokończone).
3. **Historyczny błąd: „Brak tworzenia widoków reprezentujących typy” (commit `fcf18671e`, 2020-05-11, CMINDEV-2422).** Autor nie znalazł wtedy przyczyny, a poprawka dotyczyła tylko `MDictDAO.checkExists` (zwraca `boolean`). Przy etapie 2 warto sprawdzić, czy problem był w kolejce JMS albo w przebudowie widoku (`CaseViewCreatorReceiver`).
4. **Generowanie widoku w DAO.** `CaseViewDefinitionDAO.generateView` składa `CREATE VIEW <nazwa> AS <zapytanie>` jako natywne `executeUpdate`, a przy `force` robi `DROP VIEW` i `CREATE VIEW`. Nazwa widoku trafia do SQL przez konkatenację (nazwa pochodzi z definicji, nie od klienta, ale przy odczycie widoków w etapie 1 nazwę trzeba walidować względem rejestru definicji). Blokad (`lock_timeout`), ponowień ani odczytu statusu widoku w DAO nie ma.
5. **Model Excela w `poi-toolkit` (`org.iron.poi.excel.core`).** `IExcelData` udostępnia `getResult()` i `getResult(ExcelPage)` (listy `ExcelRow`), `getHeader()` i `getColumnTypes()` (mapy numer kolumny → tekst), `getResultSize()` oraz nawigację po stronach (`ExcelPage`: rozmiar, numer, pierwszy i ostatni wiersz, domyślnie maks. 300 stron). To wystarcza do mapowania wiersza widoku: kolumny → numerowane kolumny, nazwy → nagłówek, typy SQL → typy kolumn. Nowa implementacja `IExcelData` nad wynikiem widoku jest prostsza niż zmiana modelu.

### Projekt DTO (do zatwierdzenia przez autora, `mercury-lib`)

| DTO | Pola | Uwagi |
|---|---|---|
| `ViewColumnDefinition` | nazwa, typ SQL, typ Mercury, pozycja, czy nullable, powiązany kod pola typu (gdy wynika z definicji) | metadane z `information_schema` / `ALL_TAB_COLUMNS` |
| `ViewInfo` | nazwa, identyfikator definicji (`CaseViewDefinition`), status (`VALID`, `INVALID`, `MISSING`), wersja wygenerowana i opublikowana, lista kolumn | status dla czterech baz w etapie 2 |
| `ViewDataPage` | numer strony, rozmiar, liczba wierszy, kolumny, wiersze (lista list wartości tekstowych) | odpowiada `ExcelPage`/`ExcelRow` |
| `ViewQuery` | nazwa widoku, strona, rozmiar, filtry (kolumna, operator, wartość), sortowanie (kolumna, kierunek) | kolumny tylko z metadanych widoku; wartości jako parametry zapytania |

### Wniosek i następny krok

Etap 0 jest domknięty po stronie rozpoznania kodu. Do zrobienia na serwerze testowym: zapytanie o stan `IGO_DA_CASE_VIEW_DEFS` i widoków `T_*` oraz próba `DROP`/`CREATE` pod obciążeniem w PostgreSQL. Zapraszam do zatwierdzenia projektu DTO; potem zakładamy gałąź `hgdb-016` (po Twoim potwierdzeniu) i zaczynamy etap 1.

## Etap 1: rozpoznanie wzorców i plan implementacji (2026-10-28)

**DTO.** Zatwierdzone przez autora, zmiany w `mercury-lib` (gałąź `hgdb-016`): pakiet `org.mercury.dto.view` w `mercury-ws-dto-api` (`ViewColumnDefinition`, `ViewInfo`, `ViewQuery`, `ViewFilter`, `ViewSort`, `ViewDataPage`, `ViewStatus`, `ViewFilterOperator`, `ViewSortDirection`). Wydanie biblioteki (następna wersja po 3.0.4.18) po zamknięciu etapu 1.

**Warstwy w `mercury` (wersja pierwotna, zastąpiona sekcją „Korekta planu: rozszerzenie istniejących mechanizmów”).**

| Warstwa | Moduł | Zadanie dla widoków |
|---|---|---|
| DAO (interfejs i implementacja) | `mercury-dao-api`, `mercury-dao` | Nowe `IViewDataDAO`: metadane kolumn widoku (etap 1 dla PostgreSQL, pozostałe bazy w etapie 2) i odczyt stronicowany natywnym SQL z parametrami |
| Logika/biznes | `mercury-srv` (`org.mercury`) | `IViewDataBusinessInternal`: lista widoków z `CaseViewDefinition`, `ViewInfo`, odczyt strony, kontrola uprawnień, limity |
| REST | `mercury-ws-app` (`org.mercury.rest.server.actions...`) | `IViewDataExtRest` i `ViewDataExtRest` (`@RestController`, koperta JSON z `RestWsStatusUtils`), żądania z `Context` |
| Dokumentacja OpenAPI | `mercury-ws-app/src/main/resources/META-INF/mercury` | Klucze `openapi-docs_*` w 6 językach (tłumaczy translator Gemini) |

**Reguła uprawnień (propozycja, zgodna z decyzją „jak dla spraw”).** `SecurityContextHelperBean` udostępnia `isAllRO()`, `isRO(typeCode)`, `isAllTypesRO(typeCode)` i `getReadableParams(typeId)`.
1. Użytkownik z `isAllRO()` widzi wszystkie widoki i kolumny (jak dziś w `CaseViewDefinitionLogic`).
2. Pozostali widzą widok tylko wtedy, gdy mają odczyt **wszystkich** typów z `baseTypeCodes` definicji, bo widok już filtruje wiersze po tych typach (`typeId IN (...)`) i nie ma uprawnień na poziomie wiersza.
3. Kolumny pochodzące z pól typu, których użytkownik nie może czytać (`getReadableParams`), są pomijane w metadanych i w wyniku.
4. Widoki spoza rejestru (`CaseViewDefinition`) nie są dostępne (decyzja nr 2: zakres to definicje i widoki `T_*`).

**Odczyt.** Nazwa widoku pochodzi wyłącznie z rejestru definicji. Nazwy kolumn filtrów i sortowania są sprawdzane względem metadanych, a wartości przekazuje się jako parametry zapytania. Limity: maksymalny rozmiar strony i timeout zapytania z konfiguracji (`mercury.properties`).

**Kolejność.** (1) kompilacja `mercury` na lokalnie zainstalowanej bibliotece z DTO, (2) DAO i test jednostkowy generatora zapytań, (3) biznes z uprawnieniami, (4) REST, (5) OpenAPI i `openapi-doc-report.txt`, (6) test na serwerze dev (PostgreSQL).

## Korekta planu: rozszerzenie istniejących mechanizmów (2026-10-28)

Decyzja autora: nie budować nowego mechanizmu obok istniejącego. Rozpoznanie wykazało, że dla `CaseViewDefinition` jest już cały łańcuch usług, który rozszerzamy zamiast dodawać `IViewData*`:

| Warstwa | Istniejący element | Rozszerzenie dla widoków |
|---|---|---|
| Interfejs akcji (generyczny) | `ICaseViewDefinitionAction` w `mercury-core` (`createView`, `updateView`, `generateView`, `dropView`) | `getViewInfo`, `findViewInfos`, `readViewData` ✅ |
| Interfejs SOAP | `ICaseViewDefinitionAction` w `mercury-ws-server-api` | te same trzy metody z `@WSDLDocumentation` i zwrotkami `WsStatusWithViewInfoDto/Dtos`, `WsStatusWithViewDataPage` ✅ |
| REST | `CaseViewDefinitionRest` **generowany** (`mercury-ws-app-rest-generator`) z interfejsu SOAP | nic do ręcznego pisania; powstaje przy budowaniu (nowe wpisy dokumentacji `openapi-docs_*`) |
| Implementacja SOAP | `CaseViewDefinitionAction` (`mercury-ws-server`) | trzy metody delegujące do logiki |
| Logika | `CaseViewDefinitionLogic` (`mercury-srv`): ma już kontrolę `isAllRO()` i definicje | `getViewInfo`, `findViewInfos`, `readViewData` z regułą uprawnień z sekcji etapu 1 |
| DAO | `ICaseViewDefinitionDAO` i `CaseViewDefinitionDAO` (`generateView`, `dropView`) | odczyt metadanych kolumn i stronicowany odczyt wierszy |
| Klient | `CaseViewDefinitionLogic` w `hgdb-ws-client-cxf` i `hgdb-multi-client` implementują `ICaseViewDefinitionLogic` | trzy metody wołające usługę SOAP/REST (klient musi mieć nowe metody, bo implementuje interfejs) |
| `ws-server-api20` | generowany z interfejsu SOAP | regeneruje się przy budowaniu |

**Zmiany względem poprzedniego projektu DTO.** `mercury-srv-api` i logika nie widzą `mercury-ws-dto-api` (zależność jest odwrotna), więc DTO widoków (`org.mercury.dto.view`) przeniosłem do `mercury-core`. Zwrotki `WsStatusWithView*` leżą w `mercury-ws-dto-api` (`org.mercury.dto.view`), jak ręczne `WsStatusWithCase2Case*`. Poprzednia tabela warstw (DAO `IViewDataDAO`, biznes `IViewDataBusinessInternal`, ręczny `IViewDataExtRest`) jest zastąpiona powyższą.

**Wniosek do rozpoznania z etapu 0.** W tabeli „Czego nie znalazłem” pkt 3 („usługi REST dla widoków”) był błędny: REST dla definicji istnieje (`CaseViewDefinitionRest`, katalog `src/main/generated`). Brakuje REST do odczytu danych widoku, i to ją dodajemy.

## Etap 1: stan implementacji (2026-10-28)

Zrobione i skompilowane (bez testów uruchomieniowych, bez commitów):

| Repozytorium | Zmiana |
|---|---|
| `mercury-lib` | DTO `org.mercury.dto.view` w `mercury-core`; metody `getViewInfo`, `findViewInfos`, `readViewData` w `ICaseViewDefinitionAction` (core i SOAP); zwrotki `WsStatusWithView*` w `mercury-ws-dto-api`; klucze `openapi-docs_pl/en` operacji (`mercury-ws-server-api`) |
| `mercury` | `ICaseViewDefinitionDAO`/`CaseViewDefinitionDAO`: `findViewColumns` (JDBC `DatabaseMetaData`, jedna implementacja dla czterech baz) i `readViewData` (parametry zapytania, kolumny z metadanych, `ORDER BY`, limit czasu); `CaseViewDefinitionLogic`: reguła uprawnień, limity strony (`mercury.view.maxPageSize`, domyślnie 1000; `mercury.view.queryTimeoutMs`, domyślnie 60000); `CaseViewDefinitionAction`; klucze `schema.View*` (pl, en) w generatorze; przegenerowane `openapi*.json` (`info.version` przywrócone do 3.0.4.10) |
| `hgdb-client-open` | `CaseViewDefinitionLogic` w `hgdb-ws-client-cxf` (`hgdb-multi-client` dziedziczy) |

REST (`CaseViewDefinitionRest`, `rest` i `rest2`) i `ws-server-api20` powstają z generatorów (katalogi `generated` są w `.gitignore`). Raport `openapi-doc-report.txt`: braki opisów 0; braki tłumaczeń `pl` i `en` 0, `de`/`es`/`fr`/`ko` po 64 klucze (dla translatora Gemini).

**Uproszczenia etapu 1 (do rozstrzygnięcia w kolejnych etapach):**
- Uprawnienia tylko na poziomie typów bazowych; kolumny z pól typu, których użytkownik nie może czytać, nie są jeszcze pomijane (`typeFieldCode` jest pusty, bo nazwy kolumn widoku nie mają prostego mapowania na pola).
- `status` to `VALID`/`MISSING` (brak kolumn w katalogu); `INVALID` (Oracle), `lock_timeout` i ponowienia w PostgreSQL to etap 2. Lista widoków nie ustawia statusu.
- Brak testów jednostkowych i testu na serwerze dev; zweryfikowano tylko kompilację i generatory.
- Test na PostgreSQL, potem na Oracle, MySQL i MSSQL (etap 2).

**Do wydania:** `mercury-lib` (następny numer po 3.0.4.18), potem podbicie wersji w `mercury` i `hgdb-client-open`. Lokalnie w `~/.m2` (D:\workspace\.m2) leży testowa wersja `3.0.4.19-SNAPSHOT` (lib i `POSTGRESQL-3.0.4.19-SNAPSHOT`); wydanie ją zastąpi.

### Test DAO na trzech bazach (2026-10-28)

Program testowy (poza repozytoriami) uruchamia prawdziwe `CaseViewDefinitionDAO` na własnej tabeli `MRC_VW_TEST_T` i widoku `MRC_VW_TEST_V` (25 wierszy; obiekty usuwane na końcu) i sprawdza 18 przypadków: metadane kolumn i typy, brak widoku, stronicowanie (strony 1 i 3), sortowanie, domyślne `ORDER BY 1`, filtry `LIKE` (bez rozróżniania wielkości liter), `GE`/`LT` na liczbach i datach, `IS NULL`/`IS NOT NULL`, wartość z cudzysłowem jako parametr, odrzucenie kolumny z iniekcją SQL, nieznanej kolumny sortowania, liczby z tekstem, `LIKE` na liczbie i niedozwolonej nazwy widoku.

| Baza | Wynik | Uwagi |
|---|---|---|
| PostgreSQL (localhost) | 18/18 OK | sterownik 42.2.23 |
| Oracle 23c Free (`FREEPDB1`) | 18/18 OK | wymaga sterownika `ojdbc11` (JDK 17) i adresu usługi `//host:port/FREEPDB1`; `ojdbc6` z serwera dev kończy się `ORA-28040`; `NUMBER(10)` rozpoznawany jako INTEGER po skali 0 (poprawka w DAO) |
| MSSQL (`pluton`) | 18/18 OK | sterownik `mssql-jdbc` 8.2.2 (JRE 8), `datetime2`, `decimal`, `int` rozpoznane poprawnie; wcześniej konto wymagało zmiany hasła (zmienione przez autora) |
| MySQL 8.4 (Docker, `docker/mysql`) | 18/18 OK | sterownik Connector/J 8.0.28, dialekt `MySQL8Dialect`; typy `INT`, `DECIMAL`, `DATETIME` rozpoznane poprawnie |

Wniosek dla etapu 2: adresy `jdbc.oracle.dbSID` w plikach testowych to w rzeczywistości nazwa usługi PDB. Stary sterownik `ojdbc6` nie łączy się z Oracle 23c.

## Uprawnienia: stan zaimplementowany (aktualizacja 2026-10-28)

Sekcja „Reguła uprawnień (propozycja)” z etapu 1 jest nieaktualna. Zaimplementowano (zadanie 217, `CaseViewDefinitionLogic.readViewData`):

1. Użytkownik z `isAllRO()` widzi wszystko.
2. Pozostali widzą definicję, gdy mogą czytać choć jeden typ widoku (przy `baseTypeCodes` jeden z nich).
3. Wiersze typów bez prawa odczytu są pomijane (filtr `type_code IN (…)` w SQL, więc licznik i stronicowanie są poprawne). Widok bez kolumny `TYPE_CODE` jest dla takich użytkowników niedostępny.
4. Wartości pól bez prawa odczytu (typ, nazwa pola, pozycja `parameter_N`) są zastępowane maską `###########`. Kolumny pól spraw zależnych są maskowane we wszystkich wierszach, gdy użytkownik nie czyta ich w żadnym typie (przybliżenie).
5. Zarządzanie definicjami i generowanie widoków wymaga `isAllRO()` (`checkManagePrivileges`).

## Etap 2: stan implementacji (2026-10-28)

| Element | Zmiana | Weryfikacja |
|---|---|---|
| Status widoku | `ICaseViewDefinitionDAO.findViewStatus`: istnienie z `DatabaseMetaData.getTables`, poprawność próbnym zapytaniem `SELECT … WHERE 1 = 0` w punkcie zapisu (jedna implementacja na cztery bazy; Oracle rekompiluje nieważny widok przy użyciu). `getViewInfo` i `findViewInfos` ustawiają `VALID`/`INVALID`/`MISSING`. | Test DAO na czterech bazach, w tym `INVALID` po usunięciu tabeli bazowej (MySQL, MSSQL, Oracle; PostgreSQL nie pozwala usunąć tabeli z zależnym widokiem); REST na dev |
| Stabilna kolejność kolumn | `CaseViewQueryBuilder.withColumnOrder`: kolumny pól, które już są w widoku, zachowują miejsca, nowe są dopisywane na końcu alfabetycznie (wymóg `CREATE OR REPLACE VIEW` w PostgreSQL) | 4 testy jednostkowe `CaseViewQueryBuilderColumnOrderTest` |
| Zmiana widoku w miejscu | `generateView` z `force` próbuje `CREATE OR REPLACE VIEW` (MSSQL: `CREATE OR ALTER VIEW`). Widok nie znika, więc nie ma okna niedostępności i zależne widoki nie są dotknięte. Dopiero gdy baza odrzuci zmianę (PostgreSQL `42P16`: zmiana lub usunięcie dotychczasowych kolumn), jest `DROP` i `CREATE`. | Test DAO na czterech bazach; REST: dopisanie pola nie zmienia `oid` widoku |
| Widoki zależne (PostgreSQL) | Przed `DROP` zapytanie do `pg_depend`/`pg_rewrite`. Gdy coś zależy od widoku, zamiast surowego błędu bazy jest komunikat z listą zależnych widoków. Pozostałe bazy pozwalają usunąć taki widok. | Test DAO i REST (zależny widok `mrc_dep016`) |
| `lock_timeout` i ponowienia | PostgreSQL: `SET LOCAL lock_timeout` (poza transakcją `SET` i `RESET`), po jego przekroczeniu (`55P03`) ponawianie z narastającym opóźnieniem, potem czytelny błąd. Parametry `mercury.view.lockTimeoutMs` (domyślnie 5000) i `mercury.view.ddlRetries` (domyślnie 3). Polecenie DDL w punkcie zapisu, żeby błąd nie unieważnił transakcji. | Test DAO: zajęta blokada kończy się komunikatem po 1142 ms (300 + 500 + 300 ms) |
| Widoczność błędu generowania | `ViewInfo.generationError` (nowe pole w `mercury-lib`, nie jest duplikatem `errorMessage` zwrotki: ta opisuje wynik wywołania, a pole stan widoku). Generowanie jest asynchroniczne (JMS), więc `CaseViewCreatorReceiver` zapisuje niepowodzenie w definicji (`MODIFY_COMMENT` z prefiksem, osobna transakcja `REQUIRES_NEW`, bez zmiany schematu bazy), a udane generowanie je czyści. Pętla po typach nie przerywa się na jednym błędzie. | REST na PostgreSQL: zależny widok, niezgodna zmiana, `generationError` w `getViewInfo` i `findViewInfos`, widok bez zmian, po usunięciu zależnego widoku generowanie się udaje i błąd znika |
| OpenAPI | klucz `schema.ViewInfo.generationError` w `pl` i `en`; `de`/`es`/`fr`/`ko` brakuje po 65 kluczy (translator Gemini) | |

Zmienione pliki: `mercury-lib` (`ViewInfo`, `ICaseViewDefinitionLogic.markGenerationFailed`), `mercury` (`CaseViewQueryBuilder`, `ICaseViewDefinitionDAO`, `CaseViewDefinitionDAO`, `CaseViewDefinitionLogic`, `CaseViewCreatorReceiver`, klucze OpenAPI, test buildera). Wymaga wydania `mercury-lib`.

**Ograniczenia i uwagi**
- Komunikat błędu zawiera prefiks „To jest błąd aplikacji.” z `InternalErrorException`.
- Zależne widoki w Oracle, MySQL i MSSQL nie są wykrywane (baza pozwala usunąć widok); ich status po przebudowie pokaże `INVALID`, jeśli kolumny zniknęły. Zachowanie przy zależnych widokach na tych bazach wynika z wiedzy o bazach, nie z testu.
- `mercury.view.lockTimeoutMs`/`ddlRetries` dotyczą tylko PostgreSQL.
- Przebudowa atomowa z odtworzeniem zależnych widoków w PostgreSQL (`pg_get_viewdef`, jedna transakcja) została świadomie odłożona.

### Kody pól w kolumnach i wspólne źródło nazw kolumn (2026-10-28)

- `CaseViewQueryBuilder.ColumnSource` i `getColumnSources()`: builder jako jedyny wylicza nazwy kolumn pól i zwraca dla każdej kolumny źródło (typ, nazwa pola z definicji, pozycja `parameter_N`, sprawa główna czy zależna, kod pola).
- `ViewColumnDefinition.typeFieldCode` jest wypełniane w `getViewInfo` i `readViewData`: nazwa pola typu (np. `addressGroupId`), a dla sprawy zależnej `<pole sprawy zależnej>.<pole>`. Kolumny `m_id`, `type_code` i `M_*` zostają bez kodu.
- Maskowanie pól korzysta z tych samych źródeł, więc zniknęła druga kopia logiki nazewnictwa kolumn w `CaseViewDefinitionLogic`. Dla użytkownika z ograniczeniami błąd wyliczenia źródeł przerywa odczyt (inaczej wartości nie zostałyby zamaskowane); dla metadanych błąd jest tolerowany.
- Testy: `CaseViewQueryBuilderColumnSourcesTest` (5 testów: sprawa główna, to samo pole w wielu typach, sprawa zależna, pole na wielu pozycjach, przebudowa) i `CaseViewQueryBuilderColumnOrderTest` (4 testy). Test na serwerze dev: trzej użytkownicy testowi reprezentowani przez `admin` (`mrc-useradmin`): odczyt jednego typu z maską w polu `street`, odczyt obu typów bez maski, brak uprawnień (lista widoków pusta, odmowa); `typeFieldCode` poprawne. Dane testowe i użytkowników usunięto.

### Dokumentacja (2026-10-28)

Nowy artykuł „Widoki” / „Views” w `docusaurus-hgdb`: `docs/004_API/011_Views.mdx` i wersja PL w `i18n/pl/…/004_API/011_Views.mdx`: definicja i kolumny widoku, operacje i uprawnienia, `ViewInfo` i status, odczyt z filtrami i sortowaniem, uprawnienia (filtr wierszy i maskowanie), generowanie i zmiana widoków (zmiana w miejscu, zależne widoki, `lock_timeout`).

**Do zrobienia w etapie 2:** test na kopii bazy z widokami zależnymi od innych widoków (wymóg Definicji Gotowości; zależne widoki sprawdzono tylko w PostgreSQL na widoku testowym), a po wydaniu `mercury-lib` tłumaczenia kluczy OpenAPI (de/es/fr/ko).

## Partycjonowanie `igo_da_cases` a widoki (dyskusja 2026-10-28)

Skrypty `mercury/db/postgresql/01…05` budują partycjonowaną tablicę `igo_da_cases`. Poniżej ustalenia, pomiary i otwarte decyzje.

### Założenia autora

- Identyfikator sprawy jest tekstem (`<kod typu>.<numer>`, zadanie 169) **celowo**, żeby mógł być kluczem partycjonowania. Partycjonowanie z id liczbowym nie wchodzi w grę, więc w środowiskach partycjonowanych nie ma id liczbowych.
- Widoki nie są wielotypowe: mają wiele wersji typu, ale wszystkie typy w widoku mają ten sam kod.
- Cel Mercury: baza spraw dla procesów bez migracji przy zmianie modelu. Stare wiersze zostają pod starym typem (szczegóły i czyściciel: zadanie 218).

### Jak działa partycjonowanie (skrypty 01 i 02)

- `PARTITION BY RANGE(id)` na kolumnie `varchar`. Klucz partycjonowania jest kluczem głównym, więc `PRIMARY KEY (id)` i siedem kluczy obcych do `igo_da_cases(id)` (skrypt 01) pozostają poprawne. Partycjonowanie po `type_code` (`LIST`) wymusiłoby złożony klucz i rozbiło te klucze obce.
- Trigger `BEFORE INSERT` na `igo_da_typecode` tworzy partycję na kod typu z granicami `FROM lower(unaccent(kod)) || '.0' TO upper(kod) || '.Z'` i zapisuje nazwę w `igo_da_typecode.partition_name`. Jest też partycja domyślna.
- Tylko PostgreSQL (w `db/oracle` i `db/mysql` nie ma takich skryptów). Baza dev **nie jest** partycjonowana, więc pomiary zrobiono na schemacie zastępczym.
- Skrypt 01 jest destrukcyjny (`DROP TABLE … CASCADE` i `DELETE` w ośmiu tabelach): tylko dla świeżych instalacji, ścieżki migracji istniejącej bazy nie ma.

### Pomiary (PostgreSQL 13, schemat zastępczy, 305 partycji, 800 000 wierszy)

| Warunek w zapytaniu widoku | Partycje w planie | Planowanie | Wykonanie |
|---|---|---|---|
| tylko `case_type_id = ANY(…)` (jak widok dziś) | 305 | ok. 160 ms | 5–6 ms |
| + zakres `id >= 'ty7.0' AND id < 'TY7.Z'` (granice partycji) | 1 | 0,1–0,35 ms | ok. 2 ms |
| zakres z `OR` dla dwóch typów | 2 | | |
| `id LIKE 'Typ.%'` | wszystkie | | |
| `type_code = '…'` | wszystkie | | |

- Koszt to głównie planowanie i rośnie z liczbą partycji. `readViewData` robi dwa zapytania na stronę (`COUNT` i dane).
- Przycinanie działa tylko dla stałych granic na kluczu `id` (także z `OR`). Partycja domyślna też jest przycinana. Zakres obejmował dokładnie wiersze typu (2000 z 2000, 0 obcych).

### Zastrzeżenia

1. Granice zależą od collation: w `"C"` baza odrzuca partycję (`empty range bound specified`). W Windows PL i ICU kody `slm` i `slmaddress` się nie nakładają, innych collation nie testowano. Skrypt miesza `lower(unaccent(kod))` z `upper(kod)`.
2. Indeksy z rodzica trafiają do wszystkich partycji (16 indeksów `parameter_N` w skrypcie 01), nawet gdy typ tych pól nie używa.
3. Partycja powstaje w triggerze (DDL w `BEFORE INSERT`). Zgodnie z dokumentacją PostgreSQL utworzenie partycji kończy się błędem, jeśli w partycji domyślnej są wiersze z jej zakresu (nie testowano).
4. Założenie „prefiks id = kod typu wiersza” jest spełnione dla każdego wiersza (id nowej wersji powstaje z kodu jej typu). Wyjątek to `changeModel` przenoszący sprawy do typu o innym kodzie: robi `UPDATE case_type_id` bez zmiany id, a DAO nie sprawdza zgodności kodów.

### Plan (czeka na zatwierdzenie autora, tylko `mercury`)

1. DAO: odczyt granic partycji z katalogu (`pg_get_expr(relpartbound)`) dla kodów typów, gdy `igo_da_cases` jest partycjonowana (`pg_partitioned_table`); dla innych baz i tablic niepartycjonowanych pusty wynik (bez zmiany zachowania).
2. `CaseViewQueryBuilder`: `AND (alias.id >= 'od' AND alias.id < 'do')` dla aliasu sprawy głównej i spraw zależnych (każda ma własny kod), z granicami z zewnątrz; testy jednostkowe.
3. Logika: pobranie granic i zabezpieczenie przed zbudowaniem zapytania: jeśli istnieją wiersze tych `case_type_id` poza zakresem, warunku nie dodawać i zapisać ostrzeżenie w `generationError`.
4. Testy: odczyt granic i plan zapytania na schemacie zastępczym (nazwa `igo_da_cases` w schemacie testowym i `search_path`). Pełny test przez serwer wymaga bazy z partycjonowaną `igo_da_cases` (na dev nie uruchamiać skryptu 01).

Opcjonalnie: walidacja w `changeModel`, że oba typy mają ten sam kod.

### Rozstrzygnięcie (2026-10-28): stare wiersze przeniesionych spraw w widoku

Decyzja autora: stare sprawy zostają tam, gdzie były, i są w widokach. Problem rozwiązuje czyściciel (zadanie 218). Widok nie dostaje warunku na wersję ani status. Poniżej opis, na czym polega sytuacja.

Wygenerowany widok nie ma warunku na status ani wersję (`WHERE 1=1 AND case_type_id = ANY(…)`). Widok dla kodu typu obejmuje wszystkie wersje typu, więc po zapisie zmieniającym typ sprawy w widoku są dwa wiersze: stary (stara wersja typu, `Z`) i nowy (`A`). Dotyczy to wyłącznie spraw przeniesionych tą ścieżką. Zwykła edycja nie tworzy wierszy. Warianty: bez zmian, anti-join po `piervous_version_id` (istniejący indeks `IGO_DA_CASE_VERSION_INDX`) albo join po `igo_da_case_roots.last_version`. `status <> 'Z'` odradzam. Kryterium proponowane: zgodność z tym, co zwraca wyszukiwanie (do sprawdzenia w indeksowaniu). Czyściciel (zadanie 218) zmniejsza liczbę takich wierszy w czasie, ale decyzji o widoku nie zastępuje.

### Zakres `id` w widoku: stan implementacji (2026-10-28)

Zrealizowano plan z punktów 1–4. Warunek powstaje **tylko wtedy, gdy `igo_da_cases` jest partycjonowana** i typ ma partycję. W pozostałych przypadkach (inna baza, tablica niepartycjonowana, typ bez partycji, błąd odczytu) widok jest taki jak dotąd.

| Element | Zmiana |
|---|---|
| `ICaseViewDefinitionDAO.findPartitionBounds` | Dla kodów typów odczyt granic partycji z katalogu PostgreSQL (`igo_da_typecode.partition_name`, `pg_class`, `pg_inherits`, `pg_get_expr(relpartbound)`), tylko PostgreSQL od wersji 10. Błąd odczytu daje pusty wynik (w punkcie zapisu, żeby nie unieważnić transakcji). |
| `ICaseViewDefinitionDAO.countCasesOutsideRange` | Liczba spraw podanych typów z `id` poza zakresem partycji. |
| `CaseViewQueryBuilder.withPartitionBounds` | Dla aliasu sprawy głównej i każdej sprawy zależnej dopisuje `AND ((alias.ID >= 'od' AND alias.ID < 'do') [OR …])`, ale tylko gdy granice są znane dla wszystkich kodów typów aliasu (inaczej zakres pominąłby sprawy tego kodu). Wartości są cytowane. |
| `CaseViewDefinitionLogic.generateView` | Pobiera granice i pomija kod typu, dla którego istnieją sprawy poza zakresem (np. po `changeModel` do typu o innym kodzie): takie zdarzenie jest zapisywane w dzienniku serwera (`WARN`). |

**Odstępstwo od planu:** ostrzeżenie o sprawach poza zakresem trafia do dziennika serwera, a nie do `generationError`, bo generowanie się udaje (widok jest poprawny, tylko czyta wszystkie partycje), a udane generowanie czyści `generationError`.

**Weryfikacja**
- 8 testów jednostkowych `CaseViewQueryBuilderPartitionTest` (brak granic, jeden kod z wieloma wersjami typu, granice innego kodu, kod bez granic, `OR` dla wielu kodów, własny zakres sprawy zależnej, cytowanie apostrofów), razem z poprzednimi 17 testami buildera.
- Test DAO: na PostgreSQL ze schematem zastępczym z partycjonowaną `igo_da_cases` (granice odczytane z katalogu, wykrycie sprawy z innym prefiksem), a na PostgreSQL bez partycjonowania, MySQL, MSSQL i Oracle wynik pusty.
- Prawdziwe zapytanie z buildera na replice z 300 partycjami i 600 000 wierszami: bez granic 301 partycji w planie i 167 ms planowania, z granicami 1 partycja i 0,46 ms, wynik taki sam (2000 wierszy).
- Serwer dev (niepartycjonowany): `generateView` i odczyt działają, widok nie ma zakresu `id`.
- Nie przetestowano generowania widoku przez serwer na prawdziwie partycjonowanej bazie (potrzebna baza z zastosowanymi skryptami `db/postgresql/01…05`).

## Etap 3: przegląd (2026-10-28)

Przegląd bez zmian w kodzie: `poi-toolkit` (model `IExcelData`) i istniejący w `mercury` eksport do Excela.

### Model Excel (`poi-toolkit`, `org.iron.poi.excel.core`)

| Element | Opis |
|---|---|
| `IExcelData` | `getResult()`, `getResult(ExcelPage)`, `getMessage()`, `getResultSize()`, informacje o stronach (bieżąca, pierwsza, poprzednia, następna, ostatnia), `getHeader()` (`Map<Integer, String>`), `getColumnTypes()` (`Map<Integer, String>`) |
| `ExcelRow` | numer wiersza i `Map<Integer, ExcelColumnValue>` (numer kolumny → komórka) |
| `ExcelColumnValue` | tekst `value` i `searchValue` |
| `ExcelPage` | rozmiar, numer strony, numer pierwszego i ostatniego wiersza |
| `ExcelData` | implementacja czytająca plik Excela |
| `ExcelFileWriterData` | implementacja do zapisu: nagłówek, komunikat, liczba wyników, pierwsza i ostatnia strona, typy kolumn, `setResult(strona, wiersze)` |

### Gdzie `mercury` już używa `IExcelData`

1. **Zwracanie przez RMI:** `ICaseSearcherRMI.fieldMetricQuery` i `dateMetricQuery` (agregacje Lucene). Adaptery w `mercury-lucene-indexes` (`org.mercury.lucene.search.poi`): `ExcelRowPagedResultExcelData(PagedResultSupport<ExcelRow>, PoiHeaderData)` i `DocDateValueHitsExcelData`. `ICaseSearcherRMI` jest jedynym interfejsem RMI poza transferem plików (`remoting-servlet.xml`).
2. **Eksport asynchroniczny do pliku:** REST `ReportExportStatusRest` → `ReportExportStatusLogicHelper.prepareReportRequest` (wymaga `USER_NAME`, `REPORT_NAME` = kod typu, `SUBJECT`, `FILE_NAME`, `DATE_FROM`, `DATE_TO`; opcjonalnie `CASE_STATUS`, `SKIP_HEADER`, `LUCENE_QUERY`) tworzy `ReportExportStatus` (zapisuje `userName` i `userRoles`, `PARAMS` jako URL query) → wątek `ReportExportSecretary` → `ExportGenerator.generateReport`:
   - nagłówek i typy kolumn z `poiServerWriter.createHeader` (`ReportHeaderData`; typy to nazwy `SimpleJavaType`: np. `STRING`, `LONG`, `DOUBLE`, `DATE`),
   - dane: zapytanie Lucene o sprawy stronami (`EXPORT_DEFAULT_PAGE_SIZE` = 1000), konwersja strony przez `PoiServerWriter.convertCollectionByStream` do `ExcelRow` (wartość `NULL` oznacza brak komórki, pola parametrów przechodzą przez `AttributeParser…getClientPresentation`),
   - zapis stron `ExcelFileWriterData` przez RMI do serwera Iron POI (`IWriteRemote`: `write`, `beginTransaction`, kolejne `write`, `commitTransaction` albo `rollbackTransaction`),
   - postęp w `GENERATOR_PROGRESS_MAP`.

### Wnioski dla widoków

- **Mapowanie `ViewDataPage` → `IExcelData`** jest proste: kolumny widoku dostają numery od pierwszej kolumny danych, nazwy trafiają do nagłówka, `mercuryType` mapuje się na `SimpleJavaType` (`STRING`→`STRING`, `INTEGER`→`LONG`, `DECIMAL`→`DOUBLE`, `DATE`→`DATE`, `OTHER`→`STRING`, `BOOLEAN` do ustalenia), wiersze to `ExcelRow` z `ExcelColumnValue(tekst, null)`, a stronicowanie ma już `ViewDataPage`. Do zwracania `IExcelData` wystarczy istniejący adapter `ExcelRowPagedResultExcelData`, do zapisu `ExcelFileWriterData`. Nowej implementacji `IExcelData` nie trzeba pisać.
- **Eksport (etap 4)** to gałąź w `ExportGenerator` dla widoku: raport z `REPORT_NAME` = nazwa widoku i znacznikiem źródła, pętla stron po `readViewData` zamiast zapytania Lucene, nagłówek z kolumn widoku. `prepareReportRequest` wymaga dziś `DATE_FROM` i `DATE_TO`, więc dla widoku trzeba je uczynić opcjonalnymi.
- **Uprawnienia przy eksporcie:** raport zapisuje `userName` i `userRoles` z żądania REST (które przechodzi weryfikację kontekstu z zadania 217). `ExportGenerator` buduje kontekst z raportu, więc `readViewData` zastosuje filtr wierszy i maskowanie. Do sprawdzenia, czy kontekst z raportu faktycznie niesie role.

### Otwarte pytania do autora

1. **Wartości w Excelu:** surowy tekst z widoku czy prezentacja kliencka jak w eksporcie spraw (`AttributeParser`, daty w formacie użytkownika, słowniki)? Kolumny pól widoku są tekstowe i zawierają wartości zakodowane w bazie, więc bez dekodowania Excel pokaże surowe wartości. `typeFieldCode` pozwala dojść do atrybutu pola, ale typ atrybutu może się różnić między wersjami typu.
2. **Którędy zwracać `IExcelData` dla widoku:** `ICaseSearcherRMI` jest wyspecjalizowany w wyszukiwaniu. Czy dodajemy metodę tam, nowy interfejs RMI, czy ograniczamy się na razie do eksportu (etap 4)? REST zwraca JSON, więc `IExcelData` dotyczy tylko RMI.
3. **Gdzie umieścić `ViewQuery` (filtry, sortowanie) w `ReportExportStatus`** bez zmiany schematu: w `PARAMS` (długość kolumny do sprawdzenia) czy w `LUCENE_QUERY` (semantyka pola jest inna).
4. **Środowisko testowe:** eksport wymaga serwera Iron POI (`IWriteRemote`). Nie sprawdzałem, czy jest dostępny razem z serwerem dev.

## Stan na koniec dnia 2026-10-28

| Obszar | Stan |
|---|---|
| Etap 1 (odczyt widoków) | zamknięty, test na czterech bazach |
| Uprawnienia widoków | zamknięte (filtr wierszy, maskowanie, kontrola zarządzania), zadanie 217 |
| Etap 2 | status `VALID`/`INVALID`/`MISSING`, stabilna kolejność kolumn, zmiana widoku w miejscu, zależne widoki w PostgreSQL, `lock_timeout` i ponowienia, `generationError`, `typeFieldCode`, zakres `id` dla tablicy partycjonowanej; dokumentacja „Widoki” (EN i PL) |
| Etap 2, zostaje | test na kopii bazy z widokami zależnymi od innych widoków; test generowania na partycjonowanej bazie; tłumaczenia kluczy OpenAPI (de/es/fr/ko, po 65 kluczy) |
| Etap 3 | przegląd wykonany (wyżej), implementacja po decyzjach z pytań |
| 217 | kod zamknięty dla REST; do rozstrzygnięcia: zewnętrzni klienci REST z własnym `context`, cache ról, SOAP i RMI/CMIS, mapowanie ról procesowych w środowiskach |
| 218 | zadanie założone (czyściciel starych wersji), czeka na decyzje |
| Wydanie | `mercury-lib` wymaga wydania (nowe DTO, zmiany interfejsów), potem podbicie wersji w `mercury` i `hgdb-client-open` |

**Na jutro:** (1) decyzje z pytań etapu 3 (szczególnie pkt 1 i 2), (2) implementacja etapu 3, (3) dokończenie etapu 2 (test na kopii bazy, jeśli będzie dostępna), (4) decyzje do zadania 218.

## Etap 3: decyzje autora (2026-10-29)

1. **Wartości w Excelu: dekodowanie jak w ogólnym eksporcie.** Wartość pola z widoku przechodzi przez `AttributeParser.createAttributeValueFromDbValue(...)` i `getClientPresentation(context)` na podstawie definicji pola (`TypeParam` → `AttributeTypeParameter`, `arg3`, `hasMultiValues`) typu wiersza (`type_code`) i nazwy pola (`typeFieldCode`). Wyjątek: pola LOB (pliki). Typ kolumny w Excelu (`DATE`, `DOUBLE`, `LONG`, `STRING`) wynika z typu atrybutu; gdy typy spraw różnią się dla tej samej nazwy pola, kolumna jest tekstowa (propozycja).
2. **Dwa tory prezentacji:**
   - **eksport asynchroniczny** do pliku przez istniejący `ExportGenerator` i serwer Iron POI, z adresem pobrania pliku w `ReportExportStatus.DOWNLOAD_URL`,
   - **stronicowany wynik `IExcelData`** tak jak robi to prezentacja z POI (wzorzec: `CaseSearchExtRest.fieldMetricQuery`, czyli `IExcelData` → `DataUtils.transform2Data` → JSON). Przyda się przyszłym podglądom przed eksportem.
3. **Zapytanie o widok w eksporcie: w `PARAMS`** (decyzja zależna od długości kolumny, zobacz niżej).
4. Serwer Iron POI działa na dev (`mercury-server/poi-toolkit-server`, porty 10090 i 10099), więc eksport do pliku da się przetestować.

### Ustalenia z przeglądu kodu (2026-10-29)

| Fakt | Źródło |
|---|---|
| Ogólny eksport dekoduje wartość pola przez `AttributeParser` według definicji pola typu, a typ kolumny Excela z `MPoiServerSupport.createHeader` według `AttributeType` | `PoiServerWriter.convertCase`, `MPoiServerSupport.createHeader` |
| Długie wartości (powyżej 4000 znaków, przechowywane w LOB) rozwiązuje `AttributeParser` (`checkValueStoredAsLOB`); inaczej traktowany jest atrybut typu `AttributeType.LOB` (plik) | `AttributeParser` |
| REST zwraca `IExcelData` jako JSON `Data` przez `DataUtils.transform2Data` | `CaseSearchExtRest.fieldMetricQuery` |
| `ICaseSearcherRMI` to wewnętrzna usługa klastra w `mercury` (`hgdb-rmi-server-api`), nie w `mercury-lib` | `ICaseSearcherRMI` |
| Interfejs odczytu widoków (`readViewData`) jest w `mercury-lib` (`ICaseViewDefinitionAction`), a REST jest generowany do `mercury-ws-app/src/main/generated` | |
| `ReportExportStatus` ma `DOWNLOAD_URL` na adres pobrania pliku | `ReportExportStatus` |

### Problem: `PARAMS` ma tylko 255 znaków

`igo_da_report_exps.PARAMS` (i `igo_da_report_imps.PARAMS`) to `varchar(255)`, podobnie `DOWNLOAD_URL`. Zapytanie o widok z filtrami i sortowaniem w postaci tekstowej (URL query albo JSON) szybko przekroczy ten limit. Opcje do decyzji autora:

| Opcja | Skutek |
|---|---|
| A. Poszerzyć `PARAMS` w `igo_da_report_exps` do 4000 | zmiana schematu na czterech bazach (skrypty w `mercury/db/<baza>`), zmiana encji w `mercury-lib` i wydanie; najprostsze dla eksportu |
| B. Zostawić `PARAMS` i trzymać tam tylko nazwę widoku oraz odwołanie do zapisanego zapytania | zapytanie musi być gdzieś zapisane (nowa tabela albo wykorzystanie mechanizmu LOB), więcej kodu |
| C. Ograniczyć eksport widoku do zapytań, które mieszczą się w 255 znakach | tanie, ale rzeczywiste filtry się nie zmieszczą |

### Etap 3: stan implementacji (2026-10-29, gałąź `hgdb-016`, tylko `mercury`, bez zmian w `mercury-lib`)

Decyzja o `PARAMS`: opcja B z prefiksem. Pole `PARAMS` raportu eksportu widoku zawiera `[VIEW]vName=<nazwa widoku>&file=…&…` (tylko nazwa widoku, bez filtrów; zgodne z limitem 255 znaków), a `REPORT_NAME` to nazwa widoku. Eksport obejmuje więc cały widok w zakresie uprawnień użytkownika z raportu. Filtry i sortowanie ma podgląd stronicowany.

| Element | Zmiana |
|---|---|
| `ReportServerAppConstants.ReportGeneratorParams` | `VIEW_NAME` (`vName`), `VIEW_PARAMS_PREFIX` (`[VIEW]`) |
| `ReportExportStatusLogicHelper.prepareReportRequest` | żądanie z `vName` to eksport widoku: `REPORT_NAME` = nazwa widoku, `PARAMS` z prefiksem, bez wymagania zakresu dat, statusu i zapytania Lucene (kryteria spraw przeniesione do `appendCaseCriteria`) |
| `ReportExportStatusRest.prepareReportRequest` | nowe pole żądania `viewName` (zamiast `typeCode`), domyślna nazwa pliku `<widok>.xlsx` |
| `ViewExportHeader` (nowa, `org.mercury.business.reports.internal.api`) | nagłówek widoku w modelu POI: kolumny widoku, indeks kolumny `type_code`, pamięć podręczna metadanych pól typów |
| `MPoiServerSupport` | wspólne `createCaseMetadata(TypeParam)` i `simpleTypeOf(AttributeType)` (wydzielone z `createHeader`, używa ich eksport spraw i widoków) |
| `IPoiServerWriter` / `PoiServerWriter` | `createViewHeader` (typ kolumny z typu atrybutu pola w typach widoku, przy różnych typach tekst; kolumny inne niż pola z typu kolumny w bazie) i `convertViewPage` (strona widoku → `ExcelFileWriterData`, dekodowanie wartości przez `AttributeParser` według pola typu wiersza, maska `###########`, brak definicji pola i pola LOB bez zmian) |
| `ExportGenerator` | gałąź `[VIEW]`: strony `readViewData` → `convertViewPage` → zapis w jednej transakcji serwera POI; wspólna `createWriterProperties` |
| `org.mercury.rest.server.actions.view` (nowe: `CaseViewExtRest`, `ICaseViewExtRest`, `CaseViewExtRestRequests`) | `POST /rest/service/CaseViewExtRest/readViewExcelData` zwraca stronę wyniku widoku jako JSON `Data` (jak `fieldMetricQuery`), z filtrami, sortowaniem i stronicowaniem; klucze OpenAPI `pl` i `en` dopisane, `de/es/fr/ko` czekają na translator |
| Testy | `ViewExportReportRequestTest` (6 testów: prefiks i `PARAMS`, brak wymogu dat, nazwa widoku ma pierwszeństwo, eksport spraw bez zmian, nagłówek) |

Do sprawdzenia na dev (po zbudowaniu i wdrożeniu): podgląd REST, eksport do pliku przez serwer POI (adres pobrania w `DOWNLOAD_URL`), uprawnienia i maskowanie w pliku, widok z typami o różnych typach pola. Dokumentacja w `docusaurus-hgdb` i tłumaczenia kluczy `de/es/fr/ko` po sprawdzeniu.

### Etap 3: weryfikacja na dev (2026-10-29)

Środowisko: dev Tomcat z nowym buildem, serwer Iron POI z `mercury-server/poi-toolkit-server`, widok `Vw016Slm` nad typami `SlmAddress` i `SlmAppMobileDetails` (po 100 000 spraw), użytkownicy z rolami procesowymi (wiersze `U`). Dane testowe usunięto po teście (zostały dwa pliki xlsx otwarte w Excelu, do ręcznego usunięcia).

| Przypadek | Wynik |
|---|---|
| Podgląd `readViewExcelData` jako `admin` | nagłówek (`m_id`, `type_code`, pola), typy kolumn, `FRAGMENT`, ostatnia strona 33334 przy `pageSize=3`, numeracja wierszy ciągła między stronami, komórki pól niedotyczących typu puste |
| Podgląd, rola `vw016-addr` | tylko `SlmAddress`, `street` jako `###########`; `SlmAppMobileDetails`: `NO_DATA_FOUND` |
| Podgląd, rola `vw016-both` | oba typy, pola z uprawnieniami jawnie |
| Podgląd, rola `vw016-none` | odmowa (`You do not have sufficient privileges`) |
| Eksport do pliku, `tester` z rolą `vw016-addr` | `COMPLETED`, plik 100 001 wierszy (tylko `SlmAddress`), `street` zamaskowane, nagłówek bez dodatkowej kolumny |
| Eksport do pliku, `admin` | `COMPLETED` (ok. 15 minut przy 200 000 wierszach z dekodowaniem), plik 200 001 wierszy, oba typy, brak zamaskowanych komórek, adres pobrania `https://localhost:10090/load?...&efn=<plik>` |
| `PARAMS` raportu | `[VIEW]vName=Vw016Slm&file=...&ps=1000` (w limicie 255 znaków) |
| `ps` większe niż `mercury.view.maxPageSize` (1000) | eksport kończy się błędem walidacji `Rozmiar strony musi mieścić się w przedziale 1-1000` |

Poprawki wynikłe z testu: `PoiServerLoader.createContext` tworzy użytkownika raportu przez `IModifyInfoHelper.getOrCreateUser`, w eksporcie widoku ostatnia kolumna to `dfc + headerSize - 1`, katalog danych POI w `mercury.properties` dev wskazuje na `poi-toolkit-server`, a adres pobrania w `DOWNLOAD_URL` bierze się z `excel.server.docUrl` (https). Obserwacje 114–116.

Nie sprawdzono: wartości z typami innymi niż tekst (daty, liczby, słowniki z nazwami) w pliku, bo typy testowe mają tylko pola tekstowe; widoku z typami o różnych typach tego samego pola; pól LOB. Zostaje też dokumentacja w `docusaurus-hgdb` i tłumaczenia kluczy OpenAPI `de/es/fr/ko`.

## Zamknięcie zadania (2026-10-29)

### Tłumaczenia kluczy OpenAPI (wykonane przez translator Gemini)

70 kluczy (usługa `ICaseViewDefinitionAction` 11, usługa `ICaseViewExtRest` 5, schematy `schema.View*` i `schema.WsStatusWithView*` 54) dopisano do katalogów `openapi-docs_{de,es,fr,ko}.properties` w trzech miejscach: `mercury-lib/mercury-ws-server-api`, `mercury/mercury-ws-app` i `mercury/mercury-ws-app-rest-generator`. Walidacja (`localizer.py validate`) bez błędów, przegląd niemieckiego (`review`) wykonany. Uwaga na proces: `openapi_docs_sync.py` tłumaczy z krótkich fragmentów generatora (`pl`), które są uboższe niż teksty `en` w katalogach. Pierwszy przebieg dał tłumaczenia wymagające 26 poprawek w przeglądzie niemieckiego, dlatego 70 kluczy przetłumaczono ponownie z `en` (po tym przegląd poprawił 1 klucz). Opisy parametrów w niemieckim zaczynają się dużą literą rzeczownika (poprawione po przeglądzie).

### Kolejność rytuału wydań (do wykonania przez autora)

| Krok | Repozytorium | Działanie |
|---|---|---|
| 1 | `mercury-lib` (gałąź `hgdb-016`) | commit katalogów tłumaczeń, wydanie biblioteki (ostatni znacznik 3.0.4.18, testowo używano 3.0.4.19-SNAPSHOT, więc kolejna to 3.0.4.19) |
| 2 | `mercury` (gałąź `hgdb-016`) | podniesienie `mercury.static.version` w głównym `pom.xml` do wydanej wersji lib, przebudowa `mercury-ws-app` (generator zapisze `openapi*.json` z tłumaczeniami), commit katalogów tłumaczeń i `openapi*.json`, testy |
| 3 | `hgdb-client-open` | podniesienie zależności od `mercury-lib` i wydanie (nowe DTO widoków w kliencie), jeśli klient ma je udostępniać |
| 4 | `mercury-cmd` | podniesienie wersji zależności (wydana lib i klient), jeśli narzędzia ich używają |
| 5 | `docusaurus-hgdb` | commit artykułów „Widoki”, „Permissions mechanism”, „Integracja z LDAP” (EN i PL) i `tags.yml` |
| 6 | wszystkie powyższe + workspace | push gałęzi `hgdb-016`, PR i merge, `pull` na `master`/`main`, dopiero potem nowa gałąź |

`sccommon` 2.0.0.2 (poprawka `SecurityPassword`) jest już wydany, a wersja w `mercury`, `mercury-lib`, `hgdb-client-open` i `mercury-cmd` podniesiona. `mercury-client` zamrożony i pomijany.

### Luki względem Definicji Gotowości (do potwierdzenia przez autora: zamknięcie ze znanymi lukami albo ich domknięcie przed zamknięciem)

- Nie wykonano testu generowania widoków na kopii bazy z widokami zależnymi od innych widoków (`INVALID`, lock w PostgreSQL) ani na bazie z partycjonowaną tablicą `igo_da_cases`.
- Etap 3 (podgląd i eksport) sprawdzono tylko na PostgreSQL. Dekodowania pól daty, liczby i słownika w pliku Excel nie sprawdzono w praktyce (typy testowe mają tylko pola tekstowe), pól LOB także.
- Eksport 200 000 wierszy trwał ok. 15,5 min: analiza wydajności w zadaniu 219.
- Eksport widoku obejmuje cały widok (bez filtrów i sortowania), zgodnie z decyzją o `PARAMS`; filtry ma podgląd.
