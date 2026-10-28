# [218] Czyściciel starych wersji spraw

https://github.com/slawascichy/hgdb/issues/218

**Status (2026-10-28):** zadanie założone po dyskusji przy zadaniu 016 (Widoki). Nic nie zaimplementowano. Poniżej cel, ustalone fakty, propozycja i decyzje do podjęcia.

## Cel (autor)

Mercury ma pełnić rolę bazy spraw dla procesów. Procesy i ich modele się zmieniają, a założeniem jest, żeby zmiana modelu **nie wymagała migracji**: sprawy zostają pod starą wersją typu, a nowe powstają pod nową. Stare wersje spraw usuwa „czyściciel”: na żądanie albo jako scheduler.

## Ustalone fakty (kod i dane, 2026-10-28)

| Fakt | Źródło |
|---|---|
| Zwykła edycja sprawy aktualizuje wiersz w miejscu. Migawki zmian trafiają do `igo_da_tasks_history` (CaseHistoryTrace). | uwaga autora |
| Nowy wiersz sprawy powstaje tylko wtedy, gdy zmienił się typ lub wersja typu (`typeHasChanged` w `CaseLogicHelperService.updateCaseWithHistory`). Nowy wiersz ma nowe id (`createCaseId(numer z sekwencji, kod typu nowego typu)`), status `A` i `previousVersionId` wskazujący na starą sprawę. | `CaseLogicHelperService.initNewVersionCase` |
| Stara sprawa zostaje z dotychczasowym `case_type_id` i statusem zamkniętym `Z`. Przy sprawdzaniu kluczy unikalnych kod wymaga statusu `Z` poprzedniej wersji, z możliwością pominięcia. `Z` oznacza też zwykłą „przerwaną” sprawę, więc nie jest pewnym znacznikiem „stara wersja”. | `CaseDAO` (`checkUniqueConstraintAfterDML`), `Case.State` |
| `changeModel(fromTypeId, toTypeId)` robi `UPDATE igo_da_cases SET case_type_id` w miejscu (bez nowych wierszy i bez zmiany id). DAO nie sprawdza, czy oba typy mają ten sam kod. | `CaseDAO.changeModel` |
| Bieżącą wersję wskazuje `igo_da_case_roots.last_version` (klucz `root_version_id`). | `removeValidation`, skrypt 01 |
| `TypeCode.retentionTimeMilis` („usuń sprawę po czasie od utworzenia”) nie jest nigdzie egzekwowane: brak wywołań `getRetentionTimeMilis`. Predefiniowane typy ustawiają 6 lat. | obserwacja 110 |
| `TypeCode.useArchivization` i `CaseArchivizatorService` działają dotąd **tylko przy usuwaniu spraw** (zapis do `ArchCase` przed usunięciem). To nie jest mechanizm optymalizacji ani odciążania tabeli. Usuwanie typu z `useArchivization` bez archiwizatora jest odrzucane. | `CaseLogic`, uwaga autora |
| `CaseLogic.removeValidation` zna wersje (`CaseRootVersion`, wersja główna, ostatnia, jedyna) i flagę `removeAllVersions`. | `CaseLogicHelperService.removeValidation` |
| Wzorzec schedulera: `CaseLastUpdatedCleaner` (`ScheduledExecutorService`, parametry `delay` i `interval`) wysyła komunikat JMS, a odbiorca wykonuje pracę. Klasa ostrzega przed rywalizacją węzłów w klastrze. | `org.mercury.business.data.threads` |
| W bazie dev nie ma spraw wersjonowanych (`piervous_version_id` ma 0 niepustych wierszy), więc zachowanie na takich danych nie było testowane. | zapytanie do bazy dev |

## Proponowany kształt (rozszerzenie istniejących mechanizmów, bez nowego obok)

- **Kwalifikacja:** status `Z`, ma ją jako poprzednią (`previousVersionId`) nowszy wiersz, starsza niż próg.
- **Uruchamianie:** na żądanie (operacja w usłudze: kod typu, próg wieku, limit partii) i opcjonalnie scheduler, domyślnie wyłączony, wzorowany na `CaseLastUpdatedCleaner`.
- **Tryb próbny:** raport, co zostałoby usunięte, bez usuwania.
- **Usuwanie** przez istniejącą logikę usuwania (`remove` z `removeValidation`), żeby obsłużyła powiązane dane: dokumenty, komentarze, zadania, `case2case`, wpisy kluczy unikalnych i indeks Lucene. Archiwizacja tylko dla typów z `useArchivization`, jak dotychczas.
- **Uprawnienia** jak przy usuwaniu oraz weryfikacja kontekstu z zadania 217.

## Decyzje do podjęcia (autor)

1. **Źródło progu wieku starych wersji.** `retentionTimeMilis` znaczy „usuń całą sprawę po czasie od utworzenia”, więc dla starych wersji potrzebny jest osobny parametr: globalny (konfiguracja, bez zmiany schematu) czy na typie (nowa kolumna w `igo_da_typecode`)?
2. **Historia starej wersji** (`igo_da_tasks_history`): usuwać razem z nią (klucz obcy z `case_id` do `igo_da_cases` i tak tego wymaga), czy przenosić do archiwum?
3. **Spójność łańcucha wersji** po czyszczeniu: `previousVersionId` najstarszego pozostałego wiersza i `root_version_id` mogą wskazywać na usunięte wiersze. Jak to ma wyglądać? Do rozpoznania w etapie 0: jak istniejące `remove` traktuje wersję główną.
4. **Klaster:** jeden węzeł przez kolejkę JMS (jak w `CaseLastUpdatedCleaner`), z opóźnieniami węzłów jako zabezpieczeniem przed rywalizacją.

## Etapy

| Etap | Zakres |
|---|---|
| 0 | Rozpoznanie: jak `remove` traktuje wersję główną, ostatnią i powiązane dane; co robi archiwizator; test na danych z wersjami (w dev ich brak) |
| 1 | Operacja na żądanie z trybem próbnym, uprawnienia, limit partii, testy |
| 2 | Scheduler (domyślnie wyłączony) i parametry konfiguracji |
| 3 | Dokumentacja w `docusaurus-hgdb`, obserwacje, klucze OpenAPI (po zmianie API) |

## Powiązania

- Zadanie 016 (Widoki): widok dla kodu typu obejmuje wszystkie wersje typu, więc zamknięty stary wiersz przeniesionej sprawy jest w nim obecny, dopóki czyściciel go nie usunie. Decyzja, czy widok ma pokazywać taki wiersz, zostaje w zadaniu 016 (sekcja „Partycjonowanie `igo_da_cases` a widoki”).
- Zadanie 217 (Reprezentowanie użytkowników): weryfikacja kontekstu dla operacji czyściciela.
- Obserwacja 110 w `docs/obserwacje.md`.
