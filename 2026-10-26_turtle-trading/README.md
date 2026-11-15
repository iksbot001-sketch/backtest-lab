# 2026-10-26 Turtle Trading (KOSPI & KOSDAQ 36 Years, S&P 500 & Nasdaq 100 36 Years)

## Summary
Tested Turtle Trading rules (buy on a 55-day high; sell on a 20-day low or 2N stop-loss) on 36 years of daily bars for two Korean index ETFs (KODEX 200, KODEX KOSDAQ150) and two U.S. indices (S&P 500, Nasdaq 100).
The verdict is REJECT: the strategy avoided large drawdowns, but gave up too much bull-market return and failed to beat Buy & Hold or a 50/200-day golden cross (holding when the 50-day moving average is above the 200-day moving average) (private note (not published), `adhoc_20261026_1235_cro/risk_review.md`, `adhoc_20261026_1341_quant_us_turtle/backtest/quant_report.md`).

## Why (purpose and context)
The owner ordered the backtest by asking, "Would Turtle Trading work if applied to the KOSDAQ and KOSPI indices?" (private note (not published), `turtle_review_20261026/BRIEF.md`).
Earlier the same day, the team had re-examined a KOSDAQ 150 volatility-harvesting strategy (ladder buying in tranches whenever price drops by a fixed step) (`kq150_review_20261026/BRIEF.md`), and the brief included a side-by-side comparison of Turtle Trading and volatility harvesting on the same daily data (`turtle_review_20261026/BRIEF.md`).
After the Korea study finished, a follow-up brief checked "Does it work on U.S. indices too?" using the same engine and rules (`adhoc_20261026_1341_quant_us_turtle/BRIEF.md`).
Because the owner actually trades VOO and QQQ in the U.S. using the 50/200-day golden cross, the 50/200-day golden cross became the primary benchmark in the U.S. study (`adhoc_20261026_1341_quant_us_turtle/BRIEF.md`).
Gemini (Antigravity) handled execution while Claude wrote the briefs and independently recalculated numbers; this division of labor became the standard workflow for subsequent backtests (private note (not published)).

## What was tested
- Question / hypothesis: Tested whether applying the original Turtle Trading System 2 rules directly to a single index beats Buy & Hold, and whether results in Korea carry over to the U.S. (`turtle_review_20261026/BRIEF.md`, `adhoc_20261026_1341_quant_us_turtle/BRIEF.md`).
- Markets / assets: Korea used KODEX 200 (069500) and KODEX KOSDAQ150 (229200); the U.S. used S&P 500 (`^GSPC`) and Nasdaq 100 (`^NDX`), with Nasdaq Composite (`^IXIC`) included for reference (`turtle_review_20261026/BRIEF.md`, `adhoc_20261026_1341_quant_us_turtle/BRIEF.md`).
  All tests were long-only, 1 position at a time (no pyramiding), and held cash (0% interest) when out of the market (`turtle_review_20261026/BRIEF.md`, `adhoc_20261026_1341_quant_us_turtle/BRIEF.md`).
- Period: Korea covered 1990-01-04 to 2026-10-23 (about 36.8 years), while KOSDAQ was capped at 1997-01-03 to 2026-10-23 (about 29.8 years) due to high/low data defects in early 1996 data (`adhoc_20261026_1224_quant/backtest/quant_report.md`).
  The U.S. covered 1990-01-02 to 2026-10-20 (about 36.8 years) (`adhoc_20261026_1341_quant_us_turtle/BRIEF.md`, `adhoc_20261026_1341_quant_us_turtle/backtest/quant_report.md`).
- Data sources: Korea used Naver `siseJson` daily bars, except KODEX KOSDAQ150 (229200) used a Daishin Securities daily file due to close/high mismatches in Naver data (155 days) (`adhoc_20261026_1224_quant/backtest/quant_report.md`).
  Pre-ETF periods were proxied by indices (KOSPI before 2002-10-14 for KODEX 200; KOSDAQ Composite before 2015-10-01 for KODEX KOSDAQ150) (`adhoc_20261026_1224_quant/backtest/quant_report.md`).
  The U.S. used Yahoo v8 daily JSON (`^GSPC`, `^NDX`, `^IXIC`), with the U.S. 3-month Treasury bill (`^IRX`) as the risk-free rate (`adhoc_20261026_1341_quant_us_turtle/BRIEF.md`).
  Raw data (`data/`) was not copied into this archive folder (private source list).
