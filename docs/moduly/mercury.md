# mercury – Mercury DB (serwer)

| | |
|---|---|
| Lokalizacja | `D:\workspace\git\mercury` |
| GAV | `io.hgdb:mercury:3.0.4.8` (pom) |
| Java | 1.8 |
| Opis z POM | System uniwersalnego źródła danych. |

Implementacja serwera Mercury DB: dostęp do danych, indeksowanie Lucene, logika biznesowa,
usługi SOAP/REST/RMI, GUI administracyjne i aplikacje WAR uruchamiane w Apache Tomcat.
Moduły mają GAV `io.hgdb.mercury:<moduł>:3.0.4.8`, chyba że w tabeli podano inaczej. Wersja projektu jest równa wersji
biblioteki `mercury-lib` (`mercury.static.version`) i trafia do `info.version` specyfikacji OpenAPI.

Wersja 3.0.4.2 zmienia format XML modelu obiektu MRC (przestrzenie nazw) i dodaje kontrolę wersji węzłów klastra.
Opis zmian i kolejność wdrożenia: [wydanie 3.0.4.2](../wydanie-3.0.4.2.md).

## Moduły

### Rdzeń serwera i dane

| Moduł | Typ | Java (main / test) | Opis |
|---|---|---|---|
| `mercury-core-server` | jar | 187 / 70 | Abstrakcje i klasy narzędziowe serwera: konektory (`pro.ibpm.mercury.connectors`), filtry, bazowe DAO. |
| `mercury-entities-ids` | jar | 59 / 18 | Sekwencje i generatory unikalnych identyfikatorów encji, predefiniowane atrybuty i wartości. |
| `mercury-dao-api` | jar | 92 / 1 | API warstwy DAO. |
| `mercury-dao` | jar | 195 / 32 | Implementacja DAO (Hibernate), filtry, cache DAO (`org.mercury.caches.dao`). |
| `mercury-mock` | jar | 90 / 30 | Generatory danych testowych serwera. |

### Wyszukiwanie i integracje

| Moduł | Typ | Java (main / test) | Opis |
|---|---|---|---|
| `mercury-lucene-indexes-api` | jar | 71 / 2 | API obsługi indeksów Lucene. |
| `mercury-lucene-indexes` | jar | 119 / 38 | Definicje indeksów, wyszukiwanie i budowanie zapytań Lucene (`org.mercury.lucene.search`, `.query`). |
| `mercury-cmis-client` | jar | 7 / 3 | Komunikacja z repozytoriami dokumentów CMIS (Alfresco, FileNet, SharePoint) przez Apache Chemistry OpenCMIS. |

### Logika biznesowa

| Moduł | Typ | Java (main / test) | Opis |
|---|---|---|---|
| `mercury-srv` | jar | 451 / 82 | Logika (logic) i biznes (business), obsługa JMS (`org.mercury.logic.jms`), dane biznesowe. Największy moduł serwera. |
| `mercury-srv-slave` | jar | 69 / 16 | Logika w trybie SLAVE: węzły klastra (`org.mercury.cluster.node`), serwer slave, rejestr. |

### Usługi sieciowe

| Moduł | Typ | Java (main / test) | Opis |
|---|---|---|---|
| `mercury-ws-server` | jar | 99 / 6 | Implementacje usług SOAP i RMI (CXF). |
| `mercury-ws-server-api20` | jar | 75 / 0 | API usług zgodne z Mercury 2.0 (kompatybilność wsteczna). |
| `mercury-ws-server-api20-generator` | jar | 7 / 2 | Generator interfejsów API 2.0 z interfejsów Mercury 3.0 (`mercury-ws-server-api`). |
| `mercury-ws-app-rest-generator` | jar | 14 / 6 | Generator usług REST na podstawie implementacji SOAP oraz specyfikacji OpenAPI 3.1 (`openapi.json`) z opisami usług, operacji i schematów. |
| `hgdb-rmi-server-api` | jar | 18 / 11 | API usług RMI (`org.spring4hgdb.remoting.rmi`). Używa go również klient `hgdb-multi-client`. |

### Aplikacje i GUI

