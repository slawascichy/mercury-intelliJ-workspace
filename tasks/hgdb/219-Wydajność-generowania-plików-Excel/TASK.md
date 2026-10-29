# [219] Wydajność generowania plików Excel (eksport i serwer Iron POI)

https://github.com/slawascichy/hgdb/issues/219

**Status (2026-10-29):** zadanie analizy założone po teście eksportu widoków (zadanie 016, etap 3). Nic nie zmieniono w kodzie. Poniżej cel, dotychczasowe pomiary, hipotezy, plan analizy i decyzje do podjęcia. Metodyka wzorowana na zadaniu 119 (optymalizacja zapytań Lucene): najpierw powtarzalny pomiar bazowy, potem rozbicie czasu na warstwy, dopiero potem zmiany.

## Cel (autor)

Podnieść wydajność całego systemu generowania plików Excel. Zakres obejmuje obie strony: `mercury` (odczyt danych, konwersja wartości, wysyłka stron) i serwer Iron POI (`D:\workspace\git\poi-toolkit`, też kod autora), bo czas może być stracony w każdej z nich. Analiza ma wskazać, gdzie jest wąskie gardło, i zaproponować zmiany z oczekiwanym zyskiem. Wdrożenie zmian to osobne zadania.

## Obserwacja wyjściowa (2026-10-29, serwer dev)

Eksport widoku `Vw016Slm` (zadanie 016) do pliku xlsx przez `ExportGenerator` i serwer Iron POI:

| Eksport | Wiersze | Kolumny | Start | Koniec (czas pliku) | Czas | Szybkość |
|---|---|---|---|---|---|---|
| `tester`, rola `vw016-addr` | 100 000 (`SlmAddress`) | 6, tekst | 17:57:37 | ok. 18:01 | ok. 3,5–4 min | ok. 450 wierszy/s |
| `admin`, pełny dostęp | 200 000 (dwa typy) | 6, tekst | 18:12:33 | 18:28:04 | 15,5 min | ok. 215 wierszy/s (ok. 1,3 tys. komórek/s) |

Strony po 1000 wierszy (`mercury.view.maxPageSize`), postęp narastał mniej więcej liniowo (ok. 3% na 20 s). Czasy pochodzą z czasu modyfikacji plików i z `ReportExportStatus`, a nie z pomiaru w kodzie, więc są przybliżone.

Dla porównania (z wiedzy, niezmierzone na tym środowisku; do zweryfikowania w etapie 1): strumieniowe biblioteki xlsx (Apache POI SXSSF, XlsxWriter, openpyxl w trybie write-only) zapisują takie dane w kilkanaście do kilkudziesięciu sekund, a eksport do CSV z bazy trwa około sekundy. Wniosek wstępny: czas jest o 1–2 rzędy wielkości większy, niż wynika z samego formatu, więc to nie jest cena xlsx.

## Ścieżka eksportu (zweryfikowane w kodzie)

1. `ReportExportSecretary` (pula wątków `ExportSecretary`) bierze raport `WAITING` i wywołuje `ExportGenerator.generateReport`.
2. Eksport widoku: `generateViewReport` czyta kolejne strony `ICaseViewDefinitionLogic.readViewData` (zapytanie SQL z `LIMIT`/`OFFSET`, filtr wierszy i maskowanie), potem `PoiServerWriter.convertViewPage` (dekodowanie wartości przez `AttributeParser`), potem zapis strony przez RMI (`IWriteRemote.write`) w jednej transakcji serwera POI, na końcu `commitTransaction`.
3. Eksport spraw: ta sama ścieżka, ale dane z Lucene (`caseLogic.searchByQuery`) i konwersja `convertCollectionByStream` (pula `ForkJoinPool` z 5 wątkami).
4. Serwer Iron POI: `ExcelFileWriter` (m.in. `startNewSheet`, `insertRow`, `createCell`, style kolumn), menedżer transakcji `ExcelFileWriterTransactionManager`.

## Hipotezy (do zweryfikowania, żadna nie jest potwierdzona)

