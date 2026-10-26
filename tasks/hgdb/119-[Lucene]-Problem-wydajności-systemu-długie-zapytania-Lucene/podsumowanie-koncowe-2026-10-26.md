# Zadanie 119: podsumowanie końcowe (W10, 2026-10-26)

Dokument zamyka zadanie 119 (wydajność zapytań Lucene w INEA). Szczegóły decyzji i postępu: `plan-i-decyzje-2026-10-25.md`.
Porównanie z OpenSearch: `poc-opensearch-2026-10-26.md`. Wszystkie liczby pochodzą z plików CSV i raportów w tym katalogu.

## 1. Co zmieniono

| Etap | Zmiana | Efekt |
|---|---|---|
| W0 | Baza pomiarowa: 41 zapytań INEA 3.0, trzy tryby planu (`cost`, `rootFirst`, `none`), miara „żalu”, test różnicowy wyników | 28 z 41 zapytań spełniało kryterium |
| W1 | `truncated` i `totalHits` w odpowiedzi, log obcięcia, opcjonalny błąd | Klient wie, że wynik jest niepełny |
| W3 | Sonda liczności (`CardinalityProbe`) w decyzji o kolejności planu | Koniec z wyborem „dziecko najpierw” dla dużych dzieci |
| W4 | Zbiorcze łączenie rodzic–dziecko (jedno zapytanie zamiast pętli) | Dziecko-najpierw: 680 s → 30 s na całym zestawie |
| W5 | Odczyt komórek wyniku z DocValues zamiast z pól zapisanych | Poznań + Rfs: 13,7 s → 0,22 s |
| W6 | Histogram dat z DocValues (`DateHistogramCollector`) | `groupBy(miesiąc)` na całym indeksie: 476 ms |
| W7 | Id dzieci i rodziców z DocValues; podział po dacie odrzucony | 365 dni + Mts: 6,9 s → 1,9 s |
| W8 | Pomiary współbieżności (pulpit 6 paneli, 1/4/8 klientów) | p95 odświeżenia: 2,0 / 2,9 / 4,5 s |
| W9 | PoC OpenSearch 2.19.1 | Wartość docelowa; migracji nie rekomenduję |
| W11 | Walidacja sortowania (zadanie 121): błędy `L0009.7`, `L0009.8` | Czytelny błąd zamiast `M0001` |

Wynik końcowy (przebieg 2026-10-26, wyniki identyczne we wszystkich trybach i takie same jak w W0):

- kryterium żalu spełnia **39 z 41 zapytań (95%)**, drugi próg 40 z 41 (wobec 28 z 41 w W0);
- mediana żalu 1,10 → 1,04, p90 2,4 → 1,33, maksimum 4,9 → 3,9;
- suma czasów trybu `cost`: **48,6 s → 10,9 s**.

Znane ograniczenia:

- „adres 30 dni + Mts” ma żal 3,9 (stosunek dziecko/korzeń ok. 50). Próg tego nie naprawia. Wymaga modelu kosztu z osobnymi stałymi (W3 część 2);
- degradacja pulpitu przy 8 klientach: 2,2× (cel ≤ 2× niespełniony w przebiegu końcowym; w W8 po W5 było 1,74×). Pomiar do powtórzenia.

## 2. Konfiguracja

Wyłączniki `lucene.query.nested.batch`, `lucene.query.docvalues` i `lucene.query.nested.loadAllFields` czytane są jako
właściwości systemowe JVM (`-D…`). `lucene.query.maxHits` i `lucene.query.truncation.error` pochodzą z `LuceneConfig`.
`lucene.query.cost.childFirstRatio` czytany jest najpierw z `LuceneConfig`, a gdy go tam brak, z właściwości systemowej.

| Właściwość | Domyślnie | Znaczenie |
|---|---|---|
| `lucene.query.cost.probes` | `true` | Sondy liczności w decyzji o kolejności planu. `false` przywraca starą regułę kosztową |
| `lucene.query.cost.probeLimit` | 3 000 000 | Górny limit liczenia sondy |
| `lucene.query.cost.childFirstRatio` | 2,0 | Dziecko najpierw, gdy trafień dziecka jest mniej niż 2 × trafień korzenia (opis: punkt 4) |
| `lucene.query.nested.batch` | włączone | `false` wyłącza zbiorcze łączenie (W4) |
| `lucene.query.docvalues` | włączone | `false` wyłącza odczyt z DocValues (W5, W6, W7) |
| `lucene.query.nested.loadAllFields` | wyłączone | `true` przywraca ładowanie całych dokumentów |
| `lucene.query.maxHits` | z `MercuryConfig` | Limit liczby trafień; `maxResults` w kontekście ma pierwszeństwo |
| `lucene.query.truncation.error` | wyłączone | `true`: obcięcie wyniku kończy zapytanie błędem |

Wskazówki zapytania (`ContextQueryHint`): `org.mercury.lucene.query.hint.useCostOptimization` i `org.mercury.lucene.query.hint.ruleRootFirst`.

## 3. Zmiany kontraktu API

