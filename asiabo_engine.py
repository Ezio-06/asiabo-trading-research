"""
asiabo_engine.py  --  the POCKET ENGINE, stage 1 (2026-10-10): ideal and nightmare worlds for the states we already have
theories for, so the engine first proves it can CONFIRM a known cause before it is trusted to discover new ones.

Idea (Ezio, 2026-10-10): if a lane really works BECAUSE of some market state, a world with MORE of that state (ideal)
must make it better and a world with LESS of it (nightmare) must make it worse. If the ideal world does not do better
and the nightmare world does not do worse, what we detected is noise or a quirk of the real ORDER of days.
Stage 2 (later): the hunt -- search the per-trade tables for pockets, then hand each pocket to these worlds.

What it does: builds cousin histories with make_synth (only the 4 book markets), each one moved along ONE dial from
nightmare to ideal, runs brk / ins / fast / dip on each (the lab's own lanes and one-position rule, through
asiabo_why), and measures how each part's EDGE (net R minus the coin-flip average = cost-free direction value) moves
along the dial. Every world is built with 2 seeds; a dial's worlds of the same seed share the same block schedule
(PAIRED: same shuffled history, only the dial differs), and every t is clustered by seed x market x month.

    python asiabo_engine.py                 run every world that is not done yet (resumable), then the report
    python asiabo_engine.py --seeds 3       more seeds;  --dims persist,order,vol  only some dials;  --workers N
    python asiabo_engine.py report          the report only, from the worlds already measured
    python asiabo_engine.py measure [--db x.db] --out y.json     (internal: one world)

Results: reports/engine/worlds/*.json (one per world, kept), the report in reports/engine_<date>/ and claude vision.
Memory and speed: each world is built and measured in its own process, as many in parallel as the free memory, cores and
disk allow (synth_batch's rule); the synthetic database (~1 GB, 4 markets) is deleted as soon as it is measured; the
source bars are read from synth/cache (memory-mapped) when it is up to date.

=====================================================================================================================
THE DIALS AND THE PREDICTIONS -- written 2026-10-10 BEFORE any engine world was measured
=====================================================================================================================
D1  MOMENTUM vs SNAP-BACK  (make_synth --persist k on a 2-6 week reshuffle; k = +1.5, +0.5, 0, -0.2, -0.4)
    (ladder set from WORLD statistics only, before any lane ran: on gold the 20-day variance ratio goes about
    0.68 / 0.76 / ~0.9 / 1.28 / ~2; snap-back saturates near 0.65, momentum does not, so the steps are uneven in k)
    nightmare for trend riders = snap-back (every move overshoots and is pulled back), ideal = momentum (moves keep
    going over the following weeks). The dial bends the SAME shuffled history; no drift is added.
      brk   +   rides multi-day follow-through (T1, T4)
      fast  +   filter-agreed intraday breakouts; weaker than brk (its filters looked decorative in the why phase)
      dip   -   a snap-back buyer: momentum worlds should HURT it, snap-back worlds help (the sharpest test here)
      ins   0   decided inside one day on a compression break; bending multi-day persistence should not matter much
D2  TREND LENGTH / DAY ORDER  (dayshuffle -> shuffle 2-6 weeks -> longblock 8-26 weeks)
    nightmare = days in random order (no multi-day structure at all), ideal = long stretches of real history kept.
    NOT independent of earlier work: batch 1 and the why phase already saw dayshuffle. Listed for completeness.
      brk   +   its money is multi-month trends (T4, longblock)
      fast  0   intraday (same edge on dayshuffle in the why phase)
      dip   +   the snap-back is a multi-day sequence; mostly the first step (dayshuffle -> shuffle)
      ins   +   inside days are day-to-day compression structure (T14 revised: dies on dayshuffle)
D3  VOLATILITY LEVEL  (make_synth --vol v on a 2-6 week reshuffle; v = 0.60, 0.80, 1.00, 1.25, 1.60)
    every move scaled; costs are not. The lanes work in daily ATRs, so the cost-free EDGE should not care:
      brk / ins / fast / dip   edge 0;  NET R +  (fixed costs become a smaller share of a bigger R), steepest for
                               the short holds (ins, fast) -- the cost theory T3 seen from the other side.
dipx  (added 2026-10-10 after the cloud random-walk test, BEFORE any real world was measured): the LOOSE dip --
      every day with RSI(2) < 30 and every 2+ down-close streak above the 200-day average, US500 / Germany 40,
      overlapping trades allowed, the same exits. About 6x dip's trades, so the dip MECHANISM can be read with power
      (dip itself has ~150 trades a world: the planted snap-back on the random walk gave t -0.4). Same predictions as
      dip on every dial: D1 -, D2 +, D3 edge 0 / net +.
VERDICTS (fixed now): slope of edge per dial step, pooled over seeds, clustered t.
    predicted + or -:  CONFIRMED  right sign and |t| >= 3     SUPPORTED  right sign, 2 <= |t| < 3
                       NOT SHOWN  |t| < 2                      CONTRADICTED  wrong sign and |t| >= 2
    predicted 0:       CONSISTENT |t| < 2    UNCLEAR 2 <= |t| < 3    CONTRADICTED |t| >= 3
=====================================================================================================================
"""
import os, sys, json, math, time, glob, shutil, subprocess, traceback
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import asiabo_offline as A

