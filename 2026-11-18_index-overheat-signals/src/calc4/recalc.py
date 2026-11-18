import json
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
OUT = Path(__file__).resolve().parent / "out"
OUT.mkdir(parents=True, exist_ok=True)


def load_yahoo(sym: str) -> pd.Series:
    with open(DATA / f"yh_{sym}.json", "r") as f:
        d = json.load(f)["chart"]["result"][0]
    ts = d["timestamp"]
    tz = d["meta"]["exchangeTimezoneName"]
    cl = d["indicators"]["quote"][0]["close"]
    dates = pd.to_datetime(ts, unit="s", utc=True).tz_convert(tz).strftime("%Y-%m-%d")
    s = pd.Series(cl, index=dates, dtype="float64").dropna()
    s = s[~s.index.duplicated(keep="last")].sort_index()
    return s


def rolling_z(s: pd.Series, win: int = 2520, min_p: int = 2000) -> pd.Series:
    m = s.rolling(win, min_periods=min_p).mean()
    sd = s.rolling(win, min_periods=min_p).std(ddof=1)
    return (s - m) / sd


def build_indicators() -> dict[str, tuple[pd.Series, pd.Series]]:
    res = {}
    for name, sym in [
        ("SP500_DISP", "GSPC"),
        ("NASDAQ100_DISP", "NDX"),
        ("SOX_DISP", "SOX"),
        ("KOSPI_DISP", "KS11"),
        ("KOSDAQ_DISP", "KQ11"),
    ]:
        px = load_yahoo(sym)
        sma200 = px.rolling(200, min_periods=200).mean()
        disp = px / sma200 - 1.0
        z = rolling_z(disp)
        res[name] = (px, z)

    # KOSPI_PBR
    ks_px = load_yahoo("KS11")
    krx = pd.read_csv(DATA / "kospi_per_pbr_krx.csv")
    krx["pbr"] = pd.to_numeric(krx["pbr"], errors="coerce")
    krx = krx.dropna(subset=["pbr"])
    krx = krx[krx["pbr"] > 0].set_index("date")["pbr"].sort_index()
    common_ks = ks_px.index.intersection(krx.index)
    ks_px_aligned = ks_px.loc[common_ks]
    ks_pbr_aligned = krx.loc[common_ks]
    res["KOSPI_PBR"] = (ks_px_aligned, rolling_z(ks_pbr_aligned))

    # KOSDAQ_PBR
    kq_px = load_yahoo("KQ11")
    kq_m = pd.read_csv(DATA / "agy" / "kosdaq_per_pbr.csv")
    kq_m["pbr"] = pd.to_numeric(kq_m["pbr"], errors="coerce")
    kq_m["close"] = pd.to_numeric(kq_m["close"], errors="coerce")
    kq_m = kq_m.dropna(subset=["pbr", "close"])
    kq_m = kq_m[(kq_m["pbr"] > 0) & (kq_m["close"] > 0)].sort_values("date")
    kq_m["ratio"] = kq_m["pbr"] / kq_m["close"]

    df_kq = pd.DataFrame({"date": kq_px.index, "dt": pd.to_datetime(kq_px.index), "px": kq_px.values})
    kq_m["dt"] = pd.to_datetime(kq_m["date"])
    df_kq = pd.merge_asof(
        df_kq.sort_values("dt"),
        kq_m[["dt", "ratio"]].sort_values("dt"),
        on="dt",
        direction="backward",
        allow_exact_matches=False,
    ).dropna(subset=["ratio"])
    kq_px_aligned = pd.Series(df_kq["px"].values, index=df_kq["date"].values)
    kq_pbr_daily = pd.Series(
        (df_kq["px"] * df_kq["ratio"]).values, index=df_kq["date"].values
    )
    res["KOSDAQ_PBR"] = (kq_px_aligned, rolling_z(kq_pbr_daily))

    return res


