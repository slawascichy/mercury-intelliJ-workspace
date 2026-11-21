# Podsumowanie 2026-11-21

## Wydane

- **`mercury` 3.0.4.33** (PR #253, tag), **`mercury-cmd` 3.1.4.10**, **`mercury-docker` 3.0.4.33** (PR #14, tag, merge po zbudowaniu pakietu i obrazów). Wydania robi autor.
- **Pakiet i obraz** (przygotowałem i wysłałem do Nexusa): `mercury-install-package-3.0.4.33.POSTGRESQL.20261121.zip` (repozytorium raw `mercury-docker-packages`, 136 821 263 B, zgodny z lokalnym; weryfikacja Ant przeszła, w `libExt` jest `picocli-4.7.7.jar`, `Implementation-Version` 3.0.4.33) i obraz `ibpm/mercury:mercury-hgdb-3.0.4.33` (digest `sha256:4a5a12d2…`). `mercury-lb` i obrazy pomocnicze bez zmian.
- **Klaster `mercury-cluster`:** `helm upgrade` (rewizja 7) na obraz bez nakładek jarów; trzy węzły ONLINE, role `node1` MASTER, `node2` i `node3` SLAVE, API przez LB zwraca `"version":"3.0.4.33"`. Dla `node2`, który robił restore przed poprawką, zapisałem ręcznie `lucene-index-selected.properties` (`lucene.base.indexDir2`), inaczej po wymianie poda wróciłby do pustego `index`.
- **Dokumentacja w `docusaurus-hgdb`** (gałąź `hgdb-211d`, bez commitu, 6 plików, budowanie en i pl bez ostrzeżeń): artykuł `Kubernetes_installation` (wymagania klastra, dwa wykresy, klaster trzech węzłów, notka o `kubeadm token create --print-join-command`, skrypt `containerd-nexus.sh`, nowa kolejność startu, utrzymanie) i `Lucene_index_backup` (trwały wybór katalogu, znacznik SCN, ścieżki bezwzględne, ostrzeżenie o instalacjach sprzed 3.0.4.33), linki w `index.mdx` rozdziału 005.

## Zadanie 211c (chart klastra i poprawki kopii zapasowej)

- **Chart `mercury-three-node-cluster`** w `mercury-docker/charts` (trzy węzły: node1 MASTER, node2 i node3 SLAVE; własne `ehcache`, `poi-server` i wolumeny na węzeł; wspólne PostgreSQL, ActiveMQ, OpenLDAP i nginx). Znalezione i poprawione przy teście na klastrze: port 4000 w usługach węzłów (replikacja sesji Tomcata, bez niego GUI prosiło o logowanie po zmianie węzła), czekanie węzłów 2 i 3 na odpowiedź HTTP węzła 1 (otwarty port 8080 nie wystarczał).
- **`lucene.properties` obrazu** (obs. 198): `lucene.backup.index.desc.file.dir=/backupDesc` było korzeniem systemu plików kontenera, więc `index-backup` kończył się błędem `LC016`; teraz ścieżki bezwzględne na wolumenie `lucene` (obraz) i względne w domyślnym pliku `mercury-srv`.
- **Znacznik SCN indeksu** (obs. 200, `CaseIndexScnWatermark`): w danych commitu Lucene, podnoszony tylko przez wyrównanie z archiwum; odbiorca JMS pomija wpisy o SCN nie większym niż znacznik. **`writeDocuments` zawsze `updateDocument`** (zapis idempotentny, bez `searchById`); wydajność bez zmiany (6,67 ms zapisu na wpis przed i po, ok. 40 tys. wpisów).
- **Trwały wybór katalogu indeksu po restore** (obs. 199, `IndexDirSelectionStore`, `LuceneConfig`): plik `lucene-index-selected.properties` obok katalogów indeksu, stosowany przy starcie z pierwszeństwem przed `lucene.properties`. Poprzednio po restarcie Tomcata węzeł wracał do indeksu sprzed restore. Sprawdzone na K8s.
- **Test pod obciążeniem** (ok. 66 spraw/s przez LB, backup i restore na MASTER-ze, 44 200 spraw): 0 błędów po stronie klienta, `numDocs` równe liczbie różnych id na trzech węzłach (88 229), restore trwał 628 s (limit 600 s dogonienia, zgodnie z projektem), po restarcie węzeł zostaje przy odtworzonym indeksie.
- Testy jednostkowe: `CaseIndexScnWatermarkTest` (14), `IndexWriterUpdateDocumentTest` (4), `CaseIndexArchiveAlignerTest` (6), `IndexDirSelectionStoreTest` (7); wszystkie przechodzą.

## Obserwacje

- ✅ **198** (domyślna ścieżka opisu kopii), ✅ **199** (wybór katalogu indeksu znikał po restarcie), ✅ **200** (powtórne zastosowanie paczek JMS i zawodne „dodaj albo zaktualizuj”).
- Nowa otwarta: **201** (`fieldMetricQuery` zlicza także dokumenty usunięte i obcina wynik do 10 000 wartości bez `maxResults` w `Context`).
- Wymagają decyzji autora jak wcześniej: **195** i **148**.

## Do wiedzy

- **Mój błędny wniosek o „duplikatach”:** zapytanie zliczające (`fieldMetricQuery`) liczy usunięte, jeszcze niescalone dokumenty, więc „+3091” i piłokształtny przebieg liczby dokumentów nie były dowodem na żywe duplikaty. Odczyt indeksu (program na Lucene: `numDocs` i żywe dokumenty dla id z `docFreq > 1`) pokazał 0 żywych duplikatów; po poprawce `node1` ma 25 usuniętych dokumentów (24 sprawy zapisane dwa razy przy restore, bez skutku dla danych). Błędnie też twierdziłem, że stronicowanie jest ignorowane: obiekt `page` ma pola `number` i `size`, a ja wysyłałem `pageNumber` i `pageSize`.
- **Instalacje, które robiły restore przed 3.0.4.33,** po aktualizacji obrazu wróciłyby do starego indeksu: przed aktualizacją trzeba ręcznie zapisać `lucene-index-selected.properties` (opis w artykule `Lucene_index_backup`).
- **Klaster:** na klastrze zmieści się tylko jedna kompozycja naraz (jednowęzłowa albo trzywęzłowa); wymagania (decyzja autora): single = master 4 GB + 2 × worker 8 GB, three = master 4 GB + min 4 × worker 8 GB, worker 64 GB dysku, master dodatkowy dysk min 256 GB na NFS. Nowe workery wymagają `hosts.toml` i `config_path` containerd dla rejestru po HTTP (`containerd-nexus.sh`).
- **Pułapki procedury:** `sed` zamieniający domenę w pliku wartości zmienił też adres rejestru (`nexus.bojano.local` nie ma `hosts.toml`), a pod czyszczący NFS musi działać jako root, bo pliki nginx należą do roota.
- **Dane `Bench211`** (ok. 88 tys. spraw w bazie klastra) zostają do pomiarów wydajnościowych i jakościowych (decyzja autora).

## Stan środowisk

- `mercury-cluster` (Kubernetes): 3.0.4.33, wszystkie pody `Running`, role jak wyżej; `mercury-test` wyłączony (deploymenty skalowane do 0, dane na NFS, ostatnio 3.0.4.31). Nakładki jarów usunięte razem ze starymi podami; wpisy OAuth w `commandLine.properties` (do `mercury-cmd` w podach) też, trzeba je wpisać ponownie przy kolejnym teście kopii.
- Nexus: pakiet i obraz 3.0.4.33.
- Lokalnie: `mercury-docker` na `main` (PR #14), `mercury` na `master` (PR #253), `docusaurus-hgdb` na gałęzi `hgdb-211d` z 6 niezacommitowanymi plikami; workspace ma 1 niewypchnięty commit i niezacommitowane `README.md`, `docs/moduly/mercury-docker.md`, podsumowanie i plan.
