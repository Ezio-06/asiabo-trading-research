# Lane audit: our lanes vs how standard bots do them (Claude's audit, 2026-10-08)

**Scope:** for each lane, how public bots, papers and EAs implement the same idea; where ours deviates; what to test first. This is meant to be compared against the answers from the other AIs.

**Evidence quality:** papers are author backtests, and replications are better. MQL5 Market EAs are promotional and unverified, so they're only used to show *how* the bots are built, never as proof that they work.

---

## 1. The headline: five structural deviations (these matter more than any single lane)

### A. Exits: we cap winners with fixed 1-2R targets, but standard intraday bots don't
- **The opening-range breakout paper** (Zarattini & Aziz) holds to the session close or a 10R target. It wins only about 24% of the time, and the edge lives entirely in the few large days.
- **The SPY intraday momentum paper** ("Beat the Market") uses a trailing stop (the noise boundary or VWAP) and exits at the close, with no fixed target.
- **Gold breakout EAs** almost all trail or move to break-even plus a trail. None of the ones I found use a hard 2R and flat at 16:00.
- **Our own data agrees.** The probe showed the continuation move keeps growing out to 24-48h, and only wide stops with long holds gave positive cells.
- **The gap in our testing:** the stop-menu test kept the **target price fixed**, so no lane has ever been tested with "no target, time exit or trail".
- **The point:** our design is tight stop plus capped target. That is the worst combination, because the stop gets hit by noise and the tail that pays for it is cut off.
- **First test:** same entries for every breakout and momentum lane, exit at session close / 24h / 48h with no target, plus a VWAP-trail variant.

### B. Stop unit: we use ATR(14) on M15, but standard bots size stops off the daily range
- **What the papers do:** the ORB paper uses the first-candle extreme, or 5-10% of the **14-day daily ATR** on the TQQQ version. Turtles use 2N on daily ATR. Crabel's work is all in daily-range fractions.
- **Why it matters:** an M15 ATR is a noise-sized unit by construction. Our finding that price wanders about 2.3 ATR(M15) in 4 hours is exactly that.
- **The catch:** standard tight stops only work because they come paired with an uncapped exit (see A).
- **First test:** express stops as a fraction of daily ATR and re-run A on top of it.

### C. Entry: we enter on an M15 close beyond the level +0.1 ATR, but standard bots use stop orders at the level
- **What the bots do:** session-breakout EAs place buy-stop and sell-stop orders on the range edges (a straddle).
- **What ours pays:** a close-confirmed entry pays on average part of a bar beyond the level, plus the 0.1 ATR buffer. With a box-width stop, that's a measurable chunk of R on every trade.
- **Cost:** this is cheap to test in the offline tool by entering at the level with intrabar fill on M1.

### D. Market and session matching: we run the breakout and reversal ideas where the literature doesn't
- **Opening-range breakout** is documented on **index cash opens** (QQQ, NQ, DAX, FTSE), not on gold's Asian box.
- **London breakout** on EURUSD with Asian range, 2:1, entries 07-10 UTC came out at profit factor 0.87 over 10 years, net -28% (backtrex). That's the same idea as our `main` and `london`.
- **Short-term mean reversion** (Connors RSI(2)) is profitable on S&P 500, Nasdaq and DAX daily but **loses on EURUSD** (profit factor 0.78). The reason given is that indices have an upward drift that pays dip-buyers, and FX doesn't. That matches our fades being negative on FX and gold.
- **Intraday momentum** (first half hour predicts the last half hour, Gao et al.) is an **equity index / futures** effect at the **cash session** level.

### E. Costs versus edge size: the public numbers say the same as ours
- **The replication:** a clean replication of the ORB paper on five index CFDs got the gross edge back (+0.05 to +0.13R). After spread and slippage it's net zero or negative on all five; NQ came out at +0.002R.
- **Against random:** the rule beats a random-direction benchmark by about +0.10-0.13R, which is about the size of the CFD spread.
- **What that means for us:** our "breakouts equal random after costs" isn't a bug in our build. It's what the evidence says for these setups at retail CFD costs. The edge, where it exists, is spread-sized.
- **Where it can survive:** fewer trades with bigger R distance (A plus B), or cheaper execution (futures or raw-spread accounts).
- **On method:** our control lane is the same random benchmark the replication author praised as the most useful part of his work. Keep it.

