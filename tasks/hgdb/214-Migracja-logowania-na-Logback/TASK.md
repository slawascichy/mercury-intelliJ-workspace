# [214] Migracja logowania z log4j na Logback

https://github.com/slawascichy/hgdb/issues/214

Zadanie powstało przy 058 (dynamiczne poziomy logowania) po decyzji autora z 2026-10-27: **wariant A, Logback 1.2.x (Java 8)**.

## Cel

Pozbyć się log4j (1.x i 2.x) z aplikacji Mercury i jej bibliotek, a razem z nim podatności zgłaszanych przez skanery zależności. Backend logowania ma być jeden: Logback za SLF4J.
Zakres obejmuje kod i konfigurację w repozytoriach `mercury-lib`, `mercury`, `hgdb-client-open`, `mercury-client`, `mercury-cmd` i `mercury-docker`.

## Stan wyjściowy (fakty z plików; niczego nie uruchamiano)

- **Runtime dev-serwera** (`mercury/mercury-server/apache-tomcat/mercury/lib`, jary z 2024-11-05, katalog utrzymuje autor ręcznie obok czystego Tomcata): `log4j-1.2.14.jar`, `slf4j-log4j12-1.7.25.jar`,
  `slf4j-api-1.7.36.jar`, `commons-logging-1.2.jar`, `spring-jcl-5.3.20.jar`. `apache-tomcat/lib` ma tylko `log4j.properties`.
- **POM-y:** `mercury` ma `slf4j-reload4j` 1.7.36 i `log4j-core` 2.17.2 (oba `provided`); `mercury-lib`, `hgdb-client-open`, `mercury-client`, `mercury-cmd` mają `slf4j-log4j12` i log4j 1.2.14/1.2.17 (wszystkie `provided`).
  Rozjazd: POM-y `mercury` wskazują reload4j, a na serwerze działa log4j 1.2.14.
- **Importy `org.apache.log4j.*`:** 20 plików (`mercury` 7, `mercury-lib` 6, `hgdb-client-open` 1, `mercury-cmd` 1, `mercury-client` 5), w tym klasy `LoggerConfigurator` w `mercury-cmd` i `mercury-client-cmd`, `SequenceIntervalGenerator`,
  `JndiFactory`, `EmbeddedKeyUtils` (w `main`) oraz klasy testowe (`TstProperties`, `PropertiesLoader`, `TestPropertiesLoader`, `*Integration`). Importów API log4j 2: 0.
- **Konfiguracja:** około 30 plików `log4j.properties` (głównie `src/test/resources`; w `main`: `mercury-server/src/main/config/{jenkins,scichy}/…`, `mercury-client-cmd/src/main/conf`, `mercury-cmd/…/src/main/config`),
  oraz skrypty z `-Dlog4j.configuration=…`: `setenv.sh` w obrazie Docker i w pakiecie instalacyjnym, `startServer.sh` serwera POI.
- **Inne serwery w drzewie `mercury-server` (poza aplikacją Mercury):** `poi-toolkit-server` (`reload4j` 1.2.19, `log4j-core` 2.17.2, `log4j-api` 2.17.1), ActiveMQ 5.16.4 (`reload4j` 1.2.19, `insight-log4j`, `activemq-log4j-appender`),
  `ehcache-clustered` (`logback-classic`/`core` 1.2.3). To produkty zewnętrzne lub osobne wdrożenia; poza zakresem, opisane jako obserwacja 100.

## Zakres prac (propozycja kolejności)

1. **Rozpoznanie.** Lista wszystkich miejsc, które w czasie wykonania szukają API log4j 1.x (biblioteki trzecie, np. przez `org.apache.log4j.Logger`), żeby dobrać mostki: `log4j-over-slf4j` (zamiast jarów log4j 1.x) i `jcl-over-slf4j` (zamiast `commons-logging`).
   Skan zależności (np. OWASP Dependency-Check) przed i po zmianie, jako miara.
2. **POM-y.** W `mercury-lib`, `hgdb-client-open`, `mercury-client`, `mercury-cmd` i `mercury` zastąpić `slf4j-log4j12`/`slf4j-reload4j` i `log4j` przez `logback-classic` 1.2.x (`provided`, zgodnie z modelem: biblioteki dostarcza serwer), usunąć `log4j-core`.
   Zmiana POM-ów `mercury-lib` oznacza wydanie biblioteki (łącznie z innymi zmianami przed fazą D).
3. **Kod.** Przepisać 20 plików na SLF4J (`org.slf4j.Logger`) albo na API Logbacka tam, gdzie konfiguruje się logowanie programowo (`LoggerConfigurator` używa `PropertyConfigurator`; zamiennik to `JoranConfigurator`).
4. **Konfiguracja.** Zamienić `log4j.properties` na `logback.xml` (appendery `RollingFileAppender`/`TimeBasedRollingPolicy` odpowiadają `DailyRollingFileAppender`, te same nazwy kategorii i poziomy).
   Skrypty startowe: `-Dlog4j.configuration=…` na `-Dlogback.configurationFile=…`, usunąć `-Dlog4j.debug=true`.
5. **Serwer.** Zaktualizować `mercury/lib` (autor): usunąć `log4j-1.2.14.jar` i `slf4j-log4j12-1.7.25.jar`, dodać `logback-classic`/`logback-core` 1.2.x, `log4j-over-slf4j` 1.7.36, `jcl-over-slf4j`, `slf4j-api` 1.7.36.
6. **Pakiet i obrazy.** Zmiany w `mercury-cmd` (pakiet instalacyjny, `LoggerConfigurator`) i `mercury-docker` (obraz, `docker-init-config`). Wejdą do zadania wydania (faza D).
7. **Test dymny.** Start serwera jednowęzłowego i wielowęzłowego, zapis logów do plików, rotacja, zmiana poziomu przez usługę z 058.

## Zależności i uwagi

