# Plan najbliższych działań (2026-10-27, wersja 5)

Plan uwzględnia decyzje autora z 2026-10-26 i 2026-10-27. Wersja 5 powstała późnym wieczorem 2026-10-27, po testach 058 i 214 na serwerze dev. Szacunki są orientacyjne (przypuszczenie), bo opierają się na opisach zadań
i krótkiej lekturze kodu, a nie na pełnym rozpoznaniu.

**Plan autora (2026-10-27):** najpierw **zakończyć 058 i 214**, potem **zrealizować 016, 049 i 191**; do kompletu programu należą też **209 i 211** (bez nich program nie jest kompletny). Zadania 193, 195, 198, 208 i 215 mają status „not now”. Po zakończeniu planu autor stawia serwer testowy i zaczyna testować nowe funkcje Mercury.

**Zmiany w wersji 5 (2026-10-27, późny wieczór):**
- 208 „not now”; 209 i 211 **wracają do planu** (wersja 4 wyłączyła je omyłkowo, autor je przeoczył). Kolejność: 058 → 214 → 016 → 049 → 191 → 209 → 211 (211 jako zwieńczenie z wydaniem).
- Wydanie `mercury-lib` 3.0.4.18 poprawione przez autora (2026-10-27): numer jest używany w `hgdb-client-open`, `mercury-cmd` i na serwerze dev.
- Z wersji 4 zostają: 058 i 214 mają kod, testy na serwerze dev i dokumentację (czekają na zatwierdzenia, wydania i zamknięcie, sekcja 3); `mercury-client` zamrożony (zgodny z `mercury-v3.0.1.20210709`); nowy projekt komunikacji IBM BPM -> HgDB to zadanie 215 („not now”).

## 1. Decyzje autora

| # | Decyzja | Skutek |
|---|---|---|
| 1 | Kolejność faz A → B → C jest dobra (2026-10-26) | Zastąpiona przez decyzję 11 |
| 2 | Poprawić `HtmlControlUtils` (pozycja 7 zadania 190) | Zakres 190 rośnie o zmianę w `mercury` (zapisane w `190-…/TASK.md`) |
| 3 | 058: tylko REST, SOAP niepotrzebny | Usługa `I*ExtRest` w `mercury-ws-app`, bez zmian w `mercury-lib` |
| 4 | 049: szkic oparty o repozytorium plikowe, sprawdzić `web.xml` | Stan szkicu opisany w `049-…/TASK.md`; obserwacja 87 (endpointy CMIS w WAR) |
| 5 | Pytania z 209 rozstrzygamy przy przejściu do 209 | Bez zmian |
| 6 | Dodać zadanie obrazów Docker, zwieńczające pakiet zmian i wydanie | Zadanie `211-Aktualizacja-obrazow-Docker-i-wydanie` |
| 7 | 169: `mercury-client` migrujemy do `String` na `master` | Zrobione (PR `hgdb-169` scalony w `mercury-lib` i `mercury-client`); po decyzji 13 `mercury-client` nie jest dalej rozwijany |
| 8 | 169: `LoggerEvent.caseId` na `String`, skrypty tylko dla PostgreSQL | Zrobione w kodzie (`mercury-lib`, `mercury`) |
| 9 | Dokumentację 169 poprawiamy w `docusaurus-hgdb` na `main` | Zrobione, commit wykonany przez autora |
| 10 | Zadanie 016 Widoki wchodzi do planu przed wydaniem (komplet funkcjonalności) | Zostaje w planie (etapy 0–4 w `016-Widoki/TASK.md`) |
| 11 | **Kolejność: zakończyć 058 i 214, potem 016, 049 i 191** (2026-10-27) | Sekcja 3; uzupełniona decyzją 15 o 209 i 211 |
| 12 | **193, 195, 198, 208 i 215 „not now”** (2026-10-27) | Bez działań |
| 15 | **209 i 211 pozostają w planie** (2026-10-27): bez nich program nie jest kompletny | Etap 3 w sekcji 3; po nim autor stawia serwer testowy i testuje nowe funkcje |
| 13 | **`mercury-client` zamrożony**, zgodny z `mercury-v3.0.1.20210709`; gałąź `hgdb-058` w `mercury-client` do usunięcia (`-D`) (2026-10-27) | Poza zakresem 214; zastępuje go zadanie 215 („not now”) |
| 14 | **`hgdb-client-open` zostaje na `sccommon` 2.0.0.1 i ehcache 3.6.1** (2026-10-27) | SecurityProvider nie kompiluje się na tym stosie (obserwacja 102); jego upgrade to osobne zadanie, jeszcze bez numeru |

## 2. Stan kolejki

