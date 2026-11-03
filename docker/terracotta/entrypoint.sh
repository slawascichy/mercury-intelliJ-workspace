#!/bin/bash
# server (domyślnie): uruchamia serwer Terracotta; bench: mikrotest opóźnienia klienta (TC_URL=terracotta://host:9510/default-server)
set -e
case "${1:-server}" in
  server)
    export JAVA_OPTS="${JAVA_OPTS:--Xms256m -Xmx512m -XX:MaxDirectMemorySize=2g}"
    exec /opt/terracotta/server/bin/start-tc-server.sh -f /config/tc-config.xml -n default-server
    ;;
  bench)
    : "${TC_URL:?ustaw TC_URL, np. terracotta://serwer:9510/default-server}"
    exec java -Dtc.url="$TC_URL" -cp "/opt/bench:/opt/terracotta/client/ehcache/*:/opt/terracotta/client/lib/*" Bench
    ;;
  *)
    exec "$@"
    ;;
esac