- **058:** usługa poziomów logowania ma adapter dla Logbacka (`LoggerContext`) i adapter dla log4j 1.x (`org.apache.log4j.LogManager`, działa też z reload4j). Dzięki temu 058 nie czeka na tę migrację, a po niej adapter log4j można usunąć.
- **Java 17 (zadanie 191):** gałąź Logback 1.2.x jest ostatnią dla Javy 8; po migracji do Javy 17 można przejść na nowszą linię (1.4/1.5) osobnym krokiem.
- **Ryzyka:** biblioteki trzecie używające API log4j 1.x wprost (mostek `log4j-over-slf4j` obsługuje `Logger`, ale nie wszystkie klasy konfiguracyjne i appendery); klienci, którzy mają własne `log4j.properties` w swoich wdrożeniach (zmiana kontraktu konfiguracji, wymaga opisu w dokumentacji i w instrukcji aktualizacji);
  kolejność jarów w `mercury/lib` (dwa bindingi SLF4J jednocześnie dają ostrzeżenie i losowy wybór).

## Definicja Gotowości (propozycja)

- W aplikacji Mercury i bibliotekach nie ma jarów ani zależności log4j 1.x i 2.x (poza mostkiem `log4j-over-slf4j`, który nie jest log4j).
- Skan zależności na WAR i pakiecie nie zgłasza podatności log4j.
- Logowanie działa jak dotąd (pliki, rotacja, poziomy) na serwerze jedno- i wielowęzłowym oraz w obrazie Docker.
- Instrukcja aktualizacji opisuje zamianę `log4j.properties` na `logback.xml` dla klientów z własną konfiguracją.

## Organizacja (decyzja autora 2026-10-27)

Zadanie 214 jest **podzadaniem zadania 58**: realizujemy je na tej samej gałęzi `hgdb-058` (bez zakładania `hgdb-214`) w repozytoriach, które dotyka (`mercury`, a dla zmian w `mercury-lib`, `hgdb-client-open`, `mercury-client`, `mercury-cmd`, `mercury-docker` osobne gałęzie o nazwie `hgdb-058` w każdym z nich).
Kolejność: najpierw ręczny test 058 (`058-…/test-manualny.md`), potem migracja.

## Rozpoznanie (krok 1, 2026-10-27; odczyt jarów w `mercury/lib`, niczego nie uruchamiano)

Skan bajtkodu 226 jarów w `mercury-server/apache-tomcat/mercury/lib` pod kątem odwołań do `org/apache/log4j/` i `org/apache/commons/logging/` (WAR `mercury-ws-app` ma w `WEB-INF/lib` tylko 2 jary i żadnego z logowania).

**Odwołania do API log4j 1.x w bajtkodzie (poza samym `log4j-1.2.14.jar`):**

| Jar | Klasa | Czego używa | Wniosek |
|---|---|---|---|
| `cxf-core-3.0.12` | `org.apache.cxf.common.logging.Log4jLogger` (+ `$HandlerWrapper`) | `Logger`, `Level`, `Priority`, `Appender`, `AppenderSkeleton`, `spi.LoggingEvent`, `spi.ThrowableInformation`, `LogManager` | CXF wybiera logger przez `META-INF/cxf/org.apache.cxf.Logger`; jar ma też `Slf4jLogger`. Ustawić tam `org.apache.cxf.common.logging.Slf4jLogger`, żeby nie zależeć od mostka. Czy `log4j-over-slf4j` ma `ThrowableInformation` i `AppenderSkeleton` – przypuszczenie, nie sprawdzone |
| `jboss-logging-3.4.3.Final` | `Log4jLoggerProvider`, `Log4jLogger` | `Logger`, `Level`, `Priority`, `NDC`, `MDC` | wybiera dostawcę po obecności klas; ustawić `-Dorg.jboss.logging.provider=slf4j` albo sprawdzić, że z mostkiem działa poprawnie |
| `sccommon-ldap-1.0.8.4.20241101` | `ProviderOptions`, `SecurityPassword` | `Logger` (+ `lf`, przypuszczalnie część nazwy, nie klasa) | biblioteka autora, zmiana wymaga nowego wydania |
| `sccommon-utils-1.0.8.4.20241101` | `ScObjectFactoryBean`, `SimpleSQLTypeHelper` | `Logger` | biblioteka autora, nowe wydanie |
| `mercury-core-server` | `org.scam.shared.id.SequenceIntervalGenerator` | `Logger` | nasz kod (`mercury-lib`) |
| `mercury-core` | `org.mercury.jndi.JndiFactory` | `Logger` | nasz kod (`mercury-lib`) |
| `poi-toolkit-4.0.3` | `org.iron.poi.excel.server.ExcelServerApp` | `config.PropertyPrinter` | biblioteka autora (`D:\workspace\git\poi-toolkit`); ta klasa nie ma odpowiednika w mostku |

Wszędzie poza CXF i `poi-toolkit` użyto tylko `org.apache.log4j.Logger`, które mostek `log4j-over-slf4j` obsługuje.

**Użycie `commons-logging`:** 83 klasy w `spring-*` 5.3.20 i inne jary (`commons-httpclient` 3.1, `commons-configuration` 1.10, `commons-beanutils`, `commons-discovery`, `httpclient` 4.5.13, `xmlgraphics-commons`, `json-lib`) odwołują się do `org.apache.commons.logging`. Na serwerze są jednocześnie `commons-logging-1.2.jar` i `spring-jcl-5.3.20.jar` (dwie implementacje tego samego pakietu). Po migracji zostaje `jcl-over-slf4j` zamiast `commons-logging`; `spring-jcl` Springa sam przekazuje wywołania do SLF4J, więc nie koliduje, ale warto go zostawić tylko jeden raz na classpath.

**Wnioski dla planu:**
- Kod `mercury`/`mercury-lib` ma tylko 20 plików z importem log4j (jak w „Stan wyjściowy”); w czasie wykonania na serwerze wprost używają go 2 klasy naszego kodu.
- Zależności poza workspace: `sccommon-ldap`, `sccommon-utils`, `poi-toolkit` (biblioteki autora). Bez ich nowych wydań i tak zadziała `log4j-over-slf4j` (poza `PropertyPrinter` w `ExcelServerApp`, osobny serwer POI), ale skaner zależności nie przestanie widzieć odwołań w ich bajtkodzie dopiero po przepisaniu.
- Dla CXF i `jboss-logging` wystarczy konfiguracja (wybór dostawcy SLF4J), bez zmiany jarów.

