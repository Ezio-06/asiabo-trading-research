#!/usr/bin/env python3
"""
asiabo_dipdrift.py  --  dip + drift sizing on US Tech 100 (Ezio's design, pre-registered 2026-10-13).
Rules + predictions: dip_drift_spec.md (project). SHADOW ONLY: it measures, it decides nothing, changes no other file.

    python asiabo_dipdrift.py              THE TEST. ONE run: refuses to run again once exam_hold\\DIPDRIFT_DONE.txt exists.
    test options (cloud only): --hold <folder>  --nomark  --force
                               --check <bars.db> <MARKET>   variant A on spent data vs the why phase's own dip book

WHAT IT READS
  The never-touched US TECH 100 M1 exports in exam_hold\\ (all of them, 2015-12 -> 2026-10). bars.db is NEVER read or
  changed: the test builds its own exam_hold\\ustech100.db. That db holds only US Tech 100, so the 2022-23 seal (which
  protects the six house markets) is lifted for it: the 2022 bear market is the point of the test.

US TECH 100 MARKET SPEC = a TRANSLATION of US500's, fixed before any run: New York clock and session, cost in basis
  points and recorded spreads as US500, swap and min stop in index points scaled x4 (US Tech 100 trades at ~4x the
  US500's points).

THE FOUR VARIANTS (same dip triggers and exits for all; long only; risk unit 1N; 3N disaster stop; real costs)
  triggers: rsi2 = RSI(2) < 10 at the day's close; dip3 = 3 lower closes.  exits: rsi2 out at the next open after a
  close above the 5-day average (cap 20 days); dip3 out on the first close above the prior day's high or after 10 days.
  A  dip as it is        filter: close > 200-day average     entry: next open
  B  + confirmation      filter: 200-day                     entry: close of the first 1-hour bar (within the next
                                                                    trading day) that closes above the prior hour's high
  C  + table             filter/size: Ezio's table           entry: next open
  D  Ezio's full design  table + 1-hour confirmation
  TABLE (index's own daily closes at the signal day; Q = vs 63 days ago, Y = vs 252 days ago, F = 100-day average):
     Q up & Y up -> 1;  Q up & Y down & above F -> 1;  Q up & Y down & below F -> 0.25;
     Q down & above F -> 0.5;  Q down & below F -> 0.  (Floor = 100-day: it flips 3x less than the 50-day on spent data.)
  One position at a time for the dip part (rsi2 + dip3 together), as in the book.

VERDICT (pre-registered, bars set on noise): D WINS if sized R beats A's by > 13 R AND drawdown not worse; SAFER if
  drawdown smaller by > 9 R and sized R at most 25% below A's; LOSES if sized R below A's by > 13 R; else INSIDE THE NOISE.  dip itself on a fresh index (A): PASS if net > +0.15 R/trade and EDGE > 0
  (the US500 exam's bars).
PREDICTIONS (Claude, 2026-10-13): A PASS more likely than not; D trades more than A, gains in 2020, loses some in the
  2022 bear-market rallies, 2022 worse than A; B ~ A; overall INSIDE THE NOISE most likely (revised after the noise
  runs showed D-A swings of +-12 R by chance, before any real data).  Ezio: see the spec.
"""
import os, sys, math, time, sqlite3, traceback, bisect
from pathlib import Path
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import asiabo_offline as A

MKT = "USTECH100"
EXAM_GLOB = "US TECH 100_m1_*"
VARIANTS = ("A", "B", "C", "D")
VNAME = {"A": "A  dip as it is (200-day, next open)", "B": "B  + 1-hour confirmation",
         "C": "C  + Ezio's table (no 200-day)", "D": "D  Ezio's full design (table + confirmation)"}
WIN_BAR = 13.0     # sized R: above every D-A gap on 10 drift random walks (-10.7 .. +12.5)
SAFE_BAR = 9.0     # drawdown: beyond every D-A drawdown gap on noise (-8.6 .. +4.5)
YARD = "\n".join([
    "YARDSTICK (10 fake US Tech 100 random walks WITH index-like drift + 2 without, 2026-10-13, BEFORE the test):",
    "    D - A sized R ranged -10.7 .. +12.5 and the drawdown gap -8.6 .. +4.5 on pure noise. With the first rule",
    "    ('D >= A and drawdown <= A') noise 'WON' 5 of 10 times, so the bars were set above every noise run:",
    "    WINS needs D - A > +13 R; SAFER needs a drawdown cut of more than 9 R. A on noise: net -0.31 .. +0.13, never PASS.",
    "    Power: about 100 trades over 9 years; only a large difference between D and A can show."])


