# [191] Rewizja wersji oprogramowania i migracja serwera na Javę 17

**Status (2026-10-27):** w planie po 049 (kolejność autora: 016, 049, 191). Plan: `plan-najblizszych-dzialan-2026-10-26.md`.

> Zadanie wydzielone z [133 – Swagger](../133-Swagger-implementacja/TASK.md)
> (dawne etapy 3 i 4). Swagger nie zależy od tego zadania.

## Cel zadania
Przejrzeć i uaktualnić wersje zależności we wszystkich repozytoriach Maven, a następnie przenieść
serwer (`mercury`) i narzędzia (`mercury-cmd`) na Javę 17. Biblioteki współdzielone i klienci
zostają na Javie 8.

## Podział na etapy

| Etap | Plik | Zakres | Zależy od |
|---|---|---|---|
| 1 | [etap-1-rewizja-wersji-java8.md](etap-1-rewizja-wersji-java8.md) | Porządki w zależnościach bez zmiany Javy (wszystko na 1.8) | – |
| 2 | [etap-2-migracja-serwera-java17.md](etap-2-migracja-serwera-java17.md) | `mercury` i `mercury-cmd` na Javie 17, nadal stos `javax` | Etap 1 |

Przejście na `jakarta` (Spring 6, CXF 4, Hibernate 6, Tomcat 10.1) jest **poza zakresem**.

Powiązanie z zadaniem 133: podbicie Jacksona na serwerze (`mercury/pom.xml`) realizuje zadanie 133,
etap 1 (decyzja D5 w zadaniu 133). Tutaj zostaje wyrównanie Jacksona w pozostałych repozytoriach.

## Decyzje i plan z 2026-11-23 (po zamknięciu 096)

**Decyzje autora:** Java 17; CXF **3.5.x**; Lucene 9 jako **ostatni etap tego zadania**, dopiero po tym, jak serwer działa na Javie 17 (jeśli Java 17 nie zadziała, Lucene 9 nie wchodzi); `mercury-lib` i `hgdb-client-open` zostają na bajtkodzie 1.8, `mercury-client` zamrożony. Bez warstw zgodności (upgrade wymienia cały serwer).

**Narzędzia:** JDK 17: `D:\MojeNarzedzia\Java\jdk-17.0.2`; Maven na JDK 17: `D:\MojeNarzedzia\apache-maven-3.9.11\bin\mvn17` (zwykły `mvn` to JDK 8, `mvnibm` Java IBM). Gałąź: `hgdb-191` (w `mercury-lib`, `mercury`, `mercury-cmd`, `mercury-docker`).

**Stan względem etapu 1 (sprawdzone w POM-ach 2026-11-23):** zrobione: Jackson 2.18.11 (lib, mercury, hgdb-client-open, mercury-cmd), Tomcat 9.0.123 (obraz, `tomcat.version`, dev), sccommon 2.0.0.4, Ehcache 3.6.1. Do zrobienia: kompilator (Java 1.8, `maven-compiler-plugin` do ujednolicenia), CXF 3.0.12, Spring Security 5.4.10, AspectJ 1.7.3, Hibernate 5.4.24 w `mercury-cmd`, Lucene 7.5.0, obraz Docker z JDK 8u202.

**Etapy (kolejność wykonania):**

