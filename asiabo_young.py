"""
asiabo_young.py  --  Phase 3 youngling screen, batch 1 (2026-10-12). Rules and predictions: young_batch1_spec.md
(project), copied below. Real data, SHADOW ONLY: it measures, it decides nothing. Imports the lab, the why phase and the
probe (bars, costs, walker, book); changes nothing in them.

    python asiabo_young.py                    the three lanes + the core-book correlation (real bars.db)
    python asiabo_young.py --db synth/x.db    the same on a cousin history (yardstick)

LANES (one exit per outcome = a state label; EDGE = net R minus the coin-flip average, as in the lab)
  #31 MIRROR DIP (Ezio): peak stretch of the last 5 closes >= 2.5 N from their 20-day average + er20 >= 0.30 the same
      way; trigger = the FIRST close beyond the 3-day low (high); trade AGAINST the stretch at the next session open.
      Stop = 5-day extreme +- 1.5 N, target = the 20-day average, time = 5 trading days. All 6 markets.
  #27 / #28 US500 vs GERMANY40: d10 = 10-day log return US500 - beta x GERMANY40 (beta: 120-day OLS of daily returns),
      z = d10 / sd(d10, 250 days). |z| >= 2 -> #27 bets the gap CLOSES. Exits on the spread LEVEL since the trigger
      (fixed 2026-10-12 after the noise test, before any real run: exiting on z = 0 let old days dropping out of the
      10-day window fake a 'gap closed'): target = the whole gap G closed, stop = the gap widened by another 0.75 G
      (= z 2 -> 3.5), time 10 days; R in units of 0.75 G;
      #28 = the exact mirror (relative momentum). Daily closes, both legs at the next FX-day open, both legs' costs.
  #19 SQUEEZE BREAKOUT: 20-day bandwidth at its 120-day low on one of the 5 closes before; close beyond the 2-sigma
      band -> trade the break. Stop = the 20-day average, target = 3 N, time = 15 trading days. All 6 markets.

PREDICTIONS (written 2026-10-12 BEFORE this file ever ran)
  Ezio:   #31 small win rate (chop hits the stops), best on dip's weaker markets.  #27 beats #28 ("usually catch up").
          #19 chosen over #12 (a panic peak cannot be predicted).
  Claude: #31 win 35-45%, net < 0, EDGE <= 0 overall, small + only in XTIUSD; stops most common in the indices.
          #27 EDGE > 0 but t < 2 (thin data), time exits most common.  #19 EDGE ~ 0 inside the yardstick, false-break
          stops most common.  #31 negatively correlated with dip on the indices; #19 positively with fast.
"""
import os, sys, math, time, shutil, traceback
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import asiabo_offline as A

MARKETS = ["XAUUSD", "US500", "EURUSD", "USDJPY", "XTIUSD", "GERMANY40"]
EZIO_MK = ("EURUSD", "XAUUSD", "XTIUSD", "USDJPY")
ER_TH = 0.30
OLD_YEARS = (2014, 2019)

YARD = {
    "lanes": "\n".join([
        "YARDSTICK (this file on 2 fake random walks + the v8 realistic cousin real8 s3, 2026-10-12): ALL-line EDGE",
        "    #31 +0.006 (t +0.2) / -0.106 (t -3.5) / cousin -0.057;  #19 +0.111 (t +1.1) / +0.048 / cousin +0.044.",
        "    Single markets reached t +-2.8 on noise. Overlapping 5-15 day holds make t swing far: count a lane only at",
        "    |t| ~4+, the same sign in OLD and NEW, outside the noise AND the cousin."]),
    "pair": "\n".join([
        "YARDSTICK (2 fake random walks): #27 EDGE +0.073 / -0.091 over ~50 trades; one 14-trade half reached t -5.1 on",
        "    noise. With 6-10 real trades (US500 data starts 2020 + a year of warm-up) NOTHING here can be read."]),
}


