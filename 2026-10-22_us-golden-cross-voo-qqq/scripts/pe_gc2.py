import sys; sys.path.insert(0,'~/work/quant_us/scripts')
import numpy as np, pandas as pd
from load import yh
from engine import cash_daily
PE=pd.read_csv('~/work/quant_us/data/sp500_fwd_pe_fed_fsr202605.csv',parse_dates=['date']).set_index('date')['fpe']
def pe_daily(idx):
    s=PE.copy(); s.index=s.index+pd.offsets.MonthBegin(1); return s.reindex(idx.union(s.index)).ffill().reindex(idx)
BANDS=[(0,16,'16 미만'),(16,18,'16~18'),(18,20.5,'18~20.5 (현재)'),(20.5,30,'20.5 이상'),(0,99,'전체')]
rows=[]
for t,st in [('SPY','1994-03-01'),('QQQ','2000-03-01'),('GSPC','1991-01-01'),('NDX','1991-01-01')]:
    df=yh(t); a=df['adj']; c=df['close']; r=a.pct_change(); cd=cash_daily(df.index); ex=r-cd
    on=(c.rolling(50).mean()>c.rolling(200).mean()).shift(1).fillna(False); pe=pe_daily(df.index).shift(1)
    m0=(df.index>=st)&(df.index<='2026-05-31')
    for lo,hi,lab in BANDS:
        m=m0&on&(pe>=lo)&(pe<hi); x=ex[m].dropna()
        mu=x.mean()*252; sd=x.std()*np.sqrt(252)
        rows.append(dict(대상=t,PER=lab,연수=len(x)/252,초과수익=mu,변동성=sd,Sharpe=mu/sd,켈리=mu/sd**2))
print(pd.DataFrame(rows).round(3).to_string())
