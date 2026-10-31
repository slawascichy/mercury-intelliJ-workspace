# [49] [CMIS] Implementacja API CMIS

**Status (2026-10-30):** rozpoznanie wykonane i **wszystkie decyzje autora zebrane** (sekcje „Rozpoznanie” i „Decyzje końcowe i plan etapu 1”). Implementacja czeka na zgodę na założenie gałęzi `hgdb-049` w `mercury`. Kolejność autora: 016 (zamknięte), 049, 191. Plan: `plan-najblizszych-dzialan-2026-10-26.md`.


Mercury może robić za repozytorium dokumentów. Trzeba dorobić API CMIS.
Specyfikacja CMIS:

https://github.com/slawascichy/hgdb/blob/master/documents/CMIS/CMIS-v1.1.pdf
https://github.com/slawascichy/hgdb/blob/master/documents/CMIS/cmis-spec-v1.0.pdf
http://docs.oasis-open.org/cmis/CMIS/v1.1/os/schema/CMIS-Messaging.xsd
http://docs.oasis-open.org/cmis/CMIS/v1.1/os/schema/CMIS-Core.xsd
https://www.alfresco.com/whitepaper/cmis

## Komentarze

### Najczęściej wykorzystywane metody

Najczęściej wykorzystywane metody w kontrolkach dokumentowych BPM:

Pobierz folderu według ścieżki
Utwórz folder
Pobierz treść dokumentu
Utwórz dokument
Pobierz dokument
Pobierz elementy potomne typu
Pobierz definicję typu
Szukaj (dowolne zapytanie CMIS)
Usuń dokument
Aktualizuj właściwości dokumentu
Pobierz dokumenty w folderze
Pobierz dokument z repozytorium (Check Out)
Wprowadź dokument (Check In)
Kopiuj dokument

### Koncepcja

Wymaga predefiniowanego typu "Folder"
Katalog plików to Case2Case (NIE Case2SubCase)

### Analiza

OK, przeprowadziłem analizę wykonalności zadania poprzez implementację usług opartych o przykładowy serwer dostarczony z chemistry. Było cięzko, bo okazało się, że użycie MOX'y JAXB w naszym projekcie nie do końca współpracuje z gotowymi bibliotekami chemistry. Poprawiłem implementację bibliotek Apache Chemistry i te implementacje załączyłem do projektu. Wysłałem również propozycję zmiany w projekcie Apache Chemistry (https://lists.apache.org/list.html?dev@chemistry.apache.org:2019-2) - zobaczymy, może zrobią poprawkę i nie będziemy musieli utrzymywać własnych wersji tych bibliotek.

Na razie wstrzymuję prace nad tym zadaniem - muszę dokończyć #4 ale to co zrobiłem było konieczne, by nadać odpowiedni kontekst dla zarządzania plikami, a zadanie #4 właśnie tego dotyczy.

## Stan szkicu w kodzie (2026-10-26, lektura `web.xml` i kodu)

Szkic z analizy wykonalności jest **wpięty w produkcyjny `web.xml`** aplikacji `mercury-ws-app` (`mercury/mercury-ws-app/src/main/webapp/WEB-INF/web.xml`):

- serwlety Chemistry (OpenCMIS `${chemistry.version}` = 1.1.0): `cmisws10` i `cmisws11` (usługi sieciowe, `CmisWebServicesServlet`), `cmisatom10` i `cmisatom11` (`CmisAtomPubServlet`, ścieżki `/atom/*`, `/atom11/*`),
  `cmisbrowser` (`/browser/*`), `cmisendpoints` (`/cmis-endpoints.json`, plik `WEB-INF/cmis-endpoints.json`);
- fabryka usług: `org.mercury.cxf.ws.server.cmis.services.FileShareCmisServiceFactory` (`repository.properties`, wpis `class=`) i `HgdbCmisLifecycleBean` (`webService.xml`);
  dziewięć klas `FileShare*` w pakiecie `org.mercury.cxf.ws.server.cmis.services` to **przykładowe repozytorium plikowe** z Chemistry, a nie repozytorium Mercury;
- `repository.properties` zawiera tylko `class=` (bez `repository.*` i `login.*`), więc repozytorium plikowe nie jest skonfigurowane (przypuszczenie: żądania są odrzucane, nie testowano);
- ochrona: filtr `RemoteBasicAuthFilter` obejmuje `/cmisws10/*` i `/cmisws11/*`; ścieżki `/atom/*`, `/atom11/*`, `/browser/*` i `/cmis-endpoints.json` nie są objęte filtrem ani `security-constraint` (obserwacja 87);
- istnieje moduł klienta `mercury-cmis-client` oraz pliki `cmis10`, `cmis11` w `WEB-INF`.

Wniosek: pierwszym krokiem realizacji jest wymiana repozytorium plikowego na repozytorium oparte o Mercury (typ „Folder”, katalog plików jako `Case2Case`, zgodnie z koncepcją w tym zadaniu)
dla wybranego podzbioru metod, a przed wydaniem trzeba rozstrzygnąć, czy endpointy zostają w WAR-ze bez konfiguracji (obserwacja 87).

## Rozpoznanie (2026-10-30, wersja 2 po uściśleniach autora)

Tylko odczyt kodu. Nic nie zmieniono w kodzie ani w konfiguracji. Przypuszczenia są oznaczone.

### Definicje robocze (autor, zmiana z 2026-10-31)

- **Sprawa**: obiekt sprawy z typem, który ma `isDocumentType=false`.
- **Folder**: (`CmisFolder`) obiekt sprawy z typem, który ma `isDocumentType=false`, tożsamy ze zwykłą sprawą.
- **Dokument**: obiekt sprawy z typem, który ma `isDocumentType=true`. 


### Ustalenia autora (zmiana z 2026-10-31)

1. Folder i Dokument są sprawami, a definicje ich typów mają odpowiednio `isDocumentType=false` (dla folderu) oraz `isDocumentType=true` dla dokumentu.
2. Typy Folder i Dokument trzeba zdefiniować jako predefiniowane, analogicznie jak `BpmBPDInstance` i `BpmTask`.
3. Obsługiwane wiązania i wersje CMIS są już ustalone w `web.xml`.
4. Foldery nie są katalogami na dysku.
5. Drzewo katalogu dokumentów opiera się o `CaseCatalog`.
6. Zapis pliku jest już opracowany (mechanizm plików). Trzeba uwzględnić rozproszenie plików na węzłach klastra, a identyfikatorem pliku jest `igo_adm_files_index.id`.
7. (odpowiedź na pytanie 1) Podstawowe typy to `CmisFolder` i `CmisDocument` (`TypeCode.name`), rodzaj typu (`TypeKind`) w rodzaju `BaseDocuments`, bo później będą inne typy dokumentów jak w repozytoriach Alfresco i FileNet. Typy ładowane z plików CSV, a nie przez kod jak BPM, bo dane procesowe BPM są konwertowane do spraw tylko przy odpowiedniej opcji systemowej. Pola typów: autor zdaje się na moją wiedzę o FileNet i Alfresco.
8. (odpowiedź na pytanie 4) CMIS ma korzystać z mechanizmów uprawnień spraw. `CaseDocument` jest łącznikiem między światem spraw i światem dokumentów. To nowa funkcjonalność: repozytorium dokumentów oparte o dotychczasowe mechanizmy spraw.
9. (odpowiedź na pytanie 8) Uwierzytelnianie Basic i OAuth, z SSO między dostępem do spraw i do dokumentów.
10. Tabela proponowanych pól typów jest dobrym punktem wyjścia (odpowiedź „Tak”).
11. Plik czytamy w kontekście systemowym po sprawdzeniu uprawnień sprawy (omija `checkPrivileges` z rolą twórcy).
12. `CN001RequiredNodeNotAvailableException` wystarcza w pierwszym wydaniu: to czasowa niedostępność strumienia pliku.
13. Mount point to identyfikator repozytorium. Foldery to obiekty spraw z typem `isDocumentType=false` (zmiana z 2026-10-31; wcześniej `true`); wewnętrznie nic się nie zmienia, wykorzystujemy istniejące mechanizmy; przy prezentacji `#` zamieniamy na `/`.
14. Dla spraw typu dokument powstaje indeks Lucene w drzewie „Document”. CMIS-QL tłumaczymy na Lucene, na początek podstawowe funkcje niezbędne do wyszukiwania dokumentów.
15. Role takie same jak w sprawach.
16. Limit pliku konfigurowalny w `mercury.properties`, domyślnie 10 MB.
17. Po wymianie szkicu endpointy CMIS zostają w WAR-ze domyślnie włączone.
18. `Source` ładowane z kontekstu (jak przy sprawach).

### Co już jest w kodzie

