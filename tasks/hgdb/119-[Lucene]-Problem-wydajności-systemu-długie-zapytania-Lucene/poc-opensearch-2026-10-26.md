# Zadanie 119, W9: PoC OpenSearch (2026-10-26)

Cel (decyzja D6): sprawdzić, jak zapytania z bazy pomiarowej wypadają w OpenSearch na tych samych danych, po wprowadzeniu
zmian W0–W7 w silniku Mercury. Wyniki pochodzą z jednego uruchomienia na jednej maszynie (opis niżej). Wnioski
oznaczone jako przypuszczenie nie były mierzone.

## Środowisko

- Maszyna: ta sama, na której mierzono Mercury (16 logicznych rdzeni, 31,8 GB RAM, dysk `F:`).
- OpenSearch 2.19.1 (zip dla Windows z dołączonym JDK, silnik Lucene 9.12.1), jeden węzeł, sterta 6 GB, 4 shardy,
  0 replik, bez wtyczki bezpieczeństwa (`plugins.security.disabled`), dane na `F:\opensearch-poc\data`. Serwer zatrzymany po
  pomiarach (uruchomienie: `F:\opensearch-poc\os\opensearch-2.19.1\bin\opensearch.bat` z ustawionym
  `OPENSEARCH_JAVA_HOME` na dołączony katalog `jdk` i bez `JAVA_HOME`).
- Dane: indeks INEA 3.0 (22 028 880 dokumentów, 6,9 GB, kopia na `F:`, otwierany tylko do odczytu), wyeksportowany
  programem `poc-opensearch/Exporter.java` (Lucene 7.5.0 do odczytu, `_bulk` do OpenSearch). Czas eksportu: etap A
  (adresy z dziećmi, zlecenia FSM) 17 s, etap B (pozostałe typy) 116 s.

## Model danych PoC

| Element | Rozwiązanie |
|---|---|
| Dokumenty główne | `slmaddress` (379 595) z dziećmi `slmappmobiledetails` (376 694) osadzonymi jako pole `nested` (`appMobile`: `status`, `st`), `fsmserviceorder` (224 803) oraz pozostałe typy jako płaskie rekordy (21,05 mln) |
| Pola | `type`, `status`, `createDate` (data), `price` (liczba), `caseId`, `city`, tylko te, których potrzebują zapytania. Mercury indeksuje ok. 600 pól |
| Pochodzenie wartości | kategorie z indeksu odwróconego, liczby i daty z DocValues, identyfikatory dzieci z DocValues pola rodzica |
| Rozmiar | 859 MB (Mercury: 6,9 GB), 22 031 781 dokumentów Lucene wraz z obiektami zagnieżdżonymi |

## Poprawność

**Wszystkie 10 zapytań daje takie same liczby trafień (lub liczby grup) jak Mercury.** Dotyczy to także zapytań z dzieckiem
(benchmark Poznań + Mts: 89 896, 365 dni + Mts: 204 122), czyli semantyka „to samo dziecko spełnia wszystkie warunki” jest
zachowana przez `nested`. Sprawdzono liczby, nie zawartość wierszy. W pierwszej wersji eksportu status dziecka brał pierwszy
term pola wielowartościowego zamiast kodu słownikowego, co dawało 0 trafień. Poprawione (preferowany prefiks `slmapp`).
Histogram dat wymaga `min_doc_count: 1`, bo domyślnie zwraca puste przedziały (480 grup zamiast 340).

## Czasy (najlepszy z 9 przebiegów, bez pamięci podręcznej żądań; Mercury: przebieg końcowy W0–W7, tryb `cost`)

| Zapytanie | Trafień/grup | Zgodność | Mercury [ms] | OpenSearch [ms] | Stosunek |
|---|---|---|---|---|---|
| adres Poznań + Mts (benchmark) | 89896 | ZGODNE | 903 | 12 | 75× |
| adres 365 dni + Mts | 204122 | ZGODNE | 1898 | 15 | 127× |
| adres 30 dni + Mts | 1414 | ZGODNE | 2545 | 12 | 212× |
| adres Poznań + Rfs | 14177 | ZGODNE | 223 | 11 | 20× |
| adres Leszno + Vrf | 73 | ZGODNE | 107 | 11 | 10× |
| FSO 365 dni (lista) | 34964 | ZGODNE | 282 | 12 | 24× |
| FSO 7 dni (lista) | 3426 | ZGODNE | 91 | 10 | 9× |
| groupBy(miesiąc) FSO | 16 | ZGODNE | 476 | 11 | 43× |
| groupBy(city) SlmAddress | 105 | ZGODNE | 370 | 11 | 34× |
| groupBy(price, dzień) | 340 | ZGODNE | 243 | 17 | 14× |

