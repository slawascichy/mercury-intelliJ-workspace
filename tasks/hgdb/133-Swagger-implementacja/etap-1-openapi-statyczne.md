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
- `mercury-lib` zmienia się tylko w zakresie decyzji D6 (warianty B i C) i D7 (kontrakt XML, zrobione,
  opis w [etapie 3](etap-3-zgodnosc-komunikacji-wezlow.md)): bez nowych zależności runtime, bajtkod 1.8.

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
  w `mercury-lib`, `hgdb-client-open`, `mercury-client` i `mercury-cmd` zostaje w zadaniu
  [191, etap 1](../191-Rewizja-wersji-migracja-Java17/etap-1-rewizja-wersji-java8.md).
- Ryzyko: zmiany zachowania Jacksona między 2.13 a 2.18+/2.22 (np. ograniczenia
  `StreamReadConstraints` od 2.15: maks. długość napisu 20 MB, liczby 1000 znaków, zagnieżdżenie 1000).
  Dotyczy dużych LOB-ów JSON w sprawach. Sprawdzić `JsonObjectMapper` i serializację `Context`/DTO w REST
  (przypuszczenie – zweryfikować testami).
- **Zrobione (2026-10-19): Jackson 2.18.2 w `mercury/pom.xml`** (`jackson.version` i `jackson.databind.version`), jedna wersja
  dla wszystkich modułów i generatora. Kompilacja bez zmian w kodzie, testy REST i JSON przechodzą. W
  `apache-tomcat/mercury/lib` podmieniono ręcznie jary `jackson-core`, `jackson-annotations` i `jackson-databind` (skrypt
  instalacyjny kopiuje tylko jary `mercury*` i `hgdb*`). Pakiet instalacyjny (`mercury-server/target/dependency`) dostaje
  teraz `jackson-dataformat-xml` 2.18.2 i `woodstox-core` 7.0.0 obok `woodstox-core-asl` 4.4.1 (tak jak wcześniej 2.13.2 i
  woodstox 6.2.7); w działającym serwerze tych jarów nie ma.
- **`StreamReadConstraints`:** domyślny limit długości napisu (20 000 000 znaków od Jacksona 2.15) odrzuca duże LOB-y JSON,
  więc `JacksonConstraintsListener` (`mercury-gui-core`, zarejestrowany w `web.xml` obu aplikacji przed
  `ContextLoaderListener`) przywraca brak limitu długości napisu. Pozostałe ograniczenia (liczba 1000 znaków,
  zagnieżdżenie 1000, nazwa pola 50 000) zostają domyślne. Test: `JacksonConstraintsListenerTest`.

| Element OpenAPI | Źródło |
|---|---|
| `paths` | `@RequestMapping` klasy i metody (`/rest/service/XxxRest/{metoda}`, POST, JSON) |
| `tags` | Klasa `XxxRest` / interfejs SOAP |
| `operation.summary` / `description` | `@WSDLDocumentation` metody (refleksja). Gdy jej brak: Javadoc metody interfejsu |
| `requestBody` | Wrapper `XxxRequest` (pola = parametry metody) |
| Opis pól `XxxRequest` | `@param` z Javadoc metody interfejsu |
| `components.schemas` | `ModelConverters` swagger-core dla encji (wejście) i kopert `WsStatusWith*` z `XxxDto` (wyjście). Rozumie adnotacje Jacksona |
| Opis pól schematów | Javadoc pól encji z `mercury-entities`. Dla DTO mapowanie `XxxDto.pole` → `Xxx.pole` |
| Opis kopert | `WsStatusWithXxxDto` → opis `XxxDto`, `WsStatusWithXxxDtos` → lista, `*PagedResult` → strona wyników. Pola `WsStatus` (`errorCode`, `errorMessage`) opisane raz, we wspólnym schemacie |

Javadoc czyta JavaParser 3.x ze źródeł `mercury-lib` (`${local-project-workspace-path}/mercury-lib`).

### Opisy pól DTO bez zmian w generatorze DTO

