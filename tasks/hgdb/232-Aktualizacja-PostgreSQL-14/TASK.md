# [232] Aktualizacja PostgreSQL 14 (koniec wsparcia 2026-11-12)

Status: **w toku (2026-11-06)**: implementacja i testy lokalne wykonane, czeka na commit autora, wydanie wersji mercury (3.0.4.20), obrazy i migrację klastra. Numer zadania tymczasowy: autor może go zmienić (numeracja zadań bywa przesuwana przez numery PR).

## Po co

Obraz bazy `ibpm/postgres` (`mercury-docker/postgresql/Dockerfile`) jest zbudowany na `postgres:14.24`. Wsparcie PostgreSQL 14 kończy się 2026-11-12 (źródła wtórne, zob. niżej; datę potwierdzi oficjalna strona `postgresql.org/support/versioning`). Po tej dacie wydania poprawek bezpieczeństwa dla gałęzi 14 ustają, a obraz bazy jest częścią wydania produktu (kompozycje, wykres Helm, dokumentacja).

## Stan wersji (2026-11-06)

| Wersja | Najnowsze wydanie (obraz Docker Hub) | Koniec wsparcia (źródła wtórne) |
|---|---|---|
| 14 | 14.24 (używana) | 2026-11-12 |
| 17 | 17.11 | 2029-11-08 |
| 18 | 18.6 | 2030-11-14 |

