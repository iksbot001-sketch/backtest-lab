"""Generate docs/scorecard.png from RESULTS.csv using Matplotlib only.

Plots each study's representative strategy (x = Max Drawdown %, y = Sharpe in Panel A,
or y = CAGR % in Panel B when Sharpe is unavailable), colored by verdict category,
with benchmark points in grey connected by thin lines to their paired strategy.
"""
from __future__ import annotations

import csv
import os
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/tmp/mplconfig")

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

ROOT = Path(__file__).resolve().parent.parent
RESULTS_PATH = ROOT / "RESULTS.csv"
OUT_PATH = ROOT / "docs" / "scorecard.png"

# Exact representative row selector per study folder:
# (folder, strategy, market, period, short_label, panelA_offset_pts, panelB_offset_pts, bench_offset_pts)
REPRESENTATIVES = [
    (
        "2026-10-17_kosdaq150-volatility-harvest",
        "Volatility Harvest (1.5%/0.5% 5m)",
        "KODEX KOSDAQ150",
        "2021-09-02~2026-10-16",
        "10-17 Vol Harvest\n(KQ150 5m)",
        (12, -26),
        None,
        (-12, -16),
    ),
    (
        "2026-10-21_kospi-crash-dip-buying-36y",
        "Final Rule ETF Verification",
        "KODEX KOSDAQ150",
        "2015-10~2026-10-20",
        "10-21 Dip-Buy\n(KQ150 ETF)",
        None,
        (10, 6),
        (10, -14),
    ),
    (
        "2026-10-22_us-golden-cross-voo-qqq",
        "Golden Cross (50/200)",
        "SPY",
        "1994-03-01~2026-10",
        "10-22 Golden Cross\n(SPY 50/200)",
        (12, -16),
        None,
        (-86, -16),
    ),
    (
        "2026-10-23_rebalancing-front-running",
        "01 Pension Rebalancing S1 (Full)",
        "SPY / IEF",
        "2002-09-03~2026-10-20",
        "10-23 Rebal Front-Run\n(S1 Full)",
        (10, 8),
        None,
        (-92, 0),
    ),
    (
        "2026-10-24_ai-backtest-reliability",
        "Exp 3 Golden Cross (50/200)",
        "QQQ",
        "2000~2026.10",
        "10-24 AI Reliability\n(E3 QQQ 50/200)",
        None,
        (8, -22),
        (10, 8),
    ),
    (
        "2026-10-26_turtle-trading",
        "Turtle(a) Next-Day Open (36y)",
        "KODEX 200",
        "1990-01~2026-10",
        "10-26 Turtle(a)\n(KODEX 200)",
        (12, 16),
        None,
        (10, 10),
    ),
    (
        "2026-10-28_trend-template-breakout-30y",
        "Book Rule (Variant B, 30y)",
        "KR Common Stocks (2525)",
        "1996-10-28~2026-10-27",
        "10-28 Trend Templ. B†\n(KR 30y)",
        (10, 10),
        None,
        None,
    ),
    (
        "2026-11-08_earnings-gamma-chesley-quant",
        "Chesley Quant Q1-A",
        "KR Common Stocks",
        "2017-01~2026-10",
        "11-08 Chesley Q1-A\n(KR 52w High)",
        (10, 8),
        None,
        (8, 12),
    ),
    (
        "2026-11-15_trend-x-valuation-combo",
        "MIX_TI0.5 (50:50 mix)",
        "US (S&P500)",
        "2006-11-01~2026-11-06",
        "11-15 Trend×Val†\n(US MIX_TI0.5)",
        (10, 8),
        None,
        (-78, 14),
    ),
]

NO_CURVE_STUDIES = (
    "Non-equity-curve studies omitted from panels: "
    "11-04 Valuation/DD (On Hold), 11-06 Crash Hold/Add (Hold-Cond.),\n"
    "11-14 Val v2 Calib. (Adopted v2.1), 11-15 Val v2 Ex-Ante (H1/H3 Failed).  "
    "|  † = standardized rf=0 metrics (metrics/STANDARD_METRICS.csv)."
)


