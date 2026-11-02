# [114] Obsługa indeksowania przez dedykowanych sekretarz indeksu

https://github.com/slawascichy/hgdb/issues/114

Obecnie jest tylko jedna kolejka obsługująca zmianę. Przy imporcie dużej paczki danych dochodzi do jej zagłodzenia, wysycenia zadań indeksacji a tym samym zakłócenia bieżącej pracy.

## Pomiary (2026-11-02, gałąź `hgdb-049`, `mercury-db-test`, jeden węzeł, PostgreSQL)

Narzędzie: rozszerzony `LuceneVolumeScenario` (`LuceneVolumeTest`; `-Dperf.monitor=true`: stan bufora co 2 s i sonda opóźnienia, `-Dperf.reindex=true -Dperf.reindexEntries=N -Dperf.reindexChunk=1000`: wrzucenie N wpisów do bufora przez `LucCaseSaveBufferLogicHelper.updateIndexByCaseIds`). Test wymaga `test.skip.package.LuceneVolumeTest=false` w profilu (po pomiarze przywrócono). Sonda: co 10 s zapis jednej sprawy i czas do zniknięcia jej wpisu z bufora.

**Jak działa dziś (zweryfikowane w kodzie):**
- Wstawienie wpisu to zwykły `INSERT` bez wyszukiwania (`MLucSaveBufferLogicSupport.save`). Założenie „lekki bufor” jest spełnione po stronie zapisu.
- Sekretarz: jeden wątek, paczka 1000 wpisów (`IIteratedWorkActionTh.DEFAUTL_PACKAGE_SIZE`), zapytanie `scn_number IS NULL AND (skip_before ...)` bez `ORDER BY` i bez indeksu; optymalizacja tylko w obrębie paczki.
- Konwersja w paczce jest już równoległa: `CaseIndexerBusinessSupport.updateIndex` dzieli paczkę na 10 wątków (`TRHREAD_COUNTER`, `id % 10`) uruchamianych w głównej puli wątków (`MercuryPool`), wspólnej z zapisem spraw.

| Pomiar | Wstawianie | Opróżnianie | Największa zaległość | Opóźnienie zmiany bieżącej (sonda) |
| :--- | :--- | :--- | :--- | :--- |
| Import 5000 spraw `saveList` (paczki 200) | ok. 60 spraw/s (wąskie gardło: zapis spraw, 70 z 83 s) | nadąża (po zapisie 0 s) | 400 wpisów | 0,25–1,3 s |
| 20 tys. wpisów wrzuconych naraz | ok. 900 wpisów/s | ok. 600–750 wpisów/s | ok. 9 tys. | 4,6–8 s |
| 200 tys. wpisów wrzuconych naraz | ok. 1265 wpisów/s (158 s) | 713 wpisów/s (280 s łącznie) | 87 tys. | 9, 23, 45, 63, 89 s (rośnie z zaległością) |

**Wnioski:**
1. Zwykły import spraw przez `saveList` nie zagłodzi sekretarza: wąskim gardłem jest sam zapis spraw. Problem pojawia się przy masowym zasilaniu bufora wpisami (przebudowa indeksu po zmianie punktu zamontowania w CMIS, odświeżenie po zmianie typu, migracje), bo wstawianie jest szybsze niż opróżnianie.
2. Tempo opróżniania jest stałe (ok. 700 wpisów/s) niezależnie od zaległości (10 tys.: 750, 87 tys.: 713). Ograniczeniem jest przetwarzanie wpisów, a nie skanowanie bufora (przy 87 tys. wierszy skan bez indeksu nie zwolnił).
3. Zmiana bieżąca czeka na całą zaległość, bo bufor nie ma kolejności ani priorytetu: opóźnienie rośnie liniowo z zaległością (do 89 s przy 87 tys.).
4. Ekstrapolacja liniowa (przypuszczenie, nie zmierzone): 100 tys. wpisów to ok. 2,5 min; 1 mln to ok. 23 min opróżniania, z czego zmiana bieżąca mogłaby czekać do ok. 10 min (wstawianie 13 min przy 1265 wpisów/s, w tym czasie opróżnione ok. 560 tys.).
5. Nie zmierzono: skanu bufora przy 1 mln wierszy (martwe krotki, `VACUUM`), podziału czasu paczki (konwersja, zapis do indeksu, archiwizacja), wpływu na inne obciążenie głównej puli.

