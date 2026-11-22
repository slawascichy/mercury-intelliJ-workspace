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
2. ✅ (2026-11-22, kod i test na klastrze; wdrożenie z obrazem) Szkielet `mercury-gui-auth` (moduł, WAR, `web.xml` z FORM i rolami, układ jak `pages/admin`), link w `ROOT/index.jsp`, w `mercury-gui-registry` i w `adminBar.jsp`; pakiet instalacyjny i obraz; sprawdzić nginx LB.
3. ✅ (2026-11-22, kod, testy i test na klastrze) Lokalni użytkownicy (lista, dodanie, edycja, hasło, wygaśnięcie) i profil własny.
4. Mapowania użytkowników i grup na role (lokalne i z LDAP) oraz przegląd użytkowników i grup LDAP (tylko odczyt, bez ujawniania danych połączenia).
5. Konfiguracja tokenów OAuth (`MRC_LDAP_OAUTH_CONFIG`, `MRC_LDAP_OAUTH_SERVICE`, przegląd `MRC_LDAP_OAUTH_TOKENS`), sekrety zamaskowane, odświeżenie po zapisie.
6. Audyt zmian, tłumaczenia (`admin.*`/nowe klucze przez translator), dokumentacja docusaurus (en i pl), test klastra, weryfikacja obs. 148.

## Stan etapu 1 (2026-11-22)

- `mercury-docker` (gałąź `hgdb-96`): `server.xml.docker-init` ma znacznik `TOMCAT_SSO_VALVE`, `mercury-server.sh` funkcja `initTomcatSsoValve` (klaster: `ClusterSingleSignOn`, jeden węzeł: `SingleSignOn`); sprawdzone na kopiach szablonu. Niewdrożone na klastrze (wymaga obrazu).
- `mercury` (gałąź `hgdb-96`): usługa `OAuthConfigExtRest` (`POST /rest/service/OAuthConfigExtRest/refresh`, `mrc-sysadmin`, tylko węzeł obsługujący żądanie), wspólne `AdminAccess` i `AdminEnvelope` (refaktor `LoggerLevelsExtRest` i `LoggerLevelsOperations` bez zmiany sygnatur), klucze OpenAPI en i pl (de, es, fr, ko do translatora). Testy: `OAuthConfigExtRestTest` (3), `LoggerLevelsExtRestTest` (5), `LoggerLevelsOperationsTest` (5), razem 13/13.
- Statyczne `openapi*.json` nie obejmują usług `*ExtRest` (dokumentowane dynamicznie), więc po buildzie przywracać je z gita (zmieniają się tylko `version` i szum generatora).
- Do zrobienia w etapie 5: GUI odświeża konfigurację na każdym węźle (po liście węzłów z `NodeMonitorRest/load` i `?n=`).

## Stan etapu 2 (2026-11-22)

**`mercury` (gałąź `hgdb-96`)**
- Nowy moduł `mercury-gui-auth` (WAR, 245 KB; zależności `provided`, w tym przesłonięty POI, bo nadrzędny pom dokłada go do wszystkich modułów i WAR miał 23 MB). Spring MVC + JSP (Bootstrap 3 i jQuery skopiowane z rejestru), kontekst Spring w WAR (`mercury-gui-auth-WebContextSpring.xml`, bez zmian w konfiguracji serwera), logowanie FORM (`/auth/inv_logon.jsp`, jedna strona błędu `inv_error.jsp`), `jsp-property-group` UTF-8 (bez niego dołączona stopka psuła polskie znaki).
- Adresy: `/ui/home` (karty sekcji wg ról), docelowo `/ui/profile`, `/ui/users`, `/ui/role-mappings`, `/ui/ldap`, `/ui/oauth`. Role (`AuthSection`, propozycja do potwierdzenia): profil = `mrc-user`, użytkownicy = `mrc-useradmin`, mapowania = `mrc-groupadmin`, LDAP (odczyt) = `mrc-useradmin` albo `mrc-groupadmin`, OAuth = `mrc-sysadmin`; `mrc-sysadmin` widzi wszystko. Sekcje są na razie oznaczone „wkrótce”.
- Teksty: `AuthAdminMsg` (domyślny angielski, `_pl`), źródła UTF-8 w `src/main/textmessages` i wynik `native2ascii` (linie w `native2ascii.sh`). Inne języki: translator.
- Podpięcie: moduł w głównym `pom.xml`, zależność WAR i kopiowanie do serwera dev w `mercury-server`, skrypt `restart-with-update-mercury-db.sh` (jenkins).
- Linki: `mercury-ws-app/pages/admin/include/adminBar.jsp` (dla `mrc-sysadmin`; klucz `app.index.systemAuth` w en i pl, tekst angielski do czasu tłumaczenia), menu opcji `mercury-gui-registry`, `ROOT/index.jsp` (tylko gdy kontekst zainstalowany).
- Test: `AuthSectionTest` (8).

