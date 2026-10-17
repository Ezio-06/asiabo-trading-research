# Sensor pass over the lane ideas (Claude, 2026-10-11): applying #32 "trades tell us what's going on"

Source list: lane_ideas_30.md. Nothing here is tested. This is a design map.

## 1. Mirror vs flipped as sensors
- **A mirror carries NO extra information.** It is the exact inverse of the original (same two levels, roles swapped), so its outcome is fully determined by the original's. It changes the payoff shape, never what we learn. It is only usable as a trade, and only when the original has a natural fixed target (a mean or gap level).
- **A flipped trade is a real second probe.** Same trigger, opposite direction, its own stop. Together with the original there are THREE joint outcomes:
  - A wins = continuation
  - B wins = reversal
  - both lose = chop
- So **every flipped pair, run in shadow on the same trigger, is a 3-state regime detector** at zero cost. That is the core design.
- **Exits as labels.** Every lane in a pair gets one exit per outcome:
  - price stop = the other side's thesis won
  - time stop = chop / nothing happened
  - TP or trail = our thesis won

## 2. Rules that apply to every pair
- **Same-trigger trap.** Both sides fire on the same bar, so the current pair's outcome is ONE event. A sensor may only read pairs that resolved BEFORE the new trigger, with overlapping windows excluded.
- **Sides, not lanes.** Comparing both sides of the SAME trigger separates "this trigger is bad lately" from "this direction is bad lately". Lane-P&L form (T5) can't make that split.
- **Honest risk.** At its core this is still a reading of recent results. T5 / T22 say streaks reverse at the weekly scale. So:
  - the sensor test must report the direction (persistent or contrarian)
  - it must beat a shuffled order
  - it must beat er40
- **Cost.** Trading both sides is never the plan (the both-lose third costs double). Shadow both sides, trade at most one.

## 3. The map
**Tags:**
- **F** = flipped counterpart (new)
- **L** = an existing or listed lane is the counterpart
- **M ok** = a mirror is also tradable (fixed target)
- **none** = no useful opposite; the lane serves only as a background sensor

| # | Idea | Counterpart | What the pair's joint outcome reads |
|---|---|---|---|
| 1 | Daily turtle soup | L: brk / swing2 (the breakout holds) | Breakouts holding vs failing. brk's quick failures feed soup; soup's stop-outs mean momentum is on |
| 2 | Post-shock reversion | L: #9 crash continuation. M ok | Do shocks revert (normal) or continue (crisis)? A crisis detector |
| 3 | Failed-shadow reverse | L: brk / fast (it IS the flip of a failure) | Already a sensor consumer; speed of failure is the feature |
| 4 | Blow-off fade | L: #20 range-expansion follow-through (same trigger) | Expansion at an extreme: exhaustion vs ignition |
| 5 | Weekly overextension fade | L: #26 weekly breakout | Weekly-scale momentum vs reversal |
| 6 | EURUSD Bollinger reversion | F: Bollinger breakout (a close outside 2 sigma continues). M ok | Range regime vs breakout regime in FX |
| 7 | London-open reversal of the Asian move | F: London continues the Asian move | Is the Asian flow informed lately? |
| 8 | FX fix reversal | F: post-fix continuation. M ok | Fix flow mechanical vs informed |
| 9 | Crash continuation short | L: #2 | Same pair as #2 |
| 10 | Gold flight to safety | F: gold falls WITH stocks ("dash for cash", e.g. March 2020) | Type of risk-off: safe haven vs liquidation. Decides which crisis legs are live |
| 11 | Yen safe haven | F: USDJPY rises despite risk-off | Same reading as #10, from the yen side. Shares the sensor with #10 |
| 12 | Vol-target re-leverage | F: second leg down (the vol spike returns) | Panic over vs panic resuming. Gates #9 |
| 13 | US → Germany lead-lag | F: fade the gap (Germany over-reacted). L: #23 | Cross-market under- vs over-reaction |
| 14 | Germany → US | F: US fades Germany's move | Same pair family as #13 |
| 15 | EURUSD → gold lag | F: gold moves against the dollar signal (own flows) | Gold coupled to USD vs decoupled. Decoupled = switch off #10 / #29 |
| 16 | WTI shock spillover | F: the spillover reverts | Is oil driving macro lately? |
| 17 | Shock by hour | Internal: continue at news hours / revert in quiet hours | The pair IS the test; if news-hour continuation fails, the information regime changed |
| 18 | NFP / CPI drift | F: knee-jerk fade (the first 15 min reverses) | Release digestion: drift vs overreaction |
| 19 | Multi-day squeeze breakout | F: fade the first break of the squeeze (a false break). L: #1 | True vs false release from compression |
| 20 | Range-expansion follow-through | L: #4 | Same pair as #4 |
| 21 | Opex-week pinning | Internal: pin-week fade vs release-week trend | Pin-week fade failures → is the release coming early? |
| 22 | Vol-scaled TS momentum | none (always in; the flip is multi-year reversal, too slow) | Background regime read for everything else |
| 23 | Cash-open gap by size | Internal: fade small / go big. M ok on the fade (the gap level is the target) | Where the fade/go boundary sits lately. DON'T tune it; read it |
| 24 | Gold round numbers | Internal: break-and-run vs reject | Stop clusters being run vs defended |
| 25 | 52-week-high anchoring | F: fade at the 52-week high (resistance) | Anchoring drift vs resistance |
| 26 | Weekly breakout | L: #5 | Same pair as #5 |
| 27 | US500 / Germany 40 spread reversion | L: #28 relative momentum (exact flip on the same spread). M ok | Indices coupled vs diverging. The cleanest pair on the list |
| 28 | Index relative momentum | L: #27 | Same pair as #27 |
| 29 | Gold / USDJPY divergence | F: the divergence widens (decoupling) | Shares the coupling sensor with #15 |
| 30 | Trend-end lane | L: brk (the trend continues) | Same as #31's labels |
| 31 | Mirror dip | L: dip (the end of the pullback) + brk (continuation) | price stop = trend on, time stop = chop, TP = correction |

