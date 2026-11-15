"""총정리 덱용 분포 차트: 아이디어별 거래 수익 분포 갤러리 + 개별 히스토그램 + 요약 통계 JSON."""
import sys, json, numpy as np, pandas as pd, matplotlib
matplotlib.use('Agg'); import matplotlib.pyplot as plt
from scipy import stats
from pathlib import Path
sys.path.insert(0, str(Path.home() / 'agent-fund/lib')); from dist_report import summary
H = Path.home() / 'agent-fund-data'; D = Path(sys.argv[1]); D.mkdir(exist_ok=True)
NAVY, ORANGE, BLUE, GRAY, MUTED = '#14213D', '#C4621F', '#2F6DB5', '#B8BFCC', '#4A5568'
plt.rcParams.update({'font.family': 'Apple SD Gothic Neo', 'font.size': 15, 'axes.unicode_minus': False, 'axes.spines.top': False, 'axes.spines.right': False,
                     'axes.grid': True, 'grid.color': '#ECE9E1', 'axes.axisbelow': True, 'axes.edgecolor': '#C9C4B8', 'xtick.color': MUTED, 'ytick.color': MUTED, 'axes.labelcolor': MUTED})
nolci = lambda t: t[~((t.tk == 'LCI') & (t.tq == 8055))] if 'tq' in t else t
S = {
 'kr': ('코스피 실현 감마', pd.read_parquet(H / 'trades_a_op_A.parquet').ex.values, '꺾일 때까지 보유'),
 'sp': ('S&P 500 실현 감마', pd.read_parquet(H / 'refine/tr_sp_acc0_V0.parquet').ex.values, '꺾일 때까지 보유'),
 'smg': ('중소형 실현 감마', pd.read_parquet(H / 'refine/tr_sm_acc0_V0.parquet').ex.values, '꺾일 때까지 보유'),
 'surp': ('중소형 서프라이즈 예측', nolci(pd.read_parquet(H / 'refine/tr_sm_p_ridge_V0.parquet')).ex.values, '예측 꺾일 때까지'),
 'ref': ('정교화 감마 (성장·가격·안정)', pd.read_parquet(H / 'refine/tr_sm_acc0_V6r_noSL.parquet').ex.values, '꺾일 때까지 보유'),
 'tech': ('서프라이즈 + 기술 조건', nolci(pd.read_parquet(H / 'refine/win_tr_sm_p_ridge_V0_combo.parquet')).ex.values, '예측 꺾일 때까지'),
 'cs': ('CAN SLIM', pd.read_parquet(H / 'canslim/tr_S1_E1_fixed.parquet').ex.values, '기준 깨질 때까지'),
 'ch': ('체슬리 퀀트 Q1', pd.read_parquet(H / 'chesley/tr_Q1_A_1x.parquet').ex.values, '한 달 보유'),
}
rnd = np.load(H / 'refine/dist_random.npy')
out = {}
for k, (nm, x, hold) in S.items():
    s = summary(x); out[k] = dict(name=nm, hold=hold, n=int(s['n']), mean=s['mean'], median=s['median'], win=s['win'], skew=s['skew'], exkurt=s['exkurt'],
                                 p10=s['q'][10], p90=s['q'][90], p1=s['q'][1], p99=s['q'][99], drop1=s['drop_top'][1], beat30=s['beat_prob'][30], trim1=s['trim1'])
s = summary(rnd); out['rnd'] = dict(name='무작위 중소형주', n=int(s['n']), mean=s['mean'], median=s['median'], win=s['win'], skew=s['skew'], p10=s['q'][10], p90=s['q'][90])
json.dump(out, open(D / 'summary_stats.json', 'w'), ensure_ascii=False, indent=1, default=float)
def hist(ax, x, title=None, color=BLUE, lo=-100, hi=200, step=5, small=False):
    x = x * 100; b = np.arange(lo, hi + step, step)
    ax.hist(np.clip(x, lo, hi), bins=b, color=color, alpha=.85, edgecolor='white', lw=.5, density=True)
    g = np.linspace(lo, hi, 500); ax.plot(g, stats.norm.pdf(g, x.mean(), x.std()), color=ORANGE, lw=2 if small else 2.6)
    ax.axvline(np.median(x), color=NAVY, ls='--', lw=1.6); ax.axvline(x.mean(), color=ORANGE, ls='--', lw=1.6); ax.axvline(0, color='#9AA3B2', lw=1)
    ax.set_yticks([]); ax.set_xlim(lo, hi)
    if title: ax.set_title(title, fontsize=15 if small else 17, color=NAVY, fontweight='bold', loc='left')
# 갤러리 2×4
f, axs = plt.subplots(2, 4, figsize=(20, 8.6))
for ax, (k, (nm, x, hold)) in zip(axs.flat, S.items()):
    lo, hi = (-60, 60) if k == 'ch' else (-100, 200)
    hist(ax, x, nm, color=ORANGE if k in ('ref',) else BLUE, lo=lo, hi=hi, step=3 if k == 'ch' else 5, small=True)
    o = out[k]; ax.text(.98, .95, f"n={o['n']:,}\n평균 {o['mean']*100:+.1f}%\n중앙 {o['median']*100:+.1f}%\n왜도 {o['skew']:.1f}", transform=ax.transAxes, ha='right', va='top', fontsize=12.5, color=NAVY)
    ax.tick_params(labelsize=12)
f.text(0.5, 0.01, '거래당 시장 대비 초과수익 (%, 비용 후) · 막대 = 실제 분포, 주황 곡선 = 같은 평균·표준편차의 정규분포, 남색 점선 = 중앙값, 주황 점선 = 평균 · 체슬리는 한 달 보유라 가로축을 ±60%로 좁힘', ha='center', fontsize=13, color=MUTED)
plt.tight_layout(rect=(0, .04, 1, 1)); f.savefig(D / 'gallery.png', dpi=170, bbox_inches='tight', pad_inches=.15); plt.close(f)
# 개별
for k, (nm, x, hold) in S.items():
    f, ax = plt.subplots(figsize=(11, 5.4)); lo, hi = (-60, 60) if k == 'ch' else (-100, 200)
    hist(ax, x, None, color=ORANGE if k == 'ref' else BLUE, lo=lo, hi=hi, step=3 if k == 'ch' else 5)
    if k in ('surp', 'ref', 'tech', 'cs', 'smg'):
        r = rnd * 100; b = np.arange(lo, hi + 5, 5); ax.hist(np.clip(r, lo, hi), bins=b, density=True, histtype='step', lw=2, color='#7D8799', ls='-')
    yl = ax.get_ylim()[1]; o = out[k]
    ax.text(np.median(x) * 100 - 2, yl * .95, f"중앙 {o['median']*100:+.1f}%", ha='right', color=NAVY, fontsize=14, fontweight='bold')
    ax.text(x.mean() * 100 + 2, yl * .95, f"평균 {o['mean']*100:+.1f}%", ha='left', color=ORANGE, fontsize=14, fontweight='bold')
    ax.set_xlabel('거래당 시장 대비 초과수익 (%, 비용 후)')
    f.savefig(D / f'd_{k}.png', dpi=190, bbox_inches='tight', pad_inches=.15); plt.close(f)
print(json.dumps({k: {a: (round(b, 3) if isinstance(b, float) else b) for a, b in v.items()} for k, v in out.items()}, ensure_ascii=False, indent=0))
