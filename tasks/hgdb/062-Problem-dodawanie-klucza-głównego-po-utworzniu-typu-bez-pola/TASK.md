#  [62] Problem dodawanie klucza głównego po utworzniu typu bez pola 'PK'

https://github.com/slawascichy/hgdb/issues/62

Opis scenariusza zdarzeń:
1. Tworzę typ 'X' z polami bez definicji pk
    1. field001
    2. field002
1. Wstawiam kilka spraw w takim typie
2. Wprowadzam zmianę do typu:
    1. dodaję pole 'id'
    2. ustawiam na nim 'PK'

Kończy się błędami:
1. Exception: nie wszystkie wersje typu mają zdefiniowane pole 'id'
2. Exception: nawet jeśli poprzez operacje bazodanowe da mi się sztucznie dodać pole 'id', to będzie krzyczał, że sprawy mają nieunikalną wartość (`null`)

Pomysł - zbudować usługę: forceAddPK, która zrealizuje zadanie:
1. Uzupełni wszystkie wersje typu o brakujące pole (np. na ostatniej pozycji)
2. Uzupełni unikalnymi wartościami sprawy:
    1. Dla typu pól z 'PK' typu `String ` - UUID
    2. Dla typu pól z 'PK' typu `Number ` - wartości ujemne.

Do weryfikacji po zmianach poprawność prezentacji sprawy.