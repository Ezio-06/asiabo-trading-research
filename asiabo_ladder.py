"""
asiabo_ladder.py  --  the LADDER trade (Ezio, 2026-10-10), tested as pre-registered in ladder_spec.md (project).

  Enter small early in a trend, bank each rung at a modest target, re-enter while the 20/40/60-day trend still agrees,
  size each rung by how long the trend has proven itself, stop escalating near exhaustion.

RULES (fixed before any test):
  trend-day counter (per market, start of day): consecutive days with 20-day straightness >= 0.30 and the 20-day move in
      the same direction; resets to 1 when either breaks; FORCED back to 1 after day 60.
  gates: the 20-, 40- and 60-day net moves all point the trade's way.
  size(c): c<=2 none | 3..40 rises 0.25 -> 1.00 | 41..49 1.00 -> 0.85 | 50..59 0.35 | 60 none, then the reset.
  rung 1 = brk's normal entry (the frozen brk lanes + their filter) when the gates hold and size > 0; one ladder per
      market and direction at a time. Every rung: stop = brk's stop distance at rung 1; target = entry + 1.5 daily ATR;
      out at the close if neither within 10 trading days. On a TARGET hit the next rung opens at the next bar's open if
      the gates hold and size > 0 that day; any other exit ends the ladder.
  CONTROL 'ladder, no taper': the same, but size stays 1.00 after day 40 forever and no forced reset (shows what the
      40/50/60 taper does). Compared with brk today (5-day chandelier) and brk with the er40 switch, at the SAME
      average risk (R per year rescaled to brk's total risk).
WORLDS: regime synth d=0.25 (known truth) x3, AGING synth (momentum fades over 70% of each spell, the last 30% reverses)
      x3, and the real bars.db (EXPLORATORY: the real eras are spent; also brk by trend-day bucket). Final say: new data.

    python asiabo_ladder.py            (run_18_ladder.bat; resumable)      python asiabo_ladder.py report
"""
import os, sys, json, math, time, glob, bisect, sqlite3, traceback
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import asiabo_offline as A

BOOK_MARKETS = ("XAUUSD", "US500", "GERMANY40", "USDJPY")
ER_TH, TGT_ATR, MAX_DAYS = 0.30, 1.5, 10
WORLDS = [("reg", s) for s in (1, 2, 3)] + [("aging", s) for s in (1, 2, 3)] + [("real", 0)]
VARIANTS = ("brk", "brk_switch", "ladder", "ladder_notaper")
VTEXT = {"brk": "brk today (5-day chandelier)", "brk_switch": "brk + er40 switch", "ladder": "LADDER (40/50/60 taper)",
         "ladder_notaper": "ladder, no taper (control)"}


def size_of(c, taper=True):
    if c is None or c <= 2:
        return 0.0
    if c <= 40:
        return 0.25 + 0.75 * (c - 3) / 37.0
    if not taper:
        return 1.0
    if c <= 49:
        return 1.0 - 0.15 * (c - 40) / 9.0
    if c <= 59:
        return 0.35
    return 0.0


def day_table(m):
    """Per FX day j (start of day): run length, counter, direction, gates, er40."""
    cl, seg = m.cl, m.seg
    out = {}
    run, rsign = 0, 0
    for j in range(1, len(m.D)):
        d = {}
        if j - 21 >= seg[j]:
            path = sum(abs(cl[k] - cl[k - 1]) for k in range(j - 20, j))
            mv = cl[j - 1] - cl[j - 21]
            er20 = abs(mv) / path if path else 0.0
            sg = 1 if mv > 0 else -1
            if er20 >= ER_TH:
                run = run + 1 if sg == rsign else 1
                rsign = sg
            else:
                run, rsign = 0, 0
        else:
            run, rsign = 0, 0
        d["run"], d["sign"] = run, rsign
        d["c"] = ((run - 1) % 60) + 1 if run > 0 else 0
        g = []
        for W in (20, 40, 60):
            g.append((1 if cl[j - 1] > cl[j - 1 - W] else -1) if j - 1 - W >= seg[j] else 0)
        d["gate"] = g[0] if (g[0] and g[0] == g[1] == g[2]) else 0
        if j - 41 >= seg[j]:
            path = sum(abs(cl[k] - cl[k - 1]) for k in range(j - 40, j))
            d["er40"] = abs(cl[j - 1] - cl[j - 41]) / path if path else 0.0
        out[j] = d
    return out


