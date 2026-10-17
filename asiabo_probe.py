"""
asiabo_probe.py  --  Phase 1 of next_plan.md: the PROBE STUDY (2026-10-11). Measures market behaviour; decides nothing.
Imports the lab and the why phase (their bars, lanes, costs, book walk); changes nothing in them.

    python asiabo_probe.py              everything: M1 M2 M4 M5 (daily bars, all 6 markets) + M3 M6 (lane trades)
    python asiabo_probe.py cheap        M1 M2 M4 M5 only (no lanes, a few minutes)
    python asiabo_probe.py all --db synth/<file>.db     the same on a cousin history (dayshuffle = the yardstick)

Markets: XAUUSD US500 EURUSD USDJPY XTIUSD GERMANY40 (Japan 225 and 2022-23 sealed, never read). Eras as the lab.
Every t is CLUSTERED by market x calendar month (overlapping windows / trades are not independent).

M1  TREND END. er40 spell = consecutive days with er40 (straightness of the last 40 daily closes, known at the day's
    start) >= 0.30 and the 40-day move the same way. When a spell ends, the next 5 / 10 / 20 days from that day's open,
    in the old trend's direction, in daily ATRs (N at the end day). CONTINUE = move >= +0.5 sqrt(h) N, REVERSE =
    <= -0.5 sqrt(h) N, CHOP = between (a pure random walk gives roughly 27 / 47 / 27 %). Compared with mid-spell days
    (age >= 10) and with every day in the 40-day move's direction. Split by how it ended: BLOW-OFF (last 5 closes moved
    >= 1.5 N with the trend), ROLLOVER (<= 0), FADE (between), and by spell length.
M2  HAZARD. Spells as survival data (a spell cut by a data break = censored). Hazard by age = ended at that age / still
    alive at that age. Memoryless = flat. The window itself bends the curve (a spell built by one big day leaves after
    ~40 days), so the curve is read AGAINST the dayshuffle cousin and the random-walk yardstick, not against flat.
    Test of "rises after ~20 days": hazard at age 21-40 / hazard at 6-20, with a bootstrap 90% band over spells.
M3  FAILED SHADOW. Book brk / fast trades stopped out (gross <= -0.95R). Reverse probe: enter the OTHER way at the next
    M15 bar's open, stop 1 risk unit (the original stop distance), target 1.5, out after 5 trading days. Gross R, no
    costs (a probe of direction). Control: 3 random days of the same market and era, the bar at the same local minute,
    the same stop in daily ATRs, the same direction as the reverse probe. Split by speed of failure and er40 regime.
M4  CORRECTION STATS. Every day: stretch z = (yesterday's close - 20-day average) / N. CRACK = yesterday closed below the
    prior 3-day low (mirror for z < 0). Next 1 / 3 / 5 days from today's open AGAINST the stretch, in N. Bins of |z| x
    crack, then |z| >= 2.5 and crack per market, also with a straight 20 days (er20 >= 0.30, same way) = #31's setup.
    This is NOT the #31 lane (no exits): that is Phase 3, judged fresh.
M5  SEEING SPEED. Hindsight truth per day: TREND = the 41 closes centred on the day have er >= 0.30 (signed); HIGH VOL =
    the 20 days' mean true range centred on the day >= 1.25 x the trailing 250-day mean. Detectors known at the day's
    start: price vs SMA / EMA L with the average sloping the same way over 5 days (L 5..200), erL >= 0.30 (L 10..60),
    ATR L / 250-day mean >= 1.25 (L 5..50). Precision, recall, median lag to a truth spell's start (spells >= 10 days),
    share of spells caught, caught in the first half, life left at detection, false switch-ons per market-year.
    The known-truth synth version waits for the Phase 2 generator.
M6  SERIAL DEPENDENCE. Book fast / dip / brk, per market in entry order, NON-OVERLAPPING trades only. P(loss | previous
    loss) vs P(loss), E[net | previous loss]; 500 order shuffles and 500 month-block shuffles -> percentile. The skip line
    (skipping after a loss helps if E[net | prev loss] < 0) and the mirror line (trading the mirror after a loss helps if
    E[mirror | prev loss] > E[net | prev loss]; mirror net = 2 x coin-flip net - net, costs included).

PREDICTIONS (written 2026-10-11 BEFORE this file ever ran on any data)
  Ezio:
    M1  after a trend ends: CHOP most often, then REVERSE, then CONTINUE.
    M2  the hazard RISES after ~20 days.
    M3  no prediction.
    M4  stretched + cracked markets fall more than random, most clearly over 3 days, on the markets where the mirror dip
        does better (dip's weaker markets: EURUSD, XAUUSD, XTIUSD, USDJPY).
    #31 (for Phase 3) a SMALL win rate: chop is the most likely outcome and hits most stops. Best on dip's weakest markets.
  Claude:
    M1  chop most (~45-50%), continue and reverse about equal; spell-end outcomes inside the dayshuffle / random-walk range
        (the end of an er40 spell carries little information). Blow-offs reverse more than fades.
    M2  no rise beyond the cousin's curve (ladder evidence: no gradient by trend age); ratio 21-40 / 6-20 inside the band.
    M3  quick failures: the reverse probe about equal to its random control overall; the fastest (<= 1h) a little better.
    M4  a small correction after stretch + crack in XAUUSD / XTIUSD / EURUSD (t ~2), none in the indices (drift wins).
    M5  er20 fastest with tolerable false alarms; SMA/EMA lag about L/2; ATR5-10 catches high vol within days.
    M6  P(loss | loss) inside the shuffle band for every part; neither line crossed.
"""
import os, sys, math, time, random, bisect, shutil, traceback
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import asiabo_offline as A

MARKETS = ["XAUUSD", "US500", "EURUSD", "USDJPY", "XTIUSD", "GERMANY40"]
MIRROR_MK = ("EURUSD", "XAUUSD", "XTIUSD", "USDJPY")
ER_TH = 0.30
MIN_SPELL = 10
HOLD = 5
HZ = (5, 10, 20)
AGE_BINS = [(1, 5), (6, 10), (11, 20), (21, 30), (31, 40), (41, 60), (61, 9999)]
Z_BINS = [(0.0, 1.5), (1.5, 2.5), (2.5, 3.5), (3.5, 99.0)]
SPEEDS = [("<=1h", 0, 1), ("1-4h", 1, 4), ("4-24h", 4, 24), (">1d", 24, 1e9)]
CTRL_DRAWS = 3
PERMS = 500
SEED = 20261011

