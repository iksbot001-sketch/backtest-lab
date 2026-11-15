"""CRO 독립 점검. backtest.py 의 데이터·함수 정의부만 실행(산출물 덮어쓰기 방지)하고, 결과는 cro_checks/ 에만 쓴다."""
import json, sys
from pathlib import Path
import numpy as np, pandas as pd

RUN = Path('~/agent-fund/runs/20261023_02_letf_rebalance_korea')
CK = RUN / 'backtest' / 'cro_checks'
src = (RUN / 'backtest' / 'backtest.py').read_text()
head = src.split('# ================================================================== main')[0]
head = head.replace("OUT = RUN / 'backtest'; OUT.mkdir(exist_ok=True)", "OUT = Path('%s')" % CK)
REFRESH = '--norefresh' not in sys.argv
if not REFRESH:
    head = head.replace('refresh=True', 'refresh=False')
g = {'__name__': 'cro'}
exec(compile(head, 'backtest_head', 'exec'), g)
G = type('G', (), {})()
for k, v in g.items():
    setattr(G, k, v)

out = {}
r, pos, to = G.strat()
bench = G.bh(G.TREATED)
out['reproduce'] = {k: G.mstats(r.loc[a:b]) for k, (a, b) in
                    {'full': (G.LAUNCH, G.SAMPLE_END), 'IS': (G.LAUNCH, G.IS_END), 'OOS': (G.OOS, G.SAMPLE_END)}.items()}
out['us_last_dates'] = {t: str(G.US[t].index[-1].date()) for t in G.US}

# 1. 달력 점검: 상장 후 거래일, 6/3 지방선거 휴장일 포함 여부
cal = G.CAL
post = cal[(cal >= G.LAUNCH) & (cal <= G.IS_END)]
out['calendar'] = dict(IS_days=len(post), first=str(post[0].date()), has_0603=bool(pd.Timestamp('2026-06-03') in cal),
                       IS_dates=[str(d.date()) for d in post])

# 2. 회귀 IS 창 누수: t=7/31 행의 y=ln(C_8/3 / C_7/31) 가 IS 회귀에 들어가는지
lr = np.log(G.C[G.TREATED]).diff().shift(-1)
out['IS_reg_last_row_uses_OOS_price'] = {c: float(lr[c].loc[G.IS_END]) for c in G.TREATED}
# t+1 <= 7/31 로 자른 회귀
prev = cal[cal < pd.Timestamp(G.IS_END)][-1]
out['IS_reg_t1_le_0731'] = G.reg(G.TREATED, 'QQQ', G.LAUNCH, str(prev.date()))

# 3. 가격제한폭(±30%) 근접일 — 청산/진입 체결 가능성
rc = G.C[G.TREATED].pct_change().loc[G.LAUNCH:]
W = G.weights(G.TREATED)
lim = {}
for c in G.TREATED:
    for d in rc.index[rc[c].abs() >= 0.25]:
        i = cal.get_loc(d)
        lim[f'{c}_{d.date()}'] = dict(ret=float(rc[c].loc[d]), w_prev=float(W[c].iloc[i - 1]), w_today=float(W[c].iloc[i]),
                                      note='오늘 종가에 하한가 매도/상한가 매수 필요 여부 확인')
out['limit_days'] = lim

# 4. 소수 이벤트: 상위 N일/거래 제거 (전체 기간, IS)
def ex_top(rr, n):
    lp = np.log1p(rr)
    return float(np.expm1(lp.sum() - lp.nlargest(n).sum()))
rf = r.loc[G.LAUNCH:G.SAMPLE_END]
out['top_days'] = {str(k.date()): float(v) for k, v in rf.nlargest(10).items()}
out['ex_topN_days_full_ROI'] = {n: ex_top(rf, n) for n in [1, 3, 5, 10]}
out['ex_topN_days_IS_ROI'] = {n: ex_top(r.loc[G.LAUNCH:G.IS_END], n) for n in [1, 3, 5]}
on = (pos.loc[rf.index] > 0).astype(int); grp = (on.diff().fillna(on.iloc[0]) == 1).cumsum()
trades = pd.Series({grp[on == 1][x.index].iloc[0]: (1 + x).prod() - 1 for _, x in rf[on == 1].groupby(grp[on == 1])})
tdates = {int(k): str(rf[on == 1][grp[on == 1] == k].index[0].date()) for k in trades.index}
ts = trades.sort_values(ascending=False)
out['top5_trades'] = [{'start': tdates[int(k)], 'ret': float(v)} for k, v in ts.head(5).items()]
out['ex_top5_trades_full_ROI'] = float(np.prod(1 + ts.iloc[5:]) - 1)
out['n_trades'] = int(len(ts))
out['ex_0731_full_ROI'] = float(np.expm1(np.log1p(rf).sum() - np.log1p(rf.loc['2026-07-31'])))

