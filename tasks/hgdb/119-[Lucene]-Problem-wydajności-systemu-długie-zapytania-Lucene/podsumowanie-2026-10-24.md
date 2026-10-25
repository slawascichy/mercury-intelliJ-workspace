# Podsumowanie dnia 2026-10-24: zadanie 119 (wydajność zapytań Lucene)

Status: **w toku**. Zrobiona analiza kodu, generator danych, zestaw 100 tys. adresów i pierwsze pomiary.
Pełna analiza: [analiza-2026-10-24.md](analiza-2026-10-24.md). Zadanie powiązane: [171](../171-Optymalizacja-optymalizatora-kosztowego/TASK.md).

## Co zrobiono

1. **Analiza kodu** (`mercury-lucene-indexes`, Lucene 7.5.0): optymalizator kosztowy, wykonanie zapytania, kolektory,
   grupowanie, rozkład pracy na wątki i węzły, statystyki. Wnioski i hipotezy w pliku analizy. Nic nie zmieniono w kodzie
   produkcyjnym.
2. **Gałąź** `hgdb-119` w repozytorium `mercury` (z `master`). Zmiany są tylko w testach i **niezacommitowane**.
3. **Generator wolumenu** (testy w `mercury-srv`):
   - `SlmVolumeXmlGenerator` (XML spraw `SlmAddress` z osadzonym dzieckiem `SlmAppMobileDetails`, rozkłady: Poznań 40%,
     dziecko `SlmAppMts` 20%),
   - `LuceneVolumeScenario` i `LuceneVolumeTest` (uruchamiane osobno od `SrvTest`).
4. **Pomiary zapytań** (testy w `mercury-lucene-indexes`): `LuceneVolumeQueryTest` (włączany `-Dperf.query=true`).
   Poprawka `FakeCaseMapper`: kod typu jest wrażliwy na wielkość liter (indeks tak go zapisuje).
5. **Zestaw danych i kopia:** 100 tys. adresów z dziećmi, 200 tys. dokumentów, 50 MB, 4 segmenty, daty 2019–2026
   (rosnąca gęstość). **Kopia indeksu: `mercury/integrations/lucene/perf-100k`** (katalog w `.gitignore`).
6. **Analiza projektu Grafany** (`hgdb-grafana-datasource`): kierunek dla zapytań grupujących, zakres dat zawsze obecny.

## Jak uruchomić

```
# generowanie (baza mercury-db, profil scichy, ok. 33 min, wymaga sterty 10 GB)
mvn -o test -pl mercury-srv -am -Duser=scichy -Dtest=LuceneVolumeTest -DfailIfNoTests=false \
  -Dperf.clean=true -Dperf.cases=100000 -Dperf.batch=500 -Dperf.seed=46 -Dperf.indexThreads=6 \
  "-DadditionalArgLine=${jmxArgLine} -Dsclogger.config.file=/properties/scichy/sclogger.properties \
   -Dmercury.config.file=/properties/scichy/test-mercury.properties \
   -Dmercury.lucene.config.file=/properties/scichy/test-lucene.properties -Xms512m -Xmx10g \
   -Djavax.xml.bind.context.factory=org.eclipse.persistence.jaxb.JAXBContextFactory"

# pomiary zapytań (nie wymagają bazy; czytają integrations/lucene/index)
mvn -o test -pl mercury-lucene-indexes -am -Duser=scichy -Dtest=LuceneVolumeQueryTest \
  -DfailIfNoTests=false -Dperf.query=true
```

Uwagi: `perf.clean=true` czyści `mercury-db` (zgoda autora z 2026-10-24). Domyślna sterta testów (`-Xmx1500m`) nie
wystarcza powyżej ok. 60 tys. spraw (test trzyma ok. 20 KB na sprawę, pełne GC zatrzymało przebieg). Przebieg może też
zawisnąć w inicjalizacji klienta Terracotta (problem pętli zwrotnej na Windows): zabić fork i powtórzyć.
Przepustowość zapisu: ok. 80 do 90 spraw/s. Datę utworzenia z XML serwer ignoruje, więc scenariusz po zapisie
przesuwa `create_date` w bazie (SQL) i przebudowuje indeks z bazy (`buildFullIndex`, 285 s dla 200 tys. wierszy).
Aby pomiary czytały kopię, wystarczy podstawić katalog `perf-100k` jako `lucene.base.indexDir`.

## Wyniki pierwszych pomiarów (100 tys. adresów, `maxResults` 200 000, bez pamięci podręcznej wyników)

| Zapytanie | Wynik | cost | rootFirst | none |
|---|---|---|---|---|
| adres (Poznań) | 35 886 | 0,6 s (pierwszy 1,0 s) | 0,5 s | 0,5 s |
| adres + zakres daty (2 lata) | 15 299 | 0,25 s | 0,25 s | 0,23 s |
| adres, wildcard `*znań*` | 35 886 | 0,5 s | 0,5 s | 0,5 s |
| OR czterech miast | 76 441 | 1,0 s | 1,1 s | 1,1 s |
| adres + dziecko (Mts, A) | 7 264 | **BŁĄD** | 0,7 s | **BŁĄD** |
| adres + dziecko (Lead, Z) | 1 224 | **BŁĄD** | 0,6–0,8 s | **BŁĄD** |
| adres (data ≥ -3 lata) + dziecko (Mts) | 11 139 | **BŁĄD** | 0,9 s | **BŁĄD** |
| groupBy(city, miesiąc) | 92 | 1,1–1,5 s | 1,4 s | 1,1–1,3 s |
| groupBy(street) | **1** | 0,9–1,2 s | 0,9–1,1 s | 0,9 s |

Przy tej skali (100 tys. adresów) czasy są małe, więc różnic między trybami optymalizatora nie widać. Benchmark z INEA
(82 s, 438 tys. rodziców) wymaga większej skali albo innego rozkładu.

