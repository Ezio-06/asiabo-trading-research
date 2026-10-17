"""
asiabo_young_engine.py  --  batch-1 younglings through our systems (2026-10-12). Uses asiabo_young.py (unchanged
lane rules) and make_synth.py v8 as subprocesses; changes nothing in them. Resumable: one result file per world in
reports/young_engine/worlds/.

    python asiabo_young_engine.py            run every world not done yet, then the report
    python asiabo_young_engine.py report     the report only

CHECK A  REAL vs REALISTIC FAKES: the lanes on 6 v8 worlds (preset real8; seeds 1.. that PASS the realism gate, failing
         seeds are skipped). Real is read against that spread (rank among the 6, and how many sit above real).
CHECK B  CAUSE TEST, dial worlds on the v8 block base, 2 seeds each (the gate is NOT required: these are meant to be
         unrealistic on purpose):
           MOMENTUM  --bsnap 0 --bmom 1   blocks that go AGAINST the 40-day trend are mirrored -> trends persist
           NEUTRAL   --bsnap 0            the plain block base
           SNAP-BACK --bsnap 1            blocks that go WITH the trend are mirrored (= real8)
         #31 (a snap-back bet) should rise MOMENTUM -> SNAP-BACK; #19 (a breakout bet) should fall.
CHECK C  PLACEBOS on the real data (asiabo_young --placebo): #31 the same setup without the crack trigger, #31 one day
         late, #19 squeeze without a band break, #19 one day late; and each lane without its best market-year.

PREDICTIONS (written 2026-10-12 BEFORE any world ran)
  Claude: A  #31 real above 5 of 6 fakes (it beat the one v8 world already), #19 real below 5 of 6.
          B  #31 EDGE rises momentum -> snap-back by a clear margin (its mechanism is mechanical: fading a stretch pays
             in a snap-back world); #19 falls. These cause tests should pass easily -- they say the lanes respond to
             the world they assume, NOT that the real market is such a world (that is check A).
          C  #31 no-trigger placebo about as good as #31 (the crack adds little; the stretch carries it); delay costs
             about half the edge; #31 survives losing its best market-year only barely.
  Ezio (2026-10-12 15:39, before any result was read):
          A  "depends on the type of worlds", but #31 should be BETTER on real data than on the fakes.
          B  the theory under #31 is simpler than snap-back: "the trend's over; earn from the losers that bought it
             late". No fixed expectation for the dial gap.
          C  the first crack is NOT a consistent signal: not much different from any stretched day.
"""
import os, sys, json, math, time, subprocess, glob, shutil, traceback
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import asiabo_offline as A

LANES = ["31 mirror dip", "19 squeeze", "27 gap closes"]
DIALS = [("momentum", ["--preset", "shuffle", "--bsnap", "0", "--bmom", "1.0"]),
         ("neutral", ["--preset", "shuffle", "--bsnap", "0"]),
         ("snapback", ["--preset", "real8"])]
N_REAL8 = 6
MAX_SEED = 14
SEEDS_B = (1, 2)
if os.environ.get("YE_QUICK"):          # mechanics test only: one world per check
    N_REAL8, MAX_SEED, SEEDS_B = 1, 3, (1,)


def _wdir():
    return os.path.join(A.ROOT, "reports", "young_engine", "worlds")


def _log(s):
    print(s)
    os.makedirs(os.path.dirname(_wdir()), exist_ok=True)
    with open(os.path.join(A.ROOT, "reports", "young_engine", "young_engine_log.txt"), "a", encoding="utf-8") as f:
        f.write(time.strftime("%Y-%m-%d %H:%M:%S ") + s + "\n")


