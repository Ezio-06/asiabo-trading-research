#!/usr/bin/env python3
"""
asiabo_trendwhy.py  --  the trend option: HOW we won, HOW we lost, and what we can't explain (2026-10-13).
Spec + predictions: trendwhy_spec.md (project). SHADOW ONLY. Training data (bars.db, sealed 2022-23 never read).

    python asiabo_trendwhy.py                                  the six house markets
    python asiabo_trendwhy.py --db X --markets XAUUSD --unlock  one db (cloud mechanics on fake data)

Not a disproving test (Ezio's rule, 2026-10-13): the trend option already beat its noise bar (explore: EDGE +0.33,
t 3.8 vs noise max +0.08). This breaks the SAME trades down to see WHY: where the money arrives, what kind of loss
costs us, and what our theory does not explain. Nothing here is a filter; buckets are descriptive.

THE TRADE (explore's design, with ONE measurement fix): an inside day narrower than 0.4 x ATR20; enter on the first
break of its box within 3 days (box edge, or the open on a gap); stop beyond the box + 1 x ATR50; out at the close of
day 10 if below +1R; otherwise trail 3 x ATR50 from the best price; max 60 days. Every trade has a mirror twin.
  FIX (found 2026-10-13 while building this): explore read the break on DAILY bars and skipped any day that touched
  both sides of the box. That uses the end of the day to choose which trades exist: days that broke up and then
  fell through the whole box (bad for the trade) were thrown away, which flatters the break day. Here the break is
  read in time order on M15 bars (M1 inside a bar that touches both sides), and the entry day's stop / best price use
  only the bars from the entry on. Explore's trend-option numbers are therefore biased upward by an unknown amount.

WHAT IT REPORTS (fixed before the run)
  A  WHERE THE MONEY ARRIVES: each trade's R split into the break day (entry -> close of day 1), days 2-10, and after
     day 10. Trade vs mirror.
  B  OUTCOME TYPES (every trade gets exactly one):
       BIG WIN      R >= +2                      (the trend came: what the theory is for)
       SMALL WIN    0 < R < +2, trail or max exit
       TIME WIN     R > 0 at the day-10 time stop (no trend came, but we ended up: theory does not predict this)
       FAST WRONG   price stop within the first 3 days (it reversed at once)
       SLOW WRONG   price stop after day 3
       NO TREND     R <= 0 at the day-10 time stop (the option expired)
       GAVE BACK    R <= 0 on a trail exit
     Count, average R, share of the total, and the same for the mirror.
  C  WINNERS VS LOSERS BY ENTRY CONDITION (descriptive only, never a filter):
       box tightness (box range / ATR20: < 0.25, 0.25-0.33, 0.33-0.4), gap entry vs a touch of the edge, break on
       day 1 / 2 / 3 after the inside day, direction WITH vs AGAINST the 50-day average's slope, day-1 close (did
       the break day close beyond the box or fall back inside it).
  Groups: single markets where it worked (XAUUSD USDJPY EURUSD XTIUSD), and the indices (US500 GERMANY40) apart.
"""
import os, sys, time, statistics as st, traceback
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import asiabo_offline as A

SINGLE = ("XAUUSD", "USDJPY", "EURUSD", "XTIUSD")
INDEX = ("US500", "GERMANY40")
INSIDE, WAIT, BUF, TDAY, TR, TRAIL, MAXD = 0.4, 3, 1.0, 10, 1.0, 3.0, 60
TYPES = ("BIG WIN", "SMALL WIN", "TIME WIN", "FAST WRONG", "SLOW WRONG", "NO TREND", "GAVE BACK")


def tstr(t):
    return ("%+.1f" % t) if t is not None else "  -"


def walk(dv, k, d, e, risk, a50, hi1, lo1):
    """one side; -> dict(R, why, days, r1 (R at close of day 1), r10 (R at close of day 10 or exit), mfe).
    hi1 / lo1 = the entry day's high / low AFTER the entry (from the M15 bars), never the part before it."""
    stop = e - d * risk
    moved = False
    best = e
    q = k
    r1 = r10 = None
    mfe = 0.0
    while True:
        o, h, l, c = dv.o[q], dv.hi[q], dv.lo[q], dv.cl[q]
        if q == k:
            h, l = hi1, lo1
        held = q - k + 1
        if q > k and ((d > 0 and o <= stop) or (d < 0 and o >= stop)):
            ex, why = o, ("trail" if moved else "price")
            break
        if (d > 0 and l <= stop) or (d < 0 and h >= stop):
            ex, why = stop, ("trail" if moved else "price")
            break
        best = max(best, h) if d > 0 else min(best, l)
        mfe = max(mfe, (best - e) * d / risk)
        rc = (c - e) * d / risk
        if held == 1:
            r1 = rc
        if held == TDAY:
            r10 = rc
            if rc < TR:
                ex, why = c, "time"
                break
        if held >= MAXD or q >= dv.send[k] or q >= dv.n - 1:
            ex, why = c, "max"
            break
        ns = best - d * TRAIL * a50
        if (d > 0 and ns > stop) or (d < 0 and ns < stop):
            stop, moved = ns, True
        q += 1
    R = (ex - e) * d / risk
    days = q - k + 1
    if r1 is None:
        r1 = R
    if r10 is None:
        r10 = R if days <= TDAY else r10
    return {"R": R, "why": why, "days": days, "r1": r1, "r10": r10 if r10 is not None else R, "mfe": mfe}


