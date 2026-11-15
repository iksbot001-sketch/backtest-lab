"""큰 승자 공통점 연구(WINNERS_PREREG.md). 진입 전날까지의 기술적·재무 특징 → 공통점·향상도·표본외."""
import sys, json, time, warnings
import numpy as np, pandas as pd
from pathlib import Path
from pxclean import clean
sys.path.insert(0, str(Path.home() / 'agent-fund/lib')); from dist_report import summary, text
warnings.filterwarnings('ignore')
S = Path.home() / 'agent-fund-data'; O = S / 'refine'
mk = pd.read_parquet(S / 'prices/eodhd/IWM.US.parquet'); mk['date'] = pd.to_datetime(mk.date); cal = mk.set_index('date').index[mk.date >= '2005-01-01']
sets = {'서프라이즈 예측': 'tr_sm_p_ridge_V0', '실현 감마': 'tr_sm_acc0_V0'}
TR = {k: pd.read_parquet(O / f'{v}.parquet') for k, v in sets.items()}
tks = sorted(set().union(*[set(t.tk) for t in TR.values()])); F = {}
for n_, tk in enumerate(tks):
    d = pd.read_parquet(S / f'prices/eodhd/{tk}.US.parquet'); d['date'] = pd.to_datetime(d.date); d = d.set_index('date')
    c = clean(d.adjusted_close)[0].reindex(cal); v = d.volume.reindex(cal)
    ma = {w: c.rolling(w, min_periods=int(w * .9)).mean() for w in (20, 50, 60, 120, 200)}
    dl = c.diff(); up = dl.clip(lower=0).ewm(alpha=1 / 14, min_periods=14).mean(); dn = (-dl.clip(upper=0)).ewm(alpha=1 / 14, min_periods=14).mean(); rsi = 100 - 100 / (1 + up / dn)
    above = (ma[50] > ma[200]).astype(float).where(ma[200].notna()); gc = (above.diff() == 1).rolling(60, min_periods=1).max()
    F[tk] = pd.DataFrame(dict(T1=(c > ma[20]) & (ma[20] > ma[60]) & (ma[60] > ma[120]), T2=c > ma[200], hi=c / c.rolling(252, min_periods=200).max(), T4=gc == 1, rsi=rsi,
                              vr=v.rolling(20).mean() / v.rolling(120).mean(), m6=c / c.shift(126) - 1, valid=ma[120].notna())).shift(1).values   # 진입 전날 기준
cols = ['T1', 'T2', 'hi', 'T4', 'rsi', 'vr', 'm6', 'valid']
def feats(t):
    X = np.array([F[r.tk][r.i0] for r in t.itertuples()], dtype=float); X = pd.DataFrame(X, columns=cols, index=t.index)
    out = pd.DataFrame(index=t.index)
    out['T1 정배열'] = X.T1 == 1; out['T2 200일선 위'] = X.T2 == 1; out['T3 52주 고가 90%+'] = X.hi >= .9; out['T4 최근 골든크로스'] = X.T4 == 1
    out['T5 RSI 50~70'] = X.rsi.between(50, 70); out['T6 RSI 70+'] = X.rsi > 70; out['T7 거래량 1.5배+'] = X.vr >= 1.5; out['T8 6개월 +20%+'] = X.m6 > .2
    out['T9 변동성 40% 미만'] = t.vol63 * np.sqrt(252) < .4; out['F1 발표 반응 +'] = t.ear > 0; out['F2 이익 성장 +'] = t.gR0 > 0; out['F3 서프라이즈 +'] = t.sur0 > 0; out['F4 주가 $10+'] = t.px >= 10
    return out, X.valid == 1
res = []; keep = {}
for nm, t in TR.items():
    f, ok = feats(t); t = t[ok]; f = f[ok]; t['yr'] = t.tq // 4; W, L = t.ex > .5, t.ex < -.5
    print(f'\n== {nm}: {len(t):,}건 (큰 승자 {W.sum():,} = {W.mean() * 100:.1f}%, 큰 패자 {L.sum():,} = {L.mean() * 100:.1f}%)')
    for c in f.columns:
        x = f[c].fillna(False).values
        r = dict(set=nm, feat=c, share_all=x.mean(), share_win=x[W].mean(), share_loss=x[L].mean())
        for per, m in [('dis', t.yr < 2019), ('oos', t.yr >= 2019)]:
            m = m.values; a, b = t.ex[m & x], t.ex[m & ~x]
            q = (t[m & x].groupby('tq').ex.mean() - t[m & ~x].groupby('tq').ex.mean()).dropna()
            r.update({f'{per}_n': len(a), f'{per}_dmean': a.mean() - b.mean(), f'{per}_dmed': a.median() - b.median(), f'{per}_mean': a.mean(),
                      f'{per}_winlift': (a > .5).mean() / max((t.ex[m] > .5).mean(), 1e-9), f'{per}_losslift': (a < -.5).mean() / max((t.ex[m] < -.5).mean(), 1e-9),
                      f'{per}_tdiff': q.mean() / q.std(ddof=1) * np.sqrt(len(q)) if len(q) > 2 else np.nan})
        r['adopt'] = r['dis_dmean'] >= .02 and r['dis_dmed'] >= 0 and r['dis_losslift'] <= 1
        res.append(r)
    R = pd.DataFrame([x for x in res if x['set'] == nm]); keep[nm] = list(R[R.adopt].feat)
    show = R[['feat', 'share_win', 'share_all', 'share_loss', 'dis_dmean', 'dis_dmed', 'dis_winlift', 'dis_losslift', 'adopt', 'oos_dmean', 'oos_dmed', 'oos_tdiff', 'oos_n']].copy()
    for c in ['share_win', 'share_all', 'share_loss', 'dis_dmean', 'dis_dmed', 'oos_dmean', 'oos_dmed']: show[c] = (show[c] * 100).round(1)
    print(show.round(2).to_string(index=False)); print('채택:', keep[nm])
    if keep[nm]:
        m = f[keep[nm]].fillna(False).all(axis=1).values; o = (t.yr >= 2019).values
        for lab, mm in [('조합 2019~', m & o), ('나머지 2019~', ~m & o), ('조합 전체', m)]:
            s = summary(t.ex[mm], groups=t.tq[mm]); print(text(s, f'{nm} {lab}'))
        t[m].to_parquet(O / f'win_{sets[nm]}_combo.parquet', index=False)
pd.DataFrame(res).to_csv(O / 'winners.csv', index=False); json.dump(keep, open(O / 'winners_keep.json', 'w'), ensure_ascii=False)
with open(Path.home() / 'agent-fund/data/trial_registry.jsonl', 'a') as fh:
    for x in res: fh.write(json.dumps({'ts': time.strftime('%Y-%m-%dT%H:%M:%S'), 'study': 'gamma_backtest', 'trial': f'WIN_{x["set"]}_{x["feat"]}', **{k: (round(float(v), 4) if isinstance(v, (float, np.floating)) else (bool(v) if isinstance(v, (bool, np.bool_)) else v)) for k, v in x.items()}}, ensure_ascii=False) + '\n')
