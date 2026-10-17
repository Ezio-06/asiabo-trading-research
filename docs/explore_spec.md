# Explore: every living candidate on the training data (pre-registered 2026-10-13 ~21:00)

**Ezio:** "build all and test them over our training data first to see what reality says about it."
**Module:** `asiabo_explore.py`, run with `run.bat run explore` (about 40 min). Reads bars.db (sealed 2022-23 never read) plus, for dip only, exam_hold\exam_us500.db and ustech100.db. It is shadow only and changes nothing.

**What this can and can't say:** This is EXPLORATION. The ideas were born on this data, so passing here earns a fresh-data test and nothing more. Failing here is strong evidence: an idea that can't fit its own data is dead.

## Sections (fixed before the run; no tuning)
- **F: fast per market.**
  - The frozen book's fast part runs on all six markets. EURUSD and WTI are T8 controls that should not work.
  - Reports net, EDGE vs coin flip, results per lane (orb30 / main2), and results per era (2014-17 / 2018-21 / 2024+).
- **N5: flat means undecided.**
  - Each fast trade is read at entry + 2h and grouped: up (≥ +0.3R), flat, or down (≤ -0.3R).
  - For each trade and its mirror (opposite direction, mirrored stop, same path), it reports R from 2h to the exit.
  - For the flat group, it reports the best London hours.
  - Run per market, pooled over the book markets, and pooled without gold.
- **N3: fade only against-trend breaks.**
  - Raw orb30 / main2 breaks (exit at the close), split by edge20 at entry into WITH / NONE / AGAINST.
  - FADE = the mirror trade.
  - This is a first look only: the mirror keeps the break's stop geometry, not the "beyond the extreme + buffer" stop.
  - US Tech 100 is NOT used. It stays fresh for N3.
- **N4: the trend option.** Claude fixed one design because the precondition and direction slots were open:
  - Precondition: an inside day with range < 0.4 × ATR20.
  - Entry: the first daily break of the box within 3 days. A day that touches both sides with no gap is skipped.
  - Stop: far side of the box + 1 × ATR50.
  - Time stop: at day 10, out if the trade is below +1R.
  - Trail: 3 × ATR50 chandelier, no target, max 60 days. One position per market.
  - Control: the mirror trade. Costs are on both.
  - Also reports trend legs per market: a zigzag with a 3 × ATR20 reversal on closes, showing the length distribution and the share ≥ 20 / 40 days.
- **DIP: the regime rule (T30).**
  - Skip dip while ATR(w) ≥ 1.3 × its 1-year median AND rising (above its value 5 days earlier).
  - ATR 40 is the candidate gauge (flag: seen first on spent data). ATR 5 / 10 / 20 are shown alongside.
  - Reports skipped vs kept, total R and max drawdown.

## Noise bars (set on 6 fake worlds BEFORE any real run)
The fake worlds were gold, US500, GER40 and USDJPY as random walks with clustered volatility (a log-AR(1) daily volatility) and no direction memory.

| Section | Noise reached | Bar to count as "alive on training data" |
|---|---|---|
| F (one market) | EDGE -0.10 .. +0.06, t -1.8 .. +1.3 | EDGE > +0.08 AND t > +2 |
| N5 (one market, flat group) | -0.15 .. +0.13, t -2.6 .. +1.5 | > +0.15, t > +2, mirror ≤ 0 |
| N5 (book without gold, pooled) | -0.08 .. +0.03 | > +0.06 AND t > +2 |
| N3 (one market, AGAINST fade EDGE) | -0.10 .. +0.13, t up to +2.6 | > +0.14, t > +2.6, AND fade NET > 0 |
| N4 (pooled EDGE) | -0.04 .. +0.08, t ≤ 1.3 | > +0.10 AND t > +2 |
| DIP (pooled skipped minus kept, ATR 40) | -0.18 .. +0.40, t -0.6 .. +2.0 | < -0.35 AND t < -2 |

On top of the bar, the idea must be positive in at least 2 of the 3 eras.

**Noise lessons (already learned before the real run):**
- On a single noise world, against-trend RIDE EDGE reached t +2.1, and USDJPY's fade EDGE reached t +2.6. One market's t ≈ 2 is not a signal here.
- In EVERY noise world, N4's top 5% of trades carried the entire total. "The tail pays" is what noise looks like for a trail-and-time-stop design; only EDGE vs the mirror counts.
- On noise, the dip rule's skipped trades usually did BETTER than kept ones (skipped minus kept was positive in 4 of 6 worlds). A negative real result is therefore not a mechanical artefact.

## Predictions
**Claude (locked 2026-10-13, before any real run):**
1. **F:**
   - Gold clears its bar (already known from spent data, so this is not a test).
   - Germany 40 and USDJPY: EDGE small and positive, below the bar.
   - Book without gold: t < 2.
   - EURUSD / WTI: ≤ 0.
2. **N5:**
   - Gold's flat group clears its bar (known).
   - Every other market's flat group is inside the noise.
   - Book-without-gold pooled is below its bar: the effect is gold's (COMEX / US data).
3. **N3:**
   - The AGAINST fade fails its bar everywhere: fade NET < 0 after costs on every market.
   - Fade EDGE is ≤ 0 on gold, and on the indices it sits at about 0 to slightly positive.
4. **N4:**
   - Fails (pooled EDGE t < 1).
   - Gold and the indices have median trend legs of 20-30 days.
5. **DIP:**
   - ATR 40 clears its bar pooled.
   - This is mostly a reproduction (Claude saw US500 2020+, GER40 and US Tech 100 in the cloud slip), so it proves little.

**Ezio:** (to write before `run.bat run explore`)