| Zadanie | Status | Uwagi |
|---|---|---|
| 39, 119, 121, 171 | **zamknięte** | Kod w `master`, `mercury-lib` 3.0.4.16 |
| 169 Typ id sprawy `String` | kod scalony | PR `hgdb-169` scalony w `mercury-lib` i `mercury-client`; wydanie `mercury-lib` wykonane. Do potwierdzenia przez autora: czy zostało coś z `169-…/audyt-2026-10-26.md` i `openapi-doc-report.txt` |
| 190 Dokumentacja metadanych typów | kod scalony (PR #213) | Do potwierdzenia przez autora: stan dokumentacji w `docusaurus-hgdb` |
| **058 Logger: poziomy logowania (REST)** | **kod, testy i dokumentacja gotowe** | Skrypt `test-manualny.sh`: 19 OK, 0 błędów na Logbacku; panel i `/admin/loggers/*` dają 403 dla zwykłego użytkownika. Otwarte: zatwierdzenie zmian, decyzja o obserwacji 107 (sekret klienta OAuth w dzienniku przy DEBUG), zamknięcie |
| **214 Migracja logowania na Logback** | **kod i test dymny gotowe** | Pięć repozytoriów (`mercury-lib`, `mercury`, `hgdb-client-open`, `mercury-cmd`, `mercury-docker`), test na serwerze dev wykonany. Otwarte: zatwierdzenia, wydania i podbicie wersji, transfer `mercury-transfer`, `LoggerConfigurator` w `mercury-srv-cmd` na pakiecie, rotacja plików. Szczegóły: `214-…/TASK.md` |
| **016 Widoki** | **następne** (po 058 i 214) | ok. 3 tygodnie (przypuszczenie). Etapy 0–4 w `016-Widoki/TASK.md`; cztery bazy, uprawnienia jak dla spraw, wynik w modelu Iron POI Server, nowe DTO w `mercury-lib` (kolejne wydanie) |
| **049 CMIS** | **po 016** | Szkic Chemistry w `web.xml` (obserwacja 87); duże |
| **191 Rewizja wersji i Java 17** | **po 049** | Etap 1: kilka dni; etap 2 duże (zawiera Lucene 9) |
| **209 Polecenie kalibracji (`mercury-cmd`)** | **po 191** | Szkic; pytania rozstrzygamy przy starcie. Wariant: po Lucene 9, żeby nie portować kodu pomiarowego dwa razy (przypuszczenie) |
| **211 Obrazy Docker i wydanie** | **ostatnie (po 209)** | Zwieńczenie programu; zależy od wydań `mercury`, `hgdb-client-open`, `mercury-cmd` i od zamknięcia pozostałych zadań planu. Po nim autor stawia serwer testowy |
| 193, 195, 198, 208, 215 | **not now** | Bez działań. 215: nowa komunikacja IBM BPM -> HgDB (`215-Nowa-komunikacja-IBM-BPM-HgDB/TASK.md`); 208: lokalizacja Swagger UI |
| SecurityProvider: stos `sccommon`/ehcache | nowe zadanie, bez numeru | Wynik analizy w `214-…/TASK.md` (sekcja „Zgodność z SecurityProviderem”) i obserwacji 102; do założenia przez autora, nie jest w bieżącym planie |

## 3. Kolejność

### Etap 1: zakończenie 058 i 214

1. **Zatwierdzenia przez autora** (commity robi autor): `mercury`, `mercury-lib`, `hgdb-client-open`, `mercury-cmd`, `mercury-docker`, `docusaurus-hgdb` (nowa strona „Logging configuration”, `Logging_levels`) i workspace (`docs/`, `tasks/`). Gałąź `hgdb-058` w `mercury-client` usunąć (`git checkout master`, `git branch -D hgdb-058`).
2. **Obserwacja 107** (zrobione 2026-10-27, decyzja autora): `OAuthFilter` i `SystemOAuthController` nie zapisują już sekretu klienta OAuth; sprawdzone na serwerze dev. Zostaje decyzja autora o oczyszczeniu trzech starych linii w dzienniku serwera dev.
3. **Wydania** (wykonuje autor; stan 2026-10-27: `mercury-lib` 3.0.4.18 poprawione, `mercury` 3.0.4.9, `hgdb-client-open` 3.1.4.18). Po zatwierdzeniach i ewentualnych poprawkach z kroku 2 mogą być potrzebne kolejne numery, które poda autor. W `mercury-cmd` podbić `mercury.static.version`, `hgdb-client.version`, `hgdb.client.version.release` i `mercury.server.project.version` (stan 2026-10-27: 3.0.4.18, 3.1.4.18, 3.1.4.18 i 3.0.4.9; `mvn -o clean test-compile` przechodzi).
4. **Otwarte sprawdzenia 214:** transfer `mercury-transfer` między dwiema instancjami (pusty zbiór `typeCodes`, obserwacja 105), `LoggerConfigurator` w `mercury-srv-cmd` na pakiecie instalacyjnym, rotacja plików logu (limit 7 MB, 20 kopii; obserwacja 103), REST z tokenem zwykłego użytkownika (zrobione w teście 7–8).
5. **Zamknięcie:** push `hgdb-058`, PR i merge (autor), pull `master`, ✅ w `docs/obserwacje.md` (98–100 oznaczone, 101–107 według decyzji), aktualizacja `kolejka-zadan` w pamięci. Nowej gałęzi `hgdb-NNN` nie zakładamy przed merge'em 058 (214 jest podzadaniem 58).

### Etap 2: funkcje i duże zmiany (kolejność autora)

6. **016, widoki.** Etap 0 (rozpoznanie i koncepcja, 1–2 d) zaraz po zamknięciu etapu 1, bo od odpowiedzi autora na 6 pytań z `016-Widoki/TASK.md` zależy zakres. Potem etapy 1–3 (odczyt widoków w REST, odporność na widoki `INVALID` i blokady,
   wynik w JSON i Excelu), na końcu etap 4 (Iron Server), który można wydać osobno. Zmiana API oznacza `openapi-doc-report.txt`, klucze `openapi-docs_*` w 6 językach (translator Gemini) i dokumentację w `docusaurus-hgdb`.
   Nowe DTO w `mercury-lib` oznaczają kolejne wydanie biblioteki.
7. **049, CMIS.** Szkic jest w produkcyjnym `web.xml` (serwlety Chemistry, repozytorium plikowe bez konfiguracji).
   Kroki: (a) wybór podzbioru metod pierwszej wersji (z listy 14 w opisie zadania),
   (b) wymiana repozytorium plikowego na repozytorium oparte o Mercury (typ „Folder”, `Case2Case`), (c) ochrona wszystkich ścieżek CMIS (obserwacja 87), (d) testy z klientem `mercury-cmis-client`.
8. **191, etap 1** (rewizja wersji, Java 8), potem **etap 2** (Java 17 i Lucene 9; przy okazji `DocValues` dla
   `*_subCaseIds`, rozważyć W3 część 2).

### Etap 3: kompletność programu i wydanie

9. **209, polecenie kalibracji** (`mercury-cmd`). Odpowiedzi na 6 pytań z `209-…/TASK.md`, potem implementacja; wariant po Lucene 9 (191), żeby nie portować kodu pomiarowego dwa razy (przypuszczenie).
10. **211, obrazy Docker i wydanie** (zwieńczenie). Łańcuch: wydanie `mercury` i `hgdb-client-open` → podbicie wersji w `mercury-cmd` i budowa pakietu instalacyjnego → wgranie pakietu na
    `hgdb.org/mercury-docker-packages` → aktualizacja `mercury-docker` (Dockerfile, kompozycje, Helm, README, konfiguracje) → test dymny → publikacja obrazów → artykuły o Docker i Kubernetes.
    Szczegóły i ryzyka: `211-Aktualizacja-obrazow-Docker-i-wydanie/TASK.md`. Warunek wejścia: zamknięte 058, 214, 016 (etapy 1–3), 049 i 191 albo świadomie odłożone (patrz ryzyko 7 w sekcji 4); 209 zamknięte.
    **Po 211:** autor stawia serwer testowy i zaczyna testować nowe funkcje.

### Poza planem

- 193, 195, 198, 208 i 215 („not now”) oraz zadanie dla SecurityProvidera (bez numeru).

## 4. Ocena ryzyk (z nierozwiązanych obserwacji)

Nie widzę przeszkody blokującej zakończenie 058 i 214. Warunki i ryzyka (źródło: `docs/obserwacje.md`):

1. **Obserwacja 107:** `OAuthFilter` zapisywał sekret klienta OAuth w dzienniku przy DEBUG; naprawione w 058 (2026-10-27). Zostają trzy stare linie w dzienniku serwera dev (decyzja autora).
2. **Obserwacja 102 (nowa):** SecurityProvider nie działa na stosie `sccommon` 2.0.0.1 i ehcache 3.6.1, a `hgdb-client-open` na nim zostaje. Klient `mercury-client` nie jest rozwijany, więc ryzyko dotyczy tylko wdrożeń BPM, w których oba produkty mają współistnieć z nową biblioteką.
3. **Numery wydań `mercury-lib`:** 3.0.4.17 jest wydaniem z `caseId` jako `String`. Wydanie 3.0.4.18 było rano błędne, ale autor wydał je ponownie (2026-10-27 wieczorem; „teraz jest OK”). Używają go `hgdb-client-open`, `mercury-cmd` i serwer dev. Ryzyko zamknięte.
4. **Obserwacja 103:** retencja logów spadła z 100 do 20 kopii (limit Logbacka); zmiana kontraktu konfiguracji opisana w nowej stronie dokumentacji.
5. **Obserwacja 105:** `mercury-transfer` przekazuje pusty zbiór `typeCodes`; wymaga testu między dwiema instancjami.
6. **Obserwacja 106:** generator OpenAPI wydłuża budowanie `mercury-ws-app` do ok. 4 min 15 s; nie blokuje.
7. **Zadanie 211 (wydanie, w planie):** obserwacje 7 (częściowo załatwiona: `mercury-cmd` ma podniesione wersje i buduje się), 32 (licencja próbna), 43 i 44 (zależności i dwa woodstoxy w pakiecie), 87 (endpointy CMIS; decyzja: zostają z testem albo wyłączone do czasu 049),
   88 (`/rest/**` w obrazach), 89 (sekrety przykładowe, `centos:8` po końcu wsparcia; decyzja o Javie 17 z 191 wpływa na bazę obrazu), 90 (przykłady parametrów Lucene), skrypt `06_igo_da_logger_case_id_varchar.sql` w instrukcji aktualizacji.
   Rekomendacja (przypuszczenie): nie blokować wydania na etapie 2 zadania 191, jeśli nie będzie gotowy; wydać na Javie 8 i Javę 17 w kolejnym wydaniu.
   Do instrukcji aktualizacji dochodzi też zmiana konfiguracji logowania z 214 (jary Logbacka, `logback.xml`, opcje JVM; patrz strona „Logging configuration” w `docusaurus-hgdb`).
8. **016 Widoki:** największa niewiadoma (2–3 tygodnie wg szacunku, bez rozpoznania; do tego 6 pytań do autora). Ograniczenie: etap 0 zaraz po etapie 1, a etap 4 (Iron Server) poza pierwszym wydaniem, jeśli czas się skurczy.

## 5. Zasady pracy (bez zmian)

- Dla każdego zadania gałąź `hgdb-NNN` w repozytoriach, których kod dotyka zadanie, zakładana z aktualnego `master` po pull i po potwierdzeniu merge'a poprzedniego zadania (wyjątek: 214 jest podzadaniem 58). Commity, push, PR i merge robi autor.
- Zmiana API w `mercury-lib` wymaga wydania biblioteki i podbicia wersji w `mercury` oraz `hgdb-client-open`.
- Po zmianie interfejsów `I*Action` i `I*ExtRest`: sprawdzić `openapi-doc-report.txt`, uzupełnić `openapi-docs_*`, tłumaczenia przekazać translatorowi Gemini.
- Nowe komponenty w pakiecie `org.mercury`. Dokumentacja po polsku, tylko weryfikowalne fakty.
- Upgrade u klienta wymienia cały serwer: bez okresów przejściowych i adapterów zgodności (stary mechanizm usuwamy w tej samej zmianie).

## 6. Uzupełnienie 2026-10-27

- **058:** REST z tokenem OAuth i panel z sesją (rola `mrc-sysadmin`), tłumaczenia OpenAPI w 6 językach, dokumentacja w `docusaurus-hgdb`. Test na Logbacku: 19 z 19 w `test-manualny.sh`; użytkownik `tester` (rola `mrc-user`, dodany do bazy dev) dostaje 403. Poprawka separatora zakresów OAuth (spacja i przecinek) i szablon konfiguracji `mrc-sysadmin` dla `/rest/service/**`.
- **214:** wariant A (Logback 1.2.13, Java 8) wykonany w `mercury-lib`, `mercury`, `hgdb-client-open`, `mercury-cmd` i `mercury-docker`; adapter log4j 1.x z 058 usunięty; `mercury-client` poza zakresem. Na serwerze dev: jary Logbacka i `log4j-over-slf4j`, `sccommon` 2.0.0.1, `poi-toolkit` 4.1.0.1, `ccrto-openapi` 2.0.0.1; `commons-logging` zastępuje `spring-jcl`. Nowa strona dokumentacji „Logging configuration (Logback)” (en i pl).
- **IBM BPM:** logowanie dostarcza BPM (własne `log4j.jar` i `slf4j-api`), więc kod po stronie BPM używa tylko API SLF4J; `mercury-client` i SecurityProvider współdzielą stos `sccommon`/ehcache w jednym katalogu BPM (obserwacja 102).
- **016 po decyzjach autora:** cztery bazy, uprawnienia jak dla spraw, wynik w modelu Iron POI Server (`IExcelData`), rozszerzenie istniejącego eksportu. Widoki typów (`T_<kod typu>`) trafiają do `CaseViewDefinition` (sprawdzone w kodzie).
