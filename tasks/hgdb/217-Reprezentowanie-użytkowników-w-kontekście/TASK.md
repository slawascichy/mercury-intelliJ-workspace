# [217] Reprezentowanie użytkowników: kto może działać w imieniu kogo

https://github.com/slawascichy/hgdb/issues/217

**Status (2026-10-29): zadanie otwarte ponownie i poprawione.** Role w kontekście to grupy użytkownika (nie role zmapowane); wdrożone na dev, szczegóły w sekcji „Stan implementacji po korekcie (2026-10-29)”. Poniżej wcześniejsze statusy.

**Status (2026-10-28):** podzadanie zadania 016 (Widoki), realizowane na gałęzi `hgdb-016` (bez osobnej gałęzi `hgdb-217`). Etap 0 (rozpoznanie) wykonany, wyniki w sekcji „Wyniki rozpoznania etapu 0”. Weryfikacja kontekstu w REST zaimplementowana i przetestowana na serwerze dev (sekcja „Stan implementacji”); zostają punkty z listy „Do zrobienia”. Zadanie założone z polecenia autora („bardzo ważny temat”). Temat wyszedł przy testach zadania 016.

## Założenie autora

Użytkownik w kontekście operacji (`Context.userName`) nie musi być tym, kto się uwierzytelnił. Konta techniczne reprezentują innych użytkowników. Docelowa zasada:

- użytkownik z rolą `mrc-user` może reprezentować tylko siebie,
- użytkownik z rolą `mrc-useradmin` może reprezentować innych.

## Co wiemy (zweryfikowane w kodzie lub teście)

| Fakt | Źródło |
|---|---|
| `Context` niesie `userName` i `userRoles`. Klucz pamięci podręcznej uprawnień (`SecurityContext`) powstaje z nazwy użytkownika i ról z kontekstu. | `mercury-lib/mercury-core`: `Context`, `SecurityContext` |
| Uprawnienia do typów i pól wynikają wyłącznie z ról w kontekście (tabela `igo_da_typeparameterroles`). Pusta lista ról daje pusty kontekst uprawnień. | `mercury-dao`: `SecurityContextHelper.createNewInstance` |
| Role predefiniowane: `mrc-user` (`USER_ROLE_NAME`) i `mrc-admin` (`SUPERUSER_ROLE_NAME`). W bazie dev: `mrc-user` ma `RW` do wszystkich typów i pól, `mrc-admin` ma `RO`. | `MRole`, test na bazie dev 2026-10-28 |
| Zakresy OAuth: `mrc-sysadmin`, `mrc-user`, `mrc-useradmin`. Rola `mrc-useradmin` występuje w konfiguracji bezpieczeństwa i w skryptach schematu LDAP. | `mercury-security-OAuth.properties`, `OAuthScopesTest`, `MRC_LDAP_CREATE_SCHEMA_*.sql` |
| Na serwerze dev użytkownik `admin` ma role `mrc-groupadmin`, `mrc-serviceadmin`, `mrc-sysadmin`, `mrc-user` i `mrc-useradmin`. Użytkownik `tester` ma tylko `mrc-user`. Te same pięć ról mają grupy `admins` i `CKJAV-Team` (typ `G`). | tabela `MRC_LDAP_INT_ROLES_MAP` (stan z 2026-10-28) |
| Tabela użytkowników ma flagę `is_technical`. | `igo_adm_users` |

## Obserwacje z testu REST (2026-10-28, serwer dev, PostgreSQL)

1. Żądanie z `context` bez `userName` i `userRoles` wykonuje się jako użytkownik `nullmercury` (`MUser.NULL_SYSTEM_USER_NAME`) z pełnym dostępem do danych.
2. Tokeny `admin` (zakres `mrc-sysadmin`) i `tester` (zakres `mrc-user`) dawały ten sam wynik przy tym samym `context`. Tożsamość i uprawnienia pochodziły z ciała żądania, a nie z tokenu.
3. Role podane w `context.userRoles` były stosowane. Rola z ograniczonym odczytem zawężała wyniki, a rola bez uprawnień dostawała odmowę.

## Wyniki rozpoznania etapu 0 (2026-10-28)

Z lektury kodu `mercury` i testów REST na serwerze dev (PostgreSQL).

### Jak dziś powstaje tożsamość w trzech kanałach

| Kanał | Uwierzytelnienie | Skąd `userName` i `userRoles` |
|---|---|---|
| REST (`/rest/service/…`, `OAuthFilter`) | Token OAuth (hasło użytkownika sprawdza realm Tomcata). Filtr sprawdza ważność tokenu, klienta i zgodność zakresu tokenu ze ścieżką. Nie ustawia użytkownika i nie porównuje `token.getSecurityUser()` z kontekstem. | Wyłącznie z ciała żądania: wygenerowany `*Rest` przekazuje `requestBody.getContext()` wprost do akcji. |
| SOAP (`/services/*`, CXF) | WS-Security `UsernameToken` weryfikowany przez `WSSEUsernameTokenCallback`. Zna on jedną parę (identyfikator, token) z konfiguracji serwera, wspólną dla wszystkich klientów. | Z `Context` w treści wywołania. |
| RMI/HTTP invoker i CMIS (`/remoting/*`, `/cmisws*`) | `RemoteBasicAuthFilter`: Basic z tą samą wspólną parą (identyfikator, token). Po sukcesie ustawia atrybut `REMOTE_USER` na identyfikator usługi. | Z `Context` przekazanego przez klienta. |

