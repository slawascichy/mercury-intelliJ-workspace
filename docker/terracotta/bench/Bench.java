import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.InputStream;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.util.Arrays;
import org.ehcache.Cache;
import org.ehcache.CacheManager;
import org.ehcache.PersistentCacheManager;
import org.ehcache.config.builders.CacheManagerBuilder;
import org.ehcache.xml.XmlConfiguration;

/**
 * Mikrotest opoznienia Terracotty: dwoch klientow w jednym procesie, wpisy 2, 5, 16 i 56 KB (typowe rozmiary
 * obiektow Mercury), zapis przez klienta A i odczyt przez klienta B z pominieciem lokalnej warstwy heap.
 * Adres serwera: -Dtc.url=terracotta://host:9510/default-server. Pamiec testowa jest usuwana z serwera na koncu.
 */
public class Bench {
	public static void main(String[] args) throws Exception {
		String url = System.getProperty("tc.url");
		if (url == null) {
			System.err.println("Ustaw -Dtc.url=terracotta://host:9510/default-server");
			System.exit(2);
		}
		String xml;
		try (InputStream in = Bench.class.getResourceAsStream("/bench.xml")) {
			xml = new String(readAll(in), StandardCharsets.UTF_8).replace("@TC_URL@", url);
		}
		File file = File.createTempFile("bench", ".xml");
		file.deleteOnExit();
		Files.write(file.toPath(), xml.getBytes(StandardCharsets.UTF_8));
		URL config = file.toURI().toURL();
		CacheManager a = CacheManagerBuilder.newCacheManager(new XmlConfiguration(config));
		CacheManager b = CacheManagerBuilder.newCacheManager(new XmlConfiguration(config));
		a.init();
		b.init();
		Cache<String, String> ca = a.getCache("bench-latency", String.class, String.class);
		Cache<String, String> cb = b.getCache("bench-latency", String.class, String.class);
		try {
			System.out.println("Serwer: " + url);
			for (int size : new int[] { 2048, 5000, 16000, 56000 }) {
				char[] chars = new char[size];
				Arrays.fill(chars, 'x');
				String value = new String(chars);
				int n = size > 20000 ? 100 : 200;
				for (int i = 0; i < 20; i++) {
					ca.put("warm" + i, value);
					cb.get("warm" + i);
				}
				long[] put = new long[n];
				long[] get = new long[n];
				for (int i = 0; i < n; i++) {
					long t0 = System.nanoTime();
					ca.put("k" + size + "_" + i, value);
					put[i] = System.nanoTime() - t0;
				}
				for (int i = 0; i < n; i++) {
					long t0 = System.nanoTime();
					cb.get("k" + size + "_" + i);
					get[i] = System.nanoTime() - t0;
				}
				Arrays.sort(put);
				Arrays.sort(get);
				System.out.println(String.format(
						"BENCH size=%dB n=%d zapis p50=%.2fms p90=%.2fms | odczyt (inny klient) p50=%.2fms p90=%.2fms max=%.2fms",
						size, n, put[n / 2] / 1e6, put[(int) (n * 0.9)] / 1e6, get[n / 2] / 1e6, get[(int) (n * 0.9)] / 1e6,
						get[n - 1] / 1e6));
			}
		} finally {
			b.close();
			try {
				((PersistentCacheManager) a).destroyCache("bench-latency");
			} catch (Throwable t) {
				System.out.println("Nie usunieto pamieci testowej: " + t);
			}
			a.close();
		}
	}

	private static byte[] readAll(InputStream in) throws Exception {
		ByteArrayOutputStream out = new ByteArrayOutputStream();
		byte[] buffer = new byte[4096];
		int read;
		while ((read = in.read(buffer)) > 0) {
			out.write(buffer, 0, read);
		}
		return out.toByteArray();
	}
}
