# [190] Dokumentacja – aktualizacja opisu metadanych typów spraw

> Zadanie wydzielone z [133 – Swagger, etap 2](../133-Swagger-implementacja/etap-2-openapi-typy-spraw.md).

## Cel zadania
Zaktualizować stronę „Case metadata” serwisu hgdb.org tak, aby była zgodna z kodem.
Kod ma wyższy priorytet niż dokumentacja: gdy się różnią, poprawia się dokumentację.

## Kontekst i Wymagania

Strona: `scisoftware-webpage/docusaurus-hgdb/docs/003_Architecture/001_Cases_MetaData/index.mdx`
oraz jej polska wersja w `i18n/pl` (ścieżki względne do `D:\workspace\git`).

Rozbieżności znalezione przy analizie zadania 133 (`docs/obserwacje.md`, pozycje 23–24):

| # | Miejsce w dokumentacji | Dokumentacja | Kod | Poprawka |
|---|---|---|---|---|
| 1 | `TypeParam.updateable` | Wartość z domyślnym `true` | Enum `Updatable`: `READWRITE`, `READONLY`, `ONCREATE`, `ONCREATEVISIBLE`, `OTHER`. Domyślnie `READWRITE` (`mercury-core/.../entities/beans/Updatable.java`, `CaseBusinessSupport.java:1911-1914`) | Opisać wartości enuma i ich znaczenie |
| 2 | `ParamDefinition.recommendedLabel` | `recommendedLabel` | Pole `recomendedLabel` (literówka w kodzie) | Podać nazwę z kodu, z uwagą o pisowni |
| 3 | Tabela `ParamDefinition` | Wiersze `mimeType` i `knownLobMetadata` sklejone w jednej linii | – | Rozdzielić wiersze |
| 4 | `arg4`, `arg5` | Metadane i mimeType LOB „do podglądu” | Nadpisują `ParamDefinition.knownLobMetadata`/`mimeType` przy odczycie sprawy (`CaseBusiness.java:1188-1195`) | Opisać pierwszeństwo `arg4`/`arg5` |
| 5 | `TypeCase` | Brak pola `versionMinor` | `versionMinor` (Double), wersja minor tworzona przy zmianie starszej wersji (`TypeCaseLogicHelper.createNewMinorVersion`) | Dodać pole |
| 6 | `HtmlSupportedControl.NUMBER` | „Input field with integer format validation” | Liczba zmiennoprzecinkowa | Poprawić opis |
| 7 | `arg1..arg5` dla SELECT/MULTI i STRING | `arg1` = wartość/nazwa, `arg2` = `size`, `arg3` = para `value\|name`; STRING: `arg1` = typ inputu | Kod jest niespójny wewnętrznie (patrz niżej) | Opisać według kodu po rozstrzygnięciu |
| 8 | Domyślne wartości `arg*` | Brak | `HtmlArguments.setArgumnets` (`mercury-core/.../attrs/html/HtmlArguments.java:26-125`) | Dodać tabelę wartości domyślnych według `AttributeType` |
| 9 | `TypeParam.label`, `tooltip`, `TypeCase.description`, `ParamDefinition.valueDefinition` | Brak informacji o lokalizacji | Wartość `${klucz}` to klucz encji `Resource` (klucz + język), tłumaczony przez `AttributeTypeParameter.prepareLocalizedMessage`. Zasoby predefiniowane: `resources_{de,en,es,fr,ko,pl}.properties` | Opisać mechanizm i to, które pola są tłumaczone przez serwer (patrz zadanie 133, etap 2) |
| 10 | `isRequired` | Pole sterujące formularzem | Do sprawdzenia: zachowanie serwera przy braku wymaganego pola | Uzupełnić po weryfikacji |

### Rozbieżność w kodzie (pozycja 7)

Dla list wyboru kod czyta `arg*` na dwa sposoby:

| Pole | `HtmlArguments`, `AttributeParser`, Lucene `CaseMapper`, `MPoiServerSupport` | `HtmlControlUtils.prepareSelectControl` (`mercury-ws-app`) |
|---|---|---|
| `arg1` | wartość (`true`) / nazwa | wartość (`useValue`) |
| `arg2` | `size` | `optional` |
| `arg3` | para `value\|name` | `size` |
| `arg4` | – | `useNameAndValue` |

Dla STRING `HtmlControlUtils` czyta typ inputu z `arg2`, a `HtmlArguments` zapisuje go w `arg1`.

Zapis, odczyt, indeks i eksport stosują wariant z lewej kolumny. Przypuszczenie: `HtmlControlUtils`
ma błąd. Decyzja autora: poprawić `HtmlControlUtils` (osobna zmiana w `mercury`) czy opisać obie
konwencje.

### Ograniczenia

- Zmiany w repozytorium `scisoftware-webpage` (submoduł `docusaurus-hgdb`).
- Język domyślny serwisu: angielski. Polska wersja w `i18n/pl` musi zostać zaktualizowana równolegle.

## Definicja Gotowości (DoD)

- Pozycje 1–10 poprawione w wersji angielskiej i polskiej.
- Decyzja w sprawie pozycji 7 podjęta i zapisana w tym pliku.
- `npm run build` serwisu przechodzi bez nowych ostrzeżeń o linkach.
- Obserwacje 23 i 24 w `docs/obserwacje.md` oznaczone ✅.

## Kluczowe Pliki w Projekcie

| Plik | Rola |
|---|---|
| `scisoftware-webpage/docusaurus-hgdb/docs/003_Architecture/001_Cases_MetaData/index.mdx` | Strona do poprawy |
| `scisoftware-webpage/docusaurus-hgdb/i18n/pl/...` (odpowiednik powyższej) | Wersja polska |
| `mercury-lib/mercury-core/src/main/java/pro/ibpm/mercury/attrs/html/HtmlArguments.java` | Domyślne `arg*` |
| `mercury-lib/mercury-core/src/main/java/pro/ibpm/mercury/entities/beans/Updatable.java` | Wartości `updateable` |
| `mercury-lib/mercury-entities/src/main/java/pro/ibpm/mercury/entities/attr/TypeParam.java`, `ParamDefinition.java`, `TypeCase.java` | Encje |
| `mercury/mercury-ws-app/src/main/java/pro/ibpm/mercury/html/HtmlControlUtils.java` | Generator formularzy |
| `mercury/mercury-srv/src/main/java/org/mercury/single/node/business/data/CaseBusiness.java` | Nadpisywanie metadanych LOB |

## Słownik / Zasady

- Kod ma wyższy priorytet niż dokumentacja.
- Opisywać tylko to, co da się zweryfikować w kodzie. Wnioski niepotwierdzone oznaczać jako przypuszczenie.
