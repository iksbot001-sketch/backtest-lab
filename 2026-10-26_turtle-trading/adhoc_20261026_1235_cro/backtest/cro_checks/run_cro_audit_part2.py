import sys, json
from pathlib import Path
sys.path.insert(0, '~/agent-fund/lib')
sys.path.insert(0, '~/agent-fund/runs/adhoc_20261026_1224_quant/backtest')
import numpy as np
import pandas as pd
import fund, validate
import backtest as bt

OUT = Path('~/agent-fund/runs/adhoc_20261026_1235_cro/backtest/cro_checks')
with open(OUT / 'cro_audit_results.json') as f:
    results = json.load(f)

kospi = bt._clean(bt._nv('KOSPI'))
e200 = bt._clean(bt._nv('069500'))
sp_k200 = pd.Timestamp(bt.SPLICE['K200'])
ratio_k200 = e200['close'].loc[sp_k200] / kospi['close'].loc[sp_k200]
pre_k200 = kospi[(kospi.index >= bt.START['K200']) & (kospi.index < sp_k200)][['open', 'high', 'low', 'close']] * ratio_k200
pre_k200['volume'] = np.nan; pre_k200['proxy'] = 1.0
post_k200 = e200[e200.index >= sp_k200].copy(); post_k200['proxy'] = 0.0
px_k200 = bt._px(pd.concat([pre_k200, post_k200]))

bench_k200 = fund.run({'K200': px_k200}, pd.DataFrame(1.0, index=px_k200.index, columns=['K200']), start=bt.START['K200'])[0]
s_k200_a = bt.turtle(px_k200, bt.BASE, mode='a')

# 1. Compare K200 Turtle (exposure 34% full, 38.3% ETF) vs Simple Constant-Weight B&H (34% / 38.3% B&H + Cash 0%)
r_bh_34_full = 0.34 * bench_k200
r_bh_38_etf = 0.383 * bench_k200.loc['2002-10-14':]
r_turtle_etf = s_k200_a['r'].loc['2002-10-14':]
r_bh_50_etf = 0.50 * bench_k200.loc['2002-10-14':]

results['capital_efficiency_comparison'] = {
    'K200_full_1990_2026': {
        'turtle_a_34pct_expo': {
            'cagr_pct': round(validate.ann_ret(s_k200_a['r']) * 100, 2),
            'mdd_pct': round(validate.mdd(s_k200_a['r']) * 100, 2),
            'sharpe_rf0': round(float(s_k200_a['r'].mean() / s_k200_a['r'].std() * np.sqrt(252)), 3)
        },
        'simple_34pct_BH_66pct_cash0': {
            'cagr_pct': round(validate.ann_ret(r_bh_34_full) * 100, 2),
            'mdd_pct': round(validate.mdd(r_bh_34_full) * 100, 2),
            'sharpe_rf0': round(float(r_bh_34_full.mean() / r_bh_34_full.std() * np.sqrt(252)), 3)
        }
    },
    'K200_etf_2002_2026': {
        'turtle_a_38pct_expo': {
            'cagr_pct': round(validate.ann_ret(r_turtle_etf) * 100, 2),
            'mdd_pct': round(validate.mdd(r_turtle_etf) * 100, 2),
            'sharpe_rf0': round(float(r_turtle_etf.mean() / r_turtle_etf.std() * np.sqrt(252)), 3),
            'sharpe_irx': round(validate.sharpe(r_turtle_etf), 3)
        },
        'simple_38pct_BH_62pct_cash0': {
            'cagr_pct': round(validate.ann_ret(r_bh_38_etf) * 100, 2),
            'mdd_pct': round(validate.mdd(r_bh_38_etf) * 100, 2),
            'sharpe_rf0': round(float(r_bh_38_etf.mean() / r_bh_38_etf.std() * np.sqrt(252)), 3),
            'sharpe_irx': round(validate.sharpe(r_bh_38_etf), 3)
        },
        'simple_50pct_BH_50pct_cash0': {
            'cagr_pct': round(validate.ann_ret(r_bh_50_etf) * 100, 2),
            'mdd_pct': round(validate.mdd(r_bh_50_etf) * 100, 2),
            'sharpe_rf0': round(float(r_bh_50_etf.mean() / r_bh_50_etf.std() * np.sqrt(252)), 3),
            'sharpe_irx': round(validate.sharpe(r_bh_50_etf), 3)
        }
    }
}

