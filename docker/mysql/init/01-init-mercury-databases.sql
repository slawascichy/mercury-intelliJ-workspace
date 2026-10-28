-- Wykonywany przy pierwszym uruchomieniu (pusty katalog danych).
-- Baza `mercury-db` i użytkownik `mercury` powstają ze zmiennych MYSQL_DATABASE i MYSQL_USER.
-- Użytkownik dostaje pełne prawa na wszystkich bazach Mercury (jak w obrazie PostgreSQL w mercury-docker).
-- Hasło użytkownika ustawia MYSQL_PASSWORD, więc w tym pliku nie ma żadnych haseł.

CREATE DATABASE IF NOT EXISTS `mercury-db` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE DATABASE IF NOT EXISTS `mercury-common` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE DATABASE IF NOT EXISTS `mercury-ldap` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

GRANT ALL PRIVILEGES ON `mercury-db`.* TO 'mercury'@'%';
GRANT ALL PRIVILEGES ON `mercury-common`.* TO 'mercury'@'%';
GRANT ALL PRIVILEGES ON `mercury-ldap`.* TO 'mercury'@'%';
-- widoki testowe tworzone są w bazie mercury-db; bez prawa CREATE VIEW/SHOW VIEW wystarczają powyższe uprawnienia
FLUSH PRIVILEGES;
