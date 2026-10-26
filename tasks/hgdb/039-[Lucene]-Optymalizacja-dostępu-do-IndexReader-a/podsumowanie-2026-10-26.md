# [39] Podsumowanie 2026-10-26: optymalizacja dostępu do `IndexReader`

Stan: **zamknięte** (zgłoszenie zamknięte na GitHubie; kod scalony do `master` razem z zadaniem 119: `mercury` PR #210).
Zadanie zrealizowano jako etap **W12 zadania 119**. Szczegóły: `tasks/hgdb/119-…/plan-i-decyzje-2026-10-25.md` (sekcja 11 i „Realizacja W12”).

## Rozwiązanie

`LuceneConfig.getIndexReader` otwierał nowy `DirectoryReader` przy każdym żądaniu (99 do 159 ms na indeksie INEA, 25 segmentów). Obawa z opisu zadania
(`IndexReader.close()` jest `final`) nie wymagała własnej kompilacji Lucene. Klasa `org.mercury.lucene.reader.LuceneReaderPool` utrzymuje jeden wspólny
`DirectoryReader` na indeks i wydaje uchwyty `FilterDirectoryReader`, których `doClose()` zwalnia referencję zamiast zamykać czytnik.
Odświeżanie: po commicie własnego writera i co `lucene.reader.refreshMs` (domyślnie 1000 ms). Wyłącznik: `lucene.reader.pool=false`.

## Wynik (INEA 3.0, 41 zapytań)

- suma czasów trybu `cost`: 11,0 s → 6,4 s, mediana przyspieszenia zapytania 4,35×, żadne zapytanie wolniejsze;
- pulpit (6 paneli), p95 dla 1/4/8 klientów: 2035/2886/4524 ms → 1176/1595/1982 ms (degradacja 2,2× → 1,69×).

Odkrycie: wspólny czytnik włącza pamięć podręczną zapytań Lucene, więc `CardinalityProbe` używa searchera bez tej pamięci (`setQueryCache(null)`).

## Otwarte

Przebudowa indeksu na Windows przy działającej puli nie ma dedykowanego testu (pula jest pomijana na czas przebudowy, kopii i optymalizacji). Sprawdzenie ręczne po stronie autora.
