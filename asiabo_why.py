"""
asiabo_why.py  --  THE WHY PHASE on the FROZEN omega book (frozen_design_v1; plan: why_phase_plan.md, written
2026-10-09 BEFORE any of these tests ran). Built 2026-10-10.

It changes nothing: it imports asiabo_lab.py and uses ITS lanes, walk, costs and one-position rule, so the book here is
the frozen book (checked against the lab's own sleeve code at every run: see "IDENTITY" at the top of the report).

    python asiabo_why.py            W5, W3, W1, W2, W4 (everything)
    python asiabo_why.py cheap      W5 + W3 only (no re-runs of lanes)
    python asiabo_why.py all --db synth/synth_dayshuffle_s1.db     the same on a cousin history (yardstick)

What each test may do (the plan's rules): REMOVE a part, or SWAP a fixed number for a DERIVED rule written beforehand
(D1, D2). Nothing new is added. Japan 225 and 2022-23 are never read.

  W5  cost stress     spreads x1.5 and x2 on the same trades. FLAG (not kill) a part net < 0 at x1.5 in 3 of 4 eras.
  W3  concentration   share of each part's R from its best 5% of trades / best month / best market-year; net without
                      the best market-year. KILL a part net <= 0 without it in 3 of 4 eras.
      anatomy         brk / fast: open R at 1h / 4h / 1 day / 3 days, MFE / MAE, winners vs losers.
  W1  plateau         each frozen number moved about +-25%, one at a time, everything else frozen. KILL a part whose
                      frozen value is an isolated peak: both neighbours keep less than half its EDGE/trade in 3 of 4
                      eras (only eras where the frozen edge is > 0 can count). EDGE = the lab's: net R minus the
                      coin-flip average with the same timing, stop, exit and costs. Net R/trade and R/yr also shown.
      D1 / D2         the derived-rule candidates, side by side with the fixed number's neighbours.
  W2  dose-response   edge by fine bins of the cause (range position, trend straightness / size, dip depth, inside-day
                      width). Flat or non-monotonic = the threshold is not tracking the cause (lowers confidence).
  W4  placebos        delayed entry (+15 min, +1h, +1 day, same exits) and a random entry day with the same filters and
                      exits (3 draws). The edge must fade the way the mechanism says, and vanish on random days.
"""
import os, sys, math, time, bisect, random, shutil, traceback
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import asiabo_lab as L

A = L.A
ERAS = L.POWER_ERAS
EY = L.H_YRS
PARTS = ("brk", "ins", "dip", "fast")
BRK_MK = L.K_BRK_MARKETS
DIP_MK = L.K_DIP_MARKETS
MARKETS = [s for s in A.HOUSE_SYMBOLS if s in BRK_MK]          # the book's markets only (dip markets are among them)
NEED_LV = {("main2", "box"), ("orb30", "range"), ("orb60", "range"), ("pdh2", "mid"), ("retest2", "0.25D"),
           ("inside", "mid"), ("rsi2", "long"), ("dip3", "long")}
CHAN_X = {"5d|L4": (4, 1.0), "5d|L6": (6, 1.0), "5d|D0.75": (5, 0.75), "5d|D1.25": (5, 1.25)}
D2_Z = 2.0 / math.sqrt(10.0)                    # 2 ATR over 10 days = 0.632 x sqrt(10) ATR
PLACEBO_DRAWS = 3
MIN_N = 20

# ---------------------------------------------------------------- yardstick (filled from the fake random-walk run)
YARD = {
    "W5": [
        "YARDSTICK (this file on 3 fake random-walk markets, 2026-10-10): with no edge every part is net < 0, so every",
        "    part FLAGs there. W5 only means something for a part that is net > 0 at x1: read how far x1.5 pulls it.",
    ],
    "W3": [
        "YARDSTICK (3 fake random walks, 2026-10-10): every part is net < 0 on noise, so the market-year rule kills all",
        "    four there; the rule only bites on a profitable part. ANATOMY on noise (ALL eras, winners, medians):",
        "    brk  winners positive at 1h 65-66%  4h 75-77%  1d 93%   share of final R in place at 4h 13-18%  1d 69-74%",
        "    fast winners positive at 1h 68-70%  4h 81-82%  1d 100%  share of final R in place at 4h 51-56%",
        "    So 'positive by hour 4' is ~75% (brk) / ~82% (fast) by geometry alone. Follow-through = clearly ABOVE these.",
    ],
    "W1": [
        "",
        "YARDSTICK (3 fake random walks, 2026-10-10): 1-3 PEAK eras out of 72 per seed, no part killed; edge/trade of",
        "    neighbours swung by up to +-0.10 R per era on noise. D1 / D2 'derived better' ranged 0-4 of 4 on noise, so a",
        "    derived rule needs 4 of 4 on both sides (and a sensible size) before it is worth proposing.",
    ],
    "W2": [
        "",
        "YARDSTICK (3 fake random walks, 2026-10-10): the clustered slope t ranged -2.7 .. +2.2 over 90 slopes of pure",
        "    noise, and the RANK CORR reached -0.9 / -1.0 on noise (seven bins of overlapping trades). A dose-response",
        "    counts only if the slope's t is beyond about +-3 AND points the predicted way in OLD and NEW.",
    ],
    "W4": [
        "",
        "YARDSTICK (3 fake random walks, 2026-10-10): a part's real edge reached t +2.2 on noise; 'kept %' then swung from",
        "    -2251% to +173% (meaningless when the real edge's t is small: read 'kept' only where the real t is ~3+).",
        "    Random-day placebos (all draws): t -1.8 .. +1.4. ins inside-days vs every other day: t -2.1 .. +2.3.",
    ],
}


# ================================================================ hooks into the lab
ORIG_PT, ORIG_PP = L.p_trade, L.p_plans


def _pt(m, rows, lane, var, j0, entry, d, sd, exits, t_in=None, same_bar_stop=False, tags=None, close_idx=None,
        plans=None, sub=None):
    """The lab's p_trade, plus what the why tests need to re-walk a trade: entry price, bar, risk and close bar."""
    tg = dict(tags) if tags else {}
    tg.update({"_e": entry, "_j0": j0, "_sd": sd, "_ci": close_idx})
    return ORIG_PT(m, rows, lane, var, j0, entry, d, sd, exits, t_in, same_bar_stop, tg, close_idx, plans, sub)


def _pp(m, j0, entry, d, sd, exits, tgt_r=2.0, close_idx=None):
    """The lab's p_plans, plus the chandelier neighbours (W1) whenever the 5-day chandelier is asked for."""
    out = ORIG_PP(m, j0, entry, d, sd, exits, tgt_r, close_idx)
    if "5d" in exits and WITH_CHAN:
        N = m.dN(j0) or sd
        for k, (days, dist) in CHAN_X.items():
            out[k] = (None, j0 + 96 * days, ("chan", dist * N))
    return out


WITH_CHAN = True


def _install():
    L.p_trade, L.p_plans = _pt, _pp
    L.P_EXITS = ("close", "5d")                 # only the exits the frozen book uses (each plan walks independently)
    L.REAL_COSTS = True


def _m1_cache(m):
    """Minute bars WITH their timestamps, cached per M15 bar (the ORB variants and re-runs ask for the same bars)."""
    cache = {}
    shift = A.DB_UTC_OFFSET_HOURS * 3600.0

    def m1t(i):
        if i in cache:
            return cache[i]
        out = []
        if m.m1q is not None:
            con, q, args = m.m1q
            for r in con.execute(q, args + [m._m1key(m.T[i]), m._m1key(m.T[i] + 900)]).fetchall():
                try:
                    out.append((A.to_epoch(r[0]) - shift, float(r[1]), float(r[2]), float(r[3]), float(r[4])))
                except (TypeError, ValueError):
                    continue
        cache[i] = out
        return out
    m.m1t = m1t
    m.m1 = lambda i: ([x[1:] for x in m1t(i)] or None)
    m._m1cache = cache


# ================================================================ detectors (W1 neighbours, D1, D2) and day reads
DET_KEYS = {"base": {}}
for _w in (15, 25, 16, 24):
    DET_KEYS[("ew", _w)] = {"ew": _w}
for _t in (0.80, 0.90):
    DET_KEYS[("thr", _t)] = {"thr": _t}