# ================================================================ market spec (translation of US500)
def register_spec():
    import asiabo_lab as L
    base = dict((x["name"], x) for x in A.COLLECT_SYMBOLS)["US500"]
    if MKT not in [x["name"] for x in A.COLLECT_SYMBOLS]:
        sp = dict(base)
        sp.update({"name": MKT, "match": ["USTECH100", "US100", "NAS100", "USTEC", "NDX100"],
                   "swap_long": base["swap_long"] * 4, "swap_short": base["swap_short"] * 4,
                   "min_sl": base.get("min_sl", 3.0) * 4, "xref": ["US500"]})
        A.COLLECT_SYMBOLS.append(sp)
    for mod in (L, A):
        for k, v in list(vars(mod).items()):
            if isinstance(v, dict) and "US500" in v and MKT not in v and not k.startswith("__"):
                try:
                    v[MKT] = v["US500"]
                except TypeError:
                    pass
    return dict((x["name"], x) for x in A.COLLECT_SYMBOLS)[MKT]


# ================================================================ the test database
def build_db(files, out_db, p):
    import build_bars_db as BB
    tmp = out_db + ".building"
    if os.path.exists(tmp):
        os.remove(tmp)
    con = sqlite3.connect(tmp)
    con.execute("PRAGMA journal_mode=OFF")
    cur = con.cursor()
    cur.execute("""CREATE TABLE bars_m1 (symbol TEXT, ts INTEGER, time_utc TEXT, open REAL, high REAL,
                   low REAL, close REAL, volume REAL, spread_avg REAL, spread_max REAL, ticks INTEGER,
                   PRIMARY KEY (symbol, ts)) WITHOUT ROWID""")
    cur.execute("""CREATE TABLE runs (file TEXT, symbol TEXT, broker TEXT, digits TEXT, pip_size TEXT,
                   tick_size TEXT, start TEXT, version TEXT, bars INTEGER, first_bar TEXT, last_bar TEXT,
                   complete INTEGER)""")
    cur.execute("CREATE TABLE gaps (symbol TEXT, after_bar TEXT, next_bar TEXT, missing_minutes INTEGER, kind TEXT, note TEXT)")
    cur.execute("""CREATE TEMP TABLE stage (ts INTEGER, time_utc TEXT, open REAL, high REAL, low REAL, close REAL,
                   volume REAL, spread_avg REAL, spread_max REAL, ticks INTEGER)""")
    syms = set()
    for f in files:
        meta, end, n, bad, ooo, ticks, first, last = BB.stage_file(cur, Path(f))
        sym = meta.get("symbol")
        if not n or not sym:
            raise RuntimeError("no META / no bars in %s" % f)
        complete = end is not None and int(end.get("bars", -1)) == n + bad
        cur.execute("INSERT OR IGNORE INTO bars_m1 SELECT ?, ts, time_utc, open, high, low, close, volume, spread_avg, "
                    "spread_max, ticks FROM stage ORDER BY rowid", (sym,))
        cur.execute("INSERT INTO runs VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                    (os.path.basename(f), sym, meta.get("broker"), meta.get("digits"), meta.get("pip_size"),
                     meta.get("tick_size"), meta.get("start"), meta.get("version"), n, first, last, int(complete)))
        p("file: %s  (%d bars, %d malformed, %d out of order, complete=%s, %s .. %s)"
          % (os.path.basename(f), n, bad, ooo, complete, first, last))
        syms.add(sym)
    cur.execute("DROP TABLE stage")
    con.commit()
    k0 = len(BB._LOG)
    for s in sorted(syms):
        BB.report_symbol(con, s)
    con.commit()
    con.close()
    os.replace(tmp, out_db)
    p("")
    p("DATA COVERAGE (printed BEFORE any result; exam lesson 2026-10-13):")
    for line in BB._LOG[k0:]:
        if line.startswith("year") or line[:2] in ("20", "  ") or line.startswith("===") or "#" in line:
            p("   " + line)


# ================================================================ dip, all four variants on one engine
def table_size(m, j):
    c = m.cl
    if j < 252 or m.sma(j, 100) is None:
        return None
    q_up = c[j] > c[j - 63]
    y_up = c[j] > c[j - 252]
    above = c[j] > m.sma(j, 100)
    if q_up and y_up:
        return 1.0
    if q_up and above:
        return 1.0
    if q_up:
        return 0.25
    return 0.5 if above else 0.0


