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

## Etap 0/1: pomiar eksportu widoku na `mercury-test` (2026-11-18)

Środowisko: Kubernetes `mercury-test` (węzły robocze 8 GB, chart z limitami pamięci), `mercury` 3.0.4.28, widok `T_Bench219` (typ `Bench219`, 200 007 spraw, 6 pól: cztery tekstowe, `Decimal`, `Integer`), strony po 1000, użytkownik `admin`. Eksport zlecany `ReportExportStatusRest/prepareReportRequest` (`viewName`, `ps`), czas liczony od zlecenia do `COMPLETED` (`export219.py`, odpytywanie co 5 s).

**Najpierw błędy środowiska, które uniemożliwiały eksport na Kubernetesie** (obserwacja 172): usługa `poi-server-node1` miała tylko port 10090, a serwer POI używa RMI na 10099, 10100 i 10101 (zrzut wątków: `ExportSecretary` stoi w `socketConnect` przy `RegistryImpl_Stub.lookup`); po dodaniu portów stub RMI wskazywał `localhost`, bo skrypt startowy ma `HOST_NAME=localhost` na sztywno. Poprawione w chartcie i skrypcie (gałąź `hgdb-219` w `mercury-docker`), na `mercury-test` zastosowane tymczasowo (ConfigMap + zmienna `HOST_NAME`).

**Wynik bazowy (wersja 3.0.4.28 bez instrumentacji):** eksport 200 007 wierszy × 6 kolumn: **60,7 s** (`COMPLETED`), czyli ok. 3 300 wierszy/s. Postęp co 5 s: 12, 24, 36, 46, 56, 66, 74, 82 … 100% (zwalnia pod koniec: ok. 12% na 5 s na początku, ok. 8% na końcu). Dla porównania zmierzony 29.10 na dev eksport 200 000 wierszy widoku nad dwoma typami z dekodowaniem trwał ok. 15,5 min (inne dane i środowisko, więc nieporównywalne wprost).

**Rozbicie czasu odczytu z bazy** (`psql`, `\timing` i `EXPLAIN ANALYZE`, widok `T_Bench219`): `readViewData` wykonuje dla **każdej** strony `SELECT COUNT(*) FROM <widok>` (164 ms) oraz `SELECT … ORDER BY 1 LIMIT 1000 OFFSET (n-1)*1000` (strona 1: 0,9 ms, `OFFSET 100 000`: 81 ms, `OFFSET 199 000`: 156 ms). Dla 200 stron: zliczanie ok. 33 s, rosnący `OFFSET` ok. 16 s, razem **ok. 48 s z 60,7 s (ok. 80%)**. Pozostałe ok. 13 s to konwersja stron, zapis stron do POI przez RMI i `commit`. Potwierdza H4 (koszt `OFFSET`) i odkrywa nową przyczynę: zliczanie przy każdej stronie (obserwacje 173 i 174).

**Hipotezy po pomiarach:** H1 (zapis pliku w POI): odrzucona (5–6 s dla całego wolumenu); H4 (`OFFSET`): potwierdzona; nowa: zbędne `COUNT(*)` na każdej stronie; H2 (konwersja) i H3 (RMI): razem co najwyżej ok. 13 s, do rozbicia instrumentacją; H5 (brak nakładania faz): drugorzędna, bo odczyt jest 80% czasu.

**Kandydaci na poprawki (do akceptacji):** (1) zliczanie tylko przy pierwszej stronie, (2) stronicowanie po kluczu (`id`) w eksporcie, (3) dopiero potem potok odczyt–konwersja–zapis, (4) argument formatu `csv` w POI, (5) odświeżanie klienta RMI przy błędzie połączenia i krótszy czas oczekiwania na połączenie (obserwacja 115: po odtworzeniu poda POI Mercury trzymał nieważne połączenie). Oczekiwany efekt (1)+(2): odczyt z ok. 48 s do ułamka sekundy na strony, a eksport z ok. 61 s do ok. 13 s (do potwierdzenia pomiarem).

## Odświeżanie klienta RMI serwera POI (2026-11-18, obserwacja 115 ✅)

`mercury-core-server`, pakiet `org.mercury.rmi.clients`: nowy `PoiRmiInvoker` (wspólny dla `PoiServerLoaderClient` i `PoiServerWriterClient`); `RmiClientServices` ma limit czasu połączenia z rejestrem (własna `RMIClientSocketFactory`) oraz klasyfikację błędów.
- Po utracie połączenia (`NoSuchObjectException`, `ConnectException`, `ConnectIOException`, także jako przyczyna) klient porzuca stub, czeka (opóźnienie rośnie: 1, 2, 3 s), wyszukuje usługę od nowa i ponawia wywołanie, domyślnie 3 razy. Ponawiane są tylko błędy, przy których wywołanie na pewno nie wykonało się na serwerze; zerwanie w trakcie wywołania jest zgłaszane bez ponawiania.
- Konfiguracja (`mercury.properties`): `mercury.poi.rmi.connectTimeoutMs` (5000, 0 wyłącza), `mercury.poi.rmi.retries` (3, 0 wyłącza), `mercury.poi.rmi.retryDelayMs` (1000).
- Usunięto sprawdzenie `echo` przed każdym wywołaniem (podwajało liczbę wywołań RMI: ok. 400 dodatkowych na eksport 200 stron).
- Ograniczenie: transakcja zapisu pliku żyje w pamięci serwera POI; po jego restarcie w trakcie eksportu nie da się jej dokończyć, więc taki eksport kończy się błędem (odświeżenie pomaga następnym eksportom i rozpoczęciu nowej transakcji).
- Testy: `PoiRmiInvokerTest` (8) przechodzi; na `mercury-test` po wymianie poda POI eksport zakończył się powodzeniem bez restartu Mercury (log: `NoSuchObjectException: no such object in table`, ponowienie po 1 s). Jar został tam wdrożony tymczasowo przez ConfigMap z `subPath` (klasa jest we wspólnym `lib` Tomcata).

## Stronicowanie widoków: zliczanie i klucz (analiza, 2026-11-18, do decyzji autora)

