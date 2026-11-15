# Red-Team Review (`REVIEW.md`)

> Independent adversarial review completed **after** simulation and independent recomputation. Every check below must report quantitative evidence (numbers, file references), not qualitative assurances alone.

## 1. Verdict
- **Decision:** `PASS` / `CONDITIONAL` / `REJECT`
- **Representative Strategy Reviewed:** `<strategy> (<market>, <period>)`
- **One-Line Summary:**

## 2. Fatal Flaws
List any disqualifying flaws (or explicitly write `None` if verified clean):
1. ...

## 3. Adversarial Checks (Quantitative)

| Check | Status | Numeric Evidence & Audit Details |
|---|---|---|
| **Look-Ahead & Timing** (`t` -> `t+1`, cutoff truncation, `+1d` lag test) | PASS / FAIL | Cutoff test `N/N` dates matched; `+1d` delay CAGR/Sharpe: `before -> after` |
| **Survivorship & Point-in-Time Data** (delisted names, static share count, outlier cleaning, `ALL` baseline) | PASS / FAIL | Missing-fundamental / survivorship spread: `+__%p/yr`; clean vs. raw diff: `__` |
| **2× Transaction Costs** (`2x` baseline commission + slippage + tax break-even) | PASS / FAIL | Baseline net CAGR/Sharpe: `__` -> at `2×` cost: `__`; break-even cost multiple: `__×` |
| **Single-Year / Few-Event Dependence** (LOYO / ex-top-5 days & ex-top-1/5 years) | PASS / FAIL | Full Sharpe `__` -> worst single-year removal (year `____`): `__`; ex-top-5 days ROI: `__` |
| **Multiple Testing & Overfitting** (total trials, effective independent trials, `DSR >= 0.90`, `PBO`) | PASS / FAIL | Total trials `__` (effective `__`), `DSR = __`, `PBO = __%`; benchmark OOS Sharpe: `__` |
| **Window & Regime Dependence** (H1 vs. W10 / IS vs. OOS / bull vs. bear split) | PASS / FAIL | IS / H1 Sharpe `__` -> OOS / W10 Sharpe `__` (reversal yes/no); bull vs. bear alpha: `__` |

## 4. Implementation & Independent Recomputation Audit
- **Code inspection:** Confirm simulation loop (`shift`, stop fills, missing bar behavior, annualization `252/N`) matches `SPEC.md` / `PREREG.md`.
- **Independent recomputation diff:** Compare primary run vs. independent script (tolerance `<= 1e-4` or document exact root cause of divergence in `CORRECTIONS.md`).

## 5. Impact on Conclusions
- **What can be claimed safely (3 points):**
  1.
  2.
  3.
- **What cannot be claimed (3 points):**
  1.
  2.
  3.

## 6. Reviewer Confidence
- **Confidence Level:** `HIGH` / `MEDIUM` / `LOW`
- **Justification & Remaining Blind Spots:**
