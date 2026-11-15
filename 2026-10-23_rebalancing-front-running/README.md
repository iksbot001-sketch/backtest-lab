# 2026-10-23 Rebalancing Front-Running

## Summary
Tested two ideas that trade ahead of mechanical institutional rebalancing flows. Both US pension month-end rebalancing (01) and Korean single-stock leveraged ETF close rebalancing (02) were rejected in executable, net-of-cost form.

## Why (purpose and context)
- Both are flow-anomaly ideas originating from academic papers. The goal is to test whether a retail investor can replicate them profitably after costs (`01/idea.md`, `02/idea.md`).
- 01 comes from Harvey, Mazzoleni, and Melone, NBER Working Paper 33554 (2025), which claims that month-end rebalancing by pension funds and TDFs (target date funds) moves next-day equity returns by about -17 bp (`01/idea.md`).
- 02 comes from Yinhong Zhao, arXiv:2608.03703 (2026), which claims that front-running the close rebalancing of Samsung Electronics and SK Hynix leveraged ETFs produces next-day reversals (`02/idea.md`).
- Obsidian note `리밸런싱선행매매_261023.md` (Korean) records the pre-backtest screening calculation of `annual turnover × one-way cost`: 89x turnover and roughly 7%p annual cost (private note (not published)).
- It notes that this lesson became the first line of `lessons.md` and a rule in Chapter 1 of the backtesting v1 methodology document (`[[백테스팅_v1_261108]]` (Korean)) (private note (not published)).

## What was tested
- Question/hypothesis:
  - 01: Can institutional month-end trading direction be computed in advance from past returns alone, and does taking the opposite position yield positive net-of-cost returns? Are retail long-only variants (S2, S3) better than holding SPY (`01/memo.md`)?
  - 02: On days with a large US market shock (QQQ), does entering at the close in the opposite direction and exiting at the next day's close yield positive returns after costs and taxes? There should be no effect before ETF listing or in the control group (`02/memo.md`).
- Markets and assets:
  - 01: US ETFs SPY and IEF. The paper uses futures, which were replaced with ETFs (`01/memo.md`). TLT is also mentioned in stage 1 (`01/idea.md`).
  - 02: Underlying Korean stocks Samsung Electronics (005930) and SK Hynix (000660) after single-stock leveraged ETFs were listed. The control group consists of other large-cap stocks (an inferred list) (`02/idea.md`, `02/memo.md`).
- Period:
  - 01: 2002-09-03 to 2026-10-20 (24.1 years). Out-of-sample (OOS) starts 2023-03-20 (3.58 years) (`01/memo.md`).
  - 02: 2026-05-27 to 2026-10-22 (0.40 years). In-sample is 5/27 to 7/31; out-of-sample is 8/3 to 10/22 (0.21 years, 54 trading days) (`02/memo.md`).
- Data sources:
  - 01: Agent fund data `fund.us('SPY')`, `fund.us('IEF')` (`01/idea.md`).
  - 02: Naver daily bars (Korea), Yahoo US close prices (snapshot as of 2026-10-22) (`02/memo.md`).
- Rules (entry, exit, weights, costs — key items only):
  - 01: Signal generated at day t close, executed at day t+1 open. One-way cost is 0.07% + 1 tick. Main strategy S1 is dollar-neutral long/short SPY and IEF. Annual turnover is about 89x (`01/memo.md`, private note (not published)).
  - 02: On days when the US shock magnitude is at or above the expanding median, enter at that day's close in the direction opposite to the shock and exit at the next day's close. Costs and transaction tax are modeled at 0.20%. 30 trades, 55% exposure, 229x annual turnover (`02/memo.md`).
- Pre-specified decision criteria (if any):
  - 01: Pre-specified falsification criteria F1–F8 existed. Failed F2–F6, passed F7, and F8 (long-only vs. SPY) was rejected (`01/memo.md`).
  - 02: Falsification conditions and placebo tests existed. Gate G3 (3-year OOS) failed because OOS was only 0.21 years (`02/memo.md`, `02/status.json`). Exact falsification wording is in `falsification.json`, which was not checked in this README.

## Results
01 Pension Rebalancing S1 (open execution, 7 bp + tick one-way) vs. SPY Buy & Hold (`01/memo.md`, Section 3):