- Rules (entry, exit, sizing, costs): Buy when price exceeds the prior 55-trading-day high (`shift(1)` applied); sell 100% when price breaks below the prior 20-trading-day low or below entry price − 2N (where N = 20-day ATR, fixed at entry) (`turtle_review_20261026/BRIEF.md`, `adhoc_20261026_1224_quant/backtest/quant_report.md`).
  Parameters (55/20/2N) were fixed from the brief without optimization (`turtle_review_20261026/BRIEF.md`).
  Two execution modes were tested: (a) next-day open after signal, and (b) intraday breakout price (accounting for gaps) (`turtle_review_20261026/BRIEF.md`).
  Costs were 0.015% + 1 tick (5 KRW) one-way for Korean ETFs, 0.05% one-way for Korean index-proxy periods, and 0.05% one-way for the U.S.; 2x costs were also checked (`adhoc_20261026_1224_quant/backtest/quant_report.md`, `adhoc_20261026_1341_quant_us_turtle/backtest/quant_report.md`).
- Pre-specified pass criteria (if any): Validation Protocol v1.1 (`docs/VALIDATION_SPEC.md`) was applied (`adhoc_20261026_1235_cro/risk_review.md`).
  No pre-registration (PREREG) file is present in this folder, so detailed pre-set conditions cannot be verified.
  The validation table criteria include Probabilistic Sharpe Ratio (PSR ≥ 0.95), Deflated Sharpe Ratio (DSR ≥ 0.90), and Walk-Forward Efficiency (WFE 50–150%) (`adhoc_20261026_1235_cro/risk_review.md`).

## Results
Korea — KODEX 200 Turtle (a) next-day open vs. benchmarks (`adhoc_20261026_1224_quant/backtest/quant_report.md`, `adhoc_20261026_1235_cro/risk_review.md`):
- Full 36 years (1990-01 to 2026-10): Turtle (a) posted CAGR 5.9%, MDD -34.3%, Sharpe 0.28 (`adhoc_20261026_1224_quant/backtest/quant_report.md`).
  Over the same period, Buy & Hold posted CAGR 6.5%, MDD -76.0%, Sharpe 0.27 (`adhoc_20261026_1224_quant/backtest/quant_report.md`).
- Since ETF listing (2002-10 to 2026-10): Turtle (a) posted CAGR 6.0%, MDD -27.4%, Sharpe 0.37 (38.3% exposure), while Buy & Hold posted CAGR 12.8%, MDD -52.7%, Sharpe 0.55 (`adhoc_20261026_1224_quant/backtest/quant_report.md`).
- Equal-exposure comparison (2002-10 onward): Holding KODEX 200 constantly at the same 38.3% weight with 61.7% in zero-interest cash yielded CAGR 5.53%, MDD -23.90%, Sharpe 0.448—beating Turtle on both drawdown and Sharpe (`adhoc_20261026_1235_cro/risk_review.md`).

Korea — KODEX KOSDAQ150 Turtle (a) next-day open vs. benchmarks (`adhoc_20261026_1224_quant/backtest/quant_report.md`):
- Full 30 years (1997-01 to 2026-10): Turtle (a) posted CAGR 3.9%, MDD -49.9%, Sharpe 0.18, while Buy & Hold posted CAGR -1.0%, MDD -90.5%, Sharpe 0.05 (`adhoc_20261026_1224_quant/backtest/quant_report.md`).
- Since ETF listing (2015-10 to 2026-10): Turtle (a) posted CAGR 1.7%, MDD -24.7%, Sharpe 0.04; over the same period, volatility harvesting (current) posted CAGR 6.4%, MDD -38.4%, Sharpe 0.34, and Buy & Hold posted CAGR 1.8%, MDD -56.8%, Sharpe 0.14 (`adhoc_20261026_1224_quant/backtest/quant_report.md`).

U.S. — Full 36.8 years (1990-01 to 2026-10) comparison (`adhoc_20261026_1341_quant_us_turtle/backtest/quant_report.md`):
- S&P 500 (`^GSPC`): Turtle (a) posted CAGR 1.4%, MDD -33.8%, Sharpe -0.11 (44.1% exposure) (`adhoc_20261026_1341_quant_us_turtle/backtest/quant_report.md`).
  Over the same period, the 50/200-day golden cross posted CAGR 7.6%, MDD -33.9%, Sharpe 0.42, and Buy & Hold posted CAGR 8.6%, MDD -57.2%, Sharpe 0.40 (`adhoc_20261026_1341_quant_us_turtle/backtest/quant_report.md`).