Wniosek: żaden kanał nie wiąże `Context.userName` ani `userRoles` z uwierzytelnionym użytkownikiem. SOAP i RMI uwierzytelniają usługę, a nie człowieka. To wyjaśnia, dlaczego konta techniczne mogą reprezentować innych, ale też pozwala każdemu uwierzytelnionemu klientowi podać dowolną tożsamość i role.

### Test: czy token `mrc-user` może podać dowolne role w `context`

Token użytkownika `tester` (zakres `mrc-user`), operacja `dropView` na nieistniejącym widoku (sprawdza uprawnienia przed szukaniem definicji):

| `context.userRoles` | Wynik |
|---|---|
| brak (kontekst domyślny) | uprawnienia przeszły (komunikat „nie znaleziono definicji”) |
| `mrc-user` | uprawnienia przeszły |
| `mrc-admin` | uprawnienia przeszły |
| `userName=admin`, `mrc-admin` | uprawnienia przeszły |
| `brak-takiej-roli` (roli nie ma w bazie) | odmowa `SC001` |

Rola z ciała żądania jest stosowana bez żadnej weryfikacji względem tokenu. Uwaga: w bazie dev `mrc-user` ma `RW` do wszystkich typów, więc ten test nie pokazuje eskalacji z roli słabszej do silniejszej, tylko to, że role są przyjmowane od klienta. W instalacji z zawężoną rolą `mrc-user` przejście na `mrc-admin` dawałoby eskalację uprawnień. Tego nie sprawdzono.

### Znalezione przy okazji: `generateView` omija kontrolę uprawnień

`CaseViewDefinitionAction.generateView` wysyła komunikat JMS (`caseViewCreatorSender.sendMesage(viewName, force)`) i nie sprawdza uprawnień. Odbiorca `CaseViewCreatorReceiver` wykonuje `generateView` kontekstem systemowym (`JmsContextUtils.createContext()`), więc kontrola `isAllRO()` w logice nie dotyczy wołającego.

Test na własnym widoku `Vw217`: wywołanie `generateView` z `force=true` przez token `tester` (zakres `mrc-user`) z rolą `brak-takiej-roli` zmieniło `oid` widoku w PostgreSQL (253165 → 253171), czyli widok został skasowany i utworzony od nowa. Odmowa nie została zgłoszona wołającemu. Każdy uwierzytelniony klient REST może więc wymusić przebudowę dowolnego widoku. Dane testowe usunięto. Inne operacje wysyłające komunikaty JMS bez kontroli w akcji nie były przeglądane.

### Skutki uboczne testów

Wywołania z `userName=tester` utworzyły w `igo_adm_users` rekord `tester` (id 7702). Serwer zakłada rekord użytkownika dla nieznanej nazwy z kontekstu. To kolejny skutek braku weryfikacji nazwy.

## Decyzje autora (2026-10-28)

- Zakres (scope) tokenu decyduje wyłącznie o dostępie do usług. Nie zawęża ról w `context` i nie jest źródłem ról.
- Role w `context` muszą być podzbiorem ról z `MRC_LDAP_INT_ROLES_MAP` (dla użytkowników spoza lokalnego repozytorium: grupy LDAP mapowane na role w tej samej tabeli). Role w `igo_adm_roles` to role procesowe i muszą być zmapowane użytkownikowi.
- Reprezentowanie siebie: `userName` równe uwierzytelnionemu. Reprezentowanie innych wymaga roli `mrc-useradmin` w mapowaniu ról.
- Brak `userName` jest odrzucany. Pusta lista ról oznacza brak uprawnień. Użytkownik bez zmapowanych ról jest odrzucany.
- `mrc-admin` to zwykła rola procesowa (nie zamieniamy jej na `mrc-useradmin`). Może być w kontekście, jeśli jest zmapowana użytkownikowi.
- Zakres: REST. SOAP i RMI/CMIS (wspólne poświadczenia usługowe) poza zakresem tego etapu.

## Stan implementacji (2026-10-28, gałąź `hgdb-016`, bez commita)

| Element | Gdzie |
|---|---|
| Role użytkownika bez hasła: `TomcatLdapRealm.findUserRoles` | `mercury-gui-core` |
| Reguły: `RestServicesHelper.verifyContext`, `verifyContextBasedOnOAuth`, stała `ROLE_USER_ADMIN` | `mercury-gui-core` |
| Weryfikacja przed kontrolerem: `ContextVerificationAdvice` (`@ControllerAdvice`, `RequestBodyAdvice`), HTTP 403 z `{ "error":"invalid_grant" }` albo `{ "error":"username_required" }` | `mercury-ws-app`, pakiet `org.mercury.rest.server.security` |
| Wyłączenie dla kontrolerów biorących tożsamość z tokenu: adnotacja `@IdentityFromToken` (na razie `LoggerLevelsExtRest`) | `mercury-ws-app` |
| Skanowanie pakietu | `moduleDb-3.0-servlet.xml`, `moduleDb-2.0-servlet.xml` |
| Dokumentacja | `docusaurus-hgdb`: `003_Architecture/004_Permissions_mechanism/index.mdx` (EN i PL) |

