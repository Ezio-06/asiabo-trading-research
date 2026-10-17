# Retirement report: the trading-bot research project (2 Aug – 16 Oct 2026)

**Status: RETIRED, 2026-10-16.** Not killed. Packed so it can be picked up again.
**Sources:** the 37 research notes (`docs/`), the run log (`runs.csv`) and the code in this folder. Research direction and the keep / kill decisions are Ezio's; the starting strategy came from an experienced retail trader. Everyone involved, and the tools used, are listed under "Who did what" in README.md.

---

## 1. The short version

The project set out to build a small, multi-strategy trading bot (cTrader, starting on gold) that earns about 1-2% a month with tight risk control. It turned into a research lab: 13 years of 1-minute bars for six markets, a test framework that compares every strategy to coin-flip trades and fake markets, and about 30 ideas tested under rules fixed before each run.

**The honest bottom line:**
- **No deployable edge was found at retail CFD costs.** Nothing that cleared every test also survived fresh data at a size that would pay the 1-2%/month goal.
- **Two things are real but small:**
  - buying dips in stock indices: real on two fresh-data tests, but only about +0.1 R a trade, roughly a fifth of its training size;
  - the intraday breakout ("fast") on gold: real on all spent data, never tested on fresh data.
- **The biggest result is not a strategy. It's the method:** pre-registered predictions, noise bars set on fake markets before real runs, a coin-flip twin for every trade, and data kept sealed until a single final test. That method killed bad ideas quickly and honestly, including several of ours that looked great at first.
- **Why it stops here:** Ezio's own reading on 2026-10-16. Solo retail trading lacks what a sustainable field needs (skills that compound, steady income, a team, a lasting edge). The project went as far as it reasonably could.

---

## 2. Timeline

