# [58] Logger - dynamiczne zmiana poziomów logowania

W HSBC zrobiłem obsługę log4j z dynamiczną zmianą parametrów poziomu logowania. Jest to bardzo przydatne rozwiązanie gdy chcemy bez restartu uchwycić problem.

## Cel

Efektem końcowym byłoby:

1. Usługa **REST** (bez SOAP; decyzja autora z 2026-10-26) z metodami:
   - pobranie obecnego poziomu logowania dla danej kategorii
   - zmiana obecnego poziomu logowania dla danej kategorii
   - wyszukiwanie kategorii, ale z tym ostrożnie, bo wynik wyszukiwania może być bardzo duży. Najlepiej założyć, że zwraca 10, 20 max. 30 wyników
2. w aplikacji webowej mercury-ws-ap panel administracyjny pozwalający zarządzać poziomami logowania.

## Zaktualizowane cele (2026-10-26)

Decyzja autora: zadanie obejmuje **tylko REST**. SOAP jest niepotrzebny na obecnym poziomie i kierunku rozwoju aplikacji.

1. Usługa REST z operacjami: pobranie poziomu logowania dla kategorii, zmiana poziomu dla kategorii, wyszukiwanie kategorii (wynik ograniczony do 10, 20, najwyżej 30 pozycji).
2. Panel administracyjny w aplikacji webowej `mercury-ws-app` do zarządzania poziomami logowania.
3. Opis w specyfikacji OpenAPI (sześć języków: pl, en, de, es, fr, ko), uprawnienia tylko dla administratora (przypuszczenie, do potwierdzenia), test jednostkowy zmiany poziomu.

Uwagi z rozpoznania kodu:

- Usługi REST pisane ręcznie (`I*ExtRest`, np. `ICaseSearchExtRest`) leżą w `mercury-ws-app` (repozytorium `mercury`). Usługa REST-only nie wymaga więc zmian w `mercury-lib`
  ani wydania biblioteki (przypuszczenie: dopóki DTO operacji nie trafią do `mercury-lib`).
- Backend logowania wymaga ustalenia: `mercury/pom.xml` ma jednocześnie `slf4j-reload4j` (log4j 1.x API) i `log4j-core` 2.17.2, a skrypty startowe używają `-Dlog4j.configuration` (styl log4j 1.x).

## Rozpoznanie logowania i podatności log4j (2026-10-27)

Fakty z kodu i plików konfiguracyjnych (niczego nie uruchamiano):

| Repozytorium | Zależności logowania w POM | Importy `org.apache.log4j.*` (log4j 1.x) | Importy `org.apache.logging.log4j.*` (log4j 2) |
|---|---|---|---|
| `mercury` | `slf4j-api` 1.7.36, `slf4j-reload4j` 1.7.36 (scope `provided`), `log4j-core` 2.17.2 (`provided`, w korzeniu i w `mercury-ws-app`) | 7 plików (5 testów; w `main`: `SequenceIntervalGenerator`, `mercury-mock/TestPropertiesLoader`) | 0 |
| `mercury-lib` | `slf4j-log4j12`, `log4j` 1.2.17 | 6 | 0 |
| `hgdb-client-open` | `slf4j-log4j12`, `log4j` 1.2.14 | 1 | 0 |
| `mercury-client` | `slf4j-log4j12`, `log4j` 1.2.14 | 5 | 0 |
| `mercury-cmd` | `slf4j-log4j12`, `log4j.version` 2.17.2 | 1 | 0 |

- **Konfiguracja runtime to styl log4j 1.x:** `-Dlog4j.configuration=file://${TOMCAT_HOME}/lib/log4j.properties` (obraz Docker, pakiet instalacyjny), pliki `log4j.properties` z `org.apache.log4j.DailyRollingFileAppender`/`RollingFileAppender`.
  Przy `slf4j-reload4j` (binding do forka `reload4j`) kategorie i poziomy zmienia API `org.apache.log4j.LogManager`.
- **`log4j-core` 2.17.2 nie ma użytkowników w kodzie.** Żaden plik w pięciu repozytoriach nie importuje API log4j 2, a `mercury` deklaruje go jako `provided` (nie trafia do WAR; `mercury-ws-app.war` nie zawiera żadnych jarów logowania).
  Przypuszczenie: został dodany po Log4Shell jako wymuszenie wersji. Czy coś na serwerze używa go w czasie wykonania, zależy od jarów w `lib/` Tomcata pakietu instalacyjnego, których nie ma w repozytoriach.
- **Jarów logowania w czasie wykonania nie da się ustalić z repozytoriów.** Pochodzą z pakietu instalacyjnego (`mercury-cmd`) i obrazu Docker, a lokalnie rozpakowane drzewa nie zawierają `log4j*.jar`.
  Potrzebne: lista jarów z działającego Tomcata (`lib/`) albo z ZIP-a pakietu.
