"""
asiabo_hunt.py  --  the POCKET ENGINE, stage 2 (2026-10-10): the HUNT. Which market states make each part work better
(keep it there) or worse (make it harmless there)? Stage 1 (asiabo_engine.py) then tests the causal ones on ideal and
nightmare worlds.

THE PROTOCOL (fixed 2026-10-10, before any hunt result): the search and the check never see the same years.
  1. build      the per-trade table of the frozen-book parts (brk, ins, fast, dip, dipx) on the real bars.db, every
                trade with ~25 states known AT ENTRY (volatility, momentum / persistence, compression, gaps, session,
                spread, the part's own recent form, cross-market mood ...).
  2. discover   searches ONLY the DISCOVERY half = 2014-17 + 2020-21. Pockets, for BOTH good and bad trades: every state
                read on both sides and at its extremes -- thirds, bottom / top 10%, the sign split for centred states
                (0 for "with the trade" moves, 1 for the variance ratio) -- or its categories (cut points from the
                discovery half only), alone and crossed with the momentum axis (vr120, causally established for brk /
                fast / dip in stage 1). Near-duplicates (80%+ the same trades, same sign) are dropped. Every kept
                pocket gets (2026-10-10, Ezio): a PROFILE (direction, market, era mix and the median regime /
                volatility / trend inside vs outside), a DISGUISE check (within each third / category of every other
                state, does it still beat the rest? the worst control and how much of the effect it leaves) and a
                CONCENTRATION check (share from its best market-year, and the diff without it). All on the discovery
                half only. A pocket is kept if its edge differs from the
                rest of the part with clustered |t| >= 2.5, at least 60 trades inside and outside; at most 12 per
                part (largest |t|). Writes reports/hunt/pockets_locked.csv and LOCKS the definitions.
                The report shows the discovery half only. It also runs the YARDSTICK: the same hunt 20 times with each
                market's states shifted in time against its trades (circular shift: keeps each series' own structure,
                breaks the link), counting how many pockets a hunt discovers AND confirms by pure chance.
  3. (Claude)   writes a theory for every locked pocket into the 'theory' column (or 'none'), BEFORE confirm.
  4. confirm    tests the locked pockets ONCE on the CHECK half = 2018-19 + 2024+. Refuses if the definitions changed.
       CONFIRMED  same sign as discovered, clustered t >= 2 in the check half (n >= 30 inside)
       WEAK       same sign, t < 2          FAILED  opposite sign
       The number confirmed is compared with the yardstick's chance count. Each pocket is still judged on its own
       evidence (standing rule), with the chance rate as context.
  Pockets on states synth can CREATE (persistence, trend, volatility, spread) are handed to the engine's dials next;
  select-only states (weekday, hour, market ...) can only be judged by this split.

    python asiabo_hunt.py discover            build the table (if not built) + discover + yardstick
    python asiabo_hunt.py confirm             the one-shot check on the other half
    python asiabo_hunt.py build [--db x.db]   rebuild the table only
EDGE = net R minus the coin-flip average (cost-free direction value). t clustered by market x month.
"""
import os, sys, json, math, time, random, bisect, hashlib, csv, traceback
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import asiabo_offline as A

DISC_ERAS = ("2014-17", "A 2020-21")
CHECK_ERAS = ("2018-19", "B 2024+")
PARTS = ("brk", "ins", "fast", "dip", "dipx")
MIN_IN = 60
T_DISC = 2.5
MAX_PER_PART = 12
NULL_RUNS = 20
T_CONF, MIN_CONF_N = 2.0, 30
AXIS = "vr120"
NUMERIC = ["vol", "atrchg", "trendy", "vr120", "ac60", "trend60_with", "eff10_with", "mv10_with", "pos20_with",
           "dist200_with", "prev_range", "risk_size", "day_move_with", "gap_with", "spread_R", "form20", "n_trending"]
CATEG = ["dir", "market", "weekday", "hour", "with_50d", "with_slope20", "nr7", "risk_on", "usd_up"]
CREATABLE = {"vr120": "persist dial (D1)", "ac60": "persist dial (D1)", "trend60_with": "persist / drift dial",
             "trendy": "persist dial (D1)", "eff10_with": "persist dial (D1)", "mv10_with": "persist dial (D1)",
             "vol": "needs a volatility-REGIME dial (not built)", "atrchg": "needs a volatility-REGIME dial (not built)",
             "spread_R": "spread dial", "n_trending": "persist dial on all markets"}