**`mercury-cmd` (gałąź `hgdb-96`)**: pakiet instalacyjny kopiuje `mercury-gui-auth.war` do `installableApps` i etap `verify` przerywa budowanie, gdy go brak; skrypt `restart-with-update-mercury-db.sh`.

**`mercury-docker` (gałąź `hgdb-96`)**: `initTomcatCluster` tworzy deskryptor `mercury-gui-auth.xml` z `ClusterFormAuthenticator` (strona startowa `/ui/home`). Obraz kopiuje wszystkie `installableApps/*.war`, nginx przekazuje wszystkie ścieżki, więc dalszych zmian nie trzeba.

**Test na `mercury-cluster` (node2 i node3, wdrożenie ręczne, nietrwałe):** WAR i deskryptor wgrane do działających podów. Logowanie przez `mercury-ws-app` wpuszcza do nowej aplikacji na obu węzłach; logowanie przez nową aplikację wpuszcza do pozostałych; wylogowanie w nowej aplikacji kończy logowanie we wszystkich i na obu węzłach; admin widzi 5 sekcji, użytkownik tylko z `mrc-user` jedną (i 403 na `admin/loggers`); polskie teksty i znaki poprawne, strona 404 w wybranym języku. `adminBar.jsp` sprawdzony na żywo (link dla administratora). Po zmianie `web.xml` bez zmiany JSP trzeba wyczyścić katalog `work/.../mercury-gui-auth` (Tomcat nie rekompiluje niezmienionych JSP).

**Nie sprawdzone:** `ROOT/index.jsp` na działającym serwerze (zmiana prosta, wzorzec jak dla `mercury-ws-app`), instalacja z pakietu i obrazu (wymaga wydania), kompozycje Docker.

## Etap 3b (propozycja autora 2026-11-22): wspólny formularz logowania w `mercury-gui-auth`

Skoro jest SSO, wszystkie aplikacje FORM (`mercury-ws-app`, `mercury-gui-registry`) mogłyby używać jednego formularza z `mercury-gui-auth`, **ale tylko wtedy, gdy ta aplikacja jest zarejestrowana i działa**; inaczej zostaje lokalny formularz (nie może być przekierowania do nieistniejącej aplikacji).

**Jak rejestruje się `mercury-ws-app` (sprawdzone w kodzie):** w `mercuryWebContextSpring.xml` jest bean `pro.ibpm.mercury.webapp.registry.MercuryModuleRegistry` z `init-method="writeInfo"` i plikiem `mercury-db-module.properties` (`module.id`, `module.relpath`, `module.scope`...; `mercury-gui-registry` ma swój bean i plik). `writeInfo` dopisuje wpis do pliku właściwości w `java.io.tmpdir` (z plikiem blokady) przez singleton `MercuryModuleRegistryData` z `mercury-core` (biblioteka z `$HGDB_HOME/lib`, więc wspólna dla aplikacji w jednym Tomcacie). Rejestr czyta go REST-em (`getLoadModules`, `getCheckRegistered?moduleId=`, za OAuth), a w procesie wystarczy `MercuryModuleRegistryData.getInstance().checkRegistered(id)`. **Ograniczenie:** API nie ma wyrejestrowania, a plik leży w `/tmp`, więc po usunięciu aplikacji wpis może zostać. Samo „zarejestrowana” nie gwarantuje, że aplikacja działa.

