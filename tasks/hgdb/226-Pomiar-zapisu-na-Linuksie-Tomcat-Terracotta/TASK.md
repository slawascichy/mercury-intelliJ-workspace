# [226] Pomiar zapisu sprawy na Linuksie (Tomcat i Terracotta)

Status: **zamknięte 2026-11-05** (pomiary wykonane na klastrze trzywęzłowym na `devops-box-01`; wnioski i zadania wynikające: sekcja „Podsumowanie i wnioski” na końcu). Wyniki porównane z pomiarami z zadania 118.

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

#### Wariant A po aktualizacji do obrazów 3.0.4.15 (2026-11-05, ten sam klaster i klient)

Obrazy 3.0.4.15 mają poprawiony katalog `upload` (własność `mercury`), więc `createDocument` już działa (HTTP 200). Ten sam sposób pomiaru, ms:

| węzeł | operacja | n | min | p50 | p90 | max |
|---|---|---|---|---|---|---|
| node1 (:28080) | read | 35 | 25 | 29 | 48 | 60 |
| node1 | createFolder | 35 | 109 | 129 | 157 | 246 |
| node1 | createDocument | 35 | 105 | 122 | 156 | 180 |
| node2 (:28081) | read | 35 | 21 | 24 | 42 | 48 |
| node2 | createFolder | 35 | 102 | 126 | 170 | 234 |
| node2 | createDocument | 35 | 100 | 134 | 174 | 195 |
| node3 (:28082) | read | 35 | 22 | 28 | 43 | 57 |
| node3 | createFolder | 35 | 101 | 130 | 165 | 200 |
| node3 | createDocument | 35 | 102 | 117 | 156 | 431 |

Wnioski: `createDocument` kosztuje tyle co `createFolder` (p50 ok. 117–134 ms wobec 126–130 ms), czyli zapis dokumentu z małą treścią nie dokłada zauważalnego czasu. `createFolder` jest o ok. 25–30 ms wolniejszy niż w pierwszym przebiegu na 3.0.4.14 (p50 ok. 100 ms), a odczyt też (ok. 29 wobec 22 ms), więc część różnicy to inne obciążenie sieci i serwera, a nie nowy obraz (przypuszczenie; nie sprawdzone). Nadal brakuje wariantów B i C, by oddzielić koszt Terracotty.

#### Wariant B: lokalny `default-update-timestamps-region` (2026-11-05, ten sam klaster i klient)

Konfiguracja z `warianty/B` (podmontowany `ehcacheDefault.xml`, wszystkie trzy węzły), postawiona przez autora; ten sam sposób pomiaru jak w A, ms:

| węzeł | operacja | n | min | p50 | p90 | max |
|---|---|---|---|---|---|---|
| node1 (:28080) | read | 35 | 22 | 24 | 45 | 56 |
| node1 | createFolder | 35 | 97 | 117 | 143 | 178 |
| node1 | createDocument | 35 | 94 | 107 | 148 | 841 |
| node2 (:28081) | read | 35 | 20 | 23 | 41 | 65 |
| node2 | createFolder | 35 | 89 | 104 | 142 | 160 |
| node2 | createDocument | 35 | 90 | 101 | 132 | 358 |
| node3 (:28082) | read | 35 | 21 | 24 | 42 | 52 |
| node3 | createFolder | 35 | 93 | 111 | 154 | 161 |
| node3 | createDocument | 35 | 91 | 109 | 139 | 154 |

Porównanie p50 A → B: `createFolder` 129/126/130 → 117/104/111 ms (o ok. 12–22 ms mniej), `createDocument` 122/134/117 → 107/101/109 ms (o ok. 8–33 ms mniej), odczyt bez zmiany (24–29 → 23–24 ms). Lokalny region znaczników czasu skraca więc zapis o ok. 10–20 ms (ok. 10–15%), czyli większość z ok. 100 ms zapisu nie pochodzi z tego regionu. Zastrzeżenia: jeden przebieg na węzeł, rozrzut między przebiegami A (node1: p50 99 i 129 ms w dwóch przebiegach) jest podobnego rzędu, a stan węzłów w B zakładam za autorem (konfiguracji w kontenerach nie sprawdzałem). Odczyt jest stabilny, więc różnica w zapisie jest prawdopodobna, ale wymaga potwierdzenia powtórnym przebiegiem A i B.

#### Wariant B, drugi przebieg (2026-11-05, kilka minut po pierwszym, ta sama konfiguracja)

Plan autora: po dwa przebiegi na wariant (B, potem C, potem A), by ocenić rozrzut przed porównaniem. ms:

| węzeł | operacja | n | min | p50 | p90 | max |
|---|---|---|---|---|---|---|
| node1 | read | 35 | 18 | 20 | 32 | 43 |
| node1 | createFolder | 35 | 86 | 93 | 137 | 153 |
| node1 | createDocument | 35 | 90 | 102 | 130 | 149 |
| node2 | read | 35 | 17 | 19 | 36 | 61 |
| node2 | createFolder | 35 | 84 | 100 | 119 | 160 |
| node2 | createDocument | 35 | 87 | 105 | 124 | 136 |
| node3 | read | 35 | 18 | 21 | 39 | 45 |
| node3 | createFolder | 35 | 86 | 107 | 129 | 148 |
| node3 | createDocument | 35 | 90 | 101 | 139 | 151 |

Drugi przebieg B jest o ok. 4–24 ms szybszy w `createFolder` (p50 93/100/107 wobec 117/104/111 ms), a odczyt też spadł (19–21 wobec 23–24 ms). Różnica między przebiegami B jest więc porównywalna z różnicą A→B, co potwierdza obawę o rozrzut w czasie (tło sieci i serwera). Odczyt (czas odniesienia) pomaga to skorygować: różnica `createFolder − read` p50 to w B1 93/81/87 ms, w B2 73/81/86 ms.

