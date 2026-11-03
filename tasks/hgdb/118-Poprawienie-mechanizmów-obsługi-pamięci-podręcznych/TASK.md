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
