# [256] Upgrade Terracota do wersji obsługiwanej przez Java 17

https://github.com/slawascichy/hgdb/issues/256

Serwer Terracotta (klaster Ehcache) jest jedynym komponentem Mercury DB, który po zadaniu 191 (migracja na Javę 17) zostaje na Javie 8.
Kit `ehcache-clustered-3.6.1-kit` (serwer Terracotta z 2018 r.) działa w obrazie `mercury-docker/ehcache` na Temurin 8. Chcemy kit,
który wspiera Javę 17, żeby cała kompozycja (serwer Mercury, POI, ActiveMQ, Terracotta) działała na jednym JDK.

## Kontekst (stan na 2026-11-24)

- Klient Ehcache w Mercury: `org.ehcache:ehcache` 3.6.1 (`ehcache.version` w `mercury`, `mercury-cmd`, `poi-toolkit`), `ehcache-clustered` 3.6.1.
  Klient i serwer klastra muszą mieć zgodne wersje, więc nowy kit wymusza nowego klienta.
- Biblioteka autora `sccommon-cache` 2.0.0.4 (`EhCacheProvider`) jest budowana pod Ehcache 3.6.1.
- Konfiguracja klienta: schematy `ehcache-core-3.5.xsd`, `ehcache-clustered-ext-3.5.xsd`, `ehcache-107-ext-3.5.xsd`, `ehcache-tx-ext-3.5.xsd`
  (w `mercury-server/IBPM/mercury/config` i pakiecie instalacyjnym); konfiguracja serwera: `tc-config` w obrazie `ehcache`
  (pliki `node1-config.xml` … `node3-config.xml` w kicie 3.6.1).