#### Wariant C: pamięć zapytań Hibernate wyłączona (2026-11-05, dwa przebiegi jeden po drugim)

Konfiguracja z `warianty/C` (`hibernate.cache.use_query_cache=false`), postawiona przez autora na wszystkich węzłach. Przebieg 1 i 2: kolejno node1, node2, node3. ms:

| przebieg | węzeł | operacja | n | min | p50 | p90 | max |
|---|---|---|---|---|---|---|---|
| C1 | node1 | read | 35 | 22 | 27 | 48 | 52 |
| C1 | node1 | createFolder | 35 | 93 | 116 | 166 | 248 |
| C1 | node1 | createDocument | 35 | 91 | 112 | 143 | 166 |
| C1 | node2 | read | 35 | 20 | 23 | 40 | 56 |
| C1 | node2 | createFolder | 35 | 90 | 108 | 148 | 191 |
| C1 | node2 | createDocument | 35 | 89 | 107 | 152 | 286 |
| C1 | node3 | read | 35 | 21 | 25 | 44 | 72 |
| C1 | node3 | createFolder | 35 | 97 | 117 | 154 | 166 |
| C1 | node3 | createDocument | 35 | 91 | 123 | 166 | 399 |
| C2 | node1 | read | 35 | 17 | 20 | 36 | 48 |
| C2 | node1 | createFolder | 35 | 86 | 100 | 145 | 157 |
| C2 | node1 | createDocument | brak | | | | | (żądanie nr 40: HTTP 000 po stronie klienta, mimo odpowiedzi serwera; operację pominięto, patrz C2b) |
| C2 | node2 | read | 35 | 18 | 20 | 44 | 53 |
| C2 | node2 | createFolder | 35 | 85 | 99 | 121 | 134 |
| C2 | node2 | createDocument | 35 | 91 | 123 | 164 | 176 |
| C2 | node3 | read | 35 | 18 | 21 | 38 | 50 |
| C2 | node3 | createFolder | 35 | 87 | 100 | 133 | 145 |
| C2 | node3 | createDocument | 35 | 93 | 103 | 135 | 154 |
| C2b (powtórka node1) | node1 | read | 35 | 18 | 21 | 34 | 44 |
| C2b | node1 | createFolder | 35 | 85 | 96 | 123 | 142 |
| C2b | node1 | createDocument | 35 | 87 | 106 | 128 | 148 |

Odczyt (odniesienie) w C1 to 23–27 ms, w C2 19–21 ms: tło spadło między przebiegami tak samo jak w B. Porównanie wariantów po przebiegach A.

#### Wariant A, dwa przebiegi (2026-11-05, klaster ponownie w wariancie A)

Ta sama kolejność co w B i C (node1, node2, node3; dwa przebiegi jeden po drugim). Dwie operacje wypadły przez błąd klienta (HTTP 000, patrz niżej) i powtórzono je osobno (A1b, A2b). ms:

| przebieg | węzeł | operacja | n | min | p50 | p90 | max |
|---|---|---|---|---|---|---|---|
| A1 | node1 | read | 35 | 23 | 26 | 40 | 50 |
| A1 | node1 | createFolder | brak (żądanie 22: HTTP 000) | | | | |
| A1b | node1 | read | 35 | 19 | 21 | 35 | 44 |
| A1b | node1 | createFolder | 35 | 95 | 107 | 134 | 156 |
| A1 | node1 | createDocument | 35 | 109 | 120 | 162 | 251 |
| A1 | node2 | read | 35 | 22 | 26 | 47 | 55 |
| A1 | node2 | createFolder | 35 | 102 | 126 | 186 | 543 |
| A1 | node2 | createDocument | 35 | 99 | 118 | 140 | 471 |
| A1 | node3 | read | 35 | 22 | 26 | 37 | 55 |
| A1 | node3 | createFolder | 35 | 101 | 115 | 145 | 237 |
| A1 | node3 | createDocument | 35 | 105 | 121 | 156 | 245 |
| A2 | node1 | read | 35 | 18 | 22 | 31 | 50 |
| A2 | node1 | createFolder | 35 | 93 | 108 | 133 | 160 |
| A2 | node1 | createDocument | 35 | 100 | 107 | 127 | 151 |
| A2 | node2 | read | 35 | 19 | 21 | 34 | 62 |
| A2 | node2 | createFolder | 35 | 91 | 107 | 147 | 192 |
| A2 | node2 | createDocument | brak (żądanie 9: HTTP 000) | | | | |
| A2b | node2 | read | 35 | 18 | 21 | 40 | 59 |
| A2b | node2 | createDocument | 35 | 95 | 107 | 143 | 178 |
| A2 | node3 | read | 35 | 19 | 22 | 45 | 55 |
| A2 | node3 | createFolder | 35 | 96 | 109 | 137 | 160 |
| A2 | node3 | createDocument | 35 | 99 | 120 | 162 | 186 |

### Porównanie wariantów A, B, C (p50 uśredniony po trzech węzłach, ms)

Dla B i C wartości z tabel wyżej (dla C node1 w C2: createFolder z C2, createDocument z C2b). „Netto” to zapis minus odczyt tego samego przebiegu (usuwa zmiany tła sieci i serwera).

