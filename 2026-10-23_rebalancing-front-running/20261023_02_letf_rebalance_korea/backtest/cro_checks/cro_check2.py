"""CRO 2차 독립 점검(블로그 사실검증 관점). backtest.py 정의부만 exec, US는 캐시 사용(refresh=False). 결과는 cro_checks/ 에만."""
import json
from pathlib import Path
import numpy as np, pandas as pd
RUN = Path('~/agent-fund/runs/20261023_02_letf_rebalance_korea'); CK = RUN/'backtest'/'cro_checks'
src = (RUN/'backtest'/'backtest.py').read_text().split('# ================================================================== main')[0]
src = src.replace("OUT = RUN / 'backtest'; OUT.mkdir(exist_ok=True)", f"OUT = Path('{CK}')").replace('refresh=True', 'refresh=False')
g = {'__name__': 'cro2'}; exec(compile(src, 'bt_head', 'exec'), g)
C, O, S, CAL, strat, reg, weights, sim_cc, px, US = (g[k] for k in ['C','O','S','CAL','strat','reg','weights','sim_cc','px','US'])
LAUNCH, IS_END, OOS, END = g['LAUNCH'], g['IS_END'], g['OOS'], g['SAMPLE_END']
T = g['TREATED']; out = {}
r, pos, to = strat()
out['reproduce_ROI'] = {k: float((1+r.loc[a:b]).prod()-1) for k,(a,b) in {'full':(LAUNCH,END),'IS':(LAUNCH,IS_END),'OOS':(OOS,END)}.items()}

# 1) 7/31 전후 원자료와 신호
win = slice('2026-07-27','2026-08-05')
W = weights(T)
out['raw_0731'] = {str(d.date()): dict(s_QQQ=float(S['QQQ'].loc[d]), w=float(W['005930'].loc[d]),
    **{f'{c}_{k}': float(px[c].loc[d, k]) for c in T for k in ['open','close','volume']},
    **{f'{c}_ret': float(C[c].pct_change().loc[d]) for c in T}) for d in CAL[(CAL>='2026-07-27')&(CAL<='2026-08-05')]}
q = US['QQQ']['adj']; out['QQQ_ret_0724_0803'] = {str(k.date()): float(v) for k,v in q.pct_change().loc['2026-07-24':'2026-08-03'].items()}

# 2) 시점 점검: 임의 5일에 대해 s_t 수작업 재계산
chk = {}
for d in [pd.Timestamp('2026-06-01'), pd.Timestamp('2026-07-31'), pd.Timestamp('2026-08-03'), pd.Timestamp('2026-10-06'), pd.Timestamp('2026-10-10') if pd.Timestamp('2026-10-10') in CAL else CAL[CAL>='2026-10-10'][0]]:
    i = CAL.get_loc(d); dp = CAL[i-1]
    a = q.loc[:d-pd.Timedelta(days=1)]; b = q.loc[:dp-pd.Timedelta(days=1)]
    chk[str(d.date())] = dict(prev_kr=str(dp.date()), us_end=str(a.index[-1].date()), us_start=str(b.index[-1].date()),
                              s_manual=float(np.log(a.iloc[-1]/b.iloc[-1])), s_code=float(S['QQQ'].loc[d]))
out['shock_timing_spot'] = chk

# 3) 회귀: 7/30·7/31 행 제거, 상장 첫 5일 제거(원문 41일 근사)
def reg_ex(dates_ex, a=LAUNCH, b=IS_END):
    s = S['QQQ']; lr = np.log(C[T]).diff().shift(-1); rows=[]
    for c in T:
        df = pd.DataFrame({'y': lr[c], 's': s, 's1': s.shift(-1)}).loc[a:b].dropna(); rows.append(df)
    df = pd.concat(rows); df = df[~df.index.isin(pd.to_datetime(dates_ex))]
    return g['ols_cluster'](df.y.values, df[['s','s1']].values, df.index.values)
out['IS_reg_ex_0730_0731'] = reg_ex(['2026-07-30','2026-07-31'])
first5 = CAL[(CAL>=LAUNCH)][:5]
out['IS_reg_ex_first5'] = reg_ex(list(first5))
out['IS_reg_ex_first5_and_last'] = reg_ex(list(first5)+['2026-07-31'])
# 회귀 OLS 단순 vs 군집: 날짜 군집 G=45, 처리 단위 2개 → 두 종목 상관
rc = C[T].pct_change().loc[LAUNCH:END]
out['corr_samsung_hynix_daily'] = float(rc.corr().iloc[0,1])

