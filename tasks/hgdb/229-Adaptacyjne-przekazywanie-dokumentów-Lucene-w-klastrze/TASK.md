# [229] Adaptacyjne przekazywanie dokumentów Lucene w klastrze (kolejność operacji sekretarza)

Status: **założone 2026-11-05**, wniosek z zadania 226 (etap 3).
https://github.com/slawascichy/hgdb/issues/229

## Po co

Zadanie 118 dodało przekazywanie gotowych dokumentów Lucene między węzłami (`CaseMapperShared`, `SharedLuceneDocumentStore`):
sekretarz mapuje sprawy na dokumenty, publikuje je w pamięci współdzielonej, a odbiorcy je pobierają zamiast mapować samodzielnie.
Pomiar na klastrze trzywęzłowym (`devops-box-01`, Linux, 3 węzły; zadanie 226, etap 3) pokazał, że przy obecnej kolejności operacji
mechanizm **wydłuża** czas, po którym zmiana jest widoczna w indeksach pozostałych węzłów.

## Stan obecny (kod: `LucCaseSaveBufferBusiness.processNextPackage`)

- Przekazywanie włączone (`mercury.cache.luceneDocument.shared.enabled` nieustawione = `true`, klaster, region klastrowy):
  1. `updateIndex(..., PUBLISHER)`: mapowanie, indeksowanie u sekretarza i publikacja dokumentów w pamięci współdzielonej,
  2. `awaitPublishedDocuments` (`store.flush()`),
  3. wiadomość JMS z paczką i sygnał wybudzenia.

  Odbiorca (`LuceneCaseSaveBuffersForIndexConsumer`): `updateIndex(..., CONSUMER)`; `handoff.take` pobiera gotowy dokument,
  brakujący mapuje samodzielnie.
- Przekazywanie wyłączone lub brak klastra: najpierw wiadomość JMS i wybudzenie, potem `updateIndex` u sekretarza; wszyscy
  pracują równolegle.

Praca w pierwszym wariancie jest szeregowa (mapowanie u sekretarza, publikacja, wiadomość, indeksowanie u odbiorcy), w drugim
równoległa.

## Dane z pomiaru 226 (etap 3; klaster 3 węzły, MASTER na node2, zapis na node2, p50 w ms)

Czas od końca zapisów do pojawienia się sprawy w indeksie Lucene węzła (narzędzie `226-…/mierz-indeks.py`):

| scenariusz | node1 | node2 (zapis, MASTER) | node3 |
|---|---|---|---|
| pojedyncza sprawa, przekazywanie włączone | 1119–1135 | 1026–1035 | 1112–1131 |
| pojedyncza sprawa, przekazywanie wyłączone | 1088–1112 | 1088–1097 | 1085–1110 |
| paczka 100 spraw, przekazywanie włączone | 774–785 | 334–352 | 777–837 |
| paczka 100 spraw, przekazywanie wyłączone | 447–485 | 447–460 | 447–454 |
| 3 × 100 spraw naraz (po 100 na każdy węzeł), przekazywanie włączone | 1520–1523 | 803–806 | 1449–1518 |
| 3 × 100 spraw naraz (po 100 na każdy węzeł), przekazywanie wyłączone | 1026–1146 | 1031–1080 | 1022–1086 |

Dla pojedynczej sprawy dolną granicę wyznacza cykl sekretarza (ok. 1 s, przypuszczenie), a różnica to ok. 25 ms. Dla paczki
100 spraw przekazywanie wydłuża czas do spójności indeksów odbiorców o ok. 300–350 ms (ok. +70%) i skraca o ok. 110 ms czas
u sekretarza. Nie zmierzono jedynego spodziewanego zysku: oszczędności CPU odbiorców.

## Propozycje zmian (do oceny po pomiarach)

1. **Dwie fazy w `updateIndex` sekretarza.** (1) mapowanie i publikacja dokumentów, (2) wysłanie wiadomości JMS, (3) zapis do
   własnego indeksu. Odbiorcy ruszają równolegle z zapisem sekretarza, a dokumenty są już w pamięci. Do sprawdzenia: czy
   mapowanie i zapis w `CaseIndexer` da się rozdzielić bez zmiany semantyki SCN i `cleanCache`.
2. **Strategia zależna od kosztu mapowania.** Sekretarz mierzy koszt mapowania pierwszych spraw paczki per typ (koszt per typ liczy
   już `SharedCaseObjectStore.typeCostNanos`; wg zasady rozszerzania istniejących rozwiązań wykorzystać ten sam mechanizm, nie
   budować nowego) i wybiera: tanie typy (poniżej progu): wiadomość od razu, bez publikacji dokumentów (jak M0); drogie typy:
   publikacja dokumentów przed wiadomością (jak M1), tylko dla nich. Próg jako parametr (nazwa do ustalenia; **to nie jest**
   `mercury.cache.caseObject.shared.minCostMs`, który dotyczy pamięci obiektów spraw, a nie dokumentów Lucene).
3. **Wybór wartości progu na podstawie pomiarów**, nie zgadywania: koszt mapowania typów z zestawu 116 (rozkład) oraz zużycie CPU
   odbiorców w paczce (zob. niżej).

## Pomiary do wykonania przed zmianą

- Koszt mapowania Case → dokument Lucene dla typów z zestawu 116 (`FSMServiceOrder`, `Contrahent`, …), najlepiej z logu
  `CaseIndexer` (poziom debug) albo z dodatkowego licznika: ile ms na sprawę i jak się to skaluje z liczbą powiązanych obiektów.
- Obciążenie CPU węzłów podczas paczki (`docker stats` na node1 i node3) w wariantach: przekazywanie włączone i wyłączone.
- Powtórzenie paczek 100 i 500 spraw na typie o wyższym koszcie mapowania (np. sprawa z dużą liczbą list i powiązań), żeby
  sprawdzić, od jakiego kosztu przekazywanie dokumentów zaczyna się opłacać także czasowo (po zmianie kolejności z pkt 1).

## Kryteria sukcesu

- Czas aktualizacji indeksów odbiorców w paczce 100 spraw nie dłuższy niż bez przekazywania (ok. 450–490 ms w pomiarze 226)
  przy mniejszym zużyciu CPU odbiorców.
- Dla pojedynczych spraw bez regresji względem wariantu bez przekazywania (ok. 1,1 s, dolna granica z cyklu sekretarza).
- Zachowana poprawność: żadna sprawa nie znika z indeksu odbiorcy (kontrola kompletności w `mierz-indeks.py`: 0 niekompletnych
  paczek).

## Zakres i zależności

- Repozytorium `mercury`: `mercury-srv` (`LucCaseSaveBufferBusiness`, `LuceneCaseSaveBuffersForIndexConsumer`),
  `mercury-lucene-indexes` (`CaseIndexer`), `mercury-lucene-indexes-api` (`SharedLuceneDocumentStore`). Testy:
  `SharedLuceneDocumentStoreTest` i nowe testy kolejności (atrapy sekretarza i odbiorcy).