## Raport zależności: biblioteki autora (2026-10-27; odczyt źródeł `D:\workspace\git\sccommon` i `poi-toolkit`)

Biblioteki autora, które trafiają do `mercury/lib`: `sccommon-{cache,http-client,ldap,mail,utils}` 1.0.8.4.20241101 (w `mercury/pom.xml` `sccommon.version`; `mercury-lib` i `hgdb-client-open` używają 1.0.8.4 i 1.0.8.4-jdk1.7) oraz `poi-toolkit` 4.0.3. `sccommon` jest na `master` ze zmianami niezatwierdzonymi (`pom.xml`, `.classpath` w `sccommon-cache`), `poi-toolkit` na `master` ze zmianami w certyfikatach.

**Kluczowe znalezisko (blokuje migrację serwera):** `sccommon-ldap` importuje `org.apache.log4j.lf5.LogLevel` i `LogLevelFormatException` (`LdapConfig`, `LdapConfigOptions`, `ProviderOptions`). To klasy z interfejsu graficznego LF5 z log4j 1.x. Mostek `log4j-over-slf4j` ich **nie zawiera**. Po usunięciu `log4j-1.2.14.jar` z serwera `ProviderOptions` zgłosi `NoClassDefFoundError` (ładowanie klasy konfiguracji uwierzytelniania LDAP). Wartość służy tylko jako enum opcji `logLevel`; `getLogLevel()` nie ma w drzewie żadnego wywołania poza definicjami (przeszukane `mercury`, `mercury-lib`, `hgdb-client-open`, `mercury-client`, `mercury-cmd`, `poi-toolkit`, `sccommon`).

| Biblioteka | Plik | Użycie log4j 1.x | Zmiana |
|---|---|---|---|
| `sccommon-ldap` | `ProviderOptions`, `LdapConfig`, `LdapConfigOptions` | `lf5.LogLevel`, `LogLevelFormatException` | własny enum poziomów (albo `String`) zamiast klas LF5; **konieczne** |
| `sccommon-ldap` | `SecurityPassword` | `Logger.getLogger` | SLF4J (mostek wystarczy, ale zmieniamy) |
| `sccommon-utils` | `MimeTypeUtil`, `ScObjectFactoryBean`, `SimpleSQLTypeHelper` | `Logger.getLogger` | SLF4J |
| `sccommon-*` (testy) | 8 klas (`TstProperties` x3, `MigrationTest`, `Basic`, `ClearMockInDb`, `DmlMethods`, `JndiFactory`, `MimeTypesUtilTest`) i 5 `log4j.properties` w `src/test/resources` | `Logger`, `PropertyConfigurator` | SLF4J i `logback-test.xml` |
| `sccommon` (POM) | `pom.xml` | `log4j` 1.2.17 i `slf4j-log4j12` 1.7.25 (`provided`) | `logback-classic` 1.2.x (`provided`) |
| `poi-toolkit` | `ExcelServerApp` | `org.apache.log4j.config.PropertyPrinter` w bloku `static` (wypisuje konfigurację log4j przy starcie) | usunąć blok albo zastąpić `StatusPrinter` Logbacka; bez tej zmiany serwer POI nie wystartuje na Logbacku |
| `poi-toolkit` | `pom.xml`, `src/main/conf/log4j.properties`, `startServer.sh` | `slf4j-log4j12`, `log4j-core` 2.17.2, `-Dlog4j.configuration` | Logback, `logback.xml`, `-Dlogback.configurationFile` |

`commons-logging` w źródłach `sccommon` i `poi-toolkit` nie występuje (0 plików); `sccommon-utils` wyklucza go ze `spring-core`.

**Skutek dla kolejności:** `sccommon` (nowe wydanie, np. 1.0.8.5) -> `poi-toolkit` (nowe wydanie) -> podniesienie `sccommon.version` i wersji `poi-toolkit` w `mercury`, `mercury-lib`, `hgdb-client-open` (w tym wariant `-jdk1.7`) -> migracja `mercury`.

## Postęp: biblioteki autora (2026-10-27)

Gałąź `hgdb-058` w `sccommon`, `poi-toolkit` i `ccrto-openapi` (zmiany niezatwierdzone). Decyzje autora: dostęp do wszystkich projektów; adapter log4j 1.x z zadania 58 usuwamy, bez okresu przejściowego (patrz pamięć „Upgrade wymienia cały serwer”).

- **`sccommon-ldap`:** usunięte klasy LF5 (`LogLevel`, `LogLevelFormatException`) z `ProviderOptions`, `LdapConfig`, `LdapConfigOptions`. Z `ProviderOptions` zniknęło przestarzałe pole `logLevel`, jego parsowanie opcji i getter `getLogLevel()` (bez użytkowników w całym drzewie). W `LdapConfig` zostaje przestarzałe pole `String logLevel` i stała `option_logLevel` (dane konfiguracji).
- **`sccommon-ldap`, `sccommon-utils`:** `SecurityPassword`, `MimeTypeUtil`, `ScObjectFactoryBean`, `SimpleSQLTypeHelper` na SLF4J. **Zmiana publicznego API:** `SimpleSQLTypeHelper.validateBooleanValue(String, String, Logger)` przyjmuje teraz `org.slf4j.Logger` (wywołuje ją `mercury-lib`: `org.mercury.jndi.JndiFactory`), pole `ScObjectFactoryBean.log` jest SLF4J.
- **`sccommon` (testy i POM):** 8 klas testowych bez `PropertyPrinter` i log4j; `pom.xml`: `logback-classic` 1.2.13 (`provided`) zamiast `log4j` 1.2.17 i `slf4j-log4j12`; pięć `log4j.properties` zastąpiło `logback-test.xml`; `-Dlogback.configurationFile` w `sccommon-ldap/pom.xml`. Wynik: `mvn -o test-compile` wszystkich modułów OK; w 272 klasach `sccommon-utils` i 69 `sccommon-ldap` nie ma odwołań do `org/apache/log4j`; testy jednostkowe `sccommon-utils` (5 klas, 15 testów) przechodzą, a log idzie do `target/test.log` przez Logbacka. Nie uruchamiano testów wymagających LDAP, bazy i poczty.
- **`poi-toolkit`:** usunięty blok `PropertyPrinter` z `ExcelServerApp`; `pom.xml`: `logback-classic` 1.2.13 zamiast `slf4j-log4j12` i `log4j-core`; `src/main/conf/logback.xml` zamiast `log4j.properties` (rotacja 1024 KB, 1 kopia, jak w log4j); `startServer.sh`: `-Dlogback.configurationFile`; `logback-test.xml`. `mvn -o test-compile` OK. Poza zakresem zostały: `logo/resources/log4j.properties` (kopia poza buildem).
- **`ccrto-openapi`:** `pom.xml`: `logback-classic` zamiast `log4j` i `slf4j-log4j12`, `slf4j.version` 1.5.2 -> 1.7.36 (Logback 1.2 wymaga co najmniej 1.7.25); `logback-test.xml`. `mvn -o test-compile` OK.
- **Nie zmieniano:** `sccommon-mail/src/test/resources/embedded.logging.properties` (konfiguracja OpenEJB w formacie log4j, nie jest wczytywana przez kod projektu; do sprawdzenia przy testach poczty).

