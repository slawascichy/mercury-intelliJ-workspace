# [110] CaseLobProperty: More than one row with the given identifier was found

https://github.com/slawascichy/hgdb/issues/110

Od czasu do czasu zdarzają się problemy:

	2020-06-29 17:41:45,770 ERROR [AttrTypeEncoderCallable.java:71] : [MercuryPool-3-Th-62] AttrTypeEncoderCallable
	pro.ibpm.mercury.exceptions.SQLWrongQueryException: Błąd zapytania. : More than one row with the given identifier was found: 0fc92cb8dbf279d18738d666973059b6, for class: pro.ibpm.mercury.entities.data.CaseLobProperty : More than one row with the given identifier was found: 0fc92cb8dbf279d18738d666973059b6, for class: pro.ibpm.mercury.entities.data.CaseLobProperty
			at pro.ibpm.mercury.dao.DAOSupport.throwExceptionSQL2(DAOSupport.java:161)
			at pro.ibpm.mercury.dao.MDictDAOSupport.find(MDictDAOSupport.java:345)
			at pro.ibpm.mercury.logic.MDictLogicSupport.find(MDictLogicSupport.java:104)
			at pro.ibpm.mercury.logic.MDictLogicSupport.find(MDictLogicSupport.java:54)
			at sun.reflect.GeneratedMethodAccessor322.invoke(Unknown Source)
			at sun.reflect.DelegatingMethodAccessorImpl.invoke(DelegatingMethodAccessorImpl.java:43)
			at java.lang.reflect.Method.invoke(Method.java:498)
			at org.springframework.aop.support.AopUtils.invokeJoinpointUsingReflection(AopUtils.java:343)
			at org.springframework.aop.framework.ReflectiveMethodInvocation.invokeJoinpoint(ReflectiveMethodInvocation.java:198)
			at org.springframework.aop.framework.ReflectiveMethodInvocation.proceed(ReflectiveMethodInvocation.java:163)
			at org.springframework.transaction.interceptor.TransactionAspectSupport.invokeWithinTransaction(TransactionAspectSupport.java:294)
			at org.springframework.transaction.interceptor.TransactionInterceptor.invoke(TransactionInterceptor.java:98)
			at org.springframework.aop.framework.ReflectiveMethodInvocation.proceed(ReflectiveMethodInvocation.java:186)
			at org.springframework.aop.framework.JdkDynamicAopProxy.invoke(JdkDynamicAopProxy.java:212)
			at com.sun.proxy.$Proxy171.find(Unknown Source)
			at org.mercury.business.data.threads.AttrTypeEncoderCallable.saveLobValue(AttrTypeEncoderCallable.java:171)
			at org.mercury.business.data.threads.AttrTypeEncoderCallable.runInTransaction(AttrTypeEncoderCallable.java:131)
			at org.mercury.business.data.threads.AttrTypeEncoderCallable.call(AttrTypeEncoderCallable.java:68)
			at org.mercury.business.data.threads.AttrTypeEncoderCallable.call(AttrTypeEncoderCallable.java:38)
			at sun.reflect.GeneratedMethodAccessor363.invoke(Unknown Source)
			at sun.reflect.DelegatingMethodAccessorImpl.invoke(DelegatingMethodAccessorImpl.java:43)
			at java.lang.reflect.Method.invoke(Method.java:498)
			at org.springframework.aop.support.AopUtils.invokeJoinpointUsingReflection(AopUtils.java:343)
			at org.springframework.aop.framework.ReflectiveMethodInvocation.invokeJoinpoint(ReflectiveMethodInvocation.java:198)
			at org.springframework.aop.framework.ReflectiveMethodInvocation.proceed(ReflectiveMethodInvocation.java:163)
			at org.springframework.transaction.interceptor.TransactionAspectSupport.invokeWithinTransaction(TransactionAspectSupport.java:294)
			at org.springframework.transaction.interceptor.TransactionInterceptor.invoke(TransactionInterceptor.java:98)
			at org.springframework.aop.framework.ReflectiveMethodInvocation.proceed(ReflectiveMethodInvocation.java:186)
			at org.springframework.aop.framework.JdkDynamicAopProxy.invoke(JdkDynamicAopProxy.java:212)
			at com.sun.proxy.$Proxy172.call(Unknown Source)
			at java.util.concurrent.FutureTask.run(FutureTask.java:266)
			at java.util.concurrent.ThreadPoolExecutor.runWorker(ThreadPoolExecutor.java:1149)
			at java.util.concurrent.ThreadPoolExecutor$Worker.run(ThreadPoolExecutor.java:624)
			at java.lang.Thread.run(Thread.java:748)
	Caused by: javax.persistence.PersistenceException: org.hibernate.HibernateException: More than one row with the given identifier was found: 0fc92cb8dbf279d18738d666973059b6, for class: pro.ibpm.mercury.entities.data.CaseLobProperty
			at org.hibernate.internal.ExceptionConverterImpl.convert(ExceptionConverterImpl.java:154)
			at org.hibernate.internal.ExceptionConverterImpl.convert(ExceptionConverterImpl.java:200)
			at org.hibernate.internal.SessionImpl.find(SessionImpl.java:3516)
			at org.hibernate.internal.SessionImpl.find(SessionImpl.java:3447)
			at sun.reflect.GeneratedMethodAccessor257.invoke(Unknown Source)
			at sun.reflect.DelegatingMethodAccessorImpl.invoke(DelegatingMethodAccessorImpl.java:43)
			at java.lang.reflect.Method.invoke(Method.java:498)
			at org.springframework.orm.jpa.SharedEntityManagerCreator$SharedEntityManagerInvocationHandler.invoke(SharedEntityManagerCreator.java:308)
			at com.sun.proxy.$Proxy102.find(Unknown Source)
			at pro.ibpm.mercury.dao.MDictDAOSupport.find(MDictDAOSupport.java:341)
			... 32 more
	Caused by: org.hibernate.HibernateException: More than one row with the given identifier was found: 0fc92cb8dbf279d18738d666973059b6, for class: pro.ibpm.mercury.entities.data.CaseLobProperty
			at org.hibernate.loader.entity.plan.AbstractLoadPlanBasedEntityLoader.extractEntityResult(AbstractLoadPlanBasedEntityLoader.java:251)
			at org.hibernate.loader.entity.plan.AbstractLoadPlanBasedEntityLoader.load(AbstractLoadPlanBasedEntityLoader.java:195)
			at org.hibernate.persister.entity.AbstractEntityPersister.load(AbstractEntityPersister.java:4269)
			at org.hibernate.event.internal.DefaultLoadEventListener.loadFromDatasource(DefaultLoadEventListener.java:511)
			at org.hibernate.event.internal.DefaultLoadEventListener.doLoad(DefaultLoadEventListener.java:481)
			at org.hibernate.event.internal.DefaultLoadEventListener.load(DefaultLoadEventListener.java:222)
			at org.hibernate.event.internal.DefaultLoadEventListener.proxyOrLoad(DefaultLoadEventListener.java:281)
			at org.hibernate.event.internal.DefaultLoadEventListener.doOnLoad(DefaultLoadEventListener.java:124)
			at org.hibernate.event.internal.DefaultLoadEventListener.onLoad(DefaultLoadEventListener.java:92)
			at org.hibernate.internal.SessionImpl.fireLoad(SessionImpl.java:1257)
			at org.hibernate.internal.SessionImpl.access$1900(SessionImpl.java:207)
			at org.hibernate.internal.SessionImpl$IdentifierLoadAccessImpl.doLoad(SessionImpl.java:2874)
			at org.hibernate.internal.SessionImpl$IdentifierLoadAccessImpl.load(SessionImpl.java:2848)
			at org.hibernate.internal.SessionImpl.find(SessionImpl.java:3483)
			... 39 more
	2020-06-29 17:41:45,770 ERROR [AttrTypeEncoderCallable.java:71] : [MercuryPool-3-Th-59] AttrTypeEncoderCallable
	pro.ibpm.mercury.exceptions.SQLWrongQueryException: Błąd zapytania. : More than one row with the given identifier was found: 0fc92cb8dbf279d18738d666973059b6, for class: pro.ibpm.mercury.entities.data.CaseLobProperty : More than one row with the given identifier was found: 0fc92cb8dbf279d18738d666973059b6, for class: pro.ibpm.mercury.entities.data.CaseLobProperty
			at pro.ibpm.mercury.dao.DAOSupport.throwExceptionSQL2(DAOSupport.java:161)
			at pro.ibpm.mercury.dao.MDictDAOSupport.find(MDictDAOSupport.java:345)
			at pro.ibpm.mercury.logic.MDictLogicSupport.find(MDictLogicSupport.java:104)
			at pro.ibpm.mercury.logic.MDictLogicSupport.find(MDictLogicSupport.java:54)
			at sun.reflect.GeneratedMethodAccessor322.invoke(Unknown Source)
			at sun.reflect.DelegatingMethodAccessorImpl.invoke(DelegatingMethodAccessorImpl.java:43)
			at java.lang.reflect.Method.invoke(Method.java:498)
			at org.springframework.aop.support.AopUtils.invokeJoinpointUsingReflection(AopUtils.java:343)
			at org.springframework.aop.framework.ReflectiveMethodInvocation.invokeJoinpoint(ReflectiveMethodInvocation.java:198)
			at org.springframework.aop.framework.ReflectiveMethodInvocation.proceed(ReflectiveMethodInvocation.java:163)
			at org.springframework.transaction.interceptor.TransactionAspectSupport.invokeWithinTransaction(TransactionAspectSupport.java:294)
			at org.springframework.transaction.interceptor.TransactionInterceptor.invoke(TransactionInterceptor.java:98)
			at org.springframework.aop.framework.ReflectiveMethodInvocation.proceed(ReflectiveMethodInvocation.java:186)
			at org.springframework.aop.framework.JdkDynamicAopProxy.invoke(JdkDynamicAopProxy.java:212)
			at com.sun.proxy.$Proxy171.find(Unknown Source)
			at org.mercury.business.data.threads.AttrTypeEncoderCallable.saveLobValue(AttrTypeEncoderCallable.java:171)
			at org.mercury.business.data.threads.AttrTypeEncoderCallable.runInTransaction(AttrTypeEncoderCallable.java:131)
			at org.mercury.business.data.threads.AttrTypeEncoderCallable.call(AttrTypeEncoderCallable.java:68)
			at org.mercury.business.data.threads.AttrTypeEncoderCallable.call(AttrTypeEncoderCallable.java:38)
			at sun.reflect.GeneratedMethodAccessor363.invoke(Unknown Source)
			at sun.reflect.DelegatingMethodAccessorImpl.invoke(DelegatingMethodAccessorImpl.java:43)
			at java.lang.reflect.Method.invoke(Method.java:498)
			at org.springframework.aop.support.AopUtils.invokeJoinpointUsingReflection(AopUtils.java:343)
			at org.springframework.aop.framework.ReflectiveMethodInvocation.invokeJoinpoint(ReflectiveMethodInvocation.java:198)
			at org.springframework.aop.framework.ReflectiveMethodInvocation.proceed(ReflectiveMethodInvocation.java:163)
			at org.springframework.transaction.interceptor.TransactionAspectSupport.invokeWithinTransaction(TransactionAspectSupport.java:294)
			at org.springframework.transaction.interceptor.TransactionInterceptor.invoke(TransactionInterceptor.java:98)
			at org.springframework.aop.framework.ReflectiveMethodInvocation.proceed(ReflectiveMethodInvocation.java:186)
			at org.springframework.aop.framework.JdkDynamicAopProxy.invoke(JdkDynamicAopProxy.java:212)
			at com.sun.proxy.$Proxy172.call(Unknown Source)
			at java.util.concurrent.FutureTask.run(FutureTask.java:266)
			at java.util.concurrent.ThreadPoolExecutor.runWorker(ThreadPoolExecutor.java:1149)
			at java.util.concurrent.ThreadPoolExecutor$Worker.run(ThreadPoolExecutor.java:624)
			at java.lang.Thread.run(Thread.java:748)
	Caused by: javax.persistence.PersistenceException: org.hibernate.HibernateException: More than one row with the given identifier was found: 0fc92cb8dbf279d18738d666973059b6, for class: pro.ibpm.mercury.entities.data.CaseLobProperty
			at org.hibernate.internal.ExceptionConverterImpl.convert(ExceptionConverterImpl.java:154)
			at org.hibernate.internal.ExceptionConverterImpl.convert(ExceptionConverterImpl.java:200)
			at org.hibernate.internal.SessionImpl.find(SessionImpl.java:3516)
			at org.hibernate.internal.SessionImpl.find(SessionImpl.java:3447)
			at sun.reflect.GeneratedMethodAccessor257.invoke(Unknown Source)
			at sun.reflect.DelegatingMethodAccessorImpl.invoke(DelegatingMethodAccessorImpl.java:43)
			at java.lang.reflect.Method.invoke(Method.java:498)
			at org.springframework.orm.jpa.SharedEntityManagerCreator$SharedEntityManagerInvocationHandler.invoke(SharedEntityManagerCreator.java:308)
			at com.sun.proxy.$Proxy102.find(Unknown Source)
			at pro.ibpm.mercury.dao.MDictDAOSupport.find(MDictDAOSupport.java:341)
			... 32 more
	Caused by: org.hibernate.HibernateException: More than one row with the given identifier was found: 0fc92cb8dbf279d18738d666973059b6, for class: pro.ibpm.mercury.entities.data.CaseLobProperty
			at org.hibernate.loader.entity.plan.AbstractLoadPlanBasedEntityLoader.extractEntityResult(AbstractLoadPlanBasedEntityLoader.java:251)
			at org.hibernate.loader.entity.plan.AbstractLoadPlanBasedEntityLoader.load(AbstractLoadPlanBasedEntityLoader.java:195)
			at org.hibernate.persister.entity.AbstractEntityPersister.load(AbstractEntityPersister.java:4269)
			at org.hibernate.event.internal.DefaultLoadEventListener.loadFromDatasource(DefaultLoadEventListener.java:511)
			at org.hibernate.event.internal.DefaultLoadEventListener.doLoad(DefaultLoadEventListener.java:481)
			at org.hibernate.event.internal.DefaultLoadEventListener.load(DefaultLoadEventListener.java:222)
			at org.hibernate.event.internal.DefaultLoadEventListener.proxyOrLoad(DefaultLoadEventListener.java:281)
			at org.hibernate.event.internal.DefaultLoadEventListener.doOnLoad(DefaultLoadEventListener.java:124)
			at org.hibernate.event.internal.DefaultLoadEventListener.onLoad(DefaultLoadEventListener.java:92)
			at org.hibernate.internal.SessionImpl.fireLoad(SessionImpl.java:1257)
			at org.hibernate.internal.SessionImpl.access$1900(SessionImpl.java:207)
			at org.hibernate.internal.SessionImpl$IdentifierLoadAccessImpl.doLoad(SessionImpl.java:2874)
			at org.hibernate.internal.SessionImpl$IdentifierLoadAccessImpl.load(SessionImpl.java:2848)
			at org.hibernate.internal.SessionImpl.find(SessionImpl.java:3483)
			... 39 more

