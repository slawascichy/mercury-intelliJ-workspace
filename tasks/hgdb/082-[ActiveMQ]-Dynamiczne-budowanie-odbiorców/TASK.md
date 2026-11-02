# [82] [ActiveMQ] Dynamiczne budowanie odbiorców

https://github.com/slawascichy/hgdb/issues/82

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