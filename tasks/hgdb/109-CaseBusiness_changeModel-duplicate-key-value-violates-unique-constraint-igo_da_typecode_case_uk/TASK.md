# [109] CaseBusiness_changeModel -> duplicate key value violates unique constraint "igo_da_typecode_case_uk

https://github.com/slawascichy/hgdb/issues/109

Próba zmiany modelu dla spraw posiadających PK kończy się błędem: `duplicate key value violates unique constraint "igo_da_typecode_case_uk"`

	2020-05-04 10:09:50,994 ERROR [WsStatus.java:43] : wsException [node1.35684b51-966f-4297-b3d7-e0e25338b2c8]
	pro.ibpm.mercury.exceptions.InternalErrorException: To jest błąd aplikacji. : ERROR: duplicate key value violates unique constraint "igo_da_typecode_case_uk"
	  Detail: Key (case_id)=(1775866) already exists.
			at pro.ibpm.mercury.ws.server.api.returns.WsStatus.<init>(WsStatus.java:48)
			at pro.ibpm.mercury.ws.server.api.returns.WsStatusWithLongValue.<init>(WsStatusWithLongValue.java:19)
			at pro.ibpm.mercury.ws.server.actions.business.data.CaseBusinessAction.changeModel(CaseBusinessAction.java:1742)
			at sun.reflect.GeneratedMethodAccessor2792.invoke(Unknown Source)
			at sun.reflect.DelegatingMethodAccessorImpl.invoke(DelegatingMethodAccessorImpl.java:43)
			at java.lang.reflect.Method.invoke(Method.java:498)
			at org.springframework.aop.support.AopUtils.invokeJoinpointUsingReflection(AopUtils.java:343)
			at org.springframework.aop.framework.ReflectiveMethodInvocation.invokeJoinpoint(ReflectiveMethodInvocation.java:198)
			at org.springframework.aop.framework.ReflectiveMethodInvocation.proceed(ReflectiveMethodInvocation.java:163)
			at org.springframework.remoting.support.RemoteInvocationTraceInterceptor.invoke(RemoteInvocationTraceInterceptor.java:78)
			at org.springframework.aop.framework.ReflectiveMethodInvocation.proceed(ReflectiveMethodInvocation.java:186)
			at org.springframework.aop.framework.JdkDynamicAopProxy.invoke(JdkDynamicAopProxy.java:212)
			at com.sun.proxy.$Proxy352.changeModel(Unknown Source)
			at sun.reflect.NativeMethodAccessorImpl.invoke0(Native Method)
			at sun.reflect.NativeMethodAccessorImpl.invoke(NativeMethodAccessorImpl.java:62)
			at sun.reflect.DelegatingMethodAccessorImpl.invoke(DelegatingMethodAccessorImpl.java:43)
			at java.lang.reflect.Method.invoke(Method.java:498)
			at org.springframework.remoting.support.RemoteInvocation.invoke(RemoteInvocation.java:215)
			at org.springframework.remoting.support.DefaultRemoteInvocationExecutor.invoke(DefaultRemoteInvocationExecutor.java:39)
			at org.springframework.remoting.support.RemoteInvocationBasedExporter.invoke(RemoteInvocationBasedExporter.java:78)
			at org.springframework.remoting.support.RemoteInvocationBasedExporter.invokeAndCreateResult(RemoteInvocationBasedExporter.java:114)
			at org.springframework.remoting.httpinvoker.HttpInvokerServiceExporter.handleRequest(HttpInvokerServiceExporter.java:76)
			at org.springframework.web.servlet.mvc.HttpRequestHandlerAdapter.handle(HttpRequestHandlerAdapter.java:53)
			at org.springframework.web.servlet.DispatcherServlet.doDispatch(DispatcherServlet.java:1038)
			at org.springframework.web.servlet.DispatcherServlet.doService(DispatcherServlet.java:942)
			at org.springframework.web.servlet.FrameworkServlet.processRequest(FrameworkServlet.java:998)
			at org.springframework.web.servlet.FrameworkServlet.doPost(FrameworkServlet.java:901)
			at javax.servlet.http.HttpServlet.service(HttpServlet.java:661)
			at org.springframework.web.servlet.FrameworkServlet.service(FrameworkServlet.java:875)
			at javax.servlet.http.HttpServlet.service(HttpServlet.java:742)
			at org.apache.catalina.core.ApplicationFilterChain.internalDoFilter(ApplicationFilterChain.java:231)
			at org.apache.catalina.core.ApplicationFilterChain.doFilter(ApplicationFilterChain.java:166)
			at org.apache.tomcat.websocket.server.WsFilter.doFilter(WsFilter.java:52)
			at org.apache.catalina.core.ApplicationFilterChain.internalDoFilter(ApplicationFilterChain.java:193)
			at org.apache.catalina.core.ApplicationFilterChain.doFilter(ApplicationFilterChain.java:166)
			at org.apache.catalina.filters.CorsFilter.handleNonCORS(CorsFilter.java:364)
			at org.apache.catalina.filters.CorsFilter.doFilter(CorsFilter.java:170)
			at org.apache.catalina.core.ApplicationFilterChain.internalDoFilter(ApplicationFilterChain.java:193)
			at org.apache.catalina.core.ApplicationFilterChain.doFilter(ApplicationFilterChain.java:166)
			at org.mercury.cxf.server.security.RemoteBasicAuthFilter.doFilter(RemoteBasicAuthFilter.java:69)
			at org.apache.catalina.core.ApplicationFilterChain.internalDoFilter(ApplicationFilterChain.java:193)
			at org.apache.catalina.core.ApplicationFilterChain.doFilter(ApplicationFilterChain.java:166)
			at org.apache.catalina.core.StandardWrapperValve.invoke(StandardWrapperValve.java:198)
			at org.apache.catalina.core.StandardContextValve.invoke(StandardContextValve.java:96)
			at org.apache.catalina.authenticator.AuthenticatorBase.invoke(AuthenticatorBase.java:493)
			at org.apache.catalina.core.StandardHostValve.invoke(StandardHostValve.java:140)
			at org.apache.catalina.valves.ErrorReportValve.invoke(ErrorReportValve.java:81)
			at org.apache.catalina.valves.AbstractAccessLogValve.invoke(AbstractAccessLogValve.java:650)
			at org.apache.catalina.core.StandardEngineValve.invoke(StandardEngineValve.java:87)
			at org.apache.catalina.connector.CoyoteAdapter.service(CoyoteAdapter.java:342)
			at org.apache.coyote.http11.Http11Processor.service(Http11Processor.java:800)
			at org.apache.coyote.AbstractProcessorLight.process(AbstractProcessorLight.java:66)
			at org.apache.coyote.AbstractProtocol$ConnectionHandler.process(AbstractProtocol.java:806)
			at org.apache.tomcat.util.net.NioEndpoint$SocketProcessor.doRun(NioEndpoint.java:1498)
			at org.apache.tomcat.util.net.SocketProcessorBase.run(SocketProcessorBase.java:49)
			at java.util.concurrent.ThreadPoolExecutor.runWorker(ThreadPoolExecutor.java:1149)
			at java.util.concurrent.ThreadPoolExecutor$Worker.run(ThreadPoolExecutor.java:624)
			at org.apache.tomcat.util.threads.TaskThread$WrappingRunnable.run(TaskThread.java:61)
			at java.lang.Thread.run(Thread.java:748)
	Caused by: javax.persistence.PersistenceException: org.hibernate.exception.ConstraintViolationException: could not execute statement
			at org.hibernate.internal.ExceptionConverterImpl.convert(ExceptionConverterImpl.java:154)
			at org.hibernate.internal.ExceptionConverterImpl.convert(ExceptionConverterImpl.java:181)
			at org.hibernate.query.internal.AbstractProducedQuery.executeUpdate(AbstractProducedQuery.java:1604)
			at pro.ibpm.mercury.dao.data.CaseDAO.updatePK(CaseDAO.java:1308)
			at pro.ibpm.mercury.dao.data.CaseDAO.changeModel(CaseDAO.java:1164)
			at org.mercury.single.node.logic.data.CaseLogic.changeModel(CaseLogic.java:1356)
			at sun.reflect.GeneratedMethodAccessor2794.invoke(Unknown Source)
			at sun.reflect.DelegatingMethodAccessorImpl.invoke(DelegatingMethodAccessorImpl.java:43)
			at java.lang.reflect.Method.invoke(Method.java:498)
			at org.springframework.aop.support.AopUtils.invokeJoinpointUsingReflection(AopUtils.java:343)
			at org.springframework.aop.framework.ReflectiveMethodInvocation.invokeJoinpoint(ReflectiveMethodInvocation.java:198)
			at org.springframework.aop.framework.ReflectiveMethodInvocation.proceed(ReflectiveMethodInvocation.java:163)
			at org.springframework.transaction.interceptor.TransactionAspectSupport.invokeWithinTransaction(TransactionAspectSupport.java:294)
			at org.springframework.transaction.interceptor.TransactionInterceptor.invoke(TransactionInterceptor.java:98)
			at org.springframework.aop.framework.ReflectiveMethodInvocation.proceed(ReflectiveMethodInvocation.java:186)
			at org.springframework.aop.framework.JdkDynamicAopProxy.invoke(JdkDynamicAopProxy.java:212)
			at com.sun.proxy.$Proxy124.changeModel(Unknown Source)
			at org.mercury.single.node.business.data.CaseBusiness.changeModel(CaseBusiness.java:606)
			at sun.reflect.GeneratedMethodAccessor2793.invoke(Unknown Source)
			at sun.reflect.DelegatingMethodAccessorImpl.invoke(DelegatingMethodAccessorImpl.java:43)
			at java.lang.reflect.Method.invoke(Method.java:498)
			at org.springframework.aop.support.AopUtils.invokeJoinpointUsingReflection(AopUtils.java:343)
			at org.springframework.aop.framework.ReflectiveMethodInvocation.invokeJoinpoint(ReflectiveMethodInvocation.java:198)
			at org.springframework.aop.framework.ReflectiveMethodInvocation.proceed(ReflectiveMethodInvocation.java:163)
			at org.springframework.transaction.interceptor.TransactionAspectSupport.invokeWithinTransaction(TransactionAspectSupport.java:294)
			at org.springframework.transaction.interceptor.TransactionInterceptor.invoke(TransactionInterceptor.java:98)
			at org.springframework.aop.framework.ReflectiveMethodInvocation.proceed(ReflectiveMethodInvocation.java:186)
			at org.springframework.aop.framework.JdkDynamicAopProxy.invoke(JdkDynamicAopProxy.java:212)
			at com.sun.proxy.$Proxy208.changeModel(Unknown Source)
			at pro.ibpm.mercury.ws.server.actions.business.data.CaseBusinessAction.changeModel(CaseBusinessAction.java:1739)
			... 56 more
	Caused by: org.hibernate.exception.ConstraintViolationException: could not execute statement
			at org.hibernate.exception.internal.SQLStateConversionDelegate.convert(SQLStateConversionDelegate.java:112)
			at org.hibernate.exception.internal.StandardSQLExceptionConverter.convert(StandardSQLExceptionConverter.java:42)
			at org.hibernate.engine.jdbc.spi.SqlExceptionHelper.convert(SqlExceptionHelper.java:113)
			at org.hibernate.engine.jdbc.spi.SqlExceptionHelper.convert(SqlExceptionHelper.java:99)
			at org.hibernate.engine.jdbc.internal.ResultSetReturnImpl.executeUpdate(ResultSetReturnImpl.java:178)
			at org.hibernate.engine.query.spi.NativeSQLQueryPlan.performExecuteUpdate(NativeSQLQueryPlan.java:107)
			at org.hibernate.internal.SessionImpl.executeNativeUpdate(SessionImpl.java:1593)
			at org.hibernate.query.internal.NativeQueryImpl.doExecuteUpdate(NativeQueryImpl.java:292)
			at org.hibernate.query.internal.AbstractProducedQuery.executeUpdate(AbstractProducedQuery.java:1594)
			... 83 more
	Caused by: org.postgresql.util.PSQLException: ERROR: duplicate key value violates unique constraint "igo_da_typecode_case_uk"
	  Detail: Key (case_id)=(1775866) already exists.
			at org.postgresql.core.v3.QueryExecutorImpl.receiveErrorResponse(QueryExecutorImpl.java:2477)
			at org.postgresql.core.v3.QueryExecutorImpl.processResults(QueryExecutorImpl.java:2190)
			at org.postgresql.core.v3.QueryExecutorImpl.execute(QueryExecutorImpl.java:300)
			at org.postgresql.jdbc.PgStatement.executeInternal(PgStatement.java:428)
			at org.postgresql.jdbc.PgStatement.execute(PgStatement.java:354)
			at org.postgresql.jdbc.PgPreparedStatement.executeWithFlags(PgPreparedStatement.java:169)
			at org.postgresql.jdbc.PgPreparedStatement.executeUpdate(PgPreparedStatement.java:136)
			at org.apache.tomcat.dbcp.dbcp2.DelegatingPreparedStatement.executeUpdate(DelegatingPreparedStatement.java:121)
			at org.apache.tomcat.dbcp.dbcp2.DelegatingPreparedStatement.executeUpdate(DelegatingPreparedStatement.java:121)
			at org.hibernate.engine.jdbc.internal.ResultSetReturnImpl.executeUpdate(ResultSetReturnImpl.java:175)
			... 87 more	

