# Podsumowanie 2026-11-06

## Zamknięte

- **229 Adaptacyjne przekazywanie dokumentów Lucene w klastrze:** merge PR #231 (mercury), #4 (mercury-cmd), #3 (mercury-docker). Czas do indeksu najpóźniejszego węzła spadł o 60–67% (100 spraw: 826 → 322 ms, 3 × 100: 1654 → 549 ms). Opisy i pomiary: `229-…/TASK.md`.
- **Poprawki z 226 i 229:** obs. 156 (`mercury-transfer`), 157 (skrypty pomiarowe), 158 (`max_connections`, Helm); `defaultAutoCommit="false"` w szablonie `context.xml`.
- **Docusaurus:** dokumentacja nowych parametrów (indeks Lucene, cache, nowa strona połączeń z bazą), EN i PL. Gałąź `hgdb-229`, niezacommitowane.

## Zadanie 232: PostgreSQL 14 → 17 (w toku)

- Decyzje autora: wersja 17, wymiana sterownika JDBC w tym zadaniu, migracja klastra z instrukcją.
- Zmiany: obraz bazy 17.11, pgjdbc 42.7.14 (serwer, ActiveMQ, zależność testowa), `bin/postgres-migrate.sh`, README, strona docusaurus `PostgreSQL_upgrade` (EN, PL), obserwacje 161–162.
- Testy: smoke jedno- i dwuwęzłowy (0 błędów), migracja 147 tabel zgodna, partycjonowanie 0 błędów, `DatasetScenario` 1/1.
- **Wydanie 3.0.4.20:** pakiet w Nexusie (raw), obrazy w `docker-hosted`: `ibpm/mercury:mercury-hgdb-3.0.4.20`, `ibpm/postgres:mercury-hgdb-3.0` (PG 17.11), `ibpm/activemq:mercury-hgdb-3.0`, plus rollback `ibpm/postgres:mercury-hgdb-3.0-pg14`. Wysyłka przerwana awarią Dockera, dokończona po restarcie.
- Sprzątanie: lokalne obrazy `ibpm/mercury` 3.0.4.13–18 usunięte (w Nexusie zostają 14–20); lokalnie 3.0.4.19 i 20.

## Niezacommitowane

- mercury-docker i mercury-cmd: podbicie wersji na 3.0.4.20 (`set-versions.sh --apply`).
- workspace: `docs/obserwacje.md`, `tasks/hgdb/232-…/`, to podsumowanie i plan.
- docusaurus-hgdb: nowe strony w gałęzi `hgdb-229`.

## Uwaga operacyjna

Tag `mercury-hgdb-3.0` bazy w Nexusie wskazuje teraz PostgreSQL 17. Kompozycja ściągająca nowy obraz na starym katalogu danych PG14 nie wystartuje, dopóki dane nie zostaną zmigrowane.
