# Plan zadania 096 (GUI do zarządzania danymi uwierzytelniania i autoryzacji)

Gałąź: `hgdb-96` (`mercury`, `docusaurus-hgdb`; zawiera już zmiany obs. 201: `LiveDocFreq`, opis `maxResults`).

## Decyzje autora (2026-11-22)

- Technologia widoków: **JSP** (jak `ROOT` i `pages/admin/*.jsp`), bez nowego stosu.
- Nowa aplikacja **`mercury-gui-auth`** (moduł w `mercury`, WAR), link do niej w `mercury-gui-registry` i w `ROOT.war` (`index.jsp` pokazuje link tylko, gdy kontekst jest zainstalowany, jak dla `mercury-ws-app`), do tego link w `adminBar.jsp`.
- Nowa aplikacja musi mieć **SSO** z `mercury-ws-app`.
- Edycja: tylko **lokalni użytkownicy** (`MRC_LDAP_INT_USERS`) i **mapowania ról** (`MRC_LDAP_INT_ROLES_MAP`; uczestnicy mapowania mogą pochodzić z lokalnego repozytorium albo z LDAP). **LDAP tylko do odczytu.**
- Obserwacja 148 weryfikujemy w ramach tego zadania.

## Wiedza z kodu

- `DynamicSecurityOAuthConfigManager.refresh()` istnieje (interfejs i implementacja), nikt go nie woła. Konfiguracja OAuth jest w pamięci każdego węzła, więc odświeżenie trzeba rozesłać na wszystkie węzły (mechanizm do wybrania: JMS, wywołanie między węzłami albo cache).
- Lokalnych użytkowników `TomcatLdapRealm.findUserInLocalRepository` czyta z bazy przy każdym logowaniu, więc pozycje 1, 2 i 4 z TASK.md nie wymagają odświeżania; tylko konfiguracja tokenów OAuth (pozycja 5).
- Hasło lokalnego użytkownika to SHA-1 z `nazwa/hasło` (`SecurityPassword`); GUI musi używać tego samego mechanizmu.
- `mercury-gui-registry` jest szkieletem (kontroler „Hello World” i REST rejestru modułów).
- Profil własny (pozycja 2) musi być dostępny dla każdego zalogowanego (`mrc-user`), reszta dla `mrc-sysadmin`.

## Spike SSO (etap 0, 2026-11-22) ✅

Test na `mercury-cluster` (node2 i node3 z valve, node1 był OFFLINE), przez LB z przypięciem węzła `?n=`, użytkownik `admin`, aplikacje `mercury-ws-app` (`/admin/loggers`, `mrc-sysadmin`) i `mercury-gui-registry` (`/registry/*`, `mrc-user`; obie z `ClusterFormAuthenticator`). Skrypt: scratchpad `sso/ssotest.sh`.

- **Bez SSO (baza):** druga aplikacja za każdym razem pokazuje formularz logowania; sesja w obrębie jednej aplikacji działa między węzłami (replikacja sesji z zadania 227).
- **Z `org.apache.catalina.ha.authenticator.ClusterSingleSignOn` w `<Host>`:** po zalogowaniu do `mercury-ws-app` druga aplikacja wpuszcza bez logowania, **na tym samym i na innym węźle**, w obu kierunkach (node3 → node2, node2 → node3). Ciasteczko `JSESSIONIDSSO` ma path `/` (obejmuje wszystkie konteksty).
- **Pułapka:** `ClusterSingleSignOnListener` **nie** wpisujemy do `server.xml` (brak domyślnego konstruktora, Tomcat nie wstaje: `NoSuchMethodException`). Valve rejestruje listener sam; wystarcza `<Valve className="org.apache.catalina.ha.authenticator.ClusterSingleSignOn"/>` w `<Host>` (Cluster na poziomie Engine już jest w `cluster.xml.docker-init`).
- **Zmiana nietrwała:** `server.xml` w podach node2 i node3 edytowany ręcznie (kopia `server.xml.orig-sso`); wymiana poda ją cofnie. Trwale: `server.xml.docker-init` w `mercury-docker` (valve tylko przy `TOMCAT_CLUSTER_MEMBERS`; dla jednego węzła zwykły `SingleSignOn`).
- **Kierunek odwrotny (logowanie w `mercury-gui-registry`, potem `mercury-ws-app`):** działa, na tym samym i na innym węźle.
- **Wylogowanie** (`/auth/inv_logoff.jsp`, czyli `session.invalidate()`): w którejkolwiek aplikacji kasuje SSO we **wszystkich** aplikacjach i na **wszystkich** węzłach (po wylogowaniu obie aplikacje na obu węzłach pytają o logowanie).
- **Użytkownik bez roli administratora** (tymczasowy `tester`, tylko `mrc-user`; usunięty po teście): przez SSO wchodzi do `registry` i `swagger-ui/types.html`, a `admin/loggers` (`mrc-sysadmin`) daje 403, bez pętli logowania.
- **Role do wykorzystania w `mercury-gui-auth`:** baza ma role `mrc-useradmin`, `mrc-groupadmin`, `mrc-serviceadmin` obok `mrc-sysadmin` i `mrc-user`; użytkownicy lokalni to pary w `MRC_LDAP_INT_ROLES_MAP` z typem uczestnika `U` (użytkownik) i `G` (grupa, lokalna lub z LDAP). Do ustalenia: która rola zarządza użytkownikami (`mrc-useradmin`), mapowaniami (`mrc-groupadmin`), OAuth (`mrc-sysadmin`).
- **Nie sprawdzone:** zachowanie po restarcie węzła, kompozycje Docker (inny `server.xml`), `requireReauthentication`.

