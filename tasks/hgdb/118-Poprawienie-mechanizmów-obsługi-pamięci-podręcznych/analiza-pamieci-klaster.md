# 118: analiza, które pamięci podręczne powinny być współdzielone w klastrze

Stan: 2026-11-03, rozpoznanie z kodu `mercury`, `mercury-lib`, `sccommon` i logu węzła 1 (47 pamięci utworzonych w `EhcacheManager`). Wnioski niepotwierdzone testem oznaczono jako przypuszczenie. Podstawa: obecnie żadna pamięć nie jest klastrowa (patrz `TASK.md`, „Analiza klastra”).

## 1. Najważniejsze fakty z kodu

1. **`CacheSharing.SHARED` w konstruktorach pamięci oznacza jedną instancję w JVM, a nie współdzielenie w klastrze** (`CacheSharing`: „istnieje tylko jedna instancja kesz-a”). Z tej deklaracji nie wynika zamiar klastrowania.
2. **Definicje typów i atrybutów nie leżą w pamięciach Ehcache**, więc sama zmiana XML ich nie obejmie:
   - listy typów węzła (`ICaseTypesManager`, `IDocumentTypesManager`) to struktury w JVM, odświeżane przez flagę ustawianą z JMS (`TypeCaseRegistryChangesReceiver`),
   - definicje atrybutów to `AttributeTypeParameterFactory.attributies` (zwykły `HashMap`), usuwane i przeładowywane z bazy po wiadomości JMS (`ParamDefinitionRegistryChangesReceiver`).
   - W Ehcache leżą tylko: `CaseMetadataCache` (metadane `TypeCase` po id), pamięci wartości słownikowych atrybutów (jedna pamięć na definicję parametru, np. `CalendarEventType`) i pamięci zapytań Hibernate.
3. **Hibernate**: żadna encja nie ma `@Cacheable(true)`, 21 ma `@Cacheable(false)`. W logu węzła 1 nie ma regionów encji, są tylko regiony zapytań (`default-query-results-region`, `StandardQueryCache`, `default-update-timestamps-region`, `MSubType.NamedQueryCacheName`). Pamięć zapytań jest więc włączona bez pamięci encji.
4. **Unieważnianie między węzłami istnieje tylko dla definicji** (JMS, wiadomości z zadania 082). Dla pozostałych pamięci (wyniki zapytań Hibernate, odpowiedzi HTTP, wyniki wyszukiwania) unieważnianie jest lokalne: `CasesParamsSaver` czyści `MQueryManager` i `BQueryManager` tylko na węźle, który wykonuje zapis.
5. **Pamięć dla transakcji globalnych została zaprojektowana pod klaster.** `CaseTransactionManager` mówi o pamięci klastrowej wprost („jak jest klaster pamięci podręcznych to metoda ta jest niewspierana”), a `CaseGlobalTransactionCache` służy do sprawdzania, czy sprawa jest w aktywnej transakcji (`containsInActiveTransactions`, używane przez monitoring indeksu Lucene).
6. Wartości w pamięciach to `Element` (`Serializable`), a przekazywane obiekty (`CaseGlobalTransactionObject`, `CaseLocalTransactionObject`) są `Serializable`. Dla pozostałych kandydatów serializowalność wartości trzeba sprawdzić.

## 2. Rekomendacja

### Priorytet 1: poprawność danych między węzłami

| Pamięć | Co przechowuje | Dziś | Rekomendacja |
|---|---|---|---|
| `default-update-timestamps-region` | znaczniki czasu ostatniej zmiany tabel (Hibernate) | lokalna: zapis na węźle B nie unieważnia wyników zapytań zbuforowanych na węźle A | **współdzielić.** Hibernate porównuje czas wyniku zapytania ze znacznikiem tabeli, więc przy wspólnym regionie znaczników węzeł A uzna swoje wyniki za nieaktualne po zapisie z B, a same regiony wyników mogą zostać lokalne. Brak TTL (nie może wygasać). Mały region. |
| `CaseGlobalTransactionCache` | spraw w aktywnych transakcjach globalnych (kluczem jest id sprawy) | lokalna: indekser na innym węźle nie widzi transakcji trwającej na węźle zapisującym (przypuszczenie, nie sprawdzono na dwóch węzłach) | **współdzielić.** To główny kandydat wynikający z projektu kodu. |

### Priorytet 2: definicje typów i atrybuty (Twój pierwszy cel)

