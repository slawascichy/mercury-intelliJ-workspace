import java.util.ArrayList;
import java.util.List;

import javax.jms.Connection;
import javax.jms.Destination;
import javax.jms.Message;
import javax.jms.MessageConsumer;
import javax.jms.MessageProducer;
import javax.jms.Session;
import javax.jms.TextMessage;

import org.apache.activemq.ActiveMQConnectionFactory;
import org.apache.activemq.broker.BrokerService;
import org.apache.activemq.broker.region.DestinationInterceptor;
import org.apache.activemq.broker.region.virtual.CompositeQueue;
import org.apache.activemq.broker.region.virtual.FilteredDestination;
import org.apache.activemq.broker.region.virtual.VirtualDestination;
import org.apache.activemq.broker.region.virtual.VirtualDestinationInterceptor;
import org.apache.activemq.broker.region.virtual.VirtualTopic;
import org.apache.activemq.command.ActiveMQQueue;

/**
 * Zadanie 082: eksperymenty z dynamicznym budowaniem odbiorców na wbudowanym brokerze (ActiveMQ 5.16.4, bez zapisu
 * na dysk, tylko vm://). Nie dotyka działającego brokera.
 */
public class Exp082 {

	static BrokerService broker(String name, VirtualDestination... destinations) throws Exception {
		BrokerService b = new BrokerService();
		b.setBrokerName(name);
		b.setPersistent(false);
		b.setUseJmx(false);
		b.setUseShutdownHook(false);
		VirtualDestinationInterceptor vdi = new VirtualDestinationInterceptor();
		vdi.setVirtualDestinations(destinations);
		b.setDestinationInterceptors(new DestinationInterceptor[] { vdi });
		b.start();
		b.waitUntilStarted();
		return b;
	}

	static String receive(Session s, String queue, String selector, long timeout) throws Exception {
		MessageConsumer c = selector == null ? s.createConsumer(s.createQueue(queue))
				: s.createConsumer(s.createQueue(queue), selector);
		Message m = c.receive(timeout);
		c.close();
		return m == null ? null : ((TextMessage) m).getText();
	}

	static void send(Session s, Destination d, String text, String sender) throws Exception {
		MessageProducer p = s.createProducer(d);
		TextMessage m = s.createTextMessage(text);
		if (sender != null) {
			m.setStringProperty("sender", sender);
		}
		p.send(m);
		p.close();
	}

	static void line(String s) {
		System.out.println("EXP|" + s);
	}

	public static void main(String[] args) throws Exception {
		/* E1: compositeQueue z wildcardem w forwardTo */
		CompositeQueue cq = new CompositeQueue();
		cq.setName("reg.changes");
		List<Object> fwd = new ArrayList<>();
		fwd.add(new ActiveMQQueue("reg.changes.>"));
		cq.setForwardTo(fwd);
		BrokerService b1 = broker("e1", cq);
		Connection c1 = new ActiveMQConnectionFactory("vm://e1?create=false").createConnection();
		c1.start();
		Session s1 = c1.createSession(false, Session.AUTO_ACKNOWLEDGE);
		try {
			/* węzły istnieją (kolejki utworzone przez konsumentów) */
			s1.createConsumer(s1.createQueue("reg.changes.node1")).close();
			s1.createConsumer(s1.createQueue("reg.changes.node2")).close();
			send(s1, s1.createQueue("reg.changes"), "hello", null);
			line("E1 wildcard forwardTo: node1=" + receive(s1, "reg.changes.node1", null, 1500) + " node2="
					+ receive(s1, "reg.changes.node2", null, 1500));
		} catch (Exception e) {
			line("E1 wildcard forwardTo: wyjątek " + e);
		}
		c1.close();
		b1.stop();

		/* E2: Virtual Topic, odbiorcy dynamiczni (node3 dochodzi bez zmiany konfiguracji brokera) */
		for (boolean selectorAware : new boolean[] { false, true }) {
			VirtualTopic vt = new VirtualTopic();
			vt.setName(">");
			vt.setPrefix("Consumer.*.");
			vt.setSelectorAware(selectorAware);
			BrokerService b2 = broker("e2" + selectorAware, vt);
			Connection c2 = new ActiveMQConnectionFactory("vm://e2" + selectorAware + "?create=false").createConnection();
			c2.start();
			Session s2 = c2.createSession(false, Session.AUTO_ACKNOWLEDGE);
			String topic = "VirtualTopic.reg.changes";
			String q1 = "Consumer.node1." + topic, q2 = "Consumer.node2." + topic, q3 = "Consumer.node3." + topic;
			/* konsumenci z selektorem „nie moje”: nadawca <> węzeł */
			MessageConsumer k1 = s2.createConsumer(s2.createQueue(q1), "sender <> 'node1'");
			MessageConsumer k2 = s2.createConsumer(s2.createQueue(q2), "sender <> 'node2'");
			MessageConsumer k3 = s2.createConsumer(s2.createQueue(q3), "sender <> 'node3'");
			send(s2, s2.createTopic(topic), "from-node1", "node1");
			Message m1 = k1.receive(800), m2 = k2.receive(1500), m3 = k3.receive(1500);
			long backlog1 = b2.getDestination(new ActiveMQQueue(q1)).getDestinationStatistics().getMessages()
					.getCount();
			line("E2 VirtualTopic selectorAware=" + selectorAware + ": node1(nadawca)="
					+ (m1 == null ? null : "dostał") + " node2=" + (m2 == null ? null : "dostał") + " node3(dynamiczny)="
					+ (m3 == null ? null : "dostał") + " zaległość w kolejce node1=" + backlog1);
			c2.close();
			b2.stop();
		}

		/* E3: compositeQueue z filteredDestination (stan dzisiejszy) dla porównania */
		CompositeQueue fq = new CompositeQueue();
		fq.setName("reg.filtered");
		List<Object> f = new ArrayList<>();
		for (String n : new String[] { "node1", "node2" }) {
			FilteredDestination fd = new FilteredDestination();
			fd.setSelector("sender <> '" + n + "'");
			fd.setQueue("reg.filtered." + n);
			f.add(fd);
		}
		fq.setForwardTo(f);
		BrokerService b3 = broker("e3", fq);
		Connection c3 = new ActiveMQConnectionFactory("vm://e3?create=false").createConnection();
		c3.start();
		Session s3 = c3.createSession(false, Session.AUTO_ACKNOWLEDGE);
		send(s3, s3.createQueue("reg.filtered"), "from-node1", "node1");
		line("E3 filteredDestination (dziś): node1=" + receive(s3, "reg.filtered.node1", null, 1000) + " node2="
				+ receive(s3, "reg.filtered.node2", null, 1500) + " node3(nieskonfigurowany)="
				+ receive(s3, "reg.filtered.node3", null, 800));
		c3.close();
		b3.stop();
		System.exit(0);
	}
}
