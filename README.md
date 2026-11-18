# Backtest Lab

An individual investor's quantitative research lab run with AI agents—built around **pre-registration**, **independent recomputation by a different model**, **red-team review**, and an **honest graveyard of rejected strategies**.

Author: Gangnam Father · Blog: [https://gangnamfather.com](https://gangnamfather.com)

> **Disclaimer:** This repository is for research and educational purposes only. **Nothing here is investment advice, and one adopted rule (a public-knowledge 50/200-day moving-average cross) is included; position sizing and account data are not.** All other strategies in this public companion repository are either rejected ideas or methodological/calibration studies.

---

## Why This Exists

Most published backtests suffer from silent look-ahead leaks, unmodeled transaction costs, survivorship bias, and selective reporting of winners. This lab applies an adversarial multi-agent workflow to test popular quant ideas, academic anomalies, and factor rules—and publishes the failures, bugs, and corrections openly.

- **Never silently change numbers:** Every bug, methodology drift, or post-hoc fix discovered during or after a run is appended to [`CORRECTIONS.md`](CORRECTIONS.md) with `Before → After` figures.
- **Standardized metrics & templates:** Reusable scripts live in [`tools/`](tools/) and study templates in [`templates/`](templates/).
- **Distilled rules:** Practical takeaways from failed tests and audits are collected in [`LESSONS.md`](LESSONS.md).

---

## Research Workflow

```text
+-----------------------------------------------------------------------------+
| 1. PRE-REGISTRATION (PREREG.md / SPEC.md)                                   |
|    - Lock hypotheses (H1-H3), IS/OOS windows, universe, cost model, gates   |
|    - Run turnover x cost sanity screen BEFORE coding                        |
+-----------------------------------------------------------------------------+
                                      |
                                      v
+-----------------------------------------------------------------------------+
| 2. SANDBOXED EXECUTION (Model A)                                            |
|    - Point-in-time inputs & market-cap anchor checks                        |
|    - Log all runs to trial_registry.jsonl + standardized daily returns      |
+-----------------------------------------------------------------------------+
                                      |
                                      v
+-----------------------------------------------------------------------------+
| 3. INDEPENDENT RECOMPUTATION (Model B)                                      |
|    - Re-implement signal & portfolio loop from scratch without shared state |
|    - Spot-check random dates/tickers by hand; log diffs in CORRECTIONS.md   |
+-----------------------------------------------------------------------------+
                                      |
                                      v
+-----------------------------------------------------------------------------+
| 4. RED-TEAM / CRO REVIEW (REVIEW.md / risk_review.*)                        |
|    - Cutoff-truncation & +1d execution delay (look-ahead check)             |
|    - 2x transaction costs, LOYO, top-5-day dependence, DSR / PBO            |
+-----------------------------------------------------------------------------+
                                      |
                                      v
+-----------------------------------------------------------------------------+
| 5. VERDICT & ARCHIVE                                                        |
|    - Publish code, reports, and honest rejection reasons                    |
+-----------------------------------------------------------------------------+
```

---

## Included Studies

| Date | Study | Representative Test | Verdict | Rejection / Outcome Reason |
|---|---|---|---|---|
| 2026-10-22 | [`2026-10-22_us-golden-cross-voo-qqq`](2026-10-22_us-golden-cross-voo-qqq/README.md) | 50/200-Day Golden Cross (SPY / QQQ / GSPC / NDX) | **Adopted** | Comparable CAGR to Buy & Hold (`10.3%` vs `10.9%` on SPY; `11.2%` vs `8.2%` on QQQ) with much lower MDD (`-34.0%` vs `-55.4%` on SPY; `-36.2%` vs `-82.7%` on QQQ), though post-2010 QQQ lagged Buy & Hold and trade count is small (`16–28`). |
| 2026-10-23 | [`2026-10-23_rebalancing-front-running`](2026-10-23_rebalancing-front-running/README.md) | Pension Rebalancing S1 (SPY/IEF) & KR Single-Stock LETF Rebalance | **Rejected** | `89x` annual turnover (`~7%p/yr` cost) + next-day open execution wiped out paper excess return (S1 Sharpe `-0.283`, CAGR `-1.14%` vs SPY `+11.36%`). KR LETF failed OOS and 3-year history gate (`54` OOS days). |
| 2026-10-26 | [`2026-10-26_turtle-trading`](2026-10-26_turtle-trading/README.md) | Turtle(a) Next-Day Open (36y, KODEX 200 / KQ150 / US) | **Rejected** | Drawdown reduction came from `53–75%` idle cash; trailed constant exposure and `50/200` Golden Cross, and missed `DSR >= 0.90` (`0.460` across `540` trials). |
| 2026-10-28 | [`2026-10-28_trend-template-breakout-30y`](2026-10-28_trend-template-breakout-30y/README.md) | Minervini Trend Template Book Rule (Variant B, 30y KR 2,525 stocks) | **Rejected** | `19.4%` win rate over `3,228` trades + KR round-trip costs destroyed capital (`-13.02%` CAGR, `-98.94%` MDD); modified variants (`C2`/overlays) also failed OOS gates. |
| 2026-11-08 | [`2026-11-08_earnings-gamma-chesley-quant`](2026-11-08_earnings-gamma-chesley-quant/README.md) | Chesley Quant Q1-A (KR 52w High) & Earnings Gamma / CAN SLIM | **Rejected** | Q1-A returned `-9.52%` vs KODEX 200 `+15.30%`, trailing both all-52w-high equal-weight and random entry; earnings gamma & CAN SLIM failed `t >= 3.0`. |
| 2026-11-14 | [`2026-11-14_valuation-v2-calibration`](2026-11-14_valuation-v2-calibration/README.md) | DCF Fade Calibration (`VP4` Tercile Spread, US 528) | **Rejected (Absolute Filter) / Calibrated** | Absolute `VP4 >= 1.0` buy gate rejected `71.1%` of quality stocks (`28.9%` pass rate) and trailed simple `E/P` in KR; recalibrated to relative rank & implied half-life (`v2.1`). |
| 2026-11-15 | [`2026-11-15_valuation-v2-ex-ante-test`](2026-11-15_valuation-v2-ex-ante-test/README.md) | Ex-Ante Consensus Signal `VP_E2_4` (US 462, 2017–2022) | **Rejected (Buy Filter)** | Beat forward `E/P` (`ey_fwd`) in mean IC (`0.0582` vs `0.0134`, `H2` met), but tercile spread was positive in only `4/6` years (`H1`/`H3` failed); retained as a narrative translator only. |
| 2026-11-18 | [`2026-11-18_index-overheat-signals`](2026-11-18_index-overheat-signals/README.md) | Index overheat/oversold z-scores: P/E, P/B, 200-day gap, forward P/E (S&P 500, Nasdaq 100, SOX, KOSPI, KOSDAQ), monthly and daily | **Rejected (0 signals; KOSDAQ P/B on hold)** | Trailing-window z-scores failed Bonferroni-corrected Newey-West tests (`|t| ≥ 2.73`) or episode counts; KOSDAQ P/B `t −4.31` had only 2 resolved undervalued episodes. Full-sample (broadcast-chart) bands flip 2 of 14 verdicts via look-ahead, baseline length and sample span. Horizon (1-9 months) and window (3/5 years) variants: 0 robust passes. |

---

## How to Reproduce

Raw market and fundamental vendor datasets are **not included** in this repository due to redistribution restrictions. To re-run the scripts, prepare your own local data from the following sources:

- **Korean Equities & ETFs:** Naver Finance / KRX adjusted daily OHLCV prices (`KOSPI`, `KOSDAQ`, `KODEX 200`, `KODEX KOSDAQ150`, single-stock LETFs) and survivorship-free constituent lists.
- **US Equities & ETFs:** Yahoo Finance / Stooq / Tiingo / EODHD daily adjusted prices (`SPY`, `IEF`, `QQQ`, `^GSPC`, `^NDX`, `^IRX` risk-free rate, and delisted US tickers).
- **Index valuation (2026-11-18):** KRX data system [11007] index P/E and P/B (registration required), Robert Shiller's public `ie_data.xls` (S&P 500 earnings), multpl.com S&P 500 P/B, Yahoo Finance index prices and VIX, FRED `DFF`, and a public CNN Fear & Greed archive. Forward P/E series were digitized from broker broadcast chart photos and are not redistributed.
- **Fundamentals & Consensus (2026-11-08, 2026-11-14, 2026-11-15):** EODHD fundamentals & analyst consensus API (`EODHD_API_KEY` via environment variable) and/or SEC EDGAR XBRL (`companyfacts`).

Standardized return-series aggregation and metrics computation (`rf = 0`, `252.0` trading days/year) can be run via:

```bash
python tools/extract_returns.py
python tools/metrics.py
```

See [`CONTRIBUTING.md`](CONTRIBUTING.md) for the full study structure and checklist.

---

## Challenge a Result

Independent scrutiny is the point of publishing this lab. If you spot a look-ahead leak, data anomaly, math discrepancy, or an alternative specification that changes a conclusion:

- Open an issue using the **[Challenge a Result](.github/ISSUE_TEMPLATE/challenge-a-result.md)** template (or **[Research Idea](.github/ISSUE_TEMPLATE/idea.md)** to propose a new test), or start a thread in **Discussions**.
- Verified corrections are never swept under the rug—they are appended to [`CORRECTIONS.md`](CORRECTIONS.md) with full `Before → After` numbers.

---

## License

- **Code (`*.py`, scripts, tools):** [MIT License](LICENSE)
- **Documents, notes, and reports (`*.md`, templates):** [CC BY 4.0](LICENSE)
