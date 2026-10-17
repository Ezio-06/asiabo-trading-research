# Youngling batch 1: pre-registered rules and predictions (written 2026-10-12 BEFORE any run)

Script: asiabo_young.py (CLI module `young1`). Real data, shadow only, nothing tuned. Sealed years / Japan 225 never read.

## Changes made after the noise test, BEFORE any real run (2026-10-12 ~14:10)
- **#27 / #28 exits** now use the spread LEVEL since the trigger. "z back to 0" let old days dropping out of the rolling 10-day window fake a "gap closed" with no price move at all (on noise, 62% of #27 trades hit "target" that way).
  - target = the whole gap G closed: the spread back to its level 10 days before the trigger
  - stop = the gap widened by another 0.75 G (the same distance as z 2 → 3.5)
  - R is in units of 0.75 G
- **Pair legs** execute at the next common FX-day OPEN (both markets), not at US500's session open.
- **Yardstick cousin** = the v8 realistic world (real8 seed 3, passes the gate) instead of a plain dayshuffle, since v8 is now the realistic synth.

## Common
- **Signals** use only completed FX days (up to close j-1). **Entry** (#31, #19) at the open of day j's session-open bar (the lab's session clock per market; the first bar of the day if that bar is missing).
- **Trades (#31, #19)** go through the lab's own walker (p_trade / p_walk):
  - real costs (commission + recorded spread + swap)
  - the stop is checked before the target inside a bar
  - each trade has a mirror → EDGE = net R − the coin-flip average (cost-free direction value)
- **One exit per outcome** = a state label (stop / target / time). Read off the gross R: ≤ -0.95 = stop, at the target R = target, otherwise time.
- **Report per lane:**
  - n, win %, exit-label mix, net R/trade, EDGE with t clustered by market × month
  - per market, OLD (2014-19) vs NEW (2020-26) halves
  - monthly correlation of net R with the core book (fast, dip)
- **Yardstick:** the same file on fake random walks (noise ranges printed), plus the real8 cousin.
- **One position** per lane / market / direction at a time.

## #31 Mirror dip (Ezio): short the START of a pullback in a stretched trend
- **Setup at close j-1:** peak stretch of the last 5 closes from their own 20-day average ≥ 2.5 N (N = 20-day ATR at day j), on the up side (mirror for down). er20 ≥ 0.30 in the same direction.
- **Trigger:** close j-1 is the FIRST close below the low of the 3 days before it (mirror: above the high), as in probe M4.
- **Trade:** against the stretch.
  - stop = the 5-day extreme ± 1.5 N
  - target = the 20-day average at close j-1 (skip if price is already past it)
  - time = the close 5 trading days after entry (entry day included)
- **Markets:** all 6. Ezio's markets (EURUSD, XAUUSD, XTIUSD, USDJPY) are flagged.
- **Labels:** stop = the trend continued, target = the correction came, time = chop.

## #27 / #28 US500 vs GERMANY40 (exact flips on the same trigger)
- **Spread move:** d10 = 10-day log return of US500 − β × 10-day log return of GERMANY40. β = OLS of daily returns over the last 120 common days. z = d10 / sd(d10, last 250 common days).
- **Trigger:** |z| ≥ 2.0 at close j-1 (no trade while one is open).
- **#27 gap closes:** short the leader, long the laggard (β-weighted). Exits on the spread level (see Changes), checked on daily closes, executed at the next open. Time = 10 days.
- **#28 relative momentum** = the exact mirror on the same trigger.
- **Costs:** both legs at each market's round-trip cost_bp. No swap on the pair.
- **Data:** US500 exists 2020-21 + 2024-26 only (~4.75 years), so NEW half only. Thin.
- **Labels:** #27 target = coupling, #27 stop = decoupling, time = chop.

## #19 Squeeze breakout
- **Squeeze at close k:** 20-day Bollinger bandwidth (4σ / SMA20) is the lowest of the last 120 days.
- **Trigger:** close j-1 outside the 20-day 2σ band (above = long, below = short), with a squeeze on any of the 5 closes before it.
- **Trade:** in the break direction.
  - stop = the 20-day average at close j-1 (a false break)
  - target = entry ± 3 N (the release)
  - time = the close 15 trading days after entry
- **Markets:** all 6.
- **Labels:** target = a real release, stop = a false break, time = no follow-through.

## Predictions (unchanged)
**Ezio (2026-10-11 / 12):**
- #31: a small win rate, because chop is most likely and hits most stops. Best on dip's weakest markets.
- #27 / #28: "usually catch up": #27 beats #28.
- #19: chosen over #12 (a panic peak can't be predicted, so #12 would enter too early).

**Claude:**
- #31: win rate ~35-45%, net < 0 after costs. EDGE ≤ 0 overall, a small positive EDGE only in XTIUSD; stop-outs the most common label in the indices.
- #27 / #28: #27 EDGE > 0 but t < 2; time exits the most common label.
- #19: EDGE ≈ 0, inside the yardstick; false-break stops the most common label. A small positive EDGE in XAUUSD / XTIUSD at best.
- **Correlation:** #31 negative with dip on the indices; #19 positive with fast.