| wariant | przebieg | read | createFolder | netto createFolder | createDocument | netto createDocument |
|---|---|---|---|---|---|---|
| A | 1 | 26,0 | 116,0 | 90 | 119,7 | 94 |
| A | 2 | 21,7 | 108,0 | 86 | 111,3 | 90 |
| B (lokalny update-timestamps) | 1 | 23,7 | 110,7 | 87 | 105,7 | 82 |
| B | 2 | 19,7 | 100,0 | 80 | 102,7 | 83 |
| C (bez pamięci zapytań) | 1 | 25,0 | 113,7 | 89 | 114,0 | 89 |
| C | 2 | 20,3 | 99,7 | 79 | 110,7 | 90 |

**Wnioski.**
1. Rozrzut między przebiegami tej samej konfiguracji (ok. 8–16 ms bezwzględnie, ok. 4–11 ms po odjęciu odczytu) jest porównywalny z różnicami między wariantami (ok. 3–10 ms netto). Pierwszy przebieg jest w każdym wariancie wolniejszy o ok. 4–5 ms na odczycie, więc przebiegi trzeba porównywać parami (1 z 1, 2 z 2).
2. Netto `createFolder` to ok. 79–90 ms w każdym wariancie: B zyskuje względem A 3–6 ms, C 1–7 ms. To mieści się w rozrzucie. `createDocument` netto: A 90–94, B 82–83, C 89–90 ms; B jest o ok. 8–11 ms lepszy, ale to jedna obserwacja na przebieg.
3. Żaden z wariantów nie usuwa głównego składnika kosztu zapisu (ok. 80 ms ponad odczyt). Terracotta (klastrowy region znaczników czasu) oraz pamięć zapytań Hibernate nie tłumaczą go w większości. Przypuszczenie: dominuje baza (kilka INSERT/UPDATE i commit), uwierzytelnianie i bufor Lucene; trzeba to sprawdzić osobnym pomiarem (czas po stronie serwera, log `org.hibernate.SQL`, liczba zapytań), nie jest to ustalone tym pomiarem.
4. Rekomendacja robocza: nie rezygnować z klastrowych regionów dla niewielkiego zysku (3–10 ms), zwłaszcza że wariant B bez klastrowych znaczników czasu psuje unieważnianie pamięci zapytań między węzłami, a C wyłącza pamięć zapytań. Warto natomiast prześledzić, skąd bierze się ok. 80 ms.

**Błąd klienta `HTTP 000`.** W tej serii trzy razy (C2 node1 `createDocument` nr 40, A1 node1 `createFolder` nr 22, A2 node2 `createDocument` nr 9) curl zwrócił kod 000 mimo pełnej odpowiedzi serwera z obiektem; skrypt pomija wtedy całą operację. Częstość: 3 z ok. 1000 żądań. Przypuszczenie: zamknięte połączenie utrzymane (keep-alive) lub zerwanie po stronie klienta/sieci; nie badane. Skrypt można poprawić, by liczył taki wynik jako błąd klienta i tylko go pomijał (zamiast całej operacji).

### Etap 2: „duża” sprawa FSMServiceOrder przez REST (2026-11-05)

Dane: `dataset.zip` z zadania 116 załadowany do `mercury-db-test` (DatasetScenario z `-Dtest.keep.dataset=true`), potem przeniesiony do klastra narzędziem `mercury-transfer` (źródło: lokalny Tomcat na `mercury-db-test`, cel: node2). Przeniesiono definicje `FSMServiceOrder` z podtypami i 26 spraw; w klastrze `FSMServiceOrder.2699` (27 właściwości, zagnieżdżone obiekty, odpowiedź `find` ok. 16 KB). Narzędzie: `mierz-sprawe.sh` (REST z tokenem OAuth `GIUSoapUIClient`): `find` (domyślne pamięci), `find` z `cacheUsage=REFRESH`, `save` tej samej sprawy z inną wartością pola `description` (nowa wersja). Jedno żądanie naraz, 35 pomiarów po 5 rozgrzewkowych, klient zdalny jak w etapie 1.

Uwagi do przeniesienia danych (narzędzie `mercury-transfer` w mercury-cmd wymaga poprawek, nie zmieniano repozytorium; obejścia w scratchpadzie): (1) `transfer-remote-context.xml` ma starą nazwę klasy `pro.ibpm.mercury.cmd.config.CmdSpringPropertiesUtil` (jest `org.mercury.cmd.config…`); (2) w konfiguracji brakuje `mercury.ws.service.list=source,target`; (3) `TransferAction.transferMetadata` kończy się NPE dla podtypu bez definicji w źródle (zestaw 116 ma 6 takich: `FsmDeviceSpecification`, `FsmIdentifier`, `FsmAdditionalActivity`, `FsmDiagnosticParameter`, `FsmAcceptanceProtocolDevice`, `FsmAcceptanceProtocolService`).

#### Wariant A (2 przebiegi, ms)

| przebieg | węzeł | operacja | n | min | p50 | p90 | max |
|---|---|---|---|---|---|---|---|
| A1 | node1 | find | 35 | 18 | 20 | 27 | 33 |
| A1 | node1 | find REFRESH | 35 | 20 | 23 | 40 | 58 |
| A1 | node1 | save | 35 | 69 | 72 | 88 | 101 |
| A1 | node2 | find | 35 | 18 | 22 | 43 | 55 |
| A1 | node2 | find REFRESH | 35 | 19 | 22 | 41 | 55 |
| A1 | node2 | save | 35 | 67 | 70 | 90 | 95 |
| A1 | node3 | find | 35 | 19 | 21 | 42 | 49 |
| A1 | node3 | find REFRESH | 35 | 20 | 23 | 44 | 48 |
| A1 | node3 | save | 35 | 69 | 74 | 97 | 101 |
| A2 | node1 | find | 35 | 18 | 20 | 22 | 26 |
| A2 | node1 | find REFRESH | 35 | 20 | 21 | 39 | 55 |
| A2 | node1 | save | 35 | 68 | 72 | 89 | 101 |
| A2 | node2 | find | 35 | 19 | 23 | 45 | 47 |
| A2 | node2 | find REFRESH | 35 | 20 | 22 | 37 | 51 |
| A2 | node2 | save | 35 | 67 | 70 | 88 | 93 |
| A2 | node3 | find | 35 | 19 | 22 | 41 | 48 |
| A2 | node3 | find REFRESH | 35 | 21 | 23 | 41 | 51 |
| A2 | node3 | save | 35 | 68 | 72 | 96 | 100 |