- Zmiana kolejności w sekretarzu dotyczy wyłącznie klastra z włączonym przekazywaniem; konfiguracja dev i jednowęzłowa bez zmian.
- Narzędzia pomiarowe: `tasks/hgdb/226-…/mierz-indeks.py` (tryb `--batch`), warianty konfiguracji w `226-…/warianty`.

## Wyniki

### Pomiar CPU hosta podczas paczki (2026-11-06)

Źródło: `NodeMonitorRest/load` (`/mercury-ws-app/monitor/NodeMonitorRest/load`, pola `cpuTotalMillis` i `cpuIdleMillis` z `NodeStatusDto`, odświeżane z biciem serca co 5 s). Liczniki są **wspólne dla hosta** (trzy węzły na `devops-box-01` zwracają niemal identyczne wartości), więc mierzymy łączne zużycie CPU maszyny, a nie CPU poszczególnych węzłów. Narzędzie: `226-…/mierz-indeks.py --cpu`: 2 paczki rozgrzewkowe, potem 10 paczek po 100 spraw (z jednego węzła albo `--all-writers`: po 100 z każdego), bez kontroli kompletności i z rzadszym odpytywaniem indeksu (50 ms); CPU bazowe hosta bez obciążenia mierzone 20 s przed serią i odejmowane (`netto = zajęte − bazowe × okno`). Host ma ok. 16 rdzeni (okno 346 core-s na ok. 22 s). Wartości w core-s (sekundy CPU wszystkich rdzeni).

#### M1 (przekazywanie dokumentów włączone)

| scenariusz | przebieg | CPU bazowe | netto, 10 paczek | netto na paczkę |
|---|---|---|---|---|
| 1 węzeł × 100 spraw | 1 | 0,83% | 50,0 core-s | 5,00 core-s |
| 1 węzeł × 100 spraw | 2 | 2,53% | 37,3 core-s | 3,73 core-s |
| 3 węzły × 100 spraw | 1 | 1,56% | 159,3 core-s | 15,93 core-s |
| 3 węzły × 100 spraw | 2 | 2,50% | 147,0 core-s | 14,70 core-s |

Uwaga: CPU bazowe hosta waha się 0,8–2,5% (inne obciążenie maszyny), a zużycie netto różni się między przebiegami o ok. 25% (1 węzeł) i ok. 8% (3 węzły), więc pomiar ma duży rozrzut; do porównania z M0 potrzeba co najmniej 2 przebiegów każdego wariantu.


#### M0 (przekazywanie dokumentów wyłączone)

| scenariusz | przebieg | CPU bazowe | netto, 10 paczek | netto na paczkę |
|---|---|---|---|---|
| 1 węzeł × 100 spraw | 1 | 1,03% | 88,7 core-s | 8,87 core-s |
| 1 węzeł × 100 spraw | 2 | 1,18% | 53,8 core-s | 5,38 core-s |
| 3 węzły × 100 spraw | 1 | 1,32% | 187,0 core-s | 18,70 core-s |
| 3 węzły × 100 spraw | 2 | 1,12% | 147,3 core-s | 14,73 core-s |

#### Porównanie CPU hosta M1 i M0 (netto na paczkę, core-s; przebieg 1 / 2)

| scenariusz | M1 (przekazywanie włączone) | M0 (wyłączone) | M0 − M1 |
|---|---|---|---|
| 1 węzeł × 100 spraw | 5,00 / 3,73 | 8,87 / 5,38 | +3,9 / +1,7 (M0 zużywa o ok. 30–44% więcej) |
| 3 węzły × 100 spraw | 15,93 / 14,70 | 18,70 / 14,73 | +2,8 / 0,0 (M0 o 0–15% więcej) |

Wnioski:
1. **Przekazywanie dokumentów oszczędza CPU hosta, choć wynik jest zaszumiony.** Dla paczki z jednego węzła M1 zużywa o ok. 30–44% mniej CPU niż M0 (3,7–5,0 wobec 5,4–8,9 core-s na 100 spraw), w obu przebiegach kierunek jest ten sam. Dla 3 × 100 różnica jest mniejsza (0–15%): w drugim przebiegu równa. Rozrzut między przebiegami tego samego wariantu (do 40%) jest porównywalny z częścią różnicy, więc wynik traktować jako kierunek, nie wartość.
2. **Skala oszczędności zgadza się z kosztem mapowania.** Różnica 1,7–3,9 core-s na 100 spraw w scenariuszu z jednym zapisującym to ok. 17–39 ms CPU na sprawę dla dwóch odbiorców, czyli ok. 9–20 ms na odbiorcę, co mieści się w rzędzie mapowania `FSMServiceOrder` zmierzonym w zadaniu 118 (6,6–9,5 ms na typową sprawę, więcej dla ciężkich). W scenariuszu 3 × 100 oszczędność jest mała, bo CPU zdominował zapis (REST, baza) na trzech węzłach, a sekretarz mapuje wszystkie 300 spraw, więc odbiorca oszczędza tylko część mapowania.
3. **Cena to opóźnienie (zadanie 226, etap 3):** w M1 odbiorcy mają indeks później o 40–70% (paczka 100: 780–840 wobec 450–485 ms; 3 × 100: 1,5 wobec 1,1 s). Przekazywanie opłaca się więc CPU, nie czasowi. **To uzasadnia zmianę z tego zadania:** zmiana kolejności (wiadomość JMS przed zapisem do własnego indeksu sekretarza, ale po publikacji dokumentów) powinna zachować oszczędność CPU i zlikwidować większość kary czasowej.
4. **Ograniczenia pomiaru:** liczniki CPU są wspólne dla hosta (nie da się rozdzielić CPU na węzły ani odróżnić mapowania od zapisu do bazy i REST), baza zajmuje część CPU w obu wariantach, CPU bazowe maszyny zmienia się 0,8–2,5%. Do dokładnego rozdzielenia kosztu mapowania potrzebny jest licznik czasu mapowania w `CaseIndexer` (log na poziomie debug lub metryka), czego nie zrobiono.

### Analiza kodu (2026-11-06, gałąź `hgdb-229` w `mercury`)

**Przepływ u sekretarza (MASTER)** (`LucCaseSaveBufferBusiness.processNextPackage` → `CaseIndexerBusinessSupport.updateIndex`):
1. `getNextPackageForIndexer` (SCN), `optimalization` (jedna sprawa = jeden wpis).
2. `updateIndex(ctx, optimized, false, PUBLISHER)`: wpisy `R` (usunięcia) i wpisy spraw w aktywnej transakcji (zwracane do bufora z `skipBefore`) są obsługiwane osobno; pozostałe są grupowane w 10 zadań (`caseId mod 10`, `CaseIndexerBusinessUpdateCallable`). Każde zadanie, **w jednej pętli**, dla każdej sprawy: `findByIdList` (odczyt `Case` z bazy), `searchById` w indeksie (dodać czy zaktualizować), `documentFor` (mapowanie `convert2Document` i `offer` do pamięci współdzielonej, zapis asynchroniczny; wydawca nigdy nie czyta z pamięci: `take` zwraca `null`), `addDoc` lub `updateDoc` na wspólnym `IndexWriter`.
3. Po zakończeniu wszystkich zadań: `indexWriter.flush()` i `commit()`, `LuceneReaderPool.markChanged`, `setReadable()`.
4. `awaitPublishedDocuments` (`store.flush()`), potem `luceneCaseSaveBuffersForIndexSender.sendMesage(optimized)` (cała paczka, także wpisy pominięte) i `luceneWakeUpSender.sendMesage()`.
5. `archivePackage`.