| Moduł | Typ | Java (main / test) | Opis |
|---|---|---|---|
| `mercury-ws-app` | **war** | 225 / 6 | Główna aplikacja WWW serwera: usługi SOAP, REST i RMI, dokumentacja WADL, specyfikacja OpenAPI i Swagger UI (patrz „OpenAPI i Swagger UI”), bindingi serwera CMIS. |
| `mercury-gui-core` | jar | 78 / 11 | Baza aplikacji prezentacyjnych: Tomcat Realm łączący użytkowników z RDBMS i LDAP, OAuth 2.0; `org.mercury.gui.auth.ClusterFormAuthenticator` (logowanie FORM z replikacją sesji Tomcat Cluster przy LB z round-robin, zadanie 227; wymaga Tomcata 9.0.x, wersja kompilacji w `tomcat.version` rodzica). Wspólny szablon prezentacji `mercury-ws-app` i `mercury-gui-auth` (`src/main/ui-template`: pasek z językiem i menu użytkownika, stopka, CSS; kopiowany do obu WAR-ów w `pom.xml`, bo biblioteka leży w lib Tomcata) oraz `org.mercury.gui.auth.SharedLogin` (wspólny formularz logowania, zadanie 96). |
| `mercury-gui-registry` | **war** | 5 / 0 | GUI rejestru do zarządzania modułami Mercury DB (JSP/JSTL). |
| `mercury-gui-auth` | **war** | 50 / 15 | GUI zarządzania uwierzytelnianiem i autoryzacją (zadanie 96; JSP, Spring MVC): lokalni użytkownicy i profil (`MRC_LDAP_INT_USERS`), mapowania ról (`MRC_LDAP_INT_ROLES_MAP`), przegląd LDAP (tylko odczyt), klienci i tokeny OAuth z podglądem sekretu po ponownym podaniu hasła, własny klucz licencji (`MRC_LDAP_LICENSE_KEYS`, tryb tylko do odczytu po wygaśnięciu), wspólny formularz logowania i SSO. Dane przez JDBC na `jdbc/MercuryLdapDBPoSql`. Opis dla użytkowników: `010_GUI_Application_overview` w docusaurus-hgdb. |
| `license-registry` | **war** | 1 / 1 | Rejestr licencji. GAV: `io.hgdb:license-registry`. |
| `ROOT` | **war** | 0 / 0 | Aplikacja ROOT Tomcata. GAV: `io.hgdb:ROOT:3.0.1-SNAPSHOT`, bez rodzica. |

### Narzędzia i dystrybucja

| Moduł | Typ | Java (main / test) | Opis |
|---|---|---|---|
| `hgdb-tools` | jar | 3 / 3 | Narzędzia, m.in. obsługa licencji (`org.hgdb.tools.license`). |
| `hgdb-server-monitor` | jar | 1 / 0 | Monitoring pracy serwera. |
| `mercury-server` | jar | 0 / 0 | Testowy serwer Tomcat 8.0.32 z ActiveMQ, konfiguracją i bibliotekami. Baza wersji produkcyjnej. GAV: `io.hgdb:mercury-server`. |

## Zależności (uproszczone)

```mermaid
flowchart BT
    lib[(mercury-lib)]
    cs[mercury-core-server] --> lib
    ids[mercury-entities-ids] --> cs
    daoapi[mercury-dao-api] --> cs
    daoapi --> ids
    dao[mercury-dao] --> daoapi
    cmis[mercury-cmis-client] --> dao
    lapi[mercury-lucene-indexes-api] --> daoapi
    luc[mercury-lucene-indexes] --> lapi
    luc --> dao
    srv[mercury-srv] --> luc
    srv --> cmis
    ws[mercury-ws-server] --> srv
    ws --> rmi[hgdb-rmi-server-api]
    slave[mercury-srv-slave] --> ws
    gui[mercury-gui-core] --> cs
    app[mercury-ws-app] --> slave
    app --> gui
    app --> restgen[mercury-ws-app-rest-generator]
    reg[mercury-gui-registry] --> gui
    server[mercury-server] --> app
    server --> reg
```

## OpenAPI i Swagger UI

Dokumentacja usług REST (zadanie 133, [etap 1](../../tasks/hgdb/133-Swagger-implementacja/etap-1-openapi-statyczne.md)):

- **Specyfikacja.** OpenAPI 3.1 powstaje przy budowie w `mercury-ws-app-rest-generator` (`exec-maven-plugin`, faza `compile`)
  razem z kontrolerami `XxxRest`. Wynik jest zapisywany w repozytorium: `mercury-ws-app/src/main/resources/openapi/openapi.json`
  (specyfikacja domyślna, w języku adnotacji) i `openapi_<lang>.json` dla każdego języka z katalogiem tłumaczeń (pl, en, de, es, fr, ko);
  kontrolery są w `src/main/generated`. Zapis ma być deterministyczny, ale zaobserwowano rzadkie odstępstwo (obserwacja 56), więc przed
  commitem warto sprawdzić `git diff`. Raport braków opisów i tłumaczeń: `mercury-ws-app-rest-generator/target/openapi-doc-report.txt`.
