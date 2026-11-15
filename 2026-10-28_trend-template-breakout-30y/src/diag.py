"""손실 원인 진단: 30y_A 거래를 신호일 조건별로 나눠 기대값(R) 비교."""
import re, numpy as np, pandas as pd
from pathlib import Path
RUN = Path(__file__).resolve().parent; K = Path('~/agent-fund-data/prices/kr')
t = pd.read_csv(RUN / 'out/30y_A/trades.csv', dtype={'code': str})
sig = pd.read_csv(RUN / 'out/signals_daily.csv', parse_dates=['date']).set_index('date').n_pass

def idx(sym):
    txt = (RUN / f'data/naver_{sym}.txt').read_text()
    r = re.findall(r'\["(\d{8})",\s*([\d.]+),\s*([\d.]+),\s*([\d.]+),\s*([\d.]+)', txt)
    s = pd.Series([float(x[4]) for x in r], index=pd.to_datetime([x[0] for x in r]))
    return s
kp, kq = idx('KOSPI'), idx('KOSDAQ')
reg = lambda s: (s > s.rolling(200).mean()) & (s.rolling(200).mean() > s.rolling(200).mean().shift(20))

rows = []
for code, g in t.groupby('code'):
    d = pd.read_parquet(K / f'{code}.parquet').set_index('date')
    c, h, l = d.close, d.high, d.low
    atr = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1).rolling(14).mean()
    hi52 = h.rolling(252).max(); amt20 = (c * d.volume).rolling(20).mean()
    for i, r in g.iterrows():
        sd, ed = pd.Timestamp(r.signal_date), pd.Timestamp(r.entry_date)
        if sd not in d.index: continue
        ref = hi52[sd] + atr[sd]
        rows.append(dict(i=i, dist=ref / c[sd] - 1, atrp=atr[sd] / c[sd], gap=d.open.get(ed, np.nan) >= r.entry,
                         amt=amt20[sd] / 1e8, run52=c[sd] / c.shift(252)[sd] - 1))
f = t.join(pd.DataFrame(rows).set_index('i'))
f['kospi_up'] = reg(kp).reindex(pd.to_datetime(f.signal_date), method='ffill').values
f['kosdaq_up'] = reg(kq).reindex(pd.to_datetime(f.signal_date), method='ffill').values
f['mkt_up'] = np.where(f.mkt == 'KOSPI', f.kospi_up, f.kosdaq_up)
f['npass'] = sig.reindex(pd.to_datetime(f.signal_date)).values
f['same_day_stop'] = f.entry_date == f.exit_date

def show(col, bins=None):
    k = pd.cut(f[col], bins) if bins is not None else f[col]
    g = f.groupby(k, observed=True).agg(n=('R', 'size'), win=('ret', lambda x: (x > 0).mean()), expR=('R', 'mean'),
                                        medR=('R', 'median'), sameday=('same_day_stop', 'mean'))
    print(f'\n[{col}]'); print(g.round(3).to_string())

show('mkt_up'); show('mkt'); show('gap'); show('dist', [0, .03, .05, .08, .12, .2, 1])
show('atrp', [0, .03, .045, .06, .08, 1]); show('amt', [0, 10, 30, 100, 1e6]); show('npass', [0, 5, 15, 30, 60, 1e4])
show('run52', [-1, .5, 1, 2, 100])
print('\n상위 5% 거래가 전체 R 합에서 차지:', round(f.R.nlargest(int(len(f) * .05)).sum() / f.R[f.R > 0].sum(), 2), ' 전체 R 합', round(f.R.sum(), 1))
f.to_csv(RUN / 'out/diag_30y_A.csv', index=False, encoding='utf-8-sig')