---

## 2. Lane by lane

| Lane | Standard implementation | Where ours deviates | Verdict / first test |
|---|---|---|---|
| **main** (Asian box breakout, gold) | Gold session EAs: Asian range 22:00-05:00 GMT, stop orders on the edges, ATR SL/TP with break-even and trail, weekly SMA trend filter, spread filter, range-size check, sometimes both directions per day. | Close-based entry, fixed 2R, hard flat at 16:00, no HTF trend filter (our "trends disagree" bad sign is the same idea, found independently). | Keep for one rebuild: stop-order entry, trail or session-close exit, trend filter. If it's still at random, drop it. Public evidence for Asian-box breakouts is weak. |
| **london** (07-12 box, break to 18) | London breakout: Asian range broken in 07-10 UTC, fixed 2:1. This exact design is publicly negative on EURUSD. | Our box is the London morning itself, broken in the afternoon. That's closer to an NY-open breakout than to standard London breakout. | Re-point it as a **cash-open ORB** on US500 (13:30 NY) and Germany 40 (Xetra open), with a short opening range and exit at the close. That's the documented version. |
| **retest** | Discretionary "break and retest" with no systematic evidence I could find. | Stop at box middle with 2R. | Low priority. Fold it in as an entry variant of main (pullback entry) rather than its own lane. |
| **fade** (failed breakout) | Raschke/Connors "Turtle Soup": fade a failed **20-day** breakout on daily bars, not an intraday box. | We fade an intraday box with a tight stop (extreme + 0.1 ATR). Mean-reversion bots generally use wide or no stops, because the strategy's win rate depends on surviving the wiggle. | Clearly negative here and in the literature for FX and gold. Retire it as a trader and keep it as a **signal source**: our own lead was "go *with* the move after a bad fade". |
| **sar** | Stop-and-reverse belongs to always-in trend systems (Parabolic SAR, Turtle-style reversal), not to a single intraday box. | A one-shot reverse with the other box edge as stop. | Drop it as a lane. It's covered by the continuation-after-failed-fade idea. |
| **range** (box edge fade) | Asian-session range mean reversion is a common FX EA type, with a tight range and a spread filter, run *inside* the Asian session. | We trade it after 07:00, when London volume arrives. That's the session where breakouts, not reversion, are expected. | If kept, run it in the **Asian hours** on the box being formed (USDJPY and gold Asian ranges). Otherwise drop it. |
| **exhaust** | Crabel-style "stretch" fades, done on daily bars with daily-range units. | Uses 3 ATR(M15) of extension, which is small in daily terms. | Weak case. Merge it with fade into one "reversal signal", not a lane. |
| **trend** (VWAP at 13:00) | Zarattini's VWAP paper: be long above VWAP and short below it, on 1-min bars, stay in and flip on the cross, exit at the close, on QQQ/TQQQ. | We take a one-shot at 13:00 with a fixed 2R and a stop 0.5 ATR from VWAP. The standard version uses VWAP *as* the trailing stop and has no target. | Rebuild it as **"Beat the Market" style on US500**: noise-boundary entry checked every 30 minutes, VWAP/boundary trail, flat at the close. This is the best-documented intraday momentum design for that market. |
| **vwap** (stretch reversion) | VWAP reversion scripts use standard-deviation bands. I found no credible net-of-cost evidence. | The 3 ATR(M15) stretch with a stop beyond the day extreme. | Drop it, or keep it log-only. |
| **nyaft** (NY afternoon continuation) | Intraday momentum (Gao et al.): first half-hour return → **last half-hour** return, on index ETFs and futures. | We use a 13-16 move to trade 16-20 UTC, on gold too, with a mid-range stop and 1.5R. | Rebuild on **US500 only**: first 30 minutes of the cash session predicts the last 30 minutes, entered into the close. Merge it with the trend rebuild. |
| **scalp** (NY open impulse, 1h, 1R) | Retail scalping EAs are cost-dominated. Every public replication I've seen dies at retail spreads. | Not really a deviation. The idea itself is the problem at our costs. | Keep it log-only (already the decision). Don't rebuild it. |
| **pdh** (prior-day high/low break) | A common component of daily breakout systems, usually with a wider stop and a multi-day trend exit. | The mid-yesterday stop and 2R target. | Merge it into the swing/trend-following family as a short-lookback version (1-5 days), with the same trailing exit. |
| **nr7** | Crabel: NR7 (or NR4) day → next day, **stop orders at open ± a stretch**, exit at the close or within a few days. | We trigger on yesterday's high/low on a close, with the other side as stop and 2R. Ours is close, but differs on entry and exit. | Use NR7 as a **filter on main/ORB** (does a compressed prior day improve the breakout?), not as its own lane. |
| **bigrev / bigcont** | Day-after-big-range studies are daily, with holds of 1-5 days. | Entry at 07:00 with 0.5× range stop and 1R. | Keep as **regime tags** only. Merge their signal into the trend family. |
| **gapfill** | FX weekend gaps fill about 79% of the time within a week, with a median of about 1 hour (EURUSD, GBPUSD, USDJPY; small sample). Standard practice is to enter early Sunday and target the Friday close. | Our symmetric stop at equal distance; run on gold and indices too. A high fill rate isn't an edge on its own: what matters is fill *before* an equal adverse move, net of the wide Sunday spread. | Cheap to re-check properly: entry at the first liquid bar, then fill before the adverse move, on FX only, with Sunday spread modelled. Low weight. |
| **swing** (20-day Donchian) | Turtles and modern CTAs: daily bars, 2N stop, 10/20-day exit, **volatility-sized across 20-60+ markets**. AQR's century-of-evidence result comes from the diversified portfolio, not from single markets. | The rules are close to standard. The deviations are breadth (6 markets, 2 of which are near-duplicates in risk) and **swap** on CFDs. | Keep it. It's the most standard lane we have. Size by volatility, run every market, and judge the **portfolio**, not each lane. A swap-free account matters most here. |
| **dip** (pullback in a rising SMA) | Connors RSI(2): 200-day SMA trend filter, RSI(2)<5 entry, **exit on a close above the 5-day SMA, no stop**, long-only, indices. | We use a 20-day SMA, a 2-down-days trigger, a fixed 2R target and a tight pullback-low stop, on all markets including FX. | Rebuild it as the standard version **on US500 and Germany 40 only, long side**. It's the only family with consistent public evidence for indices. Drop it on FX and gold. |
| **control** | A random benchmark, standard best practice. | n/a | Keep it. |