## Decyzja autora (2026-11-02): wariant B, bieżące zawsze pierwsze
Osobna tabela bufora dla wpisów hurtowych; jeden sekretarz; paczka z głównego bufora ma pierwszeństwo, hurtowy tylko gdy główny jest pusty (przed każdą paczką sekretarz sprawdza główny, więc zmiana bieżąca czeka najwyżej jedną paczkę hurtową). SCN i archiwum wspólne (backup bez zmian). **Otwarte:** kryteria, które wpisy są bieżące, a które hurtowe (propozycja w następnej sekcji).

## Realizacja: bufor hurtowy (2026-11-02, `hgdb-049`, niezacommitowane)

**Decyzje autora:** wariant B (osobna tabela); bieżące zawsze pierwsze; kryteria hurtowości: usunięcie zawsze bieżące, jawny znacznik w kontekście (`ContextRequestProperties.SaveRequestContext.BULK_INDEXING`, `saveRequestContext.bulkIndexing`, klient może go przesłać), próg liczby spraw w operacji (`mercury.lucene.bulkBuffer.threshold`, domyślnie 1000, `0` wyłącza); zmiana w `mercury-lib` na gałęzi `hgdb-049`.

**`mercury-lib`:** `SaveRequestContext.BULK_INDEXING`; encja `CaseSaveBufferBulk` (tabela `IGO_LUC_SAVE_BUFFER_BULK`, kolumny jak `IGO_LUC_SAVE_BUFFER`) z interfejsem `MLucCaseSaveBufferBulk` (w module `mercury-entities`, nie `mercury-core`: moduły `mercury` rozwiązują `mercury-core` z innej wersji niż encje, więc interfejs w `core` nie był widoczny). Generator dopisał `CaseSaveBufferBulkDto` (katalog `generated` nie jest w gicie; wymaga dwóch przebiegów budowania biblioteki: pierwszy generuje, drugi kompiluje).

**`mercury`:**
- `mercury-dao-api`/`mercury-dao`: `ICaseSaveBufferBulkDAO`/`CaseSaveBufferBulkDAO` (kopia DAO bufora bieżącego); identyfikatory z sekwencji bufora bieżącego (`CaseSaveBufferSeq`), bo przetworzone wpisy obu buforów trafiają do wspólnego archiwum z identyfikatorem jako kluczem.
- `LucCaseSaveBufferLogicHelper.isBulk(context, rozmiar, operacja)` i `getBulkThreshold()`; `LucCaseSaveBufferLogicCallable` (wstawianie po identyfikatorach i po sprawach) i `LucCaseSaveBufferLogic.insertList` (ścieżka agregująca używana przez `CasesParamsSaver`, `MrcCaseResultSaver`, `BpmDataTransformationHelperService`) kierują wpisy do bufora hurtowego (`insertBulk`); usunięcia zostają w buforze bieżącym. `CaseChangesRegistry.registerChangesInCase` oznacza rejestrację jako hurtową, gdy zmian jest więcej niż próg (znacznik w kontekście tylko na czas rejestracji).
- Sekretarz: `getNextPackageForIndexer` bierze paczkę z bufora bieżącego, a gdy nie ma w nim wpisów do przetworzenia, z hurtowego (`NextPackageForIndexer.bulk`); bufor bieżący jest sprawdzany przed każdą paczką, więc zmiana bieżąca czeka najwyżej jedną paczkę hurtową. `archivePackage(paczka, bulk)` usuwa wpisy z bufora, z którego pochodzą (odłożone na później wracają do niego). Stara sygnatura `archivePackage(paczka)` zastąpiona (jedyny wywołujący: `LucCaseSaveBufferBusiness`).
- Skrypt `db/postgresql/07_igo_luc_save_buffer_bulk.sql` (PostgreSQL ma `hibernate.hbm2ddl.auto=none`, więc tabelę trzeba utworzyć skryptem; Oracle, MySQL i MSSQL mają `update`, HSQL `create`, więc tabelę utworzy Hibernate; nie sprawdzano na tych bazach). Wykonany na `mercury-db-test`.
- Szablony `mercury.properties` w `mercury` (`jenkins`, `scichy`): zakomentowany `#mercury.lucene.bulkBuffer.threshold=1000`; w `mercury-cmd` i `mercury-docker` nie zmieniano. Dokumentacja: parametr `saveRequestContext.bulkIndexing` w `docusaurus-hgdb` (EN i PL, `004_API/001_Context`).

