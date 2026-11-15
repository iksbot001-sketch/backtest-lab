"""감마 킬러 차트(성장률 경로 소형 다중 차트)와 부록 표 이미지. 입력 gamma.json."""
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

plt.rcParams['font.family'] = ['Apple SD Gothic Neo', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False
H = Path(__file__).parent
R = json.loads((H / 'gamma.json').read_text())
INK, MUTE, UP, DN, NAVY, GRID = '#2b2b2b', '#8a8378', '#2f6b4f', '#9b2c2c', '#1f3a5f', '#e6e0d4'
BG = '#f7f3ea'
Q = ['2025-06-30', '2025-09-30', '2025-12-31', '2026-03-31', '2026-06-30', '2026-09-30']
QL = ['25.2Q', '3Q', '4Q', '26.1Q', '2Q', '3Q']
FINE = 3.5e9  # 2025년 3분기 EU 과징금(10-Q 원문), 기저에서 뺀다


def gmap(pairs):
    return {k: v for k, v in pairs}


g, gm = R['GOOGL'], R['MSFT']
oi = gmap(g['raw']['oi'])
oi_adj = dict(oi); oi_adj['2025-09-30'] += FINE
ks = sorted(oi_adj)
g_oi_adj = {k: oi_adj[k] / oi_adj[ks[i - 4]] - 1 for i, k in enumerate(ks) if i >= 4}
azure = {'2025-06-30': .39, '2025-09-30': .40, '2025-12-31': .39, '2026-03-31': .40, '2026-06-30': .43, '2026-09-30': .48}

panels = [
    ('구글 전체 매출', gmap(g['g']['rev']), [g['cons']['0q']['rev_g'], g['cons']['+1q']['rev_g']]),
    ('구글 검색 매출', gmap(g['seg_g']['search']), None),
    ('구글 클라우드 매출', gmap(g['seg_g']['cloud']), None),
    ('구글 영업이익 (과징금 기저 조정)', g_oi_adj, None),
    ('MSFT 전체 매출', gmap(gm['g']['rev']), [gm['cons']['0q']['rev_g'], gm['cons']['+1q']['rev_g']]),
    ('MSFT Azure 매출', azure, None),
    ('MSFT 영업이익', gmap(gm['g']['oi']), None),
]

fig, axs = plt.subplots(2, 4, figsize=(16, 7.2), facecolor=BG)
for ax, (title, ser, fc) in zip(axs.flat, panels):
    ax.set_facecolor(BG)
    ys = [ser.get(q) for q in Q]
    xs = list(range(len(Q)))
    a = ys[-1] - ys[-2]
    col = UP if a > 0 else DN
    ax.plot(xs, [y * 100 for y in ys], color=NAVY, lw=2.2, marker='o', ms=4.5, zorder=3)
    ax.plot(xs[-1], ys[-1] * 100, marker='o', ms=8, color=col, zorder=4)
    if fc:
        fx = [xs[-1], xs[-1] + 1, xs[-1] + 2]
        ax.plot(fx, [ys[-1] * 100, fc[0] * 100, fc[1] * 100], color=NAVY, lw=1.8, ls=(0, (3, 2)), marker='o', ms=4,
                mfc='white', zorder=3)
        ax.annotate(f'전망 {fc[1] * 100:.1f}%', (fx[-1], fc[1] * 100), textcoords='offset points', xytext=(0, 8),
                    ha='center', fontsize=10, color=MUTE)
        ax.set_xticks(xs + fx[1:]); ax.set_xticklabels(QL + ['4Q*', '27.1Q*'], fontsize=9, color=MUTE)
    else:
        ax.set_xticks(xs); ax.set_xticklabels(QL, fontsize=9, color=MUTE)
    lo, hi = min(ys) * 100, max(ys + (fc or [])) * 100
    pad = max(2.0, (hi - lo) * 0.35)
    ax.set_ylim(lo - pad, hi + pad * 1.4)
    ax.set_title(title, fontsize=12.5, color=INK, loc='left', fontweight='bold', pad=26)
    ax.text(0, 1.03, f'{ys[-1] * 100:.1f}%  ', transform=ax.transAxes, fontsize=15, color=INK, fontweight='bold',
            va='bottom')
    ax.text(0.40, 1.03, f'가속도 {a * 100:+.1f}%p', transform=ax.transAxes, fontsize=11.5, color=col,
            fontweight='bold', va='bottom')
    ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f'{v:.0f}%'))
    ax.tick_params(axis='y', labelsize=9, colors=MUTE)
    ax.grid(axis='y', color=GRID, lw=0.8); ax.set_axisbelow(True)
    for s in ('top', 'right', 'left'): ax.spines[s].set_visible(False)
    ax.spines['bottom'].set_color(GRID)

# 8번째 칸: 컨센서스 EPS 90일 수정률
ax = axs.flat[7]; ax.set_facecolor(BG)
labs = ['이번 분기', '다음 분기', '올해', '내년']
per = ['0q', '+1q', '0y', '+1y']
w = 0.38
for i, (t, c) in enumerate([('GOOGL', DN), ('MSFT', NAVY)]):
    vals = [R[t]['cons'][p]['rev90'] * 100 for p in per]
    bars = ax.bar([x + (i - 0.5) * w for x in range(4)], vals, w, color=c if t == 'MSFT' else '#b98a8a', label=t)
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v + (0.25 if v >= 0 else -0.25), f'{v:+.1f}', ha='center',
                va='bottom' if v >= 0 else 'top', fontsize=8.5, color=INK)
