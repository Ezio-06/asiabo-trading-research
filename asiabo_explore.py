#!/usr/bin/env python3
"""
asiabo_explore.py  --  every living candidate, measured on the TRAINING data (Ezio, 2026-10-13: "build all and test them
over our training data first to see what reality says about it"). Spec + predictions: explore_spec.md (project).

    python asiabo_explore.py                              all sections, training data (bars.db; sealed 2022-23 skipped)
    python asiabo_explore.py --db X --markets XAUUSD,US500 --unlock     one db (cloud yardstick on fake random walks)

!! EXPLORATION, NOT CONFIRMATION. Every number here comes from data the ideas were born on (or near). A good result
   earns a fresh-data test; a bad result on training data is strong evidence (an idea that can't even fit its own
   data is dead). Nothing here changes the book. SHADOW ONLY: reads, measures, writes its report.

SECTIONS (all fixed before the run; no parameter is tuned here)
  F   fast per market: the frozen book's fast part on all six markets (XAUUSD US500 GERMANY40 USDJPY are the book's;
      EURUSD XTIUSD are T8's 'should not work' controls). Net, EDGE vs coin flip, per lane, per era.
  N5  flat means undecided: every fast trade read at entry + 2h: up (>= +0.3R), flat, down (<= -0.3R). Rest of the
      day (2h -> close) for the trade AND for its mirror (opposite direction, mirrored stop, same path). The
      theory needs: flat group > 0, mirror flat group <= 0, on more than gold. London-hour profile of the flat group.
  N3  fade only against-trend breaks: raw orb30 / main2 breakouts (exit at the close, no detector filter), split by
      edge20 (the 20-day trend at entry): WITH / NONE / AGAINST. The fade of an against-trend break = its mirror
      trade (same timing, opposite direction, mirrored stop, same costs). First look only: the mirror's stop is the
      break's stop geometry, not the 'beyond the extreme + buffer' stop the old fade lesson asks for.
  N4  the trend option, ONE design fixed by Claude (the precondition and direction were left open by Ezio):
        precondition  an inside day whose range < 0.4 x ATR20 (the compression hint from spent data)
        direction     the first daily break of that inside day's box within the next 3 days (both sides on one day
                      and no gap = skipped, too ambiguous on daily bars); entry at the box edge, or the open on a gap
        price stop    far side of the box + 1.0 x ATR50 (structure + a long ATR: the compression trap)
        time stop     at the close of the 10th day, out if the close is below +1R ('no trend came')
        winners       chandelier trail 3 x ATR50 from the best high (low) since entry, no target; max 60 days
        control       the mirror (same day, opposite direction, mirrored stop, same rules), costs on both
      Also: trend lengths per market (zigzag legs with a 3 x ATR20 reversal on closes). Spends nothing.
  DIP the regime rule (T30): dip skipped while ATR(w) >= 1.3 x its 1-year median AND rising (above its value 5 days
      earlier). ATR 40 is the candidate gauge (seen first on spent data, flagged); 5 / 10 / 20 shown alongside.
      Indices: US500 2016-19 (exam db) + 2020+ and GERMANY40 (bars.db) + US Tech 100 (spent for dip). Skipped vs kept.

NOISE BARS (set 2026-10-13 BEFORE any real run: 6 fake worlds, gold / US500 / GER40 / USDJPY as random walks with
  clustered volatility and no direction memory; full table in explore_spec.md). Noise reached:
  F    one market's fast EDGE  -0.10 .. +0.06 (t -1.8 .. +1.3)       -> bar: EDGE > +0.08 AND t > +2
  N5   one market's flat group -0.15 .. +0.13 (t -2.6 .. +1.5)       -> bar: > +0.15, t > +2, mirror <= 0
       book markets without gold, pooled  -0.08 .. +0.03            -> bar: > +0.06 AND t > +2
  N3   one market's against-trend FADE EDGE  -0.10 .. +0.13 (t up to +2.6)  -> bar: > +0.14, t > +2.6, AND fade NET > 0
  N4   pooled EDGE  -0.04 .. +0.08 (t <= 1.3); in every noise world the top 5% of trades carried the whole total, so
       'the tail pays' is NOT evidence by itself              -> bar: pooled EDGE > +0.10 AND t > +2
  DIP  pooled skipped-minus-kept on ATR 40  -0.18 .. +0.40 (t -0.6 .. +2.0)  -> bar: < -0.35 AND t < -2
  An idea is ALIVE ON TRAINING DATA if it clears its bar and is positive in at least 2 of the 3 eras. Clearing it earns
  a fresh-data test, nothing more.
"""
import os, sys, time, math, statistics as st, traceback
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import asiabo_offline as A

