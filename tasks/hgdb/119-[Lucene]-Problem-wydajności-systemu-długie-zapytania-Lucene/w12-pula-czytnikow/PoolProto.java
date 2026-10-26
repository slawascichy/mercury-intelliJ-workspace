import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.List;

import org.apache.lucene.analysis.standard.StandardAnalyzer;
import org.apache.lucene.document.Document;
import org.apache.lucene.document.Field.Store;
import org.apache.lucene.document.StringField;
import org.apache.lucene.index.DirectoryReader;
import org.apache.lucene.index.FilterDirectoryReader;
import org.apache.lucene.index.FilterLeafReader;
import org.apache.lucene.index.IndexReader;
import org.apache.lucene.index.IndexWriter;
import org.apache.lucene.index.IndexWriterConfig;
import org.apache.lucene.index.LeafReader;
import org.apache.lucene.index.Term;
import org.apache.lucene.search.IndexSearcher;
import org.apache.lucene.search.TermQuery;
import org.apache.lucene.store.FSDirectory;

/** Prototyp puli czytników (zadanie 039): wspólny DirectoryReader, per wywołanie lekki wrapper z własnym close(). */
public class PoolProto {

	static class Handle extends FilterDirectoryReader {
		private final DirectoryReader shared;

		Handle(DirectoryReader shared) throws IOException {
			super(shared, new SubReaderWrapper() {
				@Override
				public LeafReader wrap(LeafReader r) {
					return new FilterLeafReader(r) {
						@Override
						public CacheHelper getCoreCacheHelper() {
							return in.getCoreCacheHelper();
						}

						@Override
						public CacheHelper getReaderCacheHelper() {
							return in.getReaderCacheHelper();
						}
					};
				}
			});
			this.shared = shared;
		}

		@Override
		protected DirectoryReader doWrapDirectoryReader(DirectoryReader in) throws IOException {
			return new Handle(in);
		}

		@Override
		public CacheHelper getReaderCacheHelper() {
			return in.getReaderCacheHelper();
		}

		@Override
		protected void doClose() throws IOException {
			shared.decRef(); /* zwolnienie referencji wziętej w acquire, bez zamykania czytnika wspólnego */
		}
	}

	static class Pool {
		final Path path;
		DirectoryReader current;
		long lastCheck;
		long intervalMs = Long.getLong("pool.interval", 0L);

		Pool(Path path) {
			this.path = path;
		}

		synchronized IndexReader acquire() throws IOException {
			if (current == null) {
				current = DirectoryReader.open(FSDirectory.open(path));
			} else if (System.currentTimeMillis() - lastCheck >= intervalMs) {
				lastCheck = System.currentTimeMillis();
				DirectoryReader n = DirectoryReader.openIfChanged(current);
				if (n != null) {
					current.decRef(); /* referencja puli; użytkownicy trzymają własne */
					current = n;
				}
			}
			current.incRef();
			return new Handle(current);
		}

		synchronized void closePool() throws IOException {
			if (current != null) {
				current.decRef();
				current = null;
			}
		}
	}

	static void check(boolean c, String m) {
		if (!c) {
			throw new AssertionError(m);
		}
		System.out.println("ok: " + m);
	}

	public static void main(String[] a) throws Exception {
		/* 1. poprawność na małym indeksie z zapisem w trakcie */
		Path tmp = Files.createTempDirectory("poolproto");
		if (Long.getLong("pool.interval", 0L) == 0L) try (IndexWriter w = new IndexWriter(FSDirectory.open(tmp), new IndexWriterConfig(new StandardAnalyzer()))) {
			add(w, 1);
			w.commit();
			Pool p = new Pool(tmp);
			IndexReader r1 = p.acquire();
			IndexReader r2 = p.acquire();
			check(new IndexSearcher(r1).count(new TermQuery(new Term("t", "x"))) == 1, "r1 widzi 1 dokument");
			add(w, 1);
			w.commit();
			IndexReader r3 = p.acquire();
			check(new IndexSearcher(r3).count(new TermQuery(new Term("t", "x"))) == 2, "nowy acquire widzi zatwierdzoną zmianę");
			check(new IndexSearcher(r1).count(new TermQuery(new Term("t", "x"))) == 1, "stary uchwyt nadal działa (migawka)");
			r1.close();
			r1.close(); /* podwójne close nie może zwolnić cudzej referencji */
			check(new IndexSearcher(r2).count(new TermQuery(new Term("t", "x"))) == 1, "r2 działa po zamknięciu r1");
			r2.close();
			r3.close();
			p.closePool();
			check(true, "zamknięcie puli i uchwytów bez wyjątku");
		}

		/* 2. czas na indeksie INEA: acquire+count+close na wspólnym czytniku, 8 wątków */
		final Pool pool = new Pool(Paths.get(a[0]));
		final int n = Integer.parseInt(a[1]);
		pool.acquire().close();
		long[] t = new long[n];
		for (int i = 0; i < n; i++) {
			long t0 = System.nanoTime();
			try (IndexReader r = pool.acquire()) {
				new IndexSearcher(r).count(new TermQuery(new Term("mrc_typeCodeValue", "fsmserviceorder")));
			}
			t[i] = System.nanoTime() - t0;
		}
		java.util.Arrays.sort(t);
		System.out.printf("pula: acquire+count+close: min %.1f ms, mediana %.1f ms%n", t[0] / 1e6, t[n / 2] / 1e6);
		Thread[] th = new Thread[8];
		final long[] tt = new long[8 * n];
		for (int k = 0; k < 8; k++) {
			final int kk = k;
			th[k] = new Thread(() -> {
				try {
					for (int i = 0; i < n; i++) {
						long t0 = System.nanoTime();
						try (IndexReader r = pool.acquire()) {
							new IndexSearcher(r).count(new TermQuery(new Term("mrc_typeCodeValue", "fsmserviceorder")));
						}
						tt[kk * n + i] = System.nanoTime() - t0;
					}
				} catch (Exception e) {
					e.printStackTrace();
				}
			});
			th[k].start();
		}
		for (Thread x : th) {
			x.join();
		}
		java.util.Arrays.sort(tt);
		System.out.printf("pula, 8 wątków: mediana %.1f ms, p95 %.1f ms%n", tt[tt.length / 2] / 1e6, tt[(int) (tt.length * 0.95)] / 1e6);
		pool.closePool();
	}

	static void add(IndexWriter w, int k) throws IOException {
		for (int i = 0; i < k; i++) {
			Document d = new Document();
			d.add(new StringField("t", "x", Store.NO));
			w.addDocument(d);
		}
	}
}
