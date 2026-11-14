# [209] [mercury-cmd] Polecenie linii komend kalibrujące parametry początkowe indeksu Lucene

**Status (2026-11-14):** rozpoczęte rozpoznanie i projekt (sekcja „Projekt”); bez kodu, bez limitu czasu, liczy się jakość rozwiązania (decyzja autora 2026-11-14). Wcześniej: w planie po 191 (decyzja 2026-10-27). Plan: `plan-najblizszych-dzialan-2026-10-26.md`.

Zgłoszenie: https://github.com/slawascichy/hgdb/issues/209

Szkic zadania (2026-10-26, propozycja z zadania 119). Numer zgłoszenia (209) nadany przez autora.
Zakres, nazwa polecenia i lista parametrów to propozycje do decyzji autora. Elementy oznaczone „przypuszczenie” nie były sprawdzane.

## Cel

Parametry w `lucene.properties` dobiera się dziś ręcznie, a ich optymalne wartości zależą od danych klienta. W zadaniu 119 kalibrację progu
`lucene.query.cost.childFirstRatio` wykonano ręcznie, na jednym indeksie (INEA 3.0, 22 mln dokumentów), trzema przemiataniami po 41 zapytań.
Zadanie dodaje do `mercury-cmd` (moduł `mercury-srv-cmd`) polecenie, które robi to samo na lokalnym indeksie klienta i podaje gotowy fragment `lucene.properties`.

## Stan wyjściowy (zweryfikowany)

- `mercury-srv-cmd` ma polecenia rejestrowane w `CmdActionsEnum` (`GL`, `RIC`, `VL`, `RPD`, `JDBCTEST`, `HELP`, `EP`, `TS`), a każde ma klasę `…Action` implementującą `ShellAction`
  (wzorzec: `GenerateLuceneAction`). Uruchamia je `mercury-cmd.sh` z `-Dmercury.lucene.config.file=$MERCURY_HOME/config/lucene.properties`.
- Opis parametrów i miejsc ich ustawiania: `tasks/hgdb/119-…/parametry-konfiguracji-lucene-2026-10-26.md`.
- Metoda kalibracji (zbiór zapytań, miara „żalu”, przemiatanie progu, kryterium): `tasks/hgdb/119-…/podsumowanie-koncowe-2026-10-26.md`, punkt 4.
  Skrypt przeliczający: `tasks/hgdb/119-…/kalibracja-przelicz.py`. Zestaw 41 zapytań jest w testach `mercury` (`LuceneLegacyIndexQueryTest`, `LuceneQueryPerfSupport`), ale jest związany z danymi INEA.

## Proponowany zakres

Polecenie (propozycja kodu: `LC`, w `CmdActionsEnum`) działa na kopii albo na kopii roboczej indeksu wskazanego w `lucene.properties`, tylko w trybie odczytu, i kalibruje:

| Grupa | Parametry | Jak mierzyć |
|---|---|---|
| Zapytania | `lucene.query.cost.childFirstRatio`, `lucene.query.cost.probeLimit` | Zbiór zapytań wygenerowany z indeksu: pary rodzic–dziecko o różnych stosunkach liczności; tryby `cost`, `rootFirst`, `none`; żal ≤ 1,25 albo różnica ≤ 100 ms |
| Czytnik | `lucene.reader.refreshMs` | Koszt `openIfChanged` wobec oczekiwanej świeżości (opcja, przypuszczenie: wartość domyślna zwykle wystarcza) |
| Limit wyniku | `lucene.query.maxHits` | Rozkład liczby trafień w zbiorze zapytań, odsetek zapytań obciętych dla kandydatów limitu |
| Zapis (opcjonalnie) | `lucene.RAMBufferSizeMB`, `lucene.maxBufferedDocs`, `lucene.index.segments` | Czas budowy kopii indeksu dla kilku wartości (kosztowne, tylko na wyraźne żądanie) |

## Wyjście

1. Raport tekstowy i CSV: wartości kandydatów, liczba zapytań spełniających kryterium, suma czasów, mediana i maksimum żalu (jak tabele w `podsumowanie-koncowe`).
2. Rekomendowane wartości i gotowy fragment do wklejenia w `lucene.properties`. Polecenie **nie modyfikuje** `lucene.properties` samo (opcja `--apply` do rozważenia).
3. Ostrzeżenia: za mały indeks (mało dokumentów daje szum), zbiór zapytań bez par rodzic–dziecko, wyniki poniżej progu szumu (ok. 100 ms).

## Do rozstrzygnięcia przez autora

1. **Źródło zapytań.** Zestaw zapytań z 119 jest związany z INEA. Opcje: (a) generowanie zapytań z indeksu (typy, pola, statystyki termów); (b) plik zapytań dostarczony przez klienta (np. z logów); (c) oba.
2. **Gdzie działa polecenie.** Lokalnie na bibliotekach serwera (`command-local-context.xml`) na kopii indeksu, czy też na działającym węźle. Pomiar na produkcji zaburza pracę użytkowników (zadanie 171: rywalizacja o zasoby).
3. **Czy kalibrować parametry zapisu** (RAM, bufor, segmenty). Pomiar wymaga przebudowy indeksu, więc jest długi.
4. **Wspólne źródło kodu pomiarowego.** Kod z testów (`LuceneQueryPerfSupport`) leży w module testowym `mercury`. Polecenie wymaga jego przeniesienia do modułu produkcyjnego albo własnej implementacji.
5. **Zależności wersji.** `mercury-cmd` buduje się z wydanymi wersjami (`mercury.static.version=3.0.3.2.12`), a nowe parametry są w gałęzi `hgdb-119`. Polecenie działa tylko na serwerze z nową wersją biblioteki Lucene; trzeba ustalić wersję docelową.
6. **Lucene 9 (zadanie 191).** Kod pomiarowy powinien używać tych samych API, które zostaną po migracji (zgodność z zasadą z 119: bez klas w `org.apache.lucene.*`).

## Kryteria akceptacji (propozycja)

- Polecenie `LC` w `HELP`, opisane w dokumentacji `mercury-cmd`.
- Na indeksie INEA 3.0 wskazuje `childFirstRatio` z przedziału zbliżonego do ręcznej kalibracji z 119 (1,0 do 4,0; wartość wdrożona 2,0) i kryterium ≥ 90% zapytań.
- Raport powtarzalny (ten sam wynik w granicach szumu) i odporny na przerwanie (wynik cząstkowy zapisywany do pliku).
- Testy jednostkowe części przeliczającej (żal, kryterium, wybór progu) bez dostępu do indeksu.

## Projekt (2026-11-14, do przeglądu autora)