Szczegóły w załączniku: [^CMINDEV-2486 - duplicate key value violates unique constraint igo_da_typecode_case_uk.txt]

Przy próbie zmiany modelu spraw w typie posiadającym PK do innej (np najnowszej) wersji tego typu usługa/integracja _changeModel_ nie powinna (moim zdaniem) wykonywać polecenia :
```sql
INSERT INTO IGO_DA_TYPECODE_UK 
(ae_type_code, parameter_def_name, case_type_id, case_id, property_value) SELECT ?, ?, ?, ID, COALESCE(PARAMETER_1, '') 
FROM IGO_DA_CASES 
WHERE case_type_id = ? AND status in ('A', 'O', 'N')
```

Ponieważ przynajmniej niektóre (jeśli nie wszystkie) sprawy podlegające takiej migracji (zmianie modelu) mogą już 
posiadać odpowiadające im wpisy (klucze) w tabeli IGO_DA_TYPECODE_UK (w tych wypadkach zamiast INSERT trzeba wg mnie wykonać UPDATE na case_type_id).

## Komentarze do zadania

W dniu dzisiejszym na środoowisku INEA DEV uruchomiłem po raz pierwszy nową usługę, która w przyszłości służyć ma do automatycznej migracji (patrz zadanie nadrzędne).
Oto log i raport z jej wykonania: [^CMINDEV-2394 migracja automatyczna 202005041010-DEV.log]
Usługa bierze pod uwagę wyłącznie typy Zpi... i dla nich zidentyfikowała 90 par (fromTypeId,toTypeId) dla których potrzebna/wskazana jest migracja (zmiana modelu) spraw do najnowszej wersji typu, ale tylko 13 takich par udało się przetworzyć poprawnie (żaden z tych typów nie posiada PK):
```text
Iteracja 15/90: Zmigrowałem 4 spraw typu "ZpiActionPropertyHolderAgreementConcatenation" z wersji 3 (id=277556) do wersjji 7 (id=280761)
Iteracja 16/90: Zmigrowałem 19 spraw typu "ZpiActionPropertyHolderAgreementConcatenation" z wersji 4 (id=277557) do wersjji 7 (id=280761)
Iteracja 17/90: Zmigrowałem 8 spraw typu "ZpiActionPropertyHolderAgreementConcatenation" z wersji 5.0001 (id=278086) do wersjji 7 (id=280761)
Iteracja 18/90: Zmigrowałem 18 spraw typu "ZpiActionPropertyHolderAgreementConcatenation" z wersji 6 (id=280058) do wersjji 7 (id=280761)
Iteracja 29/90: Zmigrowałem 30363 spraw typu "ZpiAddress" z wersji 6 (id=280056) do wersjji 7 (id=280561)
Iteracja 36/90: Zmigrowałem 2 spraw typu "ZpiBusExpansionRequest" z wersji 1 (id=272585) do wersjji 2 (id=272588)
Iteracja 48/90: Zmigrowałem 11 spraw typu "ZpiDefect" z wersji 1 (id=272638) do wersjji 2.0001 (id=277559)
Iteracja 51/90: Zmigrowałem 31 spraw typu "ZpiGeodesyLot" z wersji 3 (id=271062) do wersjji 6.0001 (id=277574)
Iteracja 66/90: Zmigrowałem 54 spraw typu "ZpiOrderDeadlines" z wersji 2 (id=267564) do wersjji 4 (id=271053)
Iteracja 74/90: Zmigrowałem 36 spraw typu "ZpiPriceList" z wersji 4 (id=267035) do wersjji 5 (id=270537)
Iteracja 83/90: Zmigrowałem 62 spraw typu "ZpiRealizationBasis" z wersji 3 (id=267042) do wersjji 4 (id=276052)
Iteracja 87/90: Zmigrowałem 20 spraw typu "ZpiTaskInstance" z wersji 1 (id=267054) do wersjji 3 (id=269540)
Iteracja 88/90: Zmigrowałem 37 spraw typu "ZpiTaskInstance" z wersji 2 (id=268033) do wersjji 3 (id=269540)
```

