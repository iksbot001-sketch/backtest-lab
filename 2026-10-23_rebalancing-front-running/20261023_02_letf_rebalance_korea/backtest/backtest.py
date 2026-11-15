"""
20261023_02_letf_rebalance_korea — 단일종목 2배 LETF 상장 후 '미국 장 충격 → 다음날 되돌림' 역추세 규칙
원문: Zhao (2026) "Preying on Leveraged ETFs", arXiv:2608.03703 v4.

실행: ~/agent-fund/venv/bin/python backtest.py
산출: metrics.json, equity.png (fund.evaluate), robustness.json, falsification.json, loss_structure.json

[체결·비용 설계 메모 — CRO 확인용]
- 주 규칙은 원문 종속변수 ln(C_{t+1}/C_t) 그대로 "t 종가 단일가 진입 → t+1 종가 청산"이다.
  신호 s_t 는 한국 개장(09:00) 4시간 전에 끝난 미국 장 종가로 확정되므로 t 종가 체결에 미래정보가 없다.
  fund.run 은 "t 종가 결정 → t+1 시가 체결 → 다음 시가까지 보유(시가→시가)"만 표현하므로 종가→종가,
  시가→당일종가(변형 B), 종가→다음시가(밤사이) 는 fund.run 으로 표현할 수 없다.
  → 이 세 가지는 수익률을 직접 계산하고(sim_cc / sim_intraday), 비용은 fund.run 과 같은 정의
     (편도 fund.COST['KR']['fee']=0.015% + 1틱 fund.kr_tick(체결가)/체결가) 를 포지션 변화량에 부과한다.
     종가→종가는 포지션이 바뀔 때만(순변화량), 변형 B·밤사이는 매일 왕복(진입+청산 2회)이다.
  → 엔진에 없는 한국 증권거래세(2026년 KOSPI 0.05% + 농특세 0.15% = 0.20%)는 매도 체결 금액에 부과한다.
     (롱 청산·숏 진입 모두 '매도'이므로 tax = 0.20% × max(0, w_old − w_new)).
  → 표준 엔진 버전(fund.run, W_t=d_t → t+1 시가~t+2 시가 보유)도 참고 변형으로 같이 보고하고, 거래세는 수동 차감.
- Buy&Hold 벤치마크: 처리군 2종목 50:50 정적 보유를 fund.run 으로 계산(비중 불변이므로 진입 후 비용 없음).
- 현금: fund.cash_daily(^IRX). 직접 계산 버전은 max(0, 1−Σ|w|) 에만 현금이자를 준다(숏 매도대금 이자 없음, 대차수수료 미반영).
- cost_mult 는 수수료+틱에만 곱한다(fund.run 과 동일). 거래세는 법정세율이라 1배 고정(전부 2배 변형도 별도 보고).
"""
import sys, json, warnings
from pathlib import Path
warnings.filterwarnings('ignore')
sys.path.insert(0, '~/agent-fund/lib')
import fund
import numpy as np, pandas as pd

RUN = Path('~/agent-fund/runs/20261023_02_letf_rebalance_korea')
OUT = RUN / 'backtest'; OUT.mkdir(exist_ok=True)
spec = json.load(open(RUN / 'spec.json'))

SAMPLE_START, SAMPLE_END = '2024-01-02', '2026-10-22'
LAUNCH, IS_END, OOS = '2026-05-27', '2026-07-31', '2026-08-03'
TAX = 0.0020          # 증권거래세+농특세 (매도 시)
FEE = fund.COST['KR']['fee']
LETF_FEE = 0.0029     # 합성 LETF 총보수(연)

TREATED = ['005930', '000660']
TECH = ['009150', '066570', '034220', '011070', '042700', '000990', '108320', '018260', '035420', '035720']
LARGE = ['373220', '207940', '005380', '000270', '068270', '105560', '055550', '005490', '012450', '329180']
NAMES = {'005930': '삼성전자', '000660': 'SK하이닉스'}

# ------------------------------------------------------------------ data
px = {}
for c in TREATED + TECH + LARGE:
    d = fund.kr(c)
    px[c] = d.loc[:SAMPLE_END]
CAL = px['005930'].loc[SAMPLE_START:SAMPLE_END].index          # 한국 거래일 달력(처리군 기준)
US = {t: fund.us(t, refresh=True) for t in ['QQQ', 'SMH', 'SPY']}

