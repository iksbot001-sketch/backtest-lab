"""정배열(종가>20>60>120일선) 진입 여부로 기존 거래를 나눠 분포·달력 기준 성과·MDD 비교. 출력 ~/agent-fund-data/refine/align_split.json"""
import json, numpy as np, pandas as pd, warnings
from pathlib import Path
from pxclean import clean
warnings.filterwarnings('ignore')
S = Path.home() / 'agent-fund-data'; O = S / 'refine'
mk = pd.read_parquet(S / 'prices/eodhd/IWM.US.parquet'); mk['date'] = pd.to_datetime(mk.date); mk = mk.set_index('date').adjusted_close
cal = mk.index[mk.index >= '2005-01-01']; mk = mk.reindex(cal)
SETS = {'원래 감마': 'tr_sm_acc0_V0', '서프라이즈': 'tr_sm_p_ridge_V0', '정교화 감마': 'tr_sm_acc0_V6r_noSL'}
TR = {k: pd.read_parquet(O / f'{v}.parquet') for k, v in SETS.items()}
tks = sorted(set().union(*[set(t.tk) for t in TR.values()]))
px = {}
for tk in tks:
    d = pd.read_parquet(S / f'prices/eodhd/{tk}.US.parquet'); d['date'] = pd.to_datetime(d.date); px[tk] = clean(d.set_index('date').adjusted_close)[0].reindex(cal)
px = pd.DataFrame(px)
ma = {w: px.rolling(w, min_periods=int(w * .9)).mean() for w in (20, 60, 120)}
AL = (((px > ma[20]) & (ma[20] > ma[60]) & (ma[60] > ma[120])).astype(float).where(ma[120].notna())).shift(1).values
last = px.apply(lambda c: c.last_valid_index()); pf = px.ffill()
for c, d in last.items():
    if d is not None: pf.loc[pf.index > d, c] = np.nan
P = pf.values; R = np.vstack([np.full(P.shape[1], np.nan), P[1:] / P[:-1] - 1]); mret = mk.pct_change().values; col = {c: j for j, c in enumerate(px.columns)}
dates = cal; N = len(cal)

def calendar(t):
    num = np.zeros(N); den = np.zeros(N)
    for r in t.itertuples():
        a, b = r.i0 + 1, r.i1 + 1; j = col[r.tk]
        if a >= N: continue
        num[a:b] += np.nan_to_num(R[a:b, j]); den[a:b] += 1; num[a] -= r.cost
    live = den > 0; first = np.argmax(live)
    ex = np.where(live, num / np.where(live, den, 1) - np.nan_to_num(mret), 0.0)[first:]; dd = dates[first:]
    cum = np.cumprod(1 + ex); mdd = (cum / np.maximum.accumulate(cum) - 1).min()
    # 총수익 기준 MDD(시장 포함, 실제 포트폴리오가 겪는 낙폭)
    raw = np.where(live, num / np.where(live, den, 1), 0.0)[first:]; cr = np.cumprod(1 + raw); mdd_raw = (cr / np.maximum.accumulate(cr) - 1).min()
    sub = lambda m: (ex[m].mean() * 252, ex[m].mean() / ex[m].std() * np.sqrt(m.sum()))
    a1, t1 = sub(dd.year < 2019); a2, t2 = sub(dd.year >= 2019)
    return dict(ann=ex.mean() * 252, t=ex.mean() / ex.std() * np.sqrt(len(ex)), mdd_ex=mdd, mdd_raw=mdd_raw, ann_pre=a1, t_pre=t1, ann_post=a2, t_post=t2,
                npos=den[first:][live[first:]].mean(), empty=1 - live[first:].mean())

def dstat(x):
    x = np.sort(x.values); n = len(x); k = max(1, int(n * .01))
    return dict(n=n, mean=x.mean(), med=np.median(x), win=(x > 0).mean(), p10=np.quantile(x, .1), p90=np.quantile(x, .9), skew=pd.Series(x).skew(), drop1=x[:-k].mean(), big_loss=(x <= -.2).mean(), big_win=(x >= .3).mean())

out = {}; rng = np.random.default_rng(0)
for name, t in TR.items():
    t = t.copy(); t['al'] = [AL[r.i0, col[r.tk]] if r.i0 < N else np.nan for r in t.itertuples()]; t['yr'] = t.tq // 4
    t = t[t.al.notna()]; t.to_parquet(O / f'al_{SETS[name]}.parquet', index=False)
    res = {}
    for g, m in [('전체', np.ones(len(t), bool)), ('정배열', t.al.values == 1), ('비정배열', t.al.values == 0)]:
        s = t[m]; res[g] = dict(all=dstat(s.ex), pre=dstat(s[s.yr < 2019].ex), post=dstat(s[s.yr >= 2019].ex), cal=calendar(s))
    # 대조: 같은 개수 무작위 부분집합 20회의 달력 MDD(종목 수가 줄어든 효과 분리)
    k = int((t.al == 1).sum()); res['무작위동수'] = dict(mdd_ex=[calendar(t.iloc[rng.choice(len(t), k, replace=False)])['mdd_ex'] for _ in range(20)])
    out[name] = res
    for g in ['전체', '정배열', '비정배열']:
        a, c = res[g]['all'], res[g]['cal']
        print(f"{name:6s} {g:4s} n{a['n']:5d} 평균{a['mean']*100:5.1f} 중앙{a['med']*100:5.1f} 승률{a['win']*100:4.0f} 하위10%{a['p10']*100:5.0f} 1%제외{a['drop1']*100:5.1f} -20%이하{a['big_loss']*100:3.0f}% "
              f"| 전{res[g]['pre']['mean']*100:5.1f}/{res[g]['pre']['win']*100:3.0f} 후{res[g]['post']['mean']*100:5.1f}/{res[g]['post']['win']*100:3.0f} "
              f"| 연{c['ann']*100:5.1f} t{c['t']:4.1f} 전{c['ann_pre']*100:5.1f} 후{c['ann_post']*100:5.1f} MDD초과{c['mdd_ex']*100:4.0f} MDD총{c['mdd_raw']*100:4.0f} 보유{c['npos']:4.0f} 공백{c['empty']*100:3.0f}%", flush=True)
    print('   무작위 동수 MDD초과 중앙', np.median(res['무작위동수']['mdd_ex']) * 100)
json.dump(out, open(O / 'align_split.json', 'w'), ensure_ascii=False, default=float, indent=1)
