# -*- coding: utf-8 -*-
"""PoC W9: pulpit Grafany (6 paneli) w OpenSearch dla 1/4/8 klientów; p50/p95 paneli i czas odświeżenia pulpitu."""
import json, sys, time, threading, statistics
sys.path.insert(0, '.')
from queries import post, addr, fso, rng, nested, SORT, TZ

PANELS = [
    ('P1 miesiąc FSO 365d', {'query': fso(rng(365)), 'aggs': {'g': {'date_histogram': {'field': 'createDate', 'calendar_interval': 'month', 'time_zone': TZ, 'min_doc_count': 1}}}}),
    ('P2 dzień FSO 30d', {'query': fso(rng(30)), 'aggs': {'g': {'date_histogram': {'field': 'createDate', 'calendar_interval': 'day', 'time_zone': TZ, 'min_doc_count': 1}}}}),
    ('P3 miasto adresów 365d', {'query': addr({'term': {'status': 'a'}}, rng(365)), 'aggs': {'g': {'terms': {'field': 'city', 'size': 10000}}}}),
    ('P4 suma ceny FSO 7d', {'query': fso(rng(7)), 'aggs': {'g': {'date_histogram': {'field': 'createDate', 'calendar_interval': 'day', 'time_zone': TZ, 'min_doc_count': 1}, 'aggs': {'s': {'sum': {'field': 'price'}}}}}}),
    ('P5 tabela Poznań+Rfs', {'query': addr({'term': {'city': 'poznań'}}, nested('slmapprfs')), 'sort': SORT}),
    ('P6 tabela Leszno+Vrf', {'query': addr({'term': {'city': 'leszno'}}, nested('slmappvrf')), 'sort': SORT}),
]


def client(shift, rounds, out, go):
    go.wait()
    for r in range(rounds):
        d0 = time.time()
        for k in range(len(PANELS)):
            name, body = PANELS[(k + shift) % len(PANELS)]
            t0 = time.time()
            post(body)
            out.append((name, (time.time() - t0) * 1000))
        out.append(('PULPIT', (time.time() - d0) * 1000))


def pct(v, p):
    v = sorted(v)
    return v[max(0, min(len(v) - 1, int(-(-p * len(v) // 1)) - 1))]


if __name__ == '__main__':
    rounds = 3
    for _ in range(2):
        for name, body in PANELS:
            post(body)  # rozgrzewka
    rows = {}
    for clients in (1, 4, 8):
        out, go, ths = [], threading.Event(), []
        for c in range(clients):
            t = threading.Thread(target=client, args=(c, rounds, out, go))
            t.start()
            ths.append(t)
        w0 = time.time()
        go.set()
        for t in ths:
            t.join()
        wall = (time.time() - w0) * 1000
        for name in [p[0] for p in PANELS] + ['PULPIT']:
            v = [x[1] for x in out if x[0] == name]
            rows[(clients, name)] = (statistics.median(v), pct(v, 0.95), max(v))
        rows[(clients, 'wall')] = wall
    for name in [p[0] for p in PANELS] + ['PULPIT']:
        print('%-26s' % name + ''.join('| %dkl p95 %6.0f ' % (c, rows[(c, name)][1]) for c in (1, 4, 8)))
    print({c: round(rows[(c, 'wall')]) for c in (1, 4, 8)})