- Nasdaq 100 (`^NDX`): Turtle (a) posted CAGR 6.1%, MDD -42.7%, Sharpe 0.31 (46.7% exposure) (`adhoc_20261026_1341_quant_us_turtle/backtest/quant_report.md`).
  Over the same period, the 50/200-day golden cross posted CAGR 13.8%, MDD -35.7%, Sharpe 0.62, and Buy & Hold posted CAGR 14.2%, MDD -82.8%, Sharpe 0.53 (`adhoc_20261026_1341_quant_us_turtle/backtest/quant_report.md`).
- In sensitivity analysis (entry 40/55/70 days × exit 10/20/30 days × stop-loss 1.5/2/3N = 27 combinations), no combination beat Buy & Hold or the golden cross on either S&P 500 or Nasdaq 100 (`adhoc_20261026_1341_quant_us_turtle/backtest/quant_report.md`).

## Verdict and reasons
The final verdict is REJECT (private note (not published), `adhoc_20261026_1235_cro/risk_review.md`, `adhoc_20261026_1341_quant_us_turtle/backtest/quant_report.md`).
- All 4 Korean combinations (KODEX 200 and KOSDAQ150 × execution (a) and (b)) had DSRs of 0.337–0.668, failing the 0.90 threshold, and the Risk Reviewer (CRO) recommended 0% allocation for both assets (`adhoc_20261026_1235_cro/risk_review.md`).
- All 4 U.S. combinations (`GSPC` and `NDX` × (a) and (b)) also received automatic REJECT verdicts under the validation protocol (`adhoc_20261026_1341_quant_us_turtle/backtest/quant_report.md`).
  Nasdaq 100 passed PSR (0.970, 0.988) and WFE (117.3%, 93.2%), but failed DSR (0.654, 0.762) below the 0.90 threshold (`adhoc_20261026_1341_quant_us_turtle/backtest/quant_report.md`).
- Turtle's smaller drawdowns compared to Buy & Hold came not from timing alpha, but from sitting in cash 53–75% of the time; passive constant-weight index exposure at the same average exposure beat Turtle on Sharpe in both Korea and the U.S. (`adhoc_20261026_1235_cro/risk_review.md`, `adhoc_20261026_1341_quant_us_turtle/backtest/quant_report.md`).
- In the U.S. market, daily return autocorrelation is negative (`GSPC` -0.080, `NDX` -0.057) and 20-day and 60-day returns after 55-day breakouts are lower than average, causing tight exit rules like the 20-day low and 2N stop to get stopped out on pullbacks (`adhoc_20261026_1341_quant_us_turtle/backtest/quant_report.md`).
- Since mixing KOSDAQ 150 post-listing volatility harvesting (Sharpe 0.34) with Turtle (Sharpe 0.04) at 50:50 drops the combined Sharpe to 0.25, the CRO also advised against combining them (`adhoc_20261026_1235_cro/risk_review.md`).

## Caveats and limitations
- Dependence on a few events: 78.9% of KOSDAQ 150 Turtle (a)'s 30-year outperformance came from a single year, 1999 (+142.2%), while cumulative return from 2000 to 2026 was +7.2% (0.26% annualized) (`adhoc_20261026_1235_cro/risk_review.md`).
  For KODEX 200 Turtle (a), excluding the 2025–2026 surge drops 1990–2024 CAGR to 3.65% (Sharpe 0.133, PSR 0.787 FAIL), with 11 of the 14 years from 2011 to 2024 flat or negative for a cumulative +8.8% (`adhoc_20261026_1235_cro/risk_review.md`).
  For S&P 500 Turtle (a), excluding 1995 (+30.2%) and 1998 leaves a 35-year cumulative return of +10.0% (0.26% annualized) (`adhoc_20261026_1341_quant_us_turtle/backtest/quant_report.md`).