**Testy:** `BulkSaveBufferTest` (scenariusz `BulkSaveBufferScenario` na `mercury-db-test`, 1 z 1; klucz `test.skip.package.BulkSaveBufferTest=true` w `scichy-test`, do dopisania przez autora w profilu `scichy`): znacznik w kontekście, usunięcie zawsze bieżące, mała operacja bieżąca, próg (i `0` wyłączający), kolejność paczek (bieżąca, potem hurtowa), archiwizacja z obu buforów. Moduły `mercury-srv-slave`, `mercury-ws-server`, `mercury-ws-app` kompilują się.

**Pomiar po zmianie** (te same `perf.*`, `-Dperf.reindexBulk=true`, 200 tys. wpisów wrzuconych naraz, import hurtowy, sonda jako zmiana bieżąca):

| | przed (bufor jeden) | po (bufor hurtowy) |
| :--- | :--- | :--- |
| Opóźnienie zmiany bieżącej | 9, 23, 45, 63, 89 s (rośnie z zaległością) | 0,25–1,5 s przez cały import |
| Czas opróżnienia 200 tys. | 280 s (713 wpisów/s) | 277 s (719 wpisów/s) |
| Zaległość | 87 tys. w buforze bieżącym | do 77 tys. w hurtowym, bufor bieżący pusty |

Całkowita przepustowość się nie zmieniła (ok. 720 wpisów/s), a zmiany bieżące przestały czekać na import.

**Nie sprawdzono / do zrobienia:** backup indeksu z dociąganiem z archiwum przy zaległości w buforze hurtowym; praca w klastrze (JMS przekazuje paczkę po optymalizacji, więc przypuszczalnie bez zmian); skan bufora hurtowego przy 1 mln wierszy (martwe krotki); zachowanie wpisu `U` hurtowego dla sprawy usuniętej w międzyczasie; `ImportGenerator` i inne źródła masowe poza rejestracją przez `CaseChangesRegistry` i `insertList` (sprawdzić, czy trafiają tą ścieżką); instalacja ręczna: `mercury-lib` zbudowana jako 3.0.4.20, jar encji skopiowany do `D:\workspace\.m2`, pom rodzica w `.m2` odświeżony (kopia starego w scratchpadzie).

### Weryfikacja uzupełniająca (2026-11-02)
- **Backup i odtwarzanie indeksu:** oparte wyłącznie na archiwum i numerze SCN (`CaseIndexBackupAction` bierze `getMaxArchSCNumber`, `CaseIndexRestoreBackupAction`/`ArchCaseIndexerBusiness.reIndexCases` odtwarzają wpisy archiwum o SCN większym od backupu), więc nie zależą od tego, z którego bufora pochodzi wpis. Paczka hurtowa dostaje nowy SCN z tej samej sekwencji i trafia do tego samego archiwum; jeden cykl sekretarza używa SCN tylko dla jednego bufora. Bez zmian w kodzie backupu. `BulkSaveBufferScenario` sprawdza, że `getMaxArchSCNumber` obejmuje paczki z bufora hurtowego.
- **Wpisy dla spraw, których nie ma w bazie** (np. usunięte w międzyczasie): 3000 wpisów hurtowych dla nieistniejących spraw (`-Dperf.reindexMissing=true`) opróżniło się w 5 s bez wyjątków w dzienniku. Ta sama klasa sytuacji istnieje w buforze bieżącym (kolejność wpisów nie jest gwarantowana).
- **Regresja:** `SrvTest` z włączonymi scenariuszami `caseSaveBufferScenario`, `luceneBackupScenario`, `luceneBackupManagerScenario`, `luceneIndexerScenario`, `saveBufferLogicSupportUpdateSbScenario`: OK (profil `scichy-test`, plik przywrócony).
- **Sprzątanie testów:** `LogicScenarioHelper.cleanAllDataFromDB` czyści też bufor hurtowy.
- **Nadal niezmierzone:** skan bufora hurtowego przy 1 mln wierszy (martwe krotki), praca w klastrze (dwa węzły), migracje i propagacja zmian typów jako źródła masowe.

