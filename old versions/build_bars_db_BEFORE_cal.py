#!/usr/bin/env python3
"""
Builds bars.db from BarExtract output.

    python build_bars_db.py                 # normal use
    run_build_bars_db.bat                   # same thing by double-click; the script
                                            # creates this file itself on its first run
    python build_bars_db.py a.txt b.txt     # one-off: only these files, nothing is moved

Normal use: drop new BarExtract files into bars_input/. Each run reads
everything in bars_origin/ plus anything new in bars_input/, rebuilds
bars.db, then moves the new files that loaded cleanly into bars_origin/
(the permanent origin history). Files with a problem (cut short, lines
lost, no bars) stay in bars_input/ so they get noticed -- fix or delete them.

Accepts the files BarExtract writes directly and also saved cTrader logs
(the "date | Info |" prefix is ignored), so the log fallback works too.
bars.db is rebuilt from scratch on every run -- bars_origin/ is the
source of truth, so never delete it. Overlapping runs are fine: duplicates are merged
(when two files disagree on a minute, the file read FIRST is kept; origin files are read
before new ones, each folder in name order).

Built to stay small in memory: bars go from each file straight into the database, so the
number of symbols and years no longer matters for RAM. The new bars.db is written beside
the old one and only replaces it once it is complete.

Besides bars.db, every run writes two files next to it:
  build_bars_db_log.txt   everything printed on screen (the "hard log")
  gaps_to_check.csv       the holes still worth explaining: every 'other' hole of
                          CHECK_MIN_MINUTES or more and every over-long weekend, MINUS the ones
                          a market holiday or a known market event already explains

Tables:
  bars_m1  one row per closed 1M bar: symbol, ts (epoch seconds, UTC, bar OPEN time),
           time_utc, open, high, low, close, volume, spread_avg, spread_max, ticks
  runs     one row per input file, with its META fields and whether it was complete
  gaps     every hole of 5+ missing minutes, labelled:
             weekend       a Saturday falls inside it and it is a normal length for this symbol
             weekend_long  a Saturday falls inside it but it is WEEKEND_EXTRA_MIN+ longer than
                           this symbol's usual weekend (a holiday beside the weekend, or lost data)
             daily_break   the symbol's own recurring pause: a hole starting in the same UTC hour
                           with about the same length on BREAK_MIN_NIGHTS+ nights within
                           BREAK_WINDOW_DAYS days of it. Learned from the data with a sliding
                           window (not per calendar year), so a winter schedule that straddles
                           New Year, or a 2-week clock-change mismatch, is still recognised
             other         everything else: holidays, early closes, quiet minutes, lost data
           plus a 'note' column: "holiday: ..." or "event: ..." when the calendar or the
           KNOWN_EVENTS list explains the hole, empty when nothing does
"""
import os
import sys
import csv
import shutil
import filecmp
import sqlite3
import datetime
import statistics
from pathlib import Path
from collections import defaultdict

HERE = Path(__file__).resolve().parent
IN_DIR = HERE / "bars_input"
ORIGIN_DIR = HERE / "bars_origin"
DB_PATH = HERE / "bars.db"
TMP_PATH = HERE / "bars.db.building"
LOG_PATH = HERE / "build_bars_db_log.txt"
CHECK_PATH = HERE / "gaps_to_check.csv"
GAP_MIN_MINUTES = 5
CHECK_MIN_MINUTES = 120        # 'other' holes this long or longer go into gaps_to_check.csv
WEEKEND_EXTRA_MIN = 180        # a weekend this much longer than the symbol's usual one is 'weekend_long'
BREAK_MIN_MINUTES = 20         # a nightly pause shorter than this is not treated as a daily break
BREAK_WINDOW_DAYS = 30        # ...and it must recur within this many days either side
BREAK_MIN_NIGHTS = 8           # ...on at least this many nights (itself included)
STUB_WEEKDAYS = 50             # a year with fewer weekdays than this is a partial stub: no break warnings
# Market events that close or halt trading and are not on the holiday calendar.
# (first UTC date, last UTC date, what happened). A hole touching these dates is tagged, not flagged.
KNOWN_EVENTS = [
    ("2015-06-30", "2015-07-01", "leap second"),
    ("2020-03-09", "2020-03-09", "US equity circuit breaker / limit-down"),
    ("2020-03-12", "2020-03-12", "US equity circuit breaker"),
    ("2020-03-16", "2020-03-16", "US equity circuit breaker / limit-down"),
    ("2020-03-18", "2020-03-18", "US equity circuit breaker"),
    ("2025-01-09", "2025-01-09", "NYSE closed: national day of mourning (Carter)"),
    ("2025-11-28", "2025-11-28", "CME Globex outage (data-centre cooling failure)"),
]
BATCH = 20000
DAYNAMES = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")

