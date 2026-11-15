"""Extract standardized daily return series across all archive folders and compute metrics.

Reads every dated folder (``2026-*``) in the archive, extracts daily simple return
or NAV/equity series into ``<folder>/returns/<strategy>__<market>__<period>.csv``
with columns ``date,ret``, writes ``<folder>/returns/MANIFEST.csv``, and produces
``metrics/STANDARD_METRICS.csv`` using ``tools/metrics.py``.
"""

from __future__ import annotations

import csv
import math
import re
from pathlib import Path
from typing import Any

import pandas as pd

from metrics import compute_metrics

ARCHIVE_ROOT = Path(__file__).resolve().parent.parent
METRICS_DIR = ARCHIVE_ROOT / "metrics"
STANDARD_METRICS_PATH = METRICS_DIR / "STANDARD_METRICS.csv"

SKIP_REASONS: dict[str, str] = {
    "2026-10-17_kosdaq150-volatility-harvest": (
        "Summary/episode tables and payoff CSVs only (dip_ladder*, payoff_monthly.csv); no daily return/NAV CSV"
    ),
    "2026-10-21_kospi-crash-dip-buying-36y": (
        "Summary comparison tables and undated 251-step event-window paths.json only; no calendar-dated daily return series"
    ),
    "2026-10-22_us-golden-cross-voo-qqq": (
        "Trade list (pe_gc_trades.csv), summary tables (out/*.csv), and raw OHLCV text files only; no strategy daily return CSV"
    ),
    "2026-10-23_rebalancing-front-running": (
        "Aggregated JSON robustness/metric summaries only; no daily return/NAV CSV"
    ),
    "2026-10-24_ai-backtest-reliability": (
        "Synthetic validation JSONs and IS/OOS Sharpe scatter (e2_scatter.csv) only; no daily return/NAV CSV"
    ),
    "2026-10-26_turtle-trading": (
        "Trade episodes, rolling 5y summaries, and sensitivity tables only; no daily return/NAV CSV"
    ),
    "2026-11-04_valuation-drawdown-study": (
        "Drawdown event study and valuation bucket/yearly EPS tables only; no daily return/NAV CSV"
    ),
    "2026-11-06_crash-hold-or-add-decision": (
        "Crash event study tables (deep_dd.csv, events_list.csv, events_summary.csv) only; no continuous daily return CSV"
    ),
    "2026-10-28_trend-template-breakout-30y": "",  # covered
    "2026-11-08_earnings-gamma-chesley-quant": (
        "Summary JSONs (gamma.json, spec.json) and markdown reports only; no CSV files"
    ),
    "2026-11-14_valuation-v2-calibration": (
        "Annual quintile/calibration tables (T1-T6b, T_*_byyear.csv) only; no daily return CSV"
    ),
    "2026-11-15_trend-x-valuation-combo": "",  # covered
    "2026-11-15_valuation-v2-ex-ante-test": (
        "Cross-sectional IC/quintile spread and annual firm-year panel (panel.csv) only; no daily return CSV"
    ),
}

METRIC_COLS = [
    "start",
    "end",
    "years",
    "cagr",
    "total_return",
    "mdd",
    "ann_vol",
    "sharpe",
    "sortino",
    "calmar",
    "worst_year",
    "worst_year_return",
    "beta",
    "n_days",
]


def _write_return_csv(path: Path, series: pd.Series) -> None:
    """Write a date-indexed daily simple return Series to ``date,ret`` CSV."""
    df = pd.DataFrame(
        {
            "date": series.index.strftime("%Y-%m-%d"),
            "ret": series.to_numpy(dtype=float),
        }
    )
    df.to_csv(path, index=False)


def _extract_2026_10_28(folder: Path) -> tuple[list[dict[str, str]], dict[str, pd.Series]]:
    """Extract all 76 baseline and improve NAV curves from 2026-10-28 as daily returns."""
    returns_dir = folder / "returns"
    returns_dir.mkdir(exist_ok=True)
    out_root = folder / "src" / "out"

    manifest_rows: list[dict[str, str]] = []
    series_map: dict[str, pd.Series] = {}

    daily_files = sorted(out_root.glob("**/daily.csv"))
    for csv_path in daily_files:
        rel_source = csv_path.relative_to(folder).as_posix()
        parent_name = csv_path.parent.name
        m = re.fullmatch(r"(\d+y)_(.+)", parent_name)
        if not m:
            raise ValueError(f"Unexpected daily.csv directory name: {csv_path}")
        period, code = m.group(1), m.group(2)

        is_improve = "improve" in csv_path.parts
        strategy = f"improve_{code}" if is_improve else f"baseline_{code}"
        market = "kr"
        out_name = f"{strategy}__{market}__{period}.csv"

        df = pd.read_csv(csv_path, usecols=["date", "nav"])
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date").set_index("date")
        ret = df["nav"].astype(float).pct_change().dropna()
        ret.name = out_name

        _write_return_csv(returns_dir / out_name, ret)
        series_map[out_name] = ret
        manifest_rows.append(
            {
                "file": out_name,
                "strategy": strategy,
                "market": market,
                "period": period,
                "source_file": rel_source,
                "conversion": "from_equity",
                "benchmark_file": "",
            }
        )

    manifest_rows.sort(key=lambda r: (r["strategy"], r["market"], r["period"]))
    _write_manifest(returns_dir / "MANIFEST.csv", manifest_rows)
    return manifest_rows, series_map


