# [241] Weryfikacja obserwacji po wykonaniu zadania #236

https://github.com/slawascichy/hgdb/issues/241

Weryfikacja obserwacji po wykonaniu zadania #236:
1. Obs. 165, kolejność startu chartu Helm. Trzeba zdecydować, czy poprawiać. Opcje to initContainers czekające na 
   postgres-db, activemq i ehcache-node1 albo probe w szablonach 04, 07, 08 i 09. Klaster k8s-master (mercury-test) jest do dyspozycji.
2. Obs. 167, klastrowy cache Hibernate w transakcji. Sprawdzić konfigurację Ehcache w klastrze i zmierzyć wpływ wolnego węzła na czas transakcji.
3. Drobne pozostałości:   - smoke jednowęzłowy po max_connections=250,   - na dev-serverze wywołać CaseViewDefinitionRest/checkManagePrivileges i markGenerationFailed (z użytkownikiem z uprawnieniami i bez) i sprawdzić, że w logu nie ma błędów PG17.

## Postęp

### 1. Obs. 165 (zrobione 2026-11-14, gałąź `hgdb-241` w `mercury-docker`, bez commita)

- `charts/mercury-single-node/templates/_helpers.tpl`: `initContainer` `wait-for-dependencies` (obraz głównego kontenera, `bash` i `/dev/tcp`).
- Szablon 07 czeka na `postgres-db:5432`; 08 na `activemq:61616`, `ehcache-node1:9410`, `openldap:389`; 09 na PostgreSQL, ActiveMQ, Ehcache, LDAP i `poi-server-node1:10090`.
- `values.yaml`: `resources.requests.memory` dla wszystkich komponentów, bez `limits`. Powód: `mercury-node1` (JVM `-Xmx4098m`, ok. 3,9 GB) ginął z `OOMKilled`, gdy scheduler upakował pody na jednym workerze (5,4 GB).
- Test na `mercury-test` (`helm upgrade` rewizje 3 i 4, `scale 0` i `1`): 0 restartów, `/mercury-ws-app/rest/openapi.json` 200. Rozkład: worker1 93% requests, worker2 16%.
- RAM workerów zwiększony do 6,4 GB (master 3,2 GB). Zimny start 2026-11-14 powtórzony: 0 restartów, `openapi.json` 200. Rozkład: worker2 88% requests (`mercury-node1`, `activemq`, `ehcache`, `postgres`, LB), worker1 3% (`openldap`, `poi-server`); scheduler nie równoważy przy jednoczesnym starcie, ale wszystko się mieści.

### Do zrobienia

- Obs. 167 oraz drobne pozostałości (pkt 2 i 3).
- Commit w `mercury-docker` (gałąź `hgdb-241`) i w workspace robi autor.