# ================================================================ helpers
def entry_bar(m, L, j):
    """the session-open bar of FX day j (the first bar of the day if that one is missing)."""
    i0, i1 = m.D[j][1], m.D[j][2]
    s = L.p_session_open(m, i0, i1)
    return s if s is not None else i0


def label(x):
    g = x[7]
    tpr = x[8].get("_tpR")
    if g is None:
        return "?"
    if g <= -0.95:
        return "stop"
    if tpr is not None and g >= tpr - 0.02:
        return "target"
    return "time"


def one_position(rows):
    """one position per lane / market / direction: drop trades that open before the previous one closed."""
    out, busy = [], {}
    for x in sorted(rows, key=lambda r: r[8]["_t_in"]):
        k = (x[0], x[1], x[8].get("_d"))
        if x[8]["_t_in"] < busy.get(k, -1.0):
            continue
        busy[k] = x[8]["_t_out"]
        out.append(x)
    return out


def clu(x):
    tt = time.gmtime(x[8]["_t_in"])
    return (x[0], tt.tm_year, tt.tm_mon)


def half(x):
    y = time.gmtime(x[8]["_t_in"]).tm_year
    return "OLD 2014-19" if y <= OLD_YEARS[1] else "NEW 2020-26"


# ================================================================ #31 and #19 (the lab's walker)
def lane31(m, dv, L, rows, mode="real"):
    """mode: real | notrigger (same setup, the crack did NOT fire) | delay (enter one day later, same levels)."""
    n = dv.n
    dl = 1 if mode == "delay" else 0
    name = {"real": "31 mirror dip", "notrigger": "31 P-no-trigger", "delay": "31 P-delay-1d"}[mode]
    for j in range(27, n - 1 - dl):
        if not dv.ok(j) or j - 26 < dv.seg[j] or j + 4 + dl > dv.send[j]:
            continue
        N = dv.N[j]
        zs = []
        for k in range(j - 5, j):
            a = dv.sma(k, 20)
            zs.append((dv.cl[k] - a) / N)
        zp = max(zs, key=abs)
        if abs(zp) < 2.5:
            continue
        u = 1 if zp > 0 else -1
        e20 = dv.er(j, 20)
        if not e20 or e20[0] < ER_TH or e20[1] != u:
            continue

        def cracked(k):
            return (dv.cl[k] < min(dv.lo[k - 3:k])) if u > 0 else (dv.cl[k] > max(dv.hi[k - 3:k]))
        trig = cracked(j - 1) and not cracked(j - 2)
        if (mode != "notrigger" and not trig) or (mode == "notrigger" and (trig or cracked(j - 1))):
            continue
        i = entry_bar(m, L, j + dl)
        entry = m.O[i]
        ext = max(dv.hi[j - 5:j]) if u > 0 else min(dv.lo[j - 5:j])
        stop = ext + u * 1.5 * N
        tp = dv.sma(j - 1, 20)
        d = -u
        sd = (stop - entry) * u
        if sd <= 0 or (entry - tp) * u <= 0:
            continue
        end = m.D[j + 4 + dl][2]
        L.p_trade(m, rows, name, "short-stretch" if u > 0 else "long-stretch", i, entry, d, sd, (),
                  tags={"_tpR": abs(tp - entry) / sd, "_dk": dv.key[j]}, plans={"own": (tp, end, None)})


