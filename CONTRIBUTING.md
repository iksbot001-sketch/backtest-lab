# Contributing a New Study to `backtest-archive`

This repository preserves every serious strategy test—both winners adopted into live trading and ideas rejected by statistical, cost, or red-team gates—using reproducible outputs, standardized metrics, and an append-only correction log.

---

## Standard End-to-End Workflow

### 1. Create the Dated Study Folder & Copy Templates
Create a new folder in the archive root named `YYYY-MM-DD_<short-english-slug>/` and seed it from [`templates/`](templates/):
- Copy [`templates/PREREG_TEMPLATE.md`](templates/PREREG_TEMPLATE.md) -> `PREREG.md`
- Copy [`templates/REVIEW_TEMPLATE.md`](templates/REVIEW_TEMPLATE.md) -> `REVIEW.md`
- Copy [`templates/STUDY_README_TEMPLATE.md`](templates/STUDY_README_TEMPLATE.md) -> `README.md` 

### 2. Lock Pre-Registration (`PREREG.md`) First
Before running any full backtest or inspecting out-of-sample results:
- Define the primary question, falsifiable hypotheses (`H1–H3`), exact IS/OOS windows, point-in-time universe, transaction-cost model, and verdict rules.
- **Run the turnover × cost sanity screen first:** Confirm `estimated annual turnover × one-way cost < expected excess return` (lesson from `2026-10-23_rebalancing-front-running`).
- Record SHA-256 hashes of `PREREG.md` and frozen input datasets under `data/`.

### 3. Execute Backtests via Antigravity (Sandboxed Runner)
- Prepare point-in-time inputs cleanly inside the study's `data/` folder (spot-checking historical split-adjusted market caps on known anchors where applicable).
- Run execution inside the sandbox using `~/agent-fund/venv/bin/python` and log steps to `RUNLOG.md`.
- Save **all** required standardized outputs:
  - Daily strategy and benchmark returns (`date,ret`): `out/returns/<strategy>__<market>.csv` (and expose under `returns/` at the study folder root so `tools/metrics.py` discovers them automatically).
  - Full parameter grid (whenever parameters are swept): `out/grid.csv`.
  - Append every executed trial to `trial_registry.jsonl` for honest `DSR` trial counting.

### 4. Independent Recomputation & Verification
- Re-implement the signal and portfolio loop in an independent verification script without sharing mutable simulation helpers.
- Confirm spot calculations by hand (`5+` random dates/tickers) and compare headline CAGR/MDD/Sharpe/IC against the primary engine.
- If any discrepancy arises between the primary run and independent recomputation (e.g., missing H/L handling, annualization basis, stale snapshot), resolve it explicitly and **log the before → after numbers in [`CORRECTIONS.md`](CORRECTIONS.md)**. Never overwrite results silently.

### 5. Run the Red-Team Review (`REVIEW.md`)
Complete every mandatory check in [`REVIEW.md`](templates/REVIEW_TEMPLATE.md) with explicit numerical evidence:
- Look-ahead (`cutoff truncation`, `+1d` execution delay)
- Survivorship & point-in-time integrity
- `2×` transaction costs
- Single-year (`LOYO`) and top-5-day dependence
- Multiple testing (`DSR`, `PBO`, effective independent trials)
- Sub-period (`IS/OOS`, `H1/W10`) regime reversal

Assign one final verdict: `Operating`, `Adopted`, `Conditional`, `On Hold`, or `Rejected`.

### 6. Compute Standardized Metrics (`returns/` -> `metrics/STANDARD_METRICS.csv`)
Ensure daily return series (`date,ret`) follow the naming convention expected by [`tools/extract_returns.py`](tools/extract_returns.py) and [`tools/metrics.py`](tools/metrics.py), then run:

```bash
~/agent-fund/venv/bin/python tools/extract_returns.py
~/agent-fund/venv/bin/python tools/metrics.py
```

All standardized metrics use one uniform definition (`rf = 0`, `252.0` trading days/year).

### 7. Update Archive Catalog, Scorecard & Root README
1. Add the study's reported rows to [`RESULTS.csv`](RESULTS.csv) (keep `std_*` columns blank for auto-fill, set exact `folder`, `strategy`, `market`, `period`, `benchmark`, `verdict`, `verdict_reason`, `source_file`, `note`).
2. Synchronize `std_*` columns and standardized-only series from `metrics/STANDARD_METRICS.csv`:
   ```bash
   ~/agent-fund/venv/bin/python tools/update_results.py
   ```
3. Register the study's representative strategy in `REPRESENTATIVES` inside [`tools/scorecard.py`](tools/scorecard.py) (if it produces a time-series `(MDD, Sharpe)` or `(MDD, CAGR)` curve; otherwise add its short label to `NO_CURVE_STUDIES`) and regenerate [`docs/scorecard.png`](docs/scorecard.png):
   ```bash
   ~/agent-fund/venv/bin/python tools/scorecard.py
   ```
4. Update the summary table and narrative flow in [`README.md`](README.md) (marking `std_*` cells with `†`), and add new reusable rules to [`LESSONS.md`](LESSONS.md).

### 8. Append `CORRECTIONS.md` Whenever Fixing Historical Numbers
Historical study outputs and published metrics are append-only records. Whenever a bug, data clean-up, look-ahead leak, or definition discrepancy is corrected after a run, append an entry to [`CORRECTIONS.md`](CORRECTIONS.md) stating:
- Date & study folder
- Exact bug or methodology discrepancy
- `Before → After` numerical change (even if zero effect)
- How the issue was detected
