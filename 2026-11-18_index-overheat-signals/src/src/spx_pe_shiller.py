"""PREREG 10절 — 쉴러(S&P 원자료) 분기 말 TTM 이익으로 S&P500 PER 재검증. 사용: python src/spx_pe_shiller.py"""
import sys
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).parent)); import core
O = core.O

def load_shiller():
    x = pd.read_excel(core.D / 'spdji' / 'shiller_ie_data_2026.xls', sheet_name='Data', header=None, engine='xlrd')
    d = x.iloc[8:, :4]; d.columns = ['date', 'P', 'D', 'E']
    d = d[pd.to_numeric(d.date, errors='coerce').notna()].copy()
    ds = d.date.map(lambda v: f'{float(v):.2f}')
    d.index = pd.PeriodIndex([f'{s[:4]}-{s[5:7]}' for s in ds], freq='M')
    return d[['P', 'E']].apply(pd.to_numeric, errors='coerce')

def eps_available(E, lag):
    q = E[E.index.month.isin([3, 6, 9, 12])].dropna()      # 실제 4분기 합계만
    q.index = q.index + lag                                 # 분기 말 + lag개월 뒤부터 사용
    return q

def per_series(px_m, E, lag):
    ea = eps_available(E, lag)
    idx = pd.period_range(min(ea.index.min(), px_m.index.min()), px_m.index.max(), freq='M')
    e = ea.reindex(idx).ffill().reindex(px_m.index)
    return (px_m / e).dropna()

if __name__ == '__main__':
    sh = load_shiller(); gspc = core.yh('GSPC'); pxm = core.month_end(gspc)
    S, Z = [], []
    for lag, tag in [(3, 'lag3'), (2, 'lag2'), (4, 'lag4')]:
        v = per_series(pxm, sh.E, lag); v = v[v > 0]
        for d in (0, 1) if lag == 3 else (0,):
            core.DELAY = d
            res, zt, st = core.analyze('SP500', gspc, f'PER_SH_{tag}', v)
            st.update(variant=tag, delay=d); S.append(st)
            if d == 0: Z += zt; res.to_csv(O / f'panel_SP500_PER_SH_{tag}.csv')
    core.DELAY = 0
    # 보조: 1900~ 장기 (쉴러 월평균 가격으로 수익률·PER)
    P = sh.P.dropna(); P = P[P.index >= pd.Period('1900-01', 'M')]
    pxd = pd.Series(P.values, index=P.index.to_timestamp('M'))         # 월 1점 → analyze가 '첫 거래일' = 그 값
    v = per_series(P, sh.E, 3); v = v[v > 0]
    res, zt, st = core.analyze('SP500', pxd, 'PER_SH_long', v); st.update(variant='long1900_shillerP', delay=0); S.append(st)
    D = pd.DataFrame(S); D.to_csv(O / 'spx_pe_shiller_stats.csv', index=False); pd.DataFrame(Z).to_csv(O / 'spx_pe_shiller_zones.csv', index=False)
    # multpl 대비 비교
    m = pd.read_csv(O / 'panel_SP500_PER.csv', index_col=0); a = pd.read_csv(O / 'panel_SP500_PER_SH_lag3.csv', index_col=0)
    j = pd.concat([m.v.rename('multpl'), a.v.rename('shiller')], axis=1).dropna()
    print('multpl vs shiller PER corr', round(j.corr().iloc[0, 1], 3), 'mean abs diff', round((j.multpl - j.shiller).abs().mean(), 2), 'n', len(j))
    pd.set_option('display.width', 250)
    cols = ['variant', 'delay', 'start', 'end', 'n_months', 'nw_t', 't_first_half', 't_second_half', 'strat_sharpe', 'c60_sharpe', 'strat_cagr', 'c60_cagr', 'bh_cagr',
            'placebo_pct', 'ep_hot', 'ep_cold', 'z_now', 'v_now']
    print(D[cols].round(3).T.to_string())
