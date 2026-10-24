# [156] Błąd podczas inicjalizacji danych predefiniowanych

https://github.com/slawascichy/hgdb/issues/156

Podczas startu serwera w logach można znaleźć błąd:

```plaintext
javax.persistence.PersistenceException: org.hibernate.exception.ConstraintViolationException: could not execute batch
at org.hibernate.internal.ExceptionConverterImpl.convert(ExceptionConverterImpl.java:154)
at org.hibernate.internal.ExceptionConverterImpl.convert(ExceptionConverterImpl.java:181)
at org.hibernate.internal.ExceptionConverterImpl.convert(ExceptionConverterImpl.java:188)
at org.hibernate.internal.SessionImpl.doFlush(SessionImpl.java:1366)
at org.hibernate.internal.SessionImpl.flush(SessionImpl.java:1349)
at sun.reflect.NativeMethodAccessorImpl.invoke0(Native Method)
at sun.reflect.NativeMethodAccessorImpl.invoke(NativeMethodAccessorImpl.java:62)
at sun.reflect.DelegatingMethodAccessorImpl.invoke(DelegatingMethodAccessorImpl.java:43)
at java.lang.reflect.Method.invoke(Method.java:498)
at org.springframework.orm.jpa.ExtendedEntityManagerCreator$ExtendedEntityManagerInvocationHandler.invoke(ExtendedEntityManagerCreator.java:362)
at com.sun.proxy.$Proxy103.flush(Unknown Source)
at org.mercury.predefined.values.PredefiniedValuesLoader.loadMercuryData(PredefiniedValuesLoader.java:227)
at pro.ibpm.mercury.dao.PredefinedValuesLoader.uploadData2Db(PredefinedValuesLoader.java:30)
....
Caused by: java.sql.BatchUpdateException: Batch entry 0 insert into IGO_ADM_USERS (FULLNAME, IS_ACTIVE, IS_TECHNICAL, LOCALE, TIME_ZONE, USERNAME, ID) values ('sysmercury', 'TRUE', 'FALSE', 'pl_PL', 'Europe/Warsaw', 'sysmercury', 0) was aborted: BŁĄD: podwójna wartość klucza narusza ograniczenie unikalności "uk_jmappyt7bhw8j4jt3xi5h95ag"
Szczegóły: Klucz (username)=(sysmercury) już istnieje.  Call getNextException to see other errors in the batch.
....
```

Błąd nie wnosi żadnych konsekwencji na działanie systemu, ale jest denerwujący (zaśmieca logi). Trzeba to poprawić.

## Kontekst z zadania 172: Problem z działaniem wątku UserInfoUpdateSecretary

Task-Url: https://github.com/slawascichy/hgdb/issues/172

Od dłuższego czasu obserwujemy problemy z MRC. W logach pojawiają się błędu dotyczące wątku UserInfoUpdateSecretary. Ma to wpływ na działanie biznesowe produktu. Usługi zapisu sprawy wykonują się w nieskończoność. Wątki są zablokowane po stronie MRC.

