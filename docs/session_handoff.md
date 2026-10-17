# Session handoff: how we work, and where things stand (updated 2026-10-13 23:05, end of session: Ezio on a break)

**Read first in a new chat:** trendwhy_spec.md (THE NEXT RUN), explore_results.md, theory_ledger.md (bottom = newest: T25-T34), theory_notebook.md (Ezio's N1-N5), exam_us500_results.md, dip_drift_results.md, dipvol_results.md, vol_worlds_spec.md, fast_giveback.md, fibrev_postmortem.md, core_book_v2.md, lane_ideas_30.md, sensor_pairs.md. Older background: young_batch1_results.md, synth_v8.md, probe_results.md, frozen_design_v1.md, why_phase_results.md, power_run_findings.md.

## Files on Ezio's PC: D:\coding stuff\Trading research project\
| File | What it is |
|---|---|
| bars.db (2.5 GB) | M1 bars; table bars_m1 + gaps. Symbol names as stored ("GERMANY 40", "US 500"). **US 500 starts 2020-01-02** in bars.db. NOT rebuilt since the exams |
| bars_origin\ | the raw exports that built bars.db |
| **exam_hold\\** | US 500 2015-19 export (SPENT by the exam), US TECH 100 2015 + 2020 exports (SPENT for dip by dipdrift / dipvol; still unused for N1 / N3 / #33), exam_us500.db, ustech100.db, EXAM_DONE.txt, DIPDRIFT_DONE.txt |
| **run.bat + asiabo.py + modules.json** | THE launcher. `run.bat run <key>`; `run.bat status`; `run.bat list` |
| runs.csv / reports\cli\logs\ | run log + full console output. **Claude: read these first** |
| asiabo_offline.py / asiabo_lab.py / asiabo_why.py / asiabo_probe.py / asiabo_young.py | base, lab, why phase, probe, younglings |
| **asiabo_exam.py** | US500 fresh-data exam (`exam_baseline`, `exam_us500` ONE-SHOT: done) |
| **asiabo_dipdrift.py** | dip + Ezio's drift table on US Tech 100 (`dipdrift` ONE-SHOT: done). Also `--check <db> <market>` |
| **asiabo_explore.py** | every living candidate on TRAINING data: F fast per market, N5, N3 fade, N4 trend option (one design), dip ATR40 (`explore`). Noise bars in its header + explore_spec.md |
| **asiabo_trendwhy.py** | trend option: how we won / lost / can't explain (`trendwhy`), with the FIXED entry timing (M15/M1 first touch). Spec: trendwhy_spec.md |
| **asiabo_dipvol.py** | dip: skip when volatility high AND rising, ATR 5/10/20/40, exploration on spent data (`dipvol`) |
| make_synth.py (v8) / synth_batch.py / engines | synth and earlier studies |

## Working rules
- Ezio runs things with run.bat and says "done"; Claude reads runs.csv → logs / reports.
- **Claude can run on REAL spent data in the cloud** (synth\cache staged + stub bars.db + `make_synth gen --preset identity`; exam dbs can be staged). Predictions BEFORE any real run. **Mechanics tests on FAKE data only** (2026-10-13 slip: the dipvol mechanics check used real spent bars, so its result existed before Ezio's prediction).
- Claude cannot move or delete files on the PC (no device shell): read, stage, write new files only.
- New study = new module + modules.json entry. Cloud test → commit with expectedMtimeMs → stage back and md5.
- **Research rules:** WHEN not "no edge on average"; each signal on its own evidence; always a random-market yardstick; predictions before results; test every scoring formula on known-truth data; **verdict bars set on noise runs before the real run** (both exams needed it); **data-coverage check before scoring**; **pre-set sample sizes, never "run until significant"**; **report skipped vs kept for every filter (T28)**; **put filters on the clock of the payer (T26)**.
- **Ezio's rule (2026-10-13): only so much skepticism on a genuinely positive signal.** Once a signal has passed a test that could have gone against it (noise bars), STOP stacking disproving tests. Next step = a WHY breakdown: how we won vs how we lost vs what we can't explain, with our theories of what wins and what loses written down BEFORE it runs. Fresh data stays the final proof, spent sparingly.
- Name ideas in plain words (not N4 / T26 alone): sessions are hours apart.
- PROCEDURE: plain-language theory first, then ASK Ezio for his prediction or choice. Every theory names who pays.
- Ezio's preferences: ask "what pattern are you trying to fix" before building his changes; honest assessment; post updates in long builds.

## Where things stand (2026-10-13 evening)
- **Core book after two fresh tests (T25):**
  - **fast:** FAILED on US500 (never real there). Its edge is on gold (EDGE +0.21, t 3.0, all eras, spent data). Agreed rule: back to the why phase. Proposed: drop US500 from fast; check Germany 40 / USDJPY per market on spent data; gold 2022-23 (sealed) is the only fresh gold test (Ezio's call).
  - **dip:** real but small on fresh data (~+0.1 R/trade vs +0.55..+0.76 training); 2018 its worst year in both tests. Ezio's drift table: INSIDE THE NOISE on US Tech 100 (barely bites on a strong-drift index; helped in 2022). Synth: the table's negative side works but is too slow (most bear damage lands in a bear's first quarter).
  - **Volatility and dip (T30):** high-and-rising volatility is bad in every synth world and in real data; on the fast gauge (ATR 10) the skipped trades = kept trades (a size cut), while slow gauges (ATR 20/40) find the losers → the enemy is a long stress REGIME. Candidate fresh-data rule: skip dip while the 40-day ATR ≥ 1.3× its 1-year median AND rising (gauge seen on spent data first: flag it).
- **Ezio's notebook:** N1 fuel/refuel, N2 gate, N3 fade against-trend breaks (US Tech 100 later), N4 trend option (precondition + direction open), **N5 flat means undecided** (gold fast flat-at-2h trades earn the afternoon, peak 13:00-14:00 London = COMEX open + US data; needs fresh data).
- **Ledger additions 2026-10-13:** T15 relabelled (as built), T16 addendum (fibrev), T25-T30.

## Fresh data left
- **Sealed:** Japan 225 (never read), 2022-23 for the six house markets (incl. gold 2022-23 for fast).
- **Not exported yet:** US 30 (Ezio). The natural fresh index for the dip regime rule.
- **US Tech 100:** spent for dip; still fresh for N1 / N3 / #33 if those tests don't use dip's results.
- **US 500 2015-19:** spent; can now go into bars_input → build_bars_db → synth_cache (only the US 500 file; keep US TECH 100 in exam_hold).

## TO-DO / next (Ezio decides)
0. **explore DONE (2026-10-13 21:37), see explore_results.md:** fast = gold only; N5 alive on gold, leaning on USDJPY / pooled (13:00 London peak again); N3 DEAD; **N4 (Claude's one design) clears its bar, EDGE +0.33 t 3.8, FX / gold / oil only, but only ~15 trades a year: a fresh test needs more fresh markets**; dip ATR40 rule fails its t bar (rests on 6 US500 trades; GER opposite). Ezio: indices are 'the whole bazaar' (diluted), not a failure; no new exports; index test held (a null result teaches little). **Explore's trend-option number is biased upward** (daily-bar entry dropped days that touched both box sides): trendwhy has the fix. Next: Ezio writes his win/lose theories in trendwhy_spec.md, runs `run.bat run trendwhy`.
1. fast: per-market check (Germany 40 / USDJPY) on spent data; decide on gold 2022-23.
2. dip: lock the regime rule (40-day ATR) with a stated reason; test once on US 30 (export first) or Japan 225.
3. N5: pre-register the afternoon test for gold 2022-23 (shares the seal decision with fast).
4. Outside-AI briefing pack; lane postmortems one per day (done: fade, turtle, fibrev; remaining: sar, range, exhaust, vwap, bigrev/bigcont, main, london, retest, pdh, nr7, trend, nyaft, scalp, gapfill, swing, dip).
5. #31 near-stop follow-up; #19 as a sensor; N4 trend-length measurement (spends nothing).