| Etap | Zakres | Warunek zakończenia |
|---|---|---|
| 0 | Spike: budowa `mercury-lib` i `mercury` na JDK 17 (`mvn17`), lista blokerów z dzisiejszych POM-ów | Lista błędów i modułów z uzasadnieniem |
| 1 | Budowa na JDK 17 z `--release 8`: generatory DTO na `javax.tools.ToolProvider` (4 moduły z `com.sun:tools`), `maven-compiler-plugin` 3.11+, usunięcie `-XX:MaxPermSize`, jawne zależności `javax.xml.bind`, `javax.jws`, `javax.annotation`, `javax.activation` | Wszystko buduje się na JDK 8 i 17, testy bez zmiany zachowania |
| 2 | Serwer na Javie 17: `<release>17</release>` w `mercury` i `mercury-cmd`, `TypeCaseClassGenerator`/`TypCaseBusiness` (usunąć albo przepisać), filtr serializacji HTTP invokera, obraz Temurin 17, Tomcat bez `--add-opens` | Serwer działa na JDK 17, testy `mercury` zielone |
| 3 | Stos `javax`: CXF 3.5.x, Spring Security 5.8.x, AspectJ 1.9.x, cglib, Hibernate 5.6.x w `mercury-cmd`, ActiveMQ (po sprawdzeniu release notes), Ehcache 3.10.x (opcjonalnie) | Testy SOAP/Aegis/WSDL, RMI i HTTP invoker z klientami na Javie 8 |
| 3b | **POI Server na Javie 17** (`poi-toolkit`, decyzja autora 2026-11-23: to produkt autora i część kompozycji): gałąź `hgdb-191`, budowa `mvn17` z `--release 8`, testy, eksport i import Excela przez POI Server na JDK 17 (Apache POI 4.1.x, XMLBeans), obraz `mercury-docker/poi-server` na Temurin 17, test `reportExport` na klastrze. Terracotta (`ehcache`) i ActiveMQ zostają na Temurin 8 (komponenty zewnętrzne) | Eksport i import Excela działają na JDK 17, obraz zbudowany |
| 4 | Spięcie: `mercury-cmd` i pakiet instalacyjny na 17, obrazy Docker, test na klastrze, dokumentacja (stos w `architektura.md`, moduły, obserwacje, artykuły z wymaganiem JDK 17) | Klaster na JDK 17, DoD etapów 1 i 2 |
| 5 | **Lucene 9** (po zielonym etapie 4): port `mercury-lucene-indexes`, przebudowa indeksów, pomiar względem `tasks/hgdb/119-*/baseline-2026-10-25.csv` oraz testy `LuceneNestedQueryOccurTest`, `LuceneTruncationTest`, `CostOptimizerTest` | Wyniki zgodne z baseline, wydajność bez regresji |
### Stan realizacji (2026-11-23, gałąź `hgdb-191`, niezatwierdzone)

