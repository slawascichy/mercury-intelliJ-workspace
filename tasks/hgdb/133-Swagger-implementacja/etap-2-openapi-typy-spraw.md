# [133] Etap 2 – Dynamiczna dokumentacja OpenAPI typu sprawy

Zadanie nadrzędne: [TASK.md](TASK.md). Zależy od: [etap 1](etap-1-openapi-statyczne.md)
(Swagger UI i kontroler specyfikacji).

## Cel zadania
Serwer w czasie działania buduje dokumentację OpenAPI dla podanego kodu typu sprawy,
na podstawie ostatniej wersji typu (`isLatestVersion = true`) albo wskazanej wersji (parametr `v`). Dokumentacja opisuje
**logiczny JSON sprawy** (decyzja D2 = a) i usługi `*ExtRest`, które go przyjmują i zwracają.

## Kontekst i Wymagania

Model typów, wersjonowanie i propagację zmian opisuje [TASK.md](TASK.md#definicje-typów-spraw).

### Logiczny JSON już istnieje

Nowy kontrakt REST nie jest potrzebny. Ręcznie pisane kontrolery w
`mercury-ws-app/src/main/java/pro/ibpm/mercury/rest/server/actions/business/data/` już pracują
na zwykłym JSON-ie sprawy:

| Kontroler | Ścieżka | Przykładowe metody |
|---|---|---|
| `CaseBusinessExtRest` | `/rest/service/CaseBusinessExtRest` | `find`, `findFirst`, `save`, `initModel`, `loadSampleByTypeCode`, `searchByParams`, `searchByQuery` |
| `CaseSearchExtRest` | `/rest/service/CaseSearchExtRest` | `searchByQuery`, `groupByQuery`, `dateMetricQuery` |
| `Case2CaseBusinessExtRest` | `/rest/service/Case2CaseBusinessExtRest` | `getAllChildrenNodes`, `getAllParentsNodes` |
| `CaseHistoryTraceBusinessExtRest` (pakiet `org.mercury`) | `/rest/service/CaseHistoryTraceBusinessExtRest` | `find`, `findByCaseId` |

Wariant `rest2/.../CaseBusinessExtRest` jest przestarzały.

Konwersja:

- **JSON → sprawa:** `RestVariableReader.readObject` (`rest/server/utils/RestVariableReader.java:78`)
  z regułami w `RestReaderHelper`. Działa analogicznie do `XMLReaderHelper` (`mercury-srv-api`):
  rozpoznaje kolejno NVP, Entry, `metadata`, sprawę (obiekt z `mrcCaseHeader`), listę, URL
  i nagłówek. Resztę traktuje jako LOB JSON (`RestVariableReader.java:244-330`).
- **Sprawa → JSON:** `RestVariableBuilder.buildObjectElement` (`RestVariableBuilder.java:86`),
  analogicznie do `XMLVariableBuilder`.

Kształt logicznego JSON-a (z kodu):

```json
{
  "mrcCaseHeader": { "typeCode": "...", "className": "...", "caseId": "...", "status": "..." },
  "metadata": { "className": "...", "status": "..." },
  "poleTekstowe": "abc",
  "poleLiczbowe": 12.5,
  "poleData": "16-10-2026",
  "poleSlownikowe": { "name": "...", "value": "..." },
  "poleMapy": { "key": "...", "value": "..." },
  "poleWielowartosciowe": ["a", "b"],
  "sprawaZalezna": { "mrcCaseHeader": { "typeCode": "..." }, "...": "..." },
  "listaSprawZaleznych": [ { "mrcCaseHeader": { "...": "..." } } ]
}
```

- Nazwa pola = `ParamDefinition.definitionName` (`MrcDataUtils.decodePropertyName` w builderze).
- Pola nagłówka: enum `MrcCaseHeaderField` (`mercury-srv-api/.../business/data/api/MrcCaseHeaderField.java`).
- NVP: `{name, value}` (`NameValuePairBean`). ENTRY/MAP: `{key, value}` (`EntryValue`).
- Element nagłówka `metadata` (`className`, `status`) jest opcjonalny (`RestReaderHelper.identifyMetaData` :120).
- Żądanie `save`/`initModel` (`CaseBusinessExtRest.java:457-537`) to
  `{ "context": {...}, "jsonNode": <sprawa lub tablica spraw>, "forceAddStore2Type": bool }`.
- Odpowiedź: `{ "errorCode", "errorMessage", "dto": <sprawa> }` albo `"value"`
  (`RestWsStatusUtils.java:13-17`).

**Ważne dla schematu: czytnik nie korzysta z definicji typu.** Typ wartości ustala z JSON-a
(`RestReaderHelper.setValueForUnknownType` :160-247):

- liczba całkowita JSON → INTEGER, inna liczba → NUMBER, boolean → BOOLEAN;
- napis jest sprawdzany przez `NumberAnalyser` i `DateAnalyser` (krótki i długi format daty
  z kontekstu). Napis „123” może więc zostać rozpoznany jako liczba;
- napis dłuższy niż `MAX_PARAM_STRING_VALUE_LENGTH` zostaje STRING (potem typ może zmienić się na TEXT).

Dla REST dozwolone są tylko `decodeRequest` = `LOB_ONLY` lub `DATE_AND_LOB`
(`RestVariableReader.java:87-107`). Format dat w odpowiedzi zależy od `decodeResult`:
napis w formacie z kontekstu albo liczba milisekund (`RestVariableBuilder.java:472-493`).

Rozbieżność typu wartości z definicją tworzy nową wersję typu, chyba że
`mercury.saveRequestContext.forceChangeType.default=false`. Schemat ma więc wartość nie tylko
dokumentacyjną: pozwala klientowi wysyłać wartości zgodne z typem.

### Endpointy dokumentacji

- `GET /rest/openapi/types/{typeCode}.json` (oraz `.yaml`): specyfikacja OpenAPI 3 dla ostatniej
  wersji typu. Zawiera schemat `components.schemas.<typeCode>` oraz operacje `*ExtRest` związane
  ze sprawą, w których `jsonNode` / `dto` wskazują na ten schemat (`$ref`).
- `GET /rest/openapi/types/{typeCode}.json?v={wersja_typu}` (oraz `.yaml`): specyfikacja dla podanej
  wersji typu. Bez `v` zwracana jest ostatnia wersja (`isLatestVersion = true`).
  - Wersja typu ma dwie części: `TypeCase.version` (Long) i `versionMinor` (Double). Wersje sortuje się
    po `version + versionMinor` (`TypeCase.java:108`). Do ustalenia: format `v` (np. `3` lub `3.1`)
    i sposób dopasowania do pary `version`/`versionMinor`.
  - Wsparcie w `TypeCaseLogic` (`mercury-srv/.../logic/attr/TypeCaseLogic.java`):

    | Metoda | Linia | Zapytanie | Zwraca |
    |---|---|---|---|
    | `findLastVersionByTypeCode` | 534 | `QgetByCodeLastVersion` (`isLatestVersion = true`) | jedna wersja |
    | `findAllVersionByTypeCode` | 659 | `QgetByCodeAllVersions`, sortowanie `version + versionMinor DESC` | wszystkie wersje kodu |
    | `findLastVersionByTypeName` | 525 | `QgetByNameLastVersion` | lista |
    | `findAllVersionByTypeName` | 782 | `QgetByNameAllVersion`, sortowanie jak wyżej | wszystkie wersje nazwy |

    Obie metody `findAllVersion*` są też dostępne w SOAP i wygenerowanym REST
    (`mercury-ws-server-api/.../ITypeCaseAction.java:162,192`).
  - **Rekomendacja:** `findAllVersionByTypeCode(ctx, typeCode)` i wybór wersji z listy po
    `version`/`versionMinor`. Lista jest już posortowana, więc ten sam wynik daje też listę wersji
    do wyboru w Swagger UI (`GET /rest/openapi/types/{typeCode}/versions`, opcjonalnie). Nie wymaga
    nowych zapytań ani zmian w `mercury-lib`.
  - Wersje wybiera się po kodzie (`TypeCode.name`), a nie po nazwie (`typeName`). Kod grupuje wersje
    typu, a nazwa opisuje pojedynczą wersję. Przypuszczenie: w typach predefiniowanych obie wartości
    są równe, ale w ogólności nie muszą. Metody `*ByTypeName` traktować pomocniczo.
  - Istnieje też `TypeCaseDAO.findByNameAndVersion(ctx, typeName, mainVersion)` (`mercury-dao/.../TypeCaseDAO.java:510`,
    zapytanie `QgetByNameAndVersion`). Działa po nazwie i tylko po wersji głównej, ale wymusza
    inicjalizację typu (`TypeCaseHelper.forceInitalizeType`). To wzorzec dla inicjalizacji
    `typeParams`.
  - Do sprawdzenia: czy wyniki `findAllVersionByTypeCode` mają zainicjalizowane `typeParams`
    (relacja LAZY, zapytanie z cache Hibernate). Jeśli nie, budować schemat w tej samej transakcji
    (`@Transactional(readOnly = true)`) albo użyć `TypeCaseHelper.forceInitalizeType`.
  - Nieznana wersja → 404.
  - Opcja do rozważenia: `?typeId={TypeCase.id}`. Nagłówek sprawy zawiera `typeId`
    (`MrcCaseHeaderField.typeId`), więc klient może pobrać dokumentację dokładnie tej wersji typu,
    w której zapisano sprawę.
  - Wersja trafia do `info.version` specyfikacji i do rozszerzenia `x-typeVersion` schematu.
    Opis wskazuje, czy wersja jest ostatnia (`isLatestVersion`) i aktywna (`isActive`).
- Opcjonalnie `GET /rest/openapi/types`: lista kodów typów do wyboru w Swagger UI
  (konfiguracja `urls` Swagger UI).
- Dane: `TypeCaseLogic.findLastVersionByTypeCode(ctx, typeCode)` i `TypeParam` posortowane
  po `position` (`TypeCaseLogicHelper.sortByPosition` :685).
- `example`: wynik `loadSampleByTypeCode` przepuszczony przez `RestVariableBuilder`
  (to samo, co zwraca `CaseBusinessExtRest.loadSampleByTypeCode`).
- Do sprawdzenia: czy `findLastVersionByTypeCode` dociąga `typeParams` (relacja LAZY).

### Usługi per typ i parametr `CASE_AS_TYPE`

Pomysł autora (2026-10-20): usługi dokumentowane w specyfikacji typu mogą być wspierane przez parametr kontekstu, który
wskazuje typ sprawy, dzięki czemu implementacja ogólnych usług `CaseBusinessExtRest` jest wykorzystana ponownie.

**Decyzje:**

- `SaveRequestContext.SAVE_CASE_AS_TYPE` (`saveRequestContext.saveCaseAsType`) w `ContextRequestProperties`
  (`mercury-lib`) jest zastąpiony przez `RequestContextes.CASE_AS_TYPE` (`requestContext.caseAsType`). Zmieniono nazwę
  i Javadoc. Nic wcześniej nie czytało parametru (`mercury`: brak odwołań). Konstanta trafiła do nowego enuma
  `ContextRequestProperties.RequestContextes` (ogólne parametry żądania, prefiks `requestContext.`), a `SaveRequestContext`
  zostaje przy parametrach zapisu. Opisy parametru w docusaurus
  (`004_API/001_Context`, wersje `en` i `pl`) nadal mówią o starej nazwie, a zdanie „Wykorzystywane w” jest urwane.
- **Zapis (`save`, `saveList`, `initModel`):** parametr wskazuje docelową definicję typu zamiast wykrywania jej z pól.
  Sprawa z `caseId` innego typu jest **migracją**: powstaje nowa wersja w podanym typie, stara dostaje status `Z`. To zwykły
  mechanizm zmiany wersji (artykuł `003_Architecture/002_Cases_Versioning`). Sprawa bez `caseId` to nowa sprawa tego typu.
- **Odczyt (`find`, `searchBy*`):** typ wynika ze ścieżki, a nie z parametru kontekstu. Usługa dokłada filtr po typie
  (`find` po `caseId` zwraca 404 przy niezgodnym typie). `Context.viewDefinition` nie jest do tego przydatne: to lista pól
  indeksu do zwrócenia w wyniku.
- **Decyzja autora (przyjęta rekomendacja), wydanie w `mercury-lib` 3.0.4.7 razem ze zmianą nazwy parametru:** jeden kontroler z wzorcem ścieżki `/rest/service/types/{typeCode}/{operation}`
  (bez klasy per typ i bez wpisu w `/restServices`). Kontroler ustawia `CASE_AS_TYPE` w `Context` i deleguje do logiki
  `CaseBusiness`. Specyfikacja typu wskazuje te ścieżki, a schematy kopert zostają.

**Wyniki analizy kodu zapisu** (`mercury-srv`, stan z 2026-10-20):

| Miejsce | Co robi dziś | Wniosek dla `CASE_AS_TYPE` |
|---|---|---|
| `CaseBusinessSupport.step1TryReadCaseHeader` (:364) | Typ bierze z nagłówka (`typeCode`, `typeId`, `className`). Parametr kontekstu `LocalTypeId.<typeCode>` ma pierwszeństwo przed `typeId` z nagłówka | Jest precedens nadpisywania typu z kontekstu. Ten krok jest też używany dla spraw zależnych (`CaseBusiness:2609`), więc parametr musi dotyczyć tylko sprawy głównej (pierwsza iteracja) |
| `step2TryIdentifyType` (:516) | Próby po kolei: typy świeżo dodane w paczce, `typeId`, nazwa klasy + suma pól, kod + suma pól, suma pól, kod. Gdy zidentyfikowany typ ma inny kod niż żądany, **kopiuje definicję do nowego typu** (:753-767) | Samo podmienienie `typeCode` nie wystarczy: próby po nazwie klasy i `typeId` znajdą stary typ, a różnica kodu utworzy kopię jego definicji. Przy ustawionym parametrze trzeba pominąć próby 1-5 i pobrać ostatnią wersję typu `A` (`findLastVersionByTypeCode`, próba 6). Brak typu `A` powinien dać błąd, a nie nowy typ |
| `step3TryIdentifyCaseId` (:892) | Gdy nagłówek ma `caseId`, zostaje on bez zmian. Sprawę z bazy ładuje później `transform2Cases` (:1841) | Zapis z `caseId` sprawy typu `B` i typem `A` w `root.getType()` trafia do logiki jako zmiana typu |
| `step4PrepareTypeObject` (:1230) i `transform2Cases` (:1896) | Przy `forceChangeType=false` pomija zmiany typu (`setParams`), przy `true` dodaje pola do typu (`addParams`) | Dla migracji do istniejącego typu `A` zachowanie jest takie samo jak dla każdego zapisu. Pola spoza `A` dodałyby nową wersję typu `A` tylko przy `forceChangeType=true` |
| `CaseLogicHelperService.updateCaseWithHistory` (:620-912) | `typeHasChanged` (inne `TypeCase.id` niż w bazie) tworzy nową wersję: stara sprawa dostaje `Z`, nowa `previousVersionId`. Dwie gałęzie: zmieniły się też pola (zapis „jak stoi”) albo tylko typ (przepisanie wartości według wspólnych definicji parametrów, `simpleName`) | **Migracja już istnieje w warstwie logicznej.** Brakuje tylko sposobu na wskazanie docelowego typu z poziomu żądania |
| `updateCaseWithHistory` (:629-695) | Gdy zmiana typu pochodzi z warstwy biznesowej (`PROP_CHANGE_FROM_BUSINESS`) i wszystkie parametry nowego typu są w starym (po nazwie definicji i wersji), sprawa jest zapisywana w **starym** typie (`typeHasChanged = false`). Kod porównuje parametry, a nie kody typów | **Ryzyko:** migracja do typu `A`, którego pola są podzbiorem pól `B`, zostałaby po cichu zapisana jako `B`. Przy `CASE_AS_TYPE` trzeba ten krok pominąć |
| `updateCaseWithHistory` (:719-781) | Zmiana typu wymaga powiązania magazynu z kodem typu (`Store2Type`). Przy zmianie samego typu, bez powiązania, bierze pierwszy magazyn typu. Przy zmianie typu i pól rzuca `LC005TypeChangeRelationshipWithStoreNotExsistsException` | Dokumentacja migracji musi o tym wspomnieć. Przy `CASE_AS_TYPE` należy podać `forceAddStore2Type` albo magazyn |

**Do sprawdzenia przed implementacją:**

- `typeId`, `groupId` i `storeId` w nagłówku sprawy `B` przy migracji (nadpisać czy zostawić).
- Identyfikator sprawy: `CaseHelper.createCaseId(seq, typeCode)` wbudowuje kod typu w `caseId`. Sprawdzić, czy `initNewVersionCase` tworzy identyfikator z kodem nowego typu.
- Klucz główny (`uniqueConstraintParamName`) kodu `A` względem sprawy z `B`: czy wyszukiwanie po PK nie znajdzie sprawy o tej samej wartości klucza w `A` (kolizja).
- Czy wszystkie ścieżki zapisu (`save`, `saveList`, `initModel`) przechodzą przez `transform2Cases`/`step2TryIdentifyType`.

**Test na serwerze (2026-10-20, Tomcat z `mercury-server`, token OAuth `mrc-user`, typy testowe `TstMigA`, `TstMigB`, `Tst.Dot` zostały w bazie):**
migracja `A → B` przez `/types/TstMigB/save` tworzy nową sprawę w `B` z `previousVersionId` i `rootVersionId` jak w `A`, a stara
dostaje `Z` (także gdy `B` ma podzbiór pól `A`, i bez `dirty` w żądaniu: migracja ustawia `dirty` sama); `find` sprawy typu `B`
przez `/types/TstMigA/find` daje błąd, przez `/types/TstMigB/find` sprawę; `searchByQuery` i `searchByParams` przez ścieżkę typu
zwracają tylko sprawy tego typu (także z `mrc_status:A`); spec typu zwraca 200 dla `TstMigA`, `TstMigB`, `CalendarUserEvent`,
`Tst.Dot` (kod z kropką działa w spec i w ścieżce usługi) i 404 dla nieznanego typu. Błędy znalezione na serwerze i poprawione:
spec typu miała 401 mimo tokenu (brak parametru fabryki OAuth, zapasowa `mercuryDbOAuthFactory`) i 500 (`@Transactional` jest
ignorowane w kontekście serwletu, zamieniono na `TransactionTemplate`), obserwacje 46-49 w `docs/obserwacje.md`.

**Strona wyboru typu i wersje (2026-10-20, kroki 5 i część 8):** `/swagger-ui/types.html` (adres dodany do ograniczenia
logowania w `web.xml`, po zalogowaniu formularzem wraca na stronę) pobiera `GET /rest/openapi/types.json` (kody, etykiety,
aliasy) i na żądanie `GET /rest/openapi/types/{kod}/versions.json` (`typeId`, `version` w postaci `3.1`, `latest`,
`active`). Kliknięcie kodu otwiera `index.html?spec=../rest/openapi/types/{kod}.json`, wersji
`…{kod}.json?typeId=…`. Spec wskazanej wersji: `?typeId=` (ma pierwszeństwo) albo `?v=3.1` (samo `3` to `3.0`); nieznana wersja
albo `typeId` innego kodu daje 404 (`CaseTypeOpenApiService.select`). `swagger-initializer.js` przyjmuje `spec` tylko w postaci
`../rest/openapi/types/{kod}.json[?v=|typeId=]`. Sprawdzone na serwerze przez `curl` z sesją: przekierowanie na logowanie i
powrót na stronę, lista 11 typów, wersje, spec bez parametrów, z `typeId`, `v=1.0`, `v=1`, 404 dla `v=2.0`, `typeId=1` i `typeId`
innego typu. Nie sprawdzone w prawdziwej przeglądarce (działanie JavaScriptu strony i Swagger UI). „Try it out” dla `POST
/rest/service/...` wymaga tokenu (przycisk Authorize, przepływ `password`). Zostaje: lokalizacja (krok 6), cache i `ETag` (krok 7),
automatyczny token dla sesji.

**Uwagi z testów w UI (2026-10-20):** (1) stara kopia `swagger-initializer.js` w przeglądarce ignorowała `?spec=` (pomógł
Ctrl+F5), więc `swagger-initializer.js` i `types.html` mają `Cache-Control: no-store`; mapowania `mvc:resources` z
`cache-period="0"` muszą stać przed `/swagger-ui/**` (wygrywa wcześniejsze) i mieć wzorce `swagger-initializer.j?` oraz
`types.htm?`, bo przy dokładnej ścieżce część ścieżki po wzorcu jest pusta i zasób daje 404 (sprawdzone na serwerze). (2)
`findFirst` w usłudze ogólnej zwracał pierwszą sprawę z bazy (np. `POLISA2`), więc `/types/{kod}/findFirst` kończył się błędem
niezgodnego typu. `CaseBusiness.findFirst` z `requestContext.caseAsType` zwraca teraz pierwszą sprawę tego typu (zapytanie
po `mrc_typeCodeValue`, jedna sprawa), a bez parametru działa jak dotąd. (3) Przykład kontekstu w specyfikacji typu ma
`requestProperties` z `"requestContext.caseAsType": "<kod>"` (`CaseTypeOperations.presetCaseAsType`). Javadoc `CASE_AS_TYPE`
w `mercury-lib` nie wspomina o `findFirst`, do uzupełnienia przy następnym wydaniu biblioteki.

**Wyszukiwanie na polach z indeksu (2026-10-20):** nazwy pól do zapytań pochodzą z `CaseIndexerFieldsManagerRest`
(`getFieldsByTypeCodes`, `getCategories`, `getSearchTypes`; dokument `003_Architecture/003_Index_Lucene`, model 3.0: pola
stałe z prefiksem `mrc_`, np. `mrc_status`, `mrc_typeCodeValue`, `mrc_rootVersionId`, pola typu pod własną nazwą, np. `nazwa`,
`kod`). Sprawdzone zapytania `searchByQuery`/`searchByParams` przez `/types/{kod}/…` i usługę ogólną: `nazwa:Adam2` daje 1
sprawę w `TstMigB` i 0 w `TstMigA`; `kod:K10` daje 1 w `TstMigB`, a usługa ogólna 2 (stara wersja w `A` i nowa w `B`);
`mrc_rootVersionId:"TstMigA.2008704"` daje 2 wersje przez usługę ogólną i po 1 przez ścieżkę typu; `mrc_status:A AND kod:K10`,
`mrc_luceneDocumentMemo:Adam2` i `searchByParams` z kluczem `nazwa`/`kod` zwracają wyniki ograniczone do typu. `*:*` nie jest
akceptowane (obserwacja 48). Pomysł na później: opisać w specyfikacji typu nazwy pól indeksu (`x-luceneField`, typ wyszukiwania)
na podstawie tego samego źródła, żeby zapytania dało się budować ze specyfikacji.

**Dostęp z przeglądarki (2026-10-20):** endpoint specyfikacji typu przyjmuje token OAuth, a gdy go nie ma, sesję użytkownika
zalogowanego formularzem Tomcata (`RestServicesHelper.createContextBasedOnSession`: nazwa i role z `Principal`). Logowanie:
`/mercury-ws-app/login/` (przekierowanie na formularz `j_security_check`), potem
`/mercury-ws-app/rest/openapi/types/{kod}.json` w tej samej przeglądarce. Sprawdzone na serwerze: bez sesji 401, z sesją 200,
z fałszywym `JSESSIONID` 401. Usługi `POST /rest/service/...` nadal wymagają tokenu (dotyczy kroku 8). Powód wyboru: ciasteczko
`OIDSESSIONTOKEN` czyta `OAuthFactory`, ale nic go nie ustawia, a `TomcatLdapRealm` bez atrybutów `oauth*` (tak jest w
`server.xml` testowego serwera) nie wystawia tokenu w principalu.

**Stan implementacji (2026-10-20, zbudowane z `mercury-lib` 3.0.4.7, 60 testów jednostkowych przechodzi, zmiany z testu na serwerze (4 pliki w `mercury`) niezatwierdzone):** w `mercury-srv` metoda `CaseBusinessSupport.step2IdentifyTargetType`
(ostatnia wersja typu ze wskazanego kodu, `className` nadpisane nazwą typu, brak typu to błąd), jej użycie w
`CaseBusiness.transform2CasesInSameThread` tylko dla pierwszej iteracji (sprawa główna) oraz pominięcie przywracania starego
typu w `CaseLogicHelperService.updateCaseWithHistory`, gdy nowy typ ma kod z parametru. W `mercury-ws-app`
`CaseTypeServicesController` (`/rest/service/types/{typeCode}/{operation}`: `save`, `initModel`, `find`, `findFirst`,
`loadSampleByTypeCode`, `searchByParams`, `searchByQuery`) i ścieżki w `CaseTypeOperations`. Kod wymaga `mercury-lib` 3.0.4.7
(`RequestContextes`). Scenariusz testu na serwerze: (1) zapis sprawy typu `A` przez `/rest/service/types/A/save`, (2) zapis
tej samej sprawy (z `caseId`) przez `/rest/service/types/B/save` (migracja do istniejącego typu `B`; oczekiwane: nowy `caseId`,
`previousVersionId` = stary, stara sprawa `Z`, `rootVersionId` bez zmian), (3) to samo dla `B` o podzbiorze pól `A`
(sprawdza pominięcie przywracania starego typu), (4) `find` sprawy typu `B` przez `/types/A/find` (oczekiwany błąd), (5)
`searchByQuery` i `searchByParams` przez ścieżkę typu, (6) typ z kropką w kodzie. Do sprawdzenia na serwerze: ograniczenie `searchByParams` kluczem `LUCENE_TYPE_CODE_VALUE` w `paramsMap` i zapytania `searchByQuery` z
klauzulą po tym polu (nie zweryfikowane, że pole przyjmuje taki zapis), migracja sprawy między typami z różnym zestawem pól.

**Skutek dla planu:** nowy krok między krokami 4 i 5 „usługi per typ”: odczyt parametru w `step1`/`step2` (tylko sprawa główna),
pominięcie przywracania starego typu, kontroler `/rest/service/types/{typeCode}/{operation}`, zmiana ścieżek w
`CaseTypeOperations` i opis migracji w operacji `save`. Zmiana dotyka `mercury-lib` (nazwa enuma, wydanie biblioteki) i
`mercury-srv`.

### Generator klas `org.mercury.data.javax` – wnioski

Pakiet `mercury-srv/src/main/java/org/mercury/data/javax` to próba generowania klas Javy z typu sprawy:

- `TypeCaseSourceGenerator` (1160 linii) tworzy źródło klasy `extends MercuryObject` z polami,
  adnotacjami `@MrcTypeParam` (nazwa, wersja, typ, etykieta, pozycja, `isRequired`, `updatable`,
  LOB, `defaultValue`, `htmlControl`) i JAXB `@XmlElement`/`@XmlElementWrapper`.
  Zależności (sprawy zależne) generuje rekurencyjnie.
- `TypeCaseClassGenerator` kompiluje je w runtime przez `com.sun.tools.javac.Main` z `-source/-target 1.7`.
  `TypeCaseClassLoader` ładuje klasy z katalogu `mercury.clazz.destionation`.
- Wejście: `TypCaseBusiness.loadClassByType*` (`mercury-srv/.../business/attr/TypCaseBusiness.java`).
  Używa go tylko test `MrcTypeGeneratorScenario`. W produkcji nie jest używany.

Teoretycznie można by schemat budować tak: klasa dynamiczna → `ModelConverters` swagger-core.
**Rekomendacja: nie iść tą drogą.**

- Klasy odwzorowują model JAXB/XML, a nie logiczny JSON (inne nazwy pól, `@XmlElementWrapper`).
- Kompilacja w runtime wymaga pełnego JDK, zapisu na dysk i własnego classloadera. Klasy starych
  wersji typu nie znikają z pamięci.
- Kod używa `sun.tools.java.CompilerError` (usunięte w JDK 9+) i `-source 1.7` (bloker migracji na Javę 17, zadanie [191](../191-Rewizja-wersji-migracja-Java17/etap-2-migracja-serwera-java17.md)).

Zamiast tego **schemat buduje się bezpośrednio z `TypeParam`** (model `io.swagger.v3.oas.models`).
Z `TypeCaseSourceGenerator` warto przejąć logikę:

- wybór typu Javy z `AttributeType.getJavaType()` i podtypu (`AttributeType.subTypeValueOf`, linie 448-470);
- obsługa `hasMultiValues` i kolekcji SELECT;
- kolejność wyboru etykiety: `SubType.label` → `TypeParam.label` → `recomendedLabel` (linie 902-908);
- rekurencja po sprawach zależnych z rejestrem zależności (ochrona przed cyklami).

Wspólną część (mapowanie `TypeParam` → opis pola) można wydzielić tak, żeby korzystały z niej
oba generatory.

### Mapowanie `TypeParam` → OpenAPI

Źródła: opis encji w `docusaurus-hgdb/docs/003_Architecture/001_Cases_MetaData/index.mdx`
oraz kod, który czyta pola `TypeParam`. **Kod ma wyższy priorytet niż dokumentacja.** Rozbieżności
(`docs/obserwacje.md`, pozycje 23–24) poprawia osobne zadanie
[190 – Dokumentacja metadanych typów](../190-Dokumentacja-metadane-typow/TASK.md).

#### Zasada: pola `arg1..arg5` to argumenty kontrolek GUI

Pola `arg*` nie mają stałego znaczenia. Ich sens zależy od `AttributeType` i `htmlControlName`.
Ustawia je `HtmlArguments.setArgumnets` (`mercury-core/.../attrs/html/HtmlArguments.java:26-125`)
przy automatycznym tworzeniu parametru (`CaseBusinessSupport.java:1896-1904`), a czyta głównie
generator formularzy (`mercury-ws-app/.../html/HtmlControlUtils.java:138-232`).
**Do schematu OpenAPI nie wolno brać `arg*` jako ogólnych ograniczeń** (`maxLength`, format daty,
format liczby). Wyjątki to tylko dwa przypadki, w których `arg*` zmienia **wartość** przesyłaną
przez API:

| Przypadek | Pole | Znaczenie (kod) | Wpływ na schemat |
|---|---|---|---|
| SELECT / MULTI | `arg1` | `true` = z opcji brana jest wartość (`value`), `false` = nazwa (domyślnie `true`, `HtmlArguments.java:30-36`) | Postać elementów `enum` |
| SELECT / MULTI | `arg3` | `true` = zapisywana jest para `value{separator}name`, separator domyślnie `\|` (domyślnie `false`). Czytają to parser wartości (`AttributeParser.java:565-650`), indeks Lucene (`CaseMapper.java:918,930`) i eksport POI (`MPoiServerSupport.java:115`) | Postać elementów `enum` / `pattern` |
| LOB | `arg4`, `arg5` | Nadpisują `ParamDefinition.knownLobMetadata` i `mimeType` przy odczycie sprawy (`CaseBusiness.java:1188-1195`) | `contentMediaType`, rozróżnienie LOB JSON / inne |

Pozostałe znaczenia `arg*` są wyłącznie prezentacyjne: kolumny i wiersze TEXTAREA, rozmiar pola,
typ inputu, format JavaScript daty, położenie ikony kalendarza, format liczby, typ pliku.
Można je przekazać w jednym rozszerzeniu `x-gui` (np. `x-gui: {arg1: ..., arg2: ...}`), bez
interpretacji. W szczególności:

- **format daty w API nie pochodzi z `arg1`.** `arg1` to format JavaScript kontrolki. Przy tworzeniu
  parametru kopiuje się do niego bieżący format z kontekstu. W API obowiązuje format z
  `Context.formats` żądania albo `MercuryConfig` (`CaseDateUtils.getShortDateFormatPattern` /
  `getLongDateFormatPattern`) albo liczba ms, zależnie od `decodeRequest`/`decodeResult`;
- **`maxLength` dla STRING nie pochodzi z `arg3`.** `arg3` to `maxlength` kontrolki (domyślnie
  wartość limitu systemowego). Limit API wynika z `XMLReaderHelper.MAX_PARAM_STRING_VALUE_LENGTH = 256`:
  dłuższy napis nie jest już rozpoznawany jako STRING (patrz „Uwagi” – zmiana typu).

#### Mapowanie pól

| OpenAPI | Źródło | Uwagi |
|---|---|---|
| nazwa property | `paramDefinition.id.definitionName` | |
| `title` | `SubType.label` → `TypeParam.label` → `ParamDefinition.recomendedLabel` | Kolejność jak w `TypeCaseSourceGenerator.java:902-908`. Przy automatycznym tworzeniu `label` = nazwa pola |
| `description` | `ParamDefinition.description`, uzupełnione o `TypeParam.tooltip` | Pominąć domyślny tooltip `"Proszę uzupełnić pole"` (`CaseBusinessSupport.DEFAULT_PARAM_TOOLTIP`) |
| `required[]` | `isRequired = true` | Dokumentacja opisuje to jako pole sterujące formularzem. Do sprawdzenia: czy serwer odrzuca sprawę bez wymaganego pola i czy brak pola zmienia sumę kontrolną typu (`sumControl` liczona z nazw pól) |
| `type: array` | `hasMultiValues = true` (dowolny typ, także prosty), `SubType.isList`, `AttributeType.SELECT` (kolekcja) | `htmlControlName` SELECT/LOVSELECT itp. oznacza jeden wybór, MULTI/…MULTI wiele |
| `readOnly` | – | **Nie mapować.** `updateable` to enum `Updatable`: `READWRITE`, `READONLY`, `ONCREATE`, `ONCREATEVISIBLE`, `OTHER` (`mercury-core/.../entities/beans/Updatable.java`), a nie wartość logiczna. Steruje formularzem. `readOnly` w OpenAPI oznacza pole pomijane w żądaniu, a API je przyjmuje. Przekazać jako `x-updatable` |
| `enum` | `valueDefinition`, gdy `sourceType = JSON` | Postać elementów według `arg1`/`arg3` (tabela wyżej). Inne źródła (`WS`, `HTTP`, `WEB`, `FILE`, `JNDI_RESOURCE`, `SAVEDVALS`, `LOCALDAO`, `QUERY`) są dynamiczne: pominąć `enum` i dodać `x-source` (`sourceType`, `source`). Ewentualnie rozwinąć przez `IParamDefinitionAction.getValuesLastVersion` (koszt, dane mogą być poufne) |
| `default` | `ParamDefinition.defaultValue` | Wartość w formacie bazy (String). Przekształcić według typu |
| `contentMediaType` | LOB: `arg5` → `ParamDefinition.mimeType` → domyślny dla `knownLobMetadata` | |
| `format: uri` + `x-presentationUrlPrefix` | `ParamDefinition.presentationUrlPrefix` | Prefiks URL doklejany przy prezentacji wartości |
| `x-position` | `TypeParam.id.position` (1..128) | |
| `x-xmlId` | `TypeParam.xmlId` | Rozróżnia pola o tej samej nazwie i różnych etykietach |
| `x-htmlControl` | `ParamDefinition.htmlControlName` (`HtmlSupportedControl`) | |
| `x-paramVersion` | `ParamDefinition.id.version` | |
| `x-searchable`, `x-indexable` | `TypeParam.isSearchData`, `ParamDefinition.isIndexable` | Informacja dla wyszukiwania (`searchByParams`, Lucene) |
| `x-alternateName` | `ParamDefinition.alternateName` | |
| `x-updatable` | `TypeParam.updateable` | Wartości `Updatable` |
| `x-gui` | `arg1..arg5`, `withEmptyOption`, `actions` (opcjonalnie) | Bez interpretacji, tylko dla generatorów formularzy |
| `mrcCaseHeader` | Wspólny schemat `MrcCaseHeader` (pola z `MrcCaseHeaderField`) | `typeCode` jako `const`. Kod typu: `TypeCode.label`/`alias` w opisie schematu |

#### Lokalizacja etykiet (klucze `${…}`)

Etykiety nie są jednojęzyczne. Tekst w postaci `${klucz}` jest kluczem zasobu tłumaczonym
według języka z kontekstu:

- `AttributeTypeParameter.prepareLocalizedMessage(context, resourceLoader, name)`
  (`mercury-core-server/.../attrs/AttributeTypeParameter.java:1249-1260`) zamienia `${klucz}` na
  komunikat. Gdy go nie znajdzie, zwraca tekst bez zmian, czyli razem z `${…}`.
- `ResourceDAO.getMessage` (`mercury-dao/.../dao/data/ResourceDAO.java:23-35`) szuka encji `Resource`
  po kluczu i języku. Język to pierwsza część `context.locale` (np. `pl` z `pl_PL`), a domyślnie
  `MercuryConfig.getSystemLang()`.
- Zasoby predefiniowane: `mercury-entities-ids/src/main/resources/org/mercury/predefined/data/resources_{de,en,es,fr,ko,pl}.properties`
  (około 150 kluczy na język).

Gdzie klucze występują w danych predefiniowanych (`mercury-entities-ids/.../predefined/attr/*.csv`):

| Pole | Plik | Przykład |
|---|---|---|
| `TypeParam.label`, `TypeParam.tooltip` | `TypeParam.csv` (45 wystąpień) | `${calendar.calendarUserEvent.subject.label}` |
| `TypeCase.description` | `TypeCase.csv` (4) | `${calendar.calendarUserEvent.typeCase.description}` |
| nazwy opcji w `ParamDefinition.valueDefinition` (`sourceType = JSON`) | `ParamDefinition.csv` | `[{"value":"1","name":"${calendar.event.type.1}"}, …]` |
| `ParamDefinition.recomendedLabel` | `ParamDefinition.csv` | **Bez kluczy.** Tekst po polsku (np. „Kalendarz: Temat zdarzenia”) albo `null` (42 ze 109 wierszy) |

Gdzie serwer tłumaczy (z kodu):

- **Tłumaczy nazwy opcji słownikowych:** `AttributeTypeParameter` (źródła JSON, DEFAULT/SAVEDVALS, LOCALDAO:
  linie 1055, 1110, 1136, 1433), `CaseBusinessHelper` (linie 678, 710, 1196, gdy flaga
  `prepareLocalizedMessage = true`) i lista wartości słownika `AttributeTypeActionSupport.loadData:196` (`mercury-ws-app`).
  W `CaseBusiness.transform2MrcObject` flaga jest ustawiona na stałe na `false` (`CaseBusiness.java:966`,
  z `TODO`), więc odczyt sprawy nie tłumaczy nazw.
- **Nie znalazłem tłumaczenia `TypeParam.label`, `tooltip` ani `TypeCase.description` po stronie serwera.**
  Jedynym wywołaniem `getMessage` jest `prepareLocalizedMessage`. Przypuszczenie: tłumaczy je GUI
  albo nie tłumaczy ich nikt. Do sprawdzenia w GUI (`mercury-gui-registry`).

Wymagania dla generatora schematu:

1. `title`, `description` i nazwy opcji (`x-enumNames` / opis `enum`) przepuścić przez
   `prepareLocalizedMessage` z `IResourceLogic`.
2. Język: parametr `?lang=` lub nagłówek `Accept-Language`, przekazany w `Context.locale`.
   Domyślnie język systemowy.
3. Klucz cache: `(typeCode, TypeCase.id, lang)`. Zmiana zasobów (`Resource.publishVersion`) też
   powinna unieważniać cache. Do sprawdzenia, czy zmiany zasobów są rozsyłane w klastrze.
4. Gdy klucza nie ma w danym języku (wynik nadal `${…}`), użyć kolejno: `recomendedLabel`, a potem `definitionName`.
5. W `enum` zostają **wartości** (`value`, ewentualnie `value|name` według `arg3`), a nie nazwy.
   Jeśli `arg3 = true`, część `name` w zapisywanej wartości to nazwa z `valueDefinition`.
   Do sprawdzenia: czy jest to nazwa przetłumaczona czy klucz.

Nie mapować: `TypeParam.withEmptyOption` i `actions` (JavaScript formularza),
`ParamDefinition.sourceJndiName`/`sourceJ2CName` (konfiguracja serwera, potencjalnie wrażliwa),
`timeToLiveSeconds`, `isEditable`, `fromDate`/`toDate`, `sourceOfObject`.

### Mapowanie `AttributeType` → OpenAPI (dla logicznego JSON-a)

Typ Javy według dokumentacji (`AttributeType`) w nawiasie.

| AttributeType | OpenAPI |
|---|---|
| STRING (`String`) | `string`, `maxLength: 256` (limit rozpoznania typu, nie `arg3`) |
| TEXT (`String`) | `string` |
| PASSWORD (`String`) | `string`, `format: password` |
| URL (`URLValue`) | do ustalenia: `RestReaderHelper.identifyUrl` rozpoznaje URL jako obiekt, nie napis |
| BOOLEAN (`Boolean`) | `boolean` |
| BOOLEAN_INTEGER (`Integer`) | `integer`, `enum: [0, 1]` |
| INTEGER (`Long`) | `integer`, `format: int64` |
| NUMBER, DECIMAL, DOUBLE (`Double`) | `number`, `format: double` |
| FLOAT (`Float`) | `number`, `format: float` |
| CURRENCY (`CurrencyValue`) | do ustalenia na podstawie `RestReaderHelper` / `RestVariableBuilder` (kwota z kodem waluty) |
| DATE (`DateInString`) | `string` z wzorcem krótkiej daty (domyślnie `DD-MM-YYYY`, nadpisywany przez `Context.formats`) albo `integer` (ms), zależnie od `decodeRequest`/`decodeResult` |
| DATE_LONG, TIME (`DateInString`) | jak DATE, wzorzec długiej daty (domyślnie `DD-MM-YYYY HH24:MI:SS`) |
| LOB z metadanymi `JSON` | dowolny obiekt/tablica JSON |
| LOB inne (`XML`, `HTML`, `TEXT`, `FILE`, `ANY`) | `string`, `contentMediaType` jak w tabeli pól |
| SELECT (`Collection`) | `array` (lub pojedyncza wartość dla kontrolek jednokrotnego wyboru – do weryfikacji testem) z `enum` |
| NVP (podtyp) | `{ name, value }` |
| ENTRY (podtyp) | `{ key, value }` |
| MAP (podtyp) | `array` obiektów `{ key, value }` |
| JSON_NVP (podtyp, przestarzały) | jak NVP |
| SUBCASE (`Object`) | `$ref` do schematu typu `SubType.code` (`array`, gdy `isList`; kontrolka `SUBTABLE`) |
| ANY (podtyp), COMPLEX (`Object`) | `object` bez ograniczeń. COMPLEX jest przestarzały (komentarz w `CaseMapper.java:908-913`) |

Mapowanie trzeba zweryfikować testem w obie strony: `loadSampleByTypeCode` → JSON → walidacja
schematem → `save` bez zmiany wersji typu.

### Cache i odświeżanie

- Cache wygenerowanych dokumentów z kluczem `typeCode → TypeCase.id` (nowe id = nowa wersja).
- Unieważnianie w `TypeCaseRegistryChangesReceiver` (JMS, kolejka per węzeł), razem z istniejącym
  czyszczeniem `caseMetadataCache`.
- Nagłówek `ETag` z `TypeCode.publishVersion`.

### Uwagi do opisania w dokumentacji

- Wysłanie pola spoza typu albo wartości innego typu tworzy nową wersję typu, chyba że
  `mercury.saveRequestContext.forceChangeType.default=false`.
- Format dat zależy od `context.decodeRequest` / `decodeResult` i od locale.
- Etykiety i nazwy opcji mogą być kluczami `${…}`. Dokumentacja jest generowana w języku żądania.

## Definicja Gotowości (DoD)

- Endpoint zwraca poprawną specyfikację OpenAPI 3 dla istniejącego kodu typu i 404 dla nieznanego.
- Parametr `v` zwraca specyfikację podanej wersji typu, a dla nieistniejącej wersji 404.
- Specyfikacja opisuje logiczny JSON sprawy oraz operacje `CaseBusinessExtRest` (co najmniej
  `find`, `save`, `loadSampleByTypeCode`, `searchByParams`) z `$ref` do schematu typu.
- Obsłużone wszystkie wartości `AttributeType` i sprawy zależne (z ochroną przed cyklami).
- Etykiety, opisy i nazwy opcji z kluczami `${…}` są tłumaczone na język żądania. Test na typach
  predefiniowanych kalendarza (`CalendarUserEvent`) w co najmniej dwóch językach.
- Test: przykład z `loadSampleByTypeCode` przechodzi walidację schematem, a `save` danych zgodnych
  ze schematem nie tworzy nowej wersji typu.
- Zmiana typu (nowa wersja) jest widoczna w dokumentacji bez restartu, także na drugim węźle klastra.
- Swagger UI pozwala wybrać typ sprawy i wyświetlić jego dokumentację.
- Brak zależności od `org.mercury.data.javax` (kompilacji w runtime).
- Opis w `docs/moduly/mercury.md`.

## Kluczowe Pliki w Projekcie

| Plik | Rola |
|---|---|
| `mercury/mercury-ws-app/src/main/java/pro/ibpm/mercury/rest/server/utils/RestVariableReader.java`, `RestReaderHelper.java` | JSON → sprawa, rozpoznawanie typów wartości |
| `mercury/mercury-ws-app/src/main/java/pro/ibpm/mercury/rest/server/utils/RestVariableBuilder.java` | Sprawa → JSON |
| `mercury/mercury-ws-app/src/main/java/pro/ibpm/mercury/rest/server/utils/RestWsStatusUtils.java` | Koperta odpowiedzi |
| `mercury/mercury-ws-app/src/main/java/pro/ibpm/mercury/rest/server/actions/business/data/*ExtRest.java` | Usługi na logicznym JSON-ie |
| `mercury-lib/mercury-srv-api/src/main/java/pro/ibpm/mercury/business/data/utils/XMLReaderHelper.java`, `XMLVariableBuilder.java` | Odpowiednik XML, stałe nazw elementów |
| `mercury-lib/mercury-srv-api/src/main/java/pro/ibpm/mercury/business/data/api/MrcCaseHeaderField.java` | Pola nagłówka |
| `mercury/mercury-srv/src/main/java/org/mercury/data/javax/TypeCaseSourceGenerator.java` | Wzorzec mapowania `TypeParam` → pole |
| `mercury-lib/mercury-core/src/main/java/pro/ibpm/mercury/attrs/html/HtmlArguments.java` | Domyślne wartości `arg1..arg5` według typu |
| `mercury/mercury-ws-app/src/main/java/pro/ibpm/mercury/html/HtmlControlUtils.java` | Odczyt `arg*` przez generator formularzy |
| `mercury-lib/mercury-core/src/main/java/pro/ibpm/mercury/entities/beans/Updatable.java` | Wartości `TypeParam.updateable` |
| `mercury/mercury-core-server/src/main/java/pro/ibpm/mercury/attrs/AttributeTypeParameter.java` | `prepareLocalizedMessage` (:1249) |
| `mercury/mercury-dao/src/main/java/pro/ibpm/mercury/dao/data/ResourceDAO.java`, `mercury/mercury-srv/src/main/java/pro/ibpm/mercury/logic/data/ResourceLogic.java` | Odczyt zasobów według języka |
| `mercury/mercury-entities-ids/src/main/resources/org/mercury/predefined/attr/*.csv` | Predefiniowane typy i pola |
| `mercury/mercury-entities-ids/src/main/resources/org/mercury/predefined/data/resources_*.properties` | Predefiniowane tłumaczenia |
| `mercury-lib/mercury-entities/src/main/java/pro/ibpm/mercury/entities/attr/TypeCase.java`, `TypeParam.java`, `ParamDefinition.java`, `SubType.java`, `TypeCode.java` | Model typu |
| `mercury-lib/mercury-core/src/main/java/pro/ibpm/mercury/attrs/AttributeType.java`, `SourceType.java` | Typy atrybutów, źródła słowników |
| `mercury/mercury-srv/src/main/java/pro/ibpm/mercury/logic/attr/TypeCaseLogic.java` | `findLastVersionByTypeCode` (:534) |
| `mercury/mercury-srv/src/main/java/org/mercury/logic/jms/TypeCaseRegistryChangesReceiver.java` | Odbiór zmian (unieważnianie cache) |
| `scisoftware-webpage/docusaurus-hgdb/docs/003_Architecture/001_Cases_MetaData/index.mdx`, `002_Cases_Versioning/index.mdx` | Opis metadanych i wersjonowania |

## Słownik / Zasady

- Schemat typu: schemat OpenAPI logicznego JSON-a sprawy, zbudowany z `TypeParam` ostatniej wersji typu.
- Implementacja w `mercury` (serwer). Bez zmian w `mercury-lib`.
