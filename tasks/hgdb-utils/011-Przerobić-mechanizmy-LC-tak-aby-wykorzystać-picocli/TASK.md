# [11]  Przerobić mechanizmy LC tak, aby wykorzystać picocli

https://github.com/slawascichy/hgdb-utils/issues/11
LC - `line command`
Bardzo fajny pakiet:
```pom.xml
		<dependency>
		    <groupId>info.picocli</groupId>
		    <artifactId>picocli</artifactId>
		    <version>4.7.7</version>
		</dependency>
```

- Warto przerobić mechanizmy linii komend, usprawnić "help'a".
- Dodatkowo przydałyby się wersje językowe dla tego narzędzia.
- Dodać narzędzie do przeprowadzenia backup i restore indeksu lucene. Sprawdzić czy obsługa JMS w trakcie backupu i 
  restore jest zawieszona, by się nie okazało, że te komunikaty zostaną pominięte? Nie chyba mogą lecieć w trakcie 
  backupu i restore bez obsługi, bo backup i restore i tak bazuje na buforze archiwalnym. Zweryfikować czy po backup 
  i restore aktualizacja indeksu lucene nie wywołuje ponownie JMS do innych węzłów.

## Etap 1: picocli i wersje językowe (2026-11-20, gałąź `hgdb-utils-011` w `mercury-cmd`)

Decyzje autora: gałąź `hgdb-utils-011`; pod-polecenia picocli zamiast flag, bez warstwy zgodności ze starymi flagami; pl i en przez `ResourceBundle` picocli, pozostałe języki (de, es, fr, ko) przez `localizer.py`; w pierwszym etapie migracja istniejących akcji i pomoc z językami, backup i restore indeksu w drugim.

**Zrobione:**
- `org.mercury.cmd.MercuryCmd` (picocli 4.7.7): polecenia `encode-password` (`ep`), `sync-types` (`ts`), `generate-lucene` (`gl`), `validate-entities` (`vl`), `reindex-cases` (`ric`), `reload-predefined` (`rpd`), `jdbc-test` (`jdbctest`), `lucene-calibration` (`lc`) w `org.mercury.cmd.commands`; opcja `-D` (przed i po nazwie polecenia), `--lang`, `--help` i `--version` (wersja z manifestu jaru). Opcje `lc` zastąpiły ręczny parser (`LuceneCalibrationOptions`), `--threads` dla `gl` i `vl` działa naprawdę (dawna pomoc obiecywała `[thread_count]`, ale kod go ignorował).
- Usunięto starą implementację: `CommandLine`, `CommandLineArguments`, `CmdActionsEnum`, `HelpAction`, `ICommandLine`; akcje mają typowane konstruktory zamiast `Object[] args`.
- Pomoc generowana z pakietu zasobów `org/mercury/cmd/CmdMessages.properties` (angielski, domyślny) i `CmdMessages_pl.properties`. Komunikaty `Operation finished ...` i `Please press 'Ctrl+C' ...` zostały po angielsku bez zmian, bo `mercury-server.sh` (mercury-docker) filtruje nimi wynik `ep`.
- Język pomocy: `--lang`, potem zmienne `LC_ALL`, `LC_MESSAGES`, `LANG` (np. `de_DE.UTF-8`), potem ustawienie JVM (JVM na Windows ignoruje `LANG`), w ostateczności angielski. Pakiety `CmdMessages_{de,es,fr,ko}.properties` przetłumaczył `localizer.py`; test sprawdza zgodność kluczy we wszystkich językach.
- Skrypty: `mercury-cmd.sh` w pakiecie instalacyjnym (dwa miejsca) i w obrazie Docker uruchamiają `org.mercury.cmd.MercuryCmd "$@"`; `mercury-server.sh` używa `ep` i `gl Case`. README `mercury-cmd` i `docs/moduly/mercury-cmd.md` zaktualizowane.
- Błędne argumenty (nieobsługiwana encja, brak `--queries` i `--generate`) kończą się kodem 2 (`System.exit`); błąd wykonania nadal zostawia proces do `Ctrl+C` jak dotąd.
- Testy `MercuryCmdTest` (13): aliasy, argumenty pozycyjne, wszystkie opcje `lc`, `-D`, kody wyjścia, wybór języka z argumentów i ze zmiennych środowiska, zgodność kluczy pakietów, pomoc we wszystkich 6 językach (zastąpiły `LuceneCalibrationActionTest`). Sprawdzone też na kopii rozpakowanego pakietu 3.0.4.31 z nowym jarem: `ep` drukuje zakodowane hasło i komunikaty jak dotąd, `--help` po polsku i angielsku, `gl Foo` kod błędu.

