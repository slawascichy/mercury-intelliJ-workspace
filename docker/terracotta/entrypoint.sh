#!/bin/bash
# server (domyślnie): uruchamia serwer Terracotta (kit Ehcache 3.10.x, dynamiczna konfiguracja);
# bench: mikrotest opóźnienia klienta (TC_URL=terracotta://host:9510/default-server)
#
# Serwer pojedynczy startuje z opcją -auto-activate (aktywuje się sam, bez config-tool). Po restarcie kontenera z zachowanym
# systemem plików (docker compose stop/start) startuje z zapisanej konfiguracji (repozytorium w ~/terracotta/config).
# Zmienne (wszystkie opcjonalne):
#   TC_PUBLIC_HOSTNAME  adres, pod którym serwer przedstawia się klientom (domyślnie localhost: klienci działają na hoście i łączą się
#                       przez opublikowany port; pusta wartość wyłącza, wtedy klienci z innych kontenerów używają nazwy usługi)
#   TC_PUBLIC_PORT      port widoczny dla klientów (domyślnie 9510; musi być równy opublikowanemu portowi hosta, patrz TC_PORT w compose)
#   TC_OFFHEAP_RESOURCES zasoby off-heap (domyślnie primary-server-resource:1024MB,secondary-server-resource:96MB)
#   TC_CLIENT_RECONNECT_WINDOW (domyślnie 120s), TC_CLIENT_LEASE_DURATION (domyślnie 150s), JAVA_OPTS
set -e
REPO="$HOME/terracotta/config"
case "${1:-server}" in
  server)
    export JAVA_OPTS="${JAVA_OPTS:--Xms256m -Xmx512m -XX:MaxDirectMemorySize=2g}"
    if [ -n "$(ls -A "$REPO" 2>/dev/null)" ]; then
      echo "[entrypoint] znaleziono repozytorium konfiguracji ($REPO), start z zapisanej konfiguracji"
      exec /opt/terracotta/server/bin/start-tc-server.sh
    fi
    PUBLIC=()
    if [ -n "${TC_PUBLIC_HOSTNAME-localhost}" ]; then
      PUBLIC=(-public-hostname "${TC_PUBLIC_HOSTNAME:-localhost}" -public-port "${TC_PUBLIC_PORT:-9510}")
    fi
    exec /opt/terracotta/server/bin/start-tc-server.sh -auto-activate \
      -name default-server -port 9510 -group-port 9530 \
      -cluster-name mercury-dev \
      -offheap-resources "${TC_OFFHEAP_RESOURCES:-primary-server-resource:1024MB,secondary-server-resource:96MB}" \
      -client-reconnect-window "${TC_CLIENT_RECONNECT_WINDOW:-120s}" \
      -client-lease-duration "${TC_CLIENT_LEASE_DURATION:-150s}" \
      -log-dir /data/logs "${PUBLIC[@]}"
    ;;
  bench)
    : "${TC_URL:?ustaw TC_URL, np. terracotta://serwer:9510/default-server}"
    exec java -Dtc.url="$TC_URL" -cp "/opt/bench:/opt/terracotta/client/ehcache/*:/opt/terracotta/client/lib/*" Bench
    ;;
  *)
    exec "$@"
    ;;
esac
