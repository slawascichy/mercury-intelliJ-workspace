# [211] [mercury-docker] Aktualizacja obrazów Docker i wydanie nowej wersji

**Status (2026-10-27):** zwieńczenie planu, po 209 (decyzja autora 2026-10-27: 209 i 211 pozostają w planie); po nim autor stawia serwer testowy. Plan: `plan-najblizszych-dzialan-2026-10-26.md`.

Szkic zadania (2026-10-26). 
Zadanie **zamyka pakiet zmian** (zadania 119, 169, 190, 058, 191 i kolejne) wydaniem nowego release. Zakres i kolejność to propozycje do decyzji autora.
Elementy oznaczone „przypuszczenie” nie były sprawdzane.

## Cel

Przygotować nowe obrazy Docker, kompozycje i wykres Helm dla bieżącej wersji serwera Mercury DB i wydać release. Obrazy w `mercury-docker` są na wersji
`3.0.3.2.11` (`HGDB_VERSION 3.0.3.2.11.POSTGRESQL.20221006`), a serwer jest już na `3.0.4.x` (`mercury-lib` 3.0.4.16, `mercury/pom.xml` 3.0.4.8).
Artykuły o Docker i Kubernetes w `docusaurus-hgdb` czekają na nowe obrazy (obserwacja 22).

## Stan wyjściowy (zweryfikowany w plikach)

- `mercury-3.0/Dockerfile` (baza `centos:8` z `vault.centos.org`, JDK `1.8.0_202`, Tomcat `8.5.82`) pobiera z `https://hgdb.org/mercury-docker-packages/`
  Tomcat, JDK i **pakiet instalacyjny** `mercury-install-package-${HGDB_VERSION}.zip`. Pakiet buduje `mercury-cmd/mercury-install-package` z wydanych artefaktów serwera.
- Wersja `3.0.3.2.11` występuje w: `mercury-3.0/Dockerfile`, `mercury-3.0/README.md`, trzech `docker-compose.yml` i README kompozycji (`mercury-single-node`,
  `mercury-two-node-cluster`, `mercury-three-node-cluster`), `charts/mercury-single-node/Chart.yaml` i `values.yaml`, `README.md` głównym.
- `mercury-cmd` zależy od wydanych wersji `mercury.static.version=3.0.3.2.12` i `hgdb-client.version=3.1.2.0.2` (obserwacja 7), więc **pakiet nie zawiera dotychczasowych zmian serwera**,
  dopóki wersje nie zostaną podbite.
- Obrazy pomocnicze (`mercury-lb`, `postgresql`, `activemq`, `ehcache`, `openldap`, `poi-server`) mają tag `mercury-hgdb-3.0`. Czy wymagają zmian, nie sprawdzono (przypuszczenie: tylko jeśli zmieni się
  zawartość, np. skrypty bazy lub konfiguracja węzłów).

## Łańcuch wydania

| Krok | Repozytorium | Czynność |
|---|---|---|
| 1 | – | Decyzja o numerze wydania i zakresie (co wchodzi, czy 191 etap 2 jest gotowy) |
| 2 | `mercury-lib` | Wydanie (3.0.4.16 jest wydane po zadaniu 119; kolejne tylko jeśli zmiany w bibliotece) |
| 3 | `mercury`, `hgdb-client-open` | Wydanie serwera i klienta; podbicie zależności od `mercury-lib` |
| 4 | `mercury-cmd` | Podbicie `mercury.lib.version`, `mercury.srv.version` i `hgdb-client.version` (główny `pom.xml`); budowa `mercury-install-package` (ZIP; `mvn -o install -Dmaven.test.skip=true`) |
| 5 | publikacja | Wgranie ZIP-a na `hgdb.org/mercury-docker-packages` (czynność autora) |
| 6 | `mercury-docker` | Aktualizacja `HGDB_VERSION`, tagów, kompozycji, Helm, README, konfiguracji (patrz niżej) |
| 7 | `mercury-docker` | Budowa obrazów i test dymny kompozycji (jednowęzłowej, potem klastrów) |
| 8 | Docker Hub | Publikacja obrazów `ibpm/…` (czynność autora) |
| 9 | `docusaurus-hgdb`, workspace | Artykuły o Docker i Kubernetes; `docs/moduly/mercury-docker.md`, `docs/moduly/mercury-cmd.md` |

