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
