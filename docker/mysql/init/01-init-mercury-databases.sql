-- Wykonywany przy pierwszym uruchomieniu (pusty katalog danych).
-- Baza `mercury` i użytkownik `mercury` powstają ze zmiennych MYSQL_DATABASE i MYSQL_USER.
-- Nazwy baz odpowiadają plikom test-mysql.properties (jdbc.mysql.default.dbName=mercury, jdbc.mysql.common.dbName=mercury_common).
-- Użytkownik dostaje pełne prawa na wszystkich bazach Mercury (jak w obrazie PostgreSQL w mercury-docker).
-- Hasło użytkownika ustawia MYSQL_PASSWORD, więc w tym pliku nie ma żadnych haseł.

CREATE DATABASE IF NOT EXISTS `mercury` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE DATABASE IF NOT EXISTS `mercury_common` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE DATABASE IF NOT EXISTS `mercury_ldap` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

GRANT ALL PRIVILEGES ON `mercury`.* TO 'mercury'@'%';
GRANT ALL PRIVILEGES ON `mercury_common`.* TO 'mercury'@'%';
GRANT ALL PRIVILEGES ON `mercury_ldap`.* TO 'mercury'@'%';
FLUSH PRIVILEGES;