### Test na działającym serwerze dev (2026-11-02, Tomcat `node1`, `mercury.node.isClustered=true`, jeden węzeł; baza `mercury-db`)
Serwer w trybie klastrowym z jednym węzłem (ścieżka JMS i `NodeStatusMonitor` aktywna; drugiego węzła nie było). Wpisy hurtowe: 100 tys. wierszy dla nieistniejących spraw wstawionych wprost do `IGO_LUC_SAVE_BUFFER_BULK` (id od 910000000); zmiana bieżąca: `createFolder` przez CMIS (`tester`) co ok. 5 s, z pomiarem czasu do zniknięcia wpisu z bufora bieżącego.
- **Wynik (51 prób, drugi przebieg):** tworzenie folderu 0,63–0,73 s, wpis bieżący przetworzony po 0,6–1,65 s przez cały czas przetwarzania zaległości hurtowej; 100 tys. wpisów opróżnione w 267 s (ok. 375 wpisów/s razem z sondami). Bufor bieżący pusty po każdej próbie.
- **Pierwszy przebieg:** jedno żądanie `createFolder` trwało 39 s i zwróciło pustą odpowiedź (reszta prób: 0,3–0,8 s). W dzienniku (poziom INFO) brak wpisów z tego czasu; powtórzony przebieg (z zrzutem wątków przy opóźnieniu powyżej 4 s) nie odtworzył zjawiska. **Przyczyna nieustalona**; w pierwszym przebiegu działały równolegle zdublowane skrypty sondy (usunięte po przebiegu), więc możliwa kolizja po stronie testu, nie potwierdzona.
- **Wymóg wdrożeniowy:** na bazie bez tabeli `IGO_LUC_SAVE_BUFFER_BULK` (PostgreSQL, `hbm2ddl=none`) sekretarz zgłasza błąd `relation "igo_luc_save_buffer_bulk" does not exist` w każdym cyklu, w którym bufor bieżący jest pusty (zaobserwowane na `mercury-db` po wdrożeniu WAR, przed wykonaniem skryptu). Skrypt `db/postgresql/07_igo_luc_save_buffer_bulk.sql` trzeba wykonać przed uruchomieniem nowej wersji; wykonany na `mercury-db` (dev) i `mercury-db-test`.
- Sprzątanie: foldery sondy usunięte (`deleteTree`), wpisy testowe w archiwum (id od 900000000) usunięte, bufory puste.
- **Nie sprawdzone:** dwa węzły (przekazywanie paczki przez JMS do drugiego węzła, `remoteWork`).

