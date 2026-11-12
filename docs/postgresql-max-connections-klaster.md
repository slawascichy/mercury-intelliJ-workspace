# PostgreSQL: limit połączeń (`max_connections`) w klastrze Mercury DB

Przy kilku węzłach Mercury domyślny limit PostgreSQL (`max_connections = 100`) przestaje wystarczać. Węzły otwierają połączenia z jednej bazy, a każda pula Tomcata sama nie widzi limitu serwera. Objaw pojawia się dopiero przy większej współbieżności zapisów, więc łatwo go przeoczyć w testach na jednym węźle.

## Objaw

Zapis (np. REST `CaseBusinessRest/save`) kończy się błędem serwera:

```text
M0001#node1.<id> This is Throwable message. : FATAL: sorry, too many clients already
```

W zadaniu 226 (klaster trzywęzłowy na `devops-box-01`) wystąpił, gdy trzy węzły przyjmowały jednocześnie po 8 równoległych zapisów (24 żądania). Pojedyncze żądania i zapisy kierowane do jednego węzła przechodziły.

## Przyczyna

Obraz `ibpm/mercury` (`apache-tomcat/conf/context.xml`) definiuje pule połączeń JDBC osobno dla trzech baz. Od wersji 3.0.4.23 (2026-11-12) wartość `maxTotal` każdej puli ustawia zmienna środowiskowa obrazu (domyślnie jak w tabeli):

| źródło danych | baza | zmienna | `maxTotal` (domyślnie) | `minIdle` |
|---|---|---|---|---|
| `jdbc/MercuryDB` | `mercury-db` | `POSTGRESQL_POOL_MAX_TOTAL` | 140 | 30 |
| `jdbc/MercuryDBCommon` | `mercury-common` | `POSTGRESQL_POOL_COMMON_MAX_TOTAL` | 40 | 5 |
| `jdbc/MercuryLdapDBPoSql` | `mercury-ldap` | `POSTGRESQL_POOL_LDAP_MAX_TOTAL` | 20 | 1 |
| razem na węzeł | | | **200** | 36 |

Wartość musi być dodatnią liczbą całkowitą, inaczej węzeł nie startuje. PostgreSQL ma domyślne `max_connections = 100`, więc już jeden węzeł z pulami domyślnymi (200) mógłby go przekroczyć, a trzy węzły dają teoretyczne maksimum 600. Dochodzą połączenia ActiveMQ (`jdbcPersistenceAdapter`), narzędzi administracyjnych i `superuser_reserved_connections` (domyślnie 3).

Kompozycje w `mercury-docker` dopasowują pule i limit (stan z 2026-11-12; pule można nadpisać w `.env` kompozycji):

| kompozycja | `maxTotal` (główna, wspólna, uwierzytelnianie) | na węzeł | razem | `max_connections` |
|---|---|---|---|---|
| jeden węzeł | 140, 40, 20 | 200 | 200 | 250 |
| dwa węzły | 120, 40, 20 | 180 | 360 | 400 |
| trzy węzły | 85, 25, 15 | 125 | 375 | 400 |

Do 2026-11-06 kompozycje wielowęzłowe nie ustawiały limitu (domyślne 100), a pule były stałe (140, 40, 20). Dla innych wdrożeń (Helm, instalacje bez kompozycji) limit trzeba ustawić samemu.

## Ile ustawić

- Minimum, które pokrywa realne obciążenie z pomiaru zadania 226: **400** (trzy węzły, 24 równoległe zapisy wyczerpywały 100).
- Pomiar 3 × 100 z pulami 85/25/15 przy limicie 400 (zadanie 232, 2026-11-12, klaster 3.0.4.23): czas do indeksu 367–417 ms, bez pogorszenia względem pul 140/40/20.
- Każde połączenie zajmuje kilka MB pamięci serwera (`work_mem` i pamięć procesu), więc nie ustawiaj więcej, niż potrzeba.
- Zasada: `max_connections` ≥ liczba węzłów × suma `maxTotal` pul **albo** zmniejsz `maxTotal` w `context.xml`, żeby suma pul wszystkich węzłów mieściła się w limicie. Dla większych klastrów rozważ pulę pośrednią (np. PgBouncer).

## Jak zmienić na działającym klastrze (bez zmiany kompozycji)

Zmiana wymaga **restartu** PostgreSQL; samo przeładowanie konfiguracji nie wystarcza. Parametr ustawia się w `postgresql.conf` (nie w `pg_hba.conf`, który dotyczy tylko uwierzytelniania).

```bash
# na hoście z kompozycją; nazwa kontenera i użytkownik wg `docker ps` i konfiguracji
docker exec postgres-db psql -U <superużytkownik> -c "ALTER SYSTEM SET max_connections = 400;"
docker restart postgres-db
docker exec postgres-db psql -U <superużytkownik> -c "SHOW max_connections;"
```

`ALTER SYSTEM` zapisuje wartość w `postgresql.auto.conf` w katalogu danych (wolumen `postgres-db`), więc przetrwa odtworzenie kontenera. Można też dopisać `max_connections = 400` na końcu `postgresql.conf` w katalogu danych; plik `postgresql.auto.conf` ma pierwszeństwo.

Po restarcie bazy zrestartuj węzły Mercury (`mercury-node1..3`), żeby pule JDBC otwarły połączenia od nowa, i poczekaj na jednego MASTER.

## Jak sprawdzić zajęcie połączeń

```sql
SELECT datname, count(*) FROM pg_stat_activity GROUP BY datname ORDER BY 2 DESC;
SHOW max_connections;
```

Wartość bliska limitu przy zwykłym ruchu oznacza, że trzeba podnieść `max_connections` albo obniżyć `maxTotal`.

## Powiązane

- Zadanie 226 (pomiar zapisu na Linuksie): `tasks/hgdb/226-Pomiar-zapisu-na-Linuksie-Tomcat-Terracotta/TASK.md`.
- Obserwacje 158 i 163 w `docs/obserwacje.md`: wpis w README kompozycji `mercury-docker` i dopasowanie pul (163: zmienne `POSTGRESQL_POOL_*_MAX_TOTAL`).
- Dokumentacja użytkowa: `docusaurus-hgdb`, strona `Database_connections`.

Źródło: `mercury-docker/mercury-3.0/docker-init-config/apache-tomcat/conf/context.xml.docker-init` i `bin/mercury-server.sh` (pule), kompozycje `mercury-docker/*/docker-compose.yml` (limity), pomiary zadań 226 i 232.
