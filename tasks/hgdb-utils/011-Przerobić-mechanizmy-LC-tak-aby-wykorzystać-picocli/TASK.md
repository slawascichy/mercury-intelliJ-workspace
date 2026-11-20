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
- Skrypty: `mercury-cmd.sh` w pakiecie instalacyjnym (dwa miejsca) i w obrazie Docker uruchamiają `org.mercury.cmd.MercuryCmd "$@"`; `mercury-server.sh` używa `ep` i `gl Case`. README `mercury-cmd` i `docs/moduly/mercury-cmd.md` zaktualizowane.
- Błędne argumenty (nieobsługiwana encja, brak `--queries` i `--generate`) kończą się kodem 2 (`System.exit`); błąd wykonania nadal zostawia proces do `Ctrl+C` jak dotąd.
- Testy `MercuryCmdTest` (9): aliasy, argumenty pozycyjne, wszystkie opcje `lc`, `-D`, kody wyjścia, wybór języka, pomoc po angielsku i polsku (zastąpiły `LuceneCalibrationActionTest`). Sprawdzone też na kopii rozpakowanego pakietu 3.0.4.31 z nowym jarem: `ep` drukuje zakodowane hasło i komunikaty jak dotąd, `--help` po polsku i angielsku, `gl Foo` kod błędu.

**Zostaje do etapu 1:** tłumaczenia pomocy na de, es, fr, ko (`localizer.py`), wydanie `mercury-cmd`, sprawdzenie w obrazie Docker (`mercury-server.sh` po zmianie `ep` i `gl`), `mercury-transfer` (osobny interfejs, nieprzerobiony).

**Etap 2 (backup i restore indeksu Lucene):** do analizy: `CaseIndexBackupAction` i `CaseIndexRestoreBackupAction` w `mercury-srv`, zawieszenie JMS podczas backupu, ponowne wysyłanie JMS do innych węzłów po restore.
