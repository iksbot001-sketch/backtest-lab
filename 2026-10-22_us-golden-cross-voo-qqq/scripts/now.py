"""2026-10-21 종가 기준 현재 상태 (SPY/QQQ는 10-21 종가 773.09/725.20 추가)"""
import sys, re, numpy as np, pandas as pd
sys.path.insert(0,'~/work/quant_us/scripts')
from load import yh
from idx import rsi
LAST={'SPY':773.09,'QQQ':725.20,'VOO':710.72,'QQQM':298.64}; D=pd.Timestamp('2026-10-21')
def us_close(t):
    d=yh(t); c=d['close'].copy(); a=d['adj'].copy()
    if t in LAST and c.index[-1]<D: c.loc[D]=LAST[t]; a.loc[D]=LAST[t]
    return c,a
def kr(s):
    rows=[re.match(r'\s*\["(\d{8})",\s*([\d.]+),\s*([\d.]+),\s*([\d.]+),\s*([\d.]+)',l) for l in open(f'~/work/quant_us/kr/sj_{s}.txt')]
    df=pd.Series({pd.Timestamp(m.group(1)):float(m.group(5)) for m in rows if m}); return df[df.index<=D]
if __name__=='__main__':
    for t in ['SPY','VOO','QQQ','QQQM']:
        c,a=us_close(t); m50=c.rolling(50).mean(); m200=c.rolling(200).mean()
        print(t,c.iloc[-1],'1y고점',c.tail(252).max(),c.tail(252).idxmax().date(),'고점대비 %.1f%%'%((c.iloc[-1]/c.tail(252).max()-1)*100),
              '50d %.1f 200d %.1f'%(m50.iloc[-1],m200.iloc[-1]),'이격200 %+.1f%%'%((c.iloc[-1]/m200.iloc[-1]-1)*100),'50/200 %+.1f%%'%((m50.iloc[-1]/m200.iloc[-1]-1)*100),
              '12m %+.1f%%'%((a.iloc[-1]/a.iloc[-253]-1)*100),'YTD %+.1f%%'%((c.iloc[-1]/c[c.index<'2026-01-01'].iloc[-1]-1)*100),'RSI14 %.0f'%rsi(c,14).iloc[-1],
              '20dvol %.1f%%'%(a.pct_change().tail(20).std()*np.sqrt(252)*100))
    for s in ['KOSPI','KOSDAQ']:
        c=kr(s); m50=c.rolling(50).mean(); m200=c.rolling(200).mean()
        print(s,c.iloc[-1],'1y고점',c.tail(250).max(),c.tail(250).idxmax().date(),'고점대비 %.1f%%'%((c.iloc[-1]/c.tail(250).max()-1)*100),
              '50d %.1f 200d %.1f'%(m50.iloc[-1],m200.iloc[-1]),'이격200 %+.1f%%'%((c.iloc[-1]/m200.iloc[-1]-1)*100),'YTD %+.1f%%'%((c.iloc[-1]/c[c.index<'2026-01-01'].iloc[-1]-1)*100))
        gc=(m50>m200); ch=gc.astype(int).diff(); print('   ',[(i.date(),'GC' if v>0 else 'DC') for i,v in ch[ch!=0].dropna().tail(3).items()])
