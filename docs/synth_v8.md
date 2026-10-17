# make_synth v8: week-block base + block snap (DONE, committed 2026-10-12 13:30, md5 verified)

**Live:** make_synth.py = v8 (md5 143f9be3...). v7 is archived as old versions\make_synth_BEFORE_v8.py; old versions\make_synth_v8_WIP.py is the same file as the live one.

**Pattern fixed:** v7's two gaps:
- no volatility clustering (dayshuffle base)
- the index next-day reversal spread over calm days, which killed dip's setups

## Model (preset `real8` = shuffle week blocks 2-6 + `--bsnap 1.0`, lb 40, bmom 0)
- A WHOLE block whose move beyond the drift goes WITH the new path's de-drifted 40-day trend is mirrored (around the era drift line, as v7).
- Blocks holding a shock day (> 5 × the median move) keep their direction. No gap closing.
- Everything inside a block stays real.
- Spell table: one row per block, mirrored / kept.

## Calibration (daily simulator on 9 REAL M1 block bases: 6 calibration × 2, 3 held out)
| | Real | v8 calibration | v8 held out | v7 |
|---|---|---|---|---|
| Days in a hindsight trend | 0.147 | 0.142 | 0.146 | 0.147 |
| er40 precision | 0.245 | 0.261 | 0.234 | 0.270 |
| Next-day autocorrelation (native) | -0.058 | -0.057 | -0.063 | -0.061 |
| Index days after 3 down closes | 0.081 | 0.090 | 0.086 | 0.02 |
| Bounce after them | 0.604 | 0.551 | 0.574 | 0.72 |
| Volatility readability | 0.776 | 0.671 | 0.669 | 0.52 |

- The generator matches the simulator on the same base.
- 8-26 week blocks don't raise volatility readability (block joins across eras break slow vol regimes): ~0.67-0.70 is the ceiling.

## Extended gate
- **Added:** vol_prec, down3 (STRONG), bounce3.
- **Tolerances:** the same rule, 2 × the calibrated generator's seed spread (now v8). vol_prec gets 0.15 (v8 ~0.10 below real).
- **Pass rates:**
  - simulator: v8 12/18, block base without the snap 2/9, v7 0/18, dayshuffle 0/9
  - **real data: v8 seeds 1, 2, 3 ALL PASS**
- **Off-switch:** identity, dayshuffle, v6 regime + aging, and real7 are identical (bars / gaps / regime / meta) between the v7 and v8 files.

## Probe on v8 worlds (real cache, cloud)
| | Real | v8 s1 | v8 s3 | v7 s3 | Cousin |
|---|---|---|---|---|---|
| dip book trades | 139 | 74 | **112** | 53 | 96 |
| dip losing share | 26.6% | 40.5% | **25.9%** | 22.6% | 29.2% |
| atr10 precision (probe) | 77.9% | 70.3% | 66.6% | 56.7% | 56.2% |
| er40 precision | 24.5% | 29.9% | - | 28.4% | 40.5% |

- **Dip setups per year** (RSI2 < 10 or 3 down closes, above the 200-day average): v8 11-22 vs real 16-18. They are realistic.
- The **dip trade count swings with each seed's bull strength** (US500 time above the 200-day average: real 0.94, v8 s1 0.73 / s2 0.87 / s3 0.97). **Judge dip on v8 over several seeds**, never one.

## CLI
- `synth8_check` = real8 s3 + gate + probe on it (~15 min).
- `synth_gate` = gate a given db.
- `synth7_check` is kept but marked superseded (it fails the v8 gate by design).

**Next:** Phase 3 younglings on REAL data (#31 mirror dip, #27/#28 US500-DAX pair, one vol lane: #19 or #12). Ezio's predictions are needed for #27/#28 and the vol lane.