**Sprawdzone w obrazie Docker** `ibpm/mercury:mercury-hgdb-3.0.4.31` z podmontowanym nowym jarem, picocli i `mercury-cmd.sh`: `--help` z `LANG=de_DE.UTF-8` po niemiecku, `ep` drukuje zakodowany hasło, a filtr `awk` z `mercury-server.sh` zostawia samą wartość. `gl Case` używa tego samego skryptu i klas co dotychczas (nie uruchamiano go bez indeksu).

**Zostaje do etapu 1:** wydanie `mercury-cmd` (robi autor, potem przebudowa obrazu Docker z nowym pakietem), nic więcej poza wydaniem; `mercury-transfer` przerobiony (patrz niżej).

**`mercury-transfer` (2026-11-20, decyzja autora):** `org.mercury.transfer.cmd.TransferCmd` (picocli) zastąpił `CommandLine`; opcje `-t/--type` (wymagana), `-s/--state` (N, A, O, Z), `-q/--query`, `--config` (domyślnie `../config/transfer.properties`), `--lang`; `TransferArguments` jest teraz zwykłym obiektem konfiguracji; pakiet zasobów `TransferMessages` w en, pl, de, es, fr, ko (de, es, fr, ko z `localizer.py`); kody wyjścia 0, 1, 2. Skrypt `mercury-transfer.sh` i `Main-Class` w `pom.xml` wskazują `TransferCmd`. Test `TransferCmdTest` (4).

**Etap 2 (backup i restore indeksu Lucene), 2026-11-20, gałęzie `hgdb-utils-011` w `mercury-cmd` i `mercury`:**

Decyzje autora: `mercury-cmd` jest tylko pośrednikiem, a kopię i odtwarzanie wykonuje serwer; REST (`LuceneIndexBackupExtRest`); restore z `--backup-id`; uwierzytelnianie tokenem OAuth z zakresem `mrc-sysadmin` (bez opcji zmiany zakresu), `client_id` i `client_secret` z konfiguracji klienta; `--user` i `--passwd` z dopytaniem o brakującą wartość; w klastrze nazwa węzła z opcji `--node` albo z konfiguracji; podczas kopii i odtwarzania węzeł wstrzymuje przetwarzanie (sekretarz stoi, paczki JMS są odbierane i odrzucane), a po operacji indeks wyrównuje się z archiwum; MASTER przed operacją przekazuje rolę innemu węzłowi (cisza heartbeatu, węzeł sam się zdetronizuje); odtwarzający węzeł wraca online (heartbeat), gdy do końca archiwum brakuje około 100 wpisów.

Ustalenia z kodu serwera:
- `CaseIndexBackupManager.backupStart()` i `CaseIndexRestoreBackupManager.backupRestoreStart()` wywoływały tylko testy, brak było punktu wejścia.
- Wątki backupu i restore trzymają blokadę rejestru (`CaseIndexLockSupport`), więc sekretarz podczas operacji stoi. W klastrze SLAVE przetwarza tylko paczki JMS (`remoteWork`), bufor przerabia MASTER (SLAVE przerabia go sam tylko wtedy, gdy żaden MASTER nie jest online); MASTER wysyła JMS, zapisuje do indeksu i dopiero potem archiwizuje.
- Dotychczasowy restore reindeksował z archiwum tylko pod warunkiem `isUpdateByArchCaseSaveBufferEnabled()` (flaga blokady zapisu, czyli w praktyce nigdy) i robił to przed przełączeniem katalogu indeksu, a niepusty katalog docelowy tylko ostrzegał (`File.delete()`), więc resztki starych segmentów mieszały się z kopią.
- Wybór MASTER-a: węzeł-MASTER, który dostanie heartbeat MASTER od innego węzła ONLINE, sam zostaje SLAVE; gdy MASTER jest OFFLINE (brak heartbeatu dłużej niż `max(offlineDiff, interwał + 0,5 s)`), pierwszy SLAVE ONLINE (A-Z) koronuje się przy najbliższym routingu sekretarza.
- Obserwacja: węzeł, który wystartuje z pustym widokiem klastra i obudzi sekretarza przed pierwszym heartbeatem węzła 1, koronuje się na MASTER-a i zdetronizowuje działającego MASTER-a (stwierdzone w teście klastrowym; patrz `docs/obserwacje.md`).

