"""
synth_batch.py  --  the FROZEN omega book (frozen_design_v1, 2026-10-09) on many cousin histories of bars.db.

For each setting and seed: build the cousin (make_synth.py) -> run 'asiabo_lab.py omega --db <it>' -> keep its
omega_summary.csv rows -> DELETE the cousin (~1.5 GB each, only one exists at a time). The real data is run once first
as the reference. Results accumulate in reports/synth_batch/results.csv, so a stopped batch RESUMES where it left off
(double-click again). The summary is rewritten after every run and put in 'claude vision' at the end.

PREDICTIONS, written 2026-10-09 BEFORE any batch result (what each setting should do IF our theories are right):
  identity    = the real result exactly (sanity check of the whole pipeline)
  shuffle     brk / fast / ins edge stays positive in most seeds and most eras (T1: short-term momentum lives inside
              2-6 week blocks); dip stays positive where it has trades. Money lower than real in some seeds: the real
              history may have been lucky in its ORDER of events (how much lower = how lucky).
  cosmetic    = shuffle within noise (price level and tiny jitter must not matter: everything is in ATR units)
  dayshuffle  brk and fast edge fall to ~0 (multi-day momentum is gone); dip falls to ~0 (multi-day snap-back is
              gone); ins changes least (it is decided inside one day). If brk SURVIVES dayshuffle, T1/T4 are wrong
              about what it lives on.
  vol_up      edge in R about the same (ATR units); NET better (fixed costs are a smaller share of a bigger R)
  vol_down    edge about the same; NET worse (costs a bigger share)
  trend_up    brk and fast improve clearly (more trend months); ins slightly; dip unclear
  costly      edge unchanged; net lower by the extra spread (most in fast and ins, the short holds)
  longblock   (added after batch 1, which showed 2024+ profit vanishing on 2-6 week blocks) if the profit lives in
              trends LONGER than 6 weeks, 8-26 week blocks bring most of the real 2024+ result back; if they do not,
              the real 2024+ was luck in the exact order of events, not long trends
  HOT-STREAK (T5) and CANARY (T22) effects: if they are real market behaviour they show up again in shuffle /
  cosmetic; if they are a quirk of the real ORDER of events they shrink toward 0 there. dayshuffle should erase any
  part of them that comes from multi-day structure.

Usage: python synth_batch.py [--seeds 3] [--presets shuffle,dayshuffle,...] [--workers N] [--redo preset]
       (double-click: run_10_synth_batch.bat)
SPEED (2026-10-10): bars.db is read ONCE into a memory-mapped source cache (synth/cache, ~1 GB); jobs run in parallel,
as many as the free memory / cores / disk allow (max 4, 3 GB of memory always kept free so Windows never swaps).
"""
import os, sys, csv, time, glob, shutil, subprocess
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import asiabo_offline as A

DEFAULT_PRESETS = ["identity", "shuffle", "cosmetic", "dayshuffle", "vol_up", "vol_down", "trend_up", "costly",
                   "longblock"]
ERAS = ["2014-17", "2018-19", "A 2020-21", "B 2024+"]
SLEEVES = ["brk", "ins", "dip", "fast", "ALL"]


def _newest(pattern):
    c = sorted(glob.glob(os.path.join(A.ROOT, "reports", pattern)), key=os.path.getmtime)
    return c[-1] if c else None


def _run(cmd, buf, env=None):
    """Run one command; its log lines go into buf (written in one piece when the job ends, so parallel jobs do not
    interleave). Returns (ok, stdout)."""
    t0 = time.time()
    buf.append("  $ " + " ".join(os.path.basename(c) if i == 1 else c for i, c in enumerate(cmd)))
    r = subprocess.run(cmd, cwd=HERE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=env)
    if r.returncode != 0:
        buf.append("    FAILED (exit %d), last lines:\n%s" % (r.returncode, "\n".join(r.stdout.splitlines()[-15:])))
    buf.append("    %.0fs" % (time.time() - t0))
    return r.returncode == 0, r.stdout


