"""리포트용 데이터 묶음(out/report.json). 판정은 PREREG 4절 J1~J4 기계 적용 + 수동 메모."""
import json, sys
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).parent)); import core
O = core.O; TK = {'SP500': 'GSPC', 'NASDAQ100': 'NDX', 'SOX': 'SOX', 'KOSPI': 'KS11', 'KOSDAQ': 'KQ11'}
KN = {'SP500': 'S&P500', 'NASDAQ100': 'NASDAQ100', 'SOX': '필라델피아 반도체(SOX)', 'KOSPI': 'KOSPI', 'KOSDAQ': 'KOSDAQ'}
f = lambda x: None if x is None or (isinstance(x, float) and not np.isfinite(x)) else round(float(x), 4)

def series(panel, mkt, extra=None):
    p = pd.read_csv(panel, index_col=0); px = core.month_end(core.yh(TK[mkt]))
    px.index = px.index.astype(str); idx = p.index.astype(str)
    out = dict(d=list(idx), z=[f(x) for x in p.z], v=[f(x) for x in p.v], px=[f(px.get(i)) for i in idx])
    if extra is not None: out['z2'] = [f(extra.get(i)) for i in idx]
    return out

def resolved_tables(panel, disp):
    """미확정 12개월 수익률(r12 NaN) 월을 뺀 구간표/에피소드 + 비중첩 12개월 OLS t(12개 오프셋)."""
    p = pd.read_csv(panel, index_col=0); r = p[p.r12.notna()]
    zt = []
    for zn in ['Z<=-2', '-2<Z<=-1', 'neutral', '1<=Z<2', 'Z>=2']:
        m = (r.zone == zn); s_ = r[m]
        d = dict(zone=zn, months=int(m.sum()), episodes=len(core.episodes(m)), r12=s_.r12.mean() if len(s_) else None,
                 up12=(s_.r12 > 0).mean() if len(s_) else None)
        if disp: d['r3'] = s_.r3.mean() if len(s_) else None
        zt.append(d)
    ep_hot = len(core.episodes(r.z >= 1)); ep_cold = len(core.episodes(r.z <= -1))
    ts = []
    y = np.log1p(r.r12.values); x = r.z.values
    for o in range(12):
        yy, xx = y[o::12], x[o::12]
        if len(yy) < 6: continue
        X = np.column_stack([np.ones(len(xx)), xx]); b = np.linalg.lstsq(X, yy, rcond=None)[0]; u = yy - X @ b
        se = np.sqrt((u @ u) / (len(yy) - 2) * np.linalg.inv(X.T @ X)[1, 1]); ts.append(b[1] / se)
    return zt, ep_hot, ep_cold, (float(np.median(ts)) if ts else None), (float(min(ts)) if ts else None), (float(max(ts)) if ts else None), int(len(r))

HALF = {'nw_t': 't_second_half', 'nw_t3': 't3_second_half'}; HN = {'nw_t': '12개월', 'nw_t3': '3개월'}
def verdict(st, crit, t_keys):
    """PREREG 4절: J1~J4 모두=시그널, J1/J4=참고지표, 단 3절 '에피소드<3이면 판정 보류'(확정 수익률 기준). 이격도는 수평선별 따로 판정."""
    rank = {'시그널': 3, '참고지표': 2, '판정 보류': 1, '기각': 0}; out = None
    j2 = st['ep_hot_res'] >= 3 and st['ep_cold_res'] >= 3
    j3 = st['strat_sharpe'] > st['c60_sharpe'] and st['placebo_pct'] >= 0.9
    for k in t_keys:
        t, th = st[k], st[HALF[k]]; tag = f'[{HN[k]}] ' if len(t_keys) > 1 else ''
        j1 = t <= -2.0 and abs(t) >= crit; j4 = t < 0 and th < 0
        if all([j1, j2, j3, j4]): v = '시그널'
        elif j1 and j4: v = '참고지표' if j2 else '판정 보류'
        else: v = '기각'
        why = []
        if not j1: why.append(f'{tag}J1 실패: t {t:+.2f} (기준 ≤ −{crit:.2f})' if t < 0 else f'{tag}J1 실패: t {t:+.2f}, 방향 반대(높을수록 이후 수익 높음)')
        if not j4: why.append(f'{tag}J4 실패: 전체 t가 양수라 방향 유지 불가 (후반부 {th:+.2f})' if t >= 0 else f'{tag}J4 실패: 후반부 t {th:+.2f}로 부호 반전')
        r = dict(v=v, j=[bool(j1), bool(j2), bool(j3), bool(j4)], why=why, k=k)
        if out is None or rank[v] > rank[out['v']]: out = dict(r, why=list(why)) if out is None else dict(r, why=out['why'] + why)
        elif out is not None: out['why'] += why
    if not j2: out['why'].append(f"J2 실패: 12개월 수익률이 확정된 에피소드 과열 {st['ep_hot_res']}회/저평가 {st['ep_cold_res']}회 (각 3회 이상 필요)")
    if not j3: out['why'].append(f"J3 실패: 전략 Sharpe {st['strat_sharpe']:.2f} vs 60% 고정 {st['c60_sharpe']:.2f}, 플라시보 {st['placebo_pct']*100:.0f}% (90% 이상 필요)")
    if out['v'] == '판정 보류': out['why'].insert(0, 'J1/J4는 통과했지만 확정 에피소드가 3회 미만 → PREREG 3절에 따라 판정 보류')
    return out

