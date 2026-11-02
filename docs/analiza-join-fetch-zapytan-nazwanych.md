# Analiza: `JOIN FETCH` w zapytaniach nazwanych encji (`mercury-lib/mercury-entities`)

Stan na 2026-11-02, gałąź `hgdb-049`. Analiza statyczna adnotacji encji oraz jeden pomiar na działającym serwerze. Nic nie zmieniono w kodzie encji.

## Wynik w skrócie

- Moduł `mercury-entities` ma 90 encji i **216 zapytań nazwanych (`@NamedQuery`), z czego żadne nie używa `JOIN FETCH`**.
- 168 zapytań zwraca całe encje (`SELECT x FROM Encja x ...`). 94 z nich dotyczy encji, które mają co najmniej jedno powiązanie `@ManyToOne` albo `@OneToOne` ładowane domyślnie w trybie `EAGER` (tabela niżej).
- W zapytaniu JPQL/HQL powiązania `EAGER` nie są dołączane złączeniem. Hibernate ładuje je osobnym zapytaniem na każdy różny identyfikator (wzorzec N+1), dopóki zapytanie nie ma `JOIN FETCH`. Przy wyszukiwaniu po kluczu (`em.find`) Hibernate używa złączenia, więc problem dotyczy tylko zapytań.
- Zmierzony przypadek (zadanie 049, `getChildren` w CMIS): zapytanie `CaseCatalog` o dzieci folderu z 3251 dziećmi wykonywało **3251 pojedynczych odczytów `igo_da_case_roots`** (po jednym na krawędź), podczas gdy samo zapytanie w bazie trwa 42 ms. Odczyty zliczono przez `pg_stat_user_tables` przed i po jednym wywołaniu. Ustawienie `hibernate.default_batch_fetch_size=50` nie pomogło dla tych odczytów (zbiło za to odczyty powiązań `Case` i użytkowników ładowanych leniwie ze 102 do 10 i z 613 do 37): przypuszczenie: partie obejmują powiązania ładowane później (leniwe), a nie `EAGER` rozwiązywane w trakcie ładowania wyniku.

## Jak policzono

1. Z adnotacji `@ManyToOne`, `@OneToOne`, `@OneToMany` i `@ManyToMany` wyznaczono tryb ładowania każdego powiązania (`EAGER` domyślnie dla `@ManyToOne` i `@OneToOne`, `LAZY` dla kolekcji; jawne `fetch = ...` ma pierwszeństwo). Wynik: 138 powiązań.
2. Z adnotacji `@NamedQuery` wyodrębniono 216 zapytań i sklasyfikowano je: zwraca encję (`SELECT alias FROM Encja alias`) albo projekcję/agregat.
3. Dla encji zwracanych zapytaniami zliczono powiązania `EAGER`.

Czego nie sprawdzono: częstości wywołań poszczególnych zapytań w produkcji (priorytet wymaga profilu użycia), zapytań budowanych dynamicznie w DAO (np. `createQuery` z tekstem JPQL w kodzie), konfiguracji pamięci podręcznej drugiego poziomu (`@Cacheable`, regiony zapytań), ani wpływu na kod, który dziś zakłada odłączone węzły (`CaseCatalog.parent/child`).

## Encje z powiązaniami `EAGER`, zwracane zapytaniami nazwanymi

Kolumny: encja, liczba zapytań nazwanych zwracających tę encję, liczba powiązań `EAGER`, cele powiązań.

