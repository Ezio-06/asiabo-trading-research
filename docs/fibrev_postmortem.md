# Postmortem: fibrev and the lane machine, 2026-10-13

**Rules of this postmortem (Ezio):** nothing gets implemented. Each idea is taken out of the corpse and judged against what we know NOW. Verdicts lean on existing evidence, plus small simulations of the corpse's own formulas. Where the evidence doesn't settle an idea, it is marked OPEN.

**Two bodies:**
- **Part A: fibrev** (`cashbot_main.py`, "CASHBOT_V1", FibRev + PULSE + SAW + shadow engine). The signal-level voting blender.
- **Part B: the lane machine** (`Cashbotas_main.py`). The same promote/demote idea one level up: every LANE is a unit, and its state (LIVE / SCOUT / SHADOW / COOLDOWN / LOG-ONLY) is its "weight".

---

# Part A: fibrev (cashbot_main.py)

## How it worked (plain)
- **Setup:** a run of 2+ same-colour candles (the "impulse"), then a pullback into the 0.5-0.618 fib zone of that run, then a lower-timeframe confirmation candle. Entry at the 0.618 price, stop at the run's swing extreme, target 2R. A ratchet arms at +2R and caps at 3R. No trend filter by default (SMA_MODE = "none").
- **PULSE (the blender):** 10 signals each vote +1 / 0 / -1: entry body %, impulse efficiency, impulse body-to-wick, LTF confirmation body, zone touches, zone dwell, zone penetration, run length, NY session, distance from the higher-timeframe MA. Score = average vote, weighted by each signal's learned weight. Score buckets set risk: positive 1.5x, neutral 1.0x, negative 0.35x (later: negative blocked).
- **Learned weights:** weight = 1 + (median R when the signal voted +1 minus median R when it voted -1), from 8 samples per side, rolling 200, bounded 0.15-2.5.
- **Tier sizing:** 7 score tiers. Each tier's size = seed + median R of that tier (15+ samples). Tiers re-ranked by median R.
- **Threshold tuning:** 4 candidate thresholds each for two signals; promote the best if it beats the default by 0.05R avg on 20 samples. Later, a general gate: Mann-Whitney test at p < 0.05 on 30+ per side, then a held-out window of 20 at p < 0.10 to confirm. Rechecked up to twice a day.
- **Shadow engine:** gate-rejected setups walked forward with a perfect fill at 0.618, flat 2R exit, no persistence.
- **SAW (money):** flat 1% base risk; the daily floor ratchets up on green days; below the floor the quality bar rises; "debt repayment" lets positive setups size up to win back the day's loss (capped at the debt); a daily target "match yesterday's gain"; a 3-trades-a-day pace that lowers the quality bar when behind; a win-streak bonus of +15% risk per consecutive win (up to +50%).

## Cause of death (four wounds)

1. **The setup had no fuel.** A 2-candle "impulse" is noise-sized: same-colour runs of 2+ happen constantly on a random walk (its own data: median run length 4). There's no trend context, no range position and no reason anyone loses money to you at 0.618. T1 says continuation pays only when it agrees with 10-20 day momentum; nothing in the setup checked that. No who-pays.

2. **The blender's gauge was blind by construction (measured, not guessed).** With fixed -1 / +2 outcomes, a MEDIAN can only be -1 or +2 (or +0.5 on a tie), depending on whether more or fewer than half the trades won. So the weight formula didn't measure edge; it measured "did this bucket win more than half its trades". Simulation of the exact formula (win rates around 35%):
   - **No-edge signal, 8 samples per side:** 23% get slammed to the 2.5 ceiling, 23% to the 0.15 floor, purely by luck.
   - **Real edge (40% vs 30% win rate, about +0.3R, a BIG edge), 100 samples:** 97% sit at 1.0, unrecognised. At 200 samples, 99.7%.
   - So it was noisy early and blind later: it chased luck on small samples and could never see a real faint edge on large ones.
   - **Tier sizing had the same flaw:** below a 50% win rate the median R of a tier is -1 almost surely (87% at 15 trades, 100% at 300). Every tier's multiplier drifts to seed - 1, which crushes all sizes toward the floor, and every tier ties on rank, so "rank tracking" just returns the seed order.
   - The code chose the median "to avoid one fat-tail trade dominating". With a fixed 2R target there are no fat tails to fear; the median just threw away the information.

