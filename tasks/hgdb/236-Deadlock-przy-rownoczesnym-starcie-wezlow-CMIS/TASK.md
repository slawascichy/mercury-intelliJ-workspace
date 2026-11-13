# [236] Deadlock przy równoczesnym starcie węzłów klastra (katalog główny CMIS, `wakeupSecretary` w transakcji)

Status: **założone 2026-11-13**, podzadanie zadania 227 (Logowanie w klastrze, sesje Tomcat). Praca w gałęzi `hgdb-227`
(odstępstwo od zasady „nowy kod w nowej gałęzi” na wyraźne polecenie autora). Źródło: obserwacja 166 w `docs/obserwacje.md`.

## Problem (krytyczny)

Przy równoczesnym starcie trzech węzłów na świeżej bazie (kompozycja trzywęzłowa, obraz 3.0.4.24) start nie kończy się:
po ponad 8 minutach węzły nadal są w „Waiting for startup”.

Ustalone 2026-11-13 (`pg_stat_activity`, `pg_blocking_pids`, `jstack`, `/proc/net/tcp`):

- Węzeł 1 trzyma otwartą transakcję (`idle in transaction`) po `insert into IGO_DA_CASE2CASE` i w tej samej transakcji
  wywołuje przez HTTP `wakeupSecretary` na węźle 2 (wątek `main` w `HttpInvokerClientInterceptor`).
- Węzły 2 i 3 stoją w bazie na blokadzie `transactionid` przy `insert into IGO_DA_CASE2CASE_MPS (ID)` (ta sama wartość
  klucza), więc ich wątek `main` nie kończy wdrażania `mercury-ws-app`, a Tomcat nie obsługuje żądania węzła 1
  (połączenie TCP jest przyjęte, bo konektor jest już związany).
- Klient HTTP nie ma skutecznego limitu czasu. Węzeł 1 czeka na węzeł 2 (HTTP), węzły 2 i 3 na węzeł 1 (baza).

Ścieżka wywołań: `MercuryCmisLifecycleBean.onApplicationEvent` → `CmisRepositoryBusiness.initializeRepositories` →
`ensureRootFolder` → `Case2CaseLogic.addNodeToMountPoint` → `refreshCatalogMembershipInIndex` →
`LucCaseSaveBufferLogicHelper.updateIndexByCaseIds` → `CaseIndexSecretaryHelper.wakeupSecretary` →
`ClientCaseIndexSecretaryManager.wakeup` (HTTP).

Niezwiązane z Tomcat Cluster (zadanie 227); zależy od kolejności i czasu startu (wcześniejsze starty tej kompozycji przechodziły).

## Ustalenia z kodu (2026-11-13)

- Główna ścieżka zapisu sprawy (`CaseChangesRegistry.registerChanges`) wstrzymuje wywołanie sekretarza na czas rejestracji
  (`WAKEUP_SECRETARY_PROP`). Wywołanie w transakcji zostaje tam, gdzie `updateIndexByCaseIds` jest wołane wprost:
  `Case2CaseLogic.refreshCatalogMembershipInIndex` (katalog, punkty zamontowania, CMIS), `Case2SubCaseLogic` (powiązania).
- Dane predefiniowane: nie ma reguły „tylko master”. Każdy węzeł ładuje je raz na JVM (`DAORegistry.loadPredefinedValues`),
  a równoległość jest tolerowana przez idempotentność (wyszukiwanie po `username`, zadania 156 i 172). Opcjonalny
  przełącznik: `mecrury.loadPredefinedValues.skip`.
- Master w klastrze ustala się dynamicznie z heartbeatów, więc przy równoczesnym starcie nie jest znany; reguła „tylko
  master” nie wyklucza wyścigu. Wspólnym arbitrem jest baza.
- `CmisRepositoryBusiness.ensureRootFolder` ma już próbę obsługi wyścigu (zostaje folder o najmniejszym identyfikatorze),
  ale nie obejmuje wpisu w `IGO_DA_CASE2CASE_MPS`.

## Zakres poprawki

1. **Serializacja tworzenia katalogu głównego CMIS w bazie:** sprawdzenie, utworzenie folderu i wpisu punktu zamontowania
   w jednej transakcji pod blokadą pesymistyczną na stałym wierszu (przenośne na wszystkie obsługiwane bazy) i **ponowne
   sprawdzenie po zdobyciu blokady**. Bez rozmowy między węzłami.
2. **Wywołanie sekretarza po `commit`** (`TransactionSynchronization.afterCommit`; wzorzec jest w `TypeCaseRegistryChanges`)
   w jednym miejscu, `LucCaseSaveBufferLogicHelper.updateIndexByCaseIds`, zamiast wywołania w otwartej transakcji.
3. **Limit czasu odczytu klienta HTTP invokera**, żeby żaden deadlock nie trwał w nieskończoność.
4. **Test:** start trzech węzłów równocześnie na świeżej bazie, powtórzony kilka razy; wcześniej odtworzenie błędu.

Do potwierdzenia: czy sekretarz indeksu nie opiera się wyłącznie na wywołaniu `wakeup` (przypuszczenie: sprawdza bufor
okresowo; wywołanie jest podpowiedzią).

## Wyniki

(do uzupełnienia)
