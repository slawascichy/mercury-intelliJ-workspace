# Silnik wyszukiwania Mercury DB a Elasticsearch: opinia (2026-10-25)

**Zastrzeżenie.** Elasticsearch nie był tu uruchamiany ani mierzony. Opis Elasticsearch to wiedza ogólna (do stanu
wiedzy modelu, czerwiec 2026), nie weryfikowana w tej sesji. Opis silnika Mercury pochodzi z kodu i pomiarów w zadaniu
119. Wnioski oznaczone jako przypuszczenie wymagają PoC.

## 1. Czym jest silnik Mercury

Silnik to **osadzony Apache Lucene 7.5.0** (rdzeń tego samego typu co w Elasticsearch i OpenSearch) z własną warstwą
domenową w `mercury-lucene-indexes`:

- model „sprawy” z atrybutami dynamicznymi zdefiniowanymi w metadanych typu (pola z sufiksem `_S`, `_N`, `_T`),
- własny język zapytań (parser `NumMultiFieldQueryParser`) z operatorami `PARENT` i `CHILD` i składnią `pole.atrybut`,
- **połączenia między sprawami niezależnymi** (rodzic i dziecko to osobne dokumenty z polami `<pole>_<id>`) realizowane
  w warstwie zapytań (`NESTED_LOOP`, `NESTED_MERGE`, `IN`, `COLLECTION`), z planistą i optymalizatorem kosztowym,
- bezpieczeństwo na poziomie pól i typów (`checkQuerySecurity`) zintegrowane z modelem uprawnień,
- grupowanie (`groupBy`) liczone po zapytaniu na zmaterializowanych wierszach,
- źródło prawdy w bazie SQL, indeks jest pochodny i budowany przez sekretarzy (kolejka zmian), osobny indeks na każdym
  węźle klastra, bez shardingu.

## 2. Porównanie funkcjonalne

| Obszar | Mercury DB (stan z kodu i pomiarów) | Elasticsearch (wiedza ogólna) | Ocena |
|---|---|---|---|
| Rdzeń wyszukiwania | Lucene 7.5.0 (2018) | Lucene aktualny (9.x/10.x), wiele ulepszeń | Mercury odstaje wersją |
| Pełnotekstowe | Analizatory, wildcard, TextField; brak podświetlania, sugestii, synonimów w API | Bogate analizatory, synonimy, fuzzy, highlighting, suggesters, BM25 z konfiguracją | ES wyraźnie lepszy |
| Agregacje | `groupBy` po zapytaniu, wiersze `String[][]`, `BigDecimal`, obcięcie do `maxHits` | Agregacje z DocValues per shard, `date_histogram`, `terms`, `cardinality`, percentyle, zagnieżdżone, scalane automatycznie | ES wyraźnie lepszy |
| Połączenia | Rodzic i dziecko jako niezależne sprawy, `PARENT`/`CHILD`, planista kosztowy | `nested` (blok, szybkie, aktualizacja całego dokumentu) i pole `join` (wolniejsze), brak planisty kosztowego | Inny kompromis (patrz niżej) |
| Skalowanie | Jeden indeks na węzeł, pełna kopia na każdym, brak shardingu | Shardy, repliki, scatter-gather, routing, ILM | ES wyraźnie lepszy |
| Spójność | Źródło prawdy w SQL, indeks asynchroniczny | Indeks jako magazyn lub drugorzędny, near-real-time | Porównywalne (ten sam wzorzec, gdy ES jest wtórny) |
| Bezpieczeństwo danych | Uprawnienia pól i typów w modelu domenowym | RBAC, uprawnienia pól i dokumentów (funkcje licencyjne zależne od wersji) | Mercury lepiej dopasowany do modelu, ES bardziej ogólny |
| Wektory (kNN), geo, percolator | Brak w API (Lucene 7.5 nie ma HNSW) | Są | ES lepszy (ważne dla zadania 193) |
| Operacje | Własne kopie zapasowe indeksu, sekretarze, monitoring węzłów | Snapshoty, API zarządzania, bogate narzędzia monitoringu | ES dojrzalszy |
| Integracja z domeną | Wbudowany model spraw, wersjonowanie, metadane, SOAP/REST/RMI | Wymaga warstwy integracji | Mercury lepszy |
| Koszt i wdrożenie | Brak dodatkowej infrastruktury, osadzony | Klaster, licencje (Elastic) lub OpenSearch (Apache 2.0), więcej zasobów | Mercury prostszy |

## 3. Wydajność: co pokazują pomiary

