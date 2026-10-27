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

## Korekta nazwy roli i generatora OpenAPI (2026-10-27)

- **Nazwa roli to `mrc-sysadmin` (z myślnikiem), nie `mrc_sysadmin`.** Autor potwierdził: zakres w definicji OAuth to `mrc-user,mrc-useradmin,mrc-sysadmin`, a w tabeli mapowania ról administrator jest przypisany do `mrc-sysadmin`.
  Wcześniej w kodzie i dokumentacji użyłem podkreślnika (po notatniku autora, który pisze „mrc_sysadmin”); zamieniono we wszystkich plikach: `LoggerLevelsExtRest.ROLE_SYSADMIN`, interfejs i test, 6 plików `openapi-docs_*`, panel, 4 pliki docusaurus, skrypt i instrukcję testu ręcznego.
  Test negatywny sprawdza teraz wariant z podkreślnikiem i wielkimi literami jako odrzucane.
- **Generator `openapi*.json` nadpisywał ręczną zmianę autora** w bloku `security`, bo `OpenApiSpecBuilder.REQUIRED_SCOPES` miał tylko `mrc-user` i `mrc-useradmin` (schemat `securitySchemes` już zawierał `mrc-sysadmin`).
  Poprawka: `REQUIRED_SCOPES = ("mrc-user", "mrc-useradmin", "mrc-sysadmin")`. Po regeneracji wszystkie siedem plików `openapi*.json` ma blok `security` z trzema zakresami i nie różni się od HEAD.
- Build z regeneracją i testami: 47 z 47 (`LoggerLevelServiceTest` 16, `LoggerBackendsTest` 10, `LoggerLevelsExtRestTest` 4, `OpenApiResourcesTest` 17).
- Wynik budowy zostawia w katalogu roboczym zmiany końców linii w trzech plikach `mercury-server/IBPM/mercury/config/ehcache-*-ext-3.5.xsd` (w indeksie LF, po buildzie CRLF; po ignorowaniu końców linii bez różnic). Nie są częścią zadania; do cofnięcia przed commitem (`git checkout -- mercury-server/IBPM`).

## Panel przez logowanie formularzem i wyniki pierwszego testu (2026-10-27)

**Wyniki testu autora:** (1) logowanie w panelu przez `/rest/token` nie działało, bo `scope` jest parametrem wymaganym (`@RequestParam(value = "scope", required = true)`), a panel i skrypt go nie wysyłały; token ze Swagger UI działał; wyszukiwanie kończyło się błędem;
(2) wywołanie `search` z tokenem ze Swagger UI zwróciło `invalid_scope`; (3) uwaga projektowa: panel ma być dostępny po zalogowaniu formularzem, jak `swagger-ui/types.html`.

**`invalid_scope` (przyczyna z kodu, bez reprodukcji):** zgłasza je `OAuthFilter`, gdy żaden zakres tokenu nie występuje w zakresach skonfigurowanych dla ścieżki (`MercurySecurityOAuthItem.scopeSet`, wzorzec `/rest/service/**`).
Token jest wydawany wg zakresów **klienta** (`OAuthService.scopes`), więc możliwy jest rozjazd: token z samym `mrc-sysadmin`, a zakresy ścieżki bez `mrc-sysadmin`. Do ustalenia z autorem: zakresy zaznaczone w „Authorize” i zakresy wpisu dla `/rest/service/**`. Diagnostyka: nagłówki `X-OAuth-Scopes`/`X-Accepted-OAuth-Scopes` odpowiedzi `/rest/token` i `DEBUG` dla `pro.ibpm.mercury.oauth.OAuthFilter`.

**Zmiana architektury (decyzja autora):**
- `web.xml`: nowe `security-constraint` dla `/static/admin/*` i `/admin/loggers/*` z rolą `mrc-sysadmin` (FORM login jak dla `types.html`) i `<security-role>mrc-sysadmin</security-role>`. Zmiana tylko w `web.xml` (nie w `web-INEA.xml`, `web-REST-*.xml`).
- Nowy `LoggerLevelsPanelController` (`/admin/loggers/{getLevel|setLevel|search}`): uwierzytelnienie sesją (`createContextBasedOnSession`, role z `GenericPrincipal` realmu), dodatkowo sprawdzenie roli w kontrolerze. Ścieżka jest poza wzorcem `/rest/service/**`, więc `OAuthFilter` jej nie dotyczy.
- `LoggerLevelsExtRest` (token OAuth, `/rest/service/...`) zostaje dla klientów API. Wspólna logika w `LoggerLevelsOperations` (koperty JSON, dziennik zmian).
- `static/admin/loggers.html` bez logowania i tokenu: woła `../../admin/loggers/*` z ciasteczkiem sesji; wygasła sesja daje komunikat „Sesja wygasła albo brak uprawnień”.
- Testy: `LoggerLevelsOperationsTest` (5), atrapa `MemoryLoggerBackend` wspólna z `LoggerLevelServiceTest`; razem 53 z 53 (z `OpenApiResourcesTest`).
- Dokumentacja docusaurus (en i pl, strona i blog) i `test-manualny.md`/`.sh` zaktualizowane (panel przez formularz, parametr `scope` w żądaniu tokenu, `SCOPE` w skrypcie); w docusaurus poprawiono też nazwę roli na `mrc-sysadmin`.

