#!/usr/bin/env python3
"""
asiabo_exam.py  --  the US500 FRESH-DATA EXAM (pre-registered 2026-10-13). Rules + predictions: exam_us500_spec.md
(project), summarised below. SHADOW ONLY: it measures, it decides nothing, and it changes no other file.

    python asiabo_exam.py --baseline     context run on bars.db only (US500 2020-21 + 2024+, already spent). Run FIRST.
    python asiabo_exam.py                THE EXAM. Runs ONCE: refuses to run again once exam_hold\\EXAM_DONE.txt exists.

    test options (cloud only): --hold <folder>  --base <bars.db>  --nomark  --force

WHAT THE EXAM READS
  * The never-touched US 500 M1 file (first bar 2015-12-18) from exam_hold\\ (or, if it was not moved yet, bars_input\\).
    Bars before 2020-01-01 only. bars.db is NEVER changed: the exam builds its own small exam_hold\\exam_us500.db.
  * GERMANY 40 bars before 2020-01-01 copied from bars.db (already spent): only the partner leg of #27 / #28.
  * Safety: it refuses to run if bars.db already holds US 500 bars before 2020 (the exam would already be spent).

WHAT IT SCORES (trades ENTERING 2016-01-01 .. 2019-12-31, US500 only; frozen code and rules, real costs)
  MAIN TEST  core book fast + dip (core_book_v2): the why phase's own book_of(), one position per part / direction.
  LEADS      #31 mirror dip (incl. the long-stretch side), #27 gap closes vs #28 relative momentum (asiabo_young).
  REPORT     brk, ins (shelved): numbers only, no verdict.

PRE-REGISTERED VERDICT per core part (fast, dip)  -- bars set from 17 random-walk runs BEFORE the exam (see YARD)
  PASS   net R/trade above the noise bar (fast > +0.07, dip > +0.15)  AND  EDGE > 0
  FAIL   (net < 0 AND EDGE < 0)  OR  net t <= -2
  MIXED  anything else
  BOOK   PASS if both PASS; FAIL if either FAILs; MIXED otherwise.
  A PASS means "not refuted", NOT "proven": with ~4 years of one market the exam can catch a dead part, it cannot
  prove a live one (see the power line in the report).
  PREDICTIONS (Claude, 2026-10-13, before the baseline and the exam): fast MIXED (FAIL second), dip PASS ~55%,
  BOOK MIXED; brk EDGE > 0, ins ~0; #31 UNREADABLE; #27/#28 sign to #28 (US outran Europe 2016-19). Ezio: see the spec.
  Leads: #31 lead SURVIVES if ALL EDGE > 0 AND long-stretch EDGE > 0 (readable only at n >= 20, else UNREADABLE).
         #27 vs #28: #27 wins if #27 EDGE > 0 (they are exact mirrors); readable only at n >= 15 triggers.
"""
import os, sys, math, time, sqlite3, shutil, traceback
from pathlib import Path
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import asiabo_offline as A

CLIP_END = "2020-01-01"          # exam bars stop here (US 500 2020+ is already in bars.db and spent)
SCORE_START = "2016-01-01"       # trades entering from here are scored (the file starts 2015-12-18)
EXAM_GLOB = "US 500_m1_2015*"    # the never-touched export
PARTNER = "GERMANY 40"           # #27 / #28 partner leg, copied from bars.db
MIN_31, MIN_PAIR = 20, 15
PASS_NET = {"fast": 0.07, "dip": 0.15}   # above every one of the 17 random-walk runs (fast max +0.066, dip max +0.116)
BASE_WINDOWS = [("2020-21", "2020-01-01", "2022-01-01"), ("2024+", "2024-01-01", "2100-01-01")]

YARD = "\n".join([
    "YARDSTICK (this file on 17 fake random-walk US 500 exam files, 2026-10-13, BEFORE the exam):",
    "    fast  n 153-247   net -0.285 .. +0.066  (t down to -4.1)   EDGE -0.117 .. +0.155",
    "    dip   n 6-42      net -0.467 .. +0.116                      EDGE -0.211 .. +0.273",
    "    With 'net > 0 and EDGE > 0' noise PASSED fast 2/17 and dip 8/17 (!), so the PASS bars were raised above every",
    "    noise run: fast net > +0.07, dip net > +0.15. With those bars noise PASSES 0/17 for both; FAIL fast 11/17.",
    "    #31: 3-10 trades on noise (UNREADABLE expected).  #27: 9-16 triggers, EDGE -0.18 .. +0.44 on noise: even",
    "    when readable, only a sign for the record."])


