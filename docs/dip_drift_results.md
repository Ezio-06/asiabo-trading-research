# dip + drift sizing on US Tech 100: RESULT (run once, 2026-10-13 17:28)

Rules: dip_drift_spec.md (locked before the run). Report: reports\dipdrift_20261013_172831\. Note: run before Ezio's prediction was written, so only Claude's prediction is on record.

## Verdict (pre-registered, noise-set bars)
- **dip itself on a fresh index (A): MIXED.** net +0.100 R/trade (bar +0.15), EDGE +0.226. Positive and above every noise run's net (max +0.13), but under the pass bar.
- **Ezio's design (D vs A): INSIDE THE NOISE.** D − A = +1.2 R (bar 13), drawdown +1.6 R (bar 9).

| Variant | n | win | net/trade | EDGE | sized R | max DD | 2020 | 2022 |
|---|---|---|---|---|---|---|---|---|
| A dip as it is | 110 | 71% | +0.100 | +0.226 | +11.0 | 15.5 | -3.8 | -2.8 |
| B + 1h confirmation | 111 | 70% | +0.077 | +0.200 | +8.6 | 18.3 | -0.7 | -2.7 |
| C + table | 98 | 72% | +0.136 | +0.265 | +12.9 | 17.4 | -5.5 | +2.5 |
| D full design | 99 | 72% | +0.126 | +0.250 | +12.2 | 17.0 | -2.3 | +2.0 |

Sized R by year (2017 → 2026), A: +2.6 -9.0 -1.2 -3.8 +9.0 -2.8 -0.8 +11.9 -2.1 +7.2 | D: +1.6 -10.1 -2.1 -2.3 +5.0 +2.0 +2.9 +11.9 +0.9 +2.3

## What it says (plain)
- **The table almost never bit.** D took 97 full-size trades, 1 half, 1 quarter, and skipped ~11 that A took. On a strong-drift index, quarter and year are "up" nearly all the time a dip signal fires. So D ≈ A with a few trades removed.
- **The trades it removed were mostly bad ones in 2022:** D +2.0 vs A -2.8 in the bear year (Claude predicted the opposite: wrong). Per unit of size, D's trades were a little better (+0.125 vs +0.100). Both are well inside the noise; it's a hint, not a finding.
- **The 1-hour confirmation cost a little** (B -2.4 R vs A), consistent with "it changes little". Noise-sized.
- **dip on fresh data is real but small:** EDGE positive on both fresh tests (US500 2016-19 +0.09, US Tech 100 +0.23), net +0.10 here and -0.11 on the US500 exam. Training said +0.55..+0.76 per trade. **Fresh data puts dip at roughly a fifth of its training size.**
- 2018 was dip's worst year again (-9 R in A; worst quarter 2018-Q1, the February volatility spike), matching the US500 exam's 2018 loss.

## Data
US Tech 100 coverage: 2017 thin (cash hours only on many days); 2018-2023 07:00-19:59 UTC; 2024+ near 24h. dip trades on daily signals with next-open entries, so it's less sensitive to the hour gaps than fast. Known-event holes (2020 circuit breakers etc.) tagged.

## Predictions scored (Claude)
| Prediction | Result |
|---|---|
| A PASS more likely than not | ✗ MIXED (net +0.10 < +0.15; EDGE +0.23) |
| D trades more than A | ✗ fewer (99 vs 110) |
| D gains in 2020 | ✓ (-2.3 vs -3.8; noise-sized) |
| D worse than A in 2022 | ✗ better (+2.0 vs -2.8) |
| B ≈ A | ✓ (-2.4 R) |
| D vs A INSIDE THE NOISE | ✓ |

## What it means for the book
- dip stays: positive EDGE on two fresh tests, but expect ~+0.1 R/trade, not +0.6.
- Ezio's table is harmless and possibly helps in bear years, but it's unproven. It rarely changes anything on a strongly drifting index. A weaker-drift index (Germany 40, Japan 225) is where it would bite more.
- US Tech 100 is now spent for dip. It stays fresh for N1 / N3 / #33 only if those tests don't use dip's results.

---

# Synth test of the "negative" side of the table (2026-10-13 ~17:45, cloud, no real data)
**Question (Ezio):** on real US Tech 100 the table almost never had a down quarter to react to. Does its "shrink / stop" side work when bear and choppy stretches really happen?