## 4. The sensor families (which pairs measure the same hidden state)
- **Momentum vs reversal** (the state brk needs, read faster than er40?): brk / fast ↔ 1, 3, 4 / 20, 5 / 26, 19, 25, 30, 31.
- **Shock regime** (shocks revert vs continue = normal vs crisis): 2 / 9, 12, 16, 17, 18.
- **Risk-off type** (safe haven vs dash for cash): 10, 11.
- **Cross-asset coupling** (markets move together vs decouple): 13, 14, 15, 27 / 28, 29.
- **Session flow** (uninformed flow reverts vs continues): 7, 8, 23.
- **Calendar mechanics:** 21.

Several lanes in one family = several independent probes of the same state. A family-level read (a vote of the resolved pairs) should be steadier than any single pair. That is a TESTABLE claim, not an assumption.

## 5. First pairs worth testing (prediction before results)
1. **#27 ↔ #28 (spread reversion vs relative momentum):** exact flip, daily, frequent, no calendar needed. Prediction: coupling persists for weeks, so the recent pair outcome predicts the next one (persistent).
2. **brk ↔ #1 soup:** the trade lists already exist for brk. Prediction: fast failures of brk predict soup wins; the brk P&L streak does not.
3. **#2 ↔ #9 shock pair:** a crisis detector. Prediction: few events; evidence will be thin, so judge it on a synth stress world first.
4. **#4 ↔ #20 same-trigger pair:** prediction: a both-lose (chop) share above the random-walk 1/3 in quiet years.

## 6. Probes by timescale (added 2026-10-11, Ezio's question)
A probe's clock = its hold time. That clock sets both its lag and how many readings it gives per year.

**Dead lanes are valid probes.** Shadow is free, so a probe only needs to be INFORMATIVE, not profitable. The graveyard becomes the sensor array: turtle55, swing2, pdh2, main2, orb, gao, trend2, range2, ins, brk, dip short.

| Scale | Readings / market / yr | Existing lanes (incl. dead) | Listed ideas | Reads | Gap |
|---|---|---|---|---|---|
| **Intraday** (resolves the same day) | ~150-250 | fast (orb30 / main2), orb, gao, trend2, range2, ins | 7, 8, 13, 14, 15, 17, 18, 23, 24 | intraday momentum vs reversion; session flow informed?; cross-market coupling | richest scale; costs don't matter for probes |
| **Daily** (1-5 days) | ~30-100 | dip (~4 d), pdh2, brk (5-day trail), dip short | 1, 2/9, 3, 4/20, 6, 10/11, 16, 19, 31 | short-term momentum vs reversal; shock regime; risk-off type | well covered |
| **Weekly** (1-4 weeks) | ~15-40 | swing2 (20-day Donchian) | 5/26, 12, 21, 25, 27/28, 29 | weekly momentum vs reversal; panic over/resuming; index coupling | thin outside indices; no weekly probe for FX / WTI beyond swing2 |
| **Monthly** (1+ months) | ~6-12 | turtle55 (dead as a trader, fine as a probe) | 22 | the macro trend direction (T9) | thinnest: only trend probes, no monthly reversal probe. ~100 readings per market in the training data → slow to validate |

### Notes
- **Probes vs indicators by scale.** At the monthly scale a probe resolves ~12x a year, so an indicator (er40, the 200-day average, the 3-12 month return) reads the same state with less lag noise. Probes earn their place at the SHORT scales, where many resolve quickly. Prediction: probes beat indicators intraday / daily, and tie or lose at monthly.
- **Nesting trap.** A monthly probe's outcome is built from the same prices as the daily probes inside it, so cross-scale features are correlated by construction. Test each scale's sensor against the next lane's trade separately first, then jointly, with overlapping windows excluded.
- **The cross-scale question worth testing.** Does a probe at one scale predict lanes at another?
  - Example: fast (intraday) when the weekly probes read momentum vs reversal.
  - Example: brk when intraday probes read momentum, which is the hope of reading brk's regime faster than er40.
  - That is "multi-timeframe alignment" made testable. Prediction (Claude): the shorter probe predicts the longer lane only weakly; the longer probe gates the shorter lane better (slow states condition fast trades).
- **Readings per year set the validation budget.** An intraday sensor can be confirmed within the training data. A monthly one barely can; it needs the sealed exams or new data.
