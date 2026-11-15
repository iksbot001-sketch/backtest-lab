import sys, json, math, re
from pathlib import Path
sys.path.insert(0, '~/agent-fund/lib')
sys.path.insert(0, '~/agent-fund/runs/adhoc_20261026_1224_quant/backtest')
import numpy as np
import pandas as pd
import fund, validate
import backtest as bt

OUT = Path('~/agent-fund/runs/adhoc_20261026_1235_cro/backtest/cro_checks')
OUT.mkdir(parents=True, exist_ok=True)

with open('~/agent-fund/runs/adhoc_20261026_1224_quant/backtest/results.json') as f:
    q_res = json.load(f)

# Load K200 exactly as backtest.py does (since nv_KOSPI and nv_069500 are in runs/adhoc_20261026_1224_quant/data/)
kospi = bt._clean(bt._nv('KOSPI'))
kpi200 = bt._clean(bt._nv('KPI200'))
e200 = bt._clean(bt._nv('069500'))
kosdaq = bt._clean(bt._nv('KOSDAQ'))
e150_nv = bt._clean(bt._nv('229200'))

sp_k200 = pd.Timestamp(bt.SPLICE['K200'])
ratio_k200 = e200['close'].loc[sp_k200] / kospi['close'].loc[sp_k200]
pre_k200 = kospi[(kospi.index >= bt.START['K200']) & (kospi.index < sp_k200)][['open', 'high', 'low', 'close']] * ratio_k200
pre_k200['volume'] = np.nan; pre_k200['proxy'] = 1.0
post_k200 = e200[e200.index >= sp_k200].copy(); post_k200['proxy'] = 0.0
S_k200 = pd.concat([pre_k200, post_k200]); S_k200.attrs['ratio'] = float(ratio_k200)
px_k200 = bt._px(S_k200)

sp_kq = pd.Timestamp(bt.SPLICE['KQ150'])
ratio_kq = e150_nv['close'].loc[sp_kq] / kosdaq['close'].loc[sp_kq]
pre_kq = kosdaq[(kosdaq.index >= bt.START['KQ150']) & (kosdaq.index < sp_kq)][['open', 'high', 'low', 'close']] * ratio_kq
pre_kq['volume'] = np.nan; pre_kq['proxy'] = 1.0
post_kq = e150_nv[e150_nv.index >= sp_kq].copy(); post_kq['proxy'] = 0.0
S_kq = pd.concat([pre_kq, post_kq]); S_kq.attrs['ratio'] = float(ratio_kq)
px_kq_nv = bt._px(S_kq)

data = {'K200': px_k200, 'KQ150_nv': px_kq_nv}
results = {}

# 1. Inspect registry counts across quant run and central registry
q_run = Path('~/agent-fund/runs/adhoc_20261026_1224_quant')
reg_files = [
    q_run / 'trial_registry.jsonl',
    q_run / 'backtest' / 'trial_registry.jsonl',
    Path('~/agent-fund/data/trial_registry.jsonl'),
    Path('~/agent-fund/runs/adhoc_20261026_0915_quant/trial_registry.jsonl')
]
reg_counts = {}
for rf in reg_files:
    if rf.exists():
        lines = rf.read_text().splitlines()
        reg_counts[str(rf)] = len(lines)
results['registry_line_counts'] = reg_counts

