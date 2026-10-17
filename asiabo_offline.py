#!/usr/bin/env python3
"""
asiabo_offline.py  --  the CURRENT Asia-breakout bot, replayed offline on bars.db.

Standalone: shares nothing with cashbotoffline.py except the bars.db lookup and the
report format (plain text in reports/). Nothing from the old project is used.

WHAT IT REPLAYS (same rules as Cashbotas_main.py)
  * M1 bars from bars.db are rolled up into M15 bars; logic runs once per closed M15 bar.
  * Asian box = M15 bars opening 00:00-06:59 UTC. Needs >= 20 bars, box 2-12 ATR(14, simple).
  * First M15 close beyond the box +/- 0.1 ATR between 07:00 and 15:59 is THE signal (one per day).
  * Stop = far side of the box, target = 2R, anything open is closed at the 16:00 bar's close (16:15).
  * Sizing: 1% of balance (cap $500), min 1 unit, step 1 unit, skip if min volume risks > 1.5x intended.
  * Equity Pulse (live in the bot) controls size / skips. Adaptive TP is SHADOW only (never changes trades).
  * Exits are checked on M1 bars: stop before target inside a bar (conservative), gaps fill at the open.

TWO RUNS, SAME TRADES WHERE POSSIBLE
  flat  = plain 1% risk, no Equity Pulse      -> the strategy's own edge (R stats come from here)
  pulse = Equity Pulse on                     -> what the account actually would have done

Usage:  python asiabo_offline.py                (menu)
        python asiabo_offline.py 2024-01-01 2026-01-01
        python asiabo_offline.py study           (what goes with the strategy working? see run_study)
        python asiabo_offline.py collect         (research data collection: every lane in shadow, see COLLECT)
        python asiabo_offline.py house           (the earners design replayed on the last collect run, see HOUSE)
US 500: collect runs it on its own clock (New York cash session, see CLOCK_NY); house replays it with gold's
        zones unchanged, as an independent check.
Pure standard library. No network.

OUTPUT: every run writes its own dated folder, reports/<mode>_<YYYYMMDD_HHMMSS>/.
LAUNCHER: every run (re)writes run_asiabo_offline.bat (Windows) or run_asiabo_offline.sh next to this
          file, so next time it can be started with a double-click.
SEALED YEARS: 2022-2023 are the exam. They are never loaded unless EXAM_UNLOCK is set by hand (see COLLECT).
"""
import os, sys, math, time, datetime, sqlite3, traceback, random, bisect, calendar
from array import array
from collections import defaultdict

# =============================== CONFIG ===============================
SYMBOL_MATCH = ["XAUUSD"]
DB_UTC_OFFSET_HOURS = 0       # hours the bars.db timestamps are AHEAD of UTC (e.g. 2 for broker time UTC+2)
COST_BP = 1.3                 # round trip cost, basis points of price, charged per trade (spread + commission)

# strategy (mirror of Cashbotas_main.py)
RANGE_START_HOUR = 0
RANGE_END_HOUR = 7
WINDOW_END_HOUR = 16
BREAKOUT_BUFFER_ATR = 0.10
MIN_RANGE_ATR = 2.0
MAX_RANGE_ATR = 12.0
MIN_RANGE_BARS = 20
STOP_MODE = "opposite"
TARGET_R = 2.0
MIN_SL_DISTANCE_USD = 3.0
ATR_PERIOD = 14

# sizing
START_BALANCE = 10000.0
RISK_PCT = 1.0
MAX_MONETARY_RISK_USD = 500.0
FLOOR_TOLERANCE = 0.5
VOLUME_MIN = 1.0              # units (1 unit = 1 oz on XAUUSD)
VOLUME_STEP = 1.0

# Equity Pulse (mirror)
EP_BASELINE = START_BALANCE
EP_STEP_PCT = 1.0
EP_TRIGGER_PCT = 2.0
EP_PROMOTE_MIN_DAYS = 2
EP_MIN_DEFEND_PCT = 1.0
EP_DECAY_MAX = 0.80
EP_DECAY_MIN = 0.50
EP_NOTCH = 0.10
EP_POINTS_PER_NOTCH = 2
EP_DIST_UNIT_PCT = 0.5
EP_POINTS_PER_DIST = 2
EP_POINTS_PER_WIN_DAY = 1
EP_DAILY_LOSS_PCT = 5.0
EP_LIFETIME_LOSS_PCT = 10.0

# Adaptive TP shadow (mirror)
ATP_DD_MILD_PCT = 2.0
ATP_DD_INTENSE_PCT = 5.0
ATP_PRIOR_LOCK = {"calm": 0.30, "mild": 0.40, "moderate": 0.60, "intense": 0.80}
ATP_GOAL_BONUS = 0.30
ATP_LOCK_THRESHOLD = 0.60
ATP_MIN_LOCK_R = 0.05
ATP_DATA_K = 20
ATP_TRAIL_START_R = 0.50
ATP_TRAIL_GAP_R = {"calm": 0.50, "mild": 0.50, "moderate": 0.35, "intense": 0.25}
# ======================================================================

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
KNOWN_FOLDERS = {"bot", "research", "data", "reports", "logs", "archive", "misc"}
if os.environ.get("CASHBOT_ROOT"):
    ROOT = os.path.abspath(os.environ["CASHBOT_ROOT"])
elif os.path.basename(SCRIPT_DIR).lower() in KNOWN_FOLDERS:
    ROOT = os.path.dirname(SCRIPT_DIR)
else:
    ROOT = SCRIPT_DIR


VISION_DIR_NAME = "claude vision"


def publish_to_vision(src_dir):
    """Wipe <ROOT>/claude vision and put a flat copy (no subfolders) of the finished run there.
    The dated folder in reports/ keeps the permanent copy, so no unique names are needed."""
    import shutil
    try:
        vdir = os.path.join(ROOT, VISION_DIR_NAME)
        os.makedirs(vdir, exist_ok=True)
        for n in os.listdir(vdir):
            fp = os.path.join(vdir, n)
            try:
                if os.path.isdir(fp) and not os.path.islink(fp):
                    shutil.rmtree(fp)
                else:
                    os.remove(fp)
            except OSError as e:
                print("(claude vision: could not remove %s: %s)" % (n, e))
        k = 0
        for n in sorted(os.listdir(src_dir)):
            fp = os.path.join(src_dir, n)
            if os.path.isfile(fp):
                shutil.copy2(fp, os.path.join(vdir, n))
                k += 1
        print("claude vision: wiped and refilled with %d file(s) from %s" % (k, os.path.basename(src_dir)))
    except Exception as e:
        print("(claude vision not updated: %s)" % e)


# ------------------------------ report ------------------------------
class Report:
    """Each run gets its own dated folder: reports/<name>_<YYYYMMDD_HHMMSS>/. The text report and any
    data files of that run all go inside it (self.dir)."""

    def __init__(self, name):
        self.name = name
        self.lines = []
        self.dir = os.path.join(ROOT, "reports", "%s_%s" % (name, time.strftime("%Y%m%d_%H%M%S")))
        os.makedirs(self.dir, exist_ok=True)

    def p(self, s=""):
        print(s)
        self.lines.append(s)

    def save(self):
        path = os.path.join(self.dir, "%s.txt" % self.name)
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(self.lines) + "\n")
        print("\nreport folder: %s" % self.dir)
        publish_to_vision(self.dir)
        return path


# ------------------------------ data ------------------------------
def find_db():
    for p in (os.path.join(ROOT, "bars.db"), os.path.join(ROOT, "data", "bars.db")):
        if os.path.exists(p):
            return p
    for dp, dn, fn in os.walk(ROOT):
        if "bars.db" in fn:
            return os.path.join(dp, "bars.db")
    return None


def _pick(lc, names):
    for n in names:
        if n in lc:
            return lc[n]
    return None


def detect_source(con, match):
    schema = {}
    for (t,) in con.execute("select name from sqlite_master where type='table'"):
        schema[t] = [r[1] for r in con.execute('pragma table_info("%s")' % t)]
    for t, cols in schema.items():
        lc = {c.lower(): c for c in cols}
        tcol = _pick(lc, ["time", "ts", "timestamp", "datetime", "open_time", "dt", "date", "t"])
        oc, hc = _pick(lc, ["open", "o"]), _pick(lc, ["high", "h"])
        lo, cc = _pick(lc, ["low", "l"]), _pick(lc, ["close", "c"])
        sc = _pick(lc, ["symbol", "sym", "market", "instrument"])
        name_hit = any(m.lower() in t.lower().replace(" ", "") for m in match)
        if tcol and oc and hc and lo and cc and (sc or name_hit):
            return t, tcol, oc, hc, lo, cc, sc, name_hit
    msg = "Could not auto-detect the bars table. Schema found:\n"
    for t, cols in schema.items():
        msg += "  %s: %s\n" % (t, cols)
    raise RuntimeError(msg)


def to_epoch(v):
    if isinstance(v, (int, float)):
        v = float(v)
        return v / 1000.0 if v > 1e12 else v
    s = str(v).strip()
    try:
        return to_epoch(float(s))
    except ValueError:
        pass
    d = datetime.datetime.fromisoformat(s.replace("Z", "+00:00").replace("T", " "))
    if d.tzinfo is None:
        d = d.replace(tzinfo=datetime.timezone.utc)
    return d.timestamp()


def epoch_of(datestr):
    return datetime.datetime.strptime(datestr, "%Y-%m-%d").replace(tzinfo=datetime.timezone.utc).timestamp()


class M1:
    pass


def load_m1(start_s, end_s, match=None):
    """M1 bars for one symbol. Bars inside the sealed exam years are NEVER returned unless EXAM_UNLOCK
    is True, so no mode of this tool can look at them by accident."""
    match = match or SYMBOL_MATCH
    path = find_db()
    if not path:
        raise RuntimeError("bars.db not found under %s" % ROOT)
    con = sqlite3.connect(path)
    try:
        t, tcol, oc, hc, lo, cc, sc, name_hit = detect_source(con, match)
    except RuntimeError:
        con.close()
        raise RuntimeError("no table for %s in bars.db" % "/".join(match))
    q = 'select "%s","%s","%s","%s","%s" from "%s"' % (tcol, oc, hc, lo, cc, t)
    params = ()
    if sc and not name_hit:
        q += ' where upper(replace("%s"," ","")) in (%s)' % (sc, ",".join("?" * len(match)))
        params = tuple(m.upper() for m in match)
    q += ' order by "%s"' % tcol
    b = M1()
    b.ts, b.o, b.h, b.l, b.c = array("d"), array("d"), array("d"), array("d"), array("d")
    shift = DB_UTC_OFFSET_HOURS * 3600.0
    last = -1.0
    for row in con.execute(q, params):
        try:
            ts = to_epoch(row[0]) - shift
            o, h, l, c = float(row[1]), float(row[2]), float(row[3]), float(row[4])
        except (ValueError, TypeError):
            continue
        if ts < start_s or ts >= end_s or ts <= last or min(o, h, l, c) <= 0:
            continue
        if sealed(ts):
            continue
        last = ts
        b.ts.append(ts); b.o.append(o); b.h.append(h); b.l.append(l); b.c.append(c)
    con.close()
    b.n = len(b.ts)
    b.path, b.table = path, t
    if b.n < 5000:
        raise RuntimeError("only %d M1 bars loaded for %s; check the symbol name / window" % (b.n, "/".join(match)))
    return b


