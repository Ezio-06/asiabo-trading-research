# Hunt round 1: discovered pockets + theories (PRE-REGISTERED 2026-10-10 15:05, before confirm)

Discovery half: 2014-17 + 2020-21. Lock hash a0bb85ee3d9c.
- Real: 44 pockets. Chance (20 shifted hunts): median 27, 90th percentile 32.
- Confirmed by chance on the check half: median 0, 90th percentile 2, max 2.
- Check half (2018-19 + 2024+) NOT read when these were written.

## Pre-registered predictions
- **Expected CONFIRMED:**
  - ins-07 (narrow inside day)
  - dipx-03 (dip entered after a gap down / no gap)
- **Expected to hold (same sign):**
  - brk-02 (against the 200-day trend in a snap-back regime)
  - ins-09 and dipx-06 (T5 hot form)
  - dipx-02 / 04 / 08 (the gap mechanism)
  - dipx-07 / 12 (no real dip)
  - dipx-11 (deeper dip)
  - ins-02 / 04 / 06 / 12 (range regime), ins-10, the USDJPY pockets
- **Expected FAILED or WEAK:** the usd_up proxies, the one-stretch pockets, and the 'NONE' pockets.

| id | pocket (discovery) | diff / t | flags | theory |
|---|---|---|---|---|
| brk-01 | vr120 mid third (0.864 .. 1.02)  AND  form20 mid third (-7.5 .. 3.67) | -0.683 / -3.5 | - | NONE. Middle third x middle third with no mechanism (form20 'mid' = neither hot nor cold); 58% USDJPY. Expect chance -> FAILED/WEAK. |
| brk-02 | vr120 low third (<= 0.864)  AND  dist200_with < 0 | -0.793 / -2.8 | - | brk is a momentum bet (engine D1, t +6.6). A breakout AGAINST the 200-day trend (84% shorts) inside a snap-back regime has both forces against it. Predict holds (bad). |
| brk-03 | vr120 low third (<= 0.864)  AND  prev_range high third (> 1.23) | -0.561 / -2.8 | disguise? (risk_on) | Snap-back regime + a big previous day: the breakout chases a move that is already stretched and tends to revert (exhaustion). Disguise flag (risk_on keeps 46%), so medium confidence. Predict holds weakly (bad). |
| brk-04 | vr120 high third (> 1.02)  AND  usd_up = 1 | +0.707 / +2.8 | - | Momentum regime half is causal (D1); usd_up is most likely a proxy for the 2014 dollar rally (USDJPY 2014 = 50%, flagged ONE STRETCH). Predict same sign but weak; the usd_up part has no mechanism. |
| brk-05 | day_move_with bottom 10% (<= -0.452) | -0.499 / -2.7 | disguise? (risk_on) | Entering a breakout after a big move AGAINST it earlier that day = an intraday reversal / whipsaw day. Effect lives only in risk-off days (risk_on=1 stratum ~0, disguise flag). Low confidence; predict WEAK. |
| brk-06 | usd_up = 1 | +0.390 / +2.6 | - | NONE as a mechanism: usd_up is a period proxy (dollar trend 2014-15; brk 68% long when the dollar rises). Mirror of brk-07. Predict WEAK/FAILED. |
| brk-07 | usd_up = 0 | -0.390 / -2.6 | - | Mirror of brk-06 (same split, other side). NONE: period proxy. Predict WEAK/FAILED. |
| brk-08 | vr120 >= 1  AND  vol high third (> 0.97) | +0.408 / +2.5 | disguise? (risk_on) | Momentum regime (D1) + volatility high vs its own year = trends are moving with size: brk's best season (T1/T4). Disguise flag (risk_on 48%) and USDJPY 2014 = 39%. Predict same sign, moderate. |
| ins-01 | vr120 >= 1  AND  prev_range mid third (0.51 .. 0.726) | -0.491 / -3.8 | - | NONE. Inside day of middle width in a momentum regime; the engine found ins slightly BETTER with momentum, so no theory points this way. Predict FAILED/WEAK. |
| ins-02 | trendy low third (<= 0.116) | +0.469 / +3.7 | disguise? (risk_on) | Range regime: when the 20-day path is not straight (no trend), the break of a compressed inside day is a fresh impulse rather than noise inside a trend. Disguise flag (works only in risk-off: risk_on keeps 7%). Predict same sign, low-moderate. |
| ins-03 | vr120 mid third (0.845 .. 0.991)  AND  market = USDJPY | +0.551 / +3.7 | - | USDJPY is where ins works (T14: USDJPY +48R); vr120 middle adds nothing. Select-only. Mechanism guess: yen compression breaks at session handovers. Predict holds via the market part. |
| ins-04 | vr120 < 1  AND  trendy low third (<= 0.116) | +0.536 / +3.6 | disguise? (risk_on) | Same family as ins-02 (no trend, non-persistent regime -> compression breaks are fresh). Disguise flag (risk_on 30%). Predict same sign, moderate. |
| ins-05 | vr120 < 1  AND  market = USDJPY | +0.410 / +3.4 | - | Same as ins-03/ins-11: the USDJPY effect. Predict holds via the market part. |
| ins-06 | vr120 mid third (0.845 .. 0.991)  AND  trendy low third (<= 0.116) | +0.713 / +3.3 | disguise? (risk_on) | Same family as ins-02 (range regime). Disguise flag (risk_on 49%). Predict same sign. |
| ins-07 | vr120 < 1  AND  risk_size low third (<= 0.271) | +0.524 / +3.1 | - | COMPRESSION WIDTH in disguise: risk_size low = the stop at the middle of a NARROW inside day, i.e. a narrow inside day (why-phase W2: narrow inside days +0.61, t 3.7). Strongest theory in the ins list. Predict CONFIRMED. |
| ins-08 | vr120 < 1  AND  market = GERMANY40 | -0.479 / -3.1 | disguise? (risk_on), one stretch (GERMANY40 2017) | NONE: GERMANY40 2017 = 73% (ONE STRETCH) and risk_on leaves 10% (disguise). Predict FAILED/WEAK. |
| ins-09 | vr120 low third (<= 0.845)  AND  form20 >= 0 | -0.357 / -3.0 | - | T5 (hot form -> worse trades), found robust for ins in synth batch 1 (form20). Predict holds (bad). |
| ins-10 | vr120 low third (<= 0.845)  AND  risk_size mid third (0.271 .. 0.389) | -0.408 / -3.0 | - | Complement-side of ins-07: a WIDER inside day = less compression -> weaker break. Predict same sign, moderate. |
| ins-11 | market = USDJPY | +0.357 / +3.0 | - | T14's market finding: ins works on USDJPY. Select-only (market list = hindsight risk). Predict same sign. |
| ins-12 | vr120 mid third (0.845 .. 0.991)  AND  n_trending low third (<= 0) | +0.511 / +2.9 | disguise? (risk_on) | Range regime across markets (no book market trending) = same family as ins-02. Disguise flag (risk_on 49%). Predict same sign, moderate. |
| fast-01 | vr120 high third (> 1.06)  AND  ac60 mid third (-0.057 .. 0.066) | +0.459 / +3.3 | - | Momentum regime half is causal (D1, t +6.8 for fast); ac60 middle adds nothing. 95% from 2014-17, USDJPY 2014 = 49%. Predict same sign but WEAK. |
| fast-02 | usd_up = 0 | -0.342 / -3.2 | - | NONE: usd_up is a period proxy (fast is 69% long when the dollar rises). Mirror of fast-03. Predict WEAK/FAILED. |
| fast-03 | usd_up = 1 | +0.342 / +3.2 | - | Mirror of fast-02. NONE: period proxy. Predict WEAK/FAILED. |
| fast-04 | vr120 >= 1  AND  usd_up = 1 | +0.430 / +3.1 | disguise? (risk_on) | Momentum regime half causal (D1); usd_up half a proxy. Disguise flag (risk_on 44%). Predict same sign, weak. |
| fast-05 | vr120 >= 1  AND  n_trending low third (<= 1) | +0.398 / +2.8 | disguise? (risk_on) | Momentum in the traded market while few others trend: no mechanism for the cross-market part, and controlling for risk_on REVERSES it (-88%). NONE. Predict FAILED/WEAK. |
| fast-06 | mv10_with bottom 10% (<= 1.46) | +0.367 / +2.7 | disguise? (risk_on) | Fresh trends: the 10-day move is small (still positive), so the filter-agreed breakout is early in the trend with room to run, not extended. Disguise flag (risk_on 25%). Low-moderate. Predict same sign. |
| fast-07 | vr120 high third (> 1.06)  AND  usd_up = 1 | +0.476 / +2.7 | - | Same as fast-04 (momentum causal, usd_up proxy). USDJPY 2014 = 39%. Predict same sign, weak. |
| fast-08 | vr120 >= 1  AND  dir = short | +0.499 / +2.7 | disguise? (risk_on) | Momentum regime (causal) + shorts: mostly the 2014-15 gold bear (T9 macro direction). Controlling for risk_on reverses it (-42%). Low. Predict WEAK. |
| fast-09 | vr120 high third (> 1.06)  AND  market = USDJPY | +0.566 / +2.6 | disguise? (gap_with), one stretch (USDJPY 2014) | NONE: USDJPY 2014 = 87% of the excess (Abenomics; ONE STRETCH); without it t +0.8. Predict FAILED/WEAK. |
| fast-10 | n_trending bottom 10% (<= 0) | +0.390 / +2.6 | - | NONE with a clear mechanism: fast does best when NO book market is trending. Weak guess: its own-market filter then catches fresh, uncrowded moves. Predict WEAK. |
| fast-11 | form20 high third (> 4.66) | +0.259 / +2.6 | - | Hot form -> better, which is AGAINST T5. Likely a proxy for a trending regime (vr120 control keeps only 73%). Predict same sign, weak; if it holds, it is regime persistence, not form. |
| fast-12 | vr120 high third (> 1.06)  AND  dir = short | +0.543 / +2.6 | - | Same as fast-08 (momentum + shorts in the gold 2015 bear). Predict WEAK. |
| dipx-01 | vr120 low third (<= 0.677)  AND  eff10_with < 0 | +0.634 / +4.2 | one stretch (US500 2021) | The ORIGINAL dip theory (buy a straight 10-day decline in a snap-back regime), but 99% from 2020-21 and US500 2021 = 58% (ONE STRETCH). The engine said dip prefers momentum overall. Predict WEAK/FAILED. |
| dipx-02 | vr120 < 1  AND  day_move_with < 0 | -0.557 / -4.0 | - | Gap-up entry: for the next-open dip trades, day_move_with < 0 means today OPENED ABOVE yesterday's close, so part of the bounce happened overnight and the entry is late. In a non-persistent regime the remaining bounce is small. Predict holds (bad). |
| dipx-03 | day_move_with >= 0 | +0.477 / +3.8 | - | Mirror of the gap mechanism: entering at an open AT or BELOW yesterday's close (gap down / no gap) captures the whole bounce. Predict CONFIRMED. |
| dipx-04 | day_move_with high third (> 0.0794) | +0.425 / +3.3 | one stretch (US500 2021) | Same gap mechanism, stronger third (opening clearly below yesterday's close). US500 2021 = 51% (stretch flag). Predict same sign. |
| dipx-05 | vr120 high third (> 0.872)  AND  spread_R mid third (0.0058 .. 0.0096) | +0.614 / +3.2 | - | Momentum half matches the engine (dip likes momentum, D1); the spread middle third has no mechanism (proxy for market / time). Predict same sign, weak. |
| dipx-06 | vr120 < 1  AND  form20 >= 0 | -0.607 / -3.1 | - | T5: after good recent form the next dip trades are worse, in a non-persistent regime. Predict holds (bad). |
| dipx-07 | vr120 < 1  AND  eff10_with >= 0 | -0.499 / -3.0 | - | No real dip: the 10-day path went UP, so the 'dip' is only a short wobble and there is no stretched move to snap back. Predict holds (bad). |
| dipx-08 | vr120 mid third (0.677 .. 0.872)  AND  day_move_with < 0 | -0.785 / -3.0 | - | Same gap-up mechanism as dipx-02. Predict holds (bad). |
| dipx-09 | eff10_with < 0 | +0.398 / +2.7 | disguise? (mv10_with), one stretch (US500 2021) | Real 10-day decline -> bounce, but DEPTH in disguise (mv10_with control keeps 24%) and ONE STRETCH (US500 2021 56%). Predict WEAK; dipx-11 is the cleaner version. |
| dipx-10 | spread_R mid third (0.0058 .. 0.0096) | +0.464 / +2.7 | one stretch (US500 2021) | NONE: the spread middle third is a market / time proxy (US500 49%); US500 2021 = 57% stretch. Predict FAILED/WEAK. |
| dipx-11 | mv10_with low third (<= -1.24) | +0.454 / +2.6 | - | Deeper dip (10-day move <= -1.24 ATR) -> bigger snap-back (why-phase W2 depth idea). Predict holds. |
| dipx-12 | mv10_with high third (> 0.39) | -0.395 / -2.6 | - | No real dip (10-day move up) -> weak bounce. Same as dipx-07. Predict holds (bad). |

## RESULT (confirm run 2026-10-10 15:03, check half 2018-19 + 2024+)
**Headline:** 1 of 44 confirmed (ins-08, which I had predicted to FAIL). By chance: median 0, 90th percentile 2. The hunt as a whole found NOTHING beyond chance.
- **Same sign in the check half:** 18 of 44 (41%). Chance after a selection like this is about 50%.
- **My pre-registered theories had no predictive power:** 9 of 20 "should hold" kept their sign.

**Leads (same sign, not significant; next-cycle list only, they need NEW data):**
- **Dip depth family, 5 of 5 same sign:**
  - deeper dip better: dipx-09 +0.27, dipx-11 +0.28, dipx-01 +0.19
  - no real dip worse: dipx-07 -0.16, dipx-12 -0.14
- **ins on USDJPY, 3 of 3 same sign:** +0.11 .. +0.24.
- **ins narrow inside day (ins-07):** +0.11, weak.

**Clear failures:**
- **Dollar proxies:** all failed, as predicted.
- **The dip gap mechanism REVERSED:** dipx-08 opposite at t +2.0, dipx-03 -0.17. Discovery was 70%+ 2020-21 (Covid gaps).
- **Every momentum-regime pocket built on vr120 (trailing 120-day persistence)** failed or was weak.

**Lesson:**
- The engine proved momentum CAUSES brk / fast edge (t 6+), but a trailing 120-day variance ratio does not READ that regime in time. That is consistent with T4.
- The "when" is real; a usable live detector is not found yet.
- With ~800 trades per half, per-trade pockets need bigger effects (or more data: more markets) to be found.
