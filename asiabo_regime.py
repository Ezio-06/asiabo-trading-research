"""
asiabo_regime.py  --  the REGIME ENGINE (2026-10-10): worlds with a KNOWN truth, to answer two questions brute force
(Ezio: "synth serves as a brute-force test that gives us a better idea; we always finalize on real data"):
  1. Can we DETECT a momentum regime fast enough to switch brk / fast on, and which signals see it?
  2. In a momentum spell, how much of the trend do the parts actually CAPTURE (entry lag, giveback)?

WORLDS: make_synth --preset dayshuffle --regime d,d (v6): every market switches at random between MOMENTUM, NEUTRAL and
SNAP-BACK spells of 20-130 trading days, independently. Base = day-shuffled real days (no multi-day structure of its
own), so all persistence is planted and the label is clean. LEAK-FREE: each day keeps its real size, range and shape;
only its DIRECTION is chosen (kept or mirrored) so it goes with the last 20 days' trend with probability 0.5 + d
(momentum), 0.5 - d (snap-back) or 0.5 (neutral). Two strengths: d = 0.15 (subtle) and 0.25 (strong), 3 seeds each.
Volatility, ranges and intraday swings are the same in every state BY CONSTRUCTION (checked in R0), so a detector cannot
cheat on a volatility side effect. Caveat: synth tells what is detectable IF the market works like this model; every
winner still needs one check on real data.

REPORT
  R0  the worlds: per true state, realized 20-day variance ratio, median |daily move| and daily ATR (the leak check)
  R1  each part's edge in each true state (brk, ins, fast, dip, dipx)
  R2  DETECTOR SCORECARD (trailing gauges known at the start of each day): AUC momentum-vs-rest (0.5 = blind),
      and at an operating point that flags as many days as are truly momentum: precision, recall, LAG (days after a
      momentum spell starts until the first flag), share of momentum spells caught in their first half, false switch-ons
      per market-year
  R3  GATING: brk / fast / dip trades with no switch vs the PERFECT switch (true label) vs each detector as the switch:
      trades kept, edge/trade kept, edge/trade of the trades turned away (the 'harmless' side), share of total edge kept
  R4  TREND CAPTURE in momentum spells: the spell's move in daily ATRs vs what brk's trades took out of it; how many days
      until brk first trades in the spell's direction; brk after the spell ends (giveback)
  R5  WHICH OF THE HUNT'S SIGNALS CARRY REGIME INFORMATION: AUC of every hunt state for 'in a momentum spell' at brk's
      entries

    python asiabo_regime.py                  build + measure the worlds not done yet (resumable), then the report
    python asiabo_regime.py --seeds 3 --strengths 0.15,0.25 --workers N
    python asiabo_regime.py report
"""
import os, sys, json, math, time, glob, bisect, sqlite3, traceback
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import asiabo_offline as A

BOOK_MARKETS = ("XAUUSD", "US500", "GERMANY40", "USDJPY")
DETECTORS = ["vr40", "vr60", "vr120", "ac20", "ac40", "ac60", "er10", "er20", "er40", "er60", "tshare60", "follow60",
             "edge20", "er10det"]
DET_TEXT = {
    "vr40": "5-day variance ratio, last 40 days", "vr60": "5-day variance ratio, last 60 days",
    "vr120": "5-day variance ratio, last 120 days", "ac20": "day-to-day autocorrelation, 20 days",
    "ac40": "day-to-day autocorrelation, 40 days", "ac60": "day-to-day autocorrelation, 60 days",
    "er10": "straightness (efficiency ratio), 10 days", "er20": "straightness, 20 days", "er40": "straightness, 40 days",
    "er60": "straightness, 60 days", "tshare60": "share of the last 60 days with 20-day straightness >= 0.3",
    "follow60": "follow-through of 20-day breakouts in the last 60 days (5-day move after the break, ATRs)",
    "edge20": "the lab's edge20 detector is on (either side)", "er10det": "the lab's er10 detector is on (either side)",
}
PARTS = ("brk", "ins", "fast", "dip", "dipx")


