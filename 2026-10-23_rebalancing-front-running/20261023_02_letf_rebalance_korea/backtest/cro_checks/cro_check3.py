"""CRO 3차: (a) 데이터 시점(refresh) 민감도, (b) 전략 손익 중 '다음날 미국 충격(진입 시점엔 미지)'이 설명하는 몫."""
import json, sys
from pathlib import Path
import numpy as np, pandas as pd
RUN = Path('~/agent-fund/runs/20261023_02_letf_rebalance_korea'); CK = RUN/'backtest'/'cro_checks'
src = (RUN/'backtest'/'backtest.py').read_text().split('# ================================================================== main')[0]
src = src.replace("OUT = RUN / 'backtest'; OUT.mkdir(exist_ok=True)", f"OUT = Path('{CK}')").replace('refresh=True', 'refresh=False')
g = {'__name__': 'cro3'}; exec(compile(src, 'bt_head', 'exec'), g)
C, S, CAL, weights, US, px = (g[k] for k in ['C','S','CAL','weights','US','px'])
LAUNCH, IS_END, OOS, END = g['LAUNCH'], g['IS_END'], g['OOS'], g['SAMPLE_END']; T = g['TREATED']
out = {}
out['data_last'] = {t: [str(US[t].index[-1].date()), float(US[t]['adj'].iloc[-1])] for t in US}
out['kr_last'] = {c: [str(px[c].index[-1].date()), float(px[c]['close'].iloc[-1])] for c in T}
out['QQQ_s_last5'] = {str(k.date()): float(v) for k, v in S['QQQ'].iloc[-5:].items()}
# (b) 분해: 50:50 포트 수익 y_{t+1} = a + c * s_{t+1} + e; 전략 손익 = Σ d_t*y_{t+1}
d = (weights(T)['005930']*2)
y = np.log(C[T]).diff().shift(-1).mean(1)
s1 = S['QQQ'].shift(-1)
for nm, (a, b) in {'IS': (LAUNCH, IS_END), 'OOS': (OOS, END)}.items():
    df = pd.DataFrame({'d': d, 'y': y, 's1': s1}).loc[a:b].dropna()
    X = np.column_stack([np.ones(len(df)), df.s1]); beta = np.linalg.lstsq(X, df.y, rcond=None)[0]
    news = beta[1]*df.s1
    out[f'{nm}_decomp'] = dict(c_next=float(beta[1]), total_gross_log=float((df.d*df.y).sum()),
        from_next_day_US_news=float((df.d*news).sum()), residual=float((df.d*(df.y-news)).sum()),
        corr_d_s1=float(df.d.corr(df.s1)), n_signal_days=int((df.d!=0).sum()))
out['0730_trade'] = dict(d_0730=float(d.loc['2026-07-30']), s_next_0731=float(S['QQQ'].loc['2026-07-31']), y=float(y.loc['2026-07-30']))
json.dump(out, open(CK/'cro_check3.json','w'), ensure_ascii=False, indent=1, default=str)
print(json.dumps(out, ensure_ascii=False, indent=1, default=str))