| Element | Gdzie | Co to jest |
|---|---|---|
| Szkic serwera CMIS | `mercury-ws-app`, pakiet `org.mercury.cxf.ws.server.cmis.services` (9 klas, `FileShareRepository` ma 2232 linie) | Przykładowe repozytorium plikowe z Chemistry (OpenCMIS 1.1.0), nie repozytorium Mercury. Fabryka `FileShareCmisServiceFactory`, `HgdbCmisLifecycleBean`. Wpięcie w `web.xml` i luka ochrony: sekcja „Stan szkicu w kodzie” i obserwacja 87 |
| Wiązania w `web.xml` | `cmisws10`, `cmisws11` (SOAP), `cmisatom10` (`/atom/*`), `cmisatom11` (`/atom11/*`), `cmisbrowser` (`/browser/*`), `/cmis-endpoints.json` | Wiązania i wersje CMIS 1.0 i 1.1 są gotowe. Wiązania Chemistry korzystają ze wspólnej fabryki usługi (`CmisService`), więc praca polega na jednej implementacji opartej o Mercury, a nie na osobnych wiązaniach (przypuszczenie, zgodne z architekturą OpenCMIS) |
| Zależności | `mercury/pom.xml` (`chemistry.version` 1.1.0, komentarz o zgodności z CXF), `mercury-ws-app/pom.xml` (`chemistry-opencmis-server-bindings-war`, MOXy 2.7.3) | Analiza z 2019 (commit `01db9ab24`) notuje kłopoty z MOXy JAXB razem z Chemistry |
| **Klient** CMIS (inna rzecz niż serwer) | moduł `mercury-cmis-client`, użycie w `TypeCaseLogic` (`synchronizationWithCMIS`, `cmis.integration`) | Mercury jako **konsument** zewnętrznego repozytorium (Archiwum Elektroniczne). Zadanie 49 to odwrotny kierunek |
| Metadane CMIS w modelu | `MType.cmisTypeName`, `MType.isDocumentType`, `MTypeParam.cmisFieldName` | Miejsca na mapowanie typów i pól Mercury na typy i właściwości CMIS |
| Hierarchia | `CaseCatalog` (`IGO_DA_CASE2CASE`): `PATH` (do 1024 znaków), `DEPTH`, `MOUNT_POINT`, `parent`, `child`; `ICase2CaseLogic` | Drzewo folderów i dokumentów (ustalenie 5) |
| Treść plików | mechanizm plików (sekcja niżej) | Pliki na dysku węzła, indeks `IGO_ADM_FILES_INDEX` |
| `CaseDocument` | `IGO_DA_CASEDOCUMENTS` | Dotychczas metadane dokumentów z **zewnętrznego** repozytorium (model Alfresco/AE); dla CMIS łącznik świata spraw i dokumentów (ustalenie 8); sama treść jest w mechanizmie plików |

### Typy predefiniowane: dwa istniejące wzorce

| Wzorzec | Gdzie | Jak działa |
|---|---|---|
| Statyczne pliki CSV | `mercury-entities-ids`, `org/mercury/predefined/attr/*.csv` (`TypeCase.csv`, `TypeCode.csv`, `TypeParam.csv`, `ParamDefinition.csv`, …), loadery `*Loader`, wyliczenie `TypeCaseName` | Typy z ujemnymi identyfikatorami (kalendarz: `CalendarUserDefinition`, `CalendarUserEvent`, …, `MrcUnknownBusinessObject`), ładowane przy starcie |
| Tworzenie przez kod przy pierwszym użyciu | `BpmDataTransformationHelperService.loadBpmInstanceTypeCase` i odpowiednik dla `BpmTask` (stałe: nazwa typu, wersja typu, nazwa pola klucza `bpmProcessInstanceId` i `bpmTaskId`, rodzaj typu `BpmProcess`) | Szuka typu po nazwie i wersji; jeśli brak, tworzy `TypeKind`, `TypeCode`, `TypeCase`, `ParamDefinition` i `TypeParam` i zapisuje. Blokada `synchronized` jest lokalna, a w kodzie jest `FIXME` o wyścigach w klastrze |

Decyzja autora (7): typy `CmisFolder` i `CmisDocument` idą **pierwszym wzorcem (CSV)**. Do dodania (przypuszczenie co do zakresu, na podstawie istniejących plików):

| Plik (`mercury-entities-ids`, `org/mercury/predefined/…`) | Wpisy |
|---|---|
| `dict/TypeKind.csv` (dziś: `Document`, `FixedAsset`, `Employee`, `Calendar`, `Generated`) | nowy rodzaj (np. `BaseDocuments`) |
| `attr/TypeCode.csv` | `CmisFolder`, `CmisDocument` |
| `attr/TypeCase.csv` (ujemne identyfikatory; dziś -1 do -5) | dwa typy, np. -6 i -7, wersja 1, rodzaj `BaseDocuments`, flaga dokumentowa; kolumny pliku: `ID;NAME;VERSION;DESCRIPTION;IS_EDITABLE;AE_TYPE_CODE;IS_ACTIVE;KIND;IS_LATEST_VERSION;FROM_DATE;TO_DATE` (flagi `isDocumentType` plik dziś nie ma: do dopisania w loaderze i CSV) |
| `attr/ParamDefinition.csv`, `attr/TypeParam.csv` | definicje i pola obu typów |
| `attr/Type2Type.csv` | **nie używamy** (korekta 2026-10-30): to hierarchia typów spraw zależnych (Case2SubCase), a katalog dokumentów to Case2Case (`CaseCatalog`); dozwolone typy potomne folderu wyznacza usługa CMIS |
| `TypeCaseName` (wyliczenie) | dwie nowe nazwy |

Konsekwencja: typy powstają przy starcie, bez wyścigów klastrowych (problem `FIXME` przy BPM nie dotyczy tego wzorca).

Skutki flagi `isDocumentType=true`: wynik sprawdzenia synchronizacji z zewnętrznym CMIS w sekcji „Synchronizacja z zewnętrznym CMIS: wynik sprawdzenia kodu”. Flaga steruje `getAllDocumentTypes`, zapytaniami `QgetDocumentTypesOnly` i `QgetCaseTypesOnly` oraz propagacją zmian typów (`TypeCaseChange`); dla typów domyślnie jest `false` (`TypeCaseDAO`).

### Mechanizm plików (zweryfikowane w kodzie)

Źródła: `mercury-ws-app`, `pro.ibpm.mercury.app.actions.file` (`SystemFileUpload*`, `SystemFileDownload*`), `FileIndex`, `IFileIndexLogicInternal`, `FileIndexLogic`, `FileNameUtils`.

| Cecha | Stan |
|---|---|
| Gdzie leży treść | na dysku węzła, w `targetDir` (`mercury.upload.file.target`, domyślnie `$CATALINA_HOME/tmpFiles`) |
| Indeks | `IGO_ADM_FILES_INDEX`: `ID`, `NODE_NAME`, `TARGET_DIR`, `FILE_NAME`, `FILE_SIZE`, `EXISTS`, `CONTROL_MD5`, daty i użytkownicy; unikalne `(NODE_NAME, TARGET_DIR, FILE_NAME)` oraz `(TARGET_DIR, FILE_NAME)` |
| Historia | `FileIndexHistoryStream`: zmiany sumy kontrolnej, pobrania i zmiana flagi `EXISTS`; `loadFileHistory` |
| Implementacje | jednowęzłowa (`mercury-srv`) i klastrowa (`mercury-srv-slave`, przekazuje operacje do węzła właściciela przez RMI); szczegóły w następnej sekcji |
| API logiki | `saveFile(context, targetDir, fileName, byte[] content, override)`, `copy2OutputStream(context, fileIndex, OutputStream)`, `deleteFile`, `findFileByFileName`, `findByNodeName`, `findFilesBySumControl`, `loadFileHistory` |
| REST | `POST /files/uploadSystemFile` (multipart `fileToUpload`), `/files/downloadSystemFile/{name}.{ext}`; typ MIME zgadywany z nazwy |
| Uprawnienia | `checkPrivileges`: rola użytkownika musi być równa roli twórcy pliku (obserwacja 121); sprawy i typy mają osobny model uprawnień |
| Nazwy | `FileNameUtils.checkFileName`: tylko litery, cyfry, podkreślenie, spacje i kropka; wynik to sama nazwa (przestrzeń nazw płaska) |

### Rozproszenie plików w klastrze (zweryfikowane w kodzie; korekta po przeglądzie 2026-10-30)

Są dwie implementacje `IFileIndexLogicInternal`: jednowęzłowa (`mercury-srv`, `org.mercury.single.node.logic.data.FileIndexLogic`) i klastrowa (`mercury-srv-slave`, `org.mercury.cluster.node.logic.data.FileIndexLogic`, podklasa jednowęzłowej). Kontekst klastrowy skanuje `org.mercury.cluster.node` (`cluster-configuration.xml`). Moje wcześniejsze twierdzenie o ustawianiu `EXISTS=false` przy pobraniu na obcym węźle dotyczyło wyłącznie wariantu jednowęzłowego; w klastrze plik trafia do właściciela automatycznie.

