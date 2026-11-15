import numpy as np, pandas as pd, sys
sys.path.insert(0,'~/work/quant_us/scripts')
from load import yh
from engine import *
from idx import strategies
pd.set_option('display.width',250)
# 지수 가격(배당 제외) 장기 검증: 양쪽 모두 배당 미포함이라 상대비교만 의미
res=[]
for t,start in [('GSPC','1971-01-01'),('NDX','1986-11-01')]:
    df=yh(t); df=df[df['open']>0]
    # 1980년대 이전 시가 결측(=종가) 많음 → 시가=전일 종가로 대체되면 그대로 사용
    S=strategies(df,0.15 if t=='GSPC' else 0.22)
    bench,_=run_single(df,S['Buy&Hold'],start)
    for k in ['Buy&Hold','Faber 10개월선','200일선','골든크로스 50/200','12개월 시계열모멘텀',[x for x in S if x.startswith('변동성타기팅 ')][0],'RSI(2) 평균회귀','월말월초 효과']:
        r,pos=run_single(df,S[k],start); d=metrics(r,bench,pos,k); d['대상']=t; res.append(d)
        r.to_pickle(f"out/long_{t}_{k.replace('/','-')}.pkl")
R=pd.DataFrame(res); R.to_csv('out/long_metrics.csv',index=False)
print(R[['대상','전략','CAGR','MDD','Sharpe','Sortino','연변동성','베타','Calmar','시장노출','매매횟수','승률','손익비','PF']].round(3).to_string())
