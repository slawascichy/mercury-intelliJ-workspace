# [56] Problem z aktualizacją typu podczas zmniejszenia liczby parametrów

## Opis problemu

@kasprzyk zauważył, że gdy zmieniamy liczbę parametrów w obiekcie np. z 34 do 22, to pierwsze 22 ją zapisane prawidłowo, lecz reszta jest bezmyślnie doklejana. Jest to błąd bo pojawiają się duplikaty pól.

Obiekt obecnie (na poziomie klienta):
![53941993-ea90db00-40b9-11e9-923f-d56b484e1272](53941993-ea90db00-40b9-11e9-923f-d56b484e1272.png)

Lista parametrów po stronie Mercury:
![53942021-0300f580-40ba-11e9-9353-a4478d203818](53942021-0300f580-40ba-11e9-9353-a4478d203818.png)

### Komentarz @scichy

Nie udaje mi się zreprodukować problemu w Mercury 3.0. Za to zaobserwowałem ciekawy case:
![54380078-f288e600-468a-11e9-82d5-d671b19c86f4](54380078-f288e600-468a-11e9-82d5-d671b19c86f4.png)

Zadziałał mechanizm:
![54380272-54495000-468b-11e9-8183-a2c2ccc8b3a9](54380272-54495000-468b-11e9-8183-a2c2ccc8b3a9.png)


Tylko nie spodziewałem się w danym momencie takiego efektu - raczej może powinny być pozostałe wartości pól (street oraz checkParameter) ustawione na null

@lcichorek co o tym myślisz?

### Komentarz @lcichorek

Mam jeden pomysł. Można by w kontekście ustawić flagę np. `setNullIfNotExists` (albo jakoś inaczej, ładniej), która by oznaczała, że jeżeli nie uzupełniłem pól, to należy je ustawić na null.

### Komentarz 2 @scichy

Przydałoby się też opisać w artykule dokumentacji opisującym kontekst (obiekt Context) wszystkie dodatkowe 
fali/parametry które są w nim używane. Wtedy będzie wiadomo, że np. `setNullIfNotExists` jest dostępne i można z niego korzystać.
Parametr `setNullIfNotExists` powinien być ustawiany jako parametr w kategorii `ContextRequestProperties.
SaveRequestContext`.


## Rozpoznanie (2026-11-17)

**Flaga z komentarzy już istnieje, ale serwer jej nie czyta.**

- `ContextRequestProperties.SaveRequestContext.VALUE_IS_NULL_IF_FIELD_NOT_EXISTS_IN_REQUEST` (`mercury-lib/mercury-core`, klucz `saveRequestContext.valueIsNullIfFieldNotExisisInRequest`, wartość domyślna z `mercury.properties`: `mercury.saveRequestContext.valueIsNullIfFieldNotExisisInRequest.default`, w obrazach i przykładach `false`; literówka `Exisis` w nazwie jest historyczna).
- Pole `valueIsNullIfFieldNotExisisInRequest` jest w DTO `ContextSaveRequest` (`ccrto-openapi`) i w przykładach `context_sample.v1.{xml,json}`.
- Jest opisane w artykule dokumentacji o `Context` (docusaurus, `004_API/001_Context/index.mdx`, EN i PL).
- **W repozytorium `mercury` nie ma żadnego użycia** ani enumu, ani klucza (przeszukane `*.java` w `mercury`, `mercury-lib`, `hgdb-client-open`, `mercury-cmd`). Flaga jest więc zadeklarowana i udokumentowana, lecz nie działa.

**Gdzie to zadziała:** `CaseLogicHelperService` (`mercury-srv/.../org/mercury/logic/heplers/services/`), metoda aktualizacji ze zmianą typu (`updateCaseWithHistory`): (1) blok „przywracam poprzednią wersję typu” (ok. linii 690): puste wartości z żądania są zastępowane wartościami z bazy (`caseFromDB.getParameter(oldPosition)`), (2) blok „wypełnij nową sprawę wartościami ze starej” (ok. linii 820 i dalej) przy zmianie typu i tworzeniu nowej wersji. Komentarz w kodzie z 2019 r. („FIXME co z polami o takich samych nazwach?”, zmienna `shit`) dotyczy tego samego miejsca.

**Do rozstrzygnięcia przed kodem:**
1. Co znaczy „pole nie istnieje w żądaniu” po stronie serwera: pozycja nieustawiona (`null`) czy pusty tekst. Dziś `StringUtils.isBlank` traktuje je tak samo i przepisuje stare wartości.
2. Odtworzyć zgłoszenie testem (typ z 34 → 22 parametrami, zapis starszym i nowszym typem), bo w 3.0 duplikatów autor nie odtworzył, a pozostałe pola dostają stare wartości.
3. Zachowanie domyślne (`false`) zostaje jak dziś; `true` ustawia pola nieprzesłane na `null` w nowej wersji.

## Postęp (2026-11-17)

Decyzja autora: „pole nie istnieje w żądaniu” oznacza tylko pozycję nieustawioną (`null`). Gałąź `hgdb-056` w `mercury` (od `master` po `pull`) i w `docusaurus-hgdb`.

- **Kod (`mercury-srv`):** `CaseLogicHelper.mergeParameterValue(valueFromRequest, valueFromDb, nullIfNotInRequest)`; `CaseLogicHelperService.updateCaseWithHistory`, blok „przywracam poprzednią wersję typu”, czyta flagę `SaveRequestContext.VALUE_IS_NULL_IF_FIELD_NOT_EXISTS_IN_REQUEST.getContextValue(context)` (kontekst, a gdy brak, domyślna z `mercury.properties`).
  - flaga wyłączona (domyślnie): zachowanie bez zmian, pusta wartość z żądania (`null`, tekst pusty, same spacje) jest zastępowana wartością z bazy;
  - flaga włączona: pole nieustawione w żądaniu zostaje `null`, każda wartość ustawiona w żądaniu, także tekst pusty, nadpisuje wartość z bazy.
- **Poza zakresem (świadomie):** blok „zmiana tylko typu” (migracja wartości ze starej sprawy po definicjach) przepisuje wartości ze starej sprawy z założenia, niezależnie od żądania, więc flaga go nie dotyczy.
- **Testy:** `CaseParameterMergeTest` (4, jednostkowe, bez bazy) przechodzi (`mvn -o -pl mercury-srv`). **Brak testu scenariuszowego na bazie** (zmniejszenie z 34 do 22 parametrów): wymaga infrastruktury (Terracotta, ActiveMQ, `mercury-db-test`), którą uruchamia autor.
- **Dokumentacja:** artykuł o `Context` (docusaurus EN i PL) miał już wszystkie parametry `saveRequestContext.*` (zgodne z enumem); opis `valueIsNullIfFieldNotExisisInRequest` rozszerzony o zakres i zachowanie.
- **Do zrobienia:** (a) test scenariuszowy na bazie, (b) ustalić, czy klient `hgdb-client-open` powinien dostać metodę ustawiającą flagę (dziś jest tylko DTO `ContextSaveRequest` w `ccrto-openapi`), (c) obserwacje 171 i 170 oraz CMIS z Bearer (zadanie ma je objąć).
