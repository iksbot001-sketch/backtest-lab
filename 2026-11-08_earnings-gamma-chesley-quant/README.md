# 2026-11-08 Earnings Gamma & Chesley Quant

## Summary
We backtested earnings acceleration (earnings gamma)—the second derivative of earnings growth—along with its derived strategies (forecasting models, refinements, and CAN SLIM), and Chesley Investment Advisory's Korean quant strategy in the U.S. and Korean stock markets.
The core earnings gamma strategy found no basis for live deployment in either Korea or the U.S. and was placed on hold for paper-trading observation, while the Chesley quant strategy was rejected due to severe underperformance against the index.

## Why (purpose and context)
The owner proposed an idea (Strategy G): buying stocks where the second derivative of the earnings path (change in growth rate) is positive, rising, and continuing, and holding them until the acceleration breaks (`gamma_backtest/PLAN.md`).
First applied to reading the current state of Microsoft and Google in the AI War Deck (Slide 36 appendix 'Gamma ⑥'), it was expanded from 2026-11-08 into a long-term U.S. and Korean backtest (private note (not published), `gamma_backtest/PLAN.md`).
Then on 2026-11-09, after securing consensus estimates (paid EODHD subscription), we sequentially tested an acceleration forecasting model, condition refinements, common traits of big winners (+50%, +30%), and a mechanized test of William O'Neil's CAN SLIM (`gamma_backtest/PLAN.md`).
On the same day, we also backtested the Korean 52-week high and share-buyback quant rules from two Chesley Investment Advisory lecture slides provided by the owner, using the same validation framework (private note (not published), `gamma_backtest/CHESLEY_PREREG.md`).

## What was tested
- Questions / hypotheses:
  Does holding top-ranked stocks by realized or forward earnings acceleration (gamma) until acceleration breaks beat fixed holding periods or the index (`gamma_backtest/PLAN.md`, `gamma_backtest/spec.json`)?
  Does combining earnings surprise forecasting, technical/fundamental refinements, and CAN SLIM conditions generate significant excess returns in U.S. small- and mid-cap stocks (`gamma_backtest/ML_PREREG.md`, `gamma_backtest/REFINE_PREREG.md`, `gamma_backtest/CANSLIM_PREREG.md`)?
  Do Korean KOSPI/KOSDAQ 52-week high + strong-earnings quant (Q1) and the ≥3 share-buyback variant (Q2) beat KODEX 200 (`gamma_backtest/CHESLEY_PREREG.md`)?
- Markets / assets:
  U.S. S&P 500 non-financial, non-real-estate common stocks, and non-S&P 500 U.S. small/mid-cap common stocks (price ≥ $5, 20-day average dollar volume ≥ $1M) (`gamma_backtest/PLAN.md`, `gamma_backtest/ML_PREREG.md`).
  Korean KOSPI non-financials (earnings gamma Stage 1) and all KOSPI/KOSDAQ common stocks (Chesley quant; excluding preferred shares, SPACs, ETFs, and REITs) (`gamma_backtest/spec.json`, `gamma_backtest/CHESLEY_PREREG.md`).
- Periods:
  Earnings gamma U.S. S1: 2009-07 to 2026-10 (in-sample through 2017, out-of-sample 2018+); U.S. S2/S3 forward-estimate-based: 2017Q2 to 2026Q3 (in-sample through 2021, out-of-sample 2022+) (`gamma_backtest/spec.json`).
  U.S. ML, refinement, winner commonalities, and CAN SLIM: 2008-07 to 2026-11 (split 2010–2018 / 2019+) (`gamma_backtest/ML_PREREG.md`, `gamma_backtest/REFINE_PREREG.md`, `gamma_backtest/WINNERS_PREREG.md`, `gamma_backtest/CANSLIM_PREREG.md`).
  Korea S1: 2016-01 to 2026; Chesley quant: 2017-01 to 2026-10 (subperiods 2017–2021 / 2022+) (`gamma_backtest/spec.json`, `gamma_backtest/CHESLEY_PREREG.md`).
