# [180] Problem z niektórymi metodami w usłudze CaseIndexerFieldsManagerAction

https://github.com/slawascichy/hgdb/issues/180

Zarządzanie polami dla niektórych metod nie spełnia oczekiwań:

- metoda getFieldsBySubFieldName powinna tak działać, że dla argumentu address dostaję tylko pola, które są w 
  adresie. Teraz dostajemy wszystkie pola, że wszystkich kategorii (pola predefiniowane) i pola ustawione. Trzeba zmienić by:
    - Prezentować tylko pola kategorii Case
    - Nie prezentować pól predefiniowanych
    - Przezentować tylko właściwe pola przypisane typom spraw.

- metoda getFieldsBySubFieldNameAndTypeCode powinna tak działać, że dla argumentu address oraz Emploee dostaję tylko pola, które są w adresie i to w typie nadrzędnym pracowników. Teraz dostajemy wszystkie pola, że wszystkich kategorii (pola predefiniowane) i pola ustawione. Trzeba zmienić by:
    - Prezentować tylko pola kategorii Case
    - Nie prezentować pól predefiniowanych
    - Przezentować tylko właściwe pola przypisane denemu typowi.