SIX = ("XAUUSD", "US500", "GERMANY40", "USDJPY", "EURUSD", "XTIUSD")
BOOK_FAST = ("XAUUSD", "US500", "GERMANY40", "USDJPY")
ERAS = [("2014-17", "2014-01-01", "2018-01-01"), ("2018-21", "2018-01-01", "2022-01-01"), ("2024+", "2024-01-01", "2100-01-01")]
N3_LANES = {("orb30", "range"), ("main2", "box")}
UPF, DNF = 0.3, -0.3
# N4 (fixed before the run)
N4_INSIDE, N4_WAIT, N4_BUF, N4_TDAY, N4_TR, N4_TRAIL, N4_MAX = 0.4, 3, 1.0, 10, 1.0, 3.0, 60
ZZ = 3.0


def era_of(t):
    for nm, a, b in ERAS:
        if A.epoch_of(a) <= t < A.epoch_of(b):
            return nm
    return None


def clu_t(mk, t):
    tt = time.gmtime(t)
    return (mk, tt.tm_year, tt.tm_mon)


def tstr(t):
    return ("%+.1f" % t) if t is not None else "  -"


# ============================================================ F: fast per market
def line(p, P, tag, xs):
    """xs: [(net, coin, cluster)]"""
    if not xs:
        p("   %-24s     0" % tag)
        return
    net = P.cmean([(a, c) for a, b, c in xs])
    ed = P.cmean([(a - b, c) for a, b, c in xs])
    p("   %-24s n %5d  win %3.0f%%  net %+.3f (t %s)  EDGE %+.3f (t %s)  total %+7.1f R" % (
        tag, len(xs), 100.0 * sum(1 for a, b, c in xs if a > 0) / len(xs), net[0], tstr(net[1]), ed[0], tstr(ed[1]),
        sum(a for a, b, c in xs)))


def fast_rows(x):
    return (x[5], x[6], clu_t(x[0], x[8]["_t_in"]))


