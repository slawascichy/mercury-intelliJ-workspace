# [16] Widoki

https://github.com/slawascichy/hgdb/issues/16
https://github.com/slawascichy/hgdb/issues/17
Obsługa widoków jest bardzo istotna. Trzeba opracować koncepcję jak to w końcu zaimplementować. Na pewno trzeba zrobić:

1. Obsługa widoków relacyjnych utworzonych w bazie danych, są problemy z ich w relacyjnej bazie danych, gdy sam 
   widok jest w zależności od innych widoków/pakietów. W Oracle jest coś takiego jak status `invalid`, kompilujesz 
   przy pierwszym użyciu, w PosthreSQL pojawiają się lock, i błędy.
2. Wykorzystanie mechanizmów dynamicznych jakie już są zaimplementowane
3. Wynik widoków:
   - Prezentacja w standardzie Excel
   - Prezentacja w standardzie listy parametrów?
4. Integracja z mechanizmami raportowania i eksportu danych z Iron Server
5. Sprawdź ze zmianami Github `17: Raporty - integracja z IRON Poi Server - obsługa widoków`.
