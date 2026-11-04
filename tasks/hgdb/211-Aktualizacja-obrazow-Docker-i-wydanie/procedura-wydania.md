# Procedura wydania (211a): pakiet instalacyjny i obrazy Docker

Stan: 2026-11-04, szkic wykonany na gałęzi `hgdb-211` (`mercury-docker`, `mercury-cmd`). Procedura jest **cykliczna**: uruchamiamy ją jako release candidate przy zamknięciu większych pakietów zadań, a jako wydanie ostateczne (211b) po zadaniach 191, 209 i 223. Publikacja na Docker Hub i na `hgdb.org` jest opcjonalna i należy do autora.

Skrypty leżą w `mercury-docker/bin/release/` (nie robią commitów):

| Skrypt | Do czego |
|---|---|
| `set-versions.sh` | podbicie wersji w `mercury-docker` (Dockerfile, kompozycje, README, Helm) i w głównym `pom.xml` `mercury-cmd` (`mercury.srv.version`, `mercury.lib.version`, `hgdb-client.version`); bez `--apply` tryb próbny |
| `verify-cache-config.sh` | kontrola konfiguracji pamięci klastrowych: wymagane regiony klastrowe, identyczne rozmiary tych samych aliasów, suma w `primary-server-resource` |
| `build-and-push-images.sh` | budowa obrazów i wysyłka do Nexusa (`docker-hosted`); `--dry-run`, `--all` (z obrazami pomocniczymi) |
| `smoke-test.sh` | test dymny kompozycji na maszynie z Dockerem: kontenery, `/rest/openapi.json` bez tokenu, `/rest/token`, błędy krytyczne w logach |

## Kroki

1. **Warunki wstępne (autor).** Wydane i otagowane: `mercury-lib`, `sccommon` (jeśli zmieniony), `mercury`, `hgdb-client-open` (jeśli zmieniony). Pakiet instalacyjny składa się z plików **katalogu serwera dev** (`CATALINA_BASE`) i z `target` w repozytorium `mercury`, a nie z pobranych artefaktów, więc katalog serwera dev musi pochodzić z tego samego wydania (spójny `install` i WAR). Niezgodność wykryje krok 4 (weryfikacja Ant).
2. **Decyzje o wersjach.** Wersja serwera (`--srv`, np. `3.0.4.13`) jest też wersją pakietu i znacznikiem obrazu `ibpm/mercury:mercury-hgdb-<wersja>`. Dalej: `--lib`, `--client`, baza (`--db`, domyślnie `POSTGRESQL`), data nazwy pakietu (domyślnie dzisiejsza).
3. **Podbicie wersji.**
   ```bash
   cd mercury-docker/bin/release
   ./set-versions.sh --srv 3.0.4.13 --lib 3.0.4.21 --client 3.1.4.19          # próbnie
   ./set-versions.sh --srv 3.0.4.13 --lib 3.0.4.21 --client 3.1.4.19 --apply  # zmiana plików
   ```
4. **Budowa pakietu** z korzenia `mercury-cmd` (jary CLI w `libExt` powstają z modułów w wersji serwera, więc samo `mercury-install-package` nie wystarczy): `mvn -o install -Dmaven.test.skip=true -Ddatabse.provider=POSTGRESQL`. Cel `verify` w `build-installation.xml` (zadanie 214) przerywa budowę, gdy wersje jarów, WAR-a (`info.version` w `openapi_en.json`) lub logowanie nie zgadzają się z właściwościami POM. Wynik: `releases/mercury-install-package-<wersja>.<DB>.<data>.zip`.
5. **Kontrola pamięci klastrowych** (dodatek do kroku 4, bo Ant nie czyta XML Ehcache):
   ```bash
   ./verify-cache-config.sh \
     ../../mercury-3.0/docker-init-config/config/ehcacheDefault.xml ../../mercury-3.0/docker-init-config/config/ehcacheCommon.xml \
     ../../../mercury-cmd/mercury-install-package/system-config-sample/linux/config/ehcacheDefault.xml \
     ../../../mercury-cmd/mercury-install-package/system-config-sample/linux/config/ehcacheCommon.xml \
     ../../../mercury-cmd/mercury-install-package/system-config-sample/linux/ehcache-clustered/server/conf/tc-config.xml \
     ../../ehcache/conf/1/node1-config.xml
   ```
   Błędem jest brak wymaganego regionu klastrowego i różne rozmiary tego samego aliasu; ostrzeżeniem suma powyżej 70% zasobu serwera. Można też podać pliki rozpakowanego pakietu.
