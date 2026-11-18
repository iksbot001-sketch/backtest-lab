"""Independent recompute: rolling vs fixed(hindsight) z for 6 valuation series. src/ not read.
Run from run folder: venv/bin/python calc6/recalc.py"""
import json, numpy as np, pandas as pd
from pathlib import Path
R = Path(__file__).resolve().parent.parent
OUT = Path(__file__).resolve().parent / "out"; OUT.mkdir(exist_ok=True)
D = R / "data"

def yh(sym):
    d = json.load(open(D / f"yh_{sym}.json"))["chart"]["result"][0]
    tz = d["meta"]["exchangeTimezoneName"]
    s = pd.Series(d["indicators"]["quote"][0]["close"],
                  index=pd.to_datetime(d["timestamp"], unit="s", utc=True).tz_convert(tz).tz_localize(None).normalize(),
                  dtype=float).dropna()
    return s[~s.index.duplicated(keep="last")].sort_index()
def mfirst(s): return s.groupby(s.index.to_period("M")).first()
def mlast(s): return s.groupby(s.index.to_period("M")).last()

# ---------------- value series (month-end signal) + exec price (first close of month)
krx = pd.read_csv(D / "kospi_per_pbr_krx.csv", parse_dates=["date"]).set_index("date").replace("-", np.nan)
for c in ["per", "pbr", "close"]: krx[c] = pd.to_numeric(krx[c])
kq = pd.read_csv(D / "agy/kosdaq_per_pbr.csv", parse_dates=["date"]).set_index("date")
for c in ["per", "pbr"]: kq[c] = pd.to_numeric(kq[c], errors="coerce")
gs, kqp = yh("GSPC"), yh("KQ11")
ex_ks, ex_kq, ex_gs = mfirst(yh("KS11")), mfirst(kqp), mfirst(gs)   # KOSPI exec = ^KS11 first close (PREREG: ^KS11/KRX)

def kq_series(col):
    s = kq[col].dropna()
    if col == "per": s = s[s.index >= "2010-08-01"]
    return mlast(s)
# S&P PER (Shiller quarter-end E, applied from quarter-end+3m, Yahoo month-end close / E)
sh = pd.read_excel(D / "spdji/shiller_ie_data_2026.xls", sheet_name="Data", header=None, skiprows=8).iloc[:, :4]
sh.columns = ["date", "P", "D", "E"]
sh = sh[pd.to_numeric(sh["date"], errors="coerce").notna()].copy(); sh["date"] = sh["date"].astype(float)
yr = np.floor(sh["date"] + 1e-9).astype(int); mo = np.round((sh["date"] - yr) * 100).astype(int)
sh.index = [pd.Period(f"{y}-{m:02d}", "M") for y, m in zip(yr, mo)]
sh["E"] = pd.to_numeric(sh["E"], errors="coerce")
assert sh.index.is_unique
qe = sh[[p.month in (3, 6, 9, 12) for p in sh.index]]["E"].dropna()
gs_last = mlast(gs)
sE = pd.Series(qe.values, index=[p + 3 for p in qe.index])
E_app = sE.reindex(gs_last.index.union(sE.index)).sort_index().ffill().reindex(gs_last.index)
spx_per = (gs_last / E_app).dropna()
pb = pd.read_csv(D / "spx_pbr_q.csv", parse_dates=["date"])
pbq = pb.groupby(pb.date.dt.to_period("M")).pbr.last()
pbq = pbq.reindex(pd.period_range(pbq.index.min(), "2026-11", freq="M")).ffill().shift(3).dropna()

SERIES = {
    "KOSPI PER": (mlast(krx.per.dropna()), ex_ks),
    "KOSPI PBR": (mlast(krx.pbr.dropna()), ex_ks),
    "SP500 PER": (spx_per, ex_gs),
    "SP500 PBR": (pbq, ex_gs),
    "KOSDAQ PER": (kq_series("per"), ex_kq),
    "KOSDAQ PBR": (kq_series("pbr"), ex_kq),
}

# ---------------- stats helpers
def nw(y, x, L):
    X = np.column_stack([np.ones(len(x)), x]); b = np.linalg.solve(X.T @ X, X.T @ y); u = y - X @ b
    Xu = X * u[:, None]; S = Xu.T @ Xu
    for j in range(1, L + 1):
        G = Xu[j:].T @ Xu[:-j]; S += (1 - j / (L + 1)) * (G + G.T)
    A = np.linalg.inv(X.T @ X); V = A @ S @ A
    return b[1], b[1] / np.sqrt(V[1, 1])
def wmap(z):
    w = np.full(len(z), 0.6); w[z <= -2] = 1.0; w[(z > -2) & (z <= -1)] = 0.8; w[(z >= 1) & (z < 2)] = 0.4; w[z >= 2] = 0.2; return w
def sharpe(r): return r.mean() / r.std(ddof=1) * np.sqrt(12)
def cagr(r): return np.prod(1 + r) ** (12 / len(r)) - 1
def episodes(months, gap=6):
    if len(months) == 0: return 0
    m = np.array([p.ordinal for p in months]); return 1 + int((np.diff(m) > gap).sum())