### Decyzje autora (2026-11-14)

- Źródło zapytań: **generator z indeksu oraz opcjonalny plik zapytań**.
- Zakres pierwszego wydania: **`lucene.query.cost.childFirstRatio` i `lucene.query.cost.probeLimit`**. `maxHits`, `refreshMs` i parametry zapisu poza zakresem.
- Środowisko: **na działającym węźle**.

### Rozpoznanie (zweryfikowane w kodzie 2026-11-14)

- Tryby z kalibracji 119 to **wskazówki kontekstu żądania**, a nie właściwości systemowe: `ContextQueryHint.USE_COST_OPTIMIZATION` i `RULE_ROOT_FIRST` (tryb `cost` = true/false, `rootFirst` = false/true, `none` = false/false; `LuceneQueryPerfSupport.measure`). Nie trzeba zmieniać konfiguracji węzła ani restartować.
- Reguła decyzji jest stała: korzeń najpierw, gdy `nChild >= childFirstRatio × nRoot` (`CostOptimizer.costOptimization`), z limitem sondy `probeLimit` (domyślnie 3 000 000), przy `nRoot >= limit` i `nChild >= limit` zawsze korzeń najpierw. Dlatego **przemiatanie progu można policzyć bez ponownych pomiarów**: dla każdego zapytania mierzymy raz czas planu „korzeń najpierw” i planu „dziecko najpierw” oraz `nRoot`, `nChild`; dla progu `r` wybrany plan wynika z reguły, a czas i żal z pomiarów. Weryfikacja końcowa: jeden przebieg w trybie `cost` z wyliczonym progiem.
- `mercury-srv-cmd` ładuje lokalny kontekst Spring z bibliotekami serwera (`command-local-context.xml`, wzorzec `GenerateLuceneAction`) i `mercury-cmd` buduje się już z `mercury` 3.0.4.25 (zawiera `CostOptimizer`). Polecenie może więc działać **w procesie na hoście węzła, na katalogu indeksu węzła otwartym tylko do odczytu** (Lucene dopuszcza równoczesne czytniki), bez REST. To spina oba wybory: generator ma dostęp do statystyk indeksu, a pomiar do wskazówek kontekstu.
- Wykonanie zapytania w kodzie produkcyjnym: `QueryExplainPlan.prepare(...)` i `execute(...)` (`org.mercury.lucene.query`). Kod pomiarowy (`LuceneQueryPerfSupport`, `LuceneQuerySupportTestCase.runNewQuery`) jest w module testowym i zależy od `FakeCaseMapper` i `FakeSecurityContexHelper`.
- Monitor zapytań z zadania 113 (rejestr, `LuceneQueriesExtRest`) przechowuje rzeczywiste zapytania. Naturalne źródło „pliku zapytań” (przypuszczenie, do sprawdzenia: czy rejestr zachowuje pełny tekst zapytania i czy da się go wyeksportować).

### Proponowana architektura

1. **Rdzeń w `mercury`** (moduł produkcyjny `mercury-lucene-indexes`, pakiet `org.mercury.lucene.calibration`): wyznaczanie `nRoot`/`nChild`, pomiar planów ze wskazówkami, obliczenia (żal, kryterium, przemiatanie, wybór progu), generator zapytań z indeksu, parser pliku zapytań. Bez klas w `org.apache.lucene.*` (zgodność z 191). Testy jednostkowe części przeliczającej bez indeksu oraz na małym indeksie testowym.
2. **Cienkie polecenie `LC` w `mercury-cmd`** (`mercury-srv-cmd`, `CmdActionsEnum`, `LuceneCalibrationAction`, wpis w `HELP`): parsowanie opcji, wywołanie rdzenia, zapis raportu.
3. **Wyjście:** raport tekstowy i CSV (tabele jak w `podsumowanie-koncowe` 119), rekomendowane wartości i fragment `lucene.properties` (bez zapisu do pliku), ostrzeżenia (mało dokumentów, brak par rodzic–dziecko, wyniki poniżej szumu 100 ms), wynik cząstkowy zapisywany na bieżąco (odporność na przerwanie).
4. Rdzeń w `mercury` oznacza wydanie `mercury`, a polecenie w `mercury-cmd` zależy od tego wydania.

### Ochrona węzła (pomiar na działającym węźle, zadanie 171)

Pomiar rywalizuje o procesor i dysk z użytkownikami. Propozycja zabezpieczeń: opcje `--max-seconds` i `--max-queries`, pojedynczy wątek, przerwa między zapytaniami (`--pause-ms`), limit czasu pojedynczego zapytania (`queryTimeout` w kontekście), ostrzeżenie i potwierdzenie przed startem, rekomendacja uruchamiania poza szczytem. Tryb `--index-copy` (ścieżka kopii) dla pomiaru bez wpływu na węzeł.

### Generator zapytań z indeksu (do dopracowania)

Cel: pary rodzic–dziecko o zróżnicowanych stosunkach `nChild/nRoot` (od ≪ 1 do ≫ 10) w modelu indeksu 3.0. Szkic: z indeksu wybrać typy z dziećmi i pola o różnej selektywności (statystyki termów: `docFreq`), złożyć zapytania korzeń+dziecko, policzyć `nRoot`, `nChild` sondą, a następnie dobrać próbkę równomiernie po logarytmie stosunku. Dochodzą zakresy dat o różnej szerokości (jak w 119). **Do zbadania:** jak w modelu 3.0 reprezentowane są powiązania (`subCaseIds`, DocValues) i jak z nich zbudować zapytanie z dzieckiem poprawne dla optymalizatora.

### Otwarte pytania do autora

1. Czy polecenie ma działać tylko w procesie na hoście węzła (bez REST), jak proponuję? Alternatywa (REST) wymaga dostępu do statystyk indeksu przez API i nie pozwala na generator.
2. Zabezpieczenia węzła z powyższej listy: czy wystarczą, czy wymagać potwierdzenia (`--yes`) i trybu kopii domyślnie?
3. Rdzeń w `mercury` (wydanie) i polecenie w `mercury-cmd`, czy cały kod w `mercury-cmd` (bez zmian w `mercury`, ale wtedy kopia kodu pomiarowego)? Rekomendacja: rdzeń w `mercury` (reuse, wspólne API po 191).
4. Zamrożenie nazwy polecenia `LC` i opcji.
5. Czy po 191 zmienić miarę (Lucene 9 zmienia koszt planów, optimum progu przesuwa się, kalibrację należy powtórzyć; sama funkcja zostaje).

### Decyzje autora w sprawie pytań (2026-11-14)

