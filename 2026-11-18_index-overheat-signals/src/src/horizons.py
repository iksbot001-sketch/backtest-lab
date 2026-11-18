"""PREREG 11절 — 이후 수익률 수평선 1/3/6/9(+12)개월. 기존 패널의 z를 그대로 쓰고 수익률만 다시 계산."""
import sys
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).parent)); import core
O = core.O; H = (1, 3, 6, 9, 12); CRIT = 3.32
COMBOS = [('KOSPI PER', 'panel_KOSPI_PER.csv', 'KS11'), ('KOSPI PBR', 'panel_KOSPI_PBR.csv', 'KS11'),
          ('S&P500 PER', 'panel_SP500_PER_SH_lag3.csv', 'GSPC'), ('S&P500 PBR', 'panel_SP500_PBR.csv', 'GSPC'),
          ('KOSDAQ PER', 'panel_KOSDAQ_PER.csv', 'KQ11'), ('KOSDAQ PBR', 'panel_KOSDAQ_PBR.csv', 'KQ11'),
          ('S&P500 이격도', 'panel_SP500_DISP_rolling.csv', 'GSPC'), ('NASDAQ100 이격도', 'panel_NASDAQ100_DISP_rolling.csv', 'NDX'),
          ('SOX 이격도', 'panel_SOX_DISP_rolling.csv', 'SOX'), ('KOSPI 이격도', 'panel_KOSPI_DISP_rolling.csv', 'KS11'),
          ('KOSDAQ 이격도', 'panel_KOSDAQ_DISP_rolling.csv', 'KQ11'),
          ('SOX 선행PER', 'panel_FPE_SOX_rolling5y.csv', 'SOX'), ('NASDAQ100 선행PER', 'panel_FPE_NDX_rolling5y.csv', 'NDX'), ('S&P500 선행PER', 'panel_FPE_GSPC_rolling5y.csv', 'GSPC')]
J3 = {}
s = pd.read_csv(O / 'stats.csv').set_index(['market', 'ind'])
for (m, i), k in [(('KOSPI', 'PER'), 'KOSPI PER'), (('KOSPI', 'PBR'), 'KOSPI PBR'), (('SP500', 'PBR'), 'S&P500 PBR'), (('KOSDAQ', 'PER'), 'KOSDAQ PER'), (('KOSDAQ', 'PBR'), 'KOSDAQ PBR')]:
    r = s.loc[(m, i)]; J3[k] = (r.strat_sharpe, r.c60_sharpe, r.placebo_pct)
sh = pd.read_csv(O / 'spx_pe_shiller_stats.csv'); r = sh[(sh.variant == 'lag3') & (sh.delay == 0)].iloc[0]; J3['S&P500 PER'] = (r.strat_sharpe, r.c60_sharpe, r.placebo_pct)
ds = pd.read_csv(O / 'disp_stats.csv'); ds = ds[ds['mode'] == 'rolling'].set_index('market')
for m in ['SP500', 'NASDAQ100', 'SOX', 'KOSPI', 'KOSDAQ']:
    r = ds.loc[m]; J3[{'SP500': 'S&P500'}.get(m, m) + ' 이격도'] = (r.strat_sharpe, r.c60_sharpe, r.placebo_pct)
fs = pd.read_csv(O / 'fpe_stats.csv'); fs = fs[fs['mode'] == 'rolling5y'].set_index('market')
for m, k in [('SOX', 'SOX 선행PER'), ('NASDAQ100(추정)', 'NASDAQ100 선행PER'), ('SP500(추정)', 'S&P500 선행PER')]:
    r = fs.loc[m]; J3[k] = (r.strat_sharpe, r.c60_sharpe, r.placebo_pct)

def nov_t(y, x, h):
    ts = []
    for o in range(h):
        yy, xx = y[o::h], x[o::h]
        if len(yy) < 8: continue
        X = np.column_stack([np.ones(len(xx)), xx]); b = np.linalg.lstsq(X, yy, rcond=None)[0]; u = yy - X @ b
        ts.append(b[1] / np.sqrt((u @ u) / (len(yy) - 2) * np.linalg.inv(X.T @ X)[1, 1]))
    return float(np.median(ts)) if ts else np.nan

rows, zrows = [], []
for name, pf, tk in COMBOS:
    p = pd.read_csv(O / pf, index_col=0); p.index = pd.PeriodIndex(p.index, freq='M'); z = p['z']
    ent = core.first_td_close(core.yh(tk)); e1 = ent.shift(-1)
    for h in H:
        r = (ent.shift(-1 - h) / e1 - 1).reindex(z.index); d = pd.DataFrame({'z': z, 'r': r}).dropna()
        y = np.log1p(d.r.values); x = d.z.values
        b, t, n = core.nw_t(y, x, max(h, 1))
        half = d.index[len(d) // 2]; dh = d.loc[half:]; t2 = core.nw_t(np.log1p(dh.r.values), dh.z.values, max(h, 1))[1]
        eh = len(core.episodes(d.z >= 1)); ec = len(core.episodes(d.z <= -1))
        sS, sC, pl = J3[name]
        j1 = t <= -2 and abs(t) >= CRIT; j2 = eh >= 3 and ec >= 3; j3 = sS > sC and pl >= .9; j4 = t < 0 and t2 < 0
        v = '시그널' if all([j1, j2, j3, j4]) else ('참고지표' if j1 and j4 and j2 else ('판정 보류' if j1 and j4 else '기각'))
        rows.append(dict(combo=name, h=h, n=n, start=str(d.index[0]), end=str(d.index[-1]), beta=b, nw_t=t, t_second_half=t2, nov_t=nov_t(y, x, h),
                         ep_hot=eh, ep_cold=ec, j1=j1, j2=j2, j3=j3, j4=j4, verdict=v if h != 12 else '(비교용)'))
        for zn in ['Z<=-2', '-2<Z<=-1', 'neutral', '1<=Z<2', 'Z>=2']:
            m = d.z.map(core.zone) == zn
            zrows.append(dict(combo=name, h=h, zone=zn, months=int(m.sum()), mean=d.r[m].mean() if m.any() else np.nan, up=(d.r[m] > 0).mean() if m.any() else np.nan, all_mean=d.r.mean()))
R = pd.DataFrame(rows); R.to_csv(O / 'horizons_stats.csv', index=False); pd.DataFrame(zrows).to_csv(O / 'horizons_zones.csv', index=False)
P = R.pivot(index='combo', columns='h', values='nw_t').reindex([c[0] for c in COMBOS]).round(2)
print('NW t by horizon (CRIT ±3.32 for h=1,3,6,9)'); print(P.to_string())
print(R[R.h != 12].groupby('verdict').size().to_string())
print(R[(R.h != 12) & (R.verdict != '기각')][['combo', 'h', 'nw_t', 't_second_half', 'nov_t', 'ep_hot', 'ep_cold', 'verdict']].round(2).to_string())