| Element | Jak działa |
|---|---|
| Kto jest właścicielem | `FileIndex.nodeName` w `IGO_ADM_FILES_INDEX`. Nowy plik dostaje nazwę węzła, który przyjął żądanie zapisu (`saveFile`: `fileIndex.setNodeName(NodeConfigProperties.getNodeName())`) |
| Wybór lokalnie czy zdalnie | `ClusterFileUtils.checkLocalExcecution(context, nodeName)`: lokalnie, gdy to ten węzeł albo `mercury.node.isClustered` jest wyłączone; w przeciwnym razie czyta status węzła z `NodeStatusMonitor` i ustawia w kontekście adres RMI (`RMI_PROTOCOL` + `hostName` + port RMI) i nazwę węzła |
| Węzeł niedostępny | brak statusu albo `ServerStatus.OFFLINE` -> `CN001RequiredNodeNotAvailableException` (to jest sytuacja awaryjna, o której mówił autor) |
| Pobranie z innego węzła | `copy2OutputStream` -> `IClientFileTransferRMI.getInputStream` i `copy` (strumień po RMI); `FileNotFoundException` z węzła właściciela ustawia `EXISTS=false` i rzuca `FI001FileNotExists` (czyli plik naprawdę zniknął z dysku właściciela) |
| Zapis na inny węzeł | `saveFile` dla istniejącego wpisu z innym `nodeName` (nadpisanie): `getOutputStream` i `copy` po RMI; zapis nowego pliku zawsze jest lokalny |
| Usunięcie | `deleteFile` -> lokalnie albo `IClientFileTransferRMI.deleteFile`; po sukcesie `EXISTS=false` i wpis w historii |
| Strona serwera RMI | `FileTransferRMI` (`mercury-ws-server`): `getInputStream`, `getOutputStream`, `deleteFile` po pełnej ścieżce pliku, strumienie `FileInputStreamDto` i `FileOutputStreamDto` |
| Użycia poza REST plików | `FileResourceProvider` (klastrowy) odczytuje zasób po `FileIndex` i zdalnie przez RMI (np. szablony Excel); sekretarze raportów |
| Redundancja | brak: wpis ma jeden `nodeName`, a kopii na drugim węźle nie ma. Para węzłów z kopią plików (propozycja autora) wymagałaby dopracowania i nie jest dziś zaimplementowana |

Wnioski dla CMIS (przypuszczenia):

- Wywołując `copy2OutputStream` i `saveFile` z logiki klastrowej nie trzeba pisać własnego przekazywania żądania. Wystarczy użyć `IFileIndexLogicInternal` i obsłużyć wyjątki `CN001RequiredNodeNotAvailableException` (węzeł niedostępny) i `FI001FileNotExists` (brak pliku).
- Identyfikator pliku to `FileIndex.id` (ustalenie 6). Sprawa dokumentowa przechowuje go w polu tekstowym.
- Nazwa na dysku powinna wynikać z identyfikatora, bo `(TARGET_DIR, FILE_NAME)` jest unikalne globalnie; nazwa CMIS (`cmis:name`) to metadana sprawy.
- **Uprawnienia pliku są inne niż uprawnienia sprawy:** `checkPrivileges` dopuszcza operację tylko wtedy, gdy rola użytkownika jest równa roli, w której plik utworzono (`createdByRoleName`; zmienna `modifierRole` też bierze `createdByRoleName`, prawdopodobnie błąd kopiowania). Dla CMIS dostęp do treści powinien wynikać z uprawnień sprawy (typ i pola), a nie z roli twórcy pliku.
- Zapis plików przyjmuje `byte[]` i zawsze tworzy plik na węźle przyjmującym żądanie.

### `CaseDocument` jako łącznik świata spraw i dokumentów (zweryfikowane w kodzie, wnioski jako przypuszczenia)

Wcześniej opisałem `CaseDocument` jako metadane zewnętrznego repozytorium. To prawda dla dotychczasowego użycia (Archiwum Elektroniczne), ale model pasuje do CMIS, a autor przyjął go jako łącznik (ustalenie 8).

| Pole `CaseDocument` | Znaczenie dziś | Odpowiednik CMIS i uwagi |
|---|---|---|
| `id` (`CaseDocumentPK`): `caseObj` (`CASE_ID`), `objectId` (`AE_OBJECT_ID`), `versionSeriesId` | sprawa biznesowa, identyfikator wersji dokumentu, seria wersji (komentarz w kodzie: „wersją jest objectId”) | `cmis:objectId` (każda wersja ma własny identyfikator), `cmis:versionSeriesId` |
| `contentStreamId` | identyfikator pliku w AE | `cmis:contentStreamId`; tu `FileIndex.id` (ustalenie 6) |
| `versionLabel`, `isLatestVersion` | etykieta wersji, czy najnowsza w serii | `cmis:versionLabel`, `cmis:isLatestVersion` |
| `type` (`DOC_TYPE_ID`, `TypeCase`, wymagane) | typ dokumentu | `cmis:objectTypeId` (`CmisDocument` i późniejsze typy dokumentów) |
| `source` (`SOURCE_VALUE`, wymagane), `initStatus` (`INIT_STATUS`, wymagane) | słowniki `IGO_DI_SOURCES`, `IGO_DI_INITSTATUSES` | brak odpowiednika; dla CMIS potrzebne wartości domyślne (do ustalenia) |
| `isActive`, `isValid`, `isReadable` | stan dokumentu | `isValid` ~ komplet danych; reszta bez odpowiednika |
| `isInput`, `isRoot`, `groupingCode`, `groupSize` | grupowanie dokumentów (np. e-mail i załączniki) | brak odpowiednika, można zostawić puste |
| `author`, `receivedDate`, `receiver`, `receiverDW`, `subject` | metadane z AE | `cm:author`, `subject` ~ `cmis:description`/tytuł; reszta puste |
| `createDate`, `createdBy`, `lastModifyDate`, `lastModifiedBy`, `modifyComment` | historia | `cmis:creationDate`, `cmis:createdBy`, `cmis:lastModificationDate`, `cmis:lastModifiedBy`, `cmis:checkinComment` (po części) |

Gotowa infrastruktura wokół `CaseDocument`: encja z DAO (`CaseDocumentDAO`, wariant archiwalny `ArchCaseDocument*`), logika `CaseDocumentLogic` z operacjami na seriach wersji (`findLastVersionByCaseAndVerionSeries`, `findAllVersionsByCaseAndVerionSeries`, `findAllVersionsByCaseId`, `findLastVersionsByCaseId`, `findAllByVersionSeries`, `findByObjectId`), mapper Lucene (`CaseDocumentMapper`, szukanie), usługi `CaseDocumentAction` (SOAP/RMI) w `mercury-ws-server` i `CaseDocumentInitializer`, klient w `hgdb-client-open`. To znaczy, że **wersjonowanie CMIS (seria wersji, najnowsza wersja, etykieta) można oprzeć na `CaseDocument`, a nie na wersjach spraw** (przypuszczenie; to odpowiada na dawne pytanie 6).

### Model `CaseDocument`: dwie koncepcje i rekomendacja

Autor opisał dwa warianty:

- **Wariant A (pierwotny):** `CaseDocument` łączy **sprawę** (`caseObj`, typ `isDocumentType=false`) z **dokumentem**. `objectId` to identyfikator wersji dokumentu (sprawy z typem dokumentowym), a `versionSeriesId` to jej wersja główna (`rootVersionId`).
- **Wariant B:** `CaseDocument` reprezentuje obiekt repozytorium dokumentów, a wskazane pola wskazują wersję zawartości pliku.

**Rekomendacja: wariant A** (przypuszczenie oparte na kodzie; decyzja należy do autora). Uzasadnienie:

1. **Wersje dokumentu to już wersje spraw.** `Case` ma `previousVersionId` i `rootVersionId`, a `CaseRootVersion` wskazuje ostatnią wersję (`lastVersion`). `ChangeCaseVersionScenario` pokazuje ręczną zmianę wersji: kopia sprawy z `previousVersionId` poprzedniej, a stara dostaje status `Z`. Wersja dokumentu CMIS (każda wersja ma własny `cmis:objectId`, wspólny `cmis:versionSeriesId`) odpowiada więc łańcuchowi wersji sprawy: `objectId` = id sprawy-wersji, `versionSeriesId` = `rootVersionId`.
2. **Drzewo wskazuje wersje główne.** `CaseCatalog.parent` i `child` to `CaseRootVersion`, więc kolejne wersje dokumentu zostają na swoim miejscu w drzewie bez zmian w katalogu.
3. **Wiersze `CaseDocument` powstają tylko dla powiązań ze sprawami biznesowymi** (jeden dokument może być podpięty do wielu spraw: kilka wierszy z tym samym `objectId`). Dokument leżący wyłącznie w drzewie folderów nie potrzebuje wiersza.
4. **Istniejące zapytania zakładają wariant A:** w `Case` są zapytania typu `SELECT cd.id.caseObj.id FROM CaseDocument cd WHERE cd.isLatestVersion = true AND cd.id.versionSeriesId = :versionSeriesId` (sprawy mające najnowszą wersję dokumentu), a `searchInDB` przyjmuje `objectId` i `versionSeriesId`. Wariant B zmieniłby znaczenie `caseObj` i zepsuł klientów (BPM, `hgdb-client-open`).

Konsekwencje wariantu A dla CMIS:

- Identyfikator pliku (`FileIndex.id`) i etykieta wersji muszą być w **samym dokumencie** (polach typu `CmisDocument`), bo dokument bez powiązania ze sprawą nie ma wiersza `CaseDocument`. `CaseDocument.contentStreamId` powtarza ten identyfikator tylko dla powiązanych dokumentów (denormalizacja).
- `cmis:isLatestVersion` i serię wersji wyznacza `CaseRootVersion.lastVersion`, a nie flaga w wierszach powiązań. Flaga `CaseDocument.isLatestVersion` musi być utrzymywana przy zmianie wersji dla wierszy powiązań (to robi `CaseDocumentLogic`; do sprawdzenia przy implementacji).
- Wymagane pola `source` i `initStatus` w wierszu powiązania: `source` z kontekstu żądania (ustalenie 18; `CaseBusinessSupport` bierze `context.getSourceOfRequest()` dla grup), `initStatus` wymaga wartości domyślnej (komentarz w kodzie: „czy dokument rozpoczął sprawę”; wartości słownika `IGO_DI_INITSTATUSES` nie ustalono).
- Wariant B nie jest konieczny: „wersja zawartości pliku” to po prostu plik wersji (każda wersja dokumentu ma swój `FileIndex.id`).

### Cykl życia dokumentu (propozycja)

Sprawa ma status procesu `Case.State`: `A` aktywna, `O` odłożona, `N` zakończona, `Z` przerwana (zasady zmiany wersji w `ChangeCaseVersionScenario`: stara wersja `Z`, nowa `A`). `InitStatus` dotyczy czegoś innego (czy dokument rozpoczął sprawę) i nie jest cyklem życia.

Proponuję **ponownie użyć `Case.State`** dla dokumentów, bez nowego słownika:

| Status | Znaczenie dla dokumentu | CMIS |
|---|---|---|
| `A` | aktualna wersja (opublikowana) | `isLatestVersion=true`, nie jest PWC |
| `O` | wersja robocza, czyli kopia robocza po `checkOut` (jeszcze nie zapisana) | `isPrivateWorkingCopy=true`, `isVersionSeriesCheckedOut=true` |
| `Z` | wersja zastąpiona nowszą | `isLatestVersion=false` |
| `N` | wycofana (opcjonalnie): nieaktualna merytorycznie, nadal czytelna | (opcjonalnie) |

Przejścia: `createDocument` -> `A` (wersja 1.0); `checkOut` -> nowa wersja `O` (kopia pliku i pól); `checkIn` -> `O` zmienia się w `A`, poprzednia `A` w `Z`, nowy `versionLabel`; `cancelCheckOut` -> usunięcie wersji `O`; `deleteObject` -> archiwizacja (istniejący mechanizm archiwizacji przy usuwaniu, brak osobnego statusu). Folder używa tylko `A`.

### Synchronizacja z zewnętrznym CMIS: wynik sprawdzenia kodu

- Importowane typy **są typami dokumentowymi**: `PropertyDefinitionCMIS.prepareDocumentType` (moduł `mercury-cmis-client`) tworzy `TypeCase` z `isDocumentType=true`, rodzajem `Document` (`TypeKindLogicHelper.loadDocument`), `isEditable=false`, `cmisTypeName` i powiązaniem ze źródłem (`TypeCase2SourceOfObject`); dotyczy tylko obiektów `DocumentType` zewnętrznego repozytorium.
- `synchronizationWithCMIS` dodaje i aktualizuje typy po kodzie (wersjonowanie typu), działa tylko przy `cmis.integration=true`. W przejrzanym fragmencie nie widać dezaktywacji typów, których zewnętrzne repozytorium nie zwraca.
- Wniosek (przypuszczenie): `CmisFolder` i `CmisDocument` (rodzaj `BaseDocuments`, kody inne niż importowane) współistnieją z importowanymi; `getAllDocumentTypes` zwróci obie grupy. Różnią się rodzajem i flagą edycji, więc da się je odróżnić.

### Ścieżki i nazwy (zweryfikowane w kodzie, wnioski jako przypuszczenia)

- `CaseCatalog.path` powstaje z **identyfikatorów** (`CatalogHelper.buildSimplePath(parentId, childId, mountPoint)`), a mount point to osobna encja `Case2CaseMountPoint` (ustalenie 13: identyfikator repozytorium). Po zamianie `#` na `/` powstaje ścieżka z identyfikatorów.
- CMIS posługuje się ścieżkami z **nazw**: `getObjectByPath("/Umowy/2026/umowa.pdf")` i `cmis:path` folderu. Konieczne jest więc rozwiązywanie nazw: od korzenia repozytorium po poziomach, po `cmis:name` dziecka. Wymaga to **unikalności `cmis:name` w obrębie folderu** (CMIS rzuca `nameConstraintViolation` przy duplikacie), egzekwowanej przy tworzeniu i zmianie nazwy.
- Przy odczycie `cmis:path` trzeba zamienić identyfikatory na nazwy (po jednym poziomie, z pamięci podręcznej).
- Operacje na poddrzewie (`IN_TREE`, usuwanie folderu z zawartością) mogą korzystać z `getAllByPathStartsWith` (istnieje w `Case2CaseLogic`).

### Wyszukiwanie: indeks „Document” i CMIS-QL (etap 2)

- **Zastąpione wariantem B (2026-10-31):** osobny indeks „Document” opisany niżej został porzucony. Sprawy i dokumenty są w jednym indeksie „Case”, dokument ma pole `mrc_typeIsDocumentType`, a wyszukiwanie zawęża `DocumentTypeFilter` (sprawy domyślnie, dokumenty na żądanie). Szczegóły w sekcjach „Wariant B” i „Realizacja: wariant B” na końcu dokumentu. Opis poniżej zostaje jako zapis rozważanej wersji.
- Indeksy Lucene są dziś nazwane od encji (`Case`, `CaseDocument`, `Comment`, …); „Case” obsługuje `CaseMapper`. Nowy indeks „Document” dla dokumentów (ustalenie 14) wymaga: kierowania spraw z typem `isDocumentType=true` do osobnego indeksu zamiast „Case” (do zbadania w `CaseMapper` i indeksatorach), przebudowy po wdrożeniu i zgodności z modelem wyszukiwania 3.0. Zdecyduj, czy indeks ma powstać już w etapie 1, żeby dokumenty były indeksowane od początku (przypuszczenie: unikniemy późniejszej przebudowy).
- Proponowany podzbiór CMIS-QL na start: `SELECT` z `cmis:document` i `cmis:folder` (oraz typów pochodnych), `WHERE` z `=`, `<>`, `<`, `>`, `<=`, `>=`, `LIKE`, `IN`, `IS NULL`, `AND`, `OR`, `NOT`, `IN_FOLDER(id)`, `IN_TREE(id)`, `ORDER BY`; bez `JOIN`; `CONTAINS` tylko na metadanych (treść plików nie jest indeksowana, przypuszczenie).

### Limit rozmiaru pliku

- `CmisServiceFactory` (OpenCMIS 1.1.0, sprawdzone w jarze) ma wprost `getMaxContentSize()`, `getMemoryThreshold()` i `getTempDirectory()`, więc limit wchodzi w kontrakt fabryki. Nowa właściwość w `mercury.properties` (np. `mercury.cmis.maxContentSize`, domyślnie 10485760) zasila `getMaxContentSize()`.
- `web.xml` ma dziś `multipart-config`: `max-file-size` 157286400 (150 MB) i `max-request-size` 41943040 (40 MB), czyli wartości niespójne (żądanie mniejsze niż plik); dotyczą REST plików, nie CMIS.
- `saveFile` przyjmuje `byte[]`, więc limit 10 MB jest też limitem pamięci na żądanie.

### Proponowane pola typów `CmisFolder` i `CmisDocument` (z mojej wiedzy o CMIS 1.1, Alfresco i FileNet; nie zweryfikowane w środowiskach tych systemów)

Właściwości systemowe CMIS (identyfikator, daty i użytkownicy utworzenia i modyfikacji, typ, wersja, ścieżka, rodzic) wynikają z nagłówka sprawy, `CaseCatalog` i `CaseDocument`, więc nie są polami typu. Pola typu to właściwości, które edytuje użytkownik:

| Pole typu | `CmisFolder` | `CmisDocument` | CMIS | Alfresco | FileNet |
|---|---|---|---|---|---|
| nazwa | tak, wymagane | tak, wymagane | `cmis:name` | `cm:name` | `FolderName` / `DocumentTitle` |
| opis | tak | tak | `cmis:description` | `cm:description` | (własna właściwość) |
| tytuł | tak | tak | (własna) | `cm:title` | `DocumentTitle` |
| autor | | tak | (własna) | `cm:author` | (własna) |
| typ MIME | | tak | `cmis:contentStreamMimeType` | `cm:content` (mimetype) | `MimeType` |
| nazwa pliku | | tak | `cmis:contentStreamFileName` | `cm:name` | (element treści) |
| rozmiar treści | | tak (z `FileIndex.fileSize`) | `cmis:contentStreamLength` | `cm:content` (size) | `ContentSize` |
| komentarz do zapisu wersji | | tak | `cmis:checkinComment` | `cm:versionLabel` / komentarz | (komentarz wersji) |
| czy główna wersja | | tak | `cmis:isMajorVersion` | wersje `1.0` i `1.1` | `MajorVersionNumber` / `MinorVersionNumber` |
| zablokowany do edycji (check-out) | | tak (stan) | `cmis:isVersionSeriesCheckedOut`, `cmis:versionSeriesCheckedOutBy` | `cm:lockable` | `Reservation` |
| niezmienny | | tak | `cmis:isImmutable` | | |

