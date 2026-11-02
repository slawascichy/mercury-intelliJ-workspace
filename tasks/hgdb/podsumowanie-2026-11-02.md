# Podsumowanie pracy, 2026-11-02

Gałąź `hgdb-049` (`mercury`, `mercury-lib`, `docusaurus-hgdb`). Plan dnia: `plan-2026-11-02.md`. Wszystkie zmiany poza repozytorium workspace zatwierdził autor w trakcie dnia (zmiany z zadania 082 i dokumentacji ActiveMQ czekają na zatwierdzenie, patrz „Do zatwierdzenia”).

## Statusy zadań

| Zadanie | Status | Co zostało |
|---|---|---|
| **222** Panel monitorowania sekretarzy | ✅ **zamknięte** (API, OpenAPI, strona, test na dev; autor potwierdził działanie panelu) | opcjonalnie dodatkowe usługi dla `caseMigrator` i raportów, jeśli pojawi się kolejka do pokazania |
| **082** Dynamiczne budowanie odbiorców ActiveMQ | ✅ **zamknięte** (Virtual Topic, DLQ dla paczek indeksu, test na żywo z `node3`, dokumentacja, przykład w `mercury-cmd`) | brak testu z prawdziwą „trucizną” dla DLQ; czyszczenie starych kolejek `…-node1/-node2` |
| **114** Sekretarz indeksu, bufor hurtowy | funkcjonalnie zamknięte (wcześniej), dziś doszedł test z panelem (100 tys. wpisów, bufor opróżniony po 147 s) | pomiar skanu przy 1 mln wierszy, źródła masowe (migracje, propagacja typów), Oracle/MSSQL/MySQL, klucze w profilu `scichy` |
| **049** CMIS | etapy 1–2 działają, **wydajność zamknięta** (poniżej) | testy uprawnień (`mrc-user`), Workbench/Atom, etap 3 (`checkOut`/`checkIn`) |
| **JOIN FETCH / N+1** (program z 049) | ✅ zrealizowane, raport `docs/raport-join-fetch-2026-11-02.md` | `Type2Type`, `CaseDocument`: ocena na większych danych; REST katalogu niezmierzony |
| **113** Podgląd zapytań Lucene | dodane do planu, **rozpoczęcie jutro** (plan na 2026-11-03) | całość |

## Co zrobiono

### Wydajność CMIS i warstwy danych (049)

- `createFolder` przy 3250 dzieciach w folderze głównym: **3,7 s → 0,10–0,12 s**; `getObjectByPath` 2,8 s → 0,03–0,07 s; `getChildren` (wszystkie 3250) 2,28 s → 0,42 s, strona 100 z początku 0,21 s → 0,08–0,10 s.
- Program `JOIN FETCH`: `CaseCatalog` (3258 → 3 zapytania), `Case`, `TypeCase` (listy typów 13 → 1), `TypeParam` (N+1 → 1), hook `getIdListFetchJoins` w DAO, `hibernate.default_batch_fetch_size=50`.
- **Pamięć zapytań a encje `@Cacheable(false)`**: trafienie w cache zapytań dawało N+1. `DAOSupport` nie ustawia już `cacheable` dla zapytań z encjami bez pamięci 2. poziomu (`findByIdList(1000)` w 2. wywołaniu: 1000 → 25 zapytań, 656 → 83 ms). Zmiana globalna, zatwierdzona.
- Sondy `JoinFetchStatsScenario` (12 encji), raport i `docs/analiza-join-fetch-zapytan-nazwanych.md`.
- Dane pomiarowe CMIS: skrypt `scripts/seed_cmis_folders.sh` i `docs/dane-pomiarowe-cmis.md` (3250 folderów w 2,5 minuty).

### Test krytyczny `WsServerTest.testMERC_0168_Scenarios` (obserwacja 141 ✅)

Padał także bez moich zmian i bez Tomcata; baseline z kodu sprzed prac też padał. Przyczyna: wyścig między `update` typu a asynchronicznym odbiorcą JMS ustawiającym flagę odświeżenia (z pauzą 3 s test przechodził). Poprawka w kodzie: `TypeCaseRegistryChanges` ustawia flagę lokalnie po zatwierdzeniu transakcji. Test przechodzi 3 razy z rzędu.

### Panel sekretarzy (222)

