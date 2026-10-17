"""
make_synth.py  --  "cousin" histories of bars.db for robustness tests (2026-10-09).

Question it serves: if a future year has the SAME KIND of properties as our study years but not the same exact
path, do the lanes still find their pattern -- or were they memorizing the past?

What it does (bars.db is only READ, never changed; Japan 225 and the sealed exam years are never read):
  1. RESHUFFLED HISTORY (block bootstrap). Each era (2014-17, 2018-19, 2020-21, 2024+) is cut into trading weeks
     (Sunday 17:00 New York to Sunday 17:00 New York) and rebuilt from random blocks of whole weeks taken from the
     SAME era (block length BMIN..BMAX weeks, from the seed). Every market uses the SAME block schedule, so the
     markets still move together the way they really did. Inside a block everything is real: sessions, opens,
     weekdays, gaps, volatility clusters, trends shorter than the block. Prices are chained so each block starts
     from where the last one ended, keeping the block's own weekend gap. The New York clock is kept exact
     (London's clock can be 1h off for ~3 weeks a year, where US and EU daylight time disagree).
     DAY-SHUFFLE (unit=day): the same, but from single whole DAYS, each drawn at random from the era among days with
     the same weekday. Every day keeps its real shape (opens, sessions, ranges, its own gap) but days no longer
     follow each other: multi-day trends AND multi-day mean reversion are gone (20-day variance ratio ~1).
  2. SHIFTS on top (all optional; 1 / 0 = off):
       vol    scales EVERY move (intraday, daily, gaps, trends) around the start price. Costs do NOT scale with
              it, exactly like a real calmer / wilder year. The trend / noise mix is unchanged.
       drift  adds a slowly wandering trend: each day's drift follows an AR(1) with persistence 0.95 (half-life
              ~14 days), standard deviation = drift x the market's daily volatility. Creates real trends with no
              snap-back (raises the 20-day variance ratio).
       jitter adds independent noise to each M1 bar (in units of that market's typical M1 move). Breaks exact
              levels (yesterday's high to the tick) without changing anything a real pattern should need.
       level  multiplies all prices (and spreads). Our lanes work in ATR units, so this should change nothing.
       spread multiplies the recorded spread.
       persist (2026-10-10, for the engine) bends the path toward MOMENTUM or SNAP-BACK without adding drift:
              log p' = log p + k x (log p - M), M = the average of the previous 20 daily closes (blended smoothly
              through each day). k > 0 = every move overshoots and is then pulled back (snap-back, 20-day variance
              ratio < 1); k < 0 = only part of a move happens at once and the rest follows over the next weeks
              (momentum, ratio > 1). 0 = off. Allowed: -0.9 .. +2. It also scales the size of intraday moves by
              (1 + k); the lanes work in daily ATRs, so read it with the cost-free EDGE, not net R.
  --markets XAUUSD,US500   build only these markets (the engine needs 4 of the 6; a third less work)
  --regime 0.15,0.15 [--spell 20,130]   (2026-10-10, regime engine) every market switches at random between MOMENTUM,
              NEUTRAL and SNAP-BACK spells of 20-130 trading days (independently per market). LEAK-FREE: every day keeps
              its real size, range and intraday shape; only its direction is chosen (kept or mirrored) so that it goes
              WITH the last 20 days' trend with probability 0.5 + d (momentum), 0.5 - d (snap-back) or 0.5 (neutral).
              The true state of every spell is written to the table 'regime' (symbol, t0, t1, state, d; UTC seconds).
  --aging 1   (with --regime; 2026-10-10, ladder test) momentum spells AGE: their strength fades linearly to 0 over
              the first 70% of the spell, and the last 30% REVERSES (snap-back strength d). Labels: 'mom' for the
              first part, 'rev' for the reversal.

--soft MU,SD,L | auto  [--lb 40] [--rev1 auto|0|x]   (v7, 2026-10-11, Phase 2 "synth realism fix")
              REALISTIC regimes, calibrated to the real market (probe_results.md / synth_v7.md). On a dayshuffle base:
              spells of mean length L trading days (geometric, at least 3), each with its OWN signed strength d drawn
              from Normal(MU, SD) (d > 0 momentum, d < 0 snap-back, ~0 neutral: mostly mild, many short). A day whose
              move beyond the drift goes AGAINST the last LB days' de-drifted trend is mirrored with probability 2d in a
              momentum spell; one that goes WITH it, with probability 2|d| in a snap-back spell. Neutral days are left
              alone. DRIFT-PRESERVING: a day is mirrored around its era's drift line (close -> 2 mu - r; inside the day
              each bar x -> 2 mu f - x, f = fraction of the FX day), so the indices keep their upward drift (dip needs
              it). --rev1 auto adds each market's real next-day reversal (lag-1 autocorrelation, strong in the indices):
              a day that continues yesterday's move is mirrored with probability 2 a1 (a1 per market, calibrated).
              SHOCK DAYS keep their real direction: a day whose move or opening gap exceeds 5 x the era's median
              |daily move| is never mirrored (crashes stay crashes; mirroring the 2020 oil days blew XTIUSD up to
              600,000 in the first M1 test). The drift line is the mean of the normal days.
              'auto' = MU -0.09, SD 0.12, L 5, LB 40: calibrated on the daily bars of 6 REAL M1 dayshuffle bases x 2
              draws, checked on 3 held-out bases (a first calibration on a home-made daily shuffle ran ~0.06 too
              trendy in er40 once generated at M1 level).
              The spell table 'regime' gets state mom / snap / none (|d| < 0.02) and a = d.
              After generating, the REALISM GATE runs (see 'gate'); a world outside it FAILS the run (exit code 3).
  gate <db>   the realism gate: 8 statistics of the FX-day bars (definitions = asiabo_probe.py), synth vs bars.db,
              with tolerances fixed 2026-10-11 = 2 x the seed spread of 12 calibrated v7 worlds. FAIL if any of truth
              share / er20 precision / er40 precision / ac1 is outside, or 2+ of the others. Report -> reports/synth_gate_<time>/ and
              ADDED to claude vision.

--bsnap Q [--lb 40] [--bmom 0]   (v8, 2026-10-12, preset real8) on the WEEK-BLOCK base (blocks of 2-6 weeks): a
              WHOLE block whose move beyond the drift goes WITH the new path's de-drifted 40-day trend is mirrored with
              probability Q (around the era's drift line, as v7); BMOM = the same for blocks going against it.
              Everything inside a block stays real: volatility clusters, next-day reversals, down-streaks and bounces
              (all lost in v7's single-day base). Blocks holding a shock day keep their direction. Q = 1.0, calibrated on
              6 real M1 block bases x 2, held out on 3 (synth_v8.md). Spell table: one row per block, mirrored / kept.

PRESETS (fixed before any synthetic result was seen):
  identity   no reshuffle, no shift      -> must reproduce the real results (sanity check of the generator)
  shuffle    reshuffled history only (blocks of 2-6 weeks)
  dayshuffle whole days reshuffled (same weekday): no multi-day structure at all
  cosmetic   shuffle + level 1.7 + jitter 0.3            (should NOT matter)
  vol_up     shuffle + vol 1.3          vol_down   shuffle + vol 0.75
  trend_up   shuffle + drift 0.15       trend_up2  shuffle + drift 0.30
  costly     shuffle + spread 1.5
  real7      (v7) dayshuffle + --soft auto --rev1 auto (superseded by real8: fails the v8 gate on volatility and
             dip setups by design)
  real8      (v8) week blocks 2-6 + --bsnap 1.0: the REALISTIC world (gate must pass)
  longblock  shuffle with blocks of 8-26 weeks (added 2026-10-09 after the first batch: tests whether profit needs
             trends LONGER than the 2-6 week blocks)
  (2026-10-09: the first 'trend0 / trend_half' knob subtracted the 20-day average and turned the market
  MEAN-REVERTING (variance ratio 0.2) instead of trendless, so it was replaced by dayshuffle before any lane ran.)

Usage:
  python make_synth.py                                   (double-click) = gen shuffle seed 1, then check it
  python make_synth.py gen --preset shuffle --seed 3 [--vol 1.3 --drift 0.15 --jitter 0.3 --level 1.7 --spread 1.5
                           --block 2,6 --unit week|day --out path]
  python make_synth.py check synth/synth_shuffle_s3.db    compare its statistics with bars.db, per market and era
  python make_synth.py cache                              build the source cache (synth/cache, ~1 GB, once; 'gen' uses
                                                          it automatically when it is up to date)
Output: <ROOT>/synth/synth_<preset>_s<seed>.db  (same schema as bars.db plus a synth_meta table; ~1.5 GB, delete
when done). The check report goes to reports/synth_<time>/ and is ADDED to 'claude vision' (no wipe).
Run the lab on it:  python asiabo_lab.py power --db synth/synth_shuffle_s3.db
"""
import os, sys, math, time, datetime, sqlite3, random, bisect, zlib, shutil, json, mmap
from array import array
from collections import defaultdict

import asiabo_offline as A