Polityka społeczności: pięć lat wsparcia od pierwszego wydania danej wersji głównej. Źródła: [Azure Database for PostgreSQL, polityka wersji](https://learn.microsoft.com/en-us/azure/postgresql/concepts-version-policy), [HeroDevs, daty EOL PostgreSQL](https://www.herodevs.com/blog-posts/postgresql-eol-dates-every-versions-release-end-of-life-timeline), [Instaclustr, wersje i EOL](https://www.instaclustr.com/education/postgresql/postgres-versions-supported-releases-eol-dates-upgrades/) (źródła wtórne, nie strona postgresql.org).

## Co sprawdzono (2026-11-06)

Test dymny kompozycji jednowęzłowej (`smoke-test.sh`, obraz serwera 3.0.4.19 bez zmian) na bazie zbudowanej z **PostgreSQL 17.11** i z **PostgreSQL 18.6** (`FROM postgres:17` i `postgres:18` w kopii `Dockerfile` bazy, obrazy testowe pod tymczasowym prefiksem `pgtest/`, usunięte po teście): oba przebiegi **bez błędów**: kontenery działają, `/rest/openapi.json` 200, token OAuth wydany, usługa REST z tokenem 200 i bez tokenu 401, brak błędów krytycznych w logach i Terracotty.

Z tego wynika:
- skrypty inicjalizacyjne bazy (`01`–`04`, użytkownik `mercury` z `SUPERUSER`, bazy tworzone przez `postgres`) działają na 17 i 18;
- schemat `mercury-db` tworzy aplikacja (`hibernate.hbm2ddl.auto=update`, `hibernate.dialect=org.hibernate.dialect.PostgreSQLDialect` bez wersji), więc ogólny dialekt wystarcza;
- kompozycja ustawia `PGDATA=/var/lib/postgresql/data/pgdata` jawnie, więc zmiana układu katalogu danych w obrazach PostgreSQL 18 (domyślny `PGDATA` `/var/lib/postgresql/<wersja>/docker`) jej nie dotyczy.

## Czego nie sprawdzono i ryzyka

- **Sterownik JDBC jest stary:** `postgresql-42.3.8.jar` w `apache-tomcat/lib` obrazu serwera i `postgresql-42.2.23.jar` w `jdbcdrivers` (`mercury-cmd`). Smoke test przeszedł, ale 42.3.x jest sprzed PostgreSQL 17 i 18, a pgjdbc 42.7.x jest obecnie linią utrzymywaną (także ze względów bezpieczeństwa; do potwierdzenia w notatkach wydań pgjdbc). Wymaga testu: aktualizacja sterownika w obrazie serwera i w `mercury-cmd`, Java 8 jest wspierana przez 42.7.x (do potwierdzenia).
- **Skrypty partycjonowania** (`mercury/db/postgresql/01_createCaseTable_partitioned.sql`, wyzwalacze `02`–`05`, `07_igo_luc_save_buffer_bulk.sql`) nie były uruchamiane na 17 i 18.
- **Funkcjonalność poza testem dymnym:** zapis i odczyt spraw, bufor indeksu i archiwizacja, import hurtowy, `mercury-cmd` (np. `-gl`, transfer), testy `SrvTest` i `DatasetScenario` na bazie 17 i 18 nie były uruchamiane.
- **Wydajność:** nie mierzono (pomiary klastra z zadań 226 i 229 na PostgreSQL 14).
- **Dane istniejących instalacji:** katalog danych PostgreSQL nie jest zgodny między wersjami głównymi; wymaga migracji (dump i odtworzenie albo `pg_upgrade`).
- **Zmiany w zachowaniu PostgreSQL 15 i nowszych** (do przejrzenia w notatkach wydań, nie sprawdzano): domyślne uprawnienia do schematu `public` (aplikacja działa jako `SUPERUSER`, więc nie dotyczy), usunięte funkcje i widoki statystyk.

## Plan (propozycja)

1. **Decyzja o wersji.** Rekomendacja: **17** (dojrzałe wydanie 17.11, wsparcie do 2029), 18 jako kolejny krok; obie przeszły test dymny.
2. **Obraz bazy:** `ARG POSTGRES_VERSION` w `postgresql/Dockerfile` (domyślnie nowa wersja), tag obrazu bez zmian (`ibpm/postgres:mercury-hgdb-3.0`) albo z numerem wersji głównej; skrypt budowania i dokumentacja.
3. **Sterownik JDBC:** pgjdbc 42.7.x w obrazie serwera i w `mercury-cmd`; test.
4. **Testy:** smoke test jedno-, dwu- i trzywęzłowy na nowym obrazie; `DatasetScenario` i `SrvTest` na kontenerze PostgreSQL 17 (profil testowy z innym portem); skrypty partycjonowania; pomiar `mierz-indeks.py` na klastrze (porównanie z wynikami zadania 229).
5. **Migracja danych:** skrypt i opis w README kompozycji i w docusaurusie (dump `pg_dumpall` z kontenera 14 i odtworzenie w 17, albo `pg_upgrade`), z kopią zapasową przed migracją i zmianą wolumenów; Helm (`image.mainTag`, wolumen).
6. **Wydanie:** nowe obrazy, test dymny, wypchnięcie do Nexusa, informacja o migracji w notatkach wydania.

## Decyzje autora (2026-11-06)

1. Wersja docelowa: **17** (17.11).
2. Wymiana sterownika JDBC jest **w tym zadaniu** (pgjdbc 42.7.14: obraz serwera, `mercury-cmd` w obrazie, ActiveMQ, zależność testowa w `mercury/pom.xml`).
3. Klaster **migrujemy**, a przy okazji powstaje instrukcja migracji.

## Zmiany

- mercury: `pom.xml`, zależność testowa pgjdbc 42.7.14.
- mercury-docker: `postgresql/Dockerfile` (`ARG POSTGRES_VERSION=17.11`), `activemq/Dockerfile` i `activemq/lib/postgresql-42.7.14.jar`, `mercury-3.0/Dockerfile` (usunięcie starych jarów, kopia 42.7.14 z `docker-init-config/jdbcdrivers`), `bin/postgres-migrate.sh`, README bazy i trzech kompozycji.
- docusaurus-hgdb (EN i PL): `005_Configuration/PostgreSQL_upgrade.mdx`, wpis w `index.mdx`; składnia MDX sprawdzona.
- Obserwacje 161 (jary w pakiecie `mercury-cmd`) i 162 (Helm, `pg_upgrade`).

## Wyniki testów (PostgreSQL 17.11, pgjdbc 42.7.14)

- Test dymny kompozycji jedno- i dwuwęzłowej: bez błędów.
- Migracja PG14 → PG17 skryptem `postgres-migrate.sh`: liczby wierszy 147 tabel zgodne, odtwarzanie bez nieoczekiwanych błędów.
- Skrypty partycjonowania `01`–`07`: 0 błędów.
- `DatasetScenario`: 1/1.
- Wydajności nie mierzono (pomiar `mierz-indeks.py` po migracji klastra, porównanie z zadaniem 229).

## Do zrobienia

1. Autor: commit zmian, wydanie lokalne mercury 3.0.4.20 (README zakłada „3.0.4.20 and later”; poprawić, jeśli numer będzie inny).
2. Claude po sygnale: `set-versions.sh`, pakiet mercury-cmd, build obrazów (przed pushem zachować rollback: stary obraz PG14 jako `ibpm/postgres:mercury-hgdb-3.0-pg14`), smoke test, push do Nexusa.
3. Autor: migracja klastra na `devops-box-01` wg `docs/005_Configuration/PostgreSQL_upgrade` lub README bazy; potem pomiary.
4. Decyzje otwarte: wymiana jarów w katalogu dev-servera (obs. 161), test Helm (obs. 162).