def ep(s):
    return A.epoch_of(s)


# ================================================================ the exam database (bars.db is only READ)
def find_exam_file(hold):
    for folder in (hold, os.path.join(A.ROOT, "bars_input")):
        if os.path.isdir(folder):
            hits = sorted(Path(folder).glob(EXAM_GLOB))
            if hits:
                return str(hits[0]), folder
    return None, None


def build_exam_db(src, base_db, out_db, p):
    import build_bars_db as BB
    clip = int(ep(CLIP_END))
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
    meta, end, n, bad, ooo, ticks, first, last = BB.stage_file(cur, Path(src))
    sym = meta.get("symbol")
    if not n or not sym:
        con.close()
        raise RuntimeError("the exam file has no META line or no bars: %s" % src)
    complete = end is not None and int(end.get("bars", -1)) == n + bad
    cur.execute("ATTACH DATABASE ? AS base", (base_db,))
    spent = cur.execute("SELECT COUNT(*) FROM base.bars_m1 WHERE symbol=? AND ts < ?", (sym, clip)).fetchone()[0]
    if spent:
        con.close()
        os.remove(tmp)
        raise RuntimeError("bars.db ALREADY holds %d '%s' bars before %s: the exam data was merged, so it is spent. "
                           "STOP: nothing was run." % (spent, sym, CLIP_END))
    cur.execute("INSERT OR IGNORE INTO bars_m1 SELECT ?, ts, time_utc, open, high, low, close, volume, spread_avg, "
                "spread_max, ticks FROM stage WHERE ts < ? ORDER BY rowid", (sym, clip))
    kept = cur.execute("SELECT COUNT(*), MIN(time_utc), MAX(time_utc) FROM bars_m1 WHERE symbol=?", (sym,)).fetchone()
    cur.execute("INSERT INTO runs VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (os.path.basename(src), sym, meta.get("broker"), meta.get("digits"), meta.get("pip_size"),
                 meta.get("tick_size"), meta.get("start"), meta.get("version"), n, first, last, int(complete)))
    cur.execute("INSERT INTO bars_m1 SELECT * FROM base.bars_m1 WHERE symbol=? AND ts < ?", (PARTNER, clip))
    cur.execute("INSERT INTO runs SELECT * FROM base.runs WHERE symbol=?", (PARTNER,))
    pk = cur.execute("SELECT COUNT(*), MIN(time_utc), MAX(time_utc) FROM bars_m1 WHERE symbol=?", (PARTNER,)).fetchone()
    con.commit()
    cur.execute("DETACH DATABASE base")
    cur.execute("DROP TABLE stage")
    for s in (sym, PARTNER):
        BB.report_symbol(con, s)
    con.commit()
    con.close()
    os.replace(tmp, out_db)
    p("exam file: %s  (%d bars read, %d malformed, %d out of order, complete=%s, %s .. %s)"
      % (os.path.basename(src), n, bad, ooo, complete, first, last))
    p("exam db:   %s  %s %d bars %s .. %s;  %s %d bars %s .. %s (partner leg, from bars.db)"
      % (os.path.basename(out_db), sym, kept[0], kept[1], kept[2], PARTNER, pk[0], pk[1], pk[2]))
    if not complete or bad or ooo:
        p("!! FILE PROBLEM: the exam still runs, but read the counts above before trusting it.")
    return sym


# ================================================================ the measurement (same code paths as asiabo_young)
def measure(p, w0, w1, want31=True, wantpair=True):
    """-> dict part -> [rows], all US500 trades entering in [w0, w1)."""
    import asiabo_lab as L
    import asiabo_why as W
    import asiabo_probe as P
    import asiabo_young as Y
    W._install()
    W.WITH_CHAN = False
    specs = dict((x["name"], x) for x in A.COLLECT_SYMBOLS)
    out = defaultdict(list)
    DV = {}
    core_rows, det = [], {}
    for s in ("US500", "GERMANY40"):
        print("exam: %s ..." % s)
        m = L.PMarket(specs[s])
        dv = P.Day(m, L)
        DV[s] = dv
        if s == "US500":
            W._m1_cache(m)
            if want31:
                a = []
                Y.lane31(m, dv, L, a)
                out["#31"] = Y.one_position([(s,) + x for x in a])
            rb = []
            for nm, fn in L.P_LANES:
                if nm in L.P_OMEGA_LANES:
                    fn(m, rb)
            core_rows += [(s,) + x for x in rb if (x[0], x[1]) in W.NEED_LV]
            det.update(W.det_table(m))
            if m.m1q:
                m.m1q[0].close()
            m._m1cache.clear()
        del m
    for x, part in W.book_of(core_rows, det):
        out[part].append(x)
    if wantpair:
        pr = Y.pair(DV["US500"], DV["GERMANY40"], specs["US500"], specs["GERMANY40"])
        out["#27"] = [x for x in pr if x[1].startswith("27")]
        out["#28"] = [x for x in pr if x[1].startswith("28")]
    a0, a1 = ep(w0), ep(w1)
    return dict((k, [x for x in v if a0 <= x[8]["_t_in"] < a1]) for k, v in out.items())


