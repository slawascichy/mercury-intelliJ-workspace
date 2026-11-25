import re

# Aktualizacja danych w OWLK (wykaz bibliotek i aplikacji w par. 2 oraz oprogramowanie osob trzecich w par. 6); reszta tekstu bez zmian.
# Wykaz bibliotek i aplikacji wynika z zawartosci pakietu instalacyjnego (lib, lib20, libExt, installableApps); wersje z Dockerfile'i mercury-docker.
# Podlisty maja wciecie 4 spacji (Markdown), ciag dalszy pozycji (adres licencji) 8 spacji.

OWN_LIBS = ['mercury-cmis-client', 'mercury-core', 'mercury-core-server', 'mercury-dao', 'mercury-dao-api',
            'mercury-entities-ids', 'mercury-entities', 'mercury-gui-core', 'mercury-lucene-indexes',
            'mercury-lucene-indexes-api', 'mercury-spring-remoting', 'mercury-srv', 'mercury-srv-api',
            'mercury-srv-slave', 'mercury-ws-dto-api', 'mercury-ws-server', 'mercury-ws-server-api',
            'mercury-ws-server-api20', 'mercury-srv-cmd', 'mercury-transfer', 'hgdb-rmi-server-api',
            'hgdb-server-monitor', 'hgdb-tools', 'hgdb-ws-client-cxf', 'hgdb-multi-client']
OWN_APPS = ['mercury-gui-registry', 'mercury-ws-app', 'mercury-gui-auth', 'ROOT']

TPL_LINK = 'https://github.com/Terracotta-OSS/terracotta-core/blob/v5.9.5/LICENSE'
APACHE = 'http://www.apache.org/licenses/LICENSE-2.0.html'
GPLCE = 'https://openjdk.org/legal/gplv2+ce.html'

THIRD = {
    'en': [
        ('Apache Tomcat 9.0.123 – Apache 2.0 license', '( %s )' % APACHE),
        ('Terracotta – Open Source Version (kit ehcache-clustered 3.10.8, Terracotta 5.9.5) / Terracotta Public License 2.0', '( %s )' % TPL_LINK),
        ('Apache ActiveMQ 5.19.12 – Apache 2.0 license', '( %s )' % APACHE),
        ('Eclipse Temurin JDK 17 – GNU General Public License, version 2, with the Classpath Exception', '( %s )' % GPLCE),
        ('IRON POI Server – Iron Sci Software OEM (Original Equipment Manufacturer ) License, only for use in the Program', None),
    ],
    'pl': [
        ('Apache Tomcat 9.0.123 – licencja Apache 2.0', '(%s)' % APACHE),
        ('Terracotta – Open Source Version (kit ehcache-clustered 3.10.8, Terracotta 5.9.5) / Terracotta Public License 2.0', '(%s)' % TPL_LINK),
        ('Apache ActiveMQ 5.19.12 – licencja Apache 2.0', '(%s)' % APACHE),
        ('Eclipse Temurin JDK 17 – GNU General Public License, wersja 2, z wyjątkiem Classpath (Classpath Exception)', '(%s)' % GPLCE),
        ('IRON POI Server – Iron Sci Software OEM (Original Equipment Manufacturer) License, tylko do użytku na potrzeby Programu', None),
    ],
}

IND = '    '


def update_owlk(t, lang):
    libs = '\n\n'.join('%s%d) %s' % (IND, i + 1, n) for i, n in enumerate(OWN_LIBS)) + '\n'
    apps = '\n\n'.join('%s%d) %s' % (IND, i + 1, n) for i, n in enumerate(OWN_APPS)) + '\n'
    third = []
    for i, (a, b) in enumerate(THIRD[lang]):
        third.append('%s%d) %s' % (IND, i + 1, a))
        if b:
            third.append(IND + IND + b)
    third = '\n\n'.join(third) + '\n'
    t, n1 = re.subn(r'[ ]{4}1\) mercury-cmis-client\n\n.*?(?=\n\n3\. )', lambda m: libs.rstrip('\n'), t, count=1, flags=re.S)
    t, n2 = re.subn(r'[ ]{4}19\) mercury[^\n]*\n\n[ ]{4}20\) mercury-ws-app\n', lambda m: apps, t, count=1)
    t, n3 = re.subn(r'[ ]{4}1\) Apache Tomcat[^\n]*\n\n.*?[ ]{4}4\) IRON POI Server[^\n]*\n', lambda m: third, t, count=1, flags=re.S)
    if (n1, n2, n3) != (1, 1, 1):
        raise SystemExit('Nie dopasowano list OWLK: %s' % ((n1, n2, n3),))
    return t
