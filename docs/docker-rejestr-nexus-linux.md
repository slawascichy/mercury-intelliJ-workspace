# Rejestr obrazów w Nexusie: konfiguracja demona Dockera na Linuksie

Obrazy Mercury DB leżą w repozytorium `docker-hosted` na `nexus.scisoftware.local:5000`. Rejestr działa po HTTP, więc demon Dockera na maszynie uruchamiającej kompozycje (np. `devops-box-01`) musi uznać go za niezabezpieczony. Na Windows robi się to w Docker Desktop (Settings → Docker Engine); na Linuksie w `/etc/docker/daemon.json`.

## 1. Nazwa hosta

```bash
getent hosts nexus.scisoftware.local
curl -s -o /dev/null -w '%{http_code}\n' http://nexus.scisoftware.local:5000/v2/   # 401 = rejestr odpowiada
```

Gdy nazwa się nie rozwiązuje, dopisz do `/etc/hosts` wiersz `<IP Nexusa> nexus.scisoftware.local`.

## 2. `daemon.json`

```bash
sudo mkdir -p /etc/docker
sudo nano /etc/docker/daemon.json
```

```json
{
  "insecure-registries": ["nexus.scisoftware.local:5000"]
}
```

Gdy plik ma już inne klucze, dopisz tylko ten, a poprzedni wiersz zakończ przecinkiem. Składnię sprawdza `python3 -m json.tool /etc/docker/daemon.json`.

## 3. Restart demona

```bash
sudo systemctl restart docker
docker info | grep -A3 -i "insecure registries"   # ma pokazać nexus.scisoftware.local:5000
```

Restart zatrzymuje działające kontenery, chyba że `daemon.json` ma `"live-restore": true`. Dla Dockera rootless plik leży w `~/.config/docker/daemon.json`, a nie w `/etc/docker`.

## 4. Logowanie

```bash
docker login nexus.scisoftware.local:5000 -u claude
```

Hasło podaj interaktywnie albo przez `--password-stdin`. Nie zapisuj go w plikach repozytorium.

## 5. Uruchomienie kompozycji

Prefiks rejestru czyta zmienna `HGDB_REGISTRY` (z ukośnikiem na końcu):

```bash
cd mercury-three-node-cluster
export HGDB_REGISTRY=nexus.scisoftware.local:5000/
docker compose pull
docker compose up -d
```

Zmienna działa tylko w bieżącej sesji. Można ją wpisać do pliku `.env` obok `docker-compose.yml` (`HGDB_REGISTRY=nexus.scisoftware.local:5000/`).

## 6. Katalogi danych

Sekcja `volumes:` w kompozycjach wskazuje katalogi hosta (`device:`) pod `/d/mercury/...`, czyli ścieżki z Windows. Na Linuksie zmień je na istniejące katalogi (np. `/opt/mercury/...`) i utwórz je przed startem. Bind-mount do katalogu, którego nie ma, kończy się błędem. Skrypty inicjalizacyjne PostgreSQL i OpenLDAP uruchamiają się tylko na pustych katalogach.

Źródło: procedura wydania 211a (`tasks/hgdb/211-Aktualizacja-obrazow-Docker-i-wydanie/procedura-wydania.md`), kompozycje w `mercury-docker`.