- **Etapy 0 i 1 ✅** (`mercury-lib`, `mercury`): budowa i testy na JDK 17 (`mvn17`) dają takie same wyniki jak na JDK 8 (`mvn8`). Zmiany: profil `jdk9plus` (API Java EE `provided`: `jaxb-api` 2.3.1, `javax.annotation-api` 1.3.2, `jaxws-api` 2.3.1, `javax.jws-api` 1.1, `javax.activation-api` 1.2.0; `jaxb-runtime` 2.3.7 do testów; `maven.compiler.release=8`; `jacoco.skip=true`, bo JaCoCo 0.7.4 nie obsługuje klas Javy 17), `maven-compiler-plugin` 3.8.1 w lib, jary JAXB w `ścieżce klas` generatorów DTO, `classpathScope=compile` w generatorze API 2.0, usunięty `-XX:MaxPermSize`, generatory DTO i kompilacja typów w runtime przez `javax.tools.ToolProvider` (klasa `JavaCompilerHelper`, `--release` zamiast `-source/-target` na JDK 9+), usunięta zależność `com.sun:tools`.
- **CXF 3.5.10** w `mercury-lib`, `mercury`, `hgdb-client-open`, `mercury-cmd`; w `mercury` dodany `dependencyManagement` z `cxf-bom`, bo `chemistry-opencmis-client-bindings` dokładał CXF 3.0.12 i JAXB RI 2.1.14 (ten wymaga `--add-opens` na JDK 17). Po zmianie `mercury-ws-server` przechodzi na JDK 17 (14 testów).
- **Testy `mercury` na JDK 17:** wszystkie moduły jak na JDK 8; dwie porażki sprzed migracji (`migrationScenario` w `mercury-srv` przy pełnym przebiegu: konflikt nazwy produktu licencji między klasami testowymi; `AuthTest.testDataSource` w `mercury-gui-core`). `mercury-lib` 100% zielony na 17. `hgdb-client-open` i `mercury-cmd` kompilują się na 17.
- **Testy lokalizacji:** na JDK 9+ trzeba `-Djava.locale.providers=COMPAT` (skróty dni tygodnia: CLDR zamiast danych JRE); dotyczy też uruchamiania serwera (do `setenv`/obrazu w etapie 2).
- **Uwaga:** scenariusz `mrcTypeGeneratorScenario` (kompilacja typów w runtime) jest w `test.properties` wyłączony; po włączeniu pada tak samo na JDK 8 i 17 błędem danych (`previousVersionId` bez `rootVersionId`), więc nie weryfikuje zmiany kompilatora.
- **Etap 2 w toku (kod, 2026-11-23):** `mercury` i `mercury-cmd` kompilują się do bajtkodu 17 (`java.version` 17, moduły z twardym `1.8` przestawione na `${java.version}`; JSP-y `mercury-gui-registry` z precompilacji Jetty zostają w wersji 51, co jest bez znaczenia). Pełne testy `mercury` na JDK 17 po przebudowie od zera: bez zmian względem poprzednich wyników. `mercury-server` ma jawny `jaxb-runtime` 2.3.7 (lib serwera dostaje: `jaxb-runtime`, `jakarta.xml.bind-api` 2.3.3, `jakarta.activation`, `istack-commons-runtime`, `txw2`, `stax-ex`, a z CXF 3.5: `jakarta.xml.ws-api`, `jakarta.jws-api`, `jakarta.xml.soap-api`, `saaj-impl`). `mercury-docker`: obraz serwera na Temurin 17 (`OpenJDK17U-jdk_x64_linux_hotspot_17.0.21.1_2.tar.gz`), `setenv.sh` bez `-d64` i z `-Xlog:gc*` oraz `-Djava.locale.providers=COMPAT`; `mercury-cmd`: przykładowy `setenv.sh` bez `-d64` i `ParallelCMSThreads` (CMS usunięty w JDK 14), skrypty `mercury-cmd.sh` i `mercury-transfer.sh` na JDK 17. **Nie sprawdzone:** start serwera na JDK 17 (potrzebuje wydania, obrazu i uruchomienia), RMI i HTTP invoker między JVM 17 i 8, `jdk.serialFilter`.- **Etap 2: serwer na JDK 17 działa na `mercury-cluster` (2026-11-23, 3.0.4.41, helm rewizja 16, Temurin 17.0.21.1):** trzy węzły startują w ok. 26 s bez `SEVERE`; w logach aplikacji brak `InaccessibleObjectException` i innych błędów refleksji, więc **`--add-opens` dla Mercury nie są potrzebne** (w `catalina.out` widać tylko własne `--add-opens` dodawane przez `catalina.sh` Tomcata 9.0.123). MASTER node1, SLAVE node2 i node3 ONLINE; REST (token, `searchByQuery` na wszystkich węzłach), strony GUI, SSO, przegląd LDAP (z nowym ACL), OAuth, mapowania ról, odświeżanie konfiguracji OAuth na trzech węzłach: test `live4.sh` bez błędów. Pułapki: (1) pakiet instalacyjny bierze `lib` z `apache-tomcat/mercury/lib` (odświeżone 2026-11-23: CXF 3.5.10, wss4j 2.4.3, `jakarta.*`, `jaxb-runtime`); (2) `-Xlog` nie znosi `D:/...` w ścieżce pliku (dwukropek), w skryptach Windows obcinamy literę dysku; (3) JVM 17 odrzuca `-d64`, `-XX:-UseGCLogFileRotation` i `-XX:ParallelCMSThreads`. **Nie sprawdzone na 17:** eksport i import Excela przez POI Server (RMI do POI na JDK 8), HTTP invoker i RMI z klientami na Javie 8 (`hgdb-client-open`), `jdk.serialFilter`. Testy `live3b.sh` i `live3c.sh` (licencje) zmieniają dane i mają nieaktualne asercje (plik klucza porównywany przez `bash` w kontenerze); po ich uruchomieniu zostają wiersze testowe `TST-SRV` (`mercury-db`) i `TST-AUTH` (2, `mercury-ldap`), aktywne klucze przywrócone przez aplikację.- **Do zrobienia:** etap 2 (`<release>17</release>`, obraz Temurin 17, `setenv`/opcje JVM, RMI i HTTP invoker 17↔8, `jdk.serialFilter`), etap 3 (Spring Security 5.8, AspectJ 1.9, cglib, Hibernate `mercury-cmd`, ActiveMQ), 3b (POI Server na 17), 4 (spięcie), 5 (Lucene 9).
- **Etap 3b (POI Server na Javie 17) ✅ (2026-11-24, `poi-toolkit` 4.1.0.7):** obraz `ibpm/poi-server` na Temurin 17 (17.0.21.1); `ExcelServerApp` używał wewnętrznego `sun.rmi.server.UnicastServerRef` (na 17 `IllegalAccessError`, a NPE w `close()` go przykrywał), teraz `UnicastRemoteObject.exportObject`; `close()` odporne na `scheduler == null`. Pamięć: `ExcelFileWriterData` zapisuje strony eksportu w plikach tymczasowych (obserwacja 177), więc POI nie rośnie z liczbą wierszy (`PageSpillTest`, 20 testów na 17). Na klastrze (3 węzły, Mercury 3.0.4.41 na 17 + POI na 17, RMI): eksport `Bench211` xlsx 88 228 spraw **9,1 s** (88 229 wierszy w pliku, szczyt pamięci poda 1150 MiB; wcześniej pod padał z `OOMKilled`), csv 8,0 s, eksport z filtrem Lucene 0,2 s (543 sprawy), import csv 1000 wierszy przez `uploadPoiFile` i `ReportImportStatusRest` **3,7 s** (88 228 → 89 228 spraw). Wcześniejsze `OOMKilled` na klastrze wynikały też z ballooningu Proxmoksa na `k8s-worker4-ai` (12,4 GB zabrane maszynie; obserwacja 208), nie tylko z kodu POI. Do sprawdzenia po decyzji autora: HTTP invoker i RMI z klientami na Javie 8 (`hgdb-client-open`), pominięte w tym przebiegu.

