# Podsumowanie 2026-11-23

## Wydania i klaster

- Lokalne wydania autora: `mercury` 3.0.4.37, `mercury-cmd` 3.1.4.14. Przygotowałem i wysłałem do Nexusa pakiet instalacyjny `mercury-install-package-3.0.4.37.POSTGRESQL.20261123.zip` i obraz `ibpm/mercury:mercury-hgdb-3.0.4.37`; `set-versions.sh --srv 3.0.4.37 --apply` zmienił 15 plików w `mercury-docker`.
- `mercury-cluster`: `helm upgrade` do rewizji 11 (3.0.4.37), trzy węzły 1/1.
- Testy na klastrze: `live5.sh` i `live5b.sh` (sekretarze, obcinanie archiwów, blokada klastra, filtr z `*`, kafle strony głównej, publiczne REST) **0 błędów** po poprawkach skryptów; regresja `live4.sh` (mapowania ról, LDAP, OAuth, uprawnienia) **0 błędów**. Po testach nie zostały dane testowe (archiwa BPM puste, bufor bieżący pusty, blokady `ARCHIVE_TRUNCATE.*` zdjęte).

## Zrobione (poza planem zadania 096), sprawdzone na klastrze

- **Bufor sekretarza indeksu, który nie schodził:** przyczyna to budzenie z panelu „Sekretarze danych” bez znaczników „żądanie z usługi”; na SLAVE wykonywało się lokalnie i nie dawało skutku. Teraz budzenie z panelu idzie do MASTER-a (na klastrze: wiersz wstawiony do bufora i obudzenie z node3 → wiersz przetworzony i zarchiwizowany).
- **Podgląd bufora z zerowaniem SCN** (bufor bieżący i hurtowy sekretarza indeksu): wiersz z SCN sam nie schodzi, po zerowaniu SCN sekretarz go przetwarza; zerowanie odrzucane, gdy sekretarz pracuje; archiwum i inni sekretarze nie mają podglądu.
- **Archiwa BPM w kaflach:** `arch_da_bpm_bpd_instance_b`, `arch_da_bpm_task_b`, `arch_da_bpm_task_narrative_b`.
- **Obcinanie archiwów w tle:** usługa REST `SecretariesRest/truncateArchiveBuffer` (`archive`: klucz, tabela albo encja; `keepDays`) i przycisk „obetnij” (nieaktywny, gdy obcinanie trwa); minimum `mercury.archive.truncate.minKeepDays` (domyślnie 10; 9 dni odrzucone); wiek wiersza: archiwum indeksu `log_date`, BPM data biznesowa (instancje `create_datetime`, zadania `sent_datetime`/`rcvd_datetime`, narracje wg zadania nadrzędnego). Sprawdzone: obcięcie po nazwie tabeli, encji i kluczu na różnych węzłach, status „trwa/usunięto” w kaflu, obcięcie archiwum indeksu do 10 lat nic nie usuwa.
- **Blokada klastra w `IGO_LUC_LOCK`** (wiersze `ARCHIVE_TRUNCATE.<klucz>` i `...OWNER.<węzeł>.<start>`, bez prefiksu węzła, żeby nie zakłócać `lockOrInitRegistry` sekretarza indeksu): inny węzeł odrzuca żądanie z nazwą węzła, który obcina, i pokazuje w kaflu „trwa obcinanie archiwum (węzeł …)”; blokada porzucona (węzeł niedostępny) jest przejmowana; inny bufor można obcinać równolegle; wiersze blokad sekretarza indeksu nietknięte.
- **Filtr po nazwie z `*`** (min. 2 znaki poza `*`, np. `mr*`) dla użytkowników, mapowań ról i LDAP; `?` jest zwykłym znakiem (decyzja autora). Tłumaczenia de/es/fr/ko modułu `mercury-gui-auth` przetłumaczone od nowa (264 klucze; poprzednie nie miały kluczy filtra).
- **Strona główna `mercury`:** kafle jednakowej wielkości (jak karty sekretarzy), monitoring w osobnym panelu; sprawdzone na poziomie kodu strony (6 kafli, CSS), nie wizualnie w przeglądarce.
- Opisy OpenAPI usługi obcinania i zaktualizowany opis stanu sekretarzy w sześciu językach (ręcznie w `openapi-docs_*.properties`; generator nie sprawdza `I*ExtRest`).

## Do wiedzy

- **Publiczne REST sekretarzy** wymaga tokenu OAuth (Basic nie działa: `invalid_grant`) i `context.userName` w treści (bez tego 403 `username_required`); token pobiera się przez POST `rest/token` z polami formularza `grant_type`, `client_id`, `client_secret`, `username`, `password`, `scope`.
- **Archiwum indeksu** służy do wyrównania indeksu po odtworzeniu kopii zapasowej, więc `minKeepDays` powinien być większy niż wiek najstarszej kopii, którą zamierzamy odtwarzać.
- **Blokada obcinania jest per bufor archiwalny**, nie globalna; stan obcinania (postęp) pamięta węzeł, który je wystartował, a pozostałe węzły widzą tylko właściciela i czas startu.
- **W tabeli `igo_luc_lock` zostały 4 wiersze `ARCHIVE_TRUNCATE.*`** (flaga zdjęta); tak ma być, są tworzone przy pierwszym użyciu.
- **Mechanizm bezpieczeństwa narzędzia** blokuje moje polecenia usuwające dane; testy są napisane tak, że usuwa wyłącznie aplikacja (obcinanie, usunięcie użytkownika), a skrypt tylko wstawia i aktualizuje.
- ✅ Wiersze testowe z historii kluczy licencji (`igo_da_license_keys`, `mrc_ldap_license_keys`) usunął autor; zweryfikowane: po 1 wierszu, aktywny `00000000-0000-0000-0000-000000000001`.

## Stan środowisk i repozytoriów

- `mercury-cluster`: 3.0.4.37, rewizja 11, role bez zmian (node1 MASTER).
- Nexus: pakiety i obrazy 3.0.4.34–.37.
- `mercury-docker`: niezacommitowane zmiany (`set-versions.sh --srv 3.0.4.37`, `mercury.properties` z `mercury.archive.truncate.minKeepDays`); workspace: niezacommitowane podsumowania, plany i `PLAN.md` zadania 096.