Spostrzeżenia: dwa przebiegi zgadzają się (p50 `save` 70–74 ms, `find` 20–23 ms), więc ten pomiar ma mały rozrzut, mniejszy niż CMIS w etapie 1. `find` tej sprawy kosztuje tyle co odczyt folderu CMIS (ok. 20–22 ms, czyli poziom sieci); `find` z `REFRESH` jest tylko o 1–3 ms wolniejszy, więc ta sprawa jest za „tania”, by pamięć współdzielona była widoczna (przypuszczenie: odczyt z bazy trwa kilka ms). `save` sprawy to ok. 50 ms ponad odczyt, mniej niż `createFolder` w CMIS (ok. 80 ms ponad odczyt). Wariant B i C do zmierzenia po przestawieniu klastra.

#### Wariant B (2 przebiegi, ms)

| przebieg | węzeł | operacja | n | min | p50 | p90 | max |
|---|---|---|---|---|---|---|---|
| B1 | node1 | find | 35 | 20 | 22 | 43 | 59 |
| B1 | node1 | find REFRESH | 35 | 22 | 25 | 44 | 51 |
| B1 | node1 | save | 35 | 74 | 79 | 92 | 106 |
| B1 | node2 | find | 35 | 20 | 23 | 40 | 46 |
| B1 | node2 | find REFRESH | 35 | 22 | 25 | 46 | 62 |
| B1 | node2 | save | 35 | 70 | 78 | 96 | 102 |
| B1 | node3 | find | 35 | 19 | 23 | 45 | 51 |
| B1 | node3 | find REFRESH | 35 | 22 | 26 | 50 | 61 |
| B1 | node3 | save | 35 | 73 | 80 | 102 | 133 |
| B2 | node1 | find | 35 | 19 | 22 | 38 | 47 |
| B2 | node1 | find REFRESH | 35 | 21 | 24 | 35 | 46 |
| B2 | node1 | save | 35 | 71 | 75 | 87 | 96 |
| B2 | node2 | find | 35 | 20 | 22 | 40 | 47 |
| B2 | node2 | find REFRESH | 35 | 21 | 23 | 41 | 51 |
| B2 | node2 | save | 35 | 69 | 73 | 91 | 102 |
| B2 | node3 | find | 35 | 19 | 21 | 34 | 57 |
| B2 | node3 | find REFRESH | 35 | 21 | 23 | 43 | 54 |
| B2 | node3 | save | 35 | 71 | 75 | 96 | 106 |

Spostrzeżenia: w B `save` jest wolniejszy niż w A o ok. 3–10 ms (p50 B1 78–80 i B2 73–75 wobec A 70–74), `find` o ok. 1–2 ms (22–23 wobec 20–23). Kierunek jest przeciwny niż w CMIS (tam B był o 10–20 ms szybszy), więc lokalny region znaczników czasu nie daje stałego zysku; różnice są rzędu rozrzutu między przebiegami (B1 → B2: ok. 3–5 ms).

#### Wariant C (2 przebiegi, ms)

| przebieg | węzeł | operacja | n | min | p50 | p90 | max |
|---|---|---|---|---|---|---|---|
| C1 | node1 | find | 35 | 20 | 22 | 45 | 51 |
| C1 | node1 | find REFRESH | 35 | 22 | 24 | 41 | 49 |
| C1 | node1 | save | 35 | 73 | 77 | 96 | 110 |
| C1 | node2 | find | 35 | 20 | 24 | 43 | 48 |
| C1 | node2 | find REFRESH | 35 | 22 | 25 | 40 | 44 |
| C1 | node2 | save | 35 | 70 | 80 | 98 | 103 |
| C1 | node3 | find | 35 | 20 | 23 | 38 | 47 |
| C1 | node3 | find REFRESH | 34 (żądanie 35: HTTP 000 po stronie klienta) | 22 | 26 | 46 | 66 |
| C1 | node3 | save | 35 | 72 | 78 | 95 | 106 |
| C2 | node1 | find | 35 | 19 | 22 | 43 | 54 |
| C2 | node1 | find REFRESH | 35 | 21 | 23 | 40 | 47 |
| C2 | node1 | save | 35 | 71 | 75 | 94 | 99 |
| C2 | node2 | find | 35 | 19 | 21 | 34 | 46 |
| C2 | node2 | find REFRESH | 35 | 21 | 23 | 45 | 47 |
| C2 | node2 | save | 35 | 69 | 72 | 88 | 106 |
| C2 | node3 | find | 35 | 19 | 21 | 41 | 47 |
| C2 | node3 | find REFRESH | 35 | 21 | 24 | 46 | 54 |
| C2 | node3 | save | 35 | 70 | 73 | 89 | 94 |

#### Porównanie A, B, C dla sprawy FSMServiceOrder (p50 uśredniony po węzłach, ms)

