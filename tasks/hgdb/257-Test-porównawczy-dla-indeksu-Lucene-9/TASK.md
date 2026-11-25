# [257] Test porównawczy dla indeksu Lucene 9

https://github.com/slawascichy/hgdb/issues/257

Zadanie 191 podniosło Lucene z 7.5.0 do 9.12.3 (razem z przejściem serwera na Javę 17). Port jest zweryfikowany funkcjonalnie
(testy jednostkowe, `live4.sh`, zapytania na klastrze zgodne z bazą), ale **nie jest zmierzony pod kątem wydajności ani zgodności
wyników na dużym indeksie**. To zadanie ma odpowiedzieć na pytania: czy zapytania zwracają te same wyniki, czy są szybsze albo wolniejsze,
ile trwa budowa indeksu i ile zajmuje, oraz czy trzeba przestroić parametry (próg `CostOptimizer`, `maxHits`, pamięć).

## Kontekst (stan na 2026-11-25)

- **Punkt odniesienia z zadania 119:** `tasks/hgdb/119-*/baseline-2026-10-25.csv` (41 zapytań kalibracji na indeksie INEA 3.0, 22 mln dokumentów,
  tryby `cost`, `rootFirst`, `none`; wyniki zgodne we wszystkich trybach), wyniki końcowe `koncowy-przebieg-2026-10-26.csv`,
  `koncowy-wspolbieznosc-2026-10-26.csv`, opis `podsumowanie-koncowe-2026-10-26.md`. Pomiar: Lucene 7.5.0 na Javie 8.
- **Indeks INEA 3.0** (kopia robocza `F:\mercury-indexes\20190705_Case_3.0`, oryginał `H:\mercury\20190705_Case_3.0`) jest w formacie Lucene 7.
  **Lucene 9 go nie otworzy** (`IndexFormatTooOldException`: obsługuje tylko indeksy utworzone w wersji 8.0 lub nowszej), a `IndexUpgrader`
  tego nie naprawia (zmienia segmenty, ale nie wersję, w której utworzono indeks, przypuszczenie z dokumentacji Lucene, do sprawdzenia).
  Do porównania na danych INEA trzeba więc zbudować nowy indeks z bazy (komenda `generate-lucene Case`).
- **Zmienne, które zmieniły się razem:** wersja Lucene (7.5.0 do 9.12.3) i JDK (8 do 17). Wersja `mercury` 3.0.4.44 działa na Javie 17
  z **Lucene 7.5.0**, a 3.0.4.45 na Javie 17 z **Lucene 9.12.3**, więc te dwie wersje pozwalają wyodrębnić wpływ samego Lucene.
- **Zmiany w kodzie portu, które mogą wpływać na wydajność** (do zmierzenia, nie zakładać): kolektory z `scoreMode` (`COMPLETE` albo
  `COMPLETE_NO_SCORES`), `ExactTotalHitsSearch` w zagnieżdżonych wyszukiwaniach dzieci (dokładne zliczanie wyłącza wczesne zakończenie
  przy przekroczeniu progu 1000 trafień), `LowerCaseFilter` w analizatorze (dawniej `normalize` w tokenizerze), `GenericTermsCollector`
  w `LuceneJoinUtil` (dawniej własne kolektory z `binaryDocValues`).
- **Znane zmiany zachowania Lucene 9** (do sprawdzenia w wynikach): `StandardAnalyzer` bez domyślnej listy słów pomijanych (od Lucene 8),
  zmiana wartości `score` (nowe formuły i normy), `totalHits` jako dolne ograniczenie po przekroczeniu progu.
- **Dane dostępne od razu:** klaster `mercury-cluster` ma 89 838 spraw (w tym `Bench211`: 89 828). Budowa indeksu Lucene 9 z tych danych:
  555 s, 14 MB, 0 błędów (opis w `tasks/hgdb/plan-2026-11-25.md`). Dla Lucene 7.5.0 takiego pomiaru budowy nie ma.

## Decyzja autora (2026-11-25): migrator indeksu do HgDB

Bazy INEA, z której powstał indeks, nie ma. Zamiast danych syntetycznych robimy **migrator indeksu Lucene do HgDB**:

