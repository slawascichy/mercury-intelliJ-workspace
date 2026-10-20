# [133] Swagger - Implementacja

## Cel zadania
Wdrożenie dokumentacji OpenAPI/Swagger dla modułu `mercury-ws-app`.

Zadanie obejmuje trzy obszary:

1. Adnotacje i opisy OpenAPI dla usług REST, które generuje moduł `mercury-ws-app-rest-generator`.
2. „Dynamiczna” dokumentacja OpenAPI dla podanego kodu typu sprawy (ostatnia albo wskazana wersja typu).
3. Zgodność komunikacji między węzłami serwera i klientami po dopasowaniu klas JAXB modelu obiektu MRC
   do XSD (kwalifikowane elementy XML). Cel: zniwelować ryzyko cichej utraty danych przy wersjach mieszanych.

Rewizję wersji oprogramowania i migrację serwera na Javę 17 wydzielono do zadania
[191 – Rewizja wersji i migracja na Javę 17](../191-Rewizja-wersji-migracja-Java17/TASK.md).

## Podział na etapy

| Etap | Plik | Zakres | Zależy od |
|---|---|---|---|
| 1 | [etap-1-openapi-statyczne.md](etap-1-openapi-statyczne.md) | Generator emituje specyfikację OpenAPI usług REST, serwowanie specyfikacji i Swagger UI, podbicie Jacksona na serwerze | – |
| 2 | [etap-2-openapi-typy-spraw.md](etap-2-openapi-typy-spraw.md) | Dynamiczny schemat OpenAPI dla kodu typu sprawy | Etap 1 (infrastruktura serwowania) |
| 3 | [etap-3-zgodnosc-komunikacji-wezlow.md](etap-3-zgodnosc-komunikacji-wezlow.md) | Zgodność węzłów i klientów po zmianie kontraktu XML w `mercury-lib` (wersje mieszane, serializacja, wydanie) | Zmiany kontraktu XML w `mercury-lib` (zrobione, opis w etapie). Warunek **wydania** zadania |

Swagger nie wymaga zmiany Javy ani zadania 191. Jedyny punkt wspólny to wersja Jacksona na serwerze
(patrz niżej): jego podbicie należy do etapu 1 tego zadania.

## Status zadania (stan na 2026-10-20)

**Jedno źródło prawdy o statusie.** Etapy i podsumowania odsyłają do tej tabeli. Podsumowania dzienne
(`podsumowanie-*.md`, `copilot-podsumowanie-*.md`) opisują stan z danego dnia i nie zmieniają statusu.

Znaczenie kolumn (jedno znaczenie, bez mieszania „zrobione w kodzie” z „domknięte procesowo”):

- **Kod**: zaimplementowane i przetestowane (testy jednostkowe oraz, gdy dotyczy, sprawdzenie na serwerze testowym). ✅ tak, ⬜ nie.
- **Commit**: zmiany zatwierdzone w repozytorium (lokalnie). ✅ tak, – nie dotyczy (brak kodu).
- **GO**: zakres obszaru jest kompletny (Kod i Commit spełnione). **NO-GO**: brakuje elementu zakresu, kolumna „Warunek” mówi jakiego.
  Wypchnięcie na zdalne repozytorium jest osobnym obszarem (wiersz „Publikacja”), a nie warunkiem GO obszarów funkcjonalnych.

| Obszar | Kod | Commit | Decyzja | Warunek / uwaga |
|---|---|---|---|---|
| Etap 1: specyfikacja OpenAPI usług REST (opisy, Swagger UI, OAuth, Jackson 2.18.2) | ✅ | ✅ | **GO** | 0 braków opisów usług, operacji i parametrów |
| Etap 2, kroki 1–4: schemat typu, mapowanie atrybutów, sprawy zależne, operacje | ✅ | ✅ | **GO** | |
| Etap 2, krok 5: wersje typu (`?v=`, `?typeId=`, `versions.json`, reguła wersji typów zależnych D20) | ✅ | ✅ | **GO** | sprawdzone na serwerze na typie z kilkoma wersjami |
| Etap 2: usługi per typ i `CASE_AS_TYPE` (kategorie A, B, C, migracja sprawy) | ✅ | ✅ | **GO** | poza zakresem decyzją D21: `fieldMetricQuery`, `history/find`, `loadSampleByTypeName`, kategoria D |
| Etap 2, krok 8: strona wyboru typu i Swagger UI per typ (logowanie sesją) | ✅ | ✅ | **GO** | sprawdzone w przeglądarce przez autora |
| Etap 2, krok 6: lokalizacja etykiet i nazw opcji (`${…}`, `?lang=`, `Accept-Language`) | ✅ | ✅ | **GO** | sprawdzone na serwerze (`CalendarUserEvent` w `pl`, `en`); pliki `*_de.properties` przetłumaczone z niderlandzkiego na niemiecki (obserwacja 50), wersja `de` do sprawdzenia po wdrożeniu |
| Etap 2: test w obie strony (`loadSampleByTypeCode` → walidacja schematem → `save` bez nowej wersji typu) | ⬜ | – | **NO-GO** | warunek DoD etapu 2 |
| Etap 3: zgodność komunikacji węzłów (kontrakt XML, kontrola wersji węzłów, testy) | ✅ | ✅ | **GO** | |
| Wydanie `mercury-lib` 3.0.4.7 (artefakty wdrożone, tag lokalny) | ✅ | ✅ | **GO** | wypchnięcie tagu: wiersz „Publikacja” |
| Dokumentacja workspace (`docs/moduly/mercury.md`, `docs/obserwacje.md`, `TASK.md`, etapy, podsumowania) | ✅ | ✅ | **GO** | uspójniona 2026-10-20 |
| Publikacja: wypchnięcie commitów i tagów na zdalne repozytoria | – | – | **NO-GO** | niewypchnięte: `mercury` 22 commity, `mercury-lib` 9 commitów i tag `3.0.4.7`, workspace 16 commitów. Tagi `3.0.4.1`–`3.0.4.6` są na zdalnym, `hgdb-client-open` jest zsynchronizowany, `mercury-docker`, `mercury-cmd`, `mercury-client` bez zmian |
| **Zadanie 133 jako całość (wydanie)** | – | – | **NO-GO** | do GO: „test w obie strony” z etapu 2 i publikacja |