C = pd.DataFrame({c: px[c]['close'] for c in px}).reindex(CAL)
O = pd.DataFrame({c: px[c]['open'] for c in px}).reindex(CAL)
CASH = fund.cash_daily(CAL)


def shock(tkr):
    """s_t = ln(US종가[날짜 ≤ t−1일] / US종가[날짜 ≤ t⁻−1일]). 미국 장은 한국 t일 05~06시에 끝나므로 t 개장 전 확정."""
    p = US[tkr]['adj'].sort_index()
    last = lambda d: p.loc[:d - pd.Timedelta(days=1)].iloc[-1]
    full = px['005930'].index
    full = full[full >= pd.Timestamp('2023-11-01')]
    v = pd.Series([np.log(last(d)) for d in full], index=full)
    return v.diff().reindex(CAL)        # 직전 한국 거래일 대비 누적(한국 휴장 시 누적, 미국 휴장 시 0)


S = {t: shock(t) for t in US}


def threshold(s, kind='median', window='expanding'):
    """t−1 까지의 |s| 분포로 임계값(미래정보 차단: shift(1)). 2024-01-02 부터 누적."""
    a = s.abs()
    if kind == 'zero':
        return pd.Series(0.0, index=s.index)
    q = 0.5 if kind == 'median' else 2 / 3
    if window == 'expanding':
        m = a.expanding(min_periods=1).quantile(q)
    else:
        m = a.rolling(250, min_periods=1).quantile(q)
    return m.shift(1)


def direction(s, m, long_only=False):
    big = (s.abs() >= m) & m.notna() & (s != 0)
    d = -np.sign(s).where(big, 0.0)
    if long_only:
        d = d.clip(lower=0)          # 미국 큰 하락(s ≤ −m)일만 롱
    return d.fillna(0.0)


# ------------------------------------------------------------------ simulators (fund.run 으로 표현 불가한 체결)
def tick_frac(p):
    return pd.DataFrame(fund.kr_tick(p.fillna(1e9).values), index=p.index, columns=p.columns) / p.fillna(1e9)


def sim_cc(W, start, end, cost_mult=1.0, tax=True, tax_mult=1.0, liquidate=True):
    """종가→종가. W: index=거래일 t, 값=t 종가에 맞출 목표비중. 일수익(t)=Σ W_{t-1}·(C_t/C_{t-1}−1) + 현금 − t 종가 체결비용."""
    W = W.reindex(CAL).fillna(0.0)
    m = (CAL >= pd.Timestamp(start)) & (CAL <= pd.Timestamp(end))
    W = W.where(pd.Series(m, index=CAL), 0.0)              # 창 밖에서는 포지션 없음(창 시작일 종가에 첫 진입)
    cols = W.columns
    Cc = C[cols]
    ret = (Cc / Cc.shift(1) - 1)
    Wp = W.shift(1).fillna(0.0)
    valid = ret.notna()
    gross = (Wp * ret.fillna(0)).sum(1) + (1 - Wp.abs().sum(1)).clip(lower=0) * CASH
    dW = (W - Wp)
    dW = dW.where(Cc.notna(), 0.0)                          # 거래정지일은 체결 불가 → 근사: 비용만 무시(대조군 일부)
    cost = (dW.abs() * (FEE + tick_frac(Cc))).sum(1) * cost_mult
    if tax:
        cost += (-dW).clip(lower=0).sum(1) * TAX * tax_mult
    r = (gross - cost)[m].copy()
    if liquidate:   # 표본 끝 종가에 청산 비용
        wl = W[m].iloc[-1]
        lc = (wl.abs() * (FEE + tick_frac(Cc[m]).iloc[-1])).sum() * cost_mult + (wl.clip(lower=0).sum()) * TAX * tax_mult * tax
        r.iloc[-1] -= lc
    pos = Wp.abs().sum(1)[m]
    to = dW.abs().sum(1)[m]
    return r, pos, to


