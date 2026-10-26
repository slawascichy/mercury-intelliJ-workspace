# [49] [CMIS] Implementacja API CMIS


Mercury może robić za repozytorium dokumentów. Trzeba dorobić API CMIS.
Specyfikacja CMIS:

https://github.com/slawascichy/hgdb/blob/master/documents/CMIS/CMIS-v1.1.pdf
https://github.com/slawascichy/hgdb/blob/master/documents/CMIS/cmis-spec-v1.0.pdf
http://docs.oasis-open.org/cmis/CMIS/v1.1/os/schema/CMIS-Messaging.xsd
http://docs.oasis-open.org/cmis/CMIS/v1.1/os/schema/CMIS-Core.xsd
https://www.alfresco.com/whitepaper/cmis

## Komentarze

### Najczęściej wykorzystywane metody

Najczęściej wykorzystywane metody w kontrolkach dokumentowych BPM:

Pobierz folderu według ścieżki
Utwórz folder
Pobierz treść dokumentu
Utwórz dokument
Pobierz dokument
Pobierz elementy potomne typu
Pobierz definicję typu
Szukaj (dowolne zapytanie CMIS)
Usuń dokument
Aktualizuj właściwości dokumentu
Pobierz dokumenty w folderze
Pobierz dokument z repozytorium (Check Out)
Wprowadź dokument (Check In)
Kopiuj dokument

### Koncepcja

Wymaga predefiniowanego typu "Folder"
Katalog plików to Case2Case (NIE Case2SubCase)

### Analiza

OK, przeprowadziłem analizę wykonalności zadania poprzez implementację usług opartych o przykładowy serwer dostarczony z chemistry. Było cięzko, bo okazało się, że użycie MOX'y JAXB w naszym projekcie nie do końca współpracuje z gotowymi bibliotekami chemistry. Poprawiłem implementację bibliotek Apache Chemistry i te implementacje załączyłem do projektu. Wysłałem również propozycję zmiany w projekcie Apache Chemistry (https://lists.apache.org/list.html?dev@chemistry.apache.org:2019-2) - zobaczymy, może zrobią poprawkę i nie będziemy musieli utrzymywać własnych wersji tych bibliotek.

Na razie wstrzymuję prace nad tym zadaniem - muszę dokończyć #4 ale to co zrobiłem było konieczne, by nadać odpowiedni kontekst dla zarządzania plikami, a zadanie #4 właśnie tego dotyczy.

## Stan szkicu w kodzie (2026-10-26, lektura `web.xml` i kodu)

Szkic z analizy wykonalności jest **wpięty w produkcyjny `web.xml`** aplikacji `mercury-ws-app` (`mercury/mercury-ws-app/src/main/webapp/WEB-INF/web.xml`):

- serwlety Chemistry (OpenCMIS `${chemistry.version}` = 1.1.0): `cmisws10` i `cmisws11` (usługi sieciowe, `CmisWebServicesServlet`), `cmisatom10` i `cmisatom11` (`CmisAtomPubServlet`, ścieżki `/atom/*`, `/atom11/*`),
  `cmisbrowser` (`/browser/*`), `cmisendpoints` (`/cmis-endpoints.json`, plik `WEB-INF/cmis-endpoints.json`);
- fabryka usług: `org.mercury.cxf.ws.server.cmis.services.FileShareCmisServiceFactory` (`repository.properties`, wpis `class=`) i `HgdbCmisLifecycleBean` (`webService.xml`);
  dziewięć klas `FileShare*` w pakiecie `org.mercury.cxf.ws.server.cmis.services` to **przykładowe repozytorium plikowe** z Chemistry, a nie repozytorium Mercury;
- `repository.properties` zawiera tylko `class=` (bez `repository.*` i `login.*`), więc repozytorium plikowe nie jest skonfigurowane (przypuszczenie: żądania są odrzucane, nie testowano);
- ochrona: filtr `RemoteBasicAuthFilter` obejmuje `/cmisws10/*` i `/cmisws11/*`; ścieżki `/atom/*`, `/atom11/*`, `/browser/*` i `/cmis-endpoints.json` nie są objęte filtrem ani `security-constraint` (obserwacja 87);
- istnieje moduł klienta `mercury-cmis-client` oraz pliki `cmis10`, `cmis11` w `WEB-INF`.

Wniosek: pierwszym krokiem realizacji jest wymiana repozytorium plikowego na repozytorium oparte o Mercury (typ „Folder”, katalog plików jako `Case2Case`, zgodnie z koncepcją w tym zadaniu)
dla wybranego podzbioru metod, a przed wydaniem trzeba rozstrzygnąć, czy endpointy zostają w WAR-ze bez konfiguracji (obserwacja 87).
