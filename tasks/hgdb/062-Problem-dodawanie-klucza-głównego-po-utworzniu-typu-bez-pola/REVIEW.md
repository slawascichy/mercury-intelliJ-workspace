# REVIEW - zadanie 62

Data: 2026-10-23  
Zakres: zmiany dla `forceAddPK` i obsługi `uniqueConstraintParamName` jako formuły (repozytoria `mercury` oraz `mercury-lib`, gałąź `hgdb-62`, bez commitów).

## Najważniejsze wnioski

### 1) [HIGH] Import Excel nie obsługuje poprawnie klucza będącego formułą

W `PoiServerLoader#importCase` wartość używana do wyszukania istniejącej sprawy (`pkValue`) jest budowana z pojedynczego pola, a nie z całej formuły klucza.

- plik: `mercury/mercury-srv/src/main/java/org/mercury/single/node/business/reports/PoiServerLoader.java`
- linie: okolice 347-349, 365-372

Konsekwencja:
- przy formule np. `name||' '||secondName` import może wyszukiwać po niepełnej wartości,
- możliwe błędne dopasowania, duplikaty lub aktualizacja nie tej sprawy.

### 2) [HIGH] Użycie `contains()` na definicji formuły daje fałszywe trafienia nazw pól

Warunek:
- `uniqueConstraintParamName.contains(propertyName)`

- plik: `mercury/mercury-srv/src/main/java/org/mercury/single/node/business/reports/PoiServerLoader.java`
- linia: okolice 348

Konsekwencja:
- pole `name` zostanie uznane za część `firstName`,
- `pkValue` może zostać ustawione z niewłaściwego parametru.

### 3) [MEDIUM] Brak twardej walidacji składni formuły przed generowaniem SQL

`UniqueConstraintParamDefinition#toSQLParam` składa fragment SQL z elementów formuły; literały są wstawiane bez pełnej walidacji składni literałów (np. apostrofy/parowanie).

- plik: `mercury/mercury-dao-api/src/main/java/pro/ibpm/mercury/dao/beans/UniqueConstraintParamDefinition.java`
- linie: okolice 165-181
- użycie: `mercury/mercury-dao/src/main/java/pro/ibpm/mercury/dao/attr/TypeCodeDAO.java` (tworzenie zapytań native)

Konsekwencja:
- ryzyko błędów SQL w runtime dla niepoprawnej formuły.

## Co wygląda dobrze

- Logika `forceAddPK` w `TypeCodeLogic` jest spójna z opisanym przebiegiem:
  1. walidacja typu i definicji,
  2. dodawanie brakujących pól do wszystkich wersji,
  3. uzupełnianie wartości w sprawach z pustymi polami klucza,
  4. zapis historii zmian spraw,
  5. utworzenie wpisów unikalności + reindeksacja.

- `UniqueConstraintParamDefinition#toValue` zachowuje się zgodnie z testami: błąd tylko dla wartości równej samym literałom.

## Rekomendacje

1. W `PoiServerLoader#importCase` wyliczać `pkValue` z pełnej formuły (tokenizacja po `||`, literały + wartości pól) zamiast wybierania pojedynczego pola.
2. Zastąpić `contains()` parserem elementów formuły i porównaniem pełnych nazw pól.
3. Dodać walidację składni formuły (zwłaszcza literałów) przed użyciem jej w SQL.
4. Dodać test regresyjny importu dla formuły `name||' '||secondName` oraz przypadku kolizyjnego (`name` vs `firstName`).

## Status przeglądu

- Kompilacja/uruchomienie nie były wykonywane na tym etapie (zgodnie z ustaleniem, że zmiany nie były jeszcze odpalane).
- Weryfikacja oparta o analizę kodu i przepływu danych.

