# Podsumowanie 2026-11-17

## Zamknięte i wydane

- **Zadanie 245** (strony admina jako JSP, nagłówek z językiem i wyborem węzła, `n=` i ciasteczko `hgdb_node` w nginx, strony `files/*` i `lobs/*`, modal planu, tłumaczenia `admin.*` przez translator, przełącznik języka na stronie głównej): wydane jako `mercury` 3.0.4.27. Pakiet i obrazy `ibpm/mercury:mercury-hgdb-3.0.4.27` i `ibpm/mercury-lb:mercury-hgdb-3.0` w Nexusie; Kubernetes `mercury-test` zaktualizowany.
- **Zadanie 056** (flaga `valueIsNullIfFieldNotExisisInRequest`) razem z obserwacjami 171 i 170 oraz CMIS z Bearer: wydane jako `mercury` 3.0.4.28. Pakiet `mercury-install-package-3.0.4.28.POSTGRESQL.20261117.zip` w Nexusie raw, obraz `ibpm/mercury:mercury-hgdb-3.0.4.28` (digest `sha256:20d65cdea3d5…`) wypchnięty; Kubernetes `mercury-test` zaktualizowany (helm rewizja 7).
  - **Flaga:** serwer czyta ją w `CaseLogicHelperService` (pozycja nieustawiona → `null`, domyślnie bez zmian), test jednostkowy `CaseParameterMergeTest` i scenariusz `reducedParamsScenario` na `mercury-db-test`; klient: `SaveRequestFlags` w `hgdb-client-open`; dokumentacja `Context`.
  - **Obserwacja 171 ✅:** miganie strony „Zapytania Lucene” (round-robin między węzłami); strony `lucene-queries`, `loggers`, `secretaries` pytają węzeł, który je wyświetlił, a zawartość podmieniana jest jednym ruchem.
  - **Obserwacja 170 ✅:** po logowaniu na innym węźle niż pokazał formularz Tomcat używał `landingPage` (`types.html`); `ClusterFormAuthenticator` kopiuje adres zapisanego żądania `GET` do replikowanych atrybutów sesji; `landingPage` dla `mercury-ws-app` to `/`.
  - **CMIS Bearer ✅:** `BearerTokenCallContextHandler` dla wiązania `/browser/*` (OpenCMIS `TokenCallContextHandler` odrzucał nagłówek Bearer).
- **Sprzątanie:** `D:\mercury-245` skasowane, po PG13 tylko archiwum rar, lokalna kompozycja `mercury245` zatrzymana.

## Zadanie 219 (wydajność generowania plików Excel): start

- **Decyzje autora:** cel 200 000 × 6 poniżej minuty; API serwera POI zachować, ale POI może wymagać modernizacji; dodać argument formatu wyniku (xlsx domyślnie, csv); zakres: odczyt i zapis; środowisko: maszyna lokalna, Kubernetes `mercury-test`, po aktualizacji także kompozycja na `devops-box-01`. Gałęzie `hgdb-219` w `mercury` i `poi-toolkit`.
- **Wynik etapu 2:** `WriterBenchmarkTest` (`poi-toolkit`): zapis 200 000 × 6 przez `ExcelFileWriter` trwa **5–6,5 s** (ponad 38 000 wierszy/s), czyli ok. 180 razy szybciej niż zmierzone eksporty z 29.10 (ok. 215 wierszy/s). **Hipoteza H1 (zapis pliku w POI) odrzucona**; czas jest gdzie indziej (konwersja H2, RMI H3, odczyt z `OFFSET` H4, brak nakładania faz H5). Ryzyko pamięci: wszystkie wiersze w pamięci do `commit` (ok. 640 MB dla tekstu).
- **Instrumentacja (etap 1):** `ExportGenerator.generateViewReport` zapisuje linię `INFO` z czasami faz (odczyt, konwersja, zapis stron do POI, commit). Jeszcze niewdrożona.
- **Dane do pomiaru na Kubernetesie `mercury-test`:** typ `Bench219` (6 pól: cztery tekstowe, `Decimal`, `Integer`), ok. 200 000 spraw ładowanych przez `CaseBusinessRest/saveList` paczkami po 1000 (generator `load219.py` w scratchpadzie, ok. 115–170 spraw/s); widok `T_Bench219` powstaje automatycznie dla typu.

## Do wiedzy

- Eksport z `ReportExportStatusRest/prepareReportRequest` (`viewName`, `typeCode`, `subject`, nazwa pliku) nie występuje w OpenAPI, ale kontroler istnieje.
- `mvn package` zmienia wygenerowane `openapi*.json` i `ehcache-*-ext-3.5.xsd` (do `git checkout`).
- Niezacommitowane: `mercury` (instrumentacja `ExportGenerator`, `minor_version.txt`), `poi-toolkit` (`WriterBenchmarkTest`), podbite wersje w `mercury-docker`, `mercury-cmd`, `hgdb-client-open` (gałęzie `hgdb-056`).