**1. Czy zliczanie ma ukrytą funkcję korekcji?** Nie. Przejrzane: `CaseViewDefinitionDAO.readViewData` (zapytanie `SELECT COUNT(*)` przy każdej stronie), `CaseViewDefinitionLogic` (z liczby wierszy wylicza informacje o stronach: bieżąca, pierwsza, ostatnia, poprzednia, następna, wiersze 500–509) i `ExportGenerator.generateViewReport`. Eksport używa liczby tylko do (a) sprawdzenia, czy widok nie jest pusty, (b) wyliczenia numeru ostatniej strony **raz, przy pierwszej stronie** (pętla `pageNumber <= lastPageNumber`) i (c) postępu. Kolejne zliczenia na stronach 2…N są **wyrzucane**: nikt ich nie porównuje z pierwszym. Skutek zmiany danych w trakcie eksportu przy `OFFSET`: dodane wiersze nigdy nie wejdą do pliku (ostatnia strona jest ustalona), a usunięte lub dodane przed bieżącą pozycją przesuwają strony (duplikaty albo pominięcia). Zliczanie na każdej stronie niczemu więc nie służy w eksporcie, ale dla **podglądu** (GUI, REST) liczba wierszy i numer ostatniej strony są częścią kontraktu „PagedResult” (tak samo jak przy wynikach Lucene).

**Co gdy informacja o liczbie „zniknie” (strona pobierana osobnym żądaniem, może trafić na inny węzeł)?** Serwer jest bezstanowy: nic o liczbie nie jest trzymane między żądaniami, każde żądanie niesie wszystko, czego potrzebuje. Zliczanie powinno być więc **parametrem żądania, a nie stanem**:
- domyślnie jak dziś (`EXACT`: liczba i informacje o stronach w każdej odpowiedzi), więc podgląd i klienci się nie zmieniają;
- opcjonalnie bez zliczania (`NONE`): odpowiedź nie ma liczby ani numeru ostatniej strony, ale ma **`hasNext`** (odczyt `rozmiar + 1` wierszy), więc klient nawiguje „dalej/wstecz” z dowolnego węzła; kto potrzebuje ostatniej strony albo sumy, prosi o `EXACT` jednym żądaniem (nie przy każdej stronie);
- dla bardzo dużych widoków możliwe zliczanie szacunkowe albo z krótkotrwałą pamięcią podręczną (klucz: widok, filtry, ograniczenia użytkownika; zadanie osobne, bo trzeba zdecydować o nieaktualności liczby).
Eksport nie powinien zależeć od liczby: pętla kończy się, gdy strona jest krótsza niż rozmiar (`hasNext = false`); liczba z pierwszej strony służy tylko do postępu (ograniczonego do 100%).

**2. Klucz, `ORDER BY 1` i JDBC.**
- `ORDER BY 1` to **pierwsza kolumna widoku**: dla widoków typów (`T_<kod>`) i widoku `Vw016Slm` jest to `m_id`, czyli identyfikator sprawy (`character varying`, np. `Bench219.123456`, unikalny, z indeksem klucza głównego `igo_da_cases_pkey`, plan używa `Index Scan`). Sortowanie tekstowe (kolejność leksykograficzna, `Bench219.10` przed `Bench219.9`) nie przeszkadza stronicowaniu: liczy się porządek **całkowity i taki sam** w `ORDER BY` i w warunku `>`, a oba używają kolacji bazy. Słabość: zależność od „pierwszej kolumny”; dla widoku zarejestrowanego ręcznie pierwsza kolumna może nie być unikalnym kluczem, więc w definicji widoku trzeba wskazać **kolumnę klucza** (domyślnie `M_ID`).
- Widok generowany zawiera `SELECT DISTINCT` (plan: węzeł `Unique` i `Incremental Sort` po wszystkich kolumnach); warunek na `m_id` jest mimo to wpychany do skanu (`Index Cond: id > $1`, odczyt ok. 1 025 wierszy), więc stronicowanie po kluczu działa także na takim widoku. `DISTINCT` jest osobnym kosztem (zliczanie 164 ms), do rozważenia w obserwacji.
- Dziś DAO używa JPA (`setFirstResult` i `setMaxResults`), czyli `LIMIT/OFFSET`, a **nie** mechanizmu pobierania JDBC (`fetchSize`, kursor). Strumieniowanie w PostgreSQL wymaga: transakcji (autocommit wyłączony), wyniku „tylko do przodu” i `fetchSize > 0` (w Hibernate `ScrollableResults` z `ScrollMode.FORWARD_ONLY` i `setFetchSize`).

**Pomiar trzech sposobów** (`psql`, widok `T_Bench219`, 200 007 wierszy, strony po 1000):

| Sposób | Strona na początku | Strona na głębokości 100 000 | Strona na głębokości 199 000 | Cały eksport (200 stron) |
|---|---|---|---|---|
| `LIMIT/OFFSET` + `COUNT(*)` na stronę (dziś) | 0,9 ms + 164 ms | 81 ms + 164 ms | 156 ms + 164 ms | ok. 49 s (33 s zliczanie + 16 s `OFFSET`) |
| po kluczu (`WHERE m_id > :ostatni ORDER BY m_id LIMIT n`) | ok. 1 ms | ok. 1–2 ms (odczyt ok. 1 025 wierszy) | ok. 1–2 ms | ok. 0,3 s |
| kursor po stronie serwera (jedno zapytanie, `fetch 1000`) | 1,7 ms | 1,5 ms (po pominięciu 99 000 w 78 ms) | 1,5 ms | ok. 0,5 s |

**Rekomendacja:** w eksporcie **stronicowanie po kluczu**: krótkie, niezależne transakcje (jedna na stronę), brak długiej transakcji i jednego połączenia przez całe minuty (pule 85 połączeń na węzeł), możliwość wznowienia od ostatniego klucza po błędzie, stały koszt strony, stabilność względem zmian danych (nowe wiersze o większym kluczu trafiają do pliku, usunięte nie przesuwają stron). Kursor JDBC jest równie szybki i daje spójną migawkę, ale trzyma połączenie i transakcję przez cały czas eksportu (konwersja i zapis do POI trwają, więc to minuty) i nie da się go wznowić; zostaje opcją, gdyby stronicowanie po kluczu okazało się niewystarczające. Dla podglądu z numerem strony `OFFSET` zostaje (dostęp losowy), a dla dużych widoków można dodać stronicowanie po kluczu („strona po tokenie”).