- Zapytania proste na indeksie 22 mln dokumentów: 0,1 do 1 s. Grupowanie: 0,4 do 1,9 s dla 35 do 140 tys. trafień.
- Ograniczenia **strukturalne**, nie strojenia: (1) dla każdego trafienia ładowane są pola zapisane, a nie kolumny
  DocValues, (2) praca łączenia idzie w jednym wątku, (3) wynik jest ograniczony `maxHits` (100 tys. na produkcji), a
  przekroczenie daje po cichu niepełny wynik, (4) nowy czytnik indeksu na każde żądanie.
- Plan „dziecko najpierw” kosztuje 0,26 ms na trafienie (56 s dla 219 tys. dzieci). Połączenie typu `nested` w
  Lucene (BlockJoin) dla tych samych danych jest zwykle o rząd wielkości szybsze, ale **wymaga innego modelu danych**
  (dziecko wewnątrz dokumentu rodzica) i nie pasuje do spraw, które mają własny cykl życia i wiele odniesień.
- Przypuszczenie: ten sam `groupBy` w Elasticsearch trwałby dziesiątki milisekund (agregacja z DocValues w
  shardach równolegle) i nie byłby obcinany. To wymaga potwierdzenia w PoC.
- Lucene robi już „iteruj od najrzadszego” dla koniunkcji w jednym dokumencie. Planista Mercury rozstrzyga tylko, co
  zrobić przy połączeniach między dokumentami, czego Elasticsearch nie planuje kosztowo (przypuszczenie).

## 4. Opinia

**Czy silnik jest konkurencyjny?** W swojej niszy tak, jako platforma ogólna nie.

- **Mocne strony:** wbudowanie w model spraw (połączenia niezależnych spraw, uprawnienia pól, metadane typu, wersje),
  źródło prawdy w SQL, brak dodatkowej infrastruktury, przewidywalność na jednym węźle. Dla wolumenów rzędu
  kilkudziesięciu milionów dokumentów i zapytań o sekundę to wystarcza.
- **Słabe strony:** skalowanie (brak shardingu i równoległości w obrębie zapytania), agregacje (materializacja wierszy,
  obcięcie), stara wersja Lucene, brak funkcji nowoczesnego wyszukiwania (wektory, podświetlanie, synonimy), narzędzia
  operacyjne.
- **Najpoważniejszy problem to nie wydajność, tylko ciche obcięcie wyników** (to samo zapytanie zwraca raz 79 tys., raz
  81 tys., a poprawnie 89 896 trafień). W Elasticsearch ekwiwalent to jawny `hits.total` z relacją `gte`
  (`track_total_hits`), więc użytkownik wie, że wynik jest ograniczony. Mercury ma to naprawić niezależnie od dalszych decyzji.

**Wniosek decyzyjny.** Nie zastępować silnika Elasticsearch. Wada Mercury to nie sam Lucene, tylko warstwa wokół niego
(agregacje, równoległość, statystyki, wersja). Wszystko, co w ES dają shardy i agregacje, da się wprowadzić stopniowo:

1. oznaczanie obcięcia (poprawka poprawności),
2. kolektor agregatów z DocValues,
3. podział po dacie (wątki, potem węzły, plan z `analiza` sekcja 2),
4. nowsza wersja Lucene (zadanie 191).

To jest powtórzenie podstawowych elementów ES w mniejszej skali, a zarazem uzasadnienie dla pozostania przy własnym
silniku: model połączeń niezależnych spraw i uprawnień jest trudny do odtworzenia w ES bez denormalizacji i własnej
warstwy.

## 5. Kiedy rozważyć Elasticsearch lub OpenSearch

PoC wykonać, gdy pojawi się co najmniej jedno z wymagań:

- wolumen rzędu setek milionów dokumentów lub więcej niż jeden węzeł musi odpowiadać na to samo zapytanie równolegle,
- wyszukiwanie pełnotekstowe z oceną trafności, synonimami, podświetlaniem lub zapytania wektorowe (zadanie 193),
- wymóg agregacji w czasie poniżej sekundy dla setek tysięcy trafień (Grafana, pulpity),
- oczekiwanie wysokiej dostępności z automatycznym przełączaniem replik.

**Szkic PoC** (2 do 3 dni): zaindeksować do OpenSearch 22 mln dokumentów z indeksu INEA 3.0 w modelu `nested` albo
`join`, wykonać 10 zapytań z katalogu (`LuceneLegacyIndexQueryTest`), porównać czas i poprawność (89 896), zmierzyć
`groupBy` (`date_histogram`) i współbieżność. Koszt: pracochłonne mapowanie metadanych i uprawnień, więc PoC obejmuje
tylko wyszukiwanie, bez bezpieczeństwa.
