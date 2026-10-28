# Checklista wydań (zadania 58 i 214)

Lista dla autora (wydania robi autor), z podziałem na to, co robisz Ty, i to, co robię ja po otrzymaniu numeru wersji. Stan z 2026-10-27, wieczór. Wszystkie nazwy właściwości i ścieżki pochodzą z POM-ów.

## 1. Stan wersji

| Artefakt | Wersja | Uwagi |
|---|---|---|
| `sccommon` | 2.0.0.1 | wydane, bez log4j; używane w `mercury-lib`, `mercury`, `hgdb-client-open`, `mercury-cmd` |
| `poi-toolkit` | 4.1.0.1 | wydane, Logback |
| `ccrto-openapi` | 2.0.0.1 | wydane, bez log4j; w `mercury` i `hgdb-client-open` podniesione z `1.2-SNAPSHOT` do 2.0.0.1 (2026-10-27, zatwierdzone przez autora) |
| `mercury-lib` | 3.0.4.18 | poprawione wydanie; używane przez `mercury`, `hgdb-client-open`, `mercury-cmd` |
| `mercury` | 3.0.4.10 | wydane 2026-10-27 po PR i merge'u, z `ccrto-openapi` 2.0.0.1 (3.0.4.9 miało snapshot). Sprawdzone: 18 jarów serwera bez odwołań do log4j, WAR z `LogbackLoggerBackend` bez adaptera log4j i bez jarów Logbacka/log4j/`sccommon` w `WEB-INF/lib`, `info.version` w `openapi_en.json` = 3.0.4.10 |
| `hgdb-client-open` | 3.1.4.19 | wydane 2026-10-28 po PR i merge'u (3.1.4.18 miało `ccrto-openapi` `1.2-SNAPSHOT`); `sccommon` 2.0.0.1, ehcache 3.6.1, `ccrto-openapi` 2.0.0.1, `mercury.server.version` 3.0.4.10; `CacheHelper` dostosowany. Trzy jary klienta 3.1.4.19 bez odwołań do log4j |
| `mercury-cmd` | niewydane | wersje w jednym pliku (`pom.xml`): `mercury.lib.version` 3.0.4.18, `mercury.srv.version` 3.0.4.10, `hgdb-client.version` 3.1.4.19 (stan 2026-10-28); `mvn -o clean test-compile` i `mvn -o install` przechodzą, pakiet `mercury-install-package-<mercury.srv.version>.POSTGRESQL.<data>.zip` zbudowany; zmiany niezatwierdzone, gałąź `hgdb-058` bez PR |
| `mercury-docker` | niewydane | wersje wskazują jeszcze 3.0.3.2.11 (zadanie 211) |

## 2. Kolejność wydań

Kolejność wynika z zależności: `mercury-lib` → `mercury` i `hgdb-client-open` → `mercury-cmd` → `mercury-docker`. `mercury` nie zależy od `hgdb-client-open` (brak w POM-ach), więc te dwa można wydać w dowolnej kolejności.

1. **Zamknięcie zadania w repozytorium** (Ty): push gałęzi, PR, merge, `git pull` na `master`. Gałąź `hgdb-058` w `mercury-client` usuń (`git checkout master`, `git branch -D hgdb-058`; nie wchodzi do wydania).
2. **Wydanie** (Ty, skrypty wydania): z czystego `master` po merge'u (`git status` bez zmian). Polecenia budowania z `CLAUDE.md`: `mercury-lib`: `mvn clean install -Dmercury.static.version=<wersja> -Ddatabse.provider=POSTGRESQL -Dmaven.test.skip`; `mercury`: `mvn -U clean install -Dmaven.test.skip=true`.
3. **Numer wersji** (Ty → ja): wiadomość w formie „wydanie `<artefakt>` `<numer>`”. Po niej robię podbicie z tabeli niżej i sprawdzam budowanie; nie commituję, zmiany zatwierdzasz Ty.
4. Przy nowym wydaniu `mercury-lib` albo `mercury` (po poprawkach) idziemy w dół łańcucha od nowa.

## 3. Podbicie wersji po wydaniu (robię ja)