| wariant | przebieg | find | find REFRESH | save |
|---|---|---|---|---|
| A | 1 | 21,0 | 22,7 | 72,0 |
| A | 2 | 21,7 | 22,0 | 71,3 |
| B | 1 | 22,7 | 25,3 | 79,0 |
| B | 2 | 21,7 | 23,3 | 74,3 |
| C | 1 | 23,0 | 25,0 | 78,3 |
| C | 2 | 21,3 | 23,3 | 73,3 |

Wniosek (pomiar klienta REST, zapis i odczyt przez jeden węzeł): w żadnym wariancie nie ma zysku względem A; B i C są w pierwszym przebiegu o 6–7 ms wolniejsze, w drugim o 2–3 ms (w granicach rozrzutu). **Ten pomiar nie sprawdza jednak zysku z przekazywania zmian między węzłami (bufor dokumentów Lucene, zdarzenia o zmianie kolejki), patrz niżej.**

### Etap 3: propagacja zmiany do indeksów Lucene węzłów (2026-11-05)

Pomiar z etapu 2 (`save` przez jeden węzeł) nie obejmuje tego, co robi mapper (Case → dokument Lucene) i przekazywanie dokumentów między węzłami: `CaseMapperShared` (bufor gotowych dokumentów, region `luceneDocument.shared`), a zysk z niego widać tylko na węzłach, które odbierają paczkę. Dlatego `mierz-indeks.py` wstawia nową sprawę (kopia `FSMServiceOrder.2699` bez identyfikatorów) na node2 i mierzy, po ilu ms od końca odpowiedzi na zapis sprawa pojawia się w lokalnym indeksie Lucene każdego z trzech węzłów (`searchByLuceneId`, odpytywanie bez przerwy). Każdy węzeł ma własny indeks. 35 wstawień po 5 rozgrzewkowych, nowe sprawy usuwane na końcu. Rozdzielczość: ok. 20–25 ms (czas jednego żądania).

Warianty mające sens dla mappera: **M1** = przekazywanie dokumentów włączone (stan domyślny; `CaseMapperShared` klastrowy) i **M0** = `mercury.cache.luceneDocument.shared.enabled=false` (`warianty/M0`: szablon `mercury.properties` z jedną dodatkową linią, każdy węzeł mapuje sam). Warianty B i C z etapów 1–2 nie dotyczą mappera, więc ich tu nie powtarzamy.

Wynik wstępny dla M1 (przekazywanie włączone) na klastrze w konfiguracji C (C nie dotyczy mappera, ale to nie jest czysta konfiguracja domyślna), ms, zapis na node2:

| przebieg | węzeł | n | min | p50 | p90 | max |
|---|---|---|---|---|---|---|
| Cw1 | node1 | 35 | 1084 | 1111 | 1159 | 1175 |
| Cw1 | node2 (zapis) | 35 | 1009 | 1023 | 1037 | 1048 |
| Cw1 | node3 | 35 | 1084 | 1107 | 1163 | 1196 |
| Cw2 | node1 | 35 | 1093 | 1109 | 1150 | 1171 |
| Cw2 | node2 (zapis) | 35 | 1004 | 1020 | 1041 | 1060 |
| Cw2 | node3 | 35 | 1087 | 1102 | 1155 | 1169 |

Spostrzeżenia: wszystkie trzy indeksy są aktualne po ok. 1,0–1,2 s, bardzo powtarzalnie (rozrzut między przebiegami do 10 ms). Ponad 1 s to prawdopodobnie cykl pracy sekretarza indeksu (przypuszczenie, nie zweryfikowane w kodzie), więc to on wyznacza dolną granicę; węzły odbierające są ok. 85 ms za węzłem zapisującym (p50 1102–1111 wobec 1020–1023 ms). Różnicę M1 → M0 będzie widać w tych ok. 85 ms (odbiorcy muszą sami zmapować sprawę zamiast pobrać gotowy dokument).

#### Wariant M0 (przekazywanie dokumentów wyłączone: pliki z `warianty/M0`), zapis na node2, ms

| przebieg | węzeł | n | min | p50 | p90 | max |
|---|---|---|---|---|---|---|
| M0w1 | node1 | 35 | 1068 | 1112 | 1153 | 1222 |
| M0w1 | node2 (zapis) | 35 | 1058 | 1097 | 1150 | 1171 |
| M0w1 | node3 | 35 | 1068 | 1110 | 1148 | 1213 |
| M0w2 | node1 | 35 | 1056 | 1088 | 1135 | 1287 |
| M0w2 | node2 (zapis) | 35 | 1054 | 1088 | 1137 | 1281 |
| M0w2 | node3 | 35 | 1054 | 1085 | 1132 | 1283 |

Spostrzeżenia: p50 1085–1112 ms na wszystkich węzłach, w przebiegu 2 praktycznie jednakowo (różnice do 3 ms); węzeł zapisujący (node2, MASTER) nie wyprzedza pozostałych. Uwaga: pierwotnie ta seria była błędnie nazwana M1 (nieporozumienie w oznaczeniach); to jest M0. Wynik wstępny „Cw” wyżej to wariant M1 (przekazywanie włączone) zmierzony na klastrze w konfiguracji C, więc nie jest czystym M1; czysty M1 (konfiguracja domyślna) do zmierzenia.

#### Wariant M1 czysty (konfiguracja domyślna, przekazywanie włączone), zapis na node2 (MASTER), ms

| przebieg | węzeł | n | min | p50 | p90 | max |
|---|---|---|---|---|---|---|
| M1c1 | node1 | 35 | 1093 | 1135 | 1176 | 1356 |
| M1c1 | node2 (zapis) | 35 | 1023 | 1035 | 1062 | 1110 |
| M1c1 | node3 | 35 | 1108 | 1131 | 1170 | 1351 |
| M1c2 | node1 | 35 | 1106 | 1119 | 1172 | 1339 |
| M1c2 | node2 (zapis) | 35 | 1012 | 1026 | 1054 | 1104 |
| M1c2 | node3 | 35 | 1098 | 1112 | 1170 | 1349 |

