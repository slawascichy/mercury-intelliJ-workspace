# Plan najbliższych działań (2026-10-27, wersja 3)

Plan powstał po zamknięciu zadań 39, 119, 121 i 171 i uwzględnia decyzje autora z 2026-10-26 i 2026-10-27. Szacunki są orientacyjne (przypuszczenie), bo opierają się na opisach zadań
i krótkiej lekturze kodu, a nie na pełnym rozpoznaniu.

**Zmiany w wersji 3 (2026-10-27):** do przedwydaniowego pakietu dołączono zadanie **016 Widoki** (komplet funkcjonalności przed wydaniem), zadanie 169 dostało zakres
(`mercury-client`, poprawka cache, dokumentacja, `LoggerEvent.caseId`) i wymaga wydania `mercury-lib` 3.0.4.17, a 190 zostało rozpoczęte (zebrane fakty z kodu).

## 1. Decyzje autora (2026-10-26)

| # | Decyzja | Skutek                                                                                                     |
|---|---|------------------------------------------------------------------------------------------------------------|
| 1 | Kolejność faz A → B → C jest dobra | Plan poniżej; faza D (wydanie) jest ostatnia                                                               |
| 2 | Poprawić `HtmlControlUtils` (pozycja 7 zadania 190) | Zakres 190 rośnie o zmianę w `mercury` (zapisane w `190-…/TASK.md`)                                        |
| 3 | 058: tylko REST, SOAP niepotrzebny | Cele 058 zaktualizowane; usługa `I*ExtRest` w `mercury-ws-app`, bez zmian w `mercury-lib` (przypuszczenie) |
| 4 | 049: szkic oparty o repozytorium plikowe, sprawdzić `web.xml` | Stan szkicu opisany w `049-…/TASK.md`; obserwacja 87 (endpointy CMIS w WAR)                                |
| 5 | Pytania z 209 rozstrzygamy przy przejściu do 209 | Bez zmian                                                                                                  |
| 6 | Dodać zadanie obrazów Docker, zwieńczające pakiet zmian i wydanie | Zadanie `211-Aktualizacja-obrazow-Docker-i-wydanie` (faza D)                                               |
| 7 | 169: `mercury-client` migrujemy do `String` na `master` (gałąź `FH_INEA_UPGRADE_20200409` zachowuje `Long` dla INEA) | Zrobione (gałąź `hgdb-169`), build z `hgdb-client` 3.1.4.16 przechodzi |
| 8 | 169: `LoggerEvent.caseId` na `String`, skrypty tylko dla PostgreSQL | Zrobione w kodzie (`mercury-lib`, `mercury`); wymaga wydania `mercury-lib` 3.0.4.17 (robi autor) |
| 9 | Dokumentację 169 poprawiamy w `docusaurus-hgdb` na `main`; gałąź `hgdb-109` usunięta | Zrobione, commit wykonany przez autora |
| 10 | Zadanie 016 Widoki wchodzi do planu przed wydaniem (komplet funkcjonalności) | Faza B, etapy 0–4 (patrz niżej) |

## 2. Stan kolejki

| Zadanie | Status | Rozmiar (szac.) | Zależności i uwagi |
|---|---|---|---|
| 39, 119, 121, 171 | **zamknięte** (kod w `master`, `mercury-lib` 3.0.4.16) | – | Podsumowania w katalogach zadań |
| 169 Typ id sprawy `String` | **kod gotowy** (faza A), do zamknięcia po wydaniu | zrobione | Zostało: commity, wydanie `mercury-lib` 3.0.4.17, scalenie PR-ów, `openapi-doc-report.txt`. Odłożone do wydania: martwe `decode*` w `mercury-lib`, `IArchCase2SubCaseDAO`. Szczegóły: `169-…/audyt-2026-10-26.md` |
| 190 Dokumentacja metadanych typów | **w toku** (faza A) | 2–3 d | Zebrane fakty z kodu do pozycji 1–6 i 8; zostają 7 (`HtmlControlUtils`), 9, 10. Dokumentacja w `docusaurus-hgdb` plus poprawka `HtmlControlUtils` w `mercury` |
| 058 Logger: poziomy logowania (REST) | **nowe** (faza B) | 3–4 d | Backend logowania do ustalenia; panel w `mercury-ws-app` |
| 016 Widoki | **nowe** (faza B) | ok. 3 tyg. (przypuszczenie) | Etapy 0–4 w `016-Widoki/TASK.md`. Decyzje autora z 2026-10-27: cztery bazy (PostgreSQL, Oracle, MySQL, MSSQL), uprawnienia jak dla spraw, wynik w modelu Iron POI Server, rozszerzenie istniejącego eksportu, nowe DTO w `mercury-lib` (kolejne wydanie) |
| 214 Migracja logowania na Logback | **nowe** (faza B, po 058) | 3–5 d (przypuszczenie) | Decyzja autora 2026-10-27: wariant A, Logback 1.2.x (Java 8). Usuwa log4j 1.x i 2.x; POM-y `mercury-lib` zmieniają się, więc wejdzie do wydania biblioteki. Zadanie: `214-Migracja-logowania-na-Logback/TASK.md` |
| 209 Polecenie kalibracji (`mercury-cmd`) | szkic (faza B) | średnie | Pytania rozstrzygamy przy starcie |
| 191 Rewizja wersji i Java 17 | w kolejce (faza C) | etap 1: kilka dni; etap 2: duże | Zawiera Lucene 9 |
| 049 CMIS | **nowe** (faza C) | duże | Szkic wpięty w `web.xml`; patrz niżej |
| 211 Obrazy Docker i wydanie | **nowe** (faza D) | 3–5 d (przypuszczenie) | Zwieńczenie pakietu; zależy od wydań `mercury`, `hgdb-client-open`, `mercury-cmd` |
| 193, 198, 208 (Swagger UI; autor pisał „195”) | **not now** | – | Bez działań |