_LOG = []


def say(text=""):
    print(text)
    _LOG.append(text)


def ensure_launcher():
    """First run on Windows: write a double-click launcher next to this script."""
    bat = HERE / "run_build_bars_db.bat"
    if os.name != "nt" or bat.exists():
        return
    bat.write_text(
        "@echo off\r\n"
        'cd /d "%~dp0"\r\n'
        "\r\n"
        "echo Running {name} ...\r\n"
        '"{py}" "%~dp0{name}"\r\n'
        "\r\n"
        "echo.\r\n"
        "echo Done.\r\n"
        "pause\r\n".format(py=sys.executable, name=Path(__file__).name),
        newline="")
    say("created launcher: %s" % bat)


_MIDNIGHT = {}


def to_epoch(s):
    """'YYYY-MM-DD HH:MM:SS' (UTC) -> epoch seconds. Raises ValueError on anything else."""
    if len(s) != 19 or s[10] != " " or s[13] != ":" or s[16] != ":":
        raise ValueError(s)
    day = s[:10]
    base = _MIDNIGHT.get(day)
    if base is None:
        d = datetime.datetime.strptime(day, "%Y-%m-%d").replace(tzinfo=datetime.timezone.utc)
        base = _MIDNIGHT[day] = int(d.timestamp())
    hh, mm, ss = int(s[11:13]), int(s[14:16]), int(s[17:19])
    if not (0 <= hh < 24 and 0 <= mm < 60 and 0 <= ss < 60):
        raise ValueError(s)
    return base + hh * 3600 + mm * 60 + ss


def num(s):
    return float(s) if s != "" else None


def payload(line, tag):
    i = line.find(tag)
    return line[i:].strip() if i >= 0 else None


def kv(parts):
    return dict(p.split("=", 1) for p in parts if "=" in p)


def stage_file(cur, path):
    """Read one file into the 'stage' table (emptied first). Nothing is kept in memory but counters."""
    cur.execute("DELETE FROM stage")
    meta, end = {}, None
    n = bad = out_of_order = ticks = 0
    first = last = None
    last_ts = None
    batch = []
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            p = payload(line, "BAR|")
            if p:
                c = p.split("|")
                try:
                    ts = to_epoch(c[1])
                    o, h, l, cl = (float(x) for x in c[2:6])
                    row = (ts, c[1], o, h, l, cl, num(c[6]), num(c[7]), num(c[8]), int(c[9]))
                except (ValueError, IndexError):
                    bad += 1
                    continue
                if not (l > 0 and h >= max(o, cl) and l <= min(o, cl)):
                    bad += 1
                    continue
                if last_ts is not None and ts <= last_ts:
                    out_of_order += 1
                last_ts = ts
                if first is None:
                    first = c[1]
                last = c[1]
                n += 1
                ticks += row[9]
                batch.append(row)
                if len(batch) >= BATCH:
                    cur.executemany("INSERT INTO stage VALUES (?,?,?,?,?,?,?,?,?,?)", batch)
                    batch = []
                continue
            p = payload(line, "META|")
            if p:
                meta = kv(p.split("|")[1:])
                continue
            p = payload(line, "END|")
            if p:
                end = kv(p.split("|")[1:])
    if batch:
        cur.executemany("INSERT INTO stage VALUES (?,?,?,?,?,?,?,?,?,?)", batch)
    return meta, end, n, bad, out_of_order, ticks, first, last


