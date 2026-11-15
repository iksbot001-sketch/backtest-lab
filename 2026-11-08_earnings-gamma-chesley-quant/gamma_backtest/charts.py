"""분포·정교화 차트(PNG). 출력: 인자로 받은 폴더."""
import sys, json
import numpy as np, pandas as pd, matplotlib
matplotlib.use('Agg'); import matplotlib.pyplot as plt
from scipy import stats
from pathlib import Path
O = Path.home() / 'agent-fund-data/refine'; D = Path(sys.argv[1])
NAVY, ORANGE, BLUE, GRAY, LIGHT, MUTED = '#14213D', '#C4621F', '#2F6DB5', '#9AA3B2', '#F7F6F2', '#4A5568'
plt.rcParams.update({'font.family': 'Apple SD Gothic Neo', 'font.size': 15, 'axes.edgecolor': '#C9C4B8', 'axes.labelcolor': MUTED, 'xtick.color': MUTED, 'ytick.color': MUTED,
                     'axes.spines.top': False, 'axes.spines.right': False, 'figure.facecolor': 'white', 'axes.facecolor': 'white', 'axes.grid': True, 'grid.color': '#ECE9E1', 'grid.linewidth': 0.8, 'axes.axisbelow': True, 'axes.unicode_minus': False})
def save(fig, name): fig.savefig(D / name, dpi=200, bbox_inches='tight', pad_inches=0.15); plt.close(fig)

t = pd.read_parquet(O / 'tr_sm_p_ridge_V0.parquet'); x = t.ex.values * 100; rnd = np.load(O / 'dist_random.npy') * 100
# 1) 히스토그램 + 같은 평균·표준편차의 정규분포
fig, ax = plt.subplots(figsize=(11, 5.6))
bins = np.arange(-100, 205, 5); xc = np.clip(x, -100, 200)
ax.hist(xc, bins=bins, color=BLUE, alpha=0.85, edgecolor='white', linewidth=0.6, label=f'실제 거래 {len(x):,}건')
g = np.linspace(-100, 200, 600); ax.plot(g, stats.norm.pdf(g, x.mean(), x.std()) * len(x) * 5, color=ORANGE, lw=2.5, label='같은 평균·표준편차의 정규분포')
for v, lab, c in [(np.median(x), f'중앙값 {np.median(x):+.1f}%', NAVY), (x.mean(), f'평균 {x.mean():+.1f}%', ORANGE)]:
    ax.axvline(v, color=c, lw=1.8, ls='--')
ax.text(np.median(x) - 3, ax.get_ylim()[1] * 0.93, f'중앙값 {np.median(x):+.1f}%', ha='right', color=NAVY, fontsize=14, fontweight='bold')
ax.text(x.mean() + 3, ax.get_ylim()[1] * 0.93, f'평균 {x.mean():+.1f}%', ha='left', color=ORANGE, fontsize=14, fontweight='bold')
n200 = (x > 200).sum(); ax.annotate(f'+200% 넘는 거래 {n200}건\n(최대 {x.max():+,.0f}%)', xy=(197, 30), xytext=(150, ax.get_ylim()[1] * 0.45), fontsize=13, color=MUTED, arrowprops=dict(arrowstyle='->', color=GRAY))
ax.set_xlabel('거래당 러셀2000 대비 초과수익 (%, 비용 후)'); ax.set_ylabel('거래 수'); ax.legend(frameon=False, loc='upper right', bbox_to_anchor=(1, 0.98))
save(fig, 'hist.png')

# 2) 분위수: 전략 vs 무작위 대조군
ps = [1, 5, 10, 25, 50, 75, 90, 95, 99]; qa = np.percentile(x, ps); qr = np.percentile(rnd, ps)
fig, ax = plt.subplots(figsize=(11, 5.2)); xs = np.arange(len(ps))
ax.bar(xs - 0.2, qr, 0.38, color='#C9CED8', label='같은 분기·같은 기간 무작위 중소형주')
ax.bar(xs + 0.2, qa, 0.38, color=BLUE, label='서프라이즈 예측 상위 종목')
for i, (a_, r_) in enumerate(zip(qa, qr)):
    ax.text(i + 0.2, a_ + (4 if a_ >= 0 else -4), f'{a_:+.0f}', ha='center', va='bottom' if a_ >= 0 else 'top', fontsize=12, color=NAVY)
    ax.text(i - 0.2, r_ + (4 if r_ >= 0 else -4), f'{r_:+.0f}', ha='center', va='bottom' if r_ >= 0 else 'top', fontsize=11, color=GRAY)
ax.set_xticks(xs); ax.set_xticklabels([f'하위 {p}%' if p < 50 else ('중앙' if p == 50 else f'상위 {100 - p}%') for p in ps], fontsize=13)
ax.axhline(0, color='#C9C4B8', lw=1); ax.set_ylabel('거래당 초과수익 (%)'); ax.legend(frameon=False, loc='upper left')
save(fig, 'quantiles.png')