**Przepływ u odbiorcy:** wiadomość wybudzenia (`LuceneWakeUpReceiver`) → `CaseIndexSecretaryHelper.wakeupLocalSecretary()` → wątek sekretarza (`CaseIndexSecretaryCallable.remoteWork`) → `LuceneCaseSaveBuffersForIndexConsumer.processNextPackage`: `receive(1000 ms)` paczki z kolejki `Consumer.<węzeł>.VirtualTopic…`, pominięcie własnej paczki, `updateIndex(..., CONSUMER)`: te same zadania i pętla, ale `documentFor` robi `take(caseId, SCN)` (brak dokumentu: mapuje sam), potem `addDoc`/`updateDoc` i `commit`. Odbiorca nadal czyta `Case` z bazy (potrzebny do `addDoc`), więc **oszczędza tylko mapowanie**, nie odczyt z bazy.

**Konsekwencje dla opóźnienia (zgodnie z pomiarami):** w M1 odbiorca startuje po zakończeniu całego `updateIndex` sekretarza (mapowanie, zapis, `commit`) i po `flush` pamięci, a dopiero potem dochodzi dostarczenie JMS, wybudzenie sekretarza odbiorcy, odczyt `Case` z bazy, `take`, zapis i `commit`. W M0 wiadomość wychodzi od razu, więc dostarczenie i wybudzenie nakładają się na pracę sekretarza, a mapowanie na odbiorcach jest równoległe. W M1 kara czasowa to więc suma: pracy zapisu i `commit` sekretarza, `flush`, dostarczenia JMS i wybudzenia; mapowanie u odbiorcy znika, ale nie odtwarza się czasowo, bo nie zastępuje szeregowości. Rozbicie tej sumy na składniki **nie zostało zmierzone** (potrzebne logi czasu na poziomie debug w `CaseIndexerBusinessSupport` i `LucCaseSaveBufferBusiness`, `/admin/loggers` pozwala je włączyć w trakcie pracy).

**Wariant A (rekomendowany pierwszy krok): trzy fazy u wydawcy.** (1) mapowanie wszystkich dokumentów paczki i `offer` (zadania wątkowe, bez `IndexWriter`), (2) `flush` pamięci współdzielonej i **wysłanie wiadomości JMS i wybudzenia**, (3) zapis dokumentów (z lokalnej mapy, bez ponownego mapowania i bez odczytu z pamięci współdzielonej) i `commit`. Dzięki temu odbiorcy startują, gdy sekretarz zapisuje swój indeks, a dokumenty są już w pamięci. Szczegóły:
- Zmiana w `CaseIndexer.updateIndexByKeys`: wyodrębnić mapowanie (`documentFor`) od zapisu (`addDoc`/`updateDoc`); nowa metoda mapująca zwraca mapę `caseId → Document` (i `Case`), druga zapisuje z tej mapy. Dokumenty ok. 2 KB średnio (max 8 KB), paczka rzędu setek spraw: pamięć nieistotna.
- `CaseIndexerBusinessUpdateCallable`: dwie fazy z barierą (`CountDownLatch`): po fazie mapowania wszystkich zadań wątek główny wykonuje wywołanie zwrotne (flush i wiadomość JMS), potem zadania zapisują.
- `CaseIndexerBusinessSupport.updateIndex` dostaje parametr wywołania zwrotnego (np. `Runnable onDocumentsPublished`), wywoływany dokładnie raz po fazie mapowania i przed zapisem; `LucCaseSaveBufferBusiness` przekazuje wysyłkę JMS zamiast wywoływać ją po `updateIndex`.
- Ścieżka bez przekazywania (M0, brak klastra) i ścieżka odbiorcy bez zmian.

**Wariant B (kolejny krok, jeśli A wystarczy w pomiarach): przekazywanie tylko dla drogich typów.** Uczony koszt mapowania per typ (średnia wykładnicza, jak w `SharedCaseObjectStore.typeCostNanos`), próg w parametrze (nazwa do ustalenia, np. `mercury.cache.luceneDocument.shared.minCostMs`; to nie jest `caseObject.shared.minCostMs`). Paczka złożona z tanich typów idzie ścieżką M0 (wiadomość od razu); drogie typy publikowane.

**Wariant C (nie rekomendowany teraz): wiadomość od razu, odbiorca czeka na dokumenty z limitem czasu.** Dokumenty pojawiają się w pamięci w trakcie mapowania, a odbiorca w `take` czeka krótko (limit), po czym mapuje sam. Złożony (limity czasu, ryzyko podwójnego mapowania), korzyść niepewna.

**Ryzyka i warunki poprawności:** (1) sprawy w aktywnej transakcji nie są mapowane (tak jak dziś są zwracane do bufora z `skipBefore`); wiadomość nadal zawiera całą paczkę, więc odbiorca sam je pominie; (2) usunięcia (`R`) robione tak jak dziś, przed zapisem; (3) błąd mapowania przed wysłaniem wiadomości: paczka nie jest archiwizowana i nic nie wychodzi do odbiorców (jak dziś przy błędzie `updateIndex`); (4) odbiorca może zacząć przed `commit` sekretarza: bez znaczenia dla poprawności (osobne indeksy); (5) klucz dokumentu to sprawa + SCN paczki, bez zmian; (6) `cleanCache` bez zmian.

**Testy:** jednostkowe: kolejność zdarzeń w `CaseIndexerBusinessUpdateCallable` (wywołanie zwrotne po `offer` wszystkich dokumentów i przed pierwszym `addDoc`, wywołane raz, także dla paczki z samymi usunięciami i samymi sprawami w transakcji), `SharedLuceneDocumentStoreTest` bez zmian; integracyjne: `mierz-indeks.py` w M1 po zmianie (kryteria sukcesu wyżej), kontrola kompletności (0 niekompletnych paczek) i zestaw 116 (`DatasetScenario`, `LuceneVolumeTest`).

### Implementacja wariantu A (2026-11-06, gałąź `hgdb-229` w `mercury`)

