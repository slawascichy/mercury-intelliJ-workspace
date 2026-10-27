# [58] Test ręczny usługi poziomów logowania (2026-10-27)

Cel: sprawdzić na działającym serwerze to, czego nie obejmują testy jednostkowe: wywołanie REST z tokenem OAuth, rolę `mrc_sysadmin`, panel w przeglądarce i faktyczny wpływ zmiany poziomu na logi.
Testy jednostkowe (30 z 30) sprawdzają logikę i adaptery, ale nie przepływ przez serwer.

## 1. Przygotowanie

1. **WAR z gałęzi `hgdb-058`.** W `mercury-server/apache-tomcat/webapps/mercury-ws-app.war` jest WAR z 2026-10-27 13:34 zawierający klasy `org.mercury.logging.*`, `LoggerLevelsExtRest` i `static/admin/loggers.html`.
   Jeśli budujesz od nowa: `mvn -pl mercury-ws-app -am package -Ddatabse.provider=POSTGRESQL -Dmaven.test.skip` (WAR w `mercury-ws-app/target/`).
2. **Biblioteki logowania w `apache-tomcat/mercury/lib`.** Na serwerze są `log4j-1.2.14.jar` i `slf4j-log4j12-1.7.25.jar` (backend `log4j`). Test warto wykonać na tym stanie, a potem powtórzyć po migracji na Logback (zadanie 214; backend `logback`).
   Adapter Logbacka w WAR-ze jest `provided`, więc do działania na Logbacku jary Logbacka muszą być w `mercury/lib`.
3. **Rola `mrc_sysadmin`.** Klient OAuth używany do testu musi mieć w konfiguracji zakres `mrc_sysadmin` (w przykładach: `mrc-user,mrc-useradmin`), a testowy użytkownik tę rolę w tabeli ról. Drugi użytkownik, bez tej roli, posłuży do testu odmowy.
4. **Plik z danymi dostępowymi** poza repozytorium: `~/.mercury-test-058.env` (format w nagłówku `test-manualny.sh`). Skrypt nie wypisuje haseł ani sekretów.

## 2. Test przez skrypt

```bash
bash tasks/hgdb/058-Logger-dynamiczne-zmiana-poziomów-logowania/test-manualny.sh
```

Skrypt pobiera token (`/rest/token`, przepływ `password`) i sprawdza: limit 30 i obcięcie wyniku, `getLevel`, `setLevel` na `DEBUG` i powrót `INHERIT`, `previousLevel`, `search` z `onlyConfigured`,
błędy walidacji (nazwa z niedozwolonymi znakami, nieznany poziom, `INHERIT` na `ROOT`, pusta nazwa), brak tokenu i (opcjonalnie) odmowę dla użytkownika bez roli.
Na końcu pisze `Wynik: N OK, M błędów`. Pełnych odpowiedzi nie trzeba mi przesyłać, wystarczy lista linii `[BŁĄD]` i fragmenty odpowiedzi z sekcji 1–3 (bez tokenu).

## 3. Test ręczny w logu

1. W katalogu logów serwera (`apache-tomcat/logs` albo `IBPM/mercury/logs`) znajdź wpisy `WARN ... Zmiana poziomu logowania: kategoria=..., poziom ... -> ... , użytkownik=...`. Powinny być po jednym na każdy udany `setLevel`, z nazwą administratora.
   Nie powinno być wpisów dla prób użytkownika bez roli.
2. **Faktyczny wpływ zmiany:** ustaw `DEBUG` na kategorii, która często loguje (np. `org.mercury.lucene`), wykonaj zapytanie wyszukujące, sprawdź, że w logu pojawiły się wpisy `DEBUG`. Wróć do `INHERIT` i sprawdź, że wpisy `DEBUG` znikają.
3. **Klaster:** zmiana dotyczy tylko węzła, który odpowiedział. Na drugim węźle poziom ma się nie zmienić (jeśli masz drugi węzeł).
4. **Restart:** po restarcie węzła obowiązuje znów poziom z pliku konfiguracyjnego (zmiana nie jest trwała).

## 4. Panel w przeglądarce

1. Otwórz `<adres mercury-ws-app>/static/admin/loggers.html`.
2. Zaloguj się (użytkownik, hasło, `client_id`, `client_secret`) albo wklej token (np. ze Swagger UI, przycisk Authorize). Oczekiwany efekt: komunikat „Zalogowano.” i dwa panele (wyszukiwanie, pojedyncza kategoria).
3. Wyszukaj `mercury` (limit 10): tabela z kategoriami; wybierz poziom w wierszu i kliknij „Zastosuj”: komunikat „Zmieniono: …”, kolumny poziomów się zmieniają.
4. W polu „Nazwa kategorii” wpisz kategorię, „Pobierz” i „Ustaw”.
5. Zaloguj użytkownika bez roli: oczekiwany komunikat o błędzie z kodem `SC001`.
6. **Do sprawdzenia, bo nie testowałem:** czy `/rest/token` przyjmuje dane klienta w treści formularza (panel i skrypt tak je wysyłają). Jeśli serwer wymaga uwierzytelnienia Basic dla klienta, pobierz token inaczej (Swagger UI) i wklej go w panelu; wtedy daj znać, poprawię wywołanie.
7. Panel jest statyczny i wołany z tej samej domeny co REST. Jeśli aplikacja stoi za serwerem pośredniczącym (Nginx), sprawdź, że `/static/admin/` jest przez niego przepuszczane.

## 5. Specyfikacja OpenAPI i Swagger UI

Sprawdź, czy w `<adres>/rest/openapi.json` (i w Swagger UI) pojawiła się usługa `LoggerLevelsExtRest` z trzema operacjami i opisami (pl i en; w pozostałych językach z kluczy `openapi-docs_*`). Zależy to od `ExtRestOpenApi`, którego nie uruchamiałem.

## 6. Czego nie ruszać

Test zmienia tylko poziomy w pamięci serwera. Nie zmienia konfiguracji, bazy ani indeksów. Po teście poziomy wracają do dziedziczenia (`INHERIT`), a restart węzła przywraca stan z pliku.