#### Porównanie M1 (przekazywanie włączone) i M0 (wyłączone), p50 w ms (przebieg 1 / 2)

| węzeł | M1 | M0 | M1 − M0 |
|---|---|---|---|
| node2 (zapis, MASTER) | 1035 / 1026 | 1097 / 1088 | ok. −62 |
| node1 | 1135 / 1119 | 1112 / 1088 | ok. +27 |
| node3 | 1131 / 1112 | 1110 / 1085 | ok. +24 |

Wniosek (dla sprawy FSMServiceOrder.2699, wstawianej pojedynczo): przekazywanie dokumentów **nie skraca** czasu do zaktualizowania indeksów węzłów odbierających, tylko go o ok. 25 ms wydłuża (odbiorca czeka na paczkę, a mapowanie tej sprawy trwa krócej niż to oczekiwanie). Skraca natomiast o ok. 60 ms czas na węźle zapisującym (MASTER), prawdopodobnie dlatego, że sekretarz nie czeka na własne mapowanie w sposób, w jaki robi to bez przekazywania (przypuszczenie, niezweryfikowane w kodzie). Różnica jest powtarzalna (przebiegi 1 i 2 zgadzają się co do ok. 10–20 ms), ale M0 i M1 mierzono po osobnych restartach klastra, więc część różnicy może pochodzić ze stanu po restarcie. Wszystkie czasy mieszczą się nad dolną granicą ok. 1 s (cykl sekretarza), więc zysk lub strata mappera to kilkadziesiąt ms w ok. 1100 ms. **Zysk mappera mógłby wystąpić dopiero przy większej paczce zmian** (kilkadziesiąt–kilkaset spraw naraz), której ten pomiar nie obejmuje.

#### Kolejność operacji sekretarza (kod, `LucCaseSaveBufferBusiness.processNextPackage`)

- **Przekazywanie włączone (M1, klaster):** (1) `caseIndexerBusiness.updateIndex(..., PUBLISHER)`: mapowanie na dokumenty, indeksowanie na węźle sekretarza i publikacja dokumentów w pamięci współdzielonej; (2) `awaitPublishedDocuments` (czeka na zapis do pamięci, `store.flush()`); (3) dopiero potem wiadomość JMS z paczką (`luceneCaseSaveBuffersForIndexSender`) i sygnał wybudzenia. Odbiorca (`LuceneCaseSaveBuffersForIndexConsumer`) po odebraniu woła `updateIndex(..., CONSUMER)`, który najpierw próbuje pobrać gotowy dokument (`handoff.take`), a brakujący mapuje sam. To jest opcja 2 z pytania autora (najpierw dokument, potem wiadomość), więc odbiorca zastaje dokumenty w pamięci.
- **Przekazywanie wyłączone (M0) lub brak klastra:** najpierw wiadomość JMS i wybudzenie, dopiero potem `updateIndex(ctx, optimized)` na węźle sekretarza: odbiorcy i sekretarz pracują równolegle, każdy mapuje sam (opcja 1).

Konsekwencja dla opóźnienia: w M1 praca jest szeregowa (mapowanie u sekretarza, publikacja, wiadomość, indeksowanie u odbiorcy), a w M0 równoległa; zysk przekazywania dokumentów to oszczędność CPU odbiorców, a nie krótszy czas do indeksu. To pasuje do wyników dla pojedynczej sprawy (M1: odbiorcy ok. 25 ms za M0). Wiadomość JMS z paczką jest wysyłana po indeksowaniu u sekretarza, więc u sekretarza M0 jest wolniejszy od M1 o ok. 60 ms (wysłanie wiadomości przed indeksowaniem; przypuszczenie, zgodne z kolejnością w kodzie).

#### Paczka 100 spraw naraz, wariant M1 (tryb `--batch 100 --threads 8`, 10 paczek po 2 rozgrzewkowych, czas od końca zapisów paczki do pojawienia się ostatniej zapisanej sprawy w indeksie węzła, ms)

| przebieg | węzeł | n | min | p50 | p90 | max |
|---|---|---|---|---|---|---|
| M1p1 | node1 | 10 | 687 | 774 | 828 | 886 |
| M1p1 | node2 (zapis) | 10 | 297 | 352 | 412 | 449 |
| M1p1 | node3 | 10 | 693 | 777 | 831 | 873 |
| M1p2 | node1 | 10 | 592 | 785 | 1054 | 1201 |
| M1p2 | node2 (zapis) | 10 | 276 | 334 | 408 | 565 |
| M1p2 | node3 | 10 | 649 | 837 | 915 | 1075 |

Wszystkie paczki kompletne (po pomiarze każda sprawa była w indeksie każdego węzła); 1200 spraw z każdego przebiegu usunięto. Odbiorcy są ok. 430–500 ms za węzłem zapisującym (p50 774–837 wobec 334–352 ms). Pomiar mierzy czas do pojawienia się ostatniej sprawy, której zapis zakończył się jako ostatni, więc to przybliżenie końca paczki (zapisy idą na 8 wątkach).

#### Paczka 100 spraw naraz, wariant M0 (przekazywanie wyłączone), ten sam tryb, ms