| Encja | Zapytania | Powiązania `EAGER` | Cele |
|---|---:|---:|---|
| `Case` | 15 | 5 | group:GroupCase, type:TypeCase, store:Store, createdBy:SystemUser, lastModifiedBy:SystemUser |
| `GroupCase` | 2 | 4 | createdBy:SystemUser, lastModifiedBy:SystemUser, ktmNumber:KtmNumber, source:Source |
| `CaseDocument` | 8 | 3 | initStatus:InitStatus, type:TypeCase, source:Source |
| `TypeParamRole` | 5 | 3 | role:Role, createdBy:SystemUser, lastModifiedBy:SystemUser |
| `CaseHistoryTrace` | 2 | 3 | group:GroupCase, type:TypeCase, matter:Case |
| `Store` | 1 | 3 | manager:SystemUser, role:Role, lastModifiedBy:SystemUser |
| `CaseCatalog` | 15 | 2 | parent:CaseRootVersion, child:CaseRootVersion |
| `Type2Type` | 15 | 2 | parent:TypeCode, child:TypeCode |
| `TypeCase` | 13 | 2 | code:TypeCode, kind:TypeKind |
| `CaseHistoryStream` | 5 | 2 | paramDefinition:ParamDefinition, matter:Case |
| `FileIndex` | 3 | 2 | createdBy:SystemUser, lastModifiedBy:SystemUser |
| `FileIndexHistoryStream` | 2 | 2 | paramDefinition:ParamDefinition, matter:FileIndex |
| `GroupCase2Participant` | 2 | 2 | createdBy:SystemUser, lastModifiedBy:SystemUser |
| `SubType` | 1 | 2 | parentType:TypeCase, code:TypeCode |
| `TypeParam` | 3 | 1 | paramDefinition:ParamDefinition |
| `Comment` | 1 | 1 | caseObj:Case |
| `QuickTask` | 1 | 1 | caseObj:Case |

Łańcuchy: powiązania `EAGER` prowadzą dalej. Przykład: `Case` ładuje `group` (`GroupCase`: użytkownicy, `KtmNumber`, `Source`), `type` (`TypeCase`: `TypeCode`, `TypeKind`), `store` (`Store`: menedżer, rola, użytkownik) i dwóch użytkowników. Jedno zapytanie o listę spraw uruchamia więc kaskadę zapytań po wszystkich tych tabelach (zaobserwowane: `igo_da_types`, `igo_da_typecode`, `igo_da_stores`, `igo_da_groupcases`, `igo_da_ktms`, `igo_di_sources`, `igo_adm_roles`, `igo_adm_users`: po ok. 100 odczytów na 100 spraw przed ustawieniem `default_batch_fetch_size`).

## Proponowana kolejność działań

Priorytet wynika z liczby różnych celów powiązań w jednym wyniku (im więcej różnych, tym większy koszt N+1) i z tego, że wynik zapytania jest listą. Wymaga potwierdzenia profilem użycia (dziennik, statystyki Hibernate).

1. **`CaseCatalog` (15 zapytań, `parent` i `child`):** zmierzone N+1 (3251 odczytów na jedno wywołanie). Zapytania o dzieci, rodziców i zależności (`getAllChildrenRelationshipsByNodeId`, `...ParentsRelationshipsByNodeId`, `...DependsRelationshipsByNodes`). Dotyczy też REST katalogu (`Case2CaseRest`) i `Case2CaseBusiness`. Zrobione tymczasowo po stronie CMIS: zapytanie `CaseCatalogDAO.findDirectChildIds` zwraca same identyfikatory dzieci, bez encji krawędzi.
2. **`Case` (15 zapytań, 5 powiązań):** największa kaskada. Do rozważenia `JOIN FETCH` dla `type` (mało różnych typów, ale głęboki łańcuch `TypeCase` → `TypeCode`, `TypeKind`) i `group`; `store` i użytkownicy ładują się z pamięci podręcznej sesji po pierwszym trafieniu.
3. **`CaseHistoryTrace`, `CaseDocument`, `CaseHistoryStream`, `TypeParamRole`:** powiązanie `matter` albo `paramDefinition` o dużej liczbie różnych wartości w wyniku.
4. **`Type2Type` (15 zapytań), `TypeCase` (13), `SubType`:** węzły typów (`TypeCode`); wynikiem są zwykle dziesiątki wierszy, więc zysk mniejszy, ale zapytania są często wywoływane (konfiguracja typów).
5. Pozostałe z tabeli: niska liczba wierszy w wyniku albo rzadkie użycie (do oceny po profilu).

## Zasady bezpiecznego użycia `JOIN FETCH`

