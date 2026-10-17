# Theory notebook (Ezio's theories, started 2026-10-12)

**What this is:** Ezio's own market theories, in plain words, written BEFORE any data is looked at for them. Learning from spent data is fine; testing on it is not. A theory only goes to a test when Ezio wants to bet on it, and then only as a pre-registered test on fresh data (US 500 2015-19, US Tech 100, US 30).

**House rule for every entry: name who pays you.** Money in a trade comes from someone else's mistake or need. A theory that can't say who is on the other side and why they lose is not finished.

---

## N1. Fuel / refuel (Ezio, 2026-10-12) — STATUS: theory with a prediction, not tested

**Plain version (the mandi):** a rush only pays while there are people not yet in it who will have to buy later. Traders aren't stupid: they see their losses. A run of winning breakouts recruits everyone into breakout bets, so the fuel is spent and breakouts start failing. A run of failures drives the crowd out (or into fading), so the fuel refills and the next real rush pays. Breakouts and fades are two sides of one cycling coin.

**Who pays:** late buyers who sat out and chase (your exit); faders who bet the day stays quiet and must buy back (your fuel).

**Two clocks:** the slow tide (month trend, T1) persists; the fast waves on top (weeks of breakout success / failure) cycle. Fuel explains why the fast clock reverses while the slow one doesn't.

**Earlier findings it re-explains (all on spent training data, so they are NOT evidence for it, only consistency):**
- run 5 contrarian switching: a small positive edge in all 4 eras at windows 40/80 trades, gone at 160; the random control lane showed none. (Previously dismissed as "no mechanism". Fuel predicts the control shows none: random entries have no crowd behind them.)
- T5: a lane's hot streak is followed by worse trades (z 4.1, 12 of 17 related lanes agree).
- T22: 3 weeks of poor breakout follow-through were followed by BETTER breakout trades (robust on reshuffled histories for brk).
- M6 lead: a fast trade after a fast loss does better.
- probe headline: real multi-week order is slightly mean-reverting relative to its own day-shuffled cousin.

**Cycle length (Ezio):** not one magic number. Use decay (older trades count less, like fading memory), with the fade speed set by a rule from the trailing year's volatility and market behaviour, recalculated as it goes. The rule is written once before any data and never adjusted. Needs ~1 year of warm-up (matches the existing "about a year of evidence before live" rule). Note: the run 5 windows were counted in trades, which already stretch with market activity.

**PREDICTION (Ezio, 2026-10-12 ~22:00), conditional on the CAUSE of high volatility:**
- **Hype-driven high volatility → SHORTER cycle.** The crowd piles in and burns out fast.
- **News / real-event-driven high volatility → LONGER cycle.** A real cause keeps fuel flowing before the crowd exhausts it.
- **Cause label must come from a rule fixed in advance, never from the outcome** ("it was hype because the cycle was short" is forbidden). Draft rule (to be fixed before any test): NEWS = a scheduled release date (central-bank meeting, inflation, jobs) inside the window, OR breadth (US 500 + US Tech 100 + US 30 moving together); HYPE = a volatility jump in one market with neither.
- **Also required:** the effect shows on fresh data; random walks and the control lane show no such relationship.
- **Fails if:** no difference between the two kinds, the order is reversed, or the labels can't be assigned before the outcome.
- **Practical limits:** news-driven high-vol stretches are rare (thin samples); breadth needs the US Tech 100 / US 30 farm.
- **Link:** the same cause classifier is #33's job (fingerprints a: news timing, b: breadth). Build it once, use it for both.

**Limits:** weak effect (contrarian switching was net negative as a stand-alone switch) → expected use is a SIZE TILT, not an on/off switch. We cannot see the crowd directly (no positioning data), only its footprints.

## N2. The gate: when the cycle applies (Ezio, 2026-10-12) — STATUS: design idea

- The cycle holds on normal days. Randomness (a 5,000-guest party) can still spike anywhere; only position size and stops protect against that.
- Cycle mode only when: volatility is normal for that symbol (vol is the most readable state: atr10 precision 78%, lag ~8 days) AND no scheduled news in sight.
- Event / sit-out side: a volatility jump, with direction from the jump day, confirmed by breadth (several markets moving together; needs US Tech 100 / US 30). Known outside the lab, untested here: in indices a vol jump usually comes with falling prices; gold can rise in a panic.
- Open (Ezio): is sit-out a rule or live judgment? A backtest needs at least a crude rule.

## N3. Fade only against-trend breaks (Ezio, 2026-10-12) — STATUS: DEAD on training data (2026-10-13)

