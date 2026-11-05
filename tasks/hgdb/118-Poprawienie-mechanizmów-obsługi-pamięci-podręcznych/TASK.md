# [118] Poprawienie mechanizmów obsługi pamięci podręcznych

Ogólnie trzeba zweryfikować poprawność wykorzystania pamięci podręcznych, szczególnie w klastrze. Czy to co teraz robimy jest OK? Czy faktycznie dane przepływaja pomiędzy węzłami klastra w sposób prawidłowy? Czy nie ma problemów z synchronizacją danych w pamięciach podręcznych? Warto też sprawdzić, czy nie ma przypadków, gdzie dane są odświeżane zbyt często lub zbyt rzadko, co może wpływać na wydajność systemu.

Zastanowić się też czy są lepsze silniki pamięci współdzielonej i czy warto je wykorzystać w naszym systemie. Warto też sprawdzić czy nie ma problemów z wydajnością przy dużej liczbie węzłów klastra.

Problem: W żądaniu wysyłany jest kontekst z cacheUsage=REFRESH. To powoduje, że w ramach wykonywanej akcji odświeżane są pamięci podręczne wszystkich warstw. Powstała propozycja by móc uszczegółowić dane dotyczące jakiej warstwy pamięci podręcznych mają być odświeżane.
Zrobimy tak, że będzie można dodawać informacje jako elementy mapy (dodatkowe parametry) w polu `requestProperties` kontekstu. Domyślnie, jeżeli nie będzie ustawionych żadnych parametrów, to odświeżane będą pamięci podręczne tylko warstwy biznesowej.
Jakie parametry będziemy ustawiać (jak będą się nazywać) to ustalimy w trakcie dalszej analizy.

Przemyślę również implementację metody "find" dla encji TypeCase - może warto tam dodać specjalną przestrzeń pamięci podręcznej skoro Hibernate sobie z tym nie radzi.


## Rozpoznanie (2026-11-03, odczyt kodu, bez zmian w kodzie)

Zakres rozszerzony przez autora o usunięcie ostrzeżenia `WARN [EhCache.java:256] The method setTimeToLive(ParamValue) is not working for this configuration` (log z 2026-11-02).

### Ostrzeżenie `setTimeToLive` (zweryfikowane w kodzie)

- `AttributeTypeParameter` (`mercury-core-server`, ok. linii 2466) przy tworzeniu pamięci podręcznej atrybutu wywołuje `cache.setTimeToLiveSeconds(...)`, a `setCacheTimeToLive` (ok. 1999) robi to samo dla niedomyślnego TTL z definicji parametru.
- `EhCache.setTimeToLiveSeconds` (`sccommon-cache`) woła `setTimeToLive(ParamValue)`. Metoda zmienia TTL w locie tylko wtedy, gdy polityka wygasania pamięci to `CustomExpiryPolicy`. W przeciwnym razie loguje ostrzeżenie (linia 256) i **nic nie robi**.
- `ehcacheDefault.xml` (serwer dev) definiuje pamięci ze standardowym `<eh:expiry><eh:ttl unit="seconds">…`, czyli bez `CustomExpiryPolicy`. Skutek: ostrzeżenie przy każdej takiej pamięci, a TTL z `ParamDefinition.timeToLiveSeconds` nie działa (obowiązuje TTL z XML). Przypuszczenie do weryfikacji: ostrzeżenie powtarza się dla każdego atrybutu.
- Warianty naprawy: (A) pamięci atrybutów w XML z `CustomExpiryPolicy`, wtedy TTL z definicji parametru zaczyna działać (zmiana zachowania, do przemyślenia); (B) nie wywoływać `setTimeToLive`, gdy polityka nie jest `CustomExpiryPolicy` (ostrzeżenie znika, TTL zostaje z XML); (C) obniżyć poziom do `debug`. Wymaga decyzji autora.

### Co oznacza `cacheUsage=REFRESH` dziś (zweryfikowane)

- `Context.cacheUsage` (String, domyślnie `TO_USE`) + `Context.requestProperties` (`Map<String,String>`, klucze opisane w `ContextRequestProperties`) już istnieją w `mercury-lib`.
- `REFRESH` ma 38 użyć w 23 plikach `mercury` i działa na wielu warstwach naraz: Hibernate query cache (`DAOSupport`, `CommonDAOSupport`: hint `CACHE_MODE=REFRESH`), pamięć obiektów spraw `CaseObjectMapCache` (+ `CaseDAO.find` robi `getEm().refresh`), wyszukiwarki (`SearchProvider`, `MSearcher`, `BSearcher`, `LuceneSearcher`), fabryka atrybutów (`AttributeTypeParameterFactory`), odpowiedzi HTTP (`HttpResponseCacheManager`) i logika (`Case2SubCaseLogic`, bufory BPM, `CaseChangesRegistry`).
- `CaseObjectMapCache` sam ustawia `context.setCacheUsage(REFRESH)` po wykryciu zmiany znacznika czasu, więc `REFRESH` w kontekście bywa też ustawiany wewnętrznie, nie tylko przez klienta.

### Do rozstrzygnięcia przez autora

1. Nazwy parametrów warstw w `requestProperties` i ich granularność (propozycja robocza: `cache.refresh.layers` = lista warstw `business,dao,lucene,http,attributes`; domyślnie bez parametru tylko `business`, jak w opisie zadania).
2. Wariant naprawy ostrzeżenia (A/B/C).
3. Czy analiza klastra (Terracotta, synchronizacja, liczba węzłów, alternatywne silniki) ma być częścią tego zadania, czy osobnym etapem po zmianie `requestProperties`.

## Decyzje autora (2026-11-03) i postęp

Decyzje: (1) parametr warstw w `requestProperties`: `cache.refresh.layers`, domyślnie tylko warstwa biznesowa; (2) ostrzeżenie `setTimeToLive`: wariant B; (3) analiza klastra wchodzi do zadania i jest robiona w tym samym kroku co zmiana `requestProperties` (potwierdzone przez autora).

Gałąź `hgdb-118` w `mercury` (z aktualnego `master`).

**Zrobione: wariant B (ostrzeżenie `setTimeToLive`).** `CacheHelper.applyTimeToLive(IObjectCache, long)` (`mercury-core-server`) ustawia czas życia tylko wtedy, gdy pamięć Ehcache ma `CustomExpiryPolicy`; w innym przypadku pomija ustawienie (wpis `debug`), a obowiązuje czas z XML. Użyte w `AttributeTypeParameter.setCacheTimeToLive` i `createCache`. Test `CacheHelperTimeToLiveTest` (2 OK). Gałąź Ehcache sprawdzi się po wdrożeniu: w logu serwera nie ma już `WARN [EhCache.java:256]`.

### Zmiana w `mercury-lib` (gałąź `hgdb-118`, 2026-11-03)

`ContextRequestProperties`: enum `CacheLayer` (`BUSINESS`, `DAO`, `LUCENE`, `HTTP`, `ATTRIBUTES`), stała `CACHE_REFRESH_LAYERS = "cache.refresh.layers"`, `CACHE_REFRESH_ALL = "ALL"`, metody `getRefreshLayers(Context)` (bez parametru: tylko `BUSINESS`; nieznane nazwy pomijane; `ALL` = wszystkie) i `refreshesLayer(Context, CacheLayer)`. Test `CacheRefreshLayersTest` (4 OK). Po wydaniu `mercury-lib` trzeba podnieść `mercury.static.version` w `mercury` i podpiąć warstwy w miejscach użycia `REFRESH` (tabela przypisań do zrobienia).

### Klaster: pierwsze ustalenia (zweryfikowane w konfiguracji, wnioski jako przypuszczenia)

- **Korekta (2026-11-03, po uwadze autora):** wniosek o pamięciach lokalnych dotyczy tylko pliku `mercury-server/IBPM/mercury/config/ehcacheDefault.xml` (konfiguracja serwera dev w repozytorium): ma blok `terracotta:cluster`, ale żadna pamięć nie ma `<terracotta:clustered-store>`. Pliki testowe (`*/src/test/resources/ehcacheDefault.xml`, np. `mercury-srv`: 33 wystąpienia) mają `clustered-store consistency="strong"` we wszystkich pamięciach, a `test-mercury.properties` ma go w komentarzu. Którego pliku używa środowisko klastrowe autora, nie wiem: w repozytoriach `mercury`, `mercury-docker`, `mercury-cmd` ani `sccommon` nie ma innego pliku z `clustered-store`. Do ustalenia z autorem.
- Unieważnienie między węzłami istnieje tylko dla definicji (JMS: `ParamDefinitionRegistryChangesReceiver`, `TypeCaseRegistryChangesReceiver`, `TypeParamRegistryChangesReceiver` czyszczą pamięci zapytań) oraz `TypeCodeDAO.evictSecondLevelCache`. Dla spraw (encja `Case` nie ma `@Cacheable(false)`) nie znaleziono unieważniania między węzłami poza TTL (`CaseObjectMapCache`: 300 s) i porównaniem znaczników czasu w `CaseDAO.find`, które czyta encję z lokalnego regionu Hibernate. Do sprawdzenia: czy regiony encji są włączone (fabryka `ScEhCacheRegionFactory`; brak `shared-cache-mode` w konfiguracji).