for _w in (8, 12):
    DET_KEYS[("erw", _w)] = {"erw": _w}
    DET_KEYS[("D2", _w)] = {"erw": _w, "mv": D2_Z * math.sqrt(_w)}
for _e in (0.3, 0.5):
    DET_KEYS[("eff", _e)] = {"eff": _e}
for _v in (1.5, 2.5):
    DET_KEYS[("mv", _v)] = {"mv": _v}


def det_table(m, ew=20, thr=0.85, erw=10, eff=0.4, mv=2.0):
    """The lab's edge20 / er10 (PMarket.__init__), with each number as a parameter. Defaults = the lab exactly."""
    out = {}
    cl, seg = m.cl, m.seg
    lo_thr = round(1.0 - thr, 10)
    for j in range(1, len(m.D)):
        if not m.f[j]:
            continue
        N = m.N[j]
        dd = {}
        h, l = m.hh(j, ew), m.ll(j, ew)
        if h is not None and h > l:
            pos = (cl[j - 1] - l) / (h - l)
            dd["edge20"] = 1 if pos >= thr else (-1 if pos <= lo_thr else 0)
        if j - erw - 1 >= seg[j]:
            path = sum(abs(cl[k] - cl[k - 1]) for k in range(j - erw, j))
            mvv = cl[j - 1] - cl[j - 1 - erw]
            dd["er10"] = (1 if mvv > 0 else -1) if (path and abs(mvv) / path >= eff and abs(mvv) >= mv * N) else 0
        out[(m.s, m.D[j][0])] = dd
    return out


def day_reads(m):
    """Continuous versions of the detector inputs, per day (W2): position of yesterday's close in the 20-day range,
    er10 efficiency (signed) and the 10-day move in daily ATRs (signed)."""
    out = {}
    cl, seg = m.cl, m.seg
    for j in range(1, len(m.D)):
        if not m.f[j]:
            continue
        N = m.N[j]
        r = {}
        h, l = m.hh(j, 20), m.ll(j, 20)
        if h is not None and h > l:
            r["pos"] = (cl[j - 1] - l) / (h - l)
        if j - 11 >= seg[j]:
            path = sum(abs(cl[k] - cl[k - 1]) for k in range(j - 10, j))
            mvv = cl[j - 1] - cl[j - 11]
            if path:
                r["eff"] = mvv / path
            r["mvN"] = mvv / N
        out[(m.s, m.D[j][0])] = r
    return out


# ================================================================ sleeves (the lab's _k_sleeves, detector as a parameter)
def _agree(x, det, names):
    t = x[8]
    dd = det.get((x[0], t.get("_dk")))
    if not dd or t.get("_d") is None:
        return False
    return any(dd.get(n, 0) == t["_d"] for n in names)


def sleeves(rows, det, brk_exit="5d"):
    sl = defaultdict(list)
    for x in rows:
        if x[6] is None or not x[8].get("_t_in") or not x[8].get("_t_out"):
            continue
        if x[1] in L.H_WIDE and x[2] == L.H_WIDE[x[1]] and x[3] == brk_exit and _agree(x, det, ("edge20", "er10")):
            if x[0] in BRK_MK:
                sl["brk"].append(x)
        elif x[1] == "inside" and x[3] == "close":
            if x[0] in BRK_MK:
                sl["ins"].append(x)
        elif x[1] in ("rsi2", "dip3") and x[2] == "long" and x[3] == "own":
            if x[0] in DIP_MK:
                sl["dip"].append(x)
        elif x[3] == "close" and ((x[1] == "orb30" and x[2] == "range" and _agree(x, det, ("er10",))) or
                                  (x[1] == "main2" and x[2] == "box" and _agree(x, det, ("edge20",)))):
            if x[0] in BRK_MK:
                sl["fast"].append(x)
    return sl


def book_of(rows, det, brk_exit="5d"):
    """-> [(row, part)] the frozen book: gates off, one position per part / market / direction (the lab's _k_walk)."""
    sl = sleeves(rows, det, brk_exit)
    bk, _ = L._k_walk(sl, {}, "off")
    return [(x, s) for x, z, s, rk in bk]


# ================================================================ parameterised copies of the omega lanes (W1, W2)
def lane_orb_x(m, rows, minutes):
    """orb30 with an opening range of any length in MINUTES (the range and the first entry minute are read on M1 bars
    when the length is not a whole number of M15 bars). Same stop ('range'), same exits, same 'no entry in the last
    hour'. At 30 it is the lab's orb30 exactly (checked)."""
    nfull, rem = divmod(minutes, 15)
    nb = nfull + (1 if rem else 0)
    for j, i0, i1 in L.p_days(m):
        io = L.p_session_open(m, i0, i1)
        if io is None:
            continue
        ce = m.next_close[io]
        if ce is None or ce > i1 + 96:
            continue
        r = list(range(io, io + nb))
        if r[-1] >= m.n or any(m.loc[x] != m.open_min + 15 * (x - io) for x in r):
            continue
        full = r[:nfull]
        hi = max(m.H[x] for x in full)
        lo = min(m.L[x] for x in full)
        e = None
        if rem:
            ip = io + nfull
            mins = m.m1t(ip)
            if not mins:
                ORB_SKIP[(m.s, minutes)] += 1
                continue
            cut = m.T[ip] + rem * 60
            rng_ = [x for x in mins if x[0] < cut]
            rest = [x[1:] for x in mins if x[0] >= cut]
            if rng_:
                hi = max(hi, max(x[2] for x in rng_))
                lo = min(lo, min(x[3] for x in rng_))
            skip = False
            for k, (o, h, l, c) in enumerate(rest):
                a, b = h >= hi, l <= lo
                if a and b:
                    skip = True
                    break
                if a:
                    e = (ip, 1, max(hi, o), rest[k:])
                    break
                if b:
                    e = (ip, -1, min(lo, o), rest[k:])
                    break
            if skip:
                continue
            if e is None:
                e = L.p_stop_entry(m, ip + 1, ce - 4, hi, lo)
        else:
            e = L.p_stop_entry(m, io + nb, ce - 4, hi, lo)
        if e is None:
            continue
        i, d, px, sub = e
        tags = {"nr7": m.nr7(j), "trend": m.with_trend(j, d)}
        _pt(m, rows, "orb30", "range", i, px, d, px - lo if d > 0 else hi - px, ("close", "5d"), same_bar_stop=True,
            tags=tags, close_idx=ce, sub=sub)


ORB_SKIP = defaultdict(int)


def lane_inside_x(m, rows, f):
    """inside day with the stop at fraction f of yesterday's range from the far side (0.5 = the middle = the lab's)."""
    for j, i0, i1 in L.p_days(m):
        if j < 2 or m.seg[j] > j - 2:
            continue
        if not (m.hi[j - 1] <= m.hi[j - 2] and m.lo[j - 1] >= m.lo[j - 2]):
            continue
        ph, pl = m.hi[j - 1], m.lo[j - 1]
        e = L.p_stop_entry(m, i0, i1, ph, pl)
        if e is None:
            continue
        i, d, px, sub = e
        stop = (pl + f * (ph - pl)) if d > 0 else (ph - f * (ph - pl))
        if abs(px - stop) <= 0:
            continue
        # exits as the lab passes them (close AND 5d): with the 5-day plan in the walk, a fill on the day's last bar
        # exits at the NEXT bar's close (a lab quirk kept on purpose); with 'close' alone that trade would be lost
        _pt(m, rows, "inside", "mid", i, px, d, abs(px - stop), ("close", "5d"), same_bar_stop=True, close_idx=i1,
            sub=sub)


def _own_row(m, rows, lane, var, j0, d, N, res, tags_extra=None):
    """res = (net price, gross price, exit bar, mirror net price) from an own-exit walk -> one row (the lab's form)."""
    if res is None or res[0] is None:
        return
    t_in = m.T[j0]
    era = L._p_era(t_in)
    if era is None:
        return
    ra, rb = res[0] / N, res[3] / N
    tg = m.tags(j0, d, N)
    tg["_t_in"], tg["_t_out"] = t_in, m.T[min(res[2], m.n - 1)] + 900
    tg["_e"], tg["_j0"], tg["_sd"] = m.O[j0], j0, N
    if tags_extra:
        tg.update(tags_extra)
    rows.append((lane, var, "own", era, ra, (ra + rb) / 2.0, res[1] / N, tg))


