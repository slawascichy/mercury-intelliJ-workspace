# [219] Wydajność generowania plików Excel (eksport i serwer Iron POI)

https://github.com/slawascichy/hgdb/issues/219

**Status (2026-10-29):** zadanie analizy założone po teście eksportu widoków (zadanie 016, etap 3). Nic nie zmieniono w kodzie. Poniżej cel, dotychczasowe pomiary, hipotezy, plan analizy i decyzje do podjęcia. Metodyka wzorowana na zadaniu 119 (optymalizacja zapytań Lucene): najpierw powtarzalny pomiar bazowy, potem rozbicie czasu na warstwy, dopiero potem zmiany.

## Cel (autor)

Podnieść wydajność całego systemu generowania plików Excel. Zakres obejmuje obie strony: `mercury` (odczyt danych, konwersja wartości, wysyłka stron) i serwer Iron POI (`D:\workspace\git\poi-toolkit`, też kod autora), bo czas może być stracony w każdej z nich. Analiza ma wskazać, gdzie jest wąskie gardło, i zaproponować zmiany z oczekiwanym zyskiem. Wdrożenie zmian to osobne zadania.

## Obserwacja wyjściowa (2026-10-29, serwer dev)

Eksport widoku `Vw016Slm` (zadanie 016) do pliku xlsx przez `ExportGenerator` i serwer Iron POI:

| Eksport | Wiersze | Kolumny | Start | Koniec (czas pliku) | Czas | Szybkość |
|---|---|---|---|---|---|---|
| `tester`, rola `vw016-addr` | 100 000 (`SlmAddress`) | 6, tekst | 17:57:37 | ok. 18:01 | ok. 3,5–4 min | ok. 450 wierszy/s |
| `admin`, pełny dostęp | 200 000 (dwa typy) | 6, tekst | 18:12:33 | 18:28:04 | 15,5 min | ok. 215 wierszy/s (ok. 1,3 tys. komórek/s) |

Strony po 1000 wierszy (`mercury.view.maxPageSize`), postęp narastał mniej więcej liniowo (ok. 3% na 20 s). Czasy pochodzą z czasu modyfikacji plików i z `ReportExportStatus`, a nie z pomiaru w kodzie, więc są przybliżone.

Dla porównania (z wiedzy, niezmierzone na tym środowisku; do zweryfikowania w etapie 1): strumieniowe biblioteki xlsx (Apache POI SXSSF, XlsxWriter, openpyxl w trybie write-only) zapisują takie dane w kilkanaście do kilkudziesięciu sekund, a eksport do CSV z bazy trwa około sekundy. Wniosek wstępny: czas jest o 1–2 rzędy wielkości większy, niż wynika z samego formatu, więc to nie jest cena xlsx.

## Ścieżka eksportu (zweryfikowane w kodzie)

1. `ReportExportSecretary` (pula wątków `ExportSecretary`) bierze raport `WAITING` i wywołuje `ExportGenerator.generateReport`.
2. Eksport widoku: `generateViewReport` czyta kolejne strony `ICaseViewDefinitionLogic.readViewData` (zapytanie SQL z `LIMIT`/`OFFSET`, filtr wierszy i maskowanie), potem `PoiServerWriter.convertViewPage` (dekodowanie wartości przez `AttributeParser`), potem zapis strony przez RMI (`IWriteRemote.write`) w jednej transakcji serwera POI, na końcu `commitTransaction`.
3. Eksport spraw: ta sama ścieżka, ale dane z Lucene (`caseLogic.searchByQuery`) i konwersja `convertCollectionByStream` (pula `ForkJoinPool` z 5 wątkami).
4. Serwer Iron POI: `ExcelFileWriter` (m.in. `startNewSheet`, `insertRow`, `createCell`, style kolumn), menedżer transakcji `ExcelFileWriterTransactionManager`.

## Hipotezy (do zweryfikowania, żadna nie jest potwierdzona)

