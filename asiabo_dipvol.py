#!/usr/bin/env python3
"""
asiabo_dipvol.py  --  dip: skip when volatility is HIGH and RISING (Ezio + Claude common ground, 2026-10-13).
Spec + predictions: dipvol_spec.md (project). SHADOW ONLY: measures, decides nothing, changes no file but its report.

    python asiabo_dipvol.py                 EXPLORATION on the indices already spent for dip (see below)
    python asiabo_dipvol.py --db X --market USTECH100   one db only (cloud yardstick on fake worlds)

!! EXPLORATION, NOT CONFIRMATION. Every index here was already used for dip, and the rule's idea came partly from the
   US Tech 100 result. A real test of the rule needs fresh data (US 30, Japan 225, or the sealed 2022-23 years).

DATA (all read-only)
  US500 2016-19   exam_hold\\exam_us500.db (the spent exam)      US500 2020+    bars.db (sealed 2022-23 skipped)
  GERMANY40 2014+ bars.db (sealed 2022-23 skipped)               USTECH100 2016+ exam_hold\\ustech100.db (spent by dipdrift)

RULE  dip as it is (rsi2 long + dip3 long, 200-day filter, own exits, one position; = dipdrift variant A).
      At the signal day: ATR(w) = average daily true range of the last w completed days. HIGH = ATR(w) >= 1.3 x its own
      median over the previous 250 days. RISING = ATR(w) above its value 5 days earlier. Skip the trade if HIGH and RISING.
GAUGE ATR(10) is the PRIMARY gauge, chosen WITHOUT any profit figure: on 20 fake worlds with planted volatility episodes
      it read 'rising' correctly 64% of the time, caught 63% of rising days, flipping 5.4x a year (ATR5: 62% / 65% /
      13.1 flips; ATR20: 43% / 46%; ATR40: 13% / 17%). ATR 5 / 20 / 40 are reported alongside, never chosen after.
PREDICTIONS (Claude, before the run): skipped trades worse than kept ones pooled (it's partly the data the idea came
      from, so this is expected and proves little); total R about the same; max drawdown a little smaller.
"""
import os, sys, time, statistics as st, traceback
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import asiabo_offline as A

GAUGES = (5, 10, 20, 40)
PRIMARY = 10
HIGH, BACK, MEDWIN = 1.3, 5, 250


def atr_series(m, w):
    n = len(m.cl)
    tr = [None] * n
    for j in range(1, n):
        h, l, pc = m.hi[j], m.lo[j], m.cl[j - 1]
        tr[j] = max(h - l, abs(h - pc), abs(l - pc))
    out = [None] * n
    for j in range(w, n):
        win = tr[j - w + 1:j + 1]
        if None not in win:
            out[j] = sum(win) / w
    return out


def state(atr, j):
    if j < MEDWIN + BACK or atr[j] is None or atr[j - BACK] is None:
        return None
    hist = [a for a in atr[j - MEDWIN:j] if a is not None]
    if len(hist) < 120:
        return None
    return "hr" if (atr[j] >= HIGH * st.median(hist) and atr[j] > atr[j - BACK]) else "ok"


def run_market(L, DD, tag, w0=None, w1=None):
    spec = dict((x["name"], x) for x in A.COLLECT_SYMBOLS)[tag]
    m = L.PMarket(spec)
    tr = DD.dip_trades(L, m, "A")
    if w0:
        tr = [x for x in tr if A.epoch_of(w0) <= x["t_in"] < A.epoch_of(w1)]
    atr = dict((w, atr_series(m, w)) for w in GAUGES)
    for x in tr:
        x["st"] = dict((w, state(atr[w], x["j"])) for w in GAUGES)
        tt = time.gmtime(x["t_in"])
        x["clu"] = (tag, tt.tm_year, tt.tm_mon)
        x["mk"] = tag
    return tr


def maxdd(xs):
    cum = peak = dd = 0.0
    for x in sorted(xs, key=lambda x: x["t_out"]):
        cum += x["R"]
        peak = max(peak, cum)
        dd = max(dd, peak - cum)
    return dd