1. Polecenie działa **w procesie na hoście węzła** (bez REST).
2. Zabezpieczenia węzła (limity, pojedynczy wątek, przerwa, potwierdzenie, tryb kopii) zaakceptowane.
3. Zmiany w `mercury` i `mercury-cmd` dozwolone, gdy konieczne (rdzeń w `mercury`, polecenie w `mercury-cmd`).
4. Nazwa polecenia `LC` i opcje zaakceptowane.
5. Dodatkowe zlecenie autora: sprawdzić rejestr monitora z 113, model indeksu 3.0 oraz implementację planu zapytania (`QueryExplainPlan`) pod kątem przydatności do kalibracji. Plan jest wizualizacją realizacji zapytania, którą developer ogląda przed i po wykonaniu, więc błędy w jego implementacji należy poprawić.

### Rozpoznanie: monitor z 113, model 3.0 i plan zapytania (2026-11-14, analiza kodu)

**Monitor zapytań (`LuceneQueryMonitor`, `mercury-lucene-indexes-api`):**
- Singleton w JVM serwera, tylko w pamięci: aktywne, ostatnie (domyślnie 200), wolne (≥ 1000 ms) i statystyki po „odcisku” zapytania (literały zastąpione `?`; do 500 odcisków). Nic nie jest zapisywane na dysk.
- Wpis ma rodzaj (`kind`), tekst zapytania Lucene (ucięty do 10 000 znaków i zakończony „…”), użytkownika, czas, liczbę trafień i błąd. **Nie ma planu, sortowania, pól wynikowych, wskazówek ani `nRoot`/`nChild`.** Tekst bez reszty kontekstu wystarcza do ponownego wykonania w kalibracji (generujemy własny kontekst), ale uciętych zapytań nie da się użyć.
- Proces polecenia `LC` to osobna JVM, więc nie widzi rejestru węzła. Źródłem pliku zapytań może być eksport przez REST (`LuceneQueriesExtRest`) albo log. Eksport z pominięciem uciętych wpisów to osobny, niewielki krok.

**Plan zapytania (`QueryExplainPlan`, 2910 linii):**
- Plan jest budowany w `prepare()` przed wykonaniem i zawiera: kroki (`QUERY`, `NESTED_LOOP`, `NESTED_MERGE`, `MERGE_RESULTS`, `PREPARE_RESULT`), poziomy, zapytanie kroku, wymagalność, `skipExecution` i koszt (`minWeight`, `maxWeight`). `toString()` i `toJSON()` pokazują to samo.
- **Decyzja „korzeń najpierw / dziecko najpierw” zapada w `prepare()`** (`CostOptimizer.costOptimization`, linia ok. 1059) i jest w planie zakodowana tylko pośrednio: korzeń najpierw to krok `Q:<grupa>.root` z dziećmi, dziecko najpierw to krok `Q:<grupa>.<pole>` z `N:….root`. Plan **nie mówi, dlaczego** wybrano strategię: brak `nRoot`, `nChild`, progu, powodu (sonda / wskazówka kontekstu / reguła awaryjna / sonda niepowodzenie).
- **Koszt pokazany w planie jest kosztem starej reguły (logarytm częstości termu), a nie liczbami z sondy, na podstawie których zapada decyzja.** Plan może więc pokazywać koszty sugerujące odwrotny wybór niż faktyczny (rozbieżność wizualizacji z zachowaniem). To realna wada planu jako narzędzia dewelopera.
- **Po wykonaniu plan nic nie dopisuje:** brak czasu i liczby trafień poszczególnych kroków. Czasy etapów są tylko w osobnych statystykach (`QueryStats`, `QueryStatsCollector`), a liczba trafień tylko w wyniku.
- Wskazówki kontekstu (`USE_COST_OPTIMIZATION`, `RULE_ROOT_FIRST`) nie są w planie widoczne, mimo że zmieniają strukturę planu. Tryb `none` oznacza „zawsze dziecko najpierw” (analiza 119), czego z wydruku nie widać.
- Znane wcześniej błędy kosztu (`currMax` z `getMinWeight()`, brak sprawdzenia `subQueryWeight != null`) są już poprawione w kodzie (sprawdzone 2026-11-14). Statycznie nie znalazłem w `toString`/`toJSON` błędu wykonania (nazwy kroków zawsze mają prefiks `Q:`/`N:`, więc `substring(1)` w `toJSON` jest bezpieczne). **Nie uruchamiałem planów** (patrz niżej).

**Wnioski dla kalibracji:**
- Plan jest przydatny jako **nośnik wyniku decyzji**: jeśli `prepare()` zapisze w planie rekord decyzji (strategia, powód, `nRoot`, `nChild`, próg, limit sondy), kalibracja czyta `nRoot`/`nChild` z planu bez drugiej sondy i zgodnie z tym, co zrobił serwer.
- Plan jest przydatny jako **nośnik pomiaru**: jeśli `execute()` zapisze w krokach czas i liczbę trafień, kalibracja i deweloper czytają to samo.
- Proponowana poprawka planu (w `mercury`, ten sam zakres co rdzeń kalibracji): (a) rekord decyzji w planie widoczny w `toString()` i `toJSON()`, (b) wskazówki kontekstu w nagłówku planu, (c) czasy i trafienia kroków po wykonaniu („plan po”), (d) koszty w planie pokazywane obok liczb sondy, z oznaczeniem, które z nich zadecydowały.

**Pomysł autora (2026-11-14):** monitor z 113 mógłby też prezentować plany zapytań (np. plan „po” z czasami kroków przy wolnych zapytaniach), co spina plan, monitor i kalibrację. Do rozważenia po poprawce planu: pamięć na plany w `LuceneQueryMonitor` (limit rozmiaru, tylko wolne zapytania), pole planu w `LuceneQueryInfo` i widok w `lucene-queries.html`.

**Model indeksu 3.0:** powiązania rodzic–dziecko są zapisywane w dokumencie rodzica w polach `…subCaseIds` (`CaseMapper`, ok. linii 1224: `case2SubCaseDAO.findSubCaseIdsByParentCaseIdAndFieldName`), a zapytanie z dzieckiem to podzapytanie z etykietą pola (`<pole>.<atrybut>:wartość`), które optymalizator rozbija na korzeń i dziecko. Szczegóły generowania par dla generatora zapytań (które pola i typy mają dzieci, jak policzyć stosunek liczności z statystyk termów) wymagają jeszcze odczytu indeksu wzorcowego i zostają do następnego kroku.

