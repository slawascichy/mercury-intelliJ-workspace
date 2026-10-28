# Analiza wersji w `mercury-cmd` (2026-10-28)

Analiza tylko do odczytu na prośbę autora: czy wersje zależności i pakietu instalacyjnego są ustawiane poprawnie, wraz z `mercury-install-package/src/main/build/build-installation.xml`. Stan: `mercury-cmd` na gałęzi `hgdb-058`, główny `pom.xml` z niezatwierdzoną zmianą autora (`mercury.static.version` = 3.0.4.10, komentarz „To jest wersja serwera, nie lib”). Analiza z punktów 1–5 poprzedziła zmiany opisane w sekcji 6.

## 1. Trzy rodziny wersji i ich właściwości

| Rodzina | Artefakty w zależnościach `mercury-cmd` | Wersja | Właściwość | Ocena |
|---|---|---|---|---|
| `mercury-lib` | `mercury-core`, `mercury-entities` (z prefiksem bazy), `mercury-srv-api`, `mercury-ws-dto-api`, `mercury-ws-server-api`, `mercury-spring-remoting` (9 deklaracji: 6 w głównym POM-ie, 3 w `mercury-srv-cmd`) | 3.0.4.18 | **`mercury.static.version`** | **błąd**: właściwość ma wartość 3.0.4.10 |
| `mercury` (serwer) | `mercury-core-server`, `mercury-entities-ids`, `mercury-ws-server-api20`, `mercury-dao-api`, `mercury-cmis-client`, `mercury-lucene-indexes(-api)`, `mercury-dao`, `mercury-srv`, `mercury-ws-server` (10 deklaracji, tylko `mercury-srv-cmd`); w Ant: jar `mercury-ws-server-api20` i trzy WAR-y | 3.0.4.10 | `mercury.server.project.version` (tylko w `mercury-srv-cmd`) i `mercury.static.version` (Ant) | poprawne |
| klient (`hgdb-client-open`) | `hgdb-ws-client-cxf`, `hgdb-multi-client`, `hgdb-client-mock` (benchmark, `mercury-srv-cmd`, `mercury-transfer`); w Ant jary do `libExt` | 3.1.4.19 | `hgdb-client.version` (POM-y) i `hgdb.client.version.release` (Ant, `mercury-install-package`) | poprawne, ale dwie właściwości |
| własna | `mercury-srv-cmd`, `mercury-transfer` (zależności między modułami), parent | 3.1.4-SNAPSHOT | `${project.version}` | poprawne |

Klasyfikacja artefaktów wg modułów POM-ów w `mercury-lib` (7 artefaktów), `mercury` (21) i `hgdb-client-open` (3).

## 2. Problem główny: `mercury.static.version` ma dwa znaczenia

`mercury.static.version` jest używana jako:

- **(a) wersja bibliotek `mercury-lib`** w 9 deklaracjach zależności (patrz tabela),
- **(b) wersja produktu/serwera** w nazwach: `finalName` jarów `mercury-srv-cmd` i `mercury-transfer` (`<artifactId>-<wersja>`), katalog pakietu `releases/mercury-install-package-<wersja>`, nazwa archiwum, `project_version` w Ant oraz **ścieżka jaru `lib20`**: `mercury/repo/io/hgdb/mercury/mercury-ws-server-api20/${mercury_static_version}` (w repozytorium `mercury/repo` jest tylko 3.0.4.10 i 3.0.4-SNAPSHOT).

Wartość 3.0.4.18 (poprzednia) była poprawna dla (a), a błędna dla (b). Wartość 3.0.4.10 (Twoja zmiana) jest poprawna dla (b), a błędna dla (a). Dowody:

- **Ostatnie budowanie pakietu** (`releases/mercury-install-package-3.0.4.18`, dziś 00:20–00:25, przy `mercury.static.version` = 3.0.4.18) zatrzymało się w połowie: `libExt` ma tylko dwa jary CLI (`mercury-srv-cmd-3.0.4.18.jar`, `mercury-transfer-3.0.4.18.jar`), bez `hgdb-ws-client-cxf`, `hgdb-multi-client`, `fscontext`, `providerutil`; `lib20` jest pusty; nie ma pliku `.zip`. Przyczyna to przypuszczenie z objawów: katalog `mercury-ws-server-api20/3.0.4.18` nie istnieje, więc kopiowanie `lib20` w Ant kończy się błędem (komunikatu Anta nie widziałem).
- **Przy 3.0.4.10** `mvn -o clean test-compile` przechodzi, ale kompiluje się na starych bibliotekach `mercury-lib` 3.0.4.10 z 2026-10-23 (`mercury-core-3.0.4.10.jar` ma 2 odwołania do `org/apache/log4j`; `mercury-core-3.0.4.18.jar` ma 0). API `ICaseBusiness` (`saveList` z `Set<TypeCode>`) jest w obu takie samo, więc błąd nie zostaje wykryty przy kompilacji. Pakiet i tak dostaje jary bibliotek 3.0.4.18, bo Ant kopiuje je z `apache-tomcat/mercury/lib` (punkt 3).