def sim_intraday(D, start, end, mode, cost_mult=1.0, tax=True, tax_mult=1.0):
    """하루 단위 왕복.
    mode='B'  : t 종가 결정 신호 D_t → t+1 시가 진입, t+1 종가 청산. 일수익(t+1)=D_t·(C/O−1) − 왕복비용
    mode='ON' : t 종가 진입 → t+1 시가 청산. 일수익(t+1)=D_t·(O_{t+1}/C_t−1) − 왕복비용
    왕복비용 = |w|·(2·0.015% + 진입틱/진입가 + 청산틱/청산가)·cost_mult + 0.20% 거래세(매도 1회)."""
    D = D.reindex(CAL).fillna(0.0)
    m = (CAL >= pd.Timestamp(start)) & (CAL <= pd.Timestamp(end))
    D = D.where(pd.Series(m, index=CAL), 0.0)
    cols = D.columns
    Wp = D.shift(1).fillna(0.0)
    if mode == 'B':
        ret = C[cols] / O[cols] - 1
        tk = tick_frac(O[cols]) + tick_frac(C[cols])
    else:
        ret = O[cols] / C[cols].shift(1) - 1
        tk = tick_frac(C[cols].shift(1).bfill()) + tick_frac(O[cols])
    Wp = Wp.where(ret.notna(), 0.0)
    gross = (Wp * ret.fillna(0)).sum(1) + (1 - Wp.abs().sum(1)).clip(lower=0) * CASH
    cost = (Wp.abs() * (2 * FEE + tk)).sum(1) * cost_mult
    if tax:
        cost += Wp.abs().sum(1) * TAX * tax_mult
    r = (gross - cost)[m].copy()       # 창 시작 전 신호는 0으로 마스킹되어 첫날 포지션 없음
    return r, Wp.abs().sum(1)[m], (2 * Wp.abs().sum(1))[m]


def sim_engine(W, start, end, cost_mult=1.0):
    """표준 엔진 fund.run: W_t 결정(t 종가) → t+1 시가 체결, t+2 시가까지 보유. 거래세는 수동 차감."""
    W = W.reindex(CAL).fillna(0.0)
    W = W.where(pd.Series(CAL >= pd.Timestamp(start), index=CAL), 0.0)
    r, pos, to = fund.run({c: px[c] for c in W.columns}, W, start=start, end=end, cost_mult=cost_mult)
    Wp, Wpp = W.shift(1).fillna(0), W.shift(2).fillna(0)
    tax = ((Wpp - Wp).clip(lower=0).sum(1) * TAX).reindex(r.index)
    return r - tax, pos.abs(), to


# ------------------------------------------------------------------ stats
def mstats(r):
    r = r.dropna()
    if len(r) < 2:
        return {}
    eq = (1 + r).cumprod(); n = len(r) / 252
    ex = r - CASH.reindex(r.index).fillna(0)
    sd = ex.std()
    return dict(start=str(r.index[0].date()), end=str(r.index[-1].date()), days=int(len(r)),
                ROI=float(eq.iloc[-1] - 1), CAGR=float(eq.iloc[-1] ** (1 / n) - 1) if eq.iloc[-1] > 0 else -1.0,
                MDD=float((eq / eq.cummax() - 1).min()), vol=float(r.std() * np.sqrt(252)),
                Sharpe=float(ex.mean() / sd * np.sqrt(252)) if sd > 0 else None)


def periods(r):
    sub = {'full': (LAUNCH, SAMPLE_END), 'IS': (LAUNCH, IS_END), 'OOS': (OOS, SAMPLE_END),
           'OOS_Aug': (OOS, '2026-08-31'), 'OOS_SepOct': ('2026-09-01', SAMPLE_END)}
    res = {k: mstats(r.loc[a:b]) for k, (a, b) in sub.items()}
    rr = r.loc[LAUNCH:SAMPLE_END]; h = len(rr) // 2
    res['first_half'] = mstats(rr.iloc[:h]); res['second_half'] = mstats(rr.iloc[h:])
    return res


def ols_cluster(y, X, groups):
    """OLS + 날짜 군집 표준오차(CR1)."""
    X = np.column_stack([np.ones(len(y)), X]); y = np.asarray(y)
    XtXi = np.linalg.inv(X.T @ X); b = XtXi @ X.T @ y; e = y - X @ b
    g = pd.Series(range(len(y))).groupby(np.asarray(groups)).apply(list)
    meat = sum(np.outer(X[i].T @ e[i], X[i].T @ e[i]) for i in g)
    G, n, k = len(g), len(y), X.shape[1]
    V = XtXi @ meat @ XtXi * (G / (G - 1)) * ((n - 1) / (n - k))
    se = np.sqrt(np.diag(V))
    return dict(b=float(b[1]), se=float(se[1]), t=float(b[1] / se[1]), c_next=float(b[2]), n=int(n), clusters=int(G))


