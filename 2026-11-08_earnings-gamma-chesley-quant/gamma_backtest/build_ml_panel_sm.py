"""중소형주(발표일에 S&P 500 비편입) 이벤트 패널. build_ml_panel.py와 같은 특징·목표, 가격은 EODHD 수정주가(배당 포함), 시장 = IWM(러셀2000).
필터: 진입가 $5 이상, 직전 20일 평균 거래대금 $100만 이상. 유동성 구간 liq = 직전 분기 거래대금 중앙값 기준 상(H)/하(L).
섹터 정보가 없어 금융업은 제외하지 못함(한계). 출력 ~/agent-fund-data/ml_panel_sm.parquet"""
import gzip, json, glob
import numpy as np, pandas as pd
from pathlib import Path
S = Path.home() / 'agent-fund-data'; E = S / 'eodhd'; PX = S / 'prices/eodhd'
sym = lambda a, b: (a - b) / ((np.abs(a) + np.abs(b)) / 2 + 1e-9)
mk = pd.read_parquet(PX / 'IWM.US.parquet'); mk['date'] = pd.to_datetime(mk.date); mk = mk.set_index('date').adjusted_close
cal = mk.index[mk.index >= '2005-01-01']; mkv = mk.reindex(cal).ffill().values
C = pd.read_csv(S / 'sp500_components.csv'); C['date'] = pd.to_datetime(C.date); C = C.sort_values('date')
md = C.date.values; ms = [set(x.replace('.', '-') for x in s.split(',')) for s in C.tickers]
def member(tk, d):
    i = np.searchsorted(md, np.datetime64(d), side='right') - 1; return i >= 0 and tk in ms[i]
def load(sub, code):
    f = E / sub / f'{code}.json.gz'; return pd.DataFrame(json.load(gzip.open(f, 'rt'))) if f.exists() else pd.DataFrame()