**Do zrobienia przez autora:** nowe wydania `sccommon` i `poi-toolkit` (numery wersji), potem podniesienie `sccommon.version` i wersji `poi-toolkit` w `mercury`, `mercury-lib`, `hgdb-client-open` (także wariant `-jdk1.7`) i `ccrto-openapi`.

## Postęp: wydania i migracja `mercury-lib`, `mercury` (2026-10-27)

Wydania autora: `sccommon` 2.0.0.1, `ccrto-openapi` 2.0.0.1, `poi-toolkit` 4.1.0.1. Gałąź `hgdb-058` założona w `mercury-lib` i `hgdb-client-open` (zmiany niezatwierdzone).

- **`mercury-lib`:** `sccommon.version` 2.0.0.1, `poi-toolkit.version` 4.1.0.1, `slf4j.version` 1.7.36, `logback.version` 1.2.13 (usunięte `log4j.version`). Logback `provided` zamiast `log4j` i `slf4j-log4j12` w głównym POM-ie oraz w `mercury-entities` i `mercury-ws-dto-api` (wcześniej `compile`; `provided`, żeby Logback nie trafiał tranzytywnie do WAR-a). `JndiFactory` na SLF4J (pasuje do nowego `SimpleSQLTypeHelper.validateBooleanValue`), `EmbeddedKeyUtils` i `SequenceIntervalGenerator` (katalogi `seq-hibernate-3.6.10.Final` i `seq-hibernate-4.3.6.Final`) na SLF4J, `TstProperties` bez `PropertyPrinter`, siedem `log4j.properties` zastąpiło `logback-test.xml`. `mvn -o -DskipTests install` wszystkich modułów OK; w skompilowanych klasach nie ma odwołań do `org/apache/log4j`. Katalogi `seq-hibernate-*` nie wchodzą do domyślnej kompilacji (przypuszczenie: profil Hibernate); zmiana w nich jest identyczna jak w skompilowanym kodzie, ale ich nie kompilowano.
- **`mercury`:** POM-y (główny, `mercury-ws-app`, oba generatory, `mercury-gui-core`): Logback `provided` (generatory `compile`), mostki `log4j-over-slf4j` i `jcl-over-slf4j` 1.7.36 `provided`, usunięte `slf4j-reload4j`, `log4j-core`, `log4j.version` oraz wykluczenia `log4j`/`slf4j-log4j12`/`slf4j-reload4j`; `sccommon.version` 2.0.0.1, `poi-toolkit.version` 4.1.0.1. Źródła: `SequenceIntervalGenerator` (`mercury-core-server`) na SLF4J; `PropertyPrinter` usunięty z siedmiu klas testowych i `TestPropertiesLoader` (`mercury-mock`); **usunięty `Log4j1LoggerBackend`** wraz z jego testami i rejestracją w `LoggerBackends` (zostaje Logback; `testCurrentBackendIsSupported` oczekuje `logback`). 19 plików `log4j.properties` zastąpiły `logback.xml` (konfiguracja serwera: `tomcat/lib` i `mercury-ws-app` w `jenkins` i `scichy`, `IBPM/mercury/config` w `jenkins`) i `logback-test.xml` (testy). Usunięty z `jenkins/.../mercuryWebContextSpring.xml` bean `log4jInitialization` (`Log4jConfigurer` nie istnieje w Springu 5). Generatory źródeł dostały `src/main/config/logback-generator.xml` (INFO) wskazany przez `logback.configurationFile` w `exec-maven-plugin`, bo Logback bez konfiguracji loguje na DEBUG (bez tego generator REST zalewał konsolę komunikatami swagger-core).
- **`hgdb-client-open`:** `TestPropertiesLoader` bez `PropertyPrinter`, dwa `log4j.properties` -> `logback-test.xml`, POM: Logback `provided` zamiast `slf4j-log4j12`, `slf4j.version` 1.7.36. Aktywny wariant zmieniony na `sccommon` 2.0.0.1 (decyzja autora): ehcache 3.6.1, `sccommon-cache` z grupy `pl.slawas.sccommon`; blok `1.0.8.4-jdk1.7` (SecurityProvider, ehcache 2.10.1) zostaje w POM-ie jako komentarz. `mvn -o test-compile` wszystkich modułów OK.
- **Do zrobienia:** `mercury-client` (5 plików Java, `LoggerConfigurator`), `mercury-cmd` (`LoggerConfigurator`, `setenv.sh`, `activemq.xml`, `catalina.properties`), `mercury-docker`; konfiguracja CXF (`org.apache.cxf.Logger`) i jboss-logging; dokumentacja; test dymny na serwerze.

## Postęp: `mercury-client`, `mercury-cmd`, `mercury-docker`, dokumentacja (2026-10-27)

Gałąź `hgdb-058` w `mercury-client`, `mercury-cmd` i `mercury-docker` (zmiany niezatwierdzone). **Nie budowano**: `mercury-client` wymaga bibliotek IBM, a `mercury-cmd` buduje się na wydanych wersjach serwera i klienta (patrz „Do zrobienia” niżej).