- Data sources:
  U.S. realized financials from SEC EDGAR (`companyfacts`), estimate trends and small/mid-cap adjusted prices & share counts from EODHD, large-cap prices from yfinance, and market benchmarks SPY and IWM (`gamma_backtest/PLAN.md`, `gamma_backtest/ML_PREREG.md`).
  Korean financials and disclosures from OpenDART, daily bars from the existing DB (`prices/kr`) plus 796 delisted stocks backfilled from Naver Finance (`prices/kr_delisted`), share counts from EODHD and DART total shares, and market benchmark KODEX 200 (`gamma_backtest/CHESLEY_PREREG.md`, `gamma_backtest/FORECAST_SOURCES.md`).
- Rules (key entry, exit, sizing, and cost rules):
  Earnings gamma: buy the top decile of quarter-over-quarter change in quarterly EPS growth rate (acceleration) equal-weighted at the close 2 trading days after filing (15 days after release for EODHD estimates), and exit on acceleration ≤ 0, two consecutive declines, or fixed holding periods (1, 3, 6, 12 months) (`gamma_backtest/PLAN.md`, `gamma_backtest/spec.json`).
  U.S. transaction costs: 0.015% + $0.01 one-way for large-caps; 0.10% for upper-liquidity and 0.30% for lower-liquidity small/mid-caps (including 2× cost sensitivity) (`gamma_backtest/ML_PREREG.md`, `gamma_backtest/REFINE_PREREG.md`).
  Chesley Q1: from 52-week high stocks, select up to 13 stocks meeting YoY & QoQ revenue and operating-income growth, profitable in the last 5 quarters, market cap ≥ KRW 500B, and no CB/BW/largest-shareholder change in the past 1 year; buy at the next month-end close and hold for 1 month (auxiliary B buys at the current month-end). Q2 holds stocks with ≥ 3 share buybacks/cancellations in 5 years for 7 months. Both use equal weighting and 0.25% one-way cost (including 2× sensitivity) (`gamma_backtest/CHESLEY_PREREG.md`).
- Pre-registered criteria (if any):
  Earnings gamma falsification criteria: fixed 1-month D10–D1 monthly return ≥ 0.5% and t ≥ 2 (F0); reversal-exit Sharpe or MDD improvement (F1); out-of-sample excess return > 0 at 2× cost (F2); out-of-sample alpha ≥ half of in-sample (F3); top 10 stocks' contribution ≤ 50% (F4) (`gamma_backtest/spec.json`).
  Live-candidate criteria for refinement, ML, and CAN SLIM: calendar-time t ≥ 3 (multiple-testing adjusted), excess return > 0 in both subperiods, > 0 at 2× cost, and mean > 0 after excluding top 10 trades or top 1% (`gamma_backtest/ML_PREREG.md`, `gamma_backtest/REFINE_PREREG.md`, `gamma_backtest/CANSLIM_PREREG.md`).
  Chesley quant criteria: monthly excess return vs. KODEX 200 with t ≥ 2 and > 0 in both subperiods for Q1-A and Q2 to be deemed "effective"; and beating all 52-week highs, > 0 at 2× cost, and > 0 excluding top 1% to be deemed a "live candidate" (`gamma_backtest/CHESLEY_PREREG.md`).