def check_pbr_approx():
    ks_px = load_yahoo("KS11")
    krx = pd.read_csv(DATA / "kospi_per_pbr_krx.csv")
    krx["pbr"] = pd.to_numeric(krx["pbr"], errors="coerce")
    krx["close"] = pd.to_numeric(krx["close"], errors="coerce")
    krx = krx.dropna(subset=["pbr", "close"])
    krx = krx[(krx["pbr"] > 0) & (krx["close"] > 0)].sort_values("date")

    krx["ym"] = krx["date"].str.slice(0, 7)
    krx_m = krx.groupby("ym", as_index=False).last()
    krx_m["ratio"] = krx_m["pbr"] / krx_m["close"]

    df = pd.DataFrame({"date": krx["date"].values, "dt": pd.to_datetime(krx["date"].values), "actual_pbr": krx["pbr"].values})
    df = df.merge(
        pd.DataFrame({"date": ks_px.index, "yh_close": ks_px.values}),
        on="date",
        how="inner",
    )
    krx_m["dt"] = pd.to_datetime(krx_m["date"])
    df = pd.merge_asof(
        df.sort_values("dt"),
        krx_m[["dt", "ratio"]].sort_values("dt"),
        on="dt",
        direction="backward",
        allow_exact_matches=False,
    ).dropna(subset=["ratio"])
    df["approx_pbr"] = df["yh_close"] * df["ratio"]

    rel_err = np.abs(df["approx_pbr"] - df["actual_pbr"]) / df["actual_pbr"]
    z_act = rolling_z(pd.Series(df["actual_pbr"].values, index=df["date"].values))
    z_app = rolling_z(pd.Series(df["approx_pbr"].values, index=df["date"].values))
    valid = z_act.notna() & z_app.notna()
    out = pd.DataFrame(
        [
            {"metric": "n", "val": float(len(df))},
            {"metric": "mape", "val": float(rel_err.mean())},
            {"metric": "p95", "val": float(np.quantile(rel_err, 0.95))},
            {"metric": "z_corr", "val": float(z_act[valid].corr(z_app[valid]))},
            {"metric": "z_mae", "val": float(np.abs(z_act[valid] - z_app[valid]).mean())},
        ]
    )
    return out