- **Etap 3 (stos `javax`), część `mercury` (2026-11-24):** po sprawdzeniu użycia okazało się, że **AspectJ 1.7.3, cglib 2.2.2, asm 3.3.1 i `spring-security-core` 5.4.10 są martwymi zależnościami** (zero importów `org.aspectj`, `net.sf.cglib`, `org.objectweb.asm` 3.x i `org.springframework.security` w kodzie, brak `<aop:*>`, `@Pointcut`, `@Aspect`, load-time weavingu i `-javaagent`; `@Transactional` działa przez proxy Springa z własnym przepakowanym cglib). Podbijanie ich do wersji 1.9.x/5.8.x nie ma więc sensu, usunąłem je: `mercury/pom.xml` (aspectjrt, aspectjweaver, asm, cglib), `mercury-dao/pom.xml` (cglib, asm), `mercury-ws-app/pom.xml` (spring-security-core). Wynik: kompilacja `test-compile` wszystkich modułów przechodzi na JDK 17, pełne testy (`mvn17 test`): bez nowych porażek (czyli `mercury-ws-server` 14 testów zielonych, `mercury-gui-registry` 104, `mercury-ws-app` 263; porażki jak na oryginalnych POM-ach: `mercury-srv` 3 (`JoinFetchStatsTest`, `LuceneBackupSrvTest`, `SrvTest`: stan lokalnej bazy testowej i konflikt licencji między klasami testowymi, potwierdzone identycznym przebiegiem na oryginalnych POM-ach, 218 testów) oraz `AuthTest.testDataSource` w `mercury-gui-core`). Uwaga: `dependency:tree` pojedynczego modułu (`-pl` bez `-am`) bierze POM-y sąsiadów z `~/.m2` (stare `mercury-dao` nadal ciągnie cglib i asm 3.3.1), więc zestaw bibliotek liczyć w całym reaktorze. Lokalny `mercury-server/apache-tomcat/mercury/lib` oczyszczony z 26 zbędnych jarów (aspectj, cglib, asm 3.3.1, spring-security-core oraz osierocone: generatory (codemodel, jsonschema2pojo, wadl), jersey/hk2, OpenSAML 2 (opensaml 2.6.1, openws, xmltooling), gson 2.2.4, jackson-asl 1.9, http-client, localizer, nekohtml, annotations 1.3.9) i wymieniony `poi-toolkit` 4.1.0.5 na 4.1.0.7; kopia: `apache-tomcat-mercury-lib.bak-20261124`. Jary z inną wersją wskazaną przez Maven (guava 14 kontra 30.1, jasypt 1.9.2 kontra 1.9.3, commons-lang3 3.17 kontra 3.4, geronimo-jta, javax.ws.rs-api 2.0.1) zostawione bez zmian do decyzji. Spring Security, AspectJ, cglib i asm: w `mercury-cmd` zostaje sprawdzić analogicznie, tak samo Hibernate 5.4.24 do 5.6.14 (tak jak w `mercury`). ActiveMQ i Ehcache: bez zmian (klienci działają na 17 na klastrze, brokery i Terracotta zostają na Temurin 8).