## Results
- U.S. realized gamma (S1, 2009-07 to 2026-10) 1-month D10–D1 was -0.08% (t=-0.26) on EAP and +0.59% (t=1.37) by announcement date, failing F0 (t ≥ 2) (`gamma_backtest/PLAN.md`, `gamma_backtest/spec.json`).
- Korean realized gamma (S1, 2016 to 2026) 1-month long-short returned +1.42% (t=3.05), mostly driven by D1 declines; long-only D10 had no significant excess return over the market under any holding rule after costs (~0.5% round-trip) (`gamma_backtest/PLAN.md`).
- U.S. forward gamma (S2/S3, 2017Q2 to 2026Q3) 1-quarter D10–D1 was insignificant at +0.28% (t=0.27) for EA and +0.50% (t=0.30) for REV, whereas the look-ahead oracle recorded +6.26% (t=5.29) (`gamma_backtest/PLAN.md`).
- U.S. forward gamma long-only Rule A (hold until acceleration breaks, net of per-trade cost vs. SPY) was -2.00% (t=-1.24) for EA and +3.37% (t=2.58, average hold 104 days) for the oracle (`gamma_backtest/PLAN.md`).
- S&P 500 acceleration forecasting models (2008-07 to 2026-11) achieved next-quarter actual acceleration IC of 0.696 for M2 vs. 0.677 for consensus EA, yet all long-only D10 trading returns were negative to zero (`gamma_backtest/ML_PREREG.md`, `gamma_backtest/out/ml_results_sp.md`).
- U.S. small/mid-cap surprise forecasting (SURP Ridge Rule A) dropped from +4.55%/trade (t=2.18) before price-error cleaning (`pxclean.py`) to +2.77%/trade (6,142 trades) and +2.3%/yr in calendar time (t=1.52) after cleaning (`gamma_backtest/PLAN.md`, `gamma_backtest/ML_PREREG.md`).
- Refinements (Q, C, P conditions) were all negative in the S&P 500; small/mid-cap realized gamma logged +7.7%/yr (t=2.98, 1,404 trades, median -0.1%) when buying the top 10% within the Q/C/P-passing universe, which was an ex-post exploratory finding (`gamma_backtest/PLAN.md`, `gamma_backtest/REFINE_PREREG.md`).
- CAN SLIM (excluding I, U.S. small/mid-caps 2010 to 2026) S1-E1 (498 trades) returned +11.2%/yr in calendar time (IR 0.35, t=1.39, MDD -46.5%) and +10.0% at 2× cost, while O'Neil's -8% stop-loss (E2) degraded performance to +4.0%/yr (`gamma_backtest/PLAN.md`, `gamma_backtest/CANSLIM_PREREG.md`).
- Chesley quant Q1-A (2017-01 to 2026-10, 1,051 trades) had CAGR -9.52%, MDD -77.48%, Sharpe -0.13, underperforming KODEX 200 (CAGR +15.30%, MDD -35.72%, Sharpe 0.63) by -22.85%p/yr (t=-2.50), and CAGR -14.60% at 2× cost (`gamma_backtest/out/chesley_run.log`).
- Chesley Q1-B (1,060 trades) had CAGR -7.02%, MDD -71.90% (-20.82%p); Q2 buyback variant (74 trades) had CAGR +1.41%, MDD -45.74% (-14.07%p, t=-1.85); all 52-week highs equal-weighted (29,836 trades) had CAGR -1.17%, MDD -43.07% (-16.86%p); and random selection (1,050 trades) had CAGR -6.80%, MDD -70.80% (-20.54%p) (`gamma_backtest/out/chesley_run.log`).

## Verdict and reasons
Earnings gamma (realized S1, forward S2/S3, ML forecasting, CAN SLIM) is **on hold (plan / observe)** (private note (not published), `gamma_backtest/PLAN.md`).
Realized acceleration and consensus-based gamma are either already priced in (failing F0 and S2 criteria) or failed the out-of-sample and multiple-testing threshold (t ≥ 3), leaving only the Q/C/P refinement and multivariate winner filter (gamma sample out-of-sample AUC 0.563, top/bottom tercile spread +6.1%p, t=3.15) for 1+ year of paper-trading observation (`gamma_backtest/PLAN.md`).
Chesley Investment Advisory quant is **rejected** (private note (not published), `gamma_backtest/CHESLEY_PREREG.md`).
Q1-A, Q1-B, and Q2 all failed the pre-registered criteria (t ≥ 2 vs. KODEX 200 and positive in both subperiods), and performed even worse than all 52-week highs without financial filters (-1.17%) or random selection (-6.80%) (`gamma_backtest/out/chesley_run.log`, private note (not published)).

