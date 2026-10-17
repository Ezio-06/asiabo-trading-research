# Momentum switch: real-data test (PRE-REGISTERED 2026-10-10 16:20, before the real run)
Source: regime engine (synth, known truth) -> er40 reads momentum (AUC 0.79-0.88). Never used on real data before.

**Switch:**
- er40 = |close(-1) - close(-41)| / sum of |daily moves| over 40 days, per market, known at the start of the entry day.
- ON when er40 > **0.30**.
- brk and fast only, applied before the one-position rule.

**Predictions:**
- **P1:** brk switched edge/trade > unswitched in >= 3 of 4 eras.
- **P2:** brk trades turned away are worse than kept, clustered t >= 2.
- **P3:** fast as P1.
- **P4:** brk switched edge beats the 90th percentile of 20 random switches with the same share of days per market.

**Reinstatement:** brk comes off the shelf only if P1 + P2 + P4 hold AND switched brk passes the W3 rule (net > 0 without its best market-year in >= 2 of 4 eras).

Exploratory only: an adaptive threshold (er40 > its own trailing 500-day 67th percentile).

**Cloud random-walk check:** every prediction FAILED, as it must on a market with no momentum (switched brk -0.10 vs random switches median +0.01).

## RESULT (real run 2026-10-10 16:20)
| Check | Result |
|---|---|
| P1 brk switched edge > unswitched | **HOLDS, 4 of 4 eras** (ALL +0.132 -> +0.275 per trade; net +0.095 -> +0.316) |
| P2 turned-away brk trades clearly worse | **FAILS**: kept +0.229 vs turned away +0.107, t +0.9. The turned-away trades still earn; the switch CONCENTRATES, it does not remove harm |
| P3 fast | HOLDS 4 of 4 (+0.113 -> +0.177), BUT fast's real switch (+0.177) is below random switches' 90th percentile (+0.249) -> not distinguishable from "trade fewer days" |
| P4 brk vs random switches | HOLDS, narrowly: +0.275 vs 90th percentile +0.231 (max +0.293) |
| W3 on switched brk | PASSED (3 of 4 eras net > 0 without the best market-year) |

**Pre-registered verdict:** brk STAYS SHELVED (P2 failed).
- The code's line "fast switch: worth adopting" applied P3 alone. My yardstick omission for fast was caught on reading: random switches do as well, and fast's R/yr falls (16 -> 6). Recommendation: do NOT switch fast.

**Money ($10k, fixed risk, %/yr by era 14-17 / 18-19 / 20-21 / 24+):**
| Book | Return | Max drawdown | Longest underwater (2014-17) |
|---|---|---|---|
| Core now (fast + dip) | +0.5 / -0.4 / +7.3 / +3.4 | 4.2 / 2.1 / 1.6 / 3.5% | 25 months |
| Core with fast switched + brk switched | +2.9 / +1.7 / +6.5 / +3.5 | 4.4 / 2.0 / 1.5 / 4.4% | 6 months |
| Old frozen 4-part book | +0.8 / +1.0 / +15.8 / +18.6 | | |

**Lesson:**
- er40 does read something real: brk's edge doubles when it is on, in every era, and beats random switches.
- But real "off" days are not harmful for brk (+0.11 edge). Real regimes are softer than synth's: neutral is mildly positive, not ~0, and snap-back is rare.
- Any future use of the switch needs NEW data (the real eras are now spent for it).