6. **Wgranie pakietów do Nexusa.** Dockerfile'e pobierają pakiety (instalacyjny serwera, Tomcat, JDK, serwer Terracotta, poi-toolkit) z repozytorium `raw` `mercury-docker-packages` na `nexus.scisoftware.local` (`ARG PACKAGES_URL`; odczyt anonimowy). Wysyła je `./upload-packages.sh` (`NEXUS_USER`, `NEXUS_PASSWORD`; pomija pliki już obecne, `--force` nadpisuje). Pliki Tomcata, JDK, kitu Terracotty i poi-toolkit są lokalnie w `mercury-docker/*/install` (`hgdb.org` odpowiada na nie 403).
7. **Budowa i wysyłka obrazów** na maszynie z Dockerem (np. `devops-box-01`):
   ```bash
   export REGISTRY=nexus.scisoftware.local:5000 NEXUS_USER=... NEXUS_PASSWORD=...
   ./build-and-push-images.sh --dry-run              # obejrzyj polecenia
   ./build-and-push-images.sh                        # tylko obraz serwera
   ./build-and-push-images.sh --all                  # także obrazy pomocnicze
   ```
   Rejestr w Nexusie działa po HTTP, więc demon Dockera wymaga `insecure-registries` w `daemon.json`. Hasło idzie do `docker login --password-stdin` i nie jest wypisywane.
8. **Test dymny.**
   ```bash
   ./smoke-test.sh --registry nexus.scisoftware.local:5000                       # jednowęzłowa
   ./smoke-test.sh --compose ../../mercury-two-node-cluster --registry nexus.scisoftware.local:5000
   ```
   Kompozycje czytają prefiks rejestru ze zmiennej `HGDB_REGISTRY` (pusta = Docker Hub), np. `HGDB_REGISTRY=nexus.scisoftware.local:5000/ docker compose up -d`. Dla Helma: `image.registry` w `values.yaml`.
9. **Publikacja (opcjonalnie, autor).** Docker Hub (`ibpm/...`) i `hgdb.org`, tylko dla wydania ostatecznego.
10. **Dokumentacja (211b).** Artykuły o Docker i Kubernetes w `docusaurus-hgdb`, `docs/moduly/mercury-docker.md`, `mercury-cmd.md`.

## Stan sprawdzenia skryptów (2026-11-04)

- `set-versions.sh`: tryb próbny na prawdziwych repozytoriach i `--apply` na kopii (11 plików w `mercury-docker`, 3 właściwości w `pom.xml`); po zmianie 0 wystąpień starej wersji.
- `verify-cache-config.sh`: uruchomiony na plikach z `mercury`, `mercury-docker`, `mercury-cmd` i z pakietu: błędów 0, ostrzeżeń 0 (suma 388 MB wobec zasobu 1024 MB; przed podniesieniem zasobu z 512 MB było 6 ostrzeżeń).
- Pakiet RC `mercury-install-package-3.0.4.13.POSTGRESQL.20261104.zip` (136 MB) zbudowany z korzenia `mercury-cmd`, weryfikacja Ant zakończona powodzeniem; w `lib` 14 jarów serwera w 3.0.4.13 i 6 jarów `mercury-lib` w 3.0.4.21, `sccommon` 2.0.0.4 (z `sccommon-ldap`), w `libExt` CLI 3.0.4.13 i klient 3.1.4.19; kontrola pamięci klastrowych na plikach pakietu: błędy 0, ostrzeżenia 0.
- `build-and-push-images.sh`: tylko `--dry-run` (na maszynie roboczej nie działa `docker pull`).
- `smoke-test.sh`: nieuruchomiony (wymaga Dockera i obrazów); sprawdzona składnia.

