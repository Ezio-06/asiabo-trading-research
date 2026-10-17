# Why phase: results (run 2026-10-10, reports\why_* + why_synth_dayshuffle_s1)

The rules were pre-registered in why_phase_plan.md. The identity check is IDENTICAL on both runs: 4,814 book trades on the real data, plus every rebuilt lane. Judged with clustered t. Noise yardsticks:
- 3 fake random walks (from the cloud test runs)
- one day-shuffled cousin (`why_synth_dayshuffle_s1.txt`): real days, no multi-day order

## Verdicts by the pre-registered rules
| Part | W5 cost (flag) | W3 market-year (kill) | W1 plateau (kill) | Verdict |
|---|---|---|---|---|
| brk | ok | **KILL**: 3 of 4 eras net <= 0 without the best market-year (USDJPY 2014, USDJPY 2018, XAUUSD 2020) | plateau, 0 peak eras | **REMOVE** |
| ins | ok (2 of 4 eras < 0 at x1.5) | **KILL**: 3 of 4 eras (2014-17 net < 0 anyway; 2018-19 and 2024+ hang on one market-year) | plateau | **REMOVE** |
| dip | ok | keep (1 of 4) | plateau | keep |
| fast | ok | keep (2 of 4) | plateau | keep |

D1 and D2 derived rules: D1 was better in 2 and 0 of 4 eras; D2 in 3, 1, 2 and 1. No swap is warranted (noise produced 0 to 4 of 4).

## What the mechanism tests say (beyond the rules)
- **ins** has the strongest mechanism evidence in the report but does not pay after costs.
  - The inside condition matters: edge +0.121, t +3.3, vs +0.019 on every other day.
  - Narrower is better: slope t -3.0, and OLD and NEW agree. This is the only W2 test that clears the +-3 bar.
  - It fades within 15 minutes when delayed (12% kept), exactly as an intraday follow-through effect should.
  - On the day-shuffled cousin it vanishes.
  - Conclusion: a real effect, too small for its spread. The 2014-17 spread is 0.12 R per trade.
  - Next-cycle candidate (NEW rule, not allowed now): inside days narrower than ~0.4 ATR (edge +0.61, n 169, t 3.7).
- **brk**:
  - Direction value is positive in every era (ALL t +2.6), but the net in 2014-21 is about zero and lives in one market-year per era.
  - Anatomy: winners are no more "early" than on a random walk (74% positive at 4h vs 75-77% on noise). There is a little more in place by day 1 (80% vs 69-74%).
  - Entering one day late erases the edge.
  - Random days with the same trend filter keep about half the edge (+0.072 vs +0.132).
  - On the day-shuffled cousin, brk 2024+ earns MORE (+77.7 R/yr vs +47.7). The 2024+ money does not need multi-day ORDER, which is consistent with riding the era's drift (gold) rather than breakout follow-through.
- **fast**:
  - Edge t +3.2 overall. It keeps 86% of its edge if entered 15 min late and 55% at 1h. Random days keep less than half the edge (+0.051).
  - Same edge on the day-shuffled cousin (t +3.3), so it is an intraday effect.
  - Its trend filters (edge20 / er10) show NO dose-response in 2024+ (slopes t -0.5 / +0.3). The filter is probably decorative. Removing a filter is not allowed in this phase, so this goes on the next-cycle list.
- **dip**:
  - Delays cost nothing (98-101% kept up to one day): a multi-day snap-back, as predicted.
  - BUT a random day above the 200-day average, with the same exits, earns +0.233 (t +3.8) of dip's +0.399. Over half of dip is "long an index in an uptrend". The dip trigger adds about +0.17 per trade.
  - No depth response: RSI slope t -0.7. The count is best at exactly 3 (t 4.6 in that bin) but not monotonic.
  - Only about 30 trades before 2020.
- **W5**: cost sensitivity is an ERA effect (2014-17 spreads), not a hold-length effect. At x1.5 the 2014-17 book goes to -1.6%/yr and 2024+ barely moves.

## Rough size of the book without brk and ins
At unchanged risk (fast 0.1%, dip 0.5%), from the R/yr lines, no compounding, ignoring small-position skips: about +0.5 / -0.1 / +8 / +8 %/yr across the four eras. With brk and ins it was +0.8 / +1.0 / +15.8 / +18.6. Most of the 2024+ return came from brk. Re-sizing is NOT allowed in this phase.

## Decision needed (Ezio)
The pre-registered rules say REMOVE brk and ins. Honouring them is the point of pre-registration. Then Japan 225 and 2022-23 test a two-part book (fast + dip).
