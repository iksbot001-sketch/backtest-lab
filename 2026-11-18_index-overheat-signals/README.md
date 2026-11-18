# 2026-11-18 Index Overheat / Oversold Signals (PER, PBR, 200-day disparity, forward PE, VIX, F&G, Fed funds)
Korean original: [README.ko.md](README.ko.md)

## Summary
Tested whether z-scores (σ distance from the trailing 10-year mean) of valuation (PER, PBR) and 200-day moving-average disparity predict subsequent index returns well enough to serve as buy/sell/weighting signals for S&P 500, NASDAQ 100, SOX, KOSPI and KOSDAQ, using pre-registered criteria J1–J4 (src/PREREG.md).
Of 24 primary tests, none qualified as a signal or reference indicator. Only KOSDAQ PBR passed J1 and J4, but with just two undervalued episodes whose 12-month returns are resolved it is On Hold; all others are Rejected (src/RESULTS.md, src/out/report.json).

## Why (purpose and context)
The owner wanted per-index overheat/oversold levels ("start selling above X, buying is fine below Y") and asked whether the 2026-06-22 KOSPI peak and the June–July drop could have been anticipated. They later supplied five Bloomberg charts from a broker broadcast (SOX/NASDAQ 100/S&P 500 forward PE ±1σ, SOX 200-day disparity) and asked for the same validation (src/PREREG.md sections 7–8).
Claude did design, core computation and verdicts; Antigravity did source research, chart digitization, three independent recomputations and three red-team reviews.

