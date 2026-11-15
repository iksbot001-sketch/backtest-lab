"""PREREG_erc.md: 기준선 B0·C2(재실행, 기존 summary 와 같아야 함) + E·R·CR 덧씌우기 4개 × 4기간. 비용 = 변형 B."""
import sys, time
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent))
import bt  # noqa: E402

C2 = {'stop_atr': True, 'dist_max': 0.05, 'no_gap': True}
CFGS = {'B0': {}, 'C2': C2,
        'B0E': {'erc': True, 'cr_cap': 0.02}, 'C2E': {**C2, 'erc': True, 'cr_cap': 0.02},
        'B0E1': {'erc': True, 'cr_cap': 0.01}, 'C2E1': {**C2, 'erc': True, 'cr_cap': 0.01}}
if len(sys.argv) > 1 and sys.argv[1] == 'nobrake':   # 사후 탐색(사전 등록 아님): 낙폭 브레이크만 뺀 분해
    CFGS = {k + 'n': {**v, 'no_brake': True} for k, v in CFGS.items() if 'erc' in v}
OOS = pd.Timestamp('2021-10-28')

t0 = time.time()
kospi = bt.fetch_benchmark('KOSPI'); kosdaq = bt.fetch_benchmark('KOSDAQ')
kospi_r, kosdaq_r = kospi['close'].pct_change().fillna(0), kosdaq['close'].pct_change().fillna(0)
u, idx, codes, O, H, L, C, V, traded, nbar, C_ff, H_ff, L_ff, V_zero, amt = bt.load_universe_and_prices()
ind = bt.compute_indicators(C_ff, H_ff, L_ff, amt, traded, nbar)
atrp = ind['atr14'] / C_ff
atrp_eff = np.maximum(atrp, atrp.rolling(252, min_periods=60).median())     # ATR 바닥값 (CRO c)
vavg50 = V_zero.where(nbar >= 1).rolling(50, min_periods=50).mean()
ext = dict(atr14=ind['atr14'].to_numpy(float), V=V.to_numpy(float), vavg50=vavg50.to_numpy(float),
           atrp_eff=atrp_eff.to_numpy(float))
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
        row['avg_E'] = daily['E'].mean(); row['avg_CR'] = daily['cr'].mean(); row['max_CR'] = daily['cr'].max()
        row['brake_days'] = daily['brake'].mean(); row['n_trim'] = int((tr.exit_reason == 'trim').sum())
        if p == '30y':
            for k in ('IS', 'OOS'):
                for m in ('CAGR', 'MDD', 'Sharpe'):
                    row[f'{k}_{m}'] = ev[k].get(m)
        rows.append(row)
        print(f"{cid:5s} {p:4s} CAGR {row['CAGR']:+.1%} MDD {row['MDD']:.1%} Sh {row['Sharpe']:.2f} n {row['n_trades']} "
              f"E {row['avg_E']:.0%} CR {row['avg_CR']:.2%} brake {row['brake_days']:.0%}", flush=True)
pd.DataFrame(rows).to_csv(bt.OUT_DIR / 'improve' / ('summary_erc_nobrake.csv' if len(sys.argv) > 1 else 'summary_erc.csv'), index=False, encoding='utf-8-sig')
print(f'done {time.time() - t0:.0f}s')
