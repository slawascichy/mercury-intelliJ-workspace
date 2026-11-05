# Warianty B i C zadania 226

Obie zmiany robi się bez przebudowy obrazu: plik z tego katalogu podmontowany do węzłów aplikacji (`mercury-node1..3`).
Tylko jeden wariant naraz. Wszystkie trzy węzły muszą mieć tę samą konfigurację (inaczej różne regiony Ehcache w klastrze).

## Wariant B: lokalny `default-update-timestamps-region`
`B/ehcacheDefault.xml` = plik z obrazu 3.0.4.15 bez `terracotta:clustered-dedicated` i `terracotta:clustered-store` w regionie
`default-update-timestamps-region` (jedyna różnica). Zmiana tylko do pomiaru: bez klastrowych znaczników czasu węzły nie
unieważniają sobie nawzajem wyników zapytań, więc nie nadaje się na produkcję bez wyłączenia pamięci zapytań.

## Wariant C: pamięć zapytań Hibernate wyłączona
`C/database-postgresql.properties` = plik z obrazu z `hibernate.cache.use_query_cache=false` (jedyna różnica). Plik jest w
`/opt/mercury-3.0/classes/mercury-ws-app/` (nie w `-D`: Spring czyta właściwości z pliku).

## Uruchomienie (devops-box-01, katalog z docker-compose.yml klastra)
```bash
cp <wariant>/{ehcacheDefault.xml|database-postgresql.properties} <wariant>/docker-compose.override.yml .
docker compose up -d --force-recreate mercury-node1 mercury-node2 mercury-node3
# po starcie: dokładnie jeden MASTER, potem pomiar
rm docker-compose.override.yml <plik>        # powrót do wariantu A; znów --force-recreate węzłów
```
