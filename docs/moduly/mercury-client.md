# mercury-client – biblioteki klienckie dla IBM BPM

| | |
|---|---|
| Lokalizacja | `D:\workspace\git\mercury-client` |
| GAV | `io.hgdb.ibmbpm:mercury-client:4.0.4.17-SNAPSHOT` (pom) |
| Wydanie | `4.0.4.17.1` (`minor_version.txt`, tag `4.0.4.17.1`); pakiet `mercury-client-cmd-4.0.4.17.1.zip` |
| Status | **zamrożony** (od 2026-11-11 nie zmieniamy kodu ani pomów) |
| Java | 1.8 wg POM (`java.version`); README wymaga Javy 1.6 / 1.7 i Maven 2.2.1 |
| Opis z POM | Zbiór integracji z IBM BPM i nie tylko do komunikacji z serwerem bazy Mercury. Biblioteki realizowane na zlecenie firmy IBPM S.A. |

Biblioteki klienta Mercury DB używane w aplikacjach procesowych IBM BPM. Działają na
klientach z `hgdb-client-open` (wersja `3.0.3.3.0`, właściwość `hgdb-client.version`). Moduły mają
GAV `io.hgdb.ibmbpm:<moduł>:4.0.4.17-SNAPSHOT`,
chyba że w tabeli podano inaczej.

Projekt nadrzędny dołącza do wszystkich modułów `pro.ibpm:tw4j` oraz biblioteki z
`mercury-lib`: `mercury-core`, `mercury-entities`, `mercury-srv-api`, `mercury-ws-dto-api`,
`mercury-ws-server-api`, `mercury-spring-remoting` (wersja `mercury.project.version`, dziś `3.0.4.16`).

## Moduły

