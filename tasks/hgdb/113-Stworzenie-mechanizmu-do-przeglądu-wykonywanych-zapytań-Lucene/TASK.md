# [113] Stworzenie mechanizmu do przeglądu wykonywanych zapytań Lucene

https://github.com/slawascichy/hgdb/issues/113

Jest taka potrzeba by mieć podgląd do aktualnie wykonywanych zapytań.
Można to zrealizować poprzez zgromadzenie aktywnych wątków aktualnie realizujących zadanie wyszukiwania
Dobrze by było również prowadzić statystykę wykonywanych zapytań - czasy wykonania, liczba wykonania itd.

Monitoring jednego węzła jest wystarczający, jeżeli węzeł przekazał fragment realizacji zadania do innego węzła to 
tylko info np. `wait for node1`.

Podział na wartswy:
1. Usługi REST
2. GUI - do prezentacji danych w formie tabeli i wykresów

W przyszłości będziemy budować proxy i wtedy można by było zrealizować mechanizm zbierania statystyk z wszystkich 
węzłów i prezentowania ich w jednym miejscu, ale na razie wystarczy monitoring jednego węzła.

## Rozpoznanie (2026-11-03)

- Lokalne wykonanie zapytania przechodzi przez `org.mercury.lucene.searchers` → `pro.ibpm.mercury.lucene.searchers.data.CaseSearcher` (`mercury-srv`): `searchIndex` (trzy warianty), `searchIndexRows`, `searchByInventoryCode`, `dateMetricQuery`, `fieldMetricQuery`, `groupByQuery`. Samo wykonanie robi `QueryExplainPlan` (`mercury-lucene-indexes`, `IndexSearcher.search`, plany i `CostOptimizer`), a dla pozostałych encji `LuceneSearcher` → `LuceneQuery.execute()` (`mercury-lucene-indexes-api`, jedno miejsce `IndexSearcher.search`).
- Warstwa biznesowa: `org.mercury.single.node.business.data.CaseSearchBusiness` (`mercury-srv`) i jej wariant klastrowy `org.mercury.cluster.node.business.data.CaseSearchBusiness` (`mercury-srv-slave`), który przekazuje zapytanie przez RMI do innego węzła (`RemoteAccessProtocol.RMI`, `ClusterUtils.isPossibleLocalExecution`) i przy błędzie wykonuje je lokalnie. To jest miejsce na wpis „czekam na węzeł”.
- Moduł `mercury-lucene-indexes-api` jest zależnością `mercury-lucene-indexes`, `mercury-srv` i `mercury-ws-app`, więc tam trafia rejestr (`org.mercury.lucene.monitor`).
- Decyzje (odpowiedzi autora 2026-11-03: statystyki NIE przeżywają restartu; pełny tekst TAK; próg 1 s i historia 200 OK): statystyki w pamięci węzła, pełny tekst zapytania (decyzja autora: TAK; strona dostępna tylko dla `mrc-sysadmin`; skracany dopiero powyżej 10000 znaków), próg wolnego zapytania 1000 ms, historia 200 pozycji.
- Zasada rejestracji: zagnieżdżone wywołania w tym samym wątku (np. `CaseSearcher` → `QueryExplainPlan` → `LuceneQuery`) nie tworzą kolejnych wpisów; liczy się najbardziej zewnętrzne wejście.

## Realizacja (2026-11-03, gałąź `hgdb-049`)

### Rejestr i statystyki (`mercury-lucene-indexes-api`, pakiet `org.mercury.lucene.monitor`)

- `LuceneQueryMonitor` (singleton w pamięci węzła): aktywne zapytania (`begin`/`Tracker.close`), historia ostatnich i wolnych zapytań (pierścienie po 200), statystyki po „odcisku” zapytania (stałe tekstowe i liczbowe zastąpione `?`, limit 500 odcisków, nadwyżka w wierszu zbiorczym), histogram czasów (przedziały do 10, 50, 100, 250, 500, 1000, 2500, 5000, 10000, 30000 ms) i przybliżone p50/p95. Zagnieżdżone wywołania w tym samym wątku nie tworzą kolejnych wpisów.
- Parametry (opcjonalne, `mercury.properties`): `mercury.lucene.query.monitor.enabled` (true), `.slowMillis` (1000), `.historySize` (200), `.maxQueryChars` (10000), `.maxFingerprints` (500).
- Test: `LuceneQueryMonitorTest` (12).

### Punkty rejestracji