def lane_rsi2_x(m, rows, level=10.0, smaw=200, loose=False):
    """The lab's rsi2 (both sides share one 'busy' clock, as in the lab), level / average length as parameters.
    loose=True (W2): every long signal day with RSI(2) < level, no busy clock, the RSI value kept in the tags."""
    busy = -1
    for j, i0, i1 in L.p_days(m):
        N = m.N[j]
        s, r = m.sma(j, smaw), m.rsi2[j]
        if s is None or r is None or i1 + 1 >= m.n:
            continue
        if not loose and i1 + 1 <= busy:
            continue
        c = m.cl[j]
        if loose:
            d = 1 if (c > s and r < level) else 0
        else:
            d = 1 if (c > s and r < level) else (-1 if (c < s and r > 100.0 - level) else 0)
        if not d:
            continue
        ex = L._p_rsi_walk(m, i1 + 1, m.O[i1 + 1], d, N)
        if not loose:
            busy = ex[2]
        _own_row(m, rows, "rsi2", "long" if d > 0 else "short", i1 + 1, d, N, ex, {"_rsi": r})


def _dip3_walk(m, j0, entry, d, N):
    """The lab's dip3 exit from bar j0: first close beyond the previous day's high (low) or 10 days; 3N disaster stop.
    -> (net, gross, exit bar, mirror net) or (None, None, bar)."""
    stop = entry - d * 3 * N
    res = None
    for k in range(j0, m.n):
        if k > j0 and m.T[k] - m.T[k - 1] > L.P_MAX_GAP:
            break
        o, h, l = m.O[k], m.H[k], m.L[k]
        px = None
        if d > 0 and l <= stop:
            px = o if (o <= stop and k > j0) else stop
        if d < 0 and h >= stop:
            px = o if (o >= stop and k > j0) else stop
        if px is None and k == m.D[m.di[k]][2] and k + 1 < m.n:
            dk = m.di[k]
            if (d > 0 and m.C[k] > m.hi[dk - 1]) or (d < 0 and m.C[k] < m.lo[dk - 1]) or dk - m.di[j0] >= 10:
                px, k = m.O[k + 1], k + 1
        if px is not None:
            res = (px, k)
            break
    if res is None:
        return None, None, m.n
    px, k = res
    t_in, t_out = m.T[j0], m.T[k] + 900
    if m.dq.overlaps(t_in, t_out):
        return None, None, k
    g = d * (px - entry)
    cst = m.cost(j0, entry)
    return g - cst + m.swap(d, t_in, t_out), g, k, (-g - cst + m.swap(-d, t_in, t_out))


def lane_dip3_x(m, rows, count=3, smaw=200, loose=False):
    """The lab's dip3 with the down-close count and the average length as parameters (both sides share one busy clock).
    loose=True (W2): every long day after 2+ down closes above the average, no busy clock; the streak length and its
    depth (in daily ATRs) kept in the tags."""
    busy = -1
    c = m.cl
    for j, i0, i1 in L.p_days(m):
        if j < (2 if loose else count) + 1 or i1 + 1 >= m.n or (not loose and i1 + 1 <= busy):
            continue
        s = m.sma(j, smaw)
        if s is None:
            continue
        N = m.N[j]
        extra = None
        if loose:
            if not c[j] > s:
                continue
            k = 0
            while j - k - 1 >= m.seg[j] and c[j - k] < c[j - k - 1]:
                k += 1
            if k < 2:
                continue
            d = 1
            extra = {"_streak": k, "_depthN": (c[j - k] - c[j]) / N}
        else:
            dn = all(c[j - q] < c[j - q - 1] for q in range(count))
            up = all(c[j - q] > c[j - q - 1] for q in range(count))
            if c[j] > s and dn:
                d = 1
            elif c[j] < s and up:
                d = -1
            else:
                continue
        j0 = i1 + 1
        res = _dip3_walk(m, j0, m.O[j0], d, N)
        if res[0] is None:
            if not loose and res[2] < m.n:
                busy = res[2]                     # the lab: an exit was found (hole across it) -> busy until then
            continue
        if not loose:
            busy = res[2]
        _own_row(m, rows, "dip3", "long" if d > 0 else "short", j0, d, N, res, extra)


# ================================================================ per-row extras (W5 spread part, W3 anatomy)
def spread_r(m, x):
    """The SPREAD part of the round-trip cost of row x, in R (commission and swap are not scaled by W5)."""
    t = x[8]
    j0 = t.get("_j0")
    if j0 is None:
        j0 = bisect.bisect_left(m.T, t["_t_in"])
    e = t.get("_e") or m.O[j0]
    sd = (t.get("risk_size") or 0) * (t.get("_N") or 0)
    if sd <= 0:
        return 0.0
    comm = L.REAL_COMM_BP.get(m.s, 1.0) / 1e4 * abs(e)
    return max(0.0, m.cost(j0, e) - comm) / sd


ANAT_K = (("1h", 4), ("4h", 16), ("1d", 96), ("3d", 288))


def anatomy(m, x):
    """Open gross R after 1h / 4h / 1 day / 3 days of trading bars (= the final R if the trade had ended), and the
    MFE / MAE so far (in R, from the bar after the fill)."""
    t = x[8]
    j0, e, sd, d = t.get("_j0"), t.get("_e"), t.get("_sd"), t.get("_d")
    if j0 is None or not sd or not d:
        return None
    ja = bisect.bisect_left(m.T, t["_t_out"] - 900)
    out = {"hold_h": (t["_t_out"] - t["_t_in"]) / 3600.0}
    mfe = mae = 0.0
    j = j0 + 1
    for name, k in ANAT_K:
        last = min(j0 + k - 1, ja)
        while j <= last and j < m.n:
            mfe = max(mfe, d * ((m.H[j] if d > 0 else m.L[j]) - e) / sd)
            mae = min(mae, d * ((m.L[j] if d > 0 else m.H[j]) - e) / sd)
            j += 1
        if j0 + k - 1 >= ja:
            out[name] = (x[7], mfe, mae, True)
        else:
            out[name] = (d * (m.C[j0 + k - 1] - e) / sd, mfe, mae, False)
    return out


# ================================================================ W4 placebos
def _next_day_bar(m, j0):
    dj = m.di[j0]
    if dj + 1 >= len(m.D) or m.seg[dj + 1] != m.seg[dj]:
        return None
    tgt = m.loc[j0]
    for i in range(m.D[dj + 1][1], m.D[dj + 1][2] + 1):
        if m.loc[i] >= tgt:
            return i
    return None


def _close_of(m, x, j1, same_day):
    lane, t = x[1], x[8]
    if same_day:
        ci = t.get("_ci")
        return ci if ci is not None else m.next_close[t["_j0"]]
    if lane == "inside":
        return m.D[m.di[j1]][2]
    ci = m.next_close[j1]
    return ci if (ci is not None and ci <= m.D[m.di[j1]][2] + 96) else None


def delayed(m, x, part, delay):
    """Re-runs book trade x entered LATER (at the open of the bar 15 min / 1h / one trading day after the real fill),
    same direction, same stop distance, same exit rule. -> row or None ('no time left' counts as None)."""
    t = x[8]
    d = t["_d"]
    j0 = t.get("_j0")
    if j0 is None:
        j0 = bisect.bisect_left(m.T, t["_t_in"])
    if delay == "1d":
        j1 = _next_day_bar(m, j0)
    else:
        j1 = j0 + (1 if delay == "15m" else 4)
    if j1 is None or j1 >= m.n or m.T[j1] - m.T[j0] > L.P_MAX_GAP:
        return None
    out = []
    if part == "dip":
        N = t["risk_size"] * t["_N"]
        res = L._p_rsi_walk(m, j1, m.O[j1], d, N) if x[1] == "rsi2" else _dip3_walk(m, j1, m.O[j1], d, N)
        _own_row(m, out, x[1], x[2], j1, d, N, res)
    else:
        sd = t["_sd"]
        if part == "brk":
            plans = {"5d": (None, j1 + 480, ("chan", m.dN(j1) or sd))}
        else:
            ci = _close_of(m, x, j1, delay != "1d")
            if ci is None or j1 >= ci:
                return None
            plans = {"close": (None, ci, None)}
        ORIG_PT(m, out, x[1], x[2], j1, m.O[j1], d, sd, (), plans=plans)
    if not out:
        return None
    y = out[0]
    return (m.s, y[0], y[1], x[3], x[4], y[4], y[5], y[6], y[7])


