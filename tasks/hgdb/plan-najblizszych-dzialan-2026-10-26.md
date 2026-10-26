# Plan najbliższych działań (2026-10-26, wersja 2)

Plan powstał po zamknięciu zadań 39, 119, 121 i 171 i uwzględnia decyzje autora z 2026-10-26. Szacunki są orientacyjne (przypuszczenie), bo opierają się na opisach zadań
i krótkiej lekturze kodu, a nie na pełnym rozpoznaniu.

## 1. Decyzje autora (2026-10-26)

| # | Decyzja | Skutek |
|---|---|---|
| 1 | Kolejność faz A → B → C jest dobra | Plan poniżej; faza D (wydanie) jest ostatnia |
| 2 | Poprawić `HtmlControlUtils` (pozycja 7 zadania 190) | Zakres 190 rośnie o zmianę w `mercury` (zapisane w `190-…/TASK.md`) |
| 3 | 058: tylko REST, SOAP niepotrzebny | Cele 058 zaktualizowane; usługa `I*ExtRest` w `mercury-ws-app`, bez zmian w `mercury-lib` (przypuszczenie) |
| 4 | 049: szkic oparty o repozytorium plikowe, sprawdzić `web.xml` | Stan szkicu opisany w `049-…/TASK.md`; obserwacja 87 (endpointy CMIS w WAR) |
| 5 | Pytania z 209 rozstrzygamy przy przejściu do 209 | Bez zmian |
| 6 | Dodać zadanie obrazów Docker, zwieńczające pakiet zmian i wydanie | Zadanie `XXX-Aktualizacja-obrazow-Docker-i-wydanie` (faza D) |

## 2. Stan kolejki

| Zadanie | Status | Rozmiar (szac.) | Zależności i uwagi |
|---|---|---|---|
| 39, 119, 121, 171 | **zamknięte** (kod w `master`, `mercury-lib` 3.0.4.16) | – | Podsumowania w katalogach zadań |
| 169 Typ id sprawy `String` | w kolejce (faza A) | 0,5–1 d (audyt) | Część poprawek zrobiona w 119 |
| 190 Dokumentacja metadanych typów | w kolejce (faza A) | 2–3 d | Dokumentacja w `docusaurus-hgdb` plus poprawka `HtmlControlUtils` w `mercury` |
| 058 Logger: poziomy logowania (REST) | **nowe** (faza B) | 3–4 d | Backend logowania do ustalenia; panel w `mercury-ws-app` |
| 209 Polecenie kalibracji (`mercury-cmd`) | szkic (faza B) | średnie | Pytania rozstrzygamy przy starcie |
| 191 Rewizja wersji i Java 17 | w kolejce (faza C) | etap 1: kilka dni; etap 2: duże | Zawiera Lucene 9 |
| 049 CMIS | **nowe** (faza C) | duże | Szkic wpięty w `web.xml`; patrz niżej |
| XXX Obrazy Docker i wydanie | **nowe** (faza D) | 3–5 d (przypuszczenie) | Zwieńczenie pakietu; zależy od wydań `mercury`, `hgdb-client-open`, `mercury-cmd` |
| 193, 198, 208 (Swagger UI; autor pisał „195”) | **not now** | – | Bez działań |

## 3. Kolejność

### Faza A: szybkie domknięcia (ok. 3–4 dni)

1. **169, audyt.** Pozostałości `Long` jako typu id sprawy w `mercury-lib`, `mercury`, `hgdb-client-open` i dokumentacji. Wynik: zamknięcie albo lista poprawek.
2. **190.** (a) Poprawka `HtmlControlUtils` w `mercury` (test jednostkowy), (b) dokumentacja metadanych według kodu (pozycje 1–10), (c) dokumentacja z 119: parametry `lucene.properties`,
   `truncated` i `totalHits`, błędy sortowania `L0009.7` i `L0009.8`.

### Faza B: funkcje (ok. 1–2 tygodni)

3. **058, logger (REST).** (a) Ustalić aktywny backend logowania (`slf4j-reload4j` i `log4j-core` 2.17.2 jednocześnie), (b) usługa `I*ExtRest` w `mercury-ws-app`
   (pobranie poziomu, zmiana, wyszukiwanie z limitem 10–30), (c) panel w `mercury-ws-app`, (d) po zmianie API: `openapi-doc-report.txt`, klucze `openapi-docs_*`, tłumaczenia przez translator Gemini,
   (e) uprawnienia tylko dla administratora (przypuszczenie).
4. **209.** Odpowiedzi na 6 pytań z `TASK.md`, potem implementacja (wariant: po Lucene 9, żeby nie portować kodu pomiarowego dwa razy; przypuszczenie).

### Faza C: duże zmiany

5. **191, etap 1** (rewizja wersji, Java 8), potem **etap 2** (Java 17 i Lucene 9; przy okazji `DocValues` dla `*_subCaseIds`, rozważyć W3 część 2).
6. **049, CMIS.** Szkic jest w produkcyjnym `web.xml` (serwlety Chemistry, repozytorium plikowe bez konfiguracji). Kroki: (a) wybór podzbioru metod pierwszej wersji (z listy 14 w opisie zadania),
   (b) wymiana repozytorium plikowego na repozytorium oparte o Mercury (typ „Folder”, `Case2Case`), (c) ochrona wszystkich ścieżek CMIS (obserwacja 87), (d) testy z klientem `mercury-cmis-client`.

### Faza D: wydanie (po fazach A–C, zadanie obrazów Docker)

7. **XXX, obrazy Docker i wydanie.** Łańcuch: wydanie `mercury` i `hgdb-client-open` → podbicie wersji w `mercury-cmd` i budowa pakietu instalacyjnego → wgranie pakietu na `hgdb.org/mercury-docker-packages`
   → aktualizacja `mercury-docker` (Dockerfile, kompozycje, Helm, README, konfiguracje) → test dymny → publikacja obrazów → artykuły o Docker i Kubernetes.
   Szczegóły i ryzyka: `XXX-Aktualizacja-obrazow-Docker-i-wydanie/TASK.md`.

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

## 5. Zasady pracy (bez zmian)

- Dla każdego zadania gałąź `hgdb-NNN` w repozytoriach, których kod dotyka zadanie, zakładana z aktualnego `master` po pull. Commity, push, PR i merge robi autor.
- Zmiana API w `mercury-lib` wymaga wydania biblioteki i podbicia wersji w `mercury` oraz `hgdb-client-open` (jak 3.0.4.16 w 119).
- Po zmianie interfejsów `I*Action` i `I*ExtRest`: sprawdzić `openapi-doc-report.txt`, uzupełnić `openapi-docs_*`, tłumaczenia przekazać translatorowi Gemini.
- Nowe komponenty w pakiecie `org.mercury`. Dokumentacja po polsku, tylko weryfikowalne fakty.