## Zakres zmian w `mercury-docker`

1. Wersje: `HGDB_VERSION`, tag `ibpm/mercury:mercury-hgdb-<wersja>`, kompozycje, README, `Chart.yaml`, `values.yaml` (`appVersion`).
2. **Wzorzec `/rest/**` (obserwacja 88).** W obrazie chroniony jest nadal cały `/rest/**`, więc `/rest/openapi.json` nie byłby publiczny. Zmienić na `/rest/service/**` w
   `mercury-security-config-db-1.0.0.xml`, `mercury-security-config-rgx-1.0.0.xml` (po dwa wpisy) i `postgresql/docker-entrypoint-initdb.d/02-init-ldap-tables.sql` (dwa wiersze).
3. **`lucene.properties`.** Dopisać zakomentowany blok parametrów z zadania 119 (wzór: `mercury/mercury-server/src/main/config/scichy/IBPM/mercury/config/lucene.properties`).
   To samo w pakiecie instalacyjnym `mercury-cmd` (obserwacja 90).
4. **Sekrety przykładowe (obserwacja 89).** Opisać w README, że `SECURITY_TOKEN`, hasła `secret` i sekret klientów OAuth są wartościami przykładowymi.
5. **Java i Tomcat.** Zależy od zadania 191. Jeśli etap 2 (Java 17) jest gotowy, zmienić JDK, Tomcat i bazę obrazu; jeśli nie, wydanie zostaje na Javie 8 (JDK 8u202, Tomcat 8.5.82),
   a baza `centos:8` (po końcu wsparcia) wymaga osobnej decyzji.
6. Przegląd obrazów pomocniczych pod kątem zmian (skrypty bazy dla nowych tabel, konfiguracja węzłów).

## Ryzyka z nierozwiązanych obserwacji (ocena 2026-10-26)

Nie widzę przeszkody blokującej wydanie, ale kilka punktów trzeba rozstrzygnąć lub sprawdzić **przed** publikacją obrazów:

| Obserwacja | Ryzyko | Postępowanie |
|---|---|---|
| 7 (`mercury-cmd` na starych wersjach) | Pakiet instalacyjny, z którego powstaje obraz, nie zawierałby zmian serwera | Krok 4 łańcucha jest warunkiem; sprawdzić zawartość ZIP-a przed budową obrazu |
| 43, 44 (biblioteki zewnętrzne, Jackson, dwa woodstoxy) | W opisie obserwacji: obrazów Docker i pakietu `mercury-cmd` nie sprawdzano | Test dymny obrazu (start serwera, logi, REST); sprawdzić `lib` pakietu |
| 88 (`/rest/**` w obrazach) | Dokumentacja OpenAPI chroniona tokenem | Zmiana z zakresu zadania i test `/rest/openapi.json` po starcie |
| 35 (konfiguracja z bazy) | W instalacjach z konfiguracją OAuth w tabeli starego wzorca zmiana pliku nie wystarczy | Dla obrazów naprawia wiersze w `02-init-ldap-tables.sql`; w istniejących instalacjach wymaga aktualizacji tabeli (opisać w notatkach wydania) |
| 32 (licencja) | Klucz próbny generowany przy pierwszym uruchomieniu musi pasować do `mercury.product.name` i trybu klastra; komunikat błędu ma zamienione etykiety | Test dymny jednowęzłowej i klastrowej kompozycji na nowej wersji (bez zmian w narzędziu generacji kluczy) |
| 87 (endpointy CMIS w WAR) | Endpointy Chemistry w `web.xml` bez ochrony części ścieżek | Decyzja przed wydaniem: zostają (z testem, że bez konfiguracji nie udostępniają plików) albo wyłączone |
| 29 (`deploy.sh` kończy `exit 0`) | Nieudane wgranie artefaktów może przejść niezauważone | Po wydaniu sprawdzić dostępność artefaktów w Nexusie |
| 10 (log4j 1.x) | Wspierane tylko log4j2; obraz ustawia `-Dlog4j.debug=true` | Przejrzeć `setenv.sh` obrazu pod kątem opcji diagnostycznych na produkcji (przypuszczenie) |