- **`slf4j-log4j12` z log4j 1.2.14 i 1.2.17 (cztery repozytoria) to wersje wycofane** (log4j 1.x ma znane podatności, np. CVE-2019-17571 i CVE-2021-4104; z pamięci, do potwierdzenia skanerem zależności).

### Opcje pozbycia się log4j

| Opcja | Zakres | Zalety | Ryzyka |
|---|---|---|---|
| A. Logback 1.2.x (Java 8) | Zastąpić `slf4j-reload4j` i `slf4j-log4j12` przez `logback-classic`; przekonwertować `log4j.properties` na `logback.xml` (obraz Docker, pakiet, `mercury-cmd`, testy); usunąć `log4j-core` | Usuwa wszystkie log4j (1.x i 2.x); dynamiczna zmiana poziomów przez `LoggerContext` jest prosta; aktywnie rozwijany | Zmiana konfiguracji w trzech repozytoriach i w pakiecie; 7 plików z `org.apache.log4j.*` do przepisania; wersja 1.2.x kończy się na Javie 8 (po migracji do Javy 17 w 191 można przejść na nowszą) |
| B. Zostać przy reload4j | Usunąć `log4j-core` 2.17.2 oraz `slf4j-log4j12` i `log4j` 1.2.x (zastąpić `slf4j-reload4j`); bez zmian konfiguracji | Najmniejsza zmiana; konfiguracje `log4j.properties` bez zmian; reload4j to utrzymywany fork z poprawkami podatności log4j 1.2 | Nazwa „log4j” zostaje w skanerach; fork ma te same ograniczenia projektowe 1.x |
| C. JUL (`java.util.logging`) | `slf4j-jdk14`, `logging.properties` | Zero dodatkowych bibliotek, Tomcat i tak używa JULI | Najuboższe appendery (rolling), przepisanie wszystkich konfiguracji |

### Rekomendacja (przypuszczenie, do decyzji autora)

1. **Usługę z 058 napisać niezależnie od backendu.** Warstwa `ILoggerLevelService` wykrywa backend po `LoggerFactory.getILoggerFactory()` i ma adaptery: reload4j (`org.apache.log4j.LogManager`) oraz Logback (`LoggerContext`). Dzięki temu 058 nie blokuje migracji i działa w obu wariantach.
2. **Migrację backendu zrobić osobnym zadaniem przed wydaniem (faza D),** w wariancie B jako krok minimalny (usunięcie `log4j-core` 2.17.2 i `slf4j-log4j12` 1.2.x), a w wariancie A jako docelowy.
3. **Krok 0 przed decyzją:** lista jarów logowania z działającego Tomcata i skan zależności (np. OWASP Dependency-Check) na WAR i pakiecie, żeby policzyć, co faktycznie jest podatne.

## Realizacja (2026-10-27, `mercury`, gałąź `hgdb-058`, bez commitu)

Decyzja autora: logowanie migrujemy na Logback (zadanie `214-Migracja-logowania-na-Logback`), a usługa 058 działa niezależnie od backendu.

**Kod (`mercury-ws-app`, pakiet `org.mercury.logging` i `org.mercury.rest.server.actions.logging`):**

| Element | Rola |
|---|---|
| `ILoggerBackend`, `LoggerInfo`, `LoggerLevel` | Interfejs backendu, stan kategorii (nazwa, poziom ustawiony, poziom obowiązujący), poziomy `TRACE`..`OFF` i `INHERIT` (usuwa poziom ustawiony wprost) |
| `LogbackLoggerBackend` | Adapter Logbacka (`LoggerContext`) |
| `Log4j1LoggerBackend` | Adapter log4j 1.x (działa z log4j 1.2.14 na serwerze i z reload4j); do usunięcia po migracji |
| `LoggerBackends` | Wybór backendu po fabryce loggerów SLF4J (`LoggerContext`, `Log4jLoggerFactory`, `Reload4jLoggerFactory`); nieobsługiwany backend daje czytelny błąd |
| `LoggerLevelService` | Walidacja nazwy (litery, cyfry, `. _ $ -`, do 256 znaków) i poziomu, limit wyszukiwania: domyślnie 20, najwyżej 30, wynik z flagą `truncated` |
| `LoggerLevelsExtRest` (`/rest/service/LoggerLevelsExtRest`) | Operacje `getLevel`, `setLevel`, `search`; koperta JSON jak w innych `*ExtRest` |
| `static/admin/loggers.html` | Panel: logowanie OAuth (przepływ password, `../../rest/token`) albo wklejony token, wyszukiwanie, zmiana poziomu w tabeli, pojedyncza kategoria; pl i en |

