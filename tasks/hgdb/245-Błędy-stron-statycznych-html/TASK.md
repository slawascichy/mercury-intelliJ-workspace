# [245] Błędy stron statycznych *.html

https://github.com/slawascichy/hgdb/issues/245

Chodzi o strony:
- mercury-ws-app/static/admin/loggers.html
- mercury-ws-app/static/admin/secretaries.html
- mercury-ws-app/static/admin/lucene-queries.html

Błędy:
1. Po realizacji wspólnego logowania, nie wiadomo na jakim węźle jesteśmy, Można by było dodać stronę z wyborem 
   węzła i podać jako paramer n=<nazwa_węzła>. W konfiguracji LB by przekierowywał ruch na konkrety węzeł (proxy).
2. Musimy zrobić wersje językowe. Strona główna się zmienia, linki, a tu? To niestety nie jest do przyjęcia.

## Postęp (2026-11-14) – etap A: strony JSP, język, węzeł

Decyzje (zatwierdził autor): strony jako JSP; wybór węzła przez parametr `n=<węzeł>`, który LB zamienia na ciasteczko `hgdb_node` i routuje do upstreamu danego węzła.

Zrobione (gałąź `hgdb-245` w `mercury` i `mercury-docker`, niezacommitowane):

- **JSP:** `pages/admin/{loggers,secretaries,lucene-queries}.jsp` z `include/adminTop.jsp`, `adminBar.jsp`, `adminFoot.jsp`. Nagłówek jak na stronie głównej: logo, wersja, nawigacja między trzema stronami, użytkownik i wylogowanie, przełącznik języka (`?l=xx`), nazwa bieżącego węzła, lista węzłów i znacznik „przypięty”.
- **Kontroler:** `AdminPagesController` (`/admin/loggers`, `/admin/secretaries`, `/admin/lucene-queries`). Język przez `MainController.loadLang`. Lista węzłów z `INodeStatusMonitor.loadNodeList()` (dynamicznie, bez konfiguracji węzłów w aplikacji), bieżący węzeł zawsze na liście.
- **Teksty:** 135 kluczy `admin.*` w `WebAppMsg_pl/en.properties`, składane przez `AdminMessages` (łańcuch języka → en → pl, klucze z kropką jako obiekty, bezpieczny JSON w `<script>`). Kod JavaScript stron bez zmian, słownik `TEXTS` zastąpiony obiektem z serwera.
- **Bezpieczeństwo:** `web.xml`, rola `mrc-sysadmin` także dla `/pages/admin/*`; `/admin/<strona>` objęte istniejącymi wzorcami `/admin/<strona>/*`.
- **Stare adresy:** `static/admin/*.html` to przekierowania na nowe strony (z zachowaniem `?` i `#`). Linki na stronie głównej wskazują nowe adresy.
- **LB (`mercury-docker/mercury-lb`):** upstreamy per węzeł, `map` z `$arg_n` i `$cookie_hgdb_node`, ciasteczko (Secure, HttpOnly, SameSite=Lax), `n=auto|all` kasuje przypięcie. Sprawdzone `nginx -t` i routingiem dla 1, 2 i 3 węzłów. Opis w `mercury-lb/README.md`.
- **Testy:** `AdminMessagesTest` (7) i `AdminPagesControllerTest` (2) przechodzą (`mvn -o -pl mercury-ws-app`, po `install` autora).

Niezweryfikowane / do zrobienia:

- Brak uruchomienia stron na działającym serwerze: kompilacja JSP, wygląd, przełączanie języka i węzła (w klastrze za LB).
- Tłumaczenia de/es/fr/ko nie istnieją; strony pokazują angielskie (fallback). Do przepuszczenia przez translator autora (`localization-project`).
- Obraz `mercury-lb` nie jest przebudowany; do ustalenia, czy chart Helm używa tej samej konfiguracji nginx.
- Przełącznik języka na stronie głównej nie jest częścią tego etapu.

## Postęp (2026-11-16): uwagi autora po pierwszym oglądzie