- **Regresja po CXF 3.5.10 wykryta testami klienta (2026-11-24, obserwacja 210):** żądania SOAP z WS-Security padały na `EHCacheTokenStore` (`ClassNotFoundException: org.ehcache.core.util.ClassLoading`, bo CXF 3.5 wymaga Ehcache >= 3.8, a serwer ma 3.6.1). Poprawka: `MemoryTokenStore` na busie CXF w `webService.xml` (do weryfikacji po restarcie serwera i na klastrze; testy klastra nie obejmowały SOAP z WS-Security). `hgdb-client-open`: testy na JDK 17 przeciwko lokalnemu serwerowi (profil `jdk9plus` wyłącza JaCoCo 0.7.4 i `-XX:MaxPermSize`): `WsClientCXFTest` 42 testy (HTTP invoker `remoting`, klient z bajtkodem 1.8 kontra serwer na 17) zielone; 3 błędy identyczne na oryginalnych POM-ach (`testSoapSecurityConnection` = obserwacja 210; `MultiClientTest` x2: `NoSuchMethodError` w `slf4j` `Log4jLoggerAdapter`, konflikt wersji slf4j w teście). Usunięte bez zmiany wyników testów: AspectJ (test), `commons-httpclient` 3.1 (zamiast tego jawny `commons-codec` 1.15 dla `Base64`), a także `json-lib`, `commons-collections` (2004), `commons-beanutils`, `jackson-databind` i `moxy` 2.5.0-RC1, które klient wystawiał konsumentom w zakresie compile.
- **Ujednolicenie Apache POI (2026-11-24, obserwacja 212):** jedna wersja 5.2.3 zamiast mieszanki 5.2.1 z `poi-ooxml-schemas` 4.1.2; `poi-ooxml-full` 5.2.3 zamiast `poi-ooxml-schemas`, `poi-ooxml-lite` wykluczony. Zmienione POM-y w `poi-toolkit`, `mercury-lib`, `mercury`, `mercury-cmd` i `hgdb-client-open`. Sprawdzone: `poi-toolkit` 20 testów (JDK 17), pełne testy `mercury` bez nowych porażek, `mercury-cmd`/`hgdb-client-open` kompilują się. Do wydania: `poi-toolkit` 4.1.0.8 i kolejno `mercury-lib`, `mercury`, `hgdb-client-open`, `mercury-cmd`; potem obraz POI i test eksportu/importu na klastrze. Dodatkowo `CaseSearchQueryBuilder` (obserwacja 211, `AND ()` w HQL) poprawiony z testami jednostkowymi.
- **Wdrożenie 3.0.4.43 na `mercury-cluster` i testy (2026-11-24, helm rewizja 17):** obrazy `mercury` 3.0.4.43 (CXF 3.5.10, Hibernate 5.6.14, POI 5.2.3 z `poi-ooxml-full`, `poi-toolkit` 4.1.0.8, bez `asm`/`cglib`/`aspectj`/`spring-security`/`jaxb-impl`) i `poi-server` 4.1.0.8 (Temurin 17.0.21.1). Wyniki: `live4.sh` 58 sprawdzeń OK, 0 błędów; SOAP z WS-Security i HTTP invoker z klienta na Javie 8 OK (obserwacja 210 zweryfikowana na klastrze); eksport `Bench211` na POI 5.2.3: xlsx 89 228 spraw 9,3 s (89 229 wierszy w pliku, szczyt pamięci poda POI 1139 MiB), csv 8,3 s (89 229 linii), z filtrem Lucene 1,1 s; import csv 300 wierszy 2 s (89 228 do 89 528 spraw). Brak `NoClassDefFoundError`/`ClassNotFoundException`/`OutOfMemoryError` w logach Mercury; pody bez restartów. Do posprzątania przez autora: dodatkowe sprawy `Bench211` z testów importu (1000 z 14:45 UTC i 300 z 17:20 UTC) oraz pliki `*poi17_*`, `*poi523_*`, `dbg_small*`, `poi17_import1000.csv` w woluminach POI. Do końca etapu 4: dokumentacja (wymaganie JDK 17 w artykułach, tabela stosu w `docs/architektura.md`, opisy modułów), `cxf-bom`/POI w `mercury-cmd` zweryfikowane budową, decyzje o wydaniu i PR.

