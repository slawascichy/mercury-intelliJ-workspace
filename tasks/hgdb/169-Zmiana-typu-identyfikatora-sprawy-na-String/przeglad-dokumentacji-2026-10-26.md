# [169] Przegląd dokumentacji 2026-10-26: identyfikator sprawy jako `String`

Zakres: `docusaurus-hgdb` (`docs/` po angielsku, `i18n/pl/.../current/` po polsku; pominięto `.history/`, `node_modules/`, `build/`) oraz klucze `openapi-docs_*` w `mercury`. Metoda: `grep` po `caseId`, `rootVersionId`,
`previousVersionId`, `subCaseId`, `parentCaseId` z typem lub przykładem liczbowym, z odczytem kontekstu. Niczego nie zmieniano (repozytorium `docusaurus-hgdb` jest na gałęzi `hgdb-109`, czyste).

**Wniosek:** w dokumentacji użytkownika zostały opisy i przykłady z liczbowym identyfikatorem sprawy. Klucze OpenAPI są w porządku.

## Klucze `openapi-docs_*` (bez zmian)

W `mercury-ws-app`, `mercury-ws-app-rest-generator` i `mercury-lucene-indexes-api` nie ma opisu `caseId` jako liczby. Wystąpienia „number” dotyczą `bpmProcessId` (numer procesu BPM, zostaje `Long`),
`ktmNumber` i kolumn `NUMBER` w opisie `CaseDocument`. Typ w specyfikacji OpenAPI bierze się z klas Java, więc po zmianie 169 jest `string` automatycznie.
Do potwierdzenia po wygenerowaniu `openapi-doc-report.txt` (generator w `mercury-ws-app-rest-generator` kończył się wcześniej błędem `MercuryException`; nie badano).

## `docusaurus-hgdb`: do poprawy (po angielsku w `docs/` i po polsku w `i18n/pl/`, razem 12 plików)

Format identyfikatora: `TYP.numer` (np. `Faktura.118906`; `CaseHelper.createCaseId`). Przykłady wystarczy przepisać na tekst w cudzysłowie.

| Plik (ścieżka od `docs/`) | Co poprawić |
|---|---|
| `004_API/002_CaseHeader/index.mdx` | Tabela pól: `caseId` ma typ `Long`/`Integer`, ma być `String`/`String`. Ta sama tabela: `previousVersionId` i `rootVersionId` (to też identyfikatory spraw) |
| `004_API/008_Search_services/002_CaseSearch.mdx` | Tabela `CaseNarrative`: `caseId` ma typ `Long` i błędny opis „Application name” (do poprawienia na „Identyfikator sprawy”), `rootVersionId` ma typ `Long`. Przykład JSON: `"caseId": 999998`, `"rootVersionId": 2337904` |
| `004_API/008_Search_services/003_CaseSearchExt/index.mdx` | 18 liczbowych przykładów `caseId` i 9 `rootVersionId`/`previousVersionId` w odpowiedziach JSON |
| `004_API/004_Universal_objects.mdx` | 4 przykłady (`"caseId": 835495`, `<caseId>808289</caseId>`, `<caseId>808300</caseId>` i pokrewne) |
| `004_API/003_Case_as_ANY_type.mdx` | 3 przykłady (`<caseId type="Integer">5012</caseId>`, `"caseId": 783695`) |
| `003_Architecture/002_Cases_Versioning/index.mdx` | `<caseId type="Integer">118906</caseId>` w opisie wersjonowania (3 miejsca) |

Do przejrzenia bez gwarancji problemu: `003_Architecture/003_Index_Lucene/index.mdx` (wspomina `caseId`; nie znalazłem typu liczbowego).
Nie dotyczy: opisy `id` typu, podtypu, akcji i powiązania roli (`Long`; to identyfikatory metadanych, nie spraw) w `001_Cases_MetaData` i `004_Permissions_mechanism`.

## Propozycja

1. Poprawki zrobić na gałęzi `hgdb-169` w `docusaurus-hgdb` (z `master`; obecnie checkout to `hgdb-109`). Zakres: 6 plików × 2 języki.
2. Alternatywa: dołączyć do zadania 190 (dokumentacja metadanych), które i tak dotyka `docs/004_API`. Wtedy 169 zamykamy bez zmian w dokumentacji i z odsyłaczem do 190.
3. Pozostałe języki dokumentacji nie istnieją (`i18n` ma tylko `en` i `pl`), więc translator Gemini nie jest potrzebny.

## Wykonanie (2026-10-26, `docusaurus-hgdb`, gałąź `main`, bez commitu)

Autor zdecydował o poprawkach w głównej gałęzi (`main`). Lokalna gałąź `hgdb-109` wskazywała ten sam commit co `main` (`4f2fb73`) i została usunięta na polecenie autora.

- Zmienione pliki: 12 (6 w `docs/`, 6 w `i18n/pl/docusaurus-plugin-content-docs/current/`), 80 linii.
- Przykłady JSON i XML: identyfikator ma postać `TYP.numer`, gdzie `TYP` to kod typu z tego samego przykładu (np. `"Month.808300"`, `<caseId type="String">TestSimpleDictionary.118906</caseId>`).
  Dotyczy `caseId`, `rootVersionId` i `previousVersionId`.
- Tabele typów: `caseId`, `piervousVersionId`, `rootVersionId` (`CaseHeader`) oraz `caseId`, `rootVersionId` (`CaseSearch`, `CaseNarrative`) mają typ `String`. Opis `caseId` w `CaseSearch` zmieniono z „Application name” na „Case identifier” (pl: „Identyfikator sprawy”).
- Bez zmian: `groupId`, `typeId`, `storeId`, `bpmProcessId` (`Long`/`Integer`; to identyfikatory metadanych i BPM).
- **Nie zmieniono:** `003_Architecture/002_Cases_Versioning` linia 54 (pl: 57), zapytanie `mrc_rootVersionId:118904` ze zrzutem ekranu. Nie sprawdzono, jak pole `rootVersionId` jest indeksowane w Lucene, więc nie wiadomo, jak poprawnie zapisać wartość tekstową w zapytaniu. Zrzut `image2020-9-14_10-36-13.png` też pokazuje stare zapytanie.
- Literówka `piervousVersionId` w tabeli `CaseHeader` (nazwa pola w nagłówku to `previousVersionId`) pozostała bez zmian.
- Nie uruchamiano budowy Docusaurusa.