DESC = {
    "vol": "volatility vs its own last year (daily ATR / 250-day average)",
    "atrchg": "volatility change: last 5 days' range / 20-day ATR",
    "trendy": "20-day straightness (efficiency ratio)",
    "vr120": "persistence: 5-day variance ratio over the last 120 days (>1 = moves persist)",
    "ac60": "day-to-day autocorrelation over the last 60 days",
    "trend60_with": "60-day move in the trade's direction (ATR x sqrt(60) units)",
    "eff10_with": "10-day straightness in the trade's direction",
    "mv10_with": "10-day move in the trade's direction (daily ATRs)",
    "pos20_with": "price position in the 20-day range, in the trade's direction",
    "dist200_with": "distance from the 200-day average in the trade's direction (daily ATRs)",
    "prev_range": "yesterday's range / ATR",
    "risk_size": "stop distance / ATR",
    "day_move_with": "today's move so far in the trade's direction (ATRs)",
    "gap_with": "today's opening gap in the trade's direction (ATRs)",
    "spread_R": "spread cost of the trade in R",
    "form20": "the part's last 20 finished trades, summed net R",
    "n_trending": "how many of the 4 book markets have 20-day straightness >= 0.3",
    "dir": "long / short", "market": "market", "weekday": "weekday (0 = Monday)", "hour": "hours after the session open",
    "with_50d": "trade with the 50-day average", "with_slope20": "trade with the 20-day average's slope",
    "nr7": "yesterday was the narrowest of 7 days", "risk_on": "US 500 above its 50-day average",
    "usd_up": "USDJPY up over 20 days (dollar strong)",
}


def _hdir():
    return os.path.join(A.ROOT, "reports", "hunt")


# ================================================================ 1. the per-trade table
def _day_feats(m):
    """Per FX day j, known at the START of day j (completed days only): vr120, ac60, signed 60-day move, ATR change,
    20-day straightness, 200-day average, 50-day average side, 20-day move."""
    import asiabo_lab as L
    out = {}
    cl, seg, N = m.cl, m.seg, m.N
    nd = len(m.D)
    r = [0.0] * nd
    for j in range(1, nd):
        r[j] = math.log(cl[j] / cl[j - 1]) if (seg[j] == seg[j - 1] and cl[j - 1] > 0 and cl[j] > 0) else 0.0
    tr = [m.hi[0] - m.lo[0]] + [max(m.hi[j] - m.lo[j], abs(m.hi[j] - cl[j - 1]), abs(m.lo[j] - cl[j - 1]))
                                for j in range(1, nd)]
    for j in range(1, nd):
        if N[j] is None:
            continue
        f = {}
        if j - 121 >= seg[j]:
            rr = r[j - 120:j]
            mu = sum(rr) / 120.0
            v1 = sum((x - mu) ** 2 for x in rr) / 119.0
            s5 = [sum(rr[i - 5:i]) for i in range(5, 121)]
            m5 = sum(s5) / len(s5)
            v5 = sum((x - m5) ** 2 for x in s5) / (len(s5) - 1)
            f["vr120"] = v5 / (5 * v1) if v1 > 0 else None
        if j - 61 >= seg[j]:
            rr = r[j - 60:j]
            mu = sum(rr) / 60.0
            v1 = sum((x - mu) ** 2 for x in rr)
            f["ac60"] = (sum((rr[i] - mu) * (rr[i - 1] - mu) for i in range(1, 60)) / v1) if v1 > 0 else None
            f["mv60"] = (cl[j - 1] - cl[j - 61]) / (N[j] * math.sqrt(60.0))
        if j - 6 >= seg[j]:
            f["atrchg"] = (sum(tr[j - 5:j]) / 5.0) / N[j]
        s200 = m.sma(j - 1, 200)
        if s200 is not None:
            f["d200"] = (cl[j - 1] - s200) / N[j]
        s50 = m.sma(j - 1, 50)
        if s50 is not None:
            f["above50"] = 1 if cl[j - 1] > s50 else 0
        if j - 21 >= seg[j]:
            f["mv20"] = cl[j - 1] - cl[j - 21]
            if m.f[j] and m.f[j].get("er20") is not None:
                f["er20"] = m.f[j]["er20"]
        out[m.D[j][0]] = f
    return out