## Kontekst i Wymagania

### Stan wersji (skrót)

Szczegóły z numerami linii w POM-ach: [etap 1](etap-1-rewizja-wersji-java8.md).

| | mercury-lib | mercury | hgdb-client-open | mercury-client | mercury-cmd |
|---|---|---|---|---|---|
| Java | 1.8 | 1.8 | 1.8 | 1.8 | 1.8 |
| Spring | 2.5.6 (provided) | 5.3.20 | 5.3.21 | 4.1.9 | 5.3.20 |
| Spring Security | – | 5.4.10 | – | – | 5.4.10 |
| CXF | 3.0.10 | 3.0.12 | 3.0.10 | 2.7.15 | 3.0.10 |
| Hibernate | – | 5.6.14.Final | – | – | 5.4.24 |
| Jackson | 2.12.6.1 | 2.13.2 (podbicie w zadaniu 133) | `[2.8.11.1,)` | 2.5.3 | 2.13.2.2 |
| Logowanie | log4j 1.2.17 | log4j2 2.17.2 | log4j 1.2.14 | log4j 1.2.14 | log4j2 2.17.2 + slf4j-log4j12 |

Tomcat: 8.5.82 (`mercury-gui-core`, obraz Docker na CentOS 8 i JDK 8u202), 8.5.14 (skrypt
instalatora), 8.0.32 (serwer testowy). Linie 8.0 i 8.5 nie mają już wsparcia.

### Granica stosu serwera

**Ograniczenie Java 8 wyznacza granicę stosu serwera.** Encje i kontrakty w `mercury-lib`
używają `javax.persistence`, `javax.jws` i `javax.xml.bind`. Stos `jakarta` (Spring 6, CXF 4,
Hibernate 6) tych adnotacji nie widzi. Dopóki lib zostaje w `javax`, serwer musi zostać na
Spring 5.3, CXF 3.5/3.6, Hibernate 5.6 i Tomcat 9. Przejście na `jakarta` wymagałoby drugiego
artefaktu lib (Eclipse Transformer) i własnego remotingu, bo Spring 6 usunął HTTP invoker i RMI.

## Decyzje

| # | Decyzja | Opcje | Status |
|---|---|---|---|
| D1 | Docelowa Java serwera | 17 lub 21 | ✅ **17** (na razie). W zadaniu 133 jako D3 |
| D2 | Czy `hgdb-client-open` i `mercury-cmd` przechodzą na nowszą Javę | Zostają na 1.8 / przechodzą razem z serwerem | ✅ `hgdb-client-open` **zostaje na 1.8**, bo zależy od niego `mercury-client`. `mercury-cmd` **przechodzi na 17 razem z serwerem**, bo to „implementacja” końcówki: zależy od artefaktów serwera (`mercury`). W zadaniu 133 jako D4 |

## Definicja Gotowości (DoD)

- Zrealizowane etapy 1 i 2 według ich DoD.
- Dokumentacja workspace zaktualizowana: tabela stosu w `docs/architektura.md` (brakuje Tomcata 8.5.82
  i Spring Security 5.4.10), `docs/moduly/*.md`, nowe pozycje w `docs/obserwacje.md`.