YARD = {
    "M1": "\n".join([
        "YARDSTICK (this file on 3 fake random-walk histories, 6 markets, 2026-10-11): every t in this section stayed",
        "    within -1.9 .. +2.4 (2 of 79 beyond 2, both on SHORT-spell lines). REAL spell END, h 10: continue 16-25%,",
        "    chop 51-62%, reverse 19-25%; END minus MID |t| <= 1.0. So a share or a t means something only well outside",
        "    these AND outside the dayshuffle cousin (probe_synth_dayshuffle_s1.txt)."]),
    "M2": "\n".join([
        "YARDSTICK (3 fake random walks): on pure noise the hazard FALLS with age, then bumps up at 41-60 days (the window):",
        "    1-5 d 0.24-0.26 | 6-10 0.10-0.12 | 11-20 0.07-0.11 | 21-30 0.06-0.08 | 31-40 0.06-0.08 | 41-60 0.14-0.18.",
        "    Ratio (21-40) / (6-20) = 0.65 .. 0.82, bootstrap bands within 0.44 .. 1.08; per market 0.11 .. 1.98 (thin).",
        "    So 'rises after ~20 days' counts only if the real ratio is above ~1.1 AND above the dayshuffle cousin's."]),
    "M3": "\n".join([
        "YARDSTICK (3 fake random walks): every t in this section within -2.6 .. +2.4 (9 of 198 beyond 2). Overall rows",
        "    (probe - ctrl, ALL) t -0.6 .. +1.0. A row stands out only with |t| >= ~3, or a speed pattern that also shows",
        "    in fast AND brk and not in the cousin."]),
    "M4": "\n".join([
        "YARDSTICK (3 fake random walks): every t in this section within -2.1 .. +2.1 (4 of 243 beyond 2); cracked rows",
        "    -2.1 .. +2.1. Count a correction only at |t| >= ~2.5, the same sign over 1 / 3 / 5 days, above the 'no crack'",
        "    row of the same market and above the dayshuffle cousin."]),
    "M5": "\n".join([
        "YARDSTICK (3 fake random walks) = what the hindsight truth gives for FREE: the truth's centred window shares 20",
        "    days with each detector's window, so even noise scores. Noise: truth on 14-15% of days; precision sma/ema",
        "    10-17%, er10 18%, er20 28-29%, er40 25-28%, er60 21-25%; caught sma20/ema20 94-99%; lag er20 3-4 d,",
        "    er40 8-21 d, er60 14-24 d; false/yr sma5 38, er20 12, er40 4.5. High-vol truth only 1-3% of noise days",
        "    (constant volatility), so the ATR rows are read against the dayshuffle cousin. A detector carries real",
        "    information only where its precision / caught beats these noise numbers."]),
    "M6": "\n".join([
        "YARDSTICK (3 fake random walks, 18 percentiles): P(L|L) shuffle% 0.2 .. 87.0 and block% 15 .. 99.0, so a single",
        "    extreme is chance. 1 of 18 lines crossed (95.4%). Count a part as dependent only if shuffle% AND block% are",
        "    both beyond 2.5 / 97.5 with the same sign, and the cousin does not show it."]),
}


# ================================================================ statistics
def cmean(pairs):
    """pairs = [(value, cluster)] -> (mean, clustered t, n)."""
    n = len(pairs)
    if n < 2:
        return (pairs[0][0] if pairs else None), None, n
    mu = sum(v for v, c in pairs) / n
    g = defaultdict(float)
    for v, c in pairs:
        g[c] += v - mu
    k = len(g)
    if k < 2:
        return mu, None, n
    var = sum(e * e for e in g.values()) * k / (k - 1.0) / (n * n)
    return mu, (mu / math.sqrt(var) if var > 0 else None), n


def cdiff(a, b):
    """difference of two clustered means; t from the two clustered standard errors (approximate)."""
    ma, ta, na = cmean(a)
    mb, tb, nb = cmean(b)
    if ma is None or mb is None or not ta or not tb:
        return (None if ma is None or mb is None else ma - mb), None
    se = math.sqrt((ma / ta) ** 2 + (mb / tb) ** 2)
    return ma - mb, ((ma - mb) / se if se > 0 else None)


def f3(v, w=6):
    return ("%+*.3f" % (w, v)) if v is not None else "%*s" % (w, "-")


def ft(v):
    return ("t%+5.1f" % v) if v is not None else "t   - "


def pct(a, b):
    return (100.0 * a / b) if b else None


def fp(v):
    return ("%5.1f%%" % v) if v is not None else "    - "