def run_ladders(m, W, L, signals, days, taper):
    """signals: brk candidate rows of ONE market (sorted by entry). -> list of rung records."""
    recs = []
    busy = {1: -1.0, -1: -1.0}
    for x in signals:
        t = x[8]
        d, j0, e, sd = t["_d"], t["_j0"], t["_e"], t["_sd"]
        if t["_t_in"] < busy[d]:
            continue
        dj = m.di[j0]
        dt = days.get(dj, {})
        c = dt.get("c") if taper else dt.get("run")
        sz = size_of(c, taper)
        if sz <= 0 or dt.get("gate") != d or dt.get("sign") != d:
            continue
        rung, j, entry, same = 1, j0, e, True
        last_out = t["_t_in"]
        while True:
            dj = m.di[j]
            N = m.N[dj] or sd
            tp = entry + d * TGT_ATR * N
            end = m.D[dj + MAX_DAYS][2] if dj + MAX_DAYS < len(m.D) else m.n - 1
            out = []
            W.ORIG_PT(m, out, x[1], x[2], j, entry, d, sd, (), same_bar_stop=same, plans={"lad": (tp, end, None)})
            if not out:
                break
            y = out[0]
            tg = y[7]
            hit = y[6] >= d * (tp - entry) / sd - 1e-9
            recs.append({"m": m.s, "t_in": tg["_t_in"], "t_out": tg["_t_out"], "size": sz, "net": y[4],
                         "edge": y[4] - y[5], "rung": rung, "c": c, "era": y[3], "hit": hit})
            last_out = tg["_t_out"]
            if not hit:
                break
            jx = bisect.bisect_left(m.T, tg["_t_out"] - 900) + 1
            if jx >= m.n:
                break
            dt = days.get(m.di[jx], {})
            c = dt.get("c") if taper else dt.get("run")
            sz = size_of(c, taper)
            if sz <= 0 or dt.get("gate") != d or dt.get("sign") != d:
                break
            rung, j, entry, same = rung + 1, jx, m.O[jx], False
        if recs:
            recs[-1]["last"] = True
        busy[d] = last_out
    return recs


def measure(db, out_path, kind):
    import asiabo_lab as L
    import asiabo_why as W
    if db:
        A.find_db = lambda: db
    W._install()
    W.WITH_CHAN = False
    specs = dict((x["name"], x) for x in A.COLLECT_SYMBOLS)
    res = defaultdict(list)
    rows_all, det_all, er_all = [], {}, {}
    ladders, ladders_nt, cday = [], [], {}
    for s in W.MARKETS:
        if s not in specs:
            continue
        print("ladder: %s ..." % s)
        m = L.PMarket(specs[s])
        W._m1_cache(m)
        rb = []
        for name, fn in L.P_LANES:
            if name in L.P_OMEGA_LANES:
                fn(m, rb)
        rows = [(s,) + x for x in rb if (x[0], x[1]) in W.NEED_LV]
        det = W.det_table(m)
        days = day_table(m)
        for j, dt in days.items():
            if "er40" in dt:
                er_all[(s, m.D[j][0])] = dt["er40"]
            cday[(s, m.D[j][0])] = dt["c"]
        sig = sorted(W.sleeves(rows, det)["brk"], key=lambda x: x[8]["_t_in"])
        ladders += run_ladders(m, W, L, sig, days, True)
        ladders_nt += run_ladders(m, W, L, sig, days, False)
        rows_all += rows
        det_all.update(det)
        if m.m1q:
            m.m1q[0].close()
        m._m1cache.clear()
        del m, rb
    rec = lambda x, size=1.0: {"m": x[0], "t_in": x[8]["_t_in"], "t_out": x[8]["_t_out"], "size": size, "net": x[5],
                               "edge": x[5] - x[6], "era": x[4], "c": cday.get((x[0], x[8].get("_dk")))}
    base = W.book_of(rows_all, det_all)
    res["brk"] = [rec(x) for x, q in base if q == "brk"]
    brk_l = set(L.H_WIDE)
    gated = [x for x in rows_all if x[1] not in brk_l or (er_all.get((x[0], x[8].get("_dk"))) or 0) > ER_TH]
    res["brk_switch"] = [rec(x) for x, q in W.book_of(gated, det_all) if q == "brk"]
    res["ladder"], res["ladder_notaper"] = ladders, ladders_nt
    spells = {}
    if db and kind != "real":
        con = sqlite3.connect(db)
        sp = defaultdict(list)
        for s, t0, t1, st, a in con.execute("select symbol, t0, t1, state, a from regime"):
            sp[s].append((t0, t1, st))
        con.close()
        spells = dict((s, sorted(v)) for s, v in sp.items())
        for v in res.values():
            for r in v:
                lst = spells.get(r["m"], [])
                k = bisect.bisect_right([a for a, b, st in lst], r["t_in"]) - 1
                r["state"] = lst[k][2] if (k >= 0 and r["t_in"] < lst[k][1]) else None
    with open(out_path + ".tmp", "w") as fh:
        json.dump({"kind": kind, "res": res}, fh)
    os.replace(out_path + ".tmp", out_path)
    print("ladder: done -> %s" % out_path)


