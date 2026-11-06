# PostgreSQL: limit połączeń (`max_connections`) w klastrze Mercury DB

Przy kilku węzłach Mercury domyślny limit PostgreSQL (`max_connections = 100`) przestaje wystarczać. Węzły otwierają połączenia z jednej bazy, a każda pula Tomcata sama nie widzi limitu serwera. Objaw pojawia się dopiero przy większej współbieżności zapisów, więc łatwo go przeoczyć w testach na jednym węźle.

## Objaw

Zapis (np. REST `CaseBusinessRest/save`) kończy się błędem serwera:

```text
M0001#node1.<id> This is Throwable message. : FATAL: sorry, too many clients already
```

W zadaniu 226 (klaster trzywęzłowy na `devops-box-01`) wystąpił, gdy trzy węzły przyjmowały jednocześnie po 8 równoległych zapisów (24 żądania). Pojedyncze żądania i zapisy kierowane do jednego węzła przechodziły.

## Przyczyna

Obraz `ibpm/mercury` (`apache-tomcat/conf/context.xml`) definiuje pule połączeń JDBC osobno dla trzech baz:

| źródło danych | baza | `maxTotal` | `minIdle` |
|---|---|---|---|
| `jdbc/MercuryDB` | `mercury-db` | 140 | 30 |
| `jdbc/MercuryDBCommon` | `mercury-common` | 40 | 5 |
| `jdbc/MercuryLdapDBPoSql` | `mercury-ldap` | 20 | 1 |
| razem na węzeł | | **200** | 36 |

Przy trzech węzłach teoretyczny maksimum to 3 × 200 = 600 połączeń, a PostgreSQL ma domyślne `max_connections = 100`. Od 2026-11-06 kompozycje dwu- i trzywęzłowa w `mercury-docker` uruchamiają `postgres-db` z `max_connections=400` (`command: ["postgres", "-c", "max_connections=400"]`), a README kompozycji opisuje ten limit; dla innych wdrożeń (Helm, instalacje bez kompozycji) trzeba go ustawić samemu. Dochodzą połączenia narzędzi administracyjnych i `superuser_reserved_connections` (domyślnie 3).

## Ile ustawić

- Minimum, które pokrywa realne obciążenie z pomiaru zadania 226: **400** (trzy węzły, 24 równoległe zapisy wyczerpywały 100).
- Pełny zapas dla trzech węzłów to ok. 600 + rezerwa, ale każde połączenie zajmuje kilka MB pamięci serwera (`work_mem` i pamięć procesu), więc nie ustawiaj więcej, niż potrzeba.
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
- Obserwacja 158 w `docs/obserwacje.md`: wpis w README kompozycji `mercury-docker` i dopasowanie pul.

Źródło: `mercury-docker/mercury-3.0/docker-init-config/apache-tomcat/conf/context.xml` (pule), pomiar zadania 226 (błąd i obciążenie).
