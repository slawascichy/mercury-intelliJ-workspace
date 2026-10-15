# docusaurus-hgdb – serwis hgdb.org

| | |
|---|---|
| Lokalizacja | `D:\workspace\git\scisoftware-webpage\docusaurus-hgdb` |
| Typ | Projekt Node.js (Docusaurus 3.8). Moduł IntelliJ `docusaurus-hgdb.iml`, nie jest projektem Maven |
| Repozytorium | `github.com/SciSoftwareSlawomirCichy/docusaurus-hgdb`, submoduł `scisoftware-webpage` |
| Adres | [https://hgdb.org](https://hgdb.org) |
| Node.js | ≥ 18.0 |

Publiczny serwis produktu Mercury DB (HgDB) 3.0: dokumentacja dla użytkowników
i programistów, artykuły wsparcia technicznego i blog. Repozytorium `scisoftware-webpage`
zawiera jeszcze dwa inne serwisy jako submoduły: `docusaurus-scisoftware` i `docusaurus-slawas`.
Nie należą one do tego workspace.

## Struktura

| Katalog | Sekcja serwisu | Zawartość |
|---|---|---|
| `docs/` | Documentation (`/docs`) | Dokumentacja produktu, opis w tabeli niżej |
| `tech/` | Technical Support (`/tech`) | Osobna instancja `plugin-content-docs` (`id: tech`) |
| `blog/` | Blog (`/blog`) | Wpis powitalny `2025-05-25-Welcome.mdx` |
| `i18n/pl/` | – | Polskie tłumaczenia `docs`, `tech`, bloga i motywu |
| `i18n/en/` | – | Etykiety motywu. Treść angielska leży w `docs/` i `tech/`, bo angielski jest językiem domyślnym |
| `src/` | Strona główna | `pages/index.js`, komponent `HomepageFeatures`, style |
| `static/` | – | Obrazy i pliki statyczne |

Każdy z katalogów `docs/`, `tech/`, `blog/` ma własne `authors.yml`, `tags.yml` i `_functions.js`
z komponentami MDX (`ProjectStatus`, `SonarcloudProject`, `YouTube`).

### Dokumentacja (`docs/`)

| Rozdział | Artykuły | Powiązane moduły |
|---|---|---|
| `001_intro` | Wprowadzenie do Mercury DB (HgDB) 3.0 | – |
| `002_Case_vs_Object` | Sprawa a obiekt | `mercury-core`, `mercury-entities` |
| `003_Architecture` | Metadane spraw, wersjonowanie spraw, indeks Lucene, mechanizm uprawnień | `mercury-dao`, `mercury-lucene-indexes`, `mercury-srv` |
| `004_API` | Kontekst żądania SOAP/REST, nagłówek sprawy (`CaseHeader`), ładowanie metadanych (`TypeCase`, `TypeCode`, `TypeKind`), sprawa jako typ ANY, obiekty uniwersalne (`MrcObject`), `PagedResult`, test połączenia (Echo), zapis sprawy, wyszukiwanie (zapytania Lucene, `CaseSearch`, `CaseSearchExt`, `CaseIndexerFieldsManager`, przykłady agregacji), komentarze, szybkie zadania | `mercury-ws-server-api`, `mercury-ws-dto-api`, `mercury-ws-app` |
| `005_Configuration` | Parametry konfiguracyjne Mercury DB | `mercury-server`, `mercury-install-package` |
| `006_IBM_BAW_Integration` | Integracja z IBM BAW, klient Mercury BPM | `mercury-client` (`mercury-bpm`) |

### Wsparcie techniczne (`tech/`)

| Rozdział | Zawartość |
|---|---|
| `intro.md` | Wstęp i kontakt (`info@scisoftware.pl`) |
| `001_Mercury_version` | Wersje Mercury DB |
| `002_ErrorCode` | Znaczenie pola `errorCode` i opisy błędów: `FI001`, `L0001`, `L0002`, `M0001`, `M0006`, `MC007`, `ML001`, `SC001` |

## Konfiguracja (`docusaurus.config.js`)

- Języki: `en` (domyślny), `pl`.
- Wyszukiwarka: Typesense (`docusaurus-theme-search-typesense`, kolekcja `hgdb-org-01`).
- Powiększanie obrazów: `docusaurus-plugin-image-zoom`. Pakiet `@docusaurus/plugin-google-gtag`
  jest w zależnościach, ale nie jest skonfigurowany.
- Włączone `future.v4` i `experimental_faster` (`@docusaurus/faster`).
- Uszkodzone linki generują ostrzeżenie, nie przerywają budowania (`onBrokenLinks: 'warn'`).
- Nawigacja prowadzi do prywatnego repozytorium `github.com/slawascichy/hgdb` (🔒) i forum Disqus.

## Budowanie

```bash
npm install          # README podaje yarn, ale projekt ma package-lock.json
npm start            # serwer deweloperski z podglądem na żywo
npm run build        # statyczny serwis w build/
npm run serve        # podgląd zbudowanej wersji
npm run write-translations -- --locale pl   # aktualizacja plików tłumaczeń
```

Wdrożenie: `npm run deploy` (`docusaurus deploy`, z `USE_SSH=true` albo `GIT_USER=<user>`).

## Stan prac

`README.md` zawiera listę TODO:

- artykuły do napisania: komentarze, szybkie zadania, konfiguracja, integracja z IBM BAW,
  część artykułów o ładowaniu metadanych, `CaseIndexerFieldsManager` (po rozwiązaniu #180),
- nowa wersja obrazów i kompozycji Docker oraz artykuły o Docker i Kubernetes,
- aktualizacja Docusaurusa do najnowszej wersji.

Tłumaczenie artykułów API na angielski jest zakończone.

Źródło: `docusaurus-hgdb/README.md`, `docusaurus.config.js`, `package.json`.