**Poza DoD, decyzja autora (nie blokuje wydania):** krok 7 etapu 2 (cache i `ETag`; wymaganie „zmiana typu widoczna bez restartu, także
na drugim węźle” jest spełnione, bo specyfikacja nie jest buforowana), automatyczny token dla „Try it out” (działa przycisk Authorize),
poprawki z obserwacji 47–49, opisanie operacji kategorii D. Odłożone: AJP (obserwacja 31), narzędzie do kluczy licencyjnych (32), limit
bufora spraw (38), `DENY` w uprawnieniach pól (37), niestabilny `SrvTest.changeCaseVersionScenario`.

### Biblioteki dla etapów 1–2 na Javie 8 (sprawdzone w POM-ach na Maven Central, 2026-10-16)

| Biblioteka | Wersja | Bajtkod | Zależności istotne dla serwera |
|---|---|---|---|
| `io.swagger.core.v3:swagger-core` / `swagger-models` / `swagger-annotations` (wariant `javax`, bez `-jakarta`) | 2.2.0 … 2.2.55 (najnowsza) | 1.8 (`<source>1.8</source>` / `maven.compiler.release=8`). Wymóg „Java 11” z README dotyczy budowania samej biblioteki | Jackson: 2.2.0 → 2.13.2, 2.2.2 → 2.13.3, 2.2.4 → 2.13.4, 2.2.7–2.2.8 → 2.14.0, 2.2.20 → 2.16.0, 2.2.30 → 2.18.2, 2.2.55 → 2.22.1. snakeyaml 1.30 → 2.6 |
| `com.github.javaparser:javaparser-core` (tylko w generatorze, etap 1) | 3.26.4, 3.28.2 | 1.8 (`java.version=1.8`) | – |
| `org.webjars:swagger-ui` | 5.x (najnowsza 5.33.2) | – (zasoby statyczne) | – |
| Jackson (`jackson-databind`) | 2.18.2, 2.22.1 | 1.8 (`javac.target.version=1.8`) | – |

Wnioski:

- Serwer ma Jackson 2.13.2 / databind 2.13.2.2 (`mercury/pom.xml:118-119`). **swagger-core 2.2.0 używa
  tej samej wersji Jacksona** i opisuje OpenAPI 3.0, więc da się go dodać bez żadnych innych zmian.
- Nowsze swagger-core (od 2.2.7, OpenAPI 3.1 od 2.2.8) wymagają podbicia Jacksona na serwerze do 2.14+.
  Jackson 2.x nadal ma bajtkod 1.8, więc to zmiana tylko w `mercury/pom.xml`, bez zmiany Javy.
  **Decyzja D5: ten wariant.** Podbicie Jacksona na serwerze należy do etapu 1 (przeniesione z zadania 191).
- W POM-ach `mercury` nie ma `snakeyaml` ani `jackson-dataformat-yaml`, więc nie ma konfliktu z YAML-em swagger-core.
- Do sprawdzenia przy wdrożeniu: `mvn dependency:tree` modułów `mercury-ws-app` i generatora pod kątem
  konfliktów (`jakarta.xml.bind-api`, `jakarta.validation-api` w wersjach 2.x z przestrzenią `javax`).

Zadania wydzielone:

- [192 – Lokalizacja opisów specyfikacji statycznej, tekstów stałych i stron dokumentacji Swagger](../192-Lokalizacja-opisow-specyfikacji-i-tekstow-stalych/TASK.md)
  (decyzja D22, 2026-10-20). Zakres obejmuje też własne strony i interfejs Swagger UI. Założenia z D22:
  Tekst domyślny w `@WSDLDocumentation` jest angielski. Tłumaczenia leżą w katalogu zasobów `openapi-docs_<lang>.properties` w
  `mercury-lib` (klucz stabilny, np. `ICaseBusinessExtRest.save`, `ICaseBusinessExtRest.save.param.arg0`), z pierwszym katalogiem `pl`.
  Generator etapu 1 wybiera tekst z katalogu danego języka, a gdy go brak, z adnotacji, i tworzy plik na język (`/rest/openapi.json?lang=`).
  Raport braków wypisuje też brakujące tłumaczenia. Etap 2 zostaje przy kluczach `${…}`, a teksty stałe generowane przez kod
  (opisy operacji, kopert i parametrów usług per typ) trzeba przenieść do tego samego mechanizmu. Dotychczasowe polskie opisy
  w adnotacjach trzeba przetłumaczyć na angielski, a polskie wersje przenieść do katalogu `pl`. Zmieni to opisy w WSDL.