| # | Hipoteza | Gdzie sprawdzić |
|---|---|---|
| H1 | Zapis do pliku w serwerze POI jest kosztowny na stronę (style komórek, stan arkusza, brak strumieniowania, zapis całości przy `commit`) | `ExcelFileWriter`, `ExcelFileWriterTransactionManager`, profil po stronie POI |
| H2 | Dekodowanie ok. 1,2 mln wartości przez `AttributeParser` (z odwołaniami do zasobów) jest wolne, a przy widoku wykonywane jednowątkowo (eksport spraw ma pulę 5 wątków) | `PoiServerWriter.convertViewPage`, mikropomiar na gotowych stronach |
| H3 | Serializacja i przesył strony przez RMI (obiekt `ExcelFileWriterData` z 1000 wierszami) jest kosztowny | rozmiar i czas wywołania `IWriteRemote.write` |
| H4 | Odczyt stron widoku z `OFFSET` rośnie wraz z numerem strony (koszt `O(strona × rozmiar)`) | `EXPLAIN ANALYZE` kolejnych stron, porównanie z paginacją po kluczu |
| H5 | Przetwarzanie sekwencyjne: czytanie, konwersja i zapis nie nakładają się na siebie (potok mógłby być równoległy) | pomiar czasów faz na stronę |
| H6 | Pamięć i GC po stronie POI (alokacja cache 512 MB `ehcache` przy starcie, duże arkusze) | logi GC, profil pamięci |

## Plan analizy

- **Etap 0: stanowisko pomiarowe.** Zestaw danych (widok z ok. 200 000 wierszy, wersja z polami dat i liczb, bo dotychczasowe typy testowe mają same pola tekstowe), skrypt zlecający eksport i zbierający czasy, plik CSV z wynikiem bazowym (jak `baseline-*.csv` w zadaniu 119). Maszyna i dysk opisane przy pomiarze (kopie robocze na szybszym dysku).
- **Etap 1: rozbicie czasu na warstwy.** Tymczasowe logowanie czasu faz dla każdej strony (odczyt, konwersja, zapis RMI, zapis po stronie POI), profil JFR (Java Flight Recorder) dla `mercury` i serwera POI, rozmiar strony po serializacji. Wynik: tabela, ile procent czasu zajmuje każda warstwa.
- **Etap 2: dolna granica.** Samodzielny program zapisujący tyle samo danych (200 000 × 6) przez POI SXSSF i inny strumieniowy zapis, na tej samej maszynie. To pokazuje, ile powinno trwać samo pisanie xlsx.
- **Etap 3: weryfikacja hipotez i kandydaci na poprawki.** Dla każdej potwierdzonej hipotezy propozycja zmiany z szacowanym zyskiem, np.: strumieniowy zapis w POI, potok odczyt–konwersja–zapis w kilku wątkach, buforowanie definicji pól i wyników dekodowania na kolumnę, większe strony po stronie wysyłki, paginacja po kluczu, mniejszy narzut RMI.
- **Etap 4: decyzje i zadania wdrożeniowe.** Zatwierdzone poprawki jako osobne zadania z testami wydajności i regresji (poprawność plików, maskowanie, typy kolumn).

## Pytania do autora

1. Jaki jest cel (np. 200 000 × 6 poniżej minuty) i jakie wolumeny uznajemy za typowe oraz graniczne (limit 1 048 576 wierszy w arkuszu)?
2. Czy serwer POI musi zachować dotychczasowe zachowania, od których mogą zależeć klienci (szablony `tfn`, style kolumn, zapis stronami w transakcji, odczyt `load`)? To ogranicza zmianę na strumieniowy zapis.
3. Czy oprócz xlsx rozważamy inne formaty wyniku (np. CSV) jako szybką ścieżkę dla bardzo dużych eksportów?
4. Czy analiza obejmuje także odczyt plików (import, `ExcelFileReader`, `load` dla podglądu), czy tylko zapis?
5. Którą maszynę i które dyski uznajemy za środowisko pomiarowe?

## Definicja Gotowości

- Powtarzalny pomiar bazowy zapisany (skrypt i plik CSV) wraz z opisem środowiska.
- Rozbicie czasu eksportu na warstwy dla widoku i dla eksportu spraw.
- Wskazane wąskie gardła z dowodem (pomiar lub profil), a nie przypuszczeniem.
- Lista poprawek z oszacowanym zyskiem i ryzykiem, uzgodniona z autorem, oraz założone zadania wdrożeniowe.
- Obserwacje wynikłe z analizy dopisane do `docs/obserwacje.md`.