**Projekt:**
1. `mercury-gui-auth` rejestruje się jak `mercury-ws-app` (bean `MercuryModuleRegistry` z właściwościami podanymi wprost w `mercury-gui-auth-WebContextSpring.xml`, bez pliku w konfiguracji serwera): `module.id=mercury-gui-auth`.
2. Strona logowania każdej aplikacji (`/auth/inv_logon.jsp`) sprawdza: (a) `checkRegistered("mercury-gui-auth")` i (b) krótki, buforowany (np. 30 s) test, że `/mercury-gui-auth/auth/inv_logon.jsp` odpowiada 200 (HEAD na `127.0.0.1` na porcie żądania, timeout poniżej sekundy). Gdy oba warunki są spełnione, przekierowuje na `/mercury-gui-auth/auth/inv_logon.jsp?returnTo=<adres oryginalnego żądania>`, inaczej pokazuje lokalny formularz. Logika w jednym pomocniku (np. w `mercury-gui-core`, który jest już w `$HGDB_HOME/lib`), wołanym z JSP.
3. `returnTo` walidowany (otwarte przekierowanie): tylko ścieżka względna zaczynająca się od `/`, bez `//` i schematu, w kontekście zarejestrowanej aplikacji. Zapis w sesji `mercury-gui-auth`; po zalogowaniu strona startowa aplikacji (`/ui/home`) przekierowuje na zapisany adres. Wspólne ciasteczko SSO (`JSESSIONIDSSO`) wpuszcza użytkownika do aplikacji docelowej.
4. Po zalogowaniu przez wspólny formularz, jeśli hasło lokalnego użytkownika wygasło, najpierw propozycja zmiany hasła (profil), potem `returnTo`.
5. Zmiany w `mercury-ws-app` i `mercury-gui-registry` (JSP logowania), ewentualnie `mercury-gui-core` (pomocnik, wymaga `install`); testy: brak `mercury-gui-auth` (lokalny formularz), aplikacja zarejestrowana, ale zatrzymana (lokalny formularz), obie aplikacje działają (przekierowanie i powrót), próby otwartego przekierowania.

## Etap 3c (decyzja autora 2026-11-22): własny klucz licencji `mercury-gui-auth`

Aplikacja ma być licencjonowana osobno, z konfigurowalną nazwą produktu, według wzoru licencji serwera.

**Jak działa licencja serwera (sprawdzone w kodzie):**
- `org.hgdb.tools.license.LicenseHelper` (moduł `hgdb-tools`): singleton, plik klucza `LicenceKey.txt` (parametr `mercury.license.file`), treść to linie `klucz=wartość` zaszyfrowane `SimpleBlowfishEncoderDecoder` (sccommon) i złamane co 80 znaków. Pola: `serialNo`, `cn` (nazwa produktu), `maxNodes`, `org`, `type` (`TRIAL`, `COMMUNITY`, `SINGLE_NODE`, `ENTERPRISE`, `GPU_ENTERPRISE`), dane kontaktowe i `expiration` (ms).
- Nazwa produktu z parametru `mercury.product.name` musi być równa `cn` w kluczu; inaczej `LicenseException`. Dla typów jednowęzłowych sprawdza też, że nie jest włączony klaster i nazwa węzła to `node1`; dla pozostałych, że nazwa węzła mieści się w `node1..nodeMaxNodes`.
- Brak pliku: generuje licencję `TRIAL` (30 dni, 3 węzły), nazwa produktu z parametru albo domyślna `Mercury DB (HgDB) 3.0 - Trial`.
- Egzekwowanie: `LicenseValidator` (mercury-srv, zapamiętuje datę wygaśnięcia) w `CaseLogic` blokuje wstawianie i usuwanie spraw po wygaśnięciu (odczyt działa). `mercury-ws-app` pokazuje dane licencji na stronie głównej i ostrzega na 30 dni przed końcem (`MainController`).
- Generator kluczy: testowa klasa `Generator` w `hgdb-tools`.

**Projekt dla `mercury-gui-auth`:** osobne parametry w `mercury.properties` (np. `mercury.gui.auth.product.name`, `mercury.gui.auth.license.file`, domyślny plik `LicenceKeyAuth.txt`), ta sama szyfrowana postać klucza i ten sam generator (z nazwą produktu aplikacji). `LicenseHelper` ma na sztywno nazwy parametrów i sprawdzanie węzłów, więc trzeba go sparametryzować małymi, chronionymi metodami (nazwy parametrów, plik domyślny, nazwa domyślna, sprawdzanie węzłów) i dopiero na tym oprzeć `AuthLicenseValidator`; zmiana w `hgdb-tools` dotyka licencji serwera, więc z testami `LicenseHelperTest`. Strona `/ui/license` (dane licencji i ostrzeżenie przed końcem).