# 2. US SPY/QQQ 50/200 Golden Cross correlation
try:
    us_px = {'SPY': fund.us('SPY'), 'QQQ': fund.us('QQQ')}
    w_us = pd.DataFrame(index=us_px['SPY'].index, columns=['SPY', 'QQQ'], dtype=float)
    for t_us in ('SPY', 'QQQ'):
        c_u = us_px[t_us]['adj']
        w_us[t_us] = (c_u.rolling(50).mean() > c_u.rolling(200).mean()).astype(float) * 0.5
    r_us_gc, pos_us_gc, _ = fund.run(us_px, w_us, start='2002-10-14')
    common_idx = s_k200_a['r'].loc['2002-10-14':].index.intersection(r_us_gc.index)
    results['k200_deep_checks']['overlap_with_50_200_gc']['us_spy_qqq_gc_daily_corr'] = round(float(s_k200_a['r'].loc[common_idx].corr(r_us_gc.loc[common_idx])), 3)
    results['k200_deep_checks']['overlap_with_50_200_gc']['us_spy_qqq_gc_monthly_corr'] = round(float(
        (1 + s_k200_a['r'].loc[common_idx]).resample('ME').prod().corr((1 + r_us_gc.loc[common_idx]).resample('ME').prod())
    ), 3)
    results['k200_deep_checks']['overlap_with_50_200_gc']['us_spy_qqq_gc_cagr_2002_2026_pct'] = round(validate.ann_ret(r_us_gc) * 100, 2)
    results['k200_deep_checks']['overlap_with_50_200_gc']['us_spy_qqq_gc_mdd_2002_2026_pct'] = round(validate.mdd(r_us_gc) * 100, 2)
    results['k200_deep_checks']['overlap_with_50_200_gc']['us_spy_qqq_gc_sharpe_2002_2026'] = round(validate.sharpe(r_us_gc), 3)
    if 'us_spy_qqq_gc_error' in results['k200_deep_checks']['overlap_with_50_200_gc']:
        del results['k200_deep_checks']['overlap_with_50_200_gc']['us_spy_qqq_gc_error']
except Exception as e:
    results['k200_deep_checks']['overlap_with_50_200_gc']['us_spy_qqq_gc_error'] = str(e)

# 3. Check total unique trials and recalculated DSR if all 330+210 trials or morning + afternoon trials are counted
# Wait: in adhoc_20261026_1224_quant, n_trials was reported as 201, while trial_registry.jsonl has 330 lines + 210 lines in backtest/trial_registry.jsonl = 540 lines!
lines_1 = (Path('~/agent-fund/runs/adhoc_20261026_1224_quant/trial_registry.jsonl')).read_text().splitlines()
lines_2 = (Path('~/agent-fund/runs/adhoc_20261026_1224_quant/backtest/trial_registry.jsonl')).read_text().splitlines()
unique_params = set()
for l in lines_1 + lines_2:
    d = json.loads(l)
    unique_params.add(json.dumps({'name': d.get('name'), 'params': d.get('params')}, sort_keys=True))
n_total_lines = len(lines_1) + len(lines_2)
n_unique_Run = len(unique_params)

# Recalculate DSR for K200_a with n_trials = 540 (total evaluations in run) and rho = 0.97198
rho_k200a = 0.9719795160898269
n_eff_540 = rho_k200a + (1 - rho_k200a) * n_total_lines
dsr_540, sr0_540 = validate.dsr(s_k200_a['r'], n_total_lines, n_eff=n_eff_540)

results['dsr_recalculation'] = {
    'reported_n_trials': 201,
    'actual_registry_lines_in_run': n_total_lines,
    'unique_name_param_combos_in_run': n_unique_Run,
    'k200_a_n_eff_at_540': round(n_eff_540, 2),
    'k200_a_sr0_annual_at_540': round(sr0_540, 3),
    'k200_a_dsr_at_540': round(dsr_540, 3)
}

json.dump(results, open(OUT / 'cro_audit_results.json', 'w'), ensure_ascii=False, indent=2)
print("Updated cro_audit_results.json")
