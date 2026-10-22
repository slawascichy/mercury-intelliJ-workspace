# [194] Tłumaczenie opisów w `@WSDLDocumentation` na angielski (tekst domyślny dokumentacji i WSDL)

> Zadanie wydzielone z [192 – Lokalizacja opisów specyfikacji](../192-Lokalizacja-opisow-specyfikacji-i-tekstow-stalych/TASK.md)
> (pytanie Q2 i decyzja D22 z zadania [133](../133-Swagger-implementacja/TASK.md)); decyzja autora z 2026-10-22: **odłożone na później**.
> Zadanie 192 nie zależy od tego zadania. Obecny stan (opisy po polsku, tłumaczenia w katalogach) autor uznał za wystarczający.

## Cel zadania
Zmienić tekst domyślny opisów usług, operacji i parametrów (adnotacje `@WSDLDocumentation` w `mercury-lib` i `mercury`) z polskiego na
angielski, tak aby:
- opisy w WSDL (`wsdl:documentation`) i dokumentacja OpenAPI bez wyboru języka były po angielsku,
- polskie opisy zostały tłumaczeniem w katalogu `pl` (już istnieje), a nie tekstem domyślnym,
- specyfikacja domyślna `openapi.json` była w całości po angielsku (także opisy schematów i pól, patrz ryzyko 3).

## Kontekst (stan na 2026-10-22, po zadaniu 192)

- Adnotacje `@WSDLDocumentation` mają **polski** tekst w stałym formacie: opis, `Parametry:`, `Zwraca:` (D12). Parser opisów
  (`WsdlDocumentationText`) rozpoznaje też nagłówki angielskie `Parameters:` i `Returns:`.
- Katalogi `META-INF/mercury/openapi-docs_<lang>.properties` mają tłumaczenia w 6 językach (pl, en, de, es, fr, ko): w
  `mercury-lib/mercury-ws-server-api` (3325 kluczy), `mercury-ws-app` (118, `I*ExtRest`) i `mercury-lucene-indexes-api` (57). Katalog `pl`
  to **poprawiona** wersja adnotacji (35 linii z literówkami), a adnotacje nadal mają stary tekst. Katalog `en` jest przetłumaczony
  z poprawionego `pl` (narzędzie `D:\workspace\git\localization-project`).
- Specyfikacja domyślna `openapi.json` powstaje bez katalogu języka: opisy operacji z adnotacji, opisy schematów i pól z Javadoc
  (`schema-docs.json`), teksty stałe z `OpenApiTexts` w języku `OpenApiTexts.DEFAULT_LANGUAGE` (dziś `"pl"`).
- `OpenApiDocsExtractor` (`mercury-lib/mercury-core`, `org.mercury.docs`) wyciągał opisy z adnotacji do katalogu (kierunek: adnotacje → katalog).
  To zadanie wymaga odwrotnego kierunku (katalog `en` → adnotacje).

## Zakres (propozycja do doprecyzowania przed realizacją)

1. **Narzędzie przenoszące tekst z katalogu `en` do adnotacji** (JavaParser, odwrotność `OpenApiDocsExtractor`): zamienia wartość
   `@WSDLDocumentation` na tekst z klucza `Interfejs`, `Interfejs.metoda` (opis, bloki `Parameters:` i `Returns:` złożone z kluczy
   `.param.<nazwa>` i `.returns`). Zachować formatowanie (konkatenacja literałów, długość linii) i pominąć metody bez wpisu.
   Dotyczy interfejsów `I*Action` w `mercury-ws-server-api`, `I*ExtRest` w `mercury-ws-app` i `ICaseIndexerFieldsManagerAction` w
   `mercury-lucene-indexes-api`.
2. **Javadoc interfejsów.** Rozstrzygnąć, czy Javadoc też tłumaczymy albo wyrównujemy do adnotacji (obserwacja 41: rozbieżności między
   Javadoc a adnotacją), skoro adnotacja jest jedynym trwałym źródłem opisów (D9).
3. **Specyfikacja domyślna po angielsku.** Wybrać sposób: generować `openapi.json` z katalogu `en` (jak `openapi_en.json`; wtedy opisy
   schematów i pól są angielskie) albo przetłumaczyć Javadoc encji i DTO w `mercury-entities`. Pierwsza opcja jest tańsza.
4. **Przełączenie języka domyślnego:** `OpenApiTexts.DEFAULT_LANGUAGE = "en"`, regeneracja `openapi.json` i `openapi_<lang>.json`,
   dostosowanie testów oczekujących polskich tekstów domyślnych.