- **`mercury-client`:** `LoggerConfigurator` (`mercury-client-cmd`) konfiguruje Logbacka przez `JoranConfigurator` z pliku `../conf/logback.xml` (stała `Client.LOG_CONFIG_FILE` zamiast `LOG_PROPERTIES_FILE`); `PropertyPrinter` usunięty z `TestPropertiesLoader`; trzy testy integracyjne na SLF4J; usunięte beany `log4jInitialization` (`Log4jConfigurer`) z `spring-test.xml` w `mercury-bpm` i `mercury-data`; pięć `log4j.properties` -> `logback.xml`/`logback-test.xml`; POM: Logback `provided` zamiast `slf4j-log4j12`, `slf4j.version` 1.7.36. Zostawione: `conf-inea/mercury-client/log4j.properties` (konfiguracja konkretnego wdrożenia), `mercury-client-cmd/releases/*` (archiwalne wydania) i artefakt `scteamworks-log4j` na liście `artifactIdsMaps` (do sprawdzenia, co to za biblioteka).
- **`mercury-cmd`:** `LoggerConfigurator` (`mercury-srv-cmd`) na `JoranConfigurator`, `CommandLineHelper.LOG_CONFIG_FILE` = `../config/logback.xml`; POM: Logback zamiast `slf4j-log4j12`, usunięte `log4j.version`; sześć `log4j.properties` -> `logback.xml`/`logback-test.xml` (pakiet instalacyjny: `src/main/config`, `system-config-sample/linux/config` i `apache-tomcat/lib`); `setenv.sh` (przykład): `-Dlogback.configurationFile` i `-Dorg.jboss.logging.provider=slf4j` zamiast `-Dlog4j.configuration` i `-Dlog4j.debug`; `poi-toolkit-server/bin/startServer.sh`: `APP_LOGBACK_CONFIG_FILE`. Nie zmieniano: `catalina.properties` (lista jarów pomijanych przy skanowaniu przez Tomcata) i `activemq.xml` (`Log4jLogQuery` to logowanie ActiveMQ, osobnego produktu).
- **`mercury-docker`:** trzy `log4j.properties` -> `logback.xml` (`mercury-3.0/docker-init-config/apache-tomcat/lib`, `.../config`, `poi-server/conf`); `setenv.sh` jak wyżej; `poi-server/Dockerfile` kopiuje `logback.xml`; `poi-server/bin/startServer.sh`. Nie zmieniano `activemq/conf/*_activemq.xml` (jak wyżej).
- **Decyzja: bez `jcl-over-slf4j`.** `spring-jcl` (Spring 5.3.20, jest w `mercury/lib`) implementuje API `commons-logging` i kieruje je do SLF4J; `jcl-over-slf4j` zdublowałby te klasy. Usunięty z POM-ów `mercury`; z serwera usuwamy `commons-logging-1.2.jar`. Do serwera dochodzą `logback-classic` i `logback-core` 1.2.13 oraz `log4j-over-slf4j` 1.7.36; znikają `log4j-1.2.14.jar` i `slf4j-log4j12-1.7.25.jar`.
- **CXF:** nie ma w `mercury` pliku `META-INF/cxf/org.apache.cxf.Logger` ani właściwości `org.apache.cxf.Logger`, więc CXF loguje przez JUL; `Log4jLogger` nie jest ładowany. Nie dodawano konfiguracji (przekierowanie logów CXF do SLF4J byłoby nową funkcją, nie koniecznością migracji).
- **jboss-logging:** `-Dorg.jboss.logging.provider=slf4j` w `setenv.sh` (`mercury-docker`, `mercury-cmd`); bez tego Hibernate wybrałby provider log4j przez mostek (przypuszczenie na podstawie kolejności wyboru providera w jboss-logging 3.4).
- **Dokumentacja:** `docusaurus` (`Logging_levels` en/pl: Logback zamiast Logback + log4j 1.x), `docs/architektura.md`, `docs/moduly/{hgdb-client-open,mercury-client,mercury-cmd}.md`. `sclogger.properties` z `logger.appender=LOG4J` (testy `mercury`) to nieużywana konfiguracja (żaden kod jej nie czyta; przypuszczenie na podstawie przeszukania Javy) – zostawiona.

**Do zrobienia:**
1. Test dymny na serwerze dev (wymiana jarów w `mercury/lib`: `sccommon-*` 2.0.0.1, `poi-toolkit` 4.1.0.1, jary `mercury-*`, logowanie wg listy wyżej; `logback.xml`; nowy WAR i `mercury-gui-core`): start, poziomy przez usługę z zadania 58, rotacja.
2. Generator REST: swagger-core nadal loguje na DEBUG mimo `logback-generator.xml` (generator API 2.0 używa go poprawnie) i generacja trwa ~4,5 min.
3. Po wydaniach `mercury-lib`, `mercury`, `hgdb-client-open`: zbudować `mercury-cmd` (zależy od wydanych wersji) i sprawdzić `LoggerConfigurator`.
4. Oznaczyć ✅ obserwacje 98–100 w `docs/obserwacje.md` po teście dymnym i wydaniu; instrukcja aktualizacji dla klientów z własnym `log4j.properties`.

**Weryfikacja `mercury-client` i `mercury-cmd` (2026-10-27):** biblioteki IBM są w `D:\workspace\lib` (`local-lib-path` z `settings.xml`), ale `mvn -o test-compile` w `mercury-client` nie przechodzi już na `master` (przed moimi zmianami): w POM-ach nie ma definicji właściwości `hgdb-client.version`, `httpclient.version` i `servlet-api.version`. Zamiast pełnego buildu sprawdzono samodzielnie oba `LoggerConfigurator`y: kompilują się z Logbackiem 1.2.13, a wersja klienta załadowała `mercury-client-cmd/src/main/conf/logback.xml` (komunikat „Logging initialized.” i wpis testowy w formacie z pliku). W `mercury-srv-cmd` kompilacja `LoggerConfigurator` nie ma błędów, ale nie dało się skompilować jego zależności `CommandLineHelper` (brakuje jarów serwera).

## Zgodność z SecurityProviderem w IBM BPM (2026-10-27)