## Decyzje do podjęcia przez autora

1. Numer wydania (schemat wersji różni się: `mercury-lib` 3.0.4.16, `mercury` 3.0.4.8, `mercury-cmd` 3.0.8.6-SNAPSHOT) i data w nazwie ZIP-a.
2. Czy wydanie czeka na 191 etap 2 (Java 17), czy wychodzi na Javie 8 (rekomendacja: nie blokować wydania na etapie 2; wydać na Javie 8, a Javę 17 w kolejnym wydaniu, przypuszczenie).
3. CMIS: zostaje w WAR czy wyłączone do czasu zadania 49 (obserwacja 87).
4. Gdzie publikowany jest pakiet instalacyjny i kto go wgrywa (`hgdb.org/mercury-docker-packages`) oraz kto publikuje obrazy w Docker Hub (`ibpm/`).

## Kryteria akceptacji (propozycja)

- Obrazy budują się z pakietu o nowej wersji; `docker compose up` (jednowęzłowa) startuje bez błędów w logu poza znanymi.
- `/rest/openapi.json` i Swagger UI są dostępne bez tokenu, `/rest/service/**` wymaga tokenu.
- Zapytanie Lucene i parametry z `lucene.properties` działają na nowej wersji (przykład wymuszenia: `lucene.reader.pool=false`).
- Kompozycje dwu- i trzywęzłowa startują (licencja próbna, ActiveMQ, Ehcache).
- README, kompozycje i Helm wskazują nową wersję; `docs/moduly/mercury-docker.md` zaktualizowany.

## Decyzja autora (2026-11-04): podział na 211a i 211b, zmiana kolejności

211 to ostateczne wydanie systemu, więc przestaje być krokiem w środku kolejki. Nowa kolejność zadań: **191 → 209 → 226 → 211b**.

- **211a, procedura wydania (cykliczna, bez obowiązkowej publikacji).** Lista kroków i skrypty do wielokrotnego użycia: podbicie wersji w `mercury-cmd` i `mercury-docker` (dziś kilkanaście miejsc, obrazy stoją na `3.0.3.2.11` od 2022 r.), budowa `mercury-install-package` i automatyczna kontrola zawartości ZIP-a (wersje jarów, `ehcache*.xml` z regionami `CaseMapperShared` i `CaseObjectMapCacheShared`, `tc-config.xml`), skrypt testu dymnego kompozycji (start, logi, `/rest/openapi.json`, CMIS). Uruchamiana jako release candidate przy zamknięciu większych pakietów zadań; wgranie ZIP-a i publikacja obrazów to czynności autora.
- **211b, wydanie ostateczne.** Ta sama procedura po 191, 209 i 226, z publikacją na `hgdb.org` i Docker Hub oraz artykułami docusaurus (Docker, Kubernetes) i `docs/moduly/mercury-docker.md`, `mercury-cmd.md`.

Powody: dryf wersji wyjdzie wcześniej, nie naraz; 191 (Java 17) zmienia JDK, Tomcat i bazę obrazu (do sprawdzenia także kompatybilność Ehcache/Terracotty 3.6.1); 226 rozstrzyga regiony klastrowe i próg `minCostMs`.

### Wejście z zadania 118 (2026-11-04)

