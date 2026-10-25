# Zadanie 119, W2: spike podniesienia Lucene 7.5.0 do 8.11.2 (2026-10-25)

Status: **spike przerwany po katalogu błędów kompilacji** (koniec dnia). Kod spike’u leży na gałęzi
`hgdb-119-spike-lucene8` (commit `80217dbf2`, **nie kompiluje się**, nie do scalenia). Gałąź `hgdb-119` jest bez zmian i
buduje się na Lucene 7.5.0 (79 testów modułu zielonych, 10 pominiętych jako `@Ignore`).

## Co ustalono

1. **Java:** Lucene 8.11.x wymaga Javy 8 ([system requirements](https://lucene.apache.org/core/8_11_2/SYSTEM_REQUIREMENTS.html)),
   więc podniesienie Lucene do 8.x nie wymaga podnoszenia Javy. Lucene 9.0 wymaga Javy 11.
2. **Dostępność artefaktów:** repozytorium firmowe (`sci-maven`, Nexus) nie zwraca Lucene 8.11.2. Pobrałem artefakty
   wprost z Maven Central do lokalnego repozytorium `D:\workspace\.m2\repository\org\apache\lucene\<artefakt>\8.11.2`
   (`core`, `queries`, `queryparser`, `highlighter`, `analyzers-common`, `join`, `memory`, `sandbox`, `backward-codecs`
   oraz `lucene-parent`, `lucene-solr-grandparent`). Wersję wybiera się właściwością `-Dlucene.version=8.11.2`
   (`mercury/pom.xml` ma `<lucene.version>7.5.0</lucene.version>`). Build offline po pobraniu działa.
3. **Kompilacja:** czysty `compile -am` na 8.11.2 przechodzi moduły nadrzędne i `mercury-core-server`, a `mercury-lucene-indexes-api`
   wymagało 3 poprawek (zrobione w spike’u). W `mercury-lucene-indexes` kompilator zgłasza **ok. 65 błędów w 20 plikach**.
   Błędy są jednorodne i da się je pogrupować (poniżej). Nie wykryto zależności, której nie da się zastąpić.

## Katalog zmian API (7.5.0 do 8.11.2)

| Grupa | Miejsca w kodzie | Poprawka |
|---|---|---|
| `TopDocs(long, ScoreDoc[], float)` i `TopFieldDocs(...)`: nowy konstruktor z `TotalHits`, brak `maxScore` | `TopHitsUtils` (10), kolektory i menedżery (`DataCollectorTopDocsManager`, `...Sub...`, `...WithSort...`), `QueryExplainPlan` (2) | Zamiana konstruktorów, `new TotalHits(value, Relation.EQUAL_TO)` |
| `TopDocs.totalHits` jest obiektem `TotalHits` (porównania i konwersje do `long`) | `DataCollectorTopDocsManagerSupport` (6), `QueryExplainPlan` (2), menedżery kolektorów (5), `QueryTruncation` użycia | `.totalHits.value` |
| `Collector.needsScores()` zastąpione przez `scoreMode()`, `setScorer(Scorer)` przez `setScorer(Scorable)` | 6 klas kolektorów (`DataCollectorTopDocs`, `...WithSort`, `DataCollectorWithTopDocs`, `DataCollectorWithScore`, `DocDateValueCollector`, `...Manager`) | `ScoreMode.COMPLETE_NO_SCORES` (nasze kolektory nie liczą ocen), `Scorable` |
| `TopDocsCollector.pq` jest `final` (kod przypisuje własną kolejkę) | `DataCollectorTopDocs`, `...WithSort`, `DataCollectorWithTopDocs` | Przebudowa: własny `TopDocsCollector` z kolejką przekazaną w konstruktorze |
| Klasa `org.apache.lucene.search.FieldCollectorTopDocs` leży w pakiecie Lucene, by użyć elementów niepublicznych (`ScoreCachingWrappingScorer`, `FieldValueHitQueue.Entry`) | `FieldCollectorTopDocs` (6 błędów) | Największe ryzyko: przepisać na API publiczne albo skopiować potrzebne klasy do własnego pakietu |
| `Query.createWeight(IndexSearcher, boolean, float)` na `ScoreMode` | `WildcardBooleanQuery` (2) | `ScoreMode` |
| `IndexWriter.maxDoc()` usunięte | `MLuceneIndexerSupport:208` | `getDocStats().maxDoc` |
| `CustomScoreProvider`/`CustomScoreQuery` usunięte | `CaseCustomScoreProvider` (używana tylko jako zbiór stałych `OK_SCORE`, `CASE_INDEX_NAME`) | Klasa zwykła bez dziedziczenia (zrobione w spike’u) |
| `CharTokenizer.normalize(int)` usunięte | `LowerCaseLetterAndDigitTokenizer` | `LowerCaseFilter` w analizatorze (zrobione) |
| `TopDocs.getMaxScore()` usunięte | `TopHits` | Max z `scoreDocs` (zrobione) |
| Inne symbole | `FieldMetricQuery:127`, `CaseIndexerFieldsManager:316` (do zbadania, prawdopodobnie `MultiFields`, `NumericUtils`) | |

Nie sprawdzono jeszcze: moduły `mercury-srv` (`lucene-analyzers-common`), `mercury-ws-*` (jeśli używają Lucene), zmiana
domyślnego `StandardAnalyzer` (brak stop-słów od 8.0), zachowanie `BooleanQuery` i `IndexSearcher.count`.

## Ocena i rekomendacja do decyzji G2

- **Koszt:** wdrożenie to ok. **4 do 6 dni roboczych** (nie 3): kolektory (6 klas), przebudowa `pq`, `FieldCollectorTopDocs`,
  testy różnicowe wyników na INEA oraz pomiar. To mniej niż się obawiano, ale to kod na ścieżce każdego zapytania.
- **Korzyść:** niezmierzona. Nie ma jeszcze działającej kompilacji, więc nie ma pomiaru. Spodziewane (wiedza ogólna, do
  weryfikacji): `ScoreMode.COMPLETE_NO_SCORES`, szybsze `count()`, ulepszone kodeki i BooleanQuery.
- **Indeks:** Lucene 8 czyta indeksy 7.x bez przebudowy (zasada N-1, do potwierdzenia po kompilacji). Lucene 9 ich nie czyta.
- **Rekomendacja:** **nie robić 8.11 w ramach 119 teraz.** Największe zyski (model kosztów i sondy liczności W3, zbiorcze
  łączenie dziecko najpierw W4, kolektor agregatów z DocValues W5) **nie zależą od wersji Lucene**. Większość zmian kolektorów
  z tabeli (TotalHits, `Scorable`, `pq`) trzeba będzie i tak zrobić przy przejściu na Lucene 9 w zadaniu 191, więc port 7 do 8 do 9
  płaci te koszty dwa razy. Zalecam: W3, W4, W5 najpierw, a przejście na Lucene 9 razem z Javą 17 w 191 (jeden port 7 do 9 z
  przebudową indeksów, którą klient i tak musi wykonać przy upgrade). Katalog powyżej i gałąź spike’u zostają jako punkt wyjścia.
- **Alternatywa:** jeśli zależy na 8.11 teraz, wystarczy dokończyć spike (ok. 2 dni do kompilacji i pomiaru z INEA), a decyzję
  podjąć na liczbach. Decyzja należy do autora (G2).

## Uwagi operacyjne

- Lokalny artefakt `mercury-core-3.0.4.14.jar` w `D:\workspace\.m2` jest podmieniony na wersję z polami `truncated`, `totalHits`
  (kopia oryginału: `scratchpad\backup-core-3.0.4.14` w katalogu sesji).
- Pobrane pliki Lucene 8.11.2 leżą w lokalnym repozytorium `D:\workspace\.m2` (nie w repozytorium git).