---

## 3. Structural questions, answered

- **Is a fixed-R target with 1-2 ATR(M15) stops standard?** No. Breakout and momentum bots use session-close, time or trailing exits. Mean-reversion bots use exit-on-strength with wide or no stops. The fixed 2R is a retail-course convention, not a systematic-bot one.
- **Timeframes:** ORB and intraday momentum use 1-5 min triggers within the **index cash session**. Mean reversion and trend following use **daily** bars. M15 as a single clock for everything matches neither.
- **One trade per day:** fine for ORB, since most standard versions do the same. Intraday momentum checks every 30 minutes and can re-enter. Trend following is always-in.
- **Flat at a fixed hour:** standard for intraday, but at the **cash close** of that market, not at 16:00 or 20:00 UTC for every market.
- **ATR(M15) as the universal unit:** non-standard. Use daily ATR for stops and sizing, and M1/M5 only for the entry trigger.

---

## 4. Proposed rebuild list (strategy machinery only, house untouched)

1. **Exit test on existing entries (cheapest, biggest):** no target; close / 24h / 48h / VWAP-trail variants for every breakout and momentum lane, against the control lane under the same exits.
2. **Stop unit change:** stops as fractions of daily ATR, combined with test 1.
3. **Entry mechanics:** stop orders at the level instead of close +0.1 ATR (main, london, pdh, nr7).
4. **Three standard-replica lanes on their home markets:**
   - US500 cash-open ORB with exit at the close.
   - US500 intraday momentum in "Beat the Market" style (noise boundary plus VWAP trail).
   - US500/Germany 40 long-only RSI(2) dip with exit on strength.