1. Migrator czyta stary indeks (Lucene 7.5, osobne narzędzie z własnym classpathem, bo serwer ma już Lucene 9).
2. Z pól indeksu tworzy **typ** w HgDB (atrybuty z nazw i typów pól oraz znanych „joinów” między sprawami).
3. Ładuje sprawy do nowej bazy relacyjnej HgDB. W bazie pojawią się **tylko pola, które zostały przechowane w indeksie** (`stored`);
   pola tylko indeksowane są nie do odtworzenia.
4. Z tak zasilonej bazy budujemy indeks Lucene 9 (`generate-lucene Case`), a dla wariantu (b) także indeks Lucene 7.5 (`mercury` 3.0.4.44),
   z tych samych danych.

**Konsekwencja dla porównania:** dane po migracji nie są identyczne z oryginalnym indeksem INEA (brak pól tylko indeksowanych, być może podzbiór
spraw), więc wyniki nie będą wprost porównywalne z `baseline-2026-10-25.csv`. Porównanie robimy między wariantami (b) i (c) na tych samych
zmigrowanych danych; wariant (a) zostaje punktem orientacyjnym.

### Co wiadomo o indeksie INEA 3.0 (odczyt kopii `F:\mercury-indexes\20190705_Case_3.0\Case`, Lucene 7.5, tylko nazwy pól, bez wartości)

- 22 028 880 dokumentów (spraw), 25 segmentów, `indexCreatedVersionMajor` = 7 (czyli Lucene 9 odmawia otwarcia, potwierdzone), brak znacznika SCN w danych commitu.
- 624 pola, z tego 417 indeksowanych, 207 punktowych (zakresy liczbowe i daty); doc values: `SORTED_SET` 353, `SORTED_NUMERIC` 206, `SORTED` 11, brak 54.
- Konwencja nazw pól: `<atrybut>_S` (tekst jako pojedyncza wartość), `<atrybut>_N` (liczba), `<atrybut>_T` (tekst analizowany), `<pole>_mrc_Case_id`
  (powiązanie ze sprawą podrzędną: 37 takich pól, to są „joiny”), pola systemowe `mrc_*`.
- W próbce 400 losowych dokumentów występuje 325 różnych pól przechowywanych (`stored`), czyli większość, ale nie wszystkie z 417 indeksowanych.
- Do ustalenia przy projekcie migratora: które pola `stored` odpowiadają jakim atrybutom typu (relacja `_S` i `_N` tego samego atrybutu), jak odtworzyć
  hierarchię spraw z pól `*_mrc_Case_id`, jak odtworzyć typ sprawy (pole z kodem typu), co zrobić z polami wielowartościowymi i z datami (punkty vs wartości przechowane).

### Cel dodatkowy: zanonimizowany zestaw danych „z życia” jako trwały zasób (uwaga autora 2026-11-25)

Jeżeli uda się zasilić HgDB taką ilością realistycznych danych (dziesiątki milionów spraw, rzeczywiste rozkłady, powiązania i typy), dostajemy zasób
użyteczny daleko poza tym zadaniem: testy wydajności i kalibracja Lucene (209, 119), partycjonowanie i wersje spraw (016, 218), import i eksport
(POI, `mercury-transfer`), kopie zapasowe i odtwarzanie indeksu, GUI i panele (096), przyszłe prace nad wyszukiwaniem. Istniejący zestaw z zadania 116
(`dataset.zip`, `DatasetScenario`) jest znacznie mniejszy i syntetyczny; nowy mógłby go uzupełnić.

Wynikające z tego wymagania wobec narzędzia i procesu (propozycja):

- **Poziomy zestawu zagnieżdżone:** małe (ok. 100 tys.), średnie (1-2 mln), pełne (22 mln), wybierane tym samym hasłem identyfikatorów korzeni
  (próg haszu), więc mały jest podzbiorem średniego, a średni pełnego. Deterministyczność i powtarzalność (ten sam klucz anonimizacji i wejście dają ten sam wynik).
- **Manifest zestawu:** skąd pochodzi (bez danych klienta), data, wersja narzędzia, skrót konfiguracji anonimizacji, liczby spraw i typów, pokrycie pól
  (które pola indeksu były przechowane, a które utracone). Dzięki temu wiadomo, do czego zestaw się nadaje.
- **Raport kontroli jakości po migracji:** liczba spraw i powiązań (czy nie ma osieroconych dzieci), porównanie z indeksem źródłowym, kontrola anonimizacji
  (skan wyniku pod kątem znanych wartości źródłowych), rozkłady wartości przed i po.