def classify_verdict(verdict: str) -> tuple[str, str]:
    v = verdict.lower()
    if v.startswith("operating") or v.startswith("adopted"):
        return "Adopted / Operating", "#0f766e"
    if v.startswith("rejected"):
        return "Rejected", "#dc2626"
    return "Hold / Conditional", "#d97706"


def pick_val(row: dict[str, str], std_col: str, rep_col: str) -> float | None:
    s = (row.get(std_col) or "").strip()
    if s != "":
        return float(s)
    r = (row.get(rep_col) or "").strip()
    if r != "":
        return float(r)
    return None


def main() -> None:
    with RESULTS_PATH.open("r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    index = {
        (r["folder"], r["strategy"], r["market"], r["period"]): r
        for r in rows
        if r.get("note") != "standardized only"
    }

    plt.rcParams.update({
        "font.family": "DejaVu Sans",
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.edgecolor": "#d1d5db",
        "axes.linewidth": 0.9,
    })

    fig, (ax_a, ax_b) = plt.subplots(
        1,
        2,
        figsize=(13.2, 6.2),
        gridspec_kw={"width_ratios": [1.65, 1.0], "wspace": 0.24},
        dpi=160,
    )
    fig.patch.set_facecolor("#ffffff")

    panel_a_items = []
    panel_b_items = []

    for folder, strat, mkt, period, label, off_a, off_b, boff in REPRESENTATIVES:
        row = index[(folder, strat, mkt, period)]
        mdd = pick_val(row, "std_mdd", "metric_mdd")
        sharpe = pick_val(row, "std_sharpe", "metric_sharpe")
        cagr = pick_val(row, "std_cagr", "metric_cagr")
        bmdd = pick_val(row, "std_bench_mdd", "bench_mdd")
        bsharpe = pick_val(row, "std_bench_sharpe", "bench_sharpe")
        bcagr = pick_val(row, "std_bench_cagr", "bench_cagr")
        v_cat, color = classify_verdict(row["verdict"])

        if sharpe is not None and mdd is not None:
            panel_a_items.append((label, mdd * 100.0, sharpe, bmdd * 100.0 if bmdd is not None else None, bsharpe, color, v_cat, off_a, boff, row["benchmark"]))
        elif cagr is not None and mdd is not None:
            panel_b_items.append((label, mdd * 100.0, cagr * 100.0, bmdd * 100.0 if bmdd is not None else None, bcagr * 100.0 if bcagr is not None else None, color, v_cat, off_b, boff, row["benchmark"]))

    # Panel A: MDD vs Sharpe
    ax_a.axhline(0.0, color="#9ca3af", linestyle="--", linewidth=0.9, zorder=1)
    ax_a.grid(True, linestyle=":", color="#e5e7eb", linewidth=0.8, zorder=0)
    for label, x, y, bx, by, color, v_cat, off, boff, bname in panel_a_items:
        if bx is not None and by is not None:
            ax_a.plot([x, bx], [y, by], color="#9ca3af", linewidth=1.15, alpha=0.85, zorder=2)
            ax_a.scatter([bx], [by], color="#6b7280", marker="s", s=52, zorder=3, edgecolors="#ffffff", linewidth=0.8)
            if boff is not None:
                ax_a.annotate(
                    f"BM: {bname}",
                    xy=(bx, by),
                    xytext=boff,
                    textcoords="offset points",
                    fontsize=7.6,
                    color="#4b5563",
                )
        ax_a.scatter([x], [y], color=color, s=92, zorder=4, edgecolors="#ffffff", linewidth=1.1)
        ax_a.annotate(
            label,
            xy=(x, y),
            xytext=off,
            textcoords="offset points",
            fontsize=8.3,
            fontweight="semibold",
            color="#111827",
            arrowprops=dict(arrowstyle="-", color="#d1d5db", lw=0.7) if abs(off[0]) > 14 or abs(off[1]) > 14 else None,
        )

    ax_a.set_xlim(-106, -12)
    ax_a.set_ylim(-0.52, 0.88)
    ax_a.set_xlabel("Max Drawdown (%, shallower to the right →)", fontsize=9.5, fontweight="semibold", color="#374151")
    ax_a.set_ylabel("Sharpe Ratio", fontsize=9.5, fontweight="semibold", color="#374151")
    ax_a.set_title("Panel A: Sharpe vs. Max Drawdown (7 Studies)", fontsize=11, fontweight="bold", color="#111827", pad=10)

    # Panel B: MDD vs CAGR (when Sharpe missing)
    ax_b.axhline(0.0, color="#9ca3af", linestyle="--", linewidth=0.9, zorder=1)
    ax_b.grid(True, linestyle=":", color="#e5e7eb", linewidth=0.8, zorder=0)
    for label, x, y, bx, by, color, v_cat, off, boff, bname in panel_b_items:
        if bx is not None and by is not None:
            ax_b.plot([x, bx], [y, by], color="#9ca3af", linewidth=1.15, alpha=0.85, zorder=2)
            ax_b.scatter([bx], [by], color="#6b7280", marker="s", s=52, zorder=3, edgecolors="#ffffff", linewidth=0.8)
            if boff is not None:
                ax_b.annotate(
                    f"BM: {bname}",
                    xy=(bx, by),
                    xytext=boff,
                    textcoords="offset points",
                    fontsize=7.8,
                    color="#4b5563",
                )
        ax_b.scatter([x], [y], color=color, s=92, zorder=4, edgecolors="#ffffff", linewidth=1.1)
        ax_b.annotate(
            label,
            xy=(x, y),
            xytext=off,
            textcoords="offset points",
            fontsize=8.5,
            fontweight="semibold",
            color="#111827",
        )

    ax_b.set_xlim(-96, 4)
    ax_b.set_ylim(0.0, 15.0)
    ax_b.set_xlabel("Max Drawdown (%, shallower to the right →)", fontsize=9.5, fontweight="semibold", color="#374151")
    ax_b.set_ylabel("CAGR (%)", fontsize=9.5, fontweight="semibold", color="#374151")
    ax_b.set_title("Panel B: CAGR vs. MDD (Sharpe Missing, 2 Studies)", fontsize=11, fontweight="bold", color="#111827", pad=10)

    legend_handles = [
        Line2D([0], [0], marker="o", color="w", label="Adopted / Operating", markerfacecolor="#0f766e", markersize=9),
        Line2D([0], [0], marker="o", color="w", label="Hold / Conditional", markerfacecolor="#d97706", markersize=9),
        Line2D([0], [0], marker="o", color="w", label="Rejected", markerfacecolor="#dc2626", markersize=9),
        Line2D([0], [0], marker="s", color="#9ca3af", label="Paired Benchmark", markerfacecolor="#6b7280", markersize=7, linewidth=1.15),
    ]
    fig.legend(
        handles=legend_handles,
        loc="upper center",
        bbox_to_anchor=(0.5, 0.935),
        ncol=4,
        frameon=False,
        fontsize=9.0,
    )

    fig.suptitle(
        "Backtest Archive Scorecard: Representative Strategies vs. Benchmarks",
        fontsize=13.5,
        fontweight="bold",
        color="#111827",
        y=0.985,
    )
    fig.text(
        0.5,
        0.025,
        NO_CURVE_STUDIES,
        ha="center",
        va="bottom",
        fontsize=8.1,
        color="#4b5563",
        linespacing=1.35,
    )

    plt.subplots_adjust(top=0.81, bottom=0.18, left=0.07, right=0.97)
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT_PATH, dpi=160)
    plt.close(fig)
    print(f"Saved {OUT_PATH} ({len(panel_a_items)} Panel A, {len(panel_b_items)} Panel B points)")


if __name__ == "__main__":
    main()
