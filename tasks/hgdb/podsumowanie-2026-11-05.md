# Podsumowanie 2026-11-05

## Zamknięte

- **226 Pomiar zapisu na Linuksie (Tomcat i Terracotta):** trzy etapy pomiarów na klastrze trzywęzłowym na `devops-box-01` (obrazy 3.0.4.15, klient zdalny), wnioski w `226-…/TASK.md` (sekcja „Podsumowanie i wnioski”).
  - CMIS: zapis ok. 100–130 ms (`createFolder`, `createDocument`), odczyt ok. 20–23 ms.
  - Sprawa `FSMServiceOrder` przez REST: `find` ok. 20–23 ms (poziom sieci), `save` ok. 70–74 ms.
  - Warianty B (lokalny region znaczników czasu) i C (bez pamięci zapytań) nie dały zysku względem A (różnice w rozrzucie, 2 przebiegi na wariant); **regiony klastrowe zostają**.
  - `minCostMs`: bez zmiany (25 ms); sprawa jest za tania, by pamięć współdzielona obiektów się włączyła; niższy próg wymaga pomiaru na droższych typach.
  - Propagacja do indeksów Lucene: ok. 1,0–1,1 s dla pojedynczej sprawy (dolna granica z cyklu sekretarza, przypuszczenie), przekazywanie dokumentów (M1) wydłuża czas do spójnych indeksów odbiorców: paczka 100 spraw ok. +70% (780–840 ms wobec 450–485 ms), 3 × 100 naraz ok. +40% (1,5 s wobec 1,1 s); MASTER szybszy o 110–250 ms. Zysk CPU odbiorców niezmierzony.
- **211a (procedura wydania i obrazy):** obrazy zaktualizowane do `mercury` 3.0.4.14, potem 3.0.4.15; pakiet instalacyjny w `mercury-cmd` zbudowany i wgrany do Nexusa (raw), wersje w `mercury-docker` ustawione, obraz `ibpm/mercury:mercury-hgdb-3.0.4.15` przetestowany (smoke test: jedno- i dwuwęzłowy, bicia serca) i wypchnięty do `nexus.scisoftware.local:5000` (digest `sha256:2bbd1c06…ab87a`, tagi `…3.0.4.14` i `…3.0.4.15`).
- **`AuthTest.testDataSource`:** użytkownik `ttesteusz` w lokalnym OpenLDAP, konfiguracja testu jak w innych testach (klient `GIUSoapUIClient`, `FrontendAccount`, użytkownik w grupie `mrc-admin`).

## Poprawki znalezione przy kompozycji trzywęzłowej (kod i konfiguracja)

- **Limit deskryptorów (`ulimits nofile`)** w trzech kompozycjach: przy ogromnym limicie JVM i glibc kończyły się błędem alokacji tablicy deskryptorów.
- **Dwóch MASTER-ów w klastrze:** `activemq.xml` w `mercury-docker` nie miał konfiguracji Virtual Topic z zadania 082, więc kolejki `Consumer.<węzeł>.VirtualTopic.…` nie dostawały bicia serca. Poprawione w trzech plikach (`<virtualTopic … prefix="Consumer.*.">`), test dymny sprawdza bicia serca na kolejkach węzłów.
- **Indeks Lucene w obrazie:** `initLucene` uznawał niepusty katalog `lucene` za zainicjowany (wystarczył `LicenseKey.txt`); teraz warunkiem jest zawartość `index/Case`.
- **Katalog `upload`** w obrazie należał do `root` (po `VOLUME`), serwer działa jako UID 1000: `createDocument` kończył się `FileNotFoundException`. Poprawiony `Dockerfile`; na hostach `chown -R 1000:1000`.
- **CMIS w obrazie:** `mercury.cmis.security.oauthClientId/Secret` zakomentowane w szablonie, więc CMIS odrzucał wszystko (401); dodane zmienne `CMIS_OAUTH_CLIENT_ID/SECRET` (kompozycje, `mercury-hgdb.env`, README, Helm), `mercury-server.sh` podstawia je w `mercury.properties`; test dymny sprawdza CMIS (Basic 200 / bez uwierzytelnienia 401).
- **Ehcache:** wzorce w `mercury-docker` i `mercury-cmd` zsynchronizowane z konfiguracją dev po zadaniu 118.
- **`ae_type_code` w `igo_luc_save_buffer`:** dwie ścieżki zapisywały wpisy bez kodu typu (`MLucSaveBufferLogicSupport.createSaveBufferObject` pomijała `CaseSaveBufferBulk`, `Case2CaseLogic.refreshCatalogMembershipInIndex`); poprawione z testami (`MLucSaveBufferLogicSupportTest`, `Case2CaseLogicTypeCodeTest`), sprawdzone na żywych danych.
- **`max_connections` PostgreSQL:** pule JDBC (200 na węzeł) przekraczają domyślne 100 połączeń; przy zapisie naraz z trzech węzłów `FATAL: sorry, too many clients already`. Autor podniósł limit w `postgresql.conf` na `devops-box-01`. Opis: `docs/postgresql-max-connections-klaster.md` (obserwacja 158).

## Nowe zadania i dokumenty

