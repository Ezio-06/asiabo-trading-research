# Youngling batch 1: results (2026-10-12 ~14:00; rules + predictions in young_batch1_spec.md)

- **Real data** = make_synth identity from Ezio's cache, run in the cloud. It reproduces the real core book exactly (fast 1679, dip 139).
- **Yardsticks:** 2 fake random walks + the v8 realistic cousin (real8 s3).
- **PC module `young1`** (real + real8 s3 cousin, ~20 min) is committed for a canonical PC copy.

## Summary (EDGE = net minus the coin-flip mirror, R/trade, t clustered by market × month)
| Lane | Real | Noise A | Noise B | v8 cousin | Verdict |
|---|---|---|---|---|---|
| #31 mirror dip | +0.062 (t +1.6), n 93 | +0.006 | -0.106 (t -3.5) | -0.057 | weak lead |
| #19 squeeze breakout | -0.139 (t -1.2), n 93 | +0.111 | +0.048 | +0.044 | dead as a trader |
| #27 gap closes | +0.41 (t +1.2), **n 6** | +0.073 | -0.091 | -0.123 (n 10) | unreadable |

The noise reached t -3.5 on a whole lane (5-15 day holds overlap a lot), so the bar is |t| ~4+, the same sign in both halves, outside the noise and the cousin. Nothing clears it.

## #31 mirror dip (Ezio)
- **Real:**
  - 93 trades, win 59%, net +0.039, EDGE +0.062 (t 1.6)
  - OLD +0.041 / NEW +0.083: positive in both halves
  - positive EDGE in all four of Ezio's markets (EURUSD +0.10, USDJPY +0.06, XTIUSD +0.04, XAUUSD +0.04; all t < 1.1); US500 -0.07 (n 6); GERMANY40 +0.12 (n 15)
- **Labels:** target 45%, time 53%, stop 2%. The 1.5 N stop beyond the 5-day extreme almost never fires in 5 days, so "trend continued" is NOT measured by this lane as built. The label is a near-dead channel.
- **Variants:**
  - "long-stretch" (buy the first bounce after a stretched DOWN move): EDGE +0.138 (t 2.3, n 35); cousin +0.03, noise +0.02 / -0.07
  - "short-stretch": +0.015
- **Correlation:** monthly net vs fast -0.12, vs dip -0.07 (diversifying, weakly).
- **Predictions:**
  - Ezio "small win rate": NO (59%), but only because the stop is far. "Best on dip's weaker markets": roughly yes.
  - Claude "net < 0, EDGE ≤ 0, only XTIUSD positive": NO.
- **Read:** the most consistent lead of the batch (both halves, all of Ezio's markets, above both noise seeds and the cousin), but small and not established.

## #19 squeeze breakout
- **Real:** 93 trades, win 34%, net -0.170, EDGE -0.139 (t -1.2); OLD -0.295 (t -1.7) / NEW +0.013. GERMANY40 -0.462 (t -2.0, 71% stopped), USDJPY -0.33, EURUSD +0.18 (n 19).
- **Labels:** stop (false break) 54% = the most common outcome, as Claude predicted. The yardsticks were all mildly positive (+0.04..+0.11), so real is BELOW them: real breaks out of quiet ranges fail more than chance.
- **Correlation:** +0.15 with fast (as Claude predicted). Same family: breakout / continuation.
- **Read:** fits the probe (trends are not readable on real data). Dead as a trader. Possibly useful as a #32 SENSOR: a cluster of false-break stops = a range regime. Its mirror (fading the break) is NOT implied, because the cousin / noise sit above zero.

## #27 / #28 US500 vs GERMANY40
- Only 6 real trades: US500 data starts 2020 and the rule needs 250 + 120 days of warm-up. Noise had ~50 trades and still reached t ±5 on a 14-trade half.
- **Nothing can be read.** Ezio's "#27 beats #28" can't be scored.
- **Needs:** a longer US500 history (does the broker export pre-2020 bars?), or a pair with long history on both sides.

## Design flaw caught before the real run
- The original #27 exit (z back to 0) on a rolling 10-day window let old days dropping out fake a "gap closed" (62% "targets" on noise). Replaced by spread-level exits before any real run (see the spec).

## Next (Ezio decides)
1. **#31:** the "long-stretch" side is the lead. Do NOT tune on it (that would be fitting the 35 trades seen). Instead:
   - a pre-registered follow-up with a near stop (so all three labels fire), on the v8 seeds and on new data
   - or straight to the #32 sensor test as a probe
2. **#19:** retire as a trader; keep as a sensor candidate.
3. **#27 / #28:** get US500 history before 2020, or drop.
4. **Batch 2 candidates:** volatility-state ideas (vol is the readable state); a #31 / dip pairing as a sensor.
