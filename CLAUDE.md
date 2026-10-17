# CLAUDE.md

Wskazówki dla Claude Code w pracy z tym repozytorium.

## Czym jest to repozytorium

Workspace IntelliJ IDEA dla systemu **Mercury DB (HgDB)**: serwera usług SOAP/REST/RMI do
zarządzania obiektami („sprawami”) na relacyjnej bazie SQL z indeksami Apache Lucene.

To repozytorium **nie zawiera kodu źródłowego**. Zawiera tylko:

- konfigurację `.idea/`, która spina sąsiednie repozytoria git w jeden projekt,
- dokumentację analizy w `README.md` i `docs/`.

Kod leży w sąsiednich repozytoriach. Ścieżki są względne do tego katalogu
(`D:\workspace\git\mercury-intelliJ-workspace`):

| Repozytorium | Ścieżka | Rola | Opis |
|---|---|---|---|
| mercury-lib | `../mercury-lib` | Biblioteki współdzielone: encje, API, DTO | `docs/moduly/mercury-lib.md` |
| mercury | `../mercury` | Serwer: DAO, Lucene, logika, WS, aplikacje WAR | `docs/moduly/mercury.md` |
| hgdb-client-open | `../hgdb-client-open` | Publiczny klient Java (CXF, multi-instancja) | `docs/moduly/hgdb-client-open.md` |
| mercury-client | `../mercury-client` | Biblioteki dla IBM BPM | `docs/moduly/mercury-client.md` |
| mercury-cmd | `../mercury-cmd` | Narzędzia CLI, transfer, pakiet instalacyjny | `docs/moduly/mercury-cmd.md` |
| mercury-docker | `../mercury-docker` | Obrazy Docker, kompozycje, Helm | `docs/moduly/mercury-docker.md` |
| docusaurus-hgdb | `../scisoftware-webpage/docusaurus-hgdb` | Serwis hgdb.org (submoduł git) | `docs/moduly/docusaurus-hgdb.md` |

Zanim zaczniesz analizę, przeczytaj `README.md` i `docs/architektura.md`. Zawierają mapę
modułów, zależności i kolejność budowania. Opisy w `docs/moduly/` są aktualne na dzień
ich utworzenia. Przed oparciem się na nich sprawdź w POM-ach, czy stan się nie zmienił.

## Zasady pracy

- **Nie modyfikuj sąsiednich repozytoriów bez wyraźnej prośby.** Domyślnie tylko je czytaj,
  a zmiany wprowadzaj w tym repozytorium (dokumentacja, `.idea/`).
- Nie commituj bez prośby. Domyślna gałąź: `main`. Lokalnie pracuje się na `master`.
- Pliki `.idea/*.xml` zmienia też IntelliJ. Nie nadpisuj ich bez sprawdzenia, co jest
  w nich obecnie.
- W sąsiednich repozytoriach pomijaj katalogi `target/`, `repo/` (lokalne repozytoria Maven),
  `node_modules/`, `.history/`, a także rozpakowane serwery w `mercury/mercury-server`
  i `mercury-cmd/mercury-install-package/bin`. Zawierają one tysiące obcych plików.
- Powłoka to PowerShell 5.1 na Windows. Pliki są w UTF-8, więc przy czytaniu ustaw
  `[Console]::OutputEncoding=[Text.Encoding]::UTF8` i `Get-Content -Encoding UTF8`.

## Dokumentacja – konwencje

- Język polski, krótkie zdania, strona czynna.
- Struktura pliku modułu (`docs/moduly/<repo>.md`): tabela metadanych (lokalizacja, GAV,
  Java, opis z POM), tabela modułów (moduł, nazwa, pliki Java main/test, pakiety, opis),
  diagram `mermaid` zależności, stos technologiczny, budowanie, na końcu linia `Źródło: …`.
- Moduły spoza reaktora Maven oznaczaj ⚠️.
- Spostrzeżenia i propozycje zmian dopisuj do `docs/obserwacje.md` z kolejnym numerem.
  Zrealizowane oznaczaj ✅, zamiast je usuwać.
- Po dodaniu pliku w `docs/` dodaj link w `README.md` (tabela repozytoriów i sekcja „Dokumentacja”).
- Opisuj tylko to, co da się zweryfikować w POM-ach, kodzie lub README. Wnioski
  niepotwierdzone oznaczaj jako przypuszczenie.

## Budowanie (skrót)

Kolejność: `mercury-lib` → `mercury` → `hgdb-client-open` → `mercury-client` / `mercury-cmd`.

```bash
# mercury-lib
mvn clean install -Dmercury.static.version=<wersja> -Ddatabse.provider=POSTGRESQL -Dmaven.test.skip
# mercury
mvn -U clean install -Dmaven.test.skip=true
# hgdb-client-open
mvn --global-settings repo/settings.xml --settings maven/<user>/settings.xml clean install -Dmaven.test.skip
# docusaurus-hgdb
npm install && npm start
```

Pułapki:

- Właściwość `databse.provider` ma literówkę, zachowaną celowo. Wartości: `POSTGRESQL`
  (domyślna), `ORACLE`, `MYSQL`, `MSSQL`, `HSQL`. Od niej zależy wersja artefaktów encji.
- Każde repozytorium ma własne lokalne repozytorium Maven `<repo>/repo`. Artefakty
  przenosi się między projektami skryptami `install.sh` / `deploy.sh` / `deploy-api.sh`.
- `mercury-client` wymaga chronionych licencją bibliotek IBM BPM/WebSphere. Nie da się go
  zbudować bez lokalnego repozytorium IBM.
- `mercury-client-cmd` buduje się osobno. Jego rodzic (`3.20.8-SNAPSHOT`) pochodzi
  z `mercury-client/repo`, a nie z `../pom.xml`.
- `mercury-cmd` zależy od wydanych wersji (`3.0.3.2.12`, klient `3.1.2.0.2`), a nie od
  bieżących snapshotów.
- Testy klientów i narzędzi wymagają działającego serwera Mercury DB
  (`src/test/resources-filtered/properties/<user>/test.properties`).
- Testy mają profile użytkowników w `src/test/resources*/properties/<nazwa_użytkownika>`.
  Nazwa pochodzi z właściwości Maven `user` (profil `sci-maven` w `~/.m2/settings.xml`).
  Tu to **`scichy`**. Plik `<user>/test.properties` jest w `.gitignore`, więc istnieje tylko
  lokalnie. Bez katalogu użytkownika testy korzystające z `TstProperties` nie ruszą.
- `mercury-lib`: testy nie wymagają bazy ani serwera. Bazowy `mvn test` (Oracle JDK
  1.8.0_202, `-Ddatabse.provider=POSTGRESQL`) przechodzi do `mercury-ws-dto-api`, gdzie
  3 z 4 testów kończy się błędem (stan z 2026-10-17, gałąź `hgdb-133`).
- `mvn` działa w bashu Cygwin (`D:\cygwin\bin\bash.exe`). Jest też `mvnibm` (Java IBM).

## Kontekst

Autor: Sławomir Cichy (Sci Software). Wersję komercyjną dystrybuuje IBPM S.A.
Biblioteki autora używane w projektach (`sccommon`, `ccrto-openapi`, `poi-toolkit`) leżą
w `D:\workspace\git`, ale nie należą do workspace.