# ============================================================ N5: the 2h read and the rest of the day
def lon_hour(t):
    return int((t + A._clock_shift(A.CLOCK_EU, t) + 3600.0) % 86400 // 3600)


def walk_2h(m, x, d_sign):
    """R path of a fast trade (d_sign=+1) or its mirror (-1): (r2, fin, hourly [(london hour, dR)] after 2h)."""
    t = x[8]
    e, sd, d = t["_e"], t["_sd"], t["_d"] * d_sign
    stop = e - d * sd
    B = []
    for i in range(t["_j0"], min((t["_ci"] or t["_j0"] + 96), m.n - 1) + 1):
        B += [b for b in m.m1t(i) if b[0] >= t["_t_in"]]
    t2 = t["_t_in"] + 7200
    r2 = fin = None
    hours = []
    prev = ph = None
    for (ts, o, h, l, c) in B:
        if (d > 0 and l <= stop) or (d < 0 and h >= stop):
            if r2 is not None and prev is not None:
                hours.append((ph, -1.0 - prev))
            fin = -1.0
            break
        r = (c - e) * d / sd
        if r2 is None and ts >= t2:
            r2 = r
            prev, ph = r, lon_hour(ts)
        elif r2 is not None:
            hh = lon_hour(ts)
            if hh != ph:
                hours.append((ph, r - prev))
                prev, ph = r, hh
        fin = r
    if r2 is None or fin is None:
        return None
    if prev is not None and fin != -1.0:
        hours.append((ph, fin - prev))
    return r2, fin, hours


def n5_market(m, fast):
    out = []
    for x in fast:
        a = walk_2h(m, x, 1)
        b = walk_2h(m, x, -1)
        if a is None or b is None:
            continue
        g = "up" if a[0] >= UPF else ("down" if a[0] <= DNF else "flat")
        out.append({"g": g, "rest": a[1] - a[0], "mrest": b[1] - b[0], "hours": a[2], "mk": x[0],
                    "clu": clu_t(x[0], x[8]["_t_in"]), "era": era_of(x[8]["_t_in"])})
    return out


def n5_report(p, P, rows, tag):
    p("")
    p("  N5 %s: %d fast trades with a 2h reading. Rest of the day = R from the 2h mark to the exit (close or stop)." % (tag, len(rows)))
    for g in ("up", "flat", "down"):
        xs = [r for r in rows if r["g"] == g]
        if not xs:
            continue
        a = P.cmean([(r["rest"], r["clu"]) for r in xs])
        b = P.cmean([(r["mrest"], r["clu"]) for r in xs])
        eras = []
        for nm, _, _ in ERAS:
            ys = [r for r in xs if r["era"] == nm]
            if ys:
                eras.append("%s %+.2f (n %d)" % (nm, st.mean(r["rest"] for r in ys), len(ys)))
        p("   %-5s n %4d  trade %+.3f (t %s)  mirror %+.3f (t %s)  |  %s" % (g, len(xs), a[0], tstr(a[1]), b[0], tstr(b[1]), "  ".join(eras)))
    fl = [r for r in rows if r["g"] == "flat"]
    acc = defaultdict(list)
    for r in fl:
        for hh, dv in r["hours"]:
            acc[hh].append(dv)
    tops = sorted(((st.mean(v), hh, len(v)) for hh, v in acc.items() if len(v) >= 20), reverse=True)[:3]
    if tops:
        p("   flat group, best London hours (mean R gained in that hour): " +
          "  ".join("%02d:00 %+.3f (n %d)" % (hh, mu, n) for mu, hh, n in tops))


# ============================================================ N3: with / none / against the 20-day trend
def n3_rows(rows, det):
    out = defaultdict(list)
    for x in rows:
        if (x[1], x[2]) not in N3_LANES or x[3] != "close" or x[6] is None or not x[8].get("_t_in"):
            continue
        t = x[8]
        dd = det.get((x[0], t.get("_dk")))
        if not dd or t.get("_d") is None or "edge20" not in dd:
            continue
        v = dd["edge20"]
        k = "WITH" if v == t["_d"] else ("AGAINST" if v == -t["_d"] else "NONE")
        mir = 2.0 * x[6] - x[5]
        out[k].append((x[5], mir, x[6], clu_t(x[0], t["_t_in"]), x[1], era_of(t["_t_in"])))
    return out


def n3_report(p, P, g, tag):
    p("")
    p("  N3 %s: raw orb30 + main2 breaks (exit at the close), by the 20-day trend at entry. FADE = the mirror trade." % tag)
    for k in ("WITH", "NONE", "AGAINST"):
        xs = g.get(k, [])
        if not xs:
            p("   %-8s 0" % k)
            continue
        ride = P.cmean([(a, c) for a, mr, cf, c, ln, er in xs])
        fade = P.cmean([(mr, c) for a, mr, cf, c, ln, er in xs])
        ed = P.cmean([(a - cf, c) for a, mr, cf, c, ln, er in xs])
        eras = "  ".join("%s fade %+.2f (n %d)" % (nm, st.mean(x[1] for x in xs if x[5] == nm), sum(1 for x in xs if x[5] == nm))
                         for nm, _, _ in ERAS if any(x[5] == nm for x in xs))
        p("   %-8s n %5d  RIDE net %+.3f (t %s)  FADE net %+.3f (t %s)  ride EDGE %+.3f (t %s; fade EDGE = minus this) | %s" % (
            k, len(xs), ride[0], tstr(ride[1]), fade[0], tstr(fade[1]), ed[0], tstr(ed[1]), eras))


# ============================================================ N4: trend lengths and the one fixed design
def zigzag(dv):
    """legs of a 3 x ATR20 reversal zigzag on closes, inside each data segment: [(days, move in ATR)]"""
    legs = []
    sg = None
    for j in range(dv.n):
        N = dv.N[j]
        if N is None:
            continue
        c = dv.cl[j]
        if dv.seg[j] != sg:                      # new data segment: restart, undecided
            sg, j0, piv, hi, jh, lo, jl, u = dv.seg[j], j, c, c, j, c, j, 0
            continue
        if c > hi:
            hi, jh = c, j
        if c < lo:
            lo, jl = c, j
        if u == 0:
            if hi - piv >= ZZ * N:
                u = 1
            elif piv - lo >= ZZ * N:
                u = -1
            continue
        if u == 1 and hi - c >= ZZ * N:          # up leg ends at the high
            legs.append((jh - j0, (hi - piv) / N))
            j0, piv, u, lo, jl = jh, hi, -1, c, j
        elif u == -1 and c - lo >= ZZ * N:       # down leg ends at the low
            legs.append((jl - j0, (piv - lo) / N))
            j0, piv, u, hi, jh = jl, lo, 1, c, j
    return [l for l in legs if l[0] > 0]


def pct(xs, q):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(q * len(xs)))]


