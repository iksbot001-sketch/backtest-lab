"""탐색(판정 아님): 미래 정보를 걸러내지 않은 '전체 기간 고정 평균/σ' z로 모든 월간 조합을 같은 J1~J4에 넣어 비교."""
import sys
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).parent)); import core
O = core.O; core.DELAY = 0

def judge(res, st, crit, t3=None, t3h=None):
    r = res[res.r12.notna()]; eh = len(core.episodes(r.z >= 1)); ec = len(core.episodes(r.z <= -1))
    cands = [(st['nw_t'], st['t_second_half'])] + ([(t3, t3h)] if t3 is not None else [])
    j2 = eh >= 3 and ec >= 3; j3 = st['strat_sharpe'] > st['c60_sharpe'] and st['placebo_pct'] >= .9
    best = '기각'
    for t, th in cands:
        j1 = t <= -2 and abs(t) >= crit; j4 = t < 0 and th < 0
        v = '시그널' if (j1 and j2 and j3 and j4) else ('참고지표' if (j1 and j4 and j2) else ('판정 보류' if (j1 and j4) else '기각'))
        if ['기각', '판정 보류', '참고지표', '시그널'].index(v) > ['기각', '판정 보류', '참고지표', '시그널'].index(best): best = v
    return best, eh, ec

def run(name, px, v, crit, horizon3=False):
    out = {}
    for mode in ('rolling', 'fixed'):
        zf = (lambda s: (s - s.mean()) / s.std()) if mode == 'fixed' else None
        orig = core.rolling_z
        if zf: core.rolling_z = lambda s, *a, **k: zf(s)
        try: res, zt, st = core.analyze(name, px, mode, v)
        finally: core.rolling_z = orig
        t3 = t3h = None
        if horizon3:
            t3 = core.nw_t(np.log1p(res.r3.values), res.z.values, 3)[1]
            r3 = res[res.r3.notna()]; h = r3.index[len(r3) // 2]; t3h = core.nw_t(np.log1p(res.loc[h:, 'r3'].values), res.loc[h:, 'z'].values, 3)[1]
        v_, eh, ec = judge(res, st, crit, t3, t3h)
        out[mode] = dict(t=st['nw_t'], t3=t3, half=st['t_second_half'], sh=st['strat_sharpe'], c60=st['c60_sharpe'], pl=st['placebo_pct'], eh=eh, ec=ec, v=v_)
    return out

rows = []
V = core.load_val()
import spx_pe_shiller as SPX
sh = SPX.load_shiller(); gspc = core.yh('GSPC'); vsp = SPX.per_series(core.month_end(gspc), sh.E, 3)
for mkt, ind, px, v in [('KOSPI', 'PER', V['KOSPI']['px'], V['KOSPI']['PER']), ('KOSPI', 'PBR', V['KOSPI']['px'], V['KOSPI']['PBR']),
                        ('SP500', 'PER', gspc, vsp), ('SP500', 'PBR', V['SP500']['px'], V['SP500']['PBR']),
                        ('KOSDAQ', 'PER', V['KOSDAQ']['px'], V['KOSDAQ']['PER']), ('KOSDAQ', 'PBR', V['KOSDAQ']['px'], V['KOSDAQ']['PBR'])]:
    v = v[v > 0]
    # fixed는 10년 롤링 워밍업 없이 전 기간 → 표본 시작을 롤링과 맞춘다(같은 달만 비교)
    o = run(f'{mkt}_{ind}', px, v, 2.73); rows.append((f'{mkt} {ind}', o))
# 이격도·선행 PER은 이미 계산된 fixed 결과 사용
DS = pd.read_csv(O / 'disp_stats.csv'); FS = pd.read_csv(O / 'fpe_stats.csv')
for mkt in ['SP500', 'NASDAQ100', 'SOX', 'KOSPI', 'KOSDAQ']:
    o = {}
    for mode in ('rolling', 'fixed'):
        st = DS[(DS.market == mkt) & (DS['mode'] == mode)].iloc[0]; res = pd.read_csv(O / f'panel_{mkt}_DISP_{mode}.csv', index_col=0)
        v_, eh, ec = judge(res, st, 2.81, st.nw_t3, st.t3_second_half)
        o[mode] = dict(t=st.nw_t, t3=st.nw_t3, half=st.t_second_half, sh=st.strat_sharpe, c60=st.c60_sharpe, pl=st.placebo_pct, eh=eh, ec=ec, v=v_)
    rows.append((f'{mkt} 이격도', o))
for mkt, tk in [('SOX', 'SOX'), ('NASDAQ100(추정)', 'NDX'), ('SP500(추정)', 'GSPC')]:
    o = {}
    for mode in ('rolling5y', 'fixed'):
        st = FS[(FS.market == mkt) & (FS['mode'] == mode)].iloc[0]; res = pd.read_csv(O / f'panel_FPE_{tk}_{mode}.csv', index_col=0)
        v_, eh, ec = judge(res, st, 2.64, st.nw_t3, st.t3_second_half)
        o['rolling' if mode == 'rolling5y' else 'fixed'] = dict(t=st.nw_t, t3=st.nw_t3, half=st.t_second_half, sh=st.strat_sharpe, c60=st.c60_sharpe, pl=st.placebo_pct, eh=eh, ec=ec, v=v_)
    rows.append((f'{mkt} 선행PER', o))
out = []
for n, o in rows:
    r, f = o['rolling'], o['fixed']
    out.append(dict(combo=n, roll_t=r['t'], fix_t=f['t'], roll_t3=r['t3'], fix_t3=f['t3'], roll_pl=r['pl'], fix_pl=f['pl'], roll_sh=f"{r['sh']:.2f}/{r['c60']:.2f}", fix_sh=f"{f['sh']:.2f}/{f['c60']:.2f}",
                    fix_half=f['half'], fix_ep=f"{f['eh']}/{f['ec']}", roll_v=r['v'], fix_v=f['v']))
D = pd.DataFrame(out); D.to_csv(O / 'hindsight_compare.csv', index=False)
pd.set_option('display.width', 250); print(D.round(2).to_string())
