# Pocket engine (stage 1 built 2026-10-10)

**Ezio's idea (2026-10-10):** one engine with two functions.
1. Pocket search hunts for market states (regimes, volatility, and so on) where a lane works.
2. Synth builds an IDEAL world (more of that state) and a NIGHTMARE world (less of it). If the ideal does not do better and the nightmare does not do worse, the pocket is noise or a quirk of day order.

**The trap, designed around:**
- Building the ideal by SELECTING the same days the lane won on is circular.
- So ideal / nightmare is used only for states synth can CREATE by changing price paths: momentum vs snap-back, day order, trend length, volatility, gaps, spreads.
- Select-only states (calendar, "Friday after CPI") are judged by a half split plus a random-world yardstick instead.

**Order:**
- Stage 1 = the intervention machinery, proven on states we already have theories for.
- Stage 2 = the open hunt. Each pocket gets a written theory naming its state, then that state's dial tests it.
- Lanes in stage 1: brk, ins (shelved; "when do they work") and fast, dip (core), to learn about all four.

## Files
- **make_synth.py v5:**
  - new `--persist k` dial: log p' = log p + k (log p - 20-day mean of closes, blended through each day). k < 0 = momentum, k > 0 = snap-back.
  - `--markets` builds a subset of markets.
  - faster writer (about 25%).
  - Byte-identical to v4 with the dial off.
- **asiabo_engine.py:** worlds built and measured in parallel, resumable, through asiabo_why / the lab lanes. Results go to reports\engine\worlds\*.json, the report to engine.txt.
- **run_13_engine.bat**

## Stage 1 dials and PREDICTIONS (written before any engine world was measured)
- **D1 momentum vs snap-back** (persist k = +1.5, +0.5, 0, -0.2, -0.4 on a 2-6 week reshuffle; the ladder was set from world statistics only):
  - brk +, fast +, dip - (snap-back buyer: momentum hurts), ins 0
- **D2 trend length / day order** (dayshuffle -> shuffle 2-6w -> longblock 8-26w):
  - brk +, fast 0, dip +, ins +
  - Not independent of batch 1 / the why phase.
- **D3 volatility level** (vol 0.6 .. 1.6):
  - EDGE 0 for all; NET + for all, steepest for ins and fast (cost theory T3)
- **Verdicts:** slope of edge per dial step, pooled seeds, clustered by seed x market x month.
  - CONFIRMED |t| >= 3 with the right sign; SUPPORTED 2-3; NOT SHOWN < 2; CONTRADICTED wrong sign with |t| >= 2.
  - For a 0 prediction: CONSISTENT < 2; CONTRADICTED >= 3.

## Calibration notes
- persist k = -0.5 gives a 20-day variance ratio of about 2-3 and trend months of 50-60% (real data: about 1 and 20%).
- k = +1.5 gives about 0.65.
- The dial scales intraday moves by (1+k), so it is judged on the cost-free EDGE.

## Added before any real world (2026-10-10)
- **dipx = LOOSE dip readout:** every RSI(2) < 30 day and every 2+ down-close streak above the 200-day average, overlapping allowed, same exits. About 6x dip's trades. Same predictions as dip (D1 -, D2 +, D3 edge 0 / net +). Reason: dip has ~150 trades a world, and on the random walk even planted snap-back gave t -0.4.

## Engine check on fake random-walk markets (cloud, 1 seed)
- **Planted momentum (D1):** brk CONFIRMED t +4.7, fast CONFIRMED t +6.1, ins CONSISTENT. dipx t -1.8: momentum hurt it clearly, but extreme snap-back (k +1.5) hurt too (an upside-down U). Read dip by its shape.
- **D2 on a random walk:** nothing found (|t| <= 0.8). No false positives.
- **D3:** edge flat, net up for brk / ins / fast.
- **Runtime:** about 2.5 min per world in the cloud (generate + measure), 23 worlds at 2 seeds. Peak about 1 GB per job.

## Stage 2: the HUNT (asiabo_hunt.py, built 2026-10-10)
**Protocol, fixed before any hunt result:** the search and the check never see the same years.
1. **discover** (run_14) on 2014-17 + 2020-21 only.
   - About 25 states known at entry, each cut into thirds (cut points from this half) or categories, alone and crossed with the momentum axis vr120.
   - Kept: clustered |t| >= 2.5, at least 60 trades in and out, at most 12 per part.
   - Locks reports/hunt/pockets_locked.csv (hash).