def confirm_entry(m, j):
    """first 1-hour bar of trading day j+1 that closes above the previous hour's high -> (bar index of its last M15
    bar, close price), or None."""
    if j + 1 >= len(m.D):
        return None
    i0, i1 = m.D[j + 1][1], m.D[j + 1][2]
    lo = max(0, i0 - 8)
    hours = []                                  # [hour key, high, close, last index]
    for i in range(lo, i1 + 1):
        h = int(m.T[i] // 3600)
        if hours and hours[-1][0] == h:
            hours[-1][1] = max(hours[-1][1], m.H[i])
            hours[-1][2] = m.C[i]
            hours[-1][3] = i
        else:
            hours.append([h, m.H[i], m.C[i], i])
    for a in range(1, len(hours)):
        prev, cur = hours[a - 1], hours[a]
        if cur[3] < i0 or cur[0] - prev[0] > 2:
            continue
        # the hour must be complete inside day j+1 and not the day's last bar
        if cur[2] > prev[1] and cur[3] + 1 < m.n and cur[3] < i1:
            return cur[3], cur[2]
    return None


def walk_rsi2(L, m, k0, entry, N):
    return L._p_rsi_walk(m, k0, entry, 1, N)


def walk_dip3(L, m, k0, entry, N):
    d = 1
    stop = entry - 3 * N
    for k in range(k0, m.n):
        if k > k0 and m.T[k] - m.T[k - 1] > L.P_MAX_GAP:
            return None, None, k
        o, l = m.O[k], m.L[k]
        px = None
        if l <= stop:
            px = o if (o <= stop and k > k0) else stop
        if px is None and k == m.D[m.di[k]][2] and k + 1 < m.n:
            dk = m.di[k]
            if m.C[k] > m.hi[dk - 1] or dk - m.di[k0] >= 10:
                px, k = m.O[k + 1], k + 1
        if px is not None:
            t_in, t_out = m.T[k0], m.T[k] + 900
            if m.dq.overlaps(t_in, t_out):
                return None, None, k
            g = px - entry
            cst = m.cost(k0, entry)
            return g - cst + m.swap(1, t_in, t_out), g, k, (-g - cst + m.swap(-1, t_in, t_out))
    return None, None, m.n


def dip_trades(L, m, var):
    """-> list of dicts (one position at a time across rsi2 + dip3)."""
    use_table = var in ("C", "D")
    confirm = var in ("B", "D")
    cand = []
    for lane in ("rsi2", "dip3"):
        busy = -1
        for j, i0, i1 in L.p_days(m):
            if i1 + 1 >= m.n or i1 + 1 <= busy or j < 4:
                continue
            c = m.cl
            if lane == "rsi2":
                r = m.rsi2[j]
                trig = r is not None and r < 10
            else:
                trig = c[j] < c[j - 1] < c[j - 2] < c[j - 3]
            if not trig:
                continue
            if use_table:
                size = table_size(m, j)
                if not size:
                    continue
            else:
                s200 = m.sma(j, 200)
                if s200 is None or not c[j] > s200:
                    continue
                size = 1.0
            N = m.N[j]
            if confirm:
                ce = confirm_entry(m, j)
                if ce is None:
                    continue
                k0, entry = ce[0] + 1, ce[1]
            else:
                k0, entry = i1 + 1, m.O[i1 + 1]
            ex = (walk_rsi2 if lane == "rsi2" else walk_dip3)(L, m, k0, entry, N)
            busy = ex[2]
            if ex[0] is None:
                continue
            ra, rb = ex[0] / N, ex[3] / N
            cand.append({"lane": lane, "t_in": m.T[k0], "t_out": m.T[min(ex[2], m.n - 1)] + 900, "R": ra,
                         "edge": ra - (ra + rb) / 2.0, "size": size, "j": j})
    cand.sort(key=lambda x: (x["t_in"], x["lane"]))
    out, free = [], -1.0
    for x in cand:
        if x["t_in"] < free:
            continue
        out.append(x)
        free = x["t_out"]
    return out


# ================================================================ report
def stats(xs, w0=None, w1=None):
    if w0 is not None:
        xs = [x for x in xs if w0 <= x["t_in"] < w1]
    if not xs:
        return None
    n = len(xs)
    sized = [x["R"] * x["size"] for x in xs]
    cum, peak, dd = 0.0, 0.0, 0.0
    for x in sorted(xs, key=lambda x: x["t_out"]):
        cum += x["R"] * x["size"]
        peak = max(peak, cum)
        dd = max(dd, peak - cum)
    q = defaultdict(float)
    for x in xs:
        tt = time.gmtime(x["t_in"])
        q[(tt.tm_year, (tt.tm_mon - 1) // 3 + 1)] += x["R"] * x["size"]
    wq = min(q.items(), key=lambda kv: kv[1]) if q else None
    tiers = defaultdict(int)
    for x in xs:
        tiers[x["size"]] += 1
    return {"n": n, "sum": sum(sized), "net": sum(x["R"] for x in xs) / n, "edge": sum(x["edge"] for x in xs) / n,
            "win": 100.0 * sum(1 for x in xs if x["R"] > 0) / n, "dd": dd, "wq": wq, "tiers": dict(tiers)}


def year_sum(xs, y):
    return sum(x["R"] * x["size"] for x in xs if time.gmtime(x["t_in"]).tm_year == y)


def report(p, res, years):
    p("")
    p("%-44s %5s %6s %8s %8s %7s %8s %9s  %s" % ("variant", "n", "win", "net/tr", "EDGE/tr", "sizedR", "maxDD",
                                                "worst Q", "trades per size (1 / .5 / .25)"))
    S = {}
    for v in VARIANTS:
        st = stats(res[v])
        S[v] = st
        if not st:
            p("%-44s     0" % VNAME[v])
            continue
        wq = "%d-Q%d %+.1f" % (st["wq"][0][0], st["wq"][0][1], st["wq"][1]) if st["wq"] else "-"
        p("%-44s %5d %5.0f%% %+8.3f %+8.3f %+7.1f %8.1f %13s  %d / %d / %d" % (
            VNAME[v], st["n"], st["win"], st["net"], st["edge"], st["sum"], st["dd"], wq,
            st["tiers"].get(1.0, 0), st["tiers"].get(0.5, 0), st["tiers"].get(0.25, 0)))
    p("")
    p("sized R by year:   " + "  ".join("%d" % y for y in years))
    for v in VARIANTS:
        p("   %s  %s" % (v, "  ".join("%+5.1f" % year_sum(res[v], y) for y in years)))
    return S


def verdicts(p, S):
    a, d = S.get("A"), S.get("D")
    p("")
    if a:
        va = "PASS" if (a["net"] > 0.15 and a["edge"] > 0) else ("FAIL" if (a["net"] < 0 and a["edge"] < 0) else "MIXED")
    else:
        va = "NO TRADES"
    if not a or not d:
        vd = "UNREADABLE (no trades)"
    elif d["sum"] - a["sum"] > WIN_BAR and d["dd"] <= a["dd"]:
        vd = "WINS"
    elif a["dd"] - d["dd"] > SAFE_BAR and d["sum"] >= a["sum"] - 0.25 * abs(a["sum"]):
        vd = "SAFER"
    elif a["sum"] - d["sum"] > WIN_BAR:
        vd = "LOSES"
    else:
        vd = "INSIDE THE NOISE"
    if a and d:
        ea = a["sum"] / a["n"]
        ed = d["sum"] / max(1e-9, sum(k * c for k, c in d["tiers"].items()))
        p("   R per unit of size: A %+.3f  D %+.3f   (does the table pick better trades, or just trade less?)" % (ea, ed))
        p("   D - A: sized R %+.1f (noise bar %.1f), max drawdown %+.1f (noise bar %.1f)" % (d["sum"] - a["sum"], WIN_BAR,
                                                                                         d["dd"] - a["dd"], SAFE_BAR))
    p("   VERDICT  dip itself on US Tech 100 (A): %s      Ezio's design (D vs A): %s" % (va, vd))
    p("   (A PASS = net > +0.15 and EDGE > 0. D WINS = sized R beats A's by more than the noise bar and drawdown is not")
    p("    worse; SAFER = drawdown smaller by more than its noise bar, sized R at most 25%% below A's; LOSES = sized R below")
    p("    A's by more than the bar; else INSIDE THE NOISE.)")
    return va, vd


def main():
    argv = sys.argv[1:]

    def opt(name, k=1):
        if name in argv:
            i = argv.index(name)
            v = argv[i + 1:i + 1 + k]
            del argv[i:i + 1 + k]
            return v if k > 1 else v[0]
        return None
    hold = os.path.abspath(opt("--hold") or os.path.join(A.ROOT, "exam_hold"))
    check = opt("--check", 2)
    nomark, force = "--nomark" in argv, "--force" in argv

    if check:                                   # cloud check on spent data: variant A vs the why phase's dip book
        db, mk = os.path.abspath(check[0]), check[1]
        A.find_db = lambda: db
        import asiabo_lab as L, asiabo_why as W
        W._install()
        W.WITH_CHAN = False
        spec = dict((x["name"], x) for x in A.COLLECT_SYMBOLS)[mk]
        m = L.PMarket(spec)
        mine = dip_trades(L, m, "A")
        rb = []
        for nm, fn in L.P_LANES:
            if nm in ("rsi2", "dip3"):
                fn(m, rb)
        rows = [(mk,) + x for x in rb if (x[0], x[1]) in W.NEED_LV]
        book = [x for x, part in W.book_of(rows, {}) if part == "dip"]
        ok = [x for x in mine if L._p_era(x["t_in"])]
        print("CHECK %s: mine %d trades (%d in eras), sum R %+.2f | book %d trades, sum R %+.2f"
              % (mk, len(mine), len(ok), sum(x["R"] for x in ok), len(book), sum(x[5] for x in book)))
        bt = set(round(x[8]["_t_in"]) for x in book)
        mt = set(round(x["t_in"]) for x in ok)
        print("   same entry times: %d   only mine: %d   only book: %d" % (len(bt & mt), len(mt - bt), len(bt - mt)))
        return

    done = os.path.join(hold, "DIPDRIFT_DONE.txt")
    if os.path.exists(done) and not force:
        print("THE DIP-DRIFT TEST HAS ALREADY RUN (%s). It runs once. Nothing was done." % done)
        with open(done, encoding="utf-8") as f:
            print(f.read())
        sys.exit(1)
    files = sorted(str(x) for x in Path(hold).glob(EXAM_GLOB))
    if not files:
        print("no '%s' files in %s. Nothing was done." % (EXAM_GLOB, hold))
        sys.exit(1)
    rep = A.Report("dipdrift")
    p = rep.p
    p("=" * 118)
    p("DIP + DRIFT SIZING on US TECH 100 -- pre-registered 2026-10-13 (dip_drift_spec.md / top of this file). ONE run.")
    p("=" * 118)
    try:
        db = os.path.join(hold, "ustech100.db")
        build_db(files, db, p)
        A.find_db = lambda: db
        A.EXAM_UNLOCK = True                     # this db holds ONLY US Tech 100: the 2022 bear market is the point
        import asiabo_lab as L
        spec = register_spec()
        m = L.PMarket(spec)
        res = dict((v, dip_trades(L, m, v)) for v in VARIANTS)
        # same scoring window for every variant: from the first day the table can be read (252 days of history)
        j_first = next((j for j in range(len(m.D)) if j >= 252 and m.sma(j, 100) is not None), None)
        t_start = m.T[m.D[j_first + 1][1]] if j_first is not None and j_first + 1 < len(m.D) else 0
        res = dict((v, [x for x in xs if x["t_in"] >= t_start]) for v, xs in res.items())
        p("scoring window for ALL variants: trades entering from %s (the table's 252-day warm-up)"
          % time.strftime("%Y-%m-%d", time.gmtime(t_start)))
        ys = sorted(set(time.gmtime(x["t_in"]).tm_year for v in VARIANTS for x in res[v]))
        p("")
        p("-" * 118)
        p("RESULTS (R per trade = unsized; sized R = R x the table's size; one position at a time)")
        p("-" * 118)
        S = report(p, res, ys)
        va, vd = verdicts(p, S)
        p("")
        p("2020 / 2022 sized R:  " + "   ".join("%s %+.1f / %+.1f" % (v, year_sum(res[v], 2020), year_sum(res[v], 2022))
                                                 for v in VARIANTS))
        p("")
        p(YARD)
        if not nomark:
            with open(done, "w", encoding="utf-8") as f:
                f.write("dip-drift test ran %s\nreport: %s\nA %s; D vs A %s\n" % (time.strftime("%Y-%m-%d %H:%M:%S"),
                                                                                rep.dir, va, vd))
            p("")
            p("marked done: %s -- the test will not run again." % done)
    except Exception:
        p(traceback.format_exc())
        p("THE TEST DID NOT FINISH. It was NOT marked done.")
    rep.save()


if __name__ == "__main__":
    main()
