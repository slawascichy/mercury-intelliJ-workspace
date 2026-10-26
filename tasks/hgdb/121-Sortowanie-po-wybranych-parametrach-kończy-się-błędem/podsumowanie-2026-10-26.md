# [121] Podsumowanie 2026-10-26: sortowanie po polu, które nie jest sortowalne

Stan: **zamknięte** (zgłoszenie zamknięte na GitHubie; kod scalony do `master` razem z zadaniem 119: `mercury` PR #210).
Poprawka to etap **W11 zadania 119** (`tasks/hgdb/119-…/plan-i-decyzje-2026-10-25.md`, sekcja 10 i „Realizacja W11”).

## Przyczyna i poprawka

Błąd z CMINATI-101: sortowanie po polu bez DocValues kończyło się `IllegalStateException` z Lucene (ogólny błąd aplikacji `M0001`).
`LuceneSearcher.addSortField` nie sprawdzał flagi `sorted` definicji pola. Teraz:

- pole z `sorted=false` kończy się błędem walidacji `L0009.7`;
- pole oznaczone jako sortowalne, ale bez DocValues w indeksie (indeks zbudowany przed zmianą definicji), kończy się błędem `L0009.8` przed wyszukiwaniem
  (`LuceneSearcher.validateSortAgainstIndex`);
- komunikaty są w sześciu językach (pl, en, de, es, fr, ko); testy: `LuceneSortNonSortableFieldTest` (5).

Listę pól typu daje `CaseIndexerFieldsManagerRest` (`getFieldsByTypeCodes`).

## Otwarte

Pytanie z komentarza zgłoszenia (czy obecna strategia pól sortowania, np. czy `status` ma być sortowalny, jest zgodna z oczekiwaniem) nie ma w workspace zapisanej decyzji.
Zadanie zamknięto na GitHubie, więc zakładam, że obecna strategia zostaje (przypuszczenie). Dokumentacja użytkownika (`docusaurus-hgdb`) nie została zmieniona.
