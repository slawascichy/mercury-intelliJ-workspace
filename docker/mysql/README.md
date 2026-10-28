# MySQL dla Mercury DB (HgDB)

Kompozycja Docker z MySQL 8.4 do testów serwera i klientów na bazie MySQL (np. weryfikacja odczytu widoków z zadania 016).
Kompozycja tworzy trzy bazy zgodne z konfiguracją w repozytoriach: `mercury-db`, `mercury-common` i `mercury-ldap`.

## Uruchomienie

```bash
cd docker/mysql
cp .env.example .env     # ustaw hasła w .env (plik jest ignorowany przez git)
docker compose up -d
docker compose ps        # stan healthy po ok. 30-60 s
```

Zatrzymanie: `docker compose down`. Dane leżą w woluminie `mysql-data`. Pełne czyszczenie (usuwa dane i pozwala zmienić ustawienia inicjalizacji): `docker compose down -v`.

## Parametry

| Element | Wartość |
|---|---|
| Obraz | `mysql:8.4` |
| Adres | `127.0.0.1:3306` (port zmienia `MYSQL_PORT` w `.env`; port nasłuchuje tylko lokalnie) |
| Użytkownik | `mercury` (hasło z `MYSQL_PASSWORD`), pełne prawa na trzech bazach |
| Administrator | `root` (hasło z `MYSQL_ROOT_PASSWORD`) |
| Kodowanie | `utf8mb4`, porządkowanie `utf8mb4_unicode_ci` |
| Nazwy tabel | `lower_case_table_names=1` (małe litery, jak na Windows); ustawienie działa tylko przy pierwszej inicjalizacji katalogu danych |

Skrypty z katalogu `init` wykonują się tylko przy pierwszym uruchomieniu z pustym woluminem.

## Połączenie z testów

Klucze w `src/test/resources-filtered/properties/<użytkownik>/test-mysql.properties` (hasło wpisz lokalnie, nie zatwierdzaj go):

```properties
jdbc.mysql.default.dbUser=mercury
jdbc.mysql.default.dbPassword=<MYSQL_PASSWORD>
jdbc.mysql.default.dbPort=3306
jdbc.mysql.default.dbName=mercury-db
jdbc.mysql.default.dbServer=127.0.0.1
jdbc.mysql.common.dbUser=mercury
jdbc.mysql.common.dbPassword=<MYSQL_PASSWORD>
jdbc.mysql.common.dbPort=3306
jdbc.mysql.common.dbName=mercury-common
jdbc.mysql.common.dbServer=127.0.0.1
```

Adres JDBC: `jdbc:mysql://127.0.0.1:3306/mercury-db`. Sterownik MySQL Connector/J nie jest częścią tej kompozycji.

## Uwagi

- Testy `mercury` czyszczą bazę. Wskazuj je wyłącznie na tę bazę testową.
- Hasła nie są częścią repozytorium. W `.env.example` są tylko wartości zastępcze.