def placebo_days(m, det):
    """Eligible random days per era: {name: {era: [(j, dir)]}}. brk = edge20 OR er10 points one way (not both ways);
    orb30 = er10 points; main2 = edge20 points; dip = close above the 200-day average (long)."""
    out = defaultdict(lambda: defaultdict(list))
    for j in range(1, len(m.D) - 1):
        dd = det.get((m.s, m.D[j][0]))
        era = L._p_era(m.T[m.D[j][1]])
        if era is None:
            continue
        if dd:
            vals = set(v for v in (dd.get("edge20", 0), dd.get("er10", 0)) if v)
            if len(vals) == 1:
                out["brk"][era].append((j, vals.pop()))
            if dd.get("er10"):
                out["orb30"][era].append((j, dd["er10"]))
            if dd.get("edge20"):
                out["main2"][era].append((j, dd["edge20"]))
        s = m.sma(j, 200)
        if s is not None and m.cl[j] > s and m.N[j]:
            out["dip"][era].append((j, 1))
    return out


def random_entry(m, x, part, days, rnd):
    """One placebo for book trade x: a random day of the same market and era where the same filter points, in the
    filter's direction, entered at the same local time (brk / fast) or the next open (dip), with the same stop in daily
    ATRs and the same exit rule. -> row or None."""
    t = x[8]
    if part == "dip":
        pool = days["dip"].get(x[4]) or []
    elif part == "fast":
        pool = days[x[1]].get(x[4]) or []
    else:
        pool = days["brk"].get(x[4]) or []
    if not pool:
        return None
    j, d = pool[rnd.randrange(len(pool))]
    N = m.N[j]
    if not N:
        return None
    out = []
    if part == "dip":
        j1 = m.D[j][2] + 1
        if j1 >= m.n:
            return None
        res = L._p_rsi_walk(m, j1, m.O[j1], d, N) if x[1] == "rsi2" else _dip3_walk(m, j1, m.O[j1], d, N)
        _own_row(m, out, x[1], x[2], j1, d, N, res)
    else:
        j0 = t.get("_j0")
        tgt = m.loc[j0]
        j1 = None
        for i in range(m.D[j][1], m.D[j][2] + 1):
            if m.loc[i] >= tgt:
                j1 = i
                break
        if j1 is None:
            return None
        sd = t["_sd"] / t["_N"] * N
        if part == "brk":
            plans = {"5d": (None, j1 + 480, ("chan", m.dN(j1) or sd))}
        else:
            ci = m.next_close[j1]
            if ci is None or ci > m.D[j][2] + 96 or j1 >= ci:
                return None
            plans = {"close": (None, ci, None)}
        ORIG_PT(m, out, x[1], x[2], j1, m.O[j1], d, sd, (), plans=plans)
    if not out:
        return None
    y = out[0]
    return (m.s, y[0], y[1], x[3], y[3], y[4], y[5], y[6], y[7])


# ================================================================ statistics helpers
def _mean(v):
    return sum(v) / len(v) if v else None


