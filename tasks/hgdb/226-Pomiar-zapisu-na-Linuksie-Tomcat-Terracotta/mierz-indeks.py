#!/usr/bin/env python3
"""Pomiar opóźnienia propagacji zmiany do indeksów Lucene węzłów klastra: zadanie 226.

Wstawia nową sprawę (kopię sprawy wzorcowej, np. FSMServiceOrder) przez REST na węźle zapisującym i mierzy, po ilu ms od
końca odpowiedzi na zapis sprawa pojawia się w LOKALNYM indeksie Lucene każdego węzła (searchByLuceneId, odpytywanie bez
przerwy na trwałych połączeniach). Wynik osobno dla węzła zapisującego i dla pozostałych: tak widać opóźnienie
propagacji (zdarzenie o zmianie kolejki, praca sekretarza, przekazanie dokumentów, odświeżenie indeksu).

Użycie (sekret klienta OAuth z 02-init-ldap-tables.sql, nie zapisuj go w repozytorium):
  CLIENT_SECRET=... python mierz-indeks.py --nodes host:28080,host:28081,host:28082 --writer 1 --case FSMServiceOrder.2699 --label A1

Argumenty: --n 35 pomiarów, --warm 5 rozgrzewkowych, --timeout 30 s na pojawienie się sprawy, --keep nie usuwaj nowych spraw.
Uwaga: czas jest z maszyny klienta; rozdzielczość to ok. czas jednego żądania (ok. 20 ms) i jest ograniczona opóźnieniem sieci.
"""
import argparse, http.client, json, os, statistics, sys, threading, time, urllib.parse


class Node:
    def __init__(self, addr):
        self.addr = addr
        host, port = addr.split(":")
        self.host, self.port = host, int(port)
        self.local = threading.local()

    def conn(self):
        c = getattr(self.local, "c", None)
        if c is None:
            c = http.client.HTTPConnection(self.host, self.port, timeout=60)
            self.local.c = c
        return c

    def post(self, path, body, token=None, raw=False):
        data = body if isinstance(body, (bytes, str)) else json.dumps(body, ensure_ascii=False)
        if isinstance(data, str):
            data = data.encode("utf-8")
        headers = {"Content-Type": "application/json;charset=UTF-8"}
        if token:
            headers["Authorization"] = "Bearer " + token
        for attempt in (0, 1):
            try:
                c = self.conn()
                c.request("POST", path, data, headers)
                r = c.getresponse()
                out = r.read()
                return r.status, out
            except (http.client.HTTPException, OSError):
                self.local.c = None
                if attempt:
                    raise


def token(node, secret):
    form = urllib.parse.urlencode({"grant_type": "password", "username": "admin", "password": "admin",
                                   "scope": "mrc-user,mrc-sysadmin", "client_id": "GIUSoapUIClient",
                                   "client_secret": secret}).encode()
    c = http.client.HTTPConnection(node.host, node.port, timeout=30)
    c.request("POST", "/mercury-ws-app/rest/token", form, {"Content-Type": "application/x-www-form-urlencoded"})
    out = json.loads(c.getresponse().read())
    return out["access_token"]


