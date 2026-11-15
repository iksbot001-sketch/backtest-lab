"""가속도 예측 모델 워크포워드 학습·평가(ML_PREREG.md). 사용: python ml_model.py [M1fast|M1safe|M2safe]
출력: ~/agent-fund-data/ml_pred_<mode>.parquet, 콘솔 요약, trial_registry 기록."""
import sys, json, time, warnings
import numpy as np, pandas as pd
from pathlib import Path
from scipy.stats import spearmanr
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.linear_model import Ridge
warnings.filterwarnings('ignore')
S = Path.home() / 'agent-fund-data'
mode = sys.argv[1] if len(sys.argv) > 1 else 'M1fast'
TGT = sys.argv[2] if len(sys.argv) > 2 else 'ORA'   # ORA(사전 등록) | SURP(사후 추가: 다음 분기 서프라이즈)
entry = 'fast' if mode.endswith('fast') else 'safe'
EC = ['gR0', 'gR1', 'gR2', 'gR3', 'acc0', 'acc1', 'base_g', 'sur0', 'sur1', 'sur2', 'sur3', 'beat8', 'gvol8']
PX = ['ear', 'mom', 'rev1m', 'vol63'] + (['drift'] if entry == 'safe' else [])
TR = ['EA', 'gF', 'rev90', 'rev30', 'ra', 'up30', 'down30', 'disp', 'n_an', 'rgF']
F = EC + PX + (TR if mode.startswith('M2') else [])
import os
SM = os.environ.get('UNIV') == 'sm'   # 중소형주 표본(ml_panel_sm)
P = pd.read_parquet(S / ('ml_panel_sm.parquet' if SM else 'ml_panel_us.parquet'))
P = P[P[f'px_{entry}'] >= 5].reset_index(drop=True)
qstart = lambda tq: pd.Timestamp(year=tq // 4, month=(tq % 4) * 3 + 1, day=1)
first_test = 2010 * 4 + 2 if mode.startswith('M1') else 2019 * 4
tqs = sorted(t for t in P.tq.unique() if t >= first_test)
pred = {}
for tq in tqs:
    tr = P[(P.T_next < qstart(tq)) & P[TGT].notna()].copy()
    tr['y'] = tr.groupby('tq')[TGT].rank(pct=True)   # 감사 반영: 정답이 공개된 학습 표본 안에서만 순위
    if tr.tq.nunique() < 8: continue
    X = tr[F].values.astype(float); y = tr.y.values
    lo, hi = np.nanpercentile(X, 1, axis=0), np.nanpercentile(X, 99, axis=0)
    lo, hi = np.nan_to_num(lo, nan=-1e9), np.nan_to_num(hi, nan=1e9)
    med = np.nan_to_num(np.nanmedian(np.clip(X, lo, hi), axis=0), nan=0.0)
    def prep(Z):
        Z = np.clip(Z.astype(float), lo, hi); Z = np.where(np.isnan(Z), med, Z); return Z
    Xr = prep(X); mu, sd = Xr.mean(0), Xr.std(0) + 1e-9
    hgb = HistGradientBoostingRegressor(max_depth=3, learning_rate=0.05, max_iter=300, min_samples_leaf=200, l2_regularization=1.0, random_state=0).fit(X, y)
    rdg = Ridge(alpha=10.0).fit((Xr - mu) / sd, y)
    for t in (tq - 1, tq):
        Z = P[P.tq == t]
        if Z.empty: continue
        ph = hgb.predict(Z[F].values.astype(float)); pr = rdg.predict((prep(Z[F].values) - mu) / sd)
        for m, pv in (('hgb', ph), ('ridge', pr)):
            if t == tq - 1: pred.setdefault(('cut', m, tq), np.nanpercentile(pv, np.arange(10, 100, 10)))
            else:
                for idx, v in zip(Z.index, pv): pred[(m, idx)] = v
    if tq % 8 == 0: print('trained', tq // 4, 'Q', tq % 4 + 1, 'n_train', len(tr), flush=True)
T = P[P.tq.isin(tqs)].copy()
for m in ('hgb', 'ridge'):
    T['p_' + m] = [pred.get((m, i), np.nan) for i in T.index]
    T['dec_' + m] = [int(np.searchsorted(pred[('cut', m, t)], v)) + 1 if ('cut', m, t) in pred and np.isfinite(v) else np.nan for t, v in zip(T.tq, T['p_' + m])]
T = T[T.p_hgb.notna()].copy()
tag = mode + ('' if TGT == 'ORA' else '_' + TGT) + ('_sm' if SM else '')
T.to_parquet(S / f'ml_pred_{tag}.parquet', index=False)
tt = lambda s: s.mean() / s.std(ddof=1) * np.sqrt(len(s)) if len(s) > 2 else np.nan
split = 2019 if mode.startswith('M1') else 2022
print(f'\n=== {mode} 목표 {TGT}: 시험 {T["T"].min().date()}~{T["T"].max().date()}, 이벤트 {len(T)}, 분기 {T.tq.nunique()}, 특징 {len(F)}개, 표본외 기준 {split}~')
# 1) 예측력: 분기별 IC(실제 다음 분기 가속도와 순위상관)
print('\n[예측력] 분기별 스피어만 IC 평균 (t) | 전체 / 분할 이전 / 이후')
ics = {}
for s in ['p_hgb', 'p_ridge', 'EA', 'sur0', 'ear', 'acc0', 'gF', 'rev90', 'rev30', 'up30']:
    if T[s].notna().sum() < 500: continue
    ic = T.groupby('tq').apply(lambda g: spearmanr(g[s], g[TGT], nan_policy='omit')[0] if g[[s, TGT]].dropna().shape[0] > 30 else np.nan).dropna()
    ics[s] = ic; yr = ic.index // 4
    print(f'  {s:8s} {ic.mean():+.3f} (t={tt(ic):5.1f}) | {ic[yr < split].mean():+.3f} / {ic[yr >= split].mean():+.3f}  [{len(ic)}분기]')
if 'EA' in ics:
    common = ics['p_hgb'].index.intersection(ics['EA'].index)
    d = ics['p_hgb'][common] - ics['EA'][common]
    print(f'  모델(HGB) − 컨센서스(EA) IC 차이 {d.mean():+.3f} (t={tt(d):.1f}, {len(d)}분기)')
# 2) 이벤트 스터디
print('\n[분위 수익] SPY 대비, 분기 평균')
for m in ('hgb', 'ridge'):
    for h in (21, 63):
        c = f'ex{h}_{entry}'; x = T[T['dec_' + m].notna() & T[c].notna()]
        dm = x.groupby('dec_' + m)[c].mean() * 100
        hq = x.groupby('tq').apply(lambda g: g[g['dec_' + m] == 10][c].mean() - g[g['dec_' + m] == 1][c].mean()).dropna()
        lq = x.groupby('tq').apply(lambda g: g[g['dec_' + m] == 10][c].mean()).dropna()
        yr = hq.index // 4
        print(f'  {m:5s} {h:2d}일: ' + ' '.join(f'{v:5.2f}' for v in dm.values) + f' | D10−D1 {hq.mean()*100:5.2f}% t={tt(hq):4.1f} '
              f'(이전 {hq[yr<split].mean()*100:5.2f} t={tt(hq[yr<split]):4.1f} / 이후 {hq[yr>=split].mean()*100:5.2f} t={tt(hq[yr>=split]):4.1f}) | D10롱 {lq.mean()*100:5.2f}% t={tt(lq):4.1f}')