## Znalezione przy okazji

- Pliki `ehcacheCommon.xml` w `mercury-docker` i `mercury-cmd` (przykłady) mają 4 regiony, a plik serwera dev (`mercury/mercury-server/IBPM/mercury/config`) 6 (dodatkowo `CaseGlobalTransactionCache` i `CaseLocalTransactionCache`). Przykłady rozjechały się z plikiem dev; plik używany przez serwer to `ehcacheDefault.xml` (`cache.configPath`), więc skutek jest ograniczony.
- Zasób Terracotty `primary-server-resource` podniesiony z 512 do 1024 MB (decyzja autora 2026-11-04) w `mercury-docker/ehcache/conf/*` i w pakiecie `mercury-cmd`; regiony klastrowe zajmują 388 MB.
- Rejestr Nexusa: repozytoria Dockera `docker-hosted`, `docker-proxy` (Docker Hub) i `docker-group` istnieją. `docker-hosted` obsługuje port **5000** (potwierdzone w ustawieniach repozytorium: `httpPort` 5000, tylko HTTP, `forceBasicAuth`); 5001 to inne repozytorium Dockera. Konto `claude` ma dostęp do rejestru (`/v2/_catalog` zwraca 200); zapis (push) nie był jeszcze sprawdzony.
- **Błąd reguły weryfikacji Ant (zadanie 214), poprawiony.** Reguła nr 3 wymagała, by wszystkie jary `mercury-*` i `hgdb-*` w `lib` miały wersję `mercury.lib.version`, a jary serwera z repozytorium `mercury` mają `mercury.srv.version`. Działało, dopóki obie wersje były równe; przy 3.0.4.21 i 3.0.4.13 budowa przerywała się. Reguła dopuszcza teraz obie wersje (`build-installation.xml`, README `mercury-cmd`).
- Pliki `config` pakietu zawierają ścieżki `D:/workspace/...` z katalogu serwera dev (tak było też w pakiecie 3.0.3.2.11); obraz nadpisuje je plikami z `docker-init-config`. Sprawdzi to test dymny.

## Obrazy bazowe (zmiana 2026-11-04, decyzja autora: nowsze i odporniejsze na podatności)

| Obraz | Było | Jest | Uwagi |
|---|---|---|---|
| `mercury` (`mercury-3.0`), `mercury-lb`, `openldap` | `centos:8` (po końcu wsparcia, repozytoria z `vault.centos.org`) | `almalinux:9` (`ARG BASE_IMAGE`) | zgodny z RHEL 9, wspierany do 2032, tagi aktualizowane co miesiąc (w proxy Nexusa 9.8-20261002). Wybór AlmaLinux zamiast Rocky: oficjalny obraz `rockylinux` w proxy ma tagi tylko do 2023 r. Wybór EL9 zamiast EL10: EL10 wymaga procesora x86-64-v3, czego nie zawsze mają maszyny wirtualne (domyślny typ CPU na Proxmoksie). Usunięty blok czyszczenia systemd i przepinania repozytoriów na `vault`. |
| `activemq`, `ehcache` (Terracotta), `poi-server` | `ringcentral/jdk:8u202` (Alpine, JDK 8u202 z 2019 r.) | `eclipse-temurin:8-jdk-alpine` (`ARG BASE_IMAGE`) | bieżące poprawki bezpieczeństwa JDK 8; Alpine zostaje, więc polecenia `apk`/`addgroup` bez zmian; dodane `bash` (skrypty startowe mają `#!/bin/bash`), `curl`, `unzip`. JDK zamiast JRE, jak dotąd (poi-server z JasperReports może kompilować szablony). |
| `activemq` | ActiveMQ 5.16.5 | 5.16.7 | 5.16.5 ma krytyczną lukę CVE-2023-46604 (zdalne wykonanie kodu), poprawioną w 5.16.7 (ostatnie wydanie z Javą 8). |
| `postgres` | `postgres:14.12` | `postgres:14.24` | poprawki wydania pomocniczego. **PostgreSQL 14 kończy wsparcie 2026-11-12**; przejście na 16 lub 17 to zmiana wersji głównej (bazy w woluminach nie są zgodne, wymaga testów Mercury DB na nowej wersji): do decyzji. |
| `openldap` | OpenLDAP 2.6.3 kompilowany ze źródeł | 2.6.16 | zmiana zależności kompilacji na EL9: repozytorium CRB (`-devel`), `libxcrypt-devel` zamiast `libdb-devel`, bez `perl-devel` i `vim`. |

