# mercury-lib – Mercury Main Library

| | |
|---|---|
| Lokalizacja | `D:\workspace\git\mercury-lib` |
| GAV | `io.hgdb.mercury:mercury-lib:3.0.4-SNAPSHOT` (pom) |
| Java | 1.8 |
| Opis z POM | Zbiór głównych komponentów systemu bazy danych Mercury DB. |

Biblioteki współdzielone przez serwer (`mercury`) i klientów (`hgdb-client-open`,
`mercury-client`, `mercury-cmd`). Definiują model encji i kontrakty usług.

## Moduły

| Moduł | Nazwa | Pliki Java (main / test) | Główne pakiety | Opis |
|---|---|---|---|---|
| `mercury-core` | Core | 500 / 32 | `pro.ibpm.mercury.entities`, `.attrs`, `.exceptions` | Abstrakcje i klasy narzędziowe: bazowe typy encji, atrybuty, wyjątki. Nie zależy od innych modułów. |
| `mercury-entities-dto-generator` | Entities DTO Generator | 9 / 0 | `pro.ibpm.mercury.entities` | Generator źródeł i kompilacji klas DTO na podstawie klas encji. |
| `mercury-entities` | Entities | 210 / 2 | `pro.ibpm.mercury.entities`, `.values` | Implementacje encji. Część źródeł jest generowana do `src/main/generated`. |
| `mercury-srv-api` | SRV API | 181 / 13 | `pro.ibpm.mercury.logic`, `pro.ibpm.mercury.business` | Interfejsy warstwy logiki (logic) i biznesu (business). |
| `mercury-ws-dto-api` | WS DTO API | 330 / 4 | `pro.ibpm.mercury.ws`, `pro.ibpm.mercury.dto` | Obiekty transportowe (DTO) usług SOAP, częściowo generowane. |
| `mercury-ws-server-api` | WS Server API | 75 / 3 | `pro.ibpm.mercury.ws`, `org.mercury.ws.server` | Interfejsy usług SOAP i REST (CXF). |
| `mercury-spring-remoting` | Spring remoting | 10 / 1 | `org.spring4hgdb.remoting.httpinvoker` | Kopia wycofanego ze Springa HTTP invokera, potrzebna do zdalnych wywołań klient–serwer. |

## Zależności wewnętrzne

```mermaid
flowchart LR
    core[mercury-core]
    gen[mercury-entities-dto-generator] --> core
    ent[mercury-entities] --> core
    ent --> gen
    srvapi[mercury-srv-api] --> core
    srvapi --> ent
    dto[mercury-ws-dto-api] --> core
    dto --> ent
    dto --> gen
    dto --> srvapi
    wsapi[mercury-ws-server-api] --> dto
    wsapi --> srvapi
    remoting[mercury-spring-remoting]
```

## Katalogi tłumaczeń opisów OpenAPI

Zadanie 192 ([TASK.md](../../tasks/hgdb/192-Lokalizacja-opisow-specyfikacji-i-tekstow-stalych/TASK.md)):

- `mercury-ws-server-api/src/main/resources/META-INF/mercury/openapi-docs_<lang>.properties` (pl, en, de, es, fr, ko; po 3325 kluczy) to
  tłumaczenia opisów z `@WSDLDocumentation` interfejsów `I*Action`. Klucze: `Interfejs`, `Interfejs.metoda`,
  `Interfejs.metoda.param.<nazwa z @WebParam>`, `Interfejs.metoda.returns`. Adnotacje zostają źródłem tekstu domyślnego (dziś polskiego),
  więc WSDL się nie zmienia. Pliki są w UTF-8 (surowe znaki), a serwer i generator łączą wszystkie zasoby języka z classpath.
- `mercury-core` (`org.mercury.docs.OpenApiDocsExtractor`) to narzędzie jednorazowej migracji: JavaParser wyciąga opisy z adnotacji do
  pliku `.properties`; bez `--overwrite` nie nadpisuje istniejącego pliku, a przy nadpisaniu zostawia kopię `.bak-<czas>`.
- `SchemaDocsGenerator` (`pro.ibpm.mercury.docs`, `mercury-core`) zapisuje podczas budowy Javadoc klas do `META-INF/mercury/schema-docs.json`.
- Wydanie 3.0.4.8 (2026-10-21) zawiera katalogi; kolejne zmiany tekstów wymagają wydania biblioteki (`minor_version.txt`, tag lekki z numerem wydania).

## Budowanie

```bash
mvn clean install -Dmercury.static.version=3.0.2.0.2 [-Dmaven.test.skip] [-Ddatabse.provider=ORACLE]
```

- `install.sh` instaluje biblioteki dla wszystkich dostawców baz do `repo/io/hgdb/mercury`.
- `deploy.sh` publikuje je do repozytorium zdalnego (Nexus SCI Software).
- `up_major_version.sh` i `up_minor_version.sh` podnoszą wersję (`major_version.txt`, `minor_version.txt`).
- Wygenerowane źródła usuwa się ręcznie: `mercury-entities/src/main/generated/pro`, `mercury-ws-dto-api/src/main/generated/pro`.

Źródło: `mercury-lib/README.md`.