def _free_ram_gb():
    """Physical memory available right now (GB), Windows or Linux; None if unknown."""
    try:
        if os.name == "nt":
            import ctypes

            class MS(ctypes.Structure):
                _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                            ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                            ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                            ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                            ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]
            m = MS()
            m.dwLength = ctypes.sizeof(MS)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
            return m.ullAvailPhys / 1e9
        with open("/proc/meminfo") as f:
            for line in f:
                if line.startswith("MemAvailable:"):
                    return int(line.split()[1]) / 1e6
    except Exception:
        return None
    return None


JOB_RAM_GB = 1.5          # peak private memory of one job (generator, then the lab), with margin
RAM_RESERVE_GB = 3.0      # always left free for Windows and other programs (no swapping = no SSD wear)
JOB_DISK_GB = 2.0         # one synthetic database (~1.5 GB) while its job runs
DISK_RESERVE_GB = 10.0
MAX_WORKERS = 4


def auto_workers(log):
    cores = os.cpu_count() or 2
    ram = _free_ram_gb()
    disk = shutil.disk_usage(A.ROOT).free / 1e9
    w = max(1, min(MAX_WORKERS, cores - 1))
    if ram is not None:
        w = min(w, max(1, int((ram - RAM_RESERVE_GB) // JOB_RAM_GB)))
    w = min(w, max(1, int((disk - DISK_RESERVE_GB) // JOB_DISK_GB)))
    log("parallel jobs: %d  (cores %d, free memory %s GB, free disk %.0f GB; each job budgeted %.1f GB memory, "
        "%.0f GB disk; %.0f GB memory always kept free)" % (w, cores, "?" if ram is None else "%.1f" % ram, disk,
                                                           JOB_RAM_GB, JOB_DISK_GB, RAM_RESERVE_GB))
    return w


def _job(p, sd, py):
    """One cousin history (or the real data) start to finish. Returns (p, sd, rows or None, log lines)."""
    buf = ["", "%s seed %s   (started %s)" % (p, sd, time.strftime("%H:%M"))]
    env = dict(os.environ, ASIABO_NO_VISION="1", ASIABO_REPORT_TAG="%s_s%s" % (p, sd))
    if p == "real":
        ok, out = _run([py, os.path.join(HERE, "asiabo_lab.py"), "omega"], buf, env)
    else:
        tmp = os.path.join(A.ROOT, "synth", "job_%s_s%s.db" % (p, sd))
        if os.path.exists(tmp):
            os.remove(tmp)
        ok, out = _run([py, os.path.join(HERE, "make_synth.py"), "gen", "--preset", p, "--seed", sd, "--out", tmp], buf)
        if ok:
            ok, out = _run([py, os.path.join(HERE, "asiabo_lab.py"), "omega", "--db", tmp], buf, env)
        try:
            if os.path.exists(tmp):
                os.remove(tmp)
        except OSError as e:
            buf.append("    (could not delete %s: %s)" % (tmp, e))
    if not ok:
        return p, sd, None, buf
    folder = None
    for line in out.splitlines():
        if line.startswith("report folder:"):
            folder = line.split(":", 1)[1].strip()
    rows = _read_summary(folder)
    if not rows:
        buf.append("    no omega_summary.csv in %s" % folder)
        return p, sd, None, buf
    for r in rows:
        r["preset"], r["seed"] = p, sd
    return p, sd, rows, buf


def _read_summary(folder):
    p = os.path.join(folder, "omega_summary.csv") if folder else None
    if not p or not os.path.exists(p):
        return None
    with open(p, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _load(path):
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _append(path, rows):
    new = not os.path.exists(path)
    keys = ["preset", "seed", "metric", "sleeve", "era", "value", "extra"]
    with open(path, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        if new:
            w.writeheader()
        for r in rows:
            w.writerow(dict((k, r.get(k, "")) for k in keys))


def _f(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def summarize(rows, out_path):
    """Per setting: each number as  mean [min .. max] (seeds above 0 / seeds)  next to the REAL value."""
    data = defaultdict(list)                       # (preset, metric, sleeve, era, extra) -> [values over seeds]
    for r in rows:
        v = _f(r["value"])
        if v is not None:
            data[(r["preset"], r["metric"], r["sleeve"], r["era"], r.get("extra", "") if r["metric"].startswith(
                "money") else "")].append(v)
    presets = [p for p in ["real"] + DEFAULT_PRESETS + sorted(set(r["preset"] for r in rows))
               if any(k[0] == p for k in data)]
    presets = list(dict.fromkeys(presets))
    seeds = defaultdict(set)
    for r in rows:
        seeds[r["preset"]].add(r["seed"])
    L = []
    L.append("SYNTHETIC BATCH  --  the frozen omega book on cousin histories (frozen_design_v1)")
    L.append("Each cell: mean over seeds [lowest .. highest] (seeds above 0 / seeds).  'real' = the actual history.")
    L.append("settings run: " + ", ".join("%s x%d" % (p, len(seeds[p])) for p in presets))
    L.append("")
    L.append("PREDICTIONS" + __doc__.split("PREDICTIONS")[1].split("Usage:")[0].rstrip())

    def cell(p, metric, sleeve, era, extra=""):
        v = data.get((p, metric, sleeve, era, extra))
        if not v:
            return "%-26s" % "-"
        m = sum(v) / len(v)
        return "%-26s" % ("%+.3f [%+.2f..%+.2f] %d/%d" % (m, min(v), max(v), sum(1 for x in v if x > 0), len(v))
                          if len(v) > 1 else "%+.3f" % m)
    for metric, title in (("edge_r", "EDGE vs coin flip, R per trade (the direction power)"),
                          ("net_r", "NET R per trade after costs"),
                          ("r_per_yr", "NET R per year")):
        L.append("")
        L.append("=" * 120)
        L.append(title)
        L.append("=" * 120)
        for s in SLEEVES:
            L.append("")
            L.append("  %s" % s)
            L.append("    %-11s %s" % ("setting", "".join("%-26s" % e for e in ERAS)))
            for p in presets:
                L.append("    %-11s %s" % (p, "".join(cell(p, metric, s, e) for e in ERAS)))
    L.append("")
    L.append("=" * 120)
    L.append("MONEY, fixed risk (the frozen sizing), %/yr and worst drawdown %, $10,000 and $100,000")
    L.append("=" * 120)
    for eq in ("10000", "100000"):
        L.append("")
        L.append("  $%s    %s" % (eq, "".join("%-26s" % e for e in ERAS)))
        for p in presets:
            L.append("    %-11s cagr %s" % (p, "".join(cell(p, "money_cagr", "fixed", e, eq) for e in ERAS)))
            L.append("    %-11s dd   %s" % ("", "".join(cell(p, "money_dd", "fixed", e, eq) for e in ERAS)))
    L.append("")
    L.append("=" * 120)
    L.append("HOT-STREAK (T5) and CANARY (T22) effects: R/trade in the 'defensive' or 'alarm' state minus normal")
    L.append("(negative = the state really precedes worse trades, as the theory says; positive = the opposite)")
    L.append("=" * 120)
    for metric in ("state_gap_form20", "state_gap_streak2", "canary_gap"):
        L.append("")
        L.append("  %s" % metric)
        for s in SLEEVES[:-1]:
            for p in presets:
                if any(k[0] == p and k[1] == metric and k[2] == s for k in data):
                    L.append("    %-4s %-11s %s" % (s, p, "".join(cell(p, metric, s, e) for e in ERAS)))
    L.append("")
    L.append("  book-level timing value: sized R/yr of each rule minus 'fixed' (positive = the rule's timing helped)")
    for rule in ("kelly", "streak2", "form20"):
        for p in presets:
            line = "    %-8s %-11s" % (rule, p)
            for e in ERAS:
                a = data.get((p, "sized_r_per_yr_" + rule, "ALL", e, ""))
                b = data.get((p, "sized_r_per_yr_fixed", "ALL", e, ""))
                if a and b and len(a) == len(b):
                    d = [x - y for x, y in zip(a, b)]
                    line += "%-26s" % ("%+.1f [%+.1f..%+.1f] %d/%d" % (sum(d) / len(d), min(d), max(d),
                                                                     sum(1 for x in d if x > 0), len(d)))
                else:
                    line += "%-26s" % "-"
            L.append(line)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")


def main():
    argv = sys.argv[1:]
    nseeds = 3
    presets = list(DEFAULT_PRESETS)
    redo = []
    nw = 0
    i = 0
    while i < len(argv):
        if argv[i] == "--seeds":
            nseeds = int(argv[i + 1]); i += 2
        elif argv[i] == "--presets":
            presets = argv[i + 1].split(","); i += 2
        elif argv[i] == "--redo":
            redo = argv[i + 1].split(","); i += 2
        elif argv[i] == "--workers":
            nw = int(argv[i + 1]); i += 2
        else:
            raise SystemExit(__doc__)
    bdir = os.path.join(A.ROOT, "reports", "synth_batch")
    os.makedirs(bdir, exist_ok=True)
    res = os.path.join(bdir, "results.csv")
    logp = os.path.join(bdir, "batch_log.txt")

    def log(s):
        print(s)
        with open(logp, "a", encoding="utf-8") as f:
            f.write(s + "\n")
    for p in redo:                       # drop a setting's old results ONCE (a marker file stops it on resume)
        mark = os.path.join(bdir, "redone_%s_v3.txt" % p)
        if not os.path.exists(mark):
            keep = [r for r in _load(res) if r["preset"] != p]
            if os.path.exists(res):
                os.remove(res)
            if keep:
                _append(res, keep)
            with open(mark, "w") as f:
                f.write("old %s results dropped %s (generator v3)\n" % (p, time.strftime("%Y-%m-%d %H:%M")))
    done = set((r["preset"], r["seed"]) for r in _load(res))
    jobs = [("real", "0")] + [(p, str(sd)) for p in presets for sd in ([1] if p == "identity" else
                                                                       range(1, nseeds + 1))]
    todo = [j for j in jobs if j not in done]
    log("")
    log("=" * 80)
    log("synth batch %s: %d jobs, %d already done, %d to run" % (
        time.strftime("%Y-%m-%d %H:%M"), len(jobs), len(jobs) - len(todo), len(todo)))
    py = sys.executable
    os.makedirs(os.path.join(A.ROOT, "synth"), exist_ok=True)
    t_all = time.time()
    if todo:
        buf = []
        ok, _ = _run([py, os.path.join(HERE, "make_synth.py"), "cache"], buf)      # once, before any parallel job
        for line in buf:
            log(line)
        if not ok:
            log("source cache failed; jobs will read bars.db directly (slower)")
    workers = nw if nw else auto_workers(log)
    import threading
    from concurrent.futures import ThreadPoolExecutor, as_completed
    lock = threading.Lock()
    finished = 0
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = []
        for p, sd in todo:
            futs.append(ex.submit(_job, p, sd, py))
            time.sleep(2)                                # stagger the starts a little
        for fu in as_completed(futs):
            p, sd, rows, buf = fu.result()
            with lock:
                finished += 1
                buf[1] = "[%d/%d] %s" % (finished, len(todo), buf[1])
                for line in buf:
                    log(line)
                if rows:
                    _append(res, rows)
                    summarize(_load(res), os.path.join(bdir, "synth_batch_summary.txt"))
                    log("    saved %d numbers; summary updated" % len(rows))
    summarize(_load(res), os.path.join(bdir, "synth_batch_summary.txt"))
    log("")
    log("batch finished in %.1f h" % ((time.time() - t_all) / 3600.0))
    A.publish_to_vision(bdir)


if __name__ == "__main__":
    main()