- `PagingInfo` (`mercury-lib`) ma pola `truncated` i `totalHits`. W postaci transportowej (`PagingInfoTransportable`) oba pola
  pojawiają się **tylko wtedy, gdy wynik jest obcięty** (`truncated=true`). Brak pola oznacza wynik pełny.
- Opisy OpenAPI: klucze `schema.<Typ>PagedResult.totalHits` i `.truncated` dla 20 schematów, w
  `mercury-ws-app-rest-generator/src/main/resources/META-INF/mercury/openapi-docs_{pl,en}.properties` (po 40 wierszy).
  Tłumaczenia de, es, fr, ko wykonał translator Gemini (`localization-project`, `validate`: 0 błędów, 0 ostrzeżeń).
  Wszystkie sześć plików ma po 40 kluczy. Raport `openapi-doc-report.txt` w `target/` jest nieaktualny (z 15:22) i trzeba
  go wygenerować ponownie; generator nie wystartował w sesji Claude (`MercuryException` w kroku `generate-model`).
- Błędy walidacji sortowania: `L0009.7` (pole oznaczone jako niesortowalne), `L0009.8` (indeks nie ma DocValues dla pola).
  Klucze są we wszystkich sześciu plikach `LuceneErrorMsg_*.properties` (de, es, fr, ko przetłumaczył Gemini).

### Sortowanie (zadanie 121, W11.5)

Sortować można tylko po polach z flagą `sorted=true` w definicji pola (`SearchField.getSorted()`), a indeks musi mieć dla
pola DocValues. Pole z `sorted=false` (np. `status`) kończy się teraz błędem `L0009.7`. Indeks zbudowany przed zmianą
definicji pola daje `L0009.8`; naprawia go przebudowa indeksu. Listę pól typu daje `CaseIndexerFieldsManagerRest`
(`getFieldsByTypeCodes`). Czy odpowiedź niesie flagę `sorted`, nie sprawdziłem w odpowiedzi REST (przypuszczenie: tak, bo
`sorted` należy do DTO pola). Dokumentacja użytkownika leży w `docusaurus-hgdb` (osobne repozytorium), więc jej nie zmieniałem.

## 4. Proces kalibracji progu `childFirstRatio`

### Problem

Dla zapytania z dzieckiem są dwa plany. **Korzeń najpierw**: zapytanie o korzeń, potem łączenie z dziećmi (od W4 zbiorczo).
**Dziecko najpierw**: zapytanie o dzieci, potem pętla po rodzicach. Pierwszy plan kosztuje tyle, ile trafień korzenia. Drugi
kosztuje tyle, ile trafień dziecka. Stare reguły zgadywały kolejność z częstości najrzadszego termu i myliły się (w W0 pomyłka
kosztowała do 4,9×, a w trybie wymuszonym nawet minuty).

### Rozwiązanie i parametr

Sonda (W3) liczy trafienia korzenia (`nRoot`) i dziecka (`nChild`) z limitem 3 mln. Decyzja:
**dziecko najpierw, gdy `nChild < childFirstRatio × nRoot`**. Parametr `childFirstRatio` mówi, ile razy łączenie zbiorcze jest
droższe w przeliczeniu na jedno trafienie niż pętla zagnieżdżona. Nie da się go wyliczyć z kodu. Trzeba go zmierzyć.

### Metoda

1. **Zbiór.** 41 zapytań na indeksie INEA 3.0 (22 mln dokumentów, kopia na `F:`): adresy z dziećmi o różnych stosunkach
   `nChild/nRoot`, zakresy dat 1/30/365 dni, wildcardy, listy i agregacje. Zbiór jest zamrożony od W0.
2. **Trzy tryby na każde zapytanie:** `cost` (decyduje optymalizator), `rootFirst`, `none` (dziecko najpierw). Każdy tryb
   mierzony dwa razy (`perf.runs=2`), z wynikami porównywanymi skrótem zawartości (`contentHash`). Wyniki musiały być identyczne.
3. **Żal** = czas trybu `cost` ÷ czas najlepszego z trzech trybów. Zapytanie spełnia cel, gdy **żal ≤ 1,25 albo różnica ≤ 100 ms**
   (krótkie zapytania nie liczą się przez szum). Poziom zadania: ≥ 90% zapytań, reszta żal ≤ 2 lub różnica ≤ 500 ms.
4. **Przemiatanie progu.** Ten sam zbiór dla kilku wartości `childFirstRatio` (właściwość systemowa, bez zmiany kodu).
   Dla każdej wartości: liczba zapytań spełniających kryterium, suma czasów, mediana i maksimum żalu.
5. **Wybór.** Najwięcej spełnionych zapytań. Przy remisie: wartość ze środka plateau i mniejsze maksimum żalu.
6. **Powtórka po zmianie kosztów.** Każda zmiana silnika, która przesuwa koszt jednego z planów, przesuwa też optimum progu.
   Kalibrację powtórzono trzy razy.

### Wyniki (przeliczone z `w3-`, `w4-`, `w7-kalibracja-*.csv`)

W3 (po sondzie, przed zbiorczym łączeniem):