## Projekt warstw odświeżania (propozycja, 2026-11-03, do zatwierdzenia)

`mercury-lib` 3.0.4.21 zainstalowane lokalnie (autor); w `mercury` podniesione `mercury.static.version` (gałąź `hgdb-118`), jar encji skopiowany do `.m2` jako `POSTGRESQL-3.0.4.21`, pom rodzica w `.m2` odświeżony. `mercury-core-server` kompiluje się.

### Zasada

Pomocnik w `mercury-core-server`: `CacheRefresh.isRefresh(Context, CacheLayer)` = `cacheUsage == REFRESH` **i** warstwa należy do `ContextRequestProperties.getRefreshLayers(context)`. Miejsca, które dziś pytają o `context.getCacheUsage()` dla swojej warstwy, przechodzą na ten pomocnik.

**Ryzyko do świadomej decyzji.** Część kodu serwera sam ustawia `context.setCacheUsage(REFRESH)` po wykryciu zmiany (np. `CaseObjectMapCache` przy zmianie znacznika czasu sprawy, bufory BPM, `CasesParamsSaver`, `CaseChangesRegistry`) i oczekuje, że dalsze odczyty w tym żądaniu pominą pamięci wszystkich warstw. Gdyby domyślnie odświeżała się tylko warstwa `BUSINESS`, takie wewnętrzne `REFRESH` przestałoby odświeżać `DAO`/`LUCENE` i mogłoby pokazać nieaktualne dane. Propozycja: wewnętrzne ustawienia `REFRESH` idą przez `CacheRefresh.refreshAll(context)` (ustawia `REFRESH` i warstwy `ALL`), a zawężenie warstw dotyczy tylko `REFRESH` przysłanego przez klienta.

### Przypisanie miejsc czytających `cacheUsage` z kontekstu do warstw (z lektury kodu; wiersze z ? to przypuszczenie)

| Warstwa | Miejsca |
|---|---|
| `DAO` | `DAOSupport` (210, 277, 291: dopuszczenie query cache i hint `CACHE_MODE=REFRESH`), `CommonDAOSupport` (123, 135, 149), `MBigDataDAOSupport` (373) |
| `LUCENE` | `QueryExplainPlan` (2374, 2778), `DateMetricQuery` (156), wyszukiwarki `SearchProvider`/`MSearcher`/`BSearcher`/`LuceneSearcher` (REFRESH z `searcher.getCacheUsage()`, do potwierdzenia skąd wartość) |
| `ATTRIBUTES` | `AttributeTypeParameter` (899, 998, 1407, 1715, 1856, 1964), `AttributeTypeParameterFactory` (123) |
| `HTTP` | `HttpResponseCacheManager` (używa `httpResponseCacheUsage`, osobnego pola kontekstu: do ustalenia, czy ma dostać też warstwę) |
| `BUSINESS` | `CaseDAO.find` + `CaseObjectMapCache` (obiekty spraw), `CaseBusiness.transform2MrcObject` (1026), `CaseHistoryStreamBusiness` (149, 545; używa pamięci obiektów tylko przy `TO_USE`), `Case2SubCaseLogic` (539, 778) |
| wewnętrzne (zostają pełnym odświeżeniem) | `CaseLogic` (702, 865), `CaseChangesRegistry` (295), `CasesParamsSaver` (239), `MrcCaseResultSaver` (245), bufory BPM (`BpmTaskBufferLogic`, `BpmBPDInstanceBufferLogic`, `BpmTaskNarrativeBufferLogic`), `BpmTaskMapper` (56), `CaseIndexerBusinessUpdateCallable`, `CaseDocumentLogicHelper`, `ParamDefinitionDAO` (299) |

Do zweryfikowania przed kodem: czy `CaseSearchBusiness` (master i slave) ma być osobną warstwą (zapisuje `NONE` na czas transformacji i przywraca wartość użytkownika, więc dziedziczy decyzję), oraz skąd `searcher.getCacheUsage()` bierze wartość.

## Realizacja: warstwy odświeżania (2026-11-03, gałąź `hgdb-118`, niezacommitowane)

Decyzja autora: zawężenie warstw tylko dla `REFRESH` przysłanego przez klienta, wewnętrzne `REFRESH` serwera odświeżają wszystkie warstwy (potwierdzone).

- `CacheRefresh` (`mercury-core-server`, `pro.ibpm.mercury.cache`): `isRefresh(Context, CacheLayer)`, `usage(Context, CacheLayer)` (dla `REFRESH`, którego warstwa nie odświeża, zwraca `TO_USE`), `refreshAll(Context)` (ustawia `REFRESH` i warstwy `ALL`). Test `CacheRefreshTest` (4 OK).
- Wewnętrzne ustawienia `REFRESH` zamienione na `CacheRefresh.refreshAll`: `CaseObjectMapCache` (3), `CaseDAO.find`, `CaseLogic` (2), `CaseChangesRegistry`, `CasesParamsSaver`, `MrcCaseResultSaver`, bufory BPM (3), `BpmTaskMapper`.
- Warstwy podpięte przez `CacheRefresh.usage(context, warstwa)`: `DAO` (`DAOSupport`, `CommonDAOSupport`, `MBigDataDAOSupport`), `LUCENE` (`QueryExplainPlan` 2, `DateMetricQuery`), `ATTRIBUTES` (`AttributeTypeParameter` 6), `BUSINESS` (`CaseBusiness`, `CaseHistoryStreamBusiness` 2, `Case2SubCaseLogic` 4).
- Bez zmian celowo: `CaseSearchBusiness` (master i slave: zapisuje `NONE` na czas transformacji i przywraca wartość klienta), wyszukiwarki (`SearchProvider`, `MSearcher`, `BSearcher`, `LuceneSearcher`: własne `REFRESH` z pola `searcher`), `HttpResponseCacheManager` (osobne pole `httpResponseCacheUsage`), `ParamDefinitionDAO`, `AttributeTypeParameterFactory` (odświeżenie wymuszone przez serwer), `CaseIndexerBusinessUpdateCallable` i `CaseDocumentLogicHelper` (pola DAO, nie kontekst).
- Zmiana zachowania: klient z `REFRESH` bez `cache.refresh.layers` odświeża tylko warstwę biznesową; `DAO` (Hibernate query cache), `LUCENE` i `ATTRIBUTES` używają pamięci bez odświeżania. Pełne odświeżenie: `cache.refresh.layers=ALL`.
- Kompilacja: `mercury-core-server`, `mercury-dao`, `mercury-lucene-indexes`, `mercury-srv` (install bez testów) OK. Nie sprawdzone na serwerze.

## Weryfikacja na Tomcacie (2026-11-03, `mercury-db-test`, pamięci klastrowe)

- Start serwera (18:25): połączenie z Terracottą (`LeaseMaintainerFactory`, `CLUSTERED node`), brak błędów konfiguracji pamięci. Jedyny `ERROR` to znany brak `ehcache.properties`.
- Wywołania REST z `cacheUsage` `TO_USE`/`REFRESH` i `cache.refresh.layers` (bez, `business`, `dao`, `ALL`) kończą się HTTP 200, bez błędów w logu. Skrypt: `scratchpad/refresh_test.sh` (token klienta OAuth czytany w locie z konfiguracji dev, niewypisywany; poziom `org.hibernate.SQL` przywracany do `INHERIT`).
- **Ograniczenie:** różnicy między wariantami nie widać w SQL dla `TypeCodeRest/findAll` (zawsze 11 zapytań o `IGO_DA_TYPECODE`: encja bez pamięci drugiego poziomu, N+1 po zapytaniu). Zachowanie warstwy DAO sprawdza test jednostkowy `DAOSupportRefreshLayerTest` (3 OK): `REFRESH` bez warstw lub z `business` daje `CACHE_MODE=NORMAL`, z `dao` lub `ALL` daje `REFRESH`, `TO_USE` i `NONE` bez zmian.
- Wariant B ostrzeżenia `setTimeToLive`: logger `pl.slawas.common.cache` jest w `apache-tomcat/lib/logback.xml` ustawiony na `ERROR` (zmiana autora), więc brak `WARN EhCache.java:256` w logu niczego nie dowodzi. Potwierdza go test `CacheHelperTimeToLiveTest` i lektura kodu; pełne sprawdzenie wymagałoby podniesienia tego loggera do `WARN` i restartu (pamięci atrybutów powstają przy pierwszym użyciu).
- Niesprawdzone: odświeżenie wewnętrzne (`CaseObjectMapCache`) po zmianie sprawy z drugiego węzła; drugi węzeł nie był uruchomiony.

