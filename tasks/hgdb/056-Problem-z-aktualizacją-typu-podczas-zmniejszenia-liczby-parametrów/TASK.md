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

