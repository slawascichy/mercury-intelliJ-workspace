# [191] Etap 2 – Migracja serwera na Javę 17 (stos `javax`)

Zadanie nadrzędne: [TASK.md](TASK.md). Zależy od: [etap 1](etap-1-rewizja-wersji-java8.md).

## Cel zadania
Uruchomić i budować serwer (`mercury`) na Javie 17 (decyzja D1; Java 21 później). `mercury-lib`
i `mercury-client` zostają na bajtkodzie Java 8. Stos serwera zostaje na `javax`.

## Kontekst i Wymagania

### Dlaczego `javax`, a nie `jakarta`

Encje i kontrakty w `mercury-lib` używają `javax.persistence` (193 pliki w `mercury-entities`),
`javax.jws` i `javax.xml.bind`. Spring 6, CXF 4, Hibernate 6 i Tomcat 10.1 widzą tylko `jakarta.*`.
Na takim stosie Hibernate nie zmapuje encji z lib, a CXF nie wystawi `@WebService`.

Przejście na `jakarta` wymagałoby:

- drugiego artefaktu lib (np. klasyfikator `-jakarta`) z tego samego źródła, przez Eclipse Transformer;
- własnego remotingu albo wygaszenia HTTP invokera i RMI (Spring 6 usunął `org.springframework.remoting`);
- migracji Hibernate 6 (zmiany API generatorów ID i typów).

To osobne, przyszłe zadanie. Opłaca się dopiero po odcięciu `mercury-client` (WebSphere)
od wspólnych artefaktów.

### Docelowy stos (wersje do potwierdzenia w release notes)

| Komponent | Obecnie | Cel |
|---|---|---|
| Java | 1.8 | 17 (`<release>17</release>` w `mercury` i `mercury-cmd`) |
| Spring | 5.3.20 | 5.3.x (najnowsza; wspiera JDK 8–21) |
| Spring Security | 5.4.10 | 5.8.x |
| CXF | 3.0.12 | 3.5.x lub 3.6.x (3.6 wymaga Javy 11 – przypuszczenie) |
| Hibernate | 5.6.14 | 5.6.x (najnowsza) |
| AspectJ | 1.7.3 | 1.9.x |
| cglib 2.2.2 | – | Spring repack (`org.springframework.cglib`) lub ByteBuddy |
| Ehcache | 3.6.1 | 3.10.x (lepsza zgodność z Javą 17 – przypuszczenie) |
| ActiveMQ | 5.16.x | 5.16.x (od 5.17 wymaga Javy 11 – przypuszczenie; możliwe podbicie) |
| Tomcat | 8.5.82 / 8.5.14 / 8.0.32 | 9.0.x (ostatnia linia `javax.servlet`) |
| Obraz Docker | CentOS 8 + JDK 8u202 | Eclipse Temurin 17 |

### Blokery w kodzie (pliki `*.java`, bez `target/` i `repo/`)

| Wzorzec | mercury-lib | mercury | Działanie |
|---|---|---|---|
| `javax.xml.bind` | 325 | 65 (ws-app 33, srv 10, ws-server 9) | Jawne zależności `javax.xml.bind:jaxb-api` + `jaxb-runtime` 2.3.x |
| `javax.jws` | 72 (ws-server-api) | 142 (ws-server 67, ws-server-api20 68) | `javax.xml.ws:jaxws-api` + `javax.jws-api` |
| `javax.annotation` | 490× `@Generated`, 92× `@Resource`, 1× `@PostConstruct` (łącznie) | | `javax.annotation:javax.annotation-api` |
| `javax.activation` | – | 1 (`mercury-srv/.../MailFileLogic.java:26`) | `javax.activation` / `jakarta.activation` 1.2.x |
| `sun.*`, `com.sun.tools` | generatory DTO | `mercury-srv/.../TypeCaseClassGenerator.java:20-21,68` | Etap 3 (lib); w serwerze `javax.tools.ToolProvider` |
| `java.rmi`, `org.springframework.remoting` | 5 / 8 | 30 / 16 | Działa na Spring 5.3. Przetestować serializację |

Inne:

- `org.mercury.data.javax.TypeCaseClassGenerator` kompiluje kod w runtime przez
  `com.sun.tools.javac.Main` z `-source/-target 1.7`, a `TypCaseBusiness` rzuca
  `sun.tools.java.CompilerError` (usunięte w JDK 9+). Mechanizm używa tylko test
  `MrcTypeGeneratorScenario`. Do decyzji: usunąć pakiet albo przepisać na `javax.tools.ToolProvider`
  z `--release 8`. Jeśli zostaje, serwer musi działać na pełnym JDK, nie na JRE.
- Usunąć `-XX:MaxPermSize` (19 POM-ów) i ze skryptów startowych.
- `--add-opens` stosować tylko awaryjnie, z listą w dokumentacji.
- `CodebaseAwareObjectInputStream` (HTTP invoker) to deserializacja Javy. Rozważyć filtr
  `jdk.serialFilter` (ryzyko bezpieczeństwa).
- Decyzja D2:
  - `hgdb-client-open` zostaje na bajtkodzie 1.8, bo zależy od niego `mercury-client` (WebSphere).
    Na Javie 17 działa jako zwykła biblioteka.
  - `mercury-cmd` przechodzi na Javę 17 razem z serwerem. Zależy od artefaktów `mercury`
    (dziś od wydanej wersji `3.0.3.2.12`), więc po migracji musi wskazać wersję serwera na Javie 17.
  - Do sprawdzenia: `mercury-cmd` korzysta z HTTP invokera/RMI przez `hgdb-multi-client`.
    Test zgodności serializacji obejmuje więc również narzędzia.

### Ryzyka

- Zmiana CXF 3.0 → 3.5/3.6: przetestować SOAP, Aegis i WSDL (zgodność z istniejącymi klientami).
- RMI i HTTP invoker: zgodność serializacji między klientem na Javie 8 a serwerem na Javie 17.
- Lucene zostaje na 7.5.0. Lucene 9 zmienia format indeksu i wymaga reindeksacji (poza zakresem).

## Definicja Gotowości (DoD)

- `mercury` i `mercury-cmd` budują się i przechodzą testy na JDK 17 (`<release>17</release>`).
- `mercury-lib`, `hgdb-client-open` i `mercury-client` mają bajtkod 1.8.
- Narzędzia `mercury-cmd` (synchronizacja typów, indeksy Lucene, transfer) działają z serwerem na Javie 17.
- Serwer działa na Tomcat 9 i JDK 17 bez `--add-opens` (albo z udokumentowaną listą).
- Klienci `hgdb-client-open` (Java 8) i `mercury-client` współpracują z serwerem: SOAP, HTTP invoker, RMI.
- Obraz Docker i pakiet instalacyjny zaktualizowane.
- Zaktualizowane `docs/architektura.md`, `docs/moduly/*.md` i `docs/obserwacje.md`.

## Kluczowe Pliki w Projekcie

| Plik | Rola |
|---|---|
| `mercury/pom.xml` | Wersje stosu serwera, opcje kompilatora |
| `mercury-cmd/pom.xml` | Java 17, wersja zależności od `mercury` |
| `mercury/mercury-srv/src/main/java/org/mercury/data/javax/` | Kompilacja w runtime (eksperymentalna) |
| `mercury/mercury-srv/src/main/java/pro/ibpm/mercury/business/attr/TypCaseBusiness.java` | `sun.tools.java.CompilerError` |
| `mercury/mercury-srv/src/main/java/.../MailFileLogic.java` | `javax.activation` |
| `mercury/hgdb-rmi-server-api/` | RMI i HTTP invoker |
| `mercury-lib/mercury-spring-remoting/` | Kopia HTTP invokera |
| `mercury-docker/mercury-3.0/Dockerfile` | Obraz serwera |
| `mercury-cmd/mercury-install-package/` | Pakiet instalacyjny (Tomcat, skrypty) |

## Słownik / Zasady

- Stos `javax`: Spring 5.3, CXF 3.x, Hibernate 5.6, Tomcat 9.
- Stos `jakarta`: Spring 6, CXF 4, Hibernate 6, Tomcat 10.1. Poza zakresem tego zadania.