- If a breakout WITH the 10-20 day trend tends to follow through (T1), a breakout AGAINST it is the weak one: fade that one, never fade the with-trend break.
- Who pays: people chasing a rush the month doesn't support.
- Never built: the original fade lane had no trend check; Hunt only looked at counter-trend breaks from the riding side.
- Combined design: with-trend break → ride (fast); against-trend break → fade (N3); cycle state (N1, via the shadow breakout/fade pair from sensor_pairs.md) → size tilt only; gate (N2) on top.
- Risk: against-trend breaks are rarer, and T1 says weak before costs; after costs unknown.
- Open (Ezio): pre-register inside the US 500 2015-19 exam, or keep the exam clean and test later on US Tech 100 / US 30. **Decided 2026-10-13: kept out of the US500 exam; goes to US Tech 100 later.**
- **Explore (2026-10-13, training data, explore_results.md):** the fade loses after costs on all six markets (pooled -0.12 R, t -4.1). Against-trend breaks do not reverse (on US500 riding them even beat the coin flip). Dead: it can't fit even its own data.

## N4. The trend option: bet BEFORE the trend (Ezio, 2026-10-13) — STATUS: one design clears its bar on training data (FX / gold / oil only); fresh test not yet possible

**Plain version:** brk and fast say "there is a trend, let's cash in" (reactive). N4 says "there WILL be a trend, I'm putting money down before it shows" (anticipatory). It is closer to buying an option than to trend-following. Accept many losers at face value; a few extreme winners pay for all of them.

**Why it's separate from brk / fast:** the trigger can NOT be price momentum (that would just be an earlier brk). It must be a PRECONDITION that a trend is coming, read before price confirms.

**Where it came from:** the T15 (Turtle) autopsy, 2026-10-13. Turtle had the right philosophy (wide stop, trail, let the tail pay) but its clock was too slow: a 55-day confirmation + 20-day giveback needs trends far longer than the short, soft regimes we measured (straight runs rarely reach 40 days). N4 fixes the clock by entering before confirmation instead of after.

