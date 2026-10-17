# Young engine results (2026-10-12)

Run: asiabo_young_engine.py (md5 31305b49...). REAL + real8_s1..s4 in the cloud; real8_s5/s6 + momentum/neutral x2 on Ezio's PC (16:20-17:18, ~9.5 min per world). Report: reports\young_engine_20261012_171844\young_engine.txt

## Check A: real vs 6 realistic v8 worlds (EDGE per trade)
- #31 mirror dip: REAL +0.062 (t1.6, n93). Fakes: +0.061 -0.029 -0.057 +0.062 +0.088 +0.044. 2 of 6 fakes at or above real, so the real result sits in the middle of the fakes.
- #31 long-stretch: REAL +0.138 (t2.3, n35). Fakes: +0.070 +0.019 +0.030 +0.084 +0.092 +0.061. Real is above all 6, but every fake is positive too (mean ~+0.06). The gap is ~+0.08 against a standard error of ~0.06, so it is not significant.
- #31 short-stretch: REAL +0.015, 4 of 6 fakes at or above.
- #19 squeeze: REAL -0.139. 5 of 6 fakes at or above (one fake -0.915 blowup).
- #27 gap closes: n=6, unreadable.
- Caveat: the v8 fakes are built from real days and include the snap-back dial, so they carry the real market's own snap. "Fakes at or above real" asks whether real holds anything extra beyond v8; it is not a pure noise test.

## Check B: cause test (momentum -> neutral -> snap-back, 2 seeds pooled)
- #31: -0.108 (t-3.5) -> -0.041 -> +0.015. The slope runs in the right direction (difference ~0.12, roughly t3). The lane does respond to the state it assumes, but the slope is about the size of the noise yardstick (+-3.5), so it is suggestive, not proof. Even the snap-back world gives only +0.015, less than real's +0.062.
- #31 long-stretch: -0.070 -> -0.057 -> +0.048. Same direction.
- #19: -0.037 -> -0.300 -> -0.060. No slope. It loses even in the momentum world built for it, so the lane design itself is broken, not just the market.
- #27: flat noise.

## Check C: placebos on real data
- #31: no-trigger (enter on the stretch without waiting for the crack) -0.000 on n740. Delay 1 day: +0.066, the same as real. Without the best market-year (EURUSD 2020): +0.049 (t1.3).
  - Read: waiting for a crack picks better situations (+0.06 vs 0, t~1.6, weak), but the exact crack day does not matter. Whatever edge exists is a slow multi-day drift, not a sharp turn.
- #19: no-break placebo +0.127 (n262, t0.7) beats the real lane. Delay 1 day: -0.054, better than real. Without the best year: -0.171.
  - Read: the break moment itself is the losing part, because entering at the break buys the top of the burst. This supports Ezio's #33 causal-breakout reasoning.

## Prediction scorecard
- Claude:
  - A: #31 above 5/6 fakes. WRONG (2/6; long-stretch only, 6/6).
  - A: #19 below 5/6. RIGHT.
  - B: #31 rises. RIGHT.
  - B: #19 falls. WRONG (no slope, loses everywhere).
  - C: no-trigger about as good as #31. WRONG.
  - C: delay costs about half. WRONG (costs nothing).
  - C: best-year removal barely survives. RIGHT.
- Ezio:
  - A: better on real. Whole lane NO; long-stretch yes.
  - B: no dial expectation.
  - C: first crack not a consistent signal. PARTLY. The trigger adds a weak edge, and its exact day doesn't matter.

## Verdicts
- #31: stays a youngling. The mechanism shows (correct slope; the trigger beats no-trigger), but real data shows nothing beyond what v8's built-in snap gives. The fresh US500 2015-19 exam is the deciding test. Do not tune on the 35 long-stretch trades.
- #19: retire as built. The break entry is an anti-signal. It feeds #33 causal breakout (batch 2).
- #27/#28: still unreadable (too few trades).
