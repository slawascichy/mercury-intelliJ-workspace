# [240] Ujednolicenie wersji zależności w `mercury-cmd` oraz `hgdb-client-open`

Status: **zrobione 2026-11-13** (kod w gałęziach `hgdb-237`, PR i merge robi autor).
Numer zadania to 240, a gałąź nazywa się `hgdb-237` (literówka autora, zostaje). Jedna gałąź w obu repozytoriach.
Źródło: obserwacje 8 i 9 w `docs/obserwacje.md`.

## Zakres

| Obs. | Repozytorium | Problem | Zmiana |
|---|---|---|---|
| 8 | `mercury-cmd` | Właściwość `junit.version` zdefiniowana dwa razy (4.13.1 w linii 103, 4.7 w linii 129). Maven brał ostatnią, czyli 4.7. | Usunięty duplikat 4.7 w `pom.xml`. Zostaje 4.13.1. |
| 9 | `hgdb-client-open` | `hgdb-ws-client-cxf` zależał w zakresie `compile` od `pro.ibpm:tw4j` (8.6.3.21030.2.0.3.20230127), biblioteki dla IBM BPM. W kodzie klienta nie ma jej użycia (grep po `*.java`, `pom.xml`, `*.xml`). | Zależność usunięta z `hgdb-ws-client-cxf/pom.xml`. |

Przy okazji (bez zadania, tylko opis stanu) w obserwacjach 6, 7 i 10 dopisano stan z 2026-11-13: obs. 7 oznaczona ✅
(`set-versions.sh` podnosi wersje w `mercury-cmd` przy każdym wydaniu), obs. 6 i 10 częściowo wykonane.

## Weryfikacja

- `hgdb-client-open`: `mvn -o -pl hgdb-ws-client-cxf -am clean test-compile` kończy się bez błędów.
- `mercury-cmd`: `mvn -o -DskipTests test-compile` kończy się bez błędów.
- Testów nie uruchamiano (wymagają działającego serwera Mercury DB).

## Skutki

- Testy `mercury-cmd` używają teraz JUnit 4.13.1 zamiast 4.7.
- `tw4j` nie jest już zależnością przechodnią klienta. Projekt, który używał jej pośrednio przez klienta, musi dodać ją sam.

## Do zrobienia przez autora

- Commit w `mercury-cmd` i `hgdb-client-open` (gałąź `hgdb-237`), PR, merge, `git pull` na `master`, usunięcie lokalnej gałęzi.
- Commit w workspace (`docs/obserwacje.md`, ten plik).