def n4_trades(dv, spec):
    out = []
    busy = -1
    for j in range(60, dv.n - 2):
        if j <= busy or dv.seg[j] != dv.seg[j - 1]:
            continue
        if not (dv.hi[j] < dv.hi[j - 1] and dv.lo[j] > dv.lo[j - 1]):
            continue
        a20, a50 = dv.atr(j + 1, 20), dv.atr(j + 1, 50)
        if not a20 or not a50 or dv.hi[j] - dv.lo[j] >= N4_INSIDE * a20:
            continue
        H, Lo = dv.hi[j], dv.lo[j]
        ent = None
        for k in range(j + 1, min(j + 1 + N4_WAIT, dv.send[j] + 1)):
            o, h, l = dv.o[k], dv.hi[k], dv.lo[k]
            if o > H:
                ent = (k, 1, o)
            elif o < Lo:
                ent = (k, -1, o)
            elif h > H and l < Lo:
                ent = "amb"
            elif h > H:
                ent = (k, 1, H)
            elif l < Lo:
                ent = (k, -1, Lo)
            if ent:
                break
        if not ent or ent == "amb":
            continue
        k, d, e = ent
        risk = abs(e - ((Lo - N4_BUF * a50) if d > 0 else (H + N4_BUF * a50)))
        if risk <= 0:
            continue
        res = []
        last = k
        for dd in (d, -d):                       # the trade, then its mirror (same distance on the other side)
            stop = e - dd * risk
            moved = False
            best = e
            q = k
            while True:
                o, h, l, c = dv.o[q], dv.hi[q], dv.lo[q], dv.cl[q]
                if q > k and ((dd > 0 and o <= stop) or (dd < 0 and o >= stop)):
                    ex = (q, o, "trail" if moved else "price")
                    break
                if (dd > 0 and l <= stop) or (dd < 0 and h >= stop):
                    ex = (q, stop, "trail" if moved else "price")
                    break
                best = max(best, h) if dd > 0 else min(best, l)
                held = q - k + 1
                if held == N4_TDAY and (c - e) * dd < N4_TR * risk:
                    ex = (q, c, "time")
                    break
                if held >= N4_MAX or q >= dv.send[k] or q >= dv.n - 1:
                    ex = (q, c, "max")
                    break
                ns = best - dd * N4_TRAIL * a50
                if (dd > 0 and ns > stop) or (dd < 0 and ns < stop):
                    stop, moved = ns, True
                q += 1
            cost = A._cost_px(spec, e) / risk
            res.append(((ex[1] - e) * dd / risk - cost, ex[2], ex[0] - k + 1))
            last = max(last, ex[0])
        if not res:
            continue
        busy = last
        t = dv.key[k] * 86400.0
        out.append({"R": res[0][0], "why": res[0][1], "days": res[0][2], "mR": res[1][0], "clu": dv.clu[k], "era": era_of(t), "d": d})
    return out


