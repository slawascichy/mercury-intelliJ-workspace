# [227] Logowanie i sesje w klastrze (Tomcat Cluster, sticky session)

Status: **zrobione 2026-11-13** (założone 2026-11-05, po zadaniu 211b i stabilizacji klastra trzywęzłowego na `devops-box-01`).
Wdrożone w `mercury` 3.0.4.24 i 3.0.4.25, obraz `ibpm/mercury:mercury-hgdb-3.0.4.25` w Nexusie. Logowanie na kompozycji na
`devops-box-01` sprawdził autor (2026-11-13): działa. Podzadanie: 236 (deadlock przy równoczesnym starcie węzłów).

## Po co

Przy pierwszym uruchomieniu kompozycji trzywęzłowej autor zaproponował sprawdzenie klastra Tomcata
(<https://tomcat.apache.org/tomcat-9.0-doc/cluster-howto.html>) jako mechanizmu logowania w klastrze.

## Do ustalenia

1. Co w Mercury trzyma stan logowania:
   - REST i OAuth: tokeny są w bazie (`MRC_LDAP_OAUTH_*`), więc nie wymagają replikacji sesji (do potwierdzenia w kodzie `OAuthFactory`).
   - GUI (`mercury-gui-core`, strony administracyjne, panele): sesje HTTP; sprawdzić, czy logowanie wygasa przy zmianie węzła.
2. Jak `mercury-lb` (nginx) rozkłada żądania: sticky (`ip_hash`, cookie) czy round-robin.
3. Opcje: (a) sticky session na LB, (b) `SimpleTcpCluster` z `DeltaManager` (multicast zwykle nie działa w sieci Dockera; trzeba `StaticMembership`), (c) sesje w Ehcache/Terracotcie (infrastruktura już jest), (d) brak replikacji i ponowne logowanie przy awarii węzła.
4. Wpływ na Kubernetes (Helm w 211b).

## Ustalenia wstępne (2026-11-12, z plików, bez uruchamiania)

- Konfiguracje nginx w `mercury-docker/mercury-lb/docker-init-config/conf/`: `1_mercury.conf` ma aktywny `ip_hash`, a `2_mercury.conf` i `3_mercury.conf` mają go zakomentowanego (`#ip_hash;`), więc `upstream cluster_hgdb` rozkłada żądania round-robin. Do potwierdzenia: który plik trafia do której kompozycji.
- Chart Helm (`mercury-single-node`) nie ustawia `sessionAffinity` (jeden węzeł Mercury, więc dziś bez znaczenia); przy wielu węzłach w Kubernetesie trzeba to uwzględnić (`sessionAffinity: ClientIP` albo sticky na ingressie).
- Istnieje testowy klaster Kubernetes (`k8s-master`) i klaster trzywęzłowy `devops-box-01` na obrazie 3.0.4.23; oba nadają się do prób przełączania węzła.

## Wyniki

### Rozkład żądań na LB (2026-11-13)

- Plik konfiguracji nginx wybiera `mercury-lb/docker-init-config/service/startServer.sh`: `${HGDB_NODES}_mercury.conf`. Dla jednego węzła `ip_hash` jest aktywny (bez znaczenia przy jednym serwerze), dla dwóch i trzech węzłów jest zakomentowany, więc **round-robin**.
- Uzasadnienie autora: sesje najczęściej realizują użytkownicy techniczni (jeden adres klienta), więc przy `ip_hash` cały ruch trafiałby na jeden węzeł i pula połączeń byłaby obciążana tylko na nim. **Zasada: LB zostaje na round-robin, nie wracamy do `ip_hash`.**

### Co w Mercury trzyma stan (kod `mercury`, 2026-11-13)

- **REST/OAuth:** `OAuthFactory` (`mercury-gui-core`) używa cache `CacheSharing.SHARED` (współdzielony w klastrze) i tokenów w bazie (`MRC_LDAP_OAUTH_TOKENS`). **Test na klastrze trzywęzłowym `devops-box-01`, 3.0.4.23:** token wystawiony na node1 przyjmują node1, node2 i node3 (`CaseBusinessRest/searchByLuceneId`: HTTP 200 ×3); zły token i brak tokenu dają 401 na wszystkich węzłach. Replikacja sesji REST nie jest potrzebna.
- **Sesje HTTP w kodzie:** tylko `lang` (`MainController`, `AbstractController`: język strony) i `SESSION_TOKENS` w `SystemOAuthController` (GUI `mercury-gui-registry`: tokeny OAuth klienta w sesji, `getTokenBySessionAndObject`, `cleanTokenBySessionAndObject`). Pozostałe trafienia `getSession()` to sesje Hibernate.
- **Konfiguracja Tomcata:** w `server.xml.docker-init` element `<Cluster SimpleTcpCluster>` jest zakomentowany, w aplikacjach nie ma `<distributable/>`, `session-timeout` 240 min w `mercury-gui-registry`. Czyli sesje nie są replikowane.
- **Przypuszczenie do sprawdzenia:** przy round-robin kolejne żądania GUI jednego użytkownika trafiają na różne węzły, a tam sesja nie istnieje: `lang` wraca do domyślnego, a `SESSION_TOKENS` jest puste, więc `createNewToken` wystawia token od nowa. Token użytkownika ma w bazie unikalny indeks `(user_name, client_id, client_secret, scope)`; jeśli nowy token zastępuje poprzedni, to sesja na innym węźle (ze starym tokenem) może dostać `OAuthInvalidGrant` i komunikat o możliwym ataku (`OAuthPossibleAttack`). Do potwierdzenia testem GUI.

### Test GUI na klastrze trzywęzłowym `devops-box-01` (2026-11-13, curl, 3.0.4.23)

Aplikacje z logowaniem FORM (`j_security_check`, sesja HTTP): `mercury-gui-registry` (`/system/*`, `/registry/*`), `mercury-ws-app` (`/files/*`, `/lobs/*`, `/login/*`, `/swagger-ui/types.html`, `/static/admin/*`), `license-registry`. Testowany admin/admin.

| Próba | Wynik |
| --- | --- |
| Logowanie bezpośrednio na node1 (`http://…:28080`) | `POST j_security_check` 303, strona po zalogowaniu działa |
| To samo ciasteczko `JSESSIONID` po zalogowaniu na node1, użyte na node2 i node3 | formularz logowania (sesja jest lokalna dla węzła) |
| Sesja z node1 przez LB (round-robin), 18 żądań | strona tylko w 6 z 18 (1/3, czyli gdy trafi na node1) |
| **Logowanie przez LB** (`https://…:1443`), `mercury-gui-registry` i `mercury-ws-app`, 7 prób | **`POST j_security_check` = 408 (Request Timeout) za każdym razem** |

Przyczyna: `GET` strony chronionej zapisuje żądanie w sesji węzła, a `POST j_security_check` musi trafić na ten sam węzeł. Round-robin wysyła kolejne żądania jednego klienta na kolejne węzły, więc `POST` zawsze ląduje na innym (Tomcat odpowiada 408). **GUI i strony z formularzem są dziś nieużywalne przez LB z 2 i 3 węzłami**, a sesji też nie ma kto przeżyć po zmianie węzła. REST (token w bazie i cache współdzielonym) nie ma tego problemu.

### Próba poprawki: powinowactwo tylko dla stron z formularzem (nginx, `ip_hash`), REST dalej round-robin

Pod testowy nginx w `mercury-test` (k8s) kierował na te same trzy węzły; konfiguracja: `upstream gui { ip_hash; … }` dla `~ ^/(mercury-gui-registry|license-registry)/` i `~ ^/mercury-ws-app/(swagger-ui|files|lobs|login|static/admin|auth|j_security_check)`, `upstream rest { … }` (round-robin) dla reszty.

- Logowanie i praca w GUI: 12 z 12 prób udanych (`POST j_security_check` 303, po zalogowaniu strona w 8 z 8 żądań), dla obu aplikacji.
- REST: 30 żądań `searchByLuceneId` rozłożonych równo, **10 / 10 / 10** na trzy węzły (pula nie jest obciążana tylko na jednym).
- GUI z jednego adresu klienta trafia zawsze na jeden węzeł (z `ip_hash`), co jest zamierzone (użytkownicy GUI mają różne adresy; użytkownicy techniczni korzystają z REST).
- Ograniczenia: `ip_hash` nie przenosi sesji po awarii węzła (użytkownik loguje się ponownie); użytkownicy GUI za jednym NAT trafiają na jeden węzeł. Alternatywy: `hash $cookie_JSESSIONID` z `jvmRoute` w `server.xml` (nginx OSS nie ma `sticky cookie`), replikacja sesji (`SimpleTcpCluster` + `<distributable/>`, sesje w Ehcache).

### Wynik próby: Tomcat Cluster (pomysł autora; 2026-11-13, lokalnie, trzy węzły + LB round-robin)

Autor wskazał, że `ip_hash` odpada (użytkownicy techniczni, jeden adres), a rozwiązaniem ma być współdzielenie sesji HTTP przez Tomcat Cluster. Sprawdzone w praktyce na lokalnej kompozycji trzywęzłowej (Docker Desktop, obrazy 3.0.4.23, LB nginx round-robin), konfiguracja w `prototyp/`.

**Działa, ale nie „z pudełka”. Potrzebne były cztery rzeczy:**

1. `<Cluster className="org.apache.catalina.ha.tcp.SimpleTcpCluster" channelSendOptions="6">` z `DeltaManager`, `ReplicationValve` i `ClusterSessionListener`. Multicast w sieci Dockera zwykle nie działa, więc członkostwo statyczne: `StaticMembershipService` (jest w Tomcat 9.0.123) z `LocalMember` i `Member` (host `mercury-nodeN`, port 4000). `uniqueId` musi mieć 16 bajtów (z 12 jest błąd `Error setting property [uniqueId]`). Interceptor `StaticMembershipInterceptor` sam nie wystarcza (domyślnie startuje `McastService` i pada).
2. `<distributable/>` w `web.xml` aplikacji z logowaniem FORM (`mercury-gui-registry`, `mercury-ws-app`, `license-registry`); bez tego Tomcat nie zakłada `DeltaManager` dla kontekstu.
3. **`FormAuthenticator` z `changeSessionIdOnAuthentication="false"`.** Przyczyna głównego problemu: Tomcat 9.0.x zmienia identyfikator sesji już przy wyświetleniu formularza (żądanie chronionego adresu, gdy sesja istnieje), a ta zmiana nie dociera do pozostałych węzłów (węzły dostają delty dla identyfikatora, którego nie znają). Bez wyłączenia: `POST j_security_check` na innym węźle = 408.
4. **`landingPage`** w tym samym `FormAuthenticator` (np. `/registry/mercury-registry`, `/swagger-ui/types.html`). Zapisane żądanie, do którego wraca użytkownik po zalogowaniu, jest „note” sesji Tomcata i **nie jest replikowane**; bez `landingPage` `POST` na innym węźle daje 400 (`authenticator.formlogin`). Z nim po zalogowaniu następuje 302 na stronę startową aplikacji (nie wraca na dokładnie ten adres, który użytkownik wpisał).

Niepotrzebne: zmiany w stronie logowania JSP (próbowałem atrybutu w sesji, po cofnięciu działało tak samo).

| Test (LB round-robin, 3 węzły) | Bez klastra | Z klastrem i powyższą konfiguracją |
| --- | --- | --- |
| Logowanie FORM przez LB, `mercury-gui-registry` | 0 z 6 (408) | **6 z 6** (302) |
| Logowanie FORM przez LB, `mercury-ws-app` | 0 z 6 (408) | **6 z 6** (302) |
| Strona chroniona po zalogowaniu (36 żądań na aplikację, cookie aktualizowane) | 0 z 36 | **36 z 36** |
| `GET` na node A, `POST` na node B (4 kombinacje, bezpośrednio) | 408 | 302 |
| Zatrzymanie node1, potem też node2 (zostaje node3), 12 żądań z tą samą sesją | – | **12 z 12** na każdym etapie; po powrocie node1 i node2 też 12 z 12 |
| REST przez LB (30 → 12 żądań, token z node1) | 200 | 200 (bez zmian) |
| Błędy w logach (`SEVERE`, `NotSerializable`) | – | 0 na trzech węzłach |

**Koszt i ryzyka:**

- `changeSessionIdOnAuthentication="false"` wyłącza ochronę przed session fixation (identyfikator sesji nie zmienia się po zalogowaniu). Trzeba o tym zdecydować świadomie (np. dla GUI wewnętrznego akceptowalne, dla publicznego niekoniecznie). Alternatywą bez tego kosztu jest naprawa replikacji zmiany identyfikatora (nie sprawdzano) albo sticky tylko na czas logowania.
- Replikacja `DeltaManager` rozsyła zmiany do **wszystkich** węzłów (all-to-all); przy większym klastrze rozważyć `BackupManager`.
- Konfiguracja członków jest per węzeł (inna lista `Member`/`LocalMember`), więc w obrazie trzeba ją generować ze zmiennych (`HGDB_NODE`, `HGDB_NODES`, nazwy hostów). W Kubernetesie nazwy `mercury-nodeN` nie istnieją; Tomcat 9.0.123 ma `KubernetesMembershipProvider` i `DNSMembershipProvider` (`org.apache.catalina.tribes.membership.cloud`), do sprawdzenia.
- Nie sprawdzono: GUI OAuth (`system/oauth/getToken` zwraca 404 także bezpośrednio na węźle w tym wdrożeniu), `lang` w sesji, wylogowanie (`inv_logoff.jsp`), wygasanie sesji w klastrze, wydajność przy dużej liczbie sesji.

### Pytania autora po próbie Tomcat Cluster (2026-11-13)

**1. Ochrona przed session fixation na poziomie LB.** Nie da się jej zapewnić w pełni: LB nie wie, kiedy użytkownik się uwierzytelnił, i nie może zmienić identyfikatora sesji po stronie serwera (cookie jest tylko wskaźnikiem na sesję w Tomcacie). Na LB można tylko utrudnić wykorzystanie fiksacji (cookie z `Secure`, `HttpOnly`, `SameSite=Strict`: nginx `proxy_cookie_flags JSESSIONID secure httponly samesite=strict;` od 1.19.3, LB ma 1.20.1; HSTS; krótki limit bezczynności) – nie sprawdzano. Właściwa ochrona to rotacja identyfikatora po zalogowaniu w Tomcacie z poprawną replikacją (patrz pkt 2).

**2. Własny realm.** `TomcatLdapRealm` (`mercury-gui-core`, rozszerza `JNDIRealm`) wywoływany jest tylko przy logowaniu (`authenticate(user, hasło)` zwraca `TomcatMercuryPrincipal`); sesji nie widzi, więc nie jest warstwą, która mogłaby je rozsyłać. Principal Tomcat i tak trzyma w sesji i `DeltaManager` go replikuje (sprawdzone: po zalogowaniu na node1 cookie działa na node2 i node3). Warstwa do rotacji identyfikatora z replikacją to własny `Valve` (obok realmu w `gui.core.auth`) wywołujący po udanym logowaniu `DeltaManager.changeSessionId(session, true)`; przyczyną problemu jest najpewniej to, że `Request.changeSessionId()` nie powiadamia klastra (przypuszczenie, nie sprawdzone). Inna droga, wykorzystująca istniejące mechanizmy: ciasteczko z tokenem OAuth (`OIDSESSIONTOKEN`, `OAuthFactory.getToken`, cache współdzielony i baza) i uwierzytelnianie GUI filtrem zamiast sesji HTTP; większa zmiana.

**3. Redis jako magazyn sesji.** Prototyp: Redis 7 w sieci kompozycji + `redisson-tomcat-9` 3.27.2 (menedżer sesji Tomcata, jary zweryfikowane sumą sha1), `readMode=REDIS`, `updateMode=AFTER_REQUEST`, bez Tomcat Cluster. Wynik jest **niestabilny**: logowanie FORM przez LB (`POST` udany 6 z 6) działa, a po nim strona chroniona otwiera się w: 0 z 36 (domyślna rotacja identyfikatora), 24 z 36 (rotacja wyłączona), 12 z 36 (dodatkowo `broadcastSessionUpdates` i `broadcastSessionEvents`). Principal i `authtype FORM` trafiają do Redisa, ale węzeł, który utworzył sesję, trzyma lokalną kopię bez zalogowanego principala (przypuszczenie). Dla porównania Tomcat Cluster dawał 36 z 36. Poza tym Redis to nowy komponent infrastruktury (bez zalet w porównaniu z dostępnym `DeltaManager` przy trzech węzłach); licencja Redis 7.4+ (RSALv2/SSPL) i 8 (AGPL) wymaga uwagi, alternatywa to Valkey. Wariant bez nowego komponentu: `PersistentManager` + `JDBCStore` w PostgreSQL z `PersistentValve` (sesja z bazy przy każdym żądaniu); nie sprawdzano.

### Własny authenticator (`ClusterFormAuthenticator`; 2026-11-13, lokalnie, trzy węzły + LB round-robin)

Cel: zachować ochronę przed session fixation (rotacja identyfikatora po zalogowaniu) i logowanie FORM przy round-robin, bez `changeSessionIdOnAuthentication="false"`. Kod i konfiguracja w `prototyp/`.

**Co naprawdę psuło logowanie w klastrze (z logów FINE `org.apache.catalina.authenticator` i `org.apache.catalina.ha`):**

1. `FormAuthenticator` zapisuje przy wyświetleniu formularza **oczekiwany identyfikator sesji w „note”** (`org.apache.catalina.authenticator.SESSION_ID`), a przy `POST j_security_check` go sprawdza (`Current session ID is [X] but FORM authenticator was expecting [null]`). „Note” sesji nie są replikowane, więc `POST` na innym węźle kończy się „User authentication failure” (302 na stronę błędu). To wbudowana ochrona Tomcata przed fixation.
2. Zmiana identyfikatora tuż po utworzeniu sesji (przy wyświetleniu formularza) nie dociera do pozostałych węzłów (węzły dostają utworzenie starego identyfikatora i deltę nowego; komunikatu o zmianie nie ma).
3. Gdy logowanie obsługuje węzeł, który **nie utworzył** sesji (kopia zapasowa), rotacja tworzy nowy obiekt sesji (stara jest wygaszana), a `AuthenticatorBase.register` ustawia zalogowanego użytkownika na starym obiekcie, więc użytkownik jest po logowaniu niezalogowany. (Wniosek z logów: „Notifying cluster of session expiration … primary [false]”, a potem „Created a new DeltaSession”.)
4. `ReplicationValve` z przykładowym filtrem `.*\.html` nie replikuje zmian sesji dla adresów `*.html` (u nas chroniony `/swagger-ui/types.html`); filtr trzeba zawęzić do zasobów statycznych bez `.html`.

**Rozwiązanie (`ClusterFormAuthenticator extends FormAuthenticator`, ok. 100 linii):** (a) oczekiwany identyfikator sesji kopiowany z „note” do **replikowanego atrybutu** sesji i przywracany przed sprawdzeniem przy logowaniu (`doAuthenticateExtended`); (b) rotacja identyfikatora (`changeSessionID`) tylko przy `j_security_check`, nie przy wyświetleniu formularza; (c) po rotacji stan uwierzytelnienia ustawiany na bieżącym obiekcie sesji (`register`). Zapisane żądanie nadal nie jest przenoszone, więc potrzebny jest `landingPage`.

| Test (LB round-robin, 3 węzły) | Wynik |
| --- | --- |
| Logowanie FORM przez LB, `mercury-gui-registry` i `mercury-ws-app` (po 6 prób; przekierowanie na stronę błędu nie liczone jako sukces) | **6 z 6** |
| Identyfikator sesji zmieniony po logowaniu | **6 z 6** (ochrona przed fixation zachowana) |
| Strona chroniona po zalogowaniu (36 żądań na aplikację) | **36 z 36** |
| **Atak fixation:** ID wystawione atakującemu, ofiara loguje się z nim | atakujący ze starym ID: formularz (3 z 3), ofiara z nowym ID: zalogowana (3 z 3) |
| Błędne hasło (6 prób) | strona „Błąd logowania do systemu”, chroniona strona nadal wymaga logowania (6 z 6) |
| Awaria: zatrzymanie node1, potem node2, powrót obu | 12 z 12 na każdym etapie |

Uwaga do wcześniejszych wyników: w próbach z Redis i w pośrednich wersjach authenticatora liczyłem „POST udany” po kodzie 302/303, a 302 bywa też przekierowaniem na stronę błędu logowania; rozstrzygającą miarą była zawsze „strona po zalogowaniu”, ta się zgadza. Rekomendacja z poprzedniej sekcji (`changeSessionIdOnAuthentication="false"`) jest **zastąpiona** tym authenticatorem.

**Do zrobienia przy wdrożeniu:** klasa w `mercury-gui-core` (jar w classpath Tomcata, zależność `provided` od Tomcat 9.0), `<distributable/>` i `META-INF/context.xml` w aplikacjach, `Cluster` w szablonie `server.xml.docker-init` (lista członków z `HGDB_NODE`/nazw hostów, filtr `ReplicationValve` bez `.html`), test w Kubernetesie (członkostwo: `KubernetesMembershipProvider`/`DNSMembershipProvider`), test regresji na zmianę wersji Tomcata (opieramy się na zachowaniu `FormAuthenticator` z 9.0.123: nazwa metody `doAuthenticateExtended`, note `SESSION_ID`). Nie sprawdzano: wylogowanie, wygasanie sesji, dłuższe obciążenie, `license-registry`.

## Podsumowanie (2026-11-13)

**Decyzja:** replikacja sesji HTTP przez Tomcat Cluster (pomysł autora) z własnym `FormAuthenticator`. LB zostaje na round-robin.
`ip_hash` odrzucony, bo użytkownicy techniczni łączą się z jednego adresu i cały ruch szedłby na jeden węzeł (pula połączeń
obciążana tylko na nim). Redis (Redisson) sprawdzony i odrzucony: wynik niestabilny (0/36, 24/36, 12/36 poprawnych stron po
zalogowaniu), do tego nowy komponent infrastruktury.

**Co wdrożono:**

| Repozytorium | Zmiana |
| --- | --- |
| `mercury` 3.0.4.24 | `org.mercury.gui.auth.ClusterFormAuthenticator` w `mercury-gui-core`, `<distributable/>` w `web.xml` aplikacji `mercury-gui-registry` i `mercury-ws-app`, właściwość `tomcat.version` (9.0.123) w parencie, `tomcat-catalina` w `gui-core` i `ws-app` na tej właściwości |
| `mercury` 3.0.4.25 | poprawki podzadania 236 |
| `mercury-docker` | `server.xml` z elementem `Cluster` i deskryptory kontekstu generowane przy starcie (`mercury-server.sh`, `initTomcatCluster`), zmienne `TOMCAT_CLUSTER_MEMBERS` i `TOMCAT_CLUSTER_PORT`, kompozycje dwu- i trzywęzłowa, wersje 3.0.4.25 (kompozycje, README, chart) |
| `mercury-cmd` | `mercury.srv.version` 3.0.4.25 |
| `hgdb-client-open` | `mercury.server.version` 3.0.4.25 (`mercury.project.version`, czyli `mercury-lib`, zostaje 3.0.4.24) |
| `docusaurus-hgdb` | strona `Cluster_sessions` (EN, PL), uwagi w `Kubernetes_installation`, 13 tagów w `tags.yml` |

**Testy (lokalnie, trzy węzły, LB round-robin):** logowanie FORM przez LB 6 z 6, strona po zalogowaniu 36 z 36, zmiana
identyfikatora sesji po logowaniu 6 z 6, atak session fixation zablokowany, awaria dwóch z trzech węzłów bez utraty sesji,
REST bez zmian. Szczegóły w sekcjach powyżej i w `prototyp/`. Test na kompozycji na `devops-box-01` (2026-11-13): logowanie działa.
Kubernetes (`mercury-test`): chart jednowęzłowy, replikacja wyłączona, logowanie działa po aktualizacji do 3.0.4.25.

**Nie sprawdzono:** wylogowanie, wygasanie sesji w klastrze, długie obciążenie, `license-registry` (jest `FormAuthenticator`, ale
bez `<distributable/>`), członkostwo w Kubernetesie (Tomcat 9.0.123 ma `KubernetesMembershipProvider` i
`DNSMembershipProvider`, chart ma jeden węzeł).

**Ryzyka i uwagi na przyszłość:**

- Authenticator opiera się na zachowaniu `FormAuthenticator` z Tomcata 9.0.123 (`doAuthenticateExtended`, „note” `SESSION_ID`). Po
  zmianie wersji Tomcata powtórzyć test logowania przez LB (opisane w Javadoc klasy i na stronie dokumentacji).
- Klasa musi być w `common.loader` Tomcata. Gdy jej brak, Tomcat uruchamia aplikację **bez uwierzytelniania** (stwierdzone
  w teście); skrypt obrazu przerywa wtedy start.
- Po zalogowaniu użytkownik trafia na `landingPage` aplikacji, a nie na adres żądany wcześniej (zapisane żądanie nie jest
  replikowane).
- `ReplicationValve` bez `.html` w filtrze (chronione strony kończą się na `.html`).

### Podzadanie 236 (2026-11-13)

Przy teście obrazu 3.0.4.24 na kompozycji trzywęzłowej wykryto deadlock przy równoczesnym starcie węzłów na świeżej bazie
(obserwacja 166, niezwiązany z Tomcat Cluster). Poprawka jako podzadanie: `236-Deadlock-przy-rownoczesnym-starcie-wezlow-CMIS`,
w tej samej gałęzi `hgdb-227`.
