"""코스닥150 ETF(229200) 변동성 수확 사다리 재검토 — 대표 지시 2026-10-26 (research/kq150_review_20261026/BRIEF.md)

질문 ① 매수 간격: ATR 배수 vs 고정 % vs 혼합 max(k×ATR, 하한)
     ② 신호 A 매집 구간: 구간 목표가 일괄 매도(현행) vs 같은 구간 포트폴리오별 회전 매매
     ③ 회전이 낫다면 익절폭(고정 %, ATR 배수, 국면별)

체결 모델 (fund.run 으로 표현 불가 → 직접 계산, 근거):
  - 사다리는 봉 내부에서 지정가가 닿으면 체결되는 전략이라 "t 종가 결정 → t+1 시가 체결"인 fund.run 으로 표현할 수 없다.
  - 그래서 ~/vol-harvest-daily/lib/vh_engine2.py(run2, 실운용 vh_daily.py 와 같은 엔진)의 체결 규칙을 그대로 옮겼다:
    봉 경로 = 양봉 O→L→H→C, 음봉 O→H→L→C. 매수 지정가 = 최근 매수가×(1−간격)(호가 내림), 갭으로 지정가 아래에서 시작하면 시가 체결.
    익절 지정가 = 매수가×(1+익절폭)(호가 올림), 갭 위 시작이면 시가 체결.
  - 비용(편도): 수수료 0.015% + 1틱(5원) 불리 체결. 매수 체결가 = 지정가+1틱, 매도 = 지정가−1틱, 양쪽에 수수료.
    → 왕복 = 수수료 0.03% + 2틱. cost_mult 배로 수수료·틱을 함께 키운다(2배 비용 = 편도 0.03%+2틱).
    ETF는 매도 거래세 없음(국내 주식형 ETF 비과세).
  - 일별 지표(ATR%, 이격도20, %B, 120일선, ATR 백분위)는 모두 전일 확정값(shift(1))만 쓴다.
  - 신호 A(코스닥 지수 T일 종가로 판정) → 매집 구간은 T+1일부터. 구간 종료 판정도 전일까지의 종가로만.
  - B&H 벤치마크는 fund.run(같은 ETF 100% 보유, t+1 시가 진입, 같은 비용 모델)으로 계산.
  - Sharpe 등은 fund.metrics(무위험 = ^IRX 일할) 정의. 과거 연구(vol-harvest)는 무위험 0 Sharpe 라 숫자가 다르다.

데이터:
  - 229200 5분봉 2021-09-02~, 일봉 2015-10~ : ~/vol-harvest-daily/data (읽기 전용)
  - 코스닥 지수 일봉 1996-07~ : fund.kr('KOSDAQ') (네이버). 2015-10-01 이전은 지수×(ETF/지수 2015-10-01 비율)로 이어 붙인 대용.
    (비율 상수는 가격 수준만 바꾸므로 수익률·신호에는 영향 없음. 1틱(5원)의 상대 비용만 달라짐 → 보고서에 명시)

사전 선언한 선택 규칙 (실행 전에 정함, 데이터 스누핑 방지):
  평가 묶음 4개는 시간이 겹치지 않는다 — M5_IS(2021-09~2024-06, 5분봉), M5_OOS(2024-07~, 5분봉),
  D_16_21(2016-06~2021-08, ETF 일봉), IDX_97_15(1997-07~2015-09, 지수 대용 일봉, 기존 사다리 연구에 한 번도 안 쓴 구간).
  변형이 현행보다 낫다고 말하려면 (a) 4묶음 중 3개 이상에서 Sharpe ≥ 현행, (b) D10 전체·I30 전체 MDD 가 현행보다 3%p 넘게 나쁘지 않을 것.
  통과한 변형 중 평균 순위 1등만 추천, 없으면 "현행 유지". 신호 A 구간이 없는 묶음은 질문 ②③ 판정에서 뺀다.

실행: ~/agent-fund/venv/bin/python backtest.py [stage]   stage = all | q1 | q2 | q3b | final | validate | report
"""
import sys, os, json, math, time, re, argparse
from pathlib import Path
sys.path.insert(0, '~/agent-fund/lib')
import fund, validate
import numpy as np, pandas as pd

OUT = Path(__file__).resolve().parent
RUN = OUT.parent
TICK = 5
FEE = 0.00015
CAPITAL = 100_000_000
END = '2026-10-23'                     # 5분봉·일봉 공통 마지막 날
DATA = Path('~/vol-harvest-daily/data').expanduser()

SETS = {  # 이름: (데이터, 시작, 끝)  — 시간 겹침 없음
    'M5_IS': ('m5', '2021-09-02', '2024-06-30'),
    'M5_OOS': ('m5', '2024-07-01', END),
    'D_16_21': ('d10', '2016-06-01', '2021-08-31'),
    'IDX_97_15': ('i30', '1997-07-01', '2015-09-30'),
}
FULL = {'M5_full': ('m5', '2021-09-02', END), 'D10_full': ('d10', '2016-06-01', END), 'I30_full': ('i30', '1997-07-01', END)}
START = {'m5': '2021-09-02', 'd10': '2016-06-01', 'i30': '1997-07-01'}

# 현행 운용 규칙 (~/vol-harvest-daily/config.json balanced + gap_floor + dip_regime)
BASE = dict(n=20, gap_k=1.0, gap_floor=0.03, j=0.6, up_j=1.5, hot=105.0, cold=0.0,
            dip=True, dip_gap_k=0.5, dip_gap_min=0.015, dip_target=0.15, dip_max=250, dip_min_rise=0.03,
            dip_mode='bulk', dip_end='keep')


# ================================================================ 데이터
def _fmt_px(df, market='KR'):
    df = df.copy()
    df['adj'] = df['close']
    for c in ('open', 'high', 'low'): df['a' + c] = df[c]
    df.attrs['market'] = market
    return df