| Element | Gdzie żyje | Dziś | Rekomendacja |
|---|---|---|---|
| `CaseMetadataCache` | pamięć Ehcache; metadane `TypeCase` po id | JMS usuwa wpis na każdym węźle | **współdzielić** (jedna kopia, brak zimnego startu węzła). JMS `remove` zostaje (nie szkodzi). Warunek: `TypeCase` i jego graf muszą być serializowalne (do sprawdzenia). |
| Pamięci wartości słownikowych atrybutów (`CalendarEventType`, `CalendarMonth`, `GroupCase2ParticipantRole`, `Source`, `CmisIsImmutable`, `CmisIsMajorVersion` i kolejne) | pamięci Ehcache tworzone dynamicznie z szablonu `default`, TTL z `ParamDefinition.timeToLiveSeconds` | lokalne; po zmianie definicji każdy węzeł przeładowuje po JMS | **współdzielić** przez szablon `default` (kolejne definicje parametrów dostaną ten sam zasób). Uwaga: `clustered-dedicated` w szablonie rezerwuje osobną pulę dla każdej takiej pamięci, więc trzeba dobrać rozmiar albo użyć puli współdzielonej (`clustered-shared`, wymaga zgodnej `server-side-config`, nieprzetestowane). |
| Listy typów węzła, mapa `attributies` (definicje) | struktury w JVM, nie Ehcache | synchronizowane JMS | **bez zmian w XML.** Zmiana wymagałaby zmiany kodu (przeniesienie do pamięci Ehcache). Proponuję zostawić JMS (działa, mały koszt) i wrócić do tematu po ocenie poprawności tej ścieżki. |
| Named query caches definicji (`MType`, `MSubType`, `MTypeCode`, `MTypeParam`, `MParamDefinition` `.NamedQueryCacheName`) | wyniki zapytań o definicje | JMS czyści je lokalnie na węzłach | po współdzieleniu znaczników czasu poprawność jest zapewniona, pamięci mogą zostać lokalne. Czyszczenie po JMS zostaje. |

### Priorytet 3: opcjonalnie (wydajność, bezpieczeństwo)

| Pamięć | Uwagi | Rekomendacja |
|---|---|---|
| `SystemUserCache`, `SecurityContext` | dane użytkowników i kontekstu bezpieczeństwa | współdzielić tylko jeśli profil obciążenia to uzasadnia (przypuszczenie: każdy węzeł może odczytać z bazy). |
| `OAuthFactory` | tokeny dostępu; przy braku w pamięci token jest czytany z bazy | zostaje lokalna (baza jest źródłem prawdy); współdzielenie tylko dla ograniczenia odczytów. |
| `CaseLobPropertyCache` | klucz to MD5 treści, wpisy niezmienne | bezpieczna do współdzielenia (brak unieważniania), ale wartości LOB mogą być duże: rozmiar do oceny. |
| `default-query-results-region`, `org.hibernate.cache.StandardQueryCache` | wyniki zapytań | lokalne przy współdzielonych znacznikach czasu. Współdzielenie dałoby wspólny wynik, ale bez pamięci encji zapytania i tak ładują encje pojedynczo (N+1), więc korzyść jest mała. |

### Zostają lokalne

| Pamięć | Powód |
|---|---|
| `CaseObjectMapCache` (150 000), `CaseMapper` (150 000) | duże; `CaseObjectMapCache` waliduje wpis znacznikiem czasu sprawy, więc lokalna jest poprawna |
| `HttpResponseCache_*` (19 pamięci, TTL 120 s), `QueryResultsManager_*`, `BQueryManager`, `MQueryManager`, `LuceneQueryManager` | krótkotrwałe wyniki żądań i wyszukiwań; stale dane ograniczone TTL. Lokalne czyszczenie w `CasesParamsSaver` nie obejmuje innych węzłów: do oceny, czy TTL wystarcza |
| `CaseLocalTransactionCache` | transakcje lokalne węzła (id transakcji unikalne na węźle) |
| `MercurySecurityOAuthConfig` | konfiguracja czytana z pliku XML na każdym węźle |
| `MercuryCore` | region domyślny; zawartość zależy od użycia (do sprawdzenia, co w nim leży, zanim zostanie zmieniony) |

## 3. Uwagi do konfiguracji

- Pamięć klastrowa wymaga zasobu w `<eh:resources>`: `<terracotta:clustered-dedicated unit="MB">N</terracotta:clustered-dedicated>` obok `heap` (sprawdzone: `heap`, `heap`+`offheap` oraz `clustered-dedicated` działają razem w Ehcache 3.6.1). `clustered-store` zostaje (spójność `strong`). `heap` pozostaje lokalną warstwą przy kliencie.
- Serwer Terracotty ma zasób `primary-server-resource` 512 MB (`tc-config.xml` w kicie serwera dev); suma `clustered-dedicated` wszystkich pamięci musi się w nim zmieścić, a `secondary-server-resource` ma 96 MB.
- Dla pamięci tworzonych dynamicznie (atrybuty, `CaseMetadataCache` i inne z `ObjectWithCacheSupport`) konfigurację dziedziczy szablon `default` w `ehcacheCommon.xml`/`ehcacheDefault.xml`; pamięci z własnym `alias` (np. `default-update-timestamps-region`, `CaseGlobalTransactionCache`) trzeba zmienić każdą osobno.
- Zmiana pamięci istniejącej nazwy z lokalnej na klastrową na działającym serwerze Terracotty może wymagać usunięcia starego wpisu (`destroyCache`); nie sprawdzono, jak zachowuje się taka zmiana przy ponownym starcie.

## 4. Proponowany plan po akceptacji

1. Zmiana XML tylko dla priorytetu 1 i `CaseMetadataCache` oraz szablonu `default` (po decyzji o rozmiarze), testy na dwóch węzłach: scenariusz `CacheClusterScenario` rozszerzyć o `CaseGlobalTransactionCache` i `default-update-timestamps-region`.
2. Test spójności zapytań: węzeł 1 zapisuje sprawę, węzeł 2 wykonuje to samo zapytanie przed i po zapisie (oczekiwany wynik: węzeł 2 widzi zmianę bez czekania na TTL), z wspólnym i bez wspólnego regionu znaczników czasu.
3. Dopiero po tym decyzja o priorytecie 3 i o przeniesieniu definicji z map JVM do pamięci Ehcache.
