"""가속도 예측 모델용 이벤트 패널(시점 기준). ML_PREREG.md의 특징·목표를 만든다.
대상: 2008-07 이후 발표일에 S&P 500 편입 + 금융·부동산 제외 + yfinance 가격 있음. 출력 ~/agent-fund-data/ml_panel_us.parquet"""
import gzip, json, glob
import numpy as np, pandas as pd
from pathlib import Path
S = Path.home() / 'agent-fund-data'; E = S / 'eodhd'
sym = lambda a, b: (a - b) / ((np.abs(a) + np.abs(b)) / 2 + 1e-9)

# 가격 행렬
px = {}
for f in glob.glob(str(S / 'prices/us/*.parquet')):
    d = pd.read_parquet(f); d = d[d.close > 0]
    if len(d): px[Path(f).stem] = d.set_index('date').close
px = pd.DataFrame(px).sort_index(); px.index = pd.to_datetime(px.index)
last = px.apply(lambda c: c.last_valid_index()); px = px.ffill()
for c, d in last.items():
    if d is not None and not pd.isna(d): px.loc[px.index > d, c] = np.nan
cal = px.index; V = px.values; col = {c: i for i, c in enumerate(px.columns)}; spy = V[:, col['SPY']]
R = np.vstack([np.full((1, V.shape[1]), np.nan), V[1:] / V[:-1] - 1])

# 편입·섹터
C = pd.read_csv(S / 'sp500_components.csv'); C['date'] = pd.to_datetime(C.date); C = C.sort_values('date')
md = C.date.values; ms = [set(x.replace('.', '-') for x in s.split(',')) for s in C.tickers]
def member(tk, d):
    i = np.searchsorted(md, np.datetime64(d), side='right') - 1; return i >= 0 and tk in ms[i]
ever = set().union(*[ms[i] for i in range(len(ms)) if C.date.iloc[i] >= pd.Timestamp('2008-01-01')])
sec = pd.read_parquet(E / 'meta/us_sector.parquet').set_index('code')
fin = set(sec.index[sec.gic.isin(['Financials', 'Real Estate']) | sec.sector.isin(['Financial Services', 'Real Estate'])])
t2c = json.load(open(S / 'us_ticker_cik.json')); sic = {}
for tk, cik in t2c.items():
    if not cik: continue
    f = S / 'sec/subs' / f'{int(cik)}.json'
    if f.exists():
        try: sic[tk.replace('.', '-')] = int(json.load(open(f)).get('sic') or 0)
        except Exception: pass

def load(sub, code):
    f = E / sub / f'{code}.json.gz'
    return pd.DataFrame(json.load(gzip.open(f, 'rt'))) if f.exists() else pd.DataFrame()