## Znaleziska (do zbadania jutro)

1. **Błąd w kodzie produkcyjnym (potwierdzony testem).** `DataCollectorSubTopDocsManagerSupport.collectSubResults`
   (linia 141) wywołuje `Long.parseLong(subCaseIdStr)` na identyfikatorze dziecka. Po zmianie typu identyfikatora
   sprawy na `String` (zadanie 169) identyfikatory mają postać `SlmAppMobileDetails.3045416`, więc
   `NumberFormatException`. Dotyczy planu, w którym najpierw wykonuje się zapytanie o dziecko, a tak wybiera
   optymalizator kosztowy (i tryb `none`). Działa tylko `ruleRootFirst`. To także wyjaśnia, że hint `ruleRootFirst` z
   zadania 171 "ratuje" zapytania. Do sprawdzenia, czy na serwerze produkcyjnym identyfikatory też mają taką postać.
   Poprawka jest mała (użyć `String`), ale wymaga decyzji, czy robić ją w 119, czy w 169.
2. **Podejrzenie błędu grupowania po polach tekstowych.** `groupBy(street)` zwraca 1 grupę (oczekiwane ok. kilkaset
   tysięcy), a `groupBy(city, miesiąc)` zwraca 92 grupy, czyli tyle, ile miesięcy (miasta nie wchodzą do klucza grupy).
   Hipoteza: pole `city` jest w indeksie zapisane jako `city_S`, a grupowanie czyta wartość pod nazwą `city`, więc
   klucz jest pusty. Do potwierdzenia na dokumencie z indeksu.
3. **`maxResults` obcina wynik grupowania bez ostrzeżenia** (z analizy kodu `CaseSearcher.groupByQuery`).
   Do potwierdzenia testem z `-Dperf.maxResults=50000`.
4. Uwaga o analizatorze: `FakeCaseMapper` używa `KeywordAnalyzer` dla `StringField`, a serwer dla pól niewrażliwych
   na wielkość liter `StandardAnalyzer`. `LuceneVolumeQueryTest` koryguje to dla pola statusu.

## Aktualizacja 2026-10-25: poprawka znaleziska 1

Indeks zapisuje identyfikator sprawy zależnej (`<pole>_id`) jako `StringField` (`CaseMapper.indexSubCases`), a
`DataCollectorSubTopDocsManagerSupport` szukał go przez `LongPoint`. Takie zapytanie nie znalazłoby dopasowania
nawet dla identyfikatorów liczbowych (przypuszczenie: pozostałość po starym formacie). Zmiana w gałęzi `hgdb-119`
(`mercury`, niezacommitowana):

- `collectSubResults`: bez `Long.parseLong`, identyfikator przekazywany jako `String`;
- `buildNestedLoopQuery(String childField, String subCaseId, ...)`: `TermQuery` zamiast `LongPoint`;
- `QueryExplainPlan` (linia 1496): `"-1"` zamiast `-1L`.

Nie zmieniałem `CaseCustomScoreProvider` (ta sama konstrukcja `LongPoint` i `Long.parseLong`, linie 118 i 170). Do decyzji.

Wyniki po poprawce (9 testów przeszło, te same liczby trafień co w `rootFirst`):

| Zapytanie | Wynik | cost | rootFirst | none |
|---|---|---|---|---|
| adres + dziecko (Mts, A) | 7 264 | 0,70 s | 0,76–0,81 s | 0,66–0,68 s |
| adres + dziecko (Lead, Z) | 1 224 | 0,26–0,42 s | 0,62–0,69 s | 0,17–0,24 s |
| data ≥ -3 lata + dziecko (Mts) | 11 132 | 0,80–1,0 s | 0,96–1,1 s | 0,79 s |

Przy 100 tys. adresów plany "najpierw dziecko" są nie wolniejsze od `rootFirst`, a dla rzadkiego dziecka (Lead, Z)
szybsze (2,5–3,5 raza). Różnice dla częstego dziecka są w granicach szumu. Znalezisko 2 (grupowanie po `city`/`street`)
bez zmian: `groupBy(street)` nadal daje 1 grupę, `groupBy(city, miesiąc)` 92.

### Poprawka `CaseCustomScoreProvider` (2026-10-25)

Ta sama zmiana (`String` i `TermQuery` zamiast `Long` i `LongPoint`) w `CaseCustomScoreProvider`
(`customScore` i `buildNestedLoopQuery`). Moduł się kompiluje, testy przechodzą. Do zadania 169 dopisałem uwagę, że
poprawkę robimy w 119.

### Znalezisko 2: wynik diagnozy (2026-10-25)

Hipoteza o nazwie pola (`city` kontra `city_S`) **nie potwierdziła się**. Nazwa jest kodowana poprawnie:
`QueryExplainPlan.prepareCollectionFields` dopisuje sufiks z `alternateSearchTypes`, a `DocGroupByField` koduje go tak
samo. Test diagnostyczny `LuceneVolumeQueryTest.testDiagGroupBy` (`-Dperf.diag=true`) pokazuje, że nawet zwykłe
zapytanie z kolekcją pól `city`, `street` zwraca puste wartości (`{city=, street=}`), więc to nie błąd grupowania.

Przyczyna w danych: w indeksie wygenerowanym testem pola tekstowe (`city_S`, `street_S`, `bos_S`...) są zaindeksowane
i mają `SORTED_SET` docValues, ale **nie są zapisane** (`stored`). Kolektory czytają wartości z pól zapisanych
(`DocumentCellsWithLuceneDoc`), więc dostają pusty tekst i wszystko trafia do jednej grupy. Pola liczbowe (`flatId_N`,
`flatId_S`, `cohort_S`) są zapisane.