**Two kinds of losers, two exits (Ezio):**
- **"No trend came"** → the thesis expired, price didn't prove you wrong. Exit on a TIME STOP (like an option expiring). These should be most losers and mostly small.
- **"It reversed instead"** → price proved you wrong. Exit on a wide PRICE STOP. This is the big loss.
- **Price-stop rules (Ezio: must be ATR-based so noise doesn't trigger it):**
  - Daily ATR, not M15 (the hold is days to weeks).
  - Placed beyond the STRUCTURE (e.g. the far side of a compression box) plus an ATR buffer, never a fixed distance from entry (old fade-lane lesson: stops a hair past a level get retested).
  - **Compression trap:** if the precondition is compression, current ATR is shrunk by the quiet days, so "N x current ATR" is tightest right before the spring releases. Use a long ATR (e.g. 50-day), the pre-compression ATR, or a floor at a fraction of the long-run ATR. Choose one before any test.
  - Noise grows with about the square root of time: a stop meant to survive a ~10-day wait needs about 3x daily ATR, not 1x. Exact multiple fixed at pre-registration.
- **Winners:** trailing exit only, never a target (T17, T24: capping winners destroys tail edges).

**Who pays:** you are in before the crowd; the late trend-chasers who arrive once the trend is visible (including brk-style traders) are your exit. By N1 that crowd is largest after a quiet or failed stretch, which is why refuel fits as a precondition.

**Open slot 1: the precondition ("a trend is coming").** Candidates, all with hints only from SPENT data:
- Compression: inside days, narrower = better (slope t -3.0); inside days < ~0.4 ATR edge +0.61. Warning: compression predicts a MOVE, not a TREND or a direction (ins is regime-blind, confirmed twice).
- Refuel (N1): after a run of failed breakouts.
- Scheduled catalyst inside the window (shares the cause classifier with N1 / #33).

**Open slot 2: direction.** Options: first break out of the compression (slightly reactive, but at the first tick); slow tide (200-day / T9 macro direction); bracket both sides like ins.

**Scorecard rule:** any candidate filter is judged on TAIL RETENTION (what share of the top-5% winners it keeps), not on win rate or average trade. In a tail-driven lane, a filter that cuts 30% of losers but also one monster winner can be a net loss. (T12 / T16 / T18 history: learned or pooled filters fail; gates change meaning inside filtered populations.)

**Survival constraint:** expect losing streaks longer than brk's 33-48 (earlier signal = more false starts). At 0.5% risk a 45-loss streak is ~20% drawdown while the system is working normally. Fixed fractional sizing only (T5 corollary).

**Prediction (draft, to be fixed before any test):** on fresh data, N4's returns are carried by its top ~5-10% of trades; most losers exit on the time stop and are small; the result vanishes on random walks and on day-shuffled cousins (it needs real multi-day order). Fails if: the edge is gone without the tail, most losers are full price-stop losses, or noise worlds produce the same tail.

**Useful outside measurement (spends no exam data):** each market's trend-length distribution — how long real trends last, and how fat the tail is. This sets the time-stop length per market and tells us where N4 can work at all (gold likely best, EURUSD likely worst, T8). **Done 2026-10-13:** real legs (median 22-28 days) look like random-walk legs (25-32), so the length distribution alone can't set the time stop.

**Training-data look (explore, 2026-10-13; Claude's one design, see explore_results.md):** inside day < 0.4 x ATR20, first daily break within 3 days, stop beyond the box + 1 x ATR50, out at day 10 if below +1R, 3 x ATR50 trail. EDGE +0.33 (t 3.8) pooled against a noise max of +0.08, carried by USDJPY / gold / oil / EURUSD; flat on US500 and GER40. The shape is NOT the drafted one: losers are mostly full price stops, and the time-stop exits are small WINNERS (+0.22R). About 15 trades a year across six markets.

**Why not on indices (Ezio, 2026-10-13, given AFTER seeing the result):** an index is the whole bazaar; gold or oil is one stall (tomatoes, onions). A one-day quiet spell in a single market is one crowd pausing, so the spring is real. An index's quiet day is many components cancelling out, and the index is driven by slower, bigger forces (tax, overall market direction) that a one-day tool can't read. Different kinds of market have different quirks: one trick holding everywhere is not the expectation, so the index misses are not "failures".
- Status: a mechanism for WHERE it works, stated after the result (hindsight-flagged). It does not yet name the payer on gold / oil / FX.
- What it predicts (and could get wrong): N4 shows no edge on ANY index. US Tech 100 and US500 2016-19 were never used for N4, so checking them spends no new data. An edge there would refute the bazaar theory.
- Ezio's call (2026-10-13): no new market exports for now; fresh data is being spent too fast.

**Outside note:** the original Turtle System 1 skipped a 20-day breakout if the previous one would have won. That's T5 / N1 written down in 1983 (outside evidence, not from our spent data).

## N5. Flat means undecided: don't time out a flat trade (Ezio, 2026-10-13) — STATUS: theory with a spent-data hint, to be tested on fresh data

**Plain version (Ezio):** a trade that's flat at midday hasn't been decided yet. A recovery is still possible, and so is the loss. If you time it out because it's flat, you never wait for the answer either way. So a flat trade stays open until the close; only the market decides it.

**Who pays (Claude, from the timing):** US money arriving. On gold, a flat-at-2h fast trade's afternoon gain comes mostly before the NY stock open, peaking 13:00-14:00 London: the COMEX gold open (08:20 NY) and the US data releases (08:30 NY). London's morning set a direction that wasn't priced yet; the late, need-driven US flow finishes it. (Ezio's first guess, "pure chaos / a loss isn't real until it hits", was refuted: the mirror trades lose in the same afternoons, so the gain follows the morning's direction.)

**Spent-data hint (gold fast, NOT evidence; see fast_giveback.md):** flat at 2h → rest of day +0.36 R (t 2.7), positive in all 3 eras; mirror -0.24. Up at 2h → ~0 (already priced). Down at 2h → +0.27, unreliable (flips by era).

**Explore (2026-10-13, training data):** gold flat group +0.42 (t 2.9), mirror -0.25, all 3 eras positive. USDJPY flat +0.14 (t 1.4), also peaking at 13:00 London; book markets without gold +0.11 (t 1.5), positive in all 3 eras. The payer may be US data / US money on more than gold.

**What it implies for rules:** no midday time-out for flat trades; "cut losers at midday" has no support; "lock in early winners" is R-neutral (a risk tool at most).

**Prediction (to fix before the test):** on fresh gold data (2022-23 sealed, if Ezio opens it), flat-at-2h fast trades gain in the afternoon, and the gain concentrates in the 13:00 London hour; mirror trades show none; on US holidays the effect is absent. Fails if: flat trades' afternoon ≤ 0, or the gain is spread evenly with no US-hour peak, or the mirror shows the same.

## Background from the retrospective (2026-10-12)
- The original fade lane failed because: stop a hair past the fake break's extreme (re-tests stop it out), wrong clock (15-min poke of a one-night box vs Turtle Soup's 20-day daily break), and these markets snap back little. It left a hint: a breakout that survives a shake-out is stronger (= #33's "hold" fingerprint).
