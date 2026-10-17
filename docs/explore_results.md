# Explore results: what the training data says (run 2026-10-13 21:37, reports\explore_20261013_213755)

> **Correction (2026-10-13 ~23:00): the trend-option ("N4") numbers below are BIASED UPWARD.** The break was read on daily bars, and days that touched both sides of the box were skipped. That picks trades by how the day ended (ledger T33). The corrected numbers come from `trendwhy` (trendwhy_spec.md), which reads the break in time order on M15 / M1 bars. Ezio's view on the index split: indices are "the whole bazaar", a different kind of market, not a failure (theory_notebook.md, trend option section).

Spec, noise bars and Claude's locked predictions are in explore_spec.md. Ezio ran it before writing his predictions, so only Claude's were on record.

**Reminder:** this is training data. Clearing a bar earns a fresh test, nothing more.

## Scoreboard against the noise bars
| Idea | Key number | Bar | Verdict |
|---|---|---|---|
| fast, gold | EDGE +0.20 (t 3.0), all 3 eras + | +0.08, t 2 | ALIVE (already known) |
| fast, GER40 | EDGE +0.10 (t 1.3); eras -0.14 / +0.29 / +0.02 | | not alive |
| fast, USDJPY | EDGE +0.07 (t 1.0) | | not alive |
| fast, US500 | EDGE +0.04 (t 0.6) | | not alive |
| fast, book without gold | EDGE +0.07 (t 1.7) | | leaning, below the bar |
| fast, controls (EURUSD, WTI) | EDGE +0.03 (t 0.9) | | inside noise, as T8 says |
| N5, gold flat-at-2h | +0.42 (t 2.9), mirror -0.25, eras +0.16 / +0.59 / +0.58 | +0.15, t 2, mirror ≤ 0 | ALIVE |
| N5, USDJPY flat | +0.14 (t 1.4), mirror -0.03, eras +0.21 / 0.00 / +0.22 | | just under the bar |
| N5, book without gold pooled | +0.11 (t 1.5), mirror -0.05, all 3 eras + | +0.06, t 2 | leaning, below the bar |
| N3, against-trend fade | fade NET < 0 on all six markets; pooled -0.12 (t -4.1) | fade net > 0 | **DEAD** |
| N4, trend option (one design) | pooled EDGE +0.33 (t 3.8); eras +0.25 / +0.35 / -0.12 | +0.10, t 2, 2 of 3 eras | CLEARED, but **biased: see the correction above** |
| DIP, ATR 40 regime rule | pooled skipped minus kept -0.56 (t -1.6) | < -0.35 AND t < -2 | **fails the t bar** |

## Claude's predictions vs reality
- **fast:** right. Gold is real; nothing else clears; the book without gold is under t 2.
- **N5:** right on the bar (gold only), but wrong in spirit. USDJPY's flat trades also gain in the afternoon, and their best hour is also 13:00 London (US data, 08:30 New York). The pooled number without gold is positive in all three eras. The "US money arriving" payer may be wider than gold. EURUSD (also hit by US data) shows nothing, but fast has no edge there to begin with.
- **N3:** right. Against-trend breaks do NOT reverse. On US500 the against-trend RIDE even had EDGE +0.13 (t 2.1).
- **N4:** wrong. I predicted t < 1; it came out t 3.8 (before the correction). Trend legs (median 22-28 days on gold and the indices) were as predicted.
- **DIP:** wrong. I predicted it would clear; it fails the t bar.

## N4 in detail (biased numbers, kept for the record)
| Market | n | EDGE (t) |
|---|---|---|
| USDJPY | 51 | +0.42 (3.6) |
| gold | 28 | +0.51 (1.9) |
| WTI | 12 | +0.47 (1.8) |
| EURUSD | 34 | +0.28 (1.6) |
| US500 | 12 | -0.09 |
| GER40 | 16 | +0.01 |

- **Not an index effect.** It works on FX / gold / oil and is flat on the indices. Ezio: an index is the whole bazaar, a different kind of market.
- **The EDGE comes mostly from the mirror losing.** Net +0.18 (t 1.4) vs mirror -0.48 (t -5.9).
- **The shape is not Ezio's theory.**
  - Losers are mostly full price stops: 48 at -1.03R.
  - Time stops (51) are small WINNERS at +0.22R, not small losers.
  - Trails: 49 at +0.96R. Max-hold exits: 5 at +3.66R.
  - The top 5% carry the whole total (+39.9R of +27.3R), but every noise world did that too.
- **2024+ is negative** (n 25, -0.12).
- **Power problem.** About 15 trades a year across six markets. Ezio decided (2026-10-13) against new market exports for now.

## DIP regime rule in detail
- **US500:** 6 skipped trades at -1.52 (t -2.8 for skipped minus kept). Total R +23.5 → +32.6; max drawdown 11.6 → 3.8.
- **US Tech 100:** skipped minus kept -0.65 (t -1.7).
- **Germany 40: the opposite.** 7 skipped trades at +1.05.
- **Pooled:** -0.56 (t -1.6). Total R +48 → +58; max drawdown 33 → 21.
- The rule rests on a handful of trades: 32 skipped across 4 datasets. One fresh index (US 30, about 100 dip trades, about 10 skipped) can't settle it. Downgrade from "candidate rule" to "plausible, unproven; maybe a risk tool rather than an edge tool".

## Lessons
- **Real trend legs look like a random walk's.** The zigzag (3 × ATR20 reversal) gives median legs of 22-28 days on real markets and 25-32 days on the noise worlds. Leg-length distributions are geometry, not proof of trends; they can't set a time stop by themselves. (Same family as T29: give-back is geometry.)
- **With-trend breaks follow through** (pooled ride EDGE +0.079, t 3.0: T1 again).
- **"Against-trend" doesn't mean "weak":** no market fades profitably. N3 joins the graveyard.
- **Noticed after the fact, not tested:** the "up at 2h" group gains in the afternoon too on GER40 (+0.60, t 2.5) and pooled (+0.29, t 2.0). Not pre-registered; it would need its own test.