def kind(x):
    R, why, days = x["R"], x["why"], x["days"]
    if R >= 2.0:
        return "BIG WIN"
    if why == "time":
        return "TIME WIN" if R > 0 else "NO TREND"
    if why == "price":
        return "FAST WRONG" if days <= 3 else "SLOW WRONG"
    return "SMALL WIN" if R > 0 else "GAVE BACK"


def first_touch(m, k, H, Lo):
    """The entry on day k as it happens in time (M15 bars, M1 inside a bar that touches both sides).
    -> (d, entry, gap, entry M15 index) or None (no break, or both sides inside one M1 bar)."""
    i0, i1 = m.D[k][1], m.D[k][2]
    o = m.O[i0]
    if o > H:
        return (1, o, True, i0)
    if o < Lo:
        return (-1, o, True, i0)
    for i in range(i0, i1 + 1):
        up, dn = m.H[i] > H, m.L[i] < Lo
        if up and not dn:
            return (1, max(H, m.O[i]), False, i)
        if dn and not up:
            return (-1, min(Lo, m.O[i]), False, i)
        if up and dn:
            for (ts, bo, bh, bl, bc) in m.m1t(i):
                u2, d2 = bh > H, bl < Lo
                if u2 and not d2:
                    return (1, max(H, bo), False, i)
                if d2 and not u2:
                    return (-1, min(Lo, bo), False, i)
                if u2 and d2:
                    return None
            return None
    return None


def trades(m, dv, spec, mk):
    out = []
    busy = -1
    for j in range(60, dv.n - 2):
        if j <= busy or dv.seg[j] != dv.seg[j - 1]:
            continue
        if not (dv.hi[j] < dv.hi[j - 1] and dv.lo[j] > dv.lo[j - 1]):
            continue
        a20, a50 = dv.atr(j + 1, 20), dv.atr(j + 1, 50)
        if not a20 or not a50 or dv.hi[j] - dv.lo[j] >= INSIDE * a20:
            continue
        H, Lo = dv.hi[j], dv.lo[j]
        ent = None
        for k in range(j + 1, min(j + 1 + WAIT, dv.send[j] + 1)):
            if dv.hi[k] > H or dv.lo[k] < Lo or dv.o[k] > H or dv.o[k] < Lo:
                ft = first_touch(m, k, H, Lo)
                ent = (k,) + ft if ft else "amb"
                break
        if not ent or ent == "amb":
            continue
        k, d, e, gap, ie = ent
        i1 = m.D[k][2]
        hi1, lo1 = max(m.H[ie:i1 + 1]), min(m.L[ie:i1 + 1])
        risk = abs(e - ((Lo - BUF * a50) if d > 0 else (H + BUF * a50)))
        if risk <= 0:
            continue
        cost = A._cost_px(spec, e) / risk
        a = walk(dv, k, d, e, risk, a50, hi1, lo1)
        b = walk(dv, k, -d, e, risk, a50, hi1, lo1)
        for z in (a, b):
            z["R"] -= cost
            z["kind"] = kind(z)
        busy = max(k + a["days"] - 1, k + b["days"] - 1)
        s50 = dv.sma(j, 50)
        s50p = dv.sma(j - 10, 50)
        slope = None if (s50 is None or s50p is None) else (1 if s50 > s50p else -1)
        c1 = dv.cl[k]
        t = dv.key[k] * 86400.0
        tt = time.gmtime(t)
        out.append({"mk": mk, "t": a, "m": b, "clu": (mk, tt.tm_year, tt.tm_mon), "d": d,
                    "tight": (H - Lo) / a20, "gap": gap, "wait": k - j,
                    "trend": None if slope is None else ("WITH" if slope == d else "AGAINST"),
                    "close1": "beyond box" if ((c1 > H) if d > 0 else (c1 < Lo)) else "back inside"})
    return out


def cm(P, xs):
    return P.cmean(xs) if len(xs) > 1 else ((xs[0][0] if xs else 0.0), None, len(xs))


