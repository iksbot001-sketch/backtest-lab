"""승자(+30% 초과) vs 패자(−20% 미만) 비교 + 다변량 표본외 검증 (WINNERS_PREREG.md 추가 등록)."""
import sys, json, time, warnings
import numpy as np, pandas as pd
from pathlib import Path
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import roc_auc_score
sys.path.insert(0, str(Path.home() / 'agent-fund/lib')); from dist_report import summary, text
warnings.filterwarnings('ignore')
O = Path.home() / 'agent-fund-data/refine'
BIN = {'정배열': lambda t: t['align'] == 1, '200일선 위': lambda t: t.d200 > 0, '52주 고가 90%+': lambda t: t.hi >= .9, '최근 골든크로스': lambda t: t.gc == 1,
       'RSI 50~70': lambda t: t.rsi.between(50, 70), 'RSI 70+': lambda t: t.rsi > 70, '거래량 1.5배+': lambda t: t.vr >= 1.5, '6개월 +20%+': lambda t: t.m6 > .2,
       '변동성 40% 미만': lambda t: t.vol63 * np.sqrt(252) < .4, '발표 반응 +': lambda t: t.ear > 0, '이익 성장 +': lambda t: t.gR0 > 0, '서프라이즈 +': lambda t: t.sur0 > 0, '주가 $10+': lambda t: t.px >= 10}
CONT = {'RSI': 'rsi', '52주 고가 대비': 'hi', '6개월 수익률': 'm6', '1개월 수익률': 'm1', '거래량 비율': 'vr', '20일선 이격': 'd20', '60일선 이격': 'd60', '120일선 이격': 'd120',
        '200일선 이격': 'd200', '연 변동성': 'vola', '주가(로그)': 'lpx', '거래대금(로그)': 'ldv', '이익 성장률': 'gR0', '이익 가속도': 'acc0', '서프라이즈': 'sur0', '발표 반응': 'ear'}