Sugestia: pola `cmis:*` oddzielić od własnych właściwości (np. tytuł i autor) przez `cmisFieldName` w `TypeParam`, a późniejsze typy dokumentów (Alfresco, FileNet) dziedziczyłyby po `CmisDocument` przez `Type2Type`.

### Uwierzytelnianie: stan i propozycja (zweryfikowane w kodzie, wnioski jako przypuszczenia)

- Filtr `RemoteBasicAuthFilter` (dziś na `/remoting/*`, `/cmisws10/*`, `/cmisws11/*`) **nie uwierzytelnia użytkowników**: porównuje nagłówek Basic ze stałą parą identyfikator i token z konfiguracji (`WS_SECURITY_IDENTIFIER_PROP`, `WS_SECURITY_TOKEN_PROP`) i ustawia stałego `REMOTE_USER`. Nie nadaje się do CMIS użytkowników.
- `OAuthFilter` chroni ścieżki z wzorca konfiguracji (`/rest/service/**` w `mrc_ldap_oauth_config`), odczytuje token z żądania (`OAuthFactory.getToken`) i sprawdza zakres (role). Ścieżek CMIS (`/atom/**`, `/atom11/**`, `/browser/**`, `/cmisws10/**`, `/cmisws11/**`) w tej konfiguracji nie ma.
- Propozycja (SSO, ustalenie 9): jeden filtr przed serwletami CMIS, który (a) przyjmuje `Authorization: Bearer` i weryfikuje token tak jak `OAuthFilter`, (b) przyjmuje `Authorization: Basic` użytkownika i weryfikuje go w tym samym realmie co logowanie hasłem do tokenu, (c) w obu przypadkach buduje ten sam `Context` (użytkownik, role z modelu zadania 217), który trafia do implementacji `CmisService` przez `CallContext`. Dzięki temu jeden token działa dla spraw i dokumentów. Do ustalenia: wzorce ścieżek CMIS w konfiguracji OAuth i zakresy (role) dostępu.

### Odwzorowanie 14 metod z opisu zadania na usługi CMIS (propozycja)

| Metoda z opisu | Usługa CMIS | Podstawa w Mercury |
|---|---|---|
| Pobierz folder według ścieżki | `getObjectByPath` | rozwiązywanie nazw po poziomach drzewa `CaseCatalog` (ścieżka z nazw; sekcja „Ścieżki i nazwy”) |
| Utwórz folder | `createFolder` | sprawa typu Folder + wpis `CaseCatalog` |
| Pobierz treść dokumentu | `getContentStream` | `FileIndex` z pola sprawy, `copy2OutputStream` (klaster: automatycznie przez RMI) |
| Utwórz dokument | `createDocument` | sprawa typu Dokument + `saveFile` + wpis `CaseCatalog` |
| Pobierz dokument | `getObject` | sprawa |
| Pobierz elementy potomne typu | `getTypeChildren` | typy z `isDocumentType`, `cmisTypeName` |
| Pobierz definicję typu | `getTypeDefinition` | `MType`, `MTypeParam` (`cmisFieldName`) |
| Szukaj (dowolne zapytanie CMIS) | `query` (CMIS-QL) | **najdroższe**: tłumaczenie CMIS-QL na zapytania Mercury |
| Usuń dokument | `deleteObject` | usunięcie sprawy, wpisu katalogu i pliku (`deleteFile`, klaster: automatycznie przez RMI) |
| Aktualizuj właściwości dokumentu | `updateProperties` | pola sprawy |
| Pobierz dokumenty w folderze | `getChildren` | `ICase2CaseLogic` |
| Check Out, Check In | `checkOut`, `checkIn` | seria wersji w `CaseDocument` (`versionSeriesId`, `versionLabel`, `isLatestVersion`; przypuszczenie, do potwierdzenia) |
| Kopiuj dokument | `createDocumentFromSource` | nowa sprawa + kopia pliku (odczyt z węzła źródłowego, zapis na bieżącym) |

### Proponowane etapy (do zatwierdzenia)

| Etap | Zakres |
|---|---|
| 1 | Typy Folder i Dokument (predefiniowane, bezpieczne dla klastra), zastąpienie `FileShare*` implementacją opartą o Mercury; informacje o repozytorium, `getTypeDefinition`, `getTypeChildren`, `getObject`, `getObjectByPath`, `getChildren`, `createFolder`, `createDocument`, `getContentStream`, `updateProperties`, `deleteObject`; użycie mechanizmu plików (klaster: przekazywanie przez RMI jest już w logice); uwierzytelnianie i ochrona wszystkich ścieżek; limit rozmiaru pliku; reguła unikalności `cmis:name` w folderze; cykl życia (`A`, `O`, `Z`) |
| 2 | `query` (CMIS-QL) |
| 3 | `checkOut`, `checkIn`, `createDocumentFromSource` |

### Ryzyka (część to przypuszczenia)

- Awaria węzła właściciela: pliki z tego węzła są niedostępne (`CN001RequiredNodeNotAvailableException`); redundancji nie ma. Mapowanie na błędy CMIS wymaga decyzji.
- Uprawnienia pliku (rola twórcy) nie pokrywają się z uprawnieniami sprawy, więc zwykłe użycie `checkPrivileges` odmówi dostępu użytkownikom z uprawnieniem do sprawy, ale inną rolą.
- Zapis pliku przyjmuje `byte[]`, więc duże pliki obciążą pamięć węzła.
- Konflikt MOXy 2.7.3 z Chemistry 1.1.0 (notatka z 2019); przy zadaniu 191 (Java 17) Chemistry 1.1.0 może wymagać aktualizacji.
- Ścieżki `/atom/*`, `/atom11/*`, `/browser/*`, `/cmis-endpoints.json` nie są objęte filtrem (obserwacja 87); uprawnienia CMIS muszą odpowiadać uprawnieniom do typów i pól Mercury.
- Typy z `isDocumentType=true` trafią do list typów dokumentowych i do mechanizmów synchronizacji z zewnętrznym CMIS.
- `CaseDocument` ma wymagane `source` i `initStatus` oraz pola z modelu AE (grupowanie, odbiorcy), których CMIS nie używa; wiele pól zostanie pustych. Flaga `isLatestVersion` w wierszach powiązań musi być spójna z łańcuchem wersji sprawy.
- Unikalność `cmis:name` w folderze wymaga sprawdzenia przy zapisie (wyścig przy równoległym tworzeniu: do rozstrzygnięcia, np. indeks unikalny albo blokada folderu).
- Nowy indeks „Document” wymaga zmian w kierowaniu spraw do indeksów i przebudowy (model wyszukiwania 3.0).
- Filtr `RemoteBasicAuthFilter` na `/cmisws*` to stały sekret usługi, a nie użytkownicy: trzeba go zastąpić filtrem uwierzytelniającym (SSO).

### Decyzje końcowe i plan etapu 1 (2026-10-30)

Autor odpowiedział „Tak” na wszystkie siedem ostatnich pytań. Decyzje:

| # | Decyzja |
|---|---|
| D1 | Model `CaseDocument`: **wariant A**. Wersja dokumentu = wersja sprawy (`previousVersionId`, `rootVersionId`, `CaseRootVersion.lastVersion`); `CaseDocument` tylko dla powiązań ze sprawami biznesowymi; identyfikator pliku (`FileIndex.id`) i etykieta wersji w polach dokumentu |
| D2 | Cykl życia przez ponowne użycie `Case.State`: `A` aktualna, `O` robocza po `checkOut`, `Z` zastąpiona, opcjonalnie `N` wycofana; folder tylko `A`. `InitStatus` w wierszach powiązań: wartość domyślna do ustalenia w implementacji (przypuszczenie: wartość „nie rozpoczął sprawy”) |
| D3 | `cmis:name` unikalna w folderze, egzekwowana przy tworzeniu i zmianie nazwy; jeden mount point = jedno repozytorium z jednym folderem głównym; `getRepositories` zwraca listę mount pointów |
| D4 | Indeks Lucene „Document” powstaje już w etapie 1 (dokumenty indeksowane od początku); wyszukiwanie CMIS-QL w etapie 2, z proponowanym podzbiorem |
| D5 | `CN001RequiredNodeNotAvailableException` -> `CmisRuntimeException` (odpowiedź 500, komunikat „plik tymczasowo niedostępny”), tylko dla operacji na treści |
| D6 | Limit pliku: `mercury.cmis.maxContentSize` w `mercury.properties`, domyślnie 10485760, zasila `CmisServiceFactory.getMaxContentSize()` |
| D7 | Szkic `FileShare*` i `repository.properties` usuwamy w tej samej zmianie |

Wcześniejsze ustalenia (typy `CmisFolder` i `CmisDocument` z CSV, rodzaj `BaseDocuments`, pola typów, uprawnienia sprawy i czytanie pliku w kontekście systemowym, Basic i OAuth z SSO, role jak w sprawach, endpointy domyślnie włączone, `Source` z kontekstu) są w sekcji „Ustalenia autora”.

#### Plan etapu 1 (propozycja kolejności; szacunki orientacyjne, przypuszczenie)