- Regiony klastrowe w `ehcacheDefault.xml`/`ehcacheCommon.xml` mają razem 388 MB (znaczniki czasu Hibernate 4, transakcje globalne 64, metadane typów 64, obiekty spraw 128, dokumenty Lucene 128). Serwer Terracotta w `mercury-docker/ehcache/conf/*` i w pakiecie `mercury-cmd` (`ehcache-clustered/server/conf/tc-config.xml`) ma `primary-server-resource` **512 MB**: mieści, ale z małym zapasem. Propozycja: 1024 MB jak w `docker/terracotta` (do akceptacji autora).
- Wzorzec `/rest/**` → `/rest/service/**` (obserwacja 88), blok `lucene.properties` (obserwacja 90), sekrety przykładowe (obserwacja 89): bez zmian względem szkicu powyżej.
- Wydane: `mercury-lib` 3.0.4.21, `mercury` 3.0.4.13, `sccommon` 2.0.0.4.

## Postęp 211a (2026-11-04, gałąź `hgdb-211` w `mercury-docker` i `mercury-cmd`, niezacommitowane)

Opis i stan skryptów: `procedura-wydania.md`. Zrobione: `mercury-docker/bin/release/` (`set-versions.sh`, `verify-cache-config.sh`, `build-and-push-images.sh`, `smoke-test.sh`), kompozycje czytają prefiks rejestru ze zmiennej `HGDB_REGISTRY` (domyślnie pusta, czyli bez zmiany zachowania). **Decyzja autora: obrazy przechowujemy w Nexusie `nexus.scisoftware.local`, repozytorium `docker-hosted`.** Rejestr: `nexus.scisoftware.local:5000` (port `docker-hosted` potwierdzony). Rozpoznanie: pakiet instalacyjny składa się z katalogu serwera dev i `target` w `mercury` (Ant `verify` już sprawdza wersje jarów, WAR i logowanie), więc 211a dodaje tylko kontrolę pamięci klastrowych, podbicie wersji, wysyłkę do Nexusa i test dymny.

Otwarte: `primary-server-resource` 512 → 1024 MB; rozjazd `ehcacheCommon.xml` w przykładach (4 regiony) z plikiem dev (6); numer wydania release candidate (`set-versions.sh` jeszcze nie zastosowany); test dymny i budowa obrazów do uruchomienia na `devops-box-01`.

### Release candidate 3.0.4.13 (2026-11-04)

Zastosowane na gałęziach `hgdb-211` (decyzje autora): `--srv 3.0.4.13 --lib 3.0.4.21 --client 3.1.4.19`; `primary-server-resource` 1024 MB. Pakiet `mercury-install-package-3.0.4.13.POSTGRESQL.20261104.zip` (136 MB) zbudowany z korzenia `mercury-cmd` po poprawce reguły weryfikacji Ant (zob. `procedura-wydania.md`). Do zrobienia przez autora: wgranie ZIP-a (krok 6), budowa obrazów (`build-and-push-images.sh`, rejestr `nexus.scisoftware.local:5000`) i test dymny na `devops-box-01`. Niezacommitowane zmiany: `mercury-docker` (wersje, kompozycje `HGDB_REGISTRY`, Terracotta 1024 MB, `bin/release/`), `mercury-cmd` (`pom.xml`, `build-installation.xml`, `README.md`, `tc-config.xml`, `README.txt` przykładu).

### Pakiety w Nexusie i obrazy bazowe (2026-11-04)

Decyzje autora: pakiety ładowane do repozytorium `raw` `mercury-docker-packages` w Nexusie (utworzone przez autora); `FROM` zmienione na nowsze i odporniejsze na podatności. Wykonane: do `mercury-docker-packages` wgrano pięć plików (pakiet RC 3.0.4.13, Tomcat 8.5.82, JDK 8u202, kit Terracotty 3.6.1, poi-toolkit 4.0.5-SNAPSHOT; odczyt anonimowy działa); Dockerfile'e pobierają z `ARG PACKAGES_URL` (domyślnie Nexus) z `curl -f`; `FROM`: `almalinux:9` (mercury, mercury-lb, openldap), `eclipse-temurin:8-jdk-alpine` (activemq, ehcache, poi-server), ActiveMQ 5.16.7 (CVE-2023-46604), `postgres:14.24`, OpenLDAP 2.6.16. Szczegóły i uzasadnienie w `procedura-wydania.md`, sekcja „Obrazy bazowe”. Nie zbudowane (brak Dockera); do sprawdzenia na `devops-box-01`. Do decyzji: PostgreSQL 14 (koniec wsparcia 2026-11-12), Tomcat 8.5.82 i JDK 8u202 w obrazie serwera.