def med(v):
    if not v:
        return None
    s = sorted(v)
    n = len(s)
    return s[n // 2] if n % 2 else 0.5 * (s[n // 2 - 1] + s[n // 2])


def qtl(v, q):
    s = sorted(v)
    return s[min(len(s) - 1, max(0, int(q * (len(s) - 1) + 0.5)))] if s else None


# ================================================================ daily view of one market
class Day(object):
    """The daily bars of one PMarket, plus the era and cluster of each day; nothing else kept (memory)."""

    def __init__(self, m, L):
        self.s = m.s
        D = m.D
        self.n = len(D)
        self.key = [d[0] for d in D]
        self.o = [d[3] for d in D]
        self.hi, self.lo, self.cl = list(m.hi), list(m.lo), list(m.cl)
        self.N, self.seg = list(m.N), list(m.seg)
        self.era, self.clu = [], []
        for k in self.key:
            t = k * 86400.0
            self.era.append(L._p_era(t))
            tt = time.gmtime(t)
            self.clu.append((self.s, tt.tm_year, tt.tm_mon))
        # segment end (last index of the segment each day is in)
        self.send = [0] * self.n
        e = self.n - 1
        for j in range(self.n - 1, -1, -1):
            self.send[j] = e
            if self.seg[j] == j:
                e = j - 1
        cs = [0.0]
        for c in self.cl:
            cs.append(cs[-1] + c)
        self._cs = cs
        ad = [0.0]
        for j in range(1, self.n):
            ad.append(abs(self.cl[j] - self.cl[j - 1]))
        self.ad = ad
        ads = [0.0]
        for v in ad:
            ads.append(ads[-1] + v)
        self._ads = ads
        tr = [self.hi[0] - self.lo[0]] + [max(self.hi[j] - self.lo[j], abs(self.hi[j] - self.cl[j - 1]),
                                              abs(self.lo[j] - self.cl[j - 1])) for j in range(1, self.n)]
        self.tr = tr
        ts = [0.0]
        for v in tr:
            ts.append(ts[-1] + v)
        self._ts = ts

    def sma(self, j, w):                # mean of closes j-w+1 .. j
        if j - w + 1 < self.seg[j] or j < 0:
            return None
        return (self._cs[j + 1] - self._cs[j + 1 - w]) / w

    def er(self, j, w):
        """straightness of the w moves ending at close j-1 (known at the START of day j): (eff, sign) or None."""
        a = j - 1 - w
        if a < self.seg[j] or j - 1 < 0:
            return None
        path = self._ads[j] - self._ads[a + 1]
        mv = self.cl[j - 1] - self.cl[a]
        return ((abs(mv) / path) if path else 0.0, 1 if mv > 0 else -1)

    def er_centred(self, j, h):
        a, b = j - h, j + h
        if a < self.seg[j] or b > self.send[j]:
            return None
        path = self._ads[b + 1] - self._ads[a + 1]
        mv = self.cl[b] - self.cl[a]
        return ((abs(mv) / path) if path else 0.0, 1 if mv > 0 else -1)

    def atr(self, j, w):                # mean TR of the w days before day j
        if j - w < self.seg[j]:
            return None
        return (self._ts[j] - self._ts[j - w]) / w

    def ok(self, j):
        return self.N[j] is not None and self.era[j] is not None


# ================================================================ M1 / M2: spells
def spells(dv):
    """-> [(start, end_or_None, dir, censored)] ; end = first day the state is off (known at its start)."""
    out = []
    j = 1
    n = dv.n
    cur = None
    for j in range(1, n):
        e = dv.er(j, 40)
        st = (e[1] if e and e[0] >= ER_TH else 0) if e else None
        if cur is not None and (dv.seg[j] == j):              # a data break cuts the spell: censored
            out.append((cur[0], j - 1, cur[1], True))
            cur = None
        if st:
            if cur is None:
                cur = (j, st)
            elif st != cur[1]:
                out.append((cur[0], j, cur[1], False))
                cur = (j, st)
        else:
            if cur is not None:
                out.append((cur[0], j, cur[1], False))
                cur = None
    if cur is not None:
        out.append((cur[0], n - 1, cur[1], True))
    return out


def fwd(dv, j, d, h):
    """from the open of day j to the close of day j+h-1, signed d, in N[j]; plus MFE / MAE over those days."""
    b = j + h - 1
    if b > dv.send[j] or not dv.N[j]:
        return None
    N, o = dv.N[j], dv.o[j]
    mv = d * (dv.cl[b] - o) / N
    if d > 0:
        mfe, mae = (max(dv.hi[j:b + 1]) - o) / N, (o - min(dv.lo[j:b + 1])) / N
    else:
        mfe, mae = (o - min(dv.lo[j:b + 1])) / N, (max(dv.hi[j:b + 1]) - o) / N
    return mv, mfe, mae


def classify(mv, h):
    th = 0.5 * math.sqrt(h)
    return "cont" if mv >= th else ("rev" if mv <= -th else "chop")


def run_m1(rep, DV):
    p = rep.p
    p("")
    p("=" * 110)
    p("M1. TREND END: what follows the end of an er40 spell (er40 >= %.2f, same direction)" % ER_TH)
    p("=" * 110)
    p("PREDICTIONS  Ezio: chop > reverse > continue.  Claude: chop ~45-50%%, continue ~ reverse, inside the yardstick;")
    p("             blow-offs reverse more than fades.")
    groups = defaultdict(list)          # (kind, h) -> [(mv, mfe, mae, cluster, market, endtype, length)]
    nsp = 0
    for s, dv in DV.items():
        for a, e, d, cen in spells(dv):
            if cen or not dv.ok(e):
                continue
            ln = e - a
            if ln < MIN_SPELL:
                for h in HZ:
                    r = fwd(dv, e, d, h)
                    if r:
                        groups[("short", h)].append(r + (dv.clu[e], s, None, ln))
                continue
            nsp += 1
            l5 = dv.cl[e - 1] - dv.cl[e - 6] if e - 6 >= dv.seg[e] else None
            l5 = d * l5 / dv.N[e] if l5 is not None else None
            et = None if l5 is None else ("blow-off" if l5 >= 1.5 else ("rollover" if l5 <= 0 else "fade"))
            for h in HZ:
                r = fwd(dv, e, d, h)
                if r:
                    groups[("end", h)].append(r + (dv.clu[e], s, et, ln))
            for j in range(a + 9, e):                       # mid-spell days, age >= 10
                if dv.ok(j):
                    for h in HZ:
                        r = fwd(dv, j, d, h)
                        if r:
                            groups[("mid", h)].append(r + (dv.clu[j], s, None, None))
        for j in range(42, dv.n):
            if not dv.ok(j):
                continue
            e = dv.er(j, 40)
            if not e:
                continue
            for h in HZ:
                r = fwd(dv, j, e[1], h)
                if r:
                    groups[("any", h)].append(r + (dv.clu[j], s, None, None))
    p("ended REAL spells (lasted %d+ days, not cut by a data break): %d. Most er40 spells are 1-2 day flickers around"
      " the threshold;" % (MIN_SPELL, nsp))
    p("those are shown on their own line ('short spell END').")
    p("")
    p("a. Outcome shares and the mean move in the OLD trend's direction (N = daily ATR at the end day)")
    p("   %-26s %4s %6s %8s %8s %8s  %-16s %7s %7s" % ("", "h", "n", "CONT", "CHOP", "REV", "mean move", "MFE med", "MAE med"))
    for kind, lab in (("end", "REAL spell END day"), ("short", "short spell END (<%d d)" % MIN_SPELL),
                      ("mid", "mid-spell (age>=10)"), ("any", "any day, 40d direction")):
        for h in HZ:
            xs = groups[(kind, h)]
            if not xs:
                continue
            c = defaultdict(int)
            for x in xs:
                c[classify(x[0], h)] += 1
            mu, t, n = cmean([(x[0], x[3]) for x in xs])
            p("   %-26s %4d %6d %7s %7s %7s  %s %s %7.2f %7.2f" % (
                lab if h == HZ[0] else "", h, n, fp(pct(c["cont"], n)), fp(pct(c["chop"], n)), fp(pct(c["rev"], n)),
                f3(mu), ft(t), med([x[1] for x in xs]), med([x[2] for x in xs])))
    p("")
    p("b. END minus MID-SPELL mean move (does the end of a spell change what comes next?)")
    for h in HZ:
        dlt, t = cdiff([(x[0], x[3]) for x in groups[("end", h)]], [(x[0], x[3]) for x in groups[("mid", h)]])
        p("   h %2d: %s %s" % (h, f3(dlt), ft(t)))
    p("")
    p("c. By how the spell ended (h = 10)                         and by spell length (h = 10)")
    xs = groups[("end", 10)]
    rows_a = []
    for et in ("blow-off", "fade", "rollover"):
        ys = [x for x in xs if x[5] == et]
        c = defaultdict(int)
        for x in ys:
            c[classify(x[0], 10)] += 1
        mu, t, n = cmean([(x[0], x[3]) for x in ys])
        rows_a.append("   %-9s n %4d cont %s chop %s rev %s move %s %s" % (
            et, n, fp(pct(c["cont"], n)), fp(pct(c["chop"], n)), fp(pct(c["rev"], n)), f3(mu), ft(t)))
    rows_b = []
    for lab, lo_, hi_ in (("10-19 d", 10, 19), ("20-39 d", 20, 39), ("40+ d", 40, 99999)):
        ys = [x for x in xs if lo_ <= x[6] <= hi_]
        mu, t, n = cmean([(x[0], x[3]) for x in ys])
        c = defaultdict(int)
        for x in ys:
            c[classify(x[0], 10)] += 1
        rows_b.append("%-8s n %4d rev %s move %s %s" % (lab, n, fp(pct(c["rev"], n)), f3(mu), ft(t)))
    for i in range(max(len(rows_a), len(rows_b))):
        p("%-74s %s" % (rows_a[i] if i < len(rows_a) else "", rows_b[i] if i < len(rows_b) else ""))
    p("")
    p("d. Per market (end day, h = 10)")
    for s in DV:
        ys = [x for x in xs if x[4] == s]
        c = defaultdict(int)
        for x in ys:
            c[classify(x[0], 10)] += 1
        mu, t, n = cmean([(x[0], x[3]) for x in ys])
        p("   %-10s n %4d cont %s chop %s rev %s move %s %s" % (
            s, n, fp(pct(c["cont"], n)), fp(pct(c["chop"], n)), fp(pct(c["rev"], n)), f3(mu), ft(t)))
    p(YARD["M1"])


def run_m2(rep, DV):
    p = rep.p
    p("")
    p("=" * 110)
    p("M2. HAZARD: the chance an er40 spell ends at each age (memoryless = flat; read against the yardstick)")
    p("=" * 110)
    p("PREDICTIONS  Ezio: rises after ~20 days.  Claude: no rise beyond the cousin's curve.")
    allsp = []
    for s, dv in DV.items():
        for a, e, d, cen in spells(dv):
            allsp.append((e - a + (1 if cen else 0), cen, s))

    def hazard(sp):
        end = defaultdict(int)
        risk = defaultdict(int)
        for ln, cen, s in sp:
            for lo_, hi_ in AGE_BINS:
                if ln >= lo_:
                    risk[(lo_, hi_)] += min(ln, hi_) - lo_ + 1
                if not cen and lo_ <= ln <= hi_:
                    end[(lo_, hi_)] += 1
        return dict((b, (end[b] / float(risk[b])) if risk[b] else None) for b in AGE_BINS), end, risk

    def ratio(sp):
        h, _, _ = hazard(sp)
        a = h[(21, 30)], h[(31, 40)]
        # pooled 21-40 vs 6-20 (exposure-weighted)
        _, e, r = hazard(sp)
        num = (e[(21, 30)] + e[(31, 40)]) / float(max(1, r[(21, 30)] + r[(31, 40)]))
        den = (e[(6, 10)] + e[(11, 20)]) / float(max(1, r[(6, 10)] + r[(11, 20)]))
        return num / den if den else None
    h, e, r = hazard(allsp)
    p("spells: %d (censored %d)" % (len(allsp), sum(1 for x in allsp if x[1])))
    p("   age (days)   ended  spell-days at risk   hazard/day")
    for b in AGE_BINS:
        p("   %-10s %7d %12d %14s" % ("%d-%s" % (b[0], b[1] if b[1] < 9999 else "+"), e[b], r[b],
                                     ("%.4f" % h[b]) if h[b] is not None else "-"))
    rnd = random.Random(SEED)
    bs = []
    for _ in range(PERMS):
        smp = [allsp[rnd.randrange(len(allsp))] for _ in allsp]
        v = ratio(smp)
        if v is not None:
            bs.append(v)
    rv = ratio(allsp)
    p("   hazard ratio (age 21-40) / (age 6-20): %s   bootstrap 90%% band %s .. %s   (1 = no ageing)" % (
        ("%.2f" % rv) if rv else "-", ("%.2f" % qtl(bs, 0.05)) if bs else "-", ("%.2f" % qtl(bs, 0.95)) if bs else "-"))
    p("   per market:  " + "  ".join("%s %s" % (s, ("%.2f" % ratio([x for x in allsp if x[2] == s]))
                                                 if ratio([x for x in allsp if x[2] == s]) else "-") for s in DV))
    p("   median spell length %s days; share of spells lasting 20+ days %s" % (
        med([x[0] for x in allsp]), fp(pct(sum(1 for x in allsp if x[0] >= 20), len(allsp)))))
    p(YARD["M2"])


# ================================================================ M4: correction stats
def run_m4(rep, DV):
    p = rep.p
    p("")
    p("=" * 110)
    p("M4. CORRECTION STATS: stretch from the 20-day average x a structure crack -> the next 1 / 3 / 5 days AGAINST the stretch")
    p("=" * 110)
    p("PREDICTIONS  Ezio: stretched + cracked falls more than random, clearest over 3 days, on %s." % "/".join(MIRROR_MK))
    p("             Claude: a small correction in XAUUSD / XTIUSD / EURUSD (t ~2), none in the indices.")
    p("|z| = the PEAK stretch of the last 5 closes from their 20-day average, in N. CRACK = yesterday was the FIRST close")
    p("below the low of the 3 days before it (above the high, for a stretch down). Moves from today's open, against the")
    p("stretch, in N. 'no crack' rows = the same stretch without the trigger (what the crack adds).")
    rows = []          # (s, |z|, crack, straight, f1, f3, f5, cluster)
    for s, dv in DV.items():
        for j in range(25, dv.n):
            if not dv.ok(j):
                continue
            if j - 26 < dv.seg[j]:
                continue
            N = dv.N[j]
            zs = []
            for k in range(j - 5, j):                       # stretch at the closes of the last 5 days
                a_ = dv.sma(k, 20)
                zs.append((dv.cl[k] - a_) / N)
            zp = max(zs, key=abs)                           # the peak stretch and its side
            u = 1 if zp > 0 else -1
            z = zp

            def cracked(k):                                 # close k beyond the low (high) of the 3 days before it
                return (dv.cl[k] < min(dv.lo[k - 3:k])) if u > 0 else (dv.cl[k] > max(dv.hi[k - 3:k]))
            crack = cracked(j - 1) and not cracked(j - 2)   # the FIRST crack
            e20 = dv.er(j, 20)
            straight = bool(e20 and e20[0] >= ER_TH and e20[1] == u)
            fs = []
            for h in (1, 3, 5):
                r = fwd(dv, j, -u, h)
                fs.append(r[0] if r else None)
            rows.append((s, abs(z), crack, straight, fs[0], fs[1], fs[2], dv.clu[j]))

    def line(lab, xs):
        out = "   %-34s" % lab
        for k in (4, 5, 6):
            v = [(x[k], x[7]) for x in xs if x[k] is not None]
            mu, t, n = cmean(v)
            out += " %s %s" % (f3(mu), ft(t))
        n3 = [x[5] for x in xs if x[5] is not None]
        return out + "  n %5d  P(3d>0) %s" % (len(n3), fp(pct(sum(1 for v in n3 if v > 0), len(n3))))
    p("   (move against the stretch in N; + = the correction happened)     1 day           3 days          5 days")
    p(line("ALL days", rows))
    for lo_, hi_ in Z_BINS:
        for cr in (False, True):
            p(line("|z| %.1f-%s %s" % (lo_, ("%.1f" % hi_) if hi_ < 50 else "+", "CRACK" if cr else "no crack"),
                   [x for x in rows if lo_ <= x[1] < hi_ and x[2] == cr]))
    p("")
    p("   |z| >= 2.5 and CRACK, per market (+ #31's straight-20-days condition)")
    for s in DV:
        xs = [x for x in rows if x[0] == s and x[1] >= 2.5 and x[2]]
        p(line("%-10s%s" % (s, " *" if s in MIRROR_MK else ""), xs))
        p(line("   ... and er20 >= 0.30 same way", [x for x in xs if x[3]]))
        p(line("   ... no crack (same stretch)", [x for x in rows if x[0] == s and x[1] >= 2.5 and not x[2]]))
    p("   * = Ezio's mirror-dip markets")
    p(YARD["M4"])


# ================================================================ M5: seeing speed
def _ema(dv, L):
    out = [None] * dv.n
    k = 2.0 / (L + 1.0)
    v, cnt = None, 0
    for j in range(dv.n):
        if dv.seg[j] == j:
            v, cnt = None, 0
        c = dv.cl[j]
        v = c if v is None else v + k * (c - v)
        cnt += 1
        out[j] = v if cnt >= L else None
    return out


def run_m5(rep, DV):
    p = rep.p
    p("")
    p("=" * 110)
    p("M5. SEEING SPEED: how fast each indicator sees a state that is true in hindsight")
    p("=" * 110)
    p("PREDICTIONS  Claude: er20 fastest with tolerable false alarms; SMA/EMA lag about L/2; ATR5-10 sees high vol in days.")
    dets_tr = [("sma%d" % L, "sma", L) for L in (5, 10, 20, 50, 100, 200)] + \
              [("ema%d" % L, "ema", L) for L in (5, 10, 20, 50, 100, 200)] + \
              [("er%d" % L, "er", L) for L in (10, 20, 40, 60)]
    dets_v = [("atr%d" % L, L) for L in (5, 10, 20, 50)]
    acc = defaultdict(lambda: defaultdict(list))
    years = 0.0
    for s, dv in DV.items():
        truth = [None] * dv.n
        vtruth = [None] * dv.n
        base = [None] * dv.n
        for j in range(dv.n):
            e = dv.er_centred(j, 20)
            if e is not None:
                truth[j] = e[1] if e[0] >= ER_TH else 0
            if j - 250 >= dv.seg[j]:
                base[j] = (dv._ts[j] - dv._ts[j - 250]) / 250.0
            if base[j] and j - 9 >= dv.seg[j] and j + 10 <= dv.send[j]:
                c20 = (dv._ts[j + 11] - dv._ts[j - 9]) / 20.0
                vtruth[j] = 1 if c20 >= 1.25 * base[j] else 0
        valid = [j for j in range(dv.n) if truth[j] is not None and dv.era[j] is not None]
        years += len(valid) / 260.0
        emas = dict((L, _ema(dv, L)) for L in (5, 10, 20, 50, 100, 200))

        def det(kind, L, j):
            if kind == "er":
                e = dv.er(j, L)
                return None if e is None else (e[1] if e[0] >= ER_TH else 0)
            if j - 6 < dv.seg[j]:
                return None
            if kind == "sma":
                a, b = dv.sma(j - 1, L), dv.sma(j - 6, L)
            else:
                a, b = emas[L][j - 1] if j >= 1 else None, emas[L][j - 6] if j >= 6 and dv.seg[j - 6] == dv.seg[j] else None
            if a is None or b is None:
                return None
            c = dv.cl[j - 1]
            if c > a and a > b:
                return 1
            if c < a and a < b:
                return -1
            return 0

        def score(name, sig, tru):
            on = [j for j in valid if sig[j] is not None and tru[j] is not None]
            a = acc[name]
            a["base_n"].append(len(on))
            a["base_k"].append(sum(1 for j in on if tru[j]))
            a["prec_n"].append(sum(1 for j in on if sig[j] != 0))
            a["prec_k"].append(sum(1 for j in on if sig[j] != 0 and tru[j] == sig[j]))
            a["rec_n"].append(sum(1 for j in on if tru[j]))
            a["rec_k"].append(sum(1 for j in on if tru[j] and sig[j] == tru[j]))
            # truth spells >= 10 days
            j = 0
            vs = set(valid)
            while j < dv.n:
                if j in vs and tru[j]:
                    k = j
                    while k + 1 < dv.n and (k + 1) in vs and tru[k + 1] == tru[j]:
                        k += 1
                    ln = k - j + 1
                    if ln >= 10:
                        hit = None
                        for q in range(j, k + 1):
                            if all(sig[r] == tru[j] for r in range(q, min(q + HOLD, k + 1))) and \
                                    (q + HOLD - 1 <= k or q == j):
                                hit = q
                                break
                        a["spells"].append(1)
                        if hit is not None:
                            a["lag"].append(hit - j)
                            a["half"].append(1 if hit - j < ln / 2.0 else 0)
                            a["left"].append((k - hit + 1) / float(ln))
                    j = k + 1
                else:
                    j += 1
            # false switch-ons: a run of sig != 0 that never meets truth with the same sign
            j = 0
            while j < dv.n:
                if j in vs and sig[j]:
                    k = j
                    while k + 1 < dv.n and (k + 1) in vs and sig[k + 1] == sig[j]:
                        k += 1
                    if not any(tru[q] == sig[j] for q in range(j, k + 1)):
                        a["false"].append(1)
                    a["runs"].append(1)
                    j = k + 1
                else:
                    j += 1
        for name, kind, L in dets_tr:
            sig = [None] * dv.n
            for j in valid:
                sig[j] = det(kind, L, j)
            score(name, sig, truth)
        for name, L in dets_v:
            sig = [None] * dv.n
            for j in valid:
                a_ = dv.atr(j, L)
                sig[j] = None if (a_ is None or not base[j]) else (1 if a_ >= 1.25 * base[j] else 0)
            score(name, sig, vtruth)
    p("days where the truth is known: %.0f market-years" % years)
    p("   %-8s %7s %7s %7s %8s %8s %8s %8s %10s" % ("", "truth", "precis.", "recall", "lag med", "caught", "1st half",
                                                     "life left", "false/yr"))
    for name in [x[0] for x in dets_tr] + ["--"] + [x[0] for x in dets_v]:
        if name == "--":
            p("   (volatility detectors vs the high-vol truth)")
            continue
        a = acc[name]
        p("   %-8s %7s %7s %7s %8s %8s %8s %8s %10.1f" % (
            name, fp(pct(sum(a["base_k"]), sum(a["base_n"]))), fp(pct(sum(a["prec_k"]), sum(a["prec_n"]))), fp(pct(sum(a["rec_k"]), sum(a["rec_n"]))),
            ("%.0f d" % med(a["lag"])) if a["lag"] else "-", fp(pct(len(a["lag"]), len(a["spells"]))),
            fp(pct(sum(a["half"]), len(a["spells"]))), fp(100 * med(a["left"]) if a["left"] else None),
            len(a["false"]) / max(years, 1e-9)))
    p("   truth = share of days the hindsight state is on (any sign). Read every column against the yardstick below.")
    p("   lag 0 d = the detector was already on when the truth spell began (its centred window includes 20 earlier days).")
    p("   precision = share of detector-on days the truth agrees with; recall = share of truth days the detector agrees.")
    p("   lag / caught / 1st half / life left: per truth spell (>= 10 days), the first day the detector agrees AND keeps")
    p("   agreeing for %d days; caught = share of spells where that happens, life left = median share of the spell ahead." % HOLD)
    p("   false/yr = detector runs per market-year that never meet the truth with the same sign.")
    p(YARD["M5"])


# ================================================================ lane trades (M3, M6)
def walk(m, i0, entry, d, sd, tp=1.5, bars=480):
    """gross R of a probe from bar i0 (entry at its open): stop 1 sd, target tp sd, out at the close of bar i0+bars.
    Both levels in one bar = the stop (conservative). Stops at a data break (> 10 days)."""
    stop, tgt = entry - d * sd, entry + d * tp * sd
    mfe = 0.0
    last = i0
    for i in range(i0, min(m.n, i0 + bars)):
        if i > i0 and m.T[i] - m.T[i - 1] > 10 * 86400:
            break
        last = i
        hs = (m.L[i] <= stop) if d > 0 else (m.H[i] >= stop)
        ht = (m.H[i] >= tgt) if d > 0 else (m.L[i] <= tgt)
        if hs:
            return -1.0, mfe, "stop"
        fav = ((m.H[i] - entry) if d > 0 else (entry - m.L[i])) / sd
        mfe = max(mfe, fav)
        if ht:
            return tp, mfe, "target"
    return d * (m.C[last] - entry) / sd, mfe, "time"


def m3_market(m, book, er40, rnd, out):
    """book = [(row, part)] of this market. Appends (part, speed, regime, R, ctrlR, mfe, cluster, outcome)."""
    import asiabo_lab as L
    days_by_era = defaultdict(list)
    for j in range(len(m.D)):
        if m.N[j]:
            e = L._p_era(m.D[j][0] * 86400.0)
            if e:
                days_by_era[e].append(j)
    for x, part in book:
        if part not in ("brk", "fast") or x[7] is None or x[7] > -0.95:
            continue
        tg = x[8]
        t_in, t_out, d, sd = tg["_t_in"], tg["_t_out"], tg["_d"], tg.get("_sd")
        if not sd:
            continue
        ja = bisect.bisect_left(m.T, t_out - 900)
        i0 = ja + 1
        if i0 >= m.n or m.T[i0] - m.T[ja] > 4 * 86400:
            continue
        jd = m.di[i0]
        Nn = m.N[jd]
        if not Nn:
            continue
        rd = -d
        R, mfe, oc = walk(m, i0, m.O[i0], rd, sd)
        hrs = (t_out - t_in) / 3600.0
        sp = [lab for lab, a, b in SPEEDS if a < hrs <= b or (a == 0 and hrs <= b)][0]
        ev = er40.get(m.D[jd][0])
        reg = "er40 on" if (ev is not None and ev >= ER_TH) else "er40 off"
        loc = m.loc[i0]
        risk_n = sd / Nn
        cands = days_by_era.get(x[4], [])
        ctrl = []
        tries = 0
        while len(ctrl) < CTRL_DRAWS and cands and tries < 30:
            tries += 1
            j = cands[rnd.randrange(len(cands))]
            ii = None
            for i in range(m.D[j][1], m.D[j][2] + 1):
                if m.loc[i] == loc:
                    ii = i
                    break
            if ii is None:
                continue
            r2, _, _ = walk(m, ii, m.O[ii], rd, risk_n * m.N[j])
            ctrl.append(r2)
        if not ctrl:
            continue
        tt = time.gmtime(t_out)
        out.append((part, sp, reg, R, sum(ctrl) / len(ctrl), mfe, (m.s, tt.tm_year, tt.tm_mon), oc))


def run_m3(rep, F):
    p = rep.p
    p("")
    p("=" * 110)
    p("M3. FAILED SHADOW: after a brk / fast stop-out, the reverse probe vs random entries (same hour, same stop in ATR)")
    p("=" * 110)
    p("PREDICTIONS  Ezio: none.  Claude: about equal overall; the fastest failures (<= 1h) a little better.")
    p("probe: the other way at the next M15 open, stop 1 risk unit, target 1.5, out after 5 trading days. Gross R.")
    p("   %-24s %6s %8s %12s %8s %12s %14s %8s" % ("", "n", "probe R", "", "control", "", "probe - ctrl", "P(tgt)"))

    def line(lab, xs):
        a = cmean([(x[3], x[6]) for x in xs])
        b = cmean([(x[4], x[6]) for x in xs])
        dl = cmean([(x[3] - x[4], x[6]) for x in xs])
        return "   %-24s %6d %8s %-12s %8s %-12s %8s %s %7s" % (
            lab, a[2], f3(a[0]), ft(a[1]), f3(b[0]), ft(b[1]), f3(dl[0]), ft(dl[1]),
            fp(pct(sum(1 for x in xs if x[7] == "target"), len(xs))))
    for part in ("brk", "fast"):
        xs = [x for x in F if x[0] == part]
        p(line("%s  ALL" % part, xs))
        for lab, _, _ in SPEEDS:
            p(line("   failed in %s" % lab, [x for x in xs if x[1] == lab]))
        for rg in ("er40 on", "er40 off"):
            p(line("   %s" % rg, [x for x in xs if x[2] == rg]))
        for s in MARKETS:
            ys = [x for x in xs if x[6][0] == s]
            if ys:
                p(line("   %s" % s, ys))
    p(YARD["M3"])


def run_m6(rep, book):
    p = rep.p
    p("")
    p("=" * 110)
    p("M6. SERIAL DEPENDENCE: does a loss predict the next trade (non-overlapping trades, per market)?")
    p("=" * 110)
    p("PREDICTIONS  Claude: P(loss | loss) inside the shuffle band for every part; neither line crossed.")
    rnd = random.Random(SEED)
    p("   %-6s %6s %7s %9s %9s %11s %11s %12s %9s %9s" % (
        "part", "pairs", "P(L)", "P(L|L)", "P(L|W)", "E[net|L]", "E[net|W]", "E[mirr|L]", "shuffle%", "block%"))
    for part in ("fast", "dip", "brk"):
        seqs = []
        for s in MARKETS:
            xs = sorted([x for x, q in book if q == part and x[0] == s], key=lambda x: x[8]["_t_in"])
            seq, last_out = [], -1.0
            for x in xs:
                if x[8]["_t_in"] >= last_out:
                    tt = time.gmtime(x[8]["_t_in"])
                    seq.append((x[5], 2 * x[6] - x[5], (tt.tm_year, tt.tm_mon)))
                    last_out = x[8]["_t_out"]
            if len(seq) >= 2:
                seqs.append(seq)
        if not seqs:
            p("   %-6s no trades" % part)
            continue

        def stats(sqs):
            n = ll = lw = nl = nw = 0
            sl = sw = ml = 0.0
            tot_l = tot = 0
            for sq in sqs:
                for a, b in zip(sq[:-1], sq[1:]):
                    n += 1
                    if a[0] < 0:
                        nl += 1
                        ll += b[0] < 0
                        sl += b[0]
                        ml += b[1]
                    else:
                        nw += 1
                        lw += b[0] < 0
                        sw += b[0]
                for x in sq:
                    tot += 1
                    tot_l += x[0] < 0
            en = sum(x[0] for sq in sqs for x in sq[1:]) / float(max(1, n))
            em = sum(x[1] for sq in sqs for x in sq[1:]) / float(max(1, n))
            enl, eml = (sl / nl, ml / nl) if nl else (None, None)
            skipg = (en - enl) if nl else None                       # gain per skipped trade vs a random skip
            mirg = ((eml - enl) - (em - en)) if nl else None         # extra mirror gain after a loss
            return (n, tot_l / float(tot), ll / float(nl) if nl else None, lw / float(nw) if nw else None,
                    enl, sw / nw if nw else None, eml, skipg, mirg)
        st = stats(seqs)
        real = st[2] - st[1] if st[2] is not None else None
        sh, bl, sk, mg = [], [], [], []
        for _ in range(PERMS):
            sq2 = []
            for sq in seqs:
                y = list(sq)
                rnd.shuffle(y)
                sq2.append(y)
            v = stats(sq2)
            if v[2] is not None:
                sh.append(v[2] - v[1])
                sk.append(v[7])
                mg.append(v[8])
            sq3 = []
            for sq in seqs:
                blocks = defaultdict(list)
                order = []
                for x in sq:
                    if x[2] not in blocks:
                        order.append(x[2])
                    blocks[x[2]].append(x)
                rnd.shuffle(order)
                sq3.append([x for k in order for x in blocks[k]])
            v = stats(sq3)
            if v[2] is not None:
                bl.append(v[2] - v[1])
        pc = lambda dist, r=None: (pct(sum(1 for v in dist if v < (real if r is None else r)), len(dist))
                                   if (real if r is None else r) is not None else None)
        p("   %-6s %6d %7s %9s %9s %11s %11s %12s %9s %9s" % (
            part, st[0], fp(100 * st[1]), fp(100 * st[2] if st[2] is not None else None),
            fp(100 * st[3] if st[3] is not None else None), f3(st[4]), f3(st[5]), f3(st[6]), fp(pc(sh)), fp(pc(bl))))
        psk, pmg = pc(sk, st[7]), pc(mg, st[8])
        p("          skip line: E[net] - E[net|L] = %s per skipped trade vs skipping at random, shuffle pct %s -> %s" % (
            f3(st[7]), fp(psk), "CROSSED" if (psk is not None and psk > 95) else "not crossed"))
        p("          mirror line: (E[mirr|L]-E[net|L]) - (E[mirr]-E[net]) = %s, shuffle pct %s -> %s" % (
            f3(st[8]), fp(pmg), "CROSSED" if (pmg is not None and pmg > 95) else "not crossed"))
    p("   shuffle% / block% = percentile of the real P(L|L) - P(L) among 500 order / month-block shuffles (>95 or <5 =")
    p("   beyond chance: persistent / contrarian). A line counts as CROSSED only above the shuffles' 95th percentile:")
    p("   every lane loses after costs on noise, so 'skipping a loser helps' is true of ANY skip and proves nothing.")
    p(YARD["M6"])


# ================================================================ main
def main():
    argv = sys.argv[1:]
    synth = None
    if "--db" in argv:
        k = argv.index("--db")
        synth = os.path.abspath(argv[k + 1])
        del argv[k:k + 2]
        if not os.path.exists(synth):
            print("no such file: %s" % synth)
            return
        A.find_db = lambda: synth
    mode = argv[0].lower() if argv else "all"
    if mode not in ("all", "cheap"):
        print("usage: python asiabo_probe.py [all|cheap] [--db synth/<file>.db]")
        return
    import asiabo_lab as L
    import asiabo_why as W
    W._install()
    W.WITH_CHAN = False
    name = "probe"
    if synth:
        b = os.path.splitext(os.path.basename(synth))[0]
        for pre in ("synth_", "probe_"):
            b = b[len(pre):] if b.startswith(pre) else b
        name = "probe_synth_" + b
    if os.environ.get("ASIABO_NO_VISION") or synth:
        def add_only(src):
            try:
                vdir = os.path.join(A.ROOT, A.VISION_DIR_NAME)
                os.makedirs(vdir, exist_ok=True)
                for n in os.listdir(src):
                    if os.path.isfile(os.path.join(src, n)):
                        shutil.copy2(os.path.join(src, n), os.path.join(vdir, n))
                print("claude vision: added %s (no wipe)" % os.path.basename(src))
            except Exception as e:
                print("(claude vision not updated: %s)" % e)
        A.publish_to_vision = add_only
    rep = A.Report(name)
    p = rep.p
    t0 = time.time()
    if synth:
        p("#" * 110)
        p("SYNTHETIC DATA (a cousin of bars.db, NOT the real market): %s   -- the YARDSTICK for the real run" % synth)
        p("#" * 110)
    p("=" * 110)
    p("THE PROBE STUDY (next_plan.md Phase 1, predictions in asiabo_probe.py written 2026-10-11)   mode: %s" % mode)
    p("=" * 110)
    p("Sealed exam years %s .. %s and Japan 225: not read. Measures only; decides nothing." % (A.SEAL_START, A.SEAL_END))
    specs = dict((x["name"], x) for x in A.COLLECT_SYMBOLS)
    DV = {}
    F3 = []
    rows_all, book_pm, det_all = [], [], {}
    rnd = random.Random(SEED)
    try:
        for s in MARKETS:
            if s not in specs:
                p("(%s: no spec, skipped)" % s)
                continue
            print("probe: %s ..." % s)
            try:
                m = L.PMarket(specs[s])
            except RuntimeError as e:
                p("(%s skipped: %s)" % (s, e))
                continue
            dv = Day(m, L)
            DV[s] = dv
            if mode == "all" and s in W.MARKETS:
                W._m1_cache(m)
                rb = []
                for nm, fn in L.P_LANES:
                    if nm in L.P_OMEGA_LANES:
                        fn(m, rb)
                rows = [(s,) + x for x in rb if (x[0], x[1]) in W.NEED_LV]
                rows_all += rows
                det = W.det_table(m)
                bk = W.book_of(rows, det)
                book_pm += bk
                er40 = {}
                for j in range(1, dv.n):
                    e = dv.er(j, 40)
                    if e:
                        er40[dv.key[j]] = e[0]
                m3_market(m, bk, er40, rnd, F3)
                if m.m1q:
                    m.m1q[0].close()
                m._m1cache.clear()
                det_all.update(det)
            del m
        if mode == "all" and rows_all:
            gb = W.book_of(rows_all, det_all)
            key = lambda xs: sorted((x[0], x[1], x[2], x[3], x[8]["_t_in"], q) for x, q in xs)
            same = key(gb) == key(book_pm)
            p("IDENTITY: book built per market %s the book built over all markets (%d trades)" % (
                "IDENTICAL to" if same else "DIFFERENT from", len(gb)))
            cnt = defaultdict(int)
            for x, q in gb:
                cnt[q] += 1
            p("book trades: " + ", ".join("%s %d" % kv for kv in sorted(cnt.items())))
        run_m1(rep, DV)
        run_m2(rep, DV)
        run_m4(rep, DV)
        run_m5(rep, DV)
        if mode == "all":
            run_m3(rep, F3)
            run_m6(rep, W.book_of(rows_all, det_all) if rows_all else [])
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