- **Źródła opisów.** Opisy operacji i parametrów to `@WSDLDocumentation` na interfejsach `I*Action` w `mercury-lib`
  (`mercury-ws-server-api`) w stałym formacie: opis, blok `Parametry:`, blok `Zwraca:`. Opisy klas i pól schematów to Javadoc,
  zapisywany podczas budowy modułów `mercury-lib` i `mercury-lucene-indexes-api` do `META-INF/mercury/schema-docs.json` w jarach
  (`SchemaDocsGenerator`). Klasa `XxxDto` dziedziczy opisy encji `Xxx`, a pole `id` bez opisu dostaje opis domyślny.
- **Serwowanie.** `OpenApiController` (`mercury-ws-app`) udostępnia `GET /rest/openapi.json` z sekcją `servers` zależną od ścieżki
  kontekstu. Swagger UI (webjar `org.webjars:swagger-ui` 5.32.0) działa pod `/swagger-ui/`, a jego konfiguracja i style są w
  `mercury-ws-app/src/main/webapp/swagger-ui-config/swagger-initializer.js`.
- **Kontrolery `*ExtRest`.** Ręcznie pisane kontrolery na logicznym JSON-ie sprawy opisuje klasa
  `org.mercury.rest.server.actions.ExtRestOpenApi` (refleksja, bez bibliotek swagger-core). `OpenApiController` dokleja ich
  operacje do statycznej specyfikacji (32 operacje w 4 usługach). Opisy pochodzą z `@WSDLDocumentation` na interfejsach `I*ExtRest`.
- **Zabezpieczenie.** Specyfikacja deklaruje schemat OAuth 2.0 `mercuryOAuth` (przepływ `password`, `POST /rest/token`) i wymaga go
  dla wszystkich operacji. Filtr `OAuthFilter` chroni ścieżki `/rest/service/**` (wzorzec z `mercury-security-config-db-1.0.0.xml`),
  a `/rest/openapi.json` i `/swagger-ui/` są publiczne.
- **Jackson.** Serwer używa Jacksona 2.18.11 (`jackson.version` i `jackson.databind.version` w `mercury/pom.xml`; wcześniej 2.18.2, a przed tym 2.13.2).
  `org.mercury.gui.listeners.JacksonConstraintsListener` (`web.xml` obu aplikacji) znosi domyślny limit długości napisu w odczycie
  JSON-a (20 000 000 znaków od Jacksona 2.15), żeby duże wartości LOB w sprawach nadal się odczytywały.
- **Języki** (zadanie 192, [TASK.md](../../tasks/hgdb/192-Lokalizacja-opisow-specyfikacji-i-tekstow-stalych/TASK.md)).
  `OpenApiController` wybiera język specyfikacji: parametr `l` (alias `lang`), `Accept-Language`, język systemu (klasa
  `org.mercury.rest.server.actions.OpenApiLanguage`); język spoza listy daje `openapi.json`. Pamięć podręczna jest per język.
  - Katalogi tłumaczeń `META-INF/mercury/openapi-docs_<lang>.properties` (UTF-8, surowe znaki) leżą w czterech modułach:
    `mercury-lib/mercury-ws-server-api` (opisy operacji `I*Action`), `mercury-ws-app` (opisy `I*ExtRest`), `mercury-lucene-indexes-api`
    (`ICaseIndexerFieldsManagerAction`) oraz `mercury-ws-app-rest-generator` (teksty stałe i opisy schematów). Wszystkie zasoby języka są łączone.
  - Klucze: `Interfejs`, `Interfejs.metoda`, `Interfejs.metoda.param.<nazwa>`, `Interfejs.metoda.returns` (operacje), `openapi.*` (teksty
    stałe generatora i serwera z argumentami `{0}`), `schema.<Schemat>[.<pole>]` (opisy z Javadoc), `ui.types.*` (strona wyboru typu)
    i `rest.<Interfejs>` (opis usługi tylko dla REST, np. bez wariantów XML, których REST nie ma). Brakujący klucz ma zapas angielski
    (`OpenApiTexts`), a jego nazwa trafia do raportu generatora.
  - Język domyślny `OpenApiTexts.DEFAULT_LANGUAGE = "pl"` to język opisów w `@WSDLDocumentation`; po ich przetłumaczeniu (pytanie Q2
    zadania 192) zmienić na `en` i zregenerować specyfikacje.
  - Narzędzia: `OpenApiDocsExtractor` (`mercury-lib/mercury-core`, `org.mercury.docs`) wyciąga opisy z adnotacji, a odświeżanie kluczy
    `schema.*` po zmianie Javadoc opisuje `tasks/hgdb/192-.../narzedzia/README.md`. Tłumaczy projekt `D:\workspace\git\localization-project`
    (`localizer.py`, Gemini), nie asystent; es, fr i ko to tłumaczenie automatyczne bez przeglądu native speakera.