2. **Claude writes a theory per pocket** into the 'theory' column, before confirm.
3. **confirm** (run_15) once on 2018-19 + 2024+.
   - CONFIRMED = same sign and t >= 2 (n >= 30); WEAK = same sign; FAILED = opposite sign.
   - Refuses if the definitions changed after the lock.
4. **Yardstick:** 20 hunts with each market's states circularly shifted against its trades.
   - On the fake random walk a hunt "discovers" about 17 pockets by chance and confirms 0-2 (90th percentile 2).
5. **Creatable pockets** (persistence, trend, volatility, spread) go next to the engine's dials. Select-only ones stand on the split.

### Hunt additions (Ezio, 2026-10-10, before any real hunt run)
- **Both directions:** GOOD pockets (keep the part on) and BAD pockets (make it harmless) pass the same bar.
- **Both sides and extremes of every state:** thirds, bottom / top 10%, and a sign split for centred states (0 for "with the trade" moves, 1 for vr120). Near-duplicates (80%+ the same trades, same sign) are dropped.
- **Per kept pocket, all on the discovery half:**
  - PROFILE: direction / market / era mix and median regime, volatility and trend, inside vs outside.
  - DISGUISE check: within each third or category of every other state, does it still beat the rest? Reports the worst control and the share of the effect it leaves. Below 50% is flagged.
  - CONCENTRATION: share from the best market-year, and the diff without it.
- The locked csv carries these columns for theory writing.
- **Fake random walk:** noise pockets passed the disguise check easily. These checks catch proxies and lucky stretches, NOT luck itself; luck is the job of the check half and the yardstick. Chance confirmations with the wider search: 0-4 (90th percentile 3).
- **Device-commit lesson:** re-committing from the SAME staged filename wrote the OLD cached file. Always stage under a fresh name and md5-check after.

## Stage 3: the REGIME ENGINE (asiabo_regime.py + make_synth v6, built 2026-10-10)
**Ezio's aims:**
- Synth as a brute-force test of each signal's ideal and worst worlds.
- In the ideal world, how much of the trend we capture, and whether any signal identifies the trend.
- Always finalize on real data.

**Worlds:** dayshuffle base + `--regime d,d`. Each market switches between momentum / neutral / snap-back spells of 20-130 FX days, and the true label is saved.
- **LEAK-FREE dial:** each FX day keeps its exact size, range and shape; only its direction is chosen (kept or mirrored). It goes with the last 20 days' trend with probability 0.5 + d / 0.5 - d / 0.5. Verified bar for bar against the base world.
- Mirroring removes base drift in every state (matters for dip, which needs drift).
- The first design (added drift) leaked close-to-close volatility and was replaced before any lane ran.
- Seam carry across eras. Artificial gaps (> 6x the typical move) are closed.

**Generator artefacts found (pre-existing in all dayshuffle / shuffle cousins):**
- Era seams: each era restarts at the source price.
- A few artificial weekend gaps of 10-36% per market (a source day from another daylight-saving period joins to a stale price).
- Rare, but they touched earlier batches slightly.

**Report:**
- R0: worlds by state.
- R1: part edge by true state.
- R2: detector scorecard (AUC, precision / recall at the base rate, lag, caught in the first half, false switch-ons).
- R3: gating (none / perfect / not-snap / top-6 detectors).
- R4: trend capture (share of the spell move taken, days to the first trade in direction, giveback).
- R5: AUC of every hunt signal for the momentum state.

Runs strengths 0.15 and 0.25, 3 seeds each (run_16_regime.bat).

**Fake random-walk preview (1 seed each; NOT results):**
- Straightness gauges (er20 / er40 / er60, tshare60, follow60) AUC 0.70-0.88; variance-ratio and autocorrelation gauges near blind (0.5-0.64).
- Gating brk on er40 kept about 42% of trades at 2x the edge / trade.
- dip LOSES in momentum when the drift is removed. dip = snap-back + uptrend drift.
