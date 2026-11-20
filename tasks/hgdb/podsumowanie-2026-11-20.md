# Podsumowanie 2026-11-20

## Wydane

- **Rano (zamknięcie 219):** `poi-toolkit` 4.1.0.5, `mercury` 3.0.4.31, `mercury-cmd` 3.1.4.8 (wydania autora). Przygotowałem pakiet i obrazy 3.0.4.31, wysłałem je do Nexusa i zaktualizowałem klaster Kubernetes `mercury-test` (testy: token idempotentny, import bez `chmod`, eksport, `saveList` 2704 spraw w 13,2 s, restarty POI 0).
- **Wieczorem (zamknięcie hgdb-utils-011):** `mercury` 3.0.4.32 i `mercury-cmd` 3.1.4.9 (wydania autora; PR #17 `hgdb-utils-011b` z poprawką pakietu zrobiony po wydaniu 3.1.4.9).
- **Pakiet i obrazy 3.0.4.32** (przygotowałem i wysłałem do Nexusa): `mercury-install-package-3.0.4.32.POSTGRESQL.20261120.zip` (repozytorium raw `mercury-docker-packages`, rozmiar zgodny z lokalnym), `ibpm/mercury:mercury-hgdb-3.0.4.32` (`sha256:4f0911f6…`) i `ibpm/mercury-lb:mercury-hgdb-3.0` (`sha256:b97a6176…`, nowa konfiguracja nginx z `503`; ruchomy znacznik zastąpił poprzedni obraz). Wersje w `mercury-docker` podbite `set-versions.sh` (12 plików). Klaster `mercury-test` nie został jeszcze zaktualizowany do 3.0.4.32.
- `docusaurus-hgdb`: rozdział `008_Command_line_tools` (en i pl: przegląd, `mercury-cmd`, kopia zapasowa indeksu Lucene, `mercury-transfer`), artykuł o parametrach `mercury.properties` (`Mercury_DB_configuration`), tagi `mercury-cmd` i `performance`, poprawiona składnia `lc` w artykule o kalibracji. Budowanie serwisu (en i pl) bez ostrzeżeń.

## Zadanie 219 zamknięte, zadanie hgdb-utils-011 zamknięte

219: ostateczne zamknięcie po wydaniach z rana (szczegóły w `tasks/hgdb/219-…/TASK.md`).

**hgdb-utils-011** (szczegóły w `tasks/hgdb-utils/011-…/TASK.md`, sekcje „Etap 1”, „Etap 2” i „Podsumowanie zadania”):
- **picocli** w `mercury-cmd` i `mercury-transfer`: podpolecenia z aliasami, `--help`, `--version`, kody wyjścia 0, 1, 2, bez zgodności ze starymi flagami; pomoc w en, pl, de, es, fr, ko (de, es, fr, ko przez `localizer.py`; język z `--lang`, potem `LC_ALL`, `LC_MESSAGES`, `LANG`, JVM).
- **Kopia zapasowa i odtwarzanie indeksu Lucene przez REST** (`index-backup`, `index-restore --backup-id`, `index-backups`): `LuceneIndexBackupExtRest` w `mercury-ws-app`, OAuth z zakresem `mrc-sysadmin`, `--user` i `--passwd` z dopytaniem, `--node` albo konfiguracja. Serwer na czas operacji odbiera i odrzuca paczki JMS, a indeks wyrównuje z archiwum (`CaseIndexArchiveAligner`); numer SCN kopii obniżany o paczki czekające w kolejce. Restore: czyszczenie katalogu docelowego, kopia, przełączenie, wyrównanie w przebiegach aż do ok. 100 brakujących wpisów, wtedy węzeł wraca online. Ustalone odczytem kodu: ponowne indeksowanie z archiwum nie wysyła JMS do innych węzłów.
- **Klaster:** MASTER przed operacją przekazuje rolę (cisza heartbeatu, węzeł sam się zdetronizuje, zostaje SLAVE; `mercury.lucene.backup.handoffMaster`), węzeł w konserwacji odpowiada klientom `503` (`NodeMaintenanceFilter`, `NodeMaintenance`), a w `mercury-lb` `max_fails` i `proxy_next_upstream http_503 non_idempotent`. `reviewMasterRole` (decyzja autora): węzeł bez MASTER-a online sam próbuje objąć rolę (po `forceSetOffline` MASTER-a i w cyklu heartbeatu).
- **Zmiana zachowania restore:** dawny restore reindeksował z archiwum tylko przy włączonej fladze blokady zapisu (w praktyce nigdy) i robił to przed przełączeniem katalogu; scenariusz `LuceneBackupScenario` dostosowany (po restore sprawa dodana po backupie jest w indeksie, ścieżka indeksu zmienia się przed wyrównaniem).
- **Testy:** jednostkowe (`MercuryCmdTest` 13, `IndexBackupCommandsTest` 13, `TransferCmdTest` 4, `CaseIndexMasterHandoffTest` 4, `CaseIndexArchiveAlignerTest` 4, `NodeStatusMonitorReviewTest` 5, `NodeMaintenanceFilterTest` 5); `LuceneBackupSrvTest` (4 scenariusze jednowęzłowe) OK; **`LuceneBackupClusterTest` fazy A, B i C OK na prawdziwym klastrze** (Tomcat jako `node1`, test jako `node2`): restore odrzucił 4 realne paczki JMS, węzeł 2 został MASTER-em po 1,5 s, a po ciszy węzła 2 węzeł 1 odzyskał rolę po 17 s; `503` w trakcie prawdziwego restore (`/browser`) przy `/rest/token` 200 przez cały czas.

## Obserwacje

- ✅ **134** (niestabilny `luceneBackupScenario`: asercja ścieżki indeksu akceptuje stan przed i po przełączeniu), ✅ **196** (`consistency="eventual"` dla `default-update-timestamps-region` we wszystkich kopiach testowych `ehcacheDefault.xml` i `ehcacheCommon.xml`), ✅ **197** (przegląd roli MASTER, `reviewMasterRole`; faza C potwierdziła koronację).
- Nowa otwarta: **195** (świeżo wystartowany węzeł z pustym widokiem klastra może zdetronizować działającego MASTER-a; nowa ścieżka ma karencję, stara bez zmian).
- Wcześniejsze z 219 (dzisiejsze): ✅ 180 (fsGroup, `runAsGroup` i `runAsUser` na NFS), ✅ 181, ✅ 182 (wydawanie tokenu idempotentne), ✅ 185 (`mercury.sequence.interval`), ❌ 186 (wycofana po pomiarze), ✅ 187 (limit nginx w chartcie), ✅ 192 (konflikt `clientId` ActiveMQ po wymianie poda), ✅ 193 i 194 (`install.sh`).

## Do wiedzy

- **Pakiet z dzisiejszą datą (22:35), który już leżał w `releases`, nie zawierał `picocli` w `libExt`:** `mercury-cmd` i `mercury-transfer` z pakietu by się nie uruchomiły. Naprawione w `hgdb-utils-011b` (zależność w module pakietu, kopiowanie, sprawdzenie w `verify`); w Nexusie jest pakiet już po poprawce. Wydany `mercury-cmd` 3.1.4.9 poprawki nie zawiera. Ta sama poprawka ustawia `Implementation-Version` jaru na `mercury.srv.version`, dzięki czemu `--version` pokazuje 3.0.4.32 zamiast `3.1.4-SNAPSHOT`.
- **Wysyłka obrazu serwera urwała się (`unexpected EOF`), po czym Docker Desktop przestał odpowiadać (HTTP 500).** Po restarcie Docker Desktop przez autora obraz został lokalnie, więc wysłałem go bez przebudowy (`--no-build`), a `mercury-lb` zbudowałem i wysłałem osobno.
- **nginx:** z `proxy_next_upstream error timeout http_503` co drugi POST dostawał 503 (nginx nie uczy się z 503 przy żądaniach nieidempotentnych), a `non_idempotent` z `error` i `timeout` mógłby podwoić POST przerwany w trakcie przetwarzania; wybrane `http_503 non_idempotent`, bez `error` i `timeout`. Skutek: żądanie na właśnie wyłączony węzeł (odmowa połączenia) nie jest ponawiane (502), ale węzeł jest od razu pomijany.
- **Warianty kodu klastra:** `mercury-srv` ma `single.node` (tylko lokalne `wakeup()`), a wybór MASTER-a jest w wariancie `cluster.node` z `mercury-srv-slave`; Tomcat używa najpewniej pierwszego. Mój pierwszy wniosek o „luce w koronacji” był błędny (wskazał go autor); opis obserwacji 197 przepisany. Zapisane w pamięci.
- **Konflikty w `docusaurus-hgdb`:** lokalny commit autora `0fbecb3` zmienił w 7 plikach tylko końce linii (LF na CRLF), więc konflikt z PR #9 rozwiązano wersją z PR #9 (drzewo identyczne z `origin/main`).
- **Tomcat po restarcie z kluczem Trial** (do 2026-12-20, `maxNodes=3`) ma działające repozytorium CMIS; poprzednio `LicenseException` wyłączał CMIS. Scenariusz klastrowy tworzy sprawy przez logikę, nie przez CMIS.
- **Incydenty dnia (rano, 219):** polecenie przywracające nakładkę K8s skasowało indeks Lucene `Case` na `mercury-test` (odbudowany automatycznie w ok. 4 minuty, zgłoszone autorowi); test z `rm` skasował `poi-toolkit-4.1.0.4.jar` w `poi-toolkit/release/lib` (przywrócony z `.m2`, identyczny); `mvn` zmienia śledzone XSD w `mercury-server/IBPM/...` (przywracane `git checkout`).

## Stan środowisk

- `mercury-test` (Kubernetes): `mercury` 3.0.4.31, wciąż bez 3.0.4.32 i bez nowego `mercury-lb`; dane `Bench219` i zestaw `Quarter`/`Month`/`Invoice` zostają (analityka).
- Lokalny Tomcat (`mercury-server`): `node1`, MASTER, `mercury-db-test`, kod 3.0.4.32; JVM testu zakończony. W `mercury-db-test` dane testowe: sprawy `BCL.*` i `CmisFolder.*` z moich prób oraz 4 stare wpisy bufora (SCN 58305); do decyzji autora.
- Nexus: pakiet i obrazy 3.0.4.32 oraz `ibpm/mercury-lb:mercury-hgdb-3.0` (nowy).
- Lokalnie: `mercury` ma zmienione XSD z budowania i `minor_version.txt`, `mercury-cmd` ma `minor_version.txt`; `mercury-intelliJ-workspace` ma 11 niewypchniętych commitów oraz niezacommitowane `docs/obserwacje.md`, `docs/moduly/mercury-cmd.md`, `tasks/hgdb-utils/011-…/TASK.md`, plan i to podsumowanie.
