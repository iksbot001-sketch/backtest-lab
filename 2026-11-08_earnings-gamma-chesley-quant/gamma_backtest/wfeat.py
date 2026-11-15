"""거래별 진입 전날 특징 계산·저장. 출력 ~/agent-fund-data/refine/wf_<trades>.parquet"""
import numpy as np, pandas as pd, warnings
from pathlib import Path
from pxclean import clean
warnings.filterwarnings('ignore')
S = Path.home() / 'agent-fund-data'; O = S / 'refine'
mk = pd.read_parquet(S / 'prices/eodhd/IWM.US.parquet'); mk['date'] = pd.to_datetime(mk.date); cal = mk.set_index('date').index[mk.date >= '2005-01-01']
sets = ['tr_sm_p_ridge_V0', 'tr_sm_acc0_V0']; TR = {k: pd.read_parquet(O / f'{k}.parquet') for k in sets}
need = {}
for k, t in TR.items():
    for r in t.itertuples(): need.setdefault(r.tk, set()).add(r.i0)
F = {}
for tk in need:
    d = pd.read_parquet(S / f'prices/eodhd/{tk}.US.parquet'); d['date'] = pd.to_datetime(d.date); d = d.set_index('date')
    c = clean(d.adjusted_close)[0].reindex(cal); v = d.volume.reindex(cal)
    ma = {w: c.rolling(w, min_periods=int(w * .9)).mean() for w in (20, 50, 60, 120, 200)}
    dl = c.diff(); up = dl.clip(lower=0).ewm(alpha=1 / 14, min_periods=14).mean(); dn = (-dl.clip(upper=0)).ewm(alpha=1 / 14, min_periods=14).mean()
    above = (ma[50] > ma[200]).astype(float).where(ma[200].notna())
    X = pd.DataFrame(dict(align=((c > ma[20]) & (ma[20] > ma[60]) & (ma[60] > ma[120])).astype(float), gc=(above.diff() == 1).rolling(60, min_periods=1).max(),
                          rsi=100 - 100 / (1 + up / dn), hi=c / c.rolling(252, min_periods=200).max(), m6=c / c.shift(126) - 1, m1=c / c.shift(21) - 1,
                          vr=v.rolling(20).mean() / v.rolling(120).mean(), d20=c / ma[20] - 1, d60=c / ma[60] - 1, d120=c / ma[120] - 1, d200=c / ma[200] - 1,
                          valid=ma[120].notna().astype(float))).shift(1)
    F[tk] = X.iloc[sorted(need[tk])]
for k, t in TR.items():
    X = pd.DataFrame([F[r.tk].loc[cal[r.i0]].values for r in t.itertuples()], columns=F[t.tk.iloc[0]].columns, index=t.index)
    pd.concat([t, X], axis=1).to_parquet(O / f'wf_{k}.parquet', index=False); print(k, len(t))