PARTS = ("brk", "ins", "fast", "dip", "dipx")
ERAS = ["2014-17", "2018-19", "A 2020-21", "B 2024+"]
GROUPS = (("ALL", tuple(ERAS)), ("OLD 2014-21", ("2014-17", "2018-19", "A 2020-21")), ("NEW 2024+", ("B 2024+",)))
BOOK_MARKETS = ("XAUUSD", "US500", "GERMANY40", "USDJPY")
SYN = ["--markets", ",".join(BOOK_MARKETS)]

WORLDS = {
    "shuffle":    ("shuffle 2-6w (k 0, vol 1)", ["--preset", "shuffle"]),
    "pers_p150":  ("snap-back k +1.5", ["--preset", "shuffle", "--persist", "1.5"]),
    "pers_p050":  ("snap-back k +0.5", ["--preset", "shuffle", "--persist", "0.5"]),
    "pers_m020":  ("momentum k -0.2", ["--preset", "shuffle", "--persist", "-0.2"]),
    "pers_m040":  ("momentum k -0.4", ["--preset", "shuffle", "--persist", "-0.4"]),
    "dayshuffle": ("dayshuffle (no day order)", ["--preset", "dayshuffle"]),
    "longblock":  ("longblock 8-26w", ["--preset", "longblock"]),
    "vol060":     ("vol x0.60", ["--preset", "shuffle", "--vol", "0.6"]),
    "vol080":     ("vol x0.80", ["--preset", "shuffle", "--vol", "0.8"]),
    "vol125":     ("vol x1.25", ["--preset", "shuffle", "--vol", "1.25"]),
    "vol160":     ("vol x1.60", ["--preset", "shuffle", "--vol", "1.6"]),
}
DIMS = [
    {"key": "persist", "name": "D1  MOMENTUM vs SNAP-BACK", "ladder": ["pers_p150", "pers_p050", "shuffle", "pers_m020",
                                                                       "pers_m040"],
     "pred": {"brk": "+", "fast": "+", "dip": "-", "dipx": "-", "ins": "0"},
     "axis": "snap-back (nightmare for trend riders) -> momentum (ideal for trend riders)"},
    {"key": "order", "name": "D2  TREND LENGTH / DAY ORDER", "ladder": ["dayshuffle", "shuffle", "longblock"],
     "pred": {"brk": "+", "fast": "0", "dip": "+", "dipx": "+", "ins": "+"},
     "axis": "days in random order -> 2-6 week blocks -> 8-26 week blocks"},
    {"key": "vol", "name": "D3  VOLATILITY LEVEL", "ladder": ["vol060", "vol080", "shuffle", "vol125", "vol160"],
     "pred": {"brk": "0", "fast": "0", "dip": "0", "dipx": "0", "ins": "0"},
     "pred_net": {"brk": "+", "fast": "+", "dip": "+", "dipx": "+", "ins": "+"},
     "axis": "calm (x0.6) -> wild (x1.6); costs fixed"},
]
YARD = [
    "",
    "=" * 110,
    "ENGINE CHECK (cloud, fake random-walk markets, 1 seed, 2026-10-10): can it find a cause we PLANTED, and does it",
    "find nothing where nothing was planted?",
    "  D1 planted momentum: brk CONFIRMED (t +4.7), fast CONFIRMED (t +6.1), ins CONSISTENT (t +1.6). dip: t -0.4",
    "     (~150 trades a world: too few). dipx: t -1.8 -- momentum clearly hurt it (-0.05 -> -0.15 -> -0.29 R), but",
    "     the most violent snap-back (k +1.5) hurt it too (an upside-down U): read dip / dipx by the SHAPE across",
    "     the ladder, not only by the straight-line slope.",
    "  D2 on a random walk (shuffling noise changes nothing): every part CONSISTENT / NOT SHOWN, |t| <= 0.8.",
    "  D3 volatility: edge flat for every part (|t| <= 1.2); net up for brk / ins / fast (t 4.5 .. 27).",
    "  So one seed finds a planted cause at t 4-6 and nothing where nothing was planted. Two seeds on real data.",
]


