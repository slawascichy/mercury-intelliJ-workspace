# Macierz identyfikacji typu atrybutu (wersje typów i definicji)

Dokument opisuje doświadczenie z 2026-10-31: kiedy ponowne ładowanie pola o innym zadeklarowanym typie tworzy
nową wersję typu sprawy i nową definicję parametru. Powód: obserwacja 128 (nieuzasadniona wersja typu) i pytanie, czy
definicje są dobierane zbyt luźno (po nazwie, bez typu).

## Jak powstała macierz

- Scenariusz badawczy `TypeIdentificationMatrixScenario` (`mercury-srv/src/test`), uruchamiany przez klasę
  `TypeIdentificationMatrixTest` poza `SrvTest`. Nie ma asercji, wypisuje wiersze `MATRIX|…` do dziennika.
- Dla każdej pary (pierwsze ładowanie, drugie ładowanie) tworzony jest osobny typ i osobne pole, więc pary nie
  wpływają na siebie. Pierwsze ładowanie tworzy typ i definicję, drugie jest ładowane do istniejącego typu.
- Nadawcy (zadeklarowany typ i wartość): `String:abc`, `String:7`, `Text:abc`, `Integer:5`, `Decimal:5.5`,
  `Number:5`, `Boolean:true`. Razem 49 par.
- Przebiegi: kod przed zmianą (obserwacja 132) i po niej, ta sama baza testowa `mercury-db-test`.
- Nie badano: `Date`, `DateLong`, `Time`, `Currency`, `Password`, `URL`, `Lob`, list, spraw zależnych, tej samej
  nazwy pola w różnych typach, kilku pól w jednym typie oraz długich wartości `Text`/`String` (od 256 znaków `String`
  jest zamieniany na `TEXT`, a powyżej 4000 znaków wartość trafia do LOB). Wszystkie wartości w macierzy są krótkie.

## Legenda

| Znak | Znaczenie |
|:-:|---|
| = | drugie ładowanie nie tworzy nowej wersji typu |
| S | nowa wersja typu, typ definicji (np. `STRING`) bez zmian, zmienia się tylko podtyp (np. `STRING/Text`) |
| T | nowa wersja typu i faktyczna zmiana typu definicji (np. `INTEGER` na `STRING`) |
| ! | błąd zapisu |

## Wyniki

Kod przed zmianą z obserwacji 132 (15 bez nowej wersji, 34 nowe wersje, w tym wszystkie 34 to zmiana samego podtypu):

| istniejąca  drugie | String:abc | String:7 | Text:abc | Integer:5 | Decimal:5.5 | Number:5 | Boolean:true |
|---|:-:|:-:|:-:|:-:|:-:|:-:|:-:|
| String:abc | = | = | S | S | S | S | S |
| String:7 | = | = | S | S | S | S | S |
| Text:abc | = | = | = | S | S | S | S |
| Integer:5 | S | S | S | = | S | = | S |
| Decimal:5.5 | S | S | S | S | = | = | S |
| Number:5 | S | S | S | S | S | = | S |
| Boolean:true | = | = | S | S | S | S | = |

Kod po zmianie (15 bez nowej wersji, 31 nowych wersji: 25 zmian samego podtypu i 6 zmian typu definicji, 3 błędy):

| istniejąca  drugie | String:abc | String:7 | Text:abc | Integer:5 | Decimal:5.5 | Number:5 | Boolean:true |
|---|:-:|:-:|:-:|:-:|:-:|:-:|:-:|
| String:abc | = | = | S | S | S | S | S |
| String:7 | = | = | S | S | S | S | S |
| Text:abc | = | = | = | S | S | S | S |
| Integer:5 | T | S | ! | = | S | = | T |
| Decimal:5.5 | T | S | ! | S | = | = | T |
| Number:5 | T | S | ! | S | S | = | T |
| Boolean:true | = | = | S | S | S | S | = |

## Wnioski

1. **Najczęstsze źródło nowych wersji to podtyp, nie typ.** Definicja parametru jest rozróżniana parą (typ, podtyp).
   Podtyp pochodzi z deklaracji w żądaniu (`type="…"`). Po zmianie typ istniejącej definicji zwykle zostaje (np.
   `STRING`), ale podtyp z deklaracji (`Text`, `Integer`, `Decimal`…) różni się, więc powstaje nowa definicja i
   nowa wersja typu. Dotyczy to 25 z 49 par w kodzie po zmianie i 34 z 49 przed zmianą.
