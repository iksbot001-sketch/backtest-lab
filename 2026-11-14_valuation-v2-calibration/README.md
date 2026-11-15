# 2026-11-14 Valuation v2 Calibration Backtest

## Summary
Tested whether the valuation engine v2's default 4-year excess-return half-life assumption unduly penalizes growth and tech stocks, using 18 years of historical US stocks under a perfect-foresight condition with 3-year realized financials (TASK_A.md, 벨류에이션_v2_261114.md).
The 4-year half-life fair value priced even average stocks at half their market price after 2017 and could not be used as a buy criterion, but the fair-value-to-price ranking from the same engine moved in the same direction as subsequent 3-year and 5-year excess returns; therefore, absolute fair value was dropped and the v2.1 revision centered on ranking and implied half-life was finalized (벨류에이션_v2_261114.md, REPORT.md).

## Why (purpose and context)
The owner pointed out, "With a 4-year excess-return half-life, aren't there almost no investable candidates among growth and tech stocks?" (TASK_A.md, 벨류에이션_v2_261114.md).
Calculating the multiples assigned by the engine by company type showed that even a high-quality growth stock (12% growth rate, 30% return on capital) received only 19.5x under a 4-year half-life, failing to exceed 20x (벨류에이션_v2_261114.md).
This bias stemmed from applying the IT sector average (4-year CFROI [cash flow return on investment] correlation of 0.50) to individual companies, setting the mean-reversion target to the cost of capital (9%) rather than the sector average, and assuming a decay faster than the market-implied expected return of 9% (벨류에이션_v2_261114.md).
This was not a trading-strategy backtest, but a calibration study isolating the engine's fade assumptions against historical data, which later led to an ex-ante validation using consensus estimates (`adhoc_20261115_val2_exante`) (TASK_A.md, 벨류에이션_v2_261114.md).

## What was tested
- Question / hypothesis: Tested whether the 4-year half-life assumption passes historical quality stocks even with perfect 3-year earnings foresight, and whether implied half-life and fair-value-to-price ranking predict subsequent returns (벨류에이션_v2_261114.md, TASK_A.md).
- Market / assets: 6,792 observations across 528 US common stocks (excluding financials, real estate, and utilities; market cap >= $2B; t+1 to t+3 average operating margin > 3%), benchmarked against SPY (S&P 500 ETF) (TASK_A.md, 벨류에이션_v2_261114.md, _log.txt).
- Period: Fiscal years 2005–2022, with total-return tracking through 2026-11-06 (TASK_A.md).
- Data sources: EODHD (financials `eodhd/fund/*.US.json.gz`, daily prices `prices/eodhd/*.US.parquet`) and SPY price files (`prices/eodhd/SPY.US.parquet` or `prices/us/SPY.parquet`) (build_inputs.py).
- Rules (entry, exit, sizing, costs, etc.): A calibration calculation study with no trading, sizing, or cost rules (TASK_A.md). For each observation, as of the valuation date (first trading day after fiscal year-end + 90 days), 3-year realized revenue and operating margin were fed into the engine (`engine.py`) to compute equity value over a 40-year fade (growth half-life = half of profitability half-life, terminal growth 4%, tax rate 21%, cost of capital fixed at 9% plus an auxiliary annual series), yielding value-to-market-cap ratios (`VP4`, `VP8`, `VP12`, `VP20`) and implied half-life (`h_star`, searched over 0.5–100 years), which were compared against subsequent 3-year and 5-year excess returns over SPY (`ex3`, `ex5`) (TASK_A.md, calib.py, verify.py).
- Pre-specified verdict criteria (if any): Not found (no pre-specified pass/fail criteria are documented; `TASK_A.md` specified only the calculations, leaving interpretation to Claude).

## Results
The share of observations where the 4-year half-life fair value met or exceeded market cap (`VP4 >= 1.0`) was 28.9% overall (6,792 obs), 30.0% for tech (1,644 obs), 39.0% for high-ROIC (top tercile of return on invested capital, 2,243 obs), and 35.9% for the owner's 15 stocks (13 stocks excluding V and MA, 195 obs) (REPORT.md, _log.txt).
Annual overall pass rates declined over time: 45% in 2005–2011 (22.9%–71.6%), 21% in 2012–2017 (12.2%–34.5%), and 19% in 2018–2022 (12.4% in 2020, 10.6% in 2021) (벨류에이션_v2_261114.md, REPORT.md).
Implied half-life (`h_star`) failed to reach market cap even at the 100-year search cap in 54.5% of all observations (0.5446 of 6,792 obs), and the full-period median `h_star` was also 100 years (REPORT.md).
By revenue growth rate, pass rates were 17% for negative growth, 28% for 0–5%, 32% for 10–20%, and 37% for >20%—higher growth actually had higher pass rates (벨류에이션_v2_261114.md).
Extending the half-life to 8, 12, and 20 years raised the overall pass rate to 33.9%, 37.3%, and 40.6%, respectively, and applying the annual cost of capital (`VP4_rt`) yielded 39.2% (REPORT.md).
Among the top 10% of 5-year total return (`ret5`) observations (593 obs), 55.8% passed `VP4 >= 1.0` (vs. 30.9% across all 5,923 valid obs); median 5-year excess return over SPY (`ex5`) was +42.6%p for passing observations (1,830 obs) and -12.2%p for failing observations (4,093 obs) (REPORT.md).
Among the owner's 13 stocks, 76% of the 108 failing observations beat the market over the next 5 years with a median excess return of +77%p, and Amazon, Costco, and Salesforce never passed in any year (벨류에이션_v2_261114.md, REPORT.md).
Splitting `VP4` into annual terciles, the top-minus-bottom spread in mean subsequent excess return over SPY was +64.8%p for 3-year (`ex3`, positive in all 18 years) and +87.9%p for 5-year (`ex5`, positive in all 17 years) in the full universe, and +79.0%p (positive in all 18 years) and +96.1%p (positive in 94.1% of 17 years) in the tech group (REPORT.md).
Using relative valuation (`VP_mkt`) based on the median market-implied half-life (`h_mkt`), the top-minus-bottom tercile spread in the full universe was +67.0%p for `ex3` and +90.2%p for `ex5`, nearly identical to `VP4` (REPORT.md).