- Obraz `mercury-docker/ehcache` (Dockerfile na Temurin 8, JVM serwera z `-d64 -XX:MaxDirectMemorySize=1048576g`, `-Xmx2049m`).
- Lokalne środowisko deweloperskie: autor uruchamia Terracottę sam (port 9510).
- Powiązane: zadanie 191 (migracja na Javę 17; ActiveMQ przeniesiony w jego ramach), obserwacja 210 (CXF 3.5.x oczekuje Ehcache >= 3.8,
  dziś obejście `MemoryTokenStore` w `webService.xml`; po upgrade'ie można je usunąć).

## Co wiadomo (z wyszukiwania w sieci, do weryfikacji, nie z testów)

- Zestaw Terracotta z linii Ehcache 3.10 (Terracotta 10.15) deklaruje wymaganie Javy 17 lub nowszej; Ehcache 3.11 jest ostatnią linią, która wspiera Javę 8.
- Terracotta DB 10.x wygląda na produkt Software AG; **nie wiadomo, czy kit jest dostępny na naszej licencji** (patrz „Do rozstrzygnięcia przez autora”).

> **Uwaga: licencja Terracotta (do przeglądu przez autora).**
> Kit serwera, który wspiera Javę 17, pochodzi z linii Terracotta 10.x (Ehcache 3.10 to Terracotta 10.15). Dokumentacja i wydania tej linii są
> publikowane przez Software AG (`documentation.softwareag.com/terracotta`, `confluence.terracotta.org`, `terracotta.org/downloads`), co sugeruje
> produkt komercyjny (Terracotta DB), a nie otwarty kit, który mamy dziś (`ehcache-clustered-3.6.1-kit`, linia open source z 2018 r.).
> To jest **przypuszczenie z wyników wyszukiwania**, nie sprawdzone w tekście licencji ani na stronie pobierania.
> Do sprawdzenia przed jakąkolwiek pracą nad zadaniem:
> 1. Na jakiej licencji jest kit serwera w wersji wspierającej Javę 17 (open source, wersja społecznościowa, czy płatna licencja Software AG)?
> 2. Czy wolno nam dołączyć kit do obrazu Docker `ibpm/ehcache` i trzymać go w repozytorium raw Nexusa (`mercury-docker-packages`) oraz dystrybuować
>    razem z Mercury DB (wersja komercyjna jest dystrybuowana przez IBPM S.A.; wersja open source hgdb.org)?
> 3. Czy licencja nakłada ograniczenia na liczbę węzłów, rozmiar pamięci offheap albo wymaga klucza licencyjnego serwera?
> 4. Jeśli licencja jest przeszkodą: opcje to pozostanie na kicie 3.6.1 na Javie 8 (jedyny komponent na starym JDK, z odrębną polityką aktualizacji
>    bezpieczeństwa), albo ocena innej klasy rozwiązania (np. cache w pamięci węzła bez Terracotty tam, gdzie klaster nie jest konieczny).
> **Decyzja autora (2026-11-24): zielone światło.** Zadanie 256 jest podzadaniem 191 i realizujemy je w jednym wydaniu z resztą (kit 3.10.8, Java 17 po stronie serwera). Ocena licencji TPL pozostaje po stronie autora.

> **Opcja: własna budowa serwera z źródeł (pomysł autora, 2026-11-24).**
> Repozytorium `Terracotta-OSS/terracotta-core` (https://github.com/Terracotta-OSS/terracotta-core) zawiera rdzeń serwera Terracotta. Jeśli kit
> dla Javy 17 jest dostępny tylko na licencji komercyjnej, można spróbować zbudować serwer samemu.
> Co wiadomo z wyszukiwania (nie z testów): oficjalna dokumentacja (https://docs.terracotta.org/about/license.html) opisuje otwarty Terracotta Server
> jako objęty licencją Terracotta Public License 2.0 (oparta na MPL), starsza strona mówi o Apache 2.0, więc **treść licencji w repozytorium
> trzeba sprawdzić samodzielnie**; strona pobierania (https://www.terracotta.org/downloads/) wspomina o wersji community z Terracotta Server 5.x
> (otwarta) i Ehcache 3.x (otwarta). Do zbadania w spike'u: wersja `terracotta-core` zgodna z docelowym klientem Ehcache, wymagana wersja Javy,
> czy budowa z źródeł daje działający serwer w obrazie `ibpm/ehcache` oraz koszt utrzymania (własne poprawki bezpieczeństwa i aktualizacje).
> Spike wykonujemy lokalnie w Dockerze, bez przebudowy klastra.

## Do rozstrzygnięcia przez autora

1. Licencja: czy kit serwera Terracotta w wersji wspierającej Javę 17 można stosować i dystrybuować w obrazie Mercury DB (wersja open source czy komercyjna Software AG).
2. Docelowa wersja (Ehcache 3.10.x z odpowiadającym kitem?) i skąd pobieramy kit (repozytorium raw Nexusa `mercury-docker-packages`, jak dziś).

## Wyniki spike'u (2026-11-24, lokalny Docker, bez ruszania klastra)

Sprawdzone na kitach `ehcache-clustered-<wersja>-kit.zip`, które są publicznie dostępne na Maven Central
(`https://repo1.maven.org/maven2/org/ehcache/ehcache-clustered/<wersja>/`; dostępne m.in. 3.8.2, 3.9.9, 3.10.0 do 3.10.9, 3.11.0, 3.11.1, 3.12.0).
Własna budowa z `Terracotta-OSS/terracotta-core` **nie jest potrzebna**: gotowe kity są otwarte i można je pobierać z Maven Central
(repozytorium `terracotta-core` ma w `LICENSE` Apache 2.0, ale to osobna sprawa niż licencje w kitach, patrz niżej).

| Kit | Terracotta Core | Java serwera | Aktywacja bez licencji |
|---|---|---|---|
| 3.10.8 | 5.9.5 (2022) | **8 i 17** (oba przetestowane: stan `ACTIVE-COORDINATOR`) | tak (`config-tool activate`, „No license specified”) |
| 3.12.0 | 5.12.22 (2026) | **tylko 17** (na Javie 8: `UnsupportedClassVersionError`, klasy w wersji 61) | tak (stan `ACTIVE-COORDINATOR`; przy restarcie ostrzeżenia `guardian failed`) |

Wnioski:
- Terracotta w wersji z Javą 17 istnieje w wydaniu otwartym, więc zadanie jest wykonalne bez licencji komercyjnej (do potwierdzenia przez autora, patrz niżej).
- **Kit 3.10.8 jest „mostem”**: serwer działa na Javie 8 i 17, a klient Ehcache 3.10.x ma bajtkod Javy 8, więc migrację można rozłożyć na etapy (najpierw serwer i klient, bez wymuszania Javy 17 w innych komponentach). Klient 3.10.x spełnia też oczekiwanie CXF 3.5.x (Ehcache >= 3.8), więc obejście `MemoryTokenStore` (obserwacja 210) przestaje być konieczne.
- Kit 3.12.0 wymaga Javy 17 także po stronie serwera; nowszy rdzeń (5.12.22) i aktualne zależności (logback 1.5, slf4j 2.0). Klient 3.12.x prawdopodobnie też wymaga Javy 17 (nie sprawdzono). **Ryzyko:** `mercury-client` (IBM BPM, Java 8, zamrożony) i `SecurityProvider` dzielą z Mercury stos `sccommon`/Ehcache; trzeba sprawdzić, czy klienci BPM łączą się z tym samym klastrem Terracotta i czy klient Ehcache 3.6.1 działa z serwerem 3.10.8 (zgodność klient–serwer nie została sprawdzona).
- **Zmiana modelu konfiguracji:** zamiast `tc-config.xml` (`node1-config.xml` … w kicie 3.6.1) jest dynamiczna konfiguracja: plik `cluster.cfg` (np. `offheap-resources=main:512MB`, `failover-priority=availability`, porty 9410 i 9430) oraz **osobny krok aktywacji** klastra narzędziem `tools/bin/config-tool.sh activate -connect-to <host>:9410 -cluster-name <nazwa>` (serwer bez aktywacji stoi w stanie `DIAGNOSTIC`). Skrypt `start-tc-server.sh` przyjmuje `-f conf/cluster.cfg`. Obraz `ibpm/ehcache` musi więc startować serwer i wykonywać aktywację (w kicie jest katalog `docker/` z wzorcowymi Dockerfile serwera, config-toola i votera).
- Stan serwera po aktywacji pamięta konfigurację w katalogu danych, więc przy zmianie wersji trzeba uwzględnić migrację danych (cache regionów da się odtworzyć, ale to do sprawdzenia).

### Zgodność klient–serwer Ehcache (test lokalny, 2026-11-24)

Test: serwer Terracotta z kitu i klient Ehcache (XML z `tc:cluster`, `put` i `get` na pamięci `clustered-dedicated`) w jednym kontenerze Temurin 8.

| Serwer | Klient | Wynik |
|---|---|---|
| 3.6.1 | 3.6.1 | działa (`get` zwraca wartość) |
| 3.10.8 | 3.10.8 | działa |
| 3.6.1 | 3.10.8 | **błąd**: `ConnectionClosedException` przy encji `org.terracotta.lease.LeaseAcquirer` |
| 3.10.8 | 3.6.1 | **błąd** po stronie serwera (`ThrowableHandlerImpl.handleDefaultException`) |

Wniosek: klient i serwer muszą mieć tę samą wersję, więc **klienta Ehcache nie da się podnieść osobno przed serwerem**. Upgrade klienta
(`mercury`, `poi-toolkit`, `mercury-cmd`, `sccommon-cache`) i serwera Terracotta robimy w jednym wydaniu (to zadanie 256).
Dotyczy to też klientów, którzy łączą się z tym samym klastrem (IBM BPM, `mercury-client`, zamrożony, Ehcache 3.6.1): po upgrade'ie serwera
nie połączą się z nim, jeśli korzystają z klastra Terracotta (do sprawdzenia, czy korzystają).

### `sccommon-cache` a Ehcache 3.10.8

Biblioteka autora (`sccommon/sccommon-cache`, w workspace) używa m.in. klas z pakietów `org.ehcache.core` (`EhcacheManager`, `Ehcache`,
`spi.service.StatisticsService`), `org.ehcache.impl.internal.statistics.DefaultStatisticsService` i `org.ehcache.xml.model.ResourceUnit`.
Kompilacja 30 plików źródłowych względem jarów Ehcache 3.10.8 (`javac --release 8`, klasy z lokalnego `lib` + klient z kitu) **przechodzi bez błędów**,
czyli biblioteka jest zgodna źródłowo. Zgodność w czasie działania (zachowanie `EhCacheProvider`, statystyki, odczyt regionów z XML) nie była testowana;
trzeba ją sprawdzić testami biblioteki i testem `mercury` z lokalną Terracottą 3.10.8. Wymaga to nowego wydania `sccommon-cache` zbudowanego pod 3.10.8
(`ehcache.version` w `sccommon-cache/pom.xml`, dziś 3.6.1; wydanie 2.0.0.4 jest zbudowane pod 3.6.1).

### Licencje w kitach (do przeglądu przez autora)

- Kit 3.10.8: katalog `legal/` zawiera `APACHE_PUBLIC_LICENSE.txt`, `TERRACOTTA-PUBLIC-LICENSE.txt` (Terracotta Public License 2.0, oparta na MPL), `THIRD-PARTY-LICENSES.txt`, `Legal_Notice.txt` (Software AG, prawa autorskie 2011–2020).
- Kit 3.12.0: `legal/LICENSE` (5 linii): „Ehcache is licensed under the Apache License 2.0. Ehcache clustering-related components and Terracotta Server include components that are licensed under the Terracotta Public License.”
- Czyli klient Ehcache jest na Apache 2.0, a komponenty klastrowe i serwer Terracotta na Terracotta Public License 2.0. Czy TPL 2.0 pozwala na dystrybucję w naszym obrazie Docker (z kodem źródłowym, MPL-podobne obowiązki) i w wydaniu komercyjnym IBPM, powinien ocenić autor (nie sprawdzano tekstu TPL pod kątem naszego użycia).

### Zalecana ścieżka

1. Etap A (po zgodzie licencyjnej): kit **3.10.8** na Temurin 17 (serwer) + klient Ehcache 3.10.8 w `mercury`, `poi-toolkit`, `mercury-cmd` oraz test `sccommon-cache` (biblioteka autora budowana pod 3.6.1).
2. Etap B (opcjonalnie): kit 3.12.0 i klient 3.12.0, gdy wszystkie komponenty klientowe pracują na Javie 17.
Tag obrazu: `ibpm/ehcache:mercury-hgdb-3.0-<wersja_kitu>` (decyzja autora 2026-11-24, zrealizowana w skrypcie budowy, chartach i kompozycjach; dziś `-3.6.1`).

## Plan (propozycja)

1. **Rozpoznanie:** licencja, dostępność kitu, wymagana wersja Javy serwera i klienta, zgodność klient–serwer, format `tc-config`, schematy XSD klienta.
2. **Spike na osobnym klastrze testowym:** serwer Terracotta na Temurin 17 (obraz `ehcache`), klient Ehcache nowej wersji, test regionów klastrowych
   (ile pamięci offheap, odtwarzanie po restarcie, tryb `failover`), z danymi `Bench211`.
3. **`sccommon-cache` i konfiguracja:** zbudować i przetestować bibliotekę autora pod nową wersją Ehcache, zaktualizować schematy XSD i opisy regionów w `ehcacheDefault.xml`/`ehcacheCommon.xml`.
4. **`mercury`, `mercury-cmd`, `poi-toolkit`:** podbić `ehcache.version`, test jednostkowy z lokalną Terracottą, pełne testy.
5. **`mercury-docker`:** obraz `ehcache` na Temurin 17 z nowym kitem (`upload-packages.sh`, `set-versions.sh`), chart i kompozycje, test klastra trzywęzłowego.
6. **Sprzątanie:** usunąć obejście `MemoryTokenStore` (obserwacja 210), jeśli CXF działa z nowym Ehcache; dokumentacja (wymaganie JDK 17 serwera Terracotta, instalacja, Kubernetes), aktualizacja `docs/architektura.md` i opisów modułów.



## Postęp (2026-11-24)

Decyzje autora: podzadanie 191, kit **3.10.8** (Terracotta 5.9.5; serwer na Temurin 17), tag obrazu `ibpm/ehcache:mercury-hgdb-3.0-3.10.8`; 3.12.0 odkładamy (lista marzeń).

Zrobione (`mercury-docker`, niezacommitowane):
- **Obraz `ehcache`:** Temurin 17, kit 3.10.8 z Maven Central (plik w `ehcache/install`, wysłany do Nexusa `mercury-docker-packages`), nowy skrypt `bin/startServer-3.10.8.sh`; usunięte stare `conf/{1,2,3}/node*-config.xml` i `startServer-3.6.1.sh`. Obraz wysłany: `ibpm/ehcache:mercury-hgdb-3.0-3.10.8`.
- **Skrypt startowy** obsługuje cztery sytuacje (opis w `ehcache/README.md`): (0) restart kontenera z zachowanym repozytorium konfiguracji, (1) jeden węzeł (`-auto-activate`), (2) pierwszy start całego klastra (wspólny `cluster.cfg`, `node1` aktywuje klaster po starcie pozostałych), (3) nowy kontener, gdy klaster już działa (`detach` wyłączonego węzła, start jako nowy serwer, `attach` do aktywnego). Pamięć offheap i dzierżawy jak dotąd (`primary-server-resource` 1024 MB, `secondary-server-resource` 96 MB, lease 20 s, reconnect 120 s, `availability`).
- **Testy lokalne w Dockerze** (trzy kontenery `ehcache-node1..3` na jednej sieci, obraz z Nexusa): czysty start (aktywny jeden, dwa pasywne), świeży restart pasywnego węzła, awaria aktywnego (przejęcie przez inny i powrót świeżego), `docker restart` z zachowanym systemem plików (wymagało poprawki: bez ścieżki 0 węzeł startował jako osobny klaster po `detach`); w każdym przypadku diagnostyka: „cluster configuration is healthy”, 3 węzły aktywne. Klient Ehcache 3.10.8 z listą trzech serwerów (`terracotta://ehcache-node1:9410,ehcache-node2:9410,ehcache-node3:9410/...`, zasób `primary-server-resource`): `put` i `get` działają.
- **Charty i kompozycje:** `ehcacheTag: mercury-hgdb-3.0-3.10.8` (osobny od `mainTag`), strategia `Recreate` dla Deploymentów `ehcache`, tag w plikach `docker-compose.yml` i README.
- **POM-y:** `ehcache.version` 3.10.8 w `mercury`, `mercury-lib`, `mercury-cmd`, `poi-toolkit`, `hgdb-client-open` (w `sccommon-cache` już ustawione przez autora).

Do zrobienia:
1. Pobranie zależności Ehcache 3.10.8 (`ehcache`, `ehcache-clustered` i przechodnie, m.in. `org.terracotta`) do lokalnego repozytorium (autor), razem z ActiveMQ 5.19.12.
2. Wydanie `sccommon-cache` zbudowanego pod 3.10.8 i podbicie `sccommon.version` w `mercury` i `poi-toolkit`; kompilacja i testy; sprawdzenie plików konfiguracji `ehcacheDefault.xml`/`ehcacheCommon.xml` (schematy 3.5) z klientem 3.10.8; wymiana jarów Ehcache w lokalnym `apache-tomcat/mercury/lib` i w pakiecie.
3. Wdrożenie na `mercury-cluster` (serwery i klienci jednocześnie, bo wersje muszą się zgadzać), test SOAP z WS-Security, eksport i import Excela, `live4.sh`.
4. Usunięcie obejścia `MemoryTokenStore` w `webService.xml` (obserwacja 210), jeśli CXF działa z Ehcache 3.10.8; dokumentacja (wymaganie JDK 17 serwera Terracotta, artykuły docusaurus, `docs/architektura.md`).
5. Lokalny Terracotta autora: zmiana na kit 3.10.8 (`cluster.cfg` plus `config-tool activate`); klienci BPM (`bpm-security-provider` ma Ehcache 3.6.1 w jednym z profili) do sprawdzenia.
## Kryteria ukończenia

- Serwer Terracotta działa na Javie 17 w obrazie Docker i w lokalnym środowisku deweloperskim.
- Klient Ehcache i `sccommon-cache` zgodne z kitem; testy `mercury`, `poi-toolkit`, `mercury-cmd` zielone.
- Klaster trzywęzłowy: sesje, cache regionów i test obciążeniowy bez regresji względem 3.6.1.
- Dokumentacja i obserwacje zaktualizowane.
