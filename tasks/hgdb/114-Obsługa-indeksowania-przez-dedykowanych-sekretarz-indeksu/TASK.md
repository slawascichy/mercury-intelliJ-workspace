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