5. **Wydanie `mercury-lib`** (kolejna wersja po 3.0.4.8) i podbicie zależności w `mercury`, `hgdb-client-open` i pozostałych
   repozytoriach; sprawdzenie `wsdl:documentation` w wygenerowanym WSDL.
6. **Dokumentacja:** `docs/moduly/mercury.md`, `docs/moduly/mercury-lib.md` (język domyślny, kierunek tłumaczeń).

## Ryzyka i pytania

1. **Zmiana WSDL.** Opisy trafiają do `wsdl:documentation` oraz do Javadoc klas generowanych z WSDL u klientów. To zmiana tylko
   dokumentacyjna (kontrakt WSDL bez zmian), ale widoczna dla klientów, więc wymaga uzgodnienia z wydaniem.
2. **Klucze `rest.<Interfejs>`** (opisy usług tylko dla REST, np. bez wariantów XML) pozostają potrzebne: adnotacja to opis dla SOAP
   (wspomina warianty XML). Sprawdzić, czy po zmianie nie zdublują się z adnotacją.
3. **Opisy schematów i pól** pochodzą z Javadoc encji (po polsku), więc samo przestawienie `DEFAULT_LANGUAGE` nie wystarczy, żeby
   `openapi.json` był angielski (zakres, punkt 3).
4. **Dryf terminologii przy ponownym tłumaczeniu.** Teksty angielskie trzeba brać z istniejącego katalogu `en`, a nie tłumaczyć od nowa
   (narzędzie przy pełnym ponownym tłumaczeniu zmieniało „catalog”→„directory”, „paged”→„paginated”). Przy poprawkach używać słownika
   `glossary_constants.json` (`terms.en`).
5. **Jakość tłumaczeń.** es, fr, ko są automatyczne bez przeglądu native speakera; angielski to język bazowy dla pozostałych, więc jego
   przegląd przed wpisaniem do adnotacji ma największy wpływ (przegląd techniczny i językowy `en`).
6. **Zapis zmiany w adnotacjach** zmienia wiele plików w `mercury-lib` (ok. 70 interfejsów); zrobić jednym commitem, żeby historia była czytelna.

## Do rozstrzygnięcia

| # | Pytanie | Uwagi |
|---|---|---|
| Q1 | Kiedy realizujemy? | Odłożone przez autora (2026-10-22). Wymaga uzgodnienia z wydaniem `mercury-lib` |
| Q2 | Czy tłumaczymy Javadoc interfejsów razem z adnotacjami? | Dziś adnotacja i Javadoc bywają rozbieżne (obserwacja 41) |
| Q3 | Specyfikacja domyślna: z katalogu `en` czy z przetłumaczonego Javadoc encji? | Zakres, punkt 3 |
| Q4 | Czy `en` przechodzi przegląd językowy przed wpisaniem do adnotacji? | Patrz ryzyko 5 |

## Definicja Gotowości (DoD)
- Adnotacje `@WSDLDocumentation` mają tekst angielski w `mercury-lib`, `mercury` (`I*ExtRest`) i `mercury-lucene-indexes-api`.
- `openapi.json` (domyślny) jest w całości po angielsku (opisy operacji, schematów i pól, teksty stałe), a `openapi_pl.json` zachowuje polski.
- Raport generatora: brakujące tłumaczenia 0, testy generatora i serwera przechodzą.
- WSDL zawiera angielskie `wsdl:documentation`, kontrakt (operacje, typy, nazwy parametrów) bez zmian.
- Wydanie `mercury-lib` z opisem zmiany; dokumentacja workspace zaktualizowana.

## Kluczowe Pliki w Projekcie

Ścieżki względne do `D:\workspace\git`.

- `mercury-lib/mercury-ws-server-api/src/main/java/` (adnotacje `@WSDLDocumentation`) i `.../resources/META-INF/mercury/openapi-docs_<lang>.properties`.
- `mercury-lib/mercury-core/src/main/java/org/mercury/docs/OpenApiDocsExtractor.java` (kierunek adnotacje → katalog).
- `mercury/mercury-ws-app/src/main/java/` (interfejsy `I*ExtRest`), `mercury/mercury-lucene-indexes-api/` (`ICaseIndexerFieldsManagerAction`).
- `mercury/mercury-ws-app-rest-generator/src/main/java/org/mercury/rest/server/generator/`: `OpenApiTexts.java` (`DEFAULT_LANGUAGE`),
  `OpenApiSpecBuilder.java`, `WsdlDocumentationText.java`.
- `tasks/hgdb/192-.../narzedzia/` (odświeżanie i scalanie katalogów), `D:\workspace\git\localization-project` (tłumacz).
