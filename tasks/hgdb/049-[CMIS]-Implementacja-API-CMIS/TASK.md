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

### Realizacja: wariant B, krok 3, pola atrybutów typów dokumentowych w indeksie (2026-10-31, `hgdb-049` w `mercury`, niezacommitowane)

Cel: pola typów dokumentowych (np. `CmisMimeType`) są znane parserowi zapytań i indeksowaniu, bez pętli `request4RefreshLuceneFields()`. Wybrane warianty (decyzje autora): zapytania dynamiczne w DAO zamiast zmian w `mercury-lib` i jedna lista pól (suma spraw i dokumentów, wariant B-1).

**Zmiany (wszystko w `mercury`):**

| Moduł | Zmiana |
|---|---|
| `mercury-dao-api`, `mercury-dao` | `IParamDefinitionDAO`/`ParamDefinitionDAO`: `getAttrsForIndexAllVersions` (suma definicji z `QgetForCasesOnlyAllVersions` i `QgetForDocumentsOnlyAllVersions`, bez powtórzeń po nazwie i wersji) oraz `findAllVersionsByTypeId` (zapytanie dynamiczne bez filtra rodzaju typu) |
| `mercury-dao-api`, `mercury-dao` | `ITypeParamDAO`/`TypeParamDAO`: `findByParamDefinitionNameWithOutCache` (zapytanie dynamiczne bez filtra rodzaju typu) |
| `mercury-dao` | `SecurityContextHelper.getBaseInfo` używa nowej metody zamiast `QsearchByParamDefinitionName` (w `mercury-lib` z filtrem `isDocumentType=false`); to trzecie źródło, którego nie przewidziałem w rozpoznaniu: bez tej zmiany lista pól typu `CmisDocument` miała tylko 3 pola wspólne z folderem |
| `mercury-srv` | `CaseAttributesSecretaryAction` używa `getAttrsForIndexAllVersions`; `CaseAttributtesManager` używa `findAllVersionsByTypeId` |

**Testy:**
- `EjbDaoTest` (na `mercury-db-test`): nowy `DocumentTypeAttributesScenario`, w tym `CmisFolder` 3 definicje i `CmisDocument` 12 definicji, stare zapytanie „tylko sprawy” nie zwraca definicji dokumentu, a lista pól indeksu zawiera pola obu typów bez powtórzeń.
- `DocumentTypeFieldsTest` w `mercury-srv` (osobna klasa z jednym scenariuszem `DocumentTypeFieldsScenario`, poza `SrvTest`): lista pól parsera i lista pól typu `CmisDocument` w kontekście systemowym zawierają wszystkie 11 pól dokumentowych. Test wykrył brakujące trzecie źródło (porażka z 3 polami).
- Czego nie ma: dokumentu Lucene zbudowanego z zapisanej sprawy typu dokumentowego. `CaseMapper.convert2Document` pobiera sprawę z bazy po id (`caseDAO.findForIndex`), więc test wymaga zapisanej sprawy; do dodania razem z usługą CMIS (krok 3 planu etapu 1). Nie sprawdziłem też w tym teście, że `request4RefreshLuceneFields()` nie jest wywoływane; na tym etapie sprawdzono tylko, że wszystkie źródła list pól zawierają pola dokumentowe.

Obserwacja 125 w `docs/obserwacje.md` opisuje zaszyty filtr `isDocumentType=false` w `mercury-lib`.

**Regresja po zmianach kroku 3 (2026-10-31).** Lokalny profil `scichy-test` pomija większość scenariuszy `SrvTest` (`test.skip.<nazwa>=true` w `mercury-srv/src/test/resources-filtered/properties/scichy-test/test.properties`; parametr `-D` nie nadpisuje pliku). Za zgodą autora włączyłem tymczasowo sześć scenariuszy i przywróciłem plik z kopii (bajt w bajt):
- OK: `searchCaseScenario`, `searchCaseDocumentScenario`, `securityContextHelperScenario`, `securityContextHelperTypeParamsScenario`.
- FAILED: `luceneFieldsScenario` („nie znalazłem pola listDates”) i `luceneIndexerScenario` („Spodziewam się konkretnego wyniku”). Oba **padają identycznie bez moich zmian** (baza porównawcza: `git stash -u` zmian kroku 3, ten sam przebieg, `git stash pop`; status repozytorium po przywróceniu identyczny). Są to wcześniejsze porażki, nie skutek zmian. Przyczyny nie badałem (przypuszczenie dla `luceneFieldsScenario`: lista pól budowana raz, przed wstawieniem danych testowych). Runner zatrzymuje się na pierwszej porażce, więc scenariusze po niej nie są uruchamiane.
- Brak pokrycia: `testMERC_0168_Scenarios` w `mercury-ws-server` (test krytyczny) nie był uruchamiany po zmianach kroku 3.

### Realizacja: błąd wyszukiwania po kroku 2, naprawa extractora i porządki testów (2026-10-31, `hgdb-049` w `mercury`)

**Korekta wcześniejszego wniosku.** W sekcji „Regresja po zmianach kroku 3” napisałem, że `luceneIndexerScenario` pada identycznie bez moich zmian. To było nieprecyzyjne: porównanie przez `git stash -u` nie obejmowało commitów kroku 2, w których jest `DocumentTypeFilter`. Porażka `luceneIndexerScenario` była skutkiem mojego filtra.

**Błąd (krytyczny, naprawiony).** Zapytanie `(A OR B) AND NOT (pole:x OR pole:y)` zwracało 0 trafień w `luceneIndexerScenario` (`LuceneIndexerScenario.java:1062`). Z `Scope.ALL` (filtr wyłączony) scenariusz przechodził.
- Przyczyna: `QueryExtractor.extractGroup` przetwarza klauzule proste przed zagnieżdżonymi, a `checkGroupOccur` (`firstIsMustNot`) uznawał cały prefiks za wykluczający, gdy pierwsza klauzula była `MUST_NOT`. Mój `-mrc_typeIsDocumentType:true` był klauzulą prostą i trafiał na początek.
- Ten sam błąd miały już zapytania użytkownika z pojedynczą negacją, np. `(A OR B) AND NOT (pole:x)` (obserwacja 126).
- Naprawa: `QueryExtractor.checkGroupOccur`, prefiks jest wykluczający tylko wtedy, gdy wszystkie klauzule są `MUST_NOT` (`allMustNot`). `DocumentTypeFilter` zostaje bez zmian.
- Testy: `DocumentTypeFilterTest` (`testNegatedGroupKeepsItsMeaning`, `testSingleNegatedCriterionKeepsItsMeaning`, 3 zakresy × 3 tryby optymalizatora). Nowy test pada na starym extractorze (0 zamiast 3). Moduł `mercury-lucene-indexes`: 118 testów, 0 porażek, 10 pominiętych.
- Regresja `SrvTest` na `mercury-db-test`: `luceneIndexerScenario`, `searchCaseScenario`, `searchCaseDocumentScenario`, `luceneConfigScenario` OK.