**Zakres zmiany i wydanie:** DTO `ViewQuery` i `ViewDataPage` są w `mercury-lib`, więc rozszerzenie publicznego API (`countMode`, klucz „po”, `hasNext`) wymaga **wydania `mercury-lib`**, tłumaczeń dokumentacji OpenAPI i dokumentacji. Wariant bez wydania biblioteki: w pierwszym kroku wewnętrzna metoda serwera (bez REST/SOAP) dla eksportu, w drugim publiczne API.

## Kursor po stronie serwera w prezentacji danych (analiza, 2026-11-18, do decyzji autora)

**Zasięg zmiany.** Stronicowanie przez `LIMIT/OFFSET` w JPA (`setFirstResult`) występuje w kodzie **tylko** w `CaseViewDefinitionDAO.readViewData`. Z niego korzystają: eksport widoku (`ExportGenerator`) oraz podgląd widoku (REST `CaseViewExtRest`, SOAP `CaseViewDefinitionAction`, przez `CaseViewDefinitionLogic.readViewData`, razem z filtrem uprawnień i maskowaniem). Wyszukiwanie spraw (Lucene → lista identyfikatorów → pobranie encji po identyfikatorach, `IdsPagedQuerySupport`/`MQuery`) używa innego mechanizmu i **nie jest dotknięte**. Zmiana wewnętrzna tylko dla eksportu nie wpływa na podgląd; zmiana `readViewData` (nowe parametry z zachowaniem domyślnych wartości) obejmuje też podgląd, ale tylko widoki.

**Pomiary dodatkowe** (`psql`, `T_Bench219`, 200 007 wierszy):

| Mechanizm | Koszt |
|---|---|
| lista wszystkich kluczy (`SELECT m_id … ORDER BY 1`) | 161 ms (jednorazowo) |
| pobranie 1000 wierszy po kluczach (`m_id = ANY(:klucze)`) | 3,5 ms, niezależnie od głębokości (dostęp losowy) |
| kursor `WITH HOLD`: `DECLARE` + `COMMIT` (materializacja całego wyniku) | 206 ms; potem `FETCH 1000` poza transakcją 0,7–0,8 ms, pominięcie 150 000 wierszy 6 ms |
| kursor `SCROLL WITH HOLD` (także wstecz) | materializacja 283 ms; `FETCH BACKWARD 1000` 2,2 ms |

**Kursor w przeglądaniu danych: ryzyka.** Kursor łączy się z jedną sesją bazy, a Mercury ma pule połączeń (do 85 na węzeł) i wiele węzłów, więc kursor między żądaniami wymaga stanu: przypięcia połączenia (sesji) do użytkownika i węzła. Zwykły kursor trzyma otwartą transakcję (`idle in transaction`: blokuje czyszczenie wersji wierszy, zajmuje połączenie z puli, ginie przy awarii węzła albo przeładowaniu). `WITH HOLD` nie trzyma transakcji, ale materializuje cały wynik (tu ok. 20 MB plików tymczasowych dla 200 000 wierszy), nadal jest związany z sesją, i trzeba go zamykać (porzucone strony, limity czasu, wyciek zasobów). Dla przeglądania danych (dowolne żądanie, dowolny węzeł) to sprzeczne z bezstanowością usług REST.

**Wzorzec zgodny z resztą Mercury: migawka kluczy i pobranie po kluczach** (tak działa wyszukiwanie spraw): pierwsze żądanie wykonuje zapytanie raz, zapisuje **uporządkowaną listę kluczy** (do limitu, np. 10 000–50 000) w pamięci podręcznej klastra (region współdzielony, krótki TTL) pod tokenem i zwraca stronę oraz token; kolejne strony: wycinek listy kluczy → `m_id = ANY(...)` (3,5 ms). Daje to dostęp losowy do dowolnej strony, stałą liczbę wierszy (znana od razu), spójną kolejność, brak transakcji i brak sesji, działa z dowolnego węzła (pamięć podręczna klastra), a kosztem jest pamięć listy kluczy (ok. 20 B na klucz) i nieaktualność migawki (do TTL). Wygasły token: ponowne wykonanie zapytania (jak dziś, bez błędu).

**Propozycja warstw prezentacji danych** (do wyboru przez autora):
1. Eksport (jedna pętla w jednym wątku, bez stanu między żądaniami): stronicowanie po kluczu albo kursor JDBC; kursor jest tu bezpieczny, bo cały cykl życia mieści się w jednym wątku (rekomendowane po kluczu: wznowienie i brak długiej transakcji).
2. Podgląd z dowolną stroną: migawka kluczy z tokenem w pamięci podręcznej (jak wyszukiwanie spraw), liczba z migawki zamiast `COUNT(*)` przy każdej stronie.
3. Przeglądanie „dalej”: stronicowanie po kluczu bez zliczania (`hasNext`).
4. Kursor `WITH HOLD` w przeglądaniu: odradzane (stan, sesja, materializacja).

## Warstwa 1: eksport widoku po kluczu (2026-11-18) ✅

**Wynik pomiaru** (`mercury-test`, widok `T_Bench219`, 200 007 spraw: 200 006 wierszy widoku, strony po 1000, użytkownik `admin`):

| Wersja | Czas eksportu | Odczyt z bazy | Konwersja | Zapis stron do POI (RMI) | Zapis pliku (`commit`) |
|---|---|---|---|---|---|
| 3.0.4.28 (`OFFSET` + `COUNT(*)` na stronę) | 60,7 s | ok. 48 s (z pomiaru w bazie) | razem ok. 13 s | | |
| po zmianie (po kluczu, bez zliczania) | **10,2 s** | **2,2 s** | 0,9 s | 2,3 s | 4,0 s |