# 2. Trade & Yearly Concentration Analysis from exact q_res['turtle']
conc = {}
for name in ('K200', 'KQ150'):
    conc[name] = {}
    for mode in ('a', 'b'):
        t_list = q_res['turtle'][name][f'{mode}_base']['trades']
        yr_dict = q_res['turtle'][name][f'{mode}_base']['yearly']
        
        rets = np.array([t['exit_eff'] / t['entry_eff'] - 1 for t in t_list])
        order = np.argsort(rets)[::-1]
        sorted_rets = rets[order]
        
        total_compound_trades = float(np.prod(1 + rets) - 1)
        top1_rem = float(np.prod(1 + sorted_rets[1:]) - 1)
        top3_rem = float(np.prod(1 + sorted_rets[3:]) - 1)
        top5_rem = float(np.prod(1 + sorted_rets[5:]) - 1)
        top10_rem = float(np.prod(1 + sorted_rets[10:]) - 1)
        
        top5_trades = []
        for idx_t in order[:5]:
            t_obj = t_list[idx_t]
            top5_trades.append({
                'entry_date': t_obj['entry_date'],
                'exit_date': t_obj['exit_date'],
                'ret_pct': round(float(rets[idx_t]) * 100, 2),
                'reason': t_obj['reason']
            })
            
        worst5_trades = []
        for idx_t in order[-5:][::-1]:
            t_obj = t_list[idx_t]
            worst5_trades.append({
                'entry_date': t_obj['entry_date'],
                'exit_date': t_obj['exit_date'],
                'ret_pct': round(float(rets[idx_t]) * 100, 2),
                'reason': t_obj['reason'],
                'stop_2N_pct': round(float(2 * t_obj['N'] / t_obj['entry_px']) * 100, 2)
            })
            
        # Yearly analysis
        yrs = sorted(int(k) for k in yr_dict.keys())
        yr_s = pd.Series({int(k): v['strat'] for k, v in yr_dict.items()})
        yr_bh = pd.Series({int(k): v['bh'] for k, v in yr_dict.items()})
        yr_sorted = yr_s.sort_values(ascending=False)
        
        n_yrs = 36.8 if name == 'K200' else 29.8
        total_yr_roi = float((1 + yr_s).prod() - 1)
        yr_top1_rem = float((1 + yr_sorted.iloc[1:]).prod() - 1)
        yr_top2_rem = float((1 + yr_sorted.iloc[2:]).prod() - 1)
        yr_top3_rem = float((1 + yr_sorted.iloc[3:]).prod() - 1)
        yr_top5_rem = float((1 + yr_sorted.iloc[5:]).prod() - 1)
        
        # Subperiod 2011-2024 (14 years before 2025-2026 surge)
        yr_11_24 = yr_s.loc[2011:2024]
        bh_11_24 = yr_bh.loc[2011:2024]
        roi_11_24 = float((1 + yr_11_24).prod() - 1)
        cagr_11_24 = float((1 + roi_11_24) ** (1 / 14.0) - 1)
        bh_roi_11_24 = float((1 + bh_11_24).prod() - 1)
        bh_cagr_11_24 = float((1 + bh_roi_11_24) ** (1 / 14.0) - 1)
        
        # Subperiod 2000-2026 for KQ150 (after 1999 dot-com bubble, 26.8 years!)
        yr_00_26 = yr_s.loc[2000:2026]
        bh_00_26 = yr_bh.loc[2000:2026]
        roi_00_26 = float((1 + yr_00_26).prod() - 1)
        cagr_00_26 = float((1 + roi_00_26) ** (1 / 26.8) - 1)
        
        conc[name][mode] = {
            'n_trades': len(rets),
            'total_compound_trades_roi_pct': round(total_compound_trades * 100, 1),
            'top1_trade_removed_roi_pct': round(top1_rem * 100, 1),
            'top3_trades_removed_roi_pct': round(top3_rem * 100, 1),
            'top5_trades_removed_roi_pct': round(top5_rem * 100, 1),
            'top5_trades_removed_cagr_pct': round(((1 + top5_rem) ** (1 / n_yrs) - 1) * 100, 2) if top5_rem > -1 else -100,
            'top10_trades_removed_roi_pct': round(top10_rem * 100, 1),
            'top5_trades': top5_trades,
            'worst5_trades': worst5_trades,
            'top5_years_pct': {int(k): round(float(v)*100, 1) for k, v in yr_sorted.iloc[:5].items()},
            'yr_top1_removed_roi_pct': round(yr_top1_rem * 100, 1),
            'yr_top2_removed_roi_pct': round(yr_top2_rem * 100, 1),
            'yr_top3_removed_roi_pct': round(yr_top3_rem * 100, 1),
            'yr_top5_removed_roi_pct': round(yr_top5_rem * 100, 1),
            'yr_top5_removed_cagr_pct': round(((1 + yr_top5_rem) ** (1 / (n_yrs - 5)) - 1) * 100, 2),
            'period_2011_2024_14yrs': {
                'roi_pct': round(roi_11_24 * 100, 1),
                'cagr_pct': round(cagr_11_24 * 100, 2),
                'bh_roi_pct': round(bh_roi_11_24 * 100, 1),
                'bh_cagr_pct': round(bh_cagr_11_24 * 100, 2),
                'win_years': int((yr_11_24 > 0).sum()),
                'loss_or_flat_years': int((yr_11_24 <= 0).sum()),
                'beat_bh_years': int((yr_11_24 > bh_11_24).sum())
            },
            'period_2000_2026_post_dotcom': {
                'roi_pct': round(roi_00_26 * 100, 1),
                'cagr_pct': round(cagr_00_26 * 100, 2),
                'bh_roi_pct': round(float((1 + bh_00_26).prod() - 1) * 100, 1)
            }
        }
