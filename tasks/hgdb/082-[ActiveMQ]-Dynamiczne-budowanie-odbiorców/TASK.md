# [82] [ActiveMQ] Dynamiczne budowanie odbiorców

https://github.com/slawascichy/hgdb/issues/82
**Status: ✅ zamknięte 2026-11-02** (do zatwierdzenia i zamknięcia w GitHubie przez autora). Podsumowanie w sekcjach „Realizacja” poniżej i w `podsumowanie-2026-11-02.md`.

Zadanie nawiązuje również do problemu zdefiniowanego w zadaniu #53 .
Dla kolejek z wiadomościami "NIE filtrowanymi" mam następujące, sztywne rozwiązanie:
```
<compositeQueue name="mrc-pram-definition-registry-changes">
	<forwardTo>
		<queue physicalName="mrc-pram-definition-registry-changes-node1" />
		<queue physicalName="mrc-pram-definition-registry-changes-node2" />
	</forwardTo>
</compositeQueue>
```
Trzeba przetestować użycie wildcard:
```
<compositeQueue name="mrc-pram-definition-registry-changes">
	<forwardTo>
		<queue physicalName="mrc-pram-definition-registry-changes->" />
	</forwardTo>
</compositeQueue>
```
i jeżeli trzeba zmienić nazwy kolejek z separatorami zamiast "-" na kropkę ".", bo wszyscy używają kropek (zobacz http://workingwithqueues.blogspot.com/2012/10/activemq-composite-destinations.html).

Jeśli chodzi o kolejki "filtrowane" - to tu jest pomysł by napisać klasę. Jeden gościu fajnie napisał (chociaż post jest stary, ale wydaje się jary: http://activemq.2283324.n4.nabble.com/Dynamic-management-of-composite-destinations-td2384484.html):

> 1. Create your own classes:
     >      1. FeedInterceptor implements org.apache.activemq.broker.region.DestinationInterceptor
               >      This will intercept all new destinations in ActiveMQ. It can match the new destinations to any wildcard using a org.apache.activemq.filter.DestinationMap. This way you can figure out whether this is a regular destination, a virtual one, or a forwarded one (maybe filtered) that's part of the virtual destination. It returns the appropriate Destination depending on the match, (i.e. it can return a org.apache.activemq.broker.region.virtual.VirtualTopic--so that I don't reimplement it again, or a regular Destination, or my own custom FilteredQueueDestinationFilter--see below)
>      2. FilteredQueueDestinationFilter extends org.apache.activemq.broker.region.DestinationFilter
          >       This can be configured on the fly when created in the FeedInterceptor (above) and this way it can have a filter set up (or no filter) so that it can decide whether to send the message (that's about to be sent) on this destination or not. For filtering it uses a org.apache.activemq.filter.BooleanExpression that gets evaluated with every call to its send method.
>
> 2. Configure ActiveMQ:
     > In activemq.xml the destinationInterceptors tag has to look like:
>
>
```
>    <destinationInterceptors>
>       <bean xmlns="http://www.springframework.org/schema/beans"
>             id="CustomFeeds" class="com.yourdomain.FeedInterceptor">
>            
>             <property name="prop1" ref="prop-value"/>
>       </bean>
> 
>      
>       <virtualDestinationInterceptor>
>          <virtualDestinations>
>            <virtualTopic name=">" prefix="VirtualTopicConsumers.*." />
>          </virtualDestinations>
>        </virtualDestinationInterceptor>
>   </destinationInterceptors>
```
>
> The filter you can use with the BooleanExpression should be any selector you can write for JMS since it is the same mechanism that ActiveMQ uses for filtering JMS messages. The advantage of this is that the filtering happens inside ActiveMQ and this way the client has no control over it. On top of that the client can still use their own selector to further filter messages they receive (for example for load balancing).

Przede wszystkim tymi komponentami rozwiążę problem dynamicznego dodawania nowych węzłów do klastra...!
## Eksperymenty na wbudowanym brokerze (2026-11-02)

Źródła: `eksperymenty/Exp082.java`, `Exp082b.java`. Broker ActiveMQ 5.16.4 (`activemq-all-5.16.4.jar` z `mercury-server/apache-activemq-5.16.4`) uruchomiony w procesie testowym (bez zapisu na dysk, `vm://`), więc działający broker nie był ruszany. Uruchomienie: `javac -cp activemq-all-5.16.4.jar Exp082.java` i `java -cp activemq-all-5.16.4.jar;. Exp082`.

| Eksperyment | Wynik |
|---|---|
| E1: `compositeQueue` z `forwardTo` na `reg.changes.>` (wildcard) | **nie działa**: `StackOverflowError` przy wysłaniu wiadomości; wildcard w `forwardTo` odpada |
| E2: Virtual Topic (`name=">"`, `prefix="Consumer.*."`), kolejki `Consumer.<węzeł>.VirtualTopic.*`, selektor konsumenta `sender <> '<węzeł>'`; `node3` dochodzi bez zmiany konfiguracji brokera | **działa**: `node2` i dynamiczny `node3` dostają wiadomość, nadawca `node1` nie; `selectorAware=false` zostawia kopię wiadomości w kolejce nadawcy (zaległość 1), `selectorAware=true` nie (0) |
| E3: `filteredDestination` (stan dzisiejszy) | `node2` dostaje, `node3` (nieskonfigurowany) nie dostaje nic: potwierdza obserwację 139 |
| E4: wiadomość wysłana, gdy węzeł jest offline (kolejka istnieje) | `selectorAware=false`: **doręczona** po powrocie węzła; `selectorAware=true`: **utracona** (wiadomość nie trafia do kolejki bez konsumenta o pasującym selektorze) |

### Wniosek

- Wildcard w `compositeQueue` odpada. Własny `DestinationInterceptor` nie jest potrzebny.
- Virtual Topics rozwiązują dynamiczne dodawanie węzłów: konfiguracja brokera ma jedną regułę, a kolejka węzła powstaje, gdy węzeł się zgłosi.
- `selectorAware=true` gubi wiadomości dla węzła offline, więc odpada. `selectorAware=false` z selektorem u konsumenta zostawia w kolejce węzła wiadomości jego własne (zaległość rośnie bez końca).
- Proponowane rozwiązanie: Virtual Topics bez selektora po stronie brokera, a pomijanie własnych wiadomości (`sender == własny węzeł`) w odbiorniku aplikacji. Węzeł offline dostaje zaległe wiadomości po powrocie (jak dziś), a nowy węzeł nie wymaga zmiany `activemq.xml`.
- Zakres zmian w kodzie (do zatwierdzenia): nazwy w `JmsDestinations`, nadawcy (temat `VirtualTopic.*` zamiast kolejki), odbiorniki `@JmsListener` (kolejki `Consumer.<węzeł>.VirtualTopic.*`), harness `mercury-srv-slave` (`BulkClusterScenario` z dowolną nazwą węzła), `activemq.xml` (jedna reguła `virtualTopic`; zmianę i restart robi autor), `redeliveryPolicy` i DLQ z obserwacji 138.

## Realizacja (2026-11-02)

- `activemq.xml` (`mercury-server/apache-activemq-5.16.4/conf`): siedem `compositeQueue` zastąpiła jedna reguła `virtualTopic name="VirtualTopic.>" prefix="Consumer.*." selectorAware="false"`. Kopia: `activemq.xml.bak-082-20261102`. Szablony w `mercury-cmd` i `mercury-docker` (`1_activemq.xml`) nie zmienione (tylko na prośbę autora).
- `mercury-srv`: `JmsDestinations` (tematy `VirtualTopic.mrc-*`, kolejki odbiorców `Consumer.<węzeł>.VirtualTopic.mrc-*`, `consumerQueue(...)`), szablony `jmsTopicTemplate` i `jmsTopicTemplateWithExpiration`, nadawcy publikują na tematach, wysyłka do jednego węzła na kolejkę odbiorcy, odbiorniki heartbeat, pobudzeń i paczek indeksu pomijają własne wiadomości (bez ostrzeżeń).
- Obserwacja 138: `LuceneCaseSaveBuffersForIndexConsumer` po 5 doręczeniach (`JMSXDeliveryCount`) przenosi paczkę do `ActiveMQ.DLQ` (kopia z `dlqDeliveryFailureCause` i `originalDestination`) i ją potwierdza.
- Testy: `JmsDestinationsTest` (4). Testu routingu na wbudowanym brokerze nie ma w `mercury-srv`, bo `activemq-broker` 5.16.2 nie ma w lokalnym `.m2` (eksperymenty w `eksperymenty/`).
- Test na żywo (autor zrestartował ActiveMQ i wdrożył WAR): kolejki `Consumer.node1.*` powstały, heartbeat przechodzi przez własną kolejkę i jest pomijany. `BulkClusterScenario` jako **`node3`** (nie ma go w dawnej konfiguracji): 5000 wpisów hurtowych, zmiana bieżąca z węzła 1 w indeksie węzła `node3` po 473, 477 i 1381 ms, bufor hurtowy opróżniony w 9 s.

### Uwagi eksploatacyjne

- Kolejki `Consumer.<węzeł>.*` zostają po wyłączeniu węzła; kolejka paczek indeksu (`mrc-lucene-document-registry-changes`) nie wygasa, więc dla węzła wycofanego na stałe trzeba ją usunąć (Jolokia/konsola), inaczej będzie rosła.
- Stare kolejki `…-node1`/`…-node2` z poprzedniej konfiguracji zostały w bazie brokera jako nieużywane.