def report(p, P, tr, tag):
    p("")
    p("=" * 118)
    p("%s: %d trades" % (tag, len(tr)))
    p("=" * 118)
    if not tr:
        return
    a = cm(P, [(x["t"]["R"], x["clu"]) for x in tr])
    b = cm(P, [(x["m"]["R"], x["clu"]) for x in tr])
    ed = cm(P, [((x["t"]["R"] - x["m"]["R"]) / 2.0, x["clu"]) for x in tr])
    p("  trade %+.3f R/tr (t %s)   mirror %+.3f (t %s)   EDGE %+.3f (t %s)   total trade %+.1f R, mirror %+.1f R" % (
        a[0], tstr(a[1]), b[0], tstr(b[1]), ed[0], tstr(ed[1]), sum(x["t"]["R"] for x in tr), sum(x["m"]["R"] for x in tr)))
    p("")
    p("  A. WHERE THE MONEY ARRIVES (total R over all trades; costs sit in 'after day 10' / the exit part)")
    for side, nm in (("t", "trade "), ("m", "mirror")):
        d1 = sum(x[side]["r1"] for x in tr)
        d10 = sum(x[side]["r10"] - x[side]["r1"] for x in tr)
        rest = sum(x[side]["R"] - x[side]["r10"] for x in tr)
        p("     %s  break day %+7.1f R | days 2-10 %+7.1f R | after day 10 (and exit costs) %+7.1f R | total %+7.1f R" % (
            nm, d1, d10, rest, d1 + d10 + rest))
    p("")
    p("  B. OUTCOME TYPES              trade: n   avg R   sum R  share |  mirror: n   avg R   sum R")
    tot = sum(x["t"]["R"] for x in tr)
    for k in TYPES:
        xs = [x["t"]["R"] for x in tr if x["t"]["kind"] == k]
        ys = [x["m"]["R"] for x in tr if x["m"]["kind"] == k]
        p("     %-12s %20d  %+6.2f  %+6.1f  %4.0f%% | %10d  %+6.2f  %+6.1f" % (
            k, len(xs), st.mean(xs) if xs else 0, sum(xs), 100.0 * len(xs) / len(tr), len(ys), st.mean(ys) if ys else 0, sum(ys)))
    big = [x for x in tr if x["t"]["kind"] == "BIG WIN"]
    if big:
        p("     BIG WINS: median days held %d, median R %.1f, %d of %d closed day 1 beyond the box, avg day-1 R %+.2f" % (
            st.median(x["t"]["days"] for x in big), st.median(x["t"]["R"] for x in big),
            sum(1 for x in big if x["close1"] == "beyond box"), len(big), st.mean(x["t"]["r1"] for x in big)))
    p("")
    p("  C. BY ENTRY CONDITION (descriptive, NOT a filter)   n  win%  trade R/tr   EDGE (t)   big wins")
    conds = [("box < 0.25 ATR", lambda x: x["tight"] < 0.25), ("box 0.25-0.33", lambda x: 0.25 <= x["tight"] < 0.33),
             ("box 0.33-0.40", lambda x: x["tight"] >= 0.33), ("gap entry", lambda x: x["gap"]),
             ("touch entry", lambda x: not x["gap"]), ("break day 1", lambda x: x["wait"] == 1),
             ("break day 2", lambda x: x["wait"] == 2), ("break day 3", lambda x: x["wait"] == 3),
             ("WITH 50d slope", lambda x: x["trend"] == "WITH"), ("AGAINST 50d slope", lambda x: x["trend"] == "AGAINST"),
             ("day 1 closed beyond", lambda x: x["close1"] == "beyond box"),
             ("day 1 fell back in", lambda x: x["close1"] == "back inside")]
    for nm, f in conds:
        xs = [x for x in tr if f(x)]
        if not xs:
            p("     %-22s 0" % nm)
            continue
        r = cm(P, [(x["t"]["R"], x["clu"]) for x in xs])
        e = cm(P, [((x["t"]["R"] - x["m"]["R"]) / 2.0, x["clu"]) for x in xs])
        p("     %-22s %4d  %3.0f%%  %+.3f      %+.3f (%s)   %d" % (
            nm, len(xs), 100.0 * sum(1 for x in xs if x["t"]["R"] > 0) / len(xs), r[0], e[0], tstr(e[1]),
            sum(1 for x in xs if x["t"]["kind"] == "BIG WIN")))


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
    markets = tuple(mks.split(",")) if mks else SINGLE + INDEX
    rep = A.Report("trendwhy" if not one_db else "trendwhy_synth")
    p = rep.p
    p("THE TREND OPTION: how we won, how we lost, what we can't explain (trendwhy_spec.md). Training data, descriptive.")
    try:
        import asiabo_lab as L
        import asiabo_probe as P
        import asiabo_why as W
        W._install()
        if one_db:
            dbp = os.path.abspath(one_db)
            A.find_db = (lambda d=dbp: d)
            A.EXAM_UNLOCK = "--unlock" in argv
        specs = dict((x["name"], x) for x in A.COLLECT_SYMBOLS)
        alltr = {}
        for mk in markets:
            print("trendwhy: %s ..." % mk)
            m = L.PMarket(specs[mk])
            W._m1_cache(m)
            dv = P.Day(m, L)
            alltr[mk] = trades(m, dv, specs[mk], mk)
            if m.m1q:
                m.m1q[0].close()
            m._m1cache.clear()
            del m, dv
        report(p, P, sum((alltr.get(k, []) for k in SINGLE), []), "SINGLE MARKETS (gold, USDJPY, EURUSD, oil) POOLED")
        for mk in markets:
            if mk in SINGLE:
                report(p, P, alltr[mk], mk)
        if any(k in alltr for k in INDEX):
            report(p, P, sum((alltr.get(k, []) for k in INDEX), []), "INDICES (US500, GERMANY40), for comparison only")
    except Exception:
        p(traceback.format_exc())
    rep.save()


if __name__ == "__main__":
    main()
