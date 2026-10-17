# Theory ledger: what we believe about the lanes, why, and how sure we are

**Started:** 2026-10-09 (Claude). Update after every run. A theory is a mechanism claim with predictions, including where it should FAIL.

**Data notes:**
- Training data: 2014-17, 2018-19, 2020-21, 2024+ (four eras), six markets.
- Untouched and kept clean: Japan 225, and the sealed exam years 2022-23.
- Every number below was seen during selection, so expect effect sizes to shrink by 1/3 to 1/2 on new data.

**Confidence scale:** HIGH = direction very likely right; MED = plausible, needs a new-ground test; LOW = barely supported; DEAD = tested and failed.

---

## T1. Breakouts pay only when they go WITH short-term momentum. HIGH (causally confirmed 2026-10-10, see the engine section)
- **Mechanism:** a break that agrees with the last 10-20 days' move meets follow-through (trend-following flows); a break against it meets mean reversion.
- **Predictions:**
  1. Edge rises in the trade's direction when er10 or edge20 agrees.
  2. It shows across all breakout lanes, not one.
  3. It fails for reversals.
- **Evidence:**
  - Detector-gated lanes positive in both periods: pdh2+er10, main2+edge20, orb30+er10, retest+edge20 and others (run 3).
  - 16 of 19 related lanes agree on the 20-day-edge signal (luck check).
  - Outside literature (time-series momentum) agrees.
- **Untested:** Japan 225, sealed years, a different timeframe.

## T2. Trade at the trade-direction edge of the 20-day range; never from the far side. HIGH
- **Evidence:** pdh2 pos20 high ++++ (z +3.7), low ---- (z -3.9); gao the same; 16 of 19 related lanes agree.
- **Prediction:** a dose-response check should show stronger results the closer price is to the edge. Not yet checked monotonically beyond thirds.

## T3. Costs, not direction, kill short holds. HIGH
- **Mechanism:** a round trip costs about 0.15-0.25 ATR(M15); price wanders about 2.3 ATR in 4 hours, so 1-2 ATR stops sit inside the noise.
- **Evidence:** the edge vs coin flip is positive in most breakout books while net stays negative. The wide stop + 5-day chandelier (H2) turned the edge positive in all 4 eras (run 5).
- **Prediction:** wider R per trade improves net more than any filter does.

## T4. Breakout profits come from trend months, which cannot be seen in advance. MED
- **Evidence:** pdh2 made +667R in trend months and lost about 1,700R in all others. Detectors spot trend months no better than chance on a random walk.
- **Implication:** you have to pay the losing months to own the trend months. Filters help at the trade level, not the month level.
- Most of a trend month's profit comes before any detector fires.

## T5. A lane's recent form does NOT persist; hot streaks are followed by worse trades. MED (against the original theory)
- **Evidence:** pdh2 hot -0.24R vs cold +0.05R (z 4.1, 12 of 17 related lanes agree). Switching on recent results loses (run 4).
- **Contrarian switching (run 5):** a small edge in all eras at windows 40/80, gone at 160; the control lane showed none.
- **Use:** don't size up after hot streaks. Don't switch on form. Contrarian switching is NOT a strategy (too weak, no clear mechanism).

## T6. Fades (reversals) only have loss-predictors, not win-predictors. MED
- **Evidence:** vwap/exhaust in low volatility lose (theory agrees). Reversals in ranges (R1/R2) are still negative.
- **But:** reversal monthly results correlate -0.12 to -0.14 with H2. They earn at different times, just not enough.
- **Open:** a reversal design that clears costs (wider targets? daily timeframe?).

## T7. Dip-buying above the 200-day average (Connors RSI2 long) works and diversifies. MED (see run 6 update below: MED-HIGH, index effect; MECHANISM REVISED 2026-10-10, see the engine section)
- **Evidence (S2, run I4):** net +0.18 / -0.22 / +0.01 / +0.15R; edge positive in 3 of 4 eras; 50-67% positive months; correlation -0.07 with H2.
- **Caveat:** small sample (about 75 trades per era). It is also the strategy with the strongest outside literature (on indices).
- **Prediction:** best on indices, weaker on FX (literature). Check per market.

## T8. The breakout edge is market-specific: gold strongly, Germany 40 and USDJPY partly; EURUSD and WTI not. MED
- **Evidence (H2 by market):**
  - gold net +0.25 / +0.19 / +0.14 / +0.56R (edge +0.15 to +0.45) in every era
  - Germany 40 +0.20 / -0.08 / -0.03 / +0.37
  - EURUSD and WTI mostly negative
