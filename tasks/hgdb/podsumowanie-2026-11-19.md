# Podsumowanie 2026-11-19

## Wydane

- **`mercury-lib` 3.0.4.25** (DTO widoków: `afterKey`, `countMode`, `useSnapshot`, `snapshotToken`, `nextKey`, `hasNext`), **`poi-toolkit` 4.1.0.4** (strumieniowe czytniki xlsx i csv), **`mercury` 3.0.4.30**, **`hgdb-client-open` 3.1.4.25**, **`mercury-cmd` 3.1.4.7**.
- `mercury-docker` (gałąź `hgdb-219a`): wersje 3.0.4.30 / `poi-toolkit` 4.1.0.4, chart z `image.mainTagPullPolicy` (domyślnie `Always` dla obrazów z ruchomym znacznikiem). Pakiety w Nexusie raw: `mercury-install-package-3.0.4.30.POSTGRESQL.20261119.zip`, `poi-toolkit-4.1.0.4.zip`. Obrazy w `nexus.scisoftware.local:5000`: `ibpm/mercury:mercury-hgdb-3.0.4.30` i `ibpm/poi-server:mercury-hgdb-3.0`.
- Kubernetes `mercury-test`: `helm upgrade --force` (rewizja 14), nakładki usunięte (jary w `upload/override`, nadpisane polecenie, dev-jar POI). Kompozycje na devops-box robi autor.
- `docusaurus-hgdb` (gałąź `hgdb-219a`): strona „Views” (en i pl) o odczycie po kluczu, migawce kluczy i formacie csv eksportu.

## Zadanie 219 zamknięte

Cel osiągnięty; pełna tabela wyników w `tasks/hgdb/219-…/TASK.md` („Zamknięcie zadania”). Dziś dodatkowo:
- **Podgląd widoków (warstwy 2 i 3):** odczyt po kluczu (`afterKey`, `countMode=NONE`, `hasNext`) i migawka kluczy z tokenem (`useSnapshot`, limit 50 000 kluczy, TTL 300 s); strona z głębi 200 000 wierszy 540–570 ms → 30–100 ms.
- **`saveList`:** z 120 do ok. 250 spraw/s (u klienta; ok. 380 na serwerze) na zestawie Kwartał→Miesiąc→Faktura→Pozycja. Kolejne kroki: zbiorcze „ostatnie zmiany” zamiast JMS na sprawę (−18%), tryb `COMMIT` w wątkach zapisu (−38%), identyfikacja typu z menedżerów typów i definicje typu w indeksowaniu z pamięci (odczyty `IGO_DA_TYPEPARAMETERS` 10 759 → 221), `FreshCaseIds` (−3%). Zapis z `findByPKProperty` nie wymagał zmian (ok. 2% czasu).
- **Tłumaczenia OpenAPI:** 7 nowych kluczy w 6 językach (de, es, fr, ko przez `localizer.py`), raport bez braków.

## Obserwacje

- ✅ 188, 189, 190, 191; ❌ 184 (wycofana: `CREATE VIEW` sam odrzuca powtórzone nazwy kolumn). Nowe otwarte: **193** (`install.sh` serwera POI ma kasować starsze `poi-toolkit-*.jar` z `release/lib`), **194** (`install.sh` `mercury` ma podmieniać `poi-toolkit` w `apache-tomcat/mercury/lib`), **185** (przedział sekwencji 100), **186** (rejestr transakcji w Terracotcie na sprawę), **187** (nginx `HTTP 413` powyżej ok. 10–20 MB), **192** (restarty kontenera POI po starcie).

## Do wiedzy

- **Pakiet `mercury` 3.0.4.30 miał `lib/poi-toolkit-4.1.0.3.jar`**, a serwer POI 4.1.0.4. Na życzenie autora podmieniłem jar w kopii pakietu (ten sam plik zip, `lib/poi-toolkit-4.1.0.4.jar`), wysłałem ją do Nexusa raw (`--force`) i przebudowałem oraz wysłałem obraz `ibpm/mercury:mercury-hgdb-3.0.4.30` (nowy digest `a464ac76…`); w obu obrazach jest tylko `poi-toolkit-4.1.0.4.jar`. Autor przebudował potem oficjalny zip i katalog `releases/mercury-install-package-3.0.4.30` (4.1.0.4); zawartość identyczna z moją kopią (388 plików, te same sumy CRC), więc obraz nie wymagał przebudowy, a do Nexusa wysłałem oficjalny zip (`--force`) dla zgodności bajtowej. Chart ma `image.hgdbTagPullPolicy` (na klastrze `Always`, bo obraz o tym samym znaczniku wysłano ponownie); helm rewizja 15.
- Pobranie bazowego obrazu `eclipse-temurin:8-jdk-ubi9-minimal` przez proxy Nexusa (port 5001) kończy się przekroczeniem czasu: obrazy zbudowane z bezpośrednim pobraniem z Docker Hub (bez `--bases-from`).
- Import: plik wgrany przez REST ma uprawnienia 640 (właściciel `mercury`), serwer POI (uid 998) go nie przeczyta: `chmod 644` w podzie `mercury-node1` (obserwacja 180).
- `hibernate.cache.use_query_cache=false` (`classes/mercury-ws-app/database-postgresql.properties`) dało tylko ok. 4%, zostaje włączone.

## Stan środowisk

- `mercury-test`: `mercury` 3.0.4.30, `poi-server` 4.1.0.4; dane `Bench219` (220 007 spraw) i zestaw `Quarter`/`Month`/`Invoice` (ok. 8000 spraw) zostają (analityka zapytań grupujących).
- Lokalnie niezacommitowane: `mercury` (`openapi*.json`, `openapi-docs_*.properties`), `mercury-docker` (wersje, chart), `docusaurus-hgdb`, `mercury-intelliJ-workspace` (`docs/obserwacje.md`, `TASK.md`, podsumowanie, plan).
