"""
asiabo.py  --  the ONE launcher (run.bat) for the whole trading-research folder.  Phase 0 of next_plan.md (2026-10-11).

The pattern it fixes: 15 run_*.bat files and a dozen scripts, with results spread over claude vision / reports /
engine\\worlds / synth_batch, and every new study adding more of both.

What it does:
  * reads the module registry modules.json (name, script steps + args, estimates, where it writes, vision behaviour)
  * runs a module, or a queue of modules, as SUBPROCESSES with their own args. No script is imported or edited, so
    every script's identity is untouched.
  * logs every run to runs.csv (start, module, args, exit code, minutes, peak RAM, new report folders, log file) and
    keeps the full console output of each run in reports\\cli\\logs\\  -> Claude reads the newest result per module
    instead of guessing which folder is fresh.
  * drops claude vision\\cli_run.txt after each run: which module produced what is in claude vision right now.
  * clean: moves the old bats to old versions\\bats\\ (never deletes), lists stale report folders / claude vision
    files for approval, shows disk use of synth\\cache and leftover job dbs.

    run.bat                         the menu
    run.bat run lab_omega why       run modules in order (no menu), then exit
    run.bat status                  print the dashboard and exit
    run.bat list                    the registry

Standard library only.
"""
import os, sys, csv, json, time, shutil, subprocess, hashlib, statistics

HERE = os.path.dirname(os.path.abspath(__file__))
REG = os.path.join(HERE, "modules.json")
RUNS = os.path.join(HERE, "runs.csv")
LOGDIR = os.path.join(HERE, "reports", "cli", "logs")
REPORTS = os.path.join(HERE, "reports")
VISION = os.path.join(HERE, "claude vision")
OLDBATS = os.path.join(HERE, "old versions", "bats")
OLDREPORTS = os.path.join(HERE, "old versions", "reports")
SYNTH = os.path.join(HERE, "synth")
FIELDS = ["start", "module", "args", "exit", "minutes", "peak_ram_gb", "reports", "log"]
KEEP_BATS = {"run.bat"}

try:
    sys.stdout.reconfigure(errors="replace")
except Exception:
    pass


# ------------------------------------------------------------------ small helpers
def now():
    return time.strftime("%Y-%m-%d %H:%M:%S")


def ask(prompt, default=""):
    try:
        s = input(prompt).strip()
    except EOFError:
        return default
    return s if s else default


def yes(prompt):
    return ask(prompt + " [y/N]: ").lower() in ("y", "yes")


def gb(n):
    return n / 1024.0 ** 3


def size_of(path):
    if os.path.isfile(path):
        return os.path.getsize(path)
    t = 0
    for d, _, fs in os.walk(path):
        for f in fs:
            try:
                t += os.path.getsize(os.path.join(d, f))
            except OSError:
                pass
    return t


def fmt_min(m):
    if m is None:
        return "?"
    if m >= 90:
        return "%.1f h" % (m / 60.0)
    return "%.0f min" % m if m >= 1 else "<1 min"


def free_ram_gb():
    if os.name == "nt":
        try:
            import ctypes

            class MS(ctypes.Structure):
                _fields_ = [("l", ctypes.c_ulong), ("load", ctypes.c_ulong), ("tot", ctypes.c_ulonglong),
                            ("avail", ctypes.c_ulonglong), ("a", ctypes.c_ulonglong), ("b", ctypes.c_ulonglong),
                            ("c", ctypes.c_ulonglong), ("d", ctypes.c_ulonglong), ("e", ctypes.c_ulonglong)]
            m = MS()
            m.l = ctypes.sizeof(MS)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
            return gb(m.avail), gb(m.tot)
        except Exception:
            return None, None
    try:
        info = {}
        with open("/proc/meminfo") as f:
            for line in f:
                k, v = line.split(":")
                info[k] = int(v.split()[0]) * 1024
        return gb(info["MemAvailable"]), gb(info["MemTotal"])
    except Exception:
        return None, None