def lane19(m, dv, L, rows, mode="real"):
    """mode: real | nobreak (squeeze, no band break: direction = close vs the 20-day average) | delay (one day later)."""
    n = dv.n
    dl = 1 if mode == "delay" else 0
    name = {"real": "19 squeeze", "nobreak": "19 P-no-break", "delay": "19 P-delay-1d"}[mode]
    bw = [None] * n
    sdv = [None] * n
    for k in range(n):
        if k - 19 < dv.seg[k]:
            continue
        w = dv.cl[k - 19:k + 1]
        mu = sum(w) / 20.0
        s = math.sqrt(sum((x - mu) ** 2 for x in w) / 20.0)
        sdv[k] = s
        bw[k] = 4.0 * s / mu if mu else None
    sq = [False] * n
    for k in range(n):
        if bw[k] is None or k - 119 < dv.seg[k]:
            continue
        win = [b for b in bw[k - 119:k + 1] if b is not None]
        if len(win) >= 100 and bw[k] <= min(win):
            sq[k] = True
    for j in range(140, n - 1 - dl):
        if not dv.ok(j) or j + 14 + dl > dv.send[j] or sdv[j - 1] is None:
            continue
        if not any(sq[k] for k in range(j - 6, j - 1)):
            continue
        mid = dv.sma(j - 1, 20)
        c = dv.cl[j - 1]
        if mode == "nobreak":
            if abs(c - mid) > 2 * sdv[j - 1] or c == mid:
                continue
            d = 1 if c > mid else -1
        elif c > mid + 2 * sdv[j - 1]:
            d = 1
        elif c < mid - 2 * sdv[j - 1]:
            d = -1
        else:
            continue
        i = entry_bar(m, L, j + dl)
        entry = m.O[i]
        sd = (entry - mid) * d
        if sd <= 0:
            continue
        N = dv.N[j]
        tp = entry + d * 3.0 * N
        end = m.D[j + 14 + dl][2]
        L.p_trade(m, rows, name, "long" if d > 0 else "short", i, entry, d, sd, (),
                  tags={"_tpR": 3.0 * N / sd, "_dk": dv.key[j]}, plans={"own": (tp, end, None)})


# ================================================================ #27 / #28 pair
def pair(dva, dvb, spa, spb):
    """dva = US500 Day view, dvb = GERMANY40. -> rows in the lab's format for '27 gap closes' and '28 rel momentum'."""
    ia = dict((k, j) for j, k in enumerate(dva.key))
    ib = dict((k, j) for j, k in enumerate(dvb.key))
    keys = [k for k in dva.key if k in ib]
    # common-day series (a gap > 10 days breaks it)
    oa, ca, ob, cb, era = [], [], [], [], []
    for k in keys:
        a, b = ia[k], ib[k]
        oa.append(dva.o[a]); ca.append(dva.cl[a]); ob.append(dvb.o[b]); cb.append(dvb.cl[b]); era.append(dva.era[a])
    n = len(keys)
    brk = [0] * n
    for t in range(1, n):
        brk[t] = t if keys[t] - keys[t - 1] > 10 else brk[t - 1]
    ra = [None] + [math.log(ca[t] / ca[t - 1]) if brk[t] != t else None for t in range(1, n)]
    rb = [None] + [math.log(cb[t] / cb[t - 1]) if brk[t] != t else None for t in range(1, n)]
    beta, d10 = [None] * n, [None] * n
    for t in range(n):
        if t - 120 < brk[t]:
            continue
        xs = [(rb[q], ra[q]) for q in range(t - 119, t + 1)]
        mx = sum(x for x, y in xs) / 120.0
        my = sum(y for x, y in xs) / 120.0
        vx = sum((x - mx) ** 2 for x, y in xs)
        beta[t] = (sum((x - mx) * (y - my) for x, y in xs) / vx) if vx > 0 else None
    for t in range(n):
        if beta[t] is None or t - 10 < brk[t]:
            continue
        d10[t] = math.log(ca[t] / ca[t - 10]) - beta[t] * math.log(cb[t] / cb[t - 10])
    z = [None] * n
    sdd = [None] * n
    for t in range(n):
        if d10[t] is None or t - 250 < brk[t]:
            continue
        w = [d10[q] for q in range(t - 249, t + 1) if d10[q] is not None]
        if len(w) < 200:
            continue
        mu = sum(w) / len(w)
        s = math.sqrt(sum((x - mu) ** 2 for x in w) / len(w))
        sdd[t] = s
        z[t] = d10[t] / s if s > 0 else None
    cost_a = spa["cost_bp"] / 1e4 + spa.get("cost_px", 0.0) / ca[-1]
    cost_b = spb["cost_bp"] / 1e4 + spb.get("cost_px", 0.0) / cb[-1]
    rows = []
    t = 0
    while t < n - 1:
        if z[t] is None or abs(z[t]) < 2.0 or era[t + 1] is None:
            t += 1
            continue
        side = 1 if z[t] > 0 else -1          # +1 = US500 is the leader
        b0 = beta[t]
        G = abs(d10[t])                        # the gap (10-day relative move) at the trigger, in log units
        S = lambda q: math.log(ca[q]) - b0 * math.log(cb[q])
        s0 = S(t)
        e = t + 1                              # entry at the open of the next common day
        x, lab = None, "time"
        for q in range(t + 1, min(n, t + 11)):
            if brk[q] != brk[t]:
                x, lab = q, "break"
                break
            g = side * (S(q) - s0)             # + = the gap widened since the trigger close
            if g <= -G:
                x, lab = q, "target"           # the whole gap closed (spread back to its level 10 days before)
                break
            if g >= 0.75 * G:
                x, lab = q, "stop"             # the gap widened by another 0.75 G (= z 2 -> 3.5)
                break
            x = q
        if x is None or lab == "break" or x + 1 >= n or brk[x + 1] != brk[t]:
            t += 1
            continue
        xo = x + 1                             # exit at the next open
        risk = 0.75 * G
        # #27: short the leader (US500 if side +1), long the laggard (beta-weighted)
        gpx = -side * (math.log(oa[xo] / oa[e]) - b0 * math.log(ob[xo] / ob[e]))
        cost = cost_a + abs(b0) * cost_b
        g27, g28 = gpx / risk, -gpx / risk
        n27, n28 = (gpx - cost) / risk, (-gpx - cost) / risk
        t_in, t_out = keys[e] * 86400.0, keys[xo] * 86400.0
        ctrl = (n27 + n28) / 2.0
        tg = {"_t_in": t_in, "_t_out": t_out, "_d": side, "_lab": lab}
        rows.append(("PAIR", "27 gap closes", "us-leads" if side > 0 else "ger-leads", "own", era[e], n27, ctrl, g27, dict(tg)))
        tg28 = dict(tg)
        tg28["_lab"] = {"target": "stop", "stop": "target"}.get(lab, lab)
        rows.append(("PAIR", "28 rel momentum", "us-leads" if side > 0 else "ger-leads", "own", era[e], n28, ctrl, g28, tg28))
        t = xo
    return rows


