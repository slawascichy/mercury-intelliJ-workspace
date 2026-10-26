# [58] Logger - dynamiczne zmiana poziomów logowania

W HSBC zrobiłem obsługę log4j z dynamiczną zmianą parametrów poziomu logowania. Jest to bardzo przydatne rozwiązanie gdy chcemy bez restartu uchwycić problem.

## Cel

Efektem końcowym byłoby:

1. Usługa SOAP/REST z metodami:
   - pobranie obecnego poziomu logowania dla danej kategorii
   - zmiana obecnego poziomu logowania dla danej kategorii
   - wyszukiwanie kategorii, ale z tym ostrożnie, bo wynik wyszukiwania może być bardzo duży. Najlepiej założyć, że zwraca 10, 20 max. 30 wyników
2. w aplikacji webowej mercury-ws-ap panel administracyjny pozwalający zarządzać poziomami logowania.