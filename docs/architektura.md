# Architektura rozwiązania Mercury DB

## Warstwy

```mermaid
flowchart TB
    subgraph Klienci
        BPM[mercury-client<br/>IBM BPM]
        OPEN[hgdb-client-open<br/>klient Java CXF]
        CMD[mercury-cmd<br/>CLI, transfer, benchmark]
    end
    subgraph Serwer["mercury (Tomcat)"]
        APP[mercury-ws-app<br/>SOAP / REST / RMI]
        GUI[mercury-gui-registry<br/>GUI rejestru]
        WS[mercury-ws-server]
        SRV[mercury-srv / mercury-srv-slave<br/>logika i biznes]
        LUC[mercury-lucene-indexes]
        DAO[mercury-dao]
        CMIS[mercury-cmis-client]
    end
    subgraph Lib["mercury-lib (wspólne)"]
        CORE[mercury-core]
        ENT[mercury-entities]
        API[mercury-srv-api / mercury-ws-server-api / mercury-ws-dto-api]
    end
    DB[(RDBMS<br/>PostgreSQL / Oracle / MySQL / MSSQL / HSQL)]
    IDX[(Indeksy Lucene)]
    MQ[[ActiveMQ]]
    CACHE[[Ehcache Clustered]]
    ECM[(Repozytoria CMIS<br/>Alfresco, FileNet, SharePoint)]

    BPM --> OPEN
    OPEN -->|SOAP / HTTP invoker| APP
    CMD -->|SOAP| APP
    APP --> WS --> SRV
    GUI --> SRV
    SRV --> LUC --> IDX
    SRV --> DAO --> DB
    SRV --> CMIS --> ECM
    SRV <--> MQ
    DAO <--> CACHE
    Serwer -.-> Lib
    Klienci -.-> Lib
```

- **mercury-lib** to kontrakt współdzielony przez serwer i klientów: encje, interfejsy
  warstwy logiki i biznesu, interfejsy usług WS i obiekty DTO.
- **mercury** zawiera implementację tego kontraktu: dostęp do danych (Hibernate), indeksy
  Lucene, logikę biznesową, usługi CXF (SOAP/REST) i Spring remoting (RMI / HTTP invoker),
  GUI oraz aplikacje WAR uruchamiane w Tomcacie.
- **hgdb-client-open** to klient Java usług serwera. Obsługuje też wiele instancji (klaster).
- **Logowanie i sesje w klastrze:** REST nie potrzebuje sesji (token OAuth w bazie i cache współdzielonym, ważny na każdym węźle).
  Strony z formularzem logowania (GUI) używają sesji HTTP, więc przy LB z round-robin węzły replikują je przez Tomcat Cluster
  (`DeltaManager`, członkostwo statyczne), z `ClusterFormAuthenticator` w `mercury-gui-core` (zadanie 227). `ip_hash` na LB
  odrzucony: użytkownicy techniczni łączą się z jednego adresu i obciążaliby jeden węzeł.
- **mercury-client** i **mercury-cmd** to rozwiązania zbudowane na klientach: integracje
  z IBM BPM i narzędzia administracyjne.
