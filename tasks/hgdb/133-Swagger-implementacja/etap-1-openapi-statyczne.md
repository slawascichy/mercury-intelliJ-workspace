# [133] Etap 1 – Specyfikacja OpenAPI usług REST

Zadanie nadrzędne: [TASK.md](TASK.md).

## Cel zadania
Generator `mercury-ws-app-rest-generator` tworzy specyfikację OpenAPI 3 dla wszystkich usług REST
`mercury-ws-app` wraz z opisami operacji, parametrów i pól. Serwer udostępnia specyfikację
i Swagger UI.

## Kontekst i Wymagania

- REST to Spring MVC, a nie CXF JAX-RS. Szczegóły w [TASK.md](TASK.md#stos-rest-w-mercury-ws-app).
- Generator zna metody, parametry (`@WebParam`) i typy wejścia/wyjścia z refleksji.
  Brakuje mu tylko opisów.
- `mercury-lib` zostaje bez zmian (Java 8, bez nowych zależności).

### Wybrany wariant (decyzja D1 = a)

Generator, poza klasami `XxxRest`, zapisuje plik `openapi.json` (lub YAML) zbudowany na modelu
`io.swagger.core.v3:swagger-models` 2.2.x (wariant `javax`, bajtkod 1.8 – sprawdzone, patrz
[TASK.md](TASK.md#biblioteki-dla-etapów-12-na-javie-8-sprawdzone-w-pom-ach-na-maven-central-2026-10-16)).
Decyzja D5: nowsza wersja swagger-core 2.2.x (OpenAPI 3.1) z podbiciem Jacksona na serwerze.

### Podbicie Jacksona (przeniesione z zadania 191, etap 1)

- Obecnie: `jackson` 2.13.2, `jackson-databind` 2.13.2.2 (`mercury/pom.xml:118-119`).
- Cel: wersja Jacksona zgodna z wybranym swagger-core (właściwość `jackson-version` w
  `io.swagger.core.v3:swagger-project`), np. swagger-core 2.2.55 → Jackson 2.22.1,
  swagger-core 2.2.30 → Jackson 2.18.2. Wersję wybrać przy wdrożeniu, najlepiej przez import
  `com.fasterxml.jackson:jackson-bom` w `dependencyManagement`, żeby wszystkie moduły Jacksona miały
  tę samą wersję.
- Zakres: tylko repozytorium `mercury`. `mercury-lib` kompiluje się przeciw Jacksonowi 2.12.6.1
  w scope `provided`, więc w runtime serwera i tak działa wersja serwera. Wyrównanie Jacksona
  w `mercury-lib`, `hgdb-client-open`, `mercury-client` i `mercury-cmd` zostaje w etapie 3.
- Ryzyko: zmiany zachowania Jacksona między 2.13 a 2.18+/2.22 (np. ograniczenia
  `StreamReadConstraints` od 2.15: maks. długość napisu 20 MB, liczby 1000 znaków, zagnieżdżenie 1000).
  Dotyczy dużych LOB-ów JSON w sprawach. Sprawdzić `JsonObjectMapper` i serializację `Context`/DTO w REST
  (przypuszczenie – zweryfikować testami).

| Element OpenAPI | Źródło |
|---|---|
| `paths` | `@RequestMapping` klasy i metody (`/rest/service/XxxRest/{metoda}`, POST, JSON) |
| `tags` | Klasa `XxxRest` / interfejs SOAP |
| `operation.summary` / `description` | `@WSDLDocumentation` metody (refleksja). Gdy jej brak: Javadoc metody interfejsu |
| `requestBody` | Wrapper `XxxRequest` (pola = parametry metody) |
| Opis pól `XxxRequest` | `@param` z Javadoc metody interfejsu |
| `components.schemas` | `ModelConverters` swagger-core dla encji i `WsStatusWith*Dto` (rozumie adnotacje Jacksona) |
| Opis pól schematów | Javadoc pól encji z `mercury-entities`. Dla DTO mapowanie `XxxDto.pole` → `Xxx.pole` |

Javadoc czyta JavaParser 3.x ze źródeł `mercury-lib` (`${local-project-workspace-path}/mercury-lib`).

Serwowanie:

- Kontroler w `mercury-ws-app` udostępnia plik, np. `GET /rest/openapi.json`, obok
  istniejącego `/restServices/{serviceName}.wadl`.
- Swagger UI z webjara (`org.webjars:swagger-ui`) jako zasób statyczny.

### Alternatywy (odrzucone wstępnie)

| Wariant | Powód odrzucenia |
|---|---|
| Adnotacje `@Tag`/`@Operation`/`@Schema` w klasach `XxxRest` + springdoc 1.8.x | springdoc zakłada Spring Boot. Bez niego konfiguracja jest krucha (przypuszczenie). Adnotacje można dodać później, równolegle do pliku |
| springfox 2.9.2 | Swagger 2, projekt nierozwijany |
| therapi-runtime-javadoc | Wymaga zmian w buildzie `mercury-lib` |
| `@Schema` w DTO przez `DtoClassGenerator` | Wymaga `swagger-annotations` w `mercury-lib`. Możliwe jako rozszerzenie (wersja zgodna z Javą 8) |
| Ręczny YAML | Za dużo pracy przy 92 klasach. Sens tylko jako uzupełnienie |

### Otwarte kwestie

- Kolejność w reaktorze: `mercury-ws-app` buduje się przed generatorem. Specyfikacja, tak jak
  klasy REST, będzie commitowana w `src/main/generated` (lub `src/main/resources`).
- Czytanie Javadoc po ścieżce działa tylko na stacji z pełnym workspace. Do rozważenia:
  `maven-source-plugin` w `mercury-lib` i czytanie z jara `-sources`.
- Generator `RestSourceGenerator2` (`.rest2.`, przestarzały): pominąć w specyfikacji.
- Ręcznie pisane kontrolery `*ExtRest` (`CaseBusinessExtRest`, `CaseSearchExtRest`,
  `Case2CaseBusinessExtRest`, `CaseHistoryTraceBusinessExtRest`) nie powstają w generatorze.
  Zwracają `String` z JSON-em, a `save`/`initModel` przyjmują surowy `String`. Ich opis w specyfikacji
  wymaga osobnego źródła: ręcznego fragmentu specyfikacji albo skanowania tych klas refleksją
  w generatorze. Część związaną z typem sprawy opisuje [etap 2](etap-2-openapi-typy-spraw.md).
- Uprawnienia i uwierzytelnianie endpointów (schemat `securitySchemes`) – do ustalenia.

## Definicja Gotowości (DoD)

- Generator tworzy poprawną specyfikację OpenAPI 3 (walidacja np. `swagger-parser`) dla wszystkich
  usług z pakietu `.rest.`.
- Każda operacja ma `summary`, gdy źródło (`@WSDLDocumentation` lub Javadoc) zawiera opis.
- Schematy encji i DTO mają opisy pól z Javadoc encji.
- Serwer udostępnia specyfikację i Swagger UI. Wywołanie „Try it out” działa dla co najmniej
  `TypeCaseRest/findLastVersionByTypeCode` i `CaseRest/findByKey`.
- `mercury-lib` bez zmian. Build `mercury` przechodzi na Javie 8.
- Jackson na serwerze podbity do wersji zgodnej z swagger-core (jedna wersja dla wszystkich modułów
  Jacksona). Testy REST (`JSONSerializationTest`, zapis i odczyt spraw przez `*ExtRest`, w tym duże LOB-y JSON) przechodzą.
- Wygenerowane pliki zacommitowane. Opis w `docs/moduly/mercury.md`.

## Kluczowe Pliki w Projekcie

| Plik | Zmiana |
|---|---|
| `mercury/mercury-ws-app-rest-generator/src/main/java/org/mercury/rest/server/generator/RestSourceGenerator.java` | Zbieranie danych do specyfikacji |
| `mercury/mercury-ws-app-rest-generator/src/main/java/org/mercury/rest/server/generator/RestSourceGeneratorApp.java` | Zapis specyfikacji |
| `mercury/mercury-ws-app-rest-generator/pom.xml` | Zależności: swagger-core, JavaParser; ścieżka do źródeł `mercury-lib` |
| `mercury/pom.xml` | Wersja Jacksona (`jackson-bom`), wersja swagger-core |
| `mercury/mercury-ws-app/pom.xml` | Webjar Swagger UI, swagger-core |
| `mercury/mercury-ws-app/src/main/java/pro/ibpm/mercury/rest/server/actions/` | Kontroler specyfikacji |
| `mercury/mercury-ws-app/src/main/webapp/WEB-INF/moduleDb-3.0-servlet.xml` | Mapowanie zasobów Swagger UI |

## Słownik / Zasady

- `@WSDLDocumentation`: adnotacja CXF z opisem operacji SOAP. Główne źródło `summary`.
- Wrapper `XxxRequest`: klasa wewnętrzna kontrolera REST z parametrami metody SOAP.
