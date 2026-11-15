"""사전 검증 입력 (Claude Code, 2026-11-15). 보정 백테스트(adhoc_20261114) 입력 표에 '그때 알 수 있던' 값만 더한다.
- 컨센서스: EODHD trends 의 FY t+1 '+1y' 행(마지막 스냅샷 = FY t 가 끝날 무렵). 매출 증가율 g1c, EPS 증가율 gec, 애널리스트 수.
- 실적: FY t 매출·영업이익·순이익(평가일 = FY t 말 + 90일, 10-K 공시 뒤).
- 실현값(rev1~3, m1~3)은 비교·진단용으로만 남긴다. 계산에 쓰면 안 된다."""
import gzip, json
from pathlib import Path
import numpy as np, pandas as pd
S = Path.home() / 'agent-fund-data'; RUN = Path(__file__).resolve().parents[1]
base = pd.read_csv('~/agent-fund/runs/adhoc_20261114_val2_calibration/data/inputs.csv')
base = base[(base.t >= 2017) & (base.t <= 2022)].copy()
f = lambda x: float(x) if x not in (None, '', 'None') else np.nan
out = []
for tk, g in base.groupby('ticker'):
    fp, tp = S / 'eodhd/fund' / f'{tk}.US.json.gz', S / 'eodhd/trends' / f'{tk}.US.json.gz'
    if not tp.exists(): continue
    inc = json.load(gzip.open(fp))['Financials']['Income_Statement']['yearly']
    tr = {r['date']: r for r in json.load(gzip.open(tp)) if r.get('period') == '+1y'}
    ys = sorted(inc)
    for _, r in g.iterrows():
        y = r.fy_end; j = ys.index(y); nxt = ys[j + 1]
        c = tr.get(nxt)
        if c is None:   # 회계연도 말 날짜가 하루 이틀 다른 경우
            near = [d for d in tr if abs((pd.Timestamp(d) - pd.Timestamp(nxt)).days) <= 10]
            c = tr[near[0]] if near else None
        if c is None: continue
        rev0, op0, ni0 = f(inc[y].get('totalRevenue')), f(inc[y].get('operatingIncome')), f(inc[y].get('netIncome'))
        g1c, gec, na = f(c.get('revenueEstimateGrowth')), f(c.get('growth')), f(c.get('revenueEstimateNumberOfAnalysts'))
        rc = f(c.get('revenueEstimateAvg'))
        if np.isnan(rc) or np.isnan(op0) or rev0 <= 0: continue
        d = r.to_dict()
        d.update(m0=op0 / rev0, ni0=ni0, rev1_cons=rc, g1c=rc / rev0 - 1, g1c_reported=g1c, gec=gec, n_analysts=na,
                 ey_fwd=(ni0 * (1 + gec) / r.mktcap) if (ni0 > 0 and not np.isnan(gec)) else np.nan)
        out.append(d)
df = pd.DataFrame(out)
# 컨센서스 매출이 FY t 실적과 너무 다르면(단위·분할·회계 변경 의심) 뺀다
bad = (df.g1c < -0.5) | (df.g1c > 2.0)
print('관측', len(df), '이상치 제외', int(bad.sum())); df = df[~bad]
print('연도별', df.groupby('t').size().to_dict(), '종목', df.ticker.nunique())
print('컨센서스 매출 증가율 vs 실제: 상관', round(df.g1c.corr(df.rev1 / df.rev0 - 1), 3), '평균 오차', round((df.g1c - (df.rev1 / df.rev0 - 1)).mean(), 4))
print('보고된 증가율과 계산 증가율 차이 중앙값', round((df.g1c - df.g1c_reported).abs().median(), 4))
df.drop(columns=['g1c_reported']).to_csv(RUN / 'data/inputs.csv', index=False)