## Uwagi autora do 211b (2026-11-04) i rozpoznanie

Test dymny pełnej kompozycji jednowęzłowej na Tomcacie 9 zaakceptowany przez autora („wygląda jakby działał”). Uwagi do wydania ostatecznego:

### 1. Zmiana nazwy produktu: `IBPM Mercury (HgDB)` → `Mercury 3.0 (HgDB)`

Rozpoznanie (tylko odczyt):
- Nazwa produktu w aplikacji pochodzi z parametru `mercury.product.name` (`AppConstants.PROP_PRODUCT_NAME`, `LicenseHelper.PROP_PRODUCT_NAME`); bez parametru używana jest stała `LicenseHelper.TRIAL_LICENSE_CN_DEFAULT` = „Mercury DB (HgDB) 3.0 - Trial”. W obrazie parametr jest ustawiony w `mercury-docker/mercury-3.0/docker-init-config/config/mercury.properties` (`mercury.product.name=IBPM Mercury (HgDB)`). Nazwa trafia do stopki stron serwera (`footer.jsp`: `AppConstants.PRODUCT_NAME`).
- W dokumentacji `mercury-docker` jest 11 plików z dokładnym ciągiem `IBPM Mercury (HgDB)` i ok. 120 wystąpień „IBPM Mercury …” (README obrazów i kompozycji, diagramy, „IBPM Mercury Enterprise”, „IBPM Mercury DB”). W `mercury` ciąg występuje w 1 pliku; docusaurus używa już „Mercury DB (HgDB) 3.0”.
- **Zależność z punktem 2:** `LicenseHelper.checkLicense` porównuje CN licencji z `mercury.product.name`, więc zmiana nazwy unieważnia istniejące pliki licencji wystawione na starą nazwę (CN = „IBPM Mercury (HgDB)”).

### 2. Weryfikacja mechanizmu licencji Trial

Rozpoznanie (kod w `hgdb-tools`: `org.hgdb.tools.license.LicenseHelper`, `LicenseType`; testy `LicenseHelperTest`, `LicenceMercurySrvTest`, `LicensePresentationTest`):
- Trial: do 3 węzłów, 30 dni (`TRIAL_LICENSE_EXPIRATION_INTERVAL`), CN = nazwa produktu, zakończenie po `expiration`.
- Gdy pliku licencji nie ma, serwer **sam generuje licencję TRIAL** (`checkLicenseFileExists` → `generateLicenseFile`), więc usunięcie pliku (albo nowy wolumen/kontener) zaczyna nowy okres próbny: do oceny, czy to zamierzone.
- Do sprawdzenia: koniec ważności (zachowanie po 30 dniach, komunikaty, blokada), limit 3 węzłów w klastrze, zgodność CN po zmianie nazwy, licencje płatne po zmianie nazwy (migracja/ponowne wystawienie), manipulacja zegarem i plikiem, zachowanie obrazu Docker (gdzie leży plik licencji, czy jest w wolumenie), testy jednostkowe, widok licencji na stronie (`LicensePresentationTest`).

### 3. Logo w stopce i favicon (aplikacja `mercury-ws-app`, nie docusaurus)

- Logo stopki: `mercury/mercury-ws-app/src/main/webapp/static/img/transparent_height_72.png` (127×72 px). Użycia: `pages/include/footer.jsp` oraz strony `static/admin/loggers.html`, `lucene-queries.html`, `secretaries.html` (`height: 72px`).
- Nowe logo: `D:\workspace\scisoftware\img\logo-SciSoftware-20241206\icononly-for-icon.png` (1000×1000 px, 72 KB): przy wyświetlaniu 72 px wysokości lepiej przeskalować (np. 144 px dla ekranów o wysokiej gęstości), żeby nie ładować 1000 px.
- Favicon: `static/img/favicon.ico`, `static/img/icons/favicon.ico` i `icons/favicon-16x16.png`, `favicon-32x32.png`, `favicon-96x96.png` (użycia: `pages/include/iconsLinks.jsp` i strony `static/admin/*.html`). Nowy: `D:\workspace\scisoftware\img\logo-SciSoftware-20241206\favicon.ico`; PNG 16/32/96 trzeba wygenerować z nowej ikony (brak ImageMagick; można użyć Java `ImageIO`).