def n4_report(p, P, tr, tag, legs):
    p("")
    if legs:
        L_ = [a for a, b in legs]
        p("  N4 %s trend legs (zigzag, 3 x ATR20 reversal): %d legs  days median %d  p75 %d  p90 %d  p95 %d  max %d | "
          ">= 20 days %.0f%%  >= 40 days %.0f%%  | move median %.1f ATR, p90 %.1f ATR" % (
              tag, len(L_), pct(L_, .5), pct(L_, .75), pct(L_, .9), pct(L_, .95), max(L_),
              100.0 * sum(1 for a in L_ if a >= 20) / len(L_), 100.0 * sum(1 for a in L_ if a >= 40) / len(L_),
              pct([b for a, b in legs], .5), pct([b for a, b in legs], .9)))
    if not tr:
        p("  N4 %s: no trades" % tag)
        return
    a = P.cmean([(x["R"], x["clu"]) for x in tr])
    b = P.cmean([(x["mR"], x["clu"]) for x in tr])
    ed = P.cmean([(x["R"] - (x["R"] + x["mR"]) / 2.0, x["clu"]) for x in tr])
    rs = sorted((x["R"] for x in tr), reverse=True)
    top = rs[:max(1, int(round(0.05 * len(rs))))]
    tot = sum(rs)
    why = defaultdict(list)
    for x in tr:
        why[x["why"]].append(x["R"])
    p("  N4 %s design: n %d  win %.0f%%  net %+.3f (t %s)  mirror %+.3f (t %s)  EDGE %+.3f (t %s)  total %+.1f R | top 5%% "
      "trades = %+.1f R (total without them %+.1f) | longs %d shorts %d" % (
          tag, len(tr), 100.0 * sum(1 for r in rs if r > 0) / len(rs), a[0], tstr(a[1]), b[0], tstr(b[1]), ed[0], tstr(ed[1]),
          tot, sum(top), tot - sum(top), sum(1 for x in tr if x["d"] > 0), sum(1 for x in tr if x["d"] < 0)))
    p("      exits: " + "  ".join("%s n %d avg %+.2f R" % (k, len(v), st.mean(v)) for k, v in sorted(why.items())) +
      "   | eras: " + "  ".join("%s %+.2f (n %d)" % (nm, st.mean(x["R"] for x in tr if x["era"] == nm), sum(1 for x in tr if x["era"] == nm))
                               for nm, _, _ in ERAS if any(x["era"] == nm for x in tr)))


# ============================================================ one market: F, N5, N3, N4
def run_market(p, P, L, W, mk, pool):
    spec = dict((x["name"], x) for x in A.COLLECT_SYMBOLS)[mk]
    print("explore: %s ..." % mk)
    m = L.PMarket(spec)
    if not m.n:
        p("(%s: no bars)" % mk)
        return
    W._m1_cache(m)
    rb = []
    for nm, fn in L.P_LANES:
        if nm in L.P_OMEGA_LANES:
            fn(m, rb)
    rows = [(mk,) + x for x in rb if (x[0], x[1]) in W.NEED_LV]
    det = W.det_table(m)
    fast = [x for x, part in W.book_of(rows, det) if part == "fast"]
    p("")
    p("=" * 120)
    p("%s   (%s market for fast)" % (mk, "a BOOK" if mk in BOOK_FAST else "a CONTROL (T8: should not work)"))
    p("=" * 120)
    p("  F fast:")
    line(p, P, "fast ALL", [fast_rows(x) for x in fast])
    for lane in ("orb30", "main2"):
        line(p, P, "  " + lane, [fast_rows(x) for x in fast if x[1] == lane])
    for nm, a, b in ERAS:
        line(p, P, "  " + nm, [fast_rows(x) for x in fast if A.epoch_of(a) <= x[8]["_t_in"] < A.epoch_of(b)])
    pool["F"][mk] = [fast_rows(x) for x in fast]
    n5 = n5_market(m, fast)
    n5_report(p, P, n5, mk)
    pool["N5"] += [r for r in n5 if mk in BOOK_FAST]
    g = n3_rows(rows, det)
    n3_report(p, P, g, mk)
    for k, v in g.items():
        pool["N3"][k] += v
    dv = P.Day(m, L)
    legs = zigzag(dv)
    n4 = n4_trades(dv, spec)
    n4_report(p, P, n4, mk, legs)
    pool["N4"] += n4
    pool["LEGS"] += legs
    if m.m1q:
        m.m1q[0].close()
    m._m1cache.clear()