def load_all():
    d = pd.read_csv(DATA / '229200_D.csv'); d['date'] = pd.to_datetime(d['date'].astype(str))
    D = d.set_index('date')[['open', 'high', 'low', 'close', 'volume']].astype(float)
    D = D[D.index <= END]
    m = pd.read_csv(DATA / '229200_m5.csv')
    m = m[m.date <= int(END.replace('-', ''))].reset_index(drop=True)
    m['dt'] = pd.to_datetime(m.date.astype(str)) + pd.to_timedelta(m.time // 100, 'h') + pd.to_timedelta(m.time % 100, 'm')
    K = fund.kr('KOSDAQ', start='19960101')[['open', 'high', 'low', 'close', 'volume']]
    K = K[(K.index <= END) & (K.index >= '1996-07-01')]
    k0 = D.index[0]; ratio = D['close'].iloc[0] / K['close'].loc[k0]
    pre = K[K.index < k0][['open', 'high', 'low', 'close']] * ratio
    pre['volume'] = np.nan                                   # 지수 거래량은 ETF 거래대금과 단위가 달라 유동성 검사에서 제외
    S = pd.concat([pre, D])
    kq = K.drop(columns=['volume'])
    return dict(D=_fmt_px(D), m5=m, S=_fmt_px(S), K=_fmt_px(kq), ratio=float(ratio))


# ================================================================ 지표·신호 (모두 과거 정보만)
def rsi(c, n):
    dd = c.diff()
    up = dd.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    dn = (-dd.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    return 100 - 100 / (1 + up / dn)


def indicators(px):
    """~/vol-harvest-daily/lib/signals.daily_indicators 와 같은 정의. 값은 그날 종가까지 정보(사용 시 shift(1))."""
    d = px[['open', 'high', 'low', 'close']].copy(); c = d['close']
    ma20, sd20 = c.rolling(20).mean(), c.rolling(20).std()
    d['pctb'] = (c - (ma20 - 2 * sd20)) / (4 * sd20)
    d['disp20'] = c / ma20 * 100
    d['gap120'] = c / c.rolling(120).mean() - 1
    tr = pd.concat([d['high'] - d['low'], (d['high'] - c.shift()).abs(), (d['low'] - c.shift()).abs()], axis=1).max(axis=1)
    d['atrp'] = tr.rolling(14).mean() / c * 100
    a = d['atrp'].values; pct = np.full(len(a), np.nan)       # ATR% 과거 1년 백분위(그 시점까지만)
    for i in range(len(a)):
        lo = max(0, i - 249)
        if i - lo + 1 >= 120 and not np.isnan(a[i]):
            w = a[lo:i]; w = w[~np.isnan(w)]
            pct[i] = (w < a[i]).mean() * 100 if len(w) else np.nan
    d['atr_pct'] = pct
    return d


def signal_A(kq_close):
    """dip_signals.kosdaq_A 와 같은 정의: 1년 고점 −20%↓ + 10년(2480일) 이평 아래 + (5일 −8%↓ 또는 RSI6<15)."""
    c = kq_close
    ma10y = c.rolling(2480, min_periods=2400).mean()
    dd252 = c / c.rolling(252, min_periods=60).max() - 1
    r5 = c / c.shift(5) - 1
    return (dd252 <= -.20) & (c < ma10y) & ((r5 <= -.08) | (rsi(c, 6) < 15))


def regime(close, sig, target=0.15, max_days=250):
    """dip_signals.regime 과 같은 코드. act[j]=True 면 j일은 매집 구간(j-1일 종가까지로 결정)."""
    c = np.asarray(close, float); s = np.asarray(sig, bool); n = len(c)
    act = np.zeros(n + 1, bool); tg = np.full(n + 1, np.nan); st = np.full(n + 1, -1)
    eps = []
    i = 0
    while i < n:
        if s[i]:
            T = i; tgt = c[T] * (1 + target); j = T + 1; hit = False
            while j <= n and j - T <= max_days:
                act[j] = True; tg[j] = tgt; st[j] = T
                if j < n and c[j] >= tgt:
                    hit = True; break
                j += 1
            eps.append((T, min(j, n - 1), hit))
            i = j + 1
        else:
            i += 1
    return act[:n], tg[:n], st[:n], eps


def day_table(px, kq, p):
    """일별 규칙 입력표(전일 확정 지표) + 매집 구간."""
    ind = indicators(px)
    sig = signal_A(kq['close']).reindex(px.index).fillna(False)
    act, tg, st, eps = regime(px['close'].values, sig.values, p['dip_target'], p['dip_max'])
    prev = ind.shift(1)
    t = pd.DataFrame(index=px.index)
    for k in ('atrp', 'pctb', 'disp20', 'gap120', 'atr_pct', 'close'): t[k] = prev[k]
    t['act'] = act if p.get('dip', True) else False
    t['tg'] = tg
    lab = np.where(t['act'], 'dip', np.where(t['atr_pct'] >= 80, 'hiatr', np.where(t['gap120'] > 0, 'up', 'plain')))
    t['label'] = lab
    conv = np.zeros(len(t), bool)                     # 목표 미달·시한(250일) 종료 다음 첫날 (그 전날 종가까지로 확정)
    for a, b, h in eps:
        if not h and b < len(t) and not act[b]: conv[b] = True
    t['conv_timeout'] = conv
    t.attrs['episodes'] = [(px.index[a], px.index[b], h) for a, b, h in eps]
    return t


def rules(p, t):
    """일별 (간격, 익절폭, 매수크기, 매수허용, 매집구간여부). vh_daily.make_rule 과 같은 현행 규칙 + 변형 키."""
    a = t['atrp'].fillna(2.0).values / 100
    dr = np.maximum(np.clip(p['gap_k'] * a, 0.008, 0.06), p['gap_floor']) if p['gap_k'] > 0 else np.full(len(a), p['gap_floor'])
    up = (t['gap120'] > 0).fillna(False).values
    ri = np.where(up, np.clip(p['up_j'] * a, 0.002, 0.05), np.clip(p['j'] * a, 0.002, 0.04))
    lab = t['label'].values
    for L in ('plain', 'up', 'hiatr'):                 # 질문 ③ 국면별 익절폭 (평상시 사다리)
        m = lab == L
        if f'tp_{L}_fix' in p: ri = np.where(m, p[f'tp_{L}_fix'], ri)
        if f'tp_{L}_atr' in p: ri = np.where(m, np.clip(p[f'tp_{L}_atr'] * a, 0.002, 0.20), ri)
    sz = np.where((t['pctb'] < p['cold']).fillna(False).values, 2.0, 1.0)
    al = ~(t['disp20'] > p['hot']).fillna(False).values
    act = t['act'].values.astype(bool)
    if p.get('dip', True):
        dg = np.maximum(p['dip_gap_k'] * a, p['dip_gap_min']) if p['dip_gap_k'] > 0 else np.full(len(a), p['dip_gap_min'])
        dr = np.where(act, dg, dr)
        if p['dip_mode'] == 'bulk':                    # 현행: 익절폭 = 구간 목표가/전일 종가 − 1 (최소 3%)
            dri = np.maximum(t['tg'].values / t['close'].values - 1, p['dip_min_rise'])
        elif 'dip_tp_fix' in p:                        # 회전: 포트폴리오별 고정 % 익절
            dri = np.full(len(a), p['dip_tp_fix'])
        else:                                          # 회전: 포트폴리오별 ATR 배수 익절
            dri = np.clip(p['dip_tp_atr'] * a, 0.002, 0.20)
        ri = np.where(act, dri, ri)
        al = np.where(act, True, al)
    return dr, ri, sz, al, act, t['conv_timeout'].fillna(False).values.astype(bool)


# ================================================================ 엔진 (vh_engine2.run2 이식 + 거래 기록·구간 종료 처리)
def engine(O, H, L, C, conv, newday, gapdays, drop, rise, size, allow, isdip, n_units=20, cost_mult=1.0,
           slip_ticks=1, capital=CAPITAL, cash_rate=0.0, dip_end='keep'):
    fee = FEE * cost_mult; slip = slip_ticks * TICK * cost_mult
    cash = float(capital); pos = []                   # [limit_px, qty, target, units, buy_bar, is_dip, fill]
    used = 0.0; ref_high = O[0]; nb = ns = 0
    n = len(O); eq = np.empty(n); expo = np.empty(n); traded = np.zeros(n)
    trades = []; dr_ = cash_rate / 365
    for t in range(n):
        if t and newday[t]:
            if dr_: cash *= (1 + dr_) ** gapdays[t]
            if (dip_end == 'convert' and not isdip[t]) or (dip_end == 'convert_timeout' and conv[t]):  # 매집 구간이 끝난 첫날: 남은 구간 포트폴리오를 평상시 익절폭으로 재설정(일괄·회전 동일 처리)
                for q in pos:
                    if q[5]:
                        q[2] = math.ceil(q[0] * (1 + rise[t]) / TICK) * TICK; q[5] = False
        o, h, l, c = O[t], H[t], L[t], C[t]
        path = (o, l, h, c) if c >= o else (o, h, l, c)
        for seg in range(4):
            a = path[seg - 1] if seg else path[0]; b = path[seg]
            if b <= a:
                while used < n_units - 1e-9 and allow[t]:
                    p0 = pos[-1][0] if pos else ref_high
                    trg = math.floor(p0 * (1 - drop[t]) / TICK) * TICK
                    if b > trg: break
                    px = min(trg, a); u = min(size[t], n_units - used); fill = px + slip
                    amt = cash / (n_units - used) * u; qty = int(amt // (fill * (1 + fee)))
                    if qty <= 0: break
                    cash -= qty * fill * (1 + fee); traded[t] += qty * fill
                    pos.append([px, qty, math.ceil(px * (1 + rise[t]) / TICK) * TICK, u, t, bool(isdip[t]), fill])
                    used += u; nb += 1
            if b >= a and pos:
                hit = [k for k, q in enumerate(pos) if q[2] <= b]
                for k in sorted(hit, reverse=True):
                    px, qty, tgt, u, bt, dp, fill = pos.pop(k)
                    sp = max(tgt, a) - slip; cash += qty * sp * (1 - fee); traded[t] += qty * sp
                    trades.append((bt, t, fill * (1 + fee), sp * (1 - fee), dp))
                    used -= u; ns += 1
                    if not pos:
                        used = 0.0; ref_high = max(tgt, a)
            if not pos:
                ref_high = max(ref_high, a, b)
        inv = sum(q[1] for q in pos) * c
        eq[t] = cash + inv; expo[t] = inv / (cash + inv)
    openpos = [(q[4], q[6] * (1 + fee), C[-1], q[5], q[1]) for q in pos]
    return eq, expo, traded, trades, openpos, nb, ns


def _bars(kind, data):
    if kind == 'm5':
        m = data['m5']; bars = m[['open', 'high', 'low', 'close']].astype(float).copy(); dt = m['dt']
        px, kq = data['D'], data['K']
    else:
        px = data['D'] if kind == 'd10' else data['S']; kq = data['K']
        px = px[px.index >= pd.Timestamp(START[kind])]  # 지표는 전체로 계산, 봉은 시작일부터
        bars = px[['open', 'high', 'low', 'close']].copy().reset_index(drop=True)
        dt = pd.Series(px.index + pd.Timedelta(hours=15, minutes=30))
    return bars, pd.DatetimeIndex(dt), kq


_TCACHE = {}


def simulate(p, kind, data, cost_mult=1.0, slip_ticks=1, cash_rate=0.0, px_override=None, win=None):
    """반환: dict(r=일수익률, expo=일말 노출, turnover, trades, label, episodes, ...)"""
    if px_override is not None:                       # validate 용 (일봉만)
        px, kq = px_override['229200'], px_override['KOSDAQ']
        px = px[px.index >= pd.Timestamp(p.get('v_start', START['i30']))]   # 검증 시작일(파라미터 아님: 문자열)
        t = day_table(px_override['229200'], kq, p).loc[px.index]
        bars = px[['open', 'high', 'low', 'close']].reset_index(drop=True); dt = pd.DatetimeIndex(px.index + pd.Timedelta(hours=15, minutes=30))
    else:
        bars, dt, kq = _bars(kind, data)
        full = data['D'] if kind in ('m5', 'd10') else data['S']
        key = (kind, p['dip_target'], p['dip_max'], p.get('dip', True))
        if key not in _TCACHE: _TCACHE[key] = day_table(full, kq, p)
        t = _TCACHE[key]
        t = t.reindex(dt.normalize())
        if win is not None:                           # 새 출발 창: a~b 봉만 (지표·구간은 전체 이력으로 계산한 값)
            mk = np.asarray((dt.normalize() >= pd.Timestamp(win[0])) & (dt.normalize() <= pd.Timestamp(win[1])))
            bars = bars[mk].reset_index(drop=True); dt = dt[mk]; t = t[mk]
    t = t.reset_index(drop=True)
    days = dt.normalize()
    newday = np.r_[True, days[1:] != days[:-1]]
    gapdays = np.r_[0, (days[1:] - days[:-1]).days]
    dr, ri, sz, al, act, conv = rules(p, t)
    O, H, L, C = (bars[k].values.astype(float) for k in ('open', 'high', 'low', 'close'))
    eq, expo, traded, trades, openpos, nb, ns = engine(list(O), list(H), list(L), list(C), list(conv), list(newday), list(gapdays),
                                                     list(dr), list(ri), list(sz), list(al), list(act), n_units=p['n'],
                                                     cost_mult=cost_mult, slip_ticks=slip_ticks, cash_rate=cash_rate,
                                                     dip_end=p.get('dip_end', 'keep'))
    s = pd.DataFrame({'eq': eq, 'expo': expo, 'traded': traded, 'day': days})
    g = s.groupby('day')
    e_d = g['eq'].last(); x_d = g['expo'].last(); tv_d = g['traded'].sum()
    r = e_d.pct_change(); r.iloc[0] = e_d.iloc[0] / CAPITAL - 1
    prev_e = e_d.shift(1).fillna(CAPITAL)
    lab = pd.Series(t['label'].values, index=days).groupby(level=0).first()
    return dict(r=r, eq=e_d, expo=x_d, turnover=tv_d / prev_e, trades=trades, openpos=openpos, nb=nb, ns=ns,
                label=lab, bar_day=days, kind=kind)


# ================================================================ 지표
_BH = {}


def bh(kind, data):
    if kind not in _BH:
        px = data['D'] if kind in ('m5', 'd10') else data['S']
        W = pd.DataFrame(1.0, index=px.index, columns=['229200'])
        r, _, _ = fund.run({'229200': px}, W, start=START[kind])
        _BH[kind] = r
    return _BH[kind]


def trade_stats(sim, a, b):
    """포트폴리오(1회 매수→익절) 단위 통계. 기간 a~b 안에서 매도된 거래 + b 시점 미청산(평가)."""
    days = sim['bar_day']; ta, tb = pd.Timestamp(a), pd.Timestamp(b)
    cl = [(days[bt], days[st], sp / bc - 1, dp) for bt, st, bc, sp, dp in sim['trades'] if ta <= days[st] <= tb]
    out = dict(n_sells=len(cl))
    if cl:
        rets = np.array([x[2] for x in cl]); hold = np.array([np.busday_count(x[0].date(), x[1].date()) for x in cl])
        out.update(avg_tp_ret=float(rets.mean()), avg_hold_days=float(hold.mean()), med_hold_days=float(np.median(hold)),
                   dip_sells=int(sum(x[3] for x in cl)))
    yrs = max((tb - ta).days / 365.25, 1e-9); out['sells_per_year'] = len(cl) / yrs
    return out


def summarize(sim, a, b, data):
    r = sim['r']; m = (r.index >= pd.Timestamp(a)) & (r.index <= pd.Timestamp(b)); rr = r[m]
    if len(rr) < 20: return {}
    bench = bh(sim['kind'], data)
    pos = sim['expo'].shift(1).fillna(0)[m]
    met = fund.metrics(rr, bench, pos)
    met['avg_invested'] = float(sim['expo'][m].mean())
    met['turnover_ann'] = float(sim['turnover'][m].sum() / (len(rr) / 252))
    met.update(trade_stats(sim, a, b))
    bm = fund.metrics(bench[(bench.index >= pd.Timestamp(a)) & (bench.index <= pd.Timestamp(b))])
    met['BH_CAGR'] = bm.get('CAGR'); met['BH_MDD'] = bm.get('MDD'); met['BH_Sharpe'] = bm.get('Sharpe')
    return met


def regime_table(sim, a, b, data):
    """일별 국면(전일 지표 기준)으로 나눈 성과. 날짜가 적은 칸은 표시."""
    r = sim['r']; lab = sim['label'].reindex(r.index); bench = bh(sim['kind'], data).reindex(r.index)
    m = (r.index >= pd.Timestamp(a)) & (r.index <= pd.Timestamp(b)); out = {}
    days = sim['bar_day']; sells = pd.Series([days[st] for _, st, _, _, _ in sim['trades']]).value_counts()
    for L in ('plain', 'up', 'hiatr', 'dip'):
        mm = m & (lab == L).values
        x = r[mm]; bx = bench[mm].fillna(0)
        if len(x) == 0: out[L] = dict(days=0); continue
        sd = x.std()
        out[L] = dict(days=int(len(x)), ann_ret=float(x.mean() * 252), sharpe_raw=float(x.mean() / sd * np.sqrt(252)) if sd > 0 else np.nan,
                      bh_ann_ret=float(bx.mean() * 252), cum=float((1 + x).prod() - 1), bh_cum=float((1 + bx).prod() - 1),
                      sells=int(sells.reindex(x.index).fillna(0).sum()), avg_invested=float(sim['expo'][mm].mean()),
                      small_sample=bool(len(x) < 60))
    return out


def episodes_table(sim, data, kind):
    """신호 A 매집 구간별: 신호일 T 종가 → 구간 마지막 날 종가 수익, 구간 중 MDD, B&H 같은 기간."""
    e = sim['eq']; full = data['D'] if kind in ('m5', 'd10') else data['S']
    key = (kind, BASE['dip_target'], BASE['dip_max'], True)
    eps = _TCACHE[key].attrs['episodes'] if key in _TCACHE else []
    rows = []
    for s0, s1, hit in eps:
        if s0 < e.index[0] or s0 > e.index[-1]: continue
        seg = e[(e.index >= s0) & (e.index <= s1)]
        if len(seg) < 2: continue
        c = full['close']
        rows.append(dict(start=str(s0.date()), end=str(s1.date()), days=int(len(seg) - 1), target_hit=bool(hit),
                         strat_ret=float(seg.iloc[-1] / seg.iloc[0] - 1), strat_mdd=float((seg / seg.cummax() - 1).min()),
                         bh_ret=float(c.loc[s1] / c.loc[s0] - 1)))
    return rows


# ================================================================ 실행 도우미 (모든 시뮬레이션을 시도 장부에 기록)
LOG = []


def evaluate_cfg(name, p, data, kinds=('m5', 'd10', 'i30'), cost_mult=1.0, slip_ticks=1, cash_rate=0.0, keep_sim=False):
    row = dict(name=name, params=p, cost_mult=cost_mult, slip_ticks=slip_ticks, cash_rate=cash_rate)
    sims = {}
    for k in kinds:
        t0 = time.time()
        sim = simulate(p, k, data, cost_mult, slip_ticks, cash_rate)
        sims[k] = sim
        fs = [s for s, v in {**SETS, **FULL}.items() if v[0] == k]
        for s in fs:
            _, a, b = {**SETS, **FULL}[s]; row[s] = summarize(sim, a, b, data)
        row[f'regimes_{k}'] = regime_table(sim, START[k], END, data)
        row[f'episodes_{k}'] = episodes_table(sim, data, k)
        sr = row[[s for s in fs if s.endswith('full')][0]].get('Sharpe')
        validate.registry_log(str(OUT), 'kq150_review', dict(p, dataset=k, cost_mult=cost_mult, slip=slip_ticks, cash=cash_rate), sr)
        print(f'  {name:42s} {k:4s} {time.time() - t0:5.1f}s  Sharpe {sr:.3f}', flush=True)
    LOG.append(row)
    return (row, sims) if keep_sim else row


def V(**kw):
    p = dict(BASE); p.update(kw)
    for k in [k for k, v in kw.items() if v is None]: p.pop(k)
    return p


def table(rows, keys=('M5_IS', 'M5_OOS', 'D_16_21', 'IDX_97_15', 'M5_full', 'D10_full', 'I30_full'),
          cols=('CAGR', 'MDD', 'Sharpe', 'avg_invested', 'sells_per_year')):
    out = []
    for r in rows:
        d = dict(name=r['name'])
        for k in keys:
            for c in cols:
                d[f'{k}.{c}'] = r.get(k, {}).get(c)
        out.append(d)
    return pd.DataFrame(out)


def select(rows, base_name, sets=('M5_IS', 'M5_OOS', 'D_16_21', 'IDX_97_15')):
    """사전 선언 규칙: ≥3/4(또는 사용 가능한 묶음의 3/4 이상) Sharpe ≥ 현행 + D10·I30 MDD 3%p 이내. 통과 중 평균 순위 1등."""
    base = next(r for r in rows if r['name'] == base_name)
    res = []
    names = [r['name'] for r in rows]
    ranks = {s: pd.Series({r['name']: r.get(s, {}).get('Sharpe', np.nan) for r in rows}).rank(ascending=False) for s in sets}
    for r in rows:
        wins = sum(1 for s in sets if r.get(s, {}).get('Sharpe', -9) >= base.get(s, {}).get('Sharpe', 9) - 1e-12)
        mdd_ok = all(r.get(k, {}).get('MDD', -1) >= base.get(k, {}).get('MDD', 0) - 0.03 for k in ('D10_full', 'I30_full'))
        need = math.ceil(len(sets) * 0.75)
        res.append(dict(name=r['name'], sharpe_wins_vs_base=wins, of=len(sets), mdd_ok=mdd_ok,
                        passes=(wins >= need and mdd_ok and r['name'] != base_name),
                        avg_rank=float(np.mean([ranks[s][r['name']] for s in sets]))))
    df = pd.DataFrame(res).sort_values('avg_rank')
    winners = df[df.passes]
    pick = winners.iloc[0]['name'] if len(winners) else base_name
    return df, pick


def dump(obj, f):
    json.dump(obj, open(OUT / f, 'w'), ensure_ascii=False, indent=1, default=lambda x: float(x) if isinstance(x, (np.floating, np.integer)) else str(x))


# ================================================================ 실험
def q1(data):
    """질문 ①: 평상시 사다리 매수 간격 (매집 구간 규칙은 현행 고정) + 매집 구간 간격."""
    V_ = {'현행 max(1.0ATR,3%)': V()}
    for k in (0.5, 0.75, 1.0, 1.25, 1.5): V_[f'ATR {k}×'] = V(gap_k=k, gap_floor=0.0)
    for f in (0.015, 0.02, 0.03, 0.04): V_[f'고정 {f:.1%}'] = V(gap_k=0.0, gap_floor=f)
    for k, f in ((0.75, 0.02), (0.75, 0.03), (1.0, 0.02), (1.0, 0.04), (1.25, 0.03)): V_[f'혼합 max({k}ATR,{f:.0%})'] = V(gap_k=k, gap_floor=f)
    rows = [evaluate_cfg(n, p, data) for n, p in V_.items()]
    sel, pick = select(rows, '현행 max(1.0ATR,3%)')
    # 매집 구간 간격 (일괄 매도 현행 유지 상태에서)
    W_ = {'매집간격 현행 max(0.5ATR,1.5%)': V()}
    for k, f, nm in ((0.3, 0.015, 'max(0.3ATR,1.5%)'), (1.0, 0.015, 'max(1.0ATR,1.5%)'), (0.0, 0.015, '고정 1.5%'),
                     (0.0, 0.03, '고정 3%'), (0.5, 0.03, 'max(0.5ATR,3%)')):
        W_[f'매집간격 {nm}'] = V(dip_gap_k=k, dip_gap_min=f)
    rows2 = [evaluate_cfg(n, p, data) for n, p in W_.items()]
    dip_sets = tuple(SETS)                            # 4묶음 모두 신호 A 구간 포함(M5_IS 2022-09, M5_OOS 2024-08·2026-07·2026-10, D 2019·2020, IDX 2006·2008·2011)
    sel2, pick2 = select(rows2, '매집간격 현행 max(0.5ATR,1.5%)', sets=dip_sets)
    dump(dict(rows=rows, select=sel.to_dict('records'), pick=pick, dip_rows=rows2, dip_select=sel2.to_dict('records'), dip_pick=pick2), 'q1.json')
    table(rows).to_csv(OUT / 'q1_table.csv', index=False, encoding='utf-8-sig')
    table(rows2).to_csv(OUT / 'q1_dipgap_table.csv', index=False, encoding='utf-8-sig')
    print(sel.to_string()); print('pick', pick); print(sel2.to_string()); print('dip pick', pick2)


def q2_variants():
    V_ = {'현행 일괄(구간 목표가, 종료 후 유지)': V(), '일괄(구간 목표가, 종료 후 평상 전환)': V(dip_end='convert'),
          '매집 구간 없음(평상 사다리만)': V(dip=False)}
    for f in (0.01, 0.02, 0.03, 0.05, 0.08): V_[f'회전 고정 {f:.0%}'] = V(dip_mode='rot', dip_tp_fix=f, dip_end='convert')
    for k in (0.2, 0.4, 0.6, 1.0, 1.5): V_[f'회전 ATR {k}×'] = V(dip_mode='rot', dip_tp_atr=k, dip_end='convert')
    return V_


def q2(data):
    """질문 ②③: 신호 A 매집 구간에서 일괄 매도 vs 포트폴리오별 회전 (같은 20포트폴리오·같은 간격·같은 종료 처리)."""
    rows = []
    for cm in (1.0, 2.0):
        for n, p in q2_variants().items():
            rows.append(evaluate_cfg(n + ('' if cm == 1 else ' [비용2배]'), p, data, cost_mult=cm))
    base_rows = [r for r in rows if r['cost_mult'] == 1.0]
    dip_sets = tuple(SETS)
    sel, pick = select([r for r in base_rows if r['name'] != '매집 구간 없음(평상 사다리만)'], '일괄(구간 목표가, 종료 후 평상 전환)', sets=dip_sets)
    sel_p, pick_p = select([r for r in base_rows if r['name'] != '매집 구간 없음(평상 사다리만)'], '현행 일괄(구간 목표가, 종료 후 유지)', sets=dip_sets)
    dump(dict(rows=rows, select_vs_bulk_convert=sel.to_dict('records'), pick=pick, select_vs_production=sel_p.to_dict('records'),
              pick_vs_production=pick_p), 'q2.json')
    table(rows).to_csv(OUT / 'q2_table.csv', index=False, encoding='utf-8-sig')
    print(sel.to_string()); print('pick', pick); print(sel_p.to_string()); print('pick vs prod', pick_p)


def q3b(data):
    """질문 ③ 국면별: 평상시 사다리에서 한 국면(평상·상승추세·고ATR)의 익절폭만 바꿨을 때."""
    rows = [evaluate_cfg('현행', V(), data)]
    for L, nm in (('plain', '평상'), ('up', '상승추세'), ('hiatr', '고ATR')):
        for f in (0.005, 0.01, 0.02, 0.03, 0.05): rows.append(evaluate_cfg(f'{nm} 익절 고정 {f:.1%}', V(**{f'tp_{L}_fix': f}), data))
        for k in (0.2, 0.4, 0.6, 1.0, 1.5): rows.append(evaluate_cfg(f'{nm} 익절 ATR {k}×', V(**{f'tp_{L}_atr': k}), data))
    out = {}
    for L, nm in (('plain', '평상'), ('up', '상승추세'), ('hiatr', '고ATR')):
        rr = [rows[0]] + [r for r in rows if r['name'].startswith(nm + ' ')]
        s, pk = select(rr, '현행'); out[L] = dict(select=s.to_dict('records'), pick=pk)
        print(nm, pk); print(s.to_string())
    dump(dict(rows=rows, by_regime=out), 'q3b.json')
    table(rows).to_csv(OUT / 'q3b_table.csv', index=False, encoding='utf-8-sig')


# ================================================================ validate 용 순수 함수 (지수 대용 30년 일봉)
def strategy(params, px, cost_mult=1.0):
    """validate.run_all 용. px={'229200': 이어붙인 일봉(1996-07~), 'KOSDAQ': 지수 일봉}. 신호·지표는 과거 정보만.
    반환 pos = 전일 장 마감 노출(= 그날 아침에 들고 시작하는 비중, 전일까지 정보로 결정) — 장중 체결은 r 에 반영."""
    sim = simulate(params, 'i30v', None, cost_mult=cost_mult, px_override=px)
    r = sim['r']; pos = sim['expo'].shift(1).fillna(0.0); to = sim['turnover']
    return r, pos, to


CFG_FINAL = {'현행': dict(BASE),
             '추천: 일괄 + 시한종료만 평상 전환': dict(BASE, dip_end='convert_timeout'),
             '조건부 후보: 추천 + 매집간격 고정 1.5%': dict(BASE, dip_end='convert_timeout', dip_gap_k=0.0)}
HALVES = {'m5': [('2021-09-02', '2024-06-30'), ('2024-07-01', END)], 'd10': [('2016-06-01', '2021-08-31'), ('2021-09-01', END)],
          'i30': [('1997-07-01', '2011-12-31'), ('2012-01-01', END)]}


def account_stats(sim):
    """포트폴리오(1회 매수→익절) 단위: 익절만 청산하므로 청산분 승률은 100% — 기간 말 미청산 포트폴리오를 평가손익으로 넣어 승률·손익비 계산."""
    days = sim['bar_day']; cl = np.array([sp / bc - 1 for bt, st, bc, sp, dp in sim['trades']])
    hold = np.array([np.busday_count(days[bt].date(), days[st].date()) for bt, st, bc, sp, dp in sim['trades']])
    op = np.array([(c * (1 - FEE) - TICK) / bc - 1 for bt, bc, c, dp, q in sim['openpos']])
    allr = np.concatenate([cl, op]) if len(op) else cl
    w, l = allr[allr > 0], allr[allr <= 0]
    return dict(closed=int(len(cl)), closed_avg_ret=float(cl.mean()) if len(cl) else None, avg_hold_days=float(hold.mean()) if len(hold) else None,
                open_at_end=int(len(op)), open_avg_mtm=float(op.mean()) if len(op) else None,
                win_rate_incl_open=float(len(w) / len(allr)) if len(allr) else None,
                payoff_incl_open=float(w.mean() / abs(l.mean())) if len(w) and len(l) else None)


def final(data):
    res = {}
    for nm, p in CFG_FINAL.items():
        res[nm] = {}
        for tag, kw in (('base', {}), ('cost2x', dict(cost_mult=2.0)), ('slip+1tick', dict(slip_ticks=2)), ('slip+2tick', dict(slip_ticks=3)),
                        ('cash2.5%', dict(cash_rate=0.025))):
            row, sims = evaluate_cfg(f'{nm} [{tag}]', p, data, keep_sim=True, **kw)
            for k, sim in sims.items():
                row[f'halves_{k}'] = [dict(summarize(sim, a, b, data), window=f'{a}~{b}') for a, b in HALVES[k]]
                row[f'accounts_{k}'] = account_stats(sim)
            res[nm][tag] = row
            if tag == 'base': res[nm]['_sims'] = sims
            if tag == 'cost2x': res[nm]['_sims2'] = sims
    return res


def strategy(params, px, cost_mult=1.0):
    """validate.run_all 용. px={'229200': ETF(또는 이어붙인) 일봉, 'KOSDAQ': 지수 일봉}. 신호·지표는 과거 정보만.
    일봉 사다리(봉 경로 O→L→H→C/O→H→L→C 지정가 체결, 비용 = 편도 0.015%+1틱 × cost_mult). fund.run 으로 표현 불가 → 직접 계산(모듈 주석 참고).
    반환 pos = 전일 장 마감 노출(= 그날 아침에 들고 시작하는 비중, 전일까지 정보로 결정) — 장중 체결 손익은 r 에 반영."""
    sim = simulate(params, 'v', None, cost_mult=cost_mult, px_override=px)
    r = sim['r']; pos = sim['expo'].shift(1).fillna(0.0); to = sim['turnover']
    return r, pos, to


def all_grid():
    g = {}
    for d in (q1_variants(), q2_variants(), extra_variants(), CFG_FINAL):
        for n, p in d.items(): g[json.dumps(p, sort_keys=True)] = p
    for f in ('q1.json', 'q3b.json'):
        x = json.load(open(OUT / f))
        for r in x['rows'] + x.get('dip_rows', []): g[json.dumps(r['params'], sort_keys=True)] = r['params']
    return list(g.values())


def stage_final(data):
    res = final(data)
    rec = '추천: 일괄 + 시한종료만 평상 전환'
    sims, sims2 = res[rec]['_sims'], res[rec]['_sims2']
    # 표준 산출물: 5분봉(2021-09~, 학습/검증 경계 2024-07-01) → backtest/metrics.json, equity.png
    ex = {k: {kk: vv for kk, vv in v.items() if not kk.startswith('_')} for k, v in res.items()}
    for kind, outdir, oos in (('m5', OUT, '2024-07-01'), ('d10', OUT / 'eval_d10', '2021-09-01'), ('i30', OUT / 'eval_i30', '2012-01-01')):
        s1, s2 = sims[kind], sims2[kind]
        extra = dict(data=kind, note='사다리 지정가 체결은 fund.run 으로 표현 불가 → 직접 계산(편도 0.015%+1틱). B&H 는 fund.run.',
                     accounts=account_stats(s1), regimes=regime_table(s1, START[kind], END, data),
                     cash25=ex[rec]['cash2.5%'].get({'m5': 'M5_full', 'd10': 'D10_full', 'i30': 'I30_full'}[kind]),
                     slip_plus1=ex[rec]['slip+1tick'].get({'m5': 'M5_full', 'd10': 'D10_full', 'i30': 'I30_full'}[kind]),
                     slip_plus2=ex[rec]['slip+2tick'].get({'m5': 'M5_full', 'd10': 'D10_full', 'i30': 'I30_full'}[kind]))
        fund.evaluate(f'KQ150 사다리 {rec} ({kind})', s1['r'], s1['expo'].shift(1).fillna(0), bh(kind, data), oos,
                      turnover=s1['turnover'], extra=extra, outdir=outdir, r_cost2=s2['r'])
    for nm in res: res[nm].pop('_sims'); res[nm].pop('_sims2')
    dump(res, 'final.json')


def stage_validate(data, which='d10'):
    grid = [dict(p, v_start=('2016-06-01' if which == 'd10' else '1997-07-01')) for p in all_grid()]
    params = dict(CFG_FINAL['추천: 일괄 + 시한종료만 평상 전환'], v_start=grid[0]['v_start'])
    px = {'229200': data['D'] if which == 'd10' else data['S'], 'KOSDAQ': data['K']}
    W = pd.DataFrame(1.0, index=px['229200'].index, columns=['229200'])
    bench, _, _ = fund.run({'229200': px['229200']}, W, start=params['v_start'])
    n_tr = validate.registry_count(str(OUT)) + len(grid)
    outdir = OUT if which == 'd10' else OUT / 'validation_i30'
    t0 = time.time()
    res = validate.run_all(f'KQ150 사다리 추천안 ({"ETF 일봉 2016-06~" if which == "d10" else "지수 대용 이어붙인 일봉 1997-07~"})',
                           strategy, params, px, bench, outdir=str(outdir), grid=grid, n_trials=n_tr, source='own', time_budget=1500)
    print(which, res['auto_verdict'], round(time.time() - t0), 's')


# ================================================================ 설계 보강 (연속 실행 결과를 보고 추가 — 보고서에 공개)
# 이유: 1997년부터 이어 돌린 사다리는 2000년 닷컴 붕괴에서 20포트폴리오가 모두 물려 2006년 이후 모든 신호 A 시점에 노출 100%였다
#       (매집 규칙이 한 번도 작동 안 함). 2016~21 ETF 일봉도 2019·2020 신호 때 사다리가 이미 소진. 그래서
#   (1) 구간별 새 출발: 신호 A 구간마다 T+1일부터 같은 1억·20포트폴리오를 새로 시작 → 구간 종료 / 250거래일 / 500거래일 시점 평가
#   (2) 5년 롤링 새 출발: 1998~2021년 매년 첫 거래일에 새로 시작해 5년 운용 (이어 붙인 일봉) → 경로 의존성 제거
def _mark(eq, d0, k):
    x = eq[eq.index >= d0]
    return x.iloc[min(k, len(x) - 1)], x.index[min(k, len(x) - 1)], len(x) > k


def episode_study(data, variants, kinds=('i30', 'm5'), cost_mult=1.0, tag=''):
    rows = []
    for kind in kinds:
        full = data['S'] if kind == 'i30' else data['D']
        key = (kind, BASE['dip_target'], BASE['dip_max'], True)
        if key not in _TCACHE: _TCACHE[key] = day_table(full, data['K'], BASE)
        eps = _TCACHE[key].attrs['episodes']
        idx = full.index
        for s0, s1, hit in eps:
            if kind == 'm5' and s0 < pd.Timestamp('2021-09-02'): continue
            i0 = idx.get_loc(s0)
            if i0 + 1 >= len(idx): continue
            a = idx[i0 + 1]; b = idx[min(i0 + 500, len(idx) - 1)]
            c0 = full['close'].loc[s0]
            o1 = full['open'].loc[a] + TICK; bh_cost = o1 * (1 + FEE)          # B&H: T+1 시가 1틱 불리 + 수수료
            for name, p in variants.items():
                sim = simulate(p, kind, data, cost_mult=cost_mult, win=(a, b))
                eq = sim['eq']; e = pd.concat([pd.Series([CAPITAL], index=[s0]), eq])
                n_reg = int(((eq.index > s0) & (eq.index <= s1)).sum())
                v_end = e.loc[:s1].iloc[-1]
                v1, d1, ok1 = _mark(e, s0, 250); v2, d2, ok2 = _mark(e, s0, 500)
                e1 = e[e.index <= d1]
                days = sim['bar_day']
                reg_buys = sum(1 for bt, st, bc, sp, dp in sim['trades'] if dp) + sum(1 for q in sim['openpos'] if q[3])
                reg_sells = sum(1 for bt, st, bc, sp, dp in sim['trades'] if dp and days[st] <= s1)
                fc = full['close']
                rows.append(dict(kind=kind, variant=name, start=str(s0.date()), regime_end=str(s1.date()), target_hit=bool(hit),
                                 regime_days=n_reg, ret_regime_end=v_end / CAPITAL - 1, ret_1y=v1 / CAPITAL - 1, complete_1y=ok1,
                                 ret_2y=v2 / CAPITAL - 1, complete_2y=ok2, mdd_1y=float((e1 / e1.cummax() - 1).min()),
                                 avg_invested_1y=float(sim['expo'][sim['expo'].index <= d1].mean()),
                                 regime_buys=reg_buys, regime_sells=reg_sells,
                                 bh_regime_end=(fc.loc[:s1].iloc[-1] * (1 - FEE) - TICK) / bh_cost - 1,
                                 bh_1y=(fc.loc[:d1].iloc[-1] * (1 - FEE) - TICK) / bh_cost - 1,
                                 bh_2y=(fc.loc[:d2].iloc[-1] * (1 - FEE) - TICK) / bh_cost - 1))
                validate.registry_log(str(OUT), 'kq150_review_episode', dict(p, dataset=kind, episode=str(s0.date()), cost_mult=cost_mult), float('nan'))
    return pd.DataFrame(rows)


def rolling_study(data, variants, years=5, cost_mult=1.0):
    S = data['S']; rows = []
    bench = bh('i30', data)
    for y in range(1998, 2022):
        a = S.index[S.index >= f'{y}-01-01'][0]
        b_ = S.index[S.index <= f'{y + years}-01-01'][-1]
        bm = fund.metrics(bench[(bench.index > a) & (bench.index <= b_)])
        for name, p in variants.items():
            sim = simulate(p, 'i30', data, cost_mult=cost_mult, win=(a, b_))
            r = sim['r']; m = fund.metrics(r, bench, sim['expo'].shift(1).fillna(0))
            rows.append(dict(start=y, variant=name, CAGR=m['CAGR'], MDD=m['MDD'], Sharpe=m['Sharpe'], vol=m['vol'],
                             avg_invested=float(sim['expo'].mean()), sells=sim['ns'],
                             BH_CAGR=bm['CAGR'], BH_MDD=bm['MDD'], BH_Sharpe=bm['Sharpe']))
            validate.registry_log(str(OUT), 'kq150_review_rolling', dict(p, dataset='i30_roll5y', start=y, cost_mult=cost_mult), m['Sharpe'])
    return pd.DataFrame(rows)


def q1_variants():
    V_ = {'현행 max(1.0ATR,3%)': V()}
    for k in (0.5, 0.75, 1.0, 1.25, 1.5): V_[f'ATR {k}×'] = V(gap_k=k, gap_floor=0.0)
    for f in (0.015, 0.02, 0.03, 0.04): V_[f'고정 {f:.1%}'] = V(gap_k=0.0, gap_floor=f)
    for k, f in ((0.75, 0.02), (0.75, 0.03), (1.0, 0.02), (1.0, 0.04), (1.25, 0.03)): V_[f'혼합 max({k}ATR,{f:.0%})'] = V(gap_k=k, gap_floor=f)
    return V_


def summarize_rolling(df, base):
    out = []
    b = df[df.variant == base].set_index('start')
    for v, g in df.groupby('variant', sort=False):
        g = g.set_index('start')
        out.append(dict(variant=v, n=len(g), Sharpe_med=g.Sharpe.median(), Sharpe_mean=g.Sharpe.mean(), CAGR_med=g.CAGR.median(),
                        CAGR_mean=g.CAGR.mean(), MDD_med=g.MDD.median(), MDD_worst=g.MDD.min(), invested=g.avg_invested.mean(),
                        win_vs_base=float((g.Sharpe > b.Sharpe.reindex(g.index) + 1e-9).mean()),
                        tie_vs_base=float((abs(g.Sharpe - b.Sharpe.reindex(g.index)) <= 1e-9).mean()),
                        BH_Sharpe_med=g.BH_Sharpe.median(), BH_CAGR_med=g.BH_CAGR.median(), BH_MDD_worst=g.BH_MDD.min()))
    return pd.DataFrame(out)


def summarize_episodes(df, base):
    out = []
    for (kind, v), g in df.groupby(['kind', 'variant'], sort=False):
        b = df[(df.kind == kind) & (df.variant == base)].set_index('start'); g = g.set_index('start')
        c1 = g[g.complete_1y]; bb = b.reindex(c1.index)
        g = g[~((~g.target_hit) & (g.regime_end >= END))]   # 진행 중(2026-10-15~) 구간은 구간 통계에서 제외
        out.append(dict(kind=kind, variant=v, n_regime=len(g), ret_regime_mean=g.ret_regime_end.mean(), ret_regime_med=g.ret_regime_end.median(),
                        ret_regime_worst=g.ret_regime_end.min(), n_1y=len(c1), ret_1y_mean=c1.ret_1y.mean(), ret_1y_med=c1.ret_1y.median(),
                        ret_1y_worst=c1.ret_1y.min(), mdd_1y_worst=c1.mdd_1y.min(), invested_1y=c1.avg_invested_1y.mean(),
                        win_1y_vs_base=int((c1.ret_1y > bb.ret_1y + 1e-9).sum()), loss_1y_vs_base=int((c1.ret_1y < bb.ret_1y - 1e-9).sum()),
                        win_regime_vs_base=int((g.ret_regime_end > b.ret_regime_end.reindex(g.index) + 1e-9).sum()),
                        loss_regime_vs_base=int((g.ret_regime_end < b.ret_regime_end.reindex(g.index) - 1e-9).sum()),
                        bh_1y_mean=c1.bh_1y.mean(), regime_sells=g.regime_sells.mean()))
    return pd.DataFrame(out)


def stage_episodes(data):
    V_ = q2_variants(); V_.pop('매집 구간 없음(평상 사다리만)')
    dg = {'매집간격 max(0.3ATR,1.5%)': V(dip_gap_k=0.3), '매집간격 고정 1.5%': V(dip_gap_k=0.0), '매집간격 max(1.0ATR,1.5%)': V(dip_gap_k=1.0),
          '매집간격 고정 3%': V(dip_gap_k=0.0, dip_gap_min=0.03)}
    allv = {**V_, **dg}
    df = episode_study(data, allv)
    df2 = episode_study(data, V_, cost_mult=2.0)
    df.to_csv(OUT / 'episodes.csv', index=False, encoding='utf-8-sig'); df2.to_csv(OUT / 'episodes_cost2x.csv', index=False, encoding='utf-8-sig')
    s1 = summarize_episodes(df, '현행 일괄(구간 목표가, 종료 후 유지)'); s2 = summarize_episodes(df2, '현행 일괄(구간 목표가, 종료 후 유지)')
    s1.to_csv(OUT / 'episodes_summary.csv', index=False, encoding='utf-8-sig'); s2.to_csv(OUT / 'episodes_summary_cost2x.csv', index=False, encoding='utf-8-sig')
    pd.set_option('display.width', 300); pd.set_option('display.max_columns', 30)
    print(s1.round(3).to_string(index=False)); print(s2.round(3).to_string(index=False))


def stage_rolling(data):
    V_ = {**q1_variants(), **{k: v for k, v in q2_variants().items() if k != '현행 일괄(구간 목표가, 종료 후 유지)'}}
    df = pd.concat([rolling_study(data, V_), rolling_study(data, {'현행 [비용2배]': V()}, cost_mult=2.0)])
    df.to_csv(OUT / 'rolling5y.csv', index=False, encoding='utf-8-sig')
    s = summarize_rolling(df, '현행 max(1.0ATR,3%)'); s.to_csv(OUT / 'rolling5y_summary.csv', index=False, encoding='utf-8-sig')
    pd.set_option('display.width', 300); pd.set_option('display.max_columns', 30)
    print(s.round(3).to_string(index=False))


def extra_variants():
    """연속·롤링 결과를 본 뒤 추가한 변형(사후 추가, 보고서에 공개): 시한 종료 때만 남은 매집 포트폴리오를 평상시 익절로 전환."""
    return {'일괄 + 시한종료만 평상 전환': V(dip_end='convert_timeout'),
            '일괄 + 시한종료 전환 + 매집간격 고정 1.5%': V(dip_end='convert_timeout', dip_gap_k=0.0)}


def stage_extra(data):
    base = {'현행 일괄(구간 목표가, 종료 후 유지)': V(), '일괄(구간 목표가, 종료 후 평상 전환)': V(dip_end='convert'),
            '매집간격 고정 1.5%': V(dip_gap_k=0.0)}
    EV = extra_variants()
    rows = [evaluate_cfg(n, p, data) for n, p in {**base, **EV}.items()]
    sel, pick = select(rows, '현행 일괄(구간 목표가, 종료 후 유지)')
    table(rows).to_csv(OUT / 'extra_table.csv', index=False, encoding='utf-8-sig')
    ep = episode_study(data, {**base, **EV}); ep.to_csv(OUT / 'episodes_extra.csv', index=False, encoding='utf-8-sig')
    es = summarize_episodes(ep, '현행 일괄(구간 목표가, 종료 후 유지)'); es.to_csv(OUT / 'episodes_extra_summary.csv', index=False, encoding='utf-8-sig')
    ro = rolling_study(data, EV); ro.to_csv(OUT / 'rolling5y_extra.csv', index=False, encoding='utf-8-sig')
    allro = pd.concat([pd.read_csv(OUT / 'rolling5y.csv'), ro])
    rs = summarize_rolling(allro, '현행 max(1.0ATR,3%)'); rs.to_csv(OUT / 'rolling5y_summary_all.csv', index=False, encoding='utf-8-sig')
    dump(dict(rows=rows, select=sel.to_dict('records'), pick=pick), 'extra.json')
    pd.set_option('display.width', 300); pd.set_option('display.max_columns', 30)
    print(sel.to_string()); print(es.round(3).to_string(index=False))
    print(rs[rs.variant.isin(list(EV) + ['현행 max(1.0ATR,3%)', '일괄(구간 목표가, 종료 후 평상 전환)'])].round(3).to_string(index=False))


def stage_robust(data):
    """robustness.json: 변형별 full/OOS(Sharpe·CAGR·MDD), 하위기간(전반/후반), 비용·슬리피지·현금, 롤링·구간 요약."""
    def pick(r):
        out = {}
        for s in list(SETS) + list(FULL):
            m = r.get(s, {})
            out[s] = {k: m.get(k) for k in ('CAGR', 'MDD', 'Sharpe', 'Sortino', 'vol', 'avg_invested', 'sells_per_year')}
        return out
    R = dict(note='full = M5_full/D10_full/I30_full, OOS = M5_OOS(2024-07~). 전반/후반 = M5_IS/M5_OOS, D_16_21/D10 후반, IDX_97_15/I30 후반(final 참조). '
                  'Sharpe 는 fund.metrics(무위험 ^IRX 차감).', sets=dict(SETS, **FULL))
    for f, keys in (('q1.json', ('rows', 'dip_rows')), ('q2.json', ('rows',)), ('q3b.json', ('rows',)), ('extra.json', ('rows',))):
        x = json.load(open(OUT / f))
        for k in keys:
            R[f'{f[:-5]}_{k}'] = [dict(name=r['name'], params=r['params'], cost_mult=r['cost_mult'], **pick(r)) for r in x[k]]
    fin = json.load(open(OUT / 'final.json'))
    R['final'] = {nm: {tag: dict(**pick(v[tag]), halves={k: v[tag].get(f'halves_{k}') for k in ('m5', 'd10', 'i30')})
                       for tag in v} for nm, v in fin.items()}
    for f in ('rolling5y_summary_all.csv', 'episodes_summary.csv', 'episodes_summary_cost2x.csv', 'episodes_extra_summary.csv'):
        R[f[:-4]] = pd.read_csv(OUT / f).to_dict('records')
    R['n_registry_trials'] = validate.registry_count(str(OUT))
    dump(R, 'robustness.json')


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('stage', nargs='?', default='all'); a = ap.parse_args()
    data = load_all()
    print('splice ratio', data['ratio'], 'bars m5', len(data['m5']), 'S', data['S'].index[0].date(), data['S'].index[-1].date())
    if a.stage in ('all', 'q1'): q1(data)
    if a.stage in ('all', 'q2'): q2(data)
    if a.stage in ('all', 'q3b'): q3b(data)
    if a.stage in ('all', 'episodes'): stage_episodes(data)
    if a.stage in ('all', 'rolling'): stage_rolling(data)
    if a.stage in ('all', 'extra'): stage_extra(data)
    if a.stage in ('all', 'final'): stage_final(data)
    if a.stage in ('all', 'validate'): stage_validate(data, 'd10'); stage_validate(data, 'i30')
    if a.stage == 'validate_d10': stage_validate(data, 'd10')
    if a.stage == 'validate_i30': stage_validate(data, 'i30')
    if a.stage in ('all', 'robust'): stage_robust(data)


if __name__ == '__main__':
    main()