Czas zadania (cel: 200 000 × 6 poniżej minuty) osiągnięty z zapasem (ok. 6 razy szybciej). Linia z czasami faz pochodzi z instrumentacji `ExportGenerator` (`stron: 201, wierszy: 200006, razem: 9346 ms (odczyt: 2154 ms, konwersja: 924 ms, zapis stron do POI: 2277 ms, zapis pliku (commit): 3967 ms)`). Po zmianie największy udział ma zapis pliku w POI (ok. 40%), potem odczyt i zapis stron przez RMI (po ok. 23%).

**Poprawność pliku** (pobrany `xlsx`, 19,2 MB): 200 007 wierszy w arkuszu (nagłówek + 200 006 wierszy danych), identyfikatory `M_ID` unikalne i w kolejności klucza (leksykograficznie rosnąco).

**Zmiany w kodzie** (`mercury`, gałąź `hgdb-219`, bez zmiany DTO w `mercury-lib`, więc bez wydania biblioteki):
- `ICaseViewDefinitionDAO` / `CaseViewDefinitionDAO`: nowy wariant `readViewData(..., boolean withCount)`; dotychczasowa metoda deleguje z `withCount = true`.
- `ViewKeyColumn` (`mercury-srv`): kolumna klucza widoku (`M_ID`, a gdy jej nie ma, pierwsza kolumna jak dotąd w `ORDER BY 1`).
- `ICaseViewDefinitionLogicInternal.readViewDataAfterKey(context, viewName, afterKey, pageSize)` (nowy interfejs wewnętrzny, bo `ICaseViewDefinitionLogic` jest w `mercury-lib`), implementowany przez `CaseViewDefinitionLogic`: filtr `klucz > afterKey`, sortowanie po kluczu, odczyt `pageSize + 1` wierszy (nadmiarowy wiersz tylko wskazuje dalsze), bez zliczania; uprawnienia, ograniczenie do typów i maskowanie bez zmian (wspólna ścieżka `doReadViewData`).
- `ExportGenerator.generateViewReport`: pierwsza strona z liczbą (postęp, zakres), kolejne po kluczu; serwer POI wymaga, by każda strona niosła te same informacje o pierwszej i ostatniej stronie, liczbie wierszy i kolejne numery, więc strony po kluczu dostają numery po kolei i informacje z pierwszej strony (`describeKeysetPage`); zakres eksportu wyznacza liczba z początku (wiersze dodane później poza zakresem nie wchodzą do pliku, zapis do logu), pętla kończy się na braku dalszych wierszy; postęp ograniczony do 100%.
- Testy: `ViewKeyColumnTest` (4). Brak testu scenariuszowego odczytu na bazie (widok powstaje asynchronicznie przez JMS); funkcjonalnie sprawdzone pomiarem na `mercury-test`.
- **Nie zmienione:** podgląd widoku (REST `CaseViewExtRest`, SOAP) nadal czyta przez `OFFSET` z `COUNT(*)`; wyszukiwanie spraw (Lucene).

**Tymczasowe nakładki na `mercury-test`** (bez publikowania obrazu; do usunięcia po wydaniu): (1) ConfigMap `poi-start-patch` z poprawionym `startServer.sh` serwera POI i zmienna `HOST_NAME` w deploymencie POI, (2) ConfigMap `core-server-jar` z `mercury-core-server-3.0.4.28.jar` zamontowany w `mercury-node1`, (3) jary `mercury-srv`, `mercury-dao` i `mercury-dao-api` na wolumenie NFS (`/opt/mercury-3.0/upload/override`) kopiowane do `lib` przy starcie kontenera przez nadpisane `command` deploymentu `mercury-node1`. Usunięcie: nowy obraz `mercury` i `poi-server` z wydania, potem `kubectl delete configmap poi-start-patch core-server-jar`, usunięcie `command` i woluminów nakładek (`kubectl patch` albo świeże `helm uninstall/install`).

### Eksport spraw (Lucene): wynik (2026-11-18)

Baza: 200 007 spraw `Bench219`, strony po 1000. Wcześniej ok. 18 min i brak pliku (eksport spraw nigdy nie kończył się plikiem przy tej liczbie danych).

| Zmiana | Skutek |
|---|---|
| `ExportGenerator`: `EntityManager.detach` encji każdej strony po konwersji | zniknął narost czasu strony z jej numerem (próbkowanie wątków: `DefaultAutoFlushEventListener.dirtyCheck` po rosnącym kontekście trwałości); 51% po 111 s zamiast 54% po 587 s |
| `MPoiServerSupport.createHeader`: `caseId` i `previousVersionId` jako `STRING` (były `LONG`) | koniec błędu `NumberFormatException: "Bench219.62114"` przy zapisie pliku (id spraw są tekstowe od zadania 016) |
| limit pamięci `poi-server-node1` 2Gi → 4Gi (live na `mercury-test` i w `values.yaml` + `charts/README.md`) | przy 2Gi POI był zabijany (`OOMKilled`) przy ok. 50% eksportu: serwer trzyma strony całego eksportu w pamięci do `commit` |

Wynik: **COMPLETED po 354 s** (cel < 60 s niespełniony). Plik nie sprawdzony. Nie zmierzony rozkład czasu faz na ścieżce spraw. Nie sprawdzony eksport na limicie 2Gi po zmianie typów.

Dalsze kroki: instrumentacja `PhaseTimes` na ścieżce spraw (odczyt Lucene, `convertCollectionByStream`, zapis RMI, `commit`), pula `ForkJoinPool` tworzona przy każdej stronie, wynik `commit` POI.

### Eksport spraw: pomiar faz i czyszczenie kontekstu (2026-11-18, po południu)

`ExportGenerator.generateReport` loguje teraz `PhaseTimes` (jak widoki). Pomiary `mercury-test`, 200 006 wierszy:

| Wariant | Razem | Odczyt (Lucene + baza) | Konwersja | Zapis stron do POI | Zapis pliku (`commit`) |
|---|---|---|---|---|---|
| tylko `detach` encji spraw, strony po 1000 | 345 s | 329 s | 2,8 s | 9,4 s | 3,9 s |
| `flush` + `clear` kontekstu po każdej stronie, strony po 1000 | **80 s** | 60 s | 3,3 s | 11,7 s | 5,2 s |
| to samo, strony po 10 000 | 92 s | 82 s | 3,2 s | 3,0 s | 4,0 s |

