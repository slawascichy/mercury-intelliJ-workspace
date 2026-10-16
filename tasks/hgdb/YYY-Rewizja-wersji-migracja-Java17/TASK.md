# [YYY] Rewizja wersji oprogramowania i migracja serwera na Javę 17

> Numer zadania do nadania. Zadanie wydzielone z [133 – Swagger](../133-Swagger-implementacja/TASK.md)
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