**Weryfikacja dynamiczna wstrzymana:** próba uruchomienia testu planu (`LuceneNestedQueryOccurTest`) kończy się błędem konstruktora: testy `mercury-lucene-indexes` wymagają Terracotty na `localhost:9510` (nie działa; ActiveMQ 51616 też nie). Infrastrukturę uruchamia autor. Do kolejnych kroków (oglądanie planów na indeksie testowym i późniejsze testy) potrzebna jest Terracotta na 9510.

### Plan prac (bez harmonogramu, w kolejności)

1. Sprawdzić rejestr monitora 113 jako źródło zapytań oraz reprezentację par rodzic–dziecko w modelu 3.0.
2. Rdzeń: sonda `nRoot`/`nChild`, pomiar planów, obliczenia i testy jednostkowe.
3. Parser pliku zapytań, generator, raport i CSV.
4. Polecenie `LC`, opis w `HELP` i dokumentacji `mercury-cmd`, docusaurus.
5. Walidacja na indeksie INEA 3.0 (`H:\mercury\20190705_Case_3.0`, kopia na `F:\mercury-indexes`): wskazany próg zbliżony do ręcznej kalibracji z 119 (przedział 1,0–4,0) i ≥ 90% zapytań spełniających kryterium; powtarzalność wyników i odporność na przerwanie.

## Postęp

### Etap A: plan zapytania pokazuje decyzję i pomiar (2026-11-14, gałąź `hgdb-209` w `mercury`, bez commita)

- `PlanDecision` (nowa klasa, `org.mercury.lucene.query`): strategia (`ROOT_FIRST`, `CHILD_FIRST`), powód (`PROBE`, `PROBE_ROOT_EMPTY`, `PROBE_OVER_LIMIT`, `PROBE_FAILED`, `HINT_ROOT_FIRST`, `HINT_NO_OPTIMIZATION`, `NO_SUBQUERY_WEIGHT`, `NO_ROOT_WEIGHT`, `WEIGHT_RULE`), `nRoot`, `nChild`, próg, limit sondy, wskazówki kontekstu; `toString()` i `toJSON()`.
- `CostOptimizer.decide(...)` i `decideByWeights(...)` zwracają decyzję z uzasadnieniem. Metody `costOptimization(...)` (zwracają `boolean`) zostają jako opakowania, więc dotychczasowi wywołujący i testy działają bez zmian.
- `QueryExplainPlan`: decyzja zapisana w kroku zapytania z podzapytaniem i widoczna w `toString()` oraz `toJSON()` (`DECISION: …`, `decision`); po wykonaniu `ACTUAL: <ms> ms, hits=<n>` (`actual`); wynik z pamięci podręcznej wyników oznaczony `RESULT FROM CACHE` (`resultFromCache`), bo kroki nie są wtedy wykonywane. Uwaga w planie, że `Cost()` pochodzi z reguły wagowej, a decyzja z sondy.
- Test `QueryExplainPlanDecisionTest` (4 testy) + `CardinalityProbeTest` (6) + `CostOptimizerTest` (5): 15 z 15 przechodzi (Terracotta 9510, ActiveMQ 51616 działają).
- Obserwacje techniczne: pierwsza kompilacja `mercury-lucene-indexes` po zmianie zgłosiła brak pakietu `org.mercury.lucene.handoff`, bo snapshot modułów w lokalnym repozytorium (`mercury/repo`) był nieaktualny. To nie był błąd chwilowy: autor uruchomił `mvn clean install -Dmaven.test.skip` w `mercury` (2026-11-14) i moduły się zaktualizowały (wcześniejsze przypuszczenie, że błąd był chwilowy, było błędne). Po aktualizacji `-pl` działa bez `-am`; zmiany w modułach `-api` (np. `LuceneProperty`) wymagają ponownej instalacji albo `-am`. `-Dtest` z kilkoma klasami po przecinku, nie `+`.
- Do zrobienia w etapie A: wskazówki w nagłówku planu poza decyzją nie są potrzebne (są w `DECISION`); przegląd pozostałych wywołań `costOptimization`; prezentacja planów w monitorze 113 (pomysł autora).

### Etap B: rdzeń kalibracji (2026-11-14, gałąź `hgdb-209` w `mercury`, bez commita)

Pakiet `org.mercury.lucene.calibration` w `mercury-lucene-indexes`:
- `PlanMode` (tryby `COST`, `ROOT_FIRST`, `CHILD_FIRST` ustawiane wskazówkami kontekstu), `PlanRun` (czas, trafienia, skrót zawartości, decyzje z planu, błąd), `PlanRunner` (interfejs wykonawcy: polecenie `LC` i testy dostarczają implementację).
- `QueryMeasurement` (czas obu planów stałych, próbki sondy dla każdego badanego limitu, status `OK`, `NO_SUBQUERY`, `MULTI_SUBQUERY`, `DIFFERENT_RESULTS`, `ERROR`, `NO_PROBE`), `CalibrationCriteria` (żal ≤ 1,25 albo różnica ≤ 100 ms; łagodniejsze 2,0 albo 500 ms; cel 90%).
- `ThresholdSweep` (czysta część obliczeniowa): decyzja jak w `CostOptimizer` (`nChild >= próg × nRoot`, pusty korzeń i obie liczności na limicie dają korzeń), czas wybranego planu = czas planu stałego + czas sondy dla danego limitu, ocena siatki (próg, limit), wybór: najwięcej spełnionych, potem najmniejsze maksimum żalu, czas w 2% od minimum, najmniejszy limit sondy, środek plateau progów; ostrzeżenia (cel nieosiągnięty, zapytania poza łagodnym kryterium, krawędź zakresu, mało zapytań ponad szumem).
- `CalibrationRunner`: każde zapytanie wykonuje się `runs` razy w obu planach stałych i raz w trybie kosztowym dla każdego limitu sondy (z pustą pamięcią sondy i tymczasowym nadpisaniem `lucene.query.cost.probeLimit`); limity liczby zapytań i czasu, przerwa po wykonaniu, `cancel()`, odbiorca wyników cząstkowych.
- `CalibrationReport`: raport tekstowy, CSV (po jednym wierszu na zapytanie, dla zapisu cząstkowego), fragment `lucene.properties` (bez zapisu do pliku).
- Zmiany wspierające: `PlanDecision.getProbeMs()` (czas sondy mierzony w `CostOptimizer.decide`), `QueryExplainPlan.getDecisions()`, `LuceneProperty.override()/clearOverride()` w `mercury-lucene-indexes-api` (nadpisanie parametru w procesie, pierwszeństwo przed plikiem).
- Testy: `ThresholdSweepTest` (6, model kosztu z 119: optimum progu ok. 0,115), `CalibrationRunnerTest` (5, fałszywy wykonawca: statusy, limity, przerwanie, zdjęcie nadpisania także po błędzie), `QueryExplainPlanDecisionTest.testCalibrationOnRealPlans` (kalibracja na prawdziwych planach i indeksie w pamięci: liczności 200/148/2 z planu, `NO_SUBQUERY` dla zapytania bez dziecka). Razem z testami etapu A: 26 z 26 przechodzi.
- Ograniczenia pierwszego wydania: jedna decyzja na zapytanie (kilka podzapytań = `MULTI_SUBQUERY`, pomijane); wynik obcięty limitem trafień (`truncated`) jest mierzony, ale czas zależy od limitu; dobór `refreshMs`, `maxHits` i parametrów zapisu poza zakresem.

