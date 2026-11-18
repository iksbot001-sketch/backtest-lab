"""PREREG 7절 H5 — 200일 이격도. 일간 D → 직전 2,520일 롤링 z → 월말 값. 평가는 core.analyze 그대로 + 3개월 NW.
사용: python src/disparity.py [delay]"""
import sys
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).parent)); import core
DELAY = int(sys.argv[1]) if len(sys.argv) > 1 else 0; core.DELAY = DELAY
O = core.O; MK = {'SP500': 'GSPC', 'NASDAQ100': 'NDX', 'SOX': 'SOX', 'KOSPI': 'KS11', 'KOSDAQ': 'KQ11'}

def daily_D(px):
    return px / px.rolling(200, min_periods=200).mean() - 1

def run(mode):
    stats, rows, now = [], [], []
    for mkt, tk in MK.items():
        px = core.yh(tk); D = daily_D(px).dropna()
        if mode == 'rolling':
            zd = (D - D.rolling(2520, min_periods=2000).mean()) / D.rolling(2520, min_periods=2000).std()
        else:                                            # 차트 방식: 표본 전체 고정 평균·σ (사후 정보)
            zd = (D - D.mean()) / D.std()
        zm = core.month_end(zd.dropna()); Dm = core.month_end(D)
        orig = core.rolling_z; core.rolling_z = lambda v, *a, **k: zm.reindex(v.index)
        try: res, zt, st = core.analyze(mkt, px, 'DISP', Dm.reindex(zm.index))
        finally: core.rolling_z = orig
        y3 = np.log1p(res['r3'].values); b3, t3, _ = core.nw_t(y3, res['z'].values, 3)
        r3v = res[res.r3.notna()]; h = r3v.index[len(r3v) // 2]; _, t3b, _ = core.nw_t(np.log1p(res.loc[h:, 'r3'].values), res.loc[h:, 'z'].values, 3)
        st.update(mode=mode, nw_t3=t3, t3_second_half=t3b, D_now=D.iloc[-1], z_daily_now=zd.dropna().iloc[-1],
                  D_mean_full=D.mean(), D_sd_full=D.std(), D_start=str(D.index[0].date()))
        stats.append(st); rows += [dict(r, mode=mode) for r in zt]
        res.to_csv(O / f'panel_{mkt}_DISP_{mode}{"_d%d" % DELAY if DELAY else ""}.csv')
    return stats, rows

S, Z = [], []
for m in ('rolling', 'fixed'):
    s, z = run(m); S += s; Z += z
sfx = f'_d{DELAY}' if DELAY else ''
pd.DataFrame(S).to_csv(O / f'disp_stats{sfx}.csv', index=False); pd.DataFrame(Z).to_csv(O / f'disp_zones{sfx}.csv', index=False)
pd.set_option('display.width', 250); pd.set_option('display.max_columns', 40)
cols = ['market', 'mode', 'start', 'n_months', 'nw_t', 't_second_half', 'nw_t3', 't3_second_half', 'strat_sharpe', 'c60_sharpe', 'strat_cagr', 'c60_cagr', 'bh_cagr',
        'strat_mdd', 'c60_mdd', 'placebo_pct', 'ep_hot', 'ep_cold', 'ep_hot2', 'ep_cold2', 'D_now', 'z_daily_now', 'z_now', 'D_mean_full', 'D_sd_full', 'D_start']
print(pd.DataFrame(S)[cols].round(3).T.to_string())
