# FROZEN DESIGN v1: the omega book (frozen 2026-10-09)

**Status:** Rules frozen. From here, only the "why" phase may change them: it may remove a part, or swap a magic number for a derived rule that has no more free choices and reproduces the old value. Nothing new is added. Japan 225 and the sealed 2022-23 years have not been touched.

## Earners (four parts)
| Part | Rule | Markets | Risk/trade |
|---|---|---|---|
| **brk** (long-term) | main2 (box), orb30 / orb60 (range), pdh2 (mid), retest2 (0.25D); wide stop + 5-day chandelier exit; only when edge20 OR er10 agrees with the trade direction | XAUUSD, US500, GERMANY40, USDJPY (+ Japan 225, decided before testing) | 0.25% |
| **ins** (short-term) | inside day: stop orders at yesterday's high / low, stop at yesterday's middle, exit at the close | same as brk | 0.25% |
| **dip** (medium, steady) | rsi2 long + dip3 long (Connors-style dip-buys above the 200-day average), own exits | US500, GERMANY40 (+ Japan 225) | 0.50% |
| **fast** (intraday harvester) | orb30 (range) only when er10 agrees; main2 (box) only when edge20 agrees; exit at the close | same as brk | 0.10% |

## Book rules
- **Positions:** one per part, market and direction at a time.
- **Risk:** fixed fractional (no Kelly: it sized up after hot streaks and lost about 40 R/yr).
- **Open risk:** at most 6% of equity (never binding so far).
- **Not included:**
  - loss gates (the scorecard showed them useless inside this book)
  - sizing states (streak / form20: within noise)
  - canary sizing rule (alarm-week trades were better)
- **Canaries (breakout follow-through, dip bounce, spreads):** reported as a dashboard only. A canary outside its 2014-21 band for most of a quarter = human review, never an automatic action.

## Open questions handed to the synthetic test (Ezio, 2026-10-09)
- The hot-streak finding (T5) and the canary finding (T22) may be quirks of this dataset's ORDER of events. The synthetic batch checks whether they reappear on reshuffled histories.
- The lab's tie-breaking between trades opening at the same moment was non-deterministic until 2026-10-09 (fixed). Run 7-9 numbers may shift slightly on rerun; the batch's "real" run is the corrected reference.

## Results so far (in-sample, all seen during selection; expect shrinkage)
- **$10k, fixed risk:** +0.5 / +2.6 / +15.1 / +18.7 %/yr (2014-17 / 2018-19 / 2020-21 / 2024+); max drawdown 21.7 / 7.9 / 5.6 / 3.0%.
- **Known weak spots:**
  - 2014-17 is roughly flat with a 26-month underwater stretch.
  - Market lists are hindsight (all-markets check is worse in 2018-19).
  - dip has about 30 trades before 2020.
  - Germany 40 / US500 trades are often too small at $10k.

## Next (in order)
1. Synthetic batch: frozen book on cousin histories (shuffle, dayshuffle, cosmetic, vol up/down, trend up, costly), many seeds, with predictions written down first.
2. "Why" phase: plateau tests (±25% on 20 / 50 / 5-day / thirds / stop width), dose-response, where the money comes from, placebos, 1.5x costs. Kill-only, or derived-rule swaps.
3. Japan 225 (one shot).
4. Sealed 2022-23 exam (one shot, EXAM_UNLOCK).