## 3. Skąd naprawdę pochodzą pliki pakietu (`build-installation.xml`)

| Część pakietu | Źródło w Ant | Wersja zależy od |
|---|---|---|
| `libExt`: `mercury-srv-cmd`, `mercury-transfer` | `maven-jar-plugin` w modułach, `outputDirectory` = `releases/mercury-install-package-${mercury.static.version}/libExt` | `mercury.static.version` (nazwa jaru i katalogu muszą być zgodne w trzech POM-ach) |
| `libExt`: `hgdb-ws-client-cxf`, `hgdb-multi-client` | `hgdb-client-open/repo/io/hgdb/mercury/<artefakt>/${hgdb.client.version.release}` (3.1.4.19 jest w tym repozytorium) | `hgdb.client.version.release` |
| `libExt`: `fscontext`, `providerutil` | `mercury-install-package/libExt/*` (w git) | stałe |
| `lib` | **cały katalog** `${CATALINA_HOME}/mercury/lib/*` (serwer dev, utrzymywany ręcznie) | stan dysku, nie właściwość: dziś 6 jarów `mercury-lib` 3.0.4.18, `sccommon-*` 2.0.0.1, Logback, `poi-toolkit` 4.1.0.1, `ccrto-openapi` 2.0.0.1 |
| `lib20` | `mercury/repo/.../mercury-ws-server-api20/${mercury_static_version}` | `mercury.static.version` (musi być wersją serwera) |
| `installableApps`: `ROOT.war`, `mercury-ws-app.war`, `mercury-gui-registry.war` | `mercury/<moduł>/target/*.war` | stan dysku (ostatni build w `mercury`); dziś `mercury-ws-app.war` jest identyczny z `mercury/mercury-ws-app/target` i ma `info.version` 3.0.4.10 |
| `classes`, `config`, `jdbcdrivers` | `${CATALINA_HOME}/mercury/classes`, `.../IBPM/mercury/config`, `.../jdbcdrivers` + `src/main/config` | stan dysku |

Wniosek: wersje `lib`, WAR-ów, `classes` i `config` są **zgodne tylko wtedy, gdy serwer dev i katalogi `target` w `mercury` odpowiadają wydaniu** (dziś odpowiadają). Żadna właściwość tego nie wymusza.

## 4. Drobne rozbieżności

1. **Dwie właściwości dla klienta:** `hgdb-client.version` (root) i `hgdb.client.version.release` (`mercury-install-package`) mają tę samą wartość; po każdym wydaniu klienta trzeba je podbić osobno.
2. **Dwie właściwości dla serwera:** `mercury.static.version` (root) i `mercury.server.project.version` (`mercury-srv-cmd`), obie 3.0.4.10.
3. **Skrypty `bin/mercury-cmd.sh` i `mercury-transfer.sh`:** `MERCURY_VERSION=3.0.1.0.2` i `MERCURY_HOME` wskazujący `.../releases/mercury-install-package-3.0.1.0.2` na sztywno (bez `${}`, więc filtrowanie Mavena ich nie podmienia). Skrypt robi `cd $MERCURY_HOME/bin`, więc po instalacji wymaga ręcznej poprawki. Rozbieżność niezależna od migracji logowania.
4. **Nazwy:** pakiet i jary nazywają się wg `mercury.static.version` (3.0.4.10), a moduły mają wersję 3.1.4-SNAPSHOT. Jest to zgodne z komentarzem autora (wersja produktu = wersja serwera).

## 5. Propozycja (do akceptacji; nic nie zmieniono)

