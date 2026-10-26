# [121] Sortowanie po wybranych parametrach kończy się błędem

https://github.com/slawascichy/hgdb/issues/121
https://support.ibpm.pro/browse/CMINATI-101

Swego czasu były problemy z sortowaniem po wybranych parametrach, które kończyły się błędem. Wydaje się, że problem został rozwiązany, ale warto to sprawdzić.
Zadanie nie zostało zamknięte, ponieważ kończy się komentarzem: 

> Otworzyłem temat do dyskusji na temat tego czy obecna strategia pól sortowania jest zgodna z oczekiwaniem.


## Analiza z 2026-10-26 (zadanie 119)

Błąd z CMINATI-101 jest odtworzony testem `LuceneSortNonSortableFieldTest` (`mercury-lucene-indexes`): sortowanie po polu bez
DocValues kończy się `IllegalStateException` z Lucene, a `LuceneSearcher.addSortField` nie sprawdza flagi `sorted`
definicji pola. Propozycja poprawki (walidacja z komunikatem `L0009.3` oraz kontrola względem indeksu) jest opisana w
zadaniu 119, sekcja 10 pliku `plan-i-decyzje-2026-10-25.md` (strumień W11), do zatwierdzenia. Pytanie o strategię pól
sortowania (czy `status` ma być sortowalny) pozostaje otwarte.

Stan 2026-10-26: poprawka W11 zrealizowana w gałęzi `hgdb-119` (walidacja pola sortowania `L0009.7` i kontrola względem indeksu `L0009.8`, testy `LuceneSortNonSortableFieldTest`). Pytanie o strategię pól sortowania pozostaje otwarte, więc zadanie nie jest zamknięte.