- **Strony wysyłania plików** (`pages/files/*` – 5 stron, `pages/lobs/*` – 2 strony): ten sam nagłówek co strony admina (logo, wersja, Strona główna, użytkownik i wylogowanie, węzeł i jego wybór, język). Zamiast zmieniać kontrolery, `UploadPagesInterceptor` (mapowanie `/files/**` i `/lobs/**` w `moduleDb-2.0/3.0-servlet.xml`) dokłada do modelu język, nazwę i listę węzłów; działa też po POST. Tytuł i nagłówek z istniejących kluczy `<strona>.title` i `<strona>.header`. `adminBar.jsp`: adres bazowy z `basePath`, linki do stron admina tylko na stronach admina (`adminNav`). Skrypt komunikatów strony POI wybierany po `${lang}` (wcześniej po cookie).
- **Plan zapytania:** w historii zapytań zamiast tekstu planu pod wierszem jest link „Zobacz plan”, który otwiera okno dialogowe (zapytanie, rodzaj, użytkownik, czas, plan; Kopiuj, Zamknij, Esc, kliknięcie tła). Plan nadal pobierany na żądanie.
- Testy: `AdminMessagesTest` (8), `AdminPagesControllerTest` (2), `UploadPagesInterceptorTest` (1).
- Poprawione przy okazji: POST `uploadDictionaryMultipleFile` zwracał widok `uploadSystemMultipleFile` (`SystemFileUpload`), teraz wraca na stronę słowników.

## Lokalna kompozycja testowa 3-węzłowa (2026-11-16)

- Katalog `…\scratchpad\c245` (kopia `docker-compose.yml` i `mercury-hgdb.env` z `mercury-three-node-cluster`), projekt `mercury245`, dane w `D:\mercury-245` (świeże, bez danych z `D:\mercury`). Obrazy lokalne: `ibpm/mercury:mercury-hgdb-3.0.4.27-local` (nakładka z WAR-em na obrazie 3.0.4.26) i `ibpm/mercury-lb:mercury-hgdb-3.0-245`. Nic nie wypchnięto do Nexusa.
- CMIS Basic wymaga `CMIS_OAUTH_CLIENT_SECRET`; w `mercury-hgdb.env` z repozytorium jest pusty (celowo), więc bez wpisu w lokalnej kopii env serwer zwraca 401 (`mercury-server.sh` pomija wtedy włączenie Basic). Po uzupełnieniu: Basic `admin:admin` 200, bez uwierzytelnienia 401.
- Plany zapytań na świeżej bazie: próg wolnego zapytania ustawiony na 0 ms (`mercury.lucene.query.monitor.slowMillis=0` dopisane do `docker-init-config/config/mercury.properties` w kontenerach; znika po odtworzeniu kontenerów). Plan powstaje tylko dla zapytań z `AND` (optymalizator), np. `a* AND b*`; stan monitora jest per węzeł.

## Etap B (2026-11-16): tłumaczenia i poprawka kodowania

- **Kodowanie:** pliki JSP zaczynające się od `include` były czytane w domyślnym kodowaniu (w modalu planu `·` jako `Â·`). Na początku 10 JSP-ów (3 admin + 7 stron wysyłania plików) jest teraz `<%@ page ... pageEncoding="UTF-8"%>`.
- **Tłumaczenia:** 138 kluczy `admin.*` (pl → en pisał Claude) przetłumaczono translatorem `localization-project` (Gemini) na `de es fr ko`; `validate`: 0 błędów (ostrzeżenia to skróty i terminy techniczne identyczne ze źródłem: `Plan`, `Max`, `p50`, `Thread`). Wpisane do `WebAppMsg_{de,es,fr,ko}.properties` w formacie `\uXXXX`. Wynik nie przeszedł przeglądu natywnego (tylko `validate`); do przeglądu przez autora.
- **Testy:** `AdminMessagesTest` sprawdza, że wszystkie języki mają ten sam zestaw kluczy `admin.*` i że de/es/fr/ko nie dostają już angielskiego zapasowego (12 testów razem z pozostałymi).
