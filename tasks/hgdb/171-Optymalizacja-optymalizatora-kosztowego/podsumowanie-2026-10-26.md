# [171] Podsumowanie 2026-10-26: optymalizacja „optymalizatora kosztowego”

Stan: **zamknięte** (zgłoszenie zamknięte na GitHubie; zadanie realizowane razem z 119, kod scalony do `master`: `mercury` PR #210, `mercury-lib` PR #30).
Szczegóły: `tasks/hgdb/119-…/podsumowanie-koncowe-2026-10-26.md`.

## Co zmieniono w optymalizatorze

- Decyzja o kolejności planu (korzeń najpierw czy dziecko najpierw) opiera się na **sondach liczności** (`CardinalityProbe`), a nie na logarytmie częstości najrzadszego termu.
  Próg `lucene.query.cost.childFirstRatio` (domyślnie 2,0) skalibrowano trzykrotnie na 41 zapytaniach INEA 3.0.
- Zbiorcze łączenie rodzic–dziecko i odczyt z DocValues (W4, W5, W7) usunęły największe koszty planów.
- Obcięcie wyniku limitem trafień jest jawne: `truncated` i `totalHits` w odpowiedzi, opcjonalny błąd (`lucene.query.truncation.error`).
- Wskazówki kontekstu `ruleRootFirst` i `useCostOptimization` działają jak dotąd (wymuszenie planu).
- Wspólny czytnik indeksu (zadanie 39) zmniejszył degradację przy wielu klientach z 2,2× do 1,69×.

Kryterium jakości (żal ≤ 1,25 albo różnica ≤ 100 ms) spełnia 39 z 41 zapytań (wobec 28 z 41 przed zmianami).

## Granice pomiaru

Pomiary wykonano na indeksie INEA 3.0, a nie na danych i zapytaniach przypadku Rejestr Publikacji (filtr „TYP PRZYŁĄCZA”, CMINGW-846) opisanego w zadaniu.
Zmierzone przed zmianami czasy z plików `Rejestr_pub*.xlsx` nie zostały powtórzone na danych klienta. Ocena skutku dla tego przypadku wymaga ponownego przejścia
scenariuszy na środowisku klienta. Znane ograniczenie: „adres 30 dni + Mts” ma żal 3,9 (wymaga modelu kosztu z osobnymi stałymi, W3 część 2).
