"""가치평가 엔진 v2 (2026-11-14). 표준 라이브러리만 쓴다.
구조: ① 명시 예측 3년(시나리오가 정한 매출·이익률) → ② 페이드(초과 수익성은 반감기 h, 초과 성장은 h/2로 줄어듦) → ③ 영구가치(신규 투자 수익률 = 자본비용).
근거: McKinsey Valuation 가치동인 공식 FCF = NOPAT × (1 − g/RONIC), Mauboussin·Rappaport Expectations Investing(주가가 담은 기대 역산),
      Base Rate Book(2016) 업종별 초과수익 회귀 속도(IT 4년 상관 0.50 = 반감기 4년), 매출 성장 지속성(3년 상관 0.19 = 반감기 약 1.3년, 넉넉히 2년).
단위: 십억 달러. 모든 이익은 GAAP 영업이익 기준(주식보상은 이미 비용으로 빠져 있고 현금흐름에 되더하지 않는다)."""
import math, random

H_FADE = 40      # 페이드를 계산하는 햇수. 끝나면 영구가치
G_T = 0.04       # 영구 성장률(명목). 신규 투자 수익률이 자본비용과 같아지면 값에 영향이 없다


class Seg:
    """사업 부문 하나.
    rev: [기준 연도, 1년차, 2년차, 3년차] 매출.  m: 1~3년차 영업이익률.  sc: 매출/투하자본(매출 1달러 늘리는 데 1/sc달러 재투자).
    g0: 페이드 시작 성장률(None이면 3년차 성장률, trough=True면 0 아래로는 안 내려감).  charge: (연차, 세전 금액) 일회성 손실."""
    def __init__(self, name, rev, m, tax, sc, g0=None, trough=False, charge=None, m_T=None):
        self.name, self.rev, self.m, self.tax, self.sc = name, rev, m, tax, sc
        g3 = rev[3] / rev[2] - 1
        self.g0 = g3 if g0 is None else g0
        if trough: self.g0 = max(self.g0, 0.0)
        self.charge, self.m_T = charge, m_T


def half(x0, xT, k, h):
    """k년 뒤 값. 목표 xT와의 거리가 h년마다 절반이 된다."""
    return xT + (x0 - xT) * 0.5 ** (k / h)


def seg_flows(s, r, h, ronic_T=None, hg=None):
    """부문의 연도별 (NOPAT, FCF) 목록과 영구가치(마지막 해 말 기준)를 돌려준다. 1년차부터.
    h: 수익성(이익률, 신규 투자 수익률) 반감기.  hg: 성장 반감기(기본 h의 절반. 성장은 수익성보다 빨리 평균으로 돌아간다)."""
    rT = r if ronic_T is None else ronic_T
    hg = h / 2 if hg is None else hg
    out = []
    rev = list(s.rev)                               # 0..3
    nm = [s.m[k] * (1 - s.tax) for k in range(3)]   # 세후 영업이익률 1..3년차
    ronic0 = nm[2] * s.sc                           # 3년차 기준 신규 투자 수익률 = 세후 이익률 × 매출/투하자본
    # 명시 예측 3년
    for k in (1, 2, 3):
        nopat = rev[k] * nm[k - 1]
        nxt = rev[k + 1] if k < 3 else rev[3] * (1 + half(s.g0, G_T, 1, hg))
        reinv = max(nxt - rev[k], 0) / s.sc          # 매출이 줄어도 자본 회수는 가정하지 않는다
        ch = s.charge[1] * (1 - s.tax) if s.charge and s.charge[0] == k else 0
        out.append((nopat, nopat - reinv - ch))
    # 페이드
    rv, mm = rev[3], nm[2]
    for k in range(1, H_FADE + 1):
        g = half(s.g0, G_T, k, hg)
        rv *= 1 + g
        if s.m_T is not None: mm = half(nm[2], s.m_T * (1 - s.tax), k, h)
        nopat = rv * mm
        g_next = half(s.g0, G_T, k + 1, hg)
        ronic = half(ronic0, rT, k, h) if ronic0 > rT else ronic0
        reinv = nopat * g_next / ronic if (g_next > 0 and ronic > 0 and nopat > 0) else 0
        out.append((nopat, nopat - reinv))
    # 영구가치: 가치동인 공식. 신규 투자 수익률이 자본비용이면 NOPAT ÷ r 이 된다
    nopat_T = out[-1][0] * (1 + G_T)
    ronic_end = half(ronic0, rT, H_FADE, h) if ronic0 > rT else max(ronic0, 1e-9)
    tv = nopat_T * (1 - G_T / ronic_end) / (r - G_T) if nopat_T > 0 else nopat_T / (r - G_T)
    return out, tv


