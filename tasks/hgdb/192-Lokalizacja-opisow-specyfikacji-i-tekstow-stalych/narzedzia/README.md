# Narzędzia do katalogów tłumaczeń OpenAPI (zadanie 192)

Katalogi `openapi-docs_<lang>.properties` modułu generatora (`mercury/mercury-ws-app-rest-generator/src/main/resources/META-INF/mercury`)
zawierają klucze `openapi.*` (teksty stałe), `ui.types.*` (strona wyboru typu) i `schema.*` (opisy schematów i pól z Javadoc encji).
Opisy operacji z `@WSDLDocumentation` mają osobne katalogi w `mercury-lib` i `mercury-ws-app` (tworzy je `OpenApiDocsExtractor`).

| Plik | Zastosowanie |
|---|---|
| `extract_schema_keys.py` | wyciąga klucze `schema.*` z `openapi_pl.json` do pliku `.properties` |
| `merge_catalogs.py` | scala pliki źródłowe z katalogami języków (dopisanie albo zastąpienie grupy kluczy) |

Tłumaczy narzędzie `D:\workspace\git\localization-project` (`localizer.py`), nie człowiek ani asystent.

## Odświeżenie opisów schematów po zmianie Javadoc encji

Javadoc jest źródłem prawdy dla polskich opisów (`schema-docs.json`, tworzony przy budowie modułów `mercury-lib`). Po jego zmianie:

1. Zbuduj `mercury-lib` i zainstaluj artefakty, a w `mercury` uruchom generator, który odświeży `openapi.json`. Specyfikacja domyślna jest
   budowana bez katalogu języka, więc zawiera opisy prosto z Javadoc (i polskie teksty stałe, dopóki `OpenApiTexts.DEFAULT_LANGUAGE = "pl"`).
   Gdy `DEFAULT_LANGUAGE` zostanie zmieniony na `en`, `openapi.json` będzie angielski i nie nadaje się jako źródło. Wtedy tymczasowo usuń
   z katalogu `pl` klucze `schema.*` i użyj `openapi_pl.json` (bez kluczy generator bierze opisy z Javadoc).
2. `python extract_schema_keys.py mercury-ws-app/src/main/resources/openapi/openapi.json pl_schema.properties`
3. Tłumaczenie (pl → en, potem en → pozostałe), słownik `glossary_constants.json`:

   ```
   localizer.py --glossary glossary_constants.json translate --input pl_schema.properties --src pl --target en --outdir OUT --cache cache_en.json
   localizer.py --glossary glossary_constants.json translate --input OUT/openapi-docs_en.properties --src en --target de es fr ko --outdir OUT2 --cache cache_other.json
   localizer.py validate --source OUT/openapi-docs_en.properties --target OUT2/openapi-docs_de.properties OUT2/openapi-docs_es.properties ...
   ```
   Pamięć podręczna (`--cache`) sprawia, że tłumaczone są tylko zmienione teksty.
4. `python merge_catalogs.py mercury/mercury-ws-app-rest-generator/src/main/resources/META-INF/mercury --replace-prefix schema. pl=pl_schema.properties en=OUT/openapi-docs_en.properties de=OUT2/openapi-docs_de.properties es=... fr=... ko=...`
5. Zbuduj generator, sprawdź raport (`mercury-ws-app-rest-generator/target/openapi-doc-report.txt`: brakujące tłumaczenia 0), uruchom testy
   i przejrzyj `git diff` plików `openapi_*.json`.

Sprawdzian poprawności: po kroku 2 w repozytorium z aktualnymi katalogami plik `pl_schema.properties` powinien być identyczny z liniami `schema.*`
katalogu `pl` (to znaczy, że katalog `pl` odtwarza Javadoc).
