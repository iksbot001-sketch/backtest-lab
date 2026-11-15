"""Synchronize RESULTS.csv standardized columns with metrics/STANDARD_METRICS.csv.

Matches existing catalog rows in RESULTS.csv against metrics/STANDARD_METRICS.csv
on exact (folder, strategy, market, period) equivalence, fills the std_* columns,
and appends rows with blank verdict and note="standardized only" for any
STANDARD_METRICS.csv series that has no matching catalog row.
"""
from __future__ import annotations

import csv
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RESULTS_PATH = ROOT / "RESULTS.csv"
STD_PATH = ROOT / "metrics" / "STANDARD_METRICS.csv"

BASE_COLS = [
    "date",
    "folder",
    "strategy",
    "market",
    "period",
    "metric_cagr",
    "metric_mdd",
    "metric_sharpe",
    "metric_sortino",
    "benchmark",
    "bench_cagr",
    "bench_mdd",
    "bench_sharpe",
    "bench_sortino",
    "verdict",
    "verdict_reason",
    "source_file",
    "note",
]

STD_COLS = [
    "std_cagr",
    "std_mdd",
    "std_sharpe",
    "std_sortino",
    "std_bench_cagr",
    "std_bench_mdd",
    "std_bench_sharpe",
    "std_bench_sortino",
    "std_file",
]

ALL_COLS = BASE_COLS + STD_COLS

# Explicit strategy aliases mapping human-readable catalog names -> STANDARD_METRICS strategy key.
STRATEGY_ALIASES = {
    ("2026-10-28_trend-template-breakout-30y", "book rule (variant b, 30y)"): ("baseline_B", "30y"),
    ("2026-10-28_trend-template-breakout-30y", "book rule (variant b, 20y)"): ("baseline_B", "20y"),
    ("2026-10-28_trend-template-breakout-30y", "book rule (variant b, 10y)"): ("baseline_B", "10y"),
    ("2026-10-28_trend-template-breakout-30y", "book rule (variant b, 5y)"): ("baseline_B", "5y"),
    ("2026-10-28_trend-template-breakout-30y", "improved rule c2 (30y)"): ("improve_C2", "30y"),
    ("2026-10-28_trend-template-breakout-30y", "improved rule c2 (5y)"): ("improve_C2", "5y"),
    ("2026-10-28_trend-template-breakout-30y", "volatility filter s1 (atr<=4.5%, 30y)"): ("improve_S1", "30y"),
    ("2026-10-28_trend-template-breakout-30y", "risk overlay c2e (30y)"): ("improve_C2E", "30y"),
    ("2026-10-28_trend-template-breakout-30y", "risk overlay c2e1 (30y)"): ("improve_C2E1", "30y"),
    ("2026-10-28_trend-template-breakout-30y", "risk overlay on book rule b0e (30y)"): ("improve_B0E", "30y"),
}


def norm_market(mkt: str) -> str:
    m = mkt.strip().lower()
    if m in (
        "kr",
        "kr (kospi)",
        "kospi",
        "kr common stocks 2525",
        "kr common stocks (2525)",
        "kr common stocks",
        "kr kospi non-financial",
    ):
        return "kr"
    if m in (
        "us",
        "us (s&p500)",
        "s&p500",
        "us s&p500 non-financial",
        "us common stocks 528",
        "us common stocks (528)",
        "us equities 462",
        "us equities (462)",
    ):
        return "us"
    return m


def fmt_num(val: str) -> str:
    val = (val or "").strip()
    if not val:
        return ""
    return f"{float(val):.4f}"


def std_period_label(std_row: dict[str, str]) -> str:
    start = std_row.get("start", "").strip()
    end = std_row.get("end", "").strip()
    if start and end:
        return f"{start}~{end}"
    return std_row.get("period", "").strip()


def match_key_for_std(std_row: dict[str, str]) -> tuple[str, str, str, str]:
    folder = std_row["folder"].strip()
    strategy = std_row["strategy"].strip()
    market = norm_market(std_row["market"])
    if folder == "2026-10-28_trend-template-breakout-30y":
        period_key = std_row["period"].strip().lower()
    else:
        period_key = std_period_label(std_row)
    return (folder, strategy, market, period_key)


