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

### 2. Obs. 167 (pomiar 2026-11-14, bez zmian w kodzie)

- Środowisko: kompozycja trzywęzłowa na `devops-box-01` (3.0.4.25), zapis `CaseBusinessExtRest/save` (typ `FsmComment`, magazyn `FSMServiceOrder`) w kontenerze `node1` z tokenem OAuth (`GIUSoapUIClient`, `admin`).
- Zdrowy klaster: 0,12–0,14 s. `node2` wstrzymany (`docker pause`): zapis nie kończy się w 100 s (kod 000). Po `unpause`: 0,14 s.
- Zrzut wątków: `StrongServerStoreProxy.performWaitingForHashInvalidation` → `ScStorageAccessImpl.putIntoCache` → `TimestampsCacheEnabledImpl.invalidate` → `ActionQueue.afterTransactionCompletion`. Przyczyna: `consistency="strong"` regionu `default-update-timestamps-region`.
- Skutek uboczny pomiaru: w bazie klastra są 3 nowe sprawy `FsmComment` z testu oraz nowa wersja typu `FsmComment` (typeId 202, było 107), a po niej kolejne zapisy testowe `t167`. Do sprzątnięcia przez autora, jeśli przeszkadzają.
- Nie sprawdzono: `consistency="eventual"` (wymaga zmiany we wszystkich klientach i ponownego utworzenia magazynu na serwerze Terracotta), węzeł faktycznie padły (zerwane TCP), limity po stronie serwera.

### 2a. Obs. 167: testy awarii klienta Terracotty (2026-11-14, `devops-box-01`)

Cel autora: problem jednego węzła nie może obciążać pozostałych (mogą pracować ciężej, ale nie czekać na niesprawny węzeł).

Osobny serwer Terracotta (obraz `mercury/terracotta:3.6.1`) i dwóch klientów Ehcache (zapisujący, trzymający klucz w heapie), region jak `default-update-timestamps-region` (heap 1000, clustered-dedicated 4 MB). Zapis co 1 s. Kod i skrypt: `/root/t167-wyniki/` na `devops-box-01`.

| Spójność | Dzierżawa | Awaria klienta | Max zapis | Wolne zapisy (>1 s) |
| :--- | :---: | :--- | ---: | ---: |
| strong | 150 s (domyślna) | brak | 7 ms | 0 |
| strong | 150 s | zamrożenie 10 s | 9683 ms | 1 |
| strong | 150 s | `kill` kontenera | 6 ms | 0 |
| strong | 150 s | `pause` | 10002 ms | 14 (ok. 140 s łącznie) |
| strong | 150 s | partycja (`iptables DROP`) | 10002 ms | 14 |
| eventual | 150 s | brak, `pause`, partycja, `kill` | 3–5 ms | 0 |
| strong | 20 s | `pause` | 10002 ms | 2 (ok. 20 s) |
| strong | 20 s | partycja | 10002 ms | 2 |

Prawdziwy pad na kompozycji trzywęzłowej: `docker kill` na `node2`, zapis `CaseBusinessExtRest/save` na `node1`: 0,12–0,16 s (bez zmiany). `node2` uruchomiony ponownie (`docker start`).

Wnioski: (1) pad z zamkniętym połączeniem nie przeszkadza; (2) zamrożona JVM albo partycja bez RST blokuje zapisy na `strong` do wygaśnięcia dzierżawy (domyślnie 150 s, każdy zapis do 10 s); (3) `eventual` całkowicie izoluje, ale nie nadaje się dla wszystkich pamięci; (4) `lease-length` w `tc-config.xml` skraca blokadę do swojej wartości, kosztem tego, że klient z przerwą (GC) dłuższą niż dzierżawa zostanie odcięty i musi się połączyć ponownie.
Do decyzji autora: wartość `lease-length` dla `ehcache/conf/1`, `conf/2`, `conf/3` oraz które regiony przestawić na `eventual`.
Pozostałości po teście: obraz `eclipse-temurin:8-jdk` na `devops-box-01`; w bazie klastra nowe sprawy i wersja typu `FsmComment` (zob. sekcja 2).
