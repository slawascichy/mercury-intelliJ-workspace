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
