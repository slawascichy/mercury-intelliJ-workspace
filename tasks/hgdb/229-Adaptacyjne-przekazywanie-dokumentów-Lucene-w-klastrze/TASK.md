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

(do uzupełnienia)
