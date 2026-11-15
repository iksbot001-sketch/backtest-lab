"""CAN SLIM 차트: 글자 빼기·손절 비교(달력 기준), 손절 전후 분위수."""
import sys, numpy as np, pandas as pd, matplotlib
matplotlib.use('Agg'); import matplotlib.pyplot as plt
from pathlib import Path
C = Path.home() / 'agent-fund-data/canslim'; D = Path(sys.argv[1])
NAVY, ORANGE, BLUE, GRAY, MUTED = '#14213D', '#C4621F', '#2F6DB5', '#B8BFCC', '#4A5568'
plt.rcParams.update({'font.family': 'Apple SD Gothic Neo', 'font.size': 15, 'axes.unicode_minus': False, 'axes.spines.top': False, 'axes.spines.right': False,
                     'axes.grid': True, 'grid.color': '#ECE9E1', 'axes.axisbelow': True, 'axes.edgecolor': '#C9C4B8', 'xtick.color': MUTED, 'ytick.color': MUTED, 'axes.labelcolor': MUTED})
sv = lambda f, n: (f.savefig(D / n, dpi=200, bbox_inches='tight', pad_inches=0.15), plt.close(f))
r = pd.read_csv(C / 'canslim_fixed.csv').set_index('v')
lab = {'S1_E1': 'CAN SLIM 전체 (C·A·N·S·L·M)', 'noC': 'C 빼기 (이번 분기 급증)', 'noA': 'A 빼기 (연속 성장)', 'noN': 'N 빼기 (52주 고가 근처)', 'noS': 'S 빼기 (거래량 증가)',
       'noL': 'L 빼기 (주도주)', 'noM': 'M 빼기 (시장 200일선)', 'S1_E2': '+ 오닐 손절 -8%', 'S1_E3': '+ 손절 -8%·익절 +25%'}
s = r.loc[list(lab)]; y = np.arange(len(s))[::-1]
f, ax = plt.subplots(figsize=(13, 6.4))
cols = [ORANGE if v == 'S1_E1' else (BLUE if v.startswith('no') else GRAY) for v in s.index]
ax.barh(y, s.ann * 100, color=cols, height=.62)
for yy, (v, row) in zip(y, s.iterrows()):
    ax.text(row.ann * 100 + .3, yy, f'연 {row.ann * 100:+.1f}%  (t {row.t:.1f}, 동시 보유 {row.npos:.0f}종목)', va='center', fontsize=12.5, color=NAVY)
ax.axvline(0, color='#C9C4B8'); ax.axvline(s.loc['S1_E1', 'ann'] * 100, color=ORANGE, ls=':', lw=1.4)
ax.set_yticks(y); ax.set_yticklabels([lab[v] for v in s.index]); ax.set_xlim(0, 24); ax.grid(axis='y', visible=False)
ax.set_xlabel('달력 기준 연환산 초과수익 (러셀2000 대비, 비용 후, %)'); sv(f, 'cs_ablation.png')
a = pd.read_parquet(C / 'tr_S1_E1_fixed.parquet'); b = pd.read_parquet(C / 'tr_S1_E2.parquet'); b = b[~((b.tk == 'LCI') & (b.tq == 8055))]
PS = [1, 5, 10, 25, 50, 75, 90, 95, 99]; qa, qb = np.percentile(a.ex * 100, PS), np.percentile(b.ex * 100, PS); xs = np.arange(len(PS))
f, ax = plt.subplots(figsize=(11, 5.2))
ax.bar(xs - .2, qa, .38, color=ORANGE, label=f'손절 없음 (평균 {a.ex.mean() * 100:+.1f}%, 중앙 {a.ex.median() * 100:+.1f}%)')
ax.bar(xs + .2, qb, .38, color=GRAY, label=f'-8% 손절 (평균 {b.ex.mean() * 100:+.1f}%, 중앙 {b.ex.median() * 100:+.1f}%, 62% 손절됨)')
for i, (p, q) in enumerate(zip(qa, qb)):
    ax.text(i - .2, p + (3 if p >= 0 else -3), f'{p:+.0f}', ha='center', va='bottom' if p >= 0 else 'top', fontsize=12, color=NAVY)
    ax.text(i + .2, q + (3 if q >= 0 else -3), f'{q:+.0f}', ha='center', va='bottom' if q >= 0 else 'top', fontsize=11, color=MUTED)
ax.set_xticks(xs); ax.set_xticklabels([f'하위 {p}%' if p < 50 else ('중앙' if p == 50 else f'상위 {100 - p}%') for p in PS], fontsize=13)
ax.axhline(0, color='#C9C4B8'); ax.set_ylabel('거래당 초과수익 (%)'); ax.legend(frameon=False, loc='upper left'); sv(f, 'cs_stop.png')
print('ok')
