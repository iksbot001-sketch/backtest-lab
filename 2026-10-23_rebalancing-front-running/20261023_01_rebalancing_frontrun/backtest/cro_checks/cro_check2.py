"""CRO 추가: 저비용(현실 스프레드) 가정 + 종가(MOC) 체결 민감도. 판정 근거가 엔진 비용가정에 과의존하는지 확인."""
import importlib.util, json, warnings; warnings.filterwarnings('ignore')
import numpy as np, pandas as pd
spec = importlib.util.spec_from_file_location('bt', '~/agent-fund/runs/20261023_01_rebalancing_frontrun/backtest/backtest.py')
bt = importlib.util.module_from_spec(spec); spec.loader.exec_module(bt)
w, _, _ = bt.weights(dict(bt.BASE)); sig = bt.SIG['IEF']; idx = sig['idx']
wp = w.shift(1).fillna(0); dw = (wp - w.shift(2).fillna(0)).abs()
out = {}
for bp in [0, 1, 2, 3, 5, 7]:
    r = wp * (sig['rs'] - sig['rb']).fillna(0) + bt.fund.cash_daily(idx) - 2 * dw * bp / 1e4
    r = r[r.index >= bt.START].copy(); r.iloc[0] = 0
    out[f'MOC_close_{bp}bp_oneway'] = {'full': bt.brief(r), 'IS': bt.brief(bt.slice_(r, bt.START, bt.IS_END)),
                                       'OOS': bt.brief(bt.slice_(r, bt.OOS, None)), 'ex_crisis': bt.brief(bt.ex_crisis(r))}
W = bt.W_s1(w, 'IEF')
for c in [0.15, 0.3]:
    r, _, _ = bt.run_engine(W, c)
    out[f'engine_costmult_{c}'] = {'full': bt.brief(r), 'OOS': bt.brief(bt.slice_(r, bt.OOS, None))}
json.dump(out, open('cro_check2.json', 'w'), indent=1, default=float)
for k, v in out.items(): print(k, {kk: round(vv.get('Sharpe', np.nan), 3) for kk, vv in v.items()})
