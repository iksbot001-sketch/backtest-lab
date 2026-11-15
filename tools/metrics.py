"""Standardized performance metrics calculator for backtest daily return series.

All metrics operate on a daily simple return series ``r`` indexed by date,
using a uniform 252 trading-days-per-year convention and zero risk-free rate
(``rf = 0``) so that strategies across the archive are directly comparable.

Formulas
--------
Given ``N = len(r)`` daily simple returns ``r_1, ..., r_N`` sorted by date:

- ``start``: first date in ``r`` (``YYYY-MM-DD``).
- ``end``: last date in ``r`` (``YYYY-MM-DD``).
- ``n_days``: ``N``, number of daily return observations.
- ``years``: ``N / 252.0`` (trading-day convention).
- ``total_return``: ``prod_{t=1}^N (1 + r_t) - 1``.
- ``cagr``: ``(1 + total_return) ** (252.0 / N) - 1``.
- ``mdd``: maximum drawdown (negative float). Let cumulative equity starting
  at ``1.0`` before day 1 be ``E_0 = 1.0``, ``E_t = prod_{i=1}^t (1 + r_i)``
  for ``t = 1..N``. Then ``mdd = min_{t=0..N} (E_t / max_{0<=s<=t} E_s - 1)``.
- ``ann_vol``: ``std(r, ddof=1) * sqrt(252)``.
- ``sharpe``: ``(mean(r) / std(r, ddof=1)) * sqrt(252)`` with ``rf = 0``.
- ``sortino``: ``(mean(r) / downside_dev) * sqrt(252)`` with ``rf = 0``, where
  ``downside_dev = sqrt(mean(min(r, 0)^2))`` computed over ALL ``N`` days.
- ``calmar``: ``cagr / abs(mdd)`` when ``mdd < 0``, else ``nan``.
- ``worst_year``: calendar year ``y`` with the lowest compounded return.
- ``worst_year_return``: ``min_y (prod_{t in year y} (1 + r_t) - 1)``.
- ``beta``: ``cov(r, b, ddof=1) / var(b, ddof=1)`` computed on the intersection
  of dates between ``r`` and ``benchmark`` (``nan`` if no benchmark is given,
  fewer than 2 overlapping days exist, or ``var(b) == 0``).
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd

TRADING_DAYS_PER_YEAR = 252.0


def _prepare_series(s: pd.Series, name: str = "returns") -> pd.Series:
    """Validate, clean, and sort a date-indexed daily simple return series."""
    if not isinstance(s, pd.Series):
        raise TypeError(f"{name} must be a pandas Series")
    clean = s.replace([np.inf, -np.inf], np.nan).dropna().astype(float)
    if clean.empty:
        raise ValueError(f"{name} is empty after dropping NaNs/infs")
    idx = pd.to_datetime(clean.index)
    clean = pd.Series(clean.to_numpy(dtype=float), index=idx, name=clean.name)
    if clean.index.has_duplicates:
        raise ValueError(f"{name} index contains duplicate dates")
    return clean.sort_index()


def compute_metrics(
    returns: pd.Series,
    benchmark: pd.Series | None = None,
) -> dict[str, Any]:
    """Compute standardized performance metrics on a daily simple return Series.

    Parameters
    ----------
    returns : pd.Series
        Daily simple returns indexed by date (DatetimeIndex or parseable strings).
    benchmark : pd.Series or None, optional
        Optional benchmark daily simple returns indexed by date.

    Returns
    -------
    dict[str, Any]
        Dictionary with keys: start, end, years, cagr, total_return, mdd,
        ann_vol, sharpe, sortino, calmar, worst_year, worst_year_return,
        beta, n_days.
    """
    r = _prepare_series(returns, "returns")
    vals = r.to_numpy(dtype=float)
    n_days = int(len(vals))
    years = float(n_days / TRADING_DAYS_PER_YEAR)

    start = r.index[0].strftime("%Y-%m-%d")
    end = r.index[-1].strftime("%Y-%m-%d")

    wealth_end = float(np.prod(1.0 + vals))
    total_return = wealth_end - 1.0
    if wealth_end > 0.0 and n_days > 0:
        cagr = float(wealth_end ** (TRADING_DAYS_PER_YEAR / n_days) - 1.0)
    elif wealth_end <= 0.0:
        cagr = -1.0
    else:
        cagr = float("nan")

    # Prepend initial wealth 1.0 so day-1 losses are captured in drawdown.
    eq = np.concatenate(([1.0], np.cumprod(1.0 + vals)))
    running_peak = np.maximum.accumulate(eq)
    drawdowns = eq / running_peak - 1.0
    mdd = float(np.min(drawdowns))

    mean_r = float(np.mean(vals))
    if n_days >= 2:
        std_r = float(np.std(vals, ddof=1))
        ann_vol = float(std_r * math.sqrt(TRADING_DAYS_PER_YEAR))
        sharpe = (
            float((mean_r / std_r) * math.sqrt(TRADING_DAYS_PER_YEAR))
            if std_r > 0.0
            else float("nan")
        )
    else:
        ann_vol = float("nan")
        sharpe = float("nan")

    downside_dev = float(np.sqrt(np.mean(np.minimum(vals, 0.0) ** 2)))
    sortino = (
        float((mean_r / downside_dev) * math.sqrt(TRADING_DAYS_PER_YEAR))
        if downside_dev > 0.0
        else float("nan")
    )

    calmar = float(cagr / abs(mdd)) if (mdd < 0.0 and not math.isnan(cagr)) else float("nan")

    yearly_returns = (1.0 + r).groupby(r.index.year).prod() - 1.0
    worst_year = int(yearly_returns.idxmin())
    worst_year_return = float(yearly_returns.min())

    beta = float("nan")
    if benchmark is not None:
        b = _prepare_series(benchmark, "benchmark")
        common = r.index.intersection(b.index)
        if len(common) >= 2:
            ra = r.loc[common].to_numpy(dtype=float)
            ba = b.loc[common].to_numpy(dtype=float)
            var_b = float(np.var(ba, ddof=1))
            if var_b > 0.0:
                cov_rb = float(np.cov(ra, ba, ddof=1)[0, 1])
                beta = float(cov_rb / var_b)

    return {
        "start": start,
        "end": end,
        "years": years,
        "cagr": cagr,
        "total_return": total_return,
        "mdd": mdd,
        "ann_vol": ann_vol,
        "sharpe": sharpe,
        "sortino": sortino,
        "calmar": calmar,
        "worst_year": worst_year,
        "worst_year_return": worst_year_return,
        "beta": beta,
        "n_days": n_days,
    }


def _self_test() -> None:
    """Verify every metric on a synthetic 2-year (504-day) series with known values."""
    # Year 1 (252 days): alternating +0.02 and -0.01 (126 pairs)
    # Year 2 (252 days): alternating +0.01 and -0.02 (126 pairs)
    dates = pd.bdate_range("2024-01-01", periods=504)
    y1 = np.tile([0.02, -0.01], 126)
    y2 = np.tile([0.01, -0.02], 126)
    r = pd.Series(np.concatenate([y1, y2]), index=dates)
    bench = 0.5 * r  # exact linear scaling -> beta must be 2.0

    res = compute_metrics(r, benchmark=bench)

    # Analytical expectations:
    # Each Y1 pair compounds to (1.02)*(0.99) = 1.0098 -> Y1 = 1.0098^126 - 1
    # Each Y2 pair compounds to (1.01)*(0.98) = 0.9898 -> Y2 = 0.9898^126 - 1
    exp_y1 = (1.0098 ** 126) - 1.0
    exp_y2 = (0.9898 ** 126) - 1.0
    exp_total = (1.0 + exp_y1) * (1.0 + exp_y2) - 1.0
    exp_cagr = (1.0 + exp_total) ** (252.0 / 504.0) - 1.0
    # Mean return: (126*0.02 + 126*(-0.01) + 126*0.01 + 126*(-0.02)) / 504 = 0.0
    exp_mean = 0.0
    # Sample variance: all 504 values have mean 0; 252 values of +-0.02 and 252 values of +-0.01
    sum_sq = 252 * (0.02 ** 2) + 252 * (0.01 ** 2)
    exp_std = math.sqrt(sum_sq / 503.0)
    exp_ann_vol = exp_std * math.sqrt(252.0)
    exp_dd = math.sqrt((126 * (0.01 ** 2) + 126 * (0.02 ** 2)) / 504.0)
    # Peak occurs at day 251 (125 pairs + 0.02 gain = 1.0098^125 * 1.02);
    # trough occurs at day 504 (1.0098^126 * 0.9898^126 = 1.0098^125 * 1.02 * 0.99 * 0.9898^126).
    exp_mdd = 0.99 * (0.9898 ** 126) - 1.0

    # Wait: check calendar year boundary for 504 business days starting 2024-01-01
    # Use exact calendar-year grouping on the actual dates for worst_year check:
    yr_actual = (1.0 + r).groupby(r.index.year).prod() - 1.0
    exp_worst_yr = int(yr_actual.idxmin())
    exp_worst_yr_ret = float(yr_actual.min())

    assert res["start"] == dates[0].strftime("%Y-%m-%d")
    assert res["end"] == dates[-1].strftime("%Y-%m-%d")
    assert res["n_days"] == 504
    assert math.isclose(res["years"], 2.0, rel_tol=1e-12)
    assert math.isclose(res["total_return"], exp_total, rel_tol=1e-12, abs_tol=1e-12)
    assert math.isclose(res["cagr"], exp_cagr, rel_tol=1e-12, abs_tol=1e-12)
    assert math.isclose(res["mdd"], exp_mdd, rel_tol=1e-12, abs_tol=1e-12)
    assert math.isclose(res["ann_vol"], exp_ann_vol, rel_tol=1e-12, abs_tol=1e-12)
    assert math.isclose(res["sharpe"], exp_mean, abs_tol=1e-12)
    assert math.isclose(res["sortino"], exp_mean / exp_dd * math.sqrt(252.0), abs_tol=1e-12)
    assert math.isclose(res["calmar"], exp_cagr / abs(exp_mdd), rel_tol=1e-12, abs_tol=1e-12)
    assert res["worst_year"] == exp_worst_yr
    assert math.isclose(res["worst_year_return"], exp_worst_yr_ret, rel_tol=1e-12, abs_tol=1e-12)
    assert math.isclose(res["beta"], 2.0, rel_tol=1e-12, abs_tol=1e-12)

    # Second test: strictly positive/negative drift to check non-zero Sharpe & Sortino
    r2 = pd.Series([0.01, -0.02, 0.03, -0.01], index=pd.bdate_range("2025-01-01", periods=4))
    res2 = compute_metrics(r2)
    mean2 = 0.01 / 4.0
    std2 = math.sqrt(((0.01 - mean2) ** 2 + (-0.02 - mean2) ** 2 + (0.03 - mean2) ** 2 + (-0.01 - mean2) ** 2) / 3.0)
    dd2 = math.sqrt((0.02 ** 2 + 0.01 ** 2) / 4.0)
    assert math.isclose(res2["sharpe"], (mean2 / std2) * math.sqrt(252.0), rel_tol=1e-12)
    assert math.isclose(res2["sortino"], (mean2 / dd2) * math.sqrt(252.0), rel_tol=1e-12)
    assert math.isnan(res2["beta"])

    print("metrics.py self-test PASSED:")
    for k, v in res.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    _self_test()