### Etap C: generator zapytań z indeksu i plik zapytań (2026-11-14, gałąź `hgdb-209` w `mercury`, bez commita)

- `QueryFileParser`: plik UTF-8, jedno zapytanie w linii, `#` komentarz, opcjonalna nazwa przed tabulatorem; pomija duplikaty, puste i ucięte zapytania (zakończone „…” albo „...”, jak z monitora 113 przy przekroczeniu limitu długości) z ostrzeżeniem.
- `QueryGenerator` (tylko odczyt indeksu modelu 3.0): z `mrc_parentFields` wyznacza pola z dziećmi (nazwa z wielkością liter z pól `<pole>_mrc_Case_id`), próbkuje dokumenty dzieci i rodziców (co n-ty dokument listy wystąpień termu, deterministycznie), zbiera wartości atrybutów `_S`, liczy liczności tą samą sondą co optymalizator (`CardinalityProbe`, limit 10 mln) i wybiera zapytania równomiernie po log10(nChild/nRoot) w przedziałach po pół rzędu wielkości (domyślny zakres -3..3, `logRatioRange`), z różnorodnością pól i preferencją większych zbiorów. Zapytania mają postać `mrc_typeCodeValue:<rodzic> [AND <atrybut korzenia>:<wartość>] AND <pole>.mrc_typeCodeValue:<dziecko> AND <pole>.<atrybut>:<wartość>` (jak benchmarki 119). Atrybuty prawie unikalne (identyfikatory) są pomijane.
- Model 3.0 (sprawdzony na indeksie INEA, 22 028 880 dokumentów, 624 pola): każda sprawa to osobny dokument; rodzic ma pola `<pole>_mrc_Case_id` z identyfikatorami dzieci (37 pól), dziecko ma `mrc_parentFields` (pole rodzica małymi literami, 37 termów), `mrc_parentTypes` (typ rodzica) i `mrc_typeCodeValue` (typ dziecka); atrybuty w polach `<atrybut>_S`, `_N`, `_T`; pola są zapisane (Store.YES), więc próbkowanie czyta dokumenty.
- Walidacja na INEA 3.0 (`F:\mercury-indexes\20190705_Case_3.0`, kopia robocza, tylko odczyt): generowanie 1,4 do 2,8 s, 1107 kandydatów, 40 wybranych zapytań o log10(nChild/nRoot) od -2,7 do 2,8 z kilku pól (`serviceList`, `address`, `appMobileDetails`, `agreementList`, `activityList` i inne), korzenie od 669 do 550 981 trafień. Bez ograniczenia zakresu generator dawał też skrajne zapytania (nChild=2 przy 200 tys. korzeni, log10 = -5), które niczego nie kalibrują, stąd domyślny zakres.
- Testy: `QueryFileParserTest` (2), `QueryGeneratorTest` (4: rozpiętość stosunków co najmniej 2 rzędy wielkości, brak identyfikatorów w warunkach, deterministyczność dla ziarna, brak pól z dziećmi, równomierny wybór przedziałów) i `QueryExplainPlanDecisionTest.testGeneratedQueriesCalibrateOnRealPlans` (zapytania z generatora wykonują się na prawdziwym planie, status `OK`). Razem z etapami A i B: 23 z 23 w tym przebiegu.
- Ograniczenia: generator nie dodaje zakresów dat (zakres dat idzie w `additionalDateRange` osobnym parametrem, którego `PlanRunner` jeszcze nie przekazuje); liczności korzenia w wyborze nie uwzględniają klauzul systemowych planu (`mrc_status`, `mrc_typeIsDocumentType`), więc są przybliżone (kalibracja mierzy dokładne); próbka dokumentów (400) może pominąć bardzo rzadkie wartości; `MultiFields` zniknie w Lucene 9 (zadanie 191).
- Nie sprawdzono jeszcze wykonania wygenerowanych zapytań na pełnym indeksie przez prawdziwy kontekst (analizatory, bezpieczeństwo): to etap D (`LC` w `mercury-cmd`) i walidacja etapu E.

### Etap D: polecenie `-lc` w `mercury-cmd` (2026-11-14, gałąź `hgdb-209` w `mercury` i `mercury-cmd`, bez commita)

Decyzje autora (2026-11-14): polecenie działa w procesie na hoście węzła, zabezpieczenia węzła zaakceptowane, nazwa `LC`.

