# [11]  Przerobić mechanizmy LC tak, aby wykorzystać picocli

https://github.com/slawascichy/hgdb-utils/issues/11
LC - `line command`
Bardzo fajny pakiet:
```pom.xml
		<dependency>
		    <groupId>info.picocli</groupId>
		    <artifactId>picocli</artifactId>
		    <version>4.7.7</version>
		</dependency>
```

- Warto przerobić mechanizmy linii komend, usprawnić "help'a".
- Dodatkowo przydałyby się wersje językowe dla tego narzędzia.
- Dodać narzędzie do przeprowadzenia backup i restore indeksu lucene. Sprawdzić czy obsługa JMS w trakcie backupu i 
  restore jest zawieszona, by się nie okazało, że te komunikaty zostaną pominięte? Nie chyba mogą lecieć w trakcie 
  backupu i restore bez obsługi, bo backup i restore i tak bazuje na buforze archiwalnym. Zweryfikować czy po backup 
  i restore aktualizacja indeksu lucene nie wywołuje ponownie JMS do innych węzłów.
