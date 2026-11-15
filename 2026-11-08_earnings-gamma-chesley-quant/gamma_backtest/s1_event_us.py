"""미국 S1 이벤트 스터디(F0 재현 시험). He & Narayanamoorthy의 EAP·EAA 정의, 직전 분기 분포로 10분위, 진입 = 기준일 후 2번째 거래일 종가,
1개월(21)·1분기(63) 보유, 시장조정 = SPY(시가총액가중). 유니버스 = 기준일에 S&P 500 편입 + SIC 6000~6799(금융·리츠) 제외 + 가격 $5 이상.
기준일: 'filed'(10-Q/10-K 첫 공시, 엄격한 point-in-time) 또는 'ann'(8-K 2.02 실적 발표일, 값은 10-Q 기준이라 약한 미래정보).
사용: python s1_event_us.py [eap|eaa] [filed|ann]"""
import sys, json, glob
import numpy as np, pandas as pd
from pathlib import Path
S = Path.home() / 'agent-fund-data'
sig = sys.argv[1] if len(sys.argv) > 1 else 'eap'
basis = sys.argv[2] if len(sys.argv) > 2 else 'filed'
P = pd.read_parquet(S / 'panel_us_raw.parquet')
px = {}
for f in glob.glob(str(S / 'prices' / 'us' / '*.parquet')):
    d = pd.read_parquet(f); px[Path(f).stem] = d.set_index('date').close
px = pd.DataFrame(px).sort_index(); px.index = pd.to_datetime(px.index)
cal = px.index
P['tk'] = P.ticker.str.replace('.', '-', regex=False)
P = P[P.tk.isin(px.columns)].copy()
def price_at(tk, d):
    s = px[tk]; i = cal.searchsorted(d, side='right') - 1
    return s.iloc[i] if i >= 0 else np.nan
P['p_l1'] = [price_at(t, e - pd.offsets.MonthEnd(3)) for t, e in zip(P.tk, P.end)]
if sig == 'eap':
    P['g'] = (P.eps - P.eps_l4) / P.p_l1; P['g1'] = (P.eps_l1 - P.eps_l5) / P.p_l1
else:
    P['g'] = (P.eps - P.eps_l4) / P.eps_l4.abs(); P['g1'] = (P.eps_l1 - P.eps_l5) / P.eps_l5.abs()
P['a'] = P.g - P.g1
P = P[np.isfinite(P.a)].copy()
# 금융·리츠 제외(SIC)
sic = {}
for f in glob.glob(str(S / 'sec' / 'subs' / '*.json')):
    try: sic[int(Path(f).stem)] = int(json.load(open(f)).get('sic') or 0)
    except Exception: pass
P['sic'] = P.cik.map(sic)
P = P[~P.sic.between(6000, 6799)]
# S&P 500 편입 여부(기준일 시점)
C = pd.read_csv(S / 'sp500_components.csv'); C['date'] = pd.to_datetime(C['date']); C = C.sort_values('date')
mem_dates = C.date.values; mem_sets = [set(t.split('-')[0] for t in s.split(',')) for s in C.tickers]
P['d0'] = P[basis] if basis == 'filed' else P.ann
P = P[P.d0.notna()].copy()
def member(tk, d):
    i = np.searchsorted(mem_dates, np.datetime64(d), side='right') - 1
    return i >= 0 and tk.replace('-', '.') in mem_sets[i] or (i >= 0 and tk in mem_sets[i])
P = P[[member(t, d) for t, d in zip(P.tk, P.d0)]].copy()
P['tq'] = P.end.dt.year * 4 + (P.end.dt.month - 1) // 3
cut = {tq: np.nanpercentile(g.a, np.arange(10, 100, 10)) for tq, g in P.groupby('tq')}
P = P[P.tq.map(lambda t: (t - 1) in cut)].copy()
P['dec'] = [int(np.searchsorted(cut[t - 1], v)) + 1 for t, v in zip(P.tq, P.a)]
spy = px['SPY']; cmk = spy / spy.iloc[0]
def window(tk, d0, h):
    s = px[tk]; i0 = cal.searchsorted(d0) + 2
    if i0 >= len(cal): return np.nan
    p0 = s.iloc[i0]
    if not np.isfinite(p0) or p0 < 5: return np.nan
    j = min(i0 + h, len(cal) - 1); seg = s.iloc[i0:j + 1].dropna()
    if len(seg) < 3: return np.nan
    return (seg.iloc[-1] / p0 - 1) - (cmk.loc[seg.index[-1]] / cmk.iloc[i0] - 1)
for h, nm in ((21, '1m'), (63, '1q')):
    P['ex_' + nm] = [window(t, d, h) for t, d in zip(P.tk, P.d0)]
P = P.rename(columns={'tk': 'stock_code', 'a': sig})
P['filed_entry'] = P.d0
P.to_parquet(S / f'events_us_{sig}_{basis}.parquet', index=False)
print(f'이벤트 {len(P)} 기업 {P.cik.nunique()} 기간 {P.end.min().date()}~{P.end.max().date()}')
for nm in ('1m', '1q'):
    E = P[np.isfinite(P['ex_' + nm])]
    t = E.groupby('dec')['ex_' + nm].mean() * 100
    h = E.groupby('tq').apply(lambda g: g[g.dec == 10]['ex_' + nm].mean() - g[g.dec == 1]['ex_' + nm].mean(), include_groups=False).dropna()
    yr = h.index // 4
    print(f'\n== {sig}/{basis} {nm}: decile ' + ' '.join(f'{v:.2f}' for v in t.values))
    print(f'D10-D1 {h.mean()*100:.2f}% t={h.mean()/h.std(ddof=1)*np.sqrt(len(h)):.2f} 양(+) {int((h>0).sum())}/{len(h)} | D10 롱온리 {E[E.dec==10]["ex_"+nm].mean()*100:.2f}% D1 {E[E.dec==1]["ex_"+nm].mean()*100:.2f}%')
    for lab, mk in (('IS ~2017', yr <= 2017), ('OOS 2018~', yr >= 2018)):
        x = h[mk]; print(f'  {lab}: {x.mean()*100:.2f}% t={x.mean()/x.std(ddof=1)*np.sqrt(len(x)):.2f} ({len(x)}분기)')