**Porządki testów.**
- `LuceneFieldsScenario` ładuje sam `TestMrcObject.single.v2.xml` (obserwacja 127). Przebiegł OK. Pełnej niezależności od poprzednich scenariuszy nie wykazałem (definicje typów przeżywają czyszczenie schematu).
- Nowa klasa `LuceneIndexerOnlyTest` uruchamia tylko `LuceneIndexerScenario` (poza `SrvTest`).
- `forceAddPKScenario` pada w pełnym przebiegu `SrvTest` (`expected:<2> but was:<3>`), osobno przechodzi (obserwacja 128, przyczyna nieustalona).

**Budowanie.** `mercury/pom.xml`: `skipIfEmpty` w wykonaniu `maven-jar-plugin:jar`, żeby `install` rodzica nie zastępował jego `.pom` archiwum JAR (obserwacja 129). `mercury-lib/pom.xml` ma tę samą konfigurację i nie został zmieniony.

**Czego nie sprawdziłem.** `testMERC_0168_Scenarios` (`mercury-ws-server`) po zmianie extractora; pozostałe pominięte scenariusze `SrvTest`.

### Stan na koniec dnia 2026-10-31 i plan na 2026-11-01

**Zrobione (wszystko w `hgdb-049` w `mercury`, zacommitowane przez autora):**
- Wariant B indeksu w całości: typy `CmisFolder`/`CmisDocument` z CSV (krok 1), pole `mrc_typeIsDocumentType` i `DocumentTypeFilter` (krok 2), pola atrybutów typów dokumentowych w indeksie (krok B-3).
- Po drodze naprawione błędy, które ujawniły testy: `QueryExtractor.checkGroupOccur` zerował wynik przy klauzuli `MUST_NOT` (obs. 126, krytyczne), statyczna mapa `AttributeTypeParameterFactory` nie była czyszczona po czyszczeniu bazy (obs. 128), `Text` po typie liczbowym kończył się mylącym `rollback-only` (obs. 136), `LuceneFieldsScenario` zależał od `caseBusinessScenario` (obs. 127), `pom.xml` rodzica zastępował swój `.pom` archiwum JAR (obs. 129).
- Zasada „lepkiej definicji” (obs. 132, 133, 135): wartość mieszcząca się w istniejącej definicji nie tworzy nowej wersji typu. Macierz 7×7: z 34 do 0 wersji samego podtypu. Dokument: `docs/macierz-identyfikacji-typu-atrybutu.md`.
- Ewidencja zależności scenariuszy testowych: `docs/testy-zaleznosci-scenariuszy.md`.

**Otwarte:**
- `datasetScenario` pada w zestawie, przechodzi sam (obs. 131): uruchamiać samodzielnie (`test.skip.datasetScenario=true`).
- `luceneBackupScenario` bywa niestabilny (obs. 134).
- `mercury-lib/pom.xml` ma tę samą konfigurację `jar` co poprawiony `mercury/pom.xml` (obs. 129): czeka na decyzję.
- `testMERC_0168_Scenarios` po zmianie „lepkiej definicji” do ponownego uruchomienia przez autora (infrastruktura).
- Nie zbadane: skutki zasady „lepkiej definicji” dla indeksu Lucene (`STRING` pochłaniające liczby), długie wartości `Text`/`String`, typy spoza macierzy (daty, waluta, listy).
- Luka kroku B-3: brak testu dokumentu Lucene zbudowanego z zapisanej sprawy typu dokumentowego (do dodania z usługą CMIS). Obserwacje 123 i 124 czekają na decyzje autora.
- Niezacommitowane w workspace: `README.md`, `docs/obserwacje.md`, `docs/testy-zaleznosci-scenariuszy.md`, `docs/macierz-identyfikacji-typu-atrybutu.md`, ten plik.

**Plan na 2026-11-01 (propozycja, do potwierdzenia):**
1. Start (autor): commit dokumentacji w workspace oraz `testMERC_0168_Scenarios` i pełny `SrvTest` po „lepkiej definicji”. Tego nie robię sam, bo infrastrukturę uruchamia autor.
2. Powrót do głównej linii zadania, krok 3 planu etapu 1 (`CmisService`, `mercury-ws-app`, Chemistry 1.1.0). Kolejność:
   1. Rozpoznanie (bez kodu): zależności Chemistry w POM-ach, miejsce usługi w `mercury-ws-app`, stan `FileShare*`.
   2. Identyfikacja typów dokumentowych w `CaseBusinessSupport`: dziś typy powstają zawsze z `isDocumentType=false`. Autor chce automatycznej identyfikacji klas dokumentów, więc potrzebna decyzja, po czym klasa dokumentu jest rozpoznawana.
   3. Szkielet usługi tylko do odczytu: `getRepositoryInfo`, `getTypeDefinition`, `getTypeChildren`, potem `getObject`, `getChildren`. Zapis (`createFolder`, `createDocument`) dopiero po odczycie.
   4. Test dokumentu Lucene z zapisanej sprawy typu dokumentowego (luka B-3).
3. Jeśli zostanie czas: obserwacja 134 (stabilność `luceneBackupScenario`), decyzja o `mercury-lib/pom.xml`, obserwacje 123 i 124.
4. Na koniec etapu: dokumentacja w `docusaurus-hgdb` (gałąź `hgdb-049`, EN i PL). Zakres zaproponować autorowi przed edycją.

### Decyzja o identyfikacji typów dokumentowych i pole `isDocumentType` w nagłówku (2026-11-01)

**Decyzja (autor):** `isDocumentType` trafia do nagłówka sprawy (`CaseHeader`, zmiana w `mercury-lib`, gałąź `hgdb-049`). Brak wartości albo `false` oznacza sprawę (folder), `true` oznacza dokument. Serwer CMIS ustawia pole, zanim obiekt trafi do warstwy biznesowej. Testy `testMERC_0168_Scenarios` i `SrvTest` po „lepkiej definicji” przeszły (potwierdzenie autora).

