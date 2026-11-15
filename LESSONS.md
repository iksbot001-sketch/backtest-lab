# Lessons Learned

Reusable rules distilled from the 13 backtest studies in this archive (rejection reasons, independent recomputations, red-team reviews, and engineering post-mortems).

---

## Costs & Turnover

- **Pre-screen daily-bps flow anomalies before coding:** Verify first whether the source paper reports close-to-close and pre-cost returns, and require `annual turnover × one-way cost < expected excess return` before running any backtest (fund lesson from `20261023_01_rebalancing_frontrun`: `89x` annual turnover at `7 bps + 1 tick` cost leaked `~7%p/yr`, turning full-sample Sharpe `-0.283`).
  - Study: `2026-10-23_rebalancing-front-running`
- **Verify high-frequency stock breakouts net of realistic round-trip tax and slippage:** Reject tight-stop equity rules early when low win rates and frequent churn make compounding impossible after costs (`Book Rule Variant B`: `19.4%` win rate over `3,228` trades yielded `-13.0%` CAGR and `-98.9%` MDD over 30 years).
  - Study: `2026-10-28_trend-template-breakout-30y`
- **Never run a weekly multi-condition screener as a portfolio without a holding buffer:** Re-evaluating strict 8-rule entry filters every week forces excessive churn (`23x/yr` turnover / `3.36%p/yr` cost in US `TS`; `9.5x/yr` / `2.22%p/yr` in KR `TS`) that destroys gross alpha.
  - Study: `2026-11-15_trend-x-valuation-combo`
- **Validate intraday grid/ladder rules against real live-account fills:** Confirm that simulated 5-minute rebalancing profits survive real slippage, taxes, and partial fills (`Live Account Ladder` indexed `114` vs `B&H 109`).
  - Study: `2026-10-17_kosdaq150-volatility-harvest`
- **Require net per-trade alpha to clear small/mid-cap execution friction with margin:** Disqualify event/earnings signals whose after-cost edge turns negative or borderline (`Forward Gamma S2/S3` returned `-2.00%/trade`, `t = -1.24`, vs SPY net of costs).
  - Study: `2026-11-08_earnings-gamma-chesley-quant`

---

## Look-Ahead & Timing

- **Run cutoff-truncation / future-shuffle tests on every backtest:** Never rely solely on PSR or DSR to detect look-ahead leaks, because leaking features (`Exp 1 Leaking Oracle`, `Sharpe 6.12`) pass statistical gates until `20`-date truncation catches `17/20` weight mismatches.
  - Study: `2026-10-24_ai-backtest-reliability`
- **Enforce `t` close signal to `t+1` open execution and run a `+1`-day delay test:** Reject strategies whose edge evaporates when shifting impossible same-day MOC fills to observable next-day open (`20261023_01` zero-cost Sharpe fell `0.52 -> 0.17` on `+1d` delay; `20261023_02` IS gross ROI collapsed `+168% -> -17%`).
  - Study: `2026-10-23_rebalancing-front-running`
- **Separate ex-ante consensus validation from realized-financial oracle tests:** Always re-run fundamental valuation signals using strictly point-in-time consensus (`VP_E2_4` mean IC `0.0582`, positive tercile spread in only `4/6` years) rather than assuming oracle IC (`VP_O_4`: `0.4331`) carries over live.
  - Study: `2026-11-15_valuation-v2-ex-ante-test`
- **Explicitly align daily index regime switches and consensus snapshot windows:** Apply conservative execution lags (`REG.shift(2)` on cross-asset daily signals) and exclude point-in-time snapshot artifacts (`VALC` consensus snapshot) from multi-decade conclusions.
  - Study: `2026-11-15_trend-x-valuation-combo`
- **Audit boolean holding arrays against same-day stop-loss boundaries:** Ensure `held.shift(1)` positioning never skips intraday stop triggers or shifts trade boundaries by one bar (`KQ150` Turtle Mode (b) shifted `75 -> 74` trades).
  - Study: `2026-10-26_turtle-trading`

