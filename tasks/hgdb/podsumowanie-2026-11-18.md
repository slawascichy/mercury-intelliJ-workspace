# Podsumowanie 2026-11-18

## Wydane

- **`mercury` 3.0.4.29** (zadanie 219) razem z `poi-toolkit` **4.1.0.3**. Pakiet `mercury-install-package-3.0.4.29.POSTGRESQL.20261118.zip` i `poi-toolkit-4.1.0.3.zip` w Nexusie raw; obrazy `ibpm/mercury:mercury-hgdb-3.0.4.29` i `ibpm/poi-server:mercury-hgdb-3.0` w `nexus.scisoftware.local:5000`. Klaster `mercury-test` zaktualizowany (helm rewizja 13), tymczasowe nakładki usunięte.
- Wcześniej dziś (zatwierdzone i scalone): obserwacje 170 i 171, zadanie 056, CMIS z Bearer (wydanie 3.0.4.28).

## Zadanie 219 (wydajność generowania plików Excel): cel osiągnięty

Cel: 200 000 × 6 poniżej minuty. Pomiary na `mercury-test` (200 006 spraw, strony po 1000):

| Eksport | Na początku | Teraz |
|---|---|---|
| widoku (`T_Bench219`) | 60,7 s | **10,2 s** |
| spraw xlsx | ok. 18 min, bez pliku | **22–37 s** |
| spraw csv (nowy format) | nie było | **21–25 s** |

Zmiany (wszystkie w `mercury` 3.0.4.29 / `poi-toolkit` 4.1.0.3):
- **Widok:** strony po kluczu (`ViewKeyColumn`, `ICaseViewDefinitionLogicInternal.readViewDataAfterKey`), bez `COUNT(*)` i `OFFSET` przy każdej stronie.
- **Sprawy:** `ICasePageCursor` w `CaseSearcher` (zapytanie Lucene wykonuje się raz, strony są czytane z jego wyniku); `flush` + `clear` kontekstu trwałości po każdej stronie (auto-flush Hibernate rósł z liczbą przeczytanych encji); klucz pamięci podręcznej Lucene bez numeru strony.
- **Błędy:** `caseId` i `previousVersionId` w nagłówku eksportu miały typ LONG mimo tekstowych identyfikatorów (zapis pliku padał); ostatnia kolumna `dlc` w eksporcie spraw była o 1 za duża.
- **Format pliku:** argument `format` (`xlsx` domyślnie, `csv`) i `csvSeparator` w `prepareReportRequest`, parametry `fmt` i `csvsep` w POI, UTF-8 z BOM, separator `;`.
- **RMI:** odświeżanie klienta serwera POI (`PoiRmiInvoker`, obserwacja 115 ✅), porty RMI i `HOST_NAME` w chartcie.
- **Instrumentacja:** log `INFO` z czasami faz eksportu (odczyt, konwersja, zapis stron do POI, `commit`) dla widoków i spraw.
- **Pamięć serwera POI:** limit 5Gi i `MaxRAMPercentage=60.0` (przy 4Gi/65% `OOMKilled`, przy 4Gi/50% xlsx wolniejszy 3–20 razy przez GC); chart `mercury-docker` ma też requests i limits wszystkich komponentów.

Plik wynikowy sprawdzony (liczba wierszy, unikalność `mrc_caseId`, wartości, liczba kolumn dla CSV). Szczegóły w `tasks/hgdb/219-…/TASK.md`.

## Obserwacje

- ✅ 115, 170, 171, 173, 174, 176. Nowe: 172 (porty RMI i `localhost` w POI, do potwierdzenia w kompozycji), 175 (JavaSysMon CPU 0% na Kubernetesie), **177** (serwer POI trzyma wszystkie strony eksportu w pamięci do `commit`).

## Do wiedzy

- Obrazy pomocnicze mają zmienny tag `mercury-hgdb-3.0` i chart nie ustawia `imagePullPolicy`, więc węzeł Kubernetesa używa obrazu z pamięci podręcznej: po wysłaniu nowego obrazu POI trzeba wymusić pobranie (`imagePullPolicy: Always` albo usunięcie obrazu z węzła).
- Rozpakowany serwer `mercury/mercury-server/apache-tomcat/mercury/lib` jest utrzymywany ręcznie: przy zmianie wersji `poi-toolkit` trzeba podmienić tam jar, bo pakiet instalacyjny bierze `lib` stamtąd (pierwszy pakiet 3.0.4.29 miał 4.1.0.2). Katalog `releases/mercury-install-package-<wersja>` nie czyści się sam przed budową.
- Pobranie pliku eksportu przez URL wymaga sesji GUI (token Bearer daje stronę logowania); w testach plik czytany z poda POI.
- Gałąź `hgdb-219a` utworzona w `mercury`, `poi-toolkit` i `mercury-docker` (po scaleniu `hgdb-219`).

## Stan środowisk

- `mercury-test`: dane `Bench219` (200 007 spraw, typ i widok `t_bench219`) zostają do dalszych pomiarów; po zakończeniu 219 do usunięcia razem z namespace i obrazem `iptables-helper`.
- Lokalnie: `minor_version.txt` (`mercury`, `poi-toolkit`, `mercury-cmd`) zmieniony przez wydania, nie do commita przeze mnie.
