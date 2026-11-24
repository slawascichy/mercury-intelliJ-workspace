#!/bin/bash
# Lokalny serwer Terracotta (Ehcache clustered 3.10.8) w Dockerze dla pracy deweloperskiej Mercury DB.
# Zastępuje lokalny kit mercury-server/ehcache-clustered-3.6.1-kit: serwer nasłuchuje na tym samym porcie 9510 (klienci:
# terracotta://localhost:9510/...), ma zasoby primary-server-resource (1024 MB) i secondary-server-resource (96 MB).
#
# Użycie: ./startEhcacheServer.sh [start|stop|restart|status|logs|bench|reset]
#   start    buduje obraz (przy pierwszym uruchomieniu), uruchamia serwer i czeka na stan ACTIVE (domyślne polecenie)
#   stop     zatrzymuje serwer i usuwa kontener (pamięci podręczne w off-heap przepadają, jak przy każdym restarcie)
#   restart  stop i start
#   status   pokazuje stan kontenera i serwera Terracotta
#   logs     pokazuje log serwera (Ctrl+C kończy)
#   bench    mikrotest opóźnienia klienta (serwer musi działać)
#   reset    jak stop, dodatkowo usuwa wolumin logów
# Zmienne (opcjonalne): TC_PORT (domyślnie 9510), TC_GROUP_PORT (9530), TC_JAVA_OPTS, TC_PUBLIC_HOSTNAME (localhost),
# TC_WAIT_SECONDS (czas oczekiwania na gotowość, domyślnie 120). Uwaga: przed pierwszym uruchomieniem zatrzymaj stary lokalny serwer
# Terracotta (ten sam port).
set -u
# Git Bash na Windows zamienia ścieżki typu /opt/... w argumentach docker exec
export MSYS_NO_PATHCONV=1
cd "$(dirname "$0")" || exit 1

if docker compose version > /dev/null 2>&1; then
	DC=(docker compose)
elif command -v docker-compose > /dev/null 2>&1; then
	DC=(docker-compose)
else
	echo "Brak docker compose (zainstaluj Docker Desktop albo plugin compose)." >&2
	exit 1
fi

PORT=${TC_PORT:-9510}
WAIT=${TC_WAIT_SECONDS:-120}

state() {
	docker exec mercury-terracotta /opt/terracotta/tools/bin/config-tool.sh diagnostic -connect-to localhost:9510 2> /dev/null |
		awk '/Node state:/ { print $NF; exit }'
}

port_busy() {
	(exec 3<> "/dev/tcp/127.0.0.1/$PORT") 2> /dev/null
}

do_start() {
	if ! docker ps --format '{{.Names}}' | grep -qx mercury-terracotta && port_busy; then
		echo "Port $PORT jest zajęty (czy działa stary lokalny serwer Terracotta?). Zatrzymaj go albo ustaw TC_PORT." >&2
		return 1
	fi
	"${DC[@]}" up -d --build terracotta || return 1
	echo "Czekam na stan ACTIVE serwera Terracotta (do ${WAIT}s)..."
	local t=0 s=""
	while [ "$t" -lt "$WAIT" ]; do
		s=$(state)
		if [ "$s" = "ACTIVE" ]; then
			echo "Serwer Terracotta działa (ACTIVE). Adres klientów: terracotta://localhost:$PORT/<nazwa>"
			return 0
		fi
		sleep 5
		t=$((t + 5))
	done
	echo "Serwer nie osiągnął stanu ACTIVE w ${WAIT}s (stan: ${s:-nieznany}). Log: ./startEhcacheServer.sh logs" >&2
	return 1
}

case "${1:-start}" in
	start) do_start ;;
	stop) "${DC[@]}" down ;;
	restart)
		"${DC[@]}" down
		do_start
		;;
	status)
		"${DC[@]}" ps
		echo "Stan serwera Terracotta: $(state)"
		;;
	logs) "${DC[@]}" logs -f terracotta ;;
	bench) "${DC[@]}" --profile bench run --rm bench ;;
	reset) "${DC[@]}" down -v ;;
	*)
		sed -n '2,17p' "$0" | sed 's/^# \{0,1\}//'
		exit 2
		;;
esac