results['concentration_and_outliers'] = conc

# 3. Direct simulation checks on K200 (exact match) and KQ150
bench_k200 = fund.run({'K200': px_k200}, pd.DataFrame(1.0, index=px_k200.index, columns=['K200']), start=bt.START['K200'])[0]
s_k200_a = bt.turtle(px_k200, bt.BASE, mode='a')
s_k200_b = bt.turtle(px_k200, bt.BASE, mode='b')

# Check Mode (b) pos shift distortion in K200
pos_b_unshifted = s_k200_b['held']
pos_b_shifted = s_k200_b['held'].shift(1).fillna(0.0)
tr_b_unshifted = validate.trade_returns(s_k200_b['r'], pos_b_unshifted)
tr_b_shifted = validate.trade_returns(s_k200_b['r'], pos_b_shifted)
closed_b = np.array([t['exit_eff'] / t['entry_eff'] - 1 for t in s_k200_b['trades']])

# Check what happens to K200 WFE if we evaluate up to 2024-12-31 (before 2025-2026 +45%/+65% rally)
r_k200_pre25 = s_k200_a['r'][s_k200_a['r'].index <= '2024-12-31']
T_p = len(r_k200_pre25); b_p = int(T_p / (5 + 7 / 3)); a_p = int(b_p * 7 / 3)
is_anns, oos_parts = [], []
for i in range(5):
    is_ = slice(i * b_p, i * b_p + a_p); oos = slice(i * b_p + a_p, min(i * b_p + a_p + b_p, T_p))
    is_anns.append(validate.ann_ret(r_k200_pre25.iloc[is_]))
    oos_parts.append(r_k200_pre25.iloc[oos])
stitched_pre25 = pd.concat(oos_parts)