def value(segs, r, h, lag=0.5, net_cash=0.0, nonop=0.0, ronic_T=None, detail=False, hg=None):
    """회사 가치(주주 몫, 십억 달러). lag: 1년차 현금흐름 중간 시점이 (1 − lag)년 뒤."""
    n = 3 + H_FADE
    fcf, nopat, tv = [0.0] * n, [0.0] * n, 0.0
    for s in segs:
        fl, t = seg_flows(s, r, h, ronic_T, hg)
        for i, (a, b) in enumerate(fl): nopat[i] += a; fcf[i] += b
        tv += t
    pv = [fcf[i] / (1 + r) ** (i + 1 - lag) for i in range(n)]
    pv_tv = tv / (1 + r) ** (n - lag)      # 영구가치 공식은 첫 현금흐름 1년 전 시점의 값. 현금흐름이 연중이므로 마지막 해 중간 시점으로 할인
    ev = sum(pv) + pv_tv
    eq = ev + net_cash + nonop
    if not detail: return eq
    # 3년차 말 시점의 영업가치와 그때 순이익 배수(결과로 나오는 PER)
    v3 = sum(fcf[i] / (1 + r) ** (i - 2 - 0.5) for i in range(3, n)) + tv / (1 + r) ** (n - 3 - 0.5)
    return dict(eq=eq, ev=ev, pv3=sum(pv[:3]), after3=(ev - sum(pv[:3])) / ev if ev else 0, pv_tv_share=pv_tv / ev if ev else 0,
                v3=v3, nopat3=nopat[2], per3=v3 / nopat[2] if nopat[2] > 0 else float("nan"), fcf=fcf[:6], nopat=nopat[:6])


def bisect(f, target, lo, hi, n=60):
    """f가 증가함수일 때 f(x) = target 인 x."""
    for _ in range(n):
        mid = (lo + hi) / 2
        if f(mid) < target: lo = mid
        else: hi = mid
    return (lo + hi) / 2


# ---------- 확률: 기저율과 분포
def shrink(inside, base, r):
    """Mauboussin: 추정 = 기저율 + r × (내부 전망 − 기저율). r은 근거의 강도(0~1)."""
    return base + r * (inside - base)


def t_draw(rng, mu, sd, df=5):
    """꼬리가 두꺼운 분포(Student-t)에서 하나 뽑는다. 표준편차가 sd가 되게 맞춘다. 함께 쓴 표준정규 z도 돌려준다."""
    z = rng.gauss(0, 1)
    chi = rng.gammavariate(df / 2, 2)
    t = z / math.sqrt(chi / df)
    return mu + sd * t / math.sqrt(df / (df - 2)), z


def coord(x, nodes, lo=None, hi=None):
    """x가 nodes(오름차순) 사이 어디인지 (왼쪽 번호, 가중)으로. 범위 밖은 lo~hi까지 끝 기울기로 연장."""
    if lo is not None: x = max(x, lo)
    if hi is not None: x = min(x, hi)
    i = 0
    while i < len(nodes) - 2 and x > nodes[i + 1]: i += 1
    return i, (x - nodes[i]) / (nodes[i + 1] - nodes[i])


def bilinear(grid, ix, wx, iy, wy):
    a = grid[ix][iy] * (1 - wy) + grid[ix][iy + 1] * wy
    b = grid[ix + 1][iy] * (1 - wy) + grid[ix + 1][iy + 1] * wy
    return a * (1 - wx) + b * wx


def pct(xs, q):
    ys = sorted(xs); k = (len(ys) - 1) * q; f = int(k)
    return ys[f] + (ys[min(f + 1, len(ys) - 1)] - ys[f]) * (k - f)


def brier(probs, hit):
    """브라이어 점수. probs: 시나리오 확률(합 1), hit: 맞은 시나리오 번호. 0이 완벽."""
    return sum((p - (1 if i == hit else 0)) ** 2 for i, p in enumerate(probs))