out = {}; reg = []
for nm, f in [('서프라이즈 예측', 'tr_sm_p_ridge_V0'), ('실현 감마', 'tr_sm_acc0_V0')]:
    t = pd.read_parquet(O / f'wf_{f}.parquet'); t = t[t.valid == 1].reset_index(drop=True)
    t['vola'] = t.vol63 * np.sqrt(252); t['lpx'] = np.log(t.px); t['ldv'] = np.log(t.dvol); t['yr'] = t.tq // 4; dis = t.yr < 2019
    for c in CONT.values():
        lo, hi = t[c].quantile([.01, .99]); t[c] = t[c].clip(lo, hi)
    res = {}
    for th, (wv, lv) in {'+30/-20': (.3, -.2), '+50/-50': (.5, -.5)}.items():
        W, L = t.ex > wv, t.ex < lv; rows = []
        for k, fn in BIN.items():
            x = fn(t).fillna(False)
            r = dict(feat=k, kind='bin', W=x[W].mean(), A=x.mean(), L=x[L].mean())
            for p, m in [('dis', dis), ('oos', ~dis)]: r[p] = x[W & m].mean() - x[L & m].mean()
            rows.append(r)
        for k, c in CONT.items():
            r = dict(feat=k, kind='cont', W=t[c][W].median(), A=t[c].median(), L=t[c][L].median())
            for p, m in [('dis', dis), ('oos', ~dis)]:
                a, b = t[c][W & m].dropna(), t[c][L & m].dropna(); r[p] = (a.mean() - b.mean()) / np.sqrt((a.var() + b.var()) / 2)
            r['strong'] = np.sign(r['dis']) == np.sign(r['oos']) and min(abs(r['dis']), abs(r['oos'])) >= .2
            rows.append(r)
        R = pd.DataFrame(rows); res[th] = R
        print(f'\n== {nm} {th}: 승자 {W.sum():,} ({W.mean() * 100:.0f}%) / 패자 {L.sum():,} ({L.mean() * 100:.0f}%) / 전체 {len(t):,}')
        b = R[R.kind == 'bin'].copy(); 
        for c in ['W', 'A', 'L', 'dis', 'oos']: b[c] = (b[c] * 100).round(1)
        print('이진(비율 %, 승자−패자 %p):'); print(b[['feat', 'W', 'A', 'L', 'dis', 'oos']].to_string(index=False))
        cc = R[R.kind == 'cont'][['feat', 'W', 'A', 'L', 'dis', 'oos', 'strong']]; print('연속(중앙값, 표준화 차이 d):'); print(cc.round(3).to_string(index=False))
    # 다변량: +30/-20 기준
    cols = list(CONT.values()) + ['align', 'gc']
    W, L = t.ex > .3, t.ex < -.2; tr = t[dis & (W | L)]; y = (tr.ex > .3).astype(int)
    med = tr[cols].median(); mu = tr[cols].fillna(med).mean(); sd = tr[cols].fillna(med).std()
    Z = lambda d: ((d[cols].fillna(med) - mu) / sd).values
    lr = LogisticRegression(C=0.1, max_iter=2000).fit(Z(tr), y); hg = HistGradientBoostingClassifier(max_depth=3, max_iter=200, learning_rate=.05, min_samples_leaf=100).fit(tr[cols], y)
    te = t[~dis].copy(); te['s_lr'] = lr.predict_proba(Z(te))[:, 1]; te['s_hg'] = hg.predict_proba(te[cols])[:, 1]
    wl = te[(te.ex > .3) | (te.ex < -.2)]; yy = (wl.ex > .3).astype(int)
    auc = {k: roc_auc_score(yy, wl[k]) for k in ['s_lr', 's_hg']}; auc_in = roc_auc_score(y, lr.predict_proba(Z(tr))[:, 1])
    coef = pd.Series(lr.coef_[0], index=[{v: k for k, v in CONT.items()}.get(c, {'align': '정배열', 'gc': '골든크로스'}.get(c)) for c in cols]).sort_values()
    print(f'\n다변량 {nm}: 학습 AUC {auc_in:.3f} / 표본외 AUC 로지스틱 {auc["s_lr"]:.3f}, HGB {auc["s_hg"]:.3f}'); print('로지스틱 계수(표준화):', coef.round(2).to_dict())
    for k in ['s_lr', 's_hg']:
        te['g'] = pd.qcut(te[k].rank(method='first'), 3, labels=['하', '중', '상'])
        d = te.groupby(['tq', 'g']).ex.mean().unstack(); q = (d['상'] - d['하']).dropna()
        print(f'  {k} 상−하 분기 평균 {q.mean() * 100:+.2f}%p t {q.mean() / q.std(ddof=1) * np.sqrt(len(q)):.2f}')
        for g in ['상', '중', '하']:
            m = te.g == g; print(text(summary(te.ex[m], groups=te.tq[m]), f'{nm} {k} 점수 {g} 1/3 (2019~)'))
        out.setdefault(nm, {})[k] = dict(auc=auc[k], dmean=q.mean(), t=q.mean() / q.std(ddof=1) * np.sqrt(len(q)))
    te[['tk', 'tq', 'i0', 'ex', 's_lr', 's_hg']].to_parquet(O / f'w2_scores_{f}.parquet', index=False)
    for th, R in res.items(): R.assign(set=nm, th=th).to_csv(O / f'w2_{f}_{th.replace("/", "_")}.csv', index=False)
    out[nm]['coef'] = coef.to_dict(); out[nm]['auc_in'] = auc_in
json.dump(out, open(O / 'w2.json', 'w'), ensure_ascii=False, indent=1, default=float)
with open(Path.home() / 'agent-fund/data/trial_registry.jsonl', 'a') as fh:
    for nm, d in out.items():
        for k in ['s_lr', 's_hg']: fh.write(json.dumps({'ts': time.strftime('%Y-%m-%dT%H:%M:%S'), 'study': 'gamma_backtest', 'trial': f'WIN2_{nm}_{k}', **{a: float(b) for a, b in d[k].items()}}, ensure_ascii=False) + '\n')