## Verdict and reasons
The documented verdict is **Adopted (v2.1 revision finalized; absolute fair-value buy threshold and market half-life benchmark rejected)** (벨류에이션_v2_261114.md).
Because the 4-year half-life absolute fair value priced even average stocks at half their market price after 2017 and 76% of failing observations among the owner's 13 stocks beat the market, it was concluded that it cannot be used as a buy/reject threshold (벨류에이션_v2_261114.md).
The approach proposed in Section 12—using the market-implied half-life as a benchmark—was also rejected because more than half of observations (54.5%) could not be matched even at 100 years (벨류에이션_v2_261114.md, REPORT.md).
By contrast, the fair-value-to-price ranking from the same engine aligned with subsequent excess returns in every year; thus, v2.1 finalized reporting (1) the 4-year half-life fair value (bottom-line reference), (2) the half-life implied by the stock price, and (3) the rank within the peer group, while restoring target operating margins (벨류에이션_v2_261114.md).

## Caveats and limitations
This is a perfect-foresight test feeding realized 3-year revenue and operating income into the explicit forecast window, not an ex-ante validation using information available at the time (TASK_A.md, 벨류에이션_v2_261114.md).
Fixing the tax rate at 21% across the entire 2005–2022 period overstated after-tax profits relative to the actual 35% statutory rate through 2017, inflating pass rates in earlier years (벨류에이션_v2_261114.md).
The main analysis fixed the cost of capital at 9%, and the auxiliary annual cost-of-capital series is an approximation written from memory (TASK_A.md, 벨류에이션_v2_261114.md).
Although 149 delisted stocks were included, only those with remaining financial files were captured, and Visa (V) and Mastercard (MA) were excluded because they are classified under Financials (벨류에이션_v2_261114.md, _log.txt).
Companies with low current margins due to expensing growth investments (Amazon, Salesforce, Netflix) and slow-growing but durable companies (Costco) are structurally missed (벨류에이션_v2_261114.md).
The first Antigravity run failed due to sandbox permission issues, and the rerun did not produce `RUNLOG.md`, so Claude recomputed 6 cases to confirm agreement (벨류에이션_v2_261114.md, dispatch.out).

## What happened next
On 2026-11-14, the v2.1 revisions (removing the absolute fair-value buy threshold; restoring peer ranking, implied half-life, and target margins) were incorporated into the methodology document (`벨류에이션_v2_261114.md`) (벨류에이션_v2_261114.md).
On 2026-11-15, a follow-up ex-ante validation using historical consensus estimates (`adhoc_20261115_val2_exante`, 462 stocks, FY 2017–2022) was run; unlike realized financials (Spearman rank IC = 0.43), consensus rank correlation was low at 0.058, leading v2.2 to restrict the engine to a translation tool only (벨류에이션_v2_261114.md).

## File guide
- private source list: Note recording the original run folder path and copy exclusion criteria.
- private note (not published): Document covering valuation v2 design, calibration backtest background and results (Sections 12–13), follow-up ex-ante validation (Section 14), and v2.1/v2.2 change history.
- `src/TASK_A.md`: Specification for the calibration backtest's questions, data definitions, engine inputs, and summary tables (T1–T6).
- `src/out/REPORT.md`: Final report tabulating the T1–T6 aggregation results.
- `src/out/_log.txt`: Execution log recording observation count (6,792 obs), counts by year and sector, and inclusion status of the owner's 15 stocks.
- `src/out/T1.csv` – `T6b.csv` and `T_VP4_*`, `T_h_star_*`, `T_VP_mkt_*`: Aggregated CSV files for pass rates, the owner's 15-stock matrix, implied half-life distributions, and tercile excess returns.
- `src/src/build_inputs.py`: Input-generation script building `data/inputs.csv` from raw EODHD financials and prices.
- `src/src/engine.py`: Three-stage valuation engine code.
- `src/src/calib.py`: Script running all observation calculations (`VP4`–`VP20`, `h_star`, `VP_mkt`) and T1–T6 aggregations.
- `src/src/verify.py`: Script independently re-implementing `V(h)` without the engine to cross-check 5 random rows from `panel.csv`.
- `src/dispatch.py`, `src/dispatch.out`, `src/agent_A_*.log.json`: Antigravity dispatch script and permission-denied failure logs.