Wnioski:
- `detach` samych spraw nie wystarcza: w kontekście zostawały encje powiązane i kolekcje, a Hibernate przed każdym zapytaniem (auto-flush) sprawdzał je wszystkie. `flush` + `clear` po stronie (`releasePage()`) daje 4-krotne przyspieszenie.
- Większa strona nie pomaga: odczyt rośnie z liczbą wierszy (ok. 0,3 ms/wiersz), a nie ze stronami.
- Próbki wątków po poprawce: czas odczytu dzieli się na (a) wykonanie zapytania Lucene i scalanie pełnego zbioru wyników przy każdej stronie (`QueryResultUtil.merge`, `ResultRows.putAll`, `QueryResultSupport.prepareResultSetByCollection`: koszt rośnie z wielkością zbioru, nie strony), (b) ładowanie encji `Case` z bazy (`SearchProviderUtils.loadFromDatabase`, `TwoPhaseLoad`) i auto-flush wewnątrz strony.
- Cel (< 60 s dla 200 000 × 6) niespełniony: 80 s. Kolejne kroki: (1) wykonywać zapytanie Lucene raz i czytać kolejne strony ze zbioru, (2) pominąć ładowanie całego `Case` (z kolekcjami) na rzecz odczytu potrzebnych pól, (3) potok odczyt–konwersja–zapis (zapis RMI ok. 12 s i `commit` ok. 5 s można nakładać na odczyt), (4) `ForkJoinPool` per strona.
- Plik wynikowy eksportu spraw nadal niesprawdzony (liczba wierszy, kolejność).

### Eksport spraw: pamięć podręczna Lucene i pokrycie pól indeksem (2026-11-18, wieczór)

- Klucz pamięci podręcznej wyniku Lucene (`QueryResultsManager.getQueryId`) zawierał numer i rozmiar strony, więc każda strona eksportu zapisywała własną pełną kopię wyniku i nie trafiała w cache. Usunięty numer i rozmiar strony (zostaje limit trafień). **Pomiar bez zmiany:** odczyt 60,4 s (przed 60,3 s), razem 76-81 s. Zmiana ogranicza zaśmiecanie cache'u (201 kopii 200 tys. wierszy), ale nie skraca eksportu.
- Powód: także trafienie w cache kosztuje O(liczba trafień) na stronę: `executeQuery` przepisuje wynik (`ResultRows.putAll`), a `QueryResultSupport.initResulSet` buduje listę wszystkich 200 tys. wpisów (`transformRow2ResultSet`) przy każdym żądaniu strony. Próbkowanie (14 zrzutów wątków w trakcie eksportu): Lucene (przepisanie wyniku + budowa listy) 8, ładowanie `Case` z bazy 4 (w tym 2 z auto-flush), zapis RMI 2.
- Wniosek: koszt Lucene wynika z tego, że każda strona buduje wynik od nowa. `QueryExplainPlan.execute` zapamiętuje wynik (`this.result`), a `QueryResultSupport.initResulSet` listę (`this.resultSet`) w instancji, więc ponowne użycie jednej instancji dla kolejnych stron kosztowałoby raz. Propozycja: metoda `CaseSearcher` wykonująca plan raz i oddająca kolejne strony wywołaniu zwrotnemu (czytnik indeksu otwarty na czas całego eksportu); `ExportGenerator` czyta strony przez nią.
- Pokrycie pól eksportu indeksem (`Case.java`, adnotacja `@LuceneSeracherField`, `CaseMapper`): w indeksie (stored) są `id`, `bpmProcessId`, `inventoryCode`, `status`, `previousVersionId`, `priceValue`, `priceValueCode`, `priceExchangeDate`, `createDate`, `lastModifyDate`, `endDate`, `dueDate`, `createdBy`, `lastModifiedBy`, `createdByRoleName`, `lastModifiedByRoleName`; typ i grupa przez mappery. **Bez adnotacji (nie w indeksie):** `modifyComment`, `storeCount`, `store` (storeId). Parametry typu: indeksowane przez `AttributeParser` (hasła pomijane, `SUBCASE` i `COMPLEX` osobno), forma zapisu wartości (surowa czy prezentacja kliencka) i flaga `stored` nie sprawdzone. Eksport z samego indeksu jest więc możliwy tylko dla eksportu bez pól `modifyComment`/`storeCount`/`storeId` (flaga pomijania nagłówka lub typy bez tych kolumn) i bez parametrów `PASSWORD`/`SUBCASE`/`COMPLEX`, po potwierdzeniu formatu wartości.

### Eksport spraw: kursor stron Lucene (2026-11-18, wieczór) - cel osiągnięty

Zmiana (`mercury-srv`, gałąź `hgdb-219`): `ICaseSearcher.openPageCursor` / `CaseSearcher` (wspólny `executeQuery` z `doSearchIndex`) i `ICaseLogicInternal.openSearchCursor` zwracają `ICasePageCursor`: zapytanie Lucene wykonuje się raz, kolejne strony (`page(n)`) są czytane z zapamiętanego wyniku (plan `QueryExplainPlan.result` i lista `QueryResultSupport.resultSet` w jednej instancji); kursor trzyma otwarty czytnik indeksu (try-with-resources w `ExportGenerator.generateReport`). Wykonanie lokalne (indeks węzła, na którym działa eksport).

| Wariant (200 006 wierszy, strony po 1000) | Razem | Odczyt | Konwersja | Zapis stron do POI | `commit` |
|---|---|---|---|---|---|
| `flush` + `clear` po stronie | 80 s | 60 s | 3,3 s | 11,7 s | 5,2 s |
| + klucz cache bez numeru strony | 76 s | 60 s | 3,4 s | 7,4 s | 5,1 s |
| + kursor stron (zapytanie raz) | **28,3 s** (30,6 s od zlecenia) | 12,0 s | 2,7 s | 9,8 s | 3,7 s |