Zmiany (repozytorium `mercury`):
- `mercury-lucene-indexes-api`: nowa klasa `org.mercury.lucene.handoff.PreparedCaseDocuments` (przygotowane dokumenty paczki i identyfikatory spraw bez rekordu w bazie), `ICaseIndexer.prepareDocuments` i `writeDocuments` (metody `default`, rzucają `UnsupportedOperationException` dla innych implementacji).
- `mercury-lucene-indexes`: `CaseIndexer.updateIndexByKeys(…, handoff)` rozdzielone na `prepareDocuments` (odczyt spraw z bazy, `documentFor`: `take` albo mapowanie i `offer`) i `writeDocuments` (`searchById`, `addDoc`/`updateDoc`, usunięcie dokumentów spraw bez rekordu); stara metoda wywołuje je kolejno, więc ścieżki bez wywołania zwrotnego (M0, odbiorca, brak klastra, testy) działają jak dotąd.
- `mercury-srv`: `IDocumentsPublishedCallback` (wywołanie zwrotne po przygotowaniu wszystkich dokumentów), `CaseIndexerBusinessUpdateCallable.prepareTask()` i `writeTask()`, nowa klasa `CaseIndexerUpdateRunner` (faza przygotowania wszystkich zadań, wywołanie zwrotne dokładnie raz, faza zapisu; bez wywołania zwrotnego jedna faza), `CaseIndexerBusinessSupport.updateIndex(…, role, onDocumentsPublished)` (wywołanie także gdy paczka nie ma spraw do zmapowania), `ICaseIndexerBusinessInternal` (nowe przeciążenie), `LucCaseSaveBufferBusiness` (powiadomienie JMS i wybudzenie przeniesione do wywołania zwrotnego).
- Parametr `mercury.cache.luceneDocument.shared.notifyBeforeWrite` (domyślnie `true`): `false` przywraca poprzednią kolejność (powiadomienie po zapisie i `commit`), więc na tym samym buildzie można porównać obie kolejności bez zmiany obrazu.

Testy: `CaseIndexerUpdateRunnerTest` (4 testy: jedna faza bez wywołania, wywołanie dokładnie raz po wszystkich przygotowaniach i przed pierwszym zapisem, brak wywołania i zapisów po błędzie przygotowania, puste zadania), `SharedLuceneDocumentStoreTest` i `SerializableDocumentTest` bez zmian (9 testów) oraz `DatasetScenario` (indeksowanie zestawu 116 po refaktoryzacji: 1/1, wynik bez zmian). Test integracyjny na klastrze wymaga wydania `mercury` i obrazu (autor wydaje lokalnie; pakiet w `mercury-cmd` i obrazy buduję ja).

Poniżej: wyniki pomiaru po zmianie (do uzupełnienia po wdrożeniu na klaster).

### Pomiar po zmianie (2026-11-06, build 3.0.4.16)

Obraz `ibpm/mercury:mercury-hgdb-3.0.4.16` (digest `sha256:b048fd65…effe`), klaster 3 węzły na `devops-box-01`, MASTER na node2; te same narzędzia i parametry co wyżej (`mierz-indeks.py --cpu`, paczka 100 spraw z jednego węzła i 3 × 100 naraz, 10 paczek po 2 rozgrzewkowych, 2 przebiegi).

#### Stara kolejność na nowym buildzie (`notifyBeforeWrite=false`, `warianty/M1-po-zapisie`), czas do indeksu (p50, ms) i CPU

| scenariusz | przebieg | node1 | node2 | node3 | CPU netto na paczkę |
|---|---|---|---|---|---|
| 1 węzeł × 100 | 1 | 638 | 352 (zapis) | 630 | 9,08 core-s |
| 1 węzeł × 100 | 2 | 608 | 330 (zapis) | 610 | 4,47 core-s |
| 3 węzły × 100 | 1 | 1024 | 693 | 975 | 16,93 core-s |
| 3 węzły × 100 | 2 | 980 | 688 | 989 | 13,78 core-s |

**Uwaga (do wyjaśnienia):** wyniki starej kolejności na nowym buildzie są szybsze niż M1 na buildzie 3.0.4.15 w tym samym trybie pomiaru (odbiorcy 1 × 100: 608–638 ms wobec 826–907 ms; 3 × 100: 975–1024 wobec ok. 1500–1650 ms; węzeł zapisujący 330–352 wobec 442–476 ms), czyli zbliżone do M0 (odbiorcy 511–606 ms). Dwie możliwe przyczyny: (a) refaktoryzacja `updateIndexByKeys` (najpierw mapowanie całej grupy, potem zapis) przyspieszyła sam sekretarz, (b) przełącznik `notifyBeforeWrite=false` nie został zastosowany na węzłach i klaster pracuje już w nowej kolejności. Rozstrzygnięcie: potwierdzenie na węzłach (`grep notifyBeforeWrite /opt/mercury-3.0/config/mercury.properties`) i porównanie z wariantem A (domyślnym) po przestawieniu klastra.

#### Wariant A: nowa kolejność (konfiguracja domyślna, build 3.0.4.16), czas do indeksu (p50, ms) i CPU

(Etykieta w skrypcie `M0n`, błędnie nazwana podczas pomiaru; według autora klaster pracował bez override, czyli w M1 z nową kolejnością.)

| scenariusz | przebieg | node1 | node2 | node3 | CPU netto na paczkę |
|---|---|---|---|---|---|
| 1 węzeł × 100 | 1 | 809 | 792 (zapis) | 659 | 9,81 core-s |
| 1 węzeł × 100 | 2 | 583 | 610 (zapis) | 596 | 5,33 core-s |
| 3 węzły × 100 | 1 | 1109 | 1198 | 1150 | 20,38 core-s |
| 3 węzły × 100 | 2 | 1169 | 1293 | 1214 | 15,94 core-s |

#### Porównanie wszystkich wariantów (przebieg 2, czas do indeksu p50 w ms: najpóźniejszy węzeł; CPU netto na paczkę 100 spraw)

| wariant | 1 × 100: czas (najpóźniejszy węzeł) | 1 × 100: CPU | 3 × 100: czas | 3 × 100: CPU |
|---|---|---|---|---|
| M1 build 3.0.4.15 (przekazywanie, stara kolejność) | 826 | 3,73 | 1654 | 14,70 |
| M0 build 3.0.4.15 (bez przekazywania) | 511 | 5,38 | 1020 | 14,73 |
| stara kolejność, build 3.0.4.16 (`notifyBeforeWrite=false`) | 610 | 4,47 | 989 | 13,78 |
| **A: nowa kolejność, build 3.0.4.16** | 610 | 5,33 | 1293 | 15,94 |

