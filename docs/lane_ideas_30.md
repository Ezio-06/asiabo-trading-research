# 33 lane ideas (Claude + Ezio, 2026-10-11 / 12): status noted where tested

**Context:** the core book (fast + dip) is momentum plus uptrend drift (engine stage 1: dip is NOT snap-back). That means the gap is lanes that earn in snap-back, chop or crashes. Score "earns when the book doesn't" next to edge.

**Already tried in the lab, so not listed:** main2, orb, pdh2, trend2 (noise boundary), gao, range2, swing2, turtle55, rsi2, inside, dip3, dip short. Also dead: turn-of-month, pre-FOMC, gapfill without a matched control.

**Tested in batch 1 (young_batch1_results.md, 2026-10-12):**
- #31: a weak lead
- #19: dead as a trader
- #27 / #28: unreadable (US500 history too short)

**Tag on each idea:** S = should like snap-back worlds, M = momentum, B = regime-blind, D = needs drift, X = crisis leg.

## A. Anti-book (snap-back / chop)
1. **Daily turtle soup:** a new 20-day extreme that closes back inside within 2 days → fade it. Stop beyond the extreme, trailing exit. Mechanism: trapped breakout buyers. EURUSD, WTI. S
2. **Post-shock reversion:** a day of 2.5+ daily ATR against the 200-day trend → partial retrace over 1-3 days. Mechanism: forced selling overshoots. Indices. S
3. **Failed-shadow reverse (Ezio):** brk/fast stopped out quickly → reverse, trailing exit. Test the opposite run vs random first. S/B. *(Probe M3: nothing beyond random.)*
4. **Blow-off fade:** price stretched 3+ daily ATR from its 20-day average plus a volatility spike → enter on the first opposite close, trailing exit. Mechanism: exhaustion and forced exits. S
5. **Weekly overextension fade:** weekly return in the top or bottom 5% of its 3-year history → fade it next week. S
6. **EURUSD Bollinger reversion:** daily close outside 2 sigma → target the 20-day mean. EURUSD is our most mean-reverting market (T8). S
7. **London-open reversal of the Asian move:** in gold and EURUSD, the thin Asian drift reverses once London liquidity arrives. Mechanism: the Asian flow is uninformed. S
8. **FX fix reversal:** the move into the 16:00 London fix reverses afterwards. Mechanism: fix flows are mechanical, not informed. EURUSD, USDJPY. S