## Dokumentacja OpenAPI typu sprawy

Dokumentacja struktury typu sprawy i usług na sprawach (zadanie 133, [etap 2](../../tasks/hgdb/133-Swagger-implementacja/etap-2-openapi-typy-spraw.md)).
Status: [TASK.md](../../tasks/hgdb/133-Swagger-implementacja/TASK.md#status-zadania-stan-na-2026-10-20).

- **Endpointy** (`org.mercury.rest.server.actions.CaseTypeOpenApiController`, w przeciwieństwie do `/rest/openapi.json` niepubliczne):
  `GET /rest/openapi/types.json` (kody typów spraw), `GET /rest/openapi/types/{kod}/versions.json` (wersje typu) i
  `GET /rest/openapi/types/{kod}.json[?v=3.1|typeId=123]` (specyfikacja OpenAPI 3.1 typu, bez parametrów ostatnia wersja). Wersja `v`
  to `version.versionMinor` (samo `3` oznacza `3.0`), a `typeId` ma pierwszeństwo. Nieznany typ albo wersja daje 404.
- **Dostęp.** Token OAuth (`Authorization: Bearer`) albo sesja użytkownika zalogowanego formularzem (`/mercury-ws-app/login/`),
  więc specyfikację da się oglądać w przeglądarce. Bez jednego i drugiego 401.
- **Schemat typu.** Budowany bezpośrednio z `TypeCase`/`TypeParam`/`ParamDefinition` (bez generowania klas Javy): logiczny JSON sprawy,
  pierwsza właściwość `mrcCaseHeader`, sprawy zależne jako `$ref` (ochrona przed cyklami, limit `Context.maxDepthResult`).
  Typy zależne starszej wersji głównej: wersja obowiązująca w chwili jej początku (`fromDate`/`toDate`), a bez takiej ostatnia.
- **Usługi per typ** (`CaseTypeServicesController`): `POST /rest/service/types/{kod}/{operacja}` ustawia w kontekście parametr
  `requestContext.caseAsType` (`ContextRequestProperties.RequestContextes.CASE_AS_TYPE`) i deleguje do usług `*ExtRest`.
  Zapis sprawy istniejącej w innym typie jest migracją (nowa wersja sprawy w typie docelowym, stara ze statusem `Z`).
  Operacje: `find`, `findFirst`, `loadSampleByTypeCode`, `searchByLuceneId`, `findByPKProperty`, `save`, `initModel`, `findByIdList`,
  `findByGroupCaseIds`, `loadLastUpdatedByTypeCodes`, `loadSubCase`, `loadSubCaseList`, `searchInDB`, `searchByParams`, `searchByQuery`,
  `search/searchByQuery`, `search/explainPlanSearchByQuery`, `search/dateMetricQuery`, `history/findByCaseId`,
  `history/findByCaseIdAllVersions`. Dla list i wyników stronicowanych typ trafia do zapytania, dla pojedynczej sprawy jest
  sprawdzany w odpowiedzi.
- **Usługi zapisu i usuwania** (zadanie 133, D23; kształt DTO jak w `CaseBusinessRest`): `remove`, `removeList`, `removeSubCase`,
  `removeSubCasesList`, `removeSubCasesAll`, `updateCaseParamsByParams`, `updateCasesParamsByParams`. Sprawy w żądaniu muszą być typu ze
  ścieżki albo typu zależnego od niego (bezpośrednio i pośrednio, np. `BpmTask` dla `BpmBPDInstance`; zbiór wyznacza
  `CaseTypeOpenApiService.typeCodesInTree`). Operacje zbiorcze (`removeList`, `updateCasesParamsByParams`) odrzucają całość przy
  jakiejkolwiek sprawie innego typu. Typy ustala jedno zapytanie `findByIdList`, a przy błędzie odczytu operacja się nie wykonuje.
  Operacje `removeSubCase*` usuwają referencje do spraw zależnych (nie same sprawy) i są w specyfikacji tylko dla typów ze sprawami zależnymi.
- **Język opisów.** Teksty typu w postaci `${klucz}` (etykiety, opisy, nazwy opcji słowników) są tłumaczone przez `IResourceLogic`
  na język z parametru `l` (alias `lang`; `pl`, `en-GB`, `en_GB`), a bez niego z nagłówka `Accept-Language` albo języka systemu. Teksty stałe typu (tytuł, wersja, opisy kopert i stronicowania, uwagi o typie, formaty dat) są w katalogach (`OpenApiTexts`, klucze `openapi.*`), a nie w kodzie. Specyfikacja ma
  `info.x-language`, a przetłumaczone nazwy opcji trafiają do `x-enumNames` (obok `enum` z wartościami). Klucz bez tłumaczenia jest
  pomijany, a tytuł pola wraca do `recomendedLabel`, potem do nazwy definicji.
- **Strona wyboru typu.** `/swagger-ui/types.html` (chroniona logowaniem w `web.xml`; `types.html?l=de` ustawia język opisów i etykiet strony, które pobiera z publicznego `GET /rest/openapi/ui/types.json`, klucze `ui.types.*`, `OpenApiUiTextsController`; `index.html?l=de` i `index.html?spec=..%2Frest%2Fopenapi.json%3Fl%3Dde` dopisują język do adresu specyfikacji) pokazuje typy i ich wersje, a kliknięcie otwiera
  Swagger UI z `index.html?spec=../rest/openapi/types/{kod}.json[?typeId=…]`. Pliki `swagger-initializer.js` i `types.html` mają
  `Cache-Control: no-store` (osobne mapowania `mvc:resources` przed `/swagger-ui/**`). „Try it out” dla `POST /rest/service/…`
  wymaga tokenu (przycisk Authorize, przepływ `password`).
- **Pułapki.** `@Transactional` w klasach skanowanych w kontekście serwletu (`moduleDb-3.0-servlet.xml`) nie działa, więc
  `CaseTypeOpenApiService` używa `TransactionTemplate` (`transactionManagerDefault`). Klucz pamięci podręcznej odpowiedzi HTTP
  uwzględnia `caseAsType`. `save` kończy się `NullPointerException` na pustych tablicach w sprawach zależnych (obserwacje 46–49
  w [obserwacjach](../obserwacje.md)).

## Tabele tworzone przez Hibernate (bez ręcznego DDL)

Encje serwera, które nie mają skryptu DDL w repozytoriach, tworzy Hibernate przy starcie, jeśli `hibernate.hbm2ddl.auto` ma wartość
`update` albo `create`. W konfiguracjach serwera (`database-<dostawca>.properties`) wartości są różne: `postgresql` i `none` (lokalny
Tomcat, profil `scichy`), `oracle` i `mysql` to `update`, `hsql` i `mssql` to `create`. Przy `none` tabele trzeba utworzyć ręcznie.

**`IGO_DA_LICENSE_KEYS`** (baza `mercury-db`, encja `org.mercury.license.LicenseKeyEntry` w `mercury-core-server`, zadanie 96): historia
kluczy licencji serwera. Każda aktualizacja klucza dodaje wiersz i robi go aktywnym, poprzednie wiersze zostają jako historia. Gdy
tabeli brakuje, węzeł zapisuje w logu `relacja "igo_da_license_keys" nie istnieje` i korzysta z klucza z pliku
(`mercury.license.file`). DDL dla PostgreSQL, wyprowadzony z adnotacji encji (daty to milisekundy od 1970-01-01 UTC):

```sql
CREATE TABLE public.igo_da_license_keys (
    id              varchar(36)   NOT NULL,
    key_text        varchar(4000) NOT NULL,
    serial_no       varchar(64),
    product_name    varchar(256),
    license_type    varchar(32),
    organization    varchar(256),
    expiration_date bigint,
    created_date    bigint        NOT NULL,
    created_by      varchar(128),
    activated_by    varchar(128),
    active          boolean       NOT NULL,
    activated_date  bigint,
    CONSTRAINT igo_da_license_keys_pkey PRIMARY KEY (id)
);

CREATE INDEX igo_da_license_keys_act_indx ON public.igo_da_license_keys (active);
```

Tabelę kluczy licencji aplikacji uwierzytelniania (`MRC_LDAP_LICENSE_KEYS`, baza realmu `mercury-ldap`) tworzy sama aplikacja
`mercury-gui-auth` przy pierwszym zapisie (`JdbcAuthLicenseKeyStore`), więc tam DDL nie jest potrzebny. Domyślna konfiguracja obrazu
Docker (`mercury-3.0/docker-init-config/classes/mercury-ws-app/database-postgresql.properties`) ma `hbm2ddl.auto=update`, dlatego na
klastrze tabela `IGO_DA_LICENSE_KEYS` powstaje sama.

## Budowanie

```bash
mvn -U clean install -Dmaven.test.skip=true
mvn -U clean install -Dmaven.test.skip=true -Ddatabse.provider=ORACLE
```

Po instalacji biblioteki ładuje się do innych projektów skryptami:

```bash
./deploy.sh slawas mercury-webapps
./deploy-api.sh slawas mercury-webapps
./deploy-api.sh slawas mercury-client
./deploy-api.sh slawas hgdb-client-open
```

Uwagi do budowania serwera testowego (`mercury-server`):

- Instalacja kopiuje do `apache-tomcat` pliki WAR i jary `mercury*` oraz `hgdb*` w `apache-tomcat/mercury/lib`. Przed
  `mvn install` zatrzymaj Tomcata: przy uruchomionym serwerze krok `mercury-server` zakończył się błędem na etapie
  kasowania starych jarów (przypuszczenie: Windows blokuje jary używane przez Tomcata), choć pozostałe moduły zbudowały się poprawnie. Po instalacji usuń rozpakowane katalogi
  `webapps/mercury-ws-app` i `webapps/mercury-gui-registry`, żeby Tomcat rozpakował nowe WAR-y.
- Biblioteki zewnętrzne w `apache-tomcat/mercury/lib` (np. Jackson) nie są aktualizowane przez instalację. Przy zmianie ich wersji
  podmień jary ręcznie, biorąc je z `mercury-server/target/dependency`.
- Lokalny Tomcat z szablonów `src/main/config/scichy` i `scichy-test` (`conf/server.xml`) ma włączony SingleSignOn (valve `org.apache.catalina.authenticator.SingleSignOn` w `<Host>`, jak w obrazie Docker): logowanie FORM w jednej aplikacji (`mercury-ws-app`, `mercury-gui-registry`, `mercury-gui-auth`) obowiązuje w pozostałych. Aplikacje trzeba otwierać przez ten sam host (np. `localhost`).
- `server.xml` z tych szablonów rejestruje `org.apache.catalina.mbeans.JmxRemoteLifecycleListener` (zdalny JMX). Klasa jest w jarze `catalina-jmx-remote.jar`, którego nie ma w podstawowych paczkach Tomcata 9.0.x (katalog `bin/extras` zniknął z serwerów Apache; w ZIP-ie 9.0.123 klasy nie ma w żadnym jarze `lib`), więc po wymianie Tomcata start kończy się `ClassNotFoundException`. Jar trzeba dołożyć do `apache-tomcat/lib` ręcznie (szablony nie zawierają jarów): `org.apache.tomcat:tomcat-catalina-jmx-remote:9.0.14` z Maven Central (ostatnia wersja tego artefaktu; zapisać jako `catalina-jmx-remote.jar`). Z Tomcatem 9.0.123 użyty 2026-11-23, 9.0.14 to wersja starsza o linię wydań, więc zgodność wynika z prostoty klasy, a nie z testów.
- Maven pracuje w trybie offline (`MAVEN_ARGS=-o`). Nowe artefakty ściąga się osobno poleceniem `mvn dependency:get`. Po `install.sh` w
  `mercury-lib` artefakty `mercury-entities:<dostawca>-<wersja>` i `mercury-lib:<wersja>` (pom nadrzędny) mogą leżeć tylko w `mercury-lib/repo`,
  a nie w `~/.m2`: do budowy `mercury` offline trzeba je tam skopiować (obserwacja 58).

## Pozostałe katalogi

- `docs/` – artykuły: metadane obiektów, DTO usług SOAP/REST, sekcje GUI, „Object vs Case”, Security Helper.
- `db/` – skrypty baz danych.
- `maven/` – pomocniczy POM `pl.slawas:install-jar` do instalacji jarów w lokalnym repozytorium. Nie należy do reaktora.
- `repo/` – lokalne repozytorium Maven projektu.
- `test-case-samples/` – przykładowe przypadki testowe.

Jakość kodu: SonarCloud, projekt `io.hgdb:mercury`.
