# Dane pomiarowe CMIS (3250 folderów w folderze głównym)

Pomiary wydajności CMIS i katalogu spraw (`CaseCatalog`) wymagają folderu z tysiącami dzieci. Zadanie 049 używa 3250 folderów `Perf1`…`Perf3250` w folderze głównym repozytorium `documents`. Taki zestaw ujawnił wzorzec N+1 w `getChildren`, `createFolder` i `getObjectByPath`.

## Jak odtworzyć

1. Uruchom Tomcata z aplikacją `mercury-ws-app` na bazie testowej (`mercury-db-test`). Testy czyszczące bazę (np. `WsServerTest`, `SrvTest`) kasują te dane, więc po nich zestaw trzeba odtworzyć.
2. Wykonaj skrypt [`scripts/seed_cmis_folders.sh`](../scripts/seed_cmis_folders.sh):

   ```bash
   CMIS_USER=<użytkownik>:<hasło> scripts/seed_cmis_folders.sh        # Perf1..Perf3250, ok. 2,5 minuty
   CMIS_USER=<użytkownik>:<hasło> scripts/seed_cmis_folders.sh 5000 3251   # dokładanie kolejnych
   ```

   Skrypt tworzy foldery równolegle (6 żądań) przez wiązanie przeglądarkowe CMIS. Nie zapisuje poświadczeń.
3. Sprawdź wynik: `GET .../browser/documents/root?cmisselector=children&maxItems=1&succinct=true` zwraca `hasMoreItems: true`.

## Co mierzyć

| Operacja | Żądanie |
|---|---|
| `getChildren` | `GET <root>?cmisselector=children&maxItems=100&skipCount=<n>&succinct=true` (n = 0, 1500, 3100) |
| `getChildren` całość | `maxItems=5000` |
| `createFolder` | `POST <root>` z `cmisaction=createFolder` (patrz skrypt) |
| `getObjectByPath` | `GET <root>/<nazwa>?cmisselector=object` |

Wyniki z 2026-11-02 są w `tasks/hgdb/049-[CMIS]-Implementacja-API-CMIS/TASK.md` i w [analizie `JOIN FETCH`](analiza-join-fetch-zapytan-nazwanych.md).

## Inne sposoby ładowania danych

Większą próbkę danych testowych (sprawy, typy, dokumenty) ładuje scenariusz `datasetScenario` z `SrvTest` (moduł `mercury-srv`). Dane `mercury-db` (profil `scichy`) odtwarza autor przez `SrvTest`.
