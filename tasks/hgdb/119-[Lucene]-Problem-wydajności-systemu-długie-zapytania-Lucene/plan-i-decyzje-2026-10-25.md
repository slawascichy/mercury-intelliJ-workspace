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
| W1 OpenAPI i tłumaczenia dla `truncated` i `totalHits` (klucze `schema.*PagedResult.*` w `openapi-docs_*.properties`, tłumaczenia de, es, fr, ko) | **do zrobienia w W10** | |
| W2 spike Lucene 8.11.2 | **przerwany po katalogu błędów** (ok. 65 błędów w 20 plikach, brak nierozwiązywalnych); gałąź `hgdb-119-spike-lucene8` (`80217dbf2`, nie kompiluje się). Szczegóły i rekomendacja: `spike-lucene-8-2026-10-25.md`. **G2 rozstrzygnięte (autor, 2026-10-25): Lucene 9 robimy w zadaniu 191** (wraz z Javą 17), w 119 zostaje Lucene 7.5.0 i następne są W3, W4, W5; uzupełnienie dopisane do TASK.md zadania 191 | `80217dbf2` (gałąź spike) |
| W3 sondy liczności (`CardinalityProbe`, `CostOptimizer.costOptimization` z czytnikiem i zapytaniami; próg dziecko-najpierw: trafień dziecka < 0,05 × trafień korzenia (kalibracja poniżej), pusty korzeń: korzeń najpierw; wyłącznik `lucene.query.cost.probes`) | **część 1 gotowa**: baza INEA 41/41 spełnia kryterium żalu (było 28/41), wyniki identyczne; najgorsze dawne decyzje: Poznań+Rfs 4,66→1,20, Leszno+Vrf 4,90→1,64 (różnica 248 ms), pusty korzeń 1 dzień 84 s→0,25 s. Dane: `w3-sondy-2026-10-26.csv`. Do zrobienia w W3: zakresy punktowe z granicami, plan dla k≤3, telemetria decyzji, kalibracja stałych | commit roboczy w `mercury` |
| W3 kalibracja progu `lucene.query.cost.childFirstRatio` (41 zapytań INEA, 2 przebiegi, plan dziecko-najpierw z bazy W0) | **gotowa, domyślnie 0,05**. Spełnia kryterium: 0,02 → 41/41 (max żal 1,35); 0,05 → 40/41 (max 1,44, różnica 151 ms); 0,1 → 40/41 (1,61); 0,2 → 37/41 (1,93); 0,5 → 31/41 (4,71); 1,0 → 30/41 (27,0 dla „365 dni + Mts”). Plateau 0,02–0,1; błąd w dół kosztuje najwyżej 1,4×, błąd w górę do 27×, więc wybrano środek plateau. Nie sprawdzono modelu 2.0 ani innych indeksów (INEA jest jedynym dużym). | commit roboczy |
| W4 zbiorcze łączenie zamiast pętli zagnieżdżonej (`collectSubResultsBatch`: jedno zapytanie `TermInSetQuery(<pole>_subCaseId) AND korzeń`, przypisanie rodzic-dziecko z zapisanych identyfikatorów; wczytywanie tylko potrzebnych pól; wyłącznik `-Dlucene.query.nested.batch=false`) | **gotowe**: plan dziecko-najpierw na bazie 41 zapytań 680 s → 30 s (30 dni + Mts 266 s → 3,2 s; 1 dzień 85 s → 3,4 s; 365 dni 202 s → 8,0 s; Poznań+Rfs 13,8 s → 0,95 s), liczby trafień identyczne (0 różnic). Przyczyna: pętla liczyła zakres punktowy korzenia od nowa dla każdego dziecka (Lucene 7 materializuje zakres w `scorer()`); wczytywanie pól dało tylko ok. 10%. Ponowna kalibracja progu `childFirstRatio`: 0,05 → 30/41, 0,3 → 39/41, **1,0 → 41/41 (max żal 1,48, suma czasów 21,8 s wobec 27–29 s)**, 3,0 → 40/41; nowy domyślny próg 1,0. Dane: `w4-*.csv`. Cel „dziecko-najpierw ≤ 8 s” osiągnięty (max 7,96 s) | |
| Do opisania dla autora (zlecenie 2026-10-26): proces kalibracji progu `childFirstRatio` (zbiór 41 zapytań, miara „żalu”, przebiegi, wybór środka plateau, dwie kalibracje: przed i po W4) | **otwarte** | |
