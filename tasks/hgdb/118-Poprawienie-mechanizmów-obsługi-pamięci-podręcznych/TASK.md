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

- `ehcacheDefault.xml` (używany przez `cache.configPath`) deklaruje blok `terracotta:cluster`, ale żadna pamięć nie ma zasobu klastrowego (`clustered-*`): wszystkie mają `heap`/`offheap`, czyli są **lokalne dla węzła**. Terracotta jest więc połączona, lecz pamięci nie są współdzielone (przypuszczenie: do potwierdzenia w kodzie `sccommon-cache` i testem na dwóch węzłach).
- Unieważnienie między węzłami istnieje tylko dla definicji (JMS: `ParamDefinitionRegistryChangesReceiver`, `TypeCaseRegistryChangesReceiver`, `TypeParamRegistryChangesReceiver` czyszczą pamięci zapytań) oraz `TypeCodeDAO.evictSecondLevelCache`. Dla spraw (encja `Case` nie ma `@Cacheable(false)`) nie znaleziono unieważniania między węzłami poza TTL (`CaseObjectMapCache`: 300 s) i porównaniem znaczników czasu w `CaseDAO.find`, które czyta encję z lokalnego regionu Hibernate. Do sprawdzenia: czy regiony encji są włączone (fabryka `ScEhCacheRegionFactory`; brak `shared-cache-mode` w konfiguracji).