## Powiązania

- Zadanie 016 (Widoki), etap 3: eksport i podgląd widoków (`../016-Widoki/TASK.md`, sekcje „Etap 3”).
- Obserwacje 114 (nadmiarowa kolumna w eksporcie spraw), 115 (nieodświeżany stub RMI po restarcie POI), 116 (kolejka raportów i zawieszone `PROCESSING`).
- Zadanie 119: wzorzec metodyki (pomiar bazowy, analiza, decyzje, pomiar końcowy).
- Kod: `mercury-srv` (`ExportGenerator`, `PoiServerWriter`, `PoiServerLoader`, `ReportSecretarySupport`), `mercury-ws-app` (`ReportExportStatusRest`, `CaseViewExtRest`), `D:\workspace\git\poi-toolkit` (`ExcelFileWriter`, `ExcelFileWriterTransactionManager`, `WriteHandler`).

## Decyzje autora (2026-11-17)

1. **Cel:** 200 000 wierszy × 6 kolumn poniżej minuty (zatwierdzone jako cel robocza).
2. **Serwer Iron POI:** zachować API (szablony `tfn`, style kolumn, zapis stronami w transakcji, odczyt `load`), ale POI może wymagać modernizacji, jeśli okaże się wąskim gardłem.
3. **CSV:** dodać argument wyboru formatu wyniku (xlsx albo csv), domyślnie xlsx; wymaga zmian po stronie POI.
4. **Zakres:** odczyt i zapis (import, `ExcelFileReader`, `load` także w analizie).
5. **Środowisko pomiarowe:** maszyna lokalna; można korzystać z Kubernetesa (`mercury-test`), po aktualizacji przez autora także z kompozycji na `devops-box-01`.

Gałęzie `hgdb-219` w `mercury` i `poi-toolkit` (od `master` po wydaniu 3.0.4.28).

## Etap 2: dolna granica po stronie serwera POI (2026-11-17)

Test `WriterBenchmarkTest` (`poi-toolkit/src/test/java/org/iron/poi/excel/`, gałąź `hgdb-219`, włączany `-Dbench.rows=<N>`; parametry `bench.cols`, `bench.pageSize`, `bench.types`) zapisuje syntetyczne strony (1000 wierszy) przez prawdziwy `ExcelFileWriter` (`load` stron, potem `commit`), bez bazy, RMI i konwersji wartości z Mercury. Uruchomienie: `mvn -o test -Dtest=WriterBenchmarkTest -Dbench.rows=200000` w `poi-toolkit`. Maszyna lokalna autora, Java 8.

| Dane | Generowanie stron | `writer.load` (200 stron) | `commit` (zapis pliku) | Razem | Plik | Sterta po |
|---|---|---|---|---|---|---|
| 200 000 × 6, same teksty | 171 ms | 9 ms | 4 284 ms | 5,1 s | 6,2 MB | 641 MB |
| 200 000 × 6, typy `STRING,INTEGER,BIGDECIMAL,DATE,STRING,STRING` | 655 ms | 3 ms | 5 229 ms | 6,5 s | 7,6 MB | 271 MB |
| 20 000 × 6, teksty (rozgrzewka) | 27 ms | 1 ms | 1 568 ms | 2,2 s | 0,6 MB | 72 MB |

**Wniosek:** sam zapis xlsx w serwerze POI (cały wolumen docelowy) trwa ok. 5–6 s (ponad 38 000 wierszy/s), czyli ok. 180 razy szybciej niż zmierzone eksporty (ok. 215 wierszy/s; 200 000 wierszy w 15,5 min). Hipoteza H1 (zapis pliku w POI jest kosztowny) **nie potwierdza się** dla rdzenia zapisu: czas jest gdzie indziej (H2 konwersja wartości, H3 przesył RMI, H4 odczyt stron z `OFFSET`, H5 brak nakładania faz, a po stronie POI jeszcze warstwa RMI/serializacji i konfiguracja serwera). Pamięć: zapis trzyma wszystkie wiersze w pamięci do `commit` (dla tekstu ok. 640 MB przy 200 000 × 6), co jest ryzykiem dla większych wolumenów (limit arkusza 1 048 576 wierszy).
Dla porównania z technikami strumieniowymi (SXSSF) nie było potrzeby, bo rdzeń zapisu już mieści się w celu (poniżej minuty z dużym zapasem).

