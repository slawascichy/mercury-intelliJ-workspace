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

## Decyzja do pozycji 7 (2026-10-26)

Decyzja autora: **poprawić `HtmlControlUtils`** (`mercury-ws-app`), czyli dostosować `prepareSelectControl` i odczyt typu inputu dla STRING do konwencji
stosowanej przez `HtmlArguments`, parser wartości, indeks Lucene (`CaseMapper`) i eksport POI (`MPoiServerSupport`). Zakres zadania rośnie o zmianę w repozytorium `mercury`
(oprócz dokumentacji w `docusaurus-hgdb`):

1. Poprawka `HtmlControlUtils.prepareSelectControl` (arg1 = wartość/nazwa, arg2 = `size`, arg3 = para `value|name`) i odczytu typu inputu dla STRING (arg1).
2. Test jednostkowy generowania kontrolki dla SELECT/MULTI i STRING.
3. Pozycja 7 w dokumentacji opisuje już jedną konwencję (według kodu po poprawce).
4. Sprawdzić, czy kod wywołujący `HtmlControlUtils` (formularze w `mercury-ws-app`) nie zakłada starych znaczeń `arg2` i `arg3` (do sprawdzenia przy realizacji).

Dodatkowy zakres z zadania 119 (ta sama witryna): parametry `lucene.properties` (`tasks/hgdb/119-…/parametry-konfiguracji-lucene-2026-10-26.md`),
pola `truncated` i `totalHits` w odpowiedzi stronicowanej, błędy sortowania `L0009.7` i `L0009.8`.

## Realizacja (2026-10-27)

Stan: kod i dokumentacja gotowe, bez commitów (commituje autor). Nie uruchomiono `npm run build`.

**Kod (`mercury`, gałąź `hgdb-190`, `mercury-ws-app`):**
- `HtmlControlUtils.prepareSelectControl`: `arg1` = wartość/nazwa, `arg2` = `size`, `arg3` = para `value|name`. `arg4` nie jest już używany dla list. Pole `optional` wynika z `isRequired` (`isRequired = false` daje pustą opcję, zgodnie z opisem w dokumentacji).
- Typ inputu dla STRING jest czytany z `arg1` (wcześniej z `arg2`, który zarazem był ustawiany jako `size`).
- Test `HtmlControlUtilsTest` (8 testów, atrapy `MTypeParam` i definicji): SELECT, MULTI, STRING, zależność `optional` od `isRequired`. Wynik: 8 zaliczonych.
- Pozycja 4 decyzji (kod wywołujący): `createControl` nie ma wywołań w kodzie, więc nic nie zakłada starych znaczeń `arg2` i `arg3` (obserwacja 93).

**Dokumentacja (`docusaurus-hgdb`, `main`, wersja en i pl):**

| # | Zmiana |
|---|---|
| 1 | Sekcja `updateable` z wartościami `Updatable`; wiersze `TypeParam.updateable` i `SubType.updateable` |
| 2 | `recomendedLabel` (pisownia z kodu, API i bazy) |
| 3 | Rozdzielone wiersze `mimeType` i `knownLobMetadata` (w en; w pl były rozdzielone) |
| 4 | Pierwszeństwo `arg4`/`arg5` nad `ParamDefinition.knownLobMetadata`/`mimeType` przy odczycie sprawy |
| 5 | Pole `versionMinor` w `TypeCase` |
| 6 | `NUMBER`: walidacja liczby zmiennoprzecinkowej |
| 7 | Jedna konwencja `arg1..arg3` dla list wyboru i STRING (zgodna z kodem po poprawce) |
| 8 | Tabela wartości domyślnych `arg1..arg5` według `AttributeType` (z `HtmlArguments`) |
| 9 | Sekcja „Localization of labels and option names” (klucze `${...}`, język, co tłumaczy serwer) |
| 10 | `isRequired`: serwer nie sprawdza wartości przy zapisie sprawy |

**Pozostało:** dokumentacja z 119 (parametry `lucene.properties`, `truncated`/`totalHits`, błędy `L0009.7` i `L0009.8`), `npm run build` serwisu, oznaczenie obserwacji 23 i 24 ✅ (zrobione), obserwacje 93–97 dopisane do `docs/obserwacje.md`.

## Domknięcie (2026-10-27)

Dokumentacja z 119 dopisana (en i pl, `docusaurus-hgdb`, `main`, bez commitu):

- `004_API/005_PagedResult`: sekcje `truncated` i `totalHits` (pola DTO pojawiają się tylko przy obciętym wyniku; `MrcPagedResult` ich nie zawiera).
- `003_Architecture/003_Index_Lucene`: sekcja „Parametry konfiguracji Lucene na serwerze (`lucene.properties`)” (gdzie ustawiać, pierwszeństwo, parametry nowe i istniejące, przykłady, wskazówki zapytań).
- `004_API/008_Search_services/002_CaseSearch` i `003_CaseSearchExt` (`sarchByQuery`): notatka o błędach sortowania `L0009.7` i `L0009.8` przy parametrze `sortClause`.

`npm run build` serwisu: `[SUCCESS]` dla wersji domyślnej i `pl`, bez ostrzeżeń i błędów w logu.

Definicja Gotowości: pozycje 1–10 w en i pl (zrobione), decyzja do pozycji 7 zapisana i wykonana, build bez nowych ostrzeżeń (zrobione), obserwacje 23 i 24 ✅ (zrobione). Do zamknięcia zadania zostają commity i PR (`mercury` na `hgdb-190`).