- Tylko dla powiązań do jednej encji (`@ManyToOne`, `@OneToOne`). `JOIN FETCH` kolekcji (`@OneToMany`) razem ze stronicowaniem (`setMaxResults`) powoduje stronicowanie w pamięci i duplikaty wierszy.
- Zapytanie musi zwracać alias encji. Dla zapytań z agregatami (`COUNT`, `MAX`) i projekcjami `JOIN FETCH` nie ma zastosowania.
- Węzły dołączone złączeniem zmieniają obraz danych dla kodu, który dziś zakłada leniwe odwołania (np. `CaseCatalog.child` odczytywane poza sesją): zmiana wymaga przeglądu użycia i testów regresji (`SrvTest`, scenariusze katalogu, `testMERC_0168_Scenarios`).
- Zapytania w tym module mają regiony pamięci podręcznej zapytań (`@QueryHint cacheRegion`). Zmiana tekstu zapytania zmienia klucze pamięci podręcznej.
- `ORDER BY` po polu encji z `JOIN FETCH` jest dozwolone. Dla `LEFT JOIN FETCH` (powiązania opcjonalne, `nullable = true`) trzeba użyć `LEFT`, żeby nie gubić wierszy.
- Alternatywa dla powiązań, które nie muszą być `EAGER`: zmiana na `fetch = LAZY` (szeroki wpływ, wymaga przeglądu całego kodu) albo zapytania projekcyjne tylko po identyfikatorach, jak `findDirectChildIds`.

## Proponowany plan wdrożenia (do zatwierdzenia)

1. Zebrać profil użycia: włączyć na dev statystyki Hibernate (`hibernate.generate_statistics`) lub liczniki zapytań i uruchomić typowe scenariusze, żeby wskazać zapytania z największą liczbą zapytań wtórnych.
2. Dla `CaseCatalog`: dodać `JOIN FETCH c2c.parent JOIN FETCH c2c.child` do zapytań o dzieci i rodziców; pomiar (`pg_stat_user_tables` przed i po, czas REST katalogu i CMIS).
3. Dla `Case`: sprawdzić, czy `JOIN FETCH` dla `type` i `group` skraca listy spraw; pomiar.
4. Pozostałe encje według profilu.
5. Każdą zmianę kończyć testami regresji i zapisem pomiarów w zadaniu; zmiany w encjach oznaczają kolejne wydanie `mercury-lib`.

## Wyniki pomiarów (2026-11-02, `JoinFetchStatsTest`, baza testowa, 3255 spraw)

Pomiar: liczba zapytań SQL z `Statistics` Hibernate (`getPrepareStatementCount`), pierwsze i drugie wywołanie tej samej sondy.

| Sonda | Przed | Po |
|---|---|---|
| `CaseCatalog` dzieci folderu głównego (3254 wiersze) | 3258 zapytań, 961 ms | 3 zapytania, 153–197 ms (`JOIN FETCH parent, child`) |
| `CaseCatalog` rodzice | 5 | 3 |
| `caseDAO.findByIdList(100)`, 1. wywołanie | ok. 100 | 7 (`JOIN FETCH group`, `LEFT JOIN FETCH group.ktmNumber`) |
| `caseDAO.findByIdList(100)`, 2. wywołanie | – | 100 zapytań, 179 ms |
| `caseDAO.findByIdList(100)` bez pamięci podręcznej zapytań | – | 7 zapytań, 15 ms |
| `caseDAO.findByIdList(1000)`, 2. wywołanie | – | 1000 zapytań, 656 ms; bez pamięci podręcznej 27 zapytań, 138 ms |

### Odkrycie: pamięć podręczna zapytań + encje `@Cacheable(false)`

`DAOSupport.setHint` ustawia `org.hibernate.cacheable=true` dla każdego `CacheUsage` poza `NONE`. Trafienie w pamięć podręczną zapytań zwraca same identyfikatory. Hibernate ładuje wtedy encje po jednej, jeśli nie ma ich w pamięci podręcznej drugiego poziomu. 21 encji ma `@Cacheable(false)`, 69 nie ma adnotacji, żadna nie ma `@Cache`. `JOIN FETCH` pomaga więc tylko przy pierwszym wywołaniu (chybienie), a każde kolejne trafienie w pamięć zapytań daje N+1.

Wniosek (do decyzji autora, zmiana globalna): nie ustawiać `cacheable` dla zapytań zwracających encje bez pamięci podręcznej drugiego poziomu (`DAOSupport.isQueryCacheEnabled`), albo świadomie włączyć pamięć drugiego poziomu dla wybranych encji. Zrobione lokalnie: `CmisRepositoryBusiness.loadCases` czyta sprawy bez pamięci podręcznej zapytań (`findByIdList(lista, true, paginacja)`).