**Wnioski (ostrożne: pomiary na różnych buildach i po osobnych restartach klastra, CPU bazowe hosta 1–2,5%, rozrzut CPU do 40%):**
1. **Nowa kolejność (A) nie poprawia czasu względem starej na tym samym buildzie:** dla 1 × 100 jest taki sam (610 ms, profil „wszystkie węzły naraz”: sekretarz kończy razem z odbiorcami, 592–610 ms, wobec 330–352 ms u sekretarza w starej kolejności), dla 3 × 100 jest gorszy (1293 wobec 989 ms). CPU w A jest taki sam albo wyższy (5,33 wobec 4,47 i 15,94 wobec 13,78 core-s). Zmiana kolejności samego powiadomienia nie usuwa wąskiego gardła.
2. **Prawdopodobne wąskie gardło (z kodu, niezmierzone):** publikacja dokumentów to `SharedStoreSupport.writeAsync`: **jeden** wątek zapisujący (`ThreadPoolExecutor(1, 1)`), każdy dokument osobnym `cache.put` do regionu `CaseMapperShared` z `consistency="strong"` (odpowiedź serwera Terracotty przed kolejnym zapisem). `store.flush()` przed wysłaniem JMS czeka, aż ten jeden wątek opróżni kolejkę, więc czas do powiadomienia odbiorców rośnie liniowo z liczbą dokumentów (przy ok. 2–5 ms na zapis: 100 dokumentów ok. 200–500 ms, 300 dokumentów ok. 600–1500 ms) i to on wyznacza czas, w którym odbiorcy startują, niezależnie od tego, czy sekretarz zapisuje własny indeks przed czy po powiadomieniu. W nowej kolejności zapis własny sekretarza dochodzi na końcu ścieżki (po `flush` i wysłaniu), stąd gorszy wynik sekretarza i, przy 3 × 100, odbiorców (rywalizacja o CPU i Terracottę).
3. **Porównanie ze starym buildem (M1 3.0.4.15 szybszy o ok. 40% po refaktoryzacji, M1po 610 wobec 826 ms) jest zaszumione**: inny stan środowiska (restart klastra, obciążenie hosta), więc nie przypisuję poprawy refaktoryzacji bez powtórzenia M1 na starym buildzie.

**Proponowane kolejne kroki (do decyzji autora):**
- **Pomiar rozbicia czasu u sekretarza** (jedna linia logu INFO na paczkę: czas mapowania, `flush`, wysyłki JMS, zapisu i `commit`, liczba dokumentów i zapisów z kolejki), żeby zmierzyć, ile trwa `flush` (potwierdzić lub obalić hipotezę z pkt 2). Logi z węzłów musi dostarczyć autor.
- **Przyspieszenie publikacji dokumentów:** (a) wiele wątków zapisujących w `SharedStoreSupport` (parametr, np. 4–8 dla `CaseMapperShared`; domyślnie 1 dla pamięci obiektów spraw), albo (b) jeden wpis na grupę spraw (`SCN` i numer grupy zadania) zamiast jednego na sprawę, z odczytem całej grupy przez odbiorcę (kilkadziesiąt razy mniej obiegów do serwera). Po poprawie pomiary A, M0 i starej kolejności ponownie.
- **Uwaga o kolejce:** `ArrayBlockingQueue(1000)` z `DiscardPolicy` odrzuca po cichu zapisy powyżej 1000 oczekujących (paczka ponad 1000 spraw publikowana nie w całości, odbiorca mapuje brakujące sam); do zapisania w obserwacjach.

### Implementacja: logi rozbicia czasu i wiele wątków zapisujących (2026-11-06, po pomiarze A)

Decyzja autora po pomiarze A: (1) logi rozbicia czasu u sekretarza i odbiorcy, (2) przyspieszenie publikacji dokumentów wieloma wątkami zapisującymi. Zmiany (repozytorium `mercury`, gałąź `hgdb-229`):
- **`SharedStoreSupport`** (obserwacja 159): parametr liczby wątków zapisujących (domyślnie 1, jak dotąd, dla `SharedCaseObjectStore`), `flush()` oparty na liczniku oczekujących zapisów (poprzedni zakładał jeden wątek: zlecenie zatrzaskowe w kolejce), licznik odrzuceń (pełna kolejka 1000) i łącznego czasu zapisów; metody `getWriteMillis`, `getDiscarded`, `getWriterThreads`.
- **`SharedLuceneDocumentStore`**: parametr `mercury.cache.luceneDocument.shared.writerThreads` (domyślnie 4, zakres 1–32), statystyki rozszerzone o czas zapisów, odrzucone i liczbę wątków.
- **Log sekretarza** (`LucCaseSaveBufferBusiness`): jedna linia na paczkę z przekazywaniem dokumentów (INFO od 20 wpisów, mniejsze paczki DEBUG): `[SCN:n] Sekretarz: paczka N wpisów, powiadomienie przed/po zapisem do indeksu: przygotowanie dokumentów X ms, flush pamięci X ms, wysyłka JMS i wybudzenie X ms, zapis do indeksu i commit X ms, razem X ms; pamięć współdzielona: zapisy +N (czas zapisów +X ms), odrzucone +N, wątki zapisujące N`. Dla kolejności „po zapisie” (`notifyBeforeWrite=false`) przygotowanie wynosi 0, a mapowanie i zapis są w jednym czasie.
- **Log odbiorcy** (`LuceneCaseSaveBuffersForIndexConsumer`): `Odbiorca: paczka N wpisów od węzła X: aktualizacja indeksu X ms, trafienia pamięci współdzielonej +N, chybienia +N` (trafienia to dokumenty pobrane z pamięci; chybienia oznaczają mapowanie na odbiorcy).
- Testy: `SharedStoreWritersTest` (4: `flush` czeka na zapisy z czterech wątków i wynik jest równoległy, jeden wątek, pełna kolejka z odrzuceniami bez zawieszenia `flush`, magazyn bez pamięci), `SharedCaseObjectStoreTest` (6) i `SharedLuceneDocumentStoreTest` (4), `CaseIndexerUpdateRunnerTest` (4) bez zmian.

Po wydaniu 3.0.4.17 autor porównuje: zależność czasu od liczby wątków (`writerThreads` 1, 4, 8; parametr w `mercury.properties` węzłów jak `notifyBeforeWrite`), nowa i stara kolejność, logi z węzłów (`docker logs … | grep -E "Sekretarz:|Odbiorca:"`).

### Pomiar po wielu wątkach zapisujących (2026-11-06, build 3.0.4.17, konfiguracja domyślna: nowa kolejność, `writerThreads=4`)

Ten sam tryb pomiaru (`mierz-indeks.py --cpu`, 10 paczek po 2 rozgrzewkowych, 2 przebiegi). Czas do indeksu (p50, ms) i CPU netto na paczkę 100 spraw:

| scenariusz | przebieg | node1 | node2 | node3 | CPU netto na paczkę |
|---|---|---|---|---|---|
| 1 węzeł × 100 | 1 | 530 | 609 (zapis) | 546 | 8,71 core-s |
| 1 węzeł × 100 | 2 | 466 | 494 (zapis) | 446 | 4,66 core-s |
| 3 węzły × 100 | 1 | 970 | 1111 | 1013 | 18,60 core-s |
| 3 węzły × 100 | 2 | 1009 | 1076 | 966 | 14,54 core-s |

Porównanie z A (jeden wątek zapisujący, ten sam build 3.0.4.16, przebieg 2): 1 × 100 najpóźniejszy węzeł **494 wobec 610 ms (ok. −19%)**, 3 × 100 **1076 wobec 1293 ms (ok. −17%)**; CPU netto 4,66 wobec 5,33 i 14,54 wobec 15,94 core-s (ok. −13% i −9%, w granicach rozrzutu). Wynik zbliża się do M0 (511 i 1020 ms na starym buildzie) i jest poniżej starej kolejności na 3.0.4.16 tylko dla 1 × 100 (610 ms); dla 3 × 100 stara kolejność (989 ms) jest nadal o ok. 90 ms szybsza. Poprawa jest więc wyraźna, ale umiarkowana (kilkanaście procent), a nie rzędu wielkości: **publikacja nie była jedynym składnikiem czasu**.

