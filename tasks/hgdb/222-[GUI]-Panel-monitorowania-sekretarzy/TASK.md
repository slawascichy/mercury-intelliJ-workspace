# [222] [GUI] Panel monitorowania sekretarzy

https://github.com/slawascichy/hgdb/issues/222
**Status: ✅ zamknięte 2026-11-02** (do zatwierdzenia i zamknięcia w GitHubie przez autora). Podsumowanie w sekcjach „Realizacja” poniżej i w `podsumowanie-2026-11-02.md`.

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
- `mercury-ws-app`: `POST /rest/service/SecretariesRest/getSecretariesState` (`SecretariesRest`, `SecretariesRestRequests.SecretariesStateRequest`, `SecretariesRestResponses.SecretariesStateResponse`: `nodeName`, `timestamp`, `secretaries[]`). Bez nowego DTO w `mercury-lib`, więc bez nowego wydania biblioteki.
- Testy: `SecretariesStateBusinessTest` (7), `SecretariesRestStateTest` (2): OK.
- OpenAPI: `SecretariesRest` nie ma dziś kluczy w `openapi-docs_*.properties` (usługi `wakeUp…` też), więc nic nie uzupełniałem; do decyzji, czy dodać opisy dla całego `SecretariesRest`.

### Do zrobienia

- Etap 2: strona `static/admin/secretaries.html` wzorowana na `loggers.html`, link na `pages/index.jsp`, uprawnienia (`mrc-sysadmin` w `web.xml`), klucze `app.index.*`.
- Etap 3: test ręczny na dev z `LuceneVolumeTest -Dperf.reindex=true -Dperf.reindexBulk=true` i `BulkClusterTest`.

### Etap 1b: opisy OpenAPI (zrobione, 2026-11-02)

- `SecretariesRest` przemianowany na `SecretariesExtRest` (interfejs `ISecretariesExtRest`), bo generator opisów OpenAPI obejmuje tylko kontrolery `*ExtRest` (`ExtRestOpenApi`). Adres `/rest/service/SecretariesRest/...` bez zmian. Proxy `rest2` (przestarzałe) dziedziczy po nowej klasie.
- Odpowiedź stanu ma kopertę z polem `dto` (`SecretariesStateResponse.dto`: `nodeName`, `timestamp`, `secretaries[]`), jak pozostałe usługi `*ExtRest`.
- `@WSDLDocumentation` na interfejsie i 9 operacjach; 28 kluczy `ISecretariesExtRest.*` w `openapi-docs_{pl,en,de,es,fr,ko}.properties` (`mercury-ws-app`). Tłumaczenia: `openapi_docs_sync.py --apply` (Gemini; zgoda autora na wysyłkę opisów). Generator nie widzi `*ExtRest`, więc fragmenty braków przygotowałem ręcznie (z kluczem pomocniczym w kopii katalogu).
- Test `SecretariesExtRestOpenApiTest`: 9 operacji, brak braków opisów i tłumaczeń we wszystkich językach.

### Etap 2: strona i zaplecze (zrobione, do sprawdzenia na Tomcacie)

- `org.mercury.rest.server.actions.secretaries.SecretariesPanelController` pod `/admin/secretaries` (`state`, `wakeup`): sesja + rola `mrc-sysadmin` (`LoggerLevelsExtRest.isSysAdmin` jest teraz publiczne), błędy w kopercie.
- `web.xml`: `/admin/secretaries/*` w kolejnym `security-constraint` z `mrc-sysadmin` (strona `/static/admin/*` już była chroniona).
- `static/admin/secretaries.html`: karta na sekretarza (wskaźnik pracy, bufory z paskami, przycisk „Pobudź”), odświeżanie ręczne i automatyczne (2–30 s), pl/en jak `loggers.html`.
- Link na `pages/index.jsp` i klucz `app.index.systemSecretaries` w 12 plikach tekstów (`WebAppMsg_*` i `*_utf8`).
- Testy: `SecretariesPanelControllerTest` (2); całość `mercury-ws-app`: 224 testy OK.

### Do zrobienia

- Sprawdzić stronę na Tomcacie po wdrożeniu WAR (logowanie `mrc-sysadmin`, bufory przy `LuceneVolumeTest -Dperf.reindex=true -Dperf.reindexBulk=true`, `BulkClusterTest`).

### Etap 3: test na dev (zrobione, 2026-11-02)

`LuceneVolumeTest -Dperf.cases=2000 -Dperf.reindex=true -Dperf.reindexBulk=true -Dperf.reindexEntries=100000` na `mercury-db-test`: bufor hurtowy opróżniony po 147 s od startu (ok. 680 wpisów/s), bufor bieżący przez cały czas 0, wpis bieżący przetworzony po 251–1003 ms w trakcie przetwarzania hurtu. Autor potwierdził, że panel pokazuje narastanie i opróżnianie buforów oraz działa przycisk „Pobudź”. Zadanie 222 zakończone, do commitu i zamknięcia przez autora.