PRESETS = {
    "identity": {"shuffle": False},
    "shuffle": {},
    "dayshuffle": {"unit": "day"},
    "cosmetic": {"level": 1.7, "jitter": 0.3},
    "vol_up": {"vol": 1.3},
    "vol_down": {"vol": 0.75},
    "trend_up": {"drift": 0.15},
    "trend_up2": {"drift": 0.30},
    "costly": {"spread": 1.5},
    "longblock": {"bmin": 8, "bmax": 26},
    "real7": {"unit": "day", "soft": "auto", "rev1": "auto"},
    "real8": {"bsnap": "1.0"},
}
# v7 keys live OUTSIDE DEFAULTS, so a v4-v6 run writes exactly the same synth_meta rows as before
V7_DEFAULTS = {"soft": "", "lb": 40, "rev1": ""}
V8_DEFAULTS = {"bsnap": "", "lb": 40, "bmom": 0.0}
SOFT_AUTO = (-0.09, 0.12, 5)
# next-day reversal per market (normal days only), calibrated 2026-10-11 on M1 bases so each market's lag-1
# autocorrelation matches bars.db
A1_V7 = {"XAUUSD": 0.000, "US500": 0.448, "EURUSD": 0.034, "USDJPY": 0.073, "XTIUSD": 0.000, "GERMANY40": 0.237}
SHOCK_V7 = 5.0      # a day moving (or gapping) more than 5 x the era's median |daily move| keeps its real direction
DEFAULTS = {"shuffle": True, "unit": "week", "vol": 1.0, "drift": 0.0, "jitter": 0.0, "level": 1.0, "spread": 1.0,
            "bmin": 2, "bmax": 6, "persist": 0.0, "markets": "", "regime": "", "spell": "20,130", "aging": 0.0}
DRIFT_PHI = 0.95
ERA_CUTS = ["2018-01-01", "2020-01-01", A.SEAL_START]      # + [SEAL_END, end of data] for the last era
WEEK = 7 * 86400


# ------------------------------------------------------------------ calendar
def _us_dst(d):
    mar1 = datetime.date(d.year, 3, 1)
    start = mar1 + datetime.timedelta(days=(6 - mar1.weekday()) % 7 + 7)
    nov1 = datetime.date(d.year, 11, 1)
    end = nov1 + datetime.timedelta(days=(6 - nov1.weekday()) % 7)
    return start <= d < end


def _anchor_of_sunday(d):
    """UTC epoch of date d (any day), 17:00 New York."""
    h = 21 if _us_dst(d) else 22
    return calendar_epoch(d) + h * 3600


def calendar_epoch(d):
    return datetime.datetime(d.year, d.month, d.day, tzinfo=datetime.timezone.utc).timestamp()


def day_anchors(t0, t1):
    """Every 17:00-NY anchor (one per calendar day) from the day before t0 to the first one after t1. The trading day
    that starts at an anchor is the NEXT calendar day (its weekday is returned with it)."""
    d = datetime.datetime.fromtimestamp(t0, datetime.timezone.utc).date() - datetime.timedelta(days=2)
    out = []
    while True:
        a = _anchor_of_sunday(d)
        out.append((a, (d + datetime.timedelta(days=1)).weekday()))
        if a > t1:
            break
        d += datetime.timedelta(days=1)
    return out


def week_anchors(t0, t1):
    """Every Sunday-17:00-NY anchor from the one at or before t0 to the first one after t1."""
    d = datetime.datetime.fromtimestamp(t0, datetime.timezone.utc).date()
    d -= datetime.timedelta(days=(d.weekday() + 1) % 7)          # back to Sunday
    d -= datetime.timedelta(days=7)
    out = []
    while True:
        a = _anchor_of_sunday(d)
        out.append(a)
        if a > t1:
            break
        d += datetime.timedelta(days=7)
    return out


# ------------------------------------------------------------------ data
def _symbols(con):
    """{spec name: db symbol} for the house markets only (Japan 225 and anything else is never read)."""
    have = [r[0] for r in con.execute("select distinct symbol from bars_m1")]
    out = {}
    for spec in A.COLLECT_SYMBOLS:
        if spec["name"] not in A.HOUSE_SYMBOLS:
            continue
        m = set(x.upper() for x in spec["match"])
        for s in have:
            if s.upper().replace(" ", "") in m:
                out[spec["name"]] = s
                break
    return out


def _load(con, dbsym):
    """All bars of one symbol OUTSIDE the sealed years, in true UTC. -> dict of arrays."""
    shift = A.DB_UTC_OFFSET_HOURS * 3600.0
    s0, s1 = A.epoch_of(A.SEAL_START) + shift, A.epoch_of(A.SEAL_END) + shift
    T, O, H, L, C, V, S = array("d"), array("d"), array("d"), array("d"), array("d"), array("d"), array("d")
    q = ("select ts, open, high, low, close, volume, spread_avg from bars_m1 where symbol=? and (ts < ? or ts >= ?) "
         "order by ts")
    for ts, o, h, l, c, v, sp in con.execute(q, (dbsym, int(s0), int(s1))):
        t = A.to_epoch(ts) - shift
        if not (A.epoch_of(A.SEAL_START) <= t < A.epoch_of(A.SEAL_END)):
            T.append(t); O.append(o); H.append(h); L.append(l); C.append(c)
            V.append(v if v is not None else 0.0)
            S.append(sp if sp is not None else float("nan"))
    return {"T": T, "O": O, "H": H, "L": L, "C": C, "V": V, "S": S}


def _eras(t_first, t_last):
    cuts = [A.epoch_of(x) for x in ERA_CUTS]
    return [(t_first, cuts[0]), (cuts[0], cuts[1]), (cuts[1], cuts[2]), (A.epoch_of(A.SEAL_END), t_last + 1)]


# ------------------------------------------------------------------ source cache (2026-10-10)
# Reading 18M bars out of bars.db took ~6-9 min of every job. The cache stores them ONCE as plain binary doubles
# (synth/cache/, ~1 GB, rewritten only when bars.db changes) and every job opens it MEMORY-MAPPED, read-only: Windows
# keeps only the pages in use in RAM, can drop them under pressure without writing anything (no swap, no SSD wear),
# and parallel jobs share one copy. Reads do not wear an SSD; only the one-time write does.
CACHE_FIELDS = ("T", "O", "H", "L", "C", "V", "S")


def _cache_dir():
    return os.path.join(A.ROOT, "synth", "cache")


def _cache_key(src):
    st = os.stat(src)
    return {"db": os.path.abspath(src), "size": st.st_size, "mtime": int(st.st_mtime), "seal": [A.SEAL_START, A.SEAL_END],
            "offset": A.DB_UTC_OFFSET_HOURS, "version": 1}


def cache_valid(src):
    try:
        with open(os.path.join(_cache_dir(), "meta.json")) as f:
            return json.load(f).get("key") == _cache_key(src)
    except (OSError, ValueError):
        return False


def build_cache(log=print):
    src = A.find_db()
    if cache_valid(src):
        log("source cache is up to date (%s)" % _cache_dir())
        return
    d = _cache_dir()
    os.makedirs(d, exist_ok=True)
    con = sqlite3.connect(src)
    syms = _symbols(con)
    shift = A.DB_UTC_OFFSET_HOURS * 3600.0
    has_gaps = bool([r for r in con.execute("select name from sqlite_master where type='table' and name='gaps'")])
    markets = {}
    for name, dbs in sorted(syms.items()):
        t0 = time.time()
        data = _load(con, dbs)
        gaps = []
        if has_gaps:
            for a, b, mins, kind, note in con.execute(
                    "select after_bar, next_bar, missing_minutes, kind, note from gaps where symbol=?", (dbs,)):
                try:
                    gaps.append([A.to_epoch(a) - shift, A.to_epoch(b) - shift, mins, kind, note])
                except (ValueError, TypeError):
                    continue
        tmp = os.path.join(d, name + ".bin.tmp")
        with open(tmp, "wb") as f:
            for k in CACHE_FIELDS:
                data[k].tofile(f)
        os.replace(tmp, os.path.join(d, name + ".bin"))
        markets[name] = {"db_symbol": dbs, "n": len(data["T"]), "gaps": gaps}
        log("  cached %-10s %9d bars  (%.0fs)" % (name, len(data["T"]), time.time() - t0))
        del data
    con.close()
    tmp = os.path.join(d, "meta.json.tmp")
    with open(tmp, "w") as f:
        json.dump({"key": _cache_key(src), "markets": markets}, f)
    os.replace(tmp, os.path.join(d, "meta.json"))
    log("source cache written to %s" % d)


class _Mapped(object):
    """One market's cached bars, memory-mapped read-only. Fields are memoryviews of doubles (no copy)."""

    def __init__(self, name, n):
        self.f = open(os.path.join(_cache_dir(), name + ".bin"), "rb")
        self.mm = mmap.mmap(self.f.fileno(), 0, access=mmap.ACCESS_READ)
        mv = memoryview(self.mm).cast("d")
        self.mv = mv
        self.d = dict((k, mv[i * n:(i + 1) * n]) for i, k in enumerate(CACHE_FIELDS))

    def close(self):
        for v in self.d.values():
            v.release()
        self.mv.release()
        self.mm.close()
        self.f.close()


# ------------------------------------------------------------------ generator
def schedule(anchors_n, cfg, rnd, weekdays=None):
    """dest unit j -> source unit index (same era). Shared by every market. Day units: same weekday, blocks of 1."""
    if not cfg["shuffle"]:
        return list(range(anchors_n))
    if weekdays is not None:
        by = defaultdict(list)
        for j, wd in enumerate(weekdays):
            by[wd].append(j)
        return [rnd.choice(by[wd]) for wd in weekdays]
    out = []
    while len(out) < anchors_n:
        L = rnd.randint(cfg["bmin"], cfg["bmax"])
        L = min(L, anchors_n)
        s = rnd.randint(0, anchors_n - L)
        out.extend(range(s, s + L))
    return out[:anchors_n]


