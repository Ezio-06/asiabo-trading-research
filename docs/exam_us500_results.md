# US500 fresh-data exam: RESULT (run once, 2026-10-13 13:22)

Rules: exam_us500_spec.md (written and agreed before the run). Report: reports\exam_us500_20261013_132246\. Context: reports\exam_baseline_20261013_131626\ (spent US500 2020+).

## Verdict (pre-registered rule, applied as written)
| Part | n | win | net R/trade (t) | EDGE (t) | Verdict |
|---|---|---|---|---|---|
| **fast** | 85 | 31.8% | **-0.287 (t -2.1)** | -0.003 (t -0.0) | **FAIL** (net t ≤ -2) |
| **dip** | 31 | 67.7% | -0.106 (t -0.4) | +0.093 (t +0.3) | **MIXED** |
| **BOOK** | | | | | **FAIL** |
| brk (report only) | 167 | 21.6% | -0.523 (t -3.2) | +0.031 | - |
| ins (report only) | 122 | 37.7% | -0.164 | +0.006 | - |

**Leads:** #31 UNREADABLE (7 trades). #27 vs #28: **#28 wins** (16 triggers; #28 EDGE +0.095, #27 -0.095). That's a sign for the record only (noise swings ±0.44).

**Agreed decision rule → fast goes back to the why phase. dip stays (MIXED). No paper trading.**

## Training vs exam (same code)
| | fast net / EDGE | dip net / EDGE |
|---|---|---|
| Training US500 2020-21 | +0.034 / +0.034 (51 trades) | +0.757 / +0.861 (20) |
| Training US500 2024+ | +0.072 / +0.044 (171) | +0.552 / +0.650 (28) |
| **Exam US500 2016-19** | **-0.287 / -0.003 (85)** | **-0.106 / +0.093 (31)** |

## What it says (plain)
- **fast lost its direction value on new data.** EDGE ≈ 0: on the fresh years, fast's direction choice was no better than a coin flip. And costs plus no follow-through ate ~0.28 R per trade. A small edge plus big costs = a loss. (Breakdown below.)
- **dip did what dip does, minus one bad quarter:** positive in 2016, 2017 and 2019 (+0.27, +0.38); 2018 (-0.72 on 13 trades, the Q4 2018 sell-off) wiped it out. EDGE stayed positive. Training dip (+0.55..+0.76) sits about 2-3 standard errors above this result, so the exam is in some tension with dip's training level, but 31 trades can't settle it.

## Data caveat (found after the run; does NOT change the verdict)
The old export covers fewer hours:
- **2016-17:** often only the US cash session (14:30-20:00 UTC); 2017 has data before 13:30 UTC on only 10-50% of days; several 2017 Mondays start at the cash open.
- **2018-19:** full 07:00-19:59 UTC, the same coverage as training 2020-21.