5. **Swing as a volatility-sized portfolio lane** across all six markets, judged as a portfolio, with swap counted.
6. **Retire as traders, keep as signals/tags:** fade, sar, exhaust, range (unless moved to Asian hours), vwap, scalp, bigrev/bigcont, nr7 (as filter), retest (as entry variant).

**Reality check:** even the best-documented items (A, plus the US500 replicas) show edges about the size of retail CFD costs in independent replications. The realistic hope is a few small, positive, *diversified* lanes, not one strong one. That fits the "few high-quality earners" goal, and makes costs (broker, swap-free account) as important as any rule change.

---

## Sources
- [ORB paper replicated on five indices: gross reproduced, net zero (MQL5 blog)](https://www.mql5.com/en/blogs/post/776235)
- [Day trading with an opening range breakout strategy (CXO Advisory on Zarattini & Aziz)](https://www.cxoadvisory.com/technical-trading/day-trading-with-an-opening-range-breakout-strategy)
- [Beat the Market: intraday momentum strategy for SPY (Concretum)](https://concretumgroup.com/beat-the-market-an-effective-intraday-momentum-strategy-for-sp500-etf-spy/)
- [VWAP: the holy grail for day trading systems (Concretum)](https://concretumgroup.com/volume-weighted-average-price-vwap-the-holy-grail-for-day-trading-systems/)
- [Intraday momentum: first half-hour predicts last half-hour (Alpha Architect)](https://alphaarchitect.com/2014/08/attention-prop-traders-the-first-half-hour-of-trading-predicts-the-last-half-hour/)
- [London breakout backtest on EUR/USD (backtrex)](https://backtrex.com/en/backtests/london-breakout-eur-usd)
- [Why the same strategy wins in London and dies in Tokyo (MQL5 blog)](https://www.mql5.com/en/blogs/post/774527)
- [Connors RSI(2) on EUR/USD vs indices (backtrex)](https://backtrex.com/en/backtests/connors-rsi-2-eur-usd)
- [Weekend gap size effect research (MQL5 article)](https://www.mql5.com/en/articles/23609)
- [EURUSD Monday gap fill statistics (TradeThatSwing)](https://tradethatswing.com/eurusd-monday-gap-fill-strategy-and-statistics/)
- [Gold Asian Breakout EA (MQL5 Market, design reference only)](https://www.mql5.com/en/market/product/166774)
- [Gold Breakout Straddle (MQL5 blog, design reference only)](https://www.mql5.com/en/blogs/post/773794)
- [A Century of Evidence on Trend-Following Investing (AQR)](https://www.aqr.com/Insights/Research/Journal-Article/A-Century-of-Evidence-on-Trend-Following-Investing)
- [Original Turtle rules automated (MQL5 article)](https://www.mql5.com/en/articles/23448)

---

## 5. Cross-AI merge (2026-10-08): Claude + 4 outside audits

The four outside audits are labelled A-D:
- **A:** blunt, unsourced; says to delete the control lane.
- **B:** long and heavily sourced (SSRN, GitHub, backtrex).
- **C:** medium length, unsourced.
- **D:** short and unsourced; ends with a table.

### Everyone agrees (5/5)
- **Fixed 1-2R targets** are not standard. Use time, trailing or structural exits.
- **ATR(M15) as the universal unit** is wrong. Use daily ATR for swing lanes, and session-specific units (opening range, VWAP standard deviation) for intraday lanes.
- **The london box (07-12)** isn't an opening range. A real one is 30-60 minutes.
- **sar:** drop it.
- **swing and dip** are the strongest pedigree. Move them to daily bars with trailing or opposite-extreme exits, and no 2R cap.

### Strong majority
- **Close-based entries** pay away the start of the move. Use stop orders at the level for breakout lanes (A, D, Claude; B says close entry is valid but a *different* strategy).
- **main's entry window is too long:** 07:00-15:59 tests "the box breaks some time today", not the London open. Standard is roughly 07-10 (B, D, plus C indirectly). *Claude's audit missed this.*
- **The trend lane fires at 13:00,** which for gold is before the NY cash open (13:30). Anchor VWAP and evaluation to the cash open (B, D). *Claude missed this.*
- **The pdh and retest stops** at the middle of the range or box are the wrong invalidation. The stop belongs just beyond the broken level (B, A, D).
- **range** should trade only during the Asian session (A, D, Claude), or needs an explicit "range day" condition (B).
- **Keep control** (B, C, D, Claude). A's "delete" is wrong: it's the benchmark.

### Disagreements and how they were settled
- **gapfill:** A and D say it's arbitraged out, C calls it robust. B gives the decisive evidence: across 11,773 gaps, 89% filled, but 88% of matched same-size midweek moves also filled. A high fill rate isn't an edge. **Drop it unless it beats a matched-move control.**
- **fade:** D says reversion beats breakouts in modern FX, C says drop it, B says keep it with a wider stop. Our own data (clearly negative) outranks unsourced claims. **Keep it as a signal, not a lane.**
- **vwap reversion:** A says it reliably beats costs, with no source. B cites a DAX VWAP-band fade that lost at a 59% win rate. **Drop it, or keep it log-only.**
- **bigrev/bigcont market splits:** A and D give *opposite* market assignments. That means no evidence. **Tags only.**
- **nr7:** A calls it robust (no source). B cites PF about 1.02 as an ORB filter. **Use it as a filter.**

### New evidence from B worth keeping
- **A 16-year, 225-cell futures study of ORB variants:** zero cells net-positive after realistic costs ([SSRN 7428398](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=7428398)).
- **A cost-aware intraday study:** baseline ORB, VWAP and momentum are negative after costs ([GitHub intraday-cost-study](https://github.com/padmesharavindan5-dot/intraday-cost-study)).
- **Weekend gaps vs matched moves** ([perfectindicators](https://perfectindicators.com/blog/do-weekend-gaps-fill)).
- **A QuantStone GBPUSD Asian-range breakout test:** it lost even before costs ([QuantStone](https://quantstone.net/en/tools/backtest-lab/strategies/asian-range-breakout-gbpusd/)).
- **Turtle pyramiding** is missing from our swing lane.

### Merged rebuild order
1. **Exit test on existing entries (unanimous):** no target; time exits (close / 24h / 48h) and trailing exits, against control under the same exits.
2. **Units:** daily ATR for stops and sizing on swing lanes; session units for intraday lanes.
3. **Entry:** stop orders at the level (main, london, pdh, nr7).
4. **Session fixes:**
   - main: entries 07-10 only.
   - london: becomes a real 30-60 minute ORB at the London open and at the US500 / Germany 40 cash opens.
   - trend: anchored to the cash open, evaluated around 14:00.
   - range: Asian hours only.
5. **Structural stops:** pdh and retest stops just beyond the broken level.
6. **swing and dip** move to daily bars with trailing exits. dip exits on strength. Test pyramiding on swing.
7. **Drop or demote to signals:** sar, gapfill, vwap fade, scalp, exhaust, bigrev/bigcont, fade. nr7 becomes a filter.

**Honest expectation:** the best-sourced evidence (B's studies plus Claude's MQL5 replication) says intraday breakouts stay cost-dominated even when implemented correctly. The likeliest survivors are the daily trend family (swing, dip), with fixed intraday versions as a secondary bet.
