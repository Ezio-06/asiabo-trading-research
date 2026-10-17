# Probe study results (run 2026-10-11 20:36, real + dayshuffle s1 cousin, 26 min; definitions + yardstick in probe_plan.md)

Identity IDENTICAL on both runs (real book 4814 trades: brk 1740, fast 1679, ins 1256, dip 139).
Reading rule: real vs the COUSIN (same days and drift, no multi-day order) vs the YARDSTICK (3 random walks).

## Headline: on real daily data, trends are SHORTER and LESS readable than in the market's own day-shuffled cousin
| Measure | Real | Dayshuffle cousin | Random walk |
|---|---|---|---|
| Days inside a hindsight 41-close straight stretch (er >= 0.30) | **14.7%** | 22.8% | 14-15% |
| er40 spells lasting 20+ days | **7.0%** | 13.7% | ~5.5% |
| er20 precision vs that truth | **28.7%** | 41.2% | 28-29% |
| er40 precision | **24.5%** | 40.5% | 25-28% |
| Mid-spell (age 10+) move over the next 20 days | **-0.03 N** (t -0.1) | +0.98 N (t +2.9) | ~0 |

- Shuffling the real days into random order (which keeps drift and each day's move) creates MORE and LONGER straight runs than the real order has. So at the multi-week scale, the real order is slightly mean-reverting relative to its own shuffle. It is no more trend-readable than pure noise.
- This fits:
  - T5 / T22 (streaks reverse)
  - brk failing on real data while it wins in momentum synth
  - "the synth worlds are too sharp" (Phase 2's premise)
- One cousin seed only. The direction is consistent across M1, M2 and M5.
- **Volatility IS readable** (the known clustering): atr10 precision 78% (cousin 56%), catches 96% of high-vol spells, median lag 8 days, 1.3 false switch-ons per market-year. atr5: 70%, lag 6 d.

## Section by section, predictions scored
**M1 trend end (60 real spells of 10+ days):**
- At h 10: continue 30% / chop 53% / reverse 17%, mean move +0.62 N (t +2.2). The cousin shows 29 / 47 / 23%. Noise shows 16-25 / 51-62 / 19-25%.
- Chop is the most common outcome: Ezio right, Claude right.
- Reverse < continue: Ezio's order of those two is wrong, and Claude's "equal" is too.
- All of it is near the cousin, so drift explains it. **The end of an er40 spell carries no reversal information.** That is evidence against #30 (trend-end lane) and against the reversal leg of #31.
- No blow-off endings among real 10+ day spells (0 of 60), so blow-off vs fade is untestable.
- END minus MID (h 20) +1.26 t +2.1 sits inside the noise range (±2.4) → not established.

**M2 hazard:**
- Ratio (21-40) / (6-20): real 0.91, band 0.67-1.28. Cousin 0.70 (0.48-0.98); noise 0.65-0.82.
- Real is above the cousin and every noise seed, so the direction is Ezio's (ageing).
- It is below the 1.1 bar set beforehand, and the band includes 0.67 → **not shown**.
- Thin: only 8 spells ended after day 30.
- Claude's "no rise beyond the cousin": also not clean (0.91 > 0.70).
- Verdict: undecided, leaning toward ageing. #31's age condition stays OPEN. Per-market values (US500 2.04, XAUUSD 1.63) sit inside the per-market noise range (0.11-1.98).

**M3 failed shadow:**
- brk failures: reverse probe minus control +0.05 R (t +1.1); fast +0.03 (t +0.6).
- The cousin is at least as high (brk +0.07, fast +0.10 t +2.2).
- brk 1-4h failures: +0.21 (t +2.2), inside noise (±2.6).
- Claude's "fastest failures better" is wrong (≤1h: -0.04 / -0.03).
- **Idea #3 (failed-shadow reverse): nothing.**

**M4 correction (stretch 2.5+ N then the first crack):**
- No clear correction in the mirror-dip markets over 3 days:
  - XAUUSD -0.05
  - EURUSD +0.19 (t 1.1)
  - USDJPY +0.09
  - XTIUSD +0.02
- The cousin shows corrections of similar or larger size, so the crack adds nothing beyond a shuffled world.
- Lead only: **XTIUSD 5 days +0.60 N (t +2.9)**, with the same sign at 1 / 3 days (+0.13 / +0.02). It is above the noise maximum (2.1), but it is one cell of ~54 and the cousin shows -0.25.
- Indices: US500 keeps going (P(3d correction) 28%) = drift. The US500 + er20 cell (t -6.2) has n = 8: a tiny-sample artifact.
- Ezio's M4 prediction: not shown. Claude's (XAUUSD / XTIUSD / EURUSD t ~2): not shown either (only XTIUSD at 5 days).

**M5 seeing speed:**
- Every trend detector (SMA / EMA 5-200, er10-60) is at noise precision on real data. Their "lags" mean nothing when they do not beat noise. Claude's "er20 fastest with tolerable false alarms" was meaningless as worded.
- ATR detectors work (above).

**M6 serial dependence:**
- P(L|L) is BELOW P(L) for all three parts (contrarian side):
  - fast 59.6 vs 60.9%
  - dip 21.6 vs 26.6%
  - brk 74.0 vs 74.8%
- Shuffle percentiles 6.4 / 11.6 / 8.2: not beyond the 2.5 bar.
- fast: E[net | previous loss] +0.181 vs E[net | previous win] -0.010. The skip line sits at the 1.8th percentile of order shuffles, i.e. skipping after a loss would HURT. The block shuffle sits at 54.6%, so the effect lives within months (short range).
- The cousin shows the opposite (90.6%).
- Lead: **"a fast trade after a fast loss does better."** Consistent with T5 / T22. Not established by the pre-set rule (it needs both shuffles).
- Claude's prediction ("inside the band everywhere") holds by the rule.

## What this changes
1. **Phase 2 (synth realism) is now the clear next step, with numbers for the gate.** The v7 synth must match:
   - real hindsight-trend share ~15% (not the cousin's 23% or the regime synth's more)
   - share of er40 spells 20+ days ~7%
   - hazard ratio ~0.9
   - er20 / er40 precision ~noise
   - Momentum lanes tested in worlds sharper than this will keep looking too good.
2. **Youngling priorities shift** (Ezio decides):
   - DOWN: #30 trend-end, #3 failed-shadow reverse, #31's reversal thesis (no correction after a crack beyond the cousin, except the XTIUSD 5-day lead).
   - UP: volatility-state ideas, because vol is the readable state. #12 vol-target re-leverage, #19 squeeze breakout, #4 blow-off fade (needs a vol spike), and vol as a sizing / gating input for fast / dip.
   - The M6 fast-after-loss lead fits #32 shadow sensors: test it there with a half split.
3. **#31 mirror dip:** still worth its Phase 3 screen as pre-registered (its exits label continue / chop / correct), but expect Ezio's "small win rate". The probe gives no reason to expect an edge outside XTIUSD.

## Known cosmetic bug
- cmean prints absurd t values when a cell has 2-3 clusters with no spread (M3 fast ">1d", n = 3). To fix: suppress t below ~10 clusters. No effect on any verdict above.