**Wycofany wniosek o luce (2026-10-27):** wcześniej uznałem, że token z zakresem `mrc-sysadmin` może dostać każdy użytkownik z poprawnymi danymi klienta. To był błąd: przeczytałem tylko publiczną wersję `OAuthService.generateToken` (z `TODO` dotyczącym zakresu `${username}`),
a prywatna wersja `generateToken(..., TomcatMercuryPrincipal p, ...)` sprawdza, że **każdy** żądany zakres jest wśród ról użytkownika z realmu (`p.getRoles()`, tabela `MRC_LDAP_INT_ROLES_MAP`), i inaczej rzuca `OAuthInvalidGrant`.
Zakres tokenu jest więc związany z rolami użytkownika w chwili wydania tokenu, a rola `mrc-sysadmin` w tokenie jest wiarygodna. Zostaje drobne zastrzeżenie: role są zapisane w tokenie przy jego wydaniu, więc odebranie roli użytkownikowi nie unieważnia już wydanego tokenu do jego wygaśnięcia.
Test 8 skryptu `test-manualny.sh` sprawdza to na działającym serwerze (oczekiwany wynik: serwer nie wydaje zwykłemu użytkownikowi tokenu z `mrc-sysadmin`).

**Swagger UI i zakresy tokenu (2026-10-27):** test w Swagger UI dał `invalid_scope`. Znaleziono dwie przyczyny.
- **Separator zakresów.** RFC 6749 (3.3) rozdziela zakresy spacją, a `mercury-gui-core` dzielił je tylko po przecinku (5 miejsc: `OAuthService` x3, `OAuthFilter`, `MercurySecurityOAuthItem`, `RestServicesHelper`). Swagger UI wysyła `scope=mrc-user mrc-sysadmin`, więc serwer widział jeden nieznany zakres. Dodano `org.mercury.oauth.OAuthScopes.split` (separator `[,\s]+`, puste elementy pomijane) i użyto go w tych miejscach. Test `OAuthScopesTest` (6). Format `scope` w odpowiedzi tokenu bez zmian (zwracany tak, jak podał klient). Sprawdzone na serwerze: spacja, przecinek i przecinek ze spacją dają token i HTTP 200 usługi.
- **Konfiguracja OAuth z pliku, nie z bazy.** `mercury-ws-app` ma `oauthConfigId=mercury-db:1`, czyli plik `mercury/classes/mercury-ws-app/mercury-security-config-db-1.0.0.xml`, a nie tabelę `MRC_LDAP_OAUTH_CONFIG`. Plik dopuszczał dla `/rest/service/**` tylko `mrc-user,mrc-useradmin`, więc token z samym `mrc-sysadmin` dostawał `invalid_scope` (filtr wymaga jednego zakresu wspólnego z wpisem). Dopisano `mrc-sysadmin` w szablonie `mercury-server/src/main/config/scichy/.../mercury-security-config-db-1.0.0.xml`. Lokalny plik w `apache-tomcat/mercury/classes` (nieśledzony) trzeba poprawić ręcznie.
- **Do wydania:** `mercury-gui-core` trafia na serwer jako osobny jar w `mercury/lib` (nie w WAR), więc razem z WAR-em trzeba wymienić ten jar. Wydanie po zakończeniu zadania 58 i podzadania 214.
- **Poza zakresem tego zadania (do rozważenia):** zakres `mrc-sysadmin` w szablonach `mercury-docker/mercury-3.0/docker-init-config/classes/mercury-ws-app/*` (zadanie 211), w skrypcie `mercury-gui-core/db/MRC_LDAP_CREATE_SCHEMA_postgreSQL.sql` (dane początkowe: wpisy 001/002 mają `mrc-user,mrc-useradmin`, a rola `mrc-sysadmin` nie jest przypisana użytkownikowi `admin`) oraz w dokumentacji docusaurus (wzmianka, że zakres trzeba dopisać w konfiguracji OAuth).
