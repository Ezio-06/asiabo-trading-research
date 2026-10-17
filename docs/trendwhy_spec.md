# The trend option: how we won, how we lost (pre-registered 2026-10-13 ~23:00)

**What the trend option is:** bet BEFORE a trend shows. After a very quiet day (an inside day narrower than 0.4 × the normal daily range), enter on the first break out of that day's box. The stop sits beyond the box + 1 × the 50-day ATR. If the trade isn't up 1R by day 10, get out (the "option" expired). Otherwise trail it (3 × ATR50, no target, max 60 days). Every trade has a mirror twin for comparison.

**Why this test (Ezio's rule, 2026-10-13):** the idea already beat its noise bar. The next step is not another disproving test. It is WHY: how we won, how we lost, and what we can't explain, with our theories written down first.

**Module:** `asiabo_trendwhy.py`, run with `run.bat run trendwhy` (about 20 min). Training data only.

## Measurement fix found while building (disclosed before any real run)
The first look (explore) read the break on DAILY bars and threw out any day that touched both sides of the box. That decides which trades exist by looking at the end of the day: a day that broke up and then fell through the whole box (bad for us) was quietly removed. This flatters the result.

The breakdown reads the break in time order on 15-minute bars (1-minute inside a bar that touched both sides), and the entry day only counts price action after the entry.

**So explore's +0.33 is biased upward by an unknown amount.** This run also gives the corrected headline.

**Noise worlds with the fix** (6 fake worlds of gold / USDJPY / EURUSD / oil, random walks with clustered volatility):
- Pooled EDGE -0.08 .. +0.12 (t up to 1.6).
- One extra 2-market world reached +0.24 (t 2.6).
- The break day itself made a little money in all 6 noise worlds (about +0.02R a trade): a small mechanical tilt to remember when reading section A.

## What it reports
- **A. Where the money arrives:** the break day vs days 2-10 vs after day 10, for the trade and its mirror.
- **B. Outcome types:**
  - BIG WIN: ≥ +2R.
  - SMALL WIN.
  - TIME WIN: up at day 10 but under +1R. The theory doesn't predict this one.
  - FAST WRONG: price stop within 3 days.
  - SLOW WRONG.
  - NO TREND: expired at a loss.
  - GAVE BACK.
- **C. Winners vs losers by entry condition (descriptive, never a filter):**
  - box tightness
  - gap vs touch entry
  - break on day 1 / 2 / 3
  - with vs against the 50-day slope
  - whether the break day closed beyond the box or fell back in

Single markets (gold, USDJPY, EURUSD, oil) pooled and one by one; indices shown apart, for comparison only.

## Theories written BEFORE the run
### Claude
**Corrected headline:**
- Single-market EDGE drops but stays above noise: between +0.10 and +0.30, t ≥ 2.
- If it falls inside the noise (≤ +0.12), the first look was mostly the measurement bias, and I'll say so.

**How we win (theory: a quiet day hides an imbalance; the break shows which side gave up, and late chasers carry it):**
- Most of the money arrives on days 2-10, not on the break day (break day < 25% of the trade's total).
- BIG WINS are few (5-10% of trades) but carry more than the whole total.
- Big wins mostly closed the break day beyond the box.
- Tighter boxes win more.
- Breaks WITH the 50-day slope win more than breaks against it.
- A break on day 1 beats a break on day 3: a late break means the coil leaked.

**How we lose:**
- SLOW WRONG is the main loss: about 25% of trades at -1R.
- FAST WRONG is rare (under 10%): the stop beyond the box survives day-one noise.
- Breaks where the break day fell back inside the box are the losers' home.
- Gap entries do worse: we're entering after the move, at a worse price.

**What I expect we can't explain:**
- TIME WIN is again the biggest single group, about 35-45% at about +0.4R. The theory says "no trend came" trades should be small losers, but they end slightly up.
- My guess is a slow drift in the break direction (a weak trend, not none), but that's a guess.

**Mirror:** loses mostly through SLOW WRONG and NO TREND, i.e. the opposite side bleeds slowly rather than getting smashed.

### Ezio
(to write before `run.bat run trendwhy`: what kind of trades win, which lose, and why)
