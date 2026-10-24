# [116] Usługa updateCasesParamsByParams nie działa prawidłowo

https://github.com/slawascichy/hgdb/issues/116

Usługi REST dla aktualizacji parametrów nie działają prawidłowo.
Należy zweryfikować działanie usługi updateCasesParamsByParams i poprawić jej działanie.

# Zakres

1. Zweryfikować działanie usługi i odtworzyć błędy (scenariusz `UpdateCasesParamsScenario` w `mercury-srv`).
2. Scalać wpisy tej samej sprawy. Gdy żądanie ma kilka wpisów o tym samym `caseId`
   (np. po jednym polu na wpis), serwer łączy je w jeden wpis przed aktualizacją. Dzięki temu
   sprawa jest zmieniana w jednej transakcji, a nie w kilku równoległych (wątki, osobne
   transakcje). Wynik ma jeden wpis na sprawę, a nie jeden na wpis żądania. Powtórzone pole
   wygrywa ostatnią wartością. Klient powinien sam wysyłać jeden wpis na sprawę, a scalanie
   chroni przed błędem po stronie klienta.
3. Opisać zmianę w `@WSDLDocumentation` i w katalogach tłumaczeń `openapi-docs_*` (zmiana API).
4. Wynik weryfikacji dla 115 (`null`, raportowanie błędów) przekazać do zadania 115.
