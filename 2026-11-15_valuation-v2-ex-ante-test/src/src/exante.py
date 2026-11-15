import sys, random
from pathlib import Path
import numpy as np, pandas as pd
RUN = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RUN / 'src'))
import engine as E

R, TAX, LAG = 0.09, 0.21, 0.75
d = pd.read_csv(RUN / 'data/inputs.csv')
OUT = RUN / 'out'; OUT.mkdir(exist_ok=True)


def paths(r):
    g1 = r.g1c; g2 = 0.04 + 0.5 * (g1 - 0.04); g3 = 0.04 + 0.25 * (g1 - 0.04)
    a = r.rev0 * (1 + g1); b = a * (1 + g2); c = b * (1 + g3)
    return [r.rev0, a, b, c]


def m1_of(r):
    if pd.isna(r.gec) or r.ni0 <= 0: return r.m0
    m = r.m0 * (1 + r.gec) / (1 + r.g1c)
    return min(max(m, 0.5 * r.m0), 1.5 * r.m0)


def val(r, kind, h):
    if kind == 'O':
        rev, m = [r.rev0, r.rev1, r.rev2, r.rev3], [r.m1, r.m2, r.m3]
    else:
        if r.m0 <= 0: return np.nan
        rev = paths(r)
        mm = r.m0 if kind == 'E1' else m1_of(r)
        m = [mm] * 3
    return E.value([E.Seg(r.ticker, rev, m, TAX, r.sc)], R, h, lag=LAG, net_cash=r.net_cash) / r.mktcap


def hs(r):
    f = lambda h: val(r, 'E2', h)
    if np.isnan(f(0.5)): return np.nan
    if f(0.5) >= 1: return 0.5
    if f(100) < 1: return 100.0
    lo, hi = 0.5, 100.0
    for _ in range(60):
        mid = (lo + hi) / 2
        if f(mid) < 1: lo = mid
        else: hi = mid
    return (lo + hi) / 2


rows = list(d.itertuples(index=False))
d['VP_E1_4'] = [val(r, 'E1', 4) for r in rows]
d['VP_E2_4'] = [val(r, 'E2', 4) for r in rows]
d['VP_E2_8'] = [val(r, 'E2', 8) for r in rows]
d['VP_O_4'] = [val(r, 'O', 4) for r in rows]
d['hs_E2'] = [hs(r) for r in rows]
d['neg_hs_E2'] = -d.hs_E2
d['sy_fwd'] = d.rev1_cons / d.mktcap
d['rev1_real_g'] = d.rev1 / d.rev0 - 1
d.to_csv(OUT / 'panel.csv', index=False)

SIGS = ['VP_E1_4', 'VP_E2_4', 'VP_E2_8', 'VP_O_4', 'neg_hs_E2', 'ey_fwd', 'sy_fwd']
YRS = sorted(d.t.unique())
md = []
def mdtab(df, idx):
    df = df.reset_index() if idx else df
    fm = lambda v: ('' if pd.isna(v) else (f'{v:.4f}' if isinstance(v, (float, np.floating)) else str(v)))
    L = ['| ' + ' | '.join(map(str, df.columns)) + ' |', '|' + '---|' * len(df.columns)]
    for r in df.itertuples(index=False): L.append('| ' + ' | '.join(fm(v) for v in r) + ' |')
    return '\n'.join(L)

def emit(title, df, idx=True):
    df.to_csv(OUT / (title.split(' ')[0] + '.csv'), index=idx)
    md.append(f'\n### {title}\n'); md.append(mdtab(df, idx))

def tert(g, s):
    x = g.dropna(subset=[s, 'ex'])
    if len(x) < 6: return None
    q = pd.qcut(x[s].rank(method='first'), 3, labels=['low', 'mid', 'high'])
    return x.groupby(q, observed=True)['ex'].agg(['mean', 'median', 'count'])

def tableA(df, s, exc, yrs):
    df = df.assign(ex=df[exc])
    rec = []
    for y in yrs:
        t = tert(df[df.t == y], s)
        if t is None: continue
        rec.append(dict(t=y, low_mean=t.loc['low', 'mean'], mid_mean=t.loc['mid', 'mean'], high_mean=t.loc['high', 'mean'],
                        low_med=t.loc['low', 'median'], mid_med=t.loc['mid', 'median'], high_med=t.loc['high', 'median'],
                        n_low=t.loc['low', 'count'], n_high=t.loc['high', 'count']))
    A = pd.DataFrame(rec).set_index('t')
    A['spread_mean'] = A.high_mean - A.low_mean
    A['spread_med'] = A.high_med - A.low_med
    avg = A.mean(); avg['n_low'] = A.n_low.sum(); avg['n_high'] = A.n_high.sum()
    A.loc['avg'] = avg
    A.loc['pos_years'] = np.nan
    A.loc['pos_years', 'spread_mean'] = (A.loc[YRS_of(A), 'spread_mean'] > 0).sum()
    A.loc['pos_years', 'spread_med'] = (A.loc[YRS_of(A), 'spread_med'] > 0).sum()
    return A

