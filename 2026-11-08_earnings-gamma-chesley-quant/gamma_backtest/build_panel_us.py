"""SEC companyfacts → 미국 분기 패널(point-in-time). 각 분기 t의 첫 공시일 f_t 시점에 알려진 값만으로
EPS_t, EPS_{t-1}, EPS_{t-4}, EPS_{t-5}를 잡아 He & Narayanamoorthy 정의의 성장률·가속도를 만든다.
분기값: 3개월(80~100일) 사실 그대로, 4분기는 연간 − 9개월 누적. 공시일 = 해당 기간 값이 처음 filed 된 날.
8-K Item 2.02(실적 발표) 날짜가 분기말 이후 ~ 첫 공시일 사이에 있으면 ann 열에 기록(발표일 진입 변형용)."""
import json, glob
import numpy as np, pandas as pd
from pathlib import Path
S = Path.home() / 'agent-fund-data'
CONC = {'eps': ['EarningsPerShareDiluted', 'EarningsPerShareBasicAndDiluted', 'EarningsPerShareBasic'],
        'ni': ['NetIncomeLoss'], 'op': ['OperatingIncomeLoss'],
        'sales': ['Revenues', 'RevenueFromContractWithCustomerExcludingAssessedTax', 'SalesRevenueNet']}
def facts(j, key):
    g = j.get('facts', {}).get('us-gaap', {}); out = []
    for c in CONC[key]:
        if c not in g: continue
        for unit, arr in g[c]['units'].items():
            for e in arr:
                if e.get('form') not in ('10-Q', '10-K', '10-Q/A', '10-K/A') or 'start' not in e: continue
                out.append((pd.Timestamp(e['start']), pd.Timestamp(e['end']), pd.Timestamp(e['filed']), float(e['val'])))
        if out: break                                       # 첫 번째로 존재하는 개념만 사용(혼용 방지)
    return pd.DataFrame(out, columns=['start', 'end', 'filed', 'val'])
def quarters(df):
    """(end, value, filed) 목록: 분기 3개월 값 + 4분기(연간−9개월). 각 (기간)의 filed 이력을 유지."""
    if df.empty: return pd.DataFrame(columns=['end', 'filed', 'val'])
    df = df.copy(); df['dur'] = (df.end - df.start).dt.days
    q = df[(df.dur >= 80) & (df.dur <= 100)][['end', 'filed', 'val']]
    fy = df[(df.dur >= 350) & (df.dur <= 380)]; nm = df[(df.dur >= 260) & (df.dur <= 290)]
    q4 = []
    for _, r in fy.iterrows():
        n = nm[(nm.start == r.start) & (nm.filed <= r.filed)]
        if len(n):
            n = n.sort_values('filed').iloc[-1]
            q4.append((r.end, r.filed, r.val - n.val))
    q = pd.concat([q, pd.DataFrame(q4, columns=['end', 'filed', 'val'])], ignore_index=True)
    q['end'] = pd.to_datetime(q.end); q['filed'] = pd.to_datetime(q.filed)
    q['end'] = q.end.dt.to_period('M').dt.to_timestamp('M')        # 회계분기말을 월말로 맞춤(52/53주 회계연도 보정)
    return q.sort_values(['end', 'filed'])
def asof(q, end, d):
    x = q[(q.end == end) & (q.filed <= d)]
    return x.val.iloc[-1] if len(x) else np.nan
def ann_dates(sub):
    try:
        rec = sub['filings']['recent']
        return sorted(pd.Timestamp(d) for f, d, it in zip(rec['form'], rec['filingDate'], rec.get('items', [''] * len(rec['form'])))
                      if f == '8-K' and '2.02' in str(it))
    except Exception: return []
m = json.load(open(S / 'us_ticker_cik.json'))
cik2t = {}
for t, c in m.items():
    if c: cik2t.setdefault(c, set()).add(t.split('-')[0])
rows = []
for f in glob.glob(str(S / 'sec' / 'facts' / '*.json')):
    cik = int(Path(f).stem); j = json.load(open(f))
    if not j: continue
    Q = {k: quarters(facts(j, k)) for k in CONC}
    sp = S / 'sec' / 'subs' / f'{cik}.json'
    ann = ann_dates(json.load(open(sp))) if sp.exists() else []
    qe = Q['eps']
    if qe.empty: continue
    first = qe.groupby('end').filed.min()
    for end, f0 in first.items():
        if end < pd.Timestamp('2008-01-01'): continue
        ends = {k: end - pd.offsets.MonthEnd(3 * k) for k in (1, 4, 5)}
        rec = {'cik': cik, 'ticker': sorted(cik2t.get(cik, {''}))[0], 'end': end, 'filed': f0}
        for k, q in Q.items():
            rec[k] = asof(q, end, f0); rec[k + '_l1'] = asof(q, ends[1], f0); rec[k + '_l4'] = asof(q, ends[4], f0); rec[k + '_l5'] = asof(q, ends[5], f0)
        a = [d for d in ann if end < d <= f0]
        rec['ann'] = a[0] if a else pd.NaT
        rows.append(rec)
P = pd.DataFrame(rows).sort_values(['cik', 'end']).reset_index(drop=True)
P.to_parquet(S / 'panel_us_raw.parquet', index=False)
print(P.shape, P.cik.nunique(), 'ann 커버리지', round(P.ann.notna().mean(), 3))
print(P.groupby(P.end.dt.year).size().to_dict())
print('지연(공시일-분기말) 중앙값', (P.filed - P.end).dt.days.median(), '| 발표일-분기말', (P.ann - P.end).dt.days.median())