### Testy na serwerze dev (2026-10-28), operacja `findViewInfos`, wszystkie zgodne z oczekiwaniem

| Token | `context` | Wynik |
|---|---|---|
| `tester` | `tester`, `[mrc-user]` | OK |
| `tester` | `tester`, role puste | OK (brak uprawnień do danych) |
| `tester` | `tester`, `[mrc-user, mrc-sysadmin]` | 403 `invalid_grant` |
| `tester` | `admin`, `[mrc-user]` | 403 `invalid_grant` (brak `mrc-useradmin`) |
| `tester` | brak `userName` albo brak `context` | 403 `username_required` |
| `admin` | `admin`, `[mrc-user, mrc-sysadmin]` | OK |
| `admin` | `tester`, `[mrc-user]` | OK (reprezentowanie) |
| `admin` | `tester`, `[mrc-sysadmin]` | 403 `invalid_grant` (rola spoza ról `tester`) |
| `admin` | `nikt217` (brak w realmie), role niepuste lub puste | 403 `invalid_grant` |
| `admin` | `admin`, `[mrc-admin]` | 403 `invalid_grant` (`mrc-admin` nie jest zmapowana `adminowi`) |

Dodatkowo: `CaseSearchExtRest/searchByQuery` (ręczny kontroler) podlega tym samym regułom. `LoggerLevelsExtRest` bez `context` działa jak dotąd (admin z `mrc-sysadmin` dostaje dane, `tester` odmowę z własnej reguły). Nie zakładano żadnych danych w bazie.

### Naprawa luki zarządzania widokami (2026-10-28)

Rozpoznanie wykazało szerszą lukę niż `generateView`: kontrolę `isAllRO()` miały tylko `generateView` i `dropView` w logice, więc `createView`, `updateView` oraz ogólne `insert`/`update`/`remove` (wystawione też w REST) nie sprawdzały uprawnień, a akcja `generateView` zlecała pracę kontekstem systemowym przez JMS bez kontroli.

| Element | Zmiana |
|---|---|
| `ICaseViewDefinitionLogic` (`mercury-lib/mercury-srv-api`) | nowa metoda `checkManagePrivileges(Context)` |
| `CaseViewDefinitionLogic` (`mercury-srv`) | jedna implementacja kontroli (zastąpiła dwa zduplikowane bloki), wywołana w `createView`, `updateView`, `dropView`, `generateView` i w nadpisanych `insert`, `insertList`, `update`, `updateList`, `remove`, `removeList`. Konteksty wewnętrzne z parametrem pomijania weryfikacji (odbiorca JMS) nie są sprawdzane. |
| `CaseViewDefinitionAction.generateView` (`mercury-ws-server`) | wywołuje `checkManagePrivileges` przed wysłaniem komunikatu JMS |

Test na serwerze dev: `admin` (`mrc-user`, `RW` do wszystkich typów) tworzy i generuje widok, a użytkownik z pustą listą ról dostaje `SC001` przy `createView`, `updateView`, `generateView`, `dropView`, `insert`, `update` i `remove`. Po próbie przebudowy bez uprawnień wersja i `oid` widoku w PostgreSQL bez zmian. Dane testowe usunięto. Wymaga wydania `mercury-lib` (zmiana interfejsu).

### Ciała żądań jako tekst JSON (2026-10-28)

Metody z `@RequestBody String` (usługi typów spraw `CaseTypeServicesController` oraz `save` i `initModel` w `CaseBusinessExtRest`, wersje `rest` i `rest2`) nie były objęte advice, bo ciało nie ma typu z `getContext()`. `withCaseAsType` tworzyło przy braku `context` kontekst bez `userName`. Dodano adnotację `@ContextInJsonBody` (na trzech klasach) i obsługę ciał `String` w `ContextVerificationAdvice`: kontekst jest odczytywany z pola `context` tekstu JSON, a brak pola albo niepoprawny JSON kończy się odrzuceniem (`username_required`).

Test na serwerze dev dla `types/SlmAddress/find`, `CaseBusinessExtRest/save` i `CaseBusinessExtRest/initModel`: brak `context`, brak `userName` i niepoprawny JSON dają 403 `username_required`; `tester` jako `admin` i role spoza zestawu dają 403 `invalid_grant`; `tester` jako `tester` i `admin` jako `tester` przechodzą weryfikację.

### Testy automatyczne

- `mercury-gui-core`: `RestServicesHelperVerifyContextTest` (9 testów, atrapa realmu, bez bazy): reguły `verifyContext`.
- `mercury-ws-app`: `ContextVerificationAdviceTest` (9 testów): które żądania obejmuje advice (ciała z `getContext()`, ciała `String` z `@ContextInJsonBody`, wyłączenie `@IdentityFromToken`) i `extractContext`.
- Uruchamiane z filtrem `-Dtest=...`. Pełne zestawy testów modułów nie były uruchamiane.

### Do zrobienia