## Etap 1: instrumentacja czasów faz (2026-11-17, gałąź `hgdb-219` w `mercury`)

`ExportGenerator.generateViewReport` (eksport widoku) mierzy teraz sumaryczne czasy faz i zapisuje jedną linię `INFO` po zakończeniu eksportu: `-->generateViewReport[<wątek>]: widok '<nazwa>': stron: N, wierszy: M, razem: T ms (odczyt: … ms, konwersja: … ms, zapis stron do POI: … ms, zapis pliku (commit): … ms)`. Klasa pomocnicza `PhaseTimes` (koszt pomiaru: cztery wywołania `System.nanoTime()` na stronę). Eksport spraw (ścieżka Lucene) jeszcze nieoznaczony.

**Do zrobienia (potrzebuje działającego środowiska):** eksport widoku o ok. 200 000 wierszy (np. `Vw016Slm` z zadania 016) na serwerze z działającym serwerem Iron POI i odczyt tej linii z logu; potem rozbicie warstw (RMI, serializacja strony), profil JFR dla `mercury` i serwera POI oraz `EXPLAIN ANALYZE` kolejnych stron widoku (H4).

## Pamięć na Kubernetesie `mercury-test` (2026-11-17)

**Problem:** ładowanie danych do pomiaru (typ `Bench219`) zabiło `mercury-node1` (`OOMKilled`, kod 137) przy ok. 65 000 z 200 000 spraw. Węzły robocze miały 6,4 GB, a chart miał tylko `requests` (bez `limits`); JVM Mercury `-Xmx4098m` plus PostgreSQL i ehcache (Terracotta `-Xmx2049m` + 1024 MB poza stertą) wyczerpały pamięć węzła.

**Pomiar zużycia** (cgroup, po załadowaniu 67 000 spraw): `mercury-node1` 3,8 GiB, ehcache 0,65, ActiveMQ 0,55, PostgreSQL 0,43, serwer POI 0,14, LDAP 0,03, balanser 0,03 GiB. Serwer POI nie ma `-Xmx` w obrazie (JVM ze sterty 25% pamięci), PostgreSQL ma `shared_buffers` 128 MB.

**Zmiana (`mercury-docker`, gałąź `hgdb-219`, chart `mercury-single-node`, niezacommitowane):**
- `values.yaml`: `requests` i `limits` dla wszystkich kontenerów (Mercury 5Gi/6Gi, ehcache 1536Mi/3Gi, PostgreSQL 1Gi/1536Mi, ActiveMQ 768Mi/1536Mi, POI 768Mi/2Gi, LDAP, balanser); założenie: dwa węzły po 8 GB.
- `javaOptions.poiServer: "-XX:MaxRAMPercentage=65.0"` (zmienna `JAVA_TOOL_OPTIONS` serwera POI; z limitem 2Gi sterta ok. 1,3 GiB; w Javie 8 wartość procentowa wymaga części dziesiętnej: `65` powodował błąd „Improperly specified VM option”).
- `affinity.mercuryNode`: miękka (preferowana) anty-afiniczność węzła Mercury względem PostgreSQL i ehcache. Efekt: `mercury-node1` i balanser na `k8s-worker1`, pozostałe na `k8s-worker2`.
- `charts/README.md`: sekcja „Memory configuration”.
- `helm upgrade` na `mercury-test`: rewizje 8 i 9; 7 z 7 podów gotowe, wszystkie bez restartów. Stare `requests` (z 2026-11-14) zastąpione. `helm lint` zgłasza błąd `Chart.yaml` (apiVersion v1 z polem `type`), istniejący wcześniej i niezwiązany z tą zmianą.
- Węzły robocze po zwiększeniu RAM do 8 GB: 7,1 GiB do przydziału (wcześniej 6,2 GiB).