## Ostrzeżenie `setTimeToLive`: poprawka w `sccommon` (2026-11-03, gałąź `hgdb-118` w `sccommon`, niezacommitowane)

Po restarcie serwera (logger `pl.slawas.common.cache` przywrócony przez autora) ostrzeżenie `EhCache.java:256` nadal się pojawiało (16 razy od startu) przy pamięciach `SecurityContext` (10), `CaseMetadataCache` (5) i `CaseLobPropertyCache` (1). Te pamięci tworzy klasa bazowa `ObjectWithCacheSupport` z `sccommon-cache`, która przy tworzeniu pamięci i w `setCacheTimeToLive` zawsze woła `setTimeToLiveSeconds`; poprawka w `mercury` (`CacheHelper.applyTimeToLive`) obejmowała tylko `AttributeTypeParameter`. (Wcześniejszy brak ostrzeżeń w oknie 18:25 wynikał z loggera ustawionego na `ERROR`; moja uwaga, że ustawienie nie działa, była błędna.)

Zmiany w `sccommon-cache` (decyzja autora: poprawiamy w `sccommon`):
- `IObjectCache.isTimeToLiveChangeable()` (metoda domyślna, `true`),
- `EhCache.isTimeToLiveChangeable()`: `true` tylko dla `CustomExpiryPolicy`,
- `ObjectWithCacheSupport`: oba miejsca ustawiania TTL idą przez `applyTimeToLive`, które pomija zmianę (wpis `debug`), gdy pamięć jej nie obsługuje.
- Test `EhCacheTimeToLiveChangeableTest` (2 OK, prawdziwy Ehcache: standardowe `ttl` i `CustomExpiryPolicy`); testy modułu `sccommon-cache` zielone (`EhCacheProviderTest`, `ScEhCacheRegionFactoryTest`). W `sccommon-utils` pada `JdbcEntityManagerTest.testDmlOperations` (moduł bez zmian, test JDBC; nie sprawdzałem, czy pada też bez mojej zmiany).

Do zrobienia po wydaniu `sccommon`: podnieść wersję w `mercury` i uprościć `CacheHelper.applyTimeToLive` do `cache.isTimeToLiveChangeable()`; sprawdzić w logu serwera brak `WARN EhCache.java:256`. Pozostałe repozytoria z `sccommon` (`mercury-lib`, `hgdb-client-open`, `mercury-cmd`) dostaną nową wersję przy własnym wydaniu (interfejs zgodny wstecz).

**2026-11-03:** `sccommon` 2.0.0.3 wydany (autor). W `mercury`: `sccommon.version` = 2.0.0.3 (pom rodzica w `.m2` odświeżony), `CacheHelper.applyTimeToLive` używa `IObjectCache.isTimeToLiveChangeable()`; testy `CacheHelperTimeToLiveTest` (3), `CacheRefreshTest` (4), `DAOSupportRefreshLayerTest` (3) OK, `mercury-core-server` zainstalowany. Do sprawdzenia po wdrożeniu WAR i restarcie: brak `WARN EhCache.java:256` w logu serwera (logger `pl.slawas.common.cache` na `WARN`).

## Analiza klastra: pamięci nie są współdzielone (2026-11-03, test na dwóch węzłach)

**Wynik (zweryfikowany):** przy obecnej konfiguracji pamięci podręczne są **lokalne dla węzła**; dane nie przepływają między węzłami przez Terracottę.

- Test `CacheClusterScenario`/`CacheClusterTest` (`mercury-srv-slave`, węzeł 2 = proces testowy, węzeł 1 = Tomcat): węzeł 2 zapisał wpis w pamięci `MercuryCore`, węzeł 1 wyczyścił tę pamięć przez REST `clearCache` (200), a wpis węzła 2 przetrwał: pamięć lokalna. Węzeł 2 raportuje zasoby pamięci `MercuryCore`: `[heap, offheap]` (bez warstwy klastrowej), mimo że `ehcacheDefault.xml` ma `<terracotta:clustered-store consistency="strong"/>`. Uwaga: `EhCacheProvider.clearCache` czyści tylko pamięci zarejestrowane w mapie `caches` providera i po cichu pomija nieznaną nazwę, więc sam wynik `clearCache` nie dowodzi; dowodem jest lista zasobów pamięci i eksperyment poniżej.
- **Eksperyment kontrolny** (dwóch klientów Terracotty w jednym procesie, tymczasowe pamięci `probe118-*`, po teście usunięte z serwera Terracotty; skrypty w `scratchpad/probe`, Ehcache 3.6.1):
  | Konfiguracja pamięci | Zasoby | B widzi zapis A | `clear()` z B widoczny w A |
  |---|---|---|---|
  | `heap` + `<terracotta:clustered-store consistency="strong"/>` (jak w Mercury) | `[heap]` | nie | nie |
  | `heap` + `<terracotta:clustered-dedicated unit="MB">2</...>` + `clustered-store` | `[heap, clustered-dedicated]` | tak | tak |
  | `heap` + `offheap` + `clustered-dedicated` + `clustered-store` | `[heap, offheap, clustered-dedicated]` | tak | tak |
- **Wniosek:** w Ehcache 3 pamięć jest klastrowa dzięki **zasobowi klastrowemu** w `<eh:resources>` (`clustered-dedicated`, albo `clustered-shared` z pulą), a `clustered-store` tylko ustawia spójność i bez zasobu nic nie daje. Wszystkie obecne `ehcacheDefault.xml`/`ehcacheCommon.xml` (serwer, profile, `mercury-docker`, `mercury-cmd`, pliki testowe) mają `clustered-store` bez zasobu klastrowego, więc pamięci w klastrze nie są współdzielone. Nie sprawdzono wariantu `clustered-shared` (zmiana `server-side-config` na już skonfigurowanym serwerze Terracotty prawdopodobnie wymaga zgodnej konfiguracji).
- **Konsekwencje:** spójność między węzłami opiera się dziś tylko na JMS (unieważnianie pamięci definicji: `ParamDefinition`, `TypeCase`, `TypeParam`), na porównaniu znaczników czasu w `CaseDAO.find`/`CaseObjectMapCache` oraz na TTL. Dla pamięci bez unieważniania (np. regiony Hibernate, pamięci odpowiedzi HTTP, `CaseObjectMapCache` w węźle bez zmiany) dane mogą być nieaktualne do wygaśnięcia TTL. Czy encja `Case` jest w pamięci drugiego poziomu i które regiony faktycznie są używane: do sprawdzenia.
- **Do decyzji autora:** które pamięci mają być klastrowe (nie wszystkie: koszt serializacji i opóźnienie Terracotty) i jak duże (`clustered-dedicated unit="MB"`); wartości w pamięciach klastrowych muszą być serializowalne.

## Analiza: co współdzielić w klastrze (2026-11-03)

Pełna analiza w `analiza-pamieci-klaster.md` (tabele z rekomendacją i priorytetami). Skrót: priorytet 1 (poprawność): `default-update-timestamps-region`, `CaseGlobalTransactionCache`; priorytet 2 (definicje i atrybuty): `CaseMetadataCache` i pamięci wartości słownikowych atrybutów (szablon `default`); definicje typów i atrybutów w mapach JVM (`ICaseTypesManager`, `AttributeTypeParameterFactory.attributies`) nie są pamięciami Ehcache, więc XML ich nie obejmie (synchronizacja JMS); reszta zostaje lokalna. Czeka na decyzję autora, potem zmiana plików XML i test na dwóch węzłach.

## Zmiany konfiguracji pamięci klastrowych (2026-11-03, niezacommitowane)

Zakres (decyzja autora: „zaczynamy tak jak piszesz”): w `ehcacheDefault.xml` i `ehcacheCommon.xml` (serwer dev, profile `scichy` i `scichy-test`, `mercury-srv-slave` test, `mercury-docker`, `mercury-cmd` sample):
- `default-update-timestamps-region`: `heap` + `clustered-dedicated` 4 MB (bez `offheap`),
- `CaseGlobalTransactionCache`: `heap` 20000 + `clustered-dedicated` 64 MB (bez `offheap`), `ttl` 86400 bez zmian,
- nowy alias `CaseMetadataCache` (tylko Default): `heap` 1000 + `clustered-dedicated` 64 MB, `ttl` 3600 (zabezpieczenie; unieważnia JMS),
- szablon `default` (tylko Default): `<eh:expiry><eh:class>…CustomExpiryPolicy</eh:class></eh:expiry>`.
Parsowanie wszystkich 12 plików przez `XmlConfiguration` OK.

