# Zadanie 119: plan (wersja 2, 2026-10-25) z decyzjami autora

Dokument zastępuje pierwszą wersję planu z tego samego dnia. Stan wiedzy: `analiza-2026-10-24.md` (analiza i opinia o
optymalizatorze), `podsumowanie-2026-10-24.md` (pomiary, naprawy, rozbieżność wyników), `porownanie-z-elasticsearch-2026-10-25.md`.

## 1. Decyzje autora (2026-10-25)

| Nr | Decyzja |
|---|---|
| D1 | Zadanie jest **duże i robimy je za jednym razem** (bez kolejnych wydań). Zagęszczamy commity. Celem jest wyraźna poprawa działania silnika, nie sama diagnoza. |
| D2 | Znacznik `truncated` i `totalHits` w odpowiedzi, ostrzeżenie w logu, **błąd jako opcja konfiguracyjna**. |
| D3 | **Spike histogramu dat** w tym zadaniu. |
| D4 | Poprawki (`calculateCost`, `null`, znacznik obcięcia, wczesne wyjście) zostają w 119. |
| D5 | Jeżeli nowszy Lucene nie wymaga nowszej Javy, podniesienie wersji robimy w 119. W przeciwnym razie zostaje w 191. |
| D6 | PoC Elasticsearch/OpenSearch **po wprowadzeniu zmian**. |
| D7 | Wszystko w jednym zadaniu i jednej gałęzi. Claude może robić częste commity robocze (wspierają jego decyzje, np. porównania przy błędach). Decyzje ostateczne, push, PR i merge zostają przy autorze. Claude sygnalizuje, gdy potrzebuje częstszych zatwierdzeń. |

## 2. Odpowiedzi na dwa nowe pytania

### 2.1. Podniesienie wersji Lucene: czy trzeba podnosić Javę?

Obecnie: Lucene **7.5.0** (`<lucene.version>7.5.0</lucene.version>` w `mercury/pom.xml`), moduły: `lucene-core`,
`lucene-queryparser`, `lucene-queries`, `lucene-highlighter`, `lucene-analyzers-common`, `lucene-join`, `lucene-memory`,
`lucene-sandbox`, `lucene-backward-codecs`. Serwer buduje się i działa na **Javie 8**.

