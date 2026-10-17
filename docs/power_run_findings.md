# Power run (asiabo_lab.py power), 2026-10-08: findings

**Setup:** real costs; every trade compared against a coin flip with the same timing, stop, exit and costs. OLD = 2014-21, NEW = 2024+.

## The power gap, measured
- **Breakout direction has real power:** main2, orb30/60, pdh2 and trend2 beat the coin flip by +0.03 to +0.10R a trade. It shows in both periods, with t of 2-4 in the old years.
- **Costs are bigger than that edge:** the coin-flip result is about -0.08 to -0.2R a trade, so most cells stay net negative.
- **Exits were not the leak:** the exit test (A) moved net results only slightly.
- **No direction power** in fades, range, vwap, exhaust (negative edge, t down to -5), the gao half-hour effect, range2, or swing2 (daily Donchian loses with or without pyramiding; swap is a big drag).
- **rsi2 long on US500** is +0.8R on 25+15 trades. Interesting, but the sample is tiny.

## The one consistent cell family (chosen after looking: treat as a lead, not a result)
- **Gold, main2 (overnight box, stop orders in the first 3h, stop at the far side), trail exit:** net positive in all 4 eras (+0.023 / +0.022 / +0.049 / +0.057 R), edge +0.08 to +0.10 (t 1.7-2.7 each era). About +6 R a year.
- **Gold, pdh2 (yesterday's high/low stop order, stop at the middle of yesterday), trail exit:** edge positive in all 4 eras, net positive in 3.
- **USDJPY pdh2 trail:** edge positive in all 4 eras (t about 2); net positive in 2.
- **NR7 as a filter on pdh2:** edge +0.08 in both periods (t 2.2 / 1.6).

## Open issues
- Gold's commission is ASSUMED ($45 per million). Gold is where the net-positive cells are, so the gold symbol sheet is now the most important missing input.
- **EURUSD / USDJPY ORB have only 176 trades in 2024+, against about 2,040 in the old years:** probable data coverage or timestamp issue around the London open in the newer FX data. Check before trusting any FX ORB number.
- US500 has only 2020-21 in the "old" period.

## Rerun 2026-10-08 (real gold costs, FX close bug fixed, per-signal dossier + month view)

### When pdh2 works
pdh2 is yesterday's high/low breakout with a 5-day trail. It works in TREND MONTHS: the market moved 3+ daily ATRs net, with straightness 0.3+.

| Market | Trend months: share good | Trend months: net R/month | Other months: net R/month |
|---|---|---|---|
| Germany 40 | 71% | +8.1 | -4.1 |
| USDJPY | 57% | +7.0 | -3.3 |
| Gold | 56% | +5.7 | +0.0 |
| US500 | 79% | +5.0 | -6.5 |
| WTI | 54% | +2.8 | -3.0 |
| EURUSD | 45% | -1.2 | -6.0 |

- Trend months made +667R; all other months lost about -1,700R.
- Month-to-month persistence is about zero: a good month is followed by a good month 39% of the time, after a bad month 37%. "It worked last month" is not a usable signal.

### Signals (each bucket compared with the rest of its own lane, in each of 4 eras, cut points from 2014-21)
- **pdh2, price near the trade-direction end of its 20-day range (pos20_with = high):** better in all 4 eras (++++). +0.146R old (t 3.1), +0.144R new (t 2.0), on 5 of 6 markets; theory agrees. The opposite bucket (near the other end) is worse in all 4 eras: -0.198R old (t -4.4), weaker in 2024+.
  - The backward 20-day trendiness read (ER20) does NOT predict pdh2 (it flips by era). Trend months are only visible in hindsight; being at the edge of the 20-day range is the in-time detector found so far.
- **pdh2 with the 50-day trend:** ++++, 6 of 6 markets, +0.084 / +0.053R (t 1.9 / 0.8).
- **Old nr7 lane, yesterday's range low (compression):** ++++, +0.15R in both periods (t 2.8 / 2.0), 5 of 6 markets; Crabel's theory agrees. Net +0.097R a trade.
- **swing2 with the 50-day trend:** ++++, +0.40R advantage in both periods, 5 of 5 markets. But swing2 is still net negative overall (costs and swap).
- **main2 on Fridays:** worse in all 4 eras, on 0 of 6 markets (t -2.1 / -2.0); skipping Fridays saves about 11.6R a year. There is no prior theory for this, so it needs checking.
- **Reversals (vwap, exhaust) at low volatility:** worse in all 4 eras (theory agrees). Skipping that bucket saves 31-44R a year.
- **Base rate:** 182 of 1,157 buckets with data in all four eras had the same sign in every era. Coin flips would give about 145. Individual buckets are judged on theory, market spread and strength, not on this count.

### Data notes
- ATR% month averages have outliers (WTI around April 2020, near-zero and negative price): ignore that column's means.
- FX opening-range trades are fixed: 697 in 2024+, against 176 before.

## Rerun 3, 2026-10-08 (detectors, gates, per-signal luck check)

### Spotting trend months in advance: NO
- All four detectors (edge20, donch5, ma, er10) catch trend months, raise false alarms and point the right way at the same rates as on a fake random-walk market (e.g. edge20 78% by day 10, 31% false alarms, 33% precision, against a random yardstick of 72% / 34% / 33%).
- A trend month does not make the next month more likely to trend (18-35% after one, against 19-27% otherwise).

### Filtering trades by the detector: YES for breakout lanes ("trade only when it agrees with the trade's direction")
| Lane + detector | Net R/trade, old | Net R/trade, new | Net R/year, old | Net R/year, new | Edge t, old |
|---|---|---|---|---|---|
| pdh2 + er10 | +0.046 | +0.125 | +8.5 | +29.9 | 3.0 |
| main2 + edge20 | +0.041 | +0.065 | +5.1 | +12.6 | 2.7 |
| orb30 + er10 | +0.052 | +0.028 | +8.6 | +5.8 | 3.0 |
| orb30 + edge20 | +0.019 | +0.046 | | | |
| retest + edge20 | +0.028 | +0.124 | | | |
| nr7 + edge20 | +0.030 | +0.021 | | | |

- The same short-term momentum detectors help across the breakout family. The 50-day (ma) filter is weaker.
- **The catch:** most of a trend month's profit comes BEFORE a detector turns on. pdh2 made +644R in trend months; only +177 to +320R of that came after the detector's first signal.

### Luck check (per-signal p, false-discovery q, related-lane agreement, theory)
Out of 1,202 buckets: 8 REAL, 3 LIKELY REAL, 3 REAL BUT AGAINST THEORY, 4 PLAUSIBLE, 17 WEAK, 1,167 LIKELY LUCK.
- **REAL: trade at the trade-direction edge of the 20-day range.** pdh2 z +3.7 / -3.9, gao +3.9; 16 of 19 related lanes agree.
- **REAL: trade with the 50-day trend** (gao, swing2).
- **LIKELY REAL: nr7 lane after a narrow prior day** (z 3.4).
- **REAL BUT AGAINST THEORY: lane form mean-reverts.** pdh2 after its last 20 trades went well: -0.24R net. After they went badly: +0.05R (z 4.1, 12 of 17 related lanes agree). Hot streaks predict worse trades: never size up after a hot streak (relevant to the house).
- **PLAUSIBLE: vwap fades in low volatility lose** (skipping them saves about 44R a year).

## Run 4, 2026-10-08: the earners (each lane and filter variant switched live on its own last 80 finished trades)
- **Live book:**

  | Period | Net R/trade | Edge vs coin flip | Edge t | Net R/year |
  |---|---|---|---|---|
  | 2014-17 | -0.003 | +0.091 | 5.1 | |
  | 2018-19 | -0.136 | -0.032 | | |
  | 2020-21 | -0.077 | +0.010 | | |
  | 2024+ | +0.011 | +0.040 | 2.8 | +32 |

  Positive months 17-44%, drawdowns 130-460R, 19-25 months under water.
- **Switching on recent results does not work:** it chases noise. This fits the finding that lane form mean-reverts. The random control lane was live 12.7% of the time, below the 21% it reached on the random market.
- **Reversal bar:** reversal lanes reached their hard bar only 0.3-2.5% of the time and did nothing useful when they did.
- **Static detector filters on the breakout family** (all lanes pooled, no switching): edge20 -0.027R/trade old, +0.049R new (+114 R/year new); er10 -0.020 old, +0.035 new. donch5 and ma are negative.
- **Positive in both periods, n 100+ (chosen after the fact):** main+edge20, main2+edge20, nr7+edge20, orb30+edge20, orb30+er10, orb60+er10, pdh2+er10, retest+edge20, retest+er10.

## Run 5, 2026-10-08: books side by side (H0-H6)
| Book | 2014-17 net / edge | 2018-19 | 2020-21 | 2024+ |
|---|---|---|---|---|
| H0 base (rebuilt breakouts, all) | -0.060 / +0.045 | -0.094 / +0.010 | -0.047 / +0.044 | -0.019 / +0.038 |
| H1 filtered (edge20 or er10) | +0.001 / +0.090 | -0.136 / -0.014 | -0.037 / +0.037 | +0.026 / +0.057 |
| **H2 wide stop + 5-day chandelier, filtered** | **+0.058 / +0.150** | **-0.167 / +0.010** | **+0.105 / +0.157** | **+0.047 / +0.117** |
| H3 learned score | -0.083 / +0.016 | -0.130 / -0.018 | -0.076 / +0.003 | -0.058 / -0.005 |
| H4 score + cooldown | same as H3 (no help) | | | |
| H5 contrarian W=40 | -0.075 / +0.043 | -0.040 / +0.041 | -0.080 / +0.029 | -0.060 / +0.017 |

(each cell: net R / edge vs coin flip, per 1R risked)

- **H2 is the first book with a positive edge in every era.** It is net positive in 3 of 4 eras: +57, -186, +135 and +70 R a year. The yardstick on the fake random market had no book positive in every era.
- **H3 learned score failed:** it took nearly every trade. The weights stayed tiny and selected nothing, so the threshold needs to be relative (only the top-scoring days).
- **Win-streak cooldown:** no effect.
- **Contrarian switching:** a small positive edge in all 4 eras at W=40/80, gone at W=160, net negative everywhere. The control lane alone showed no effect, so it is not a measurement artifact. Its "hot" mirror is worse. Verdict: a real but weak lane-form mean reversion. Use it as "don't push after a hot streak", not as a switch.
- **H6 weights still alive at the end:** late hours (5h+ after the open) negative, Friday and Sunday negative; everything else demoted to about 0.

## Run 6, 2026-10-09: Part J (per-trade odds, asymmetry/capital, new contenders)

### J1: one learned P(win) per trade does not work
- **Breakouts:** the actual win rate moves only from 33% to 36% across the predicted deciles. The top-minus-bottom edge is -0.01 / -0.07 (t -0.7 / -2.5), the wrong way round.
- **Reversals:** the win rate climbs steadily from 35% to 42% in 2014-21, but net and edge don't follow, and 2024+ is flat.
- **"Skip the bottom 10%"** vs a random 10%: breakouts -9 / +109R, reversals +137 / -83R. The sign flips between periods.
- **Verdict:** pooling every read into one learner drowns the few real loss-predictors. Keep those as separate hard filters.

### J2: asymmetry
- **Breakout lanes with 5-day exits** (orb30, orb60, pdh2, retest2, main2):
  - Win rate 17-28%. The best 10% of trades add +0.5 to +0.8R per trade; without the best 5% they lose -0.4 to -0.7R per trade.
  - Losing streaks of 33-48 trades.
- **Index dip-buys:**
  - rsi2 long: 65% win, +0.058 net, Kelly 2.5%, streak 4.
  - dip3 long: 64% win, +0.064 net, Kelly 3.25%, streak 7.
  - These are the only lanes positive unfiltered across all data.
- **Old "swing, close exit":** Kelly hits the 10% cap. That is an artefact: its losses are -0.20R on average, so R is not the true risk. Ignore it.
- **Minimum position size too big at $10k / 0.5% risk:** Germany 40 on 76% of trades, US500 12%, gold 2%, FX 0%.

### J3: new contenders
| Contender | Net, 4 eras (R/trade) | Edge, 4 eras | Corr with H2 | Verdict |
|---|---|---|---|---|
| dip3 long | -0.06 / -0.11 / +0.06 / +0.26 | +0.08 / +0.03 / +0.17 / +0.35 | -0.12 | long-term contender, indices + USDJPY |
| dip3 short | -0.59 / +0.07 / -0.24 / +0.05 | mixed | 0.00 | no |
| inside day, close exit | -0.02 / +0.01 / +0.14 / +0.03 | +0.10 / +0.11 / +0.17 / +0.08 | +0.05 | short-term contender (best of 6 variants) |
| inside day, 48h / 5d | 2018-21 good, 2014-17 and 2024+ bad | | +0.20 / +0.30 | no |
| turtle 55/20 | -0.73 / -0.57 / -0.33 / -0.29 | | | dead |

**Per market:**
- **rsi2 long:** US500 +14/+19, USDJPY +15/-2, Germany 40 -3/+7.
- **dip3 long:** US500 +9/+9, Germany 40 +4/+12, USDJPY +2/+3.
- **inside day:** USDJPY +48/+2, WTI +71/-19, EURUSD -103/-24.

## Run 7, 2026-10-09: Part K, the OMEGA path (shadow-trusted loss gates, three sleeves, dedupe, Kelly sizing)

### Gates failed in this book; the scorecard worked
- Inside the deduped H2 breakout sleeve, trades the gates FLAGGED often did BETTER. Examples:
  - far side: +0.24 vs +0.03 (2014-17), +0.41 vs +0.08 (2024+)
  - Friday: +0.41 vs +0.03, +0.45 vs +0.16
- The shadow scorecard pushed trust to about 0, so OMEGA ≈ gates off ≈ random gates.
- **Gates always fully trusted** (no scorecard) cost a lot: 2020-21 +8.9 vs +40.2 R/yr, 2024+ +25.4 vs +63.2.
- **Lesson:** loss signals found on raw lanes do not carry over into a population already filtered by the momentum detector. Being at the far side of the range while momentum agrees probably means a pullback inside a trend, which is good, not bad. A signal's meaning depends on the filter in front of it.

### The real gain came from dedupe + the T8 market list
- brk sleeve, gates off, one position per market per direction:
  - net +0.021 / +0.021 / +0.047 / +0.230
  - edge +0.135 / +0.189 / +0.036 / +0.162
  - Net positive in all 4 eras for the first time. +2.7 / +3.0 / +8.8 / +47.7 R/yr.
- All-markets check: 2018-19 goes to -0.069. The market list is hindsight (T8).
- **ins:** -0.05 / +0.02 / +0.16 / +0.05 net, edge positive in all 4 eras.
- **dip:** +0.14 / -0.09 / +0.43 / +0.39, but only 15 and 14 trades before 2020 (US500 / Germany 40 data). Correlation with brk -0.22, with ins -0.38.
- **OMEGA in R:** -0.018 / +0.035 / +0.112 / +0.171 net; edge +0.11 to +0.18 in all eras. -4 / +8 / +35 / +61 R/yr.

### Money
- $10k: -1.2 / -2.6 / +2.2 / +24.7 %/yr, drawdowns 8-23%.
- $100k: 2020-21 is -0.5%/yr, even though the R book made +35 R/yr.
- **Suspect:** trailing-Kelly sizing raises risk after good stretches and cuts it after bad ones. That is "size up after a hot streak", which T5 says loses.
- **Next:** fixed-risk vs Kelly, plus a count of the trades the open-risk cap skipped.

## Run 8, 2026-10-09: omega mode, sizing by state at the SAME average risk (K5)
- **Kelly was the money leak.** Timing-weighted R/yr, fixed vs kelly: -4.0/-1.6, +8.3/-9.4, +34.5/-8.5, +60.9/+66.6. Trailing Kelly sizes up after good stretches (T5) and gave away about 40 R/yr in 2020-21.
- **Fixed risk** (brk 0.25%, ins 0.25%, dip 0.5%), $10k:

  | Era | %/yr | Max drawdown | Months under water |
  |---|---|---|---|
  | 2014-17 | +0.7 | 19% | 26 |
  | 2018-19 | +3.0 | 7% | 11 |
  | 2020-21 | +12.2 | 5% | 6 |
  | 2024+ | +16.7 | 4.4% | 7 |

  Positive in all 4 eras. At $100k: -1.5 / +1.5 / +11.1 / +18.5. At $10k, 120-290 trades per era were too small to take (Germany 40 / US500).
- **streak2 / streak3** (Ezio's defensive state after wins): no better than fixed.
  - R/yr: -3.6 / +10.8 / +30.8 / +57.8 vs fixed -4.0 / +8.3 / +34.5 / +60.9.
  - Drawdowns slightly worse (21.6% vs 19.3%, 7.3% vs 5.1%).
  - In brk, trades in defensive state were worse in 3 of 4 eras, but only 14-56 trades each: within the noise.
- **form20** (defensive while the last 20 trades are positive): beats fixed in 3 of 4 eras on R/yr (+19.1 vs +8.3, +39.9 vs +34.5, -0.4 vs -4.0) but loses in 2024+ (52.9 vs 60.9). Money is mixed, and the 2014-17 drawdown is deeper (26.8%). Consistent with T5, but within the random-market yardstick.
- **The 6% open-risk cap never bound.**

## Run 9, 2026-10-09: the intraday earner (fast) + canaries (K6)
- **fast** (orb30 + er10, main2 + edge20, close exit, brk markets, 0.10%):
  - net +0.010 / +0.019 / +0.243 / +0.145; edge positive in all 4 eras (+0.15 / +0.09 / +0.17 / +0.06).
  - 125-220 trades a year.
  - Correlation +0.47 with brk (same entries), +0.03 with ins, -0.13 with dip.
  - At $10k most of its index trades are too small to take (592 skipped in 2024+).
- **Omega with fast, fixed risk:**
  - $10k: +0.5 / +2.6 / +15.1 / +18.7 %/yr, drawdowns 21.7 / 7.9 / 5.6 / 3.0%.
  - $100k: -2.0 / +1.7 / +14.9 / +21.9.
- **Canaries as a sizing rule FAILED.** Trades taken in alarm weeks were usually BETTER:
  - brk 2014-17: +0.89 (68) vs -0.11
  - fast: better in all 4 eras (tiny n)
  - At the same average risk the rule gave -1.4 vs +0.5 %/yr in 2014-17 and about equal elsewhere.
  - Alarms are rare: 0-3% of weeks for breakouts, never on a dip trade.
- **Same lesson as T5 at the weekly scale:** a weak few weeks for the mechanism is followed by better trades, not worse.
- **Out of sample (2024+):** the breakout canary false-alarmed only 1.4% of weeks, so it is a quiet monitor.
- **Keep the canaries as a dashboard only, with no trading action.**

## Synthetic batch 1, 2026-10-09 (frozen omega book; 21 of 23 jobs: real, identity, 3 seeds each of shuffle / cosmetic / dayshuffle / vol_up / vol_down / trend_up, costly seed 1)
**Note:** generator v2 re-joined prices after any >8-day data hole, so 2014-19 synthetic numbers carry a small artifact (identity did not match real there). 2020-21 and 2024+ identity matched exactly. Fixed in v3.

**Corrected real reference** (deterministic lab): $10k +0.8 / +1.0 / +15.8 / +18.6 %/yr, drawdowns 23 / 11 / 6 / 3%.

### 1. The direction power survives reshuffling
Whole book, edge vs coin flip:

| Setting | 2014-17 | 2018-19 | 2020-21 | 2024+ |
|---|---|---|---|---|
| real | +0.13 | +0.14 | +0.13 | +0.12 |
| shuffle | +0.11 (3/3) | +0.09 (2/3) | +0.11 (3/3) | +0.06 (3/3) |

- cosmetic = shuffle (prediction confirmed).
- vol_up / vol_down: edge unchanged, net better / worse (confirmed).
- trend_up: brk edge +0.49 / +0.28 / +0.23 in 3 eras (confirmed).

### 2. The PROFIT is not robust: 2024+ was mostly the real order of events
- Money 2024+: real +18.6 %/yr vs shuffle -0.7 [-5.7..+1.9], cosmetic -3.2.
- brk net 2024+: real +0.23 vs shuffle +0.00.
- 2020-21 holds: shuffle +11.9 %/yr, 3/3 positive.
- **Reading:** the 2024+ result rode trends longer than the 2-6 week blocks (gold 2024-25). The book harvests long trends and is flat without them.
- **Next test:** longblock preset (8-26 week blocks).

### 3. Prediction misses
- **ins depends on day-to-day structure.** Dayshuffle kills it: edge -0.10 / -0.09 / 0.00 / +0.06, net 0/3 positive in 3 eras. Predicted "changes least". Wrong: inside-day is compression across consecutive days, not an intraday effect.
- **fast's edge is largely intraday.** It survives dayshuffle: +0.16 / +0.15 / +0.04 / +0.05.
- **dip is partly index drift.** Dayshuffle keeps +0.32 of +0.50 in 2024+ (just being long a rising index), but only +0.02 of +0.43 in 2020-21. The real bounce part ≈ the real result minus dayshuffle.

### 4. Hot-streak (T5) and canary (T22) on cousin histories
- **brk form20 (hot → worse):** gone on shuffle (+0.32 / +0.21 / +0.04 / +0.04). A quirk of the real order, or a structure longer than 6 weeks.
- **ins form20 (hot → worse):** SURVIVES shuffle / cosmetic / vol (-0.50 / -0.32 / -0.09 / -0.15, mostly 0/3 positive); gone on dayshuffle. Real multi-day behaviour.
- **brk streak2 (after 2 wins in a row, the next trade is worse):** survives shuffle in 3 of 4 eras (-0.45 / +0.24 / -0.51 / -0.20); gone on dayshuffle. Ezio's idea has real support FOR BREAKOUTS. ins goes the other way in 2020+ (+0.36 / +0.22), so the book-level timing value nets to about 0.
- **brk canary (weak breakout weeks → BETTER trades next):** survives shuffle (+1.2 / +2.3 / +0.3, mostly 3/3). Real weekly mean reversion of breakout follow-through. ins canary goes the warning direction on shuffle (-0.41 / -0.26 / -0.46).
- **Kelly timing:** worse than fixed on shuffle in 3-4 eras (mostly 0/3). Robust: never use trailing Kelly.
- **Under the freeze rule,** sleeve-specific state sizing (brk streak2, ins form20) is a NEW pattern: next-cycle list.

## Synthetic batch 2, 2026-10-10: longblock (8-26 week blocks), generator v4, 3 seeds, parallel (3 jobs, 0.3 h incl. one-time cache)
**Prediction (written before):** if the profit lives in trends longer than 6 weeks, long blocks bring the real 2024+ result back; if not, 2024+ was luck in the exact order.

**Result: CONFIRMED. The profit lives in multi-month trends.**

| 2024+ | real | longblock | shuffle (2-6 wk) |
|---|---|---|---|
| Money, $10k, %/yr | +18.6 | +16.2 [+3.7..+23.4] (3/3) | -0.7 |
| Whole book, R/yr | +96 | +85 (3/3) | +23 |
| brk net R/trade | +0.23 | +0.19 (3/3) | +0.00 |

- 2020-21: longblock +9.0 %/yr (2/3) vs real +15.8, shuffle +11.9.
- 2014-17 / 2018-19: flat, as on real data (+4.3 / -3.9).
- dip is strong on long blocks: net +0.54 / +0.46 / +0.45 in 2018-26 (3/3). Its 200-day trend context survives long blocks.
- **Reading:** the book harvests MULTI-MONTH trends. It earns when a history contains them (2020+) and is flat when it does not (2014-19). Whether future years have such trends is a regime question we cannot control. That makes Japan 225 and 2022-23 (a strong-trend year: USD rally, rate shock) informative tests.