def reg(codes, tkr, a, b, drop_big=False, drop_july=False):
    """r_{i,t+1} = a + b·s_t + c·s_{t+1} (ln 종가→종가), t ∈ [a,b]. 날짜 군집."""
    s = S[tkr]; rows = []
    lr = np.log(C[codes]).diff().shift(-1)        # t 행 = ln(C_{t+1}/C_t)  (회귀 종속변수 — 신호에는 쓰지 않음)
    for c in codes:
        df = pd.DataFrame({'y': lr[c], 's': s, 's1': s.shift(-1)}).loc[a:b].dropna()
        df['date'] = df.index
        rows.append(df)
    df = pd.concat(rows)
    if drop_big:
        df = df[df.y.abs() <= np.log(1.10)]
    if drop_july:
        df = df[~((df.index >= '2026-07-01') & (df.index <= '2026-07-31'))]
    return ols_cluster(df.y.values, df[['s', 's1']].values, df.date.values)


# ------------------------------------------------------------------ strategy builder
def weights(codes, shock_t='QQQ', thr='median', window='expanding', long_only=False, hold=1):
    s = S[shock_t]; m = threshold(s, thr, window)
    d = direction(s, m, long_only)
    if hold == 2:
        d = (d + d.shift(1).fillna(0)) / 2
    return pd.DataFrame({c: d / len(codes) for c in codes})


def strat(codes=TREATED, exec_='cc', start=LAUNCH, end=SAMPLE_END, cost_mult=1.0, tax=True, tax_mult=1.0, **kw):
    W = weights(codes, **kw)
    if exec_ == 'cc':
        return sim_cc(W, start, end, cost_mult, tax, tax_mult)
    if exec_ in ('B', 'ON'):
        return sim_intraday(W, start, end, exec_, cost_mult, tax, tax_mult)
    if exec_ == 'engine':
        return sim_engine(W, start, end, cost_mult)


def bh(codes, start=LAUNCH, end=SAMPLE_END):
    W = pd.DataFrame({c: 1.0 / len(codes) for c in codes}, index=CAL)
    r, _, _ = fund.run({c: px[c] for c in codes}, W, start=start, end=end)
    return r


# ================================================================== main
r, pos, to = strat()
r2, _, _ = strat(cost_mult=2.0)
bench = bh(TREATED)
sig = weights(TREATED)['005930'] * 2
sig_post = sig.loc[LAUNCH:SAMPLE_END]

# ---------------- falsification
F = {}
F['F0_IS_reg_QQQ'] = reg(TREATED, 'QQQ', LAUNCH, IS_END)
F['F0_IS_reg_SMH'] = reg(TREATED, 'SMH', LAUNCH, IS_END)
F['F0_IS_reg_SPY'] = reg(TREATED, 'SPY', LAUNCH, IS_END)
F['F0_pass(b_QQQ<=-0.5)'] = F['F0_IS_reg_QQQ']['b'] <= -0.5
F['F1_OOS_reg_QQQ'] = reg(TREATED, 'QQQ', OOS, SAMPLE_END)
F['F1_OOS_reg_SMH'] = reg(TREATED, 'SMH', OOS, SAMPLE_END)
F['F1_OOS_reg_SPY'] = reg(TREATED, 'SPY', OOS, SAMPLE_END)
b1 = F['F1_OOS_reg_QQQ']
F['F1_verdict'] = 'reject' if b1['b'] >= 0 else ('pending(t>-1.65)' if b1['t'] > -1.65 else 'pass')
# F2: OOS 순수익 (주 규칙 / 변형 A)
rA, posA, _ = strat(long_only=True)


def trade_stats(r_, pos_):
    on = (pos_ > 0).astype(int); g = (on.diff().fillna(on.iloc[0]) == 1).cumsum()
    t = np.array([(1 + x).prod() - 1 for _, x in r_[on == 1].groupby(g[on == 1])])
    return dict(n=int(len(t)), mean=float(t.mean()) if len(t) else None)