Porównanie z indeksem INEA modelu 3.0 (`H:\mercury\20190705_Case_3.0`, 22 mln dokumentów): w próbce są 236 zapisane
pola `_S` (np. `agreementType_S`, `agent_S`), więc na produkcji pola tekstowe są zapisywane. Zgodnie z kodem
(`CaseMapperHelper.addLuceneSimpleField`, gałąź domyślna) pole `STRING` bez `isProtected` dostaje `FieldStore.YES`.
Definicje `city` i `street` w bazie to `STRING`, `is_protected=null`, `is_indexable=t`. Mimo to indeks ich nie zapisał.
**Przyczyna ustalona testem jednostkowym** `CaseMapperStoreTest` (3 przypadki: `isProtected` = null, false, true).
Test przed poprawką dawał `store=NO` dla `isProtected=null`. Konstruktor `AttributeTypeParameter` (linia 477)
zamieniał `null` na `true`: `getIsProtected() == null || getIsProtected()`. Zmiana pochodzi z commitu `dfa775f80`
(2023-01-10, „169: Zmiana typu identyfikatora sprawy na String”), więc wygląda na pomyłkę przy dopisywaniu
`isCaseSensitive` (tam jest `!= null &&`). Skutek: każdy atrybut z `is_protected=null` stał się chroniony, więc pola
tekstowe nie są zapisywane, a ich słowa nie trafiają do `memoFieldWords`.

**Poprawka** (`mercury-core-server`, `AttributeTypeParameter`): `getIsProtected() != null && getIsProtected()`.
Po niej `CaseMapperStoreTest` i `CaseMapperTest` przechodzą. Indeks `perf-100k` trzeba zbudować od nowa
(`buildFullIndex` z bazy, ok. 5 min), a pomiary grupowania powtórzyć. Indeksy z `H:\mercury` powstały przed zmianą
z 2023 roku, więc mają pola zapisane. Do sprawdzenia: czy serwery produkcyjne po aktualizacji do wersji z `dfa775f80`
przebudowały indeks (przypuszczenie: tam po zmianie nowe i zmienione sprawy tracą zapisane pola tekstowe).
Pomiary `groupBy(city, miesiąc)` i `groupBy(street)` z tabeli wyżej są nieważne (92 grupy to same miesiące).

Wniosek na przyszłość: indeksy z `H:\mercury` mają pola tekstowe zapisane, więc nadają się do pomiaru grupowania.

### Przebudowany indeks i ponowne pomiary (2026-10-25)