| Wersja | Wymagana Java | Uwagi |
|---|---|---|
| 8.x (ostatnia 8.11.x) | **Java 8** ([system requirements 8.11.2](https://lucene.apache.org/core/8_11_2/SYSTEM_REQUIREMENTS.html): „runs on Java 8 or greater”) | Odczytuje indeksy 7.x bez przebudowy (zasada: czytnik N czyta N-1; wymaga potwierdzenia w spike). |
| 9.x | **Java 11** ([ogłoszenie 9.0](https://cwiki-test.apache.org/confluence/x/xZBnCw): wymaga JDK 11) | Nie czyta indeksów 7.x (trzeba przebudowy lub przejścia przez 8.x). |
| 10.x | Java 21 (z wiedzy ogólnej, niezweryfikowane) | Poza zakresem. |

**Wniosek (zgodny z D5):** **Lucene 8.11.x można wdrożyć bez podnoszenia Javy, więc robimy to w 119.** Lucene 9.x wymaga
Javy 11 i zostaje w zadaniu 191.

**Zakres zmian w kodzie** (liczone grepem w `mercury-lucene-indexes`, `-api`, `mercury-srv`, `mercury-core-server`):

| Zmiana API w 8.0 | Miejsca w kodzie |
|---|---|
| `Collector.needsScores()` zastąpione przez `scoreMode()` | 8 plików, 19 wystąpień (kolektory) |
| `TopDocs.totalHits` jest obiektem `TotalHits` (wartość i relacja) | 3 pliki (9 wystąpień) + 4 pliki z `TotalHits` |
| `Query.createWeight(searcher, needsScores, boost)` na `ScoreMode` | 1 plik (6 wystąpień) |
| `MultiFields` oznaczone jako przestarzałe (usunięte w 9) | 3 pliki (8 wystąpień) |
| `CustomScoreQuery`/`CustomScoreProvider` | 4 pliki (9 wystąpień); w razie usunięcia zastąpić `FunctionScoreQuery` lub własnym kolektorem |
| `WeightedTerm`, `QueryTermExtractor` z modułu highlighter | 1 plik (10 wystąpień, `CostOptimizer`); ewentualnie własna ekstrakcja termów |
| `TopDocs.merge`, `TopDocs(` | 13 plików (52 wystąpienia), zmiana sygnatur konstruktorów |
| `StandardAnalyzer()` domyślnie bez stop-słów (od 8.0) | 2 pliki; sprawdzić wpływ na indeksowane wartości (np. status `a`) |

Oszacowanie: **2 do 3 dni** na kompilację i testy po stronie kodu, plus pomiary. Spodziewane zyski (wiedza ogólna, do
weryfikacji pomiarem): `ScoreMode.COMPLETE_NO_SCORES` w kolektorach bez ocen (nasze kolektory nie liczą ocen), szybsze
`count()` z metadanych segmentów, ulepszenia `BooleanQuery`/doc values, lepsze kodeki. Bez pomiaru nie obiecujemy
przyspieszenia.

**Bramka G2 (go/no-go) po spike:** (a) całość kompiluje się na Javie 8, (b) testy zielone, (c) indeksy INEA 7.x
otwierają się i dają **te same liczby trafień**, (d) pomiar na zestawie kluczowych zapytań nie pokazuje regresji. Jeśli
któryś warunek nie zachodzi, zostajemy przy 7.5.0 i wracamy do tematu w 191.

### 2.2. Podniesienie jakości i decyzyjności optymalizatora

Wnioski z `analiza` sekcja 1 wprost zamieniamy na zmiany. Cel to **decyzja bliska optymalnej bez ręcznych wskazówek**:

| Element | Zmiana | Kryterium |
|---|---|---|
| Liczności | **Sondowanie liczności**: `IndexSearcher.count()` na stronie korzenia i dziecka (mierzone: 2 do 50 ms na 22 mln dokumentów) zamiast `min(docFreq)`; wynik w pamięci podręcznej per generacja czytnika; limit czasu sondy i powrót do `min(docFreq)` | Liczność dokładna zamiast zawyżenia 1,6 do 2 razy |
| Koszt strategii | Jawny model pracy: `H_korzeń · c_merge` kontra `H_dziecko · c_loop` (oraz `c_in`, `c_collection`), stałe z kalibracji (mikropomiar przy starcie lub konfiguracja). Ma to zastąpić `int(ln)` | Brak remisów rozstrzyganych losowo |
| Zakresy punktowe | Koszt z granicami zakresu (sonda `count` albo histogram z punktu 3) | Wąski zakres daje tani korzeń |
| Wiele podzapytań | Wybór planu dla całego zapytania (przy k ≤ 3 dzieciach wszystkie 2^k kombinacje) zamiast niezależnych decyzji | Brak k-krotnego wykonywania korzenia, gdy nie opłaca się |
| Limity | Do kosztu wchodzą `maxHits` i sortowanie; ostrzeżenie, gdy plan obcina | Brak cichego obcięcia |
| Wczesne wyjście | Pusty wynik pierwszego etapu przerywa plan | Zapytanie z pustym wynikiem w ułamku sekundy (obecnie ok. 50 s) |
| Poprawki | `calculateCost` (`max`), `null` w `costOptimization` | Test jednostkowy kosztów |
| Telemetria | Log decyzji: koszt dziecka i korzenia, sondy, wybór, rzeczywiste trafienia i czasy | Dane do kalibracji i wykrywania złych decyzji |
| Wskazówki | `ruleRootFirst` i `useCostOptimization` zostają jako wymuszenia. Dodać wskazówki per podzapytanie | Zgodność wsteczna |

**Metryka jakości decyzji:** *żal* (regret) = czas wybranego planu / czas najlepszego z planów (korzeń najpierw, dziecko
najpierw). Stan obecny na 3 rozstrzygających zapytaniach: 1,0 do 1,1 (trafne), ale tylko na 3 przypadkach. Zbudujemy zestaw
**co najmniej 20 zapytań** z pokryciem trudnych przypadków (stosunek trafień dziecko/korzeń 0,05 do 0,5, wąskie zakresy dat
przy rzadkim dziecku, wiele podzapytań, negacje, OR) na indeksach INEA 3.0 i generowanym.

**Kryterium (zatwierdzone przez autora 2026-10-25):** zapytanie spełnia cel, gdy **żal ≤ 1,25 albo różnica bezwzględna
między planem wybranym a najlepszym ≤ 100 ms** (sam iloraz przecenia zapytania krótkie). Poziom zadania: kryterium
spełnia co najmniej 90% zapytań zestawu, a pozostałe mają żal ≤ 2 lub różnicę ≤ 500 ms. Każdy plan musi dawać identyczny
wynik. **Stan bazowy (W0, 41 zapytań):** kryterium spełnia 28 zapytań (68%); nie spełnia 13, z czego 3 z różnicą powyżej
0,5 s (Poznań + Rfs +10,7 s, Leszno + Vrf +1,8 s, Leszno + Abs +1,1 s), 4 z różnicą 0,2 do 0,4 s (serie Leszno i Oborniki)
i 6 z różnicą 110 do 150 ms (zapytania z wieloma dziećmi na `FsmServiceOrder`: tu `rootFirst` jest ok. 2 razy szybszy).

## 3. Cel i kryteria akceptacji zadania (do zatwierdzenia przez autora)

Cel: znacząco poprawić poprawność, wydajność i przewidywalność silnika wyszukiwania. Mierzalnie:

| Obszar | Stan obecny (pomiar) | Cel |
|---|---|---|
| Poprawność | Ciche obcięcie do `maxHits`, różne wyniki zależnie od planu | **Zero cichych obcięć** (znacznik, log, opcja błędu). Test różnicowy: ten sam wynik w trybach `cost`, `rootFirst`, `none` dla całego zestawu zapytań |
| Decyzje optymalizatora | Trafne na 3 przypadkach, luki w modelu | Żal ≤ 1,25 (90%) i ≤ 2 (100%) na zestawie ≥ 20 zapytań |
| Plan dziecko najpierw | 56 do 63 s dla 219 tys. dzieci | ≤ 8 s (zamiana `NESTED_LOOP` na zbiorcze łączenie, nawet gdy optymalizator go nie wybierze) |
| Zapytanie z pustym wynikiem | ok. 50 s | < 1 s |
| `groupBy` (35 do 140 tys. trafień) | 0,4 do 1,9 s | ≤ 0,3 s dla kolektora z DocValues; wynik identyczny z dotychczasowym |
| Redukcja wyniku (200 tys. trafień) | jeden wątek | ≥ 2 razy szybciej na 4 wątkach (wariant A, ograniczona pula) |
| Współbieżność (wzorzec Grafany: 6 paneli) | brak pomiaru; hipoteza 11 do 70 s z 171 | Degradacja p95 ≤ 2 razy przy 8 klientach; zarejestrowana tabela |
| Lucene | 7.5.0 | 8.11.x na Javie 8, testy zielone, indeksy 7.x czytelne bez przebudowy (bramka G2) |
| Dokumentacja i API | brak | OpenAPI i tłumaczenia dla nowych pól (`truncated`, `totalHits`), opis w dokumentacji hgdb.org |

## 4. Zakres prac (strumienie)

| Strumień | Treść | Zależności |
|---|---|---|
| **W0 Baza pomiarowa** | Zamrożenie zestawu zapytań (≥ 20), skrypt tabeli „żal”, test różnicowy wyników trzech trybów, zapis wyników bazowych. Zestaw na INEA 3.0 (kopia `F:`), generowany (model 3.0 i 2.0) | — |
| **W1 Poprawność** | Znacznik `truncated`, `totalHits`, log, opcja błędu (D2). `calculateCost`, `null`, wczesne wyjście. Test regresji na małym indeksie (jak `LuceneNestedQueryOccurTest`) | W0 |
| **W2 Lucene 8.11** | Spike (kompilacja, testy, otwarcie indeksów 7.x, pomiar), bramka G2, potem wdrożenie w modułach | W0 |
| **W3 Optymalizator v2** | Sondy liczności, model kosztu strategii, zakresy z granicami, plan dla całego zapytania, limity, telemetria, wskazówki per podzapytanie (punkt 2.2) | W1, W0 |
| **W4 Silnik wykonania** | Dziecko najpierw: zbiorcze łączenie zamiast pętli; `doc(docId, fieldsToLoad)`; ograniczona pula i równoległa redukcja (wariant A); `SearcherManager`; skrót `DocGroupByEntry` | W0 |
| **W5 Kolektor `groupBy` z DocValues** | Nowy komponent w `org.mercury` (kolektor agregatów, scalanie częściowych), stary jako zapas; identyczny wynik | W2 (zalecane) |
| **W6 Spike histogramu dat** (D3) | Bisekcja `count(range)` na INEA: czas, równość przedziałów; decyzja, czy potrzebny sekretarz | W0 |
| **W7 Podział po dacie** | Planista przedziałów i scalacz (`TopDocs.merge`, agregaty częściowe), wykonanie w wątkach lokalnych; interfejs wykonawcy zdalnego (węzły) | W4, W5, W6 |
| **W8 Pomiary współbieżności** | Wzorzec Grafany (6 paneli, 1/4/8 klientów) przed i po zmianach | W0, W4 |
| **W9 PoC OpenSearch** (D6) | Po zakończeniu W1 do W8: indeksowanie 22 mln dokumentów, 10 zapytań, porównanie czasu i poprawności | po W8 |
| **W10 Domknięcie** | OpenAPI i tłumaczenia (po zmianie API sprawdzić `openapi-doc-report.txt`), dokumentacja, podsumowanie końcowe, PR | po wszystkich |

## 5. Kolejność, commity i bramki decyzyjne

Kolejność: **W0, W1, W2 (spike), bramka G2, W3, W4, W8, W6, W5, W7, W9, W10.** Strumienie W3 i W4 są niezależne i można je
przeplatać.

**Zasady commitów** (D7): commit roboczy po każdym zamkniętym kroku (zielone testy, działający pomiar), na gałęzi `hgdb-119`,
komunikat `hgdb-119 <krótki opis>`. Claude **nie** wykonuje push, PR ani merge. Jeśli zmiana dotknie `mercury-lib` lub
`hgdb-client-open`, to na ich gałęziach `hgdb-119` (wyjątek z CLAUDE.md dla gałęzi zadania). Claude zgłosi autorowi, gdy
potrzebna będzie częstsza akceptacja (np. po każdym kroku optymalizatora).

**Bramki wymagające decyzji autora:**

| Bramka | Kiedy | Decyzja |
|---|---|---|
| G1 | początek W1 | Kształt API: gdzie dodać pola `truncated` i `totalHits` (klasa paginacji `PagingInfo` w `mercury-lib` odziedziczona przez `PagedResult`, DTO usług REST i SOAP, klient `hgdb-client-open`), nazwa opcji błędu, wartość domyślna (propozycja: błąd wyłączony) |
| G2 | koniec spike W2 | Wdrażamy Lucene 8.11.x czy zostajemy przy 7.5.0 |
| G3 | po W3 | Akceptacja modelu optymalizatora na podstawie tabeli „żal” |
| G4 | przed W7 | Zakres podziału po dacie: tylko wątki lokalne czy także węzły klastra (potrzebne środowisko z kilkoma węzłami do testów) |
| G5 | przed W9 | Czy wykonujemy PoC i na jakim sprzęcie |

## 6. Szacunki (dni robocze, orientacyjne)

W0 2, W1 3, W2 4 (spike 1, wdrożenie 3), W3 6, W4 5, W5 4, W6 1, W7 5, W8 1, W9 3, W10 3. **Razem ok. 37 dni roboczych**
(7 do 8 tygodni), z dużą niepewnością przy W3, W5 i W7 oraz zależnością od bramek.

## 7. Ryzyka

- **Zmiana API publicznego** (`truncated`, `totalHits`) dotyka `mercury-lib`, usług REST i SOAP, klienta, OpenAPI i
  tłumaczeń. Nowe pola opcjonalne i domyślnie niewysyłane do starych klientów (do ustalenia w G1).
- **Lucene 8.x** zmienia zachowanie `StandardAnalyzer` (brak stop-słów) i API kolektorów. Ryzyko ukrytej zmiany wyników.
  Łagodzenie: test różnicowy z W0 przed i po.
- **Sondy liczności** dodają koszt (2 do 50 ms) do każdego zapytania z dziećmi. Łagodzenie: pamięć podręczna, limit czasu,
  pomijanie sond dla zapytań bez podzapytań.
- **Węzły klastra:** brak środowiska wielowęzłowego w tej sesji. Podział między węzłami będzie projektem i symulacją, nie
  pomiarem (G4).
- **Jedno środowisko i jeden indeks INEA z 2019 roku.** Rozkład produkcyjny może być inny. Telemetria decyzji (W3) ma to
  skorygować po wdrożeniu.
- **Wielkość zadania:** ok. 37 dni w jednej gałęzi. Częste commity i bramki ograniczają ryzyko, ale PR będzie duży.

## 8. Pytania do autora (nowe)

1. Czy cele z punktu 3 (tabela kryteriów) są właściwe i wystarczające? Czy któryś zmienić lub dodać (np. czas odpowiedzi
   dla wybranych zapytań z 171)?
2. G1: gdzie umieścić `truncated` i `totalHits` (propozycja: `PagingInfo` w `mercury-lib` plus DTO usług) i czy mogę
   założyć gałąź `hgdb-119` w `mercury-lib` i `hgdb-client-open`?
3. Czy mogę zacząć od W0 i W1 (poprawność), a spike W2 (Lucene 8.11.x) wykonać zaraz po nich?
4. G4: czy do testów podziału między węzłami będzie dostępny klaster (kilka węzłów), czy zostajemy przy projekcie i wątkach
   lokalnych?


## 9. Postęp (aktualizowane na bieżąco)

| Krok | Stan | Commit |
|---|---|---|
| Gałęzie `hgdb-119` w `mercury-lib` i `hgdb-client-open` | gotowe (G1: `PagingInfo`) | |
| W0 baza pomiarowa (41 zapytań, CSV, test różnicowy, żal) | **gotowe**, 28 z 41 spełnia kryterium | `d1c82be55` (mercury) |
| W1 `truncated` i `totalHits` w `IPagingInfo`, `PagingInfo`, `PagingInfoTransportable` (wygenerowane DTO dziedziczą pola; nowe elementy wysyłane tylko przy obcięciu) | **gotowe** | `d165103` (mercury-lib) |
| W1 śledzenie obcięć w kolektorach (`QueryTruncation`), ostrzeżenie w logu, opcja `lucene.query.truncation.error` (domyślnie wyłączona), test regresji `LuceneTruncationTest` | **gotowe**; na INEA oznacza dokładnie 2 znane zapytania (Mts 79 158 z 219 238; 365 dni 160 170 z 244 970), bez fałszywych alarmów | `7d505e0f2` |
| W1 `calculateCost` (`max`), `null` w `costOptimization`, `CostOptimizerTest` | **gotowe** | `fdbb0e9a9` |
| W1 wczesne wyjście przy pustym wyniku | **przeniesione do W3** (to sonda liczności korzenia w planie dziecko-najpierw) | |
| W1 OpenAPI i tłumaczenia dla `truncated` i `totalHits` (klucze `schema.*PagedResult.*` w `openapi-docs_*.properties`, tłumaczenia de, es, fr, ko) | **W10: pl i en dopisane** (20 schematów × 2 klucze); **de, es, fr, ko przetłumaczone przez Gemini (2026-10-26), walidacja bez błędów** | |
| W2 spike Lucene 8.11.2 | **przerwany po katalogu błędów** (ok. 65 błędów w 20 plikach, brak nierozwiązywalnych); gałąź `hgdb-119-spike-lucene8` (`80217dbf2`, nie kompiluje się). Szczegóły i rekomendacja: `spike-lucene-8-2026-10-25.md`. **G2 rozstrzygnięte (autor, 2026-10-25): Lucene 9 robimy w zadaniu 191** (wraz z Javą 17), w 119 zostaje Lucene 7.5.0 i następne są W3, W4, W5; uzupełnienie dopisane do TASK.md zadania 191 | `80217dbf2` (gałąź spike) |
| W3 sondy liczności (`CardinalityProbe`, `CostOptimizer.costOptimization` z czytnikiem i zapytaniami; próg dziecko-najpierw: trafień dziecka < 0,05 × trafień korzenia (kalibracja poniżej), pusty korzeń: korzeń najpierw; wyłącznik `lucene.query.cost.probes`) | **część 1 gotowa**: baza INEA 41/41 spełnia kryterium żalu (było 28/41), wyniki identyczne; najgorsze dawne decyzje: Poznań+Rfs 4,66→1,20, Leszno+Vrf 4,90→1,64 (różnica 248 ms), pusty korzeń 1 dzień 84 s→0,25 s. Dane: `w3-sondy-2026-10-26.csv`. Do zrobienia w W3: zakresy punktowe z granicami, plan dla k≤3, telemetria decyzji, kalibracja stałych | commit roboczy w `mercury` |
| W3 kalibracja progu `lucene.query.cost.childFirstRatio` (41 zapytań INEA, 2 przebiegi, plan dziecko-najpierw z bazy W0) | **gotowa, domyślnie 0,05**. Spełnia kryterium: 0,02 → 41/41 (max żal 1,35); 0,05 → 40/41 (max 1,44, różnica 151 ms); 0,1 → 40/41 (1,61); 0,2 → 37/41 (1,93); 0,5 → 31/41 (4,71); 1,0 → 30/41 (27,0 dla „365 dni + Mts”). Plateau 0,02–0,1; błąd w dół kosztuje najwyżej 1,4×, błąd w górę do 27×, więc wybrano środek plateau. Nie sprawdzono modelu 2.0 ani innych indeksów (INEA jest jedynym dużym). | commit roboczy |
| W4 zbiorcze łączenie zamiast pętli zagnieżdżonej (`collectSubResultsBatch`: jedno zapytanie `TermInSetQuery(<pole>_subCaseId) AND korzeń`, przypisanie rodzic-dziecko z zapisanych identyfikatorów; wczytywanie tylko potrzebnych pól; wyłącznik `-Dlucene.query.nested.batch=false`) | **gotowe**: plan dziecko-najpierw na bazie 41 zapytań 680 s → 30 s (30 dni + Mts 266 s → 3,2 s; 1 dzień 85 s → 3,4 s; 365 dni 202 s → 8,0 s; Poznań+Rfs 13,8 s → 0,95 s), liczby trafień identyczne (0 różnic). Przyczyna: pętla liczyła zakres punktowy korzenia od nowa dla każdego dziecka (Lucene 7 materializuje zakres w `scorer()`); wczytywanie pól dało tylko ok. 10%. Ponowna kalibracja progu `childFirstRatio`: 0,05 → 30/41, 0,3 → 39/41, **1,0 → 41/41 (max żal 1,48, suma czasów 21,8 s wobec 27–29 s)**, 3,0 → 40/41; nowy domyślny próg 1,0. Dane: `w4-*.csv`. Cel „dziecko-najpierw ≤ 8 s” osiągnięty (max 7,96 s) | |
| Do opisania dla autora (zlecenie 2026-10-26): proces kalibracji progu `childFirstRatio` (zbiór 41 zapytań, miara „żalu”, przebiegi, wybór środka plateau, dwie kalibracje: przed i po W4) | **opisane w W10**: `podsumowanie-koncowe-2026-10-26.md`, punkt 4 (trzy kalibracje: W3, W4, W7) | |
| W8 pomiar współbieżności (`LuceneConcurrencyPerfTest`: pulpit 6 paneli, 1/4/8 klientów, 3 odświeżenia, jedna JVM, INEA 3.0, model 3.0) | **gotowy**. Odświeżenie pulpitu p95: przed (bez sond, pętla) 16,2 s / 21,3 s / 32,3 s dla 1/4/8 klientów; po W3+W4 3,7 s / 5,1 s / 7,2 s (4,5× szybciej przy 8 klientach). Degradacja p95 8 klientów względem 1: 2,0× przed, 1,95× po (cel ≤ 2× spełniony na styk). Panele grupujące pojedynczo degradują mocniej (P2 dzień 30d: 0,36 → 1,46 s, 4,1×; P4: 3,4×; P3: 2,5×; P5 tabela: 2,3×). Czas 24 pulpitów: 82 s → 19 s. Hipoteza z 171 (11 → 70 s) **nie potwierdziła się** w tym układzie (jedna JVM, bez sieci i bez HTTP). Dane: `w8-*.csv`. Uwagi: n=24 próbek na panel przy 8 klientach, jeden przebieg; maszyna ma 16 logicznych rdzeni (`nproc`) | |
| W5 odczyt komórek wyniku z DocValues (`DocValuesCells`: identyfikator sprawy z samych cyfr i pola liczbowe data/long/int/float/double, jednowartościowe, zapisane i sortowane; reszta z pól zapisanych; wyłącznik `-Dlucene.query.docvalues=false`) oraz wczytywanie tylko potrzebnych pól zapisanych (wyłącznik `-Dlucene.query.nested.loadAllFields=true`) | **etap 1 gotowy**: zbieranie komórek dla groupBy(miesiąc) 39 tys. trafień 894 ms → 12–15 ms; całe zapytanie 958 → 521 ms; skrót zawartości wyników identyczny z poprzednim kodem na 41 zapytaniach (0 różnic), test jednostkowy `DocValuesCellsTest` (równość z polami zapisanymi dla 4 typów, kolejność trafień, id z literami, pole niesortowane). Wczytywanie samych potrzebnych pól dało tylko 7% (koszt to dekompresja bloków pól zapisanych, nie liczba pól). Nie poprawia: grupowania po polach tekstowych (np. `city`, DocValues napisów jest małymi literami i zakodowane do sortowania). Pozostaje ok. 320 ms potoku wiersze → dokumenty → groupBy (obiekty, BigDecimal) i ok. 200 ms samego zapytania. Dane: `w5-*.csv` | |
| W5 etap 2 (bezpośrednia agregacja w kolektorze, z pominięciem potoku wiersze → dokumenty → groupBy) | **odstąpiono (decyzja po pomiarze)**. Rozbicie `groupBy(miesiąc)` 39 tys. trafień, rozgrzane: zapytanie 173 ms, wiersze → dokumenty 53 ms, grupowanie 58 ms (razem ok. 290 ms, cel ≤ 0,3 s osiągnięty); reszta z 430 ms to narzut harnessu (log planu, JSON, wynik). Potok daje więc ≤ 110 ms możliwego zysku, a zastąpienie go wymagałoby odtworzenia semantyki `DocGroupByFunction` (typy, `MathExpression`, wartości puste, strefa czasowa `TRUNC`) z ryzykiem różnic wyników. Ponowny pomiar współbieżności po W5 (`w8-wspolbieznosc-po-w5-2026-10-26.csv`): odświeżenie pulpitu p95 2,7 s / 3,6 s / 4,8 s dla 1/4/8 klientów, degradacja 1,74× (cel ≤ 2×); 24 pulpity w 12,2 s (start: 82 s, po W3+W4: 19 s). Dodano log debug `initResulSet` z rozbiciem czasu | |
| W6 spike histogramu dat (`DateHistogramCollector` z DocValues, `DatePartitioner`, test `LuceneDateHistogramPerfTest`) | **gotowy**. (1) Histogram dzienny z DocValues jest identyczny ze starym `DocDateValueCollector` (401 dni dla FSO 38 981 dok., 97 dni dla adresów 19 334 dok.) i **17× szybszy** (44 vs 742 ms oraz 17 vs 292 ms; stary wczytuje cały dokument na trafienie); cały indeks 22 mln dok. w 468 ms (pierwszy przebieg 794 ms), więc histogram bez filtra można liczyć na żądanie i trzymać w pamięci podręcznej na generację czytnika. (2) Planista dzieli zakres według liczności: nierównowaga części (największa / średnia) dla FSO przy 2/4/8/16 częściach 1,00 / 1,03 / 1,54 / 3,08, a przy podziale równego czasu 1,08 / 1,36 / 2,08 / 3,51; dla adresów 1,05 / 1,09 / 1,37 / 2,74 wobec 1,54 / 1,61 / 2,78 / 4,98. Powyżej 4 części granulacja dzienna nie wystarcza (jeden dzień większy od celu), potrzebny histogram godzinowy. (3) Równoległe liczenie części zapytaniem `count` nie pokazało zysku (zapytania 1–11 ms, narzut wątków dominuje), więc korzyść z podziału zmierzę w W7 na zapytaniach ciężkich (np. 200 tys. trafień z dzieckiem). Różnica semantyczna: dla pól wielowartościowych liczony jest najmniejszy znacznik, a nie pierwszy zapisany (dla `mrc_createDate` bez różnic). Opcja W6b: podpiąć `DateMetricQuery` pod nowy kolektor (dziś liczy dni, godziny i minuty naraz; nowy liczy jedną jednostkę na przebieg). Dane: `w6-histogram-dat-2026-10-26.txt` | |
| W6b `DateMetricQuery` pod `DateHistogramCollector` (dni, godziny, minuty w jednym przebiegu; powrót do `DocDateValueCollector` dla trybów innych niż FIRST, pól wielowartościowych, pól bez DocValues, pól podrzędnych) | **gotowe**: mapy dzień/godzina/minuta identyczne ze starą ścieżką (401 dni, 4075 godzin, 17 451 minut dla FSO), czas 824 → 95 ms; test `testDateMetricQueryDocValuesEqualsOldPath` | |
| W7 podział po dacie wątkami lokalnymi (prototyp `LuceneDateSplitPerfTest`: pełne zapytanie silnika z dodanym zakresem daty na część) | **prototyp wykonany, podział nie jest opłacalny**. Sumy wyników części zgadzają się z całością (ZGODNE) dla 4 scenariuszy, ale czas ścienny nie spada (np. „365 dni + Mts”: 5,9 s całość, 5,3/5,4/5,8 s dla 2/4/8 części; reszta scenariuszy wolniej). Przyczyna: koszt nie zależy od zakresu daty korzenia, bo dominuje wczytywanie komórek 219 tys. dzieci (2,7 s) i 204 tys. rodziców (2,9 s) z pól zapisanych. Dane: `w7-podzial-po-dacie-2026-10-26.txt` | |
| W7 zamiast podziału: odczyt komórek dzieci i rodziców z DocValues w ścieżkach dziecko-najpierw (`collectSubResultsBatch`) i kolekcji (`collectSubResultsByCollection`); `DocValuesCells.readIdValues` czyta identyfikatory dzieci z DocValues pola rodzica (`SORTED_NUMERIC` jak w indeksie INEA albo `SORTED_SET` z samych cyfr) | **gotowe**: „365 dni + Mts” 8,1 → 2,0 s, benchmark Poznań+Mts 3,8 → 2,3 s, suma czasów 41 zapytań (tryb cost) 22,3 → 12,7 s; skróty zawartości wyników identyczne (0 różnic). Podział po dacie po tej zmianie daje 0,9× (nie ma sensu). Rekomendacja do 191/75: przy przebudowie indeksu zapisywać `*_subCaseIds` także jako DocValues (nowy format zapisuje je tylko jako pola zapisane, więc odczyt kolumnowy działa dziś tylko na indeksach w starym formacie z `SORTED_NUMERIC`) | |
| W7 ponowna kalibracja progu `childFirstRatio` po W4/W7 (dziecko-najpierw stało się tańsze) | **gotowa, nowy domyślny próg 2,0**: 0,5 → 36/41 (max żal 3,15), 1,0 → 37/41, **2,0 → 40/41 (suma 10,8 s)**, 4,0 → 39/41. Niespełnione zostaje „30 dni + Mts” (stosunek ok. 10, żal 3,2), którego nie da się poprawić progiem bez pogorszenia innych. Dane: `w7-kalibracja-*.csv` | |
| **Przebieg końcowy** (2026-10-26, stan po W0–W7; `koncowy-przebieg-2026-10-26.csv`, `koncowy-wspolbieznosc-2026-10-26.csv`) | **41/41 zapytań z identycznymi wynikami** we wszystkich trybach i liczbami trafień jak w W0. Kryterium żalu (≤ 1,25 lub ≤ 100 ms): **39/41 (95%)** wobec 28/41 w W0; drugi próg (żal ≤ 2 lub różnica ≤ 500 ms): 40/41. Mediana żalu 1,10 → 1,04, p90 2,4 → 1,33, max 4,9 → 3,9. Suma czasów 41 zapytań w trybie `cost`: **48,6 s → 10,9 s (4,5×)**. Plan dziecko-najpierw: 680 s → 30 s (W4). Najwolniejsze dawne zapytania: Poznań+Rfs 13,7 s → 0,22 s; 365 dni + Mts 6,9 s → 1,9 s; benchmark Poznań+Mts 5,5 s → 0,9 s. Pulpit Grafany (6 paneli) p95: 1/4/8 klientów 2,0 / 2,9 / 4,5 s (W0: 16,2 / 21,3 / 32,3 s), degradacja p95 8 klientów wobec 1: **2,2× — cel ≤ 2× niespełniony w tym przebiegu** (w W8 po W5 było 1,74×; jedna seria po 24 próbki na panel, więc pomiar jest rozrzucony; wymaga powtórzenia, W3 część 2 / SearcherManager). Testy modułu 92 zielone, 10 pominiętych. Znane ograniczenia: „adres 30 dni + Mts” (żal 3,9, różnica 1,9 s) — plan dziecko-najpierw jest tu 3,5× szybszy, ale stosunek dziecko/korzeń (ok. 50) leży między tym przypadkiem a „1 dzień + Mts” (stosunek rzędu 10³, tam wygrywa korzeń); próg 12/24/48 tego nie naprawia (`w7-kalibracja-{12,24,48}.csv`), potrzebny model kosztu z osobnymi stałymi dla obu planów (W3, część 2); „groupBy(miesiąc)” 1,33 (różnica 119 ms) | |


## 10. Propozycja uzupełnienia: zadanie 121 (sortowanie po polach, które nie są sortowalne), strumień W11

**Status: zatwierdzone przez autora (2026-10-26) i zrealizowane (W11.1–W11.3, W11.4 częściowo).** Zakres poniżej opisuje
propozycję; stan realizacji jest w podsekcji „Realizacja W11”.

### Co ustalono (źródło: zgłoszenie CMINATI-101 oraz kod)

1. Błąd z CMINATI-101 (`IllegalStateException` zwrócony jako ogólny `M0001`) pochodzi z Lucene. Pole bez DocValues użyte w
   `SortedSetSortField` kończy wyszukiwanie wyjątkiem. Test odtwarza to na indeksie w pamięci: pole `status` jako
   `StringField` bez DocValues kończy się `IllegalStateException`, a pole z DocValues sortuje się poprawnie.
2. `LuceneSearcher.addSortField` (`mercury-lucene-indexes-api`) **nie sprawdza flagi `sorted`** definicji pola. Dla
   `StringField` zawsze tworzy `SortedSetSortField`, więc pole zdefiniowane jako `sorted=false` (np. `status`) przechodzi
   budowanie sortowania, a błąd pojawia się dopiero przy wyszukiwaniu. Dla `TextField` wyjątek jest zgłaszany od razu
   (`IllegalArgumentException`), ale też jako ogólny błąd aplikacji.
3. Drugi przypadek z zgłoszenia (`companyName`) wynikał z różnicy definicji między środowiskami: na TST pole było
   `TextField`, `sorted=false`; na PROD `StringField`, `sorted=true`. To samo źródło: sortowanie wymaga pola z DocValues,
   a definicja pola i zawartość indeksu mogą się rozjechać (np. indeks zbudowany przed zmianą definicji).
4. W kodzie jest już mechanizm komunikatów dla tego rodzaju błędu: `L0009ValidationException` z komunikatem `L0009.3`
   („Kolektor wymaga pól sortowanych. Pole nie spełnia tego wymagania.”), używany w `CollectorValidator`
   (`sortableOnly`). Sortowanie go nie używa.

### Czy to pasuje do 119

Częściowo. Zadanie 121 nie dotyczy wydajności, ale leży w tej samej ścieżce zapytania (`LuceneSearcher`,
`QueryExplainPlan`), a poprawka jest mała. Zgodnie z decyzją D1 (jedno duże zadanie, bez kolejnych wydań) proponuję włączyć
ją do 119 jako W11 (ok. 1 do 1,5 dnia). Decyzja o **strategii pól sortowania** (czy `status` ma być sortowalny) jest osobną,
produktową decyzją autora i **nie jest** częścią W11.

### Zakres W11 (propozycja)

| Krok | Opis |
|---|---|
| W11.1 | `addSortField`: gdy definicja pola ma `sorted=false` (także dla pól alternatywnych `_S`, `_N`), zgłosić `L0009ValidationException` z komunikatem `L0009.3` i nazwą pola. Wyjątek walidacji trafia do klienta jako błąd walidacji, a nie ogólny `M0001`. |
| W11.2 | Weryfikacja względem indeksu przed wyszukiwaniem: dla każdego pola sortowania sprawdzić w `FieldInfos` czytnika, czy istnieje typ DocValues zgodny z `SortField` (`SORTED_SET`/`SORTED`/`SORTED_NUMERIC`). Brak oznacza walidację z komunikatem o rozbieżności definicji i indeksu („przebuduj indeks”, zadanie 75). Dotyczy przypadku `companyName` na TST. |
| W11.3 | Testy: zmiana `testNonSortableFieldFailsOnlyAtSearchTime` na oczekiwanie `L0009ValidationException`; test pola z definicją `sorted=true`, ale bez DocValues w indeksie; test przez `QueryExplainPlan` (sortowanie przekazane przez `defaultLuceneSortClause`). |
| W11.4 | Komunikaty w `*.properties` (pl, en; de, es, fr, ko przez translator Gemini, zgodnie z ustaleniami), w razie zmiany API sprawdzić `openapi-doc-report.txt`. |
| W11.5 | Dokumentacja: lista pól sortowalnych dostępna przez `CaseIndexerFieldsManagerRest` (już istnieje, wskazana w zgłoszeniu), dopisek w TASK.md zadania 121. |

### Czego W11 nie robi (do decyzji autora)

- Nie zmienia definicji pól (`status` zostaje niesortowalny). Zmiana wymaga aktualizacji definicji i przebudowy indeksu.
- Nie wprowadza sortowania w pamięci po polach zapisanych (`store=YES`) jako rozwiązania zastępczego: dla dużych wyników
  jest kosztowne, a `status` nie jest nawet zapisany (`store=NO`). Do rozważenia przy dyskusji o strategii pól.
- Nie zamyka zadania 121: komentarz z otwartą dyskusją o strategii sortowania pozostaje. W11 usuwa tylko mylący błąd.

### Realizacja W11 (2026-10-26)

| Krok | Stan |
|---|---|
| W11.1 | **Gotowe.** `LuceneSearcher.addSortField` zgłasza `L0009ValidationException` (klucz `L0009.7`) dla pola z `sorted=false` oraz dla pola nieistniejącego w definicjach (`L0009.2`). `prepareSort` i `addSortField` deklarują ten wyjątek; zaktualizowane wywołania w `LuceneQuery` (opakowanie w `IllegalArgumentException` jak dotąd) i test `RAMDirectoryTest`. `CaseSearcher` i `CaseSearchExtRest` kompilują się bez zmian (metody deklarują `MercuryException`). |
| W11.2 | **Gotowe.** `LuceneSearcher.validateSortAgainstIndex(reader, sort)` sprawdza typ DocValues pól sortowania w segmentach (`SORTED_SET`/`SORTED` dla pól tekstowych, `SORTED_NUMERIC`/`NUMERIC` dla liczbowych); rozbieżność daje `L0009ValidationException` (`L0009.8`: przebuduj indeks albo użyj innego pola). Pole nieobecne w indeksie jest dozwolone. Wywołanie w `QueryExplainPlan.prepare`. |
| W11.3 | **Gotowe.** `LuceneSortNonSortableFieldTest` (5 testów: pole sortowalne działa; `sorted=false` odrzucone; Lucene bez walidacji daje `IllegalStateException`; indeks bez DocValues odrzucony; pole z DocValues i pole nieobecne przechodzą). Moduł: 97 testów zielonych, 10 pominiętych. Baza 41 zapytań INEA wykonuje się bez błędów walidacji (sortowanie po `mrc_createDate`). |
| W11.4 | **Częściowo.** Klucze `L0009.7` i `L0009.8` dodane w `LuceneErrorMsg_pl.properties` i `LuceneErrorMsg_en.properties`. Dla de, es, fr, ko brak kluczy: `MercuryMessageFactory.getMessage` wraca wtedy do wersji wymaganej (`REQUIRED_LANG_VERSION`), więc komunikat jest zawsze dostępny. **Gotowe (W10):** tłumaczenie obu kluczy (de, es, fr, ko) przez translator Gemini (`localization-project`). Zmiana API nie dotyczy `I*Action`/`I*ExtRest`, więc `openapi-doc-report.txt` bez zmian. |
| W11.5 | **Gotowe w W10:** opis sortowania i listy pól (`CaseIndexerFieldsManagerRest`) w `podsumowanie-koncowe-2026-10-26.md`, punkt 3. Dokumentacja użytkownika w `docusaurus-hgdb` (osobne repozytorium) bez zmian. Notatka w `TASK.md` zadania 121 zaktualizowana. |
| W9 PoC OpenSearch 2.19.1 (jeden węzeł, 4 shardy, dane INEA 22 mln dokumentów w modelu zdenormalizowanym z `nested`) | **gotowy**: wszystkie 10 zapytań z identycznymi liczbami trafień i grup jak Mercury; OpenSearch 9–212× szybszy na zapytaniach (10–17 ms), odświeżenie pulpitu p95 121/117/179 ms (Mercury 2035/2886/4524 ms). Przewaga wynika głównie z modelu danych (wąski dokument, dzieci osadzone, DocValues) i braku materializacji wierszy; migracji nie rekomenduję. Opis, ograniczenia i wnioski projektowe: `poc-opensearch-2026-10-26.md` | |
| W10 Domknięcie | **gotowy po stronie Claude**: klucze OpenAPI pl i en (`truncated`, `totalHits`), opis sortowania (W11.5), opis kalibracji, konfiguracja, podsumowanie końcowe: `podsumowanie-koncowe-2026-10-26.md`. **Zostaje autorowi:** ponowne wygenerowanie raportu OpenAPI (generator nie startuje w sesji Claude: `MercuryException` w `generate-model`), push i PR | |


## 11. Propozycja W12: pula czytników (zadanie 39, 2026-10-26)

Zadanie 39 opisuje stos wątku z `LuceneConfig.getIndexReader` → `DirectoryReader.open` → `MMapDirectory.map` (blokada przy mapowaniu pliku).
Kod to potwierdza: `LuceneConfig.getIndexReader(indexName)` (`mercury-lucene-indexes-api`) tworzy **nowy `FSDirectory` i nowy `DirectoryReader` przy każdym wywołaniu**,
a wszystkie ścieżki zapytań (`MLuceneIndexerSupport`, `CaseIndexer`, `CaseSearcher`, `CaseSearchExtRest`, kolektory dat) zamykają go po użyciu.

**Pomiar (INEA 3.0, 25 segmentów; `w12-pula-czytnikow/wyniki.txt`):**
otwarcie czytnika kosztuje **99–159 ms** (mediana 159 ms, maks. 759 ms), a samo zapytanie na wspólnym czytniku 0,3 ms. To stały koszt każdego żądania,
niezależny od zapytania. Na pulpicie (6 paneli) to ok. 0,75 s z p95 2,0 s dla jednego klienta (szacunek: 6 × ok. 125 ms, nie mierzone na pulpicie).
Przy wielu klientach dochodzi rywalizacja o mapowanie plików (stos z zadania 39).

**Czy da się bez własnej kompilacji Lucene: tak.** Obawa z zadania 39 (`IndexReader.close()` jest `final`) omija wzorzec:
jeden wspólny `DirectoryReader` w puli (liczenie referencji `incRef`/`decRef`) i **lekki uchwyt per wywołanie** (`FilterDirectoryReader`,
którego `doClose()` zwalnia referencję wspólnego czytnika zamiast go zamykać). Uchwyt jest `DirectoryReader`, więc istniejący kod
(`try (IndexReader r = …)`, `new IndexSearcher(r)`) działa bez zmian. W `mercury` nie ma rzutowań na `DirectoryReader`. Prototyp
`w12-pula-czytnikow/PoolProto.java` przeszedł testy: migawka starego uchwytu po odświeżeniu, podwójne `close()`, zamknięcie puli.

**Czas po zmianie (prototyp):** acquire+count+close 0,2 ms (sprawdzanie zmian co 1 s) zamiast 125 ms; 8 wątków: p95 0,6 ms.
Sprawdzanie zmian przy każdym acquire (`openIfChanged`, 8 ms) serializuje wątki (p95 70 ms), więc nie nadaje się jako domyślne.

**Ryzyka i warunki:**
1. **Świeżość danych.** Dziś każde zapytanie widzi ostatni commit. Pula musi unieważniać czytnik po commicie własnego writera (miejsca: 10 wystąpień w `MLuceneIndexerSupport`, 6 w `LuceneConfig`) oraz sprawdzać zmiany co N ms dla zapisów spoza procesu
   (przypuszczenie: węzły podrzędne mogą zapisywać do tego samego katalogu; do potwierdzenia). Interwał konfigurowalny, np. `lucene.reader.refreshMs` (0 = jak dziś).
2. **Windows i pliki.** Długo żyjący czytnik trzyma mapowania plików. Przebudowa, usuwanie i archiwizacja indeksu (`closeIndexWriterForce`, `buildNew`) muszą najpierw zamknąć pulę dla danego indeksu.
3. **Pamięć i wersje.** Po odświeżeniu stary czytnik żyje, dopóki ktoś go używa (długie zapytania). Wymaga testu współbieżności z zapisem.
4. **Cache zapytań Lucene** jest kluczowany rdzeniem segmentu, więc wspólny czytnik poprawia też trafienia w cache (przypuszczenie, do zmierzenia).
5. Wyłącznik `-Dlucene.reader.pool=false` przywraca otwieranie na każde żądanie.

**Zakres W12 (szacunek 2 dni):** klasa puli w `org.mercury.lucene` (zgodnie z zasadą nowych komponentów), podpięcie w `LuceneConfig.getIndexReader`,
unieważnianie przy commit/zamknięciu writera/przebudowie, testy (poprawność, współbieżność z zapisem, zamknięcie), pomiar na pulpicie (W8) i w 41 zapytaniach.
Zadanie 39 zamykamy razem z 119 (po decyzji autora).