def build_m15(m):
    """M15 bars: (t0, o, h, l, c, first_m1, last_m1_exclusive) plus ATR(14, simple)."""
    bars = []
    cur = None
    for i in range(m.n):
        k = int(m.ts[i] // 900) * 900
        if cur is None or k != cur[0]:
            if cur is not None:
                bars.append(cur)
            cur = [k, m.o[i], m.h[i], m.l[i], m.c[i], i, i + 1]
        else:
            if m.h[i] > cur[2]: cur[2] = m.h[i]
            if m.l[i] < cur[3]: cur[3] = m.l[i]
            cur[4] = m.c[i]
            cur[6] = i + 1
    if cur is not None:
        bars.append(cur)
    tr = []
    for k, b in enumerate(bars):
        if k == 0:
            tr.append(b[2] - b[3])
        else:
            pc = bars[k - 1][4]
            tr.append(max(b[2] - b[3], abs(b[2] - pc), abs(b[3] - pc)))
    atr = [None] * len(bars)
    s = 0.0
    for k in range(len(bars)):
        s += tr[k]
        if k >= ATR_PERIOD:
            s -= tr[k - ATR_PERIOD]
        if k >= ATR_PERIOD - 1:
            atr[k] = s / ATR_PERIOD
    return bars, atr


def hour_profile(m):
    """Average M1 range per UTC hour: a sanity check that the timestamps really are UTC."""
    tot, cnt = [0.0] * 24, [0] * 24
    for i in range(0, m.n, 3):
        hr = time.gmtime(m.ts[i]).tm_hour
        tot[hr] += m.h[i] - m.l[i]
        cnt[hr] += 1
    return [tot[h] / cnt[h] if cnt[h] else 0.0 for h in range(24)]


# ------------------------------ equity pulse ------------------------------
class Pulse:
    def __init__(self, enabled):
        self.on = enabled
        self.x = self.anchor = self.peak = self.dist_base = EP_BASELINE
        self.decay = EP_DECAY_MAX
        self.points = 0
        self.days = 0
        self.defending = False
        self.lifetime_halted = False
        self.day_halted = False
        self.day_start_balance = None
        self.day_start_equity = None
        self.ev = defaultdict(int)
        self.events = []

    def floor(self):
        if not self.on or not self.defending:
            return None
        return self.peak - self.decay * (self.peak - self.anchor)

    def allowed(self, bal):
        f = self.floor()
        return None if f is None else bal - f

    def mode(self, bal):
        if self.lifetime_halted: return "lifetime_halt"
        if self.day_halted: return "daily_halt"
        if self.floor() is not None: return "gain_defence"
        return "normal" if bal >= self.x else "below_x"

    def add_points(self, n, bal):
        self.points += n
        while self.points >= EP_POINTS_PER_NOTCH:
            self.points -= EP_POINTS_PER_NOTCH
            up = bal >= self.x * (1 + EP_TRIGGER_PCT / 100.0)
            old = self.decay
            self.decay = round(min(EP_DECAY_MAX, max(EP_DECAY_MIN, old + (EP_NOTCH if up else -EP_NOTCH))), 2)
            if self.decay != old:
                self.ev["notch_loosen" if up else "notch_tighten"] += 1

    def check_promotion(self, bal, day):
        if (self.floor() is not None and self.days >= EP_PROMOTE_MIN_DAYS
                and bal >= self.x * (1 + EP_TRIGGER_PCT / 100.0)):
            old = self.x
            self.x = round(old * (1 + EP_STEP_PCT / 100.0), 2)
            self.anchor = self.x
            self.days = 0
            self.ev["promotion"] += 1
            self.events.append((day, "promotion", old, self.x))

    def release(self, bal, day):
        self.ev["release"] += 1
        self.events.append((day, "release", self.anchor, bal))
        self.anchor = self.peak = bal
        self.days = 0
        self.defending = False

    def on_close(self, bal, day):
        if not self.on:
            return
        was = self.floor() is not None
        if bal > self.peak:
            self.peak = bal
        unit = self.x * EP_DIST_UNIT_PCT / 100.0
        while bal >= self.dist_base + unit:
            self.dist_base += unit
            if was:
                self.add_points(EP_POINTS_PER_DIST, bal)
        if not was and bal >= self.anchor * (1 + EP_MIN_DEFEND_PCT / 100.0):
            self.defending = True
            self.decay = EP_DECAY_MAX
            self.points = 0
            self.days = 0
            self.dist_base = max(self.dist_base, bal)
            self.ev["defence_start"] += 1
        self.check_promotion(bal, day)

    def new_day(self, bal, eq, weekday, day):
        if self.on:
            if self.floor() is not None and self.day_start_balance is not None and bal > self.day_start_balance:
                self.add_points(EP_POINTS_PER_WIN_DAY, bal)
            if self.floor() is not None and weekday:
                self.days += 1
            self.check_promotion(bal, day)
        self.day_start_balance = bal
        self.day_start_equity = eq
        self.day_halted = False

    def hard_limits(self, eq, day=None):
        """returns 'lifetime' / 'daily' / None. Pulse run only: the flat run measures the raw strategy."""
        if not self.on:
            return None
        if self.lifetime_halted:
            return "lifetime"
        if eq <= EP_BASELINE * (1 - EP_LIFETIME_LOSS_PCT / 100.0):
            self.lifetime_halted = True
            self.halt_day = day
            self.ev["lifetime_halt"] += 1
            return "lifetime"
        if (not self.day_halted and self.day_start_equity
                and eq <= self.day_start_equity * (1 - EP_DAILY_LOSS_PCT / 100.0)):
            self.day_halted = True
            self.ev["daily_halt"] += 1
            return "daily"
        return None


# ------------------------------ adaptive TP shadow ------------------------------
class ATP:
    def __init__(self):
        self.stats = {}
        self.hwm = START_BALANCE

    @staticmethod
    def bucket(hour, r):
        tb = "morning" if hour < 12 else ("midday" if hour < 14 else "afternoon")
        rb = "neg" if r < 0 else ("0-0.5" if r < 0.5 else ("0.5-1" if r < 1.0 else "1+"))
        return tb + "|" + rb

    def state(self, bal):
        if bal > self.hwm:
            self.hwm = bal
        dd = (self.hwm - bal) / self.hwm * 100.0
        if dd <= 0: return "calm"
        if dd < ATP_DD_MILD_PCT: return "mild"
        if dd < ATP_DD_INTENSE_PCT: return "moderate"
        return "intense"

    @staticmethod
    def goals(pulse, bal, open_usd):
        proj = bal + open_usd
        g = []
        if bal < pulse.x <= proj: g.append("back_to_x")
        if bal < pulse.x * (1 + EP_TRIGGER_PCT / 100.0) <= proj: g.append("reach_trigger")
        if not pulse.defending and bal < pulse.anchor * (1 + EP_MIN_DEFEND_PCT / 100.0) <= proj: g.append("start_defence")
        if pulse.defending and proj >= pulse.dist_base + pulse.x * EP_DIST_UNIT_PCT / 100.0: g.append("earn_notch")
        return g

    def on_bar(self, tr, bar, pulse, bal):
        a = tr["atp"]
        e, rd, d = tr["entry"], tr["rd"], tr["dir"]
        cls_r = (bar[4] - e) * d / rd
        worst_r = ((bar[3] - e) if d > 0 else (e - bar[2])) / rd
        mfe_r = tr["mfe"] / rd
        g = time.gmtime(bar[0])
        key = self.bucket(g.tm_hour, cls_r)
        if g.tm_min == 45:
            a["snaps"].append((key, cls_r))
        if a["exited"]:
            return
        st = self.state(bal)
        if a["trail"] is not None and worst_r <= a["trail"]:
            a.update(exited=True, exit_r=a["trail"], reason="trail", state=st, goals="none")
            return
        if mfe_r >= ATP_TRAIL_START_R:
            nt = mfe_r - ATP_TRAIL_GAP_R[st]
            if a["trail"] is None or nt > a["trail"]:
                a["trail"] = nt
        gl = self.goals(pulse, bal, cls_r * rd * tr["vol"]) if cls_r > 0 else []
        sm, n = self.stats.get(key, [0.0, 0])
        exp_hold = sm / n if n else 0.0
        w = n / float(n + ATP_DATA_K)
        score = min(1.0, w * min(1.0, max(0.0, 0.5 - exp_hold)) + (1 - w) * ATP_PRIOR_LOCK[st]
                    + (ATP_GOAL_BONUS if gl else 0.0))
        if cls_r >= ATP_MIN_LOCK_R and score >= ATP_LOCK_THRESHOLD:
            a.update(exited=True, exit_r=cls_r, reason="lock", state=st, goals="+".join(gl) if gl else "none")

    def on_close(self, tr, real_r):
        a = tr["atp"]
        for key, r in a["snaps"]:
            s = self.stats.setdefault(key, [0.0, 0])
            s[0] += real_r - r
            s[1] += 1
        if not a["exited"]:
            a.update(exited=True, exit_r=real_r, reason="held", state="-", goals="none")


# ------------------------------ simulation ------------------------------
def floor_units(v):
    return math.floor(v / VOLUME_STEP + 1e-9) * VOLUME_STEP


def simulate(m, bars, atr, pulse_on):
    pulse = Pulse(pulse_on)
    atp = ATP()
    bal = START_BALANCE
    trades, skips, days_seen = [], defaultdict(int), 0
    eq_curve = []            # (day, balance) at each day start
    day = None
    rng_hi = rng_lo = None
    rng_n = 0
    status = "none"
    signal_done = False
    pos = None

    def open_pnl(p, price):
        return (price - p["entry"]) * p["dir"] * p["vol"]

    def close(p, price, reason, when):
        nonlocal bal, pos
        move = (price - p["entry"]) * p["dir"]
        cost = p["entry"] * COST_BP / 1e4
        net = (move - cost) * p["vol"]
        bal += net
        p.update(exit=price, reason=reason, exit_t=when, net=net,
                 r=(move - cost) / p["rd"], exit_move=move)
        p["mfe"] = max(p["mfe"], move)
        p["mae"] = max(p["mae"], -move)
        if pulse_on:
            atp.on_close(p, move / p["rd"])
        trades.append(p)
        pos = None
        pulse.on_close(bal, p["day"])

    for k, bar in enumerate(bars):
        t0, o, h, l, c, a1, b1 = bar
        g = time.gmtime(t0)
        hour = g.tm_hour
        dkey = "%04d-%02d-%02d" % (g.tm_year, g.tm_mon, g.tm_mday)

        # 1) intrabar exits on M1 (stop checked before target; gaps fill at the open)
        if pos is not None:
            for i in range(a1, b1):
                mo, mh, ml = m.o[i], m.h[i], m.l[i]
                if pos["dir"] > 0:
                    if ml <= pos["sl"]:
                        close(pos, min(mo, pos["sl"]), "StopLoss", m.ts[i]); break
                    if mh >= pos["tp"]:
                        close(pos, max(mo, pos["tp"]), "TakeProfit", m.ts[i]); break
                else:
                    if mh >= pos["sl"]:
                        close(pos, max(mo, pos["sl"]), "StopLoss", m.ts[i]); break
                    if ml <= pos["tp"]:
                        close(pos, min(mo, pos["tp"]), "TakeProfit", m.ts[i]); break

        # 2) bar-close logic (mirrors on_bar_closed)
        if dkey != day:
            day = dkey
            days_seen += 1
            weekday = datetime.date(g.tm_year, g.tm_mon, g.tm_mday).weekday() < 5
            eq = bal + (open_pnl(pos, c) if pos else 0.0)
            pulse.new_day(bal, eq, weekday, day)
            eq_curve.append((day, bal))
            rng_hi = rng_lo = None
            rng_n = 0
            status = "none"
            if pos is None:
                signal_done = False

        if RANGE_START_HOUR <= hour < RANGE_END_HOUR:
            rng_hi = h if rng_hi is None else max(rng_hi, h)
            rng_lo = l if rng_lo is None else min(rng_lo, l)
            rng_n += 1
            rng_last_close = c

        if pos is not None:
            mv_hi = (h - pos["entry"]) if pos["dir"] > 0 else (pos["entry"] - l)
            mv_lo = (pos["entry"] - l) if pos["dir"] > 0 else (h - pos["entry"])
            if mv_hi > pos["mfe"]:
                pos["mfe"], pos["mfe_t"] = mv_hi, t0
            pos["mae"] = max(pos["mae"], mv_lo)
            if g.tm_min == 45:
                pos["hour_r"].append(((hour + 1) % 24, (c - pos["entry"]) * pos["dir"] / pos["rd"]))
            if pulse_on:
                atp.on_bar(pos, bar, pulse, bal)

        eq = bal + (open_pnl(pos, c) if pos else 0.0)
        hl = pulse.hard_limits(eq, day)
        if hl:
            if pos is not None:
                close(pos, c, "pulse_%s_loss" % hl, t0 + 900)
            if hl == "lifetime":
                break
            continue

        if pos is not None and hour >= WINDOW_END_HOUR:
            close(pos, c, "window_end", t0 + 900)
            continue
        if pulse.day_halted:
            continue

        if status == "none" and hour >= RANGE_END_HOUR:
            a = atr[k]
            if rng_n < MIN_RANGE_BARS or rng_hi is None:
                status = "skip"
                if rng_n:
                    skips["range_insufficient_bars"] += 1
            else:
                ratio = (rng_hi - rng_lo) / a if a else None
                if ratio is None or ratio < MIN_RANGE_ATR:
                    status = "skip"; skips["range_too_small"] += 1
                elif ratio > MAX_RANGE_ATR:
                    status = "skip"; skips["range_too_wide"] += 1
                else:
                    status = "ready"
                    rng_ratio = ratio

        if status != "ready" or signal_done or pos is not None:
            continue
        if not (RANGE_END_HOUR <= hour < WINDOW_END_HOUR):
            continue

        a = atr[k]
        buf = BREAKOUT_BUFFER_ATR * a
        if c > rng_hi + buf:
            d = 1
        elif c < rng_lo - buf:
            d = -1
        else:
            continue
        signal_done = True
        entry = c
        sl = ((rng_hi + rng_lo) / 2.0) if STOP_MODE == "mid" else (rng_lo if d > 0 else rng_hi)
        rd = abs(entry - sl)
        if rd < MIN_SL_DISTANCE_USD:
            skips["stop_too_close"] += 1
            continue
        tp = entry + d * TARGET_R * rd

        risk = min(bal * RISK_PCT / 100.0, MAX_MONETARY_RISK_USD)
        mode = pulse.mode(bal)
        cap = pulse.allowed(bal)
        min_risk = VOLUME_MIN * rd
        if cap is not None and cap < min_risk:
            if pulse.days >= EP_PROMOTE_MIN_DAYS:
                pulse.release(bal, day)
                cap = None
                mode = pulse.mode(bal)
            else:
                skips["pulse_cushion"] += 1
                continue
        if cap is not None:
            risk = min(risk, cap)
        vol = floor_units(risk / rd)
        if vol <= VOLUME_MIN:
            if min_risk > risk * (1 + FLOOR_TOLERANCE):
                skips["volume_floor"] += 1
                continue
            vol = VOLUME_MIN
        pos = {"day": day, "dir": d, "entry": entry, "sl": sl, "tp": tp, "rd": rd, "vol": vol,
               "risk_usd": vol * rd, "entry_t": t0 + 900, "mode": mode, "cap": cap, "decay": pulse.decay,
               "range_ratio": rng_ratio, "bal_at_entry": bal,
               "i_next": b1, "atr": a, "box_hi": rng_hi, "box_lo": rng_lo, "box_end_close": rng_last_close,
               "signal_close": c,
               "mfe": 0.0, "mfe_t": None, "mae": 0.0, "hour_r": [],
               "atp": {"exited": False, "exit_r": None, "reason": None, "state": None, "goals": None,
                       "trail": None, "snaps": []}}

    if pos is not None:
        close(pos, bars[-1][4], "data_end", bars[-1][0] + 900)
    return {"trades": trades, "skips": skips, "pulse": pulse, "bal": bal, "eq_curve": eq_curve,
            "days": days_seen, "atp": atp}


# ------------------------------ report helpers ------------------------------
def year_of(t):
    return time.gmtime(t).tm_year


def max_dd(values):
    pk, dd = None, 0.0
    for v in values:
        pk = v if pk is None else max(pk, v)
        dd = max(dd, pk - v)
    return dd


def streak(rs):
    best = cur = 0
    for r in rs:
        cur = cur + 1 if r < 0 else 0
        best = max(best, cur)
    return best


def mean(xs):
    return sum(xs) / len(xs) if xs else 0.0


def se(xs):
    if len(xs) < 2:
        return 0.0
    mu = mean(xs)
    return math.sqrt(sum((x - mu) ** 2 for x in xs) / (len(xs) - 1) / len(xs))


def row(rep, cells, widths):
    rep.p("  " + "".join((str(c).ljust(w) if i == 0 else str(c).rjust(w)) for i, (c, w) in enumerate(zip(cells, widths))))


def edge_block(rep, trades, title):
    rs = [t["r"] for t in trades]
    wins = [r for r in rs if r > 0]
    losses = [r for r in rs if r <= 0]
    rep.p(title)
    rep.p("  trades %d | win rate %.1f%% | avg win %+.2fR | avg loss %+.2fR" %
          (len(rs), 100.0 * len(wins) / max(1, len(rs)), mean(wins), mean(losses)))
    rep.p("  expectancy %+.3fR per trade (+/- %.3f standard error) | total %+.1fR | max drawdown %.1fR | worst losing streak %d" %
          (mean(rs), se(rs), sum(rs), max_dd([sum(rs[:i + 1]) for i in range(len(rs))]), streak(rs)))


def run(start, end):
    check_window_unsealed(start, end)
    rep = Report("asiabo_offline")
    t_start = time.time()
    m = load_m1(start, end)
    bars, atr = build_m15(m)
    first = time.strftime("%Y-%m-%d", time.gmtime(m.ts[0]))
    last = time.strftime("%Y-%m-%d", time.gmtime(m.ts[-1]))

    rep.p("=" * 78)
    rep.p("ASIA BREAKOUT  --  offline replay on bars.db")
    rep.p("=" * 78)
    rep.p("data: %s (table %s) | %s .. %s | %d M1 bars -> %d M15 bars" % (m.path, m.table, first, last, m.n, len(bars)))
    rep.p("box %02d:00-%02d:00 UTC | entries until %02d:00 | stop=%s | target %.1fR | buffer %.2f ATR | box %.0f-%.0f ATR" %
          (RANGE_START_HOUR, RANGE_END_HOUR, WINDOW_END_HOUR, STOP_MODE, TARGET_R, BREAKOUT_BUFFER_ATR, MIN_RANGE_ATR, MAX_RANGE_ATR))
    rep.p("costs %.2f bp round trip | start balance $%.0f | risk %.1f%% (cap $%.0f) | min volume %.0f unit" %
          (COST_BP, START_BALANCE, RISK_PCT, MAX_MONETARY_RISK_USD, VOLUME_MIN))

    prof = hour_profile(m)
    peak_h = max(range(24), key=lambda h: prof[h])
    rep.p("")
    rep.p("TIMEZONE CHECK  (gold is most active around the US open, ~12-15 UTC)")
    rep.p("  busiest hour in the data: %02d:00 | quietest: %02d:00" % (peak_h, min(range(24), key=lambda h: prof[h] or 1e9)))
    if not 12 <= peak_h <= 15:
        rep.p("  !! WARNING: the busiest hour is outside 12-15. bars.db is probably NOT in UTC.")
        rep.p("  !! Set DB_UTC_OFFSET_HOURS (e.g. 2 or 3 for broker time) or the Asian box is in the wrong place.")
    else:
        rep.p("  looks like UTC. OK.")

    flat = simulate(m, bars, atr, False)
    pul = simulate(m, bars, atr, True)
    ft, pt = flat["trades"], pul["trades"]

    # ---------------- strategy edge ----------------
    rep.p("")
    rep.p("-" * 78)
    rep.p("1. THE STRATEGY'S OWN EDGE  (flat 1% risk, no Equity Pulse; R is net of costs)")
    rep.p("-" * 78)
    edge_block(rep, ft, "all years")
    rep.p("")
    rep.p("  by year:")
    widths = [8, 8, 8, 10, 11, 11, 12]
    row(rep, ["year", "trades", "win%", "total R", "exp R", "+/- se", "pos months"], widths)
    by_y = defaultdict(list)
    for t in ft:
        by_y[year_of(t["entry_t"])].append(t)
    for y in sorted(by_y):
        rs = [t["r"] for t in by_y[y]]
        mo = defaultdict(float)
        for t in by_y[y]:
            mo[time.strftime("%m", time.gmtime(t["entry_t"]))] += t["r"]
        row(rep, [str(y), str(len(rs)), "%.0f" % (100.0 * sum(r > 0 for r in rs) / len(rs)),
                  "%+.1f" % sum(rs), "%+.3f" % mean(rs), "%.3f" % se(rs),
                  "%d/%d" % (sum(v > 0 for v in mo.values()), len(mo))], widths)

    rep.p("")
    rep.p("  by exit:")
    widths = [14, 8, 10, 10]
    row(rep, ["exit", "trades", "total R", "avg R"], widths)
    by_x = defaultdict(list)
    for t in ft:
        by_x[t["reason"]].append(t["r"])
    for k in sorted(by_x, key=lambda k: -len(by_x[k])):
        row(rep, [k, str(len(by_x[k])), "%+.1f" % sum(by_x[k]), "%+.2f" % mean(by_x[k])], widths)

    rep.p("")
    rep.p("  by direction:")
    for d, nm in ((1, "long"), (-1, "short")):
        rs = [t["r"] for t in ft if t["dir"] == d]
        if rs:
            rep.p("    %-6s %4d trades | win %.0f%% | total %+.1fR | exp %+.3fR" %
                  (nm, len(rs), 100.0 * sum(r > 0 for r in rs) / len(rs), sum(rs), mean(rs)))

    rep.p("")
    rep.p("  skipped signals / days (flat run): " + ", ".join("%s %d" % kv for kv in sorted(flat["skips"].items())))

    # ---------------- equity ----------------
    rep.p("")
    rep.p("-" * 78)
    rep.p("2. ACCOUNT  --  flat 1% vs Equity Pulse")
    rep.p("-" * 78)
    for nm, res in (("flat 1%*", flat), ("pulse", pul)):
        bals = [START_BALANCE] + [START_BALANCE + sum(t["net"] for t in res["trades"][:i + 1]) for i in range(len(res["trades"]))]
        dd = max_dd(bals)
        pk = max(bals)
        rep.p("  %-8s final $%.0f (%+.1f%%) | trades %d | max drawdown $%.0f (%.1f%% of peak equity)" %
              (nm, res["bal"], 100.0 * (res["bal"] / START_BALANCE - 1), len(res["trades"]), dd, 100.0 * dd / pk))
    rep.p("  * flat has no daily/lifetime limits, so it shows the strategy uninterrupted")
    rep.p("")
    rep.p("  pulse by year (balance change):")
    yb = defaultdict(float)
    for t in pt:
        yb[year_of(t["entry_t"])] += t["net"]
    yf = defaultdict(float)
    for t in ft:
        yf[year_of(t["entry_t"])] += t["net"]
    widths = [8, 14, 14]
    row(rep, ["year", "flat $", "pulse $"], widths)
    for y in sorted(set(yb) | set(yf)):
        row(rep, [str(y), "%+.0f" % yf[y], "%+.0f" % yb[y]], widths)
    p = pul["pulse"]
    rep.p("")
    rep.p("  pulse events: " + ", ".join("%s %d" % kv for kv in sorted(p.ev.items())))
    rep.p("  final x $%.2f | decay %.0f%% | skipped by pulse: %d | releases: %d" %
          (p.x, 100 * p.decay, pul["skips"].get("pulse_cushion", 0), p.ev.get("release", 0)))
    dt = [t for t in pt if t["mode"] == "gain_defence"]
    if dt:
        act = sum(t["net"] for t in dt)
        full = sum(t["r"] * t["bal_at_entry"] * RISK_PCT / 100.0 for t in dt)
        rep.p("  trades taken in gain defence: %d | they made $%+.0f; at full 1%% size they'd have made $%+.0f" %
              (len(dt), act, full))
        rep.p("  -> pulse premium on defended trades: $%+.0f (positive = pulse cost money, negative = it saved money)" % (full - act))
    if p.lifetime_halted:
        rep.p("  !! LIFETIME HALT on %s: the account fell 10%% below $%.0f and the bot stopped there."
              % (p.halt_day, EP_BASELINE))
        rep.p("  !! Everything after that date exists only in the flat run.")

    # ---------------- excursion ----------------
    rep.p("")
    rep.p("-" * 78)
    rep.p("3. HOW TRADES MOVE  (flat run; best/worst move measured on M15 bars + exit price)")
    rep.p("-" * 78)
    we = [t for t in ft if t["reason"] == "window_end"]
    if we:
        mf = [t["mfe"] / t["rd"] for t in we]
        ex = [t["exit_move"] / t["rd"] for t in we]
        rep.p("  clock exits: avg best point %+.2fR | avg exit %+.2fR | avg given back %.2fR" %
              (mean(mf), mean(ex), mean(mf) - mean(ex)))
        rep.p("  clock exits that were at >= +1R at some point: %d of %d (%.0f%%)" %
              (sum(x >= 1 for x in mf), len(mf), 100.0 * sum(x >= 1 for x in mf) / len(mf)))
    so = [t for t in ft if t["reason"] == "StopLoss"]
    if so:
        mf = [t["mfe"] / t["rd"] for t in so]
        rep.p("  stop-outs by best point first reached: <0.25R %d | 0.25-0.5R %d | 0.5-1R %d | >=1R %d  (of %d)" %
              (sum(x < .25 for x in mf), sum(.25 <= x < .5 for x in mf), sum(.5 <= x < 1 for x in mf),
               sum(x >= 1 for x in mf), len(mf)))
    hr = defaultdict(list)
    for t in ft:
        for h_, r_ in t["hour_r"]:
            hr[h_].append(r_)
    if hr:
        rep.p("  average open R by hour (UTC): " + "  ".join("%02d:%+.2f" % (h_, mean(hr[h_])) for h_ in sorted(hr)))
    mh = defaultdict(int)
    for t in ft:
        if t["mfe_t"] is not None:
            mh[time.gmtime(t["mfe_t"]).tm_hour] += 1
    if mh:
        rep.p("  hour the best point was reached:  " + "  ".join("%02d:%d" % (h_, mh[h_]) for h_ in sorted(mh)))

    # ---------------- adaptive TP shadow ----------------
    rep.p("")
    rep.p("-" * 78)
    rep.p("4. ADAPTIVE TP  --  SHADOW ONLY (pulse run). delta = shadow exit R - real exit R, before costs")
    rep.p("-" * 78)
    ad = [(t, t["atp"]["exit_r"] - t["exit_move"] / t["rd"]) for t in pt if t["atp"]["exit_r"] is not None]
    if ad:
        rep.p("  total delta %+.1fR over %d trades (%+.3fR per trade)" % (sum(d for _, d in ad), len(ad), mean([d for _, d in ad])))
        for label, keyf in (("by decision", lambda t: t["atp"]["reason"]),
                            ("by account state at decision", lambda t: t["atp"]["state"]),
                            ("by goal reached", lambda t: t["atp"]["goals"])):
            g = defaultdict(list)
            for t, d in ad:
                g[keyf(t)].append(d)
            rep.p("  %s:" % label)
            for k in sorted(g, key=lambda k: -len(g[k])):
                rep.p("    %-30s %4d trades | delta %+.1fR | %+.3fR each | better %d / worse %d" %
                      (k, len(g[k]), sum(g[k]), mean(g[k]), sum(d > 0 for d in g[k]), sum(d < 0 for d in g[k])))
        clipped = [t for t, d in ad if t["atp"]["reason"] in ("lock", "trail") and t["reason"] == "TakeProfit"]
        rep.p("  real 2R winners the shadow would have cut early: %d" % len(clipped))
        rep.p("  learned buckets at the end: " + ", ".join("%s n=%d avg hold %+.2fR" % (k, v[1], v[0] / v[1])
                                                          for k, v in sorted(pul["atp"].stats.items())))

    rep.p("")
    rep.p("runtime %.1fs" % (time.time() - t_start))
    rep.save()


# ============================================================================
# STUDY: what goes with the strategy working?  (python asiabo_offline.py study)
# ============================================================================
STUDY_SPLIT = "2024-01-01"     # features are judged on data BEFORE this date, then checked once on data after it
STUDY_RANDOM_SEEDS = 200       # random-direction null
STUDY_RANDOM_TIME_SEEDS = 10   # random-time null (slower)


def day_exit_ts(t):
    g = time.gmtime(t)
    return epoch_of("%04d-%02d-%02d" % (g.tm_year, g.tm_mon, g.tm_mday)) + WINDOW_END_HOUR * 3600 + 900


def sim_light(m, i0, d, entry, rd, exit_ts):
    """One trade on M1: stop before target, gaps at the open, flat at exit_ts.
    Returns (R before costs, R net of costs, {hour: R at :59 incl. closed trades' final R})."""
    sl = entry - d * rd
    tp = entry + d * TARGET_R * rd
    snaps = {}
    done_r = None
    last_c = entry
    i = i0
    while i < m.n and m.ts[i] < exit_ts:
        o, h, l, c = m.o[i], m.h[i], m.l[i], m.c[i]
        if done_r is None:
            if d > 0:
                if l <= sl: done_r = (min(o, sl) - entry) / rd
                elif h >= tp: done_r = (max(o, tp) - entry) / rd
            else:
                if h >= sl: done_r = (entry - max(o, sl)) / rd
                elif l <= tp: done_r = (entry - min(o, tp)) / rd
            last_c = c
        g = time.gmtime(m.ts[i])
        if g.tm_min == 59:
            snaps[g.tm_hour + 1] = done_r if done_r is not None else (c - entry) * d / rd
            if done_r is not None and g.tm_hour + 1 >= WINDOW_END_HOUR:
                break
        i += 1
    r = done_r if done_r is not None else (last_c - entry) * d / rd
    cost_r = entry * COST_BP / 1e4 / rd
    return r, r - cost_r, snaps


def daily_table(bars):
    days, by = [], {}
    for b in bars:
        g = time.gmtime(b[0])
        k = "%04d-%02d-%02d" % (g.tm_year, g.tm_mon, g.tm_mday)
        if k not in by:
            by[k] = [b[1], b[2], b[3], b[4]]
            days.append(k)
        else:
            x = by[k]
            x[1] = max(x[1], b[2]); x[2] = min(x[2], b[3]); x[3] = b[4]
    # drop thin days (Sunday evening stubs) from the "previous day" chain
    full = [k for k in days if datetime.date(*map(int, k.split("-"))).weekday() < 5]
    return full, by


def features(t, days, by, idx):
    d = t["dir"]
    f = {}
    f["direction"] = "long" if d > 0 else "short"
    f["weekday"] = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][datetime.date(*map(int, t["day"].split("-"))).weekday()]
    hr = time.gmtime(t["entry_t"] - 900).tm_hour
    f["entry hour"] = "07-08" if hr < 9 else ("09-11" if hr < 12 else "12-15")
    f["box size (ATR)"] = t["range_ratio"]
    f["box size (% of price)"] = (t["box_hi"] - t["box_lo"]) / t["entry"] * 100
    edge = t["box_hi"] if d > 0 else t["box_lo"]
    f["breakout extent (ATR)"] = (t["signal_close"] - edge) * d / t["atr"] if t["atr"] else None
    pos = (t["box_end_close"] - t["box_lo"]) / max(1e-9, t["box_hi"] - t["box_lo"])
    f["box-end position (toward trade)"] = pos if d > 0 else 1 - pos
    i = idx.get(t["day"])
    if i is not None and i >= 21:
        pd_ = by[days[i - 1]]
        f["prior day with trade"] = ("with" if (pd_[3] - pd_[0]) * d > 0 else "against")
        sma = sum(by[days[j]][3] for j in range(i - 20, i)) / 20.0
        f["20-day trend with trade (%)"] = (t["entry"] - sma) * d / t["entry"] * 100
        rngs = [by[days[j]][1] - by[days[j]][2] for j in range(i - 21, i - 1)]
        f["volatility regime (prev day / 20d avg)"] = (pd_[1] - pd_[2]) / (sum(rngs) / len(rngs))
    return f


def bucket_stats(rs):
    return len(rs), mean(rs), se(rs)