- **Dane tylko w sieci autora (warunek autora 2026-11-25, doprecyzowany).** Autor może użyć postaci zanonimizowanej jako zestawu testowego, ale **nie może jej
  dalej udostępniać**. Inni mogą użyć narzędzia, żeby przeprowadzić test na własnym źródle, a dane nie mogą wypłynąć poza sieć autora. Konsekwencje:
  - **dozwolone:** infrastruktura autora, w tym wewnętrzny Nexus (`nexus.scisoftware.local`, `*.bojano.local`: chroniony, niedostępny z zewnątrz), lokalny PostgreSQL,
    `D:\mercury`, klaster testowy (NFS). Zrzut bazy (np. `pg_dump`) albo pakiet eksportu HgDB może leżeć np. w osobnym repozytorium raw wewnętrznego Nexusa;
  - **zabronione:** git, **publiczny `nexus.scisoftware.pl`**, publikacje, wiadomości, raporty z wartościami. Wydanie 3.0.5.x (produkt bez danych) trafi na publiczny
    Nexus i do innych, więc **żaden artefakt wydania ani obraz produktowy nie może zawierać danych**: zestaw leży w osobnym repozytorium (osobne uprawnienia, bez
    promocji do wydania), a obrazy `ibpm/*` budujemy bez danych, także na wewnętrznym Nexusie, bo to z niego robimy wydanie;
  - **repozytorium na dane już jest** (autor 2026-11-25): `mercury-test-data` (raw, hosted, `writePolicy` ALLOW, blob store `default`, obecnie puste) na wewnętrznym
    Nexusie: `http://nexus.bojano.local:8081/repository/mercury-test-data` (przeglądarka: `http://nexus.bojano.local:8081/#browse/browse:mercury-test-data`).
    Konto `claude` widzi repozytorium (odczyt); zapisu nie sprawdzano. Repozytorium jest osobne od `mercury-docker-packages` (pakiety do budowy obrazów), więc
    wydanie nie obejmuje danych. Nexus działa po HTTP w sieci wewnętrznej;
  - zestaw dostaje w manifeście i opisie znacznik „nie do udostępniania”;
  - **narzędzie jest do udostępnienia** (trafi do wydania), bo nie zawiera danych: kod, testy i fixtury w repozytorium są wyłącznie syntetyczne, logi i komunikaty
    narzędzia zawierają nazwy pól i liczby, nigdy wartości, a dokumentacja opisuje, jak ktoś inny uruchamia je na własnym indeksie;
  - klucz anonimizacji po zbudowaniu zestawu jest nieodwracalny (klucz niezapisywany), jako dodatkowe zabezpieczenie przed skutkami przypadkowego wycieku
    (nie zastępuje zakazu udostępniania).
- **Pytanie prawne rozstrzygnięte w zakresie użycia:** użycie testowe zanonimizowanych danych tak, udostępnianie dalej nie.
- **Wniosek dla fazy próbki:** skoro zestaw ma być zasobem, pełne 22 mln też budujemy (próbka służy do rozwoju narzędzia i wstępnego A/B).

### Narzędzie `mercury-lu2hgdb` (decyzja autora 2026-11-25)

Nazwa modułu: **`mercury-lu2hgdb`** (nazwa robocza narzędzia: Lucene2Hgdb). Samodzielne narzędzie, które nie używa istniejących modułów
(`mercury-srv-cmd`, `mercury-transfer`), z **osobnymi classpathami dla każdej wersji Lucene**.

Wywołanie: `lu2hgdb <model> <wersja Lucene> <ścieżka indeksu>`, gdzie:

1. `model`: model indeksu, `2.0` albo `3.0` (od niego zależy mapowanie pól: np. powiązania `subCaseIds` w 2.0, `*_mrc_Case_id` w 3.0),
2. `wersja Lucene`: wersja, w której indeks powstał, na razie **`7` i `9`**; wersję 8 pomijamy (do dorobienia na zlecenie; Lucene 9 otwiera
   też indeksy utworzone w 8, więc argument `9` powinien je obejmować, do potwierdzenia testem),
3. `ścieżka`: lokalizacja katalogu indeksu (tylko odczyt).

Założenia projektowe (propozycja do zatwierdzenia):