# ================================================================ report
def lane_report(rep, name, xs, P, core_m, yard):
    p = rep.p
    p("")
    p("=" * 110)
    p(name)
    p("=" * 110)
    if not xs:
        p("  no trades")
        return
    lab = (lambda x: x[8].get("_lab")) if xs[0][0] == "PAIR" else label

    def line(tag, ys):
        if not ys:
            return "   %-24s    0" % tag
        c = defaultdict(int)
        for y in ys:
            c[lab(y)] += 1
        net = P.cmean([(y[5], clu(y)) for y in ys])
        edge = P.cmean([(y[5] - y[6], clu(y)) for y in ys])
        win = 100.0 * sum(1 for y in ys if y[5] > 0) / len(ys)
        yrs = sum(time.gmtime(y[8]["_t_in"]).tm_year for y in ys)
        return "   %-24s %5d  win %5.1f%%  stop %4.0f%% target %4.0f%% time %4.0f%%  net %s  EDGE %s %s" % (
            tag, len(ys), win, 100.0 * c["stop"] / len(ys), 100.0 * c["target"] / len(ys), 100.0 * c["time"] / len(ys),
            P.f3(net[0]), P.f3(edge[0]), P.ft(edge[1]))
    p(line("ALL", xs))
    for h in ("OLD 2014-19", "NEW 2020-26"):
        p(line(h, [x for x in xs if half(x) == h]))
    vs = sorted(set(x[2] for x in xs))
    for v in vs:
        p(line("variant " + v, [x for x in xs if x[2] == v]))
    mks = sorted(set(x[0] for x in xs))
    if len(mks) > 1:
        for s in MARKETS:
            ys = [x for x in xs if x[0] == s]
            if ys:
                p(line(s + (" *" if s in EZIO_MK and name.startswith("#31") else ""), ys))
                for h in ("OLD 2014-19", "NEW 2020-26"):
                    hs = [x for x in ys if half(x) == h]
                    if hs:
                        p(line("   " + h, hs))
    # monthly correlation with the core book
    mon = defaultdict(float)
    for x in xs:
        tt = time.gmtime(x[8]["_t_in"])
        mon[(tt.tm_year, tt.tm_mon)] += x[5]
    for part in ("fast", "dip"):
        cm = core_m.get(part, {})
        ks = sorted(set(mon) | set(cm))
        if len(ks) < 12:
            continue
        a = [mon.get(k, 0.0) for k in ks]
        b = [cm.get(k, 0.0) for k in ks]
        ma, mb = sum(a) / len(a), sum(b) / len(b)
        va = sum((x - ma) ** 2 for x in a)
        vb = sum((x - mb) ** 2 for x in b)
        r = sum((x - ma) * (y - mb) for x, y in zip(a, b)) / math.sqrt(va * vb) if va > 0 and vb > 0 else None
        p("   monthly net-R correlation with core %-4s: %s  (%d months)" % (part, ("%+.2f" % r) if r is not None else "-",
                                                                            len(ks)))
    p("   labels: stop / target / time = which exit fired (see the spec); EDGE = net minus the coin-flip average, t")
    p("   clustered by market x month.")
    p(yard)


