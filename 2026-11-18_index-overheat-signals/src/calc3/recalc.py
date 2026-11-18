import json
import os
from zoneinfo import ZoneInfo
import numpy as np
import pandas as pd

ROOT = "~/agent-fund/runs/adhoc_20261118_valuation_signals"
DATA_DIR = os.path.join(ROOT, "data")
OUT_DIR = os.path.join(ROOT, "calc3", "out")
os.makedirs(OUT_DIR, exist_ok=True)

ASSETS = [
    ("SOX", "agy/fwdpe_img1_sox.csv", "yh_SOX.json", 14.4),
    ("NASDAQ100(추정)", "agy/fwdpe_img2.csv", "yh_NDX.json", 18.9),
    ("SP500(추정)", "agy/fwdpe_img3.csv", "yh_GSPC.json", 18.1),
]


def load_yahoo_daily(json_path: str) -> pd.Series:
    with open(json_path, "r", encoding="utf-8") as f:
        raw = json.load(f)
    res = raw["chart"]["result"][0]
    ts = res["timestamp"]
    closes = res["indicators"]["quote"][0]["close"]
    ny = ZoneInfo("America/New_York")
    dates = [
        pd.Timestamp(t, unit="s", tz="UTC").tz_convert(ny).strftime("%Y-%m-%d")
        for t in ts
    ]
    s = pd.Series(closes, index=dates, dtype=float).dropna()
    s = s[~s.index.duplicated(keep="last")].sort_index()
    return s


def first_trading_day_close_by_month(daily_close: pd.Series) -> pd.Series:
    df = pd.DataFrame({"date": daily_close.index, "close": daily_close.values})
    df["ym"] = df["date"].str.slice(0, 7)
    first = df.groupby("ym", sort=True)["close"].first()
    return first


def ols_nw(x: np.ndarray, y: np.ndarray, maxlags: int):
    n = len(y)
    X = np.column_stack([np.ones(n), x])
    XtX_inv = np.linalg.inv(X.T @ X)
    beta = XtX_inv @ (X.T @ y)
    e = y - X @ beta

    # Regular OLS
    s2 = float((e @ e) / (n - 2))
    V_ols = s2 * XtX_inv
    t_ols = float(beta[1] / np.sqrt(V_ols[1, 1]))

    # Newey-West HAC (Bartlett kernel)
    Xe = X * e[:, None]
    S = Xe.T @ Xe
    for j in range(1, maxlags + 1):
        w = 1.0 - j / (maxlags + 1.0)
        G = Xe[j:].T @ Xe[:-j]
        S = S + w * (G + G.T)
    V_nw = XtX_inv @ S @ XtX_inv
    t_nw = float(beta[1] / np.sqrt(V_nw[1, 1]))
    return float(beta[1]), t_nw, t_ols


def weight_from_z(z: np.ndarray) -> np.ndarray:
    w = np.full_like(z, 0.6, dtype=float)
    w = np.where(z <= -2.0, 1.0, w)
    w = np.where((z > -2.0) & (z <= -1.0), 0.8, w)
    w = np.where((z >= 1.0) & (z < 2.0), 0.4, w)
    w = np.where(z >= 2.0, 0.2, w)
    return w


def calc_perf(r: np.ndarray):
    n = len(r)
    cum = np.cumprod(np.concatenate([[1.0], 1.0 + r]))
    cagr = float(cum[-1] ** (12.0 / n) - 1.0)
    sharpe = float((np.mean(r) / np.std(r, ddof=1)) * np.sqrt(12.0))
    peak = np.maximum.accumulate(cum)
    mdd = float(np.min(cum / peak - 1.0))
    return cagr, sharpe, mdd


def strat_returns(w: np.ndarray, r1: np.ndarray, cost_bp: float = 5.0, init_w: float = 0.0):
    c = cost_bp / 10000.0
    w_prev = np.concatenate([[init_w], w[:-1]])
    turnover = np.abs(w - w_prev)
    return w * r1 - c * turnover


def count_episodes(cond: np.ndarray, gap: int = 6) -> int:
    ep = 0
    last_idx = None
    for i, flag in enumerate(cond):
        if bool(flag):
            if last_idx is None or (i - last_idx) > gap:
                ep += 1
            last_idx = i
    return ep