- `mercury` (`mercury-srv`): `CalibrationPlanRunnerFactory` (`pro.ibpm.mercury.lucene.searchers.data`, już skanowany pakiet, więc bez zmian w XML) tworzy `PlanRunner`, który robi to samo co `CaseSearcher#searchIndexRows` (parser z analizatorami mapera, czytnik indeksu Case, `QueryExplainPlan.prepare/execute`, kontekst bezpieczeństwa serwera), ustawia wskazówki trybu, wyłącza pamięć podręczną wyników, mierzy czas całości (plan z sondą i wykonanie), liczy skrót zawartości pierwszej strony wyniku i zwraca decyzje z planu. To zwykły komponent bez transakcji i proxy; API biblioteki (`mercury-lib`) bez zmian, więc `mercury-lib` nie wymaga wydania.
- `QueryFileParser.write/format`: zapis pliku zapytań w tym samym formacie, który czyta `parse` (nazwa, tabulator, zapytanie; nagłówek w komentarzach; nazwa zaczynająca się od `#` dostaje prefiks, tabulatory i końce linii w polach zamieniane na spacje); test przejścia w obie strony.
- `mercury-cmd` (`mercury-srv-cmd`): `CmdActionsEnum.LC` (`-lc`), `LuceneCalibrationAction` (opcje: `--queries`, `--generate`, `--seed`, `--save-queries`, `--out`, `--ratios`, `--limits`, `--runs`, `--max-queries`, `--max-seconds`, `--pause-ms`, `--noise-ms`, `--index-copy`, `--dry-run`, `--yes`), opis w pomocy `-?`. Wyniki w katalogu `--out`: `report.txt`, `measurements.csv` (po każdym zapytaniu, odporne na przerwanie), `queries.txt`, `recommended.properties`. `lucene.properties` nie jest zmieniany. Bez `--yes` polecenie pyta o potwierdzenie (bez konsoli odmawia). `--index-copy` wskazuje katalog z podkatalogiem `Case` (przez `LuceneConfig.changeIndexDir`).
- Testy: `LuceneCalibrationActionTest` (4, parsowanie opcji, pierwszy test w `mercury-srv-cmd`), w `mercury`: `QueryFileParserTest` (3 z zapisem), razem z etapami A-C: 18 z 18 w module `mercury-lucene-indexes` w ostatnim przebiegu; kompilacja `mercury-srv` z nową klasą przeszła.
- Budowanie lokalne: moduły `mercury-lucene-indexes-api`, `mercury-lucene-indexes` i `mercury-srv` zainstalowane jako `3.0.4-SNAPSHOT` (`mvn -o install -pl … -Dmaven.test.skip=true`), `mercury-srv-cmd` kompiluje się z `-Dmercury.srv.version=3.0.4-SNAPSHOT`. Wersje w POM-ach `mercury-cmd` zostają na wydanych (3.0.4.25); zmiana na nowe wydanie `mercury` należy do rytuału wydania (autor).
- **Nie sprawdzono:** uruchomienia polecenia na prawdziwym kontekście (Spring, baza, indeks węzła) przez `mercury-cmd.sh`; to zadanie etapu E (potrzebne środowisko z pakietem instalacyjnym, bazą z typami i indeksem). Zależność: pełny pomiar na indeksie INEA 3.0 wymaga też bazy z jego typami (mapper bierze pola z bazy), więc na INEA planuję pomiar przez wykonawcę testowego (`FakeCaseMapper`) jak w 119.

### Etap E: walidacja na indeksie INEA 3.0 (2026-11-14, `mercury`, gałąź `hgdb-209`, bez commita)

Pomiar: kopia indeksu `F:\mercury-indexes\20190705_Case_3.0` (22 028 880 dokumentów, tylko odczyt), test `LuceneCalibrationPerfTest` (wykonawca `FakeCaseMapper`, jak w 119), zapytania z generatora (40, `maxChildHits` 300 000) i z zestawu 119 (`LuceneLegacyIndexQueryTest`, test `testCalibrateLegacySet`). Wyniki zbiorcze: `kalibracja-inea-2026-11-14/` (`report-generator.txt`, `report-zestaw-119.txt`). Pliki z zapytaniami i pomiarami per zapytanie **nie są w repozytorium**: generator bierze wartości z indeksu i zapytania zawierają dane klientów (nazwiska, loginy, adresy), więc pliki zapytań z generatora i z monitora trzeba traktować jak dane osobowe.

Uruchomienie (wszystkie flagi są potrzebne; bez `-Dmercury.config.file` plan używa innych nazw pól systemowych i zwraca 0 trafień oraz `NullPointerException`):
`mvn -o test -pl mercury-lucene-indexes -Dtest=LuceneCalibrationPerfTest -Dperf.query=true -Dperf.typeCodeLower=true -Dperf.cal.legacy=true -Dperf.maxResults=1000000 -Dperf.cal.generate=40 -Dperf.cal.runs=2 -Dperf.cal.out=<katalog> -DadditionalArgLine=" -Dmercury.lucene.config.file=/properties/scichy/test-lucene-inea-maxhits1m.properties -Dmercury.config.file=/properties/scichy/test-mercury3.properties -Dsclogger.config.file=/properties/scichy/sclogger.properties -Xmx6g"` (spacja przed pierwszym `-D` chroni ścieżki w Git Bash; surefire tej wersji nie obsługuje `Klasa#metoda1+metoda2`).

Wyniki:
1. **Mechanizm działa od początku do końca:** 40 z 40 zapytań ze statusem `OK` (ten sam wynik w obu planach), czas pomiaru 8 minut (484 s i 435 s w dwóch przebiegach), żadnej awarii.
2. **Powtarzalność:** dwa niezależne przebiegi na tym samym indeksie dały to samo optimum i tę samą kolejność ocen. Liczba spełnionych zapytań dla progów: 0,5: 24/40; 2: 29/40; 8: 32/40; 32: 35/40; 64: 37/40; 128: 38/40; 256: 40/40 (żal maks. 1,15-1,17); 512 i więcej: 36/40.
3. **Wynik dla indeksu INEA w obecnym stanie silnika:** plan „dziecko najpierw” wygrywa w 36 z 40 zapytań; korzeń najpierw wygrywa dopiero przy `nChild/nRoot` rzędu 300 i więcej (dziecko: ok. 0,001 do 0,005 ms na trafienie, korzeń: czas rośnie z liczbą dzieci w łączeniu zbiorczym i ma stały narzut ok. 2 s). Optimum progu to ok. **256**, a domyślne **2,0** daje 29/40, żal do 7,9 i łączny czas 52-56 s wobec 21 s przy 256.
4. **Zestaw z 119** (20 użytecznych zapytań z 38; 11 bez podzapytania, 7 z dwoma podzapytaniami): próg 2: 19/20, 256 i więcej: 20/20, łączny czas 4,9 s wobec 3,5 s; tylko 4 zapytania ponad szumem 100 ms, więc wynik jest słaby, ale kierunek ten sam. Kalibracja z 119 (2,0) była optymalna dla silnika z tamtej chwili; od tamtej pory koszty planów się przesunęły (zgodnie z ostrzeżeniem z 119: „każda zmiana silnika przesuwa optimum progu”).
5. **Limit sondy `probeLimit`:** największa liczność w obu próbkach to ok. 550 tys., poniżej najmniejszego badanego limitu (1 mln), więc na tych danych limit nie ma wpływu na wynik; narzędzie po poprawce nie rekomenduje wtedy żadnej wartości i zostawia obecną. Pomiar limitu wymaga indeksu lub próbki z licznościami powyżej limitu (zapytania z milionami trafień dziecka są dziś wykluczone limitem `maxChildHits`).