1. ~~Kontrola uprawnień w `CaseViewDefinitionAction.generateView` przed wysłaniem komunikatu JMS (obserwacja 109).~~ Wykonane 2026-10-28, patrz „Naprawa luki zarządzania widokami”.
2. ~~`CaseTypeServicesController` przyjmuje `@RequestBody String`.~~ Wykonane, patrz „Ciała żądań jako tekst JSON”.
3. ~~`NodeMonitorRest`.~~ Wykonane 2026-10-28 na polecenie autora: endpoint `/monitor/NodeMonitorRest/load` (prezentacja obciążenia węzłów na stronie głównej) jest poza mechanizmami uwierzytelniania i nie używa tożsamości, więc dostał `@IdentityFromToken`. Bez tego żądanie z tokenem (np. z ciasteczka sesji OAuth) dostawało 403 `username_required`. Test: bez tokenu i z tokenem zwraca listę węzłów. Pozostaje otwarte pytanie o zewnętrznych klientów REST wysyłających własny `context` (monitoring, serwer Iron POI, IBM BPM): w repozytoriach `mercury-cmd`, `mercury-client`, `hgdb-client-open` i `mercury-docker` nie ma klientów REST w Javie. W Swagger UI przykłady nie mają wypełnionego `userName`, trzeba go podać.
4. ~~Testy automatyczne w repozytorium.~~ Wykonane, patrz „Testy automatyczne”.
5. Ewentualny cache ról (każde żądanie czyta role z bazy, a dla użytkowników LDAP także z LDAP). Dodać po pomiarze.
6. Kanały SOAP i RMI/CMIS (osobna decyzja, razem z kontami technicznymi).
7. Role procesowe w istniejących środowiskach: `mrc-admin` musi być zmapowana użytkownikom, którzy mają ją podawać w `context`.
8. Przegląd operacji wykonywanych kontekstem systemowym: w warstwie `ws` jedyną wysyłką JMS z akcji użytkownika był `generateView` (naprawiony). Wewnętrzne użycia kontekstu systemowego w `mercury-srv` (sekretarze, `CaseBusiness`) nie były audytowane.

## Czego nie wiemy (do rozpoznania)

1. ~~Czy serwer porównuje `context.userName` i `userRoles` z uwierzytelnionym użytkownikiem lub tokenem.~~ Rozstrzygnięte: nie, w żadnym z trzech kanałów (patrz wyżej).
2. ~~Czy token `mrc-user` może podać w `context.userRoles` dowolne role.~~ Rozstrzygnięte: tak. Nie sprawdzono eskalacji w instalacji z zawężoną rolą `mrc-user`.
3. ~~Jak wygląda to samo w SOAP i RMI.~~ Rozstrzygnięte: wspólna para (identyfikator, token) usługi, tożsamość z `Context`. Nie sprawdzono, co dokładnie przekazują klienci (`hgdb-client-open`, `mercury-client`, `mercury-cmd`).
4. Skąd brać role reprezentowanego użytkownika: z kontekstu żądania (jak teraz), z repozytorium ról (LDAP, `MRC_LDAP_INT_ROLES_MAP`) czy z bazy Mercury.
5. Kto z istniejących kont technicznych używa reprezentowania i które integracje (IBM BPM, `mercury-cmd`, serwer Iron POI) na nim polegają.
6. Które inne operacje wysyłają komunikaty JMS lub wykonują pracę kontekstem systemowym bez kontroli uprawnień wołającego (jak `generateView`).
7. Jak token (`getSecurityUser()`, zakres) ma się do zasady „`mrc-user` tylko siebie, `mrc-useradmin` innych”: czy `useradmin` ma być zakresem OAuth (jest w konfiguracji), rolą LDAP, czy obiema.

## Proponowane etapy

### Etap 0. Rozpoznanie (bez zmian w kodzie): wykonany 2026-10-28

- Przepływ `Context` w REST, SOAP i RMI prześledzony (wyniki wyżej).
- Test z tokenem `mrc-user` wykonany.
- Do dokończenia: lista klientów przekazujących własny `Context` (pytanie 5) i przegląd operacji JMS (pytanie 6).

### Etap 1. Decyzje autora

- Zasada dla `mrc-user` i `mrc-useradmin` (patrz „Założenie autora”). Czy `mrc-sysadmin` i `mrc-admin` mają tu osobne reguły.
- Źródło ról reprezentowanego użytkownika (pytanie 4).
- Zachowanie przy braku `userName` w kontekście: dziś jest to użytkownik `nullmercury` z pełnym dostępem.
- Sposób zapisu reprezentowania w audycie (kto działał, w czyim imieniu).

### Etap 2. Implementacja

- Kontrola w jednym miejscu, wspólnym dla REST, SOAP i RMI, rozszerzająca istniejący mechanizm tworzenia kontekstu. Bez drugiego, równoległego mechanizmu.
- Odrzucanie żądań, w których uwierzytelniony użytkownik reprezentuje kogoś, kogo nie wolno mu reprezentować, błędem uprawnień (`SC001…`).
- Pochodzenie ról z zaufanego źródła, a nie z pola przesłanego przez klienta.
- Upgrade wymienia cały serwer, więc bez okresu przejściowego i bez adapterów zgodności. Stare zachowanie usuwamy w tej samej zmianie.

