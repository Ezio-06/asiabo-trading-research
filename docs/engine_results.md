# Pocket engine stage 1: results (run 2026-10-10, reports\engine_*, 23 worlds, 2 seeds, 0 failed, 42 min)

Edge = cost-free direction value per trade. Slope per dial step is pooled over seeds and clustered by seed x market x month. Predictions were written before the run (engine_plan.md).

## D1 momentum vs snap-back (the new dial): the big result
| Part | Snap-back k+1.5 ... momentum k-0.4 (edge/trade) | Slope t | Predicted | Verdict |
|---|---|---|---|---|
| brk | -0.27 / -0.14 / +0.05 / +0.17 / +0.52 | +6.6 (both seeds, OLD and NEW) | + | **CONFIRMED** |
| fast | +0.01 / +0.05 / +0.07 / +0.12 / +0.19 | +6.8 (both seeds, OLD and NEW) | + | **CONFIRMED** |
| ins | +0.08 / +0.09 / +0.09 / +0.10 / +0.16 | +2.2 (flat until extreme momentum) | 0 | UNCLEAR (mostly flat) |
| dip | +0.10 / +0.27 / +0.34 / +0.42 / +0.39 | +2.5 (both seeds) | - | **CONTRADICTED** |
| dipx | +0.04 / +0.21 / +0.20 / +0.22 / +0.15 | +1.0 (upside-down U) | - | NOT SHOWN |

- **brk is a pure momentum bet.** It loses in snap-back markets and earns heavily when moves persist. This is the "WHEN" for brk: markets whose moves keep going (20-day variance ratio about 0.9+).
- **fast** is the same mechanism, milder, and never clearly negative even in the worst world. That is why it survived.
- **dip is NOT a snap-back trade.** It does WORSE when markets snap back and better with momentum (dipx flattens at both extremes). Combined with the why-phase placebo (random days above the 200-day average earn over half of dip), dip = buying a pause INSIDE a persistent uptrend (trend continuation with a pullback entry), not mean reversion. T7's mechanism is revised.

## D2 day order / trend length: nothing confirmed
- Directions were mostly as predicted (brk, ins, dip, dipx up from dayshuffle to longblock) but every |t| < 2 with 2 seeds.
- ins drops from +0.085 to +0.010 on dayshuffle, and dip goes +0.30 -> +0.34 -> +0.53. These are suggestive, not shown. More seeds would be needed.

## D3 volatility: calibration passed
- Edge flat for every part. Net R rises with volatility for brk / ins / fast (t 8-22), steepest for the short holds. The cost theory T3 holds.
- dip's net is insensitive (long holds, small costs).

## What this means for growing the book (Ezio's "keep them for when they work")
- **brk has a causal WHEN: momentum regimes.** The next test is whether a market's CURRENT momentum regime can be read in time. Candidate: a trailing persistence measure (e.g. a 60-120 day variance ratio or trend-month share per market), brk on only above a threshold.
  - Pre-register the threshold from theory (VR > 1, i.e. moves persisting), use a half split, and run the engine's dial as the causal check.
  - Caveat T4: trend MONTHS could not be predicted before. A persistence REGIME over months is a different, slower question.
- **ins:** insensitive to momentum. Its lever remains compression width (narrow inside days), not a regime.
- **dip:** reframe as uptrend-pullback. Its "when" = persistent index uptrends. It also overlaps brk's regime (both like momentum), so it diversifies less than thought. Watch the correlation.
- **Stage 2 hunt:** use momentum / persistence as the first context axis, since it is now causally established for brk / fast / dip.