**Zrobione w `mercury-lib` (gałąź `hgdb-049`, niezacommitowane, kompilacja `mercury-srv-api` z `-am` bez błędów):** pole `Boolean isDocumentType` w `ICaseHeader`, `CaseHeader`, `MrcCaseHeader`, `MercuryHeader`; element `isDocumentType` w wyliczeniu `MrcCaseHeaderField` (typ `BOOLEAN`); obsługa w `MrcDataUtils` (`createCaseBaseInfo`, `CaseBaseInfo.getIsDocumentType()`, nagłówek z encji ustawia pole tylko dla dokumentów), `MrcObjectUtils` (`extractCaseFromHeader`, kopiowanie, `caseHeaderHashCode`) i w `hgdb-mrc-object-3.0.xsd`.

**Do zrobienia w `mercury` (wymaga zainstalowanej nowej wersji `mercury-lib` w `.m2`):** `CaseBusinessSupport` (linie ~818, ~869, ~1351 ustawiają dziś zawsze `false`: ma brać wartość z nagłówka), przegląd użyć `MrcCaseHeaderField.values()` i `switch` po tym wyliczeniu (`RestVariableBuilder`, `CaseHeaderSchema`, `CaseViewQueryBuilder`, `CaseBusiness`, raporty POI, GUI `CaseHeaderSection`), testy.

### Rozpoznanie kroku 3: `CmisService` w `mercury-ws-app` (2026-11-01, tylko odczyt kodu)

- **Szkic:** pakiet `org.mercury.cxf.ws.server.cmis.services`, 9 klas (3617 linii). `FileShareCmisServiceFactory` (`AbstractServiceFactory`) tworzy po jednej usłudze na wątek (`ThreadLocal`), owija ją `ConformanceCmisServiceWrapper` i uwierzytelnia przez `FileShareUserManager`. Usługa `FileShareCmisService` dziedziczy po `AbstractCmisService` i `CallContextAwareCmisService`. Fabryka jest wpięta w `webService.xml` (`fileShareCmisServiceFactory`, `HgdbCmisLifecycleBean`), a `repository.properties` ma tylko wpis `class=`.
- **Wniosek o bezpieczeństwie (zweryfikowane w kodzie):** `HgdbCmisLifecycleBean.afterPropertiesSet` ma na stałe wpisane loginy i hasła testowe (trzy konta) oraz repozytorium plikowe na katalogu `mercury.upload.file.target`. Dane nie są dopisane tutaj. Szkic jest więc nie tylko nieskonfigurowany, ale też zawiera wbudowane konta; to kolejny powód, żeby wymienić go w jednej zmianie (D7).
- **Uwierzytelnianie (propozycja dla kroków 3 i 5):** `RestServicesHelper` (`mercury-gui-core`) ma już `createContextBasedOnOAuth(request, response, oauthFactoryName)` (token Bearer, role z zakresu) i `createContextBasedOnSession(request)` (`Principal` kontenera, role z `GenericPrincipal`). `CallContext` z Chemistry udostępnia `HttpServletRequest` (`CallContext.HTTP_SERVLET_REQUEST`), więc fabryka może zbudować `Context` Mercury, a gdy się nie uda, rzucić `CmisPermissionDeniedException`. Basic wymaga `security-constraint` z `login-config` BASIC dla ścieżek CMIS w `web.xml` (krok 5); do tego czasu bez tokena Bearer usługa jest zamknięta.
- **Typy:** `IDocumentTypesManager.getAllDocumentTypes(Context)`, `ITypeCaseDAO.getAllCaseTypes` i `getAllDocumentTypes`, `TypeCase.getIsDocumentType()`, `TypeParam.cmisFieldName`, `MType.cmisTypeName`.
- **Wstrzykiwanie:** klasy w `mercury-ws-app` korzystają z `@Autowired` (np. `CaseTypeServicesController`); fabrykę CMIS tworzy Spring (`webService.xml`), więc może dostać beany logiki.

### Decyzja: repozytorium CMIS = punkt zamontowania (2026-11-01, autor)

- **Typy (opcja B):** każdy typ sprawy Mercury może być typem CMIS (podtyp `cmis:folder`, a typ dokumentowy podtyp `cmis:document`).
- **Obiekty:** repozytorium CMIS to punkt zamontowania `CaseCatalog` (`Case2CaseMountPoint`, identyfikator = nazwa). Katalog (folder i dokumenty) obejmuje tylko sprawy umieszczone w danym punkcie zamontowania.
- **Reguła:** punkt zamontowania repozytorium dokumentów nie może być pusty ani domyślny.
- **Stan kodu (zweryfikowane):** `Case2CaseLogic` traktuje pusty punkt zamontowania jak brak punktu (`checkMountpoint` zwraca `null`), a `addNodeToMountPoint` tworzy punkt, którego nie ma. CMIS musi więc sam odrzucać pustą nazwę przed wywołaniem logiki, a nazwę repozytorium sprawdzać w `ICase2CaseMountPointDAO` (słownik `MDictDAO<Mp, String>`).
- **Do ustalenia przy `getRepositoryInfos`:** czy lista repozytoriów to wszystkie punkty zamontowania, czy tylko te oznaczone jako repozytoria dokumentów (dziś `Case2CaseMountPoint` służy też innym zastosowaniom katalogu spraw; przypuszczenie, nie sprawdzono użyć).

### Realizacja: krok 3, szkielet usługi CMIS (2026-11-01, `hgdb-049` w `mercury`, niezacommitowane)

**Zmiany w `mercury-ws-app`:**
- Nowy pakiet `org.mercury.cmis.server`: `CmisServerConfig` (właściwości `mercury.cmis.repositories` i `mercury.cmis.maxContentSize`), `MercuryCmisRepositoryManager` (repozytorium = punkt zamontowania, informacja o repozytorium), `MercuryCmisTypeManager` (typy CMIS z typów Mercury), `MercuryCmisService` (`AbstractCmisService`), `MercuryCmisServiceFactory`, `MercuryCmisLifecycleBean`, `CmisAuthenticator` i `DenyAllCmisAuthenticator`.
- Usunięty szkic `FileShare*` (8 klas), `ContentRangeInputStream`, `HgdbCmisLifecycleBean` (wraz z wbudowanymi kontami) i `example-type.xml`. `webService.xml` tworzy teraz `mercuryCmisServiceFactory` (autowiring po typie menedżerów typów) i `mercuryCmisLifecycleBean`; `repository.properties` wskazuje nową fabrykę.

