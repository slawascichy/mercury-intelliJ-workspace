# Opisy pull requestów, zadanie 229

Gałąź `hgdb-229` w trzech repozytoriach. Kolejność merge: `mercury` (kod), `mercury-cmd` (pakiet i `mercury-transfer`), `mercury-docker` (obrazy, kompozycje). Wydanie lokalne `mercury` 3.0.4.19, obrazy `ibpm/mercury:mercury-hgdb-3.0.4.16`–`3.0.4.19` w Nexusie (`nexus.scisoftware.local:5000`). Szczegóły, pomiary i rekomendacja: `tasks/hgdb/229-…/TASK.md`.

## mercury (`hgdb-229`, 6 commitów, 23 pliki)

**Cel.** Skrócić czas, po którym zmiana jest widoczna w indeksach Lucene wszystkich węzłów klastra, i sprawdzić, czy przekazywanie gotowych dokumentów między węzłami (zadanie 118) się opłaca.

**Zmiany.**
- `updateIndex` sekretarza w fazach: przygotowanie dokumentów równolegle (odczyt spraw, mapowanie albo `take`, publikacja), wywołanie zwrotne (powiadomienie JMS i wybudzenie innych węzłów), zapis do indeksu (`CaseIndexerUpdateRunner`, `PreparedCaseDocuments`, `ICaseIndexer.prepareDocuments` i `writeDocuments`, `IDocumentsPublishedCallback`).
- Zapis do indeksu domyślnie jednym wątkiem (`mercury.lucene.indexer.writeThreads=1`; `0` przywraca dawne zachowanie): jeden segment na paczkę zamiast do 10, mniej `fsync` na dysku z 5 ms na synchroniczny zapis. Stały koszt zapisu i `commit` spadł z ok. 300–340 do ok. 110–130 ms.
- Sprawdzanie spraw paczki w aktywnych transakcjach równolegle (`findCasesInActiveTransactions`): u sekretarza ok. 257 → 74 ms dla paczki ok. 250 wpisów.
- Wiele wątków zapisujących do pamięci współdzielonej (`SharedStoreSupport`, `mercury.cache.luceneDocument.shared.writerThreads`, domyślnie 4); poprawny `flush()` oparty na liczniku oczekujących zapisów; liczniki czasu i odrzuceń.
- Powiadomienie innych węzłów po opublikowaniu dokumentów, przed własnym zapisem (`mercury.cache.luceneDocument.shared.notifyBeforeWrite`, domyślnie `true`).
- Logi: `Indeks:` (rozbicie czasu paczki), `Sekretarz:`, `Odbiorca:` (INFO od 20 wpisów, mniejsze DEBUG).
- Poprawka `mercury-lib`: `MLucSaveBufferLogicSupport` i `Case2CaseLogic` ustawiają kod typu w buforze indeksu (obserwacja 154, zadanie 226).

**Wynik** (klaster 3 węzły, Linux, przebieg 2, najpóźniejszy węzeł): paczka 100 spraw z jednego węzła 826 → 322 ms, 3 × 100 naraz 1654 → 549 ms (−60–67%), CPU hosta nie wyższe. Przekazywanie dokumentów jest nie wolniejsze niż M0, praca odbiorcy nad dużą paczką spada z 594 do 261 ms, CPU hosta o 0–14% niższe.

**Testy.** `CaseIndexerUpdateRunnerTest` (6), `CaseIndexerTransactionCheckTest` (5), `SharedStoreWritersTest` (4), `SharedLuceneDocumentStoreTest`, `SharedCaseObjectStoreTest`, `DatasetScenario` na prawdziwym indeksie; pomiary na klastrze: `mierz-indeks.py`.

## mercury-cmd (`hgdb-229`, 6 commitów, 7 plików)

- Pakiet instalacyjny 3.0.4.16–3.0.4.19 (`mercury.srv.version`).
- `mercury-transfer` (obserwacja 156): poprawiona nazwa klasy w `transfer-remote-context.xml`, `mercury.ws.service.list=source,target` w `transfer.properties`, `transferMetadata` pomija podtyp bez definicji w źródle zamiast kończyć się NPE; test `TransferActionMetadataTest`; nowy `mercury-transfer/README.md`.
- Przykład `context.xml` (`system-config-sample/linux`): `defaultAutoCommit="false"` dla `jdbc/MercuryDB` i `jdbc/MercuryDBCommon` (jak w serwerze dev).

## mercury-docker (`hgdb-229`, 5 commitów, 14 plików)

- Obraz 3.0.4.16–3.0.4.19 (Dockerfile, kompozycje, README, Helm).
- Szablon `context.xml.docker-init`: `defaultAutoCommit="false"` dla `jdbc/MercuryDB` i `jdbc/MercuryDBCommon`. Bez tego każda archiwizacja paczki bufora indeksu kończyła się błędem `PSQLException: Cannot commit when autoCommit is enabled` (`AbstractDAO.commitTransaction`) na MASTER-ze.
- Kompozycje dwu- i trzywęzłowa: `postgres-db` z `max_connections=400` (pule JDBC do 200 połączeń na węzeł; przy zapisie z kilku węzłów naraz błąd `too many clients already`), opis w README; wykres Helm: `postgres.maxConnections` (domyślnie 200 dla jednego węzła; nieprzetestowane, brak `helm` na maszynie roboczej).

## docusaurus-hgdb (`hgdb-229`, niezacommitowane, EN i PL)

- `docs/003_Architecture/003_Index_Lucene/index.mdx`: zaktualizowany opis „How it works” (fazy: przygotowanie i publikacja dokumentów, powiadomienie, zapis jednym wątkiem), nowe parametry w tabeli regionu, nowa sekcja „Performance of the index update” (rozbicie czasu paczki, zapis jednym wątkiem, równoległe sprawdzanie transakcji, dysk indeksu i test `fsync`, tabela czasu do indeksu przed i po zmianach, parametry, logi `Indeks:`, `Sekretarz:`, `Odbiorca:`).
- `docs/005_Configuration/Cache_configuration.mdx`: parametry `mercury.cache.luceneDocument.shared.writerThreads` i `notifyBeforeWrite`, odsyłacz do logów w sekcji Monitoring.
- Nowa strona `docs/005_Configuration/Database_connections.mdx`: pule połączeń węzła, limit `max_connections` PostgreSQL w klastrze, `defaultAutoCommit="false"`; wpis w spisie `docs/005_Configuration/index.mdx`.
- Wersje polskie w `i18n/pl/docusaurus-plugin-content-docs/current/` (te same pliki). Składnię MDX sprawdziłem kompilatorem `@mdx-js/mdx` (8 plików OK); pełnego `docusaurus build` nie uruchamiano (ciężki dla pamięci).

## Do zrobienia po merge

- Zaciągnąć `master` (`mercury`, `mercury-cmd`) i `main` (`mercury-docker`), zamknąć zadanie 229 na GitHubie, dopiero potem zakładać gałąź następnego zadania.
- Opcjonalnie: publikacja obrazów na Docker Hub i `hgdb.org` (tylko wydanie ostateczne), dopasowanie `maxTotal` w `context.xml` do limitu bazy (obserwacja 158), test wykresu Helm.
