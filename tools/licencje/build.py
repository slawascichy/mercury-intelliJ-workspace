import csv, re, os, sys, io, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from owlk_update import update_owlk

OUT = sys.argv[1]
RELEASE = '3.0.4.45'
POI_VERSION = '4.1.0.11'
ASOF = '2026-11-25'


def read(p):
    return open(p, encoding='utf-8').read()


def rows(p):
    return list(csv.DictReader(open(p, encoding='utf-8'), delimiter=';'))


def is_own(r):
    f = r['plik']
    g = r['groupId:artifactId']
    return f.startswith(('mercury-', 'hgdb-', 'poi-toolkit')) or g.startswith(('io.hgdb', 'org.iron'))


LIB = [r for r in rows('libs.csv') if not is_own(r)]
POI = [r for r in rows('poi_libs.csv') if not is_own(r)]

LICENSE_LINKS = {
    'Apache-2.0': 'https://www.apache.org/licenses/LICENSE-2.0',
    'EPL-1.0': 'https://www.eclipse.org/legal/epl-v10.html',
    'EPL-2.0': 'https://www.eclipse.org/legal/epl-2.0/',
    'EDL-1.0 (BSD-3-Clause)': 'https://www.eclipse.org/org/documents/edl-v10.php',
    'CDDL-1.0': 'https://opensource.org/license/cddl-1-0',
    'CDDL-1.1': 'https://javaee.github.io/glassfish/LICENSE',
    'GPL-2.0 with Classpath Exception': 'https://openjdk.org/legal/gplv2+ce.html',
    'GPL-2.0 with FOSS License Exception': 'https://www.mysql.com/about/legal/licensing/foss-exception/',
    'GPL-2.0': 'https://www.gnu.org/licenses/old-licenses/gpl-2.0.html',
    'LGPL-2.1': 'https://www.gnu.org/licenses/old-licenses/lgpl-2.1.html',
    'MIT': 'https://opensource.org/license/mit',
    'BSD-2-Clause': 'https://opensource.org/license/bsd-2-clause',
    'BSD-3-Clause': 'https://opensource.org/license/bsd-3-clause',
    'MPL-1.1': 'https://www.mozilla.org/en-US/MPL/1.1/',
    'CPL-1.0': 'https://www.eclipse.org/legal/cpl-v10.html',
    'Terracotta Public License 2.0': 'https://github.com/Terracotta-OSS/terracotta-core/blob/v5.9.5/LICENSE',
    'PostgreSQL License': 'https://www.postgresql.org/about/licence/',
    'OpenLDAP Public License': 'https://www.openldap.org/software/release/license.html',
    'SIL OFL 1.1': 'https://openfontlicense.org/',
    'DejaVu Fonts License': 'https://dejavu-fonts.github.io/License.html',
}

# licencje, których POM nie podaje albo podaje błędnie: wynik sprawdzenia w Maven Central, w jarze albo w repozytorium projektu
OVERRIDE = {
    'ezmorph': 'Apache-2.0',
    'json-lib': 'Apache-2.0',
    'javasysmon': 'BSD-2-Clause',
    'jstl': 'CDDL-1.0',
    'jsp-api': 'Not stated (Sun / Oracle JSP 2.1 API)',
    'ojdbc6': 'Oracle proprietary (vendor terms)',
    'sqljdbc4': 'Microsoft proprietary (vendor terms)',
    'mysql-connector-java': 'GPL-2.0 with FOSS License Exception',
    'fscontext': 'Sun Binary Code License (proprietary)',
    'providerutil': 'Sun Binary Code License (proprietary)',
}


