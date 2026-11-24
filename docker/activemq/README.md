# ActiveMQ dla pracy lokalnej

Broker Apache ActiveMQ Classic 5.19.12 (Java 17) w Dockerze. Zastępuje lokalny katalog `mercury/mercury-server/apache-activemq-*`.

| Usługa | Adres |
|---|---|
| OpenWire (Mercury, POI Server) | `tcp://localhost:51616` |
| Konsola WWW | http://localhost:8161 (`admin` / `admin`, tylko z tego komputera) |

## Użycie

```bash
./startActiveMq.sh          # start (buduje obraz, czeka na port)
./startActiveMq.sh status
./startActiveMq.sh logs
./startActiveMq.sh stop     # kolejki w woluminie zostają
./startActiveMq.sh reset    # usuwa też dane
```

Przed startem zatrzymaj stary lokalny ActiveMQ (te same porty 51616 i 8161). Porty zmienia się zmiennymi `AMQ_PORT` i `AMQ_UI_PORT`.

## Konfiguracja

- `conf/activemq.xml`: domyślna konfiguracja 5.19.12, złącze OpenWire na 51616 (`maxFrameSize` 100 MB), trwałość w KahaDB, `id="broker"` na `<broker>`.
- `conf/jetty.xml`: konsola nasłuchuje na `0.0.0.0` wewnątrz kontenera (host publikuje ją tylko na `127.0.0.1`).
- Linia 5.19.x używa javax JMS, więc klienci `activemq-client` 5.19.x w Mercury nie wymagają zmian w kodzie.
- Ścieżka `ACTIVEMQ_HOME` musi być rzeczywista (bez dowiązania), bo Jetty odrzuca zasoby konsoli przez symlink.