- **mercury-docker** i **docusaurus-hgdb** nie zawierają kodu Java. Pierwsze definiuje obrazy
  i kompozycje do wdrożenia serwera, drugie to serwis [hgdb.org](https://hgdb.org)
  z dokumentacją API, konfiguracji i integracji z IBM BAW.

## Zależności między repozytoriami

| Repozytorium | Zależy od (repozytoria workspace) | Zależności zewnętrzne autora |
|---|---|---|
| mercury-lib | – | `sccommon-utils`, `sccommon-cache`, `sccommon-eclipse-emf-api` |
| mercury | mercury-lib | `sccommon-*` (utils, cache, ldap, mail, http-client, eclipse-emf-api), `ccrto-openapi`, `poi-toolkit` |
| hgdb-client-open | mercury-lib, mercury (`hgdb-rmi-server-api`) | `sccommon-utils`, `sccommon-cache`, `ccrto-openapi`, `poi-toolkit` |
| mercury-client (zamrożony) | mercury-lib 3.0.4.16, hgdb-client-open 3.0.3.3.0 (`hgdb-ws-client-cxf`, `hgdb-multi-client`, tranzytywnie `hgdb-rmi-server-api`) | `sccommon-utils` 1.0.8.4-jdk1.7, `sccommon-cache` 0.0.3-20180724, `tw4j` (z SecurityProvidera), biblioteki IBM BPM / WebSphere |
| mercury-cmd | mercury-lib, mercury, hgdb-client-open | `sccommon-*`, `ccrto-openapi` |

Biblioteki `sccommon`, `ccrto-openapi` i `poi-toolkit` też pochodzą od autora. Leżą
w `D:\workspace\git` (`sccommon`, `ccrto-openapi`, `poi-toolkit`), ale nie są częścią tego workspace.

Każde repozytorium ma własne lokalne repozytorium Maven (`<repo>/repo`), skonfigurowane
w `.idea/jarRepositories.xml`. Artefakty przekazuje się między projektami skryptami
`install.sh` / `deploy.sh` / `deploy-api.sh`. Repozytorium publiczne:
`https://nexusrepo.scisoftware.pl/repository/sci-maven-releases`.

## Kolejność budowania

1. **mercury-lib**, z parametrem wersji i dostawcy bazy:
   ```bash
   mvn clean install -Dmercury.static.version=<wersja> -Ddatabse.provider=POSTGRESQL -Dmaven.test.skip
   ```
2. **mercury** (serwer):
   ```bash
   mvn -U clean install -Dmaven.test.skip=true [-Ddatabse.provider=ORACLE|MYSQL]
   ```
3. **hgdb-client-open**:
   ```bash
   mvn $MAVEN_SETTINGS clean install -Dmaven.test.skip
   ```
4. **mercury-client**: wymaga dostępu do bibliotek IBM BPM. README zaleca Javę 1.6/1.7
   i Maven 2.2.1, a POM ustawia `java.version=1.8`. Moduł `mercury-client-cmd` buduje się
   osobno, z jego katalogu (`./install.sh`). Projekt jest zamrożony; opis w `mercury-client/README.md`.
5. **mercury-cmd**: buduje narzędzia oraz pakiet instalacyjny serwera.
6. **docusaurus-hgdb** (niezależnie od powyższych): `npm install && npm run build`.

Kolejność modułów w reaktorze `mercury` (z `mercury/README.md`):
core-server → entities-ids → dao-api → mock → dao → cmis-client → lucene-indexes-api →
lucene-indexes → srv → ws-server-api20-generator → ws-server-api20 → ws-server → gui-core →
gui-registry → srv-slave → ws-app-rest-generator → ws-app → server.

## Dostawca bazy danych

Encje i biblioteki buduje się osobno dla każdego dostawcy RDBMS. Steruje tym właściwość
`databse.provider` (nazwa z literówką, celowo zachowana w POM-ach):
`POSTGRESQL` (domyślny), `ORACLE`, `MYSQL`, `MSSQL`, `HSQL`.
Na tej podstawie powstaje wersja artefaktu encji, np. `mercury-entities.version=${databse.provider}-${mercury.static.version}`.

## Wersjonowanie

Wersja ma pięć pozycji (opis z `mercury-lib/README.md`):

1. i 2. Wartości specyficzne dla produktu. Ich zmiana oznacza zmianę nazwy produktu.
3. Poważna zmiana: nowe podejście, aktualizacja Javy i zależności. Wymaga aktualizacji klientów i serwera.
4. Zmiana API (SOAP lub REST). Wymaga aktualizacji klientów i serwera.
5. Drobna zmiana. Wymaga aktualizacji tylko po stronie serwera.

## Stos technologiczny (wg POM-ów)

| Obszar | mercury (serwer) | mercury-lib | hgdb-client-open | mercury-client |
|---|---|---|---|---|
| Java | 1.8 | 1.8 | 1.8 | 1.8 wg POM (README: 1.6 / 1.7) |
| Spring | 5.3.21 | 2.5.6 | 5.3.21 | 4.1.9.RELEASE |
| Apache CXF | 3.0.12 | 3.0.12 | 3.0.12 | 2.7.15 |
| Hibernate | 5.6.14.Final | – (JPA 2.1) | – | – |
| Lucene | 7.5.0 | – | – | – |
| Ehcache | 3.6.1 | 3.6.1 | 3.6.1 | 2.10.1 |
| Logowanie | slf4j 1.7.36 + Logback 1.2.13 | slf4j 1.7.36 + Logback 1.2.13 | slf4j 1.7.36 + Logback 1.2.13 | slf4j 1.7.36 + Logback 1.2.13 |
| Serwer aplikacji | Tomcat 8.0.32 (`mercury-server`) | – | – | IBM WebSphere 8.5.5 |
| Inne | ActiveMQ 5.16, OpenCMIS 1.1.0, POI 5.2.1, Jackson 2.18.11, commons-io 2.14.0 | POI 5.2.1, Jackson 2.18.11, commons-io 2.14.0 | Jackson 2.18.11, commons-io 2.14.0 | IBM BPM 8.6.3, Axis 1.4 |