**Do rozstrzygnięcia przed realizacją:**
1. Co robi aplikacja po wygaśnięciu albo przy niepasującym kluczu: (a) blokada zmian, odczyt działa (jak serwer), (b) pełna blokada, (c) tylko ostrzeżenie.
2. Brak pliku klucza: automatyczna licencja `TRIAL` 30 dni (jak serwer) czy tryb tylko do odczytu.
3. Czy sprawdzanie węzłów (`maxNodes`, `node1..N`) ma dotyczyć aplikacji, czy tylko nazwa produktu i data.

*Uwaga autora (2026-11-22):* moduł `license-registry` w repozytorium `mercury` to nieskończona aplikacja do zarządzania kluczami klientów (szkielet: `App.java`, `web.xml`). Nie jest podstawą etapu 3c; klucze generuje na razie klasa `Generator` w `hgdb-tools`.

## Stan etapu 3 (2026-11-22): lokalni użytkownicy i profil własny

**Zakres (`mercury`, gałąź `hgdb-96`, moduł `mercury-gui-auth`):** sekcje „Lokalni użytkownicy” (`/ui/users`: lista z rolami przypisanymi wprost, dodanie, zmiana, usunięcie) i „Mój profil” (`/ui/profile`: pełna nazwa, zmiana hasła). Dane przez JDBC na zasobie JNDI `jdbc/MercuryLdapDBPoSql` (to samo źródło co realm), SQL ANSI, nazwy tabel i kolumn z `DbConstants` (te same co w realmie). Profil własny to tylko pełna nazwa i hasło (decyzja autora: tabela nie ma kolumn kontaktowych, bez zmiany schematu).

**Reguły (`LocalUserService`):**
- Skrót hasła jak w realmie: SHA1 z `nazwa/hasło` (`PasswordService`; test porównuje skrót `admin/admin` z wartością z DDL). Algorytm sprawdzany przy starcie (`SecurityPassword` przy nieznanym algorytmie tylko loguje błąd i zwracałby pusty skrót). Nazwa użytkownika niezmienna (wchodzi do skrótu); `[A-Za-z0-9._@-]{1,128}`.
- Hasło 8-128 znaków, różne od nazwy. Zmiana własnego hasła wymaga obecnego hasła.
- **Zmiana hasła przesuwa datę ważności o interwał z parametru** `mercury.gui.auth.password.expirationDays` w `mercury.properties` (domyślnie 120 dni jak interwał hasła w realmie, `0` wyłącza; opis w `mercury-docker/.../config/mercury.properties`). Dotyczy zmiany własnej i zmiany przez administratora (data z formularza jest wtedy pomijana); przy dodawaniu konta data z formularza (podpowiedź: teraz plus interwał).
- **„Bezterminowo”** (formularze administratora: dodanie i zmiana): data ważności 4000-01-01 00:00 UTC (`LocalUser.NEVER_EXPIRES` = 64060588800000), ma pierwszeństwo przed polityką i datą z formularza. W formularzu własnej zmiany hasła pola nie ma (każdy mógłby ominąć politykę).
- Ochrona: użytkownik nie usuwa własnego konta; zmienić hasło lub usunąć konto z rolą `mrc-sysadmin` (przypisaną wprost) może tylko administrator systemu (inaczej `mrc-useradmin` przejąłby konto administratora). Usunięcie konta usuwa jego mapowania ról typu `U` (typu `G` nie rusza).
- Formularze: POST z tokenem CSRF (sesja, `CsrfToken`), zapisz-i-przekieruj z komunikatem (`Flash`), brak tokenu lub roli to 403; wartości wypisywane przez `c:out`/`fn:escapeXml`, potwierdzenie usuwania w `data-confirm`. Niedostępna baza lub brak zasobu JNDI to komunikat, nie błąd 500.
- **Wygasłe hasło po zalogowaniu (propozycja autora):** `PasswordExpiryFilter` przekierowuje żądania GET w `/ui/*` lokalnego użytkownika z minioną datą na `/ui/profile?expired=1` z ostrzeżeniem i odnośnikiem „Kontynuuj bez zmiany” (wyłącza propozycję do końca sesji). Realm nie blokuje logowania po dacie ważności, więc to propozycja, nie wymuszenie. Konta spoza lokalnego repozytorium (LDAP) nie są przekierowywane. Dotyczy tylko wejścia przez `mercury-gui-auth`; wejście wprost do `mercury-ws-app` tego nie robi (patrz etap 3b: wspólny formularz).

