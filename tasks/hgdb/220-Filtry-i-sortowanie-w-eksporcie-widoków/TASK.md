# [220] Filtry i sortowanie w eksporcie widoków do pliku Excel

https://github.com/slawascichy/hgdb/issues/220

**Status (2026-10-29): not now.** Zadanie założone przy zamykaniu zadania 016 (Widoki). Nic nie zaimplementowano i nie jest planowane w najbliższym czasie. Poniżej tylko opis problemu i opcje, żeby po decyzji o wznowieniu nie odtwarzać analizy.

## Problem

Eksport widoku do pliku Excel (zadanie 016, etap 3) obejmuje **cały widok** w zakresie uprawnień użytkownika. Podgląd w modelu Excel (`CaseViewExtRest/readViewExcelData`) przyjmuje pełne zapytanie `ViewQuery` (filtry, sortowanie, strona), ale eksport go nie przyjmuje: nie da się wyeksportować np. tylko wierszy z danego miasta albo posortowanych według daty.

Przyczyna jest w sposobie przekazania zapytania do raportu. Eksport zleca `ReportExportStatusRest.prepareReportRequest`, a zlecenie zapisuje się w `ReportExportStatus`. Pole `PARAMS` jest `varchar(255)` (`igo_da_report_exps.PARAMS` i `igo_da_report_imps.PARAMS`), więc zapytanie z filtrami i sortowaniem w postaci tekstowej się w nim nie mieści. W zadaniu 016 przyjęto opcję B: w `PARAMS` jest tylko prefiks `[VIEW]` i nazwa widoku (`[VIEW]vName=<widok>&file=...`).

## Opcje

| Opcja | Opis | Skutek |
| :--- | :--- | :--- |
| A | Poszerzyć `PARAMS` w `igo_da_report_exps` do 4000 i zapisywać w nim zakodowane `ViewQuery` | Zmiana schematu na czterech bazach (skrypty w `mercury/db/<baza>`), zmiana encji w `mercury-lib` i wydanie. Najprostsze w kodzie eksportu |
| B1 | Zachować `PARAMS`, a zapytanie zapisać osobno (np. jako zapisane zapytanie widoku) i w `PARAMS` podać tylko odwołanie | Nowy byt (tabela albo encja) i jego cykl życia (kto usuwa), więcej kodu |
| B2 | Zachować `PARAMS`, a zapytanie zapisać w istniejącym mechanizmie LOB (jak wartości powyżej 4000 znaków) i w `PARAMS` podać identyfikator | Wykorzystuje istniejący mechanizm, ale trzeba obsłużyć sprzątanie i odczyt w `ExportGenerator` |
| C | Ograniczyć filtrowanie w eksporcie do zapytań mieszczących się w 255 znakach | Najtańsze, ale rzeczywiste filtry się nie zmieszczą |

Przy każdej opcji eksport musi użyć tego samego `ViewQuery` co podgląd, więc użytkownik widzi w podglądzie dokładnie to, co trafi do pliku. Do ustalenia: czy eksport przyjmuje zapytanie z filtrami i sortowaniem tylko z podglądu (jedno źródło prawdy), i jak walidować kolumny z zapytania względem widoku.

## Co jest już gotowe (zadanie 016)

- `ViewQuery` (filtry `EQ`, `NE`, `LT`, `LE`, `GT`, `GE`, `LIKE`, `IS_NULL`, `IS_NOT_NULL`, sortowanie, strona) i jego wykonywanie w `readViewData`.
- Prefiks `[VIEW]` w `PARAMS` i gałąź eksportu widoku w `ExportGenerator.generateViewReport` (strony czytane przez `readViewData`).
- Dekodowanie wartości jak w eksporcie spraw (`PoiServerWriter.convertViewPage`).

## Powiązania

- Zadanie 016 (Widoki), etap 3: `../016-Widoki/TASK.md`, sekcje „Etap 3”.
- Zadanie 219 (wydajność generowania plików Excel): eksport dużych widoków z filtrami zmniejszyłby wolumen, ale nie zastępuje analizy wydajności.
- Obserwacje 114–116 (nadmiarowa kolumna w eksporcie spraw, stub RMI po restarcie POI, kolejka raportów).
