# [222] [GUI] Panel monitorowania sekretarzy

https://github.com/slawascichy/hgdb/issues/222

1. Rozbudowa usług rest  mercury-ws-app\src\main\java\pro\ibpm\mercury\rest\server\actions\secretaries
   \SecretariesRest.java. Dodanie usług wpierwjących wizualizację stanu sekretarzy:
    - Czy pracuje?
    - Jak długie sa kolejki (wielkość buforów)
2. W oparciu o SecretariesRest przygotowac stronę monitoringu sekretarzy w mercury-ws-app. Analogicznie jak działa mercury-ws-app\src\main\webapp\static\admin\loggers.html: sekcje dotyczące posczególnych sekretarzy z wizualizacją działania i przyciskiem start/pobudź.