ax.axhline(0, color=MUTE, lw=0.8)
ax.set_xticks(range(4)); ax.set_xticklabels(labs, fontsize=9, color=MUTE)
ax.set_ylim(-7.5, 5)
ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f'{v:.0f}%'))
ax.tick_params(axis='y', labelsize=9, colors=MUTE)
ax.set_title('EPS 전망, 90일 사이 수정률', fontsize=12.5, color=INK, loc='left', fontweight='bold', pad=26)
ax.text(0, 1.03, 'MSFT 전부 상향 · 구글 단기 하향', transform=ax.transAxes, fontsize=11, color=INK, va='bottom')
ax.legend(frameon=False, fontsize=9, loc='lower left')
for s in ('top', 'right', 'left'): ax.spines[s].set_visible(False)
ax.grid(axis='y', color=GRID, lw=0.8); ax.set_axisbelow(True)

fig.text(0.01, 0.005, '전년 동기 대비 성장률. 가속도 = 이번 분기 성장률 − 직전 분기 성장률. * 컨센서스(EODHD, 2026-11-08). '
         '구글 영업이익은 2025년 3분기 EU 과징금 35억달러를 기저에서 뺐다. 구글 올해 EPS 하향에는 3분기 투자평가손 반영분이 섞여 있다.',
         fontsize=9, color=MUTE)
fig.tight_layout(rect=(0, 0.03, 1, 1), h_pad=3.2, w_pad=2.2)
fig.savefig(H / 'gamma_chart.png', dpi=170, facecolor=BG)

# 부록 표: 분기별 성장률과 가속도
rows = []
def line(name, ser):
    vals = [ser.get(q) for q in Q]
    acc = [None] + [vals[i] - vals[i - 1] if vals[i] is not None and vals[i - 1] is not None else None for i in range(1, 6)]
    rows.append([name + ' 성장률'] + [f'{v * 100:.1f}%' if v is not None else '-' for v in vals])
    rows.append(['   가속도'] + [f'{v * 100:+.1f}%p' if v is not None else '' for v in acc])
for title, ser, _ in panels:
    line(title.replace(' (과징금 기저 조정)', '(조정)'), ser)
cons = []
for t in ('GOOGL', 'MSFT'):
    c = R[t]['cons']
    cons.append([t, f"{c['0q']['rev_g'] * 100:.1f}%", f"{c['+1q']['rev_g'] * 100:.1f}%"] +
                [f"{c[p]['rev90'] * 100:+.1f}% ({c[p]['up30']:.0f}↑/{c[p]['down30']:.0f}↓)" for p in per])

fig2, (a1, a2) = plt.subplots(2, 1, figsize=(16, 7.4), facecolor='white', gridspec_kw={'height_ratios': [3.3, 1]})
for a in (a1, a2): a.axis('off')
hdr = ['항목'] + ['2025.2Q', '2025.3Q', '2025.4Q', '2026.1Q', '2026.2Q', '2026.3Q']
tb = a1.table(cellText=rows, colLabels=hdr, loc='upper center', cellLoc='right', colLoc='center',
              colWidths=[0.28] + [0.12] * 6)
tb.auto_set_font_size(False); tb.set_fontsize(10.5); tb.scale(1, 1.42)
for (r, c), cell in tb.get_celld().items():
    cell.set_edgecolor('#d0d0d0')
    if r == 0: cell.set_facecolor('#1f3a5f'); cell.get_text().set_color('white'); cell.get_text().set_fontweight('bold')
    elif c == 0: cell.get_text().set_ha('left'); cell._loc = 'left'
    txt = cell.get_text().get_text()
    if r > 0 and '%p' in txt:
        cell.get_text().set_color(UP if txt.startswith('+') else DN); cell.set_facecolor('#fafafa')
a1.set_title('① 분기별 성장률과 가속도 (전년 동기 대비)', loc='left', fontsize=13, fontweight='bold')
tb2 = a2.table(cellText=cons, colLabels=['', '매출 전망 4Q', '매출 전망 27.1Q', 'EPS 수정 이번 분기', '다음 분기', '올해', '내년'],
               loc='upper center', cellLoc='center', colWidths=[0.08, 0.11, 0.12, 0.18, 0.17, 0.17, 0.17])
tb2.auto_set_font_size(False); tb2.set_fontsize(10.5); tb2.scale(1, 1.5)
for (r, c), cell in tb2.get_celld().items():
    cell.set_edgecolor('#d0d0d0')
    if r == 0: cell.set_facecolor('#1f3a5f'); cell.get_text().set_color('white'); cell.get_text().set_fontweight('bold')
a2.set_title('② 컨센서스: 매출 성장률 전망과 EPS 90일 수정률 (괄호: 최근 30일 상향/하향 건수)', loc='left', fontsize=13,
             fontweight='bold')
fig2.text(0.01, 0.01, '출처: 매출·영업이익 EODHD 분기 손익(=10-Q), 구글 부문 매출 10-Q/10-K 원문(4분기 = 연간 − 3분기 누적), '
          'Azure 성장률 MSFT 실적 보도자료, 컨센서스 EODHD 전망 추세(2026-11-08). MSFT 회계연도는 6월 결산이라 "올해"=FY27(2027.6).',
          fontsize=9, color='#666')
fig2.tight_layout(rect=(0, 0.03, 1, 1))
fig2.savefig(H / 'gamma_table.png', dpi=150, facecolor='white')
print('ok')