def build(out_path, day_hook=None):
    """day_hook(m) -> {FX day key: {...}} per market (the regime engine's detectors); stored under 'days'."""
    import asiabo_lab as L
    import asiabo_why as W
    W._install()
    W.WITH_CHAN = False
    t0 = time.time()
    specs = dict((x["name"], x) for x in A.COLLECT_SYMBOLS)
    rows, det, reads, loose, dayf, spr = [], {}, {}, [], {}, {}
    days_out = {}
    for s in W.MARKETS:
        if s not in specs:
            continue
        print("hunt: %s ..." % s)
        try:
            m = L.PMarket(specs[s])
        except RuntimeError as e:
            print("hunt: %s skipped (%s)" % (s, str(e).splitlines()[0]))
            continue
        W._m1_cache(m)
        rb = []
        for name, fn in L.P_LANES:
            if name in L.P_OMEGA_LANES:
                fn(m, rb)
        mine = [(s,) + x for x in rb if (x[0], x[1]) in W.NEED_LV]
        lx = []
        if s in W.DIP_MK:                     # the loose dip (dipx): every signal day, overlapping allowed
            lr = []
            W.lane_rsi2_x(m, lr, level=30.0, loose=True)
            W.lane_dip3_x(m, lr, loose=True)
            lx = [(s,) + x for x in lr if x[6] is not None]
        for x in mine + lx:
            spr[id(x)] = W.spread_r(m, x)
        rows += mine
        loose += lx
        det.update(W.det_table(m))
        reads.update(W.day_reads(m))
        dayf[s] = _day_feats(m)
        if day_hook:
            days_out[s] = day_hook(m)
        if m.m1q:
            m.m1q[0].close()
        m._m1cache.clear()
        del m, rb
    book = W.book_of(rows, det)
    # cross-market mood per FX day
    keys = set(k for s in dayf for k in dayf[s])
    cross = {}
    for k in keys:
        n_tr = sum(1 for s in dayf if dayf[s].get(k, {}).get("er20") is not None and dayf[s][k]["er20"] >= 0.3)
        us = dayf.get("US500", {}).get(k, {})
        jp = dayf.get("USDJPY", {}).get(k, {})
        cross[k] = {"n_trending": n_tr, "risk_on": us.get("above50"),
                    "usd_up": (1 if jp["mv20"] > 0 else 0) if jp.get("mv20") is not None else None}
    # the part's own recent form: last 20 FINISHED trades before entry, summed net R (per part)
    items = [(x, p) for x, p in book] + [(y, "dipx") for y in loose]
    form = {}
    by = defaultdict(list)
    for x, p in items:
        by[p].append(x)
    for p, xs in by.items():
        xs = sorted(xs, key=lambda x: x[8]["_t_in"])
        fin = sorted((x[8]["_t_out"], x[5]) for x in xs)
        for x in xs:
            k = bisect.bisect_right(fin, (x[8]["_t_in"], float("inf")))
            last = [v for t, v in fin[max(0, k - 20):k]]
            form[id(x)] = sum(last) if len(last) >= 20 else None
    out = []
    for x, p in items:
        t = x[8]
        d = t.get("_d")
        dk = t.get("_dk")
        f = dayf.get(x[0], {}).get(dk, {})
        rd = reads.get((x[0], dk), {})
        c = cross.get(dk, {})
        tt = time.gmtime(t["_t_in"])
        sg = lambda v: (v * d) if (v is not None and d) else None
        feat = {"vol": t.get("vol"), "atrchg": f.get("atrchg"), "trendy": t.get("trendy"), "vr120": f.get("vr120"),
                "ac60": f.get("ac60"), "trend60_with": sg(f.get("mv60")), "eff10_with": sg(rd.get("eff")),
                "mv10_with": sg(rd.get("mvN")), "pos20_with": t.get("pos20_with"), "dist200_with": sg(f.get("d200")),
                "prev_range": t.get("prev_range"), "risk_size": t.get("risk_size"),
                "day_move_with": t.get("day_move_with"), "gap_with": t.get("gap_with"), "spread_R": spr.get(id(x)),
                "form20": form.get(id(x)), "n_trending": c.get("n_trending"),
                "dir": "long" if d and d > 0 else "short", "market": x[0], "weekday": t.get("weekday"),
                "hour": t.get("hour"), "with_50d": t.get("with_50d"), "with_slope20": t.get("with_slope20"),
                "nr7": t.get("nr7"), "risk_on": c.get("risk_on"), "usd_up": c.get("usd_up")}
        out.append({"part": p, "market": x[0], "era": x[4], "t_in": t["_t_in"], "t_out": t["_t_out"],
                    "edge": x[5] - x[6], "net": x[5], "gross": x[7], "dk": dk,
                    "cl": "%s|%d-%02d" % (x[0], tt.tm_year, tt.tm_mon), "f": feat})
    out.sort(key=lambda r: (r["market"], r["t_in"]))
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    tmp = out_path + ".tmp"
    with open(tmp, "w") as fh:
        json.dump({"db": A.find_db(), "built": time.strftime("%Y-%m-%d %H:%M"), "trades": out,
                   "days": days_out}, fh)
    os.replace(tmp, out_path)
    print("hunt: %d trades in the table (%.0fs) -> %s" % (len(out), time.time() - t0, out_path))


