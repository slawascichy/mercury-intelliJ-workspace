# Terracotta dla Mercury DB (Ehcache clustered 3.6.1)

Kompozycja Docker z serwerem Terracotta, na którym leżą współdzielone w klastrze pamięci podręczne Mercury DB
(zadanie 118). Wersja serwera odpowiada klientowi `ehcache-clustered` 3.6.1. Nazwy zgadzają się z konfiguracją
Mercury: serwer `default-server`, port `9510`, zasób `primary-server-resource` (adres w XML:
`terracotta://<host>:9510/default-server`).

**Stan:** obraz zbudowany i uruchomiony na `devops-box-01.hgdb.org` (autor, 2026-11-03). Plik `Dockerfile` i `tc-config.xml` oparto na kicie 3.6.1 używanym w środowisku dev.

## Uruchomienie

```bash
cd docker/terracotta
docker compose up -d --build        # budowa pobiera kit z Maven Central (wymaga Internetu przy budowie)
docker compose ps                   # stan healthy po ok. 20-40 s
docker compose logs -f terracotta   # w logu: "Terracotta Server instance has started up as ACTIVE node"
```

Zatrzymanie: `docker compose down`. Dane (pamięci podręczne) są w pamięci off-heap serwera i nie przeżywają restartu,
co jest zamierzone (to pamięci podręczne). Zmiana portów: zmienne `TC_PORT` i `TC_GROUP_PORT`.

## Mikrotest opóźnienia (zmierzyć PRZED przełączeniem Mercury na ten serwer)

Zmierz opóźnienie z maszyny, na której działa serwer aplikacji Mercury, bo ono decyduje o opłacalności pamięci
klastrowych (zapis w regionie znaczników czasu Hibernate wykonuje kilkanaście operacji na zapis sprawy).

```bash
# z tego samego hosta co serwer Terracotta (kontener do kontenera):
docker compose --profile bench run --rm bench

# z innej maszyny (np. węzeł aplikacji): zbuduj ten sam obraz i wskaż adres serwera
docker compose build terracotta
docker run --rm -e TC_URL=terracotta://ADRES_SERWERA:9510/default-server mercury/terracotta:3.6.1 bench
```

Wynik to czasy zapisu i odczytu od innego klienta dla wpisów 2, 5, 16 i 56 KB. Dla porównania: na serwerze dev (Windows,
localhost) zapis i odczyt trwały ok. **13-15 ms** niezależnie od rozmiaru; po stronie zapisów sprawy Mercury (`createFolder`)
dawało to ok. 190 ms wobec 90 ms przy pamięciach lokalnych. Opóźnienie rzędu 1-2 ms na Linuksie oznaczałoby narzut
kilkunastu milisekund na zapis.

## Parametry

| Element | Wartość |
|---|---|
| Porty | `9510` (klienci, TSA), `9530` (komunikacja serwerów, przy HA) |
| Zasoby off-heap | `primary-server-resource` 1024 MB, `secondary-server-resource` 96 MB (`tc-config.xml`) |
| Pamięć JVM serwera | `JAVA_OPTS` (zmienna `TC_JAVA_OPTS`), domyślnie `-Xms256m -Xmx512m -XX:MaxDirectMemorySize=2g` |
| Logi | wolumin `terracotta-logs` (`/data/logs`) |

Suma rozmiarów `clustered-dedicated` wszystkich pamięci w `ehcacheDefault.xml` i `ehcacheCommon.xml` musi mieścić się
w `primary-server-resource` (obecnie 388 MB: znaczniki czasu Hibernate 4, transakcje globalne 64, metadane typów 64, obiekty spraw 128, dokumenty Lucene 128). `MaxDirectMemorySize` powinno być większe niż suma zasobów off-heap,
a pamięć maszyny wirtualnej większa od `MaxDirectMemorySize` plus sterta.

**Zasada zgodności:** ten sam alias pamięci musi mieć identyczny rozmiar `clustered-dedicated` we wszystkich
konfiguracjach klientów. Niezgodny rozmiar kończy się błędem `InvalidServerStoreConfigurationException` przy starcie
klienta; usunięcie pamięci z serwera (`destroyCache`) albo restart serwera naprawia sytuację.

## Wdrożenie na Proxmoksie

Serwer Terracotta jest wrażliwy na opóźnienie sieci do węzłów aplikacji, więc maszynę (lub kontener LXC) należy
postawić w tej samej sieci L2 i, jeśli to możliwe, na tym samym hoście Proxmox co węzły Mercury. Szczegóły w
rozmowie z autorem zadania 118 (rekomendacja: mała maszyna wirtualna z Linuksem i Dockerem, 2 vCPU, 4 GB RAM, dysk
nie jest krytyczny).
