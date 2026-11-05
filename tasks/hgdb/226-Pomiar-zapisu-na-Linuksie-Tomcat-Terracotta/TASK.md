# [226] Pomiar zapisu sprawy na Linuksie (Tomcat i Terracotta)

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

## Przygotowanie pomiaru (2026-11-05)

**Środowisko.** Klaster trzywęzłowy na `devops-box-01` (Linux), uruchomiony i sprawdzony przez autora na obrazach 3.0.4.14: węzły `:28080`, `:28081`, `:28082`, LB `https://…:1443`. Ta maszyna ma do nich dostęp sieciowy (odczyt przez REST działa). Odczyt `TypeCodeRest/findAll` z maszyny roboczej do węzła: p50 ok. 20 ms na wywołanie (n = 12 na węzeł, min 17–18, max 35–45), więc to jest tło sieciowe pomiarów zdalnych. Najczystszy pomiar jest z samego hosta serwera.

**Narzędzie:** `mierz-zapis.sh` (w tym folderze). CMIS Browser Binding, jedno żądanie naraz: odczyt folderu (czas odniesienia), `createFolder` i `createDocument` w własnym folderze `Perf226-<czas>`, rozgrzewka (domyślnie 5), `N` pomiarów (domyślnie 35 jak w 118), wynik p50/p90/max i wiersze do tabeli, na końcu `deleteTree` (chyba że `KEEP=1`). Sprawdzony lokalnie na pojedynczym węźle (Docker Desktop, Windows; nie jest to wynik do porównań). Użycie:
```bash
CMIS_USER=admin:<hasło> CMIS_BASE=http://127.0.0.1:8080/mercury-ws-app/browser/documents N=35 LABEL=A-regiony-klastrowe ./mierz-zapis.sh
```

**Warunek: klient OAuth dla CMIS.** W obrazie Docker CMIS odrzuca wszystko (HTTP 401, także `/browser` i Bearer), bo `mercury.properties` ma zakomentowane `mercury.cmis.security.oauthClientId` i `oauthClientSecret` (weryfikacja Basic idzie przez realm klienta OAuth). Plik jest nadpisywany z szablonu w obrazie przy każdym starcie kontenera. Na czas pomiaru podstaw własny szablon przez bind-mount (sprawdzone lokalnie, po tym `admin:admin` daje HTTP 200):
```bash
# szablon z tego samego obrazu, z odkomentowanym klientem (sekret z tabeli MRC_LDAP_OAUTH_CONFIG, nie z repozytorium)
docker run --rm --entrypoint cat nexus.scisoftware.local:5000/ibpm/mercury:mercury-hgdb-3.0.4.14 \
  /opt/mercury-3.0/docker-init-config/config/mercury.properties \
  | sed "s|^#mercury.cmis.security.oauthClientId=.*|mercury.cmis.security.oauthClientId=GIUSoapUIClient|; s|^#mercury.cmis.security.oauthClientSecret=.*|mercury.cmis.security.oauthClientSecret=$CLIENT_SECRET|" > mercury.properties.cmis
# docker-compose.override.yml (dla każdego węzła aplikacji):
#   services:
#     mercury-node1:
#       volumes:
#         - ./mercury.properties.cmis:/opt/mercury-3.0/docker-init-config/config/mercury.properties:ro
docker compose up -d --force-recreate mercury-node1
```
**Trwała poprawka (obserwacja 152, 2026-11-05):** obraz `ibpm/mercury:mercury-hgdb-3.0.4.14` (nowy digest `sha256:f4068343…`) czyta zmienne `CMIS_OAUTH_CLIENT_ID` i `CMIS_OAUTH_CLIENT_SECRET`; bez obu CMIS Basic zostaje wyłączone. Zamiast bind-mountu wystarczy dopisać je do `.env` (id: `GIUSoapUIClient`; sekret z tabeli `MRC_LDAP_OAUTH_CONFIG`) i zrobić `docker compose pull` oraz `up -d --force-recreate` węzłów. Kompozycje przekazują obie zmienne do węzłów aplikacji.

## Warianty A/B (ten sam klaster i klient, po jednym restarcie węzłów)