| `childFirstRatio` | spełnia kryterium | suma [s] | maks. żal |
|---|---|---|---|
| 0,02 | 41 | 28,6 | 1,35 |
| **0,05** | **41** | 29,2 | 1,29 |
| 0,2 | 38 | 28,4 | 1,93 |
| 0,5 | 33 | 42,4 | 4,71 |
| 1,0 | 30 | 195,5 | 27,01 |

W4 (po zbiorczym łączeniu): optimum przesunęło się w górę, bo łączenie zbiorcze zmieniło relację kosztów.

| `childFirstRatio` | spełnia kryterium | suma [s] | maks. żal |
|---|---|---|---|
| 0,05 | 30 | 27,1 | 9,19 |
| 0,3 | 39 | 22,8 | 2,31 |
| **1,0** | **41** | 21,8 | 1,48 |
| 3,0 | 40 | 22,6 | 1,40 |

W7 (po DocValues dla dzieci i rodziców):

| `childFirstRatio` | spełnia kryterium | suma [s] | maks. żal |
|---|---|---|---|
| 0,5 | 36 | 15,0 | 3,15 |
| 1,0 | 37 | 12,7 | 3,39 |
| **2,0** | **40** | 10,8 | 3,21 |
| 4,0 | 39 | 10,5 | 3,10 |
| 12 | 39 | 10,8 | 3,56 |
| 24 | 39 | 10,4 | 2,80 |
| 48 | 38 | 11,0 | 3,24 |

### Wnioski z kalibracji

- **Asymetria kosztu błędu.** Zbyt wysoki próg w W3 (1,0) wybierał dziecko-najpierw dla dużych dzieci: suma 195 s i żal do 27.
  Zbyt niski próg w W4 (0,05) daje żal do 9, ale suma rośnie tylko o 5 s. Dlatego w W3 wybrano ostrożne 0,05, nie 1,0.
- **Plateau.** W W3 plateau obejmowało 0,02–0,05, a w W4 1,0–3,0. Domyślne 2,0 leży w obszarze 1,0–4,0, gdzie po W7 wyniki są
  najlepsze (40 i 39 z 41). W W7 jedynie 2,0 daje 40, więc wybór nie wynika ze środka plateau, tylko z maksimum liczby spełnionych zapytań.
- **Zapytanie, którego próg nie naprawia:** „adres 30 dni + Mts” (żal 3,2 przy 2,0, w przebiegu końcowym 3,9). Jego stosunek
  `nChild/nRoot` wynosi ok. 10 do 50, a zmiana progu na 12, 24 lub 48 psuje inne zapytania. Wymaga modelu kosztu z osobnymi
  stałymi dla każdej strategii (W3 część 2, poza zakresem 119).
- **Ograniczenia metody.** Zbiór pochodzi z jednego indeksu (INEA). Pomiary robiono na jednej maszynie z dwoma powtórzeniami
  na tryb, więc różnice poniżej ok. 100 ms to szum. Próg dla innych rozkładów danych jest przypuszczeniem (do sprawdzenia
  przy wdrożeniu na innym kliencie, np. przez ponowne przemiecenie progu na ich zapytaniach).
- **Jak powtórzyć.** W `mercury` (gałąź `hgdb-119`), dla każdej wartości progu osobno:

  ```bash
  mvn -o test -pl mercury-lucene-indexes -am -Duser=scichy -Dtest=LuceneLegacyIndexQueryTest -DfailIfNoTests=false \
    -Dperf.query=true -Dperf.model=3 -Dperf.maxResults=1000000 -Dperf.runs=2 -Dperf.modes=cost,rootFirst,none \
    "-Dperf.report=<plik>.csv" \
    "-DadditionalArgLine= -Dlucene.query.cost.childFirstRatio=<wartość> -Dmercury.lucene.config.file=<konfiguracja Lucene z maxHits 1 mln> -Xmx6g <pozostałe właściwości środowiska testowego>"
  ```

  Kolumny CSV: nazwa zapytania, model, status, żal, następnie para (czas ms, trafienia) dla `cost`, `rootFirst`, `none`
  i skrót zawartości wyniku. Skrypt `kalibracja-przelicz.py` (żal, liczba spełnionych, suma) odtwarza tabele powyżej.

## 5. Do zrobienia po stronie autora

1. Zatwierdzić zmiany w `mercury` (tłumaczenia: `openapi-docs_{de,es,fr,ko}.properties`, `LuceneErrorMsg_{de,es,fr,ko}.properties`) i w workspace (dokumenty z tej sesji).
2. Przejrzeć tłumaczenia de, es, fr, ko (40 kluczy OpenAPI w dwóch wartościach + `L0009.7`, `L0009.8`) i zatwierdzić je.
3. Zbudować `mercury-ws-app-rest-generator` i sprawdzić, że `openapi-doc-report.txt` nie ma braków.
4. Zrobić push gałęzi `hgdb-119` (`mercury`, `mercury-lib`) i PR.
5. Opcjonalnie: powtórzyć pomiar współbieżności (cel degradacji ≤ 2×); decyzja o W3 część 2 (osobne zadanie).