| Krok | Zakres | Repozytorium |
|---|---|---|
| 1 | Typy predefiniowane z CSV: rodzaj `BaseDocuments`, kody `CmisFolder` i `CmisDocument`, `TypeCase`, `ParamDefinition`, `TypeParam`, `Type2Type`, flaga `isDocumentType` w loaderze `TypeCaseLoader`, wyliczenie `TypeCaseName`; test ładowania | `mercury` (`mercury-entities-ids`) |
| 2 | ~~Indeks Lucene „Document”: osobny indeks~~ **Zastąpione wariantem B (2026-10-31):** jeden indeks „Case”, pole `mrc_typeIsDocumentType` dla dokumentów, filtr zakresu wyszukiwania (`DocumentTypeFilter`); zrobione w dwóch częściach (pole w `TypeCaseMapper`, filtr w `QueryExplainPlan` i `DateMetricQuery`), luki w sekcji „Realizacja: wariant B, krok 2” | `mercury` (`mercury-lucene-indexes`) |
| 3 | Warstwa dostępu CMIS (`CmisService` oparte o logikę Mercury): repozytorium i typy (`getRepositoryInfo`, `getTypeDefinition`, `getTypeChildren`), obiekty (`getObject`, `getObjectByPath`, `getChildren`, `createFolder`, `createDocument`, `updateProperties`, `deleteObject`), treść (`getContentStream`, `setContentStream`) przez `IFileIndexLogicInternal` w kontekście systemowym po sprawdzeniu uprawnień sprawy | `mercury` (`mercury-ws-app`) |
| 4 | Reguły: unikalność `cmis:name`, rozwiązywanie ścieżek z nazw, limit rozmiaru (`getMaxContentSize`), mapowanie `CN001` i `FI001` na wyjątki CMIS | `mercury` |
| 5 | Uwierzytelnianie i SSO: filtr przed serwletami CMIS (Bearer jak `OAuthFilter`, Basic w tym samym realmie), ten sam `Context` (model zadania 217), wzorce ścieżek CMIS w konfiguracji OAuth | `mercury` (`mercury-ws-app`) |
| 6 | Usunięcie `FileShare*`, `repository.properties`, uporządkowanie `web.xml` (endpointy zostają domyślnie włączone) | `mercury` |
| 7 | Testy: jednostkowe i klientem CMIS (np. `mercury-cmis-client` albo klient OpenCMIS), test z dwoma węzłami dla pliku zdalnego; dokumentacja w `docusaurus-hgdb` (EN i PL) | `mercury`, `docusaurus-hgdb` |

Zmiana API REST/SOAP Mercury w etapie 1 nie jest planowana (serwer CMIS to Chemistry), więc nowe klucze `openapi-docs_*` nie powinny być potrzebne (przypuszczenie). Zmiany w `mercury-lib` nie są planowane (przypuszczenie, do weryfikacji w kroku 1: flaga `isDocumentType` w `TypeCase` już istnieje). Wydanie klienta i `mercury-cmd` tylko przy zmianach w tych repozytoriach (decyzja autora z 2026-10-29).

Kolejne zapisy z realizacji dopisujemy poniżej.

### Realizacja: krok 1, typy predefiniowane (2026-10-30, gałąź `hgdb-049` w `mercury`)

Zrobione w `mercury-entities-ids` (niezacommitowane):

| Zmiana | Szczegóły |
|---|---|
| Rodzaj typu | `dict/TypeKind.csv`: `BaseDocuments` (klucz zasobu `typeKind.baseDocuments.description`) |
| Kody typów | `attr/TypeCode.csv`: `CmisFolder`, `CmisDocument`; wyliczenia `TypeCodeName` i `TypeCaseName` rozszerzone o te nazwy |
| Typy | `attr/TypeCase.csv`: nowa kolumna `IS_DOCUMENT_TYPE`; wiersze `-6 CmisFolder` i `-7 CmisDocument` (wersja 1, rodzaj `BaseDocuments`, nieedytowalne; `isDocumentType`: `-7 CmisDocument` = `true`, `-6 CmisFolder` = `false` po korekcie z 2026-10-31, przy pierwszym zapisie było `true`) |
| Loader | `TypeCaseLoader`: czyta kolumnę `IS_DOCUMENT_TYPE` (indeks 11); gdy jej brak, ustawia `false` (sprawa) |
| Definicje pól | `attr/ParamDefinition.csv`: 12 definicji (`CmisName`, `CmisTitle`, `CmisDescription`, `CmisAuthor`, `CmisMimeType`, `CmisFileName`, `CmisContentSize`, `CmisContentStreamId`, `CmisVersionLabel`, `CmisCheckinComment`, `CmisIsMajorVersion`, `CmisIsImmutable`) |
| Pola typów | `attr/TypeParam.csv`: `CmisFolder` 3 pola (nazwa wymagana, tytuł, opis), `CmisDocument` 12 pól (jak w tabeli pól typów; `CmisContentStreamId` bez indeksowania) |
| Zasoby | `resources_pl.properties` (UTF-8) i `resources_en.properties` (ISO-8859-1, tylko znaki ASCII): 44 klucze każdy; de/es/fr/ko do uzupełnienia przez translator Gemini |
| Lustra | `mercury-entities-ids/resources/**` i `mercury-srv/resources/**` (używane przez testy przez `mercury.predefined.data.path`) zsynchronizowane z `src/main/resources` (14 plików; kopie miały zgodność z `src` na HEAD) |
| Test | nowy `PredefinedDocumentTypesTest` (5 testów): typy, flaga dokumentowa i pozostałe typy jako sprawy, rodzaj i kody, definicje i kolejność pól, klucze zasobów w pl i en |

Weryfikacja: `PredefinedDocumentTypesTest` 5/5; pozostałe testy `pro/ibpm/mercury/entities/**` 14/14 (razem z nowym); `EjbDaoTest` na `mercury-db-test` (profil `scichy-test`) przechodzi, a loader przetwarza 121 definicji, 7 kodów, 6 rodzajów, 7 typów i 60 pól bez błędów. Czego nie sprawdzono: samej obecności wierszy `-6` i `-7` w bazie po teście (test sprząta dane), oraz ładowania do bazy z istniejącymi typami (loader dodaje tylko brakujące wiersze).

Uwagi: istniejące typy predefiniowane (kalendarz, `MrcUnknownBusinessObject`) mają w bazie `IS_DOCUMENT_TYPE=NULL` (zbadane na `mercury-db`), więc nie są ani sprawą, ani dokumentem (obserwacja 123). Pliki CSV i zasoby występują w trzech kopiach (obserwacja 124).

### Stan na koniec dnia 2026-10-30 i otwarta kwestia indeksu „Document” (krok 2)

**Stan:** krok 1 (typy predefiniowane) zacommitowany przez autora (`d102994af` w `mercury`, gałąź `hgdb-049`). Krok 2 (osobny indeks Lucene „Document”) **wstrzymany**: w kodzie nic nie zmieniono. Autor przemyśli, czy osobny indeks jest dobrym rozwiązaniem.

**Co potwierdzono w kodzie (rozpoznanie kroku 2):**
- `CaseIndexBackupAction` i `CaseIndexRestoreBackupAction` mają zaszytą nazwę indeksu `Case.class.getSimpleName()`; drugi indeks wymagałby ich rozszerzenia.
- `CaseIndexerBusinessSupport.updateIndex` używa jednego `ICaseIndexer`, jednego writera i readera dla całego bufora; routing po typie trzeba by dodać w tej centralnej pętli (locki, paczki JMS z klastra, wątki).
- Pełna przebudowa dwóch indeksów musiałaby iść sekwencyjnie (współdzielony token zrzutu w DAO, stan w singletonie `CaseMapper`).
- Mapa atrybutów „ForCasesOnly” pomija pola typów dokumentowych; dokumenty wymagałyby mapowania „ForDocumentsOnly”.
- Wyszukiwarki spraw (`CaseSearchExt`, wyszukiwanie po id, statystyki) czytają indeks „Case”, więc po rozdzieleniu przestałyby zwracać dokumenty.

**Obawa autora:** osobny indeks jest kłopotliwy, a pole `isDocumentType` jest zbyt mało selektywne, żeby wspierać wyszukiwanie.

**Czy Lucene ma partycje?** Nie. Indeks Lucene nie ma partycji w sensie bazodanowym. Dzieli się na segmenty (to podział fizyczny, nie logiczny; zarządza nim merge policy). Podział logiczny robi się przez osobne indeksy (sharding) albo przez filtr po polu. Zachowanie dla wersji Lucene użytej w Mercury do sprawdzenia (przypuszczenie, że nie odbiega od ogólnych zasad).

**Alternatywy do omówienia jutro:**