combos = []
S = pd.read_csv(O / 'stats.csv').set_index(['market', 'ind']); D1 = pd.read_csv(O / 'stats_d1.csv').set_index(['market', 'ind'])
Z = pd.read_csv(O / 'zones.csv')
NOTE = {('KOSPI', 'PER'): 'TTM PER이라 이익 급증기에 낮아짐(2026 하반기 32배→9.5배). 고점 2개월 전 과열 신호는 맞았지만 통계적으로는 무관.',
        ('KOSPI', 'PBR'): '2010~2024에는 작동(원수준 t −2.76, 2025 제외 t −3.13, 사후 분석). 2025-09 과열 진입 뒤 +164%로 크게 실패.',
        ('SP500', 'PER'): 'S&P가 집계한 실제 이익(쉴러 교수 공개 자료)의 분기 말 값만 쓰고, 분기 말 3개월 뒤부터 알았다고 보고 계산(1998~). 처음 쓴 multpl.com은 같은 자료를 월별로 직선 보간한 값이라 2008~2010 이익 급락이 미리 반영돼 후반부 t +2.60, 전략 Sharpe 0.67 > 0.63처럼 좋아 보였음. 교체 후 그 착시가 사라짐. 1908~ 장기 표본도 t −0.39. 레드팀 5차: 반영 지연 0~6개월, CAPE, 일드갭, 2008~2010 제외 모두 통과 0건.',
        ('SP500', 'PBR'): '후반부만 −2.80. 2023년부터 계속 과열인데 지수는 상승. 2026 분기값 3개 결측.',
        ('KOSDAQ', 'PER'): '합산이익이 0 근처라 PER이 수십~수백 배로 튐. 2010-08 이후만 사용.',
        ('KOSDAQ', 'PBR'): '중첩 12개월 NW t는 −4.31이지만, 겹치지 않는 12개월 수익률로 나눠 보면 t −1.3~−2.4(중앙 −2.0)로 약해짐. 확정 저평가 진입은 2022-09/2024-09 두 번뿐이고 z≤−2는 한 번도 없었음. 2005~2013 평균 PBR 1.55보다 2013~ 평균 1.98이 높아, 지금 1.44가 10년 기준으로는 크게 싸 보이는 측면도 있음. 2026-01 z +2.06(1,098)은 4월 고점 1,226 직전 과열 신호. 현재 z −1.71(KRX 11-17 기준).'}
SH = pd.read_csv(O / 'spx_pe_shiller_stats.csv')
for (mkt, ind), st in S.iterrows():
    st = dict(st); st['d1_t'] = D1.loc[(mkt, ind), 'nw_t']
    panel = O / f'panel_{mkt}_{ind}.csv'
    if (mkt, ind) == ('SP500', 'PER'):                       # PREREG 10절: 쉴러(S&P 원자료) 분기 말 이익으로 교체
        r0 = SH[(SH.variant == 'lag3') & (SH.delay == 0)].iloc[0]; r1 = SH[(SH.variant == 'lag3') & (SH.delay == 1)].iloc[0]
        st = {k: r0[k] for k in r0.index if k in st or k in ('start', 'end')}; st['d1_t'] = r1['nw_t']; panel = O / 'panel_SP500_PER_SH_lag3.csv'
    zt, st['ep_hot_res'], st['ep_cold_res'], st['nov_t_med'], st['nov_t_min'], st['nov_t_max'], st['n_res'] = resolved_tables(panel, False)
    combos.append(dict(group='valuation', id=f'{mkt}_{ind}', title=f'{KN[mkt]} {"PER(TTM)" if ind=="PER" else "PBR"}', mkt=mkt, ind=ind,
                       stats={k: f(st[k]) if not isinstance(st[k], str) else st[k] for k in st}, zones=zt,
                       verdict=verdict(st, 2.73, ['nw_t']), note=NOTE.get((mkt, ind), ''), s=series(panel, mkt)))