### Test z dwoma procesami (2026-11-02): Tomcat jako węzeł 1 + `mercury-srv-slave` jako węzeł 2
Drugi Tomcat nie jest potrzebny: moduł `mercury-srv-slave` ma własną infrastrukturę testową (`SrvSlaveAbstract`, profil `scichy-test`: węzeł `node2`, własny indeks `lucene-test-node2`, ten sam ActiveMQ), więc test działa jako węzeł 2. Oba węzły muszą używać tej samej bazy, więc Tomcat został przełączony (przez autora) na `mercury-db-test`. Dodane: `BulkClusterScenario` i `BulkClusterTest` (klucz `test.skip.package.BulkClusterTest=true` w profilu; pom slave'a ma `maven.test.skip=true`, więc uruchomienie wymaga `-Dmaven.test.skip=false`). Do bazy testowej dodano ok. 3200 spraw (foldery CMIS na węźle 1).
- **Sprawdzone:** 20 tys. wpisów hurtowych wstawionych z procesu węzła 2 do wspólnej tabeli `IGO_LUC_SAVE_BUFFER_BULK` zostało przetworzonych przez sekretarza węzła 1 (Tomcat) w ok. 60 s; bufory puste po przebiegu.
- **Nie udało się sprawdzić (ograniczenie środowiska, nie wynik dotyczący bufora hurtowego):** czy węzeł 2 odbiera paczki przez JMS i uzupełnia swój indeks. Węzeł 1 nie zna procesu testowego jako węzła (w dzienniku Tomcata brak wzmianki o `node2`/`node3`; komentarz w `LuceneIndexerScenario` slave'a: testowy węzeł nie rozsyła `HEARTBEAT`), więc nie wysyła do niego paczek: także zmiana bieżąca (zwykłe `createFolder`) nie pojawiła się w indeksie węzła 2 w ciągu 60 s. Pełną wymianę paczek między dwoma węzłami da się sprawdzić tylko z dwoma Tomcatami (węzeł 2 z heartbeatem).
- **Stan ActiveMQ:** kolejka `mrc-lucene-document-registry-changes-node2` zawiera ok. 400 starych trwałych wiadomości z wcześniejszych prób (ok. 20 października i później). Węzeł 2 nie jest w stanie ich przetworzyć (`NumberFormatException: For input string: "Dot"` w `CaseHelper.getCaseIdLongPart`), a konsument nie potwierdza wiadomości, więc każda kolejna próba kończy się tym samym błędem i kolejka węzła 2 jest zablokowana. Wiadomości nie pochodzą z bufora hurtowego. Kolejkę trzeba opróżnić ręcznie w ActiveMQ (infrastruktura autora). Obserwacja do `docs/obserwacje.md`: wiadomość, której nie da się przetworzyć, blokuje kolejkę węzła (brak dead-letter, brak potwierdzenia przy błędzie).
- Czas `createFolder` na węźle 1 w tej serii wynosił ok. 3,3–3,8 s (wcześniej 0,65 s) także po opróżnieniu bufora hurtowego; przyczyna nieustalona (więcej spraw w bazie testowej, inne obciążenie albo wysyłka do nieznanych węzłów).

### Test z dwoma procesami, wersja końcowa (2026-11-02): Tomcat = `node1`, `BulkClusterTest` = `node2` z heartbeatem w wątku tła
Poprzedni wniosek („nie udało się sprawdzić wymiany paczek”) jest nieaktualny. Przyczyny braku wymiany były po stronie środowiska (obs. 138–140): kolejka `node2` blokowana przez nieprzetwarzalne stare wiadomości, statyczny routing `compositeQueue` tylko dla `node1` i `node2` (próba pod nazwą `node3` nie dostała nic), brak heartbeatu i odbiornika `WAKEUP` w kontekście testowym. `BulkClusterScenario` usuwa z kolejki `node2` wiadomości starsze niż godzina (641 przy pierwszym uruchomieniu), uruchamia w wątku tła heartbeat (`IHeartbeatSender`) i budzenie sekretarza węzła 2 co 3 s.
- **Wynik (20 tys. wpisów hurtowych, 8 sond):** bufor hurtowy opróżniony przez sekretarza węzła 1 w ok. 77 s; w tym czasie każda zmiana bieżąca (`createFolder` na węźle 1) trafiła do lokalnego indeksu węzła 2 po 0,2–3,5 s (mediana ok. 1,3 s), mimo zaległości hurtowej 20 tys. → 0. Paczki hurtowe i bieżące docierają do węzła 2 przez JMS tą samą drogą; bufor bieżący pusty po każdej próbie.
- Czas `createFolder` na węźle 1: 4,5–6,8 s w tym przebiegu (0,65 s w pojedynczym węźle bez bufora hurtowego i drugiego węzła); przyczyna nieustalona (więcej spraw w bazie testowej, praca węzła 2, wysyłka JMS).
- Błędy węzła 2 w dzienniku: `AlreadyClosedException` na początku (konsument działa równolegle z budową indeksu `buildFullIndex`) i `JMSException: InterruptedException` przy zamykaniu; bez wpływu na wynik.
- Uruchomienie: `mvn -o test -pl mercury-srv-slave -Dmaven.test.skip=false -Dtest=BulkClusterTest -Duser=scichy-test -Dcluster.entries=20000` z `test.skip.package.BulkClusterTest=false` w profilu; wymaga działającego Tomcata na tej samej bazie (węzeł 1), Terracotty i ActiveMQ.
