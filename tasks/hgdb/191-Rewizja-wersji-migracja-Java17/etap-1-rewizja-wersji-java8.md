# [191] Etap 1 – Rewizja wersji zależności (bez zmiany Javy)

Zadanie nadrzędne: [TASK.md](TASK.md). Kolejny etap: [etap 2](etap-2-migracja-serwera-java17.md).

## Cel zadania
Uporządkować i podbić zależności we wszystkich repozytoriach Maven, nadal z bajtkodem Java 8.
Przygotować `mercury-lib` do budowania nowszym JDK z `--release 8`.

## Kontekst i Wymagania

### Stan wersji (z POM-ów)

| | mercury-lib | mercury | hgdb-client-open | mercury-client | mercury-cmd |
|---|---|---|---|---|---|
| Java src/target | 1.8 (`pom.xml:20`) | 1.8 (`:39`) | 1.8 na sztywno (`:316-317`) | 1.8 (`:19`) | 1.8 (`:35`) |
| maven-compiler-plugin | 3.3 (`:346`) | 3.8.1 (`:319`), `-parameters` | 3.3 (`:313`) | 3.3 (`:296`) | 3.3 (`:264`) |
| Spring | 2.5.6 (`:33`), provided | 5.3.20 (`:43`); spring-test/ws 5.2.20 | 5.3.21 (`:21`) | 4.1.9 (`:33`), spring-ws 1.5.10 | 5.3.20 (`:39`) |
| Spring Security | – | 5.4.10 (`:46`) | – | – | 5.4.10 (`:42`) |
| CXF | 3.0.10 (`:65`) | 3.0.12 (`:88`) | 3.0.10 (`:35`) | 2.7.15 (`:43`) | 3.0.10 (`:83`) |
| Hibernate | – | 5.6.14.Final (`:52`) | – | – | 5.4.24 (`:45`) |
| JPA API | `javax.persistence` 2.1.0 | hibernate-jpa-2.1-api | persistence-api 1.0 | persistence-api 1.0 | persistence-api 1.0 |
| Jackson | 2.12.6.1 (`:90`) | 2.13.2 / 2.13.2.2 (`:118-119`) | `[2.8.11.1,)` (`:71`) | 2.5.3 (`:64`) | 2.13.2.2 |
| Lucene | – | 7.5.0 (`:61`) | – | – | 7.5.0 |
| Ehcache | 3.6.1 | 3.6.1 (`:58`) | 2.10.1 | 2.10.1 | 3.6.1 |
| ActiveMQ | – | 5.16.2 (`:121`) | – | – | 5.16.2; 5.15.8 w `mercury-srv-cmd` i `mercury-install-package` |
| JAXB RI | – | 2.2.11 (`:120`) | 2.2.11 | 2.2.11 | 2.2.11 |
| servlet-api | 2.5 | 3.1.0 (`:105`) | 2.5 | – | 2.5 |
| Logowanie | log4j 1.2.17 (`:53`) | log4j2 2.17.2 + slf4j-reload4j 1.7.36 | log4j 1.2.14 | log4j 1.2.14 | log4j2 2.17.2 + slf4j-log4j12 |
| sccommon | 1.0.8.4 (`:81`) | 1.0.8.4.20241101 (`:108`) | 1.0.8.4-jdk1.7 | 1.0.8.4-jdk1.7 | 1.0.7 |

Numery linii dotyczą głównego `pom.xml` danego repozytorium.

Tomcat:

- `mercury/mercury-gui-core/pom.xml:101-102`: tomcat-catalina 8.5.82.
- `mercury-docker/mercury-3.0/Dockerfile:38-41`: Tomcat 8.5.82, JDK 8u202, CentOS 8 (bez wsparcia).
- `mercury-cmd/mercury-install-package/src/main/scripts/restart-with-update-mercury-db.sh:3`: Tomcat 8.5.14.
- `mercury/mercury-server`: Tomcat 8.0.32 (testowy).
- Obrazy ActiveMQ i Ehcache: `ringcentral/jdk:8u202`. Broker w Dockerze: ActiveMQ 5.16.5.

### Przestarzałe biblioteki, bez wsparcia lub ze znanymi lukami (wg wiedzy ogólnej)

| Biblioteka | Gdzie |
|---|---|
| log4j 1.x | mercury-lib, hgdb-client-open, mercury-client |
| commons-collections 3.2.1, commons-fileupload 1.1.1 | mercury-client (`pom.xml:597`, `:616`) |
| json-lib 2.2.3 | mercury-client, hgdb-client-open, mercury-cmd |
| axis 1.4 | mercury-lib, mercury, mercury-client |
| commons-httpclient 3.1 | kilka repozytoriów |
| dom4j 1.6.1 | mercury-lib, hgdb-client-open |
| xmlbeans 2.5.0, moxy 2.5.0-RC1, mysql-connector 5.1.17 | mercury-lib |
| aspectj 1.7.3, cglib 2.2.2, asm 3.x | serwer |
| Jackson 2.5.3, Spring 4.1.9, ojdbc6 | mercury-client |

