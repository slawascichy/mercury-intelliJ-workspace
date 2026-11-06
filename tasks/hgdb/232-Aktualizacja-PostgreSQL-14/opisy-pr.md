# Opisy pull requestów, zadanie 232

Gałąź `hgdb-232`. Kolejność merge: `mercury`, `mercury-docker`. Szczegóły: `TASK.md`.

## mercury (`hgdb-232`)

**Cel.** Koniec wsparcia PostgreSQL 14 (2026-11-12): aktualizacja sterownika JDBC.
- `pom.xml`: zależność testowa pgjdbc 42.7.14 (Java 8, zależność `checker-qual`).
- Testy: `DatasetScenario` na PostgreSQL 17.11 przechodzi.

## mercury-docker (`hgdb-232`)

**Cel.** Obraz bazy na PostgreSQL 17 i migracja danych istniejących instalacji.
- `postgresql/Dockerfile`: `ARG POSTGRES_VERSION=17.11`.
- Sterownik pgjdbc 42.7.14 w obrazie serwera (stare jary usuwane w Dockerfile) i w ActiveMQ.
- `bin/postgres-migrate.sh`: migracja dump i odtworzenie, porównanie liczby wierszy, `vacuumdb`, kopia starego katalogu do wycofania zmian.
- README bazy i trzech kompozycji: wersja PostgreSQL i procedura migracji.
- **Uwaga dla wdrażających:** katalog danych PG14 nie startuje na PG17; przed pierwszym startem należy uruchomić skrypt migracji.

**Testy.** Test dymny jedno- i dwuwęzłowy; migracja 147 tabel zgodna; skrypty partycjonowania 0 błędów. Helm: nieprzetestowane.

## docusaurus-hgdb

Nowa strona `PostgreSQL_upgrade` (EN i PL) i wpis w spisie konfiguracji.
