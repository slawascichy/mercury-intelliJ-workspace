# [217] Reprezentowanie użytkowników: kto może działać w imieniu kogo

https://github.com/slawascichy/hgdb/issues/217

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

### Do zrobienia

1. ~~Kontrola uprawnień w `CaseViewDefinitionAction.generateView` przed wysłaniem komunikatu JMS (obserwacja 109).~~ Wykonane 2026-10-28, patrz „Naprawa luki zarządzania widokami”.
2. `CaseTypeServicesController` przyjmuje `@RequestBody String`, więc advice go nie obejmuje.
3. Sprawdzić `NodeMonitorRest` (komunikacja między węzłami) i klientów REST wysyłających własny `context` (`mercury-cmd`, serwer Iron POI, IBM BPM): po zmianie ich `context` musi spełniać reguły.
4. Testy automatyczne w repozytorium (obecnie tylko test ręczny na serwerze dev).
5. Ewentualny cache ról (każde żądanie czyta role z bazy).
6. Kanały SOAP i RMI/CMIS (osobna decyzja, razem z kontami technicznymi).
7. Role procesowe w istniejących środowiskach: `mrc-admin` musi być zmapowana użytkownikom, którzy mają ją podawać w `context`.

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