| Wariant | Co zmienić | Jak |
|---|---|---|
| A | regiony klastrowe wg 118 (stan obecny obrazów) | bez zmian |
| B | `default-update-timestamps-region` lokalny (bez `clustered-dedicated`) | własny `ehcacheDefault.xml` przez bind-mount na `/opt/mercury-3.0/docker-init-config/config/ehcacheDefault.xml`, region bez `terracotta:clustered-dedicated` i bez `clustered-store`; ta sama zmiana na wszystkich węzłach |
| C | pamięć zapytań Hibernate wyłączona (`hibernate.cache.use_query_cache=false`) | parametr jest w `database-*.properties` w `mercury-entities-ids` (zmienna `${hibernate.cache.use_query_cache}` w `dao-context.xml`); czy wystarczy `-D` w `CATALINA_OPTS`, trzeba sprawdzić (przypuszczenie: Spring bierze właściwości z pliku przed systemowymi) |

Dla każdego wariantu: `mierz-zapis.sh` na węźle 1 po rozgrzewce klastra, potem jeszcze raz na węźle 2 (ruch między węzłami), a w wariancie C dodatkowo liczba zapytań w logu `org.hibernate.SQL`.

## Wyniki

### Wariant A: regiony klastrowe wg 118, pomiar zdalny (2026-11-05)

Klaster trzywęzłowy na `devops-box-01` (Linux, obrazy 3.0.4.14 z wzorcami Ehcache po zadaniu 118), klient: maszyna robocza autora na tej samej sieci (zdalny pomiar, bo użytkownicy będą korzystać z serwera z maszyn klienckich; decyzja autora). CMIS Browser Binding, Basic, jedno żądanie naraz, 35 pomiarów po 5 rozgrzewkowych, ms:

| węzeł | operacja | n | min | p50 | p90 | max |
|---|---|---|---|---|---|---|
| node1 (:28080) | read (odniesienie) | 35 | 19 | 21 | 28 | 42 |
| node1 (:28080) | createFolder | 35 | 95 | 99 | 105 | 123 |
| node2 (:28081) | read | 35 | 21 | 23 | 40 | 55 |
| node2 (:28081) | createFolder | 35 | 95 | 102 | 113 | 130 |
| node3 (:28082) | read | 35 | 20 | 23 | 43 | 49 |
| node3 (:28082) | createFolder | 35 | 97 | 103 | 117 | 129 |
| node1, drugi przebieg | read | 35 | 20 | 23 | 45 | 47 |
| node1, drugi przebieg | createFolder | 35 | 95 | 99 | 114 | 123 |

Wnioski (z zastrzeżeniami): `createFolder` p50 to ok. 100 ms na każdym z trzech węzłów i powtarza się między przebiegami (p50 99 i 99 ms na node1), a odczyt kosztuje ok. 22 ms (HTTP, uwierzytelnianie i sieć). Narzut zapisu ponad odczyt to więc ok. 75–80 ms. W 118 na Windowsie (localhost, inny sprzęt) `createFolder` trwał 189 ms z regionami klastrowymi i 90 ms z lokalnymi; Linux z klastrowymi regionami (ok. 100 ms) jest zatem wyraźnie bliżej wartości z lokalnymi pamięciami niż z klastrowymi na Windowsie. **To jeszcze nie jest porównanie A/B**: brakuje wariantu B (lokalny region znaczników czasu) i C na tym samym klastrze i sprzęcie, więc nie wiemy, ile z tych ok. 100 ms to koszt Terracotty. Różnice między węzłami są w granicach rozrzutu.

**`createDocument` nie działa na tym klastrze (HTTP 500, `Cannot store the content … FileNotFoundException`).** Przyczyna: katalog `/opt/mercury-3.0/upload` w obrazie należał do `root` (powstawał dopiero przez `VOLUME`, po `chown`), a serwer działa jako `mercury` (UID 1000); dodatkowo katalog hosta podmontowany do `mercury-upload-*` musi mieć właściciela UID 1000. Poprawka w Dockerfile (katalog tworzony przed `chown`) w obserwacji 153. Do czasu aktualizacji obrazu i `sudo chown -R 1000:1000` na katalogach `mercury-upload-*` (i `mercury-lucene-*`, `poi-server-*`) mierzone są tylko `read` i `createFolder` (`OPS="read createFolder"`).