def norm1(raw):
    s = raw.strip()
    l = s.lower()
    if not s:
        return ''
    if 'sun microsystems' in l and 'binary' in l:
        return 'Sun Binary Code License (proprietary)'
    if 'classpath' in l or 'gpl2 w/ cpe' in l or 'gplv2+ce' in l or 'gpl2 w/cpe' in l:
        return 'GPL-2.0 with Classpath Exception'
    if 'foss' in l:
        return 'GPL-2.0 with FOSS License Exception'
    if 'eclipse distribution' in l or l.startswith('edl'):
        return 'EDL-1.0 (BSD-3-Clause)'
    if 'eclipse public' in l or l.startswith('epl'):
        return 'EPL-2.0' if re.search(r'2\.0|v\. ?2|epl 2|epl-2', l) else 'EPL-1.0'
    if 'cddl' in l or 'common development' in l:
        if '1.1' in l:
            return 'CDDL-1.1'
        return 'CDDL-1.0'
    if 'lesser' in l or 'library general' in l or 'lgpl' in l:
        return 'LGPL-2.1'
    if 'general public license' in l or l.startswith('gpl'):
        return 'GPL-2.0'
    if 'mpl' in l or 'mozilla' in l:
        return 'MPL-1.1'
    if 'apache' in l or l.startswith('asl'):
        return 'Apache-2.0'
    if 'bsd' in l:
        if '2' in l or 'free' in l:
            return 'BSD-2-Clause'
        if '3' in l or 'new' in l:
            return 'BSD-3-Clause'
        return 'BSD (variant not stated in the POM)'
    if 'mit' in l:
        return 'MIT'
    if l == 'cpl':
        return 'CPL-1.0'
    if 'sax' in l:
        return 'SAX (public domain)'
    if 'w3c' in l:
        return 'W3C Software License'
    return s


def license_type(r):
    base = re.sub(r'-[0-9].*$', '', r['plik'][:-4])
    for k, v in OVERRIDE.items():
        if base == k or base.startswith(k):
            return v
    raw = r['licencja_z_pom']
    parts = []
    for p in raw.split(';'):
        n = norm1(p)
        if n and n not in parts:
            parts.append(n)
    if not parts:
        return 'Not stated'
    return ' / '.join(parts)


def repo_url(r):
    for cand in (r['scm'], r['url']):
        c = cand.strip()
        c = re.sub(r'^scm:git:', '', c)
        c = re.sub(r'^scm:svn:', '', c)
        c = re.sub(r'^git@github\.com:', 'https://github.com/', c)
        c = re.sub(r'^git://', 'https://', c)
        c = re.sub(r'\.git$', '', c)
        if c.startswith('http') and ' ' not in c and ')' not in c and '(' not in c:
            return c
    return ''


ESC = {'{': '&#123;', '}': '&#125;', '<': '&lt;', '>': '&gt;', '|': '&#124;'}


def esc(t):
    t = ''.join(ESC.get(ch, ch) for ch in t)
    t = t.replace('\\', '\\\\').replace('*', '\\*').replace('_', '\\_').replace('`', '\\`').replace('[', '\\[').replace(']', '\\]')
    return re.sub(r'\s+', ' ', t).strip()


JDBC_MANUAL = {
    'mysql-connector-java-5.1.38-bin.jar': ('mysql-connector-java', '5.1.38', 'MySQL Connector/J (JDBC driver for MySQL). [link](https://github.com/mysql/mysql-connector-j)'),
    'ojdbc6.jar': ('ojdbc6', '11.2.0.1.0', 'Oracle JDBC driver (Oracle Database 11.2).'),
    'sqljdbc4.jar': ('sqljdbc4', '-', 'Microsoft JDBC driver for SQL Server.'),
}
DESC_OVERRIDE = {'ojdbc6': 'Oracle JDBC driver (Oracle Database 11.2).'}


JDBC_GROUP = {'mysql-connector-java-5.1.38-bin.jar': 'mysql', 'ojdbc6.jar': 'com.oracle', 'sqljdbc4.jar': 'com.microsoft.sqlserver'}


def split_ga(r):
    ga = r['groupId:artifactId']
    if ga:
        g, a = ga.split(':', 1)
        return g, a
    if r['plik'] in JDBC_MANUAL:
        return JDBC_GROUP[r['plik']], JDBC_MANUAL[r['plik']][0]
    return '(no group)', r['plik'][:-4]