- [190 – Dokumentacja metadanych typów](../190-Dokumentacja-metadane-typow/TASK.md): poprawa strony
  „Case metadata” na hgdb.org według kodu (rozbieżności wykryte w etapie 2).
- [191 – Rewizja wersji i migracja na Javę 17](../191-Rewizja-wersji-migracja-Java17/TASK.md):
  porządki w zależnościach (Java 8) i migracja `mercury` oraz `mercury-cmd` na Javę 17 (dawne etapy 3 i 4).

## Kontekst i Wymagania

### Stos REST w `mercury-ws-app`

- REST to **Spring MVC 5.3.20** (`@RestController`, `@RequestMapping`), a nie JAX-RS/CXF.
  - `DispatcherServlet` „moduleDb-3.0” na `/` (`mercury-ws-app/.../WEB-INF/web.xml:41-53`).
  - `component-scan` i `<mvc:annotation-driven/>` w `WEB-INF/moduleDb-3.0-servlet.xml:30-44`.
  - Prefiks `/rest` pochodzi z `IRestController`, a `/service` z `IRestService` (`mercury-gui-core`).
- JSON: Jackson 2.13.2 / databind 2.13.2.2 (`mercury/pom.xml:118-119`).
- CXF 3.0.12 obsługuje tylko SOAP (`CXFServlet` na `/services/*`, 96 `jaxws:endpoint`
  w `webService.xml`). Nie ma żadnego `jaxrs:server`. **CXF `OpenApiFeature`/`Swagger2Feature`
  nie mają zastosowania.**
- Brak Swaggera, springdoc i springfox w obu repozytoriach. `pl.slawas:ccrto-openapi`
  (`mercury-ws-app/pom.xml:140`) to biblioteka autora, niezwiązana ze Swaggerem.
- Istniejąca samodokumentacja:
  - `RestServicesController.java:84`: `/restServices` to lista usług z `RequestMappingHandlerMapping`.
  - `RestServicesController.java:217`: własny WADL `/restServices/{serviceName}.wadl`.
  - `RestServicesSampleRequestController.java:48`: przykładowe żądanie z `getRequestSampleInstance`.

### Generator `mercury-ws-app-rest-generator`

- Klasa startowa: `RestSourceGeneratorApp.java`. Biblioteka `org.reflections` skanuje pakiety
  `*.ws.server.actions.*` (linie 50-63) i szuka klas z `@WebService`, czyli **implementacji SOAP**
  z `mercury-ws-server`.
- `RestSourceGenerator.java` działa **tylko na refleksji ze skompilowanych klas**. Nie parsuje
  źródeł i nie używa szablonów, kod składa przez `StringBuilder`.
  - Metody interfejsów SOAP (86-117), nazwy parametrów z `@WebParam(name)` (666-678).
  - Pakiet `.ws.` zmienia na `.rest.`, a nazwę `XxxAction` na `XxxRest` (255-257).
  - Adnotacje metody (286-288) i klasy (465-468).
  - Dla każdej metody powstaje klasa wewnętrzna `XxxRequest` z parametrami (332-386).
- `RestSourceGenerator2` (pakiet `.rest2.`) jest przestarzały.
- Wynik: `mercury-ws-app/src/main/generated/` (92 pliki, **commitowane do repozytorium**).
- Maven: `exec-maven-plugin` 1.5.0 w fazie `compile` (`mercury-ws-app-rest-generator/pom.xml:29-42`).
  W reaktorze (`mercury/pom.xml:1060-1061`) `mercury-ws-app` buduje się **przed** generatorem,
  więc wygenerowane źródła trafiają do następnego builda.
- Endpointy REST przyjmują **encje** (np. `Case` w `FindByKeyRequest`), a zwracają
  `WsStatusWith*Dto` z `mercury-ws-dto-api`.

Przykład wygenerowanej klasy (`.../rest/server/actions/data/CaseRest.java:36-49`):

```java
@RequestMapping("/rest/service/CaseRest")
@RestController
public class CaseRest extends CaseAction implements IRestServicesHelper {
	@RequestMapping(value = "findByKey", method = RequestMethod.POST, produces = MediaType.APPLICATION_JSON_VALUE + ";charset=UTF-8")
	@ResponseBody
	public WsStatusWithCaseDto findByKey(@RequestBody FindByKeyRequest requestBody) throws ServletException {
```

### Źródła opisów do dokumentacji

