# Podsumowanie 2026-11-03

## Zamknięte

- **049 CMIS** (etapy 1–3): wersjonowanie dokumentów (`checkOut`, `checkIn`, `cancelCheckOut`, `getAllVersions`, `createDocumentFromSource`,
  `deleteObject` z `allVersions`), dokumentacja 007_CMIS (EN i PL), smoke test na Tomcacie. Wydane: `mercury-lib` 3.0.4.20, `mercury` 3.0.4.12 (PR #34 i #223).
  Luki zapisane w `TASK.md`: wersjonowanie klientem Workbench/Atom, test pliku zdalnego na dwóch węzłach, przegląd `MrcCaseHeaderField.values()`.

## 118 Pamięci podręczne (w toku, główny temat dnia)

**Zrobione i sprawdzone**
- `cache.refresh.layers` (`BUSINESS`, `DAO`, `LUCENE`, `HTTP`, `ATTRIBUTES`): klient z `REFRESH` odświeża domyślnie tylko warstwę biznesową, serwer odświeża wewnętrznie wszystkie warstwy (`CacheRefresh.refreshAll`). Testy jednostkowe (`CacheRefreshTest`, `DAOSupportRefreshLayerTest`).
- Ostrzeżenie `EhCache.java:256`: poprawka w `sccommon` (`isTimeToLiveChangeable`), wydane `sccommon` 2.0.0.3.
- **`CustomExpiryPolicy` (sccommon 2.0.0.4):** odczyt wpisu przedłużał jego życie do 24 h, więc TTL z definicji parametru działał tylko dla wpisów, których nikt nie czytał. Poprawione; szablon `default` dostał `CustomExpiryPolicy`, bo pamięci dynamiczne wcześniej **nie miały żadnego wygasania**. Nowa metoda `getCache(nazwa, szablon)` i szablon `attribute-values` (lokalny).
- **Pamięci nie były klastrowe:** `clustered-store` bez zasobu klastrowego niczego nie współdzieli. Dodano `clustered-dedicated` dla `default-update-timestamps-region` (4 MB), `CaseGlobalTransactionCache` (64 MB), `CaseMetadataCache` (64 MB) i `CaseObjectMapCacheShared` (128 MB) w 12 plikach XML. Test na dwóch węzłach (`CacheClusterScenario`): pamięci współdzielone, zapis na jednym węźle unieważnia zapytania na drugim.
- **`MrcObject` po deserializacji był nieużyteczny** (`propertyNamesLock` `final transient`): poprawka w `mercury-lib` 3.0.4.21 z testem.
- **Klucz obiektu spraw zależał od `hashCode()` enuma** (różny w każdym JVM): poprawka `name().hashCode()`. Po niej Tomcat trafia w wpisy zapisane przez węzeł 2 (3 trafienia, 0 chybień, 44–55 ms wobec 115–290 ms zimnego przekształcenia).
- **Selektywna pamięć współdzielona** (`SharedCaseObjectStore`): do klastra trafiają tylko obiekty o zmierzonym koszcie przekształcenia ≥ progu (`mercury.cache.caseObject.shared.minCostMs`, 25 ms), zdalny odczyt tylko dla ciężkich spraw i typów (uczony koszt, średnia wykładnicza 0,2), zapis asynchroniczny, klucz zależy od locale i strefy czasowej.
- **Pomiary** (zestaw 116 i `FSMServiceOrder`): przekształcenie sprawy 3,3–4,6 ms średnio, `FSMServiceOrder` ok. 63 ms (łącznie z podobiektami 319 ms przy zimnym starcie), `MrcObject` 4,6 KB średnio i 63 KB max, dokument Lucene 2,1 KB średnio i 8 KB max, mapowanie dokumentu 6,6–9,5 ms.
- **Terracotta:** klient Java na Windowsie ma 13–15 ms na operację niezależnie od serwera, klient na Linuksie 0,3–0,9 ms. Kompozycja `docker/terracotta` (serwer i `bench`) działa na `devops-box-01.hgdb.org`.
- Analiza i rekomendacje: `118-…/analiza-pamieci-klaster.md`.

**Otwarte w 118:** przekazywanie dokumentów Lucene (`CaseMapper`) między węzłami (plan na jutro), dokumentacja (docusaurus) dla `cache.refresh.layers`, szablonów i `CaseObjectMapCacheShared`, test na żywo warstw `LUCENE` i `ATTRIBUTES`, commity i wydanie `mercury`.

## Nowe zadanie

- **223** Pomiar zapisu sprawy na Linuksie (Tomcat i Terracotta): po zadaniu 211, porównanie z wynikami 118.

## Moje błędy dnia (zapisane, żeby się nie powtórzyły)

- Test `CacheMeasureTest` wyczyścił `mercury-db-test` i usunął folder główny CMIS (przywrócił go restart Tomcata); utworzył też magazyn `CaseObjectMapCacheShared` o innym rozmiarze, który zablokował start Tomcata (`InvalidServerStoreConfigurationException`). Rozmiar `clustered-dedicated` musi być identyczny we wszystkich konfiguracjach (serwer, profile, testy).
- `docker builder prune -f` na Twoim Docker Desktop usunął 17 GB nieużywanego cache budowania (obrazy i woluminy bez zmian).
- Błędne wnioski, które wycofałem: ustawienie loggera w `logback.xml` „nie działa”; „REST uzupełnia locale i strefę” (to było przypadkowe trafienie enumowego skrótu); pamięci „lokalne” oceniane po jednym pliku XML.

## Stan repozytoriów (do sprawdzenia rano `git status`)

- `mercury` (gałąź `hgdb-118`): zmiany po ostatnim commicie to m.in. poprawka klucza (`decodeResultMethod.name()`), logowanie w `SharedCaseObjectStore`, rozmiar 128 MB w XML testu `mercury-srv`, `CacheMeasureScenario`/`CacheMeasureTest` (sonda kluczy), klucz `test.skip.package.CacheMeasureTest=true` w `scichy-test` (w `scichy` dopisać samemu).
- `mercury-docker`, `mercury-cmd`: tylko pliki `ehcacheCommon.xml` i `ehcacheDefault.xml`.
- `mercury-lib` 3.0.4.21 i `sccommon` 2.0.0.4 wydane (potwierdzone przez autora).
- Workspace: `docker/terracotta/` (nowe), `tasks/hgdb/223-…` (nowe), ten plik i `plan-2026-11-04.md`.
