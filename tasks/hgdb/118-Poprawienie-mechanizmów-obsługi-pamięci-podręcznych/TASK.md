# [118] Poprawienie mechanizmów obsługi pamięci podręcznych

Ogólnie trzeba zweryfikować poprawność wykorzystania pamięci podręcznych, szczególnie w klastrze. Czy to co teraz robimy jest OK? Czy faktycznie dane przepływaja pomiędzy węzłami klastra w sposób prawidłowy? Czy nie ma problemów z synchronizacją danych w pamięciach podręcznych? Warto też sprawdzić, czy nie ma przypadków, gdzie dane są odświeżane zbyt często lub zbyt rzadko, co może wpływać na wydajność systemu.

Zastanowić się też czy są lepsze silniki pamięci współdzielonej i czy warto je wykorzystać w naszym systemie. Warto też sprawdzić czy nie ma problemów z wydajnością przy dużej liczbie węzłów klastra.

Problem: W żądaniu wysyłany jest kontekst z cacheUsage=REFRESH. To powoduje, że w ramach wykonywanej akcji odświeżane są pamięci podręczne wszystkich warstw. Powstała propozycja by móc uszczegółowić dane dotyczące jakiej warstwy pamięci podręcznych mają być odświeżane.
Zrobimy tak, że będzie można dodawać informacje jako elementy mapy (dodatkowe parametry) w polu `requestProperties` kontekstu. Domyślnie, jeżeli nie będzie ustawionych żadnych parametrów, to odświeżane będą pamięci podręczne tylko warstwy biznesowej.
Jakie parametry będziemy ustawiać (jak będą się nazywać) to ustalimy w trakcie dalszej analizy.

Przemyślę również implementację metody "find" dla encji TypeCase - może warto tam dodać specjalną przestrzeń pamięci podręcznej skoro Hibernate sobie z tym nie radzi.

