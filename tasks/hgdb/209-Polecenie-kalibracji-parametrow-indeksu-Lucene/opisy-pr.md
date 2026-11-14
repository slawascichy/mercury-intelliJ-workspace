# Opisy pull requestów, zadanie 209

Gałąź `hgdb-209` w czterech miejscach: `mercury` (kod), `mercury-cmd` (polecenie `-lc`), `docusaurus-hgdb` (dokumentacja EN i PL) i workspace (dokumentacja analizy). `mercury-docker` bez zmian. Kolejność merge: `mercury` → wydanie `mercury` (rytuał, numer podaje autor) → `mercury-cmd` (podniesienie `mercury.srv.version`) → `docusaurus-hgdb` → workspace. Stan na 2026-11-14: `mercury`, `mercury-cmd` i workspace mają po jednym commicie autora (pośredni, z etapami do D), a po nim dochodzą **niezacommitowane** zmiany etapów E i F oraz dokumentacji; `docusaurus-hgdb` jest w całości niezacommitowany. Liczby plików poniżej dotyczą stanu roboczego po tych commitach, a opisy obejmują całość zadania (commit i zmiany po nim).

**Przed commitem w `mercury`:** `git status` pokazuje też pliki generowane przez `mvn install`: `mercury-ws-app/src/main/resources/openapi/openapi*.json` i trzy `mercury-server/IBPM/mercury/config/ehcache-*-ext-3.5.xsd`. Nie należą do zadania: przywrócić `git checkout`.

## mercury (`hgdb-209`, 1 commit `1244d2d49`: 22 pliki, +3519/−35; po nim 24 pliki w stanie roboczym: 18 zmienionych i 6 nowych)

**Cel.** Narzędzie do kalibracji parametrów optymalizatora zapytań Lucene `lucene.query.cost.childFirstRatio` i `lucene.query.cost.probeLimit` na indeksie węzła (metoda ręczna z zadania 119 zautomatyzowana), a po drodze plan zapytania, który pokazuje decyzję optymalizatora i pomiar, oraz rozszerzenie monitora z zadania 113.

**Zmiany.**
- **Plan zapytania (`QueryExplainPlan`)**: nowa klasa `PlanDecision` (strategia `ROOT_FIRST`/`CHILD_FIRST`, powód, `nRoot`, `nChild`, próg, limit sondy, czas sondy, wskazówki kontekstu). `CostOptimizer.decide(...)` i `decideByWeights(...)` zwracają decyzję z uzasadnieniem; dotychczasowe `costOptimization(...)` (`boolean`) zostają jako opakowania. Plan zapisuje decyzję w kroku z podzapytaniem (`DECISION: …`, `decision` w JSON), po wykonaniu czas i trafienia kroku (`ACTUAL: … ms, hits=…`), a wynik z pamięci podręcznej wyników oznacza `RESULT FROM CACHE`. Koszty `Cost()` w planie nadal pochodzą ze starej reguły wagowej (plan o tym mówi); decyzja zapada na licznościach z sondy. `getDecisions()`.
- **Kalibracja** (`org.mercury.lucene.calibration` w `mercury-lucene-indexes`): `PlanMode` (w tym `PROBE`: plan tylko przygotowany, bez wykonania), `PlanRun`, `PlanRunner`, `QueryMeasurement`, `CalibrationCriteria` (kryterium z 119: żal ≤ 1,25 albo różnica ≤ 100 ms, cel 90%), `ThresholdSweep` (czysta symulacja siatki próg × limit sondy: czas wybranego planu plus czas sondy; wybór: najwięcej spełnionych, potem najmniejsze maksimum żalu z tolerancją 0,05, czas w 2%, najmniejszy limit, środek plateau; limit sondy nierekomendowany, gdy żadna liczność go nie osiąga), `CalibrationRunner` (limity liczby zapytań i czasu, przerwa, `cancel()`, wynik cząstkowy po każdym zapytaniu), `CalibrationReport` (tekst, CSV, fragment `lucene.properties`, nic nie zapisuje do konfiguracji). `LuceneProperty.override()/clearOverride()` w `mercury-lucene-indexes-api` (tymczasowe nadpisanie parametru w procesie, pierwszeństwo przed plikiem).
- **Zapytania do kalibracji**: `QueryFileParser` (odczyt i zapis pliku `nazwa<TAB>zapytanie`, `#` komentarz; pomija duplikaty i zapytania ucięte przez monitor) i `QueryGenerator` (z indeksu modelu 3.0: pola z dziećmi z `mrc_parentFields`, próbkowanie, liczności tą samą sondą, wybór równomierny po log10(nChild/nRoot), opcja `maxChildHits` chroniąca węzeł przed planem „dziecko najpierw” z milionami dzieci).
- **Wykonawca w serwerze**: `CalibrationPlanRunnerFactory` w `mercury-srv` (zwykły komponent bez proxy, w skanowanym pakiecie `pro.ibpm.mercury.lucene.searchers.data`), wykonuje plan jak `CaseSearcher#searchIndexRows`. API biblioteki (`mercury-lib`) bez zmian.
- **Monitor zapytań (113)**: `LuceneQueryInfo` (`plan`, `hasPlan`, `copyWithoutPlan()`), `LuceneQueryMonitor` (`Tracker.setPlanSupplier`: tekst planu powstaje po zakończeniu zapytania i tylko dla wolnego, przycinany do `mercury.lucene.query.monitor.planMaxChars`, domyślnie 20 000, `0` wyłącza; `findFinished(id)`), `SampleExporter` (próbka zapytań z monitora w formacie pliku zapytań, bez nazw użytkowników, z ostrzeżeniem o danych osobowych), `mercury-ws-app`: `LuceneQueriesPanelController` (operacje `plan` i `calibrationSample`, tylko `mrc-sysadmin`), `LuceneQueriesCalibration`, modele w `LuceneQueriesRestModel`, odczyt stanu bez treści planów (flaga `hasPlan`), strona `lucene-queries.html` (kolumna „Plan”, przycisk „Zapisz próbkę do kalibracji”, PL i EN). Operacji **nie dodano** do `LuceneQueriesExtRest` (API OAuth), więc bez zmian w OpenAPI i bez kluczy tłumaczeń.

