"""PREREG_improve.md 의 8개 설정 × 4기간 실행. 비용 = 변형 B(수수료+1틱+매도세 0.2%)."""
import json, sys, time
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent))
import bt  # noqa: E402

CFGS = {
    'B0': {}, 'S1': {'atr_max': 0.045}, 'S1b': {'stop_atr': True}, 'S2': {'dist_max': 0.05},
    'S3': {'no_gap': True}, 'S4': {'vol_breakout': True},
    'C1': {'atr_max': 0.045, 'dist_max': 0.05, 'no_gap': True},
    'C2': {'stop_atr': True, 'dist_max': 0.05, 'no_gap': True},
}
OOS = pd.Timestamp('2021-10-28')

t0 = time.time()
kospi = bt.fetch_benchmark('KOSPI'); kosdaq = bt.fetch_benchmark('KOSDAQ')
kospi_r, kosdaq_r = kospi['close'].pct_change().fillna(0), kosdaq['close'].pct_change().fillna(0)
u, idx, codes, O, H, L, C, V, traded, nbar, C_ff, H_ff, L_ff, V_zero, amt = bt.load_universe_and_prices()
ind = bt.compute_indicators(C_ff, H_ff, L_ff, amt, traded, nbar)
vavg50 = V_zero.where(nbar >= 1).rolling(50, min_periods=50).mean()
ext = dict(atr14=ind['atr14'].to_numpy(float), V=V.to_numpy(float), vavg50=vavg50.to_numpy(float))
A = dict(O_arr=O.to_numpy(float), H_arr=H.to_numpy(float), L_arr=L.to_numpy(float), C_ff_arr=C_ff.to_numpy(float),
         traded_arr=traded.to_numpy(bool), passed_arr=ind['passed'].to_numpy(bool), ref_arr=ind['ref'].to_numpy(float),
         rs0_arr=ind['RS0'].to_numpy(float), sma20_arr=ind['sma20'].to_numpy(float), amt_ma20_arr=ind['amt_ma20'].to_numpy(float))
print(f'loaded {time.time() - t0:.0f}s', flush=True)

rows = []
for cid, cfg in CFGS.items():
    for p, start in bt.PERIODS.items():
        row, tr, daily, ev = bt.run_simulation(p, start, 'B', u, idx, codes, **A, kospi_r=kospi_r, kosdaq_r=kosdaq_r,
                                               cfg={**cfg, 'id': cid}, ext=ext)
        row['cfg'] = cid
        if p == '30y':
            row['IS_CAGR'] = ev['IS'].get('CAGR'); row['IS_MDD'] = ev['IS'].get('MDD')
            row['OOS_CAGR'] = ev['OOS'].get('CAGR'); row['OOS_MDD'] = ev['OOS'].get('MDD')
            row['IS_expR'] = tr[pd.to_datetime(tr.entry_date) < OOS].R.mean()
            row['OOS_expR'] = tr[pd.to_datetime(tr.entry_date) >= OOS].R.mean()
        rows.append(row)
        print(f"{cid:4s} {p:4s} CAGR {row['CAGR']:+.1%} MDD {row['MDD']:.1%} n {row['n_trades']} expR {row['expectancy_R']:+.3f}", flush=True)
s = pd.DataFrame(rows)
s.to_csv(bt.OUT_DIR / 'improve' / 'summary.csv', index=False, encoding='utf-8-sig')
print(f'done {time.time() - t0:.0f}s')