def YRS_of(A): return [i for i in A.index if i not in ('avg', 'pos_years')]

def tableB(df, s):
    ic = {}
    for y in YRS:
        x = df[df.t == y].dropna(subset=[s, 'ex3'])
        if len(x) >= 10: ic[y] = x[s].corr(x.ex3, method='spearman')
    v = pd.Series(ic)
    return v, v.mean(), v.std(ddof=1), v.mean() / (v.std(ddof=1) / np.sqrt(len(v)))

# sector neutral
d['n_sec'] = d.groupby(['t', 'sector']).ticker.transform('count')
dn = d[d.n_sec >= 5].copy()
for s in SIGS:
    dn[s] = dn.groupby(['t', 'sector'])[s].rank(pct=True).where(dn[s].notna())

res = {}
for tag, df in (('', d), ('_neut', dn)):
    ics = {}
    for s in SIGS:
        A3 = tableA(df, s, 'ex3', YRS); emit(f'A{tag}_ex3_{s} 3분위 초과수익 ({"업종중립" if tag else "전체"}) ex3', A3)
        A5 = tableA(df, s, 'ex5', [y for y in YRS if y <= 2020]); emit(f'A{tag}_ex5_{s} 3분위 초과수익 ({"업종중립" if tag else "전체"}) ex5', A5)
        v, m, sd, tstat = tableB(df, s)
        ics[s] = dict(**{str(y): v.get(y, np.nan) for y in YRS}, mean=m, std=sd, tstat=tstat)
        res[(tag, s)] = (A3, m)
    emit(f'B{tag}_IC 순위상관(IC) ({"업종중립" if tag else "전체"})', pd.DataFrame(ics).T)

# D
d['tech'] = d.sector.isin(['Technology', 'Communication Services'])
d['hiroic'] = d.groupby('t').roic.transform(lambda x: x >= x.quantile(2 / 3)) & d.roic.notna()
rec = []
for y in YRS:
    g = d[d.t == y]
    for name, gg in (('all', g), ('tech', g[g.tech]), ('hiroic', g[g.hiroic])):
        rec.append(dict(t=y, group=name, n=len(gg), pass_E2_4=(gg.VP_E2_4 >= 1).sum() / gg.VP_E2_4.notna().sum(),
                        pass_O_4=(gg.VP_O_4 >= 1).sum() / gg.VP_O_4.notna().sum()))
emit('D_pass 통과율', pd.DataFrame(rec), idx=False)
# E
emit('E_corr 신호 사이 스피어만 상관', d[SIGS].corr(method='spearman'))
# F
rec = []
for y in YRS:
    g = d[d.t == y]
    rec.append(dict(t=y, n=len(g), mean_diff=(g.g1c - g.rev1_real_g).mean(), corr=g.g1c.corr(g.rev1_real_g)))
emit('F_consensus 컨센서스 오차 (g1c − 실현)', pd.DataFrame(rec), idx=False)

def hyp(tag):
    A = res[(tag, 'VP_E2_4')][0]
    sp = A.loc[YRS_of(A), 'spread_mean']
    return bool(A.loc['avg', 'spread_mean'] > 0 and (sp > 0).sum() >= 5 and len(sp) == 6)
H1, H3 = hyp(''), hyp('_neut')
H2 = res[('', 'VP_E2_4')][1] > res[('', 'ey_fwd')][1]
f = lambda b: '충족' if b else '미충족'
head = f'# REPORT\n\n- H1: {f(H1)}\n- H2: {f(H2)}\n- H3: {f(H3)}\n'
(OUT / 'REPORT.md').write_text(head + '\n'.join(md) + '\n')
print(head); print({s: round(res[('', s)][1], 4) for s in SIGS}); print({s: round(res[('_neut', s)][1], 4) for s in SIGS})
print('blank', d[['VP_E1_4', 'VP_E2_4', 'VP_E2_8', 'VP_O_4', 'hs_E2', 'ey_fwd', 'sy_fwd']].isna().sum().to_dict(), len(d), len(dn))
