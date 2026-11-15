# 2026-11-15 Valuation Engine v2 Ex-Ante Validation

## Summary
We conducted an ex-ante validation of whether price-to-fair-value rankings—computed using only consensus estimates and reported financials available as of the evaluation date for fiscal years 2017–2022—predict subsequent 3-year excess returns (src/TASK.md).
The ex-ante signal (VP_E2_4) achieved a mean information coefficient (IC = Spearman rank correlation) of 0.0582, higher than simple forward earnings yield (0.0134), but its 3-tercile excess return spread was positive in only 4 of the 6 years; accordingly, pre-specified core hypotheses H1 and H3 were judged not met, while H2 was met (src/out/REPORT.md, src/RUNLOG.md).

## Why (purpose and context)
In the preceding calibration backtest (2026-11-14), valuation engine v2 was tested using realized 3-year financials ex-post (src/TASK.md).
This validation was performed to check whether price-to-fair-value rankings still work when fed only information actually known on the evaluation date—reported financials after 10-K (U.S. annual report) filing and contemporaneous consensus estimates (src/TASK.md, src/src/build_inputs.py).
At the same time, we compared whether the complex valuation engine has better predictive power than simple forward earnings yield (E/P = forward EPS ÷ stock price) (src/TASK.md).
We tested only cross-sectional relative ranking predictive power, not an absolute buy threshold (fair value > price) (src/TASK.md).

## What was tested
- Question/hypothesis: Validate whether fair value ÷ stock price rankings calculated with evaluation-date consensus predicted subsequent 3-year excess returns, and whether they outperformed simple forward earnings yield (ey_fwd) (src/TASK.md).
- Market/assets: 462 U.S. stocks, totaling 2,202 observations (src/TASK.md, src/RUNLOG.md).
For the sector-neutral analysis, 2,200 observations are used after excluding 2 observations in the Consumer Goods sector, which had fewer than 5 observations (src/RUNLOG.md).
- Period: Fiscal years (FY) t = 2017–2022, spanning evaluation dates (eval_date) from 2017-06-29 to 2023-03-31 (src/TASK.md, src/out/panel.csv).
5-year excess returns (ex5) cover only 2017–2020 observations (src/TASK.md).
- Data source: data/inputs.csv, which joins the calibration backtest (adhoc_20261114_val2_calibration) input table with FY t revenue, operating income, and net income from EODHD fundamentals, plus revenue and EPS growth rates and analyst count from EODHD consensus (+1y last snapshot) (src/TASK.md, src/src/build_inputs.py).
- Rules (entry, exit, weighting, costs, etc. — key points only):
Without assuming trading costs, slippage, or portfolio weights, evaluation is based on annual signal-sorted tercile equal-weighted excess returns (ex3 = 3-year excess return, ex5 = 5-year excess return) and Spearman rank correlation (IC) (src/TASK.md, src/src/exante.py).
Engine parameters are discount rate r = 0.09, tax rate 0.21, cash-flow timing lag = 0.75, with net_cash added (src/TASK.md, src/src/exante.py).
Ex-ante signal E1 (VP_E1_4, half-life h = 4 years) sets year-1 revenue growth to consensus (g1c), fades years 2 and 3 toward a 4% nominal growth rate, and holds operating margin at FY t realized margin (m0) for 3 years (src/TASK.md, src/src/exante.py).
Ex-ante signal E2 (VP_E2_4 has h = 4 years, VP_E2_8 has h = 8 years) uses the same revenue path as E1 and applies operating margin m0 × (1 + EPS growth consensus) ÷ (1 + g1c), clipped to 0.5·m0 ~ 1.5·m0, for 3 years (src/TASK.md, src/src/exante.py).
For comparison, implied half-life (-hs_E2), simple forward earnings yield (ey_fwd), forward sales yield (sy_fwd), and an oracle using realized ex-post financials (VP_O_4) are also computed (src/TASK.md, src/src/exante.py).
- Pre-specified verdict criteria (if any):
H1 is met if VP_E2_4's overall 3-tercile ex3 top-minus-bottom mean spread is greater than 0 and positive in at least 5 of the 6 years (src/TASK.md).
H2 is met if VP_E2_4's overall mean IC is greater than ey_fwd's overall mean IC (src/TASK.md).
H3 is met if H1's conditions are also satisfied on a sector-neutral basis (annual percentile rank within sector) (src/TASK.md).