| przebieg | węzeł | n | min | p50 | p90 | max |
|---|---|---|---|---|---|---|
| M0p1 | node1 | 10 | 391 | 447 | 536 | 840 |
| M0p1 | node2 (zapis) | 10 | 411 | 447 | 682 | 860 |
| M0p1 | node3 | 10 | 364 | 454 | 663 | 842 |
| M0p2 | node1 | 10 | 354 | 485 | 538 | 588 |
| M0p2 | node2 (zapis) | 10 | 349 | 460 | 577 | 657 |
| M0p2 | node3 | 10 | 352 | 447 | 583 | 629 |

#### Porównanie M1 i M0 dla paczki 100 spraw (p50, przebieg 1 / 2, ms od końca zapisów)

| węzeł | M1 (przekazywanie włączone) | M0 (wyłączone) | M1 − M0 |
|---|---|---|---|
| node1 | 774 / 785 | 447 / 485 | ok. +310 |
| node2 (zapis, MASTER) | 352 / 334 | 447 / 460 | ok. −110 |
| node3 | 777 / 837 | 454 / 447 | ok. +355 |

Wniosek (opóźnienie): dla paczki 100 spraw przekazywanie dokumentów **wydłuża** czas aktualizacji indeksów odbiorców o ok. 300–350 ms (z ok. 450 do ok. 780–840 ms; ok. +70%), a skraca o ok. 110 ms czas u sekretarza (MASTER). Czas do spójnego stanu wszystkich trzech indeksów (najpóźniejszy węzeł) to w M0 ok. 450–485 ms, w M1 ok. 780–840 ms. Przyczyna wynika z kolejności w kodzie: w M1 sekretarz najpierw mapuje, indeksuje i publikuje cały pakiet, dopiero potem wysyła wiadomość, więc praca jest szeregowa; w M0 wiadomość wychodzi od razu i wszyscy mapują równolegle. Różnica jest powtarzalna (przebiegi 1 i 2 zgadzają się). **Nie zmierzono zysku w CPU odbiorców**, który jest jedyną stroną, po której przekazywanie dokumentów powinno wygrywać; wymaga to obserwacji obciążenia (`docker stats`) węzłów node1 i node3 podczas paczki.

**Możliwa poprawa kolejności (propozycja, nie wprowadzona):** podzielić `updateIndex` sekretarza na dwie fazy: (1) mapowanie i publikacja dokumentów w pamięci współdzielonej, (2) wysłanie wiadomości JMS, (3) dopiero zapis do własnego indeksu. Wtedy odbiorcy startują, gdy sekretarz zapisuje swój indeks (praca równoległa), a dokumenty już są w pamięci. Opóźnienie odbiorców spadłoby wtedy zapewne do czasu mapowania + zapisu u odbiorcy, a CPU odbiorców zostałby zaoszczędzony.

## Podsumowanie i wnioski (2026-11-05)

Środowisko: klaster trzywęzłowy (Linux, obrazy 3.0.4.15) na `devops-box-01`, klient zdalny (maszyna robocza autora); wszystkie liczby to p50 po 35 pomiarach (paczki: po 10), jedno żądanie naraz.

**1. Koszt zapisu na Linuksie.** Zapis z klastrowymi regionami Ehcache (wariant A) kosztuje ok. 100–130 ms (CMIS `createFolder` i `createDocument`) i ok. 70–74 ms (REST `save` sprawy `FSMServiceOrder`), czyli ok. 50–80 ms ponad odczyt tego samego typu (ok. 20–23 ms, poziom sieci). W 118 na Windowsie `createFolder` trwał 189 ms z regionami klastrowymi i 90 ms z lokalnymi; na Linuksie z regionami klastrowymi jest ok. 100–130 ms.

**2. Warianty konfiguracji (A, B, C).** B (lokalny `default-update-timestamps-region`) i C (`hibernate.cache.use_query_cache=false`) **nie dają mierzalnego zysku** względem A: różnice (CMIS ok. 3–10 ms, sprawa REST do ok. 7 ms, kierunek bywa przeciwny) mieszczą się w rozrzucie między przebiegami (4–11 ms netto w CMIS, ok. 3–5 ms w REST). **Rekomendacja: zostawić regiony klastrowe w konfiguracji A**; B psuje unieważnianie pamięci zapytań między węzłami, C ją wyłącza, a zysku nie widać. Czas zapisu nie jest zdominowany przez Terracottę.

**3. Próg `mercury.cache.caseObject.shared.minCostMs`.** Odczyt `FSMServiceOrder.2699` (27 właściwości, 16 KB) kosztuje tyle co odczyt folderu CMIS (ok. 20–23 ms), a `find` z `cacheUsage=REFRESH` tylko 1–3 ms więcej, więc przekształcenie tej sprawy trwa kilka ms i pamięć współdzielona obiektów (próg 25 ms) się dla niej nie włącza. Próg 5 ms zamiast 25 jest rozsądny dla klienta z Linuksa (odczyt Terracotty 0,3–0,9 ms), ale **nie zmierzono go na typach o wyższym koszcie**, więc wartość pozostaje domyślna (25 ms) do czasu takiego pomiaru. Parametr dotyczy pamięci obiektów spraw, nie przekazywania dokumentów Lucene.

**4. Propagacja zmian do indeksów węzłów (etap 3).** Zmiana jest widoczna w indeksach wszystkich węzłów po ok. 1,0–1,1 s (dolna granica z cyklu sekretarza, przypuszczenie); dla paczki 100 spraw po ok. 450 ms przy wyłączonym przekazywaniu dokumentów i ok. 780–840 ms przy włączonym (obecna kolejność: mapowanie i indeksowanie, potem wiadomość JMS). **Przekazywanie dokumentów Lucene w obecnej kolejności nie skraca czasu do spójności indeksów, tylko go wydłuża (ok. +70% dla paczki 100); jego jedyny spodziewany zysk (CPU odbiorców) nie został zmierzony.** Szczegóły i dane: etap 3 powyżej.

