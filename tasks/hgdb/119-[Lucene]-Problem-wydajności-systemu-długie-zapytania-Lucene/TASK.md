# [119] [Lucene] Problem wydajności systemu - długie zapytania Lucene

https://github.com/slawascichy/hgdb/issues/119

W INEA występują problemy wydajnościowe - trzeba to zbadać.
To zadanie ma związek z zadaniem [171 Optymalizacja "optymalizatora kosztowego"](../171-Optymalizacja-optymalizatora-kosztowego/TASK.md) i może być jego kontynuacją.
 
## Ustalenia (2026-10-24)

- Podział zadań: **119** dotyczy wydajności wyszukiwania w indeksie, **171** problemu optymalizatora kosztowego. Mogą być realizowane razem.
- Pytania autora: (1) czy optymalizator kosztowy spełnia zadanie, (2) zapytania wielowątkowe (pomysł: 10 wątków, podział po dacie) oraz
  podział na wiele węzłów klastra, (3) wydajność i jakość kolektorów zapytań grupujących.
- Analiza kodu i plan: [analiza-2026-10-24.md](analiza-2026-10-24.md).
- Brak dużego indeksu do pomiarów. Decyzja: wygenerować dane testowe (pilot 10 tys. spraw `SlmAddress` + `SlmAppMobileDetails`, potem
  skala), baza `mercury-db` z profilu `scichy` (zgoda autora). Wzór dla `GeoAddressRegister`: `mercury/mercury-srv/MrcList.v1.xml`.
- Gałąź: `hgdb-119` w repozytorium `mercury`.
