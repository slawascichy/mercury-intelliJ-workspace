# Parametry konfiguracji Lucene: zestawienie (zadanie 119, 2026-10-26)

Zestawienie obejmuje parametry nowe (zadania 119, 39, 121) i istniejące parametry indeksu. Każdy wiersz mówi, jak parametr się nazywa,
co robi, jaką ma wartość domyślną i gdzie go ustawić. Źródło: kod w `mercury` (gałąź `hgdb-119`), pliki konfiguracyjne serwera i `mercury-docker`.

## 1. Gdzie ustawia się parametry

Są dwa miejsca.

| Miejsce | Zapis | Kiedy działa |
|---|---|---|
| **Plik `lucene.properties`** | `nazwa=wartość` | Wczytywany przy starcie serwera (klasa `LuceneConfig`). Zmiana wymaga restartu (przypuszczenie: wartości są cache'owane przy pierwszym użyciu, np. `LuceneHelper`). |
| **Właściwość systemowa JVM** | `-Dnazwa=wartość` | Tomcat: `bin/setenv.sh` (zmienna `CATALINA_OPTS` albo `JAVA_OPTS`). Działa po restarcie serwera. |

Lokalizacja pliku `lucene.properties`:

- wskazuje ją właściwość systemowa `-Dmercury.lucene.config.file=<ścieżka>` w `setenv.sh` (domyślnie `/lucene.properties` z classpath);
- w obrazie Docker: `${HGDB_HOME}/config/lucene.properties` (`mercury-docker/mercury-3.0/docker-init-config/apache-tomcat/bin/setenv.sh`);
- w pakiecie instalacyjnym: `IBPM/mercury/config/lucene.properties` (wzorce: `mercury-server/src/main/config/{jenkins,scichy}/IBPM/mercury/config/`);
- narzędzie `mercury-cmd` czyta ten sam plik (`-Dmercury.lucene.config.file=$MERCURY_HOME/config/lucene.properties` w `mercury-cmd.sh`).

**Pierwszeństwo:** wszystkie parametry z punktu 2 (poza `lucene.query.truncation.error`) czyta klasa `org.mercury.lucene.config.LuceneProperty`: najpierw
`lucene.properties`, a gdy wpisu brak, właściwość systemowa `-D`. Wpis w pliku ma więc pierwszeństwo przed `-D`.
`lucene.query.truncation.error` i parametry z punktu 3 czytają tylko `lucene.properties`.

## 2. Parametry nowe (zadania 119, 39, 121)

| Parametr | Domyślnie | Co robi | Gdzie ustawić | Etap |
|---|---|---|---|---|
| `lucene.query.truncation.error` | `false` | `true`: obcięcie wyniku limitem trafień kończy zapytanie błędem. `false`: zapytanie zwraca niepełny wynik z `truncated=true` i `totalHits` | `lucene.properties` | W1 |
| `lucene.query.cost.probes` | `true` | Włącza sondy liczności w wyborze kolejności planu (korzeń najpierw albo dziecko najpierw). `false` przywraca starą regułę kosztową | plik, potem `-D` | W3 |
| `lucene.query.cost.probeLimit` | `3000000` | Górny limit liczenia trafień przez sondę (zapytanie z dużą liczbą trafień nie jest liczone w całości) | plik, potem `-D` | W3 |
| `lucene.query.cost.childFirstRatio` | `2.0` | Próg wyboru planu: dziecko najpierw, gdy trafień dziecka jest mniej niż `ratio × trafień korzenia`. Kalibracja: `podsumowanie-koncowe-2026-10-26.md`, punkt 4 | plik, potem `-D` | W3, W4, W7 |
| `lucene.query.nested.batch` | włączone | `false` wyłącza zbiorcze łączenie rodzic–dziecko i wraca do pętli zagnieżdżonej | plik, potem `-D` | W4 |
| `lucene.query.docvalues` | włączone | `false` wyłącza odczyt komórek wyniku i histogramu dat z DocValues (wraca do pól zapisanych) | plik, potem `-D` | W5, W6, W7 |
| `lucene.query.nested.loadAllFields` | `false` | `true` przywraca wczytywanie całych dokumentów dzieci zamiast potrzebnych pól | plik, potem `-D` | W5 |
| `lucene.reader.pool` | `true` | `false` wyłącza wspólny czytnik indeksu i wraca do otwierania czytnika na każde żądanie | plik, potem `-D` | W12 (zadanie 39) |
| `lucene.reader.refreshMs` | `1000` | Najdłuższy czas (ms) bez sprawdzenia zmian indeksu przez wspólny czytnik. Własne zapisy odświeżają czytnik od razu, a ten parametr obejmuje zapisy spoza procesu. `0` = sprawdzanie przy każdym pobraniu, wartość ujemna = tylko po zgłoszeniu zmiany | plik, potem `-D` | W12 |

Wskazówki per zapytanie (nie ustawia się ich w pliku, tylko w kontekście zapytania, `ContextQueryHint`):
`org.mercury.lucene.query.hint.useCostOptimization` (wymusza decyzję kosztową) i `org.mercury.lucene.query.hint.ruleRootFirst` (wymusza „korzeń najpierw”).

## 3. Parametry istniejące, powiązane z wydajnością

| Parametr | Domyślnie | Co robi | Gdzie ustawić |
|---|---|---|---|
| `lucene.query.maxHits` | `100000` w plikach wzorcowych serwera | Limit trafień zapytania. Po jego przekroczeniu wynik jest obcięty (patrz `lucene.query.truncation.error`). `maxResults` w kontekście zapytania ma pierwszeństwo | `lucene.properties` |
| `lucene.index.segments` | `32` | Do ilu segmentów (najwyżej) łączy się indeks przy optymalizacji | `lucene.properties` |
| `lucene.RAMBufferSizeMB` | `32` | Rozmiar bufora RAM writera przed zapisem segmentu na dysk | `lucene.properties` |
| `lucene.maxBufferedDocs` | `100` | Liczba dokumentów w buforze writera, po której powstaje segment | `lucene.properties` |
| `lucene.base.indexDir`, `lucene.base.indexDir2`, `lucene.base.indexDir.selected` | – (wymagane) | Katalogi indeksu i wybór aktywnego | `lucene.properties` |

## 4. Uwagi i luki

1. **Odczyt ujednolicony (2026-10-26).** Trzy przełączniki (`lucene.query.nested.batch`, `lucene.query.docvalues`, `lucene.query.nested.loadAllFields`) i
   `lucene.query.cost.probeLimit` czytały wcześniej tylko jedno źródło (pierwsze trzy wyłącznie `-D`, `probeLimit` wyłącznie plik). Teraz wszystkie
   działają jak `childFirstRatio`: plik, potem `-D`.
2. **`lucene.query.truncation.error`** czyta tylko `lucene.properties` (bez `-D`).
3. **`lucene.RAMBufferSizeMB`, `lucene.maxBufferedDocs` i `lucene.index.segments`:** wartości są cache'owane przy pierwszym odczycie (`LuceneHelper`), więc zmiana wymaga restartu.
4. **Pliki konfiguracyjne z zakomentowanymi przykładami (2026-10-26).** Nowe parametry dopisano jako zakomentowane przykłady (z wartościami domyślnymi)
   po wpisie `lucene.query.maxHits` w 20 plikach `*lucene.properties` repozytorium `mercury` (gałąź `hgdb-119`):
   serwer (`mercury-server/src/main/config/{jenkins,scichy}`), `mercury-srv` i `mercury-ws-server` (`src/main/resources`), `integrations/lucene.properties`,
   `mercury-lucene-indexes-api/src/test/resources/lucene.properties` oraz profile testowe `test-lucene.properties` (`jenkins`, `scichy`, `scichy-test`)
   w modułach `mercury-core-server`, `mercury-lucene-indexes`, `mercury-srv`, `mercury-srv-slave`, `mercury-ws-server`.
   **Nie zmieniano** plików w innych repozytoriach (zasada: bez zgody nie modyfikuję sąsiednich repozytoriów): `mercury-docker/mercury-3.0/docker-init-config/config/lucene.properties`,
   `mercury-cmd/mercury-install-package/system-config-sample/linux/config/lucene.properties` (oraz wydania w `releases/`) i konfiguracje klienta w `mercury-client`.
   Pliki `test-lucene-inea*.properties`, `test-lucene2.properties` i `test-lucene3.properties` (indeksy z `F:`) też bez zmian.
5. **Wartości, które zależą od danych** (`childFirstRatio`, `probeLimit`, `refreshMs`, `maxHits`) kalibrowano na jednym indeksie (INEA 3.0, 22 mln dokumentów). Dla innego klienta wartości optymalne mogą się różnić.
   Stąd propozycja zadania z poleceniem `mercury-cmd`, które kalibruje parametry na lokalnym indeksie (`tasks/hgdb/209-Polecenie-kalibracji-parametrow-indeksu-Lucene/TASK.md`).

## 5. Przykład wpisu w `lucene.properties`

```properties
# Limit trafień zapytania; po przekroczeniu wynik jest obcięty (truncated=true)
lucene.query.maxHits=100000
# true: obcięcie kończy zapytanie błędem zamiast niepełnym wynikiem
lucene.query.truncation.error=false

# Sondy liczności w wyborze kolejności planu (W3). Próg wyboru "dziecko najpierw"
lucene.query.cost.probes=true
lucene.query.cost.probeLimit=3000000
lucene.query.cost.childFirstRatio=2.0

# Wspólny czytnik indeksu (zadanie 39)
lucene.reader.pool=true
lucene.reader.refreshMs=1000
```

Wyłączniki awaryjne można ustawić w `lucene.properties` (`lucene.query.docvalues=false`) albo w `bin/setenv.sh`, np.:

```bash
export CATALINA_OPTS="$CATALINA_OPTS -Dlucene.query.nested.batch=false -Dlucene.query.docvalues=false"
```
