# [171] Optymalizacja "optymalizatora kosztowego"

https://github.com/slawascichy/hgdb/issues/171


## [RejestrPublikacji] Optymalizacja TYP PRZYŁĄCZA na PRD

Ciekawy problem opisany w zadaniu klienta https://support.ibpm.pro:8443/browse/CMINGW-846

Kiełczewski Łukasz  po warsztacie prośba o analizę czy jest szansa na optymalizację filtra "TYP PRZYŁĄCZA".
Prośba o podanie innych rozwiązań niż zwiększanie limitu.
Aktualnie mamy limit 5 min.

### Komentarze

#### Użytkownik lkielczewski Kiełczewski Łukasz dodał komentarz - 2023-03-22 15:02

Załączyłem plik excel, w arkuszu drugim znajduje się analiza pokazująca czas wykonywania się zapytań dla większości 
filtrów w rejestrze przed i po dodaniu hintów.

#### Użytkownik jkruszka Kruszka Jacek dodał komentarz - 2023-03-22 20:44

Kiełczewski Łukasz w arkuszu Scenariusze Fiberhost lista najczęściej używanych kombinacji filtrów w rejestrze 
Rejestr_pub_jk.xlsx
daj znać gdyby było coś niejasnego

#### Użytkownik jkruszka Kruszka Jacek dodał komentarz - 2023-03-22 20:44

Sprawdziłem najczęściej używane kombinacje filtrów w rejestrze(załącznik), wynika z niej, że hinty znacznie udrażniają problem filtrowania po typie przyłącza, jednak dla niektórych filtrów takich jak np. TERC, gmina, Miejscowość, potrafią wydłużyć czas wykonywania się zapytań (do 10 sekund). Moja rekomendacja to dodanie hintów podczas zapytań gdzie występuje typ przyłącza z wartością doziemne.

#### Użytkownik mkawa Kawa Michal dodał komentarz - 2023-03-28 17:21 - zmieniono

Wdrożyłem funkcjonalność dodawania hintów podczas zapytań o typ przyłącza na tst i prod, czas zapytań o "doziemne" został skrócony do ok. 10 sekund,

Przeprowadziliśmy analogiczne testy jak w załączonych przez Was plikach.

Czasy, które podaliście w większości przypadków się zgadzają jednak zaobserwowaliśmy kilkukrotnie zwiększony czas filtrowania raz na kilka filtrowań. Doszliśmy do wniosku, że w tym czasie ktoś inny pracował w Rejestrze Publikacji i postanowiliśmy przeprowadzić testy. Okazało się, że praca drugiej osoby ma ogromny wpływ na wydajność. Na przykładzie filtra Gotowy do Geografii:
W przypadku jeśli pracuje jedna osoba filtrowanie zajmuje 10-11 sekund. W przypadku jeśli druga osoba korzysta z Rejestru czas wydłuża się do ponad minuty w każdym z przypadków. Poniżej tabela, która pokazuje jak wydłużył się czas pobierania danych dla filtra "Czy gotowy do Geografii" na TAK:

| Czynność wykonywana przez użytkownika 2 | Czas filtrowania użytkownika 1 [sekund] |
|:---|:---:|
| Brak                                    |                   11                    |
| gotowy do geografii TAK (filtrowanie)   |                   69                    |
| technologia sieci - pobieranie filtrów  |                   74                    |
| technologia sieci GPON (filtrowanie)    |                   74                    |
| pobieranie filtrów miejscowości         |                   70                    |
| technologia sieci GPON (filtrowanie)    |                   71                    |


Zaobserwowaliśmy również wydłużenie czasu "Pobierania filtrów" jednak na to nie mamy pomiarów przed zmianami.

Dodatkowo niepokojący jest fakt, że aby przyspieszyć filtr "Typ przyłącza" musimy spowolnić większość innych filtrów.

Załączam plik, w którym Patrycja przeszła większość scenariuszy i uzupełniła czas filtrowania i pobierania filtrów: Rejestr_pub-1 PB.xlsx

## Podsumowanie

Aby zapytanie dobrze się wykonywało trzeba sterować trzema parametrami kontekstu:

1. maxResults
2. requestProperties
    - "org.mercury.lucene.query.hint.ruleRootFirst"
    - "org.mercury.lucene.query.hint.useCostOptimization"

I teraz w zależności od rozkładu danych można byłoby wpływać na powyższe parametry. Trzeba to przemyśleć. i zoptymalizować plan.