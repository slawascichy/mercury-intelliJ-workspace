# [169] Zmiana typu identyfikatora sprawy na String

https://github.com/slawascichy/hgdb/issues/169

Zadanie polega na zmianie typu identyfikatora sprawy z `Long` na `String` w całym systemie. Wymaga to modyfikacji 
zarówno w warstwie danych, jak i w interfejsach użytkownika oraz API. W ramach zadania zostały już wykonane poprawki.
Trzeba sprawdzić jak bardzo jest zaawansowana zmiana i czy nie wymaga dodatkowych poprawek w dokumentacji lub kodzie.
Jeżeli jest wszystko OK, to zamykamy zadanie

## Uwagi (2026-10-25)

Przy zadaniu 119 znaleziono pozostałość po `Long` w module `mercury-lucene-indexes`: wyszukiwanie spraw nadrzędnych po
identyfikatorze sprawy zależnej używało `Long.parseLong` i `LongPoint`
(`DataCollectorSubTopDocsManagerSupport.collectSubResults`, `CaseCustomScoreProvider`). Plany „najpierw dziecko”
kończyły się `NumberFormatException`. Poprawka jest wykonana w zadaniu 119 (gałąź `hgdb-119`, `mercury`). Indeks
zapisuje te identyfikatory jako `StringField`, więc zapytanie używa teraz `TermQuery`. Nie trzeba jej powtarzać w 169.
Szczegóły: `tasks/hgdb/119-…/podsumowanie-2026-10-24.md`.