# [223] Pomiar zapisu sprawy na Linuksie (Tomcat i Terracotta)

Status: **zaplanowane po zadaniu 211** (Aktualizacja obrazów Docker i wydanie). Wyniki porównać z pomiarami z zadania 118.

## Po co

W zadaniu 118 regiony Ehcache zostały przełączone na pamięć klastrową (znaczniki czasu Hibernate, transakcje globalne,
metadane typów). Na środowisku dev (Tomcat na Windowsie) zapis sprawy zwolnił z ok. 90 ms do ok. 190 ms
(`createFolder` w pustym folderze, p50, 35 wywołań). Przyczyną jest opóźnienie klienta Java na Windowsie:
13–15 ms na operację Terracotty. Klient z Linuksa ma 0,3 ms (odczyt) i 0,55–0,9 ms (zapis), więc narzut na Linuksie
szacujemy na 4–6 ms na zapis (**oszacowanie, nie pomiar**). To zadanie ma to zmierzyć na środowisku produkcyjnym.

## Zakres

1. Środowisko: Tomcat z Mercury na Linuksie (obrazy z `mercury-docker` po zadaniu 211) i serwer Terracotta z
   `docker/terracotta` na `devops-box-01.hgdb.org`; baza PostgreSQL testowa. Węzły aplikacji i Terracotta w tej samej sieci.
2. Pomiar opóźnienia Terracotty z węzła aplikacji: `docker run --rm -e TC_URL=terracotta://devops-box-01.hgdb.org:9510/default-server mercury/terracotta:3.6.1 bench`
   (kontener na hoście aplikacji; różni się od pomiaru z 2026-11-03, który był kontener do kontenera na jednym hoście).
3. Pomiar zapisu: `createFolder` (35 wywołań w pustym folderze, p50, p90, max) jak w zadaniu 118 oraz `createDocument` i zapis
   sprawy przez REST.
4. Porównanie A/B (ten sam sprzęt, trzy warianty konfiguracji): (a) regiony klastrowe wg zadania 118, (b) region
   `default-update-timestamps-region` lokalny, (c) pamięć zapytań Hibernate wyłączona (`hibernate.cache.use_query_cache=false`).
   Wariant (c) mierzyć też pod kątem liczby zapytań do bazy (log `org.hibernate.SQL`).
5. Selektywna pamięć współdzielona obiektów spraw: próg `mercury.cache.caseObject.shared.minCostMs` (domyślnie 25 ms,
   na Linuksie rozważyć 5 ms), liczba trafień i chybień, czasy `CaseBusinessRest/find` dla ciężkich spraw (`FSMServiceOrder`).
6. Wynik: tabela i rekomendacja (które regiony zostają klastrowe, wartość progu), wpis w `TASK.md` zadania 118.

## Wejście z zadania 118

- Skrypty i testy: `docker/terracotta` (kompozycja, `bench`), `mercury-srv-slave` (`CacheClusterTest`), `mercury-srv` (`CacheMeasureTest`).
- Pomiary dev (Windows) w `tasks/hgdb/118-…/TASK.md`; analiza pamięci w `analiza-pamieci-klaster.md`.
- Notatka pamięci: opóźnienie Terracotty zależy od klienta (Windows 13–15 ms, Linux 0,3–0,9 ms).