## Etapy

0. ✅ Spike SSO (wyżej).
1. ✅ (2026-11-22, kod i testy; wdrożenie z nowym obrazem i `helm upgrade`) Trwała konfiguracja SSO w `mercury-docker` (`server.xml.docker-init`, kompozycje i charty) oraz usługa REST odświeżająca konfigurację OAuth na wszystkich węzłach (z OpenAPI, tłumaczeniami i testem).
2. Szkielet `mercury-gui-auth` (moduł, WAR, `web.xml` z FORM i rolami, układ jak `pages/admin`), link w `ROOT/index.jsp`, w `mercury-gui-registry` i w `adminBar.jsp`; pakiet instalacyjny i obraz; sprawdzić nginx LB.
3. Lokalni użytkownicy (lista, dodanie, edycja, hasło, wygaśnięcie) i profil własny.
4. Mapowania użytkowników i grup na role (lokalne i z LDAP) oraz przegląd użytkowników i grup LDAP (tylko odczyt, bez ujawniania danych połączenia).
5. Konfiguracja tokenów OAuth (`MRC_LDAP_OAUTH_CONFIG`, `MRC_LDAP_OAUTH_SERVICE`, przegląd `MRC_LDAP_OAUTH_TOKENS`), sekrety zamaskowane, odświeżenie po zapisie.
6. Audyt zmian, tłumaczenia (`admin.*`/nowe klucze przez translator), dokumentacja docusaurus (en i pl), test klastra, weryfikacja obs. 148.

## Stan etapu 1 (2026-11-22)

- `mercury-docker` (gałąź `hgdb-96`): `server.xml.docker-init` ma znacznik `TOMCAT_SSO_VALVE`, `mercury-server.sh` funkcja `initTomcatSsoValve` (klaster: `ClusterSingleSignOn`, jeden węzeł: `SingleSignOn`); sprawdzone na kopiach szablonu. Niewdrożone na klastrze (wymaga obrazu).
- `mercury` (gałąź `hgdb-96`): usługa `OAuthConfigExtRest` (`POST /rest/service/OAuthConfigExtRest/refresh`, `mrc-sysadmin`, tylko węzeł obsługujący żądanie), wspólne `AdminAccess` i `AdminEnvelope` (refaktor `LoggerLevelsExtRest` i `LoggerLevelsOperations` bez zmiany sygnatur), klucze OpenAPI en i pl (de, es, fr, ko do translatora). Testy: `OAuthConfigExtRestTest` (3), `LoggerLevelsExtRestTest` (5), `LoggerLevelsOperationsTest` (5), razem 13/13.
- Statyczne `openapi*.json` nie obejmują usług `*ExtRest` (dokumentowane dynamicznie), więc po buildzie przywracać je z gita (zmieniają się tylko `version` i szum generatora).
- Do zrobienia w etapie 5: GUI odświeża konfigurację na każdym węźle (po liście węzłów z `NodeMonitorRest/load` i `?n=`).