# 5. MDD 기간·회복
eq = (1 + rf).cumprod(); dd = eq / eq.cummax() - 1
trough = dd.idxmin(); peak = eq.loc[:trough].idxmax()
rec = eq.loc[trough:][eq.loc[trough:] >= eq.loc[peak]]
out['MDD'] = dict(mdd=float(dd.min()), peak=str(peak.date()), trough=str(trough.date()),
                  recovered=str(rec.index[0].date()) if len(rec) else None,
                  days_peak_to_trough=int(len(eq.loc[peak:trough]) - 1), peak_equity=float(eq.loc[peak]), end_equity=float(eq.iloc[-1]))

# 6. 상관: B&H, QQQ, 코스닥150
bh = bench.reindex(rf.index)
out['corr_BH'] = {k: float(rf.loc[a:b].corr(bh.loc[a:b])) for k, (a, b) in
                  {'full': (G.LAUNCH, G.SAMPLE_END), 'IS': (G.LAUNCH, G.IS_END), 'OOS': (G.OOS, G.SAMPLE_END)}.items()}
q = G.US['QQQ']['adj']; qd = q.pct_change()
qs = G.S['QQQ'].reindex(rf.index)   # 한국 t 일에 반영되는 직전 미국 수익률(로그)
out['corr_QQQ_prevnight_return'] = float(rf.corr(qs))
# VOO/QQQ 50/200 골든크로스 보유 전략 근사(미국 일수익, 신호 t-1 결정) -> 한국 달력으로 매핑
gc = {}
for t in ['QQQ']:
    p = G.US[t]['adj']; sig = (p.rolling(50).mean() > p.rolling(200).mean()).astype(float).shift(1)
    gr = (sig * p.pct_change()).fillna(0)
    lg = np.log1p(gr).cumsum()
    m = pd.Series([lg.loc[:d - pd.Timedelta(days=1)].iloc[-1] for d in rf.index], index=rf.index).diff()
    gc[t] = dict(corr_same_kr_day=float(rf.corr(m)), corr_strategy_vs_next_kr_day=float(rf.corr(m.shift(-1))),
                 gc_invested_share=float(sig.reindex(q.loc[G.LAUNCH:].index).mean()))
out['corr_golden_cross_proxy'] = gc
try:
    k = G.fund.kr('229200')
    kc = k['close'].reindex(rf.index).pct_change(); ki = (k['close'] / k['open'] - 1).reindex(rf.index)
    out['corr_KOSDAQ150'] = dict(close_to_close=float(rf.corr(kc)), intraday_open_close=float(rf.corr(ki)),
                                 abs_ret_corr=float(rf.abs().corr(kc.abs())))
except Exception as e:
    out['corr_KOSDAQ150'] = f'fail: {e}'

# 7. 국면: 상장 전 placebo 연도별 + 2024-08-05 엔캐리 폭락 등
rp, _, _ = G.strat(start=G.SAMPLE_START, end='2026-05-26')
out['placebo_net_by_year'] = {str(y): float((1 + x).prod() - 1) for y, x in rp.groupby(rp.index.year)}
out['regime_2008_2020_2022'] = 'not testable: 데이터 2024-01 시작, 현상 자체가 2026-05-27 이후'

# 8. 신호 하루 지연 (OOS·IS 비용 전)
W0 = G.weights(G.TREATED); W1 = W0.shift(1).fillna(0)
for nm, (a, b) in {'IS': (G.LAUNCH, G.IS_END), 'OOS': (G.OOS, G.SAMPLE_END)}.items():
    out[f'lag1_gross_{nm}'] = float((1 + G.sim_cc(W1, a, b, 0, False)[0]).prod() - 1)
    out[f'lag0_gross_{nm}'] = float((1 + G.sim_cc(W0, a, b, 0, False)[0]).prod() - 1)

# 9. 배당 미반영 확인(삼성 분기배당 ex-date 근처 수익률)
out['kr_adj_equals_close'] = bool((G.px['005930']['adj'] == G.px['005930']['close']).all())

# 10. 숏 레그 분해
for side, f in {'long_only': lambda d: d.clip(lower=0), 'short_only': lambda d: d.clip(upper=0)}.items():
    Ws = f(W0)
    out[f'{side}_net'] = {nm: float((1 + G.sim_cc(Ws, a, b)[0]).prod() - 1) for nm, (a, b) in
                          {'IS': (G.LAUNCH, G.IS_END), 'OOS': (G.OOS, G.SAMPLE_END), 'full': (G.LAUNCH, G.SAMPLE_END)}.items()}

# 11. 차입비용 민감도: 숏 노출에 연 5%, 20%
for fee in [0.05, 0.20]:
    sh = (-W0.clip(upper=0)).shift(1).fillna(0).sum(1).reindex(rf.index)
    adj = rf - sh * fee / 252
    out[f'borrow_{int(fee*100)}pct_full_ROI'] = float((1 + adj).prod() - 1)
    out[f'borrow_{int(fee*100)}pct_OOS_ROI'] = float((1 + adj.loc[G.OOS:]).prod() - 1)

json.dump(out, open(CK / 'cro_check.json', 'w'), ensure_ascii=False, indent=1, default=str)
print(json.dumps(out, ensure_ascii=False, indent=1, default=str))