- Full-sample CAGR: S1 -1.14%, SPY 11.36%.
- Full-sample Sharpe: S1 -0.283, SPY 0.580.
- Full-sample MDD: S1 -52.07%, SPY -55.40%.
- Out-of-sample CAGR: S1 2.25%, SPY 22.50%.
- Out-of-sample Sharpe: S1 -0.374, SPY 1.154.
- Zero-cost close-to-close (paper's method, non-executable): Sharpe 0.907; open execution with zero cost: Sharpe 0.520 (`01/memo.md`).
- Breakeven cost is 0.65x the current assumption (about 4.5 bp one-way). Assuming about 1 bp one-way gives full-sample Sharpe 0.40 and OOS Sharpe 0.59 (`01/memo.md`).

02 Leveraged ETF Reversal Contrarian vs. Samsung/Hynix 50:50 Buy & Hold (`02/memo.md`, Section 3):

- Full-sample ROI (cumulative return): Strategy +69.8%, Buy & Hold -38.2%. Full-sample Sharpe: Strategy 1.96, Buy & Hold -0.77.
- In-sample ROI +141.6%, Sharpe 5.24.
- Out-of-sample ROI: Strategy -29.7%, Buy & Hold -23.5%. Out-of-sample Sharpe: Strategy -2.67, Buy & Hold -1.39.
- Retail-feasible long-only variant OOS return: -19.4%.
- Paper coefficient replication: reversal coefficient b = -1.65; excluding first 5 days b = -1.76 (matches the paper); randomization p = 0.004. OOS effect t-stat is 0.40.

## Verdict and reasons
- Verdict: Rejected (both).
- 01 was rejected by the Head Researcher (reject, score 1) (`01/memo.md`, `01/status.json`). In executable form it failed all of F2–F6, and every variant in `robustness_plan` was negative. Main causes are roughly 7%p annual cost from ~89x turnover and execution timing. Recommended weight: 0%.
- 02 has `status.json` status `'G3 failed'`. OOS 54-trading-day net return was -29.7%, and no robustness variant had >= 0 OOS return on the treatment group. Recommended weight: 0% (negative Kelly, about -0.36).
- Re-evaluation condition for 02: Re-run only after August 2029, once 3 years of OOS data have accumulated and provided the single-stock 2x leveraged ETF structure remains intact (`02/memo.md`).

## Caveats and limitations
- 01 cost sensitivity: 7 bp one-way is conservative compared to actual current SPY/IEF execution costs (spread ~0.3–1 bp). It turns positive at 1 bp, but even at the low-cost close-execution upper bound, OOS Sharpe is 0.10–0.25, falling short of SPY (1.15). The rejection should be stated as "failed under the 7 bp one-way assumption," not exaggerated as "structurally impossible" (`01/memo.md`).
- 01 return concentration: Relies on a single year (2008). Excluding the top 5 days / 5 months / 5 years drops Sharpe to -0.45 / -0.57 / -0.69. Still unrecovered from its max drawdown after 17.8 years (`01/memo.md`).
- 01 post-publication decay: Annual t-stat of the Threshold signal shrank from -2.74 / -2.96 / -2.56 in 2020–2022 to -0.48 / -0.57 / -0.17 in 2024–2026 (`01/memo.md`).
- 01 engine limitations: Zero borrow cost, omitted intraday rebalancing cost, and days exceeding Reg T margin all favor the strategy. The in-sample period overlaps with the paper authors' parameter sample (`01/memo.md`).
- 02 short sample: The effect only exists after the 2026-05-27 listing. With only 54 OOS days, even "decay" cannot be claimed statistically (`02/memo.md`).
- 02 return concentration: Of the +69.8% total return, the top 5 in-sample days account for 77% of log PnL. Excluding the top 5 days gives about -15%, and excluding July gives -13.2%. CAGR is meaningless over such a short period (`02/memo.md`).
- 02 replication is not independent validation: Same period and stocks as the paper, and the 2 treatment stocks have 0.89 correlation, making them effectively 1 bet. The paper is a pre-peer-review working paper (v4). Short returns are theoretical without borrow fees (`02/memo.md`).
- 02 CRO (Chief Risk Officer) verdict is `fix`: 0 critical issues such as lookahead bias, and 8 items requested to tone down exaggerated blog phrasing (`02/memo.md`).
- Survivorship bias is noted as not applicable for both (explicit for 01; unverified for 02).

## What happened next
- Lessons were incorporated into `lessons.md` and Chapter 1 of the backtesting v1 methodology document (private note (not published)). Rule: first verify the benchmark of the paper's returns (close-to-close, pre-cost), and screen by turnover × cost before running a backtest.
- 01 memo is recommended for a blog post (value 4/5). Candidate titles include "Why a Paper's Sharpe 1.1 Became -0.3 in My Account" (`01/memo.md`).
- 02 memo is conditionally recommended for a blog post (value 4/5) subject to CRO edits (`02/memo.md`).
- Whether a blog post was actually published or applied in live operations is unverified. The Obsidian note's `글:` field is `-`.

## File guide
- private source list: Original source paths for this folder and copy exclusion rules.
- private note (not published): Obsidian strategy log note. Summary of verdict and recorded rules.
- `20261023_01_rebalancing_frontrun/memo.md`: 01 final edited memo. Consolidates result tables, verdict, limitations, and blog outline—the first file to read.
- `20261023_01_rebalancing_frontrun/idea.md`: 01 idea card and paper reference.
- `20261023_01_rebalancing_frontrun/backtest/`: Code (`backtest.py`), `metrics.json`, `robustness.json`, `quant_report.md`, and 2 equity curve plots.
- `20261023_01_rebalancing_frontrun/backtest/cro_checks/`: CRO independent replication/verification code and results.
- `spec.json`, `head_review.json`, `risk_review.json`, `researcher_notes.md`, `status.json` in `20261023_01_rebalancing_frontrun/`: Specification, Head Researcher review, risk review, researcher notes, status.
- `20261023_02_letf_rebalance_korea/memo.md`: 02 final edited memo. Result tables, CRO findings, blog checklist.
- `20261023_02_letf_rebalance_korea/idea.md`: 02 idea card and paper reference.
- `20261023_02_letf_rebalance_korea/backtest/`: Code, `metrics.json`, `falsification.json`, `robustness.json`, `loss_structure.json` (holder loss structure), `quant_report.md`, `equity.png`.
- `20261023_02_letf_rebalance_korea/backtest/cro_checks/`: 3 rounds of CRO verification code and results.
- `spec.json`, `risk_review.json`, `researcher_notes.md`, `status.json` in `20261023_02_letf_rebalance_korea/`: Specification, risk review, researcher notes, status (G3 failed).
- This folder does not contain PREREG, PLAN, TASK, RUNLOG, or REPORT files.