Zmiany w `mercury` (`mercury-srv`, `mercury-ws-app`, `mercury-srv-slave`):
- `ILuceneIndexQueueMaintenance` (`org.mercury.logic.jms`): `drainAndDiscard()` (odbiera, potwierdza i odrzuca paczki kolejki węzła na osobnym połączeniu JMS) i `peekMinPendingScn()` (przegląda kolejkę bez odbierania); używane tylko w klastrze (`isClustered()`).
- `CaseIndexArchiveAligner`: `align()` (odrzuca paczki, czeka do 60 s, aż archiwum obejmie ich SCN, reindeksuje od SCN zapisanego na początku operacji) i `alignUntilNear()` (kolejne przebiegi, aż brakuje najwyżej `mercury.lucene.restore.onlineGap` wpisów, domyślnie 100, albo upłynie `mercury.lucene.restore.maxCatchUpMillis`, domyślnie 10 min; wtedy callback wznawia heartbeat i jeszcze jeden przebieg domyka resztę).
- `CaseIndexBackupAction`: numer SCN kopii obniżony do najmniejszego SCN paczki czekającej w kolejce minus 1; w klastrze po kopii `align()`.
- `CaseIndexRestoreBackupAction`: czyszczenie katalogu docelowego, kopia, przełączenie katalogu, `alignUntilNear()`; wynik w `getLastResult()`. Identyfikator kopii przekazuje statycznie `setRequestedBackupId` (akcja jest beanem z proxy), menedżer ma `backupRestoreStart(Long backupId)`.
- `CaseIndexMasterHandoff` (wywoływany z `CaseIndexBackupTh` i `CaseIndexRestoreBackupTh`): MASTER klastra z innym węzłem SLAVE ONLINE wstrzymuje heartbeat (`NodeStatusCheckerRunnable.setHeartbeatPaused`) i czeka (najwyżej `max(offlineDiff, interwał + 0,5 s) + interwał + 2 s`, domyślnie 22,5 s), aż sam się zdetronizuje; wyłączenie: `mercury.lucene.backup.handoffMaster=false`. Restore w klastrze milczy przez cały czas wyrównania.
- `NodeMaintenance` i filtr `NodeMaintenanceFilter` (`mercury-ws-app`, pierwszy w `web.xml`): w trakcie odtwarzania indeksu węzeł odpowiada klientom 503 z `Retry-After` i nagłówkiem `X-Hgdb-Maintenance` (przepuszcza `/rest/token`, usługę kopii, `/remoting/`, `/monitor/`; dodatkowe ścieżki `mercury.node.maintenance.allowPaths`); znacznik włącza wątek restore, a wyłącza moment wznowienia heartbeatu albo `finally`. Test `NodeMaintenanceFilterTest` (5).
- `mercury-docker/mercury-lb` (`1_`, `2_`, `3_mercury.conf`): `max_fails=1 fail_timeout=30s` w grupie `cluster_hgdb` i `proxy_next_upstream http_503 non_idempotent` (celowo bez `error` i `timeout`: z `non_idempotent` mogłyby podwoić POST); składnia sprawdzona na nginx 1.20.1, zachowanie na atrapach backendów (z `error timeout http_503` co drugi POST dostawał 503, bo nginx nie uczy się z 503 przy żądaniach nieidempotentnych).
- `NodeStatusMonitor.reviewMasterRole()` (obserwacja 197): przegląd roli MASTER po `forceSetOffline` MASTER-a i w każdym cyklu heartbeatu; bramki (klaster, nie MASTER/SHARED, nie milczy, nie konserwacja, karencja po starcie, brak ONLINE MASTER-a); test bramek `NodeStatusMonitorReviewTest` (5); koronację sprawdza faza C testu klastrowego (`-Dcluster.phases=ABC`), jeszcze niewykonana.
- REST `LuceneIndexBackupExtRest` w `mercury-ws-app` (`startBackup`, `startRestore`, `getBackupState`; `SysAdminAccess.checkPrivileges()`), klucze `ILuceneIndexBackupExtRest*` w `openapi-docs_{pl,en,de,es,fr,ko}.properties` (en, de, es, fr, ko z `localizer.py`).
- Testy: `CaseIndexMasterHandoffTest`, `CaseIndexArchiveAlignerTest` (jednostkowe), `LuceneBackupSrvTest` (cztery scenariusze backupu w `mercury-srv`; w `scichy-test` klucze `test.skip.luceneBackup*` są `true`), `LuceneBackupClusterTest` w `mercury-srv-slave` (tylko na żądanie, `-Dcluster.backup.run=true`). Zmieniony scenariusz `LuceneBackupScenario`: po restore sprawa dodana po backupie jest w indeksie (nadrobiona z archiwum), a przełączenie katalogu następuje przed wyrównaniem.
- Kopia `ehcacheDefault.xml` w testach `mercury-srv-slave`: `consistency="eventual"` dla `default-update-timestamps-region` (jak w konfiguracji serwera; inne kopie testowe mają jeszcze `strong`).