## Caveats and limitations
The initial U.S. S&P 500 run and EODHD estimate data omit delisted/bankrupt stocks (e.g., SIVB, FRC) and unlinked-price stocks, leaving survivorship bias (`gamma_backtest/PLAN.md`, `gamma_backtest/FORECAST_SOURCES.md`).
EODHD adjusted prices contained data errors such as 99× (SCU, OSB) or 4× (LCI) single-day jumps, causing results to shift significantly before vs. after cleaning (`pxclean.py`), and 282 jumps in the 3×–5× range remain unclassified (`gamma_backtest/PLAN.md`, `gamma_backtest/CANSLIM_PREREG.md`).
EODHD estimate snapshots lack exact observation dates and were approximated using ±20 days around prior earnings releases, delaying entry to T+15 days (`gamma_backtest/PLAN.md`).
In the Chesley quant test, the "6-month net foreign buying" filter was omitted due to missing data, major-shareholder stake reduction was approximated by "largest-shareholder change" disclosures, delisted stocks were liquidated at the last pre-halt price (creating an upward bias), and some spin-off price gaps were counted as losses (private note (not published), `gamma_backtest/CHESLEY_PREREG.md`).
There is also a regime effect in the Korean market over the sample period (2017–2026), where large-caps (KODEX 200 +15.30%/yr) dominated small/mid-caps (KOSDAQ 150 +3.8%) (private note (not published)).
During agent delegation, Antigravity Claude hit its usage limit, so Gemini Argon took over the P1 literature review and part of the code/audits (A1, CAN SLIM, Chesley), and those outputs are marked "provisional" (`gamma_backtest/PLAN.md`, `gamma_backtest/CHESLEY_PREREG.md`, `gamma_backtest/CANSLIM_PREREG.md`).

## What happened next
Chesley quant was confirmed not to be operated, with a note that it could be re-tested with the foreign-flow condition once a KRX Open API key is obtained (private note (not published), `gamma_backtest/CHESLEY_PREREG.md`).
Earnings gamma was not added as a trading rule; instead, Q/C/P conditions were frozen for 1+ year of forward paper trading (≥ 30 stocks, equal-weighted, no stop-loss) (`gamma_backtest/PLAN.md`).
`snapshot_trends.py` and `com.example.gamma-snapshot.plist` were created to accumulate daily EODHD estimate snapshots; launchd registration hit permission denied and was left for the owner to register directly (`gamma_backtest/PLAN.md`).
The standard distribution-reporting bundle was organized in `~/agent-fund/lib/dist_report.py`, and the AI War Deck Slide 36 appendix 'Gamma ⑥' charts were generated in `gamma/` (private note (not published), `gamma_backtest/PLAN.md`).