def lib_row(r):
    if r['plik'] in JDBC_MANUAL and not r['groupId:artifactId']:
        c, v, d = JDBC_MANUAL[r['plik']]
        return '| %s | %s | %s | %s |' % (esc(c), esc(v), esc(license_type(r)), d)
    comp = split_ga(r)[1]
    ver = r['wersja'] or '-'
    lt = license_type(r)
    desc = r['nazwa'] if r['nazwa'] and not r['nazwa'].startswith('$') else ''
    if r['opis'] and r['opis'][:40] not in desc:
        desc = (desc + ': ' if desc else '') + r['opis']
    for k, v in DESC_OVERRIDE.items():
        if comp == k:
            desc = v
    desc = esc(desc)[:150]
    url = repo_url(r)
    link = ' [link](%s)' % url if url else ''
    return '| %s | %s | %s | %s%s |' % (esc(comp), esc(ver), esc(lt), desc, link)


def table(rs, head):
    """Biblioteki podzielone na sekcje (naglowek ###) wg groupId; w tabeli tylko artifactId."""
    groups = collections.defaultdict(list)
    for r in rs:
        g, a = split_ga(r)
        groups[g].append((a.lower(), r))
    out = []
    for g in sorted(groups, key=lambda x: x.lower()):
        out += ['### ' + esc(g), '', '| ' + ' | '.join(head) + ' |', '|' + '---|' * len(head)]
        seen = set()
        for _, r in sorted(groups[g], key=lambda x: x[0]):
            row = lib_row(r)
            if row in seen:
                continue
            seen.add(row)
            out.append(row)
        out.append('')
    return '\n'.join(out).rstrip('\n')


def summary(rs):
    c = collections.Counter(license_type(r) for r in rs)
    out = []
    for k, v in c.most_common():
        link = ''
        for part in k.split(' / '):
            if part in LICENSE_LINKS:
                link += (' ' if link else '') + '[%s](%s)' % (esc(part), LICENSE_LINKS[part])
        out.append('| %s | %d | %s |' % (esc(k), v, link or '-'))
    return out


