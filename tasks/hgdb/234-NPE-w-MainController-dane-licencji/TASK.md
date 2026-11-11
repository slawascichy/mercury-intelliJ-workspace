# [234] NullPointerException w `MainController.index` („Can't load license data.”)

Status: **w toku (2026-11-11)**: przyczyna potwierdzona testem, poprawka w `mercury-lib` (gałąź `hgdb-234`, niezacommitowana); do wydania `mercury-lib` i decyzji o `MainController`.

## Objaw

Log z 2026-11-05 17:35:52 (`stacktrace.txt`): `ERROR [MainController.java:85] : Can't load license data.`, `NullPointerException` w `java.text.SimpleDateFormat.<init>(SimpleDateFormat.java:598)`, wywołanym z `pro.ibpm.mercury.app.actions.jsp.MainController.index(MainController.java:56)`. Strona główna (`GET /`) nie pokazuje danych licencji (wyjątek jest złapany w `catch (Exception e)` i tylko logowany).

## Gdzie jest NPE

`MainController.java:56` (`mercury/mercury-ws-app`):

```java
Locale lLoc = new Locale(langValue, MercuryConfig.getSystemTerritory());   // linia 54
String fromatPattern = MercuryConfig.getDateLoggerFormat();                // linia 55
SimpleDateFormat dateFormat = new SimpleDateFormat(fromatPattern, lLoc);   // linia 56
```

Konstruktor `SimpleDateFormat(String, Locale)` w Javie 8 rzuca `NullPointerException` (bez komunikatu, stąd `null` w logu) tylko wtedy, gdy `pattern == null` albo `locale == null`. Locale nie jest `null` (`new Locale(...)`; `null` w `langValue` dałby NPE w konstruktorze `Locale`, nie w `SimpleDateFormat`). Zostaje `fromatPattern == null`, czyli `MercuryConfig.getDateLoggerFormat()` zwróciło `null`.

## Przyczyna (z kodu)

`mercury-lib/mercury-core/.../config/MercuryConfig.java`, linie 300–307:

```java
public static String getDateLoggerFormat() {
    if (dateLongFormat == null) {            // <-- zły warunek: pole dateLongFormat, powinno być dateLoggerFormat
        dateLoggerFormat = (... ? DEFAULT_DATE_LOGGER_FORMAT : ...);
    }
    return dateLoggerFormat;
}
```

Warunek sprawdza **inne pole** (`dateLongFormat`, format daty długiej) niż to, które ustawia i zwraca (`dateLoggerFormat`). To błąd kopiuj-wklej z `getDateLongFormat()` (linie 286–293), wprowadzony w commicie `29a7d60` „Zmiana parametru konfiguracji z formatem daty do logowania” (przypuszczenie co do pochodzenia: `git log -S` wskazuje też wcześniejsze commity zmieniające ten plik).

Skutek: gdy **przed pierwszym** `getDateLoggerFormat()` ktoś wywoła `getDateLongFormat()` (które ustawia `dateLongFormat`), warunek jest fałszywy, `dateLoggerFormat` zostaje `null` i metoda zwraca `null`. Taki kod wykonuje się m.in. w `AbstractController` (`mercury-gui-core`, linia 98: formaty kontekstu GUI) i `ReportUtils` (linia 69). Po tym `getDateLoggerFormat()` zwraca `null` do czasu `cleanStaticProperties()` (linie 101–111 zerują oba pola). Zależy więc od kolejności: kto pierwszy wejdzie, `MainController` (strona `/`) albo kod wołający `getDateLongFormat()`.

Ten sam błąd dotyka innych wywołań `getDateLoggerFormat()`: `CaseDAO.java:270` (`new SimpleDateFormat(MercuryConfig.getDateLoggerFormat())`, ten sam NPE) i `HtmlArguments.java:110` (zwróci `null` do atrybutu HTML).

## Do zrobienia

1. **Odtworzyć** w teście jednostkowym `mercury-core`: `MercuryConfig.getDateLongFormat()` przed `getDateLoggerFormat()` zwraca `null` (test czerwony), po poprawce `yyyy-MM-dd HH:mm:ss,SSS` albo wartość parametru `date.format.logger`.
2. **Poprawić warunek** w `getDateLoggerFormat()` (`dateLoggerFormat == null`) w `mercury-lib` (zmiana w sąsiednim repozytorium: wymaga zgody autora, bo domyślnie tylko je czytamy).
3. Sprawdzić **pozostałe gettery** (`getDateFormat`, `getNumberFormat`, `getCurrencyFormat`, `getCurrencyCode`, `getIntegerFormat`, `getSystemLang`, `getSystemTerritory`) pod kątem tego samego błędu kopiuj-wklej (pierwsze przejrzenie: `getDateFormat` i `getDateLongFormat` mają poprawne warunki).
4. **Zabezpieczyć `MainController.index`:** błąd formatowania daty nie powinien kasować całej sekcji danych licencji; `catch (Exception)` połyka zbyt dużo (decyzja, czy zmieniać).
5. Wydanie `mercury-lib` (numer wg rytuału) i test w `mercury-ws-app` (strona `/` po wejściu na ekran logowania lub raportu).

## Czego nie sprawdzono

- Nie odtworzono błędu na działającym serwerze. Z logu z 2026-11-05 nie wynika, która ścieżka wywołała wcześniej `getDateLongFormat()`.
- Nie sprawdzono, od jakiej wersji `mercury-lib` istnieje błąd i czy wpływa na wersje wydane.

## Wyniki (2026-11-11)

- **Test odtwarzający:** `mercury-lib/mercury-core/src/test/java/pro/ibpm/mercury/config/MercuryConfigFormatsTest.java` (3 przypadki: logger po formacie daty długiej, odwrotna kolejność, niezależność formatów). Przed poprawką 2 z 3 czerwone (`getDateLoggerFormat()` zwraca `null`), czyli hipoteza z analizy potwierdzona.
- **Poprawka:** `MercuryConfig.getDateLoggerFormat()` sprawdza `dateLoggerFormat == null` (było `dateLongFormat == null`), jedna linia.
- **Po poprawce:** `MercuryConfigFormatsTest` 3/3 i `MercuryConfigTest` 1/1 zielone (`mvn -o test -pl mercury-core -Ddatabse.provider=POSTGRESQL -Duser=scichy -Dtest=MercuryConfigFormatsTest,MercuryConfigTest`).
- **Przegląd getterów (punkt 3):** pozostałe gettery (`getDateFormat`, `getDateLongFormat`, `getLoggerAddDate`, `getNumberFormat`, `getCurrencyFormat`, `getCurrencyCode`, `getIntegerFormat`, `getSystemLang`, `getSystemTerritory`, `getSystemTimeZone`, `getSystemLocale`) sprawdzają to samo pole, które ustawiają. Błąd występował tylko w jednej metodzie.

## Do zrobienia

1. Autor: commit (`hgdb-234 Poprawka warunku w MercuryConfig.getDateLoggerFormat`), wydanie `mercury-lib` (kopie do `.m2`, numer wg rytuału), push, PR, merge.
2. Decyzja: czy zabezpieczać `MainController.index` (błąd formatu daty kasuje całą sekcję danych licencji; `catch (Exception)`), czy zostawić po poprawce źródłowej. Przypuszczenie: po poprawce nie ma takiej potrzeby, bo `getDateLoggerFormat()` zawsze zwraca niepustą wartość.
3. Po wydaniu `mercury-lib` w `mercury`: sprawdzić stronę `/` na dev-serverze (dane licencji) i brak wpisu `Can't load license data.` w logu.