---

## Survivorship & Data

- **Benchmark against an all-universe baseline (`ALL_me_panel`) and ban static historical share counts:** Quantify missing-fundamental survivorship (`+1.07%p/yr` in US), never project current share counts backward (`lastsh` invariant across `0/807` KR tickers), and scrub multi-bagger price errors (`US` `ACS +17,208%` inflated equal-weight CAGR `10.05% -> 14.35%`).
  - Study: `2026-11-15_trend-x-valuation-combo`
- **Clean corporate-action price spikes before trusting small/mid-cap factor regressions:** Detect and sanitize anomalous single-day vendor jumps (`EODHD` `99x`/`4x` jumps like `SCU`, `OSB`, `LCI`), which deflated `SURP Ridge Rule A` from `+4.55%/trade (t=2.18)` to `+2.77%/trade (t=1.52)`.
  - Study: `2026-11-08_earnings-gamma-chesley-quant`
- **Gate input generation on historical market-cap anchor spot checks:** Verify split-adjusted price × shares against known historical market caps (`AAPL 2015-12-31`, `MSFT 2019-12-31`, `NVDA 2020-12-31` within `+1~3%`) and retain delisted/ended tickers (`149` US names) whenever statements exist.
  - Study: `2026-11-14_valuation-v2-calibration`
- **Never compare dividend-adjusted ETF returns to price-only index series without disclosure:** Label dividend inclusion explicitly when juxtaposing `SPY`/`QQQ` (total return) against `^GSPC`/`^NDX`/`KOSPI`/`KOSDAQ` (price return) across mismatched start dates.
  - Study: `2026-10-22_us-golden-cross-voo-qqq`
- **Freeze data snapshots during verification and verify synthetic leveraged proxies:** Disallow live `refresh=True` downloads inside verification scripts (`refresh=False` drifted OOS `-29.7%` to `-29.3%`), and calibrate synthetic 2x series against actual ETF prices (`4,211` vs `4,790 KRW`).
  - Study: `2026-10-23_rebalancing-front-running`

---

## Overfitting & Multiple Testing

- **Penalize multi-rule searches with correlation-adjusted `DSR >= 0.90` and `PBO`:** Compute effective independent trials from pairwise strategy return correlations rather than nominal count, and reject in-sample winners whose OOS Sharpe lags buy-and-hold (`Exp 2`: IS `0.65` -> OOS `0.46`, `DSR 0.56`, `PBO 68.8%`).
  - Study: `2026-10-24_ai-backtest-reliability`
- **Maintain an append-only `trial_registry.jsonl` and test sizing grids for flat plateaus:** Count every executed specification (`540` actual vs `201` reported dropped `KODEX 200` DSR `0.636 -> 0.460`) and flag constant-Sharpe neighbors caused by sizing floors (`atr_n 16–22` identical `0.278`).
  - Study: `2026-10-26_turtle-trading`
- **Enforce `t >= 3.0` on post-hoc factor screens and require equal-weight / random baselines:** Treat after-the-fact refinements (`Q/C/P top 10%` `t = 2.98`, `CAN SLIM` `t = 1.39`) as exploratory only, and reject rules that trail random entry or equal-weight peer universes (`Chesley Q1-A -9.52%` vs random `-6.80%` and 52w-high equal-weight `-1.17%`).
  - Study: `2026-11-08_earnings-gamma-chesley-quant`
- **Never promote thresholds calibrated on full-sample loss diagnostics (`S1`) as validated rules:** Any filter (`ATR <= 4.5%`) discovered after examining why `C2` lost money requires fresh out-of-sample data before adoption.
  - Study: `2026-10-28_trend-template-breakout-30y`
- **Benchmark complex valuation models against trivial `E/P` and avoid rigid absolute buy cutoffs:** Require DCF/fade models (`VAL0`) to outperform simple earnings yield (`EY` beat `VAL0` across all KR windows: `7.83%` vs `6.69%`), and prefer relative rank / implied fade over absolute fair-value filters (`VP4 >= 1.0` rejected `71.1%` of quality stocks).
  - Study: `2026-11-14_valuation-v2-calibration`