**Decyzja autora (2026-11-14): nie zmieniamy `lucene.query.cost.childFirstRatio` (zostaje 2,0).** Poniższe zastrzeżenia zostają jako uzasadnienie. Pytanie wyjściowe: czy zmieniać domyślne `lucene.query.cost.childFirstRatio` (dziś 2,0). Moje zastrzeżenia: (a) próbka z generatora jest tendencyjna (duże dzieci, małe korzenie; odcięte dzieci powyżej 300 tys.), (b) to jeden indeks (INEA), (c) nie mierzono zakresów dat ani innych sortowań niż po `createDate`, (d) skok między 128 (38/40) a 256 (40/40) i spadek przy 512 (36/40) pokazują, że optimum jest ostre i zależy od kilku zapytań o skrajnych stosunkach. Rekomendacja: nie zmieniać domyślnej wartości na podstawie jednego indeksu; powtórzyć kalibrację na indeksie z innych środowisk (po wydaniu narzędzia `-lc`) i na zestawie prawdziwych zapytań z monitora (etap F).

Poprawki narzędzia wynikłe z walidacji: tryb `PROBE` (plan tylko przygotowany, liczności zbierane przed wykonaniem planów stałych, bez zbędnych wykonań w trybie kosztowym); opcja `maxChildHits` w generatorze (plan „dziecko najpierw” z milionami dzieci trwałby kilkanaście minut); domyślny zakres progów 0,05 do 1024 co dwukrotność i ostrzeżenie, gdy najlepsze progi sięgają krawędzi zakresu; limit sondy nierekomendowany, gdy żadna liczność go nie osiąga; tolerancja 0,05 dla maksimum żalu (różnice czasu sondy rzędu kilku ms to szum); test diagnostyczny `testExplainFirstQueries` (plany po wykonaniu z decyzją i czasami kroków, wykorzystany do znalezienia przyczyny zer).

Odkrycie przy okazji (zapisane jako obserwacja 169 w `docs/obserwacje.md`, kodu nie ruszano): przy limicie `lucene.query.maxHits` mniejszym niż liczność korzenia plan „korzeń najpierw” obcina **zbiór korzeni**, zanim zastosuje filtr dzieci, więc zwraca mniej wyników niż plan „dziecko najpierw” (np. 1034 wobec 2832 przy 550 981 korzeniach i `maxHits` 200 000; wynik oznaczony `truncated`). Ta sama obserwacja z 119 („dowód: po podniesieniu maxHits do 1 000 000 wyniki równe”); kalibrację trzeba robić z `maxHits` powyżej liczności korzeni (`test-lucene-inea-maxhits1m.properties`).

Ograniczenia: trzeci przebieg kontrolny został zatrzymany przez system (brak pamięci, doszedł do 37 z 40 zapytań) i nie jest używany; raporty zbiorcze w katalogu pochodzą z drugiego przebiegu i zawierają rekomendację sprzed poprawki limitu sondy (10 mln), którą należy czytać jako „limit nie sprawdzony”. Nie uruchamiano polecenia `-lc` przez `mercury-cmd.sh` (kontekst Spring, baza, indeks węzła).

### Etap F: rozszerzenie monitora z 113 (zakres dodany przez autora 2026-11-14, do zaprojektowania i wykonania)

Zlecenie autora: oprócz pokazywania planów zapytań monitor ma mieć przycisk **„Zapisz próbkę do kalibracji”**, który na podstawie danych monitora generuje plik do pobrania w formacie zapytań kalibracji (ten sam, który czyta `QueryFileParser` i który produkuje generator: `nazwa<TAB>zapytanie`, UTF-8, `#` komentarz).

Rozpoznanie (kod 2026-11-14):
- Monitor (`LuceneQueryMonitor`, `mercury-lucene-indexes-api`) trzyma w pamięci węzła ostatnie (domyślnie 200) i wolne zapytania z tekstem zapytania (ucięty do 10 000 znaków) oraz statystyki po odcisku (bez literałów). Rejestr jest per węzeł. REST: `LuceneQueriesExtRest` (`getQueriesState`, `resetQueriesStatistics`), strona `mercury-ws-app/src/main/webapp/static/admin/lucene-queries.html` (wywołania `fetch` z sesją użytkownika, przyciski w pasku narzędzi).
- Próbka do kalibracji potrzebuje prawdziwych literałów, więc źródłem są listy ostatnich i wolnych zapytań (statystyki po odcisku się nie nadają).

Propozycja projektu:
1. **Format pliku jednym kodem:** do `QueryFileParser` dochodzi zapisywanie (`write(List<Query>, nagłówek)`), używane przez monitor i przez polecenie `LC` (generator zapisuje swoje zapytania do pliku tym samym formatem). Powtarzalność: zapis i odczyt mają wspólny test w obie strony.
2. **Eksport z monitora:** nowa operacja `exportCalibrationSample` (parametry: źródło `recent|slow|both`, limit, opcja „tylko zapytania z podzapytaniem”, domyślnie włączona). Wybór: tylko zakończone bez błędu, rodzaje wyszukiwań, bez uciętych tekstów, bez duplikatów, nazwa wiersza bez danych użytkownika (np. `monitor <id> <czas> ms, trafień <n>`). Heurystyka „z podzapytaniem”: obecność składni `pole.atrybut:` (kalibracja i tak sklasyfikuje `NO_SUBQUERY`). Nagłówek pliku w komentarzach: węzeł, czas, próg wolnych zapytań, liczba pozycji.
3. **UI:** przycisk „Zapisz próbkę do kalibracji” (i wersje językowe jak w stronie) z ostrzeżeniem, że plik zawiera rzeczywiste wartości z zapytań (dane biznesowe); pobranie przez `Blob` z nazwą `lucene-calibration-sample-<węzeł>-<data>.txt`.
4. **Plany w monitorze:** w `LuceneQueryInfo` pole z planem po wykonaniu (`QueryExplainPlan.toString()` z decyzją i czasami kroków z etapu A) dla zapytań wolnych (limit rozmiaru i liczby planów), rozwijany wiersz w tabeli wolnych zapytań.
5. **Zmiana API:** nowa operacja w `ILuceneQueriesExtRest` oznacza obowiązki z reguły projektu: wpisy `openapi-docs_*.properties`, raport `openapi-doc-report.txt`, tłumaczenia (przez translator Gemini, nie ręcznie) i, jeśli nowe DTO trafi do `mercury-lib`, wydanie biblioteki. Do ustalenia: czy zwracać plik jako zwykły endpoint tekstowy (bez nowego DTO i bez wydania lib), czy jako kopertę `dto` jak pozostałe operacje.
6. **Dane osobowe i prywatność:** eksport robi użytkownik z uprawnieniem do strony monitora (jak reszta strony); plik trafia tylko do niego; w dokumentacji ostrzeżenie. Brak maskowania literałów (kalibracja wymaga prawdziwych wartości).

Do rozstrzygnięcia: kolejność wobec etapu D (rekomendacja: najpierw D, bo eksport z monitora zasila `LC`, ale format i zapis w `QueryFileParser` robimy już teraz); sposób zwracania pliku (punkt 5).

