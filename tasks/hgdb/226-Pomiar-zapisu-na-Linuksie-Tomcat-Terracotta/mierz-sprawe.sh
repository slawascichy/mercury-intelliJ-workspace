#!/bin/bash
# Pomiar odczytu i zapisu „dużej” sprawy (domyślnie FSMServiceOrder) przez REST: zadanie 226, punkt 3 i 5.
#
# Mierzy w jednym przebiegu (jedno żądanie naraz, rozgrzewka odrzucana):
#   - find (domyślne użycie pamięci podręcznych),
#   - find z cacheUsage=REFRESH (odczyt z bazy, bez pamięci),
#   - save (zapis tej samej sprawy z inną wartością pola `description`, więc powstaje nowa wersja).
#
# Użycie:  CASE_ID=FSMServiceOrder.2699 CLIENT_SECRET=<sekret GIUSoapUIClient> LABEL=A1-node1 ./mierz-sprawe.sh
# Zmienne: BASE       domyślnie http://127.0.0.1:8080/mercury-ws-app
#          CASE_ID    identyfikator sprawy (wymagany)
#          CLIENT_SECRET sekret klienta OAuth GIUSoapUIClient (wymagany; nie zapisuj w repozytorium)
#          MRC_USER   użytkownik (domyślnie admin), MRC_PASSWORD (domyślnie admin)
#          N, WARM    liczba pomiarów (35) i rozgrzewki (5)
#          OPS        "find findRefresh save" (domyślnie wszystkie)
# Wynik:   wiersze n, min, p50, p90, max w ms oraz tabela do wklejenia do TASK.md.
set -u
: "${CASE_ID:?ustaw CASE_ID}"
: "${CLIENT_SECRET:?ustaw CLIENT_SECRET}"
BASE="${BASE:-http://127.0.0.1:8080/mercury-ws-app}"
N="${N:-35}"; WARM="${WARM:-5}"; LABEL="${LABEL:-pomiar}"; OPS="${OPS:-find findRefresh save}"
USERN="${MRC_USER:-admin}"; PASSW="${MRC_PASSWORD:-admin}"
tmp=$(mktemp -d); trap 'rm -rf "$tmp"' EXIT
w() { cygpath -m "$1" 2>/dev/null || echo "$1"; }

TOK=$(curl -s -m 30 -X POST "$BASE/rest/token" --data-urlencode grant_type=password --data-urlencode "username=$USERN" \
	--data-urlencode "password=$PASSW" --data-urlencode "scope=mrc-user,mrc-sysadmin" --data-urlencode client_id=GIUSoapUIClient \
	--data-urlencode "client_secret=$CLIENT_SECRET" | sed -n 's/.*"access_token" *: *"\([^"]*\)".*/\1/p')
[ -n "$TOK" ] || { echo "brak tokenu OAuth"; exit 1; }
URL="$BASE/rest/service/CaseBusinessRest"
post() { # post <operacja> <plik z treścią> -> "kod czas"
	curl -s -o "$tmp/out" -w '%{http_code} %{time_total}\n' -X POST "$URL/$1" -H 'Content-Type: application/json;charset=UTF-8' \
		-H "Authorization: Bearer $TOK" --data-binary @"$(w "$2")"
}

printf '{"context":{"userName":"%s","maxDepth":8},"id":"%s"}' "$USERN" "$CASE_ID" > "$tmp/find.json"
printf '{"context":{"userName":"%s","maxDepth":8,"cacheUsage":"REFRESH"},"id":"%s"}' "$USERN" "$CASE_ID" > "$tmp/findr.json"
post find "$tmp/find.json" > /dev/null
cp "$tmp/out" "$tmp/case.json"

stats() { # stats <etykieta> <plik z czasami ms>
	sort -n "$2" | awk -v l="$1" -v lab="$LABEL" '{a[NR]=$1} END{ if(NR==0){print l"\tbrak"; exit}
		p50=a[int((NR+1)/2)]; p90=a[int(NR*0.9+0.9999)]; printf "%-14s n=%d min=%d p50=%d p90=%d max=%d\n", l, NR, a[1], p50, p90, a[NR];
		printf "| %s | %s | %d | %d | %d | %d | %d |\n", lab, l, NR, a[1], p50, p90, a[NR] >> "'"$(w "$tmp")"'/rows" }'
}

run() { # run <nazwa> <operacja REST> <plik|"save">
	local name="$1" op="$2" i code secs ms
	: > "$tmp/t.$name"
	for ((i = 1; i <= WARM + N; i++)); do
		if [ "$name" = save ]; then
			python -c "
import json,sys
d=json.load(open(sys.argv[1],encoding='utf-8'))['dto']
for e in d['propertyMap']['entries']:
    for k,v in e.items():
        if k.startswith('description^'): v['valueString']='Pomiar 226 '+sys.argv[2]; v['isString']=True
json.dump({'context':{'userName':sys.argv[3]},'mrcObject':d},open(sys.argv[4],'w',encoding='utf-8'),ensure_ascii=False)
" "$(w "$tmp/case.json")" "$LABEL-$i-$RANDOM" "$USERN" "$(w "$tmp/save.json")"
			read -r code secs < <(post save "$tmp/save.json")
		else
			read -r code secs < <(post "$op" "$3")
		fi
		if [ "$code" != 200 ]; then echo "UWAGA: $name nr $i: HTTP $code: $(head -c 200 "$tmp/out")"; continue; fi
		[ "$i" -le "$WARM" ] && continue
		ms=$(awk -v s="$secs" 'BEGIN{printf "%d", s*1000+0.5}'); echo "$ms" >> "$tmp/t.$name"
	done
}

echo "== $LABEL: $BASE, sprawa $CASE_ID, $N pomiarów po $WARM rozgrzewkowych, $(date '+%Y-%m-%d %H:%M')"
for op in $OPS; do
	case "$op" in
	find) run find find "$tmp/find.json"; stats find "$tmp/t.find" ;;
	findRefresh) run findRefresh find "$tmp/findr.json"; stats findRefresh "$tmp/t.findRefresh" ;;
	save) run save save x; stats save "$tmp/t.save" ;;
	esac
done
echo; echo '| wariant | operacja | n | min | p50 | p90 | max |   (ms)'; cat "$tmp/rows" 2>/dev/null