2. **Zachowanie jest niesymetryczne.** `Text` po `String` tworzy wersję (`STRING/Text`), a `String` po `Text`
   nie. Typy liczbowe po `Number` też nie (podtyp bierze się z istniejącej definicji), ale po `Integer` lub
   `Decimal` tak.
3. **Zmiana typu definicji (T) zachodzi tylko dla wartości, które nie pasują do istniejącego typu liczbowego**
   (obserwacja 132): `String:abc` oraz `Boolean:true` po definicji liczbowej. Wartość liczbowa w polu `String`
   zostaje w typie liczbowym, ale z podtypem `String` (obserwacja 133).
4. **`Text` po definicji liczbowej jest teraz odrzucany (!) z właściwym komunikatem.** Reguła `Pole[…]: Nie można
   zmieniać typu definicji z INTEGER na TEXT` istniała, ale klient widział tylko `Transaction silently rolled back`
   (obserwacja 136, naprawiona: wariant A). Przed zmianą z obserwacji 132 ten przypadek zapisywał tekst w definicji
   liczbowej (`INTEGER/Text`) bez błędu. `Text` jest specyficzny (powyżej 256 znaków, może być LOB `text/plain`), więc
   odrzucenie jest zamierzone.
5. **Wyszukiwanie po samej nazwie nie jest głównym źródłem problemu.** Wybór definicji dla pola używa nazwy, typu i
   podtypu. Główne źródła to podtyp z deklaracji żądania oraz definicje globalne (wspólne dla wszystkich typów), z
   kluczem `nazwa#wersja`.

Powiązane: obserwacje 128, 132, 133, 135, 136 w [obserwacje.md](obserwacje.md).

## Jak powtórzyć

`mvn -o test -pl mercury-srv -am -Duser=scichy-test -Dtest=TypeIdentificationMatrixTest`. Wiersze są w
`mercury-srv/target/test.log` (prefiks `MATRIX|`). Klasę pomija klucz
`test.skip.package.TypeIdentificationMatrixTest=true` w profilu testów.

Źródło: przebiegi `TypeIdentificationMatrixScenario` z 2026-10-31 oraz `CaseBusiness.encodeSimpleValue4NewType`.

## Jak czytać liczby (6 wobec 0)

Tabela zbiorcza zlicza 49 par według wyniku drugiego ładowania:

| Nagłówek | Znaczenie | Dobrze czy źle |
|---|---|---|
| bez nowej wersji | Drugie ładowanie pasuje do istniejącej wersji typu. | Dobrze. |
| nowa wersja, tylko podtyp | Powstaje nowa wersja typu, ale typ definicji jest ten sam (np. `STRING`), zmienia się tylko etykieta podtypu (`STRING/Text`). To szum bez zmiany treści. | Źle. Spadło z 34 do 25. |
| nowa wersja, zmiana typu | Typ definicji faktycznie się zmienia (`INTEGER` na `STRING` albo `BOOLEAN`). | Zależy od przypadku, patrz niżej. |
| błąd | Zapis odrzucony. | Zależy od przypadku, patrz niżej. |

Zmiana typu: 0 przed zmianą i 6 po niej to te same 6 par: `Integer`, `Decimal` albo `Number` jako istniejąca
definicja, a w drugim ładowaniu `String:abc` albo `Boolean:true`. Przed zmianą kod w ogóle nie zmieniał typu definicji,
tylko zostawiał liczbowy i zmieniał podtyp na `String` albo `Boolean`. Z kodu wynika, że wartość `abc` albo `true`
trafiała wtedy do definicji `INTEGER`. Wartości zapisanej w bazie nie odczytywałem, to wniosek z kodu. Po zmianie
(decyzja z obserwacji 132) typ definicji dostosowuje się do wartości, której nie da się zapisać jako liczba. Zero nie było
więc wynikiem lepszego rozpoznawania typu, tylko tym, że kod nigdy nie przyznawał, że typ się zmienił. Nie oceniałem
skutków zmiany typu definicji dla indeksu Lucene i wyszukiwania.

Błąd: 0 przed zmianą i 3 po niej to pary `Integer`, `Decimal`, `Number` jako definicja i `Text:abc` w drugim
ładowaniu. Przed zmianą `abc` było zapisywane w definicji liczbowej bez błędu, teraz zapis jest odrzucany regułą
(obserwacja 136).