**Nie sprawdzone (brak Dockera na maszynie roboczej):** żadna z budów obrazów nie była uruchomiona. Największe ryzyko: `openldap` (kompilacja na EL9) i `mercury-lb` (konfiguracja nginx na EL9). Pierwsza budowa na `devops-box-01`.

**Pozostaje przestarzałe w obrazie serwera (do decyzji, powiązane z zadaniem 191):** Tomcat 8.5.82 (gałąź 8.5 bez wsparcia od 2024-03) i Oracle JDK 8u202 z 2019 r. (tarballe z repozytorium `raw`). Rekomendacja: Tomcat 9.0.x (ta sama specyfikacja Servlet 4, bez przepisywania aplikacji) i JDK Temurin 8 jako tarball; wymaga testu aplikacji, więc nie zmienione w tym release candidate.

## Pierwsza budowa i test dymny lokalnie (2026-11-04, Docker na maszynie roboczej)

Obrazy bazowe pobierane przez proxy Dockera w Nexusie (`nexus.scisoftware.local:5001`, `build-and-push-images.sh --bases-from`; pierwsze pobranie dużego obrazu bywa wolne, więc skrypt ponawia 3 razy). Wszystkie siedem obrazów zbudowało się; test dymny kompozycji jednowęzłowej (porty hosta przesunięte, osobny projekt) wykrył **problemy, których nie było widać bez uruchomienia**:

| Problem | Przyczyna | Poprawka |
|---|---|---|
| `setenv.sh` i `poi-server/bin/startServer.sh` w kontenerze: `$'\r': command not found`, `not found` | pliki miały CRLF w katalogu roboczym (checkout na Windowsie; w indeksie git są LF) | konwersja do LF, `.gitattributes`: `*.sh` i `*.docker-init` z `eol=lf` |
| `activemq`: `bin/linux-x86-64/wrapper: not found` | ActiveMQ używa natywnej binarki glibc, a Alpine ma musl | obrazy Javy na `eclipse-temurin:8-jdk-ubi9-minimal` (glibc) zamiast Alpine |
| `activemq`: `Unable to locate 'ps'` | brak `procps-ng` w UBI minimal | dodany pakiet |
| `poi-server`: `/opt/java/bin/java: No such file` | skrypt ma na sztywno `JAVA_HOME=/opt/java` (układ starego obrazu) | `JAVA_HOME=${JAVA_HOME:-/opt/java}` |
| ostrzeżenia `setlocale: pl_PL.UTF-8` | UBI minimal ma tylko angielskie ustawienia regionalne | dodany `glibc-langpack-pl` |
| `smoke-test.sh` uznał stos za sprawny mimo zatrzymanych kontenerów | `docker compose ps` bez `-a` nie pokazuje zatrzymanych | `docker compose ps -a` |