3. **Its promotion tests peeked.** Threshold promotion picked the best of 4 candidates on 20 samples with a 0.05R margin; the noise on 20 trades is about ±0.3R, so it picked noise. The later Mann-Whitney gate was a real upgrade (a held-out confirmation window is the right idea), but rechecking a p < 0.05 test twice a day as data arrives is optional stopping: the real false-positive rate is many times 5%. And Mann-Whitney on -1 / +2 outcomes is basically a win-rate test.

4. **The money layer chased losses and hot streaks.**
   - **Win-streak bonus** = sizing up after hot streaks: exactly what K5 measured losing (trailing Kelly -43 R/yr), and T5 says hot form precedes worse trades.
   - **Debt repayment** = sizing up to win back today's loss: recovery chasing. The cap stops it from risking more than the debt, but it still sizes up after losses on the theory that a "positive" setup will repay them.
   - **Pace target** = lowering the quality bar to hit 3 trades a day: the same quota that lost in the lane machine.
   - **Daily target "match yesterday's gain"** ties today's goal to yesterday's luck.

## What fibrev got right (worth keeping)
| Idea | Why |
|---|---|
| Structural invalidations kept separate from quality votes | Correct split: "this isn't the setup any more" vs "this is a weaker version of it". |
| Flat base risk instead of compounding risk decay | Its own backtests found decay digs an unrecoverable hole. Matches "fixed fractional" (T5 corollary). |
| `low_info` flag (all signals abstained ≠ a real neutral) | Honest bookkeeping. |
| Held-out confirmation window before trusting a promotion | The right instinct; it later became "exam data stays sealed". |
| Non-parametric test awareness (skewed R) | Right worry, wrong fix for fixed-target outcomes. |
| Shadow copy of the logic, duplicated not imported | Live changes can't silently change what shadow tests. |
| Honest scope notes in the code (what is and isn't built) | Good practice. |

## What fibrev was missing that the next generation added
- **A random control lane / random yardstick.** fibrev never asked "would random entries do the same?" The lane machine added the control lane and the luck budget; both are direct answers to fibrev.
- **Costs in shadow** (perfect fills at 0.618, no spread). Limit-style fills at a pullback level also suffer adverse selection: you get filled most often on the trades that keep going against you.

## One finding that points the WRONG way, by today's knowledge
- `htf_ma_distance` voted NEGATIVE when price was extended in the trade's direction from the higher-timeframe MA. T1 / T2 say the opposite: trades that agree with the bigger move and sit at the trade-direction edge are the ones that pay. fibrev was penalising its best trades. (Spent-data finding, consistent only, not proof for fibrev's timeframe.)

## Correction to the chat
Earlier in the chat Claude said fibrev's architecture "was fine, there was no job to do". That was wrong. Even with good inputs, its median-based weights could not have seen a faint edge (wound 2). It died of no fuel AND a blind gauge.

---

# Part B: the lane machine (Cashbotas_main.py)

The file has no fib signals and no weighted vote. Every lane is a unit; its state is its weight; each lane's shadow record moves it up and down.

## Cause of death (three wounds, any one fatal)

1. **No fuel.** Most lanes had no edge after costs: fixed 2R targets, ATR(M15) stops, flat at 16:00 (lane audit, T3, T17, T24). No promotion machine can make edge out of inputs that have none.
2. **It followed form, on every layer.** Lanes were promoted after good recent results (last 10 >= 0, fresh-run confidence, fast promotion on 20 home trades, log-only straight to live on a strong run, revive on last 60 >= 0). They were benched after bad recent results (last-20 test, 5 losses in a row, 5R drawdown). Scouts were paused and released on recent form, and equity zones halved size after give-back. Our most robust finding about form says it REVERSES on this scale: T5 (z 4.1, 12 of 17 lanes), T22, run 4 (switching on form loses), K5 (trailing Kelly -43 R/yr). So the machine was built to be anti-timed: in after luck, out after bad luck.
3. **Its windows were too short to see faint edges.** A lane with a real +0.08R edge and a 2R target has a per-trade spread of about 1.45R. To clear z = 2 it needs about (2 x 1.45 / 0.08)^2 ≈ 1,300 trades: years at ~0.7 trades a day. Promotion at 40 trades, or 20 on the fast bar, could only catch luck or lumpy lanes. Benching was worse: a lane losing 64% of the time hits 5 losses in a row within 20 trades 58% of the time; at 75% losses (breakout-like), 98% within 40. So the bench rules benched healthy lanes routinely. State changes were mostly driven by noise.

