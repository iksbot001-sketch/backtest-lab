"""PREREG 12절 — z 기준 기간 3년/5년. 사용: python src/windows.py [delay]"""
import sys
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).parent)); import core
import spx_pe_shiller as SPX
DELAY = int(sys.argv[1]) if len(sys.argv) > 1 else 0; core.DELAY = DELAY
O = core.O; CRIT = 3.21

def run(name, px, v, zm, start_cut=None):
    if start_cut is not None: zm = zm[zm.index >= start_cut]
    orig = core.rolling_z; core.rolling_z = lambda s, *a, **k: zm.reindex(s.index)
    try: res, zt, st = core.analyze(name, px, 'w', v.reindex(zm.index))
    finally: core.rolling_z = orig
    t3 = core.nw_t(np.log1p(res.r3.values), res.z.values, 3)[1]
    r3 = res[res.r3.notna()]; h = r3.index[len(r3) // 2]; t3h = core.nw_t(np.log1p(r3.loc[h:, 'r3'].values), r3.loc[h:, 'z'].values, 3)[1]
    r = res[res.r12.notna()]; eh = len(core.episodes(r.z >= 1)); ec = len(core.episodes(r.z <= -1))
    return res, dict(start=str(res.index[0]), n=len(res), t12=st['nw_t'], t12_half=st['t_second_half'], t3=t3, t3_half=t3h,
                     sh=st['strat_sharpe'], c60=st['c60_sharpe'], placebo=st['placebo_pct'], cagr=st['strat_cagr'], c60_cagr=st['c60_cagr'],
                     ep_hot=eh, ep_cold=ec, z_now=st['z_now'])

def verdict(d, keys):
    rank = ['기각', '판정 보류', '참고지표', '시그널']; best = '기각'
    j2 = d['ep_hot'] >= 3 and d['ep_cold'] >= 3; j3 = d['sh'] > d['c60'] and d['placebo'] >= .9
    for k in keys:
        t, th = d[k], d[k + '_half']; j1 = t <= -2 and abs(t) >= CRIT; j4 = t < 0 and th < 0
        v = '시그널' if (j1 and j2 and j3 and j4) else ('참고지표' if (j1 and j4 and j2) else ('판정 보류' if (j1 and j4) else '기각'))
        if rank.index(v) > rank.index(best): best = v
    return best

rows = []
V = core.load_val(); sh = SPX.load_shiller(); g = core.yh('GSPC'); vsp = SPX.per_series(core.month_end(g), sh.E, 3)
VAL = [('KOSPI PER', V['KOSPI']['px'], V['KOSPI']['PER']), ('KOSPI PBR', V['KOSPI']['px'], V['KOSPI']['PBR']), ('S&P500 PER', g, vsp),
       ('S&P500 PBR', V['SP500']['px'], V['SP500']['PBR']), ('KOSDAQ PER', V['KOSDAQ']['px'], V['KOSDAQ']['PER']), ('KOSDAQ PBR', V['KOSDAQ']['px'], V['KOSDAQ']['PBR'])]
for name, px, v in VAL:
    v = v[v > 0]
    z10 = ((v - v.rolling(120, min_periods=96).mean()) / v.rolling(120, min_periods=96).std()).dropna(); s10 = z10.index[0]
    for lab, w, mp in [('10y', 120, 96), ('5y', 60, 48), ('3y', 36, 29)]:
        zm = ((v - v.rolling(w, min_periods=mp).mean()) / v.rolling(w, min_periods=mp).std()).dropna()
        for cut in ([None, s10] if lab != '10y' else [None]):
            _, d = run(name, px, v, zm, cut); d.update(combo=name, group='밸류', window=lab, same_start=cut is not None)
            d['verdict'] = verdict(d, ['t12']) if lab != '10y' else '(기존)'; rows.append(d)
for mkt, tk in [('SP500', 'GSPC'), ('NASDAQ100', 'NDX'), ('SOX', 'SOX'), ('KOSPI', 'KS11'), ('KOSDAQ', 'KQ11')]:
    px = core.yh(tk); D = (px / px.rolling(200, min_periods=200).mean() - 1).dropna(); Dm = core.month_end(D)
    z10 = core.month_end(((D - D.rolling(2520, min_periods=2000).mean()) / D.rolling(2520, min_periods=2000).std()).dropna()); s10 = z10.index[0]
    for lab, w, mp in [('10y', 2520, 2000), ('5y', 1260, 1008), ('3y', 756, 605)]:
        zm = core.month_end(((D - D.rolling(w, min_periods=mp).mean()) / D.rolling(w, min_periods=mp).std()).dropna())
        for cut in ([None, s10] if lab != '10y' else [None]):
            _, d = run(mkt, px, Dm, zm, cut); d.update(combo=f'{mkt} 이격도', group='이격도', window=lab, same_start=cut is not None)
            d['verdict'] = verdict(d, ['t12', 't3']) if lab != '10y' else '(기존)'; rows.append(d)
for mkt, fn, tk in [('SOX', 'fwdpe_img1_sox.csv', 'SOX'), ('NASDAQ100', 'fwdpe_img2.csv', 'NDX'), ('S&P500', 'fwdpe_img3.csv', 'GSPC')]:
    wk = pd.read_csv(core.D / 'agy' / fn, parse_dates=['date']).set_index('date')['fwd_pe']; px = core.yh(tk); vm = core.month_end(wk)
    z5 = core.month_end(((wk - wk.rolling(260, min_periods=156).mean()) / wk.rolling(260, min_periods=156).std()).dropna()); s5 = z5.index[0]
    for lab, w, mp in [('5y', 260, 156), ('3y', 156, 104)]:
        zm = core.month_end(((wk - wk.rolling(w, min_periods=mp).mean()) / wk.rolling(w, min_periods=mp).std()).dropna())
        for cut in ([None, s5] if lab == '3y' else [None]):
            _, d = run(mkt, px, vm, zm, cut); d.update(combo=f'{mkt} 선행PER', group='선행PER', window=lab, same_start=cut is not None)
            d['verdict'] = verdict(d, ['t12', 't3']) if lab == '3y' else '(기존)'; rows.append(d)
R = pd.DataFrame(rows); sfx = f'_d{DELAY}' if DELAY else ''; R.to_csv(O / f'windows_stats{sfx}.csv', index=False)
pd.set_option('display.width', 250)
cols = ['combo', 'window', 'same_start', 'start', 't12', 't12_half', 't3', 'sh', 'c60', 'placebo', 'ep_hot', 'ep_cold', 'verdict']
print(R[cols].round(2).to_string())