- **Mechanism guess:** gold and indices have trending flows; EURUSD is the most efficient, mean-reverting major.

## T9. The direction of the edge follows the macro trend (longs in 2020+, shorts in 2014-17). MED
- **Evidence:** H2 longs negative 2014-19, strongly positive 2020+; shorts the reverse. Consistent with T1 at a slower scale.
- **Risk:** a book that only works in one macro direction.

## T10. Narrow-range compression (NR7, Crabel) improves breakouts. LOW-MED
- **Evidence:** the nr7 lane after a narrow day was LIKELY REAL in the luck check (z 3.4), but B1 (nr7 only after a narrow day) was about flat in run I4.

## T11. Session / weekday effects (Friday, late hours). LOW
- **Evidence:** H6 learned these on all data. Applying them (H2+H6) did NOT improve H2 in 3 of 4 eras. Treat as noise until a theory exists.

## T12. A learned, fading signal score finds standout days. DEAD (as built)
- **Evidence:** H3, H4 and the top-20% day ranks all failed or were unstable across eras. The weights stay tiny, because the per-trade signals are too weak for a learner.

## T13. Turn-of-month, pre-FOMC, news blackout, confidence gate, merit entry, mirror trades. DEAD (2026-10-07 tests)

---

## Structural lesson (run I3, real-money sizing)
- **The lanes fire on the same breakout.** main2, orb30, orb60, pdh2 and retest2 all fire on the same move in the same market. The book was stacking 3-5 correlated copies of one bet, which is why its R drawdowns (400R+) are huge and the money sizing loses even when the R total is positive.
- **Next fix:** one position per market per direction at a time (dedupe), then size.

---

## Run 6 updates (2026-10-09, Part J)

## T7 (update). Index dip-buying works; it is an INDEX effect. MED-HIGH
- **dip3 long** (3 closes against the 200-day trend, then buy at the next open):
  - Edge vs coin flip positive in all 4 eras: +0.08 / +0.03 / +0.17 / +0.35.
  - Net -0.06 / -0.11 / +0.06 / +0.26R.
  - Win rate 64%, Kelly 3.25%, longest losing streak 7, correlation with H2 -0.12.
- **By market:**
  - Positive in both periods: US500 (dip3 +9/+9, rsi2 +14/+19), Germany 40 (dip3 +4/+12), USDJPY (dip3 +2/+3).
  - Negative: EURUSD; gold was negative in the old period.
- Matches the literature prediction: dip-buying works on indices, not FX.
- **Short side** (dip3 short, rsi2 short): no edge. Selling rallies in downtrends does not mirror buying dips.

## T14. Inside-day breakout with a same-day exit. MED (new, chosen from 6 variants)
- **Rules:** stop orders at yesterday's high and low; stop at yesterday's middle; exit at the close.
- **Results:**
  - Edge positive in all 4 eras: +0.10 / +0.11 / +0.17 / +0.08.
  - Net -0.02 / +0.01 / +0.14 / +0.03.
  - Correlation with H2 +0.05.
- **Markets:** USDJPY +48/+2, WTI +71/-19; EURUSD -103/-24.
- **Longer exits (48h, 5d)** are better in 2018-21 but worse in 2014-17 and 2024+.

## T15. Turtle 55/20 on single markets. DEAD
- Net -0.3 to -0.7R in all 4 eras, on 5 of 6 markets.