Do rozbicia składników potrzebne są logi z węzłów (`Sekretarz:` i `Odbiorca:`) z tego pomiaru i z wariantów `W1` (jeden wątek) i `W8` (osiem wątków): ile trwa `flush`, ile mapowanie, ile zapis i `commit`, jaka jest średnia długość zapisu do Terracotty (czas zapisów podzielony przez liczbę zapisów) i czy odbiorcy mają trafienia (CPU).

### Błąd `Cannot commit when autoCommit is enabled` na MASTER i wariant AC (2026-11-06)

**Znalezisko (autor, logi node2):** `PSQLException: Cannot commit when autoCommit is enabled` przy każdej archiwizacji paczki (ślad: `LucCaseSaveBufferLogic.archivePackage` → `ArchCaseSaveBufferDAO.insertList` → `AbstractDAO.insertList:330` → `commitTransaction:373` → `conn.commit()`). **Przyczyna:** szablon `context.xml.docker-init` obrazu nie ma `defaultAutoCommit="false"` dla `jdbc/MercuryDB` i `jdbc/MercuryDBCommon` (serwer dev ma), a JDBC DAO wywołuje `commit()` ręcznie. Ten sam brak jest w przykładzie `mercury-cmd/mercury-install-package/system-config-sample/linux/apache-tomcat/conf/context.xml`. Wystąpiło niezależnie od zadania 229 (kod archiwizacji bez zmian; od jakiej wersji obrazu, nie ustalono). Skutek danych: `igo_luc_save_buffer` ma 0 wierszy, a `igo_luc_arch_save_buffer` 145 375, więc archiwizacja działa (autocommit zatwierdza każde zapytanie osobno), a błąd pojawia się po fakcie. Skutki uboczne po wyjątku (zrzuty błędów `dumpErrorLog`, czas MASTER) **nie zostały sprawdzone w kodzie**.

**Poprawka na stałe (gałęzie `hgdb-229`, niezacommitowane):** `defaultAutoCommit="false"` dla `jdbc/MercuryDB` i `jdbc/MercuryDBCommon` w `mercury-docker/mercury-3.0/docker-init-config/apache-tomcat/conf/context.xml.docker-init` i w przykładzie `context.xml` w `mercury-cmd`. Do testu bez przebudowy obrazu: `warianty/AC` (zamontowany szablon `context.xml.docker-init`).

#### Wariant AC (konfiguracja domyślna 3.0.4.17 + `defaultAutoCommit=false`), czas do indeksu (p50, ms) i CPU

| scenariusz | przebieg | node1 | node2 | node3 | CPU netto na paczkę |
|---|---|---|---|---|---|
| 1 węzeł × 100 | 1 | 601 | 689 (zapis) | 634 | 8,76 core-s |
| 1 węzeł × 100 | 2 | 581 | 623 (zapis) | 597 | 5,22 core-s |
| 3 węzły × 100 | 1 | 1003 | 1101 | 1008 | 18,99 core-s |
| 3 węzły × 100 | 2 | 1001 | 1071 | 1019 | 14,59 core-s |

Porównanie z D4 (konfiguracja domyślna, przebieg 2, najpóźniejszy węzeł): 1 × 100 **623 wobec 494 ms**, 3 × 100 **1071 wobec 1076 ms**; CPU 5,22 wobec 4,66 i 14,59 wobec 14,54 core-s. **Poprawka autocommit nie skraca czasu do indeksu** (3 × 100 bez różnicy, 1 × 100 wolniej o ok. 130 ms, co jest w zakresie rozrzutu między seriami tego pomiaru, do 20%); sam błąd jest szumem w logu i kosztem pojedynczych wyjątków na paczkę, a nie głównym składnikiem czasu. Potwierdzenie zniknięcia błędu i rozbicie czasu sekretarza wymagają logów node2 z tego pomiaru (`grep -E "Cannot commit|Sekretarz:"`).

### Logi z węzłów po poprawce autocommit (wariant AC, 3.0.4.17, 2026-11-06 15:04–; pliki `226-…/AC_mercury-three-node-cluster-mercury-node{1,2,3}-1.log`)

Wcześniejsze logi (`M1_…`) odrzucone decyzją autora (węzły na niepewnym obrazie); poniżej tylko nowe. Wszystkie trzy węzły na 3.0.4.17: node2 ma 25 linii `Sekretarz:`, node1 i node3 po 79 linii `Odbiorca:`, błędu `Cannot commit` nie ma, `wątki zapisujące 4`, odrzuconych zapisów 0.

**Sekretarz (node2, 25 paczek, naprzemiennie duże ok. 250 i małe ok. 50 wpisów, kolejność „przed zapisem do indeksu”):**

| paczki | n | średni rozmiar | przygotowanie dokumentów | flush pamięci | JMS i wybudzenie | zapis do indeksu i commit | razem |
|---|---|---|---|---|---|---|---|
| duże (≥ 200 wpisów) | 12 | 249 | 429 ms | 0 ms | 13 ms | 308 ms | 753 ms |
| małe (30–80 wpisów) | 12 | 50 | 74 ms | 0 ms | 16 ms | 334 ms | 426 ms |

Zależność od rozmiaru paczki (regresja liniowa): przygotowanie ≈ −15 ms + 1,78 ms na wpis (równolegle na 10 wątkach), **zapis do indeksu i commit ≈ 343 ms + (−0,14) ms na wpis, czyli stałe ok. 300–350 ms niezależnie od rozmiaru**, razem ≈ 347 ms + 1,62 ms na wpis.

**Odbiorcy (node1 i node3, 158 paczek):** 19 120 trafień i **0 chybień** (przekazywanie dokumentów działa w pełni). Czas aktualizacji indeksu paczki ≈ **298 ms + 0,10 ms na wpis**: mediana 243 ms dla paczek ok. 45 wpisów, 321 ms dla ok. 90 i 300 ms dla ok. 243; czyli **także u odbiorcy dominuje stały koszt ok. 250–300 ms na paczkę, a nie praca na dokument**.

