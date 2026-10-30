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

### Definicje robocze (autor, 2026-10-30)

- **Sprawa**: obiekt sprawy z typem, który ma `isDocumentType=false`.
- **Dokument**: obiekt sprawy z typem, który ma `isDocumentType=true`. W tym znaczeniu dokumentem jest zarówno folder (`CmisFolder`), jak i plik (`CmisDocument`). Poniżej „folder” i „dokument plikowy” oznaczają te dwa typy.

### Ustalenia autora (2026-10-30)

1. Folder i Dokument są sprawami, a definicje ich typów mają `isDocumentType=true`.
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
13. Mount point to identyfikator repozytorium. Foldery to obiekty spraw z typem `isDocumentType=true`; wewnętrznie nic się nie zmienia, wykorzystujemy istniejące mechanizmy; przy prezentacji `#` zamieniamy na `/`.
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
| 2 | Indeks Lucene „Document”: kierowanie spraw z `isDocumentType=true` do osobnego indeksu, mapper i indeksator, zgodność z modelem 3.0 | `mercury` (`mercury-lucene-indexes`) |
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
| Typy | `attr/TypeCase.csv`: nowa kolumna `IS_DOCUMENT_TYPE`; wiersze `-6 CmisFolder` i `-7 CmisDocument` (wersja 1, rodzaj `BaseDocuments`, `isDocumentType=true`, nieedytowalne) |
| Loader | `TypeCaseLoader`: czyta kolumnę `IS_DOCUMENT_TYPE` (indeks 11); gdy jej brak, ustawia `false` (sprawa) |
| Definicje pól | `attr/ParamDefinition.csv`: 12 definicji (`CmisName`, `CmisTitle`, `CmisDescription`, `CmisAuthor`, `CmisMimeType`, `CmisFileName`, `CmisContentSize`, `CmisContentStreamId`, `CmisVersionLabel`, `CmisCheckinComment`, `CmisIsMajorVersion`, `CmisIsImmutable`) |
| Pola typów | `attr/TypeParam.csv`: `CmisFolder` 3 pola (nazwa wymagana, tytuł, opis), `CmisDocument` 12 pól (jak w tabeli pól typów; `CmisContentStreamId` bez indeksowania) |
| Zasoby | `resources_pl.properties` (UTF-8) i `resources_en.properties` (ISO-8859-1, tylko znaki ASCII): 44 klucze każdy; de/es/fr/ko do uzupełnienia przez translator Gemini |
| Lustra | `mercury-entities-ids/resources/**` i `mercury-srv/resources/**` (używane przez testy przez `mercury.predefined.data.path`) zsynchronizowane z `src/main/resources` (14 plików; kopie miały zgodność z `src` na HEAD) |
| Test | nowy `PredefinedDocumentTypesTest` (5 testów): typy, flaga dokumentowa i pozostałe typy jako sprawy, rodzaj i kody, definicje i kolejność pól, klucze zasobów w pl i en |

Weryfikacja: `PredefinedDocumentTypesTest` 5/5; pozostałe testy `pro/ibpm/mercury/entities/**` 14/14 (razem z nowym); `EjbDaoTest` na `mercury-db-test` (profil `scichy-test`) przechodzi, a loader przetwarza 121 definicji, 7 kodów, 6 rodzajów, 7 typów i 60 pól bez błędów. Czego nie sprawdzono: samej obecności wierszy `-6` i `-7` w bazie po teście (test sprząta dane), oraz ładowania do bazy z istniejącymi typami (loader dodaje tylko brakujące wiersze).

Uwagi: istniejące typy predefiniowane (kalendarz, `MrcUnknownBusinessObject`) mają w bazie `IS_DOCUMENT_TYPE=NULL` (zbadane na `mercury-db`), więc nie są ani sprawą, ani dokumentem (obserwacja 123). Pliki CSV i zasoby występują w trzech kopiach (obserwacja 124).