# ================================================================ per world
def day_detectors(m):
    """Per FX day j (known at the START of day j; completed days only)."""
    cl, seg, N, nd = m.cl, m.seg, m.N, len(m.D)
    r = [0.0] * nd
    for j in range(1, nd):
        r[j] = math.log(cl[j] / cl[j - 1]) if (seg[j] == seg[j - 1] and cl[j - 1] > 0 and cl[j] > 0) else 0.0
    er20 = [None] * nd
    for j in range(21, nd):
        if j - 21 >= seg[j]:
            path = sum(abs(cl[k] - cl[k - 1]) for k in range(j - 20, j))
            er20[j] = abs(cl[j - 1] - cl[j - 21]) / path if path else 0.0
    brk = []                                         # (day of the break, direction)
    for j in range(21, nd):
        h, l = m.hh(j, 20), m.ll(j, 20)
        if h is None:
            continue
        d = 1 if cl[j] > h else (-1 if cl[j] < l else 0)
        if d:
            brk.append((j, d))
    bdays = [b for b, d in brk]
    out = {}
    for j in range(1, nd):
        if N[j] is None:
            continue
        f = {"t": m.T[m.D[j][1]], "N": N[j], "c": cl[j], "cprev": cl[j - 1]}
        for W in (40, 60, 120):
            if j - W - 1 >= seg[j]:
                rr = r[j - W:j]
                mu = sum(rr) / W
                v1 = sum((x - mu) ** 2 for x in rr) / (W - 1)
                s5 = [sum(rr[i - 5:i]) for i in range(5, W + 1)]
                m5 = sum(s5) / len(s5)
                v5 = sum((x - m5) ** 2 for x in s5) / (len(s5) - 1)
                f["vr%d" % W] = v5 / (5 * v1) if v1 > 0 else None
        for W in (20, 40, 60):
            if j - W - 1 >= seg[j]:
                rr = r[j - W:j]
                mu = sum(rr) / W
                v1 = sum((x - mu) ** 2 for x in rr)
                f["ac%d" % W] = (sum((rr[i] - mu) * (rr[i - 1] - mu) for i in range(1, W)) / v1) if v1 > 0 else None
        for W in (10, 20, 40, 60):
            if j - W - 1 >= seg[j]:
                path = sum(abs(cl[k] - cl[k - 1]) for k in range(j - W, j))
                f["er%d" % W] = abs(cl[j - 1] - cl[j - 1 - W]) / path if path else 0.0
        if j - 60 >= seg[j]:
            xs = [er20[k] for k in range(j - 60, j) if er20[k] is not None]
            if len(xs) >= 40:
                f["tshare60"] = sum(1 for x in xs if x >= 0.3) / float(len(xs))
            lo = bisect.bisect_left(bdays, j - 60)
            hi = bisect.bisect_right(bdays, j - 6)
            fl = [d * (cl[b + 5] - cl[b]) / N[b] for b, d in brk[lo:hi] if N[b] and m.seg[b + 5] == m.seg[b]]
            if len(fl) >= 3:
                f["follow60"] = sum(fl) / len(fl)
        dd = m.det[j] or {}
        if "edge20" in dd:
            f["edge20"] = 1.0 if dd["edge20"] else 0.0
        if "er10" in dd:
            f["er10det"] = 1.0 if dd["er10"] else 0.0
        out[str(m.D[j][0])] = f
    return out


