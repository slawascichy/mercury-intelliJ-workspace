# Generator artykułów „Licencje” (docusaurus)

Narzędzia, które budują katalog `003_Licenses` w `scisoftware-webpage/docusaurus-hgdb` (`tech/` dla angielskiego, `i18n/pl/docusaurus-plugin-content-docs-tech/current/` dla polskiego).
Skrypty są w Pythonie 3 (`python -I`), bez zależności zewnętrznych. Ścieżki do wydania i do `.m2` są stałymi na początku skryptów (dla tego wydania: `3.0.4.45`).

Kolejność przy nowym wydaniu (np. 3.0.5.x):

1. `gen_server.py <plik.csv>`: inwentarz jarów pakietu instalacyjnego (`lib`, `libExt`, `lib20`, `jdbcdrivers`, jary w WAR) z licencjami odczytanymi z POM w `D:\workspace\.m2\repository`
   (z łańcucha POM-ów rodziców; `libs.csv`). `gen_poi.py <plik.csv>`: to samo dla katalogu `lib` wydania `poi-toolkit` (`poi_libs.csv`). Zmień stałą `REL` na nowy katalog wydania.
2. `docx2mdx.py <plik.docx> [początek] [koniec]`: konwersja dokumentów licencyjnych z `Y:\SciSoftware\Licencje` na MDX z zachowaniem numeracji (`owlk_en.mdx.txt`,
   `owlk_pl.mdx.txt` z `...v1.0-en.docx` i `...v1.0.docx`; `annex2_pl.mdx.txt` z `...zal_2.docx` od początku do nagłówka „Zależności bezpośrednie Iron POI Serwera”).
3. `build.py <katalog>`: składa artykuły (angielski w `<katalog>`, polski w `<katalog>_pl`). Edytuj tam stałe `RELEASE`, `POI_VERSION`, `ASOF`, tabele `TOOLS` i `WEBLIBS` (wersje
   Tomcata, Temurina, PostgreSQL itd. z Dockerfile'i `mercury-docker` i wersje bibliotek WWW z banerów w plikach) oraz słownik `OVERRIDE` (licencje, których POM nie podaje).
4. `node chk-mdx.mjs <katalog>/003_Licenses`: sprawdza, że pliki kompilują się jako MDX (`@mdx-js/mdx` z `node_modules` projektu docusaurus; zmień ścieżkę w imporcie).
5. Skopiuj wynik do projektu docusaurus (bez `index.mdx`; kategoria jest w `tech/003_Licenses/_category_.json`, tłumaczenie etykiety w `current.json`) i zbuduj stronę (`npx docusaurus build`).

Uwagi:
- Licencje własnych komponentów (`mercury-*`, `hgdb-*`, `poi-toolkit`) są pomijane w tabelach (podlegają OWLK i licencji klienta HgDB).
- Teksty OWLK i załączników są konwertowane wiernie z dokumentów Worda; nie tłumaczymy ich ani nie poprawiamy (w źródle zdarzają się literówki).
- Zapytania i wartości z danych klientów nie mają tu nic do rzeczy: narzędzie czyta tylko metadane bibliotek i dokumenty licencyjne.

Aktualizacja danych w OWLK: `owlk_update.py` podmienia w skonwertowanym tekście wykaz bibliotek i aplikacji (§2) oraz wykaz oprogramowania osób trzecich (§6) na bieżący
(listy `OWN_LIBS`, `OWN_APPS`, `THIRD` na początku pliku; wersje Tomcata, ActiveMQ i Terracotty z Dockerfile'i `mercury-docker`). Reszta tekstu OWLK i Załącznika 2 zostaje bez zmian.
Przy nowym wydaniu sprawdź te listy i zmień je ręcznie. W razie zmiany układu dokumentu Word skrypt zgłasza błąd zamiast po cichu nic nie zmienić.

Układ wyniku: w Załącznikach biblioteki są podzielone na sekcje `###` wg `groupId`, a w tabeli jest sam `artifactId` (kolumny: artefakt, wersja, rodzaj licencji, opis i repozytorium).
Zagnieżdżone listy w dokumentach prawnych są prawdziwymi listami Markdown z wcięciem 4 spacji na poziom (pozycje numerowane `1)` jako lista numerowana, pozycje z literami `a.` jako
punkty `- a.`, adres licencji jako ciąg dalszy pozycji z wcięciem 8 spacji). Zagnieżdżenie wylicza `docx2mdx.py` z lewego wcięcia akapitów Worda względem początku bieżącej listy.
`annex2_en.mdx.txt` (tłumaczenie robocze Załącznika 2) jest pisane ręcznie w tym samym formacie.
