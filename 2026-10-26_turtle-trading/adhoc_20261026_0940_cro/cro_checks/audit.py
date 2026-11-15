import json
from pathlib import Path
import numpy as np, pandas as pd

QB = Path('~/agent-fund/runs/adhoc_20261026_0915_quant/backtest')
OUT_DIR = Path('~/agent-fund/runs/adhoc_20261026_0940_cro/cro_checks')
OUT_DIR.mkdir(parents=True, exist_ok=True)

fin = json.load(open(QB / 'final.json'))
q1 = json.load(open(QB / 'q1.json'))
q2 = json.load(open(QB / 'q2.json'))
q3b = json.load(open(QB / 'q3b.json'))
extra = json.load(open(QB / 'extra.json'))
val_d10 = json.load(open(QB / 'validation.json'))
val_i30 = json.load(open(QB / 'validation_i30/validation.json'))
m_m5 = json.load(open(QB / 'metrics.json'))
m_d10 = json.load(open(QB / 'eval_d10/metrics.json'))
m_i30 = json.load(open(QB / 'eval_i30/metrics.json'))

ep_df = pd.read_csv(QB / 'episodes.csv')
ep_ex = pd.read_csv(QB / 'episodes_extra.csv')
ro_sum = pd.read_csv(QB / 'rolling5y_summary_all.csv')
ro_all = pd.concat([pd.read_csv(QB / 'rolling5y.csv'), pd.read_csv(QB / 'rolling5y_extra.csv')])

# 1. 연도별 집중도 및 최고 연도 제거 시 누적수익률(ROI) 계산
def yearly_concentration(m_json):
    yr = m_json['yearly']
    s_rets = {k: v['strat'] for k, v in yr.items()}
    b_rets = {k: v['bh'] for k, v in yr.items()}
    best_y = max(s_rets, key=lambda k: s_rets[k])
    worst_y = min(s_rets, key=lambda k: s_rets[k])
    full_prod = float(np.prod([1 + v for v in s_rets.values()]) - 1)
    no_best_prod = float(np.prod([1 + v for k, v in s_rets.items() if k != best_y]) - 1)
    # Top 2 years removal
    top2 = sorted(s_rets, key=lambda k: s_rets[k], reverse=True)[:2]
    no_top2_prod = float(np.prod([1 + v for k, v in s_rets.items() if k not in top2]) - 1)
    # Correlation of yearly returns with B&H
    corr_yr = float(np.corrcoef(list(s_rets.values()), list(b_rets.values()))[0, 1])
    return dict(
        best_year=best_y, best_year_ret=s_rets[best_y],
        worst_year=worst_y, worst_year_ret=s_rets[worst_y],
        top2_years=top2,
        compounded_yearly_roi=full_prod,
        roi_without_best_year=no_best_prod,
        roi_without_top2_years=no_top2_prod,
        yearly_corr_with_bh=corr_yr,
        crisis_years={y: dict(strat=s_rets.get(y), bh=b_rets.get(y)) for y in ('2000', '2008', '2020', '2022', '2024', '2026') if y in s_rets}
    )

# 2. 선택 규칙 동점(tie) 제외 시 실제 승수 재집계
def strict_wins(rows, base_name, sets=('M5_IS', 'M5_OOS', 'D_16_21', 'IDX_97_15')):
    base = next(r for r in rows if r['name'] == base_name)
    out = []
    for r in rows:
        if r['name'] == base_name: continue
        strict_w = sum(1 for s in sets if r.get(s, {}).get('Sharpe', -9) > base.get(s, {}).get('Sharpe', 9) + 1e-6)
        ties = sum(1 for s in sets if abs(r.get(s, {}).get('Sharpe', -9) - base.get(s, {}).get('Sharpe', 9)) <= 1e-6)
        losses = len(sets) - strict_w - ties
        mdd_d10_diff = r.get('D10_full', {}).get('MDD', -1) - base.get('D10_full', {}).get('MDD', 0)
        mdd_i30_diff = r.get('I30_full', {}).get('MDD', -1) - base.get('I30_full', {}).get('MDD', 0)
        out.append(dict(
            name=r['name'], strict_wins=strict_w, ties=ties, losses=losses,
            mdd_d10_diff=float(mdd_d10_diff), mdd_i30_diff=float(mdd_i30_diff),
            strict_pass=(strict_w >= 3 and mdd_d10_diff >= -0.03 and mdd_i30_diff >= -0.03)
        ))
    return out