**Stan:** zmiany w Dockerfile'ach `activemq`, `ehcache`, `poi-server` i w `startServer.sh` są wprowadzone, ale trzy obrazy nie zostały po nich jeszcze przebudowane, a test dymny nie przeszedł do końca (drugi przebieg został zatrzymany przez system z powodu niskiej pamięci). Zbudowane i sprawdzone: `mercury-lb`, `postgres`, `openldap` (kompilacja OpenLDAP 2.6.16 na AlmaLinux 9 powiodła się). Obraz serwera po poprawce `setenv.sh` startował bez błędów `\r`, ale nie doczekał końca sprawdzania.

## Tomcat 9: konsultacja z `mercury-gui-core` (2026-11-04)

Kompilacja klas `mercury-gui-core` zależnych od Catalina przeciwko `tomcat-catalina` 9.0.123 wykazała dokładnie dwa miejsca niezgodności: `GenericPrincipal` w 8.5.82 ma konstruktor 6-argumentowy (z `GSSCredential`), a w 9.0.123 tylko 7-argumentowy; `RealmBase.getName()` w 9.0 nie istnieje. Konstruktor 6-argumentowy `TomcatMercuryPrincipal` nie jest nigdzie używany (realm woła tylko 3-argumentowy), a `@Override` przy `getName()` można usunąć. Zmiana (gałąź `hgdb-211` w `mercury`, niezacommitowana): usunięty konstruktor 6-argumentowy i `@Override`; klasy kompilują się przeciwko **8.5.82 (Maven) i 9.0.123 (`javac`)**, więc jeden jar działa w obu wersjach (środowisko dev autora może zostać na 8.5.x).
Konfiguracja obrazu względem oryginału 8.5.82 jest mało zmieniona (`catalina.properties`: dwa loadery i dwa dopisane wzorce `jarsToSkip`; `server.xml`: parametry Connectora i własny `Realm`; `web.xml` to w praktyce starszy oryginał bez własnej konfiguracji, więc w obrazie z Tomcatem 9 należy użyć oryginalnego). Pliki dla 9.0.123 są przygotowane (tymczasowo poza repozytorium); Tomcat 9.0.123 (suma SHA-1 zgodna) jest wgrany do repozytorium `raw` jako `apache-tomcat-9.0.123.tar.gz`. **Nie wprowadzone w obrazie**: najpierw ma przejść test dymny obecnej wersji, potem zmiana Tomcata i drugi test.
Uwaga: Tomcat 9.0.123 ma domyślnie `maxParameterCount="1000"` na Connectorze (starsze wydania 10000); do sprawdzenia przy żądaniach z wieloma parametrami.

## Wynik testu dymnego na pełnym stosie (2026-11-04, Docker lokalnie)

Pełny test dymny kompozycji jednowęzłowej (`smoke-test.sh --port-offset 10000`, izolowane dane `/d/mercury-smoke`, usunięte po teście) **przeszedł bez błędów**: wszystkie kontenery zdrowe, `/rest/openapi.json` publiczny (200), token OAuth dla `admin` z zakresem `mrc-user,mrc-sysadmin` wydany, usługa REST z tokenem 200 i bez tokenu 401, brak błędów krytycznych w logach i zasobów Terracotty. Stos: `almalinux:9` (mercury, mercury-lb), `eclipse-temurin:8-jdk-ubi9-minimal` (activemq, ehcache, poi-server), `postgres:14.24`, `scisoftware/openldap:ubuntu-24.04`, **Tomcat 9.0.123** (potwierdzone w obrazie), JDK 8u202.

### Zmiany po pierwszym teście