def run_study(start, end):
    check_window_unsealed(start, end)
    rep = Report("asiabo_study")
    t_start = time.time()
    m = load_m1(start, end)
    bars, atr = build_m15(m)
    split = epoch_of(STUDY_SPLIT)
    flat = simulate(m, bars, atr, False)
    tr = [t for t in flat["trades"] if t["reason"] != "data_end"]
    days, by = daily_table(bars)
    idx = {k: i for i, k in enumerate(days)}

    rep.p("=" * 78)
    rep.p("ASIA BREAKOUT  --  STUDY: what goes with the strategy working?")
    rep.p("=" * 78)
    rep.p("data %s .. %s | %d trades (flat 1%%, same rules as the main report)" %
          (time.strftime("%Y-%m-%d", time.gmtime(m.ts[0])), time.strftime("%Y-%m-%d", time.gmtime(m.ts[-1])), len(tr)))
    rep.p("DISCOVERY = before %s, CONFIRM = from %s on. A feature only counts if it shows up in BOTH." % (STUDY_SPLIT, STUDY_SPLIT))
    rep.p("All R is net of costs. +/- is one standard error. With ~30 buckets, expect 1-2 to look 'significant' by luck.")

    # ---- re-simulate every trade both ways with the light simulator (also a cross-check) ----
    both = []
    for t in tr:
        ex = day_exit_ts(t["entry_t"])
        same = sim_light(m, t["i_next"], t["dir"], t["entry"], t["rd"], ex)
        flip = sim_light(m, t["i_next"], -t["dir"], t["entry"], t["rd"], ex)
        both.append((t, same, flip))
    real = [s[1] for _, s, _ in both]
    flipped = [f[1] for _, _, f in both]

    rep.p("")
    rep.p("-" * 78)
    rep.p("A. DOES THE BREAKOUT DIRECTION MATTER?  (same entries, same stop distance, same exits)")
    rep.p("-" * 78)
    rep.p("  cross-check: light simulator %+.3fR/trade vs main simulator %+.3fR/trade (should be close)" %
          (mean(real), mean([t["r"] for t in tr])))
    rep.p("  strategy direction : %+.3fR per trade (+/- %.3f)" % (mean(real), se(real)))
    rep.p("  OPPOSITE direction : %+.3fR per trade (+/- %.3f)" % (mean(flipped), se(flipped)))
    rng = random.Random(7)
    rand_means = []
    for _ in range(STUDY_RANDOM_SEEDS):
        rand_means.append(mean([s[1] if rng.random() < 0.5 else f[1] for _, s, f in both]))
    rand_means.sort()
    pct = 100.0 * sum(x < mean(real) for x in rand_means) / len(rand_means)
    rep.p("  RANDOM direction   : %+.3fR per trade on average over %d shuffles (middle 90%%: %+.3f .. %+.3f)" %
          (mean(rand_means), len(rand_means), rand_means[int(.05 * len(rand_means))], rand_means[int(.95 * len(rand_means)) - 1]))
    rep.p("  -> the real direction beats %.0f%% of random-direction shuffles (95%%+ would mean the direction carries signal)" % pct)
    for lab, lo_, hi_ in (("discovery", 0, split), ("confirm", split, 1e18)):
        a = [s[1] for t, s, _ in both if lo_ <= t["entry_t"] < hi_]
        b = [f[1] for t, _, f in both if lo_ <= t["entry_t"] < hi_]
        rep.p("    %-9s  strategy %+.3fR (+/- %.3f)  vs opposite %+.3fR (+/- %.3f)   n=%d" %
              (lab, mean(a), se(a), mean(b), se(b), len(a)))

    # ---- afternoon drift without survivorship bias ----
    rep.p("")
    rep.p("-" * 78)
    rep.p("B. THE AFTERNOON DRIFT, MEASURED HONESTLY")
    rep.p("-" * 78)
    rep.p("  The main report's 'open R by hour' only averages trades still open, so stopped trades drop out")
    rep.p("  and the line drifts up even with zero edge (survivorship). Here closed trades keep their final R.")
    hrs = list(range(9, WINDOW_END_HOUR + 1))

    def profile(snaps_list):
        out = []
        for h in hrs:
            vals, last = [], None
            for sn in snaps_list:
                v = None
                for hh in range(h, 6, -1):
                    if hh in sn:
                        v = sn[hh]; break
                if v is not None:
                    vals.append(v)
            out.append(mean(vals) if vals else 0.0)
        return out

    ps = profile([s[2] for _, s, _ in both])
    pf = profile([f[2] for _, _, f in both])
    rep.p("  hour (UTC)       " + "".join("%7s" % ("%02d" % h) for h in hrs))
    rep.p("  strategy         " + "".join("%+7.2f" % v for v in ps))
    rep.p("  opposite         " + "".join("%+7.2f" % v for v in pf))

    # random-time entries on the same days, random direction, same stop distance
    rt_snaps, rt_r = [], []
    for seed in range(STUDY_RANDOM_TIME_SEEDS):
        r2 = random.Random(100 + seed)
        for t, _, _ in both:
            day0 = epoch_of(t["day"])
            k_ts = day0 + RANGE_END_HOUR * 3600 + 900 * r2.randrange(0, (WINDOW_END_HOUR - RANGE_END_HOUR) * 4)
            # first M1 index at/after k_ts (search forward from the strategy's entry neighbourhood)
            i = t["i_next"]
            while i > 0 and m.ts[i - 1] >= k_ts:
                i -= 1
            while i < m.n and m.ts[i] < k_ts:
                i += 1
            if i >= m.n:
                continue
            dd = 1 if r2.random() < 0.5 else -1
            res = sim_light(m, i, dd, m.o[i], t["rd"], day_exit_ts(t["entry_t"]))
            rt_r.append(res[1]); rt_snaps.append(res[2])
    pr = profile(rt_snaps)
    rep.p("  random time+dir  " + "".join("%+7.2f" % v for v in pr))
    rep.p("  random time+direction overall: %+.3fR per trade (+/- %.3f), n=%d" % (mean(rt_r), se(rt_r), len(rt_r)))
    rep.p("  -> a real drift shows as the strategy line climbing while random stays near its cost level.")

    # ---- features ----
    rep.p("")
    rep.p("-" * 78)
    rep.p("C. FEATURES KNOWN AT ENTRY vs RESULT  (expectancy R per trade, by bucket)")
    rep.p("-" * 78)
    rows = []
    for (t, s, _) in both:
        rows.append((t, features(t, days, by, idx), s[1]))
    disc = [x for x in rows if x[0]["entry_t"] < split]
    conf = [x for x in rows if x[0]["entry_t"] >= split]
    base_d = mean([r for _, _, r in disc]); base_c = mean([r for _, _, r in conf])
    rep.p("  baseline: discovery %+.3fR (n=%d) | confirm %+.3fR (n=%d)" % (base_d, len(disc), base_c, len(conf)))
    rep.p("  'holds' = beats the baseline by > 2 se in discovery AND by > 1 se in confirm, same direction")
    keys = []
    for _, f, _ in rows:
        for k in f:
            if k not in keys:
                keys.append(k)
    # bucket every trade once (tercile cut points come from discovery only)
    labels = {}     # key -> (bucket order, [bucket of each row])
    for k in keys:
        vals = [f[k] for _, f, _ in disc if f.get(k) is not None]
        if not vals:
            continue
        if isinstance(vals[0], float):
            sv = sorted(vals)
            c1, c2 = sv[len(sv) // 3], sv[2 * len(sv) // 3]
            names = ["low (< %.2f)" % c1, "mid", "high (> %.2f)" % c2]
            lab = [None if f.get(k) is None else (names[0] if f[k] < c1 else (names[1] if f[k] < c2 else names[2]))
                   for _, f, _ in rows]
            labels[k] = (names, lab)
        else:
            lab = [f.get(k) for _, f, _ in rows]
            labels[k] = (sorted(set(v for v in lab if v is not None)), lab)
    is_disc = [x[0]["entry_t"] < split for x in rows]

    def evaluate(rvals):
        bd = mean([r for r, dsc in zip(rvals, is_disc) if dsc])
        bc = mean([r for r, dsc in zip(rvals, is_disc) if not dsc])
        out, table = [], []
        for k, (order, lab) in labels.items():
            for bname in order:
                a_ = [r for r, l_, dsc in zip(rvals, lab, is_disc) if l_ == bname and dsc]
                c_ = [r for r, l_, dsc in zip(rvals, lab, is_disc) if l_ == bname and not dsc]
                if len(a_) < 10 or len(c_) < 5:
                    continue
                ma, sa, mc, sc = mean(a_), se(a_), mean(c_), se(c_)
                flag = ""
                if ma - bd > 2 * sa and mc - bc > sc:
                    flag = "<- holds (better)"
                elif bd - ma > 2 * sa and bc - mc > sc:
                    flag = "<- holds (worse)"
                table.append((k, bname, ma, len(a_), mc, len(c_), flag))
                if flag:
                    out.append((k, bname, ma, mc, len(a_), len(c_), flag))
        return out, table

    rvals = [r for _, _, r in rows]
    hits, table = evaluate(rvals)
    cur = None
    for k, bname, ma, na, mc, nc, flag in table:
        if k != cur:
            cur = k
            rep.p("")
            rep.p("  %s" % k)
            rep.p("    %-26s %18s %18s" % ("bucket", "discovery", "confirm"))
        rep.p("    %-26s %+7.3f n=%-4d     %+7.3f n=%-4d    %s" % (bname, ma, na, mc, nc, flag))

    # how many 'holds' would pure luck produce? shuffle results across trades within each period
    shuf = []
    r3 = random.Random(11)
    dv = [r for r, dsc in zip(rvals, is_disc) if dsc]
    cv = [r for r, dsc in zip(rvals, is_disc) if not dsc]
    for _ in range(100):
        r3.shuffle(dv); r3.shuffle(cv)
        it_d, it_c = iter(dv), iter(cv)
        fake = [next(it_d) if dsc else next(it_c) for dsc in is_disc]
        shuf.append(len(evaluate(fake)[0]))
    shuf.sort()

    rep.p("")
    rep.p("-" * 78)
    rep.p("D. SHORTLIST  (buckets that held in both periods)")
    rep.p("-" * 78)
    rep.p("  real data: %d bucket(s) held | shuffled results (no real link to any feature): %.1f on average, 95th pct %d"
          % (len(hits), mean(shuf), shuf[94]))
    if len(hits) <= shuf[94]:
        rep.p("  -> NOT more than luck produces. Treat everything below as noise until proven otherwise.")
    else:
        rep.p("  -> more than luck usually produces: worth a closer look, one candidate at a time.")
    if not hits:
        rep.p("  none. Nothing known at entry separated good trades from bad ones in both periods.")
    for k, b_, ma, mc, na, nc, flag in hits:
        rep.p("  %-40s %-20s disc %+.3fR (n=%d) | conf %+.3fR (n=%d)  %s" % (k, b_, ma, na, mc, nc, flag))
    rep.p("  A shortlisted bucket is a CANDIDATE, not a result: a filter built from it needs a fresh test")
    rep.p("  (forward on paper), because the confirm period has now been looked at.")
    rep.p("")
    rep.p("runtime %.1fs" % (time.time() - t_start))
    rep.save()


# ============================================================================
# COLLECT: research data collection  (python asiabo_offline.py collect)
#
# Runs EVERY lane in shadow (no sizing, no Equity Pulse) and writes one row per trade with what was
# known at entry and what happened after. Nothing here decides anything: it only measures.
#
# DATA SPLIT (fixed):  training A = before SEAL_START, training B = from SEAL_END on.
# The years in between are the EXAM. This tool refuses to load them (see load_m1) until EXAM_UNLOCK
# is set to True by hand. Each training period is run as its own segment: no trade, average or
# regime read ever spans the gap.
#
# Lane rules are the bot's (Cashbotas_main.py), written out again here because this tool shares no
# code with the bot. Known differences, all stated so results are read correctly:
#   * entry = the signal bar's close; costs = one flat round-trip charge (cost_bp of price) per trade
#   * session VWAP is the plain average of typical prices (bars.db has no tick volume)
#   * no pair-conflict rule, no promotion states: every signal of every lane is taken
# ============================================================================
SEAL_START = "2022-01-01"      # exam years start (inclusive)
SEAL_END = "2024-01-01"        # exam years end (exclusive)
EXAM_UNLOCK = False            # True ONLY for the one-shot exam run with a frozen bot

# ---- each market's own clock (TRANSLATION, not tuning: fixed by reasoning before any US 500 result) ----
# Every distance in the lanes is in the market's own ATR or daily range, so stops, targets and buffers
# carry over untouched. What does not carry over is the CLOCK: gold's day is built around the London
# open (07:00 UTC) with New York arriving at 13:00; an index has one main event, the New York cash open.
#   clock "utc": hours are UTC, as before (gold; these numbers are the old constants, nothing changed).
#   clock "ny":  New York time + 3h30, daylight saving followed, so the cash open (09:30 NY) is ALWAYS
#                lane-hour 13:00 and the cash close (16:00 NY) is 19:30. The lane day starts at 20:30 NY
#                the evening before, close to where gold's UTC day starts, so daily bars are built the
#                same way for both markets.
# US 500 hours below, in New York time:
#   box      20:30 -> 09:30  the overnight range (gold: the Asian range). Traded 09:30-15:30, flat 15:45.
#   range    fade the box edges in the cash morning only (to 12:30)        (gold: London morning, to 12:00)
#   london   box = the cash morning 09:30-12:30, broken 12:30-14:30        (gold: London morning broken by NY)
#   trend    joins the day's lean in the first cash hour; the average price's slope is measured from
#            05:30 (same four-hour gap as gold's 09:00 -> 13:00)
#   vwap     stretches faded 10:30-14:30                                   (gold: 10:00-18:00)
#   nyaft    first three cash hours, entry 12:30                           (gold: the same idea on whole hours)
#   big      entry at the cash open                                        (gold: 07:00, the London open)
#   pdh, swing, dip   entries in cash hours only                           (gold: 07:00-20:00, its active hours)
#   nr7      all hours up to 14:30, as on gold; scalp and gapfill have no clock of their own to move
CLOCK_UTC = {"clock": "utc", "box": (RANGE_START_HOUR, RANGE_END_HOUR), "win_end": WINDOW_END_HOUR,
             "box_min_bars": MIN_RANGE_BARS, "london": (7, 12, 18, 20), "london_min_bars": 16, "range_end": 12,
             "trend": (13, 9, 20), "vwap": (10, 18, 20), "ny": (13, 16, 20), "late_end": 20,
             "pdh": (7, 20), "nr7": (1, 18), "big": 7, "multi": (7, 20), "open_hours": (7, 8, 13, 14),
             "busy_hour": "13 or 14 (New York arriving)"}
CLOCK_NY = {"clock": "ny", "box": (0, 13), "win_end": 19,
            "box_min_bars": MIN_RANGE_BARS, "london": (13, 16, 18, 19), "london_min_bars": 10, "range_end": 16,
            "trend": (13, 9, 19), "vwap": (14, 18, 19), "ny": (13, 16, 19), "late_end": 19,
            "pdh": (13, 19), "nr7": (1, 18), "big": 13, "multi": (13, 19), "open_hours": (13, 14),
            "busy_hour": "13 (the cash open, 09:30 New York)"}
NY_CLOCK_SHIFT = 3.5           # lane clock = New York time + this many hours (puts the cash open on 13:00)

# ---- the European clock (FX and Germany 40) ----
# TRANSLATION, fixed by reasoning before any result, like the New York clock. Lane clock = London time - 1h
# = Berlin time - 2h (the two change on the same dates), so the London / Xetra open (08:00 London = 09:00
# Berlin) is ALWAYS lane-hour 07:00, gold's own London open, and the New York cash open is always 13:30.
# That is plain UTC in European summer time and UTC minus one hour in winter. Every lane parameter is gold's,
# unchanged; only the clock follows the market's own daylight saving. Days run 00:00 -> 24:00 on this clock.
#   box      00:00 -> 07:00  the overnight range before the London / Xetra open (gold: the Asian range)
#   others   exactly as CLOCK_UTC (london box 07-12 broken to 18, new-york lanes 13/16, exit hour 20 ...)
CLOCK_EU = dict(CLOCK_UTC)
CLOCK_EU.update({"clock": "eu", "busy_hour": "07 (London / Xetra open) or 13 (New York arriving)"})


def _eu_summer(t):
    """True while European summer time is on (last Sunday of March 01:00 UTC to last Sunday of October 01:00 UTC)."""
    y = time.gmtime(t).tm_year
    def last_sun(m):
        d = datetime.date(y, m, 31)
        return d - datetime.timedelta(days=(d.weekday() + 1) % 7)
    lo = calendar.timegm((y, 3, last_sun(3).day, 1, 0, 0))
    hi = calendar.timegm((y, 10, last_sun(10).day, 1, 0, 0))
    return lo <= t < hi


COLLECT_SYMBOLS = [
    # swap = price units per 1 unit per night (negative = you pay), worst case as in the bot.
    # xref = the markets whose shock days become this market's cross-market flag (gold and US 500 keep the pair
    # they always had, so their trades do not change when a market is added).
    {"name": "XAUUSD", "match": ["XAUUSD"], "cost_bp": COST_BP, "min_sl": MIN_SL_DISTANCE_USD,
     "swap_long": -0.805, "swap_short": -0.0192, "hours": CLOCK_UTC, "xref": ["US500"]},
    # US 500, from the broker's symbol sheet (Oct 2026): commission 0.01% of volume per side with a $4 minimum,
    # swap -1 point a night long AND short, triple on Wednesday at 20:59, smallest position 1 contract.
    #   cost_bp 3.5 = 2.0 (commission, both sides) + 1.5 for spread. The SPREAD part is still an assumption:
    #                 replace it with (typical spread in points / price x 10000) once read off the quote panel.
    #   comm_min    = the $4 minimum PER SIDE. It is a fixed dollar amount, so it depends on position size and
    #                 cannot be part of an R figure: 'collect' leaves it out, 'house' charges it (see House._exit).
    #   comm_sides  = 2 assumes the minimum is charged on the open AND the close (cTrader's usual way, and the
    #                 worse case). Set to 1 if a paper deal shows $4 for the whole round trip.
    #   min_sl 3.0  = the bot's own guard; the broker itself has no minimum stop distance.
    {"name": "US500", "match": ["US500", "SPX500", "USA500", "SP500", "US500CASH", "SPX"], "cost_bp": 3.5,
     "min_sl": 3.0, "swap_long": -1.0, "swap_short": -1.0, "hours": CLOCK_NY,
     "comm_pct": 0.01, "comm_min": 4.0, "comm_sides": 2, "xref": ["XAUUSD"]},
    # ---- added 2026-10-07, from the broker's symbol sheets. NOTHING below was tuned on a result. ----
    # cost_bp = round-trip basis points of price (commission both sides + a spread allowance);
    # cost_px = a spread allowance in PRICE units added on top (for markets where the spread is a fixed number
    #           of pips, so its size in bp moves with the price: oil);
    # swap in price units = sheet pips x pip size. Credits are NOT counted (worst case).
    # EURUSD: commission $45 per million USD = 0.45 bp a side = 0.9 bp round trip. Spread in the data averages
    #   0.2-0.5 pip in 2020-26 (1 pip in 2014-15), so 1.1 bp more is an allowance for a bad day. Swap long
    #   -2.445 pips, short -0.105 pips, triple on Wednesday, 20:59. Pip 0.0001, min trade 0.01 lot, 1:100.
    {"name": "EURUSD", "match": ["EURUSD"], "cost_bp": 2.0, "min_sl": 0.0005,
     "swap_long": -2.445e-4, "swap_short": -1.05e-5, "hours": CLOCK_EU, "xref": ["XAUUSD", "US500"],
     "min_unit": 1000.0, "quote": "usd"},
    # USDJPY: commission $45 per million USD = 0.9 bp round trip, +1.1 bp allowance (0.5 pip is 0.33 bp at 150).
    #   Swap long -0.345 pips, short -2.295 pips; pip 0.01 (JPY per USD). Min trade 0.01 lot, 1:100.
    {"name": "USDJPY", "match": ["USDJPY"], "cost_bp": 2.0, "min_sl": 0.05,
     "swap_long": -0.00345, "swap_short": -0.02295, "hours": CLOCK_EU, "xref": ["XAUUSD", "US500"],
     "min_unit": 1000.0, "quote": "jpy"},
    # WTI (XTIUSD): commission $40 per million USD = 0.8 bp round trip (1.0 here). The spread is the cost that
    #   matters: it averages 3.3-6.4 pips in the data, i.e. $0.03-0.06 a barrel, so cost_px 0.07 = 7 pips
    #   (about 10 bp at $70, far more at $20). Swap long -1.3275 pips = -0.013275; the sheet's SHORT swap is a
    #   +0.4375 pip CREDIT, left out (worst case). Lot 100 barrels, min trade 0.10 lot, 1:14.
    #   Clock: the New York clock as it stands (09:30 NY = lane 13:00; the pit opens at 09:00, so the lane's
    #   first hour is 30 minutes after it).
    {"name": "XTIUSD", "match": ["XTIUSD", "USOIL", "WTI", "WTIUSD", "CRUDEOIL"], "cost_bp": 1.0, "cost_px": 0.07,
     "min_sl": 0.15, "swap_long": -0.013275, "swap_short": 0.0, "hours": CLOCK_NY, "xref": ["XAUUSD", "US500"],
     "min_unit": 10.0, "quote": "usd"},
    # Germany 40: commission 0.01% of volume a side with a $4 minimum (same terms as US 500), swap -1.5 points
    #   both ways. cost_bp 3.5 = 2.0 commission + 1.5 spread allowance (the data's spread is 0.3-1.4 points on
    #   ~15,000-24,000, i.e. under 1 bp). Min trade 1 lot (1 contract), 1:20, no minimum stop distance.
    #   The broker's history holds only 07:00-19:00 UTC until 2024 (24 hours from 2025): the overnight box is
    #   missing in the early years and those box days are skipped, exactly as on US 500.
    {"name": "GERMANY40", "match": ["GERMANY40", "DE40", "DE30", "GER40", "GER30", "DAX40", "DAX"], "cost_bp": 3.5,
     "min_sl": 10.0, "swap_long": -1.5, "swap_short": -1.5, "hours": CLOCK_EU,
     "comm_pct": 0.01, "comm_min": 4.0, "comm_sides": 2, "xref": ["XAUUSD", "US500"],
     "min_unit": 1.0, "quote": "eur"},
]
SWAP_TRIPLE_WEEKDAY = 2        # Wednesday night counts 3
SWAP_HOUR, SWAP_MINUTE = 20, 59

# ---- DATA QUALITY (see the DATA QUALITY block below) ----
COLLECT_FROM = "2020-01-01"    # 'collect' reads bars from this date unless you give a start date on the command line.
                               # bars.db now reaches back to 2013 for gold, so WITHOUT this line period A would silently
                               # grow from 2020-2021 to 2013-2021 and every number would change. Set it earlier on purpose.
CLEAN_ONLY = True              # analysis and the house run on clean trades; cut ones go to trades_<symbol>_cut.csv
DIRTY_MIN_MINUTES = 120        # an unexplained hole this long or longer cuts the data (same rule as gaps_to_check.csv)
STRICT_WARMUP = True           # a trade is cut too when a hole sits in the WARM_DAYS weekdays before it
WARM_DAYS = 20                 # the longest look-back that decides a signal (20-day high/low, 20-day average, ER20)
SENSITIVITY_MINUTES = (5, 30, 60, 120, 360)   # the report shows what each cutting threshold would cost

# ---- lane parameters (copied from the bot's config) ----
C_LONDON = (7, 12, 18, 20, 2.0)          # box start, box end, entry end, exit hour, target R
C_FADE_STOP_ATR, C_FADE_MIN_R = 0.10, 1.0
C_SAR_R = 1.5
C_RETEST_TOUCH_ATR, C_RETEST_R = 0.10, 2.0
C_RANGE = (12, 0.25, 0.25, 0.8)          # entry end hour, edge zone ATR, stop ATR, min target R
C_EXH = (3.0, 1.0, 0.10, 1.0)            # extension ATR, pullback ATR, stop ATR, min target R
C_TREND = (13, 9, 1.0, 0.5, 2.0, 20)     # entry hour, slope-from hour, min dist ATR, stop ATR, target R, exit hour
C_VWAP = (10, 18, 3.0, 0.25, 1.0, 20)    # start, entry end, stretch ATR, stop ATR, min target R, exit hour
C_NY = (13, 16, 2.0, 1.5, 20)            # NY open hour, afternoon hour, min move ATR, target R, exit hour
C_SCALP = (1.0, 0.25, 1.0, 4)            # impulse ATR, close zone, target R, max hold bars
C_PDH = (0.10, 7, 20, 2.0, 288)          # buffer ATR, entry start, entry end, target R, max hold bars
C_NR = (7, 2.0)                          # lookback days, target R
C_BIG = (2.0, 0.25, 14, 7, 0.5, 1.0)     # range mult, close zone, avg days, entry hour, stop frac, target R
C_GAP = (0.5, 96)                        # min gap ATR, max hold bars

# ---- the two multi-day lanes (rules fixed before any data; textbook numbers, nothing tuned) ----
SWING_ENTRY_DAYS = 20          # swing: first M15 close beyond the 20-day high/low
SWING_EXIT_DAYS = 10           # ... out on an M15 close beyond the 10-day extreme on the other side
SWING_STOP_RANGES = 2.0        # ... initial stop = 2 average daily ranges
SWING_MAX_HOLD_BARS = None     # no time cap: trend following lives on its few very long winners (was 20 days)
DIP_AVG_DAYS = 20              # dip: daily close above a RISING 20-day average (mirror for shorts) ...
DIP_RISING_DAYS = 5            # ... rising = higher than it was 5 days ago
DIP_PULLBACK_DAYS = 2          # ... after 2 lower closes in a row, enter on the first M15 close back above
DIP_TARGET_R = 2.0             #     yesterday's high. Stop under the pullback low. Target 2R.
DIP_MAX_HOLD_BARS = 5 * 96     # ... held up to ~5 trading days
MULTI_ENTRY_HOURS = (7, 20)    # entries for both between 07:00 and 20:00

# ---- fixes on OUR side of the trade (execution, not the idea) ----
# STOP MENU: every trade is replayed with its stop at these multiples of the lane's own stop distance.
# Same entry, same target PRICE, same clock. Each result is in ITS OWN R (risk = the new stop distance),
# so a wider stop is not flattered by being measured against the old, smaller risk.
STOP_MENU = (0.5, 1.5, 2.0, 3.0)
# ENTRY DELAY: every trade is replayed entering this many M15 bars later, at that bar's close, but only
# if the setup is still intact (the original stop and target were not touched meanwhile and the target
# is still ahead). Same stop and target prices; result in its own R (risk = new entry to the stop).
DELAY_MENU = (1, 2)
# COST RULE: a trade whose stop is under this many round-trip costs pays more than 1/N of its risk in
# costs before it starts. Nothing is removed: each trade is marked, and the report shows lanes both ways.
COST_MIN_STOP_MULT = 10.0

FAMILY = {"main": "breakout", "london": "breakout", "pdh": "breakout", "nr7": "breakout", "retest": "breakout",
          "fade": "reversal", "sar": "reversal", "range": "reversal", "exhaust": "reversal", "vwap": "reversal",
          "gapfill": "reversal", "bigrev": "reversal",
          "trend": "momentum", "nyaft": "momentum", "scalp": "momentum", "bigcont": "momentum",
          "swing": "swing", "dip": "swing", "control": "control"}
FAMILIES = ["breakout", "reversal", "momentum", "swing"]

# ---- the signals, with the direction THEORY says they should work in (written before looking) ----
# +1 = higher value should mean better trades, -1 = lower value should mean better trades.
SIGNAL_TESTS = {
    "breakout": [("setup_range_rel", -1, "setup range small vs recent daily ranges (quiet before expansion)"),
                 ("trend20_with", +1, "break goes with the 20-day trend"),
                 ("open_hours", +1, "break in the London/New York open hours"),
                 ("bar_extreme", +1, "breakout bar closes near its extreme"),
                 ("room_r", +1, "room before yesterday's high/low")],
    "reversal": [("er20", -1, "recent days made little net progress"),
                 ("trend20_with", +1, "trade goes with the 20-day trend, not against it"),
                 ("stretch_atr", +1, "bigger stretch from fair value (VWAP)"),
                 ("hour", +1, "later in the session")],
    "momentum": [("trend20_with", +1, "intraday lean matches the 20-day trend"),
                 ("day_used", -1, "day has NOT already used most of its usual range"),
                 ("volrank", +1, "volatility high against its own history")],
    "swing": [("er20", +1, "market has been moving in a straight line")],
}
# regime reads at two speeds: no direction predicted, so they are judged two-sided and more strictly
REGIME_READS = ["er5", "er20", "trend5_with", "vol3rel", "volrank", "turning", "asia_rel", "day_eff"]
PASS_Z = 2.0            # predicted-direction signals: combined z >= this ...
PASS_EACH_Z = 1.0       # ... AND at least this in EACH period (one strong period cannot carry a weak one)
EXPLORE_Z = 2.5         # regime reads (two-sided): same sign in both periods and |combined z| >= this

REG_ER_DAYS, REG_ER_TREND, REG_ER_CHOP = 20, 0.30, 0.12
REG_VOL_DAYS, REG_VOL_RANK_DAYS, REG_VOL_HIGH, REG_CONFIRM = 14, 120, 0.80, 2
FAST_DAYS, FAST_ER_TREND = 5, 0.50      # the fast trend read: 5-day efficiency ratio at or above 0.50
EPISODE_MIN_DAYS = 5                    # a hindsight trend episode must last at least this long
STANDASIDE_SHOCK = 2.0                  # yesterday's range >= this x the 20-day average
STANDASIDE_GAP = 0.25                   # today's open this share of an average daily range away from the last close


def sealed(ts):
    return (not EXAM_UNLOCK) and epoch_of(SEAL_START) <= ts < epoch_of(SEAL_END)


def check_window_unsealed(start, end):
    """The older single-lane modes run one continuous simulation, so they may not straddle the exam."""
    if EXAM_UNLOCK:
        return
    if start < epoch_of(SEAL_END) and end > epoch_of(SEAL_START):
        raise RuntimeError(
            "This window touches the sealed exam years (%s to %s).\n"
            "Give a window outside them, e.g.  2024-01-01 2100-01-01   or   2020-01-01 2022-01-01\n"
            "(or use 'collect', which runs both training periods and skips the exam by itself)." % (SEAL_START, SEAL_END))


def _ny_open_hm(t0):
    """(hour, minute) of the NY cash open in UTC: 13:30 in US daylight time, else 14:30."""
    g = time.gmtime(t0)
    y = g.tm_year
    mar1 = datetime.date(y, 3, 1)
    dst_start = mar1 + datetime.timedelta(days=(6 - mar1.weekday()) % 7 + 7)
    nov1 = datetime.date(y, 11, 1)
    dst_end = nov1 + datetime.timedelta(days=(6 - nov1.weekday()) % 7)
    d = datetime.date(y, g.tm_mon, g.tm_mday)
    return (13, 30) if dst_start <= d < dst_end else (14, 30)


_LANE_SHIFT_CACHE = {}


def _clock_shift(H, t):
    """Seconds to ADD to a UTC time to get the market's lane clock. 'utc': 0. 'ny': New York time +
    NY_CLOCK_SHIFT hours (UTC minus 30 minutes in US daylight time, minus 90 in winter). 'eu': London time
    minus 1h = Berlin time minus 2h (0 in European summer time, minus one hour in winter)."""
    c = H["clock"]
    if c == "utc":
        return 0.0
    key = (c, int(t // 86400))
    sh = _LANE_SHIFT_CACHE.get(key)
    if sh is None:
        if c == "ny":
            sh = ((-4.0 if _ny_open_hm(t) == (13, 30) else -5.0) + NY_CLOCK_SHIFT) * 3600.0
        elif c == "eu":
            sh = 0.0 if _eu_summer(t) else -3600.0
        else:
            raise ValueError("unknown clock %r" % c)
        _LANE_SHIFT_CACHE[key] = sh
    return sh


def _cost_px(sym, entry):
    """Round-trip cost of a trade in PRICE units: cost_bp of the price, plus cost_px (a fixed spread allowance)."""
    return abs(entry) * sym["cost_bp"] / 1e4 + sym.get("cost_px", 0.0)


def lane_clock(hours, t0):
    """(hour, minute, day key) on the market's own lane clock (see _clock_shift)."""
    if hours["clock"] != "utc":
        t0 = t0 + _clock_shift(hours, t0)
    g = time.gmtime(t0)
    return g.tm_hour, g.tm_min, "%04d-%02d-%02d" % (g.tm_year, g.tm_mon, g.tm_mday)


def _scalp_open_hm(H, t0):
    """Lane (hour, minute) of the New York cash open, the bar the scalp lane looks at."""
    if H["clock"] == "ny":
        return 13, 0
    h, m = _ny_open_hm(t0)
    sec = h * 3600 + m * 60 + _clock_shift(H, t0)
    return int(sec // 3600) % 24, int(sec % 3600 // 60)


# ============================================================================
# DATA QUALITY: know what every run actually touched, and never let a hole in the data become a result.
#
# build_bars_db.py already finds every hole and writes it into bars.db's 'gaps' table, labelled weekend /
# daily_break / other and tagged with the holiday or market event that explains it, if any. Here those labels
# decide what counts as a CUT:
#   * normal closures (weekend, the symbol's nightly break, a holiday or a known event) are NOT cuts: the
#     market really was shut, nothing is missing.
#   * a hole with no explanation, DIRTY_MIN_MINUTES or longer, IS a cut (the same rule that fills
#     gaps_to_check.csv, so the two files always agree).
# What a cut does, without touching how any lane trades (the engine is unchanged, so every trade is the same
# trade as before, only now labelled):
#   * a lane-day is cut for a lane if a hole lies inside that lane's own window of the day (lane-day start to
#     its exit hour; a multi-day lane's window is the whole day). A hole at 03:00 spoils the Asian box but not
#     the New York open.
#   * a trade is cut if it was open while a hole passed (its exit would be a price jump across the hole, not
#     a market move), or if the hole is inside its entry day's window, or if a hole sits in the WARM_DAYS
#     weekdays before it (its ATR, daily ranges and trend reads were built across the hole).
#   * a TRADING DAY is a weekday the market was open, whose lane window is clean and whose reads are warm.
#     Reports count trading days and trades taken, so every result carries how much evidence is behind it.
# Everything is tagged (data_ok, cut_why in trades_*.csv; clean, reads_ok in days_*.csv). With CLEAN_ONLY the
# analysis sections and the house replay run on the clean trades; the cut ones are listed in trades_*_cut.csv.
# ============================================================================
def lane_shift_seconds(H, t):
    """Seconds to ADD to a UTC time to get the market's lane clock (see lane_clock). 0 for the utc clock."""
    return _clock_shift(H, t)


def _key_date(key):
    return datetime.date(int(key[:4]), int(key[5:7]), int(key[8:10]))


def _utc_minute(s):
    """'YYYY-MM-DD HH:MM' (UTC) -> epoch seconds."""
    return calendar.timegm((int(s[:4]), int(s[5:7]), int(s[8:10]), int(s[11:13]), int(s[14:16]), 0))


class DataQuality(object):
    def __init__(self, sym, db_path=None):
        self.name = sym["name"]
        self.H = sym.get("hours", CLOCK_UTC)
        self.holes = []             # (lo, hi, minutes, kind, note): every stored hole, UTC seconds, hi exclusive
        self.status = ""            # "" = gap table loaded; otherwise why there is no gap information
        self.seg_keys = []          # the weekday lane-days of each loaded period, for the sensitivity table
        self.seg_spans = []
        self._load(sym["match"], db_path)
        self.set_threshold(DIRTY_MIN_MINUTES)

    def _load(self, match, db_path):
        path = db_path or find_db()
        if not path:
            self.status = "bars.db not found"
            return
        con = sqlite3.connect(path)
        try:
            if not [r[0] for r in con.execute("select name from sqlite_master where type='table' and name='gaps'")]:
                self.status = "bars.db has no 'gaps' table (rebuild it with build_bars_db.py)"
                return
            q = ("select after_bar, next_bar, missing_minutes, kind, note from gaps "
                 "where upper(replace(symbol,' ','')) in (%s) order by after_bar" % ",".join("?" * len(match)))
            shift = DB_UTC_OFFSET_HOURS * 3600.0
            for a, b, mins, kind, note in con.execute(q, tuple(x.upper() for x in match)):
                try:
                    self.holes.append((to_epoch(a) - shift + 60.0, to_epoch(b) - shift, int(mins), kind, note or ""))
                except (ValueError, TypeError):
                    continue
        finally:
            con.close()

    def set_threshold(self, minutes):
        self.thr = minutes
        self.cut = sorted(h for h in self.holes if h[4] == "" and h[3] in ("other", "weekend_long") and h[2] >= minutes)
        self.los = [h[0] for h in self.cut]
        self.his = [h[1] for h in self.cut]

    def overlaps(self, lo, hi):
        """True when a cutting hole overlaps [lo, hi)."""
        i = bisect.bisect_right(self.his, lo)           # the first hole that ends after lo
        return i < len(self.los) and self.los[i] < hi

    def day_span(self, key, h0, h1):
        """UTC seconds of lane hours h0..h1 of a lane-day."""
        mid = calendar.timegm((int(key[:4]), int(key[5:7]), int(key[8:10]), 0, 0, 0))
        base = mid - lane_shift_seconds(self.H, mid)
        return base + h0 * 3600.0, base + h1 * 3600.0

    def classify(self, keys):
        """keys = weekday lane-days that have bars, in time order. Returns
        full_ok {key: no cutting hole anywhere in the lane-day}, after {key: a weekday with NO bars at all, lost
        to a cutting hole, lies between the previous bar-day and this one}, absent_cut / absent_closed (dates of
        weekdays with no bars: lost to a hole vs a normal closure)."""
        full_ok, after, absent_cut, absent_closed = {}, {}, [], []
        one = datetime.timedelta(days=1)
        prev, pend = None, False
        for k in keys:
            kd = _key_date(k)
            if prev is not None:
                d = prev + one
                while d < kd:
                    if d.weekday() < 5:
                        lo, hi = self.day_span(d.isoformat(), 0, 24)
                        if self.overlaps(lo, hi):
                            pend = True
                            absent_cut.append(d.isoformat())
                        else:
                            absent_closed.append(d.isoformat())
                    d += one
            lo, hi = self.day_span(k, 0, 24)
            full_ok[k] = not self.overlaps(lo, hi)
            after[k] = pend
            pend = False
            prev = kd
        return full_ok, after, absent_cut, absent_closed

    def tag(self, col, period):
        """Label one finished Collector run: its trades (data_ok, cut_why) and its days (clean, reads_ok).
        Returns the numbers the report needs."""
        keys = [k for k in col.day_order if _key_date(k).weekday() < 5]
        full_ok, after, absent_cut, absent_closed = self.classify(keys)
        clean = dict((k, full_ok[k] and not after[k]) for k in keys)
        pref = [0]
        for k in keys:
            pref.append(pref[-1] + (0 if clean[k] else 1))
        reads_ok = {}
        for i, k in enumerate(keys):
            reads_ok[k] = (pref[i] - pref[max(0, i - WARM_DAYS)] == 0) and not after[k]
        win_ok = {}
        for eh in set(min(24, l.end_hour) for l in col.lanes):
            w = {}
            for k in keys:
                lo, hi = self.day_span(k, 0, eh)
                w[k] = not self.overlaps(lo, hi)
            win_ok[eh] = w
        lane_status = {}
        for l in col.lanes:
            w = win_ok[min(24, l.end_hour)]
            lane_status[l.name] = dict(
                (k, "window" if not w[k] else ("warmup" if STRICT_WARMUP and not reads_ok[k] else "ok")) for k in keys)
        for r_ in col.rows:
            st = lane_status[r_["lane"]].get(r_["day"], "window")
            t_in, t_out = _utc_minute(r_["entry_time"]), _utc_minute(r_["exit_time"]) + 60.0
            why = "window" if st == "window" else ("hold" if self.overlaps(t_in, t_out) else
                                                    ("warmup" if st == "warmup" else ""))
            r_["data_ok"] = 0 if why else 1
            r_["cut_why"] = why
        for d in col.days_out:
            d["clean"] = 1 if clean.get(d["day"], True) else 0
            d["reads_ok"] = 1 if reads_ok.get(d["day"], True) else 0
        cov = defaultdict(lambda: defaultdict(int))
        for k in keys:
            c = cov[k[:4]]
            c["data"] += 1
            if clean[k]:
                c["clean"] += 1
                c["usable"] += 1 if reads_ok[k] else 0
            else:
                c["cut"] += 1
        for d in absent_cut:
            cov[d[:4]]["cut"] += 1
        for d in absent_closed:
            cov[d[:4]]["closed"] += 1
        for y in cov:
            cov[y]["weekdays"] = cov[y]["clean"] + cov[y]["cut"] + cov[y]["closed"]
        if keys:
            self.seg_keys.append(keys)
            self.seg_spans.append((self.day_span(keys[0], 0, 0)[0], self.day_span(keys[-1], 0, 24)[1]))
        return {"period": period, "keys": keys, "cov": cov, "lane_status": lane_status, "clean": clean,
                "reads_ok": reads_ok}

    def touched(self):
        """The cutting holes that fall inside a loaded period, longest first, each with the weekdays it cut."""
        out = []
        for h in self.cut:
            if not any(h[1] > a and h[0] < b for a, b in self.seg_spans):
                continue
            d0 = datetime.datetime.fromtimestamp(h[0], datetime.timezone.utc).date()
            d1 = datetime.datetime.fromtimestamp(h[1], datetime.timezone.utc).date()
            n, d = 0, d0
            while d <= d1:
                if d.weekday() < 5:
                    lo, hi = self.day_span(d.isoformat(), 0, 24)
                    if h[0] < hi and h[1] > lo:
                        n += 1
                d += datetime.timedelta(days=1)
            out.append((h, n))
        return sorted(out, key=lambda x: -x[0][2])

    def sensitivity(self):
        """For each cutting threshold: holes inside the loaded periods, weekdays cut, weekdays in all."""
        out, save = [], self.thr
        for thr in SENSITIVITY_MINUTES:
            self.set_threshold(thr)
            n_holes = sum(1 for h in self.cut if any(h[1] > a and h[0] < b for a, b in self.seg_spans))
            cut = total = 0
            for keys in self.seg_keys:
                fo, af, ac, acl = self.classify(keys)
                cut += len(ac) + sum(1 for k in keys if not (fo[k] and not af[k]))
                total += len(keys) + len(ac) + len(acl)
            out.append((thr, n_holes, cut, total))
        self.set_threshold(save)
        return out


def _lane_evidence(tags, all_rows):
    """(lane, period, year) -> counters: trading days the lane could have fired on, and trades taken / kept / cut."""
    ev = defaultdict(lambda: {"days_ok": 0, "days_window": 0, "days_warm": 0, "taken": 0, "kept": 0,
                              "cut_window": 0, "cut_hold": 0, "cut_warm": 0})
    for tg in tags:
        for lane, st in tg["lane_status"].items():
            for k, s_ in st.items():
                ev[(lane, tg["period"], k[:4])]["days_ok" if s_ == "ok" else ("days_window" if s_ == "window" else "days_warm")] += 1
    for r_ in all_rows:
        e = ev[(r_["lane"], r_["period"], r_["day"][:4])]
        e["taken"] += 1
        why = r_.get("cut_why", "")
        if why:
            e["cut_" + ("warm" if why == "warmup" else why)] += 1
        else:
            e["kept"] += 1
    return ev


def report_coverage(rep, name, dq, tags, all_rows, outdir):
    """Section 0: where and when the data ran, how much of it was cut, and what each cut threshold would cost."""
    rep.p("")
    rep.p("-" * 78)
    rep.p("0. DATA COVERAGE  (what the bars cover and which weekdays a hole took out)")
    rep.p("-" * 78)
    if dq is None or dq.status:
        rep.p("  !! NO GAP INFORMATION (%s)." % (dq.status if dq else "not loaded"))
        rep.p("  Nothing below is cut: every trade is treated as clean. Rebuild bars.db with build_bars_db.py first.")
        return
    rep.p("  A hole is CUT when bars.db's gap table has it with no holiday / known event / weekend / nightly-break")
    rep.p("  explanation and %d+ minutes missing (the same rule as gaps_to_check.csv). Normal closures are not cuts." % DIRTY_MIN_MINUTES)
    rep.p("  CLEAN_ONLY=%s: sections 2-11 and the CSVs use clean trades only; cut trades are in trades_%s_cut.csv." % (CLEAN_ONLY, name))
    rep.p("  A trade is cut if a hole is inside its entry day's window, or it was open while one passed, or one sits in")
    rep.p("  the %d weekdays before it (STRICT_WARMUP=%s: its ATR and trend reads were built across the hole)." % (WARM_DAYS, STRICT_WARMUP))
    yrs = defaultdict(lambda: defaultdict(int))
    for tg in tags:
        for y, c in tg["cov"].items():
            for k_, v in c.items():
                yrs[y][k_] += v
    tr_y = defaultdict(lambda: [0, 0])
    for r_ in all_rows:
        tr_y[r_["day"][:4]][0 if r_.get("data_ok", 1) else 1] += 1
    rep.p("")
    rep.p("  year  weekdays  closed  cut  clean  usable | trades kept  cut | usable = clean AND no hole in the %d days before" % WARM_DAYS)
    tot = defaultdict(int)
    for y in sorted(yrs):
        c = yrs[y]
        rep.p("  %s  %8d  %6d  %3d  %5d  %6d | %11d %4d" % (y, c["weekdays"], c["closed"], c["cut"], c["clean"], c["usable"],
                                                           tr_y[y][0], tr_y[y][1]))
        for k_ in ("weekdays", "closed", "cut", "clean", "usable"):
            tot[k_] += c[k_]
        tot["kept"] += tr_y[y][0]
        tot["gone"] += tr_y[y][1]
    rep.p("  total %8d  %6d  %3d  %5d  %6d | %11d %4d" % (tot["weekdays"], tot["closed"], tot["cut"], tot["clean"], tot["usable"],
                                                         tot["kept"], tot["gone"]))
    rep.p("  (closed = weekdays with no bars that a holiday / event / normal closure explains. The sealed years %s .. %s" % (SEAL_START, SEAL_END))
    rep.p("   were never read and do not appear. Cut days are conservative: a weekend hole that begins on a Friday")
    rep.p("   evening also marks that Friday's daily bar as cut.)")
    touched = dq.touched()
    rep.p("")
    rep.p("  HOLES CUT FROM THIS RUN  (%d inside the loaded periods; longest first, up to 15)" % len(touched))
    for h, n in touched[:15]:
        rep.p("    %s -> %s   %7d min  %-12s  %d weekdays cut" % (
            time.strftime("%Y-%m-%d %H:%M", time.gmtime(h[0])), time.strftime("%Y-%m-%d %H:%M", time.gmtime(h[1])), h[2], h[3], n))
    rep.p("")
    rep.p("  WHAT EACH CUT RULE WOULD COST  (weekdays cut by holes of at least this many unexplained minutes)")
    for thr, nh, cut, total in dq.sensitivity():
        rep.p("    %4d+ min%s  %3d holes  %4d of %d weekdays cut (%.1f%%)" % (
            thr, "   <- in use" if thr == dq.thr else "          ", nh, cut, total, 100.0 * cut / max(1, total)))
    import csv
    with open(os.path.join(outdir, "coverage_%s.csv" % name), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["symbol", "year", "weekdays", "closed", "cut", "clean", "usable", "trades_kept", "trades_cut"])
        for y in sorted(yrs):
            c = yrs[y]
            w.writerow([name, y, c["weekdays"], c["closed"], c["cut"], c["clean"], c["usable"], tr_y[y][0], tr_y[y][1]])
    with open(os.path.join(outdir, "holes_cut_%s.csv" % name), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["symbol", "from_utc", "to_utc", "missing_minutes", "kind", "weekdays_cut"])
        for h, n in touched:
            w.writerow([name, time.strftime("%Y-%m-%d %H:%M", time.gmtime(h[0])),
                        time.strftime("%Y-%m-%d %H:%M", time.gmtime(h[1])), h[2], h[3], n])


def report_evidence(rep, name, tags, all_rows, days, outdir):
    """Sections 1b and 1c: trading days and trades taken, per lane and per regime; and a per-year file."""
    ev = _lane_evidence(tags, all_rows)
    rep.p("")
    rep.p("-" * 78)
    rep.p("1b. EVIDENCE BEHIND EACH LANE  (trading days and trades taken; R per trade, all trades vs clean only)")
    rep.p("-" * 78)
    rep.p("  trading days = weekdays the market was open whose lane window and reads were clean (what the lane could")
    rep.p("  have fired on). cut days: window = a hole in the lane's own window, warm-up = a hole in the days before.")
    rep.p("  trades: taken = every signal | kept = clean | cut = by hole in window / trade open through a hole / warm-up")
    rep.p("  %-9s %-2s %6s %12s | %6s %5s %-13s | %9s | %-8s %-8s" % (
        "lane", "", "days", "cut(win/wrm)", "taken", "kept", "cut(w/h/m)", "per 100 d", "R all", "R clean"))
    lanes = []
    for fam in FAMILIES + ["control"]:
        lanes += [k for k, v in FAMILY.items() if v == fam]
    for ln in lanes:
        for p in ("A", "B"):
            sel = [v for (l_, p_, y_), v in ev.items() if l_ == ln and p_ == p]
            if not sel:
                continue
            s = dict((k_, sum(v[k_] for v in sel)) for k_ in sel[0])
            ra = [r_["r"] for r_ in all_rows if r_["lane"] == ln and r_["period"] == p]
            rk = [r_["r"] for r_ in all_rows if r_["lane"] == ln and r_["period"] == p and r_.get("data_ok", 1)]
            rep.p("  %-9s %-2s %6d %6d/%-5d | %6d %5d %4d/%d/%-4d | %9.1f | %+8.3f %+8.3f" % (
                ln if p == "A" else "", p, s["days_ok"], s["days_window"], s["days_warm"], s["taken"], s["kept"],
                s["cut_window"], s["cut_hold"], s["cut_warm"], 100.0 * s["kept"] / max(1, s["days_ok"]),
                mean(ra), mean(rk)))
    rep.p("")
    rep.p("-" * 78)
    rep.p("1c. WHAT KIND OF DAYS THE TRADES CAME FROM  (clean trading days and kept trades, by the bot's regime label)")
    rep.p("-" * 78)
    rep.p("  %-3s %-9s %6s | %s | %s" % ("", "regime", "days", "trades kept: " + " ".join("%9s" % f[:9] for f in FAMILIES), "all"))
    for p in ("A", "B"):
        for reg in ("trending", "volatile", "choppy", "drift", "unknown"):
            nd = sum(1 for d in days if d["period"] == p and d.get("clean", 1) and d.get("regime") == reg)
            rs = [r_ for r_ in all_rows if r_["period"] == p and r_.get("data_ok", 1) and r_.get("regime") == reg]
            if not nd and not rs:
                continue
            rep.p("  %-3s %-9s %6d | %s | %d" % (p if reg == "trending" else "", reg, nd,
                                                 "              " + " ".join("%9d" % sum(1 for r_ in rs if r_["family"] == f) for f in FAMILIES), len(rs)))
    import csv
    with open(os.path.join(outdir, "evidence_%s.csv" % name), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["symbol", "lane", "period", "year", "trading_days", "days_cut_window", "days_cut_warmup",
                    "trades_taken", "trades_kept", "cut_window", "cut_hold", "cut_warmup"])
        for (ln, p, y), v in sorted(ev.items()):
            w.writerow([name, ln, p, y, v["days_ok"], v["days_window"], v["days_warm"], v["taken"], v["kept"],
                        v["cut_window"], v["cut_hold"], v["cut_warm"]])


class CLane(object):
    def __init__(self, name, end_hour, max_hold=None):
        self.name, self.fam = name, FAMILY[name]
        self.end_hour, self.max_hold = end_hour, max_hold
        self.done = False
        self.trade = None
        self.pending = 0            # sar
        self.lstatus, self.lhi, self.llo = "none", None, None      # london
        self.slot, self.rdir = None, 0                             # control

    def new_day(self):
        if self.trade is None:
            self.done = False
        self.pending = 0
        self.lstatus, self.lhi, self.llo = "none", None, None


class Collector(object):
    """One contiguous stretch of bars for one symbol, every lane in shadow."""

    def __init__(self, sym, m, bars, atr, period, xdays=None):
        self.sym, self.m, self.bars, self.atr_s, self.period = sym, m, bars, atr, period
        self.xdays = xdays or {}        # other symbol's daily flags (cross-market shock), day -> True
        H = self.H = sym.get("hours", CLOCK_UTC)            # this market's own clock (see CLOCK_UTC / CLOCK_NY)
        self.RS, self.RE = H["box"]                         # box start / end hour
        self.WE = H["win_end"]                              # last hour of the box lanes' window
        late = H["late_end"]
        self.lanes = [CLane("main", self.WE), CLane("fade", self.WE), CLane("sar", self.WE),
                      CLane("retest", self.WE), CLane("london", H["london"][3]), CLane("range", self.WE),
                      CLane("exhaust", self.WE), CLane("trend", H["trend"][2]), CLane("vwap", H["vwap"][2]),
                      CLane("nyaft", H["ny"][2]), CLane("scalp", late, C_SCALP[3]), CLane("pdh", 24, C_PDH[4]),
                      CLane("nr7", late), CLane("bigrev", late), CLane("bigcont", late), CLane("gapfill", 24, C_GAP[1]),
                      CLane("swing", 24, SWING_MAX_HOLD_BARS), CLane("dip", 24, DIP_MAX_HOLD_BARS),
                      CLane("control", self.WE)]
        self.hour_rng = [[0.0, 0] for _ in range(24)]       # clock check: M15 range by lane hour
        self.box_days = [0, 0]                              # clock check: days the box was usable / skipped
        self.by_name = dict((l.name, l) for l in self.lanes)
        self.rng = random.Random(20240101)      # fixed seed: the control lane is the same on every run
        self.rows, self.days_out = [], []
        self.open = []                          # trades still being tracked (real or exit-menu variants)
        self.daily, self.day_order = {}, []     # day -> [o,h,l,c]; completed + current
        self.day = None
        self.k = 0
        self.dm = {}                            # today's day-start measures
        self.reg_label, self.reg_pending, self.reg_pending_n = "unknown", None, 0
        self.swap_prev = None

    # ---------------- context ----------------
    def atr(self):
        return self.atr_s[self.k]

    def prior_days(self, n):
        out = []
        for key in reversed(self.day_order):
            if key >= self.day:
                continue
            if datetime.date(*map(int, key.split("-"))).weekday() >= 5:
                continue
            out.append(self.daily[key])
            if len(out) >= n:
                break
        out.reverse()
        return out

    def _day_measures(self):
        """Everything known at the START of today, from completed weekdays only."""
        pd_ = self.prior_days(REG_VOL_RANK_DAYS + REG_VOL_DAYS + 5)
        dm = {"n_days": len(pd_)}
        if len(pd_) >= 22:
            c = [x[3] for x in pd_]
            rng = [x[1] - x[2] for x in pd_]
            dm["avg_range20"] = sum(rng[-20:]) / 20.0

            def er(n):
                net = c[-1] - c[-1 - n]
                path = sum(abs(c[i] - c[i - 1]) for i in range(len(c) - n, len(c)))
                return (abs(net) / path if path else 0.0), (1 if net > 0 else (-1 if net < 0 else 0))
            dm["er20"], dm["sign20"] = er(REG_ER_DAYS)
            dm["er5"], dm["sign5"] = er(FAST_DAYS)
            rp = [(x[1] - x[2]) / x[3] * 100.0 for x in pd_]
            dm["vol3rel"] = (sum(rp[-3:]) / 3.0) / (sum(rp[-20:]) / 20.0) if sum(rp[-20:]) else None
            dm["turning"] = 1.0 if (dm["sign5"] and dm["sign20"] and dm["sign5"] != dm["sign20"]) else 0.0
            dm["sma20"] = sum(c[-DIP_AVG_DAYS:]) / float(DIP_AVG_DAYS)
            dm["sma20_prev"] = (sum(c[-DIP_AVG_DAYS - DIP_RISING_DAYS:-DIP_RISING_DAYS]) / float(DIP_AVG_DAYS)
                                if len(c) >= DIP_AVG_DAYS + DIP_RISING_DAYS else None)
            dm["shock"] = 1.0 if rng[-1] >= STANDASIDE_SHOCK * (sum(rng[-21:-1]) / 20.0) else 0.0
            raw = "unknown"
            if len(pd_) >= 40:
                vs = [sum(rp[i - REG_VOL_DAYS + 1:i + 1]) / REG_VOL_DAYS for i in range(REG_VOL_DAYS - 1, len(rp))]
                hist = vs[-REG_VOL_RANK_DAYS:]
                dm["volrank"] = sum(1 for v in hist if v <= hist[-1]) / float(len(hist))
                if dm["volrank"] >= REG_VOL_HIGH:
                    raw = "volatile"
                elif dm["er20"] >= REG_ER_TREND:
                    raw = "trending"
                elif dm["er20"] < REG_ER_CHOP:
                    raw = "choppy"
                else:
                    raw = "drift"
            # same 2-day confirmation as the bot
            if raw == self.reg_label:
                self.reg_pending, self.reg_pending_n = None, 0
            elif self.reg_label == "unknown" or raw == "unknown":
                self.reg_label = raw
            else:
                if raw == self.reg_pending:
                    self.reg_pending_n += 1
                else:
                    self.reg_pending, self.reg_pending_n = raw, 1
                if self.reg_pending_n >= REG_CONFIRM:
                    self.reg_label, self.reg_pending, self.reg_pending_n = raw, None, 0
        dm["regime"] = self.reg_label
        return dm

    def _new_day(self, key, bar):
        self.day = key
        self.dm = self._day_measures()
        self.box_hi = self.box_lo = None
        self.box_n, self.box_status, self.box_ratio = 0, "none", None
        self.brk_dir, self.brk_bar, self.brk_ext, self.brk_failed = 0, None, None, False
        self.today, self.today_h, self.vw_sum, self.vwap, self.vwap_hr = [], [], 0.0, None, {}
        self.day_hi = self.day_lo = None
        self.day_open = bar[1]
        self.path_len = 0.0
        for l in self.lanes:
            l.new_day()
        c = self.by_name["control"]
        c.slot = self.rng.randint(0, (self.WE - self.RE) * 4 - 1)
        c.rdir = 1 if self.rng.random() < 0.5 else -1
        dm = self.dm
        pd1 = self.prior_days(1)
        gap = None
        if pd1 and dm.get("avg_range20"):
            gap = abs(bar[1] - pd1[-1][3]) / dm["avg_range20"]
        dm["gap"] = 1.0 if (gap is not None and gap >= STANDASIDE_GAP) else 0.0
        dm["xshock"] = 1.0 if self.xdays.get(key) else 0.0
        wd = datetime.date(*map(int, key.split("-"))).weekday()
        if wd < 5:
            self.days_out.append({"symbol": self.sym["name"], "period": self.period, "day": key,
                                  "regime": dm.get("regime"), "er5": dm.get("er5"), "sign5": dm.get("sign5"),
                                  "er20": dm.get("er20"), "sign20": dm.get("sign20"), "vol3rel": dm.get("vol3rel"),
                                  "volrank": dm.get("volrank"), "turning": dm.get("turning"),
                                  "shock": dm.get("shock"), "gap": dm.get("gap"), "xshock": dm.get("xshock"),
                                  "avg_range20": dm.get("avg_range20")})

    # ---------------- trade bookkeeping ----------------
    def _features(self, lane, d, entry, rd, bar, hour, ref_range):
        dm = self.dm
        a = self.atr()
        avg = dm.get("avg_range20")
        f = {"hour": float(hour), "stop_atr": (rd / a) if a else None}
        for k_ in ("er5", "er20", "vol3rel", "volrank", "turning", "shock", "gap", "xshock"):
            f[k_] = dm.get(k_)
        f["regime"] = dm.get("regime")
        f["trend20_with"] = (dm["er20"] * dm["sign20"] * d) if dm.get("er20") is not None else None
        f["trend5_with"] = (dm["er5"] * dm["sign5"] * d) if dm.get("er5") is not None else None
        f["asia_rel"] = ((self.box_hi - self.box_lo) / avg) if (avg and self.box_status == "ready") else None
        f["setup_range_rel"] = (ref_range / avg) if (avg and ref_range) else None
        f["day_used"] = ((self.day_hi - self.day_lo) / avg) if (avg and self.day_hi is not None) else None
        f["day_eff"] = (abs(bar[4] - self.day_open) / self.path_len) if self.path_len > 0 else None
        f["open_move_with"] = ((entry - self.day_open) * d / avg) if avg else None
        f["open_hours"] = 1.0 if hour in self.H["open_hours"] else 0.0
        hl = bar[2] - bar[3]
        pos = ((bar[4] - bar[3]) / hl) if hl > 0 else 0.5
        f["bar_extreme"] = pos if d > 0 else 1.0 - pos
        pd1 = self.prior_days(1)
        if pd1:
            dist = (pd1[-1][1] - entry) if d > 0 else (entry - pd1[-1][2])
            f["room_r"] = min(9.9, dist / rd) if dist > 0 else 9.9      # already beyond it = nothing in the way
        else:
            f["room_r"] = None
        f["stretch_atr"] = (abs(entry - self.vwap) / a) if (a and self.vwap is not None) else None
        return f

    def _enter(self, lane, sig, bar, hour):
        d = sig["dir"]
        entry = bar[4]
        rd = abs(entry - sig["sl"])
        if rd < self.sym["min_sl"]:
            return
        cost = _cost_px(self.sym, entry)
        f = self._features(lane, d, entry, rd, bar, hour, sig.get("ref"))
        f["target_r"] = sig.get("target_r")
        f["cost_r"] = cost / rd
        f["cost_ok"] = 1.0 if rd >= COST_MIN_STOP_MULT * cost else 0.0
        tr = {"lane": lane.name, "fam": lane.fam, "dir": d, "entry": entry, "sl": sig["sl"], "rd": rd,
              "tp": (entry + d * sig["target_r"] * rd) if sig.get("target_r") else None,
              "t_entry": bar[0] + 900, "day": self.day, "bars": -1, "nights": 0,
              "mfe": 0.0, "mae": 0.0, "mfe_t": None, "done": False, "after": 0.0,
              "f": f,
              # stop menu: same entry and target price, stop at k x the lane's distance
              "s": dict((k, {"done": False, "sl": entry - d * k * rd, "rd": k * rd, "r": None}) for k in STOP_MENU),
              # entry delay: waits k bars, then enters at that bar's close if the setup is intact
              "dl": dict((k, {"state": "wait", "r": None}) for k in DELAY_MENU),
              # the fixed exit menu, run on the same path as the real trade
              "v": {"t1": {"done": False, "tp": entry + d * 1.0 * rd},      # nearer target (1R)
                    "hold": {"done": False},                                 # no target: stop or the clock
                    "trail": {"done": False, "best": 0.0}}}                  # after +1R, stop trails 1R behind
        lane.trade = tr
        self.open.append(tr)

    def _net(self, tr, move, nights):
        swap = nights * (self.sym["swap_long"] if tr["dir"] > 0 else self.sym["swap_short"])
        return (move - _cost_px(self.sym, tr["entry"]) + swap) / tr["rd"]

    def _close_real(self, tr, price, reason, when):
        move = (price - tr["entry"]) * tr["dir"]
        tr.update(done=True, exit=price, reason=reason, t_exit=when, r=self._net(tr, move, tr["nights"]),
                  gross_r=move / tr["rd"], nights_real=tr["nights"])
        lane = self.by_name[tr["lane"]]
        lane.trade = None
        if tr["lane"] == "main" and reason == "StopLoss":
            sar = self.by_name["sar"]
            if not sar.done:
                sar.pending = -tr["dir"]

    def _close_var(self, tr, name, price):
        v = tr["v"][name]
        v["done"] = True
        v["r"] = self._net(tr, (price - tr["entry"]) * tr["dir"], tr["nights"])

    def _close_stop_var(self, tr, k, price):
        x = tr["s"][k]
        swap = tr["nights"] * (self.sym["swap_long"] if tr["dir"] > 0 else self.sym["swap_short"])
        x["done"] = True
        x["r"] = ((price - tr["entry"]) * tr["dir"] - _cost_px(self.sym, tr["entry"]) + swap) / x["rd"]

    def _close_delay_var(self, tr, k, price):
        x = tr["dl"][k]
        nights = tr["nights"] - x["nights0"]
        swap = nights * (self.sym["swap_long"] if tr["dir"] > 0 else self.sym["swap_short"])
        x["state"] = "done"
        x["r"] = ((price - x["entry"]) * tr["dir"] - _cost_px(self.sym, x["entry"]) + swap) / x["rd"]

    def _try_delay_entries(self, tr, c, hour):
        """Called at each M15 close after the trade's bar was walked: bar index tr['bars'] is 0 for the
        first bar after the signal bar, so delay k enters at the close of bar k-1."""
        lane = self.by_name[tr["lane"]]
        for k, x in tr["dl"].items():
            if x["state"] != "wait" or tr["bars"] < k - 1:
                continue
            x["state"] = "none"
            # intact = the as-built trade is still open (same stop and target prices, so if it has been
            # stopped, hit its target or run out of clock, there is nothing left to enter)
            if tr["done"] or tr.get("gone") or tr["bars"] > k - 1 or hour >= lane.end_hour:
                continue
            d, rd = tr["dir"], abs(c - tr["sl"])
            if (c - tr["sl"]) * d <= 0 or rd < self.sym["min_sl"]:
                continue
            if tr["tp"] is not None and (tr["tp"] - c) * d <= 0:
                continue
            x.update(state="open", entry=c, rd=rd, nights0=tr["nights"])

    def _all_done(self, tr):
        return (tr["done"] and all(v["done"] for v in tr["v"].values()) and all(x["done"] for x in tr["s"].values())
                and all(x["state"] in ("none", "done") for x in tr["dl"].values()))

    def _walk(self, tr, a1, b1):
        """Advance one trade through the M1 bars of one M15 bar. Stop before target inside a bar;
        gaps fill at the open. The real trade and each exit-menu variant are tracked separately."""
        m, d, e, sl, rd = self.m, tr["dir"], tr["entry"], tr["sl"], tr["rd"]
        v = tr["v"]
        for i in range(a1, b1):
            o, h, l = m.o[i], m.h[i], m.l[i]
            hit_sl = (l <= sl) if d > 0 else (h >= sl)
            sl_px = (min(o, sl) if d > 0 else max(o, sl))
            if not tr["done"]:
                fav = (h - e) if d > 0 else (e - l)
                adv = (e - l) if d > 0 else (h - e)
                if hit_sl:
                    tr["mae"] = max(tr["mae"], (e - sl_px) * d)
                    self._close_real(tr, sl_px, "StopLoss", m.ts[i])
                else:
                    if fav > tr["mfe"]:
                        tr["mfe"], tr["mfe_t"] = fav, m.ts[i]
                    tr["mae"] = max(tr["mae"], adv)
                    if tr["tp"] is not None and ((h >= tr["tp"]) if d > 0 else (l <= tr["tp"])):
                        self._close_real(tr, (max(o, tr["tp"]) if d > 0 else min(o, tr["tp"])), "TakeProfit", m.ts[i])
            else:
                # how far price kept going our way after the real exit (until the clock runs out)
                tr["after"] = max(tr["after"], ((h - tr["exit"]) if d > 0 else (tr["exit"] - l)))
            x = v["t1"]
            if not x["done"]:
                if hit_sl:
                    self._close_var(tr, "t1", sl_px)
                elif (h >= x["tp"]) if d > 0 else (l <= x["tp"]):
                    self._close_var(tr, "t1", (max(o, x["tp"]) if d > 0 else min(o, x["tp"])))
            x = v["hold"]
            if not x["done"] and hit_sl:
                self._close_var(tr, "hold", sl_px)
            x = v["trail"]
            if not x["done"]:
                tsl = sl
                if x["best"] >= rd:                       # armed: trail 1R behind the best price so far
                    tsl = (e + x["best"] - rd) if d > 0 else (e - x["best"] + rd)
                if (l <= tsl) if d > 0 else (h >= tsl):
                    self._close_var(tr, "trail", (min(o, tsl) if d > 0 else max(o, tsl)))
                else:
                    x["best"] = max(x["best"], (h - e) if d > 0 else (e - l))
            tp = tr["tp"]
            hit_tp = tp is not None and ((h >= tp) if d > 0 else (l <= tp))
            for k, x in tr["s"].items():                  # stop menu
                if x["done"]:
                    continue
                if (l <= x["sl"]) if d > 0 else (h >= x["sl"]):
                    self._close_stop_var(tr, k, (min(o, x["sl"]) if d > 0 else max(o, x["sl"])))
                elif hit_tp:
                    self._close_stop_var(tr, k, (max(o, tp) if d > 0 else min(o, tp)))
            for k, x in tr["dl"].items():                 # entry delay (same stop and target prices)
                if x["state"] != "open":
                    continue
                if hit_sl:
                    self._close_delay_var(tr, k, sl_px)
                elif hit_tp:
                    self._close_delay_var(tr, k, (max(o, tp) if d > 0 else min(o, tp)))

    def _finish(self, tr, price, reason, when):
        """The clock ran out (session end / max hold): close whatever is still open and write the row."""
        if not tr["done"]:
            self._close_real(tr, price, reason, when)
        for name in tr["v"]:
            if not tr["v"][name]["done"]:
                self._close_var(tr, name, price)
        for k in tr["s"]:
            if not tr["s"][k]["done"]:
                self._close_stop_var(tr, k, price)
        for k in tr["dl"]:
            if tr["dl"][k]["state"] == "open":
                self._close_delay_var(tr, k, price)
        rd = tr["rd"]
        row_ = {"symbol": self.sym["name"], "period": self.period, "lane": tr["lane"], "family": tr["fam"],
                "day": tr["day"], "entry_time": time.strftime("%Y-%m-%d %H:%M", time.gmtime(tr["t_entry"])),
                "exit_time": time.strftime("%Y-%m-%d %H:%M", time.gmtime(tr["t_exit"])),
                "dir": tr["dir"], "entry": tr["entry"], "stop_dist": rd, "reason": tr["reason"],
                "r": tr["r"], "gross_r": tr["gross_r"], "nights": tr["nights_real"],
                "mfe_r": tr["mfe"] / rd, "mae_r": tr["mae"] / rd,
                "giveback_r": tr["mfe"] / rd - tr["gross_r"], "after_exit_r": tr["after"] / rd,
                "exit_1r": tr["v"]["t1"]["r"], "exit_hold": tr["v"]["hold"]["r"], "exit_trail": tr["v"]["trail"]["r"]}
        for k in STOP_MENU:
            row_["stop_%s" % str(k).replace(".", "")] = tr["s"][k]["r"]
        for k in DELAY_MENU:
            row_["delay_%d" % k] = tr["dl"][k]["r"]          # blank = no entry (setup gone before the delay)
        row_.update(tr["f"])
        self.rows.append(row_)
        tr["gone"] = True

    def _swap(self, t0):
        g = time.gmtime(t0)
        lab = datetime.date(g.tm_year, g.tm_mon, g.tm_mday)
        if (g.tm_hour, g.tm_min) >= (SWAP_HOUR, SWAP_MINUTE):
            lab += datetime.timedelta(days=1)
        prev, self.swap_prev = self.swap_prev, lab
        if prev is None or lab == prev:
            return
        wd = prev.weekday()
        nights = 0 if wd >= 5 else (3 if wd == SWAP_TRIPLE_WEEKDAY else 1)
        for tr in self.open:
            tr["nights"] += nights

    # ---------------- lanes (the bot's rules) ----------------
    def _signal(self, lane, bar, hour, minute):
        n = lane.name
        t0, o, h, l, c = bar[0], bar[1], bar[2], bar[3], bar[4]
        a = self.atr()
        if a is None:
            return None
        box_ready = self.box_status == "ready"
        H = self.H
        in_win = self.RE <= hour < self.WE
        box_h = (self.box_hi - self.box_lo) if box_ready else None

        if n == "main":
            if lane.done or lane.trade or not box_ready or not in_win:
                return None
            buf = BREAKOUT_BUFFER_ATR * a
            d = 1 if c > self.box_hi + buf else (-1 if c < self.box_lo - buf else 0)
            if not d:
                return None
            lane.done = True
            sl = ((self.box_hi + self.box_lo) / 2.0) if STOP_MODE == "mid" else (self.box_lo if d > 0 else self.box_hi)
            return {"dir": d, "sl": sl, "target_r": TARGET_R, "ref": box_h}

        if n == "fade":
            if lane.done or lane.trade or self.brk_dir == 0 or self.brk_bar == t0 or not in_win:
                return None
            if self.brk_dir > 0 and c < self.box_hi:
                d, sl, edge = -1, self.brk_ext + C_FADE_STOP_ATR * a, self.box_lo
            elif self.brk_dir < 0 and c > self.box_lo:
                d, sl, edge = 1, self.brk_ext - C_FADE_STOP_ATR * a, self.box_hi
            else:
                return None
            lane.done = True
            risk = abs(c - sl)
            return {"dir": d, "sl": sl, "ref": box_h,
                    "target_r": max(C_FADE_MIN_R, abs(c - edge) / risk) if risk > 0 else C_FADE_MIN_R}

        if n == "sar":
            if not lane.pending or lane.done or lane.trade or not box_ready:
                return None
            d, lane.pending = lane.pending, 0
            lane.done = True
            if not in_win:
                return None
            sl = self.box_hi if d < 0 else self.box_lo
            if (d < 0 and c >= sl) or (d > 0 and c <= sl):
                return None
            return {"dir": d, "sl": sl, "target_r": C_SAR_R, "ref": box_h}

        if n == "retest":
            if lane.done or lane.trade or self.brk_dir == 0 or self.brk_bar == t0 or not in_win or self.brk_failed:
                return None
            mid = (self.box_hi + self.box_lo) / 2.0
            if self.brk_dir > 0 and l <= self.box_hi + C_RETEST_TOUCH_ATR * a and c > self.box_hi:
                d = 1
            elif self.brk_dir < 0 and h >= self.box_lo - C_RETEST_TOUCH_ATR * a and c < self.box_lo:
                d = -1
            else:
                return None
            lane.done = True
            return {"dir": d, "sl": mid, "target_r": C_RETEST_R, "ref": box_h}

        if n == "london":
            (ls, le, lee, _), ltr = H["london"], C_LONDON[4]
            if lane.lstatus == "none" and hour >= le:
                hi = lo = None
                cnt = 0
                for b, bh in zip(self.today, self.today_h):
                    if ls <= bh < le:
                        hi = b[2] if hi is None else max(hi, b[2])
                        lo = b[3] if lo is None else min(lo, b[3])
                        cnt += 1
                ratio = (hi - lo) / a if (hi is not None and a) else None
                if cnt < H["london_min_bars"] or ratio is None or not (MIN_RANGE_ATR <= ratio <= MAX_RANGE_ATR):
                    lane.lstatus = "skipped"
                else:
                    lane.lstatus, lane.lhi, lane.llo = "ready", hi, lo
            if lane.lstatus != "ready" or lane.done or lane.trade or not (le <= hour < lee):
                return None
            buf = BREAKOUT_BUFFER_ATR * a
            if c > lane.lhi + buf:
                d, sl = 1, lane.llo
            elif c < lane.llo - buf:
                d, sl = -1, lane.lhi
            else:
                return None
            lane.done = True
            return {"dir": d, "sl": sl, "target_r": ltr, "ref": lane.lhi - lane.llo}

        if n == "range":
            (_, zone_a, stop_a, min_r), ee = C_RANGE, H["range_end"]
            if lane.done or lane.trade or not box_ready or self.brk_dir != 0 or not (self.RE <= hour < ee):
                return None
            zone = zone_a * a
            mid = (self.box_hi + self.box_lo) / 2.0
            if h >= self.box_hi - zone and mid < c < self.box_hi - zone:
                d, sl = -1, self.box_hi + stop_a * a
            elif l <= self.box_lo + zone and self.box_lo + zone < c < mid:
                d, sl = 1, self.box_lo - stop_a * a
            else:
                return None
            risk = abs(c - sl)
            tr_ = abs(mid - c) / risk if risk > 0 else 0.0
            if tr_ < min_r:
                return None
            lane.done = True
            return {"dir": d, "sl": sl, "target_r": tr_, "ref": box_h}

        if n == "exhaust":
            ext_a, back_a, stop_a, min_r = C_EXH
            if lane.done or lane.trade or self.brk_dir == 0 or self.brk_bar == t0 or not in_win:
                return None
            ext, back = ext_a * a, back_a * a
            if self.brk_dir > 0 and self.brk_ext - self.box_hi >= ext and self.box_hi < c <= self.brk_ext - back:
                d, sl, edge = -1, self.brk_ext + stop_a * a, self.box_hi
            elif self.brk_dir < 0 and self.box_lo - self.brk_ext >= ext and self.brk_ext + back <= c < self.box_lo:
                d, sl, edge = 1, self.brk_ext - stop_a * a, self.box_lo
            else:
                return None
            risk = abs(c - sl)
            tr_ = abs(c - edge) / risk if risk > 0 else 0.0
            if tr_ < min_r:
                return None
            lane.done = True
            return {"dir": d, "sl": sl, "target_r": tr_, "ref": box_h}

        if n == "trend":
            _, _, dist_a, stop_a, tr_, _ = C_TREND
            eh, sh = H["trend"][0], H["trend"][1]
            if lane.done or lane.trade or hour != eh or self.vwap is None:
                return None
            then = self.vwap_hr.get(sh)
            if then is None:
                return None
            dist = (c - self.vwap) / a if a else 0.0
            slope = self.vwap - then
            if dist >= dist_a and slope > 0:
                d, sl = 1, self.vwap - stop_a * a
            elif dist <= -dist_a and slope < 0:
                d, sl = -1, self.vwap + stop_a * a
            else:
                return None
            lane.done = True
            return {"dir": d, "sl": sl, "target_r": tr_}

        if n == "vwap":
            _, _, stretch, stop_a, min_r, _ = C_VWAP
            s_, e_ = H["vwap"][0], H["vwap"][1]
            if lane.done or lane.trade or self.vwap is None or self.day_hi is None or not (s_ <= hour < e_) or not a:
                return None
            dist = (c - self.vwap) / a
            if dist >= stretch and c < o:
                d, sl = -1, self.day_hi + stop_a * a
            elif dist <= -stretch and c > o:
                d, sl = 1, self.day_lo - stop_a * a
            else:
                return None
            risk = abs(c - sl)
            tr_ = abs(c - self.vwap) / risk if risk > 0 else 0.0
            if tr_ < min_r:
                return None
            lane.done = True
            return {"dir": d, "sl": sl, "target_r": tr_}

        if n == "nyaft":
            _, _, min_a, tr_, _ = C_NY
            oh, ah = H["ny"][0], H["ny"][1]
            if lane.done or lane.trade or hour != ah:
                return None
            lane.done = True
            fo = lc = hi = lo = None
            for b, bh in zip(self.today, self.today_h):
                if oh <= bh < ah:
                    if fo is None:
                        fo = b[1]
                    lc = b[4]
                    hi = b[2] if hi is None else max(hi, b[2])
                    lo = b[3] if lo is None else min(lo, b[3])
            if fo is None or not a or abs(lc - fo) < min_a * a:
                return None
            d = 1 if lc > fo else -1
            sl = (hi + lo) / 2.0
            if (d > 0 and c <= sl) or (d < 0 and c >= sl):
                return None
            return {"dir": d, "sl": sl, "target_r": tr_, "ref": hi - lo}

        if n == "scalp":
            imp, zone, tr_, _ = C_SCALP
            if lane.done or lane.trade:
                return None
            if (hour, minute) != _scalp_open_hm(H, t0):
                return None
            lane.done = True
            rng_ = h - l
            if not a or rng_ < imp * a:
                return None
            pos = (c - l) / rng_
            d = 1 if pos >= 1.0 - zone else (-1 if pos <= zone else 0)
            if not d:
                return None
            # stop at the FAR END of the impulse bar (was its midpoint: so tight that costs ate 6-9% of the risk)
            return {"dir": d, "sl": (l if d > 0 else h), "target_r": tr_, "ref": rng_}

        if n == "pdh":
            buf_a, _, _, tr_, _ = C_PDH
            s_, e_ = H["pdh"]
            if lane.done or lane.trade or not (s_ <= hour < e_):
                return None
            pd_ = self.prior_days(1)
            if not pd_:
                return None
            _, ph, pl, _ = pd_[-1]
            buf = buf_a * a
            d = 1 if c > ph + buf else (-1 if c < pl - buf else 0)
            if not d:
                return None
            lane.done = True
            return {"dir": d, "sl": (ph + pl) / 2.0, "target_r": tr_, "ref": ph - pl}

        if n == "nr7":
            look, tr_ = C_NR
            if lane.done or lane.trade or not (H["nr7"][0] <= hour < H["nr7"][1]):
                return None
            pd_ = self.prior_days(look)
            if len(pd_) < look:
                return None
            rngs = [x[1] - x[2] for x in pd_]
            if rngs[-1] > min(rngs):
                lane.done = True
                return None
            _, ph, pl, _ = pd_[-1]
            if c > ph:
                d, sl = 1, pl
            elif c < pl:
                d, sl = -1, ph
            else:
                return None
            lane.done = True
            return {"dir": d, "sl": sl, "target_r": tr_, "ref": ph - pl}

        if n in ("bigrev", "bigcont"):
            mult, zone, avg_n, _, stop_f, tr_ = C_BIG
            eh = H["big"]
            if lane.done or lane.trade or hour != eh:
                return None
            lane.done = True
            pd_ = self.prior_days(avg_n + 1)
            if len(pd_) < avg_n + 1:
                return None
            _, ph, pl, pc = pd_[-1]
            rng_ = ph - pl
            avg = sum(x[1] - x[2] for x in pd_[:-1]) / float(avg_n)
            if not avg or rng_ < mult * avg or rng_ <= 0:
                return None
            pos = (pc - pl) / rng_
            move = 1 if pos >= 1.0 - zone else (-1 if pos <= zone else 0)
            if not move:
                return None
            d = move * (1 if n == "bigcont" else -1)
            return {"dir": d, "sl": c - d * stop_f * rng_, "target_r": tr_, "ref": rng_}

        if n == "gapfill":
            min_a, _ = C_GAP
            if lane.trade or self.k < 1:
                return None
            prev = self.bars[self.k - 1]
            if t0 - prev[0] < 24 * 3600:
                return None
            gap = o - prev[4]
            if abs(gap) < min_a * a:
                return None
            d = -1 if gap > 0 else 1
            dist = abs(c - prev[4])
            if (d > 0 and c >= prev[4]) or (d < 0 and c <= prev[4]) or dist <= 0:
                return None
            return {"dir": d, "sl": c - d * dist, "target_r": 1.0, "ref": abs(gap)}

        if n == "swing":
            if lane.done or lane.trade or not (H["multi"][0] <= hour < H["multi"][1]):
                return None
            pd_ = self.prior_days(SWING_ENTRY_DAYS)
            avg = self.dm.get("avg_range20")
            if len(pd_) < SWING_ENTRY_DAYS or not avg:
                return None
            hi, lo = max(x[1] for x in pd_), min(x[2] for x in pd_)
            d = 1 if c > hi else (-1 if c < lo else 0)
            if not d:
                return None
            lane.done = True
            return {"dir": d, "sl": c - d * SWING_STOP_RANGES * avg, "target_r": None, "ref": hi - lo}

        if n == "dip":
            if lane.done or lane.trade or not (H["multi"][0] <= hour < H["multi"][1]):
                return None
            dm = self.dm
            pd_ = self.prior_days(DIP_PULLBACK_DAYS + 1)
            if len(pd_) < DIP_PULLBACK_DAYS + 1 or dm.get("sma20") is None or dm.get("sma20_prev") is None:
                return None
            closes = [x[3] for x in pd_]
            up = closes[-1] > dm["sma20"] and dm["sma20"] > dm["sma20_prev"]
            dn = closes[-1] < dm["sma20"] and dm["sma20"] < dm["sma20_prev"]
            falling = all(closes[i] < closes[i - 1] for i in range(1, len(closes)))
            rising = all(closes[i] > closes[i - 1] for i in range(1, len(closes)))
            _, ph, pl, _ = pd_[-1]
            if up and falling and c > ph:
                d = 1
                sl = min(min(x[2] for x in pd_[-DIP_PULLBACK_DAYS:]), self.day_lo if self.day_lo is not None else pl)
            elif dn and rising and c < pl:
                d = -1
                sl = max(max(x[1] for x in pd_[-DIP_PULLBACK_DAYS:]), self.day_hi if self.day_hi is not None else ph)
            else:
                return None
            lane.done = True
            return {"dir": d, "sl": sl, "target_r": DIP_TARGET_R, "ref": ph - pl}

        if n == "control":
            if lane.done or lane.trade or not box_ready or lane.slot is None or not in_win:
                return None
            if (hour - self.RE) * 4 + minute // 15 < lane.slot:
                return None
            lane.done = True
            d = lane.rdir
            return {"dir": d, "sl": c - d * (self.box_hi - self.box_lo), "target_r": 2.0, "ref": box_h}
        return None

    # ---------------- main loop ----------------
    def run(self):
        bars = self.bars
        for k, bar in enumerate(bars):
            self.k = k
            t0, o, h, l, c, a1, b1 = bar
            hour, minute, key = lane_clock(self.H, t0)       # the market's own clock (gold: plain UTC)
            hr_ = self.hour_rng[hour]
            hr_[0] += h - l; hr_[1] += 1
            if key != self.day:
                self._new_day(key, bar)
            dc = self.daily.get(key)
            if dc is None:
                self.daily[key] = [o, h, l, c]
                self.day_order.append(key)
            else:
                dc[1] = max(dc[1], h); dc[2] = min(dc[2], l); dc[3] = c

            # session lanes never carry a trade into another day: if the data simply stops before the
            # lane's end hour (short sessions, early closes), the trade ends at the last bar it had
            if self.open and k > 0:
                stale = [tr for tr in self.open if self.by_name[tr["lane"]].end_hour < 24 and tr["day"] != key]
                if stale:
                    for tr in stale:
                        self._finish(tr, bars[k - 1][4], "session_end", bars[k - 1][0] + 900)
                    self.open = [tr for tr in self.open if not tr.get("gone")]

            # 0) overnight swap, 1) open trades walk this bar's M1 path
            self._swap(t0)
            for tr in self.open:
                tr["bars"] += 1
                if tr["bars"] >= 1 or tr["t_entry"] <= t0:
                    self._walk(tr, a1, b1)

            # 2) the clock: session end / max hold / the swing lane's trailing exit
            for tr in self.open:
                lane = self.by_name[tr["lane"]]
                why = None
                if hour >= lane.end_hour and tr["t_entry"] <= t0:
                    why = "window_end"
                elif lane.max_hold and tr["bars"] >= lane.max_hold:
                    why = "time_exit"
                if why:
                    self._finish(tr, c, why, t0 + 900)
                    continue
                if tr["lane"] == "swing" and tr["t_entry"] <= t0:
                    # the swing lane's only way out besides its stop: an M15 close beyond the 10-day
                    # extreme on the other side. It ends the trade AND every variant of it.
                    pd_ = self.prior_days(SWING_EXIT_DAYS)
                    if len(pd_) >= SWING_EXIT_DAYS:
                        if (tr["dir"] > 0 and c < min(x[2] for x in pd_)) or (tr["dir"] < 0 and c > max(x[1] for x in pd_)):
                            self._finish(tr, c, "trail_exit", t0 + 900)
                            continue
                self._try_delay_entries(tr, c, hour)
                if self._all_done(tr):
                    self._finish(tr, c, tr["reason"], t0 + 900)      # nothing left to track
            self.open = [tr for tr in self.open if not tr.get("gone")]

            # 3) shared context (same order as the bot: box, breakout tracker, session)
            if self.RS <= hour < self.RE:
                self.box_hi = h if self.box_hi is None else max(self.box_hi, h)
                self.box_lo = l if self.box_lo is None else min(self.box_lo, l)
                self.box_n += 1
            a = self.atr()
            if self.box_status == "none" and hour >= self.RE:
                ratio = ((self.box_hi - self.box_lo) / a) if (self.box_hi is not None and a) else None
                if self.box_n < self.H["box_min_bars"] or ratio is None or not (MIN_RANGE_ATR <= ratio <= MAX_RANGE_ATR):
                    self.box_status = "skipped"
                else:
                    self.box_status, self.box_ratio = "ready", ratio
                if datetime.date(*map(int, key.split("-"))).weekday() < 5:
                    self.box_days[0 if self.box_status == "ready" else 1] += 1
            if self.box_status == "ready" and self.RE <= hour < self.WE and a:
                buf = BREAKOUT_BUFFER_ATR * a
                if self.brk_dir == 0:
                    if c > self.box_hi + buf:
                        self.brk_dir, self.brk_ext, self.brk_bar = 1, h, t0
                    elif c < self.box_lo - buf:
                        self.brk_dir, self.brk_ext, self.brk_bar = -1, l, t0
                elif self.brk_dir > 0:
                    self.brk_ext = max(self.brk_ext, h)
                    if c < self.box_hi:
                        self.brk_failed = True
                else:
                    self.brk_ext = min(self.brk_ext, l)
                    if c > self.box_lo:
                        self.brk_failed = True
            if self.today:
                self.path_len += abs(c - self.today[-1][4])
            self.today.append(bar)
            self.today_h.append(hour)
            self.vw_sum += (h + l + c) / 3.0
            self.vwap = self.vw_sum / len(self.today)
            self.vwap_hr[hour] = self.vwap
            self.day_hi = h if self.day_hi is None else max(self.day_hi, h)
            self.day_lo = l if self.day_lo is None else min(self.day_lo, l)

            # 4) signals
            if a is None:
                continue
            for lane in self.lanes:
                sig = self._signal(lane, bar, hour, minute)
                if sig:
                    self._enter(lane, sig, bar, hour)
        # end of the segment: a trade whose real exit already happened is written (its exit-menu variants
        # are closed at the last price); a trade still really open is dropped, not counted
        self.dropped = 0
        last = bars[-1]
        for tr in self.open:
            if tr["done"]:
                self._finish(tr, last[4], "segment_end", last[0] + 900)
            else:
                self.dropped += 1
        self.open = []
        for d in self.days_out:
            dc = self.daily.get(d["day"])
            d["close"] = dc[3]
            d["range_pct"] = (dc[1] - dc[2]) / dc[3] * 100.0
        return self


# ------------------------------ collect: analysis ------------------------------
def _slice_m1(m, lo_ts, hi_ts):
    b = M1()
    i0 = 0
    while i0 < m.n and m.ts[i0] < lo_ts:
        i0 += 1
    i1 = i0
    while i1 < m.n and m.ts[i1] < hi_ts:
        i1 += 1
    b.ts, b.o, b.h, b.l, b.c = m.ts[i0:i1], m.o[i0:i1], m.h[i0:i1], m.l[i0:i1], m.c[i0:i1]
    b.n = i1 - i0
    return b


def shock_days(bars):
    """Days whose PREVIOUS weekday had a range >= STANDASIDE_SHOCK x its 20-day average (known at the open)."""
    days, by = daily_table(bars)
    out = {}
    for i in range(21, len(days)):
        prev = by[days[i - 1]]
        avg = sum(by[days[j]][1] - by[days[j]][2] for j in range(i - 21, i - 1)) / 20.0
        if avg and (prev[1] - prev[2]) >= STANDASIDE_SHOCK * avg:
            out[days[i]] = True
    return out


def _corr(a, b):
    if len(a) < 3:
        return None
    ma, mb = mean(a), mean(b)
    sa = math.sqrt(sum((x - ma) ** 2 for x in a))
    sb = math.sqrt(sum((y - mb) ** 2 for y in b))
    return (sum((x - ma) * (y - mb) for x, y in zip(a, b)) / (sa * sb)) if sa and sb else None


def _hi_lo_z(rows, key):
    """Top third minus bottom third of `key` (or 1 vs 0 for a yes/no signal), in R, as a z-score."""
    pts = [(r_[key], r_["r"]) for r_ in rows if r_.get(key) is not None]
    if len(pts) < 30:
        return None
    vals = sorted(set(v for v, _ in pts))
    if len(vals) <= 2:
        top = [r for v, r in pts if v == vals[-1]]
        bot = [r for v, r in pts if v == vals[0]]
        if len(vals) < 2:
            return None
    else:
        sv = sorted(v for v, _ in pts)
        c1, c2 = sv[len(sv) // 3], sv[2 * len(sv) // 3]
        top = [r for v, r in pts if v >= c2]
        bot = [r for v, r in pts if v < c1]
    if len(top) < 10 or len(bot) < 10:
        return None
    s = math.sqrt(se(top) ** 2 + se(bot) ** 2)
    if not s:
        return None
    return {"diff": mean(top) - mean(bot), "z": (mean(top) - mean(bot)) / s, "n_top": len(top), "n_bot": len(bot),
            "top": mean(top), "bot": mean(bot)}


def trend_episodes(days, rows, symbol, period):
    """Hindsight trend episodes vs when the trailing reads noticed them.
    Hindsight truth for a day = the 21-day window CENTERED on it (10 days back, 10 forward) has an
    efficiency ratio >= REG_ER_TREND. A read 'detects' on the second day in a row it says trending
    in the episode's direction."""
    n = len(days)
    c = [d["close"] for d in days]
    bad = [0]
    for d in days:
        bad.append(bad[-1] + (0 if d.get("clean", 1) else 1))
    truth = [0] * n
    for i in range(10, n - 10):
        if bad[i + 11] - bad[i - 10] > 0:           # a hole inside the 21-day window: no hindsight verdict
            continue
        net = c[i + 10] - c[i - 10]
        path = sum(abs(c[j] - c[j - 1]) for j in range(i - 9, i + 11))
        if path and abs(net) / path >= REG_ER_TREND:
            truth[i] = 1 if net > 0 else -1
    day_r = defaultdict(float)
    for r_ in rows:
        if r_["family"] in ("breakout", "momentum", "swing"):
            day_r[r_["day"]] += r_["r"]

    def on(i, sign, speed):
        d = days[i]
        if not d.get("reads_ok", 1):                # the read was built across a hole: it says nothing
            return False
        if speed == "slow":
            return d.get("er20") is not None and d["er20"] >= REG_ER_TREND and d["sign20"] == sign
        return d.get("er5") is not None and d["er5"] >= FAST_ER_TREND and d["sign5"] == sign

    out = []
    i = 0
    while i < n:
        if truth[i] == 0:
            i += 1
            continue
        j = i
        while j + 1 < n and truth[j + 1] == truth[i]:
            j += 1
        if j - i + 1 >= EPISODE_MIN_DAYS:
            sign = truth[i]
            ep = {"symbol": symbol, "period": period, "start": days[i]["day"], "end": days[j]["day"],
                  "days": j - i + 1, "dir": "up" if sign > 0 else "down",
                  "r_total": sum(day_r[days[x]["day"]] for x in range(i, j + 1))}
            for speed in ("slow", "fast"):
                det = None
                for x in range(max(i, 1), j + 1):
                    if on(x, sign, speed) and on(x - 1, sign, speed):
                        det = x
                        break
                over = 0
                x = j + 1
                while det is not None and x < n and on(x, sign, speed):
                    over += 1
                    x += 1
                ep[speed + "_lag_days"] = (det - i) if det is not None else None
                ep[speed + "_r_before"] = sum(day_r[days[x]["day"]] for x in range(i, det if det is not None else j + 1))
                ep[speed + "_r_after"] = sum(day_r[days[x]["day"]] for x in range(det, j + 1)) if det is not None else 0.0
                ep[speed + "_overstay_days"] = over
                ep[speed + "_r_overstay"] = sum(day_r[days[x]["day"]] for x in range(j + 1, j + 1 + over))
            out.append(ep)
        i = j + 1
    return out


def _write_csv(path, rows, first=()):
    if not rows:
        return
    keys = list(first)
    for r_ in rows:
        for k in r_:
            if k not in keys:
                keys.append(k)
    import csv
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(keys)
        for r_ in rows:
            w.writerow(["" if r_.get(k) is None else (("%.5f" % r_[k]) if isinstance(r_[k], float) else r_[k]) for k in keys])


def _ms(xs):
    return "%+.3f +/-%.3f n=%-4d" % (mean(xs), se(xs), len(xs)) if xs else "      (no trades)     "


def collect_symbol(rep, sym, m, xflags, dq=None):
    name = sym["name"]
    segs = [("A", 0.0, epoch_of(SEAL_START)), ("B", epoch_of(SEAL_END), 1e18)]
    rows, days, eps, notes = [], [], [], []
    all_rows, tags = [], []             # all_rows = every trade the engine took; rows = the ones the analysis uses
    hour_rng, box_days = [[0.0, 0] for _ in range(24)], [0, 0]
    for period, lo_, hi_ in segs:
        ms = _slice_m1(m, lo_, hi_)
        if ms.n < 5000:
            notes.append("period %s: no data" % period)
            continue
        bars, atr = build_m15(ms)
        col = Collector(sym, ms, bars, atr, period, xflags).run()
        if dq is not None and not dq.status:
            tags.append(dq.tag(col, period))
        all_rows += col.rows
        kept = [r_ for r_ in col.rows if r_.get("data_ok", 1)] if CLEAN_ONLY else col.rows
        rows += kept
        days += col.days_out
        for hh in range(24):
            hour_rng[hh][0] += col.hour_rng[hh][0]
            hour_rng[hh][1] += col.hour_rng[hh][1]
        box_days[0] += col.box_days[0]
        box_days[1] += col.box_days[1]
        eps += trend_episodes(col.days_out, kept, name, period)
        notes.append("period %s: %s .. %s | %d M15 bars | %d trades (%d kept after cutting holes) | %d still open at the end (dropped)" % (
            period, time.strftime("%Y-%m-%d", time.gmtime(ms.ts[0])), time.strftime("%Y-%m-%d", time.gmtime(ms.ts[-1])),
            len(bars), len(col.rows), len(kept), col.dropped))
    A = [r_ for r_ in rows if r_["period"] == "A"]
    B = [r_ for r_ in rows if r_["period"] == "B"]

    rep.p("")
    rep.p("#" * 78)
    rep.p("%s   (costs %.2f bp round trip%s, swap long %.6g / short %.6g per night)" % (
        name, sym["cost_bp"], (" + %.4g price units" % sym["cost_px"]) if sym.get("cost_px") else "",
        sym["swap_long"], sym["swap_short"]))
    rep.p("#" * 78)
    for s_ in notes:
        rep.p("  " + s_)
    rep.p("  A = before %s, B = from %s. The years between are sealed and were not read." % (SEAL_START, SEAL_END))
    H = sym.get("hours", CLOCK_UTC)
    if sym.get("comm_min"):
        rep.p("  COSTS NOT IN THESE R FIGURES: the broker's $%.2f minimum commission per side. It is a fixed dollar" % sym["comm_min"])
        rep.p("  amount, so what it costs in R depends on position size; the 'house' mode charges it. Read this")
        rep.p("  report as 'does the idea hold', and the house report as 'could it be traded at this size'.")
    if H["clock"] == "ny":
        rep.p("  CLOCK: New York time (daylight saving followed). Box = the overnight range 20:30-09:30 NY, box lanes")
        rep.p("  trade 09:30-15:30 and are flat by 15:45; 'london' = the cash-morning range broken in the afternoon;")
        rep.p("  pdh, swing and dip enter in cash hours only. Stops, targets and every ATR distance are gold's, unchanged.")
        rep.p("  This translation was fixed by reasoning BEFORE any result. A bad result here does not earn a re-map.")
    elif H["clock"] == "eu":
        rep.p("  CLOCK: European time (London time - 1h = Berlin time - 2h, daylight saving followed): the London / Xetra")
        rep.p("  open is ALWAYS lane-hour 07:00 and the New York cash open 13:30. Box = the overnight range 00:00-07:00,")
        rep.p("  every other lane hour is gold's, unchanged. Fixed by reasoning BEFORE any result: a bad result here")
        rep.p("  does not earn a re-map.")
    else:
        rep.p("  CLOCK: UTC, as before.")
    avg_h = [(hour_rng[hh][0] / hour_rng[hh][1], hh) for hh in range(24) if hour_rng[hh][1] >= 50]
    if avg_h:
        top = sorted(avg_h, reverse=True)[:3]
        rep.p("  CLOCK CHECK: the biggest M15 bars are at lane hours %s. Expected at or near the top: %s." % (
            ", ".join("%02d:00" % hh for _, hh in top), H["busy_hour"]))
        rep.p("    If the expected hour is not there, the timestamps are not what the tool assumes (see")
        rep.p("    DB_UTC_OFFSET_HOURS) and every session lane below is misplaced: fix that before reading on.")
    if sum(box_days):
        rep.p("  box usable on %d of %d weekdays (%.0f%%); the rest had too few bars or a box outside %g-%g ATR." % (
            box_days[0], sum(box_days), 100.0 * box_days[0] / sum(box_days), MIN_RANGE_ATR, MAX_RANGE_ATR))
    report_coverage(rep, name, dq, tags, all_rows, rep.dir)
    if not rows:
        return {"rows": rows, "days": days, "eps": eps, "tests": []}

    # ---- 1. lanes and families ----
    rep.p("")
    rep.p("-" * 78)
    rep.p("1. EVERY LANE IN SHADOW  (R per trade, net of costs; +/- is one standard error)")
    rep.p("-" * 78)
    rep.p("  %-10s %-9s  %-26s %-26s" % ("lane", "family", "period A", "period B"))
    for fam in FAMILIES + ["control"]:
        for ln in [k for k, v in FAMILY.items() if v == fam]:
            rep.p("  %-10s %-9s  %-26s %-26s" % (ln, fam, _ms([r_["r"] for r_ in A if r_["lane"] == ln]),
                                                 _ms([r_["r"] for r_ in B if r_["lane"] == ln])))
        if fam != "control":
            rep.p("  %-10s %-9s  %-26s %-26s" % ("= " + fam, "", _ms([r_["r"] for r_ in A if r_["family"] == fam]),
                                                 _ms([r_["r"] for r_ in B if r_["family"] == fam])))
            rep.p("")

    if tags:
        report_evidence(rep, name, tags, all_rows, days, rep.dir)

    # ---- 2. predicted signals ----
    tests = []
    rep.p("-" * 78)
    rep.p("2. SIGNALS WITH A PREDICTED DIRECTION  (top third minus bottom third of the signal, in R)")
    rep.p("-" * 78)
    rep.p("  PASS = z >= %.1f in EACH period AND combined z >= %.1f. z is already signed so that" % (PASS_EACH_Z, PASS_Z))
    rep.p("  positive = the way theory said. A signal that works the opposite way is a fail, not a find.")
    n_tests = 0
    for fam in FAMILIES:
        rep.p("")
        rep.p("  %s" % fam)
        for key, sign, why in SIGNAL_TESTS[fam]:
            n_tests += 1
            za = _hi_lo_z([r_ for r_ in A if r_["family"] == fam], key)
            zb = _hi_lo_z([r_ for r_ in B if r_["family"] == fam], key)
            if za is None or zb is None:
                rep.p("    %-16s not enough trades in one of the periods   (%s)" % (key, why))
                tests.append({"symbol": name, "kind": "predicted", "family": fam, "signal": key, "verdict": "no data"})
                continue
            a_, b_ = za["z"] * sign, zb["z"] * sign
            comb = (a_ + b_) / math.sqrt(2.0)
            ok = a_ >= PASS_EACH_Z and b_ >= PASS_EACH_Z and comb >= PASS_Z
            rep.p("    %-16s A %+5.2fR z%+5.2f | B %+5.2fR z%+5.2f | combined z %+5.2f  %s" % (
                key, za["diff"] * sign, a_, zb["diff"] * sign, b_, comb, "PASS" if ok else "-"))
            rep.p("    %-16s   (%s)" % ("", why))
            tests.append({"symbol": name, "kind": "predicted", "family": fam, "signal": key, "expected": sign,
                          "A_diff_r": za["diff"], "A_z": a_, "B_diff_r": zb["diff"], "B_z": b_, "combined_z": comb,
                          "verdict": "PASS" if ok else "fail"})
    rep.p("")
    rep.p("  %d signals tested. By luck alone, expect about %.1f of them to pass." % (n_tests, n_tests * 0.015))

    # ---- 3. regime reads, two-sided ----
    rep.p("")
    rep.p("-" * 78)
    rep.p("3. REGIME READS AT TWO SPEEDS  (no direction predicted: looked at both ways, so a stricter bar)")
    rep.p("-" * 78)
    rep.p("  er5/er20 = how straight the market moved over 5 / 20 days | vol3rel = last 3 days' range vs 20")
    rep.p("  volrank = volatility vs its own last 120 days | turning = fast and slow trend disagree")
    rep.p("  asia_rel = Asian range vs average day | day_eff = how straight today has moved so far")
    rep.p("  HOLDS = same sign in both periods AND |combined z| >= %.1f" % EXPLORE_Z)
    n_exp = 0
    rep.p("  %-13s" % "read" + "".join("%-16s" % f for f in FAMILIES))
    for key in REGIME_READS:
        line = "  %-13s" % key
        for fam in FAMILIES:
            n_exp += 1
            za = _hi_lo_z([r_ for r_ in A if r_["family"] == fam], key)
            zb = _hi_lo_z([r_ for r_ in B if r_["family"] == fam], key)
            if za is None or zb is None:
                line += "%-16s" % "n/a"
                continue
            comb = (za["z"] + zb["z"]) / math.sqrt(2.0)
            ok = za["z"] * zb["z"] > 0 and abs(comb) >= EXPLORE_Z
            line += "%-16s" % ("%+.1f/%+.1f%s" % (za["z"], zb["z"], " HOLDS" if ok else ""))
            tests.append({"symbol": name, "kind": "regime read", "family": fam, "signal": key, "A_diff_r": za["diff"],
                          "A_z": za["z"], "B_diff_r": zb["diff"], "B_z": zb["z"], "combined_z": comb,
                          "verdict": "HOLDS" if ok else "-"})
        rep.p(line)
    rep.p("  (each cell: z in period A / z in period B; positive = higher read went with better trades)")
    rep.p("  %d cells. By luck alone, expect about %.1f to hold." % (n_exp, n_exp * 0.012))

    # ---- 4. persistence ----
    rep.p("")
    rep.p("-" * 78)
    rep.p("4. DO THE READS PERSIST?  (this week vs next week; a read that doesn't persist can't be a filter)")
    rep.p("-" * 78)
    for period in ("A", "B"):
        dd = [d for d in days if d["period"] == period and d.get("clean", 1)]
        wk = []
        for i in range(0, len(dd) - 4, 5):
            blk = dd[i:i + 5]
            cl = [x["close"] for x in blk]
            path = sum(abs(cl[j] - cl[j - 1]) for j in range(1, 5))
            wk.append((abs(cl[-1] - cl[0]) / path if path else 0.0, mean([x["range_pct"] for x in blk]),
                       1 if cl[-1] > cl[0] else -1))
        if len(wk) < 10:
            continue
        ce = _corr([w[0] for w in wk[:-1]], [w[0] for w in wk[1:]])
        cv = _corr([w[1] for w in wk[:-1]], [w[1] for w in wk[1:]])
        same = sum(1 for a_, b_ in zip(wk[:-1], wk[1:]) if a_[2] == b_[2]) / float(len(wk) - 1)
        rep.p("  period %s (%d weeks): straightness %+.2f | volatility %+.2f | same direction next week %.0f%%" % (
            period, len(wk), ce or 0.0, cv or 0.0, 100 * same))
    rep.p("  (first two are correlations: 0 = no memory, 1 = next week is the same; direction: 50% = coin flip)")

    # ---- 5. episodes ----
    rep.p("")
    rep.p("-" * 78)
    rep.p("5. TREND EPISODES: HOW LATE ARE THE READS?  (trend-side families: breakout + momentum + swing)")
    rep.p("-" * 78)
    rep.p("  An episode = a stretch that, looking back with hindsight, was a trend (>= %d days)." % EPISODE_MIN_DAYS)
    rep.p("  slow = 20-day read, fast = 5-day read; a read detects on its 2nd day in a row.")
    for period in ("A", "B"):
        ee = [e for e in eps if e["period"] == period]
        if not ee:
            rep.p("  period %s: no episodes" % period)
            continue
        ln = sorted(e["days"] for e in ee)
        rep.p("  period %s: %d episodes, median length %d days, total R earned inside them %+.1f" % (
            period, len(ee), ln[len(ln) // 2], sum(e["r_total"] for e in ee)))
        for sp in ("slow", "fast"):
            lags = sorted(e[sp + "_lag_days"] for e in ee if e[sp + "_lag_days"] is not None)
            miss = sum(1 for e in ee if e[sp + "_lag_days"] is None)
            rep.p("    %-4s read: detected %d, missed %d | median lag %s days | R before detection %+.1f, after %+.1f,"
                  " staying on after the end %+.1f" % (
                      sp, len(lags), miss, lags[len(lags) // 2] if lags else "n/a",
                      sum(e[sp + "_r_before"] for e in ee), sum(e[sp + "_r_after"] for e in ee),
                      sum(e[sp + "_r_overstay"] for e in ee)))

    # ---- 6. stand-aside days ----
    rep.p("")
    rep.p("-" * 78)
    rep.p("6. STAND-ASIDE DAYS  (flags known at the open; is every family worse on them?)")
    rep.p("-" * 78)
    rep.p("  shock = yesterday's range >= %.0fx average | gap = big opening gap | turning = fast/slow trend disagree" %
          STANDASIDE_SHOCK)
    rep.p("  xshock = the OTHER market had a shock day yesterday")
    for flag in ("shock", "gap", "turning", "xshock"):
        if not any(r_.get(flag) for r_ in rows):
            rep.p("  %-8s never set" % flag)
            continue
        rep.p("  %s" % flag)
        worse_all = True
        for fam in FAMILIES:
            cells = []
            for per in (A, B):
                on_ = [r_["r"] for r_ in per if r_["family"] == fam and r_.get(flag) == 1.0]
                off = [r_["r"] for r_ in per if r_["family"] == fam and r_.get(flag) == 0.0]
                cells.append("%+.3f (n=%d) vs %+.3f" % (mean(on_), len(on_), mean(off)) if len(on_) >= 5 else "too few")
                if len(on_) < 5 or mean(on_) >= mean(off):
                    worse_all = False
            rep.p("    %-9s A: flagged %-28s | B: flagged %-28s" % (fam, cells[0], cells[1]))
        rep.p("    -> %s" % ("every family worse on flagged days in both periods" if worse_all
                             else "not consistently worse"))

    # ---- 7. trust ladder ----
    rep.p("")
    rep.p("-" * 78)
    rep.p("7. TRUST LOOKUP  (family x the bot's regime label)")
    rep.p("-" * 78)
    rep.p("  rung: 'normal' = clearly positive (mean - 1 se > 0) in BOTH periods | 'shadow' = clearly negative")
    rep.p("  in both | 'scout' = everything in between. No rung here ever means 'risk more'.")
    for fam in FAMILIES:
        for reg in ("trending", "volatile", "choppy", "drift"):
            a_ = [r_["r"] for r_ in A if r_["family"] == fam and r_.get("regime") == reg]
            b_ = [r_["r"] for r_ in B if r_["family"] == fam and r_.get("regime") == reg]
            if len(a_) < 20 or len(b_) < 20:
                rung = "scout (too few trades to judge)"
            elif mean(a_) - se(a_) > 0 and mean(b_) - se(b_) > 0:
                rung = "normal"
            elif mean(a_) + se(a_) < 0 and mean(b_) + se(b_) < 0:
                rung = "shadow"
            else:
                rung = "scout"
            rep.p("  %-9s %-9s A %-26s B %-26s -> %s" % (fam, reg, _ms(a_), _ms(b_), rung))
        rep.p("")

    # ---- 8. exit menu + timing ----
    rep.p("-" * 78)
    rep.p("8. THE FIXED EXIT MENU AND TIMING  (same entries, same stop; only the way out differs)")
    rep.p("-" * 78)
    rep.p("  as built = the lane's own exit | 1R = nearer target | hold = no target, stop or the clock")
    rep.p("  trail = after +1R the stop follows 1R behind the best price")
    rep.p("  %-9s %-3s %10s %10s %10s %10s | %8s %9s %10s %9s" % (
        "family", "", "as built", "1R", "hold", "trail", "best R", "given", "ran on", "day used"))
    for fam in FAMILIES:
        for lab, per in (("A", A), ("B", B)):
            x = [r_ for r_ in per if r_["family"] == fam]
            if not x:
                continue
            du = [r_["day_used"] for r_ in x if r_.get("day_used") is not None]
            rep.p("  %-9s %-3s %+10.3f %+10.3f %+10.3f %+10.3f | %8.2f %9.2f %10.2f %9.2f" % (
                fam, lab, mean([r_["r"] for r_ in x]), mean([r_["exit_1r"] for r_ in x]),
                mean([r_["exit_hold"] for r_ in x]), mean([r_["exit_trail"] for r_ in x]),
                mean([r_["mfe_r"] for r_ in x]), mean([r_["giveback_r"] for r_ in x]),
                mean([r_["after_exit_r"] for r_ in x]), mean(du)))
    rep.p("  best R = furthest the trade got our way | given = how much of that was handed back by the exit")
    rep.p("  ran on = how far price kept going our way AFTER the exit | day used = share of an average day's")
    rep.p("  range already covered when the trade was entered (1.0 = a full average day)")

    # ---- 9. stop menu ----
    def _cell(per, sel, key):
        x = [r_[key] for r_ in per if sel(r_) and r_.get(key) is not None]
        return ("%+.2f" % mean(x)) if len(x) >= 15 else "  . "

    def _both(sel, key, base="r"):
        """'<<' when this variant is positive in BOTH periods and better than as-built in both."""
        out = []
        for per in (A, B):
            x = [r_[key] for r_ in per if sel(r_) and r_.get(key) is not None]
            b_ = [r_[base] for r_ in per if sel(r_)]
            out.append(len(x) >= 15 and mean(x) > 0 and mean(x) > mean(b_))
        return all(out)

    skeys = [("stop_%s" % str(k).replace(".", ""), "%gx" % k) for k in STOP_MENU]
    order = [("stop_05", "0.5x")] + [("r", "built")] + [x for x in skeys if x[0] != "stop_05"]
    units = [(ln, (lambda r_, ln=ln: r_["lane"] == ln)) for fam in FAMILIES for ln in [k for k, v in FAMILY.items() if v == fam]]
    units += [("= " + fam, (lambda r_, fam=fam: r_["family"] == fam)) for fam in FAMILIES]
    rep.p("")
    rep.p("-" * 78)
    rep.p("9. STOP MENU  (same entry, same target price, same clock; only the stop distance changes)")
    rep.p("-" * 78)
    rep.p("  Each number is R per trade net of costs IN THAT VARIANT'S OWN R (its risk = its own stop distance).")
    rep.p("  'built' = the lane as it is. '<<' = a variant that is positive in BOTH periods and beats 'built' in both.")
    rep.p("  %-11s | %s | %s" % ("", "period A:  " + " ".join("%6s" % lab for _, lab in order),
                                   "period B:  " + " ".join("%6s" % lab for _, lab in order)))
    for nm, sel in units:
        marks = [lab for key, lab in order if key != "r" and _both(sel, key)]
        rep.p("  %-11s | %s | %s  %s" % (nm, "           " + " ".join("%6s" % _cell(A, sel, key) for key, _ in order),
                                           "           " + " ".join("%6s" % _cell(B, sel, key) for key, _ in order),
                                           ("<< " + ",".join(marks)) if marks else ""))

    # ---- 10. entry delay ----
    rep.p("")
    rep.p("-" * 78)
    rep.p("10. ENTRY DELAY  (enter 1 or 2 bars later, only if the original stop and target were not touched)")
    rep.p("-" * 78)
    rep.p("  R per trade in the delayed trade's own R. 'took' = share of the lane's signals still alive to enter.")
    rep.p("  Compare with 'built' on ALL signals: a delay only helps if what it enters beats what it skips.")
    rep.p("  %-11s | %-40s | %-40s" % ("", "period A:  built   +1 bar (took)   +2 bars (took)",
                                         "period B:  built   +1 bar (took)   +2 bars (took)"))
    for nm, sel in units:
        cells = []
        for per in (A, B):
            base = [r_["r"] for r_ in per if sel(r_)]
            c_ = "           %+.2f" % mean(base) if len(base) >= 15 else "             .  "
            for k in DELAY_MENU:
                x = [r_["delay_%d" % k] for r_ in per if sel(r_) and r_.get("delay_%d" % k) is not None]
                c_ += ("   %+.2f (%3.0f%%)  " % (mean(x), 100.0 * len(x) / max(1, len(base)))) if len(x) >= 15 else "     .           "
            cells.append(c_)
        marks = [("+%d" % k) for k in DELAY_MENU if _both(sel, "delay_%d" % k)]
        rep.p("  %-11s | %-40s | %-40s %s" % (nm, cells[0], cells[1], ("<< " + ",".join(marks)) if marks else ""))

    # ---- 11. cost rule ----
    rep.p("")
    rep.p("-" * 78)
    rep.p("11. COST RULE  (only trades whose stop is at least %.0f round-trip costs wide)" % COST_MIN_STOP_MULT)
    rep.p("-" * 78)
    rep.p("  %-11s | %-34s | %-34s" % ("", "period A: all -> rule (kept, cost/R)", "period B: all -> rule (kept, cost/R)"))
    for nm, sel in units:
        cells = []
        for per in (A, B):
            x = [r_ for r_ in per if sel(r_)]
            y = [r_ for r_ in x if r_.get("cost_ok") == 1.0]
            cells.append(("%+.2f -> %+.2f (%3.0f%%, %.3f)" % (mean([r_["r"] for r_ in x]), mean([r_["r"] for r_ in y]) if y else 0.0,
                                                           100.0 * len(y) / len(x), mean([r_["cost_r"] for r_ in x])))
                         if len(x) >= 15 else "  .")
        rep.p("  %-11s | %-34s | %-34s" % (nm, cells[0], cells[1]))
    rep.p("  kept = share of the lane's trades that satisfy the rule | cost/R = average cost as a share of the risk")

    d = rep.dir
    _write_csv(os.path.join(d, "trades_%s.csv" % name), rows,
               ("symbol", "period", "family", "lane", "day", "entry_time", "exit_time", "dir", "r"))
    _write_csv(os.path.join(d, "days_%s.csv" % name), days, ("symbol", "period", "day", "clean", "reads_ok"))
    if CLEAN_ONLY:
        _write_csv(os.path.join(d, "trades_%s_cut.csv" % name), [r_ for r_ in all_rows if not r_.get("data_ok", 1)],
                   ("symbol", "period", "family", "lane", "day", "entry_time", "exit_time", "dir", "r", "cut_why"))
    _write_csv(os.path.join(d, "episodes_%s.csv" % name), eps)
    _write_csv(os.path.join(d, "tests_%s.csv" % name), tests)
    return {"rows": rows, "days": days, "eps": eps, "tests": tests}


OLD_FROM, OLD_TO = "2014-01-01", "2020-01-01"     # 'oldcollect': the years no lane has traded yet (not the sealed exam)


def run_collect(start, end):
    # a run that stops before the sealed years is a partial one: it gets its own folder name, so 'house' and the
    # lab's main parts (which use the newest collect_* folder) never pick it up by accident
    rep = Report("oldcollect" if end <= epoch_of(SEAL_START) else "collect")
    t_start = time.time()
    rep.p("=" * 78)
    rep.p("DATA COLLECTION  --  every lane in shadow, what was known at entry, what happened after")
    rep.p("=" * 78)
    rep.p("Nothing here decides anything. It measures, on the two TRAINING periods only.")
    rep.p("Sealed exam years %s .. %s: not read by this mode, whatever EXAM_UNLOCK says." % (SEAL_START, SEAL_END))
    rep.p("Lanes: the bot's 16 + swing (20-day breakout, trailing exit) + dip (pullback in a trend) + control.")
    rep.p("US 500 now runs on ITS OWN clock (New York cash session), not gold's hours: see the CLOCK lines under")
    rep.p("its heading. Gold is untouched: same clock, same trades as the previous collection.")
    rep.p("NEW MARKETS (EURUSD, USDJPY, XTIUSD = WTI, GERMANY40): each on its own clock with its own costs from its symbol sheet;")
    rep.p("see the COSTS and CLOCK lines under each heading. FX and Germany 40 use the European clock (London open = lane 07:00),")
    rep.p("WTI the New York clock. Japan 225 is left out on purpose (Tokyo-session data only until Oct 2024, a 4-year hole).")
    rep.p("Changed since the first collection: scalp's stop is the far end of its impulse bar (was the midpoint);")
    rep.p("swing has no 20-day cap (trailing exit only); session lanes close at the day's last bar if the data ends")
    rep.p("early. New sections 9-11: stop menu, entry delay, cost rule. Sections 1-8 are otherwise as before.")
    rep.p("DATA QUALITY (new): bars.db's hole list decides which days and trades a hole touches. Section 0 shows what was")
    rep.p("cut and why, 1b/1c count trading days and trades taken per lane and per regime. Bars read from %s on" % time.strftime("%Y-%m-%d", time.gmtime(start)))
    rep.p("(COLLECT_FROM, or the start date you gave). Cutting rule: %d+ unexplained minutes; CLEAN_ONLY=%s." % (DIRTY_MIN_MINUTES, CLEAN_ONLY))
    # each market's shock days, so the other one can use them as a cross-market flag
    shocks, loaded, missing = {}, {}, {}
    for sym in COLLECT_SYMBOLS:
        try:
            print("loading %s ..." % sym["name"])
            m = load_m1(start, end, sym["match"])
            loaded[sym["name"]] = m
            sd = {}
            for lo_, hi_ in ((0.0, epoch_of(SEAL_START)), (epoch_of(SEAL_END), 1e18)):
                ms = _slice_m1(m, lo_, hi_)
                if ms.n >= 5000:
                    sd.update(shock_days(build_m15(ms)[0]))
            shocks[sym["name"]] = sd
        except RuntimeError as e:
            missing[sym["name"]] = str(e).splitlines()[0]
    for sym in COLLECT_SYMBOLS:
        if sym["name"] in missing:
            rep.p("")
            rep.p("%s: not collected (%s)" % (sym["name"], missing[sym["name"]]))
            continue
        other = {}
        refs = sym.get("xref")
        for k, v in shocks.items():
            if k != sym["name"] and (refs is None or k in refs):
                other.update(v)
        print("collecting %s ..." % sym["name"])
        collect_symbol(rep, sym, loaded[sym["name"]], other, DataQuality(sym))
    rep.p("")
    rep.p("files in this folder: trades_<symbol>.csv (one row per trade), days_<symbol>.csv (daily reads and flags),")
    rep.p("episodes_<symbol>.csv (trend episodes), tests_<symbol>.csv (every signal test with its numbers)")
    rep.p("runtime %.1fs" % (time.time() - t_start))
    rep.save()


# ============================================================================
# HOUSE: the earners-and-allowance design, replayed on a collect run   (python asiabo_offline.py house)
#
# Reads the newest reports/collect_*/ folder (run 'collect' first) and replays the HOUSE on its trades:
#   1. WHO GOES OUT   a lane trades only while its ZONE is on (its written "works when" rule)
#   2. HOW BIG        a ladder of rungs set by the PESSIMISTIC estimate of the lane's in-zone edge
#   3. THE ALLOWANCE  the most the house may lose in a week if everything out hits its stop
#   4. THE CUSHION    size above the minimum rung is paid for only out of profit above the floor
# Every size is recomputed from the current state; nothing is remembered as a decision, so every
# step down can climb back and every step up can shrink. There is no permanent stop.
# SHADOW ONLY: this measures the design. It decides nothing in the bot.
#
# HONESTY NOTE: the zones below were found on the same 2020-2021 / 2024-2026 data this replay runs
# on, so its results flatter the zones. The random-twin comparison is fair about the HOUSE mechanics
# (twins get the same zones, ladder, allowance and cushion) but not about how the zones were chosen.
# ============================================================================
HOUSE_SYMBOL = "XAUUSD"         # the market the zones were found on; its collect file decides which folder is used
HOUSE_SYMBOLS = ["XAUUSD", "US500", "EURUSD", "USDJPY", "XTIUSD", "GERMANY40"]   # replayed in this order. Every market but gold gets gold's zones and thresholds AS THEY ARE:
                                      # nothing about a zone was chosen on US 500, so there it is an independent check.
HOUSE_START = 10000.0

# ---- 1. zones (candidates; thresholds fixed from 2020-2021 trades and not re-fitted here) ----
ACTIVE_DAY = {"day_eff": (">=", 0.189),          # the day has moved in a fairly straight line so far
              "asia_rel": (">=", 0.372),         # the Asian range is large against an average day
              "prev_range_rel": ("<=", 0.836),   # yesterday was quieter than usual
              "open_move_with": (">=", 0.291)}   # the trade goes with the day's move from the open
ACTIVE_DAY_NEED = 3                              # at least 3 of the 4
ZONES = {
    "main": "active_day", "london": "active_day", "retest": "active_day", "nr7": "active_day", "pdh": "active_day",
    "trend": "calm_agree",     # volatility in the lower half of its own history AND fast/slow trend agree
    "fade": "tide",            # gold has moved straight for three months AND the trade goes with that move
    "swing": "base_trend",     # with the six-month direction AND volatility in the lower half of its history
}                              # every other lane has no zone yet: shadow only (rung 0)
TIDE_STRAIGHT = 0.10           # 60-day efficiency ratio at or above this = "moved straight"

# ---- 2. ladder ----
RUNG_RISK_PCT = (0.0, 0.25, 0.50, 0.75, 1.00)    # % of the FLOOR risked per trade on rungs 0..4
LADDER_Z = 1.0                 # pessimistic estimate = average - Z standard errors of the in-zone record
RUNG_UP = {2: (60, 0.00), 3: (100, 0.03), 4: (150, 0.06)}   # rung: (in-zone trades needed, pessimistic R needed)
RUNG_HYSTERESIS = 0.03         # a rung is kept until the estimate is this far BELOW the line that earned it
BENCH_MIN_TRADES = 100         # BENCH ON CONDITIONS, NOT ON RECORD: a lane in its zone always goes out at rung 1.
                               # Its record can bench it only when it is LONG (this many in-zone trades) and even
                               # its optimistic end is below zero. (The first version also benched on short records
                               # and a warm-up wait; on the real trades that cost about 10 points per period, because
                               # a lane's recent results predict nothing.)
RUNG_STEP_TRADES = 20          # CAUTIOUS UP: at most one rung per this many of the lane's in-zone trades
RECENT_N, RECENT_DROP_R = 10, -4.0   # QUICK DOWN: last 10 live trades at or below -4R -> down two rungs at once,
                                     # but never below rung 1 (recent results may shrink a lane, not bench it)
RECORD_WINDOW = 300            # the in-zone record that is judged (newest trades)

# ---- 3. allowance (possibility side: counted BEFORE a trade goes out) ----
ALLOW_NOTCHES_PCT = (1.5, 2.0, 2.5, 3.0, 4.0)    # % of the floor the house may lose in one week.
                                                 # The lowest notch is 6 minimum-size stop-outs: a clamp tighter
                                                 # than that blocks ordinary trading instead of bounding damage
                                                 # (the first version started at 1% and strangled the earners).
ALLOW_START_NOTCH = 1
ALLOW_DAY_SHARE = 0.5          # at most this share of the week's allowance in one day
ALLOW_UP_WEEKS = 4             # CAUTIOUS UP: one notch per 4 good weeks; a losing week takes one good week
                               # back off the count (it does not wipe the count, or the climb back never happens)
ALLOW_BAD_WEEK = 0.5           # QUICK DOWN: a week that loses this share of its allowance ...
ALLOW_DOWN_NOTCHES = 2         # ... costs two notches at once
SLIP_MARGIN = 1.25             # every stop is counted as this much worse than planned

# ---- 4. cushion and floor ----
CUSHION_SHARE = 0.25           # all risk above rung-1 size, house-wide, may total this share of the cushion
FLOOR_TRIGGER_PCT, FLOOR_HOLD_DAYS, FLOOR_SHARE = 2.0, 5, 0.5   # equity 2% above the floor for 5 weekdays ->
                                                                # the floor moves up by half the gap
# ---- 5. recovery sizing (bounded; not a chase) ----
# Without this, size is largest at the top (cushion) and smallest in the hole (no cushion), so the climb
# back is slower than the fall. Recovery sizing lifts a PROVEN lane's size while the account is below its
# previous high, in step with how far below it is, so the arithmetic of getting back works.
#   who:   only a lane whose in-zone record has earned rung 2 on evidence (RUNG_UP[2]: enough trades and
#          a pessimistic estimate at or above zero). An unproven lane stays at minimum size.
#   size:  minimum size x (1 + REC_STEP_PER_PCT x depth%), never above REC_MAX_MULT.
#   bound: still inside the weekly allowance, so the worst week is unchanged.
#   brake: beyond REC_OFF_DEPTH_PCT the evidence itself is in doubt, so it switches OFF (back to minimum).
#   It shrinks by itself as the account climbs back, and is zero at a new high.
# RESULT ON THE REAL TRADES (Oct 2026): it did NOT shorten the time below the previous high (180 -> 344
# weekdays in 2020-21, 197 -> 218 in 2024-26). The bigger trades used up the weekly allowance and crowded
# out ordinary ones, and time under water is set by edge and trade count, not by size (see the RECOVERY
# ARITHMETIC lines in the report). So it ships OFF: REC_MAX_MULT = 1.0. Set it to 2.0 to switch it on.
REC_ON_DEPTH_PCT = 1.0
REC_STEP_PER_PCT = 0.25
REC_MAX_MULT = 1.0
REC_OFF_DEPTH_PCT = 8.0

# ---- 6. cheques (a lane whose stop is too wide for minimum size) ----
# The smallest position is 1 unit. If one unit risks more than the lane's budget (plus tolerance), the
# signal used to stay home. A lane that has shown it delivers may have the cheque cashed: it trades one
# unit anyway. The full real risk is counted in the allowance, so the house limit is not bent.
#   who:   in-zone record of at least CHEQUE_MIN_TRADES with a positive average
#   limit: one unit may risk at most CHEQUE_MAX_MULT x the minimum size
CHEQUE_MIN_TRADES = 20
CHEQUE_MAX_MULT = 3.0

HOUSE_MIN_UNIT = 1.0           # smallest position (1 oz); HOUSE_UNIT_TOL as in the bot's floor tolerance
HOUSE_UNIT_TOL = 0.5
EUR_USD_PROXY = 1.10           # Germany 40 is quoted in euros: its money figures use this flat rate (2020-26 range
                               # 0.96-1.25), so they are approximate to about 10%; R figures are not affected
# Per market (set in COLLECT_SYMBOLS): "min_unit" = smallest position AND the step, in the instrument's own units
# (default 1: one ounce / contract). EURUSD 1,000 = 0.01 lot of 100,000; USDJPY 1,000 = 0.01 lot; WTI 10 barrels =
# 0.10 lot of 100 barrels (the sheet gives no volume step, so the step is taken equal to the minimum).
# "quote" = how a price move becomes dollars: "usd" 1, "jpy" 1/price (USDJPY), "eur" EUR_USD_PROXY (Germany 40).


def _quote_to_usd(spec):
    q = (spec or {}).get("quote", "usd")
    if q == "jpy":
        return lambda px: 1.0 / px if px else 1.0
    if q == "eur":
        return lambda px: EUR_USD_PROXY
    return lambda px: 1.0
HOUSE_TWINS = 20               # random twins: same house, every trade's direction decided by a coin


def _house_folder():
    base = os.path.join(ROOT, "reports")
    folders = sorted(d for d in (os.listdir(base) if os.path.isdir(base) else []) if d.startswith("collect_")
                     and os.path.exists(os.path.join(base, d, "trades_%s.csv" % HOUSE_SYMBOL)))
    if not folders:
        raise RuntimeError("no collect run found under %s. Run 'collect' first; 'house' replays its trades." % base)
    return os.path.join(base, folders[-1])


def _house_inputs(folder, symbol):
    import csv

    def rd(name):
        with open(os.path.join(folder, name), newline="", encoding="utf-8") as f:
            return list(csv.DictReader(f))
    trades, days = rd("trades_%s.csv" % symbol), rd("days_%s.csv" % symbol)
    num = ("r", "gross_r", "stop_dist", "dir", "entry", "day_eff", "asia_rel", "open_move_with", "volrank", "turning")
    for t in trades:
        for k in num:
            v = t.get(k, "")
            t[k] = float(v) if v not in ("", None) else None
        t["t_in"] = epoch_of(t["entry_time"][:10]) + int(t["entry_time"][11:13]) * 3600 + int(t["entry_time"][14:16]) * 60
        t["t_out"] = epoch_of(t["exit_time"][:10]) + int(t["exit_time"][11:13]) * 3600 + int(t["exit_time"][14:16]) * 60
    # slow reads, from COMPLETED days before each trade's day only
    slow = {}
    for p in ("A", "B"):
        d = [x for x in days if x["period"] == p]
        cl = [float(x["close"]) for x in d]
        rp = [float(x["range_pct"]) for x in d]
        bad = [0]                                   # days flagged 'clean = 0' by collect (older folders have no flag)
        for x in d:
            bad.append(bad[-1] + (1 if str(x.get("clean", "1")) == "0" else 0))

        def whole(i, n):                            # no cut day in the n days before day i: the read spans no hole
            return bad[i] - bad[max(0, i - n)] == 0
        for i, x in enumerate(d):
            e = {}
            if i >= 22 and whole(i, 21):
                e["prev_range_rel"] = rp[i - 1] / mean(rp[i - 21:i - 1])
            if i > 60 and whole(i, 61):
                path = sum(abs(cl[j] - cl[j - 1]) for j in range(i - 60, i))
                e["er60"] = abs(cl[i - 1] - cl[i - 61]) / path if path else 0.0
                e["ret60"] = cl[i - 1] / cl[i - 61] - 1.0
            if i > 120 and whole(i, 121):
                e["ret120"] = cl[i - 1] / cl[i - 121] - 1.0
            slow[(p, x["day"])] = e
    for t in trades:
        e = slow.get((t["period"], t["day"]), {})
        t["prev_range_rel"] = e.get("prev_range_rel")
        t["er60"] = e.get("er60")
        t["ret60_with"] = e["ret60"] * t["dir"] if "ret60" in e else None
        t["ret120_with"] = e["ret120"] * t["dir"] if "ret120" in e else None
        t["zone"] = in_zone(t)
    return trades, days


def in_zone(t, z=None):
    """True / False, or None when the lane has no zone or the reads it needs are not available yet.
    z = a zone name to test this trade against instead of its own lane's (used for the control lane)."""
    z = z or ZONES.get(t["lane"])
    if z is None:
        return None
    if z == "active_day":
        if any(t.get(k) is None for k in ACTIVE_DAY):
            return None
        hits = sum(1 for k, (op, thr) in ACTIVE_DAY.items() if (t[k] >= thr if op == ">=" else t[k] <= thr))
        return hits >= ACTIVE_DAY_NEED
    if z == "calm_agree":
        if t.get("volrank") is None or t.get("turning") is None:
            return None
        return t["volrank"] <= 0.5 and t["turning"] == 0.0
    if z == "tide":
        if t.get("er60") is None or t.get("ret60_with") is None:
            return None
        return t["er60"] >= TIDE_STRAIGHT and t["ret60_with"] > 0
    if z == "base_trend":
        if t.get("ret120_with") is None or t.get("volrank") is None:
            return None
        return t["ret120_with"] > 0 and t["volrank"] <= 0.5
    return None


class House(object):
    """One period, replayed in time order. mode: 'house' (full design), 'zones_min' (zones, everything at
    rung 1, no allowance/cushion) or 'all_min' (every lane, no zones, rung 1: the old scouts-everywhere)."""

    def __init__(self, trades, weekdays, mode="house", flip=None, fee=None, spec=None):
        self.mode, self.flip = mode, flip
        self.mu = (spec or {}).get("min_unit", HOUSE_MIN_UNIT)    # smallest position and step
        self.qf = _quote_to_usd(spec)                              # price move -> dollars per unit
        self.fee = fee                        # (commission % of volume, minimum $ per side, sides) or None
        self.fee_paid, self.fee_n = 0.0, 0    # dollars paid ABOVE the percentage rate because of the minimum
        self.trades = [t for t in trades if t["lane"] != "control"]
        self.weekdays = weekdays
        self.E = self.F = self.peak = HOUSE_START
        self.notch, self.good_weeks, self.hold = ALLOW_START_NOTCH, 0, 0
        self.week, self.week_pnl, self.day, self.day_pnl = None, 0.0, None, 0.0
        self.open = {}
        self.rec = defaultdict(list)          # lane -> in-zone results, newest last (shadow and live alike)
        self.live = defaultdict(list)         # lane -> results of trades really taken
        self.rung = defaultdict(lambda: 1)    # a lane with a zone starts at the minimum rung
        self.since = defaultdict(int)         # in-zone trades since the lane's rung last changed
        self.blocked = defaultdict(int)
        self.lane_pnl, self.lane_n = defaultdict(float), defaultdict(int)
        self.rung_trades = defaultdict(lambda: [0, 0, 0, 0, 0])
        self.moves = {"up": 0, "down": 0, "notch_up": 0, "notch_down": 0, "floor": 0}
        self.max_dd = 0.0
        self.week_log, self.notch_weeks = [], defaultdict(int)
        self.extras = {"recovery": [0, 0.0], "cheque": [0, 0.0]}      # [trades, money]
        self.curve = []
        self.under_since, self.longest_under = None, 0

    def _r(self, t):
        if self.flip is None:
            return t["r"]
        return self.flip[id(t)] * t["gross_r"] - (t["gross_r"] - t["r"])     # coin-flip direction, same costs

    # ---- ladder ----
    def _estimate(self, lane):
        xs = self.rec[lane][-RECORD_WINDOW:]
        if len(xs) < 2:
            return len(xs), None, None
        mu, s = mean(xs), se(xs)
        return len(xs), mu - LADDER_Z * s, mu + LADDER_Z * s

    def _review(self, lane):
        n, lb, opt = self._estimate(lane)
        cur = self.rung[lane]
        if lb is None:
            target = keep = 1                         # no record yet: in zone means out, at minimum size
        elif n >= BENCH_MIN_TRADES and opt < 0:
            target = keep = 0                         # a LONG record whose optimistic end is negative: stay home
        else:
            target = keep = 1
            for r_ in (2, 3, 4):
                need_n, line = RUNG_UP[r_]
                if n >= need_n and lb >= line and target == r_ - 1:
                    target = r_
                if n >= need_n and lb >= line - RUNG_HYSTERESIS and keep == r_ - 1:
                    keep = r_
        if cur > keep:                                # QUICK DOWN: straight to the highest rung it can still hold
            self.rung[lane], self.since[lane] = keep, 0
            self.moves["down"] += 1
        elif target > cur:                            # CAUTIOUS UP: one rung, and only after enough new trades
            ok = self.since[lane] >= RUNG_STEP_TRADES or cur == 0     # back from the bench: straight to rung 1
            if ok:
                self.rung[lane], self.since[lane] = cur + 1, 0
                self.moves["up"] += 1

    # ---- calendar: floor, allowance ----
    def _roll(self, day):
        if day == self.day:
            return
        self.day, self.day_pnl = day, 0.0
        if self.E >= self.F * (1 + FLOOR_TRIGGER_PCT / 100.0):
            self.hold += 1
            if self.hold >= FLOOR_HOLD_DAYS:
                self.F += FLOOR_SHARE * (self.E - self.F)
                self.hold = 0
                self.moves["floor"] += 1
        else:
            self.hold = 0
        y, mo, d = map(int, day.split("-"))
        wk = "%d-W%02d" % datetime.date(y, mo, d).isocalendar()[:2]
        if wk != self.week:
            if self.week is not None:
                allow = self.F * ALLOW_NOTCHES_PCT[self.notch] / 100.0
                self.week_log.append((self.week, self.week_pnl, allow))
                self.notch_weeks[self.notch] += 1
                if self.week_pnl <= -ALLOW_BAD_WEEK * allow:
                    new = max(0, self.notch - ALLOW_DOWN_NOTCHES)
                    self.moves["notch_down"] += new != self.notch
                    self.notch, self.good_weeks = new, 0
                elif self.week_pnl > 0 and self.E >= self.F:      # a week with no trades is not a good week
                    self.good_weeks += 1
                    if self.good_weeks >= ALLOW_UP_WEEKS and self.notch < len(ALLOW_NOTCHES_PCT) - 1:
                        self.notch += 1
                        self.good_weeks = 0
                        self.moves["notch_up"] += 1
                elif self.week_pnl < 0:
                    self.good_weeks = max(0, self.good_weeks - 1)     # an idle week neither helps nor hurts
                self._week_end()
            self.week, self.week_pnl = wk, 0.0
        self.curve.append((day, self.E, self.F))
        if self.E < self.peak:
            if self.under_since is None:
                self.under_since = len(self.curve)
            self.longest_under = max(self.longest_under, len(self.curve) - self.under_since)
        else:
            self.under_since = None

    # ---- a signal arrives ----
    # ---- hooks: no-ops here; asiabo_lab.py overrides them to try extra machinery on the same replay ----
    def _gate(self, t):
        return False                    # True = this signal stays home

    def _merit(self, t):
        return False                    # True = a trade outside its zone may go out at minimum size

    def _size(self, t, lane, risk, base, tag):
        return risk, tag

    def _week_end(self):
        pass

    def _after(self, t, r, o):
        pass

    def _entry(self, t):
        lane = t["lane"]
        if self._gate(t):
            return
        if self.mode == "all_min":
            rung = 1
        else:
            merit = (not t["zone"]) and self._merit(t)
            if not merit:
                if t["zone"] is None:
                    self.blocked["no zone (shadow)"] += 1
                    return
                if not t["zone"]:
                    self.blocked["zone off"] += 1
                    return
            rung = 1 if (self.mode == "zones_min" or merit) else self.rung[lane]
            if rung == 0:
                self.blocked["rung 0"] += 1
                return
        base = self.F * RUNG_RISK_PCT[1] / 100.0
        if self.mode == "house" and rung > 1:
            cushion = max(0.0, self.E - self.F)
            extra_out = sum(o["extra"] for o in self.open.values())
            while rung > 1 and extra_out + (self.F * RUNG_RISK_PCT[rung] / 100.0 - base) > CUSHION_SHARE * cushion:
                rung -= 1
            if rung < self.rung[lane]:
                self.blocked["sized down: cushion"] += 1
        risk = self.F * RUNG_RISK_PCT[rung] / 100.0
        funded = risk                                  # the part of the size that rung + cushion pay for
        tag = None
        n_rec, lb, _opt = self._estimate(lane) if self.mode == "house" else (0, None, None)
        if self.mode == "house" and REC_MAX_MULT > 1.0:
            depth = (self.peak - self.E) / self.peak * 100.0
            proven = lb is not None and n_rec >= RUNG_UP[2][0] and lb >= RUNG_UP[2][1]
            if proven and REC_ON_DEPTH_PCT <= depth < REC_OFF_DEPTH_PCT:
                rec = base * min(REC_MAX_MULT, 1.0 + REC_STEP_PER_PCT * depth)
                if rec > risk:
                    risk, tag = rec, "recovery"
        risk, tag = self._size(t, lane, risk, base, tag)
        sd = t["stop_dist"] * self.qf(t.get("entry"))              # dollars at risk per unit (price units on USD markets)
        MU = self.mu
        units = math.floor(risk / sd / MU) * MU
        if units < MU:
            if sd * MU > risk * (1 + HOUSE_UNIT_TOL):
                xs = self.rec[lane][-RECORD_WINDOW:]
                cashable = (self.mode == "house" and CHEQUE_MAX_MULT > 0 and len(xs) >= CHEQUE_MIN_TRADES
                            and mean(xs) > 0 and sd * MU <= CHEQUE_MAX_MULT * base)
                if not cashable:
                    self.blocked["minimum lot too big"] += 1
                    return
                tag = "cheque"
            units = MU
        if self.mode == "house":
            allow = self.F * ALLOW_NOTCHES_PCT[self.notch] / 100.0
            out = sum(o["risk"] for o in self.open.values()) * SLIP_MARGIN
            room = min(allow - max(0.0, -self.week_pnl) - out, allow * ALLOW_DAY_SHARE - max(0.0, -self.day_pnl) - out)
            fit = math.floor(room / SLIP_MARGIN / sd / MU) * MU
            if fit < MU:
                self.blocked["allowance used up"] += 1
                return
            if fit < units:
                units = fit
                self.blocked["sized down: allowance"] += 1
        actual = units * sd
        self.open[id(t)] = {"risk": actual, "extra": max(0.0, min(actual, funded) - base), "rung": rung, "tag": tag,
                            "units": units}
        self.rung_trades[lane][rung] += 1

    def _exit(self, t):
        lane, r = t["lane"], self._r(t)
        o = self.open.pop(id(t), None)
        if o is not None:
            pnl = r * o["risk"]
            if self.fee and t.get("entry"):
                # MINIMUM COMMISSION: r already carries the percentage commission (inside cost_bp). When the
                # position is so small that the percentage comes to less than the minimum, the broker charges
                # the minimum instead: the difference is taken off here, in dollars, on each side.
                pct, mn, sides = self.fee
                top_up = sides * max(0.0, mn - pct / 100.0 * t["entry"] * self.qf(t["entry"]) * o["units"])
                if top_up > 0:
                    pnl -= top_up
                    self.fee_paid += top_up
                    self.fee_n += 1
            self.E += pnl
            self.week_pnl += pnl
            self.day_pnl += pnl
            self.lane_pnl[lane] += pnl
            self.lane_n[lane] += 1
            if o.get("tag"):
                x_ = self.extras.setdefault(o["tag"], [0, 0.0])
                x_[0] += 1
                x_[1] += pnl
            self.peak = max(self.peak, self.E)
            self.max_dd = max(self.max_dd, (self.peak - self.E) / self.peak * 100.0)
            self.live[lane].append(r)
            if self.mode == "house" and sum(self.live[lane][-RECENT_N:]) <= RECENT_DROP_R and self.rung[lane] > 1:
                self.rung[lane] = max(1, self.rung[lane] - 2)       # QUICK DOWN on live results (not below rung 1)
                self.since[lane] = 0
                self.live[lane] = []
                self.moves["down"] += 1
        if t["zone"]:
            self.rec[lane].append(r)
            self.since[lane] += 1
            if self.mode == "house":
                self._review(lane)
        self._after(t, r, o)

    def run(self):
        ev = sorted([(t["t_out"], 0, i) for i, t in enumerate(self.trades)] +
                    [(t["t_in"], 1, i) for i, t in enumerate(self.trades)])
        di = 0
        for ts, kind, i in ev:
            day = time.strftime("%Y-%m-%d", time.gmtime(ts))
            while di < len(self.weekdays) and self.weekdays[di] <= day:
                self._roll(self.weekdays[di])
                di += 1
            if kind == 1:
                self._entry(self.trades[i])
            else:
                self._exit(self.trades[i])
        return self


def zone_check(rep, trades):
    """Plain R per trade at equal size, in the zone against out of it: no ladder, allowance or cushion.
    The control lane (random direction, random time) is put through each zone rule too: if random trades
    also do well inside a zone, the zone is doing the work, not the lane's idea."""
    rep.p("")
    rep.p("  ZONE CHECK  (R per trade, net of costs, every trade the same size; +/- is one standard error)")
    rep.p("    %-8s %-11s %-3s %-26s %-26s %s" % ("lane", "zone", "", "in the zone", "out of the zone", "in minus out"))
    kinds = []
    for lane in sorted(ZONES):
        if ZONES[lane] not in kinds:
            kinds.append(ZONES[lane])
    todo = [(lane, ZONES[lane], lane) for lane in sorted(ZONES)] + [("control", z, "control") for z in kinds]
    for label, z, lane in todo:
        for p in ("A", "B"):
            tr = [t for t in trades if t["lane"] == lane and t["period"] == p and t["r"] is not None]
            zs = [(in_zone(t, z), t["r"]) for t in tr]
            a = [r_ for f_, r_ in zs if f_ is True]
            b = [r_ for f_, r_ in zs if f_ is False]
            if len(a) >= 2 and len(b) >= 2:
                d_, s_ = mean(a) - mean(b), math.sqrt(se(a) ** 2 + se(b) ** 2)
                diff = "%+.3f (z %+.1f)" % (d_, d_ / s_ if s_ else 0.0)
            else:
                diff = "-"
            rep.p("    %-8s %-11s %-3s %-26s %-26s %s" % (label if p == "A" else "", z if p == "A" else "", p, _ms(a), _ms(b), diff))
    rep.p("    Read it as: a zone HOLDS where 'in the zone' is above zero and above 'out of the zone' in BOTH periods,")
    rep.p("    and the lane's row beats the control row for the same zone. One good period is a lucky run until")
    rep.p("    the other agrees.")


def run_house():
    rep = Report("house")
    t0 = time.time()
    folder = _house_folder()
    rep.p("=" * 78)
    rep.p("THE HOUSE  --  earners, zones, ladder, allowance, cushion: replayed in shadow")
    rep.p("=" * 78)
    rep.p("trades from: %s" % folder)
    rep.p("Each training period is replayed on its own from $%.0f. Nothing here trades or changes the bot." % HOUSE_START)
    rep.p("")
    rep.p("zones: " + "; ".join("%s=%s" % kv for kv in sorted(ZONES.items())))
    rep.p("ladder: rungs risk %s%% of the floor | allowance notches %s%% of the floor per week | cushion share %.0f%%" % (
        "/".join("%g" % x for x in RUNG_RISK_PCT[1:]), "/".join("%g" % x for x in ALLOW_NOTCHES_PCT), 100 * CUSHION_SHARE))
    for symbol in HOUSE_SYMBOLS:
        if not os.path.exists(os.path.join(folder, "trades_%s.csv" % symbol)):
            rep.p("")
            rep.p("%s: no trades file in that collect folder, skipped." % symbol)
            continue
        trades, days = _house_inputs(folder, symbol)
        rep.p("")
        rep.p("=" * 78)
        rep.p("%s" % symbol)
        rep.p("=" * 78)
        if symbol == HOUSE_SYMBOL:
            rep.p("NOTE: the zones were found on this same data, so these results flatter them. The twins are a fair")
            rep.p("test of the house mechanics only (they get the same zones, ladder, allowance and cushion).")
        else:
            rep.p("INDEPENDENT CHECK: the zones and every threshold in them were found on %s and are used here" % HOUSE_SYMBOL)
            rep.p("unchanged. Nothing was chosen on this market, so a zone that holds here did not get there by")
            rep.p("being fitted. A zone that fails here needs a %s-specific reason in words, or it was luck." % HOUSE_SYMBOL)
            rep.p("('asia_rel' here is the overnight box against an average day. Smallest position: %g units, as the broker sets it.)" % dict((x["name"], x) for x in COLLECT_SYMBOLS).get(symbol, {}).get("min_unit", HOUSE_MIN_UNIT))
            rep.p("The ZONE CHECK below is in R and does not include the broker's minimum commission; the money figures do.")
        zone_check(rep, trades)
        _house_symbol(rep, symbol, trades, days)
    rep.p("")
    rep.p("not in this version: adding to a winning trade (needs the price path, so it belongs in 'collect').")
    rep.p("runtime %.1fs" % (time.time() - t0))
    rep.save()


def _house_symbol(rep, symbol, trades, days):
    spec = dict((x["name"], x) for x in COLLECT_SYMBOLS).get(symbol, {})
    fee = (spec["comm_pct"], spec["comm_min"], spec.get("comm_sides", 2)) if spec.get("comm_min") else None
    for p, name in (("A", "PERIOD A (before %s)" % SEAL_START), ("B", "PERIOD B (from %s)" % SEAL_END)):
        tr = [t for t in trades if t["period"] == p]
        tdays = set(t["day"] for t in tr)
        # the house calendar = trading days: a weekday a hole took out, or whose reads were built across one, is not
        # counted, so the weekly allowance, the floor clock and 'weekdays under water' measure time the house could
        # actually trade (a day with a kept trade always counts)
        def usable(x):
            return str(x.get("clean", "1")) != "0" and str(x.get("reads_ok", "1")) != "0"
        wd = [x["day"] for x in days if x["period"] == p and (usable(x) or x["day"] in tdays)]
        n_cut = sum(1 for x in days if x["period"] == p and not usable(x) and x["day"] not in tdays)
        if not tr:
            continue
        h = House(tr, wd, "house", fee=fee, spec=spec).run()
        zm = House(tr, wd, "zones_min", fee=fee, spec=spec).run()
        am = House(tr, wd, "all_min", fee=fee, spec=spec).run()
        rng = random.Random(4242)
        twins = []
        for _ in range(HOUSE_TWINS):
            flip = dict((id(t), 1 if rng.random() < 0.5 else -1) for t in tr)
            twins.append(House(tr, wd, "house", flip, fee=fee, spec=spec).run().E)
        twins.sort()
        beat = sum(1 for x in twins if h.E > x)
        rep.p("")
        rep.p("#" * 78)
        rep.p("%s  %s" % (symbol, name))
        rep.p("#" * 78)
        rep.p("  calendar: %d trading days on the house clock; %d weekdays not counted (a hole, or a hole in the %d days before)" % (len(wd), n_cut, WARM_DAYS))
        rep.p("  %-44s %12s %10s %8s" % ("", "end equity", "worst drop", "trades"))
        for lab, x in (("THE HOUSE (zones + ladder + allowance + cushion)", h), ("zones only, everything at minimum size", zm),
                       ("every lane out at minimum size (no zones)", am)):
            rep.p("  %-44s %12.0f %9.1f%% %8d" % (lab[:44], x.E, x.max_dd, sum(x.lane_n.values())))
        rep.p("  random twins (same house, coin-flip direction): middle %.0f, range %.0f to %.0f" % (
            twins[len(twins) // 2], twins[0], twins[-1]))
        rep.p("  -> the house finished above %d of %d twins" % (beat, HOUSE_TWINS))
        rep.p("  floor ended at %.0f (moved up %d times) | longest stretch below the previous high: %d weekdays" % (
            h.F, h.moves["floor"], h.longest_under))
        if fee:
            n_all = max(1, sum(h.lane_n.values()))
            base_ = HOUSE_START * RUNG_RISK_PCT[1] / 100.0
            rep.p("  MINIMUM COMMISSION ($%.2f a side, %d sides): the house paid $%.0f above the percentage rate, on %d of" % (
                fee[1], fee[2], h.fee_paid, h.fee_n))
            rep.p("    its %d trades. That is $%.2f a trade, or %.2fR of a minimum-size trade ($%.0f at risk), on top of the" % (
                n_all, h.fee_paid / n_all, h.fee_paid / n_all / base_, base_))
            rep.p("    costs already in every R figure. Without it the house would have ended at %.0f. The minimum stops" % (h.E + h.fee_paid))
            last_px = [t["entry"] for t in tr if t.get("entry")][-1]
            rep.p("    applying at $%.0f of volume: about %.0f contracts at this period's last price." % (
                fee[1] / (fee[0] / 100.0), math.ceil(fee[1] / (fee[0] / 100.0) / (last_px * _quote_to_usd(spec)(last_px)))))
        rep.p("  recovery sizing: %d trades, %+.0f | cheques cashed: %d trades, %+.0f   (money those trades made, whole trade)" % (
            h.extras["recovery"][0], h.extras["recovery"][1], h.extras["cheque"][0], h.extras["cheque"][1]))
        zr = [t["r"] for t in tr if t["zone"]]
        if len(zr) > 30 and mean(zr) > 0:
            mu, sd_ = mean(zr), se(zr) * math.sqrt(len(zr))
            pace = sum(h.lane_n.values()) / float(max(1, len(wd)))
            scale = (sd_ / mu) ** 2
            rep.p("  RECOVERY ARITHMETIC: in-zone trades average %+.3fR with a spread of %.2fR, and the house takes %.2f a weekday." % (mu, sd_, pace))
            rep.p("    A typical climb back to a previous high then takes about (spread/average)^2 = %.0f trades = %.0f weekdays." % (scale, scale / pace))
            rep.p("    Size does not change that number (it scales the wins and the losses alike). What does:")
            rep.p("    twice the trades -> %.0f weekdays | four times -> %.0f | 1.5x the average -> %.0f | twice the average -> %.0f" % (
                scale / pace / 2, scale / pace / 4, scale / 2.25 / pace, scale / 4 / pace))
        rep.p("")
        rep.p("  THE ALLOWANCE")
        worst = min(h.week_log, key=lambda w: w[1] / w[2]) if h.week_log else None
        rep.p("    weeks at each notch: " + ", ".join("%g%%: %d" % (ALLOW_NOTCHES_PCT[k], v) for k, v in sorted(h.notch_weeks.items())))
        rep.p("    notch moved up %d times, down %d times | ended at %g%%" % (
            h.moves["notch_up"], h.moves["notch_down"], ALLOW_NOTCHES_PCT[h.notch]))
        if worst:
            rep.p("    worst week %s: lost %.0f against an allowance of %.0f (%.0f%% of it)" % (
                worst[0], -worst[1], worst[2], -100.0 * worst[1] / worst[2]))
            over = sum(1 for w in h.week_log if -w[1] > w[2])
            rep.p("    weeks that lost more than their allowance: %d of %d (only slippage past the margin or gaps can do this)" % (
                over, len(h.week_log)))
        rep.p("")
        rep.p("  THE LADDER  (rung moves: %d up, %d down)" % (h.moves["up"], h.moves["down"]))
        rep.p("    %-8s %-11s %7s %9s   %s   %s" % ("lane", "zone", "taken", "money", "trades by rung 1/2/3/4", "in-zone record now (pessimistic .. average)"))
        for lane in sorted(ZONES, key=lambda l: -h.lane_pnl[l]):
            n, lb, opt = h._estimate(lane)
            est = ("n=%d  %+.3f .. %+.3f" % (n, lb, (lb + opt) / 2.0)) if lb is not None else ("n=%d" % n)
            rep.p("    %-8s %-11s %7d %+9.0f   %-22s   %s  (rung %d now)" % (
                lane, ZONES[lane], h.lane_n[lane], h.lane_pnl[lane], "/".join(str(x) for x in h.rung_trades[lane][1:]), est, h.rung[lane]))
        rep.p("")
        rep.p("  WHAT STAYED HOME, AND WHY  (signals, not money)")
        for k, v in sorted(h.blocked.items(), key=lambda kv: -kv[1]):
            rep.p("    %-26s %d" % (k, v))
        yrs = defaultdict(lambda: [None, None])
        for day, e, f in h.curve:
            y = day[:4]
            if yrs[y][0] is None:
                yrs[y][0] = e
            yrs[y][1] = e
        rep.p("")
        rep.p("  by year: " + "   ".join("%s %+.1f%%" % (y, (v[1] / v[0] - 1) * 100.0) for y, v in sorted(yrs.items())))
        import csv
        cname = "house_curve_%s.csv" % p if symbol == HOUSE_SYMBOL else "house_curve_%s_%s.csv" % (symbol, p)
        with open(os.path.join(rep.dir, cname), "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["day", "equity", "floor"])
            for row_ in h.curve:
                w.writerow([row_[0], "%.2f" % row_[1], "%.2f" % row_[2]])


def write_launcher():
    """(Re)write a double-click launcher next to this file: .bat on Windows, .sh elsewhere."""
    try:
        me = os.path.abspath(__file__)
        if os.name == "nt":
            path = os.path.join(SCRIPT_DIR, "run_asiabo_offline.bat")
            body = ('@echo off\r\ncd /d "%%~dp0"\r\n"%s" "%s" %%*\r\necho.\r\npause\r\n' % (sys.executable, me))
        else:
            path = os.path.join(SCRIPT_DIR, "run_asiabo_offline.sh")
            body = '#!/bin/sh\ncd "$(dirname "$0")"\n"%s" "%s" "$@"\n' % (sys.executable, me)
        old = None
        if os.path.exists(path):
            with open(path, "r", newline="") as f:
                old = f.read()
        if old != body:                 # never rewrite a launcher that may be the one running us
            with open(path, "w", newline="") as f:
                f.write(body)
            if os.name != "nt":
                os.chmod(path, 0o755)
        return path
    except Exception as e:
        print("(launcher not written: %s)" % e)
        return None


def main():
    launcher = write_launcher()
    args = sys.argv[1:]
    mode = "report"
    if args and args[0].lower() == "oldcollect":
        mode, args = "collect", [OLD_FROM, OLD_TO]
    elif args and args[0].lower() in ("study", "report", "collect", "house"):
        mode = args[0].lower()
        args = args[1:]
    elif not args:
        # no arguments (double-click / launcher): ask
        print("asiabo_offline   (root: %s)\n" % ROOT)
        print("  1  report   -- replay the main lane, flat vs Equity Pulse, adaptive TP shadow")
        print("  2  study    -- main lane only: direction test, drift, features")
        print("  3  collect  -- research data collection: every lane in shadow, signals, regimes, exits")
        print("  4  house    -- the earners design (zones, ladder, allowance, cushion) replayed on the last collect")
        print("  5  oldcollect -- the same collection on %s .. %s (old data check; writes reports/oldcollect_*)" % (OLD_FROM, OLD_TO))
        choice = input("\nchoose [1/2/3/4/5] (Enter = 3): ").strip()
        mode = {"1": "report", "2": "study", "4": "house"}.get(choice, "collect")
        if choice == "5":
            args = [OLD_FROM, OLD_TO]
        elif mode == "house":
            args = []
        elif mode == "collect":
            print("collect runs both training periods and skips the sealed years (%s .. %s) by itself." %
                  (SEAL_START, SEAL_END))
            args = []
        else:
            win = input("date window, e.g. 2024-01-01 2026-12-31 (Enter = %s onward): " % SEAL_END).strip()
            args = win.split() if win else [SEAL_END]
    start = epoch_of(args[0]) if len(args) >= 1 else (epoch_of(COLLECT_FROM) if mode == "collect" else 0.0)
    end = epoch_of(args[1]) if len(args) >= 2 else epoch_of("2100-01-01")
    if mode == "study":
        run_study(start, end)
    elif mode == "collect":
        run_collect(start, end)
    elif mode == "house":
        run_house()
    else:
        run(start, end)
    if launcher:
        print("launcher: %s  (double-click it next time)" % launcher)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        if sys.stdin and sys.stdin.isatty():
            input("\nerror above. Press Enter to close.")
