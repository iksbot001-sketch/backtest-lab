"""S1(실현 분기 이익 가속도) 한국 이벤트 스터디 — 고정 보유 1개월(21거래일)·1분기(63거래일). He & Narayanamoorthy 방식의 한국판 1차 점검.
진입 = 공시일(rcept_no 앞 8자리) 이후 2번째 거래일 종가. 시장조정 = 같은 구간 KOSPI 유니버스 동일가중 평균수익.
decile 컷오프 = 직전 회계분기 A 분포(논문과 동일). 가격은 수정주가(기존 DB + 상장폐지 보관분).
주의(결과 해석): DART 값은 최종 정정본일 수 있음, 상장폐지로 가격이 끊기면 마지막 가격으로 청산(보수적이지 않을 수 있음)."""
import sys, glob
import numpy as np, pandas as pd
from pathlib import Path
S = Path.home() / 'agent-fund-data'
sig = sys.argv[1] if len(sys.argv) > 1 else 'a_ni'
panel = pd.read_parquet(S / 'dart' / 'panel_kr.parquet')
co = pd.read_parquet(S / 'dart' / 'company.parquet')
co = co[(co.corp_cls == 'Y')]
ind2 = co.induty_code.astype(str).str[:2]
co = co[~ind2.isin(['64', '65', '66'])]                      # 금융업 제외
P = panel.merge(co[['corp_code']], on='corp_code')
P = P[np.isfinite(P[sig]) & (P.assets0 > 0)].copy()
print('KOSPI 비금융 이벤트 후보', len(P), '기업', P.corp_code.nunique())
# 가격
px = {}
for f in glob.glob(str(S / 'prices' / 'kr' / '*.parquet')) + glob.glob(str(S / 'prices' / 'kr_delisted' / '*.parquet')):
    c = Path(f).stem
    d = pd.read_parquet(f, columns=['date', 'close']); d = d[d.close > 0]
    if len(d): px[c] = d.set_index('date').close
px = pd.DataFrame(px).sort_index()
px = px[px.index >= '2015-06-01']
print('가격', px.shape)
univ = [c for c in P.stock_code.dropna().unique() if c in px.columns]
ret = px[univ].pct_change(fill_method=None)
mkt = ret.mean(axis=1)                                      # 동일가중 시장
cal = px.index
# 늦게 공시된(정정 의심) 건 제외: 분기말 + 한도일 초과
qe = pd.to_datetime(P.fy.astype(str) + '-' + (P.q * 3).astype(str).str.zfill(2) + '-01') + pd.offsets.MonthEnd(0)
slack = np.where(P.q == 4, 120, 60)
P['late'] = (P.filed - qe).dt.days > slack
print('늦은 공시(제외):', int(P.late.sum()))
P = P[~P.late]
# decile 컷오프: 직전 회계분기 분포
cut = {}
for tq, g in P.groupby('tq'):
    cut[tq] = np.nanpercentile(g[sig], np.arange(10, 100, 10))
P = P[P.tq.map(lambda t: (t - 1) in cut)].copy()
P['dec'] = [int(np.searchsorted(cut[t - 1], v)) + 1 for t, v in zip(P.tq, P[sig])]
# 수익률
cm = (1 + mkt.fillna(0)).cumprod()
def window(code, d0, h):
    s = px[code]
    i = cal.searchsorted(d0)                                 # 공시일 당일 또는 다음 거래일
    i0 = i + 2
    if i0 >= len(cal): return np.nan, np.nan, 0
    p0 = s.iloc[i0]
    if not np.isfinite(p0) or p0 < 2000: return np.nan, np.nan, 0   # 2,000원 미만 제외(논문 $5 필터의 대용)
    j = min(i0 + h, len(cal) - 1)
    seg = s.iloc[i0:j + 1].dropna()
    if len(seg) < 3: return np.nan, np.nan, 0
    trunc = int(seg.index[-1] < cal[j] and cal[j] < cal[-1] - pd.Timedelta(days=5))
    r = seg.iloc[-1] / p0 - 1
    m = cm.iloc[cal.get_loc(seg.index[-1])] / cm.iloc[i0] - 1
    return r, m, trunc
out = []
for h, nm in ((21, '1m'), (63, '1q')):
    rr = [window(c, d, h) if c in px.columns else (np.nan, np.nan, 0) for c, d in zip(P.stock_code, P.filed)]
    P['r_' + nm] = [x[0] for x in rr]; P['m_' + nm] = [x[1] for x in rr]; P['ex_' + nm] = P['r_' + nm] - P['m_' + nm]
    P['tr_' + nm] = [x[2] for x in rr]
P.to_parquet(S / f'events_kr_{sig}.parquet', index=False)
for nm in ('1m', '1q'):
    E = P[np.isfinite(P['ex_' + nm])]
    t = E.groupby('dec')['ex_' + nm].agg(['mean', 'count'])
    print(f'\n== {sig} 보유 {nm}: decile별 평균 시장조정 수익 (n={len(E)}, 상폐절단 {int(E["tr_"+nm].sum())}건)')
    print((t['mean'] * 100).round(2).to_string())
    h = E.groupby(['tq']).apply(lambda g: g[g.dec == 10]['ex_' + nm].mean() - g[g.dec == 1]['ex_' + nm].mean(), include_groups=False).dropna()
    print(f'D10-D1 평균 {h.mean()*100:.2f}%  분기 t={h.mean()/h.std(ddof=1)*np.sqrt(len(h)):.2f}  양(+) 분기 {int((h>0).sum())}/{len(h)}')
    for lab, sub in (('Q1~Q3', E[E.q < 4]), ('Q4', E[E.q == 4])):
        hh = sub.groupby('tq').apply(lambda g: g[g.dec == 10]['ex_' + nm].mean() - g[g.dec == 1]['ex_' + nm].mean(), include_groups=False).dropna()
        print(f'  {lab}: D10-D1 {hh.mean()*100:.2f}% (분기 {len(hh)}개, t={hh.mean()/hh.std(ddof=1)*np.sqrt(len(hh)):.2f})')
