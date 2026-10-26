# [39] [Lucene] Optymalizacja dostępu do IndexReader'a

Podczas obserwacji zauważyłem:

"http-nio-8080-exec-64" - Thread t@300:
```text

java.lang.Thread.State: RUNNABLE
at sun.nio.ch.FileChannelImpl.map0(Native Method)
at sun.nio.ch.FileChannelImpl.map(FileChannelImpl.java:930)
- locked <511c7745> (a java.lang.Object)
at org.apache.lucene.store.MMapDirectory.map(MMapDirectory.java:267)
at org.apache.lucene.store.MMapDirectory.openInput(MMapDirectory.java:242)
at org.apache.lucene.store.Directory.openChecksumInput(Directory.java:157)
at org.apache.lucene.codecs.lucene70.Lucene70SegmentInfoFormat.read(Lucene70SegmentInfoFormat.java:91)
at org.apache.lucene.index.SegmentInfos.readCommit(SegmentInfos.java:361)
at org.apache.lucene.index.SegmentInfos.readCommit(SegmentInfos.java:291)
at org.apache.lucene.index.StandardDirectoryReader$1.doBody(StandardDirectoryReader.java:61)
at org.apache.lucene.index.StandardDirectoryReader$1.doBody(StandardDirectoryReader.java:58)
at org.apache.lucene.index.SegmentInfos$FindSegmentsFile.run(SegmentInfos.java:688)
at org.apache.lucene.index.StandardDirectoryReader.open(StandardDirectoryReader.java:81)
at org.apache.lucene.index.DirectoryReader.open(DirectoryReader.java:63)
at pro.ibpm.mercury.lucene.config.LuceneConfig.getIndexReader(LuceneConfig.java:532)
at pro.ibpm.mercury.lucene.MLuceneIndexerSupport.getIndexReader(MLuceneIndexerSupport.java:160)
at pro.ibpm.mercury.lucene.MLuceneIndexerSupport.searchIndex(MLuceneIndexerSupport.java:843)
at pro.ibpm.mercury.lucene.indexers.data.CaseIndexer.searchIndex(CaseIndexer.java:411)
at sun.reflect.GeneratedMethodAccessor291.invoke(Unknown Source)
at sun.reflect.DelegatingMethodAccessorImpl.invoke(DelegatingMethodAccessorImpl.java:43)
at java.lang.reflect.Method.invoke(Method.java:498)
at org.springframework.aop.support.AopUtils.invokeJoinpointUsingReflection(AopUtils.java:343)
at org.springframework.aop.framework.ReflectiveMethodInvocation.invokeJoinpoint(ReflectiveMethodInvocation.java:198)
at org.springframework.aop.framework.ReflectiveMethodInvocation.proceed(ReflectiveMethodInvocation.java:163)
at org.springframework.transaction.interceptor.TransactionInterceptor$$Lambda$306/326071275.proceedWithInvocation(Unknown Source)
at org.springframework.transaction.interceptor.TransactionAspectSupport.invokeWithinTransaction(TransactionAspectSupport.java:294)
at org.springframework.transaction.interceptor.TransactionInterceptor.invoke(TransactionInterceptor.java:98)
at org.springframework.aop.framework.ReflectiveMethodInvocation.proceed(ReflectiveMethodInvocation.java:186)
at org.springframework.aop.framework.JdkDynamicAopProxy.invoke(JdkDynamicAopProxy.java:212)
at com.sun.proxy.$Proxy192.searchIndex(Unknown Source)
at pro.ibpm.mercury.lucene.searchers.data.CaseSearcher.searchIndex(CaseSearcher.java:75)
at sun.reflect.GeneratedMethodAccessor287.invoke(Unknown Source)
at sun.reflect.DelegatingMethodAccessorImpl.invoke(DelegatingMethodAccessorImpl.java:43)
at java.lang.reflect.Method.invoke(Method.java:498)
at org.springframework.aop.support.AopUtils.invokeJoinpointUsingReflection(AopUtils.java:343)
at org.springframework.aop.framework.ReflectiveMethodInvocation.invokeJoinpoint(ReflectiveMethodInvocation.java:198)
at org.springframework.aop.framework.ReflectiveMethodInvocation.proceed(ReflectiveMethodInvocation.java:163)
at org.springframework.transaction.interceptor.TransactionInterceptor$$Lambda$306/326071275.proceedWithInvocation(Unknown Source)
at org.springframework.transaction.interceptor.TransactionAspectSupport.invokeWithinTransaction(TransactionAspectSupport.java:294)
at org.springframework.transaction.interceptor.TransactionInterceptor.invoke(TransactionInterceptor.java:98)
at org.springframework.aop.framework.ReflectiveMethodInvocation.proceed(ReflectiveMethodInvocation.java:186)
at org.springframework.aop.framework.JdkDynamicAopProxy.invoke(JdkDynamicAopProxy.java:212)
at com.sun.proxy.$Proxy193.searchIndex(Unknown Source)
at org.mercury.single.node.logic.data.CaseLogic.searchIndex(CaseLogic.java:659)
at org.mercury.cluster.node.logic.data.CaseLogic.searchIndex(CaseLogic.java:255)
at org.mercury.cluster.node.logic.data.CaseLogic.searchIndex(CaseLogic.java:28)

```

Nie jest dobrze. Już wcześniej próbowałem rozwiązać ten problem, utworzyć pulę połączeń, ale implementacja IndexReader ma final przy metodzie close() i nie można jej nadpisać. Hmmm... pojawił się pomysł by ściągnąć źródła indeksu Lucene, usunąć final, zrobić własną kompilację bibliotek i w końcu zrobić tę pulę połączeń.

## Analiza i propozycja (2026-10-26, w ramach zadania 119)

Kod potwierdza opis: `LuceneConfig.getIndexReader` otwiera nowy `DirectoryReader` przy każdym wywołaniu (99–159 ms na indeksie INEA, zapytanie na wspólnym czytniku 0,3 ms).
Własna kompilacja Lucene nie jest potrzebna: wspólny czytnik z liczeniem referencji i lekki uchwyt `FilterDirectoryReader` per wywołanie (jego `doClose()` zwalnia referencję). Prototyp i pomiary:
`../119-[Lucene]-Problem-wydajności-systemu-długie-zapytania-Lucene/w12-pula-czytnikow/`. Propozycja wpięcia do 119 jako W12: sekcja 11 w `plan-i-decyzje-2026-10-25.md`.