**Zasady:**
- Lista repozytoriów: `mercury.cmis.repositories` (rozdzielona przecinkami). Gdy właściwości nie ma, jest jedno przykładowe repozytorium `documents`, więc po instalacji bez zmian w konfiguracji CMIS ma repozytorium. Puste elementy listy są pomijane (punkt zamontowania nie może być pusty). Repozytorium spoza listy daje `CmisObjectNotFoundException`.
- Typy: `cmis:folder` i `cmis:document` są typami bazowymi; każdy najnowszy typ sprawy (`isDocumentType=false`) jest podtypem folderu, a typ dokumentowy podtypem dokumentu; identyfikator typu to kod typu Mercury. Pola typu stają się właściwościami (`BOOLEAN`, `INTEGER`, `NUMBER`/`DECIMAL`/`DOUBLE` jako `DECIMAL`, daty i czas jako `DATETIME`, reszta tekst); pole z `cmisFieldName` równym nazwie właściwości systemowej jej nie zastępuje.
- Zaimplementowane: `getRepositoryInfos`, `getRepositoryInfo`, `getTypeChildren`, `getTypeDefinition`, `getTypeDescendants`. `getObject`, `getChildren`, `getObjectParents` zwracają „nieobsługiwane” do kolejnego kroku.

**Założenia do potwierdzenia:**
- Folder główny repozytorium ma identyfikator `@root` i jest wirtualny (nie jest sprawą); sprawy bez rodzica w danym punkcie zamontowania są jego dziećmi. Dotyczy kroku `getObject` i `getChildren`.
- Punkt zamontowania z listy nie jest jeszcze zakładany w bazie. Zakładanie przy starcie (system context, transakcja) albo przy pierwszym zapisie wymaga decyzji w kroku zapisu; `Case2CaseLogic.addNodeToMountPoint` tworzy punkt sam, a CMIS ma przepuszczać tylko nazwy z listy.
- Uwierzytelnianie: `DenyAllCmisAuthenticator` odrzuca każde wywołanie (usługa zamknięta). Prawdziwy uwierzytelniacz (Basic i token Bearer, SSO) to krok 5. Atom używa `BasicAuthCallContextHandler`, który przekazuje do fabryki tylko nazwę i hasło, więc weryfikację w tym samym realmie co logowanie hasłem robi fabryka, a nie `login-config` kontenera (korekta wcześniejszego założenia o `Principal`).
- Szablony `mercury.properties` w pakiecie instalacyjnym (`mercury-cmd`) i obrazie Docker (`mercury-docker`) nie dostały wpisu `mercury.cmis.repositories`; to inne repozytoria, a domyślne `documents` działa bez wpisu.

**Testy:** `MercuryCmisServerTest` (9 testów, bez bazy): konfiguracja, repozytoria, typy bazowe, role typów, właściwości i ich typy, stronicowanie, drzewo typów, odrzucanie przez uwierzytelniacz domyślny. Wynik 9 z 9. Nie sprawdziłem na uruchomionym serwerze (Tomcat), więc nie wiem, czy autowiring po typie w `webService.xml` znajduje oba menedżery typów.

### Realizacja: punkt zamontowania i folder główny jako dane startowe, szablony (2026-11-01, `hgdb-049` w `mercury`, niezacommitowane)

**Zmiana względem szkieletu:** folder główny repozytorium nie jest już wirtualnym `@root`. To sprawa typu predefiniowanego `CmisFolder` (kod inwentaryzacyjny `CMIS-ROOT:<repozytorium>`, nazwa CMIS równa identyfikatorowi repozytorium) w punkcie zamontowania o tej samej nazwie. Jej identyfikator trafia do `RepositoryInfo.rootFolderId`.

**Mechanizm:**
- `org.mercury.cmis.CmisRepositoryInitializer` (`mercury-srv`): dla każdego repozytorium z `mercury.cmis.repositories` szuka folderu głównego (`ICaseLogic.findByProperty` po polu `CmisName`, potem kod inwentaryzacyjny), a gdy go nie ma, zapisuje sprawę przez `ICaseBusiness.save`, i zawsze woła `ICase2CaseLogic.addNodeToMountPoint`, który tworzy punkt zamontowania, jeśli go brak. Powtórzenie niczego nie dubluje. Pusty identyfikator jest odrzucany (`IllegalArgumentException`), a błąd jednego repozytorium nie blokuje pozostałych (log `error`).
- `MercuryCmisLifecycleBean` (`mercury-ws-app`) uruchamia inicjalizator po `ContextRefreshedEvent` (raz, kontekst systemowy `sysmercury`) i rejestruje foldery główne w `MercuryCmisRepositoryManager`. Repozytorium bez folderu głównego (nieudana inicjalizacja) nie jest wystawiane w `getRepositoryInfos`.

**Ustalenia z testów na bazie (ważne):**
1. Zapis sprawy do predefiniowanego typu `CmisFolder` tworzył jego wersję 2. Przyczyny (zweryfikowane na `mercury-db-test`): (a) przy pierwszym ładowaniu danych predefiniowanych typy miały `sumControl = null`, bo pętla sum czytała pola z encji, która ich jeszcze nie znała; (b) źródło żądania było dopisywane do typu; (c) pola typu z CSV różnią się od pól generowanych przy zapisie (`updateable`, `withEmptyOption`, `hasMultiValues`, `arg1..3`, etykiety, `isRequired`).
2. Naprawy: `PredefiniedValuesLoader` liczy sumę kontrolną także z listy dopiero załadowanych pól; nowa reguła `CaseBusinessSupport.isLockedPredefinedType` (typ nieedytowalny z ujemnym identyfikatorem): zapis sprawy go nie zmienia (`changeType=false` w kroku 4 i w `CaseBusiness.transform2Cases`), źródło żądania nie powoduje nowej wersji. Typy BPM (nieedytowalne, ale z identyfikatorami z sekwencji) reguły nie obejmuje.
3. Skutek reguły: pole spoza typu zablokowanego nie rozszerzy go (typ pozostaje taki, jak w CSV). Do rozważenia przy `CmisDocument` (te same zasady).