q1_strict = strict_wins(q1['rows'], '현행 max(1.0ATR,3%)')
q1_dip_strict = strict_wins(q1['dip_rows'], '매집간격 현행 max(0.5ATR,1.5%)')
q2_base_rows = [r for r in q2['rows'] if r['cost_mult'] == 1.0 and r['name'] != '매집 구간 없음(평상 사다리만)']
q2_strict = strict_wins(q2_base_rows, '현행 일괄(구간 목표가, 종료 후 유지)')

# 3. 2008 구간 새출발 상세
ep_2008 = ep_ex[(ep_ex['kind'] == 'i30') & (ep_ex['start'] == '2008-01-16')][
    ['variant', 'ret_regime_end', 'ret_1y', 'ret_2y', 'mdd_1y', 'avg_invested_1y', 'regime_buys', 'regime_sells']
].to_dict('records')

# 4. 롤링 5년 창에서 시한종료 전환 vs 현행 차이
ro_base = ro_all[ro_all['variant'] == '현행 max(1.0ATR,3%)'].set_index('start')
ro_conv = ro_all[ro_all['variant'] == '일괄 + 시한종료만 평상 전환'].set_index('start')
diff_years = []
for y in ro_base.index:
    if y in ro_conv.index:
        ds = float(ro_conv.loc[y, 'Sharpe'] - ro_base.loc[y, 'Sharpe'])
        dc = float(ro_conv.loc[y, 'CAGR'] - ro_base.loc[y, 'CAGR'])
        if abs(ds) > 1e-6:
            diff_years.append(dict(start_year=int(y), base_sharpe=float(ro_base.loc[y, 'Sharpe']),
                                   conv_sharpe=float(ro_conv.loc[y, 'Sharpe']),
                                   base_cagr=float(ro_base.loc[y, 'CAGR']),
                                   conv_cagr=float(ro_conv.loc[y, 'CAGR'])))

# 5. 대표 실거래 습관과 가장 가까운 실험 결과 추출
# (a) 평상시 매수 간격 고정 1.5%, 2.0% 및 ATR 0.5x
habit_gap = [
    dict(name=r['name'],
         M5_IS_Sharpe=r['M5_IS']['Sharpe'], M5_OOS_Sharpe=r['M5_OOS']['Sharpe'],
         M5_OOS_CAGR=r['M5_OOS']['CAGR'], M5_OOS_MDD=r['M5_OOS']['MDD'],
         M5_full_MDD=r['M5_full']['MDD'], D10_full_MDD=r['D10_full']['MDD'],
         I30_full_MDD=r['I30_full']['MDD'])
    for r in q1['rows'] if r['name'] in ('현행 max(1.0ATR,3%)', '고정 1.5%', '고정 2.0%', 'ATR 0.5×')
]
# (b) 고ATR 국면 익절 0.5%, 1.0%, 1.5%(~2.0%), ATR 0.2x, 0.4x
habit_hiatr = [
    dict(name=r['name'],
         M5_IS_Sharpe=r['M5_IS']['Sharpe'], M5_OOS_Sharpe=r['M5_OOS']['Sharpe'],
         D_16_21_Sharpe=r['D_16_21']['Sharpe'], IDX_97_15_Sharpe=r['IDX_97_15']['Sharpe'],
         M5_full_CAGR=r['M5_full']['CAGR'], M5_full_MDD=r['M5_full']['MDD'])
    for r in q3b['rows'] if r['name'] == '현행' or r['name'].startswith('고ATR ')
]

audit_out = dict(
    yearly_m5=yearly_concentration(m_m5),
    yearly_d10=yearly_concentration(m_d10),
    yearly_i30=yearly_concentration(m_i30),
    q1_strict_wins=q1_strict,
    q1_dip_strict_wins=q1_dip_strict,
    q2_strict_wins=q2_strict,
    episode_2008_detail=ep_2008,
    rolling_convert_timeout_diff_years=diff_years,
    habit_gap_comparison=habit_gap,
    habit_hiatr_comparison=habit_hiatr
)

with open(OUT_DIR / 'cro_audit.json', 'w') as f:
    json.dump(audit_out, f, ensure_ascii=False, indent=2)

print("Saved cro_audit.json successfully.")
