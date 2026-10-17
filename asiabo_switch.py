"""
asiabo_switch.py  --  ONE pre-registered real-data test of the momentum SWITCH found in the regime engine (2026-10-10).

The switch (chosen in synthetic known-truth worlds; never used in any selection on real data, so every real era is fair):
    er40 = straightness of the last 40 daily closes = |close(-1) - close(-41)| / sum of |daily moves| over those 40 days,
    per market, known at the START of the entry day. SWITCH ON when er40 > 0.30 (fixed now: between the synth
    operating points 0.26 and 0.32). brk and fast trade only while their market's switch is on; ins and dip are never
    switched (shown for completeness). The switch is applied BEFORE the one-position rule, as it would run live.

PREDICTIONS AND VERDICT (written 2026-10-10 BEFORE this file ever ran on real data):
  P1  brk: switched edge/trade > unswitched edge/trade in at least 3 of 4 eras.
  P2  brk: the trades the switch turns away are about harmless: their pooled edge/trade is below the kept trades' with
      a clustered t of the difference >= 2 (kept minus turned away).
  P3  fast: as P1 (at least 3 of 4 eras).
  P4  YARDSTICK: the switch beats a RANDOM switch that keeps the same share of days per market (20 draws): its pooled
      edge/trade for brk is above the random switches' 90th percentile.
  BRK COMES OFF THE SHELF only if P1, P2 and P4 hold AND the switched brk passes the why-phase W3 rule that shelved it
  (net > 0 without its best market-year in at least 2 of 4 eras). Anything else: brk stays shelved, and we learn that
  real momentum regimes do not look like the model (or er40 does not read them in time).
  Secondary, EXPLORATORY ONLY (no verdict): an adaptive threshold (er40 above its own trailing 500-day 67th percentile).

    python asiabo_switch.py        (double-click: run_17_switch.bat)
"""
import os, sys, math, time, random, bisect, traceback
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import asiabo_offline as A

TH = 0.30
BRK_LANES = ("main2", "orb30", "orb60", "pdh2", "retest2")
RAND_DRAWS = 20


def er40_days(m):
    cl, seg = m.cl, m.seg
    out, hist = {}, []
    for j in range(1, len(m.D)):
        if j - 41 < seg[j]:
            continue
        path = sum(abs(cl[k] - cl[k - 1]) for k in range(j - 40, j))
        v = abs(cl[j - 1] - cl[j - 41]) / path if path else 0.0
        hist.append(v)
        h = sorted(hist[-500:])
        out[m.D[j][0]] = (v, h[int(0.67 * (len(h) - 1))] if len(h) >= 250 else None)
    return out