def measure(db, out_path):
    import asiabo_hunt as Hh
    A.find_db = lambda: db
    tmp = out_path + ".table.json"
    Hh.build(tmp, day_hook=day_detectors)
    with open(tmp) as fh:
        tab = json.load(fh)
    os.remove(tmp)
    con = sqlite3.connect(db)
    spells = defaultdict(list)
    for s, t0, t1, st, a in con.execute("select symbol, t0, t1, state, a from regime"):
        spells[s].append((t0, t1, st))
    meta = dict(con.execute("select key, value from synth_meta"))
    con.close()
    for s in spells:
        spells[s].sort()
    starts = dict((s, [x[0] for x in v]) for s, v in spells.items())

    def state(s, t):
        k = bisect.bisect_right(starts.get(s, []), t) - 1
        if k < 0:
            return None
        a, b, st = spells[s][k]
        return st if t < b else None
    for r in tab["trades"]:
        r["state"] = state(r["market"], r["t_in"])
    for s, days in tab["days"].items():
        for k, f in days.items():
            f["state"] = state(s, f["t"])
    out = {"meta": meta, "trades": tab["trades"], "days": tab["days"],
           "spells": dict((s, v) for s, v in spells.items())}
    with open(out_path + ".tmp", "w") as fh:
        json.dump(out, fh)
    os.replace(out_path + ".tmp", out_path)
    print("regime: measured %d trades -> %s" % (len(tab["trades"]), out_path))


# ================================================================ many worlds
def _wdir():
    return os.path.join(A.ROOT, "reports", "regime", "worlds")


def run(seeds, strengths, workers):
    import synth_batch as SB
    import threading
    from concurrent.futures import ThreadPoolExecutor, as_completed
    os.makedirs(_wdir(), exist_ok=True)
    os.makedirs(os.path.join(A.ROOT, "synth"), exist_ok=True)
    logp = os.path.join(A.ROOT, "reports", "regime", "regime_log.txt")

    def log(s):
        print(s)
        with open(logp, "a", encoding="utf-8") as f:
            f.write(s + "\n")
    jobs = [(d, sd) for d in strengths for sd in range(1, seeds + 1)]
    todo = [(d, sd) for d, sd in jobs if not os.path.exists(os.path.join(_wdir(), "d%s_s%d.json" % (d, sd)))]
    log("")
    log("regime engine %s: %d worlds, %d to build" % (time.strftime("%Y-%m-%d %H:%M"), len(jobs), len(todo)))
    py = sys.executable
    if todo:
        buf = []
        SB._run([py, os.path.join(HERE, "make_synth.py"), "cache"], buf)
        for line in buf:
            log(line)
        nw = workers if workers else SB.auto_workers(log)
        lock = threading.Lock()
        cnt = [0]

        def one(d, sd):
            buf = []
            tmp = os.path.join(A.ROOT, "synth", "reg_d%s_s%d.db" % (d, sd))
            out = os.path.join(_wdir(), "d%s_s%d.json" % (d, sd))
            try:
                if os.path.exists(tmp):
                    os.remove(tmp)
                ok, _ = SB._run([py, os.path.join(HERE, "make_synth.py"), "gen", "--preset", "dayshuffle", "--regime",
                                 "%s,%s" % (d, d), "--markets", ",".join(BOOK_MARKETS), "--seed", str(sd), "--out",
                                 tmp], buf)
                if ok:
                    ok, _ = SB._run([py, os.path.join(HERE, "asiabo_regime.py"), "measure", "--db", tmp, "--out", out],
                                    buf)
            finally:
                try:
                    if os.path.exists(tmp):
                        os.remove(tmp)
                except OSError as e:
                    buf.append("    (could not delete %s: %s)" % (tmp, e))
            with lock:
                cnt[0] += 1
                buf.insert(0, "[%d/%d] strength %s seed %d: %s" % (cnt[0], len(todo), d, sd, "ok" if ok else "FAILED"))
                for line in buf:
                    log(line)
        with ThreadPoolExecutor(max_workers=nw) as ex:
            fs = []
            for d, sd in todo:
                fs.append(ex.submit(one, d, sd))
                time.sleep(2)
            for f in as_completed(fs):
                f.result()
    report()