## Idea-by-idea verdicts

| Idea | Verdict | Why (current evidence) |
|---|---|---|
| Shadow record for every lane, live or not | **KEEP** | The basis of T19. Free evidence. |
| Confidence = mean - z x SE for promotion | **KEEP the maths, fix the window** | Sound statistic (and a MEAN, unlike fibrev's median); fatal only with 40-trade windows on faint edges (wound 3). |
| "Fresh" record resets on each demotion | **DEAD** | Throws away exactly the history faint edges need. |
| "Last 10 >= 0" on every promotion path | **DEAD** | A hot-form requirement; T5 says hot form precedes worse trades. |
| Bench on last-20 / 5-loss streak / 5R drawdown | **DEAD** | Triggers on noise (58-98% odds, wound 3), and bad stretches precede better trades (T22). |
| Dormancy / log-only (turn off on strong evidence of losing, 150 trades, z 2) | **KEEP, off-only** | The smoke-alarm half: long window, strong evidence, can only switch off (T19). |
| Revive / log-only straight to LIVE on a strong run | **DEAD** | Promotion on hot form again. |
| Luck budget + dynamic bars (simulate a no-edge copy, set each lane's bar so false promotions stay within a system budget) | **KEEP, best idea in either corpse** | Proper false-discovery control, built in. Same spirit as the random yardstick rule. Reusable for any future gate or lane admission. |
| Control lane through the same lifecycle | **KEEP** | Already a house rule. fibrev had none. |
| Regimes from the 20-day efficiency ratio (trend >= 0.30, chop < 0.12) + vol rank | **RIGHT gauge, WRONG use** | T23: straightness reads regime (er40 AUC 0.79-0.88); vol readable. But here it only sped up promotion (z 1, 20 trades) on regimes that flip ~weekly (the file's own comment). Today's use: gate the trades, don't speed up trust. |
| Empirical home regime (re-derived at 2.5 SE, 1.5 SE exit, theory as prior, 48 tests counted) | **OPEN** | Careful multiple-testing design. Now superseded by causal results (brk/fast home = momentum, ins regime-blind). Only worth reviving for a new lane with no causal test. |
| Quota / scouts (force trades to hit 3 a day) | **DEAD** | Its own data: forced fills -$394 / 146 trades vs earned +$302 / 98. Trade count is not a goal (T3). Same idea as fibrev's pace target. |
| Pair conflict + max open risk 2% | **KEEP** | The dedupe idea that T20 later proved (stacking was a big part of the drag). |
| Worst-case costs incl. swap (gold long -$0.805/oz/night) | **KEEP** | Anything that survives can only improve live. Matters for multi-week holds (N4, Turtle): ~20 nights at that rate is a real slice of a faint edge. |
| Warm start 365 days, calibration 250 days, nothing tuned on it | **KEEP** | Same as the "about a year of evidence before live" rule. |
| Fixed 2R targets, ATR(M15) units, flat at 16:00 | **DEAD** | Lane audit 5/5; T17 / T24 (caps destroy tail edges). |
| Adaptive TP (lock profit tighter in drawdowns) | **DEAD** | Caps winners (T17 / T24). |
| Equity Pulse survival limits (kill line, daily halt, kill base seasoned over ~3 months) | **KEEP (house, Ezio's side)** | Survival, not edge; nothing in the evidence argues against them. |
| Equity Pulse form-sizing (defend / recovery at 0.5x, run leashes, scout pause and escalation) | **OPEN (house, Ezio's side)** | All of it sizes on recent equity form. T5 / T22 suggest size cuts after losses are anti-timed; T21 says cutting after win streaks points the right way but is within noise. Testable cleanly: same trades, fixed size vs zone sizing, on fresh data. |

---

# Lessons carried forward (both corpses)

1. **Inputs first.** Every unit (signal, gate, lane) must prove itself alone against a random yardstick before any combiner sees it.
2. **Combine simply.** Separate switches, not learned or form-moved weights (T12, T16, fibrev).
3. **The scorecard can only turn things OFF,** on long windows and strong evidence. Anything that promotes on recent form is the T5 trap.
4. **Windows must match edge size.** Before any rule judges a unit, compute how many trades a real edge of the expected size needs to show at the chosen z. If that's years, the rule is judging noise.
5. **Admission control is worth keeping.** The luck budget is the reusable piece: admit new lanes or gates at a rate where false admissions stay within a fixed yearly budget.
6. **(fibrev) Test the gauge on known-truth data before trusting it.** fibrev's weight formula could have been caught in five minutes by feeding it a planted edge and a planted no-edge signal. Every scoring formula gets that check first.
7. **(fibrev) No peeking.** A significance test rechecked as data arrives needs a correction (or a fixed sample size decided in advance).

# Open question for the retrial
Can any promotion ever beat off-only? Only in a world where edges switch on and off slowly and cleanly. Test on planted-switch regime worlds (no exam data): (a) promote + demote with decay (using a MEAN-based score, not fibrev's median), (b) off-only, (c) fixed equal weights, (d) best single input, plus random inputs on a random walk. Claude's prediction: b >= a, and c ≈ a, on real-shaped worlds.

---

# The scorecard's family tree (fibrev → today), added 2026-10-13

| fibrev piece | What it did | Today's descendant | What changed |
|---|---|---|---|
| SignalPerformanceTracker | Per signal: outcomes when it voted +1 vs when it voted -1; the gap = its weight | Gate scorecard (T19): flagged vs unflagged trades; the gap = trust | **The core idea survived intact: judge a signal by the CONTRAST between its "yes" and "no" trades, not by raw P&L.** The gauge went from median (blind on -1/+2 outcomes) to mean R. |
| Live tracker fed only by trades the gate LET THROUGH; shadow tracker fed only by trades the gate REJECTED | Two half-populations, each biased by the gate | Every trade simulated, gate only flags it | Today sees the full population, so flagged vs unflagged is a clean comparison. fibrev never saw a signal judged on the same trades it was filtering. |
| Shadow kept separate "because the populations aren't apples-to-apples" | Early instinct that a signal's meaning depends on the population | T18 (a gate has to be validated on the population it will filter) | fibrev noticed the problem and kept the books apart; T18 named it and fixed it by measuring on the filtered population itself. |
| PromotionCandidate: testing → provisional → confirmed on a held-out window → back to testing if the held-out fails; REJECTED state | Two-stage trust with fresh confirmation | Pre-registration + sealed exam data | Same instinct, moved from inside the bot to the research process. The in-bot version peeked (rechecked twice a day). |
| Shadow promotions logged, never auto-written to live ("a deliberate, reviewed config change") | Human in the loop | "Ezio runs it, Claude reads, predictions before results" | Kept. |
| Weight floor 0.15 ("never fully silence a signal") | Bad signals keep a small vote | Trust can go to ~0 | Today is stricter; T19 showed trust ~0 cost nothing. |
| Archived, never built: "reversal trial" (a persistently backwards signal gets its polarity flipped after sustained further evidence) | | Not in today's system: trust stops at 0 | **Lost heirloom.** T18 found exactly that case (inside H2, far-side and Friday trades did BETTER). Today we only switch such gates off. A flip would be a NEW signal found on spent data, so it needs its own pre-registered test, but it has a mechanism (see below). |

**Connection worth keeping (hint only, spent data):** T18's reading of the backwards "far side" gate was "a pullback inside a trend". That's fibrev's own entry idea (buy the pullback), and the thing fibrev lacked was trend context. So fibrev's entry concept may live on as "pullback while 10-20 day momentum agrees", a sub-population of H2, not as a standalone 2-candle fib setup.