F['F2'] = {}
for nm, (rr, pp) in {'main': (r, pos), 'A_longonly': (rA, posA)}.items():
    ro, po = rr.loc[OOS:], pp.loc[OOS:]
    F['F2'][nm] = dict(OOS_cum=float((1 + ro).prod() - 1), OOS_trades=trade_stats(ro, po))
F['F2_verdict'] = 'reject' if all(v['OOS_cum'] <= 0 or (v['OOS_trades']['mean'] or 0) <= 0 for v in F['F2'].values()) else 'pass'
# F3: placebo (상장 전)
rp, _, _ = strat(start=SAMPLE_START, end='2026-05-26', cost_mult=0.0, tax=False)
rpn, _, _ = strat(start=SAMPLE_START, end='2026-05-26')
F['F3_placebo_gross'] = mstats(rp); F['F3_placebo_net'] = mstats(rpn)
F['F3_placebo_reg_QQQ'] = reg(TREATED, 'QQQ', SAMPLE_START, '2026-05-26')
F['F3_verdict'] = 'reject_LETF_causality' if (F['F3_placebo_gross']['Sharpe'] > 0.5 or F['F3_placebo_reg_QQQ']['b'] < -0.5) else 'pass'
# F4: 대조군 (상장 후 전체)
F['F4_treated_post_reg_QQQ'] = reg(TREATED, 'QQQ', LAUNCH, SAMPLE_END)
F['F4_tech_post_reg_QQQ'] = reg(TECH, 'QQQ', LAUNCH, SAMPLE_END)
F['F4_large_post_reg_QQQ'] = reg(LARGE, 'QQQ', LAUNCH, SAMPLE_END)
F['F4_tech_per_stock_b'] = {c: reg([c], 'QQQ', LAUNCH, SAMPLE_END)['b'] for c in TECH}
F['F4_large_per_stock_b'] = {c: reg([c], 'QQQ', LAUNCH, SAMPLE_END)['b'] for c in LARGE}
bt = F['F4_treated_post_reg_QQQ']['b']
F['F4_verdict'] = {g: ('reject_specificity' if F[f'F4_{g}_post_reg_QQQ']['b'] < bt / 2 else 'pass') for g in ['tech', 'large']}
# F5: 소수 이벤트 의존 (IS 주 규칙 순손익)
ris = r.loc[LAUNCH:IS_END]
pnl = np.log1p(ris)
F['F5'] = dict(IS_logpnl=float(pnl.sum()), IS_ex_top3=float(pnl.sum() - pnl.nlargest(3).sum()),
               IS_ex_July=float(pnl[~((pnl.index >= '2026-07-01') & (pnl.index <= '2026-07-31'))].sum()),
               top3_days={str(k.date()): float(v) for k, v in pnl.nlargest(3).items()})
F['F5_verdict'] = 'fragile' if (F['F5']['IS_ex_top3'] <= 0 or F['F5']['IS_ex_July'] <= 0) else 'pass'
# 추가 회귀 절단 (원문 Table A6 대응)
F['reg_cuts_post_QQQ'] = {
    'IS_drop_|r|>10%': reg(TREATED, 'QQQ', LAUNCH, IS_END, drop_big=True),
    'IS_drop_July': reg(TREATED, 'QQQ', LAUNCH, IS_END, drop_july=True),
    'IS_hynix': reg(['000660'], 'QQQ', LAUNCH, IS_END), 'IS_samsung': reg(['005930'], 'QQQ', LAUNCH, IS_END),
    'OOS_hynix': reg(['000660'], 'QQQ', OOS, SAMPLE_END), 'OOS_samsung': reg(['005930'], 'QQQ', OOS, SAMPLE_END)}

# 신호 통계
sq = S['QQQ']; mq = threshold(sq)
F['signal_stats'] = dict(
    post_signal_rate=float((sig_post != 0).mean()), post_long_days=int((sig_post > 0).sum()), post_short_days=int((sig_post < 0).sum()),
    median_threshold_at_launch=float(mq.loc[LAUNCH]), median_threshold_end=float(mq.iloc[-1]),
    mean_abs_s_signal_days_IS=float(sq.loc[LAUNCH:IS_END][sig.loc[LAUNCH:IS_END] != 0].abs().mean()),
    mean_abs_s_signal_days_OOS=float(sq.loc[OOS:][sig.loc[OOS:] != 0].abs().mean()),
    IS_days=int(len(CAL[(CAL >= LAUNCH) & (CAL <= IS_END)])), OOS_days=int(len(CAL[CAL >= OOS])))

