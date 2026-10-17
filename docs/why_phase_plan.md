# The "why" phase: pre-registered plan (written 2026-10-09, before any of these tests ran)

**Applies to:** the frozen book (frozen_design_v1). This phase may only:
- **REMOVE** a part, or
- **SWAP** a fixed number for a DERIVED rule. A swap must:
  - come from the mechanism and be written here before testing,
  - have no more free choices than the number it replaces,
  - reproduce roughly the old value where it was chosen.

New patterns go on the next-cycle list. Japan 225 and 2022-23 stay untouched.

## W1. Plateau test (is each number a peak or a plateau?)
Shift each frozen number by about ±25%, one at a time, everything else frozen:

| Number | Shifted to |
|---|---|
| edge20 window (20) | 15 / 25 |
| edge20 threshold (0.85) | 0.80 / 0.90 |
| er10 window (10) | 8 / 12 |
| er10 straightness (0.4) | 0.3 / 0.5 |
| er10 move (2 ATR) | 1.5 / 2.5 |
| chandelier length (5 days) | 4 / 6 |
| chandelier distance (1N) | 0.75 / 1.25 |
| ORB window (30 min) | 22 / 38 |
| inside-day stop (middle, 0.5) | 0.4 / 0.6 |
| rsi2 entry level | ±25% |
| dip3 count (3) | 2 / 4 |
| 200-day average | 150 / 250 |

- **Prediction:** real mechanisms degrade smoothly; the neighbours keep at least half the edge in most eras.
- **KILL** a part if its frozen value is an isolated peak: both neighbours lose more than half the edge in 3 of 4 eras.

## W2. Dose-response (does "more of the cause" give more of the effect?)
- **brk / fast:** edge by fine bins of position in the 20-day range and of er10 straightness. Predict a monotonic rise toward the edge and the straighter trends.
- **dip:** bounce by dip depth (down-day count, RSI level). Predict deeper dips bounce more, until a crash regime.
- **ins:** edge by how narrow the inside day is relative to ATR. Predict narrower is better (compression, Crabel).
- **Reading:** a flat or non-monotonic response means the threshold is not tracking the cause. That is not a kill on its own, but it lowers confidence.

## W3. Where the money comes from
- **Concentration:** share of each part's R from its best 5% of trades, its best month and its best market-year. Recompute net without the best market-year.
- **KILL** a part if, without its best market-year, it is net ≤ 0 in 3 of 4 eras (one lucky stretch is not an edge).
- **Trade anatomy (brk, fast):** how much of a winner's final R exists after 1h / 4h / 1 day / 3 days, and the median MFE / MAE path.
  - Predict breakout winners show early follow-through (positive by hour 4).
  - If winners only appear on day 3-5, the edge is macro trend riding, not breakout follow-through. T1 would need rewriting.

## W4. Placebos (the edge must fade the way the mechanism says)
- **Delayed entry** (+15 min, +1h, +1 day, same exits).
  - brk: decays slowly over hours (multi-day momentum).
  - fast / ins: decays fast (intraday follow-through).
  - dip: barely changes over 1 day (a multi-day snap-back).
- **Random entry day with the same exits and filters:** the edge must vanish.

## W5. Cost stress
- Spreads ×1.5 and ×2.
- **Prediction:** fast and ins suffer most (short holds); brk and dip barely.
- **FLAG** (not kill): a part that turns net negative at ×1.5 in 3 of 4 eras. It goes live only if real spreads are confirmed at or below the tested level.

## Derived-rule candidates (written now, tested in W1's neighbourhood)
- **D1.** Range lookback = 4 × the hold (20 days = 4 × 5-day chandelier): the room a trend needs relative to how long we sit in it.
- **D2.** er10's move threshold in units of the window's own expected random range (2 ATR over 10 days ≈ 0.63 × √10 ATR). That makes it a z-score of the move against a random walk, not a fixed 2.
- **D3.** Inside-day stop at the middle = the compression's own centre, already structural (no number to derive).

## Order
W5 and W3 first (cheap: reuse the frozen run), then W1, W2, W4 (each needs re-runs of the lanes).
