# US500 fresh-data exam: pre-registered rules and predictions (written 2026-10-13, BEFORE any exam run)

Script: asiabo_exam.py. Modules: `exam_baseline` (step 1, spent data only) then `exam_us500` (step 2, ONE-SHOT).

## The plain version
For four years we've built and judged the core book on data we kept looking at. This exam hands it four years of the US500 it has **never seen** (2016-19) and asks one question: does it still behave like a book with an edge, or like noise? It's like testing a recipe on a new kitchen: same rules, same costs, no tasting first.

## Data
- **Exam:** the never-touched US 500 M1 export (first bar 2015-12-18), bars before 2020-01-01 only. Read from `exam_hold\` (fallback `bars_input\`). bars.db is NEVER changed: the exam builds its own `exam_hold\exam_us500.db`.
- **Partner leg:** GERMANY 40 bars before 2020 copied from bars.db (already spent). Used only by #27 / #28.
- **Scored:** US500 trades ENTERING 2016-01-01 .. 2019-12-31. Warm-ups use the 2 weeks of 2015, so dip (200-day average) starts trading only in late 2016, and #27/#28 (370 days of warm-up) only from 2017.
- **Safety:** the script refuses to run if bars.db already holds US 500 bars before 2020 (the exam would be spent), and refuses to run a second time once `exam_hold\EXAM_DONE.txt` exists.

## What runs (frozen code, real costs, nothing tuned)
- **MAIN TEST:** core book fast + dip on US500 (core_book_v2), via the why phase's own `book_of()`, one position per part / direction.
  - fast: orb30 when er10 agrees + main2 when edge20 agrees, exit at the close.
  - dip: rsi2 long + dip3 long above the 200-day average, own exits.
- **LEADS:** #31 mirror dip (incl. the long-stretch side), #27 gap closes vs #28 relative momentum (asiabo_young code).
- **REPORT ONLY:** brk, ins (shelved). Numbers, no verdict.

## Verdict rules (fixed now)
Per core part:
- **PASS:** net R/trade above the noise bar (**fast > +0.07, dip > +0.15**) AND EDGE > 0.
- **FAIL:** (net < 0 AND EDGE < 0) OR net t ≤ -2.
- **MIXED:** anything else.

**BOOK:** PASS if both PASS; FAIL if either FAILs; MIXED otherwise.

**Why the bars are above zero:** the first draft said "net > 0 and EDGE > 0". On 17 fake random-walk exam files, that rule PASSED pure noise for fast 2/17 and **dip 8/17**: dip's ~30 trades can't tell an edge from luck. The bars were raised above every noise run before any real data was read. With them, noise PASSES 0/17 for both, and fast FAILS on noise 11/17.

**What a PASS means:** "not refuted", not "proven". One standard error is ~0.07 R/trade for fast and ~0.2 for dip, so a real but small edge will often show as MIXED. The exam is good at catching a dead part, weak at confirming a live one.

**Leads:**
- #31 SURVIVES if ALL EDGE > 0 AND long-stretch EDGE > 0; UNREADABLE below 20 trades (noise gave 3-10).
- #27 vs #28: #27 wins if #27 EDGE > 0 (exact mirrors). UNREADABLE below 15 triggers (noise gave 9-16, with EDGE swinging -0.18 .. +0.44), so even a readable result is only a sign for the record.

## Yardstick (17 random-walk exam files, cloud, 2026-10-13)
| | n | net R/trade | EDGE |
|---|---|---|---|
| fast | 153-247 | -0.285 .. +0.066 (t down to -4.1) | -0.117 .. +0.155 |
| dip | 6-42 | -0.467 .. +0.116 | -0.211 .. +0.273 |

## Order of play
1. Ezio moves the 3 files from `bars_input` to `exam_hold` (US Tech 100 is held too, for later tests).
2. Run `exam_baseline`: the same measurement on bars.db's US500 2020-21 and 2024+ (spent data, context only).
3. Both predictions written below. Done 2026-10-13.
4. Run `exam_us500` ONCE.
5. Only then: move the US 500 file into bars_input, build_bars_db, rebuild synth_cache.

## Predictions
**Claude (written 2026-10-13, before the baseline and before the exam):**
- **fast:** n ~150-220. EDGE > 0 but small; net around 0 to slightly negative. 2017 was a record-quiet year, so opening ranges were tiny next to fixed costs. **Verdict: MIXED most likely, FAIL second.**
- **dip:** n ~25-40. Net positive: 2016-19 was a strong US bull market and dip's edge needs index drift (T7). The danger is Q4 2018. **Verdict: PASS slightly more likely than MIXED** (~55%).
- **BOOK: MIXED.**
- brk: EDGE > 0 (steady 2016-17 trend). ins: about 0.
- #31: UNREADABLE (too few trades on one market).
- #27 vs #28: the sign goes to **#28** (the US outran Europe persistently in 2016-19, so relative momentum beats gap-closing). Probably UNREADABLE by count.

**Ezio (2026-10-13 13:18, before the baseline and the exam):** "pretty much" the same as Claude's: fast MIXED, dip leaning PASS, book MIXED. On the pair, his earlier call (2026-10-11/12) was #27 beats #28 ("they usually catch up"). It stays recorded as a disagreement with Claude's #28 unless he changes it before the run.

## Post-exam decision rule (AGREED by Ezio 2026-10-13 13:18)
- **BOOK PASS** → fast + dip go to cTrader paper at fixed risk for a fixed period.
- **MIXED** → no paper yet; keep growing the book.
- **FAIL** → the failing part goes back to the why phase.

## Notes
- **Kept out of this exam:** N3 (fade against-trend breaks). It goes to US Tech 100 later, as its own pre-registered test.
