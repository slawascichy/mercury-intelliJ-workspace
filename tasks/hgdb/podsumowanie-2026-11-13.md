# Podsumowanie 2026-11-13

## Zamknięte i wydane

- **Zadanie 227 (logowanie i sesje w klastrze) ✅:** replikacja sesji HTTP przez Tomcat Cluster (pomysł autora) z własnym `org.mercury.gui.auth.ClusterFormAuthenticator` (`mercury-gui-core`); LB zostaje na round-robin. Sprawdzone lokalnie (trzy węzły): logowanie FORM przez LB 6 z 6, strona po zalogowaniu 36 z 36, zmiana identyfikatora sesji po logowaniu 6 z 6, atak session fixation zablokowany, awaria dwóch z trzech węzłów bez utraty sesji, REST bez zmian. Test na kompozycji na `devops-box-01` wykonał autor: logowanie działa. Odrzucone: `ip_hash` (użytkownicy techniczni z jednego adresu), Redis/Redisson (niestabilny: 0/36, 24/36, 12/36).
- **Zadanie 236 (deadlock przy równoczesnym starcie węzłów) ✅:** rozproszony deadlock baza + HTTP przy tworzeniu katalogu głównego CMIS na świeżej bazie (obserwacja 166). Poprawki: sekretarz indeksu budzony po `commit`, pętla ponawiania z nazwą węzła, który zawiódł, ponawianie dodania folderu głównego do punktu zamontowania. Test A/B z zablokowanym HTTP mastera: transakcja `idle in transaction` 29 s bez poprawki, 0 s z poprawką. Przy okazji poprawiony `NullPointerException` w `Case2CaseBusinessRest/addNodeToMountPoint` (endpoint nigdy nie działał).
- **Wydania:** `mercury` 3.0.4.24 (klaster, `tomcat.version` 9.0.123 w parencie) i 3.0.4.25 (236). Pakiet `mercury-install-package-3.0.4.25.POSTGRESQL.20261113.zip` w `mercury-docker-packages`, obraz `ibpm/mercury:mercury-hgdb-3.0.4.25` w Nexusie (digest `sha256:cd996dafb42e…`). Obrazu 3.0.4.24 nie wysłano (pierwszy opublikowany obraz z klastrem to 3.0.4.25). Pierwszy push przerwała awaria DNS (po restarcie komputera powtórzony bez budowania).
- **Zależności:** `mercury-cmd` `mercury.srv.version` 3.0.4.25, `mercury-docker` (kompozycje, README, chart, `appVersion`) 3.0.4.25, `hgdb-client-open` `mercury.server.version` 3.0.4.25 (`mercury.project.version`, czyli `mercury-lib`, zostaje 3.0.4.24: lib wersjonowany osobno).
- **`mercury-docker`:** przy starcie (`mercury-server.sh`, `initTomcatCluster`) element `Cluster` w `server.xml` i deskryptory kontekstu aplikacji z authenticatorem; zmienne `TOMCAT_CLUSTER_MEMBERS` i `TOMCAT_CLUSTER_PORT`; kompozycje dwu- i trzywęzłowa; start przerywany przy błędnej konfiguracji lub braku klasy (w przeciwnym razie Tomcat uruchomiłby aplikację bez uwierzytelniania).
- **Kubernetes (`mercury-test`):** chart zaktualizowany do 3.0.4.25 (`helm upgrade`), logowanie do GUI przez LB działa; chart jednowęzłowy, replikacja sesji wyłączona. Wcześniej: klaster `k8s-master` (dostęp, NFS, containerd), chart na PostgreSQL 17 (instrukcja na stronie `Kubernetes_installation`).
- **Dokumentacja (docusaurus, PR #4 scalony):** nowa strona `Cluster_sessions` (EN i PL), uwagi w `Kubernetes_installation`, 13 brakujących tagów w `tags.yml`.
- **Obserwacje:** 166 ✅, nowa 167 (klastrowy cache Hibernate w transakcji); wpis 168 (długi start węzła) wycofany jako pomyłka; w wierszu 165 poprawiony format.
- **Wcześniej tego dnia:** obs. 162 zamknięta (migracja na Helm niepotrzebna), 163 ✅ (pule JDBC zmiennymi), 164 ✅ (klucz tłumaczenia), commons-io 2.14.0.

## Do wiedzy

- **Dane predefiniowane:** nie ma reguły „tylko master”. Każdy węzeł ładuje je raz na JVM, a równoległość jest tolerowana przez idempotentność (wyszukiwanie po `username`, zadania 156 i 172); przełącznik `mecrury.loadPredefinedValues.skip` (literówka w nazwie).
- **Ryzyko:** `ClusterFormAuthenticator` zależy od zachowania `FormAuthenticator` z Tomcata 9.0.123 (`doAuthenticateExtended`, „note” `SESSION_ID`); po zmianie wersji Tomcata powtórzyć test logowania przez LB.
- **Zasada pracy (pamięć `nowy-kod-w-galezi-zadania`):** nowy kod tylko w gałęzi zadania; wyjątek wyłącznie na wyraźne polecenie autora (236 w gałęzi `hgdb-227`). Zdarzyło mi się napisać klasę na `master` i poprawiłem to (`checkout -b`).
- **Pomiary:** czas `Server startup` 82–148 s na węzeł, stos `healthy` po 200–245 s; bez punktu odniesienia, więc to nie dowód usterki (obs. 168 wycofana).
- **Sprzątnięte lokalnie:** tagi testowe obrazów 3.0.4.24, dane `D:\mercury-smoke`. Zostaje lokalny obraz pomocniczy `iptables-helper` (Docker) i środowisko testowe `mercury-test` w Kubernetesie (sekret `nexus-registry`).
- **`mercury-lib`:** commons-io 2.14.0 czeka na wydanie (`minor_version.txt` 3.0.4.25); do tego czasu lib 3.0.4.24 w `mercury-cmd` i `hgdb-client-open`.

## Niezacommitowane

- workspace: `227-…/TASK.md`, `236-…/TASK.md`, `docs/obserwacje.md` (166 ✅, 167, 168 wycofana, format 165), `docs/moduly/mercury-docker.md`, `mercury.md`, `architektura.md`, `hgdb-client-open.md`, ten plik, `plan-2026-11-13.md` (oznaczenia), `plan-2026-11-16.md`.
- Repozytoria z kodem są czyste (po rytuale). Do usunięcia przez autora: zdalna gałąź `origin/hgdb-227` w `docusaurus-hgdb`.
