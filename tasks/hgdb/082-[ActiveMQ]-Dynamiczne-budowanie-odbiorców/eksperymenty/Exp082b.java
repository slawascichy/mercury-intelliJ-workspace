import javax.jms.*;
import org.apache.activemq.ActiveMQConnectionFactory;
import org.apache.activemq.broker.BrokerService;
import org.apache.activemq.broker.region.DestinationInterceptor;
import org.apache.activemq.broker.region.virtual.*;

public class Exp082b {
	public static void main(String[] a) throws Exception {
		for (boolean sa : new boolean[] { false, true }) {
			VirtualTopic vt = new VirtualTopic();
			vt.setName(">");
			vt.setPrefix("Consumer.*.");
			vt.setSelectorAware(sa);
			BrokerService b = new BrokerService();
			b.setBrokerName("x" + sa);
			b.setPersistent(false);
			b.setUseJmx(false);
			VirtualDestinationInterceptor vdi = new VirtualDestinationInterceptor();
			vdi.setVirtualDestinations(new VirtualDestination[] { vt });
			b.setDestinationInterceptors(new DestinationInterceptor[] { vdi });
			b.start();
			Connection c = new ActiveMQConnectionFactory("vm://x" + sa + "?create=false").createConnection();
			c.start();
			Session s = c.createSession(false, Session.AUTO_ACKNOWLEDGE);
			String q = "Consumer.node2.VirtualTopic.t";
			/* węzeł 2 był online (kolejka istnieje), potem się rozłączył */
			s.createConsumer(s.createQueue(q), "sender <> 'node2'").close();
			MessageProducer p = s.createProducer(s.createTopic("VirtualTopic.t"));
			TextMessage m = s.createTextMessage("while-offline");
			m.setStringProperty("sender", "node1");
			p.send(m);
			/* węzeł 2 wraca */
			Message got = s.createConsumer(s.createQueue(q), "sender <> 'node2'").receive(1500);
			System.out.println("EXP|E4 selectorAware=" + sa + ": wiadomość wysłana gdy węzeł offline po powrocie węzła: "
					+ (got == null ? "UTRACONA" : "doręczona"));
			c.close();
			b.stop();
		}
		System.exit(0);
	}
}
