"""CRO 독립 점검. 결과는 이 폴더(cro_checks/)에만 쓴다."""
import sys, json, importlib.util, warnings
warnings.filterwarnings('ignore')
import numpy as np, pandas as pd
from pathlib import Path

OUT = Path('~/agent-fund/runs/20261023_01_rebalancing_frontrun/backtest/cro_checks')
spec = importlib.util.spec_from_file_location('bt', '~/agent-fund/runs/20261023_01_rebalancing_frontrun/backtest/backtest.py')
bt = importlib.util.module_from_spec(spec); spec.loader.exec_module(bt)   # main() 미실행
fund = bt.fund
res = {}

# ---- 1. 재현
p = dict(bt.BASE); w, wT, wC = bt.weights(p); W = bt.W_s1(w, 'IEF')
r1, _, to1 = bt.run_engine(W, 1.0); r0, _, _ = bt.run_engine(W, 0.0)
rcc_g, _ = bt.run_cc(w, 'IEF', False); rcc_n, _ = bt.run_cc(w, 'IEF', True)
rspy, _, _ = bt.run_engine(pd.DataFrame({'SPY': 1.0}, index=W.index))
cal = bt.SIG['IEF']['CAL']; win = bt.SIG['IEF']['from_end'] < 5; to_ief = win & (cal > 0)
W3 = pd.DataFrame({'SPY': (~to_ief).astype(float), 'IEF': to_ief.astype(float)})
rS3, _, _ = bt.run_engine(W3)
res['reproduce'] = {k: bt.brief(v) for k, v in dict(S1=r1, S1_cost0=r0, cc_gross=rcc_g, cc_net=rcc_n, SPY=rspy, S3=rS3).items()}
res['reproduce']['S1_OOS'] = bt.brief(bt.slice_(r1, bt.OOS, None))

# ---- 2. 미래정보: 절단 테스트 (데이터를 T까지만 주고 신호 재계산 → T까지 w 동일해야 함)
trunc = {}
PX_full = {k: v.copy() for k, v in bt.PX.items()}
for T in ['2008-10-15', '2020-03-20', '2023-06-28']:
    bt.PX = {k: v[v.index <= T] for k, v in PX_full.items()}
    sigT = bt.base_signals('IEF')
    wTt, _, _ = bt.weights(p, sigT)
    common = wTt.index.intersection(w.index)
    # 마지막 달은 달력 보충이 있으므로 전체 비교
    trunc[T] = float((wTt.reindex(common) - w.reindex(common)).abs().max())
bt.PX = PX_full
res['lookahead_truncation_maxdiff'] = trunc
# 추가 1일 지연: 성과가 급변하면 타이밍 민감
rlag, _, _ = bt.run_engine(W.shift(1).fillna(0), 1.0); rlag0, _, _ = bt.run_engine(W.shift(1).fillna(0), 0.0)
res['extra_1day_lag'] = {'net': bt.brief(rlag), 'cost0': bt.brief(rlag0)}

# ---- 3. 비용 민감도 / 손익분기 / 차입비용
cm = {}
for c in [0.0, 0.25, 0.5, 0.75, 1.0]:
    rc, _, _ = bt.run_engine(W, c); cm[str(c)] = bt.brief(rc)['Sharpe']
res['cost_mult_sharpe'] = cm
gross_ex = (r0 - fund.cash_daily(r0.index)).mean() * 252
cost_ann = (r0 - r1).mean() * 252
res['breakeven_cost_mult'] = float(gross_ex / cost_ann)
borrow = (w.shift(1).abs().reindex(r1.index).fillna(0)) * 0.003 / 252   # 숏 다리 차입 연 0.30% 가정
res['S1_with_borrow_30bp'] = bt.brief(r1 - borrow)

# ---- 4. 소수 이벤트 의존: 상위 5일/5개월/5년 제거
def drop_top(r, freq, k=5):
    if freq == 'D':
        top = r.nlargest(k).index; return r.drop(top), [str(d.date()) for d in top]
    g = (1 + r).groupby(r.index.to_period(freq)).prod() - 1
    top = g.nlargest(k).index
    return r[~r.index.to_period(freq).isin(top)], [str(t) for t in top]
ev = {}
for nm, rr in dict(S1=r1, cc_gross=rcc_g, S1_cost0=r0).items():
    ev[nm] = {}
    for f in ['D', 'M', 'Y']:
        rd, tops = drop_top(rr, f); ev[nm][f] = dict(removed=tops, after=bt.brief(rd))
res['top5_removal'] = ev