### Etap 3. Testy i dokumentacja

- Testy REST, SOAP i RMI: `mrc-user` reprezentujący siebie (OK), `mrc-user` reprezentujący innego (odmowa), `mrc-useradmin` reprezentujący innego (OK), konto techniczne.
- Sprawdzić `openapi-doc-report.txt` i klucze `openapi-docs_*` po ewentualnej zmianie API.
- Dokumentacja w `docs/` po polsku oraz wpis do `docs/obserwacje.md`.

## Powiązania

- Zadanie 016 (Widoki): kontrola uprawnień odczytu widoków opiera się na rolach z `context`. Testy uprawnień wykonano, podając role w ciele żądania. Poprawność tej kontroli w produkcji zależy od tego zadania.
- Testy wcześniejszych zadań na serwerze dev (58) wykonywano na tych samych założeniach co do kontekstu.

## Korekta założeń (2026-10-29)

### Koncepcja autora

1. Lista ról w `context` (`userRoles`) to lista **grup/ról użytkownika**.
2. Lista musi być podzbiorem `TomcatMercuryPrincipal.groups`. Dane do tej listy pozyskuje realm: z LDAP albo z bazy danych (użytkownicy lokalni).
3. Użytkownicy lokalni mogą nie mieć ustawionych grup. Wtedy ich grupą domyślną jest `mrc-localgroup`.
4. Automatyczne mapowanie grupy `mrc-localgroup` na rolę `mrc-user`.

### Stan kodu (zweryfikowane 2026-10-29)

| Fakt | Źródło |
|---|---|
| `TomcatMercuryPrincipal` ma osobno `roles` (role usługowe, np. `mrc-user`, `mrc-sysadmin`), `groups` i `primaryGroup`. | `TomcatMercuryPrincipal` |
| `groups` jest ustawiane **tylko w gałęzi LDAP** (`p.setGroups(ldapGroups)` w `TomcatLdapRealm.authenticate`). Dla użytkownika lokalnego `groups` jest `null`. | `TomcatLdapRealm` |
| Repozytorium lokalne ma tylko `mrc_ldap_int_users` (nazwa, pełna nazwa, hasło, data wygaśnięcia) i `mrc_ldap_int_roles_map` (uczestnik, typ `U`/`G`, rola). Nie ma tabeli ani kolumny z grupami użytkownika lokalnego. | schemat bazy dev |
| Role usługowe wylicza `findRolesInLocalRepository(użytkownik, grupy LDAP)` z mapowania (`U` po nazwie użytkownika, `G` po grupach LDAP). | `TomcatLdapRealm` |
| GUI buduje `context.userRoles` z **ról** principala (`user.getRoles()`), a `currentRole` z `primaryGroup`, potem pierwszej roli, potem pierwszej grupy. | `AbstractController` |
| Weryfikacja z zadania 217 (`RestServicesHelper.verifyContext`, `TomcatLdapRealm.findUserRoles`) porównuje `userRoles` z **rolami zmapowanymi**, a nie z grupami. | zadanie 217, wdrożone 2026-10-28 |

### Rozbieżności i pytania do autora

1. **Z czego składa się zbiór dozwolony: wyłącznie z `groups`, czy `groups` plus role zmapowane?**
   - Tylko `groups` (ścisła wersja koncepcji): użytkownik lokalny bez zapisanych grup ma `[mrc-localgroup]`, więc `context` z `mrc-user` zostałby odrzucony, a domyślne uprawnienia w bazie dev (`mrc-user` ma `RW` do wszystkich typów) przypisane są do roli `mrc-user`, nie do `mrc-localgroup`. Zmieniłoby to też role procesowe w `igo_da_typeparameterroles` u klientów (nazwy grup zamiast `mrc-user`).
   - `groups` plus role zmapowane: zgodne z GUI (które wysyła role) i z danymi domyślnymi. Moja rekomendacja.
2. **Skąd użytkownik lokalny ma grupy?** Dziś nie ma gdzie ich zapisać. Opcje: (a) bez nowego magazynu: każdy użytkownik lokalny ma tylko `mrc-localgroup`; (b) nowa kolumna lub tabela grup użytkowników lokalnych (zmiana schematu); (c) traktować wiersze `U` z `mrc_ldap_int_roles_map` jako grupy użytkownika lokalnego. Punkt 3 koncepcji („jeżeli nie mają ustawionych grup”) zakłada, że ustawienie jest możliwe.
3. **Skutek automatycznego mapowania `mrc-localgroup` → `mrc-user`:** każdy użytkownik lokalny bez zapisanych grup dostaje rolę `mrc-user`, także ten, któremu administrator celowo jej nie nadał. W bazie dev `admin` i `tester` już ją mają, więc nic się nie zmienia. Czy mapowanie ma obowiązywać zawsze, czy tylko gdy użytkownik nie ma żadnej jawnej roli w `mrc_ldap_int_roles_map`?
4. **GUI i sesja** (`AbstractController`, `createContextBasedOnSession`) nadal budują kontekst z ról, nie z grup. Weryfikacja dotyczy tylko REST, więc ścieżki GUI się nie zmieniają, ale zasada „role w kontekście = grupy” będzie wtedy różna dla REST i GUI.

