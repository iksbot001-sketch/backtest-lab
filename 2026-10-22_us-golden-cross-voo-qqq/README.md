# 2026-10-22 US Golden Cross (VOO & QQQ 50/200)

> **Status:** adopted. The rule itself (50/200-day moving-average cross on S&P 500 / Nasdaq-100) is public knowledge; position sizes and account data are not included.

## Summary
Applied the 50-day / 200-day moving average golden cross rule to the S&P 500 (VOO, SPY) and Nasdaq-100 (QQQ), and compared it against Buy & Hold.
Returns were similar while maximum drawdown (MDD) dropped significantly, so it was rated "Operate" (private note (not published)).

## Why (purpose and context)
- This folder does not contain PREREG, PLAN, TASK, RUNLOG, or REPORT. The exact question the owner asked and the context at the time could not be verified.
- The reference document is titled "Korea is at -37%, US is still in a Golden Cross (Backtesting 10 Quant Strategies)" (private note (not published)).
- It appears to be part of a backtest that tested 10 quant strategies together. The same document mentions the methodology note `백테스팅_v1_261108` and "Turtle comparison" (private note (not published)).
- The central theme of the post is the contrast between the US maintaining a golden cross and Korean indices being weak (private note (not published)).

## What was tested
- Question/Hypothesis: Can a 50/200 golden cross avoid bear markets while maintaining index buy-and-hold returns? (Not explicitly stated as a hypothesis in the document; inferred from the results statements.)
- Markets/Assets: US ETFs SPY and QQQ (confirmed in code); live alerts use VOO and QQQ. Long-term validation uses the S&P 500 index (GSPC) and Nasdaq-100 index (NDX). KOSPI and KOSDAQ are included for comparison (`scripts/longrun.py`, private note (not published)).
- Period: SPY from 1994-03-01, QQQ from 2000-03-01 (`scripts/idx.py`). GSPC from 1971-01-01, NDX from 1986-11-01 (`scripts/longrun.py`). End date could not be verified (status output is as of 2026-10-20 and 2026-10-21, `out/kelly_out.txt`).
- Data source: Uses the `yh()` function reading Yahoo daily bars (`scripts/longrun.py`). Raw data is not in this folder (private source list).
- Rules: Hold when the 50-day MA is above the 200-day MA; sell 100% at the next US market open on a dead cross; buy at the next open on a golden cross. Signals are based on closing prices (private note (not published)).
- Costs: One-way commission of 0.07% and 1 tick slippage ($0.01) applied (`scripts/engine.py`).
- Pre-specified pass/fail criteria: None (could not be verified).

## Results
SPY and QQQ appear to be on a total-return basis including dividends, while GSPC and NDX are price indices excluding dividends (comment in `scripts/longrun.py`). CAGR = compound annual growth rate, MDD = maximum drawdown, Sharpe = return relative to volatility.

| Target (start) | Strategy | CAGR | MDD | Sharpe | Source |
|---|---|---|---|---|---|
| SPY (1994~) | Golden Cross | 10.3% | -34.0% | 0.60 | `out/idx_metrics.csv` |
| SPY (1994~) | Buy&Hold | 10.9% | -55.4% | 0.52 | `out/idx_metrics.csv` |
| QQQ (2000~) | Golden Cross | 11.2% | -36.2% | 0.57 | `out/idx_metrics.csv` |
| QQQ (2000~) | Buy&Hold | 8.2% | -82.7% | 0.36 | `out/idx_metrics.csv` |
| GSPC (1971~) | Golden Cross | 8.8% | -34.8% | 0.39 | `out/long_metrics.csv` |
| GSPC (1971~) | Buy&Hold | 8.2% | -57.2% | 0.30 | `out/long_metrics.csv` |
| NDX (1986~) | Golden Cross | 13.8% | -39.9% | 0.60 | `out/long_metrics.csv` |
| NDX (1986~) | Buy&Hold | 14.3% | -82.8% | 0.53 | `out/long_metrics.csv` |