## Załącznik: zapytania nazwane zwracające encje z powiązaniami `EAGER` (94)

Kolumny: encja, nazwa zapytania, warunek `WHERE` (skrócony).

| Encja | Zapytanie | Warunek |
|---|---|---|
| Case | `Case.QFIND_BY_INVENTORY_CODE` | c.inventoryCode = :inventoryCode |
| Case | `MCase.QfindAllLastVersions` | rootVersionId = :rootVersionId ORDER BY c.id |
| Case | `MCase.QfindByPKPropertName` | 1 = 1 AND pk.id.name = :typeCode AND pk.id.uniqueConstraintParamName = :uniqueConstraintParamNa |
| Case | `MCase.QfindLastUpdatedByRoleName` | c.id = l.id ORDER BY l.lastModifyDate desc |
| Case | `MCase.QfindLastUpdatedByRoleNameAndTypeCodes` | c.id = l.id AND l.typeCode in (:typeCodes) ORDER BY l.lastModifyDate desc |
| Case | `MCase.QfindLastVersion` | c.previousVersionId is null AND rootVersionId = :rootVersionId |
| Case | `MCase.QfindNewestVersion` | c.previousVersionId = :id |
| Case | `MCase.QfindSubCasesByParentCaseIdAndFieldName` | c.packageId = :packageId AND c.fieldName = :fieldName) |
| Case | `MCase.QgetActiveByBpmId` | c.bpmProcessId = :bpmProcessId AND c.status in ('A', 'O') |
| Case | `MCase.QgetByGroupCaseIdsList` | c.group.id in (:groupIds) |
| Case | `MCase.QgetByVerionSeriesAll` | cd.id.versionSeriesId = :versionSeriesId) |
| Case | `MCase.QgetByVerionSeriesLastVersion` | cd.isLatestVersion = true AND cd.id.versionSeriesId = :versionSeriesId) |
| Case | `MCase.QgetByVerionSeriesNotLastVersion` | cd.isLatestVersion = false AND cd.id.versionSeriesId = :versionSeriesId) |
| Case | `MCase.QgetLastByBpmId` | c1.bpmProcessId = :bpmProcessId) |
| Case | `MCase.QgetSubCases` | c2s.packageId = :parentCaseId) |
| CaseCatalog | `MCase2Case.QAllByPathStartsWith` | c2c.path LIKE :preffix AND c2c.depth BETWEEN 2 AND (2 + :maxDepth) AND c2c.mountPoint = :mountP |
| CaseCatalog | `MCase2Case.QAllByPathStartsWithForDefaultMountPoint` | c2c.path LIKE :preffix AND c2c.depth BETWEEN 2 AND (2 + :maxDepth) AND c2c.mountPoint is null O |
| CaseCatalog | `MCase2Case.QBaseRelationship` | c2c.child.id = :nodeId AND c2c.depth = 1 AND c2c.mountPoint = :mountPoint |
| CaseCatalog | `MCase2Case.QBaseRelationships` | c2c.child.id = :nodeId AND c2c.depth = 1 |
| CaseCatalog | `MCase2Case.QDefaultBaseRelationship` | c2c.child.id = :nodeId AND c2c.depth = 1 AND c2c.mountPoint is null |
| CaseCatalog | `MCase2Case.QgetAllChildrenRelationshipsByNodeId` | c2c.parent.id = :nodeId AND c2c.depth BETWEEN 2 AND (2 + :maxDepth) AND c2c.mountPoint = :mount |
| CaseCatalog | `MCase2Case.QgetAllDefaultChildrenRelationshipsByNodeId` | c2c.parent.id = :nodeId AND c2c.depth BETWEEN 2 AND (2 + :maxDepth) AND c2c.mountPoint is null  |
| CaseCatalog | `MCase2Case.QgetAllDefaultDependsRelationshipsByNodesCollection` | (c2c.child.id IN (:nodeList) AND c2c.depth BETWEEN 2 AND (2 + :maxDepth) AND c2c.mountPoint is  |
| CaseCatalog | `MCase2Case.QgetAllDefaultDependsRelationshipsByNodesWithoutMeCollection` | (c2c.child.id IN (:nodeList) AND c2c.depth BETWEEN 2 AND (2 + :maxDepth) AND c2c.mountPoint is  |
| CaseCatalog | `MCase2Case.QgetAllDefaultParentsRelationshipsByNodeId` | c2c.child.id = :nodeId AND c2c.depth BETWEEN 2 AND (2 + :maxDepth) AND c2c.mountPoint is null O |
| CaseCatalog | `MCase2Case.QgetAllDefaultRelationshipsByIdList` | c2c.parent.id = c2c.child.id AND c2c.parent.id IN (:nodeIdList) AND c2c.depth BETWEEN 2 AND (2  |
| CaseCatalog | `MCase2Case.QgetAllDependsRelationshipsByNodesCollection` | (c2c.child.id IN (:nodeList) AND c2c.depth BETWEEN 2 AND (2 + :maxDepth) AND c2c.mountPoint = : |
| CaseCatalog | `MCase2Case.QgetAllDependsRelationshipsByNodesWithoutMeCollection` | (c2c.child.id IN (:nodeList) AND c2c.depth BETWEEN 2 AND (2 + :maxDepth) AND c2c.mountPoint = : |
| CaseCatalog | `MCase2Case.QgetAllParentsRelationshipsByNodeId` | c2c.child.id = :nodeId AND c2c.depth BETWEEN 2 AND (2 + :maxDepth) AND c2c.mountPoint = :mountP |
| CaseCatalog | `MCase2Case.QgetAllRelationshipsByIdList` | c2c.parent.id = c2c.child.id AND c2c.parent.id IN (:nodeIdList) AND c2c.depth BETWEEN 2 AND (2  |
| CaseDocument | `MCaseDocument.QgetByCaseAll` | cd.id.caseObj.id = :caseObj  |
| CaseDocument | `MCaseDocument.QgetByCaseAndVersionSeriesAll` | cd.id.caseObj.id = :caseObj AND cd.id.versionSeriesId = :versionSeriesId |
| CaseDocument | `MCaseDocument.QgetByCaseAndVersionSeriesLastVersion` | cd.id.caseObj.id = :caseObj AND cd.isLatestVersion = true AND cd.id.versionSeriesId = :versionS |
| CaseDocument | `MCaseDocument.QgetByCaseLastVersion` | cd.id.caseObj.id = :caseObj AND cd.isLatestVersion = true |
| CaseDocument | `MCaseDocument.QgetByObjectId` | cd.id.objectId = :objectId |
| CaseDocument | `MCaseDocument.QgetByVersionSeriesAll` | cd.id.versionSeriesId = :versionSeriesId  |
| CaseDocument | `MCaseDocument.QgetByVersionSeriesLastVersion` | cd.isLatestVersion = true AND cd.id.versionSeriesId = :versionSeriesId |
| CaseDocument | `MCaseDocument.QgetByVersionSeriesNotLastVersion` | cd.isLatestVersion = false AND cd.id.versionSeriesId = :versionSeriesId |
| CaseHistoryStream | `MCaseHistoryStream.QgetByCaseId` | h.matter.id = :caseId |
| CaseHistoryStream | `MCaseHistoryStream.QgetByCaseIdAndBetweenModifyDate` | h.matter.id = :caseId AND (h.modifyDate BETWEEN :fromDate AND :toDate) |
| CaseHistoryStream | `MCaseHistoryStream.QgetByCaseIdAndParamDefinitionName` | h.matter.id = :caseId AND h.paramDefinition.id.definitionName = :definitionName |
| CaseHistoryStream | `MCaseHistoryStream.QgetByCaseIdOrderbyModifyDate` | h.matter.id = :caseId order by h.modifyDate asc |
| CaseHistoryStream | `MCaseHistoryStream.QgetBySourceAndSourceId` | h.source = :source AND h.sourceId = :sourceId order by h.modifyDate asc |
| CaseHistoryTrace | `MCaseHistoryTrace.QgetByCaseId` | h.matter.id = :caseId |
| CaseHistoryTrace | `MCaseHistoryTrace.QgetByCaseIdOrderbyModifyDate` | h.matter.id = :caseId order by h.createdBy asc  |
| Comment | `"MComment.getAllByCaseId"` | cd.caseObj.id = :caseId |
| FileIndex | `"MFileIndex.findByControlMD5"` | f.controlMD5 = :controlMD5 |
| FileIndex | `"MFileIndex.findByFileName"` | f.targetDir = :targetDir AND f.fileName = :fileName |
| FileIndex | `"MFileIndex.findByNodeName"` | f.nodeName = :nodeName |
| FileIndexHistoryStream | `"MFileIndexHistoryStream.QgetByFileId"` | h.matter.id = :fileId |
| FileIndexHistoryStream | `"MFileIndexHistoryStream.QgetByFileIdOrderbyModifyDate"` | h.matter.id = :fileId order by h.modifyDate asc  |
| GroupCase | `MGroupCase.QgetGroupCasesByKTMNumberCode` | gc.ktmNumber.ktmCode = :ktmNumberCode  |
| GroupCase | `MGroupCase.QgetGroupCasesByKTMNumberId` | gc.ktmNumber.id = :ktmNumberId  |
| GroupCase2Participant | `MGroupCase2Participant.QgetGroupCase2ParticipantByGroupId` | g2p.id.groupCase.id = :groupId  |
| GroupCase2Participant | `MGroupCase2Participant.QgetGroupCase2ParticipantByParticipantId` | g2p.id.participant.id = :participantId  |
| QuickTask | `"MQuickTask.getAllByCaseId"` | cd.caseObj.id = :caseId |
| Store | `MStore.QgetStoreByNameAndSource` | s.name = :name AND s.sourceOfObject = :sourceOfObject |
| SubType | `MSubType.QfindByTypeAndFieldName` | st.parentType.id = :typeId AND st.fieldName = :fieldName |
| Type2Type | `MType2Type.QAllByPathStartsWith` | t2t.path LIKE :preffix AND t2t.depth BETWEEN 2 AND (2 + :maxDepth) AND t2t.mountPoint = :mountP |
| Type2Type | `MType2Type.QAllByPathStartsWithForDefaultMountPoint` | t2t.path LIKE :preffix AND t2t.depth BETWEEN 2 AND (2 + :maxDepth) AND t2t.mountPoint is null O |
| Type2Type | `MType2Type.QBaseRelationship` | t2t.child.name = :nodeId AND t2t.depth = 1 AND t2t.mountPoint = :mountPoint |
| Type2Type | `MType2Type.QBaseRelationships` | t2t.child.name = :nodeId AND t2t.depth = 1 |
| Type2Type | `MType2Type.QDefaultBaseRelationship` | t2t.child.name = :nodeId AND t2t.depth = 1 AND t2t.mountPoint is null |
| Type2Type | `MType2Type.QgetAllChildrenRelationshipsByNodeId` | t2t.parent.name = :nodeId AND t2t.depth BETWEEN 2 AND (2 + :maxDepth) AND t2t.mountPoint = :mou |
| Type2Type | `MType2Type.QgetAllDefaultChildrenRelationshipsByNodeId` | t2t.parent.name = :nodeId AND t2t.depth BETWEEN 2 AND (2 + :maxDepth) AND t2t.mountPoint is nul |
| Type2Type | `MType2Type.QgetAllDefaultDependsRelationshipsByNodesCollection` | (t2t.child IN (:nodeList) AND t2t.depth BETWEEN 2 AND (2 + :maxDepth) AND t2t.mountPoint is nul |
| Type2Type | `MType2Type.QgetAllDefaultDependsRelationshipsByNodesWithoutMeCollection` | (t2t.child IN (:nodeList) AND t2t.depth BETWEEN 2 AND (2 + :maxDepth) AND t2t.mountPoint is nul |
| Type2Type | `MType2Type.QgetAllDefaultParentsRelationshipsByNodeId` | t2t.child.name = :nodeId AND t2t.depth BETWEEN 2 AND (2 + :maxDepth) AND t2t.mountPoint is null |
| Type2Type | `MType2Type.QgetAllDefaultRelationshipsByIdList` | t2t.parent.name = t2t.child.name AND t2t.parent.name IN (:nodeIdList) AND t2t.depth BETWEEN 2 A |
| Type2Type | `MType2Type.QgetAllDependsRelationshipsByNodesCollection` | (t2t.child IN (:nodeList) AND t2t.depth BETWEEN 2 AND (2 + :maxDepth) AND t2t.mountPoint = :mou |
| Type2Type | `MType2Type.QgetAllDependsRelationshipsByNodesWithoutMeCollection` | (t2t.child IN (:nodeList) AND t2t.depth BETWEEN 2 AND (2 + :maxDepth) AND t2t.mountPoint = :mou |
| Type2Type | `MType2Type.QgetAllParentsRelationshipsByNodeId` | t2t.child.name = :nodeId AND t2t.depth BETWEEN 2 AND (2 + :maxDepth) AND t2t.mountPoint = :moun |
| Type2Type | `MType2Type.QgetAllRelationshipsByIdList` | t2t.parent.name = t2t.child.name AND t2t.parent.name IN (:nodeIdList) AND t2t.depth BETWEEN 2 A |
| TypeCase | `MType.QfindAllBySumControl` | tc.sumControl = :sumControl ORDER BY (tc.version + tc.versionMinor) DESC |
| TypeCase | `MType.QfindLatestVersionBySumControl` | tc.sumControl = :sumControl AND tc.isLatestVersion = true |
| TypeCase | `MType.QgetByCode` | tc.code.name = :typeCode ORDER BY (tc.version + tc.versionMinor) DESC |
| TypeCase | `MType.QgetByCodeAllVersions` | tc.code.name = :typeCode ORDER BY (tc.version + tc.versionMinor) DESC |
| TypeCase | `MType.QgetByCodeAndSumControl` | tc.code.name = :typeCode AND tc.sumControl = :sumControl ORDER BY (tc.version + tc.versionMinor |
| TypeCase | `MType.QgetByCodeLastVersion` | tc.code.name = :typeCode AND tc.isLatestVersion = true |
| TypeCase | `MType.QgetByCodeNotLastVersionButOne` | tcg.code.name = tc.code.name AND tcg.isLatestVersion = false GROUP BY tcg.code.name) |
| TypeCase | `MType.QgetByNameAllVersion` | tc.typeName = :typeName ORDER BY (tc.version + tc.versionMinor) DESC |
| TypeCase | `MType.QgetByNameAndSumControl` | tc.typeName = :typeName AND tc.sumControl = :sumControl ORDER BY (tc.version + tc.versionMinor) |
| TypeCase | `MType.QgetByNameAndVersion` | tc.typeName = :typeName AND tc.version = :version |
| TypeCase | `MType.QgetByNameLastVersion` | tc.typeName = :typeName AND tc.isLatestVersion = true |
| TypeCase | `MType.QgetCaseTypesOnly` | tc.isDocumentType = false AND tc.isLatestVersion = true |
| TypeCase | `MType.QgetDocumentTypesOnly` | tc.isDocumentType = true AND tc.isLatestVersion = true |
| TypeParam | `MTypeParam.QgetByTypeCaseId` | tp.id.type.id = :typeCaseId order by tp.id.position  |
| TypeParam | `MTypeParam.QsearchByParamDefinitionName` | tp.paramDefinition.id.definitionName = :paramDefinitionName AND tp.id.type.isDocumentType = fal |
| TypeParam | `MTypeParam.QsearchByParamDefinitionNameLastVersion` | tp.paramDefinition.id.definitionName IN ( :paramDefinitionName ) AND tp.id.type.isLatestVersion |
| TypeParamRole | `MTypeParamRole.QgetByRoleName` | pd.role.name = :roleName |
| TypeParamRole | `MTypeParamRole.QgetByRoleNames` | pd.role.name IN (:roleNames) |
| TypeParamRole | `MTypeParamRole.QgetByRoleNamesAndTypeCode` | pd.role.name IN (:roleNames) AND (pd.typeCode = :typeCode OR pd.typeCode = '*')  |
| TypeParamRole | `MTypeParamRole.QgetByTypeCode` | pd.typeCode = :typeCode |
| TypeParamRole | `MTypeParamRole.QgetByTypeCodeParamNameAndRoleName` | pd.typeCode = :typeCode AND pd.paramName = :paramName AND pd.role.name = :roleName  |