def zroll(v): return (v - v.rolling(120, min_periods=96).mean()) / v.rolling(120, min_periods=96).std(ddof=1)
def zfix(v, ref=None):
    ref = v if ref is None else ref
    return (v - ref.mean()) / ref.std(ddof=1)
def zexp(v): return (v - v.expanding(96).mean()) / v.expanding(96).std(ddof=1)

def run(z, ex, rets_out=None):
    z = z.dropna()
    lastm = ex.index[-1]
    idx = z.index[z.index < lastm]            # partial last month never a signal month with fill
    zz_all = z.loc[idx]
    e = lambda t, k: ex.get(t + k, np.nan)
    r12 = np.array([e(t, 13) / e(t, 1) - 1 for t in idx]); ok = ~np.isnan(r12)
    y = np.log1p(r12[ok]); zv = zz_all.values[ok]; n = int(ok.sum())
    beta, t = nw(y, zv, 12)
    h = n // 2
    t1 = nw(y[:h], zv[:h], 12)[1]; t2 = nw(y[h:], zv[h:], 12)[1]
    r1 = np.array([e(t, 2) / e(t, 1) - 1 for t in idx]); sok = ~np.isnan(r1)
    w = wmap(zz_all.values[sok]); r1 = r1[sok]
    net = lambda ww: ww * r1 - np.abs(np.diff(ww, prepend=ww[0])) * 0.0005
    rs = net(w); S = sharpe(rs); rc = 0.6 * r1
    N = len(w)
    ps = np.array([sharpe(net(np.roll(w, k))) for k in range(12, N - 12 + 1)])
    pct = float((ps < S).mean()); pct_ex = float((ps[:-1] < S).mean())   # pct_ex: shifts 12..N-13
    mi = idx[ok]
    eh, ec = episodes(list(mi[zv >= 1])), episodes(list(mi[zv <= -1]))
    J1 = (t <= -2.0) and (abs(t) >= 2.73); J2 = eh >= 3 and ec >= 3; J3 = (S > sharpe(rc)) and pct >= 0.9; J4 = t2 < 0
    verdict = "시그널" if (J1 and J2 and J3 and J4) else ("판정 보류" if (J1 and J4 and not J2) else ("참고지표" if (J1 and J4) else "기각"))
    if rets_out is not None:
        pd.DataFrame({"date": [ex.index[0].start_time.date() for _ in []]})  # placeholder (monthly rets saved below)
    return dict(start=str(idx[0]), end=str(idx[-1]), n_months=len(idx), n12=n, nw_beta=beta, nw_t=t, t_first_half=t1, t_second_half=t2,
                half=str(mi[h]), strat_cagr=cagr(rs), strat_sharpe=S, c60_sharpe=sharpe(rc), c60_cagr=cagr(rc), avg_w=w.mean(),
                placebo_pct=pct, placebo_pct_excl_last=pct_ex, n_placebo=len(ps), ep_hot=eh, ep_cold=ec, J1=J1, J2=J2, J3=J3, J4=J4, verdict=verdict,
                z_now=float(z.iloc[-1]), z_now_month=str(z.index[-1])), (idx[sok], rs)

rows = []
for name, (v, ex) in SERIES.items():
    v = v.dropna()
    gaps = int((np.diff([p.ordinal for p in v.index]) > 1).sum())
    zr = zroll(v); r_start = zr.dropna().index[0]
    variants = {
        "rolling": zr,
        "fixed": zfix(v),
        "fixed_cut": zfix(v)[lambda s: s.index >= r_start],                        # full-sample stats, rolling's start month
        "fixed_cutstats": zfix(v[v.index >= r_start]),                             # stats also from cut sample only
        "expanding": zexp(v),                                                      # past-only (no hindsight), same start
    }
    for mode, z in variants.items():
        res, (di, rs) = run(z, ex)
        res.update(combo=name, mode=mode, gaps_in_value_series=gaps, val_first=str(v.index[0]), val_last=str(v.index[-1]),
                   mu_used=float(v.mean()) if mode == "fixed" else np.nan, sd_used=float(v.std(ddof=1)) if mode == "fixed" else np.nan)
        rows.append(res)
        pd.DataFrame({"period": [str(p) for p in di], "ret": rs}).to_csv(OUT / f"ret_{name.replace(' ', '_')}_{mode}.csv", index=False)
df = pd.DataFrame(rows)
cols = ["combo", "mode"] + [c for c in df.columns if c not in ("combo", "mode")]
df[cols].to_csv(OUT / "recalc.csv", index=False)
pd.set_option("display.width", 250, "display.max_columns", 40)
print(df[["combo", "mode", "start", "n12", "nw_t", "t_second_half", "strat_sharpe", "c60_sharpe", "placebo_pct", "ep_hot", "ep_cold", "J1", "J2", "J3", "J4", "verdict", "gaps_in_value_series"]].to_string())