---

## Regime & Period Dependence

- **Require stability across sub-period splits (`H1` vs `W10`) and leave-one-year-out (`LOYO`) checks:** Reject general claims of outperformance when recent-decade leadership reverses (`VAL0 > BH` and `MIX_TI0.5 > BH` flipped negative in `2016–2026` in both US and KR) or flips on removing single years (`2008`, `2009`, `2020`, `2025`).
  - Study: `2026-11-15_trend-x-valuation-combo`
- **Compare low-exposure strategies against constant-exposure B&H and `50/200 Golden Cross`:** Separate true timing skill from passive cash drag (`53–75%` cash in `Turtle(a)` trailed `38.3%` constant exposure `0.448` Sharpe on `KODEX 200` and `50/200 GC` `0.42` Sharpe on `S&P500`).
  - Study: `2026-10-26_turtle-trading`
- **Condition crash-buying signals on cross-market breadth and secular trend regimes:** Only activate historical dip-buying triggers in verified structural regimes (`KOSPI` required concurrent US oversold; `KOSDAQ` required being below its 10-year average, yielding `17/17` historical wins on `KOSPI Base`).
  - Study: `2026-10-21_kospi-crash-dip-buying-36y`
- **Withhold binary buy verdicts when extreme episodes number in single digits or multiples diverge:** Do not deploy systematic rules on `n = 5–6` historical `-30%` drawdowns or when `PER (9–10x)` and `PBR` give conflicting regime signals.
  - Study: `2026-11-04_valuation-drawdown-study`
- **Pair positive expected-value crash models with binding numeric risk limits and tail bounds:** Anchor holding/adding decisions on explicit worst-case additional drawdowns (`-36.3%` to `-44%` historical post-event tails) and enforce tranche sizes and account-level ATR risk caps (`2.5%` limit vs `2.73%` actual) prior to execution.
  - Study: `2026-11-06_crash-hold-or-add-decision`
- **Reject strategies reliant on top-5 days/years or structurally insufficient OOS history:** Flag single-crisis concentration (`20261023_01` Sharpe fell to `-0.69` ex-top-5 years; `20261023_02` lost `77%` of IS return outside top 5 days) and refuse live deployment when product history fails minimum 3-year OOS gates (`G3`: only `54` OOS trading days).
  - Study: `2026-10-23_rebalancing-front-running`

---

## AI-Agent Workflow

- **Gate agent delegation with deterministic engine checks, spot hand-calculations, and model quota pings:** Verify reference engine test values (`347.453`), verify `5` random ticker-year rows manually, and handle sandboxed tool-denial fallbacks cleanly before accepting model output.
  - Study: `2026-11-15_valuation-v2-ex-ante-test`
- **Freeze edge-case handling, annualization (`252/N`), and standardized return outputs in `TASK.md`:** Specify exact missing-OHLC rules (close-fill `-2.5%` vs H/L-missing fail `-1.4%` drift in KR `TS`) and require `out/returns/<strategy>__<market>.csv` plus full `out/grid.csv` on every multi-agent run.
  - Study: `2026-11-15_trend-x-valuation-combo`
- **Inspect generated simulator code line-by-line against `SPEC.md` before accepting numbers:** Catch implementation errors early—such as entry-day `L <= stop` liquidating trades on day 1 (`9%` win rate / `-99%` MDD) or hard-coding `fund._cash = 0` over `^IRX` risk-free rates.
  - Study: `2026-10-28_trend-template-breakout-30y`
- **Separate implementation, independent recomputation, and adversarial review across distinct passes:** Use structured red-team checks (`CRO` / `RF_REVIEW`) so statistical flaws (`DSR` trial inflation, cash days counted as wins, missing loss-clustering warnings) are caught outside the coding pass.
  - Study: `2026-10-24_ai-backtest-reliability`
