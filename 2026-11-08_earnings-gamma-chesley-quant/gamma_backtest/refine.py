"""감마 전략 정교화 시험(REFINE_PREREG.md). 사용: python refine.py <sm|sp>
기본 신호마다 V0~V8 변형을 거래 단위·달력 기준 포트폴리오로 평가. 거래는 ~/agent-fund-data/refine/ 에 저장."""
import sys, json, time, glob, warnings
import numpy as np, pandas as pd
from pathlib import Path
from pxclean import clean
warnings.filterwarnings('ignore')
S = Path.home() / 'agent-fund-data'; OUT = S / 'refine'; OUT.mkdir(exist_ok=True)
U = sys.argv[1]; SM = U == 'sm'
T = pd.read_parquet(S / f'ml_pred_M1fast_SURP{"_sm" if SM else ""}.parquet').sort_values(['tk', 'T']).reset_index(drop=True)
T['mom'] = T.mom.replace([np.inf, -np.inf], np.nan)
px = {}
if SM:
    mk = pd.read_parquet(S / 'prices/eodhd/IWM.US.parquet'); mk['date'] = pd.to_datetime(mk.date); mk = mk.set_index('date').adjusted_close
    cal = mk.index[mk.index >= '2005-01-01']
    for tk in T.tk.unique():
        d = pd.read_parquet(S / f'prices/eodhd/{tk}.US.parquet'); d['date'] = pd.to_datetime(d.date); px[tk] = clean(d.set_index('date').adjusted_close)[0]
    px = pd.DataFrame(px).reindex(cal); px['MKT'] = mk.reindex(cal)
else:
    for f in glob.glob(str(S / 'prices/us/*.parquet')):
        d = pd.read_parquet(f); d = d[d.close > 0]
        if len(d): px[Path(f).stem] = clean(d.set_index('date').close)[0]
    px = pd.DataFrame(px).sort_index(); px.index = pd.to_datetime(px.index); px['MKT'] = px['SPY']
last = px.apply(lambda c: c.last_valid_index()); px = px.ffill()
for c, d in last.items():
    if d is not None and not pd.isna(d): px.loc[px.index > d, c] = np.nan
dates = px.index; N = len(px); col = {c: j for j, c in enumerate(px.columns)}; P = px.values
R = np.vstack([np.full(P.shape[1], np.nan), P[1:] / P[:-1] - 1]); mret = R[:, col['MKT']]; M = P[:, col['MKT']]
T = T[T.tk.isin(col)].reset_index(drop=True)

def deciles(c, mask=None):
    x = T[c].where(mask) if mask is not None else T[c]; X = T.assign(_x=x)
    cut = {tq: np.nanpercentile(g._x, np.arange(10, 100, 10)) for tq, g in X.groupby('tq') if g._x.notna().sum() >= (30 if mask is not None else 50)}
    return np.array([int(np.searchsorted(cut[t - 1], v)) + 1 if (t - 1) in cut and np.isfinite(v) else np.nan for t, v in zip(T.tq, x)])
gmed = T.groupby('tq').gvol8.median(); T['gv_ok'] = T.gvol8 <= T.tq.map(lambda t: gmed.get(t - 1, np.nan))
FILT = dict(Q=lambda g: (g.gR0 > 0) & (g.gR1 > 0), C=lambda g: (g.ear > 0) & (g.mom > 0), P=lambda g: g.gv_ok.astype(bool), R=lambda g: g.rev90 > 0)

def run(dec, filt='', stop=False, H=252, E=False, cm=1.0, start=2010, edec=None):
    edec = dec if edec is None else edec   # 진입 분위(edec==10), 청산은 전체 분위 dec ≤5
    ok = np.ones(len(T), bool)
    for f in filt: ok &= FILT[f](T).fillna(False).values
    tr = []
    for tk, idx in T.groupby('tk').indices.items():
        g = T.iloc[idx]; dg = dec[idx]; eg = edec[idx]; okg = ok[idx]; ie = g.i_fast.values.astype(int); j = col[tk]; s = P[:, j]; k = 0
        while k < len(g):
            if eg[k] != 10 or not okg[k] or g.tq.values[k] // 4 < start: k += 1; continue
            i0 = ie[k]; p0 = s[i0] if i0 < N else np.nan
            if not np.isfinite(p0) or p0 < 5: k += 1; continue
            i1 = min(i0 + H, N - 1); kk = k + 1; why = 'max'
            while kk < len(g) and ie[kk] <= i1:
                v = dg[kk]
                if np.isfinite(v) and v <= 5: i1 = ie[kk]; why = 'A'; break
                if E and np.isfinite(g.EA.values[kk]) and g.EA.values[kk] < 0: i1 = ie[kk]; why = 'E'; break
                kk += 1
            seg = s[i0:i1 + 1]; okp = np.where(np.isfinite(seg))[0]; i1 = i0 + okp[-1]
            if i1 < min(i0 + H, N - 1) and why == 'max': why = 'delist'
            if stop:
                rel = (s[i0:i1 + 1] / p0) / (M[i0:i1 + 1] / M[i0]) - 1; hit = np.where(rel <= -0.25)[0]
                if len(hit) and i0 + hit[0] + 1 < i1: i1 = i0 + hit[0] + 1; why = 'stop'
                if not np.isfinite(s[i1]): i1 -= 1
            p1 = s[i1]; rs, rm = p1 / p0 - 1, M[i1] / M[i0] - 1
            cost = cm * (2 * (0.001 if g.liq.values[k] == 'H' else 0.003) if SM else 2 * 0.00015 + 0.01 / p0 + 0.01 / p1)
            r = g.iloc[k]
            tr.append(dict(tk=tk, tq=r.tq, i0=i0, i1=i1, d=i1 - i0, why=why, rs=rs, rm=rm, cost=cost, ex=rs - rm - cost,
                           px=p0, dvol=r.get('dvol', np.nan), vol63=r.vol63, mom=r.mom, ear=r.ear, gR0=r.gR0, acc0=r.acc0, sur0=r.sur0, gvol8=r.gvol8, n_an=r.n_an, liq=r.get('liq', '')))
            while kk < len(g) and ie[kk] <= i1: kk += 1
            k = max(kk, k + 1)
    return pd.DataFrame(tr)