**Worlds:** 8 fake indices (2015-12 → 2026-10), each a chain of planted spells: bull +25%/yr (55%), flat 0 (25%), bear -30%/yr (20%), spell length ~6 months on average (min 40 days), constant volatility. A and D run with the same code as the real test, scored by the spell each trade entered in.

**Claude's prediction (written before the run):** D cuts bear-spell losses by about half, pays a smaller cost early in bull spells, and beats A overall.

| spell | A sized R (trades) | D sized R (trades) | D − A | D's avg size | first ~quarter of the spell: A / D |
|---|---|---|---|---|---|
| bull | -12.2 (404) | -16.5 (400) | -4.3 | 0.95 | -29.4 / -31.3 |
| flat | -53.0 (151) | -58.8 (176) | -5.8 | 0.89 | -16.9 / -24.3 |
| bear | -75.9 (78) | -64.3 (79) | **+11.5** | **0.85** | **-57.3 / -49.3** |
| total | -141.0 | -139.6 | +1.4 | | |

(All worlds net negative: the fakes have drift but no real bounce, so read the A-vs-D differences, not the levels.)

**Findings:**
1. **The negative side points the right way, but it's slow.** D saved 11.5 R in bear spells (15%), not the half Claude predicted. Its average size in bear spells was still 0.85.
2. **The damage happens before the table can see it.** 75% of A's bear-spell loss (-57 of -76 R) lands in the FIRST quarter of a bear spell, while the 63-day quarter still reads "up" from the bull before it. The quarter clock is the bottleneck.
3. **Removing the 200-day costs in chop:** D took more trades in flat spells (176 vs 151) and lost 5.8 R more there.
4. **Net: a wash** (+1.4 R over 8 worlds), consistent with the real run's INSIDE THE NOISE.

**The structural problem:** dip buys short-term weakness. Any fast "the trend is breaking" detector fires on that same weakness and blocks dip's own trades; any slow one (the quarter) reacts after most of the damage. Price-trend clocks can't escape this trade-off.

**Where a faster warning might come from (idea, untested):** not price direction but **volatility**. In indices, bear phases usually start with a volatility jump, and vol is our most readable state (atr10, lag ~8 days; N2). These synth worlds have constant volatility, so they can't test it; real data can. Candidate: shrink dip when index volatility jumps above its own normal, independent of the quarter. That gives the negative side a fast clock that doesn't fire on ordinary calm dips.

---

# Volatility state and dip (2026-10-13 ~18:55, spent data for dip: US500, Germany 40, US Tech 100; learning, not proof)
**Competing predictions (written before the run):**
- **Ezio:** volatility is bad for dip either way. In volatile stretches the triggers (3 down closes, RSI(2) < 10) fire on "dips that aren't dips", falling knives.
- **Claude:** it depends on direction. High and rising is worst; high and falling (panic exhausted) is best.

**State at the signal day:** 20-day ATR vs its own 1-year median. Normal < 1.3×; high-rising = ≥ 1.3× and above its level 5 days earlier; high-falling = ≥ 1.3× and not rising.

| state | US500 | Germany 40 | US Tech 100 | ALL (n, net/trade, t, total) |
|---|---|---|---|---|
| normal | +0.62 (42) | +0.11 (80) | +0.29 (81) | 203, **+0.285 (t 2.8)**, +57.8 R |
| high-rising | +0.83 (5) | +0.49 (7) | -0.48 (19) | 31, **-0.047**, -1.5 R |
| high-falling | +0.51 (1) | +0.99 (3) | -0.11 (13) | 17, **+0.124**, +2.1 R |

**Read:**
- **Pooled, Ezio's prediction holds and Claude's fails:** both high-vol groups are well below normal, and high-falling is NOT the best.
- **But it rests on US Tech 100:** US500 and Germany 40 high-vol trades were fine (5 / 1 / 7 / 3 trades: too few to read). The high-vol groups are tiny (31 and 17 trades).
- **Practical size:** about 80% of dip trades happen in normal volatility, and they carry all the profit. Skipping the high-vol 20% would leave total R about the same (+57.8 vs +58.4) with fewer trades and less stress exposure.
- **Next (if pursued):** lock "skip / shrink dip when 20-day ATR ≥ 1.3× its 1-year median" as Ezio's rule, and test it on a FRESH index (US 30, not yet exported) with predictions first.
