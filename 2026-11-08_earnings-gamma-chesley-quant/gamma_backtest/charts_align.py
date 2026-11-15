"""정배열 분할 차트 + 정배열-비정배열 차이의 분기 군집 t. 출력 scratchpad charts3/"""
import json, sys, numpy as np, pandas as pd, matplotlib
matplotlib.use('Agg'); import matplotlib.pyplot as plt
from pathlib import Path
plt.rcParams['font.family'] = 'Apple SD Gothic Neo'; plt.rcParams['axes.unicode_minus'] = False
O = Path.home() / 'agent-fund-data/refine'; D = Path(sys.argv[1]); D.mkdir(exist_ok=True)
SETS = {'원래 감마': 'tr_sm_acc0_V0', '서프라이즈': 'tr_sm_p_ridge_V0', '정교화 감마': 'tr_sm_acc0_V6r_noSL'}
J = json.load(open(O / 'align_split.json'))
fig, ax = plt.subplots(2, 3, figsize=(16, 8.6), gridspec_kw=dict(height_ratios=[3, 2]))
NAV, ORG, GRY = '#14213D', '#C4621F', '#9AA3B2'
for i, (name, f) in enumerate(SETS.items()):
    t = pd.read_parquet(O / f'al_{f}.parquet'); x = t.ex.clip(-1, 1.5)
    q = t.groupby(['tq', 'al']).ex.mean().unstack().dropna(); dq = q[1.0] - q[0.0]; tq = dq.mean() / dq.std() * np.sqrt(len(dq))
    pre = dq[dq.index // 4 < 2019]; post = dq[dq.index // 4 >= 2019]
    print(name, '분기 차이 %.2f%%p t %.2f | 전 %.2f(t %.2f) 후 %.2f(t %.2f)' % (dq.mean() * 100, tq, pre.mean() * 100, pre.mean() / pre.std() * np.sqrt(len(pre)), post.mean() * 100, post.mean() / post.std() * np.sqrt(len(post))))
    b = np.linspace(-1, 1.5, 51); a = ax[0, i]
    for g, c, lab in [(0.0, GRY, '비정배열'), (1.0, ORG, '정배열')]:
        s = x[t.al == g]; a.hist(s, bins=b, density=True, histtype='stepfilled' if g == 0 else 'step', color=c, alpha=.45 if g == 0 else 1, lw=2.2, label=f'{lab} n={len(s):,}')
        a.axvline(np.median(t.ex[t.al == g]), color=c, ls='--', lw=1.5)
    a.axvline(0, color=NAV, lw=.8); a.set_title(f'{name}: 거래별 초과수익 분포', fontsize=14, color=NAV, loc='left')
    a.set_xlabel('초과수익 (점선=중앙값)'); a.legend(frameon=False, fontsize=10); a.set_yticks([])
    for s in ['top', 'right', 'left']: a.spines[s].set_visible(False)
    a = ax[1, i]; r = J[name]; labs = ['연 초과수익', '초과 MDD', '총 MDD']
    v1 = [r['정배열']['cal']['ann'], r['정배열']['cal']['mdd_ex'], r['정배열']['cal']['mdd_raw']]
    v0 = [r['비정배열']['cal']['ann'], r['비정배열']['cal']['mdd_ex'], r['비정배열']['cal']['mdd_raw']]
    va = [r['전체']['cal']['ann'], r['전체']['cal']['mdd_ex'], r['전체']['cal']['mdd_raw']]
    X = np.arange(3); w = .26
    for k, (v, c, lab) in enumerate([(va, NAV, '전체'), (v0, GRY, '비정배열'), (v1, ORG, '정배열')]):
        bars = a.bar(X + (k - 1) * w, np.array(v) * 100, w * .92, color=c, label=lab)
        for bb, vv in zip(bars, v): a.text(bb.get_x() + bb.get_width() / 2, vv * 100 + (1 if vv >= 0 else -1), f'{vv*100:.0f}', ha='center', va='bottom' if vv >= 0 else 'top', fontsize=9, color=NAV)
    rm = np.median(r['무작위동수']['mdd_ex']) * 100; a.plot([1 + w - w / 2, 1 + w + w / 2], [rm, rm], color='k', lw=2); a.text(1 + w + w / 2 + .02, rm, f'같은 수 무작위 {rm:.0f}', fontsize=8.5, va='center')
    a.set_xticks(X); a.set_xticklabels(labs); a.axhline(0, color=NAV, lw=.8); a.set_ylabel('%'); a.legend(frameon=False, fontsize=9, ncol=3, loc='lower left')
    for s in ['top', 'right']: a.spines[s].set_visible(False)
fig.suptitle('정배열(종가>20>60>120일선)로 진입한 거래 vs 아닌 거래 · 미국 중소형 2010~2025', fontsize=16, color=NAV, x=.01, ha='left')
fig.tight_layout(); fig.savefig(D / 'align_split.png', dpi=150)