# ================================================================ report
def _mean_t(vals):
    """vals [(value, cluster)] -> (n, mean, clustered t)"""
    n = len(vals)
    if n < 2:
        return n, None, None
    mu = sum(v for v, c in vals) / n
    g = defaultdict(float)
    for v, c in vals:
        g[c] += v - mu
    k = len(g)
    if k < 2:
        return n, mu, None
    var = sum(e * e for e in g.values()) * k / (k - 1.0) / (n * n)
    return n, mu, (mu / math.sqrt(var) if var > 0 else None)


def _auc(pos, neg):
    """P(a random positive scores above a random negative); ties = 1/2."""
    if not pos or not neg:
        return None
    allv = sorted([(v, 1) for v in pos] + [(v, 0) for v in neg])
    rank_sum, i, n = 0.0, 0, len(allv)
    while i < n:
        j = i
        while j + 1 < n and allv[j + 1][0] == allv[i][0]:
            j += 1
        avg = (i + j) / 2.0 + 1.0
        rank_sum += avg * sum(1 for q in range(i, j + 1) if allv[q][1] == 1)
        i = j + 1
    np_, nn = len(pos), len(neg)
    return (rank_sum - np_ * (np_ + 1) / 2.0) / (np_ * nn)


def _f(v, w=6, p=3):
    return ("%+*.*f" % (w, p, v)) if v is not None else "%*s" % (w, "-")