1. Dodać w głównym POM-ie **`mercury.lib.version`** = 3.0.4.18 i użyć jej w 9 deklaracjach bibliotek `mercury-lib` (6 w głównym POM-ie, 3 w `mercury-srv-cmd`).
2. **`mercury.static.version`** zostaje wersją serwera/produktu (3.0.4.10) dla nazw i ścieżki `lib20`; `mercury.server.project.version` w `mercury-srv-cmd` ustawić na `${mercury.static.version}` (jedno miejsce dla serwera).
3. `hgdb.client.version.release` w `mercury-install-package` ustawić na `${hgdb-client.version}` (jedno miejsce dla klienta).
4. Po zmianie podbijanie wersji sprowadza się do trzech właściwości w jednym pliku: `mercury.lib.version`, `mercury.static.version`, `hgdb-client.version`. Zaktualizować `checklista-wydan.md`.
5. Sprawdzenie: `mvn -o clean test-compile` oraz pełne zbudowanie pakietu (`mvn -o install` w `mercury-cmd`), czyli to, co ostatnio zatrzymało się na `lib20`; skan jarów pakietu pod kątem log4j.
6. Opcjonalnie (osobna decyzja): w Ant sprawdzać, że `info.version` WAR-a w `mercury/mercury-ws-app/target` równa się `mercury.static.version`, żeby nie spakować WAR-a z innego wydania.

## 6. Wykonane zmiany (2026-10-28)

Decyzja autora: kroki 1, 3 i 4 z propozycji, a w kroku 2 zamiast aliasu zmiana nazwy `mercury.static.version` na **`mercury.srv.version`** i wskazanie jej we wszystkich zależnościach serwera.

| Właściwość | Wartość | Gdzie używana |
|---|---|---|
| `mercury.lib.version` (nowa) | 3.0.4.18 | 9 zależności `mercury-lib` (6 w głównym `pom.xml`, 3 w `mercury-srv-cmd`) |
| `mercury.srv.version` (dawniej `mercury.static.version`) | 3.0.4.10 | 10 zależności serwera w `mercury-srv-cmd` (dawniej `mercury.server.project.version`, usunięta), `finalName` i `outputDirectory` jarów, katalog `mercury-install-package-<wersja>`, Ant: `project_version` i `mercury_srv_version` (ścieżka jaru `lib20`) |
| `hgdb-client.version` | 3.1.4.19 | zależności klienta; `hgdb.client.version.release` w `mercury-install-package` jest teraz aliasem `${hgdb-client.version}` |

Zmienione pliki: `pom.xml`, `mercury-srv-cmd/pom.xml`, `mercury-transfer/pom.xml`, `mercury-install-package/pom.xml`, `mercury-install-package/src/main/build/build-installation.xml` (w `git grep` nie zostało żadne `mercury.static.version`, `mercury_static_version` ani `mercury.server.project.version` poza archiwalnym `releases/`). Po wydaniach wystarczy podbić trzy właściwości w głównym `pom.xml`.

**Sprawdzenie:**

- `mvn -o clean test-compile`: wszystkie moduły `SUCCESS`.
- `mvn -o install -Dmaven.test.skip=true`: `BUILD SUCCESS`; powstał `releases/mercury-install-package-3.0.4.10.POSTGRESQL.20261027.zip` (374 pliki, 131 MB). To ten krok zatrzymał się wcześniej na `lib20`.
- Zawartość pakietu: `libExt` = `mercury-srv-cmd-3.0.4.10`, `mercury-transfer-3.0.4.10`, `hgdb-ws-client-cxf-3.1.4.19`, `hgdb-multi-client-3.1.4.19`, `fscontext`, `providerutil`; `lib20` = `mercury-ws-server-api20-3.0.4.10`; `lib` = sześć jarów `mercury-lib` 3.0.4.18, `sccommon-*` 2.0.0.1, `poi-toolkit` 4.1.0.1, `ccrto-openapi` 2.0.0.1, Logback 1.2.13, `log4j-over-slf4j` 1.7.36, `spring-jcl`; `installableApps` = trzy WAR-y; `config/logback.xml` pisze do `mercury-cmd.log`, nie ma `log4j.properties`.
- Skan 219 jarów pakietu: odwołania do `org/apache/log4j` mają tylko `cxf-core-3.0.12.jar` (10) i `jboss-logging-3.4.3.Final.jar` (5), czyli to, co znaleziono w rozpoznaniu 214 (klasy opcjonalne, uruchamiane tylko po jawnym wyborze loggera).

**Uwagi i rzeczy niezmienione:**

