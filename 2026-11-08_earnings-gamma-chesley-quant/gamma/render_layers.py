"""6장 가치사슬 그림: 다섯 층(무엇을 팔고 어떻게 버나) × 세 회사(어디에 서 있나) + 층별 이익률 단서."""
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

plt.rcParams['font.family'] = ['Apple SD Gothic Neo', 'DejaVu Sans']
H = Path(__file__).parent
INK, MUTE, NAVY, BLUE, BG, LINE = '#1a1a1a', '#8a8378', '#1f3a5f', '#1f5fad', '#f7f3ea', '#d9d1c0'
STRONG, PART, NONE = '#1f3a5f', '#9fb3cc', '#ffffff'

layers = [  # 위에서 아래로
    ('앱·업무 배포', '사람이 쓰는 AI 앱', '좌석당 구독료'),
    ('업무 맥락·관제', '메일·문서 데이터 연결, 에이전트 관리', '앱에 묶어 판다'),
    ('프런티어 모델', 'Claude·Gemini·GPT 같은 두뇌', '토큰(사용량)당 요금'),
    ('클라우드', '데이터센터의 연산을 빌려준다', '연산 시간당 임대료'),
    ('칩·시스템', 'AI 계산을 하는 칩과 서버', '칩·서버 판매와 리스'),
]
margin = ['MSFT 앱+Azure 사업부 이익률 52.8%', '따로 공시 없음', 'Anthropic 조정 영업이익률 14.5%\n(컴퓨트가 매출의 58%)',
          'Google Cloud 영업이익률 36%', 'TPU 금융리스 1,612억달러(Anthropic)']
cos = ['MSFT', 'GOOGL', 'Anthropic']
cells = [  # (강도, 설명) 0=빌리거나 없음, 1=일부, 2=직접·강함
    [(2, 'M365 4.5억 좌석·Copilot'), (1, 'Workspace·Gemini 앱'), (1, 'Claude 앱·Code 직판')],
    [(2, 'Work IQ·Agent 365'), (1, 'Gemini Enterprise'), (1, 'Cowork가 노림')],
    [(1, 'OpenAI 지분 24%·자체 MAI'), (2, 'Gemini'), (2, 'Claude, 기업 점유율 55%')],
    [(2, 'Azure 332억달러'), (2, 'Google Cloud 307억달러'), (0, '3사에서 빌림')],
    [(1, 'Maia, 대부분 NVIDIA'), (2, 'TPU 설계·판매·리스'), (0, '빌림(TPU·Trainium·GPU)')],
]

fig = plt.figure(figsize=(15, 5.3), facecolor=BG)
ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, 150); ax.set_ylim(0, 53); ax.axis('off')
top, rh, gap = 48.2, 8.0, 0.8
x_l, w_l = 4.5, 33          # 층 설명
x_c, w_c = 39.5, 22.5       # 회사 칸
x_m, w_m = 110.5, 38        # 이익률 단서

for j, c in enumerate(cos):
    ax.text(x_c + j * (w_c + 1) + w_c / 2, top + 2.4, c, ha='center', va='center', fontsize=13, fontweight='bold', color=INK)
ax.text(x_l, top + 2.4, '층 · 무엇을 팔고 어떻게 버나', ha='left', va='center', fontsize=12, fontweight='bold', color=INK)
ax.text(x_m, top + 2.4, '이 층의 이익률 단서', ha='left', va='center', fontsize=12, fontweight='bold', color=INK)

for i, (name, what, how) in enumerate(layers):
    y = top - (i + 1) * rh - i * gap
    hl = i == 2
    ax.add_patch(FancyBboxPatch((x_l, y), w_l, rh, boxstyle='round,pad=0,rounding_size=0.8',
                                fc='#efe7d6' if not hl else '#e8eef6', ec=BLUE if hl else LINE, lw=1.6 if hl else 1))
    ax.text(x_l + 1.4, y + rh - 2.3, name, fontsize=12.5, fontweight='bold', color=INK, va='center')
    ax.text(x_l + 1.4, y + 3.3, what, fontsize=9.6, color=INK, va='center')
    ax.text(x_l + 1.4, y + 1.3, how, fontsize=9.6, color=MUTE, va='center')
    for j, (lv, txt) in enumerate(cells[i]):
        x = x_c + j * (w_c + 1)
        fc = {2: STRONG, 1: PART, 0: NONE}[lv]
        ax.add_patch(FancyBboxPatch((x, y), w_c, rh, boxstyle='round,pad=0,rounding_size=0.8', fc=fc, ec=LINE, lw=1))
        ax.text(x + w_c / 2, y + rh / 2, txt, ha='center', va='center', fontsize=9.8,
                color='white' if lv == 2 else INK, fontweight='bold' if lv == 2 else 'normal', wrap=True)
    ax.add_patch(FancyBboxPatch((x_m, y), w_m, rh, boxstyle='round,pad=0,rounding_size=0.8',
                                fc='white', ec=BLUE if hl else LINE, lw=1.6 if hl else 1))
    ax.text(x_m + 1.4, y + rh / 2, margin[i], fontsize=10, color=BLUE if hl else INK, va='center',
            fontweight='bold' if hl else 'normal')

# 돈의 흐름 화살표(위 → 아래)
ax.add_patch(FancyArrowPatch((2.2, top - 1), (2.2, top - 5 * rh - 4 * gap + 1), arrowstyle='-|>', mutation_scale=16,
                             color=MUTE, lw=1.6))
ax.text(1.0, top - 2.5 * rh - 2 * gap, '기업 고객의 돈이 위에서 아래로 흐른다', rotation=90, ha='center', va='center',
        fontsize=9, color=MUTE)
# 범례
lx = x_c
for k, (fc, lab) in enumerate([(STRONG, '직접·강함'), (PART, '일부'), (NONE, '빌리거나 없음')]):
    ax.add_patch(FancyBboxPatch((lx + k * 15, 0.9), 2.2, 1.6, boxstyle='round,pad=0,rounding_size=0.3', fc=fc, ec=LINE))
    ax.text(lx + k * 15 + 3, 1.7, lab, fontsize=9.5, color=MUTE, va='center')
fig.savefig(H / 'layers_chart.png', dpi=170, facecolor=BG)
print('ok')
