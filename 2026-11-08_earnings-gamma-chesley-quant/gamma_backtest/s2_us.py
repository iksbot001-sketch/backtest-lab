"""미국 S2/S3/오라클 이벤트 스터디(EODHD 전망 추세 + 실적 발표). 2017년 이후.
신호(분기 q 실적 발표일 T 기준, 모두 대칭 성장률 = 차이 / ((|a|+|b|)/2), 분할 기준 차이를 없애기 위해 비율만 사용):
  gR  = 실현 성장률(q vs q-4, 실적 발표 actual)
  gF  = 다음 분기(q+1) 컨센서스 대비 1년 전 EPS 성장률(+1q 기록: earningsEstimateAvg vs earningsEstimateYearAgoEps)
  EA  = gF - gR   (S2: 전망 기준 다음 분기 가속도)       ORA = 실제 q+1 성장률 - gR (오라클, 미래정보)
  REV = (현재 - 90일 전)/대칭 (S3: 다음 분기 전망 수정)  RA = 최근 30일 수정 - 그 전 30일 수정 (S3b: 수정 가속)
  PER = 실현 가속도>0 이면서 EA>0 인 '감마 지속' 표시
진입: safe = T+15일 뒤 첫 거래일 종가(스냅샷 날짜 불확실성 ±20일 대비) / fast = T 후 2번째 거래일, 30일 전 값 사용.
유니버스: 발표일에 S&P 500 편입, 금융·부동산 제외, 진입가 $5 이상. 시장 = SPY. 분위 = 직전 분기 분포 컷.
사용: python s2_us.py [safe|fast]"""
import sys, gzip, json, glob
import numpy as np, pandas as pd
from pathlib import Path
S = Path.home() / 'agent-fund-data'; E = S / 'eodhd'
mode = sys.argv[1] if len(sys.argv) > 1 else 'safe'
sym = lambda a, b: (a - b) / ((np.abs(a) + np.abs(b)) / 2 + 1e-9)

# 섹터(재무 JSON에서 한 번만 추출)
secf = E / 'meta/us_sector.parquet'
if not secf.exists():
    rows = []
    for f in glob.glob(str(E / 'fund/*.US.json.gz')):
        try:
            g = (json.load(gzip.open(f, 'rt')) or {}).get('General', {})
            rows.append(dict(code=Path(f).name[:-8], sector=g.get('Sector'), gic=g.get('GicSector'), ind=g.get('Industry')))
        except Exception: pass
    pd.DataFrame(rows).to_parquet(secf)
sec = pd.read_parquet(secf).set_index('code')
fin = set(sec.index[(sec.gic.isin(['Financials', 'Real Estate'])) | (sec.sector.isin(['Financial Services', 'Real Estate']))])

ev = []
for f in glob.glob(str(E / 'earnings/*.US.json.gz')):
    code = Path(f).name[:-8]
    er = pd.DataFrame(json.load(gzip.open(f, 'rt')))
    tr = pd.DataFrame(json.load(gzip.open(str(E / 'trends' / Path(f).name), 'rt')) if (E / 'trends' / Path(f).name).exists() else [])
    if er.empty or tr.empty or code in fin: continue
    er = er[er.actual.notna() & er.date.notna() & er.report_date.notna()].copy()
    er['ym'] = pd.to_datetime(er.date).dt.to_period('M'); er = er.drop_duplicates('ym', keep='last').set_index('ym').sort_index()
    tr = tr[tr.period == '+1q'].copy()
    tr['ym'] = pd.to_datetime(tr.date).dt.to_period('M'); tr = tr.drop_duplicates('ym', keep='last').set_index('ym')
    num = ['earningsEstimateAvg', 'earningsEstimateYearAgoEps', 'epsTrendCurrent', 'epsTrend7daysAgo', 'epsTrend30daysAgo', 'epsTrend60daysAgo', 'epsTrend90daysAgo']
    tr[num] = tr[num].apply(pd.to_numeric, errors='coerce')
    A = er.actual.astype(float)
    for ym, r in er.iterrows():
        if ym.year < 2017: continue
        nx = ym + 3
        if nx not in tr.index: continue
        t = tr.loc[nx]
        a_q, a_q4, a_q1, a_q5 = (A.get(ym - k) for k in (0, 12, 3, 15))
        if a_q is None or a_q4 is None: continue
        cur = t.epsTrendCurrent if mode == 'safe' else t.epsTrend30daysAgo
        ya = t.earningsEstimateYearAgoEps
        if not np.isfinite(cur) or not np.isfinite(ya): continue
        gR = sym(a_q, a_q4); gF = sym(cur, ya)
        gR1 = sym(a_q1, a_q5) if a_q1 is not None and a_q5 is not None else np.nan
        a_nx = A.get(nx); a_q3 = A.get(ym - 9)
        ora = sym(a_nx, a_q3) - gR if a_nx is not None and a_q3 is not None else np.nan
        b90 = t.epsTrend90daysAgo if mode == 'safe' else np.nan
        ev.append(dict(code=code, tk=code[:-3], ym=ym, T=pd.Timestamp(r.report_date), bam=r.before_after_market,
                       gR=gR, gF=gF, EA=gF - gR, ORA=ora, acc=gR - gR1,
                       REV=sym(cur, t.epsTrend90daysAgo) if mode == 'safe' else sym(t.epsTrend30daysAgo, t.epsTrend90daysAgo),
                       RA=(sym(t.epsTrendCurrent, t.epsTrend30daysAgo) - sym(t.epsTrend30daysAgo, t.epsTrend60daysAgo)) if mode == 'safe' else np.nan))
