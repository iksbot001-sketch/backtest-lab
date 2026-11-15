"""큰 승자 공통점 차트."""
import sys, numpy as np, pandas as pd, matplotlib
matplotlib.use('Agg'); import matplotlib.pyplot as plt
from pathlib import Path
O = Path.home() / 'agent-fund-data/refine'; D = Path(sys.argv[1])
NAVY, ORANGE, BLUE, GRAY, MUTED = '#14213D', '#C4621F', '#2F6DB5', '#B8BFCC', '#4A5568'
plt.rcParams.update({'font.family': 'Apple SD Gothic Neo', 'font.size': 15, 'axes.unicode_minus': False, 'axes.spines.top': False, 'axes.spines.right': False,
                     'axes.grid': True, 'grid.color': '#ECE9E1', 'axes.axisbelow': True, 'axes.edgecolor': '#C9C4B8', 'xtick.color': MUTED, 'ytick.color': MUTED, 'axes.labelcolor': MUTED})
sv = lambda f, n: (f.savefig(D / n, dpi=200, bbox_inches='tight', pad_inches=0.15), plt.close(f))
R = pd.read_csv(O / 'winners.csv'); s = R[R.set == '서프라이즈 예측'].reset_index(drop=True)
# 1) 공통점: 큰 승자·전체·큰 패자에서의 비율
f, ax = plt.subplots(figsize=(15, 6.2)); y = np.arange(len(s))[::-1]; h = 0.26
ax.barh(y + h, s.share_win * 100, h, color=ORANGE, label='큰 승자 (+50% 초과, 705건)')
ax.barh(y, s.share_all * 100, h, color=GRAY, label='전체 (6,007건)')
ax.barh(y - h, s.share_loss * 100, h, color=BLUE, label='큰 패자 (−50% 미만, 599건)'.replace('−', '-'))
ax.set_yticks(y); ax.set_yticklabels(s.feat); ax.set_xlabel('그 특징을 가진 거래의 비율 (%)'); ax.set_xlim(0, 105); ax.grid(axis='y', visible=False)
ax.legend(frameon=False, loc='lower center', bbox_to_anchor=(0.5, 1.0), ncol=3); sv(f, 'win_common.png')
# 2) 발견 구간 vs 검증 구간 평균 차이
f, axs = plt.subplots(1, 2, figsize=(15, 6.4), sharey=True)
for ax, nm in zip(axs, ['서프라이즈 예측', '실현 감마']):
    r = R[R.set == nm].reset_index(drop=True); y = np.arange(len(r))[::-1]
    for yy, a, b, ad in zip(y, r.dis_dmean * 100, r.oos_dmean * 100, r.adopt):
        ax.plot([a, b], [yy, yy], color='#D9D4C8', lw=2.2, zorder=1)
        ax.scatter([a], [yy], s=90, color=GRAY if not ad else NAVY, zorder=2); ax.scatter([b], [yy], s=90, color=ORANGE, zorder=3, marker='D')
    ax.axvline(0, color='#C9C4B8'); ax.axvline(2, color='#C9C4B8', ls=':'); ax.set_yticks(y); ax.set_yticklabels(r.feat); ax.grid(axis='y', visible=False)
    ax.set_title(nm + ' 거래', fontsize=16, color=NAVY, fontweight='bold'); ax.set_xlabel('특징 있음 - 없음, 거래당 평균 차이 (%p)')
axs[0].scatter([], [], s=90, color=NAVY, label='2010~2018 (채택)'); axs[0].scatter([], [], s=90, color=GRAY, label='2010~2018 (탈락)'); axs[0].scatter([], [], s=90, color=ORANGE, marker='D', label='2019~ 검증')
axs[0].legend(frameon=False, loc='lower left', fontsize=13); sv(f, 'win_oos.png')
# 3) 분포 모양: 조합 vs 나머지 (서프라이즈, 2019~)
t = pd.read_parquet(O / 'tr_sm_p_ridge_V0.parquet'); c = pd.read_parquet(O / 'win_tr_sm_p_ridge_V0_combo.parquet')
key = set(zip(c.tk, c.i0)); t = t[t.tq // 4 >= 2019]; m = np.array([(a, b) in key for a, b in zip(t.tk, t.i0)])
PS = [1, 5, 10, 25, 50, 75, 90, 95, 99]; qa, qr = np.percentile(t.ex[m] * 100, PS), np.percentile(t.ex[~m] * 100, PS); xs = np.arange(len(PS))
f, ax = plt.subplots(figsize=(11, 5.2)); ax.bar(xs - .2, qr, .38, color=GRAY, label=f'조건 미충족 ({(~m).sum():,}건, 평균 {t.ex[~m].mean() * 100:+.1f}%)')
ax.bar(xs + .2, qa, .38, color=ORANGE, label=f'채택 조건 모두 충족 ({m.sum()}건, 평균 {t.ex[m].mean() * 100:+.1f}%)')
for i, (a, r_) in enumerate(zip(qa, qr)):
    ax.text(i + .2, a + (4 if a >= 0 else -4), f'{a:+.0f}', ha='center', va='bottom' if a >= 0 else 'top', fontsize=12, color=NAVY)
    ax.text(i - .2, r_ + (4 if r_ >= 0 else -4), f'{r_:+.0f}', ha='center', va='bottom' if r_ >= 0 else 'top', fontsize=11, color=MUTED)
ax.set_xticks(xs); ax.set_xticklabels([f'하위 {p}%' if p < 50 else ('중앙' if p == 50 else f'상위 {100 - p}%') for p in PS], fontsize=13)
ax.axhline(0, color='#C9C4B8'); ax.set_ylabel('거래당 초과수익 (%)'); ax.legend(frameon=False, loc='upper left'); sv(f, 'win_shape.png')
print('ok')
