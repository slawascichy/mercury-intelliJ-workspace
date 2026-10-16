# Obserwacje z analizy i kandydaci do udoskonaleń

Spostrzeżenia z przeglądu struktury repozytoriów, POM-ów i dokumentacji. Nie są to
zweryfikowane błędy, tylko miejsca do sprawdzenia.

## Struktura modułów

| # | Repozytorium | Obserwacja | Propozycja |
|---|---|---|---|
| 1 | mercury-client | `mercury-client-cmd` i `mercury-data` nie są wymienione w `<modules>` projektu nadrzędnego. Reaktor ich nie buduje. | ✅ `mercury-client-cmd` zaimportowano w IntelliJ jako osobny projekt Maven. `mercury-data`: patrz pkt 3. |
| 2 | mercury-client | `mercury-client-cmd` dziedziczy po `mercury-client:3.20.8-SNAPSHOT`, a bieżący rodzic ma wersję `3.0.8.6-SNAPSHOT`. Maven pobiera więc starą kopię rodzica z `repo/io/hgdb/ibmbpm/mercury-client/3.20.8-SNAPSHOT`. Stamtąd pochodzi np. `hgdb-client.version`, której bieżący `pom.xml` nie definiuje. Zmiany w bieżącym rodzicu nie wpływają na moduł. | Ustawić rodzica na bieżącą wersję i dodać brakujące właściwości. Można też zrezygnować z dziedziczenia i zdefiniować wersje w module. |
| 2a | mercury-client | W `pom.xml` są niezatwierdzone zmiany: usunięto wpis `<module>mercury-ws-client-cxf</module>` i pliki `.project`, `.gitignore` tego modułu. | Zatwierdzić zmianę. Wygląda na to, że jego rolę przejął `hgdb-ws-client-cxf` z `hgdb-client-open`. |
| 2b | workspace | `.idea/misc.xml` importuje `mercury-cmd/mercury-install-package/pom.xml` osobno, choć moduł jest już w reaktorze `mercury-cmd`. | Usunąć osobny import, chyba że jest celowy. |
| 3 | mercury-client | `mercury-data` zawiera tylko szablon „Hello world” i zależy od nieistniejącego artefaktu `mercury-ws-client-cxf` (obecnie `hgdb-ws-client-cxf`). | Usunąć moduł. |
| 4 | mercury-cmd | W `mercury-benchmark` cały kod jest w `src/test`, a `src/main` zawiera tylko szablon `App.java`. | Przenieść benchmark do `src/main` albo usunąć `App.java`. |
| 5 | mercury-cmd | `mercury-install-package` przechowuje w git Tomcat 8.5.14, instalatory JDK 8 i zbudowane pakiety ZIP (`bin/`, `releases/`). | Pobierać zależności w czasie budowania, a pakiety publikować w repozytorium artefaktów. |

## Wersje i zależności

| # | Repozytorium | Obserwacja | Propozycja |
|---|---|---|---|
| 6 | mercury-cmd, mercury-server | Pakiet instalacyjny zawiera Tomcat 8.5.14, a testowy serwer `mercury-server` Tomcat 8.0.32. Obie wersje nie są już wspierane. | Ujednolicić i zaktualizować wersję Tomcata. |
| 7 | mercury-cmd | Projekt zależy od wydanych wersji (`mercury.static.version=3.0.3.2.12`, `hgdb-client.version=3.1.2.0.2`), a nie od bieżących snapshotów w workspace (`3.0.4.x`, `3.1.4-SNAPSHOT`). | Zdecydować, czy narzędzia mają nadążać za bieżącą wersją serwera. |
| 8 | mercury-cmd | Właściwość `junit.version` jest zdefiniowana dwa razy (4.13.1 i 4.7). Obowiązuje ostatnia. | Usunąć duplikat. |
| 9 | hgdb-client-open | Publiczny klient `hgdb-ws-client-cxf` zależy w zakresie `compile` od `pro.ibpm:tw4j` (biblioteka dla IBM BPM). | Sprawdzić, czy zależność jest potrzebna. Jeśli tak, oznaczyć ją jako `optional` lub `provided`. |
| 10 | wszystkie | Wersje Springa (2.5.6 – 5.3.21), CXF (2.7.15 – 3.0.12), Ehcache (2.10.1 / 3.6.1) i log4j (1.2.14 / 2.17.2) różnią się między repozytoriami. log4j 1.x nie jest wspierany. | Wspólny BOM wersji zależności. |

## Dokumentacja i opisy