| Źródło | Dostępność | Uwagi |
|---|---|---|
| `@org.apache.cxf.annotations.WSDLDocumentation` w interfejsach `mercury-ws-server-api` | Refleksja (retencja RUNTIME – przypuszczenie) | 127 wystąpień w 67 plikach, np. `ICaseAction.java:57,69`. Nie każda metoda ją ma |
| Javadoc interfejsów SOAP (`@param`, `@return`) | Tylko źródła | Około 814 bloków |
| Javadoc pól encji (`mercury-entities`) | Tylko źródła | Np. `Case.java:194-213` |
| Własne adnotacje `mercury-core` (`ColumnPosition`, `MappedProperty`, `NameRepresentation`…) | Refleksja | Nie zawierają opisu ani etykiety |
| DTO z `mercury-entities-dto-generator` | – | `DtoClassGenerator.java:244-330` nie kopiuje Javadoc. Opis pola `XxxDto.pole` = Javadoc `Xxx.pole` (patrz niżej) |

### Generator DTO `mercury-entities-dto-generator` (mercury-lib)

Typy wejścia i wyjścia wygenerowanego REST w dużej części pochodzą z drugiego generatora,
w `mercury-lib/mercury-entities-dto-generator` (pakiet `pro.ibpm.mercury.entities.dto.generator`).

| Aplikacja | Uruchamiana w | Wejście | Wynik |
|---|---|---|---|
| `ClassGeneratorApp` | `mercury-entities` (`pom.xml:93-125`, `exec-maven-plugin` 3.0.0, faza `process-test-resources`) | Encje z `@Table` i `@Embeddable` (refleksja, `org.reflections`) | `XxxDto` w pakiecie `pro.ibpm.mercury.dto` (`DtoClassGenerator`) oraz fabryka encji (`EntitesFactoryClassGenerator`) |
| `WsResultDtoClassGeneratorApp` | `mercury-ws-dto-api` (`pom.xml:24-50`, ta sama faza) | Klasy DTO | Koperty odpowiedzi w `pro.ibpm.mercury.ws.server.api.returns`: `WsStatusWithXxxDto`, `WsStatusWithXxxDtos`, `XxxPagedResult`, `WsStatusWithXxxPagedResult` |

- Działa jak generator REST: refleksja na skompilowanych klasach i składanie kodu przez `StringBuilder`.
  Potem sam kompiluje wynik przez `com.sun.tools.javac.Main` z `-source/-target 1.8`
  (`ClassGeneratorApp.java:84-113`, `Constants.java`).
- `DtoClassGenerator` (`:244-330`) przenosi pola z `@Column`, `@JoinColumn(s)`, `@Id`, `@EmbeddedId`
  i kopiuje tylko `@Id`, `@EmbeddedId`, `@MappedProperty`, `@MappedPropertyEager`. Klasa dostaje
  `@XmlType(namespace = "http://pro.ibpm.mercury.dto")`. **Javadoc encji nie jest przenoszony.**
  W miejscu opisu jest tylko komentarz z typem (`/* class java.lang.String */`).
- Nazewnictwo jest stałe: `Xxx` → `XxxDto` (`EntityHelper.DTO_NAME_SUFFIX`), te same nazwy pól.
  Pozwala to przypisać opis pola DTO do Javadoc pola encji bez zmian w generatorze DTO.
- **Wygenerowane źródła nie są w repozytorium** (`mercury-entities/.gitignore:6`: `/src/main/generated/pro`,
  w gicie jest tylko `README.txt`). Na dysku leży 325 plików. Inaczej niż w generatorze REST,
  którego wynik jest commitowany.
- Typy w operacjach REST:
  - wejście: wrappery `XxxRequest` z **encjami** (np. `Case` w `FindByKeyRequest`);
  - wyjście: koperty `WsStatusWithXxxDto(s)` z polem `dto` typu `XxxDto`.

  Schematy OpenAPI trzeba więc zbudować dla encji (wejście) i DTO (wyjście). Opisy pól obu pochodzą
  z tego samego źródła: Javadoc pól encji w `mercury-entities`.

### Generator API 2.0 `mercury-ws-server-api20-generator` (mercury)

- `Ws20SourceGeneratorApp` skanuje interfejsy z `@WebService` w `pro.ibpm.mercury.ws.server.api.actions`
  (`mercury-ws-server-api`) i tworzy interfejsy SOAP zgodne z Mercury 2.0 w
  `mercury-ws-server-api20/src/main/generated` (59 plików, w gicie tylko `README.txt`).
  Uruchomienie: `exec-maven-plugin`, faza `compile`.
- Kopiuje same sygnatury. Parametry dostają nazwy `arg0`, `arg1`…, bez `@WebParam`
  i `@WSDLDocumentation`. Dotyczy tylko SOAP (WSDL 2.0), nie REST. Generator REST czyta
  implementacje interfejsów 3.0.

Żaden POM nie ma `maven-source-plugin`. Generator ma dziś dostęp tylko do skompilowanych klas.
Źródła `mercury-lib` leżą obok na dysku (`${local-project-workspace-path}/mercury-lib`), więc
można je czytać po ścieżce.

### Definicje typów spraw

Encje leżą w `mercury-lib/mercury-entities/src/main/java/pro/ibpm/mercury/entities/attr/`.
Opis pojęć: `docusaurus-hgdb/docs/003_Architecture/001_Cases_MetaData/index.mdx`.