# ================================================================ one world: measure
def _cluster(x):
    tt = time.gmtime(x[8]["_t_in"])
    return "%s|%d-%02d" % (x[0], tt.tm_year, tt.tm_mon)


def world_stats(m):
    """Properties of the world the lanes actually saw (daily FX-day bars), per era: annual vol %, day-to-day
    autocorrelation, 20-day variance ratio (>1 trending, <1 snapping back), share of trend months, share of inside
    days."""
    import asiabo_lab as L
    by = defaultdict(list)
    for j in range(len(m.D)):
        era = L._p_era(m.T[m.D[j][1]])
        if era:
            by[era].append(j)
    out = {}
    for era, js in by.items():
        r, inside, nin = [], 0, 0
        for a, b in zip(js, js[1:]):
            if b == a + 1 and m.seg[b] == m.seg[a] and m.cl[a] > 0 and m.cl[b] > 0:
                r.append(math.log(m.cl[b] / m.cl[a]))
                nin += 1
                if m.hi[b] <= m.hi[a] and m.lo[b] >= m.lo[a]:
                    inside += 1
        if len(r) < 60:
            continue
        n = len(r)
        mu = sum(r) / n
        var = sum((y - mu) ** 2 for y in r) / (n - 1)
        ac = (sum((r[i] - mu) * (r[i - 1] - mu) for i in range(1, n)) / ((n - 1) * var)) if var > 0 else 0.0
        r20 = [sum(r[i - 20:i]) for i in range(20, n + 1)]
        m20 = sum(r20) / len(r20)
        v20 = sum((y - m20) ** 2 for y in r20) / (len(r20) - 1)
        mon = defaultdict(list)
        for j in js:
            mon[time.strftime("%Y-%m", time.gmtime(m.T[m.D[j][1]]))].append(j)
        tm = tot = 0
        for k_, ds in mon.items():
            if len(ds) < 12:
                continue
            rng = sum(m.hi[j] - m.lo[j] for j in ds) / len(ds)
            cl = [m.cl[j] for j in ds]
            path = sum(abs(cl[i] - cl[i - 1]) for i in range(1, len(cl)))
            mv = abs(cl[-1] - cl[0])
            tot += 1
            if rng > 0 and mv / rng >= 3.0 and path > 0 and mv / path >= 0.3:
                tm += 1
        out[era] = {"vol": 100 * math.sqrt(var * 252), "ac1": ac, "vr20": v20 / (20 * var) if var > 0 else 0.0,
                    "trendm": 100.0 * tm / tot if tot else 0.0, "inside": 100.0 * inside / max(1, nin)}
    return out


def measure(out_path):
    import asiabo_lab as L
    import asiabo_why as W
    W._install()
    W.WITH_CHAN = False                      # the chandelier neighbours are a why-phase thing; not needed here
    t0 = time.time()
    specs = dict((x["name"], x) for x in A.COLLECT_SYMBOLS)
    rows, det, world, loose = [], {}, {}, []
    for s in W.MARKETS:
        if s not in specs:
            continue
        print("engine: %s ..." % s)
        try:
            m = L.PMarket(specs[s])
        except RuntimeError as e:
            print("engine: %s skipped (%s)" % (s, str(e).splitlines()[0]))
            continue
        W._m1_cache(m)
        rb = []
        for name, fn in L.P_LANES:
            if name in L.P_OMEGA_LANES:
                fn(m, rb)
        rows += [(s,) + x for x in rb if (x[0], x[1]) in W.NEED_LV]
        if s in W.DIP_MK:                    # the loose dip (dipx): every signal day, overlapping allowed
            lr = []
            W.lane_rsi2_x(m, lr, level=30.0, loose=True)
            W.lane_dip3_x(m, lr, loose=True)
            loose += [(s,) + x for x in lr if x[6] is not None]
        det.update(W.det_table(m))
        world[s] = world_stats(m)
        if m.m1q:
            m.m1q[0].close()
        m._m1cache.clear()
        del m, rb
    book = W.book_of(rows, det)
    agg = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: [0, 0.0, 0.0])))
    for x, part in book + [(y, "dipx") for y in loose]:
        c = agg[part][x[4]][_cluster(x)]
        c[0] += 1
        c[1] += x[5] - x[6]
        c[2] += x[5]
    out = {"parts": dict((p, dict((e, dict(v)) for e, v in d.items())) for p, d in agg.items()), "world": world,
           "trades": len(book), "runtime": round(time.time() - t0, 1), "db": A.find_db()}
    tmp = out_path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(out, f)
    os.replace(tmp, out_path)
    print("engine: measured %d book trades in %.0fs -> %s" % (len(book), time.time() - t0, out_path))