# ================================================================ statistics
def _diff_t(y, cl, ind):
    """edge inside the pocket minus outside, and its t clustered by market x month (OLS on the indicator)."""
    n = len(y)
    n1 = sum(ind)
    if n1 == 0 or n1 == n:
        return None, None, None, None
    xb = n1 / float(n)
    yb = sum(y) / n
    m1 = sum(v for v, i in zip(y, ind) if i) / n1
    m0 = (sum(y) - m1 * n1) / (n - n1)
    b = m1 - m0
    sxx = n * xb * (1 - xb)
    u = defaultdict(float)
    for v, c, i in zip(y, cl, ind):
        dx = i - xb
        u[c] += dx * (v - yb - b * dx)
    k = len(u)
    if k < 2:
        return b, None, m1, m0
    var = sum(e * e for e in u.values()) * k / (k - 1.0) / (sxx * sxx)
    return b, (b / math.sqrt(var) if var > 0 else None), m1, m0


def _mean_t(y, cl):
    n = len(y)
    if n < 2:
        return None, None
    mu = sum(y) / n
    g = defaultdict(float)
    for v, c in zip(y, cl):
        g[c] += v - mu
    k = len(g)
    if k < 2:
        return mu, None
    var = sum(e * e for e in g.values()) * k / (k - 1.0) / (n * n)
    return mu, (mu / math.sqrt(var) if var > 0 else None)


# ================================================================ 2. discover
# 2026-10-10 (Ezio): every numeric state is read on BOTH sides and at its EXTREMES -- thirds, bottom / top 10%, and,
# for states centred on a natural middle (0 for "with the trade" moves, 1 for the variance ratio), the sign split.
CENTRE = {"trend60_with": 0.0, "eff10_with": 0.0, "mv10_with": 0.0, "dist200_with": 0.0, "day_move_with": 0.0,
          "gap_with": 0.0, "ac60": 0.0, "form20": 0.0, "vr120": 1.0}
TER = ("low third", "mid third", "high third")
JACCARD_DUP = 0.8                 # a pocket that shares 80%+ of its trades with a stronger kept one (same sign) is a duplicate


