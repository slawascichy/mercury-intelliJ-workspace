# [222] [GUI] Panel monitorowania sekretarzy

https://github.com/slawascichy/hgdb/issues/222

1. Rozbudowa usług rest  mercury-ws-app\src\main\java\pro\ibpm\mercury\rest\server\actions\secretaries
   \SecretariesRest.java. Dodanie usług wpierwjących wizualizację stanu sekretarzy:
    - Czy pracuje?
    - Jak długie sa kolejki (wielkość buforów)
2. W oparciu o SecretariesRest przygotowac stronę monitoringu sekretarzy w mercury-ws-app. Analogicznie jak działa mercury-ws-app\src\main\webapp\static\admin\loggers.html: sekcje dotyczące posczególnych sekretarzy z wizualizacją działania i przyciskiem start/pobudź.
## Realizacja (2026-11-02, gałąź `hgdb-049`)

### Etap 1: API (zrobione)

- Zakres i znaczenie przycisku (decyzje autora): panel obejmuje węzeł obsługujący żądanie; „start” to pobudzenie sekretarza (istniejące usługi `wakeUp…Secretary`).
- `mercury-srv`, pakiet `org.mercury.business.secretaries`: `ISecretariesStateBusiness`, `SecretariesStateBusiness`, `SecretaryState`, `SecretaryBufferState`. Stan „czy pracuje” z menedżerów sekretarzy (`isWorking()`), rozmiary buforów jako `SELECT count(*)` z tabel o stałych nazwach.
- Bufory pokazane tylko dla tabel, które są kolejkami sekretarza (zweryfikowane w encjach): `bpmBPDInstance` (`IGO_DA_BPM_BPD_INSTANCE_B`), `bpmTask` (`IGO_DA_BPM_TASK_B`, `IGO_DA_BPM_TASK_NARRATIVE_B`), `caseIndex` (bieżący `IGO_LUC_SAVE_BUFFER`, hurtowy `IGO_LUC_SAVE_BUFFER_BULK`, archiwum `IGO_LUC_ARCH_SAVE_BUFFER`), `statsBuffer` (`IGO_DA_STATS_BUFFER`). `caseMigrator`, `reportExport`, `reportImport`, `caseAttributes`: tylko stan pracy (brak kolejki w bazie, którą dałoby się policzyć jednoznacznie).
- Nie ma jeszcze rozmiaru „w przetwarzaniu” dla sekretarza indeksu: w `CaseSaveBuffer` nie znalazłem kolumny znacznika przetwarzania (przypuszczenie: stan trzymany w pamięci sekretarza, do sprawdzenia przy stronie).
- `mercury-ws-app`: `POST /rest/service/SecretariesRest/getSecretariesState` (`SecretariesRest`, `SecretariesRestRequests.SecretariesStateRequest`, `SecretariesRestResponses.SecretariesStateResponse`: `nodeName`, `timestamp`, `secretaries[]`). Bez nowego DTO w `mercury-lib`, więc bez nowego wydania biblioteki.
- Testy: `SecretariesStateBusinessTest` (7), `SecretariesRestStateTest` (2): OK.
- OpenAPI: `SecretariesRest` nie ma dziś kluczy w `openapi-docs_*.properties` (usługi `wakeUp…` też), więc nic nie uzupełniałem; do decyzji, czy dodać opisy dla całego `SecretariesRest`.

### Do zrobienia

- Etap 2: strona `static/admin/secretaries.html` wzorowana na `loggers.html`, link na `pages/index.jsp`, uprawnienia (`mrc-sysadmin` w `web.xml`), klucze `app.index.*`.
- Etap 3: test ręczny na dev z `LuceneVolumeTest -Dperf.reindex=true -Dperf.reindexBulk=true` i `BulkClusterTest`.