STR = {
    'en': {
        'a1_title': 'Annex No. 1 – Third Party Software',
        'a1_intro': 'This annex lists the third-party software delivered with Mercury 3.0 DB (HgDB), with the version, the type of license and a link to the project. The list was generated from the files of the installation package of release **%s** (state as of %s) and from the license data in the POM files of the libraries; versions of the next release are published in the same way. Where a library does not state its license in its POM file, the license was taken from the artifact published in Maven Central, from the license file inside the library or from the project repository; entries that could not be confirmed are marked as not stated.' % (RELEASE, ASOF),
        'a1_note': 'The license of a component is the one stated by its authors; this page is informational. Full license texts are available under the links in the summary table and in the components themselves. The wording of the General Commercial License Terms and of this annex that applies to a given license agreement is the one attached to that agreement.',
        'tools_h': 'Runtime, tools and images',
        'libs_h': 'Java libraries of the server',
        'libs_p': 'Libraries delivered in the directories `lib`, `lib20` and `libExt` of the installation package and in the web application `mercury-ws-app`. Own libraries of Mercury DB (HgDB) (`mercury-*`, `hgdb-*`, `poi-toolkit`) are covered by the General Commercial License Terms and by the license of the HgDB client, and are not listed here.',
        'jdbc_h': 'JDBC drivers',
        'jdbc_p': 'Drivers delivered in the directory `jdbcdrivers` of the installation package. Drivers of Oracle and Microsoft are proprietary products of their vendors; their terms of use apply.',
        'web_h': 'Libraries of the web user interface',
        'sum_h': 'Summary of license types (Java libraries)',
        'head': ['Component', 'Version', 'License type', 'Description and repository'],
        'head_lib': ['Artifact', 'Version', 'License type', 'Description and repository'],
        'sum_head': ['License type', 'Components', 'License text'],
        'poi_h': 'Libraries of Iron POI Server',
        'poi_p': 'Third-party libraries delivered with Iron POI Server **%s** (directory `lib` of the release, state as of %s). The library `poi-toolkit` is an own component of Mercury DB (HgDB).' % (POI_VERSION, ASOF),
        'a2_title': 'Annex No. 2 – Iron Sci Software OEM License',
        'a2_notice': ':::note Language\nThe text of the license "Iron Sci Software OEM License, for use only for the Program" (Annex No. 2 to the General Commercial License Terms) is available in Polish only. See the Polish version of this page.\n:::',
        'owlk_title': 'General Commercial License Terms',
        'idx_title': 'Licenses',
        'idx_text': 'License documents of Mercury 3.0 DB (HgDB):\n\n1. [General Commercial License Terms](./OWLK) – terms of licenses to use and to distribute the Program.\n2. [Annex No. 1 – Third Party Software](./Annex_1_Third_Party_Software) – third-party software delivered with the Program, with versions and types of licenses.\n3. [Annex No. 2 – Iron Sci Software OEM License](./Annex_2_Iron_POI_Server_OEM_License) – license of Iron POI Server and its third-party libraries (the license text is available in Polish only).\n\nQuestions about licenses: `info@scisoftware.pl`.',
    },
    'pl': {
        'a1_title': 'Załącznik Nr 1 – Oprogramowanie osób trzecich',
        'a1_intro': 'Załącznik zawiera wykaz oprogramowania osób trzecich dostarczanego z Mercury 3.0 DB (HgDB), wraz z wersją, rodzajem licencji i odsyłaczem do projektu. Wykaz został wygenerowany z plików pakietu instalacyjnego wydania **%s** (stan na %s) oraz z danych o licencjach zapisanych w plikach POM bibliotek; wersje kolejnych wydań są publikowane w ten sam sposób. Jeżeli biblioteka nie podaje licencji w swoim pliku POM, licencję przyjęto z artefaktu opublikowanego w Maven Central, z pliku licencji wewnątrz biblioteki albo z repozytorium projektu; pozycje, których nie udało się potwierdzić, oznaczono jako niepodane.' % (RELEASE, ASOF),
        'a1_note': 'Licencja składnika jest taka, jaką podają jego autorzy; ta strona ma charakter informacyjny. Pełne teksty licencji są dostępne pod odsyłaczami w tabeli podsumowania i w samych składnikach. Brzmienie Ogólnych Warunków Licencji Komercyjnej i niniejszego załącznika obowiązujące w danej umowie licencyjnej jest to, które zostało do niej dołączone.',
        'tools_h': 'Środowisko uruchomieniowe, narzędzia i obrazy',
        'libs_h': 'Biblioteki Java serwera',
        'libs_p': 'Biblioteki dostarczane w katalogach `lib`, `lib20` i `libExt` pakietu instalacyjnego oraz w aplikacji webowej `mercury-ws-app`. Własne biblioteki Mercury DB (HgDB) (`mercury-*`, `hgdb-*`, `poi-toolkit`) podlegają Ogólnym Warunkom Licencji Komercyjnej i licencji klienta HgDB i nie są tu wymienione.',
        'jdbc_h': 'Sterowniki JDBC',
        'jdbc_p': 'Sterowniki dostarczane w katalogu `jdbcdrivers` pakietu instalacyjnego. Sterowniki Oracle i Microsoft są produktami własnościowymi ich producentów; obowiązują ich warunki użytkowania.',
        'web_h': 'Biblioteki interfejsu webowego',
        'sum_h': 'Podsumowanie rodzajów licencji (biblioteki Java)',
        'head': ['Składnik', 'Wersja', 'Rodzaj licencji', 'Opis i repozytorium'],
        'head_lib': ['Artefakt', 'Wersja', 'Rodzaj licencji', 'Opis i repozytorium'],
        'sum_head': ['Rodzaj licencji', 'Składniki', 'Tekst licencji'],
        'poi_h': 'Biblioteki Iron POI Server',
        'poi_p': 'Biblioteki osób trzecich dostarczane z Iron POI Server **%s** (katalog `lib` wydania, stan na %s). Biblioteka `poi-toolkit` jest własnym komponentem Mercury DB (HgDB).' % (POI_VERSION, ASOF),
        'a2_title': 'Załącznik Nr 2 – Iron Sci Software OEM License',
        'a2_notice': '',
        'owlk_title': 'Ogólne Warunki Licencji Komercyjnej',
        'idx_title': 'Licencje',
        'idx_text': 'Dokumenty licencyjne Mercury 3.0 DB (HgDB):\n\n1. [Ogólne Warunki Licencji Komercyjnej](./OWLK) – warunki licencji na korzystanie z Programu i na jego dystrybucję.\n2. [Załącznik Nr 1 – Oprogramowanie osób trzecich](./Annex_1_Third_Party_Software) – oprogramowanie osób trzecich dostarczane z Programem, z wersjami i rodzajami licencji.\n3. [Załącznik Nr 2 – Iron Sci Software OEM License](./Annex_2_Iron_POI_Server_OEM_License) – licencja Iron POI Server i jego bibliotek osób trzecich.\n\nPytania dotyczące licencji: `info@scisoftware.pl`.',
    },
}

