import json
import os
import numpy as np
import pandas as pd

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(BASE, "data")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
os.makedirs(OUT, exist_ok=True)


def load_yh(fn):
    with open(os.path.join(DATA, fn)) as f:
        d = json.load(f)["chart"]["result"][0]
    tz = d["meta"].get("exchangeTimezoneName", "UTC")
    ts = d["timestamp"]
    close = d["indicators"]["quote"][0]["close"]
    dt = pd.to_datetime(ts, unit="s", utc=True).tz_convert(tz).strftime("%Y-%m-%d")
    s = pd.Series(close, index=pd.to_datetime(dt), dtype=float).dropna()
    s = s[~s.index.duplicated(keep="last")].sort_index()
    return s


def first_trading_close_monthly(daily_px):
    # Monthly period -> first trading day's close in that month
    p = daily_px.index.to_period("M")
    m = daily_px.groupby(p).first()
    m.index = m.index.astype(str)
    return m


def last_trading_close_monthly(daily_px):
    p = daily_px.index.to_period("M")
    m = daily_px.groupby(p).last()
    m.index = m.index.astype(str)
    return m


def newey_west_t(y, x, lag):
    y = np.asarray(y, dtype=float)
    x = np.asarray(x, dtype=float)
    n = len(y)
    if n < 5 or np.std(x) == 0:
        return np.nan
    X = np.column_stack([np.ones(n), x])
    beta, _, _, _ = np.linalg.lstsq(X, y, rcond=None)
    u = y - X @ beta
    XtX_inv = np.linalg.inv(X.T @ X)
    # S = sum_{l=-lag}^{lag} w_l * Gamma_l
    Xu = X * u[:, None]
    S = Xu.T @ Xu
    for l in range(1, lag + 1):
        if l >= n:
            break
        w = 1.0 - l / (lag + 1.0)
        G = Xu[l:].T @ Xu[:-l]
        S = S + w * (G + G.T)
    cov = XtX_inv @ S @ XtX_inv
    se = np.sqrt(cov[1, 1])
    if se <= 0 or np.isnan(se):
        return np.nan
    return float(beta[1] / se)


def weight_from_z(z):
    z = np.asarray(z, dtype=float)
    w = np.full(len(z), 0.6)
    w[z <= -2.0] = 1.0
    w[(z > -2.0) & (z <= -1.0)] = 0.8
    w[(z >= 1.0) & (z < 2.0)] = 0.4
    w[z >= 2.0] = 0.2
    return w


def eval_strategy(z_vals, exec_rets, cost_bps=5.0):
    # z_vals aligned with exec_rets (month m signal -> month m+1..m+2 return)
    w = weight_from_z(z_vals)
    cost = cost_bps / 10000.0
    dw = np.abs(np.diff(w, prepend=w[0]))
    # check if initial cost is applied or not; we'll test prepend=0.0 vs prepend=w[0]
    r = w * exec_rets - cost * dw
    sh = float(np.mean(r) / np.std(r, ddof=1) * np.sqrt(12)) if np.std(r, ddof=1) > 0 else np.nan
    cagr = float(np.prod(1.0 + r) ** (12.0 / len(r)) - 1.0)
    return sh, cagr, r


def count_episodes(z_vals, months, thresh, direction):
    # direction: 'hot' (z >= thresh) or 'cold' (z <= thresh)
    # 6-month cooldown: within 6 months of previous episode start (diff <= 6? or < 6?)
    ep = 0
    last_idx = -999
    for i, z in enumerate(z_vals):
        cond = (z >= thresh) if direction == "hot" else (z <= thresh)
        if cond:
            if i - last_idx > 6:
                ep += 1
                last_idx = i
            else:
                last_idx = i  # wait: is cooldown from episode start or last active month? Let's test both!
    return ep