def clu(x):
    tt = time.gmtime(x[8]["_t_in"])
    return (x[0], tt.tm_year, tt.tm_mon)


def stats(xs):
    import asiabo_probe as P
    if not xs:
        return None
    net = P.cmean([(x[5], clu(x)) for x in xs])
    edge = P.cmean([(x[5] - x[6], clu(x)) for x in xs])
    win = 100.0 * sum(1 for x in xs if x[5] > 0) / len(xs)
    return {"n": len(xs), "win": win, "net": net[0], "net_t": net[1], "edge": edge[0], "edge_t": edge[1],
            "sum": sum(x[5] for x in xs)}


def fmt(tag, st):
    import asiabo_probe as P
    if not st:
        return "   %-22s     0 trades" % tag
    return "   %-22s %5d  win %5.1f%%  net %s %s  EDGE %s %s  total %+7.1f R" % (
        tag, st["n"], st["win"], P.f3(st["net"]), P.ft(st["net_t"]), P.f3(st["edge"]), P.ft(st["edge_t"]), st["sum"])


def verdict(st, part):
    if not st:
        return "NO TRADES"
    if st["net_t"] is not None and st["net_t"] <= -2.0:
        return "FAIL"
    if st["net"] < 0 and st["edge"] < 0:
        return "FAIL"
    if st["net"] > PASS_NET[part] and st["edge"] > 0:
        return "PASS"
    return "MIXED"


def table(p, res, years):
    for part in ("fast", "dip", "brk", "ins"):
        xs = res.get(part, [])
        p(fmt(part, stats(xs)))
        for y in years:
            ys = [x for x in xs if time.gmtime(x[8]["_t_in"]).tm_year == y]
            if ys:
                p(fmt("   %d" % y, stats(ys)))
        for d, nm in ((1, "long"), (-1, "short")):
            ys = [x for x in xs if x[8].get("_d") == d]
            if ys and part in ("fast", "brk", "ins"):
                p(fmt("   " + nm, stats(ys)))


def leads(p, res):
    x31 = res.get("#31", [])
    s31 = stats(x31)
    p(fmt("#31 ALL", s31))
    for v in ("long-stretch", "short-stretch"):
        p(fmt("#31 " + v, stats([x for x in x31 if x[2] == v])))
    s27, s28 = stats(res.get("#27", [])), stats(res.get("#28", []))
    p(fmt("#27 gap closes", s27))
    p(fmt("#28 rel momentum", s28))
    return s31, stats([x for x in x31 if x[2] == "long-stretch"]), s27


