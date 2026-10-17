# Gold fast: peak R vs kept R (give-back study, 2026-10-13, spent data, descriptive only)

**Question (Ezio):** how much profit did fast trades SEE before the close and then give back? e.g. "we were up 9R and closed at a loss".

**Method:** all 546 gold fast trades (2014-26 minus the sealed 2022-23), walked on M1 bars from entry to the close (or the stop). Peak = best open profit in R; kept = where it closed (gross, before costs). **Yardstick:** the same entries traded the OPPOSITE way (coin-flip mirror), which shows how much give-back pure path geometry makes.

## Headline
| | real direction | mirror (geometry) |
|---|---|---|
| avg peak | 1.81 R | 1.42 R |
| avg close | +0.25 R | -0.19 R |
| avg given back | 1.56 R | 1.62 R |
| total peak / kept / given back | 990 / +138 / 852 R | 778 / -105 / 883 R |

**Most give-back is geometry, not a flaw.** Any path's best point sits above where it ends; the mirror gives back just as much. What fast's direction adds is reaching peaks more often (52% of trades hit +1R vs 38% for the mirror) and keeping more of the big ones.

## Where the give-back hurts
| peak reached | trades | kept ≥ half the peak | closed ≤ 0 | of which stopped |
|---|---|---|---|---|
| ≥ 1R | 283 (52%) | 42% | 38% | 95 |
| ≥ 2R | 163 (30%) | 55% | 28% | 41 |
| ≥ 3R | 94 (17%) | 69% | 15% | 13 |
| ≥ 5R | 43 (8%) | 86% | 5% | 2 |

- **Small peaks (1-2R) are where the money leaks:** 95 trades were up 1R+ and still went on to hit the full stop (mirror: 79, so about 16 of those are "extra" beyond geometry).
- **Big peaks mostly get kept:** past 5R, 86% close at half the peak or better.
- **"Up 9R, closed at a loss" happened once:** 2021-05-21, peak +9.56R → stopped -1R. Other big round-trips: 2017-09-01 (+6.75 → -1), 2019-08-13 (+4.72 → -1), 2024-07-17 (+4.02 → -1). Reaching 3R+ and closing ≤ 0: 14 trades in 11 years.
- **By year,** fast keeps 0-42% of the peak it sees; 2016 and 2024 gave back more than all of it.

## Read
Fast's real problem isn't the occasional 9R round-trip (rare). It's the many trades that go 1-2R up and then come back to the full stop. Any "lock in" idea has to beat the mirror on exactly those trades, without clipping the 5R+ runners that carry the edge (T17 / T24). Follow-up below. (The second script counts 102 such trades instead of 95: slightly different bar handling, same picture.)

---

# Follow-up: winner-side trails and the 2-hour checkpoint (2026-10-13 ~16:20, spent gold data, exploratory)
Every rule was also run on the mirror trades. The whole grid is shown, not only the best cell. Gross R, before costs (one exit either way, so costs don't change between rules).

**Scale check:** gold's median daily ATR = **4.5 R** (fast's stop is the opening-range box, about 0.22 of a daily ATR). So a "1 daily ATR" trail sits ~4.5R behind the peak and almost never binds inside one day.

| Rule | real total | mirror total | real − mirror | 1R+ then full stop | 5R+ runners avg kept |
|---|---|---|---|---|---|
| baseline (close / stop) | +137.8 | -105.4 | +243.1 | 102 | +5.57 (46) |
| breakeven at +1R | +122.5 | -117.0 | +239.4 | 0 | +5.43 (34) |
| trail 0.5 daily ATR, arm +1R | +120.5 | -99.2 | +219.7 | 55 | +5.36 (41) |
| trail 1.0 daily ATR, arm +1R | +143.0 | -97.4 | +240.4 | 92 | +5.57 (46) |
| trail 1.0 daily ATR, arm +2R | +140.1 | -98.5 | +238.5 | 96 | +5.57 (46) |
| trail 1.5 daily ATR, arm +1R | +135.9 | -103.9 | +239.8 | 98 | +5.57 (46) |