- Index proxies and missing dividends: Pre-ETF periods and U.S. indices (`^GSPC`, `^NDX`) are price indices without dividends (distributions), and KOSDAQ Composite behaved differently from KOSDAQ 150 (`adhoc_20261026_1224_quant/backtest/quant_report.md`, `adhoc_20261026_1341_quant_us_turtle/backtest/quant_report.md`).
  Raising friction costs in the Korean index-proxy period to 0.25% + 3 ticks lowers KODEX 200 (b) Sharpe from 0.287 to 0.245 (`adhoc_20261026_1235_cro/risk_review.md`).
- Optimistic execution assumptions: KOSDAQ 150 intraday breakout (b)'s 6.0% CAGR versus 3.9% for open execution (a) assumes exact fills at the breakout level; in live stop orders, gaps and order-book air pockets narrow this gap (`adhoc_20261026_1235_cro/risk_review.md`).
  Even with a 2N stop-loss in place, gap-down opens caused large single-day losses in KOSDAQ 150 (a), such as -21.55% (2000-03-21) and -13.10% (2026-10-15) (`adhoc_20261026_1235_cro/risk_review.md`).
- Validation code bugs (flagged by Korea CRO): In intraday breakout mode (b), passing prior-day holdings (`pos = held.shift(1)`) to `validate` shifted trade boundaries by 1 day and missed 1 same-day stop-loss (`adhoc_20261026_1235_cro/risk_review.md`).
  In Korea's `trial_registry.jsonl`, 540 trials were logged but only 201 were reported; reflecting all 540 trials drops KODEX 200 (a) DSR from 0.636 to 0.460 (`adhoc_20261026_1235_cro/risk_review.md`).
  At 100% capital allocation, 4 neighboring ATR periods (`atr_n`) became identical clones, inflating neighbor stability (`adhoc_20261026_1235_cro/risk_review.md`).
- Differences from original Turtle Trading: Original Turtle Trading included diversification across multiple futures markets, 1% account risk sizing, pyramiding during trends, and short selling, whereas this test was a simplified single-index, long-only version (private note (not published)).
- Missing documents: `PREREG`, `PLAN`, `TASK`, and `RUNLOG.md` are not in this archive folder (cannot be verified).

## What happened next
- A blog post draft titled "터틀트레이딩, 코스닥 코스피 지수에 적용하면 먹힐까?" ("Would Turtle Trading work on KOSDAQ and KOSPI indices?") was written in private note (not published) (whether it was published to the blog cannot be verified).
- The draft concluded that the rules would be used not as a replacement for index investing, but as an "auxiliary signal indicating when to reduce index exposure" (private note (not published)).
- Among the follow-up items mentioned in the draft (U.S. indices, bonds, and gold diversification), the U.S. index test (S&P 500, Nasdaq 100) was executed in `adhoc_20261026_1341_quant_us_turtle/` (`adhoc_20261026_1341_quant_us_turtle/BRIEF.md`).
  Results for bond and gold diversification are not in this folder and cannot be verified.
- The workflow where Gemini executes first and Claude writes the brief and reconciles numbers by recalculating became the standard practice for subsequent backtests (private note (not published)).
- Whether anything was reflected in live capital management cannot be verified (the CRO recommended 0% allocation) (`adhoc_20261026_1235_cro/risk_review.md`).

## File guide
- private note (not published): Obsidian strategy-log note briefly summarizing the verdict and lessons learned.
- private note (not published): Blog post draft with the clearest explanation of the rules and interpretation of the Korea study.
- `turtle_review_20261026/BRIEF.md`: The owner's brief for the Korean Turtle Trading backtest.
- `adhoc_20261026_1224_quant/`: Korea quant run folder containing `backtest/quant_report.md` (report), `backtest/backtest.py` (code), `backtest/results.json`, and `backtest/validation*.md`.
- `adhoc_20261026_1235_cro/`: Korea CRO audit folder; `risk_review.md` contains the final REJECT verdict and code audit findings.
- `adhoc_20261026_1341_quant_us_turtle/`: U.S. quant run folder containing `BRIEF.md` (brief), `backtest/quant_report.md` (report), `backtest/backtest.py` (code), `results.json`, and chart PNGs.
- `kq150_review_20261026/BRIEF.md`, `adhoc_20261026_0915_quant/`, `adhoc_20261026_0940_cro/`: Same-day KOSDAQ 150 volatility-harvesting review folders, serving as the source for comparison figures against Turtle.
- `trial_registry.jsonl`: Ledger of combinations tried in each run folder (used for DSR calculation).
- private source list: List of original source paths from which this folder was copied.