## File guide
- [private note (not published)) (Korean): Obsidian note containing the earnings gamma definition and its first application in the AI War Deck.
- [private note (not published)) (Korean): Obsidian note containing Chesley Investment Advisory's quant rules, lecture example table, results, and rejection verdict.
- [gamma_backtest/PLAN.md](file://~/backtest-archive/2026-11-08_%EC%9D%B4%EC%9D%B5%EA%B0%90%EB%A7%88%C2%B7%EC%B2%B4%EC%8A%AC%EB%A6%AC_%ED%80%80%ED%8A%B8/gamma_backtest/PLAN.md): Master document summarizing the full research plan and stage-by-stage results from P0 through §15 Chesley quant.
- [gamma_backtest/spec.json](file://~/backtest-archive/2026-11-08_%EC%9D%B4%EC%9D%B5%EA%B0%90%EB%A7%88%C2%B7%EC%B2%B4%EC%8A%AC%EB%A6%AC_%ED%80%80%ED%8A%B8/gamma_backtest/spec.json): Pre-registration specification and revision history for the earnings gamma backtest.
- [gamma_backtest/CHESLEY_PREREG.md](file://~/backtest-archive/2026-11-08_%EC%9D%B4%EC%9D%B5%EA%B0%90%EB%A7%88%C2%B7%EC%B2%B4%EC%8A%AC%EB%A6%AC_%ED%80%80%ED%8A%B8/gamma_backtest/CHESLEY_PREREG.md): Chesley quant strategy pre-registration, mechanized definitions, verdict, and audit log.
- [gamma_backtest/ML_PREREG.md](file://~/backtest-archive/2026-11-08_%EC%9D%B4%EC%9D%B5%EA%B0%90%EB%A7%88%C2%B7%EC%B2%B4%EC%8A%AC%EB%A6%AC_%ED%80%80%ED%8A%B8/gamma_backtest/ML_PREREG.md): Pre-registration and amendment log for large-cap and small/mid-cap acceleration and surprise forecasting models.
- [gamma_backtest/REFINE_PREREG.md](file://~/backtest-archive/2026-11-08_%EC%9D%B4%EC%9D%B5%EA%B0%90%EB%A7%88%C2%B7%EC%B2%B4%EC%8A%AC%EB%A6%AC_%ED%80%80%ED%8A%B8/gamma_backtest/REFINE_PREREG.md): Pre-registration for gamma strategy refinement factors (Q, C, P, S, L, W, R, E).
- [gamma_backtest/WINNERS_PREREG.md](file://~/backtest-archive/2026-11-08_%EC%9D%B4%EC%9D%B5%EA%B0%90%EB%A7%88%C2%B7%EC%B2%B4%EC%8A%AC%EB%A6%AC_%ED%80%80%ED%8A%B8/gamma_backtest/WINNERS_PREREG.md): Pre-registration for the common-traits analysis of big winners (+50%, +30%).
- [gamma_backtest/CANSLIM_PREREG.md](file://~/backtest-archive/2026-11-08_%EC%9D%B4%EC%9D%B5%EA%B0%90%EB%A7%88%C2%B7%EC%B2%B4%EC%8A%AC%EB%A6%AC_%ED%80%80%ED%8A%B8/gamma_backtest/CANSLIM_PREREG.md): Pre-registration and summary of results for the mechanized CAN SLIM test.
- [gamma_backtest/FORECAST_SOURCES.md](file://~/backtest-archive/2026-11-08_%EC%9D%B4%EC%9D%B5%EA%B0%90%EB%A7%88%C2%B7%EC%B2%B4%EC%8A%AC%EB%A6%AC_%ED%80%80%ED%8A%B8/gamma_backtest/FORECAST_SOURCES.md): Survey of U.S. and Korean historical consensus data sources and EODHD empirical test notes.
- [gamma_backtest/out/](file://~/backtest-archive/2026-11-08_%EC%9D%B4%EC%9D%B5%EA%B0%90%EB%A7%88%C2%B7%EC%B2%B4%EC%8A%AC%EB%A6%AC_%ED%80%80%ED%8A%B8/gamma_backtest/out/): Output folder containing Chesley (`chesley_run.log`, `CH_DIGEST.md`), CAN SLIM (`CS_DIGEST.md`), ML (`ml_results_sp.md`, `ml_results_sm.md`), literature, and audit logs.
- [gamma_backtest/](file://~/backtest-archive/2026-11-08_%EC%9D%B4%EC%9D%B5%EA%B0%90%EB%A7%88%C2%B7%EC%B2%B4%EC%8A%AC%EB%A6%AC_%ED%80%80%ED%8A%B8/gamma_backtest/): Contains data collection (`collect_*.py`), price cleaning (`pxclean.py`), and backtest (`s1_*.py`, `s2_*.py`, `ml_model.py`, `refine.py`, `winners.py`, `canslim.py`, `chesley.py`) scripts.
- [gamma/](file://~/backtest-archive/2026-11-08_%EC%9D%B4%EC%9D%B5%EA%B0%90%EB%A7%88%C2%B7%EC%B2%B4%EC%8A%AC%EB%A6%AC_%ED%80%80%ED%8A%B8/gamma/): Microsoft and Google gamma calculation (`gamma.py`) and chart rendering files for the AI War Deck appendix 'Gamma ⑥'.