**Check on the clean years only:** fast 2018-19 = 50 trades, net -0.36 R/trade (2018 -0.17, 2019 -0.56). The FAIL holds where the data matches training. The thin 2016-17 data cost fast trade count (85 vs Claude's predicted 150-220), not the verdict.

**Process lesson:** the exam should have pre-registered a data-coverage check (hours-with-data per year vs the training years) before scoring. Add it to every future exam.

## Predictions scored
| | Claude | Ezio | Result |
|---|---|---|---|
| fast | MIXED (FAIL second) | same | **FAIL** |
| dip | PASS ~55% | leaning PASS | **MIXED** |
| book | MIXED | MIXED | **FAIL** |
| #27 vs #28 | #28 | #27 | **#28** (sign only) |
| brk EDGE > 0, ins ~0 | yes | - | +0.031, +0.006 ✓ |
| #31 unreadable | yes | - | ✓ (7 trades) |
| fast n 150-220 | - | - | 85 ✗ (data hours) |

Both of us were too optimistic on the core book.

## What happens next
- **fast → the why phase.** First answer (below): fast's edge was never on US500; it's on gold.
- **dip → stays in the book (MIXED).** The 2018 sell-off is the known risk: dip buys pauses in an uptrend (T7 revised), so a regime break hurts it.
- **Data:** the exam is now spent, so the US 500 2015 file can go into bars_input → build_bars_db → synth_cache. **The two US TECH 100 files stay in exam_hold** (fresh data for N1 / N3 / #33).

---

# Why fast failed: decomposition (cloud, 2026-10-13 ~13:50; exam data now spent, real training bars rebuilt from Ezio's cache)
Same code as the exam; training numbers reproduce the baseline exactly (51 / 171 fast trades, same R).

**net = − cost + (both-direction path) + EDGE.** "Both-direction path" = the gross R of a trade and its coin-flip mirror averaged: positive when breakouts in EITHER direction follow through intraday, negative when both get stopped.

| US500 fast | n | gross | cost | coin-flip | EDGE | net | median stop |
|---|---|---|---|---|---|---|---|
| Training 2020-21 (all orb30) | 51 | +0.137 | 0.102 | +0.001 | +0.034 | +0.034 | 31 bp |
| Training 2024+ orb30 | 68 | +0.327 | 0.101 | +0.081 | +0.145 | +0.226 | 27 bp |
| Training 2024+ main2 | 103 | +0.034 | 0.064 | -0.009 | -0.022 | -0.030 | 45 bp |
| **Exam 2016-19 (all orb30)** | 85 | **-0.108** | **0.179** | **-0.284** | **-0.003** | **-0.287** | 25 bp (2017: 13 bp) |

Exam net -0.287 ≈ costs -0.179 + both-direction path -0.105 + direction -0.003. **Three causes:**
1. **Costs nearly doubled in R** (0.18 vs 0.08-0.10). Cost in price terms rose too (~4.4 bp vs ~3.0 bp per trade): the spread in index points was similar while the index was at about half the price, and 2017's opening ranges were tiny (13 bp stops).
2. **No intraday follow-through in either direction** (path -0.105 vs +0.10 in training): after the opening range broke, price tended to come back. 2016-19 was a calm grind-up market, a snap-back regime for 30-minute breakouts. That fits T1: fast is a momentum bet.
3. **Direction value zero** (EDGE -0.003). And it was never strong on US500: training EDGE +0.03 (2020-21) / +0.04 (2024+), all of it orb30 in 2024+.

**main2 never ran on US500 before 2024:** the 2020-21 export has no overnight hours (07-19 UTC), so the overnight box can't form. Every US500 fast trade before 2024, and in the exam, is orb30.

## Where fast's edge actually lives: gold (spent training data, cloud)
| gold fast | n | net (t) | EDGE (t) |
|---|---|---|---|
| ALL 2014-26 (excl. sealed 2022-23) | 546 | +0.116 (1.1) | **+0.206 (3.0)** |
| 2014-17 | 229 | +0.008 | +0.219 (1.9) |
| 2018-19 | 77 | +0.204 | +0.274 (2.7) |
| 2020-21 | 107 | +0.144 | +0.181 (1.2) |
| 2024+ | 133 | +0.230 | +0.164 (1.2) |

Gold's direction value is positive in all 4 eras, and the clustered t is 3.0 overall. US500's was ~+0.04. **The exam tested fast on its weakest market.** The failure says "fast on US500 is not real". It does not say "fast is not real". But "fast = gold" is a hindsight market pick (T8 warned about exactly this), so it needs its own fresh test.

## Fresh data available for a gold test
- 2020-21 gold is TRAINING (spent). Only **gold 2022-23 is sealed** (~100 fast trades expected).
- Expected power: an EDGE of +0.2 on ~100 trades shows at t ≈ 1.3, so the test can refute but not prove.
- Opening it spends gold 2022-23 only; other markets' 2022-23 stays sealed. Ezio's call (core_book_v2: exams stay sealed until the book grows).

## dip footnote
In the exam, dip3 held up (20 trades, net +0.25, EDGE +0.47); rsi2 collapsed (11 trades, net -0.75, mostly 2018). Hindsight split on tiny samples: a note, not a finding.