**Odkrycie (szablon `default`):** gdy w XML jest szablon `default`, `EhCacheProvider` tworzy z niego wszystkie pamięci dynamiczne i nigdy nie używa `CustomExpiryPolicy`, więc `setTimeToLive` nie mógł działać: pamięci dynamiczne (`SecurityContext`, `OAuthFactory`, `CaseLobPropertyCache`, wartości słownikowe atrybutów i inne) **nie miały żadnego wygasania**, a TTL z `ParamDefinition.timeToLiveSeconds` i `cache.timeToLiveSeconds` były ignorowane. Sprawdzone eksperymentem: szablon z `CustomExpiryPolicy` daje każdej pamięci własną instancję polityki, a TTL ustawiony na jednej nie zmienia drugiej (domyślnie 86400 s). Skutek zmiany: pamięci dynamiczne zaczną wygasać po TTL (24 h domyślnie albo z definicji parametru); `MercurySecurityOAuthConfig` trzyma tylko wyniki sprawdzenia ścieżek (bezpieczne), `OAuthFactory` czyta token z bazy po wygaśnięciu.

**Weryfikacja węzła 2 (proces `mercury-srv-slave`):** zasoby `[heap, clustered-dedicated]` dla `CaseGlobalTransactionCache`, `CaseMetadataCache` i `default-update-timestamps-region`; `TypeCase` CmisFolder (3 parametry) po serializacji: 6489 bajtów. Kroki z węzłem 1 (czyszczenie przez REST) czekają na restart Tomcata z nową konfiguracją (węzeł 1 działa jeszcze na starej, lokalnej).

**`CaseObjectMapCache` i `CaseMapper` (uwaga autora):** `CaseObjectMapCache` trzyma wynik przekształcenia relacyjnego w obiekt (`MrcObject`, klucz: id sprawy + skrót parametrów transformacji, walidacja znacznikiem czasu sprawy), więc to najdroższy do odtworzenia wpis i współdzielenie ma uzasadnienie (ciepła pamięć na każdym węźle). Zastrzeżenia do pomiaru: rozmiar (150000 wpisów wobec 512 MB zasobu), `put` serializuje całą mapę wariantów sprawy, serializowalność zagnieżdżonych właściwości `MrcObject`. `CaseMapper` trzyma `org.apache.lucene.document.Document`, które **nie jest `Serializable`** (sprawdzone), więc bez zmiany kodu nie może być klastrowe; używa go głównie indekser.

### `CaseMapper`: współdzielenie gotowych dokumentów Lucene (uwaga autora, 2026-11-03)

Cel autora: jeden węzeł przygotowuje dokument (kosztowne mapowanie sprawy), pozostałe węzły dodają gotowy do własnych indeksów.

Ustalenia z kodu:
- Pamięć dokumentów jest **wyłączona w kodzie**: w `CaseMapper.convert2Document` wywołanie `helper.getDocument(...)` jest zakomentowane z uwagą FIXME („Document cannot be cast to java.io.Serializable, na razie wyłączam użycie pamięci podręcznej”), a używane jest `CaseMapperHelper.createNewInstance` (zawsze pełne mapowanie). Region `CaseMapper` (150000 wpisów) jest więc dziś nieużywany.
- Każdy węzeł dostaje te same zmiany indeksu (paczki rozsyłane do kolejek węzłów, obs. 139) i mapuje sprawy samodzielnie, więc praca jest powielana na każdym węźle indeksującym.
- Dawny projekt (`CachedDocument`, `removeExternalFields`, `sourceChanges`) zakładał częściową aktualizację dokumentu z pamięci; dokument zależy też od źródeł zewnętrznych (komentarze, podsprawy, pliki), których zmiana nie zmienia `Case.lastModifyDate`.

Wniosek: współdzielenie jest możliwe po zmianie kodu: serializowalny odpowiednik dokumentu (lista pól z parametrami `FieldType` i wartościami, odtwarzany do `Document`) oraz klucz oparty na tożsamości zmiany (sprawa + wersja źródeł/paczka), nie samo id sprawy; pamięć ma być krótkim buforem przekazania (TTL rzędu minut, usuwanie przez eksmisję), a nie 150000 wpisów. Przed implementacją: pomiar udziału `convert2Document` w czasie indeksowania sprawy.

### `CaseMapper`: komunikat JMS o zmianach indeksu i import (odpowiedzi na uwagi autora, 2026-11-03)

**Komunikat JMS** (`LuceneCaseSaveBuffersForIndexMessage`, temat `LUCENE_DOCUMENT_REGISTRY_CHANGES_TOPIC`, właściwość `sender`): `nodeName` nadawcy i lista `CaseSaveBuffer`: `id` (klucz wiersza bufora w wspólnej bazie), `matterId` (id sprawy), `operation` (I/U/R), `scnNumber` (numer sesji indeksowania nadawany przez sekretarza, dla niesprocesowanych wpisów `null`), `source` (nazwa obiektu, którego zmiana wywołała aktualizację), `skipBefore`, `typeCode`.
- Komunikat mówi **co** się zmieniło, ale **nie niesie wersji** sprawy ani źródeł. Wiersz bufora dla sprawy z `SCN_NUMBER IS NULL` jest wyszukiwany po `MATTER_ID` (`CaseSaveBufferDAOJDBC`), więc kolejne zmiany tej samej sprawy przed przetworzeniem trafiają do tego samego wiersza (przypuszczenie: aktualizowany, nie dublowany); `id` wiersza nie jest więc tożsamością wersji dokumentu. Klucz (`matterId`, `operation`, `source`) ani `id` nie wystarczy, żeby bezpiecznie użyć dokumentu przygotowanego przez inny węzeł (węzeł B mógłby użyć dokumentu starszego niż zmiana).
- Warianty: (A) dodać do bufora token wersji zmiany (kolumna rosnąca przy każdej zmianie wiersza; DDL dla wszystkich baz, na PostgreSQL ręcznie), dokument w pamięci kluczowany `matterId` + token; (B) węzeł używający sprawdza odcisk danych wejściowych (np. `lastModifyDate` sprawy i znaczniki źródeł) przed użyciem dokumentu, o ile da się go policzyć taniej niż pełne mapowanie; (C) węzeł mapujący publikuje gotowy dokument w komunikacie (zmiana architektury: rozmiar komunikatu, kolejność, obsługa błędów). Rekomendacja: pomiar, potem wariant A.

**Import (skokowy, duży rozmiar):** rozmiar bufora przekazania ≈ tempo mapowania × opóźnienie drugiego węzła × rozmiar dokumentu, np. 500 dok/s × 120 s × 15 KB ≈ 900 MB (wartości przykładowe, bez pomiaru); cały milionowy import (≈ 15 GB) i tak nie zmieści się w `primary-server-resource` (512 MB w kicie dev). Alokowanie pod import nie ma więc sensu: pamięć ma być ograniczona (eksmisja zastępuje brakujące wpisy zwykłym mapowaniem na węźle), a tryb hurtowy (bufor hurtowy z zadania 114, importy przekraczające próg) powinien albo omijać bufor przekazania (serializacja i sieć bez zysku, gdy odbiorca jest daleko w tyle), albo go używać z krótkim TTL i akceptować chybienia. Prawdziwą dźwignią dla importu jest podział pracy (każdy węzeł mapuje inny podzbiór spraw i publikuje dokumenty), co wymaga wariantu C.

## Wynik testu klastra po restarcie Tomcata z nową konfiguracją (2026-11-03)

`CacheClusterScenario` (węzeł 2 = proces `mercury-srv-slave`, węzeł 1 = Tomcat, wspólna baza `mercury-db-test`, wspólna Terracotta): **przechodzi** (1 test, 0 błędów).
- `CaseGlobalTransactionCache` i `CaseMetadataCache`: wpis zapisany przez węzeł 2 znika po `clearCache` wykonanym przez REST na węźle 1: pamięci są współdzielone.
- `default-update-timestamps-region`: zasoby `[clustered-dedicated, heap]`. Po `createFolder` (CMIS, Basic) na węźle 1 węzeł 2, pytając Hibernate (`UpdateTimestampsCache.isUpToDate`) o tabelę `IGO_DA_CASES`, uznaje wyniki zapytań po chwili `t0` za nieaktualne (przed zapisem: aktualne). Czyli zapis na jednym węźle unieważnia zbuforowane zapytania na drugim. Nie wykonano kontroli negatywnej na starej, lokalnej konfiguracji (wcześniej region był lokalny, więc brak propagacji jest oczekiwany, ale nie zmierzony).
- `TypeCase` (CmisFolder, 3 parametry) po serializacji: 6489 bajtów.
- Start Tomcata (19:51): brak ostrzeżeń i błędów związanych z pamięciami.
- Scenariusz uruchamiany z `-Dmaven.test.skip=false -Duser=scichy-test`, kluczem `test.skip.package.CacheClusterTest=false` (tymczasowo, w profilu `scichy-test`) i zmiennymi środowiskowymi `HGDB_OAUTH_CLIENT_ID`, `HGDB_OAUTH_CLIENT_SECRET`, `HGDB_USER`, `HGDB_PASSWORD`. Test sprząta po sobie (folder CMIS usuwany `deleteTree`).

