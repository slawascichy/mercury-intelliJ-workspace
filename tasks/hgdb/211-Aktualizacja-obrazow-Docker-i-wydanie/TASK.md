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