def spans_saturday(ts_a, ts_b):
    """True when a Saturday (UTC date) lies between the bar before the hole and the bar after it."""
    d, end = ts_a // 86400, ts_b // 86400
    while d <= end:
        if (d + 3) % 7 == 5:
            return True
        d += 1
    return False


def _nth_weekday(year, month, weekday, n):
    """n-th (0-based; -1 = last) given weekday (Mon=0) of a month."""
    days = [datetime.date(year, month, d) for d in range(1, 32)
            if _valid(year, month, d) and datetime.date(year, month, d).weekday() == weekday]
    return days[n]


def _valid(y, m, d):
    try:
        datetime.date(y, m, d)
        return True
    except ValueError:
        return False


def _easter(year):
    """Gregorian Easter Sunday (anonymous algorithm)."""
    a, b, c = year % 19, year // 100, year % 100
    d, e = b // 4, b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = c // 4, c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = (h + l - 7 * m + 114) % 31 + 1
    return datetime.date(year, month, day)


_HOLIDAYS = {}


def holidays_of(year):
    """US + UK market holidays and the usual early-close days of one year: {date: name}."""
    if year in _HOLIDAYS:
        return _HOLIDAYS[year]
    D, one = datetime.date, datetime.timedelta(days=1)
    easter = _easter(year)
    thanksgiving = _nth_weekday(year, 11, 3, 3)
    hol = {
        D(year, 1, 1): "New Year", _nth_weekday(year, 1, 0, 2): "MLK day",
        _nth_weekday(year, 2, 0, 2): "Presidents day", easter - 2 * one: "Good Friday",
        easter + one: "Easter Monday", _nth_weekday(year, 5, 0, 0): "UK May bank holiday",
        _nth_weekday(year, 5, 0, -1): "Memorial / UK spring bank holiday",
        D(year, 7, 3): "July 3 early close", D(year, 7, 4): "Independence day",
        _nth_weekday(year, 8, 0, -1): "UK summer bank holiday", _nth_weekday(year, 9, 0, 0): "Labor day",
        thanksgiving: "Thanksgiving", thanksgiving + one: "Black Friday early close",
        D(year, 12, 24): "Christmas Eve", D(year, 12, 25): "Christmas", D(year, 12, 26): "Boxing day",
        D(year, 12, 31): "New Year's Eve",
    }
    if year >= 2022:
        hol[D(year, 6, 19)] = "Juneteenth"
    # a fixed-date holiday on a weekend is observed on the Friday before / Monday after
    for day, name in list(hol.items()):
        if name in ("New Year", "Independence day", "Christmas", "Boxing day", "Juneteenth"):
            if day.weekday() == 5:
                hol.setdefault(day - one, name + " (observed)")
            elif day.weekday() == 6:
                hol.setdefault(day + one, name + " (observed)")
    _HOLIDAYS[year] = hol
    return hol


def _events_by_day():
    out = {}
    for a, b, what in KNOWN_EVENTS:
        d = datetime.date.fromisoformat(a)
        while d <= datetime.date.fromisoformat(b):
            out[d] = what
            d += datetime.timedelta(days=1)
    return out


_EVENT_DAYS = _events_by_day()