- W `releases/` został katalog `mercury-install-package-3.0.4.18` z przerwanego budowania sprzed zmiany (bez zipa, `lib20` pusty). Jest nieśledzony i można go usunąć.
- Skrypty `bin/mercury-cmd.sh` i `mercury-transfer.sh` nie mają `-Dorg.jboss.logging.provider=slf4j` (w `setenv.sh` Tomcata jest). Hibernate w narzędziach wybierze więc provider log4j przez mostek `log4j-over-slf4j`; działa, ale nie jest to jawny wybór. Do decyzji, czy dodać.
- Nadal na sztywno `MERCURY_VERSION=3.0.1.0.2` i `MERCURY_HOME` w tych skryptach (punkt 4.3).
- Opcjonalny krok 6 z propozycji (kontrola `info.version` WAR-a w Ant) nie został wykonany.

## 7. Skrypty i weryfikacja pakietu (2026-10-28)

Decyzja autora: poprawić skrypty `*.sh` i dopisać weryfikację. Katalog `releases/mercury-install-package-3.0.4.18` autor usunął.

**Skrypty** (`mercury-install-package/src/main/bin/mercury-cmd.sh`, `mercury-transfer.sh` i `system-config-sample/linux/bin/mercury-cmd.sh`):

- dodane `-Dorg.jboss.logging.provider=slf4j` w `JAVA_OPTS` (jawny wybór SLF4J przez Hibernate/JBoss Logging, jak w `setenv.sh` Tomcata),
- usunięty `MERCURY_VERSION` (3.0.1.0.2 i 3.0.1.0.1; nigdzie nieużywany w repozytorium),
- w skryptach `src/main/bin` `MERCURY_HOME` liczony z położenia skryptu (`$(cd "$(dirname "$0")/.." && pwd)`) zamiast ścieżki na sztywno do `releases/mercury-install-package-3.0.1.0.2`; w przykładzie Linux zostaje `MERCURY_HOME=/opt/mercury-3.0` (przykładowa ścieżka wdrożenia).
- Nie zmieniano `mercury-server.sh`, `mercury-ports.sh`, `startup.sh` i `shutdown.sh` (opakowania serwera Tomcat, bez opcji JVM Mercury), ani `JAVA_HOME` i ścieżek magazynu zaufania (konfiguracja środowiska). Skrypty z `src/main/bin` kopiuje Ant bez filtrowania Mavena (`clean` kasuje wcześniej przefiltrowany katalog), więc zmienne `${...}` w nich nie byłyby podstawiane; stąd wyliczanie `MERCURY_HOME` w samym skrypcie.

**Weryfikacja:** nowy cel `verify` w `build-installation.xml`, uruchamiany po `windows` (albo `unix`), a przed `dist` (`installByMaven`, `all`, `allUnix`). Przerywa budowanie z komunikatem, gdy:

| # | Sprawdzenie | Oczekiwanie |
|---|---|---|
| 1 | WAR `mercury-ws-app.war` | `info.version` w `openapi_en.json` równe `mercury.srv.version` |
| 2 | `lib` | sześć jarów `mercury-lib` w wersji `mercury.lib.version` (`mercury-core`, `mercury-entities-<baza>`, `mercury-spring-remoting`, `mercury-srv-api`, `mercury-ws-dto-api`, `mercury-ws-server-api`) |
| 3 | `lib` | brak innych jarów `mercury-*` i `hgdb-*` w innej wersji |
| 4 | `lib` | brak `log4j.jar`, `log4j-*`, `reload4j*`, `slf4j-log4j12*`, `slf4j-reload4j*`, `commons-logging*` (poza `log4j-over-slf4j`), obecne `logback-classic`, `logback-core`, `log4j-over-slf4j` |
| 5 | `libExt` | `mercury-srv-cmd` i `mercury-transfer` w wersji `mercury.srv.version`, `hgdb-ws-client-cxf` i `hgdb-multi-client` w wersji klienta; brak innych `mercury-*` i `hgdb-*` |
| 6 | `lib20` | dokładnie jeden jar `mercury-ws-server-api20-<mercury.srv.version>.jar` |
| 7 | `config` | jest `logback.xml`, nie ma `log4j.properties` |

W `pre` doszła właściwość `mercury_lib_version` (z `mercury.lib.version`).