def _extract_2026_11_15(folder: Path) -> tuple[list[dict[str, str]], dict[str, pd.Series]]:
    """Extract deduplicated daily simple returns and BENCH_BH benchmarks from 2026-11-15."""
    returns_dir = folder / "returns"
    returns_dir.mkdir(exist_ok=True)
    out_root = folder / "src" / "out"

    manifest_rows: list[dict[str, str]] = []
    series_map: dict[str, pd.Series] = {}

    # Ordered sources to deduplicate overlapping columns (T_returns -> C_returns -> F_returns).
    # V_returns_{kr,us}.csv and chk/ replicas are intentionally skipped (verified exact duplicates).
    for market in ("kr", "us"):
        seen_cols: set[str] = set()
        bench_filename = ""

        sources = [
            (f"T_returns_{market}.csv", out_root / f"T_returns_{market}.csv"),
            (f"C_returns_{market}.csv", out_root / f"C_returns_{market}.csv"),
            (f"F_returns_{market}.csv", out_root / f"F_returns_{market}.csv"),
        ]

        for source_name, csv_path in sources:
            if not csv_path.exists():
                raise FileNotFoundError(f"Expected return file missing: {csv_path}")
            df = pd.read_csv(csv_path)
            df["date"] = pd.to_datetime(df["date"])
            df = df.sort_values("date").set_index("date")
            rel_source = csv_path.relative_to(folder).as_posix()

            for col in df.columns:
                if col in seen_cols:
                    continue
                seen_cols.add(col)

                s = df[col].dropna().astype(float)
                if s.empty:
                    raise ValueError(f"Empty series for {col} in {csv_path}")

                period = f"{s.index[0].strftime('%Y%m%d')}-{s.index[-1].strftime('%Y%m%d')}"
                is_bench = col == "BH"
                strategy = "BENCH_BH" if is_bench else col
                out_name = f"{strategy}__{market}__{period}.csv"

                if is_bench:
                    bench_filename = out_name

                s.name = out_name
                _write_return_csv(returns_dir / out_name, s)
                series_map[out_name] = s
                manifest_rows.append(
                    {
                        "file": out_name,
                        "strategy": strategy,
                        "market": market,
                        "period": period,
                        "source_file": rel_source,
                        "conversion": "none",
                        "benchmark_file": "" if is_bench else bench_filename,
                    }
                )

    manifest_rows.sort(key=lambda r: (r["market"], not r["strategy"].startswith("BENCH_"), r["strategy"]))
    _write_manifest(returns_dir / "MANIFEST.csv", manifest_rows)
    return manifest_rows, series_map


def _write_manifest(path: Path, rows: list[dict[str, str]]) -> None:
    """Write per-folder returns/MANIFEST.csv."""
    fieldnames = [
        "file",
        "strategy",
        "market",
        "period",
        "source_file",
        "conversion",
        "benchmark_file",
    ]
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    METRICS_DIR.mkdir(exist_ok=True)
    dated_folders = sorted(p for p in ARCHIVE_ROOT.iterdir() if p.is_dir() and p.name.startswith("2026-"))

    extractors = {
        "2026-10-28_trend-template-breakout-30y": _extract_2026_10_28,
        "2026-11-15_trend-x-valuation-combo": _extract_2026_11_15,
    }

    standard_rows: list[dict[str, Any]] = []
    covered_folders: list[str] = []
    skipped_folders: list[tuple[str, str]] = []

    for folder in dated_folders:
        name = folder.name
        extractor = extractors.get(name)
        if extractor is None:
            reason = SKIP_REASONS.get(name, "No daily return/equity series found")
            skipped_folders.append((name, reason))
            continue

        covered_folders.append(name)
        manifest_rows, series_map = extractor(folder)

        for entry in manifest_rows:
            fname = entry["file"]
            s = series_map[fname]
            bench_fname = entry["benchmark_file"]

            if bench_fname:
                bench_full = series_map[bench_fname]
                common_idx = s.index.intersection(bench_full.index)
                if len(common_idx) != len(s):
                    raise ValueError(
                        f"{name}/{fname}: benchmark {bench_fname} missing dates "
                        f"({len(common_idx)}/{len(s)})"
                    )
                bench_paired = bench_full.loc[s.index]
                m = compute_metrics(s, benchmark=bench_paired)
                bm = compute_metrics(bench_paired)
                bench_cagr = bm["cagr"]
                bench_mdd = bm["mdd"]
                bench_sharpe = bm["sharpe"]
                bench_sortino = bm["sortino"]
            else:
                m = compute_metrics(s)
                bench_cagr = math.nan
                bench_mdd = math.nan
                bench_sharpe = math.nan
                bench_sortino = math.nan

            row: dict[str, Any] = {
                "folder": name,
                "file": fname,
                "strategy": entry["strategy"],
                "market": entry["market"],
                "period": entry["period"],
            }
            for k in METRIC_COLS:
                row[k] = m[k]
            row["benchmark"] = bench_fname
            row["bench_cagr"] = bench_cagr
            row["bench_mdd"] = bench_mdd
            row["bench_sharpe"] = bench_sharpe
            row["bench_sortino"] = bench_sortino
            standard_rows.append(row)

    out_fields = (
        ["folder", "file", "strategy", "market", "period"]
        + METRIC_COLS
        + ["benchmark", "bench_cagr", "bench_mdd", "bench_sharpe", "bench_sortino"]
    )
    out_df = pd.DataFrame(standard_rows, columns=out_fields)
    out_df.to_csv(STANDARD_METRICS_PATH, index=False)

    print(f"Total dated folders: {len(dated_folders)}")
    print(f"Covered folders ({len(covered_folders)}): {', '.join(covered_folders)}")
    print(f"Skipped folders ({len(skipped_folders)}):")
    for fname, reason in skipped_folders:
        print(f"  - {fname}: {reason}")
    print(f"Total standardized series extracted: {len(out_df)}")
    for fld, cnt in out_df.groupby("folder").size().items():
        print(f"  - {fld}: {cnt}")


if __name__ == "__main__":
    main()