def explain_hole(ts_a, ts_b):
    """'event: ...' / 'holiday: ...' when the calendar explains the hole, else ''.
    A holiday only explains a hole when every weekday the hole swallows WHOLE is itself a holiday,
    so a holiday sitting inside a two-week outage does not hide the outage."""
    a = datetime.datetime.fromtimestamp(ts_a, datetime.timezone.utc).date()
    b = datetime.datetime.fromtimestamp(ts_b, datetime.timezone.utc).date()
    one = datetime.timedelta(days=1)
    d, names, events = a, [], []
    while d <= b:
        if d in _EVENT_DAYS:
            events.append(_EVENT_DAYS[d])
        name = holidays_of(d.year).get(d)
        if name:
            names.append(name)
        elif a < d < b and d.weekday() < 5:
            names = None                    # a normal weekday lost completely: not a holiday hole
            break
        d += one
    if events:
        return "event: " + ", ".join(dict.fromkeys(events))
    if names:
        return "holiday: " + ", ".join(dict.fromkeys(names))
    return ""


def scan_symbol(con, symbol):
    """One ordered pass over a symbol's bars: finds the holes, the hours that have data, the weekdays."""
    holes = []                          # [ts_a, time_a, ts_b, time_b, missing, kind]
    small = 0
    days_in_year = defaultdict(int)     # year -> weekdays that have any bar
    hour_days = defaultdict(int)        # (year, hour) -> weekdays that have a bar in that hour
    prev_ts = prev_t = None
    prev_hour_key = prev_day = None
    for ts, t in con.execute("SELECT ts, time_utc FROM bars_m1 WHERE symbol=? ORDER BY ts", (symbol,)):
        day = ts // 86400
        if (day + 3) % 7 < 5:
            hour_key = ts // 3600
            if hour_key != prev_hour_key:
                prev_hour_key = hour_key
                hour_days[(t[:4], hour_key % 24)] += 1
                if day != prev_day:
                    prev_day = day
                    days_in_year[t[:4]] += 1
        if prev_ts is not None and ts - prev_ts > 60:
            missing = (ts - prev_ts) // 60 - 1
            if missing >= GAP_MIN_MINUTES:
                holes.append([prev_ts, prev_t, ts, t, missing, None])
            else:
                small += 1
        prev_ts, prev_t = ts, t
    return holes, small, days_in_year, hour_days


def _start_minute(h):
    """Minute of the UTC day of the first missing minute."""
    return ((h[0] + 60) % 86400) // 60