W pozostałych 77 przypadkach (iteracjach) wystąpiły błędy, z których większość dotyczy naruszenia unikalności klucza igo_da_typecode_case_uk.


Niektóre, jak np poniższe:
```
Iteracja 50/90: Próba migracji 38 spraw typu "ZpiGeodesyLot" z wersji 2 (id=271054) do wersjji 6.0001 (id=277574) zakończyła się błędem: pro.ibpm.mercury.exceptions.MercuryException: To jest błąd aplikacji. : . Sprawdź logi serwera. Błąd został oznaczony etykietą [node1.423ec6e8-aa05-4891-a8d3-99acfb35e608].
Iteracja 52/90: Próba migracji 4 spraw typu "ZpiGeodesyLot" z wersji 4 (id=272050) do wersjji 6.0001 (id=277574) zakończyła się błędem: pro.ibpm.mercury.exceptions.MercuryException: To jest błąd aplikacji. : . Sprawdź logi serwera. Błąd został oznaczony etykietą [node1.ff5f8e70-f3ab-494a-a7cf-72984c04d930].
Iteracja 53/90: Próba migracji 33 spraw typu "ZpiGeodesyLot" z wersji 5 (id=272060) do wersjji 6.0001 (id=277574) zakończyła się błędem: pro.ibpm.mercury.exceptions.MercuryException: To jest błąd aplikacji. : . Sprawdź logi serwera. Błąd został oznaczony etykietą [node1.e6cbb20a-19ed-4a21-bd01-b26713c973b1].
```
... dotyczą innych problemów, ale nimi zajmę się osobno (nie są przedmiotem niniejszego zgłoszenia).