def _wdir():
    return os.path.join(A.ROOT, "reports", "ladder", "worlds")


def run(workers):
    import synth_batch as SB
    import threading
    from concurrent.futures import ThreadPoolExecutor
    os.makedirs(_wdir(), exist_ok=True)
    os.makedirs(os.path.join(A.ROOT, "synth"), exist_ok=True)
    logp = os.path.join(A.ROOT, "reports", "ladder", "ladder_log.txt")
    lock = threading.Lock()

    def log(s):
        print(s)
        with lock:
            with open(logp, "a", encoding="utf-8") as f:
                f.write(s + "\n")
    todo = [(k, s) for k, s in WORLDS if not os.path.exists(os.path.join(_wdir(), "%s_s%d.json" % (k, s)))]
    log("ladder %s: %d worlds to build" % (time.strftime("%Y-%m-%d %H:%M"), len(todo)))
    py = sys.executable
    if todo:
        buf = []
        SB._run([py, os.path.join(HERE, "make_synth.py"), "cache"], buf)
        for line in buf:
            log(line)
        nw = workers if workers else SB.auto_workers(log)

        def one(k, s):
            buf = []
            out = os.path.join(_wdir(), "%s_s%d.json" % (k, s))
            tmp = os.path.join(A.ROOT, "synth", "lad_%s_s%d.db" % (k, s))
            ok = True
            try:
                if k == "real":
                    ok, _ = SB._run([py, os.path.join(HERE, "asiabo_ladder.py"), "measure", "--kind", "real", "--out",
                                     out], buf)
                else:
                    args = ["--preset", "dayshuffle", "--regime", "0.25,0.25"] + (["--aging", "1"] if k == "aging" else [])
                    ok, _ = SB._run([py, os.path.join(HERE, "make_synth.py"), "gen"] + args +
                                    ["--markets", ",".join(BOOK_MARKETS), "--seed", str(s), "--out", tmp], buf)
                    if ok:
                        ok, _ = SB._run([py, os.path.join(HERE, "asiabo_ladder.py"), "measure", "--kind", k, "--db", tmp,
                                         "--out", out], buf)
            finally:
                if os.path.exists(tmp):
                    try:
                        os.remove(tmp)
                    except OSError:
                        pass
            log("%s seed %d: %s" % (k, s, "ok" if ok else "FAILED"))
            for line in buf:
                log(line)
        with ThreadPoolExecutor(max_workers=nw) as ex:
            fs = []
            for k, s in todo:
                fs.append(ex.submit(one, k, s))
                time.sleep(2)
            for f in fs:
                f.result()
    report()


# ================================================================ report
def _cl(r, w):
    tt = time.gmtime(r["t_in"])
    return "%s|%s|%d-%02d" % (w, r["m"], tt.tm_year, tt.tm_mon)


def _wstats(rs, key="net"):
    """size-weighted mean per unit risk, clustered t (world x market x month)."""
    S = sum(r["size"] for r, w in rs)
    if S <= 0:
        return None, None
    mu = sum(r["size"] * r[key] for r, w in rs) / S
    g = defaultdict(float)
    for r, w in rs:
        g[_cl(r, w)] += r["size"] * (r[key] - mu)
    k = len(g)
    if k < 2:
        return mu, None
    var = sum(e * e for e in g.values()) * k / (k - 1.0) / (S * S)
    return mu, (mu / math.sqrt(var) if var > 0 else None)


def _dd(rs, scale):
    mon = defaultdict(float)
    for r, w in rs:
        mon[(w, time.strftime("%Y-%m", time.gmtime(r["t_out"])))] += r["size"] * r["net"] * scale
    worst = 0.0
    for w in set(k[0] for k in mon):
        eq = peak = 0.0
        for k in sorted(k for k in mon if k[0] == w):
            eq += mon[k]
            peak = max(peak, eq)
            worst = max(worst, peak - eq)
    return worst