TOOLS = {
    'en': [
        ('Eclipse Temurin JDK', '17.0.21.1', 'GPL-2.0 with Classpath Exception', 'Java runtime of the server image. [link](https://github.com/adoptium/temurin17-binaries)'),
        ('Eclipse Temurin 17 on Red Hat UBI 9 minimal', 'image `eclipse-temurin:17-jdk-ubi9-minimal`', 'GPL-2.0 with Classpath Exception (Temurin); Red Hat UBI end user license agreement (base system)', 'Base image of the Iron POI Server, ActiveMQ and Ehcache (Terracotta) images. [link](https://www.redhat.com/en/about/red-hat-end-user-license-agreements#UBI)'),
        ('AlmaLinux', '9', 'Open source licenses of the packages of the distribution (mainly GPL and LGPL)', 'Base image of the server and the load balancer images. [link](https://almalinux.org/)'),
        ('Apache Tomcat', '9.0.123', 'Apache-2.0', 'Web application server. [link](https://github.com/apache/tomcat)'),
        ('Apache ActiveMQ', '5.19.12', 'Apache-2.0', 'Message broker. [link](https://github.com/apache/activemq)'),
        ('Terracotta Server (kit `ehcache-clustered` 3.10.8, Terracotta 5.9.5)', '3.10.8', 'Terracotta Public License 2.0 (server and clustering components); Ehcache client: Apache-2.0', 'Server of the clustered caches. The kit is delivered unmodified; the source code is available in [terracotta-core](https://github.com/Terracotta-OSS/terracotta-core) (tag v5.9.5) and [ehcache3](https://github.com/ehcache/ehcache3).'),
        ('PostgreSQL', '17.11', 'PostgreSQL License', 'Database (image `postgres:17.11`). [link](https://github.com/postgres/postgres)'),
        ('nginx', 'package of AlmaLinux 9 (depends on the build date)', 'BSD-2-Clause', 'Load balancer. [link](https://github.com/nginx/nginx)'),
        ('OpenLDAP (slapd)', 'package of Ubuntu 24.04 (image `scisoftware/openldap:ubuntu-24.04`)', 'OpenLDAP Public License', 'Directory service of the authentication data. [link](https://www.openldap.org/)'),
        ('DejaVu fonts', 'package `dejavu-sans-fonts`', 'DejaVu Fonts License', 'Fonts of Iron POI Server (rendering of reports). [link](https://dejavu-fonts.github.io/)'),
    ],
    'pl': [
        ('Eclipse Temurin JDK', '17.0.21.1', 'GPL-2.0 with Classpath Exception', 'Środowisko Java obrazu serwera. [link](https://github.com/adoptium/temurin17-binaries)'),
        ('Eclipse Temurin 17 na Red Hat UBI 9 minimal', 'obraz `eclipse-temurin:17-jdk-ubi9-minimal`', 'GPL-2.0 with Classpath Exception (Temurin); umowa licencyjna użytkownika końcowego Red Hat UBI (system bazowy)', 'Obraz bazowy obrazów Iron POI Server, ActiveMQ i Ehcache (Terracotta). [link](https://www.redhat.com/en/about/red-hat-end-user-license-agreements#UBI)'),
        ('AlmaLinux', '9', 'Licencje open source pakietów dystrybucji (głównie GPL i LGPL)', 'Obraz bazowy obrazów serwera i load balancera. [link](https://almalinux.org/)'),
        ('Apache Tomcat', '9.0.123', 'Apache-2.0', 'Serwer aplikacji webowych. [link](https://github.com/apache/tomcat)'),
        ('Apache ActiveMQ', '5.19.12', 'Apache-2.0', 'Broker komunikatów. [link](https://github.com/apache/activemq)'),
        ('Terracotta Server (kit `ehcache-clustered` 3.10.8, Terracotta 5.9.5)', '3.10.8', 'Terracotta Public License 2.0 (serwer i komponenty klastrowe); klient Ehcache: Apache-2.0', 'Serwer klastrowych pamięci podręcznych. Kit jest dostarczany bez zmian; kod źródłowy jest dostępny w [terracotta-core](https://github.com/Terracotta-OSS/terracotta-core) (tag v5.9.5) i [ehcache3](https://github.com/ehcache/ehcache3).'),
        ('PostgreSQL', '17.11', 'PostgreSQL License', 'Baza danych (obraz `postgres:17.11`). [link](https://github.com/postgres/postgres)'),
        ('nginx', 'pakiet AlmaLinux 9 (zależy od daty budowy)', 'BSD-2-Clause', 'Load balancer. [link](https://github.com/nginx/nginx)'),
        ('OpenLDAP (slapd)', 'pakiet Ubuntu 24.04 (obraz `scisoftware/openldap:ubuntu-24.04`)', 'OpenLDAP Public License', 'Usługa katalogowa danych uwierzytelniania. [link](https://www.openldap.org/)'),
        ('Czcionki DejaVu', 'pakiet `dejavu-sans-fonts`', 'DejaVu Fonts License', 'Czcionki Iron POI Server (generowanie raportów). [link](https://dejavu-fonts.github.io/)'),
    ],
}
WEBLIBS = {
    'en': [
        ('Bootstrap', '3.3.7', 'MIT', 'CSS and JavaScript framework. [link](https://github.com/twbs/bootstrap)'),
        ('jQuery', '2.0.3', 'MIT', 'JavaScript library. [link](https://github.com/jquery/jquery)'),
        ('Font Awesome', '4.7.0', 'MIT (CSS); SIL OFL 1.1 (fonts)', 'Icon fonts. [link](https://github.com/FortAwesome/Font-Awesome)'),
        ('Bootstrap-3-Typeahead', '4.0.2', 'Apache-2.0', 'Typeahead for Bootstrap 3. [link](https://github.com/bassjobsen/Bootstrap-3-Typeahead)'),
        ('Swagger UI (webjar `org.webjars:swagger-ui`)', '5.32.0', 'Apache-2.0', 'Documentation of the REST API. [link](https://github.com/swagger-api/swagger-ui)'),
    ],
    'pl': [
        ('Bootstrap', '3.3.7', 'MIT', 'Biblioteka CSS i JavaScript. [link](https://github.com/twbs/bootstrap)'),
        ('jQuery', '2.0.3', 'MIT', 'Biblioteka JavaScript. [link](https://github.com/jquery/jquery)'),
        ('Font Awesome', '4.7.0', 'MIT (CSS); SIL OFL 1.1 (czcionki)', 'Czcionki ikon. [link](https://github.com/FortAwesome/Font-Awesome)'),
        ('Bootstrap-3-Typeahead', '4.0.2', 'Apache-2.0', 'Podpowiedzi dla Bootstrap 3. [link](https://github.com/bassjobsen/Bootstrap-3-Typeahead)'),
        ('Swagger UI (webjar `org.webjars:swagger-ui`)', '5.32.0', 'Apache-2.0', 'Dokumentacja REST API. [link](https://github.com/swagger-api/swagger-ui)'),
    ],
}