rows = []
files = sorted(glob.glob(str(PX / '*.US.parquet')))
for n_f, f in enumerate(files):
    code = Path(f).stem; tk = code[:-3]
    er = load('earnings', code)
    if er.empty: continue
    d = pd.read_parquet(f)
    if len(d) < 300: continue
    d['date'] = pd.to_datetime(d.date); d = d.set_index('date').reindex(cal)
    last = d.adjusted_close.last_valid_index()
    p = d.adjusted_close.ffill(); p[p.index > last] = np.nan; p = p.values
    dv = (d.close * d.volume).rolling(20, min_periods=10).mean().values
    R = np.r_[np.nan, p[1:] / p[:-1] - 1]
    er = er[er.date.notna() & er.report_date.notna()].copy(); er['ym'] = pd.to_datetime(er.date).dt.to_period('M')
    er = er.sort_values('report_date').drop_duplicates('ym', keep='last').set_index('ym').sort_index()
    A = pd.to_numeric(er.actual, errors='coerce'); Es = pd.to_numeric(er.estimate, errors='coerce').replace(0, np.nan)
    tr = load('trends', code)
    if not tr.empty:
        tr = tr[tr.period == '+1q'].copy(); tr['ym'] = pd.to_datetime(tr.date).dt.to_period('M'); tr = tr.drop_duplicates('ym', keep='last').set_index('ym')
        for c in tr.columns:
            if c not in ('code', 'date', 'period'): tr[c] = pd.to_numeric(tr[c], errors='coerce')
    ga = lambda ym: A.get(ym, np.nan); gR = lambda ym: sym(ga(ym), ga(ym - 12))
    for ym, r in er.iterrows():
        T = pd.Timestamp(r.report_date)
        if T < pd.Timestamp('2008-07-01') or not np.isfinite(ga(ym)) or member(tk, T): continue
        iT = cal.searchsorted(T)
        if iT >= len(cal) - 3 or iT < 260: continue
        ir = iT + 1 if (r.before_after_market == 'AfterMarket' and cal[iT] == T) else iT
        ifast, isafe = ir + 2, cal.searchsorted(T + pd.Timedelta(days=15))
        if ifast >= len(cal) or not np.isfinite(p[ifast]) or p[ifast] < 5 or not (dv[ir - 1] >= 1e6): continue
        x = dict(tk=tk, ym=str(ym), T=T, ir=ir, i_fast=ifast, i_safe=isafe, dvol=dv[ir - 1])
        x.update(gR0=gR(ym), gR1=gR(ym - 3), gR2=gR(ym - 6), gR3=gR(ym - 9)); x['acc0'] = x['gR0'] - x['gR1']; x['acc1'] = x['gR1'] - x['gR2']
        x['base_g'] = gR(ym - 9)
        sur = [sym(ga(ym - 3 * k), Es.get(ym - 3 * k, np.nan)) for k in range(8)]
        x.update(sur0=sur[0], sur1=sur[1], sur2=sur[2], sur3=sur[3])
        s8 = np.array(sur); x['beat8'] = np.nanmean(s8 > 0) if np.isfinite(s8).sum() >= 4 else np.nan
        g8 = np.array([gR(ym - 3 * k) for k in range(8)]); x['gvol8'] = np.nanstd(g8) if np.isfinite(g8).sum() >= 4 else np.nan
        rel = lambda a, b: (p[a] / p[b] - 1) - (mkv[a] / mkv[b] - 1) if a < len(p) and np.isfinite(p[a]) and np.isfinite(p[b]) else np.nan
        x['ear'] = rel(ir + 1, ir - 1); x['drift'] = rel(isafe, ir + 1) if isafe < len(p) else np.nan
        x['mom'] = p[ir - 21] / p[ir - 252] - 1 if np.isfinite(p[ir - 252]) else np.nan
        x['rev1m'] = p[ir - 1] / p[ir - 22] - 1; x['vol63'] = np.nanstd(R[ir - 63:ir])
        x['px_fast'] = p[ifast]; x['px_safe'] = p[isafe] if isafe < len(p) else np.nan
        nx = ym + 3
        if not tr.empty and nx in tr.index:
            t = tr.loc[nx]; cur = t.epsTrendCurrent; ya = t.earningsEstimateYearAgoEps; n = t.earningsEstimateNumberOfAnalysts
            x.update(gF=sym(cur, ya), rev90=sym(cur, t.epsTrend90daysAgo), rev30=sym(cur, t.epsTrend30daysAgo),
                     ra=sym(cur, t.epsTrend30daysAgo) - sym(t.epsTrend30daysAgo, t.epsTrend60daysAgo),
                     up30=t.epsRevisionsUpLast30days / n if n and n > 0 else np.nan, down30=t.epsRevisionsDownLast30days / n if n and n > 0 else np.nan,
                     disp=(t.earningsEstimateHigh - t.earningsEstimateLow) / (abs(cur) + 1e-9) if np.isfinite(cur) else np.nan, n_an=n, rgF=t.revenueEstimateGrowth)
            x['EA'] = x['gF'] - x['gR0']
        x['ORA'] = sym(ga(nx), ga(ym - 9)) - x['gR0']; x['SURP'] = sym(ga(nx), Es.get(nx, np.nan))
        x['U'] = x['ORA'] - x['EA'] if 'EA' in x else np.nan
        x['T_next'] = pd.Timestamp(er.loc[nx].report_date) if nx in er.index else pd.NaT
        for nm, i0 in (('fast', ifast), ('safe', isafe)):
            for h in (21, 63):
                if i0 >= len(cal) - 1: x[f'ex{h}_{nm}'] = np.nan; continue
                seg = p[i0:min(i0 + h, len(cal) - 1) + 1]; ok = np.where(np.isfinite(seg))[0]
                x[f'ex{h}_{nm}'] = (seg[ok[-1]] / p[i0] - 1) - (mkv[i0 + ok[-1]] / mkv[i0] - 1) if len(ok) >= 3 and np.isfinite(p[i0]) else np.nan
        rows.append(x)
    if n_f % 1000 == 0: print(n_f, len(rows), flush=True)
P = pd.DataFrame(rows); P['tq'] = P['T'].dt.year * 4 + (P['T'].dt.month - 1) // 3
P['liq'] = np.where(P.dvol >= P.groupby('tq').dvol.transform('median'), 'H', 'L')
P.to_parquet(S / 'ml_panel_sm.parquet', index=False)
print('events', len(P), 'firms', P.tk.nunique(), P['T'].min().date(), P['T'].max().date(), '| 전망 있음', P.EA.notna().mean().round(2))