# ============================================================ DIP regime rule (reuses asiabo_dipvol)
def dip_section(p, P, L, one_db, markets):
    import asiabo_dipvol as DV
    import asiabo_dipdrift as DD
    DD.register_spec()
    DV.PRIMARY = 40
    hold = os.path.join(A.ROOT, "exam_hold")
    bars = A.find_db()
    if one_db:
        runs = [(one_db, mk, True, None, None) for mk in markets if mk in ("US500", "GERMANY40", "USTECH100")]
    else:
        runs = [(os.path.join(hold, "exam_us500.db"), "US500", False, "2016-01-01", "2020-01-01"),
                (bars, "US500", False, "2020-01-01", "2100-01-01"),
                (bars, "GERMANY40", False, None, None),
                (os.path.join(hold, "ustech100.db"), "USTECH100", True, None, None)]
    keep_find, keep_unlock = A.find_db, A.EXAM_UNLOCK
    allt = []
    p("")
    p("=" * 120)
    p("DIP: skip while ATR(w) >= 1.3 x its 1-year median AND rising. Candidate gauge ATR 40 (marked *; seen first on spent data).")
    p("=" * 120)
    for db, mk, unlock, w0, w1 in runs:
        if not db or not os.path.exists(db):
            p("(missing %s for %s: skipped)" % (db, mk))
            continue
        A.find_db = (lambda d=db: d)
        A.EXAM_UNLOCK = unlock
        print("explore dip: %s from %s ..." % (mk, os.path.basename(db)))
        tr = DV.run_market(L, DD, mk, w0, w1)
        p("%s %s: %d dip trades%s" % (mk, os.path.basename(db), len(tr), (" (%s .. %s)" % (w0, w1)) if w0 else ""))
        allt += tr
    A.find_db, A.EXAM_UNLOCK = keep_find, keep_unlock
    for mk in sorted(set(x["mk"] for x in allt)):
        DV.report(p, P, [x for x in allt if x["mk"] == mk], mk)
    if allt:
        DV.report(p, P, allt, "DIP: ALL INDICES POOLED")


def main():
    argv = sys.argv[1:]

    def opt(name):
        if name in argv:
            i = argv.index(name)
            v = argv[i + 1]
            del argv[i:i + 2]
            return v
        return None
    one_db, mks = opt("--db"), opt("--markets")
    unlock = "--unlock" in argv
    skip_dip = "--nodip" in argv
    markets = tuple(mks.split(",")) if mks else SIX
    rep = A.Report("explore" if not one_db else "explore_synth")
    p = rep.p
    p("=" * 120)
    p("EXPLORE: every living candidate on the TRAINING data (explore_spec.md). EXPLORATION, NOT CONFIRMATION.")
    p("Sealed years 2022-23 are never read. t = clustered by market x month. EDGE = net minus the coin flip (same timing).")
    p("=" * 120)
    try:
        import asiabo_lab as L
        import asiabo_why as W
        import asiabo_probe as P
        W._install()
        W.WITH_CHAN = False
        W.BRK_MK = SIX                       # fast measured on every market (EURUSD / XTIUSD as T8 controls)
        if one_db:
            dbp = os.path.abspath(one_db)
            A.find_db = (lambda d=dbp: d)
            A.EXAM_UNLOCK = unlock
        pool = {"F": {}, "N5": [], "N3": defaultdict(list), "N4": [], "LEGS": []}
        for mk in markets:
            if mk == "USTECH100":
                continue
            try:
                run_market(p, P, L, W, mk, pool)
            except Exception:
                p("%s FAILED:\n%s" % (mk, traceback.format_exc()))
        p("")
        p("=" * 120)
        p("POOLED")
        p("=" * 120)
        p("  F fast, book markets pooled vs controls pooled:")
        line(p, P, "book (gold+US500+GER+JPY)", sum((v for k, v in pool["F"].items() if k in BOOK_FAST), []))
        line(p, P, "book without gold", sum((v for k, v in pool["F"].items() if k in BOOK_FAST and k != "XAUUSD"), []))
        line(p, P, "controls (EURUSD+WTI)", sum((v for k, v in pool["F"].items() if k not in BOOK_FAST), []))
        n5_report(p, P, pool["N5"], "book markets pooled")
        n5_report(p, P, [r for r in pool["N5"] if r["mk"] != "XAUUSD"], "book markets WITHOUT gold")
        n3_report(p, P, pool["N3"], "all markets pooled")
        n4_report(p, P, pool["N4"], "all markets pooled", pool["LEGS"])
        if not skip_dip:
            dip_section(p, P, L, one_db and os.path.abspath(one_db), markets)
    except Exception:
        p(traceback.format_exc())
    rep.save()


if __name__ == "__main__":
    main()