def build_series():
    yh_gspc = load_yh("yh_GSPC.json")
    yh_ks11 = load_yh("yh_KS11.json")
    yh_kq11 = load_yh("yh_KQ11.json")
    yh_ndx = load_yh("yh_NDX.json")
    yh_sox = load_yh("yh_SOX.json")

    exec_map = {
        "SP500": first_trading_close_monthly(yh_gspc),
        "NASDAQ100": first_trading_close_monthly(yh_ndx),
        "SOX": first_trading_close_monthly(yh_sox),
        "KOSPI": first_trading_close_monthly(yh_ks11),
        "KOSDAQ": first_trading_close_monthly(yh_kq11),
    }

    series = {}

    # 1. KOSPI PER, PBR
    krx_ks = pd.read_csv(os.path.join(DATA, "kospi_per_pbr_krx.csv"))
    krx_ks["date"] = pd.to_datetime(krx_ks["date"])
    krx_ks = krx_ks.sort_values("date")
    krx_ks["ym"] = krx_ks["date"].dt.to_period("M").astype(str)
    for col, name in [("per", "KOSPI PER"), ("pbr", "KOSPI PBR")]:
        s = pd.to_numeric(krx_ks[col], errors="coerce")
        df_tmp = pd.DataFrame({"ym": krx_ks["ym"], "val": s}).dropna()
        m_val = df_tmp.groupby("ym")["val"].last()
        series[name] = ("밸류", m_val, exec_map["KOSPI"])

    # 2. KOSDAQ PER, PBR
    krx_kq = pd.read_csv(os.path.join(DATA, "agy", "kosdaq_per_pbr.csv"))
    krx_kq["ym"] = pd.to_datetime(krx_kq["date"]).dt.to_period("M").astype(str)
    for col, name in [("per", "KOSDAQ PER"), ("pbr", "KOSDAQ PBR")]:
        s = pd.to_numeric(krx_kq[col], errors="coerce")
        df_tmp = pd.DataFrame({"ym": krx_kq["ym"], "val": s}).dropna()
        if col == "per":
            df_tmp = df_tmp[df_tmp["ym"] >= "2010-08"]
        m_val = df_tmp.groupby("ym")["val"].last()
        series[name] = ("밸류", m_val, exec_map["KOSDAQ"])

    # 3. S&P500 PER (Shiller E quarterly + 3m lag, Yahoo ^GSPC month-end close / E)
    xl = pd.ExcelFile(os.path.join(DATA, "spdji", "shiller_ie_data_2026.xls"))
    df_sh = xl.parse("Data", skiprows=7)
    df_sh = df_sh[df_sh["Date"].notna()].copy()
    df_sh["ym"] = df_sh["Date"].apply(lambda v: f"{v:.2f}".replace(".", "-"))
    df_sh["E"] = pd.to_numeric(df_sh["E"], errors="coerce")
    q_sh = df_sh[df_sh["ym"].str.endswith(("-03", "-06", "-09", "-12")) & df_sh["E"].notna()].copy()
    q_sh["eff_ym"] = (pd.PeriodIndex(q_sh["ym"], freq="M") + 3).astype(str)
    gspc_m = last_trading_close_monthly(yh_gspc)
    all_ym = sorted(set(gspc_m.index) | set(q_sh["eff_ym"]))
    e_full = q_sh.set_index("eff_ym")["E"].reindex(all_ym).ffill()
    pe_sh = (gspc_m / e_full.reindex(gspc_m.index)).dropna()
    series["S&P500 PER"] = ("밸류", pe_sh, exec_map["SP500"])

    # 4. S&P500 PBR (quarterly + 3m lag)
    spx_pbr = pd.read_csv(os.path.join(DATA, "spx_pbr_q.csv"))
    spx_pbr["ym"] = pd.to_datetime(spx_pbr["date"]).dt.to_period("M").astype(str)
    spx_pbr["eff_ym"] = (pd.PeriodIndex(spx_pbr["ym"], freq="M") + 3).astype(str)
    all_ym_pbr = sorted(set(gspc_m.index) | set(spx_pbr["eff_ym"]))
    pbr_full = spx_pbr.set_index("eff_ym")["pbr"].reindex(all_ym_pbr).ffill()
    pbr_m = pbr_full.reindex(gspc_m.index).dropna()
    series["S&P500 PBR"] = ("밸류", pbr_m, exec_map["SP500"])

    # 5. Disparity (daily close / SMA200 - 1)
    disp_specs = [
        ("SP500 이격도", yh_gspc, exec_map["SP500"]),
        ("NASDAQ100 이격도", yh_ndx, exec_map["NASDAQ100"]),
        ("SOX 이격도", yh_sox, exec_map["SOX"]),
        ("KOSPI 이격도", yh_ks11, exec_map["KOSPI"]),
        ("KOSDAQ 이격도", yh_kq11, exec_map["KOSDAQ"]),
    ]
    for name, px, ex in disp_specs:
        sma200 = px.rolling(200, min_periods=200).mean()
        disp = (px / sma200 - 1.0).dropna()
        series[name] = ("이격도", disp, ex)

    # 6. Forward PER (weekly -> monthly)
    fwd_specs = [
        ("SOX 선행PER", "fwdpe_img1_sox.csv", exec_map["SOX"]),
        ("NASDAQ100 선행PER", "fwdpe_img2.csv", exec_map["NASDAQ100"]),
        ("S&P500 선행PER", "fwdpe_img3.csv", exec_map["SP500"]),
    ]
    for name, fn, ex in fwd_specs:
        df_f = pd.read_csv(os.path.join(DATA, "agy", fn))
        df_f["date"] = pd.to_datetime(df_f["date"])
        df_f = df_f.sort_values("date")
        s = df_f.set_index("date")["fwd_pe"]
        series[name] = ("선행PER", s, ex)

    return series