| Zmiana | Powód |
|---|---|
| zależności w kompozycjach (`condition: service_healthy`): `mercury` → `mercury-nodeN` → `poi-server-nodeN`, `openldap`, `ehcache-nodeN`; `poi-server` → `activemq` → `postgres-db`; healthchecki TCP/HTTP | start w kolejności gotowości; zależność od niezdrowego `openldap` ujawniła błąd obrazu |
| wzorzec `/rest/**` → `/rest/service/**` (XML, SQL) i zakres OAuth `mrc-user,mrc-useradmin,mrc-sysadmin` | obserwacja 88; zakres zgodny z konfiguracją dev (użytkownik `admin` ma rolę `mrc-sysadmin`) |
| `openldap`: obraz `scisoftware/openldap:ubuntu-24.04` (repozytorium `docker-openldap`) zamiast własnej kompilacji; ścieżki woluminów `/var/lib/ldap`, `/etc/ldap/slapd.d`; Helm `image.openldap` | własna kompilacja OpenLDAP na AlmaLinux 9 kolidowała z systemowymi bibliotekami (`libldap.so.2` → `libldap_r`), `slapd` nie startował; obraz Ubuntu jest utrzymywany i bez kompilacji |
| Tomcat 8.5.82 → 9.0.123 (`catalina.properties`, `server.xml.docker-init` przeniesione na oryginały 9.0.123; własny `web.xml` usunięty) | koniec wsparcia gałęzi 8.5; `mercury-gui-core` zgodny z oboma wersjami |
| `smoke-test.sh`: izolowana kopia kompozycji, własny `--data-root`, `--port-offset`, sprawdzenie funkcjonalne OAuth/REST, `ps -a` | kompozycje montują dane z `D:\mercury` (bind-mounty), których `down -v` nie czyści; stare dane maskowały zmiany i były modyfikowane przez test |

### Uwagi i ryzyka

- **Nie sprawdzone:** kompozycje dwu- i trzywęzłowa (zmienione tym samym skryptem, walidacja `docker compose config` OK, ale nie uruchamiane); wykres Helm (brak klastra); budowa i wysyłka obrazów do `docker-hosted` (tylko `--dry-run`); `maxParameterCount=1000` Tomcata 9 przy żądaniach z wieloma parametrami.
- **Skutek uboczny na maszynie roboczej:** test przy pierwszych przebiegach używał `D:\mercury\postgres-db` (stare dane z 2022 r.) i zmodyfikował ten katalog; dane są zbędne (decyzja autora). Tag lokalny `ibpm/openldap:mercury-hgdb-3.0` wskazuje obraz EL9 z poprawką bibliotek; skrypt `bin/openldap-dev-start.sh` (kontener deweloperski autora) nadal używa tego tagu i starych ścieżek, bez zmian.
- **Do zrobienia:** usunąć katalog `mercury-docker/openldap` (zastąpiony obrazem z `docker-openldap`) po decyzji autora; zaktualizować `bin/openldap-dev-start.sh`; przebudować i wgrać pakiet RC (przykłady `mercury-cmd` mają nowe wzorce i zakresy); wgrać obrazy do Nexusa.

### OpenLDAP: decyzja autora i zmiany (2026-11-04)

Zgoda autora: katalog `mercury-docker/openldap` (własna kompilacja na CentOS 8, potem AlmaLinux 9) usunięty, zostaje krótki `README.md` z odesłaniem do repozytorium `docker-openldap` i obrazu `scisoftware/openldap:ubuntu-24.04`. Skrypt `bin/openldap-dev-start.sh` przepięty: nie buduje obrazu, tylko go pobiera (opcjonalnie przez proxy Nexusa: `LDAP_IMAGE_SOURCE`), nowe woluminy `openldap_ldap` i `openldap_slapd-d` (ścieżki `/var/lib/ldap` i `/etc/ldap/slapd.d`; stare woluminy `openldap_database` i `openldap_config` zostały nietknięte). Autor usunął stary kontener deweloperski, nowy `openldap` utworzono tym skryptem (te same ustawienia domyślne: sufiks `dc=sample,dc=example,dc=com`, `cn=Manager`).
