# Ewidencja zależności i konfliktów scenariuszy testowych (`mercury-srv`)

Dokument zbiera zależności i konflikty między scenariuszami `SrvTest` i klasami testowymi
`mercury-srv`. Cel: nie powtarzać szukania przyczyn porażek, które zależą od kolejności lub od stanu
zostawionego przez poprzedni scenariusz.

Stan: 2026-10-31. Wpisy oznaczone „zweryfikowane” sprawdziłem przebiegiem testów lub w kodzie.
Wpisy oznaczone „przypuszczenie” są wnioskiem bez dowodu.

## Mechanizmy współdzielenia stanu

| Mechanizm | Skutek | Status |
|---|---|---|
| Jeden proces JVM dla wszystkich klas testowych w jednym przebiegu `mvn test` | Klasy testowe i scenariusze współdzielą pola statyczne i indeks Lucene. Klasy poza `SrvTest` (np. `LuceneIndexerOnlyTest`) uruchamiają się przed nim i zostawiają stan. | zweryfikowane (log `mercury-srv/target/test.log` i odtworzenie) |
| Statyczna flaga `LogicScenarioHelper.isIndexLuceneCreated` | Indeks spraw buduje się raz, w pierwszym scenariuszu, który go potrzebuje. Kolejne scenariusze ładują dane do bazy, ale indeksu nie przebudowują. | zweryfikowane w kodzie |
| Indeks Lucene na dysku, katalog zależy od profilu (`scichy`: `integrations\lucene`, `scichy-test`: `integrations\lucene-test`) | Stan indeksu może przeżyć między przebiegami. Zmiany z poprzedniego przebiegu mogą być widoczne w następnym. | zweryfikowane w konfiguracji |
| Statyczna mapa `AttributeTypeParameterFactory.attributies` (klucz `nazwa#wersja`) | Wpis przeżywa czyszczenie bazy w testach. `getAttributeType(..., TO_USE, ...)` zwraca go bez zaglądania do bazy. Wpis jest usuwany tylko przez logikę (`ParamDefinitionDAO.removeFromCache`, wywołanie z logiki i z `ParamDefinitionRegistryChangesReceiver`) albo ręcznie (`clearAttributiesMap`), a `MockDataUtils.cleanScheme` usuwa dane z pominięciem logiki. Nowa definicja z tym samym kluczem (np. `id#1`) dostaje stary typ. | zweryfikowane (diagnostyka `CaseBusiness`, naprawa testu) |
| Definicje typów (`TypeCase`, definicje parametrów) po czyszczeniu schematu | Typ załadowany przez jeden scenariusz był widoczny w następnym przebiegu (`luceneFieldsScenario` przeszedł bez własnego ładowania po przebiegu, który typ załadował). | zweryfikowane obserwacją; mechanizm nieustalony |
| Runner zatrzymuje się na pierwszej porażce | Scenariusze po porażce nie są uruchamiane. Porażka wcześniejszego scenariusza maskuje późniejsze. | zweryfikowane w przebiegach |
| Scenariusze bez klucza `test.skip.<nazwa>` w profilu | Uruchamiają się domyślnie (np. `forceAddPKScenario`). | zweryfikowane w przebiegach |

## Zależności i konflikty