def calendar(t, w=False):
    num = np.zeros(N); den = np.zeros(N)
    for r in t.itertuples():
        a, b = r.i0 + 1, r.i1 + 1; j = col[r.tk]
        if a >= N: continue
        ww = 1 / max(r.vol63, 0.005) if w else 1.0
        x = np.nan_to_num(R[a:b, j]); num[a:b] += ww * x; den[a:b] += ww; num[a] -= ww * r.cost
    live = den > 0; ex = np.where(live, num / np.where(live, den, 1) - np.nan_to_num(mret), 0.0)
    first = np.argmax(live); ex = ex[first:]; dd = dates[first:]
    cum = np.cumprod(1 + ex); mdd = (cum / np.maximum.accumulate(cum) - 1).min()
    yr = pd.Series(ex, index=dd).groupby(dd.year).apply(lambda s: np.prod(1 + s) - 1)
    sub = lambda m: (ex[m].mean() * 252, ex[m].mean() / ex[m].std() * np.sqrt(m.sum()))
    a1, t1 = sub(dd.year < 2019); a2, t2 = sub(dd.year >= 2019)
    return dict(ann=ex.mean() * 252, ir=ex.mean() / ex.std() * np.sqrt(252), tcal=ex.mean() / ex.std() * np.sqrt(len(ex)), mdd=mdd,
                ann_pre=a1, t_pre=t1, ann_post=a2, t_post=t2, npos=den[first:][live[first:]].mean() if not w else np.nan), pd.Series(ex, index=dd), yr

tt = lambda s: s.mean() / s.std(ddof=1) * np.sqrt(len(s)) if len(s) > 2 else np.nan
def summ(t):
    q = t.groupby('tq').ex.mean(); top = t.ex.sort_values(ascending=False)
    return dict(n=len(t), hold=round(t.d.mean()), mean=t.ex.mean(), med=t.ex.median(), win=(t.ex > 0).mean(), t_trade=tt(q),
                top10=top.head(10).sum() / t.ex.sum() if t.ex.sum() > 0 else np.nan, skew=t.ex.skew(), kurt=t.ex.kurt(), stop=(t.why == 'stop').mean())

bases = {'acc0': 'B1 실현 감마', 'p_ridge': 'B2 서프라이즈 예측'} if SM else {'acc0': 'B3 실현 감마'}
VAR = [('V0', {}), ('V1', dict(filt='Q')), ('V2', dict(filt='C')), ('V3', dict(filt='P')), ('V4', dict(stop=True)), ('V5', dict(H=504)),
       ('V6', dict(filt='QCP', stop=True, H=504)), ('V7', dict(filt='QCP', stop=True, H=504)), ('V8', dict(filt='QCPR', stop=True, H=504, E=True, start=2017)),
       ('V0b', dict(start=2017)), ('V6x2', dict(filt='QCP', stop=True, H=504, cm=2.0))]
rows = []; series = {}
for b, bname in bases.items():
    dec = deciles(b); mq = FILT['Q'](T).fillna(False) & FILT['C'](T).fillna(False) & FILT['P'](T).fillna(False)
    VAR2 = VAR + [('V6r', dict(stop=True, H=504, edec=deciles(b, mq))), ('V6r_noSL', dict(edec=deciles(b, mq)))]   # 사후 수정: 필터 통과군 안에서 상위 10%
    for v, kw in VAR2:
        t = run(dec, **kw); t.to_parquet(OUT / f'tr_{U}_{b}_{v}.parquet', index=False)
        c, ser, yr = calendar(t, w=(v == 'V7')); series[f'{b}_{v}'] = ser
        rows.append(dict(base=bname, v=v, **summ(t), **c)); print(bname, v, 'n', len(t), 'mean %.2f%%' % (t.ex.mean() * 100), 'ann %.1f%% IR %.2f t %.2f' % (c['ann'] * 100, c['ir'], c['tcal']), flush=True)
r = pd.DataFrame(rows); r.to_csv(OUT / f'refine_{U}.csv', index=False); pd.DataFrame(series).to_parquet(OUT / f'cal_{U}.parquet')
with open(Path.home() / 'agent-fund' / 'data' / 'trial_registry.jsonl', 'a') as f:
    for x in rows: f.write(json.dumps({'ts': time.strftime('%Y-%m-%dT%H:%M:%S'), 'study': 'gamma_backtest', 'trial': f'REFINE_{U}_{x["base"]}_{x["v"]}', **{k: (round(float(v), 4) if isinstance(v, (float, np.floating)) else v) for k, v in x.items()}}, ensure_ascii=False) + '\n')
pd.set_option('display.width', 250); fm = r.copy()
for c in ['mean', 'med', 'win', 'top10', 'ann', 'mdd', 'ann_pre', 'ann_post', 'stop']: fm[c] = (fm[c] * 100).round(1)
for c in ['t_trade', 'skew', 'kurt', 'ir', 'tcal', 't_pre', 't_post', 'npos']: fm[c] = fm[c].round(2)
print(fm.to_string(index=False))