| # | Hipoteza | Gdzie sprawdzić |
|---|---|---|
| H1 | Zapis do pliku w serwerze POI jest kosztowny na stronę (style komórek, stan arkusza, brak strumieniowania, zapis całości przy `commit`) | `ExcelFileWriter`, `ExcelFileWriterTransactionManager`, profil po stronie POI |
| H2 | Dekodowanie ok. 1,2 mln wartości przez `AttributeParser` (z odwołaniami do zasobów) jest wolne, a przy widoku wykonywane jednowątkowo (eksport spraw ma pulę 5 wątków) | `PoiServerWriter.convertViewPage`, mikropomiar na gotowych stronach |
| H3 | Serializacja i przesył strony przez RMI (obiekt `ExcelFileWriterData` z 1000 wierszami) jest kosztowny | rozmiar i czas wywołania `IWriteRemote.write` |
| H4 | Odczyt stron widoku z `OFFSET` rośnie wraz z numerem strony (koszt `O(strona × rozmiar)`) | `EXPLAIN ANALYZE` kolejnych stron, porównanie z paginacją po kluczu |
| H5 | Przetwarzanie sekwencyjne: czytanie, konwersja i zapis nie nakładają się na siebie (potok mógłby być równoległy) | pomiar czasów faz na stronę |
| H6 | Pamięć i GC po stronie POI (alokacja cache 512 MB `ehcache` przy starcie, duże arkusze) | logi GC, profil pamięci |

## Plan analizy

- **Etap 0: stanowisko pomiarowe.** Zestaw danych (widok z ok. 200 000 wierszy, wersja z polami dat i liczb, bo dotychczasowe typy testowe mają same pola tekstowe), skrypt zlecający eksport i zbierający czasy, plik CSV z wynikiem bazowym (jak `baseline-*.csv` w zadaniu 119). Maszyna i dysk opisane przy pomiarze (kopie robocze na szybszym dysku).
- **Etap 1: rozbicie czasu na warstwy.** Tymczasowe logowanie czasu faz dla każdej strony (odczyt, konwersja, zapis RMI, zapis po stronie POI), profil JFR (Java Flight Recorder) dla `mercury` i serwera POI, rozmiar strony po serializacji. Wynik: tabela, ile procent czasu zajmuje każda warstwa.
- **Etap 2: dolna granica.** Samodzielny program zapisujący tyle samo danych (200 000 × 6) przez POI SXSSF i inny strumieniowy zapis, na tej samej maszynie. To pokazuje, ile powinno trwać samo pisanie xlsx.
- **Etap 3: weryfikacja hipotez i kandydaci na poprawki.** Dla każdej potwierdzonej hipotezy propozycja zmiany z szacowanym zyskiem, np.: strumieniowy zapis w POI, potok odczyt–konwersja–zapis w kilku wątkach, buforowanie definicji pól i wyników dekodowania na kolumnę, większe strony po stronie wysyłki, paginacja po kluczu, mniejszy narzut RMI.
- **Etap 4: decyzje i zadania wdrożeniowe.** Zatwierdzone poprawki jako osobne zadania z testami wydajności i regresji (poprawność plików, maskowanie, typy kolumn).

## Pytania do autora

1. Jaki jest cel (np. 200 000 × 6 poniżej minuty) i jakie wolumeny uznajemy za typowe oraz graniczne (limit 1 048 576 wierszy w arkuszu)?
2. Czy serwer POI musi zachować dotychczasowe zachowania, od których mogą zależeć klienci (szablony `tfn`, style kolumn, zapis stronami w transakcji, odczyt `load`)? To ogranicza zmianę na strumieniowy zapis.
3. Czy oprócz xlsx rozważamy inne formaty wyniku (np. CSV) jako szybką ścieżkę dla bardzo dużych eksportów?
4. Czy analiza obejmuje także odczyt plików (import, `ExcelFileReader`, `load` dla podglądu), czy tylko zapis?
5. Którą maszynę i które dyski uznajemy za środowisko pomiarowe?

## Definicja Gotowości

- Powtarzalny pomiar bazowy zapisany (skrypt i plik CSV) wraz z opisem środowiska.
- Rozbicie czasu eksportu na warstwy dla widoku i dla eksportu spraw.
- Wskazane wąskie gardła z dowodem (pomiar lub profil), a nie przypuszczeniem.
- Lista poprawek z oszacowanym zyskiem i ryzykiem, uzgodniona z autorem, oraz założone zadania wdrożeniowe.
- Obserwacje wynikłe z analizy dopisane do `docs/obserwacje.md`.

## Powiązania

- Zadanie 016 (Widoki), etap 3: eksport i podgląd widoków (`../016-Widoki/TASK.md`, sekcje „Etap 3”).
- Obserwacje 114 (nadmiarowa kolumna w eksporcie spraw), 115 (nieodświeżany stub RMI po restarcie POI), 116 (kolejka raportów i zawieszone `PROCESSING`).
- Zadanie 119: wzorzec metodyki (pomiar bazowy, analiza, decyzje, pomiar końcowy).
- Kod: `mercury-srv` (`ExportGenerator`, `PoiServerWriter`, `PoiServerLoader`, `ReportSecretarySupport`), `mercury-ws-app` (`ReportExportStatusRest`, `CaseViewExtRest`), `D:\workspace\git\poi-toolkit` (`ExcelFileWriter`, `ExcelFileWriterTransactionManager`, `WriteHandler`).
