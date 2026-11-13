# [236] Deadlock przy równoczesnym starcie węzłów klastra (katalog główny CMIS, `wakeupSecretary` w transakcji)

Status: **zrobione 2026-11-13**, wydane w `mercury` 3.0.4.25 (obraz `ibpm/mercury:mercury-hgdb-3.0.4.25` w Nexusie).
Założone 2026-11-13 jako podzadanie zadania 227. Praca w gałęzi `hgdb-227` (odstępstwo od zasady „nowy kod w nowej gałęzi”
na wyraźne polecenie autora). Źródło: obserwacja 166 w `docs/obserwacje.md`.

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

## Wyniki (2026-11-13)

### Co zmieniono (`mercury` 3.0.4.25)

| Plik | Zmiana |
| --- | --- |
| `mercury-srv/.../LucCaseSaveBufferLogicHelper.java` | sekretarz indeksu budzony po `commit` (`wakeupSecretaryWhenCommitted`, `TransactionSynchronization.afterCommit`), raz na transakcję; poza transakcją od razu; błąd po `commit` tylko logowany. Dotyczy obu miejsc: `updateIndexByCases` i `updateIndexByCaseIds` |
| `mercury-srv-slave/.../SecretaryManagerWithServiceSupp.java` | ponawianie po `RemoteAccessException` (`wakeup` i `isWorking`) dostaje nazwę węzła, który zawiódł (`requestedMasterNameWithError`), a nie pierwotny parametr (`null`); wcześniej mogło wracać do tego samego węzła |
| `mercury-srv/.../CmisRepositoryBusiness.java` | `addRootToMountPoint`: węzeł, który przegra wyścig o punkt zamontowania (naruszenie klucza po zatwierdzeniu zwycięzcy), ponawia operację; dla istniejącego wpisu nic nie zmienia |
| `mercury-srv/.../Case2CaseLogic.java` | `addNodeToMountPoint(Context, Case, String)`: rodzic i dziecko wyniku ustawiane na przekazany węzeł, gdy są puste |

**Zmiana planu:** zamiast blokady pesymistycznej `FOR UPDATE` (punkt 1 zakresu) arbitrem jest klucz unikalny w bazie, a
przegrywający ponawia operację. Blokada na wierszu typu mogłaby zakleszczyć się z wątkami zapisującymi w osobnych
transakcjach (zapis bufora w puli wątków, `thread.get()`), bo `FOR UPDATE` blokuje też sprawdzenia kluczy obcych.
Limit czasu klienta HTTP (punkt 3) już istnieje (`mercury.node.redirection.read.timeout`, domyślnie 60 s); błędem była pętla
ponawiania. `depends_on` w kompozycjach (punkt 4) nie było potrzebne.

### Dodatkowo: `NullPointerException` w `Case2CaseBusinessRest/addNodeToMountPoint`

Endpoint nigdy nie działał: wpis bazowy ma jako rodzica i dziecko ten sam `CaseRootVersion` bez załadowanej ostatniej wersji
sprawy (tylko `id`), więc `Case2Case` miał puste `parent` i `child`, a `Case2CaseBusinessHelper.transform2Case2CaseRelationship`
kończył się `NullPointerException` (`CaseBusinessHelper.convert2CaseNarrative`), co wycofywało całą transakcję (warstwa
`Business` jest `@Transactional`). Po poprawce odpowiedź zawiera `parent`, `child`, `path`, `depth`, `mountPoint`.

### Testy

**Częstość błędu bez poprawki:** na obrazie 3.0.4.24 bez poprawki deadlock wystąpił raz (start trzech węzłów, ponad 8 minut,
nie kończył się sam), a trzy kolejne starty przeszły (dwa węzły 180 s, trzy węzły 229 s i 234 s). Wyścig jest losowy, więc
samo „start przechodzi” niczego nie dowodzi.

**Test deterministyczny (A/B):** dwuwęzłowa kompozycja, HTTP (port 8080) węzła z rolą MASTER zablokowany regułą `iptables`
w jego przestrzeni sieciowej (baza, Terracotta i Tribes działają), wywołanie `Case2CaseBusinessRest/addNodeToMountPoint` na
drugim węźle, pomiar najstarszej transakcji `idle in transaction` w `pg_stat_activity` tylko dla sesji wywołującego węzła:

| Obraz | Transakcja wywołującego węzła `idle in transaction` | Odpowiedź |
| --- | --- | --- |
| bez poprawki | **29 s** (cały czas blokady) | po 32 s, błąd `NullPointerException` |
| z poprawką | **0 s** | sukces, mount point zatwierdzony |
| z poprawką, HTTP zablokowany przez cały czas | – | sukces po 130 s (dwa nieudane wywołania z limitem czasu, ostrzeżenie `RemoteAccessException for 'node2'`), operacja ograniczona w czasie |

**Starty trzech węzłów na świeżej bazie z poprawką:** 202 s, 214 s (obraz testowy) i 244 s (obraz wydania 3.0.4.25), wszystkie
`healthy`. Czasy `Server startup` 82–148 s na węzeł (zob. obserwacja 168).

**Pierwszy test A/B (`docker pause`) był błędny:** wstrzymanie całego kontenera zatrzymuje też klienta Terracotty, więc
blokada pochodziła z klastrowego cache Hibernate (zob. obserwacja 167), a nie z wywołania sekretarza; wynik był taki sam
z poprawką i bez niej (29 s).

### Nie sprawdzono

- Ścieżka ponawiania w `CmisRepositoryBusiness.addRootToMountPoint` nie została wywołana w testach (nie udało się wymusić
  wyścigu o punkt zamontowania); brak testu jednostkowego, całość to integracja z Tomcatem, Springiem i bazą.
- Wywołanie sekretarza po `commit` w ścieżce `Case2SubCaseLogic` (ta sama funkcja pomocnicza, osobnego testu nie było).
- Czy po wycofaniu transakcji pozostaje wpis w buforze zmian bez obudzenia sekretarza: wpisy zapisuje wątek z puli (`thread.get()`),
  przypuszczalnie w osobnej transakcji, więc zostają i przetworzy je następne obudzenie (przypuszczenie z kodu, bez testu).