Cel zadania (200 000 × 6 poniżej 1 minuty) osiągnięty dla eksportu spraw (wcześniej ok. 18 min bez pliku) i widoków (10,2 s). Plik wynikowy sprawdzony: 200 007 wierszy w arkuszu (nagłówek + 200 006), 200 006 unikalnych `mrc_caseId`, wartości nagłówka i parametrów poprawne (m.in. `caseId` jako tekst).

Zmiany niezatwierdzone w `mercury`: `ExportGenerator`, `MPoiServerSupport`, `QueryResultsManager`, `CaseSearcher`, `ICaseSearcher`, `ICasePageCursor`, `ICaseLogicInternal`, `CaseLogic`. Brak testu jednostkowego kursora (wymaga indeksu Lucene i bazy); sprawdzone pomiarem na `mercury-test`.

Dalsze (opcjonalne): eksport z samego indeksu dla typów bez pól spoza indeksu, potok odczyt-konwersja-zapis, argument formatu `csv`, ścieżka odczytu (import, `load`), warstwy 2 i 3 podglądu widoków.

### Argument formatu pliku: `csv` (2026-11-18, wieczór)

Decyzje: domyślnie `xlsx`; `csv` to UTF-8 z BOM (Excel poprawnie czyta polskie znaki), separator pól `;` (zmienny parametrem), końce wierszy `
`, wartości z separatorem, cudzysłowem lub końcem wiersza w cudzysłowie (RFC 4180), jeden wiersz nagłówka, bez limitu arkusza. Wartości zapisywane tak, jak przychodzą w wierszach (bez zamiany typów), wartości zaczynające się od `=`, `+`, `-`, `@` nie są zmieniane (arkusz może je potraktować jako formuły; zostawione świadomie, żeby nie zmieniać danych).

Zmiany:
- `poi-toolkit` (wersja **4.1.0.3**, `minor_version.txt`; 4.1.0.2 była wydana): `FileFormat` (`XLSX`, `CSV`), parametry zapisu `fmt` i `csvsep` (`ServerAppConstants.WriteParams.FMT`, `CSVSEP`), `ExcelFileWriter` (rozszerzenie pliku wg formatu, `saveCsv`), test `CsvWriterTest` (4 testy: parsowanie formatu, dwie strony ze znakami specjalnymi, własny separator, domyślny xlsx).
- `mercury`: `poi-toolkit.version` 4.1.0.3 w `pom.xml`; REST `ReportExportStatusRest.prepareReportRequest`: pola `format` (`xlsx`/`csv`, nieznany format daje błąd w odpowiedzi) i `csvSeparator` (jeden znak), rozszerzenie pliku wg formatu; `ReportExportStatusLogicHelper` przenosi `fmt` i `csvsep` do PARAMS raportu (bez tego generator ich nie widział); `ExportGenerator` przekazuje je do serwera POI. W OpenAPI (`openapi-docs_*.properties`) `PrepareReportRequest` nie jest opisany, więc nie ma kluczy do uzupełnienia.
- Poprawka błędu: w eksporcie spraw ostatnia kolumna `dlc` była o 1 za duża (`dfc + headerSize`, w widokach `dfc + headerSize - 1`), co w CSV dawało pustą kolumnę na końcu każdego wiersza (w xlsx pusta kolumna z nazwą litery w nagłówku).

Pomiar `mercury-test` (200 006 spraw, 27 kolumn, strony po 1000): CSV 25-30 s, plik 40 MB (xlsx 19 MB, 30 s); sprawdzony: 200 007 wierszy (nagłówek + dane), po 27 pól w każdym, 200 006 unikalnych `mrc_caseId`. Eksport widoku w CSV 15 s.