| When | Phase | What happened |
|---|---|---|
| Aug – early Oct | **Live bot era** | Cashbotas on cTrader (gold, Asian-range breakout, then "lanes": many small strategies that earn their way from shadow to live). Equity Pulse risk system (Ezio's design). The earlier fibrev bot was shut down before this. |
| 5-7 Oct | **Offline lab** | `asiabo_offline.py` + `bars.db` (gold back to 2013, then US500, EURUSD, USDJPY, WTI, Germany 40, Japan 225). "House" money-management design. `asiabo_lab.py`: signals, theory reads, probe. Verdict: no tradeable edge yet; costs vs noise explains why lanes lose. |
| 8 Oct | **Power run + audit** | Every trade compared to a coin flip. Breakout direction has real but cost-sized power. Audit against public bots and papers (plus 4 outside AIs): our exits, stop units and entries were non-standard. |
| 9 Oct | **Frozen book v1** | Four parts (brk, ins, dip, fast), fixed rules. Synthetic "cousin" histories: the 2024+ profit lives in multi-month trends. |
| 10 Oct | **Why phase + engines** | Why phase removed brk and ins → core book = fast + dip. Causal engine: breakouts are momentum bets; dip is NOT mean reversion. Pocket hunt: 1 of 44 confirmed (chance level). Momentum switch and ladder: not adopted. |
| 11 Oct | **One launcher + realism** | `run.bat` / `asiabo.py` / `modules.json`. Probe: real trends are shorter and harder to read than noise; volatility IS readable. Fake-market generator v7 → v8 with a realism gate. |
| 12 Oct | **Younglings + Ezio's theories** | New ideas (mirror dip, squeeze, index pairs) through real data, fakes and placebos. Ezio's theory notebook started (fuel/refuel, the gate, fade against-trend breaks). |
| 13 Oct | **Fresh-data exams** | US500 2016-19: fast FAILED, dip MIXED. US Tech 100: dip real but small; Ezio's drift sizing inside the noise. Volatility worlds, dipvol, explore. Trend-option test built (`trendwhy`), never run. |
| 14 Oct | **Scope reset** | V-model adopted; goal scoped down to "short-term deterministic profitability with failure foresight"; loss limits 5% daily / 30% lifetime. |
| 16 Oct | **Retired** | This report. |

---

## 3. Where every idea stands at retirement

Units: **R** = profit per trade in units of the risk taken. **EDGE** = our trade's result minus its coin-flip twin (same timing, stop, exit and costs): the pure value of the direction call. **t** ≈ how many standard errors from zero (about 2+ starts to mean something; noise here often reached 2-3).

### Alive (real but small, or untested on fresh data)
| Idea | Plain description | Best evidence | Status |
|---|---|---|---|
| **dip** | Buy an index after 3 down closes / RSI(2) < 10 while above its 200-day average; out on strength | Fresh US500 2016-19: net -0.11, EDGE +0.09 (31 trades). Fresh US Tech 100: net +0.10, EDGE +0.23 (110 trades). Training was +0.55 to +0.76. | **Real but small.** Over half of it is just "long an index in an uptrend" (random days earn +0.23 of its +0.40). Worst year 2018 in both tests. |
| **fast, on gold** | Intraday breakout of the 30-min opening range / overnight box when short-term trend agrees; out at the close | Gold EDGE +0.21 (t 3.0), positive in all 4 eras; 546 trades | **Real on spent data only.** Failed on fresh US500 (never real there). Gold 2022-23 is the one fresh test left (sealed). |
| **Flat means undecided** (Ezio) | Don't time out a fast trade that's flat at 2 hours; its afternoon pays | Gold flat group +0.42 (t 2.9), coin-flip twin -0.25, all eras; money arrives 13:00-14:00 London (COMEX open + US data) | **Lead on spent data.** USDJPY shows a weaker version at the same hour. Needs fresh gold. |
| **Trend option** (Ezio's idea, one test design) | After a very quiet day, enter on the first break; wide stop, 10-day time stop, trail | +0.33 (t 3.8) on FX / gold / oil, flat on indices | **Number is biased upward** (entry read on daily bars, see lesson M9). The corrected test `trendwhy` is built and ready, never run. |

### Shelved (real mechanism, not worth trading as built)
| Idea | Why shelved |
|---|---|
| **brk** (multi-day breakouts, 5-day trailing exit) | Removed by the pre-registered why-phase rule: without its best market-year it was ≤ 0 in 3 of 4 eras. Causally a momentum bet; a 40-day straightness switch doubles its edge, but the days it switches off still earn. Fresh US500: net -0.52. |
| **ins** (inside-day breakout, exit at the close) | Strongest mechanism evidence (narrower inside days pay more, t -3.0), but the effect is smaller than the spread. |
| **Mirror dip** (Ezio, #31) | Short the start of a pullback in a stretched trend. Weak lead (EDGE +0.06); the long-stretch side +0.14 (t 2.3, only 35 trades), sits in the middle of realistic fake markets. |
| **Dip volatility rule** | Skip dip while 40-day ATR is high and rising: failed its bar (t -1.6, rests on 6 US500 trades). Maybe a risk tool (drawdown 33 → 21 R), not an edge tool. |
| **Ezio's drift-sizing table for dip** | Inside the noise on US Tech 100 (it almost never bit on a strong-drift index). Right direction in bear spells on fake markets, but too slow. |

### Dead (tested and failed; don't rebuild on them)
- **Fade against-trend breaks** (Ezio's N3): loses after costs on all six markets (pooled -0.12, t -4.1). Against-trend breaks don't reverse.
- **Squeeze breakout** (#19): the break moment itself is the losing part (you buy the top of the burst).
- **Ladder** (re-enter a trend in rungs): never beat a plain on/off switch; worst on real data.
- **Turtle 55/20:** its clock was slower than real trends.
- **Learned scores / one P(win) model / fibrev's weighted voting:** pooling faint signals into one learner drowns them.
- **Sizing up after good stretches** (trailing Kelly): lost about 40 R a year. Fixed-fraction sizing wins.
- **Canary sizing** (cut size after weak weeks): weak weeks were followed by BETTER trades.
- **Pocket hunt round 1:** 1 of 44 pockets confirmed; chance alone gives 0-2.
- **From the early lab:** turn of month, pre-FOMC drift, news blackout, confidence gate, merit entry, mirror of a bad trade, gold's time zones copied to other markets.
- **The old lane machine's promotion rules** (promote after good runs, bench after bad runs): built anti-timed, because recent form reverses at this scale.

### Never got to (open ideas, written down in `docs/`)
- Fuel/refuel cycle (Ezio's N1) and the gate (N2), in `theory_notebook.md`.
- Causal breakout (#33: only take breaks with a real cause: news timing, breadth, weight, hold), in `lane_ideas_30.md`.
- Shadow trades as market sensors (#32), in `sensor_pairs.md`.
- The other ~25 ideas in `lane_ideas_30.md`.

---

## 4. What the data taught about markets

These are the findings that held up across tests. Numbers come from `docs/theory_ledger.md` (T-numbers) unless noted.

1. **Costs, not direction, kill short trades** (T3, HIGH). A round trip costs about 0.15-0.25 of a 15-minute ATR, and price wanders about 2.3 of those ATRs in 4 hours. Tight stops sit inside the noise. Public replications agree: opening-range breakouts beat random by about the size of a CFD spread.
2. **Breakouts only pay with momentum, and that's causal** (T1, HIGH). On fake markets bent toward momentum vs snap-back, the breakout edge moved from -0.27 to +0.52 per trade (t 6.6).
3. **The profit lives in multi-month trends you can't see coming** (T4). Shuffle history in 2-6 week blocks and the 2024+ profit disappears; shuffle in 8-26 week blocks and it comes back. Trend detectors spot trend months no better than chance.
4. **Recent form reverses** (T5, T22). A lane's hot streak is followed by worse trades (z 4.1); weak weeks by better ones. Never size up after a hot streak.
5. **Real trends are short and soft.** Real daily data has fewer and shorter straight runs than its own day-shuffled copy. Trend detectors work at noise level on real data; **volatility is the readable state** (10-day ATR: 78% precision, about 8 days lag).
6. **Index dip-buying is mostly index drift.** Its payer is the index going up over time, plus a small fee from forced sellers. It shares the momentum regime with breakouts, so it diversifies less than it looks.
7. **Different markets have different quirks** (T8, T34). Gold carries the intraday breakout; indices carry dip-buying; EURUSD (the most efficient major) carries almost nothing. Ezio's "whole bazaar vs one stall" for indices vs single markets.
8. **Give-back is mostly geometry** (T29, T32). A random path gives back as much open profit as a real one. Exit rules reshape results but can't create an edge.
9. **Protect a strategy on its payer's clock** (T26). Gauges on the trade's own fast clock can't tell food from poison; dip's real enemy is a long stress regime, which only a slow gauge sees.

---

## 5. What the project taught about method (the part that transfers)

This is the most reusable output, for any data, market or field.

- **M1. Predictions before results.** Both people write what they expect, then run once. Scored predictions showed both of us were too optimistic on the core book.
- **M2. Noise bars before real runs.** Run the exact test on fake random markets first and set the pass bar above everything noise produced. Both exams needed it: a "net > 0" rule passed pure noise for dip 8 times out of 17.
- **M3. A coin-flip twin for every trade** (EDGE). It separates "is the direction call worth anything" from "did costs and the market's path help or hurt".
- **M4. Cousin histories as a yardstick.** Day-shuffled and block-shuffled copies of real data show which part of a result needs the real order of events.
- **M5. Fake markets need a realism gate.** Our first fake worlds were too trendy, so momentum ideas looked too good. v8 is checked against real statistics before use.
- **M6. Test every gauge on known-truth data first.** fibrev's weighting formula could not see a real edge even at 200 samples; a 5-minute planted-edge test would have shown it.
- **M7. Skipped vs kept.** A filter whose skipped trades earn the same as its kept trades is a size cut, not a filter (T28).
- **M8. Spend fresh data sparingly, once, with a coverage check first.** The US500 exam found thin early-hour data only after scoring.
- **M9. Never let the end of the bar choose which trades exist** (T33). Reading entries on daily bars silently removed bad trades from the trend option.
- **M10. Combine simply; the scorecard may only switch things off.** Learned blends drowned faint signals; promotion on recent form is anti-timed.
- **M11. Match the test window to the edge size.** A +0.08 R edge needs about 1,300 trades to show at z = 2. A 40-trade promotion rule judges noise.
- **M12. Name who pays.** A theory that can't say who loses money to you, and why, isn't finished.

**Mistakes we made (kept on record):**
- A mechanics check once ran on real spent data before Ezio's prediction existed (dipvol). Rule since: mechanics tests on fake data only.
- Several one-shot runs went ahead before Ezio's prediction was written, so only the assistant's was on record.
- Market lists were chosen with hindsight (T8). That's why "fast = gold" still needs its own fresh test.
- The explore run's trend-option entry bias (M9).

---

## 6. What carries over to stocks

Stocks are the natural next market. Here is what applies there and what doesn't. These are research findings, not financial advice.

**Carries over directly:**
- **The whole method** (section 5). It's market-agnostic.
- **Index drift is the payer.** The dip work found that most of dip's profit was simply being long a rising index. Timing the dips added a small extra. That fits the standard evidence for broad, long-held index exposure.
- **Costs dominate short holds.** The lower the turnover, the less of any edge goes to spread and commission.
- **Recent hot form doesn't persist** at the strategy level, and multi-month trends drive most returns. Both point away from chasing recent winners on short clocks.
- **Code:** the bar database builder, the fake-market generator, the launcher and the coin-flip / noise-bar test harness all work on any time series.

**Forex/CFD-specific (doesn't carry over as is):**
- Broker sheets, commissions and swaps per symbol (gold, EURUSD, USDJPY, WTI, Germany 40, US500).
- Session clocks (Asian box, London open, COMEX open) and the gold intraday findings.
- Overnight swap: long CFD holds cost about 5-8% a year on gold, EURUSD and WTI at Ezio's broker. That's a CFD cost, not a stock cost.
- Minimum position sizes vs a $10k account (Germany 40 was too big on 76% of trades).

---

## 7. If this is ever picked up again

**First, read:** this report, then `docs/session_handoff.md` (how we worked), `docs/theory_ledger.md` (bottom = newest), `docs/theory_notebook.md` (Ezio's theories).

**Ready to run (training data only, spends nothing):**
1. `run.bat run trendwhy`: the corrected trend-option breakdown. Ezio's predictions go into `docs/trendwhy_spec.md` first.

**Fresh data still unspent (spend once, with a written test):**
| Data | Where | Natural test |
|---|---|---|
| **2022-23, all six house markets** | inside bars.db, locked out by the code | fast on gold + "flat means undecided" (about 100 fast trades: can refute, can't prove) |
| **Japan 225** | inside bars.db, never read by any lane | dip on a weaker-drift index; the bazaar theory (trend option shows nothing on any index) |
| **US Tech 100** | `exam_hold\` | spent for dip; still fresh for fuel/refuel and causal breakout |
| **US 30** | not exported yet | dip volatility rule |

**Before trusting anything old:** re-check costs against a current broker sheet, and append recent months to bars.db as genuinely new data (`build_bars_db.py`).

**Rough size to expect:** the core book (fast + dip) made about +0.5 / -0.4 / +7.3 / +3.4 %/yr across the four training eras at fixed risk, before shrinkage on new data. That's below the 1-2%/month goal in every era.