Indeks przebudowany z bazy po poprawce `isProtected` (`-Dperf.rebuildOnly=true`, 271 s, 200 tys. wierszy, 51 MB).
Pola tekstowe są teraz zapisane (`city_S`, `street_S`, `bos_S`, `technology_S`). **Kopie indeksów** leżą w
`D:\workspace\git\mercury\integrations\lucene\` (katalog w `.gitignore`):

| Katalog | Zawartość |
|---|---|
| `index` | indeks roboczy (z niego czytają testy `LuceneVolumeQueryTest`) |
| `perf-100k` | stara kopia: pola tekstowe **niezapisane** (do porównań, błędne grupowanie) |
| `perf-100k-stored` | nowa kopia: pola tekstowe zapisane |

Grupowanie działa: `groupBy(city, miesiąc)` zwraca 642 grupy (7 miast × ok. 92 miesiące), `groupBy(street)` 13 314 grup.
Zapytanie z `street`/`city` zwraca wartości (`Ulica 1507 (Poznań)`).

Czasy po przebudowie (100 tys. adresów, `maxResults` 200 000, dwa przebiegi):

| Zapytanie | Wynik | cost | rootFirst | none |
|---|---|---|---|---|
| adres (Poznań) | 35 886 | 0,76–1,16 s | 0,67–0,77 s | 0,60–0,67 s |
| adres + zakres 2 lat | 15 279 | 0,29–0,31 s | 0,28–0,30 s | 0,26–0,27 s |
| wildcard `*znań*` | 35 886 | 0,56–0,61 s | 0,54–0,58 s | 0,57–0,58 s |
| OR czterech miast | 76 441 | 1,18 s | 1,18 s | 1,20–1,23 s |
| adres + dziecko (Mts, A) | 7 264 | 0,55–0,64 s | 0,72–0,74 s | 0,56–0,58 s |
| adres + dziecko (Lead, Z) | 1 224 | 0,29–0,43 s | 0,69–0,79 s | 0,17–0,20 s |
| data ≥ -3 lata + dziecko (Mts) | 11 132 | 0,84–0,91 s | 0,98 s | 0,68–0,80 s |
| groupBy(city, miesiąc) | 642 grupy | 1,5–1,9 s | 1,3–1,7 s | 1,3–1,5 s |
| groupBy(street) | 13 314 grup | 1,16–1,21 s | 1,22–1,44 s | 1,15–1,43 s |

Wnioski: zapisanie pól tekstowych nie zmieniło czasów zapytań zwykłych. Grupowanie po wielu grupach kosztuje 1,2–1,9 s przy
35 tys. trafień (wcześniejsze 1 s dotyczyło pustych wartości). Tryby optymalizatora nadal się nie różnią na tej skali,
poza rzadkim dzieckiem (Lead, Z), gdzie `none` i `cost` są 2–4 razy szybsze niż `rootFirst`.

### Pomiary na indeksie INEA 3.0 (2026-10-25)

Indeks `H:\mercury\20190705_Case_3.0` (22 mln dokumentów, 6,9 GB, `slmaddress` 379 tys., `slmappmobiledetails` 377 tys.)
skopiowałem na szybszy dysk: `F:\mercury-indexes\` (`20190705_Case_3.0`, `20190405_Case.2.0`, `INEA_createDate.json`).
Oryginały na `H:` są nietknięte. Pomiary czytają kopię z `F:` (`test-lucene-inea.properties`, nowy plik testowy).
Uruchomienie: `-Dperf.query=true -Dperf.typeCodeLower=true -Dperf.maxResults=500000
-DadditionalArgLine=" -Dmercury.lucene.config.file=/properties/scichy/test-lucene-inea.properties -Xmx6g ..."`
(spacja przed pierwszym `-D` chroni ścieżki przed konwersją Git Bash). Stary format: kody typów małymi literami
(`-Dperf.typeCodeLower=true`), identyfikator dziecka w polu rodzica to liczba (`LongPoint`), nie tekst.

Zgodność wsteczna: `buildSubCaseIdQuery` dla identyfikatora z samych cyfr dodaje `LongPoint` obok `TermQuery`. Bez
tego plany „najpierw dziecko” nie znajdują dzieci w starych indeksach. Do decyzji, czy zostawić (kod produkcyjny).

Wyniki (dysk `F:`, 2 przebiegi, pierwszy zimny; `maxResults` 500 000):

| Zapytanie | Wynik | cost | rootFirst | none |
|---|---|---|---|---|
| adres + dziecko (Mts, A) | 79 158 (`none`: **81 238**) | 3,9–5,1 s | 3,8–4,0 s | **58 s** |
| adres (Poznań) | 10 232 | 0,4–8,5 s (zimny) | 0,3–0,5 s | 0,3 s |
| groupBy(city, miesiąc) | 127 grup | 0,5–1,0 s | 0,43 s | 0,43 s |
| data ≥ -3 lata + dziecko | 0 (dane z 2019) | 0,1 s | 0,09 s | **49–53 s** |

Na `H:` te same zapytania: `adres+dziecko(Mts)` zimny `cost` 56 s (potem 3,7 s), `rootFirst` 4,1 s, `none` 55 s. Dysk `F:`
skrócił tylko pierwszy (zimny) przebieg, więc różnica 4 s a 58 s nie wynika z dysku, tylko z planu.

Wnioski:
1. **Różnice między trybami są realne na dużym indeksie.** Plan „najpierw dziecko” bez optymalizatora (`none`) trwa
   ok. 58 s, a `cost` i `rootFirst` ok. 4 s. To odtwarza benchmark z `LuceneQueryAdvancedTest` (82 s bez optymalizatora).
   Dla zakresu daty bez trafień (`data ≥ -3 lata`) `none` też trwa ok. 50 s, choć wynik jest pusty, więc plan
   nie przerywa się na pustym korzeniu. Kandydat do poprawy.
2. **Rozbieżność wyniku.** `none` zwraca 81 238 trafień, a `cost` i `rootFirst` 79 158 (różnica 2 080). Dwie z trzech
   strategii zgadzają się ze sobą. Przyczyna nieznana (przypuszczenia: strategia `NESTED_LOOP` kontra `IN` z limitem,
   duplikaty rodzic-dziecko, obcięcie `maxResults` w jednym z planów). To błąd poprawności do zbadania.
3. Zakres `now-2/3 lata` nie ma trafień w tym indeksie (dane z 2018–2019). Zakres w testach trzeba liczyć od końca
   danych (`INEA_createDate.json`), nie od dziś.
4. W indeksie INEA `Poznań` ma 10 232 adresów, nie 438 tys. z benchmarku. Zapytanie benchmarku miało inne kryterium
   (do dopasowania z `LuceneQueryAdvancedTest`).

### Testy `@Ignore` dopasowane do indeksów INEA (2026-10-25)

Nowa klasa `LuceneLegacyIndexQueryTest` (`mercury-lucene-indexes`, testy) i wspólna baza `LuceneQueryPerfSupport`
(`measure`, `groupBy`, `maxDateInIndex`; `LuceneVolumeQueryTest` korzysta z niej). Zapytania pochodzą z testów
`LuceneQueryAdvancedTest`, `LuceneQueryBaseTest`, `LuceneQueryChildJoinTest`, `SingleLuceneQuery*Test` (model 3.0) oraz
`LuceneQuerySubQueryParserProblemTest` (model 2.0, jak mówi jego nagłówek). Model wybiera `-Dperf.model=2|3`
(`LuceneQuerySupportTestCase.testedModel` czyta tę właściwość, domyślnie 3). Zakresy dat liczone są od końca danych
(`maxDateInIndex`; w INEA 3.0 koniec danych to 2019-04-01). Nowe pliki konfiguracji: `test-lucene-inea.properties`
(model 3.0, `F:\mercury-indexes\20190705_Case_3.0`) i `test-lucene-inea2.properties` (model 2.0).
Dodatkowe właściwości: `perf.modes` (np. `rootFirst`), `perf.runs`, `perf.maxResults`, `perf.typeCodeLower=true`.

**Model 3.0** (22 mln dokumentów, `maxResults` 500 000, 1 przebieg):
Liczby trafień zgadzają się z komentarzami testów pierwotnych (19823, 7, 7, 136, 25, 595, 4, 3), czyli indeks z `H:` jest
tym, na którym te testy powstały. Wyjątek: benchmark `adres+Mts` (oczekiwane 89 896 z indeksu z 2019-07-03).

| Zapytanie | Wynik | cost | rootFirst | none |
|---|---|---|---|---|
| adres + dziecko Mts (benchmark) | 79 158 / 79 158 / **81 238** | 4,6 s | 4,2 s | **56 s** |
| adres + dziecko Lead (oczek. 136) | 136 | 0,44 s | **1,9 s** | 0,34 s |
| PARENT adres ← SlmLead (oczek. 25) | 25 | 0,32 s | **1,8 s** | 0,31 s |
| wildcard `name:*serwisanta o konieczności*` | 19 823 | **2,3 s** | 0,59 s | 0,53 s |
| FsmServiceOrder, ostatni rok od końca danych | 34 964 | 1,8 s | 0,96 s | 0,91 s |
| FsmServiceOrder, 1/7/30 dni | 1 328 / 3 426 / 5 713 | 0,14–0,40 s | 0,10–0,19 s | 0,10–0,19 s |
| groupBy(miesiąc) FsmServiceOrder | 16 grup | 1,3 s | 0,94 s | 0,88 s |
| groupBy(city) SlmAddress | 105 grup | 0,38 s | 0,63 s | 0,37 s |
| rodzina `detailsUnavailability` (9 zapytań) | 1–595 | 0,1–0,3 s | 0,08–0,17 s | 0,09–0,23 s |
| `AND -businessNetworkAreaId:6931` | **3 / 1 / 3** | 0,22 s | 0,10 s | 0,21 s |

**Model 2.0.** Katalog `H:\mercury90405_Case.2.0` jest **niekompletny**: ma 408 MB i 96 plików, a archiwum
`20190405_Case.2.0.tar.gz` (4,5 GB) zawiera 131 wpisów i po rozpakowaniu 6,9 GB (130 plików, jest `segments_*`).
Wskazał to autor. Rozpakowałem archiwum od nowa do `F:\mercury-indexes90405_Case.2.0` (43 s; w Git Bash trzeba
rozpakowywać przez `gzip -dc /h/... | tar -xf -`, bo `tar` czyta `H:` jako nazwę hosta). Poprzednią, niekompletną kopię
na `F:` usunąłem. Pełny indeks 2.0 ma **te same dane co 3.0** (22 028 880 dokumentów, 85 typów, identyczne liczności
typów i statusów), ale nazwy pól z modelu 2.0 (`typeTypeCodeValue`, `status`, `createDate`, `dateFrom_N`). Powiązania są w nim zapisane **inaczej niż w kodzie**: nadrzędna sprawa ma jedno pole `subCaseIds` (liczby,
`LongPoint`, wszystkie dzieci bez rozróżnienia pola), a dziecko ma `parentFields` (nazwy pól, w których występuje).
Obecny kod szuka pól `<pole>_<id sprawy>` (w modelu 2.0 `address_luceneDocId`, w 3.0 `address_mrc_Case_id`), których tu nie ma,
więc zapytania z dziećmi zwracają 0 (`FSMServiceOrder AND address.typeTypeCodeValue:FsmInstallationAddress`).
Przyczyna jest w historii kodu: commit `d474a2da9` (2019-10-17, zadanie 75, „Błąd wyszukiwania spraw zależnych w modelu
indeksu 2.0”) usunął `LUCENE_SUBCASE_IDS2 = "subCaseIds"` i `indexSubCases2`, żeby model 2.0 i 3.0 budowały powiązania tak
samo. Komunikat commitu: „Podczas migracji z Mercury 2.0 trzeba będzie zrobić przebudowę indeksu Lucene”. Indeks z
2019-04-05 jest starszy od tej zmiany, więc zgodnie z założeniem zadania 75 wymaga przebudowy i nie obsłuży zapytań z
dziećmi. Operator `PARENT` w modelu 2.0 był wcześniej zabroniony (`L0009ValidationException`).
Aby uruchomić takie zapytania na tym indeksie, trzeba by dodać warstwę zgodności (zapytanie po `subCaseIds` zamiast
`<pole>_<id>`) w `QueryExplainPlan` (linie 325, 338), `DocDateValueCollector` (269) i kolektorach
`DataCollectorTopDocsManagerSupport`. To większa zmiana, więc czeka na decyzję.
Zapytania płaskie działają (`config`: `test-lucene-inea2.properties`):

| Zapytanie (model 2.0) | Wynik | cost | rootFirst | none |
|---|---|---|---|---|
| FsmTimeSlot + 400 loginów + 7 dni od końca danych | 5 | 0,55 s | 0,39 s | 0,46 s |
| FsmTimeSlot + 400 loginów + rok | 2 459 | 0,58 s | 0,60 s | 0,78 s |
| `FsmInstallationAddress AND city:*Poznań*` | 78 774 | | 1,9 s | |
| `FSMServiceOrder` + `address.city:*Poznań*` + dziecko | 0 (brak łączy) | 4,3–4,6 s | 0,3–0,9 s | 4,4–4,5 s |

`ZpiPlan` nie występuje w tym indeksie (grupowanie `processing.login` daje 0). Zapytania modelu 2.0 z dziećmi trzeba
albo przenieść na model 3.0 (pola `*_mrc_Case_id`), albo znaleźć indeks 2.0 z polami łączącymi. 
Wnioski:
1. **Błąd poprawności `rootFirst`:** `... AND -businessNetworkAreaId:6931` zwraca 1 trafienie zamiast 3 (`cost` i `none`
   dają 3, oczekiwano 3). To nowy, niezależny od danych błąd. Do zbadania w `QueryExplainPlan` (negacja w planie z
   korzeniem na początku).
2. **`none` kontra reszta (benchmark Mts):** 81 238 kontra 79 158. Rozbieżność nie jest wynikiem różnicy modeli (to ten
   sam indeks 3.0). `cost` i `rootFirst` zgadzają się ze sobą. Oczekiwane 89 896 pochodziło z innego (starszego)
   indeksu, więc nie jest kryterium poprawności.
3. **Żaden tryb nie jest dobry dla wszystkich zapytań:** przy zapytaniach z dzieckiem `rootFirst` jest 5-8 razy wolniejszy
   (Lead, PARENT), a `none` 14 razy wolniejszy dla Mts. Wcześniejszy wynik „wildcard 2,3 s w `cost`” był efektem zimnej
   pamięci podręcznej (pierwsze wykonanie w klasie); po trzech przebiegach `cost` i `rootFirst` mają 0,56 do 0,64 s. To potwierdza, że żaden jeden tryb nie jest dobry
   dla wszystkich zapytań (sprawa 171).
4. Przy zimnej pamięci podręcznej systemu pierwsze zapytanie trwa 8-56 s (dysk). Powtórzenia są wielokrotnie szybsze.

### Gałąź produktowa INEA `v3.0.1.20210709` (2026-10-25, tylko weryfikacja)

Repozytorium `D:\workspace\git\mercury-v3.0.1.20210709` (gałąź do utrzymania, nie do rozwoju; niczego w nim nie zmieniano).
Przejrzany moduł `mercury-lucene-indexes`:

- **Zadanie 75 jest w gałęzi** (commit `d474a2da`, przodek HEAD). Model 2.0 i 3.0 budują powiązania tak samo:
  `CaseMapper.indexSubCases` zapisuje pole `<pole>_<id>` dla każdego pola sprawy zależnej. Nie ma `subCaseIds`
  (`LUCENE_SUBCASE_IDS2`), `CORRECT_SUBCASE_FILED_TYPE` ani warstwy zgodności z formatem sprzed zadania 75.
  Indeks 2.0 z 2019-04-05 (jedno pole `subCaseIds`) nie pasuje więc do kodu produktu, tak samo jak do `master`.
- **Identyfikator sprawy to `Long`**: `List<Long>`, zapis `FieldSearchType.LongField`, zapytanie
  `LongPoint.newRangeQuery` (`DataCollectorSubTopDocsManagerSupport`, linia 183). To stan `master` sprzed zadania 169.
  Zgadza się z indeksem INEA 3.0 (`appMobileDetails_mrc_Case_id` ma wartość liczbową).
- Model 2.0 zostaje w kodzie tylko jako różnice nazw pól (`luceneDocId` zamiast `mrc_Case_id`, `typeTypeCodeValue`
  zamiast `mrc_typeCodeValue`, brak prefiksu `mrc_`): `CaseIndexer`, `CaseMapperHelper`, `DictionaryMapperHelper`,
  `LuceneHelper`.
- **Błędy znalezione w `master` nie dotyczą tej gałęzi:** `Long.parseLong` (znalezisko 1) działa tu poprawnie, bo
  identyfikator jest liczbą, a konstruktor `AttributeTypeParameter` przepisuje `isProtected` bez zmiany
  (`this.isProtected = paramDefinition.getIsProtected()`, linia 476). Błąd z commitu `dfa775f80` (zadanie 169) jest
  tylko w `master`.
- Zgodność wsteczna w `buildSubCaseIdQuery` (`LongPoint` obok `TermQuery` dla samych cyfr) służy pomiarom na indeksach
  INEA w `master`. W gałęzi produktowej jest niepotrzebna.

### Mały indeks w formacie 2.0 zbudowany z bazy (2026-10-25)

Zgodnie z ustaleniami (model 2.0 tylko dla zgodności wstecznej, zmiany z 3.0 obowiązują także w 2.0, upgrade wymaga
przebudowy indeksu, stary indeks `20190405_Case.2.0` jest bezużyteczny dla rozwoju) zbudowałem indeks w formacie 2.0
z tych samych 200 tys. wierszy w bazie `mercury-db` (`-Dperf.rebuildOnly=true` z konfiguracją
`mercury.lucene.model.version=2`, 250 s, 51 MB). Nowe pliki konfiguracji w `mercury-srv` (testy):
`test-mercury-m2.properties`, `test-lucene-m2.properties` (katalog roboczy `mercury/integrations/lucene/index-m2`).
**Kopia na F:** `F:\mercury-indexes\perf-100k-model2`. Do pomiarów: `mercury-lucene-indexes/.../test-lucene-m2.properties`
z `-Dperf.model=2` i `-Dmercury.config.file=/properties/scichy/test-mercury2.properties`.

Format 2.0 zbudowany obecnym kodem: id sprawy w polu `luceneDocId` (wartość `SlmAddress.2994803`), powiązanie w polu
`appMobileDetails_luceneDocId` (tekst), status sprawy w polu `status`, kod typu w `typeTypeCodeValue`. Czyli powiązania
działają tak samo jak w 3.0 (tylko inne nazwy pól).

**Różnica modeli widoczna w zapytaniach:** w modelu 2.0 atrybut o nazwie zajętej przez pole podstawowe dostaje prefiks
`custom_` (`CaseMapperHelper.ATTR_FIELD_PREFIX_FOR_DUP`), więc `status` sprawy zależnej (np. `SlmAppMts`) to
`appMobileDetails.custom_status`, a `appMobileDetails.status` to status sprawy (A, Z). W modelu 3.0 jest odwrotnie
(`mrc_status` kontra `status_S`). Testy mapują to w `LuceneQueryPerfSupport.measure` dla `-Dperf.model=2`.
Dodatkowo `FakeCaseMapper` ustawia wrażliwość na wielkość liter także dla `typeTypeCodeValue`.

Wyniki modelu 2.0 (100 tys. adresów, `maxResults` 200 000): **identyczne liczby trafień jak w modelu 3.0** dla wszystkich
zapytań (35 886; 1 224; 7 264; 11 132; 15 279; 76 441; groupBy 642 i 13 314 grup) i **zbliżone czasy**
(Poznań 0,55–1,1 s; dziecko Mts 0,55–0,75 s; Lead,Z `cost` 0,21–0,37 s, `rootFirst` 0,67–0,70 s, `none` 0,14–0,20 s;
groupBy 1,1–1,8 s). Wniosek: zmiany z modelu 3.0 działają w 2.0 w tym zakresie.

### Naprawa błędu `rootFirst` z wykluczeniem (2026-10-25)

**Objaw:** `typ AND status:A AND detailsUnavailability.unavailabilityStatus:Otwarta AND -businessNetworkAreaList.businessNetworkAreaId:6931`
zwracało w trybie `rootFirst` 1 trafienie zamiast 3 (`cost` i `none` dawały 3).

**Przyczyna:** w `QueryExplainPlan.prepare` (gałąź `rootIsBetter`, ok. linii 1066) wpis zapytania głównego dostawał
`arg.queryOccur = rootOccur` (MUST). Wymagalność wpisu trafia potem do `ExplainResult.subOccurs`
(`prepareSubPlan`, linia 462: `addEntryResult(result, subQ.occur, ...)`). Plan root-first tworzy po jednym zapytaniu
głównym na każde podzapytanie, więc wszystkie dostały MUST, a `MUST_NOT` podzapytania zniknęło. Plan wyglądał jak
`PREPARE_RESULT: MUST, MUST` (zamiast `MUST, MUST_NOT`), czyli przecięcie zamiast różnicy. Gałąź bez root-first używa
wymagalności podzapytania (`arg.queryOccur = queryOccur`), stąd poprawny wynik w `cost` i `none`.
Wpisy miały też tę samą nazwę (`R:S.BbQ.0001.root`), ale mapowanie po nazwie nie miało wpływu na ten błąd.

**Poprawka:** w gałęzi root-first `arg.queryOccur = queryOccur` (wymagalność podzapytania) z komentarzem
(`QueryExplainPlan`, 6 linii). Skutki dla podzapytań `SHOULD` w tej samej grupie poprawiają się tak samo
(wcześniej wymuszane na MUST).

**Weryfikacja** (INEA 3.0, `cost` i `rootFirst`): `AND -area` 3 / 3 (było `rootFirst`=1). Pozostałe zapytania bez zmiany:
simple 4, base+Otwarta 4, AND 1, OR 4, NOT IN 3, SUB 595, CHILD 4, CHILD OR 4, PARENT 25, adres+Lead 136, adres+Mts 79 158.
**Test regresji:** `LuceneNestedQueryOccurTest` (`mercury-lucene-indexes`, testy). Buduje mały indeks w pamięci
(`RAMDirectory`: 5 zleceń `FsmServiceOrder`, dzieci `detailsUnavailability` i `businessNetworkAreaList`) i sprawdza w
trzech trybach (`cost`, `rootFirst`, `none`) pięć zapytań, m.in. wykluczenie obszaru 6931 (oczekiwane 2) i `NOT IN`.
Z poprawką przechodzi. Po cofnięciu poprawki (`arg.queryOccur = rootOccur`) pada na `wykluczenie obszaru 6931 (tryb
rootFirst) expected:<2> but was:<1>`, więc rzeczywiście wykrywa błąd. Nie wymaga dużego indeksu, uruchamia się z
`-Duser=scichy` jak inne testy modułu.

### Rozbieżność wyników benchmarku Mts: przyczyna (2026-10-25)

**Objaw:** zapytanie `SlmAddress AND city:Poznań AND appMobileDetails.(SlmAppMobileDetails, status:SlmAppMts, status A)`
na indeksie INEA 3.0 zwracało 79 158 (`cost`, `rootFirst`) i 81 238 (`none`). Test z 2019 roku oczekiwał 89 896.

**Prawda odniesienia** (czysty Lucene, połączenie rodzic-dziecko policzone poza silnikiem Mercury): 140 131 adresów w
Poznaniu, 219 238 dzieci `SlmAppMts` ze statusem A, **89 896 adresów z takim dzieckiem** (po jednym dziecku na adres, więc
liczba par też wynosi 89 896). Oczekiwana wartość z 2019 roku była więc poprawna, a dziś żaden plan jej nie zwraca.

**Przyczyna: ciche obcięcie do `lucene.query.maxHits`.** W konfiguracji pomiarów `lucene.query.maxHits=200000`, a dzieci
jest 219 238. W logu planu `cost` i `rootFirst`: `collectSubResultsByCollection: childCellsResult.size=200000` (powinno
być 219 238), czyli 19 238 dzieci i ich 10 738 adresów zniknęło. Plan `none` (dziecko najpierw) zbiera do `numHits`
dzieci i gubi 8 658 adresów. Plany różnią się tylko tym, **które** trafienia wypadają, więc wyniki są różne, a oba
błędne.

**Dowód:** po podniesieniu `lucene.query.maxHits` do 1 000 000 (plik `test-lucene-inea-maxhits1m.properties`) wszystkie
trzy tryby zwracają **89 896** (`cost` 4,3 s, `rootFirst` 3,8 s, `none` 62,7 s), a w logu `childCellsResult.size=219238`.

**Skutki:**
- Błąd poprawności, nie wydajności: wynik jest po cichu niepełny, bez ostrzeżenia, flagi i błędu. Dotyczy też `groupBy`
  (agregaty z obciętych trafień) i `count`.
- Domyślne limity produkcyjne są niższe niż w moich pomiarach: `lucene.query.maxHits=100000` w konfiguracjach serwera
  (`mercury-server/.../lucene.properties`), 10 000 w `mercury-srv/src/main/resources/lucene.properties`. Zapytanie z
  więcej niż 100 tys. trafień dziecka daje tam niepełny wynik.
- To ten sam mechanizm, który autor opisał jako „`maxResults` spędzający sen z oczu”. Podział zapytania na przedziały
  (wątki, węzły) pozwoliłby go ominąć, ale **najpierw trzeba sygnalizować obcięcie** (patrz plan).
- Wcześniejsze wnioski: różnica `none` kontra `cost` nie wynikała z modelu 2.0 ani 3.0, tylko z limitu.

## Plan z 2026-10-24 (zastąpiony)

Aktualny plan i decyzje: `plan-i-decyzje-2026-10-25.md`.


1. Poprawka znaleziska 1 (`Long` na `String`) i powtórzenie pomiarów w trybach `cost`, `none`, a potem porównanie z `rootFirst`.
2. Potwierdzić (lub obalić) znalezisko 2 na dokumencie z indeksu i naprawić grupowanie, albo opisać przyczynę.
3. Test obcięcia: `-Dperf.maxResults=50000` na `groupBy` i `count`, wynik z ostrzeżeniem `truncated`.
4. Skala: zestaw 1 mln adresów (ok. 3,5 h zapisu, trzeba nowej sterty i miejsca) lub przybliżenie rozkładu z benchmarku
   (438 tys. adresów z Poznania). Generator trzeba przyspieszyć albo dzielić na kilka uruchomień.
5. Dodać typy `Fsm*` (zestaw 11 kształtów z katalogu w analizie) i wzorzec pulpitu Grafany (równoległe zapytania
   grupujące, różne zakresy dat).
6. Prototyp statystyki rozkładu daty (rozszerzenie `DateMetricQuery`) i planisty podziału po dacie (wątki, potem węzły).
7. Decyzje do podjęcia: w której gałęzi poprawiać znalezisko 1; czy sekretarz histogramu ma być nowy czy częścią
   sekretarza indeksowania.

## Stan repozytoriów

- `mercury`, gałąź `hgdb-119`: zmiany niezacommitowane (tylko testy):
  `mercury-lucene-indexes/.../fake/FakeCaseMapper.java` (zmiana),
  `mercury-lucene-indexes/.../indexes/LuceneVolumeQueryTest.java` (nowy),
  `mercury-srv/.../logic/LuceneVolumeTest.java`, `.../scenarios/LuceneVolumeScenario.java`, `.../volume/` (nowe).
- Workspace (`main`): `analiza-2026-10-24.md`, to podsumowanie, uzupełnienie `TASK.md` i `156/podsumowanie` (niezacommitowane).
- Baza `mercury-db` zawiera 200 tys. wierszy testowych (adresy i dzieci). Dane Swaggera zostały wyczyszczone (zgoda autora).
- Procesy Maven nie działają. Tomcat lokalny nie jest uruchomiony.

### Baza pomiarowa W0 (2026-10-25, plik `baseline-2026-10-25.csv`)

Przebieg 41 zapytań na indeksie INEA 3.0 (22 mln dokumentów, kopia `F:`), `lucene.query.maxHits=1000000` (bez obcięcia), 3 tryby,
2 przebiegi, najlepszy czas. Kolumna „żal” = czas `cost` / czas najlepszego z planów stałych (`rootFirst`, `none`). Czas
całego przebiegu 26,6 min (tryb `none` trwa 60 do 290 s dla zapytań z 219 tys. dzieci).

**Poprawność:** `0` zapytań z różnymi wynikami w trzech trybach (przy wyłączonym obcięciu). Wcześniejsze różnice wynikały wyłącznie z `maxHits`.

**Żal optymalizatora:** mediana 1,10; 90. percentyl 2,36; maksimum 4,90. Powyżej 1,25: 16 zapytań, powyżej 2: 11 (z 41).
Większość dużych żali dotyczy zapytań szybkich (poniżej 0,3 s, różnice setek milisekund). Istotne bezwzględnie (różnica > 0,5 s):

| Zapytanie | `cost` | `rootFirst` | Różnica | Żal |
|---|---|---|---|---|
| Poznań (140 tys.) + dziecko Rfs (39,6 tys.), stosunek 0,28 | 13,7 s | 2,9 s | +10,7 s | 4,66 |
| Leszno (12,8 tys.) + dziecko Vrf (7,6 tys.), stosunek 0,6 | 2,2 s | 0,46 s | +1,8 s | 4,90 |
| Leszno + dziecko Abs (5,1 tys.), stosunek 0,4 | 1,5 s | 0,35 s | +1,1 s | 4,20 |

Wniosek: **optymalizator wybiera plan „dziecko najpierw” także wtedy, gdy dziecko ma tylko 28 do 60% trafień korzenia**, a
plan „korzeń najpierw” jest wtedy 4 do 5 razy szybszy. Przyczyna: reguła porównuje `int(ln(docFreq))`, więc przekroczenie
granicy kubełka (np. ln 7 610 = 8,9 kontra ln 12 786 = 9,5) wystarcza do wyboru dziecka najpierw. Zmierzone koszty
jednostkowe (0,26 do 0,34 ms na trafienie dziecka w pętli kontra 0,02 do 0,04 ms na trafienie korzenia w łączeniu zbiorczym)
dają próg opłacalności ok. 0,06 do 0,12, a nie ok. 0,4 do 0,6 jak w regule. Trafne decyzje: Mts (korzeń), Lead i `PARENT`
(dziecko), serie Poznań z Vrf, Abs, Clb, Lty (dziecko, żal 1,0 do 1,1). To potwierdza kierunek zmian W3 (jawny model kosztu z
kalibrowanymi stałymi, sondy liczności).


### Uwagi operacyjne (2026-10-25, W1)

- **Wielkość liter kodu typu w testach:** domyślnie jak dawniej (zapytanie zmniejsza litery; pasuje do indeksów INEA, więc
  `-Dperf.typeCodeLower` nie jest już potrzebne). Dla indeksu wygenerowanego testem `LuceneVolumeTest` (zachowuje wielkość
  liter, np. `SlmAddress`) trzeba dodać **`-Dperf.typeCodeCaseSensitive=true`**.
- **Nie uruchamiać `mvn test -pl <moduł> -am` bez `-Dtest`:** zbiera testy modułów nadrzędnych, które czyszczą bazę
  (widziano `delete from IGO_DA_CASES` w testach `mock`). Do testów modułu `mercury-lucene-indexes` używać
  `-Dtest=org/mercury/lucene/**/*Test,pro/ibpm/mercury/lucene/**/*Test -DfailIfNoTests=false`. Baza `mercury-db` miała w tym
  momencie nadal 200 000 wierszy (przebieg przerwany po wykryciu, pozostały fork surefire zabity).