| Scenariusz / klasa | Zależy od lub koliduje z | Objaw | Dowód | Stan |
|---|---|---|---|---|
| `LuceneIndexerOnlyTest` → `luceneIndexerScenario` (w `SrvTest`) | Pierwsze uruchomienie `LuceneIndexerScenario` zostawia w indeksie spraw grupę KTM nr 7 z kodem `CODE56 35122` (linia 375). Drugie uruchomienie w tym samym JVM używa tego indeksu bez przebudowy. | `luceneIndexerScenario` pada na linii 366 (`Nie spodziewam się, jakiegoś wyniku`). | odtworzone (klasa i `SrvTest` w jednym przebiegu) | rozwiązane: klucz `test.skip.package.LuceneIndexerOnlyTest=true` w profilu |
| `DocumentTypeFieldsTest` | Klasa poza `SrvTest`, uruchamia się przed nim w jednym przebiegu. | brak porażki; ryzyko stanu jak wyżej | przypuszczenie | klucz `test.skip.package.DocumentTypeFieldsTest=true` w profilu |
| `luceneFieldsScenario` → `caseBusinessScenario` | Oczekiwał typu `TestMrcObject` (pola `listDates`, `users.*`, `manager.*`), który tworzy `caseBusinessScenario`. | „nie znalazłem pola listDates” | odtworzone (przebieg z włączonym i wyłączonym `caseBusinessScenario`) | rozwiązane: scenariusz sam ładuje `TestMrcObject.single.v2.xml` |
| `caseBusinessScenario` | Wymaga wcześniejszych scenariuszy. Uruchomiony sam kończy się statusem ERROR: `QuerySyntaxException: unexpected AST node: query` w `MQuery.getPagedResult` (zapytanie `select DISTINCT ca.id from Case ca JOIN ca.type ct JOIN ct.subTypes …`). | ERROR w izolacji | odtworzone | otwarte; których scenariuszy wymaga, nie ustalono |
| `caseBusinessScenario` → `forceAddPKScenario` | `caseBusinessScenario` tworzy definicję `id#1` jako `INTEGER` (pole `id` obiektu `TestMrcObject`). Po czyszczeniu bazy wpis `id#1` zostaje w statycznej mapie `AttributeTypeParameterFactory`. `forceAddPKScenario` tworzy `id#1` jako `STRING`, ale przy ładowaniu `v2.withId` kod pobiera typ z tej mapy (`INTEGER`) i tworzy trzecią wersję typu. | `ForceAddPKScenario.java:99`, `expected:<2> but was:<3>` | zweryfikowane diagnostyką (`attrType=INTEGER` mimo `oldDefType=STRING`) i naprawą | rozwiązane dwiema niezależnymi poprawkami: czyszczenie mapy w `LogicScenarioHelper.cleanAllDataFromDB` (`clearAttributiesMap(null)`) oraz ścisła reguła zgodności wartości w `CaseBusiness` (obserwacja 132) |
| `datasetScenario` | Po naprawie `forceAddPKScenario` runner dociera do `datasetScenario`, który pada. Z czyszczeniem mapy atrybutów: `Nie znaleziono ParamDefinition dla NazwiskoKlienta, wersja 2` i `Transaction silently rolled back`; bez czyszczenia: `Not-null property references a transient value`. W obu przypadkach nie załadowano 8 plików. | `DatasetScenario.java:132` (`Pliki, których nie udało się załadować`) | odtworzone (dwa przebiegi bez `forceAddPKScenario`) | otwarte; przyczyny nie zbadano. Nie wynika z czyszczenia mapy, bo pada także bez niego. |
| `luceneBackupScenario` | Niestabilny: czasowy wyścig przy odtwarzaniu backupu oraz zależność od stanu `index2` w katalogu indeksu profilu. | `ComparisonFailure` (`LuceneBackupScenario.java:261`) albo `Nie mozna odczytac z indeksu sprawy z id=TODO.63 … index2` | zaobserwowane w trzech przebiegach, w pozostałych OK (obserwacja 134) | otwarte; przyczyna nieustalona |

### Bisekcja `forceAddPKScenario` (2026-10-31, profil `scichy-test` z flagami `scichy`)

