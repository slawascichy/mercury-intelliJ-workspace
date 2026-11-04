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
