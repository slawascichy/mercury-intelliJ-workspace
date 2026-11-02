# [113] Stworzenie mechanizmu do przeglądu wykonywanych zapytań Lucene

https://github.com/slawascichy/hgdb/issues/113

Jest taka potrzeba by mieć podgląd do aktualnie wykonywanych zapytań.
Można to zrealizować poprzez zgromadzenie aktywnych wątków aktualnie realizujących zadanie wyszukiwania
Dobrze by było również prowadzić statystykę wykonywanych zapytań - czasy wykonania, liczba wykonania itd.

Monitoring jednego węzła jest wystarczający, jeżeli węzeł przekazał fragment realizacji zadania do innego węzła to 
tylko info np. `wait for node1`.

Podział na wartswy:
1. Usługi REST
2. GUI - do prezentacji danych w formie tabeli i wykresów

W przyszłości będziemy budować proxy i wtedy można by było zrealizować mechanizm zbierania statystyk z wszystkich 
węzłów i prezentowania ich w jednym miejscu, ale na razie wystarczy monitoring jednego węzła.
