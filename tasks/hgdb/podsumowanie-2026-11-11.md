# Podsumowanie 2026-11-11

## Zamknięte i wydane

- **Obs. 161 (sterownik JDBC w pakiecie i dev-serverze):** pakiet `mercury-cmd` bierze `postgresql-42.7.14.jar` z zależności Maven (`postgresql.jdbc.version`), `mercury-srv-cmd` też (było 42.3.3), jary w dev-serverze (`apache-tomcat/mercury/lib`, `apache-tomcat/jdbcdrivers`, `apache-activemq-5.16.4/lib`) wymienione (stare w `D:\workspace\jdbc-backup-2026-11-11`), zależność testowa w `mercury-lib` 42.5.1 → 42.7.14. PR `mercury-cmd` #6 zmergowany.
- **Lokalny PostgreSQL 13 → 17:** dump (`pg_dumpall --globals-only`, `pg_dump -Fc` sześciu baz) w `D:\PostgreSQL\backup-pg13-2026-11-11`, PG 17.11 na porcie 5432, odtworzenie bez błędów, liczby wierszy zgodne. Na PG15+ rola `mercury` dostała `GRANT CREATE ON SCHEMA public` w pięciu bazach (inaczej `CaseViewCreator` nie tworzył widoków). Dev Tomcat działa na PG17 i nowym sterowniku.
- **Obs. 158** zamknięta, **163** (dopasowanie `maxTotal` do `max_connections`) wydzielona.
- **Zadanie 234 (NPE w `MainController`):** przyczyna to zły warunek w `MercuryConfig.getDateLoggerFormat()` (sprawdzał `dateLongFormat`); poprawka i `MercuryConfigFormatsTest` w `mercury-lib`, wydanie lib 3.0.4.23.
- **Ujednolicenie wersji zależności** (`mercury-lib`, `mercury`, `hgdb-client-open`, `mercury-cmd`): `sccommon` 2.0.0.4, CXF 3.0.12, Jackson 2.18.11, `commons-io` 2.11.0, Spring 5.3.21 (poza lib: 2.5.6), Xerces 2.12.2 (zamiast zakresów otwartych).
- **Naprawa klienta po zadaniu 016:** `markGenerationFailed` i `checkManagePrivileges` dodane do usługi zdalnej (`ICaseViewDefinitionAction`), serwer (`CaseViewDefinitionAction`, `markGenerationFailed` ze sprawdzeniem uprawnień) i klient; opisy OpenAPI w sześciu językach (translator `openapi_docs_sync.py`), `openapi*.json` z nowymi endpointami.
- **Wydania:** `mercury-lib` 3.0.4.23 i 3.0.4.24, `mercury` 3.0.4.21 i 3.0.4.22, `hgdb-client-open` 3.1.4.20. W Nexusie: pakiety i obrazy `ibpm/mercury:mercury-hgdb-3.0.4.21` i `3.0.4.22` (22 z klientem 3.1.4.20, smoke 0 błędów jedno- i dwuwęzłowo). Lokalnie obrazy 3.0.4.21 i 3.0.4.22.

## Do wiedzy

- **Ujednolicenie zmienia decyzję z 2026-10-27:** `hgdb-client-open` jest teraz na `sccommon` 2.0.0.4, a SecurityProvider (IBM BPM) nie kompilował się nawet na 2.0.0.1. Nie sprawdzano zgodności stosu cache klienta z BPM.
- Dependabot podbił w kliencie `commons-io` do 2.14.0, reszta projektów ma 2.11.0 (dryf).
- Generator OpenAPI zgłasza brak klucza `schema.CaseHeader.isDocumentType` (obs. 164).
- Dev-server: `ehcache.properties` nie znaleziony (stary wpis) i connector AJP 8009 bez `secret` (niezwiązane z PG).
- Hasło `postgres` lokalnego PG17 (i PG13) pojawiło się w rozmowie, do zmiany.
- Numeracja wydań: `minor_version.txt` bywał resetowany niżej niż wydane tagi (notatka w pamięci `numeracja-wydan-mercury`).

## Niezacommitowane

- workspace: `docs/obserwacje.md` (obs. 163, 164), `tasks/hgdb/234-…/`, plany i podsumowania (ten plik, `plan-2026-11-12.md`), poprawka dat w `232-…/TASK.md`.
