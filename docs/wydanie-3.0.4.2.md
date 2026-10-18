# Wydanie 3.0.4.2 – zmiana formatu XML modelu obiektu MRC

Notatki wydania przygotowane w zadaniu [133 – Swagger, etap 3](../tasks/hgdb/133-Swagger-implementacja/etap-3-zgodnosc-komunikacji-wezlow.md).
Wersja według zasad z `mercury-lib/README.md`: pozycja 4 oznacza zmianę API (SOAP), po której klienci i serwer
muszą zostać zaktualizowani razem.

| Repozytorium | Zmiana wersji |
|---|---|
| `mercury-lib` | `minor_version.txt`: `3.0.4.1` → `3.0.4.2` (skrypt `up_minor_version.sh 2`). POM-y zostają `3.0.4-SNAPSHOT`, wersję ustawia `install.sh` |
| `mercury` | POM-y `3.0.4.1` → `3.0.4.2` (`mvn versions:set`), `mercury.static.version` = `3.0.4.2` |
| `hgdb-client-open` | `mercury.project.version` = `3.0.4.2`. Własny numer klienta: `minor_version.txt` `3.1.4.1` → `3.1.4.2` (POM-y zostają `3.1.4-SNAPSHOT`, wersję ustawia `install.sh`) |

## Zmiana formatu XML (niezgodna wstecznie)

Elementy modelu obiektu MRC są teraz zapisywane w przestrzeni nazw `http://business.dto.ws.hgdb.io/mrcObject`
(zgodnie z `hgdb-mrc-object-3.0.xsd`, `elementFormDefault="qualified"`). Dotyczy klas:

- `DtoMrcList`, `DtoMrcListItems`, `DtoMrcObject`, `DtoMrcProperty`, `DtoMrcPropertyNames`, `DtoPropertyMap`, `DtoPropertyMapEntry`,
- `CaseHeader`, `MrcObjectMetadata`, `MrcCaseHeader` (w `MrcCaseHeader` element `metadata` nazywa się teraz `headerMetadata`).

Skutek: odbiorca ze starą biblioteką pomija elementy kwalifikowane **bez błędu** i dostaje puste obiekty (i odwrotnie).
Dlatego klienci SOAP (`hgdb-client-open`, IBM BPM, integracje) muszą zostać zaktualizowani razem z serwerem.
Test `DtoLegacyXmlCompatibilityTest` (`mercury-lib`) dokumentuje to zachowanie.

Bez zmian: serializacja Javy (HTTP invoker, RMI) — `DtoPropertyMap` zachowuje format i `serialVersionUID`,
a komunikaty JMS to JSON bez klas `Dto*`.

## Kontrola wersji węzłów klastra (`mercury`)

- Heartbeat zawiera wersję biblioteki (`mercury.version`). Węzeł o innej wersji, albo bez wersji (starsze wydanie),
  jest niezgodny: **nie dostaje przekierowanych żądań** (odczyt, zapis, operacje Lucene), a w logu pojawia się ostrzeżenie.
- Wybór mastera indeksu Lucene i statusy `ONLINE`/`OFFLINE` nie zależą od wersji.
- Parametr `mercury.node.version.check` (domyślnie `true`): `false` wyłącza kontrolę (tylko świadome, krótkie okno wdrożenia).
- Poprawiony błąd w `NodeStatusMonitor.registerHeartbeat`: węzły grupy HA nie trafiały na listę partnerów do przekierowania,
  a master Lucene nie ustępował po odebraniu heartbeatu innego mastera. Od tego wydania oba mechanizmy działają
  (zmiana zachowania w klastrach HA — sprawdzić po wdrożeniu).

## Kolejność wdrożenia

1. Zatrzymać ruch klientów SOAP albo uzgodnić okno wdrożenia: klienci i serwer muszą zmienić wersję razem.
2. Zaktualizować **wszystkie** węzły klastra do 3.0.4.2. W oknie wdrożenia węzły o różnych wersjach nie przekierowują
   sobie żądań (log ostrzega o niezgodności).
3. Zaktualizować klientów (`hgdb-client-open` z `mercury.project.version` = 3.0.4.2, klienci IBM BPM).
4. Sprawdzić log: brak ostrzeżeń „Niezgodne wersje” po zakończeniu wdrożenia.

## Stan przygotowania wydania (2026-10-18)

- Zrobione lokalnie: podbicie wersji, `install.sh` w `mercury-lib` (warianty POSTGRESQL, MYSQL, ORACLE, MSSQL; bez testów),
  `mvn install -Dmaven.test.skip=true` w `mercury` (24 moduły) i `hgdb-client-open` (4 moduły). Wszystkie przeszły.
- **Nie zrobione:** testy `mercury` na 3.0.4.2 (ostatni pełny przebieg był na 3.0.4-SNAPSHOT, przed punktem 4 i poprawką
  `registerHeartbeat`), `deploy.sh` (Nexus), tagi git, commity, wypchnięcie zmian.
- Warianty encji innych niż POSTGRESQL zainstalowano do lokalnego `.m2` z `mercury-lib/repo`, ale nie testowano.