def report():
    rep = A.Report("regime")
    p = rep.p
    files = sorted(glob.glob(os.path.join(_wdir(), "d*_s*.json")))
    worlds = defaultdict(list)
    for fp in files:
        name = os.path.basename(fp)[:-5]
        d = name.split("_s")[0][1:]
        with open(fp) as fh:
            w = json.load(fh)
        w["_name"] = name
        worlds[d].append(w)
    p("=" * 110)
    p("REGIME ENGINE: worlds with a KNOWN momentum / neutral / snap-back truth   (%s)" % time.strftime("%Y-%m-%d %H:%M"))
    p("=" * 110)
    p("Base = day-shuffled real days; every market switches between spells of 20-130 days; LEAK-FREE dial (each day keeps")
    p("its size, range and shape; only its direction is chosen). Strength d = how much more often a day goes WITH (momentum)")
    p("or AGAINST (snap-back) its last 20 days. Worlds: " + ", ".join("d=%s: %d" % (d, len(v)) for d, v in sorted(worlds.items())))
    p("Synth shows what is detectable IF the market works like this model; winners still need one check on real data.")
    for d in sorted(worlds):
        ws = worlds[d]
        p("")
        p("#" * 110)
        p("STRENGTH d = %s   (%d worlds)" % (d, len(ws)))
        p("#" * 110)
        days = []                                       # (world, market, day dict)
        for w in ws:
            for mk, dd in w["days"].items():
                ks = sorted(dd, key=lambda k: dd[k]["t"])
                for k in ks:
                    days.append((w["_name"], mk, dd[k]))
        trades = [(w["_name"], r) for w in ws for r in w["trades"] if r.get("state")]
        # R0
        p("")
        p("R0. THE WORLDS by true state: days | realized 20-day variance ratio | median |daily move| | median daily ATR "
          "(% of price)")
        p("    The dial keeps every day's size exactly (verified against the base world day by day, 2026-10-10); size")
        p("    differences between states here come only from WHICH base days landed in which spells (chance, shrinks")
        p("    with more seeds). The variance ratio is what the dial changes.")
        for st in ("mom", "none", "snap"):
            seq = defaultdict(list)
            for wn, mk, f in days:
                seq[(wn, mk)].append(f)
            r1, r20, mv, atr = [], [], [], []
            for key, fs in seq.items():
                for i in range(1, len(fs)):
                    if fs[i]["state"] == st and fs[i - 1]["state"] == st and fs[i]["t"] - fs[i - 1]["t"] < 5 * 86400:
                        x = math.log(fs[i]["c"] / fs[i - 1]["c"])
                        r1.append(x)
                        mv.append(abs(x))
                        atr.append(fs[i]["N"] / fs[i]["c"])
                for i in range(20, len(fs)):
                    if all(fs[q]["state"] == st for q in range(i - 20, i + 1)) and fs[i]["t"] - fs[i - 20]["t"] < 40 * 86400:
                        r20.append(math.log(fs[i]["c"] / fs[i - 20]["c"]))
            if not r1:
                continue
            v1 = sum(x * x for x in r1) / len(r1)
            v20 = sum(x * x for x in r20) / len(r20) if r20 else float("nan")
            mv.sort(); atr.sort()
            p("    %-5s days %6d | VR20 %4.2f | median |move| %.3f%% | median ATR %.3f%%" % (
                st, len(r1), v20 / (20 * v1), 100 * mv[len(mv) // 2], 100 * atr[len(atr) // 2]))
        # R1
        p("")
        p("R1. EACH PART'S EDGE by true state at entry (edge/trade (n, t clustered by world x market x month))")
        for part in PARTS:
            line = "    %-5s" % part
            for st in ("mom", "none", "snap"):
                n, mu, t = _mean_t([(r["edge"], wn + r["cl"]) for wn, r in trades if r["part"] == part and r["state"] == st])
                line += " | %s %s (%d, t %s)" % (st, _f(mu), n, "%+.1f" % t if t is not None else "-")
            p(line)
        # R2
        p("")
        p("R2. DETECTOR SCORECARD (known at the start of each day). AUC = chance a momentum day scores above a non-momentum")
        p("    day (0.5 = blind, 1 = perfect). Operating point: the threshold that flags as many days as are truly momentum.")
        p("    lag = median days from a momentum spell's start to the detector's first flag inside it; caught = share of")
        p("    momentum spells flagged within their first half; false on/yr = switch-ons during non-momentum spells per")
        p("    market-year. AUC snap = the same for snap-back days (below 0.5 = it reads snap-back as 'not trending').")
        share_mom = sum(1 for wn, mk, f in days if f["state"] == "mom") / float(max(1, sum(1 for x in days if x[2]["state"])))
        thr = {}
        rows = []
        for dn in DETECTORS:
            vals = [f.get(dn) for wn, mk, f in days if f.get(dn) is not None and f["state"]]
            if len(vals) < 100:
                continue
            pos = [f[dn] for wn, mk, f in days if f.get(dn) is not None and f["state"] == "mom"]
            neg = [f[dn] for wn, mk, f in days if f.get(dn) is not None and f["state"] in ("none", "snap")]
            snp = [f[dn] for wn, mk, f in days if f.get(dn) is not None and f["state"] == "snap"]
            nsn = [f[dn] for wn, mk, f in days if f.get(dn) is not None and f["state"] in ("none", "mom")]
            auc = _auc(pos, neg)
            aucs = _auc(snp, nsn)
            sv = sorted(vals)
            th = 0.5 if len(set(sv)) <= 2 else sv[min(len(sv) - 1, int((1 - share_mom) * len(sv)))]
            thr[dn] = th
            flag = lambda f: f.get(dn) is not None and f[dn] > th
            tp = sum(1 for wn, mk, f in days if f["state"] == "mom" and flag(f))
            fp = sum(1 for wn, mk, f in days if f["state"] in ("none", "snap") and flag(f))
            fn = sum(1 for wn, mk, f in days if f["state"] == "mom" and f.get(dn) is not None and not flag(f))
            lags, caught, spells_n, false_on, yrs = [], 0, 0, 0, 0.0
            seq = defaultdict(list)
            for wn, mk, f in days:
                seq[(wn, mk)].append(f)
            for key, fs in seq.items():
                yrs += len(fs) / 252.0
                i = 0
                prev_flag = False
                while i < len(fs):
                    st = fs[i]["state"]
                    j = i
                    while j + 1 < len(fs) and fs[j + 1]["state"] == st:
                        j += 1
                    if st == "mom" and j - i >= 10:
                        spells_n += 1
                        first = next((q - i for q in range(i, j + 1) if flag(fs[q])), None)
                        if first is not None:
                            lags.append(first)
                            if first <= (j - i) / 2:
                                caught += 1
                    for q in range(i, j + 1):
                        fl = flag(fs[q])
                        if st != "mom" and fl and not prev_flag:
                            false_on += 1
                        prev_flag = fl
                    i = j + 1
            lags.sort()
            rows.append((auc or 0, dn, auc, aucs, tp / float(max(1, tp + fp)), tp / float(max(1, tp + fn)),
                         lags[len(lags) // 2] if lags else None, caught / float(max(1, spells_n)), false_on / max(1e-9, yrs),
                         th))
        rows.sort(reverse=True)
        p("    %-9s %-62s %5s %6s %5s %5s %5s %6s %7s %8s" % ("detector", "", "AUC", "AUCsnp", "prec", "recl", "lag", "caught",
                                                             "falseon", "thresh"))
        for _, dn, auc, aucs, prec, recl, lag, cg, fo, th in rows:
            p("    %-9s %-62s %5.3f %6.3f %5.2f %5.2f %5s %5.0f%% %7.1f %8.3g" % (
                dn, DET_TEXT[dn][:62], auc, aucs if aucs is not None else float("nan"), prec, recl,
                "%d" % lag if lag is not None else "-", 100 * cg, fo, th))
        p("    (base rate: %.0f%% of days are momentum days; precision above that = information)" % (100 * share_mom))
        # R3
        p("")
        p("R3. GATING: trade only when the switch says 'momentum' (the detector on the trade's entry day above its R2")
        p("    threshold). kept = trades kept; edge kept / turned away = edge per trade of the kept / rejected trades;")
        p("    share = share of the total edge kept. 'perfect' = the true label (the upper bound); 'not snap' = the true")
        p("    label, skipping only snap-back spells.")
        dayix = {}
        for w in ws:
            for mk, dd in w["days"].items():
                for k, f in dd.items():
                    dayix[(w["_name"], mk, str(k))] = f
        for part in ("brk", "fast", "dip", "dipx"):
            rs = [(wn, r) for wn, r in trades if r["part"] == part]
            if not rs:
                continue
            tot = sum(r["edge"] for wn, r in rs)
            p("    %s: %d trades, edge/trade %+.3f, total edge %+.0f R" % (part, len(rs), tot / len(rs), tot))
            gates = [("perfect", lambda wn, r: r["state"] == "mom"), ("not snap", lambda wn, r: r["state"] != "snap")]
            for _, dn, *rest in rows[:6]:
                gates.append((dn, (lambda dn: lambda wn, r: (dayix.get((wn, r["market"], str(r["dk"]))) or {}).get(dn)
                                   is not None and dayix[(wn, r["market"], str(r["dk"]))][dn] > thr[dn])(dn)))
            for gn, g in gates:
                kept = [(r["edge"], wn + r["cl"]) for wn, r in rs if g(wn, r)]
                away = [(r["edge"], wn + r["cl"]) for wn, r in rs if not g(wn, r)]
                nk, mk_, tk = _mean_t(kept)
                na, ma, ta = _mean_t(away)
                p("      %-9s kept %5d (%3.0f%%) edge %s (t %s) | turned away %5d edge %s | share of edge kept %s" % (
                    gn, nk, 100.0 * nk / len(rs), _f(mk_), "%+.1f" % tk if tk is not None else "-", na, _f(ma),
                    ("%4.0f%%" % (100 * sum(v for v, c in kept) / tot)) if tot else "-"))
        # R4
        p("")
        p("R4. TREND CAPTURE in momentum spells (brk): per spell and market, the spell's net move in daily ATRs, what brk's")
        p("    trades entered inside the spell took out of it (gross move in ATRs, both directions), days until brk's first")
        p("    trade in the spell's direction, and brk's edge in the 20 days after the spell ended (giveback).")
        cap, lag1, after, moves = [], [], [], []
        for w in ws:
            for mk, sps in w["spells"].items():
                dd = sorted(w["days"].get(mk, {}).values(), key=lambda f: f["t"])
                ts = [f["t"] for f in dd]
                br = sorted([r for r in w["trades"] if r["part"] == "brk" and r["market"] == mk], key=lambda r: r["t_in"])
                for t0, t1, st in sps:
                    if st != "mom":
                        continue
                    i0, i1 = bisect.bisect_left(ts, t0), bisect.bisect_left(ts, t1) - 1
                    if i1 - i0 < 10:
                        continue
                    natr = sum(dd[q]["N"] for q in range(i0, i1 + 1)) / (i1 - i0 + 1)
                    move = (dd[i1]["c"] - dd[i0]["cprev"]) / natr
                    sgn = 1 if move > 0 else -1
                    ins = [r for r in br if t0 <= r["t_in"] < t1]
                    took = sum(r["gross"] * (r["f"].get("risk_size") or 0) for r in ins)
                    moves.append(abs(move))
                    cap.append((took, abs(move)))
                    firsts = [r for r in ins if (1 if r["f"]["dir"] == "long" else -1) == sgn]
                    if firsts:
                        lag1.append((firsts[0]["t_in"] - t0) / 86400.0)
                    after += [(r["edge"], w["_name"] + r["cl"]) for r in br if t1 <= r["t_in"] < t1 + 28 * 86400]
        if cap:
            tm, tt_ = sum(c for c, m in cap), sum(m for c, m in cap)
            moves.sort(); lag1.sort()
            p("    momentum spells: %d | median |move| %.1f ATR | brk took %+.0f of %.0f ATR in total (%.0f%%) | median "
              "calendar days to brk's first trade in the spell's direction %s" % (
                  len(cap), moves[len(moves) // 2], tm, tt_, 100 * tm / tt_ if tt_ else 0,
                  "%.0f" % lag1[len(lag1) // 2] if lag1 else "-"))
            n, mu, t = _mean_t(after)
            p("    brk in the 4 weeks after a momentum spell ended: %d trades, edge %s (t %s)" % (
                n, _f(mu), "%+.1f" % t if t is not None else "-"))
        # R5
        p("")
        p("R5. WHICH HUNT SIGNALS CARRY REGIME INFORMATION: AUC of each state at brk's entries for 'inside a momentum spell'")
        p("    (|AUC - 0.5| = information; below 0.5 = high values point AWAY from momentum)")
        import asiabo_hunt as Hh
        br = [r for wn, r in trades if r["part"] == "brk"]
        res = []
        for fn in Hh.NUMERIC:
            pos = [r["f"][fn] for r in br if r["f"].get(fn) is not None and r["state"] == "mom"]
            neg = [r["f"][fn] for r in br if r["f"].get(fn) is not None and r["state"] != "mom"]
            a = _auc(pos, neg)
            if a is not None:
                res.append((abs(a - 0.5), fn, a))
        res.sort(reverse=True)
        for _, fn, a in res:
            p("    %-14s AUC %.3f   %s" % (fn, a, Hh.DESC.get(fn, "")))
    rep.save()


def main():
    argv = sys.argv[1:]
    if argv and argv[0] == "measure":
        db = os.path.abspath(argv[argv.index("--db") + 1])
        out = os.path.abspath(argv[argv.index("--out") + 1])
        measure(db, out)
        return
    if argv and argv[0] == "report":
        report()
        return
    seeds, strengths, workers = 3, ["0.15", "0.25"], 0
    i = 0
    while i < len(argv):
        if argv[i] == "--seeds":
            seeds = int(argv[i + 1]); i += 2
        elif argv[i] == "--strengths":
            strengths = argv[i + 1].split(","); i += 2
        elif argv[i] == "--workers":
            workers = int(argv[i + 1]); i += 2
        else:
            raise SystemExit(__doc__)
    run(seeds, strengths, workers)


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
