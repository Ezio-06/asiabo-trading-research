# Ladder trade: PRE-REGISTERED SPEC (Ezio + Claude, 2026-10-10 17:00, before any test)
**Idea (Ezio):**
- Enter small early in a trend and bank each rung at a modest target.
- Re-enter while the 20/40/60-day trend still agrees, sizing each rung by how long the trend has proven itself.
- Stop escalating near trend exhaustion.

**Pattern it attacks:**
- The switch is late (T4: most trend profit comes early).
- brk depends on rare huge winners (T17).

## Rules
- **Trend-day counter (per market, known at the start of each day):** consecutive days with 20-day straightness >= 0.30 AND the 20-day move in the same direction.
  - Resets to 1 when either breaks ("trend over").
  - FORCED back to 1 after day 60, so trends longer than 60 days are re-entered small and re-escalated.
- **Gates for any rung:** the 20-, 40- and 60-day net moves all point the trade's way.
- **Size by counter day c (multiplier of brk's normal risk):**

  | Counter day | Size |
  |---|---|
  | c <= 2 | 0 (no trade) |
  | c = 3 .. 40 | rises linearly 0.25 -> 1.00 |
  | c = 41 .. 49 | 1.00 -> 0.85 (minor) |
  | c = 50 .. 59 | 0.35 (sharp drop) |
  | c = 60 | 0, then the forced reset |

- **Rung 1:** brk's normal entry signal (the frozen brk lanes: main2 box, orb30 / orb60 range, pdh2 mid, retest2), if the gates hold and size > 0. One ladder per market and direction at a time.
- **Each rung:**
  - stop = brk's stop distance at rung 1
  - target = entry + 1.5 daily ATR
  - exit at the close if neither is hit within 10 trading days
- **Next rung:** when a rung hits its target, the next rung opens at the next bar's open IF the gates still hold and size(c) > 0 on that day. A trend-over blocks new rungs; an open rung keeps its own stop / target.
- **Costs:** real (commission + recorded spread + swap), each rung charged. Edge vs a coin flip computed per rung (mirror).

## Comparisons (fair = same average risk)
1. brk today (5-day chandelier, size 1).
2. brk with the er40 switch.
3. The LADDER.

Metrics:
- net R per unit of risk
- R per year scaled to the same total risk as brk
- edge
- max drawdown in R
- share of each trend captured
- loss on the final rung of each ladder

## Worlds
- **Regime synth (known truth, d = 0.25):** expect the ladder to beat brk per unit of risk in momentum spells and lose less in snap-back.
- **NEW "aging" synth world:** momentum fades over the first 70% of each spell, and the last 30% REVERSES. Expect the day-50 / 60 taper to cut the final-rung losses versus an un-tapered ladder (shown alongside as a control).
- **Real data, EXPLORATORY only** (eras spent): ladder vs brk, and brk results by trend day.
- **Final verdict on fresh data.**

**No tuning of the 40 / 50 / 60, the 1.5 ATR target or the 10-day limit after seeing results.**

## Cloud preview on the fake random-walk market (2026-10-10 17:15, BEFORE the PC run)
- **The taper almost never activates:** runs of 20-day straightness >= 0.30 rarely last past 20-40 days, so taper vs no-taper came out nearly identical.
- **Regime synth:** the ladder beats brk today per unit of risk (+0.61 vs +0.22) but trails the er40 switch (+0.84).
- **Aging synth:** ladder and switch about tie (+0.10 / +0.14), both above brk (-0.19).
- **Target hit rate:** 20-36%; the last rung of each ladder averages about -1R (a stop-out, by construction).
- **Built:** make_synth --aging 1; asiabo_ladder.py; run_18_ladder.bat.

## RESULT (PC run 2026-10-10 17:33, 6 synth worlds + real; all 7 ok; report: claude vision\ladder.txt)

| World | brk today | brk + er40 switch | LADDER | ladder no-taper |
|---|---|---|---|---|
| Regime synth: net per risk (t) | +0.31 (+4.9) | **+0.82 (+8.7)** | +0.66 (+9.5) | +0.69 (+10.8) |
| Regime synth: R/yr at brk's risk / max DD | +55 / 159 | **+145 / 125** | +117 / 141 | +122 / 124 |
| Aging synth: net per risk (t) | -0.17 (-2.6) | +0.10 (+1.1) | +0.11 (+1.2) | +0.11 (+1.2) |
| Aging synth: R/yr / max DD | -29 / 723 | +16 / 362 | +18 / 250 | +18 / 250 |
| Real (exploratory): net per risk (t) | +0.10 (+1.4) | **+0.32 (+2.0)** | +0.06 (+0.4) | identical |
| Real: R/yr / max DD | +15 / 89 | +51 / 81 | +9 / 165 | identical |

**Against the pre-registered expectations:**
1. **Ladder beats brk per unit of risk in the regime synth: YES** (+0.66 vs +0.31). But the simpler switch beats the ladder (+0.82, more R/yr, smaller drawdown).
2. **Ladder better than brk IN momentum spells: NO.** Per trade in momentum: ladder +0.90 vs brk +1.31. The 1.5 ATR target cuts off the big runners that brk's chandelier keeps (T17 again).
3. **Ladder loses less in snap-back: only by trading less** (163 vs 1535 trades); per trade it loses slightly more (-0.79 vs -0.66).
4. **Taper cuts final-rung losses in the aging world: NOT TESTABLE.** Taper and no-taper are identical: the counter almost never reaches day 40 (brk had 15 entries at c>=41 across 3 aging worlds, 0 on real data). The 40/50/60 part of the rule never fires.
5. **Last rung:** about -1.1R per ladder everywhere (each ladder ends on a stop, by construction); targets hit 22-35%.
6. **Real data (exploratory):** the ladder is the WORST variant (+0.06, t 0.4, deepest drawdown 165R). Rungs 3+ lose (-0.23, -0.48).
7. **brk by trend age:** in the regime synth older trends pay more (c0-2 -0.11 ... c50-60 +1.61). On REAL data there is no age pattern (c0-2 +0.13, c3-10 -0.03, c11-20 +0.10, c21-40 +0.18). Real trends are short and soft; trend age does not grade brk trades the way the synth suggests.

**Verdict:** the ladder is NOT adopted. It never beats the plain er40 switch, the taper never activates, and on real data it is worse than brk alone. brk stays shelved. Per the no-tuning rule, the 40/50/60, 1.5 ATR and 10-day settings are not adjusted to rescue it.