| Encja | Tabela | Rola i kluczowe pola |
|---|---|---|
| `TypeCode` | `IGO_DA_TYPECODE` | Kod typu, grupuje wersje. `name` (PK), `alias`, `label`, `publishVersion` (zmienia się przy każdej aktualizacji) |
| `TypeCase` | `IGO_DA_TYPES` | Wersja typu. `id`, `version` + `versionMinor`, `description`, `code`, `isActive`, `isLatestVersion`, `fromDate`/`toDate`, `sumControl`, `typeParams`, `subTypes` |
| `TypeParam` | `IGO_DA_TYPEPARAMETERS` | Pole typu. PK = (`CASE_TYPE_ID`, `POSITION` 1..128), `label`, `tooltip`, `updateable`, `isRequired`, `hasMultiValues`, `arg1..arg5` |
| `ParamDefinition` | `IGO_DA_PARAMETER_DEFINITIONS` | Wersjonowana definicja atrybutu. `paramType` (`AttributeType`), `subType`, `valueDefinition`, `sourceType`, `defaultValue`, `mimeType` |
| `SubType` | `IGO_DA_TYPESUBS` | Pole będące sprawą zależną. `code`, `fieldName`, `isList`, `label` |

- Etykiety (`TypeParam.label`, `tooltip`, `TypeCase.description`) i nazwy opcji słowników mogą być
  kluczami zasobów `${klucz}`, tłumaczonymi według języka z kontekstu
  (`AttributeTypeParameter.prepareLocalizedMessage`, encja `Resource`). `ParamDefinition.recomendedLabel`
  to zwykły tekst. Szczegóły w [etapie 2](etap-2-openapi-typy-spraw.md#lokalizacja-etykiet-klucze-).
- Typy atrybutów: `mercury-core/.../attrs/AttributeType.java:94-225`.
- **Ostatnią wersję wskazuje flaga `isLatestVersion = true`**, a nie maksymalny numer wersji
  (named query `MType.QgetByCodeLastVersion`, `TypeCase.java:92-94`).
- **Nowa wersja typu powstaje automatycznie** przy zapisie sprawy z nowym polem albo innym typem
  pola (`TypeCaseLogicHelper.checkNewVersion` :465, `createNewLatestVersion` :514). Blokuje to
  `mercury.saveRequestContext.forceChangeType.default=false`.
- Pobranie definicji:
  - logika: `TypeCaseLogic.findLastVersionByTypeCode(Context, String)` (`mercury-srv/.../logic/attr/TypeCaseLogic.java:534`);
  - SOAP: `ITypeCaseAction.findLastVersionByTypeCode` (`mercury-ws-server-api/.../actions/attr/ITypeCaseAction.java:165`);
  - REST: `POST /rest/service/TypeCaseRest/findLastVersionByTypeCode`;
  - przykładowa pusta sprawa: `ICaseBusinessAction.loadSampleByTypeCode` (:732).
- Sprawa ma trzy reprezentacje w usługach:
  - **generyczna** `DtoMrcObject` (SOAP i wygenerowany REST): `mrcCaseHeader` i `propertyMap`
    (`Map<String, DtoMrcProperty>` z polami nazwa/typ/wartość);
  - **XML** (`saveXML`/`findXML`): `XMLReaderHelper` i `XMLVariableBuilder` w `mercury-srv-api`.
    Elementy nazywają się jak pola typu;
  - **logiczny JSON** (ręcznie pisane kontrolery `*ExtRest` w `mercury-ws-app`):
    `RestVariableReader`/`RestReaderHelper` (JSON → `MrcObject`) i `RestVariableBuilder`
    (`MrcObject` → JSON). Pola obiektu JSON nazywają się jak pola typu.
- Schemat per typ trzeba zbudować samemu z `TypeParam`. Opisuje on logiczny JSON (decyzja D2).
- `mercury-srv/.../org/mercury/data/javax` zawiera eksperymentalny generator klas Javy z typu sprawy
  (`TypeCaseSourceGenerator`, kompilacja w runtime). Używa go tylko test `MrcTypeGeneratorScenario`.
- Zmiany typów rozchodzą się przez JMS: kolejka `mrc-type-case-registry-changes`,
  odbiorca `TypeCaseRegistryChangesReceiver.java:36-58` (kolejka per węzeł).

### Ograniczenia wersji

- Serwer działa na Javie 8 ze Spring MVC 5.3.20 i stosem `javax`. Biblioteki Swaggera muszą działać
  w tym środowisku (sprawdzone, patrz „Biblioteki dla etapów 1–2”).
- Nie używać wariantów `-jakarta` (swagger-core) ani bibliotek wymagających Spring 6 / Spring Boot 3
  (np. springdoc 2.x). Stan wersji i plan migracji: zadanie
  [191](../191-Rewizja-wersji-migracja-Java17/TASK.md).

## Decyzje

| # | Decyzja | Opcje | Status |
|---|---|---|---|
| D1 | Sposób serwowania specyfikacji (etap 1) | (a) statyczny `openapi.json` z generatora + Swagger UI z webjara; (b) springdoc-openapi 1.8.x bez Spring Boot; (c) springfox 2.9.2 | ✅ **(a)** |
| D2 | Kształt dokumentacji typu sprawy (etap 2) | (a) „logiczny” JSON typu; (b) opis generycznego `DtoMrcObject` | ✅ **(a)**. Logiczny JSON już istnieje w usługach `*ExtRest` (`RestVariableReader` / `RestVariableBuilder`), więc nie trzeba nowego kontraktu. Szczegóły w [etapie 2](etap-2-openapi-typy-spraw.md) |
| D3 | Docelowa Java serwera | 17 lub 21 | ✅ **17**. Przeniesione do zadania [191](../191-Rewizja-wersji-migracja-Java17/TASK.md) (D1) |
| D4 | Czy `hgdb-client-open` i `mercury-cmd` przechodzą na nowszą Javę | Zostają na 1.8 / przechodzą razem z serwerem | ✅ `hgdb-client-open` zostaje na 1.8, `mercury-cmd` przechodzi na 17. Przeniesione do zadania [191](../191-Rewizja-wersji-migracja-Java17/TASK.md) (D2) |
| D6 | Źródło opisów operacji i pól (etap 1) | A: generator REST czyta źródła (bez zmian w `mercury-lib`); B: generator DTO tworzy katalog opisów pól w jarze `mercury-entities`; C: uzupełnić `@WSDLDocumentation` w interfejsach; D: generator API 2.0 kopiuje `@WSDLDocumentation` | ✅ **A + B + C stopniowo, D opcjonalnie.** Cel: dokumentacja spójna i generowana jednoznacznie z określonych danych. Zasady i kolejność źródeł w [etapie 1](etap-1-openapi-statyczne.md#zasada-spójności-i-jednoznaczności) |
| D7 | Zgodność kontraktu XML i sposób zabezpieczenia wersji mieszanych (etap 3) | Kontrakt: (a) klasy dopasowane do XSD (kwalifikowane elementy), (b) XSD i próbki dopasowane do klas. Zabezpieczenie: A wspólne wdrożenie z kontrolą wersji, B czytnik tolerancyjny, C zapis wg wersji partnera | Kontrakt ✅ **(a)** (zrobione w `mercury-lib`: 7 klas `Dto*`, `CaseHeader`, `MrcObjectMetadata`). Zabezpieczenie ✅ **A** (wspólne wdrożenie z kontrolą wersji): klienci aktualizują się razem z serwerem, więc czytnik tolerancyjny (B) nie jest potrzebny. Klienci zostają na Javie 1.8. Szczegóły w [etapie 3](etap-3-zgodnosc-komunikacji-wezlow.md) |
| D5 | Wersja swagger-core (etapy 1–2) | (a) 2.2.0 z obecnym Jacksonem 2.13.2, OpenAPI 3.0; (b) nowsza 2.2.x (od 2.2.8 OpenAPI 3.1) z podbiciem Jacksona na serwerze | ✅ **(b)**. Podbicie Jacksona w `mercury/pom.xml` należy do [etapu 1](etap-1-openapi-statyczne.md). Java bez zmian |
| D8 | Naprawa odczytu JSON `DtoMrcObject`/`DtoMrcList` (etap 1) | Obejście w generatorze / poprawka w `mercury-lib` | ✅ poprawka w `mercury-lib` bez zmiany kontraktu XML. Szczegóły: [etap 1](etap-1-openapi-statyczne.md) |
| D9 | Trwałe źródło opisów (etap 1) | Javadoc / `@WSDLDocumentation` | ✅ `@WSDLDocumentation` jest jedynym trwałym źródłem opisów operacji i parametrów, Javadoc służył do jednorazowej migracji. Szczegóły: [etap 1](etap-1-openapi-statyczne.md) |
| D10 | Jackson na serwerze | Podbicie w tym zadaniu / w zadaniu 191 | ✅ w tym zadaniu, osobny commit. Wykonane: Jackson 2.18.2 (`mercury/pom.xml`), `JacksonConstraintsListener` przywraca brak limitu długości napisu w odczycie JSON-a |
| D11 | Zakres bezpieczeństwa (etap 1) | Usługi chronione OAuth, dokumentacja publiczna | ✅ `/rest/service/**` chronione OAuth, `/rest/openapi.json` i `/swagger-ui/` publiczne |
| D12 | Opisy parametrów (etap 1) | Osobne medium / w tekście `@WSDLDocumentation` metody | ✅ w tekście metody: opis, blok `Parametry:`, blok `Zwraca:` |
| D13 | Migracja opisów z Javadoc (etap 1) | Ręcznie / narzędzie | ✅ narzędzie jednorazowe (JavaParser), metody bez opisu trafiały do raportu braków |
| D14 | Opis kontrolerów `*ExtRest` (etap 1) | Refleksja w `mercury-ws-app` / ręczny fragment / generator po kompilacji `mercury-ws-app` | ✅ refleksja w `mercury-ws-app` (`org.mercury.rest.server.actions.ExtRestOpenApi`), scalana w locie z `openapi.json` |
| D15 | Źródło opisów `*ExtRest` (etap 1) | `@WSDLDocumentation` na `I*ExtRest` / Javadoc | ✅ `@WSDLDocumentation` na interfejsach `I*ExtRest` |
| D16 | Pakiety nowych komponentów | `pro.ibpm.mercury` / `org.mercury` | ✅ nowe komponenty w `org.mercury`. Istniejące klasy migrują stopniowo i tylko na prośbę autora |
| D17 | Parametr kontekstu wskazujący typ sprawy (etap 2) | Zostawić `SAVE_CASE_AS_TYPE` / nowy ogólny parametr | ✅ `RequestContextes.CASE_AS_TYPE` (`requestContext.caseAsType`) w `mercury-lib` 3.0.4.7, bez okresu przejściowego dla starego klucza. Zapis: migracja sprawy do nowej wersji w typie docelowym. Odczyt: `findFirst` zwraca pierwszą sprawę typu. Szczegóły w [etapie 2](etap-2-openapi-typy-spraw.md) |
| D18 | Usługi per typ (etap 2) | Osobne kontrolery per typ / jeden kontroler ze ścieżką wzorcową / tylko opis w specyfikacji | ✅ jeden kontroler `/rest/service/types/{typeCode}/{operacja}` (przedrostki `search/`, `history/`), delegacja do usług ogólnych |
| D19 | Dostęp do specyfikacji typu (etap 2) | Publiczny / token OAuth / token albo sesja | ✅ token OAuth albo sesja zalogowana formularzem. Usługi `POST /rest/service/…` nadal wymagają tokenu |
| D20 | Wersja typu zależnego w specyfikacji starszej wersji typu głównego (etap 2) | Dokładnie ta sama wersja / wersja obowiązująca w czasie (`fromDate`/`toDate`) albo ostatnia | ✅ wersja obowiązująca w chwili początku wersji głównej, a gdy jej nie ma, ostatnia. Dla ostatniej wersji głównego: ostatnie wersje zależnych |
| D21 | Zakres operacji `*ExtRest` per typ (etap 2) | Wszystkie 32 / tylko związane z typem | ✅ kategorie A, B, C. Poza zakresem: `fieldMetricQuery` (statystyka całego indeksu), `history/find` (`versionId` nie wskazuje typu), `loadSampleByTypeName` (zbędne), kategoria D |
| D22 | Język domyślny opisów w dokumentacji OpenAPI (etapy 1 i 2) | Polski / angielski | ✅ angielski jako tekst domyślny (zapas dla języków bez tłumaczenia), polski w pierwszym katalogu tłumaczeń. Język specyfikacji: `?lang=`, potem `Accept-Language`, potem język systemu. Realizacja w osobnym zadaniu (sekcja „Zadania wydzielone”) |

## Definicja Gotowości (DoD)

- Zrealizowane etapy 1, 2 i 3 według ich DoD. Wydanie zadania wymaga etapu 3.
- Dokumentacja workspace zaktualizowana: `docs/moduly/mercury.md` (Swagger, nowe endpointy,
  wersja Jacksona), nowe pozycje w `docs/obserwacje.md`.
- Wszystkie obszary w tabeli „Status zadania” mają decyzję **GO**, a commity i tagi są wypchnięte (wiersz „Publikacja”).
  Stan na 2026-10-20: **NO-GO** (patrz tabela).

## Kluczowe Pliki w Projekcie

Ścieżki względne do `D:\workspace\git`.

| Plik | Rola |
|---|---|
| `mercury/mercury-ws-app-rest-generator/src/main/java/org/mercury/rest/server/generator/RestSourceGeneratorApp.java` | Start generatora, skanowanie pakietów |
| `mercury/mercury-ws-app-rest-generator/src/main/java/org/mercury/rest/server/generator/RestSourceGenerator.java` | Generowanie klas REST |
| `mercury/mercury-ws-app-rest-generator/pom.xml` | Uruchomienie generatora (`exec-maven-plugin`) |
| `mercury/mercury-ws-app/src/main/generated/` | Wygenerowane klasy REST |
| `mercury/mercury-ws-app/src/main/webapp/WEB-INF/web.xml`, `moduleDb-3.0-servlet.xml` | Konfiguracja Spring MVC i CXF |
| `mercury/mercury-ws-app/src/main/java/pro/ibpm/mercury/rest/server/actions/RestServicesController.java` | Lista usług i WADL |
| `mercury-lib/mercury-ws-server-api/src/main/java/` | Interfejsy SOAP z `@WSDLDocumentation` i Javadoc |
| `mercury-lib/mercury-entities-dto-generator/src/main/java/pro/ibpm/mercury/entities/dto/generator/` | Generator DTO i kopert `WsStatusWith*` |
| `mercury-lib/mercury-entities/src/main/java/pro/ibpm/mercury/entities/` | Encje: Javadoc pól jako źródło opisów schematów |
| `mercury-lib/mercury-entities/src/main/java/pro/ibpm/mercury/entities/attr/` | `TypeCode`, `TypeCase`, `TypeParam`, `ParamDefinition`, `SubType` |
| `mercury-lib/mercury-core/src/main/java/pro/ibpm/mercury/attrs/AttributeType.java` | Typy atrybutów |
| `mercury-lib/mercury-ws-dto-api/.../ws/server/api/returns/DtoMrcObject.java` | Generyczny obiekt sprawy |
| `mercury-lib/mercury-srv-api/src/main/java/pro/ibpm/mercury/business/data/utils/XMLReaderHelper.java`, `XMLVariableBuilder.java` | Sprawa jako XML |
| `mercury/mercury-ws-app/src/main/java/pro/ibpm/mercury/rest/server/utils/RestVariableReader.java`, `RestReaderHelper.java`, `RestVariableBuilder.java` | Sprawa jako logiczny JSON |
| `mercury/mercury-ws-app/src/main/java/pro/ibpm/mercury/rest/server/actions/business/data/CaseBusinessExtRest.java` | Usługi spraw na logicznym JSON-ie |
| `mercury/mercury-srv/src/main/java/org/mercury/data/javax/` | Eksperymentalny generator klas Javy z typu sprawy |
| `mercury/mercury-srv/src/main/java/pro/ibpm/mercury/logic/attr/TypeCaseLogic.java` | `findLastVersionByTypeCode` |
| `mercury/mercury-srv/src/main/java/pro/ibpm/mercury/logic/heplers/attr/TypeCaseLogicHelper.java` | Wersjonowanie typów |
| `mercury/mercury-srv/.../logic/jms/TypeCaseRegistryChangesReceiver.java` | Propagacja zmian typów |
| `mercury/pom.xml`, `mercury/mercury-ws-app/pom.xml` | Jackson, swagger-core, Swagger UI |
| `mercury/mercury-ws-app-rest-generator/src/main/java/org/mercury/rest/server/generator/OpenApiSpecBuilder.java` | Budowa specyfikacji OpenAPI 3.1 (swagger-core), raport braków opisów |
| `mercury/mercury-ws-app-rest-generator/src/main/java/org/mercury/rest/server/generator/SchemaDocsCatalog.java`, `WsdlDocumentationText.java` | Katalog opisów klas i parser formatu `@WSDLDocumentation` |
| `mercury/mercury-ws-app/src/main/resources/openapi/openapi.json` | Wygenerowana specyfikacja (w repozytorium) |
| `mercury/mercury-ws-app/src/main/java/pro/ibpm/mercury/rest/server/actions/OpenApiController.java` | Serwowanie `/rest/openapi.json` i przekierowanie Swagger UI |
| `mercury/mercury-ws-app/src/main/java/org/mercury/rest/server/actions/ExtRestOpenApi.java` | Opis kontrolerów `*ExtRest` w specyfikacji (refleksja) |
| `mercury/mercury-ws-app/src/main/webapp/swagger-ui-config/swagger-initializer.js` | Konfiguracja i style Swagger UI |
| `mercury/mercury-gui-core/src/main/java/org/mercury/gui/listeners/JacksonConstraintsListener.java` | Ograniczenia odczytu JSON-a (Jackson 2.15+) |
| `mercury-lib/mercury-core/src/main/java/pro/ibpm/mercury/docs/SchemaDocsGenerator.java` | Katalog opisów klas (`schema-docs.json`) z Javadoc podczas budowy modułów lib |

## Słownik / Zasady

| Pojęcie | Znaczenie |
|---|---|
| Typ sprawy | Definicja struktury sprawy. Identyfikuje go kod (`TypeCode.name`), ma wiele wersji (`TypeCase`) |
| Ostatnia wersja | `TypeCase` z `isLatestVersion = true` |
| Parametr typu | `TypeParam`: pole typu na pozycji 1..128, wskazuje `ParamDefinition` |
| `DtoMrcObject` | Generyczna reprezentacja sprawy w WS/REST (mapa właściwości) |
| Logiczny JSON sprawy | Sprawa jako zwykły obiekt JSON z polami nazwanymi jak pola typu i obiektem `mrcCaseHeader`. Używają go usługi `*ExtRest` |
| Generator REST | `mercury-ws-app-rest-generator`: tworzy kontrolery Spring MVC z implementacji SOAP |

Zasady:

- Kod ma wyższy priorytet niż dokumentacja. Błędy w dokumentacji poprawia się w osobnym zadaniu.
- Nowe komponenty trafiają do pakietów `org.mercury` (nie `pro.ibpm.mercury`). Istniejące klasy migrują stopniowo i tylko na prośbę autora (decyzja D16).
- Zadanie działa na obecnej Javie 8 serwera. Nowe zależności muszą mieć bajtkod 1.8 i używać `javax`.
- `mercury-lib`: dozwolone zmiany z decyzji D6 (wariant B – katalog opisów pól z generatora DTO,
  wariant C – adnotacje `@WSDLDocumentation`), zmiany kontraktu XML z decyzji D7 (namespace elementów
  modelu obiektu MRC, `DtoPropertyMap`, testy kontraktowe) oraz parametr kontekstu `CASE_AS_TYPE` z decyzji D17.
  Bez zmian bajtkodu (1.8) i zależności runtime.
  Zmiana formatu XML wymaga etapu 3 przed wydaniem.
- Dokumentacja jest spójna i jednoznaczna: każdy element ma określone źródło opisu, a to samo wejście
  daje ten sam wynik.
- Zmiany w generatorze wymagają ponownego wygenerowania i commitu `mercury-ws-app/src/main/generated`.
- Wymagania JDK bibliotek dla etapów 1–2 są sprawdzone w POM-ach na Maven Central.
