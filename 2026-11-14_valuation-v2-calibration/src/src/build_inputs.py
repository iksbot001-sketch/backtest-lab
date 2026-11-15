"""입력 패널 만들기 (Claude Code 작성, 2026-11-14). 샌드박스 밖 자료(~/agent-fund-data)를 읽어 data/inputs.csv 로 정리한다.
정의는 TASK_A.md '관측 단위'·'엔진 입력' 그대로. 엔진 계산과 집계는 Antigravity가 한다."""
import gzip, json, sys
from pathlib import Path
import numpy as np, pandas as pd

S = Path.home() / 'agent-fund-data'
RUN = Path(__file__).resolve().parents[1]
(RUN / 'data').mkdir(exist_ok=True)
EXC = {'Financial Services', 'Real Estate', 'Utilities'}
f = lambda x: float(x) if x not in (None, '', 'None') else np.nan


def prices(t):
    p = S / 'prices/eodhd' / f'{t}.US.parquet'
    if not p.exists(): return None
    d = pd.read_parquet(p)[['date', 'close', 'adjusted_close']].dropna()
    d['date'] = pd.to_datetime(d['date']); d = d.sort_values('date').reset_index(drop=True)
    d = d[(d.close > 0) & (d.adjusted_close > 0)]
    if len(d) < 300: return None
    ratio = (d.close / d.adjusted_close).values
    step = ratio[1:] / ratio[:-1]                       # 분할이 있던 날 크게 뛴다(배당은 몇 % 이내)
    fac = np.where((step > 1.2) | (step < 0.8), step, 1.0)
    # 그날 이후(다음 날부터) 일어난 비율 변화의 누적 곱: close × 누적 곱 = 현재 주식 수 기준 주가
    after = np.concatenate([np.cumprod(fac[::-1])[::-1], [1.0]])
    d['px_split'] = d.close.values * after            # 분할 전 주가는 비율이 1/n로 뛰므로 곱한다
    return d.set_index('date')


spy = None
for cand in (S / 'prices/eodhd/SPY.US.parquet', S / 'prices/us/SPY.parquet'):
    if cand.exists():
        x = pd.read_parquet(cand); x['date'] = pd.to_datetime(x['date'])
        col = 'adjusted_close' if 'adjusted_close' in x else 'close'
        spy = x.sort_values('date').set_index('date')[col]; print('SPY', cand.name, spy.index[0].date(), spy.index[-1].date()); break


def fwd(series, d0, years):
    d1 = d0 + pd.DateOffset(years=years)
    if d1 > series.index[-1]: return np.nan
    a = series[series.index >= d0]; b = series[series.index >= d1]
    return b.iloc[0] / a.iloc[0] - 1 if len(a) and len(b) else np.nan