`mercury-client` (przez `hgdb-client-open`) i SecurityProvider (`D:\workspace\git\bpm-security-provider`) działają w jednym środowisku IBM BPM, w którym współdzielą katalog bibliotek i classloader. Poniższe ustalenia pochodzą z POM-ów, kodu i katalogów `D:\workspace\lib\TeamWorks-*`.

**1. Logowanie w BPM dostarcza BPM.**
- Katalogi `TeamWorks-*` zawierają tylko biblioteki IBM (biblioteki autora zostały z nich usunięte, stan z 2026-10-27). Logowanie: `TeamWorks-8.6.3` ma `log4j.jar`, `slf4j-api-1.7.25` i `slf4j-log4j12-1.7.25`; `TeamWorks-8.6.8` ma `slf4j-api` (w tym 2.0.1) i `slf4j-jdk14` bez `log4j.jar`; `TeamWorks-8.6.9` ma `log4j.jar`, `log4j-core.jar`, `slf4j-api` (w tym 2.0.1) i `slf4j-jdk14`.
- Skutek: biblioteki po stronie BPM (`mercury-client`, SecurityProvider, `tw4j`, `sccommon-*`) mogą używać tylko API SLF4J i nie mogą wnosić Logbacka ani `log4j-over-slf4j` (ten drugi zderzyłby się z `log4j.jar` BPM-a). Logback i mostek są tylko dla serwera Mercury (Tomcat). Listy instalowanych artefaktów (`artifactIdsMaps` w `mercury-client-cmd`, `includeArtifactIds` w `bpm-security-installer`) nie mogą ich zawierać; obecnie nie zawierają.
- Wyjątek to `LoggerConfigurator` w `mercury-client-cmd` (Joran/Logback): to narzędzie linii poleceń uruchamiane poza BPM.

**2. Wspólne biblioteki w katalogu BPM.** Oba produkty instalują do katalogu BPM te same artefakty pod tymi samymi nazwami (z prefiksem `0_`): `sccommon-utils`, `sccommon-cache`, `ehcache`. Instalator usuwa wcześniej pliki o tym prefiksie, więc ostatnia instalacja wygrywa. W BPM może być tylko jedna wersja tych klas.

**3. Niezgodność API `sccommon-cache`.**

| | SecurityProvider (stan obecny) | `hgdb-client-open` po zmianie |
|---|---|---|
| `sccommon-utils` | 1.0.8.4-jdk1.7 | 2.0.0.1 |
| `sccommon-cache` | `pl.slawas:sccommon-cache` 0.0.3-20180724 | `pl.slawas.sccommon:sccommon-cache` 2.0.0.1 |
| ehcache | `net.sf.ehcache:ehcache` 2.10.1 | `org.ehcache:ehcache` 3.6.1 (plus `ehcache-clustered`, `hibernate-core`, `hibernate-ehcache` jako zależności `sccommon-cache` 2.0.0.1) |
| interfejsy cache | `_IObjectCache`, `_IObjectCacheProvider`, `_IObjectCacheStatistics`, `...cache.config.CacheConstants` | `IObjectCache`, `IObjectCacheProvider`, `IObjectCacheStatistics`, `...cache.CacheConstants` |
| czyszczenie | `getEhCache().getCacheManager().clearAll()` | `getEhCache().clear()` |

Nazwy pakietów (`pl.slawas.common.cache.*`) są te same, a API niezgodne, więc dwie wersje w jednym BPM-ie dają `NoClassDefFoundError`/`NoSuchMethodError` zależnie od kolejności ładowania. Pakiety samego ehcache różnią się (`net.sf.ehcache` i `org.ehcache`), więc nie kolidują ze sobą, ale `sccommon-cache` 2.0.0.1 wymaga wersji 3.x i `javax.cache`.

**4. Wynik próbnej kompilacji SecurityProvidera na `sccommon` 2.0.0.1 i ehcache 3.6.1** (kopia źródeł poza repozytorium, nadpisanie właściwości wersji z linii poleceń): moduł `security-provider` (Core) **nie kompiluje się**. Błędy dotyczą siedmiu klas: `ProviderOptions`, `_LdapConfigOptions`, `LdapSecurityCore`, `CacheNotAllowed`, `UserSynchronizationCache`, `UserSynchronizationCacheNotAllowed`, `IUserSynchronizationCache` (zmiana nazw interfejsów cache i pakietu `CacheConstants`); moduły zależne (`security-wsjmx-client`, `security-integrations`, `plugin-*`) nie były kompilowane. Moduły `tw4j`, `security-mq-client` i `ibm-teamworks-ext` kompilują się. `tw4j` (`pl.slawas.twl4j`) pochodzi z repozytorium SecurityProvidera, a nie z `sccommon`.

**5. Wniosek.** Przejście `hgdb-client-open` na `sccommon` 2.0.0.1 i ehcache 3.6.1 wymaga jednoczesnego przejścia SecurityProvidera, inaczej `mercury-client` i SecurityProvider nie zadziałają razem w BPM. To jest **osobne zadanie** (zmiana stosu cache w SecurityProviderze, instalatory, test w BPM); nie wchodzi w zakres 214. Do czasu jego wykonania `mercury-client` i `hgdb-client-open` w BPM nie mogą wyjść na 2.0.0.1.

**Decyzja autora (2026-10-27):** `hgdb-client-open` zostaje na `sccommon` 2.0.0.1 i ehcache 3.6.1 (blok `jdk1.7` pozostaje tylko komentarzem w POM-ie). Konsekwencja: `mercury-client` musi przejść na ten sam stos (jego `pom.xml` ma jeszcze `net.sf.ehcache` 2.10.1 i `sccommon-cache` 0.0.3-20180724), a SecurityProvider wymaga osobnego zadania (patrz wyżej).

## Zmiana planu (2026-10-27)

**Decyzja autora:** `mercury-client` zostaje w obecnej postaci, zgodny z `D:\workspace\git\mercury-v3.0.1.20210709`, i nie jest dalej rozwijany. Zmiany z `hgdb-058` w `mercury-client` (logowanie, podniesione wersje, poprawki `Long` -> `String` i `TestPropertiesLoader`) nie wchodzą do wydania. Jedyna funkcja, która musi przetrwać, to `mercury-bpm/.../dao` (patrz niżej); ma powstać w nowym projekcie `hgdb-ibm-bpm-client`.