def report(p, P, trades, label):
    p("")
    p("-" * 112)
    p(label)
    p("-" * 112)
    p("%-8s %6s %6s | %-27s | %-27s | %-14s | %s" % ("gauge", "trades", "scored", "SKIPPED (high+rising)", "KEPT", "skip - kept",
                                                     "total R plain -> rule | max DD plain -> rule"))
    for w in GAUGES:
        xs = [x for x in trades if x["st"][w] is not None]
        sk = [x for x in xs if x["st"][w] == "hr"]
        kp = [x for x in xs if x["st"][w] == "ok"]
        if not xs:
            continue
        a = P.cmean([(x["R"], x["clu"]) for x in sk]) if sk else (None, None, 0)
        b = P.cmean([(x["R"], x["clu"]) for x in kp])
        dif = P.cdiff([(x["R"], x["clu"]) for x in sk], [(x["R"], x["clu"]) for x in kp]) if len(sk) > 1 else (None, None)
        p("ATR%-4d%s %6d %6d | n %4d  %+.3f R/tr (t %s) | n %4d  %+.3f R/tr (t %s) | %s (t %s) | %+7.1f -> %+7.1f | %5.1f -> %5.1f" % (
            w, "*" if w == PRIMARY else " ", len(trades), len(xs), len(sk), a[0] or 0, P.ft(a[1]).strip()[1:] if a[1] else "-",
            len(kp), b[0], P.ft(b[1]).strip()[1:] if b[1] else "-", P.f3(dif[0]), ("%+.1f" % dif[1]) if dif[1] else "-",
            sum(x["R"] for x in xs), sum(x["R"] for x in kp), maxdd(xs), maxdd(kp)))
    p("   (* = primary gauge, fixed before the run. 'scored' = trades with enough history to read the gauge.)")


def main():
    argv = sys.argv[1:]

    def opt(name):
        if name in argv:
            i = argv.index(name)
            v = argv[i + 1]
            del argv[i:i + 2]
            return v
        return None
    one_db, one_mk = opt("--db"), opt("--market")
    rep = A.Report("dipvol" if not one_db else "dipvol_synth")
    p = rep.p
    p("=" * 112)
    p("DIP: SKIP WHEN VOLATILITY IS HIGH AND RISING -- EXPLORATION on spent data (dipvol_spec.md). NOT a confirmation.")
    p("=" * 112)
    try:
        import asiabo_lab as L
        import asiabo_probe as P
        import asiabo_dipdrift as DD
        DD.register_spec()
        bars = A.find_db()
        hold = os.path.join(A.ROOT, "exam_hold")
        if one_db:
            runs = [(os.path.abspath(one_db), one_mk or "USTECH100", True, None, None)]
        else:
            runs = [(os.path.join(hold, "exam_us500.db"), "US500", False, "2016-01-01", "2020-01-01"),
                    (bars, "US500", False, "2020-01-01", "2100-01-01"),
                    (bars, "GERMANY40", False, None, None),
                    (os.path.join(hold, "ustech100.db"), "USTECH100", True, None, None)]
        allt = []
        for db, mk, unlock, w0, w1 in runs:
            if not db or not os.path.exists(db):
                p("(missing %s for %s: skipped)" % (db, mk))
                continue
            A.find_db = (lambda d=db: d)
            A.EXAM_UNLOCK = unlock
            print("dipvol: %s from %s ..." % (mk, os.path.basename(db)))
            tr = run_market(L, DD, mk, w0, w1)
            p("%s %s: %d dip trades%s" % (mk, os.path.basename(db), len(tr), (" (%s .. %s)" % (w0, w1)) if w0 else ""))
            allt += tr
        for mk in sorted(set(x["mk"] for x in allt)):
            report(p, P, [x for x in allt if x["mk"] == mk], "%s" % mk)
        report(p, P, allt, "ALL MARKETS POOLED")
    except Exception:
        p(traceback.format_exc())
    rep.save()


if __name__ == "__main__":
    main()
