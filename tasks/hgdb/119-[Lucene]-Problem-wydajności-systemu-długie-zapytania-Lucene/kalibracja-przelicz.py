# -*- coding: utf-8 -*-
import csv, glob, os, re
d = r'D:\workspace\git\mercury-intelliJ-workspace\tasks\hgdb\119-[Lucene]-Problem-wydajności-systemu-długie-zapytania-Lucene'
rows = []
for f in sorted(glob.glob(glob.escape(d) + r'\w[347]-kalibracja-*.csv')):
    m = re.match(r'w(\d)-kalibracja-(.+)\.csv', os.path.basename(f))
    stage, ratio = m.group(1), float(m.group(2))
    n = ok = ok2 = 0
    tot = 0
    regs = []
    for r in csv.reader(open(f, encoding='utf-8'), delimiter=';'):
        c, rf, no = [float(r[i]) if r[i] != '' else 1e12 for i in (4, 6, 8)]
        if c >= 1e12:
            print('brak czasu cost:', f, r[0])
            continue
        best = max(1.0, min(c, rf, no))
        reg = c / best
        n += 1
        tot += c
        regs.append(reg)
        if reg <= 1.25 or c - best <= 100:
            ok += 1
        if reg <= 2 or c - best <= 500:
            ok2 += 1
    regs.sort()
    rows.append((stage, ratio, n, ok, ok2, tot / 1000.0, regs[len(regs) // 2], max(regs)))
for x in sorted(rows):
    print('W%s ratio %-5s n=%d kryterium=%d drugi próg=%d suma=%.1f s mediana żalu=%.2f max=%.2f' % x)