def label_holes(holes):
    """Fills in each hole's kind. Returns the usual weekend length."""
    weekend = [h for h in holes if spans_saturday(h[0], h[2])]
    usual_weekend = statistics.median(h[4] for h in weekend) if weekend else None
    for h in weekend:
        h[5] = "weekend_long" if h[4] > usual_weekend + WEEKEND_EXTRA_MIN else "weekend"
    # recurring pause: same UTC start hour, about the same length, on many nights close in time.
    # A sliding window instead of a calendar year, so schedules that change with the seasons
    # (and winters that run across New Year) are still seen as one pattern.
    groups = defaultdict(list)          # (start hour, length to the nearest 30 min) -> holes, in time order
    for h in holes:
        if h[5] is None and h[4] >= BREAK_MIN_MINUTES:
            groups[(_start_minute(h) // 60, int(round(h[4] / 30.0)))].append(h)
    confirmed = defaultdict(list)       # day -> [(start minute, minutes)]
    for hs in groups.values():
        days = [h[0] // 86400 for h in hs]
        lo = hi = 0
        for i in range(len(hs)):
            while days[i] - days[lo] > BREAK_WINDOW_DAYS:
                lo += 1
            hi = max(hi, i)
            while hi + 1 < len(hs) and days[hi + 1] - days[i] <= BREAK_WINDOW_DAYS:
                hi += 1
            if hi - lo + 1 >= BREAK_MIN_NIGHTS:
                hs[i][5] = "daily_break"
                confirmed[days[i]].append((_start_minute(hs[i]), hs[i][4]))
    # a pause that began a few minutes early or late (a quiet last minute) is still the daily break
    for h in holes:
        if h[5] is None and h[4] >= BREAK_MIN_MINUTES:
            day, start_min = h[0] // 86400, _start_minute(h)
            for d in range(day - BREAK_WINDOW_DAYS, day + BREAK_WINDOW_DAYS + 1):
                hit = False
                for s_min, minutes in confirmed.get(d, ()):
                    off = abs(start_min - s_min)
                    if min(off, 1440 - off) <= 30 and abs(h[4] - minutes) <= max(30, 0.2 * minutes):
                        hit = True
                        break
                if hit:
                    h[5] = "daily_break"
                    break
    for h in holes:
        if h[5] is None:
            h[5] = "other"
        h.append(explain_hole(h[0], h[2]) if h[5] in ("other", "weekend_long") else "")
    return usual_weekend


def break_summary(holes, days_in_year):
    """year -> [(start hour, typical minutes, nights)] for the recurring pauses, and minutes shut per weekday."""
    per = defaultdict(list)
    for h in holes:
        if h[5] == "daily_break":
            per[(h[1][:4], _start_minute(h) // 60, int(round(h[4] / 30.0)))].append(h[4])
    breaks, shut = defaultdict(list), defaultdict(float)
    for (year, hour, _), lens in per.items():
        shut[year] += sum(lens)
        if len(lens) >= BREAK_MIN_NIGHTS:
            breaks[year].append((hour, int(statistics.median(lens)), len(lens)))
    for year in shut:
        shut[year] /= max(1, days_in_year.get(year, 0))
    return breaks, shut


def coverage_row(year, days_in_year, hour_days):
    """24 characters, one per UTC hour: how many of the year's weekdays have a bar in that hour."""
    out = []
    n = max(1, days_in_year.get(year, 0))
    for hour in range(24):
        share = hour_days.get((year, hour), 0) / n
        out.append("#" if share >= 0.9 else "+" if share >= 0.5 else "." if share >= 0.1 else " ")
    return "".join(out)


def report_symbol(con, symbol):
    cur = con.cursor()
    n_bars, first, last = cur.execute(
        "SELECT COUNT(*), MIN(time_utc), MAX(time_utc) FROM bars_m1 WHERE symbol=?", (symbol,)).fetchone()
    holes, small, days_in_year, hour_days = scan_symbol(con, symbol)
    usual_weekend = label_holes(holes)
    breaks, shut = break_summary(holes, days_in_year)
    cur.executemany("INSERT INTO gaps VALUES (?,?,?,?,?,?)",
                    [(symbol, h[1], h[3], h[4], h[5], h[6]) for h in holes])
    pip = None
    for (p,) in cur.execute("SELECT pip_size FROM runs WHERE symbol=? AND pip_size IS NOT NULL", (symbol,)):
        try:
            pip = float(p)
            break
        except ValueError:
            pass

    say("\n=== %s: %d bars, %s -> %s ===" % (symbol, n_bars, first, last))
    brokers = [r[0] for r in cur.execute("SELECT DISTINCT broker FROM runs WHERE symbol=?", (symbol,))]
    if len(brokers) > 1:
        say("!! this symbol comes from %d different brokers (%s): prices and hours may not match"
            % (len(brokers), ", ".join(str(b) for b in brokers)))
    say("year     bars  weekdays  %s   ticks/bar   hours with data, UTC 00..23"
        % ("spread pips" if pip else " avg_spread"))
    years = cur.execute("""SELECT substr(time_utc,1,4), COUNT(*), AVG(spread_avg), AVG(ticks)
                           FROM bars_m1 WHERE symbol=? GROUP BY 1 ORDER BY 1""", (symbol,)).fetchall()
    for y, n, sp, tk in years:
        if sp is None:
            sp_txt = "n/a"
        elif pip:
            sp_txt = "%.2f" % (sp / pip)
        else:
            sp_txt = "%.6g" % sp
        say("%s  %7d  %8d  %11s   %9.1f   |%s|" % (y, n, days_in_year.get(y, 0), sp_txt, tk,
                                                    coverage_row(y, days_in_year, hour_days)))
    say("         (# = data on 90%+ of that year's weekdays in that hour, + = 50%+, . = 10%+, blank = under 10%)")

    # the nightly pause, year by year: a change from one year to another is the thing to look at
    full_years = [y for y, _, _, _ in years if days_in_year.get(y, 0) >= STUB_WEEKDAYS]
    for y, _, _, _ in years:
        if y not in full_years:
            say("usual daily break %s: (partial year, %d weekdays -- skipped)" % (y, days_in_year.get(y, 0)))
            continue
        bs = sorted(breaks.get(y, []))
        desc = "; ".join("from %02d:00 for about %d min (%d nights)" % b for b in bs) or "none found"
        say("usual daily break %s: %s" % (y, desc))
    if full_years:
        ref_year = full_years[-1]
        for y in full_years:
            if abs(shut[y] - shut[ref_year]) > 60:
                say("!! %s is shut about %d min a night, %s about %d: whole hours are missing in one of them. Look at"
                    % (y, shut[y], ref_year, shut[ref_year]))
                say("   the 'hours with data' rows above. This is either the broker's history or the extraction.")

    kinds = defaultdict(int)
    for h in holes:
        kinds[h[5]] += 1
    say("gaps: %d weekend (usual length %s min), %d weekend_long, %d daily break, %d other (5+ min), "
        "%d short (<5 min, not stored)" % (kinds["weekend"], "n/a" if usual_weekend is None else int(usual_weekend),
                                           kinds["weekend_long"], kinds["daily_break"], kinds["other"], small))
    flagged = [h for h in holes if h[5] == "weekend_long" or (h[5] == "other" and h[4] >= CHECK_MIN_MINUTES)]
    check = [h for h in flagged if not h[6]]
    n_hol = sum(1 for h in flagged if h[6].startswith("holiday"))
    n_evt = sum(1 for h in flagged if h[6].startswith("event"))
    say("long holes: %d -- %d explained by a holiday, %d by a known event, %d unexplained -> %s"
        % (len(flagged), n_hol, n_evt, len(check), CHECK_PATH.name))
    for h in [h for h in flagged if h[6].startswith("event")]:
        say("   %s -> %s   %d min   %s" % (h[1], h[3], h[4], h[6]))
    if check:
        say("unexplained, longest first (up to 15):")
    for h in sorted(check, key=lambda h: -h[4])[:15]:
        say("   %s -> %s   %d min missing   %s" % (h[1], h[3], h[4], h[5]))
    return [(symbol, h[1], DAYNAMES[(h[0] // 86400 + 3) % 7], h[3], DAYNAMES[(h[2] // 86400 + 3) % 7],
             h[4], round(h[4] / 60.0, 1), h[5]) for h in check]


def main():
    ensure_launcher()
    folder_mode = len(sys.argv) == 1
    if folder_mode:
        IN_DIR.mkdir(exist_ok=True)
        ORIGIN_DIR.mkdir(exist_ok=True)
        files = (sorted(p for p in ORIGIN_DIR.glob("*") if p.is_file())
                 + sorted(p for p in IN_DIR.glob("*") if p.is_file()))
    else:
        files = [Path(a) for a in sys.argv[1:]]
    if not files:
        say("No input files. Put BarExtract output in %s" % IN_DIR)
        return
    to_archive = []

    if TMP_PATH.exists():
        TMP_PATH.unlink()
    con = sqlite3.connect(TMP_PATH)
    con.execute("PRAGMA journal_mode=OFF")
    con.execute("PRAGMA synchronous=OFF")
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

    problems, conflicts, n_runs, symbols = [], 0, 0, []
    for i, path in enumerate(files, 1):
        print("reading %d/%d  %s" % (i, len(files), path.name), flush=True)
        meta, end, n, bad, ooo, ticks, first, last = stage_file(cur, path)
        symbol = meta.get("symbol")
        if not n or not symbol:
            problems.append("%s: no META line or no bars -- skipped" % path.name)
            continue
        complete = end is not None and int(end.get("bars", -1)) == n + bad
        if end is None:
            problems.append("%s: no END line -- run was cut short or the file is truncated" % path.name)
        elif not complete:
            problems.append("%s: END says %s bars, file has %d -- lines were lost"
                            % (path.name, end.get("bars"), n + bad))
        if bad:
            problems.append("%s: %d malformed / impossible bars dropped" % (path.name, bad))
        if ooo:
            problems.append("%s: %d bars out of time order" % (path.name, ooo))
        if ticks / n < 5:
            problems.append("%s: %.1f ticks per bar on average -- this does not look like tick-data mode"
                            % (path.name, ticks / n))
        # first file wins: a minute already in bars_m1 is left alone
        cur.execute("INSERT OR IGNORE INTO bars_m1 SELECT ?, ts, time_utc, open, high, low, close, volume, "
                    "spread_avg, spread_max, ticks FROM stage ORDER BY rowid", (symbol,))
        differ = cur.execute("""SELECT COUNT(*) FROM stage s JOIN bars_m1 b ON b.symbol=? AND b.ts=s.ts
                                WHERE b.open<>s.open OR b.high<>s.high OR b.low<>s.low OR b.close<>s.close""",
                             (symbol,)).fetchone()[0]
        if differ:
            conflicts += differ
            problems.append("%s: %d bars disagree on price with a file read earlier (the earlier one was kept)"
                            % (path.name, differ))
        cur.execute("INSERT INTO runs VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                    (path.name, symbol, meta.get("broker"), meta.get("digits"), meta.get("pip_size"),
                     meta.get("tick_size"), meta.get("start"), meta.get("version"), n, first, last, int(complete)))
        n_runs += 1
        if symbol not in symbols:
            symbols.append(symbol)
        if folder_mode and path.parent == IN_DIR and complete and not ooo:
            to_archive.append(path)
    if conflicts:
        problems.append("%d bars in total appear in two files with different prices (first file kept)" % conflicts)
    cur.execute("DROP TABLE stage")
    con.commit()

    check_rows = []
    for symbol in symbols:
        check_rows += report_symbol(con, symbol)
    con.commit()
    con.close()

    # Only now swap the finished database in; the old one stayed usable until this moment.
    try:
        os.replace(TMP_PATH, DB_PATH)
    except OSError as e:
        say("\nCOULD NOT REPLACE %s (%s). Is it open in another program? The new database is ready as %s:"
            % (DB_PATH.name, e, TMP_PATH.name))
        say("close whatever has bars.db open, delete bars.db and rename that file to bars.db. No input files were moved.")
        LOG_PATH.write_text("\n".join(_LOG) + "\n", encoding="utf-8")
        return

    with open(CHECK_PATH, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["symbol", "last_bar_before", "weekday", "first_bar_after", "weekday", "missing_minutes",
                    "missing_hours", "kind"])
        w.writerows(check_rows)

    # Only after bars.db is safely written: move the clean new files to the origin history.
    for path in to_archive:
        dest = ORIGIN_DIR / path.name
        if dest.exists():
            if filecmp.cmp(path, dest, shallow=False):
                path.unlink()                      # exact copy already archived
                continue
            dest = ORIGIN_DIR / ("%s__%s%s" % (path.stem, datetime.datetime.now().strftime("%Y%m%d_%H%M%S"), path.suffix))
        shutil.move(str(path), str(dest))
    if to_archive:
        say("\nmoved to %s: %s" % (ORIGIN_DIR.name, ", ".join(p.name for p in to_archive)))
    say("\nfiles read: %d   written: %s" % (n_runs, DB_PATH))
    say("unexplained holes: %d   written: %s" % (len(check_rows), CHECK_PATH))
    if problems:
        say("\nFILE PROBLEMS:")
        for p in problems:
            say("  - " + p)
    else:
        say("input files: no problems found (data holes are reported per symbol above)")
    LOG_PATH.write_text("\n".join(_LOG) + "\n", encoding="utf-8")
    print("\nthis log was saved as %s" % LOG_PATH)


if __name__ == "__main__":
    main()