def simple_table(head, rs):
    out = ['| ' + ' | '.join(head) + ' |', '|' + '---|' * len(head)]
    for r in rs:
        out.append('| ' + ' | '.join(r) + ' |')
    return '\n'.join(out)


def fm(title, label, pos, tags='[license, mercury, hgdb]'):
    return '---\ntitle: %s\nsidebar_label: %s\nsidebar_position: %d\nauthors: [slawas]\ntags: %s\n---\n\n' % (title, label, pos, tags)


def fix_sections(t):
    t = re.sub(r'\*\*(§\s*\d+)\s*\.?\s*\*\*\n\n\*\*([^\n]+?)\*\*', lambda m: '### %s. %s' % (re.sub(r'\s+', ' ', m.group(1)), m.group(2)), t)
    return t


def write(lang, name, content):
    base = OUT if lang == 'en' else OUT + '_pl'
    d = os.path.join(base, '003_Licenses')
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, name), 'w', encoding='utf-8', newline='\n') as f:
        f.write(content)


for lang in ('en', 'pl'):
    S = STR[lang]
    # indeks
    write(lang, 'index.mdx', fm(S['idx_title'], S['idx_title'], 4) + S['idx_text'] + '\n')
    # OWLK
    owlk = fix_sections(update_owlk(read('owlk_%s.mdx.txt' % lang), lang))
    write(lang, 'OWLK.mdx', fm(S['owlk_title'], S['owlk_title'], 1) + owlk + '\n')
    # załącznik 1
    a1 = [S['a1_intro'], '', S['a1_note'], '']
    a1 += ['## ' + S['tools_h'], '', simple_table(S['head'], [(esc(a), esc(b), esc(c), d) for a, b, c, d in TOOLS[lang]]), '']
    a1 += ['## ' + S['libs_h'], '', S['libs_p'], '', table([r for r in LIB if r['katalog'] != 'jdbcdrivers'], S['head_lib']), '']
    a1 += ['## ' + S['jdbc_h'], '', S['jdbc_p'], '', table([r for r in LIB if r['katalog'] == 'jdbcdrivers'], S['head_lib']), '']
    a1 += ['## ' + S['web_h'], '', simple_table(S['head'], [(esc(a), esc(b), esc(c), d) for a, b, c, d in WEBLIBS[lang]]), '']
    a1 += ['## ' + S['sum_h'], '', '| ' + ' | '.join(S['sum_head']) + ' |', '|---|---|---|'] + summary(LIB) + ['']
    write(lang, 'Annex_1_Third_Party_Software.mdx', fm(S['a1_title'], S['a1_title'], 2) + '\n'.join(a1) + '\n')
    # załącznik 2
    a2 = []
    a2.append(fix_sections(read('annex2_%s.mdx.txt' % lang)).strip())
    a2 += ['', '## ' + S['poi_h'], '', S['poi_p'], '', table(POI, S['head_lib']), '']
    write(lang, 'Annex_2_Iron_POI_Server_OEM_License.mdx', fm(S['a2_title'], S['a2_title'], 3) + '\n'.join(a2) + '\n')

print('LIB (osoby trzecie):', len(LIB), 'POI:', len(POI))
