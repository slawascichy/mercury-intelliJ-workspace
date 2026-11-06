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