**Co robi `mercury-bpm/.../dao` (14 klas, 1843 linie):** `MrcTaskDAO`, `MrcBpdInstanceDAO` i `MrcTaskNarrativeDAO` nadpisują DAO IBM BPM (`TaskDAO` itd.; podmiana w `registry.persistence.xml` dla BPM 8.5.x). Po zapisie zadania, instancji procesu albo narracji w BPM `BpmTaskBufferDAO` (i dwie podobne) tworzą rekordy buforowe (`Transformer`) i w puli wątków (20–200 wątków, opóźnienie 2 s na łączenie zadania z narracją) wstawiają je `INSERT`-em JDBC (`AbstractDAO`, źródło danych z JNDI) do tabel bufora w bazie Mercury (encje `MBpmTaskBuffer` itd. w `mercury-lib`). Przy błędzie robi zrzut danych do pliku (`dumpErrorLog`). Serwer Mercury przetwarza bufor po swojej stronie.

**Do rozstrzygnięcia w nowym zadaniu (kanał BPM -> Mercury):**

| Wariant | Uwagi |
|---|---|
| A. JDBC do tabel bufora (stan obecny) | BPM musi mieć dostęp do bazy Mercury i znać jej schemat; sprzężenie z bazą |
| B. REST z OAuth (narzędzie Swagger w BPM) | REST serwera ma tylko OAuth 2.0 (`/rest/token`, grant `password` i `refresh_token`); Basic jest tylko w `RemoteBasicAuthFilter` dla RMI i CMIS. Trzeba sprawdzić, czy narzędzie w BPM obsłuży token i odświeżanie; jeśli nie, dodać Basic do REST. Wywołanie synchroniczne wiąże zapis w BPM z dostępnością Mercury, więc i tak potrzebny jest bufor z ponawianiem |
| C. DAO -> JMS/MQ/Kafka -> odbiorca w Mercury | oddziela dostępność, daje kolejkowanie i ponawianie; po stronie Mercury nowy komponent (`org.mercury`) zapisujący bufor. JMS jest natywny w WebSphere; precedens: `security-mq-client` w SecurityProviderze (ActiveMQ i Spring JMS). Klient Kafki w BPM ma wymagania co do wersji Javy i konfliktów bibliotek (BPM 8.6.8+ ma własne `slf4j-api` 2.0.1) |

**Zakres 214 po zmianie:** `mercury-lib`, `mercury`, `hgdb-client-open`, `mercury-cmd`, `mercury-docker`. Bez `mercury-client`. SecurityProvider: osobne zadanie (stos cache).

**`mercury-cmd` — moduły (stan 2026-10-27):**

| Moduł | Rola | Pliki Java (main/test) | Zależności |
|---|---|---|---|
| `mercury-benchmark` | pomiary wydajności klienta | 1 / 6 | `hgdb-ws-client-cxf`, `hgdb-multi-client`, `hgdb-client-mock`, CXF, `sccommon-*` |
| `mercury-srv-cmd` | polecenia linii komend dla serwera (`pro.ibpm.mercury.cmd.CommandLine`, `LoggerConfigurator`) | 18 / 0 | 11 artefaktów serwera (`mercury-dao`, `mercury-srv`, `mercury-lucene-indexes`, `mercury-ws-server`...), `mercury-lib`, klient, sterowniki JDBC, `activemq-client` |
| `mercury-transfer` | kopiowanie danych typu między dwiema instancjami serwera (`org.mercury.transfer.cmd.CommandLine`) | 5 / 3 | `mercury-srv-cmd`, klient (`hgdb-*`), CXF |
| `mercury-install-package` | pakiet instalacyjny (`bin`, `config`, `scripts`, `system-config-sample`, `libExt`) | 0 / 0 | składa moduły powyżej; odwołuje się do `hgdb-client-open`, ale ma jeszcze właściwości wskazujące `mercury-client` |

Zmiany zrobione w `mercury-cmd` (gałąź `hgdb-058`): Logback w POM-ie, `LoggerConfigurator` na Joran, sześć konfiguracji, skrypty `setenv.sh` i `startServer.sh`; podniesione wersje (`mercury.static.version` 3.0.4.18, `hgdb-client.version` 3.1.4.18, `sccommon` 2.0.0.1, `poi-toolkit` 4.1.0.1, `ccrto-openapi` 2.0.0.1) i **`mercury.server.project.version` 3.0.1-SNAPSHOT -> 3.0.4.9** (11 artefaktów serwera w `mercury-srv-cmd`). Do zrobienia: usunąć odwołania do `mercury-client` (właściwości `project.client.dir`, `project.local.client.repo` i repozytorium `project.local.client`), zbudować po pobraniu `hgdb-multi-client` 3.1.4.18 i sprawdzić `mercury-srv-cmd` (zależy od klas serwera, które w 3.0.4.9 mogły się zmienić), sprawdzić nazwę pakietu instalacyjnego (od `mercury.static.version`).

**`mercury-cmd` — wynik budowania (2026-10-27):** `mvn -o clean test-compile` przechodzi dla `mercury-benchmark`, `mercury-srv-cmd`, `mercury-transfer` i `mercury-install-package` (po pobraniu `hgdb-multi-client` 3.1.4.18). W skompilowanych klasach nie ma odwołań do `org/apache/log4j`. Zrobione: usunięte odwołania do `mercury-client` (`project.client.dir`, `project.local.client.repo`, repozytorium `project.local.client`); `hgdb.client.version.release` i `hgdb-client.version` = 3.1.4.18. Poprawki rozjazdu z API serwera 3.0.4.9 (zadanie 169 i `typeCodes`): `TransferThread` i `IneaTerytTest` wołają `saveList(..., Collections.<TypeCode>emptySet())` (wcześniej trzy argumenty; pusty zbiór odtwarza stare zachowanie, a `null` rzuciłby wyjątek w `ClientCaseBusiness`, która iteruje po zbiorze); `IneaGeoTest` przekazuje identyfikatory jako `String`. Do sprawdzenia przy teście transferu: czy pusty zbiór `typeCodes` wystarcza serwerowi docelowemu (przypuszczenie, nie testowano).