## What was tested
- Hypothesis: higher z (overheated) → lower subsequent 12-month returns (also 3-month for disparity and forward PE).
- Indicators/markets: KOSPI and KOSDAQ PER/PBR (KRX [11007]); S&P 500 PER (S&P-compiled earnings from Shiller's public data, quarter-end values + 3-month lag; initial multpl series dropped for interpolation leakage) and PBR (quarterly, +3 month lag); 200-day disparity for five indices (Yahoo); forward PE for three indices (digitized from photos, weekly 2016-11–2026-11).
- z windows: valuation trailing 120 months (min 96); disparity trailing 2,520 trading days (min 2,000); forward PE trailing 260 weeks (min 156; shortened because only 10 years of data exist). Chart-style full-sample mean/σ used only for comparison.
- Rules: month-end signal → next month's first trading-day close; weight map z≤−2 100% / −2..−1 80% / neutral 60% / +1..+2 40% / ≥+2 20%; cash 0%; 5 bp one-way.
- Verdict: J1 Newey-West t ≤ −2 and Bonferroni (valuation 8 tests 2.73, disparity 10 tests 2.81, forward PE 6 tests 2.64); J2 ≥3 resolved overheated and undervalued episodes each; J3 strategy Sharpe > constant 60% and circular-shift placebo top 10%; J4 same sign in the second half. All = Signal; J1+J4 = Reference indicator; episodes <3 = On Hold; otherwise Rejected.
- Exploratory (no verdict): VIX (monthly max ≥30, monthly average ≤14), CNN Fear & Greed (2011+, pre-2021-02 third-party reconstruction), Fed funds level, 12-month change and gap to 10-year mean.

## Results
| Combination | t 12m | t 3m | Placebo | Verdict |
|---|---|---|---|---|
| KOSPI PER / PBR | +0.39 / −1.52 | — | 21% / 70% | Rejected / Rejected |
| S&P 500 PER / PBR | +0.61 / −0.19 | — | 44% / 16% | Rejected / Rejected |
| KOSDAQ PER / PBR | +0.31 / **−4.31** | — | 37% / 82% | Rejected / **On Hold** |
| Disparity S&P·NDX·SOX·KOSPI·KOSDAQ | +0.92·+1.08·−0.76·−0.11·−2.09 | +0.76·+1.78·−0.01·+1.28·−0.21 | 5·4·54·6·66% | all Rejected |
| Forward PE SOX·NDX·S&P | −0.92·−0.32·+0.12 | −0.72·−0.27·−0.13 | 27·27·15% | all Rejected |
- KOSDAQ PBR: non-overlapping 12-month t median −2.02 (range −1.32 to −2.43); resolved undervalued entries only 2022-09 and 2024-09; z≤−2 never occurred. 2026-01 z +2.06 flagged overheating just before the April peak (1,226).
- KOSPI 2026: PER z +2.11 (Apr) and +2.88 (May) flagged overheating ~2 months before the 6/22 peak, but the index rose a further 31%; PBR z had been overheated since 2025-09, after which the index rose 164%.
- Disparity: 3-month t mostly positive → short-term trend continuation; for S&P, NDX and KOSPI the contrarian weighting was worse than random timing.
- Chart reproduction: SOX disparity mean 5.82%, ±1σ +24.3/−12.7%, 11-09 value −7.45% match the chart; digitized forward PE mean/σ within 0.07x of chart labels.
- 12 months after VIX ≥30: KOSPI and NDX beat average even ex-crisis years; S&P 500 edge disappears ex-2008/2009/2020 (9.5% vs 9.9%). Extreme fear (F&G) underperformed in the official CNN period. Fed funds variables NW |t| < 1.6.

### Daily / short horizon (PREREG section 9)
- Events where daily z crossed below −1σ (buy) or above +1σ (sell); 20-trading-day excess return vs 10,000 random-date draws (14 tests, Bonferroni one-sided p<0.0036, 60-day event spacing). 0 of 7 indicators passed (5 disparities, KOSPI PBR, approximated daily KOSDAQ PBR). Lowest p 0.029 (KOSDAQ PBR buy, 7 events) depends on 2020-03-12 alone. Daily weighting underperformed the exposure-matched constant in 6 of 7. Antigravity calc4 matched; review4 PASS.

### Additional robustness checks (PREREG sections 10-12, partly exploratory)
- **S&P 500 P/E source replaced (s10):** multpl.com turned out to be Shiller's monthly linear interpolation, leaking future earnings → switched to Shiller ie_data.xls quarter-end actual earnings with a 3-month lag. t +0.61, second half +0.12, still rejected (the S&P DJI EPS file returned 404 on both public and logged-in paths).
- **Return horizons of 1/3/6/9 months (s11, 56 tests, |t| ≥ 3.32):** 55 rejected, 1 on hold (KOSDAQ P/B 9 months −3.35, fragile: non-overlapping t −1.86). Valuation relationships weaken at shorter horizons; no short-horizon positive t was significant.
- **3- and 5-year z windows (s12, 38 tests, |t| ≥ 3.21):** 37 rejected, 1 reference indicator (KOSDAQ P/B 3-year −3.33, falls to −2.53 without the 2008-06 to 2009-03 stretch). Shorter windows were not better overall.
- **Decomposing the full-sample-band (broadcast chart) effect (exploratory):** 2 of 14 verdicts change (KOSPI P/B → signal, KOSDAQ gap → reference). Three causes: look-ahead (NDX forward P/E, same period −0.18 → −2.69), baseline length (KOSPI P/B expanding mean −2.82), and a longer test span (most of KOSPI gap −0.11 → −2.24).

## Verdict and reasons
- Zero signals or reference indicators; on a real-time (rolling) basis almost every combination failed J1.
- Drawing bands with full-sample mean/σ (as the charts do) makes indicators look better through hindsight (KOSPI disparity t −0.11 → −2.24; NDX forward PE placebo 27% → 93%).
- KOSDAQ PBR was first reported as a Reference indicator, then downgraded to On Hold after red-team review 2 showed an unresolved episode had been counted.

## Caveats and limitations
- Price indices (no dividends), cash at 0%. Korean indices used US VIX and Fed funds only (VKOSPI and BOK rate untested).
- NASDAQ 100/SOX trailing valuation and long forward PE histories unavailable for free; forward PE is 10 years read from photos, with ~6 years usable for verdicts.
- TTM PER flips direction when earnings swing (2009, 2020, 2026 KOSPI); a shrinking 10-year σ inflates z (KOSPI PBR 2025).
- Corrections: unresolved months in up-probability denominators (fixed); unresolved months in half-sample split (fixed, verdicts unchanged); KOSDAQ PBR downgrade.

## What happened next
Per-combination chart/verdict report published as an Artifact (_refs/report_link.txt). Korean post published on gangnamfather.com on 2026-11-18; English post saved as a draft. No trading changes.

## File guide
src/PREREG.md (sections 1–8) · src/RESULTS.md · src/RUNLOG.md · src/src/ (core.py, overlay.py, disparity.py, fwdpe.py, fwdpe_test.py, report_data.py) · src/out/ · src/calc, calc2, calc3 (Antigravity recomputations) · src/review, review2, review3 · src/digitize · src/data · REVIEW.md (three red-team reviews combined).