Pamięć serwera POI: kolejne eksporty 200 000 spraw przy `-XX:MaxRAMPercentage=65.0` i limicie 4Gi kończyły się `OOMKilled` (heap 2,6 GiB + pamięć poza stertą cache'u i JVM przekraczały limit kontenera). Przy `50.0` trzy eksporty z rzędu przeszły bez restartu; zmienione w `values.yaml` i `charts/README.md` (`mercury-docker`) i na żywo na `mercury-test`. Obserwacja 177: serwer trzyma wszystkie strony eksportu w pamięci do `commit` (dla CSV wystarczyłby zapis strony na dysk przy `load`).

Nakładki na `mercury-test` (tymczasowe, do usunięcia po wydaniu): jar `poi-toolkit-4.1.0.3` w `mercury-node1` (usuwanie 4.1.0.2 z `lib`) i w poziomie POI, `mercury-ws-app.war` z NFS `upload/override/mercury-ws-app.war.new` kopiowany przy starcie (webapp jest rozpakowywany z WAR przy każdym starcie, więc same klasy podmienić się nie dają), zmienna `JAVA_TOOL_OPTIONS` na wdrożeniu POI. Do zrobienia przy wydaniu: nowy pakiet i obraz `poi-server` z `poi-toolkit-4.1.0.3` (`mercury-docker/poi-server`: zip, `Dockerfile`, `startServer.sh`, `conf/node*.properties`, `mercury.properties`; dziś wskazują 4.1.0.2) oraz wydanie `mercury`.

### Import (219a): wyniki pomiaru i analiza rejestru transakcji (2026-11-19)

**Czytanie pliku** (poi-toolkit, gałąź `hgdb-219a`, jeszcze nie wydane): nowe czytniki strumieniowe `XlsxStreamReader` (SAX) i `CsvStreamReader` zastępują `XSSFWorkbook`, który przy pliku 200 000 × 27 padał (`MaxLength (100000000) reached`: arkusz ma ponad 200 MB XML-a, limit `IOUtils` POI 100 MB). Odczyt lokalnie (test `ReaderBenchmarkTest`): **xlsx 19,4 s / 655 MB sterty, csv 8,8 s / 507 MB** (200 006 wierszy × 27 kolumn). Import przyjmuje teraz też pliki `.csv` (rozpoznanie po rozszerzeniu, separator z pierwszego wiersza albo parametr `csvsep`). `ExcelFileReaderResult` buduje indeks wartości kolumn leniwie (dotąd przy każdym `addRow`: pamięć i czas; indeks potrzebny tylko do filtrowania). Testy: `StreamReaderTest` (xlsx i csv, round-trip z zapisem), `CsvWriterTest`.

**Import na `mercury-test`** (`base2`, plik z eksportu, strony po 1000): po 30 min 55%, ok. 60 wierszy/s i malejące (przewidywane > 1 h); przerwany ręcznie po 11:50 (restart `mercury-node1`, raport oznaczony `FAILED`). Import tworzył **nowe sprawy** (nie wersje: `piervous_version_id` puste): w `Bench219` zostało ok. 130 800 dodatkowych spraw (łącznie 330 840), do posprzątania (odtworzenie danych `load219.py`).

**Przyczyna: rejestr transakcji spraw (`CaseTransactionManager.join2Transactions`).** Zrzuty wątków: 4 z 5 wątków `ForkJoinPool` czeka na monitorze w `join2Transactions` (z `CaseDAO.beforeInsert`), piąty serializuje `HashSet` albo czeka na klastrowy cache Ehcache (Terracotta, `consistency="strong"`). Dla każdego wiersza, pod jedną blokadą na transakcję:
1. `get` obiektu `CaseLocalTransactionObject` z klastrowego cache'u `CaseLocalTransactionCache` (zawiera `HashSet` identyfikatorów wszystkich spraw transakcji),
2. dopisanie jednego identyfikatora,
3. `put` całego obiektu,
4. `get` i `put` obiektu `CaseGlobalTransactionObject` sprawy w `CaseGlobalTransactionCache`.

Import jest jedną transakcją dla całego pliku, więc obiekt rośnie z każdym wierszem: przy n wierszach przesyłanych jest ok. 2 × n × 30 B na wiersz, czyli **ok. 30 B × n² łącznie** (200 000 wierszy ≈ 1,2 TB; przy 110 000 wierszach pojedynczy `get`/`put` to ok. 3 MB). To złożoność kwadratowa plus cztery wywołania do Terracotty na wiersz pod jedną blokadą. Czytnik pliku nie jest wąskim gardłem.

**Do czego rejestr służy** (z kodu): (a) rejestr globalny (`caseId` → aktywne podtransakcje) odpowiada na pytanie „czy sprawa jest przetwarzana w niezatwierdzonej transakcji”; jedyny czytelnik to `CaseLastUpdatedCleanerReceiver.cleanLastUpdatedBuffer` (`containsInActiveTransactions`), który wtedy pomija usunięcie wpisu z bufora ostatnich zmian; (b) zbiór `caseIds` transakcji lokalnej jest czytany tylko w `closeLocalTransaction` (żeby zdjąć podtransakcję z wpisów globalnych); (c) obiekt transakcji lokalnej niesie też mapę treści LOB (`addLobContent`/`getLobContent`), czytaną przez sekretarzy LOB, więc musi zostać w pamięci podręcznej. Import ustawia `SUSPEND_REGISTER_OF_CHANGES_PROP`, więc bufor ostatnich zmian dla jego spraw powstaje dopiero na końcu; rejestr nie ma dla niego praktycznego skutku, a kosztuje najwięcej. Zamknięcie transakcji (`closeLocalTransaction`) robi dodatkowo `get` i `put` dla każdej sprawy (także `put(null)`, gdy wpisu brak) pod blokadą.

**Propozycja poprawek** (zachowują semantykę wykrywania spraw w transakcji):
1. Zbiór `caseIds` trzymać w pamięci węzła (współbieżny zbiór w mapie `transactionId → zbiór`, jak już robi `localTransactionIds`), a w obiekcie w cache'u zostawić tylko stan i LOB-y; usunąć blokadę na transakcję na rzecz blokady na sprawę. Usuwa złożoność kwadratową i serializację wątków.
2. Rejestrację globalną dla operacji hurtowych (kontekst z `BULK_INDEXING`/`SUSPEND_REGISTER_OF_CHANGES_PROP`) wykonywać w pakietach (np. po 1000 spraw i przy `commit`) zamiast na wiersz; przed `containsInActiveTransactions` opróżniać bufor oczekujących.
3. `closeLocalTransaction`: `remove` zamiast `put` i operacje w pakietach (albo zostawić czyszczenie leniwe w `containsInActiveTransactions`, które już usuwa nieaktywne wpisy).

### Import (219a): rejestr transakcji w pamięci węzła i profil jednego wiersza (2026-11-19)

**Zmiana** (`mercury-dao`, `CaseTransactionManager`, punkty 1 i 3 z analizy): identyfikatory spraw transakcji w pamięci węzła (`localCaseIds`), wpis globalny pod blokadą paskową po `caseId`, `closeLocalTransaction` z `remove` zamiast `put`, `isActiveTransaction` bez zapytania do cache'u dla transakcji tego węzła; sprawy dołączone przez inny węzeł nadal trafiają do obiektu w cache'u. Punkt 2 (rejestracja globalna w pakietach) odłożony: rejestr jest ochroną optymalizacji strony głównej GUI (lista ostatnio modyfikowanych spraw per typ, `CaseLastUpdated*`), import zawiesza rejestrację zmian (`SUSPEND_REGISTER_OF_CHANGES_PROP`) do końca. Test `CaseTransactionManagerTest` (3 testy, Terracotta lokalna): dwie transakcje na jednej sprawie, 20 000 spraw z 8 wątków, dołączenie z innego węzła.

**Pomiar na `mercury-test`** (plik csv 20 000 wierszy, wgrany przez `/rest/files/uploadPoiFile`, strony po 1000): nowy kod 146,6 / 202 / 146,7 s, stary kod 166,9 s; przy takim n różnica jest w szumie (składnik kwadratowy jeszcze mały: import ok. 100 s = 200 wierszy/s, rejestracja zmian ok. 45 s). Zysk ma wyjść przy dużych plikach (stary kod: ok. 60 wierszy/s i malejące przy 110 000 wierszy); pełny import 200 000 wierszy z nowym kodem do zmierzenia. Próbki wątków po zmianie: nikt nie czeka już na monitorze `join2Transactions`, wątki czekają na PostgreSQL i na potwierdzenia Terracotty.

**Profil jednego wiersza** (liczniki `pg_stat_*` różnicowo dla importu 20 000 wierszy z nowym kodem): **4,7 transakcji bazy na wiersz** (94 290 `commit`), ok. 3,7 mln krotek zwróconych, 694 tys. pobranych. Skany indeksów na wiersz: `igo_adm_users` 5,0, `igo_da_types` 2,1, `igo_da_groupcases` 2,05, `igo_da_stores` 2,0, `igo_da_cases` 1,07, `igo_di_sources` 1,0, `igo_da_groupcace2participant` 1,0, `igo_da_store2type` 1,0, `igo_da_case_roots` 1,0 (+ wstawienie), `igo_da_cases_removed` 1,0, a `igo_da_ktms` jest czytana **sekwencyjnie raz na wiersz** (20 002 `seq_scan`). Dane referencyjne (użytkownicy, typ, grupa, magazyn, źródło, powiązania magazyn-typ, KTM) są więc ładowane od nowa dla każdego wiersza, bo każdy wiersz to osobna transakcja bez wspólnego kontekstu trwałości.

**Kierunki dalszej optymalizacji importu** (do uzgodnienia): (A) ładować dane referencyjne raz na import (lub na wątek) i przekazywać do `importCase`; (B) jedna transakcja na stronę zamiast na wiersz oraz wstawianie wsadowe (`hibernate.jdbc.batch_size`), co usuwa większość z 4,7 `commit` na wiersz; (C) rejestracja globalna w pakietach (punkt 2) po decyzji autora.

### Import 200 000 spraw po zmianie rejestru transakcji i projekt dalszych poprawek (2026-11-19)

**Pomiar pełnego importu** (`mercury-test`, xlsx z eksportu, 200 006 wierszy, strony po 1000, nowy `mercury-dao`): **COMPLETED po 1429 s** (stary kod: ponad godzina i nieukończony). Faza importu 564 s (tempo stałe, ok. 355 wierszy/s: 25% po 149 s, 50% po 282 s, 75% po 426 s, 100% po 564 s, czyli złożoność kwadratowa usunięta), **faza rejestracji zmian 860 s (60% całości)**, ok. 230 spraw/s.

**Faza rejestracji (R): zrzuty wątków.** Wszystkie 3 wątki (`ImportSecretary` i dwa z `ForkJoinPool.commonPool`) stoją w `LucCaseSaveBufferLogicHelper.updateIndexByCaseIds` w `thread.get()` (wiersz 204): rejestracja każdej sprawy (`ImportGenerator` → `caseLogic.registerChangesOfCase` → `CaseChangesRegistry.registerChanges`) wysyła osobne zadanie do głównej puli wątków (`ThreadPoolManager.getMainThreadPool()`) i czeka na wynik; zadanie to osobna transakcja z jednym `insert` do `IGO_LUC_SAVE_BUFFER_BULK`. W repozytorium istnieje gotowy mechanizm agregacji: gdy w kontekście jest kolekcja pod `LucCaseSaveBufferLogicHelper.AGREGATE_BUFFER_DATA_PROP`, `updateIndexByCaseIds` tylko dopisuje wpisy do kolekcji, a wywołujący po zakończeniu robi `LucCaseSaveBufferLogicHelper.optimalization(...)` i `lucCaseSaveBufferLogic.insertList(...)` (używają go `CasesParamsSaver`, `MrcCaseResultSaver` i transformacje BPM). **Propozycja R:** `ImportGenerator` ustawia kolekcję (`ConcurrentLinkedQueue<CaseSaveBuffer>`) przed pętlą rejestracji i po niej robi `optimalization` + `insertList` w jednej transakcji (i budzi sekretarza po zatwierdzeniu); semantyka zapisu do bufora bez zmian, mniej transakcji i zadań. Oczekiwany zysk: faza rejestracji z kilkunastu minut do sekund.

**Faza importu (A i B): zapytania SQL jednego wiersza** (log `log_statement=all` dla importu 300 wierszy; sprawy nowe, ścieżka wstawiania). Na wiersz: 11 instrukcji i 2 transakcje (`BEGIN`/`COMMIT`): `select igo_da_groupcases` (`groupCaseDAO.find` w `CaseLogicHelper.verifyGroupCaseAndStoreCount`), `select igo_da_groupcace2participant` (ta sama metoda), `select igo_da_store2type` (`store2TypeDAO.find` w `CaseLogic.simpleInsert`), po jednym `select` encji `systemuser_`, `store_`, `typecase_` (ładowanie powiązań po `id` przy zapisie sprawy), `select igo_da_cases_removed`, `select igo_da_case_roots`, oraz `insert` do `igo_da_cases`, `igo_da_case_roots` i `igo_luc_save_buffer_bulk`.

- **A (dane referencyjne raz na import):** grupa z uczestnikami, powiązanie magazyn-typ i encje typu, magazynu i użytkownika są w całym imporcie te same, więc można je rozwiązać raz (np. w `ImportGenerator.runInTransaction`) i przekazać do `importCase`/`simpleInsert` (osobna ścieżka wstawiania dla importu, bez zmiany `simpleInsert` dla zwykłych zapisów). Usuwa ok. 6 z 11 instrukcji na wiersz. Alternatywa: pamięć podręczna drugiego poziomu Hibernate (włączona w `dao-context.xml`, ale encje referencyjne nie są oznaczone `@Cacheable`; wymaga zmiany `mercury-lib`, więc wydania biblioteki).
- **B (transakcja na stronę i wstawianie wsadowe):** `importCase` jest wywoływany równolegle w `ForkJoinPool`, a każde wywołanie to osobna transakcja (4,7 `commit` na wiersz łącznie z rejestracją). Wariant: jedna transakcja na stronę (wątek przetwarza paczkę wierszy) i `hibernate.jdbc.batch_size` dla wstawień spraw i korzeni. Największy zysk (usuwa `BEGIN`/`COMMIT` i zbija `insert` w paczki), ale największa zmiana: wspólny kontekst trwałości dla paczki wymaga `flush`/`clear` po stronie (jak w eksporcie) i uwagi na identyfikatory generowane przez sekwencję tabelaryczną `IGO_SEQ_PK` (pobranie zakresu raz na paczkę).

**Kolejność:** R (mała zmiana, 60% czasu), potem A, na końcu B.