## Test dymny na serwerze dev (2026-10-27)

**Zmiany na serwerze** (`mercury-server/apache-tomcat`, kopie zapasowe zmienianych plików w katalogu roboczym sesji `backup-214`): usunięte `log4j-1.2.14`, `slf4j-log4j12-1.7.25`, `commons-logging-1.2`, `lib/log4j.properties` i `mercury/classes/mercury-ws-app/log4j.properties`; dodane `logback-classic` i `logback-core` 1.2.13, `log4j-over-slf4j` 1.7.36 oraz `logback.xml` w `lib` i `mercury/classes/mercury-ws-app`; `sccommon-{utils,cache,ldap,mail,http-client}` 2.0.0.1, `poi-toolkit` 4.1.0.1 i `ccrto-openapi` 2.0.0.1 zamiast starszych. Jary `mercury-*` (3.0.4.18) i WAR-y zostały wdrożone wcześniej przez skrypty wydania (w nich brak odwołań do log4j, jest `LogbackLoggerBackend`, nie ma `Log4j1LoggerBackend`).

**Wynik:**
- Start Tomcata: 272 s, bez błędów związanych ze zmianą (SEVERE dotyczą tylko natywnej biblioteki APR/AJP i połączenia `JNDIRealm` z LDAP, które są środowiskowe). Logback zainicjował się z `lib/logback.xml`; aplikacja loguje do `logs/mercury-ws-app.log`.
- Usługa poziomów (panel `/admin/loggers/*`, logowanie formularzem jako `admin`): `getLevel` i `search` zwracają `"backend":"logback"`; `setLevel` ROOT na `DEBUG` zwiększył liczbę wpisów `DEBUG` w pliku (34 -> 72 po trzech żądaniach), przywrócenie `INFO` zadziałało, w pliku jest wpis audytu `WARN` (kategoria, poziomy, użytkownik); `INHERIT` na nowej kategorii zwraca `level: null`; nazwa z niedozwolonym znakiem daje błąd walidacji.
- **Odchylenie wykryte i poprawione:** Logback ograniczył `FixedWindowRollingPolicy` do 21 kopii (`MaxIndex reduced to 21`), a log4j trzymał 100 (`MaxBackupIndex=100`). W sześciu szablonach (`mercury` jenkins i scichy: `tomcat/lib` i `mercury-ws-app`; `mercury-cmd` i `mercury-docker`: `tomcat/lib`) `maxIndex` zmieniony na 20 (nazwy `mercury-ws-app.log.N` bez zmian); retencja spada ze 100 do 20 kopii po 7024 KB. Alternatywa, jeśli potrzebna większa retencja: `SizeAndTimeBasedRollingPolicy` z `totalSizeCap`, ale zmienia nazwy plików. Poprawiony plik w działającym serwerze sprawdzony samodzielnie (Joran, bez ostrzeżeń); po zmianie nie restartowano Tomcata.
- **Nieprzetestowane:** rotacja plików (log miał 0,6 MB, limit to 7 MB), test 403 i zwykłego użytkownika (jak w zadaniu 58), wywołanie przez REST z tokenem OAuth (brak sekretu klienta w tej sesji), transfer `mercury-transfer`, `LoggerConfigurator` w `mercury-srv-cmd` na działającym pakiecie.

## Zamknięcie: generator REST, dokumentacja, obserwacje (2026-10-27)

- **Generator REST:** czysty przebieg (`mvn -o -pl mercury-ws-app-rest-generator -am compile`) nie wypisuje ani jednej linii DEBUG; konfiguracja `logback-generator.xml` działa (własne komunikaty generatora w formacie z pliku, `INFO`). Wcześniejsze DEBUG pochodziło z pierwszego przebiegu zatrzymanego przeze mnie przez `TaskStop`, który dalej pisał do tego samego pliku logu (przebiegi się mieszały); zatrzymanie zadania nie zabija procesu Mavena. Czas generacji (ok. 4 min 15 s, siedem języków po 30–40 s) nie zależy od logowania (obserwacja 106). Pliki `openapi*.json` zmieniały się po buildzie tylko w polu `info.version` (`3.0.4-SNAPSHOT`) i zostały przywrócone do zatwierdzonej wersji.
- **Dokumentacja:** nowa strona docusaurus „Logging configuration (Logback)” / „Konfiguracja logowania (Logback)” (`docs/005_Configuration/Logging_configuration.mdx` i wersja `pl`, wpis w `index.mdx`): zmiany względem log4j, lista jarów, konwersja konfiguracji, opcje JVM, limit 21 rotowanych plików, uwaga o IBM BPM. Buduje się (`npm run build`, en i pl). Wersje de/es/fr/ko tłumaczy translator Gemini (`localization-project`). Zaktualizowane też `docs/architektura.md` i `docs/moduly/*` (wcześniej) oraz `Logging_levels` (backend).
- **Obserwacje (`docs/obserwacje.md`):** ✅ przy 98 i 99, dopisek przy 100; nowe 101–106 (`mercury-client` zamrożony, stos cache SecurityProvidera, retencja logów, `sclogger.properties`, `saveList` z pustym `typeCodes`, czas generatora).
- **Zostaje otwarte:** wydania i podniesienie wersji po wydaniach (numery od autora), test 403 i zwykłego użytkownika, wywołanie REST z tokenem OAuth, rotacja plików, transfer `mercury-transfer`, `LoggerConfigurator` w `mercury-srv-cmd` na pakiecie, zadanie 215 (komunikacja IBM BPM -> HgDB) i osobne zadanie dla SecurityProvidera, obrazy Docker (zadanie 211).

**Zwykły użytkownik do testów (2026-10-27):** w bazie `mercury-ldap` serwera dev dodany użytkownik `tester` (`MRC_LDAP_INT_USERS`, hasło = SHA-1 z `tester/tester`, ważność jak u `admin`) z rolą `mrc-user` (`MRC_LDAP_INT_ROLES_MAP`). Po zalogowaniu jako `tester` panel i `/admin/loggers/*` zwracają 403 (zadanie 58, patrz tam); start Tomcata po zmianie `maxIndex` nie zgłasza już ostrzeżenia Logbacka.
