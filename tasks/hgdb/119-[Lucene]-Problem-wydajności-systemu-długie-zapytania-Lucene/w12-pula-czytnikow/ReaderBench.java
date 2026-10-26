import java.nio.file.Paths;

import org.apache.lucene.index.DirectoryReader;
import org.apache.lucene.index.IndexReader;
import org.apache.lucene.index.Term;
import org.apache.lucene.search.IndexSearcher;
import org.apache.lucene.search.TermQuery;
import org.apache.lucene.store.FSDirectory;

/** Koszt otwarcia DirectoryReader na każde żądanie (zadanie 039) wobec ponownego użycia jednego czytnika. */
public class ReaderBench {
	public static void main(String[] a) throws Exception {
		String dir = a[0];
		int n = Integer.parseInt(a[1]);
		long[] t = new long[n];
		for (int i = 0; i < n; i++) {
			long t0 = System.nanoTime();
			try (IndexReader r = DirectoryReader.open(FSDirectory.open(Paths.get(dir)))) {
				t[i] = System.nanoTime() - t0;
			}
		}
		java.util.Arrays.sort(t);
		System.out.printf("open+close: min %.1f ms, mediana %.1f ms, max %.1f ms (n=%d)%n", t[0] / 1e6, t[n / 2] / 1e6,
				t[n - 1] / 1e6, n);

		/* otwarcie + pierwsze zapytanie (liczenie trafień typu) na świeżym czytniku */
		long[] q = new long[n];
		for (int i = 0; i < n; i++) {
			long t0 = System.nanoTime();
			try (IndexReader r = DirectoryReader.open(FSDirectory.open(Paths.get(dir)))) {
				new IndexSearcher(r).count(new TermQuery(new Term("mrc_typeCodeValue", "fsmserviceorder")));
				q[i] = System.nanoTime() - t0;
			}
		}
		java.util.Arrays.sort(q);
		System.out.printf("open+count+close (świeży czytnik): min %.1f ms, mediana %.1f ms%n", q[0] / 1e6, q[n / 2] / 1e6);

		try (IndexReader shared = DirectoryReader.open(FSDirectory.open(Paths.get(dir)))) {
			long[] s = new long[n];
			for (int i = 0; i < n; i++) {
				long t0 = System.nanoTime();
				new IndexSearcher(shared).count(new TermQuery(new Term("mrc_typeCodeValue", "fsmserviceorder")));
				s[i] = System.nanoTime() - t0;
			}
			java.util.Arrays.sort(s);
			System.out.printf("count na wspólnym czytniku: min %.1f ms, mediana %.1f ms%n", s[0] / 1e6, s[n / 2] / 1e6);
			long[] c = new long[n];
			for (int i = 0; i < n; i++) {
				long t0 = System.nanoTime();
				DirectoryReader nr = DirectoryReader.openIfChanged((DirectoryReader) shared);
				c[i] = System.nanoTime() - t0;
				if (nr != null) {
					nr.close();
				}
			}
			java.util.Arrays.sort(c);
			System.out.printf("openIfChanged (bez zmian): min %.2f ms, mediana %.2f ms%n", c[0] / 1e6, c[n / 2] / 1e6);
		}
	}
}
