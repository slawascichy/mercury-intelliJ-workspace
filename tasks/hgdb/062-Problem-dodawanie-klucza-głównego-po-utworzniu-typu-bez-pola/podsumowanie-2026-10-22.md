# [62] Podsumowanie 2026-10-22: krok 0 (analiza kodu)

Stan: gałąź `hgdb-62` założona w `mercury-lib` (z `2d3457b`) i w `mercury` (z `a50b393d5`, po merge zadania 110).
Nic nie zmieniono w kodzie. Wnioski pochodzą z czytania kodu i nie były odtwarzane testem.

## Gdzie powstają błędy z opisu zadania

Klucz główny typu to pole `TypeCode.uniqueConstraintParamName`. Ustawienie go uruchamia
`TypeCodeLogic.update` (`mercury-srv`), a to `TypeCodeDAO.createUniqueConstraints` (`mercury-dao`):

1. Krok 2 (`createUniqueConstraints`): zapytanie `QL_STRING_CREATE_UQ_2` zwraca tylko wersje typu, które mają pole.
   Gdy ich liczba jest inna niż liczba wszystkich wersji, rzucany jest wyjątek
   „Nie wszystkie z wersji typu '…' zawiera pola '…'”. To **błąd 1** z opisu (pole `id` dodane tylko w nowej wersji).
2. Krok 3 (`createUniqueConstraints`): `INSERT INTO IGO_DA_TYPECODE_UK ... SELECT ... COALESCE(PARAMETER_n, '')`
   (`UniqueConstraintParamDefinition.toSQLParam`). Sprawy, które nie mają wartości w nowym polu, dostają wartość `''`.
   Klucz główny tabeli to `(AE_TYPE_CODE, CASE_TYPE_ID, PARAMETER_DEF_NAME, PROPERTY_VALUE)`, więc dwie sprawy
   z pustą wartością w tej samej wersji typu naruszają klucz. To **błąd 2** z opisu („nieunikalna wartość”).
   Dodatkowo indeks `IGO_DA_TYPECODE_CASE_UK` jest unikalny po `CASE_ID` (zob. obserwacja 60).

Drugą drogą ustawienia klucza jest `save` z `pkPropertyName` (`CaseBusiness`, ok. linii 2010–2055): klucz da się tylko
ustawić z pustego na niepusty, a zmiana albo usunięcie są ignorowane (z notyfikacją). Ustawia to ten sam `TypeCode`,
więc kończy się tym samym wywołaniem `createUniqueConstraints`.

Wniosek: błąd występuje w obecnym kodzie. Opis zadania zgadza się z obydwoma miejscami.

## Propozycja usługi `forceAddPK`

Miejsce: interfejs `ITypeCodeAction` w `mercury-lib/mercury-ws-server-api` (z `@WSDLDocumentation`, żeby generator REST
i dokumentacja OpenAPI ją objęły) oraz implementacja w `mercury` (`TypeCodeLogic` albo osobna klasa biznesowa).

Kroki w jednej transakcji, dla kodu typu i nazwy pola klucza:

1. Walidacja: typ istnieje, ma co najmniej jedną wersję, klucz nie jest jeszcze ustawiony, wskazano typ pola (`String` albo `Number`).
2. Uzupełnienie brakującego pola w każdej wersji typu, która go nie ma (nowy `TypeParam` na ostatniej pozycji,
   `ParamDefinition` istniejąca albo utworzona).
3. Uzupełnienie wartości w sprawach tej wersji, które ich nie mają: `String` to UUID, `Number` to wartości ujemne
   (unikalne, np. malejąco od `-1`).
4. Wywołanie `createUniqueConstraints` (teraz już bez błędów) i ustawienie `uniqueConstraintParamName` w `TypeCode`.
5. Zarejestrowanie spraw do ponownego zaindeksowania w Lucene (mechanizm z `changeModel`: wpisy w `IGO_DA_CASE_MIGRATION`
   i `CaseMigratorSecretaryHelper.wakeupSecretary`).

## Ryzyka i decyzje do podjęcia

- **Suma kontrolna wersji typu.** `TypeCase.sumControl` jest liczona z nazw pól (`MTypeCaseUtils.calculateSumControl`) i służy do
  rozpoznawania wersji (`QgetByCodeAndSumControl`, `QfindAllBySumControl`). Dodanie pola do starej wersji zmienia
  zestaw pól, więc trzeba przeliczyć `sumControl` i sprawdzić, czy nie zrówna się z inną wersją. To największe ryzyko
  projektu (przypuszczenie, nie sprawdzano na danych).
- **Zakres spraw.** Czy uzupełniać wartości tylko w sprawach aktywnych (`CASE_ACTIVE_STATUSES`, tak jak `changeModel`), czy
  we wszystkich. `createUniqueConstraints` wstawia wpisy dla spraw ze statusami aktywnymi.
- **Wartości ujemne dla `Number`.** Malejąco od `-1` czy losowe. Trzeba też zdecydować o zakresie, jeśli pole ma zdefiniowaną długość.
- **Historia zmian.** Czy uzupełnienie wartości ma być zapisane w historii sprawy (`CaseHistory`), czy wykonane „po cichu”.
- **Duże typy.** Na INEA są typy z dziesiątkami tysięcy spraw (np. `ZpiAddress`: 30363). Jedno zapytanie `UPDATE` z podzapytaniem
  i licznikiem jest lepsze niż pętla po sprawach. Do ustalenia dla każdego dialektu (UUID i licznik różnią się w SQL).
- **Powiązanie z obserwacją 61.** Sprawy bez wpisu w `IGO_DA_TYPECODE_UK` po `changeModel` to ten sam obszar. `forceAddPK`
  może wstawić brakujące wpisy dla całego typu.

## Plan testów (na profilu `scichy-test`)

Scenariusz w `mercury-srv` (`LogicScenarioSupport`, czyszczenie bazy przed i po scenariuszu):
typ bez klucza z kilkoma sprawami w dwóch wersjach, pole dodane tylko w nowszej, `forceAddPK`, sprawdzenie wpisów
w `IGO_DA_TYPECODE_UK`, unikalności wartości i prezentacji sprawy (`findByPKProperty`). Test najpierw na starym kodzie,
żeby potwierdzić oba błędy.

## Pytania do autora przed implementacją

1. Parametry usługi: nazwa pola, typ (`String`/`Number`), czy tworzyć `ParamDefinition`, gdy jej brak?
2. Zakres spraw (aktywne czy wszystkie) i zapis w historii.
3. Czy usługa ma być także w REST (`CaseBusinessExtRest`-podobnym kontrolerze), czy tylko w SOAP/panelu?