# ================================================================ many worlds: run
def _wdir():
    return os.path.join(A.ROOT, "reports", "engine", "worlds")


def _job(key, seed, py, log_buf):
    import synth_batch as SB
    out = os.path.join(_wdir(), "%s_s%d.json" % (key, seed) if key != "real" else "real.json")
    log_buf.append("")
    log_buf.append("%s seed %s   (started %s)" % (key, seed, time.strftime("%H:%M")))
    if key == "real":
        ok, _ = SB._run([py, os.path.join(HERE, "asiabo_engine.py"), "measure", "--out", out], log_buf)
        return ok
    tmp = os.path.join(A.ROOT, "synth", "eng_%s_s%d.db" % (key, seed))
    try:
        if os.path.exists(tmp):
            os.remove(tmp)
        ok, _ = SB._run([py, os.path.join(HERE, "make_synth.py"), "gen"] + WORLDS[key][1] + SYN +
                        ["--seed", str(seed), "--out", tmp], log_buf)
        if ok:
            ok, _ = SB._run([py, os.path.join(HERE, "asiabo_engine.py"), "measure", "--db", tmp, "--out", out], log_buf)
        return ok
    finally:
        try:
            if os.path.exists(tmp):
                os.remove(tmp)
        except OSError as e:
            log_buf.append("    (could not delete %s: %s)" % (tmp, e))


def run(seeds, dims, workers):
    import synth_batch as SB
    import threading
    from concurrent.futures import ThreadPoolExecutor, as_completed
    os.makedirs(_wdir(), exist_ok=True)
    os.makedirs(os.path.join(A.ROOT, "synth"), exist_ok=True)
    logp = os.path.join(A.ROOT, "reports", "engine", "engine_log.txt")

    def log(s):
        print(s)
        with open(logp, "a", encoding="utf-8") as f:
            f.write(s + "\n")
    keys = []
    for d in DIMS:
        if d["key"] in dims:
            for k in d["ladder"]:
                if k not in keys:
                    keys.append(k)
    jobs = [("real", 0)] + [(k, sd) for k in keys for sd in range(1, seeds + 1)]
    todo = [(k, sd) for k, sd in jobs if not os.path.exists(
        os.path.join(_wdir(), "real.json" if k == "real" else "%s_s%d.json" % (k, sd)))]
    log("")
    log("=" * 80)
    log("engine %s: %d worlds, %d already measured, %d to build" % (time.strftime("%Y-%m-%d %H:%M"), len(jobs),
                                                                  len(jobs) - len(todo), len(todo)))
    py = sys.executable
    t_all = time.time()
    if todo:
        buf = []
        ok, _ = SB._run([py, os.path.join(HERE, "make_synth.py"), "cache"], buf)
        for line in buf:
            log(line)
        nw = workers if workers else SB.auto_workers(log)
        lock = threading.Lock()
        done = [0]

        def one(k, sd):
            buf = []
            ok = _job(k, sd, py, buf)
            with lock:
                done[0] += 1
                buf.insert(0, "[%d/%d] %s seed %s: %s" % (done[0], len(todo), k, sd, "ok" if ok else "FAILED"))
                for line in buf:
                    log(line)
        with ThreadPoolExecutor(max_workers=nw) as ex:
            futs = []
            for k, sd in todo:
                futs.append(ex.submit(one, k, sd))
                time.sleep(2)
            for fu in as_completed(futs):
                fu.result()
    log("worlds done in %.1f h" % ((time.time() - t_all) / 3600.0))
    report(dims)