## 3. Kolejność

### Faza A: szybkie domknięcia (ok. 3–4 dni)

1. **169, audyt.** Pozostałości `Long` jako typu id sprawy w `mercury-lib`, `mercury`, `hgdb-client-open` i dokumentacji. Wynik: zamknięcie albo lista poprawek.
2. **190.** (a) Poprawka `HtmlControlUtils` w `mercury` (test jednostkowy), (b) dokumentacja metadanych według kodu (pozycje 1–10), (c) dokumentacja z 119: parametry `lucene.properties`,
   `truncated` i `totalHits`, błędy sortowania `L0009.7` i `L0009.8`.

### Faza B: funkcje (ok. 3–5 tygodni razem z 016)

3. **058, logger (REST).** (a) Ustalić aktywny backend logowania (`slf4j-reload4j` i `log4j-core` 2.17.2 jednocześnie), (b) usługa `I*ExtRest` w `mercury-ws-app`
   (pobranie poziomu, zmiana, wyszukiwanie z limitem 10–30), (c) panel w `mercury-ws-app`, (d) po zmianie API: `openapi-doc-report.txt`, klucze `openapi-docs_*`, tłumaczenia przez translator Gemini,
   (e) uprawnienia tylko dla administratora (przypuszczenie).
4. **016, widoki** (komplet funkcjonalności przed wydaniem). Etap 0 (rozpoznanie i koncepcja, 1–2 d) zaczynamy zaraz 
   po 058, bo od odpowiedzi autora na 6 pytań z `016-Widoki/TASK.md` zależy zakres. Potem etapy 1–3 (odczyt widoków w REST, odporność na widoki `INVALID` i blokady,
   wynik w JSON i Excelu), na końcu etap 4 (Iron Server), który można wydać osobno. Zmiana API oznacza `openapi-doc-report.txt`, klucze `openapi-docs_*` w 6 językach (translator Gemini) i dokumentację w `docusaurus-hgdb`.
   Jeśli pojawią się nowe DTO w `mercury-lib`, potrzebne będzie kolejne wydanie biblioteki przed fazą D.
5. **209.** Odpowiedzi na 6 pytań z `TASK.md`, potem implementacja (wariant: po Lucene 9, żeby nie portować kodu 
   pomiarowego dwa razy; przypuszczenie).

### Faza C: duże zmiany

6. **191, etap 1** (rewizja wersji, Java 8), potem **etap 2** (Java 17 i Lucene 9; przy okazji `DocValues` dla 
`*_subCaseIds`, rozważyć W3 część 2).
7. **049, CMIS.** Szkic jest w produkcyjnym `web.xml` (serwlety Chemistry, repozytorium plikowe bez konfiguracji). 
   Kroki: (a) wybór podzbioru metod pierwszej wersji (z listy 14 w opisie zadania),
   (b) wymiana repozytorium plikowego na repozytorium oparte o Mercury (typ „Folder”, `Case2Case`), (c) ochrona wszystkich ścieżek CMIS (obserwacja 87), (d) testy z klientem `mercury-cmis-client`.

### Faza D: wydanie (po fazach A–C, zadanie obrazów Docker)

8. **211, obrazy Docker i wydanie.** Łańcuch: wydanie `mercury` i `hgdb-client-open` → podbicie wersji w 
   `mercury-cmd` i budowa pakietu instalacyjnego → wgranie pakietu na `hgdb.org/mercury-docker-packages`
   → aktualizacja `mercury-docker` (Dockerfile, kompozycje, Helm, README, konfiguracje) → test dymny → publikacja obrazów → artykuły o Docker i Kubernetes.
   Szczegóły i ryzyka: `211-Aktualizacja-obrazow-Docker-i-wydanie/TASK.md`.
   Warunek wejścia do fazy D: zamknięte 169, 190, 058 i 016 (etapy 1–3), zadania z fazy C zamknięte albo świadomie odłożone (patrz ryzyko 6).

## 4. Ocena ryzyk dla wydania (z nierozwiązanych obserwacji)