def compute_z_monthly(group, raw_s, win_name):
    if group == "밸류":
        cfg = {"10y": (120, 96), "5y": (60, 48), "3y": (36, 29)}[win_name]
        w, mp = cfg
        z = (raw_s - raw_s.rolling(w, min_periods=mp).mean()) / raw_s.rolling(w, min_periods=mp).std(ddof=1)
        return z.dropna()
    elif group == "이격도":
        cfg = {"10y": (2520, 2000), "5y": (1260, 1008), "3y": (756, 605)}[win_name]
        w, mp = cfg
        z_d = (raw_s - raw_s.rolling(w, min_periods=mp).mean()) / raw_s.rolling(w, min_periods=mp).std(ddof=1)
        z_d = z_d.dropna()
        p = z_d.index.to_period("M")
        z_m = z_d.groupby(p).last()
        z_m.index = z_m.index.astype(str)
        return z_m
    elif group == "선행PER":
        cfg = {"5y": (260, 156), "3y": (156, 104)}[win_name]
        w, mp = cfg
        z_w = (raw_s - raw_s.rolling(w, min_periods=mp).mean()) / raw_s.rolling(w, min_periods=mp).std(ddof=1)
        z_w = z_w.dropna()
        p = z_w.index.to_period("M")
        z_m = z_w.groupby(p).last()
        z_m.index = z_m.index.astype(str)
        return z_m


