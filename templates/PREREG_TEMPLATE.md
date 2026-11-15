# Pre-Registration (`PREREG.md`)

> Complete and lock this document **before** running any backtest or viewing out-of-sample performance. Record its commit hash or file hash alongside data hashes before execution.

## 1. Research Question
- **Core question:** State the single primary question this study answers in plain language.
- **Decision impact:** Specify what portfolio, allocation, or rule changes if hypotheses pass vs. fail.

## 2. Hypotheses
| ID | Null / Hypothesis Statement | Measurable Metric & Threshold | Failure Mode |
|---|---|---|---|
| H1 | | | |
| H2 | | | |
| H3 | | | |

## 3. Markets & Benchmarks
- **Target market(s):** e.g., US (S&P 500), KR (KOSPI / KOSDAQ).
- **Primary benchmark(s):** Exact ticker / index definition and whether total-return (dividends reinvested) or price-only.
- **Pre-screen check (turnover × cost):** Verify whether the source idea's return is pre-cost / close-to-close, and confirm `estimated annual turnover × one-way cost < expected excess return` prior to full simulation.

## 4. Windows (In-Sample / Out-of-Sample)
- **Full sample:** `YYYY-MM-DD ~ YYYY-MM-DD`
- **In-sample (IS):** `YYYY-MM-DD ~ YYYY-MM-DD`
- **Out-of-sample (OOS):** `YYYY-MM-DD ~ YYYY-MM-DD` (must be strictly locked prior to viewing results; verify OOS >= 3 years where structurally applicable).
- **Sub-period / regime splits:** e.g., H1 vs. W10, bear vs. bull, crisis stress windows.

## 5. Universe (Point-in-Time)
- **Inclusion criteria:** Liquidity, minimum market cap, listing status, sector exclusions.
- **Point-in-time guarantee:** Confirm how delisted/acquired names are kept, confirm no backward projection of ending share counts or latest fundamentals/consensus snapshots, and document any survivorship-bias baseline (`ALL_me_panel` or equal-weight universe).
- **Missing data / corporate action rule:** Specify exact handling for missing OHLC bars (e.g., fail condition vs. fill) and abnormal split/price-jump screening.

## 6. Execution Timing & Transaction Costs
- **Signal timestamp -> execution fill:** e.g., close of day `t` signal -> open of day `t+1` (or close `t+1`) fill; ban same-day MOC unless proved observable before cutoff.
- **One-way cost schedule by market:**
  - US: commission + slippage (`__ bps`)
  - KR: commission + slippage (`__ bps`) + securities transaction tax on sells (`__ bps`, specify regime year)
- **Cash interest / borrow cost:** Risk-free rate convention (`rf = 0` for `tools/metrics.py` standardized metrics vs. cash yield if modeled separately) and short borrow fees if applicable.

## 7. Signals & Strategy Definitions
- Exact mathematical/logical rules for each baseline, candidate strategy, rebalance frequency, position sizing, and holding buffer.
- Note baseline simple comparators (`Buy&Hold`, matched-exposure hold, equal-weight universe, simple `E/P` or `50/200 Golden Cross`).

## 8. Pre-Registered Verdict Rules
- **Adopt / Operating:** Exact numerical conditions all primary gates must clear.
- **Conditional / Hold:** Conditions under which the signal is retained only as an auxiliary tool or paper-traded.
- **Reject:** Objective disqualifiers (`DSR < 0.90`, `OOS` underperformance vs. B&H, failure of cutoff-truncation / `+1d` delay test, excessive concentration).

## 9. Number of Trials & Parameter Grid
- **Planned variants / parameters:** List exact combinations (`N_trials = __`).
- **Grid disclosure:** All tested combinations must be written to `out/grid.csv` (never cherry-pick best parameters), and all executions logged to `trial_registry.jsonl`.

## 10. Known Limitations (Declared Before Running)
- e.g., missing historical KOSPI dividend adjustment, short OOS window, reliance on synthetic ETF proxy before listing date, single-country scope.

## 11. Required Outputs
- **Standardized daily returns:** `out/returns/<strategy>__<market>.csv` with columns `date,ret` (plus `returns/` symlinks/copies for `tools/extract_returns.py` & `tools/metrics.py`).
- **Full parameter grid (when parameters vary):** `out/grid.csv` containing metrics for every tested combination.
- **Run log:** `RUNLOG.md` documenting execution steps, spot hand-recalculations, independent checks, and any discrepancies.

## 12. Input Data & Specification Hashes
| Artifact | Path | SHA-256 Hash | Snapshot Date |
|---|---|---|---|
| Preregistration | `PREREG.md` | | |
| Primary market data | `data/...` | | |
| Fundamentals / consensus | `data/...` | | |
