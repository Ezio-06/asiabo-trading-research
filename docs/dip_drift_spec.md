# dip + drift sizing on US Tech 100: pre-registered spec (LOCKED 2026-10-13 ~17:40, Ezio's design, not run)

Script: asiabo_dipdrift.py. Module `dipdrift` (ONE-SHOT; refuses to run twice: exam_hold\DIPDRIFT_DONE.txt).

## The plain version (Ezio)
dip's payer is the index's own long-run drift (500 companies surviving and growing; the index drops its losers) plus a small fee for buying from forced sellers. So size dip like an investor who owns the index himself: full when the index is clearly climbing or suddenly recovering, small when it's unclear, out when it's falling with no sign of recovery. And don't buy the dip until a shorter timeframe shows the bounce has started.

## Sizing table (locked; Ezio; up/down signs only, nothing fitted). REPLACES the 200-day filter (Ezio: "the 200-day is almost a whole trading year, it just asks 'is the year up'")
Read on the index's OWN daily closes at the signal day (never on our trades' results: T5 / K5).
- **Quarter** = close vs close 63 trading days ago. **Year** = close vs close 252 days ago.
- **Floor** = the **100-day** average, chosen on NOISE only on spent data: it flips 4.7 times a year on US500 vs 14.1 for the 50-day, and 10.2 vs 18.5 on Germany 40.

| Last quarter | Year | Price vs 100-day | dip size |
|---|---|---|---|
| up | up | any | 1 (full) |
| up | down | above | 1 (sudden recovery: catch it) |
| up | down | below | 0.25 (maybe a small peak in the trough) |
| down | any | above | 0.5 |
| down | any | below | 0 (dead: falling, no recovery) |

## Entry confirmation (lower timeframe)
After the dip signal (the day's close), enter at the close of the **first 1-hour bar that closes above the previous 1-hour bar's high**, within the next trading day. No such bar → no trade. (Spent data: dip keeps 98-101% of its edge when entered up to a day late.)

## Unchanged
dip's triggers and exits: rsi2 long (RSI(2) < 10, out at the next open after a close above the 5-day average, 20-day cap) and dip3 long (3 lower closes, out on the first close above the prior day's high or after 10 days), 3N disaster stop, risk unit 1N, long only, real costs, one position at a time for rsi2 + dip3 together. **Engine check (cloud, spent data):** variant A reproduces the book's dip trades exactly on US500 (48/48, same R) and 89/90 on Germany 40 (one tie-break, ~1 R).

## Data
- **US Tech 100**, both files in exam_hold (M1 2015-12-18 → 2026-10). Never read by anything; dip has never traded it. The test builds its own exam_hold\ustech100.db (bars.db untouched). That db holds only US Tech 100, so the 2022-23 seal (which protects the six house markets) is lifted for it: the 2022 bear market (-33%) is the point.
- **Market spec = a translation of US500's:** NY clock and session, same cost model and recorded spreads; swap and min stop in index points ×4. Fixed before the run.
- **Same scoring window for all variants:** trades entering after the table's 252-day warm-up (from about 2016-12).
- **Data coverage is printed BEFORE any result** (exam lesson).

## Variants
| | Filter | Entry |
|---|---|---|
| A: dip as it is | 200-day | next open |
| B: + confirmation | 200-day | 1-hour confirm |
| C: + table | table | next open |
| **D: Ezio's full design** | **table** | **1-hour confirm** |

## Verdict rules (bars set on noise BEFORE any real data)
- **dip itself (A):** PASS = net > +0.15 R/trade and EDGE > 0 (the US500 exam's bars). On 14 noise worlds A never passed (net -0.71 .. +0.13).
- **D vs A:**
  - **WINS** = sized R beats A's by more than **13 R**, and drawdown is not worse
  - **SAFER** = max drawdown smaller by more than **9 R**, and sized R at most 25% below A's
  - **LOSES** = sized R below A's by more than 13 R
  - otherwise **INSIDE THE NOISE**

**Why the bars:** the first draft ("D ≥ A and drawdown ≤ A") was run on 10 fake random walks with index-like drift. Noise "WON" 5 of 10 times. D − A swung -10.7 .. +12.5 R and the drawdown gap -8.6 .. +4.5 by pure chance. The bars sit above every noise run.

**Power:** about 100 trades over 9 years. Only a large difference between D and A can show. A small real improvement will read INSIDE THE NOISE.

## Measures in the report
Per variant: n, win %, net R/trade, EDGE, sized R, max drawdown, worst quarter, trades per size tier, sized R per year, 2020 and 2022 separately, and R per unit of size (does the table pick better trades, or just trade less?).

## Predictions
**Claude (before any real run; revised after the noise runs, still before any real data):**
- A on US Tech 100: PASS more likely than not (a strong-drift index).
- D trades more than A (no 200-day): gains in the 2020 recovery, loses some in the 2022 bear-market rallies (quarter down but above the 100-day → half size). 2022: D worse than A.
- B ≈ A (confirmation changes little).
- **D vs A: INSIDE THE NOISE most likely.**

**Ezio:** _(to be written before the run)_