### Etap F: wykonanie (2026-11-14, `mercury`, `mercury-cmd`, docusaurus, gałąź `hgdb-209`, bez commita)

Zakres z projektu powyżej, z decyzjami: pomysł autora (monitor pokazuje plany) i przycisk „Zapisz próbkę do kalibracji”.
- `LuceneQueryInfo`: pola `plan` i `hasPlan`, `copyWithoutPlan()`. `LuceneQueryMonitor`: `Tracker.setPlanSupplier` (tekst planu powstaje po zakończeniu zapytania i tylko dla wolnego, przycinany do `mercury.lucene.query.monitor.planMaxChars`, domyślnie 20 000, `0` wyłącza), `findFinished(id)`. `QueryExplainPlan.execute` zgłasza plan trackerowi bieżącego zapytania (`this::toString`).
- `LuceneQueriesState` (odczyt stanu) zwraca listy bez treści planów (flaga `hasPlan`), bo strona odświeża je co kilka sekund; plan pobiera operacja `plan` po identyfikatorze.
- `SampleExporter` (`mercury-lucene-indexes`, pakiet `calibration`): z zakończonych zapytań monitora wybiera nadające się do ponownego wykonania (zakończone bez błędu; rodzaje `searchIndex`, `searchIndexRows`, `groupByQuery` bez dopisanej klauzuli grupowania; bez uciętych, bez duplikatów; domyślnie tylko z podzapytaniem `pole.atrybut:`), nazwy wierszy bez danych użytkownika, nagłówek z ostrzeżeniem o danych osobowych; zapis tym samym `QueryFileParser.format`.
- `mercury-ws-app`: `LuceneQueriesCalibration` (logika), `LuceneQueriesPanelController`: operacje `plan` i `calibrationSample` (tylko `mrc-sysadmin`, jak reszta strony), modele w `LuceneQueriesRestModel`. **Nie dodano ich do `LuceneQueriesExtRest`** (API OAuth), więc bez zmian w OpenAPI, bez kluczy tłumaczeń i bez wydania `mercury-lib`; można je tam dołożyć później.
- Strona `lucene-queries.html`: przycisk „Zapisz próbkę do kalibracji” (z potwierdzeniem o danych osobowych i opcją „tylko zapytania z podzapytaniem”, pobranie pliku przez `Blob`), kolumna „Plan” z przyciskiem rozwijającym plan pod wierszem (otwarte plany przeżywają automatyczne odświeżenie), teksty PL i EN.
- Testy: `LuceneQueryMonitorPlanTest` (6), `SampleExporterTest` (4), `QueryExplainPlanDecisionTest.testMonitorGetsThePlanOfASlowQuery` (prawdziwy plan wykonanego zapytania trafia do monitora z `DECISION` i `ACTUAL`), `LuceneQueriesCalibrationTest` (4, `mercury-ws-app`) i istniejący `LuceneQueriesStateTest`. W ostatnich przebiegach: `mercury-lucene-indexes-api` 20 z 20, `mercury-lucene-indexes` 32 z 32 (wybrane klasy), `mercury-ws-app` 8 z 8 (wybrane klasy).
- Nie sprawdzono w przeglądarce: strony `lucene-queries.html` (przycisk próbki, plany) nie uruchamiałem na działającym serwerze; kod JavaScript tylko przeczytany i dopasowany do istniejących wzorców strony.
- Uwaga: test `LuceneQueryMonitorPlanTest` używa progu 250 ms (próg 20 ms bywał przekraczany przy rozruchu JVM i szybkie zapytanie budowało plan).

### Dokumentacja (2026-11-14, gałąź `hgdb-209` w docusaurus-hgdb)

- Nowa strona `docs/005_Configuration/Lucene_optimizer_calibration.mdx` i jej odpowiednik PL (`i18n/pl/…`): jak optymalizator wybiera plan, polecenie `-lc` (opcje, bezpieczeństwo), źródła zapytań, co robi pomiar, wyniki, interpretacja (w tym wymóg `maxHits` powyżej liczności korzenia i ostrożny przykład z INEA: wartość domyślna nie została zmieniona).
- `Lucene_queries_monitor.mdx` (EN i PL): plany wolnych zapytań, przycisk próbki, parametr `planMaxChars`; odsyłacz w `003_Index_Lucene/index.mdx` (EN i PL).
- Uzupełnienie z zadania 241: polska wersja `Cache_configuration.mdx` nie miała rozdziału o awarii węzła i dzierżawie (dodano „Awaria węzła i spójność regionów” i opis `eventual` w tabeli regionów). Poprzednio zmieniono tylko wersję angielską.
- `mercury-cmd/README.md`: sekcja o poleceniu `-lc`; `docs/moduly/mercury-cmd.md`: wiersz `LC`.
- Sprawdzone: wszystkie zmienione pliki `.mdx` kompilują się (`@mdx-js/mdx`); strony nie budowano (`npm run build`).

### Pozostaje przed zamknięciem zadania 209

1. Commity, PR-y i merge (autor): `mercury` (gałąź `hgdb-209`), `mercury-cmd` (`hgdb-209`), docusaurus-hgdb (`hgdb-209`) i workspace; uwaga na zmiany w plikach generowanych `openapi*.json` i `ehcache-*-ext-3.5.xsd` w `mercury` (skutek `mvn install`, nie część zadania; przywrócić `git checkout`).
2. Wydanie `mercury` z nowym kodem i podniesienie wersji `mercury.srv.version` w `mercury-cmd` (rytuał wydania, autor); do tego czasu `mercury-srv-cmd` buduje się z `-Dmercury.srv.version=3.0.4-SNAPSHOT`.
3. Próba polecenia `-lc` na prawdziwym środowisku przez `mercury-cmd.sh` (kontekst Spring, baza, indeks węzła) oraz strony monitora w przeglądarce; nie wykonywano.
4. Decyzje podjęte: parametru `lucene.query.cost.childFirstRatio` nie zmieniamy; obserwacja 169 (obcinanie zbioru korzeni przy `maxHits`) zapisana, bez zmian w kodzie.

### Dalej (stan po etapie D)

Etap B: rdzeń kalibracji w `mercury-lucene-indexes` (`org.mercury.lucene.calibration`): pomiar planów ze wskazówkami, `nRoot`/`nChild` z `PlanDecision`, obliczenia i testy jednostkowe. Etap C: parser pliku zapytań i generator, raport. Etap D: polecenie `LC` w `mercury-cmd`. Etap E: walidacja na indeksie INEA 3.0.