**Testy:** `CmisRepositoryInitializerTest` (scenariusz na `mercury-db-test`, 1 z 1: dwa repozytoria, brak nowej wersji typu, wpisy w `IGO_DA_CASE2CASE_MPS` i `IGO_DA_CASE2CASE`, powtórzenie bez duplikatów, odrzucenie pustego punktu), `CmisRepositoryInitializerXmlTest` (2, bez bazy), `MercuryCmisServerTest` (9), `PredefinedDocumentTypesTest` (5). Nie sprawdzone: pełny `SrvTest` i `testMERC_0168_Scenarios` po zmianach w `CaseBusiness*` i loaderze, start na Tomcacie (autowiring po typie w `webService.xml`, zdarzenie `ContextRefreshedEvent`, wyścig dwóch węzłów klastra przy tworzeniu folderu głównego).

**Szablony `mercury.properties`:** dopisane `mercury.cmis.repositories=documents` i `mercury.cmis.maxContentSize=10485760` w `mercury` (`mercury-server/src/main/config/jenkins` i `.../scichy`), `mercury-cmd` (`system-config-sample/linux`) i `mercury-docker` (`docker-init-config`). Parametry są opcjonalne: bez nich działa to samo (domyślne wartości w kodzie), więc starsze konfiguracje nie wymagają zmian.

### Realizacja: krok 3, odczyt obiektów (2026-11-01, `hgdb-049` w `mercury`, niezacommitowane)

**Zakres:** `MercuryCmisObjectManager` (`mercury-ws-app`, tylko odczyt) i podpięcie w `MercuryCmisService`: `getObject`, `getChildren`, `getObjectParents` (a przez nie także `getFolderParent` Chemistry). Każde wywołanie najpierw sprawdza, że repozytorium jest skonfigurowane.

**Zasady (z kodu `CaseCatalog`, zweryfikowane w zapytaniach nazwanych, nie na bazie):**
- Identyfikator obiektu to identyfikator sprawy; rolę wyznacza `isDocumentType` typu. Węzeł katalogu to `CaseRootVersion`, więc zapytania używają `rootVersionId` sprawy.
- Krawędź katalogu ma głębokość: 1 to wpis własny węzła (rodzic = dziecko), 2 to bezpośrednia krawędź rodzic-dziecko, więcej to domknięcie przechodnie. Dzieci folderu i jego rodzic to krawędzie o głębokości 2 w punkcie zamontowania równym repozytorium.
- Obiekt należy do repozytorium, gdy jest jego folderem głównym albo ma w nim krawędź rodzica. Inny obiekt (także istniejący) daje „nie znaleziono”. Konsekwencja dla zapisu: każdy nowy folder i dokument musi dostać krawędź od folderu nadrzędnego (folder główny to jedyny węzeł bez rodzica).
- `cmis:name`: pole `CmisName`, potem kod inwentaryzacyjny, potem `CID:<id>`. Kolizje nazw w folderze (dopisek `(id)`) nie są jeszcze obsługiwane.
- Właściwości: systemowe (id, typ bazowy i obiektu, nazwa, twórca, daty, opis), dla folderu `cmis:parentId` (a dla głównego `cmis:path` = `/`), dla dokumentu właściwości wersji (etykieta z `CmisVersionLabel` albo `1.0`, seria wersji = `rootVersionId`, najnowsza gdy status sprawy nie jest `Z`), a do tego pola typu (tekst, logiczne, liczby; pola wielowartościowe i daty pominięte). Pole `CmisName` występuje obok `cmis:name`, zgodnie z definicją typu.

**Czego brak (świadomie):** `cmis:path` poza folderem głównym, `getObjectByPath`, filtr właściwości, dozwolone akcje, treść dokumentu (`contentStream*`), uprawnienia sprawy (przypuszczenie: `ICaseLogic.find` stosuje uprawnienia kontekstu, nie sprawdzone), daty z pól typu.

**Testy:** `MercuryCmisObjectManagerTest` (10, logika podstawiona przez `Proxy`, bez bazy): folder główny, folder, dokument, wersje, nazwa zastępcza, obiekt spoza repozytorium, dzieci bezpośrednie ze stronicowaniem, rodzice, dokument nie jest folderem. Razem z `MercuryCmisServerTest` 19 z 19. Nie sprawdzone na bazie ani przez klienta CMIS (np. Workbench): semantyka głębokości krawędzi wynika z odczytu zapytań, a nie z uruchomienia.

### Realizacja: krok 3, zapis obiektów (2026-11-01, `hgdb-049` w `mercury`, niezacommitowane)

**Zakres:** `MercuryCmisObjectWriter` (`mercury-ws-app`) i podpięcie w `MercuryCmisService`: `createFolder`, `createDocument` (bez treści), `updateProperties`, `deleteObject`. Stan git na początku: wszystkie repozytoria (workspace, `mercury`, `mercury-lib`, `mercury-cmd`, `mercury-docker`) czyste, zatwierdzone przez autora.

**Zasady:**
- Typ: `cmis:folder` i `cmis:document` odwzorowują się na predefiniowane `CmisFolder` i `CmisDocument`; inny typ musi istnieć, mieć właściwą rolę (`isDocumentType`) i pole `CmisName`, bo tylko tam zapisujemy `cmis:name` (inaczej `CmisConstraintException`).
- Nazwa (`cmis:name`) jest wymagana i unikalna wśród bezpośrednich dzieci folderu (`CmisNameConstraintViolationException`); ta sama nazwa w innym folderze jest dozwolona. Przy zmianie nazwy obiekt nie koliduje sam ze sobą.
- Tworzenie: XML z nagłówkiem (kod typu, `isDocumentType` zgodnie z rolą, status `A`) i **wszystkimi polami typu** (puste, gdy brak wartości), deklarowany typ pola z definicji; zapis `ICaseBusiness.save` w kontekście użytkownika, potem krawędź od folderu nadrzędnego (`ICase2CaseLogic.insert` z punktem zamontowania = repozytorium). Pełny komplet pól chroni przed nową wersją typu.
- `updateProperties`: zmiana tylko podanych pól przez `ICaseBusiness.updateCaseParamsByParams`; folder główny nie podlega zmianie.
- `deleteObject`: folder główny i niepusty folder nie mogą być usunięte (`CmisConstraintException`); usuwany jest węzeł z punktu zamontowania, potem sprawa (`ICaseBusiness.remove`).
- Właściwości typu data i czas dają `CmisNotSupportedException` (jeszcze bez odwzorowania zapisu dat). `createDocument` z treścią dostaje `CmisNotSupportedException`; polityki, ACL, `checkOut`/`checkIn` nie są obsługiwane.