**Konfiguracja opcjonalna** (właściwości systemowe JVM, np. w `CATALINA_OPTS`): `mercury.gui.auth.dsJndiName`, `mercury.gui.auth.schema`, `mercury.gui.auth.messageDigest` (musi być taki sam jak w realmie).

**Testy:** 44 jednostkowe (`AuthSectionTest` 8, `LocalUserServiceTest` 19 na HSQLDB 2.3.2 w pamięci, bo 2.7.x wymaga Javy 11, `PasswordServiceTest` 5, `PasswordExpiryPolicyTest` 5, `WebHelpersTest` 7). **Test na `mercury-cluster`** (skrypt `scratchpad/sso/stage3_live.sh`, 40 sprawdzeń, 0 błędów): dodanie użytkownika przez GUI i logowanie nim do `mercury-ws-app` (zgodność z realmem), „bezterminowo” zapisane jako 4000-01-01, CSRF (403), uprawnienia (`mrc-user` bez listy użytkowników), propozycja zmiany wygasłego hasła i „kontynuuj”, zmiana hasła przesuwa ważność o 120 dni, stare hasło przestaje działać, `mrc-useradmin` nie przejmuje konta administratora, usunięcie z mapowaniami, administrator nie usuwa siebie. Po teście baza bez zmian (1 użytkownik, hasło admina niezmienione).

**Wdrożenie:** WAR wgrany ręcznie na node2 i node3 (nietrwale, do wydania). Do ustalenia/zrobienia: dokumentacja (docusaurus, etap 6), tłumaczenia `AuthAdminMsg` na de, es, fr, ko (translator).

## Etap 3d (wymaganie autora 2026-11-22): formularz „Aktualizacja klucza licencji” (`mercury-gui-auth` i `mercury-ws-app`)

Rola `mrc-sysadmin`, pole tekstowe na klucz. Po wysłaniu: (1) kopia starego pliku z kluczem na wszystkich węzłach (możliwość „back”), (2) nowy plik z kluczem na wszystkich węzłach i przeładowanie klucza na wszystkich węzłach, (3) pytanie: czy klucz może być w bazie.

**Stan dziś (sprawdzone na `mercury-cluster`):**
- Położenie pliku wskazuje parametr `mercury.license.file` w `mercury.properties` (obraz Docker: `/opt/mercury-3.0/lucene/LicenseKey.txt`, czyli wolumen `lucene` **danego węzła**, na NFS `mercury-lucene-N`; domyślna nazwa w kodzie to `LicenceKey.txt`, inna pisownia). Plik jest czytany przy każdym `getLicenseData`; `LicenseValidator` (serwer) zapamiętuje tylko datę wygaśnięcia, więc po zmianie klucza trzeba ją odświeżyć.
- Każdy węzeł ma **własny, inny** klucz: node2 i node3 wygenerowały przy pierwszym starcie osobne licencje Trial (różne `serialNo` i `expiration`, skróty plików różne). Prawdziwy klucz trzeba dziś ręcznie skopiować na każdy węzeł, a węzeł wyłączony w tym czasie zostaje ze starym.
- Nie ma gotowego mechanizmu „wykonaj na wszystkich węzłach” (strony administracyjne działają per węzeł, `?n=`; konfiguracja OAuth z etapu 1 ma ten sam problem).