| Zestaw włączonych scenariuszy | Wynik `forceAddPKScenario` |
|---|---|
| sam (klasa `ForceAddPKOnlyTest`, usunięta) | OK |
| `changeCaseVersionScenario`, `caseBusinessSaveListScenario` | OK |
| lista `scichy` do `securityContextHelperTypeParamsScenario` bez `luceneBackup*` i bez `caseBusinessScenario` | OK |
| ta lista + `caseBusinessScenario` | FAILED (3 wersje typu) |
| ta lista + `caseBusinessScenario` + `changeCaseVersionScenario` + `caseBusinessSaveListScenario` | FAILED |
| sam `caseBusinessScenario` + `forceAddPKScenario` | `caseBusinessScenario` ERROR (zależność wyżej) |

Ustalenie przyczyny (tabele `IGO_DA_TYPES`, `IGO_DA_TYPEPARAMETERS`, `IGO_DA_PARAMETER_DEFINITIONS` oraz tymczasowy log w `CaseBusiness.encodeSimpleValue4NewType`):

- Wersja 3 typu `ForceAddPkText` powstaje przy ładowaniu `ForceAddPK.text.v2.withId.xml`. Pliki `v2` i `v2.withId` mają identyczną strukturę (`field001`, `field002`, `id`, wszystkie `type="String"`), więc dane nie dają podstaw do nowej wersji.
- Różnica wersji 2 i 3 to parametr `id`: tekstowy w wersji 2 (definicja `id#1`, `STRING`), liczbowy w wersji 3 (definicja `id#2`, `INTEGER`).
- Log przy ładowaniu `v2.withId`: `pVal.type=String`, `value=known-1`, a po bloku weryfikacji istniejącego parametru `attrType=INTEGER`, mimo że `oldDef` (`id#1`) ma `paramType=STRING`. Blok czyta typ z `AttributeTypeParameterFactory` (`paramDefinitionLogic.getAttributeTypeParameter`), czyli ze statycznej mapy, nie z bazy. Gałąź „przywracam zmianę typu parametru” (`CaseBusiness`, `currentAttrType != attrType`) przyjmuje wtedy `INTEGER`.
- Mechanizm identyfikacji typu zadziałał zgodnie z założeniem. Błędne było wejście: stary wpis `id#1` (`INTEGER`) z `caseBusinessScenario`, który przeżył czyszczenie bazy.
- Sprawdzone i wykluczone: `FORCE_CHANGE_TYPE` (jest w `Context`), pamięć podręczna encji JPA (`getCache().evictAll()` nie pomogło), zmiany w plikach XML scenariusza.

## Reguły dla nowych scenariuszy i klas testowych

1. Scenariusz nie zakłada, że dane typów lub indeks zostawił inny scenariusz. Potrzebne typy ładuje sam.
2. Scenariusz, który zmienia dane w indeksie spraw (np. zmiana kodu KTM, partycypanta), ma przywracać stan na końcu albo wymuszać przebudowę indeksu (`LogicScenarioHelper.setIndexLuceneCreated(false)`).
3. Klasa testowa poza `SrvTest` czyta klucz `test.skip.package.<Klasa>` (wzór: `LuceneVolumeTest`). Autor dopisuje klucz do profilu `scichy`, Claude do `scichy-test`.
4. Każdy scenariusz w `SrvTest` ma klucz `test.skip.<etykieta>` w profilach, żeby nie uruchamiał się domyślnie bez wiedzy autora.
5. Porażkę zależną od kolejności zapisuj w tabeli wyżej z dowodem (przebieg lub kod) i statusem.

## Jak badać zależność

Ustaw w lokalnym profilu `test.skip.<etykieta>=false` tylko dla wybranych scenariuszy (resztę na `true`) i uruchom `mvn -o test -pl mercury-srv -am -Duser=scichy-test -Dtest=SrvTest`. Dziel zbiór scenariuszy na pół, aż zostanie najmniejszy zestaw, który powoduje porażkę. Pamiętaj, że runner zatrzymuje się na pierwszej porażce.

Źródło: `mercury-srv/src/test/java/pro/ibpm/mercury/logic/` (`SrvTest`, `LogicScenarioHelper`, scenariusze), logi przebiegów z 2026-10-31.