**Testy:** pozytywny: `mvn -o install -Dmaven.test.skip=true` przechodzi i wypisuje „Weryfikacja pakietu zakonczona powodzeniem” (powstał `mercury-install-package-3.0.4.10.POSTGRESQL.20261028.zip`). Negatywne (osobne uruchomienie Anta 1.8.1 na gotowym pakiecie z podmienionymi wartościami lub katalogami): zła wersja `mercury-lib` (3.0.4.17), zła wersja klienta (3.1.4.18), WAR z wydania 3.0.4.9, `log4j-1.2.14.jar` i `commons-logging-1.2.jar` w `lib`, nadmiarowy `mercury-core-3.0.4.10.jar` w `lib`, `log4j.properties` w `config`, nadmiarowy `mercury-transfer-3.0.4.9.jar` w `libExt`, dwa jary w `lib20`: każdy przypadek przerywa budowanie ze zrozumiałym komunikatem. Nie testowano brakującego `logback-classic` ani `log4j-over-slf4j` (kontrola nr 4, druga część).

**Do wiadomości:** w `releases/` jest teraz też starszy `mercury-install-package-3.0.4.10.POSTGRESQL.20261027.zip` (z poprzedniego budowania); nieśledzony, można usunąć.

## 8. Ścieżka `pro/ibpm` w `repo/` i skrypty `install.sh`/`deploy.sh` (2026-10-28)

**Błąd:** `maven-jar-plugin` w głównym `pom.xml` `mercury-cmd` zapisywał jary do `repo/pro/ibpm/mercury/<artefakt>/<mercury.srv.version>/`, czyli w starej grupie `pro.ibpm.mercury` i z wersją serwera, a GAV projektu to `io.hgdb.mercury:<artefakt>:<project.version>`. Plik `.gitignore` ignorował tę błędną ścieżkę (`/repo/pro/ibpm/mercury`), więc błąd nie był widoczny w `git status`. W repozytorium nie było też dokąd wysyłać `mercury-srv-cmd` i `mercury-transfer`: ich jary trafiają do `libExt` pakietu, a nie do `repo/`.

**Poprawki:**

- `pom.xml`: `outputDirectory` = `${project.local.cmd.repo}/io/hgdb/mercury/${project.artifactId}/${project.version}`, `finalName` = `${project.artifactId}-${project.version}` (jak w `hgdb-client-open`). Wersja katalogu to teraz wersja projektu; wersja serwera (`mercury.srv.version`) zostaje w nazwach jarów w `libExt` i pakiecie.
- `mercury-srv-cmd/pom.xml` i `mercury-transfer/pom.xml`: dodatkowe wykonanie `repo-jar` (`maven-jar-plugin`, faza `package`) z kopią jaru w `repo/io/hgdb/mercury/...`; dotychczasowe wykonanie nadal pisze do `libExt`.
- `install.sh`: po `install` kopiuje `pom.xml` i pliki pom modułów `mercury-srv-cmd` i `mercury-transfer` do `repo/io/hgdb/mercury/<moduł>/<wersja>/` (w układzie `hgdb-client-open`), potem `versions:revert`.
- `deploy.sh`: dotąd kopia skryptu `hgdb-client-open` (jary `hgdb-*`). Teraz wysyła pom nadrzędny `mercury-cmd` oraz jary `mercury-srv-cmd` i `mercury-transfer`, sprawdza obecność plików i przerywa z komunikatem, gdy ich nie ma; tryb `DRY_RUN=1`, wersję można nadpisać (`LIB_VERSION`). Nie wysyła `mercury-benchmark` i `mercury-install-package`.
- `.gitignore`: `/repo/pro/ibpm/mercury` → `/repo/io/hgdb/mercury`.

**Testy:** `mvn -o clean install -Dmaven.test.skip=true` zapisuje pięć jarów w `repo/io/hgdb/mercury/...` (wersja `3.1.4-SNAPSHOT`); `install.sh` uruchomiony naprawdę (offline, wersja 3.1.4.1 z `minor_version.txt`) kończy się sukcesem, kopiuje trzy pliki `pom` z wersją 3.1.4.1 i przywraca wersje POM do `3.1.4-SNAPSHOT`; `DRY_RUN=1 ./deploy.sh` wypisuje trzy polecenia `deploy:deploy-file` z poprawnymi ścieżkami, a brak plików (inna wersja, brak jaru) przerywa z kodem 1. **Prawdziwego wysłania do Nexusa nie wykonano.** Do decyzji autora: czy wysyłać też `mercury-benchmark` (jar tylko z testami) i `mercury-install-package` (pusty jar modułu `pom`); obecnie nie.
