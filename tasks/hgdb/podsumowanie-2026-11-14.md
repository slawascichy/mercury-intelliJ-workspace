# Podsumowanie 2026-11-14

## Zamknięte i wydane

- **Zadanie 209 (kalibracja parametrów indeksu Lucene):** kalibracja na indeksie INEA, obserwacja 169, opisy PR-ów, pliki w `209-…/kalibracja-inea-2026-11-14/`. PR i merge wykonał autor.
- **Wydania i zależności:** `mercury` 3.0.4.26, `hgdb-client-open` 3.1.4.22, `mercury-cmd` 3.1.4.4. Zależności podniesione w `mercury-cmd`, `mercury-docker`, `hgdb-client-open`; obrazy zbudowane lokalnie i wypchnięte do Nexusa, pakiet sprawdzony. Data w `HGDB_VERSION` to tylko informacja o buildzie.
- **Kolejka:** dopisane 056 i 011 (picocli w `hgdb-utils`). W `CLAUDE.md` odnotowane, że `mercury-cmd` to `hgdb-utils` na GitHubie.

## W toku: zadanie 245 (najwyższy priorytet), etap A

- Strony `loggers`, `secretaries`, `lucene-queries` przepisane na JSP: język z aplikacji (pl/en), nagłówek jak strona główna, nazwa węzła, lista węzłów z monitora węzłów, `n=<węzeł>` + ciasteczko `hgdb_node` w nginx. Szczegóły: `245-…/TASK.md`.
- Kompilacja `mercury-ws-app` i 9 testów jednostkowych przechodzą. **Nie sprawdzone na działającym serwerze** (render JSP, wygląd, klaster za LB).
- Zacommitowane przez autora w gałęziach `hgdb-245` (`mercury`, `mercury-docker`); PR i merge jeszcze nie.

## Do wiedzy

- Monitor zapytań (113) nie pokazał planu na ekranie autora: plan zapisywany jest tylko dla zapytań wolnych (≥ `slowMillis`, 1000 ms). Autor zgłosił to przed zadaniem 245; do sprawdzenia po zakończeniu 245, czy to zachowanie, czy usterka.
- `mercury-ws-app` kompiluje się offline tylko po `install` pozostałych modułów (stare snapshoty w `.m2` nie mają nowych metod).
- Tłumaczenia de/es/fr/ko nowych kluczy `admin.*`: do translatora autora.