# 4) 무작위화 추론: IS 기간 신호 방향을 무작위 부호로 1만회 (같은 노출일, 비용 전)
rng = np.random.default_rng(7)
d0 = (W['005930']*2).loc[LAUNCH:IS_END]
retp = C[T].pct_change().shift(-1).loc[LAUNCH:IS_END].mean(1)   # t 진입 → t+1 종가, 50:50
act = float((d0*retp).sum())
nz = d0 != 0
sims = np.array([(np.where(nz, rng.choice([-1,1], len(d0)), 0)*retp.values).sum() for _ in range(10000)])
out['IS_signflip_perm'] = dict(actual_sum_simple=act, p_one_sided=float((sims>=act).mean()))
# OOS 동일
d1 = (W['005930']*2).loc[OOS:END]; retq = C[T].pct_change().shift(-1).loc[OOS:END].mean(1).fillna(0)
act1 = float((d1*retq).sum()); nz1 = d1!=0
s1 = np.array([(np.where(nz1, rng.choice([-1,1], len(d1)), 0)*retq.values).sum() for _ in range(10000)])
out['OOS_signflip_perm'] = dict(actual_sum_simple=act1, p_lower=float((s1<=act1).mean()))

# 5) 상위 5 거래일/7월 제거 (IS 로그손익 비중)
pnl = np.log1p(r.loc[LAUNCH:IS_END])
out['IS_logpnl'] = float(pnl.sum()); out['IS_0731_log'] = float(pnl.loc['2026-07-31'])
out['IS_top5_share'] = float(pnl.nlargest(5).sum()/pnl.sum())
# 전체 기간 '상위 5일 제거' ROI
lp = np.log1p(r.loc[LAUNCH:END]); out['full_ex_top5_days_ROI'] = float(np.expm1(lp.sum()-lp.nlargest(5).sum()))

# 6) 7/31 상한가 근접일: 7/31 종가에 숏 진입(매도)은 가능하나, 30% 상한가 도달 시 체결 경쟁 — 7/31 종가가 상한가인지
for c in T:
    prev = C[c].shift(1).loc['2026-07-31']; lim = prev*1.30
    out[f'{c}_0731_close_vs_limit'] = dict(close=float(C[c].loc['2026-07-31']), prev=float(prev), limit_up_approx=float(lim), ratio=float(C[c].loc['2026-07-31']/lim))

# 7) 합성 LETF 수치 재계산 (블로그 '10,000 KRW→1,873원')
for c in T:
    x = C[c].pct_change().loc[LAUNCH:END].iloc[1:]
    out[f'{c}_synth_10000_to_1022'] = float(10000*(1+2*x-0.0029/252).prod())
    out[f'{c}_synth_10000_to_0731'] = float(10000*(1+2*x.loc[:IS_END]-0.0029/252).prod())
# 상장일 진입 기준 차이: 5/26 종가 기준(상장일 첫 리밸런싱 포함) 민감도
for c in T:
    x = C[c].pct_change().loc['2026-05-27':IS_END]
    out[f'{c}_synth_from_0526close_to_0731'] = float(10000*(1+2*x).prod())

# 8) 블로그 주장 "모든 변형에서 표본외 ROI 음수" 확인
rb = json.load(open(RUN/'backtest'/'robustness.json'))['variants']
out['variants_OOS_ROI_nonneg'] = {k: v['OOS']['ROI'] for k,v in rb.items() if v.get('OOS') and v['OOS']['ROI'] >= 0}
out['variants_secondhalf_nonneg'] = {k: v['second_half']['Sharpe'] for k,v in rb.items() if v.get('second_half') and (v['second_half'].get('Sharpe') or -1) >= 0}

# 9) MDD 기간·회복
rf = r.loc[LAUNCH:END]; eq = (1+rf).cumprod(); dd = eq/eq.cummax()-1; tr = dd.idxmin(); pk = eq.loc[:tr].idxmax()
out['MDD'] = dict(mdd=float(dd.min()), peak=str(pk.date()), trough=str(tr.date()), recovered=bool((eq.loc[tr:]>=eq.loc[pk]).any()),
                  underwater_days_to_end=int(len(eq.loc[pk:])-1))
# 10) B&H·QQQ 상관
bh = g['bh'](T).reindex(rf.index)
out['corr_BH_full'] = float(rf.corr(bh)); out['corr_BH_OOS'] = float(rf.loc[OOS:].corr(bh.loc[OOS:]))
# 11) 배당: 삼성 분기배당(약 0.1~0.2%) 미반영 — 롱/숏 노출일과 ex-date 근처
out['dividend_note'] = 'kr adj==close: 배당 미조정. 삼성 분기배당 ~361원/주 ≈ 0.1%(가격 300,000 KRW대), 하이닉스 ~375원 ≈ 0.02%. 영향 미미.'
json.dump(out, open(CK/'cro_check2.json','w'), ensure_ascii=False, indent=1, default=str)
print(json.dumps(out, ensure_ascii=False, indent=1, default=str))
