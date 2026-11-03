# Serwer Terracotta (Ehcache clustered 3.6.1) dla pamięci podręcznych Mercury DB.
# Kit serwera pochodzi z Maven Central (ta sama wersja co klient ehcache-clustered 3.6.1 w Mercury).
FROM eclipse-temurin:8-jdk AS kit
ARG EHCACHE_VERSION=3.6.1
ADD https://repo1.maven.org/maven2/org/ehcache/ehcache-clustered/${EHCACHE_VERSION}/ehcache-clustered-${EHCACHE_VERSION}-kit.tgz /tmp/kit.tgz
RUN mkdir -p /opt/terracotta \
 && tar -xzf /tmp/kit.tgz -C /opt/terracotta --strip-components=1 \
 && rm /tmp/kit.tgz
COPY bench/Bench.java /tmp/bench/Bench.java
RUN mkdir -p /opt/bench \
 && javac -encoding UTF-8 -cp "/opt/terracotta/client/ehcache/*:/opt/terracotta/client/lib/*" -d /opt/bench /tmp/bench/Bench.java

FROM eclipse-temurin:8-jre
COPY --from=kit /opt/terracotta /opt/terracotta
COPY --from=kit /opt/bench /opt/bench
COPY bench/bench.xml /opt/bench/bench.xml
COPY tc-config.xml /config/tc-config.xml
COPY entrypoint.sh /entrypoint.sh
# usunięcie ewentualnych znaków CR (plik edytowany na Windows) i nadanie praw wykonania
RUN tr -d '\r' < /entrypoint.sh > /entrypoint.tmp \
 && mv /entrypoint.tmp /entrypoint.sh \
 && chmod +x /entrypoint.sh /opt/terracotta/server/bin/start-tc-server.sh \
 && mkdir -p /data/logs
EXPOSE 9510 9530
ENTRYPOINT ["/entrypoint.sh"]
CMD ["server"]