- Odczyt za małym interfejsem; implementacje ładowane w osobnych classloaderach z katalogów bibliotek `lib7/` (Lucene 7.5.0) i `lib9/`
  (Lucene 9.12.x). Mapowanie pól (model 2.0 i 3.0) nie zależy od wersji Lucene.
- Walidacja argumentu wersji: przy niezgodności (`IndexFormatTooOldException`, `IndexFormatTooNewException`) czytelny komunikat zamiast śladu stosu.
- Opcje dodatkowe: dane docelowej instancji HgDB (adres, użytkownik), `--limit` (podzbiór), `--schema-only` albo `--dry-run` (sam typ bez ładowania),
  później wznawianie po awarii (22 mln spraw).
- Ładowanie przez klienta `hgdb-client-open` (bez własnego dostępu do bazy). **Główne ryzyko:** czy API pozwala utworzyć typ z listy pól;
  do sprawdzenia w kodzie przed projektem.
- Bez danych osobowych w kodzie, testach i dokumentacji (tylko nazwy pól i statystyki).
- **Test okrągły (ścieżka 9):** baza klastra -> indeks Lucene 9 (już zbudowany 2026-11-25: 89 838 spraw, 14 MB) -> `lu2hgdb` -> nowa baza -> porównanie
  z bazą źródłową (które informacje migrator gubi). Dla ścieżki 7 dostępne kopie: model 2.0 `F:\mercury-indexes\20190405_Case.2.0`, model 3.0
  `F:\mercury-indexes\20190705_Case_3.0`.
- Lokalizacja (autor): `D:\workspace\git\mercury-cmd\mercury-lu2hgdb` (katalog w repozytorium `mercury-cmd`; nie musi być modułem reaktora, może być).
  Kod powstaje w gałęzi nowego zadania (`hgdb-NNN`, po zamknięciu 191).
- **Wersje Lucene: dwie osobne dystrybucje** (decyzja autora 2026-11-25), każda z własnym classpathem; **wybór dystrybucji w skrypcie bash**
  (`lu2hgdb.sh <model> <wersja Lucene> <ścieżka>` wybiera katalog bibliotek i uruchamia `java -cp`), bez classloaderów i `ServiceLoader` z izolacją.
  Układ jak `API20`: **jeden interfejs i dwie implementacje**. Własny agregator Maven poza reaktorem `mercury-cmd` (żeby nie trafił do pakietu
  instalacyjnego i nie dziedziczył `lucene.version` 9.12.3):
  - `lu2hgdb-api`: interfejs `IndexSource` i dane neutralne (pola: nazwa, indeksowane, przechowane, typ doc values, wymiary punktów; dokumenty jako
    `pole -> wartości`), bez Lucene;
  - `lu2hgdb-core`: CLI (picocli), mapowanie modelu 2.0 i 3.0, ładowanie do HgDB; zależy tylko od `lu2hgdb-api`;
  - `lu2hgdb-lucene7` (Lucene 7.5.0) i `lu2hgdb-lucene9` (Lucene 9.12.x): implementacje `IndexSource`; kod odczytu musi być kompilowany osobno
    dla każdej wersji (API różnią się, np. `MultiFields` w 7, `FieldInfos.getMergedFieldInfos` w 9);
  - dystrybucje (`lucene7`, `lucene9`): `core` + `api` + jedna implementacja + jej Lucene; wspólny skrypt `bin/lu2hgdb.sh` z `case` po argumencie wersji.
  Nowa wersja (8, 10) to nowy moduł implementacji i nowa dystrybucja. Program sprawdza, że wersja z argumentu zgadza się z implementacją na
  classpathie, i przy niezgodności kończy się czytelnym komunikatem (dodatkowo do ochrony przed błędem skryptu).

### Ryzyka i pytania do autora