**Wniosek: klucz w bazie jest lepszy niż pliki na węzłach** (jedno źródło prawdy, bez rozsyłania, węzeł offline dogania po powrocie, historia zamiast kopii plików):
- Tabela w bazie realmu (dostępna z obu aplikacji przez `jdbc/MercuryLdapDBPoSql`, zwykły JDBC; DDL dla 5 baz w skryptach `MRC_LDAP_CREATE_SCHEMA_*.sql` plus skrypt dla istniejących instalacji), np. `MRC_LICENSE_KEYS`: id, produkt (`mercury-server`, `mercury-gui-auth`), tekst klucza (zaszyfrowany blob jak w pliku), data dodania, kto dodał, znacznik aktywnej wersji i pola wyciągnięte z klucza (typ, `cn`, `expiration`, `serialNo`).
- „Back” to aktywacja poprzedniej wersji z historii.
- Przeładowanie na węzłach przy starcie i na zdarzenie (komunikat JMS na nowym Virtual Topic, bez odpytywania bazy; patrz korekta niżej). Każdy węzeł po zmianie zapisuje klucz także do pliku z `mercury.license.file` i robi kopię poprzedniego (`.bak` ze znacznikiem czasu): to spełnia (1) i (2) bez rozsyłania, a plik zostaje rezerwą przy niedostępnej bazie.
- Pierwszeństwo: baza, potem plik (zgodność wsteczna: puste tabele i błąd bazy dają dzisiejsze zachowanie, w tym licencję Trial).
- Walidacja przed zapisem (żeby zły klucz nie zablokował serwera, bo przy nieprawidłowej nazwie produktu `CaseLogic` blokuje zapisy): odszyfrowanie, wymagane pola, `cn` równe skonfigurowanej nazwie produktu, data w przyszłości, test `checkLicense` dla bieżącego węzła; wynik (typ, organizacja, ważność) pokazany po zapisie.
- Wspólna usługa (np. w `hgdb-tools`: `LicenseKeySource` z implementacją DB i plikową) dla serwera (`LicenseValidator`) i dla licencji `mercury-gui-auth` (etap 3c), a formularz w każdej aplikacji obsługuje klucz swojego produktu.
- Uwaga techniczna: `LicenseHelper` jest w bibliotece wspólnej (common loader) i czytany także poza wątkami aplikacji; źródło DB powinno dostać `DataSource` od aplikacji (rejestracja przy starcie), a nie szukać JNDI samodzielnie.

**Pytanie autora (2026-11-22): osobne bazy dla modułów?** Dwa moduły (serwer i `mercury-gui-auth`) mają osobne klucze. Osobne klucze nie wymagają osobnych baz (kolumna „produkt” albo osobne tabele), ale osobne bazy dają niezależność licencjonowania.
- **Opcja A, klucz w bazie swojego modułu** (serwer w `mercury-db`, `mercury-gui-auth` w `mercury-ldap`): niezależność, brak ryzyka nadpisania cudzego klucza, kopia bazy przywraca klucz z danymi modułu. Koszt: `mercury-db` nie ma ręcznego DDL (tabele z encji w `mercury-lib`, osobne repozytorium i wydanie biblioteki), więc tabela klucza to nowa encja albo własny DDL dla 5 baz; `mercury-gui-auth` nie widzi głównej bazy, więc jego formularz zarządza tylko własnym kluczem.
- **Opcja B, jedna tabela w bazie realmu** (`MRC_LDAP_*`, ręczne DDL dla 5 baz, skrypt inicjujący w obrazie Postgresa, JDBC już używany przez realm, OAuth i `mercury-gui-auth`) z kolumną „produkt”: najmniej pracy, ale moduły dzielą bazę klucza.
- **Rekomendacja:** B na start, ze wspólną usługą opartą na `DataSource` i nazwie tabeli, żeby późniejsze przeniesienie klucza serwera do `mercury-db` (A) nie wymagało przeróbki formularzy ani walidatora. Gdy niezależność jest wymogiem od razu: A z wydaniem `mercury-lib`.
- Zapis klucza także do pliku z `mercury.license.file` (kopia `.bak` plus nowy plik na każdym węźle) jako rezerwa: domyślnie tak, do decyzji autora.

**DECYZJA AUTORA (2026-11-22): opcja A, plik jako rezerwa.** Klucz serwera w głównej bazie `mercury-db`, klucz `mercury-gui-auth` w bazie realmu `mercury-ldap`; każdy węzeł zapisuje aktywny klucz także do pliku z `mercury.license.file` (kopia poprzedniego pliku jako `.bak` ze znacznikiem czasu).

**Schemat w `mercury-db`:** w obrazie `hibernate.hbm2ddl.auto=update` (PostgreSQL, MySQL, Oracle; `create` dla MSSQL i HSQL), więc nowa encja w `mercury-entities` (`mercury-lib`) utworzy tabelę przy starcie serwera, bez ręcznego DDL. Wymaga wydania `mercury-lib` (podniesienie wersji w `mercury`, `hgdb-client-open`, `mercury-cmd`).

