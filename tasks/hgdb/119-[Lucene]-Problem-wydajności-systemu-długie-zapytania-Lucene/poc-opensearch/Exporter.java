import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Semaphore;
import java.util.concurrent.atomic.AtomicLong;

import org.apache.lucene.index.DirectoryReader;
import org.apache.lucene.index.LeafReader;
import org.apache.lucene.index.LeafReaderContext;
import org.apache.lucene.index.PostingsEnum;
import org.apache.lucene.index.SortedDocValues;
import org.apache.lucene.index.SortedNumericDocValues;
import org.apache.lucene.index.Terms;
import org.apache.lucene.index.TermsEnum;
import org.apache.lucene.search.DocIdSetIterator;
import org.apache.lucene.store.MMapDirectory;
import org.apache.lucene.util.BytesRef;
import org.apache.lucene.util.NumericUtils;

/**
 * Eksport PoC (zadanie 119, W9): indeks INEA 3.0 (tylko do odczytu) do OpenSearch. Kategorie (typ, status, miasto, status
 * dziecka) z indeksu odwróconego, liczby i daty z DocValues, identyfikatory dzieci adresu z DocValues pola
 * appMobileDetails_mrc_Case_id. Etap A: typy slmaddress (z zagnieżdżonymi dziećmi), fsmserviceorder. Etap B: pozostałe
 * dokumenty jako płaskie rekordy (typ, status, data, cena).
 *
 * Użycie: java Exporter <indeks> <url> <A|B> [maks. dokumentów]
 */
public class Exporter {

	static final String F_TYPE = "mrc_typeCodeValue";
	static final String F_STATUS = "mrc_status";
	static final String F_DATE = "mrc_createDate";
	static final String F_ID = "mrc_Case_id";
	static final String F_CITY = "city_S";
	static final String F_PRICE = "price_N";
	static final String F_CHILD_STATUS = "status_S";
	static final String F_CHILD_IDS = "appMobileDetails_mrc_Case_id";

	static String esc(String s) {
		StringBuilder sb = new StringBuilder(s.length() + 2);
		sb.append('"');
		for (int i = 0; i < s.length(); i++) {
			char c = s.charAt(i);
			if (c == '"' || c == '\\') {
				sb.append('\\').append(c);
			} else if (c < 0x20) {
				sb.append(String.format("\\u%04x", (int) c));
			} else {
				sb.append(c);
			}
		}
		return sb.append('"').toString();
	}

	/** wartość pola z indeksu odwróconego dla każdego dokumentu segmentu (term pierwszy napotkany) */
	static String[] postingsValues(LeafReader lr, String field, String preferPrefix, String[] unused) throws Exception {
		String[] out = new String[lr.maxDoc()];
		Terms terms = lr.terms(field);
		if (terms == null) {
			return out;
		}
		TermsEnum te = terms.iterator();
		BytesRef term;
		while ((term = te.next()) != null) {
			String v = term.utf8ToString();
			PostingsEnum pe = te.postings(null, PostingsEnum.NONE);
			int d;
			while ((d = pe.nextDoc()) != DocIdSetIterator.NO_MORE_DOCS) {
				/* pole wielowartościowe: preferuję term z podanym prefiksem (kod słownikowy), inaczej pierwszy */
				if (out[d] == null || (preferPrefix != null && v.startsWith(preferPrefix) && !out[d].startsWith(preferPrefix))) {
					out[d] = v;
				}
			}
		}
		return out;
	}

	static class Sender {
		final String url;
		final ExecutorService pool;
		final Semaphore inflight;
		final AtomicLong sent = new AtomicLong();
		final AtomicLong errors = new AtomicLong();

		Sender(String url, int threads) {
			this.url = url;
			this.pool = Executors.newFixedThreadPool(threads);
			this.inflight = new Semaphore(threads * 2);
		}

		void send(final String body, final int docs) throws Exception {
			inflight.acquire();
			pool.submit(() -> {
				try {
					HttpURLConnection c = (HttpURLConnection) new URL(url + "/_bulk").openConnection();
					c.setRequestMethod("POST");
					c.setDoOutput(true);
					c.setRequestProperty("Content-Type", "application/x-ndjson");
					c.setConnectTimeout(30000);
					c.setReadTimeout(300000);
					try (OutputStream os = c.getOutputStream()) {
						os.write(body.getBytes(StandardCharsets.UTF_8));
					}
					int code = c.getResponseCode();
					java.io.InputStream is = code >= 400 ? c.getErrorStream() : c.getInputStream();
					byte[] resp = new byte[8192];
					int n = is.read(resp);
					String head = n > 0 ? new String(resp, 0, Math.min(n, 400), StandardCharsets.UTF_8) : "";
					byte[] rest = new byte[65536];
					while (is.read(rest) > 0) {
						/* odczytuję do końca */
					}
					if (code >= 300 || head.contains("\"errors\":true")) {
						errors.incrementAndGet();
						System.err.println("BŁĄD bulk: " + code + " " + head);
					}
					sent.addAndGet(docs);
				} catch (Exception e) {
					errors.incrementAndGet();
					System.err.println("BŁĄD bulk: " + e);
				} finally {
					inflight.release();
				}
			});
		}

		void finish() throws Exception {
			pool.shutdown();
			pool.awaitTermination(1, java.util.concurrent.TimeUnit.HOURS);
		}
	}