Zmiany w `mercury-cmd`: polecenia `index-backup` (`ib`), `index-restore` (`ir`), `index-backups` (`ibs`), klient `ServerRestClient` (token OAuth, JSON), opcje `RestAccessOptions` (`--user`, `--passwd`, `--url`, `--node`), właściwości `mercury.cmd.rest.*` w `commandLine.properties` (szablony w pakiecie, w przykładzie dla Linuksa i w `mercury-docker`), pakiet zasobów w sześciu językach. Test `IndexBackupCommandsTest` (13, imitacja serwera HTTP).

**Sprawdzone na prawdziwym serwerze (2026-11-20, Tomcat jako `node1`, test jako `node2`, baza `mercury-db-test`):**
- `mercury-cmd index-backups` i `index-backup --node node1` z lokalnego pakietu: token OAuth, kopia id 1 (SCN 58905), wyrównanie.
- `LuceneBackupClusterScenario` (faza A): kopia i odtworzenie indeksu węzła 2 (SLAVE) pod ruchem; restore trwał 6 s, węzeł milczał (cisza heartbeatu zaobserwowana), wynik „backup SCN 59305, reindeksacja do SCN 59318, odrzucone paczki JMS: 4”, wszystkie 8 spraw z czasu operacji w indeksie.
- Faza B: `startBackup` na węźle 1 (MASTER) przez REST; węzeł 2 został MASTER-em po 7,5 s, węzeł 1 przekazał rolę (log: `Change Lucene Role ... SLAVE`), zrobił kopię i wrócił jako SLAVE; jeden MASTER w klastrze.

- Faza C (ten sam scenariusz, po restarcie Tomcata z nowym kodem): węzeł 2 (MASTER po fazie B) zamilkł, węzeł 1 objął rolę MASTER po 17 s (log: `[Review Lucene Role] ... no online MASTER`, `Change Lucene Role ... MASTER`), a węzeł 2 został zdetronizowany; jeden MASTER w klastrze. Fazy A, B i C w jednym przebiegu: `OK`.
- Filtr 503 na prawdziwym restore: `mercury-cmd index-restore --node node1` na Tomcacie przy równoległym `curl` co ok. 150 ms: ścieżka kliencka `/mercury-ws-app/browser` odpowiadała 503 przez około 1,5 s (5 z 24 zapytań, log: `Węzeł w konserwacji (index-restore)` i `Koniec konserwacji węzła`), a `/rest/token` odpowiadał 200 przez cały czas (24 z 24).

**Nie sprawdzone:** nginx (`mercury-lb`) z prawdziwymi węzłami Mercury (składnia i zachowanie sprawdzone tylko na atrapach backendów, nowy obraz nie jest zbudowany); klaster z trzema węzłami; dwa węzły z wariantem `single.node` (wtedy nie ma następcy i przekazanie roli kończy się ostrzeżeniem po 22,5 s, backup idzie bez przekazania); restore z dużym indeksem i realną liczbą paczek JMS (w testach okno było rzędu sekund, odrzucono 4 paczki); `mercury-cmd` z fazą B (kopia na MASTER-ze zlecona testem przez REST, nie CLI).
