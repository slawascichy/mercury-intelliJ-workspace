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

## Plan na jutro

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
