"""
asiabo_lab.py -- one cheap labelled run of every open idea, on top of asiabo_offline.py

    python asiabo_lab.py            everything below, one report folder (reports/lab_<date>/)
    python asiabo_lab.py labels     only part 1        (needs a 'collect' run)
    python asiabo_lab.py daily      only part 2        (reads bars.db)
    python asiabo_lab.py machine    only part 3        (needs a 'collect' run)
    python asiabo_lab.py persist    part 4: do the signals found on 2020-26 show up on 2014-2019?
                                    (needs 'python asiabo_offline.py oldcollect' first; not part of the default run)
    python asiabo_lab.py signals    part 5: chart reads (moving averages, higher time frame, candle shape, RSI, the
                                    lane's own recent trades ...) per lane: which change the outcome, when, and does it
                                    last. Needs collect, oldcollect and bars.db; not part of the default run.
    python asiabo_lab.py theory     part 6: each lane's own theory reads (volume, spread, levels, pullback depth, other
                                    markets, other lanes ...) judged per kind of market, with recent years trusted more.
                                    Same needs as 'signals'; not part of the default run.
    python asiabo_lab.py probe      part 7: the raw move after the moments the reads point at, and whether any plain
                                    stop-and-target structure pays there. Same needs; not part of the default run.
    python asiabo_lab.py final      parts 7 and 8 with REAL costs (the broker's commission + the recorded spread): the probe
                                    extended to holds of 16-48 trading hours with wide stops, and every lane re-priced.
    python asiabo_lab.py power      part 9 (2026-10-08 audit): A = every collect / oldcollect trade re-exited six ways;
                                    B = the rebuilt standard lanes (stop orders, daily-ATR stops, real sessions, daily
                                    trend lanes). Everything against a coin-flip direction with the same timing and costs.

It CHANGES NOTHING in collect or house: it reads the newest reports/collect_*/ folder and bars.db, and
writes its own folder. The sealed exam years are never read (asiabo_offline's own lock is used).

PART 1  LABELS     every kept trade of every market gets calendar and state labels (news day, before / after
                   the release, day before the Fed, turn of the month, weekday, regime, shock, volatility).
                   For each label: R per trade inside it against outside it, per family, both periods, all
                   markets. A label MATTERS only if it points the same way in both periods and on most markets.
PART 2  DAILY      three ideas from the literature, rules fixed before any result, on daily closes:
                   turn of the month, the day before the Fed (pre-FOMC drift), slow trend following.
                   Reported for 2014-17 (older check), 2018-19 (early check), 2020-21 (A) and 2024+ (B).
PART 3  MACHINE    the house replay with extra machinery, one piece at a time and all together:
                   news blackout, confidence gate, merit entry, recovery scouts, harvest; plus the
                   consistency tracker (how often a day / week / month / quarter ended up).
Everything is SHADOW: it measures, it decides nothing in the bot.
"""
import os, sys, math, time, datetime, sqlite3, calendar, traceback
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import asiabo_offline as A

mean, se = A.mean, A.se

# ---- US release dates (BLS / Federal Reserve calendars, checked Oct 2026) ----
# jobs report and CPI: 08:30 New York. FOMC statement: 14:00 New York.
NFP = set("""
    2014-01-10 2014-02-07 2014-03-07 2014-04-04 2014-05-02 2014-06-06 2014-07-03 2014-08-01 2014-09-05
    2014-10-03 2014-11-07 2014-12-05 2015-01-09 2015-02-06 2015-03-06 2015-04-03 2015-05-08 2015-06-05
    2015-07-02 2015-08-07 2015-09-04 2015-10-02 2015-11-06 2015-12-04 2016-01-08 2016-02-05 2016-03-04
    2016-04-01 2016-05-06 2016-06-03 2016-07-08 2016-08-05 2016-09-02 2016-10-07 2016-11-04 2016-12-02
    2017-01-06 2017-02-03 2017-03-10 2017-04-07 2017-05-05 2017-06-02 2017-07-07 2017-08-04 2017-09-01
    2017-10-06 2017-11-03 2017-12-08 2018-01-05 2018-02-02 2018-03-09 2018-04-06 2018-05-04 2018-06-01
    2018-07-06 2018-08-03 2018-09-07 2018-10-05 2018-11-02 2018-12-07 2019-01-04 2019-02-01 2019-03-08
    2019-04-05 2019-05-03 2019-06-07 2019-07-05 2019-08-02 2019-09-06 2019-10-04 2019-11-01 2019-12-06
    2020-01-10 2020-02-07 2020-03-06 2020-04-03 2020-05-08 2020-06-05 2020-07-02 2020-08-07 2020-09-04
    2020-10-02 2020-11-06 2020-12-04 2021-01-08 2021-02-05 2021-03-05 2021-04-02 2021-05-07 2021-06-04
    2021-07-02 2021-08-06 2021-09-03 2021-10-08 2021-11-05 2021-12-03 2022-01-07 2022-02-04 2022-03-04
    2022-04-01 2022-05-06 2022-06-03 2022-07-08 2022-08-05 2022-09-02 2022-10-07 2022-11-04 2022-12-02
    2023-01-06 2023-02-03 2023-03-10 2023-04-07 2023-05-05 2023-06-02 2023-07-07 2023-08-04 2023-09-01
    2023-10-06 2023-11-03 2023-12-08 2024-01-05 2024-02-02 2024-03-08 2024-04-05 2024-05-03 2024-06-07
    2024-07-05 2024-08-02 2024-09-06 2024-10-04 2024-11-01 2024-12-06 2025-01-10 2025-02-07 2025-03-07
    2025-04-04 2025-05-02 2025-06-06 2025-07-03 2025-08-01 2025-09-05 2025-11-20 2025-12-16 2026-01-09
    2026-02-11 2026-03-06 2026-04-03 2026-05-08 2026-06-05 2026-07-02 2026-08-07 2026-09-04 2026-10-02
    2026-11-06 2026-12-04
""".split())
CPI = set("""
    2014-01-16 2014-02-20 2014-03-18 2014-04-15 2014-05-15 2014-06-17 2014-07-22 2014-08-19 2014-09-17
    2014-10-22 2014-11-20 2014-12-17 2015-01-16 2015-02-26 2015-03-24 2015-04-17 2015-05-22 2015-06-18
    2015-07-17 2015-08-19 2015-09-16 2015-10-15 2015-11-17 2015-12-15 2016-01-20 2016-02-19 2016-03-16
    2016-04-14 2016-05-17 2016-06-16 2016-07-15 2016-08-16 2016-09-16 2016-10-18 2016-11-17 2016-12-15
    2017-01-18 2017-02-15 2017-03-15 2017-04-14 2017-05-12 2017-06-14 2017-07-14 2017-08-11 2017-09-14
    2017-10-13 2017-11-15 2017-12-13 2018-01-12 2018-02-14 2018-03-13 2018-04-11 2018-05-10 2018-06-12
    2018-07-12 2018-08-10 2018-09-13 2018-10-11 2018-11-14 2018-12-12 2019-01-11 2019-02-13 2019-03-12
    2019-04-10 2019-05-10 2019-06-12 2019-07-11 2019-08-13 2019-09-12 2019-10-10 2019-11-13 2019-12-11
    2020-01-14 2020-02-13 2020-03-11 2020-04-10 2020-05-12 2020-06-10 2020-07-14 2020-08-12 2020-09-11
    2020-10-13 2020-11-12 2020-12-10 2021-01-13 2021-02-10 2021-03-10 2021-04-13 2021-05-12 2021-06-10
    2021-07-13 2021-08-11 2021-09-14 2021-10-13 2021-11-10 2021-12-10 2022-01-12 2022-02-10 2022-03-10
    2022-04-12 2022-05-11 2022-06-10 2022-07-13 2022-08-10 2022-09-13 2022-10-13 2022-11-10 2022-12-13
    2023-01-12 2023-02-14 2023-03-14 2023-04-12 2023-05-10 2023-06-13 2023-07-12 2023-08-10 2023-09-13
    2023-10-12 2023-11-14 2023-12-12 2024-01-11 2024-02-13 2024-03-12 2024-04-10 2024-05-15 2024-06-12
    2024-07-11 2024-08-14 2024-09-11 2024-10-10 2024-11-13 2024-12-11 2025-01-15 2025-02-12 2025-03-12
    2025-04-10 2025-05-13 2025-06-11 2025-07-15 2025-08-12 2025-09-11 2025-10-24 2025-12-18 2026-01-13
    2026-02-13 2026-03-11 2026-04-10 2026-05-12 2026-06-10 2026-07-14 2026-08-12 2026-09-11 2026-10-14
    2026-11-10 2026-12-10
""".split())
FOMC = set("""
    2014-01-29 2014-03-19 2014-04-30 2014-06-18 2014-07-30 2014-09-17 2014-10-29 2014-12-17 2015-01-28
    2015-03-18 2015-04-29 2015-06-17 2015-07-29 2015-09-17 2015-10-28 2015-12-16 2016-01-27 2016-03-16
    2016-04-27 2016-06-15 2016-07-27 2016-09-21 2016-11-02 2016-12-14 2017-02-01 2017-03-15 2017-05-03
    2017-06-14 2017-07-26 2017-09-20 2017-11-01 2017-12-13 2018-01-31 2018-03-21 2018-05-02 2018-06-13
    2018-08-01 2018-09-26 2018-11-08 2018-12-19 2019-01-30 2019-03-20 2019-05-01 2019-06-19 2019-07-31
    2019-09-18 2019-10-30 2019-12-11 2020-01-29 2020-03-03 2020-03-15 2020-03-23 2020-04-29 2020-06-10
    2020-07-29 2020-09-16 2020-11-05 2020-12-16 2021-01-27 2021-03-17 2021-04-28 2021-06-16 2021-07-28
    2021-09-22 2021-11-03 2021-12-15 2022-01-26 2022-03-16 2022-05-04 2022-06-15 2022-07-27 2022-09-21
    2022-11-02 2022-12-14 2023-02-01 2023-03-22 2023-05-03 2023-06-14 2023-07-26 2023-09-20 2023-11-01
    2023-12-13 2024-01-31 2024-03-20 2024-05-01 2024-06-12 2024-07-31 2024-09-18 2024-11-07 2024-12-18
    2025-01-29 2025-03-19 2025-05-07 2025-06-18 2025-07-30 2025-09-17 2025-10-29 2025-12-10 2026-01-28
    2026-03-18 2026-04-29 2026-06-17 2026-07-29 2026-09-16 2026-10-28 2026-12-09
""".split())
FOMC_UNSCHEDULED = {"2020-03-03", "2020-03-15", "2020-03-23"}   # nobody could plan around these: tagged as Fed days,
                                                               # never used as 'day before the Fed' or for a blackout

SEGS = [("2014-17", "2014-01-01", "2018-01-01"), ("2018-19", "2018-01-01", "2020-01-01"),
        ("A 2020-21", "2020-01-01", "2022-01-01"), ("B 2024+", "2024-01-01", "2100-01-01")]
DAILY_FROM = "2014-01-01"       # 2013 is left out (agreed data roles)
WD = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")


def _date(s):
    return datetime.date(int(s[:4]), int(s[5:7]), int(s[8:10]))


def _shift_weekday(d, step):
    d += datetime.timedelta(days=step)
    while d.weekday() >= 5:
        d += datetime.timedelta(days=step)
    return d


def release_ts(day, kind):
    """UTC seconds of a release: jobs / CPI 08:30 New York, FOMC 14:00 New York (daylight saving followed)."""
    base = A.epoch_of(day)
    oh, om = A._ny_open_hm(base + 43200)            # 09:30 New York as a UTC hour and minute
    opening = base + oh * 3600 + om * 60
    return opening - 3600 if kind in ("nfp", "cpi") else opening + 4.5 * 3600


def _turn_of_month_days(y0=2013, y1=2027):
    """The classic window: the last weekday of a month and the first three weekdays of the next one."""
    out = set()
    for y in range(y0, y1 + 1):
        for m in range(1, 13):
            d = datetime.date(y, m, 1)
            while d.weekday() >= 5:
                d += datetime.timedelta(days=1)
            for _ in range(3):
                out.add(d.isoformat())
                d = _shift_weekday(d, 1)
            out.add(_shift_weekday(datetime.date(y, m, 1), -1).isoformat())
    return out


TOM = _turn_of_month_days()
FOMC_SCHED = FOMC - FOMC_UNSCHEDULED
PRE_FOMC = set(_shift_weekday(_date(d), -1).isoformat() for d in FOMC_SCHED)
NEWS_SCHED = {}
for _k, _S in (("nfp", NFP), ("cpi", CPI), ("fomc", FOMC_SCHED)):
    for _d in _S:
        NEWS_SCHED.setdefault(_d, []).append(_k)
POST_NEWS = set(_shift_weekday(_date(d), 1).isoformat() for d in NEWS_SCHED)
_REL_TS = {}


def first_release_ts(day):
    if day not in _REL_TS:
        _REL_TS[day] = min(release_ts(day, k) for k in NEWS_SCHED[day])
    return _REL_TS[day]


def _f(v):
    if v in ("", None):
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


CONF_SIGNALS = ("day_eff", "asia_rel", "open_move_with", "volrank", "prev_range_rel", "er60", "ret60_with",
                "trend20_with", "trend5_with", "er5", "er20", "vol3rel", "room_r", "stretch_atr", "cost_r",
                "setup_range_rel", "stop_atr", "bar_extreme", "day_used")


def load_market(folder, symbol):
    trades, days = A._house_inputs(folder, symbol)
    for t in trades:
        for k in CONF_SIGNALS + ("shock", "xshock", "gap"):
            if not isinstance(t.get(k), float):
                t[k] = _f(t.get(k))
    return trades, days


def _symbols(folder):
    return [s for s in A.HOUSE_SYMBOLS if os.path.exists(os.path.join(folder, "trades_%s.csv" % s))]


# ======================================================================================================
# PART 1: LABELS
# ======================================================================================================
def trade_labels(t):
    d, L = t["day"], []
    if d in NFP:
        L.append("jobs_report_day")
    if d in CPI:
        L.append("cpi_day")
    if d in FOMC:
        L.append("fed_day")
    if d in NEWS_SCHED:
        L.append("news_day (any of the 3)")
        L.append("news: entered BEFORE release" if t["t_in"] < first_release_ts(d) else "news: entered AFTER release")
    if d in PRE_FOMC:
        L.append("day before the Fed")
    if d in POST_NEWS:
        L.append("day after a release")
    if d in TOM:
        L.append("turn of the month")
    L.append("weekday " + WD[_date(d).weekday()])
    reg = t.get("regime")
    if reg and reg != "unknown":
        L.append("regime " + reg)
    if t.get("shock"):
        L.append("day after a shock (own market)")
    if t.get("xshock"):
        L.append("day after a shock (other market)")
    if t.get("gap"):
        L.append("opened with a gap")
    if t.get("turning"):
        L.append("fast and slow trend disagree")
    vr = t.get("volrank")
    if vr is not None:
        L.append("volatility high (top 20%)" if vr > 0.8 else ("volatility low (lower half)" if vr <= 0.5 else "volatility middle"))
    return L


LABEL_GROUPS = ["all lanes", "breakout", "reversal", "momentum", "swing", "control"]
LABEL_MIN_N = 15


def _diff(a, b):
    """(mean a - mean b, z) or (None, None) when either side is too thin."""
    if len(a) < LABEL_MIN_N or len(b) < LABEL_MIN_N:
        return None, None
    d = mean(a) - mean(b)
    s = math.sqrt(se(a) ** 2 + se(b) ** 2)
    return d, (d / s if s > 0 else 0.0)


def run_labels(rep, folder):
    rep.p("")
    rep.p("=" * 100)
    rep.p("PART 1: LABELS   which days and states separate good trades from bad ones")
    rep.p("=" * 100)
    rep.p("trades from: %s" % folder)
    rep.p("Every kept trade of every lane and market, labelled by what was KNOWN when it was entered. For each label:")
    rep.p("average R of the trades inside it, minus the average of the same group's trades outside it.")
    rep.p("  A / B        the two training periods. A label only counts if both point the same way.")
    rep.p("  in R (n)     average R per trade inside the label, pooled over all markets, and how many trades")
    rep.p("  diff (z)     inside minus outside, and how many standard errors that is")
    rep.p("  mk+          on how many of the markets (with enough trades) inside was BETTER than outside")
    rep.p("  control      the same diff for the random control lane: if random trades shift the same way, the")
    rep.p("               label is describing the day, not improving the lane's idea")
    rep.p("News dates: US jobs report, US CPI, FOMC. 'before / after' = entered before or after the release time.")
    rep.p("'turn of the month' = last weekday of a month and the first three of the next.")
    syms = _symbols(folder)
    data = defaultdict(list)            # (symbol, period, group, label or '*') -> [r]
    for s in syms:
        trades, _days = load_market(folder, s)
        for t in trades:
            fam = A.FAMILY.get(t["lane"], "other")
            groups = ["control"] if fam == "control" else ["all lanes", fam]
            labs = trade_labels(t)
            for g in groups:
                data[(s, t["period"], g, "*")].append(t["r"])
                for l in labs:
                    data[(s, t["period"], g, l)].append(t["r"])
    labels = sorted(set(k[3] for k in data if k[3] != "*"))
    cells, verdicts = [], []

    def pooled(p, g, l):
        ins, outs, plus, mk = [], [], 0, 0
        for s in syms:
            a = data.get((s, p, g, l), [])
            allr = data.get((s, p, g, "*"), [])
            if not allr:
                continue
            # outside = the group's trades not in the label (sum trick: keep it simple, rebuild by count)
            tot, n = sum(allr), len(allr)
            if len(a) >= LABEL_MIN_N and n - len(a) >= LABEL_MIN_N:
                mk += 1
                out_mean = (tot - sum(a)) / (n - len(a))
                plus += mean(a) > out_mean
        return plus, mk

    outside = {}                        # (symbol, period, group, label) -> [r outside]
    for s in syms:
        trades, _days = load_market(folder, s)
        for t in trades:
            fam = A.FAMILY.get(t["lane"], "other")
            groups = ["control"] if fam == "control" else ["all lanes", fam]
            labs = set(trade_labels(t))
            for g in groups:
                for l in labels:
                    if l not in labs:
                        outside.setdefault((s, t["period"], g, l), []).append(t["r"])
    for s in syms:
        for p in ("A", "B"):
            for g in LABEL_GROUPS:
                for l in labels:
                    a, b = data.get((s, p, g, l), []), outside.get((s, p, g, l), [])
                    d, z = _diff(a, b)
                    cells.append({"symbol": s, "period": p, "group": g, "label": l, "n_in": len(a), "n_out": len(b),
                                  "r_in": mean(a) if a else None, "r_out": mean(b) if b else None, "diff": d, "z": z})
    A._write_csv(os.path.join(rep.dir, "labels_cells.csv"), cells)
    tested = holds = leans = 0
    for g in LABEL_GROUPS[:-1]:
        rep.p("")
        rep.p("-" * 100)
        rep.p("%s   (pooled over %s)" % (g.upper(), ", ".join(syms)))
        rep.p("-" * 100)
        rep.p("  %-34s | %-31s | %-31s | %-13s | %s" % ("label", "A: in R (n)   diff (z)   mk+", "B: in R (n)   diff (z)   mk+",
                                                    "control A / B", "verdict"))
        for l in labels:
            parts, zs, ds = [], [], []
            for p in ("A", "B"):
                a = [r for s in syms for r in data.get((s, p, g, l), [])]
                b = [r for s in syms for r in outside.get((s, p, g, l), [])]
                d, z = _diff(a, b)
                plus, mk = pooled(p, g, l)
                if d is None:
                    parts.append("%-31s" % ("too few (n=%d)" % len(a)))
                else:
                    parts.append("%+.3f (%4d) %+.3f (%+.1f) %d/%d  " % (mean(a), len(a), d, z, plus, mk))
                zs.append(z)
                ds.append(d)
            cz = []
            for p in ("A", "B"):
                a = [r for s in syms for r in data.get((s, p, "control", l), [])]
                b = [r for s in syms for r in outside.get((s, p, "control", l), [])]
                d, z = _diff(a, b)
                cz.append("  -  " if d is None else "%+.2f" % d)
            verdict = ""
            if None not in zs:
                tested += 1
                same = (ds[0] > 0) == (ds[1] > 0)
                if same and min(abs(zs[0]), abs(zs[1])) >= 2.0:
                    holds += 1
                    verdict = "HOLDS: %s inside" % ("better" if ds[0] > 0 else "worse")
                    verdicts.append((g, l, ds, zs))
                elif same and min(abs(zs[0]), abs(zs[1])) >= 1.0:
                    leans += 1
                    verdict = "leans %s" % ("better" if ds[0] > 0 else "worse")
            rep.p("  %-34s | %-31s | %-31s | %-13s | %s" % (l[:34], parts[0][:31], parts[1][:31], " / ".join(cz), verdict))
    rep.p("")
    rep.p("READING IT: %d label-and-group pairs were tested. By luck alone about %.1f would 'hold' (2+ standard errors" % (tested, tested * 0.001))
    rep.p("the same way in both periods) and about %.0f would 'lean' (1+ both). Found: %d hold, %d lean." % (tested * 0.05, holds, leans))
    if verdicts:
        rep.p("The ones that hold:")
        for g, l, ds, zs in verdicts:
            rep.p("  %-10s %-34s A %+.3f (z %+.1f)  B %+.3f (z %+.1f)" % (g, l, ds[0], zs[0], ds[1], zs[1]))
        rep.p("A label that holds as 'worse inside' is a day to stay home on; 'better inside' is not an edge until the")
        rep.p("'in R' column itself is above zero. Check its control column before believing either.")
    else:
        rep.p("Nothing holds. No calendar or state label separates good trades from bad ones in both periods.")
    rep.p("every cell, per market: labels_cells.csv")


# ======================================================================================================
# PART 2: DAILY IDEAS
# ======================================================================================================
TREND_LOOKBACKS = (21, 63, 252)     # one, three and twelve months of trading days: the textbook horizons
TREND_TARGET_VOL = 0.10             # each market is sized to 10% a year of its own volatility ...
TREND_VOL_DAYS = 60                 # ... measured over the last 60 days ...
TREND_MAX_POS = 2.0                 # ... and never more than 2x its own notional
MAX_GAP_DAYS = 5                    # a jump across more calendar days than this is a hole, not a return


class Daily(object):
    """One market's daily closes (its own lane day), plus its price just before 14:00 New York each day."""

    def __init__(self, sym):
        self.sym = sym
        path = A.find_db()
        if not path:
            raise RuntimeError("bars.db not found under %s" % A.ROOT)
        con = sqlite3.connect(path)
        try:
            t, tcol, _oc, _hc, _lo, cc, sc, name_hit = A.detect_source(con, sym["match"])
        except RuntimeError:
            con.close()
            raise RuntimeError("no table for %s in bars.db" % sym["name"])
        q = 'select "%s","%s" from "%s"' % (tcol, cc, t)
        params = ()
        if sc and not name_hit:
            q += ' where upper(replace("%s"," ","")) in (%s)' % (sc, ",".join("?" * len(sym["match"])))
            params = tuple(m.upper() for m in sym["match"])
        q += ' order by "%s"' % tcol
        H = sym.get("hours", A.CLOCK_UTC)
        start = A.epoch_of(DAILY_FROM)
        s0, s1 = A.epoch_of(A.SEAL_START), A.epoch_of(A.SEAL_END)
        locked = not A.EXAM_UNLOCK
        dbshift = A.DB_UTC_OFFSET_HOURS * 3600.0
        to_epoch = A.to_epoch
        close, p14 = {}, {}
        last_ud, sh, nysh = None, 0.0, 0.0
        for raw, c in con.execute(q, params):
            try:
                ts = to_epoch(raw) - dbshift
                c = float(c)
            except (ValueError, TypeError):
                continue
            if ts < start or c <= 0 or (locked and s0 <= ts < s1):
                continue
            ud = int(ts // 86400)
            if ud != last_ud:
                last_ud = ud
                sh = A._clock_shift(H, ts)
                nysh = A._clock_shift(A.CLOCK_NY, ts) - A.NY_CLOCK_SHIFT * 3600.0
            close[int((ts + sh) // 86400)] = c
            nt = ts + nysh
            if 46800 <= nt % 86400 < 50400:             # 13:00-14:00 New York: the last bar before 14:00 wins
                p14[int(nt // 86400)] = c
        con.close()
        e0 = datetime.date(1970, 1, 1)
        self.days = [(e0 + datetime.timedelta(days=k), close[k]) for k in sorted(close) if (k + 3) % 7 < 5]
        self.p14 = [(e0 + datetime.timedelta(days=k), p14[k]) for k in sorted(p14) if (k + 3) % 7 < 5]
        if len(self.days) < 300:
            raise RuntimeError("only %d daily closes for %s" % (len(self.days), sym["name"]))

    def cost(self, price):
        return self.sym["cost_bp"] / 1e4 + self.sym.get("cost_px", 0.0) / price

    def swap(self, price, long_):
        return (self.sym["swap_long"] if long_ else self.sym["swap_short"]) / price     # per night, negative = paid


def _seg_of(d):
    s = d.isoformat()
    for name, a, b in SEGS:
        if a <= s < b:
            return name
    return None


def _nights(d):
    return 3 if d.weekday() == 2 else 1


def _stat(xs):
    if len(xs) < 2:
        return None
    m, s = mean(xs), se(xs)
    return m, (m / s if s > 0 else 0.0), len(xs)


def daily_turn_of_month(rep, mk, out):
    rep.p("")
    rep.p("-" * 100)
    rep.p("2a. TURN OF THE MONTH   (long over the last weekday of a month and the first three of the next)")
    rep.p("-" * 100)
    rep.p("  The claim (stock indices): most of a month's gain comes in these four days. US500 and GERMANY40 are the test;")
    rep.p("  the other markets are placebos (no reason to expect it there).")
    rep.p("  window / other = average daily return in basis points (1 bp = 0.01%) on window days and on all other days")
    rep.p("  net/month      = the four days' return minus one round trip and the swap for the nights held, in %")
    rep.p("  %-10s %-10s | %7s %7s %6s | %9s %6s %6s %7s" % ("market", "period", "window", "other", "t", "net/month", "t", "months", "up"))
    for name, D in mk.items():
        seg_win, seg_oth, months = defaultdict(list), defaultdict(list), defaultdict(lambda: defaultdict(float))
        for i in range(1, len(D.days)):
            (d0, c0), (d1, c1) = D.days[i - 1], D.days[i]
            if (d1 - d0).days > MAX_GAP_DAYS:
                continue
            seg = _seg_of(d1)
            if seg is None:
                continue
            r = c1 / c0 - 1.0
            if d1.isoformat() in TOM:
                seg_win[seg].append(r)
                key = (d1.year, d1.month) if d1.day <= 15 else ((d1.year + (d1.month == 12)), d1.month % 12 + 1)
                m = months[seg]
                first = key not in m
                m[key] += r + D.swap(c0, True) * _nights(d0) - (D.cost(c0) if first else 0.0)
            else:
                seg_oth[seg].append(r)
        for seg, _a, _b in SEGS:
            w, o, m = seg_win.get(seg, []), seg_oth.get(seg, []), list(months.get(seg, {}).values())
            if len(w) < 12 or len(o) < 30:
                continue
            d, z = _diff(w, o)
            st = _stat(m)
            rep.p("  %-10s %-10s | %+7.1f %+7.1f %+6.1f | %+8.2f%% %+6.1f %6d %6.0f%%" % (
                name, seg, 1e4 * mean(w), 1e4 * mean(o), z, 100 * st[0], st[1], st[2], 100.0 * sum(1 for x in m if x > 0) / len(m)))
            out.append({"idea": "turn_of_month", "market": name, "period": seg, "window_bp": 1e4 * mean(w), "other_bp": 1e4 * mean(o),
                        "t_diff": z, "net_month_pct": 100 * st[0], "t_net": st[1], "n": st[2]})
    rep.p("  Read: it is real where 'window' is clearly above 'other' (t of 2 or more) in SEVERAL periods on the indices and")
    rep.p("  not on the placebos, and net/month stays positive after costs.")


def daily_pre_fomc(rep, mk, out):
    rep.p("")
    rep.p("-" * 100)
    rep.p("2b. THE DAY BEFORE THE FED   (long from 14:00 New York the day before a scheduled FOMC statement to just before it)")
    rep.p("-" * 100)
    rep.p("  The claim (Lucca and Moench, US stocks): the index drifts up in the 24 hours before the statement.")
    rep.p("  Eight events a year, so every period here is a small sample: read the t column, not the average.")
    rep.p("  fed = average 24-hour return into the statement, other = the same 24-hour window on every other day (bp)")
    rep.p("  %-10s %-10s | %4s %7s %7s %6s | %8s %6s" % ("market", "period", "n", "fed", "other", "t", "net bp", "up"))
    for name, D in mk.items():
        fed, oth = defaultdict(list), defaultdict(list)
        for i in range(1, len(D.p14)):
            (d0, c0), (d1, c1) = D.p14[i - 1], D.p14[i]
            if (d1 - d0).days > 4:
                continue
            seg = _seg_of(d1)
            if seg is None:
                continue
            r = c1 / c0 - 1.0
            if d1.isoformat() in FOMC_SCHED:
                fed[seg].append((r, r - D.cost(c0) + D.swap(c0, True) * _nights(d0)))
            else:
                oth[seg].append(r)
        for seg, _a, _b in SEGS:
            f, o = fed.get(seg, []), oth.get(seg, [])
            if len(f) < 6 or len(o) < 30:
                continue
            g = [x[0] for x in f]
            d, z = _diff(g, o) if len(g) >= LABEL_MIN_N else (mean(g) - mean(o), (mean(g) - mean(o)) / math.sqrt(se(g) ** 2 + se(o) ** 2))
            net = [x[1] for x in f]
            rep.p("  %-10s %-10s | %4d %+7.1f %+7.1f %+6.1f | %+8.1f %5.0f%%" % (
                name, seg, len(g), 1e4 * mean(g), 1e4 * mean(o), z, 1e4 * mean(net), 100.0 * sum(1 for x in net if x > 0) / len(net)))
            out.append({"idea": "pre_fomc", "market": name, "period": seg, "window_bp": 1e4 * mean(g), "other_bp": 1e4 * mean(o),
                        "t_diff": z, "net_bp": 1e4 * mean(net), "n": len(g)})
    rep.p("  Read: the published effect was about +30 to +50 bp per event on US stocks before 2011 and has faded since.")
    rep.p("  If 'fed' is not clearly above 'other' on US500 in both A and B, it is not there to trade.")


def _trend_series(D, mode):
    """Daily P&L (fraction of the market's notional risk budget) for one market. mode = a lookback in days,
    'blend' (average of the three signals) or 'long' (always long, same sizing: the fair comparison)."""
    days = D.days
    n = len(days)
    rets, run0 = [0.0] * n, [0] * n
    for i in range(1, n):
        gap = (days[i][0] - days[i - 1][0]).days > MAX_GAP_DAYS
        run0[i] = i if gap else run0[i - 1]
        rets[i] = 0.0 if gap else days[i][1] / days[i - 1][1] - 1.0
    pos, prev, out, active = 0.0, 0.0, [], False
    for i in range(1, n):
        d, c = days[i]
        if run0[i] == i:
            pos, active = 0.0, False                    # a hole: flat until the next rebalance
        pnl = pos * rets[i]
        swap = abs(pos) * D.swap(days[i - 1][1], pos > 0) * _nights(days[i - 1][0]) if pos else 0.0
        if pos != prev:
            pnl -= abs(pos - prev) * D.cost(c) / 2.0   # one side of the round trip per unit changed
            prev = pos
        hist = i - run0[i]
        if active:
            out.append((d, pnl + swap, pnl))            # (day, net, before swap), from the first month a signal existed
        if d.month != days[i - 1][0].month and run0[i] != i:      # first trading day of a month: rebalance at its close
            if hist >= TREND_VOL_DAYS:
                xs = rets[i - TREND_VOL_DAYS + 1:i + 1]
                mu = mean(xs)
                vol = math.sqrt(sum((x - mu) ** 2 for x in xs) / (len(xs) - 1)) * math.sqrt(252.0)
                size = min(TREND_MAX_POS, TREND_TARGET_VOL / vol) if vol > 0 else 0.0
                if mode == "long":
                    sig = 1.0
                else:
                    looks = TREND_LOOKBACKS if mode == "blend" else (mode,)
                    sg = [(1.0 if c > days[i - L][1] else -1.0) for L in looks if hist >= L]
                    sig = mean(sg) if len(sg) == len(looks) else None
                active = sig is not None
                pos = (sig or 0.0) * size
            else:
                pos, active = 0.0, False
    return out


def _perf(xs):
    if len(xs) < 60:
        return None
    m, s = mean(xs), se(xs)
    sd = s * math.sqrt(len(xs))
    eq = peak = dd = 0.0
    for x in xs:
        eq += x
        peak = max(peak, eq)
        dd = max(dd, peak - eq)
    if sd <= 0:
        return None
    return {"ann": 252 * m, "vol": sd * math.sqrt(252.0), "sharpe": (m / sd * math.sqrt(252.0)) if sd > 0 else 0.0,
            "t": (m / s) if s > 0 else 0.0, "dd": dd, "n": len(xs)}


def daily_trend(rep, mk, out):
    rep.p("")
    rep.p("-" * 100)
    rep.p("2c. SLOW TREND   (time-series momentum: be long a market that is up over the lookback, short one that is down)")
    rep.p("-" * 100)
    rep.p("  Rules, textbook and fixed in advance: decide on the first trading day of each month; long if the close is above")
    rep.p("  the close %s trading days ago, else short; size each market to %.0f%% a year of its own volatility (last %d days," % (
        "/".join(str(x) for x in TREND_LOOKBACKS), 100 * TREND_TARGET_VOL, TREND_VOL_DAYS))
    rep.p("  never above %gx); hold to the next month. Costs: your spread + commission on every change of position, swap every night." % TREND_MAX_POS)
    rep.p("  'blend' averages the three lookbacks. 'always long' uses the same sizing and never goes short: trend following")
    rep.p("  has to beat THAT, because gold and stocks went up for most of these years.")
    rep.p("  Each cell: yearly return % / Sharpe ratio (return per unit of risk; 0.5 is good for one idea, above 1 is rare).")
    rep.p("  The sealed years are not read, so period B has to rebuild its lookback from January 2024: the 12-month signal")
    rep.p("  only starts trading in 2025.")
    rep.p("  WHAT HOLDING OVERNIGHT COSTS at this broker (swap from your symbol sheets, as % of the price per year):")
    for name, D in mk.items():
        px = D.days[-1][1]
        rep.p("    %-10s long %+6.1f%% a year | short %+6.1f%% a year" % (name, 100 * 365 * D.swap(px, True), 100 * 365 * D.swap(px, False)))
    rep.p("  Every cell below is AFTER that. The ALL MARKETS lines also show the result before swap, so you can see how much")
    rep.p("  of a bad number is the idea and how much is financing.")
    modes = [("12-month", 252), ("blend", "blend"), ("always long", "long"), ("3-month", 63), ("1-month", 21)]
    series = {}
    for label, mode in modes:
        for name, D in mk.items():
            series[(label, name)] = _trend_series(D, mode)
    for label, mode in modes:
        rep.p("")
        rep.p("  %-12s %-11s | %s" % (label.upper(), "market", " | ".join("%-15s" % s[0] for s in SEGS)))
        book = defaultdict(lambda: defaultdict(list))            # seg -> date -> [pnl]
        book0 = defaultdict(lambda: defaultdict(list))           # the same before swap
        for name in mk:
            cells = []
            by = defaultdict(list)
            for d, x, x0 in series[(label, name)]:
                seg = _seg_of(d)
                if seg:
                    by[seg].append(x)
                    book[seg][d].append(x)
                    book0[seg][d].append(x0)
            for seg, _a, _b in SEGS:
                pf = _perf(by.get(seg, []))
                cells.append("%-15s" % ("-" if pf is None else "%+5.1f%% / %+.2f" % (100 * pf["ann"], pf["sharpe"])))
                if pf:
                    out.append({"idea": "trend " + label, "market": name, "period": seg, "ann_pct": 100 * pf["ann"],
                                "vol_pct": 100 * pf["vol"], "sharpe": pf["sharpe"], "t": pf["t"], "max_dd_pct": 100 * pf["dd"], "n": pf["n"]})
            rep.p("  %-12s %-11s | %s" % ("", name, " | ".join(cells)))
        cells, extra = [], []
        for seg, _a, _b in SEGS:
            xs = [mean(v) for _d2, v in sorted(book[seg].items())]
            pf = _perf(xs)
            cells.append("%-15s" % ("-" if pf is None else "%+5.1f%% / %+.2f" % (100 * pf["ann"], pf["sharpe"])))
            if pf:
                p0 = _perf([mean(v) for _d2, v in sorted(book0[seg].items())])
                extra.append("%s: %+.2f%% a month, t %+.1f, worst drop %.1f%%, risk %.1f%% a year | before swap: %+.1f%% a year / %+.2f" % (
                    seg, 100 * pf["ann"] / 12.0, pf["t"], 100 * pf["dd"], 100 * pf["vol"], 100 * p0["ann"], p0["sharpe"]))
                out.append({"idea": "trend " + label, "market": "ALL (equal risk)", "period": seg, "ann_pct": 100 * pf["ann"],
                            "vol_pct": 100 * pf["vol"], "sharpe": pf["sharpe"], "t": pf["t"], "max_dd_pct": 100 * pf["dd"], "n": pf["n"]})
        rep.p("  %-12s %-11s | %s" % ("", "ALL MARKETS", " | ".join(cells)))
        if label in ("12-month", "blend", "always long"):
            for e in extra:
                rep.p("  %-12s   %s" % ("", e))
    rep.p("")
    rep.p("  Read: ALL MARKETS is the average of the markets that had a position that day (it runs at low risk; returns")
    rep.p("  scale with size). Trend following is worth keeping if its ALL MARKETS Sharpe is positive in most periods AND it")
    rep.p("  is not just 'always long' in disguise (compare the two tables, and look at its short side: EURUSD, USDJPY, WTI).")
    rep.p("  t = how sure the average is; below 2 in a 2-year period is normal even for a real edge, which is why the four")
    rep.p("  periods are shown side by side.")


def run_daily(rep):
    rep.p("")
    rep.p("=" * 100)
    rep.p("PART 2: DAILY IDEAS   three ideas from the literature, on daily closes from bars.db")
    rep.p("=" * 100)
    mk = {}
    for sym in A.COLLECT_SYMBOLS:
        try:
            print("reading daily closes: %s ..." % sym["name"])
            mk[sym["name"]] = Daily(sym)
        except RuntimeError as e:
            rep.p("%s: skipped (%s)" % (sym["name"], str(e).splitlines()[0]))
    if not mk:
        rep.p("no market could be read.")
        return
    rep.p("daily closes: " + "; ".join("%s %s..%s (%d days)" % (n, D.days[0][0], D.days[-1][0], len(D.days)) for n, D in mk.items()))
    rep.p("Periods: 2014-17 = older check (less weight), 2018-19 = early check, A and B = the training periods. %s..%s sealed." % (A.SEAL_START, A.SEAL_END))
    rep.p("A day's return is skipped when the closes are more than %d calendar days apart (a data hole)." % MAX_GAP_DAYS)
    out = []
    daily_turn_of_month(rep, mk, out)
    daily_pre_fomc(rep, mk, out)
    daily_trend(rep, mk, out)
    A._write_csv(os.path.join(rep.dir, "daily_results.csv"), out, first=("idea", "market", "period"))
    rep.p("every number above: daily_results.csv")


# ======================================================================================================
# PART 3: MACHINE
# ======================================================================================================
NEWS_AFTER_SECONDS = 3600       # blackout: no new trade on a release day until one hour after the release
CONF_MIN_TRADES = 80            # confidence: a lane needs this much history before any signal can be 'proven'
CONF_MIN_T = 2.5                # ... and a signal is proven when its correlation with the lane's results is this many
                                #     standard errors from zero, on the lane's OWN past trades only
CONF_REFRESH = 25               # proven signals are re-checked every this many new trades
CONF_DEFENSIVE_PCT = 1.0        # the gate only acts while the account is this far below its high (soft, not a ruler)
MERIT_MIN_TRADES, MERIT_Z = 100, 1.0   # merit: a lane's own record (all its trades) pessimistically above zero
RECSCOUT_DEPTH_PCT = 1.0        # recovery scouts: only while this far below the high ...
RECSCOUT_TOP, RECSCOUT_MIN_TRADES, RECSCOUT_MULT = 2, 60, 2.0   # ... the 2 best-proven lanes go out at 2x minimum, one at a time
HARVEST_BAR_PCT = 0.25          # harvest: a week must earn this % of the floor (a 1% month split in four) ...
HARVEST_SHARE = 0.25            # ... then this share of the week's profit is banked, if equity stays above the floor
TRACK_WINDOWS = ((1, "1 day"), (5, "1 week"), (10, "2 weeks"), (15, "3 weeks"), (21, "1 month"), (63, "3 months"))
VARIANTS = [("plain house", ()), ("+ news blackout", ("news",)), ("+ confidence gate", ("conf",)), ("+ merit entry", ("merit",)),
            ("+ recovery scouts", ("rec",)), ("+ harvest", ("harvest",)), ("ALL of them", ("news", "conf", "merit", "rec", "harvest"))]


class LabHouse(A.House):
    def __init__(self, trades, weekdays, flags=(), fee=None, spec=None, rand_p=0.0, seed=1):
        A.House.__init__(self, trades, weekdays, "house", None, fee, spec)
        self.flags = set(flags)
        self.rand_p, self.rng = rand_p, __import__("random").Random(seed)
        self.bank, self.harvests, self.total = 0.0, [], []
        self.hist = defaultdict(list)           # lane -> [(signals at entry, r)] for every trade the lane ever showed
        self.allrec = defaultdict(list)
        self.proven, self.proven_at = {}, {}
        self.score = {}
        self.conf_r = {"low": [], "high": []}   # results of trades the gate scored below / at or above zero
        self._m = False

    # ---- confidence: which of the lane's entry reads have really gone with its results so far ----
    def _proven(self, lane):
        H = self.hist[lane]
        if len(H) < CONF_MIN_TRADES:
            return []
        if lane in self.proven and len(H) - self.proven_at[lane] < CONF_REFRESH:
            return self.proven[lane]
        out = []
        for k in CONF_SIGNALS:
            xs = [(f[k], r) for f, r in H if f.get(k) is not None]
            m = len(xs)
            if m < 60:
                continue
            mx, my = sum(x for x, _ in xs) / m, sum(y for _, y in xs) / m
            sxx = sum((x - mx) ** 2 for x, _ in xs)
            syy = sum((y - my) ** 2 for _, y in xs)
            if sxx <= 0 or syy <= 0:
                continue
            c = sum((x - mx) * (y - my) for x, y in xs) / math.sqrt(sxx * syy)
            if abs(c) >= 0.999:
                continue
            if abs(c * math.sqrt((m - 2) / (1 - c * c))) >= CONF_MIN_T:
                out.append((k, 1.0 if c > 0 else -1.0, mx, math.sqrt(sxx / m)))
        self.proven[lane], self.proven_at[lane] = out, len(H)
        return out

    def _score(self, t):
        pv = self._proven(t["lane"])
        vals = [sg * (t[k] - mx) / sd for k, sg, mx, sd in pv if t.get(k) is not None and sd > 0]
        return sum(vals) if vals else None

    def _gate(self, t):
        self._m = False
        sc = self._score(t)
        self.score[id(t)] = sc
        if self.rand_p and self.rng.random() < self.rand_p:
            self.blocked["random stay-home"] += 1
            return True
        if "news" in self.flags and t["day"] in NEWS_SCHED and t["t_in"] < first_release_ts(t["day"]) + NEWS_AFTER_SECONDS:
            self.blocked["news blackout"] += 1
            return True
        if "conf" in self.flags and sc is not None and sc < 0 and self.E <= self.peak * (1 - CONF_DEFENSIVE_PCT / 100.0):
            self.blocked["confidence gate"] += 1
            return True
        return False

    def _merit(self, t):
        if "merit" not in self.flags:
            return False
        xs = self.allrec[t["lane"]][-A.RECORD_WINDOW:]
        ok = len(xs) >= MERIT_MIN_TRADES and mean(xs) - MERIT_Z * se(xs) > 0
        self._m = ok
        return ok

    def _size(self, t, lane, risk, base, tag):
        if self._m:
            tag, self._m = tag or "merit", False
        if "rec" in self.flags and (self.peak - self.E) / self.peak * 100.0 >= RECSCOUT_DEPTH_PCT:
            rank = []
            for l in list(self.rec):
                n, lb, _o = self._estimate(l)
                if lb is not None and n >= RECSCOUT_MIN_TRADES and lb > 0:
                    rank.append((lb, l))
            best = [l for _lb, l in sorted(rank, reverse=True)[:RECSCOUT_TOP]]
            if lane in best and not any(o.get("tag") == "recovery scout" for o in self.open.values()) and RECSCOUT_MULT * base > risk:
                risk, tag = RECSCOUT_MULT * base, "recovery scout"
        return risk, tag

    def _week_end(self):
        if "harvest" in self.flags and self.week_pnl >= HARVEST_BAR_PCT / 100.0 * self.F:
            h = HARVEST_SHARE * self.week_pnl
            if self.E - h >= self.F:
                self.E -= h
                self.peak -= h                  # money taken out is not a drawdown
                self.bank += h
                self.harvests.append((self.week, h))

    def _after(self, t, r, o):
        lane = t["lane"]
        self.hist[lane].append((dict((k, t.get(k)) for k in CONF_SIGNALS), r))
        self.allrec[lane].append(r)
        sc = self.score.pop(id(t), None)
        if sc is not None:
            self.conf_r["low" if sc < 0 else "high"].append(r)

    def _roll(self, day):
        n = len(self.curve)
        A.House._roll(self, day)
        if len(self.curve) > n:
            self.total.append(self.curve[-1][1] + self.bank)


def tracker(rep, values, label):
    rep.p("  CONSISTENCY TRACKER (%s): how each stretch of trading days ended, equity plus anything banked" % label)
    rep.p("    %-9s %7s %7s %7s %9s %9s %9s" % ("stretch", "up", "down", "flat", "middle", "worst", "best"))
    for w, name in TRACK_WINDOWS:
        ch = [values[i + w] / values[i] - 1.0 for i in range(0, len(values) - w)]
        if len(ch) < 5:
            continue
        s = sorted(ch)
        n = float(len(ch))
        rep.p("    %-9s %6.0f%% %6.0f%% %6.0f%% %+8.2f%% %+8.2f%% %+8.2f%%" % (
            name, 100 * sum(1 for x in ch if x > 1e-9) / n, 100 * sum(1 for x in ch if x < -1e-9) / n,
            100 * sum(1 for x in ch if abs(x) <= 1e-9) / n, 100 * s[len(s) // 2], 100 * s[0], 100 * s[-1]))


def run_machine(rep, folder):
    rep.p("")
    rep.p("=" * 100)
    rep.p("PART 3: MACHINE   the house replay with extra machinery, one piece at a time")
    rep.p("=" * 100)
    rep.p("trades from: %s" % folder)
    rep.p("'plain house' is the same replay as the house mode (same numbers). Each '+' line switches ONE thing on:")
    rep.p("  news blackout     no new trade on a jobs / CPI / Fed day until %d minutes after the release" % (NEWS_AFTER_SECONDS // 60))
    rep.p("  confidence gate   each lane learns, from its OWN past trades only, which entry reads have gone with its results")
    rep.p("                    (%d+ trades, %.1f+ standard errors). While the account is %g%%+ below its high, a signal whose" % (CONF_MIN_TRADES, CONF_MIN_T, CONF_DEFENSIVE_PCT))
    rep.p("                    proven reads say 'below average' stays home. Soft: it never acts at a new high.")
    rep.p("  merit entry       a trade OUTSIDE its zone (or from a lane with no zone) may go out at minimum size once that")
    rep.p("                    lane's whole record (%d+ trades) is above zero even at its pessimistic end" % MERIT_MIN_TRADES)
    rep.p("  recovery scouts   while %g%%+ below the high, the %d best-proven lanes go out at %gx minimum size, one at a time" % (RECSCOUT_DEPTH_PCT, RECSCOUT_TOP, RECSCOUT_MULT))
    rep.p("  harvest           a week that earns %g%%+ of the floor banks %.0f%% of its profit, if equity stays above the floor" % (HARVEST_BAR_PCT, 100 * HARVEST_SHARE))
    rep.p("total = end equity + banked. Start $%.0f per market and period. Sizes are small, so read direction, not dollars." % A.HOUSE_START)
    specs = dict((x["name"], x) for x in A.COLLECT_SYMBOLS)
    rows, sums, helped, ctl_sum = [], defaultdict(float), defaultdict(int), defaultdict(float)
    for symbol in _symbols(folder):
        trades, days = load_market(folder, symbol)
        spec = specs.get(symbol, {})
        fee = (spec["comm_pct"], spec["comm_min"], spec.get("comm_sides", 2)) if spec.get("comm_min") else None
        for p in ("A", "B"):
            tr = [t for t in trades if t["period"] == p]
            if not tr:
                continue
            tdays = set(t["day"] for t in tr)

            def usable(x):
                return str(x.get("clean", "1")) != "0" and str(x.get("reads_ok", "1")) != "0"
            wd = [x["day"] for x in days if x["period"] == p and (usable(x) or x["day"] in tdays)]
            rep.p("")
            rep.p("#" * 100)
            rep.p("%s  period %s   (%d trading days)" % (symbol, p, len(wd)))
            rep.p("#" * 100)
            rep.p("  %-20s %9s %8s %9s %7s %7s %7s  %s" % ("", "equity", "banked", "total", "drop", "trades", "under", "what it did"))
            keep = {}
            for name, flags in VARIANTS:
                h = LabHouse(tr, wd, flags, fee=fee, spec=spec).run()
                keep[name] = h
                notes = []
                for k in ("news blackout", "confidence gate"):
                    if h.blocked.get(k):
                        notes.append("%s kept %d home" % (k, h.blocked[k]))
                for k in ("merit", "recovery scout"):
                    if k in h.extras and h.extras[k][0]:
                        notes.append("%s: %d trades, %+.0f" % (k, h.extras[k][0], h.extras[k][1]))
                if h.harvests:
                    notes.append("%d harvests" % len(h.harvests))
                tot = h.E + h.bank
                rep.p("  %-20s %9.0f %8.0f %9.0f %6.1f%% %7d %7d  %s" % (name, h.E, h.bank, tot, h.max_dd, sum(h.lane_n.values()),
                                                                  h.longest_under, "; ".join(notes)))
                rows.append({"symbol": symbol, "period": p, "variant": name, "equity": h.E, "banked": h.bank, "total": tot,
                             "worst_drop_pct": h.max_dd, "trades": sum(h.lane_n.values()), "longest_under": h.longest_under})
                sums[(name, p)] += tot - A.HOUSE_START
                helped[(name, p)] += tot > keep["plain house"].E + keep["plain house"].bank + 0.5
                if name in ("+ news blackout", "+ confidence gate"):
                    k = name[2:]
                    seen = sum(1 for t in tr if t["lane"] != "control")
                    share = h.blocked.get(k, 0) / float(max(1, seen))
                    if share > 0:
                        ctl = [LabHouse(tr, wd, (), fee=fee, spec=spec, rand_p=share, seed=s_).run() for s_ in range(1, 6)]
                        ct = mean([c.E for c in ctl])
                        rep.p("  %-20s %9.0f %8s %9.0f %6.1f%% %7.0f %7s  the same share of signals kept home AT RANDOM (average of 5)" % (
                            "  control for it", ct, "", ct, mean([c.max_dd for c in ctl]), mean([sum(c.lane_n.values()) for c in ctl]), ""))
                        ctl_sum[(name, p)] += ct - A.HOUSE_START
            h = keep["plain house"]
            lo, hi = h.conf_r["low"], h.conf_r["high"]
            if len(lo) >= 20 and len(hi) >= 20:
                d, z = _diff(lo, hi)
                rep.p("  CONFIDENCE SCORE, tested on every trade it scored (not only the ones it could block):")
                rep.p("    scored below average: %+.3fR (n=%d) | at or above: %+.3fR (n=%d) | gap %+.3f (z %+.1f)   %s" % (
                    mean(lo), len(lo), mean(hi), len(hi), -d, -z, "the score has skill" if -z >= 2 else ("the score is backwards" if -z <= -2 else "no skill shown")))
            else:
                rep.p("  CONFIDENCE SCORE: too few scored trades to judge (%d below, %d above): no read was proven for most lanes." % (len(lo), len(hi)))
            pv = sorted((l, [k for k, _s, _m, _d in v]) for l, v in h.proven.items() if v)
            if pv:
                rep.p("    reads proven at the end of the period: " + "; ".join("%s: %s" % (l, ", ".join(ks)) for l, ks in pv)[:900])
            if len(h.total) > 30:
                tracker(rep, h.total, "plain house")
            a = keep["ALL of them"]
            if len(a.total) > 30:
                tracker(rep, a.total, "ALL of them")
            if a.harvests:
                months = len(set(w for w, _h in a.harvests))
                rep.p("  HARVEST (ALL of them): $%.0f banked in %d weeks out of %d; that is %.2f%% of the start a month on average." % (
                    a.bank, len(a.harvests), len(a.week_log), 100 * a.bank / A.HOUSE_START / max(1.0, len(wd) / 21.0)))
    rep.p("")
    rep.p("-" * 100)
    rep.p("ALL MARKETS TOGETHER   (sum of each market's gain or loss on its own $%.0f; total = equity + banked)" % A.HOUSE_START)
    rep.p("-" * 100)
    rep.p("  %-20s %12s %12s %14s %14s   %s" % ("", "period A", "period B", "vs plain, A", "vs plain, B", "markets it helped, A / B"))
    for name, _f2 in VARIANTS:
        rep.p("  %-20s %+12.0f %+12.0f %+14.0f %+14.0f   %d / %d" % (name, sums[(name, "A")], sums[(name, "B")],
                                                    sums[(name, "A")] - sums[("plain house", "A")], sums[(name, "B")] - sums[("plain house", "B")],
                                                    helped[(name, "A")], helped[(name, "B")]))
        if (name, "A") in ctl_sum or (name, "B") in ctl_sum:
            rep.p("  %-20s %+12.0f %+12.0f %+14.0f %+14.0f" % ("  control for it", ctl_sum[(name, "A")], ctl_sum[(name, "B")],
                                                        ctl_sum[(name, "A")] - sums[("plain house", "A")], ctl_sum[(name, "B")] - sums[("plain house", "B")]))
    rep.p("  THE CONTROL LINES MATTER: where the lanes lose money on average, keeping ANY trades home 'helps'. A blackout or a")
    rep.p("  gate has skill only if it beats its control (the same number of trades kept home at random).")
    rep.p("  Read: a piece earns its place if it helps in BOTH periods and on most markets, not in the sum alone (gold")
    rep.p("  dominates the sum because the zones were found there). Harvest never adds money: judge it by 'banked' and by")
    rep.p("  whether the worst drop and time under water got worse.")
    A._write_csv(os.path.join(rep.dir, "machine_variants.csv"), rows, first=("symbol", "period", "variant"))
    rep.p("every row: machine_variants.csv")


# ======================================================================================================
# PART 4: PERSIST   do the signals found on 2020-21 / 2024-26 show up on 2014-2019, which no lane had traded?
# ======================================================================================================
# FROZEN ON 2026-10-07, BEFORE the old data was collected. Nothing below may be changed after seeing its result.
# Each claim: (family, entry read, direction). +1 = trades with a HIGH value do better, -1 = do worse.
CLAIMS = [("momentum", "day_eff", +1, "the straighter the day so far, the better momentum trades do"),
          ("breakout", "day_eff", +1, "the straighter the day so far, the better breakouts do"),
          ("reversal", "day_eff", -1, "the straighter the day so far, the worse fades do"),
          ("breakout", "turning", -1, "breakouts do worse when the fast and slow trend disagree"),
          ("reversal", "stretch_atr", -1, "the more stretched the price, the worse fades do")]
# THE RULE: a breakout-family trade counts as 'in' when the day so far is in the top third for straightness
# (cut-off = the 2020-21 value of each market, read from the main collect folder and printed below) AND the fast
# and slow trend agree. Claim: 'in' beats 'out', and the random control lane under the same condition does not.
# THE LABEL: trades entered at the turn of the month (last weekday + first three) do better than the rest.
PERSIST_SIGNALS = CONF_SIGNALS + ("turning",)
PERSIST_FAMILIES = ("breakout", "momentum", "reversal")
ERAS = ["2014-17", "2018-19", "A 2020-21", "B 2024+"]
PERSIST_MIN_N = 30


def _era(t, old):
    if not old:
        return "A 2020-21" if t["period"] == "A" else "B 2024+"
    y = int(t["day"][:4])
    return "2014-17" if y <= 2017 else "2018-19"


def _old_folder():
    base = os.path.join(A.ROOT, "reports")
    fs = sorted(d for d in (os.listdir(base) if os.path.isdir(base) else []) if d.startswith("oldcollect_")
                and any(f.startswith("trades_") for f in os.listdir(os.path.join(base, d))))
    if not fs:
        raise RuntimeError("no oldcollect run found. Run:  python asiabo_offline.py oldcollect   (menu option 5) first.")
    return os.path.join(base, fs[-1])


def _hi_lo(ts, key, field="r"):
    """(diff, z): top third minus bottom third of the read (for a yes/no read: yes minus no). None if too thin."""
    xs = [(t[key], t[field]) for t in ts if t.get(key) is not None and t.get(field) is not None]
    vals = set(v for v, _ in xs)
    if len(vals) <= 2:
        hi, lo = [r for v, r in xs if v], [r for v, r in xs if not v]
    else:
        xs.sort(key=lambda x: x[0])
        k = len(xs) // 3
        lo, hi = [r for _, r in xs[:k]], [r for _, r in xs[len(xs) - k:]]
    if len(hi) < PERSIST_MIN_N or len(lo) < PERSIST_MIN_N:
        return None
    d = mean(hi) - mean(lo)
    sd = math.sqrt(se(hi) ** 2 + se(lo) ** 2)
    return d, (d / sd if sd > 0 else 0.0)


def _cell(zs):
    if not zs:
        return "      -      ", None
    st = sum(zs) / math.sqrt(len(zs))
    return "%+5.1f (%d/%d)  " % (st, sum(1 for z in zs if z > 0), len(zs)), st


def run_persist(rep, folder):
    rep.p("")
    rep.p("=" * 100)
    rep.p("PART 4: PERSIST   do the signals from 2020-21 / 2024-26 show up on 2014-2019?")
    rep.p("=" * 100)
    old = _old_folder()
    rep.p("recent trades: %s" % folder)
    rep.p("old trades:    %s" % old)
    rep.p("The old years were never traded by any lane before this run, and every claim below was written into this file")
    rep.p("BEFORE they were collected. So this is a fair test: nothing here was chosen with the old data in view.")
    rep.p("Costs in the old years are approximate (today's commission, spread allowance and swap are used; real spreads were")
    rep.p("wider then, gold's about 2-3x). That shifts every trade alike, so read the DIFFERENCES and the before-cost column.")
    data = {}                                   # (symbol, era) -> trades
    syms = []
    for s in A.HOUSE_SYMBOLS:
        for fol, is_old in ((folder, False), (old, True)):
            if not os.path.exists(os.path.join(fol, "trades_%s.csv" % s)):
                continue
            trades, _days = load_market(fol, s)
            for t in trades:
                data.setdefault((s, _era(t, is_old)), []).append(t)
            if s not in syms:
                syms.append(s)
    rep.p("trades per era: " + " | ".join("%s %d" % (e, sum(len(v) for (s_, e_), v in data.items() if e_ == e)) for e in ERAS))
    rep.p("markets with old data: " + ", ".join(s for s in syms if (s, "2014-17") in data or (s, "2018-19") in data))

    # ---- 4a: every entry read, every family, four eras ----
    rep.p("")
    rep.p("-" * 100)
    rep.p("4a. EVERY ENTRY READ   (top third minus bottom third of the read, in R; combined over the markets)")
    rep.p("-" * 100)
    rep.p("  each cell: combined z (markets where high was better / markets tested). z beyond +-2 is a real lean, beyond +-3 strong.")
    rep.p("  %-9s %-16s | %-14s %-14s | %-14s %-14s | %s" % ("family", "read", "2014-17", "2018-19", "A 2020-21", "B 2024+", "verdict"))
    table, claims = [], dict(((f, k), (sg, txt)) for f, k, sg, txt in CLAIMS)
    out_rows = []
    for fam in PERSIST_FAMILIES:
        for key in PERSIST_SIGNALS:
            cells, sts = [], []
            for era in ERAS:
                zs = []
                for s in syms:
                    r = _hi_lo([t for t in data.get((s, era), []) if t["family"] == fam], key)
                    if r:
                        zs.append(r[1])
                        out_rows.append({"family": fam, "read": key, "era": era, "symbol": s, "diff_r": r[0], "z": r[1]})
                c, st = _cell(zs)
                cells.append(c)
                sts.append(st)
            table.append((fam, key, cells, sts))
    def strength(row):
        return -abs((row[3][2] or 0) + (row[3][3] or 0))
    kept = 0
    for fam, key, cells, sts in sorted(table, key=strength):
        o1, o2, a, b = sts
        verdict = ""
        if (fam, key) in claims:
            sg = claims[(fam, key)][0]
            olds = [x for x in (o1, o2) if x is not None]
            if not olds:
                verdict = "CLAIM: no old data"
            else:
                comb = sum(olds) / math.sqrt(len(olds))
                right = all(x * sg > 0 for x in olds)
                if right and comb * sg >= 2.0:
                    verdict, kept = "CLAIM: PERSISTS", kept + 1
                elif right:
                    verdict = "CLAIM: same direction, weak"
                else:
                    verdict = "CLAIM: DID NOT PERSIST"
        elif None not in (o1, o2, a, b) and min(abs(o1), abs(o2)) >= 2.0 and (o1 > 0) == (o2 > 0) == (a > 0) == (b > 0):
            verdict = "same way in all four eras (not a claim: found here)"
        rep.p("  %-9s %-16s | %s%s| %s%s| %s" % (fam, key, cells[0], cells[1], cells[2], cells[3], verdict))
    A._write_csv(os.path.join(rep.dir, "persist_reads.csv"), out_rows, first=("family", "read", "era", "symbol"))
    rep.p("")
    rep.p("  THE FIVE CLAIMS: %d of %d persist on the old data." % (kept, len(CLAIMS)))
    for f, k, sg, txt in CLAIMS:
        rep.p("    %-9s %-12s %s" % (f, k, txt))
    rep.p("  By luck alone a claim 'persists' (right direction in both old eras, 2+ standard errors together) about 1 time in 40.")

    # ---- 4b: the rule ----
    rep.p("")
    rep.p("-" * 100)
    rep.p("4b. THE RULE   breakout trades on a straight day (top third, 2020-21 cut-off) with fast and slow trend agreeing")
    rep.p("-" * 100)
    cuts = {}
    for s in syms:
        a = sorted(t["day_eff"] for t in data.get((s, "A 2020-21"), []) if t["family"] == "breakout" and t.get("day_eff") is not None)
        if len(a) < 60:
            a = sorted(t["day_eff"] for e in ("A 2020-21", "B 2024+") for t in data.get((s, e), [])
                       if t["family"] == "breakout" and t.get("day_eff") is not None)
        if a:
            cuts[s] = a[2 * len(a) // 3]
    rep.p("  cut-offs (frozen): " + ", ".join("%s %.3f" % kv for kv in cuts.items()))

    def is_in(t, s):
        return t.get("day_eff") is not None and t["day_eff"] >= cuts[s] and t.get("turning") == 0.0
    rep.p("  %-10s %-10s | %-24s | %-24s | %-13s | %-18s | %s" % ("market", "era", "in: R (n)", "out: R (n)", "in - out (z)", "in, before costs", "control in"))
    rule_rows = []
    for s in list(cuts) + ["ALL"]:
        for era in ERAS:
            src = [(t, s2) for s2 in (cuts if s == "ALL" else [s]) for t in data.get((s2, era), [])]
            ins = [t for t, s2 in src if t["family"] == "breakout" and is_in(t, s2)]
            outs = [t for t, s2 in src if t["family"] == "breakout" and not is_in(t, s2)]
            ctl = [t["r"] for t, s2 in src if t["family"] == "control" and is_in(t, s2)]
            if len(ins) < PERSIST_MIN_N or len(outs) < PERSIST_MIN_N:
                continue
            ri, ro = [t["r"] for t in ins], [t["r"] for t in outs]
            g = [t["gross_r"] for t in ins if t.get("gross_r") is not None]
            d = mean(ri) - mean(ro)
            sd = math.sqrt(se(ri) ** 2 + se(ro) ** 2)
            z = d / sd if sd > 0 else 0.0
            rep.p("  %-10s %-10s | %+.3f +/-%.3f (%5d) | %+.3f +/-%.3f (%5d) | %+.3f (%+.1f) | %+.3f +/-%.3f    | %s" % (
                s, era, mean(ri), se(ri), len(ri), mean(ro), se(ro), len(ro), d, z, mean(g), se(g),
                ("%+.3f (%d)" % (mean(ctl), len(ctl))) if len(ctl) >= 20 else "-"))
            rule_rows.append({"market": s, "era": era, "in_r": mean(ri), "in_n": len(ri), "out_r": mean(ro), "out_n": len(ro),
                              "diff": d, "z": z, "in_gross_r": mean(g), "control_in_r": mean(ctl) if ctl else None})
    A._write_csv(os.path.join(rep.dir, "persist_rule.csv"), rule_rows, first=("market", "era"))
    rep.p("  by year, all markets ('in' against 'out'):")
    by = defaultdict(lambda: ([], []))
    for (s, era), ts in data.items():
        if s not in cuts:
            continue
        for t in ts:
            if t["family"] == "breakout":
                by[t["day"][:4]][0 if is_in(t, s) else 1].append(t["r"])
    rep.p("    " + "  ".join("%s %+.2f/%+.2f" % (y, mean(v[0]), mean(v[1])) for y, v in sorted(by.items()) if len(v[0]) >= 20))
    rep.p("  Read: the rule PERSISTS if, on the ALL rows for 2014-17 and 2018-19, 'in' beats 'out' by 2+ standard errors, the")
    rep.p("  before-cost column is above zero, and the control lane under the same condition is not also lifted.")
    rep.p("  Whether 'in' is above zero AFTER costs in the old years depends on the cost approximation: do not lean on it.")

    # ---- 4c: the label ----
    rep.p("")
    rep.p("-" * 100)
    rep.p("4c. THE LABEL   trades entered at the turn of the month against all other trades (every lane except control)")
    rep.p("-" * 100)
    rep.p("  %-10s | %-22s | %-22s | %-13s | %s" % ("era", "in: R (n)", "out: R (n)", "in - out (z)", "markets better / control in - out"))
    for era in ERAS:
        ins, outs, ci, co, plus, mk = [], [], [], [], 0, 0
        for s in syms:
            ts = data.get((s, era), [])
            a = [t["r"] for t in ts if t["family"] != "control" and t["day"] in TOM]
            b = [t["r"] for t in ts if t["family"] != "control" and t["day"] not in TOM]
            ci += [t["r"] for t in ts if t["family"] == "control" and t["day"] in TOM]
            co += [t["r"] for t in ts if t["family"] == "control" and t["day"] not in TOM]
            if len(a) >= PERSIST_MIN_N and len(b) >= PERSIST_MIN_N:
                mk += 1
                plus += mean(a) > mean(b)
            ins += a
            outs += b
        if len(ins) < PERSIST_MIN_N:
            continue
        d = mean(ins) - mean(outs)
        sd = math.sqrt(se(ins) ** 2 + se(outs) ** 2)
        rep.p("  %-10s | %+.3f +/-%.3f (%5d) | %+.3f +/-%.3f (%5d) | %+.3f (%+.1f) | %d/%d   control %+.3f" % (
            era, mean(ins), se(ins), len(ins), mean(outs), se(outs), len(outs), d, d / sd if sd > 0 else 0.0, plus, mk,
            (mean(ci) - mean(co)) if ci and co else 0.0))
    rep.p("  Read: it persists if 'in - out' is positive in both old eras with 2+ standard errors between them.")


# ======================================================================================================
# PART 5: SIGNALS   classic chart reads, per lane: do they change the outcome, when, and does it last?
# ======================================================================================================
# Every read below is computed from the bars up to and INCLUDING the signal bar (the trade enters at its close),
# so it was known at entry. '_with' = signed by the trade's direction: positive means the read agrees with the trade.
# atr = the M15 ATR(14) at the signal bar. Nothing here was tuned: the lengths are the textbook ones.
NEW_SIGNALS = [
    # ---- higher time frame and moving averages ----
    ("sma20_with", "price above/below the M15 SMA20, in ATR, in the trade's direction"),
    ("sma50_with", "the same against the M15 SMA50"),
    ("h1_trend_with", "against the 1-hour SMA20 (80 M15 bars): the 1-hour trend"),
    ("h4_trend_with", "against the 4-hour SMA20 (320 M15 bars): the 4-hour trend"),
    ("h4_slope_with", "slope of the 4-hour SMA20 over the last 4 hours, in the trade's direction"),
    ("d20_with", "yesterday's close against the daily SMA20, in daily ranges"),
    ("d50_with", "the same against the daily SMA50"),
    ("d200_with", "the same against the daily SMA200"),
    ("htf_agree", "how many of 1-hour, 4-hour, daily-20, daily-50 trends agree with the trade (0-4)"),
    ("ema_stack_with", "M15 EMA20 above/below EMA50 in the trade's direction (yes/no)"),
    # ---- the signal candle ----
    ("body_pct", "body of the signal bar as a share of its range"),
    ("wick_front", "wick on the side the trade is heading to (rejection ahead), share of the range"),
    ("wick_back", "wick on the side the trade comes from, share of the range"),
    ("bar_with", "the signal bar closed in the trade's direction (yes/no)"),
    ("bar_range_atr", "range of the signal bar in ATR"),
    ("run_with", "how many bars in a row before entry closed in the trade's direction"),
    ("body3_pct", "average body share of the last three bars"),
    # ---- stretch and oscillators ----
    ("rsi_with", "RSI(14) minus 50, in the trade's direction"),
    ("bb_with", "position in the Bollinger band (20, 2), in the trade's direction"),
    ("day_pos_with", "where price sits in today's range so far, 1 = at the extreme the trade is heading to"),
    ("prev_close_with", "distance from yesterday's close in daily ranges, in the trade's direction"),
    # ---- volatility ----
    ("squeeze", "range of the last 16 bars against 4 ATR: low = compressed"),
    ("atr_vs_week", "ATR now against its average over the last 5 days"),
    # ---- the lane's own recent trades (known at entry: only trades already closed) ----
    ("last_r", "result of the lane's previous trade"),
    ("last5_r", "average result of the lane's last five trades"),
    ("last5_mae", "average worst point (MAE, in R) of the lane's last five trades"),
    ("last5_mfe", "average best point (MFE, in R) of the lane's last five trades"),
    ("mkt_last20_r", "average result of the last twenty trades of ALL lanes on this market"),
    ("days_since", "days since the lane's previous trade"),
]
SIG_OLD = ("day_eff", "asia_rel", "open_move_with", "volrank", "prev_range_rel", "er60", "ret60_with", "trend20_with",
           "trend5_with", "er5", "er20", "vol3rel", "room_r", "stretch_atr", "setup_range_rel", "stop_atr", "bar_extreme",
           "day_used", "turning", "hour")
SIG_ALL = tuple(k for k, _ in NEW_SIGNALS) + SIG_OLD
SIG_STRONG_Z, SIG_CAND_Z = 3.5, 2.5         # all four eras the same way, and this strong when combined
SEG_GAP_DAYS = 10                           # a break in the bars longer than this starts a new segment (the sealed years, holes)
LANES_ORDER = ["main", "london", "pdh", "retest", "nr7", "fade", "sar", "range", "exhaust", "vwap", "bigrev", "gapfill",
               "trend", "nyaft", "scalp", "bigcont", "swing", "dip", "control"]


def _prefix(xs):
    out = [0.0]
    for x in xs:
        out.append(out[-1] + x)
    return out


def _m15_full(spec):
    """M15 bars straight from bars.db with tick volume and average spread: T, O, H, L, C, V, S, ATR(14).
    Same bars and ATR as asiabo_offline builds (same filters, sealed years never read)."""
    path = A.find_db()
    if not path:
        raise RuntimeError("bars.db not found under %s" % A.ROOT)
    con = sqlite3.connect(path)
    try:
        t, tcol, oc, hc, lo, cc, sc, name_hit = A.detect_source(con, spec["match"])
    except RuntimeError:
        con.close()
        raise RuntimeError("no table for %s in bars.db" % spec["name"])
    cols = dict((r[1].lower(), r[1]) for r in con.execute('pragma table_info("%s")' % t))
    vcol, scol = cols.get("volume"), cols.get("spread_avg")
    q = 'select "%s","%s","%s","%s","%s",%s,%s from "%s"' % (tcol, oc, hc, lo, cc, ('"%s"' % vcol) if vcol else "null",
                                                          ('"%s"' % scol) if scol else "null", t)
    params = ()
    if sc and not name_hit:
        q += ' where upper(replace("%s"," ","")) in (%s)' % (sc, ",".join("?" * len(spec["match"])))
        params = tuple(m.upper() for m in spec["match"])
    q += ' order by "%s"' % tcol
    start = A.epoch_of("2013-01-01")
    s0, s1, locked = A.epoch_of(A.SEAL_START), A.epoch_of(A.SEAL_END), not A.EXAM_UNLOCK
    shift, to_epoch = A.DB_UTC_OFFSET_HOURS * 3600.0, A.to_epoch
    T, O, Hh, L, C, V, S, SN = [], [], [], [], [], [], [], []
    last, cur = -1.0, None
    for raw, o, h, l, c, v, sp in con.execute(q, params):
        try:
            ts = to_epoch(raw) - shift
            o, h, l, c = float(o), float(h), float(l), float(c)
        except (ValueError, TypeError):
            continue
        if ts < start or ts <= last or min(o, h, l, c) <= 0 or (locked and s0 <= ts < s1):
            continue
        last = ts
        k = int(ts // 900) * 900
        if k != cur:
            cur = k
            T.append(k); O.append(o); Hh.append(h); L.append(l); C.append(c); V.append(0.0); S.append(0.0); SN.append(0)
        else:
            if h > Hh[-1]: Hh[-1] = h
            if l < L[-1]: L[-1] = l
            C[-1] = c
        if v is not None:
            V[-1] += v
        if sp is not None:
            S[-1] += sp
            SN[-1] += 1
    con.close()
    n = len(T)
    if n < 2000:
        raise RuntimeError("only %d M15 bars for %s" % (n, spec["name"]))
    S = [(S[i] / SN[i]) if SN[i] else None for i in range(n)]
    if not vcol:
        V = [None] * n
    atr, ssum, trs = [None] * n, 0.0, []
    for i in range(n):
        tr = (Hh[i] - L[i]) if i == 0 else max(Hh[i] - L[i], abs(Hh[i] - C[i - 1]), abs(L[i] - C[i - 1]))
        trs.append(tr)
        ssum += tr
        if i >= A.ATR_PERIOD:
            ssum -= trs[i - A.ATR_PERIOD]
        if i >= A.ATR_PERIOD - 1:
            atr[i] = ssum / A.ATR_PERIOD
    return T, O, Hh, L, C, V, S, atr


def enrich_market(spec, trades, series=None):
    """Adds every NEW_SIGNALS and THEORY_SIGNALS read to the trades of one market. Returns {(half-year): (vol, trendiness)}
    for its stretches. series (a dict) receives this market's (T, C, atr) for the cross-market read."""
    T, O, Hh, L, C, V, S, atr = _m15_full(spec)
    n = len(T)
    if series is not None:
        series[spec["name"]] = (T, C, atr, Hh, L, S)
    seg = [0] * n                               # index where the current unbroken segment starts
    for i in range(1, n):
        seg[i] = i if T[i] - T[i - 1] > SEG_GAP_DAYS * 86400 else seg[i - 1]
    pc, pc2 = _prefix(C), _prefix([c * c for c in C])

    def sma(i, w):
        return (pc[i + 1] - pc[i + 1 - w]) / w if i - seg[i] + 1 >= w else None
    ema20, ema50, rsi = [None] * n, [None] * n, [None] * n
    e20 = e50 = ag = al = None
    for i in range(n):
        if seg[i] == i:
            e20 = e50 = C[i]
            ag = al = 0.0
        else:
            e20 += (C[i] - e20) * 2.0 / 21.0
            e50 += (C[i] - e50) * 2.0 / 51.0
            ch = C[i] - C[i - 1]
            ag += (max(ch, 0.0) - ag) / 14.0
            al += (max(-ch, 0.0) - al) / 14.0
        if i - seg[i] >= 100:
            ema20[i], ema50[i] = e20, e50
        if i - seg[i] >= 28 and ag + al > 0:
            rsi[i] = 100.0 * ag / (ag + al)
    patr = _prefix([a if a is not None else 0.0 for a in atr])
    has_v, has_s = V[0] is not None, any(x is not None for x in S[:2000])
    pv_ = _prefix([v or 0.0 for v in V])
    ps_ = _prefix([x or 0.0 for x in S])
    volrel = [None] * n                         # volume against the same quarter-hour of the last 20 days
    if has_v:
        slots = defaultdict(list)
        for i in range(n):
            sl = slots[int(T[i] % 86400 // 900)]
            if len(sl) >= 10:
                base = sum(sl[-20:]) / len(sl[-20:])
                if base > 0:
                    volrel[i] = V[i] / base
            sl.append(V[i])
            if len(sl) > 40:
                del sl[:20]
    adx = [None] * n                            # ADX(14), Wilder
    sp_ = sm_ = st_ = ax = None
    for i in range(1, n):
        if seg[i] == i:
            sp_ = sm_ = st_ = ax = None
            continue
        up, dn = Hh[i] - Hh[i - 1], L[i - 1] - L[i]
        pdm, mdm = (up if up > dn and up > 0 else 0.0), (dn if dn > up and dn > 0 else 0.0)
        tr = max(Hh[i] - L[i], abs(Hh[i] - C[i - 1]), abs(L[i] - C[i - 1]))
        if sp_ is None:
            sp_, sm_, st_ = pdm, mdm, tr
        else:
            sp_ += (pdm - sp_) / 14.0
            sm_ += (mdm - sm_) / 14.0
            st_ += (tr - st_) / 14.0
        if st_ > 0 and sp_ + sm_ > 0:
            dx = 100.0 * abs(sp_ - sm_) / (sp_ + sm_)
            ax = dx if ax is None else ax + (dx - ax) / 14.0
            if i - seg[i] >= 42:
                adx[i] = ax
    Hc = spec.get("hours", A.CLOCK_UTC)
    open_hour = Hc["big"]                       # the market's main open on its own clock (London 07, New York cash 13)
    open_idx, lday_of = {}, [0] * n
    sh_day, sh = None, 0.0
    for i in range(n):
        ud = int(T[i] // 86400)
        if ud != sh_day:
            sh_day, sh = ud, A._clock_shift(Hc, T[i])
        lt = T[i] + sh
        ld = int(lt // 86400)
        lday_of[i] = ld
        if ld not in open_idx and int(lt % 86400 // 3600) >= open_hour:
            open_idx[ld] = i
    # daily bars on plain UTC days
    dk, dO, dH, dL, dC, dfirst = [], [], [], [], [], []
    for i in range(n):
        k = int(T[i] // 86400)
        if (k + 3) % 7 >= 5:
            continue
        if not dk or dk[-1] != k:
            dk.append(k); dO.append(O[i]); dH.append(Hh[i]); dL.append(L[i]); dC.append(C[i]); dfirst.append(i)
        else:
            if Hh[i] > dH[-1]: dH[-1] = Hh[i]
            if L[i] < dL[-1]: dL[-1] = L[i]
            dC[-1] = C[i]
    dpos = dict((k, j) for j, k in enumerate(dk))
    dseg = [0] * len(dk)
    for j in range(1, len(dk)):
        dseg[j] = j if dk[j] - dk[j - 1] > SEG_GAP_DAYS else dseg[j - 1]
    dpc = _prefix(dC)
    dpr = _prefix([h - l for h, l in zip(dH, dL)])

    def dsma(j, w):                             # over the w completed days ending at day j
        return (dpc[j + 1] - dpc[j + 1 - w]) / w if j - dseg[j] + 1 >= w else None
    import bisect as _b
    by_lane, mkt = defaultdict(list), []
    order = sorted(trades, key=lambda t: t["t_in"])
    closed = sorted(trades, key=lambda t: t["t_out"])
    ci = 0
    for t in order:
        for k, _ in NEW_SIGNALS:
            t[k] = None
        while ci < len(closed) and closed[ci]["t_out"] <= t["t_in"]:
            c_ = closed[ci]
            by_lane[c_["lane"]].append(c_)
            if c_["lane"] != "control":
                mkt.append(c_["r"])
            ci += 1
        hist = by_lane[t["lane"]]
        if hist:
            t["last_r"] = hist[-1]["r"]
            t["days_since"] = (t["t_in"] - hist[-1]["t_in"]) / 86400.0
        if len(hist) >= 5:
            h5 = hist[-5:]
            t["last5_r"] = mean([x["r"] for x in h5])
            ma = [x["mae_r"] for x in h5 if x.get("mae_r") is not None]
            mf = [x["mfe_r"] for x in h5 if x.get("mfe_r") is not None]
            t["last5_mae"] = mean(ma) if len(ma) == 5 else None
            t["last5_mfe"] = mean(mf) if len(mf) == 5 else None
        if len(mkt) >= 20:
            t["mkt_last20_r"] = mean(mkt[-20:])
        i = _b.bisect_right(T, t["t_in"] - 900 + 0.5) - 1          # the signal bar
        if i < 0 or abs(T[i] - (t["t_in"] - 900)) > 1.0 or atr[i] is None or not atr[i]:
            continue
        a, d, c = atr[i], t["dir"], C[i]
        for w, key in ((20, "sma20_with"), (50, "sma50_with"), (80, "h1_trend_with"), (320, "h4_trend_with")):
            v = sma(i, w)
            if v is not None:
                t[key] = (c - v) / a * d
        if i - seg[i] + 1 >= 336:
            t["h4_slope_with"] = (sma(i, 320) - sma(i - 16, 320)) / a * d
        if ema20[i] is not None:
            t["ema_stack_with"] = 1.0 if (ema20[i] - ema50[i]) * d > 0 else 0.0
        rng = Hh[i] - L[i]
        if rng > 0:
            body = abs(c - O[i])
            up, dn = Hh[i] - max(c, O[i]), min(c, O[i]) - L[i]
            t["body_pct"] = body / rng
            t["wick_front"] = (up if d > 0 else dn) / rng
            t["wick_back"] = (dn if d > 0 else up) / rng
            t["bar_range_atr"] = rng / a
        t["bar_with"] = 1.0 if (c - O[i]) * d > 0 else 0.0
        run = 0
        j = i
        while j > seg[i] and run < 12 and (C[j] - O[j]) * d > 0:
            run += 1
            j -= 1
        t["run_with"] = float(run)
        if i - seg[i] >= 3:
            bp = [abs(C[j] - O[j]) / (Hh[j] - L[j]) for j in (i, i - 1, i - 2) if Hh[j] > L[j]]
            t["body3_pct"] = mean(bp) if bp else None
        if rsi[i] is not None:
            t["rsi_with"] = (rsi[i] - 50.0) * d
        s20 = sma(i, 20)
        if s20 is not None:
            var = (pc2[i + 1] - pc2[i - 19]) / 20.0 - s20 * s20
            if var > 0:
                t["bb_with"] = (c - s20) / (2.0 * math.sqrt(var)) * d
        if i - seg[i] >= 16:
            t["squeeze"] = (max(Hh[i - 15:i + 1]) - min(L[i - 15:i + 1])) / (4.0 * a)
        if i - seg[i] >= 480 + 14:
            t["atr_vs_week"] = a / ((patr[i + 1] - patr[i - 479]) / 480.0)
        # ---- batch two: reads each lane's theory asks for ----
        for k, _ in THEORY_SIGNALS:
            t.setdefault(k, None)
        back = i - seg[i]
        if has_v:
            t["vol_rel"] = volrel[i]
            if back >= 20:
                b4, b16 = (pv_[i + 1] - pv_[i - 3]) / 4.0, (pv_[i - 3] - pv_[i - 19]) / 16.0
                t["vol_trend"] = b4 / b16 if b16 > 0 else None
            if back >= 96:
                w = V[i - 95:i + 1]
                t["vol_rank96"] = sum(1 for x in w if x <= V[i]) / 96.0
        if has_s and S[i] is not None:
            t["spread_px"] = S[i]
            t["spread_atr"] = S[i] / a
            if back >= 480:
                base = (ps_[i + 1] - ps_[i - 479]) / 480.0
                t["spread_rel"] = S[i] / base if base > 0 else None
        if back >= 33:
            w0 = i - 32
            if d > 0:
                ref = max(Hh[w0:i])
                t["beyond20_with"] = (c - max(Hh[i - 20:i])) / a
                t["edge_tests"] = float(sum(1 for j2 in range(w0, i) if Hh[j2] >= ref - 0.25 * a))
                hi_i = max(range(w0, i + 1), key=lambda j2: Hh[j2])
                lo_v = min(L[w0:hi_i + 1])
                if Hh[hi_i] > lo_v:
                    t["fib_retrace"] = (Hh[hi_i] - c) / (Hh[hi_i] - lo_v)
            else:
                ref = min(L[w0:i])
                t["beyond20_with"] = (min(L[i - 20:i]) - c) / a
                t["edge_tests"] = float(sum(1 for j2 in range(w0, i) if L[j2] <= ref + 0.25 * a))
                lo_i = min(range(w0, i + 1), key=lambda j2: L[j2])
                hi_v = max(Hh[w0:lo_i + 1])
                if hi_v > L[lo_i]:
                    t["fib_retrace"] = (c - L[lo_i]) / (hi_v - L[lo_i])
            t["speed8_with"] = (c - C[i - 8]) / a * d
            if abs(c - C[i - 8]) > 0.05 * a:
                t["accel"] = min(3.0, abs(c - C[i - 4]) / abs(c - C[i - 8]))
            if rsi[i] is not None and rsi[i - 16] is not None:
                t["rsi_div_with"] = 1.0 if (c - C[i - 16]) * d < 0 and (rsi[i] - rsi[i - 16]) * d > 0 else 0.0
        ra, j2 = 0, i
        while j2 > seg[i] and ra < 12 and (C[j2] - O[j2]) * d < 0:
            ra += 1
            j2 -= 1
        t["run_against"] = float(ra)
        t["adx"] = adx[i]
        if t.get("h4_slope_with") is not None:
            t["h4_slope_abs"] = abs(t["h4_slope_with"])
        oi = open_idx.get(lday_of[i])
        if oi is not None and i >= oi:
            t["hours_since_open"] = (T[i] + 900 - T[oi]) / 3600.0
            if i >= oi + 3 and T[oi + 3] - T[oi] <= 3600:
                t["first_hour_with"] = (C[oi + 3] - O[oi]) / a * d
        j = dpos.get(int(T[i] // 86400))
        if j is not None and j - 1 >= 0 and dseg[j - 1] == dseg[j]:
            p = j - 1
            if dH[p] > dL[p]:
                pos_ = (dC[p] - dL[p]) / (dH[p] - dL[p])
                t["prev_close_pos_with"] = pos_ if d > 0 else 1.0 - pos_
            if p - dseg[p] >= 20:
                dr = (dpr[p + 1] - dpr[p - 19]) / 20.0
                if dr > 0:
                    t["pdh_dist_with"] = ((dH[p] - c) if d > 0 else (c - dL[p])) / dr
                    if oi is not None and i >= oi:
                        t["overnight_with"] = (O[oi] - dC[p]) / dr * d
            if p - dseg[p] >= 1:
                t["inside_day"] = 1.0 if dH[p] <= dH[p - 1] and dL[p] >= dL[p - 1] else 0.0
            if p - dseg[p] >= 4:
                wh, wl = max(dH[p - 4:p + 1]), min(dL[p - 4:p + 1])
                if wh > wl:
                    t["week_pos_with"] = (c - wl) / (wh - wl) if d > 0 else (wh - c) / (wh - wl)
                cnt = 0
                for k2 in range(p - 3, p + 1):
                    if d > 0 and dH[k2] > dH[k2 - 1] and dL[k2] > dL[k2 - 1]:
                        cnt += 1
                    if d < 0 and dH[k2] < dH[k2 - 1] and dL[k2] < dL[k2 - 1]:
                        cnt += 1
                t["d_hh_with"] = float(cnt)
        j = dpos.get(int(T[i] // 86400))
        if j is not None:
            hi_, lo_ = max(Hh[dfirst[j]:i + 1]), min(L[dfirst[j]:i + 1])
            if hi_ > lo_:
                t["day_pos_with"] = (c - lo_) / (hi_ - lo_) if d > 0 else (hi_ - c) / (hi_ - lo_)
            p = j - 1                               # the last COMPLETED day
            if p >= 0 and dseg[p] == dseg[j] and p - dseg[p] + 1 >= 20:
                dr = (dpr[p + 1] - dpr[p - 19]) / 20.0
                if dr > 0:
                    t["prev_close_with"] = (c - dC[p]) / dr * d
                    agree = 0
                    for w, key in ((20, "d20_with"), (50, "d50_with"), (200, "d200_with")):
                        v = dsma(p, w)
                        if v is not None:
                            t[key] = (dC[p] - v) / dr * d
                    if t["d20_with"] is not None and t["d50_with"] is not None and t["h1_trend_with"] is not None and t["h4_trend_with"] is not None:
                        t["htf_agree"] = float(sum(1 for k in ("h1_trend_with", "h4_trend_with", "d20_with", "d50_with") if t[k] > 0))
    # what each half-year looked like on this market: how much it moved a day, and how straight it went
    cells = defaultdict(list)
    for j in range(1, len(dk)):
        if dseg[j] != j:
            dt_ = datetime.date(1970, 1, 1) + datetime.timedelta(days=dk[j])
            cells["%d%s" % (dt_.year, "H1" if dt_.month <= 6 else "H2")].append(dC[j] / dC[j - 1] - 1.0)
    out = {}
    for k, rs in cells.items():
        if len(rs) >= 60:
            path = sum(abs(x) for x in rs)
            out[k] = (path / len(rs), abs(sum(rs)) / path if path else 0.0)
    return out


def _half(t):
    return t["day"][:4] + ("H1" if t["day"][5:7] <= "06" else "H2")


def _prev_half(h):
    y, k = int(h[:4]), h[4:]
    return "%dH1" % y if k == "H2" else "%dH2" % (y - 1)


def _sig_cells(trades_by, key, pick):
    """Combined z over markets for one era of one lane/family: [(market z)...] -> (stouffer, n+, n)."""
    zs = []
    for ts in trades_by:
        r = _hi_lo([t for t in ts if pick(t)], key)
        if r:
            zs.append(r[1])
    if not zs:
        return None
    return sum(zs) / math.sqrt(len(zs)), sum(1 for z in zs if z > 0), len(zs)


def _top_r(ts, key, sign):
    """Average R of the favourable third of the read (top third if sign > 0, bottom third otherwise)."""
    xs = sorted([(t[key], t["r"]) for t in ts if t.get(key) is not None], key=lambda x: x[0])
    if len(set(v for v, _ in xs)) <= 2:
        pick = [r for v, r in xs if (v > 0) == (sign > 0)]
    else:
        k = len(xs) // 3
        pick = [r for _, r in (xs[len(xs) - k:] if sign > 0 else xs[:k])]
    return (mean(pick), len(pick)) if len(pick) >= PERSIST_MIN_N else (None, len(pick))


def run_signals(rep, folder):
    rep.p("")
    rep.p("=" * 100)
    rep.p("PART 5: SIGNALS   chart reads at entry, per lane: do they change the outcome, when, and does it last?")
    rep.p("=" * 100)
    old = _old_folder()
    rep.p("recent trades: %s" % folder)
    rep.p("old trades:    %s" % old)
    rep.p("Each read is computed from bars.db at every trade's signal bar (known at entry). New reads in this part:")
    for k, txt in NEW_SIGNALS:
        rep.p("  %-16s %s" % (k, txt))
    rep.p("plus the %d reads collect already saved (day_eff, stretch_atr, volrank ...)." % len(SIG_OLD))
    specs = dict((x["name"], x) for x in A.COLLECT_SYMBOLS)
    data, state, syms = {}, {}, []              # data[(symbol, era)] = trades ; state[(symbol, half)] = (vol, trendiness)
    for s in A.HOUSE_SYMBOLS:
        both = []
        for fol, is_old in ((folder, False), (old, True)):
            if os.path.exists(os.path.join(fol, "trades_%s.csv" % s)):
                trades, _days = load_market(fol, s)
                for t in trades:
                    t["era"] = _era(t, is_old)
                    t["hour"] = _f(t.get("hour"))
                    for k in ("mae_r", "mfe_r"):
                        t[k] = _f(t.get(k))
                both += trades
        if not both:
            continue
        print("computing chart reads: %s (%d trades) ..." % (s, len(both)))
        try:
            st = enrich_market(specs[s], both)
        except RuntimeError as e:
            rep.p("%s: skipped (%s)" % (s, str(e).splitlines()[0]))
            continue
        syms.append(s)
        for k, v in st.items():
            state[(s, k)] = v
        for t in both:
            data.setdefault((s, t["era"]), []).append(t)
        A._write_csv(os.path.join(rep.dir, "trades_plus_%s.csv" % s),
                     [dict((k, t.get(k)) for k in ("symbol", "era", "family", "lane", "day", "entry_time", "dir", "r", "gross_r") + SIG_ALL) for t in both],
                     first=("symbol", "era", "family", "lane", "day", "entry_time", "dir", "r"))
    if not syms:
        rep.p("no market could be read.")
        return
    filled = sum(1 for ts in data.values() for t in ts if t.get("h1_trend_with") is not None)
    total = sum(len(ts) for ts in data.values())
    rep.p("trades: %d, of which %d (%.0f%%) could be matched to their signal bar and given chart reads." % (total, filled, 100.0 * filled / max(1, total)))
    # high / low volatility and trendy / choppy half-years, per market, against that market's own median
    med = {}
    for s in syms:
        vs = sorted(v[0] for (s2, _k), v in state.items() if s2 == s)
        es = sorted(v[1] for (s2, _k), v in state.items() if s2 == s)
        if vs:
            med[s] = (vs[len(vs) // 2], es[len(es) // 2])
    for s in syms:
        for era in ERAS:
            for t in data.get((s, era), []):
                h = _half(t)
                st, pv = state.get((s, h)), state.get((s, _prev_half(h)))
                t["st_vol"] = None if st is None else (1.0 if st[0] >= med[s][0] else 0.0)
                t["st_trend"] = None if st is None else (1.0 if st[1] >= med[s][1] else 0.0)
                t["pv_vol"] = None if pv is None else (1.0 if pv[0] >= med[s][0] else 0.0)
                t["pv_trend"] = None if pv is None else (1.0 if pv[1] >= med[s][1] else 0.0)
    lanes = [l for l in LANES_ORDER if any(t["lane"] == l for ts in data.values() for t in ts)]
    groups = [("lane", l, (lambda t, l=l: t["lane"] == l)) for l in lanes] + \
             [("family", f, (lambda t, f=f: t["family"] == f)) for f in A.FAMILIES]
    idx = defaultdict(lambda: defaultdict(list))        # (kind, name) -> (symbol, era) -> trades
    for (s, era), ts in data.items():
        for t in ts:
            idx[("lane", t["lane"])][(s, era)].append(t)
            if t["family"] in A.FAMILIES:
                idx[("family", t["family"])][(s, era)].append(t)

    def zcomb(lists, key, field="r"):
        zs = [r[1] for r in (_hi_lo(ts, key, field) for ts in lists if len(ts) >= 2 * PERSIST_MIN_N) if r]
        return (sum(zs) / math.sqrt(len(zs)), sum(1 for z in zs if z > 0), len(zs)) if zs else None

    # ---- 5a: reads that change the outcome in all four eras ----
    rep.p("")
    rep.p("-" * 100)
    rep.p("5a. READS THAT CHANGE THE OUTCOME IN ALL FOUR ERAS   (per lane and per family)")
    rep.p("-" * 100)
    rep.p("  For each lane and read: average R of the top third of the read minus the bottom third, on each market, combined")
    rep.p("  over the markets. Listed only when all four eras point the SAME way and the four together are %.1f+ standard" % SIG_CAND_Z)
    rep.p("  errors from zero (%.1f+ = STRONG). z columns: 2014-17, 2018-19, 2020-21, 2024+. 'best third' = average R, after" % SIG_STRONG_Z)
    rep.p("  costs, of the favourable third of the read, old years | recent years: above zero there is what an edge looks like.")
    all_rows, found, tested = [], [], 0
    for kind, name, pick in groups:
        for key in SIG_ALL:
            sts = []
            for era in ERAS:
                sts.append(zcomb([idx[(kind, name)].get((s, era), []) for s in syms], key))
            row = {"kind": kind, "name": name, "read": key}
            for era, st in zip(ERAS, sts):
                row["z " + era] = st[0] if st else None
                row["markets+ " + era] = ("%d/%d" % (st[1], st[2])) if st else None
            all_rows.append(row)
            if None in sts:
                continue
            tested += 1
            zs = [st[0] for st in sts]
            comb = sum(zs) / 2.0
            row["z all"] = comb
            if (min(zs) > 0 or max(zs) < 0) and abs(comb) >= SIG_CAND_Z:
                sign = 1 if comb > 0 else -1
                gz = [zcomb([idx[(kind, name)].get((s, era), []) for s in syms], key, "gross_r") for era in ERAS]
                gross = sum(g[0] for g in gz if g) / math.sqrt(max(1, sum(1 for g in gz if g)))
                row["z all before costs"] = gross
                oldt = [t for s in syms for e in ERAS[:2] for t in idx[(kind, name)].get((s, e), [])]
                newt = [t for s in syms for e in ERAS[2:] for t in idx[(kind, name)].get((s, e), [])]
                found.append((abs(comb), kind, name, key, zs, comb, _top_r(oldt, key, sign), _top_r(newt, key, sign),
                              mean([t["r"] for t in oldt]), mean([t["r"] for t in newt]), gross))
    A._write_csv(os.path.join(rep.dir, "signals_all.csv"), all_rows, first=("kind", "name", "read"))
    rep.p("  'pre-cost' = the same combined z measured on results BEFORE costs. If it collapses towards zero, the read only")
    rep.p("  'works' because it goes with wider stops (a cost that is a smaller share of the stop): arithmetic, not prediction.")
    rep.p("  %-7s %-9s %-16s | %5s %5s %5s %5s | %5s %8s | %-9s | %-21s | %s" % (
        "", "", "read", "14-17", "18-19", "20-21", "24+", "all", "pre-cost", "better", "best third: old | new", "all its trades: old | new"))
    for _a, kind, name, key, zs, comb, to, tn, bo, bn, gross in sorted(found, reverse=True):
        note = "STRONG" if abs(comb) >= SIG_STRONG_Z else ""
        if abs(gross) < 2.0 or (gross > 0) != (comb > 0):
            note = "cost arithmetic"
        rep.p("  %-7s %-9s %-16s | %+5.1f %+5.1f %+5.1f %+5.1f | %+5.1f %+8.1f | %-9s | %s | %s   %s" % (
            kind, name, key, zs[0], zs[1], zs[2], zs[3], comb, gross, "when HIGH" if comb > 0 else "when LOW",
            "%s | %s" % ("%+.3f" % to[0] if to[0] is not None else "   -  ", "%+.3f" % tn[0] if tn[0] is not None else "   -  "),
            "%+.3f | %+.3f" % (bo, bn), note))
    n_strong = sum(1 for f in found if f[0] >= SIG_STRONG_Z and abs(f[10]) >= 2.0 and (f[10] > 0) == (f[5] > 0))
    rep.p("  %d lane-and-read pairs were tested in all four eras. By luck alone about %.1f would be listed and about %.1f would" % (
        tested, tested * 0.0096, tested * 0.00043))
    rep.p("  be STRONG. Listed: %d, of which STRONG and not cost arithmetic: %d." % (len(found), n_strong))
    rep.p("  every pair, listed or not: signals_all.csv")

    # ---- 5b: when each lane worked ----
    rep.p("")
    rep.p("-" * 100)
    rep.p("5b. WHEN EACH LANE WORKED   (half-years, all markets together)")
    rep.p("-" * 100)
    halves = sorted(set(_half(t) for ts in data.values() for t in ts))
    rep.p("  One character per half-year, %s to %s (the sealed years are missing):" % (halves[0], halves[-1]))
    rep.p("    + average R above +0.05   - below -0.05   . in between   (blank) fewer than 15 trades")
    rep.p("  up = share of half-years above zero | lasts = does a good half-year follow a good one on the same market")
    rep.p("  (+1 always, 0 no link, -1 flips) | high-vol / low-vol and trendy / choppy = average R in half-years where that")
    rep.p("  market moved more / less than its own usual, and went straighter / less straight than its own usual.")
    rep.p("  %-9s %-*s %4s %6s | %-17s | %-17s" % ("lane", len(halves), "half-years", "up", "lasts", "high-vol / low-vol", "trendy / choppy"))
    stretch_rows = []
    for kind, name, pick in groups:
        by = defaultdict(list)
        cell = defaultdict(list)
        mine = [t for ts in idx[(kind, name)].values() for t in ts]
        for (s, era), ts in idx[(kind, name)].items():
            for t in ts:
                by[_half(t)].append(t["r"])
                cell[(s, _half(t))].append(t["r"])
        line = "".join((" " if len(by[h]) < 15 else ("+" if mean(by[h]) > 0.05 else ("-" if mean(by[h]) < -0.05 else "."))) for h in halves)
        ok = [h for h in halves if len(by[h]) >= 15]
        if len(ok) < 6:
            continue
        up = sum(1 for h in ok if mean(by[h]) > 0) / float(len(ok))
        pairs = [(mean(cell[(s, _prev_half(h))]), mean(v)) for (s, h), v in cell.items()
                 if len(v) >= 15 and len(cell.get((s, _prev_half(h)), [])) >= 15]
        lasts = A._corr([p[0] for p in pairs], [p[1] for p in pairs]) if len(pairs) >= 8 else None
        def avg(flag, val):
            xs = [t["r"] for t in mine if t.get(flag) == val]
            return mean(xs) if len(xs) >= PERSIST_MIN_N else None
        hv, lv, tr_, ch = avg("st_vol", 1.0), avg("st_vol", 0.0), avg("st_trend", 1.0), avg("st_trend", 0.0)
        f2 = lambda x: "  -   " if x is None else "%+.3f" % x
        rep.p("  %-9s %s %3.0f%% %6s | %s / %s   | %s / %s" % (name, line, 100 * up, "  -  " if lasts is None else "%+.2f" % lasts,
                                                        f2(hv), f2(lv), f2(tr_), f2(ch)))
        for h in ok:
            stretch_rows.append({"kind": kind, "name": name, "half": h, "r": mean(by[h]), "n": len(by[h])})
    A._write_csv(os.path.join(rep.dir, "lane_stretches.csv"), stretch_rows, first=("kind", "name", "half"))
    rep.p("  what each half-year looked like on each market (average daily move, straightness): market_stretches.csv")
    A._write_csv(os.path.join(rep.dir, "market_stretches.csv"),
                 [{"symbol": s, "half": h, "avg_daily_move_pct": 100 * v[0], "straightness": v[1],
                   "high_vol": int(v[0] >= med[s][0]), "trendy": int(v[1] >= med[s][1])} for (s, h), v in sorted(state.items()) if s in med],
                 first=("symbol", "half"))

    # ---- 5c: reads that only matter in one kind of stretch ----
    rep.p("")
    rep.p("-" * 100)
    rep.p("5c. READS THAT ONLY MATTER IN ONE KIND OF STRETCH   (and do so in BOTH the old years and the recent years)")
    rep.p("-" * 100)
    rep.p("  The same top-third-minus-bottom-third test, but only on trades from one kind of half-year: high-vol, low-vol,")
    rep.p("  trendy or choppy (per market, against its own usual). Listed when the read is 2+ standard errors the same way in")
    rep.p("  the old years (2014-19) AND the recent years (2020-26) inside that kind of stretch, and NOT in the opposite kind.")
    rep.p("  'known before' repeats the test using the PREVIOUS half-year's kind, which is all you would know while trading.")
    rep.p("  %-7s %-9s %-16s %-10s | %-13s | %-17s | %-17s | %s" % ("", "", "read", "stretch", "old / recent z", "opposite stretch", "known before", "best third R old | new"))
    cond_rows, listed, tested_c = [], 0, 0
    for kind, name, pick in groups:
        sub = defaultdict(list)                 # (symbol, old/new, flag, value) -> trades
        for (s, era), ts in idx[(kind, name)].items():
            on_ = 0 if era in ERAS[:2] else 1
            for t in ts:
                for fl in ("st_vol", "st_trend", "pv_vol", "pv_trend"):
                    if t.get(fl) is not None:
                        sub[(s, on_, fl, t[fl])].append(t)

        def z_in(_pick, key, flag, val, eras):
            st = zcomb([sub.get((s, 0 if eras[0] == ERAS[0] else 1, flag, val), []) for s in syms], key)
            return st[0] if st else None
        for key in SIG_ALL:
            for flag, pflag, labels in (("st_vol", "pv_vol", ("low-vol", "high-vol")), ("st_trend", "pv_trend", ("choppy", "trendy"))):
                for val in (1.0, 0.0):
                    zo, zn = z_in(pick, key, flag, val, ERAS[:2]), z_in(pick, key, flag, val, ERAS[2:])
                    if zo is None or zn is None:
                        continue
                    tested_c += 1
                    oo, on = z_in(pick, key, flag, 1.0 - val, ERAS[:2]), z_in(pick, key, flag, 1.0 - val, ERAS[2:])
                    row = {"kind": kind, "name": name, "read": key, "stretch": labels[int(val)], "z_old": zo, "z_new": zn,
                           "z_old_opposite": oo, "z_new_opposite": on}
                    cond_rows.append(row)
                    if not ((zo > 0) == (zn > 0) and min(abs(zo), abs(zn)) >= 2.0):
                        continue
                    opp_same = oo is not None and on is not None and (oo > 0) == (on > 0) == (zo > 0) and min(abs(oo), abs(on)) >= 1.0
                    if opp_same:
                        continue                # it works in both kinds: that is 5a's business, not a 'when'
                    po, pn = z_in(pick, key, pflag, val, ERAS[:2]), z_in(pick, key, pflag, val, ERAS[2:])
                    sign = 1 if zo > 0 else -1
                    to = _top_r([t for s in syms for t in sub.get((s, 0, flag, val), [])], key, sign)
                    tn = _top_r([t for s in syms for t in sub.get((s, 1, flag, val), [])], key, sign)
                    listed += 1
                    f1 = lambda x: "  -  " if x is None else "%+5.1f" % x
                    rep.p("  %-7s %-9s %-16s %-10s | %s / %s | %s / %s     | %s / %s     | %s | %s" % (
                        kind, name, key, labels[int(val)], f1(zo), f1(zn), f1(oo), f1(on), f1(po), f1(pn),
                        "   -  " if to[0] is None else "%+.3f" % to[0], "   -  " if tn[0] is None else "%+.3f" % tn[0]))
    A._write_csv(os.path.join(rep.dir, "signals_by_stretch.csv"), cond_rows, first=("kind", "name", "read", "stretch"))
    rep.p("  %d lane-read-stretch combinations were tested; by luck alone about %.0f would be listed. Listed: %d." % (
        tested_c, tested_c * 0.0455 * 0.0455 / 2.0, listed))
    rep.p("  A listing is only useful if 'known before' agrees (the same sign, 2+ in both): otherwise you could not have known")
    rep.p("  you were in that kind of stretch while trading. every combination: signals_by_stretch.csv")
    rep.p("  each trade with all its reads: trades_plus_<market>.csv")


# ======================================================================================================
# PART 6: THEORY   each lane's own reads, judged per kind of market, with recent years trusted more
# ======================================================================================================
THEORY_SIGNALS = [
    ("vol_rel", "tick volume of the signal bar against the same quarter-hour over the last 20 days"),
    ("vol_trend", "volume of the last 4 bars against the 16 before them"),
    ("vol_rank96", "where the signal bar's volume ranks among the last 96 bars (1 = the biggest: a climax)"),
    ("spread_atr", "spread at the signal bar as a share of ATR (what the market charges right now)"),
    ("spread_rel", "spread at the signal bar against its 5-day average"),
    ("beyond20_with", "how far the close is beyond the last 20 bars' extreme, in ATR, in the trade's direction"),
    ("edge_tests", "how many of the last 32 bars reached the level being traded through (tests of the edge)"),
    ("fib_retrace", "pullback depth: how much of the last swing has been given back (0 = none, 1 = all of it)"),
    ("speed8_with", "move over the last 2 hours in ATR, in the trade's direction (speed of approach)"),
    ("accel", "share of that 2-hour move made in the last hour (above 0.5 = speeding up)"),
    ("rsi_div_with", "RSI divergence in the trade's favour: price went against it, RSI did not (yes/no)"),
    ("run_against", "how many bars in a row before entry closed AGAINST the trade"),
    ("adx", "ADX(14) on M15: how strong the trend is, whatever its direction"),
    ("h4_slope_abs", "how steep the 4-hour average is, whatever its direction (low = flat market)"),
    ("hours_since_open", "hours since the market's main open (London, or the New York cash open)"),
    ("first_hour_with", "the first hour after the main open, in ATR, in the trade's direction"),
    ("overnight_with", "move from yesterday's close to the main open, in daily ranges, in the trade's direction"),
    ("prev_close_pos_with", "where yesterday closed in its range, 1 = at the extreme the trade is heading to"),
    ("pdh_dist_with", "distance still to go to yesterday's high (longs) or low (shorts), in daily ranges"),
    ("inside_day", "yesterday was an inside day (yes/no)"),
    ("week_pos_with", "position in the last five days' range, 1 = at the extreme the trade is heading to"),
    ("d_hh_with", "how many of the last four days made a higher high and higher low (lower for shorts)"),
    ("xm_with", "related markets moved the trade's way over the last 2 hours (dollar for gold, US 500 for Germany ...)"),
    ("lanes_same_today", "other lanes that already traded the same direction today"),
    ("lanes_opp_today", "other lanes that already traded the opposite direction today"),
    ("failed_fade_with", "a fade against this direction was stopped out in the last 4 hours (yes/no)"),
    ("failed_break_with", "a breakout against this direction failed in the last 4 hours (yes/no)"),
]
# THE SHEET (written 2026-10-07, before any of these reads was computed): what each lane's theory says should help.
# +1 = a HIGH value should mean better trades, -1 = a LOW value should.
THEORY = {
    "main": [("vol_rel", 1), ("beyond20_with", 1), ("edge_tests", 1), ("asia_rel", -1), ("h1_trend_with", 1), ("h4_trend_with", 1)],
    "london": [("vol_rel", 1), ("xm_with", 1), ("hour", -1)],
    "pdh": [("prev_close_pos_with", 1), ("d20_with", 1), ("day_used", -1)],
    "retest": [("fib_retrace", -1), ("vol_trend", -1), ("wick_back", 1)],
    "nr7": [("squeeze", -1), ("vol_trend", 1), ("d20_with", 1)],
    "fade": [("wick_back", 1), ("vol_rel", 1), ("h4_trend_with", 1), ("day_eff", -1)],
    "sar": [("speed8_with", 1), ("failed_break_with", 1)],
    "range": [("volrank", -1), ("h4_slope_abs", -1), ("edge_tests", 1)],
    "exhaust": [("vol_rank96", 1), ("rsi_div_with", 1), ("day_used", 1), ("run_against", 1)],
    "vwap": [("vol_rank96", 1), ("rsi_div_with", 1), ("day_used", 1), ("run_against", 1)],
    "bigrev": [("prev_close_pos_with", -1)],
    "bigcont": [("prev_close_pos_with", 1)],
    "trend": [("first_hour_with", 1), ("xm_with", 1), ("failed_fade_with", 1)],
    "nyaft": [("vol_rel", 1), ("fib_retrace", -1), ("d20_with", 1)],
    "scalp": [("vol_rel", 1), ("spread_atr", -1), ("stop_atr", 1)],
    "swing": [("adx", 1), ("d_hh_with", 1), ("d200_with", 1)],
    "dip": [("fib_retrace", -1), ("adx", 1), ("vol_trend", -1)],
}
# TRUST: how much each era's evidence counts. Recent markets count most; a market whose history in an era is only
# part of the day (Germany 40 and US 500 before 2025) counts half.
TRUST = {"2014-17": 0.25, "2018-19": 0.40, "A 2020-21": 0.70, "B 2024+": 1.00}
PARTIAL = {"GERMANY40": 0.5, "US500": 0.5}          # applied to every era except B 2024+
RECENT, PRIOR = ("B 2024+",), ("2014-17", "2018-19", "A 2020-21")
XREF = {"XAUUSD": [("EURUSD", 1), ("USDJPY", -1)], "EURUSD": [("USDJPY", -1), ("XAUUSD", 1)],
        "USDJPY": [("EURUSD", -1), ("US500", 1)], "US500": [("GERMANY40", 1), ("USDJPY", 1)],
        "GERMANY40": [("US500", 1)], "XTIUSD": [("US500", 1)]}
VOL_KINDS, TREND_KINDS = ("low-vol", "mid-vol", "high-vol"), ("choppy", "drifting", "trending")
T_ALL = tuple(k for k, _ in THEORY_SIGNALS) + SIG_ALL


def _kind_vol(v):
    return None if v is None else ("low-vol" if v < 0.34 else ("high-vol" if v > 0.66 else "mid-vol"))


def _kind_trend(e):
    return None if e is None else ("trending" if e >= A.REG_ER_TREND else ("choppy" if e <= A.REG_ER_CHOP else "drifting"))


def _cross_and_lanes(s, trades, series):
    """The reads that need other markets or other lanes."""
    import bisect as _b
    refs = [(series[r], sg) for r, sg in XREF.get(s, []) if r in series]
    order = sorted(trades, key=lambda t: t["t_in"])
    today, day, recent = [], None, []
    for t in order:
        if t["day"] != day:
            day, today = t["day"], []
        d = t["dir"]
        if t["lane"] != "control":
            t["lanes_same_today"] = float(sum(1 for o in today if o["dir"] == d and o["lane"] != t["lane"]))
            t["lanes_opp_today"] = float(sum(1 for o in today if o["dir"] == -d and o["lane"] != t["lane"]))
            lo = t["t_in"] - 4 * 3600
            recent = [o for o in recent if o["t_out"] > lo - 86400 * 3]
            ff = fb = 0.0
            for o in recent:
                if lo <= o["t_out"] <= t["t_in"] and o["dir"] == -d and o["r"] < 0:
                    if o["family"] == "reversal":
                        ff = 1.0
                    elif o["family"] == "breakout":
                        fb = 1.0
            t["failed_fade_with"], t["failed_break_with"] = ff, fb
            today.append(t)
            recent.append(t)
        vals = []
        for ser_, sg in refs:
            Tr, Cr, Ar = ser_[0], ser_[1], ser_[2]
            r = _b.bisect_right(Tr, t["t_in"] - 900 + 0.5) - 1
            if r >= 8 and t["t_in"] - 900 - Tr[r] <= 1800 and Tr[r] - Tr[r - 8] <= 3 * 3600 and Ar[r]:
                vals.append(sg * (Cr[r] - Cr[r - 8]) / Ar[r] * d)
        t["xm_with"] = mean(vals) if vals else None


# ---- REAL COSTS (switched on by the 'final' mode) ----
# The cautious model in asiabo_offline charges a flat allowance. Real cost = the broker's commission from the symbol
# sheets + the spread that bars.db actually recorded at the signal bar. Round-trip commission in basis points of price:
REAL_COMM_BP = {"EURUSD": 0.9, "USDJPY": 0.9, "XTIUSD": 0.8, "US500": 2.0, "GERMANY40": 2.0,
                "XAUUSD": 0.5}      # gold: $25 per million USD a side (broker symbol sheet, 2026-10-08) = 0.5 bp round trip
REAL_COSTS = False


def _real_cost_px(s, spec, price, spread):
    """Round-trip cost in price units: commission + the recorded spread (the model's own figure if no spread was recorded)."""
    if spread is None:
        return A._cost_px(spec, price)
    return REAL_COMM_BP.get(s, 1.0) / 1e4 * abs(price) + spread


def _reprice(per, specs):
    for s, ts in per.items():
        for t in ts:
            p, rd = t.get("entry"), t.get("stop_dist")
            if not p or not rd:
                continue
            model = A._cost_px(specs[s], p)
            real = _real_cost_px(s, specs[s], p, t.get("spread_px"))
            t["r_model"], t["cost_model_r"], t["cost_real_r"] = t["r"], model / rd, real / rd
            t["r"] = t["r"] + (model - real) / rd


def _prepare(rep, folder, old):
    """Loads both collect runs, computes every read, tags each trade with its kind of market. -> data, syms"""
    specs = dict((x["name"], x) for x in A.COLLECT_SYMBOLS)
    per, series, syms = {}, {}, []
    for s in A.HOUSE_SYMBOLS:
        both, kinds = [], {}
        for fol, is_old in ((folder, False), (old, True)):
            if not os.path.exists(os.path.join(fol, "trades_%s.csv" % s)):
                continue
            trades, days = load_market(fol, s)
            for t in trades:
                t["era"] = _era(t, is_old)
                t["hour"] = _f(t.get("hour"))
                for k in ("mae_r", "mfe_r"):
                    t[k] = _f(t.get(k))
            both += trades
            # episodes: unbroken runs of days of the same kind; numbered so they can be split odd / even
            for p in ("A", "B"):
                ep = {"v": [None, 0], "t": [None, 0]}
                for x in [x for x in days if x["period"] == p]:
                    kv, kt = _kind_vol(_f(x.get("volrank"))), _kind_trend(_f(x.get("er20")))
                    for key, kval in (("v", kv), ("t", kt)):
                        if kval != ep[key][0]:
                            ep[key] = [kval, ep[key][1] + 1]
                    kinds[x["day"]] = (kv, ep["v"][1] % 2, kt, ep["t"][1] % 2)
        if not both:
            continue
        print("computing chart reads: %s (%d trades) ..." % (s, len(both)))
        try:
            enrich_market(specs[s], both, series)
        except RuntimeError as e:
            rep.p("%s: skipped (%s)" % (s, str(e).splitlines()[0]))
            continue
        for t in both:
            kv, pv, kt, pt = kinds.get(t["day"], (None, 0, None, 0))
            t["k_vol"], t["p_vol"], t["k_trend"], t["p_trend"] = kv, pv, kt, pt
        per[s] = both
        syms.append(s)
    if REAL_COSTS:
        _reprice(per, specs)
    data = {}
    for s in syms:
        _cross_and_lanes(s, per[s], series)
        for t in per[s]:
            data.setdefault((s, t["era"]), []).append(t)
        A._write_csv(os.path.join(rep.dir, "trades_plus_%s.csv" % s),
                     [dict((k, t.get(k)) for k in ("symbol", "era", "family", "lane", "day", "entry_time", "dir", "r", "gross_r",
                                                   "k_vol", "k_trend") + T_ALL) for t in per[s]],
                     first=("symbol", "era", "family", "lane", "day", "entry_time", "dir", "r"))
    return data, syms, series


def _w(s, era):
    return TRUST[era] * (PARTIAL.get(s, 1.0) if era != "B 2024+" else 1.0)


def _wz(cells, eras=None):
    """Trust-weighted combined z over (market, era) cells: {(s, era): z} -> (z, cells, cells the same way as the result)."""
    num = den = 0.0
    zs = []
    for (s, era), z in cells.items():
        if eras is None or era in eras:
            w = _w(s, era)
            num += w * z
            den += w * w
            zs.append(z)
    if not zs:
        return None
    z = num / math.sqrt(den)
    return z, len(zs), sum(1 for x in zs if (x > 0) == (z > 0))


def _label(rec, pri):
    """rec / pri = trust-weighted z of the recent years and of everything before them."""
    r, p = (rec[0] if rec else None), (pri[0] if pri else None)
    if r is not None and abs(r) >= 2.0 and p is not None and abs(p) >= 2.0 and (r > 0) == (p > 0):
        return "DURABLE"
    if r is not None and abs(r) >= 2.5:
        return "RECENT-ONLY"
    if p is not None and abs(p) >= 2.5 and (r is None or abs(r) < 1.0 or (r > 0) != (p > 0)):
        return "EXPIRED"
    return ""


def run_theory(rep, folder):
    rep.p("")
    rep.p("=" * 100)
    rep.p("PART 6: THEORY   each lane's own reads, per kind of market, recent years trusted more")
    rep.p("=" * 100)
    old = _old_folder()
    rep.p("recent trades: %s" % folder)
    rep.p("old trades:    %s" % old)
    rep.p("TRUST: how much each era's evidence counts when eras are combined: " + ", ".join("%s %.0f%%" % (e, 100 * TRUST[e]) for e in ERAS) + ".")
    rep.p("       Germany 40 and US 500 count half before 2024 (their history then covers only part of the day).")
    rep.p("LABELS (z = standard errors from zero, after the trust weights):")
    rep.p("  DURABLE      2+ in 2024-26 AND 2+ the same way in the years before")
    rep.p("  RECENT-ONLY  2.5+ in 2024-26, no such support before: it has performed lately, nothing more. Smaller size, forward test.")
    rep.p("  EXPIRED      2.5+ in the years before, gone or reversed in 2024-26: not to be used")
    rep.p("KIND OF MARKET, from what was known on the day: volatility rank low / mid / high (third of its own last 120 days) and")
    rep.p("  20-day straightness choppy / drifting / trending (the bot's own thresholds). A kind comes and goes, so it shows up as")
    rep.p("  many separate EPISODES across the years; 'odd / even' splits a kind's episodes into two interleaved halves, so a")
    rep.p("  read found in one half is checked on other occurrences of the same kind of market.")
    rep.p("New reads in this part:")
    for k, txt in THEORY_SIGNALS:
        rep.p("  %-20s %s" % (k, txt))
    data, syms, _series = _prepare(rep, folder, old)
    if not syms:
        rep.p("no market could be read.")
        return
    total = sum(len(v) for v in data.values())
    rep.p("trades: %d | with volume reads: %d | with a kind of market: %d" % (
        total, sum(1 for v in data.values() for t in v if t.get("vol_rel") is not None),
        sum(1 for v in data.values() for t in v if t.get("k_vol") is not None)))
    lanes = [l for l in LANES_ORDER if any(t["lane"] == l for ts in data.values() for t in ts)]
    groups = [("lane", l) for l in lanes] + [("family", f) for f in A.FAMILIES]
    idx = defaultdict(lambda: defaultdict(list))
    for (s, era), ts in data.items():
        for t in ts:
            idx[("lane", t["lane"])][(s, era)].append(t)
            if t["family"] in A.FAMILIES:
                idx[("family", t["family"])][(s, era)].append(t)

    def cells(lists, key, field="r"):
        out = {}
        for ck, ts in lists.items():
            if len(ts) >= 2 * PERSIST_MIN_N:
                r = _hi_lo(ts, key, field)
                if r:
                    out[ck] = r[1]
        return out

    def best(ts, key, sign):
        v = _top_r(ts, key, sign)
        return "   -  " if v[0] is None else "%+.3f" % v[0]

    def verdict(lists, key):
        cz = cells(lists, key)
        al, rec, pri = _wz(cz), _wz(cz, RECENT), _wz(cz, PRIOR)
        return cz, al, rec, pri, _label(rec, pri)

    def gross_ok(lists, key, z):
        g = _wz(cells(lists, key, "gross_r"))
        return g is not None and abs(g[0]) >= 2.0 and (g[0] > 0) == (z > 0), (g[0] if g else None)
    f1 = lambda x: "   - " if x is None else "%+5.1f" % x[0]
    rows = []

    # ---- 6a: the sheet ----
    rep.p("")
    rep.p("-" * 100)
    rep.p("6a. THE SHEET   does each lane's theory predict its own good trades?")
    rep.p("-" * 100)
    rep.p("  says = what the theory predicted (written before the reads were computed). all / recent / before = trust-weighted z,")
    rep.p("  signed so that + means AS THE THEORY SAYS. best third = after-cost R of the third the theory favours, 2024-26 | before.")
    rep.p("  %-8s %-20s %-5s | %5s %6s %6s | %-15s | %-12s | %s" % ("lane", "read", "says", "all", "recent", "before", "best third R", "label", "theory"))
    n_as = n_ag = n_no = 0
    for lane in lanes:
        for key, sg in THEORY.get(lane, []):
            lists = idx[("lane", lane)]
            cz, al, rec, pri, lab = verdict(lists, key)
            if al is None:
                rep.p("  %-8s %-20s %-5s | too few trades" % (lane, key, "high" if sg > 0 else "low"))
                continue
            sal = al[0] * sg
            newt = [t for (s, e), ts in lists.items() if e in RECENT for t in ts]
            oldt = [t for (s, e), ts in lists.items() if e in PRIOR for t in ts]
            ok, _g = gross_ok(lists, key, al[0])
            if sal >= 2.0:
                th, n_as = "AS PREDICTED", n_as + 1
            elif sal <= -2.0:
                th, n_ag = "AGAINST THE THEORY", n_ag + 1
            else:
                th, n_no = "no effect", n_no + 1
            if abs(sal) >= 2.0 and not ok:
                th += " (cost arithmetic)"
            rep.p("  %-8s %-20s %-5s | %+5.1f %+6.1f %+6.1f | %s | %s | %-12s | %s" % (
                lane, key, "high" if sg > 0 else "low", sal, (rec[0] * sg) if rec else 0.0, (pri[0] * sg) if pri else 0.0,
                best(newt, key, sg), best(oldt, key, sg), lab, th))
            rows.append({"part": "6a", "kind": "lane", "name": lane, "read": key, "market_kind": "any", "predicted": sg,
                         "z_all": al[0], "z_recent": rec[0] if rec else None, "z_before": pri[0] if pri else None, "label": lab})
    rep.p("  %d predictions: %d as predicted, %d against the theory, %d no effect. By luck alone about %.1f would land on each side." % (
        n_as + n_ag + n_no, n_as, n_ag, n_no, (n_as + n_ag + n_no) * 0.023))

    # ---- 6b: every read, any kind of market ----
    rep.p("")
    rep.p("-" * 100)
    rep.p("6b. EVERY READ, TRUST-WEIGHTED   (any kind of market; per lane and per family)")
    rep.p("-" * 100)
    rep.p("  recent / before = trust-weighted z in 2024-26 and in the years before. 'cells' = (market, era) cells that agree with")
    rep.p("  the result / cells tested. best third = after-cost R of the favourable third, 2024-26 | before.")
    rep.p("  %-7s %-9s %-20s | %6s %6s | %-6s | %-9s | %-15s | %s" % ("", "", "read", "recent", "before", "cells", "better", "best third R", "label"))
    hits, tested, counts = [], 0, defaultdict(int)
    for g in groups:
        lists = idx[g]
        newt = [t for (s, e), ts in lists.items() if e in RECENT for t in ts]
        oldt = [t for (s, e), ts in lists.items() if e in PRIOR for t in ts]
        for key in T_ALL:
            cz, al, rec, pri, lab = verdict(lists, key)
            if al is None or rec is None or pri is None:
                continue
            tested += 1
            rows.append({"part": "6b", "kind": g[0], "name": g[1], "read": key, "market_kind": "any", "z_all": al[0],
                         "z_recent": rec[0], "z_before": pri[0], "label": lab})
            if not lab:
                continue
            lead = rec[0] if lab != "EXPIRED" else pri[0]
            ok, _g = gross_ok(lists, key, lead)
            if not ok:
                lab += " (cost arithmetic)"
            else:
                counts[lab] += 1
            sign = 1 if lead > 0 else -1
            hits.append((0 if lab == "DURABLE" else (1 if lab == "RECENT-ONLY" else (2 if lab == "EXPIRED" else 3)), -abs(lead),
                         "  %-7s %-9s %-20s | %+6.1f %+6.1f | %2d/%-3d | %-9s | %s | %s | %s" % (
                             g[0], g[1], key, rec[0], pri[0], al[2], al[1], "when HIGH" if sign > 0 else "when LOW",
                             best(newt, key, sign), best(oldt, key, sign), lab)))
    for _o, _z, line in sorted(hits):
        rep.p(line)
    rep.p("  %d lane-and-read pairs tested. By luck alone: about %.1f DURABLE, %.0f RECENT-ONLY, %.0f EXPIRED." % (
        tested, tested * 0.001, tested * 0.012, tested * 0.010))
    rep.p("  Found (not counting cost arithmetic): %d DURABLE, %d RECENT-ONLY, %d EXPIRED." % (
        counts["DURABLE"], counts["RECENT-ONLY"], counts["EXPIRED"]))

    # ---- 6c: per kind of market ----
    rep.p("")
    rep.p("-" * 100)
    rep.p("6c. READS THAT DECIDE THE OUTCOME IN ONE KIND OF MARKET   (and are confirmed on other occurrences of that kind)")
    rep.p("-" * 100)
    rep.p("  Listed when, INSIDE one kind of market, the read is DURABLE or RECENT-ONLY, both halves of that kind's episodes")
    rep.p("  agree (1.5+ each, the same way), and no other kind on the same axis shows the same thing (otherwise it is a general")
    rep.p("  read and belongs in 6b). 'other kinds' = the read's trust-weighted z in the other two kinds: near zero or the other")
    rep.p("  sign is what makes this a WHEN, not just a WHAT.")
    rep.p("  %-7s %-9s %-20s %-9s | %6s %6s | %-11s | %-13s | %-9s | %-15s | %s" % (
        "", "", "read", "kind", "recent", "before", "odd / even", "other kinds", "better", "best third R", "label"))
    listed, tested_c, lines = 0, 0, []
    for g in groups:
        for axis, kinds_, kf, pf in (("vol", VOL_KINDS, "k_vol", "p_vol"), ("trend", TREND_KINDS, "k_trend", "p_trend")):
            sub = dict((k, defaultdict(list)) for k in kinds_)
            par = dict(((k, q), defaultdict(list)) for k in kinds_ for q in (0, 1))
            for ck, ts in idx[g].items():
                for t in ts:
                    k = t.get(kf)
                    if k is not None:
                        sub[k][ck].append(t)
                        par[(k, t[pf])][ck].append(t)
            for key in T_ALL:
                res = {}
                for k in kinds_:
                    cz = cells(sub[k], key)
                    res[k] = (_wz(cz), _wz(cz, RECENT), _wz(cz, PRIOR))
                for k in kinds_:
                    al, rec, pri = res[k]
                    if al is None or rec is None:
                        continue
                    tested_c += 1
                    lab = _label(rec, pri)
                    rows.append({"part": "6c", "kind": g[0], "name": g[1], "read": key, "market_kind": k, "z_all": al[0],
                                 "z_recent": rec[0], "z_before": pri[0] if pri else None, "label": lab})
                    if lab not in ("DURABLE", "RECENT-ONLY"):
                        continue
                    sign = 1 if rec[0] > 0 else -1
                    zo, ze = _wz(cells(par[(k, 1)], key)), _wz(cells(par[(k, 0)], key))
                    if zo is None or ze is None or min(zo[0] * sign, ze[0] * sign) < 1.5:
                        continue
                    others = [res[o][0] for o in kinds_ if o != k]
                    if any(o is not None and o[0] * sign >= 2.0 for o in others):
                        continue
                    ok, _g = gross_ok(sub[k], key, rec[0])
                    if not ok:
                        continue
                    newt = [t for (s, e), ts in sub[k].items() if e in RECENT for t in ts]
                    oldt = [t for (s, e), ts in sub[k].items() if e in PRIOR for t in ts]
                    listed += 1
                    lines.append((0 if lab == "DURABLE" else 1, -abs(rec[0]),
                                  "  %-7s %-9s %-20s %-9s | %+6.1f %s | %+5.1f/%+5.1f | %s / %s | %-9s | %s | %s | %s" % (
                                      g[0], g[1], key, k, rec[0], (" " + f1(pri)), zo[0], ze[0], f1(others[0]), f1(others[1]),
                                      "when HIGH" if sign > 0 else "when LOW", best(newt, key, sign), best(oldt, key, sign), lab)))
    for _o, _z, line in sorted(lines):
        rep.p(line)
    rep.p("  %d lane-read-kind combinations tested; by luck alone at most about %.0f would be listed. Listed: %d." % (
        tested_c, tested_c * 0.012 * 0.25, listed))
    rep.p("  The odd / even halves use the same trades as the label, so they do not make a listing independent proof: they")
    rep.p("  only show the effect is spread over many separate occurrences of that kind of market, not one stretch.")
    A._write_csv(os.path.join(rep.dir, "theory_all.csv"), rows, first=("part", "kind", "name", "read", "market_kind"))
    rep.p("  every test: theory_all.csv | every trade with all its reads and its kind of market: trades_plus_<market>.csv")


# ======================================================================================================
# PART 7: PROBE   what does price do AFTER the moments the reads point at, free of any lane's stop and target?
# ======================================================================================================
# FROZEN 2026-10-07, before any of this was measured. Each moment: which lane event, and which way to look.
BAD_SIGNS = {      # (read, 'yes' / 'no' / +1 = top third / -1 = bottom third); thirds per market and lane, from before 2024
    "reversal": [("day_pos_with", -1), ("turning", "no"), ("room_r", 1), ("edge_tests", -1), ("er60", -1)],
    "breakout": [("turning", "yes"), ("failed_fade_with", "no"), ("room_r", 1)],
}
GOOD_SIGNS = {"momentum": [("failed_fade_with", "yes"), ("day_eff", 1), ("open_move_with", 1), ("h1_trend_with", 1), ("stretch_atr", 1)]}
PROBES = [
    ("1 bad fade", "a fade fires with 4+ of its 5 bad signs", "go WITH the move it is fading"),
    ("2 fade stopped", "a fade lane's trade is stopped out", "go WITH the move that stopped it"),
    ("3 clean breakout", "a breakout fires with none of its 3 bad signs", "go WITH the breakout"),
    ("4 bad breakout", "a breakout fires with all 3 bad signs", "go AGAINST the breakout"),
    ("5 strong momentum", "a momentum trade fires with all 5 good signs", "go WITH it"),
    ("base: any fade", "every fade entry (the comparison for 1)", "go AGAINST the fade"),
    ("base: any breakout", "every breakout entry (the comparison for 3 and 4)", "go WITH the breakout"),
    ("base: any momentum", "every momentum entry (the comparison for 5)", "go WITH it"),
    ("base: random", "the control lane's random entries", "its random direction"),
]
PROBE_GAP_BARS = 8                      # one moment per market, kind and direction every 2 hours (later ones are the same move)
PROBE_HORIZONS = ((4, "1h"), (8, "2h"), (16, "4h"), (32, "8h"))
BRACKETS = [(st, tg, hz) for hz in (16, 32) for st in (1.0, 2.0) for tg in (1.0, 2.0, None)]   # stop in ATR, target in R, bars


def _sign_score(t, conds, cuts):
    m = 0
    for k, h in conds:
        v = t.get(k)
        if v is None:
            return None
        if h == "yes":
            m += v > 0
        elif h == "no":
            m += v == 0
        else:
            c = cuts.get((k, t["symbol"], t["lane"]))
            if c is None:
                return None
            m += (v >= c[1]) if h > 0 else (v <= c[0])
    return m


PROBE_HORIZONS_LONG = ((16, "4h"), (32, "8h"), (64, "16h"), (96, "24h"), (192, "48h"))
BRACKETS_LONG = [(3.0, None, 32), (5.0, None, 32), (3.0, None, 96), (5.0, None, 96), (8.0, None, 96), (5.0, 2.0, 96),
                 (5.0, None, 192), (8.0, None, 192), (8.0, 2.0, 192)]
PROBE_CAP = 25.0                        # a move bigger than this many ATR is a data glitch (oil in April 2020): capped


def _swap_nights(t0, t1):
    """Nights a position open from t0 to t1 pays swap for (20:59 UTC on weekdays, Wednesday counts three)."""
    n = 0
    for day in range(int(t0 // 86400), int(t1 // 86400) + 1):
        ts = day * 86400 + A.SWAP_HOUR * 3600 + A.SWAP_MINUTE * 60
        wd = (day + 3) % 7
        if t0 < ts <= t1 and wd < 5:
            n += 3 if wd == A.SWAP_TRIPLE_WEEKDAY else 1
    return n


def run_probe(rep, folder, long_=False):
    import bisect as _b
    horizons = PROBE_HORIZONS_LONG if long_ else PROBE_HORIZONS
    brackets = BRACKETS_LONG if long_ else BRACKETS
    max_bars = max(h for h, _ in horizons)
    rep.p("")
    rep.p("=" * 100)
    rep.p("PART 7: PROBE   what price does after the moments the reads point at (no lane's stop or target involved)")
    rep.p("=" * 100)
    old = _old_folder()
    rep.p("The lanes' own stops and targets cost 0.06-0.17R a trade, about as much as the reads are worth. So this part")
    rep.p("drops them: it takes each MOMENT, enters at the close of that bar in the stated direction, and measures the raw move.")
    rep.p("Moments (fixed before measuring):")
    for name, what, way in PROBES:
        rep.p("  %-20s %s -> %s" % (name, what, way))
    rep.p("bad signs of a fade: day_pos_with low, trends agree, far target, few tests of the level, choppy last 60 days.")
    rep.p("bad signs of a breakout: trends disagree, no failed fade against it, far target.")
    rep.p("good signs of a momentum trade: a failed fade against it, straight day, with the day's move, with the 1-hour trend, stretched.")
    rep.p("One moment per market, kind and direction every %d hours. ATR = M15 ATR(14) at the moment." % (PROBE_GAP_BARS // 4))
    if long_:
        rep.p("LONG HOLDS: hours here are TRADING hours (bars), so 24h is about one trading day and crosses the nightly break;")
        rep.p("weekends are crossed too. Swap is charged for every night held (your sheet's figure, scaled to the price then).")
    rep.p("COSTS: %s." % ("REAL = your broker's commission + the spread bars.db recorded at that bar (gold's commission is assumed)"
                          if REAL_COSTS else "the cautious model"))
    rep.p("For 'fade stopped' the entry is the close of the M15 bar in which the stop was hit, so the stop-out move itself is")
    rep.p("already over and is not counted.")
    data, syms, series = _prepare(rep, folder, old)
    if not syms:
        rep.p("no market could be read.")
        return
    specs = dict((x["name"], x) for x in A.COLLECT_SYMBOLS)
    allt = [t for ts in data.values() for t in ts]
    cuts = {}
    for conds in list(BAD_SIGNS.values()) + list(GOOD_SIGNS.values()):
        for k, h in conds:
            if h in (1, -1):
                grp = defaultdict(list)
                for t in allt:
                    if t["era"] != "B 2024+" and t.get(k) is not None:
                        grp[(k, t["symbol"], t["lane"])].append(t[k])
                for key, v in grp.items():
                    if len(v) >= 45:
                        v.sort()
                        cuts[key] = (v[len(v) // 3], v[2 * len(v) // 3])
    events = defaultdict(list)          # (probe, symbol) -> [(time, direction)]
    for t in allt:
        s, d, fam = t["symbol"], int(t["dir"]), t["family"]
        if fam == "reversal":
            events[("base: any fade", s)].append((t["t_in"], -d))
            sc = _sign_score(t, BAD_SIGNS["reversal"], cuts)
            if sc is not None and sc >= 4:
                events[("1 bad fade", s)].append((t["t_in"], -d))
            if str(t.get("reason", "")).lower().startswith("stop") and t["r"] < 0:
                # the stop happens INSIDE a bar: enter at the close of THAT bar, never the one before it
                events[("2 fade stopped", s)].append((float(int(t["t_out"] // 900) * 900 + 900), -d))
        elif fam == "breakout":
            events[("base: any breakout", s)].append((t["t_in"], d))
            sc = _sign_score(t, BAD_SIGNS["breakout"], cuts)
            if sc == 0:
                events[("3 clean breakout", s)].append((t["t_in"], d))
            elif sc == 3:
                events[("4 bad breakout", s)].append((t["t_in"], -d))
        elif fam == "momentum":
            events[("base: any momentum", s)].append((t["t_in"], d))
            if _sign_score(t, GOOD_SIGNS["momentum"], cuts) == 5:
                events[("5 strong momentum", s)].append((t["t_in"], d))
        elif fam == "control":
            events[("base: random", s)].append((t["t_in"], d))
    # measure
    res = defaultdict(lambda: defaultdict(list))        # (probe, era) -> measure -> values
    rows = []
    for (probe, s), evs in events.items():
        T, C, atr, Hh, L, S_ = series[s]
        spec = specs[s]
        ref_px = C[-1]
        evs.sort()
        last = {}
        for te, d in evs:
            i = _b.bisect_right(T, te - 900 + 0.5) - 1
            if i < 20 or te - (T[i] + 900) > 900 or atr[i] is None or not atr[i]:
                continue
            if i - last.get(d, -10 ** 9) < PROBE_GAP_BARS:
                continue
            last[d] = i
            p, a = C[i], atr[i]
            era = "recent" if T[i] >= A.epoch_of(A.SEAL_END) else "before"
            R_ = res[(probe, era)]
            cost = (_real_cost_px(s, spec, p, S_[i]) if REAL_COSTS else A._cost_px(spec, p)) / a
            R_["cost_atr"].append(cost)
            M_ = res[(probe, era, s)]
            M_["n"].append(1.0)
            # the bars after the moment: unbroken for short holds; long holds may cross nights and weekends, not holes
            max_gap = 3.5 * 86400 if long_ else 1800
            j, path = i + 1, []
            while j < len(T) and j - i <= max_bars and T[j] - T[j - 1] <= max_gap:
                path.append(j)
                j += 1
            swap_unit = (spec["swap_long"] if d > 0 else spec["swap_short"]) * (p / ref_px) / a    # per night, in ATR
            for h, lab in horizons:
                if len(path) >= h:
                    mv = max(-PROBE_CAP, min(PROBE_CAP, (C[path[h - 1]] - p) / a * d))
                    R_["ret_" + lab].append(mv)
                    if long_:
                        net = mv - cost + swap_unit * _swap_nights(T[i] + 900, T[path[h - 1]] + 900)
                        R_["net_" + lab].append(net)
                        M_["net_" + lab].append(net)
            if len(path) >= 16:
                seg = path[:16]
                hi, lo = max(Hh[k] for k in seg), min(L[k] for k in seg)
                R_["mfe_4h"].append(min(PROBE_CAP, ((hi - p) if d > 0 else (p - lo)) / a))
                R_["mae_4h"].append(min(PROBE_CAP, ((p - lo) if d > 0 else (hi - p)) / a))
            for st, tg, hz in brackets:
                if not path:
                    continue
                stop = p - d * st * a
                target = None if tg is None else p + d * tg * st * a
                out, kx = None, path[min(hz, len(path)) - 1]
                for k in path[:hz]:
                    if (L[k] <= stop) if d > 0 else (Hh[k] >= stop):
                        out, kx = -1.0, k                # stop first when a bar touches both: the cautious reading
                        break
                    if target is not None and ((Hh[k] >= target) if d > 0 else (L[k] <= target)):
                        out, kx = tg, k
                        break
                if out is None:
                    out = (C[kx] - p) * d / (st * a)
                swp = swap_unit * _swap_nights(T[i] + 900, T[kx] + 900) / st if long_ else 0.0
                R_[("br", st, tg, hz)].append(out - cost / st + swp)
    order = [p[0] for p in PROBES]
    rep.p("")
    rep.p("-" * 100)
    rep.p("7a. THE RAW MOVE   (in ATR, in the stated direction; + = price went the way the moment points)")
    rep.p("-" * 100)
    rep.p("  n = moments. 1h..8h = average move after that long, with its z (standard errors from zero) under it. best / worst")
    rep.p("  = the average furthest point for and against within 4 hours. cost = one round trip in ATR: a move has to beat it.")
    for era, lab in (("recent", "2024-26"), ("before", "2014-21")):
        rep.p("  %s" % lab)
        rep.p("    %-20s %6s | %s | %6s %6s | %5s" % ("moment", "n", " ".join("%7s" % hl for _h, hl in horizons), "best", "worst", "cost"))
        for probe in order:
            R_ = res.get((probe, era))
            if not R_ or len(R_["cost_atr"]) < 30:
                continue
            cells, zs = [], []
            for _h, hl in horizons:
                xs = R_["ret_" + hl]
                cells.append("%+7.3f" % mean(xs) if len(xs) >= 30 else "   -   ")
                zs.append("(%+5.1f)" % (mean(xs) / se(xs)) if len(xs) >= 30 and se(xs) > 0 else "   -   ")
            rep.p("    %-20s %6d | %s | %6.2f %6.2f | %5.2f" % (probe, len(R_["cost_atr"]), " ".join(cells),
                                                          mean(R_["mfe_4h"]) if R_["mfe_4h"] else 0, mean(R_["mae_4h"]) if R_["mae_4h"] else 0,
                                                          mean(R_["cost_atr"])))
            rep.p("    %-20s %6s | %s |" % ("", "", " ".join(zs)))
            if long_:
                nets = []
                for _h, hl in horizons:
                    xs = R_["net_" + hl]
                    nets.append("%+7.3f" % mean(xs) if len(xs) >= 30 else "   -   ")
                rep.p("    %-20s %6s | %s |   <- AFTER cost and swap, no stop" % ("", "", " ".join(nets)))
            for _h, hl in horizons:
                xs = R_["ret_" + hl]
                if len(xs) >= 30:
                    rows.append({"part": "move", "moment": probe, "era": lab, "what": hl, "value": mean(xs), "z": mean(xs) / se(xs) if se(xs) > 0 else 0, "n": len(xs)})
    rep.p("  Read: a moment is worth something if its move is clearly above zero (z of 2+) in BOTH periods, above its 'base' line")
    rep.p("  (otherwise the bad / good signs added nothing), and bigger than the cost column.")
    rep.p("")
    rep.p("-" * 100)
    rep.p("7b. IS THERE A STOP AND TARGET THAT PAYS?   (R per trade AFTER costs; enter at the moment's bar close)")
    rep.p("-" * 100)
    if long_:
        rep.p("  Nine WIDE structures, fixed in advance: stop 3, 5 or 8 ATR (outside the usual 4-hour noise); no target (two have")
        rep.p("  a 2R target); out at the stop, the target, or after 8, 24 or 48 trading hours. Swap is charged for nights held.")
    else:
        rep.p("  Twelve plain structures, fixed in advance: stop 1 or 2 ATR; target 1R, 2R or none; out at the stop, the target, or")
        rep.p("  after 4 or 8 hours, whichever comes first. A bar that touches stop and target counts as the stop.")
    hdr = " ".join("%-13s" % ("%gATR/%s/%dh" % (st, ("%gR" % tg) if tg else "time", hz // 4)) for st, tg, hz in brackets)
    for era, lab in (("recent", "2024-26"), ("before", "2014-21")):
        rep.p("  %s   (stop / target / time limit)" % lab)
        rep.p("    %-20s %s" % ("moment", hdr))
        for probe in order:
            R_ = res.get((probe, era))
            if not R_ or len(R_["cost_atr"]) < 30:
                continue
            cells = []
            for b in brackets:
                xs = R_[("br",) + b]
                cells.append("%-13s" % ("%+.3f (%+.1f)" % (mean(xs), mean(xs) / se(xs)) if len(xs) >= 30 and se(xs) > 0 else "-"))
                if len(xs) >= 30:
                    rows.append({"part": "structure", "moment": probe, "era": lab, "what": "%gATR/%s/%dh" % (b[0], ("%gR" % b[1]) if b[1] else "time", b[2] // 4),
                                 "value": mean(xs), "z": mean(xs) / se(xs) if se(xs) > 0 else 0, "n": len(xs)})
            rep.p("    %-20s %s" % (probe, " ".join(cells)))
    rep.p("  Each cell: average R after costs (z). A structure is a candidate only if it is above zero in BOTH periods for the")
    rep.p("  same moment. There are 12 structures per moment, so one positive cell alone means little: look for a whole row,")
    rep.p("  or a whole column pattern (all the wide stops, all the long holds), that is positive in both.")
    if long_:
        rep.p("")
        rep.p("-" * 100)
        rep.p("7c. BY MARKET   (average move in ATR AFTER cost and swap, no stop; n = moments)")
        rep.p("-" * 100)
        for probe in ("3 clean breakout", "1 bad fade", "base: random"):
            rep.p("  %s" % probe)
            rep.p("    %-10s | %-44s | %-44s" % ("market", "2024-26:  n     8h     24h     48h", "2014-21:  n     8h     24h     48h"))
            for s in syms:
                parts = []
                for era in ("recent", "before"):
                    M_ = res.get((probe, era, s))
                    if not M_ or len(M_["n"]) < 20:
                        parts.append("%-44s" % "-")
                        continue
                    parts.append("%-44s" % ("%6d %s" % (len(M_["n"]), " ".join(
                        ("%+6.2f(%+4.1f)" % (mean(M_["net_" + hl]), mean(M_["net_" + hl]) / se(M_["net_" + hl]))) if len(M_["net_" + hl]) >= 20 and se(M_["net_" + hl]) > 0 else "      -     "
                        for hl in ("8h", "24h", "48h")))))
                rep.p("    %-10s | %s | %s" % (s, parts[0], parts[1]))
        rep.p("  Read: a real effect shows on most markets in both periods, not on one. (z in brackets.)")
    A._write_csv(os.path.join(rep.dir, "probe.csv"), rows, first=("part", "moment", "era", "what"))
    rep.p("  every number: probe.csv")
    return data, syms


def run_realcost(rep, data, syms):
    rep.p("")
    rep.p("=" * 100)
    rep.p("PART 8: REAL COSTS   the lanes re-priced with your broker's commission and the spread recorded at each entry")
    rep.p("=" * 100)
    rep.p("Same trades, same entries and exits; only the cost charged changes. Gold's commission is an assumption (0.9 bp")
    rep.p("round trip, the FX rate on your sheets). Slippage on stop orders is not modelled in either column.")
    allt = [t for ts in data.values() for t in ts if t.get("r_model") is not None]
    rec = lambda t: t["era"] == "B 2024+"
    rep.p("")
    rep.p("  COST PER TRADE, in R (median):   model -> real")
    for s in syms:
        a = sorted(t["cost_model_r"] for t in allt if t["symbol"] == s and rec(t))
        b = sorted(t["cost_real_r"] for t in allt if t["symbol"] == s and rec(t))
        if a:
            rep.p("    %-10s %.3f -> %.3f   (2024-26)" % (s, a[len(a) // 2], b[len(b) // 2]))
    rep.p("")
    rep.p("  R PER TRADE:   %-9s | %-33s | %-33s" % ("", "2024-26: model -> real (n)", "2014-21: model -> real (n)"))

    def line(name, pick):
        cells = []
        for sel in (rec, lambda t: not rec(t)):
            ts = [t for t in allt if pick(t) and sel(t)]
            cells.append("%-33s" % ("%+.3f -> %+.3f +/-%.3f (%d)" % (mean([t["r_model"] for t in ts]), mean([t["r"] for t in ts]), se([t["r"] for t in ts]), len(ts)) if len(ts) >= 30 else "-"))
        rep.p("    %-22s | %s | %s" % (name, cells[0], cells[1]))
    for fam in A.FAMILIES:
        line("family " + fam, lambda t, fam=fam: t["family"] == fam)
    for l in LANES_ORDER:
        if any(t["lane"] == l for t in allt):
            line("lane " + l, lambda t, l=l: t["lane"] == l)
    for s in syms:
        line("breakouts on " + s, lambda t, s=s: t["family"] == "breakout" and t["symbol"] == s)
    # the breakout filter, with real costs
    cuts = {}
    grp = defaultdict(list)
    for t in allt:
        if not rec(t) and t.get("room_r") is not None:
            grp[("room_r", t["symbol"], t["lane"])].append(t["room_r"])
    for k, v in grp.items():
        if len(v) >= 45:
            v.sort()
            cuts[k] = (v[len(v) // 3], v[2 * len(v) // 3])
    rep.p("")
    rep.p("  THE BREAKOUT FILTER with real costs   (bad signs: trends disagree, no failed fade against it, far target)")
    rep.p("    %-10s %-9s | %-30s | %-30s" % ("lanes", "bad signs", "2024-26: R +/-se (n)", "2014-21: R +/-se (n)"))
    for name, pick in (("all", lambda t: t["family"] == "breakout"), ("main", lambda t: t["lane"] == "main"),
                       ("retest", lambda t: t["lane"] == "retest"), ("pdh", lambda t: t["lane"] == "pdh"),
                       ("london", lambda t: t["lane"] == "london")):
        by = defaultdict(lambda: ([], []))
        for t in allt:
            if pick(t):
                sc = _sign_score(t, BAD_SIGNS["breakout"], cuts)
                if sc is not None:
                    by[sc][0 if rec(t) else 1].append(t["r"])
                    by["0-1" if sc <= 1 else "2-3"][0 if rec(t) else 1].append(t["r"])
        for sc in (0, 1, 2, 3, "0-1", "2-3"):
            a, b = by[sc]
            f = lambda xs: "%-30s" % ("%+.3f +/-%.3f (%d)" % (mean(xs), se(xs), len(xs)) if len(xs) >= 20 else "-")
            rep.p("    %-10s %-9s | %s | %s%s" % (name, sc, f(a), f(b), "   <- what the filter keeps" if sc == "0-1" else ""))
    rep.p("  Read: the filter is worth building if the '0-1' row is above zero in BOTH periods for a lane, by more than its")
    rep.p("  standard error. Above zero in one period only is a maybe.")


def run_final(rep, folder):
    global REAL_COSTS
    REAL_COSTS = True
    rep.p("")
    rep.p("FINAL RUN: real costs everywhere below, and the probe extended to holds of 16, 24 and 48 trading hours.")
    out = run_probe(rep, folder, long_=True)
    if out:
        run_realcost(rep, out[0], out[1])


# ======================================================================================================
# ======================================================================================================
# PART 9: POWER   fix the power gap first: the audit's rebuild list, measured against a random direction
# ======================================================================================================
# What the audit (Claude + four outside AIs, 2026-10-08) agreed on, and what this part measures:
#   A. EXIT TEST     every collect / oldcollect trade, SAME entry, re-exited six ways: as recorded (fixed target),
#                    at the market's session close, after 24h, after 48h, a trail at the trade's own risk distance
#                    (48h cap), and a 5-day chandelier trail (1 daily ATR behind the best close).
#   B. REBUILT LANES the standard versions, with stop-order entries, daily-ATR / structural stops, real sessions:
#        main2    overnight box -> stop orders on its edges in the FIRST 3 HOURS after the open only
#        orb30/60 a real opening range (first 30 / 60 minutes of the London / Xetra / cash open), stop orders
#        pdh2     stop orders on yesterday's high / low, stop just beyond the broken level (or the old mid)
#        retest2  after a main2 break, a limit back at the broken edge (within 2 hours), stop just beyond it
#        trend2   "Beat the Market" style: noise boundary from the open, checked every 30 min, VWAP/boundary
#                 trail, flat at the close, may re-enter
#        gao      first half hour of the session -> trade the last half hour in that direction
#        range2   Asian-hours range fade only (00:00-08:00 London), target the middle, out by the London open
#        swing2   20-day Donchian on DAILY bars (close or stop-order entry), 2N stop, 10-day exit, + pyramiding
#        rsi2     Connors: close above the 200-day average, RSI(2) < 10 -> long, out on a close above the 5-day
#                 average (mirror for shorts, reported apart); dipx = our old dip entry with trailing exits
#   CONTROL  every trade is also run in the OPPOSITE direction with the mirrored stop / target / exit. The average
#            of the two is what a coin flip would have made with the same timing, stop, exit and costs, so
#            EDGE = trade - that average = what the DIRECTION call was worth. A trade can be positive and still have
#            no edge (the market drifted), and a lane can be negative with an edge (costs too big for it).
# Units: N / D = daily ATR(20) on daily bars that end at 17:00 New York (the FX day). Every stop is in daily ATR or a
# price structure, never M15 ATR. Exits are checked on M15 bars: a stop and a target inside the same bar = the stop
# (cautious); a stop-order fill and the stop inside the fill bar = stopped (cautious). Costs: REAL (commission +
# recorded spread at the entry bar, swap for every night held). A trade that is open across an unexplained hole in
# the data is dropped. Nothing here was tuned: every number is the textbook one or a round default, fixed before
# any result.
POWER_ERAS = ["2014-17", "2018-19", "A 2020-21", "B 2024+"]
POWER_OLD = ("2014-17", "2018-19", "A 2020-21")
P_EXITS = ("close", "24h", "48h", "trail", "5d", "2R")
P_EXITS_A = ("orig", "close", "24h", "48h", "trail", "5d")
P_EXIT_TEXT = {"orig": "as recorded (the lane's own target / clock)", "close": "no target, out at the session close",
               "24h": "no target, out after 24 trading hours", "48h": "no target, out after 48 trading hours",
               "trail": "stop trails at the trade's own risk distance behind the best close (48h cap)",
               "5d": "chandelier: 1 daily ATR behind the best close, up to 5 trading days",
               "2R": "the old way: 2R target, else out at the session close",
               "own": "the lane's own exit rule"}
# market sessions, LOCAL times: (zone, open hh:mm, close hh:mm). Gold and FX: London open, out at 17:00 New York (end
# of the FX day). Germany 40: Xetra 09:00-17:30 Berlin = 08:00-16:30 London. US 500: cash 09:30-16:00 New York.
# WTI: the pit session 09:00-14:30 New York.
P_SESSION = {"XAUUSD": ("lon", 8 * 60, None), "EURUSD": ("lon", 8 * 60, None), "USDJPY": ("lon", 8 * 60, None),
             "GERMANY40": ("lon", 8 * 60, 16 * 60 + 30), "US500": ("ny", 9 * 60 + 30, 16 * 60),
             "XTIUSD": ("ny", 9 * 60, 14 * 60 + 30)}
P_HOME = {"orb30": ("US500", "GERMANY40"), "orb60": ("US500", "GERMANY40"), "trend2": ("US500",), "gao": ("US500",),
          "rsi2": ("US500", "GERMANY40"), "range2": ("EURUSD", "USDJPY"), "main2": ("XAUUSD", "EURUSD", "USDJPY")}
P_MIN_N = 20
# the exit each rebuilt lane is judged on, fixed BEFORE any result (the textbook one for its family)
P_PRIMARY = {"main2": ("box", "close"), "retest2": ("0.25D", "close"), "orb30": ("range", "close"),
             "orb60": ("range", "close"), "pdh2": ("lvl0.25D", "5d"), "trend2": ("own", "own"), "gao": ("0.25D", "close"),
             "range2": ("asia", "own"), "swing2": ("stop", "own"), "rsi2": ("long", "own"), "dipx": ("pullback", "5d"),
             "inside": ("mid", "5d"), "turtle55": ("55/20", "own"), "dip3": ("long", "own")}
P_MAX_GAP = 4 * 86400                  # a jump in the bars longer than this ends a walk unfinished (trade dropped)


def _p_era(t):
    y = int(time.gmtime(t).tm_year)
    if y < 2014:
        return None
    if y <= 2017:
        return "2014-17"
    if y <= 2019:
        return "2018-19"
    if y <= 2021:
        return "A 2020-21"
    return "B 2024+" if y >= 2024 else None


class PMarket(object):
    """One market's M15 bars plus everything the power lanes need: local clocks, sessions, daily bars and reads."""

    def __init__(self, spec):
        self.s, self.spec = spec["name"], spec
        T, O, H, L, C, V, S, _ = _m15_full(spec)
        self.T, self.O, self.H, self.L, self.C, self.V, self.S = T, O, H, L, C, V, S
        n = self.n = len(T)
        self.dq = A.DataQuality(spec)
        zone, self.open_min, close_min = P_SESSION[self.s]
        # local minute of day (London or New York) and the FX day (ends 17:00 New York) of every bar
        nyoff, lonoff = {}, {}
        self.loc, dkey = [0] * n, [0] * n
        nyl = [0] * n
        for i in range(n):
            t = T[i]
            k = int(t // 86400)
            if k not in nyoff:
                nyoff[k] = A._clock_shift(A.CLOCK_NY, t) - A.NY_CLOCK_SHIFT * 3600.0
                lonoff[k] = A._clock_shift(A.CLOCK_EU, t) + 3600.0
            ny = t + nyoff[k]
            nyl[i] = int(ny % 86400 // 60)
            self.loc[i] = nyl[i] if zone == "ny" else int((t + lonoff[k]) % 86400 // 60)
            dkey[i] = int((ny + 7 * 3600) // 86400)          # the FX day: 17:00 New York -> 17:00 New York
        self.close_min = close_min if close_min is not None else 17 * 60
        self.close_zone_ny = (close_min is None) or zone == "ny"
        cl_loc = nyl if self.close_zone_ny else self.loc
        # close bars: the bar that ENDS at the session close; next_close[i] = first close bar at or after i
        # the close bar = the LAST bar that ends at or before the close, within the hour before it. (Brokers often stop
        # quoting FX a few minutes before 17:00 New York, so the 16:45 bar can be missing: then 16:30 is the close bar.)
        cm = self.close_min
        isc = [False] * n
        for i in range(n):
            e = cl_loc[i] + 15
            if not (cm - 60 < e <= cm):
                continue
            if i + 1 >= n:
                isc[i] = True
                continue
            e2 = cl_loc[i + 1] + 15
            if T[i + 1] - T[i] > 3600 or not (cm - 60 < e2 <= cm) or e2 <= e:
                isc[i] = True
        self.next_close = [None] * n
        nxt = None
        for i in range(n - 1, -1, -1):
            if isc[i]:
                nxt = i
            self.next_close[i] = nxt
        # daily bars
        self.di = [0] * n
        D = []                                              # [key, i0, i1, o, h, l, c]
        for i in range(n):
            if not D or D[-1][0] != dkey[i]:
                D.append([dkey[i], i, i, O[i], H[i], L[i], C[i]])
            else:
                d = D[-1]
                d[2] = i
                d[4] = max(d[4], H[i]); d[5] = min(d[5], L[i]); d[6] = C[i]
            self.di[i] = len(D) - 1
        self.D = D
        m = len(D)
        seg, s0 = [0] * m, 0
        for j in range(1, m):
            if D[j][0] - D[j - 1][0] > SEG_GAP_DAYS:
                s0 = j
            seg[j] = s0
        self.seg = seg
        hi = [d[4] for d in D]; lo = [d[5] for d in D]; cl = [d[6] for d in D]
        tr = [hi[0] - lo[0]] + [max(hi[j] - lo[j], abs(hi[j] - cl[j - 1]), abs(lo[j] - cl[j - 1])) for j in range(1, m)]
        self.N = [None] * m             # ATR(20) of the 20 days BEFORE day j (known at day j's start)
        for j in range(m):
            if j - 20 >= seg[j]:
                self.N[j] = sum(tr[j - 20:j]) / 20.0
        cs = _prefix(cl)

        def sma(j, w):                  # over the w completed days ending at day j (inclusive)
            return (cs[j + 1] - cs[j + 1 - w]) / w if j + 1 - w >= seg[j] else None
        self.sma = sma
        # RSI(2), Wilder
        self.rsi2 = [None] * m
        ag = al = None
        for j in range(1, m):
            if seg[j] == j:
                ag = al = None
                continue
            ch = cl[j] - cl[j - 1]
            g, l_ = max(ch, 0.0), max(-ch, 0.0)
            if ag is None:
                ag, al = g, l_
            else:
                ag, al = (ag + g) / 2.0, (al + l_) / 2.0
            if j - 3 >= seg[j]:
                self.rsi2[j] = 100.0 if al == 0 else 100.0 - 100.0 / (1.0 + ag / al)
        self.hi, self.lo, self.cl = hi, lo, cl
        # ---- daily reads, all known at the START of day j (from completed days only) ----
        self.f = [None] * m
        Nps = [0.0]
        for j in range(m):
            Nps.append(Nps[-1] + (self.N[j] or 0.0))
        Ncnt = [0]
        for j in range(m):
            Ncnt.append(Ncnt[-1] + (1 if self.N[j] else 0))
        for j in range(1, m):
            N = self.N[j]
            if N is None:
                continue
            f = {}
            if j - 21 >= seg[j]:
                path = sum(abs(cl[k] - cl[k - 1]) for k in range(j - 20, j))
                f["er20"] = abs(cl[j - 1] - cl[j - 21]) / path if path else 0.0
            s50, s20, s20p = sma(j - 1, 50), sma(j - 1, 20), (sma(j - 6, 20) if j >= 6 else None)
            f["s50"] = None if s50 is None else (1 if cl[j - 1] > s50 else -1)
            f["slope20"] = None if (s20 is None or s20p is None) else (1 if s20 > s20p else -1)
            k0 = max(seg[j], j - 250)
            cnt = Ncnt[j] - Ncnt[k0]
            if cnt >= 120:
                f["volrel"] = N / ((Nps[j] - Nps[k0]) / cnt)
            f["prevrng"] = (hi[j - 1] - lo[j - 1]) / N
            f["hh20"], f["ll20"] = self.hh(j, 20), self.ll(j, 20)
            f["nr7"] = self.nr7(j)
            f["open"] = self.O[D[j][1]]
            f["wd"] = (D[j][0] + 3) % 7
            self.f[j] = f
        # ---- trend detectors, each known at the START of day j: +1 up, -1 down, 0 off (fixed before any result) ----
        #   edge20  yesterday's close in the top / bottom 15% of the previous 20 days' range
        #   donch5  a close beyond the 20-day high / low on one of the last 5 days (and not both)
        #   ma      close above the 50-day average AND the 20-day average rising (or both the other way)
        #   er10    the last 10 days moved 2+ daily ATRs in a fairly straight line (efficiency 0.4+)
        self.det = [None] * m
        brk = [0] * m
        for j in range(1, m):
            h20, l20 = self.hh(j, 20), self.ll(j, 20)
            if h20 is not None:
                brk[j] = 1 if cl[j] > h20 else (-1 if cl[j] < l20 else 0)
        for j in range(1, m):
            f = self.f[j]
            if not f:
                continue
            N = self.N[j]
            dd = {}
            if f["hh20"] is not None and f["hh20"] > f["ll20"]:
                pos = (cl[j - 1] - f["ll20"]) / (f["hh20"] - f["ll20"])
                dd["edge20"] = 1 if pos >= 0.85 else (-1 if pos <= 0.15 else 0)
            if j - 5 >= seg[j]:
                b = set(brk[k] for k in range(j - 5, j)) - {0}
                dd["donch5"] = b.pop() if len(b) == 1 else 0
            if f["s50"] is not None and f["slope20"] is not None:
                dd["ma"] = f["s50"] if f["s50"] == f["slope20"] else 0
            if j - 11 >= seg[j]:
                path = sum(abs(cl[k] - cl[k - 1]) for k in range(j - 10, j))
                mv = cl[j - 1] - cl[j - 11]
                dd["er10"] = (1 if mv > 0 else -1) if (path and abs(mv) / path >= 0.4 and abs(mv) >= 2 * N) else 0
            self.det[j] = dd
        self._m1_open()

    # ---- M1 bars on demand: a stop / limit order is filled minute by minute inside its M15 bar ----
    def _m1_open(self):
        self.m1q = None
        try:
            con = sqlite3.connect(A.find_db())
            t, tcol, oc, hc, lo, cc, sc, name_hit = A.detect_source(con, self.spec["match"])
            where, args = "", []
            if sc and not name_hit:
                want = set(x.upper() for x in self.spec["match"])
                sym = [r[0] for r in con.execute('select distinct "%s" from "%s"' % (sc, t))
                       if str(r[0]).upper().replace(" ", "") in want]
                if not sym:
                    return
                where, args = '"%s" = ? and ' % sc, [sym[0]]
            q = 'select "%s","%s","%s","%s","%s" from "%s" where %s' % (tcol, oc, hc, lo, cc, t, where)
            row = con.execute(q + "1=1 limit 1", args).fetchone()
            if row is None:
                return
            raw = row[0]
            shift = A.DB_UTC_OFFSET_HOURS * 3600.0
            if isinstance(raw, (int, float)):
                scale = 1000.0 if raw > 1e12 else 1.0
                self._m1key = lambda x: (x + shift) * scale
            else:
                fmt = "%Y-%m-%d %H:%M:%S" if len(str(raw)) >= 19 else "%Y-%m-%d %H:%M"
                tsep = "T" if "T" in str(raw) else " "
                self._m1key = lambda x: time.strftime(fmt.replace(" ", tsep), time.gmtime(x + shift))
            self.m1q = (con, q + '"%s" >= ? and "%s" < ? order by "%s"' % (tcol, tcol, tcol), args)
        except Exception as e:
            print("(%s: no minute bars, fills judged on M15 bars: %s)" % (self.s, e))
            self.m1q = None

    def m1(self, i):
        """The M1 bars (o, h, l, c) inside M15 bar i, or None."""
        if self.m1q is None:
            return None
        con, q, args = self.m1q
        rows = con.execute(q, args + [self._m1key(self.T[i]), self._m1key(self.T[i] + 900)]).fetchall()
        out = []
        for r in rows:
            try:
                out.append((float(r[1]), float(r[2]), float(r[3]), float(r[4])))
            except (TypeError, ValueError):
                continue
        return out or None

    def dN(self, i):
        return self.N[self.di[i]]

    def hh(self, j, w):                 # highest high of the w days BEFORE day j
        return max(self.hi[j - w:j]) if j - w >= self.seg[j] else None

    def ll(self, j, w):
        return min(self.lo[j - w:j]) if j - w >= self.seg[j] else None

    def nr7(self, j):                   # day j-1 was the narrowest of the 7 days ending at j-1
        if j - 7 < self.seg[j]:
            return None
        r = [self.hi[k] - self.lo[k] for k in range(j - 7, j)]
        return 1 if r[-1] <= min(r) else 0

    def with_trend(self, j, d):         # direction agrees with the 50-day average's side
        s = self.sma(j - 1, 50) if j >= 1 else None
        return None if s is None else (1 if (self.cl[j - 1] - s) * d > 0 else 0)

    def tags(self, j0, d, sd):
        """What was known when a trade starting at bar j0 (direction d, risk sd) was taken."""
        j = self.di[min(j0, self.n - 1)]
        f = self.f[j]
        if not f:
            return {}
        N = self.N[j]
        px = self.C[j0 - 1] if j0 >= 1 else self.O[j0]
        t = {"vol": f.get("volrel"), "trendy": f.get("er20"), "prev_range": f["prevrng"], "risk_size": sd / N,
             "with_50d": None if f["s50"] is None else (1 if f["s50"] == d else 0),
             "with_slope20": None if f["slope20"] is None else (1 if f["slope20"] == d else 0),
             "nr7": f["nr7"], "weekday": f["wd"], "day_move_with": d * (px - f["open"]) / N,
             "gap_with": d * (f["open"] - self.cl[j - 1]) / N, "_N": N, "_px": px, "_d": d, "_dk": self.D[j][0]}
        if f["hh20"] is not None and f["hh20"] > f["ll20"]:
            pos = (px - f["ll20"]) / (f["hh20"] - f["ll20"])
            t["pos20_with"] = pos if d > 0 else 1.0 - pos
        h = (self.loc[j0] - self.open_min) // 60
        t["hour"] = "pre-open" if h < 0 else ("0-2h" if h < 2 else ("2-5h" if h < 5 else "5h+"))
        return t

    def cost(self, i, price):
        return _real_cost_px(self.s, self.spec, price, self.S[i] if self.S else None)

    def swap(self, d, t0, t1):
        n = _swap_nights(t0, t1)
        return n * (self.spec["swap_long"] if d > 0 else self.spec["swap_short"]) if n else 0.0


def p_walk(m, j0, entry, d, sd, plans, same_bar_stop=False, sub=None):
    """Walks bars from j0 for one direction. plans: {name: (target_px or None, end_index or None, trail kind)}
    trail kind: None, ("risk", dist) = trail at dist behind best close, ("chan", dist) = the same idea, other cap.
    Returns {name: (exit_price, exit_index)} for the plans that finished (data end = not finished)."""
    H, L, O, C = m.H, m.L, m.O, m.C
    st = {}
    end_max = j0
    for k, (tp, end, tr) in plans.items():
        st[k] = [entry - d * sd, tp, end, tr, entry, None]       # stop, target, end, trail, best close, result
        if end is not None and end > end_max:
            end_max = end
    end_max = min(end_max, m.n - 1)
    left = len(st)
    T = m.T

    def steps():
        if sub:                                          # the fill bar, minute by minute (first minute: cautious)
            for q, b in enumerate(sub):
                yield j0, b[0], b[1], b[2], b[3], q == 0, True
            start = j0 + 1
        else:
            start = j0
        for j in range(start, end_max + 1):
            if j > j0 and T[j] - T[j - 1] > P_MAX_GAP:
                return                                   # a long break in the data (sealed years, holes): unfinished
            yield j, O[j], H[j], L[j], C[j], (j == j0 and same_bar_stop), False

    for j, o, h, l, c, first, minute in steps():
        for k, x in st.items():
            if x[5] is not None:
                continue
            stop, tp = x[0], x[1]
            px = None
            gap_ok = not first
            if d > 0:
                if gap_ok and o <= stop:
                    px = o
                elif l <= stop:
                    px = stop
                elif tp is not None and h >= tp:
                    px = o if (gap_ok and o >= tp) else tp
            else:
                if gap_ok and o >= stop:
                    px = o
                elif h >= stop:
                    px = stop
                elif tp is not None and l <= tp:
                    px = o if (gap_ok and o <= tp) else tp
            if px is None and x[2] is not None and j >= x[2] and not minute:
                px = c
            if px is not None:
                x[5] = (px, j)
                left -= 1
                continue
            if x[3] is not None and not minute:
                if (c - x[4]) * d > 0:
                    x[4] = c
                ns = x[4] - d * x[3][1]
                if (ns - x[0]) * d > 0:
                    x[0] = ns
        if not left:
            break
    return dict((k, x[5]) for k, x in st.items() if x[5] is not None)


def p_plans(m, j0, entry, d, sd, exits, tgt_r=2.0, close_idx=None):
    """Builds the standard exit plans for a trade that is live from bar j0."""
    N = m.dN(j0) or sd
    ci = close_idx if close_idx is not None else m.next_close[j0]
    if ci is not None and ci - j0 > 96:
        ci = j0 + 96                                     # no close bar within a day (holiday): a day at most
    out = {}
    for e in exits:
        if e == "close":
            out[e] = (None, ci if ci is not None else j0 + 96, None)
        elif e == "24h":
            out[e] = (None, j0 + 96, None)
        elif e == "48h":
            out[e] = (None, j0 + 192, None)
        elif e == "trail":
            out[e] = (None, j0 + 192, ("risk", sd))
        elif e == "5d":
            out[e] = (None, j0 + 480, ("chan", N))
        elif e == "2R":
            out[e] = (entry + d * tgt_r * sd, ci if ci is not None else j0 + 96, None)
    return out


def p_trade(m, rows, lane, var, j0, entry, d, sd, exits, t_in=None, same_bar_stop=False, tags=None, close_idx=None,
            plans=None, sub=None):
    """Runs one trade and its mirror; appends one row per finished exit:
    (lane, variant, exit, era, r_net, ctrl_net, r_gross, tags)."""
    if sd is None or sd <= 0 or j0 >= m.n:
        return
    t_in = t_in if t_in is not None else m.T[j0]
    era = _p_era(t_in)
    if era is None:
        return
    pl = plans if plans is not None else p_plans(m, j0, entry, d, sd, exits, close_idx=close_idx)
    mir = {}
    for k, (tp, end, tr) in pl.items():
        mir[k] = ((2 * entry - tp) if tp is not None else None, end, tr)
    a = p_walk(m, j0, entry, d, sd, pl, same_bar_stop, sub)
    b = p_walk(m, j0, entry, -d, sd, mir, same_bar_stop, sub)
    cost = m.cost(j0, entry)
    base_tags = m.tags(j0, d, sd)
    if tags:
        base_tags.update(tags)
    for k in pl:
        if k not in a or k not in b:
            continue
        (pa, ja), (pb, jb) = a[k], b[k]
        t_a, t_b = m.T[ja] + 900, m.T[jb] + 900
        if m.dq.overlaps(t_in, max(t_a, t_b)):
            continue
        ga = d * (pa - entry)
        gb = -d * (pb - entry)
        ra = (ga - cost + m.swap(d, t_in, t_a)) / sd
        rb = (gb - cost + m.swap(-d, t_in, t_b)) / sd
        tg = dict(base_tags)
        tg["_t_in"], tg["_t_out"] = t_in, t_a
        rows.append((lane, var, k, era, ra, (ra + rb) / 2.0, ga / sd, tg))


# ---- B. the rebuilt lanes ----
def p_days(m):
    """Yields (j, i_first, i_last) for every daily bar with enough history."""
    for j in range(1, len(m.D)):
        if m.N[j] is None:
            continue
        yield j, m.D[j][1], m.D[j][2]


def p_session_open(m, i0, i1):
    """Index of the bar that starts at the session open inside the day's bars i0..i1 (None if that bar is missing)."""
    for i in range(i0, i1 + 1):
        if m.loc[i] == m.open_min:
            return i
    return None


def p_stop_entry(m, i_from, i_to, up, dn):
    """First bar in i_from..i_to that trades through up (buy stop) or dn (sell stop).
    -> (i, dir, fill, sub) or None. The fill bar is resolved on its M1 bars: the first minute that crosses fills at the
    level (or that minute's open if it opened beyond it); sub = that minute and the rest of the M15 bar, walked minute by
    minute. Both levels crossed in one bar (or one minute) = unknown order: the day is skipped."""
    for i in range(i_from, min(i_to, m.n - 1) + 1):
        hu = up is not None and m.H[i] >= up
        hd = dn is not None and m.L[i] <= dn
        if not (hu or hd):
            continue
        mins = m.m1(i)
        if mins:
            for k, (o, h, l, c) in enumerate(mins):
                a = up is not None and h >= up
                b = dn is not None and l <= dn
                if a and b:
                    return None
                if a:
                    return i, 1, max(up, o), mins[k:]
                if b:
                    return i, -1, min(dn, o), mins[k:]
        if hu and hd:
            return None
        if hu:
            return i, 1, max(up, m.O[i]), None
        return i, -1, min(dn, m.O[i]), None
    return None


def p_limit_entry(m, i, lvl, d):
    """A limit order at lvl (buy below / sell above) touched in bar i. -> (fill, sub)."""
    mins = m.m1(i)
    if mins:
        for k, (o, h, l, c) in enumerate(mins):
            if (d > 0 and l <= lvl) or (d < 0 and h >= lvl):
                return (min(lvl, o) if d > 0 else max(lvl, o)), mins[k:]
    return (min(lvl, m.O[i]) if d > 0 else max(lvl, m.O[i])), None


def lane_main2(m, rows):
    if m.s not in P_SESSION:
        return
    box_from = (18 * 60) if P_SESSION[m.s][0] == "ny" else 0
    for j, i0, i1 in p_days(m):
        io = p_session_open(m, i0, i1)
        if io is None:
            continue
        N = m.N[j]
        # the box: London markets 00:00 London -> the open; New York markets 18:00 New York (evening before) -> the open
        if box_from == 0:
            b = [i for i in range(i0, io) if m.loc[i] < m.open_min]
            need = m.open_min // 15
        else:
            b = [i for i in range(i0, io) if m.loc[i] >= box_from or m.loc[i] < m.open_min]
            need = (24 * 60 - box_from + m.open_min) // 15
        if len(b) < 0.7 * need:
            continue
        hi, lo = max(m.H[i] for i in b), min(m.L[i] for i in b)
        if not (0.15 * N <= hi - lo <= 1.5 * N):
            continue
        e = p_stop_entry(m, io, min(i1, io + 11), hi, lo)
        if e is None:
            continue
        i, d, px, sub = e
        tags = {"nr7": m.nr7(j), "trend": m.with_trend(j, d)}
        for var, sd in (("box", px - lo if d > 0 else hi - px), ("0.3D", 0.3 * N)):
            p_trade(m, rows, "main2", var, i, px, d, sd, P_EXITS, same_bar_stop=True, tags=tags, sub=sub)
        # retest2: the broken edge comes back within 2 hours after the break bar -> limit there, stop 0.25D beyond
        lvl = hi if d > 0 else lo
        for k in range(i + 1, min(i + 9, m.n)):
            if (d > 0 and m.L[k] <= lvl) or (d < 0 and m.H[k] >= lvl):
                fill, sub2 = p_limit_entry(m, k, lvl, d)
                p_trade(m, rows, "retest2", "0.25D", k, fill, d, abs(fill - (lvl - d * 0.25 * N)), P_EXITS,
                        same_bar_stop=True, tags=tags, sub=sub2)
                break


P_DIAG = defaultdict(int)       # (market, era, why a day gave no orb30 trade) -> days; printed in the report


def lane_orb(m, rows):
    for j, i0, i1 in p_days(m):
        era = _p_era(m.T[i0])
        io = p_session_open(m, i0, i1)
        if io is None:
            P_DIAG[(m.s, era, "no bar at the open")] += 1
            continue
        N = m.N[j]
        ce = m.next_close[io]
        if ce is None or ce > i1 + 96:
            P_DIAG[(m.s, era, "no close bar")] += 1
            continue
        for name, nb in (("orb30", 2), ("orb60", 4)):
            r = list(range(io, io + nb))
            if r[-1] >= m.n or any(m.loc[x] != m.open_min + 15 * (x - io) for x in r):
                if name == "orb30":
                    P_DIAG[(m.s, era, "range bars missing")] += 1
                continue
            hi, lo = max(m.H[x] for x in r), min(m.L[x] for x in r)
            e = p_stop_entry(m, io + nb, ce - 4, hi, lo)        # no new entry in the last hour
            if e is None:
                if name == "orb30":
                    P_DIAG[(m.s, era, "no break / both sides in one bar")] += 1
                continue
            if name == "orb30":
                P_DIAG[(m.s, era, "entry")] += 1
            i, d, px, sub = e
            tags = {"nr7": m.nr7(j), "trend": m.with_trend(j, d)}
            for var, sd in (("range", px - lo if d > 0 else hi - px), ("0.1D", 0.1 * N)):
                p_trade(m, rows, name, var, i, px, d, sd, P_EXITS, same_bar_stop=True, tags=tags, close_idx=ce, sub=sub)


def lane_pdh2(m, rows):
    for j, i0, i1 in p_days(m):
        ph, pl = m.hi[j - 1], m.lo[j - 1]
        N = m.N[j]
        e = p_stop_entry(m, i0, i1, ph, pl)
        if e is None:
            continue
        i, d, px, sub = e
        tags = {"nr7": m.nr7(j), "trend": m.with_trend(j, d)}
        lvl = ph if d > 0 else pl
        for var, stop in (("lvl0.25D", lvl - d * 0.25 * N), ("mid", (ph + pl) / 2.0)):
            p_trade(m, rows, "pdh2", var, i, px, d, abs(px - stop), P_EXITS, same_bar_stop=True, tags=tags,
                    close_idx=i1, sub=sub)


def lane_trend2(m, rows):
    """Noise boundary (Zarattini, Aziz, Barbon). sigma_k = average over the 14 previous sessions of |close_k / open - 1|
    at the same bar k after the open. Upper = max(open, previous close) * (1 + sigma_k), lower = min(...) * (1 - sigma_k).
    Every 30 minutes: close above upper -> long, below lower -> short. Stop = boundary / VWAP (the nearer one on the
    right side), checked at every bar close; out at the session close; may re-enter."""
    hist = []                                           # per session: {k: |c/o - 1|}
    prev_close = None
    for j, i0, i1 in p_days(m):
        io = p_session_open(m, i0, i1)
        if io is None:
            prev_close = None
            continue
        ce = m.next_close[io]
        if ce is None or ce > i1 + 96:
            continue
        o = m.O[io]
        moves = dict((k, abs(m.C[io + k] / o - 1.0)) for k in range(0, ce - io + 1))
        N = m.N[j]
        if len(hist) >= 14 and prev_close:
            ref_hi, ref_lo = max(o, prev_close), min(o, prev_close)
            pv = pw = 0.0
            pos = None                                  # [dir, entry, entry index, stop distance]
            for k in range(0, ce - io + 1):
                i = io + k
                tp = (m.H[i] + m.L[i] + m.C[i]) / 3.0
                w = m.V[i] if (m.V and m.V[i]) else 1.0
                pv += tp * w; pw += w
                vwap = pv / pw
                sig = [h.get(k) for h in hist[-14:]]
                if any(x is None for x in sig):
                    break
                sg = sum(sig) / 14.0
                up, dn = ref_hi * (1 + sg), ref_lo * (1 - sg)
                c = m.C[i]
                if pos is not None:
                    d, e, ie, sd = pos
                    stop = max(up, vwap) if d > 0 else min(dn, vwap)
                    if (d > 0 and c < stop) or (d < 0 and c > stop) or i == ce:
                        _p_own(m, rows, "trend2", "own", ie, e, d, sd, c, i)
                        pos = None
                if pos is None and k >= 2 and k % 2 == 0 and i < ce:
                    d = 1 if c > up else (-1 if c < dn else 0)
                    if d and i + 1 < m.n:
                        stop = max(up, vwap) if d > 0 else min(dn, vwap)
                        sd = max(abs(c - stop), 0.1 * N)
                        pos = [d, c, i + 1, sd]
                        p_trade(m, rows, "trend2", "gen", i + 1, c, d, sd, ("close", "trail"), t_in=m.T[i] + 900,
                                close_idx=ce)
        hist.append(moves)
        prev_close = m.C[ce]


def _p_own(m, rows, lane, var, j0, entry, d, sd, px, jx):
    t_in, t_out = m.T[j0], m.T[jx] + 900
    era = _p_era(t_in)
    if era is None or m.dq.overlaps(t_in, t_out):
        return
    g = d * (px - entry)
    r = (g - m.cost(j0, entry) + m.swap(d, t_in, t_out)) / sd
    rows.append((lane, var, "own", era, r, None, g / sd, {}))


def lane_gao(m, rows):
    prev_close = None
    for j, i0, i1 in p_days(m):
        io = p_session_open(m, i0, i1)
        if io is None:
            prev_close = None
            continue
        ce = m.next_close[io]
        if ce is None or ce > i1 + 96 or ce - io < 6:
            prev_close = None
            continue
        if prev_close:
            first = m.C[io + 1] - prev_close              # previous close -> 30 minutes after the open
            d = 1 if first > 0 else (-1 if first < 0 else 0)
            ie = ce - 2                                   # enter at the close of the bar ending 30 minutes before the close
            if d and m.T[ce] - m.T[ie] == 1800:
                p_trade(m, rows, "gao", "0.25D", ie + 1, m.C[ie], d, 0.25 * m.N[j], ("close",), t_in=m.T[ie] + 900,
                        close_idx=ce)
        prev_close = m.C[ce]


def lane_range2(m, rows):
    if P_SESSION[m.s][0] != "lon":
        return
    for j, i0, i1 in p_days(m):
        N = m.N[j]
        bs = [i for i in range(i0, i1 + 1) if 0 <= m.loc[i] < 8 * 60]
        if len(bs) < 24 or m.loc[bs[0]] > 30:
            continue
        lon_open = bs[-1]                         # out at the close of the 07:45 bar = 08:00 London
        hi = lo = None
        for i in bs:
            if hi is not None and m.loc[i] >= 2 * 60 and hi - lo >= 0.1 * N:
                mid = (hi + lo) / 2.0
                z = 0.05 * N
                d = 0
                if m.H[i] >= hi - z and mid < m.C[i] <= hi - z:
                    d, stop = -1, max(hi, m.H[i]) + 0.15 * N
                elif m.L[i] <= lo + z and lo + z <= m.C[i] < mid:
                    d, stop = 1, min(lo, m.L[i]) - 0.15 * N
                if d and i + 1 < m.n:
                    e = m.C[i]
                    sd = abs(e - stop)
                    p_trade(m, rows, "range2", "asia", i + 1, e, d, sd, (), t_in=m.T[i] + 900,
                            plans={"own": (mid, lon_open, None)})
                    break
            hi = m.H[i] if hi is None else max(hi, m.H[i])
            lo = m.L[i] if lo is None else min(lo, m.L[i])


def _p_swing_walk(m, j0, entry, d, N, units_max, add_step, t_in, exit_days=10):
    """Turtle walk from bar j0: stop 2N from the LAST unit, exit on a daily close beyond the 10-day extreme on the other
    side (out at the next bar's open), adds every add_step*N in favour up to units_max. -> (pnl price units incl. costs
    and swap, exit bar) or None."""
    units = [(entry, j0)]
    stop = entry - d * 2 * N
    nxt = entry + d * add_step * N
    pnl_cost = m.cost(j0, entry)
    for j in range(j0, m.n):
        if j > j0 and m.T[j] - m.T[j - 1] > P_MAX_GAP:
            return None, None, j
        o, h, l = m.O[j], m.H[j], m.L[j]
        px = None
        if d > 0:
            if o <= stop and j > j0:
                px = o
            elif l <= stop:
                px = stop
        else:
            if o >= stop and j > j0:
                px = o
            elif h >= stop:
                px = stop
        if px is None and len(units) < units_max:
            if (d > 0 and h >= nxt) or (d < 0 and l <= nxt):
                f = max(nxt, o) if d > 0 else min(nxt, o)
                units.append((f, j))
                pnl_cost += m.cost(j, f)
                stop = f - d * 2 * N
                nxt = f + d * add_step * N
        if px is None and j == m.D[m.di[j]][2] and j + 1 < m.n:     # last bar of the day: the 10-day exit
            dj = m.di[j]
            ex = m.ll(dj, exit_days) if d > 0 else m.hh(dj, exit_days)
            if ex is not None and ((d > 0 and m.C[j] < ex) or (d < 0 and m.C[j] > ex)):
                px, j = m.O[j + 1], j + 1
        if px is not None:
            t_out = m.T[j] + 900
            if m.dq.overlaps(t_in, t_out):
                return None, None, j
            g = sum(d * (px - u) for u, _ in units)
            sw = sum(m.swap(d, m.T[ju], t_out) for _, ju in units)
            swm = sum(m.swap(-d, m.T[ju], t_out) for _, ju in units)
            return g - pnl_cost + sw, g, j, (-g - pnl_cost + swm)
    return None, None, m.n


def lane_swing2(m, rows):
    busy = {"close": -1, "stop": -1, "stop+pyr": -1}    # one position at a time per variant (as the turtles traded)
    for j, i0, i1 in p_days(m):
        N = m.N[j]
        h20, l20 = m.hh(j, 20), m.ll(j, 20)
        if h20 is None:
            continue
        # (a) daily close beyond the 20-day extreme -> in at the next bar's open
        c = m.cl[j]
        d = 1 if c > h20 else (-1 if c < l20 else 0)
        if d and i1 + 1 < m.n and i1 + 1 > busy["close"]:
            busy["close"] = _p_swing(m, rows, "close", i1 + 1, m.O[i1 + 1], d, N)
        # (b) stop orders on the 20-day high / low during the day (the original turtle entry)
        e = p_stop_entry(m, max(i0, busy["stop"] + 1), i1, h20, l20)
        if e is not None:
            i, d, px, _ = e
            busy["stop"] = _p_swing(m, rows, "stop", i, px, d, N)
        e = p_stop_entry(m, max(i0, busy["stop+pyr"] + 1), i1, h20, l20)
        if e is not None:
            i, d, px, _ = e
            busy["stop+pyr"] = _p_swing(m, rows, "stop+pyr", i, px, d, N, units=4)


def _p_swing(m, rows, var, j0, entry, d, N, units=1, lane="swing2", exit_days=10):
    """Runs one swing trade (and its mirror). Returns the bar the trade ended on (the position is busy until then)."""
    t_in = m.T[j0]
    a = _p_swing_walk(m, j0, entry, d, N, units, 0.5, t_in, exit_days)
    if a is None or a[0] is None:
        return a[2] if a else m.n                        # unfinished (break in the data / hole): busy until there
    era = _p_era(t_in)
    if era is not None:
        # control = the same units, same times, opposite direction (a coin flip with the same timing and costs)
        ra, rb = a[0] / (2 * N), a[3] / (2 * N)
        tg = m.tags(j0, d, 2 * N)
        tg["_t_in"], tg["_t_out"] = t_in, m.T[min(a[2], m.n - 1)] + 900
        rows.append((lane, var, "own", era, ra, (ra + rb) / 2.0, a[1] / (2 * N), tg))
    return a[2]


def lane_rsi2(m, rows):
    """Connors RSI(2): risk unit = 1N; catastrophic stop 3N (rarely hit). Out at the next open after a close beyond the
    5-day average. Plus dipx: the old dip entry (2 lower closes above a rising 20-day average, stop order on yesterday's
    high, stop under the pullback) with the trailing exits instead of 2R."""
    busy = -1
    for j, i0, i1 in p_days(m):
        N = m.N[j]
        s200, r = m.sma(j, 200), m.rsi2[j]
        if s200 is not None and r is not None and i1 + 1 < m.n and i1 + 1 > busy:
            c = m.cl[j]
            d = 1 if (c > s200 and r < 10) else (-1 if (c < s200 and r > 90) else 0)
            if d:
                ex = _p_rsi_walk(m, i1 + 1, m.O[i1 + 1], d, N)
                busy = ex[2]
                if ex[0] is not None:
                    t_in = m.T[i1 + 1]
                    era = _p_era(t_in)
                    if era:
                        ra, rb = ex[0] / N, ex[3] / N
                        tg = m.tags(i1 + 1, d, N)
                        tg["_t_in"], tg["_t_out"] = t_in, m.T[min(ex[2], m.n - 1)] + 900
                        rows.append(("rsi2", "long" if d > 0 else "short", "own", era, ra, (ra + rb) / 2.0, ex[1] / N,
                                     tg))
        # dipx
        if j >= 3:
            s20, s20p = m.sma(j - 1, 20), m.sma(j - 6, 20) if j >= 6 else None
            if s20 is None or s20p is None:
                continue
            c1, c2, c3 = m.cl[j - 1], m.cl[j - 2], m.cl[j - 3]
            up = c1 > s20 and s20 > s20p and c1 < c2 < c3
            dn = c1 < s20 and s20 < s20p and c1 > c2 > c3
            if up or dn:
                d = 1 if up else -1
                e = p_stop_entry(m, i0, i1, m.hi[j - 1] if d > 0 else None, m.lo[j - 1] if d < 0 else None)
                if e is None:
                    continue
                i, d2, px, sub = e
                stop = min(m.lo[j - 1], m.lo[j - 2]) if d > 0 else max(m.hi[j - 1], m.hi[j - 2])
                p_trade(m, rows, "dipx", "pullback", i, px, d, abs(px - stop), ("2R", "48h", "5d"), same_bar_stop=True,
                        close_idx=i + 480, sub=sub)


def _p_rsi_walk(m, j0, entry, d, N):
    stop = entry - d * 3 * N
    t_in = m.T[j0]
    for j in range(j0, m.n):
        if j > j0 and m.T[j] - m.T[j - 1] > P_MAX_GAP:
            return None, None, j
        o, h, l = m.O[j], m.H[j], m.L[j]
        px = None
        if d > 0 and (l <= stop):
            px = o if (o <= stop and j > j0) else stop
        if d < 0 and (h >= stop):
            px = o if (o >= stop and j > j0) else stop
        if px is None and j == m.D[m.di[j]][2] and j + 1 < m.n:
            dj = m.di[j]
            s5 = m.sma(dj, 5)
            if s5 is not None and ((d > 0 and m.C[j] > s5) or (d < 0 and m.C[j] < s5)):
                px, j = m.O[j + 1], j + 1
        if px is None and j - j0 > 96 * 20:
            px = m.C[j]
        if px is not None:
            t_out = m.T[j] + 900
            if m.dq.overlaps(t_in, t_out):
                return None, None, j
            g = d * (px - entry)
            cst = m.cost(j0, entry)
            return g - cst + m.swap(d, t_in, t_out), g, j, (-g - cst + m.swap(-d, t_in, t_out))
    return None, None, m.n


# ---- 2026-10-09 contenders (rules fixed before any result) ----
def lane_inside(m, rows):
    """Inside day (yesterday's range inside the day before's): stop orders on yesterday's high / low the next day.
    Crabel's contraction family. Stop = middle of yesterday (structural); every exit on the menu."""
    for j, i0, i1 in p_days(m):
        if j < 2 or m.seg[j] > j - 2:
            continue
        if not (m.hi[j - 1] <= m.hi[j - 2] and m.lo[j - 1] >= m.lo[j - 2]):
            continue
        ph, pl = m.hi[j - 1], m.lo[j - 1]
        e = p_stop_entry(m, i0, i1, ph, pl)
        if e is None:
            continue
        i, d, px, sub = e
        p_trade(m, rows, "inside", "mid", i, px, d, abs(px - (ph + pl) / 2.0), P_EXITS, same_bar_stop=True,
                close_idx=i1, sub=sub)


def lane_turtle55(m, rows):
    """Turtle system 2: stop order on the 55-day high / low, 2N stop, out on the 20-day opposite extreme. Long-term."""
    busy = -1
    for j, i0, i1 in p_days(m):
        h55, l55 = m.hh(j, 55), m.ll(j, 55)
        if h55 is None:
            continue
        e = p_stop_entry(m, max(i0, busy + 1), i1, h55, l55)
        if e is not None:
            i, d, px, _ = e
            busy = _p_swing(m, rows, "55/20", i, px, d, m.N[j], lane="turtle55", exit_days=20)


def lane_dip3(m, rows):
    """Three closes against the 200-day trend, then in at the next open WITH the trend; out on the first close beyond the
    previous day's high (low for shorts) or after 10 days; 3N disaster stop. Risk unit 1N. Long-term pullback buyer."""
    busy = -1
    for j, i0, i1 in p_days(m):
        if j < 4 or i1 + 1 >= m.n or i1 + 1 <= busy:
            continue
        s200 = m.sma(j, 200)
        if s200 is None:
            continue
        c = m.cl
        if c[j] > s200 and c[j] < c[j - 1] < c[j - 2] < c[j - 3]:
            d = 1
        elif c[j] < s200 and c[j] > c[j - 1] > c[j - 2] > c[j - 3]:
            d = -1
        else:
            continue
        N = m.N[j]
        j0 = i1 + 1
        entry = m.O[j0]
        stop = entry - d * 3 * N
        t_in = m.T[j0]
        res = None
        for k in range(j0, m.n):
            if k > j0 and m.T[k] - m.T[k - 1] > P_MAX_GAP:
                break
            o, h, l = m.O[k], m.H[k], m.L[k]
            px = None
            if d > 0 and l <= stop:
                px = o if (o <= stop and k > j0) else stop
            if d < 0 and h >= stop:
                px = o if (o >= stop and k > j0) else stop
            if px is None and k == m.D[m.di[k]][2] and k + 1 < m.n:
                dk = m.di[k]
                if (d > 0 and m.C[k] > m.hi[dk - 1]) or (d < 0 and m.C[k] < m.lo[dk - 1]) or dk - m.di[j0] >= 10:
                    px, k = m.O[k + 1], k + 1
            if px is not None:
                res = (px, k)
                break
        if res is None:
            continue
        px, k = res
        busy = k
        t_out = m.T[k] + 900
        era = _p_era(t_in)
        if era is None or m.dq.overlaps(t_in, t_out):
            continue
        g = d * (px - entry)
        cst = m.cost(j0, entry)
        ra = (g - cst + m.swap(d, t_in, t_out)) / N
        rb = (-g - cst + m.swap(-d, t_in, t_out)) / N
        tg = m.tags(j0, d, N)
        tg["_t_in"], tg["_t_out"] = t_in, t_out
        rows.append(("dip3", "long" if d > 0 else "short", "own", era, ra, (ra + rb) / 2.0, g / N, tg))


P_OMEGA_ONLY = False                      # 'omega' mode: only the lanes the omega book uses, then Part K only
P_OMEGA_LANES = ("main2", "orb", "pdh2", "rsi2", "inside", "dip3")
P_LANES = [("main2", lane_main2), ("orb", lane_orb), ("pdh2", lane_pdh2), ("trend2", lane_trend2), ("gao", lane_gao),
           ("range2", lane_range2), ("swing2", lane_swing2), ("rsi2", lane_rsi2), ("inside", lane_inside),
           ("turtle55", lane_turtle55), ("dip3", lane_dip3)]


# ---- A. the exit test on the collect trades ----
def p_exit_test(m, rows, trades):
    import bisect as _b
    for t in trades:
        if t.get("stop_dist") is None or t.get("entry") is None or t.get("t_in") is None:
            continue
        j0 = _b.bisect_left(m.T, t["t_in"])
        if j0 >= m.n or m.T[j0] - t["t_in"] > 3600:
            continue
        d, e, sd = int(t["dir"]), t["entry"], t["stop_dist"]
        if j0 < 1 or sd <= 0 or abs(e - m.C[j0 - 1]) > 0.5 * sd:
            continue                                     # the bars do not match this trade (should not happen)
        p_trade(m, rows, t["lane"], "exit", j0, e, d, sd, P_EXITS_A[1:], t_in=t["t_in"])
        era = _p_era(t["t_in"])
        if era and t.get("r") is not None:
            rows.append((t["lane"], "exit", "orig", era, t["r"], None, t.get("gross_r"), {}))


# ---- report ----
def _p_stats(rs):
    n = len(rs)
    if not n:
        return None
    r = [x[5] for x in rs]
    mr = sum(r) / n
    ed = [x[5] - x[6] for x in rs if x[6] is not None]
    me = sum(ed) / len(ed) if ed else None
    if ed and len(ed) > 1:
        v = sum((x - me) ** 2 for x in ed) / (len(ed) - 1)
        te = me / math.sqrt(v / len(ed)) if v > 0 else 0.0
    else:
        te = None
    return n, mr, me, te


def _p_fmt(st):
    if st is None or st[0] < P_MIN_N:
        return "%22s" % ("n=%d" % (st[0] if st else 0))
    n, mr, me, te = st
    if me is None:
        return "%5d %+6.3f %15s" % (n, mr, "")
    return "%5d %+6.3f %+6.3f t%+5.1f" % (n, mr, me, te)


def run_power_omega(rep):
    """Fast mode: build only the omega book's lanes and run Part K (the omega path + sizing comparison)."""
    global P_OMEGA_ONLY
    P_OMEGA_ONLY = True
    run_power(rep, None)


def run_power(rep, folder=None):
    global REAL_COSTS
    REAL_COSTS = True
    rep.p("")
    rep.p("=" * 110)
    rep.p("PART 9: POWER   the audit's rebuild list. Same costs as 'final' (REAL), every trade against a random direction")
    rep.p("=" * 110)
    rep.p("Read every cell as:  n   R/trade (net)   EDGE (R/trade minus the coin-flip average with the same timing, stop,")
    rep.p("exit and costs)   t (of the edge).  OLD = 2014-21 (2014-17, 2018-19, 2020-21), NEW = 2024+.  2022-23 sealed.")
    rep.p("+ = net R/trade above 0 in BOTH old and new.  E = edge above 0 in both with t >= 2 in at least one.")
    rep.p("There are about 90 cells and many share the same trades: a few will show |t| above 2.5 by chance. A cell")
    rep.p("counts only if it holds in both periods AND on more than one market (see the by-market lines).")
    rep.p("Swing2 / rsi2 control = the same trade held over the same time in the other direction (their exits are not")
    rep.p("mirror images). TESTED on a pure random walk before shipping: edges came out at 0 within noise.")
    rep.p("Exits:")
    for k in P_EXITS_A + ("2R", "own"):
        rep.p("  %-6s %s" % (k, P_EXIT_TEXT[k]))
    rep.p("Sessions (local): gold, EURUSD, USDJPY open 08:00 London, day ends 17:00 New York; Germany 40 08:00-16:30 London;")
    rep.p("US 500 09:30-16:00 New York; WTI 09:00-14:30 New York. N / D = daily ATR(20), FX days ending 17:00 New York.")
    rep.p("Gold: commission $25 per million a side, swap -2.0895 / -1.92 pips (0.01) a night: the broker's sheet (2026-10-08).")
    specs = dict((x["name"], x) for x in A.COLLECT_SYMBOLS)
    old = None
    if folder:
        try:
            old = _old_folder()
        except RuntimeError as e:
            rep.p("(exit test: no oldcollect run, 2014-19 rows missing: %s)" % e)
    rows_a, rows_b = [], []
    t0 = time.time()
    for s in A.HOUSE_SYMBOLS:
        if s not in specs:
            continue
        print("power: loading %s ..." % s)
        try:
            m = PMarket(specs[s])
        except RuntimeError as e:
            rep.p("%s: skipped (%s)" % (s, str(e).splitlines()[0]))
            continue
        ra, rb = [], []
        if folder:
            tr = []
            for fol, is_old in ((folder, False), (old, True)):
                if fol and os.path.exists(os.path.join(fol, "trades_%s.csv" % s)):
                    ts, _ = load_market(fol, s)
                    tr += ts
            per = {s: tr}
            _reprice(per, specs)
            print("power: %s exit test on %d trades ..." % (s, len(tr)))
            p_exit_test(m, ra, tr)
        for name, fn in P_LANES:
            if P_OMEGA_ONLY and name not in P_OMEGA_LANES:
                continue
            print("power: %s %s ..." % (s, name))
            fn(m, rb)
        rows_a += [(s,) + x for x in ra]
        rows_b += [(s,) + x for x in rb]
        print("power: %s done (%.0fs)" % (s, time.time() - t0))
        P_MONTHS.update(p_months(m))
        p_canary_events(m)
        for j, d in enumerate(m.D):
            if m.det[j] is not None:
                P_DAYS[(m.s, d[0])] = (time.strftime("%Y-%m", time.gmtime(m.T[d[1]])), m.det[j], _p_era(m.T[d[1]]))
        if m.m1q:
            m.m1q[0].close()
        del m
    if P_OMEGA_ONLY:
        run_part_k(rep, rows_b)
        rep.p("")
        rep.p("(omega mode: lanes %s only; parts A-J not run)   runtime %.0fs" % (", ".join(P_OMEGA_LANES),
                                                                             time.time() - t0))
        return
    cells = []

    def table(rows, title, order=None):
        rep.p("")
        rep.p("-" * 110)
        rep.p(title)
        rep.p("-" * 110)
        rep.p("%-9s %-9s %-6s | %-22s | %-22s | %s" % ("lane", "variant", "exit", "OLD 2014-21", "NEW 2024+", "marks"))
        g = defaultdict(list)
        for x in rows:
            g[(x[1], x[2], x[3])].append(x)
        keys = sorted(g, key=lambda k: ((order or []).index(k[0]) if (order and k[0] in order) else 99, k))
        best = []
        for k in keys:
            rs = g[k]
            so = _p_stats([x for x in rs if x[4] in POWER_OLD])
            sn = _p_stats([x for x in rs if x[4] == "B 2024+"])
            mk = ""
            if so and sn and so[0] >= P_MIN_N and sn[0] >= P_MIN_N:
                if so[1] > 0 and sn[1] > 0:
                    mk += "+"
                if so[2] is not None and sn[2] is not None and so[2] > 0 and sn[2] > 0 and max(so[3], sn[3]) >= 2:
                    mk += "E"
            rep.p("%-9s %-9s %-6s | %s | %s | %s" % (k[0], k[1], k[2], _p_fmt(so), _p_fmt(sn), mk))
            if mk:
                best.append(k)
            # per market x era cells for the csv
            for s in sorted(set(x[0] for x in rs)):
                for era in POWER_ERAS:
                    st = _p_stats([x for x in rs if x[0] == s and x[4] == era])
                    if st:
                        cells.append({"part": title[:1], "lane": k[0], "variant": k[1], "exit": k[2], "market": s,
                                      "era": era, "n": st[0], "r": round(st[1], 4),
                                      "edge": round(st[2], 4) if st[2] is not None else "",
                                      "t_edge": round(st[3], 2) if st[3] is not None else ""})
        return g, best

    def by_market(g, keys, title):
        if not keys:
            return
        rep.p("")
        rep.p(title)
        for k in keys:
            rep.p("  %s %s %s" % k)
            for s in A.HOUSE_SYMBOLS:
                rs = [x for x in g[k] if x[0] == s]
                if not rs:
                    continue
                so = _p_stats([x for x in rs if x[4] in POWER_OLD])
                sn = _p_stats([x for x in rs if x[4] == "B 2024+"])
                yrs = 8.0 + 2.75                                       # 2014-21 + 2024-26 (to Oct)
                pw = sum(x[5] for x in rs) / yrs
                home = " (home)" if s in P_HOME.get(k[0], ()) else ""
                rep.p("    %-10s old %s   new %s   power %+6.1f R/year%s" % (s, _p_fmt(so), _p_fmt(sn), pw, home))

    if rows_a:
        order = LANES_ORDER + ["control"]
        g, best = table(rows_a, "A. EXIT TEST   same entries as collect / oldcollect, six exits (control lane included)", order)
        by_market(g, best, "A. marked cells by market (power = net R per year from this cell on that market):")
    else:
        rep.p("")
        rep.p("A. EXIT TEST skipped: no collect run found.")
    order_b = ["main2", "retest2", "orb30", "orb60", "pdh2", "trend2", "gao", "range2", "swing2", "rsi2", "dipx"]
    g, best = table(rows_b, "B. REBUILT LANES   standard versions (stop orders, daily-ATR / structural stops, real sessions)",
                    order_b)
    by_market(g, best, "B. marked cells by market (power = net R per year from this cell on that market):")
    # home markets, whatever the marks
    rep.p("")
    rep.p("B. home markets (where the literature says each lane lives), on each lane's PRIMARY exit (fixed beforehand):")
    for lane, homes in sorted(P_HOME.items()):
        var, ex = P_PRIMARY[lane]
        for s in homes:
            r2 = [x for x in g.get((lane, var, ex), []) if x[0] == s]
            so = _p_stats([x for x in r2 if x[4] in POWER_OLD])
            sn = _p_stats([x for x in r2 if x[4] == "B 2024+"])
            rep.p("  %-7s %-10s %-9s %-6s old %s   new %s" % (lane, s, var, ex, _p_fmt(so), _p_fmt(sn)))
    # filters on the breakout lanes: NR7 day before, with the 50-day trend
    rep.p("")
    rep.p("B. filters on main2 / orb / pdh2 (exit 'close', stop variant 1): does the tag change the result?")
    for lane in ("main2", "orb30", "orb60", "pdh2"):
        rs = [x for x in rows_b if x[1] == lane and x[3] == "close" and x[2] in ("box", "range", "lvl0.25D")]
        for tag in ("nr7", "trend"):
            line = "  %-6s %-5s" % (lane, tag)
            for val in (1, 0):
                sub = [x for x in rs if x[8].get(tag) == val]
                so = _p_stats([x for x in sub if x[4] in POWER_OLD])
                sn = _p_stats([x for x in sub if x[4] == "B 2024+"])
                line += "   %s: old %s new %s" % ("yes" if val else "no ", _p_fmt(so), _p_fmt(sn))
            rep.p(line)
    # swing as a portfolio: every market, one unit, all signals; R per year
    rep.p("")
    rep.p("B. swing2 / rsi2 as a PORTFOLIO (all markets together): net R per year and per era")
    for var in ("close", "stop", "stop+pyr"):
        _p_portfolio(rep, [x for x in rows_b if x[1] == "swing2" and x[2] == var], "swing2 %s" % var)
    for var in ("long", "short"):
        _p_portfolio(rep, [x for x in rows_b if x[1] == "rsi2" and x[2] == var], "rsi2 %s" % var)
    rep.p("")
    rep.p("DATA CHECK: what happened on each day for orb30 (days per market and era)")
    for s in A.HOUSE_SYMBOLS:
        for era in POWER_ERAS:
            ks = sorted((k[2], v) for k, v in P_DIAG.items() if k[0] == s and k[1] == era)
            if ks:
                rep.p("  %-10s %-10s %s" % (s, era, "   ".join("%s %d" % kv for kv in ks)))
    run_when(rep, rows_a + rows_b)
    A._write_csv(os.path.join(rep.dir, "power_cells.csv"), cells,
                 first=("part", "lane", "variant", "exit", "market", "era", "n", "r", "edge", "t_edge"))
    rep.p("")
    rep.p("per market x era for every cell: power_cells.csv   (runtime %.0fs)" % (time.time() - t0))


def _p_portfolio(rep, rs, name):
    yrs = {"2014-17": 4.0, "2018-19": 2.0, "A 2020-21": 2.0, "B 2024+": 2.75}
    line = "  %-15s" % name
    for era in POWER_ERAS:
        x = [r for r in rs if r[4] == era]
        tot = sum(r[5] for r in x)
        ctl = sum(r[6] for r in x if r[6] is not None)
        line += "  %s: %+6.1f R/yr (coin flip %+5.1f, n %d)" % (era[-7:], tot / yrs[era], ctl / yrs[era], len(x))
    rep.p(line)


# ---- C. WHEN does it work, and which signals say so ----
# Standing rule (2026-10-08): "no edge on average" is never the answer. This part answers: when did each lane work,
# which reads predict it working or failing, in what ranges / regimes, can that state be seen early enough to act on,
# and what months with a real trend looked like (volatility, ATR, stops, profits). NO signal is dropped by a luck
# count: every read is kept and given its own evidence -- in how many of the 4 eras it pointed the same way, on how
# many markets, whether it held on 2024+ with cut points taken from 2014-21 only, and whether its direction is the one
# its written theory predicts. Luck can't be ruled out for any single cell; that evidence is what tells them apart.
W_NUM = ("vol", "trendy", "prev_range", "risk_size", "day_move_with", "gap_with", "pos20_with")
W_CAT = ("with_50d", "with_slope20", "nr7", "weekday", "hour")
W_FORM_N = 20
W_ERA_MIN = 15
P_MONTHS = {}
P_DAYS = {}                     # (market, FX day key) -> (month, detector states, era)
P_DETECTORS = ("edge20", "donch5", "ma", "er10")
# the direction each family's THEORY says a read should work in (written before any result). +1: the 'high' / '1' /
# 'hot' bucket should be better; -1: worse; 0: no theory. Breakouts and momentum ride expansion and trend; reversals
# want stretched, directionless markets.
W_THEORY = {
    "go": {"vol": +1, "trendy": +1, "prev_range": -1, "risk_size": -1, "day_move_with": +1, "gap_with": +1,
           "pos20_with": +1, "with_50d": +1, "with_slope20": +1, "nr7": +1, "form": +1},
    "back": {"vol": +1, "trendy": -1, "prev_range": +1, "risk_size": 0, "day_move_with": -1, "gap_with": -1,
             "pos20_with": -1, "with_50d": +1, "with_slope20": +1, "nr7": 0, "form": +1}}
W_BACK = {"fade", "sar", "range", "exhaust", "vwap", "gapfill", "bigrev", "range2", "rsi2", "dip3"}
W_HIGH = {"high", "1", "hot"}
W_LOW = {"low", "0", "cold"}


def p_months(m):
    """Per calendar month of one market: move in daily ATRs, straightness (ER of the daily closes), ATR as % of price."""
    out = {}
    by = defaultdict(list)
    for j, d in enumerate(m.D):
        if m.N[j]:
            by[time.strftime("%Y-%m", time.gmtime(m.T[d[1]]))].append(j)
    for ym, js in by.items():
        if len(js) < 12:
            continue
        cl = [m.cl[j] for j in js]
        path = sum(abs(cl[k] - cl[k - 1]) for k in range(1, len(cl)))
        N = sum(m.N[j] for j in js) / len(js)
        mv = (cl[-1] - m.cl[js[0] - 1] if js[0] >= 1 else cl[-1] - cl[0]) / N
        out[(m.s, ym)] = {"move_atr": mv, "dir": 1 if mv > 0 else -1,
                          "er": abs(cl[-1] - cl[0]) / path if path else 0.0, "atr_pct": 100.0 * N / cl[-1]}
    return out


def _w_groups(rows):
    keep = set((lane, var, ex) for lane, (var, ex) in P_PRIMARY.items())
    keep.add(("rsi2", "short", "own"))
    keep.add(("dip3", "short", "own"))
    out = defaultdict(list)
    for x in rows:
        k = (x[1], x[2], x[3])
        if (k in keep or (x[2] == "exit" and x[3] == "close")) and x[6] is not None:
            out[k].append(x)
    return out


def _w_form(rs):
    by = defaultdict(list)
    for x in rs:
        by[x[0]].append(x)
    for s, xs in by.items():
        xs.sort(key=lambda x: x[8].get("_t_in", 0))
        pend = sorted(((x[8].get("_t_out", 0), x[5] - x[6]) for x in xs))
        done, p = [], 0
        for x in xs:
            t = x[8].get("_t_in", 0)
            while p < len(pend) and pend[p][0] <= t:
                done.append(pend[p][1])
                p += 1
            x[8]["form"] = ("hot" if sum(done[-W_FORM_N:]) > 0 else "cold") if len(done) >= W_FORM_N else None


def _w_bucket(rs):
    """Thirds per market with cut points from 2014-21 ONLY (so 2024+ is a true out-of-sample check)."""
    out = defaultdict(dict)
    by = defaultdict(list)
    for x in rs:
        by[x[0]].append(x)
    for s, xs in by.items():
        old = [x for x in xs if x[4] in POWER_OLD]
        for k in W_NUM:
            v = sorted(x[8][k] for x in old if x[8].get(k) is not None)
            if len(v) < 30:
                continue
            a, b = v[len(v) // 3], v[2 * len(v) // 3]
            for x in xs:
                y = x[8].get(k)
                if y is not None:
                    out[id(x)][k] = "low" if y <= a else ("high" if y > b else "mid")
        for x in xs:
            for k in W_CAT + ("form",):
                y = x[8].get(k)
                if y is not None:
                    out[id(x)][k] = str(y)
            vb, tb = out[id(x)].get("vol"), out[id(x)].get("trendy")
            if vb and tb:
                out[id(x)]["regime"] = "vol-%s/trend-%s" % (vb, tb)
    return out


def _w_adv(ins, outs):
    """Edge inside the bucket minus edge outside it, and its t."""
    a = [x[5] - x[6] for x in ins]
    b = [x[5] - x[6] for x in outs]
    if len(a) < W_ERA_MIN or len(b) < W_ERA_MIN:
        return None
    ma, mb = sum(a) / len(a), sum(b) / len(b)
    va = sum((v - ma) ** 2 for v in a) / max(1, len(a) - 1)
    vb = sum((v - mb) ** 2 for v in b) / max(1, len(b) - 1)
    se = math.sqrt(va / len(a) + vb / len(b))
    return ma - mb, ((ma - mb) / se if se else 0.0), len(a)


def _w_dossier(g, rs, bk, rd, b):
    """Everything known about one bucket of one read for one lane group."""
    ins = [x for x in rs if bk[id(x)].get(rd) == b]
    outs = [x for x in rs if bk[id(x)].get(rd) is not None and bk[id(x)].get(rd) != b]
    eras = []
    for e in POWER_ERAS:
        eras.append(_w_adv([x for x in ins if x[4] == e], [x for x in outs if x[4] == e]))
    signs = "".join("." if v is None else ("+" if v[0] > 0 else "-") for v in eras)
    mk_pos = mk_tot = 0
    for s in sorted(set(x[0] for x in rs)):
        v = _w_adv([x for x in ins if x[0] == s], [x for x in outs if x[0] == s])
        if v is not None:
            mk_tot += 1
            mk_pos += 1 if v[0] > 0 else 0
    old = _w_adv([x for x in ins if x[4] in POWER_OLD], [x for x in outs if x[4] in POWER_OLD])
    new = _w_adv([x for x in ins if x[4] == "B 2024+"], [x for x in outs if x[4] == "B 2024+"])
    fam = "back" if g[0] in W_BACK else "go"
    th = W_THEORY[fam].get(rd, 0)
    if b in W_HIGH:
        th_b = th
    elif b in W_LOW:
        th_b = -th
    else:
        th_b = 0
    st_in = _p_stats(ins)
    n_e = sum(1 for c in signs if c != ".")
    k_p, k_m = signs.count("+"), signs.count("-")
    if n_e >= 3 and (k_p == n_e or k_m == n_e):
        label = "every era"
    elif n_e >= 3 and max(k_p, k_m) == n_e - 1:
        label = "all but one era"
    elif n_e >= 2:
        label = "flips by era"
    else:
        label = "too few trades"
    way = "+" if k_p > k_m else ("-" if k_m > k_p else "0")
    theory = "" if th_b == 0 else ("theory agrees" if (th_b > 0) == (way == "+") else "AGAINST theory")
    yrs = 10.75
    skip = -sum(x[5] for x in ins) / yrs if way == "-" else None
    sgn = 1 if way == "+" else -1
    ev = (max(k_p, k_m) / float(n_e) if n_e else 0.0) + ((mk_pos if way == "+" else mk_tot - mk_pos) / float(mk_tot)
                                                      if mk_tot else 0.0)
    ev += min(abs(old[1]), 3.0) / 3.0 if (old and old[1] * sgn > 0) else 0.0
    ev += min(abs(new[1]), 3.0) / 3.0 if (new and new[1] * sgn > 0) else 0.0
    return {"_era_t": [v[1] if v else None for v in eras],
            "lane": g[0], "variant": g[1], "exit": g[2], "read": rd, "bucket": b, "n": len(ins), "evidence": round(ev, 2),
            "net_r": round(st_in[1], 4) if st_in else "", "eras": signs, "label": label, "way": way,
            "markets_pos": "%d/%d" % (mk_pos, mk_tot), "old_adv": round(old[0], 4) if old else "",
            "old_t": round(old[1], 2) if old else "", "new_adv": round(new[0], 4) if new else "",
            "new_t": round(new[1], 2) if new else "", "theory": theory,
            "skip_gain_r_per_year": round(skip, 1) if skip is not None else ""}


def run_when(rep, rows):
    rep.p("")
    rep.p("-" * 110)
    rep.p("C. SIGNALS   which reads predict a lane working or failing, judged one by one (nothing dropped by a luck count)")
    rep.p("-" * 110)
    rep.p("For each read and bucket: ADVANTAGE = the lane's edge inside the bucket minus its edge outside it. 'eras' shows")
    rep.p("its sign in 2014-17, 2018-19, 2020-21, 2024+ ('.' = too few trades). Thirds are cut on 2014-21 only, so the")
    rep.p("2024+ column is out of sample. markets = on how many markets the advantage was positive. skip = net R a year")
    rep.p("the lane would have saved by not trading that bucket (only shown for buckets that point the bad way).")
    rep.p("Listed per lane: the 12 buckets with the most evidence, ranked by EVIDENCE = share of eras pointing the same way +")
    rep.p("share of markets agreeing + strength on 2014-21 + strength on 2024+ in the same direction (each 0-1, max 4).")
    rep.p("Nothing is labelled luck: the columns are the evidence. Every bucket of every read is in signal_dossier.csv.")
    groups = _w_groups(rows)
    reads = W_NUM + W_CAT + ("form", "regime")
    dossier = []
    for g, rs in sorted(groups.items()):
        _w_form(rs)
        bk = _w_bucket(rs)
        lines = []
        for rd in reads:
            for b in sorted(set(v.get(rd) for v in (bk[id(x)] for x in rs) if v.get(rd) is not None)):
                dd = _w_dossier(g, rs, bk, rd, b)
                dossier.append(dd)
                if dd["label"] != "too few trades" and dd["way"] != "0":
                    lines.append(dd)
        if not lines:
            continue
        rep.p("")
        rep.p("%s %s %s   (%d trades)" % (g[0], g[1], g[2], len(rs)))
        lines.sort(key=lambda d: -d["evidence"])
        for d in lines[:12]:
            rep.p("  ev %.2f  %-14s = %-22s %s %-15s n %5d  net %+6.3f  old adv %+6.3f t%+5.1f  new adv %s  mkts+ %-5s %s%s" %
                  (d["evidence"], d["read"], d["bucket"], d["eras"], d["label"], d["n"], d["net_r"] or 0, d["old_adv"] or 0,
                   d["old_t"] or 0,
                   ("%+6.3f t%+5.1f" % (d["new_adv"], d["new_t"])) if d["new_adv"] != "" else "     n/a     ",
                   d["markets_pos"], d["theory"],
                   ("  skip saves %+.1f R/yr" % d["skip_gain_r_per_year"]) if d["skip_gain_r_per_year"] != "" else ""))
    A._write_csv(os.path.join(rep.dir, "signal_dossier.csv"),
                 [dict((k, v) for k, v in d.items() if not k.startswith("_")) for d in dossier],
                 first=("lane", "variant", "exit", "read", "bucket", "evidence", "n", "net_r", "eras", "label", "way"))
    run_months(rep, groups)
    run_detect(rep, groups)
    run_luck(rep, dossier)
    run_earners(rep, groups)
    run_books(rep, rows, groups)
    run_part_i(rep, rows, groups)
    run_part_j(rep, rows, groups)
    run_part_k(rep, rows)


def run_months(rep, groups):
    """WHEN: month by month. Good months vs bad months of each lane, what the market looked like then, whether a good
    month can be seen coming (the month before, or the market's own trend), and what trending months looked like."""
    rep.p("")
    rep.p("-" * 110)
    rep.p("D. WHEN   month by month (each lane on its own primary exit; markets pooled, each market-month counted once)")
    rep.p("-" * 110)
    rep.p("good month = the lane made net R > 0 on that market that month. Columns are averages over those months.")
    rep.p("move = the market's move over the month in daily ATRs (signed with nothing: size only); straight = efficiency")
    rep.p("of the daily closes (1 = one straight line); ATR% = daily ATR as % of price; stop = average stop in daily ATRs;")
    rep.p("win / loss = average R of winning / losing trades; next good = how often the NEXT month was good too.")
    rep.p("TREND MONTHS = the market moved 3+ daily ATRs net with straightness 0.3+ (fixed before looking).")
    allm = []
    for g, rs in sorted(groups.items()):
        cell = defaultdict(list)
        for x in rs:
            ym = time.strftime("%Y-%m", time.gmtime(x[8].get("_t_in", 0)))
            cell[(x[0], ym)].append(x)
        months = []
        for (s, ym), xs in sorted(cell.items()):
            mm = P_MONTHS.get((s, ym))
            if not mm or len(xs) < 3:
                continue
            net = sum(x[5] for x in xs)
            wins = [x[5] for x in xs if x[5] > 0]
            loss = [x[5] for x in xs if x[5] <= 0]
            risk = [x[8]["risk_size"] for x in xs if x[8].get("risk_size") is not None]
            months.append({"lane": g[0], "variant": g[1], "exit": g[2], "market": s, "month": ym, "era": xs[0][4],
                           "trades": len(xs), "net_r": round(net, 3), "edge": round(sum(x[5] - x[6] for x in xs) / len(xs), 4),
                           "win_rate": round(len(wins) / float(len(xs)), 3),
                           "avg_win": round(sum(wins) / len(wins), 3) if wins else "",
                           "avg_loss": round(sum(loss) / len(loss), 3) if loss else "",
                           "stop_atr": round(sum(risk) / len(risk), 3) if risk else "",
                           "move_atr": round(abs(mm["move_atr"]), 2), "straight": round(mm["er"], 3),
                           "atr_pct": round(mm["atr_pct"], 3),
                           "trend_month": 1 if (abs(mm["move_atr"]) >= 3 and mm["er"] >= 0.3) else 0})
        if len(months) < 12:
            continue
        allm += months
        bym = defaultdict(dict)
        for mo in months:
            bym[mo["market"]][mo["month"]] = mo
        nxt = {"good": [], "bad": []}
        for s, d in bym.items():
            ks = sorted(d)
            for a, b in zip(ks, ks[1:]):
                ya, ma = int(a[:4]), int(a[5:])
                if (ya * 12 + ma + 1) != (int(b[:4]) * 12 + int(b[5:])):
                    continue
                nxt["good" if d[a]["net_r"] > 0 else "bad"].append(1 if d[b]["net_r"] > 0 else 0)

        def avg(ms, k):
            v = [m_[k] for m_ in ms if m_[k] != ""]
            return sum(v) / len(v) if v else 0.0
        good = [m_ for m_ in months if m_["net_r"] > 0]
        bad = [m_ for m_ in months if m_["net_r"] <= 0]
        rep.p("")
        rep.p("%s %s %s   %d market-months, %d good (%.0f%%)" % (g[0], g[1], g[2], len(months), len(good),
                                                                 100.0 * len(good) / len(months)))
        rep.p("            months  net R/mo  move  straight  ATR%   stop  win%   win R  loss R  next good")
        for name, ms, nx in (("good", good, nxt["good"]), ("bad", bad, nxt["bad"])):
            if ms:
                rep.p("  %-9s %6d  %+8.2f  %4.1f  %8.2f  %5.2f  %5.2f  %4.0f  %+6.2f  %+6.2f  %s" %
                      (name, len(ms), avg(ms, "net_r"), avg(ms, "move_atr"), avg(ms, "straight"), avg(ms, "atr_pct"),
                       avg(ms, "stop_atr"), 100 * avg(ms, "win_rate"), avg(ms, "avg_win"), avg(ms, "avg_loss"),
                       ("%.0f%% of %d" % (100.0 * sum(nx) / len(nx), len(nx))) if nx else "-"))
        tm = [m_ for m_ in months if m_["trend_month"]]
        om = [m_ for m_ in months if not m_["trend_month"]]
        for name, ms in (("trend mo", tm), ("other mo", om)):
            if ms:
                gp = sum(1 for m_ in ms if m_["net_r"] > 0)
                rep.p("  %-9s %6d  %+8.2f  %4.1f  %8.2f  %5.2f  %5.2f  %4.0f  %+6.2f  %+6.2f  good %d%%  edge %+.3f" %
                      (name, len(ms), avg(ms, "net_r"), avg(ms, "move_atr"), avg(ms, "straight"), avg(ms, "atr_pct"),
                       avg(ms, "stop_atr"), 100 * avg(ms, "win_rate"), avg(ms, "avg_win"), avg(ms, "avg_loss"),
                       100 * gp // len(ms), avg(ms, "edge")))
        # good months per year: does it cluster in some years?
        yr = defaultdict(lambda: [0, 0])
        for m_ in months:
            yr[m_["month"][:4]][1] += 1
            yr[m_["month"][:4]][0] += 1 if m_["net_r"] > 0 else 0
        rep.p("  good months by year: " + "  ".join("%s %d/%d" % (y, v[0], v[1]) for y, v in sorted(yr.items())))
    A._write_csv(os.path.join(rep.dir, "months.csv"), allm, first=("lane", "variant", "exit", "market", "month", "era"))
    rep.p("")
    rep.p("every lane x market x month: months.csv (trades, net R, edge, win rate, win/loss R, stop, move, straightness, ATR%)")


# ---- E. CAN WE SEE IT IN TIME: trend detectors, their lag, their false alarms, and each lane gated by them ----
def _trend_month(mm):
    return abs(mm["move_atr"]) >= 3 and mm["er"] >= 0.3


def run_detect(rep, groups):
    rep.p("")
    rep.p("-" * 110)
    rep.p("E. CAN A TREND MONTH BE SEEN IN TIME?   four detectors, each known at the start of the day (fixed before looking)")
    rep.p("-" * 110)
    rep.p("edge20 = yesterday's close in the top/bottom 15% of the last 20 days' range; donch5 = a close beyond the 20-day")
    rep.p("high/low on one of the last 5 days; ma = above the 50-day average with the 20-day average rising (or the mirror);")
    rep.p("er10 = the last 10 days moved 2+ daily ATRs fairly straight. A detector is 'right' when it points the month's way.")
    # E1: lag and false alarms, per detector, pooled and per market
    bym = defaultdict(list)
    for (s, dk), (ym, det, era) in sorted(P_DAYS.items()):
        bym[(s, ym)].append((dk, det, era))
    rep.p("")
    rep.p("E1. trend months caught: % caught at all / by trading day 5 / by day 10, median day it first points the right")
    rep.p("    way; on in other months = share of days it is on in NON-trend months (false alarms); right-way precision =")
    rep.p("    of the days it is on, the share that sit in a trend month going the same way.")
    rep.p("    YARDSTICK, measured on a fake random-walk market where no real trends exist (same detectors, same rules):")
    rep.p("      edge20 by d5 48%  by d10 72%  false 34%  precision 33% | donch5 45% 57% 40% 30% | ma 64% 78% 79% 22% |")
    rep.p("      er10 40% 71% 23% 37%. A detector only helps where it beats these numbers.")
    rep.p("    %-8s %-10s %7s %7s %7s %7s %8s %12s %10s" % ("detector", "market", "trendmo", "caught", "by d5", "by d10",
                                                         "median d", "on other mo", "precision"))
    first_on = {}
    for dname in P_DETECTORS:
        for mk in ["ALL"] + list(A.HOUSE_SYMBOLS):
            tm = caught = c5 = c10 = 0
            lags = []
            other_on = other_tot = on_tot = on_right = 0
            for (s, ym), days in bym.items():
                if mk != "ALL" and s != mk:
                    continue
                mm = P_MONTHS.get((s, ym))
                if not mm:
                    continue
                isT = _trend_month(mm)
                for k, (dk, det, era) in enumerate(days):
                    v = det.get(dname, 0)
                    if v:
                        on_tot += 1
                        on_right += 1 if (isT and v == mm["dir"]) else 0
                    if not isT:
                        other_tot += 1
                        other_on += 1 if v else 0
                if isT:
                    tm += 1
                    lag = next((k for k, (dk, det, era) in enumerate(days) if det.get(dname, 0) == mm["dir"]), None)
                    if mk == "ALL":
                        first_on[(dname, s, ym)] = None if lag is None else days[lag][0]
                    if lag is not None:
                        caught += 1
                        lags.append(lag + 1)
                        c5 += 1 if lag < 5 else 0
                        c10 += 1 if lag < 10 else 0
            if not tm:
                continue
            lags.sort()
            rep.p("    %-8s %-10s %7d %6.0f%% %6.0f%% %6.0f%% %8s %11.0f%% %9.0f%%" %
                  (dname, mk, tm, 100.0 * caught / tm, 100.0 * c5 / tm, 100.0 * c10 / tm,
                   lags[len(lags) // 2] if lags else "-", 100.0 * other_on / max(1, other_tot),
                   100.0 * on_right / max(1, on_tot)))
    # E1b: does a trend month follow a trend month?
    rep.p("")
    rep.p("E1b. does a trend month follow a trend month (same market)? P(trend | last month trend) vs P(trend | not)")
    for mk in A.HOUSE_SYMBOLS:
        ks = sorted(k for k in P_MONTHS if k[0] == mk)
        a = [0, 0]
        b = [0, 0]
        for k1, k2 in zip(ks, ks[1:]):
            y1, m1 = int(k1[1][:4]), int(k1[1][5:])
            if y1 * 12 + m1 + 1 != int(k2[1][:4]) * 12 + int(k2[1][5:]):
                continue
            t1, t2 = _trend_month(P_MONTHS[k1]), _trend_month(P_MONTHS[k2])
            x = a if t1 else b
            x[0] += 1 if t2 else 0
            x[1] += 1
        if a[1] and b[1]:
            rep.p("    %-10s after a trend month %3.0f%% (%d)   after another month %3.0f%% (%d)" %
                  (mk, 100.0 * a[0] / a[1], a[1], 100.0 * b[0] / b[1], b[1]))
    # E2: every lane gated by every detector (trade only when the detector points the trade's way)
    rep.p("")
    rep.p("E2. each lane traded ONLY when a detector points the trade's way, vs when it does not. net R/trade, edge vs the")
    rep.p("    coin flip, and net R a year (all markets). OLD = 2014-21, NEW = 2024+.")
    yrs = {"old": 8.0, "new": 2.75}
    gate_rows = []
    for g, rs in sorted(groups.items()):
        lines = []
        for dname in P_DETECTORS:
            on, off = [], []
            for x in rs:
                t = x[8]
                day = P_DAYS.get((x[0], t.get("_dk")))
                if not day or t.get("_d") is None:
                    continue
                (on if day[1].get(dname, 0) == t["_d"] else off).append(x)
            cells = []
            for name, xs in (("with", on), ("not", off)):
                o = _p_stats([x for x in xs if x[4] in POWER_OLD])
                n = _p_stats([x for x in xs if x[4] == "B 2024+"])
                cells.append((name, o, n))
                gate_rows.append({"lane": g[0], "variant": g[1], "exit": g[2], "detector": dname, "side": name,
                                  "old_n": o[0] if o else 0, "old_r": round(o[1], 4) if o else "",
                                  "old_edge": round(o[2], 4) if o and o[2] is not None else "",
                                  "new_n": n[0] if n else 0, "new_r": round(n[1], 4) if n else "",
                                  "new_edge": round(n[2], 4) if n and n[2] is not None else ""})
            w = cells[0]
            if w[1] and w[2]:
                lines.append("    %-7s with: old %s  %+6.1f R/yr | new %s  %+6.1f R/yr   (not: old %+.3f new %+.3f)" %
                             (dname, _p_fmt(w[1]), w[1][1] * w[1][0] / yrs["old"], _p_fmt(w[2]),
                              w[2][1] * w[2][0] / yrs["new"],
                              cells[1][1][1] if cells[1][1] else 0.0, cells[1][2][1] if cells[1][2] else 0.0))
        if lines:
            rep.p("  %s %s %s" % g)
            for ln in lines:
                rep.p(ln)
    A._write_csv(os.path.join(rep.dir, "gates.csv"), gate_rows, first=("lane", "variant", "exit", "detector", "side"))
    # E3: how much of a trend month's profit is left after the detector first turns on (pdh2 and dipx, the trend lanes)
    rep.p("")
    rep.p("E3. in trend months: the lane's net R in the month, and the part earned on or after the day each detector first")
    rep.p("    pointed the month's way (what a gate could still have caught).")
    for g, rs in sorted(groups.items()):
        if g[0] not in ("pdh2", "dipx", "swing2", "main2", "orb30", "retest2", "pdh", "trend"):
            continue
        line = "  %-8s %-9s %-6s" % g
        tot_all = None
        for dname in P_DETECTORS:
            tot = after = 0.0
            for x in rs:
                t = x[8]
                day = P_DAYS.get((x[0], t.get("_dk")))
                if not day:
                    continue
                ym = day[0]
                mm = P_MONTHS.get((x[0], ym))
                if not mm or not _trend_month(mm):
                    continue
                tot += x[5]
                fo = first_on.get((dname, x[0], ym))
                if fo is not None and t.get("_dk") >= fo:
                    after += x[5]
            tot_all = tot
            line += "  %s: %+.0f of %+.0f" % (dname, after, tot)
        rep.p(line)


# ---- F. LUCK OR REAL: every signal bucket gets a luck number of its own, then theory decides what to do with it ----
def _phi(z):
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def run_luck(rep, dossier):
    """Each bucket's four era t-values are combined (Stouffer): how likely is a bucket with NO real effect to look at
    least this consistent across four independent stretches of years? That is its own luck probability p. Ranked
    together, Benjamini-Hochberg gives q = the expected share of luck among all buckets at least that strong -- so
    a list position, not a blanket count, says how much of the list is luck. Then each bucket is sorted by theory."""
    rep.p("")
    rep.p("-" * 110)
    rep.p("F. LUCK OR REAL   every signal bucket judged on its own luck number, then on theory")
    rep.p("-" * 110)
    rep.p("p = chance a bucket with NO real effect looks at least this consistent across the 4 eras (eras combined).")
    rep.p("q = expected share of luck among all buckets with p at least this small (false discovery rate).")
    rep.p("family = in how many lanes of the same family (breakout/momentum vs reversal) the same read and bucket points")
    rep.p("the same way. A real effect should show in related lanes too; luck usually sits in one.")
    rows = []
    for d in dossier:
        rows.append(d)
    # per-era t values were not kept in the dossier: recompute from old/new columns is not enough, so use the
    # dossier's own era t (stored below by _w_dossier)
    scored = []
    for d in rows:
        ts = d.get("_era_t") or []
        ts = [t for t in ts if t is not None]
        if len(ts) < 3:
            continue
        z = sum(ts) / math.sqrt(len(ts))
        p = 2.0 * (1.0 - _phi(abs(z)))
        d["z"], d["p"] = round(z, 2), p
        scored.append(d)
    scored.sort(key=lambda d: d["p"])
    m = len(scored)
    qmin = 1.0
    for i in range(m - 1, -1, -1):
        q = scored[i]["p"] * m / (i + 1)
        qmin = min(qmin, q)
        scored[i]["q"] = round(qmin, 4)
    # family agreement
    fam = lambda lane: "back" if lane in W_BACK else "go"
    byk = defaultdict(list)
    for d in scored:
        byk[(fam(d["lane"]), d["read"], d["bucket"])].append(d)
    for d in scored:
        sib = [x for x in byk[(fam(d["lane"]), d["read"], d["bucket"])] if x["lane"] != d["lane"]]
        same = sum(1 for x in sib if (x["z"] > 0) == (d["z"] > 0))
        d["family"] = "%d/%d" % (same, len(sib))
        d["family_share"] = same / float(len(sib)) if sib else 0.0
        th = d["theory"]
        strong = d["q"] <= 0.10
        mid = d["q"] <= 0.30
        if strong and th == "theory agrees" and d["family_share"] >= 0.5:
            d["verdict"] = "REAL: luck unlikely, theory and related lanes agree"
        elif strong and th == "theory agrees":
            d["verdict"] = "LIKELY REAL: luck unlikely, theory agrees, related lanes don't"
        elif strong and th == "AGAINST theory":
            d["verdict"] = "REAL BUT AGAINST THEORY: find out why"
        elif strong:
            d["verdict"] = "UNEXPLAINED: luck unlikely, no theory yet"
        elif mid and th == "theory agrees":
            d["verdict"] = "PLAUSIBLE: theory agrees, evidence moderate"
        elif mid:
            d["verdict"] = "WEAK: moderate evidence, no theory"
        else:
            d["verdict"] = "LIKELY LUCK"
    cnt = defaultdict(int)
    for d in scored:
        cnt[d["verdict"].split(":")[0]] += 1
    rep.p("")
    rep.p("%d buckets with 3+ eras of data: " % m + ", ".join("%s %d" % kv for kv in sorted(cnt.items())))
    for head in ("REAL", "LIKELY REAL", "REAL BUT AGAINST THEORY", "UNEXPLAINED", "PLAUSIBLE"):
        ds = [d for d in scored if d["verdict"].split(":")[0] == head]
        if not ds:
            continue
        rep.p("")
        rep.p("%s (%d), strongest first:" % (ds[0]["verdict"], len(ds)))
        for d in ds[:25]:
            rep.p("  %-8s %-8s %-6s %-14s = %-22s %s z%+5.1f p %.4f q %.3f fam %-5s n %5d net %+.3f%s" %
                  (d["lane"], d["variant"], d["exit"], d["read"], d["bucket"], d["eras"], d["z"], d["p"], d["q"],
                   d["family"], d["n"], d["net_r"] or 0,
                   ("  skip saves %+.1f R/yr" % d["skip_gain_r_per_year"]) if d["skip_gain_r_per_year"] != "" else ""))
    A._write_csv(os.path.join(rep.dir, "luck_check.csv"),
                 [dict((k, v) for k, v in d.items() if not k.startswith("_")) for d in scored],
                 first=("verdict", "lane", "variant", "exit", "read", "bucket", "z", "p", "q", "family", "eras"))
    rep.p("")
    rep.p("every bucket with its p, q, family agreement and verdict: luck_check.csv")


# ---- G. THE EARNERS: every lane and filter variant in shadow, switched live only on its own past evidence ----
# Fixed before running (2026-10-08). Nothing here looks ahead: a variant's evidence is built only from its trades
# that had FINISHED before the moment it is asked.
#   variants per lane:  raw | er10 (trade only when the 10-day-move detector agrees) | edge20 (only at the 20-day edge
#                       in the trade's direction) | edge20+cold (and not after a hot streak of the lane) | er10+cold
#                       | calm-skip (reversals only: skip when volatility is under 0.85 of its 1-year average)
#   evidence:           over the variant's last G_WINDOW finished trades (pooled over markets): mean net R and the t of
#                       its edge over the coin flip
#   live bar:           breakout / momentum / other lanes: at least G_MIN_HIST trades, edge t >= 1.0, mean net > 0
#                       REVERSAL lanes (losing badly so far): edge t >= 2.5 AND mean net >= +0.05 -- extremely hard,
#                       but they DO switch on when their own record clears it
#                       control (random) lane: the breakout bar, so its live time shows how often luck alone gets in
#   one variant per lane: of a lane's variants that clear the bar, the one with the highest edge t is the live one
G_WINDOW, G_MIN_HIST = 80, 40
G_BAR = {"go": (1.0, 0.0), "back": (2.5, 0.05), "control": (1.0, 0.0)}


def _g_family(lane):
    if lane == "control":
        return "control"
    return "back" if lane in W_BACK else "go"


def _g_variants(g, x):
    """Which variants of lane g a trade x belongs to."""
    t = x[8]
    day = P_DAYS.get((x[0], t.get("_dk")))
    det = day[1] if day else {}
    d = t.get("_d")
    out = ["raw"]
    if d is None:
        return out
    cold = t.get("form") == "cold"
    if _g_family(g[0]) == "back":
        if t.get("vol") is not None and t["vol"] >= 0.85:
            out.append("calm-skip")
        return out
    if det.get("er10", 0) == d:
        out.append("er10")
        if cold:
            out.append("er10+cold")
    if det.get("edge20", 0) == d:
        out.append("edge20")
        if cold:
            out.append("edge20+cold")
    return out


def _g_ev(hist):
    xs = hist[-G_WINDOW:]
    n = len(xs)
    if n < G_MIN_HIST:
        return None
    e = [a for a, b in xs]
    me = sum(e) / n
    v = sum((y - me) ** 2 for y in e) / (n - 1)
    t = me / math.sqrt(v / n) if v > 0 else 0.0
    return t, sum(b for a, b in xs) / n


def run_earners(rep, groups):
    rep.p("")
    rep.p("-" * 110)
    rep.p("G. THE EARNERS   every lane x filter variant in shadow; live only on its own finished-trade evidence")
    rep.p("-" * 110)
    rep.p("Variants: raw, er10, edge20, edge20+cold, er10+cold (breakout / momentum), calm-skip (reversals). Evidence =")
    rep.p("last %d finished trades of the variant, all markets. Live bar: breakout / momentum edge t >= %.1f and net > 0;"
          % (G_WINDOW, G_BAR["go"][0]))
    rep.p("REVERSALS edge t >= %.1f and net >= +%.2f (extremely hard, but reachable); control = breakout bar (a luck"
          % G_BAR["back"])
    rep.p("test: its live time is what luck alone achieves). One live variant per lane: the strongest that clears its bar.")
    rep.p("YARDSTICK (same code on a fake random-walk market): the live book's edge came out 0 within noise (t -0.6..+0.1),")
    rep.p("the random control lane was live 21% of the time, reversals 0%. Real lanes must beat that.")
    events = []
    for g, rs in groups.items():
        for x in rs:
            t = x[8]
            if t.get("_t_in") is None or t.get("_t_out") is None:
                continue
            events.append((t["_t_in"], g, x, _g_variants(g, x)))
    events.sort(key=lambda e: e[0])
    hist = defaultdict(list)            # (lane group, variant) -> [(edge, net)] finished, in exit order
    pend = []                           # (t_out, key, edge, net)
    import heapq
    live = []                           # (x, group, variant)
    on_time = defaultdict(lambda: [0, 0])   # lane -> [decisions live, decisions]
    for t_in, g, x, vs in events:
        while pend and pend[0][0] <= t_in:
            _, k, e, nr = heapq.heappop(pend)
            hist[k].append((e, nr))
        fam = _g_family(g[0])
        bar_t, bar_net = G_BAR[fam]
        best, best_t = None, None
        for v in ("raw", "er10", "edge20", "edge20+cold", "er10+cold", "calm-skip"):
            ev = _g_ev(hist[(g, v)])
            ok = ev is not None and ev[0] >= bar_t and (ev[1] > 0.0 if bar_net == 0.0 else ev[1] >= bar_net)
            if ok:
                if best_t is None or ev[0] > best_t:
                    best, best_t = v, ev[0]
        on_time[g][1] += 1
        if best is not None and best in vs:
            live.append((x, g, best))
            on_time[g][0] += 1
        for v in vs:
            heapq.heappush(pend, (x[8]["_t_out"], (g, v), x[5] - x[6], x[5]))
    if not live:
        rep.p("no lane ever cleared its bar.")
        return
    yrs = {"2014-17": 4.0, "2018-19": 2.0, "A 2020-21": 2.0, "B 2024+": 2.75}
    rep.p("")
    rep.p("G1. the whole live book, per era (each trade 1R of risk):")
    rep.p("    %-10s %6s %9s %9s %9s %10s %12s" % ("era", "trades", "net R/tr", "edge/tr", "t edge", "net R/yr", "coin flip R/yr"))
    for era in POWER_ERAS:
        xs = [x for x, g, v in live if x[4] == era]
        st = _p_stats(xs)
        if st:
            rep.p("    %-10s %6d %+9.3f %+9.3f %+9.1f %+10.1f %+12.1f" %
                  (era, st[0], st[1], st[2], st[3], sum(x[5] for x in xs) / yrs[era],
                   sum(x[6] for x in xs) / yrs[era]))
    # monthly curve in R: drawdown, underwater, positive months
    mon = defaultdict(float)
    for x, g, v in live:
        mon[time.strftime("%Y-%m", time.gmtime(x[8]["_t_in"]))] += x[5]
    rep.p("")
    rep.p("G2. the live book month by month (net R): per era -- positive months, worst month, max drawdown from a high,")
    rep.p("    longest stretch below a previous high (months).")
    for era in POWER_ERAS:
        ms = sorted(k for k in mon if _p_era(calendar.timegm((int(k[:4]), int(k[5:]), 15, 0, 0, 0))) == era)
        if not ms:
            continue
        eq = peak = dd = 0.0
        under = longest = 0
        for k in ms:
            eq += mon[k]
            if eq >= peak:
                peak, under = eq, 0
            else:
                under += 1
                longest = max(longest, under)
            dd = max(dd, peak - eq)
        pos = sum(1 for k in ms if mon[k] > 0)
        rep.p("    %-10s months %3d  positive %3.0f%%  total %+7.1f R  worst month %+6.1f R  max drawdown %5.1f R  "
              "longest under water %2d mo" % (era, len(ms), 100.0 * pos / len(ms), eq, min(mon[k] for k in ms), dd, longest))
    rep.p("")
    rep.p("G3. who earned it: per lane -- share of its decisions that were live, live trades, net R (old / new), the")
    rep.p("    variants it ran live")
    by = defaultdict(list)
    for x, g, v in live:
        by[g].append((x, v))
    for g in sorted(groups, key=lambda g: (_g_family(g[0]), g[0])):
        lt = by.get(g, [])
        on, tot = on_time[g]
        if not tot:
            continue
        old = [x for x, v in lt if x[4] in POWER_OLD]
        new = [x for x, v in lt if x[4] == "B 2024+"]
        vc = defaultdict(int)
        for x, v in lt:
            vc[v] += 1
        rep.p("    %-8s %-6s %-5s live %5.1f%% of %6d   trades %5d   net old %+7.1f R  new %+7.1f R   %s" %
              (g[0], _g_family(g[0]), g[2], 100.0 * on / tot, tot, len(lt), sum(x[5] for x in old),
               sum(x[5] for x in new), " ".join("%s:%d" % kv for kv in sorted(vc.items(), key=lambda kv: -kv[1]))))
    rep.p("")
    rep.p("G4. per market (net R, old / new):")
    for s in A.HOUSE_SYMBOLS:
        xs = [x for x, g, v in live if x[0] == s]
        if xs:
            o = sum(x[5] for x in xs if x[4] in POWER_OLD)
            n = sum(x[5] for x in xs if x[4] == "B 2024+")
            rep.p("    %-10s trades %5d   old %+7.1f R   new %+7.1f R" % (s, len(xs), o, n))
    A._write_csv(os.path.join(rep.dir, "earners_live.csv"),
                 [{"market": x[0], "lane": g[0], "exit": g[2], "variant": v, "era": x[4],
                   "t_in": time.strftime("%Y-%m-%d %H:%M", time.gmtime(x[8]["_t_in"])),
                   "net_r": round(x[5], 4), "coin_flip_r": round(x[6], 4)} for x, g, v in live],
                 first=("market", "lane", "exit", "variant", "era", "t_in"))
    rep.p("")
    rep.p("every live trade: earners_live.csv")


# ---- H. BOOKS SIDE BY SIDE (2026-10-08): fixed filters, wider room, a learned signal score, cooldowns, contrarian ----
# Everything walks forward in time: a trade can only use what had FINISHED before it was taken.
#   H0 base      every breakout / momentum trade of the rebuilt lanes, primary exit
#   H1 filtered  breakout / momentum lanes (rebuilt and old), only when edge20 OR er10 agrees with the trade
#   H2 wide      the rebuilt breakout lanes on their WIDE stop and the 5-day chandelier exit, filtered as H1
#                (more room per trade: costs are a smaller share of a bigger R)
#   H3 scored    every lane of every family. Each signal bucket (per family) carries a WEIGHT learned from finished
#                trades: its advantage over the family's average, shrunk by its own t (|t| < 1 -> weight 0, |t| >= 3 ->
#                full), with old evidence fading (half-life H_HALF trades), so a signal that stops predicting loses its
#                weight and a strong one keeps it. Expected R = the lane's own fading average + the trade's score.
#                Trade only if expected R clears the family bar (breakout 0, reversal +0.10). Breakout size 1x-2x by
#                expected R ("more volume" when the evidence is strong); reversal 1x.
#   H4 cooldown  H3, plus: after 3 winning live trades in a row a lane sits out its next 3 signals
#   H5 contrarian a lane is live only while its last W finished trades were COLD (edge t <= -1). Stress-tested:
#                windows 40 / 80 / 160, every era and market apart, and the random control lane on its own (if the
#                control lane 'earns' with it, it is an artifact of the measurement, not an edge)
H_HALF = 500.0
H_LANE_HALF = 300.0
H_BAR = {"go": 0.0, "back": 0.10, "control": 0.0}
H_GO_REBUILT = ("main2", "orb30", "orb60", "pdh2", "retest2")
H_WIDE = {"main2": "box", "orb30": "range", "orb60": "range", "pdh2": "mid", "retest2": "0.25D"}
H_FEATURES = W_NUM + W_CAT + ("form",)
H_YRS = {"2014-17": 4.0, "2018-19": 2.0, "A 2020-21": 2.0, "B 2024+": 2.75}


def _h_agree(x, names=("edge20", "er10")):
    t = x[8]
    day = P_DAYS.get((x[0], t.get("_dk")))
    if not day or t.get("_d") is None:
        return False
    return any(day[1].get(n, 0) == t["_d"] for n in names)


def _h_report(rep, name, book, days_total=None):
    """book = [(row, size)]. One line per era plus the month curve."""
    rep.p("  %s" % name)
    if not book:
        rep.p("    (no trades)")
        return
    for era in POWER_ERAS:
        xs = [(x, z) for x, z in book if x[4] == era]
        if not xs:
            continue
        n = len(xs)
        risk = sum(z for x, z in xs)
        net = sum(x[5] * z for x, z in xs)
        edge = sum((x[5] - x[6]) * z for x, z in xs)
        mon = defaultdict(float)
        for x, z in xs:
            mon[time.strftime("%Y-%m", time.gmtime(x[8]["_t_in"]))] += x[5] * z
        ms = sorted(mon)
        eq = peak = dd = 0.0
        under = longest = 0
        for k in ms:
            eq += mon[k]
            if eq >= peak:
                peak, under = eq, 0
            else:
                under += 1
                longest = max(longest, under)
            dd = max(dd, peak - eq)
        pos = sum(1 for k in ms if mon[k] > 0)
        rep.p("    %-10s trades %5d  net %+.3f R per 1R risked  edge %+.3f  net %+7.1f R/yr  months+ %3.0f%%  "
              "max dd %6.1f R  under water %2d mo" %
              (era, n, net / risk, edge / risk, net / H_YRS[era], 100.0 * pos / max(1, len(ms)), dd, longest))


class _HWeights(object):
    """Fading per-family signal weights (see H3)."""

    def __init__(self):
        self.base = defaultdict(lambda: [0.0, 0.0])          # family -> [decayed sum edge, decayed count]
        self.b = defaultdict(lambda: [0.0, 0.0, 0.0])        # (family, feature, bucket) -> [sum adv, sum adv^2, count]
        self.lane = defaultdict(lambda: [0.0, 0.0])          # lane group -> [decayed sum net, decayed count]
        self.k = 0.5 ** (1.0 / H_HALF)
        self.kl = 0.5 ** (1.0 / H_LANE_HALF)

    def learn(self, fam, g, buckets, edge, net):
        bs = self.base[fam]
        mean = bs[0] / bs[1] if bs[1] > 0 else 0.0
        adv = edge - mean
        bs[0] = bs[0] * self.k + edge
        bs[1] = bs[1] * self.k + 1.0
        for fb in buckets:
            v = self.b[(fam,) + fb]
            v[0] = v[0] * self.k + adv
            v[1] = v[1] * self.k + adv * adv
            v[2] = v[2] * self.k + 1.0
        ln = self.lane[g]
        ln[0] = ln[0] * self.kl + net
        ln[1] = ln[1] * self.kl + 1.0

    def weight(self, fam, fb):
        v = self.b.get((fam,) + fb)
        if not v or v[2] < 30:
            return 0.0
        m = v[0] / v[2]
        var = max(v[1] / v[2] - m * m, 1e-9)
        t = m / math.sqrt(var / v[2])
        shrink = min(max((abs(t) - 1.0) / 2.0, 0.0), 1.0)
        return m * shrink

    def expect(self, fam, g, buckets):
        ln = self.lane[g]
        if ln[1] < 40:
            return None, 0.0
        sc = sum(self.weight(fam, fb) for fb in buckets)
        return ln[0] / ln[1] + sc, sc


def _h_buckets(x, bk):
    out = []
    b = bk.get(id(x), {})
    for f in H_FEATURES:
        if f in b:
            out.append((f, b[f]))
    t = x[8]
    day = P_DAYS.get((x[0], t.get("_dk")))
    if day and t.get("_d") is not None:
        for n in P_DETECTORS:
            v = day[1].get(n, 0)
            out.append((n, "with" if v == t["_d"] else ("against" if v else "off")))
    return out


def _h_walk(groups, bk, mode, window=80, cooldown=False):
    """Walk forward over every trade of every group. mode: 'score' or 'contra' or 'hot'. -> [(row, size, group)]"""
    import heapq
    ev = []
    for g, rs in groups.items():
        for x in rs:
            if x[8].get("_t_in") is not None and x[8].get("_t_out") is not None:
                ev.append((x[8]["_t_in"], id(x), g, x))
    ev.sort(key=lambda e: (e[0], e[1]))
    W = _HWeights()
    pend = []
    hist = defaultdict(list)
    live_done = defaultdict(list)       # lane -> finished live results in exit order (for cooldown)
    live_pend = []
    skip = defaultdict(int)
    ranks = defaultdict(list)          # family -> the last 500 expected-R values seen (rank mode)
    out = []
    seq = 0
    for t_in, _, g, x in ev:
        while pend and pend[0][0] <= t_in:
            _, _, fam, gg, bs, e, nr = heapq.heappop(pend)
            W.learn(fam, gg, bs, e, nr)
            hist[gg].append(e)
        while live_pend and live_pend[0][0] <= t_in:
            _, _, gg, nr = heapq.heappop(live_pend)
            live_done[gg].append(nr)
            if cooldown and len(live_done[gg]) >= 3 and all(v > 0 for v in live_done[gg][-3:]):
                skip[gg] = 3
                live_done[gg].append(-1.0)      # a marker so the same streak does not re-trigger
        fam = _g_family(g[0])
        bs = _h_buckets(x, bk)
        take, size = False, 1.0
        if mode == "rank":
            e, sc = W.expect(fam, g, bs)
            if e is not None:
                past = ranks[fam]
                if len(past) >= 200:
                    srt = sorted(past)
                    p80, p95 = srt[int(0.80 * len(srt))], srt[int(0.95 * len(srt))]
                    if e >= p80 and (fam != "back" or e >= H_BAR["back"]):
                        take = True
                        size = 2.0 if (fam == "go" and e >= p95) else 1.0
                past.append(e)
                if len(past) > 500:
                    past.pop(0)
        elif mode == "score":
            e, sc = W.expect(fam, g, bs)
            if e is not None and e > H_BAR[fam]:
                take = True
                if fam == "go":
                    size = 1.0 + min(max(e / 0.10, 0.0), 1.0)
        else:
            h = hist[g][-window:]
            if len(h) >= max(20, window // 2):
                n = len(h)
                m = sum(h) / n
                v = sum((y - m) ** 2 for y in h) / (n - 1)
                tt = m / math.sqrt(v / n) if v > 0 else 0.0
                take = tt <= -1.0 if mode == "contra" else tt >= 1.0
        if take and skip[g] > 0:
            skip[g] -= 1
            take = False
        if take:
            out.append((x, size, g))
            seq += 1
            heapq.heappush(live_pend, (x[8]["_t_out"], seq, g, x[5]))
        seq += 1
        heapq.heappush(pend, (x[8]["_t_out"], seq, fam, g, bs, x[5] - x[6], x[5]))
    return out


def run_books(rep, rows, groups):
    rep.p("")
    rep.p("-" * 110)
    rep.p("H. BOOKS SIDE BY SIDE   (net R per 1R risked; sized books count each trade at its size)")
    rep.p("-" * 110)
    for line in ("H0 base: rebuilt breakout lanes, every trade.  H1 filtered: breakout / momentum lanes only when edge20 or",
                 "er10 agrees.  H2 wide: rebuilt breakout lanes on the wide stop + 5-day chandelier, filtered as H1.",
                 "H3 scored: learned, fading signal weights over every lane (breakout sized 1-2x by expected R; reversals",
                 "need expected R >= +0.10).  H4: H3 + cooldown after 3 wins in a row.  H5 contrarian: lane live only while",
                 "its last W finished trades were cold.  Signal thirds use cut points from 2014-21 (outcome-blind).",
                 "YARDSTICK (same code, fake random-walk market): every book's edge sat between -0.13 and +0.16 per 1R in",
                 "single eras (mostly -0.04..+0.03), none positive in all eras; H3 kept weight on only 3 of 48 breakout buckets.",
                 "A real book has to beat that: a positive edge in EVERY era, not one good stretch."):
        rep.p(line)
    bk = {}
    for g, rs in groups.items():
        bk.update(_w_bucket(rs))
    go_groups = dict((g, rs) for g, rs in groups.items() if _g_family(g[0]) == "go")
    H0 = [(x, 1.0) for g, rs in go_groups.items() if g[0] in H_GO_REBUILT for x in rs]
    H1 = [(x, 1.0) for g, rs in go_groups.items() for x in rs if _h_agree(x)]
    wide = []
    for x in rows:
        if x[1] in H_WIDE and x[2] == H_WIDE[x[1]] and x[3] == "5d" and x[6] is not None and _h_agree(x):
            wide.append((x, 1.0))
    rep.p("")
    _h_report(rep, "H0 base (rebuilt breakout lanes, primary exit, no filter)", H0)
    _h_report(rep, "H1 filtered (edge20 or er10 agrees)", H1)
    _h_report(rep, "H2 wide (wide stop + 5-day chandelier, filtered)", wide)
    sc = _h_walk(groups, bk, "score")
    _h_report(rep, "H3 scored (learned fading weights, all families)", [(x, z) for x, z, g in sc])
    by = defaultdict(int)
    for x, z, g in sc:
        by[_g_family(g[0])] += 1
    rep.p("    H3 trades by family: " + ", ".join("%s %d" % kv for kv in sorted(by.items())) +
          "   (control lane trades = what the score lets through on pure luck)")
    cd = _h_walk(groups, bk, "score", cooldown=True)
    _h_report(rep, "H4 scored + cooldown after 3 wins in a row", [(x, z) for x, z, g in cd])
    # H5 contrarian, with its stress test
    rep.p("")
    rep.p("H5 CONTRARIAN SWITCHING and its stress test (live only while the lane's last W finished trades were cold;")
    rep.p("   'hot' = the opposite rule, for comparison; 'control only' = the same rule on the random lane alone)")
    for wdw in (40, 80, 160):
        co = _h_walk(groups, bk, "contra", window=wdw)
        ho = _h_walk(groups, bk, "hot", window=wdw)
        _h_report(rep, "contrarian W=%d, all lanes" % wdw, [(x, 1.0) for x, z, g in co if g[0] != "control"])
        _h_report(rep, "hot W=%d, all lanes" % wdw, [(x, 1.0) for x, z, g in ho if g[0] != "control"])
        _h_report(rep, "contrarian W=%d, control lane only (must show NO edge)" % wdw,
                  [(x, 1.0) for x, z, g in co if g[0] == "control"])
        if wdw == 80:
            rep.p("    contrarian W=80 by market (net R old / new):")
            for s in A.HOUSE_SYMBOLS:
                xs = [x for x, z, g in co if x[0] == s and g[0] != "control"]
                if xs:
                    rep.p("      %-10s old %+7.1f  new %+7.1f   (trades %d)" %
                          (s, sum(x[5] for x in xs if x[4] in POWER_OLD), sum(x[5] for x in xs if x[4] == "B 2024+"),
                           len(xs)))
    # what the score learned: the strongest weights at the end
    rep.p("")
    rep.p("H6. the score's weights at the END of the data (advantage in R per trade, after shrinking by t; 0 = demoted):")
    W = _HWeights()
    import heapq
    ev = sorted(((x[8]["_t_out"], id(x), g, x) for g, rs in groups.items() for x in rs
                 if x[8].get("_t_out") is not None), key=lambda e: (e[0], e[1]))
    for _, _, g, x in ev:
        W.learn(_g_family(g[0]), g, _h_buckets(x, bk), x[5] - x[6], x[5])
    ws = []
    for key in W.b:
        w = W.weight(key[0], key[1:])
        ws.append((w, key))
    for fam in ("go", "back", "control"):
        f = sorted([z for z in ws if z[1][0] == fam], key=lambda z: -abs(z[0]))
        live = [z for z in f if z[0] != 0.0]
        rep.p("  %-7s %d of %d signal buckets still carry weight; strongest:" % (fam, len(live), len(f)))
        for w, key in live[:12]:
            rep.p("     %+.3f  %s = %s" % (w, key[1], key[2]))


# ---- I. (2026-10-08) standout days, H2 dissected, real money sizing, and more contenders for diversity ----
I_WEEKEND = (4, 5, 6)                  # Friday, Saturday, Sunday (FX day key)


def _i_h6(x):
    """H6's lessons (learned on ALL data -- in-sample, stated): skip breakout trades taken 5h+ after the open and on
    Fridays / weekends."""
    t = x[8]
    return t.get("hour") != "5h+" and t.get("weekday") not in I_WEEKEND


def _i_month_r(book):
    mon = defaultdict(float)
    for x, z in book:
        mon[time.strftime("%Y-%m", time.gmtime(x[8]["_t_in"]))] += x[5] * z
    return mon


def _i_portfolio(rep, name, book, risk_pcts=(0.10, 0.25, 0.50), max_open=4.0):
    """$10,000 per era, each trade risks pct% of CURRENT equity x its size, no new trade if open risk would pass
    max_open% of equity. Monthly returns, compounding."""
    rep.p("  %s" % name)
    for pct in risk_pcts:
        line = "    risk %.2f%%/trade:" % pct
        for era in POWER_ERAS:
            xs = sorted([(x, z) for x, z in book if x[4] == era], key=lambda e: e[0][8]["_t_in"])
            if not xs:
                continue
            import heapq
            eq, openq, open_risk = 10000.0, [], 0.0
            mon = defaultdict(float)
            skipped = 0
            start = {}
            for x, z in xs:
                t = x[8]["_t_in"]
                while openq and openq[0][0] <= t:
                    to, _, amt, r = heapq.heappop(openq)
                    open_risk -= amt
                    pnl = amt * r
                    eq += pnl
                    mon[time.strftime("%Y-%m", time.gmtime(to))] += pnl
                amt = eq * pct / 100.0 * z
                if open_risk + amt > eq * max_open / 100.0:
                    skipped += 1
                    continue
                open_risk += amt
                heapq.heappush(openq, (x[8]["_t_out"], id(x), amt, x[5]))
            while openq:
                to, _, amt, r = heapq.heappop(openq)
                eq += amt * r
                mon[time.strftime("%Y-%m", time.gmtime(to))] += amt * r
            ms = sorted(mon)
            e2, peak, dd, under, longest = 10000.0, 10000.0, 0.0, 0, 0
            rets = []
            for k in ms:
                r = mon[k] / e2
                rets.append(r)
                e2 += mon[k]
                if e2 >= peak:
                    peak, under = e2, 0
                else:
                    under += 1
                    longest = max(longest, under)
                dd = max(dd, (peak - e2) / peak)
            yrs = H_YRS[era]
            cagr = (e2 / 10000.0) ** (1.0 / yrs) - 1.0 if e2 > 0 else -1.0
            pos = sum(1 for r in rets if r > 0)
            line += "  %s %+5.1f%%/yr (%+.2f%%/mo) dd %4.1f%% under %2dmo m+ %2.0f%% worst %+4.1f%%" % (
                era[-7:], 100 * cagr, 100 * ((1 + cagr) ** (1 / 12.0) - 1), 100 * dd, longest,
                100.0 * pos / max(1, len(rets)), 100 * min(rets) if rets else 0.0)
        rep.p(line)


def run_part_i(rep, rows, groups):
    rep.p("")
    rep.p("-" * 110)
    rep.p("I. STANDOUT DAYS, H2 DISSECTED, REAL-MONEY SIZING, AND MORE CONTENDERS")
    rep.p("-" * 110)
    rep.p("YARDSTICK (fake random-walk market): top-20% days came out at edge -0.24..+0.09 per era (no era-stable gain),")
    rep.p("H2 + H6 at 0.25% risk: -35%..+2% a year. On real data a book counts only if it beats that in EVERY era.")
    # the H2 universe: wide stop + 5-day chandelier on the rebuilt breakout lanes
    h2g = defaultdict(list)
    for x in rows:
        if x[1] in H_WIDE and x[2] == H_WIDE[x[1]] and x[3] == "5d" and x[6] is not None and x[8].get("_t_in"):
            h2g[(x[1], x[2], "5d")].append(x)
    bk2 = {}
    for g, rs in h2g.items():
        _w_form(rs)
        bk2.update(_w_bucket(rs))
    H2 = [(x, 1.0) for rs in h2g.values() for x in rs if _h_agree(x)]
    H2s = [(x, z) for x, z in H2 if _i_h6(x)]
    # I1: standout days (top 20% of the learned expected R, judged against past scores only)
    rep.p("")
    rep.p("I1. STANDOUT DAYS: a trade is taken only if its expected R (lane's fading average + learned signal weights) is")
    rep.p("    in the top 20% of the last 500 seen in its family; top 5% gets double size. Reversals also need >= +0.10.")
    bk = {}
    for g, rs in groups.items():
        bk.update(_w_bucket(rs))
    top_all = _h_walk(groups, bk, "rank")
    _h_report(rep, "top-20% days, every lane and family", [(x, z) for x, z, g in top_all])
    fam = defaultdict(int)
    for x, z, g in top_all:
        fam[_g_family(g[0])] += 1
    rep.p("    by family: " + ", ".join("%s %d" % kv for kv in sorted(fam.items())))
    top_h2 = _h_walk(h2g, bk2, "rank")
    _h_report(rep, "top-20% days inside the H2 universe (wide + 5-day trail, no detector filter)",
              [(x, z) for x, z, g in top_h2])
    top_h2f = [(x, z) for x, z, g in top_h2 if _h_agree(x)]
    _h_report(rep, "top-20% days inside H2 AND the detector agrees", top_h2f)
    # I2: H2 dissected
    rep.p("")
    rep.p("I2. H2 DISSECTED (net R per trade, edge) -- by lane, by market, by direction, and with H6's lessons applied")
    _h_report(rep, "H2 as in part H", H2)
    _h_report(rep, "H2 + H6 (no trades 5h+ after the open, none on Friday / weekend) -- H6 was learned on all years", H2s)
    for lane in sorted(set(x[1] for x, z in H2)):
        _h_report(rep, "H2 lane %s" % lane, [(x, z) for x, z in H2 if x[1] == lane])
    for s in A.HOUSE_SYMBOLS:
        _h_report(rep, "H2 market %s" % s, [(x, z) for x, z in H2 if x[0] == s])
    for d, nm in ((1, "longs"), (-1, "shorts")):
        _h_report(rep, "H2 %s" % nm, [(x, z) for x, z in H2 if x[8].get("_d") == d])
    # 2018-19: what was different?
    rep.p("")
    rep.p("    what the market looked like per era (all six markets, months): share of trend months, average move, ATR%")
    for era in POWER_ERAS:
        ms = [mm for (s, ym), mm in P_MONTHS.items() if _p_era(calendar.timegm((int(ym[:4]), int(ym[5:]), 15, 0, 0, 0))) == era]
        if ms:
            tm = sum(1 for mm in ms if _trend_month(mm))
            rep.p("      %-10s months %3d  trend months %3.0f%%  average |move| %.1f ATR  straightness %.2f" %
                  (era, len(ms), 100.0 * tm / len(ms), sum(abs(mm["move_atr"]) for mm in ms) / len(ms),
                   sum(mm["er"] for mm in ms) / len(ms)))
    # I3: real-money sizing
    rep.p("")
    rep.p("I3. REAL-MONEY SIZING: $10,000 at the start of each era, risk = x% of current equity per trade (x size),")
    rep.p("    open risk capped at 4% of equity (a signal that would pass the cap is skipped). %/yr compounded, dd = worst")
    rep.p("    drop from a high, under = longest months below a high, m+ = share of positive months, worst = worst month.")
    _i_portfolio(rep, "H2 + H6", H2s)
    _i_portfolio(rep, "top-20% days inside H2 + detector agrees", top_h2f)
    # I4: more contenders -- diversity, long and short term
    rep.p("")
    rep.p("I4. MORE CONTENDERS (for diversity; long-term and short-term), each fixed before running:")
    cont = {}
    rev = [(x, 1.0) for g, rs in groups.items() if _g_family(g[0]) == "back" and g[0] not in ("rsi2",)
           for x in rs if not _h_agree(x, ("edge20", "er10", "donch5"))]
    cont["R1 reversals only when NO trend detector is on (fades belong in ranges)"] = rev
    rev2 = [(x, z) for x, z in rev if x[8].get("vol") is not None and x[8]["vol"] >= 1.0]
    cont["R2 R1 and volatility at or above its 1-year average (fades need movement)"] = rev2
    sw = [(x, 1.0) for g, rs in groups.items() if g[0] == "swing2" for x in rs if x[8].get("with_50d") == 1]
    cont["S1 swing2 (daily Donchian) only with the 50-day trend (long-term)"] = sw
    rl = [(x, 1.0) for g, rs in groups.items() if g[0] == "rsi2" and g[1] == "long" for x in rs]
    cont["S2 rsi2 long (Connors dip-buy above the 200-day average, long-term)"] = rl
    bc = [(x, 1.0) for g, rs in groups.items() if g[0] == "bigcont" for x in rs if x[8].get("trendy", 1) is not None]
    cont["S3 bigcont (follow an outsized day)"] = bc
    br = [(x, 1.0) for g, rs in groups.items() if g[0] == "bigrev" for x in rs
          if x[8].get("trendy") is not None and x[8]["trendy"] < 0.25]
    cont["R3 bigrev (fade an outsized day) only when the last 20 days were directionless (ER20 < 0.25)"] = br
    nr = [(x, 1.0) for g, rs in groups.items() if g[0] == "nr7" for x in rs
          if x[8].get("prev_range") is not None and x[8]["prev_range"] < 0.8]
    cont["B1 nr7 lane only after a narrow day (yesterday's range < 0.8 daily ATR)"] = nr
    for k, v in cont.items():
        _h_report(rep, k, v)
    # I5: do the contenders move together? monthly correlation with H2+H6
    rep.p("")
    rep.p("I5. DIVERSIFICATION: correlation of monthly net R with H2 + H6 (low or negative = they earn at other times)")
    base = _i_month_r(H2s)
    for k, v in cont.items():
        mo = _i_month_r(v)
        ks = sorted(set(base) & set(mo))
        if len(ks) < 12:
            rep.p("    %-70s too few months" % k[:70])
            continue
        a = [base[q] for q in ks]
        b = [mo[q] for q in ks]
        rep.p("    %-70s corr %+.2f over %d months" % (k[:70], A._corr(a, b) or 0.0, len(ks)))
    combo = H2s + [(x, 1.0) for x, z in nr] + [(x, 1.0) for x, z in sw]
    rep.p("")
    _h_report(rep, "COMBINED book: H2 + H6, plus B1 and S1", combo)
    _i_portfolio(rep, "COMBINED book", combo)


# ---- J. (2026-10-09) per-trade odds, asymmetry / capital profile, and new contenders ----
def _sig(z):
    return 1.0 / (1.0 + math.exp(-max(-30.0, min(30.0, z))))


def _j_odds(rep, groups, bk, fam_name):
    """Walk-forward logistic model of P(trade wins after costs) from the trade's own reads + its lane. It predicts each
    trade BEFORE learning from it (only finished trades teach it). Then: do predicted odds match real odds?"""
    import heapq
    ev = sorted(((x[8]["_t_in"], id(x), g, x) for g, rs in groups.items() if _g_family(g[0]) == fam_name
                 for x in rs if x[8].get("_t_in") and x[8].get("_t_out")), key=lambda e: (e[0], e[1]))
    w = defaultdict(float)
    lr, l2 = 0.02, 0.0005
    pend, preds, seq = [], [], 0
    for t_in, _, g, x in ev:
        while pend and pend[0][0] <= t_in:
            _, _, feats, y = heapq.heappop(pend)
            z = sum(w[f] for f in feats)
            err = y - _sig(z)
            for f in feats:
                w[f] += lr * (err - l2 * w[f])
        feats = [("lane", g[0]), ("bias",)] + [("b",) + fb for fb in _h_buckets(x, bk)]
        preds.append((_sig(sum(w[f] for f in feats)), x))
        seq += 1
        heapq.heappush(pend, (x[8]["_t_out"], seq, feats, 1.0 if x[5] > 0 else 0.0))
    rep.p("  family %s: %d trades. Deciles of the predicted win chance RANKED WITHIN EACH LANE (so a lane that simply"
          % (fam_name, len(preds)))
    rep.p("    wins more often by design does not fill the top deciles):")
    for per, eras in (("2014-21", POWER_OLD), ("2024+", ("B 2024+",))):
        ps = sorted([(p, x) for p, x in preds if x[4] in eras], key=lambda e: e[1][8]["_t_in"])
        ps = ps[len(ps) // 10:] if len(ps) > 500 else ps          # the first stretch is the model warming up
        if len(ps) < 200:
            continue
        bylane = defaultdict(list)
        for p, x in ps:
            bylane[x[1]].append(p)
        for v in bylane.values():
            v.sort()
        import bisect
        dec = defaultdict(list)
        for p, x in ps:
            v = bylane[x[1]]
            q = (bisect.bisect_left(v, p) + bisect.bisect_right(v, p)) / 2.0 / len(v)
            dec[min(9, int(q * 10))].append((p, x))
        mean_net = sum(x[5] for p, x in ps) / len(ps)
        mean_ed = sum(x[5] - x[6] for p, x in ps) / len(ps)
        rep.p("    %s (all trades: net %+.3f, edge %+.3f)" % (per, mean_net, mean_ed))
        rep.p("            decile  trades  predicted  actual win%   net R/trade   edge   net vs average")
        for dcl in range(10):
            ch = dec.get(dcl, [])
            if not ch:
                continue
            pr = sum(p for p, x in ch) / len(ch)
            wr = sum(1 for p, x in ch if x[5] > 0) / float(len(ch))
            nr = sum(x[5] for p, x in ch) / len(ch)
            ed = sum(x[5] - x[6] for p, x in ch) / len(ch)
            rep.p("           %6d  %6d     %5.1f%%      %5.1f%%       %+7.3f    %+7.3f    %+7.3f" %
                  (dcl + 1, len(ch), 100 * pr, 100 * wr, nr, ed, nr - mean_net))
        lo, hi = dec.get(0, []), dec.get(9, [])
        if lo:
            extra = -(sum(x[5] for p, x in lo) - len(lo) * mean_net)
            rep.p("           skipping the bottom decile saves %+.1f R MORE than skipping a random 10%% (%d trades;"
                  " positive = it really spots losers)" % (extra, len(lo)))
        if lo and hi:
            a = [x[5] - x[6] for p, x in hi]
            b = [x[5] - x[6] for p, x in lo]
            ma, mb = sum(a) / len(a), sum(b) / len(b)
            va = sum((v - ma) ** 2 for v in a) / max(1, len(a) - 1)
            vb = sum((v - mb) ** 2 for v in b) / max(1, len(b) - 1)
            t = (ma - mb) / math.sqrt(va / len(a) + vb / len(b)) if va + vb > 0 else 0.0
            rep.p("           top decile minus bottom decile, edge vs coin flip: %+.3f R  (t %.1f)" % (ma - mb, t))


def _j_profile(xs):
    """Asymmetry and capital profile of a list of rows."""
    r = [x[5] for x in xs]
    n = len(r)
    if n < 30:
        return None
    wins = [v for v in r if v > 0]
    loss = [v for v in r if v <= 0]
    srt = sorted(r, reverse=True)
    tot = sum(r)
    top = srt[:max(1, n // 10)]
    no5 = sum(srt[max(1, n // 20):]) / (n - max(1, n // 20))
    streak = best = 0
    for v in sorted(xs, key=lambda x: x[8].get("_t_in", 0)):
        streak = streak + 1 if v[5] <= 0 else 0
        best = max(best, streak)
    # growth-optimal risk per trade (Kelly on the R distribution), searched 0.0% .. 10%
    fbest, gbest = 0.0, 0.0
    for k in range(1, 201):
        f = k * 0.0005
        if min(r) * f <= -0.99:
            break
        g = sum(math.log(1 + f * v) for v in r) / n
        if g > gbest:
            fbest, gbest = f, g
    hold = [(x[8]["_t_out"] - x[8]["_t_in"]) / 3600.0 for x in xs if x[8].get("_t_out")]
    return {"n": n, "win": len(wins) / float(n), "avg_win": sum(wins) / len(wins) if wins else 0.0,
            "avg_loss": sum(loss) / len(loss) if loss else 0.0, "net": tot / n,
            "top10_share": sum(top) / n, "net_wo_top5": no5, "streak": best,
            "kelly": fbest, "hold_h": sorted(hold)[len(hold) // 2] if hold else None}


def _j_min_risk(xs, spec):
    """Share of trades whose SMALLEST possible position already risks more than 0.5% of a $10,000 account."""
    mu = spec.get("min_unit", A.HOUSE_MIN_UNIT)
    conv = A._quote_to_usd(spec)
    bad = tot = 0
    for x in xs:
        t = x[8]
        if t.get("risk_size") is None or t.get("_N") is None or t.get("_px") is None:
            continue
        sd = t["risk_size"] * t["_N"]
        usd = sd * mu * conv(t["_px"])
        tot += 1
        bad += 1 if usd > 50.0 else 0
    return (bad / float(tot)) if tot else None


def run_part_j(rep, rows, groups):
    rep.p("")
    rep.p("-" * 110)
    rep.p("J. PER-TRADE ODDS, ASYMMETRY / CAPITAL PROFILE, AND NEW CONTENDERS (2026-10-09)")
    rep.p("-" * 110)
    bk = {}
    for g, rs in groups.items():
        _w_form(rs)
        bk.update(_w_bucket(rs))
    rep.p("")
    rep.p("J1. CAN WE PREDICT A TRADE'S CHANCE TO WIN (OR TO LOSE)? A walk-forward logistic model per family, fed every")
    rep.p("    read the trade had when it was taken plus its lane, learning only from trades that had finished. If the reads")
    rep.p("    carry information, the top deciles win more often and the bottom deciles less. If the 'predicted' column moves")
    rep.p("    but 'actual' does not, the model is fooling itself. Bottom decile = the trades it calls most likely to LOSE.")
    rep.p("    YARDSTICK (same code on a fake random-walk market, 2026-10-09): predicted odds spread 11-55% while actual win%")
    rep.p("    stayed flat (26-33%); 'saves more than a random 10%' ranged -12 to +60 R; top-minus-bottom edge t ranged -2.5")
    rep.p("    to +0.4. So only believe it if actual win% climbs steadily with the deciles, in BOTH periods, with |t| above ~3.")
    for fam_name in ("go", "back"):
        _j_odds(rep, groups, bk, fam_name)
    # J2 asymmetry & capital
    rep.p("")
    rep.p("J2. ASYMMETRY AND CAPITAL PROFILE per lane (primary exit, all markets, all eras):")
    rep.p("    win%, average win / loss (R), net R per trade, top10 = R per trade that the best 10% of trades contribute, net R per")
    rep.p("    trade WITHOUT the best 5% (fragility), longest losing streak, KELLY = the risk per trade (%) that would have")
    rep.p("    grown the account fastest (0 = no size is good; half of it is the usual practical ceiling), median hold, and")
    rep.p("    MIN-SIZE = share of trades whose smallest possible position already risks more than 0.5% of $10,000.")
    specs = dict((x["name"], x) for x in A.COLLECT_SYMBOLS)
    rep.p("    %-9s %-9s %-6s %5s %5s %6s %6s %7s %6s %7s %5s %6s %7s" % ("lane", "variant", "exit", "n", "win%", "avgW",
          "avgL", "net", "top10", "w/o top5", "strk", "kelly", "hold h"))
    keys = sorted(groups)
    extra = defaultdict(list)
    for x in rows:
        if x[1] in H_WIDE and x[2] == H_WIDE[x[1]] and x[3] == "5d" and x[6] is not None and x[8].get("_t_in"):
            extra[(x[1], x[2], "5d")].append(x)
    allg = [(g, groups[g]) for g in keys] + sorted(extra.items())
    for g, rs in allg:
        pr = _j_profile(rs)
        if not pr:
            continue
        rep.p("    %-9s %-9s %-6s %5d %4.0f%% %+6.2f %+6.2f %+7.3f %6s %+7.3f %5d %5.2f%% %7s" %
              (g[0], g[1], g[2], pr["n"], 100 * pr["win"], pr["avg_win"], pr["avg_loss"], pr["net"],
               "%+.2f" % pr["top10_share"], pr["net_wo_top5"],
               pr["streak"], 100 * pr["kelly"], ("%.0f" % pr["hold_h"]) if pr["hold_h"] is not None else "-"))
    rep.p("")
    rep.p("    MIN-SIZE per market (H2 lanes and the new contenders; share of trades the smallest position cannot size")
    rep.p("    at 0.5% of $10,000 -- these need more capital or a bigger risk budget to be traded as designed):")
    for s in A.HOUSE_SYMBOLS:
        xs = [x for g, rs in allg if g[0] in H_WIDE or g[0] in ("inside", "turtle55", "dip3", "rsi2") for x in rs
              if x[0] == s]
        v = _j_min_risk(xs, specs[s]) if s in specs else None
        if v is not None:
            rep.p("      %-10s %4.0f%% of %d trades" % (s, 100 * v, len(xs)))
    # J3 new contenders
    rep.p("")
    rep.p("J3. NEW CONTENDERS (rules fixed before running). Short-term: inside-day breakout. Long-term: turtle 55/20,")
    rep.p("    dip3 (3 closes against the 200-day trend, then in with it). Plus rsi2 and dip3 per market.")
    con = {}
    for x in rows:
        if x[1] == "inside" and x[3] in ("5d", "close", "48h") and x[6] is not None:
            con.setdefault("inside day, %s exit" % x[3], []).append((x, 1.0))
            if _h_agree(x):
                con.setdefault("inside day, %s exit, detector agrees" % x[3], []).append((x, 1.0))
        if x[1] == "turtle55" and x[6] is not None:
            con.setdefault("turtle 55/20 (all)", []).append((x, 1.0))
            if x[8].get("with_50d") == 1:
                con.setdefault("turtle 55/20, with the 50-day trend", []).append((x, 1.0))
        if x[1] == "dip3" and x[6] is not None:
            con.setdefault("dip3 %s" % x[2], []).append((x, 1.0))
    for k in sorted(con):
        _h_report(rep, k, con[k])
    rep.p("")
    rep.p("    per market (net R old / new, trades):")
    for lane, var in (("rsi2", "long"), ("rsi2", "short"), ("dip3", "long"), ("dip3", "short"), ("turtle55", "55/20"),
                      ("inside", "mid")):
        line = "      %-9s %-6s" % (lane, var)
        for s in A.HOUSE_SYMBOLS:
            xs = [x for x in rows if x[0] == s and x[1] == lane and x[2] == var and x[6] is not None
                  and (x[3] == "own" or x[3] == "5d")]
            if xs:
                line += "  %s %+.0f/%+.0f (%d)" % (s[:6], sum(x[5] for x in xs if x[4] in POWER_OLD),
                                                    sum(x[5] for x in xs if x[4] == "B 2024+"), len(xs))
        rep.p(line)
    base = _i_month_r([(x, 1.0) for rs in extra.values() for x in rs if _h_agree(x)])
    rep.p("")
    rep.p("    monthly correlation with the H2 book (low / negative = earns at other times):")
    for k in sorted(con):
        mo = _i_month_r(con[k])
        ks = sorted(set(base) & set(mo))
        if len(ks) >= 12:
            rep.p("      %-50s corr %+.2f over %d months" % (k[:50], A._corr([base[q] for q in ks], [mo[q] for q in ks]) or 0.0,
                                                          len(ks)))


# ---- K. (2026-10-09) the OMEGA path: loss gates with a live shadow scorecard, every contender, theory sizing ----
# GATES = the loss signals found so far (fixed here, before this run). A gate is BROKEN when the trade sits in its bad
# bucket. Each gate carries a TRUST rating 0..1, learned live per sleeve from ALL trades it flagged -- taken or skipped
# (the skipped ones are followed in shadow) -- against the trades it did not flag, using finished trades only:
#   trust = clamp((-t - 0.5) / 1.5, 0, 1), t = (flagged net - unflagged net) / its standard error (decayed, half-life
#   K_HALF flagged trades); 0.5 until a gate has K_MIN_FLAGGED finished flagged trades in that sleeve.
# SCORE = sum of the trust of every broken gate. Size = 1 - skip chance, skip chance through (0,0) (1,.35) (2,.85) (3,1).
# Size scaling instead of random skips: same average result, no dice.
K_HALF = 150.0
K_MIN_FLAGGED = 40
K_SKIP = ((0.0, 0.0), (1.0, 0.35), (2.0, 0.85), (3.0, 1.0))
K_BRK_MARKETS = ("XAUUSD", "US500", "GERMANY40", "USDJPY")       # T8: trending flows (gold, indices, yen); not EURUSD/WTI
K_DIP_MARKETS = ("US500", "GERMANY40")                           # T7: dip-buying is an index effect
# sleeve -> (default risk % before 100 finished trades, floor, cap)   T17: big-winner breakouts ride 30-48 loss streaks,
# so they get a small cap; dip-buys win 65% with 4-7 loss streaks, so they may carry more.
K_RISK = {"brk": (0.25, 0.05, 0.50), "ins": (0.25, 0.05, 0.50), "dip": (0.50, 0.05, 1.00), "fast": (0.10, 0.05, 0.20)}
K_GATES = {"brk": ("far side", "against 50d", "hot form", "friday"),
           "ins": ("far side", "against 50d", "hot form", "friday"),
           "dip": ("hot form", "calm"),
           "fast": ("far side", "against 50d", "hot form", "friday")}
# fast (added 2026-10-09, before the freeze, rules fixed before running): the INTRADAY version of the breakouts, a
# small quick harvester and a second, faster read on the breakout mechanism -- orb30 (range) only when er10 agrees and
# main2 (box) only when edge20 agrees (run 3's two both-period positives), exit at the close, on the brk markets,
# 0.10% risk. It shares its entries with brk, so it adds trades, not diversity.
K_SLEEVES = ("brk", "ins", "dip", "fast")
K_OPEN_CAP = 6.0                       # % of equity at risk at once, all sleeves
K_SUMMARY = []                         # machine-readable results of the omega run -> omega_summary.csv (synth batch)


def _ks(metric, sleeve, era, value, extra=""):
    K_SUMMARY.append({"metric": metric, "sleeve": sleeve, "era": era,
                      "value": "" if value is None else round(value, 5), "extra": extra})


def _k_skip(score):
    for (a, pa), (b, pb) in zip(K_SKIP, K_SKIP[1:]):
        if score <= b:
            return pa + (pb - pa) * (score - a) / (b - a)
    return 1.0


def _k_flags(x, b, sleeve):
    t = x[8]
    f = []
    for g in K_GATES[sleeve]:
        if g == "far side" and b.get("pos20_with") == "low":
            f.append(g)
        elif g == "against 50d" and t.get("with_50d") == 0:
            f.append(g)
        elif g == "hot form" and t.get("form") == "hot":
            f.append(g)
        elif g == "friday" and t.get("weekday") == 4:
            f.append(g)
        elif g == "calm" and b.get("vol") == "low":
            f.append(g)
    return f


def _k_sleeves(rows, all_markets=False):
    """-> {sleeve: [rows]}; tags 'form' and thirds are computed per lane group."""
    sl = defaultdict(list)
    for x in rows:
        if x[6] is None or not x[8].get("_t_in") or not x[8].get("_t_out"):
            continue
        if x[1] in H_WIDE and x[2] == H_WIDE[x[1]] and x[3] == "5d" and _h_agree(x):
            if all_markets or x[0] in K_BRK_MARKETS:
                sl["brk"].append(x)
        elif x[1] == "inside" and x[3] == "close":
            if all_markets or x[0] in K_BRK_MARKETS:
                sl["ins"].append(x)
        elif x[1] in ("rsi2", "dip3") and x[2] == "long" and x[3] == "own":
            if all_markets or x[0] in K_DIP_MARKETS:
                sl["dip"].append(x)
        elif x[3] == "close" and ((x[1] == "orb30" and x[2] == "range" and _h_agree(x, ("er10",))) or
                                  (x[1] == "main2" and x[2] == "box" and _h_agree(x, ("edge20",)))):
            if all_markets or x[0] in K_BRK_MARKETS:
                sl["fast"].append(x)
    return sl


def _k_prepare(sl, rand_seed=None):
    """flags per row id. rand_seed: replace every gate by a random flag with the SAME frequency (the control)."""
    flags = {}
    for s, xs in sl.items():
        by = defaultdict(list)
        for x in xs:
            by[(x[1], x[2])].append(x)
        for _, g in by.items():
            _w_form(g)
            bk = _w_bucket(g)
            for x in g:
                flags[id(x)] = _k_flags(x, bk.get(id(x), {}), s)
    if rand_seed is not None:
        import random
        rnd = random.Random(rand_seed)
        for s, xs in sl.items():
            freq = defaultdict(int)
            for x in xs:
                for g in flags[id(x)]:
                    freq[g] += 1
            for x in xs:
                flags[id(x)] = [g for g in K_GATES[s] if rnd.random() < freq[g] / float(max(1, len(xs)))]
    return flags


def _k_kelly(r):
    fb, gb = 0.0, 0.0
    lo = min(r)
    for k in range(1, 201):
        f = k * 0.0005
        if lo * f <= -0.99:
            break
        g = sum(math.log(1 + f * v) for v in r) / len(r)
        if g > gb:
            fb, gb = f, g
    return fb


def _k_walk(sl, flags, mode="shadow"):
    """mode: 'shadow' (live trust), 'fixed' (every gate fully trusted), 'off' (no gates).
    -> book [(x, size, sleeve, risk_pct)], trace {(sleeve, gate): [(era, trust, flagged?, net)]}"""
    import heapq
    # ties (two trades opening at the same moment) broken by market / lane / variant / exit -- NOT by memory
    # address, which changed between runs and made the one-position rule pick differently (found 2026-10-09)
    ev = sorted(((x[8]["_t_in"], (x[0], x[1], x[2], x[3], x[8].get("_d") or 0), s, x) for s, xs in sl.items()
                 for x in xs), key=lambda e: (e[0], e[1]))
    k = 0.5 ** (1.0 / K_HALF)
    st = defaultdict(lambda: [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0])   # (s,g) -> f sum, f sum2, f n, u sum, u sum2, u n, raw f n
    pend, done_r = [], defaultdict(list)
    busy = {}
    book, trace = [], defaultdict(list)
    gsize = {}
    kcache = {}
    seq = 0

    def trust(s, g):
        v = st[(s, g)]
        if v[6] < K_MIN_FLAGGED or v[2] < 5 or v[5] < 5:
            return 0.5
        mf, mu = v[0] / v[2], v[3] / v[5]
        vf = max(v[1] / v[2] - mf * mf, 1e-9)
        vu = max(v[4] / v[5] - mu * mu, 1e-9)
        t = (mf - mu) / math.sqrt(vf / v[2] + vu / v[5])
        return min(max((-t - 0.5) / 1.5, 0.0), 1.0)

    for t_in, _, s, x in ev:
        while pend and pend[0][0] <= t_in:
            _, _, ps, pfl, pr, taken = heapq.heappop(pend)
            for g in K_GATES[ps]:
                v = st[(ps, g)]
                if g in pfl:
                    v[0], v[1], v[2] = v[0] * k + pr, v[1] * k + pr * pr, v[2] * k + 1.0
                    v[6] += 1
                else:
                    v[3], v[4], v[5] = v[3] * k + pr, v[4] * k + pr * pr, v[5] * k + 1.0
            if taken:
                done_r[ps].append(pr)
        fl = flags.get(id(x), [])
        tr = dict((g, trust(s, g)) for g in K_GATES[s])
        for g in K_GATES[s]:
            trace[(s, g)].append((x[4], tr[g], g in fl, x[5]))
        if mode == "off":
            size = 1.0
        elif mode == "fixed":
            size = 1.0 - _k_skip(float(len(fl)))
        else:
            size = 1.0 - _k_skip(sum(tr[g] for g in fl))
        gsize[id(x)] = size
        key = (s, x[0], x[8].get("_d"))
        if size > 0.001 and busy.get(key, 0) > t_in:
            size = 0.0                                   # one position per sleeve, market and direction
        dflt, lo, hi = K_RISK[s]
        nh = len(done_r[s])
        if nh < 100:
            risk = dflt
        else:
            ck = kcache.get(s)
            if ck is None or nh - ck[0] >= 10:          # re-fit every 10 finished trades (speed)
                ck = (nh, min(max(0.25 * 100.0 * _k_kelly(done_r[s][-300:]), lo), hi))
                kcache[s] = ck
            risk = ck[1]
        if size > 0.001:
            busy[key] = x[8]["_t_out"]
            book.append((x, size, s, risk))
        seq += 1
        heapq.heappush(pend, (x[8]["_t_out"], seq, s, fl, x[5], size > 0.001))
    trace["_gsize"] = gsize
    return book, trace


def _k_money(rep, name, book, start_eq):
    """Compounding money run per era from start_eq: each trade risks its sleeve's risk% x gate size of CURRENT equity;
    a trade is skipped if the smallest position would risk more than 1.5x that, or open risk would pass K_OPEN_CAP%."""
    import heapq
    specs = dict((q["name"], q) for q in A.COLLECT_SYMBOLS)
    line = "  %-34s $%-7s" % (name[:34], "{:,}".format(int(start_eq)))
    for era in POWER_ERAS:
        xs = sorted([e for e in book if e[0][4] == era], key=lambda e: e[0][8]["_t_in"])
        if not xs:
            continue
        eq, openq, open_risk = start_eq, [], 0.0
        mon = defaultdict(float)
        small = capped = qn = 0
        for x, z, s, rk in xs:
            t = x[8]["_t_in"]
            while openq and openq[0][0] <= t:
                to, _, amt, r = heapq.heappop(openq)
                open_risk -= amt
                eq += amt * r
                mon[time.strftime("%Y-%m", time.gmtime(to))] += amt * r
            amt = eq * rk / 100.0 * z
            sp = specs.get(x[0])
            tg = x[8]
            if sp and tg.get("risk_size") is not None and tg.get("_N") and tg.get("_px"):
                mn = tg["risk_size"] * tg["_N"] * sp.get("min_unit", A.HOUSE_MIN_UNIT) * A._quote_to_usd(sp)(tg["_px"])
                if mn > 1.5 * amt:
                    small += 1
                    continue
            if open_risk + amt > eq * K_OPEN_CAP / 100.0:
                capped += 1
                continue
            open_risk += amt
            qn += 1
            heapq.heappush(openq, (x[8]["_t_out"], qn, amt, x[5]))
        while openq:
            to, _, amt, r = heapq.heappop(openq)
            eq += amt * r
            mon[time.strftime("%Y-%m", time.gmtime(to))] += amt * r
        e2, peak, dd, under, longest, rets = start_eq, start_eq, 0.0, 0, 0, []
        for kk in sorted(mon):
            rets.append(mon[kk] / e2)
            e2 += mon[kk]
            if e2 >= peak:
                peak, under = e2, 0
            else:
                under += 1
                longest = max(longest, under)
            dd = max(dd, (peak - e2) / peak)
        cagr = (e2 / start_eq) ** (1.0 / H_YRS[era]) - 1.0 if e2 > 0 else -1.0
        line += "  |%s %+5.1f%%/yr dd %4.1f%% under %2dmo m+ %2.0f%% small %d cap %d" % (
            era[-5:], 100 * cagr, 100 * dd, longest, 100.0 * sum(1 for r in rets if r > 0) / max(1, len(rets)), small,
            capped)
        _ks("money_cagr", name, era, 100 * cagr, "%d" % int(start_eq))
        _ks("money_dd", name, era, 100 * dd, "%d" % int(start_eq))
    rep.p(line)


def run_part_k(rep, rows):
    rep.p("")
    rep.p("-" * 110)
    rep.p("K. THE OMEGA PATH: every contender, loss gates with a live shadow scorecard, sizing by each sleeve's theory")
    rep.p("-" * 110)
    for line in (
            "SLEEVES  brk = H2 breakouts (wide stop, 5-day chandelier, edge20/er10 agrees) on gold, US500, Germany 40, USDJPY",
            "         dip = rsi2 long + dip3 long on US500 and Germany 40 (index dip-buys)",
            "         ins = inside-day breakout, exit at the close, on the brk markets",
            "         fast = INTRADAY breakouts: orb30 when er10 agrees + main2 when edge20 agrees, exit at the close,",
            "                brk markets, 0.10% risk (a small quick harvester; same entries as brk, so not diversity)",
            "         (market lists come from T7/T8 -- chosen after seeing these years; the all-markets row is the check)",
            "GATES    far side = price in the bottom third of its 20-day range for the trade's direction   (brk, ins)",
            "         against 50d = trade against the 50-day average                                       (brk, ins)",
            "         hot form = the lane's last 20 finished trades beat the coin flip                     (all)",
            "         friday (no theory; main2 only)                                                       (brk, ins)",
            "         calm = volatility in its bottom third (fades need movement)                          (dip)",
            "TRUST    each gate's flagged trades (taken or skipped -- skipped ones followed in shadow) vs its unflagged",
            "         ones, live, finished trades only, per sleeve. 0 = the gate is useless right now, 1 = fully trusted.",
            "SIZE     1 - skip chance(sum of trust of broken gates): 1 gate fully trusted = 0.65x, 2 = 0.15x, 3+ = skip.",
            "         No upsizing on 'good' signals: a trade with every gate open is taken at its intended 1x.",
            "RISK     per sleeve: quarter Kelly of its last 300 finished trades, brk/ins 0.05-0.50%, dip 0.05-1.00%",
            "         (0.25 / 0.25 / 0.50% before 100 trades). One position per sleeve, market and direction. Open risk",
            "         at most 6% of equity. HONEST LIMIT: the gates themselves were found on these same years, so this is",
            "         in-sample; the shadow trust only guards against a gate going dead. Japan 225 / 2022-23 decide."):
        rep.p(line)
    rep.p("YARDSTICK (same code, fake random-walk market, 2026-10-09): gates ON vs OFF moved net R by -6..+6 R a year per era;")
    rep.p("    'R kept out' ranged -38..+142 R per era (so one big era is NOT proof); trust drifted to 0 for most gates;")
    rep.p("    Kelly put every sleeve on its 0.05% floor. Real gates must beat their RANDOM copy in most eras.")
    sl = _k_sleeves(rows)
    for s in K_SLEEVES:
        rep.p("  sleeve %s: %d candidate trades" % (s, len(sl.get(s, []))))
    flags = _k_prepare(sl)
    book, trace = _k_walk(sl, flags, "shadow")
    # K1 scorecard
    rep.p("")
    rep.p("K1. GATE SCORECARD per sleeve and era: flagged = trades the gate flagged (taken or skipped); net/trade flagged vs")
    rep.p("    not flagged; trust = the gate's average live trust when it fired. Then: R KEPT OUT = net R of the size the gates")
    rep.p("    cut, sign flipped (positive = the cut shadow trades lost money: the gates helped; before the one-position rule)")
    sz = trace.pop("_gsize")
    for s in K_SLEEVES:
        for g in K_GATES[s]:
            tr = trace.get((s, g), [])
            if not tr:
                continue
            line = "    %-4s %-12s" % (s, g)
            for era in POWER_ERAS:
                e = [v for v in tr if v[0] == era]
                f = [v for v in e if v[2]]
                u = [v for v in e if not v[2]]
                if len(f) < 10 or len(u) < 10:
                    line += " | %-7s  -" % era[-5:]
                    continue
                line += " | %s n%4d %+.3f vs %+.3f trust %.2f" % (
                    era[-5:], len(f), sum(v[3] for v in f) / len(f), sum(v[3] for v in u) / len(u),
                    sum(v[1] for v in f) / len(f))
            rep.p(line)
    for s in K_SLEEVES:
        xs = sl.get(s, [])
        line = "    %-4s R kept out by all gates together:" % s
        for era in POWER_ERAS:
            cut = sum(x[5] * (1.0 - sz.get(id(x), 1.0)) for x in xs if x[4] == era)
            line += "  %s %+7.1f R" % (era[-5:], -cut)
        rep.p(line)
    # K2 per sleeve, gated vs not
    rep.p("")
    rep.p("K2. EACH SLEEVE, gates off vs on (net R per 1R risked, sizes counted; deduped)")
    off, tr_off = _k_walk(sl, flags, "off")
    for s in K_SLEEVES:
        _h_report(rep, "%s, gates OFF" % s, [(x, z) for x, z, q, rk in off if q == s])
        _h_report(rep, "%s, gates ON (shadow trust)" % s, [(x, z) for x, z, q, rk in book if q == s])
    # K3 the omega book and its checks
    rep.p("")
    rep.p("K3. THE OMEGA BOOK in R (all sleeves, each trade at its gate size) and its checks")
    fixed, _ = _k_walk(sl, flags, "fixed")
    rflags = _k_prepare(sl, rand_seed=7)
    rnd, _ = _k_walk(sl, rflags, "shadow")
    sla = _k_sleeves(rows, all_markets=True)
    fla = _k_prepare(sla)
    alm, _ = _k_walk(sla, fla, "shadow")
    for nm, bk_ in (("OMEGA (shadow-trusted gates)", book), ("check: gates OFF", off),
                    ("check: gates always fully trusted (no scorecard)", fixed),
                    ("check: RANDOM gates, same flag rates, shadow trust (must NOT help)", rnd),
                    ("check: all six markets in every sleeve", alm)):
        _h_report(rep, nm, [(x, z) for x, z, q, rk in bk_])
    # K4 money
    rep.p("")
    rep.p("K4. MONEY (compounding, each era starts fresh; risk = sleeve risk% x gate size; small = trades the smallest")
    rep.p("    position could not take without risking 1.5x+ the intended amount; cap = trades skipped because open risk")
    rep.p("    would have passed 6% of equity)")
    for eq0 in (10000.0, 100000.0):
        _k_money(rep, "OMEGA", book, eq0)
        _k_money(rep, "check: gates OFF", off, eq0)
        _k_money(rep, "check: all six markets", alm, eq0)
    rep.p("")
    rep.p("    risk % per trade the sizing chose (average over taken trades, per era):")
    for s in K_SLEEVES:
        line = "      %-4s" % s
        for era in POWER_ERAS:
            e = [rk for x, z, q, rk in book if q == s and x[4] == era]
            if e:
                line += "  %s %.2f%%" % (era[-5:], sum(e) / len(e))
        rep.p(line)
    rep.p("")
    rep.p("    monthly correlation between sleeves (OMEGA, R):")
    mo = dict((s, _i_month_r([(x, z) for x, z, q, rk in book if q == s])) for s in K_SLEEVES)
    for a, b in (("brk", "ins"), ("brk", "dip"), ("ins", "dip"), ("fast", "brk"), ("fast", "ins"), ("fast", "dip")):
        ks = sorted(set(mo[a]) & set(mo[b]))
        if len(ks) >= 12:
            rep.p("      %s vs %s  corr %+.2f over %d months" % (a, b, A._corr([mo[a][q] for q in ks],
                                                                         [mo[b][q] for q in ks]) or 0.0, len(ks)))
    # the FROZEN design (2026-10-09) has no gates: sizing (K5) and canaries (K6) run on the gates-OFF book
    rep.p("")
    rep.p("    (K5 and K6 below use the FROZEN design's book: gates OFF, one position per sleeve / market / direction)")
    for s_ in K_SLEEVES + ("ALL",):
        for era in POWER_ERAS:
            xs = [(x, z) for x, z, q, rk in off if (q == s_ or s_ == "ALL") and x[4] == era]
            if not xs:
                continue
            rk_ = sum(z for x, z in xs)
            _ks("net_r", s_, era, sum(x[5] * z for x, z in xs) / rk_, "%d" % len(xs))
            _ks("edge_r", s_, era, sum((x[5] - x[6]) * z for x, z in xs) / rk_, "%d" % len(xs))
            _ks("r_per_yr", s_, era, sum(x[5] * z for x, z in xs) / H_YRS[era], "%d" % len(xs))
    _k_sizing(rep, off)
    run_canaries(rep, off)
    try:
        A._write_csv(os.path.join(rep.dir, "omega_summary.csv"), K_SUMMARY,
                     first=("metric", "sleeve", "era", "value", "extra"))
        rep.p("")
        rep.p("machine-readable results: omega_summary.csv")
    except Exception as e:
        rep.p("(omega_summary.csv not written: %s)" % e)


# ---- K5. (2026-10-09) sizing by state, at the SAME average risk ----
# Ezio's idea (reading 2, 'protect what was banked'): a NORMAL state with a higher base size and a DEFENSIVE state with
# a smaller one after a winning streak; the first loss puts the sleeve back to normal. Not a skip -- a size state. It
# mirrors 'cold does better' (T5). Every rule is rescaled per sleeve so its AVERAGE risk per trade equals the fixed
# rule's (the rescale uses the whole sample: it sets the level only, never the timing). So any difference comes from
# WHEN size is high or low, not from how much is risked on average.
K5_BASE = {"brk": 0.25, "ins": 0.25, "dip": 0.50, "fast": 0.10}
K5_NORMAL, K5_DEF = 1.25, 0.50


def _k5_states(book, rule):
    """Multiplier per entry (same order as book) from finished trades only, per sleeve."""
    import heapq
    order = sorted(range(len(book)), key=lambda i: book[i][0][8]["_t_in"])
    pend, out = [], [1.0] * len(book)
    streak, defensive, hist = defaultdict(int), defaultdict(bool), defaultdict(list)
    seq = 0
    for i in order:
        x, z, s, rk = book[i]
        t = x[8]["_t_in"]
        while pend and pend[0][0] <= t:
            _, _, ps, r = heapq.heappop(pend)
            hist[ps].append(r)
            if r > 0:
                streak[ps] += 1
            else:
                streak[ps] = 0
                defensive[ps] = False
            if rule.startswith("streak") and streak[ps] >= int(rule[6:]):
                defensive[ps] = True
        if rule == "form20":
            h = hist[s][-20:]
            defensive[s] = len(h) >= 20 and sum(h) > 0
        if rule in ("fixed",):
            out[i] = 1.0
        elif rule == "kelly":
            out[i] = rk
        else:
            out[i] = K5_DEF if defensive[s] else K5_NORMAL
        seq += 1
        heapq.heappush(pend, (x[8]["_t_out"], seq, s, x[5]))
    # rescale per sleeve to an average multiplier of 1 (same average risk as fixed)
    by = defaultdict(list)
    for i, e in enumerate(book):
        by[e[2]].append(i)
    for s, idx in by.items():
        mu = sum(out[i] for i in idx) / len(idx)
        for i in idx:
            out[i] = out[i] / mu if mu > 0 else 1.0
    return out


def _k_sizing(rep, book):
    rep.p("")
    rep.p("K5. SIZING BY STATE, every rule at the SAME average risk per sleeve (brk 0.25%, ins 0.25%, dip 0.50%, fast 0.10%):")
    rep.p("    fixed    = always the base")
    rep.p("    kelly    = quarter Kelly of the last 300 finished trades (K4's rule), rescaled to the same average")
    rep.p("    streak2  = NORMAL %.2fx, DEFENSIVE %.2fx after 2 wins in a row (finished trades of that sleeve); the first" %
          (K5_NORMAL, K5_DEF))
    rep.p("               loss returns to normal. streak3 = the same after 3 wins.  (before rescaling)")
    rep.p("    form20   = DEFENSIVE while the sleeve's last 20 finished trades sum above 0 (T5's 'hot' read)")
    rep.p("    YARDSTICK (same code, fake random-walk market, 2026-10-09): the rules' weighted R/yr differed from 'fixed' by")
    rep.p("    -15..+8 R/yr per era and their money by -4..+2 %/yr from noise alone; defensive-vs-normal R gaps up to 2R")
    rep.p("    showed up on 6-25 trades. A rule is better only if it beats 'fixed' in most eras by more than that.")
    rules = ("fixed", "kelly", "streak2", "streak3", "form20")
    mults = dict((r, _k5_states(book, r)) for r in rules)
    # does the state carry information? mean R of trades taken in each state
    rep.p("")
    rep.p("    Does the state predict the next trade?  net R/trade taken in DEFENSIVE vs NORMAL state (n), per era:")
    for r in ("streak2", "streak3", "form20"):
        for s in K_SLEEVES:
            line = "      %-8s %-4s" % (r, s)
            for era in POWER_ERAS:
                d = [book[i][0][5] for i in range(len(book)) if book[i][2] == s and book[i][0][4] == era
                     and mults[r][i] < 1.0]
                n = [book[i][0][5] for i in range(len(book)) if book[i][2] == s and book[i][0][4] == era
                     and mults[r][i] >= 1.0]
                if len(d) >= 5 and len(n) >= 5:
                    line += "  %s def %+.2f (%d) norm %+.2f (%d)" % (era[-5:], sum(d) / len(d), len(d),
                                                                     sum(n) / len(n), len(n))
                    _ks("state_gap_" + r, s, era, sum(d) / len(d) - sum(n) / len(n), "%d/%d" % (len(d), len(n)))
                else:
                    line += "  %s  -" % era[-5:]
            rep.p(line)
    rep.p("")
    rep.p("    R per year with each trade weighted by its size multiplier (timing value, no compounding):")
    for r in rules:
        line = "      %-8s" % r
        for era in POWER_ERAS:
            v = sum(book[i][0][5] * book[i][1] * mults[r][i] for i in range(len(book)) if book[i][0][4] == era)
            line += "  %s %+7.1f R/yr" % (era[-5:], v / H_YRS[era])
            _ks("sized_r_per_yr_" + r, "ALL", era, v / H_YRS[era])
        rep.p(line)
    rep.p("")
    rep.p("    Money with each rule (same engine as K4):")
    for eq0 in (10000.0, 100000.0):
        for r in rules:
            b2 = [(x, z, s, K5_BASE[s] * mults[r][i]) for i, (x, z, s, rk) in enumerate(book)]
            _k_money(rep, "sizing: %s" % r, b2, eq0)



# ---- K6. (2026-10-09) CANARIES: watch each earner's MECHANISM weekly, on every event, traded or not ----
# Fixed before running. A slow earner's own P&L needs ~1,500 trades to tell 'working' from 'dead'. A canary pools every
# event of the mechanism on every market (no costs, no exits), so it reads faster:
#   breakout  every daily close beyond the previous 20-day high / low, all six markets; value = move over the next 5
#             days in the break's direction, in daily ATRs. Window: the last 4 weeks of events.  -> brk, ins, fast
#   dip       every 3rd down close in a row while above the 200-day average, US500 and Germany 40; value = move over
#             the next 3 days, in daily ATRs. Window: the last 8 weeks (fewer events).               -> dip
#   spread    per market: the day's average spread in bp of price; window 4 weeks; the BAD side is HIGH.  -> that market
# A canary's NORMAL BAND is the 10th-90th percentile of its weekly window values in 2014-21. ALARM: 3 weeks in a row on
# the bad side of the band; it ends the first week back inside. RULE (fixed): during an alarm the linked earner (or
# market, for spread) trades at HALF size. A window value uses only events whose outcome was already known that week.
P_CANARY = defaultdict(list)          # (kind, market) -> [(t_known, value)]
C_LINK = {"breakout": ("brk", "ins", "fast"), "dip": ("dip",)}
C_WIN = {"breakout": 4, "dip": 8, "spread": 4}
C_WEEK = 7 * 86400


def p_canary_events(m):
    D, cl, N = m.D, m.cl, m.N
    nd = len(D)
    for j in range(1, nd - 5):
        if N[j] is None or m.seg[j + 5] != m.seg[j]:
            continue
        t_known = m.T[D[j + 5][2]]
        h20, l20 = m.hh(j, 20), m.ll(j, 20)
        if h20 is not None and l20 is not None:
            d = 1 if cl[j] > h20 else (-1 if cl[j] < l20 else 0)
            if d:
                P_CANARY[("breakout", m.s)].append((t_known, d * (cl[j + 5] - cl[j]) / N[j]))
        if m.s in K_DIP_MARKETS and j >= 3 and m.seg[j - 3] == m.seg[j]:
            s200 = m.sma(j, 200)
            if s200 is not None and cl[j] > s200 and cl[j] < cl[j - 1] < cl[j - 2] < cl[j - 3]:
                P_CANARY[("dip", m.s)].append((m.T[D[j + 3][2]], (cl[j + 3] - cl[j]) / N[j]))
    if m.S:
        for j in range(nd):
            i0, i1 = D[j][1], D[j][2]
            v = [m.S[i] / m.C[i] * 1e4 for i in range(i0, i1 + 1) if m.S[i] is not None and m.C[i] > 0]
            if v:
                P_CANARY[("spread", m.s)].append((m.T[i1], sum(v) / len(v)))


def _c_weekly(evs, win):
    """{week: (window mean, n events)} using events known by the END of that week."""
    by = defaultdict(list)
    for t, v in evs:
        by[int(t // C_WEEK)].append(v)
    if not by:
        return {}
    out = {}
    w0, w1 = min(by), max(by)
    for w in range(w0 + win - 1, w1 + 1):
        vs = [v for k in range(w - win + 1, w + 1) for v in by.get(k, [])]
        if len(vs) >= 3:
            out[w] = (sum(vs) / len(vs), len(vs))
    return out


def _c_era_of_week(w):
    return _p_era(w * C_WEEK + 3 * 86400)


def _c_alarms(series, bad_high=False):
    """series {week: (value, n)} -> (band lo, band hi, set of ALARM weeks (state at the START of the next week))."""
    base = sorted(v for w, (v, n) in series.items() if _c_era_of_week(w) in POWER_OLD)
    if len(base) < 30:
        return None, None, set()
    lo, hi = base[len(base) // 10], base[9 * len(base) // 10]
    alarm, run, on = set(), 0, False
    for w in sorted(series):
        v = series[w][0]
        bad = v > hi if bad_high else v < lo
        run = run + 1 if bad else 0
        if run >= 3:
            on = True
        elif not bad:
            on = False
        if on:
            alarm.add(w + 1)              # acts on the trades of the FOLLOWING week
    return lo, hi, alarm


def run_canaries(rep, book):
    rep.p("")
    rep.p("K6. CANARIES (fixed before running): each earner's mechanism read weekly on EVERY event, traded or not.")
    rep.p("    breakout = next-5-day move after any daily close beyond the 20-day high/low (all markets, last 4 weeks);")
    rep.p("    dip = next-3-day move after the 3rd down close in a row above the 200-day average (US500, Germany 40, last 8")
    rep.p("    weeks); spread = daily average spread in bp (per market, last 4 weeks). Band = 10th-90th percentile of 2014-21")
    rep.p("    (so 2014-21 is in-sample for the band, 2024+ is not). ALARM = 3 weeks in a row on the bad side; RULE = the")
    rep.p("    linked earner (or market) trades at HALF size during an alarm.")
    rep.p("    YARDSTICK (same code, fake random-walk market, 2026-10-09): alarm-vs-normal gaps of up to 1R per trade on")
    rep.p("    15-50 trades, in both directions; the un-rescaled rule 'gained' 0.3-1.7 %/yr only because it risked less on a")
    rep.p("    losing book. Judge the rule on the SAME-AVERAGE-RISK line, and on alarm trades being worse in most eras.")
    alarms = {}
    for kind in ("breakout", "dip"):
        evs = [e for (k, s), v in P_CANARY.items() if k == kind for e in v]
        ser = _c_weekly(evs, C_WIN[kind])
        lo, hi, al = _c_alarms(ser)
        alarms[kind] = al
        if lo is None:
            rep.p("    %-9s too few weeks for a band" % kind)
            continue
        line = "    %-9s band %+.3f .. %+.3f ATR  events %d  | weeks in ALARM:" % (kind, lo, hi, len(evs))
        for era in POWER_ERAS:
            ws = [w for w in ser if _c_era_of_week(w) == era]
            if ws:
                line += "  %s %4.1f%%" % (era[-5:], 100.0 * sum(1 for w in ws if w + 1 in al) / len(ws))
        rep.p(line)
    sp_alarm = {}
    for (k, s), v in sorted(P_CANARY.items()):
        if k != "spread":
            continue
        ser = _c_weekly(v, C_WIN["spread"])
        lo, hi, al = _c_alarms(ser, bad_high=True)
        sp_alarm[s] = al
        if lo is None:
            continue
        line = "    spread %-10s band %.2f .. %.2f bp | weeks in ALARM:" % (s, lo, hi)
        for era in POWER_ERAS:
            ws = [w for w in ser if _c_era_of_week(w) == era]
            if ws:
                line += "  %s %4.1f%%" % (era[-5:], 100.0 * sum(1 for w in ws if w + 1 in al) / len(ws))
        rep.p(line)
    # does an alarm warn? trades of the linked earner entered during alarm vs normal weeks
    rep.p("")
    rep.p("    Does an ALARM warn?  net R/trade of the linked earner's trades entered during ALARM vs NORMAL weeks (n):")

    def in_alarm(x, s):
        w = int(x[8]["_t_in"] // C_WEEK)
        a = any(w in alarms.get(k, ()) for k, sls in C_LINK.items() if s in sls)
        return a or (w in sp_alarm.get(x[0], ()))
    for s in K_SLEEVES:
        line = "      %-4s" % s
        for era in POWER_ERAS:
            a = [x[5] for x, z, q, rk in book if q == s and x[4] == era and in_alarm(x, s)]
            n = [x[5] for x, z, q, rk in book if q == s and x[4] == era and not in_alarm(x, s)]
            if len(a) >= 5 and len(n) >= 5:
                line += "  %s alarm %+.2f (%d) normal %+.2f (%d)" % (era[-5:], sum(a) / len(a), len(a),
                                                                    sum(n) / len(n), len(n))
                _ks("canary_gap", s, era, sum(a) / len(a) - sum(n) / len(n), "%d/%d" % (len(a), len(n)))
            else:
                line += "  %s alarm - (%d)" % (era[-5:], len(a))
        rep.p(line)
    rep.p("")
    rep.p("    Money: fixed risk vs fixed risk + the canary rule (half size in alarm; NOT rescaled, so it also risks less):")
    fixed = [(x, z, s, K5_BASE[s]) for x, z, s, rk in book]
    canary = [(x, z, s, K5_BASE[s] * (0.5 if in_alarm(x, s) else 1.0)) for x, z, s, rk in book]
    mean = defaultdict(list)
    for x, z, s, rk in canary:
        mean[s].append(rk / K5_BASE[s])
    mu = dict((s, sum(v) / len(v)) for s, v in mean.items())
    fair = [(x, z, s, rk / mu[s]) for x, z, s, rk in canary]
    for eq0 in (10000.0, 100000.0):
        _k_money(rep, "fixed", fixed, eq0)
        _k_money(rep, "fixed + canary rule", canary, eq0)
        _k_money(rep, "canary rule, same avg risk", fair, eq0)
    share = sum(1 for x, z, s, rk in book if in_alarm(x, s)) / float(max(1, len(book)))
    rep.p("    (%.0f%% of all trades fell in an alarm week)" % (100 * share))


def write_launcher():
    try:
        me = os.path.abspath(__file__)
        here = os.path.dirname(me)
        if os.name == "nt":
            path = os.path.join(here, "run_asiabo_lab.bat")
            body = '@echo off\r\ncd /d "%%~dp0"\r\n"%s" "%s" %%*\r\necho.\r\npause\r\n' % (sys.executable, me)
        else:
            path = os.path.join(here, "run_asiabo_lab.sh")
            body = '#!/bin/sh\ncd "$(dirname "$0")"\n"%s" "%s" "$@"\n' % (sys.executable, me)
        old = None
        if os.path.exists(path):
            with open(path, "r", newline="") as f:
                old = f.read()
        if old != body:
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
    synth = None
    if "--db" in sys.argv:                 # run on a synthetic cousin of bars.db (make_synth.py); bars.db untouched
        k = sys.argv.index("--db")
        synth = os.path.abspath(sys.argv[k + 1])
        del sys.argv[k:k + 2]
        if not os.path.exists(synth):
            print("no such file: %s" % synth)
            return
        A.find_db = lambda: synth
    mode = sys.argv[1].lower() if len(sys.argv) > 1 else "all"
    if mode not in ("all", "labels", "daily", "machine", "persist", "signals", "theory", "probe", "final", "power", "omega"):
        print("usage: python asiabo_lab.py [all|labels|daily|machine|persist|signals|theory|probe|final|power|omega]"
              "  [--db synth/<file>.db]")
        return
    t0 = time.time()
    if os.environ.get("ASIABO_NO_VISION"):          # a parallel batch job: leave 'claude vision' alone
        A.publish_to_vision = lambda d: print("(claude vision left alone: batch job)")
    meta = {}
    if synth:
        try:
            con = sqlite3.connect(synth)
            meta = dict(con.execute("select key, value from synth_meta"))
            con.close()
        except Exception:
            meta = {}
    tag = os.environ.get("ASIABO_REPORT_TAG", "")      # unique report folder per batch job
    rep = A.Report(("synth_lab" if synth else "lab") + (("_" + tag) if tag else ""))
    if synth:
        rep.p("#" * 100)
        rep.p("SYNTHETIC DATA (a cousin of bars.db, NOT the real market): %s" % synth)
        rep.p("settings: " + ", ".join("%s=%s" % kv for kv in sorted(meta.items()) if kv[0] != "source"))
        rep.p("Parts that read real collect / house trades are skipped.")
        rep.p("#" * 100)
    rep.p("=" * 100)
    rep.p("THE LAB  --  every open idea, labelled, in one run. Shadow only: it measures, it decides nothing.")
    rep.p("=" * 100)
    rep.p("Sealed exam years %s .. %s: not read by any part." % (A.SEAL_START, A.SEAL_END))
    folder = None
    if not synth and mode in ("all", "labels", "machine", "persist", "signals", "theory", "probe", "final", "power"):
        try:
            folder = A._house_folder()
        except RuntimeError as e:
            rep.p("PARTS 1 and 3 skipped (power: exit test skipped): %s" % e)
    for part, fn in (("labels", lambda: run_labels(rep, folder)), ("daily", lambda: run_daily(rep)), ("machine", lambda: run_machine(rep, folder)),
                     ("persist", lambda: run_persist(rep, folder)), ("signals", lambda: run_signals(rep, folder)),
                     ("theory", lambda: run_theory(rep, folder)), ("probe", lambda: run_probe(rep, folder)),
                     ("final", lambda: run_final(rep, folder)), ("power", lambda: run_power(rep, folder)),
                     ("omega", lambda: run_power_omega(rep))):
        if (mode != part and not (mode == "all" and part not in ("persist", "signals", "theory", "probe", "final", "power",
                                                                 "omega"))) or \
                (part not in ("daily", "power", "omega") and folder is None):
            continue
        try:
            fn()
        except Exception:
            rep.p("")
            rep.p("PART '%s' FAILED (the other parts still ran):" % part)
            rep.p(traceback.format_exc())
    rep.p("")
    rep.p("runtime %.1fs" % (time.time() - t0))
    rep.save()
    if launcher:
        print("launcher: %s  (double-click it next time)" % launcher)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        if sys.stdin and sys.stdin.isatty():
            input("\nerror above. Press Enter to close.")