	public static void main(String[] args) throws Exception {
		String dir = args[0];
		String url = args[1];
		String stage = args[2];
		long max = args.length > 3 ? Long.parseLong(args[3]) : Long.MAX_VALUE;
		Sender sender = new Sender(url, 4);
		long t0 = System.currentTimeMillis();
		try (DirectoryReader reader = DirectoryReader.open(MMapDirectory.open(Paths.get(dir)))) {
			List<LeafReaderContext> leaves = reader.leaves();
			System.out.println("dokumentów: " + reader.maxDoc() + ", segmentów: " + leaves.size());

			/* etap A, przebieg 1: dzieci (slmappmobiledetails): id -> {status, mrc_status} */
			Map<String, String[]> children = new HashMap<>();
			if (stage.equals("A")) {
				for (LeafReaderContext ctx : leaves) {
					LeafReader lr = ctx.reader();
					String[] type = postingsValues(lr, F_TYPE, null, null);
					String[] mst = postingsValues(lr, F_STATUS, null, null);
					String[] cst = postingsValues(lr, F_CHILD_STATUS, "slmapp", null);
					SortedDocValues id = lr.getSortedDocValues(F_ID);
					for (int d = 0; d < lr.maxDoc(); d++) {
						if ("slmappmobiledetails".equals(type[d]) && id != null && id.advanceExact(d)) {
							children.put(id.binaryValue().utf8ToString(), new String[] { cst[d], mst[d] });
						}
					}
				}
				System.out.println("dzieci slmappmobiledetails: " + children.size() + " ("
						+ (System.currentTimeMillis() - t0) / 1000 + " s)");
			}

			long exported = 0;
			StringBuilder batch = new StringBuilder();
			int inBatch = 0;
			for (LeafReaderContext ctx : leaves) {
				LeafReader lr = ctx.reader();
				String[] type = postingsValues(lr, F_TYPE, null, null);
				String[] mst = postingsValues(lr, F_STATUS, null, null);
				String[] city = stage.equals("A") ? postingsValues(lr, F_CITY, null, null) : null;
				SortedDocValuesHolder idH = new SortedDocValuesHolder(lr.getSortedDocValues(F_ID));
				SortedNumericDocValues date = lr.getSortedNumericDocValues(F_DATE);
				SortedNumericDocValues price = lr.getSortedNumericDocValues(F_PRICE);
				SortedNumericDocValues kids = lr.getSortedNumericDocValues(F_CHILD_IDS);
				for (int d = 0; d < lr.maxDoc() && exported < max; d++) {
					String t = type[d];
					if (t == null) {
						continue;
					}
					boolean primary = t.equals("slmaddress") || t.equals("fsmserviceorder");
					if (stage.equals("A") ? !primary : (primary || t.equals("slmappmobiledetails"))) {
						continue;
					}
					StringBuilder doc = new StringBuilder(160);
					doc.append("{\"type\":").append(esc(t));
					if (mst[d] != null) {
						doc.append(",\"status\":").append(esc(mst[d]));
					}
					if (date != null && date.advanceExact(d) && date.docValueCount() > 0) {
						doc.append(",\"createDate\":").append(date.nextValue());
					}
					if (price != null && price.advanceExact(d) && price.docValueCount() > 0) {
						doc.append(",\"price\":").append(NumericUtils.sortableLongToDouble(price.nextValue()));
					}
					String id = idH.get(d);
					if (stage.equals("A")) {
						if (id != null) {
							doc.append(",\"caseId\":").append(esc(id));
						}
						if (city[d] != null) {
							doc.append(",\"city\":").append(esc(city[d]));
						}
						if (t.equals("slmaddress") && kids != null && kids.advanceExact(d)) {
							int n = kids.docValueCount();
							doc.append(",\"appMobile\":[");
							boolean first = true;
							for (int i = 0; i < n; i++) {
								String[] ch = children.get(Long.toString(kids.nextValue()));
								if (ch == null) {
									continue;
								}
								if (!first) {
									doc.append(',');
								}
								first = false;
								doc.append("{\"status\":").append(ch[0] == null ? "null" : esc(ch[0]))
										.append(",\"st\":").append(ch[1] == null ? "null" : esc(ch[1])).append('}');
							}
							doc.append(']');
						}
					}
					doc.append("}\n");
					batch.append("{\"index\":{}}\n").append(doc);
					inBatch++;
					exported++;
					if (inBatch >= 4000) {
						sender.send(batch.toString(), inBatch);
						batch.setLength(0);
						inBatch = 0;
						if (exported % 400000 < 4000) {
							System.out.println("wysłano " + exported + " (" + (System.currentTimeMillis() - t0) / 1000
									+ " s), błędów " + sender.errors.get());
						}
					}
				}
			}
			if (inBatch > 0) {
				sender.send(batch.toString(), inBatch);
			}
			sender.finish();
			System.out.println("KONIEC etap " + stage + ": wyeksportowano " + exported + " dokumentów w "
					+ (System.currentTimeMillis() - t0) / 1000 + " s, błędów " + sender.errors.get());
		}
	}

	/** dostęp do SORTED DocValues w kolejności rosnącej numerów dokumentów */
	static class SortedDocValuesHolder {
		final SortedDocValues dv;

		SortedDocValuesHolder(SortedDocValues dv) {
			this.dv = dv;
		}

		String get(int d) throws Exception {
			if (dv != null && dv.advanceExact(d)) {
				return dv.binaryValue().utf8ToString();
			}
			return null;
		}
	}
}
