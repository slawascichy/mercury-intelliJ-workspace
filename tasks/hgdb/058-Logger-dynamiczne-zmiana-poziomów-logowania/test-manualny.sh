#!/bin/bash
# Ręczny test usługi zmiany poziomów logowania (zadanie 58).
#
# Dane dostępowe czyta z pliku (poza repozytorium), którego ten skrypt nie wypisuje:
#   ~/.mercury-test-058.env   (domyślnie; inną ścieżkę podaje zmienna ENV_FILE)
# Zawartość pliku (KEY=value, bez cudzysłowów):
#   BASE=http://localhost:8080/mercury-ws-app        # adres aplikacji mercury-ws-app (bez końcowego /)
#   TUSER=nazwa_uzytkownika_z_rola_mrc-sysadmin
#   TPASSWORD=haslo
#   CLIENT_ID=identyfikator_klienta_oauth
#   CLIENT_SECRET=sekret_klienta_oauth
#   # opcjonalnie: drugi użytkownik BEZ roli mrc-sysadmin (test odmowy)
#   NUSER=zwykly_uzytkownik
#   NPASSWORD=haslo
#   # opcjonalnie: kategoria do testów (domyślnie org.mercury.lucene)
#   LOGGER=org.mercury.lucene
#   # opcjonalnie: zakresy tokenu administratora (domyślnie mrc-user,mrc-sysadmin). Zakres jest parametrem WYMAGANYM
#   # żądania /rest/token i musi mieć część wspólną z zakresami skonfigurowanymi dla ścieżki /rest/service/**
#   SCOPE=mrc-user,mrc-sysadmin
#
# Użycie: bash test-manualny.sh
ENV_FILE="${ENV_FILE:-$HOME/.mercury-test-058.env}"
if [ ! -r "$ENV_FILE" ]; then echo "Brak pliku $ENV_FILE (opis w nagłówku skryptu)"; exit 2; fi
# shellcheck disable=SC1090
. "$ENV_FILE"
LOGGER="${LOGGER:-org.mercury.lucene}"
SCOPE="${SCOPE:-mrc-user,mrc-sysadmin}"
SVC="$BASE/rest/service/LoggerLevelsExtRest"
PASS=0; FAIL=0

token() { # $1 użytkownik, $2 hasło, $3 zakresy (opcjonalnie, domyślnie $SCOPE)
  curl -sS -X POST "$BASE/rest/token" \
    --data-urlencode "grant_type=password" --data-urlencode "username=$1" --data-urlencode "password=$2" \
    --data-urlencode "scope=${3:-$SCOPE}" \
    --data-urlencode "client_id=$CLIENT_ID" --data-urlencode "client_secret=$CLIENT_SECRET" \
    | sed -n 's/.*"access_token" *: *"\([^"]*\)".*/\1/p'
}

call() { # $1 operacja, $2 JSON, $3 token (puste = bez tokenu)
  if [ -n "$3" ]; then
    curl -sS -w '\nHTTP=%{http_code}' -X POST "$SVC/$1" -H 'Content-Type: application/json;charset=UTF-8' \
      -H "Authorization: Bearer $3" -d "$2"
  else
    curl -sS -w '\nHTTP=%{http_code}' -X POST "$SVC/$1" -H 'Content-Type: application/json;charset=UTF-8' -d "$2"
  fi
}

check() { # $1 opis, $2 odpowiedź, $3 wzorzec, który musi wystąpić
  if echo "$2" | tr -d " " | grep -q -- "$3"; then PASS=$((PASS+1)); echo "  [OK]   $1"; else FAIL=$((FAIL+1)); echo "  [BŁĄD] $1  (oczekiwano: $3)"; fi
}

echo "== Token administratora"
T=$(token "$TUSER" "$TPASSWORD")
if [ -z "$T" ]; then echo "Nie udało się pobrać tokenu (sprawdź BASE, dane użytkownika i klienta OAuth)."; exit 3; fi
echo "  token pobrany (${#T} znaków)"

echo "== 1. search: limit i obcięcie"
R=$(call search '{"namePart":"","limit":1000}' "$T"); echo "$R" | tail -c 400; echo
check "limit ograniczony do 30" "$R" '"limit":30'
check "brak błędu (errorCode pusty)" "$R" '"errorCode":""'
R=$(call search '{"namePart":"mercury","limit":2}' "$T")
check "obcięcie wyniku do 2 (truncated)" "$R" '"truncated":true'