**Wnioski:**
1. **Hipoteza z pomiaru A obalona:** `flush` pamięci trwa 0 ms (zapisy dokumentów, ok. 1,1 ms na zapis przy 4 wątkach, kończą się w trakcie mapowania), wysyłka JMS i wybudzenie ok. 12 ms. Jeden wątek zapisujący byłby jednak wąskim gardłem: łączny czas zapisów to ok. 270 ms na 240 zapisów przy 4 wątkach wobec ok. 1000 ms przy jednym (zmiana wielowątkowa ma sens, ale nie jest głównym składnikiem czasu).
2. **Dominuje stały koszt zapisu do indeksu i `commit` na każdym węźle: ok. 300–350 ms na paczkę.** W wariancie M0 (bez przekazywania) odbiorca mapuje sam (ok. 1,8 ms na wpis równolegle), a potem płaci ten sam stały koszt; w M1 mapowanie znika, a stały koszt zostaje. Stąd brak zysku w czasie: koszt `commit` nakłada się u wszystkich węzłów równolegle, a przekazywanie oszczędza tylko mapowanie (CPU), co pasuje do wcześniejszych pomiarów (M1 i M0 o podobnym czasie, M1 o kilkanaście procent mniej CPU przy jednym piszącym węźle).
3. **Gdzie leży stały koszt, nie wiadomo:** możliwe źródła to `indexWriter.commit()` z `fsync` plików na woluminie z indeksem (`/opt/mercury/mercury-lucene-N`), `LuceneReaderPool.markChanged` i ponowne otwarcie czytnika, praca przygotowawcza `updateIndex` (`setUpdate`, `getCaseAttributes`, otwarcie czytnika). Do rozbicia potrzebny pomiar wewnątrz fazy zapisu (flush, commit, odświeżenie czytnika osobno) i test opóźnienia `fsync` dysku z indeksem.

**Proponowane kolejne kroki (do decyzji autora):** (a) test `fsync` na hoście: `dd if=/dev/zero of=<katalog indeksu>/dsync.test bs=4k count=500 oflag=dsync` (czas na zapis); (b) w kolejnej wersji dodać do logu czasy `flush`, `commit` i odświeżenia czytnika w `CaseIndexerBusinessSupport.updateIndex` (u sekretarza i u odbiorcy); (c) po ustaleniu składników rozważyć zmniejszenie stałego kosztu (rzadszy `commit` z odświeżaniem czytnika bez `commit`, większe paczki, szybszy dysk), co jest zmianą trwałości i wymaga osobnej decyzji.

### Test `fsync` dysku z indeksem i zapis dokumentów jednym wątkiem (2026-11-06)

**Test autora (devops-box-01, `dd … bs=4k count=500 oflag=dsync` w katalogach `/opt/mercury/mercury-lucene-{1,2,3}/index/Case`):** 500 synchronicznych zapisów w 2,55–2,59 s na każdym z trzech indeksów, czyli **ok. 5,1 ms na synchroniczny zapis** (ok. 800 kB/s). To wolny dysk (typowy SSD: poniżej 1 ms).

**Hipoteza (do potwierdzenia pomiarem):** `IndexWriter` ma osobny bufor (segment) na każdy wątek dodający dokumenty. Dotąd 10 zadań (`caseId mod 10`) mapowało i zapisywało dokumenty równolegle, więc paczka dawała do 10 segmentów, a `commit` synchronizuje na dysku pliki każdego z nich (kilka plików na segment, plus `segments_N` i katalog), po ok. 5 ms każdy. To tłumaczy stały koszt ok. 300 ms na paczkę niezależny od rozmiaru (zapis sekretarza 343 ms − 0,14 ms na wpis, odbiorcy 298 ms + 0,10 ms na wpis). Faza przygotowania jest już oddzielona od zapisu, więc zapis można wykonać **jednym wątkiem** (jeden segment na paczkę, kilka `fsync`).

**Zmiana (repozytorium `mercury`, gałąź `hgdb-229`):**
- `CaseIndexerUpdateRunner.run(pool, zadania, wywołanie zwrotne, writeThreads)` zwraca `Result` (liczba dokumentów, czasy: przygotowanie, wywołanie zwrotne, zapis). Faza 1 (przygotowanie, odczyt spraw i mapowanie lub `take`) jest równoległa jak dotąd; faza 2 (zapis do indeksu) przy `writeThreads=1` (domyślnie) idzie jednym wątkiem (wątek wywołujący), przy `n > 1` w co najwyżej `n` zadaniach, a `0` przywraca dawne zachowanie (bez wywołania zwrotnego jedna faza, z wywołaniem zwrotnym zapis jednym zadaniem na grupę). Dotyczy sekretarza, odbiorcy i ścieżki bez klastra.
- Parametr `mercury.lucene.indexer.writeThreads` (`CaseIndexerBusinessSupport`, domyślnie 1, zakres 0–32).
- Log `Indeks: paczka N wpisów: przygotowanie dokumentów X ms, wywołanie po przygotowaniu X ms, zapis dokumentów X ms (wątki zapisu: N), flush indeksu X ms, commit X ms, odświeżenie czytnika X ms, razem X ms` (INFO od 20 wpisów, mniejsze DEBUG), u sekretarza i u odbiorcy; rozdziela koszt `flush`, `commit` i odświeżenia czytnika.
- Testy: `CaseIndexerUpdateRunnerTest` (6: jedna faza dla `writeThreads=0`, wywołanie zwrotne raz po wszystkich przygotowaniach, zapis jednym wątkiem w wątku wywołującym po wszystkich przygotowaniach, najwyżej dwa wątki zapisu, błąd przygotowania bez wywołania i zapisu, puste zadania), `SharedStoreWritersTest` (4), `SharedLuceneDocumentStoreTest` (5), `DatasetScenario` na prawdziwym indeksie (1/1).

Po wydaniu 3.0.4.18: pomiar domyślny (`writeThreads=1`) i porównanie z `writeThreads=0` (dawne, wariant do wygenerowania z `warianty/utworz-wariant.sh`), logi `Indeks:`, `Sekretarz:`, `Odbiorca:` z węzłów. Oczekiwany efekt: `commit` z ok. 300 ms do kilkudziesięciu ms (kilka `fsync` zamiast kilkudziesięciu) u sekretarza i odbiorców.

### Pomiar na buildzie 3.0.4.18: zapis do indeksu jednym wątkiem (2026-11-06, konfiguracja domyślna, bez override)

Build 3.0.4.18 (obraz `sha256:accbfcc3…d59e`): nowa kolejność powiadomienia, `writerThreads=4`, **`mercury.lucene.indexer.writeThreads=1` (zapis do indeksu jednym wątkiem)**, poprawka `defaultAutoCommit`. Czas do indeksu (p50, ms) i CPU netto na paczkę 100 spraw:

| scenariusz | przebieg | node1 | node2 | node3 | CPU netto na paczkę |
|---|---|---|---|---|---|
| 1 węzeł × 100 | 1 | 400 | 335 (zapis) | 401 | 8,00 core-s |
| 1 węzeł × 100 | 2 | 371 | 333 (zapis) | 362 | 4,76 core-s |
| 3 węzły × 100 | 1 | 780 | 740 | 786 | 16,33 core-s |
| 3 węzły × 100 | 2 | 618 | 592 | 615 | 13,14 core-s |

**Porównanie przebiegu 2 (najpóźniejszy węzeł) z poprzednimi buildami:**

| wariant | 1 × 100 | 3 × 100 |
|---|---|---|
| M1 3.0.4.15 (stara kolejność, dawny zapis) | 826 ms | 1654 ms |
| M0 3.0.4.15 (bez przekazywania) | 511 ms | 1020 ms |
| 3.0.4.17 domyślny (4 wątki zapisu pamięci, nowa kolejność, dawny zapis do indeksu) | 494 ms | 1076 ms |
| **3.0.4.18 domyślny (zapis do indeksu jednym wątkiem)** | **371 ms** | **618 ms** |

