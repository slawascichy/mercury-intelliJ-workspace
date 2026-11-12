# Podsumowanie 2026-11-12

## Zamknięte i wydane

- **Wydanie 3.0.4.23 (obraz z nowymi zmiennymi pul JDBC):** `mercury` 3.0.4.23 wydane przez autora; `set-versions.sh --srv 3.0.4.23 --lib 3.0.4.24 --client 3.1.4.20` (obraz, kompozycje, Helm, `mercury.srv.version` w `mercury-cmd`), pakiet `mercury-install-package-3.0.4.23.POSTGRESQL.20261112.zip` (weryfikacja Ant OK) wgrany do `mercury-docker-packages`, obraz `ibpm/mercury:mercury-hgdb-3.0.4.23` w Nexusie (digest `sha256:eff2fae4…`), smoke jednowęzłowy 0 błędów.
- **Pomiary klastra `devops-box-01`** (`mierz-indeks.py --cpu`, p50 do indeksu węzła): na 3.0.4.22 1 × 100: 271–363 ms, 3 × 100: 356–500 ms; na 3.0.4.23 z pulami 85/25/15 3 × 100: 367–417 ms. Zgodne z 3.0.4.20 (zadanie 232), bez regresji; wyniki w `232-…/TASK.md` (`T22_*.log`, `T23_*.log`).
- **`commons-io` 2.14.0** w `mercury-lib`, `mercury`, `mercury-cmd` (klient już miał; `mercury-client` zamrożony na 1.4).
- **Obs. 164 ✅:** klucz `schema.CaseHeader.isDocumentType` dopisany i przetłumaczony (pl, en, de, es, fr, ko) w `mercury/mercury-ws-app-rest-generator/.../META-INF/mercury` (nie w mercury-lib, jak sugerował wpis).
- **Obs. 163 ✅:** `maxTotal` pul JDBC ustawiany zmiennymi `POSTGRESQL_POOL_MAX_TOTAL`, `POSTGRESQL_POOL_COMMON_MAX_TOTAL`, `POSTGRESQL_POOL_LDAP_MAX_TOTAL` (domyślnie 140/40/20; `context.xml.docker-init`, `mercury-server.sh` z walidacją, `Dockerfile`, README obrazu). Kompozycje: jeden węzeł 140/40/20 przy `max_connections=250`, dwa węzły 120/40/20 i trzy 85/25/15 przy 400 (wartości dobrał autor), komentarze poprawione; `docs/postgresql-max-connections-klaster.md` zaktualizowany.
- **Obs. 162 ✅ (zamknięta bez testu):** migracja PG14 → 17 na Helmie niepotrzebna, bo nie ma instalacji HgDB na Kubernetesie (chart to nowa oferta, startuje na PG17). `pg_upgrade --link` dla dużych baz zostaje otwarty.
- **Dev-server na 3.0.4.22:** strona `/` działa, usługi widoczne (autor).
- **docusaurus-hgdb:** repozytorium sprawdzone (hgdb-229 i hgdb-232 scalone). `PostgreSQL_upgrade`: uwagi o schemacie `public` na PG15+ i o instalacjach bez Dockera, nowa notatka o Kubernetesie; `Database_connections`: zmienne pul i tabela limitów kompozycji; polskie wersje uzupełnione; **nowa strona `Kubernetes_installation` (EN i PL)**: klaster kubeadm, NFS, PV, niedomyślny rejestr (przykład), namespace i instalacja chartu.
- **Testowy klaster Kubernetes** (`k8s-master`, 2 workery, Kubernetes 1.30): dostęp przez `ssh` z cygwin, Helm 3.16.4 w `~/bin`, skrypt `containerd-nexus.sh` (rejestr Nexusa po HTTP; wykonał autor), NFS na masterze (eksport dla 192.168.3.0/24, więc serwer w chartcie = 192.168.3.110), chart `mercury-single-node` na PostgreSQL 17.11 w namespace `mercury-test` (7 podów `Running`, `openapi.json` przez LB 200). Zostaje do testów (decyzja autora).

## Do wiedzy

- **Obs. 165 (nowa):** chart nie pilnuje kolejności startu: `mercury-node1` wstał przed PostgreSQL (`mercury-ws-app` się nie wdrożył, 404), `activemq` i `poi-server-node1` restartowały się; pomaga `rollout restart`. Moja hipoteza o `stdin: true` dla `poi-server` okazała się błędna (po wstaniu zależności działa bez zmian).
- Błąd mojego rozpoznania: węzły k8s mają drugą kartę `ens19` (192.168.3.x); eksport NFS był poprawny, a ja testowałem adres z `ens18`.
- W obrazie jednowęzłowej kompozycji dopisano `max_connections=250`; smoke po tej zmianie nie był puszczany.
- Zapis w dokumentacji „zmienne działają od Mercury 3.0.4.23” zakłada, że ta wersja jest wydana (jest, obraz w Nexusie).
- Logów węzłów `devops-box-01` nie sprawdzono (brak dostępu do kontenerów); endpointy `markGenerationFailed` i `checkManagePrivileges` na dev-serverze nie były wywołane.
- W namespace `mercury-test` jest sekret `nexus-registry` z kontem Nexusa (do usunięcia przy sprzątaniu klastra).
- Hasło `postgres` lokalnego PG17 (i PG13) pojawiło się w rozmowie 2026-11-11, do zmiany.

## Niezacommitowane

- Repozytoria `mercury`, `mercury-lib`, `mercury-cmd`, `hgdb-client-open`, `mercury-client`: tylko `minor_version.txt` (podbicie po wydaniu); `mercury-docker` i `docusaurus-hgdb` czyste (autor zatwierdził zmiany).
- Workspace: `227-…/TASK.md` (ustalenia wstępne) oraz ten plik i `plan-2026-11-13.md`.