# Check K200 pre-ETF realistic cost (0.25% one-way in 1990-2002 proxy period due to 0.3% stock sell tax + spread)
# And check Mode (b) with +3 ticks (15 KRW) intraday stop slippage
def turtle_realistic_friction(px, p=bt.BASE, mode='a', proxy_cost=0.0025, etf_slip_ticks=3.0):
    d = px
    O, H, L, C = (d[k].values.astype(float) for k in ('open', 'high', 'low', 'close'))
    prox = d['proxy'].values
    hs, ls, cs = pd.Series(H), pd.Series(L), pd.Series(C)
    ch_in = hs.rolling(int(p['entry'])).max().shift(1).values
    ch_out = ls.rolling(int(p['exit'])).min().shift(1).values
    tr = pd.concat([hs - ls, (hs - cs.shift()).abs(), (ls - cs.shift()).abs()], axis=1).max(axis=1)
    N = tr.ewm(alpha=1 / p['atr_n'], adjust=False).mean().values
    idx = d.index; n = len(d)
    def rate(t, price):
        return proxy_cost if prox[t] else (bt.FEE + (etf_slip_ticks * bt.TICK) / price)
    cash = 1.0; sh = 0.0; eq = np.empty(n); cur = None; pend = None
    for t in range(n):
        exited = False
        if mode == 'a' and pend is not None:
            px_ = O[t]; rt = rate(t, px_)
            if pend[0] == 'buy':
                sh = cash / (px_ * (1 + rt)); cash = 0.0
                cur = dict(stop=px_ - p['stop_n'] * pend[1], i0=t)
            else:
                cash += sh * px_ * (1 - rt); cur = None; sh = 0.0; exited = True
            pend = None
        if mode == 'b':
            if cur is not None and t > cur['i0']:
                lvl = max(ch_out[t], cur['stop']) if not np.isnan(ch_out[t]) else cur['stop']
                if L[t] <= lvl:
                    px_ = min(lvl, O[t]); rt = rate(t, px_)
                    cash += sh * px_ * (1 - rt); cur = None; sh = 0.0; exited = True
            if cur is None and not exited and t >= 1 and not np.isnan(ch_in[t]) and H[t] > ch_in[t]:
                px_ = max(ch_in[t], O[t]); Ne = N[t - 1]; rt = rate(t, px_)
                sh = cash / (px_ * (1 + rt)); cash = 0.0
                cur = dict(stop=px_ - p['stop_n'] * Ne, i0=t)
                if L[t] <= cur['stop']:
                    sp = cur['stop']; rt = rate(t, sp); cash += sh * sp * (1 - rt); cur = None; sh = 0.0
        eq[t] = cash + sh * C[t]
        if mode == 'a':
            if cur is not None:
                if C[t] < cur['stop']: pend = ('sell', 'stop')
                elif not np.isnan(ch_out[t]) and C[t] < ch_out[t]: pend = ('sell', 'low20')
            elif not np.isnan(ch_in[t]) and C[t] > ch_in[t]:
                pend = ('buy', N[t])
    e = pd.Series(eq, index=idx); r = e.pct_change(); r.iloc[0] = e.iloc[0] - 1
    return r

r_k200_a_real = turtle_realistic_friction(px_k200, mode='a', proxy_cost=0.0025, etf_slip_ticks=1.0)
r_k200_b_real = turtle_realistic_friction(px_k200, mode='b', proxy_cost=0.0025, etf_slip_ticks=3.0)

# Overlap with 50/200 Golden Cross on K200 and US SPY/QQQ
c_k200 = px_k200['close']
gc_k200_pos = (c_k200.rolling(50).mean() > c_k200.rolling(200).mean()).shift(1).fillna(False).astype(float)
r_gc_k200, _, _ = fund.run({'K200': px_k200}, gc_k200_pos.to_frame('K200'), start=bt.START['K200'])

