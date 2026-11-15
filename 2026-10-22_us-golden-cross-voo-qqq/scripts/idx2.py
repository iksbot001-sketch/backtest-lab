import numpy as np, pandas as pd, sys
sys.path.insert(0,'~/work/quant_us/scripts')
from load import yh
from engine import *
from idx import strategies
pd.set_option('display.width',250); pd.set_option('display.max_columns',30)
cols=['대상','구간','전략','CAGR','MDD','Sharpe','Sortino','연변동성','베타','Calmar','시장노출','매매횟수','승률','손익비','PF']
# --- 1) 구간별 (2000~2009 / 2010~2026: 대부분 전략이 2010 이전에 발표 → 2010~ 는 사실상 표본 외)
res=[]
for t,tv in [('SPY',0.15),('QQQ',0.22)]:
    df=yh(t); S=strategies(df,tv)
    for lab,s,e in [('2000-09','2000-01-01','2009-12-31'),('2010-26','2010-01-01',None)]:
        bench,_=run_single(df,S['Buy&Hold'],s,e)
        for k,w in S.items():
            r,pos=run_single(df,w,s,e); d=metrics(r,bench,pos,k); d['대상']=t; d['구간']=lab; res.append(d)
R=pd.DataFrame(res); R.to_csv('out/idx_sub_metrics.csv',index=False)
print(R[cols].round(3).to_string())

# --- 2) 레버리지 + 추세필터 (Gayed & Bilello 2016 'Leverage for the Long Run')
def lev_run(df,w,L,start,er=0.0095):
    er=er if L>1 else 0.0
    idx=df.index; c=df['adj']; o=df['aopen']; cd=cash_daily(idx)
    on=o/c.shift(1)-1; intr=c/o-1
    wp=w.reindex(idx).fillna(0).shift(1).fillna(0); wpp=w.reindex(idx).fillna(0).shift(2).fillna(0)
    lev_day=L*(on+intr+on*intr)-(L-1)*cd-er/252   # 레버리지 ETF 일간 수익(합성)
    # 단순화: 신호 전환일엔 시가 체결 (오버나이트 구간은 이전 비중)
    lev_on=L*on-(L-1)*cd-er/252; lev_in=(1+lev_day)/(1+lev_on)-1
    gross=wpp*lev_on+wp*lev_in+(1-wp)*cd
    cost=(wp-wpp).abs()*(FEE+0.0002)   # 레버리지ETF 스프레드 가정 +0.02%
    r=(gross-cost)[idx>=pd.Timestamp(start)]; r.iloc[0]=0
    return r, wp[r.index]
res=[]
for t,start in [('SPY','1994-03-01'),('QQQ','2000-03-01'),('QQQ','2010-01-01')]:
    df=yh(t); S=strategies(df,0.2); bench,_=run_single(df,S['Buy&Hold'],start)
    for L in [1,2,3]:
        for k in ['Buy&Hold','200일선','Faber 10개월선','골든크로스 50/200']:
            r,pos=lev_run(df,S[k],L,start); d=metrics(r,bench,pos,f'{L}배 {k}'); d['대상']=t; d['구간']=start[:4]+'~'; res.append(d)
            r.to_pickle(f"out/lev_{t}_{start[:4]}_{L}_{k.replace('/','-')}.pkl")
R2=pd.DataFrame(res); R2.to_csv('out/lev_metrics.csv',index=False)
print(R2[cols].round(3).to_string())
