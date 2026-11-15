"""연구 2: 반도체 전망 상향 폭(breadth)이 반도체 섹터의 이후 초과수익을 예측하는가 (미국, 2017~, 잠정).
매월 말 M: 각 반도체 종목의 가장 최근 '알려진' +1q 스냅샷(알려진 날 = 직전 실적 발표 + 15일, 90일 이내)에서
 rev30 = 현재 vs 30일 전, rev90 = 현재 vs 90일 전, EA = 전망 가속도. breadth = 상향 비율 − 하향 비율.
목표: 이후 1·3개월 SOXX − SPY 수익. 규칙: breadth>0 이면 SOXX, 아니면 SPY(비교: SOXX 보유, SPY 보유)."""
import gzip, json
import numpy as np, pandas as pd
from pathlib import Path
from scipy.stats import spearmanr
E = Path.home() / 'agent-fund-data/eodhd'; PX = Path.home() / 'agent-fund-data/prices/eodhd'
sym = lambda a, b: (a - b) / ((np.abs(a) + np.abs(b)) / 2 + 1e-9)
sec = pd.read_parquet(E / 'meta/us_sector.parquet'); semis = sec[sec.ind.fillna('').str.contains('Semicon')].code.tolist()
recs = []
for c in semis:
    tr = pd.DataFrame(json.load(gzip.open(E / 'trends' / f'{c}.json.gz', 'rt')))
    er = pd.DataFrame(json.load(gzip.open(E / 'earnings' / f'{c}.json.gz', 'rt')))
    if tr.empty or er.empty: continue
    er = er[er.report_date.notna()]; er['ym'] = pd.to_datetime(er.date).dt.to_period('M')
    rep = dict(zip(er.ym, pd.to_datetime(er.report_date)))
    tr = tr[tr.period == '+1q'].copy(); tr['ym'] = pd.to_datetime(tr.date).dt.to_period('M')
    for _, r in tr.iterrows():
        T = rep.get(r.ym - 3)
        if T is None: continue
        f = lambda k: pd.to_numeric(r[k], errors='coerce')
        cur = f('epsTrendCurrent')
        recs.append(dict(code=c, known=T + pd.Timedelta(days=15), rev30=sym(cur, f('epsTrend30daysAgo')), rev90=sym(cur, f('epsTrend90daysAgo')),
                         gF=sym(cur, f('earningsEstimateYearAgoEps'))))
R = pd.DataFrame(recs).sort_values('known')
px = lambda s: pd.read_parquet(PX / f'{s}.parquet').assign(date=lambda d: pd.to_datetime(d.date)).set_index('date').adjusted_close
soxx, spy = px('SOXX.US'), px('SPY.US')
me = pd.date_range('2017-09-30', '2026-10-31', freq='ME')
rows = []
for m in me:
    k = R[(R.known <= m) & (R.known > m - pd.Timedelta(days=90))].drop_duplicates('code', keep='last')
    if len(k) < 8: continue
    p0 = lambda s: s[:m].iloc[-1]
    def fwd(s, mo):
        e = m + pd.offsets.MonthEnd(mo); return s[:e].iloc[-1] / p0(s) - 1 if e <= s.index[-1] else np.nan
    rows.append(dict(m=m, n=len(k), b30=np.sign(k.rev30).mean(), b90=np.sign(k.rev90).mean(), gF=k.gF.median(),
                     x1=fwd(soxx, 1) - fwd(spy, 1), x3=fwd(soxx, 3) - fwd(spy, 3), s1=fwd(soxx, 1), p1=fwd(spy, 1)))
B = pd.DataFrame(rows).set_index('m')
print(f'월 {len(B)}개, 종목 수 평균 {B.n.mean():.0f}, 반도체 {len(semis)}개 중 사용 {R.code.nunique()}')
for s in ['b30', 'b90', 'gF']:
    for t in ['x1', 'x3']:
        x = B[[s, t]].dropna(); rho, p = spearmanr(x[s], x[t])
        print(f'  {s} → {t}: 순위상관 {rho:+.2f} (p={p:.2f}, n={len(x)}{", 3개월 겹침" if t=="x3" else ""})')
for s in ['b30', 'b90']:
    x = B.dropna(subset=['s1', 'p1']).copy(); pos = x[s] > 0
    strat = np.where(pos, x.s1, x.p1)
    cagr = lambda r: (np.prod(1 + r)) ** (12 / len(r)) - 1
    mdd = lambda r: (lambda c: (c / np.maximum.accumulate(c) - 1).min())(np.cumprod(1 + r))
    print(f'  규칙[{s}>0 이면 SOXX 아니면 SPY]: CAGR {cagr(strat)*100:.1f}% MDD {mdd(strat)*100:.1f}% | SOXX {cagr(x.s1.values)*100:.1f}%/{mdd(x.s1.values)*100:.1f}% | SPY {cagr(x.p1.values)*100:.1f}%/{mdd(x.p1.values)*100:.1f}% | SOXX 보유 개월 {pos.mean()*100:.0f}% (월 리밸런싱, 비용 미반영)')
B.to_csv(Path.home() / 'agent-fund-data/semis_breadth.csv')
print(B.tail(4).round(3).to_string())