**Kolejność realizacji (3c i 3d razem, bo dzielą infrastrukturę licencji):**
1. `mercury-lib`: encja klucza licencji serwera (tabela np. `MRC_LICENSE_KEYS`: id, tekst klucza, data dodania, kto dodał, aktywna, `serialNo`, `cn`, typ, `expiration`) i wydanie biblioteki (robi autor).
2. `hgdb-tools`: `LicenseHelper` sparametryzowany (nazwy parametrów, plik i nazwa domyślne, sprawdzanie węzłów) oraz źródło klucza (`LicenseKeySource`) z implementacją plikową (obecne zachowanie plus zapis z kopią `.bak`) i bazodanową; rejestracja `DataSource` przez aplikację przy starcie. Testy `LicenseHelperTest` dalej zielone.
3. Serwer (`mercury-srv`, `mercury-ws-app`): zapis i odczyt klucza w `mercury-db`, przeładowanie przy starcie i na zdarzenie JMS, przeładowanie `LicenseValidator` i zapis do pliku na każdym węźle, walidacja przed zapisem (odszyfrowanie, pola, `cn` = nazwa produktu, data w przyszłości, `checkLicense` dla bieżącego węzła), formularz „Aktualizacja klucza licencji” (`mrc-sysadmin`) w stronach administracyjnych z historią i „back” (aktywacja poprzedniej wersji).
4. `mercury-gui-auth`: własna licencja (`AuthLicenseValidator`, nazwa produktu z parametru), klucz w bazie realmu (tabela dochodzi do `MRC_LDAP_CREATE_SCHEMA_*.sql` dla 5 baz, skryptu inicjującego w obrazie Postgresa i skryptu dla istniejących instalacji), to samo odpytywanie i zapis do pliku, formularz w aplikacji, strona `/ui/license`.

**Nadal do rozstrzygnięcia (etap 3c):** zachowanie po wygaśnięciu lub przy niepasującym kluczu (blokada zmian, pełna blokada, tylko ostrzeżenie), brak klucza (automatyczne Trial czy tylko odczyt), czy sprawdzać liczbę węzłów.

**Korekta decyzji (autor, 2026-11-22): encja klucza serwera leży w `mercury-core-server`, nie w `mercury-lib`** (to funkcja tylko serwera, więc bez wydania biblioteki współdzielonej; punkt 1 kolejności realizacji odpada). Tabelę tworzy Hibernate (`hbm2ddl=update`) z encji.

**Stan (2026-11-22):** krok 1 ✅ w `mercury-core-server`, pakiet `org.mercury.license`: encja `LicenseKeyEntry` (tabela `IGO_DA_LICENSE_KEYS`, 12 kolumn: id (UUID), tekst klucza do 4000 znaków, numer seryjny, nazwa produktu, typ, organizacja, data wygaśnięcia, data i autor dodania, data i autor aktywacji, znacznik aktywności; jawnie `@Cacheable(false)`, bo cache drugiego poziomu jest włączony, a klucz musi być czytany zawsze z bazy), interfejs `LicenseKeyRepository` i `JpaLicenseKeyRepository` (`findActive`, `findAll`, `find`, `addActive` z dezaktywacją poprzednich, `activate` jako „back”; przy kilku aktywnych po równoczesnym zapisie obowiązuje najpóźniej aktywowany). Pakiet `org.mercury.license` dopisany do skanowania encji jednostki `mercuryDB` i skanowania komponentów w `dao-context.xml` (`mercury-dao`) i `logic-context.xml` (`mercury-srv`). Test `JpaLicenseKeyRepositoryTest` (8) na prawdziwym Hibernate i HSQLDB 2.3.2 w pamięci (sprawdza też mapowanie tabeli); zależność testowa HSQLDB 2.3.2 w `pom.xml` modułu, bo dziedziczony 2.7.1 wymaga Javy 11. Do zrobienia: kroki 2-4 (źródło klucza w `hgdb-tools`, serwer i formularz, `mercury-gui-auth`).

