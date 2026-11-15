"""연구 4: B북(VOO·QQQ 50/200일 골든크로스) 장기 재검증. EODHD 수정주가(배당 포함) SPY(1993~)·QQQ(1999~).
규칙: 종가 기준 50일 이평 > 200일 이평이면 다음 날 종가에 보유, 아니면 현금(수익 0, 단기금리 미반영). 비용 편도 0.015% + $0.01.
지표: CAGR·MDD·Sharpe·연율 변동성·Sortino·거래 횟수, 같은 기간 단순 보유 비교. 세금(해외주식 양도세 22%) 미반영."""
import numpy as np, pandas as pd
from pathlib import Path
PX = Path.home() / 'agent-fund-data/prices/eodhd'
def stats(r):
    c = np.cumprod(1 + r); yrs = len(r) / 252
    dd = (c / np.maximum.accumulate(c) - 1).min(); vol = r.std() * np.sqrt(252)
    dn = r[r < 0].std() * np.sqrt(252)
    return dict(CAGR=(c[-1] ** (1 / yrs) - 1) * 100, MDD=dd * 100, Sharpe=r.mean() * 252 / vol, Vol=vol * 100, Sortino=r.mean() * 252 / dn)
for s in ['SPY.US', 'QQQ.US']:
    d = pd.read_parquet(PX / f'{s}.parquet'); d['date'] = pd.to_datetime(d.date); d = d.set_index('date')
    p = d.adjusted_close; raw = d.close
    sig = (p.rolling(50).mean() > p.rolling(200).mean()).astype(float).shift(1)   # 오늘 신호 → 다음 날 보유
    r = p.pct_change(); pos = sig
    trade = pos.diff().abs().fillna(0)
    cost = trade * (0.00015 + 0.01 / raw)
    strat = (pos * r - cost).iloc[200:].dropna(); bh = r.iloc[200:].dropna()
    for lab, sl in (('전체', slice(None)), ('2010~', slice('2010', None))):
        a, b = stats(strat[sl].values), stats(bh[sl].values)
        print(f'{s} {lab} {strat[sl].index[0].date()}~{strat[sl].index[-1].date()}: 골든크로스 ' + ' '.join(f'{k} {v:.2f}' for k, v in a.items())
              + f' | 단순보유 ' + ' '.join(f'{k} {v:.2f}' for k, v in b.items()) + f' | 진입·청산 {int(trade[sl].sum())}회, 보유 비중 {pos[sl].mean()*100:.0f}%')