ev = pd.DataFrame(ev)
print('raw events', len(ev), 'firms', ev.code.nunique())

# S&P 500 편입(발표일 기준)
C = pd.read_csv(S / 'sp500_components.csv'); C['date'] = pd.to_datetime(C.date); C = C.sort_values('date')
md = C.date.values; ms = [set(x.replace('.', '-') for x in s.split(',')) for s in C.tickers]
ev = ev[[ (lambda i: i >= 0 and t in ms[i])(np.searchsorted(md, np.datetime64(d), side='right') - 1) for t, d in zip(ev.tk, ev['T'])]].copy()
print('S&P member events', len(ev), 'firms', ev.code.nunique())

px = {}
for f in glob.glob(str(S / 'prices/us/*.parquet')):
    d = pd.read_parquet(f); d = d[d.close > 0]
    if len(d): px[Path(f).stem] = d.set_index('date').close
px = pd.DataFrame(px).sort_index(); px.index = pd.to_datetime(px.index); px = px[px.index >= '2016-06-01']
last = px.apply(lambda c: c.last_valid_index()); px = px.ffill()
for c, d in last.items():
    if d is not None and not pd.isna(d): px.loc[px.index > d, c] = np.nan
cal = px.index
ev = ev[ev.tk.isin(px.columns)].copy()
print('with prices', len(ev), 'firms', ev.code.nunique(), '(가격 없는 종목은 빠짐: 생존편향 점검 대상)')
lag = pd.Timedelta(days=15)
def i_entry(T, bam):
    if mode == 'safe': return cal.searchsorted(T + lag)
    return cal.searchsorted(T) + (2 if bam != 'AfterMarket' else 3) - 1
ev['i0'] = [i_entry(T, b) for T, b in zip(ev['T'], ev.bam)]
ev = ev[ev.i0 < len(cal) - 1].copy()
spy = px['SPY']
def exret(tk, i0, h):
    s = px[tk]; p0 = s.iloc[i0]
    if not np.isfinite(p0) or p0 < 5: return np.nan
    j = min(i0 + h, len(cal) - 1); seg = s.iloc[i0:j + 1].dropna()
    if len(seg) < 3: return np.nan
    return (seg.iloc[-1] / p0 - 1) - (spy.loc[seg.index[-1]] / spy.iloc[i0] - 1)
for h, nm in ((21, '1m'), (63, '1q'), (126, '2q')):
    ev['ex_' + nm] = [exret(t, i, h) for t, i in zip(ev.tk, ev.i0)]
ev['tq'] = ev['T'].dt.year * 4 + (ev['T'].dt.month - 1) // 3
ev.to_parquet(S / f'events_us_s2_{mode}.parquet', index=False)

def study(sig, nm):
    x = ev[np.isfinite(ev[sig]) & np.isfinite(ev['ex_' + nm])].copy()
    cut = {tq: np.nanpercentile(g[sig], np.arange(10, 100, 10)) for tq, g in x.groupby('tq') if len(g) >= 50}
    x = x[x.tq.map(lambda t: (t - 1) in cut)].copy()
    x['dec'] = [int(np.searchsorted(cut[t - 1], v)) + 1 for t, v in zip(x.tq, x[sig])]
    dm = x.groupby('dec')['ex_' + nm].mean() * 100
    h = x.groupby('tq').apply(lambda g: g[g.dec == 10]['ex_' + nm].mean() - g[g.dec == 1]['ex_' + nm].mean(), include_groups=False).dropna()
    lo = x.groupby('tq').apply(lambda g: g[g.dec == 10]['ex_' + nm].mean(), include_groups=False).dropna()
    tt = lambda s: s.mean() / s.std(ddof=1) * np.sqrt(len(s)) if len(s) > 2 else np.nan
    yr = h.index // 4
    print(f'{sig:4s} {nm}: dec ' + ' '.join(f'{v:5.2f}' for v in dm.values) +
          f' | D10-D1 {h.mean()*100:5.2f}% t={tt(h):5.2f} +{int((h>0).sum())}/{len(h)} | D10롱 {lo.mean()*100:5.2f}% t={tt(lo):4.2f}'
          f' | IS(~21) {h[yr<=2021].mean()*100:5.2f}% t={tt(h[yr<=2021]):4.2f} OOS(22~) {h[yr>=2022].mean()*100:5.2f}% t={tt(h[yr>=2022]):4.2f}')
print(f'\n== mode={mode} 기간 {ev["T"].min().date()}~{ev["T"].max().date()} 분기 {ev.tq.nunique()}')
for sig in ['EA', 'REV', 'RA', 'gF', 'acc', 'ORA']:
    for nm in ('1m', '1q', '2q'):
        if ev[sig].notna().sum() > 1000: study(sig, nm)
p = ev[(ev.acc > 0) & (ev.EA > 0)]; n = ev[~((ev.acc > 0) & (ev.EA > 0))]
for nm in ('1m', '1q', '2q'):
    print(f'감마 지속(실현 가속>0 & 전망 가속>0) {nm}: {p["ex_"+nm].mean()*100:.2f}% (n={p["ex_"+nm].notna().sum()}) vs 나머지 {n["ex_"+nm].mean()*100:.2f}%')