# ================================================================ main
def main():
    argv = sys.argv[1:]

    def opt(name):
        if name in argv:
            k = argv.index(name)
            v = argv[k + 1]
            del argv[k:k + 2]
            return v
        return None
    hold = os.path.abspath(opt("--hold") or os.path.join(A.ROOT, "exam_hold"))
    base = os.path.abspath(opt("--base") or (A.find_db() or os.path.join(A.ROOT, "bars.db")))
    baseline = "--baseline" in argv
    nomark = "--nomark" in argv
    force = "--force" in argv
    done = os.path.join(hold, "EXAM_DONE.txt")

    if baseline:
        A.find_db = lambda: base
        rep = A.Report("exam_baseline")
        p = rep.p
        p("=" * 110)
        p("US500 EXAM -- BASELINE (context only): the same measurement on bars.db's US500, ALREADY SPENT data.")
        p("No exam data is read. Use these numbers for the predictions, then run the exam once.")
        p("=" * 110)
        try:
            allres = measure(p, BASE_WINDOWS[0][1], BASE_WINDOWS[-1][2])
            for nm, w0, w1 in BASE_WINDOWS:
                a0, a1 = ep(w0), ep(w1)
                res = dict((k, [x for x in v if a0 <= x[8]["_t_in"] < a1]) for k, v in allres.items())
                p("")
                p("-" * 110)
                p("US500 %s  (trades entering %s .. %s)" % (nm, w0, w1))
                p("-" * 110)
                y0, y1 = int(w0[:4]), min(int(w1[:4]), time.gmtime().tm_year + 1)
                table(p, res, range(y0, y1))
                leads(p, res)
        except Exception:
            p(traceback.format_exc())
        rep.save()
        return

    if os.path.exists(done) and not force:
        print("THE EXAM HAS ALREADY RUN (%s exists). It runs once. Nothing was done." % done)
        with open(done, encoding="utf-8") as f:
            print(f.read())
        sys.exit(1)
    src, where = find_exam_file(hold)
    if not src:
        print("no exam file '%s' in %s or bars_input. Nothing was done." % (EXAM_GLOB, hold))
        sys.exit(1)
    os.makedirs(hold, exist_ok=True)
    exam_db = os.path.join(hold, "exam_us500.db")
    rep = A.Report("exam_us500")
    p = rep.p
    p("=" * 110)
    p("US500 FRESH-DATA EXAM -- pre-registered 2026-10-13 (exam_us500_spec.md / the top of this file). ONE run.")
    p("=" * 110)
    if where != hold:
        p("note: the exam file was read from %s (not moved to exam_hold yet). Do NOT run build_bars_db before moving it"
          % where)
    try:
        build_exam_db(src, base, exam_db, p)
        A.find_db = lambda: exam_db
        res = measure(p, SCORE_START, CLIP_END)
        p("")
        p("-" * 110)
        p("MAIN TEST: core book on US500, trades entering %s .. %s (net / EDGE in R per trade, t clustered by month)"
          % (SCORE_START, "2019-12-31"))
        p("-" * 110)
        table(p, res, range(2016, 2020))
        vf, vd = verdict(stats(res.get("fast")), "fast"), verdict(stats(res.get("dip")), "dip")
        book = "PASS" if (vf == "PASS" and vd == "PASS") else ("FAIL" if "FAIL" in (vf, vd) else "MIXED")
        p("")
        p("   VERDICT  fast: %s   dip: %s   ->  BOOK: %s" % (vf, vd, book))
        p("   (PASS = net above the noise bar (fast +0.07, dip +0.15) and EDGE > 0; FAIL = net < 0 and EDGE < 0, or")
        p("    net t <= -2; else MIXED.")
        p("    PASS means 'not refuted', not 'proven'. brk / ins: numbers only, no verdict.)")
        for part in ("fast", "dip"):
            st = stats(res.get(part))
            if st and st["net_t"]:
                se = abs(st["net"] / st["net_t"])
                p("   power, %-4s: one standard error = %.3f R/trade; a real edge of +0.05 would show as t ~%+.1f"
                  % (part, se, 0.05 / se))
        p("")
        p("-" * 110)
        p("LEADS")
        p("-" * 110)
        s31, s31l, s27 = leads(p, res)
        if not s31 or s31["n"] < MIN_31:
            v31 = "UNREADABLE (n < %d)" % MIN_31
        else:
            v31 = "SURVIVES" if (s31["edge"] > 0 and s31l and s31l["edge"] > 0) else "FADES"
        if not s27 or s27["n"] < MIN_PAIR:
            v27 = "UNREADABLE (n < %d)" % MIN_PAIR
        else:
            v27 = "#27 (gap closes) wins" if s27["edge"] > 0 else "#28 (relative momentum) wins"
        p("   #31 lead: %s     #27 vs #28: %s" % (v31, v27))
        p("")
        p(YARD)
        if not nomark:
            with open(done, "w", encoding="utf-8") as f:
                f.write("exam ran %s\nreport: %s\nBOOK %s (fast %s, dip %s); #31 %s; pair %s\n"
                        % (time.strftime("%Y-%m-%d %H:%M:%S"), rep.dir, book, vf, vd, v31, v27))
            p("")
            p("marked done: %s -- the exam will not run again. Now the US 500 file may go into bars_input and the"
              % done)
            p("cache be rebuilt (build_bars_db, then make_synth cache).")
    except Exception:
        p(traceback.format_exc())
        p("THE EXAM DID NOT FINISH. It was NOT marked done; fix and run again (nothing was scored if this happened")
        p("before the VERDICT line).")
    rep.save()


if __name__ == "__main__":
    main()