- **229** Adaptacyjne przekazywanie dokumentów Lucene w klastrze: dwufazowy `updateIndex` sekretarza, strategia zależna od kosztu mapowania, pomiary CPU i kosztu mapowania przed wyborem progu.
- **227** Logowanie i sesje w klastrze (Tomcat Cluster): opis zadania (przeniesione z numeru 224).
- Dokumenty: `docs/docker-rejestr-nexus-linux.md` (konfiguracja demona Dockera i rejestru na Linuksie), `docs/postgresql-max-connections-klaster.md`; w `docs/obserwacje.md` pozycje 149–158; zasada ✅ w ostatniej kolumnie w `CLAUDE.md`.
- Narzędzia pomiarowe w `226-…`: `mierz-zapis.sh` (CMIS), `mierz-sprawe.sh` (REST), `mierz-indeks.py` (propagacja do indeksów, tryby `--batch` i `--all-writers`), `warianty/` (B, C, M0).

## Obserwacje dnia (wnioski do wykorzystania)

- `save` na węźle SLAVE (Lucene) **nie** jest przekierowywany do MASTER; przekierowanie zależy od `mercury.node.case.role` i obciążenia CPU (`ClusterUtils.createResultForRWServer`), a w obrazach jest `RW` i `mercury.node.redirection.cpu.idle=0` (brak przekierowań).
- Kolejność w sekretarzu (przekazywanie włączone): mapowanie, indeksowanie i publikacja, potem wiadomość JMS; praca jest szeregowa, stąd dłuższy czas u odbiorców.
- `mercury-transfer` w `mercury-cmd` ma trzy błędy (stara nazwa klasy w XML, brak `mercury.ws.service.list`, NPE dla podtypu bez definicji); obejście w scratchpadzie (obserwacja 156).
- Sporadyczny kod `000` z `curl` w skryptach pomiarowych (3 na ok. 1000 żądań; obserwacja 157).
- Pomiar CPU węzłów podczas paczki: usługa `NodeMonitorRest` (`load`) zwraca `cpuIdle`, `cpuIdleMillis`, `cpuTotalMillis` dla węzłów (`NodeStatusDto`), więc różnicę zużycia CPU w trakcie testu da się policzyć bez dostępu do Dockera.

## Moje błędy dnia

- **✅ w obserwacjach** stawiałem w złej kolumnie (numer zamiast ostatniej kolumny); poprawione, zasada zapisana w `CLAUDE.md` i w pamięci.
- **Oznaczenia M0 i M1:** po nieporozumieniu (autor miał na myśli M0, ja przyjąłem M1) seria M0 przez chwilę była opisana jako M1; poprawione w `226-…/TASK.md`.
- **Przerwane testy zostawiały sprawy pomiarowe w klastrze** (dwa razy: błąd skryptu i przerwanie zadania w tle); usunąłem je (ok. 70 spraw `FSMServiceOrder` o numerach powyżej 2699), przy czym pierwsza próba usunięcia nie działała przez CRLF w pliku identyfikatorów.
- **Zbyt wiele równoległych zapisów (8 wątków × 3 węzły)** wyczerpało limit połączeń bazy; wynik pomiaru z błędami odrzuciłem, powtórzyłem po podniesieniu `max_connections`.
- Kilka poleceń powłoki z długim `heredoc` nie przeszło (pliki zapisane narzędziem do zapisu plików).

## Skutki uboczne w środowiskach (do wiadomości)

- **Klaster (baza):** zawiera typy `FSMServiceOrder*` i powiązane (kilkadziesiąt definicji) oraz 26 przeniesionych spraw z zestawu 116 (`FSMServiceOrder.2673`, `.2698`, `.2699` i inne) — dane testowe z pomiaru, nie sprzątałem ich.
- **`mercury-db-test`:** zestaw danych 116 (243 sprawy) zostaje (`-Dtest.keep.dataset=true`); profil `scichy-test/test.properties` był tymczasowo zmieniony na czas testu i przywrócony z kopii.
- **`mercury-cmd`:** uruchomienie narzędzia transferu zapisało log w `mercury-install-package/releases/mercury-install-package-3.0.4.15/logs/mercury-cmd.log` (sprawdzić `git status`).
- **Docker Desktop (Windows)** wymaga teraz logowania do organizacji `ibpm` (polityka `registry.json`); polecenia `docker run` z mojej strony nie działają do czasu zalogowania.

## Stan repozytoriów (rano `git status`)

- `mercury` (`hgdb-226`): zmiany `ae_type_code` i testy zatwierdzone przez autora; sprawdzić, czy gałąź została wypchnięta.
- `mercury-docker`, `mercury-cmd`: zmiany z 211a zatwierdzone przez autora; `mercury-docker` ma tag 3.0.4.15 w `Dockerfile` i kompozycjach.
- Workspace (do zatwierdzenia): `docs/obserwacje.md`, `README.md`, `docs/postgresql-max-connections-klaster.md`, `226-…/TASK.md`, `226-…/mierz-indeks.py`, `226-…/mierz-sprawe.sh`, `226-…/warianty/M0/`, `229-…/TASK.md`, ten plik i `plan-2026-11-06.md`.
