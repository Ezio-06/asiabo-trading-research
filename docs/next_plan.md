# Next plan (Claude, 2026-10-11): CLI cleanup, then probes, then younglings and sensors

Sources: lane_ideas_30.md (ideas 1-32), sensor_pairs.md (pairs, families, timescales).

## Phase 0: one launcher, CLI dashboard (Ezio: "one bat, clean up everything")
**The pattern being fixed:** 15 run_*.bat files and 12 scripts, with results spread over claude vision / reports / engine\worlds / synth_batch. New studies keep adding more of both.
- **New files only:**
  - `asiabo.py`: an interactive menu dashboard
  - `run.bat`: the only launcher
  - `modules.json`: the module registry
- **Existing scripts are NOT edited.** The CLI runs them as subprocesses with their own args, so identity is untouched.
- **The registry**, per module:
  - name, script, args (editable)
  - estimated time and peak RAM
  - where it writes
  - whether it wipes claude vision
- **Menu:**
  - run a module, or a queue of modules
  - status: the last run of each module and its newest report folder
  - open / list the latest report per module
  - tweak a module's args
  - add / remove a module
  - clean
- **Results routing.** Every CLI run is logged to `runs.csv` (time, module, args, exit code, report folder, duration). That way Claude reads the newest result per module instead of guessing which folder is fresh.
- **Clean:**
  - MOVE the old bats to `old versions\bats\` (never delete)
  - list stale files in claude vision, reports and synth for Ezio to approve
  - show disk use of synth\cache and the job dbs
- **Test before commit:** the usual fake-bars.db workflow, md5 check after commit, fresh filenames.

## Phase 1: the probe study (the first new CLI module, `asiabo_probe.py`; reads bars.db + existing trade lists)
- **M1 trend end:** after each real er40 spell ends, the next 5 / 10 / 20 days. How often does it reverse, chop or continue, by how far (daily ATR), blow-off vs slow ending?
- **M2 hazard curve:** survival analysis of momentum spells by age, against a memoryless curve and the dayshuffle cousin. This decides #31's age condition.
- **M3 failed-shadow run:** after quick brk / fast stop-outs, the opposite run before the initial stop, against random entries at the same hour / volatility. Split by speed of failure and by regime.
- **M4 correction stats:** stretch from the 20-day average × structure crack → next 1 / 3 / 5 days, against random and dayshuffle.
- **M5 seeing-speed map:** per indicator / lookback (SMA / EMA 5-200, er10-60, ATR 5-50), the detection lag vs the remaining life of the state, on synth (known truth) and real data.
- **M6 serial dependence:** P(loss | loss) for fast / dip / brk, with a permutation percentile (trade order and block shuffle), on non-overlapping trades. Report the skip and mirror break-even lines.
- **Every section:** predictions written first, a random-walk yardstick, the dayshuffle cousin, clustered t.

## Phase 2: synth realism fix (before any new lane goes through the engine)
- **The pattern being fixed:** synth regimes are sharper and longer than real ones, so momentum lanes look too good in the ideal worlds. That is what kept the brk results misleading.
- **make_synth v7:** regime spells drawn from the REAL spell length / softness distribution (taken from M2), including mild spells where neutral days still pay.
- **Realism gate:** the synth er40 spell histogram must match the real one, or the run fails.
- **Off-switch:** v7 with the new options off must stay byte-identical to v4.

## Phase 3: youngling screen (real data, shadow)
- #31 mirror dip
- the first pairs: #27 / #28, brk / #1 soup, #4 / #20
- each with one exit per outcome (labels)
- protocol: prediction, yardstick, clustered t, half split, monthly correlation with fast + dip

## Phase 4: sensor test (#32)
- Per pair and per family: do features of resolved shadow trades predict the next trade of another lane?
- Compare against er40 and against a shuffled order. Report the direction.
- Then cross-scale: slow probes gating fast lanes, and fast probes predicting brk.
- Keep the same-trigger and nesting traps excluded.

## Phase 5: engine on survivors
- Ideal / nightmare worlds on the v7 synth.
- Anything that survives goes to the pre-registered add-to-book check. The exams stay sealed.

## Ezio's predictions to write before Phase 1 runs
- **M1:** after a trend ends, does price reverse or chop, and how often?
- **M2:** is the hazard curve flat, or rising after ~20 days?
- **M3:** do quick failures run further the other way than random? Fast vs slow failures?
- **M4:** do stretched + cracked markets fall more than random? Which markets?
- **#31:** roughly what win rate, and which markets?