for mkt, ind, why in [('NASDAQ100', 'PER/PBR', '무료 장기 시계열 없음'), ('SOX', 'PER/PBR(TTM)', '무료 장기 시계열 없음 → 가격 기반(이격도)과 사진 차트 선행 PER로 대체')]:
    combos.append(dict(group='valuation', id=f'{mkt}_NA', title=f'{KN[mkt]} {ind}', mkt=mkt, verdict=dict(v='검증 불가', j=[], why=[why]), note='', s=None))

DS = pd.read_csv(O / 'disp_stats.csv'); DD = pd.read_csv(O / 'disp_stats_d1.csv'); DZ = pd.read_csv(O / 'disp_zones.csv')
NOTE_D = {'SOX': '사진 차트와 같은 구간(1995-10-16~2026-11-09)으로 계산하면 평균 5.82%, ±1σ +24.3/−12.7%, 11-09 값 −7.45%로 차트와 일치(아래 표의 전체 평균 6.5%는 1995-02 시작 기준). 일간 탐색: 고정 −1σ 하향 돌파(6개월 내 재돌파 제외) 15회 뒤 12개월 평균 15.6%, 같은 기간 무조건 22.1%. 2000/2002/2007은 −15~−59%.',
          'KOSDAQ': '12개월 t −2.09로 가장 근접했지만 기준 미달, 2016~2026은 −1.89. 현재 이격도 −30.8%, z −2.57 (역대 하위권).',
          'NASDAQ100': '3개월 t +1.78: 이격도가 낮을 때 이후 3개월도 약함. 200일선 아래로 내려간 초기에는 하락이 이어지는 경향(추세 지속)이 역추세 매수를 깎아 먹음.',
          'SP500': '플라시보 5%: 역추세 비중 조절이 무작위보다 나쁨(과열 구간에서 덜 사고 하락 초기에 더 삼).',
          'KOSPI': '차트 방식(전체 고정)으로는 t −2.24지만 롤링으로는 −0.11. 같은 시작월로 맞추면 고정 −0.81, 누적 평균(미래 정보 없음) −0.35 → 차이 대부분은 1997~2005가 표본에 더해진 효과.'}
for mkt in TK:
    st = dict(DS[(DS.market == mkt) & (DS['mode'] == 'rolling')].iloc[0]); fx = dict(DS[(DS.market == mkt) & (DS['mode'] == 'fixed')].iloc[0])
    st['d1_t'] = DD[(DD.market == mkt) & (DD['mode'] == 'rolling')].nw_t.iloc[0]
    st['fixed_t'] = fx['nw_t']; st['fixed_t3'] = fx['nw_t3']
    pf = pd.read_csv(O / f'panel_{mkt}_DISP_fixed.csv', index_col=0)['z']
    zt, st['ep_hot_res'], st['ep_cold_res'], st['nov_t_med'], st['nov_t_min'], st['nov_t_max'], st['n_res'] = resolved_tables(O / f'panel_{mkt}_DISP_rolling.csv', True)
    combos.append(dict(group='disparity', id=f'{mkt}_DISP', title=f'{KN[mkt]} 200일 이격도', mkt=mkt, ind='DISP',
                       stats={k: f(v) if not isinstance(v, str) else v for k, v in st.items()}, zones=zt,
                       verdict=verdict(st, 2.81, ['nw_t', 'nw_t3']), note=NOTE_D.get(mkt, ''),
                       s=series(O / f'panel_{mkt}_DISP_rolling.csv', mkt, extra=pf.set_axis(pf.index.astype(str)))))