# ================================================================ report
def _load_world(key, seed):
    p = os.path.join(_wdir(), "real.json" if key == "real" else "%s_s%d.json" % (key, seed))
    if not os.path.exists(p):
        return None
    with open(p) as f:
        return json.load(f)


def _cells(w, part, eras):
    """-> {cluster: [n, sum edge, sum net]} for one world, part and era group."""
    out = defaultdict(lambda: [0, 0.0, 0.0])
    for e in eras:
        for c, v in w["parts"].get(part, {}).get(e, {}).items():
            o = out[c]
            o[0] += v[0]; o[1] += v[1]; o[2] += v[2]
    return out


def _mean_t(cells, idx):
    """cells: {cluster: [n, s_edge, s_net]} -> (n, mean, clustered t)."""
    n = sum(v[0] for v in cells.values())
    if n < 2:
        return n, None, None
    mu = sum(v[idx] for v in cells.values()) / n
    k = len(cells)
    if k < 2:
        return n, mu, None
    var = sum((v[idx] - v[0] * mu) ** 2 for v in cells.values()) * k / (k - 1.0) / (n * n)
    return n, mu, (mu / math.sqrt(var) if var > 0 else None)


def _slope(points, idx):
    """points: [(x, {cluster: [n, s_edge, s_net]})] where clusters are already keyed by seed -> (slope, t).
    OLS of the per-trade value on x; standard error clustered by seed x market x month ACROSS the ladder (paired)."""
    N = sum(v[0] for x, cs in points for v in cs.values())
    if N < 10:
        return None, None
    xb = sum(x * v[0] for x, cs in points for v in cs.values()) / N
    yb = sum(v[idx] for x, cs in points for v in cs.values()) / N
    sxx = sum(v[0] * (x - xb) ** 2 for x, cs in points for v in cs.values())
    if sxx <= 0:
        return None, None
    b = sum((x - xb) * (v[idx] - v[0] * yb) for x, cs in points for v in cs.values()) / sxx
    u = defaultdict(float)
    for x, cs in points:
        for c, v in cs.items():
            u[c] += (x - xb) * (v[idx] - v[0] * yb - v[0] * b * (x - xb))
    k = len(u)
    if k < 2:
        return b, None
    var = sum(e * e for e in u.values()) * k / (k - 1.0) / (sxx * sxx)
    return b, (b / math.sqrt(var) if var > 0 else None)


def _verdict(pred, b, t):
    if b is None or t is None:
        return "no data"
    if pred == "0":
        return "CONSISTENT" if abs(t) < 2 else ("UNCLEAR" if abs(t) < 3 else "CONTRADICTED")
    right = (b > 0) == (pred == "+")
    if right and abs(t) >= 3:
        return "CONFIRMED"
    if right and abs(t) >= 2:
        return "SUPPORTED"
    if not right and abs(t) >= 2:
        return "CONTRADICTED"
    return "NOT SHOWN"


def _f(v, w=6, p=3):
    return ("%+*.*f" % (w, p, v)) if v is not None else "%*s" % (w, "-")


def _t(v):
    return ("t%+5.1f" % v) if v is not None else "t   - "


