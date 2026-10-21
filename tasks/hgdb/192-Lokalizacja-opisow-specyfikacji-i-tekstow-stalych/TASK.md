# [192] Lokalizacja opisów specyfikacji statycznej, tekstów stałych i stron dokumentacji Swagger

> Zadanie wydzielone z [133 – Swagger](../133-Swagger-implementacja/TASK.md) (decyzja D22, 2026-10-20).
> Zadanie 133 nie zależy od tego zadania. Zakres rozszerzono o strony dokumentacji Swagger na prośbę autora.

## Cel zadania
Udostępnić dokumentację Swagger (OpenAPI) w wielu językach: nie tylko opisy w specyfikacjach, ale też teksty
stałe generowane przez kod, własne strony (`types.html`) i, w miarę możliwości, interfejs samego Swagger UI.
Tekstem domyślnym jest angielski, pierwszym katalogiem tłumaczeń polski.

## Podział na etapy

| Etap | Zakres | Uwagi |
|---|---|---|
| 1 | Opisy specyfikacji statycznej (etap 1 zadania 133, `@WSDLDocumentation`) | Katalog `openapi-docs_<lang>.properties` w `mercury-lib` |
| 2 | Teksty stałe generowane przez kod w specyfikacji per typ (etap 2 zadania 133) | Operacje, koperty i parametry w `CaseTypeOperations` i pokrewnych, tytuł specyfikacji (dziś „Typ sprawy …”) |
| 3 | Własne strony `swagger-ui-config` (`types.html`, strona wejściowa) | Słownik tekstów w JS, wybór języka jak w specyfikacji |
| 4 | Interfejs Swagger UI („Try it out”, „Execute”, „Parameters”, filtr itd.) | Najbardziej ryzykowny, robić na końcu, pokrycie „najlepsze możliwe” |

## Kontekst i Wymagania

### Decyzje z zadania 133 (D22)
- `@WSDLDocumentation` zostaje angielskim tekstem domyślnym, więc WSDL nie niesie kluczy.
- Tłumaczenia: `openapi-docs_<lang>.properties` w `mercury-lib`, klucze stabilne
  (np. `ICaseBusinessExtRest.save`, `ICaseBusinessExtRest.save.param.arg0`), pierwszy katalog `pl`.
- Generator etapu 1 wybiera tekst z katalogu danego języka, a gdy go brak, z adnotacji. Tworzy plik na język,
  `/rest/openapi.json?lang=` wybiera plik.
- Raport braków wypisuje też brakujące tłumaczenia.
- Etap 2 (specyfikacje per typ) zostaje przy kluczach `${…}` rozwiązywanych przez `IResourceLogic.getMessage`.
  Teksty stałe z kodu przenosi się do tego samego mechanizmu.
- Dotychczasowe polskie opisy w adnotacjach trzeba przetłumaczyć na angielski, a polskie wersje przenieść do katalogu `pl`.
  **Zmieni to opisy w WSDL.**

### Wybór języka (stan po zadaniu 133, krok 6)
- API specyfikacji: dziś `?lang=` (pl, en-GB, en_GB; wartość błędna jest ignorowana), potem `Accept-Language`,
  potem język systemu. **Ustalenie z 2026-10-20:** w `/rest/openapi.json` i w specyfikacji typu parametrem głównym ma być
  `?l=`, a `?lang=` jego aliasem (jak na stronach). Kolejność bez zmian. **Zrobione 2026-10-21** (`OpenApiLanguage`, `OpenApiController`, `CaseTypeOpenApiController`), nie sprawdzone na serwerze.
- Strony `types.html` i `index.html`: parametr `?l=` (jak na stronie głównej i liście usług REST), alias `?lang=`.
  Wartość trafia do adresu specyfikacji typu. Pełna specyfikacja statyczna na razie ignoruje język.
- Aktualne języki zasobów: pl, en, de, es, fr, ko.

### Język specyfikacji domyślnej (decyzja autora 2026-10-21)
- Do czasu przetłumaczenia opisów w `@WSDLDocumentation` (Q2, krok 6 planu) domyślny `openapi.json` (bez wyboru języka) jest **po polsku**,
  tak jak adnotacje, a nie angielski jak zakładała D22. Teksty stałe generatora i serwera w specyfikacji domyślnej też są polskie.
  Zapas dla brakującego klucza w danym języku zostaje angielski.
- Jedno miejsce przełączenia: `OpenApiTexts.DEFAULT_LANGUAGE` (`mercury-ws-app-rest-generator`). Po przetłumaczeniu adnotacji
  zmienić na `"en"` i zregenerować specyfikacje.

### Kodowanie plików `*.properties`
- `\uXXXX` stosujemy tam, gdzie konieczne. `WebAppMsg_*` jest w `\u` (inaczej strona główna pokazuje `Ã¼`).
- `resources_*`, `LuceneErrorMsg_*`, `LuceneFieldsLabels_*` i `ClusterErrorMsg_*` są w UTF-8 (surowe znaki).
- Dla nowych plików `openapi-docs_<lang>.properties` trzeba zdecydować i sprawdzić sposób ładowania (do ustalenia w etapie 1).

