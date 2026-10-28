# [16] Widoki

**Status (2026-10-28):** 058 i 214 zamknięte; etap 0 w toku (rozpoznanie w sekcji „Wyniki rozpoznania etapu 0”). Kolejność autora: 016, 049, 191. Plan: `plan-najblizszych-dzialan-2026-10-26.md`

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

**Do zrobienia w etapie 2:** `typeFieldCode` w kolumnach (mapowanie kolumna → pole typu ze wspólnego kodu maskowania i `CaseViewQueryBuilder`), test na kopii bazy z widokami zależnymi od innych widoków, dokumentacja w `docusaurus-hgdb`.