| # | Wariant | Zalety | Wady / ryzyka |
|---|---|---|---|
| A | Osobny indeks „Document” (plan pierwotny) | Brak wpływu na zapytania o sprawy; osobny rozmiar, osobny cykl odświeżania | Routing w `updateIndex`, backup/restore, przebudowa, wyszukiwarki do rozdzielenia; największy zakres zmian |
| B | Jeden indeks „Case”, dokumenty z polem `isDocumentType` i **dopisywany filtr** (klauzula `FILTER`/`MUST_NOT`) | Zero zmian w indeksowaniu, backupie i przebudowie; dokumenty indeksowane od razu | Wszystkie dotychczasowe wyszukiwania spraw muszą wykluczać dokumenty (jedno miejsce w `CaseSearcher`, ale ryzyko pominięcia); niska selektywność pola nie przeszkadza, bo filtr jest tani i cache'owany, jeśli dokumentów jest mało. Kiedy dokumentów jest dużo, rośnie koszt dla zapytań o sprawy |
| C | Jak B, ale CMIS-QL dostaje filtr `isDocumentType:true` automatycznie, a wyszukiwania spraw nie zmieniamy (dokumenty widoczne jako sprawy tylko w wynikach, jeśli ktoś szuka bez filtra typu) | Najmniejszy zakres | Dokumenty „wyciekają” do wyników spraw; sprzeczne z definicją roboczą (sprawa = `isDocumentType=false`) |
| D | Wyszukiwanie CMIS bez Lucene: zapytania do bazy (`CaseCatalog`, dopasowanie po nazwie/folderze/typie) | Brak zmian w Lucene; wystarczy dla `getChildren`, `getObjectByPath`, nazwy w folderze | Brak pełnotekstowego CMIS-QL i `ORDER BY`/`LIKE` na dużych zbiorach; etap 2 trzeba by zrobić inaczej |
| E | Wariant A, ale przez wspólną infrastrukturę: ta sama klasa indeksera z parametrem nazwy indeksu i predykatem `accepts`, bez podklas | Mniej klas, jedna ścieżka kodu | To nadal rozdzielenie routingu, więc ryzyka z A pozostają |

**Do rozstrzygnięcia jutro:** (1) jak liczny będzie zbiór dokumentów względem spraw (od tego zależy B i D); (2) czy CMIS-QL w etapie 2 ma być pełnotekstowy; (3) czy wystarczy rozdzielenie po stronie wyszukiwania (B), czy potrzebna fizyczna izolacja (A). Rekomendacja robocza Claude: sprawdzić najpierw B (najmniejszy zakres zmian), a A zachować, jeśli pomiary lub wymagania pokażą potrzebę izolacji (przypuszczenie, bez pomiarów).

Kroki 3–7 planu (CmisService, reguły, filtr SSO, usunięcie `FileShare*`, testy i dokumentacja) nie zależą od wyboru indeksu w etapie 1, o ile `getObject`, `getChildren` i `getObjectByPath` czytają z bazy (`CaseCatalog`); od indeksu zależy tylko `query` (CMIS-QL).

### Wariant B: rozpoznanie (2026-10-30, wieczór; bez zmian w kodzie)

Autor wybrał wariant B (jeden indeks „Case” plus filtr). Ustalone w kodzie `mercury`:

- **Pole nie jest dziś indeksowane.** `TypeCase.isDocumentType` nie ma adnotacji `@LuceneSeracherField` (mają ją tylko `id`, nazwa, opis i `accountNumber`), więc w indeksie nie ma pola „czy dokument”. Adnotacja leży w `mercury-lib` (inne repozytorium), więc nie dotykamy jej. Wzorzec obejścia już istnieje: `TypeCaseMapper` dodaje ręcznie pole `sourceOfObject` (`getLuceneFields` + `convert2Document`). Tak samo można dodać pole `mrc_typeIsDocumentType` (StringField, tylko dla dokumentów).
- **Istniejące indeksy nie wymagają przebudowy.** Dotychczas indeksowane obiekty to sprawy. Filtr „brak pola `isDocumentType:true`” (`MUST_NOT`) przepuszcza je bez reindeksu. Pole dostają tylko nowe dokumenty.
- **Brak jednego miejsca na filtr.** Zapytania o sprawy powstają w kilku miejscach: `QueryExplainPlan` (model 3, zapytanie Lucene od użytkownika), `FieldMetricQuery`, `DateMetricQuery`, `CaseIndexer.createOneQuery` i `buildSimpleQueryClause` (stare ścieżki, model 2), `CaseSearcher` (4 użycia indeksu „Case”), `CaseSearchExtRest`. `SecurityQueryHelper` sprawdza tylko uprawnienia do pól, nie dokłada klauzul.
- **Uprawnienia typów już zawężają wyniki.** `CaseIndexer.checkPrivilegesForParams` dokłada obowiązkowe warunki po kodzie i id typu, ale tylko gdy użytkownik poda typ. Użytkownik z prawem do wszystkich typów (`isAllRO`) szuka bez typu, więc bez filtra zobaczy też dokumenty.
- **Typy w indeksie są już rozróżnialne po kodzie.** Pola `mrc_type.codeValue`/`codeName` istnieją, więc alternatywą do pola logicznego jest filtr po zbiorze kodów typów dokumentowych (`IDocumentTypesManager`), ale zbiór zmienia się z typami (wersje, nowe typy), więc pole jest trwalsze (przypuszczenie).

**Proponowane kroki wariantu B (do zatwierdzenia):**
1. Indeksowanie: pole `mrc_typeIsDocumentType` w `TypeCaseMapper` (zwykły dopisek jak `sourceOfObject`), test jednostkowy mappera bez bazy.
2. Jedna metoda w `CaseIndexer` budująca klauzulę „tylko sprawy”, wywołana w `QueryExplainPlan`, metrykach i ścieżkach `CaseSearcher`/`CaseSearchExtRest`; flaga w kontekście zapytania pozwala CMIS szukać „tylko dokumenty”.
3. Testy: istniejące scenariusze wyszukiwania nie zmieniają wyników (dokumentów brak), nowy test: sprawa i dokument w jednym indeksie, wyszukiwanie spraw pomija dokument, wyszukiwanie dokumentów pomija sprawę.

### Cel zadania i korekta definicji roli (2026-10-31)

**Cel (autor):** Mercury ma być także repozytorium dokumentów, z automatycznym identyfikowaniem definicji klas dokumentów (odpowiednik typów spraw). Wzorem są SharePoint, IBM FileNet i Alfresco. CMIS jest standardowym interfejsem do tego repozytorium. `CmisFolder` i `CmisDocument` to tylko typy predefiniowane, które pokazują, jak zbudować drzewo katalogu. Nowe klasy mają pełnić role folderów lub dokumentów przez `CaseCatalog`.

**Decyzja (autor, 2026-10-31):** rola obiektu w CMIS wynika z `TypeCase.isDocumentType`:

| Typ w Mercury | `cmis:baseTypeId` |
|---|---|
| sprawa (`isDocumentType=false`) | `cmis:folder` |
| dokument (`isDocumentType=true`) | `cmis:document` |

Ta decyzja **zastępuje** wcześniejszą definicję „folder `CmisFolder` i plik `CmisDocument` to oba dokumenty”. `CaseCatalog` nie ogranicza typów węzłów (potwierdzone w `CaseCatalog.java`: zapytania po id węzła, rodzicu i ścieżce).

**Skutki do zrealizowania (propozycje, jeszcze nie wykonane):**
1. `CmisFolder` (typ `-6`) ma mieć `isDocumentType=false`. Dotyczy to `TypeCase.csv` i jego lustra w `mercury-entities-ids/resources` i `mercury-srv/resources`, oraz testu `PredefinedDocumentTypesTest` (dziś oczekuje `TRUE` dla folderu). Zmiana jest już zacommitowana w kroku 1 (`d102994af`), więc to nowa zmiana w gałęzi `hgdb-049`.
2. Wariant B upraszcza się: foldery zostają w „Case” bez filtra, filtrować trzeba tylko dokumenty (pole `mrc_typeIsDocumentType` i klauzula „tylko sprawy” w wyszukiwaniu spraw).
3. Automatyczna identyfikacja typów: dla spraw działa już dziś (`CaseBusinessSupport` ustawia `isDocumentType=false`). Brakuje ścieżki, w której ten sam mechanizm tworzy typy z `isDocumentType=true` (dokumenty).
4. Każda sprawa w drzewie `CaseCatalog` pod mount pointem jest folderem CMIS. Folder musi mieć `cmis:name`, więc dla dowolnej sprawy trzeba ustalić źródło nazwy (np. pole `CmisName`, jeśli typ je ma; w przeciwnym razie wartość zastępcza). Do decyzji.
5. Dokument nie może mieć dzieci w katalogu. Dodawanie węzła pod dokumentem trzeba odrzucać.
6. Wyszukiwanie po polach nowych typów dokumentów wymaga mapy atrybutów obejmującej typy dokumentowe (dziś „ForCasesOnly” je pomija).

### Nazwa obiektu w CMIS (`cmis:name`): rozpoznanie i stan (2026-10-31)

**Zweryfikowane w kodzie:**
- `Case.getName()` i `@NameRepresentation` (zadanie 28) dają `inventoryCode` albo `CID:<id>`, spację i nazwę typu. Rola prezentacyjna („temat”). Wyrażenie z adnotacji pozwala też wyliczać nazwę w zapytaniu JPQL.
- `Case.inventoryCode`: kolumna `INVENTORY_CODE`, indeks zwykły `IGO_DA_CASE_INVCODE_INDX` (nie unikalny), opis „wygenerowany/unikalny kod sprawy”, w Lucene pole stringowe (zapisywane, sortowalne) z polem odwróconym. Mechanizm generowania numerów nie istnieje (zadanie 18 odłożone, nie ma go w workspace), więc pole może być `null`.
- `CaseNarrative` (`CaseBusinessHelper.transform2CaseNarrative`, `convert2CaseNarrative`): zajawka sprawy budowana z reguły `TypeCode.subjectFormula`. Formuła to elementy rozdzielone `||`: literały w apostrofach i nazwy pól (wartości z `MrcObject`, pierwsza wartość, daty formatowane wg kontekstu). Bez formuły `subject` jest pusty (narracja ma tylko id, `inventoryCode`, kod typu, `rootVersionId` i status). Temat jest wyliczany w locie; w kodzie nie widziałem jego zapisu w bazie (przypuszczenie, nie sprawdzono cache).