### Interfejs Swagger UI (etap 4)
Z tego, co wiadomo, Swagger UI nie ma oficjalnej obsługi wielu języków. **Do potwierdzenia na początku etapu** w wersji
webjara używanej w projekcie. Dwa warianty:
- plugin Swagger UI (`wrapComponents`): czysty, ale pokrywa tylko to, co plugin obejmie, i zależy od wersji UI,
- warstwa tłumacząca DOM (słownik i `MutationObserver`) w `swagger-ui-config`: prosta, ale krucha przy aktualizacji UI
  i niepełna.

## Status zadania

| Obszar | Zakres | Stan |
|---|---|---|
| Etap 1 | Opisy specyfikacji statycznej | 🟡 w toku: katalogi pl, en, de, generator i serwer (wybór języka `l`/`lang`) zatwierdzone, testy 112/112. Zostaje wydanie `mercury-lib`, regeneracja plików `openapi_<lang>.json` i sprawdzenie na serwerze. [Podsumowanie 2026-10-20](podsumowanie-2026-10-20.md), [2026-10-21](podsumowanie-2026-10-21.md) |
| Etap 2 | Teksty stałe specyfikacji per typ | 🟡 kod gotowy 2026-10-21 (`OpenApiTexts`, 44 klucze `openapi.*` w 6 językach, teksty generatora i serwera), testy 114/114, niezatwierdzone i niesprawdzone na serwerze. Opisy schematów i pól z Javadoc też w katalogach (klucze `schema.*`, 2659 kluczy na język, krok 3 z 2026-10-21). Zostaje sprawdzenie na serwerze, wydanie i decyzja Q2 (adnotacje) |
| Etap 3 | Własne strony `swagger-ui-config` | ⬜ nie rozpoczęto |
| Etap 4 | Interfejs Swagger UI | ⬜ nie rozpoczęto |

## Tłumaczenia: sposób pracy (od 2026-10-21)

Tłumaczy projekt autora `D:\workspace\git\localization-project` (`localizer.py`, Gemini, klucz w `.env`), a nie asystent.
Asystent zarządza plikami `openapi-docs_<lang>.properties` i przekazuje je do narzędzia. Polecenia: `translate` (nowe języki z `en`),
`review` (przegląd istniejącego tłumaczenia, raport zmian), `validate` (klucze, zmienne, polskie znaki, hangul). Narzędzie tłumaczy
unikalne wartości (714 na 3443 klucze), ma pamięć podręczną (wznowienie po przerwie, np. po wyczerpaniu limitu API) i słownik
`glossary.json` (`Case`, `TypeCase` bez tłumaczenia, terminologia `de`). Opis użycia: README projektu tłumacza.

## Do rozstrzygnięcia

| # | Pytanie | Uwagi |
|---|---|---|
| Q1 | Które języki obejmuje pierwsze wydanie tłumaczeń? | Zrobione pl, en, de (2026-10-20) oraz es, fr, ko (2026-10-21, tłumaczenie automatyczne z `en` przez narzędzie `D:\workspace\git\localization-project`, kontrola techniczna `validate` bez błędów; **bez przeglądu native speakera**). `de` przejrzane tym samym narzędziem (57 unikalnych poprawek w `mercury-lib`, 22 w `mercury`; odrzucone: „beliebig” → „verfügbar” i niespójne „Behandlung” → „Verwaltung”/„Verarbeitung”) |
| Q2 | Czy tłumaczymy opisy w WSDL (zmiana tekstów adnotacji)? | Wynika z D22, wymaga uzgodnienia z wydaniem |
| Q3 | Wariant dla interfejsu Swagger UI (plugin czy warstwa DOM)? | Rozstrzygnąć po sprawdzeniu wersji webjara |

## Definicja Gotowości (DoD)
- Etapy 1–3 zrealizowane i sprawdzone w pl i en oraz w co najmniej jednym kolejnym języku.
- Etap 4: wybrany wariant, zakres pokrycia opisany, brakujące teksty wymienione.
- Raport generatora wypisuje brakujące tłumaczenia.
- Dokumentacja workspace zaktualizowana (`docs/moduly/mercury.md`, `docs/moduly/mercury-lib.md`).

## Kluczowe Pliki w Projekcie

Ścieżki względne do `D:\workspace\git`.

- `mercury/mercury-ws-app/src/main/java/org/mercury/rest/server/actions/`: `CaseTypeLocalizer.java`,
  `CaseTypeOpenApiController.java` (`resolveLocale`), `CaseTypeOpenApiService.java`, `CaseTypeOperations` i pokrewne.
- `mercury/mercury-ws-app/src/main/webapp/swagger-ui-config/`: `types.html`, `swagger-initializer.js`.
- `mercury/mercury-ws-app-rest-generator/`: generator specyfikacji statycznej i raport braków.
- `mercury/mercury-ws-app/src/main/resources/textmessages/WebAppMsg_*.properties`.
- `mercury-lib`: adnotacja `@WSDLDocumentation` i miejsce katalogu `openapi-docs_<lang>.properties`.
