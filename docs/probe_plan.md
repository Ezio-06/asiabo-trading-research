# Probe study (Phase 1): definitions, predictions, yardstick (2026-10-11, BEFORE the real run)

Script: asiabo_probe.py. CLI module `probe` = real data, then a dayshuffle s1 cousin, then the cousin deleted (~30 min est.). `probe_cheap` = M1 M2 M4 M5 only. 6 markets (XAUUSD US500 EURUSD USDJPY XTIUSD GERMANY40), sealed years never read, every t clustered by market x month. Measures only; decides nothing.

## Definitions
- **M1 trend end:** er40 spell = consecutive days with er40 >= 0.30 and the same sign. REAL spell = lasted 10+ days (most spells are 1-2-day flickers; median length 2 days on noise). From the end day's open, the next 5 / 10 / 20 days in the old trend's direction, in N. Continue >= +0.5 sqrt(h) N, reverse <= -0.5 sqrt(h) N, chop between. Compared with mid-spell days and any day. Split by blow-off / fade / rollover and by length.
- **M2 hazard:** survival by age; ratio hazard(21-40) / hazard(6-20), with a bootstrap band.
- **M3 failed shadow:** book brk / fast trades stopped out (gross <= -0.95R). Reverse at the next M15 open, stop 1 risk unit, target 1.5, 5 days, gross R. Control: 3 random days, same market / era / local minute / stop in ATR / direction. Split by failure speed and er40.
- **M4 correction:** peak stretch of the last 5 closes from their 20-day average (in N) × the FIRST close below the prior 3-day low (mirror for down). The next 1 / 3 / 5 days against the stretch. Per market, plus #31's straight-20-days condition. Changed during the build: a crack at the moment of peak stretch fired only 5 times in 6 markets × 11 years, so "stretched, then first crack" it is. Not the #31 lane (Phase 3).
- **M5 seeing speed:** hindsight truth = centred 41-close er >= 0.30 (trend), centred 20-day TR >= 1.25 × trailing 250-day mean (high vol). Detectors SMA / EMA 5-200 (price beyond an average sloping the same way over 5 days), er10-60, ATR5-50. Lag = the first day the detector agrees and holds for 5 days. The known-truth synth version is deferred to Phase 2.
- **M6 serial dependence:** non-overlapping book trades per market. P(L|L) vs P(L); 500 order and 500 month-block shuffles. Skip line = E[net] - E[net|L] (vs a random skip), mirror line = extra mirror gain after a loss; CROSSED only above the shuffles' 95th percentile.

## Predictions
**Ezio:**
- M1: chop > reverse > continue.
- M2: the hazard rises after ~20 days.
- M3: no prediction.
- M4: stretched + cracked falls more than random, clearest over 3 days, on the mirror-dip markets (EURUSD, XAUUSD, XTIUSD, USDJPY).
- #31 (Phase 3): a small win rate (chop hits most stops); best on dip's weakest markets.

**Claude:**
- M1: chop ~45-50%, continue ≈ reverse, inside the yardstick; blow-offs reverse more than fades.
- M2: no rise beyond the cousin.
- M3: equal overall; the fastest failures (<= 1h) a little better.
- M4: a small correction in XAUUSD / XTIUSD / EURUSD (t ~2), none in the indices.
- M5: er20 fastest with tolerable false alarms; SMA/EMA lag ~L/2; ATR5-10 sees high vol within days.
- M6: inside the shuffle band everywhere; no line crossed.

## Yardstick (3 fake random-walk histories, 6 markets)
- **M1:** all t -1.9 .. +2.4. Real spell end h 10: continue 16-25%, chop 51-62%, reverse 19-25%.
- **M2:** on noise the hazard FALLS with age (1-5 d 0.25, 6-10 0.11, 21-40 0.07) and bumps up at 41-60 (window effect). Ratio 0.65-0.82, bands up to 1.08. Ezio's rise needs a ratio > ~1.1 AND above the cousin.
- **M3:** all t -2.6 .. +2.4 → needs |t| ~3.
- **M4:** all t -2.1 .. +2.1 → needs |t| ~2.5, the same sign on 1 / 3 / 5 days, above the no-crack row and the cousin.
- **M5:** the hindsight truth shares 20 days with the detectors' windows, so noise scores too:
  - precision: sma / ema 10-17%, er20 28-29%, er40 25-28%
  - lag: er20 3-4 d, er40 8-21 d
  - Real information = beating these.
- **M6:** single shuffle percentiles hit 0.2% and 99% on noise; count only when both shuffles agree beyond 2.5 / 97.5 and the cousin doesn't show it.
- **Identity check:** the per-market book = the all-markets book (IDENTICAL on 3 fake seeds and the cousin).