def _run(cmd):
    p = subprocess.run(cmd, cwd=HERE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return p.returncode, p.stdout.decode("utf-8", "replace")


def world(name, gen_args, need_gate):
    """-> 'done' | 'gate_fail' | 'error'. Generates the world, runs the lanes, keeps the trades, deletes the db."""
    out = os.path.join(_wdir(), name + ".json")
    if os.path.exists(out):
        return "done"
    if os.path.exists(out + ".gatefail"):
        return "gate_fail"
    db = os.path.join(A.ROOT, "synth", "ye_%s.db" % name)
    py = sys.executable
    t0 = time.time()
    try:
        code, txt = _run([py, os.path.join(HERE, "make_synth.py"), "gen"] + gen_args + ["--out", db])
        if code == 3 and need_gate:
            open(out + ".gatefail", "w").write(txt[-3000:])
            _log("%s: realism gate FAILED -> skipped" % name)
            return "gate_fail"
        if code not in (0, 3) or not os.path.exists(db):
            _log("%s: generation failed (exit %s)\n%s" % (name, code, txt[-2000:]))
            return "error"
        tmp = out + ".part"
        code, txt = _run([py, os.path.join(HERE, "asiabo_young.py"), "--db", db, "--dump", tmp, "--nocore"])
        if code != 0 or not os.path.exists(tmp):
            _log("%s: lanes failed (exit %s)\n%s" % (name, code, txt[-2000:]))
            return "error"
        os.replace(tmp, out)
        _log("%s: done in %.0fs" % (name, time.time() - t0))
        return "done"
    finally:
        for f in (db, db + "-journal"):
            if os.path.exists(f):
                try:
                    os.remove(f)
                except OSError:
                    pass


def real_dump():
    out = os.path.join(_wdir(), "REAL.json")
    if os.path.exists(out):
        return True
    tmp = out + ".part"
    code, txt = _run([sys.executable, os.path.join(HERE, "asiabo_young.py"), "--dump", tmp, "--placebo", "--nocore"]
                     + (["--db", os.environ["YOUNG_REAL_DB"]] if os.environ.get("YOUNG_REAL_DB") else []))
    if code != 0 or not os.path.exists(tmp):
        _log("REAL: failed (exit %s)\n%s" % (code, txt[-2000:]))
        return False
    os.replace(tmp, out)
    _log("REAL: done")
    return True


def run():
    os.makedirs(_wdir(), exist_ok=True)
    os.makedirs(os.path.join(A.ROOT, "synth"), exist_ok=True)
    _log("young engine: start")
    real_dump()
    have, s = 0, 0
    while have < N_REAL8 and s < MAX_SEED:
        s += 1
        st = world("real8_s%d" % s, ["--preset", "real8", "--seed", str(s)], True)
        have += st == "done"
    for dial, args in DIALS:
        for sd in SEEDS_B:
            if dial == "snapback" and os.path.exists(os.path.join(_wdir(), "real8_s%d.json" % sd)):
                continue                       # the snap-back dial IS real8: reuse that world
            world("%s_s%d" % (dial, sd), args + ["--seed", str(sd)], False)
    report()


# ------------------------------------------------------------------ report
def _load(name):
    p = os.path.join(_wdir(), name + ".json")
    return json.load(open(p)) if os.path.exists(p) else None


def _cl(x):
    tt = time.gmtime(x["t_in"])
    return (x["m"], tt.tm_year, tt.tm_mon)


def cm(xs, val):
    """clustered mean and t (market x month)."""
    n = len(xs)
    if n < 2:
        return (val(xs[0]) if xs else None), None, n
    mu = sum(val(x) for x in xs) / n
    g = defaultdict(float)
    for x in xs:
        g[_cl(x)] += val(x) - mu
    k = len(g)
    if k < 2:
        return mu, None, n
    v = sum(e * e for e in g.values()) * k / (k - 1.0) / (n * n)
    return mu, (mu / math.sqrt(v) if v > 0 else None), n


def edge(xs):
    return cm(xs, lambda x: x["net"] - x["ctrl"])


def f(v, p=3):
    return ("%+.*f" % (p, v)) if v is not None else "-"


def ft(v):
    return ("t%+.1f" % v) if v is not None else "t -"


def report():
    rep = A.Report("young_engine")
    p = rep.p
    p("=" * 110)
    p("YOUNG ENGINE: batch-1 younglings through our systems (asiabo_young_engine.py; predictions at its top)")
    p("=" * 110)
    real = _load("REAL")
    if real is None:
        p("no REAL result yet")
        rep.save()
        return
    pick = lambda xs, lane, var=None: [x for x in xs if x["lane"] == lane and (var is None or x["var"] == var)]
    subsets = [("31 mirror dip", None), ("31 mirror dip", "long-stretch"), ("31 mirror dip", "short-stretch"),
               ("19 squeeze", None), ("27 gap closes", None)]
    # ---------------- A
    p("")
    p("CHECK A. REAL vs 6 REALISTIC v8 WORLDS (gate-passing seeds). EDGE per trade (n).")
    names = sorted(os.path.basename(x)[:-5] for x in glob.glob(os.path.join(_wdir(), "real8_s*.json")))
    skipped = sorted(os.path.basename(x)[:-14] for x in glob.glob(os.path.join(_wdir(), "real8_s*.json.gatefail")))
    p("   worlds: %s%s" % (", ".join(names), ("   (gate failed, skipped: %s)" % ", ".join(skipped)) if skipped else ""))
    for lane, var in subsets:
        e_r = edge(pick(real, lane, var))
        fakes = []
        for nm in names:
            w = _load(nm)
            e = edge(pick(w, lane, var))
            fakes.append(e)
        vals = [e[0] for e in fakes if e[0] is not None]
        above = sum(1 for v in vals if e_r[0] is not None and v >= e_r[0])
        p("   %-30s REAL %s %s (n %d) | fakes: %s | fakes at or above real: %d of %d" % (
            lane + (" / " + var if var else ""), f(e_r[0]), ft(e_r[1]), e_r[2],
            " ".join("%s(%d)" % (f(e[0]), e[2]) for e in fakes), above, len(vals)))
    # ---------------- B
    p("")
    p("CHECK B. CAUSE TEST: the same lanes in worlds dialled from MOMENTUM to SNAP-BACK (2 seeds each, pooled).")
    for lane, var in subsets:
        row = []
        for dial, _ in DIALS:
            xs = []
            for sd in (1, 2):
                w = _load("%s_s%d" % (dial, sd)) or (_load("real8_s%d" % sd) if dial == "snapback" else None)
                if w:
                    xs += pick(w, lane, var)
            e = edge(xs)
            row.append((dial, e))
        p("   %-30s " % (lane + (" / " + var if var else "")) +
          "  ".join("%s %s %s (n %d)" % (d, f(e[0]), ft(e[1]), e[2]) for d, e in row))
    p("   read: #31 should rise from momentum to snap-back, #19 should fall. A clear slope = the lane responds to the")
    p("   state it assumes (a cause, not a quirk); flat = its result is not coming from that mechanism.")
    # ---------------- C
    p("")
    p("CHECK C. PLACEBOS on the real data (EDGE per trade, n) and the best market-year test.")
    for lane, pls in (("31 mirror dip", ("31 P-no-trigger", "31 P-delay-1d")),
                      ("19 squeeze", ("19 P-no-break", "19 P-delay-1d"))):
        base = pick(real, lane)
        e0 = edge(base)
        p("   %-22s %s %s (n %d)" % (lane, f(e0[0]), ft(e0[1]), e0[2]))
        for pl in pls:
            e = edge(pick(real, pl))
            p("      %-19s %s %s (n %d)" % (pl[3:], f(e[0]), ft(e[1]), e[2]))
        my = defaultdict(float)
        for x in base:
            my["%s %d" % (x["m"], time.gmtime(x["t_in"]).tm_year)] += x["net"] - x["ctrl"]
        if my:
            best = max(my, key=my.get)
            rest = [x for x in base if "%s %d" % (x["m"], time.gmtime(x["t_in"]).tm_year) != best]
            e = edge(rest)
            p("      without its best market-year (%s, %+.2f R): %s %s (n %d)" % (best, my[best], f(e[0]), ft(e[1]), e[2]))
    p("")
    p("YARDSTICK: on fake random walks the whole-lane t reached +-3.5 (young1 report); a cause-test slope or a")
    p("placebo gap counts only if it is large next to that.")
    rep.save()


def main():
    argv = sys.argv[1:]
    if argv and argv[0] == "report":
        report()
    else:
        run()


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
