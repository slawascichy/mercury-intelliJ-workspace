# Podsumowanie 2026-11-24

Zadanie **191** (rewizja wersji, migracja na Javę 17) na gałęzi `hgdb-191`, razem z podzadaniem **256** (Terracotta). Etapy 2, 3b i 3 zrobione, wdrożone na `mercury-cluster` i sprawdzone. Zostaje etap 4 (dokumentacja i spięcie) oraz etap 5 (Lucene 9).

## Zrobione

- **Etap 2:** lokalny Tomcat dev na Javie 17 startuje. Testy POI przez RMI i klientów na Javie 8 pominięte za zgodą autora (i tak testowane po 3b).
- **Etap 3b, POI Server na Javie 17:** obraz `poi-server` na Temurin 17. Poprawka w `poi-toolkit` (RMI na 17: `UnicastRemoteObject.exportObject`, zabezpieczenia `close()`), wydanie 4.1.0.6. Eksport 88 tys. wierszy zabijał pody (OOMKilled): przyczyną było balonowanie pamięci w Proxmoksie (naprawił autor) oraz trzymanie stron w pamięci. W `poi-toolkit` doszło tymczasowe zapisywanie stron na dysk (4.1.0.7, test `PageSpillTest`).
- **Etap 3, stos:** usunięte martwe zależności (aspectj, asm, cglib, `spring-security-core` w `ws-app`), wyczyszczony `apache-tomcat/mercury/lib`. Optymalizacja zależności `hgdb-client-open` (przed `mercury-cmd`). POI ujednolicone na **5.2.3** z `poi-ooxml-full` we wszystkich repozytoriach (`poi-toolkit` 4.1.0.8).
- **Poprawka `CaseSearchQueryBuilder`:** blok `subTypes` budował zapytanie z pustych podzapytań. Teraz bez podzapytań daje `(1 = 0)`, z nimi poprawny `OR`. Dwa nowe testy.
- **Obserwacje:** 177 ✅, 207 ❌ (wycofana: mój błąd, plik POI z moim uid), 208, 209 (ostrzeżenie JAXB `javax.xml.bind.context.factory`), 210 ✅ (SOAP i EHCache, obejście `MemoryTokenStore`), 211 ✅, 212 ✅.
- **Podzadanie 256 (Terracotta) i ActiveMQ:** zielone światło autora na kit **3.10.8** (Java 17 po stronie serwera, dynamiczna konfiguracja, 3 węzły HA sprawdzone lokalnie i na klastrze). ActiveMQ **5.19.12** na Temurin 17 (JMS 2.0 przez `jakarta.jms-api`). Klienci Ehcache 3.10.8 i ActiveMQ 5.19.12 w `mercury`, `poi-toolkit`, `mercury-lib`, `hgdb-client-open`, `mercury-cmd`; `sccommon` 2.0.0.5. Tagi obrazów z wersją produktu (`activemq:mercury-hgdb-3.0-5.19.12`, `ehcache:mercury-hgdb-3.0-3.10.8`) w skrypcie, chartach i kompozycjach.
- **Lokalne kompozycje dev w workspace:** `docker/terracotta` (3.10.8, `startEhcacheServer.sh`, porty 9510/9530) i nowe `docker/activemq` (OpenWire 51616, konsola 8161, `startActiveMq.sh`). Zastępują lokalne kity `ehcache-clustered-3.6.1-kit` i `apache-activemq-5.16.4` w `mercury-server`.

## Wydania

`sccommon` 2.0.0.5, `poi-toolkit` 4.1.0.11, `mercury-lib` 3.0.4.28, `mercury` 3.0.4.44, `hgdb-client-open` 3.1.4.28, `mercury-cmd` 3.1.4.20. Obrazy `mercury`, `poi-server`, `activemq`, `ehcache` w Nexusie, wdrożone na `mercury-cluster`.

## Problemy znalezione po wdrożeniu

1. **Pakiet instalacyjny brał stare jary.** `lib` pakietu pochodzi z `mercury/mercury-server/apache-tomcat/mercury/lib`, a tam zostały Ehcache 3.6.1 i ActiveMQ 5.16.2. Skutek: klient Terracotty 5.5.1 kontra serwer 5.9.5 (`client version is not compatible`), aplikacje nie startowały.
2. **Brak API JMS 2.0.** ActiveMQ 5.19 wymaga `jakarta.jms-api` 2.0.3, a w `lib` było `geronimo-jms_1.1_spec` (błąd `NoClassDefFoundError: javax/jms/JMSContext`).
3. **Duplikaty w katalogu wydania.** Ant nie czyści katalogu wydania, więc obok sccommon 2.0.0.5 zostały jary 2.0.0.4.
4. **POI bez JAXB.** Ehcache 3.10.8 czyta `ehcache.xml` przez JAXB, a Java 17 nie ma implementacji. Eksport Excela kończył się statusem `FAILED` (`NullPointerException` w `WriteRemote.isActive`). Poprawka: `org.glassfish.jaxb:jaxb-runtime:2.3.7` w `poi-toolkit` (4.1.0.11).
5. **`mercury-lib`:** błędny import `org.terracotta.context.query.QueryBuilder` w Javadoc czterech plików (kompilował się dzięki starej bibliotece statystyk Ehcache). Import usunięty.
6. **Konsola ActiveMQ 5.19:** filtr adresów w `jetty.xml` wpuszcza tylko loopback, więc przez Docker daje błąd HTTP 403 przed logowaniem. W `docker/activemq` dodane zakresy prywatne; w `mercury-docker` opis w README (`activemq`, `charts`).

## Testy na klastrze (po poprawkach)

`live4.sh`: 58 OK, 0 błędów. Eksport xlsx (1000 wierszy `Bench211`): `COMPLETED`. Import 300 wierszy: `COMPLETED` (`Bench211`: 89 528 do 89 828). Przy wysyłce pliku (`uploadPoiFile`) skrypt dostał **błąd HTTP 500**, mimo że import przeszedł: do zbadania.

## Decyzje

- `bpm-security-provider` jest powiązany tylko z zamrożonym `mercury-client`: w 191 i 256 nic po tej stronie nie sprawdzamy.
- Konsola ActiveMQ nie musi być wystawiona: wystarczy opis w dokumentacji (nadpisanie `jetty.xml`).
- Licencja Terracotta (TPL 2.0) w kitach: teksty przeczytane (`mercury-docker/ehcache/install/legal`), `legal/` zachowane w obu obrazach, w README dopisane odsyłacze do źródeł. Ocena dla IBPM zostaje po stronie autora.

## Niezacommitowane (robi autor)

`mercury-docker` (chart, kompozycje, README, skrypty, `poi-server`), workspace (`docker/terracotta`, `docker/activemq`, `tasks/`, `docs/obserwacje.md`), `poi-toolkit/pom.xml` (JAXB), `mercury-lib` (4 pliki z Javadoc).
