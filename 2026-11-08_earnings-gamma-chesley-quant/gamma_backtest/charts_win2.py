"""승자 vs 패자 비교 차트(기준 2종) + 다변량 점수 3분위 분포."""
import sys, numpy as np, pandas as pd, matplotlib
matplotlib.use('Agg'); import matplotlib.pyplot as plt
from pathlib import Path
O = Path.home() / 'agent-fund-data/refine'; D = Path(sys.argv[1])
NAVY, ORANGE, BLUE, GRAY, MUTED = '#14213D', '#C4621F', '#2F6DB5', '#B8BFCC', '#4A5568'
plt.rcParams.update({'font.family': 'Apple SD Gothic Neo', 'font.size': 15, 'axes.unicode_minus': False, 'axes.spines.top': False, 'axes.spines.right': False,
                     'axes.grid': True, 'grid.color': '#ECE9E1', 'axes.axisbelow': True, 'axes.edgecolor': '#C9C4B8', 'xtick.color': MUTED, 'ytick.color': MUTED, 'axes.labelcolor': MUTED})
sv = lambda f, n: (f.savefig(D / n, dpi=200, bbox_inches='tight', pad_inches=0.15), plt.close(f))
f, axs = plt.subplots(1, 2, figsize=(15, 7), sharey=True)
for ax, (nm, fn) in zip(axs, [('서프라이즈 예측 거래', 'tr_sm_p_ridge_V0'), ('실현 감마 거래', 'tr_sm_acc0_V0')]):
    a = pd.read_csv(O / f'w2_{fn}_+30_-20.csv'); b = pd.read_csv(O / f'w2_{fn}_+50_-50.csv'); a, b = a[a.kind == 'cont'].reset_index(drop=True), b[b.kind == 'cont'].reset_index(drop=True)
    y = np.arange(len(a))[::-1]
    ax.axvspan(-0.2, 0.2, color='#F1EEE6', zorder=0)
    ax.scatter(a.dis, y + .15, s=70, facecolors='none', edgecolors=ORANGE, lw=1.6); ax.scatter(a.oos, y + .15, s=80, color=ORANGE, marker='D')
    ax.scatter(b.dis, y - .15, s=70, facecolors='none', edgecolors=NAVY, lw=1.6); ax.scatter(b.oos, y - .15, s=80, color=NAVY, marker='D')
    ax.axvline(0, color='#C9C4B8'); ax.set_yticks(y); ax.set_yticklabels(a.feat); ax.grid(axis='y', visible=False); ax.set_xlim(-.6, .6)
    ax.set_title(nm, fontsize=16, color=NAVY, fontweight='bold'); ax.set_xlabel('승자 - 패자 표준화 차이 (d)')
for lab, kw in [('+30% vs -20%, 2010~2018', dict(facecolors='none', edgecolors=ORANGE)), ('+30% vs -20%, 2019~', dict(color=ORANGE, marker='D')),
                ('+50% vs -50%, 2010~2018', dict(facecolors='none', edgecolors=NAVY)), ('+50% vs -50%, 2019~', dict(color=NAVY, marker='D'))]:
    axs[0].scatter([], [], s=70, label=lab, **kw)
f.legend(*axs[0].get_legend_handles_labels(), frameon=False, loc='lower center', bbox_to_anchor=(0.5, 0.98), ncol=4, fontsize=13); sv(f, 'win2_diff.png')
# 점수 3분위(실현 감마, 로지스틱, 2019~)
s = pd.read_parquet(O / 'w2_scores_tr_sm_acc0_V0.parquet'); s['g'] = pd.qcut(s.s_lr.rank(method='first'), 3, labels=['하', '중', '상'])
PS = [5, 10, 25, 50, 75, 90, 95]; xs = np.arange(len(PS)); w = .27
f, ax = plt.subplots(figsize=(12, 5.4))
for k, (g, c) in enumerate([('하', BLUE), ('중', GRAY), ('상', ORANGE)]):
    v = s.ex[s.g == g] * 100; q = np.percentile(v, PS)
    ax.bar(xs + (k - 1) * w, q, w, color=c, label=f'점수 {g}위 1/3 ({len(v):,}건, 평균 {v.mean():+.1f}%, 중앙 {np.median(v):+.1f}%)')
    for i, qq in enumerate(q):
        if g != '중': ax.text(i + (k - 1) * w, qq + (2 if qq >= 0 else -2), f'{qq:+.0f}', ha='center', va='bottom' if qq >= 0 else 'top', fontsize=11, color=NAVY)
ax.set_xticks(xs); ax.set_xticklabels([f'하위 {p}%' if p < 50 else ('중앙' if p == 50 else f'상위 {100 - p}%') for p in PS], fontsize=13)
ax.axhline(0, color='#C9C4B8'); ax.set_ylabel('거래당 초과수익 (%)'); ax.legend(frameon=False, loc='upper left', fontsize=13); sv(f, 'win2_tercile.png')
print('ok')