## Kluczowe Pliki w Projekcie

Ścieżki względne do `D:\workspace\git`.

| Plik | Rola |
|---|---|
| `mercury-lib/pom.xml`, `mercury/pom.xml`, `hgdb-client-open/pom.xml`, `mercury-client/pom.xml`, `mercury-cmd/pom.xml` | Wersje zależności |
| `mercury-lib/mercury-entities-dto-generator/` | Użycie `sun.tools` (bloker budowania na JDK 9+) |
| `mercury/mercury-srv/src/main/java/org/mercury/data/javax/` | Kompilacja w runtime (`com.sun.tools.javac`, `-source 1.7`) |
| `mercury-docker/mercury-3.0/Dockerfile` | Obraz serwera |
| `mercury-cmd/mercury-install-package/` | Pakiet instalacyjny (Tomcat, skrypty) |

## Słownik / Zasady

- `mercury-lib`, `hgdb-client-open` i `mercury-client` zostają na bajtkodzie Java 8 i stosie `javax`.
- `mercury` i `mercury-cmd` mogą używać Javy 17.
- Stos `javax`: Spring 5.3, CXF 3.x, Hibernate 5.6, Tomcat 9. Stos `jakarta`: poza zakresem.
- Wymagania JDK bibliotek (CXF 3.6, ActiveMQ 5.17, jakarta API 3.1) pochodzą z wiedzy ogólnej.
  Przed decyzją trzeba je potwierdzić w release notes albo w POM-ach na Maven Central.
- Kod ma wyższy priorytet niż dokumentacja.

## Uzupełnienie z zadania 119 (2026-10-25): Lucene 9 należy do tego zadania

Decyzja autora: **podniesienie Lucene do wersji 9 robimy w 191**, razem z Javą 17 (w 119 zostaje Lucene 7.5.0).
Powody i dane (szczegóły: `tasks/hgdb/119-*/spike-lucene-8-2026-10-25.md`):

- Lucene 8.11.x działa na Javie 8, a **Lucene 9.0 wymaga Javy 11** (ogłoszenie wydania 9.0). Lucene 9 nie czyta indeksów 7.x,
  więc po przejściu potrzebna jest przebudowa indeksów (i tak wymagana przy upgrade u klienta).
- Spike 7.5.0 do 8.11.2 (gałąź `hgdb-119-spike-lucene8` w `mercury`, commit `80217dbf2`, nie kompiluje się) wykazał ok. 65 błędów
  kompilacji w 20 plikach `mercury-lucene-indexes`. Dotyczą m.in. konstruktorów `TopDocs` i `TopFieldDocs` (`TotalHits`),
  `Collector.needsScores()` na `scoreMode()` i `Scorer` na `Scorable` (6 klas kolektorów), `TopDocsCollector.pq` (`final`),
  klasy `FieldCollectorTopDocs` w pakiecie Lucene (największe ryzyko), `createWeight` na `ScoreMode`, `IndexWriter.maxDoc()`.
  Port 7 do 9 w jednym kroku jest tańszy niż dwa porty (7 do 8, 8 do 9).
- Dodatkowe zmiany w 9 (z wiedzy ogólnej, do potwierdzenia): usunięcie `MultiFields`, przeniesienie `lucene-analyzers-common` do
  `lucene-analysis-common`, usunięcie `CustomScoreQuery` (w kodzie to tylko stałe w `CaseCustomScoreProvider`), `RAMDirectory`.
- Punkt odniesienia dla pomiarów po porcie: baza z `tasks/hgdb/119-*/baseline-2026-10-25.csv` (41 zapytań na indeksie INEA 3.0,
  wyniki zgodne we wszystkich trybach) oraz testy `LuceneNestedQueryOccurTest`, `LuceneTruncationTest`, `CostOptimizerTest`.
- Zakres kolektorów po stronie 119 (W3, W4, W5) powinien być pisany tak, by nie utrudniał portu (bez klas w pakiecie
  `org.apache.lucene.*`, bez przypisywania `pq`, bez zależności od `TopDocs.maxScore`).
