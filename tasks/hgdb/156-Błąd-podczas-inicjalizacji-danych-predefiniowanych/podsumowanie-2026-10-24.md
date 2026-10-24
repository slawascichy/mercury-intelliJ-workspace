# Podsumowanie zadania 156: Błąd podczas inicjalizacji danych predefiniowanych

Data: 2026-10-24. Status: **zrobione, nie wymagało zmian w kodzie**. Błąd naprawiło zadanie 172.

## Przyczyna

`PredefiniedValuesLoader.loadMercuryData` ładował użytkowników systemowych z `SystemUser.csv`
(dla `sysmercury` jest to `id = 0`). Szukał ich przez `em.find(SystemUser.class, id)`.
Gdy w bazie `sysmercury` istniał już pod innym `id`, `find` zwracał `null`. Loader robił `INSERT`
i łamał ograniczenie unikalności kolumny `username` (`uk_jmappyt7bhw8j4jt3xi5h95ag`).
Błąd kończył się wpisem w logu, a transakcja ładowania danych była wycofywana.

## Co zmieniło zadanie 172

Commit `9e02e9a60` (2024-11-01), moduł `mercury-entities-ids`:

- Loader szuka użytkownika zapytaniem `MUser.QgetByUserName`, czyli po `username`.
  To jest to samo pole, na którym leży ograniczenie unikalności.
- `INSERT` jest wykonywany tylko wtedy, gdy zapytanie nic nie zwróciło.
- Użytkownik (nowy lub istniejący) trafia do `ISystemUserCache`.
- Blok użytkowników stoi na początku ładowania, przed definicjami parametrów.
- Nazwę pliku CSV można nadpisać właściwością `<Klasa>.predefined.data.fileName` w `mercury.properties`.

## Weryfikacja

1. **Logi lokalnego Tomcata** (`mercury-ws-app.log.1`, od 2026-10-18): 50 startów `loadMercuryData`,
   każdy bez `ConstraintViolation` i bez `ERROR : wyjatek`.
2. **Test scenariusza z innym `id`** (PostgreSQL, baza `scichy-test`, `-Duser=scichy-test`).
   Tymczasowa metoda w `EntityScenarioSupport` przepinała `sysmercury` na `id = 7777`
   (razem z kluczami obcymi `created_by` i `modified_by` w `IGO_DA_TYPEPARAMETERROLES`)
   i uruchamiała loader ponownie.
   - Obecny kod: `loadMercuryData` zwraca `true`, w bazie jest jeden wiersz `sysmercury` z `id = 7777`.
   - Kontrola ze starym wyszukiwaniem (`em.find` po `id`): ten sam błąd co w zadaniu
     (`duplicate key value violates unique constraint "uk_jmappyt7bhw8j4jt3xi5h95ag"`), `loadMercuryData` zwraca `false`.
   - Test usunąłem po weryfikacji (`git checkout`), baza wróciła do `id = 0`. Repozytorium `mercury` jest czyste.

Nie sprawdzano innych dialektów niż PostgreSQL.

## Uwagi do kodu (kosmetyka, bez osobnego zadania)

- W `PredefiniedValuesLoader` zmienna `flushIsNeeded` w bloku użytkowników nigdy nie jest ustawiana,
  więc `if (flushIsNeeded)` jest martwe.
- Literówka w logu: „inerted to cache”.

## Ocena zmian z zadania 172

Oceniam kod (`dd823c160`, 2025-10-02) i nie odtwarzałem problemu wyścigu. Wnioski o działaniu
pod obciążeniem oznaczam jako przypuszczenia.

**Co poprawiono (wynika z porównania ze starym `UserInfoSecretary`):**

- Stary kod miał wyścig „sprawdź, potem działaj”: `getRuningAction` i `runNewThread` nie były atomowe.
- Stary `finally` usuwał wpis z mapy także w wątku, który tylko dołączył się do cudzej akcji.
  Trzeci wywołujący mógł wtedy uruchomić drugi wątek dla tego samego użytkownika.
- Nowe `ActionWithReturnValueSupport` robi sprawdzenie i start pod blokadą klucza,
  a wpis usuwa tylko wątek, który go utworzył.
- Blokady kluczy (`LockGeneratorUtils`) mają licznik użyć, więc usunięcie blokady nie rozdziela
  czekających wątków.
- Mapa działających akcji jest `ConcurrentHashMap` (poprawka z hgdb-110).
- Timeout oczekiwania jest konfigurowalny (`mercury.actionWithReturn.timeout`, domyślnie 100 s).
  Po jego upływie w logu jest stos wątku, a wątek dostaje `interrupt`.
- Ten sam mechanizm obsługuje role i obiekty LOB, więc jest jedna implementacja zamiast trzech kopii.

**Ryzyka i luki (przypuszczenia, do rozważenia w osobnych zadaniach):**

1. **Wiele węzłów.** Blokady są lokalne dla JVM. Dwa węzły mogą jednocześnie wstawić tego samego
   użytkownika. Drugi dostanie błąd unikalności, to ten sam typ błędu co w 156, tylko w innym miejscu.
   `ModifyInfoHelperImpl.createUserInfo` robi samo `insert`. Naturalną poprawką jest ponowne
   wyszukanie po loginie, gdy `insert` się nie uda (tworzenie idempotentne).
2. **Brak wyniku po błędzie lub timeoucie.** `UserInfoUpdateSecretaryTh.run` łapie wyjątek
   i zostawia `result = null`. Wywołujący dostaje `null` bez informacji o przyczynie.
   Pole `result` nie jest `volatile`, a po timeoucie nie ma `join`, więc widoczność wyniku nie jest gwarantowana.
3. **Timeout nie kończy pracy.** `interrupt` nie przerywa zapytania JDBC. Wpis jest usuwany,
   a stary wątek może jeszcze pracować, więc kolejny wywołujący uruchomi drugi.
4. **Dołączający dostaje cudzy wynik.** Jeśli wątek `update` z innymi danymi użytkownika już działa,
   drugi `updateUserInfo` dołącza się do niego i jego dane nie są zapisane.
5. **Źródło blokady (przypuszczenie, nieodtworzone).** Wywołujący trzyma blokadę `synchronized`
   i transakcję, a autonomiczny wątek czeka na wiersz użytkownika w innej transakcji. Taka kolejność
   może dać zakleszczenie, które teraz kończy się timeoutem zamiast wiecznego oczekiwania.
   Warto zmierzyć, jak często timeout występuje w logach produkcyjnych (`thread waiting time expired`).
6. **Testy.** Jest `ActionWithReturnValueTest`. Problem wyścigu trudno odtworzyć lokalnie,
   więc warto dodać test wielowątkowy: N wątków wywołuje `createUserInfo` dla tego samego loginu
   i oczekujemy jednego wiersza oraz jednej wartości wyniku.

## Decyzje

- Zadanie 156 zamykamy bez zmian w kodzie. Gałęzi nie tworzono.
- Test z innym `id` nie został dodany na stałe (zgodnie z poleceniem). Można go dodać do `EntityTest`,
  wymaga przepinania kluczy obcych, więc jest nieco kłopotliwy.