DTO i koperty odpowiedzi powstają w `mercury-lib` przez `mercury-entities-dto-generator`
(szczegóły w [TASK.md](TASK.md#generator-dto-mercury-entities-dto-generator-mercury-lib)).
Generator DTO nie przenosi Javadoc i w tym zadaniu **zostaje bez zmian**. Opisy dokleja generator REST:

1. Dla klasy `pro.ibpm.mercury.dto.XxxDto` wyznacza encję `Xxx`: usuwa sufiks `Dto`
   (`EntityHelper.DTO_NAME_SUFFIX`) i szuka klasy w pakietach encji (`EntityHelper.ENTITIES_MAIN_PACKAGE`
   + `EntityHelper.entityPrefixes`, tak jak `ClassGeneratorApp`).
2. Z pliku źródłowego encji (JavaParser) bierze Javadoc pól i klasy.
3. Ustawia `description` w schemacie `XxxDto` dla pól o tych samych nazwach. Ten sam opis trafia do
   schematu encji `Xxx` (wejście).
4. Pola bez Javadoc zostają bez opisu. Lista takich pól trafia do raportu generatora (log), żeby
   uzupełnić Javadoc w encjach.

Wygenerowane DTO nie są w repozytorium (`.gitignore`), ale nie jest to potrzebne. Generator REST
korzysta z klas DTO na classpath (zbudowany `mercury-entities`), a z Javadoc encji ze źródeł.

Rozszerzenie: patrz „Jedno źródło opisów” niżej (wariant B).

### Jedno źródło opisów – rola generatorów (decyzja D6)

W projekcie są trzy generatory i wszystkie działają na refleksji ze skompilowanych klas:

| Generator | Repozytorium | Co przenosi z kontraktu |
|---|---|---|
| `mercury-ws-app-rest-generator` | `mercury` | Nazwy parametrów z `@WebParam(name)`. Opisów nie przenosi |
| `mercury-entities-dto-generator` | `mercury-lib` | `@Id`, `@EmbeddedId`, `@MappedProperty*`. Javadoc nie przenosi |
| `mercury-ws-server-api20-generator` | `mercury` | Same sygnatury. Parametry dostają nazwy `arg0`, `arg1`…, bez `@WebParam` i bez `@WSDLDocumentation` (np. `IArchCaseAction` w `mercury-ws-server-api20/src/main/generated`) |

Javadoc znika przy kompilacji. Do refleksji docierają tylko adnotacje z retencją RUNTIME
(`@WSDLDocumentation`, `@WebParam`). `@WSDLDocumentation` jest dziś w 127 miejscach, a metod
w interfejsach `I*Action` jest około 770 (szacunek z `grep`). Część z tych 127 to opisy metody `echo`.

Opis jest „jednoznaczny”, gdy dla każdego elementu istnieje jedno źródło, czytane tak samo przez
WSDL, OpenAPI i ewentualnie GUI. Warianty:

| Wariant | Opisy operacji | Opisy pól encji i DTO | Zmiany | Ocena |
|---|---|---|---|---|
| **A. Generator REST czyta źródła** (obecny plan) | `@WSDLDocumentation`, a gdy jej brak – Javadoc interfejsu (JavaParser) | Javadoc encji (JavaParser) i mapowanie `XxxDto` → `Xxx` | Tylko `mercury` | Działa tylko z pełnym workspace na dysku (ścieżka do źródeł `mercury-lib`). Dwa źródła opisów operacji |
| **B. Generator DTO tworzy katalog opisów pól** | jak A | `ClassGeneratorApp` działa w module `mercury-entities`, więc ma źródła encji lokalnie (`src/main/java`). Czyta Javadoc pól (JavaParser) i zapisuje zasób, np. `META-INF/mercury/field-docs.json` (`klasa.pole → opis`), pakowany do jara `mercury-entities`. Opcjonalnie dopisuje też własną adnotację opisu do pól DTO | `mercury-lib` (generator DTO + JavaParser jako zależność czasu budowania). Bez nowych zależności runtime | Opisy pól jadą razem z artefaktem. Czytają je generator REST i serwer (etap 2 – nagłówek sprawy, koperty). Nie trzeba ścieżki do workspace |
| **C. Uzupełnić `@WSDLDocumentation`** w `mercury-ws-server-api` | Jedno źródło dla WSDL i OpenAPI | – | `mercury-lib` (tylko adnotacje, bez zmiany sygnatur) | Najbardziej jednoznaczne dla operacji. Praca ręczna przy ~640 metodach. Można to robić stopniowo: generator raportuje metody bez opisu |
| **D. Generator API 2.0 kopiuje `@WSDLDocumentation`** | Opisy także w WSDL dla API 2.0 | – | `mercury` | Tylko dla SOAP 2.0, nie wpływa na Swaggera. **Nie** kopiować `@WebParam(name)`: zmieniłoby nazwy parametrów w WSDL 2.0 (`arg0` → nazwa) i zepsuło zgodność starych klientów |

**Decyzja D6: A + B + C stopniowo, D opcjonalnie.**

- B rozwiązuje opisy pól bez zależności od układu katalogów. Generator DTO już działa we właściwym
  module i w tym samym kroku buildu. JavaParser ma bajtkod 1.8.
- C ustala jedno źródło opisu operacji. Do czasu uzupełnienia A daje Javadoc jako zapas.
- Retencja i dopuszczalne miejsca `@WSDLDocumentation` (metoda, typ, parametr) – przypuszczenie
  z wiedzy o CXF. Sprawdzić w `cxf-core` 3.0.x przed użyciem na parametrach.
- Warianty B i C zmieniają `mercury-lib` (dozwolone decyzją D6). Zmiany nie dotykają kontraktu:
  bez nowych zależności runtime, sygnatur i bajtkodu (dalej 1.8).

### Decyzje z 2026-10-18 (po szkielecie end-to-end)

- **D8. Naprawa `DtoMrcObject`/`DtoMrcList` w `mercury-lib`.** Konflikt settera JAXB z `List`
  (`Conflicting setter definitions for property "propertyNames"`) blokuje deserializację JSON także
  zwykłemu Jacksonowi. Konfiguracja `ObjectMapper` serwera naprawiłaby tylko serwer, a poprawka w
  `mercury-lib` naprawia też klientów Java (`hgdb-client-open`). Poprawka nie może zmienić kontraktu
  XML/JAXB: rozszerzyć `DtoLegacyXmlCompatibilityTest` o te klasy. Wymaga wydania `mercury-lib` i podbicia
  zależności w `mercury` i `hgdb-client-open`. Do czasu wydania zostaje w generatorze obejście (mixin
  `DtoMrcObjectMixin` i fallback `object`).
- **D9. `@WSDLDocumentation` jedynym trwałym źródłem opisów.** Cel: przy generacji dokumentacji korzystać z
  jednego, najwyżej dwóch nośników (`@WSDLDocumentation` plus ewentualnie katalog opisów pól z wariantu B).
  Javadoc i istniejące opisy służą do jednorazowego przeniesienia treści do `@WSDLDocumentation`, a nie jako
  stałe źródło. Wariant C przestaje być pracą ciągłą poza DoD i wchodzi do zadania. Źródło 2 (Javadoc, wariant A)
  zostaje tylko na czas migracji. Skalę (~770 metod w `I*Action`, 127 istniejących adnotacji) i podział na kroki
  ustalić po sprawdzeniu aktualnego stanu adnotacji.
  **Stan z 2026-10-18 (pomiar `mercury-ws-server-api`, przybliżony):** 74 interfejsy, ok. 895 deklaracji metod,
  ok. 700 z Javadoc (opis), 117 z `@WSDLDocumentation` (63 to `echo`), ok. 170 bez żadnego opisu. `@WSDLDocumentation`
  z CXF 3.0.10 ma `@Target({TYPE, METHOD})` i retencję RUNTIME, więc **nie może stać na parametrze**.
- **D12. Opisy parametrów w tekście `@WSDLDocumentation` metody.** Jedno medium dla operacji i parametrów. Format
  tekstu (stały, rozdzielany przez generator): opis metody (akapity rozdzielone pustą linią), po pustej linii
  `Parametry:` i linie `- nazwa: opis`, po pustej linii `Zwraca: opis`. Bloki są opcjonalne. Opisy pól encji i DTO
  zostają drugim medium (katalog opisów z generatora DTO, wariant B). Razem dwa media. Skutek uboczny: opisy
  parametrów trafią też do `wsdl:documentation` (zmiana tylko dokumentacyjna, kontrakt WSDL bez zmian).
- **D13. Migracja jednorazowa z Javadoc.** Narzędzie czyta Javadoc interfejsów `I*Action` (JavaParser 3.23.1) i dopisuje
  `@WSDLDocumentation` na metodach i interfejsach (adnotacja już istniejąca zachowuje swój opis, dostaje tylko bloki
  `Parametry:` i `Zwraca:`). Po migracji źródłem jest adnotacja, a Javadoc dokumentuje kod. Metody bez żadnego opisu
  trafiają do raportu braków do ręcznego uzupełnienia.
- **D14. Kontrolery `*ExtRest` opisuje refleksja w `mercury-ws-app`, scalana w locie.** Generator jest osobnym modułem
  budowanym przed `mercury-ws-app`, więc nie widzi tych klas. Nowa klasa w `mercury-ws-app` (`org.mercury.rest.server.actions.ExtRestOpenApi`) czyta kontrolery `*ExtRest`
  (adnotacje Spring, klasy `*Request`, bez pakietu `rest2`) i buduje operacje w formacie specyfikacji generatora.
  `OpenApiController` dokleja je (ścieżki, tagi, schematy) do statycznego `openapi.json`. Żądania `save` i `initModel`
  przyjmują surowy JSON sprawy (`String`), a odpowiedzią jest zawsze koperta JSON (`errorCode`, `errorMessage` i dane).
  Typowanie JSON-a konkretnego typu sprawy to etap 2. Klasa `ExtRestOpenApi` używa tylko Jacksona (drzewo JSON) i parsera
  opisów z generatora, bo biblioteki swagger-core są w generatorze w zakresie `provided` i nie trafiają do WAR-a
  (ich Jackson jest nowszy od serwerowego). Metody `save` i `initModel` przyjmują `String`, który kontroler sam parsuje do
  obiektu `{context, jsonNode, forceAddStore2Type}`, więc klasę żądania wskazuje adnotacja `@ExtRestRequest`. Żądania
  zagnieżdżone w wygenerowanych kontrolerach (`CaseBusinessRest.FindRequest`) odwołują się do istniejących schematów.
  Wynik: 32 operacje w 4 usługach, bez braków opisów (test `ExtRestOpenApiTest`).
- **D15. Opisy `*ExtRest` w `@WSDLDocumentation` na interfejsach `I*ExtRest`.** Ta sama adnotacja i ten sam format
  (D12) co dla usług SOAP, więc jedno medium i jeden parser. Adnotacja nie trafia do WSDL, bo kontrolery REST nie są
  usługami SOAP. Braki opisów są raportowane i pilnuje ich test.
- **D10. Jackson na serwerze podbijamy w tym zadaniu.** Ostatni krok etapu 1, osobny commit, z pełnym
  przebiegiem testów REST (`JSONSerializationTest`, zapis i odczyt spraw przez `*ExtRest`, duże LOB-y JSON).
- **D11. Zakres bezpieczeństwa.** Usługi `/rest/service/**` chronione OAuth (filtr `OAuthFilter`), dokumentacja
  (`/rest/openapi.json`, `/swagger-ui/`) publiczna. Szczegóły w „Otwartych kwestiach”.

Kolejność dalszych prac: OAuth w specyfikacji → walidacja swagger-parserem → D8 → D9 (migracja opisów,
raport braków) → `*ExtRest` → D10 → etap 2 → dokumentacja → wydanie.

### Zasada spójności i jednoznaczności

Cel: dokumentacja jest spójna i generowana jednoznacznie na podstawie określonych danych.

**1. Każdy element ma ustaloną kolejność źródeł.** Generator bierze pierwsze niepuste:

| Element OpenAPI | Źródło 1 (docelowe) | Źródło 2 (zapas, wariant A) | Brak opisu |
|---|---|---|---|
| `operation.summary` / `description` | `@WSDLDocumentation` metody interfejsu (C) | Pierwsze zdanie / całość Javadoc metody interfejsu | Pozycja w raporcie braków |
| Opis parametru (pole `XxxRequest`) | `@WSDLDocumentation` parametru, jeśli CXF na to pozwala (C, do sprawdzenia) | `@param` z Javadoc metody | Pozycja w raporcie braków |
| `tags` (opis klasy usługi) | `@WSDLDocumentation` interfejsu (C) | Javadoc interfejsu | Pozycja w raporcie braków |
| Opis pola encji / DTO | Katalog opisów pól z jara `mercury-entities` (B) | Javadoc pola encji czytany ze źródeł (A) | Pozycja w raporcie braków |
| Opis schematu encji / DTO | Katalog opisów (B, Javadoc klasy) | Javadoc klasy encji (A) | Pozycja w raporcie braków |
| Pola typu sprawy (etap 2) | Metadane typu (`TypeParam`, `ParamDefinition`, zasoby `${…}`) | – | `definitionName` |

Gdy oba źródła istnieją i się różnią, wygrywa źródło 1, a różnica trafia do raportu.
Z czasem (C, B) źródło 2 przestaje być potrzebne.

**2. To samo wejście daje ten sam wynik.**

- Specyfikacja bez znaczników czasu i wartości losowych. Wersja specyfikacji (`info.version`)
  = wersja artefaktu `mercury` (`project.version`).
- Stała kolejność: ścieżki, operacje, schematy i pola sortowane alfabetycznie (pola typu sprawy –
  po `position`). Serializacja z posortowanymi kluczami.
- Ten sam generator i ten sam model (swagger-models) dla etapu 1 i 2. Wspólne schematy (`WsStatus`,
  `Context`, `MrcCaseHeader`) zdefiniowane w jednym miejscu i używane przez `$ref`.
- Uwaga: generator REST zapisuje datę w `@javax.annotation.Generated` każdej klasy
  (`CaseRest.java:36`). Każde uruchomienie zmienia więc wszystkie 92 pliki w repozytorium.
  Do rozważenia: datę pomijać albo brać z `project.build.outputTimestamp` (powtarzalny build).
  Generatory DTO i API 2.0 robią to samo, ale ich wyników nie ma w gicie.

**3. Raport braków.** Każde uruchomienie generatora zapisuje raport (np.
`target/openapi-doc-report.txt` lub log), w którym są: metody bez `@WSDLDocumentation`, parametry
bez opisu, pola encji bez Javadoc i rozbieżności między źródłami. Raport wskazuje, co uzupełnić
w ramach wariantu C i Javadoc encji.

**4. Kolejność realizacji w etapie 1.**

| Krok | Zakres | Repozytorium |
|---|---|---|
| 1 | Generator REST: specyfikacja, raport braków, źródła z wariantu A, deterministyczny zapis. Podbicie Jacksona, serwowanie, Swagger UI | `mercury` |
| 2 | Wariant B: generator DTO zapisuje katalog opisów pól do jara `mercury-entities`. Generator REST czyta katalog jako źródło 1 | `mercury-lib`, `mercury` |
| 3 | Wariant C (decyzja D9): migracja opisów do `@WSDLDocumentation` według raportu braków. W zakresie etapu 1 | `mercury-lib` |
| 4 | Wariant D (opcjonalnie): generator API 2.0 kopiuje `@WSDLDocumentation`, bez `@WebParam` | `mercury` |

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
| `@Schema` w DTO przez `DtoClassGenerator` | Wymaga `swagger-annotations` w `mercury-lib` i czytania źródeł encji w generatorze DTO. Możliwe jako rozszerzenie (patrz wyżej) |
| Ręczny YAML | Za dużo pracy przy 92 klasach. Sens tylko jako uzupełnienie |

### Otwarte kwestie

- Kolejność w reaktorze: `mercury-ws-app` buduje się przed generatorem. Specyfikacja, tak jak
  klasy REST, będzie commitowana w `src/main/generated` (lub `src/main/resources`).
- Czytanie Javadoc po ścieżce działa tylko na stacji z pełnym workspace. Rozwiązania: wariant B
  (katalog opisów pól w jarze `mercury-entities`) albo `maven-source-plugin` w `mercury-lib`
  i czytanie z jara `-sources`.
- Generator `RestSourceGenerator2` (`.rest2.`, przestarzały): pominąć w specyfikacji.
- ✅ **Rozwiązane (D14, D15).** Ręcznie pisane kontrolery `*ExtRest` (`CaseBusinessExtRest`, `CaseSearchExtRest`,
  `Case2CaseBusinessExtRest`, `CaseHistoryTraceBusinessExtRest`) nie powstają w generatorze.
  Zwracają `String` z JSON-em, a `save`/`initModel` przyjmują surowy `String`. Ich opis w specyfikacji
  wymaga osobnego źródła: ręcznego fragmentu specyfikacji albo skanowania tych klas refleksją
  w generatorze. Część związaną z typem sprawy opisuje [etap 2](etap-2-openapi-typy-spraw.md).
- Uwierzytelnianie OAuth usług REST (schemat `securitySchemes`). **Wymaganie:** usługi nie mogą być
  niezabezpieczone. Specyfikacja musi deklarować schemat OAuth i wymóg `security` dla każdej operacji,
  a Swagger UI musi umożliwiać autoryzację („Authorize”) przed „Try it out”.
  Zabezpieczenie realizują filtry z `mercury-ws-app/src/main/webapp/WEB-INF/web.xml`, oba przypięte do
  serwletu `moduleDb-3.0` (mapowanie `/`): `org.mercury.gui.filters.XSSFilter` i
  `pro.ibpm.mercury.oauth.OAuthFilter` (`oauthConfigId=mercury-db:1`, `oauthFactoryName=mercuryDbOAuthFactory`).
  Specyfikacja ma więc tylko opisać istniejące zabezpieczenie, a nie je dodawać.
  Z kodu `OAuthFilter` (mercury-gui-core): filtr działa tylko przy `mercury.oauth.filter.enabled=true`;
  chronione ścieżki wynikają z konfiguracji `MercurySecurityOAuthConfig` (kontekst + `servletPath`);
  token pobiera się z `accessTokenURI` (`/rest/token`, w konfiguracji klienci `GIUPortalClient` i `GIUSoapUIClient`);
  zakresy (`scopes`) są sprawdzane względem tokenu. Do ustalenia: typ przepływu w `securitySchemes`
  (z `/rest/token` wygląda na `password` lub `clientCredentials`, przypuszczenie do potwierdzenia w kodzie
  `OAuthService`).
  **Decyzja:** `/rest/openapi.json` i `/swagger-ui/` są publiczne (bez uwierzytelnienia). Konfiguracja
  `mercury-db:1` nie może ich oznaczać jako chronionych, a usługi `/rest/service/**` pozostają chronione.
  Wzorzec `/rest/**` obejmował też `/rest/openapi.json`, więc w konfiguracji `mercury-db:1` zawężono go do
  `/rest/service/**` (decyzja A, bez zmiany kodu `OAuthFilter`). Wzorzec trzeba zmienić w każdej instalacji:
  `mercury-server/src/main/config/scichy`, `mercury-docker/mercury-3.0/docker-init-config` i
  `mercury-cmd/mercury-install-package/system-config-sample/linux` (wszystkie trzy zrobione, dwa ostatnie
  w osobnych repozytoriach, niezatwierdzone). Konfiguracja `jenkins` używa innego `configId` (`portal:32424`),
  a `mercury-security-config-rgx-1.0.0.xml` dotyczy `mercury-gui-registry`, więc ich nie zmieniano.
  Test `OpenApiResourcesTest.testOAuthSecurityConfigKeepsDocumentationPublic` pilnuje tylko pliku z `mercury`.
  Do sprawdzenia: wartość `mercury.oauth.filter.enabled` (w konfiguracji `scichy` nie znalazłem tego klucza,
  więc lokalnie filtr jest prawdopodobnie wyłączony) i które ścieżki konfiguracja `mercury-db:1` oznacza jako
  chronione, w tym `/rest/service/**`.

## Definicja Gotowości (DoD)

- Generator tworzy poprawną specyfikację OpenAPI 3 (walidacja np. `swagger-parser`) dla wszystkich
  usług z pakietu `.rest.`.
- Każda operacja ma `summary`, gdy źródło (`@WSDLDocumentation` lub Javadoc) zawiera opis.
- Schematy encji i DTO mają opisy pól z katalogu opisów (B) albo z Javadoc encji (A).
- Generator stosuje kolejność źródeł z „Zasady spójności” i zapisuje raport braków.
- Dwa kolejne uruchomienia generatora na tym samym kodzie dają identyczną specyfikację (porównanie bajt po bajcie).
- Specyfikacja deklaruje OAuth (`securitySchemes`) i `security` dla wszystkich operacji. Żadna usługa REST
  nie jest dostępna bez uwierzytelnienia, a Swagger UI pozwala się autoryzować.
- Serwer udostępnia specyfikację i Swagger UI. Wywołanie „Try it out” działa dla co najmniej
  `TypeCaseRest/findLastVersionByTypeCode` i `CaseRest/findByKey`.
- `mercury-lib` zmieniony tylko w zakresie wariantu B (krok 2) i kontraktu XML z D7. Build `mercury-lib` i `mercury` przechodzi na Javie 8.
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
| `mercury-lib/mercury-entities-dto-generator/src/main/java/pro/ibpm/mercury/entities/dto/generator/ClassGeneratorApp.java`, `DtoClassGenerator.java` | Wariant B: katalog opisów pól |
| `mercury-lib/mercury-entities-dto-generator/pom.xml` | JavaParser (zależność generatora, nie runtime) |
| `mercury-lib/mercury-ws-server-api/src/main/java/` | Wariant C: `@WSDLDocumentation` |
| `mercury/mercury-ws-server-api20-generator/src/main/java/org/mercury/ws/server20/generator/Ws20SourceGenerator.java` | Wariant D (opcjonalnie) |

## Słownik / Zasady

- `@WSDLDocumentation`: adnotacja CXF z opisem operacji SOAP. Główne źródło `summary`.
- Wrapper `XxxRequest`: klasa wewnętrzna kontrolera REST z parametrami metody SOAP.