def _cutmap(trs):
    cm = {}
    for f in NUMERIC:
        v = sorted(r["f"][f] for r in trs if r["f"].get(f) is not None)
        n = len(v)
        cm[f] = None if n < 30 else {"q": [v[n // 3], v[2 * n // 3]], "p10": v[n // 10], "p90": v[9 * n // 10]}
    return cm


def _member(f, v, key, cm):
    if v is None:
        return False
    if f in CATEG:
        return str(v) == key
    c = cm.get(f)
    if not c:
        return False
    if key in ("0", "1", "2"):
        b = 0 if v <= c["q"][0] else (1 if v <= c["q"][1] else 2)
        return b == int(key)
    if key == "t10":
        return v <= c["p10"]
    if key == "t90":
        return v > c["p90"]
    if key == "neg":
        return v < CENTRE[f]
    if key == "pos":
        return v >= CENTRE[f]
    return False


def _keys(f, trs, cm, cross=False):
    if f in CATEG:
        return sorted(set(str(r["f"][f]) for r in trs if r["f"].get(f) is not None))
    if not cm.get(f):
        return []
    ks = ["0", "1", "2"] + ([] if cross else ["t10", "t90"])
    if f in CENTRE:
        ks += ["neg", "pos"]
    return ks


def _label(f, key, cm):
    if f in CATEG:
        return "%s = %s" % (f, key)
    c = cm.get(f) or {}
    if key in ("0", "1", "2"):
        lo, hi = c["q"]
        rng = {"0": "<= %.3g" % lo, "1": "%.3g .. %.3g" % (lo, hi), "2": "> %.3g" % hi}[key]
        return "%s %s (%s)" % (f, TER[int(key)], rng)
    if key == "t10":
        return "%s bottom 10%% (<= %.3g)" % (f, c["p10"])
    if key == "t90":
        return "%s top 10%% (> %.3g)" % (f, c["p90"])
    if key == "neg":
        return "%s < %g" % (f, CENTRE[f])
    return "%s >= %g" % (f, CENTRE[f])


def _ind(trs, defn, cm):
    return [1 if all(_member(f, r["f"].get(f), k, cm) for f, k in defn) else 0 for r in trs]


def find_pockets(trs, cm=None):
    """trs = one part's discovery trades -> (pockets, cutmap). Pockets: every state's thirds, 10% tails, sign split
    (centred states) and categories, alone; and crossed with the momentum axis (its thirds and its 1.0 split)."""
    if cm is None:
        cm = _cutmap(trs)
    y = [r["edge"] for r in trs]
    cl = [r["cl"] for r in trs]
    mem = {}

    def M(f, k):
        if (f, k) not in mem:
            mem[(f, k)] = [1 if _member(f, r["f"].get(f), k, cm) else 0 for r in trs]
        return mem[(f, k)]
    cand = []

    def test(defn, ind):
        n1 = sum(ind)
        if n1 < MIN_IN or len(ind) - n1 < MIN_IN:
            return
        b, t, m1, m0 = _diff_t(y, cl, ind)
        if t is None or abs(t) < T_DISC:
            return
        cand.append({"def": defn, "n_in": n1, "n_out": len(ind) - n1, "edge_in": m1, "edge_out": m0, "diff": b,
                     "t": t, "_ind": ind})
    for f in NUMERIC + CATEG:
        for k in _keys(f, trs, cm):
            test([(f, k)], M(f, k))
    for a in _keys(AXIS, trs, cm, cross=True):
        ia = M(AXIS, a)
        for f in NUMERIC + CATEG:
            if f == AXIS:
                continue
            for k in _keys(f, trs, cm, cross=True):
                test([(AXIS, a), (f, k)], [p * q for p, q in zip(ia, M(f, k))])
    cand.sort(key=lambda p: -abs(p["t"]))
    out = []
    for p in cand:
        s = set(i for i, v in enumerate(p["_ind"]) if v)
        dup = False
        for q in out:
            if (q["diff"] > 0) == (p["diff"] > 0):
                inter = len(s & q["_set"])
                if inter / float(len(s | q["_set"])) >= JACCARD_DUP:
                    dup = True
                    break
        if dup:
            continue
        p["_set"] = s
        out.append(p)
        if len(out) >= MAX_PER_PART:
            break
    return out, cm


def _confirm_one(trs, p, cm):
    y = [r["edge"] for r in trs]
    cl = [r["cl"] for r in trs]
    ind = _ind(trs, p["def"], cm)
    n1 = sum(ind)
    b, t, m1, m0 = _diff_t(y, cl, ind)
    if b is None or t is None or n1 < MIN_CONF_N:
        return "TOO FEW", n1, b, t, m1, m0
    same = (b > 0) == (p["diff"] > 0)
    v = "CONFIRMED" if (same and abs(t) >= T_CONF) else ("WEAK" if same else "FAILED")
    return v, n1, b, t, m1, m0


# ---- 2026-10-10 (Ezio): what else is true when a pocket fires, is it another state in disguise, is it one lucky stretch
PROFILE = ["vol", "atrchg", "vr120", "trendy", "trend60_with", "dist200_with", "n_trending", "spread_R"]
CONTROLS = NUMERIC + ["market", "dir", "hour", "weekday", "risk_on", "usd_up"]


def _profile(trs, ind):
    ins = [r for r, i in zip(trs, ind) if i]
    out = [r for r, i in zip(trs, ind) if not i]

    def mix(rs, key, vals):
        n = float(len(rs)) or 1.0
        return " ".join("%s %2.0f%%" % (v, 100 * sum(1 for r in rs if str(key(r)) == v) / n) for v in vals)
    mk = sorted(set(r["market"] for r in trs))
    lines = []
    for name, rs in (("inside ", ins), ("outside", out)):
        med = []
        for f in PROFILE:
            v = sorted(r["f"][f] for r in rs if r["f"].get(f) is not None)
            med.append("%s %.2f" % (f, v[len(v) // 2]) if v else "%s -" % f)
        lines.append("          %s | %s | %s | %s | medians: %s" % (
            name, mix(rs, lambda r: r["f"]["dir"], ("long", "short")), mix(rs, lambda r: r["market"], mk),
            mix(rs, lambda r: r["era"][-5:], ("14-17", "20-21")), ", ".join(med)))
    return lines


def _controls(trs, ind, diff, cm, defn):
    """Disguise check: within each third / category of every other state, does the pocket still beat the rest? ->
    (worst retained share, worst state, its strata text, strata where the sign holds, strata tested)."""
    used = set(f for f, k in defn)
    y = [r["edge"] for r in trs]
    worst = (None, None, "")
    hold = tested = 0
    for z in CONTROLS:
        if z in used:
            continue
        if z in CATEG or z in ("market", "dir", "hour", "weekday", "risk_on", "usd_up"):
            keyf = lambda r: None if r["f"].get(z) is None else str(r["f"][z])
        else:
            c = cm.get(z)
            if not c:
                continue
            keyf = lambda r, c=c: None if r["f"].get(z) is None else (
                0 if r["f"][z] <= c["q"][0] else (1 if r["f"][z] <= c["q"][1] else 2))
        st = defaultdict(lambda: [0, 0.0, 0, 0.0])
        for r, i, v in zip(trs, ind, y):
            k = keyf(r)
            if k is None:
                continue
            s = st[k]
            if i:
                s[0] += 1; s[1] += v
            else:
                s[2] += 1; s[3] += v
        sw = swd = 0.0
        parts = []
        for k in sorted(st, key=str):
            a = st[k]
            if a[0] < 15 or a[2] < 15:
                continue
            d = a[1] / a[0] - a[3] / a[2]
            w = a[0] * a[2] / float(a[0] + a[2])
            sw += w; swd += w * d
            tested += 1
            hold += (d > 0) == (diff > 0)
            parts.append("%s:%+.2f" % (k, d))
        if sw <= 0:
            continue
        ret = (swd / sw) / diff if diff else 0.0
        if worst[0] is None or ret < worst[0]:
            worst = (ret, z, " ".join(parts))
    return worst[0], worst[1], worst[2], hold, tested


def _concentration(trs, ind, diff):
    """Share of the pocket's excess edge from its best market-year, and the diff without that market-year."""
    y = [r["edge"] for r in trs]
    out_m = [v for v, i in zip(y, ind) if not i]
    m0 = sum(out_m) / len(out_m) if out_m else 0.0
    by = defaultdict(float)
    for r, i, v in zip(trs, ind, y):
        if i:
            by[r["cl"][:-3]] += v - m0                   # 'MARKET|YYYY'
    tot = sum(by.values())
    if not by or tot == 0:
        return None, None, None, None
    sgn = 1 if diff > 0 else -1
    best = max(by, key=lambda k: by[k] * sgn)
    share = by[best] / tot if tot * sgn > 0 else None
    keep = [k for k, r in enumerate(trs) if r["cl"][:-3] != best]
    b, t, _, _ = _diff_t([y[k] for k in keep], [trs[k]["cl"] for k in keep], [ind[k] for k in keep])
    return best, share, b, t


def _shifted(trs, rnd):
    """Circular time shift of each market's state vectors against its own trades (within the half): keeps every
    series' structure, breaks the link between states and outcomes."""
    out = []
    by = defaultdict(list)
    for r in trs:
        by[r["market"]].append(r)
    for mk, rs in by.items():
        n = len(rs)
        if n < 10:
            out += rs
            continue
        k = rnd.randint(max(1, n // 10), max(1, n - n // 10))
        for i, r in enumerate(rs):
            q = dict(r)
            q["f"] = dict(rs[(i + k) % n]["f"])
            q["f"]["market"] = r["f"]["market"]
            out.append(q)
    return out


def _load_table():
    p = os.path.join(_hdir(), "trades.json")
    with open(p) as fh:
        return json.load(fh)


def _def_text(defn, cutmap):
    return "  AND  ".join(_label(f, str(v), cutmap) for f, v in defn)


def _kind(defn):
    ks = [CREATABLE[f] for f, v in defn if f in CREATABLE]
    if not ks:
        return "select-only (half split + yardstick only)"
    if len(ks) == len(defn):
        return "creatable: " + ks[0]
    return "partly creatable: " + ks[0] + " + a select-only state"


def discover():
    tab = _load_table()
    trs = tab["trades"]
    rep = A.Report("hunt_discover")
    p = rep.p
    p("=" * 110)
    p("POCKET HUNT, step 2: DISCOVER on %s ONLY   (table built %s from %s)" % (" + ".join(DISC_ERAS), tab["built"],
                                                                                tab["db"]))
    p("=" * 110)
    p("Protocol: asiabo_hunt.py top. Pocket = a third of one state (cut points from this half) or a category, alone or")
    p("crossed with the momentum axis (%s); thirds, 10%% tails and sign splits, good AND bad pockets. Kept: |t| >= %.1f" %
      (AXIS, T_DISC))
    p("(clustered by market x month), >= %d trades inside and" % MIN_IN)
    p("outside, at most %d per part. diff = edge inside minus edge outside (R per trade, cost-free). The CHECK half is" %
      MAX_PER_PART)
    p("not read here. States: " + ", ".join(NUMERIC + CATEG))
    locked, cuts_all = [], {}
    for part in PARTS:
        d = [r for r in trs if r["part"] == part and r["era"] in DISC_ERAS]
        mu, t = _mean_t([r["edge"] for r in d], [r["cl"] for r in d])
        p("")
        p("-" * 110)
        p("%s: %d discovery trades, edge %s/trade (t %s)" % (part, len(d), "%+.3f" % mu if mu is not None else "-",
                                                            "%+.1f" % t if t is not None else "-"))
        p("-" * 110)
        if len(d) < 2 * MIN_IN:
            p("  too few trades to hunt")
            continue
        pk, cutmap = find_pockets(d)
        cuts_all[part] = cutmap
        for i, q in enumerate(pk):
            pid = "%s-%02d" % (part, i + 1)
            txt = _def_text(q["def"], cutmap)
            p("")
            p("  %s  %s" % (pid, txt))
            p("        in %4d out %4d | edge in %+.3f out %+.3f | diff %+.3f t %+.1f | %s | %s" % (
                q["n_in"], q["n_out"], q["edge_in"], q["edge_out"], q["diff"], q["t"],
                "GOOD pocket (keep the part on)" if q["diff"] > 0 else "BAD pocket (make it harmless)", _kind(q["def"])))
            for line in _profile(d, q["_ind"]):
                p(line)
            ret, wz, wtxt, hold, tested = _controls(d, q["_ind"], q["diff"], cutmap, q["def"])
            flag = ""
            if ret is not None and ret < 0.5:
                flag = "  <-- DISGUISE? controlling for %s leaves %.0f%% of it" % (wz, 100 * ret)
            p("          controls: the sign holds in %d of %d strata of the other states; worst control %s keeps %s%s" % (
                hold, tested, wz or "-", ("%.0f%%" % (100 * ret)) if ret is not None else "-", flag))
            if wz:
                p("          within %s: %s" % (wz, wtxt))
            best, share, bw, tw = _concentration(d, q["_ind"], q["diff"])
            if best:
                p("          concentration: best market-year %s = %s of the pocket's excess; without it diff %s t %s%s" % (
                    best.replace("|", " "), ("%.0f%%" % (100 * share)) if share is not None else "n/a",
                    "%+.3f" % bw if bw is not None else "-", "%+.1f" % tw if tw is not None else "-",
                    "  <-- ONE STRETCH?" if (bw is not None and (bw > 0) != (q["diff"] > 0)) or
                                            (share is not None and share > 0.5) else ""))
            locked.append({"id": pid, "part": part, "def": json.dumps(q["def"]), "text": txt, "n_in": q["n_in"],
                           "edge_in": round(q["edge_in"], 4), "edge_out": round(q["edge_out"], 4),
                           "diff": round(q["diff"], 4), "t": round(q["t"], 2), "kind": _kind(q["def"]),
                           "controls_kept": "" if ret is None else round(ret, 2), "worst_control": wz or "",
                           "best_market_year": (best or "").replace("|", " "),
                           "share_best_my": "" if share is None else round(share, 2),
                           "diff_without_best_my": "" if bw is None else round(bw, 4), "theory": ""})
        if not pk:
            p("  no pocket at |t| >= %.1f" % T_DISC)
    # yardstick: the whole hunt (discover on this half, confirm on the other) on circularly shifted states
    p("")
    p("=" * 110)
    p("YARDSTICK: the same hunt %d times with each market's states circularly shifted against its trades" % NULL_RUNS)
    p("(discover on the discovery half, confirm on the check half; same rules, caps and cut points method)")
    p("=" * 110)
    rnd = random.Random(20261010)
    tot_d, tot_c = [], []
    per_part = defaultdict(list)
    for run in range(NULL_RUNS):
        nd = nc = 0
        for part in PARTS:
            d = [r for r in trs if r["part"] == part and r["era"] in DISC_ERAS]
            c = [r for r in trs if r["part"] == part and r["era"] in CHECK_ERAS]
            if len(d) < 2 * MIN_IN:
                continue
            ds, cs = _shifted(d, rnd), _shifted(c, rnd)
            pk, cm = find_pockets(ds)
            k = sum(1 for q in pk if _confirm_one(cs, q, cm)[0] == "CONFIRMED")
            nd += len(pk)
            nc += k
            per_part[part].append((len(pk), k))
        tot_d.append(nd)
        tot_c.append(nc)
    sd, sc = sorted(tot_d), sorted(tot_c)
    q = lambda s, f: s[min(len(s) - 1, int(f * len(s)))]
    p("  pockets discovered by chance, all parts: median %d, 90th percentile %d   (real: %d)" % (
        q(sd, 0.5), q(sd, 0.9), len(locked)))
    p("  of those, CONFIRMED by chance on the check half: median %d, 90th percentile %d, max %d" % (
        q(sc, 0.5), q(sc, 0.9), sc[-1]))
    for part in PARTS:
        if per_part[part]:
            a = sorted(x[0] for x in per_part[part])
            b = sorted(x[1] for x in per_part[part])
            p("    %-4s discovered median %d (90%%: %d) | confirmed by chance median %d (90%%: %d)" % (
                part, q(a, 0.5), q(a, 0.9), q(b, 0.5), q(b, 0.9)))
    # lock
    path = os.path.join(_hdir(), "pockets_locked.csv")
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["id", "part", "def", "text", "n_in", "edge_in", "edge_out", "diff", "t",
                                           "kind", "controls_kept", "worst_control", "best_market_year",
                                           "share_best_my", "diff_without_best_my", "theory"])
        w.writeheader()
        for r in locked:
            w.writerow(r)
    h = hashlib.sha256(json.dumps([(r["id"], r["part"], r["def"]) for r in locked]).encode()).hexdigest()
    with open(os.path.join(_hdir(), "lock.json"), "w") as fh:
        json.dump({"hash": h, "locked": time.strftime("%Y-%m-%d %H:%M"), "cuts": cuts_all,
                   "null_confirmed": tot_c, "null_discovered": tot_d}, fh)
    p("")
    p("LOCKED %d pockets -> %s (hash %s). Next: Claude writes a theory per pocket into the 'theory' column, then" % (
        len(locked), path, h[:12]))
    p("python asiabo_hunt.py confirm  (the one-shot check on %s)." % " + ".join(CHECK_ERAS))
    rep.save()
    try:
        import shutil
        shutil.copy2(path, os.path.join(A.ROOT, A.VISION_DIR_NAME, "pockets_locked.csv"))
    except Exception as e:
        print("(pockets_locked.csv not copied to claude vision: %s)" % e)


# ================================================================ 4. confirm
def confirm():
    with open(os.path.join(_hdir(), "lock.json")) as fh:
        lock = json.load(fh)
    path = os.path.join(_hdir(), "pockets_locked.csv")
    with open(path, encoding="utf-8") as fh:
        locked = list(csv.DictReader(fh))
    h = hashlib.sha256(json.dumps([(r["id"], r["part"], r["def"]) for r in locked]).encode()).hexdigest()
    rep = A.Report("hunt_confirm")
    p = rep.p
    p("=" * 110)
    p("POCKET HUNT, step 4: the ONE-SHOT CHECK on %s   (pockets locked %s)" % (" + ".join(CHECK_ERAS), lock["locked"]))
    p("=" * 110)
    if h != lock["hash"]:
        p("REFUSED: the pocket definitions changed after the lock (hash %s vs %s)." % (h[:12], lock["hash"][:12]))
        rep.save()
        return
    missing = [r["id"] for r in locked if not r["theory"].strip()]
    if missing:
        p("NOTE: no theory written for %s (the protocol wants one, even 'none'). Run anyway." % ", ".join(missing))
    trs = _load_table()["trades"]
    p("Rules: CONFIRMED = same sign as discovered and clustered t >= %.1f with >= %d trades inside; WEAK = same sign;" %
      (T_CONF, MIN_CONF_N))
    p("FAILED = opposite sign. diff = edge inside minus outside (R/trade). Judge each pocket on its own evidence.")
    nconf = 0
    by = defaultdict(list)
    for r in locked:
        by[r["part"]].append(r)
    for part in PARTS:
        if not by[part]:
            continue
        c = [r for r in trs if r["part"] == part and r["era"] in CHECK_ERAS]
        cutmap = lock["cuts"].get(part, {})
        p("")
        p("-" * 110)
        p("%s: %d check-half trades" % (part, len(c)))
        p("-" * 110)
        for r in by[part]:
            defn = json.loads(r["def"])
            v, n1, b, t, m1, m0 = _confirm_one(c, {"def": defn, "diff": float(r["diff"])}, cutmap)
            nconf += v == "CONFIRMED"
            p("  %s  %-60s discovered diff %+.3f (t %+.1f) | check: in %4d diff %s t %s | %-9s | %s" % (
                r["id"], r["text"][:60], float(r["diff"]), float(r["t"]), n1, "%+.3f" % b if b is not None else "-",
                "%+.1f" % t if t is not None else "-", v, r["kind"]))
            p("        theory: %s" % (r["theory"].strip() or "(none written)"))
            if m1 is not None:
                p("        check half: edge inside %+.3f, outside %+.3f" % (m1, m0))
    nc = sorted(lock["null_confirmed"])
    q = lambda s, f: s[min(len(s) - 1, int(f * len(s)))]
    p("")
    p("CONFIRMED: %d of %d locked pockets. By chance (yardstick, %d shifted hunts): median %d, 90th percentile %d, max %d."
      % (nconf, len(locked), len(nc), q(nc, 0.5), q(nc, 0.9), nc[-1]))
    p("Next for the confirmed pockets on CREATABLE states: the engine's matching dial (ideal / nightmare) as the causal")
    p("check. Select-only pockets stand on this split alone.")
    rep.save()


def main():
    argv = sys.argv[1:]
    if "--db" in argv:
        db = os.path.abspath(argv[argv.index("--db") + 1])
        A.find_db = lambda: db
    cmd = argv[0] if argv and not argv[0].startswith("--") else "discover"
    table = os.path.join(_hdir(), "trades.json")
    if cmd == "build":
        build(table)
    elif cmd == "discover":
        if not os.path.exists(table) or "--rebuild" in argv:
            build(table)
        discover()
    elif cmd == "confirm":
        confirm()
    else:
        raise SystemExit(__doc__)


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