### Plan naprawy (po odpowiedziach na pytania 1–3)

| Krok | Zakres |
|---|---|
| 1 | `TomcatLdapRealm`: stała `mrc-localgroup`. Nowa metoda grup użytkownika (`findUserGroups`): LDAP → grupy z LDAP; lokalny → zapisane grupy (zgodnie z odpowiedzią na pytanie 2) albo `mrc-localgroup`. `authenticate` ustawia `groups` także dla użytkownika lokalnego. |
| 2 | Automatyczne mapowanie `mrc-localgroup` → `mrc-user` w jednym pomocniku używanym przez `authenticate` i `findUserRoles` (zakres według pytania 3). |
| 3 | `RestServicesHelper.verifyContext`: zbiór dozwolony = grupy reprezentowanego użytkownika (plus role zmapowane według pytania 1). Warunek reprezentowania innych bez zmian (rola `mrc-useradmin` uwierzytelnionego użytkownika). Użytkownik bez grup i ról nadal odrzucany. |
| 4 | Testy: aktualizacja `RestServicesHelperVerifyContextTest` (atrapa realmu z grupami), nowe przypadki: grupa domyślna, grupy LDAP, automatyczne `mrc-user`, podzbiory. |
| 5 | Dokumentacja EN i PL (`Permissions_mechanism`): role w kontekście to grupy użytkownika, grupa domyślna, mapowanie. Poprawka sekcji decyzji w tym pliku i obserwacji 108. |
| 6 | Wdrożenie na dev i test REST: `tester` z `[mrc-localgroup]` i z `[mrc-user]` (według pytania 1), `admin` reprezentujący, odmowy. Ścieżki LDAP nie da się sprawdzić na dev (brak dostępu do LDAP), tylko testem jednostkowym z atrapą. |

**Ograniczenia:** wcześniejsze testy REST i dokumentacja z 2026-10-28 opisują stary model (role zmapowane) i wymagają powtórzenia po zmianie. Testy z kontekstem `[mrc-user]` przestałyby przechodzić przy wersji „tylko grupy”.

### Decyzje autora (2026-10-29)

1. Zbiór dozwolony dla `userRoles` w `context` to **wyłącznie `groups`**. Role (usługowe) zostają w `roles`.
2. Użytkownicy lokalni nie mają magazynu grup. Role lokalnych użytkowników nadaje się bezpośrednio użytkownikowi (wiersze `U` w `mrc_ldap_int_roles_map`). Użytkownicy z LDAP dostają role przez grupy (wiersze `G`) i mogą też dostawać je bezpośrednio (wiersze `U`); dla nich działają oba źródła (potwierdzone w kodzie: `findRolesInLocalRepository` łączy `U` po nazwie użytkownika i `G` po grupach LDAP). Użytkownik lokalny bez grup dostaje grupę domyślną.
3. Rola `mrc-user` to podstawowa rola systemu (bez niej nie ma logowania). Użytkownicy lokalni są tworzeni po to, żeby mieć dostęp do aplikacji, więc rola `mrc-user` ma im być nadawana automatycznie, zawsze.
4. Zasada „role w kontekście = grupy użytkownika” ma obowiązywać jednakowo w REST i w GUI.
5. Przy weryfikacji `currentRole`: gdy jest ustawione, musi być jedną z wartości `userRoles`; gdy nie jest, ustawić `primaryGroup`, jeśli to możliwe.
6. Nazwa grupy domyślnej użytkownika lokalnego to **`mrc-user`**, a nie `mrc-localgroup`. Powód: `Context` domyślnie dodaje `MRole.DEFAULT_ROLE_NAME` (`mrc-user`) do `userRoles` (konstruktory `Context`, linie 256–257 i 286–287 w `Context.java`). Stała `mrc-localgroup` z poprzedniej wersji planu odpada.

### Fakty z kodu, które z tego wynikają

| Fakt | Skutek |
|---|---|
| `new Context()` zawsze zaczyna z `userRoles = {mrc-user}`. Żądanie JSON bez pola `userRoles` zachowuje tę wartość domyślną. | Kontekst bez jawnych ról niesie `mrc-user`, więc `mrc-user` musi być dozwolone dla każdego uwierzytelnionego użytkownika (zobacz pytanie 1 niżej). |
| Serwer sam zakłada użytkowników i role z kontekstu (`ModifyInfoHelperImpl.getOrCreateUser`/`getOrCreateRole`: tabele `igo_adm_users` i `igo_adm_roles`). Przy pustych rolach rejestruje `mrc-user`, a przy pustym `currentRole` też `mrc-user`. Uprawnienia do danych (`SecurityContext`) liczą się z `userRoles` wprost, pusta lista oznacza brak uprawnień. | `currentRole` nie jest nigdzie sprawdzany względem `userRoles`: reguła z punktu 5 jest nowa. |
| GUI (`AbstractController.createContext`) buduje `userRoles` z ról principala (`user.getRoles()`), a `currentRole` z `primaryGroup`, potem pierwszej roli, potem pierwszej grupy. REST z sesji (`createContextBasedOnSession`) bierze role z principala, z tokenu OAuth (`createContextBasedOnOAuth`) zakresy tokenu. | Do ujednolicenia (punkt 4): wspólny sposób budowy kontekstu z principala, z grup. Tokenowy kontekst z zakresów służy kontrolerom `@IdentityFromToken` (role usługowe, np. `mrc-sysadmin`) i zostaje. |