| Moduł | Nazwa | Pliki Java (main / test) | Główne pakiety | Opis |
|---|---|---|---|---|
| `mercury-client-mock` | Mock Client | 57 / 0 | `pro.ibpm.mercury.mock.data`, `.arch`, `.attr`, `.dict` | Generatory danych do testów klienta. |
| `mercury-bpm` | BPM | 302 / 46 | `pro.ibpm.mercury.bpm.mappers`, `pro.ibpm.mercury.bpm.actions` | Główna biblioteka dla IBM BPM. Akcje wywoływane z procesów i mapowanie obiektów Mercury na typy BPM. Od wydania 4.0.4.17.1 zawiera zmiany z gałęzi INEA: pamięci podręczne ostatnio zmienionych obiektów (`bpm.dao.cache`) i klasy `BpmBeforeSave…` w `bpm.dao`. |
| `mercury-bpm-fix` | BPM Fix | 2 / 0 | `pro.ibpm.mercury.bpm.actions` | Elementy usunięte z `mercury-bpm`, zachowane dla zgodności wstecz (`KTMNumberBPMAction`). |
| `mercury-integrations` | BPM Integrations | 45 / 26 | `pro.ibpm.mercury.integrations.bpm`, `pro.ibpm.bpm.utils` | Implementacja integracji IBM BPM z Mercury DB. |
| `mercury-client-cmd` ⚠️ | mercury-client-cmd | 10 / 0 | `pro.ibpm.mercury.cmd` | Polecenia CLI klienta BPM i pakiet instalacji bibliotek klienta na serwerze IBM BPM. Opis w sekcji [mercury-client-cmd](#mercury-client-cmd). **Poza reaktorem**, w IntelliJ zaimportowany jako osobny projekt Maven. |
| `mercury-data` ⚠️ | mercury-data | 1 / 2 | `org.mercury.data` | Szablon Maven („Hello world”). **Poza reaktorem.** Zależy od klientów `hgdb-ws-client-cxf` i `hgdb-multi-client` (`${hgdb-client.version}`), które zastąpiły usunięty moduł `mercury-ws-client-cxf` (w jego katalogu zostały tylko `.gitignore` i `.project`). |

## Zależności wewnętrzne

```mermaid
flowchart LR
    open[(hgdb-client-open:<br/>hgdb-ws-client-cxf,<br/>hgdb-multi-client)]
    mock[mercury-client-mock]
    bpm[mercury-bpm] --> mock
    bpm --> open
    fix[mercury-bpm-fix] --> bpm
    integ[mercury-integrations] --> bpm
    integ --> fix
    integ --> mock
    cmd[mercury-client-cmd] -.-> bpm
    cmd -.-> fix
    cmd -.-> open
    data[mercury-data] -.-> mock
    data -.-> open
```

Linie przerywane oznaczają moduły spoza reaktora.

## mercury-client-cmd

| | |
|---|---|
| GAV | `io.hgdb.ibmbpm:mercury-client-cmd:4.0.4.17-SNAPSHOT` |
| Rodzic | `io.hgdb.ibmbpm:mercury-client:4.0.4.17-SNAPSHOT` (korzeń repozytorium, od 2026-11-11) |
| Budowanie | Osobno, poza reaktorem `mercury-client`: `./install.sh` w katalogu modułu. W IntelliJ zaimportowany jako osobny projekt Maven (`.idea/misc.xml`) |

Moduł ma dwie role:

1. **Narzędzie CLI** (`pro.ibpm.mercury.cmd.Client`) z akcjami `-ep` (kodowanie hasła),
   `-?` (pomoc) i trybem shell. Uruchamia się je skryptami `src/main/bin/startApp.sh` / `.bat`.
   Konfiguracja leży w `src/main/conf`: `client.properties`, `mercury.properties`,
   `lucene.properties`, `logback.xml`.
2. **Pakiet instalacyjny bibliotek klienta** dla serwera IBM BPM (`src/main/build/build-installation.xml`).
   Właściwość `artifactIdsMaps` wskazuje, które biblioteki trafiają do katalogu `Lombardi/lib`
   i w jakim trybie: `B` – BPM, `S` – klient/serwer. Instalator przenosi do classpath BPM tylko biblioteki z mapy.
   Lista jest podzielona na grupy z prefiksem (np. `0_`). Prefiks jest doklejany do nazw bibliotek i służy jako maska: pliki o takich
   nazwach są usuwane z katalogu przed instalacją. Lista obejmuje biblioteki `mercury-lib`,
   `mercury-bpm`, `mercury-bpm-fix`, `hgdb-ws-client-cxf`, `hgdb-multi-client`,
   `hgdb-rmi-server-api` (tranzytywnie z klienta, potrzebny `hgdb-multi-client`), Springa,
   Ehcache, `sccommon` i `tw4j` (poprzednio `scteamworks-log4j`). Skrypt Ant (`rename-artifactIds`, faza
   `package`) zmienia nazwy jarów i wymaga dokładnie jednego jaru na pozycję mapy; zależności
   bierze z `copy-dependencies` (`includeScope=compile`, czyli także `provided`).

Większość zależności ma zakres `provided`, bo w środowisku IBM BPM dostarcza je serwer
albo pakiet instalacyjny. Wyjątkiem są klienci `hgdb-ws-client-cxf`, `hgdb-multi-client`
w wersji `${hgdb-client.version}` i moduły Springa.

Rodzicem wszystkich modułów, także `mercury-client-cmd`, jest korzeń `mercury-client` (`4.0.4.17-SNAPSHOT`).
Do 2026-11-11 `mercury-client-cmd` miał rodzica `3.20.8-SNAPSHOT` z `mercury-client/repo` i `.m2`,
skąd brał m.in. `hgdb-client.version`, `scteamworks-log4j` i `servlet-api.version`. Po ujednoliceniu
te właściwości i zależności są w korzeniu (`hgdb-client.version` = `3.0.3.3.0`).

## Stos technologiczny

IBM BPM 8.6.3 (`tw4j` 8.6.3.21030.2.0.3.20230127), IBM WebSphere 8.5.5.22, Spring 4.1.9.RELEASE,
Apache CXF 2.7.15, Ehcache 2.10.1, POI 3.9, slf4j 1.7.36 + Logback 1.2.13, Jackson 2.5.3, JUnit 4.7,
`sccommon-utils` 1.0.8.4-jdk1.7, `sccommon-cache` 0.0.3-20180724, klient `hgdb-client-open` 3.0.3.3.0
(tranzytywnie `hgdb-rmi-server-api` 3.0.3.2.11), biblioteki Mercury 3.0.4.16.

## Spójność wersji w IBM BPM

W BPM biblioteki tego projektu i SecurityProvider (`bpm-security-provider`) trafiają do jednego
classpath, więc ich zależności muszą być zgodne. SecurityProvider używa `sccommon` 1.0.8.4-jdk1.7
i Ehcache 2.10.1, dlatego `mercury-client` zostaje na starym stosie, a nie na `sccommon` 2.x i
Ehcache 3.x z klienta `hgdb-client-open` 3.1.4.x. Dodatkowo `mercury-client` zależy w czasie
kompilacji od modułu `tw4j` SecurityProvidera (`8.6.3.21030.2.0.3.20230127`).

Znane ryzyko: jary Mercury w paczce mają wersję 3.0.4.16, a klient 3.0.3.3.0 jest zbudowany pod
serwerowe API 3.0.3.x (`hgdb-rmi-server-api` 3.0.3.2.11). Zgodności tych generacji nie weryfikowano.

## Budowanie

Wymagania:

- Biblioteki `mercury-lib` zainstalowane w lokalnym repozytorium projektu
  (w `mercury-lib`: `./install.sh slawas mercury-client deployAll`).
- Dostęp do bibliotek IBM BPM i WebSphere. Są chronione licencją IBM i nie wolno ich
  rozpowszechniać. Ładują je skrypty `01_install_teamworks_libs.sh <wersja>` (biblioteki
  Lombardi/TeamWorks) i `02_install_websphere_libs.sh <wersja>`. Ścieżkę repozytorium
  podaje właściwość `ibm-lib-local-repository`.

```bash
export MAVEN_SETTINGS="--global-settings \"repo/settings.xml\" --settings \"maven/slawas/settings.xml\""
mvnibm $MAVEN_SETTINGS clean install -Dmaven.test.skip
```

- `mvnibm` to Maven 2.2.1 z `JAVA_HOME` ustawionym na IBM Java.
- Biblioteki trafiają do `repo/io/hgdb/ibmbpm`.
- `./install.sh` w korzeniu ustawia wersję z `minor_version.txt` i instaluje pakiet dla `POSTGRESQL`,
  a potem kopiuje pomy do `repo/`.
- `./install.sh` w `mercury-client-cmd` (po zbudowaniu reszty) tworzy `releases/mercury-client-cmd-<wersja>/`
  i archiwum `.zip` z podkatalogiem `lib`.
- Profil `skipInstall` pomija instalację artefaktów.
- `mercury-bpm-fix` jest w reaktorze, ale w `pom.xml` jest oznaczony komentarzem
  „To musi być budowane osobno!!!”.
- Opis budowania jest też w `mercury-client/README.md`.

## Pozostałe katalogi

- `conf/`, `conf-inea/` – przykładowe konfiguracje klienta (`conf-inea` dla wdrożenia INEA).
- `documents/` – dokumentacja.
- `maven-ibm-lib-repo/` – lokalne repozytorium bibliotek IBM.

Źródło: `mercury-client/README.md`, `mercury-client/README.txt`, POM-y projektu.