Łącznie liczba par z nową wersją spadła z 34 do 31, a z błędem wzrosła z 0 do 3.

## Zasada „lepkiej definicji” (wdrożona 2026-10-31)

Decyzja autora po analizie macierzy: istniejąca definicja parametru jest „lepka”. Jeżeli wartość mieści się w jej
typie, zostaje definicja w całości (typ, podtyp, kontrolka) i nie powstaje nowa wersja typu. Typ zmienia się tylko,
gdy wartość się nie mieści, i tylko w stronę szerszą. Zawężenie jest pochłaniane (ignorowane), bez błędu.

| Istniejąca definicja | Przychodzi | Zachowanie |
|---|---|---|
| `STRING`, `TEXT` | dowolna wartość | pochłonięte (bez nowej wersji). Wartość od 256 znaków w `STRING` poszerza typ do `TEXT` istniejącym mechanizmem |
| `INTEGER`, `DECIMAL`, `DOUBLE`, `FLOAT`, `NUMBER` | wartość liczbowa | pochłonięte |
| `INTEGER` | wartość ułamkowa (`5.5`) | poszerzenie do `DECIMAL` (nowa wersja) |
| typy liczbowe | wartość nieliczbowa (`abc`, `true`) | wiążący jest typ zadeklarowany (nowa wersja, a gdy reguła typów zabrania zmiany: błąd z komunikatem) |
| `BOOLEAN`, `BOOLEAN_INTEGER` | `true`, `false`, `0`, `1`, nazwa lokalna (`tak`, `nie`) | pochłonięte |
| `BOOLEAN`, `BOOLEAN_INTEGER` | inny tekst | wiążący `String` (poszerzenie do `STRING`, nowa wersja) |
| `BOOLEAN`, `BOOLEAN_INTEGER` | inna liczba, `Text` | błąd reguły typów (`BOOLEAN` na liczbę lub `TEXT` jest zabronione) |
| pozostałe typy (`CURRENCY`, daty i in.) | | dotychczasowe zachowanie |

Implementacja: `CaseBusiness.fitToCurrentDefinition` (wynik `ABSORB`, `WIDEN` albo `DECLARED`) w gałęzi „przywracam
zmianę typu parametru”. Testy: `DeclaredTypeScenario` (12 przypadków, w tym odczyt zapisanej wartości z bazy).

### Wynik macierzy po wdrożeniu

| istniejąca / drugie | String:abc | String:7 | Text:abc | Integer:5 | Decimal:5.5 | Number:5 | Boolean:true |
|---|:-:|:-:|:-:|:-:|:-:|:-:|:-:|
| String:abc | = | = | = | = | = | = | = |
| String:7 | = | = | = | = | = | = | = |
| Text:abc | = | = | = | = | = | = | = |
| Integer:5 | T | = | ! | = | T | = | T |
| Decimal:5.5 | T | = | ! | = | = | = | T |
| Number:5 | T | = | ! | = | = | = | T |
| Boolean:true | T | T | ! | ! | ! | ! | = |

| Wynik | przed obs. 132 | po obs. 132 | po zasadzie lepkiej |
|---|:-:|:-:|:-:|
| bez nowej wersji (=) | 15 | 15 | 33 |
| tylko podtyp (S) | 34 | 25 | 0 |
| zmiana typu (T) | 0 | 6 | 9 |
| błąd (!) | 0 | 3 | 7 |

Zmiana typu (9): `Integer`, `Decimal`, `Number` po `String:abc` (3) i po `Boolean:true` (3), `Integer` po
`Decimal:5.5` (poszerzenie, 1) oraz `Boolean` po `String:abc` i `String:7` (2). Błędy (7): liczbowe i logiczna
definicja po `Text:abc` (4) oraz `Boolean` po wartości liczbowej (3), wszystkie z komunikatem reguły (np. `z BOOLEAN
na INTEGER`). Prognoza przed wdrożeniem zakładała ok. 35 par bez wersji. Dwie pary więcej poszły w zmianę typu
(`Boolean` po `String:abc` i `String:7`, bo wartości nie są logiczne), czego prognoza nie rozstrzygała.

Nie zbadano skutków dla indeksu Lucene i wyszukiwania: definicja `STRING` pochłaniająca wartość liczbową lub logiczną
nie daje wyszukiwania numerycznego na tym polu. Nie testowano też długich wartości ani typów spoza macierzy.