def run_one(market: str, fpe_rel: str, yh_rel: str, now_v: float, mode: str):
    fpe_df = pd.read_csv(os.path.join(DATA_DIR, fpe_rel))
    fpe_df = fpe_df.sort_values("date").reset_index(drop=True)

    daily = load_yahoo_daily(os.path.join(DATA_DIR, yh_rel))
    m_px = first_trading_day_close_by_month(daily)

    s = fpe_df["fwd_pe"].astype(float)
    if mode == "rolling5y":
        mu = s.rolling(260, min_periods=156).mean()
        sd = s.rolling(260, min_periods=156).std(ddof=1)
        z_w = (s - mu) / sd
        # photo replacement at last week
        s_photo = s.copy()
        s_photo.iloc[-1] = now_v
        mu_p = s_photo.rolling(260, min_periods=156).mean()
        sd_p = s_photo.rolling(260, min_periods=156).std(ddof=1)
        z_now_photo = float(((s_photo - mu_p) / sd_p).iloc[-1])
    elif mode == "fixed":
        z_w = (s - s.mean()) / s.std(ddof=1)
        s_photo = s.copy()
        s_photo.iloc[-1] = now_v
        z_now_photo = float(((s_photo - s_photo.mean()) / s_photo.std(ddof=1)).iloc[-1])
    else:
        raise ValueError(mode)

    fpe_df["z"] = z_w
    fpe_df["ym"] = fpe_df["date"].str.slice(0, 7)

    # Monthly month-end signal
    m_sig = fpe_df.groupby("ym", sort=True).last()
    now_ym = m_sig.index[-1]  # 2026-11
    v_now = float(m_sig.loc[now_ym, "fwd_pe"])
    z_now = float(m_sig.loc[now_ym, "z"])

    # Completed signal months: exclude partial month 2026-11
    sig_df = m_sig.loc[m_sig.index < now_ym].dropna(subset=["z"]).copy()
    sig_yms = list(sig_df.index)

    # Map monthly execution prices (next month's first trading day close)
    px_yms = list(m_px.index)
    ym_to_pos = {ym: idx for idx, ym in enumerate(px_yms)}

    r1_list, r3_list, r12_list, ret_ym_list = [], [], [], []
    for ym in sig_yms:
        p = ym_to_pos[ym]
        # execution at p + 1
        p_exec = p + 1
        ret_ym_list.append(px_yms[p_exec])
        r1_list.append(m_px.iloc[p_exec + 1] / m_px.iloc[p_exec] - 1.0 if p_exec + 1 < len(m_px) else np.nan)
        r3_list.append(m_px.iloc[p_exec + 3] / m_px.iloc[p_exec] - 1.0 if p_exec + 3 < len(m_px) else np.nan)
        r12_list.append(m_px.iloc[p_exec + 12] / m_px.iloc[p_exec] - 1.0 if p_exec + 12 < len(m_px) else np.nan)

    sig_df["ret_ym"] = ret_ym_list
    sig_df["r1"] = r1_list
    sig_df["r3"] = r3_list
    sig_df["r12"] = r12_list

    # 12m regression sample
    res12 = sig_df.dropna(subset=["r12"]).copy()
    z12 = res12["z"].values
    y12 = np.log(1.0 + res12["r12"].values)
    n12 = len(res12)
    nw_beta, nw_t, _ = ols_nw(z12, y12, 12)

    # Half split on valid 12m signal months (n12 // 2)
    mid12 = n12 // 2
    _, t_first_half, _ = ols_nw(z12[:mid12], y12[:mid12], 12)
    _, t_second_half, _ = ols_nw(z12[mid12:], y12[mid12:], 12)
    half_ym = str(res12.index[mid12])

    # 3m regression sample
    res3 = sig_df.dropna(subset=["r3"]).copy()
    z3 = res3["z"].values
    y3 = np.log(1.0 + res3["r3"].values)
    n3 = len(res3)
    _, nw_t3, _ = ols_nw(z3, y3, 3)
    mid3 = n3 // 2
    _, t3_second_half, _ = ols_nw(z3[mid3:], y3[mid3:], 3)

    # Permutation p-values (circular shift 12 <= k <= n - 12, i.e., range(12, n - 12))
    p12_ts = [ols_nw(np.roll(z12, k), y12, 12)[1] for k in range(12, n12 - 12)]
    perm_p12 = float(np.mean(np.array(p12_ts) <= nw_t))

    p3_ts = [ols_nw(np.roll(z3, k), y3, 3)[1] for k in range(12, n3 - 12)]
    perm_p3 = float(np.mean(np.array(p3_ts) <= nw_t3))

    # Non-overlapping 12m OLS (12 offsets)
    nov_ts = []
    for off in range(12):
        _, _, t_ols = ols_nw(z12[off::12], y12[off::12], 0)
        nov_ts.append(t_ols)
    nov_t_med = float(np.median(nov_ts))
    nov_t_min = float(np.min(nov_ts))
    nov_t_max = float(np.max(nov_ts))

    # Strategy (valid r1 months)
    strat_df = sig_df.dropna(subset=["r1"]).copy()
    n_months = len(strat_df)
    z_s = strat_df["z"].values
    r1_s = strat_df["r1"].values
    w_s = weight_from_z(z_s)
    r_strat = strat_returns(w_s, r1_s, cost_bp=5.0, init_w=0.0)
    strat_cagr, strat_sharpe, strat_mdd = calc_perf(r_strat)
    avg_w = float(np.mean(w_s))

    r_c60 = 0.6 * r1_s
    c60_cagr, c60_sharpe, c60_mdd = calc_perf(r_c60)

    r_bh = r1_s
    bh_cagr, bh_sharpe, bh_mdd = calc_perf(r_bh)

    # Strategy circular-shift placebo
    pl_sharpes = []
    for k in range(12, n_months - 12):
        w_sh = weight_from_z(np.roll(z_s, k))
        r_sh = strat_returns(w_sh, r1_s, cost_bp=5.0, init_w=0.0)
        _, sh_sh, _ = calc_perf(r_sh)
        pl_sharpes.append(sh_sh)
    n_placebo = len(pl_sharpes)
    placebo_pct = float(np.mean(np.array(pl_sharpes) <= strat_sharpe))

    # Episodes: all completed signal months vs 12m-confirmed months
    ep_hot = count_episodes(sig_df["z"].values >= 1.0, gap=6)
    ep_cold = count_episodes(sig_df["z"].values <= -1.0, gap=6)
    ep_hot2 = count_episodes(sig_df["z"].values >= 2.0, gap=6)
    ep_cold2 = count_episodes(sig_df["z"].values <= -2.0, gap=6)

    ep_hot_res = count_episodes(z12 >= 1.0, gap=6)
    ep_cold_res = count_episodes(z12 <= -1.0, gap=6)

    # Independent verdict (J1~J4, Bonferroni |t| >= 2.64)
    # J1: nw_t <= -2.64 (12m or 3m)
    j1_12 = nw_t <= -2.64
    j1_3 = nw_t3 <= -2.64
    j1 = j1_12 or j1_3
    j2 = (ep_hot_res >= 3) and (ep_cold_res >= 3)
    j3 = (strat_sharpe > c60_sharpe) and (placebo_pct >= 0.90)
    j4_12 = (t_second_half < 0) if j1_12 else False
    j4_3 = (t3_second_half < 0) if j1_3 else False
    j4 = (j4_12 or j4_3) if j1 else (t_second_half < 0 and t3_second_half < 0)

    if not j2:
        verdict = "판정 보류(에피소드<3)"
    elif j1 and j2 and j3 and j4:
        verdict = "시그널(잠정)"
    elif j1 and j4:
        verdict = "참고 지표(잠정)"
    else:
        verdict = "기각"

    return {
        "market": market,
        "ind": "FPE",
        "mode": mode,
        "start": str(strat_df["ret_ym"].iloc[0]),
        "end": str(strat_df["ret_ym"].iloc[-1]),
        "n_months": n_months,
        "nw_beta": nw_beta,
        "nw_t": nw_t,
        "n": n12,
        "t_first_half": t_first_half,
        "t_second_half": t_second_half,
        "half": half_ym,
        "strat_cagr": strat_cagr,
        "strat_sharpe": strat_sharpe,
        "strat_mdd": strat_mdd,
        "avg_w": avg_w,
        "c60_cagr": c60_cagr,
        "c60_sharpe": c60_sharpe,
        "c60_mdd": c60_mdd,
        "bh_cagr": bh_cagr,
        "bh_sharpe": bh_sharpe,
        "bh_mdd": bh_mdd,
        "placebo_pct": placebo_pct,
        "n_placebo": n_placebo,
        "ep_hot": ep_hot,
        "ep_cold": ep_cold,
        "ep_hot2": ep_hot2,
        "ep_cold2": ep_cold2,
        "z_now": z_now,
        "v_now": v_now,
        "now": str(now_ym),
        "nw_t3": nw_t3,
        "t3_second_half": t3_second_half,
        "perm_p12": perm_p12,
        "perm_p3": perm_p3,
        "nov_t_med": nov_t_med,
        "nov_t_min": nov_t_min,
        "nov_t_max": nov_t_max,
        "ep_hot_res": ep_hot_res,
        "ep_cold_res": ep_cold_res,
        "n_res": n12,
        "res_start": str(res12.index[0]),
        "res_end": str(res12.index[-1]),
        "now_v": now_v,
        "z_now_photo": z_now_photo,
        "verdict": verdict,
    }


def main():
    rows = []
    for mode in ["rolling5y", "fixed"]:
        for market, fpe_rel, yh_rel, now_v in ASSETS:
            rows.append(run_one(market, fpe_rel, yh_rel, now_v, mode))
    out_df = pd.DataFrame(rows)
    out_path = os.path.join(OUT_DIR, "recalc.csv")
    out_df.to_csv(out_path, index=False)
    print(f"Saved {out_path} ({len(out_df)} rows)")


if __name__ == "__main__":
    main()
