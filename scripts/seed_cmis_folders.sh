#!/bin/bash
# Odtwarza dane pomiarowe CMIS: tworzy foldery Perf<od>..Perf<do> w folderze głównym repozytorium CMIS
# na działającym serwerze Mercury DB (Tomcat). Używane do pomiarów wydajności getChildren, createFolder,
# getObjectByPath i katalogu CaseCatalog przy dużej liczbie dzieci jednego folderu (zadanie 049).
#
# Użycie:   CMIS_USER=<użytkownik>:<hasło> scripts/seed_cmis_folders.sh [do=3250] [od=1]
# Zmienne:  CMIS_USER (wymagana, nie zapisuj hasła w repozytorium)
#           CMIS_BASE (domyślnie http://127.0.0.1:8080/mercury-ws-app/browser/documents/root)
#           CMIS_PARALLEL (domyślnie 6 równoległych żądań)
# Uwaga:    nazwa folderu musi być unikalna w folderze nadrzędnym. Powtórne uruchomienie z tym samym zakresem
#           zwróci 409 dla istniejących nazw. Dla zakresu 1..3250 czas to ok. 2,5 minuty.
set -u
: "${CMIS_USER:?ustaw CMIS_USER=<użytkownik>:<hasło>}"
BASE="${CMIS_BASE:-http://127.0.0.1:8080/mercury-ws-app/browser/documents/root}"
seq "${2:-1}" "${1:-3250}" | xargs -P "${CMIS_PARALLEL:-6}" -I{} curl -s -o /dev/null -w "%{http_code}\n" \
  -u "$CMIS_USER" -X POST "$BASE" \
  -F cmisaction=createFolder -F propertyId[0]=cmis:objectTypeId -F propertyValue[0]=cmis:folder \
  -F propertyId[1]=cmis:name -F propertyValue[1]=Perf{} -F succinct=true | sort | uniq -c