def peak_ram_of(proc):
    """Peak working set of the child process (Windows). Grandchildren (synth_batch's jobs) are NOT included."""
    if os.name != "nt":
        try:
            import resource
            return resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss / 1024.0 ** 2   # Linux: KB, max over children
        except Exception:
            return None
    try:
        import ctypes
        from ctypes import wintypes

        class PMC(ctypes.Structure):
            _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD),
                        ("PeakWorkingSetSize", ctypes.c_size_t), ("WorkingSetSize", ctypes.c_size_t),
                        ("QuotaPeakPagedPoolUsage", ctypes.c_size_t), ("QuotaPagedPoolUsage", ctypes.c_size_t),
                        ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t), ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                        ("PagefileUsage", ctypes.c_size_t), ("PeakPagefileUsage", ctypes.c_size_t)]
        c = PMC()
        c.cb = ctypes.sizeof(PMC)
        f = ctypes.windll.psapi.GetProcessMemoryInfo
        f.argtypes = [wintypes.HANDLE, ctypes.POINTER(PMC), wintypes.DWORD]
        if f(int(proc._handle), ctypes.byref(c), c.cb):
            return gb(c.PeakWorkingSetSize)
    except Exception:
        pass
    return None


def unique_path(folder, name):
    p = os.path.join(folder, name)
    if not os.path.exists(p):
        return p
    b, e = os.path.splitext(name)
    k = 2
    while os.path.exists(os.path.join(folder, "%s_%d%s" % (b, k, e))):
        k += 1
    return os.path.join(folder, "%s_%d%s" % (b, k, e))


