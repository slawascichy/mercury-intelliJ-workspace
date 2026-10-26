# [58] Logger - dynamiczne zmiana poziomów logowania

W HSBC zrobiłem obsługę log4j z dynamiczną zmianą parametrów poziomu logowania. Jest to bardzo przydatne rozwiązanie gdy chcemy bez restartu uchwycić problem.

## Cel

Efektem końcowym byłoby:

1. Usługa **REST** (bez SOAP; decyzja autora z 2026-10-26) z metodami:
   - pobranie obecnego poziomu logowania dla danej kategorii
   - zmiana obecnego poziomu logowania dla danej kategorii
   - wyszukiwanie kategorii, ale z tym ostrożnie, bo wynik wyszukiwania może być bardzo duży. Najlepiej założyć, że zwraca 10, 20 max. 30 wyników
2. w aplikacji webowej mercury-ws-ap panel administracyjny pozwalający zarządzać poziomami logowania.

## Zaktualizowane cele (2026-10-26)

Decyzja autora: zadanie obejmuje **tylko REST**. SOAP jest niepotrzebny na obecnym poziomie i kierunku rozwoju aplikacji.

1. Usługa REST z operacjami: pobranie poziomu logowania dla kategorii, zmiana poziomu dla kategorii, wyszukiwanie kategorii (wynik ograniczony do 10, 20, najwyżej 30 pozycji).
2. Panel administracyjny w aplikacji webowej `mercury-ws-app` do zarządzania poziomami logowania.
3. Opis w specyfikacji OpenAPI (sześć języków: pl, en, de, es, fr, ko), uprawnienia tylko dla administratora (przypuszczenie, do potwierdzenia), test jednostkowy zmiany poziomu.

Uwagi z rozpoznania kodu:

- Usługi REST pisane ręcznie (`I*ExtRest`, np. `ICaseSearchExtRest`) leżą w `mercury-ws-app` (repozytorium `mercury`). Usługa REST-only nie wymaga więc zmian w `mercury-lib`
  ani wydania biblioteki (przypuszczenie: dopóki DTO operacji nie trafią do `mercury-lib`).
- Backend logowania wymaga ustalenia: `mercury/pom.xml` ma jednocześnie `slf4j-reload4j` (log4j 1.x API) i `log4j-core` 2.17.2, a skrypty startowe używają `-Dlog4j.configuration` (styl log4j 1.x).
