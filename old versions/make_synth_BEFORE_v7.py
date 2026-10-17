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

PRESETS (fixed before any synthetic result was seen):
  identity   no reshuffle, no shift      -> must reproduce the real results (sanity check of the generator)
  shuffle    reshuffled history only (blocks of 2-6 weeks)
  dayshuffle whole days reshuffled (same weekday): no multi-day structure at all
  cosmetic   shuffle + level 1.7 + jitter 0.3            (should NOT matter)
  vol_up     shuffle + vol 1.3          vol_down   shuffle + vol 0.75
  trend_up   shuffle + drift 0.15       trend_up2  shuffle + drift 0.30
  costly     shuffle + spread 1.5
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
}
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
    meta["generator"] = "v6"
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
            for j, w in enumerate(sch):
                lo, hi = idx[w]
                contiguous = prev_w is not None and w == prev_w + 1
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
            if cfg.get("regime"):
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
            ("  regime: %d artificial gaps closed" % rstats.get("gaps_closed", 0)) if cfg.get("regime") else ""))
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
        else:
            raise SystemExit("unknown option %s" % a)
    if cfg["preset"] not in PRESETS:
        raise SystemExit("unknown preset %s (have: %s)" % (cfg["preset"], ", ".join(PRESETS)))
    base = dict(DEFAULTS)
    base.update(PRESETS[cfg["preset"]])
    for k, v in base.items():                     # preset fills only what the command line left at default
        if cfg[k] == DEFAULTS[k]:
            cfg[k] = v
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