fw = []
FS = pd.read_csv(O / 'fpe_stats.csv'); FD = pd.read_csv(O / 'fpe_stats_d1.csv')
FTK = {'SOX': 'SOX', 'NASDAQ100(추정)': 'NDX', 'SP500(추정)': 'GSPC'}
FTITLE = {'SOX': 'SOX 선행 PER', 'NASDAQ100(추정)': 'NASDAQ100 선행 PER (지수명 추정)', 'SP500(추정)': 'S&P500 선행 PER (지수명 추정)'}
FNOTE = {'SOX': '사진 차트(Bloomberg, 주간 2016-11~2026-11) 디지털화. 직전 5년 롤링 z라 신호는 2019-12부터, 12개월 수익률 확정 72개월(약 6년). 후반부 t −4.45는 2022-11~2025-10(반도체 바닥→AI 랠리) 36개월 한 사이클 값이고 전반부는 +0.60으로 반대. 겹치지 않게 나누면 t 최소 −1.78. Antigravity 레드팀: 2~7년 창/확장 창/잡음 주입 1,200회 어디서도 통과 0건.',
         'NASDAQ100(추정)': '차트 방식(전체 고정)에서는 t −1.33, 비중 전략이 플라시보 93%로 가장 그럴듯했지만 사후 기준선이고 유의하지 않음. 그 우위는 2016~2019를 나중에 정한 평균으로 저평가라 본 덕분이고, 실시간 구간(2019-12~)만 보면 플라시보 61%(레드팀). 직전 5년 롤링 z로 바꾸면 t −0.32. 현재 사진값 18.9배는 직전 5년 기준 z −2.58로 표본 내 최저권.',
         'SP500(추정)': '실시간/차트 방식 모두 t ≈ 0. 현재 18.1배는 직전 5년 기준 z −0.97로 중립~약한 저평가. TTM PER(z +0.18)과 같은 결론.'}
for mkt in FS.market.unique():
    st = dict(FS[(FS.market == mkt) & (FS['mode'] == 'rolling5y')].iloc[0]); fx = dict(FS[(FS.market == mkt) & (FS['mode'] == 'fixed')].iloc[0])
    st['d1_t'] = FD[(FD.market == mkt) & (FD['mode'] == 'rolling5y')].nw_t.iloc[0]; st['fixed_t'] = fx['nw_t']; st['fixed_t3'] = fx['nw_t3']
    st['fixed_placebo'] = fx['placebo_pct']; st['z_now'] = st['z_now_photo']; st['v_now'] = st['now_v']
    zt, _, _, _, _, _, _ = resolved_tables(O / f'panel_FPE_{FTK[mkt]}_rolling5y.csv', True)
    p = pd.read_csv(O / f'panel_FPE_{FTK[mkt]}_rolling5y.csv', index_col=0); pf = pd.read_csv(O / f'panel_FPE_{FTK[mkt]}_fixed.csv', index_col=0)
    px = core.month_end(core.yh(FTK[mkt])); px.index = px.index.astype(str); idx = list(pf.index.astype(str))
    zr = p.z.set_axis(p.index.astype(str)); vv = pf.v.set_axis(pf.index.astype(str))
    sr = dict(d=idx, z=[f(zr.get(i)) for i in idx], z2=[f(x) for x in pf.z], v=[f(vv.get(i)) for i in idx], px=[f(px.get(i)) for i in idx])
    vd = verdict(st, 2.64, ['nw_t', 'nw_t3'])
    combos.append(dict(group='fwd', id=f'FPE_{FTK[mkt]}', title=FTITLE[mkt], mkt=mkt, ind='선행 PER',
                       stats={k: f(v) if not isinstance(v, str) else v for k, v in st.items()}, zones=zt, verdict=vd, note=FNOTE[mkt], s=sr))


