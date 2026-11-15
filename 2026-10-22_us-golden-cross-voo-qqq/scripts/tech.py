import numpy as np, pandas as pd, sys
sys.path.insert(0,'~/work/quant_us/scripts')
from load import yh
from engine import *
pd.set_option('display.width',250); pd.set_option('display.max_columns',30)
import sys as _s
UNIV={'today8':['AAPL','MSFT','GOOGL','AMZN','META','NVDA','TSLA','AVGO'],
 'exante2013':['AAPL','GOOGL','MSFT','IBM','ORCL','QCOM','INTC','CSCO','META','AMZN']}
TAG=_s.argv[1] if len(_s.argv)>1 else 'today8'
U=UNIV[TAG]
px={t:yh(t) for t in U}; qqq=yh('QQQ')
idx=qqq.index[qqq.index>='2012-01-01']
C=pd.DataFrame({t:px[t]['adj'] for t in U}).reindex(idx)
ret=C.pct_change()
s=pd.Series(idx,idx); me=s.groupby(idx.to_period('M')).transform('max')==s
fri=pd.Series(idx.dayofweek==4,idx)
def at(mask,W): return W.where(mask,np.nan).ffill().fillna(0)
def topk(score,k):
    rk=score.rank(axis=1,ascending=False); return (rk<=k).astype(float).div(k)
S={}
S['동일가중 B&H(월 리밸런싱)']=at(me,C.notna().astype(float).div(C.notna().sum(1),axis=0))
mom121=C.shift(21)/C.shift(252)-1
mom6=C.shift(21)/C.shift(126)-1
for k in [2,3,4]: S[f'모멘텀 12-1 상위{k}']=at(me,topk(mom121,k))
S['모멘텀 6-1 상위3']=at(me,topk(mom6,3))
vol60=ret.rolling(60).std()
iv=(1/vol60); S['역변동성 가중']=at(me,iv.div(iv.sum(1),axis=0))
S['저변동성 상위4']=at(me,topk(-vol60,4))
ma200=C.rolling(200).mean(); up=(C>ma200).astype(float)
S['종목별 200일선 필터(1/8씩)']=at(me,up/len(U))
# 듀얼모멘텀: 12-1 상위3 중 12개월 수익>현금인 것만
cd=cash_daily(idx); ci=(1+cd).cumprod()
absm=(C/C.shift(252)).gt(ci/ci.shift(252),axis=0)
S['듀얼모멘텀 상위3']=at(me,topk(mom121,3)*absm)
# 단기 반전 (Lehmann 1990, Jegadeesh 1990): 매주 금요일 5일 수익 하위3
r5=C/C.shift(5)-1
S['단기반전 주간 하위3']=at(fri,topk(-r5,3))
# 바스켓 변동성타기팅 25%
ew=S['동일가중 B&H(월 리밸런싱)']
br=(ew.shift(1)*ret).sum(1); bv=br.rolling(20).std()*np.sqrt(252)
S['동일가중+변동성타기팅 25%']=at(fri,ew.mul((0.25/bv).clip(upper=1),axis=0))
start='2013-07-01'
qb,_=run_single(qqq,pd.Series(1.0,qqq.index),start)
res=[]
d=metrics(qb,qb,None,'QQQ Buy&Hold'); res.append(d)
for k,W in S.items():
    W=W.fillna(0)
    r,expo=run_multi(px,W,start)
    d=metrics(r,qb,None,k); d['평균노출']=expo.mean()
    # 종목 단위 매매 손익비
    T=[]
    for t in U:
        ww=(W[t]>0).astype(float)
        rr,pp=run_single(px[t].reindex(idx),ww,start); T+=list(trades(rr,pp))
    T=np.array(T); w_=T[T>0]; l_=T[T<=0]
    d.update(매매횟수=len(T),승률=len(w_)/len(T),손익비=w_.mean()/abs(l_.mean()),PF=w_.sum()/abs(l_.sum()))
    d['연회전율']=W.diff().abs().sum(1)[W.index>=start].sum()/ (len(r)/252)
    res.append(d); r.to_pickle(f"out/tech_{TAG}_{k.replace('/','-')}.pkl")
# 모멘텀-동일가중 월간 초과수익 t값
ew_r=pd.read_pickle(f"out/tech_{TAG}_동일가중 B&H(월 리밸런싱).pkl")
for k in S:
    rr=pd.read_pickle(f"out/tech_{TAG}_{k.replace('/','-')}.pkl")
    dm=((1+rr).resample('ME').prod()-(1+ew_r).resample('ME').prod())
    for d in res:
        if d['전략']==k: d['초과(연)']=dm.mean()*12; d['t값']=dm.mean()/dm.std()*np.sqrt(len(dm))
R=pd.DataFrame(res); R.to_csv('out/tech_metrics_'+TAG+'.csv',index=False)
cols=['전략','초과(연)','t값','CAGR','ROI','MDD','Sharpe','Sortino','연변동성','베타','Calmar','평균노출','매매횟수','승률','손익비','PF','월손익비','연회전율']
print(R[cols].round(3).to_string())