def pct(v, p):
    v = sorted(v)
    return v[min(len(v) - 1, int(len(v) * p + 0.9999) - 1)] if v else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--nodes", required=True)
    ap.add_argument("--writer", type=int, default=2, help="numer węzła zapisującego (1..n), domyślnie 2")
    ap.add_argument("--case", required=True)
    ap.add_argument("--label", default="pomiar")
    ap.add_argument("--n", type=int, default=35)
    ap.add_argument("--warm", type=int, default=5)
    ap.add_argument("--timeout", type=float, default=30.0)
    ap.add_argument("--keep", action="store_true")
    ap.add_argument("--batch", type=int, default=1, help="liczba spraw wstawianych naraz w jednym pomiarze")
    ap.add_argument("--threads", type=int, default=8, help="liczba równoległych zapisów w paczce (na każdy piszący węzeł)")
    ap.add_argument("--all-writers", action="store_true", help="tryb paczki: zapisy jednocześnie na wszystkich węzłach (batch spraw na każdy)")
    ap.add_argument("--cpu", action="store_true", help="tryb paczki: zmierz zużycie CPU hosta (NodeMonitorRest) w oknie serii; bez kontroli kompletności i z rzadszym odpytywaniem")
    ap.add_argument("--cpu-baseline", type=float, default=30.0, help="czas pomiaru bazowego CPU bez obciążenia, s (przed serią)")
    a = ap.parse_args()
    secret = os.environ["CLIENT_SECRET"]
    nodes = [Node(x) for x in a.nodes.split(",")]
    writer = nodes[a.writer - 1]
    tok = token(writer, secret)
    base = "/mercury-ws-app/rest/service/CaseBusinessRest/"
    ctx = {"userName": "admin", "maxDepth": 8}

    st, out = writer.post(base + "find", {"context": ctx, "id": a.case}, tok)
    template = json.loads(out)["dto"]
    h = template["mrcCaseHeader"]
    for k in ("caseId", "rootVersionId", "previousVersionId", "version", "objectID", "groupId", "typeId"):
        pass

    created = []
    results = {i: [] for i in range(len(nodes))}
    failures = 0

    def new_object(i):
        d = json.loads(json.dumps(template))
        hd = d["mrcCaseHeader"]
        for k in ("caseId", "rootVersionId", "previousVersionId", "version", "objectID", "groupId"):
            hd[k] = None
        hd["modifyComment"] = "Pomiar 226 indeks %s-%s" % (a.label, i)
        return d

    def found(node, case_id):
        st, out = node.post(base + "searchByLuceneId", {"context": {"userName": "admin"}, "caseId": case_id}, tok)
        if st != 200:
            return False
        try:
            o = json.loads(out)
        except ValueError:
            return False
        dto = o.get("dto")
        return bool(dto and (dto.get("mrcCaseHeader") or {}).get("caseId") == case_id)

    print("== %s: węzły %s, zapis na %s, sprawa wzorcowa %s, %d pomiarów po %d rozgrzewkowych, %s" % (
        a.label, a.nodes, writer.addr, a.case, a.n, a.warm, time.strftime("%Y-%m-%d %H:%M")))
    if a.batch > 1:
        from concurrent.futures import ThreadPoolExecutor
        results = {i: [] for i in range(len(nodes))}
        totals = {i: [] for i in range(len(nodes))}
        incomplete = 0

        def cpu_now():
            """Liczniki CPU hosta z NodeMonitorRest (ostatnie bicie serca węzła; liczniki są wspólne dla hosta)."""
            st, out = nodes[0].post("/mercury-ws-app/monitor/NodeMonitorRest/load", {"context": {"userName": "admin"}}, tok)
            dto = json.loads(out).get("dto") or []
            r = {n["nodeName"]: (n["cpuTotalMillis"], n["cpuIdleMillis"]) for n in dto if n.get("cpuTotalMillis")}
            return r

        def cpu_fresh():
            """Czeka na nowy odczyt (kolejne bicie serca), zwraca (total, idle) średnio po węzłach."""
            first = cpu_now()
            while True:
                time.sleep(0.5)
                cur = cpu_now()
                if cur and cur != first:
                    vals = list(cur.values())
                    return (sum(v[0] for v in vals) / len(vals), sum(v[1] for v in vals) / len(vals))

        f0 = None
        if a.cpu:
            b0 = cpu_fresh()
            time.sleep(a.cpu_baseline)
            b1 = cpu_fresh()
            dt, di = b1[0] - b0[0], b1[1] - b0[1]
            f0 = (dt - di) / dt if dt > 0 else 0.0
            print("CPU bazowe hosta bez obciążenia: %.2f%% (okno %.0f core-s)" % (f0 * 100, dt / 1000.0))
        cpu0 = None
        for i in range(1, a.warm + a.n + 1):
            if a.cpu and i == a.warm + 1:
                cpu0 = cpu_fresh()
            ids, lock = [], threading.Lock()
            errors = []
            last_by_writer = {}
            t_start = time.perf_counter()
            writers = nodes if a.all_writers else [writer]

            def one(task):
                w, j = task
                st, out = w.post(base + "save", {"context": {"userName": "admin"},
                                                 "mrcObject": new_object("%d-%s-%d" % (i, w.port, j))}, tok)
                if st != 200:
                    return None
                resp = json.loads(out)
                if not resp.get("dto"):
                    with lock:
                        errors.append("%s: %s %s" % (w.addr, resp.get("errorCode"), (resp.get("errorMessage") or "")[:200]))
                    return None
                cid = resp["dto"]["mrcCaseHeader"]["caseId"]
                with lock:
                    ids.append(cid)
                    created.append(cid)
                    last_by_writer[w.addr] = cid  # ostatnia zakończona sprawa danego węzła
                return cid

            # zapisy wszystkich piszących węzłów idą jednocześnie (naprzemiennie w kolejce zadań)
            tasks = [(w, j) for j in range(a.batch) for w in writers]
            with ThreadPoolExecutor(a.threads * len(writers)) as ex:
                list(ex.map(one, tasks))
            t0 = time.perf_counter()
            if len(ids) != a.batch * len(writers):
                print("UWAGA: paczka %d: zapisano %d z %d; błędy: %s" % (i, len(ids), a.batch * len(writers), errors[:3]))
            lasts = list(last_by_writer.values())
            times = {}

            def poll(idx, node):
                pending = list(lasts)
                while time.perf_counter() - t0 < a.timeout:
                    pending = [c for c in pending if not found(node, c)]
                    if not pending:
                        now = time.perf_counter()
                        times[idx] = ((now - t0) * 1000.0, (now - t_start) * 1000.0)
                        return
                    if a.cpu:
                        time.sleep(0.05)  # rzadsze odpytywanie, by nie zawyżać CPU
                times[idx] = None

            th = [threading.Thread(target=poll, args=(k, n)) for k, n in enumerate(nodes)]
            for t in th:
                t.start()
            for t in th:
                t.join()
            # kontrola kompletności (poza pomiarem czasu): czy wszystkie sprawy paczki są w indeksie każdego węzła
            missing = 0
            if not a.cpu:
                for node in nodes:
                    missing += sum(1 for cid in ids if not found(node, cid))
            if missing:
                incomplete += 1
            if i > a.warm:
                for k in range(len(nodes)):
                    results[k].append(times[k][0] if times.get(k) else None)
                    totals[k].append(times[k][1] if times.get(k) else None)
            time.sleep(1.0)
        cpu_line = None
        if a.cpu and cpu0 is not None:
            cpu1 = cpu_fresh()
            dt, di = cpu1[0] - cpu0[0], cpu1[1] - cpu0[1]
            busy = dt - di
            net = busy - (f0 or 0.0) * dt
            cpu_line = ("CPU hosta w oknie serii: okno %.0f core-s, zajęte %.1f core-s (%.1f%%), netto po odjęciu CPU bazowego %.1f core-s, "
                        "na paczkę %.2f core-s" % (dt / 1000.0, busy / 1000.0, busy / dt * 100 if dt else 0, net / 1000.0, net / 1000.0 / a.n))
            print(cpu_line)
        print("\npaczka %d spraw (%d równoległych zapisów): czas do pojawienia się OSTATNIEJ sprawy w indeksie węzła (ms)" % (a.batch, a.threads))
        print("niekompletnych paczek (w chwili kontroli brakowało spraw): %d" % incomplete)
        print("%-42s %4s %12s %12s %12s" % ("węzeł", "n", "p50 koniec", "p90 koniec", "p50 początek"))
        rows = []
        for k, node in enumerate(nodes):
            vals = [v for v in results[k] if v is not None]
            tv = [v for v in totals[k] if v is not None]
            role = "zapis" if (node is writer or a.all_writers) else "pozostały"
            if vals:
                print("%-42s %4d %12.0f %12.0f %12.0f" % (node.addr + " (" + role + ")", len(vals), statistics.median(vals), pct(vals, 0.9), statistics.median(tv)))
                rows.append("| %s | %d | %s | %d | %.0f | %.0f | %.0f | %.0f | %d |" % (a.label, a.batch, node.addr + " (" + role + ")", len(vals), min(vals), statistics.median(vals), pct(vals, 0.9), max(vals), incomplete))
        print("\n| wariant | paczka | węzeł | n | min | p50 | p90 | max (od końca zapisów, ms) | niekompletne |")
        print("\n".join(rows))
        if not a.keep:
            removed = 0
            for cid in created:
                st, _ = writer.post(base + "remove", {"context": {"userName": "admin"}, "id": cid}, tok)
                removed += st == 200
            print("usunięto %d z %d nowych spraw" % (removed, len(created)))
        sys.exit(0)

    for i in range(1, a.warm + a.n + 1):
        st, out = writer.post(base + "save", {"context": {"userName": "admin"}, "mrcObject": new_object(i)}, tok)
        t0 = time.perf_counter()
        if st != 200:
            print("UWAGA: zapis nr %d: HTTP %d %s" % (i, st, out[:200]))
            failures += 1
            continue
        resp = json.loads(out)
        cid = resp["dto"]["mrcCaseHeader"]["caseId"]
        created.append(cid)
        times = {}

        def poll(idx, node):
            while time.perf_counter() - t0 < a.timeout:
                if found(node, cid):
                    times[idx] = (time.perf_counter() - t0) * 1000.0
                    return
            times[idx] = None

        th = [threading.Thread(target=poll, args=(k, n)) for k, n in enumerate(nodes)]
        for t in th:
            t.start()
        for t in th:
            t.join()
        if i > a.warm:
            for k in range(len(nodes)):
                results[k].append(times.get(k))
        # krótka przerwa, by poprzednie zmiany nie nakładały się na kolejną
        time.sleep(0.5)

    print("\nczas od końca odpowiedzi na zapis do pojawienia się w indeksie węzła (ms):")
    print("%-18s %4s %6s %6s %6s %6s %s" % ("węzeł", "n", "min", "p50", "p90", "max", "brak"))
    rows = []
    for k, node in enumerate(nodes):
        vals = [v for v in results[k] if v is not None]
        miss = len([v for v in results[k] if v is None])
        role = "zapis" if node is writer else "pozostały"
        if vals:
            line = (node.addr + " (" + role + ")", len(vals), min(vals), statistics.median(vals), pct(vals, 0.9), max(vals), miss)
            print("%-18s %4d %6.0f %6.0f %6.0f %6.0f %d" % line)
            rows.append("| %s | %s | %d | %.0f | %.0f | %.0f | %.0f | %d |" % (a.label, line[0], line[1], line[2], line[3], line[4], line[5], miss))
        else:
            print("%-18s brak wyników (%d bez pojawienia się)" % (node.addr, miss))
    print("\n| wariant | węzeł | n | min | p50 | p90 | max | brak |   (ms)")
    print("\n".join(rows))

    if not a.keep:
        removed = 0
        for cid in created:
            st, _ = writer.post(base + "remove", {"context": {"userName": "admin"}, "id": cid}, tok)
            removed += st == 200
        print("usunięto %d z %d nowych spraw" % (removed, len(created)))
    sys.exit(0 if not failures else 1)


if __name__ == "__main__":
    main()
