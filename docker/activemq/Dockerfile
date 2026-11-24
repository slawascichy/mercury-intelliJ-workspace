# Apache ActiveMQ Classic 5.19.x dla pracy lokalnej (dev) z Mercury DB: broker OpenWire na porcie 51616 (jak dotychczasowy lokalny
# apache-activemq z mercury-server), konsola WWW na 8161, trwałość w KahaDB (wolumin /opt/activemq/data).
# Linia 5.19.x pozostaje przy javax JMS (Java 11, 17, 21), więc klienci activemq-client 5.19.x w Mercury działają bez zmian w kodzie.
FROM eclipse-temurin:17-jre
ARG ACTIVEMQ_VERSION=5.19.12
ADD https://archive.apache.org/dist/activemq/${ACTIVEMQ_VERSION}/apache-activemq-${ACTIVEMQ_VERSION}-bin.tar.gz /tmp/activemq.tar.gz
RUN mkdir -p /opt \
 && tar -xzf /tmp/activemq.tar.gz -C /opt \
 && mv /opt/apache-activemq-${ACTIVEMQ_VERSION} /opt/activemq \
 && rm /tmp/activemq.tar.gz
COPY conf/activemq.xml /opt/activemq/conf/activemq.xml
COPY conf/jetty.xml /opt/activemq/conf/jetty.xml
# ścieżka rzeczywista (bez dowiązania symbolicznego): Jetty odrzuca zasoby konsoli WWW przez alias symlinku
ENV ACTIVEMQ_HOME=/opt/activemq ACTIVEMQ_BASE=/opt/activemq ACTIVEMQ_OPTS_MEMORY="-Xms256m -Xmx1g"
RUN groupadd -r activemq && useradd -r -M -g activemq -d /opt/activemq activemq \
 && mkdir -p /opt/activemq/data /opt/activemq/tmp \
 && chown -R activemq:activemq /opt/activemq
USER activemq
WORKDIR /opt/activemq
EXPOSE 51616 8161
CMD ["bin/activemq", "console"]
