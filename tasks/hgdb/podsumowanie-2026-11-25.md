# Podsumowanie 2026-11-25

Zadanie **191** (rewizja wersji, migracja na Javę 17) razem z podzadaniami **256** (Terracotta) i **Lucene 9** jest **zamknięte**. Autor zrobił PR i merge we wszystkich repozytoriach, które są teraz w `master` lub `main`, bez zmian niezatwierdzonych.

## Zrobione

- **Lucene 9.12.3 (etap 5):** port `mercury` i `mercury-cmd` na API Lucene 9:
  - `scoreMode`, `Scorable`, `TotalHits`, `MultiTerms`, `FieldInfos`, `ByteBuffersDirectory`, `TopDocs.merge` bez `setShardIndex`,
  - własny `LazyQueueTopDocsCollector` w miejsce zablokowanej kolejki `pq`,
  - `ExactTotalHitsSearch` (domyślnie Lucene 9 liczy trafienia dokładnie tylko do progu 1000), z testem,
  - usunięty pakiet `search/cases/score` (Lucene 9 nie ma `CustomScoreProvider`),
  - znacznik SCN w danych commitu Lucene (`CaseIndexScnWatermark`) sprawdzony testami.
- **Wdrożenie na `mercury-cluster` (mercury 3.0.4.45):** indeks zbudowany na węźle 1 (555 s, 89 838 dokumentów, 14 MB) i skopiowany do węzłów 2 i 3 pomocniczym podem z PVC. `live4.sh` 58 OK, eksport, wyszukiwanie (89 828 = baza), SOAP i status 409 sprawdzone.
- **Status 409 Conflict** dla istniejącego pliku w `SystemFileUploadSupport` (z testem). Obejście `MemoryTokenStore` usunięte z `webService.xml` (SOAP działa na Ehcache 3.10.8).
- **Stopka GUI:** linia z odsyłaczem do `terracotta-core` (`mgui.footer.cache`, en i pl).
- **ActiveMQ:** opcjonalny `activemq.jettyConfigMap` w chartach. W `docker/activemq` zakresy prywatne w `jetty.xml`, żeby konsola nie dawała błędu HTTP 403.
- **Terracotta (TPL 2.0):** teksty licencji w obrazach (`legal/`), odsyłacze w README. Ocena prawna po stronie autora.
- **Licencje w docusaurus (en i pl):** katalog `003_Licenses`: OWLK z zaktualizowanymi wykazami (§2, §6), Załącznik 1 (bieżący wykaz składników 3.0.4.45, grupy jako `###`, w tabeli sam `artifactId`), Załącznik 2 (Iron POI Server OEM, w en z pełnym tłumaczeniem roboczym). Generator w `tools/licencje`. `docusaurus build` w en i pl przechodzi.
- **Dokumentacja (etap 4):** tabela stosu w `docs/architektura.md`, `docs/moduly/{mercury,mercury-lib,hgdb-client-open,mercury-cmd,mercury-docker}.md`, `README.md`, `CLAUDE.md`. W docusaurus: `Cache_configuration` (kit 3.10.8) i `Kubernetes_installation` (tagi obrazów, ramka „Java 17” z procedurą po przejściu na Lucene 9).
- **Numeracja `hgdb-client-open`:** sekcja „Numeracja wersji” w `README.txt`.
- **Wyniki w `TASK.md`:** 256 (Wynik, status kryteriów) i 191 (status etapów).
- **Obserwacje:** 213 ✅, 214 (nieaktualne załączniki OWLK), 215 (artefakty własnościowe w pakiecie), 216–220 (JAXB w POI na Javie 17, `jakarta.jms-api`, ant nie czyści katalogu wydania, błąd log4j w `SimpleClientTest`, `StandardAnalyzer` i procedura po Lucene 9).

## Wydania

`sccommon` 2.0.0.5, `poi-toolkit` 4.1.0.11, `mercury-lib` 3.0.4.28, `mercury` 3.0.4.45, `hgdb-client-open` 3.4.28.45, `mercury-cmd` 3.1.4.21. Obrazy w Nexusie: `ibpm/mercury:mercury-hgdb-3.0.4.45`, `ibpm/poi-server:mercury-hgdb-3.0`, `ibpm/activemq:mercury-hgdb-3.0-5.19.12`, `ibpm/ehcache:mercury-hgdb-3.0-3.10.8`.

## Zadanie 257 (założone)

Osobne zadanie „Test porównawczy dla indeksu Lucene 9” (191 na nie nie czeka). Decyzje autora:
- Migrator indeksu Lucene do HgDB (bazy INEA nie ma): z pól `stored` indeksu 7.x powstaje typ i sprawy w nowej bazie, indeks 9 budowany z bazy.
- Etap 0 to narzędzie `mercury-lu2hgdb` w `mercury-cmd` (gałąź `hgdb-257`): `lu2hgdb-api`, `lu2hgdb-core`, `lu2hgdb-lucene7`, `lu2hgdb-lucene9`, dwie dystrybucje, wybór w skrypcie bash.
- Argumenty: model indeksu (2.0 lub 3.0), wersja Lucene (7 lub 9), ścieżka. Do tego `--max-documents` i anonimizacja.
- Zanonimizowany zestaw może leżeć w wewnętrznym Nexusie i służyć testowo, ale nie wolno go udostępniać dalej. Narzędzie można udostępnić (bez danych).

## Decyzje

- Wydanie publiczne **3.0.5.x** na `nexus.scisoftware.pl` jest częścią zadania **211b** (jego zakończeniem). Tam też aktualizacja Załączników 1 i 2 do OWLK oraz obserwacje 214 i 215.
- `bpm-security-provider` jest powiązany tylko z zamrożonym `mercury-client`, więc nic tam nie zmieniamy.

## Otwarte

- **Autor:** sprzątanie lokalne (stare kity `ehcache-clustered-3.6.1-kit` i `apache-activemq-5.16.4`, dane `Bench211` ok. 89,8 tys. spraw, pliki testowe POI), tłumaczenia `mgui.footer.cache` na de, es, fr i ko w `localization-project`, ocena licencji TPL dla IBPM.
- **Niezbadane:** `SimpleClientTest` kończy się `NoClassDefFoundError: org/apache/log4j/config/PropertyPrinter` (obs. 219), przeniesione do 211b.
- **Wyjaśnione:** 500 przy `uploadPoiFile` to była powtórna wysyłka istniejącego pliku bez `override` (obs. 213), teraz 409, sprawdzone na klastrze.
- **Bez pomiaru:** porównanie wydajności Lucene 7 i 9 (zadanie 257) oraz test obciążeniowy Terracotta 3.10.8 względem 3.6.1.
- **Znane lokalne niepowodzenia testów, niezwiązane z 191:** `JoinFetchStatsTest`, `LuceneBackupSrvTest`, `SrvTest`, `AuthTest`, testy wymagające lokalnego indeksu Lucene 7.