Otwarte: pamięci wartości słownikowych atrybutów (własny szablon klastrowy), pomiar `CaseObjectMapCache` i `convert2Document` (`CaseMapper`), przycięcie `CacheRefresh`/warstw na serwerze (sprawdzenie na żywo dla `LUCENE` i `ATTRIBUTES`), commity.

## Pomiary dla `CaseObjectMapCache` i `CaseMapper` (2026-11-03, zestaw 116, 243 sprawy, `mercury-db-test`)

Scenariusz `CacheMeasureScenario` (`mercury-srv`, test `CacheMeasureTest`; czyści bazę i ładuje zestaw z zadania 116; dane zostawione `-Dtest.keep.dataset=true`).

| Wielkość | średnia | p50 | p90 | p99 | max |
|---|---|---|---|---|---|
| przekształcenie sprawy w `MrcObject`, bez pamięci (ms) | 4,58 | 3,43 | 6,75 | 19,7 | 90,3 |
| to samo z pamięcią, trafienie lokalne (ms) | 1,97 | 1,83 | 2,60 | 4,50 | 15,6 |
| serializacja `MrcObject` (ms) / odczyt (ms) | 0,20 / 0,42 | 0,15 / 0,35 | 0,29 / 0,58 | 1,14 / 1,61 | 4,2 / 4,9 |
| rozmiar `MrcObject` po serializacji (B) | 4446 | 3454 | 7073 | 15655 | 56770 |
| pobranie sprawy do indeksu `findForIndex` (ms) | 1,87 | 1,82 | 2,54 | 3,93 | 5,7 |
| mapowanie na dokument Lucene `convert2Document` (ms) | 9,54 | 8,82 | 13,9 | 21,2 | 32,0 |
| rozmiar dokumentu Lucene, suma długości pól (B) | 2093 | 1924 | 2795 | 5085 | 7884 |

Wszystkie 243 `MrcObject` są serializowalne. Pamięć lokalna oszczędza średnio ok. 2,6 ms na sprawę (4,6 → 2,0 ms: samo `find` nadal czyta sprawę z bazy). Dokument Lucene jest mały (średnio 2 KB, max 8 KB), więc bufor przekazania dokumentów zajmuje ok. 7 razy mniej, niż zakładał wcześniejszy przykład (15 KB): 500 dok/s × 120 s × 2,1 KB ≈ 126 MB.

**Opóźnienie Terracotty (mikrotest, serwer kit dev na Windows, localhost, dwóch klientów, `clustered-dedicated`, odczyty z pominięciem `heap`):** zapis i odczyt wpisu od innego klienta trwa **ok. 13–15 ms** niezależnie od rozmiaru (2, 5, 16, 56 KB), spójności (`strong` i `eventual`) i `preferIPv4Stack`. Wartość zbliżona do kwantu zegara Windows (15,6 ms); opóźnienie na Linuksie (środowisko produkcyjne) nie zostało zmierzone.

Wnioski (dla tego środowiska):
- `CaseObjectMapCache` w pamięci klastrowej: odczyt (≥ 13 ms) jest wolniejszy niż pełne przekształcenie (średnio 4,6 ms, p99 19,7 ms), więc współdzielenie opłaca się tylko dla rzadkich, bardzo ciężkich spraw. **Zostaje lokalna.**
- `CaseMapper` (przekazywanie dokumentów): mapowanie średnio 9,5 ms vs odczyt z Terracotty ≥ 13 ms; opłacalne dopiero przy opóźnieniu Terracotty wyraźnie poniżej czasu mapowania (do zmierzenia na Linuksie) albo przy pobieraniu wielu dokumentów jednym żądaniem.
- **Ryzyko dla już wdrożonych pamięci klastrowych:** każdy zapis w regionie znaczników czasu (Hibernate: wstępne i końcowe unieważnienie dla każdej tabeli transakcji) i w `CaseGlobalTransactionCache` kosztuje jedną operację Terracotty; przy 13–15 ms na operację zapis sprawy może zwolnić o dziesiątki–setki ms (do zmierzenia: `createFolder` w pustym folderze miał 0,09 s przy pamięciach lokalnych).
- Alternatywa dla znaczników czasu: wyłączenie pamięci zapytań Hibernate (`hibernate.cache.use_query_cache=false`), co usuwa i ryzyko nieaktualnych wyników między węzłami, i zapisy do Terracotty; koszt to więcej zapytań do bazy (do zmierzenia, zapytania zwracające encje bez pamięci drugiego poziomu już omijają pamięć zapytań).

Stan bazy po pomiarze: w `mercury-db-test` jest zestaw 243 spraw z zadania 116, a folder główny CMIS został usunięty przez czyszczenie (Tomcat zgłasza `objectNotFound` dla starego id; po restarcie serwer tworzy folder główny od nowa).

## Pomiar na dużych obiektach (FSMServiceOrder, 2026-11-03) i szablon `attribute-values`