## Results
- Overall mean IC (2017–2022) for ex-ante signals: VP_E2_4 is 0.0582 (t-stat 1.4078), VP_E1_4 is 0.0601 (t-stat 1.6947), and VP_E2_8 is 0.0607 (t-stat 1.5209) (src/out/REPORT.md).
- Overall mean IC for benchmarks: simple forward earnings yield (ey_fwd) is 0.0134 (t-stat 0.2299), forward sales yield (sy_fwd) is 0.0265 (t-stat 0.3756), and oracle (VP_O_4) is 0.4331 (t-stat 12.6734) (src/out/REPORT.md).
- Sector-neutral mean IC: VP_E2_4 is 0.0525 (t-stat 1.2765), VP_E1_4 is 0.0529, ey_fwd is 0.0174, sy_fwd is 0.0127, and VP_O_4 is 0.3787 (src/out/REPORT.md).
- Overall 3-tercile ex3 top-minus-bottom mean spread: VP_E2_4 is +0.0132 (median +0.0548, positive in 4 of 6 years), ey_fwd is -0.0408 (median +0.0339, positive in 3 of 6 years), and VP_O_4 is +0.8676 (positive in all 6 years) (src/out/REPORT.md).
- Sector-neutral 3-tercile ex3 top-minus-bottom mean spread: VP_E2_4 is +0.0492 (median +0.0613, positive in 4 of 6 years), ey_fwd is 0.0000 (positive in 4 of 6 years), and VP_O_4 is +0.7683 (positive in all 6 years) (src/out/REPORT.md).
- 5-year excess return (ex5, 2017–2020) overall 3-tercile mean spread: VP_E2_4 is +0.1537 (sector-neutral +0.1914), and ey_fwd is -0.0224 (sector-neutral +0.0646) (src/out/REPORT.md).
- Annual pass rate (share with fair value ÷ price ≥ 1): VP_E2_4 overall ranged from 6.55% (2020) to 20.00% (2022), while oracle (VP_O_4) pass rate in the same years ranged from 10.49% (2021) to 30.95% (2019) (src/out/REPORT.md).
- Annual correlation between consensus revenue growth (g1c) and realized year-1 revenue growth ranged from 0.4945 (2019) to 0.7560 (2022) (src/out/REPORT.md).

## Verdict and reasons
Documented hypothesis verdicts: H1 not met, H2 met, H3 not met (src/RUNLOG.md, src/out/REPORT.md).
Final interpretation (Claude, Obsidian `벨류에이션_v2_261114.md` Ch. 14): When fed realized financials, IC was 0.43; when fed contemporaneous consensus, it dropped to 0.06. Most of the strong predictive power in the calibration backtest came from knowing the future.
Therefore, it was decided to use the engine strictly as a translator that converts scenarios into value rather than as a buy signal. The source of excess return is a view that differs from consensus, and it was decided to record "how my view differs from consensus" on the scenario card (v2.2).
H2 was met because VP_E2_4's mean IC (0.0582) exceeded ey_fwd's (0.0134) (src/out/REPORT.md).
For H1 and H3, VP_E2_4's 3-tercile ex3 mean spread was positive both overall (+0.0132) and sector-neutral (+0.0492), but it recorded negative spreads in 2017 (overall -0.3337, sector-neutral -0.2628) and 2021 (overall -0.1161, sector-neutral -0.1105), reaching only 4 positive years out of 6 and falling short of the threshold (at least 5 years) (src/out/REPORT.md, src/TASK.md).

## Caveats and limitations
The input-generation script (build_inputs.py) loads the calibration backtest (adhoc_20261114_val2_calibration) input table directly and only excludes consensus outliers (g1c < -0.5 or g1c > 2.0); how survivorship bias was controlled in the parent sample cannot be verified because that original script is not in this folder (src/src/build_inputs.py, private source list).
The sample period is short at 6 years (2017–2022; 4 years for ex5), giving VP_E2_4's mean IC a t-statistic of 1.4078 (1.2765 sector-neutral) and low statistical significance (src/out/REPORT.md).
109 observations with operating margin m0 ≤ 0 were left blank in the ex-ante signals (VP_E1_4, VP_E2_4, VP_E2_8, hs_E2), and 190 observations were left blank in ey_fwd due to net income ≤ 0 or missing gec (src/RUNLOG.md, src/out/gates.txt, src/src/build_inputs.py).
These are rank and quantile comparisons without trading costs, taxes, turnover, or execution feasibility (src/TASK.md, src/src/exante.py).
Regarding the verification gate checking whether oracle (VP_O_4) matches VP4 from the preceding calibration backtest, the original file is outside the workspace, so only recomputed values remain in out/panel.csv; the actual comparison result cannot be verified within this folder (src/TASK.md, src/RUNLOG.md).

## What happened next
Cannot be verified (the extra analysis file out/EXTRA.md was not generated, and there are no records of follow-up work, production deployment, or blog posts in this folder) (src/dispatch.out).

## File guide
- src/TASK.md: Task specification containing the validation questions, data definitions, signal formulas, H1–H3 verdict criteria, and verification gates.
- src/RUNLOG.md: Execution log recording summary results, verification gate passes, observation/blank counts, and H1–H3 verdicts.
- src/out/REPORT.md: Final report compiling hypothesis verdicts and all markdown tables A–F.
- src/out/gates.txt: Verification output recording the engine check value (347.4534), manual recalculation match for 5 random stocks, and blank counts by signal.
- src/out/: Output directory containing tables A (A_*.csv), B (B_*.csv), D (D_pass.csv), E (E_corr.csv), F (F_consensus.csv), and full computation results panel.csv.
- src/src/build_inputs.py: Preprocessing script that joins EODHD financials and consensus onto the calibration backtest inputs to produce data/inputs.csv.
- src/src/exante.py: Execution script that computes ex-ante and benchmark signals and generates tables A–F and REPORT.md.
- src/src/engine.py: Valuation engine v2 library computing enterprise value from a 3-year explicit forecast, half-life fade, and terminal value.
- src/dispatch.py · src/dispatch.out · src/agent_bt_calc_claude-sonnet-5-5-medium.log.json: Dispatch script, output, and execution log used to delegate and run TASK.md on an agent.
- private note (not published)
- private source list: Guide file recording the original execution path and excluded items for this archive folder.