rows = []
for tk in sorted(ever):
    if tk not in col: continue
    code = tk + '.US'
    if code in fin or 6000 <= sic.get(tk, 0) <= 6799: continue
    er = load('earnings', code)
    if er.empty: continue
    er = er[er.date.notna() & er.report_date.notna()].copy()
    er['ym'] = pd.to_datetime(er.date).dt.to_period('M')
    er = er.sort_values('report_date').drop_duplicates('ym', keep='last').set_index('ym').sort_index()
    A = pd.to_numeric(er.actual, errors='coerce'); Es = pd.to_numeric(er.estimate, errors='coerce').replace(0, np.nan)
    tr = load('trends', code)
    if not tr.empty:
        tr = tr[tr.period == '+1q'].copy(); tr['ym'] = pd.to_datetime(tr.date).dt.to_period('M')
        tr = tr.drop_duplicates('ym', keep='last').set_index('ym')
        for c in tr.columns:
            if c not in ('code', 'date', 'period'): tr[c] = pd.to_numeric(tr[c], errors='coerce')
    ga = lambda ym: A.get(ym, np.nan)
    gR = lambda ym: sym(ga(ym), ga(ym - 12))
    j = col[tk]
    for ym, r in er.iterrows():
        T = pd.Timestamp(r.report_date)
        if T < pd.Timestamp('2008-07-01') or not np.isfinite(ga(ym)) or not member(tk, T): continue
        iT = cal.searchsorted(T)
        if iT >= len(cal) - 3 or iT < 260: continue
        ir = iT + 1 if (r.before_after_market == 'AfterMarket' and cal[iT] == T) else iT
        ifast, isafe = ir + 2, cal.searchsorted(T + pd.Timedelta(days=15))
        p = V[:, j]
        x = dict(tk=tk, ym=str(ym), T=T, ir=ir, i_fast=ifast, i_safe=isafe)
        x.update(gR0=gR(ym), gR1=gR(ym - 3), gR2=gR(ym - 6), gR3=gR(ym - 9))
        x['acc0'] = x['gR0'] - x['gR1']; x['acc1'] = x['gR1'] - x['gR2']
        x['base_g'] = gR(ym - 9)
        sur = [sym(ga(ym - 3 * k), Es.get(ym - 3 * k, np.nan)) for k in range(8)]
        x.update(sur0=sur[0], sur1=sur[1], sur2=sur[2], sur3=sur[3])
        s8 = np.array(sur); x['beat8'] = np.nanmean(s8 > 0) if np.isfinite(s8).sum() >= 4 else np.nan
        g8 = np.array([gR(ym - 3 * k) for k in range(8)]); x['gvol8'] = np.nanstd(g8) if np.isfinite(g8).sum() >= 4 else np.nan
        # 주가 특징
        rel = lambda a, b: (p[a] / p[b] - 1) - (spy[a] / spy[b] - 1) if a < len(p) and np.isfinite(p[a]) and np.isfinite(p[b]) else np.nan
        x['ear'] = rel(ir + 1, ir - 1)
        x['drift'] = rel(isafe, ir + 1) if isafe < len(p) else np.nan
        x['mom'] = p[ir - 21] / p[ir - 252] - 1 if np.isfinite(p[ir - 252]) else np.nan
        x['rev1m'] = p[ir - 1] / p[ir - 22] - 1
        x['vol63'] = np.nanstd(R[ir - 63:ir, j])
        x['px_fast'] = p[ifast] if ifast < len(p) else np.nan; x['px_safe'] = p[isafe] if isafe < len(p) else np.nan
        # 전망 추세(다음 분기 +1q 스냅샷)
        nx = ym + 3
        if not tr.empty and nx in tr.index:
            t = tr.loc[nx]; cur = t.epsTrendCurrent; ya = t.earningsEstimateYearAgoEps; n = t.earningsEstimateNumberOfAnalysts
            x.update(gF=sym(cur, ya), rev90=sym(cur, t.epsTrend90daysAgo), rev30=sym(cur, t.epsTrend30daysAgo),
                     ra=sym(cur, t.epsTrend30daysAgo) - sym(t.epsTrend30daysAgo, t.epsTrend60daysAgo),
                     up30=t.epsRevisionsUpLast30days / n if n and n > 0 else np.nan,
                     down30=t.epsRevisionsDownLast30days / n if n and n > 0 else np.nan,
                     disp=(t.earningsEstimateHigh - t.earningsEstimateLow) / (abs(cur) + 1e-9) if np.isfinite(cur) else np.nan,
                     n_an=n, rgF=t.revenueEstimateGrowth)
            x['EA'] = x['gF'] - x['gR0']
        # 목표(미래): 다음 분기 실제 가속도, 정답 공개일
        x['ORA'] = sym(ga(nx), ga(ym - 9)) - x['gR0']
        x['SURP'] = sym(ga(nx), Es.get(nx, np.nan))          # 다음 분기 실제 vs 발표 직전 컨센서스(최종 서프라이즈)
        x['U'] = x['ORA'] - x['EA'] if 'EA' in x else np.nan   # 전망이 예상 못 한 가속도(성장률 차이라 분할 기준 무관)
        x['T_next'] = pd.Timestamp(er.loc[nx].report_date) if nx in er.index else pd.NaT
        # 미래 수익(SPY 대비)
        for nm, i0 in (('fast', ifast), ('safe', isafe)):
            for h in (21, 63):
                i1 = min(i0 + h, len(cal) - 1)
                if i0 >= len(cal) - 1: x[f'ex{h}_{nm}'] = np.nan; continue
                seg = p[i0:i1 + 1]; ok = np.where(np.isfinite(seg))[0]
                x[f'ex{h}_{nm}'] = (seg[ok[-1]] / p[i0] - 1) - (spy[i0 + ok[-1]] / spy[i0] - 1) if len(ok) >= 3 and np.isfinite(p[i0]) else np.nan
        rows.append(x)
P = pd.DataFrame(rows)
P['tq'] = P['T'].dt.year * 4 + (P['T'].dt.month - 1) // 3
P.to_parquet(S / 'ml_panel_us.parquet', index=False)
print('events', len(P), 'firms', P.tk.nunique(), 'period', P['T'].min().date(), P['T'].max().date())
print('coverage %:', (P.notna().mean() * 100).round(0).to_dict())
print('S&P 2008+ ever members', len(ever), 'with price', sum(t in col for t in ever))