1. **Dane osobowe: anonimizacja (propozycja autora 2026-11-25, projekt do zatwierdzenia).** Indeks INEA zawiera dane osobowe (nazwiska, loginy, adresy).
   Migrator oferuje funkcję mieszającą (anonimizującą) wartości, więc zmigrowana baza nie zawiera danych osobowych. Założenia:
   - **mapowanie deterministyczne i różnowartościowe z kluczem:** ta sama wartość daje zawsze ten sam wynik, różne wartości różne wyniki, więc zachowane są
     równość, kardynalność terminów i długości list wystąpień (selektywność zapytań równościowych). Klucz losowy na przebieg (albo podany argumentem),
     tablicy mapowania nie zapisujemy, żeby nie dało się odwrócić;
   - **zachowanie „kształtu” wartości:** długość, klasy znaków (litery pozostają literami, cyfry cyframi), granice słów w polach tekstowych (mapowanie słowo po
     słowie), żeby analizatory, zapytania z `*` i rozkład długości terminów zachowały się podobnie. Zapytania prefiksowe i zakresowe po tekście nie będą
     zwracały tych samych wyników co na oryginale (ograniczenie, do opisania w raporcie);
   - **nie mieszamy:** identyfikatorów i powiązań (`*_mrc_Case_id`, klucze), dat i liczb używanych w zakresach, wartości słownikowych i systemowych (`mrc_*`, kody
     typów, statusy). Lista pól osobowych jest konfiguracją (plik właściwości z wzorcami nazw), a **domyślnie mieszane są wszystkie pola tekstowe poza
     białą listą** (bezpieczniej: pomyłka w konfiguracji nie ujawnia danych);
   - **zapytania:** zapytania kalibracji z danymi osobowymi (z `baseline-2026-10-25.csv`) nie są wprost użyteczne po anonimizacji; nowe zapytania generuje
     `QueryGenerator` (kalibracja, zadanie 209) z nowego indeksu, więc nie trzeba przekładać starych;
   - opcje: `--anonymize` (domyślnie włączona), `--no-anonymize` (tylko lokalnie, do diagnostyki), `--anonymize-key`, `--anonymize-config`.
   Anonimizacja zmniejsza ryzyko przy lokalnym użyciu, ale **zestaw nie może być udostępniany dalej** (warunek autora, patrz „Cel dodatkowy”). Rozkład wartości
   bywa sam w sobie identyfikujący dla rzadkich wartości (przypuszczenie), więc anonimizacja nie zastępuje tego zakazu.
2. **Skala: dwie fazy** (propozycja po uwadze autora o rozkładzie danych). Opcja `--max-documents N` w narzędziu (nazwa po konwencji długich opcji picocli).
   - **Do czego próbka wystarcza:** weryfikacja narzędzia (test okrągły, mapowanie pól, anonimizacja) i pierwsze porównanie wersji Lucene (b) kontra (c)
     na tych samych danych: różnica względna czasów jest wtedy miarodajna dla tej skali.
   - **Do czego nie wystarcza:** decyzja o progach `CostOptimizer` i kalibracja (`childFirstRatio`, `probeLimit`), bo zależą od **bezwzględnych** liczności
     (np. zapytanie z 1414 trafieniami na 22 mln dałoby ok. 130 na 2 mln, czyli inny reżim). Do kalibracji potrzebny jest pełny zbiór.
   - **Jak wybierać próbkę:** nie „pierwsze N” (dokumenty są uporządkowane czasowo, więc to zniekształca rozkład) i nie losowe dokumenty (zrywają powiązania
     rodzic-dziecko). Proponowana metoda: deterministyczna selekcja **korzeni** po haszu identyfikatora (stały ułamek, powtarzalna, bez dodatkowej pamięci)
     razem z całym poddrzewem spraw podrzędnych; `--max-documents` jest górnym limitem. Szczegóły zależą od tego, jak z dokumentu odczytać rodzica
     (do sprawdzenia przy projekcie).
   - **Wniosek:** próbka służy do rozwoju i wstępnego A/B, a ostateczny pomiar i decyzja o progach na pełnych 22 mln.
3. **Gdzie leży narzędzie:** rozstrzygnięte. `D:\workspace\git\mercury-cmd\mercury-lu2hgdb`, dwie dystrybucje wybierane skryptem bash. Narzędzie jest
   **etapem 0 zadania 257** (decyzja autora: bez niego zadania nie da się zrealizować, a pomysł wynika z samego zadania), więc jego implementacja
   należy do 257 i powstaje w jego gałęzi.
4. Na jakim sprzęcie mierzymy (lokalnie na Windows z dyskiem NVMe, czy na klastrze Kubernetes z NFS)? Wynik dla NFS jest inny niż dla dysku lokalnego.

## Plan (propozycja)

1. **Zakres porównania:** zbiór zapytań (41 z kalibracji), tryby planu (`cost`, `rootFirst`, `none`), współbieżność (`LuceneConcurrencyPerfTest`),
   budowa indeksu (czas, rozmiar, zużycie pamięci), zgodność wyników (liczba trafień i identyfikatory dla każdego zapytania).