- `CaseSearcher` (`mercury-srv`): `searchIndex` (zapytanie tekstowe; warianty z mapą delegują do niego), `searchIndexRows`, `searchByInventoryCode`, `dateMetricQuery`, `fieldMetricQuery`, `groupByQuery`. Kontekst: użytkownik z `Context`; liczba trafień z `IPagedResult.getTotalHits()` albo `getResultSize()`.
- `LuceneQuery.execute()` (`mercury-lucene-indexes-api`): zapytania pozostałych encji (np. grupy); zapytanie obejmuje tylko wykonanie `IndexSearcher`.
- `CaseSearchBusiness` w `mercury-srv-slave` (wariant klastrowy): zapytanie przekazane do innego węzła (RMI) to wpis w stanie `WAITING_REMOTE` z nazwą węzła (z kontekstu `HTTP_INVOCER_PROXY_FACTORY_INSTANCE_NAME`, a gdy jej brak, `remote`); po błędzie zdalnym i powrocie do wykonania lokalnego stan zmienia się na `RUNNING`.

### REST i strona

- `ILuceneQueriesExtRest` / `LuceneQueriesExtRest` (`/rest/service/LuceneQueriesExtRest`): `getQueriesState` (aktywne, wolne, ostatnie, statystyki; parametr `limit`) i `resetQueriesStatistics`; rola `mrc-sysadmin` z tokenu OAuth albo sesji (wspólny `SysAdminAccess`).
- 8 kluczy `ILuceneQueriesExtRest.*` w `openapi-docs_{pl,en,de,es,fr,ko}.properties` (translator Gemini, `openapi_docs_sync.py`); test pokrycia `LuceneQueriesExtRestOpenApiTest`.
- Zaplecze strony: `LuceneQueriesPanelController` (`/admin/lucene-queries`: `state`, `reset`), `web.xml` (`/admin/lucene-queries/*`, rola `mrc-sysadmin`).
- Strona `static/admin/lucene-queries.html`: kafelki, wykresy w czystym SVG (aktywne zapytania w czasie, zapytania na sekundę, rozkład czasów dla wybranej statystyki), tabele aktywnych, statystyk, wolnych i ostatnich zapytań; odświeżanie ręczne i automatyczne; pl/en. Link na `index.jsp` i klucz `app.index.systemLuceneQueries` w 12 plikach tekstów.
- Testy: `LuceneQueriesStateTest` (4); całość `mercury-ws-app`: 229 testów OK.

### Do zrobienia

- Test na Tomcacie po wdrożeniu WAR (wymaga `mercury-lucene-indexes-api`, `mercury-srv` i `mercury-ws-app`): zapytania z CMIS/REST widoczne na stronie, wolne zapytanie w historii, `LuceneVolumeTest` jako obciążenie, wpis `WAITING_REMOTE` na drugim węźle (`mercury-srv-slave`, np. `node3`).
- Pomiar narzutu monitora na ścieżce zapytania (przypuszczenie: pomijalny, sprawdzić przy 1000 zapytań).
- Dokumentacja w `docusaurus-hgdb` (EN i PL) i parametry w szablonach `mercury.properties`.

### Test na Tomcacie (2026-11-03, `mercury-db-test`, węzeł `node1`)

- Zaplecze po zalogowaniu `admin` (sesja, `j_security_check`) zwraca stan; bez logowania jest formularz logowania.
- Zapytania CMIS `query` widać jako `searchIndex` (użytkownik z kontekstu, liczba trafień); 150 zapytań o tym samym odcisku (`CmisName:?`) policzonych razem (n=151, średnio 7 ms, p50 10 ms, p95 50 ms, maks. 152 ms), wyszukiwanie po identyfikatorze jako `luceneQuery:Case`.
- Poprawka po teście: stałe w identyfikatorach i wzorcach z gwiazdką (`CmisFolder.5812402`, `Perf17*`) trafiały do osobnych statystyk; odcisk zastępuje teraz każdy ciąg cyfr znakiem `?` (wymaga ponownego wdrożenia).
- Narzut rejestracji: 14 µs na zapytanie (100 tys. rejestracji, razem z odciskiem).
- Nie sprawdzone na żywo: stan `WAITING_REMOTE` na drugim węźle (potrzebny proces `mercury-srv-slave` z wyszukiwaniem przez RMI), wolne zapytanie (próg 1 s) w historii, strona w przeglądarce (autor).
- Dokumentacja: `docusaurus-hgdb` strona „Lucene queries monitor” (EN i PL), link w `index.mdx`.