echo "== 2. getLevel kategorii $LOGGER"
R=$(call getLevel "{\"loggerName\":\"$LOGGER\"}" "$T"); echo "$R"
check "zwraca effectiveLevel" "$R" '"effectiveLevel"'
check "zwraca nazwę backendu" "$R" '"backend"'

echo "== 3. setLevel DEBUG"
R=$(call setLevel "{\"loggerName\":\"$LOGGER\",\"level\":\"debug\"}" "$T"); echo "$R"
check "poziom ustawiony na DEBUG" "$R" '"level":"DEBUG"'
check "poziom obowiązujący DEBUG" "$R" '"effectiveLevel":"DEBUG"'
R=$(call getLevel "{\"loggerName\":\"$LOGGER\"}" "$T")
check "getLevel widzi zmianę" "$R" '"level":"DEBUG"'
R=$(call search "{\"namePart\":\"$LOGGER\",\"onlyConfigured\":true,\"limit\":5}" "$T")
check "search onlyConfigured znajduje kategorię" "$R" "\"name\":\"$LOGGER\""

echo "== 4. setLevel INHERIT (powrót do dziedziczenia)"
R=$(call setLevel "{\"loggerName\":\"$LOGGER\",\"level\":\"INHERIT\"}" "$T"); echo "$R"
check "poziom ustawiony wprost usunięty (null)" "$R" '"level":null'
check "poprzedni poziom DEBUG" "$R" '"previousLevel":"DEBUG"'

echo "== 5. Błędy walidacji"
R=$(call getLevel '{"loggerName":"org mercury"}' "$T"); echo "$R" | head -c 300; echo
check "niedozwolone znaki w nazwie" "$R" '"errorCode":"'
R=$(call setLevel "{\"loggerName\":\"$LOGGER\",\"level\":\"VERBOSE\"}" "$T")
check "nieznany poziom" "$R" '"errorCode":"'
R=$(call setLevel '{"loggerName":"ROOT","level":"INHERIT"}' "$T")
check "INHERIT na ROOT odrzucone" "$R" '"errorCode":"'
R=$(call getLevel '{"loggerName":""}' "$T")
check "pusta nazwa" "$R" '"errorCode":"'

echo "== 6. Brak tokenu"
R=$(call getLevel "{\"loggerName\":\"$LOGGER\"}" ""); echo "$R" | tail -c 200; echo
check "odmowa bez tokenu (kod HTTP 401/403 albo błąd w kopercie)" "$R" 'HTTP=40[13]\|"errorCode":"'

if [ -n "$NUSER" ]; then
  echo "== 7. Użytkownik bez roli mrc-sysadmin (token z zakresem mrc-user)"
  N=$(token "$NUSER" "$NPASSWORD" "mrc-user")
  R=$(call getLevel "{\"loggerName\":\"$LOGGER\"}" "$N"); echo "$R" | head -c 400; echo
  check "odmowa dla użytkownika bez roli (SC001)" "$R" 'SC001\|"errorCode":"'
  R=$(call setLevel "{\"loggerName\":\"$LOGGER\",\"level\":\"TRACE\"}" "$N")
  check "zmiana odrzucona dla użytkownika bez roli" "$R" '"errorCode":"'

  echo "== 8. Zwykły użytkownik prosi o zakres administratora (mrc-user,mrc-sysadmin)"
  N2=$(token "$NUSER" "$NPASSWORD" "mrc-user,mrc-sysadmin")
  if [ -z "$N2" ]; then
    PASS=$((PASS+1)); echo "  [OK]   serwer nie wydał tokenu z zakresem mrc-sysadmin zwykłemu użytkownikowi"
  else
    R=$(call getLevel "{\"loggerName\":\"$LOGGER\"}" "$N2")
    if echo "$R" | tr -d " " | grep -q '"errorCode":""'; then
      FAIL=$((FAIL+1)); echo "  [BŁĄD] zwykły użytkownik dostał token z zakresem mrc-sysadmin i dostęp administratora (oczekiwano odmowy: zakres tokenu ma być związany z rolami użytkownika)"
    else
      PASS=$((PASS+1)); echo "  [OK]   token wydany, ale dostęp administratora odrzucony"
    fi
  fi
fi

echo
echo "Wynik: $PASS OK, $FAIL błędów."
echo "Sprawdź ręcznie w logu serwera wpisy WARN 'Zmiana poziomu logowania' (po jednym na każdy setLevel administratora"
echo "oraz brak takich wpisów dla prób użytkownika bez roli)."
[ "$FAIL" -eq 0 ]
