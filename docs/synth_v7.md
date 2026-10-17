# make_synth v7: the realistic world + realism gate (Phase 2, 2026-10-11; committed, md5 verified)

**The pattern being fixed (Ezio):** the synth regime worlds were sharper and longer than real, so momentum lanes looked too good. Probe (probe_results.md): real has FEWER and SHORTER straight runs than even its own dayshuffle cousin.

## Model (`--soft auto --rev1 auto`, preset `real7`)
- **Base:** dayshuffle (whole days, same weekday, same era).
- **Spells:** mean length 5 trading days (geometric, minimum 3). Each spell has its own signed strength d ~ Normal(-0.09, 0.12):
  - d > 0 = momentum, d < 0 = snap-back
  - about 23% of spells are momentum; most are mild
- **Nudge:** a day whose move beyond the drift goes against the de-drifted 40-day trend is mirrored with probability 2d (momentum spell); one going with it, with probability 2|d| (snap-back spell). Neutral days are untouched.
- **Drift-preserving mirror:** around the era's drift line. Close → 2μ − r; each bar x → 2μf − x. The indices keep their drift (US500 +19%/yr vs real +18%).
- **Shock days** (move or gap > 5 × the era's median |daily move|) keep their real direction.
- **No v6 gap closing.** It deleted oil's contract-roll gaps.
- **Next-day reversal per market** (normal days only), calibrated to the real lag-1 autocorrelation: US500 0.448, GERMANY40 0.237, USDJPY 0.073, EURUSD 0.034, XAUUSD / XTIUSD 0.
- **Spell table:** state mom / snap / none (|d| < 0.02), a = d.

## How it was calibrated
1. Probe definitions reproduced on real daily bars (truth 14.7%, er20 28.7%, er40 24.5%, spells 20+ 7.2%, hazard 0.90, VR20 0.90, ac1 -0.058).
2. Grid search with a fast daily simulator. Lookback 40 beat 10 / 20.
3. Real-data M1 tests in the cloud (Ezio's cache) found three problems, each fixed:
   - flipping the 2020 oil crash days (XTIUSD reached 600,000) → shock-day rule
   - v6 gap closing → removed
   - a home-made daily shuffle ~0.06 trendier in er40 than the generator's → recalibrated on 6 REAL M1 dayshuffle bases × 2 draws, checked on 3 held-out bases (score 3.10 / 3.03)
4. Off-switch: identity, dayshuffle, v6 regime + aging, and shuffle + persist + vol produce identical bars / gaps / regime / meta with the new file.

## Realism gate (`make_synth.py gate <db>`; runs automatically after any v7 gen; exit code 3 on FAIL)
- **Tolerances** (2 × the seed spread; revised once when the shock rule was added):
  - truth ±0.040, er20 ±0.070, er40 ±0.060, ac1 ±0.021 (STRONG)
  - spells 20+ ±0.030, hazard ±0.37, mid20 ±0.90, VR20 ±0.135
- **Rule:** FAIL if any strong statistic is out, or 2+ weak ones.
- **Power:** 22 of 27 v7 worlds pass (81%); 0 of 9 plain dayshuffle cousins pass.
- **Residual bias:** v7 er40 precision averages 0.270 vs real 0.245. The gate is a FILTER: failing seeds are discarded. Real-data seeds 1-2 fail (trendier bases), seed 3 passes.

## Probe on real7 seed 3 vs real vs cousin
| | Real | v7 s3 | Cousin |
|---|---|---|---|
| Days in a hindsight trend | 14.7% | 12.7% | 22.8% |
| er20 / er40 precision | 28.7 / 24.5% | 24.5 / 28.4% | 41.2 / 40.5% |
| er40 spells 20+ days | 7.0% | 6.4% | 13.7% |
| Hazard ratio | 0.91 | 0.63 | 0.70 |
| **atr10 precision (vol clustering)** | **77.9%** | **56.7%** | 56.2% |
| **dip book trades** | **139** | **53** | 96 |

## Known gaps (the next fix, v8)
1. **No volatility clustering.** It is a dayshuffle base, so calm and wild days mix at random. Volatility is THE readable real state (probe M5), so any vol-gated lane must not be judged on v7.
2. **The index next-day reversal sits in the wrong place.** In real data it is concentrated in crises (US500 2020: -0.31, 2025: -0.19). v7 spreads it uniformly over normal days, which suppresses calm-market down-streaks: dip's trigger (53 trades vs 139). **Do NOT judge dip on v7.**
3. **Proposal v8:** a base that keeps volatility clusters (e.g. days drawn from the same volatility state, or week blocks), with the reversal tied to volatility. Then add atr10 precision and dip-trigger frequency to the gate.

**Use now:** v7 is the realistic world for TREND / momentum lanes (brk, fast, #27 / #28 ...) and the ideal / nightmare dial worlds of Phase 5 should be built on it. CLI: `synth7_check` (real7 s3 + gate + probe on it, ~15 min), `synth7_gate`.