Pulpit (6 paneli, 3 odświeżenia na klienta): odświeżenie pulpitu **p95 OpenSearch 121 / 117 / 179 ms** dla 1 / 4 / 8 klientów
(`poc-opensearch/res_conc.txt`), Mercury 2035 / 2886 / 4524 ms (`koncowy-wspolbieznosc-2026-10-26.csv`). Wyłączenie pamięci
podręcznej zapytań w indeksie nie zmieniło wyników (zapytania 9 do 15 ms, pulpit p95 131 / 130 / 151 ms,
`poc-opensearch/res_nocache.txt`, `res_conc_nocache.txt`).

## Jak to czytać (ograniczenia porównania)

1. **Indeks PoC jest 8 razy mniejszy i wąski** (859 MB, kilka pól wobec ok. 600). Mercury nosi koszt szerokiego modelu
   (zapisane pola w blokach, wiele pól przy dokumencie). To nie jest różnica silników, tylko modelu danych.
2. **Inny kontrakt wyniku.** Mercury buduje wszystkie wiersze wyniku (do `maxHits`), wczytuje komórki każdego trafienia i dopiero
   potem stronicuje. OpenSearch zwraca 60 pierwszych dokumentów, a agregacje liczy na DocValues bez tworzenia wierszy.
   Wynik dla klienta (strona 60 wierszy lub grupy) jest ten sam, ale ścieżka obliczeń inna.
3. **Brak uprawnień, metadanych i semantyki Mercury.** PoC nie zawiera kontroli uprawnień, filtrów bezpieczeństwa, tłumaczenia
   słowników (np. `SlmAppMts` na wartość indeksu), wersjonowania typów ani wyrażeń `groupBy` (funkcje, `MathExpression`).
4. **Pomiar jednowęzłowy, pojedyncza maszyna, ciepła pamięć podręczna systemu plików** (indeks PoC mieści się w pamięci).
   Zimny start i wiele węzłów nie były mierzone.
5. Nie mierzono zapisu: ścieżki aktualizacji pojedynczych spraw (sekretarz indeksu), spójności z bazą SQL ani zużycia
   pamięci przy pełnym modelu 600 pól (przypuszczenie: indeks OpenSearch z pełnym modelem byłby kilkukrotnie większy).
6. Dla odniesienia, histogram dat po stronie czystego Lucene 7.5 na indeksie INEA (kolektor z DocValues, W6) kosztuje 44 ms
   (FSO, 39 tys. trafień) i 468 ms dla całego indeksu 22 mln dokumentów. Mercury `groupBy(miesiąc)` to 476 ms, z czego silnik
   (zapytanie, wiersze, grupowanie) ok. 290 ms, reszta to narzut pomiaru.

## Wnioski i rekomendacja

1. Na tych 10 zapytaniach OpenSearch jest od 9 do 212 razy szybszy, a odświeżenie pulpitu (p95) 17 do 25 razy szybsze, ale
   przewaga pochodzi głównie z **modelu danych** (zdenormalizowany, wąski dokument z osadzonymi dziećmi i DocValues) oraz z
   **braku materializacji wierszy**, a nie z samego silnika Lucene. Mercury po W3–W7 używa tego samego silnika i tych samych
   technik tam, gdzie dało się je zastosować (DocValues, zbiorcze łączenie, histogram z DocValues).
2. **Zgodność wyniku jest osiągalna**, więc PoC nie wskazuje przeszkody semantycznej dla zapytań z dzieckiem i agregacji dat.
3. **Nie rekomenduję migracji na OpenSearch w ramach 119.** Wymagałaby zastąpienia modelu uprawnień, metadanych pól, budowania
   indeksów (sekretarze, przebudowa) i semantyki `groupBy`, a czasy Mercury po zmianach (od 0,1 do 2,5 s) mieszczą się w celach
   zadania. PoC ustala natomiast **wartość docelową**, do której warto zbliżać silnik.
4. **Wnioski projektowe do wykorzystania w Mercury (kolejność wg stosunku zysku do kosztu):**
   a. zapis `*_subCaseIds` jako DocValues przy przebudowie indeksu w 191/75 (odczyt rodziców kolumnowo także w nowym formacie);
   b. materializacja wierszy tylko dla strony wyniku przy zapytaniach bez `groupBy` (dziś wszystkie trafienia do `maxHits`);
   c. dla zapytań grupujących po polach liczbowych i dat: agregacja w kolektorze z DocValues, bez potoku wiersze → dokumenty
      (odrzucone w W5 etap 2 jako zbyt ryzykowne semantycznie, do rozważenia dla wąskiego podzbioru funkcji: `count`, `sum`,
      `min`, `max`, `trunc(data)`);
   d. osadzanie dzieci w dokumencie rodzica dla najczęstszych par (usuwa koszt łączenia; wymaga zmiany modelu 3.0, przypuszczenie).
5. Gdyby pojawiło się wymaganie przekraczające możliwości silnika (skala wielowęzłowa, setki równoległych klientów), PoC z pełnym
   modelem pól i uprawnieniami byłby następnym krokiem (nie w 119).

## Pliki

`poc-opensearch/Exporter.java` (eksport), `queries.py` (10 zapytań, porównanie liczb), `conc.py` (pulpit), `res_*.txt`,
`queries-result.json`, `tabela.md`.
