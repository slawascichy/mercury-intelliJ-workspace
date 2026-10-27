# [208] Lokalizacja tekstów interfejsu Swagger UI (etap 4 zadania 192)

**Status (2026-10-27):** **not now** (decyzja autora, 2026-10-27); bez działań.

> Zadanie wydzielone z [192 – Lokalizacja opisów specyfikacji](../192-Lokalizacja-opisow-specyfikacji-i-tekstow-stalych/TASK.md)
> (etap 4 i pytanie Q3); decyzja autora z 2026-10-22: **odłożone, niepilne**. Zadanie 192 nie zależy od tego zadania.
> Brak tłumaczenia napisów samego Swagger UI nie zmienia ogólnego wrażenia z nowych funkcji: opisy operacji, schematów, tekstów stałych
> i strony `index.html` / `types.html` są już w 6 językach.

## Cel zadania
Napisy wbudowane w Swagger UI (np. „Execute”, „Authorize”, „Parameters”, „Responses”, „Request body”, „Filter by tag”) mają być
wyświetlane w języku wybranym parametrem `l` / `lang` strony `index.html`, tak jak opisy specyfikacji (pl, en, de, es, fr, ko).

## Ustalenia z rozpoznania (2026-10-22)

- Wersja webjara: `org.webjars:swagger-ui` **5.32.0** (`mercury-ws-app/pom.xml`, właściwość `swagger-ui.version`).
- `swagger-ui-bundle.js` 5.32.0 **nie ma obsługi wielu języków**: brak `i18n`, `getLocale` i odczytu języka przeglądarki. Napisy są wpisane
  na stałe w komponentach React (zweryfikowane wyszukiwaniem w bundlu: m.in. „Execute”, „Authorize”, „Parameters”, „Responses”,
  „Request body”, „Filter by tag”, „No parameters”, „Server response”, „Example Value”).
- Własna konfiguracja leży w `mercury-ws-app/src/main/webapp/swagger-ui-config/` (`swagger-initializer.js`, `types.html`). Język strony jest
  tam już rozpoznawany (`specUrl()`: `l`, `lang`).

## Warianty (Q3)

| Wariant | Zalety | Wady |
|---|---|---|
| Plugin `wrapComponents` | Czysty mechanizm Swagger UI | Podmienia komponent w całości; do tłumaczenia pojedynczych napisów trzeba przepisywać wiele komponentów (operacje, parametry, odpowiedzi, autoryzacja) i powtarzać to po aktualizacji UI |
| Warstwa DOM (słownik + `MutationObserver`) | Obejmuje wszystko, co UI wyświetla; bez zmian w komponentach; mały kod | Krucha przy zmianie wersji webjara (napisy mogą przestać pasować); wymaga ostrożności, żeby nie tłumaczyć treści specyfikacji ani odpowiedzi |

**Rekomendacja (propozycja asystenta, niezatwierdzona):** warstwa DOM. Wersja webjara jest przypięta, więc kruchość dotyczy tylko świadomej
aktualizacji. Teksty z katalogu `ui.swagger.*` w 6 językach, podobnie jak `ui.types.*`.

## Zakres (po zatwierdzeniu wariantu)

1. Wypisać faktyczne napisy UI z bundla i ze strony; podzielić na „tłumaczymy” i „zostaje” (kody odpowiedzi, treści z serwera, nazwy metod HTTP).
2. Dodać klucze `ui.swagger.*` do katalogów `openapi-docs_<lang>.properties` modułu generatora (pl ręcznie, en i pozostałe przez
   `D:\workspace\git\localization-project`, `validate`) i udostępnić je stronie (endpoint jak `/rest/openapi/ui/types.json` albo plik).
3. Warstwa tłumacząca w `swagger-initializer.js` (język z `l` / `lang`, zapas: angielski, czyli oryginał UI).
4. Test w przeglądarce w pl, en i jednym kolejnym języku; dopisanie do `docs/moduly/mercury.md`.

## Do rozstrzygnięcia

| # | Pytanie | Uwagi |
|---|---|---|
| Q1 | Który wariant: plugin czy warstwa DOM? | Rekomendacja: warstwa DOM (dawne Q3 z zadania 192) |
| Q2 | Czy przy aktualizacji webjara dodać kontrolę kompletności słownika (lista napisów z bundla)? | Zmniejsza kruchość wariantu DOM |

## Definicja Gotowości (DoD)
- Wybrany wariant, zakres pokrycia opisany, napisy bez tłumaczenia wymienione.
- Napisy interfejsu zmieniają język razem z parametrem `l` / `lang` w 6 językach; sprawdzone w przeglądarce.
- Dokumentacja workspace zaktualizowana (`docs/moduly/mercury.md`).