def main():
    argv = sys.argv[1:]
    synth = None
    dump = None
    placebo = "--placebo" in argv
    nocore = "--nocore" in argv
    if "--dump" in argv:
        k = argv.index("--dump")
        dump = os.path.abspath(argv[k + 1])
        del argv[k:k + 2]
    if "--db" in argv:
        k = argv.index("--db")
        synth = os.path.abspath(argv[k + 1])
        del argv[k:k + 2]
        if not os.path.exists(synth):
            print("no such file: %s" % synth)
            return
        A.find_db = lambda: synth
    import asiabo_lab as L
    import asiabo_why as W
    import asiabo_probe as P
    W._install()
    W.WITH_CHAN = False
    name = "young1"
    if synth:
        b = os.path.splitext(os.path.basename(synth))[0]
        for pre in ("synth_", "young_"):
            b = b[len(pre):] if b.startswith(pre) else b
        name = "young1_synth_" + b

        def add_only(src):
            try:
                vdir = os.path.join(A.ROOT, A.VISION_DIR_NAME)
                os.makedirs(vdir, exist_ok=True)
                for fn in os.listdir(src):
                    if os.path.isfile(os.path.join(src, fn)):
                        shutil.copy2(os.path.join(src, fn), os.path.join(vdir, fn))
                print("claude vision: added %s (no wipe)" % os.path.basename(src))
            except Exception as e:
                print("(claude vision not updated: %s)" % e)
        A.publish_to_vision = add_only
    rep = A.Report(name)
    p = rep.p
    t0 = time.time()
    if synth:
        p("#" * 110)
        p("SYNTHETIC DATA (a cousin of bars.db, NOT the real market): %s   -- a yardstick for the real run" % synth)
        p("#" * 110)
    p("=" * 110)
    p("YOUNGLING SCREEN, batch 1 (#31 mirror dip, #27/#28 US500-DAX pair, #19 squeeze breakout). Shadow only.")
    p("Rules + predictions: young_batch1_spec.md / the top of asiabo_young.py, written 2026-10-12 before any run.")
    p("=" * 110)
    p("Sealed exam years %s .. %s and Japan 225: not read." % (A.SEAL_START, A.SEAL_END))
    specs = dict((x["name"], x) for x in A.COLLECT_SYMBOLS)
    r31, r19, core_rows, det_all, DV = [], [], [], {}, {}
    pl31, pl19 = defaultdict(list), defaultdict(list)
    try:
        for s in MARKETS:
            if s not in specs:
                continue
            print("young: %s ..." % s)
            try:
                m = L.PMarket(specs[s])
            except RuntimeError as e:
                p("(%s skipped: %s)" % (s, e))
                continue
            dv = P.Day(m, L)
            DV[s] = dv
            W._m1_cache(m)
            a, b = [], []
            lane31(m, dv, L, a)
            lane19(m, dv, L, b)
            r31 += [(s,) + x for x in a]
            r19 += [(s,) + x for x in b]
            if placebo:
                for md in ("notrigger", "delay"):
                    c = []
                    lane31(m, dv, L, c, md)
                    pl31[md] += [(s,) + x for x in c]
                for md in ("nobreak", "delay"):
                    c = []
                    lane19(m, dv, L, c, md)
                    pl19[md] += [(s,) + x for x in c]
            if s in W.MARKETS and not nocore:
                rb = []
                for nm, fn in L.P_LANES:
                    if nm in L.P_OMEGA_LANES:
                        fn(m, rb)
                core_rows += [(s,) + x for x in rb if (x[0], x[1]) in W.NEED_LV]
                det_all.update(W.det_table(m))
            if m.m1q:
                m.m1q[0].close()
            m._m1cache.clear()
            del m
        r31, r19 = one_position(r31), one_position(r19)
        book = W.book_of(core_rows, det_all) if core_rows else []
        core_m = defaultdict(lambda: defaultdict(float))
        for x, part in book:
            tt = time.gmtime(x[8]["_t_in"])
            core_m[part][(tt.tm_year, tt.tm_mon)] += x[5]
        p("core book (for the correlations): " + ", ".join("%s %d" % (k, sum(1 for x, q in book if q == k))
                                                           for k in ("fast", "dip")))
        lane_report(rep, "#31 MIRROR DIP (Ezio) -- short the start of a pullback in a stretched trend", r31, P, core_m,
                    YARD["lanes"])
        pr = []
        if "US500" in DV and "GERMANY40" in DV:
            pr = pair(DV["US500"], DV["GERMANY40"], specs["US500"], specs["GERMANY40"])
        lane_report(rep, "#27 GAP CLOSES -- US500 vs GERMANY40 spread reversion", [x for x in pr if x[1].startswith("27")],
                    P, core_m, YARD["pair"])
        lane_report(rep, "#28 RELATIVE MOMENTUM -- the exact mirror of #27 on the same triggers",
                    [x for x in pr if x[1].startswith("28")], P, core_m, YARD["pair"])
        lane_report(rep, "#19 SQUEEZE BREAKOUT -- trade the break out of a 120-day-low bandwidth", r19, P, core_m,
                    YARD["lanes"])
        for md, xs in sorted(pl31.items()):
            lane_report(rep, "#31 PLACEBO %s" % md, one_position(xs), P, core_m, "")
        for md, xs in sorted(pl19.items()):
            lane_report(rep, "#19 PLACEBO %s" % md, one_position(xs), P, core_m, "")
        if dump:
            import json
            out = []
            allx = r31 + r19 + pr + [x for v in pl31.values() for x in one_position(v)] + \
                [x for v in pl19.values() for x in one_position(v)]
            for x in allx:
                out.append({"m": x[0], "lane": x[1], "var": x[2], "era": x[4], "net": x[5], "ctrl": x[6], "gross": x[7],
                            "lab": (x[8].get("_lab") if x[0] == "PAIR" else label(x)),
                            "t_in": x[8]["_t_in"], "t_out": x[8]["_t_out"]})
            tmp = dump + ".tmp"
            with open(tmp, "w") as f:
                json.dump(out, f)
            os.replace(tmp, dump)
            print("dumped %d trades -> %s" % (len(out), dump))
    except Exception:
        p("")
        p("FAILED:")
        p(traceback.format_exc())
    p("")
    p("runtime %.0fs" % (time.time() - t0))
    rep.save()


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