Względem 3.0.4.17: **−25% (1 × 100) i −43% (3 × 100)** przy niezmienionym CPU (4,76 wobec 4,66 i 13,14 wobec 14,54 core-s). Względem M0 na 3.0.4.15: −27% i −39% (M0 na nowym buildzie nie zmierzono: zmiana zapisu do indeksu dotyczy także M0, więc porównanie z M0 wymaga jego pomiaru na 3.0.4.18). Zgodnie z hipotezą: zapis do indeksu jednym wątkiem (jeden segment na paczkę, kilka `fsync` zamiast kilkudziesięciu na dysku z 5 ms na synchroniczny zapis) usunął główny, stały składnik czasu. Potwierdzenie liczbowe i rozbicie wymagają logów `Indeks:` z węzłów.

Do wykonania na tym buildzie: logi z węzłów (`Indeks:`, `Sekretarz:`, `Odbiorca:`), wariant `WR0` (`writeThreads=0`, dawny zapis wieloma wątkami: izoluje wpływ zmiany) oraz M0 (przekazywanie wyłączone) dla uczciwego porównania.

#### Logi z węzłów na 3.0.4.18 (pliki `226-…/18_mercury-three-node-cluster-mercury-node{1,2,3}-1.log`)

node2: 21 linii `Sekretarz:` (20 z przygotowaniem > 0), node1 i node3: po 78 linii `Odbiorca:`, błędu `Cannot commit` brak. **Linii `Indeks:` (rozbicie flush, commit, odświeżenie czytnika) w plikach nie ma**: do wyjaśnienia, czy nie zostały zebrane (wzorzec `grep`), czy nie są wypisywane (kod wywołuje `logIndexTiming` po `commit` przy `INFO` dla paczek od 20 wpisów).

| składnik | 3.0.4.17 (zapis wieloma wątkami) | 3.0.4.18 (zapis jednym wątkiem) |
|---|---|---|
| sekretarz: zapis do indeksu i commit | ≈ 343 ms stałe (308 ms dla paczek ≈ 250, 334 ms dla ≈ 50) | **≈ 127 ms stałe** (125 ms dla ≈ 250, 124 ms dla ≈ 50) |
| sekretarz: razem, paczka ≈ 250 wpisów | 753 ms | **526 ms** (przygotowanie 385, JMS 14, flush 0, zapis i commit 125) |
| sekretarz: razem, paczka ≈ 50 wpisów | 426 ms | **210 ms** |
| odbiorca: aktualizacja indeksu | ≈ 298 ms + 0,10 ms na wpis (medianę 243 / 321 / 300 ms dla paczek ≈ 45 / 90 / 243) | **≈ 110 ms + 0,49 ms na wpis** (mediana 97 / 122 / 219 ms) |
| odbiorca: trafienia / chybienia pamięci współdzielonej | 19 120 / 0 | 19 154 / 0 |

Stały koszt zapisu do indeksu i `commit` spadł z ok. 300–340 ms do ok. 110–127 ms (ok. −60%), czyli tyle, ile przewidywała hipoteza o liczbie segmentów i `fsync`. Koszt na wpis u odbiorcy wzrósł z 0,10 do 0,49 ms, bo zapis dokumentów (`searchById` i `addDocument`) idzie teraz jednym wątkiem (u odbiorcy paczka ≈ 243 wpisów: ok. 120 ms w fazie zapisu). Pozostałe ok. 110–125 ms stałego kosztu nie jest jeszcze rozbite: do tego potrzebne są linie `Indeks:` (flush, commit, odświeżenie czytnika).

#### Logi `Indeks:` z 3.0.4.18 (pliki `226-…/18i_mercury-three-node-cluster-mercury-node{1,2,3}-1.log`): rozbicie czasu paczki

Linie `Indeks:` (po poprawce wzorca `grep`): node2 20 paczek, node1 i node3 po 74. Średnie (ms; `inne` = `razem` minus suma pozostałych składników, czyli praca w `updateIndex` poza fazami: otwarcie indeksu i czytnika, pętla po wpisach z `containsInActiveTransactions`, usunięcia):

| węzeł, paczki | n | rozmiar | przygotowanie | wywołanie po przyg. | zapis dok. | flush | commit | **inne** | razem |
|---|---|---|---|---|---|---|---|---|---|
| sekretarz, duże | 10 | 252 | 130 | 14 | 24 | 2 | 96 | **257** | 525 |
| sekretarz, małe | 10 | 48 | 35 | 17 | 5 | 2 | 116 | **33** | 210 |
| odbiorcy, duże | 44 | 246 | 12 | 0 | 22 | 2 | 150 | **44** | 233 |
| odbiorcy, małe | 96 | 75 | 10 | 0 | 11 | 2 | 106 | **17** | 147 |

**Wnioski:** (1) u sekretarza **ok. połowa czasu paczki (257 z 525 ms) to praca poza fazami**, rosnąca z liczbą wpisów (ok. 1 ms na wpis; 33 ms dla paczki 48 wpisów). Przyczyna (z kodu): pętla po wpisach woła po kolei `containsInActiveTransactions`, a to zdalny odczyt z klastrowej pamięci `CaseGlobalTransactionCache` (z `consistency="strong"`), a dla zakończonych transakcji także zdalne `remove`; sekretarz robi to pierwszy, odbiorcy trafiają już na usunięte wpisy (u nich tylko ok. 0,18 ms na wpis). (2) `commit` ma teraz 65–200 ms (mediana 71–134, wartości skrajne do 330 ms) przy jednym segmencie na paczkę; to nadal największy pojedynczy koszt po stronie odbiorców (134–150 ms dla dużych paczek). (3) `flush` 2 ms, odświeżenie czytnika 0 ms, zapis dokumentów 5–24 ms: pomijalne.

**Zmiana w 3.0.4.19 (repozytorium `mercury`, gałąź `hgdb-229`):** sprawdzenie aktywnych transakcji spraw paczki **równolegle** w puli wątków (od 16 spraw; mniejsze paczki po kolei), przed pętlą po wpisach (`CaseIndexerBusinessSupport.findCasesInActiveTransactions`); wynik taki sam jak przy sprawdzaniu po kolei (zbiór spraw w transakcji, wpisy usunięć pomijane, błąd z puli propagowany). Nowy składnik logu `Indeks:`: `sprawdzenie transakcji N ms`. Testy: `CaseIndexerTransactionCheckTest` (5: mała paczka po kolei, duża równolegle z tym samym wynikiem i czasem poniżej 500 ms wobec 800 ms po kolei, usunięcia pomijane, brak menedżera lub pusta lista, błąd propagowany), `CaseIndexerUpdateRunnerTest` (6), `DatasetScenario` (1/1). Oczekiwany efekt u sekretarza: `inne` z ok. 257 do kilkudziesięciu ms dla paczki ok. 250 wpisów, `razem` z ok. 525 do ok. 300 ms.
