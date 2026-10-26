# -*- coding: utf-8 -*-
"""PoC W9: 10 zapytań z bazy W0 w OpenSearch; czas serwera i całkowity, liczba trafień wobec Mercury."""
import json, sys, time, statistics, urllib.request

URL = sys.argv[1] if len(sys.argv) > 1 else 'http://127.0.0.1:9200/mrc'
RUNS = int(sys.argv[2]) if len(sys.argv) > 2 else 7
END = 1554100481773
DAY = 24 * 3600 * 1000
TZ = 'Europe/Warsaw'


def nested(status, st=None):
    f = [{'term': {'appMobile.status': status}}]
    if st:
        f.append({'term': {'appMobile.st': st}})
    return {'nested': {'path': 'appMobile', 'query': {'bool': {'filter': f}}}}


def addr(*extra):
    return {'bool': {'filter': [{'term': {'type': 'slmaddress'}}] + list(extra)}}


def fso(*extra):
    return {'bool': {'filter': [{'term': {'type': 'fsmserviceorder'}}, {'term': {'status': 'a'}}] + list(extra)}}


def rng(days):
    return {'range': {'createDate': {'gte': END - days * DAY}}}


SORT = [{'createDate': 'asc'}]
Q = [
    # (nazwa, treść, oczekiwane trafienia lub grupy w Mercury, oznaczenie czy liczymy buckets)
    ('adres Poznań + Mts (benchmark)', {'query': addr({'term': {'city': 'poznań'}}, nested('slmappmts', 'a')), 'sort': SORT}, 89896, 'hits'),
    ('adres 365 dni + Mts', {'query': addr(rng(365), nested('slmappmts', 'a')), 'sort': SORT}, 204122, 'hits'),
    ('adres 30 dni + Mts', {'query': addr(rng(30), nested('slmappmts', 'a')), 'sort': SORT}, 1414, 'hits'),
    ('adres Poznań + Rfs', {'query': addr({'term': {'city': 'poznań'}}, nested('slmapprfs')), 'sort': SORT}, 14177, 'hits'),
    ('adres Leszno + Vrf', {'query': addr({'term': {'city': 'leszno'}}, nested('slmappvrf')), 'sort': SORT}, 73, 'hits'),
    ('FSO 365 dni (lista)', {'query': fso(rng(365)), 'sort': SORT}, 34964, 'hits'),
    ('FSO 7 dni (lista)', {'query': fso(rng(7)), 'sort': SORT}, 3426, 'hits'),
    ('groupBy(miesiąc) FSO', {'query': fso(), 'aggs': {'g': {'date_histogram': {'field': 'createDate', 'calendar_interval': 'month', 'time_zone': TZ, 'min_doc_count': 1}}}}, 16, 'buckets'),
    ('groupBy(city) SlmAddress', {'query': addr({'term': {'status': 'a'}}), 'aggs': {'g': {'terms': {'field': 'city', 'size': 10000}}}}, 105, 'buckets'),
    ('groupBy(price, dzień)', {'query': {'range': {'price': {'gte': 0}}}, 'aggs': {'g': {'date_histogram': {'field': 'createDate', 'calendar_interval': 'day', 'time_zone': TZ, 'min_doc_count': 1}, 'aggs': {'s': {'stats': {'field': 'price'}}}}}}, 340, 'buckets'),
]


def post(body):
    body = dict(body)
    body['size'] = body.get('size', 60) if 'aggs' not in body else 0
    body['track_total_hits'] = True
    data = json.dumps(body).encode('utf-8')
    req = urllib.request.Request(URL + '/_search?request_cache=false', data=data, headers={'Content-Type': 'application/json'})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=600) as r:
        resp = json.loads(r.read().decode('utf-8'))
    return resp, (time.time() - t0) * 1000


if __name__ == '__main__':
    out = []
    for name, body, expected, kind in Q:
        times, took = [], []
        resp = None
        for i in range(RUNS):
            resp, wall = post(body)
            times.append(wall)
            took.append(resp['took'])
        total = resp['hits']['total']['value']
        buckets = len(resp['aggregations']['g']['buckets']) if 'aggregations' in resp else None
        got = buckets if kind == 'buckets' else total
        ok = 'ZGODNE' if got == expected else 'RÓŻNE'
        best = min(times)
        print('%-34s trafień %7d grup %-5s oczekiwane %7d %s | najlepszy %7.0f ms, mediana %7.0f ms (took %s)' % (
            name, total, buckets, expected, ok, best, statistics.median(times), min(took)))
        out.append((name, total, buckets, expected, ok, round(best), round(statistics.median(times))))
    json.dump(out, open('queries-result.json', 'w'), ensure_ascii=False)