def evaluate_one(z_m, exec_m, start_override=None):
    if start_override is not None:
        z_m = z_m[z_m.index >= start_override]
    months = z_m.index.tolist()
    z_vals = z_m.values
    z_now = float(z_vals[-1])
    start = months[0]
    n = len(months)

    # Align forward returns using PeriodIndex arithmetic
    p_idx = pd.PeriodIndex(months, freq="M")
    exec_p = exec_m.copy()
    exec_p.index = pd.PeriodIndex(exec_p.index, freq="M")

    p_m1 = p_idx + 1
    p_m2 = p_idx + 2
    p_m4 = p_idx + 4
    p_m13 = p_idx + 13

    px1 = exec_p.reindex(p_m1).values
    px2 = exec_p.reindex(p_m2).values
    px4 = exec_p.reindex(p_m4).values
    px13 = exec_p.reindex(p_m13).values

    r12 = np.log(px13 / px1)
    r3 = np.log(px4 / px1)
    r1_simple = px2 / px1 - 1.0

    # 12m NW t and half
    m12 = ~np.isnan(r12)
    t12 = newey_west_t(r12[m12], z_vals[m12], 12)
    n12 = int(np.sum(m12))
    t12_half = newey_west_t(r12[m12][n12 // 2:], z_vals[m12][n12 // 2:], 12)

    # 3m NW t and half
    m3 = ~np.isnan(r3)
    t3 = newey_west_t(r3[m3], z_vals[m3], 3)
    n3 = int(np.sum(m3))
    t3_half = newey_west_t(r3[m3][n3 // 2:], z_vals[m3][n3 // 2:], 3)

    # Strategy
    ms = ~np.isnan(r1_simple)
    z_s = z_vals[ms]
    r_s = r1_simple[ms]
    sh, cagr, _ = eval_strategy(z_s, r_s, 5.0)
    # c60
    w60 = np.full(len(r_s), 0.6)
    dw60 = np.abs(np.diff(w60, prepend=w60[0]))
    r60 = w60 * r_s - 0.0005 * dw60
    c60 = float(np.mean(r60) / np.std(r60, ddof=1) * np.sqrt(12))
    c60_cagr = float(np.prod(1.0 + r60) ** (12.0 / len(r60)) - 1.0)

    # Placebo: circular shifts >= 12
    ns = len(z_s)
    shifts = list(range(12, ns - 12)) if ns - 24 <= 1000 else np.linspace(12, ns - 13, 1000, dtype=int)
    pl_shs = []
    for k in shifts:
        z_sh = np.roll(z_s, int(k))
        sh_k, _, _ = eval_strategy(z_sh, r_s, 5.0)
        pl_shs.append(sh_k)
    placebo = float(np.mean(np.array(pl_shs) < sh)) if len(pl_shs) > 0 else np.nan

    # Episodes on resolved r12
    z_res = z_vals[m12]
    ep_hot = count_episodes(z_res, months, 1.0, "hot")
    ep_cold = count_episodes(z_res, months, -1.0, "cold")

    return {
        "start": start, "n": n, "t12": t12, "t12_half": t12_half,
        "t3": t3, "t3_half": t3_half, "sh": sh, "c60": c60,
        "placebo": placebo, "cagr": cagr, "c60_cagr": c60_cagr,
        "ep_hot": ep_hot, "ep_cold": ep_cold, "z_now": z_now,
    }


def judge(group, row):
    # PREREG 4, 7, 8, 12
    # J1: t <= -2.0 and |t| >= 3.21 (for disparity and fwdpe, either 12m or 3m)
    if group == "밸류":
        j1 = (row["t12"] <= -2.0) and (abs(row["t12"]) >= 3.21)
        j4 = row["t12_half"] < 0
    else:
        j1_12 = (row["t12"] <= -2.0) and (abs(row["t12"]) >= 3.21)
        j1_3 = (row["t3"] <= -2.0) and (abs(row["t3"]) >= 3.21)
        j1 = j1_12 or j1_3
        j4 = ((not j1_12) or (row["t12_half"] < 0)) and ((not j1_3) or (row["t3_half"] < 0))
        if not j1:
            j4 = (row["t12_half"] < 0) or (row["t3_half"] < 0)
    j2 = (row["ep_hot"] >= 3) and (row["ep_cold"] >= 3)
    j3 = (row["sh"] > row["c60"]) and (row["placebo"] >= 0.90)
    if j1 and j2 and j3 and j4:
        return "시그널"
    if j1 and j4:
        if not j2:
            return "판정보류"
        return "참고지표"
    return "기각"


def main():
    series = build_series()
    ref = pd.read_csv(os.path.join(BASE, "out", "windows_stats.csv"))
    rows = []
    for combo, (group, raw_s, ex) in series.items():
        base_win = "5y" if group == "선행PER" else "10y"
        z_base = compute_z_monthly(group, raw_s, base_win)
        base_start = z_base.index[0]

        wins = ["5y", "3y"] if group == "선행PER" else ["10y", "5y", "3y"]
        for w in wins:
            z_m = compute_z_monthly(group, raw_s, w)
            res = evaluate_one(z_m, ex, None)
            res.update({"combo": combo, "group": group, "window": w, "same_start": False})
            res["verdict"] = "(기존)" if w == base_win else judge(group, res)
            rows.append(res)

            if w != base_win:
                res_s = evaluate_one(z_m, ex, base_start)
                res_s.update({"combo": combo, "group": group, "window": w, "same_start": True})
                res_s["verdict"] = judge(group, res_s)
                rows.append(res_s)

    df_out = pd.DataFrame(rows)
    cols = ["start", "n", "t12", "t12_half", "t3", "t3_half", "sh", "c60", "placebo",
            "cagr", "c60_cagr", "ep_hot", "ep_cold", "z_now", "combo", "group", "window", "same_start", "verdict"]
    df_out = df_out[cols]
    df_out.to_csv(os.path.join(OUT, "recalc.csv"), index=False)

    # Compare with ref
    merged = ref.merge(df_out, on=["combo", "group", "window", "same_start"], suffixes=("_ref", "_new"))
    print(f"Matched rows: {len(merged)} / {len(ref)}")
    num_cols = ["n", "t12", "t12_half", "t3", "t3_half", "sh", "c60", "placebo", "cagr", "c60_cagr", "ep_hot", "ep_cold", "z_now"]
    for c in num_cols:
        diff = (merged[c + "_new"] - merged[c + "_ref"]).abs()
        max_d = diff.max()
        idx = diff.idxmax()
        r_max = merged.loc[idx]
        print(f"  {c:10s}: max |diff| = {max_d:.6e}  (at {r_max['combo']} {r_max['window']} same={r_max['same_start']}: ref={r_max[c+'_ref']}, new={r_max[c+'_new']})")
    for c in ["start", "verdict"]:
        mism = merged[merged[c + "_new"] != merged[c + "_ref"]]
        print(f"  {c:10s}: mismatches = {len(mism)}")
        if len(mism) > 0:
            print(mism[["combo", "window", "same_start", c + "_ref", c + "_new"]].to_string(index=False))


if __name__ == "__main__":
    main()