def compute_events(indicators: dict[str, tuple[pd.Series, pd.Series]]) -> pd.DataFrame:
    rng = np.random.default_rng(42)
    rows = []
    for name, (px, z) in indicators.items():
        dates = px.index.values
        p_arr = px.values
        z_arr = z.values
        n_total = len(p_arr)

        for lvl in [-1, 1, -2, 2]:
            side = "buy" if lvl < 0 else "sell"
            # Find crossing events
            events = []
            last_t = None
            for t in range(1, n_total):
                if np.isnan(z_arr[t - 1]) or np.isnan(z_arr[t]):
                    continue
                if side == "buy":
                    hit_cross = (z_arr[t - 1] > lvl) and (z_arr[t] <= lvl)
                else:
                    hit_cross = (z_arr[t - 1] < lvl) and (z_arr[t] >= lvl)
                if hit_cross:
                    if last_t is None or (t - last_t) > 60:
                        events.append(t)
                        last_t = t

            for h in [5, 20, 60]:
                primary = (lvl in (-1, 1)) and (h == 20)
                # Valid pool of all dates with non-nan z and resolved h
                valid_mask = (~np.isnan(z_arr)) & (np.arange(n_total) + 1 + h < n_total)
                valid_idx = np.where(valid_mask)[0]
                all_rets = np.log(p_arr[valid_idx + 1 + h] / p_arr[valid_idx + 1])
                base = float(all_rets.mean())

                ev_idx = np.array([t for t in events if t + 1 + h < n_total], dtype=int)
                n_ev = len(ev_idx)
                ev_rets = np.log(p_arr[ev_idx + 1 + h] / p_arr[ev_idx + 1])
                ev_mean = float(ev_rets.mean())
                excess = ev_mean - base
                hit_rate = float((ev_rets > 0).mean())

                # 10,000 random samples without replacement
                n_sim = 10000
                null_means = np.empty(n_sim, dtype=float)
                pool_len = len(all_rets)
                for s in range(n_sim):
                    sample = rng.choice(all_rets, size=n_ev, replace=False)
                    null_means[s] = sample.mean()
                if side == "buy":
                    p_val = float((null_means >= ev_mean).mean())
                else:
                    p_val = float((null_means <= ev_mean).mean())

                half_ev = ev_rets[n_ev // 2 :]
                excess_2nd = float(half_ev.mean() - base) if len(half_ev) > 0 else np.nan

                rows.append(
                    {
                        "name": name,
                        "lvl": lvl,
                        "side": side,
                        "h": h,
                        "primary": primary,
                        "n": n_ev,
                        "mean": ev_mean,
                        "base": base,
                        "excess": excess,
                        "hit": hit_rate,
                        "p": p_val,
                        "excess_2nd": excess_2nd,
                        "first": dates[ev_idx[0]] if n_ev > 0 else "",
                        "last": dates[ev_idx[-1]] if n_ev > 0 else "",
                    }
                )
    return pd.DataFrame(rows)


def z_to_weight(z: np.ndarray) -> np.ndarray:
    w = np.full_like(z, 0.6, dtype=float)
    w[z <= -2.0] = 1.0
    w[(z > -2.0) & (z <= -1.0)] = 0.8
    w[(z >= 1.0) & (z < 2.0)] = 0.4
    w[z >= 2.0] = 0.2
    return w


def calc_perf(r: np.ndarray) -> tuple[float, float]:
    n = len(r)
    sharpe = float(r.mean() / r.std(ddof=1) * np.sqrt(252))
    cagr = float(np.prod(1.0 + r) ** (252.0 / n) - 1.0)
    return sharpe, cagr


def compute_strategy(indicators: dict[str, tuple[pd.Series, pd.Series]]) -> pd.DataFrame:
    rows = []
    for name, (px, z) in indicators.items():
        valid = z.notna()
        first_valid_pos = int(np.argmax(valid.values))
        # w_t decided at t (from first_valid_pos to len-3) -> traded at t+1 -> applied to r_idx[t+2]
        dates = px.index.values
        p_arr = px.values
        z_arr = z.values

        # Signal indices t: first_valid_pos .. len(p_arr) - 3
        sig_idx = np.arange(first_valid_pos, len(p_arr) - 2)
        w = z_to_weight(z_arr[sig_idx])
        r_idx = p_arr[sig_idx + 2] / p_arr[sig_idx + 1] - 1.0

        dw = np.abs(np.diff(w, prepend=w[0]))
        # Wait: let's check if initial trade cost is 0 or |w[0]|; prepend=w[0] gives 0 for day 0
        r_5 = w * r_idx - dw * 0.0005
        r_10 = w * r_idx - dw * 0.0010

        sh_5, cagr_5 = calc_perf(r_5)
        sh_10, _ = calc_perf(r_10)

        avg_w = float(w.mean())
        r_const = avg_w * r_idx
        sh_const, cagr_const = calc_perf(r_const)
        sh_bh, _ = calc_perf(r_idx)

        n_days = len(r_idx)
        years = n_days / 252.0
        turnover = float(dw.sum() / years)
        cost_yr = turnover * 0.0005

        # Placebo circular shifts
        ks = range(252, n_days - 252 + 1, 21)
        sh_pl_5 = []
        sh_pl_10 = []
        for k in ks:
            wk = np.roll(w, k)
            dwk = np.abs(np.diff(wk, prepend=wk[0]))
            rk5 = wk * r_idx - dwk * 0.0005
            rk10 = wk * r_idx - dwk * 0.0010
            sh_pl_5.append(float(rk5.mean() / rk5.std(ddof=1) * np.sqrt(252)))
            sh_pl_10.append(float(rk10.mean() / rk10.std(ddof=1) * np.sqrt(252)))

        plac_5 = float(np.mean(np.array(sh_pl_5) < sh_5))
        plac_10 = float(np.mean(np.array(sh_pl_10) < sh_10))

        rows.append(
            {
                "sharpe": sh_5,
                "const_sharpe": sh_const,
                "bh_sharpe": sh_bh,
                "cagr": cagr_5,
                "const_cagr": cagr_const,
                "avg_w": avg_w,
                "placebo": plac_5,
                "turnover": turnover,
                "cost_yr": cost_yr,
                "start": dates[sig_idx[0]],
                "end": dates[sig_idx[-1]],
                "name": name,
                "sharpe_10bp": sh_10,
                "placebo_10bp": plac_10,
                "z_now": float(z_arr[-1]),
                "z_date": dates[-1],
            }
        )
    return pd.DataFrame(rows)


if __name__ == "__main__":
    inds = build_indicators()
    pbr_chk = check_pbr_approx()
    pbr_chk.to_csv(OUT / "recalc_pbr_approx_check.csv", index=False)
    ev = compute_events(inds)
    ev.to_csv(OUT / "recalc_events.csv", index=False)
    st = compute_strategy(inds)
    st.to_csv(OUT / "recalc_strategy.csv", index=False)
    print("Done.")
