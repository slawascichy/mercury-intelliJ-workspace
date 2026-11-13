# Prototyp: Tomcat Cluster (replikacja sesji HTTP) + własny authenticator FORM z ochroną przed session fixation

Sprawdzony 2026-11-13 lokalnie na kompozycji trzywęzłowej (obrazy `mercury-hgdb-3.0.4.23`, Tomcat 9.0.123, LB nginx round-robin), bez przebudowy obrazu:
konfigurację i jar wstrzyknięto do kontenerów (`docker cp`) i zrestartowano węzły. Zmiany stałe wymagają zmian w repozytoriach (patrz `TASK.md`).

| Plik | Gdzie | Co |
| --- | --- | --- |
| `server-xml-Cluster-node2.xml` | w `server.xml` Tomcata, wewnątrz `<Engine>` (u nas wstawiony `sed` w szablonie `server.xml.docker-init`, bo init nadpisuje `server.xml` przy każdym starcie) | `SimpleTcpCluster` + `DeltaManager`, `StaticMembershipService` (bez multicastu), `ReplicationValve` **bez filtra `.html`**. Na każdym węźle inna lista `Member` i inny `LocalMember`. `uniqueId` musi mieć 16 bajtów. Hosty `mercury-nodeN` to nazwy usług z kompozycji. |
| (kod w repozytorium `mercury`) | `mercury-gui-core/src/main/java/org/mercury/gui/auth/ClusterFormAuthenticator.java` (jar modułu jest w `common.loader` Tomcata w obrazie: `/opt/mercury-3.0/lib`) | `FormAuthenticator` działający w klastrze przy round-robin; opis w Javadoc klasy |
| `mercury-gui-registry-META-INF-context.xml`, `mercury-ws-app-META-INF-context.xml` | `META-INF/context.xml` aplikacji (źródło: `src/main/webapp/META-INF/context.xml` w `mercury`) | zawierają ten authenticator z `landingPage` aplikacji |
| (zmiana w `web.xml`) | `mercury-gui-registry`, `mercury-ws-app` (i `license-registry`) | `<distributable/>` |