- **No trail adds direction value.** Real − mirror stays ~+240 for every rule. Trails only reshape the results (the random-walk fact: exit rules can't create an edge).
- **Breakeven at +1R removes all 102 "1R up then full stop" trades, but costs 15 R net.** Trades that dipped back to entry and THEN won were cut, and they were worth more than the saved stops. The 1-2R leak is real, but plugging it costs more than it saves.
- Daily-ATR trails don't clip winners, but on fast's one-day hold they barely bind, so they change little (+5 R at best: noise).

## The 2-hour checkpoint: does midday predict the close? (baseline paths)
| state 2h after entry | REAL n | REAL rest of day | MIRROR n | MIRROR rest of day |
|---|---|---|---|---|
| up (≥ +0.3R) | 174 | **-0.01** | 128 | +0.05 |
| flat | 215 | **+0.36** | 214 | -0.24 |
| down (≤ -0.3R) | 55 | **+0.27** | 75 | -0.17 |

- **Trades already up at 2h are done:** their afternoon is ~0. They keep the gain but add nothing.
- **Slow starters carry the afternoon edge:** flat-at-2h trades earn +0.36 R more (mirror -0.24); down-at-2h trades recover +0.27 R (mirror -0.17).
- **So "cut the ones that are losing by midday" would HURT gold fast:** it would throw away exactly the trades where the real direction still pays.
- **Possible lead (not tested as a rule):** since the up-at-2h group's afternoon is ~0, closing it at 2h would be roughly R-neutral and would cut variance and open risk. A sizing / risk question, not an edge. Needs fresh data before any use.

**Overall read:** fast's direction value on gold arrives **late in the day for the trades that start slowly**. Early winners are already "spent". That fits the why phase (edge keeps 55% even at a 1h-late entry).

---

# Who pays the afternoon? (2026-10-13 ~16:40, spent gold data, exploratory)
**Ezio's hypothesis:** no real payer; "a loss isn't real until it hits", and slow days come back by chaos.
**Test:** if it were chaos, the mirror trades (same days, other direction) would recover too. They don't: mirror flat -0.24, down -0.17. **Refuted:** the afternoon gain follows the morning's DIRECTION.

**Is it luck?** (rest of day after the 2h mark, t clustered by month)
| group at 2h | n | rest of day | 2014-17 | 2018-21 | 2024+ |
|---|---|---|---|---|---|
| up | 174 | -0.01 (t -0.1) | -0.07 | +0.21 | -0.21 |
| **flat** | 215 | **+0.36 (t +2.7)** | +0.13 | +0.53 (t 2.6) | +0.45 |
| down | 55 | +0.27 (t +1.2) | +0.70 | -0.20 | +0.07 |
- **Flat:** positive in all 3 eras, t 2.7. Unlikely to be pure luck (but found by looking: 3 groups, spent data).
- **Down:** not reliable (small, flips sign by era). "Never sell a loser before the close" has no support.
- **Up:** afternoon ≈ 0 in every era. "Lock in the winners" is neutral, not a gain.

**When the flat group's gain arrives (London clock):** most of it before the NY cash open (2h → NY open +0.28, t 3.0; NY open → close +0.08). Biggest single hour: **13:00-14:00 London: +0.14 R per trade (sum +26 R of ~+60)**, then 11:00-13:00 (+0.04, +0.06).

**Candidate payer (a story fitted after looking; must be tested fresh):** US money arriving. 13:00-14:00 London holds the **COMEX gold open (08:20 New York)** and the **US data releases (08:30 New York: jobs, CPI, retail sales)**. London's morning sets a direction; on days it hasn't fully moved by late morning, the arriving US flow finishes the move. On days it already moved (up at 2h), that information is priced, and the afternoon adds nothing. Payers = the late, need-driven US participants (futures hedgers, ETF / physical flows, data-reactive traders) who buy after the direction is already set. Classic slow information spread across time zones.

**Predictions that would kill or support it (fresh data only, e.g. gold 2022-23):**
1. Flat-at-2h trades gain in the afternoon, concentrated in the 13:00 London hour.
2. On US holidays (no COMEX session, no US data), the effect is absent.
3. Mirror trades show nothing in that hour (not yet checked even on spent data).