### Pytania do autora przed realizacją
1. Dokładny zapis nazwy: `Mercury 3.0 (HgDB)`; czy zmienić też `TRIAL_LICENSE_CN_DEFAULT` („Mercury DB (HgDB) 3.0 - Trial”) i teksty „IBPM Mercury Enterprise / DB” w dokumentacji obrazów?
2. Co z istniejącymi licencjami (CN ze starą nazwą): akceptujemy nowe wystawienie, czy `LicenseHelper` ma tolerować starą nazwę?
3. Logo: podmienić zawartość pliku `transparent_height_72.png` (bez zmian w JSP), czy dodać plik o nowej nazwie i poprawić odwołania?

### Decyzje autora do 211b (2026-11-04) — realizacja w 211b, nie teraz

1. **Nazwa produktu = nazwa w licencji.** Nazwę produktu ustawiamy na tę, która jest w licencji: dla Trial `Mercury DB (HgDB) 3.0 - Trial` (czyli `LicenseHelper.TRIAL_LICENSE_CN_DEFAULT`), bo inaczej licencja nie przejdzie sprawdzenia CN. Wymagany **prosty mechanizm powiązania nazwy produktu z kompozycją i z licencją** (jedno źródło prawdy dla `mercury.product.name` w obrazie, kompozycjach, pakiecie i generatorze licencji; do zaprojektowania w 211b). Dotychczasowa wartość `IBPM Mercury (HgDB)` w `mercury-docker/.../mercury.properties` nie pasuje do licencji.
2. **Porządek z licencjami:** osobny moduł/usługa/narzędzie do generowania kluczy licencji (zamiast wspólnej logiki w `hgdb-tools`); zakres, forma (CLI, usługa) i migracja istniejących licencji do ustalenia w 211b.
3. **Logo i favicon:** podmienić zawartość pliku `transparent_height_72.png` (bez zmian w JSP), obraz przeskalować do 72 px wysokości (opcjonalnie 144 px dla ekranów o wysokiej gęstości); favicon podmienić na `favicon.ico` z `logo-SciSoftware-20241206` i wygenerować PNG 16/32/96 px.

Wszystko powyższe wchodzi do 211b (wydanie ostateczne), teraz nie realizujemy.

### Wydanie `mercury` 3.0.4.14 i dalsze kroki (ustalenia autora, 2026-11-04)

- Zmiana `mercury-gui-core` (zgodność realmu z Tomcatem 8.5 i 9.0, usunięty nieużywany konstruktor `TomcatMercuryPrincipal`) jest poważna wersyjnie, więc **autor wydaje `mercury` 3.0.4.14**. Potem Claude „odświeża” obrazy: `set-versions.sh --srv 3.0.4.14 …`, przebudowa pakietu (po wdrożeniu spójnego katalogu serwera dev), wgranie pakietu do Nexusa (`upload-packages.sh`), przebudowa obrazów, test dymny.
- Gdy będziemy gotowi: wypchnięcie obrazów do `docker-hosted` i próba uruchomienia **kompozycji 3-węzłowej na `devops-box-01`** (decyzja autora: najpierw autor sprawdza całość „klikając”).
- **Do 211b dopisane:** przygotować na `devops-box-01` **Kubernetes** i zweryfikować kompozycję także na tym rozwiązaniu (wykres Helm `charts/mercury-single-node`: nieprzetestowany; zmieniony `image.openldap`, ścieżki woluminów `/var/lib/ldap` i `/etc/ldap/slapd.d`). Dopiero gdy wszystko będzie gotowe do wydania ostatecznego.
