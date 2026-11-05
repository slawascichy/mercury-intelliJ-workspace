# [227] Logowanie i sesje w klastrze (Tomcat Cluster, sticky session)

Status: **założone 2026-11-05**, po zadaniu 211b / po stabilizacji klastra trzywęzłowego na `devops-box-01`.

## Po co

Przy pierwszym uruchomieniu kompozycji trzywęzłowej autor zaproponował sprawdzenie klastra Tomcata
(<https://tomcat.apache.org/tomcat-9.0-doc/cluster-howto.html>) jako mechanizmu logowania w klastrze.

## Do ustalenia

1. Co w Mercury trzyma stan logowania:
   - REST i OAuth: tokeny są w bazie (`MRC_LDAP_OAUTH_*`), więc nie wymagają replikacji sesji (do potwierdzenia w kodzie `OAuthFactory`).
   - GUI (`mercury-gui-core`, strony administracyjne, panele): sesje HTTP; sprawdzić, czy logowanie wygasa przy zmianie węzła.
2. Jak `mercury-lb` (nginx) rozkłada żądania: sticky (`ip_hash`, cookie) czy round-robin.
3. Opcje: (a) sticky session na LB, (b) `SimpleTcpCluster` z `DeltaManager` (multicast zwykle nie działa w sieci Dockera; trzeba `StaticMembership`), (c) sesje w Ehcache/Terracotcie (infrastruktura już jest), (d) brak replikacji i ponowne logowanie przy awarii węzła.
4. Wpływ na Kubernetes (Helm w 211b).

## Wyniki

(do uzupełnienia)
