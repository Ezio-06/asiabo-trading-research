# Regime engine: results (run 2026-10-10 15:58, 6 worlds: strength 0.15 x3, 0.25 x3, 0 failed)
Known truth: momentum / neutral / snap-back spells of 20-130 days per market, on day-shuffled real days. Leak-free dial (direction only). Synth = what is detectable IF the market works like this model.

## R1: who depends on the regime (edge/trade by true state, subtle / strong)
- **brk:** mom +0.57 / +1.05 (t 10 / 15), neutral +0.05 / +0.06, snap -0.37 / -0.58. Pure regime bet.
- **fast:** mom +0.26 / +0.39, neutral ~0, snap -0.10 / -0.19. Same mechanism, milder.
- **ins:** about 0 everywhere. Regime-blind (as in engine D1).
- **dip / dipx:** about 0 or negative in every state once the base drift is removed (mirroring). dip's real edge needs the indices' upward drift; momentum or snap-back alone does not create it.

## R2: detector scorecard (AUC momentum vs rest, subtle / strong; median lag; spells caught in their first half; false switch-ons per market-year)
| Detector | AUC | Lag (days) | Caught | False on / yr |
|---|---|---|---|---|
| **er40 (40-day straightness)** | **0.79 / 0.88** | 10-14 | 87-88% | 2-4 |
| er60 | 0.76 / 0.85 | 13-17 | 75-77% | 1.6-3 |
| er20 | 0.74 / 0.85 | 4-5 | 95-100% | 5-8 |
| follow60 (breakout follow-through) | 0.74 / 0.83 | 20 | 71% | 0.5-1 |
| tshare60 | 0.77 / 0.82 | 32-38 | 58-61% | 0.3-0.6 |
| lab edge20 / er10 | 0.60-0.70 | 1-2 | ~99% | 14-18 (too twitchy) |
| **vr40 / vr60 / vr120, ac20 / ac40 / ac60** | **0.49-0.57 (BLIND)** | | | |

So variance-ratio and autocorrelation gauges cannot read the regime at these windows. That explains why every vr120 pocket in hunt round 1 failed. Straightness reads it.

## R3: gating (the "keep it when it works, harmless when it doesn't" switch)
- **brk, er40 switch:**
  - keeps 38-39% of trades
  - edge / trade +0.13 -> **+0.32** (subtle), +0.28 -> **+0.72** (strong)
  - keeps 94-103% of the total edge; the trades turned away are about 0 (+0.01 / -0.01) = HARMLESS
  - perfect switch (the true label): +0.57 / +1.05, so er40 captures roughly 55-70% of the possible gain
- **fast, er40 / er60 switch:** +0.10 -> +0.16 and +0.18 -> +0.31-0.33, keeping 74-86% of the edge with 45-49% of the trades.
- **dip:** nothing (no edge to gate in drift-free worlds).

## R4: trend capture (brk in momentum spells)
- brk takes **37% (subtle) / 52% (strong)** of the spells' total move (in ATRs).
- First trade in the spell's direction after a median of 7-9 calendar days.
- No measurable giveback in the 4 weeks after a spell (edge +0.18 / +0.21, t about 1.5).

## R5: which hunt signals carry regime information (AUC at brk entries)
- **Carry it:** trendy (er20) 0.73 / 0.84, trend60_with 0.68 / 0.82, dist200_with 0.65 / 0.76; then form20, n_trending, pos20 0.6-0.66.
- **Near blind:** vr120 (0.54-0.57), ac60, vol, atrchg, gap, prev_range, spread.

## Next (proposed)
- **ONE pre-registered real-data check of the er40 switch for brk and fast**, threshold and predictions fixed BEFORE running.
- er40 was never used in any selection on real data; it was chosen in synth, so all 4 real eras are a fair test.
- Real decides: synth only says it is detectable IF momentum regimes look like the model.
