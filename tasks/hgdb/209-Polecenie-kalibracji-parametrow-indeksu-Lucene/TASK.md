# [209] [mercury-cmd] Polecenie linii komend kalibrujące parametry początkowe indeksu Lucene

Zgłoszenie: https://github.com/slawascichy/hgdb/issues/209

Szkic zadania (2026-10-26, propozycja z zadania 119). Numer zgłoszenia (209) nadany przez autora.
Zakres, nazwa polecenia i lista parametrów to propozycje do decyzji autora. Elementy oznaczone „przypuszczenie” nie były sprawdzane.

## Cel

Parametry w `lucene.properties` dobiera się dziś ręcznie, a ich optymalne wartości zależą od danych klienta. W zadaniu 119 kalibrację progu
`lucene.query.cost.childFirstRatio` wykonano ręcznie, na jednym indeksie (INEA 3.0, 22 mln dokumentów), trzema przemiataniami po 41 zapytań.
Zadanie dodaje do `mercury-cmd` (moduł `mercury-srv-cmd`) polecenie, które robi to samo na lokalnym indeksie klienta i podaje gotowy fragment `lucene.properties`.

## Stan wyjściowy (zweryfikowany)

- `mercury-srv-cmd` ma polecenia rejestrowane w `CmdActionsEnum` (`GL`, `RIC`, `VL`, `RPD`, `JDBCTEST`, `HELP`, `EP`, `TS`), a każde ma klasę `…Action` implementującą `ShellAction`
  (wzorzec: `GenerateLuceneAction`). Uruchamia je `mercury-cmd.sh` z `-Dmercury.lucene.config.file=$MERCURY_HOME/config/lucene.properties`.
- Opis parametrów i miejsc ich ustawiania: `tasks/hgdb/119-…/parametry-konfiguracji-lucene-2026-10-26.md`.
- Metoda kalibracji (zbiór zapytań, miara „żalu”, przemiatanie progu, kryterium): `tasks/hgdb/119-…/podsumowanie-koncowe-2026-10-26.md`, punkt 4.
  Skrypt przeliczający: `tasks/hgdb/119-…/kalibracja-przelicz.py`. Zestaw 41 zapytań jest w testach `mercury` (`LuceneLegacyIndexQueryTest`, `LuceneQueryPerfSupport`), ale jest związany z danymi INEA.

## Proponowany zakres

Polecenie (propozycja kodu: `LC`, w `CmdActionsEnum`) działa na kopii albo na kopii roboczej indeksu wskazanego w `lucene.properties`, tylko w trybie odczytu, i kalibruje:

| Grupa | Parametry | Jak mierzyć |
|---|---|---|
| Zapytania | `lucene.query.cost.childFirstRatio`, `lucene.query.cost.probeLimit` | Zbiór zapytań wygenerowany z indeksu: pary rodzic–dziecko o różnych stosunkach liczności; tryby `cost`, `rootFirst`, `none`; żal ≤ 1,25 albo różnica ≤ 100 ms |
| Czytnik | `lucene.reader.refreshMs` | Koszt `openIfChanged` wobec oczekiwanej świeżości (opcja, przypuszczenie: wartość domyślna zwykle wystarcza) |
| Limit wyniku | `lucene.query.maxHits` | Rozkład liczby trafień w zbiorze zapytań, odsetek zapytań obciętych dla kandydatów limitu |
| Zapis (opcjonalnie) | `lucene.RAMBufferSizeMB`, `lucene.maxBufferedDocs`, `lucene.index.segments` | Czas budowy kopii indeksu dla kilku wartości (kosztowne, tylko na wyraźne żądanie) |

## Wyjście

1. Raport tekstowy i CSV: wartości kandydatów, liczba zapytań spełniających kryterium, suma czasów, mediana i maksimum żalu (jak tabele w `podsumowanie-koncowe`).
2. Rekomendowane wartości i gotowy fragment do wklejenia w `lucene.properties`. Polecenie **nie modyfikuje** `lucene.properties` samo (opcja `--apply` do rozważenia).
3. Ostrzeżenia: za mały indeks (mało dokumentów daje szum), zbiór zapytań bez par rodzic–dziecko, wyniki poniżej progu szumu (ok. 100 ms).

## Do rozstrzygnięcia przez autora

1. **Źródło zapytań.** Zestaw zapytań z 119 jest związany z INEA. Opcje: (a) generowanie zapytań z indeksu (typy, pola, statystyki termów); (b) plik zapytań dostarczony przez klienta (np. z logów); (c) oba.
2. **Gdzie działa polecenie.** Lokalnie na bibliotekach serwera (`command-local-context.xml`) na kopii indeksu, czy też na działającym węźle. Pomiar na produkcji zaburza pracę użytkowników (zadanie 171: rywalizacja o zasoby).
3. **Czy kalibrować parametry zapisu** (RAM, bufor, segmenty). Pomiar wymaga przebudowy indeksu, więc jest długi.
4. **Wspólne źródło kodu pomiarowego.** Kod z testów (`LuceneQueryPerfSupport`) leży w module testowym `mercury`. Polecenie wymaga jego przeniesienia do modułu produkcyjnego albo własnej implementacji.
5. **Zależności wersji.** `mercury-cmd` buduje się z wydanymi wersjami (`mercury.static.version=3.0.3.2.12`), a nowe parametry są w gałęzi `hgdb-119`. Polecenie działa tylko na serwerze z nową wersją biblioteki Lucene; trzeba ustalić wersję docelową.
6. **Lucene 9 (zadanie 191).** Kod pomiarowy powinien używać tych samych API, które zostaną po migracji (zgodność z zasadą z 119: bez klas w `org.apache.lucene.*`).

## Kryteria akceptacji (propozycja)

- Polecenie `LC` w `HELP`, opisane w dokumentacji `mercury-cmd`.
- Na indeksie INEA 3.0 wskazuje `childFirstRatio` z przedziału zbliżonego do ręcznej kalibracji z 119 (1,0 do 4,0; wartość wdrożona 2,0) i kryterium ≥ 90% zapytań.
- Raport powtarzalny (ten sam wynik w granicach szumu) i odporny na przerwanie (wynik cząstkowy zapisywany do pliku).
- Testy jednostkowe części przeliczającej (żal, kryterium, wybór progu) bez dostępu do indeksu.
