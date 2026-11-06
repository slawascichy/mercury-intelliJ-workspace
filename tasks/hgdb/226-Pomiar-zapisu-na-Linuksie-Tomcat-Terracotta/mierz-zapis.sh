#!/bin/bash
# Pomiar czasu zapisu w CMIS (Browser Binding) na działającym Mercury DB: zadanie 226.
#
# Tworzy własny folder pomiarowy w katalogu głównym repozytorium, mierzy w nim kolejno (jedno żądanie na raz):
#   - odczyt (GET obiektu folderu), jako czas odniesienia: opóźnienie sieci i narzut serwera bez zapisu,
#   - createFolder (N podfolderów),
#   - createDocument (N dokumentów z małą treścią tekstową),
# a na końcu usuwa folder pomiarowy (deleteTree), chyba że KEEP=1. Pierwsze WARM żądań każdego rodzaju jest
# odrzucanych (rozgrzewka JIT i pamięci podręcznych) i nie liczy się do statystyk.
#
# Użycie:  CMIS_USER=<użytkownik>:<hasło> LABEL=<opis> ./mierz-zapis.sh
# Zmienne: CMIS_USER  wymagana (nie zapisuj hasła w repozytorium)
#          CMIS_BASE  domyślnie http://127.0.0.1:8080/mercury-ws-app/browser/documents
#          N          liczba mierzonych żądań każdego rodzaju (domyślnie 35, jak w zadaniu 118)
#          WARM       liczba żądań rozgrzewkowych (domyślnie 5)
#          LABEL      opis wariantu w wyniku (np. A-regiony-klastrowe)
#          KEEP=1     nie usuwaj folderu pomiarowego (domyślnie usuwany na końcu, także po błędzie lub Ctrl+C)
#          OPS        które operacje mierzyć, domyślnie "read createFolder createDocument"
# Wynik:   wiersz na rodzaj operacji (ms): n, min, p50, p90, max; po nim tabela wierszy do wklejenia do TASK.md.
# Uwaga:   błąd klienta (HTTP 000) pomija tylko jedno żądanie (obserwacja 157); inny kod błędu przerywa daną operację.
# Uwaga:   uruchamiaj z maszyny o znanym opóźnieniu do serwera. Najczystszy pomiar jest z samego hosta serwera
#          (devops-box-01); z innej maszyny czas odczytu pokazuje, ile dochodzi na sieć.
set -u
: "${CMIS_USER:?ustaw CMIS_USER=<użytkownik>:<hasło>}"
BASE="${CMIS_BASE:-http://127.0.0.1:8080/mercury-ws-app/browser/documents}"
N="${N:-35}"; WARM="${WARM:-5}"; LABEL="${LABEL:-pomiar}"; KEEP="${KEEP:-0}"
stamp=$(date +%Y%m%d-%H%M%S)
parent="Perf226-$stamp"
OPS="${OPS:-read createFolder createDocument}"
tmp=$(mktemp -d); created=0
# usunięcie folderu pomiarowego także po błędzie lub przerwaniu (Ctrl+C), chyba że KEEP=1
cleanup() {
	if [ "$created" = 1 ] && [ "$KEEP" != 1 ]; then
		created=0
		timed -X POST "$URL" -F cmisaction=deleteTree -F allVersions=true > /dev/null
		case "$(cat "$tmp/code")" in
		200 | 204) echo "folder $parent usunięty" ;;
		*) echo "UWAGA: folder $parent nie został usunięty (HTTP $(cat "$tmp/code")); usuń go ręcznie" ;;
		esac
	fi
	rm -rf "$tmp"
}
trap cleanup EXIT INT TERM
echo "tresc pomiarowa zadania 226 ($stamp)" > "$tmp/doc.txt"
# curl w Windows nie rozumie ścieżek MSYS (/tmp/...); cygpath daje ścieżkę w postaci C:/...
docfile=$(cygpath -m "$tmp/doc.txt" 2>/dev/null || echo "$tmp/doc.txt")

# czas jednego żądania w ms (w stdout), treść odpowiedzi w $tmp/out, kod HTTP w $tmp/code
timed() {
	curl -s -o "$tmp/out" -w '%{http_code} %{time_total}\n' -u "$CMIS_USER" "$@" > "$tmp/res"
	read -r code secs < "$tmp/res"
	echo "$code" > "$tmp/code"
	awk -v s="$secs" 'BEGIN { printf "%.1f\n", s * 1000 }'
}