`CacheMeasureScenario` rozszerzony o `-Dmeasure.files=<pliki z /pro/ibpm/mercury/logic/>`, `-Dmeasure.dataset=false`, `-Dmeasure.clean=false`, `-Dmeasure.repeats=5`. Załadowano `FSMServiceOrder.v1.xml` (84 339 B XML, 1 sprawa, 3,1 s), `FSMServiceOrderSimple.v1.xml` (1 sprawa) i `FSMServiceOrderSimple.v3.xml` (2 sprawy); `FSMServiceOrder.v2.xml` nie załadował się (loader: „Can't insert case with previousVersionId=…, because is not set rootVersionId”, niezwiązane z pomiarem). Cztery sprawy po 5 powtórzeń (n=20):

| Wielkość (DUZE) | średnia | p50 | p90 (≈ `FSMServiceOrder`) | max |
|---|---|---|---|---|
| przekształcenie w `MrcObject`, bez pamięci (ms) | 22,4 | 11,3 | 62,7 | 63,7 |
| to samo, trafienie lokalne (ms) | 1,16 | 1,02 | 1,72 | 2,02 |
| rozmiar `MrcObject` (B) | 26 880 | 18 079 | 62 945 | 62 945 |
| serializacja / odczyt (ms) | 0,62 / 0,79 | 0,43 / 0,65 | 1,41 / 1,60 | 1,52 / 1,64 |
| mapowanie na dokument Lucene (ms) | 8,1 | 8,1 | 10,6 | 11,2 |
| rozmiar dokumentu Lucene (B) | 4488 | 4137 | 5614 | 5614 |

(Zestaw 116, 278 spraw, bez dużych: przekształcenie średnio 3,3 ms, `MrcObject` średnio 4,6 KB, dokument 2,1 KB, mapowanie 6,6 ms.)

Wnioski:
- `FSMServiceOrder` v1 (sprawa 63 KB po serializacji) przekształca się w ok. 63 ms, więc odczyt z Terracotty (ok. 15 ms + 1,6 ms odczytu) oszczędziłby ok. 46 ms (73%), ale dla typowych spraw (3–11 ms) byłby stratą. Próg opłacalności: koszt przekształcenia powyżej opóźnienia Terracotty (tu ok. 17 ms), więc tylko dla rzadkich, ciężkich spraw. Wariant selektywny (do rozważenia, nie wdrożony): do pamięci klastrowej trafiają tylko wpisy, których przekształcenie trwało powyżej progu, a zdalne wyszukiwanie wykonuje się tylko dla typów uznanych lokalnie za ciężkie.
- Dokument Lucene nie rośnie tak jak `MrcObject` (4,5 KB wobec 27 KB średnio; mapowanie 8 ms), więc przekazywanie dokumentów nie zyskuje na dużych typach; opłacalność `CaseMapper` zależy od opóźnienia Terracotty na Linuksie.

**Punkt 1 (sccommon 2.0.0.4, wydany przez autora):** `sccommon.version` = 2.0.0.4 w `mercury` (pom rodzica w `.m2` odświeżony); `AttributeTypeParameter.createCache` używa `getCache(nazwa, CacheHelper.ATTRIBUTE_VALUES_TEMPLATE)`; w sześciu `ehcacheDefault.xml` dodano szablon `attribute-values` (lokalny, `CustomExpiryPolicy`): współdzielenie w klastrze to dopisanie zasobu klastrowego w tym szablonie. Testy `mercury-core-server` (10) OK. Poprawka `CustomExpiryPolicy` w 2.0.0.4: odczyt nie przedłuża już życia wpisu.

## Selektywna pamięć współdzielona `CaseObjectMapCacheShared` (stan na 2026-11-03, praca wstrzymana na prośbę autora)

Zaimplementowane (niezacommitowane, nieprzetestowane end-to-end): `SharedCaseObjectStore` (próg kosztu `mercury.cache.caseObject.shared.minCostMs`, domyślnie 25 ms; uczony koszt typu EWMA 0,2 i lista ciężkich spraw; asynchroniczny zapis; nieaktywna, gdy pamięć nie jest klastrowa; wyłączenie `mercury.cache.caseObject.shared.enabled=false`), integracja w `CaseObjectMapCache` (nowe przeciążenia `getCaseObject/putCaseObject` z `typeKey` i kosztem) i `CaseBusiness.transform2MrcObject` (pomiar kosztu), alias `CaseObjectMapCacheShared` (128 MB, `ttl` 3600) w sześciu `ehcacheDefault.xml` (16 MB w teście `mercury-srv`), test `SharedCaseObjectStoreTest` (6 OK).

**Błąd znaleziony przy teście (mercury-lib):** `MrcObject.propertyNamesLock` jest `final transient` z inicjalizacją w deklaracji, więc po deserializacji Javy ma wartość `null` i `getPropertyNames()` kończy się `NullPointerException` (dotyczy też `MrcPage`, `MrcPagedResult`, `MrcPagingParams`). Obiekt odczytany z pamięci współdzielonej jest bezużyteczny. Poprawka w `MrcObject` (pole niefinalne + `readObject`) jest zrobiona na gałęzi `hgdb-118` w `mercury-lib`, test `MrcObjectSerializationTest` w `mercury-srv-api` jeszcze się nie kompiluje (konstruktor `MrcPagingParams` ma inne parametry; moduł kompiluje się ze `-source 1.5`, bez try-with-resources).

**Ostrzeżenie:** do czasu wydania poprawki w `mercury-lib` włączona pamięć współdzielona z nowymi jarami `mercury-srv` może zgłaszać `NullPointerException` dla ciężkich spraw (koszt > 25 ms). Do tego czasu nie wdrażać nowego `mercury-srv` z aliasem `CaseObjectMapCacheShared` albo ustawić `mercury.cache.caseObject.shared.enabled=false`.

**2026-11-03: poprawka `MrcObject` w `mercury-lib` gotowa** (gałąź `hgdb-118`, niezacommitowana): `propertyNamesLock` niefinalne + `readObject` odtwarzające blokadę po deserializacji. Test `MrcObjectSerializationTest` (3 OK: obiekt po serializacji ma poprawne `getPropertyNames`/`getPropertyValue`, można go zmieniać, `MrcPagingParams` działa po odczycie). Po lokalnym wydaniu `mercury-lib` wymagane: podniesienie `mercury.static.version` w `mercury`, wdrożenie jarów i WAR, dopiero wtedy test selektywnej pamięci współdzielonej na ciężkich sprawach.

## Po wdrożeniu poprawki `MrcObject` i konfiguracji klastrowej (2026-11-03, 21:04 start Tomcata)

- Błąd startu Tomcata `InvalidServerStoreConfigurationException (existing 16777216, desired 134217728)`: magazyn `CaseObjectMapCacheShared` o 16 MB utworzył test `CacheMeasureTest` (`mercury-srv/src/test/resources/ehcacheDefault.xml` miał 16 MB, konfiguracja serwera 128 MB). Magazyn usunięty z Terracotty (`destroyCache`), rozmiar w teście wyrównany do 128 MB; `tc-config.xml` bez zmian. Zasada: ten sam alias musi mieć identyczny rozmiar `clustered-dedicated` we wszystkich konfiguracjach (serwer, profile, testy).
- Start po poprawce: czysto, `Pamięć współdzielona 'CaseObjectMapCacheShared' włączona: próg 25 ms`, folder główny CMIS odtworzony.
- **Koszt zapisów przy regionach klastrowych (Windows, localhost):** `createFolder` w pustym folderze, 35 wywołań: **p50 189 ms** (min 145, p90 255, max 436) wobec 90 ms przy pamięciach lokalnych (pomiar z 2026-11-02, inne warunki). Narzut ok. 100 ms zgodny z kilkunastoma operacjami Terracotty po 13–15 ms na zapis (znaczniki czasu Hibernate: wstępne i końcowe unieważnienie na tabelę). Do rozstrzygnięcia: porównanie A/B z regionem znaczników czasu lokalnym albo wyłączoną pamięcią zapytań oraz pomiar na Linuksie.
- **Selektywna pamięć współdzielona, węzeł 2 (proces testowy) działa na prawdziwych sprawach `FSMServiceOrder`:** przekształcenie 48–65 ms, po wyczyszczeniu pamięci lokalnej to samo `find` wraca z pamięci współdzielonej w 5–16 ms (po poprawce `MrcObject`); wszystkie 28 właściwości sprawy mają identyczne rozmiary po serializacji (całość 63011 B wobec 62956 B: różnica 55 B w strukturze obiektu zewnętrznego).
- **Klucz obiektu** zawiera dekodowanie, formaty, poziom zagnieżdżenia, **locale i strefę czasową**: wpisy dzielą tylko żądania z takim samym kontekstem. Sonda kluczy: sprawa przekształcona przez Tomcata (REFRESH, REST) została odczytana przez węzeł 2 tylko dla kontekstu `pl_PL` / `Europe/Warsaw` (trafienie w 15,7 ms wobec 84–112 ms przy chybieniach), czyli REST uzupełnia te ustawienia domyślnymi wartościami serwera.
- **Kierunek węzeł 2 → Tomcat nie trafił** (żądania 3 i 4 po REST: 93–122 ms jak zimne przekształcenie; w logu Tomcata brak wpisów `SharedCaseObjectStore`). Hipoteza: na rozgrzanym Tomcacie samo przekształcenie (bez ładowania encji) trwa poniżej progu 25 ms, więc Tomcat nie uznaje typu za ciężki i nie sięga do pamięci współdzielonej (zachowanie zgodne z założeniem selektywności, ale do potwierdzenia pomiarem w Tomcacie). Dodane logowanie decyzji (INFO przy zmianie klasyfikacji typu, DEBUG dla pominięć, chybień i próbek kosztu) w `SharedCaseObjectStore`; do ponownego testu po wdrożeniu z `mercury.cache.caseObject.shared.minCostMs=5`.
- `CacheManagerRest/getCachesStatistics` zwraca `NullPointerException` (błąd istniejący wcześniej, niezwiązany z tą zmianą).

## Klucz obiektu spraw był różny w każdym JVM (2026-11-03, 22:10)

Test z `minCostMs=5` na Tomcacie (start 21:31): Tomcat uczył się typów (log INFO „uznany za ciężki”: `FSMServiceOrder` średnio 318,7 ms przy pierwszym zimnym przekształceniu, `FSMServiceOrderExtendedDetails` 89,2 ms, `FsmAgreement` 34 ms itd.; koszty są **łączne z podobiektami**) i sięgał do pamięci współdzielonej, ale wszystkie odczyty były chybieniami („wpis brak”), mimo że wpisy istniały na serwerze Terracotty (potwierdzone niezależnym czytnikiem Ehcache pod dokładnie tym kluczem) i że bezpośredni odczyt przez `IObjectCache` w węźle 2 zwracał wpis, a znaczniki czasu wpisu i sprawy były równe.

**Przyczyna:** `CaseBusiness.createTransform2MrcObjectKey` (i analogicznie `CaseHistoryStreamBusiness`) liczył skrót klucza z `decodeResultMethod.hashCode()`; dla enuma `hashCode()` to skrót tożsamości obiektu, **inny w każdym uruchomieniu JVM**. Klucz był więc stabilny tylko wewnątrz jednego procesu (stąd poprawna pamięć lokalna), a nigdy nie zgadzał się między węzłami ani po restarcie. Poprawka: `decodeResultMethod.name().hashCode()` (formaty, locale, strefa i poziom są stałe: skróty łańcuchów i liczb).

**Weryfikacja:** dwa osobne procesy węzła 2: proces A zapisał ciężką sprawę (`FSMServiceOrder.5818002`, kontekst `pl_PL`/`Europe/Warsaw`), świeży proces B w sondzie kluczy trafił w pamięć współdzieloną tylko dla tego samego kontekstu (**30 ms** wobec 111–173 ms przy chybieniach), pozostałe warianty kontekstu (bez locale, tylko strefa, `en_US`) słusznie chybiły. Do potwierdzenia po wdrożeniu jara `mercury-srv` na Tomcacie: kierunek węzeł 2 → Tomcat (REST `CaseBusinessRest/find`, log `Trafienie w pamięć współdzieloną`).

**Uwaga o progu:** koszty w logu Tomcata są łączne z podobiektami (np. `FSMServiceOrder` 319 ms zawiera 11 typów zagnieżdżonych), a typy zagnieżdżone też trafiają do pamięci współdzielonej, jeśli przekraczają próg; przy opóźnieniu Terracotty ok. 15 ms próg 25 ms jest rozsądnym minimum, a niższe wartości (5 ms) zapełniają pamięć wpisami, których odczyt jest droższy niż przekształcenie.

## Wynik: Terracotta na Linuksie i test węzeł 2 → Tomcat (2026-11-03, wieczór)

**Opóźnienie Terracotty (mikrotest `Bench`, wpisy 2/5/16/56 KB):**
| Klient → serwer | zapis p50 | odczyt (inny klient) p50 |
|---|---|---|
| kontener Linux → serwer Linux (`devops-box-01`, Docker, autor) | 0,55–0,88 ms | 0,26–0,37 ms |
| JVM Windows → serwer Linux (`devops-box-01.hgdb.org:9510`) | 12,5–13,6 ms | 12,8–15,6 ms |
| JVM Windows → serwer Windows (localhost) | 12,9–14,0 ms | 13,3–15,5 ms |

Narzut 13–15 ms wynika ze strony **klienta Java na Windowsie** (nie serwera i nie rozmiaru wpisu); sztuczka z wątkiem `Thread.sleep(Long.MAX_VALUE)` (rozdzielczość zegara) go nie usuwa. Na Linuksie koszt operacji jest ok. 40 razy mniejszy, więc regiony klastrowe (znaczniki czasu Hibernate, transakcje globalne) kosztują na zapis rzędu kilku ms, a nie ok. 100 ms jak na dev. Pomiar `createFolder` (189 ms) dotyczy więc tylko środowiska dev na Windowsie; pomiar zapisu na Tomcacie pod Linuksem nie był wykonany.

**Selektywna pamięć współdzielona potwierdzona między węzłami:** węzeł 2 (proces testowy) zapisał trzy ciężkie sprawy `FSMServiceOrder` (kontekst bez locale i strefy, jak w REST), a Tomcat po REST `CaseBusinessRest/find` trafił w pamięć współdzieloną **3 razy, 0 chybień** (log: `Trafienie w pamięć współdzieloną ... koszt przekształcenia 59/67/59 ms`); czas żądań 44–55 ms wobec 115–290 ms przy zimnym przekształceniu (lokalne trafienie: ok. 31–37 ms). Klucz zależy od locale i strefy: REST przekazuje je jako `null`, więc węzły dzielą wpisy tylko dla żądań z takim samym kontekstem (wpis zapisany dla `pl_PL`/`Europe/Warsaw` nie jest widoczny dla żądania bez tych pól).

**Progi:** przy opóźnieniu ok. 0,3 ms (Linux) odczyt z pamięci współdzielonej (z deserializacją 0,4–1,6 ms) kosztuje ok. 1–2 ms, czyli poniżej typowego przekształcenia (3,3–4,6 ms; 11 ms typy średnie; 63 ms `FSMServiceOrder`). Na produkcji na Linuksie sensowny jest próg ok. 5 ms (`mercury.cache.caseObject.shared.minCostMs`), na dev (Windows, 13–15 ms) zostaje 25 ms.

## Decyzje autora (2026-11-03, wieczór) i plan

- **CaseMapper (przekazywanie dokumentów Lucene)** robimy w tym zadaniu (118). Plan szczegółowy: `tasks/hgdb/plan-2026-11-04.md`.
- **Pomiar zapisu na Linuksie** (`createFolder` itd.) przeniesiony do osobnego zadania **226**, po 211; porównamy wyniki z pomiarami z 118.
- Zrestartowany Tomcat; podsumowanie dnia: `tasks/hgdb/podsumowanie-2026-11-03.md`.

## Przekazywanie dokumentów Lucene między węzłami (2026-11-04, niezacommitowane)

### Rozpoznanie (odczyt kodu) i decyzje autora

- **Bufor zmian:** `MLucSaveBufferLogicSupport.save` zawsze **wstawia nowy wiersz** (nowe `id` z sekwencji). Metoda `getNotProcessesByMatterId`, która miała łączyć zmiany tej samej sprawy, nie jest nigdzie wywoływana (wcześniejsze przypuszczenie o aktualizacji w miejscu było błędne). SCN nadaje sekretarz przy pobraniu paczki (`CaseSaveBufferScnSeq`), a `LucCaseSaveBufferLogicHelper.optimalization` scala wiersze tej samej sprawy w paczce w jeden wpis (`R` wygrywa, `I` wypiera `U`, źródła się sumują).
- **Tożsamość dokumentu = id sprawy + SCN paczki** (bez DDL i bez nowego tokena). Paczka wysyłana w JMS jest już zoptymalizowana, więc para jest unikalna i taka sama u nadawcy i odbiorców. Zmiana po pobraniu paczki trafia do następnej paczki (nowy SCN) i wywołuje ponowne mapowanie; sprawa w aktywnej transakcji wraca do bufora z `scnNumber=null` i dostaje nowy SCN. Decyzja autora: wariant bez DDL, wysyłka JMS po mapowaniu.
- **Kolejność w sekretarzu** (`LucCaseSaveBufferBusiness.processNextPackage`) była: wysyłka JMS, potem własne mapowanie. Przy włączonym przekazywaniu: mapowanie i publikacja dokumentów, czekanie na zapisy (`flush`), dopiero potem JMS i obudzenie. Przy wyłączonym zostaje stara kolejność.
- Pełne mapowanie nie zależy od `sources` (pamięć dokumentów wyłączona w kodzie, `createNewInstance`); `sources` wpływa tylko na to, co `findForIndex` inicjalizuje.
- Rodzaje pól wytwarzane przez mapowanie: `TextField`, `StringField`, `StoredField` (tekst, liczby, bajty), punkty `Int/Long/Float/DoublePoint`, DocValues `SortedNumeric/Sorted/SortedSet`.

### Zaimplementowane

- `SharedStoreSupport` (`mercury-core-server`): wspólna część magazynów współdzielonych (zapis asynchroniczny, liczniki, `isClustered`, `flush`); `SharedCaseObjectStore` rozszerza ją (6 testów OK).
- `org.mercury.lucene.handoff` (`mercury-lucene-indexes-api`): `SerializableDocument` (odwzorowanie `Document`, nieobsługiwane pole to `UnsupportedFieldException`), `SharedLuceneDocumentStore` (region `CaseMapperShared`, klucz `caseId|scn`, parametr `mercury.cache.luceneDocument.shared.enabled`), `ICaseDocumentHandoff` (`take`/`offer`, `NONE`), `HandoffRole` (`NONE`/`PUBLISHER`/`CONSUMER`).
- `CaseIndexer.updateIndexByKeys(..., handoff)` (nowe przeciążenie, w `ICaseIndexer` metoda domyślna): gotowy dokument albo mapowanie i publikacja; `MLuceneIndexerSupport.addDoc/updateDoc` z gotowym dokumentem.
- `CaseIndexerBusinessSupport.updateIndex(..., HandoffRole)`, `ICaseIndexerBusinessInternal`, `CaseIndexerBusinessUpdateCallable`, konsument JMS (`CONSUMER`), sekretarz (`PUBLISHER`, kolejność jak wyżej).
- Region `CaseMapperShared`: `heap` 100 + `clustered-dedicated` 128 MB, `ttl` 600 s, w 7 plikach `ehcacheDefault.xml` (serwer dev, `scichy`, `scichy-test`, testy `mercury-srv` i `mercury-srv-slave`, `mercury-cmd`, `mercury-docker`). **Rozmiar identyczny wszędzie.**

### Wyniki

Testy: `SerializableDocumentTest` (4 OK: pola i wyniki wyszukiwania/sortowania w `RAMDirectory` identyczne po serializacji Javy), `SharedLuceneDocumentStoreTest` (5 OK: sekretarz publikuje, odbiorca pobiera tylko dla tej samej paczki, inny SCN to chybienie, odbiorca nie publikuje, nieobsługiwane pole pomijane), testy modułów `mercury-lucene-indexes*` zielone (121, 10 pominiętych kluczem).

Pomiar na 883 sprawach `mercury-db-test` (`CacheMeasureTest`, `measure.clean=false`, `measure.dataset=false`, Windows):

| Wielkość | średnia | p50 | p90 | p99 | max |
|---|---|---|---|---|---|
| mapowanie dokumentu `convert2Document` (ms) | 5,07 | 4,53 | 7,21 | 11,7 | 42,1 |
| `findForIndex` (ms) | 0,90 | 0,83 | 1,19 | 1,89 | 6,25 |
| serializacja dokumentu przekazania (ms) | 0,073 | 0,066 | 0,102 | 0,166 | 0,332 |
| odtworzenie dokumentu (ms) | 0,123 | 0,106 | 0,156 | 0,252 | 6,71 |
| rozmiar po serializacji Javy (B) | 4613 | 4715 | 5697 | 8286 | 11 553 |
| suma długości pól dokumentu (B) | 2515 | 2485 | 3136 | 5614 | 7884 |

Wszystkie 883 dokumenty się odwzorowują (bez nieobsługiwanych pól). Rozmiar po serializacji to ok. 1,8 raza suma długości pól (narzut Javy), więc szacunek bufora dla importu: 500 dok/s × 120 s × 4,6 KB ≈ 276 MB, więcej niż 128 MB regionu; nadmiar wypiera eksmisja (brakujące wpisy to zwykłe mapowanie). Do rozważenia: kompresja albo zwięzła serializacja.

Region na prawdziwej Terracotcie (30 spraw, ten sam proces): `CaseMapperShared` utworzony jako klastrowy, 30 z 30 dokumentów opublikowanych i odczytanych z kompletem pól (zapisy 30, nieobsługiwane 0). Odczyty trafiały w warstwę `heap` tego samego procesu, więc to nie jest pomiar opóźnienia sieci.

Oczekiwany zysk po stronie odbiorcy: koszt mapowania (ok. 5 ms) zastępuje odczyt (ok. 0,3 ms na Linuksie) i odtworzenie (ok. 0,12 ms), więc rzędu 4,5 ms na sprawę (≈ 90%). Na Windowsie (13–15 ms na operację) przekazywanie dokumentów jest wolniejsze niż mapowanie; środowisko docelowe to Linux, pomiar w zadaniu 226.

### Nie sprawdzone

- Dwa prawdziwe węzły z JMS (sekretarz publikuje, drugi węzeł pobiera z Terracotty): wymaga wdrożenia WAR i drugiego węzła.
- Zmiana kolejności w sekretarzu (mapowanie przed JMS) i rola `CONSUMER` w konsumencie JMS nie mają testu integracyjnego.
- Import hurtowy (tryb z zadania 114): przekazywanie działa tak samo jak w trybie zwykłym; decyzja, czy omijać je dla paczek hurtowych, jest otwarta.

### Zmiany pomocnicze w testach

`CacheMeasureScenario`: pobiera mapper z indeksera (bez ładowania zestawu danych mapper nie miał wstrzykniętego menedżera ról, `NullPointerException` w `GroupCaseMapper`), mierzy przekazanie dokumentu (`hand_ser_ms`, `hand_deser_ms`, `hand_size_B`) i sprawdza przekazywanie na prawdziwym regionie (`checkDocumentHandoff`).

### Test dwóch węzłów (2026-11-04, 12:24)

`LuceneHandoffScenario` / `LuceneHandoffTest` (`mercury-srv-slave`; klucz `test.skip.package.LuceneHandoffTest` w `scichy-test`, w `scichy` do dopisania): węzeł 1 = Tomcat z nowym WAR (log: `Przekazywanie dokumentów Lucene włączone`, region `CaseMapperShared` utworzony), węzeł 2 = proces testowy (`node2`, klaster, wspólne: baza, Terracotta, ActiveMQ). Węzeł 1 utworzył 6 folderów CMIS (`createFolder`); jego sekretarz zmapował sprawy i opublikował dokumenty, a węzeł 2 jako odbiorca paczek JMS pobrał je z Terracotty: **trafienia 6, chybienia 0, własne zapisy 0**. Log Tomcata w czasie testu: 0 wpisów `ERROR`/`WARN`. Foldery usunięte (`deleteTree`).

Uwagi: łączne liczniki węzła 2 po teście to trafienia 7, chybienia 4 (4 chybienia dotyczą paczek sprzed punktu odniesienia testu, czyli odbiorca zmapował sprawy sam, zgodnie z założeniem awaryjnego mapowania). Test nie weryfikuje osobno zawartości indeksu węzła 2 (trafienie oznacza, że dokument został użyty w `addDoc`/`updateDoc`). Rola `master` indeksu była `null` (żaden węzeł nie ogłosił się masterem), więc oba węzły mogły pełnić rolę sekretarza; w tym przebiegu publikował Tomcat.

Nadal nie sprawdzone: scenariusz odwrotny (sekretarzem jest węzeł 2, odbiorcą Tomcat), import hurtowy, opóźnienie na Linuksie.

## Dokumentacja (2026-11-04, docusaurus-hgdb, niezacommitowane)

EN i PL (sprawdzone kompilacją MDX): nowa strona `005_Configuration/Cache_configuration.mdx` (warstwy, pliki Ehcache, regiony klastrowe i zasada identycznego rozmiaru, szablony i wygasanie, selektywne współdzielenie obiektów spraw z parametrami, przekazywanie dokumentów, opóźnienie Terracotty, monitorowanie); `004_API/001_Context` (wiersz `cacheUsage`, wiersz `cache.refresh.layers`, sekcja „Odświeżanie pamięci podręcznych według warstw”); `003_Architecture/003_Index_Lucene` (sekcja „Przekazywanie dokumentów między węzłami”); `005_Configuration/index` (pozycje listy zaznaczone ✅). `docs/obserwacje.md`: pozycje 142–148. OpenAPI: opisy `schema.Context.cacheUsage` i `schema.Context.requestProperties` uzupełnione w `openapi-docs_en.properties`; **tłumaczenia `de`/`es`/`fr`/`ko` do uzupełnienia przez translator (`localization-project`)**, strony docusaurus w `es`/`fr`/`ko`/`de` również. `docker/terracotta/README.md`: suma regionów 388 MB, stan „uruchomiony na devops-box-01”.

## Pozostało do zamknięcia 118

- Autor: dopisać klucze `test.skip.package.CacheClusterTest=true`, `CacheMeasureTest=true` (`mercury-srv`, `mercury-srv-slave`) i `LuceneHandoffTest=true` do profilu `scichy`; przywrócić `mercury.cache.caseObject.shared.minCostMs` na 25 na Tomcacie dev; commity (`mercury`, `mercury-lib`, `sccommon`, `mercury-docker`, `mercury-cmd`, workspace, docusaurus).
- Nie sprawdzone: odwrotny kierunek przekazywania dokumentów (sekretarz = węzeł 2), test na żywo warstw `LUCENE` i `ATTRIBUTES`, import hurtowy, opóźnienie na Linuksie (zadanie 226).
- Rytuał zamknięcia: wydanie `mercury` (PR, merge, tag), potem `master`, `git pull`, nowa gałąź.

### Test dwóch węzłów: kierunek odwrotny (2026-11-04, 12:38)

`LuceneHandoffScenario` z `-Dhandoff.reverse=true`: węzeł 2 (proces testowy) wstawił do bufora indeksu 6 zmian istniejących spraw (`updateIndexByCaseIds`), jego sekretarz zmapował je, opublikował dokumenty w `CaseMapperShared` (zapisy 6, nieobsługiwane 0) i wysłał komunikat JMS (SCN 50602). Tomcat jako odbiorca: w logu (`org.mercury.lucene.handoff` na DEBUG ustawione przez REST na czas testu, potem `inherit`) **6 trafień, 0 chybień, 0 wpisów `ERROR`/`WARN`**. Oba kierunki przekazywania dokumentów potwierdzone. Skrypt: `scratchpad/handoff_reverse.sh` (token OAuth czytany w locie z konfiguracji dev, niewypisywany).

### Stan do rytuału zamknięcia (2026-11-04)

`minCostMs` przywrócone na 25 w profilu `scichy` (`mercury-server/src/main/config/scichy/.../mercury.properties` i wygenerowanej kopii); klucze `test.skip.package.*` w profilu `scichy` są (`CacheMeasureTest`, `CacheClusterTest`, `LuceneHandoffTest`). Niezacommitowane w `mercury`: tryb odwrotny `LuceneHandoffScenario` i `minCostMs`. Niewypchnięte: `mercury-lib` `hgdb-118` (3 commity, bez tagu 3.0.4.21), `mercury` `hgdb-118` (12 commitów), `mercury-docker` (7), `mercury-cmd` (8), docusaurus (1), workspace (55). `sccommon` 2.0.0.4 wydany (PR #15, tag), zmiany w katalogu roboczym to tylko końce linii w 5 plikach `pom.xml`.