**Wynik walidacji** (indeks INEA 3.0, 22 mln dokumentów, kopia tylko do odczytu, 40 wygenerowanych zapytań, dwa niezależne przebiegi po ok. 8 minut, 40 z 40 zapytań z tym samym wynikiem w obu planach): optimum progu wyszło ok. 256 (40/40, żal 1,15–1,17), a domyślne 2,0 daje 29/40 i łączny czas 52–56 s wobec 21 s; zestaw 41 zapytań z 119: próg 2: 19/20, próg 256: 20/20. **Wartości domyślnej nie zmieniono** (decyzja autora): próbka jest tendencyjna (duże dzieci, małe korzenie), to jeden indeks, nie mierzono zakresów dat; optimum jest ostre (128: 38/40, 256: 40/40, 512: 36/40). Raporty zbiorcze: `kalibracja-inea-2026-11-14/`.

**Testy.** `ThresholdSweepTest` (8), `CalibrationRunnerTest` (5), `QueryFileParserTest` (3), `QueryGeneratorTest` (5), `SampleExporterTest` (4), `QueryExplainPlanDecisionTest` (7, w tym kalibracja na prawdziwych planach, generator i monitor z planem), `LuceneQueryMonitorPlanTest` (6), `LuceneQueriesCalibrationTest` (4, `mercury-ws-app`), istniejące `CardinalityProbeTest` i `CostOptimizerTest` bez zmian (przechodzą). Pomiar na INEA: `LuceneCalibrationPerfTest` (tylko z `-Dperf.query=true`, komplet flag w pamięci projektu i w `TASK.md`).

**Nie sprawdzono.** Strony `lucene-queries.html` w przeglądarce (przycisk próbki, plany) ani polecenia na prawdziwym środowisku; kod JavaScript tylko przeczytany i dopasowany do wzorców strony.

**Ryzyka.** Plan zapytania ma teraz więcej tekstu w logu `DEBUG` i w monitorze (tylko wolne zapytania, ograniczone `planMaxChars`); `LuceneProperty.override` jest globalne w procesie (używa go tylko kalibracja i zdejmuje w `finally`). Zachowanie wyszukiwania i wybór planu bez zmian (`decide` to ta sama logika co `costOptimization`).

## mercury-cmd (`hgdb-209`, 1 commit `920328b`: 3 pliki, +526; po nim 3 pliki zmienione w stanie roboczym)