def _transform(T, O, H, L, C, S, cfg, rnd):
    """Apply vol / drift / jitter / level / spread to one chained era series (in place).
    log p' = log p0 + vol x (log p - log p0) + D(t) + e ;  then x level.  Spread scales with the price change only."""
    n = len(T)
    if n == 0:
        return
    v, dr, jit, lev, spr = cfg["vol"], cfg["drift"], cfg["jitter"], cfg["level"], cfg["spread"]
    if cfg.get("persist"):
        _persist_pass = True
    else:
        _persist_pass = False
    if v == 1.0 and dr == 0.0 and jit == 0.0:
        if lev != 1.0 or spr != 1.0:
            for i in range(n):
                O[i] *= lev; H[i] *= lev; L[i] *= lev; C[i] *= lev
                if S[i] == S[i]:
                    S[i] *= lev * spr
        if _persist_pass:
            _persist(T, O, H, L, C, S, cfg["persist"])
        return
    x0 = math.log(C[0])
    # daily closes (for the drift path and the daily volatility)
    day_t, day_x = [], []
    cur = None
    for i in range(n):
        d = int(T[i] // 86400)
        if d != cur:
            day_t.append(T[i]); day_x.append(math.log(C[i])); cur = d
        else:
            day_t[-1], day_x[-1] = T[i], math.log(C[i])
    nd = len(day_x)
    Dd = [0.0] * nd
    if dr and nd > 2:
        r = [day_x[j] - day_x[j - 1] for j in range(1, nd)]
        mu = sum(r) / len(r)
        sd = math.sqrt(sum((y - mu) ** 2 for y in r) / (len(r) - 1)) * v
        m, acc = 0.0, 0.0
        k = math.sqrt(1.0 - DRIFT_PHI ** 2)
        for j in range(1, nd):
            m = DRIFT_PHI * m + k * rnd.gauss(0.0, dr * sd)
            acc += m
            Dd[j] = acc
    sc = 0.0
    if jit:
        diffs = sorted(abs(math.log(C[i] / C[i - 1])) for i in range(1, n, 7) if C[i - 1] > 0 and C[i] > 0)
        sc = diffs[len(diffs) // 2] * v if diffs else 0.0
    p = 0
    for i in range(n):
        t = T[i]
        Dt = 0.0
        if dr:
            while p + 1 < nd and day_t[p + 1] <= t:
                p += 1
            if t <= day_t[0]:
                Dt = Dd[0]
            elif p + 1 < nd and day_t[p + 1] > day_t[p]:
                w = (t - day_t[p]) / (day_t[p + 1] - day_t[p])
                Dt = Dd[p] + w * (Dd[p + 1] - Dd[p])
            else:
                Dt = Dd[min(p, nd - 1)]
        base = x0 - v * x0 + Dt + (rnd.gauss(0.0, jit * sc) if jit else 0.0)
        c_old = C[i]
        O[i] = lev * math.exp(base + v * math.log(O[i]))
        H[i] = lev * math.exp(base + v * math.log(H[i]))
        L[i] = lev * math.exp(base + v * math.log(L[i]))
        C[i] = lev * math.exp(base + v * math.log(c_old))
        if S[i] == S[i]:
            S[i] *= (C[i] / c_old) * spr
    if _persist_pass:
        _persist(T, O, H, L, C, S, cfg["persist"])


def _persist(T, O, H, L, C, S, k):
    """The 'persist' dial (see the top): log p' = log p + k (log p - M(t)). M(t) = average of the previous 20 daily
    closes, blended linearly through each day from that day's value to the next day's, so no artificial jumps appear
    at day boundaries. Monotone for k > -1, so highs stay highs. The spread keeps its size in bp."""
    n = len(T)
    if n == 0 or not k:
        return
    if not (-0.9 <= k <= 2.0):
        raise ValueError("persist must be between -0.9 and +2 (got %s)" % k)
    first, day_x = [], []                       # first bar index and closing log price of each UTC day
    cur = None
    for i in range(n):
        d = int(T[i] // 86400)
        if d != cur:
            first.append(i); day_x.append(math.log(C[i])); cur = d
        else:
            day_x[-1] = math.log(C[i])
    nd = len(day_x)
    M = [0.0] * (nd + 1)                         # M[j] = the anchor in force at the START of day j
    acc = 0.0
    for j in range(nd + 1):
        if j == 0:
            M[0] = math.log(O[0])
            continue
        acc += day_x[j - 1]
        if j > 20:
            acc -= day_x[j - 21]
        M[j] = acc / min(j, 20)
    first.append(n)
    lg, ex = math.log, math.exp
    for j in range(nd):
        i0, i1 = first[j], first[j + 1]
        t0, span = T[i0], (T[i1 - 1] - T[i0]) or 1.0
        m0, dm = M[j], M[j + 1] - M[j]
        for i in range(i0, i1):
            m = m0 + dm * ((T[i] - t0) / span)
            c_old = C[i]
            O[i] = ex(lg(O[i]) * (1.0 + k) - k * m)
            H[i] = ex(lg(H[i]) * (1.0 + k) - k * m)
            L[i] = ex(lg(L[i]) * (1.0 + k) - k * m)
            C[i] = ex(lg(c_old) * (1.0 + k) - k * m)
            if S[i] == S[i]:
                S[i] *= C[i] / c_old


REGIME_LOOKBACK = 20
_FXD = {}


def _fx_day(t):
    """FX day of UTC time t: days end at 17:00 New York (21:00 UTC in US summer time, 22:00 UTC otherwise)."""
    dd = int(t // 86400)
    bh = _FXD.get(dd)
    if bh is None:
        bh = 21 if _us_dst(datetime.date(1970, 1, 1) + datetime.timedelta(days=dd)) else 22
        _FXD[dd] = bh
    return dd + (1 if (t - dd * 86400) >= bh * 3600 else 0)


def _regime(T, O, H, L, C, S, cfg, rnd, carry=0.0, stats=None):
    """The switching momentum / neutral / snap-back dial (see the top), LEAK-FREE BY CONSTRUCTION: every day keeps its
    real path size, range and intraday shape; only its DIRECTION is chosen. Each day is kept or MIRRORED (all its moves,
    overnight gap included, reflected around the previous close) so that it goes WITH the trend of the last 20 days of
    the new path with probability 0.5 + d (momentum), 0.5 - d (snap-back) or 0.5 (neutral). The base drift is removed in
    every state (mirroring is symmetric), so the states differ ONLY in direction persistence. One chained era series,
    in place. carry = (new - original) log level at the end of the previous era, so eras join without a seam (the base
    generator restarts each era at the source price). Opening gaps above 6x the typical daily move are closed (a
    dayshuffle artefact: a source day from another daylight-saving period can join to a stale price).
    -> (spells [(t0, t1, state, d)] in UTC seconds, carry for the next era)."""
    n = len(T)
    if n == 0:
        return [], carry
    dm, ds = [float(x) for x in str(cfg["regime"]).split(",")]
    lo, hi = [int(x) for x in str(cfg.get("spell") or "20,130").split(",")]
    if not (0 <= dm <= 0.5 and 0 <= ds <= 0.5):
        raise ValueError("regime strengths must be 0 .. 0.5 (probability shifts)")
    first, dayc = [], []
    cur = None
    for i in range(n):
        d = _fx_day(T[i])                           # the FX day (17:00 New York), the day the lanes read
        if d != cur:
            first.append(i); dayc.append(math.log(C[i])); cur = d
        else:
            dayc[-1] = math.log(C[i])
    nd = len(dayc)
    first.append(n)
    p_of, spells = [0.5] * nd, []
    j = 0
    aging = bool(cfg.get("aging"))
    while j < nd:
        ln = rnd.randint(lo, hi)
        st = rnd.choice(("mom", "none", "snap"))
        dd = {"mom": dm, "none": 0.0, "snap": -ds}[st]
        e = min(nd, j + ln)
        if aging and st == "mom":
            mid = j + max(1, int(round(0.7 * (e - j))))
            for q in range(j, min(mid, e)):
                p_of[q] = 0.5 + dm * (1.0 - (q - j) / float(max(1, mid - j)))
            for q in range(mid, e):
                p_of[q] = 0.5 - dm
            spells.append((T[first[j]], T[first[min(mid, e)] - 1] + 60.0, "mom", dm))
            if mid < e:
                spells.append((T[first[mid]], T[first[e] - 1] + 60.0, "rev", -dm))
        else:
            for q in range(j, e):
                p_of[q] = 0.5 + dd
            spells.append((T[first[j]], T[first[e] - 1] + 60.0, st, dd))
        j = e
    lg, ex = math.log, math.exp
    Lb = REGIME_LOOKBACK
    rr = sorted(abs(dayc[j] - dayc[j - 1]) for j in range(1, nd))
    gap_cap = 6.0 * (rr[len(rr) // 2] if rr else 0.0)
    X = [0.0] * nd                                  # new closing log price of every day
    prev_orig = lg(O[0])                            # original previous close (day 0: its own open)
    prev_new = prev_orig + carry
    for j in range(nd):
        g = lg(O[first[j]]) - prev_orig             # this day's opening gap
        if gap_cap > 0 and abs(g) > gap_cap and j > 0:
            prev_orig += g                          # treat the artificial gap as if the day opened flat
            if stats is not None:
                stats["gaps_closed"] = stats.get("gaps_closed", 0) + 1
        r = dayc[j] - prev_orig
        if j - 1 - Lb >= 0:
            tr = X[j - 1] - X[j - 1 - Lb]
            want = 1 if tr > 0 else (-1 if tr < 0 else 0)
        else:
            want = 0
        if want == 0 or r == 0:
            m = 1 if rnd.random() < 0.5 else -1
        else:
            agree = rnd.random() < p_of[j]
            m = 1 if ((r > 0) == (want > 0)) == agree else -1
        i0, i1 = first[j], first[j + 1]
        for i in range(i0, i1):
            o, h, l, c = lg(O[i]) - prev_orig, lg(H[i]) - prev_orig, lg(L[i]) - prev_orig, lg(C[i]) - prev_orig
            c_old = C[i]
            if m < 0:
                o, h, l, c = -o, -l, -h, -c
            O[i], H[i], L[i], C[i] = ex(prev_new + o), ex(prev_new + h), ex(prev_new + l), ex(prev_new + c)
            if S[i] == S[i]:
                S[i] *= C[i] / c_old
        X[j] = prev_new + m * r
        prev_new = X[j]
        prev_orig = dayc[j]
    return spells, prev_new - dayc[-1]


def _soft_params(cfg):
    v = str(cfg.get("soft"))
    mu, sd, L = SOFT_AUTO if v == "auto" else [float(x) for x in v.split(",")]
    return float(mu), float(sd), float(L), int(cfg.get("lb") or 40)


def _regime7(T, O, H, L, C, S, cfg, rnd, name, carry=0.0, stats=None):
    """v7 soft regimes (see the top). FX days and the carry between eras as in _regime; NO gap closing (shock days
    instead); its own spell model, the drift-preserving mirror and the next-day reversal. -> (spells, carry)."""
    n = len(T)
    if n == 0:
        return [], carry
    mu_s, sd_s, Lm, lb = _soft_params(cfg)
    r1 = cfg.get("rev1") or ""
    a1 = A1_V7.get(name, 0.0) if r1 == "auto" else (float(r1) if r1 else 0.0)
    first, dayc = [], []
    cur = None
    for i in range(n):
        d = _fx_day(T[i])
        if d != cur:
            first.append(i); dayc.append(math.log(C[i])); cur = d
        else:
            dayc[-1] = math.log(C[i])
    nd = len(dayc)
    first.append(n)
    lg, ex = math.log, math.exp
    # pass 1: each day's move from the previous close and the era's drift (normal days only)
    base, R_, G_ = [0.0] * nd, [0.0] * nd, [0.0] * nd   # base = the previous-close reference of each day
    prev_orig = lg(O[0])
    for j in range(nd):
        # v7 keeps every opening gap as the dayshuffle base has it (v6 closed gaps > 6x the median move, which
        # deleted oil's contract-roll gaps and made XTIUSD trend up: first M1 test, 2026-10-11). Big-gap days are
        # shock days instead: they keep their real direction.
        base[j] = prev_orig
        R_[j] = dayc[j] - prev_orig
        G_[j] = lg(O[first[j]]) - prev_orig
        prev_orig = dayc[j]
    srt = sorted(abs(v) for v in R_)
    cut = SHOCK_V7 * srt[len(srt) // 2]
    shock = [abs(R_[j]) > cut or abs(G_[j]) > cut for j in range(nd)]
    nrm = [R_[j] for j in range(nd) if not shock[j]]
    md = sum(nrm) / len(nrm) if nrm else 0.0
    if stats is not None:
        stats["shock_days"] = stats.get("shock_days", 0) + sum(shock)
    # the spells
    dd, spells = [0.0] * nd, []
    j = 0
    while j < nd:
        ln = 3 + int(rnd.expovariate(1.0 / max(1e-9, Lm - 3.0)))
        ln = min(ln, 250)
        d = max(-0.45, min(0.45, rnd.gauss(mu_s, sd_s)))
        e = min(nd, j + ln)
        for q in range(j, e):
            dd[q] = d
        spells.append((T[first[j]], T[first[e] - 1] + 60.0, "mom" if d >= 0.02 else ("snap" if d <= -0.02 else "none"), d))
        j = e
    # pass 2: the mirror decisions on the new (de-drifted) path, then the bars
    X = [0.0] * nd
    x, prev = 0.0, 0.0
    prev_new = lg(O[0]) + carry
    for j in range(nd):
        dev = R_[j] - md
        m = 1
        if not shock[j] and j > lb and dev != 0:
            tr = X[j - 1] - X[j - 1 - lb]
            if tr != 0:
                agree = (dev > 0) == (tr > 0)
                d = dd[j]
                if d > 0 and not agree and rnd.random() < 2 * d:
                    m = -1
                elif d < 0 and agree and rnd.random() < -2 * d:
                    m = -1
        if a1 and not shock[j] and prev != 0 and dev != 0:
            if ((m * dev > 0) == (prev > 0)) and rnd.random() < 2 * a1:
                m = -m
        i0, i1 = first[j], first[j + 1]
        b0 = base[j]
        t0, span = T[i0], (T[i1 - 1] + 60.0 - T[i0]) or 60.0
        for i in range(i0, i1):
            o, h, l, c = lg(O[i]) - b0, lg(H[i]) - b0, lg(L[i]) - b0, lg(C[i]) - b0
            c_old = C[i]
            if m < 0:
                f = (T[i] + 60.0 - t0) / span
                w = 2.0 * md * f
                o, h, l, c = w - o, w - l, w - h, w - c
            O[i], H[i], L[i], C[i] = ex(prev_new + o), ex(prev_new + h), ex(prev_new + l), ex(prev_new + c)
            if S[i] == S[i]:
                S[i] *= C[i] / c_old
        newr = R_[j] if m > 0 else 2.0 * md - R_[j]
        x += newr - md
        X[j] = x
        prev = newr - md
        prev_new += newr
    return spells, prev_new - dayc[-1]


def _blocksnap(T, O, H, L, C, S, cfg, rnd, bstarts, carry=0.0, stats=None):
    """v8 (see the top): on a week-block base, a WHOLE block whose move beyond the drift goes WITH the new path's
    de-drifted trend of the last LB days is mirrored (around the era's drift line, as v7) with probability BSNAP; one
    going against it with probability BMOM. Everything inside a block stays real (volatility clusters, next-day
    reversals, down-streaks and bounces). Blocks holding a shock day keep their direction. -> (spells, carry)."""
    n = len(T)
    if n == 0:
        return [], carry
    q, qm, lb = float(cfg.get("bsnap") or 0.0), float(cfg.get("bmom") or 0.0), int(cfg.get("lb") or 40)
    first, dayc = [], []
    cur = None
    for i in range(n):
        d = _fx_day(T[i])
        if d != cur:
            first.append(i); dayc.append(math.log(C[i])); cur = d
        else:
            dayc[-1] = math.log(C[i])
    nd = len(dayc)
    first.append(n)
    lg, ex = math.log, math.exp
    base, R_, G_ = [0.0] * nd, [0.0] * nd, [0.0] * nd
    prev_orig = lg(O[0])
    for j in range(nd):
        base[j] = prev_orig
        R_[j] = dayc[j] - prev_orig
        G_[j] = lg(O[first[j]]) - prev_orig
        prev_orig = dayc[j]
    srt = sorted(abs(v) for v in R_)
    cut = SHOCK_V7 * srt[len(srt) // 2]
    shock = [abs(R_[j]) > cut or abs(G_[j]) > cut for j in range(nd)]
    nrm = [R_[j] for j in range(nd) if not shock[j]]
    md = sum(nrm) / len(nrm) if nrm else 0.0
    bid = [bisect.bisect_right(bstarts, T[first[j]]) for j in range(nd)]
    flip = [1] * nd
    X = [0.0] * nd
    x = 0.0
    spells = []
    j = 0
    while j < nd:
        e = j
        while e + 1 < nd and bid[e + 1] == bid[j]:
            e += 1
        dev = sum(R_[k] - md for k in range(j, e + 1))
        f = 1
        if j - 1 - lb >= 0 and dev != 0 and not any(shock[j:e + 1]):
            tr = X[j - 1] - X[j - 1 - lb]
            if tr != 0:
                agree = (dev > 0) == (tr > 0)
                if (agree and rnd.random() < q) or (not agree and rnd.random() < qm):
                    f = -1
        for k in range(j, e + 1):
            flip[k] = f
            x += f * (R_[k] - md)
            X[k] = x
        spells.append((T[first[j]], T[first[e + 1] - 1] + 60.0, "mirrored" if f < 0 else "kept", float(f)))
        if stats is not None:
            stats["blocks"] = stats.get("blocks", 0) + 1
            stats["mirrored"] = stats.get("mirrored", 0) + (f < 0)
        j = e + 1
    if stats is not None:
        stats["shock_days"] = stats.get("shock_days", 0) + sum(shock)
    prev_new = lg(O[0]) + carry
    for j in range(nd):
        i0, i1 = first[j], first[j + 1]
        b0 = base[j]
        t0, span = T[i0], (T[i1 - 1] + 60.0 - T[i0]) or 60.0
        m = flip[j]
        for i in range(i0, i1):
            o, h, l, c = lg(O[i]) - b0, lg(H[i]) - b0, lg(L[i]) - b0, lg(C[i]) - b0
            c_old = C[i]
            if m < 0:
                w = 2.0 * md * ((T[i] + 60.0 - t0) / span)
                o, h, l, c = w - o, w - l, w - h, w - c
            O[i], H[i], L[i], C[i] = ex(prev_new + o), ex(prev_new + h), ex(prev_new + l), ex(prev_new + c)
            if S[i] == S[i]:
                S[i] *= C[i] / c_old
        prev_new += R_[j] if m > 0 else 2.0 * md - R_[j]
    return spells, prev_new - dayc[-1]


def _day_str_cache():
    """time_utc strings without a strftime per bar (the writer's slowest line): one date string per day."""
    cache = {}

    def f(t):
        it = int(t)
        d = it // 86400
        s = cache.get(d)
        if s is None:
            s = time.strftime("%Y-%m-%d ", time.gmtime(d * 86400))
            cache[d] = s
        r = it - d * 86400
        return "%s%02d:%02d" % (s, r // 3600, (r % 3600) // 60)
    return f


def generate(cfg, out_path, log=print):
    """2026-10-09 v3: ONE market in memory at a time (the all-at-once version ran a PC out of memory late in a
    batch), and prices are re-joined ONLY where two blocks meet (v2 also re-joined after any >8-day data hole inside
    an unbroken run of weeks, so 'identity' did not reproduce 2014-19 exactly)."""
    src = A.find_db()
    if not src:
        raise RuntimeError("bars.db not found under %s" % A.ROOT)
    if os.path.abspath(out_path) == os.path.abspath(src):
        raise RuntimeError("refusing to overwrite bars.db")
    con = sqlite3.connect(src)
    syms = _symbols(con)
    if cfg.get("markets"):
        want = set(x.strip().upper() for x in str(cfg["markets"]).split(",") if x.strip())
        syms = dict((k, v) for k, v in syms.items() if k.upper() in want)
        if not syms:
            raise RuntimeError("none of the markets %s is in bars.db" % cfg["markets"])
    log("markets: %s" % ", ".join("%s (%s)" % kv for kv in sorted(syms.items())))
    shift = A.DB_UTC_OFFSET_HOURS * 3600.0
    s0, s1 = A.epoch_of(A.SEAL_START) + shift, A.epoch_of(A.SEAL_END) + shift
    firsts, lasts = [], []
    for name, dbs in syms.items():          # the data span, without loading any bars
        r = con.execute("select min(ts), max(ts) from bars_m1 where symbol=? and (ts < ? or ts >= ?)",
                        (dbs, int(s0), int(s1))).fetchone()
        if r and r[0] is not None:
            firsts.append(A.to_epoch(r[0]) - shift)
            lasts.append(A.to_epoch(r[1]) - shift)
    t_first, t_last = min(firsts), max(lasts)
    has_gaps = bool([r for r in con.execute("select name from sqlite_master where type='table' and name='gaps'")])
    eras = _eras(t_first, t_last)
    rnd = random.Random(cfg["seed"])
    unit_len = 86400 if cfg["unit"] == "day" else WEEK
    plans = []
    for (e0, e1) in eras:
        if cfg["unit"] == "day":
            ad = [(a, wd) for a, wd in day_anchors(e0, e1) if a + 86400 > e0 and a < e1]
            anc = [a for a, wd in ad]
            sch = schedule(len(anc), cfg, rnd, [wd for a, wd in ad])
        else:
            anc = [a for a in week_anchors(e0, e1) if a + WEEK > e0 and a < e1]
            sch = schedule(len(anc), cfg, rnd)
        plans.append((e0, e1, anc, sch))
        log("  era %s .. %s: %d %ss" % (time.strftime("%Y-%m-%d", time.gmtime(e0)),
                                         time.strftime("%Y-%m-%d", time.gmtime(min(e1, t_last))), len(anc), cfg["unit"]))
    if os.path.exists(out_path):
        os.remove(out_path)
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    out = sqlite3.connect(out_path)
    out.execute("PRAGMA journal_mode=OFF")
    out.execute("PRAGMA synchronous=OFF")
    out.execute("CREATE TABLE bars_m1 (symbol TEXT, ts INTEGER, time_utc TEXT, open REAL, high REAL, low REAL, "
                "close REAL, volume REAL, spread_avg REAL, PRIMARY KEY (symbol, ts)) WITHOUT ROWID")
    out.execute("CREATE TABLE gaps (symbol TEXT, after_bar TEXT, next_bar TEXT, missing_minutes INTEGER, kind TEXT, "
                "note TEXT)")
    out.execute("CREATE TABLE synth_meta (key TEXT, value TEXT)")
    out.execute("CREATE TABLE regime (symbol TEXT, t0 REAL, t1 REAL, state TEXT, a REAL)")
    meta = dict(cfg)
    meta["source"] = src
    meta["made"] = time.strftime("%Y-%m-%d %H:%M:%S")
    meta["generator"] = "v8" if cfg.get("bsnap") else ("v7" if cfg.get("soft") else "v6")
    if cfg.get("bsnap") and (cfg.get("soft") or cfg.get("regime") or cfg["unit"] != "week"):
        raise RuntimeError("--bsnap needs week blocks and cannot be combined with --soft / --regime")
    if cfg.get("soft") and cfg.get("regime"):
        raise RuntimeError("--soft and --regime cannot be combined")
    out.executemany("insert into synth_meta values (?,?)", [(k, str(v)) for k, v in sorted(meta.items())])
    dropped = 0
    fmt = lambda t: time.strftime("%Y-%m-%d %H:%M", time.gmtime(t + shift))
    use_cache = cache_valid(src)
    if use_cache:
        with open(os.path.join(_cache_dir(), "meta.json")) as f:
            cmeta = json.load(f)["markets"]
        log("  reading bars from the source cache (memory-mapped)")
    for name, dbs in sorted(syms.items()):
        t0 = time.time()
        mapped = None
        if use_cache and name in cmeta:
            mapped = _Mapped(name, cmeta[name]["n"])
            d = mapped.d
            gaps = [tuple(g) for g in cmeta[name]["gaps"]]
        else:
            d = _load(con, dbs)
            gaps = []
            if has_gaps:
                for a, b, mins, kind, note in con.execute(
                        "select after_bar, next_bar, missing_minutes, kind, note from gaps where symbol=?", (dbs,)):
                    try:
                        gaps.append((A.to_epoch(a) - shift, A.to_epoch(b) - shift, mins, kind, note))
                    except (ValueError, TypeError):
                        continue
        T, O, H, L, C, V, S = d["T"], d["O"], d["H"], d["L"], d["C"], d["V"], d["S"]
        jr = random.Random(cfg["seed"] * 1000003 + zlib.crc32(name.encode()))
        rcarry, rstats = 0.0, {}
        written = 0
        for e0, e1, anc, sch in plans:
            idx = []                                     # bar index range of every source unit of this era
            for w, a in enumerate(anc):
                nxt = anc[w + 1] if w + 1 < len(anc) else a + unit_len
                idx.append((bisect.bisect_left(T, max(a, e0)), bisect.bisect_left(T, min(nxt, e1))))
            nT, nO, nH, nL, nC, nV, nS = (array("d") for _ in range(7))
            last_close, kf, prev_w = None, 1.0, None
            bstarts = []                                 # v8: where each block starts (destination time)
            for j, w in enumerate(sch):
                lo, hi = idx[w]
                contiguous = prev_w is not None and w == prev_w + 1
                if not contiguous:
                    bstarts.append(max(anc[j], e0))
                prev_w = w
                if hi <= lo:
                    continue
                if not contiguous and last_close is not None:
                    # a block join: start this block from where the last one ended, keeping its own opening gap
                    prev = C[lo - 1] if lo >= 1 and T[lo] - T[lo - 1] < 8 * 86400 else O[lo]
                    kf = last_close / prev
                dt = anc[j] - anc[w]
                end = anc[j] + unit_len if j + 1 >= len(anc) else anc[j + 1]
                for i in range(lo, hi):
                    t = T[i] + dt
                    if t >= end or t < e0 or t >= e1:
                        dropped += 1
                        continue
                    nT.append(t); nO.append(O[i] * kf); nH.append(H[i] * kf); nL.append(L[i] * kf)
                    nC.append(C[i] * kf); nV.append(V[i]); nS.append(S[i] * kf if S[i] == S[i] else S[i])
                last_close = C[hi - 1] * kf
            _transform(nT, nO, nH, nL, nC, nS, cfg, jr)
            if cfg.get("bsnap"):
                rr = random.Random(cfg["seed"] * 7919 + zlib.crc32(name.encode()) + int(e0))
                spells, rcarry = _blocksnap(nT, nO, nH, nL, nC, nS, cfg, rr, bstarts, rcarry, rstats)
                out.executemany("insert into regime values (?,?,?,?,?)", [(name, a, b, st, k) for a, b, st, k in spells])
            elif cfg.get("soft"):
                rr = random.Random(cfg["seed"] * 7919 + zlib.crc32(name.encode()) + int(e0))
                spells, rcarry = _regime7(nT, nO, nH, nL, nC, nS, cfg, rr, name, rcarry, rstats)
                out.executemany("insert into regime values (?,?,?,?,?)", [(name, a, b, st, k) for a, b, st, k in spells])
            elif cfg.get("regime"):
                rr = random.Random(cfg["seed"] * 7919 + zlib.crc32(name.encode()) + int(e0))
                spells, rcarry = _regime(nT, nO, nH, nL, nC, nS, cfg, rr, rcarry, rstats)
                out.executemany("insert into regime values (?,?,?,?,?)", [(name, a, b, st, k) for a, b, st, k in spells])
            rows = []
            tstr = _day_str_cache()
            for i in range(len(nT)):
                t = nT[i]
                rows.append((dbs, int(round(t + shift)), tstr(t),
                             nO[i], nH[i], nL[i], nC[i], nV[i], None if nS[i] != nS[i] else nS[i]))
                if len(rows) >= 200000:
                    out.executemany("insert or ignore into bars_m1 values (?,?,?,?,?,?,?,?,?)", rows)
                    written += len(rows)
                    rows = []
            if rows:
                out.executemany("insert or ignore into bars_m1 values (?,?,?,?,?,?,?,?,?)", rows)
                written += len(rows)
            del nT, nO, nH, nL, nC, nV, nS, rows
        # data holes travel with their source unit (week or day), so the lab skips the same broken stretches
        ng = 0
        for e0, e1, anc, sch in plans:
            rev = defaultdict(list)
            for j, w in enumerate(sch):
                rev[w].append(j)
            for ga, gb, mins, kind, note in gaps:
                if not (e0 <= ga < e1):
                    continue
                w = bisect.bisect_right(anc, ga) - 1
                if w < 0:
                    continue
                for j in rev.get(w, []):
                    dt = anc[j] - anc[w]
                    out.execute("insert into gaps values (?,?,?,?,?,?)", (dbs, fmt(ga + dt), fmt(gb + dt), mins, kind,
                                                                         note))
                    ng += 1
        out.commit()
        log("  %-10s read %d bars, wrote %d bars, %d data holes  (%.0fs)%s" % (
            name, len(T), written, ng, time.time() - t0,
            ("  regime: %d artificial gaps closed%s%s" % (rstats.get("gaps_closed", 0),
                ", %d shock days kept" % rstats["shock_days"] if "shock_days" in rstats else "",
                ", %d of %d blocks mirrored" % (rstats.get("mirrored", 0), rstats.get("blocks", 0)) if "blocks" in rstats else ""))
            if (cfg.get("regime") or cfg.get("soft") or cfg.get("bsnap"))
            else ""))
        del d, T, O, H, L, C, V, S, gaps                # free this market before the next one
        if mapped is not None:
            mapped.close()
    con.close()
    out.close()
    log("bars dropped at period edges: %d" % dropped)
    return out_path


# ------------------------------------------------------------------ check
def _stats(con, dbsym, eras):
    """Per era: annual vol %, daily lag-1 autocorr, 20-day variance ratio, mean |M15 move| bp, trend-month share,
    spread bp."""
    shift = A.DB_UTC_OFFSET_HOURS * 3600.0
    s0, s1 = A.epoch_of(A.SEAL_START) + shift, A.epoch_of(A.SEAL_END) + shift
    out = {}
    q = ("select ts, high, low, close, spread_avg from bars_m1 where symbol=? and (ts < ? or ts >= ?) order by ts")
    per = defaultdict(lambda: {"day": [], "m15": [], "spr": []})
    cur_d = cur_q = None
    for ts, h, l, c, sp in con.execute(q, (dbsym, int(s0), int(s1))):
        t = A.to_epoch(ts) - shift
        e = None
        for k, (e0, e1) in enumerate(eras):
            if e0 <= t < e1:
                e = k
                break
        if e is None or c is None or c <= 0:
            continue
        P = per[e]
        d = int(t // 86400)
        if P["day"] and P["day"][-1][0] == d:
            dd = P["day"][-1]
            dd[1], dd[2], dd[3] = max(dd[1], h), min(dd[2], l), c
        else:
            P["day"].append([d, h, l, c, t])
        qq = int(t // 900)
        if P["m15"] and P["m15"][-1][0] == qq:
            P["m15"][-1][1] = c
        else:
            P["m15"].append([qq, c])
        if sp is not None and len(P["spr"]) < 400000 and int(t) % 37 == 0:
            P["spr"].append(sp / c * 1e4)
    for e, P in per.items():
        days = [x for x in P["day"]]
        if len(days) < 60:
            continue
        x = [math.log(dd[3]) for dd in days]
        r = [x[i] - x[i - 1] for i in range(1, len(x))]
        n = len(r)
        mu = sum(r) / n
        var = sum((y - mu) ** 2 for y in r) / (n - 1)
        ac = sum((r[i] - mu) * (r[i - 1] - mu) for i in range(1, n)) / ((n - 1) * var) if var > 0 else 0.0
        r20 = [x[i] - x[i - 20] for i in range(20, len(x))]
        m20 = sum(r20) / len(r20)
        v20 = sum((y - m20) ** 2 for y in r20) / (len(r20) - 1)
        vr = v20 / (20 * var) if var > 0 else 0.0
        m15 = P["m15"]
        mv = [abs(math.log(m15[i][1] / m15[i - 1][1])) for i in range(1, len(m15)) if m15[i][0] - m15[i - 1][0] == 1]
        # trend months: |net move| >= 3 daily ranges and straightness >= 0.3 (same rule as Part D)
        mon = defaultdict(list)
        for dd in days:
            mon[time.strftime("%Y-%m", time.gmtime(dd[4]))].append(dd)
        tm = tot = 0
        for k_, ds in mon.items():
            if len(ds) < 12:
                continue
            rng = sum(dd[1] - dd[2] for dd in ds) / len(ds)
            cl = [dd[3] for dd in ds]
            path = sum(abs(cl[i] - cl[i - 1]) for i in range(1, len(cl)))
            mvm = abs(cl[-1] - cl[0])
            tot += 1
            if rng > 0 and mvm / rng >= 3.0 and path > 0 and mvm / path >= 0.3:
                tm += 1
        out[e] = {"vol": 100 * math.sqrt(var * 252), "ac1": ac, "vr20": vr,
                  "m15": 1e4 * sum(mv) / len(mv) if mv else 0.0, "trendm": 100.0 * tm / tot if tot else 0.0,
                  "spr": sum(P["spr"]) / len(P["spr"]) if P["spr"] else float("nan"), "days": len(days)}
    return out


def check(synth_path, lines):
    src = A.find_db()
    rc, sc = sqlite3.connect(src), sqlite3.connect(synth_path)
    meta = dict(sc.execute("select key, value from synth_meta"))
    lines.append("SYNTHETIC: %s" % synth_path)
    lines.append("settings: " + ", ".join("%s=%s" % kv for kv in sorted(meta.items()) if kv[0] not in ("source",)))
    lines.append("")
    lines.append("Each cell: REAL / SYNTH.  vol = annualized daily volatility %; ac1 = day-to-day autocorrelation of")
    lines.append("returns (+ = trends persist); VR20 = 20-day variance ratio (>1 = trending, <1 = mean-reverting);")
    lines.append("m15 = average |M15 move| in bp; trend% = share of months that were trend months (3+ daily ranges,")
    lines.append("straightness 0.3+); spread = average spread in bp of price. 'shuffle' should match vol / m15 / spread")
    lines.append("closely and VR20 / trend% roughly (trends longer than a block are cut); 'dayshuffle' should push VR20")
    lines.append("toward 1 and ac1 toward 0; vol / drift / spread should move their columns in the stated direction.")
    syms = _symbols(rc)
    ss = set(r[0] for r in sc.execute("select distinct symbol from bars_m1"))
    t_first = A.epoch_of("2013-01-01")
    eras = _eras(t_first, time.time())
    names = ["2014-17", "2018-19", "2020-21", "2024+"]
    for name, dbs in sorted(syms.items()):
        if dbs not in ss and name not in ss:
            continue
        a = _stats(rc, dbs, eras)
        b = _stats(sc, dbs if dbs in ss else name, eras)
        lines.append("")
        lines.append("%s" % name)
        lines.append("  era        vol %          ac1             VR20           m15 bp         trend%          spread bp")
        for e in range(4):
            if e not in a or e not in b:
                continue
            x, y = a[e], b[e]
            lines.append("  %-8s %5.1f / %5.1f  %+.3f / %+.3f  %.2f / %.2f   %5.1f / %5.1f  %4.0f / %4.0f    %5.2f / %5.2f" % (
                names[e], x["vol"], y["vol"], x["ac1"], y["ac1"], x["vr20"], y["vr20"], x["m15"], y["m15"],
                x["trendm"], y["trendm"], x["spr"], y["spr"]))
    rc.close()
    sc.close()


def _write_report(lines):
    stamp = time.strftime("%Y%m%d_%H%M%S")
    d = os.path.join(A.ROOT, "reports", "synth_%s" % stamp)
    os.makedirs(d, exist_ok=True)
    p = os.path.join(d, "synth_check.txt")
    with open(p, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    try:
        v = os.path.join(A.ROOT, A.VISION_DIR_NAME)
        os.makedirs(v, exist_ok=True)
        shutil.copy2(p, os.path.join(v, "synth_check.txt"))
        print("claude vision: added synth_check.txt (nothing wiped)")
    except Exception as e:
        print("(claude vision not updated: %s)" % e)
    print("report: %s" % p)



def _gate_extra(mdict):
    """v8 additions. mdict = {market: FX-day bars}. vol_prec / vol_share: atr10 >= 1.25 x trailing 250-day mean TR vs the
    hindsight truth (centred 20-day mean TR >= 1.25 x the same base), as asiabo_probe M5. down3: share of index days
    (US500, GERMANY40) that follow 3 down closes; bounce3: share of those where the day closes up."""
    vk = vn = vt = vtn = 0
    d3 = dn = b3 = 0
    for m, d in mdict.items():
        key, hi, lo, cl = d["key"], d["h"], d["l"], d["c"]
        n = len(key)
        seg = [0] * n
        for j in range(1, n):
            seg[j] = j if key[j] - key[j - 1] > GATE_SEGGAP else seg[j - 1]
        send = [0] * n
        e = n - 1
        for j in range(n - 1, -1, -1):
            send[j] = e
            if seg[j] == j:
                e = j - 1
        tr = [hi[0] - lo[0]] + [max(hi[j] - lo[j], abs(hi[j] - cl[j - 1]), abs(lo[j] - cl[j - 1])) for j in range(1, n)]
        ts = [0.0]
        for v in tr:
            ts.append(ts[-1] + v)
        for j in range(n):
            if not _era_ok(key[j]):
                continue
            if j - 250 >= seg[j] and j + 10 <= send[j] and j - 10 >= seg[j]:
                base = (ts[j] - ts[j - 250]) / 250.0
                truth = (ts[j + 11] - ts[j - 9]) / 20.0 >= 1.25 * base
                det = (ts[j] - ts[j - 10]) / 10.0 >= 1.25 * base
                vtn += 1
                vt += truth
                if det:
                    vn += 1
                    vk += truth
            if m in ("US500", "GERMANY40") and j - 3 >= seg[j] and j >= 4:
                dn += 1
                if cl[j - 1] < cl[j - 2] < cl[j - 3] < cl[j - 4]:
                    d3 += 1
                    b3 += cl[j] > cl[j - 1]
    return {"vol_prec": vk / float(max(1, vn)), "vol_share": vt / float(max(1, vtn)),
            "down3": d3 / float(max(1, dn)), "bounce3": b3 / float(max(1, d3))}


# ------------------------------------------------------------------ realism gate (v7, 2026-10-11; v8 2026-10-12)
# Statistics of FX-day bars, definitions = asiabo_probe.py (probe_plan.md). Tolerances fixed 2026-10-11 BEFORE any
# v7 world was generated at M1 level: 2 x the seed-to-seed spread of 12 calibrated v7 worlds (daily simulator).
GATE_ER = 0.30
GATE_SEGGAP = 10
# (revised once, 2026-10-11 22:30, when the shock-day rule was added after the first M1 world failed: same rule,
#  recomputed for the final model; vr20 moved to the weak set because the plain cousin sits inside its band)
# v8 (2026-10-12): the same rule (2 x the seed spread of the calibrated generator, now v8, 18 worlds) + three new
# statistics for the v7 gaps. vol_prec: v8 sits ~0.10 below real (block joins break slow volatility regimes); the
# tolerance 0.15 still rejects every v7 / dayshuffle world (0.20-0.27 below). Pass rates: v8 12/18, block base without
# the snap 2/9, v7 0/18, dayshuffle 0/9.
GATE_TOL = {"truth_share": 0.019, "er20_prec": 0.039, "er40_prec": 0.081, "ac1": 0.051, "vol_prec": 0.15,
            "down3": 0.021, "spell20_share": 0.028, "hazard_ratio": 0.381, "mid20": 1.298, "vr20": 0.169,
            "bounce3": 0.075}
GATE_STRONG = ("truth_share", "er20_prec", "er40_prec", "ac1", "vol_prec", "down3")
GATE_ORDER = ("truth_share", "er20_prec", "er40_prec", "ac1", "vol_prec", "down3",
              "spell20_share", "hazard_ratio", "mid20", "vr20", "bounce3")
GATE_TEXT = {"truth_share": "days inside a hindsight 41-close straight stretch (er >= 0.30)",
             "er40_prec": "er40 >= 0.30 agrees with that hindsight trend",
             "vr20": "20-day variance ratio of daily returns (< 1 = mean-reverting)",
             "ac1": "lag-1 autocorrelation of daily returns (mean of markets)",
             "er20_prec": "er20 >= 0.30 agrees with the hindsight trend",
             "spell20_share": "share of er40 spells lasting 20+ days",
             "hazard_ratio": "er40 spell hazard, age 21-40 / age 6-20",
             "mid20": "mid-spell (age 10+) move over the next 20 days, in daily ATRs",
             "vol_prec": "atr10 >= 1.25 x 250-day mean TR agrees with the hindsight high-vol state (volatility clustering)",
             "down3": "share of index days (US500, GERMANY40) after 3 down closes (dip's setup)",
             "bounce3": "share of those index days that close up"}


def _fx_daily(rows):
    """rows = iterable of (t_utc, o, h, l, c) in time order -> FX-day bars {key, o, h, l, c}."""
    out = {"key": [], "o": [], "h": [], "l": [], "c": []}
    cur = None
    for t, o, h, l, c in rows:
        if c is None or c <= 0:
            continue
        d = _fx_day(t)
        if d != cur:
            out["key"].append(d); out["o"].append(o); out["h"].append(h); out["l"].append(l); out["c"].append(c)
            cur = d
        else:
            if h > out["h"][-1]:
                out["h"][-1] = h
            if l < out["l"][-1]:
                out["l"][-1] = l
            out["c"][-1] = c
    return out


def _daily_of_db(path, real):
    """{market: FX-day bars} of the house markets in a bars db (sealed years skipped; the cache is used for bars.db)."""
    shift = A.DB_UTC_OFFSET_HOURS * 3600.0
    con = sqlite3.connect(path)
    syms = _symbols(con) if real else None
    if not real:
        have = set(r[0] for r in con.execute("select distinct symbol from bars_m1"))
        rc = sqlite3.connect(A.find_db())
        syms = dict((k, v) for k, v in _symbols(rc).items() if v in have)
        rc.close()
    out = {}
    cmeta = None
    if real and cache_valid(path):
        with open(os.path.join(_cache_dir(), "meta.json")) as f:
            cmeta = json.load(f)["markets"]
    for name, dbs in sorted(syms.items()):
        if cmeta and name in cmeta:
            mp = _Mapped(name, cmeta[name]["n"])
            d = mp.d
            out[name] = _fx_daily(zip(d["T"], d["O"], d["H"], d["L"], d["C"]))
            mp.close()
        else:
            q = "select ts, open, high, low, close from bars_m1 where symbol=? order by ts"
            s0, s1 = A.epoch_of(A.SEAL_START), A.epoch_of(A.SEAL_END)
            rows = ((A.to_epoch(ts) - shift, o, h, l, c) for ts, o, h, l, c in con.execute(q, (dbs,)))
            out[name] = _fx_daily((r for r in rows if not (s0 <= r[0] < s1)))
    con.close()
    return out


def gate(synth_path, log=print):
    """The realism gate (see the top). -> True if the synthetic world passes."""
    t0 = time.time()
    log("realism gate: reading FX-day bars of bars.db and %s ..." % synth_path)
    rd = _daily_of_db(A.find_db(), True)
    sd = _daily_of_db(synth_path, False)
    common = sorted(set(rd) & set(sd))
    r = _gate_stats([rd[m] for m in common])
    y = _gate_stats([sd[m] for m in common])
    r.update(_gate_extra(dict((m, rd[m]) for m in common)))
    y.update(_gate_extra(dict((m, sd[m]) for m in common)))
    lines = ["REALISM GATE (make_synth v7, 2026-10-11): %s vs bars.db, markets %s" % (synth_path, ", ".join(common)), ""]
    try:
        sc = sqlite3.connect(synth_path)
        meta = dict(sc.execute("select key, value from synth_meta"))
        sc.close()
        lines.append("settings: " + ", ".join("%s=%s" % kv for kv in sorted(meta.items()) if kv[0] != "source"))
        lines.append("")
    except sqlite3.Error:
        pass
    lines.append("  %-14s %8s %8s %8s %6s   %s" % ("statistic", "real", "synth", "tol", "", "meaning"))
    bad_s, bad_w = [], []
    for k in GATE_ORDER:
        a, b = r.get(k), y.get(k)
        ok = a is not None and b is not None and abs(a - b) <= GATE_TOL[k]
        if not ok:
            (bad_s if k in GATE_STRONG else bad_w).append(k)
        lines.append("  %-14s %8s %8s %8.3f %6s   %s%s" % (
            k, ("%.3f" % a) if a is not None else "-", ("%.3f" % b) if b is not None else "-", GATE_TOL[k],
            "ok" if ok else "OUT", GATE_TEXT[k], "  (strong)" if k in GATE_STRONG else ""))
    passed = not bad_s and len(bad_w) < 2
    lines.append("")
    lines.append("per market (real / synth): truth share, ac1")
    for m in common:
        a, b = _gate_stats([rd[m]]), _gate_stats([sd[m]])
        lines.append("  %-10s truth %.3f / %.3f   ac1 %+.3f / %+.3f" % (m, a["truth_share"], b["truth_share"],
                                                                      a["ac1"] or 0.0, b["ac1"] or 0.0))
    lines.append("")
    lines.append("RULE: FAIL if any strong statistic is outside its tolerance, or 2+ of the others.")
    lines.append("KNOWN: v8 worlds sit ~0.10 below real in vol_prec (volatility clustering only partly restored).")
    lines.append("VERDICT: %s%s" % ("PASS" if passed else "FAIL",
                                    "" if passed else "  (strong out: %s; others out: %s)" % (
                                        ", ".join(bad_s) or "none", ", ".join(bad_w) or "none")))
    lines.append("gate runtime %.0fs" % (time.time() - t0))
    for ln in lines:
        log(ln)
    stamp = time.strftime("%Y%m%d_%H%M%S")
    d = os.path.join(A.ROOT, "reports", "synth_gate_%s" % stamp)
    os.makedirs(d, exist_ok=True)
    nm = "synth_gate_%s.txt" % os.path.splitext(os.path.basename(synth_path))[0]
    with open(os.path.join(d, nm), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    try:
        v = os.path.join(A.ROOT, A.VISION_DIR_NAME)
        os.makedirs(v, exist_ok=True)
        shutil.copy2(os.path.join(d, nm), os.path.join(v, nm))
        log("claude vision: added %s (nothing wiped)" % nm)
    except Exception as e:
        log("(claude vision not updated: %s)" % e)
    return passed


def _era_ok(k):
    y = time.gmtime(k * 86400.0).tm_year
    return 2014 <= y <= 2021 or y >= 2024


def _gate_stats(markets):
    acc = {"truth_n": 0, "truth_k": 0, "e20_n": 0, "e20_k": 0, "e40_n": 0, "e40_k": 0,
           "sp": [], "mid": [], "vr": [], "ac1": []}
    for d in markets:
        key, o, hi, lo, cl = d["key"], d["o"], d["h"], d["l"], d["c"]
        n = len(key)
        if n < 100:
            continue
        seg = [0] * n
        for j in range(1, n):
            seg[j] = j if key[j] - key[j - 1] > GATE_SEGGAP else seg[j - 1]
        send = [0] * n
        e = n - 1
        for j in range(n - 1, -1, -1):
            send[j] = e
            if seg[j] == j:
                e = j - 1
        ad = [0.0] + [abs(cl[j] - cl[j - 1]) for j in range(1, n)]
        ads = [0.0]
        for v in ad:
            ads.append(ads[-1] + v)
        tr = [hi[0] - lo[0]] + [max(hi[j] - lo[j], abs(hi[j] - cl[j - 1]), abs(lo[j] - cl[j - 1])) for j in range(1, n)]
        N = [None] * n
        s = 0.0
        for j in range(n):
            if j - 20 >= seg[j]:
                N[j] = sum(tr[j - 20:j]) / 20.0
        ok = [N[j] is not None and _era_ok(key[j]) for j in range(n)]

        def er(j, w):
            a = j - 1 - w
            if a < seg[j] or j < 1:
                return None
            path = ads[j] - ads[a + 1]
            mv = cl[j - 1] - cl[a]
            return ((abs(mv) / path) if path else 0.0, 1 if mv > 0 else -1)

        def erc(j, h):
            a, b = j - h, j + h
            if a < seg[j] or b > send[j]:
                return None
            path = ads[b + 1] - ads[a + 1]
            mv = cl[b] - cl[a]
            return ((abs(mv) / path) if path else 0.0, 1 if mv > 0 else -1)
        # truth + precision
        for j in range(n):
            if not _era_ok(key[j]):
                continue
            t = erc(j, 20)
            if t is None:
                continue
            tv = t[1] if t[0] >= GATE_ER else 0
            acc["truth_n"] += 1
            acc["truth_k"] += 1 if tv else 0
            for w, nm in ((20, "e20"), (40, "e40")):
                x = er(j, w)
                if x is None or x[0] < GATE_ER:
                    continue
                acc[nm + "_n"] += 1
                acc[nm + "_k"] += 1 if tv == x[1] else 0
        # er40 spells
        cur = None
        for j in range(1, n):
            x = er(j, 40)
            st = (x[1] if x[0] >= GATE_ER else 0) if x else None
            if cur is not None and seg[j] == j:
                acc["sp"].append((j - 1 - cur[0] + 1, True))
                cur = None
            if st:
                if cur is None:
                    cur = (j, st)
                elif st != cur[1]:
                    acc["sp"].append((j - cur[0], False))
                    _mid(acc, cur, j, cl, o, N, ok, send)
                    cur = (j, st)
            elif cur is not None:
                acc["sp"].append((j - cur[0], False))
                _mid(acc, cur, j, cl, o, N, ok, send)
                cur = None
        if cur is not None:
            acc["sp"].append((n - 1 - cur[0] + 1, True))
        # variance ratio (20 days) and lag-1 autocorrelation of daily log returns, per segment
        r = [math.log(cl[j] / cl[j - 1]) for j in range(1, n) if seg[j] != j and _era_ok(key[j])]
        if len(r) > 200:
            mu = sum(r) / len(r)
            v1 = sum((x - mu) ** 2 for x in r) / len(r)
            r20 = [sum(r[i:i + 20]) - 20 * mu for i in range(0, len(r) - 20, 5)]
            v20 = sum(x * x for x in r20) / len(r20)
            acc["vr"].append(v20 / (20 * v1) if v1 else None)
            acc["ac1"].append(sum((r[i] - mu) * (r[i - 1] - mu) for i in range(1, len(r))) / (len(r) * v1))
    sp = acc["sp"]
    out = {}
    out["truth_share"] = acc["truth_k"] / float(max(1, acc["truth_n"]))
    out["er20_prec"] = acc["e20_k"] / float(max(1, acc["e20_n"]))
    out["er40_prec"] = acc["e40_k"] / float(max(1, acc["e40_n"]))
    out["spells"] = len(sp)
    out["spell20_share"] = sum(1 for ln, c in sp if ln >= 20) / float(max(1, len(sp)))
    e, rk = {}, {}
    for b in ((6, 20), (21, 40)):
        e[b] = sum(1 for ln, c in sp if not c and b[0] <= ln <= b[1])
        rk[b] = sum(max(0, min(ln, b[1]) - b[0] + 1) for ln, c in sp if ln >= b[0])
    h1 = e[(6, 20)] / float(max(1, rk[(6, 20)]))
    h2 = e[(21, 40)] / float(max(1, rk[(21, 40)]))
    out["hazard_ratio"] = h2 / h1 if h1 else None
    out["mid20"] = sum(acc["mid"]) / len(acc["mid"]) if acc["mid"] else None
    vr = [x for x in acc["vr"] if x is not None]
    out["vr20"] = sum(vr) / len(vr) if vr else None
    out["ac1"] = sum(acc["ac1"]) / len(acc["ac1"]) if acc["ac1"] else None
    return out


def _mid(acc, cur, e, cl, o, N, ok, send):
    a, d = cur
    if e - a < 10:
        return
    for j in range(a + 9, e):
        if ok[j] and j + 19 <= send[j] and N[j]:
            acc["mid"].append(d * (cl[j + 19] - o[j]) / N[j])


def _parse(argv):
    cfg = dict(DEFAULTS)
    cfg["seed"], cfg["preset"] = 1, "shuffle"
    out = None
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--preset":
            cfg["preset"] = argv[i + 1]; i += 2
        elif a == "--seed":
            cfg["seed"] = int(argv[i + 1]); i += 2
        elif a == "--out":
            out = argv[i + 1]; i += 2
        elif a == "--block":
            lo, hi = argv[i + 1].split(","); cfg["bmin"], cfg["bmax"] = int(lo), int(hi); i += 2
        elif a == "--markets":
            cfg["markets"] = argv[i + 1]; i += 2
        elif a == "--regime":
            cfg["regime"] = argv[i + 1]; i += 2
        elif a == "--spell":
            cfg["spell"] = argv[i + 1]; i += 2
        elif a in ("--vol", "--drift", "--jitter", "--level", "--spread", "--persist", "--aging"):
            cfg[a[2:]] = float(argv[i + 1]); i += 2
        elif a == "--unit":
            cfg["unit"] = argv[i + 1]; i += 2
        elif a == "--soft":
            cfg["soft"] = argv[i + 1]; i += 2
        elif a == "--lb":
            cfg["lb"] = int(argv[i + 1]); i += 2
        elif a == "--rev1":
            cfg["rev1"] = argv[i + 1]; i += 2
        elif a == "--bsnap":
            cfg["bsnap"] = argv[i + 1]; i += 2
        elif a == "--bmom":
            cfg["bmom"] = float(argv[i + 1]); i += 2
        else:
            raise SystemExit("unknown option %s" % a)
    if cfg["preset"] not in PRESETS:
        raise SystemExit("unknown preset %s (have: %s)" % (cfg["preset"], ", ".join(PRESETS)))
    base = dict(DEFAULTS)
    base.update(PRESETS[cfg["preset"]])
    for k, v in base.items():                     # preset fills only what the command line left at default
        if k in DEFAULTS:
            if cfg[k] == DEFAULTS[k]:
                cfg[k] = v
        elif k not in cfg:                       # v7 keys: only present when a v7 preset / option uses them
            cfg[k] = v
    if cfg.get("soft"):
        for k, v in V7_DEFAULTS.items():
            cfg.setdefault(k, v)
    if cfg.get("bsnap"):
        for k, v in V8_DEFAULTS.items():
            cfg.setdefault(k, v)
    if out is None:
        out = os.path.join(A.ROOT, "synth", "synth_%s_s%d.db" % (cfg["preset"], cfg["seed"]))
    return cfg, out


def main():
    argv = sys.argv[1:]
    cmd = argv[0] if argv else "default"
    t0 = time.time()
    if cmd == "cache":
        build_cache()
    elif cmd == "check":
        lines = []
        check(argv[1], lines)
        _write_report(lines)
    elif cmd == "gen":
        cfg, out = _parse(argv[1:])
        print("generating %s (seed %d) -> %s" % (cfg["preset"], cfg["seed"], out))
        generate(cfg, out)
        if cfg.get("soft") or cfg.get("bsnap"):
            ok = gate(out)
            if not ok:
                print("done in %.0fs" % (time.time() - t0))
                raise SystemExit(3)
    elif cmd == "gate":
        ok = gate(argv[1])
        print("done in %.0fs" % (time.time() - t0))
        raise SystemExit(0 if ok else 3)
    elif cmd == "default":
        cfg, out = _parse([])
        lines = ["make_synth default run: shuffle, seed 1, then a statistics check against bars.db", ""]
        generate(cfg, out, log=lambda s: (print(s), lines.append(s)))
        lines.append("")
        check(out, lines)
        _write_report(lines)
    else:
        raise SystemExit(__doc__)
    print("done in %.0fs" % (time.time() - t0))


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception:
        import traceback
        traceback.print_exc()
        sys.exit(1)