def md5(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def python_exe():
    return sys.executable


# ------------------------------------------------------------------ registry and run log
def load_reg():
    with open(REG, "r", encoding="utf-8") as f:
        return json.load(f)


def save_reg(reg):
    if os.path.exists(REG):
        shutil.copy2(REG, REG + ".bak")
    tmp = REG + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(reg, f, indent=2)
    os.replace(tmp, REG)


def mods(reg):
    return reg["modules"]


def find(reg, key):
    for m in mods(reg):
        if m["key"] == key:
            return m
    return None


def load_runs():
    if not os.path.exists(RUNS):
        return []
    with open(RUNS, "r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def add_run(row):
    new = not os.path.exists(RUNS)
    with open(RUNS, "a", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        if new:
            w.writeheader()
        w.writerow(row)


def args_str(m):
    return " | ".join(" ".join([s["script"]] + [quote(a) for a in s.get("args", [])]) for s in m["steps"])


def quote(a):
    return '"%s"' % a if (" " in a or a == "") else a


def split_args(s):
    """Windows-friendly split: spaces separate, double quotes group, backslashes stay as they are."""
    out, cur, q, any_ = [], [], False, False
    for ch in s:
        if ch == '"':
            q = not q
            any_ = True
        elif ch.isspace() and not q:
            if cur or any_:
                out.append("".join(cur))
            cur, any_ = [], False
        else:
            cur.append(ch)
    if cur or any_:
        out.append("".join(cur))
    return out


def learned(m, runs):
    """(minutes, peak GB) from the module's past successful runs with the SAME args; else the registry guess."""
    a = args_str(m)
    ok = [r for r in runs if r["module"] == m["key"] and r["exit"] == "0" and r["args"] == a]
    mins = [float(r["minutes"]) for r in ok if r.get("minutes")]
    rams = [float(r["peak_ram_gb"]) for r in ok if r.get("peak_ram_gb")]
    t = (statistics.median(mins), True) if mins else (m.get("est_min"), False)
    r = (max(rams), True) if rams else (m.get("ram_gb"), False)
    return t, r


def last_run(key, runs):
    rs = [r for r in runs if r["module"] == key]
    return rs[-1] if rs else None


def newest_report(m):
    pre = m.get("report_prefix")
    if not pre or not os.path.isdir(REPORTS):
        return None
    c = [d for d in os.listdir(REPORTS) if d.startswith(pre) and os.path.isdir(os.path.join(REPORTS, d))]
    if not c:
        return None
    return max(c, key=lambda d: os.path.getmtime(os.path.join(REPORTS, d)))


# ------------------------------------------------------------------ running
def snapshot():
    s = {}
    if os.path.isdir(REPORTS):
        for d in os.listdir(REPORTS):
            p = os.path.join(REPORTS, d)
            if os.path.isdir(p):
                s[d] = os.path.getmtime(p)
    return s


def run_step(cmd, logf, env):
    """Run one command; console output is shown live AND copied to the log. Input (an error's 'press Enter',
    asiabo_offline's own menu) still comes from the keyboard."""
    proc = subprocess.Popen(cmd, cwd=HERE, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, bufsize=0)
    out = sys.stdout
    import codecs
    dec = codecs.getincrementaldecoder("utf-8")(errors="replace")
    try:
        fd = proc.stdout.fileno()
        while True:
            b = os.read(fd, 4096)
            if not b:
                break
            logf.write(b)
            logf.flush()
            out.write(dec.decode(b))
            out.flush()
        code = proc.wait()
    except KeyboardInterrupt:
        try:
            proc.wait(timeout=30)
        except Exception:
            proc.kill()
            proc.wait()
        code = "interrupted"
    ram = peak_ram_of(proc)
    return code, ram


def tidy_bats(names):
    """Bats that a script re-writes by itself (write_launcher): move back to old versions\\bats. If an identical copy is
    already archived, the new one is just removed (nothing is lost)."""
    for n in names or []:
        p = os.path.join(HERE, n)
        if not os.path.isfile(p):
            continue
        os.makedirs(OLDBATS, exist_ok=True)
        arch = os.path.join(OLDBATS, n)
        try:
            if os.path.isfile(arch) and md5(arch) == md5(p):
                os.remove(p)
                print("(tidy: %s was re-written by the script; identical copy already in old versions\\bats, removed)" % n)
            else:
                dst = unique_path(OLDBATS, n)
                shutil.move(p, dst)
                print("(tidy: %s moved to old versions\\bats\\%s)" % (n, os.path.basename(dst)))
        except OSError as e:
            print("(tidy: could not move %s: %s)" % (n, e))


def run_module(m, runs):
    (t, _), (r, _) = learned(m, runs)
    print("")
    print("=" * 100)
    print(" %s  --  %s" % (m["key"], m["name"]))
    print(" %s" % args_str(m))
    print(" expected %s, peak RAM %s, writes %s, claude vision: %s" % (
        fmt_min(t), ("%.1f GB" % r) if r else "?", m.get("writes", "?"), m.get("vision", "?")))
    print("=" * 100)
    os.makedirs(LOGDIR, exist_ok=True)
    stamp = time.strftime("%Y%m%d_%H%M%S")
    logp = os.path.join(LOGDIR, "%s_%s.txt" % (stamp, m["key"]))
    before = snapshot()
    t0 = time.time()
    start = now()
    env = dict(os.environ, PYTHONUNBUFFERED="1", PYTHONIOENCODING="utf-8")
    code, peak = 0, None
    with open(logp, "wb") as logf:
        logf.write(("# %s  module %s\n# %s\n\n" % (start, m["key"], args_str(m))).encode("utf-8"))
        for i, st in enumerate(m["steps"]):
            cmd = [python_exe(), os.path.join(HERE, st["script"])] + list(st.get("args", []))
            if len(m["steps"]) > 1:
                hdr = "\n----- step %d of %d: %s %s\n" % (i + 1, len(m["steps"]), st["script"], " ".join(st.get("args", [])))
                print(hdr)
                logf.write(hdr.encode("utf-8"))
            code, ram = run_step(cmd, logf, env)
            if ram is not None:
                peak = ram if peak is None else max(peak, ram)
            if code != 0:
                break
    for f in m.get("delete_after", []) or []:
        p = os.path.join(HERE, f)
        if os.path.exists(p):
            try:
                os.remove(p)
                print("(temp file removed: %s)" % f)
            except OSError as e:
                print("(could not remove temp %s: %s)" % (f, e))
    tidy_bats(m.get("tidy_after"))
    after = snapshot()
    new = sorted(d for d in after if d not in before and d != "cli")
    touched = sorted(d for d in after if d in before and after[d] > before[d] + 1 and d != "cli")
    reps = new + ["%s (updated)" % d for d in touched]
    mins = (time.time() - t0) / 60.0
    row = {"start": start, "module": m["key"], "args": args_str(m), "exit": str(code), "minutes": "%.2f" % mins,
           "peak_ram_gb": ("%.2f" % peak) if peak is not None else "", "reports": "; ".join(reps),
           "log": os.path.relpath(logp, HERE)}
    add_run(row)
    runs.append(row)
    try:
        if os.path.isdir(VISION):
            with open(os.path.join(VISION, "cli_run.txt"), "w", encoding="utf-8") as f:
                f.write("last CLI run (asiabo.py) -- written AFTER the module, so this file is newer than its reports\n\n")
                for k in FIELDS:
                    f.write("%-12s %s\n" % (k, row[k]))
                f.write("\nvision behaviour of this module: %s\n" % m.get("vision", "?"))
    except OSError:
        pass
    print("")
    print("-" * 100)
    print(" %s finished: exit %s after %s%s" % (m["key"], code, fmt_min(mins),
                                                 (", peak RAM %.2f GB" % peak) if peak is not None else ""))
    print(" new report folders: %s" % (", ".join(reps) if reps else "none"))
    print(" log: %s" % row["log"])
    print("-" * 100)
    return code == 0


def run_queue(reg, keys, stop_on_fail=True, confirm=True):
    runs = load_runs()
    ms = []
    for k in keys:
        m = find(reg, k)
        if not m:
            print("unknown module: %s" % k)
            return False
        ms.append(m)
    tot, peak, unknown = 0.0, 0.0, []
    for m in ms:
        (t, _), (r, _) = learned(m, runs)
        if t is None:
            unknown.append(m["key"])
        else:
            tot += t
        if r:
            peak = max(peak, r)
    fr, _ = free_ram_gb()
    print("\nqueue: %s" % " -> ".join(m["key"] for m in ms))
    print("expected total %s%s; largest peak RAM %s; free RAM now %s" % (
        fmt_min(tot) if len(unknown) < len(ms) else "?", (" + unknown (%s)" % ", ".join(unknown)) if unknown else "",
        ("%.1f GB" % peak) if peak else "?", ("%.1f GB" % fr) if fr else "?"))
    wipers = [m["key"] for m in ms if str(m.get("vision", "")).startswith("wipe")]
    if len(ms) > 1 and wipers:
        print("note: %s wipe claude vision; earlier modules' reports stay in reports\\ (runs.csv lists them)." %
              ", ".join(wipers))
    for m in ms:
        if m.get("confirm") and confirm:
            print("\n!! %s: %s" % (m["key"], m["confirm"]))
            if not yes("run %s anyway?" % m["key"]):
                print("queue cancelled.")
                return False
    ok_all = True
    for i, m in enumerate(ms):
        if len(ms) > 1:
            print("\n### queue %d of %d" % (i + 1, len(ms)))
        ok = run_module(m, runs)
        ok_all = ok_all and ok
        if not ok and stop_on_fail and i < len(ms) - 1:
            print("queue stopped: %s failed (exit != 0). Remaining: %s" % (m["key"], ", ".join(x["key"] for x in ms[i + 1:])))
            return False
    return ok_all


# ------------------------------------------------------------------ screens
def dashboard(reg):
    runs = load_runs()
    print("")
    print("=" * 100)
    print(" ASIABO  --  one launcher for the research folder          %s" % now())
    print("=" * 100)
    db = os.path.join(HERE, "bars.db")
    if os.path.exists(db):
        print(" bars.db %.2f GB, changed %s" % (gb(os.path.getsize(db)), time.strftime("%Y-%m-%d %H:%M", time.localtime(os.path.getmtime(db)))))
    else:
        print(" bars.db: NOT FOUND in %s" % HERE)
    fr, tr = free_ram_gb()
    du = shutil.disk_usage(HERE)
    print(" free RAM %s of %s   free disk %.0f GB   python %s" % (
        ("%.1f GB" % fr) if fr else "?", ("%.1f GB" % tr) if tr else "?", gb(du.free), python_exe()))
    loose = [f for f in os.listdir(HERE) if f.lower().endswith(".bat") and f.lower() not in KEEP_BATS]
    if loose:
        print(" %d old bat(s) still loose in the folder -> menu c (clean) moves them to old versions\\bats" % len(loose))
    print("")
    print(" %-3s %-16s %-52s %9s %7s  %s" % ("#", "module", "what", "time", "RAM", "last run"))
    print(" " + "-" * 98)
    group = None
    for i, m in enumerate(mods(reg), 1):
        if m.get("group") != group:
            group = m.get("group")
            print(" [%s]" % group)
        (t, tl), (r, rl) = learned(m, runs)
        lr = last_run(m["key"], runs)
        last = ""
        if lr:
            last = "%s  exit %s" % (lr["start"][:16], lr["exit"])
        print(" %-3d %-16s %-52s %9s %7s  %s" % (
            i, m["key"], m["name"][:52], fmt_min(t) + ("" if tl or t is None else "~"),
            (("%.1fG" % r) + ("" if rl else "~")) if r else "?", last))
    print(" (~ = first guess; plain = learned from runs.csv)")
    if runs:
        print("\n last runs:")
        for r in runs[-5:]:
            print("   %s  %-16s exit %-4s %7s  -> %s" % (r["start"][:16], r["module"], r["exit"],
                                                       fmt_min(float(r["minutes"])) if r.get("minutes") else "?",
                                                       r["reports"] or "-"))


def pick(reg, s):
    """'3' or 'lab_omega' -> module; several separated by spaces / commas."""
    out = []
    for tok in s.replace(",", " ").split():
        m = None
        if tok.isdigit() and 1 <= int(tok) <= len(mods(reg)):
            m = mods(reg)[int(tok) - 1]
        else:
            m = find(reg, tok)
        if not m:
            print("unknown: %s" % tok)
            return None
        out.append(m["key"])
    return out


def screen_reports(reg):
    runs = load_runs()
    print("\n newest report per module (runs.csv first; else the newest folder on disk with the module's prefix)")
    rows = []
    for i, m in enumerate(mods(reg), 1):
        lr = last_run(m["key"], runs)
        rep = None
        src = ""
        if lr and lr["reports"]:
            rep = lr["reports"].split(";")[0].replace(" (updated)", "").strip()
            src = "cli %s" % lr["start"][:16]
        else:
            rep = newest_report(m)
            src = "disk" if rep else ""
        rows.append((m, rep))
        print(" %-3d %-16s %-48s %s" % (i, m["key"], rep or "-", src))
    s = ask("\n number to list / open that folder (Enter = back): ")
    if not s.isdigit() or not (1 <= int(s) <= len(rows)):
        return
    m, rep = rows[int(s) - 1]
    if not rep:
        print("no report folder for %s" % m["key"])
        return
    d = os.path.join(REPORTS, rep)
    files = sorted(os.listdir(d)) if os.path.isdir(d) else []
    print("\n %s  (%d files)" % (d, len(files)))
    for j, f in enumerate(files, 1):
        print("   %2d  %-50s %8.1f KB" % (j, f, os.path.getsize(os.path.join(d, f)) / 1024.0))
    s = ask(" file number to open, f = open the folder, Enter = back: ")
    target = d if s.lower() == "f" else (os.path.join(d, files[int(s) - 1]) if s.isdigit() and 1 <= int(s) <= len(files) else None)
    if target:
        open_path(target)


def open_path(p):
    try:
        if os.name == "nt":
            os.startfile(p)
        else:
            print("(would open %s)" % p)
    except OSError as e:
        print("could not open: %s" % e)


def screen_tweak(reg):
    s = ask(" module to tweak (number or key): ")
    ks = pick(reg, s) if s else None
    if not ks:
        return
    m = find(reg, ks[0])
    print("\n %s: %s" % (m["key"], m["name"]))
    for i, st in enumerate(m["steps"], 1):
        print("   step %d: %s %s" % (i, st["script"], " ".join(quote(a) for a in st.get("args", []))))
    if len(m["steps"]) > 1:
        n = ask(" which step (Enter = 1): ", "1")
        if not n.isdigit() or not (1 <= int(n) <= len(m["steps"])):
            return
        st = m["steps"][int(n) - 1]
    else:
        st = m["steps"][0]
    new = ask(" new args for %s (Enter = keep, - = none): " % st["script"])
    if not new:
        return
    st["args"] = [] if new == "-" else split_args(new)
    for k in ("est_min", "ram_gb"):
        v = ask(" %s (Enter = keep %s): " % (k, m.get(k)))
        if v:
            try:
                m[k] = float(v)
            except ValueError:
                pass
    save_reg(reg)
    print(" saved (old registry kept as modules.json.bak). Now: %s" % args_str(m))


def screen_add(reg):
    key = ask(" new module key (short, no spaces): ")
    if not key or " " in key or find(reg, key):
        print(" not added (empty, has spaces, or already exists)")
        return
    script = ask(" script file (e.g. asiabo_probe.py): ")
    if not script:
        return
    if not os.path.exists(os.path.join(HERE, script)):
        print(" (warning: %s is not in the folder yet)" % script)
    m = {"key": key, "group": ask(" group (Enter = new): ", "new"), "name": ask(" description: ", key),
         "steps": [{"script": script, "args": split_args(ask(" args (Enter = none): "))}],
         "est_min": None, "ram_gb": None, "writes": ask(" where it writes (free text): ", "?"),
         "report_prefix": ask(" report folder prefix in reports\\ (e.g. probe_; Enter = none): ") or None,
         "vision": ask(" claude vision behaviour [wipe/add/none] (Enter = wipe): ", "wipe")}
    reg["modules"].append(m)
    save_reg(reg)
    print(" added %s" % key)


def screen_remove(reg):
    s = ask(" module to remove from the registry (number or key): ")
    ks = pick(reg, s) if s else None
    if not ks:
        return
    if yes(" remove %s from modules.json? (the script file is not touched)" % ks[0]):
        reg["modules"] = [m for m in mods(reg) if m["key"] != ks[0]]
        save_reg(reg)
        print(" removed.")


# ------------------------------------------------------------------ clean
def clean_bats():
    loose = sorted(f for f in os.listdir(HERE) if f.lower().endswith(".bat") and f.lower() not in KEEP_BATS)
    if not loose:
        print(" no old bats left in the folder.")
        return
    print(" these move to old versions\\bats\\ (never deleted):")
    for f in loose:
        print("   %s" % f)
    if not yes(" move them?"):
        return
    os.makedirs(OLDBATS, exist_ok=True)
    for f in loose:
        dst = unique_path(OLDBATS, f)
        shutil.move(os.path.join(HERE, f), dst)
        print("   moved %s" % os.path.basename(dst))


def report_groups():
    """reports\\<prefix>_<YYYYMMDD_HHMMSS> folders grouped by prefix. Fixed folders (engine, hunt, synth_batch ...)
    hold resumable state and are never offered."""
    g = {}
    if not os.path.isdir(REPORTS):
        return g
    for d in os.listdir(REPORTS):
        p = os.path.join(REPORTS, d)
        parts = d.split("_")
        if not os.path.isdir(p) or len(parts) < 3 or not (parts[-2].isdigit() and len(parts[-2]) == 8):
            continue
        prefix = "_".join(parts[:-2])
        if prefix.startswith("synth_lab_"):
            prefix = "synth_lab_*"
        g.setdefault(prefix, []).append(d)
    for k in g:
        g[k].sort(key=lambda d: d.split("_")[-2] + d.split("_")[-1])
    return g


def clean_reports(runs):
    g = report_groups()
    if not g:
        print(" no dated report folders.")
        return
    keep_n = 2
    cited = set()
    for r in runs:
        for x in (r.get("reports") or "").split(";"):
            cited.add(x.replace(" (updated)", "").strip())
    print(" dated folders in reports\\ by kind. Offered: all but the newest %d of each kind, never one listed in runs.csv." % keep_n)
    print(" Approved folders MOVE to old versions\\reports\\ (same drive: instant, nothing deleted).")
    offers = []
    for k in sorted(g):
        ds = g[k]
        stale = [d for d in ds[:-keep_n] if d not in cited]
        sz = sum(size_of(os.path.join(REPORTS, d)) for d in stale)
        print("   %-3d %-18s %3d folders, newest %-34s stale %3d (%.1f MB)" % (len(offers) + 1, k, len(ds), ds[-1], len(stale), sz / 1e6))
        offers.append((k, stale))
    s = ask(" numbers to move (e.g. 1 3), a = all, Enter = none: ")
    if not s:
        return
    chosen = offers if s.lower() == "a" else [offers[int(x) - 1] for x in s.replace(",", " ").split()
                                                if x.isdigit() and 1 <= int(x) <= len(offers)]
    n = sum(len(st) for _, st in chosen)
    if not n or not yes(" move %d folder(s) to old versions\\reports\\?" % n):
        return
    os.makedirs(OLDREPORTS, exist_ok=True)
    for _, st in chosen:
        for d in st:
            shutil.move(os.path.join(REPORTS, d), unique_path(OLDREPORTS, d))
    print(" moved %d folder(s)." % n)


def clean_vision(runs):
    if not os.path.isdir(VISION):
        print(" no claude vision folder.")
        return
    fs = sorted(os.listdir(VISION), key=lambda f: os.path.getmtime(os.path.join(VISION, f)))
    last = runs[-1] if runs else None
    t_last = time.mktime(time.strptime(last["start"], "%Y-%m-%d %H:%M:%S")) if last else None
    print(" claude vision now (oldest first). 'stale' = older than the start of the last CLI run (%s):" % (
        last["start"] if last else "no CLI run yet"))
    stale = []
    for f in fs:
        mt = os.path.getmtime(os.path.join(VISION, f))
        st = t_last is not None and mt < t_last - 1 and f != "cli_run.txt"
        if st:
            stale.append(f)
        print("   %-44s %s %s" % (f, time.strftime("%Y-%m-%d %H:%M", time.localtime(mt)), " STALE" if st else ""))
    if stale and yes(" move the %d stale file(s) to old versions\\vision_<now>\\?" % len(stale)):
        dst = os.path.join(HERE, "old versions", "vision_" + time.strftime("%Y%m%d_%H%M%S"))
        os.makedirs(dst, exist_ok=True)
        for f in stale:
            shutil.move(os.path.join(VISION, f), os.path.join(dst, f))
        print(" moved.")


def clean_synth():
    if not os.path.isdir(SYNTH):
        print(" no synth folder.")
        return
    cache = os.path.join(SYNTH, "cache")
    print(" synth\\cache: %.2f GB (rebuilt by module synth_cache; synth_batch builds it itself if missing)" % (
        gb(size_of(cache)) if os.path.isdir(cache) else 0))
    dbs = []
    for d, _, fs in os.walk(SYNTH):
        if os.path.abspath(d).startswith(os.path.abspath(cache)):
            continue
        for f in fs:
            if f.lower().endswith((".db", ".db-journal", ".db-wal", ".tmp")):
                dbs.append(os.path.join(d, f))
    if not dbs:
        print(" no leftover synthetic dbs / temp files.")
    else:
        print(" leftover synthetic dbs / temp files (jobs delete theirs when they finish; these are left over):")
        for p in dbs:
            print("   %-50s %6.2f GB  %s" % (os.path.relpath(p, SYNTH), gb(os.path.getsize(p)),
                                           time.strftime("%Y-%m-%d %H:%M", time.localtime(os.path.getmtime(p)))))
        print(" these are generated cousins (rebuildable from a preset + seed), not data. Deleting frees the disk.")
        if ask(" type DELETE to delete them (anything else = keep): ") == "DELETE":
            for p in dbs:
                try:
                    os.remove(p)
                except OSError as e:
                    print("   could not delete %s: %s" % (p, e))
            print(" deleted.")
    du = shutil.disk_usage(HERE)
    print(" free disk now %.0f GB" % gb(du.free))


def screen_clean():
    runs = load_runs()
    while True:
        print("\n CLEAN:  1 move old bats   2 stale report folders   3 claude vision   4 synth disk use   Enter = back")
        s = ask(" > ")
        if s == "1":
            clean_bats()
        elif s == "2":
            clean_reports(runs)
        elif s == "3":
            clean_vision(runs)
        elif s == "4":
            clean_synth()
        elif s == "":
            return
        else:
            print(" choose 1-4, or Enter to go back")


def screen_runs():
    runs = load_runs()
    if not runs:
        print(" runs.csv is empty.")
        return
    for r in runs[-20:]:
        print(" %s  %-16s exit %-11s %8s  RAM %-5s -> %s" % (
            r["start"][:16], r["module"], r["exit"], fmt_min(float(r["minutes"])) if r.get("minutes") else "?",
            r.get("peak_ram_gb") or "?", r["reports"] or "-"))
    s = ask(" open the log of the last run? [y/N]: ")
    if s.lower() == "y":
        open_path(os.path.join(HERE, runs[-1]["log"]))


def menu():
    while True:
        reg = load_reg()
        dashboard(reg)
        print("\n  number/key = run it   q = queue   s = latest reports   l = run log   t = tweak args")
        print("  a = add module   r = remove module   c = clean   x = exit")
        s = ask("\n > ")
        if not s:
            continue
        low = s.lower()
        if low in ("x", "exit", "quit"):
            return
        if low == "q":
            ks = pick(reg, ask(" modules in order (numbers or keys, space-separated): "))
            if ks:
                stop = not yes(" keep going after a failure? (default: stop the queue)")
                run_queue(reg, ks, stop_on_fail=stop)
                ask("\n queue done. Enter = back to the menu ")
        elif low == "s":
            screen_reports(reg)
        elif low == "l":
            screen_runs()
        elif low == "t":
            screen_tweak(reg)
        elif low == "a":
            screen_add(reg)
        elif low == "r":
            screen_remove(reg)
        elif low == "c":
            screen_clean()
        else:
            ks = pick(reg, s)
            if ks:
                runs = load_runs()
                tot = [learned(find(reg, k), runs)[0][0] for k in ks]
                eta = fmt_min(sum(t for t in tot if t)) if all(t is not None for t in tot) else "unknown time"
                if ask(" run %s (%s)? [y/N]: " % (" -> ".join(ks), eta)).lower() in ("y", "yes"):
                    run_queue(reg, ks)
                    ask("\n done. Enter = back to the menu ")


def main():
    argv = sys.argv[1:]
    if not argv:
        menu()
        return
    reg = load_reg()
    cmd = argv[0].lower()
    if cmd == "run":
        ok = run_queue(reg, argv[1:], confirm=True)
        sys.exit(0 if ok else 1)
    elif cmd == "status":
        dashboard(reg)
    elif cmd == "list":
        for m in mods(reg):
            print("%-16s %s\n%16s %s" % (m["key"], m["name"], "", args_str(m)))
    else:
        print(__doc__)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n(stopped)")