**Stan (2026-11-22), krok 2 ✅ `hgdb-tools` (pakiet `org.hgdb.tools.license`):**
- `LicenseHelper` sparametryzowany bez zmiany dotychczasowych sygnatur (`Generator`, `LicenseValidator` bez zmian): przesłanialne `licenseFileProperty()`, `productNameProperty()`, `defaultLicenseLocation()`, `defaultTrialProductName()` i `checkNodes(type, data)` (domyślnie obecne ograniczenia węzłów; licencja `mercury-gui-auth` może je wyłączyć). Logika sprawdzania wydzielona do `evaluate(data, print)`; nieznany typ licencji i liczby w kluczu dają `LicenseException` zamiast wyjątku uruchomieniowego.
- Źródło klucza: interfejs `LicenseKeySource` (`readActiveKey`, `readActiveVersion`) i `LicenseHelper.setKeySource(...)`. **Klucz ze źródła ma pierwszeństwo przed plikiem; przy braku klucza, błędzie odczytu (baza niedostępna) albo uszkodzonym kluczu obowiązuje plik** (rezerwa), a przyczyna trafia do dziennika. `readKeyVersion()` do taniego sprawdzania, czy klucz się zmienił.
- Klucz z tekstu: `parseKey(text)` (CRLF, puste linie, komentarze i spacje na brzegach pomijane; wyjątek dla pustego, nieodszyfrowalnego i niepełnego klucza), `normalizeKeyText` (postać zapisywana w bazie i pliku), `encodeKey`.
- **Walidacja przed zapisem klucza:** `validateKeyForInstall(text)`: odszyfrowanie, wymagane pola, nazwa produktu równa skonfigurowanej, ograniczenia węzłów bieżącego węzła, data w przyszłości; dzięki temu zły klucz nie zablokuje serwera.
- Zapis do pliku: `LicenseKeyFile.write(plik, klucz)` i `LicenseHelper.mirrorKeyToFile(klucz)`: ten sam klucz nic nie zmienia, zmieniony klucz robi kopię `<plik>.<rrrrMMdd-HHmmss>.bak` (przy kolizji z numerem), zapis atomowy (plik tymczasowy i przeniesienie).
- Testy: `LicenseKeySourceTest` (10) i dotychczasowy `LicenseHelperTest` (1) zielone; `mercury-srv` kompiluje się z nową wersją. Klasa testowa `TestLicenseHelper` pokazuje, jak licencja innego produktu przesłania parametry.
- Do zrobienia w kroku 3 (serwer): `LicenseValidator.reload()` (zapamiętuje datę wygaśnięcia), źródło klucza oparte na `LicenseKeyRepository`, odbiornik zdarzenia JMS „klucz zmieniony” i zapis do pliku, formularz w `mercury-ws-app`.

**Korekta (autor, 2026-11-22): bez okresowego odpytywania bazy.** Licencja jest czytana przy starcie węzła i na zdarzenie „klucz zmieniony”, nie co kilkadziesiąt sekund.
- **Zdarzenie przez ActiveMQ:** w projekcie jest gotowy mechanizm rozsyłania do wszystkich węzłów (`JmsDestinations`, zadanie 82): temat `VirtualTopic.<nazwa>` i kolejka każdego węzła `Consumer.<węzeł>.VirtualTopic.<nazwa>`, tworzona przez broker, gdy węzeł się zgłosi; ten sam wzorzec Sender, Receiver i Listener mają zmiany typów, definicji i atrybutów. Nowy temat np. `VirtualTopic.mrc-license-key-changes`, publikowany po zapisie lub „back” w formularzu. Konfiguracja brokera (reguła `VirtualTopic.>` z przedrostkiem `Consumer.*.`) już obejmuje nowe tematy.
- **Odbiornik na każdym węźle** (także tym, który wysłał, bo przeładowanie jest idempotentne): odczyt aktywnej wersji z bazy, walidacja (`parseKey`), zapis do pliku z kopią `.bak`, `LicenseValidator.reload()`. To samo przy starcie węzła.
- **Dlaczego to jest niezawodne:** węzeł wyłączony w chwili zmiany ma kolejkę z komunikatem (o ile kiedyś się zgłosił) i przeładuje klucz po powrocie; węzeł, który nigdy się nie zgłosił, czyta klucz z bazy przy starcie; przy niedostępnej bazie obowiązuje plik. Ryzyko: komunikat utracony przy restarcie brokera bez trwałego magazynu; w razie czego przycisk „Przeładuj na tym węźle” w formularzu (opcjonalny) i restart węzła.
- **Dla `mercury-gui-auth`:** ta aplikacja nie ma JMS w swoich zależnościach; jej licencja (klucz w bazie realmu) wymaga albo własnego, lekkiego powiadomienia (np. wywołanie `refresh` per węzeł z GUI, jak przy konfiguracji OAuth z etapu 1), albo JMS. Do rozstrzygnięcia przy etapie 4 licencji.
