"""체슬리 퀀트 차트: 누적 자산 곡선, 편입 건별 분위수(전략 vs 무작위 vs 신고가 전체)."""
import sys, numpy as np, pandas as pd, matplotlib
matplotlib.use('Agg'); import matplotlib.pyplot as plt
from pathlib import Path
C = Path.home() / 'agent-fund-data/chesley'; D = Path(sys.argv[1])
NAVY, ORANGE, BLUE, GRAY, MUTED, GREEN = '#14213D', '#C4621F', '#2F6DB5', '#B8BFCC', '#4A5568', '#3E8E5E'
plt.rcParams.update({'font.family': 'Apple SD Gothic Neo', 'font.size': 15, 'axes.unicode_minus': False, 'axes.spines.top': False, 'axes.spines.right': False,
                     'axes.grid': True, 'grid.color': '#ECE9E1', 'axes.axisbelow': True, 'axes.edgecolor': '#C9C4B8', 'xtick.color': MUTED, 'ytick.color': MUTED, 'axes.labelcolor': MUTED})
sv = lambda f, n: (f.savefig(D / n, dpi=200, bbox_inches='tight', pad_inches=0.15), plt.close(f))
m = pd.read_parquet(C / 'monthly_returns.parquet'); m.index = pd.to_datetime(m.index)
f, ax = plt.subplots(figsize=(13, 5.8))
for col, lab, c, lw in [('BM_KODEX200', 'KODEX 200', NAVY, 2.4), ('BM_HIGH_A_1x', '신고가 종목 전체(동일비중)', GRAY, 2.2), ('RAND_HIGH_A_1x', '신고가 중 무작위 같은 수', '#D9C7B5', 2.0),
                      ('Q2_A_1x', 'Q2 자사주 변형', GREEN, 2.4), ('Q1_A_1x', 'Q1 체슬리 퀀트(외인 수급 제외)', ORANGE, 2.8)]:
    w = (1 + m[col].fillna(0)).cumprod(); ax.plot(w.index, w.values, color=c, lw=lw, label=lab)
    ax.text(w.index[-1] + pd.Timedelta(days=20), w.values[-1], f'{w.values[-1]:.2f}', va='center', fontsize=12, color=c, fontweight='bold')
ax.set_yscale('log'); ax.set_yticks([0.25, 0.5, 1, 2, 4]); ax.set_yticklabels(['0.25', '0.5', '1', '2', '4']); ax.minorticks_off(); ax.set_ylabel('1원이 얼마가 됐나 (로그 눈금, 비용 후)'); ax.legend(frameon=False, loc='upper left', fontsize=13); ax.axhline(1, color='#C9C4B8', lw=1)
sv(f, 'ch_curve.png')
PS = [1, 5, 10, 25, 50, 75, 90, 95, 99]; xs = np.arange(len(PS)); w_ = .27
f, ax = plt.subplots(figsize=(12, 5.2))
for k, (fn, lab, c) in enumerate([('tr_BM_HIGH_A_1x', '신고가 전체', GRAY), ('tr_RAND_HIGH_A_1x', '신고가 중 무작위', '#D9C7B5'), ('tr_Q1_A_1x', 'Q1 체슬리 퀀트', ORANGE)]):
    t = pd.read_parquet(C / f'{fn}.parquet'); q = np.percentile(t.ex * 100, PS)
    ax.bar(xs + (k - 1) * w_, q, w_, color=c, label=f'{lab} ({len(t):,}건, 평균 {t.ex.mean() * 100:+.1f}%, 중앙 {t.ex.median() * 100:+.1f}%)')
    if k == 2:
        for i, qq in enumerate(q): ax.text(i + w_, qq + (1.5 if qq >= 0 else -1.5), f'{qq:+.0f}', ha='center', va='bottom' if qq >= 0 else 'top', fontsize=11, color=NAVY)
ax.set_xticks(xs); ax.set_xticklabels([f'하위 {p}%' if p < 50 else ('중앙' if p == 50 else f'상위 {100 - p}%') for p in PS], fontsize=13)
ax.axhline(0, color='#C9C4B8'); ax.set_ylabel('한 달 보유 초과수익 (KODEX 200 대비, %)'); ax.legend(frameon=False, loc='upper left', fontsize=12.5); sv(f, 'ch_quant.png')
print('ok')