2. **Macierz wariantów:** (a) Lucene 7.5.0 na Javie 8 (istniejący baseline z 119), (b) Lucene 7.5.0 na Javie 17 (`mercury` 3.0.4.44),
   (c) Lucene 9.12.3 na Javie 17 (`mercury` 3.0.4.45). Różnica (b) do (c) to czysty wpływ Lucene, różnica (a) do (b) to wpływ JDK.
3. **Dane:** baza HgDB zasilona migratorem z indeksu INEA (patrz „Decyzja autora”), a do kontroli także zestaw syntetyczny (`perf-100k`). Indeksy 7.x
   i 9.x budowane z tych samych danych, osobne katalogi, bez modyfikowania kopii roboczych na `F:\mercury-indexes` (odczyt tylko do odczytu).
   **Etap 0 (część zadania 257): implementacja `mercury-lu2hgdb`** (projekt w sekcji „Narzędzie `mercury-lu2hgdb`”): interfejs `IndexSource`, czytniki Lucene 7 i 9,
   mapowanie modeli 2.0 i 3.0, ładowanie do HgDB, dwie dystrybucje i skrypt, testy (w tym test okrągły ścieżki 9), pierwszy przebieg na podzbiorze, potem
   na całości. Pomiary (kolejne kroki planu) zaczynają się po etapie 0.
4. **Uruchomienie:** flagi i konfiguracja z notatki `pomiary-lucene-inea-flagi` (`-Dperf.query=true -Dperf.typeCodeLower=true
   -Dperf.maxResults=1000000`, konfiguracja `maxhits1m`, `-Xmx6g`); Terracotta (9510) i ActiveMQ (51616) startuje autor.
5. **Raport:** `porownanie-lucene-7-vs-9-<data>.md` i `.csv` w katalogu zadania (zbiorcze, bez danych osobowych z zapytań), z wnioskami:
   czy zostawiamy bieżące progi (`CostOptimizer`, `maxHits`), czy potrzebna rekalibracja (`kalibracja-przelicz.py` z 119).
6. **Poprawki wynikające z pomiaru** (np. rezygnacja z `ExactTotalHitsSearch` tam, gdzie dokładna liczba nie jest potrzebna, zmiana
   `totalHitsThreshold`) jako osobne, małe zmiany po zatwierdzeniu wyników.

## Kryteria akceptacji

- Raport z tabelą czasów per zapytanie i tryb dla wariantów (b) i (c) (oraz (a), jeśli baseline da się porównać) i wnioskiem.
- Zgodność wyników: dla każdego zapytania ta sama liczba trafień w wariantach (b) i (c); rozbieżności opisane i wyjaśnione (np. słowa pomijane).
- Czas i rozmiar budowy indeksu dla (b) i (c) na tych samych danych.
- Decyzja o progach `CostOptimizer` (zostają albo rekalibracja).
- Etap 0: działające narzędzie `mercury-lu2hgdb` (obie dystrybucje, skrypt `lu2hgdb.sh`): test okrągły ścieżki 9 pokazuje, które informacje migrator gubi;
  zmigrowane dane INEA (pełne albo podzbiór uzgodniony z autorem) w lokalnej bazie HgDB, z których powstaje indeks Lucene 9 i 7.5; dokumentacja użycia.

## Stan realizacji

- 2026-11-25: zadanie założone po porcie Lucene 9 (zadanie 191). Decyzja autora: migrator indeksu INEA do HgDB (brak bazy źródłowej).
  Odczytana struktura indeksu INEA (nazwy pól, bez wartości). Ustalony układ narzędzia `mercury-lu2hgdb` (dwie dystrybucje, jeden interfejs, dwie
  implementacje, skrypt bash) i jego miejsce: etap 0 zadania 257. Implementacja ruszy w gałęzi `hgdb-257` po zamknięciu 191 (PR i merge).
  Dane osobowe: anonimizacja (opcja narzędzia, projekt w pytaniu 1); skala: dwie fazy, próbka do rozwoju i wstępnego A/B, pełny zbiór do kalibracji
  (pytanie 2); oba projekty czekają na zatwierdzenie autora. Otwarte pytanie 4 (sprzęt pomiarów).
