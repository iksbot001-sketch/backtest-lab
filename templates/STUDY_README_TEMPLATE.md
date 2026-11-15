# [YYYY-MM-DD] Study Title

Korean: [README.ko.md](README.ko.md)

## 1. Core Verdict / Conclusion
- **Headline verdict:** `Operating` / `Adopted` / `Conditional` / `On Hold` / `Rejected`
- **Key numbers at a glance:** Primary strategy vs. benchmark (`CAGR`, `MDD`, `Sharpe`, `Sortino`, noting `†` where standardized by `tools/metrics.py`), sample period, and verdict trigger.

## 2. Why We Did This
- Origin of the question (live trading problem, paper claim, blog hypothesis, or model calibration question).
- Pre-registered decision criteria (`PREREG.md` summary).

## 3. Rules Tested
- Exact entry, exit, rebalance frequency, position sizing, regime switch, and benchmark definitions.
- Variants and ablation comparisons tested.

## 4. Markets, Periods, Data & Costs
- Market(s), ticker universe, sample start/end dates (IS vs. OOS).
- Data sources, dividend inclusion/exclusion, corporate-action cleaning, and transaction-cost / tax assumptions.

## 5. Key Metrics
| Strategy / Variant | Market | Period | CAGR | MDD | Sharpe | Sortino | Benchmark (CAGR / MDD / Sharpe) | Source |
|---|---|---|---|---|---|---|---|---|
| | | | | | | | | |

## 6. Robustness & Overfitting Checks
- Out-of-sample vs. in-sample stability, H1/W10 split, leave-one-year-out (LOYO), `2×` cost sensitivity, `+1d` delay test, `DSR` / `PBO` / bootstrap tests.

## 7. Critical Review & Caveats
- Summary of independent recomputation (`verify`) and red-team review (`REVIEW.md`).
- Bugs found and cross-referenced in `CORRECTIONS.md` (if any), survivorship/data limits, and fair-comparison caveats.

## 8. Verdict & Adoption Status
- Final archive verdict (`Operating` / `Adopted` / `Conditional` / `On Hold` / `Rejected`) and exact deployment status (live capital, A-book guide, paper watch, archived).

## 9. Next Action
- Concrete follow-up experiments, live-monitoring milestones, or explicit archival closure criteria.

## 10. File Index
| File / Folder | Role |
|---|---|
| `PREREG.md` | Pre-registered hypotheses and gates |
| `returns/` or `src/out/returns/` | Daily return CSVs (`date,ret`) for `tools/metrics.py` |
| `REVIEW.md` | Independent red-team audit |
| `README.ko.md` | Korean companion note |