def _median(v):
    if not v:
        return None
    s = sorted(v)
    n = len(s)
    return s[n // 2] if n % 2 else 0.5 * (s[n // 2 - 1] + s[n // 2])


def pstats(xs):
    """xs = rows -> (n, net R/trade, edge R/trade, R total)."""
    n = len(xs)
    if not n:
        return (0, None, None, 0.0)
    net = sum(x[5] for x in xs)
    edge = sum(x[5] - x[6] for x in xs if x[6] is not None)
    return n, net / n, edge / n, net


def by_part_era(book):
    g = defaultdict(list)
    for x, s in book:
        g[(s, x[4])].append(x)
    return g


def _f(v, w=6, p=3):
    return ("%+*.*f" % (w, p, v)) if v is not None else ("%*s" % (w, "-"))


def _spearman(ys):
    """rank correlation of bin order with ys (None skipped)."""
    pts = [(i, y) for i, y in enumerate(ys) if y is not None]
    if len(pts) < 3:
        return None
    xs = [p[0] for p in pts]
    rk = sorted(range(len(pts)), key=lambda k: pts[k][1])
    ry = [0] * len(pts)
    for r, k in enumerate(rk):
        ry[k] = r
    rx = list(range(len(pts)))
    n = len(pts)
    d2 = sum((rx[i] - ry[i]) ** 2 for i in range(n))
    return 1.0 - 6.0 * d2 / (n * (n * n - 1))


def _cl(x):
    tt = time.gmtime(x[8]["_t_in"])
    return (x[0], tt.tm_year, tt.tm_mon)


def ct(xs, val=lambda x: x[5] - x[6]):
    """mean of val over rows and its t, with the standard error CLUSTERED by market x calendar month of entry.
    Trades of the same market and month overlap (several lanes, multi-day holds) and are not independent: on the fake
    random walk, raw counts made +-0.3R swings between bins look like 10 standard errors. -> (mean, t) or (None, None)"""
    ys = [(val(x), _cl(x)) for x in xs]
    n = len(ys)
    if n < 2:
        return None, None
    mu = sum(y for y, c in ys) / n
    g = defaultdict(float)
    for y, c in ys:
        g[c] += y - mu
    k = len(g)
    if k < 2:
        return mu, None
    v = sum(e * e for e in g.values()) * k / (k - 1.0) / (n * n)
    return mu, (mu / math.sqrt(v) if v > 0 else None)


def slope_t(pairs):
    """pairs = [(bin index, row)] -> (slope of edge per bin step, clustered t). OLS of edge on the bin index."""
    n = len(pairs)
    if n < 10:
        return None, None
    xb = sum(b for b, x in pairs) / n
    yb = sum(x[5] - x[6] for b, x in pairs) / n
    sxx = sum((b - xb) ** 2 for b, x in pairs)
    if sxx <= 0:
        return None, None
    sl = sum((b - xb) * (x[5] - x[6] - yb) for b, x in pairs) / sxx
    g = defaultdict(float)
    for b, x in pairs:
        g[_cl(x)] += (b - xb) * ((x[5] - x[6]) - yb - sl * (b - xb))
    k = len(g)
    if k < 2:
        return sl, None
    v = sum(e * e for e in g.values()) * k / (k - 1.0) / (sxx * sxx)
    return sl, (sl / math.sqrt(v) if v > 0 else None)


def _t(v):
    return ("t%+5.1f" % v) if v is not None else "t   - "


# ================================================================ the run
class Run(object):
    def __init__(self, rep, full):
        self.rep, self.full = rep, full
        self.rows = []                       # base rows of every book market
        self.det = defaultdict(dict)         # det key -> {(s, dk): {...}}
        self.reads = {}                      # (s, dk) -> continuous reads
        self.var_rows = defaultdict(list)    # variant key -> rows (replacing lanes)
        self.loose = []                      # W2 dip rows
        self.delay = defaultdict(list)       # delay -> [(part, real row, delayed row)]
        self.rand = defaultdict(list)        # draw -> [(part, real row, placebo row)]
        self.anat = {}                       # id(row) -> anatomy
        self.spr = {}                        # id(row) -> spread part in R
        self.checks = []
        self.lab_book_ids = set()

    def market(self, s, spec):
        p = self.rep.p
        t0 = time.time()
        print("why: loading %s ..." % s)
        try:
            m = L.PMarket(spec)
        except RuntimeError as e:
            p("%s: skipped (%s)" % (s, str(e).splitlines()[0]))
            return
        _m1_cache(m)
        rb = []
        for name, fn in L.P_LANES:
            if name in L.P_OMEGA_LANES:
                print("why: %s %s ..." % (s, name))
                fn(m, rb)
        rows = [(s,) + x for x in rb if (x[0], x[1]) in NEED_LV]
        self.rows += rows
        for j, d in enumerate(m.D):                       # the lab's P_DAYS, for the identity check with its own code
            if m.det[j] is not None:
                L.P_DAYS[(m.s, d[0])] = (time.strftime("%Y-%m", time.gmtime(m.T[d[1]])), m.det[j], L._p_era(m.T[d[1]]))
        for k, kw in DET_KEYS.items():
            self.det[k].update(det_table(m, **kw))
        self.reads.update(day_reads(m))
        mine = det_table(m)
        bad = sum(1 for j, d in enumerate(m.D) if m.det[j] is not None and any(
            mine.get((s, d[0]), {}).get(k) != m.det[j].get(k) for k in ("edge20", "er10")))
        self.checks.append("%s detector copy vs the lab's: %d day(s) differ" % (s, bad))
        for x in rows:
            self.spr[id(x)] = spread_r(m, x)
        # pdh2 'mid' on inside days must equal the inside lane (same entry, stop and close): a free check
        for x in rows:
            if x[1] == "pdh2":
                j = m.di[x[8]["_j0"]]
                x[8]["_inside"] = 1 if (j >= 2 and m.seg[j] <= j - 2 and m.hi[j - 1] <= m.hi[j - 2]
                                        and m.lo[j - 1] >= m.lo[j - 2]) else 0
        # the frozen book of this market (one position per part / market / direction is per market, so this is exact)
        bk = book_of(rows, self.det["base"])
        for x, part in bk:
            if part in ("brk", "fast"):
                a = anatomy(m, x)
                if a:
                    self.anat[id(x)] = a
        if self.full:
            print("why: %s variants ..." % s)
            vr = self.var_rows
            for mins in (22, 30, 38):
                lane_orb_x(m, vr[("orb", mins)], mins)
            for f in (0.4, 0.5, 0.6):
                lane_inside_x(m, vr[("ins", f)], f)
            if s in DIP_MK:
                for lv in (7.5, 10.0, 12.5):
                    lane_rsi2_x(m, vr[("rsi", lv)], level=lv)
                for cn in (2, 3, 4):
                    lane_dip3_x(m, vr[("dip3", cn)], count=cn)
                for w in (150, 250):
                    lane_rsi2_x(m, vr[("sma", w)], smaw=w)
                    lane_dip3_x(m, vr[("sma", w)], smaw=w)
                lr = []
                lane_rsi2_x(m, lr, level=30.0, loose=True)
                lane_dip3_x(m, lr, loose=True)
                self.loose += [(s,) + x for x in lr]
            for k in vr:
                vr[k] = [((s,) + x) if len(x) == 8 else x for x in vr[k]]
            print("why: %s placebos ..." % s)
            for x, part in bk:
                for dl in ("15m", "1h", "1d"):
                    y = delayed(m, x, part, dl)
                    self.delay[dl].append((part, x, y))
            days = placebo_days(m, self.det["base"])
            for draw in range(PLACEBO_DRAWS):
                rnd = random.Random("%s|%d" % (s, draw))
                for x, part in bk:
                    if part == "ins":
                        continue
                    self.rand[draw].append((part, x, random_entry(m, x, part, days, rnd)))
        if m.m1q:
            m.m1q[0].close()
        print("why: %s done (%.0fs, %d minute-bar lookups cached)" % (s, time.time() - t0, len(m._m1cache)))
        del m

    # -------------------------------------------------------------- variant row sets
    def rows_with(self, replace):
        """base rows with the given lanes replaced: replace = {lane: variant key}."""
        if not replace:
            return self.rows
        out = [x for x in self.rows if x[1] not in replace]
        for lane, key in replace.items():
            out += [x for x in self.var_rows[key] if x[1] == lane]
        return out


def report(run):
    rep = run.rep
    p = rep.p
    base = book_of(run.rows, run.det["base"])
    # ---------------------------------------------------------- identity
    p("")
    p("=" * 110)
    p("IDENTITY  (this file must trade the frozen book, or nothing below means anything)")
    p("=" * 110)
    lab_sl = L._k_sleeves(run.rows)
    lab_bk, _ = L._k_walk(lab_sl, {}, "off")
    a = sorted((x[0], x[1], x[2], x[3], round(x[8]["_t_in"]), s) for x, s in base)
    b = sorted((x[0], x[1], x[2], x[3], round(x[8]["_t_in"]), s) for x, z, s, rk in lab_bk)
    p("  book from this file vs the lab's own _k_sleeves + _k_walk (gates off): %d vs %d trades, %s" % (
        len(a), len(b), "IDENTICAL" if a == b else "DIFFERENT (stop: something is wrong)"))
    for c in run.checks:
        p("  " + c)
    if run.full:
        def same(lane, key, var="range", ex=None):
            r0 = sorted((x[0], x[2], x[3], round(x[8]["_t_in"]), round(x[5], 9)) for x in run.rows
                        if (lane not in ("rsi2", "dip3") or x[0] in DIP_MK) and x[1] == lane and x[2] == var and (ex is None or x[3] in ex))
            r1 = sorted((x[0], x[2], x[3], round(x[8]["_t_in"]), round(x[5], 9)) for x in run.var_rows[key]
                        if (lane not in ("rsi2", "dip3") or x[0] in DIP_MK) and x[1] == lane and x[2] == var and (ex is None or x[3] in ex))
            return "%d vs %d rows, %s" % (len(r0), len(r1), "IDENTICAL" if r0 == r1 else "DIFFERENT")
        p("  orb30 rebuilt at 30 minutes vs the lab's orb30:      " + same("orb30", ("orb", 30), "range", ("close", "5d")))
        p("  inside rebuilt with the stop at 0.5 vs the lab's:     " + same("inside", ("ins", 0.5), "mid", ("close",)))
        if run.var_rows.get(("rsi", 10.0)):
            p("  rsi2 rebuilt at level 10 vs the lab's (long):         " + same("rsi2", ("rsi", 10.0), "long"))
            p("  dip3 rebuilt with 3 down closes vs the lab's (long):  " + same("dip3", ("dip3", 3), "long"))
        ins = sorted((x[0], round(x[8]["_t_in"]), round(x[5], 9)) for x in run.rows if x[1] == "inside" and x[3] == "close")
        pi = sorted((x[0], round(x[8]["_t_in"]), round(x[5], 9)) for x in run.rows
                    if x[1] == "pdh2" and x[2] == "mid" and x[3] == "close" and x[8].get("_inside"))
        p("  pdh2 'mid' exit 'close' on inside days vs the inside lane (same rule): %d vs %d, %s" % (
            len(pi), len(ins), "IDENTICAL" if pi == ins else "DIFFERENT"))
        if ORB_SKIP:
            p("  ORB days skipped for missing minute bars: " + ", ".join("%s %dmin %d" % (k[0], k[1], v)
                                                                        for k, v in sorted(ORB_SKIP.items())))
    p("")
    p("THE FROZEN BOOK here (net R per trade / coin-flip EDGE per trade and its clustered t / R per year; 1R per trade):")
    p("  (YARDSTICK, 3 fake random walks: these per-era t values ranged -1.7 .. +3.0 over 60 cells of pure noise)")
    g = by_part_era(base)
    for s in PARTS + ("ALL",):
        line = "  %-4s" % s
        for era in ERAS:
            xs = [x for x, q in base if (q == s or s == "ALL") and x[4] == era]
            n, net, edge, tot = pstats(xs)
            line += " | %s n%4d net %s edge %s %s %+6.1f R/yr" % (era[-5:], n, _f(net), _f(edge), _t(ct(xs)[1]),
                                                                  tot / EY[era])
        p(line)

    w5(run, base)
    w3(run, base)
    if run.full:
        w1(run, base)
        w2(run)
        w4(run, base)


# ---------------------------------------------------------------- W5
def w5(run, base):
    p = run.rep.p
    p("")
    p("=" * 110)
    p("W5. COST STRESS: the recorded spread x1.5 and x2 on the SAME trades (commission and swap unchanged)")
    p("=" * 110)
    p("PREDICTION (2026-10-09): fast and ins suffer most (short holds); brk and dip barely.")
    p("RULE: FLAG (not kill) a part net < 0 per trade at x1.5 in 3 of 4 eras -> live only if real spreads are confirmed")
    p("      at or below the tested level.")
    p("Each cell: net R per trade at x1 / x1.5 / x2   (spread cost per trade in R at x1)")
    for s in PARTS + ("ALL",):
        line = "  %-4s" % s
        neg = 0
        for era in ERAS:
            xs = [x for x, q in base if (q == s or s == "ALL") and x[4] == era]
            if not xs:
                line += " | %s -" % era[-5:]
                continue
            sp = [run.spr.get(id(x), 0.0) for x in xs]
            n = len(xs)
            v = [sum(x[5] for x in xs) / n - k * sum(sp) / n for k in (0.0, 0.5, 1.0)]
            if v[1] < 0:
                neg += 1
            line += " | %s %s %s %s (%.3f)" % (era[-5:], _f(v[0]), _f(v[1]), _f(v[2]), sum(sp) / n)
        if s != "ALL":
            line += "   -> %s" % ("FLAG" if neg >= 3 else "ok")
        p(line)
    p("")
    p("  money, $10,000, fixed risk 0.25 / 0.25 / 0.50 / 0.10 %, the lab's K4 engine:")
    for k, nm in ((0.0, "spreads x1"), (0.5, "spreads x1.5"), (1.0, "spreads x2")):
        bk = []
        for x, s in base:
            sp = run.spr.get(id(x), 0.0) * k
            y = x[:5] + (x[5] - sp, (x[6] - sp) if x[6] is not None else None) + x[7:]
            bk.append((y, 1.0, s, L.K5_BASE[s]))
        L._k_money(run.rep, nm, bk, 10000.0)
    _yard(run, "W5")


# ---------------------------------------------------------------- W3
def w3(run, base):
    p = run.rep.p
    p("")
    p("=" * 110)
    p("W3. WHERE THE MONEY COMES FROM")
    p("=" * 110)
    p("RULE: KILL a part if, without its best market-year, it is net <= 0 in 3 of 4 eras.")
    p("Shares are of the era's total net R (n/a when the total is <= 0). Best market-year = market x calendar year with")
    p("the most net R inside that era.")
    for s in PARTS:
        p("  %s" % s)
        dead = 0
        for era in ERAS:
            xs = [x for x, q in base if q == s and x[4] == era]
            if not xs:
                p("    %-10s no trades" % era)
                continue
            tot = sum(x[5] for x in xs)
            k = max(1, int(math.ceil(0.05 * len(xs))))
            top = sum(sorted((x[5] for x in xs), reverse=True)[:k])
            mon, my = defaultdict(float), defaultdict(float)
            for x in xs:
                tt = time.gmtime(x[8]["_t_in"])
                mon["%d-%02d" % (tt.tm_year, tt.tm_mon)] += x[5]
                my["%s %d" % (x[0], tt.tm_year)] += x[5]
            bm = max(mon, key=mon.get)
            bmy = max(my, key=my.get)
            wo = tot - my[bmy]
            if wo <= 0:
                dead += 1
            sh = (lambda v: ("%4.0f%%" % (100.0 * v / tot)) if tot > 0 else " n/a")
            p("    %-10s n %4d net %+7.1f R | best 5%% (%3d trades) %s | best month %s %s | best market-year %-15s %s"
              " | without it %+7.1f R" % (era, len(xs), tot, k, sh(top), bm, sh(mon[bm]), bmy, sh(my[bmy]), wo))
        p("    -> %s (net <= 0 without the best market-year in %d of 4 eras)" % ("KILL" if dead >= 3 else "keep", dead))
    # anatomy
    p("")
    p("W3b. TRADE ANATOMY (brk, fast): gross R (no costs) of the open trade after 1h / 4h / 1 day / 3 days of trading")
    p("     bars (a trade that has ended counts at its final R); MFE / MAE so far, in R. Medians.")
    p("PREDICTION: breakout winners show early follow-through (positive by hour 4). If winners only appear on day 3-5,")
    p("            the edge is macro trend riding, not breakout follow-through, and T1 needs rewriting.")
    p("READ AGAINST THE YARDSTICK: on a random walk a winner is also 'positive early' more often than not (a path that")
    p("            ends up is more likely to have been up along the way). Only the gap above the yardstick is follow-through.")
    for s in ("brk", "fast"):
        for grp, eras in (("OLD 2014-21", L.POWER_OLD), ("NEW 2024+", ("B 2024+",)), ("ALL", tuple(ERAS))):
            xs = [x for x, q in base if q == s and x[4] in eras and id(x) in run.anat]
            for kind, sel in (("winners", lambda x: x[5] > 0), ("losers ", lambda x: x[5] <= 0)):
                ys = [x for x in xs if sel(x)]
                if len(ys) < MIN_N:
                    p("  %-4s %-11s %s n %4d (too few)" % (s, grp, kind, len(ys)))
                    continue
                line = "  %-4s %-11s %s n %4d hold %5.1fh |" % (s, grp, kind, len(ys),
                                                              _median([run.anat[id(x)]["hold_h"] for x in ys]))
                for name, _ in ANAT_K:
                    v = [run.anat[id(x)][name] for x in ys]
                    pos = 100.0 * sum(1 for a in v if a[0] > 0) / len(v)
                    line += " %s %3.0f%%+ R %s mfe %4.2f mae %5.2f |" % (name, pos, _f(_median([a[0] for a in v]), 5, 2),
                                                                     _median([a[1] for a in v]), _median([a[2] for a in v]))
                if kind == "winners":
                    sh = []
                    for name, _ in ANAT_K:
                        sh.append(_median([run.anat[id(x)][name][0] / x[7] for x in ys if x[7] and x[7] > 0]))
                    line += " share of final R in place: " + " ".join(
                        "%s %s" % (ANAT_K[i][0], ("%4.0f%%" % (100 * v)) if v is not None else "-") for i, v in enumerate(sh))
                p(line)
    _yard(run, "W3")


# ---------------------------------------------------------------- W1
W1_SPECS = [
    # (name, parts it can move, [(label, spec) low, frozen, high]); spec = dict(det=, brk_exit=, replace=)
    ("edge20 window (days)", ("brk", "fast"), [("15", {"det": ("ew", 15)}), ("20", {}), ("25", {"det": ("ew", 25)})]),
    ("edge20 threshold", ("brk", "fast"), [("0.80", {"det": ("thr", 0.80)}), ("0.85", {}), ("0.90", {"det": ("thr", 0.90)})]),
    ("er10 window (days)", ("brk", "fast"), [("8", {"det": ("erw", 8)}), ("10", {}), ("12", {"det": ("erw", 12)})]),
    ("er10 straightness", ("brk", "fast"), [("0.3", {"det": ("eff", 0.3)}), ("0.4", {}), ("0.5", {"det": ("eff", 0.5)})]),
    ("er10 move (ATR)", ("brk", "fast"), [("1.5", {"det": ("mv", 1.5)}), ("2.0", {}), ("2.5", {"det": ("mv", 2.5)})]),
    ("chandelier length (days)", ("brk",), [("4", {"brk_exit": "5d|L4"}), ("5", {}), ("6", {"brk_exit": "5d|L6"})]),
    ("chandelier distance (N)", ("brk",), [("0.75", {"brk_exit": "5d|D0.75"}), ("1.0", {}),
                                          ("1.25", {"brk_exit": "5d|D1.25"})]),
    ("ORB window (minutes)", ("brk", "fast"), [("22", {"replace": {"orb30": ("orb", 22)}}), ("30", {}),
                                               ("38", {"replace": {"orb30": ("orb", 38)}})]),
    ("inside-day stop (fraction)", ("ins",), [("0.4", {"replace": {"inside": ("ins", 0.4)}}), ("0.5", {}),
                                              ("0.6", {"replace": {"inside": ("ins", 0.6)}})]),
    ("rsi2 entry level", ("dip",), [("7.5", {"replace": {"rsi2": ("rsi", 7.5)}}), ("10", {}),
                                    ("12.5", {"replace": {"rsi2": ("rsi", 12.5)}})]),
    ("dip3 count (down closes)", ("dip",), [("2", {"replace": {"dip3": ("dip3", 2)}}), ("3", {}),
                                           ("4", {"replace": {"dip3": ("dip3", 4)}})]),
    ("long average (days)", ("dip",), [("150", {"replace": {"rsi2": ("sma", 150), "dip3": ("sma", 150)}}), ("200", {}),
                                       ("250", {"replace": {"rsi2": ("sma", 250), "dip3": ("sma", 250)}})]),
]
D_SPECS = [
    ("D1  range lookback = 4 x hold", ("brk",),
     [("fixed 20, hold 4", {"brk_exit": "5d|L4"}), ("derived 16, hold 4", {"brk_exit": "5d|L4", "det": ("ew", 16)})],
     [("fixed 20, hold 6", {"brk_exit": "5d|L6"}), ("derived 24, hold 6", {"brk_exit": "5d|L6", "det": ("ew", 24)})]),
    ("D2  er10 move = 0.632 x sqrt(window) ATR", ("brk", "fast"),
     [("fixed 2.0, window 8", {"det": ("erw", 8)}), ("derived 1.79, window 8", {"det": ("D2", 8)})],
     [("fixed 2.0, window 12", {"det": ("erw", 12)}), ("derived 2.19, window 12", {"det": ("D2", 12)})]),
]


def _variant_book(run, spec, cache):
    key = repr(sorted(spec.items()))
    if key not in cache:
        rows = run.rows_with(spec.get("replace"))
        cache[key] = book_of(rows, run.det[spec.get("det", "base")], spec.get("brk_exit", "5d"))
    return cache[key]


def _cell(book, part, era):
    return pstats([x for x, q in book if q == part and x[4] == era])


def w1(run, base):
    p = run.rep.p
    p("")
    p("=" * 110)
    p("W1. PLATEAU: each frozen number moved about +-25%, one at a time, everything else frozen (books re-deduped)")
    p("=" * 110)
    p("PREDICTION: real mechanisms degrade smoothly; the neighbours keep at least half the edge in most eras.")
    p("RULE: KILL a part if its frozen value is an isolated PEAK: both neighbours keep less than half of the frozen")
    p("      EDGE per trade in 3 of 4 eras (an era counts only where the frozen edge is > 0). Edge = net minus the")
    p("      coin-flip average (the lab's definition). Each cell: edge/trade (n) low | FROZEN | high, then R/yr.")
    p("      The ORB window uses minute bars for 22 / 38 (not whole M15 bars).")
    cache = {}
    for name, parts, vals in W1_SPECS:
        books = [_variant_book(run, v[1], cache) for v in vals]
        p("")
        p("  %s: %s | %s | %s" % (name, vals[0][0], vals[1][0], vals[2][0]))
        for part in parts:
            peaks = 0
            line = "    %-4s" % part
            for era in ERAS:
                c = [_cell(b, part, era) for b in books]
                pk = ""
                if c[1][2] is not None and c[1][2] > 0 and all(x[2] is not None for x in c):
                    if c[0][2] < 0.5 * c[1][2] and c[2][2] < 0.5 * c[1][2]:
                        pk, peaks = " PEAK", peaks + 1
                line += " | %s %s(%d) %s(%d) %s(%d) R/yr %+.0f/%+.0f/%+.0f%s" % (
                    era[-5:], _f(c[0][2]), c[0][0], _f(c[1][2]), c[1][0], _f(c[2][2]), c[2][0],
                    c[0][3] / EY[era], c[1][3] / EY[era], c[2][3] / EY[era], pk)
            p(line + "   -> %s" % ("KILL (isolated peak)" if peaks >= 3 else "plateau / ok (%d peak eras)" % peaks))
    p("")
    p("  DERIVED-RULE CANDIDATES (written 2026-10-09): at the frozen point each reproduces the frozen value exactly, so")
    p("  they are judged in W1's neighbourhood: does tying the number to the mechanism keep MORE of the frozen edge")
    p("  when the neighbouring number moves? Cells: edge/trade (n), fixed rule vs derived rule. A swap is worth")
    p("  proposing only if the derived rule keeps more in most eras on both sides (decision is Ezio's, not automatic).")
    for name, parts, lo, hi in D_SPECS:
        p("  %s" % name)
        for side in (lo, hi):
            bf, bd = _variant_book(run, side[0][1], cache), _variant_book(run, side[1][1], cache)
            for part in parts:
                line = "    %-4s %-26s vs %-26s" % (part, side[0][0], side[1][0])
                wins = 0
                for era in ERAS:
                    cf, cd = _cell(bf, part, era), _cell(bd, part, era)
                    if cf[2] is not None and cd[2] is not None and cd[2] > cf[2]:
                        wins += 1
                    line += " | %s %s(%d) %s(%d)" % (era[-5:], _f(cf[2]), cf[0], _f(cd[2]), cd[0])
                p(line + "   derived better in %d of 4" % wins)
    _yard(run, "W1")


# ---------------------------------------------------------------- W2
def _bins(xs, val, edges, labels):
    out = [[] for _ in labels]
    for x in xs:
        v = val(x)
        if v is None:
            continue
        k = bisect.bisect_right(edges, v)
        out[k].append(x)
    return out


def _dose(run, title, xs, val, edges, labels, pred):
    p = run.rep.p
    p("")
    p("  %s   (prediction: %s)" % (title, pred))
    for grp, eras in (("OLD 2014-21", L.POWER_OLD), ("NEW 2024+", ("B 2024+",)), ("ALL", tuple(ERAS))):
        bs = _bins([x for x in xs if x[4] in eras], val, edges, labels)
        cells, means, pairs = [], [], []
        for k, (lab, b) in enumerate(zip(labels, bs)):
            n, net, edge, tot = pstats(b)
            mu, t = ct(b)
            cells.append("%s %s(%d,%s)" % (lab, _f(edge, 6, 3), n, _t(t).strip()))
            means.append(edge if n >= MIN_N else None)
            pairs += [(k, x) for x in b]
        rho = _spearman(means)
        sl, st = slope_t(pairs)
        p("    %-11s %s" % (grp, "  ".join(cells)))
        p("    %-11s   -> slope %s R per bin step, %s (clustered)   rank corr %s" % (
            "", _f(sl, 6, 3), _t(st), ("%+.2f" % rho) if rho is not None else "-"))


def w2(run):
    p = run.rep.p
    p("")
    p("=" * 110)
    p("W2. DOSE-RESPONSE: does more of the cause give more of the effect?  (ALL candidate trades, before the trend filter")
    p("    and before the one-position rule; edge = net minus the coin-flip average, per trade)")
    p("    Each bin: edge/trade (n, t). t and the slope's t are CLUSTERED by market x month: the candidates overlap")
    p("    heavily (five brk lanes on the same day, multi-day holds), so n hugely overstates the evidence. Judge a")
    p("    response by the slope's t against the yardstick, and by OLD and NEW agreeing -- never by the rank corr alone.")
    p("=" * 110)
    p("READING: flat or non-monotonic = the threshold is not tracking the cause. Not a kill on its own; lowers confidence.")
    rd = run.reads

    def rv(key, signed=True):
        def f(x):
            r = rd.get((x[0], x[8].get("_dk")))
            if not r or key not in r or x[8].get("_d") is None:
                return None
            v = r[key]
            if key == "pos":
                return v if x[8]["_d"] > 0 else 1.0 - v
            return v * x[8]["_d"]
        return f
    brk = [x for x in run.rows if x[0] in BRK_MK and x[1] in L.H_WIDE and x[2] == L.H_WIDE[x[1]] and x[3] == "5d"
           and x[6] is not None]
    fast = [x for x in run.rows if x[0] in BRK_MK and x[3] == "close" and x[6] is not None and
            ((x[1] == "orb30" and x[2] == "range") or (x[1] == "main2" and x[2] == "box"))]
    pos_e = [0.15, 0.30, 0.50, 0.70, 0.85, 0.95]
    pos_l = ["<.15", ".15-.3", ".3-.5", ".5-.7", ".7-.85", ".85-.95", ">=.95"]
    eff_e = [-0.4, -0.2, 0.0, 0.2, 0.4, 0.6]
    eff_l = ["<-.4", "-.4..-.2", "-.2..0", "0..+.2", "+.2..+.4", "+.4..+.6", ">=+.6"]
    mv_e = [-2.0, -1.0, 0.0, 1.0, 2.0, 3.0]
    mv_l = ["<-2", "-2..-1", "-1..0", "0..1", "1..2", "2..3", ">=3"]
    for nm, xs in (("brk (5-day chandelier lanes)", brk), ("fast (orb30 + main2, exit at the close)", fast)):
        p("")
        p("  %s: %d candidate trades" % (nm, len(xs)))
        _dose(run, "yesterday's close in the 20-day range, IN the trade's direction (edge20 fires at >= .85)", xs,
              rv("pos"), pos_e, pos_l, "rises toward the edge")
        _dose(run, "er10 straightness, signed with the trade (er10 needs >= +.4)", xs, rv("eff"), eff_e, eff_l,
              "rises with straighter trends in the trade's direction")
        _dose(run, "10-day move in daily ATRs, signed with the trade (er10 needs >= 2)", xs, rv("mvN"), mv_e, mv_l,
              "rises with bigger moves in the trade's direction")
    ins = [x for x in run.rows if x[0] in BRK_MK and x[1] == "inside" and x[3] == "close" and x[6] is not None]
    p("")
    p("  ins: %d candidate trades" % len(ins))
    _dose(run, "inside day's width in daily ATRs", ins, lambda x: x[8].get("prev_range"), [0.4, 0.6, 0.8, 1.0],
          ["<.4", ".4-.6", ".6-.8", ".8-1", ">=1"], "narrower is better (compression; read the rank corr NEGATIVE)")
    rs = [x for x in run.loose if x[1] == "rsi2" and x[2] == "long" and x[6] is not None]
    dp = [x for x in run.loose if x[1] == "dip3" and x[2] == "long" and x[6] is not None]
    p("")
    p("  dip (US500, Germany 40; LOOSE versions: every signal day, overlapping trades allowed, same exits):")
    p("    rsi2 long with RSI(2) < 30: %d trades; down-close streaks of 2+ above the 200-day average: %d trades" % (
        len(rs), len(dp)))
    _dose(run, "RSI(2) on the signal day (rsi2 enters below 10)", rs, lambda x: x[8].get("_rsi"),
          [2.5, 5.0, 10.0, 20.0], ["<2.5", "2.5-5", "5-10", "10-20", "20-30"],
          "deeper (lower RSI) bounces more, until a crash regime; read the rank corr NEGATIVE")
    _dose(run, "down closes in a row (dip3 enters at 3)", dp, lambda x: x[8].get("_streak"), [2.5, 3.5, 4.5],
          ["2", "3", "4", "5+"], "more down days bounce more")
    _dose(run, "depth of the streak in daily ATRs", dp, lambda x: x[8].get("_depthN"), [0.5, 1.0, 1.5, 2.5],
          ["<.5", ".5-1", "1-1.5", "1.5-2.5", ">=2.5"], "deeper bounces more, until a crash")
    _yard(run, "W2")


# ---------------------------------------------------------------- W4
def w4(run, base):
    p = run.rep.p
    p("")
    p("=" * 110)
    p("W4. PLACEBOS: the edge must fade the way the mechanism says")
    p("=" * 110)
    p("PREDICTIONS: delayed entry -- brk decays slowly over hours (multi-day momentum); fast / ins decay fast (intraday")
    p("             follow-through); dip barely changes over 1 day (a multi-day snap-back).")
    p("             random entry day, same filter, same exits -- the edge must vanish.")
    p("a. DELAYED ENTRY: each book trade re-entered at the bar open 15 min / 1h / 1 trading day after its real fill,")
    p("   same direction, same stop distance, same exit rule (fast / ins: the same day's close for +15m / +1h, the next")
    p("   day's close for +1d; trades with no time left are dropped and counted). Cells: edge/trade (n), net/trade.")
    for s in PARTS:
        for era in ERAS + ["ALL"]:
            real = [x for x, q in base if q == s and (era == "ALL" or x[4] == era)]
            if not real:
                continue
            n, net, edge, _ = pstats(real)
            line = "  %-4s %-10s real %s(%d) %s net %s" % (s, era, _f(edge), n, _t(ct(real)[1]), _f(net))
            for dl in ("15m", "1h", "1d"):
                ys = [y for q, x, y in run.delay[dl] if q == s and (era == "ALL" or x[4] == era) and y is not None]
                drop = sum(1 for q, x, y in run.delay[dl] if q == s and (era == "ALL" or x[4] == era) and y is None)
                n2, net2, edge2, _ = pstats(ys)
                kept = (" kept %4.0f%%" % (100 * edge2 / edge)) if (edge and edge > 0 and edge2 is not None) else ""
                line += " | +%s %s(%d) net %s%s drop %d" % (dl, _f(edge2), n2, _f(net2), kept, drop)
            p(line)
    p("")
    p("b. RANDOM ENTRY DAY: for every book trade, a random day of the same market and era where the SAME filter points")
    p("   (brk: edge20 or er10; fast: its own detector; dip: above the 200-day average), traded in the filter's")
    p("   direction at the same local time (dip: the next open), same stop in daily ATRs, same exits. %d draws." % PLACEBO_DRAWS)
    p("   This asks whether the ENTRY TRIGGER adds anything beyond the filter. Cells: edge/trade (n) net/trade, per draw.")
    for s in ("brk", "fast", "dip"):
        for era in ERAS + ["ALL"]:
            real = [x for x, q in base if q == s and (era == "ALL" or x[4] == era)]
            if not real:
                continue
            n, net, edge, _ = pstats(real)
            line = "  %-4s %-10s real %s(%d) %s net %s" % (s, era, _f(edge), n, _t(ct(real)[1]), _f(net))
            allp = []
            for draw in range(PLACEBO_DRAWS):
                ys = [y for q, x, y in run.rand[draw] if q == s and (era == "ALL" or x[4] == era) and y is not None]
                allp += ys
                n2, net2, edge2, _ = pstats(ys)
                line += " | draw %d %s(%d) net %s" % (draw + 1, _f(edge2), n2, _f(net2))
            n3, net3, edge3, _ = pstats(allp)
            line += " | ALL DRAWS %s %s net %s" % (_f(edge3), _t(ct(allp)[1]), _f(net3))
            p(line)
    p("")
    p("   ins: the inside condition removed -- the same rule (stop orders on yesterday's high / low, stop at its middle,")
    p("   out at the close) on every day that was NOT an inside day (= the lab's pdh2 'mid' with the close exit):")
    for era in ERAS + ["ALL"]:
        real = [x for x, q in base if q == "ins" and (era == "ALL" or x[4] == era)]
        oth = [x for x in run.rows if x[1] == "pdh2" and x[2] == "mid" and x[3] == "close" and x[0] in BRK_MK
               and not x[8].get("_inside") and x[6] is not None and (era == "ALL" or x[4] == era)]
        a, b = pstats(real), pstats(oth)
        p("    %-10s inside days %s(%d) %s net %s   | every other day %s(%d) %s net %s" % (
            era, _f(a[2]), a[0], _t(ct(real)[1]), _f(a[1]), _f(b[2]), b[0], _t(ct(oth)[1]), _f(b[1])))
    _yard(run, "W4")


def _yard(run, sec):
    for line in YARD.get(sec, []):
        run.rep.p(line)


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
        print("usage: python asiabo_why.py [all|cheap] [--db synth/<file>.db]")
        return
    _install()
    t0 = time.time()
    name = "why"
    if synth:
        b = os.path.splitext(os.path.basename(synth))[0]
        for pre in ("synth_", "why_"):
            b = b[len(pre):] if b.startswith(pre) else b
        name = "why_synth_" + b
    if os.environ.get("ASIABO_NO_VISION") or synth:
        # a cousin run ADDS its report to 'claude vision' (no wipe), so the real run's report stays there
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
    if synth:
        rep.p("#" * 100)
        rep.p("SYNTHETIC DATA (a cousin of bars.db, NOT the real market): %s   -- the YARDSTICK for the real run" % synth)
        rep.p("#" * 100)
    rep.p("=" * 110)
    rep.p("THE WHY PHASE (why_phase_plan.md, pre-registered 2026-10-09) on the FROZEN omega book   mode: %s" % mode)
    rep.p("=" * 110)
    rep.p("Sealed exam years %s .. %s and Japan 225: not read. Costs REAL (commission + recorded spread + swap), as in" %
          (A.SEAL_START, A.SEAL_END))
    rep.p("the lab's omega run. Markets: %s (dip: %s). Each era is judged on its own." % (
        ", ".join(MARKETS), ", ".join(DIP_MK)))
    run = Run(rep, mode == "all")
    specs = dict((x["name"], x) for x in A.COLLECT_SYMBOLS)
    try:
        for s in MARKETS:
            if s in specs:
                run.market(s, specs[s])
        report(run)
    except Exception:
        rep.p("")
        rep.p("FAILED:")
        rep.p(traceback.format_exc())
    rep.p("")
    rep.p("runtime %.0fs" % (time.time() - t0))
    rep.save()


if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        if sys.stdin and sys.stdin.isatty():
            input("\nerror above. Press Enter to close.")