**Niezweryfikowane (logika i biznes podstawione, bez bazy):** zachowanie `ICaseBusiness.save` z `isDocumentType` w nagłówku na typie edytowalnym, kolejność „usuń węzeł z katalogu, potem sprawę” (czy `remove` czyści też krawędzie i archiwizuje), semantyka `ICase2CaseLogic.insert` dla `Case2Case` zbudowanego z wczytanych spraw, uprawnienia kontekstu użytkownika przy zapisie.

**Testy:** `MercuryCmisObjectWriterTest` (10) + wcześniejsze: `MercuryCmisServerTest` (9) i `MercuryCmisObjectManagerTest` (10), razem 29 z 29.

### Realizacja: krok 5, uwierzytelnianie Basic i token Bearer (2026-11-01, `hgdb-049` w `mercury`, niezacommitowane)

**Mechanizm:** `HttpCmisAuthenticator` (`mercury-ws-app`) zastępuje `DenyAllCmisAuthenticator` (usunięty). Fabryka wywołuje go przy każdym `getService`; wszystkie wiązania (Atom, Browser, SOAP) idą tą samą drogą, bo uwierzytelniacz czyta nagłówek `Authorization` z `HttpServletRequest` w `CallContext`.
- **Bearer:** `RestServicesHelper.createContextBasedOnOAuth` z fabryką OAuth jak w REST (`mercury.rest.security.oauthFactoryName`, domyślnie `mercuryDbOAuthFactory`). Rola i użytkownik pochodzą z tokenu, więc jeden token działa dla spraw i dokumentów (SSO).
- **Basic:** nazwa i hasło (z `CallContext`, a gdy ich brak, z nagłówka) są sprawdzane w realmie wskazanego klienta OAuth, czyli w tym samym realmie, który sprawdza hasło przy wydawaniu tokena (`RestServicesHelper.authenticateInOAuthRealm`, nowa metoda w `mercury-gui-core`). Klienta wskazują parametry `mercury.cmis.security.oauthClientId` i `mercury.cmis.security.oauthClientSecret`; bez nich Basic jest wyłączone, a Bearer działa.
- Kontekst z `Principal`: nowa metoda `RestServicesHelper.createContextBasedOnPrincipal` (dawna treść `createContextBasedOnSession`, która teraz ją wywołuje).
- Brak lub błędne dane: `CmisUnauthorizedException` (HTTP 401).

**Inne zmiany:** z `web.xml` usunięte `/cmisws10/*` i `/cmisws11/*` z filtra `RemoteBasicAuthFilter` (stały sekret usługi nie jest uwierzytelnianiem użytkowników); `mercury-ws-app/pom.xml` ma zależność `tomcat-catalina` (`provided`), bo realm używa `GenericPrincipal`; szablony `mercury.properties` (4 pliki) dostały zakomentowane parametry klienta (bez wartości).

**Ograniczenia i ryzyka (przypuszczenia, bez uruchomienia na Tomcacie):**
- Ścieżki `/atom/*`, `/browser/*` i `/cmis-endpoints.json` nie mają `security-constraint` (obserwacja 87): usługa jest zamknięta przez fabrykę (401 bez uwierzytelnienia), a `cmis-endpoints.json` jest nadal publiczny (tylko opis punktów dostępu).
- Wiązanie Browser używa `TokenCallContextHandler` (własne tokeny Chemistry po pierwszym uwierzytelnieniu); jego współpraca z naszym nagłówkiem nie była sprawdzana.
- Wiązanie SOAP: czy `CmisWebServicesServlet` przekazuje nagłówek Basic w `CallContext` bez dodatkowego handlera, do sprawdzenia klientem.
- Każde żądanie Basic odpytuje realm (LDAP lub baza); brak pamięci podręcznej.
- Token Bearer niesie role z zakresu (`scope`); weryfikacja kontekstu jak w `ContextVerificationAdvice` nie jest powtarzana.

**Testy:** `HttpCmisAuthenticatorTest` (5: Basic z podstawionym weryfikatorem, brak i błędne dane, Bearer z nieznanym tokenem, Basic wyłączone bez klienta, rozbieranie nagłówka z dwukropkiem w haśle); razem 33 testy CMIS w `mercury-ws-app` bez błędów. Nie sprawdzone: prawdziwy token i prawdziwy realm (wymaga serwera i klienta OAuth).

### Realizacja: krok 3, treść plików (2026-11-01, `hgdb-049` w `mercury`, niezacommitowane)

**Zakres:** `MercuryCmisContentManager` (`mercury-ws-app`) i obsługa w `MercuryCmisObjectWriter` oraz `MercuryCmisService`: `createDocument` ze strumieniem, `getContentStream` (z zakresem `offset`/`length`), `setContentStream` (z flagą `overwriteFlag`), `deleteContentStream`; `deleteObject` usuwa też treść.

**Zasady:**
- Treść leży w istniejącym mechanizmie plików (`IFileIndexLogicInternal`): katalog `mercury.upload.file.target`, nazwa na dysku `cmis_<uuid>` (nazwa na dysku jest globalnie unikalna), identyfikatorem treści jest `FileIndex.id`. W klastrze zapis i odczyt na obcym węźle obsługuje logika plików (RMI), a `CN001RequiredNodeNotAvailableException` daje `CmisRuntimeException` „The content is temporarily unavailable”, a `FI001FileNotExists` daje „nie znaleziono”.
- Opis treści trzyma sam dokument w polach `CmisContentStreamId`, `CmisFileName`, `CmisMimeType`, `CmisContentSize`; typ dokumentu bez wszystkich czterech pól odrzuca treść (`CmisConstraintException`), ale dokument bez treści tworzy się normalnie. Pola te są dla klienta tylko do odczytu (typ CMIS i `updateProperties`/`createDocument` je ignorują), bo identyfikator treści z klienta wskazywałby dowolny plik.
- Plik jest zapisywany i czytany w kontekście systemowym; wywołujący sprawdza wcześniej uprawnienia sprawy przez zwykłe wczytanie obiektu w kontekście użytkownika (przypuszczenie, że `ICaseLogic.find` stosuje uprawnienia kontekstu, nie sprawdzone).
- Limit rozmiaru: `mercury.cmis.maxContentSize` (domyślnie 10 MB), sprawdzany przez zadeklarowaną długość i przy czytaniu strumienia (strumień bez długości też jest ograniczony). Treść jest w pamięci (tablica bajtów), więc to także limit pamięci na żądanie.
- Spójność: gdy sprawa nie powstanie (błąd zapisu), nowy plik jest usuwany; przy zmianie treści poprzedni plik jest usuwany dopiero po zapisaniu nowego opisu; niepowodzenie usunięcia pliku trafia do dziennika (`warn`), bo sprawa jest już zapisana.
- Właściwości CMIS dokumentu `cmis:contentStreamId`, `cmis:contentStreamLength`, `cmis:contentStreamMimeType`, `cmis:contentStreamFileName` pochodzą z tych pól; pola typu o tych samych nazwach nadal widać jako zwykłe właściwości.