| Po wydaniu | Właściwość i plik do podbicia |
|---|---|
| `mercury-lib` | `mercury.static.version` w `mercury/pom.xml` (to właściwość `mercury`, nie `mercury-cmd`); `mercury.project.version` w `hgdb-client-open/pom.xml`; **`mercury.lib.version`** w `mercury-cmd/pom.xml` |
| `mercury` | `mercury.server.version` w `hgdb-client-open/pom.xml`; **`mercury.srv.version`** w `mercury-cmd/pom.xml` (steruje też nazwą pakietu, jarów `mercury-srv-cmd` i `mercury-transfer` oraz ścieżką `lib20`; 3.0.4.10 podniesione 2026-10-27) |
| `hgdb-client-open` | `hgdb-client.version` w `mercury-cmd/pom.xml` (jedno miejsce; `hgdb.client.version.release` w `mercury-install-package` jest aliasem `${hgdb-client.version}`) |
| `sccommon`, `poi-toolkit`, `ccrto-openapi` | `sccommon.version`, `poi-toolkit.version`, `ccrto-openapi.version` w `mercury-lib`, `mercury`, `hgdb-client-open` i `mercury-cmd` (`sccommon-utils.version` też w `mercury-cmd`) |

W `mercury` właściwości `3.0.4-SNAPSHOT` (wersja projektu) ustawia skrypt wydania; ich nie ruszam.

**Podniesione 2026-10-27** (decyzja autora): `ccrto-openapi.version` z `1.2-SNAPSHOT` do `2.0.0.1` w `mercury/pom.xml` i `hgdb-client-open/pom.xml` (wydanie 2.0.0.1 jest bez log4j). Sprawdzone budowaniem: `mvn -o -pl mercury-ws-app -am test-compile` w `mercury` i `mvn -o test-compile` w `hgdb-client-open` przechodzą. Zmiany niezatwierdzone. Jeśli `mercury` 3.0.4.9 i `hgdb-client-open` 3.1.4.18 zostały wydane ze snapshotem, potrzebne jest kolejne wydanie obu.

## 4. Kontrola po każdym wydaniu

Sprawdzam ja (na podstawie wydanych jarów i WAR-ów w lokalnym repozytorium albo na serwerze dev):

- w jarach `mercury-*` i `hgdb-*` nie ma odwołań do `org/apache/log4j` (`unzip -p <jar> | grep -a -c "org/apache/log4j"` daje 0),
- WAR `mercury-ws-app` ma `LogbackLoggerBackend` i nie ma `Log4j1LoggerBackend`,
- w `openapi*.json` pole `info.version` równa się numerowi wydania,
- **Pakiet `mercury-cmd`** weryfikuje się sam: cel `verify` w `build-installation.xml` (uruchamiany przy `mvn install` w `mercury-cmd`) przerywa budowanie, gdy wersje `lib`, `libExt`, `lib20` i WAR `mercury-ws-app` nie zgadzają się z `mercury.lib.version`, `mercury.srv.version` i `hgdb-client.version`, albo w pakiecie są jary starego logowania (szczegóły: `analiza-wersji-mercury-cmd.md`, sekcja 7),
- `mvn -o clean test-compile` w `mercury-cmd` przechodzi; dla nowych numerów, których nie ma lokalnie, pobierasz je poleceniem `mvn -U test-compile` w `mercury-cmd` (u mnie certyfikaty do Nexusa nie działają).

## 5. Pakiet i serwer testowy (po wszystkich wydaniach)

1. W `mercury-cmd`: zbudowanie pakietu instalacyjnego (`mercury-install-package`; uruchamia skrypt Ant `src/main/build/build-installation.xml`, który bierze jary klienta z `hgdb-client-open/repo/...` według `hgdb.client.version.release`). Dokładna ścieżka i polecenie: `211-…/TASK.md`. Sprawdzenie nazwy pakietu i zawartości `config/logback.xml`.
2. Zadanie 211: wgranie pakietu na `hgdb.org/mercury-docker-packages`, aktualizacja `mercury-docker` (wersje, `logback.xml`, `setenv.sh`), test dymny, publikacja obrazów.
3. Serwer testowy (Twój): sprawdzenia odłożone z 214, czyli transfer `mercury-transfer` między dwiema instancjami (pusty `typeCodes`, obserwacja 105), `LoggerConfigurator` w `mercury-srv-cmd` na pakiecie, rotacja plików logu (limit 7 MB, 20 kopii; obserwacja 103). Do instrukcji aktualizacji dochodzą: strona „Logging configuration” (docusaurus), skrypt `06_igo_da_logger_case_id_varchar.sql` (zadanie 169) i zmiana konfiguracji logowania.

## 6. Na serwerze dev (stan 2026-10-27)

`apache-tomcat/mercury/lib` ma jary Logbacka (`logback-classic` i `logback-core` 1.2.13, `log4j-over-slf4j` 1.7.36), `sccommon-*` 2.0.0.1, `poi-toolkit` 4.1.0.1, `ccrto-openapi` 2.0.0.1 i `mercury-gui-core-3.0.4.18.jar` z poprawką `OAuthFilter` (podmienione dwie klasy; po następnym wydaniu `mercury` jar zastąpi wydany). Kopie zapasowe zmienianych plików są w katalogu roboczym sesji (`backup-214`).
