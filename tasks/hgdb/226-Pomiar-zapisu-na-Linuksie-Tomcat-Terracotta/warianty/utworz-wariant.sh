#!/bin/bash
# Tworzy wariant konfiguracji klastra: szablon mercury.properties z obrazu serwera + dopisane parametry + override kompozycji.
#
# Użycie:  ./utworz-wariant.sh <nazwa-katalogu> <znacznik-obrazu> <parametr=wartość> [<parametr=wartość> ...]
# Przykład: ./utworz-wariant.sh W8 mercury-hgdb-3.0.4.17 mercury.cache.luceneDocument.shared.writerThreads=8
#
# Wynik: katalog <nazwa-katalogu>/ z plikami mercury.properties (szablon z obrazu, CRLF jak w obrazie, parametry na końcu)
# i docker-compose.override.yml (montowanie szablonu na mercury-node1..3). Skopiuj oba pliki obok docker-compose.yml klastra
# i zrób `docker compose up -d --force-recreate mercury-node1 mercury-node2 mercury-node3`. Wariant domyślny to brak plików.
set -eu
[ $# -ge 3 ] || { sed -n '2,9p' "$0"; exit 2; }
name="$1"; tag="$2"; shift 2
dir="$(cd "$(dirname "$0")" && pwd)/$name"
mkdir -p "$dir"
# MSYS_NO_PATHCONV: Git Bash na Windowsie nie może zamieniać ścieżek kontenera
MSYS_NO_PATHCONV=1 docker run --rm --entrypoint cat "ibpm/mercury:$tag" /opt/mercury-3.0/docker-init-config/config/mercury.properties > "$dir/mercury.properties"
{
	printf '\r\n\r\n# Wariant %s (zadanie 229): parametry dopisane do szablonu z obrazu %s\r\n' "$name" "$tag"
	for kv in "$@"; do printf '%s\r\n' "$kv"; done
} >> "$dir/mercury.properties"
cat > "$dir/docker-compose.override.yml" <<EOF
# Wariant $name zadania 229: szablon mercury.properties z obrazu $tag + parametry: $*
# Skopiuj obok docker-compose.yml razem z plikiem mercury.properties z tego katalogu.
services:
  mercury-node1:
    volumes:
      - ./mercury.properties:/opt/mercury-3.0/docker-init-config/config/mercury.properties:ro
  mercury-node2:
    volumes:
      - ./mercury.properties:/opt/mercury-3.0/docker-init-config/config/mercury.properties:ro
  mercury-node3:
    volumes:
      - ./mercury.properties:/opt/mercury-3.0/docker-init-config/config/mercury.properties:ro
EOF
echo "Wariant $name: $dir (parametry: $*)"