## B. Crisis / down-regime legs
9. **Crash continuation short:** an index day with a range more than 2x its 20-day average that closes in the bottom 10% → short the next day. Falls are faster than rises. X
10. **Gold flight to safety:** US500 falls 2+ daily ATR → long gold the next day. X
11. **Yen safe haven:** US500 breaks its 20-day low → short USDJPY. X
12. **Vol-target re-leverage:** once a volatility spike has peaked (5-day realized vol drops below 10-day), go long indices. Mechanism: vol-targeting funds buy back in mechanically. D/B. *(Ezio rejected it 2026-10-12: the panic peak can't be predicted, so it would enter too early.)*

## C. Information flow (regime-blind)
13. **US → Germany lead-lag:** US500's move after the Xetra close → trade Germany 40's next open and first hour. B
14. **Germany → US:** Germany 40's morning move → trade US500 into its cash open. B
15. **EURUSD → gold, intraday:** a dollar move in one hour → trade gold the next hour (gold reprices to USD with a lag). B
16. **WTI shock spillover:** an oil day of ±3 ATR → trade indices / USDJPY the next day. B
17. **Shock by hour:** big moves at news hours continue (information); big moves in quiet hours revert (liquidity). Same signal, split by mechanism. B
18. **NFP/CPI drift:** take the direction of the first 15 minutes after a scheduled release and hold it to the close. Release dates are computable. M (short clock)

## D. Volatility & compression
19. **Multi-day squeeze breakout:** Bollinger bandwidth at a 120-day low → breakout with a trailing exit. B. *(Batch 1: dead as a trader, EDGE -0.14, 54% false breaks; a sensor candidate.)*
20. **Range-expansion follow-through (Crabel):** a wide-range day that closes at its extreme → continuation the next day, out at the close. M
21. **Opex-week pinning:** in index expiry weeks (third Friday), fade the ranges because dealer hedging damps moves; trend release the week after. B
22. **Vol-scaled time-series momentum:** always in, by the sign of the 3-12 month return, sized by volatility, rebalanced monthly. A slow clock, and the crash leg for a carry pairing. M (slow), X

## E. Levels & structure
23. **Cash-open gap by size:** small index gaps fade, big gaps go. B
24. **Gold round numbers:** at $50 / $100 levels, compare break-and-run against rejection (stop clusters). B
25. **52-week-high anchoring:** near the 52-week high, the drift continues (anchoring bias makes traders sell too early). M/D
26. **Weekly breakout, weekly trailing exit:** brk on a slower clock, with fewer and larger trades (T3). M

## F. Relative value
27. **US500 vs Germany 40 spread reversion:** a beta-hedged z-score on daily closes. B. *(Batch 1: unreadable, 6 trades; waits for US500 2015-19 = the fresh-data exam.)*
28. **Index relative momentum:** long the stronger of the two indices, short the weaker. M (relative)
29. **Gold vs USDJPY divergence:** both react to US real rates; when they disagree, the laggard catches up. B
30. **Trend-end lane:** after an er40 spell ends, trade whatever the trend-end study finds (reverse, chop or continue), only where it found it. S/B. *(Probe M1: the end of a trend carries no reversal information.)*

## G. Ezio's ideas
31. **Mirror dip (Ezio, 2026-10-11):** short the START of a pullback in a stretched trend. dip buys the END of one; this lane takes the phase before it.
    - **Ezio's theory (2026-10-12):** "the trend's over; earn from the losers that bought it late."
    - **Batch 1:** a weak lead (EDGE +0.06, t 1.6); the long-stretch side +0.14 (t 2.3, n 35). The stop almost never fires.
    - **Young engine** (realistic fakes, cause test, placebos): running 2026-10-12.
    - **Original design notes:** condition = price ≥ 2.5 daily ATR from the 20-day average plus a straight trend; trigger = the first close below the prior 3-day low; exits = stop beyond the extreme, 5-day time stop, TP at the 20-day average.

32. **Shadow sensors: "trades tell us what's going on" (Ezio, 2026-10-11).** Use shadow trades as free probes of the market's state.
    - **Read the HOW, not the P&L** (P&L streaks reverse, T5 / T22): which exit fired, how fast, MFE / MAE.
    - **Exits as labels:** lanes with one exit per outcome are built-in state labels.
    - **Speed:** a sensor's lag is its hold time.
    - **Test:** features from lane A's resolved shadow trades → predict lane B's next trade, against er40 and a shuffled order. Exclude overlapping windows.
    - **Prediction (Claude):** a weak but real signal from HOW trades end; P&L streaks show nothing or are contrarian.
    - **Candidates from batch 1:** #19's false-break stops (a range-regime read); the M6 lead (a fast trade after a fast loss does better).

33. **Causal breakout (Ezio, 2026-10-12):** #19's breakout, taken ONLY when there is evidence of a real reason behind the move.
    - **The pattern being fixed (Ezio):** #19 chases every break like buying every new meme coin; most are hype, one firm's buying or a "mass hallucination", and the early chasers get slammed. Broad claims rarely work. Look for the cause, not the price move.
    - **Fingerprints of a real move** (each tested as its own variant, so we learn WHICH one separates real from hype, if any):
      - a. **News timing:** the break happens at a scheduled release hour (ties to #17 / #18) vs a quiet hour.
      - b. **Breadth:** US500 + US Tech 100 + US 30 break together vs one alone. Needs the new symbols (US Tech 100, US 30 being farmed).
      - c. **Weight:** the break day's range and tick volume well above normal vs a thin drift through the line.
      - d. **Hold:** after the first pullback, price stays beyond the breakout level vs falls back inside (a confirmation, priced honestly: a later entry).
    - **Status:** queued as the first lane of batch 2. a, c and d can be tested now; b waits for the new data. Plain explanation + Ezio's predictions before any run.

## Caveats
- Ideas in B fire rarely, so they will have thin evidence.
- C needs care with time zones and cash hours.
- 8, 18 and 21 need calendars.
- Intraday ideas fight costs (T3).
- Protocol for any of them: write the prediction first, then the random-walk yardstick, the realistic v8 cousins, clustered t, a half split, and monthly correlation with fast + dip.