### Zaktualizowany plan naprawy

| Krok | Zakres |
|---|---|
| 1 | `TomcatLdapRealm`: grupy użytkownika. LDAP: grupy z LDAP. Lokalny: grupa domyślna `mrc-user` (stała w jednym miejscu). `authenticate` ustawia `groups` także dla użytkowników lokalnych. Role lokalnego: wiersze `U` plus `mrc-user` zawsze. Role użytkownika LDAP: wiersze `G` po grupach (jak dotąd). |
| 2 | `RestServicesHelper.verifyContext`: `userRoles` ⊆ `groups` reprezentowanego użytkownika (z regułą dla `mrc-user`, zobacz pytanie 1). Nowa reguła `currentRole`: ustawione musi należeć do `userRoles`, nieustawione dostaje `primaryGroup`, jeśli jest w `userRoles`. Warunek reprezentowania innych (`mrc-useradmin` w `roles` uwierzytelnionego) bez zmian. |
| 3 | Ujednolicenie REST i GUI: jeden pomocnik budujący `Context` z principala (nazwa, `userRoles` = grupy, `currentRole` = `primaryGroup` albo pierwsza grupa). `AbstractController` i `createContextBasedOnSession` korzystają z niego. |
| 4 | Testy: `RestServicesHelperVerifyContextTest` (atrapa z grupami i rolami osobno): grupa domyślna lokalnego, grupy LDAP, `mrc-user` zawsze dozwolone (jeśli takie będzie rozstrzygnięcie), `currentRole` (poza zbiorem, ustawione z `primaryGroup`), reprezentowanie. Testy pomocnika kontekstu dla GUI. |
| 5 | Dokumentacja EN i PL (`Permissions_mechanism`), poprawka obserwacji 108 i opisu w tym pliku. |
| 6 | Wdrożenie na dev i test REST i GUI (logowanie `admin`/`tester`, kontekst z sesji). Ścieżki LDAP tylko testem jednostkowym z atrapą (brak dostępu do LDAP). |

### Otwarte pytania

1. **`mrc-user` a użytkownicy LDAP.** Kontekst bez `userRoles` niesie domyślnie `mrc-user`. Dla użytkownika lokalnego to jego grupa domyślna. Użytkownik z LDAP ma grupy z LDAP (np. nazwy grup AD), więc bez `mrc-user` w nich taki kontekst zostałby odrzucony. Czy `mrc-user` ma być zawsze dozwolone jako grupa domyślna każdego uwierzytelnionego użytkownika (moja propozycja, bo logowanie i tak wymaga tej roli)?
2. **Skutek dla istniejących instalacji z LDAP.** GUI wysyła dziś jako `userRoles` role zmapowane (np. `mrc-user`), a uprawnienia do typów (`igo_da_typeparameterroles`) są zapisane na te nazwy. Po zmianie GUI wyśle nazwy grup, więc wiersze uprawnień trzeba mieć także dla nazw grup (albo je przepisać). Wydanie wymienia cały serwer, ale dane zostają. Czy mamy przygotować notatkę lub skrypt migracji uprawnień na wydanie?
3. **`currentRole` poza zbiorem:** odrzucać żądanie (`invalid_grant`, moja propozycja, bo to jawny błąd klienta), czy poprawiać po cichu?

### Rozstrzygnięcia z 2026-10-29 (uzupełnienie)

- `mrc-user` jest zawsze dozwolone w `userRoles` dla każdego uwierzytelnionego użytkownika (także z LDAP), bo `Context` nadaje je domyślnie.
- `currentRole` poza zbiorem `userRoles` jest odrzucane (`invalid_grant`). Nieustawione dostaje grupę główną, jeśli należy do `userRoles`.
- Użytkownicy z LDAP dostają role usługowe z wierszy `U` (po nazwie) i `G` (po grupach LDAP). Lokalni: wiersze `U` plus zawsze `mrc-user`.
- Autor: uprawnienia do spraw wynikają z `userRoles`, a weryfikacja kontekstu jest tylko sprawdzeniem zgodności danych z kontekstu z realmem.

## Rewizja decyzji (2026-10-29, po analizie skutków)

Model „tylko grupy” (decyzja 1 powyżej) odrzucono. Powód: użytkownik lokalny miałby wyłącznie grupę `mrc-user`, więc nie mógłby mieć własnych ról procesowych (np. `vw016-addr` z testów maskowania), a użytkownicy LDAP wymagaliby migracji uprawnień z nazw ról na nazwy grup. Autor wskazał, że uprawnienia do spraw wynikają z `userRoles`, a weryfikacja kontekstu ma tylko sprawdzić zgodność danych z kontekstu z realmem. Obowiązujące zasady:

1. `userRoles` ⊆ **suma grup i ról** użytkownika z realmu, plus zawsze `mrc-user` (kontekst nadaje ją domyślnie).
2. `currentRole` **musi pochodzić z grup**. Ustawione musi należeć do `userRoles` i do grup użytkownika, inaczej `invalid_grant`. Rola, która nie jest grupą (np. `mrc-useradmin`), nie może być obecną rolą. Nieustawione dostaje grupę główną, jeśli należy do `userRoles`.
3. Reprezentowanie innych, użytkownik bez grup i ról, brak `userName`: bez zmian.
4. Zasada jest wspólna dla REST i GUI (jeden pomocnik budujący kontekst).

Decyzje 2–6 z sekcji „Decyzje autora (2026-10-29)” (grupa domyślna lokalnego `mrc-user`, role lokalnych przez wiersze `U`, LDAP przez `U` i `G`, `mrc-user` zawsze) pozostają w mocy.

## Stan implementacji po rewizji (2026-10-29)

| Element | Zmiana |
|---|---|
| `TomcatLdapRealm` | Stała `LOCAL_USER_GROUP` = `mrc-user`. Użytkownik lokalny dostaje rolę `mrc-user` zawsze oraz grupę i grupę główną `mrc-user`. `authenticate` ustawia `groups` i `primaryGroup` także dla lokalnych. Nowe: `findUserGroups`, `findUserPrimaryGroup` (wspólny parser `parsePrimaryGroup`). `findUserRoles` łączy dla LDAP wiersze `U` i `G` (wcześniej pomijał `U`, gdy użytkownik nie miał grup). |
| `RestServicesHelper.verifyContext` | `userRoles` ⊆ grupy ∪ role reprezentowanego użytkownika ∪ `{mrc-user}`. `currentRole` ustawione: musi należeć do `userRoles` i do grup. Nieustawione: grupa główna, jeśli jest w `userRoles`. |
| `RestServicesHelper.applyUserRolesToContext(context, groups, roles, primaryGroup, fallbackRole)` | `userRoles` = grupy ∪ role; `currentRole` = grupa główna albo pierwsza grupa (nigdy sama rola); rola zastępcza (anonimowa) tylko bez grup i ról. |
| `AbstractController` (GUI) | Kontekst przez ten sam pomocnik: grupy principala `TomcatMercuryPrincipal` i jego role. Principal spoza realmu Mercury nie ma grup, więc ma tylko role i pusty `currentRole`. |

**Poza zakresem ujednolicenia:** `createContextBasedOnSession` i `createContextBasedOnOAuth` zostają przy rolach usługowych (kontrolery `@IdentityFromToken`, np. panel loggera wymaga `mrc-sysadmin`).

### Testy (2026-10-29)

- `RestServicesHelperVerifyContextTest`: 24 testy, wszystkie przechodzą (suma grup i ról, rola cudza odrzucona, `mrc-user` zawsze, reprezentowanie, `currentRole` tylko z grup, pomocnik kontekstu).
- Test REST na dev (14 przypadków, wszystkie zgodne, jar wdrożony o 12:09): `tester` `[mrc-user]` i bez `userRoles` (200); `tester` z cudzą rolą `[mrc-sysadmin]` (403); `admin` `[mrc-user, mrc-sysadmin]` i `[mrc-useradmin]` (200); `admin` z nieznaną rolą (403); `admin` jako `tester` `[mrc-user]` (200) i `[mrc-sysadmin]` (403); `tester` jako `admin`, nieznany użytkownik (403); brak `userName` (403 `username_required`); `currentRole=mrc-user` (200); `currentRole=mrc-sysadmin`, bo to rola a nie grupa (403); `currentRole` spoza `userRoles` (403).
- Nie sprawdzono: ścieżki LDAP (brak dostępu na dev, tylko atrapa realmu w teście jednostkowym), GUI w działającej aplikacji (logowanie formularzem), ponownego testu maskowania pól przez REST z rolami procesowymi lokalnych użytkowników.

### Skutki zmiany

1. **Migracja uprawnień nie jest wymagana.** `userRoles` mogą nadal zawierać role zmapowane (np. `mrc-user`), więc wiersze `igo_da_typeparameterroles` zapisane na nazwy ról działają jak dotąd. Role procesowe lokalnych użytkowników (wiersze `U`) działają także w REST.
2. **`currentRole` z grup.** Klient, który dotąd wysyłał jako `currentRole` samą rolę (nie grupę), dostanie 403. Dla użytkownika lokalnego dozwolone jest `mrc-user`, dla LDAP nazwy jego grup. `currentRole` trafia do pól `createdByRoleName` i `lastModifiedByRoleName`, więc to zmiana widoczna dla integracji. Do wiadomości na wydanie.
3. **Wydajność:** każde żądanie REST z kontekstem odczytuje z realmu grupy i role (z bazy, dla LDAP także z LDAP) oraz, gdy `currentRole` nie jest ustawione, grupę główną. Cache do rozważenia po pomiarze.

### Do zrobienia

- Test GUI w działającej aplikacji (autor lub wspólnie) i ponowny test maskowania pól przez REST (`mask016.sh`).
- Zewnętrzni klienci REST z własnym `context` (czy ich `currentRole` jest grupą), cache ról, SOAP i RMI/CMIS, audyt kontekstu systemowego w `mercury-srv`.
- Notatka na wydanie o punkcie 2 skutków.