Występują one gdy systemy są bardzo obciążone i wielowątkowa aktualizacje nie widzą zmian obiektu LOB.


## Komentarze do zadania

### Komentarz 1

Workaround: Oczyścić tablicę IGO_DA_CASE_LOB_PROPS z duplikatów.

```
create table IGO_DA_CASE_LOB_PROPS_TMP 
as
select distinct *  
FROM IGO_DA_CASE_LOB_PROPS
where 
id in (
SELECT ID 
FROM IGO_DA_CASE_LOB_PROPS
GROUP BY ID
HAVING count(1) > 1
);


delete FROM IGO_DA_CASE_LOB_PROPS
where id in (select id from IGO_DA_CASE_LOB_PROPS_TMP);

commit;

insert into IGO_DA_CASE_LOB_PROPS
select * from IGO_DA_CASE_LOB_PROPS_TMP;

commit;

drop table IGO_DA_CASE_LOB_PROPS_TMP; 

commit;
```

### Komentarz 2

Prawdopodobnie problem się pojawia podczas ładowania komentarzy zmian gdy jest aktualizowana lista spraw oraz komentarz zmiany jest taki sam dla wszystkich spraw na liście. Dotychczas problem łączyłem tylko z wartością pola i na nim skupiałem swoją uwagę podczas napraw transakcji. Hipoteza z komentarzami zmienia postać rzeczy i wyjaśnia dlaczego jeszcze nie rozwiązałem problemu.


