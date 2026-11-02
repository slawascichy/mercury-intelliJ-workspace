# Raport: optymalizacja N+1 (`JOIN FETCH`, pamięć zapytań), 2026-11-02

Gałąź `hgdb-049` (`mercury`, `mercury-lib`). Pomiar: `JoinFetchStatsTest` (liczba zapytań SQL z `Statistics` Hibernate) na `mercury-db-test` z 3253 dziećmi folderu głównego ([dane pomiarowe](dane-pomiarowe-cmis.md)) oraz żądania CMIS do Tomcata. Szczegóły zasad i listy zapytań: [analiza `JOIN FETCH`](analiza-join-fetch-zapytan-nazwanych.md).

## Zmiany

| Zmiana | Repozytorium | Cel |
|---|---|---|
| `JOIN FETCH parent, child` w 14 zapytaniach `CaseCatalog` | mercury-lib | koniec 1 odczytu na krawędź katalogu |
| `JOIN FETCH group`, `LEFT JOIN FETCH group.ktmNumber` w 13 zapytaniach `Case`, nowe `Case.findByInventoryCode` | mercury-lib | koniec odczytów grupy i numeru KTM na sprawę |
| `JOIN FETCH code, kind` w `QgetCaseTypesOnly`, `QgetDocumentTypesOnly` (`TypeCase`) | mercury-lib | ładowanie typów przez sekretarzy |
| `JOIN FETCH paramDefinition` w 3 zapytaniach `TypeParam` | mercury-lib | koniec odczytu definicji na parametr |
| `getIdListFetchJoins()` (`MDataDAOSupport`, `CaseDAO`) | mercury | `findByIdList` ze złączeniami |
| `hibernate.default_batch_fetch_size=50` (`dao-context.xml`) | mercury | partie dla powiązań leniwych |
| Pamięć zapytań wyłączona dla wyników z encjami bez pamięci 2. poziomu (`DAOSupport.returnsUncachedEntity`) | mercury | koniec N+1 przy trafieniu w pamięć zapytań |
| `findDirectChildIds`, `getChildren` stronicowane, `childrenNamed` (CMIS) | mercury | bez ładowania całego folderu |
| Flaga odświeżenia list typów po zatwierdzeniu transakcji (`TypeCaseRegistryChanges`) | mercury | usunięcie wyścigu w `testMERC_0168_Scenarios` (obserwacja 141) |

## Wyniki: liczba zapytań SQL

| Sonda | Przed | Po |
|---|---:|---:|
| `CaseCatalog`, dzieci folderu głównego (3253 wiersze) | 3258 | **3** |
| `CaseCatalog`, rodzice | 5 | 3 |
| `caseDAO.findByIdList(100)`, 1. wywołanie | ok. 100 | **5** |
| `caseDAO.findByIdList(100)`, 2. wywołanie (pamięć zapytań) | 100 | **5** |
| `caseDAO.findByIdList(1000)`, 2. wywołanie | 1000 | **25** |
| `QgetCaseTypesOnly` (14 typów) | 13 przy 8 typach | **1** |
| `TypeParam.QgetByTypeCaseId` (33 parametry) | N+1 (sonda zwykłego JPQL: 91 na 94 wiersze) | **1** |

Czasy (`getChildren` itd.) w tabeli niżej.

## Wyniki: CMIS na Tomcacie (3250 dzieci)

| Operacja | Przed | Po |
|---|---:|---:|
| `getChildren`, maxItems=100, skip 0 | 2,07 s | 0,08–0,10 s |
| `getChildren`, skip 1500 | 0,89 s (po `findDirectChildIds`) | 0,23 s |
| `getChildren`, skip 3100 | 1,86 s | 0,35 s |
| `getChildren`, wszystkie | 2,28 s | 0,42 s |
| `createFolder` | 3,7 s | 0,10–0,12 s |
| `getObjectByPath` | 2,8 s | 0,03–0,07 s |

## Pozostałe sondy (zwykłe JPQL, limit 200 wierszy, baza testowa)

Kolejność: encja, wiersze → zapytania SQL, osobne ładowania.

| Encja | Wiersze → zapytania | Osobne ładowania | Ocena |
|---|---|---|---|
| `TypeParam` (zwykłe JPQL, bez złączenia) | 108 → 101 | `ParamDefinition`=93 | naprawione w zapytaniach nazwanych |
| `CaseDocument` | 8 → 12 | `Case`=5, `InitStatus`=3, `Source`=2 | mały zysk, wymaga większych danych |
| `Type2Type` | 9 → 10 | `TypeCode`=9 | mały zysk (typy w pamięci podręcznej) |
| `CaseHistoryStream`, `CaseHistoryTrace`, `Comment`, `TypeParamRole`, `SubType`, `GroupCase`, `Store`, `QuickTask`, `FileIndex` | 0–200 → 1–5 | pojedyncze | brak wzorca N+1 w danych testowych |

## Testy regresji

- `CmisRepositoryBusinessTest`: 36 z 36.
- `WsServerTest.testMERC_0168_Scenarios` (krytyczny): przechodzi 3 razy z rzędu po poprawce wyścigu w `TypeCaseRegistryChanges`. Wcześniejsza porażka nie wynikała z optymalizacji (baseline z kodu sprzed prac też padał); przyczyną był wyścig z komunikatem JMS.
- Pełny `SrvTest` nie był uruchamiany po zmianach (czyści bazę; `mercury-db-test` służy do pomiarów).

## Co dalej

1. `Type2Type`, `CaseDocument`: ocena na bazie z większą liczbą wierszy (`datasetScenario` z `SrvTest`).
2. Zmierzyć REST katalogu (`Case2CaseRest.getAllChildrenRelationshipsByNodeId`) na Tomcacie.
3. Pełny `SrvTest` w profilu `scichy` po zatwierdzeniu zmian.
