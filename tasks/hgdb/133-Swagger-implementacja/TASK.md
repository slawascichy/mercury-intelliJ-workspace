# [133] Swagger - Implementacja

## Cel zadania
Wdrożenie dokumentacji OpenAPI/Swagger dla modułu `mercury-ws-app`.

Zadanie obejmuje dwa obszary:

1. Adnotacje i opisy OpenAPI dla usług REST, które generuje moduł `mercury-ws-app-rest-generator`.
2. „Dynamiczna” dokumentacja OpenAPI dla podanego kodu typu sprawy (ostatnia albo wskazana wersja typu).

Rewizję wersji oprogramowania i migrację serwera na Javę 17 wydzielono do zadania
[191 – Rewizja wersji i migracja na Javę 17](../191-Rewizja-wersji-migracja-Java17/TASK.md).

## Podział na etapy

| Etap | Plik | Zakres | Zależy od |
|---|---|---|---|
| 1 | [etap-1-openapi-statyczne.md](etap-1-openapi-statyczne.md) | Generator emituje specyfikację OpenAPI usług REST, serwowanie specyfikacji i Swagger UI, podbicie Jacksona na serwerze | – |
| 2 | [etap-2-openapi-typy-spraw.md](etap-2-openapi-typy-spraw.md) | Dynamiczny schemat OpenAPI dla kodu typu sprawy | Etap 1 (infrastruktura serwowania) |

Swagger nie wymaga zmiany Javy ani zadania 191. Jedyny punkt wspólny to wersja Jacksona na serwerze
(patrz niżej): jego podbicie należy do etapu 1 tego zadania.

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
| DTO z `mercury-entities-dto-generator` | – | `DtoClassGenerator.java:244-330` nie kopiuje Javadoc |

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
| D5 | Wersja swagger-core (etapy 1–2) | (a) 2.2.0 z obecnym Jacksonem 2.13.2, OpenAPI 3.0; (b) nowsza 2.2.x (od 2.2.8 OpenAPI 3.1) z podbiciem Jacksona na serwerze | ✅ **(b)**. Podbicie Jacksona w `mercury/pom.xml` należy do [etapu 1](etap-1-openapi-statyczne.md). Java bez zmian |

## Definicja Gotowości (DoD)

- Zrealizowane etapy 1 i 2 według ich DoD.
- Dokumentacja workspace zaktualizowana: `docs/moduly/mercury.md` (Swagger, nowe endpointy,
  wersja Jacksona), nowe pozycje w `docs/obserwacje.md`.

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
- Zadanie działa na obecnej Javie 8 serwera. Nowe zależności muszą mieć bajtkod 1.8 i używać `javax`.
- `mercury-lib` zostaje bez zmian.
- Zmiany w generatorze wymagają ponownego wygenerowania i commitu `mercury-ws-app/src/main/generated`.
- Wymagania JDK bibliotek dla etapów 1–2 są sprawdzone w POM-ach na Maven Central.