Nie widzę przeszkody blokującej wydanie. Są jednak warunki, które trzeba spełnić przed publikacją obrazów (źródło: `docs/obserwacje.md`):

1. **Obserwacja 7:** `mercury-cmd` buduje się z wydanymi, starszymi wersjami serwera (3.0.3.2.12), więc bez podbicia wersji pakiet instalacyjny i obrazy nie zawierałyby zmian z 119.
   To warunek wstępny zadania Docker, nie jego opcja.
2. **Obserwacja 88 (nowa, dopełnia 35):** obrazy chronią nadal `/rest/**`, więc `/rest/openapi.json` byłby niedostępny bez tokenu; zmiana wzorca z zadania 133 objęła tylko `mercury`.
3. **Obserwacje 43 i 44:** zależności zewnętrzne i dwa woodstoxy w pakiecie. Obrazy i pakiet `mercury-cmd` nie były sprawdzane, więc potrzebny jest test dymny.
4. **Obserwacja 87 (nowa):** endpointy CMIS w `web.xml` z częścią ścieżek bez ochrony. Decyzja przed wydaniem: zostają (z testem) albo wyłączone do czasu 049.
5. **Obserwacja 32 (licencja próbna):** start jedno- i wielowęzłowy trzeba sprawdzić na nowej wersji.
6. **Obserwacja 89 (nowa):** domyślne sekrety przykładowe i podstawa obrazu `centos:8` po końcu wsparcia; decyzja o Javie 17 (191) wpływa na bazę obrazu.
   Rekomendacja (przypuszczenie): nie blokować wydania na etapie 2 zadania 191, jeśli nie będzie gotowy; wydać na Javie 8 i Javę 17 w kolejnym wydaniu.
7. Pozostałe z 119: przegląd tłumaczeń ko, ponowne wygenerowanie `openapi-doc-report.txt`, ręczny test przebudowy indeksu na Windows z pulą czytników, przykłady parametrów w pakiecie `mercury-cmd` i obrazie (obserwacja 90).
8. **016 Widoki (nowe, 2026-10-27):** największa niewiadoma pakietu (2–3 tygodnie wg szacunku, bez rozpoznania; do tego 6 pytań do autora). Rośnie ryzyko opóźnienia wydania i dodatkowego wydania `mercury-lib`. Ograniczenie: etap 0 zaraz po 058, a etap 4 (Iron Server) poza pierwszym wydaniem, jeśli czas się skurczy.
9. **169, wydanie `mercury-lib` 3.0.4.17:** zmiana `LoggerEvent.caseId` wymaga skryptu `06_igo_da_logger_case_id_varchar.sql` na istniejących bazach PostgreSQL. Skrypt trzeba dołączyć do instrukcji aktualizacji w zadaniu 211.

## 5. Zasady pracy (bez zmian)

- Dla każdego zadania gałąź `hgdb-NNN` w repozytoriach, których kod dotyka zadanie, zakładana z aktualnego `master` po pull. Commity, push, PR i merge robi autor.
- Zmiana API w `mercury-lib` wymaga wydania biblioteki i podbicia wersji w `mercury` oraz `hgdb-client-open` (jak 3.0.4.16 w 119).
- Po zmianie interfejsów `I*Action` i `I*ExtRest`: sprawdzić `openapi-doc-report.txt`, uzupełnić `openapi-docs_*`, tłumaczenia przekazać translatorowi Gemini.
- Nowe komponenty w pakiecie `org.mercury`. Dokumentacja po polsku, tylko weryfikowalne fakty.

## 6. Uzupełnienie 2026-10-27

- **Wydania `mercury-lib`:** 3.0.4.17 jest wydaniem z `LoggerEvent.caseId` jako `String`. Wydanie 3.0.4.18 jest błędne (afected) i nie jest używane; autor poprawi je przy następnym wydaniu biblioteki.
  Kolejne wydanie `mercury-lib` będzie potrzebne dla 016 (nowe DTO), więc przy nim warto naprawić 3.0.4.18.
- **016 po decyzjach autora:** cztery bazy, uprawnienia jak dla spraw, wynik w modelu Iron POI Server (`IExcelData`), rozszerzenie istniejącego eksportu. Widoki typów (`T_<kod typu>`) trafiają do `CaseViewDefinition` (sprawdzone w kodzie).
  Szczegóły: `016-Widoki/TASK.md` (sekcja „Decyzje autora”).
- **Logowanie (2026-10-27):** na serwerze działa log4j 1.2.14 z `slf4j-log4j12` (jary w `mercury-server/apache-tomcat/mercury/lib`), a POM-y wskazują różne bindingi. Autor wybrał wariant A (Logback 1.2.x, Java 8).
  Zadanie `214-Migracja-logowania-na-Logback` wchodzi do fazy B po 058 i przed fazą D (pakiet i obrazy muszą zawierać nowy backend). Usługa z 058 ma adaptery dla Logbacka i log4j 1.x, więc nie czeka na migrację.
