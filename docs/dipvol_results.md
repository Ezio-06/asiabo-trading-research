# dip: skip when volatility is high AND rising (exploration on spent data, 2026-10-13 ~19:45)

Script: asiabo_dipvol.py (module `dipvol`). **Exploration, not confirmation:** every index here was already used for dip, and the idea came partly from US Tech 100. Note: the first full result came from Claude's cloud check on copies of the real spent bars (US500 / Germany 40 rebuilt from the cache + the two exam dbs), not from fake data, so it exists before Ezio's prediction. Nothing fresh was spent.

## Gauge, chosen WITHOUT profit figures
On 20 fake worlds with planted volatility episodes (40 days: 20 rising, 20 falling), how well each ATR reads "high and rising":
| gauge | right when it says "rising" | rising days caught | flips / yr |
|---|---|---|---|
| ATR 5 | 62% | 65% | 13.1 |
| **ATR 10 (primary)** | **64%** | **63%** | **5.4** |
| ATR 20 (used before) | 43% | 46% | 3.8 |
| ATR 40 | 13% | 17% | 3.6 |

## Result (282 dip trades: US500 2016-26, Germany 40 2014-26, US Tech 100 2016-26; sealed 2022-23 skipped for US500 / Germany 40)
| gauge | skipped n | skipped R/trade | kept R/trade | skip − kept (t) | total R plain → rule | max DD plain → rule |
|---|---|---|---|---|---|---|
| ATR 5 | 75 | +0.200 | +0.166 | +0.03 (0.1) | +47.7 → +32.7 | 33.2 → 20.0 |
| **ATR 10*** | **60** | **+0.197** | **+0.169** | **+0.03 (0.1)** | **+47.7 → +35.9** | **33.2 → 21.7** |
| ATR 20 | 48 | -0.007 | +0.215 | -0.22 (-0.6) | +47.7 → +48.1 | 33.2 → 18.7 |
| ATR 40 | 32 | -0.317 | +0.241 | -0.56 (-1.6) | +47.7 → +57.8 | 33.2 → 21.2 |

## Read
- **On the primary gauge, the rule does nothing per trade:** skipped dips earned the same as kept ones (+0.20 vs +0.17). Skipping them just shrinks everything: -25% total R, -35% drawdown. That's a size cut, not an edge.
- **The harm sits in the SLOW gauges:** ATR 20 / 40 "high and rising" trades lost (-0.01 / -0.32 R) while the rest earned. A slow gauge only reads "high and rising" during long stress REGIMES (weeks of elevated volatility: 2018, 2022-style), not short bursts. The fast gauge catches every short volatility burst, many of which are ordinary V-dips that pay.
- **So the danger for dip isn't "volatility is rising"; it's "we're inside a long stress regime".** That fits Ezio's "volatility is bad" and his quarter table (also a slow, regime-level read), and it explains why the 40-day synth episodes favoured ATR 10: those planted episodes were short.
- **Caution:** picking ATR 40 now, after seeing this, would be fitting (6-19 skipped trades per market, t -1.6 pooled). If pursued: lock a REGIME rule written in advance (e.g. "skip while the 40-day ATR is ≥ 1.3× its 1-year median and rising"), with a reason, and test once on fresh data (US 30 / Japan 225).

## Predictions scored (Claude)
- skipped worse than kept (pooled): ✗ on the primary gauge (+0.03); ✓ only on the slow gauges
- total R about the same: ✗ (-25%)
- drawdown smaller: ✓ (-35%)
