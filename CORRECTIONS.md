# Corrections & Discrepancies Log

> **Rule:** Numbers in this archive are **never silently changed**. Any bug, implementation discrepancy, methodology difference, or post-hoc correction discovered during or after a study must be appended here with its date, study, before → after numbers (when stated), and how it was found.

---

## Required & Major Archive Entries

### 2026-11-15 — Ex-Ante Valuation v2: Sandbox Denial on Initial Antigravity Runs
- **Study:** `2026-11-15_valuation-v2-ex-ante-test`
- **What was wrong:** Initial Antigravity dispatch attempts were denied by the CLI sandbox when attempting unauthorized commands/actions outside the allowed sandbox boundary.
- **Before → After:** No numerical results affected (runs were blocked prior to producing valid outputs; rerouted/completed cleanly under `claude-sonnet-5-5-medium` with `src/exante.py` and `src/RUNLOG.md`).
- **How found:** Dispatch/sandbox execution logs during multi-agent orchestration (`dispatch.py` / `dispatch.out`; cf. `2026-11-14` `dispatch.out` `[agy 권한 거부: [{'action': 'command', 'display_name': 'Bash'}]]`).

### 2026-11-14 — Valuation v2 Calibration: Split-Adjustment Direction Bug in Input Panel
- **Study:** `2026-11-14_valuation-v2-calibration`
- **What was wrong:** When reconstructing historical split-adjusted price (`px_split`) in `src/src/build_inputs.py` to multiply by point-in-time share counts for historical market cap, the cumulative split adjustment was initially applied in the wrong direction.
- **Before → After:** `AAPL` historical market cap was off by **`+1524%`**, fixed in `build_inputs.py` (`after = np.concatenate([np.cumprod(fac[::-1])[::-1], [1.0]])`) before generating `data/inputs.csv` and final results → **`+2%`** (`$589B` vs `$580B` anchor on `2015-12-31`; `MSFT +1%`, `NVDA +3%` across `src/TASK_A.md` Gate 1).
- **How found:** Pre-run Market Cap Gate 1 anchor verification (`src/src/build_inputs.py` & `src/TASK_A.md`).

---

## Chronological Log of Other Documented Bugs, Fixes & Discrepancies

### 2026-11-08 — Earnings Gamma & Chesley Quant: EODHD Price-Jump Outliers (`99x` / `4x`)
- **Study:** `2026-11-08_earnings-gamma-chesley-quant`
- **What was wrong:** Uncleaned EODHD price data contained massive single-day split/bad-print jumps (`99x` in `SCU`, `OSB`; `4x` in `LCI`), plus `282` smaller `3x–5x` jumps left unclassified; also `launchd` scheduler registration hit sandbox permission denial.
- **Before → After:** Applying `pxclean.py` to remove `SCU`/`OSB`/`LCI` errors reduced US small/mid-cap `SURP Ridge Rule A` from **`+4.55%/trade (t = 2.18)` → `+2.77%/trade (+2.3%/yr calendar, t = 1.52)`**.
- **How found:** Outlier audit and cleanup (`pxclean.py`) logged in `README.md`.

### 2026-10-28 — Trend Template Breakout 30y: Entry-Day Stop Bug, `rf` Override & 5y Rounding
- **Study:** `2026-10-28_trend-template-breakout-30y`
- **What was wrong:**
  1. Initial spec caused entry-day `L <= stop` checks to stop out nearly every new trade on day 1.
  2. Original `bt.py` pinned `fund._cash = 0`, silently overriding `^IRX` risk-free rate.
  3. Reported `5y` CAGR in blog/RUNLOG (`+15.3%`) differed slightly from `summary.csv` (`+15.2%`, exact `+15.26%`).
  4. Standardized `rf = 0` (`tools/metrics.py`) differs systematically from original `^IRX`-adjusted Sharpe ratios (`metrics/RUNLOG.md`).
- **Before → After:** Fixing entry-day stop semantics recovered win rate from **`9%` / MDD `−99%`** to **`19.4%` (`B`)** and **`~44%` (`C2`)** before final cost evaluation; removing `fund._cash = 0` restored `^IRX` in original `bt.py`; standardized `rf = 0` shifted `B 30y` Sharpe **`-0.4772` → `-0.3934`** and `C2 30y` Sharpe **`0.2469` → `0.4476`**.
- **How found:** Claude Code code review against `SPEC.md` (`src/RUNLOG.md`) and `metrics/RUNLOG.md`.

### 2026-10-26 — Turtle Trading: `shift(1)` Stop Miss, Sizing Plateau & Trial Count Under-Reporting
- **Study:** `2026-10-26_turtle-trading`
- **What was wrong:** Korea CRO audit discovered three issues:
  1. Mode (b) `pos = held.shift(1)` shifted entry/exit boundaries by 1 day and missed 1 same-day stop-loss in `KODEX KOSDAQ150`.
  2. `sizing='full'` floored leverage/weights so four `atr_n` neighbors (`16, 18, 20, 22`) returned bit-identical Sharpe, artificially inflating stability checks.
  3. Quant report cited `201` variants instead of all `540` recorded in `trial_registry.jsonl`.
- **Before → After:** `KQ150` trades changed **`75` → `74`** (`shift(1)` bug); `atr_n` `16–22` collapsed to **`0.27801018135062294`**; `KODEX 200` (a) DSR dropped **`0.636` → `0.460`** when counting all `540` trials.
- **How found:** Adversarial CRO inspection (`adhoc_20261026_1235_cro/risk_review.md`).

### 2026-10-23 — Rebalancing Front-Running: Unpinned Live Refresh, Regression Boundary Leak, Synthetic Proxy Drift & Memo Figures
- **Study:** `2026-10-23_rebalancing-front-running`
- **What was wrong:**
  1. (`02_letf_rebalance_korea`) `backtest.py` used `fund.us(refresh=True)` causing non-reproducible OOS returns across snapshots; IS regression boundary (`t = 7/31`) used `8/3` price; synthetic 2x tracker diverged from actual product price; quant memo listed `"unknown"` for `82` vs `92` observation mismatch.
  2. (`01_rebalancing_frontrun`) Memo described `2020-03` using pre-cost `+2.4%`, described MDD recovery inaccurately, and claimed no CRO output existed.
- **Before → After:** (`02`) Cached `refresh=False` gave **`-29.34%` vs `-29.72%`**; dropping boundary row shifted IS slope **`-1.65` → `-1.54`**; dropping first 5 listing days resolved `92 → 82` observations (`b = -1.761`, matching source paper `-1.76`); synthetic `10,000` grew to **`4,211` vs `4,790 KRW`** actual (`12%` gap). (`01`) `2020-03` net return corrected **`+2.4%` → `-0.2%`** (`-11.1%` full year 2020); underwater span corrected to **`2009-01` peak → `2022-07` trough (`17.8 yrs` unrecovered)**.
- **How found:** Independent CRO reviews (`20261023_01_rebalancing_frontrun/risk_review.json`, `20261023_02_letf_rebalance_korea/risk_review.json`).
