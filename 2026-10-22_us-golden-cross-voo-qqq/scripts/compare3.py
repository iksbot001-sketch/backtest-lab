"""SPY vs VOO vs QQQ (+IVV, QQQM 참고) 비교"""
import sys; sys.path.insert(0,'~/work/quant_us/scripts')
import numpy as np, pandas as pd
from load import yh
from engine import run_single, metrics, cash_daily
from idx import strategies
pd.set_option('display.width',250); pd.set_option('display.max_columns',30)
T=['SPY','VOO','IVV','QQQ','QQQM']; px={t:yh(t) for t in T}
print('### A. 총수익(배당 재투자) 공통 구간')
for st in ['2010-09-10','2020-10-14']:
    row={}
    for t in T:
        a=px[t]['adj']; a=a[a.index>=st]
        if a.index[0]>pd.Timestamp(st)+pd.Timedelta(days=5): continue
        n=(a.index[-1]-a.index[0]).days/365.25; row[t]=f"{(a.iloc[-1]/a.iloc[0])**(1/n)-1:.4%}"
    print(st,'~',row)
r=pd.DataFrame({t:px[t]['adj'].pct_change() for t in T})
y=(1+r[r.index>='2010-09-10']).groupby(r[r.index>='2010-09-10'].index.year).prod()-1
y['VOO-SPY(%p)']=(y.VOO-y.SPY)*100; y['IVV-SPY(%p)']=(y.IVV-y.SPY)*100; y['QQQM-QQQ(%p)']=(y.QQQM-y.QQQ)*100
print(y[['SPY','VOO','IVV','QQQ','VOO-SPY(%p)','IVV-SPY(%p)','QQQM-QQQ(%p)']].round(4).to_string())
x=r[r.index>='2010-09-13'].dropna(subset=['SPY','VOO'])
print('일간 VOO-SPY 차이 표준편차(연율) %.3f%%, 상관 %.5f, 연평균 차이 %.3f%%p'%((x.VOO-x.SPY).std()*np.sqrt(252)*100,x.VOO.corr(x.SPY),(x.VOO-x.SPY).mean()*252*100))
print('\n### B. 거래대금(최근 60일 평균, 억달러)')
for t in T: d=px[t].tail(60); print(t, round((d.volume*d.close).mean()/1e8,1))
print('\n### C. 골든크로스·데드크로스 날짜 비교 (2011~)')
for t in ['SPY','VOO','IVV']:
    c=px[t]['close']; gc=(c.rolling(50).mean()>c.rolling(200).mean()); ch=gc.astype(int).diff(); ev=ch[(ch!=0)&(ch.index>='2011-06-01')].dropna()
    print(t,[(i.strftime('%y.%m.%d'),'G' if v>0 else 'D') for i,v in ev.items()])
print('\n### D. 골든크로스 전략 & 보유, 2011-07~ 공통 구간')
res=[]
for t in ['SPY','VOO','IVV','QQQ']:
    S=strategies(px[t],0.15)
    bench,_=run_single(px['SPY'],pd.Series(1.0,px['SPY'].index),'2011-07-01')
    for k in ['Buy&Hold','골든크로스 50/200']:
        rr,pos=run_single(px[t],S[k],'2011-07-01'); d=metrics(rr,bench,pos,k); d['대상']=t; res.append(d)
        rr.to_pickle(f'out/c3_{t}_{k.replace("/","-")}.pkl')
R=pd.DataFrame(res); print(R[['대상','전략','CAGR','ROI','MDD','Sharpe','Sortino','연변동성','베타','매매횟수','승률','손익비','PF']].round(4).to_string())
print('\n### E. S&P500(VOO 또는 SPY) + QQQ 혼합, 각자 골든크로스 규칙, 매일 비중 유지')
def mix(a,b,st):
    out=[]
    for w in [1,.7,.5,.3,0]:
        rr=(w*a+(1-w)*b).dropna(); rr=rr[rr.index>=st]; eq=(1+rr).cumprod(); n=len(rr)/252; cd=cash_daily(rr.index); ex=rr-cd
        out.append(dict(SP비중=w,CAGR=eq.iloc[-1]**(1/n)-1,MDD=(eq/eq.cummax()-1).min(),Sharpe=ex.mean()/ex.std()*np.sqrt(252),변동성=rr.std()*np.sqrt(252)))
    return pd.DataFrame(out)
a=pd.read_pickle('out/c3_VOO_골든크로스 50-200.pkl'); b=pd.read_pickle('out/c3_QQQ_골든크로스 50-200.pkl')
print('VOO+QQQ 2011.7~'); print(mix(a,b,'2011-07-01').round(4).to_string())
a=pd.read_pickle('out/r_SPY_골든크로스 50-200.pkl'); b=pd.read_pickle('out/r_QQQ_골든크로스 50-200.pkl')
print('SPY+QQQ 2000.3~ (닷컴·금융위기 포함)'); print(mix(a,b,'2000-03-01').round(4).to_string())
a=pd.read_pickle('out/r_SPY_Buy&Hold.pkl'); b=pd.read_pickle('out/r_QQQ_Buy&Hold.pkl')
print('보유 SPY+QQQ 2000.3~'); print(mix(a,b,'2000-03-01').round(4).to_string())
print('상관(골든크로스 보유일) SPY-QQQ', round(r.SPY.corr(r.QQQ),3))
