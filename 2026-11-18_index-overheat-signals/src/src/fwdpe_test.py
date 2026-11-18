"""PREREG 8절 — 선행 PER 3건 판정 검증. 주간 → 260주 롤링 z(최소 156) → 월말 → core.analyze. 사용: python src/fwdpe_test.py [delay]"""
import sys
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).parent)); import core
DELAY = int(sys.argv[1]) if len(sys.argv) > 1 else 0; core.DELAY = DELAY
O = core.O; A = core.D / 'agy'
SRC = {'SOX': ('fwdpe_img1_sox.csv', 'SOX', 14.4), 'NASDAQ100(추정)': ('fwdpe_img2.csv', 'NDX', 18.9), 'SP500(추정)': ('fwdpe_img3.csv', 'GSPC', 18.1)}

def perm_t(res, col, lag):
    y = np.log1p(res[col].values); z = res['z'].values; m = ~np.isnan(y); y, z = y[m], z[m]; n = len(y)
    t0 = core.nw_t(y, z, lag)[1]; ts = [core.nw_t(y, np.roll(z, k), lag)[1] for k in range(12, n - 12)]
    return t0, (np.array(ts) <= t0).mean() if ts else np.nan

def nov_t(res):
    r = res[res.r12.notna()]; y = np.log1p(r.r12.values); x = r.z.values; ts = []
    for o in range(12):
        yy, xx = y[o::12], x[o::12]
        if len(yy) < 4: continue
        X = np.column_stack([np.ones(len(xx)), xx]); b = np.linalg.lstsq(X, yy, rcond=None)[0]; u = yy - X @ b
        ts.append(b[1] / np.sqrt((u @ u) / (len(yy) - 2) * np.linalg.inv(X.T @ X)[1, 1]))
    return np.median(ts), min(ts), max(ts)

S = []
for mode in ('rolling5y', 'fixed'):
    for mkt, (fn, tk, nowv) in SRC.items():
        w = pd.read_csv(A / fn, parse_dates=['date']).set_index('date')['fwd_pe'].dropna()
        if mode == 'rolling5y': zw = (w - w.rolling(260, min_periods=156).mean()) / w.rolling(260, min_periods=156).std()
        else: zw = (w - w.mean()) / w.std()
        zm = core.month_end(zw.dropna()); vm = core.month_end(w).reindex(zm.index)
        px = core.yh(tk)
        orig = core.rolling_z; core.rolling_z = lambda v, *a, **k: zm.reindex(v.index)
        try: res, zt, st = core.analyze(mkt, px, 'FPE', vm)
        finally: core.rolling_z = orig
        b3, t3, _ = core.nw_t(np.log1p(res.r3.values), res.z.values, 3)
        r3v = res[res.r3.notna()]; h = r3v.index[len(r3v) // 2]; t3b = core.nw_t(np.log1p(res.loc[h:, 'r3'].values), res.loc[h:, 'z'].values, 3)[1]
        _, p12 = perm_t(res, 'r12', 12); _, p3 = perm_t(res, 'r3', 3); med, mn, mx = nov_t(res)
        r = res[res.r12.notna()]
        hist = w.iloc[-261:-1] if mode == 'rolling5y' else w
        st.update(mode=mode, nw_t3=t3, t3_second_half=t3b, perm_p12=p12, perm_p3=p3, nov_t_med=med, nov_t_min=mn, nov_t_max=mx,
                  ep_hot_res=len(core.episodes(r.z >= 1)), ep_cold_res=len(core.episodes(r.z <= -1)), n_res=len(r),
                  res_start=str(r.index[0]), res_end=str(r.index[-1]), now_v=nowv, z_now_photo=(nowv - hist.mean()) / hist.std())
        S.append(st)
        res.to_csv(O / f'panel_FPE_{tk}_{mode}{"_d%d" % DELAY if DELAY else ""}.csv')
D = pd.DataFrame(S); D.to_csv(O / f'fpe_stats{"_d%d" % DELAY if DELAY else ""}.csv', index=False)
pd.set_option('display.width', 250)
cols = ['market', 'mode', 'start', 'n_months', 'n_res', 'res_start', 'res_end', 'nw_t', 't_second_half', 'nw_t3', 't3_second_half', 'perm_p12', 'perm_p3',
        'nov_t_med', 'nov_t_min', 'nov_t_max', 'strat_sharpe', 'c60_sharpe', 'strat_cagr', 'c60_cagr', 'bh_cagr', 'placebo_pct', 'ep_hot_res', 'ep_cold_res', 'z_now', 'z_now_photo']
print(D[cols].round(3).T.to_string())
