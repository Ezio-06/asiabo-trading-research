# Pocket pipeline plan: context-conditional signals (agreed 2026-10-09, not built yet)

**Idea (Ezio):** a signal S may predict lane L's outcome only inside a context C (e.g. ema_below_200 predicts main2 when volatile, ATR between x and y, ...). Whole-population tests average these pockets away. We never generated these multi-condition candidates; the 10-07 "kinds of market" run was a coarse, hand-labelled single-context version and came back unproven. Generalizes T18 (a signal's meaning depends on the filter in front of it).

**Status:** research track, runs alongside the why phase. Does NOT change the frozen book. Survivors become candidates for the next design cycle.

## Steps
1. **Per-trade table per lane:** every signal + every context variable known at entry (ATR band, volatility, trend states, session, weekday, cross-market states such as USD strength from EURUSD/USDJPY/gold, several markets trending at once).
2. **Discover on half the eras** (e.g. 2014-17 + 2020-21): shallow trees (depth 2-3, min ~100 trades per pocket) and/or 2-way grids. Trees find the x-y thresholds themselves. Not the T16 approach (one global score), but local pockets.
3. **Write each pocket's theory (or "none") BEFORE looking at the other half.** Including which synth perturbations it should survive and which should kill it.
4. **Confirm on the other half** (2018-19 + 2024+), then swap halves. Also check other markets.
5. **Random-market yardstick:** run the identical pipeline on random-market data. If it "confirms" about as many pockets there, the survivors are noise. Chance alone: ~1 in 20 pockets at |z|>2, ~1 in 400 at |z|>3.
6. **Luck vs theory review** (standing rules: judge each pocket individually, never by a luck count).
7. **Synth stress test on the survivors (Ezio):** does a pocket behave like a real signal (graceful fall-off) or a knife-edge artefact?
   - **Threshold nudge** on real data (shift the x-y band ±10 / 20 / 30%): real = plateau, fake = spike that dies at the first nudge.
   - **Data perturbation ladder:** identity → cosmetic → vol_up/vol_down → trend presets → dayshuffle → shuffle. Plot the pocket's edge against perturbation strength. Real = smooth, mostly monotone decline that matches its theory's predictions. Fake = cliff at cosmetic, or noise around zero throughout.
   - Express thresholds in ATR / relative terms so vol presets test the mechanism, not the units.
   - Surviving shuffle is a RED flag (non-temporal artefact: cost structure, bug, leakage).
   - Train vs validation gap: discovery-half z vs confirm-half z. A modest drop is normal; full collapse = fitted.

## Limits
- Sample size: a pocket with ~5% of a lane's trades has ~100-150 trades; at z=3 it only detects effects of roughly 0.25R+. Big pockets only.
- Split one dimension at a time where possible, and only on dimensions with a written theory, to keep cells from going to a dozen trades.

## Open question for Ezio
- Lane scope: frozen sleeves only, or also dead/raw lanes (main2, vwap, ...) in case a pocket revives one?
- Also undecided: what decision the adaptive counterfactual "twins" (coin-flip / opposite / unfiltered / drift) would drive. Dashboard-only first.