# statystyka z listy liczb (jedna na wiersz): n min p50 p90 max
stats() {
	sort -n | awk '{ a[NR] = $1 } END {
		if (NR == 0) { print "0 - - - -"; exit }
		p50 = a[int((NR + 1) / 2)]; i90 = int(NR * 0.9 + 0.999); if (i90 < 1) i90 = 1
		printf "%d %.0f %.0f %.0f %.0f\n", NR, a[1], p50, a[i90], a[NR] }'
}

fail() { echo "BŁĄD: $*"; echo "ostatnia odpowiedź: $(head -c 300 "$tmp/out")"; exit 1; }

# folder pomiarowy
timed -X POST "$BASE/root" -F cmisaction=createFolder -F propertyId[0]=cmis:objectTypeId -F propertyValue[0]=cmis:folder \
	-F propertyId[1]=cmis:name -F propertyValue[1]="$parent" -F succinct=true > /dev/null
[ "$(cat "$tmp/code")" = 201 ] || [ "$(cat "$tmp/code")" = 200 ] || fail "nie utworzono folderu pomiarowego (HTTP $(cat "$tmp/code"))"
URL="$BASE/root/$parent"; created=1

run() { # $1 nazwa, $2 polecenie (funkcja) ; rozgrzewka + N pomiarów; błąd operacji pomija tę operację, nie cały pomiar
	local name="$1" fn="$2" i t
	: > "$tmp/$name.ms"
	for i in $(seq 1 $((WARM + N))); do
		t=$($fn "$i")
		case "$(cat "$tmp/code")" in
		200 | 201) ;;
		000)
			# błąd po stronie klienta (curl nie dokończył odczytu, mimo że serwer mógł odpowiedzieć; ok. 3 na 1000 żądań na
			# Windowsie, obserwacja 157): pomijam tylko to żądanie, pozostałe pomiary zostają
			echo "UWAGA: $name nr $i: HTTP 000 (błąd klienta): $(head -c 120 "$tmp/out"); to żądanie pominięte w wyniku"
			continue ;;
		*) echo "UWAGA: $name nr $i: HTTP $(cat "$tmp/code"): $(head -c 200 "$tmp/out"); operacja pominięta w wyniku"
			: > "$tmp/$name.ms"; return 1 ;;
		esac
		[ "$i" -gt "$WARM" ] && echo "$t" >> "$tmp/$name.ms"
	done
}

op_read() { timed "$URL?cmisselector=object&succinct=true"; }
op_folder() { timed -X POST "$URL" -F cmisaction=createFolder -F propertyId[0]=cmis:objectTypeId -F propertyValue[0]=cmis:folder \
	-F propertyId[1]=cmis:name -F propertyValue[1]="F$1" -F succinct=true; }
op_doc() { timed -X POST "$URL" -F cmisaction=createDocument -F propertyId[0]=cmis:objectTypeId -F propertyValue[0]=cmis:document \
	-F propertyId[1]=cmis:name -F propertyValue[1]="D$1.txt" -F "content=@$docfile;type=text/plain" -F succinct=true; }

for op in $OPS; do
	case "$op" in
	read) run read op_read ;;
	createFolder) run createFolder op_folder ;;
	createDocument) run createDocument op_doc ;;
	*) echo "UWAGA: nieznana operacja $op (dozwolone: read createFolder createDocument)" ;;
	esac
done

echo "== $LABEL: $BASE, $N pomiarów po $WARM rozgrzewkowych, $(date '+%Y-%m-%d %H:%M')"
printf '%-16s %4s %6s %6s %6s %6s\n' operacja n min p50 p90 max
rows=""
for name in $OPS; do
	[ -f "$tmp/$name.ms" ] || continue
	read -r n mn p50 p90 mx <<< "$(stats < "$tmp/$name.ms")"
	printf '%-16s %4s %6s %6s %6s %6s\n' "$name" "$n" "$mn" "$p50" "$p90" "$mx"
	rows="$rows| $LABEL | $name | $n | $mn | $p50 | $p90 | $mx |\n"
done
echo
echo "| wariant | operacja | n | min | p50 | p90 | max |   (ms)"
printf "$rows"
