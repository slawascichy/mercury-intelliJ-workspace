import zipfile, re, sys, io, xml.etree.ElementTree as ET

W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'


def q(n):
    return W + n


def load(path):
    z = zipfile.ZipFile(path)
    doc = ET.fromstring(z.read('word/document.xml'))
    num = ET.fromstring(z.read('word/numbering.xml')) if 'word/numbering.xml' in z.namelist() else None
    sty = ET.fromstring(z.read('word/styles.xml')) if 'word/styles.xml' in z.namelist() else None
    return doc, num, sty


def roman(k):
    r = ''
    for v, s in ((1000, 'm'), (900, 'cm'), (500, 'd'), (400, 'cd'), (100, 'c'), (90, 'xc'), (50, 'l'), (40, 'xl'),
                 (10, 'x'), (9, 'ix'), (5, 'v'), (4, 'iv'), (1, 'i')):
        while k >= v:
            r += s
            k -= v
    return r


def fmt_num(n, f):
    if f == 'decimal':
        return str(n)
    if f == 'decimalZero':
        return '%02d' % n
    if f == 'lowerLetter':
        return chr(ord('a') + (n - 1) % 26) * (1 + (n - 1) // 26)
    if f == 'upperLetter':
        return chr(ord('A') + (n - 1) % 26) * (1 + (n - 1) // 26)
    if f == 'lowerRoman':
        return roman(n)
    if f == 'upperRoman':
        return roman(n).upper()
    return str(n)


class Numbering:
    def __init__(self, num, sty):
        self.abs = {}
        self.nums = {}
        self.counters = {}
        self.style_num = {}
        self.lvl_left = {}
        if num is not None:
            for a in num.findall(q('abstractNum')):
                lv = {}
                for l in a.findall(q('lvl')):
                    i = int(l.get(q('ilvl')))
                    fmt = l.find(q('numFmt'))
                    txt = l.find(q('lvlText'))
                    st = l.find(q('start'))
                    lv[i] = (fmt.get(q('val')) if fmt is not None else 'decimal',
                             txt.get(q('val')) if txt is not None else '',
                             int(st.get(q('val'))) if st is not None else 1)
                    pp = l.find(q('pPr'))
                    ind = pp.find(q('ind')) if pp is not None else None
                    if ind is not None:
                        v = ind.get(q('left')) or ind.get(q('start'))
                        if v:
                            self.lvl_left[(a.get(q('abstractNumId')), i)] = int(v)
                self.abs[a.get(q('abstractNumId'))] = lv
            for n in num.findall(q('num')):
                aid = n.find(q('abstractNumId')).get(q('val'))
                over = {}
                for o in n.findall(q('lvlOverride')):
                    s = o.find(q('startOverride'))
                    if s is not None:
                        over[int(o.get(q('ilvl')))] = int(s.get(q('val')))
                self.nums[n.get(q('numId'))] = (aid, over)
        if sty is not None:
            for s in sty.findall(q('style')):
                ppr = s.find(q('pPr'))
                if ppr is not None:
                    np_ = ppr.find(q('numPr'))
                    if np_ is not None:
                        nid = np_.find(q('numId'))
                        il = np_.find(q('ilvl'))
                        if nid is not None:
                            self.style_num[s.get(q('styleId'))] = (nid.get(q('val')),
                                                                   int(il.get(q('val'))) if il is not None else 0)

    def left(self, numid, ilvl):
        if numid not in self.nums:
            return None
        return self.lvl_left.get((self.nums[numid][0], ilvl))

    def label(self, numid, ilvl):
        if numid not in self.nums:
            return None
        aid, over = self.nums[numid]
        lv = self.abs.get(aid, {})
        if ilvl not in lv:
            return None
        fmt, txt, st = lv[ilvl]
        if fmt == 'bullet':
            return '-'
        key = (aid, numid)
        c = self.counters.setdefault(key, {})
        start = over.get(ilvl, st)
        c[ilvl] = c.get(ilvl, start - 1) + 1
        for k in list(c):
            if k > ilvl:
                del c[k]

        def rep(m):
            lvl = int(m.group(1)) - 1
            f2 = lv.get(lvl, ('decimal', '', 1))[0]
            val = c.get(lvl, lv.get(lvl, ('decimal', '', 1))[2])
            return fmt_num(val, f2)

        return re.sub(r'%(\d)', rep, txt)


ESC = {'{': '&#123;', '}': '&#125;', '<': '&lt;', '>': '&gt;'}


def esc(t):
    t = ''.join(ESC.get(ch, ch) for ch in t)
    t = t.replace('\\', '\\\\').replace('*', '\\*').replace('_', '\\_').replace('`', '\\`')
    t = t.replace('[', '\\[').replace(']', '\\]')
    return t


def run_text(r):
    out = ''
    for ch in r:
        if ch.tag == q('t'):
            out += ch.text or ''
        elif ch.tag == q('tab'):
            out += ' '
        elif ch.tag == q('br'):
            out += '\n'
        elif ch.tag == q('noBreakHyphen'):
            out += '-'
    return out


def para_text(p):
    parts = []
    for r in p.iter(q('r')):
        t = run_text(r)
        if not t:
            continue
        rpr = r.find(q('rPr'))
        b = False
        if rpr is not None and rpr.find(q('b')) is not None:
            b = rpr.find(q('b')).get(q('val')) not in ('0', 'false')
        parts.append((b, t))
    merged = []
    for b, t in parts:
        if merged and merged[-1][0] == b:
            merged[-1] = (b, merged[-1][1] + t)
        else:
            merged.append((b, t))
    s = ''
    for b, t in merged:
        if b and t.strip():
            lead = t[:len(t) - len(t.lstrip())]
            trail = t[len(t.rstrip()):]
            s += lead + '**' + esc(t.strip()).replace('\n', ' ') + '**' + trail
        else:
            s += esc(t).replace('\n', '  \n')
    return s.strip()


def convert(path, skip_until=None, stop_at=None):
    doc, num, sty = load(path)
    N = Numbering(num, sty)
    body = doc.find(q('body'))
    out = []
    started = skip_until is None
    stopped = False
    run = {'base': None, 'prev': -1}
    for el in body:
        if stopped:
            break
        if el.tag == q('p'):
            ppr = el.find(q('pPr'))
            style = ''
            numid = None
            ilvl = 0
            if ppr is not None:
                ps = ppr.find(q('pStyle'))
                style = ps.get(q('val')) if ps is not None else ''
                npr = ppr.find(q('numPr'))
                if npr is not None:
                    n = npr.find(q('numId'))
                    if n is not None:
                        numid = n.get(q('val'))
                    il = npr.find(q('ilvl'))
                    if il is not None:
                        ilvl = int(il.get(q('val')))
            if numid is None and style in N.style_num:
                numid, ilvl = N.style_num[style]
            txt = para_text(el)
            if not txt:
                continue
            if re.match(r'^(TOC|Spis tre)', txt) or style.lower().startswith(('toc', 'spis')):
                continue
            if not started:
                if skip_until and skip_until in txt:
                    started = True
                else:
                    continue
            if stop_at and stop_at in txt:
                stopped = True
                break
            sl = style.lower()
            m = re.match(r'^(heading|nag[^0-9]*)\s*([0-9])', sl)
            if numid == '0':
                numid = None
            left_p = None
            if ppr is not None and ppr.find(q('ind')) is not None:
                v = ppr.find(q('ind')).get(q('left')) or ppr.find(q('ind')).get(q('start'))
                left_p = int(v) if v else None
            if m:
                run['base'] = None
                run['prev'] = -1
                lvl = min(int(m.group(2)) + 1, 5)
                lab = N.label(numid, ilvl) if numid else None
                prefix = (lab + ' ') if lab and lab != '-' else ''
                out.append('\n' + '#' * lvl + ' ' + prefix + txt + '\n')
                continue
            if sl in ('title', 'tytu'):
                run['base'] = None
                run['prev'] = -1
                out.append('\n## ' + txt + '\n')
                continue
            if numid:
                lab = N.label(numid, ilvl)
                left = left_p if left_p is not None else N.left(numid, ilvl)
                if left is None:
                    left = 720 * (ilvl + 1)
                if run['base'] is None:
                    run['base'] = left
                    depth = 0
                else:
                    depth = max(0, int(round((left - run['base']) / 720.0)))
                    depth = min(depth, run['prev'] + 1)
                run['prev'] = depth
                indent = '    ' * depth
                if lab == '-':
                    out.append(indent + '- ' + txt + '\n')
                elif lab and re.match(r'^[0-9]+[.)]$', lab):
                    out.append(indent + lab + ' ' + txt + '\n')
                elif lab:
                    out.append(indent + '- ' + lab + ' ' + txt + '\n')
                else:
                    out.append(indent + txt + '\n')
            elif run['prev'] >= 0 and left_p is not None and left_p >= 700:
                # akapit z wcięciem zaraz po pozycji listy: ciąg dalszy tej pozycji
                out.append('    ' * (run['prev'] + 1) + txt + '\n')
            else:
                run['base'] = None
                run['prev'] = -1
                out.append(txt + '\n')
        elif el.tag == q('tbl') and started:
            run['base'] = None
            run['prev'] = -1
            rows = []
            for tr in el.findall(q('tr')):
                cells = []
                for tc in tr.findall(q('tc')):
                    cells.append(' '.join(x for x in (para_text(p) for p in tc.findall(q('p'))) if x).replace('|', '&#124;'))
                rows.append(cells)
            if rows:
                w = max(len(r) for r in rows)
                out.append('\n| ' + ' | '.join(rows[0] + [''] * (w - len(rows[0]))) + ' |')
                out.append('|' + '---|' * w)
                for r in rows[1:]:
                    out.append('| ' + ' | '.join(r + [''] * (w - len(r))) + ' |')
                out.append('')
    return '\n'.join(out)


if __name__ == '__main__':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    su = sys.argv[2] if len(sys.argv) > 2 and sys.argv[2] != '-' else None
    sa = sys.argv[3] if len(sys.argv) > 3 else None
    print(convert(sys.argv[1], su, sa))