rows, skip = [], {}
def sk(k): skip[k] = skip.get(k, 0) + 1
files = sorted((S / 'eodhd/fund').glob('*.US.json.gz'))
delisted = 0
for i, fp in enumerate(files):
    t = fp.name.split('.US')[0]
    try: d = json.load(gzip.open(fp))
    except Exception: sk('재무 파일 오류'); continue
    g = d.get('General') or {}
    if g.get('Type') != 'Common Stock': sk('보통주 아님'); continue
    if g.get('Sector') in EXC: sk('제외 섹터'); continue
    px = prices(t)
    if px is None: sk('가격 없음'); continue
    if px.index[-1] < pd.Timestamp('2026-01-01'): delisted += 1
    fin = d.get('Financials') or {}
    inc = (fin.get('Income_Statement') or {}).get('yearly') or {}
    bal = (fin.get('Balance_Sheet') or {}).get('yearly') or {}
    sh = {int(v['date']): f(v.get('shares')) for v in ((d.get('outstandingShares') or {}).get('annual') or {}).values() if str(v.get('date', '')).isdigit()}
    ys = sorted(inc)
    for j, y in enumerate(ys):
        fy = pd.Timestamp(y)
        if not (pd.Timestamp('2005-01-01') <= fy <= pd.Timestamp('2022-12-31')): continue
        if j + 3 >= len(ys): sk('t+3 없음'); continue
        nxt = ys[j + 1:j + 4]
        if any(abs((pd.Timestamp(nxt[k]) - fy).days - 365 * (k + 1)) > 45 for k in range(3)): sk('회계연도 간격 이상'); continue
        rev = [f(inc[y].get('totalRevenue'))] + [f(inc[n].get('totalRevenue')) for n in nxt]
        op = [f(inc[y].get('operatingIncome'))] + [f(inc[n].get('operatingIncome')) for n in nxt]
        b = bal.get(y) or {}
        eq = f(b.get('totalStockholderEquity')); debt = f(b.get('shortLongTermDebtTotal'))
        if np.isnan(debt):
            lt, st = f(b.get('longTermDebt')), f(b.get('shortTermDebt'))
            debt = np.nansum([lt, st]) if not (np.isnan(lt) and np.isnan(st)) else 0.0
        cash = f(b.get('cashAndShortTermInvestments'))
        if np.isnan(cash): cash = f(b.get('cash'))
        if any(np.isnan(v) for v in rev + op) or np.isnan(eq) or np.isnan(cash): sk('값 누락'); continue
        if min(rev) <= 0: sk('매출 0 이하'); continue
        m = [op[k] / rev[k] for k in (1, 2, 3)]
        if np.mean(m) <= 0.03: sk('평균 이익률 3% 이하'); continue
        ev = fy + pd.Timedelta(days=90)
        pe = px[px.index >= ev]
        if not len(pe) or (pe.index[0] - ev).days > 10: sk('평가일 가격 없음'); continue
        d0 = pe.index[0]
        shares = sh.get(fy.year) or sh.get(fy.year - 1) or np.nan
        if not shares or np.isnan(shares): sk('주식 수 없음'); continue
        mc = shares * pe.px_split.iloc[0]
        if mc < 2e9: sk('시총 20억 달러 미만'); continue
        ic = eq + debt - cash
        sc = 5.0 if ic <= 0 else float(np.clip(rev[0] / ic, 0.3, 5.0))
        r3, r5 = fwd(px.adjusted_close, d0, 3), fwd(px.adjusted_close, d0, 5)
        s3, s5 = (fwd(spy, d0, 3), fwd(spy, d0, 5)) if spy is not None and d0 >= spy.index[0] else (np.nan, np.nan)
        rows.append(dict(ticker=t, sector=g.get('Sector'), t=fy.year, fy_end=y, eval_date=d0.date(), mktcap=mc,
                         rev0=rev[0], rev1=rev[1], rev2=rev[2], rev3=rev[3], m1=m[0], m2=m[1], m3=m[2], sc=sc,
                         roic=(op[0] * 0.79 / ic if ic > 0 else np.nan), net_cash=cash - debt,
                         rev_cagr3=(rev[3] / rev[0]) ** (1 / 3) - 1, m_avg=float(np.mean(m)),
                         ret3=r3, ret5=r5, spy3=s3, spy5=s5, ex3=r3 - s3, ex5=r5 - s5))
    if i % 500 == 0: print(i, len(rows), flush=True)

df = pd.DataFrame(rows)
df.to_csv(RUN / 'data/inputs.csv', index=False)
print('관측', len(df), '종목', df.ticker.nunique(), '상장폐지(가격이 2026년 전에 끝남) 종목', delisted)
print('제외', skip)
print(df.groupby('t').size().to_dict())
# 검증 관문 1: 시가총액 점검
def mcap_on(t, date):
    px = prices(t); d = json.load(gzip.open(S / 'eodhd/fund' / f'{t}.US.json.gz'))
    sh = {int(v['date']): f(v.get('shares')) for v in d['outstandingShares']['annual'].values()}
    p = px[px.index <= pd.Timestamp(date)].px_split.iloc[-1]
    return sh[pd.Timestamp(date).year] * p / 1e9
for t, dt, ref in (('AAPL', '2015-12-31', 580), ('MSFT', '2019-12-31', 1200), ('NVDA', '2020-12-31', 320)):
    v = mcap_on(t, dt); print(f'관문1 {t} {dt}: {v:,.0f} (기준 {ref}, {v / ref - 1:+.0%})')