- **Uprawnienia (przypuszczenie autora potwierdzone tylko częściowo, do decyzji):** odczyt wymaga `isAllRO()`, zmiana `isAllRW()` w `SecurityContextHelperBean` (dostęp do wszystkich typów). W repozytorium nie ma osobnego pojęcia roli administratora; ten sam wzorzec stosuje `CaseViewDefinitionLogic`. Własności `additionalProperties` kontekstu nie wyłączają sprawdzenia.
- **Dziennik:** każda zmiana poziomu jest zapisywana na poziomie WARN (kategoria, poziom przed i po, użytkownik).
- **OpenAPI:** klucze `ILoggerLevelsExtRest.*` dopisane w `openapi-docs_pl.properties` i `openapi-docs_en.properties` (16 kluczy). **Brakuje de, es, fr, ko** (translator Gemini).
- **POM:** `logback-classic` w `mercury-ws-app` jako `provided` (adapter); `logback.version` = 1.2.10 (jedyna 1.2.x z jarami w lokalnym repozytorium; Nexus odrzuca pobranie 1.2.11 i 1.2.13 przez błąd certyfikatu PKIX). Docelowo 1.2.13 lub nowsza 1.2.x.
- **Testy:** `LoggerLevelServiceTest` (16, atrapa backendu: walidacja, limit, obcięcie) i `LoggerBackendsTest` (10, adaptery na prawdziwych bibliotekach: Logback na własnym kontekście, log4j 1.x, wybór backendu). Wynik: 26 z 26. Test wykrył, że `slf4j-reload4j` używa `Reload4jLoggerFactory`, a nie `Log4jLoggerFactory`.

**Nie zrobiono i nie sprawdzono:** uruchomienia usługi na działającym serwerze (wywołanie REST, panel w przeglądarce, przepływ `/rest/token` z danymi klienta OAuth), tłumaczeń OpenAPI de/es/fr/ko, dokumentacji w `docusaurus-hgdb`, `openapi-doc-report.txt`.

## Aktualizacja po decyzjach autora (2026-10-27)

- **Rola administratora: `mrc_sysadmin`** (zakres tokenu OAuth). Wszystkie operacje (odczyt i zmiana) wymagają tej roli; zastąpiła ona sprawdzanie `isAllRO()`/`isAllRW()`.
  Użytkownika i role serwer ustala z tokenu OAuth (`RestServicesHelper.createContextBasedOnOAuth`, role = zakresy tokenu) albo z sesji (`createContextBasedOnSession`), a **nie** z pola `context` żądania, bo je wypełnia klient.
  Pole `context` jest opcjonalne; panel go nie wysyła. `oauthFactoryName` w `CaseTypeOpenApiController` jest teraz `public static`.
  Sprawdzenie roli: `LoggerLevelsExtRest.isSysAdmin(Context)`, test `LoggerLevelsExtRestTest` (4).
- **Logback:** autor pobrał `logback-classic` 1.2.13 i poprawił POM (`logback.version` = 1.2.13).
- **OpenAPI:** klucze `ILoggerLevelsExtRest.*` (16) są teraz we wszystkich sześciu plikach `openapi-docs_*`. Tłumaczenia de, es, fr i ko wykonał translator Gemini (`localizer.py translate`, `validate`: 16 kluczy, 0 błędów, 0 ostrzeżeń na język);
  stałe (`mrc_sysadmin`, `errorCode`, `INHERIT`, lista poziomów) zachowane.
- **Dokumentacja (`docusaurus-hgdb`, `main`, en i pl, bez commitu):** nowa strona `005_Configuration/Logging_levels.mdx` (co można zrobić, ograniczenia, rola, backend, trzy operacje z przykładami JSON, panel),
  pozycje na liście w `005_Configuration/index.mdx` oraz wpis na blogu `2026-10-27-Logging-levels-at-runtime` (informacja o nowej funkcji w następnym wydaniu).
  Przy okazji pozycja „Parametry konfiguracyjne indeksu Lucene” na liście TODO oznaczona ✅ z odnośnikiem do sekcji dodanej w 190.
- **Testy:** 30 z 30 (`LoggerLevelServiceTest` 16, `LoggerBackendsTest` 10, `LoggerLevelsExtRestTest` 4), `mvn -pl mercury-ws-app -am test` z filtrem `-Dtest`.
- **Nie sprawdzono:** wywołania na działającym serwerze (REST, panel, `/rest/token` z danymi klienta OAuth), obecności operacji w specyfikacji OpenAPI i Swagger UI (zależy od `ExtRestOpenApi`, nie uruchamiano), tego, czy token zawiera zakres `mrc_sysadmin`
  na wdrożeniach (konfiguracja klientów OAuth w XML ma w przykładach `mrc-user,mrc-useradmin`, więc zakres `mrc_sysadmin` trzeba dopisać w konfiguracji klienta).