def main():
    import asiabo_lab as L
    import asiabo_why as W
    W._install()
    W.WITH_CHAN = False
    rep = A.Report("switch")
    p = rep.p
    t0 = time.time()
    p("=" * 110)
    p("THE MOMENTUM SWITCH on REAL data: one pre-registered test (rules and predictions: asiabo_switch.py top)")
    p("=" * 110)
    p("Switch: er40 (straightness of the last 40 daily closes) > %.2f, per market, known at the start of the entry day." % TH)
    p("Chosen in synthetic known-truth worlds (regime engine), never used on real data before. brk and fast only.")
    specs = dict((x["name"], x) for x in A.COLLECT_SYMBOLS)
    rows, det, er = [], {}, {}
    for s in W.MARKETS:
        if s not in specs:
            continue
        print("switch: %s ..." % s)
        m = L.PMarket(specs[s])
        W._m1_cache(m)
        rb = []
        for name, fn in L.P_LANES:
            if name in L.P_OMEGA_LANES:
                fn(m, rb)
        rows += [(s,) + x for x in rb if (x[0], x[1]) in W.NEED_LV]
        det.update(W.det_table(m))
        for k, v in er40_days(m).items():
            er[(s, k)] = v
        if m.m1q:
            m.m1q[0].close()
        m._m1cache.clear()
        del m, rb
    is_trend = lambda x: x[1] in BRK_LANES
    erv = lambda x: er.get((x[0], x[8].get("_dk")))

    def gate_fixed(x):
        v = erv(x)
        return v is not None and v[0] > TH

    def gate_adapt(x):
        v = erv(x)
        return v is not None and v[1] is not None and v[0] > v[1]
    base = W.book_of(rows, det)
    sw = W.book_of([x for x in rows if not is_trend(x) or gate_fixed(x)], det)
    ad = W.book_of([x for x in rows if not is_trend(x) or gate_adapt(x)], det)
    # the trades the switch turned away = in the unswitched book, entered on a switch-off day
    eras = W.ERAS

    def cell(bk, part, era):
        xs = [x for x, q in bk if q == part and (era == "ALL" or x[4] == era)]
        n, net, edge, tot = W.pstats(xs)
        return n, net, edge, tot, W.ct(xs)[1], xs
    p("")
    p("A. EACH PART, unswitched vs switched (edge = cost-free direction value; net = after real costs; R/yr = net):")
    verdict = {}
    for part in ("brk", "fast", "ins", "dip"):
        p("")
        p("  %s" % part)
        wins = 0
        for era in eras + ["ALL"]:
            a = cell(base, part, era)
            b = cell(sw, part, era)
            c = cell(ad, part, era)
            yrs = W.EY.get(era, sum(W.EY.values()))
            if era != "ALL" and a[2] is not None and b[2] is not None and b[2] > a[2]:
                wins += 1
            p("    %-10s unswitched n%4d edge %s (t %s) net %s %+6.1f R/yr | SWITCHED n%4d edge %s (t %s) net %s %+6.1f R/yr"
              " | adaptive n%4d edge %s" % (
                  era, a[0], W._f(a[2]), "%+.1f" % a[4] if a[4] is not None else "-", W._f(a[1]), a[3] / yrs,
                  b[0], W._f(b[2]), "%+.1f" % b[4] if b[4] is not None else "-", W._f(b[1]), b[3] / yrs,
                  c[0], W._f(c[2])))
        verdict[part] = wins
        p("    -> switched edge above unswitched in %d of 4 eras" % wins)
    # P2: turned-away vs kept (brk), on the unswitched book
    p("")
    p("B. P2: brk trades of the UNSWITCHED book split by the switch on their entry day (kept vs turned away):")
    xs = [x for x, q in base if q == "brk"]
    ind = [1 if gate_fixed(x) else 0 for x in xs]
    y = [x[5] - x[6] for x in xs]
    cl = [W._cl(x) for x in xs]
    n1 = sum(ind)
    m1 = sum(v for v, i in zip(y, ind) if i) / max(1, n1)
    m0 = sum(v for v, i in zip(y, ind) if not i) / max(1, len(y) - n1)
    import asiabo_hunt as Hh
    b_, t_, _, _ = Hh._diff_t(y, cl, ind)
    p2 = t_ is not None and t_ >= 2
    p("    kept %d trades edge %+.3f | turned away %d trades edge %+.3f | difference %+.3f, clustered t %s -> P2 %s" % (
        n1, m1, len(y) - n1, m0, b_ or 0, "%+.1f" % t_ if t_ is not None else "-", "HOLDS" if p2 else "FAILS"))
    for era in eras:
        e = [(v, i) for v, i, x in zip(y, ind, xs) if x[4] == era]
        k = [v for v, i in e if i]
        a_ = [v for v, i in e if not i]
        p("      %-10s kept %4d edge %s | turned away %4d edge %s" % (
            era, len(k), W._f(sum(k) / len(k) if k else None), len(a_), W._f(sum(a_) / len(a_) if a_ else None)))
    # P4: random switches with the same share of days per market
    p("")
    p("C. P4 YARDSTICK: %d random switches, each keeping the same SHARE of days per market as the real switch:" % RAND_DRAWS)
    days = defaultdict(list)
    for (s, k), v in er.items():
        days[s].append(k)
    share = dict((s, sum(1 for k in ks if er[(s, k)][0] > TH) / float(len(ks))) for s, ks in days.items())
    rnd = random.Random(20261010)
    rs_brk, rs_fast = [], []
    for dr in range(RAND_DRAWS):
        on = set()
        for s, ks in days.items():
            for k in ks:
                if rnd.random() < share[s]:
                    on.add((s, k))
        bk = W.book_of([x for x in rows if not is_trend(x) or (x[0], x[8].get("_dk")) in on], det)
        rs_brk.append(cell(bk, "brk", "ALL")[2])
        rs_fast.append(cell(bk, "fast", "ALL")[2])
    real_b, real_f = cell(sw, "brk", "ALL")[2], cell(sw, "fast", "ALL")[2]
    sb, sf = sorted(rs_brk), sorted(rs_fast)
    q90 = lambda s: s[int(0.9 * (len(s) - 1))]
    p4 = real_b is not None and real_b > q90(sb)
    p("    days switched on per market: " + ", ".join("%s %.0f%%" % (s, 100 * v) for s, v in sorted(share.items())))
    p("    brk  real switch edge %s | random switches: median %s, 90th percentile %s, max %s -> P4 %s" % (
        W._f(real_b), W._f(sb[len(sb) // 2]), W._f(q90(sb)), W._f(sb[-1]), "HOLDS" if p4 else "FAILS"))
    p("    fast real switch edge %s | random switches: median %s, 90th percentile %s, max %s" % (
        W._f(real_f), W._f(sf[len(sf) // 2]), W._f(q90(sf)), W._f(sf[-1])))
    # W3 rule on switched brk
    p("")
    p("D. THE RULE THAT SHELVED brk (why phase W3), on the SWITCHED brk: net without its best market-year, per era")
    alive = 0
    for era in eras:
        xs = [x for x, q in sw if q == "brk" and x[4] == era]
        if not xs:
            p("    %-10s no trades" % era)
            continue
        tot = sum(x[5] for x in xs)
        my = defaultdict(float)
        for x in xs:
            my["%s %d" % (x[0], time.gmtime(x[8]["_t_in"]).tm_year)] += x[5]
        best = max(my, key=my.get)
        wo = tot - my[best]
        alive += wo > 0
        p("    %-10s n %4d net %+7.1f R | best market-year %-15s %+6.1f R | without it %+7.1f R" % (
            era, len(xs), tot, best, my[best], wo))
    w3 = alive >= 2
    p("    -> net > 0 without the best market-year in %d of 4 eras -> W3 %s" % (alive, "PASSED" if w3 else "FAILED"))
    # money
    p("")
    p("E. MONEY ($10,000, fixed risk brk 0.25 / ins 0.25 / dip 0.50 / fast 0.10 %, the lab's K4 engine):")
    core = [(x, 1.0, s, L.K5_BASE[s]) for x, s in base if s in ("fast", "dip")]
    core_sw = [(x, 1.0, s, L.K5_BASE[s]) for x, s in sw if s in ("fast", "dip")]
    brk_sw = [(x, 1.0, s, L.K5_BASE[s]) for x, s in sw if s == "brk"]
    full = [(x, 1.0, s, L.K5_BASE[s]) for x, s in base]
    L._k_money(rep, "core now (fast + dip)", core, 10000.0)
    L._k_money(rep, "core, fast switched", core_sw, 10000.0)
    L._k_money(rep, "core switched + brk switched", core_sw + brk_sw, 10000.0)
    L._k_money(rep, "old frozen book (all 4, no switch)", full, 10000.0)
    # verdict
    p1, p3 = verdict["brk"] >= 3, verdict["fast"] >= 3
    p("")
    p("=" * 110)
    p("VERDICT (pre-registered): P1 brk %s (%d of 4) | P2 %s | P3 fast %s (%d of 4) | P4 %s | W3 on switched brk %s" % (
        "HOLDS" if p1 else "FAILS", verdict["brk"], "HOLDS" if p2 else "FAILS", "HOLDS" if p3 else "FAILS",
        verdict["fast"], "HOLDS" if p4 else "FAILS", "PASSED" if w3 else "FAILED"))
    p("brk %s" % ("COMES OFF THE SHELF as 'momentum markets only' (er40 > %.2f)" % TH if (p1 and p2 and p4 and w3)
                  else "STAYS SHELVED"))
    p("fast switch: %s" % ("worth adopting (P3 holds)" if p3 else "not shown; fast stays as it is"))
    p("=" * 110)
    p("runtime %.0fs" % (time.time() - t0))
    rep.save()


if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        if sys.stdin and sys.stdin.isatty():
            input("\nerror above. Press Enter to close.")
