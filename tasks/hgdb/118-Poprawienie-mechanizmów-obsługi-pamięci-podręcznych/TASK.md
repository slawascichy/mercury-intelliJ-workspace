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