# ---------------- robustness
V = {}
def add(name, res, note=''):
    rr = res[0]
    V[name] = dict(note=note, **periods(rr), annual_turnover=float(res[2].sum() / (len(res[2]) / 252)))

add('base_QQQ_median_cc_both', (r, pos, to))
add('shock_SMH', strat(shock_t='SMH')); add('shock_SPY', strat(shock_t='SPY'))
add('thr_zero_all_days', strat(thr='zero')); add('thr_top_third', strat(thr='top3'))
add('median_rolling250', strat(window='rolling'))
add('exec_B_open_t1_to_close_t1', strat(exec_='B'), '변형 B: 다음날 장중만')
add('exec_overnight_close_t_to_open_t1', strat(exec_='ON'), '밤사이만')
add('exec_engine_fund_run_open_to_open', strat(exec_='engine'), '표준 엔진(t+1 시가~t+2 시가)')
add('A_longonly_down_shock_cc', (rA, posA, strat(long_only=True)[2]))
add('A_longonly_exec_B', strat(long_only=True, exec_='B'))
add('hold_2d', strat(hold=2))
add('cost_2x_fee_tick', strat(cost_mult=2.0)); add('cost_2x_incl_tax', strat(cost_mult=2.0, tax_mult=2.0))
add('cost_no_tax', strat(tax=False)); add('gross_no_cost', strat(cost_mult=0.0, tax=False))
add('only_hynix', strat(codes=['000660'])); add('only_samsung', strat(codes=['005930']))
# 절단: 결과 수익률에서 해당 일자 제거(사후 절단 — 민감도 확인용)
rr_ = r.copy()
big = (C[TREATED].pct_change().abs() > 0.10).any(axis=1).reindex(rr_.index)
add('cut_ex_|r|>10%_days', (rr_[~big], pos[~big], to[~big]), '처리군 중 하나라도 |r|>10%인 날 수익 제거')
jul = (rr_.index >= '2026-07-01') & (rr_.index <= '2026-07-31')
add('cut_ex_July2026', (rr_[~jul], pos[~jul], to[~jul]))
add('control_tech10', strat(codes=TECH)); add('control_large10', strat(codes=LARGE))
add('control_tech10_gross', strat(codes=TECH, cost_mult=0.0, tax=False))
add('control_large10_gross', strat(codes=LARGE, cost_mult=0.0, tax=False))
add('treated_gross_only_ref', strat(cost_mult=0.0, tax=False))
add('BH_treated_5050', (bench, pd.Series(1.0, index=bench.index), pd.Series(0.0, index=bench.index)))
add('BH_tech10', (bh(TECH), pd.Series(1.0, index=bench.index), pd.Series(0.0, index=bench.index)))
add('BH_large10', (bh(LARGE), pd.Series(1.0, index=bench.index), pd.Series(0.0, index=bench.index)))

# placebo 기간 전체 지표
placebo = dict(gross=mstats(rp), net=mstats(rpn),
               longonly_gross=mstats(strat(long_only=True, start=SAMPLE_START, end='2026-05-26', cost_mult=0, tax=False)[0]),
               BH=mstats(bh(TREATED, SAMPLE_START, '2026-05-26')))
# placebo 상장일 이동: 상장 전 구간에서 임의 날짜 20개 → 이후 IS 길이(거래일)만큼 동일 규칙
rng = np.random.default_rng(20261023)
nIS = F['signal_stats']['IS_days']
pre = CAL[(CAL >= '2024-03-01') & (CAL <= pd.Timestamp('2026-05-26'))]
pre = pre[:len(pre) - nIS]
draws = sorted(rng.choice(len(pre), 20, replace=False))
pl = []
for i in draws:
    a = pre[i]; b_ = CAL[CAL.get_loc(a) + nIS - 1]
    rg, _, _ = strat(start=a, end=b_, cost_mult=0, tax=False)
    rn, _, _ = strat(start=a, end=b_)
    pl.append(dict(start=str(a.date()), end=str(b_.date()), gross_cum=float((1 + rg).prod() - 1),
                   net_cum=float((1 + rn).prod() - 1), b_QQQ=reg(TREATED, 'QQQ', a, b_)['b']))