results['k200_deep_checks'] = {
    'pre2025_1990_2024': {
        'cagr_pct': round(validate.ann_ret(r_k200_pre25) * 100, 2),
        'mdd_pct': round(validate.mdd(r_k200_pre25) * 100, 2),
        'sharpe_irx': round(validate.sharpe(r_k200_pre25), 3),
        'psr0': round(validate.psr(r_k200_pre25), 3),
        't_stat': round(float(validate._ex(r_k200_pre25).mean() / validate._ex(r_k200_pre25).std() * np.sqrt(len(r_k200_pre25))), 3),
        'wfe_pct': round(float(validate.ann_ret(stitched_pre25) / np.mean(is_anns)) * 100, 1),
        'stitched_oos_cagr_pct': round(validate.ann_ret(stitched_pre25) * 100, 2),
        'stitched_oos_sharpe': round(validate.sharpe(stitched_pre25), 3)
    },
    'etf_2002_2024_before_25_26_rally': {
        'turtle_a_cagr_pct': round(validate.ann_ret(s_k200_a['r'].loc['2002-10-14':'2024-12-31']) * 100, 2),
        'turtle_a_sharpe_irx': round(validate.sharpe(s_k200_a['r'].loc['2002-10-14':'2024-12-31']), 3),
        'turtle_a_psr0': round(validate.psr(s_k200_a['r'].loc['2002-10-14':'2024-12-31']), 3),
        'bh_cagr_pct': round(validate.ann_ret(bench_k200.loc['2002-10-14':'2024-12-31']) * 100, 2),
        'bh_sharpe_irx': round(validate.sharpe(bench_k200.loc['2002-10-14':'2024-12-31']), 3)
    },
    'realistic_pre_etf_cost_0.25pct': {
        'mode_a_cagr_pct': round(validate.ann_ret(r_k200_a_real) * 100, 2),
        'mode_a_sharpe': round(validate.sharpe(r_k200_a_real), 3),
        'mode_b_3tick_cagr_pct': round(validate.ann_ret(r_k200_b_real) * 100, 2),
        'mode_b_3tick_sharpe': round(validate.sharpe(r_k200_b_real), 3)
    },
    'mode_b_pos_shift_in_validate': {
        'true_closed_trades_win_rate_pct': round(float((closed_b > 0).mean()) * 100, 1),
        'shifted_pos_win_rate_in_validate_pct': round(float((tr_b_shifted > 0).mean()) * 100, 1),
        'true_closed_trades_mean_pct': round(float(closed_b.mean()) * 100, 2),
        'shifted_pos_mean_in_validate_pct': round(float(tr_b_shifted.mean()) * 100, 2)
    },
    'corr_with_bh': {
        'all_days': round(float(s_k200_a['r'].corr(bench_k200)), 3),
        'exposed_days': round(float(s_k200_a['r'][s_k200_a['held'] > 0].corr(bench_k200[s_k200_a['held'] > 0])), 3)
    },
    'overlap_with_50_200_gc': {
        'k200_gc_cagr_pct': round(validate.ann_ret(r_gc_k200) * 100, 2),
        'k200_gc_mdd_pct': round(validate.mdd(r_gc_k200) * 100, 2),
        'k200_gc_sharpe': round(validate.sharpe(r_gc_k200), 3),
        'daily_corr_turtle_vs_k200_gc': round(float(s_k200_a['r'].corr(r_gc_k200)), 3),
        'state_agreement_pct': round(float(((s_k200_a['held'] > 0) == (gc_k200_pos > 0)).mean()) * 100, 1)
    }
}

try:
    us_px = fund.us(['SPY', 'QQQ'], start='2002-01-01')
    w_us = pd.DataFrame(index=us_px['SPY'].index, columns=['SPY', 'QQQ'], dtype=float)
    for t_us in ('SPY', 'QQQ'):
        c_u = us_px[t_us]['adj']
        w_us[t_us] = (c_u.rolling(50).mean() > c_u.rolling(200).mean()).astype(float) * 0.5
    r_us_gc, _, _ = fund.run(us_px, w_us, start='2002-10-14')
    results['k200_deep_checks']['overlap_with_50_200_gc']['us_spy_qqq_gc_daily_corr'] = round(float(s_k200_a['r'].reindex(r_us_gc.index).corr(r_us_gc)), 3)
except Exception as e:
    results['k200_deep_checks']['overlap_with_50_200_gc']['us_spy_qqq_gc_error'] = str(e)

json.dump(results, open(OUT / 'cro_audit_results.json', 'w'), ensure_ascii=False, indent=2)
print("Saved cro_audit_results.json successfully.")