def report():
    rep = A.Report("ladder")
    p = rep.p
    data = defaultdict(list)
    for fp in sorted(glob.glob(os.path.join(_wdir(), "*.json"))):
        with open(fp) as fh:
            w = json.load(fh)
        data[w["kind"]].append((os.path.basename(fp)[:-5], w["res"]))
    yrs = 10.75
    p("=" * 110)
    p("THE LADDER TRADE (pre-registered: ladder_spec.md / asiabo_ladder.py top)   %s" % time.strftime("%Y-%m-%d %H:%M"))
    p("=" * 110)
    p("Per unit of risk = size-weighted net R per trade (t clustered by world x market x month). 'R/yr at brk's risk' =")
    p("net R per year per world, rescaled so the variant deploys the same TOTAL risk as brk today. max DD = worst")
    p("peak-to-trough of that rescaled monthly curve, in R. Ladder rows are RUNGS; 'last rung' = the rung that ended")
    p("each ladder (not a target hit).")
    for kind in ("reg", "aging", "real"):
        ws = data.get(kind)
        if not ws:
            continue
        p("")
        p("#" * 110)
        p({"reg": "REGIME SYNTH (known truth, strength 0.25)", "aging": "AGING SYNTH (momentum fades, then the last 30% of "
           "each spell REVERSES)", "real": "REAL bars.db -- EXPLORATORY (the real eras are already spent)"}[kind] +
          "   worlds: %d" % len(ws))
        p("#" * 110)
        brk_risk = sum(r["size"] for wn, res in ws for r in res["brk"]) / len(ws)
        for v in VARIANTS:
            rs = [(r, wn) for wn, res in ws for r in res.get(v, [])]
            if not rs:
                continue
            risk = sum(r["size"] for r, w in rs) / len(ws)
            sc = brk_risk / risk if risk else 0.0
            mu, t = _wstats(rs)
            me, te = _wstats(rs, "edge")
            ryr = sum(r["size"] * r["net"] for r, w in rs) / len(ws) / yrs
            line = "  %-30s n %5d  risk/world %6.0f | net per risk %s (t %s) | edge %s | R/yr at brk's risk %+6.1f | max DD %5.0f R" % (
                VTEXT[v], len(rs), risk, "%+.3f" % mu if mu is not None else "-", "%+.1f" % t if t is not None else "-",
                "%+.3f" % me if me is not None else "-", ryr * sc, _dd(rs, sc))
            p(line)
            if v.startswith("ladder"):
                last = [(r, w) for r, w in rs if r.get("last")]
                ml, tl = _wstats(last)
                hits = sum(1 for r, w in rs if r.get("hit")) / float(len(rs))
                rungs = defaultdict(list)
                for r, w in rs:
                    rungs[min(r["rung"], 4)].append((r, w))
                p("      targets hit %.0f%% | last rung of each ladder: n %d, net per risk %s | by rung: %s" % (
                    100 * hits, len(last), "%+.3f" % ml if ml is not None else "-",
                    "  ".join("%s%d %+.3f (%d)" % ("#" if k < 4 else "#>=", k, _wstats(x)[0] or 0, len(x))
                              for k, x in sorted(rungs.items()))))
            if kind != "real":
                parts = []
                for st in ("mom", "rev", "none", "snap"):
                    x = [(r, w) for r, w in rs if r.get("state") == st]
                    if x:
                        parts.append("%s %+.3f (%d)" % (st, _wstats(x)[0], len(x)))
                p("      by true state at entry: " + "  ".join(parts))
        # by trend-day bucket (brk today)
        p("")
        p("  brk TODAY by the trend-day counter on its entry day (does the trend's age matter?): net per trade (n)")
        bk = [(0, 2), (3, 10), (11, 20), (21, 40), (41, 49), (50, 60)]
        line = "   "
        for a, b in bk:
            x = [(r, wn) for wn, res in ws for r in res["brk"] if r.get("c") is not None and a <= r["c"] <= b]
            mu = _wstats(x)[0] if x else None
            line += "  c %d-%d: %s (%d)" % (a, b, "%+.3f" % mu if mu is not None else "-", len(x))
        p(line)
    rep.save()


def main():
    argv = sys.argv[1:]
    if argv and argv[0] == "measure":
        db = os.path.abspath(argv[argv.index("--db") + 1]) if "--db" in argv else None
        measure(db, os.path.abspath(argv[argv.index("--out") + 1]), argv[argv.index("--kind") + 1])
        return
    if argv and argv[0] == "report":
        report()
        return
    workers = int(argv[argv.index("--workers") + 1]) if "--workers" in argv else 0
    run(workers)


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