def report(dims=None):
    dims = dims or [d["key"] for d in DIMS]
    rep = A.Report("engine")
    p = rep.p
    seeds = sorted(set(int(os.path.basename(f).rsplit("_s", 1)[1][:-5])
                       for f in glob.glob(os.path.join(_wdir(), "*_s*.json"))))
    p("=" * 110)
    p("POCKET ENGINE stage 1: ideal and nightmare worlds for the states we have theories for   (%s)" %
      time.strftime("%Y-%m-%d %H:%M"))
    p("=" * 110)
    p("Each world = a reshuffled cousin of bars.db (4 book markets), moved along ONE dial. Measured: the frozen-book")
    p("parts brk / ins / fast / dip (lab lanes, one position per part / market / direction). EDGE = net R minus the")
    p("coin-flip average (cost-free direction value). Seeds: %s. Worlds of one seed share the same block schedule" %
      (", ".join(str(s) for s in seeds) or "none"))
    p("(paired); t clustered by seed x market x month. Predictions and verdict rules were written in asiabo_engine.py")
    p("BEFORE any world was measured (see its top). The slope is per dial STEP along the ladder as listed.")
    real = _load_world("real", 0)
    if real:
        p("")
        p("REFERENCE: the real bars.db (same code), edge/trade (n, t) per era:")
        for part in PARTS:
            line = "  %-4s" % part
            for e in ERAS:
                n, mu, t = _mean_t(_cells(real, part, (e,)), 1)
                line += " | %s %s(%d) %s" % (e[-5:], _f(mu), n, _t(t))
            p(line)
    for d in DIMS:
        if d["key"] not in dims:
            continue
        p("")
        p("=" * 110)
        p("%s   ladder: %s" % (d["name"], d["axis"]))
        p("=" * 110)
        # the worlds as measured
        p("  the worlds (average over markets, eras and seeds): vol %/yr | day-to-day autocorr | 20-day variance ratio |")
        p("  trend months % | inside days %")
        for k in d["ladder"]:
            ws = [w for w in (_load_world(k, s) for s in seeds) if w]
            vals = defaultdict(list)
            for w in ws:
                for mk, eras in w["world"].items():
                    for e, st in eras.items():
                        for q, v in st.items():
                            vals[q].append(v)
            g = lambda q: (sum(vals[q]) / len(vals[q])) if vals[q] else float("nan")
            p("    %-28s seeds %d | vol %5.1f | ac1 %+.3f | VR20 %4.2f | trend %4.1f%% | inside %4.1f%%" % (
                WORLDS[k][0], len(ws), g("vol"), g("ac1"), g("vr20"), g("trendm"), g("inside")))
        for part in PARTS:
            pred = d["pred"][part]
            p("")
            p("  %s   predicted edge %s%s" % (part, pred, ("   net %s" % d["pred_net"][part]) if d.get("pred_net") else ""))
            for gname, eras in GROUPS:
                pts_e, line = [], "    %-11s" % gname
                per_seed = defaultdict(list)
                for i, k in enumerate(d["ladder"]):
                    merged = {}
                    for s in seeds:
                        w = _load_world(k, s)
                        if not w:
                            continue
                        cs = _cells(w, part, eras)
                        for c, v in cs.items():
                            merged["%d|%s" % (s, c)] = v
                        per_seed[s].append((i, dict(("%d|%s" % (s, c), v) for c, v in cs.items())))
                    n, mu, t = _mean_t(merged, 1)
                    line += " %s(%d)" % (_f(mu), n)
                    pts_e.append((i, merged))
                b, t = _slope(pts_e, 1)
                bn, tn = _slope(pts_e, 2)
                agree = sum(1 for s, pts in per_seed.items() if len(pts) == len(d["ladder"]) and
                            (_slope(pts, 1)[0] or 0) * (b or 0) > 0)
                line += "  | edge slope %s/step %s  seeds same sign %d/%d" % (_f(b), _t(t), agree, len(per_seed))
                line += "  | net slope %s %s" % (_f(bn), _t(tn))
                if gname == "ALL":
                    line += "  -> %s" % _verdict(pred, b, t)
                    if d.get("pred_net"):
                        line += " / net %s" % _verdict(d["pred_net"][part], bn, tn)
                p(line)
    for line in YARD:
        p(line)
    rep.save()


def main():
    argv = sys.argv[1:]
    if argv and argv[0] == "measure":
        out = None
        if "--db" in argv:
            db = os.path.abspath(argv[argv.index("--db") + 1])
            A.find_db = lambda: db
        if "--out" in argv:
            out = os.path.abspath(argv[argv.index("--out") + 1])
        if not out:
            raise SystemExit("measure needs --out")
        measure(out)
        return
    if argv and argv[0] == "report":
        report()
        return
    seeds, dims, workers = 2, [d["key"] for d in DIMS], 0
    i = 0
    while i < len(argv):
        if argv[i] == "--seeds":
            seeds = int(argv[i + 1]); i += 2
        elif argv[i] == "--dims":
            dims = argv[i + 1].split(","); i += 2
        elif argv[i] == "--workers":
            workers = int(argv[i + 1]); i += 2
        else:
            raise SystemExit(__doc__)
    run(seeds, dims, workers)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception:
        traceback.print_exc()
        if sys.stdin and sys.stdin.isatty():
            input("\nerror above. Press Enter to close.")
        sys.exit(1)
