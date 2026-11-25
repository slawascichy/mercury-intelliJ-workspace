import os, re, sys, csv, zipfile, xml.etree.ElementTree as ET
M2 = r'D:\workspace\.m2\repository'
REL = r'D:\workspace\git\mercury-cmd\mercury-install-package\releases\mercury-install-package-3.0.4.45'
OUT = sys.argv[1]
# indeks: nazwa pliku jar -> lista ścieżek w .m2
idx = {}
for root, dirs, files in os.walk(M2):
    for f in files:
        if f.endswith('.jar') and not f.endswith('-sources.jar') and not f.endswith('-javadoc.jar'):
            idx.setdefault(f, []).append(os.path.join(root, f))
jars = []
for d in ('lib', 'libExt', 'lib20', 'jdbcdrivers'):
    p = os.path.join(REL, d)
    for f in sorted(os.listdir(p)):
        if f.endswith('.jar'):
            jars.append((d, f))
for war in ('mercury-ws-app.war',):
    z = zipfile.ZipFile(os.path.join(REL, 'installableApps', war))
    for n in z.namelist():
        if n.startswith('WEB-INF/lib/') and n.endswith('.jar'):
            jars.append(('war:' + war, os.path.basename(n)))
NS = {'p': 'http://maven.apache.org/POM/4.0.0'}
def strip(tag): return tag.split('}')[-1]
def parse_pom(path):
    try:
        t = ET.parse(path).getroot()
    except Exception:
        return None
    def txt(el, name):
        for c in el:
            if strip(c.tag) == name: return (c.text or '').strip()
        return ''
    info = {'lic': [], 'url': txt(t, 'url'), 'scm': '', 'parent': None, 'name': txt(t, 'name'), 'desc': txt(t, 'description')}
    for c in t:
        n = strip(c.tag)
        if n == 'licenses':
            for l in c:
                info['lic'].append(txt(l, 'name') or txt(l, 'url'))
        elif n == 'scm':
            info['scm'] = txt(c, 'url')
        elif n == 'parent':
            info['parent'] = (txt(c, 'groupId'), txt(c, 'artifactId'), txt(c, 'version'))
    return info
def pom_path(g, a, v):
    return os.path.join(M2, *g.split('.'), a, v, '%s-%s.pom' % (a, v))
def resolve(path_jar):
    pom = path_jar[:-4] + '.pom'
    seen = 0
    info = parse_pom(pom) if os.path.exists(pom) else None
    lic, url, scm, name, desc = [], '', '', '', ''
    cur = info
    while cur is not None and seen < 6:
        if not lic and cur['lic']: lic = cur['lic']
        if not url and cur['url']: url = cur['url']
        if not scm and cur['scm']: scm = cur['scm']
        if not name and cur['name']: name = cur['name']
        if not desc and cur['desc']: desc = cur['desc']
        par = cur['parent']
        if not par: break
        pp = pom_path(*par)
        cur = parse_pom(pp) if os.path.exists(pp) else None
        seen += 1
    return lic, url, scm, name, desc
rows = []
for d, f in jars:
    base = f[:-4]
    cands = idx.get(f, [])
    if cands:
        p = cands[0]
        rel = os.path.relpath(p, M2).split(os.sep)
        ver, art, grp = rel[-2], rel[-3], '.'.join(rel[:-3])
        lic, url, scm, name, desc = resolve(p)
        rows.append((d, f, grp + ':' + art, ver, '; '.join(dict.fromkeys(lic)), url, scm, name, re.sub(r'\s+', ' ', desc)[:160]))
    else:
        rows.append((d, f, '', '', '', '', '', '', ''))
with open(OUT, 'w', newline='', encoding='utf-8') as fh:
    w = csv.writer(fh, delimiter=';')
    w.writerow(['katalog', 'plik', 'groupId:artifactId', 'wersja', 'licencja_z_pom', 'url', 'scm', 'nazwa', 'opis'])
    w.writerows(rows)
print('jary:', len(rows), 'bez .m2:', sum(1 for r in rows if not r[2]), 'bez licencji:', sum(1 for r in rows if r[2] and not r[4]))