- Polecenie `-lc` (`CmdActionsEnum.LC`, `LuceneCalibrationAction` w `mercury-srv-cmd`): kalibracja na indeksie węzła w osobnym procesie na hoście węzła, indeks tylko do odczytu albo kopia (`--index-copy`), nie zmienia `lucene.properties`. Opcje: `--queries`, `--generate`, `--seed`, `--max-child-hits`, `--save-queries`, `--out`, `--ratios`, `--limits`, `--runs`, `--max-queries`, `--max-seconds`, `--pause-ms`, `--noise-ms`, `--index-copy`, `--dry-run`, `--yes`. Zabezpieczenia węzła: jeden wątek, limity, przerwa, potwierdzenie (bez konsoli odmawia bez `--yes`). Wyniki: `report.txt`, `measurements.csv` (po każdym zapytaniu), `queries.txt`, `recommended.properties`. Opis w pomocy `-?`.
- `LuceneCalibrationActionTest` (4, parsowanie opcji): pierwszy test w `mercury-srv-cmd`.
- `README.md`: sekcja o poleceniu `-lc`.
- **Zależność:** polecenie używa klas z `mercury` w tym PR-ze, więc wymaga wydania `mercury` i podniesienia `mercury.srv.version` (dziś 3.0.4.25); lokalnie buduje się z `-Dmercury.srv.version=3.0.4-SNAPSHOT`. Wersji w POM-ach nie zmieniano.
- Uwaga o zakończeniach linii: pliki w katalogu roboczym mają CRLF, a w indeksie LF; `git diff` z Git Bash pokazuje całe pliki, rzeczywista zmiana `CmdActionsEnum` to 12 linii.

## docusaurus-hgdb (`hgdb-209`, 7 plików niezacommitowanych, EN i PL)

- Nowa strona `docs/005_Configuration/Lucene_optimizer_calibration.mdx` i jej polska wersja: jak optymalizator wybiera plan, polecenie `-lc` (opcje, bezpieczeństwo), źródła zapytań (plik, generator, monitor), co robi pomiar, wyniki i raport, interpretacja (wymóg `maxHits` powyżej liczności korzenia, ostrożny przykład z INEA z informacją, że wartość domyślna nie została zmieniona), ostrzeżenie o danych osobowych w plikach zapytań.
- `Lucene_queries_monitor.mdx` (EN i PL): plany wolnych zapytań, przycisk próbki do kalibracji, parametr `planMaxChars`.
- `003_Index_Lucene/index.mdx` (EN i PL): odsyłacz do kalibracji przy parametrach zapytań.
- **Uzupełnienie zadania 241:** polska wersja `Cache_configuration.mdx` nie miała rozdziału o awarii węzła, dzierżawie połączenia i spójności `eventual` (wtedy zmieniono tylko wersję angielską); dodano „Awaria węzła i spójność regionów” i opis `eventual` w tabeli regionów.
- Składnia MDX sprawdzona kompilatorem `@mdx-js/mdx` (8 plików OK); pełnego `docusaurus build` nie uruchamiano.

## workspace (`main`, 1 commit `342c31a` z etapami do D; po nim zmiany w stanie roboczym)

- `tasks/hgdb/209-…/TASK.md`: rozpoznanie, projekt, etapy A-F, walidacja na INEA, decyzje autora, lista tego, co zostaje; `kalibracja-inea-2026-11-14/` (raporty zbiorcze bez danych osobowych); ten plik.
- `docs/obserwacje.md`: obserwacja 169 (plan „korzeń najpierw” obcina zbiór korzeni limitem `maxHits` przed filtrem dzieci, więc wynik zależy od planu; mechanizm to przypuszczenie do sprawdzenia w kodzie).
- `docs/moduly/mercury-cmd.md`: wiersz `LC`.
- W stanie roboczym są też zmiany spoza zadania 209: staged `tasks/hgdb-utils/011-…` i `tasks/hgdb/056-…` (TASK.md i obrazy), `tasks/workspace.txt` (prywatny notatnik, pomijać).

## Do zrobienia po merge

- Wydanie `mercury` (numer podaje autor), potem w `mercury-cmd` `set-versions` albo ręczna zmiana `mercury.srv.version` i budowa pakietu; zaciągnąć `master` (`mercury`, `mercury-cmd`) i `main` (`docusaurus-hgdb`, workspace), zamknąć zadanie 209 na GitHubie, dopiero potem zakładać gałąź następnego zadania.
- Próba polecenia `-lc` na środowisku z pakietem instalacyjnym (kontekst Spring, baza, indeks węzła) i strony monitora w przeglądarce.
- Poza zakresem 209: sprawdzić w kodzie mechanizm z obserwacji 169; powtórzyć kalibrację na indeksach z innych środowisk i na próbce prawdziwych zapytań z monitora, zanim ktokolwiek rozważy zmianę `childFirstRatio`; przy zadaniu 191 (Lucene 9) dostosować `MultiFields` w generatorze i `TopDocs.totalHits` w `stepHits()` oraz powtórzyć kalibrację.
