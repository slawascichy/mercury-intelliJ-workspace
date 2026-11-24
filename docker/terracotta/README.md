# Terracotta dla Mercury DB (Ehcache clustered 3.10.8)

Kompozycja Docker z serwerem Terracotta, na którym leżą współdzielone w klastrze pamięci podręczne Mercury DB
(zadania 118 i 256). Wersja serwera odpowiada klientowi `ehcache-clustered` 3.10.8 (wersje klienta i serwera muszą się zgadzać).
Serwer działa na Javie 17 (kit 3.10.x działa też na Javie 8). Nazwy zgadzają się z konfiguracją Mercury: serwer `default-server`,
port `9510`, zasób `primary-server-resource` (adres w XML: `terracotta://<host>:9510/default-server`).

Kompozycja służy do pracy lokalnej (dev) i zastępuje kit `mercury/mercury-server/ehcache-clustered-3.6.1-kit`. Obrazy klastra
Kubernetes (`ibpm/ehcache`, trzy węzły HA) buduje się osobno w `mercury-docker/ehcache`.

## Uruchomienie

```bash
cd docker/terracotta
./startEhcacheServer.sh            # start: buduje obraz (pierwszy raz pobiera kit z Maven Central), czeka na stan ACTIVE
./startEhcacheServer.sh status     # stan kontenera i serwera
./startEhcacheServer.sh logs       # log serwera (Ctrl+C kończy)
./startEhcacheServer.sh stop       # zatrzymanie i usunięcie kontenera
./startEhcacheServer.sh restart
./startEhcacheServer.sh reset      # jak stop, dodatkowo usuwa wolumin logów
./startEhcacheServer.sh bench      # mikrotest opóźnienia (serwer musi działać)
```

Skrypt sprawdza, czy port jest wolny. Przed pierwszym użyciem zatrzymaj stary lokalny serwer Terracotta (ten sam port 9510).
Bez skryptu: `docker compose up -d --build`.

Dane (pamięci podręczne) są w pamięci off-heap serwera i nie przeżywają usunięcia kontenera, co jest zamierzone (to pamięci
podręczne). Zwykłe `docker compose stop/start` zachowuje konfigurację, a serwer startuje z zapisanego repozytorium.

Zmienne (opcjonalne): `TC_PORT` (9510), `TC_GROUP_PORT` (9530), `TC_JAVA_OPTS`, `TC_PUBLIC_HOSTNAME` (localhost),
`TC_WAIT_SECONDS` (120), a w kontenerze także `TC_OFFHEAP_RESOURCES`, `TC_CLIENT_RECONNECT_WINDOW`, `TC_CLIENT_LEASE_DURATION`.

## Konfiguracja serwera

Kit 3.10.x nie używa `tc-config.xml`. Konfiguracja jest dynamiczna (`config-tool`), a pojedynczy serwer startuje z opcją
`-auto-activate` (parametry w `entrypoint.sh`): klaster `mercury-dev`, serwer `default-server`, zasoby off-heap
`primary-server-resource` 1024 MB i `secondary-server-resource` 96 MB, okno ponownego połączenia klientów 120 s, dzierżawa 150 s.
Serwer przedstawia się klientom jako `localhost:9510` (`-public-hostname`, `-public-port`), dlatego klienci z hosta łączą się
przez opublikowany port. Klienci z innych kontenerów muszą ustawić `TC_PUBLIC_HOSTNAME` na nazwę usługi.

Serwer jest gotowy dopiero w stanie ACTIVE. Port 9510 nasłuchuje już w stanie DIAGNOSTIC, przed aktywacją, więc kontrola
gotowości (healthcheck) pyta `config-tool diagnostic`.

## Mikrotest opóźnienia (zmierzyć PRZED przełączeniem Mercury na inny serwer)

Opóźnienie decyduje o opłacalności pamięci klastrowych (zapis w regionie znaczników czasu Hibernate wykonuje kilkanaście
operacji na zapis sprawy).

```bash
./startEhcacheServer.sh bench       # z tego hosta, w sieci kontenera serwera

# z innej maszyny (np. węzeł aplikacji): zbuduj ten sam obraz i wskaż adres serwera
docker compose build terracotta
docker run --rm -e TC_URL=terracotta://ADRES_SERWERA:9510/default-server mercury/terracotta:3.10.8 bench
```

Wynik to czasy zapisu i odczytu od innego klienta dla wpisów 2, 5, 16 i 56 KB. Dla porównania: klient na Windows
(localhost, serwer dev) daje ok. **13-15 ms** na operację, klient na Linuksie 0,3-0,9 ms. Zapis sprawy Mercury (`createFolder`)
dawał na Windows ok. 190 ms wobec 90 ms przy pamięciach lokalnych (pomiary z wersji 3.6.1).

## Parametry

| Element | Wartość |
|---|---|
| Porty | `9510` (klienci), `9530` (komunikacja serwerów, przy HA) |
| Zasoby off-heap | `primary-server-resource` 1024 MB, `secondary-server-resource` 96 MB |
| Pamięć JVM serwera | `JAVA_OPTS` (zmienna `TC_JAVA_OPTS`), domyślnie `-Xms256m -Xmx512m -XX:MaxDirectMemorySize=2g` |
| Logi | wolumin `terracotta-logs` (`/data/logs`) |

Suma rozmiarów `clustered-dedicated` wszystkich pamięci w `ehcacheDefault.xml` i `ehcacheCommon.xml` musi mieścić się
w `primary-server-resource` (obecnie 388 MB: znaczniki czasu Hibernate 4, transakcje globalne 64, metadane typów 64,
obiekty spraw 128, dokumenty Lucene 128). `MaxDirectMemorySize` powinno być większe niż suma zasobów off-heap,
a pamięć maszyny wirtualnej większa od `MaxDirectMemorySize` plus sterta.

**Zasada zgodności:** ten sam alias pamięci musi mieć identyczny rozmiar `clustered-dedicated` we wszystkich
konfiguracjach klientów. Niezgodny rozmiar kończy się błędem `InvalidServerStoreConfigurationException` przy starcie
klienta; usunięcie pamięci z serwera (`destroyCache`) albo restart serwera naprawia sytuację.

## Licencja

Kit Terracotta 3.10.x podlega własnej licencji (TPL, zadanie 256). Zanim kit trafi do dystrybucji poza środowiskiem
deweloperskim, autor przegląda warunki licencji (opis w `tasks/hgdb/256-.../TASK.md`).

Pełne teksty licencji są w katalogu `legal/` kitu (w obrazie: `/opt/terracotta/legal`, bez zmian). Kit jest niezmodyfikowany. Kod źródłowy
komponentów Terracotta (TPL 2.0, sekcja 3.2) jest dostępny w https://github.com/Terracotta-OSS/terracotta-core (serwer, Terracotta 5.9.5
dla kitu 3.10.8) i https://github.com/ehcache/ehcache3 (Ehcache), w znacznikach odpowiadających wersji kitu.

## Wdrożenie na Proxmoksie

Serwer Terracotta jest wrażliwy na opóźnienie sieci do węzłów aplikacji, więc maszynę (lub kontener LXC) należy
postawić w tej samej sieci L2 i, jeśli to możliwe, na tym samym hoście Proxmox co węzły Mercury. Szczegóły w
rozmowie z autorem zadania 118 (rekomendacja: mała maszyna wirtualna z Linuksem i Dockerem, 2 vCPU, 4 GB RAM, dysk
nie jest krytyczny).