act_g = float((1 + strat(cost_mult=0, tax=False, end=IS_END)[0]).prod() - 1)
act_b = F['F0_IS_reg_QQQ']['b']
placebo_dates = dict(n=20, draws=pl, actual_IS_gross_cum=act_g, actual_IS_b=act_b,
                     rank_gross=int(sum(p['gross_cum'] >= act_g for p in pl)),
                     rank_b_more_negative=int(sum(p['b_QQQ'] <= act_b for p in pl)))

# 7/30 리밸런싱 분산 합의 전후
pre_post_0731 = dict(before=mstats(r.loc[:IS_END]), after=mstats(r.loc[OOS:]),
                     reg_before=F['F0_IS_reg_QQQ'], reg_after=F['F1_OOS_reg_QQQ'])

json.dump(dict(variants=V, placebo_pre_launch=placebo, placebo_launch_dates=placebo_dates,
               rebal_dispersion_0731_split=pre_post_0731,
               note='임계값·체결·기간 변형은 민감도 확인용. 결과로 파라미터를 고르지 않음.'),
          open(OUT / 'robustness.json', 'w'), ensure_ascii=False, indent=1, default=float)
json.dump(F, open(OUT / 'falsification.json', 'w'), ensure_ascii=False, indent=1, default=float)

# ---------------- 손실 구조 (블로그용, 게이트 무관)
LS = {}
for c in TREATED:
    rc = C[c].pct_change()
    for nm, (a, b_) in {'to_0731': (LAUNCH, IS_END), 'to_1022': (LAUNCH, SAMPLE_END)}.items():
        x = rc.loc[a:b_].iloc[1:]        # 5/27 종가 기준 시작
        letf = (1 + 2 * x - LETF_FEE / 252).prod()
        static2 = 1 + 2 * (C[c].loc[b_] / C[c].loc[a] - 1)
        under = C[c].loc[b_] / C[c].loc[a]
        drag_log = float(np.log1p(2 * x - LETF_FEE / 252).sum() - 2 * np.log1p(x).sum())
        LS[f'{NAMES[c]}_{nm}'] = dict(underlying=float(under), synthetic_2x_daily=float(letf), static_2x=float(max(static2, 0)),
                                      won_10000_synthetic=float(10000 * letf), log_drag_vs_2x_log=drag_log,
                                      approx_minus_sum_r2=float(-(x ** 2).sum()),
                                      ann_vol_underlying=float(np.log1p(x).std() * np.sqrt(252)))
LS['note'] = '실제 LETF 6자리 코드를 샌드박스에서 조회하지 못해(ac.stock.naver.com 차단) 합성 2배(2r − 연0.29%/252)로 대체. 괴리율·스왑비용은 미반영.'
LS['paper_reference'] = 'SK하이닉스 10,000 KRW→4,790원(반사실 6,554원), 삼성 5,971원(6,740원), 2026-05-27~07-31'
json.dump(LS, open(OUT / 'loss_structure.json', 'w'), ensure_ascii=False, indent=1, default=float)

# ---------------- 표준 산출물
extra = dict(note='주 규칙은 종가→종가 직접계산(sim_cc). 비용 = 편도 0.015%+1틱 + 매도 시 거래세 0.20%. B&H=처리군 50:50 fund.run.',
             falsification_verdicts={k: F[k] for k in ['F0_pass(b_QQQ<=-0.5)', 'F1_verdict', 'F2_verdict', 'F3_verdict', 'F4_verdict', 'F5_verdict']},
             reg_IS_QQQ=F['F0_IS_reg_QQQ'], reg_OOS_QQQ=F['F1_OOS_reg_QQQ'], signal_stats=F['signal_stats'],
             G3_note='OOS 약 2.7개월(54거래일) — OOS ≥ 3년 요건 구조적 미충족. 이벤트 스터디 수준 결론.')
res = fund.evaluate('LETF reversal (QQQ shock, cc)', r, pos, bench, OOS, turnover=to, extra=extra, outdir=OUT, r_cost2=r2)
print(json.dumps({k: res[k] for k in ['full', 'IS', 'OOS', 'BH_full', 'BH_OOS']}, ensure_ascii=False, indent=1, default=float))
print(json.dumps(extra['falsification_verdicts'], ensure_ascii=False, default=float))