- Warstwa biznesowa `org.mercury.business.secretaries` (stan: czy pracuje, rozmiary buforów z tabel o znanym przeznaczeniu; indeks: bieżący, hurtowy, archiwum).
- `POST /rest/service/SecretariesRest/getSecretariesState`; kontroler `SecretariesRest` przemianowany na `SecretariesExtRest` (generator OpenAPI obejmuje tylko `*ExtRest`), 28 kluczy opisów w 6 językach (translator Gemini), test pokrycia OpenAPI.
- Zaplecze `SecretariesPanelController` (`/admin/secretaries`, sesja + `mrc-sysadmin`, `web.xml`), strona `static/admin/secretaries.html`, link na `index.jsp`, klucze w 12 plikach tekstów.
- Test pod obciążeniem: bufor hurtowy 100 tys. wpisów opróżniony po 147 s (ok. 680 wpisów/s), bufor bieżący 0, wpisy bieżące przetworzone po 0,25–1 s.

### ActiveMQ: Virtual Topic (082)

- Eksperymenty na wbudowanym brokerze 5.16.4 (`tasks/hgdb/082-…/eksperymenty/`): wildcard w `forwardTo` → `StackOverflowError`; Virtual Topic działa; `selectorAware=true` gubi wiadomości dla węzła offline; samo zamknięcie połączenia bez `recover()` nigdy nie kieruje wiadomości do DLQ.
- `activemq.xml`: 7 `compositeQueue` zastąpiła jedna reguła `virtualTopic`. Kod `mercury-srv`: tematy `VirtualTopic.mrc-*`, kolejki `Consumer.<węzeł>.VirtualTopic.mrc-*`, własne wiadomości pomijane w aplikacji, DLQ po 5 doręczeniach (obserwacja 138 ✅), obserwacja 139 ✅.
- **Test na żywo:** `node3` (nieznany w dawnej konfiguracji) dostał zmianę bieżącą w indeksie po 0,5–1,4 s, bufor hurtowy 5000 wpisów opróżniony w 9 s.
- Dokumentacja: nowa strona `docusaurus-hgdb` „Configuration and integration with Apache ActiveMQ” (EN i PL), przykład `mercury-cmd/.../system-config-sample/linux/apache-activemq` (`activemq.xml`, `README.txt` → `README.md`, hasło i IP zastąpione placeholderami).

### Inne

- Obserwacje 138–141 w `docs/obserwacje.md`; pamięć: `mercury-db` należy do autora, Tomcat nie jest infrastrukturą, optymalizacja całościowa.
- Błąd własny: testy `mercury-dao` uruchomione bez `-Duser=scichy-test` wyczyściły `mercury-db` (zgłoszone autorowi; autor odpowiada za te dane).
- Narzędzie poleceń Bash przetwarza sekwencje `\uXXXX` w tekście polecenia: pliki `WebAppMsg_*.properties` z escapami wymagają zbudowania ukośnika w zmiennej (`B=$(printf '\134')`).

## Do zatwierdzenia i commitu (autor)

- `mercury`: zmiany zadania 082 (`mercury-srv/.../jms/*`, `JmsDestinations`, `jms-configuration.xml`, `JmsDestinationsTest`, `BulkClusterScenario`), `mercury-ws-app` (panel sekretarzy, OpenAPI, teksty, strona), `mercury-srv` (stan sekretarzy); `mercury-server/apache-activemq-5.16.4/conf/activemq.xml` (poza gitem, kopia `activemq.xml.bak-082-20261102`).
- `mercury-cmd`: `system-config-sample/linux/apache-activemq` (`activemq.xml`, `README.md`, usunięty `README.txt`).
- `docusaurus-hgdb`: `ActiveMQ_configuration.mdx` (EN, PL), oba `index.mdx`.
- workspace: ten plik, `plan-2026-11-03.md`, zmiany `TASK.md`, `plan-2026-11-02.md`, `docs/obserwacje.md`.
- Zalecenie: zmienić hasło PostgreSQL ActiveMQ, które było w starym `README.txt` w historii gita.

## Stan środowiska na koniec dnia

- Tomcat dev na `mercury-db-test` z WAR z Virtual Topic; ActiveMQ z nową konfiguracją; w `mercury-db-test` ok. 5 tys. spraw (zestaw CMIS 3250 folderów + `SlmAddress` z testów); `mercury-db` (profil `scichy`) w gestii autora.
- Klucze `test.skip.package.*` w `scichy-test` przywrócone po testach.