# ---- 5. 국면
reg = {'2008': ('2008-01-01', '2008-12-31'), 'GFC_2008-09~2009-03': ('2008-09-01', '2009-03-31'),
       '2020': ('2020-01-01', '2020-12-31'), '2020-03': ('2020-03-01', '2020-03-31'),
       '2022': ('2022-01-01', '2022-12-31')}
rg = {}
for k, (a, b) in reg.items():
    rg[k] = {nm: float((1 + bt.slice_(rr, a, b)).prod() - 1) for nm, rr in
             dict(S1=r1, S1_cost0=r0, cc_gross=rcc_g, S3=rS3, SPY=rspy).items()}
res['regimes_total_return'] = rg

# ---- 6. 낙폭 기간·회복
def dd_info(r):
    eq = (1 + r).cumprod(); peak = eq.cummax(); dd = eq / peak - 1
    trough = dd.idxmin(); pk = eq[:trough].idxmax()
    rec = eq[trough:][eq[trough:] >= peak[trough]]
    return dict(MDD=float(dd.min()), peak=str(pk.date()), trough=str(trough.date()),
                recovery=str(rec.index[0].date()) if len(rec) else 'not recovered',
                peak_to_trough_days=int((trough - pk).days),
                underwater_years=round(((rec.index[0] if len(rec) else r.index[-1]) - pk).days / 365.25, 2),
                pct_time_underwater=float((dd < -1e-9).mean()))
res['drawdown'] = {nm: dd_info(rr) for nm, rr in dict(S1=r1, cc_gross=rcc_g, S3=rS3, SPY=rspy).items()}

# ---- 7. 상관: SPY B&H, VOO/QQQ 50/200 골든크로스, KOSDAQ150
def gc(t):
    a = fund.us(t)['adj']; s50 = a.rolling(50).mean(); s200 = a.rolling(200).mean()
    wgc = (s50 > s200).astype(float).where(s200.notna(), 0)
    wgc = wgc.reindex(W.index).fillna(0)
    r, _, _ = bt.run_engine.__globals__['fund'].run({t: fund.us(t)}, pd.DataFrame({t: wgc}), start=bt.START)
    return r
# VOO는 2010-09 상장 → SPY로 대리(동일 지수)
rgc_spy = gc('SPY'); rgc_qqq = gc('QQQ')
rgc = 0.5 * rgc_spy + 0.5 * rgc_qqq
series = dict(S1=r1, S1_cost0=r0, cc_gross=rcc_g, S3=rS3, SPY=rspy, GC_VOOproxy_QQQ=rgc)
try:
    k = fund.kr('229200')
    rk = k['adj'].pct_change()
    series['KOSDAQ150_229200_BH'] = rk
except Exception as e:
    res['kosdaq_error'] = repr(e)
D = pd.DataFrame(series)
corr = {}
dD = D.dropna(subset=['S1'])
corr['daily'] = dD.drop(columns=[c for c in dD if c.startswith('KOSDAQ')]).corr().round(3).to_dict()
Mo = (1 + D.fillna(0)).groupby(D.index.to_period('M')).prod() - 1
Mo = Mo[Mo.index >= pd.Period(bt.START[:7], 'M')]
corr['monthly'] = Mo.corr().round(3).to_dict()
# 하락장 상관(SPY 월수익 하위 20%)
q = Mo['SPY'] <= Mo['SPY'].quantile(0.2)
corr['monthly_SPY_bottom20pct_mean_ret'] = Mo[q].mean().round(4).to_dict()
res['correlation'] = corr
res['GC_sharpe'] = bt.brief(rgc)
# 조합 효과: GC 90% + S1 10% vs GC 100%
res['blend_GC90_S1_10'] = bt.brief(0.9 * rgc + 0.1 * r1); res['GC100'] = bt.brief(rgc)
res['blend_GC90_cc10_upperbound'] = bt.brief(0.9 * rgc + 0.1 * rcc_g)

# ---- 8. 연도별 OOS 회귀 계수 안정성: 롤링 3년 Threshold 계수 부호
sig = bt.SIG['IEF']; y = (sig['rs'] - sig['rb']).shift(-1); thr = sig['TH'].mean(1)
DD = pd.DataFrame({'y': y, 'thr': thr}).dropna(); DD = DD[DD.index >= bt.START]
yr = {}
for Y, g in DD.groupby(DD.index.year):
    o = bt.ols_hc1(g['y'].values, g[['thr']].values); yr[int(Y)] = round(o['t'][1], 2)
res['threshold_t_by_year'] = yr

json.dump(res, open(OUT / 'cro_checks.json', 'w'), ensure_ascii=False, indent=1, default=str)
print(json.dumps(res, ensure_ascii=False, indent=1, default=str))