**Testy:** `MercuryCmisContentTest` (11, mechanizm plików i biznes podstawione): zapis i opis treści, domyślna nazwa i typ MIME, blokada pól treści, limit (deklarowany i rzeczywisty), typ bez pól treści, brak sieroty po błędzie zapisu, odczyt i zakresy, mapowanie błędów (brak treści, brak pliku, węzeł niedostępny), zastąpienie i usunięcie treści, usunięcie dokumentu. Razem 44 testy CMIS w `mercury-ws-app` bez błędów. Scenariusz `CmisContentFileScenario` (`CmisContentFileTest`, baza testowa, 1 z 1) sprawdza na prawdziwej logice ścieżkę, na której opiera się treść: `saveFile`, `findFileByFileName`, `find` po identyfikatorze, `copy2OutputStream`, `deleteFile`. Nowy klucz profilu: `test.skip.package.CmisContentFileTest=true` (w `scichy-test` dodany; w `scichy` dopisuje autor).

**Nie sprawdzone:** zapis i odczyt między węzłami klastra, rzeczywiste uprawnienia użytkownika do sprawy, duże pliki (pamięć), daty modyfikacji treści, `checkOut`/`checkIn`.

### Pierwszy test na działającym serwerze dev (2026-11-01, `http://127.0.0.1:8080/mercury-ws-app`)

Użytkownik testowy: domyślny administrator (dane podał autor). Badane `curl`-em przez wiązanie Browser (JSON) i Atom.

**Zweryfikowane na serwerze:**
- Start: w dzienniku `Utworzono folder główny 'CmisFolder.5783302' repozytorium CMIS 'documents'`; brak błędów autowiringu `webService.xml`.
- Bez uwierzytelnienia `/atom`, `/atom11`, `/browser`: 401 z `WWW-Authenticate: Basic realm="CMIS"`; `/cmisws10`, `/cmisws11` (GET): 200 (strona opisowa usługi). Błędne dane Basic i śmieciowy Bearer: 401. Przy wyłączonym LDAP realm zwracał `null` (log `CommunicationException`), więc 401; po starcie LDAP Basic działa.
- Basic (admin) w realmie klienta `GIUPortalClient`: dokument usługi Atom (`documents`, kolekcja główna z id folderu głównego) oraz lista repozytoriów wiązania Browser z poprawnym `rootFolderId`.
- Typy: dwa typy bazowe; pod `cmis:folder`: `CalendarUser*`, `CmisFolder`, `BpmBPDInstance`, `BpmTask`, `MrcUnknownBusinessObject`; pod `cmis:document`: `CmisDocument`; definicja typu `CmisDocument` zwracana z właściwościami.
- `children` folderu głównego po identyfikatorze: pusta lista (poprawnie).

**Błędy znalezione i naprawione w kodzie (wymagają ponownego wdrożenia WAR):**
1. `getObject` kończył się błędem `failed to lazily initialize a collection of role ...TypeCase.typeParams`: pola typu dołączonego do sprawy są ładowane leniwie, a poza transakcją nie da się ich odczytać. Naprawa: `MercuryCmisObjectManager.fullType` pobiera pełny typ (`ITypeCaseLogic.find(context, id, true)`) przy wczytaniu sprawy, dzieci i rodziców; `MercuryCmisObjectWriter` robi to samo dla typu z `findLastVersionByTypeCode`. Ten sam błąd groził zapisowi i treści.
2. Adres `.../browser/documents/root?cmisselector=children` (bez `objectId`) kończył się „Not supported!”, bo wiązanie szuka obiektu po ścieżce `/`, a `getObjectByPath` nie był zaimplementowany. Dodane: `getObjectByPath` (ścieżka z nazw CMIS od folderu głównego, `/` to folder główny) i `cmis:path` folderu w `getObject` (liczone przez przejście w górę drzewa; dla listy dzieci nie jest liczone).
3. Informacja o repozytorium deklarowała `capabilityContentStreamUpdatability: none`, mimo obsługi `setContentStream`; zmienione na `ANYTIME`.

**Uwagi z testu:** opis typów (`description`) pokazuje niewyrenderowany znacznik zasobu (`${cmis.document.typeCase.description}`); nazwa wyświetlana to kod typu. Do poprawy przez wyrenderowanie kluczy zasobów w `MercuryCmisTypeManager`. Wywołania z błędnym tokenem Bearer zapisują w dzienniku ostrzeżenie ze stack trace (kod wspólny z REST, `RestServicesHelper.createContextBasedOnOAuth`).

**Testy po zmianach:** 45 testów CMIS w `mercury-ws-app` bez błędów (nowy: ścieżki i `cmis:path`).

## Refaktor do warstwy biznesowej i poprawki klastrowe (2026-11-01)

Logika domenowa CMIS przeniesiona z `mercury-ws-app` do `mercury-srv`, do wspólnego pakietu `org.mercury.business.cmis` (wzór `ITypeCodeBusiness`; skan `logic-context.xml`, więc działa w węźle jednowęzłowym i klastrowym).

**Podział warstw:**
- `mercury-srv`: `ICmisRepositoryBusiness` (`internal/api`) i `CmisRepositoryBusiness` (`@Service`) – inicjalizacja repozytoriów, nawigacja, ścieżki, zapis, unikalność nazw, usuwanie, treść plików. Pomocnicze: `CmisServerConfig`, `CmisBusinessException` (rodzaje: NOT_FOUND, INVALID_ARGUMENT, CONSTRAINT, NAME_CONSTRAINT, CONTENT_ALREADY_EXISTS, NOT_SUPPORTED, UNAVAILABLE, FAILURE), `CmisContent`, `CmisCaseUtils`. Usunięty `org.mercury.cmis.CmisRepositoryInitializer`.
- `mercury-ws-app` (adapter protokołu): `MercuryCmisService`, `MercuryCmisObjectMapper`, `CmisExceptionMapper`, `MercuryCmisRepositoryManager`, `MercuryCmisServiceFactory`, `MercuryCmisLifecycleBean`, `MercuryCmisTypeManager`, uwierzytelnianie. Usunięte: `MercuryCmisObjectManager`, `MercuryCmisObjectWriter`, `MercuryCmisContentManager`.