# 3) 상위 거래를 빼면 평균이 어떻게 되나
fig, ax = plt.subplots(figsize=(11, 5.2)); cuts = [0, 0.1, 0.5, 1, 2, 5]
xg = pd.read_parquet(O / 'tr_sm_acc0_V6r_noSL.parquet').ex.values * 100
for v, lab, c in [(x, f'서프라이즈 예측 상위 ({len(x):,}건)', BLUE), (xg, f'정교화한 실현 감마 ({len(xg):,}건)', ORANGE)]:
    s_ = np.sort(v)[::-1]; m = [s_[int(len(s_) * p / 100):].mean() for p in cuts]
    ax.plot(range(len(cuts)), m, marker='o', ms=9, lw=2.6, color=c, label=lab)
    for i, mm in enumerate(m):
        up = (c == ORANGE) != (i == 0); ax.text(i, mm + (0.35 if up else -0.35), f'{mm:+.1f}%', ha='center', va='bottom' if up else 'top', fontsize=12, color=c)
ax.axhline(0, color='#C9C4B8', lw=1.2); ax.set_xticks(range(len(cuts))); ax.set_xticklabels(['전체'] + [f'상위 {p:g}% 제외' for p in cuts[1:]])
ax.set_ylabel('거래당 평균 초과수익 (%)'); ax.set_ylim(-7.8, 4); ax.legend(frameon=False, loc='upper right')
save(fig, 'contrib.png')

# 4) 보유 종목 수별 시장을 이길 확률
d2 = json.load(open(O / 'dist2.json')); ns = [10, 30, 100, 300]
fig, ax = plt.subplots(figsize=(11, 5.2))
for nm, lab, c in [('중소형 실현 감마 정교화(V6r_noSL)', '정교화한 실현 감마', ORANGE), ('중소형 서프라이즈 예측 V0', '서프라이즈 예측 상위', BLUE), ('중소형 실현 감마 V0', '기본 실현 감마', GRAY)]:
    v = [d2[nm]['port'][str(n)]['beat'] * 100 for n in ns]; ax.plot(range(4), v, marker='o', ms=9, lw=2.6, color=c, label=lab)
    ax.text(3.08, v[-1], f'{v[-1]:.0f}%', va='center', fontsize=13, color=c, fontweight='bold')
ax.axhline(50, color='#C9C4B8', lw=1.2, ls=':'); ax.text(1.5, 51.5, '동전 던지기 50%', fontsize=12, color=MUTED)
ax.set_xticks(range(4)); ax.set_xticklabels([f'{n}종목' for n in ns]); ax.set_xlim(-0.2, 3.4); ax.set_ylim(30, 100)
ax.set_ylabel('무작위로 고른 거래 묶음이\n시장을 이길 확률 (%)'); ax.legend(frameon=False, loc='upper left')
save(fig, 'portsize.png')

# 5) 정교화 결과: 달력 기준 연환산 초과수익
r = pd.concat([pd.read_csv(O / 'refine_sm.csv'), pd.read_csv(O / 'refine_sp.csv')])
lab = {'V0': '기본', 'V1': '+성장 지속(Q)', 'V2': '+가격 확인(C)', 'V3': '+비경기순환(P)', 'V4': '+손절 -25%', 'V5': '+최대 2년', 'V6r_noSL': 'Q+C+P 결합', 'V6r': '+손절·2년까지 결합'}
bs = ['B3 실현 감마', 'B1 실현 감마', 'B2 서프라이즈 예측']; bt = {'B3 실현 감마': 'S&P 500 실현 감마', 'B1 실현 감마': '중소형 실현 감마', 'B2 서프라이즈 예측': '중소형 서프라이즈 예측'}
fig, axs = plt.subplots(1, 3, figsize=(15, 6.6), sharey=True)
for ax, b in zip(axs, bs):
    s = r[(r.base == b) & r.v.isin(lab)].set_index('v').loc[list(lab)]
    y = np.arange(len(s))[::-1]; vals = s.ann.values * 100; ts = s.tcal.values
    cols = [ORANGE if (v > 0 and tt >= 2) else (BLUE if v > 0 else GRAY) for v, tt in zip(vals, ts)]
    ax.barh(y, vals, color=cols, height=0.62)
    for yy, v, tt in zip(y, vals, ts): ax.text(v + (0.3 if v >= 0 else -0.3), yy, f'{v:+.1f}% (t {tt:.1f})', va='center', ha='left' if v >= 0 else 'right', fontsize=12, color=NAVY)
    ax.axvline(0, color='#C9C4B8', lw=1); ax.set_title(bt[b], fontsize=16, color=NAVY, fontweight='bold'); ax.set_yticks(y); ax.set_yticklabels(list(lab.values()))
    lo, hi = min(vals.min(), 0), max(vals.max(), 0); ax.set_xlim(lo - 8, hi + 7); ax.grid(axis='y', visible=False)
axs[1].set_xlabel('달력 기준 연환산 초과수익 (%, 비용 후)')
save(fig, 'refine.png')
print('ok', sorted(p.name for p in D.glob('*.png')))