| # | Repozytorium | Obserwacja | Propozycja |
|---|---|---|---|
| 11 | mercury-client | README wymaga Javy 1.6 / 1.7 i Maven 2.2.1, a POM kompiluje z `java.version=1.8`. | Zaktualizować README albo POM. (`architektura.md` już opisuje obie wartości.) |
| 12 | hgdb-client-open | Nazwa i opis w POM (`Mercury Client`, „integracje z IBM BPM”) są skopiowane z `mercury-client`. | Nadać własną nazwę i opis. |
| 13 | mercury-client | README wskazuje plik testowy w nieistniejącym module `mercury-ws-client-cxf`. | Poprawić ścieżkę. |
| 14 | mercury-cmd | Brak README i opisu budowania. `documents/README.txt` zawiera tylko zdanie „Tutaj będziemy trzymać dokumenty”. | Dodać README z opisem poleceń i budowania pakietu. |
| 15 | wszystkie | Właściwość `databse.provider` ma literówkę, zachowaną celowo dla zgodności. | Przy najbliższej zmianie wersji głównej wprowadzić `database.provider` z aliasem. |

## Serwis dokumentacji (docusaurus-hgdb)

| # | Obserwacja | Propozycja |
|---|---|---|
| 16 | `README.md` opisuje budowanie przez `yarn`, ale projekt ma `package-lock.json` (npm) i nie ma `yarn.lock`. | Ujednolicić instrukcję i menedżer pakietów. |
| 17 | `package.json` ma nazwę `template` i wersję `0.0.0`, pozostałe z szablonu Docusaurusa. | Zmienić na `docusaurus-hgdb`. |
| 18 | `@docusaurus/plugin-google-gtag` jest w zależnościach, ale nie jest skonfigurowany w `docusaurus.config.js`. `@docusaurus/theme-classic` ma wersję `^3.8.0`, reszta pakietów `^3.8.1`. | Usunąć nieużywany pakiet albo go skonfigurować. Wyrównać wersje. |
| 19 | `onBrokenLinks` i `onBrokenMarkdownLinks` mają wartość `warn`, więc uszkodzone linki nie przerywają budowania. | Po uporządkowaniu linków przełączyć na `throw`. |
| 20 | Nawigacja i stopka kierują do prywatnego repozytorium `github.com/slawascichy/hgdb` (🔒), niedostępnego dla czytelników. | Wskazać publiczne repozytoria (`hgdb-client-open`, `mercury-docker`) albo usunąć link. |
| 21 | Część tematów z TODO jest opisana tylko w kodzie: konfiguracja (`mercury-install-package/src/main/config`), integracja z IBM BAW (`mercury-bpm`, `mercury-client-cmd`), polecenia CLI (`mercury-srv-cmd`). | Wykorzystać opisy z `docs/moduly/` jako materiał do artykułów. |
| 22 | Artykuły o Docker i Kubernetes czekają na nową wersję obrazów. `mercury-docker` jest na wersji `3.0.3.2.11`, a serwer na `3.0.4.1`. | Zaktualizować obrazy razem z artykułami. |
| 23 | `docs/003_Architecture/001_Cases_MetaData/index.mdx` różni się od kodu: (a) `TypeParam.updateable` opisano jako wartość z domyślnym `true`, a w kodzie to enum `Updatable` (`READWRITE`, `READONLY`, `ONCREATE`, `ONCREATEVISIBLE`, `OTHER`), domyślnie `READWRITE`; (b) pole nazywa się w kodzie `recomendedLabel`, a w dokumentacji `recommendedLabel`; (c) w tabeli `ParamDefinition` wiersze `mimeType` i `knownLobMetadata` są sklejone w jedną linię; (d) brak opisu, że `arg4`/`arg5` nadpisują `knownLobMetadata`/`mimeType` przy odczycie (`CaseBusiness.java:1188-1195`); (e) `TypeCase` nie opisuje `versionMinor`; (f) `HtmlSupportedControl.NUMBER` ma opis „integer format validation”. | Poprawić stronę (także `i18n/pl`). Zadanie: `tasks/hgdb/XXX-Dokumentacja-metadane-typow`. |
| 24 | Znaczenie `arg*` dla list wyboru jest niespójne. Dokumentacja, `HtmlArguments` (wartości domyślne), parser wartości, indeks Lucene i eksport POI: `arg1` = wartość/nazwa, `arg2` = `size`, `arg3` = para `value\|name`. Generator formularzy `HtmlControlUtils.prepareSelectControl` (`mercury-ws-app`): `arg2` = `optional`, `arg3` = `size`, `arg4` = `useNameAndValue`. Dla STRING `HtmlControlUtils` czyta typ inputu z `arg2` (dokumentacja: `arg1`). | Ujednolicić `HtmlControlUtils` z dokumentacją albo opisać różnicę. Przy zmianie uważać na istniejące definicje typów w bazach klientów. Zadanie: `tasks/hgdb/XXX-Dokumentacja-metadane-typow`. |
