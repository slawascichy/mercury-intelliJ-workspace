#!/bin/bash
# Lokalny broker Apache ActiveMQ 5.19.x w Dockerze dla pracy deweloperskiej Mercury DB.
# Zastępuje lokalny apache-activemq z mercury-server: OpenWire na porcie 51616, konsola WWW http://localhost:8161 (admin/admin).
#
# Użycie: ./startActiveMq.sh [start|stop|restart|status|logs|reset]
#   start    buduje obraz (przy pierwszym uruchomieniu), uruchamia broker i czeka na port OpenWire (domyślne polecenie)
#   stop     zatrzymuje broker i usuwa kontener (kolejki w woluminie KahaDB zostają)
#   restart  stop i start
#   status   pokazuje stan kontenera
#   logs     pokazuje log brokera (Ctrl+C kończy)
#   reset    jak stop, dodatkowo usuwa wolumin z danymi (kolejki)
# Zmienne (opcjonalne): AMQ_PORT (domyślnie 51616), AMQ_UI_PORT (8161), AMQ_JAVA_MEMORY, AMQ_WAIT_SECONDS (domyślnie 90).
# Uwaga: przed uruchomieniem zatrzymaj stary lokalny ActiveMQ (te same porty).
set -u
cd "$(dirname "$0")" || exit 1

if docker compose version > /dev/null 2>&1; then
	DC=(docker compose)
elif command -v docker-compose > /dev/null 2>&1; then
	DC=(docker-compose)
else
	echo "Brak docker compose (zainstaluj Docker Desktop albo plugin compose)." >&2
	exit 1
fi

PORT=${AMQ_PORT:-51616}
UI_PORT=${AMQ_UI_PORT:-8161}
WAIT=${AMQ_WAIT_SECONDS:-90}

port_busy() {
	(exec 3<> "/dev/tcp/127.0.0.1/$1") 2> /dev/null
}

do_start() {
	if ! docker ps --format '{{.Names}}' | grep -qx mercury-activemq; then
		for p in "$PORT" "$UI_PORT"; do
			if port_busy "$p"; then
				echo "Port $p jest zajęty (czy działa stary lokalny ActiveMQ?). Zatrzymaj go albo ustaw AMQ_PORT / AMQ_UI_PORT." >&2
				return 1
			fi
		done
	fi
	"${DC[@]}" up -d --build activemq || return 1
	echo "Czekam na broker (do ${WAIT}s)..."
	local t=0
	while [ "$t" -lt "$WAIT" ]; do
		if [ "$(docker inspect -f '{{.State.Health.Status}}' mercury-activemq 2> /dev/null)" = "healthy" ]; then
			echo "ActiveMQ działa. OpenWire: tcp://localhost:$PORT, konsola: http://localhost:$UI_PORT (admin/admin)"
			return 0
		fi
		sleep 3
		t=$((t + 3))
	done
	echo "Broker nie wystartował w ${WAIT}s. Log: ./startActiveMq.sh logs" >&2
	return 1
}

case "${1:-start}" in
	start) do_start ;;
	stop) "${DC[@]}" down ;;
	restart)
		"${DC[@]}" down
		do_start
		;;
	status) "${DC[@]}" ps ;;
	logs) "${DC[@]}" logs -f activemq ;;
	reset) "${DC[@]}" down -v ;;
	*)
		sed -n '2,14p' "$0" | sed 's/^# \{0,1\}//'
		exit 2
		;;
esac