# ---- PREREG 9절 일간/단기 ----
daily = []
if (O / 'daily_events_test.csv').exists():
    import daily as DY
    ET = pd.read_csv(O / 'daily_events_test.csv'); ST = pd.read_csv(O / 'daily_strategy.csv').set_index('name')
    EVS = pd.read_csv(O / 'daily_events.csv'); CHK = pd.read_csv(O / 'daily_pbr_approx_check.csv', index_col=0).iloc[:, 0].to_dict()
    data, _ = DY.load()
    DT = {'SP500_DISP': 'S&P500 200일 이격도', 'NASDAQ100_DISP': 'NASDAQ100 200일 이격도', 'SOX_DISP': 'SOX 200일 이격도', 'KOSPI_DISP': 'KOSPI 200일 이격도',
          'KOSDAQ_DISP': 'KOSDAQ 200일 이격도', 'KOSPI_PBR': 'KOSPI PBR (일간)', 'KOSDAQ_PBR': 'KOSDAQ PBR (일간 근사)'}
    DN = {'KOSDAQ_PBR': f"일간값은 직전 월말 PBR/종가 비율 × 당일 종가로 근사. 같은 근사를 KOSPI에 적용하면 실제 일간 PBR과 평균 오차 {CHK['mape']*100:.1f}%, z 상관 {CHK['z_corr']:.3f}.",
          'KOSPI_PBR': 'KRX 일간 PBR은 11-04까지라 현재 z는 그 날짜 기준.'}
    DN['KOSDAQ_PBR'] += ' 매수 쪽 p 0.029(7회)는 2020-03-12 한 건(+15.4%)만 빼면 p 0.14, 사건 간격을 20일로 바꾸면 p 0.37로 사라짐(레드팀 4차). 2026-10-22 진입분은 11-18까지 −12.8%.'
    for name, (px, v) in data.items():
        st = dict(ST.loc[name]); d3 = st['sharpe'] > st['const_sharpe'] and st['placebo'] >= 0.9
        z = DY.zroll(v.dropna()).dropna(); pxz = px.reindex(z.index)
        wk = pd.DataFrame({'z': z, 'px': pxz}).resample('W-FRI').last().dropna()
        sides = []
        for side, lvl, nm in [('buy', -1, '매수 (−1σ 하향 돌파)'), ('sell', 1, '매도 (+1σ 상향 돌파)')]:
            r = ET[(ET.name == name) & (ET.lvl == lvl) & (ET.h == 20)].iloc[0]; sg = 1 if side == 'buy' else -1
            n = int(r['n']); d1 = n > 0 and sg * r['excess'] > 0 and r['p'] < 0.05 / 14; d2 = n >= 8
            d4 = n > 0 and sg * r['excess_2nd'] > 0
            v_ = '단기 시그널' if all([d1, d2, d3, d4]) else ('단기 참고지표' if d1 and d4 and d2 else ('판정 보류' if d1 and d4 else '기각'))
            why = []
            if not d1: why.append(f"D1 실패: 20일 초과수익 {r['excess']*100:+.2f}%p, p {r['p']:.3f}" + (' (방향 반대)' if sg * r['excess'] <= 0 else f' (기준 < 0.0036)'))
            if not d2: why.append(f'D2 실패: 독립 이벤트 {n}회 (8회 이상 필요)')
            if not d4: why.append(f"D4 실패: 후반부 초과수익 {r['excess_2nd']*100:+.2f}%p")
            if not d3: why.append(f"D3 실패(지표 공통): 일간 전략 Sharpe {st['sharpe']:.2f} vs 노출 일치 {st['const_sharpe']:.2f}, 플라시보 {st['placebo']*100:.0f}%")
            tab = ET[(ET.name == name) & (ET.side == side)][['lvl', 'h', 'n', 'excess', 'hit', 'p']].copy()
            sides.append(dict(side=nm, v=v_, j=[bool(d1), bool(d2), bool(d3), bool(d4)], why=why, tab=tab.round(4).to_dict('records')))
        ev = EVS[(EVS.name == name) & (EVS.lvl.isin([-1, 1]))][['lvl', 'date', 'r20']]
        daily.append(dict(id=f'D_{name}', title=DT[name], note=DN.get(name, ''), strat={k: (round(float(x), 4) if isinstance(x, (int, float, np.floating)) else x) for k, x in st.items()},
                          sides=sides, s=dict(d=[str(i.date()) for i in wk.index], z=[f(x) for x in wk.z], px=[f(x) for x in wk.px]),
                          ev=ev.to_dict('records')))

HZ = pd.read_csv(O / 'horizons_stats.csv') if (O / 'horizons_stats.csv').exists() else pd.DataFrame()
hz = HZ[['combo', 'h', 'nw_t', 't_second_half', 'nov_t', 'ep_hot', 'ep_cold', 'verdict']].round(3).to_dict('records') if len(HZ) else []
WN = pd.read_csv(O / 'windows_stats.csv') if (O / 'windows_stats.csv').exists() else pd.DataFrame()
wn = WN[['combo', 'group', 'window', 'same_start', 'start', 't12', 't12_half', 't3', 'placebo', 'ep_hot', 'ep_cold', 'verdict']].round(3).to_dict('records') if len(WN) else []
ov = pd.read_csv(O / 'overlay.csv'); ofg = pd.read_csv(O / 'overlay_fg.csv'); reg = pd.read_csv(O / 'overlay_reg.csv')
def _c(o):
    import numpy as _n
    if isinstance(o,dict): return {k:_c(v) for k,v in o.items()}
    if isinstance(o,list): return [_c(v) for v in o]
    if isinstance(o,(_n.bool_,)): return bool(o)
    if isinstance(o,(_n.integer,)): return int(o)
    if isinstance(o,float) and not math.isfinite(o): return None
    return o
import math
json.dump(_c(dict(combos=combos, fwd=fw, daily=daily, hz=hz, wn=wn, overlay=ov.round(4).to_dict('records'), overlay_fg=ofg.round(4).to_dict('records'),
               reg=reg.round(3).to_dict('records'))), open(O / 'report.json', 'w'), ensure_ascii=False)
for c in combos: print(c['id'], c['verdict']['v'], c['verdict']['why'])
for c in daily:
    for sd in c['sides']: print(c['id'], sd['side'], sd['v'], sd['why'])
