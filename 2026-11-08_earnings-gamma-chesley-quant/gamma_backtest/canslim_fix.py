"""CAN SLIM 결과에서 자료 오류 거래(LCI 2013-12, 하루 ×4 오류 시세) 제외 후 재계산. 달력 기준은 거래 종목 가격만 불러 계산."""
import sys, numpy as np, pandas as pd
from pathlib import Path
from pxclean import clean
sys.path.insert(0, str(Path.home() / 'agent-fund/lib')); from dist_report import summary, text
S = Path.home() / 'agent-fund-data'; C = S / 'canslim'
mk = pd.read_parquet(S / 'prices/eodhd/IWM.US.parquet'); mk['date'] = pd.to_datetime(mk.date); mk = mk.set_index('date').adjusted_close
cal = mk.index[mk.index >= '2005-01-01']; M = mk.reindex(cal).values; mret = np.r_[np.nan, M[1:] / M[:-1] - 1]; N = len(cal)
BAD = {('LCI', 8055)}
vs = ['S1_E1', 'S1_E2', 'S1_E3', 'noC', 'noA', 'noN', 'noS', 'noL', 'noM', 'S1_E1_x2']
TR = {v: pd.read_parquet(C / f'tr_{v}.parquet') for v in vs}
tks = sorted(set().union(*[set(t.tk) for t in TR.values()])); R = {}
for tk in tks:
    d = pd.read_parquet(S / f'prices/eodhd/{tk}.US.parquet'); d['date'] = pd.to_datetime(d.date)
    s = clean(d.set_index('date').adjusted_close)[0].reindex(cal); lv = s.last_valid_index(); s = s.ffill()
    if lv is not None: s[s.index > lv] = np.nan
    v = s.values; R[tk] = np.r_[np.nan, v[1:] / v[:-1] - 1]
def cal_metrics(t):
    num = np.zeros(N); den = np.zeros(N)
    for r in t.itertuples():
        a, b = r.i0 + 1, r.i1 + 1
        if a >= N: continue
        num[a:b] += np.nan_to_num(R[r.tk][a:b]); den[a:b] += 1; num[a] -= r.cost
    live = den > 0; ex = np.where(live, num / np.where(live, den, 1) - np.nan_to_num(mret), 0.0); f = np.argmax(live); ex = ex[f:]; dd = cal[f:]
    cum = np.cumprod(1 + ex); sub = lambda m: (ex[m].mean() * 252, ex[m].mean() / ex[m].std() * np.sqrt(m.sum()))
    a1, t1 = sub(dd.year < 2019); a2, t2 = sub(dd.year >= 2019)
    return dict(ann=ex.mean() * 252, ir=ex.mean() / ex.std() * np.sqrt(252), t=ex.mean() / ex.std() * np.sqrt(len(ex)), mdd=(cum / np.maximum.accumulate(cum) - 1).min(), ann_pre=a1, t_pre=t1, ann_post=a2, t_post=t2, npos=den[f:][live[f:]].mean())
rows = []
for v, t in TR.items():
    bad = np.array([(a, b) in BAD for a, b in zip(t.tk, t.tq)]); t2 = t[~bad]
    m = cal_metrics(t2); s = summary(t2.ex, groups=t2.tq)
    rows.append(dict(v=v, n=len(t2), removed=int(bad.sum()), mean=t2.ex.mean(), med=t2.ex.median(), drop1=s['drop_top'][1], beat30=s['beat_prob'][30], skew=s['skew'], stop=(t2.why == 'stop').mean(), **m))
    if v == 'S1_E1': print(text(s, 'S1_E1 (LCI 제외)')); t2.to_parquet(C / 'tr_S1_E1_fixed.parquet', index=False)
r = pd.DataFrame(rows); r.to_csv(C / 'canslim_fixed.csv', index=False)
fm = r.copy()
for c in ['mean', 'med', 'drop1', 'beat30', 'ann', 'mdd', 'ann_pre', 'ann_post', 'stop']: fm[c] = (fm[c] * 100).round(1)
print(fm.round(2).to_string(index=False))