**Stanowiska autora:** (a) nazwa ma być `inventoryCode` (gdy nie `null`) albo `CID:<id>`, bez nazwy typu; (b) `getName()` jest prezentacyjne jak temat, a najwięcej o sprawie mówi reguła z `CaseNarrative`.

**Otwarte (do decyzji):** czy `cmis:name` ma pochodzić z reguły `subjectFormula`, czy z pól trwałych. Ryzyka: temat nie jest unikalny w folderze, nie ma jak go zapisać przy zmianie nazwy, a rozwiązywanie ścieżki po nim wymagałoby wyliczania tematu dla każdego dziecka folderu (koszt nieznany). Propozycja: `cmis:name` z pól trwałych (kolejność: `CmisName`, potem `inventoryCode`, potem `CID:<id>`; przy kolizji dopisanie `(id)`), a temat z `subjectFormula` udostępniony jako osobna właściwość tylko do odczytu (np. do prezentacji). `inventoryCode` jako miejsce zapisu nazw nadanych przez klienta CMIS kłóci się z zadaniem 18 (unikalność globalna vs nazwa unikalna w folderze), dlatego nazwy z CMIS idą do `CmisName`.

### Realizacja: korekta kroku 1, `CmisFolder` jako sprawa (2026-10-31, `hgdb-049` w `mercury`, niezacommitowane)

- `TypeCase.csv` (`src/main/resources/.../attr`, `mercury-entities-ids/resources/attr`, `mercury-srv/resources/attr`): typ `-6 CmisFolder` ma `IS_DOCUMENT_TYPE=false` (był `true`). Typ `-7 CmisDocument` bez zmian (`true`). Końce linii zachowane (lustro w entities-ids: CRLF).
- `PredefinedDocumentTypesTest`: folder oczekuje `FALSE`; test „pozostałe typy są sprawami” obejmuje już folder (pomija tylko `CmisDocument`).
- Wynik: 5 z 5 testów (`mvn -o test -pl mercury-entities-ids -am -Dtest=PredefinedDocumentTypesTest -Duser=scichy-test`; bez `-am` moduł nie kompiluje testów, bo brakuje w `.m2` artefaktu z pakietem `org.mercury.caches.core.api`).
- Uwaga: istniejące bazy z wierszem `-6` załadowanym w kroku 1 zachowają `IS_DOCUMENT_TYPE=true` (loader dodaje tylko brakujące wiersze). Dotyczy to tylko baz, na których uruchomiono kod z commitu `d102994af` (u autora na bazach testowych; przypuszczenie, nie sprawdzono).

**Decyzja (autor, 2026-10-31): `cmis:name` z pól trwałych.** Kolejność: (1) parametr `CmisName`, jeśli typ go ma i jest wypełniony (edytowalny, może się powtarzać między folderami); (2) `inventoryCode`, gdy nie jest pusty (tylko do odczytu); (3) `CID:<id>`. Przy kolizji w folderze dopisujemy `(id)`; duplikat `CmisName` w folderze odrzucamy przy zapisie. Temat z `TypeCode.subjectFormula` (`CaseNarrative`) jest osobną właściwością tylko do odczytu, do prezentacji. Nazwy nadane przez klienta CMIS idą do `CmisName`, nie do `inventoryCode` (zadanie 18: unikalność globalna). Ścieżki: lookup po `CmisName`, potem po `inventoryCode`.

### Realizacja: wariant B, krok 1, pole `isDocumentType` w indeksie (2026-10-31, `hgdb-049` w `mercury`, niezacommitowane)

- `TypeCaseMapper` (`mercury-lucene-indexes`): stałe `IS_DOCUMENT_TYPE` (`isDocumentType`), `IS_DOCUMENT_TYPE_VALUE` (`true`), pole zadeklarowane w `getLuceneFields()` (StringField, bez zapisu, bez rozróżniania wielkości liter, wzorzec jak `sourceOfObject`). `convert2Document` dodaje pole tylko dla typów z `isDocumentType=true`. Brak pola oznacza sprawę, więc istniejące indeksy nie wymagają przebudowy. W indeksie pole nazywa się `mrc_typeIsDocumentType` (prefiks typu w modelu 3; sprawdzone w teście z prefiksem `mrc_type`, nie na pełnym indeksie).
- Nowy test `TypeCaseMapperDocumentTypeTest` (4 testy): pole zadeklarowane, dokument ma pole z wartością `true`, sprawa (`false`) i typ bez flagi (`null`) pola nie mają. Wynik 4/4; `CaseMapperTest` i `CaseMapperStoreTest` też przechodzą.
- Pełny przebieg testów modułu `mercury-lucene-indexes` (110 testów) dał 62 niepowodzenia w klasach wymagających Ehcache/Terracotty (`localhost:9510`: „Connection refused”). Infrastruktura nie była uruchomiona, więc nie ocenia to zmiany. Do powtórzenia po starcie Terracotty.
- Plik `TypeCaseMapper.java` ma w indeksie LF (po edycji narzędziem wróciłem do LF).

**Korekta nazwy pola (2026-10-31):** w indeksie pole nazywa się `mrc_typeIsDocumentType` (nie `mrc_type.isDocumentType`). `EntityHelper.addPrefixName` skleja prefiks z nazwą pisaną wielką literą (jak `mrc_typeCodeValue`). Wcześniejsze wpisy poprawiono.

### Realizacja: wariant B, krok 2, zawężanie wyszukiwania do spraw lub dokumentów (2026-10-31, `hgdb-049` w `mercury`, niezacommitowane)

- `CaseMapper`: stała `LUCENE_TYPE_IS_DOCUMENT_TYPE` (`mrc_typeIsDocumentType`), dopisana do pól specjalnych.
- Nowa klasa `org.mercury.lucene.query.DocumentTypeFilter`: zakres wyszukiwania `Scope` (`CASES` domyślnie, `DOCUMENTS`, `ALL`) w parametrze żądania `org.mercury.lucene.query.scope` (`setScope(context, scope)`); `apply(context, query)` dopisuje do sparsowanego zapytania klauzulę `MUST_NOT` (sprawy) albo `MUST` (dokumenty) na polu `mrc_typeIsDocumentType:true`. Zapytanie, które samo wymienia to pole, zostaje bez zmian.
- Podpięcie: `QueryExplainPlan.prepareSubPlan` (po sprawdzeniu uprawnień, przed `QueryExtractor`; obejmuje też plan rodzica przy JOIN) oraz `DateMetricQuery.prepare`. `CaseSearcher` i `CaseSearchExtRest` korzystają z tych ścieżek.
- **Ważne ustalenie:** filtr jako tekst `+(A AND B) -pole:wartość` daje 0 wyników, bo `QueryExtractor` traktuje zagnieżdżone `BooleanQuery` jak zapytania do spraw zależnych. Dlatego warunek jest dopisywany do głównego `BooleanQuery` (bez zagnieżdżania). Dla dokumentów i zapytania z samymi klauzulami `SHOULD` (np. `A OR B`) zapytanie jest zagnieżdżane, bo dopisanie `MUST` uczyniłoby `SHOULD` opcjonalnymi; ten wariant jest pokryty testem.
- Test `DocumentTypeFilterTest` (6 testów, indeks w pamięci, trzy tryby optymalizatora `cost`/`rootFirst`/`none`): rozdzielenie spraw i dokumentów, łączenie z innymi kryteriami, zapytania `OR`, zapytanie z jawnym polem, przypadki brzegowe. Pole dokumentu jest dodawane do parsera w teście, bo fixture `LuceneSearchableFields.json` go nie zawiera (produkcyjny mapper deklaruje je przez `TypeCaseMapper`).
- Wynik: moduł `mercury-lucene-indexes` 116 testów, 0 niepowodzeń, 10 pominiętych (przy działającej Terracotcie).

**Luki (świadomie nie ruszone):**
1. `FieldMetricQuery` (statystyki wartości pola) enumeruje terminy całego indeksu, więc zliczy też dokumenty. Wymaga osobnego rozwiązania (zliczanie przez zapytanie z filtrem).
2. Stare ścieżki modelu 2.0 (`CaseIndexer.searchIndex`, `buildSimpleQueryClause`, `createOneQuery`, oznaczone `@Deprecated`) nie dostały filtra, zgodnie z zasadą, że model 2.0 jest tylko wsteczny.
3. Nie sprawdzono na pełnym indeksie (mapper produkcyjny z Springiem): że pole `mrc_typeIsDocumentType` trafia do dokumentu Lucene i że wyszukiwanie spraw na indeksie z dokumentami działa end-to-end. Do zrobienia w testach `mercury-srv` (scenariusze Lucene na bazie testowej).
4. Atrybuty (pola `Cmis*`) typów dokumentowych: mapa atrybutów „ForCasesOnly” je pomija, więc wyszukiwanie po tych polach wymaga osobnej zmiany.