- Trade count: SPY 16 trades, QQQ 17 trades, GSPC 28 trades, NDX 25 trades. Market exposure: SPY 77%, QQQ 74% (`out/idx_metrics.csv`, `out/long_metrics.csv`).
- In the post-2010 period, Buy&Hold outperformed on QQQ with Golden Cross CAGR of 15.2% vs. Buy&Hold 18.7% (`out/idx_sub_metrics.csv`).
- Numbers in the document body differ from the CSVs. The document lists S&P 500 at 7.6% (Buy&Hold 8.6%) and Nasdaq at 13.8% (14.2%), and for Korea, KOSPI 6.2% / MDD -47% and KOSDAQ 1.9% / -69% (private note (not published)). It notes these were recalculated during the Turtle comparison; those recalculation files could not be found in this folder.
- CRO (risk officer) warning in the document: QQQ Monte Carlo 95% MDD is -54.3% (private note (not published)).
- Korean index results cannot be reproduced in this folder because raw Korean index data files are excluded from the public repository.

## Verdict and reasons
- Verdict: Operate (private note (not published)).
- Reason: Returns were similar to holding the index, while avoiding bear markets reduced MDD. Confirmed in an independent recalculation by Claude (private note (not published)).
- In the CSVs above as well, MDD fell from -55% to -34% for SPY and from -83% to -36% for QQQ (`out/idx_metrics.csv`).

## Caveats and limitations
- VOO and QQQ suffer losses together during bear markets (CRO warning, private note (not published)).
- Korean index figures (KOSPI, KOSDAQ) were not independently verified by Claude (private note (not published)).
- Numbers in the document and the CSVs diverge. This may be due to differences in data or periods used, but the cause could not be confirmed.
- On QQQ, returns were lower than Buy&Hold after 2010. A comment notes that since most strategies were known before 2010, post-2010 is effectively out-of-sample (`scripts/idx2.py`, `out/idx_sub_metrics.csv`).
- During 2000–2009, QQQ Buy&Hold had a CAGR of -6.6%. The golden cross advantage relies heavily on the dot-com bust and the 2008 crash (`out/idx_sub_metrics.csv`).
- Tests on price indices excluding dividends are only meaningful for relative comparison (comment in `scripts/longrun.py`). Open prices were frequently missing prior to the 1980s, so proxy values were used (same file).
- With few trades (16–28), statistical confidence is limited. In post-hoc analysis, each Forward PER bucket in the current regime had only 1–3 samples (`out/pe_gc.txt`).
- A survivorship bias check exists in `charts/03_bigtech_survivorship.png`, but the image contents were not read (could not be verified).

## What happened next
- Operations: a daily alert job (not published) sends Telegram alerts for VOO and QQQ golden/dead crosses at 07:10 KST Tuesday–Saturday (private note (not published)).
- In the "AI War Deck" investment example, "liquidate even individual stocks on a QQQ dead cross" was used as a rule (private note (not published)).
- Additional analyses: performance by Forward PER at golden cross entry (`out/pe_gc.txt`), Kelly sizing (`out/kelly_out.txt`), lump-sum vs. staged entry comparison (`ladder/out_re.txt`), and 2x/3x leverage tests (`out/lev_metrics.csv`).
- In the staged entry comparison, SPY lump-sum average return (11.1%) beat 6-month dollar-cost averaging (8.8%) (`ladder/out_re.txt`).
- 2x and 3x leverage had large MDDs of -60% to -80% (SPY 3x Golden Cross -77.3%, `out/lev_metrics.csv`) and were not reflected in the document's verdict. Whether they were adopted elsewhere could not be verified.
- Blog post: "Korea is at -37%, US is still in a Golden Cross (Backtesting 10 Quant Strategies)" (private note (not published)). Whether it was published could not be verified.

## File guide
- `out/idx_metrics.csv`: Performance table of 10 strategies for SPY and QQQ (including Golden Cross).
- `out/long_metrics.csv`: Long-term validation performance table for GSPC and NDX.
- `out/idx_sub_metrics.csv`: Sub-period performance split into 2000–2009 and 2010–present.
- `out/lev_metrics.csv`: 1x, 2x, and 3x leverage tests.
- `out/pe_gc.txt`, `out/pe_gc2.txt`, `out/pe_gc_trades.csv`, `out/pe_gc_paths.csv`: Trade-by-trade results and analysis by PER bucket.
- `out/kelly_out.txt`, `out/compare3.txt`: Kelly sizing and return comparison across ETFs (SPY, VOO, IVV, QQQ).
- `ladder/`: Staged entry comparison and post-entry further drawdown distribution.
- `charts/`: 3 charts covering equity curve & drawdown, win rate & payoff ratio, and Big Tech survivorship bias.
- `scripts/`: Backtest code. `engine.py` (execution & costs), `idx.py`, `idx2.py`, `longrun.py` (strategy definition and execution), `load.py` (data loading).