**Poprawki klastrowe:**
1. Metody biznesu ustawiają flagę kierowania (`NodeStatusMonitor.PROP_METHOD_REMOTE_ACCESS`) i `setDirectRequest(false)` przed wywołaniami `caseBusiness`/`caseLogic`.
2. Folder główny tworzy tylko węzeł z prawem zapisu (`!isClustered || rola != RO`). Gdy dwa węzły utworzą go równocześnie, zostaje folder o najmniejszym id, a własny jest usuwany.
3. Korzeń repozytorium jest wyszukiwany po kodzie inwentaryzacyjnym `CMIS-ROOT:<repo>`, nie trzymany w pamięci startowej (węzeł bez zapisu znajduje go przy pierwszym użyciu).

**Testy:** `CmisRepositoryBusinessTest` (28, jednostkowe), `CmisRepositoryDbTest` (scenariusz na `mercury-db-test`, OK), w `mercury-ws-app`: `MercuryCmisServerTest`, `MercuryCmisAdapterTest` (nowy: odwzorowanie obiektów, stronicowanie, przekazywanie właściwości i treści, mapowanie błędów), `HttpCmisAuthenticatorTest` – razem 23 testy bez błędów. Nowy klucz profilu: `test.skip.package.CmisRepositoryDbTest` (stare `CmisRepositoryInitializerTest`, `CmisContentFileTest` nieaktualne).

**Niezweryfikowane (przypuszczenia):** zachowanie w klastrze (routing, wyścig korzenia, pliki między węzłami), autowiring `ICmisRepositoryBusiness` w `webService.xml` na działającym Tomcacie, uprawnienia użytkownika przy odczycie. Wymaga ponownego wdrożenia WAR i powtórzenia testu `curl` na dev.

## Dokumentacja w docusaurus-hgdb (2026-11-01)

Nowa sekcja „CMIS” (gałąź `hgdb-049`, niezacommitowana), EN w `docs/007_CMIS/`, PL w `i18n/pl/docusaurus-plugin-content-docs/current/007_CMIS/`:
- `index.mdx`: odwzorowanie CMIS na Mercury, parametry `mercury.cmis.*`, adresy wiązań (`/browser`, `/atom11`, `/atom`), uwierzytelnianie Bearer i Basic.
- `001_Workbench.mdx`: instalacja Workbencha, połączenie (Browser i AtomPub), scenariusz testowy, ograniczenia.
- Dodane: tag `cmis` (`docs/tags.yml`, PL `tags.yml`) i etykieta kategorii w `i18n/pl/.../current.json`.
- Sekret klienta OAuth nie jest opisany (strona wymienia tylko nazwy parametrów).
- Weryfikacja: `docusaurus build` dla `en` i `pl` przechodzi (ostrzeżenie o braku daty git dla nowych plików jest oczekiwane). Zawartość scenariusza Workbench nie została jeszcze sprawdzona klientem; autor testuje go sam.
- Nieopisane: wiązania SOAP (`/cmisws10`, `/cmisws11`) – nie testowane klientem.

## Nazwa obiektu przy zapisie (2026-11-01)

Zgłoszenie z testu: utworzenie obiektu typu `BpmBPDInstance` (typ bez pola `CmisName`) kończyło się błędem `constraint: Type ... has no field 'CmisName'`. Decyzja autora: odczyt zostaje (`CmisName` → `inventoryCode` → `CID:<id>`), a zapis przyjmuje tę samą kolejność.
- Tworzenie: typ z polem `CmisName` zapisuje nazwę w polu (`inventoryCode` pusty); typ bez pola zapisuje nazwę w `inventoryCode` nagłówka sprawy. Wymóg pola `CmisName` usunięty.
- Zmiana nazwy (`cmis:name`): ta sama reguła, przez pole nagłówka `mrcCaseHeader.inventoryCode` w `updateCaseParamsByParams`.
- Unikalność nazw w folderze liczona przez `nameOf`, więc obejmuje oba rodzaje typów.
- Testy: `CmisRepositoryBusinessTest` 30 OK (nowe: typ bez pola, typ z polem), `CmisRepositoryDbTest` OK (nowy krok 5b: własny typ `CmisNoNameType`, tworzenie, duplikat, zmiana nazwy, ścieżka, brak nowych wersji typu).
- Ryzyka (obserwacja 137): `inventoryCode` powinien być unikalny, ale mechanizmy jego obsługi nie są zaimplementowane, więc dziś jest pusty; ma tylko zwykły indeks, więc nazwa może się powtórzyć w różnych folderach (unikalność w folderze pilnuje CMIS). Zmiana nazwy zmienia kod widoczny dla innych funkcji. Po wdrożeniu mechanizmów kodu inwentaryzacyjnego zablokować zmianę nazwy dla typów bez pola `CmisName`.

**Test na dev po wdrożeniu (typ bez `CmisName`):** utworzenie folderu typu `BpmBPDInstance`, odczyt po ścieżce, duplikat nazwy (409), zmiana nazwy i usunięcie działają, o ile klient poda pole `bpmProcessInstanceId`. Typ ma regułę unikalności (`TypeCode.uniqueConstraintParamName`), a bez wartości pola Mercury odrzuca zapis (`Naruszenie integralności… pole nie może być puste`), co serwer CMIS zwracał jako `runtime`/500.
- Zmiana (decyzja autora): w definicji typu CMIS (`MercuryCmisTypeManager`) pola z reguły unikalności typu są oznaczone jako wymagane (`required=true`). Elementy formuły rozdziela `||`, literały w apostrofach są pomijane. Test: `MercuryCmisServerTest.fieldsOfUniqueRuleAreRequired`; razem 24 testy `mercury-ws-app` OK.
- Nieobjęte: błąd naruszenia integralności nadal wraca jako `runtime`/500 (do ewentualnego mapowania na `constraint`).