Inne problemy:

- Zakresy wersji `[x,)` dają niepowtarzalne buildy.
- `-XX:MaxPermSize` w 19 POM-ach (JVM 17+ odrzuca tę opcję).
- Generator DTO w `mercury-lib` używa `sun.tools.java.CompilerError` z `tools.jar`
  (`mercury-entities-dto-generator/.../ClassGeneratorApp.java:15,112`,
  `WsResultDtoClassGeneratorApp.java:19,142`). Zależność systemowa `com.sun:tools` jest też w
  `mercury-entities`, `mercury-ws-dto-api`, `mercury-entities-ids` i `mercury-ws-server-api20-generator`.
  Bez przepisania na `javax.tools.ToolProvider` lib nie zbuduje się na JDK 9+.

### Ograniczenia

- `mercury-lib` i `mercury-client` zostają na bajtkodzie Java 8 i stosie `javax`.
- `mercury-client` działa na WebSphere 8.5.5 z CXF 2.7.15 i Spring 4.1.9. Podbicie jego zależności
  wymaga zgodności z bibliotekami serwera IBM BPM. Zakres zmian w tym repozytorium do uzgodnienia.
- Zależności lib mają scope `provided`, więc w runtime wersje dostarcza serwer.

### Zakres prac

1. Ujednolicić `maven-compiler-plugin` do 3.11+ i używać `<release>8</release>` (przy JDK 9+).
2. Skompilować `mercury-lib` przeciw Spring 5.3.x zamiast 2.5.6.
3. Wyrównać wersje CXF w lib, serwerze, kliencie i narzędziach (cel: 3.5.x – ostatnia linia z Javą 8,
   do potwierdzenia).
4. Zastąpić log4j 1.x przez reload4j albo log4j2 / slf4j.
5. Usunąć lub podbić commons-collections, commons-fileupload, dom4j, json-lib, commons-httpclient.
6. Ujednolicić Jacksona w `mercury-lib`, `hgdb-client-open` (zakres `[2.8.11.1,)`), `mercury-client`
   (2.5.3) i `mercury-cmd` z wersją serwera. Podbicie na serwerze (`mercury/pom.xml`) przeniesiono do
   [zadania 133, etapu 1](../133-Swagger-implementacja/etap-1-openapi-statyczne.md) (decyzja D5 w zadaniu 133). Podbić ActiveMQ do 5.16.x we wszystkich miejscach.
7. Zastąpić zakresy `[x,)` stałymi wersjami.
8. Przepisać generatory DTO na `javax.tools.ToolProvider` i usunąć zależność `com.sun:tools`.
9. Spring Security 5.4.10 → 5.8.x (Java 8).
10. Zweryfikować i uaktualnić tabelę stosu w `docs/architektura.md` (brakuje Tomcata 8.5.82
    i Spring Security 5.4.10).

## Definicja Gotowości (DoD)

- Wszystkie repozytoria budują się na JDK 8. `mercury-lib` buduje się też na JDK 17 z `--release 8`.
- Brak log4j 1.x i zakresów wersji `[x,)` w POM-ach (poza uzgodnionymi wyjątkami w `mercury-client`).
- Testy serwera przechodzą. Klient `hgdb-client-open` działa z serwerem (SOAP, HTTP invoker, RMI).
- Tabela stosu w `docs/architektura.md` i opisy modułów zaktualizowane.

## Kluczowe Pliki w Projekcie

| Plik | Rola |
|---|---|
| `mercury-lib/pom.xml`, `mercury/pom.xml`, `hgdb-client-open/pom.xml`, `mercury-client/pom.xml`, `mercury-cmd/pom.xml` | Wersje zależności |
| `mercury-lib/mercury-entities-dto-generator/src/main/java/.../ClassGeneratorApp.java`, `WsResultDtoClassGeneratorApp.java` | Użycie `sun.tools` |
| `mercury/mercury-gui-core/pom.xml` | Tomcat 8.5.82 |
| `mercury-docker/mercury-3.0/Dockerfile` | Obraz serwera |

## Słownik / Zasady

- Etap nie zmienia wersji Javy ani pakietów `javax`.
- Każdą podbitą wersję sprawdzić pod kątem wymagań JDK (release notes).