**5. Zadanie wynikające: [229] Adaptacyjne przekazywanie dokumentów Lucene w klastrze** (`tasks/hgdb/229-…/TASK.md`): zmiana kolejności w sekretarzu (dwie fazy), strategia zależna od kosztu mapowania, pomiary CPU i kosztu mapowania przed doborem progu.

**6. Obserwacje:** 155 (kolejność w sekretarzu i zadanie 229), 156 (błędy narzędzia `mercury-transfer`), 157 (błąd klienta HTTP 000 w skryptach pomiarowych).

**Narzędzia i dane pomiarowe (w katalogu zadania):** `mierz-zapis.sh` (CMIS), `mierz-sprawe.sh` (REST, sprawa), `mierz-indeks.py` (propagacja do indeksów, tryb `--batch`), `warianty/` (B, C, M0: konfiguracje i override do kompozycji). Dane testowe: zestaw 116 w `mercury-db-test`, przeniesiony do klastra narzędziem `mercury-transfer` (z obejściem trzech błędów, obserwacja 156).

**Co zostało nieprzetestowane:** zużycie CPU odbiorców przy przekazywaniu dokumentów; koszt mapowania i `minCostMs` dla typów droższych niż `FSMServiceOrder.2699`; `createDocument` z dużą treścią; punkt 2 zakresu (pomiar opóźnienia Terracotty z węzła aplikacji kontenerem `bench`) wykonano wcześniej w pomiarach dev i nie powtórzono na tym klastrze.

#### Zapis jednocześnie na trzech węzłach, wariant M0 (3 × 100 spraw naraz, `--all-writers --batch 100 --threads 8`), ms

Kod: `save` na węźle SLAVE (Lucene) nie jest przekierowywany do MASTER; przekierowanie zależy od `mercury.node.case.role` (RO/WO/RW) i obciążenia CPU (`ClusterUtils.createResultForRWServer`), a w obrazach jest `RW` i `mercury.node.redirection.cpu.idle=0` (brak przekierowań), więc każdy węzeł zapisuje lokalnie. Czas od końca wszystkich 300 zapisów paczki do pojawienia się ostatnich zapisanych spraw każdego węzła w lokalnym indeksie węzła. Wcześniejsze próby z `max_connections=100` kończyły się błędem `too many clients already` (obserwacja 158); po podniesieniu limitu zapisy przeszły bez błędów.

| przebieg | węzeł | n | min | p50 | p90 | max |
|---|---|---|---|---|---|---|
| M0t1 | node1 | 10 | 905 | 1146 | 1235 | 1330 |
| M0t1 | node2 (MASTER) | 10 | 855 | 1080 | 1303 | 1323 |
| M0t1 | node3 | 10 | 898 | 1086 | 1204 | 1431 |
| M0t2 | node1 | 10 | 873 | 1026 | 1260 | 1461 |
| M0t2 | node2 (MASTER) | 10 | 956 | 1031 | 1107 | 1268 |
| M0t2 | node3 | 10 | 883 | 1022 | 1164 | 1393 |

Wszystkie paczki kompletne, 3600 spraw z każdego przebiegu usunięto. Przy zapisie z trzech węzłów jednocześnie czas do spójnych indeksów to ok. 1,0–1,15 s, wszystkie trzy węzły są jednakowo daleko (różnice kilkadziesiąt ms), a rozrzut jest większy niż w pomiarze z jednym piszącym węzłem (max do 1,4–1,5 s). Do porównania z M1.

#### Zapis jednocześnie na trzech węzłach, wariant M1 (przekazywanie włączone), te same parametry, ms

| przebieg | węzeł | n | min | p50 | p90 | max |
|---|---|---|---|---|---|---|
| M1t1 | node1 | 10 | 1401 | 1520 | 1615 | 1665 |
| M1t1 | node2 (MASTER) | 10 | 702 | 806 | 858 | 880 |
| M1t1 | node3 | 10 | 1345 | 1449 | 1609 | 1943 |
| M1t2 | node1 | 10 | 1327 | 1523 | 1827 | 1941 |
| M1t2 | node2 (MASTER) | 10 | 628 | 803 | 919 | 1019 |
| M1t2 | node3 | 10 | 1255 | 1518 | 1770 | 1845 |

#### Porównanie M1 i M0 dla zapisu na trzech węzłach naraz (p50, przebieg 1 / 2, ms)

| węzeł | M1 (przekazywanie włączone) | M0 (wyłączone) | M1 − M0 |
|---|---|---|---|
| node1 | 1520 / 1523 | 1146 / 1026 | ok. +440 |
| node2 (MASTER) | 806 / 803 | 1080 / 1031 | ok. −250 |
| node3 | 1449 / 1518 | 1086 / 1022 | ok. +430 |

Wniosek: przy 300 sprawach zapisanych jednocześnie z trzech węzłów przekazywanie dokumentów jest dla odbiorców **wolniejsze** o ok. 430–440 ms (ok. +40%): ostatni indeks jest aktualny po ok. 1,5 s wobec ok. 1,1 s bez przekazywania. MASTER jest szybszy o ok. 250 ms (806 wobec ok. 1050 ms). Kierunek jest taki sam jak dla pojedynczej paczki (ok. +70% przy 100 sprawach na jednym węźle), więc potwierdza wniosek z obecnej kolejności operacji sekretarza (praca szeregowa), a wielkość różnicy nie maleje przy większym obciążeniu. Obie serie kompletne (0 niekompletnych paczek), 3600 spraw z każdego przebiegu usunięto. Zysku w CPU odbiorców nadal nie zmierzono (zadanie 229).