def match_key_for_catalog(cat_row: dict[str, str]) -> tuple[str, str, str, str] | None:
    folder = cat_row["folder"].strip()
    raw_strat = cat_row["strategy"].strip()
    raw_mkt = norm_market(cat_row["market"])
    raw_period = cat_row["period"].strip()

    alias = STRATEGY_ALIASES.get((folder, raw_strat.lower()))
    if alias:
        strat_key, period_key = alias
        return (folder, strat_key, raw_mkt, period_key)

    # Otherwise extract bare strategy token (e.g. "MIX_TI0.5 (50:50 combo)" -> "MIX_TI0.5")
    # Exclude "second 10y" rows whose period is 2016-11-01~2026-11-06 vs full W20 2006-11-01~2026-11-06
    token = re.split(r"\s+\(", raw_strat, maxsplit=1)[0].strip()
    return (folder, token, raw_mkt, raw_period)


def main() -> None:
    with STD_PATH.open("r", encoding="utf-8") as f:
        std_rows = list(csv.DictReader(f))

    std_by_key: dict[tuple[str, str, str, str], dict[str, str]] = {}
    for sr in std_rows:
        std_by_key[match_key_for_std(sr)] = sr

    with RESULTS_PATH.open("r", encoding="utf-8") as f:
        existing_rows = list(csv.DictReader(f))

    catalog_rows = [
        r for r in existing_rows if (r.get("note") or "").strip() != "standardized only"
    ]

    matched_files: set[str] = set()
    matched_catalog_count = 0
    out_rows: list[dict[str, str]] = []

    for row in catalog_rows:
        out = {c: row.get(c, "") for c in ALL_COLS}
        for c in STD_COLS:
            out[c] = ""
        key = match_key_for_catalog(row)
        sr = std_by_key.get(key) if key else None
        if sr is not None:
            out["std_cagr"] = fmt_num(sr["cagr"])
            out["std_mdd"] = fmt_num(sr["mdd"])
            out["std_sharpe"] = fmt_num(sr["sharpe"])
            out["std_sortino"] = fmt_num(sr["sortino"])
            out["std_bench_cagr"] = fmt_num(sr["bench_cagr"])
            out["std_bench_mdd"] = fmt_num(sr["bench_mdd"])
            out["std_bench_sharpe"] = fmt_num(sr["bench_sharpe"])
            out["std_bench_sortino"] = fmt_num(sr["bench_sortino"])
            out["std_file"] = sr["file"].strip()
            matched_files.add(f"{sr['folder'].strip()}/{sr['file'].strip()}")
            matched_catalog_count += 1
        out_rows.append(out)

    std_only_count = 0
    for sr in std_rows:
        uid = f"{sr['folder'].strip()}/{sr['file'].strip()}"
        if uid in matched_files:
            continue
        folder = sr["folder"].strip()
        date_prefix = folder[:10] if re.match(r"^\d{4}-\d{2}-\d{2}", folder) else ""
        out = {c: "" for c in ALL_COLS}
        out["date"] = date_prefix
        out["folder"] = folder
        out["strategy"] = sr["strategy"].strip()
        out["market"] = sr["market"].strip().upper()
        out["period"] = std_period_label(sr)
        out["benchmark"] = sr["benchmark"].strip()
        out["verdict"] = ""
        out["verdict_reason"] = ""
        out["source_file"] = f"metrics/STANDARD_METRICS.csv ({sr['file'].strip()})"
        out["note"] = "standardized only"
        out["std_cagr"] = fmt_num(sr["cagr"])
        out["std_mdd"] = fmt_num(sr["mdd"])
        out["std_sharpe"] = fmt_num(sr["sharpe"])
        out["std_sortino"] = fmt_num(sr["sortino"])
        out["std_bench_cagr"] = fmt_num(sr["bench_cagr"])
        out["std_bench_mdd"] = fmt_num(sr["bench_mdd"])
        out["std_bench_sharpe"] = fmt_num(sr["bench_sharpe"])
        out["std_bench_sortino"] = fmt_num(sr["bench_sortino"])
        out["std_file"] = sr["file"].strip()
        out_rows.append(out)
        std_only_count += 1

    with RESULTS_PATH.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=ALL_COLS)
        writer.writeheader()
        writer.writerows(out_rows)

    print(
        f"RESULTS.csv updated: {len(out_rows)} total rows "
        f"({len(catalog_rows)} catalog, {matched_catalog_count} catalog rows matched with std_*, "
        f"{std_only_count} standardized-only rows appended)."
    )


if __name__ == "__main__":
    main()
