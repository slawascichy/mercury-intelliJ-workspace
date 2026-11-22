 # [96] GUI do zarządzania danymi uwierzytelniania i autoryzacji

Teraz zmiany w bazie danych wymagają restartu serwera aplikacji, ale implementacja `org.mercury.oauth.config.DynamicSecurityOAuthConfigManager` zawiera metodę `refresh()`. Można się zastanowić nad wystawieniem usługi realizującej zadanie odświeżania konfiguracji po jej zmianie.
W ogóle przydałby się interfejs do zarządzania danymi realm'a:
1. Przegląd i aktualizacja lokalnych użytkowników
2. Profil lokalnego użytkownika (zmiana hasła, zmiana danych kontaktowych)
3. Przegląd użytkowników LDAP
4. Przegląd i aktualizacja powiązań uży`tkowników i grup z rolami aplikacji
5. Przegląd i zmiana konfiguracji tokenów OAuth

Originally posted by @slawascichy in https://github.com/slawascichy/hgdb/issues/54#issuecomment-601631572_

Można to zrobić w aplikacji `mercury-gui-registry` albo w nowej aplikacji `mercury-gui-auth`. W tym drugim przypadku trzeba by było wprowadzić nowy moduł `mercury-gui-auth` w projekcie `mercury` i dodać go do konfiguracji `mercury-gui-registry`. Wtedy w `mercury-gui-registry` można by było dodać link do nowej aplikacji.