## T16. One model of P(win) per trade from all the reads. DEAD (as built)
- The predicted spread is 11-68%, but the actual win rate moves only 33-36% (breakouts) and 35-42% (reversals).
- The top-minus-bottom decile edge is negative in both periods for both families.
- Skipping the bottom decile saves -9 to +137R vs a random 10%, and the sign flips between periods.
- **Lesson:** the individual loss-predictors (T2, T5, T6, Fridays) work as separate filters, but pooling every read into one learner drowns them. Same failure as T12.
- **2026-10-13 addition (fibrev postmortem):** faint clues die when blended into one learner (T12, T16, fibrev's median weights); they survive as separate switches with a scorecard that can only turn a switch off (T19). Rule: every input proves itself alone first; combine as simply as possible; test any scoring formula on known-truth data before trusting it.

## T17. Asymmetry: two different capital profiles. MED
- **Breakout lanes with 5-day exits:**
  - Win 17-28%. The best 10% of trades contribute +0.5 to +0.8R per trade (more than the total profit).
  - Without the best 5% they lose -0.4 to -0.7R per trade. Losing streaks 33-48.
  - They need many markets, never cutting winners, and an account big enough to ride a 40-loss streak at small % risk.
- **Index dip-buys:**
  - Win 64-65%, losing streaks 4-7, Kelly 2.5-3.25%, holding about 4 days.
  - Suits small accounts, but there are few trades (~25 a year).
- **Minimum position size at $10k / 0.5% risk:**
  - Too big on 76% of Germany 40 trades and 12% of US500 trades.
  - Germany 40 needs a bigger account or bigger risk.

## Run 7 updates (2026-10-09, Part K)
- **T18. A loss signal's meaning depends on the filter in front of it.** MED. The T2/T5/Friday/50d gates, found on raw lanes, pointed the WRONG way inside the momentum-filtered, deduped H2 sleeve. A gate has to be validated on the population it will actually filter.
- **T19. Shadow scorecards protect against dead gates.** MED-HIGH (as a mechanism). With the scorecard, bad gates were switched off and cost nothing; blind gates cost 25-38 R/yr in 2020+.
- **T20. Stacking was a big part of the drag.** MED. One position per market per direction made the H2 sleeve net positive in all 4 eras (market list = hindsight).
- **T5 corollary (to test):** trailing-Kelly sizing = sizing up after hot streaks. It probably explains why the R results (+35 R/yr in 2020-21) did not turn into money.

## Run 8 updates (2026-10-09, K5)
- **T5 corollary CONFIRMED:** trailing-Kelly sizing loses because it sizes up after hot stretches (-43 R/yr vs fixed in 2020-21 at the same average risk). Use fixed fractional risk.
- **T21. Defensive sizing after win streaks (streak2/3, form20). LOW.** The direction matches T5 in most eras, but the gains sit within noise and drawdowns did not shrink. On the next-cycle list, not in the frozen design.

## Run 9 updates (2026-10-09)
- **T22. Weekly mechanism weakness mean-reverts. MED.** Breakout canary alarms (3 weeks of poor follow-through) were followed by BETTER trades. Weekly dips in an edge are noise that snaps back, which matches T5. So "detect a dead edge in weeks" cannot be done with a P&L or mechanism alarm on this scale. A structural death would have to show as months outside the band.
- **Intraday filtered breakouts (fast)** are net positive in all 4 eras (small early). Same entries as brk (corr +0.47).

## Synthetic batch 1 updates (2026-10-09)
- **T1 (momentum edge): survives reshuffling.** The edge stays positive across cousin histories. **T4 (profit from long trends) strengthened:** money depends on trends longer than 6 weeks; the 2024+ profit vanished on 2-6 week reshuffles.
- **T10 / T14 (inside day): REVISED.** Its edge is day-to-day compression structure (dies on dayshuffle), not intraday. The hot-form loss signal for ins is robust.
- **T7 (dip): partly index drift.** The pure bounce is clear in 2020-21 (+0.4R) and smaller in 2024+ (+0.2R).
- **T5:** robust for ins (form20) and for brk after 2 wins in a row (streak2); NOT robust for brk form20.
- **T22:** brk canary reversal robust (real weekly mean reversion of follow-through).
- **T4 CONFIRMED by longblock (2026-10-10).** 8-26 week reshuffles restore most of the 2024+ profit; 2-6 week reshuffles erase it. The book's profit = multi-month trends. Expect flat periods (like 2014-19) whenever those are absent.

## Engine stage 1 updates (2026-10-10, causal tests on ideal / nightmare worlds; engine_results.md)
- **T1 CONFIRMED CAUSALLY (HIGH).** Bending the same histories toward momentum vs snap-back moves brk's edge from -0.27 to +0.52 per trade (t +6.6) and fast's from +0.01 to +0.19 (t +6.8), in both seeds and both periods. brk is a momentum-regime bet. Its WHEN = markets whose moves persist (20-day variance ratio about 0.9+).
- **T7 MECHANISM REVISED (dip is NOT mean reversion).** dip gets WORSE in snap-back worlds and better with momentum (+0.10 -> +0.42, t +2.5). That is the opposite of the pre-registered prediction. Together with the why-phase placebo (random days above the 200-day average earn over half of it), dip = buying a pause INSIDE a persistent uptrend. Consequence: dip shares brk's regime, so it diversifies less than thought.
- **T14 (ins):** insensitive to momentum except at the extreme (t +2.2). Its lever is compression width, not regime.
- **T3 CONFIRMED** on real-shaped worlds: volatility leaves the edge flat and raises net R, steepest for short holds.
- **T4 / T14 day-order claims:** direction as expected on day-order / trend-length worlds, but not shown with 2 seeds (|t| < 2).

## Regime engine updates (2026-10-10, known-truth worlds; regime_results.md)
- **T1 / T4 refined:** brk and fast are pure momentum-regime bets (brk mom +0.57..+1.05, snap -0.37..-0.58 per trade).
- **T23 (NEW, MED, synth-only): straightness READS the regime, variance ratio does NOT.**
  - er40 (40-day efficiency ratio) separates momentum days at AUC 0.79-0.88, catches 87% of spells in their first half, median lag 10-14 days.
  - VR / autocorrelation gauges are blind (AUC ~0.5); that explains hunt round 1.
  - Gating brk on er40 keeps ~39% of trades, ~100% of the edge; the rejected trades are about 0 (harmless).
  - NEEDS the real-data check.
- **T7 (dip) refined again:** with the base drift removed, dip has no edge in ANY regime. Its real edge requires the indices' upward drift (plus a small snap-back component).
- **T14 (ins):** regime-blind (confirmed again).

## Ladder test (2026-10-10 17:33; ladder_spec.md)
- **T24 (NEW, MED): banked re-entry ladders do not beat an on/off straightness switch.**
  - The 1.5 ATR target clips brk's rare large winners (T17), so per momentum trade the ladder earns less than brk.
  - On real data (exploratory) it is worse than brk alone.
- **T17 reinforced:** brk's value is in letting a few winners run; capping exits destroys it.
- **Trend-age sizing: NOT supported on real data.**
  - In synth, older trends grade brk trades strongly.
  - On real bars there is no age gradient, and 20-day straightness >= 0.30 runs almost never reach 40 days.
  - Real regimes are short and soft (consistent with switch P2: neutral days still pay).


---

## 2026-10-13 updates (theory runs, fresh-data exams, synth worlds)

- **T15 relabel: DEAD (as built).** Single markets, no pyramiding, and above all a slow clock: a 55-day confirmation + 20-day giveback against real straight runs that rarely reach 40 days. Outside note: Turtle System 1's "skip after a winning breakout" rule is T5 / N1 written down in 1983.

## T25. Fresh-data reality for the core book. HIGH (two one-shot tests)
- **fast on US500: dead** (exam 2016-19: EDGE ≈ 0, costs doubled, breaks snapped back both ways). It was never real there: training EDGE +0.03 / +0.04.
- **fast's edge lives on gold:** EDGE +0.21 (t 3.0), positive in all 4 eras (spent data; a hindsight market pick, T8: needs its own fresh test, gold 2022-23 sealed).
- **dip on fresh indices: real but small.** EDGE positive on both fresh tests (US500 2016-19, US Tech 100 2017-26), net about +0.1 R/trade vs +0.55..+0.76 in training: roughly a fifth of its training size. 2018 was its worst year in both.

## T26. The clock rule. MED-HIGH (consistent across fast, dip, Turtle and the synth worlds)
**Protect (filter, size, switch) a strategy with a gauge on the clock of its PAYER, not on the clock of its TRADE.**
- On the trade's own clock, a strategy's food and its poison look the same. For dip, a healthy pullback and the first days of a crash are both "a few red days with volatility jumping": a fast gauge cuts both and gains nothing (dipvol: ATR 10 skipped trades = kept trades). A slow gauge sees the real enemy, a stress REGIME (ATR 20 / 40 skipped trades lost; Ezio's quarter table helped in 2022).
- fast is paid by intraday flow: its multi-day filters were decoration, while an intraday checkpoint (2h) carried information (N5).
- Turtle's detector was slower than the trends it hunted: clock too slow for the payer.
- **Use:** before designing any filter, name the payer and its lifetime, and put the gauge on that clock.

## T27. An accurate gauge can be useless. MED (method)
A gauge validated on a world built around the wrong threat is perfectly calibrated and useless. ATR 10 won the synth accuracy test because the planted storms were short (40 days); the real enemy of dip is long stress regimes. **Define the threat first, then build the test world around that threat.**

## T28. Skipped-vs-kept is the test of any filter. MED (method)
If the trades a rule skips earn the same as the trades it keeps, the rule is not a filter, only a size cut (less profit, proportionally less drawdown). Always report skipped vs kept, not just totals. (Same family as T18 / T19: judge a gate on the population it filters.)

## T29. Give-back is mostly geometry; fast's afternoon edge belongs to slow starters. MED (spent gold data)
- fast on gold sees ~7× more open profit than it keeps, but the coin-flip mirror gives back just as much: give-back is path geometry, not a flaw. The real leak is trades that go 1-2R up and come back to the full stop. Breakeven / ATR trails reshape the results without adding EDGE (exit rules can't create an edge).
- Trades already up at 2h add ~nothing in the afternoon; flat-at-2h trades earn +0.36 R more (t 2.7, all 3 eras; mirror -0.24). The money arrives around 13:00-14:00 London (COMEX open + US data). Candidate payer: arriving US flow finishing London's move. See N5 and fast_giveback.md. Needs fresh data.

## T30. Volatility and dip. MED (synth + spent data)
- High AND RISING volatility is bad for dip in every synth world and in real data; high-but-falling depends on the world, and a slow gauge mostly reads "falling" AFTER the storm has passed (fine for dip).
- Combined with T26: the harmful state is a long stress regime, not a volatility burst. Candidate rule for a FRESH test (US 30 / Japan 225): skip dip while the 40-day ATR is ≥ 1.3× its 1-year median AND rising. Written with a reason before testing, but the gauge was seen on spent data first: flag it as such.
- **Update 2026-10-13 late (explore, training data):** pooled skipped minus kept -0.56 R (t -1.6): FAILS its noise bar (t < -2). It rests on 6 skipped US500 trades; on Germany 40 the 7 skipped trades WON (+1.05). Downgraded to "plausible, unproven; maybe a risk tool (max DD 33 -> 21 R), not an edge tool".

## T31. Explore on training data: what lives (2026-10-13). MED (one run, noise bars set first)
- **fast:** real only on gold (EDGE +0.20, t 3.0, all eras). Germany 40 / USDJPY / US500 inside noise; book without gold +0.07 (t 1.7), below the bar. EURUSD / WTI controls did nothing (T8 holds).
- **Afternoon hold for flat trades (Ezio's "flat means undecided"):** alive on gold (+0.42, t 2.9, mirror -0.25, all eras). USDJPY +0.14 (t 1.4) and also peaks at 13:00 London (US data). The payer (US money / data arriving) may be wider than gold.
- **Fade against-trend breaks: DEAD.** Fade loses after costs on all six markets (pooled -0.12, t -4.1). Against-trend breaks don't reverse. With-trend breaks follow through (pooled ride EDGE +0.08, t 3.0: T1 again).
- **Trend option (bet on the first break out of a very quiet day):** cleared its bar (+0.33, t 3.8) on FX / gold / oil, flat on indices. BUT see T33: that number was measured with a biased entry. Corrected breakdown pending (trendwhy).
- Details: explore_results.md.

## T32. Real trend lengths look like a random walk's. MED (method)
A 3 x ATR20 zigzag gives median legs of 22-28 days on real markets and 25-32 on random walks. A leg-length distribution is geometry; it can't prove trends exist or set a time stop by itself. (Same family as T29: give-back is geometry.)

## T33. Never let the end of the bar choose which trades exist. HIGH (method; found 2026-10-13)
Explore read the trend option's break on DAILY bars and skipped days that touched both sides of the box. That decides which trades exist by looking at how the day ENDED: days that broke up and then collapsed through the box were silently removed, flattering the result. Rule: entries are read in time order on the finest bars we have (M15, then M1), and anything ambiguous is resolved by time, not by dropping it. A noise bar does not fully protect against this, because the size of the bias depends on the market's real intraday behaviour.

## T34. Research stance (Ezio, 2026-10-13). RULE
Only so much skepticism on a genuinely positive signal. Once a signal has passed a test that could have gone against it, stop stacking disproving tests and break it down: how we won vs how we lost vs what we can't explain, aimed at WHY, with our theories of what wins and loses written down first. Fresh data stays the final proof, spent sparingly. Also (Ezio): a trick working on some markets and not others is not a failure. An index (the whole bazaar) is a different kind of thing from a single market (one stall), and quirks differ, as long as the quirk is stated as a reason that predicts something.
