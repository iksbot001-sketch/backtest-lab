import numpy as np, pandas as pd, sys
sys.path.insert(0,'~/work/quant_us/scripts')
from load import yh
from engine import cash_daily, trades, run_single
from idx import strategies, rsi
pd.set_option('display.width',250); pd.set_option('display.max_columns',40)
SETS=[('SPY','1994-03-01'),('QQQ','1999-12-01'),('GSPC','1971-01-01'),('NDX','1986-11-01')]
out={}
print('### A. 현재 상태')
for t,_ in SETS:
    df=yh(t); c=df['adj']; ma50=c.rolling(50).mean(); ma200=c.rolling(200).mean()
    print(t,df.index[-1].date(),'200일선 이격 %+.1f%%'%((c.iloc[-1]/ma200.iloc[-1]-1)*100),'50/200 %+.1f%%'%((ma50.iloc[-1]/ma200.iloc[-1]-1)*100),
          '12m %+.1f%%'%((c.iloc[-1]/c.iloc[-253]-1)*100),'20d vol %.1f%%'%(c.pct_change().tail(20).std()*np.sqrt(252)*100),
          '고점대비 %.1f%%'%((c.iloc[-1]/c.cummax().iloc[-1]-1)*100),'RSI14 %.0f'%rsi(c,14).iloc[-1])

print('\n### B. 골든크로스 ON/OFF 상태별 일간 초과수익 → 연속 켈리 f*=μ/σ²')
rows=[]
for t,st in SETS:
    df=yh(t); c=df['adj']; cd=cash_daily(df.index)
    gc=(c.rolling(50).mean()>c.rolling(200).mean()).shift(1)   # 전일 신호
    ex=(c.pct_change()-cd)
    m=df.index>=st
    for lab,mask in [('전체',m),('GC ON',m&(gc==True)),('GC OFF',m&(gc==False))]:
        x=ex[mask].dropna(); mu=x.mean()*252; sd=x.std()*np.sqrt(252); n=len(x)/252
        se=sd/np.sqrt(n)
        rows.append(dict(대상=t,상태=lab,연수=round(n,1),초과수익μ=mu,변동성σ=sd,Sharpe=mu/sd,켈리=mu/sd**2,
                         켈리_μ하한1SE=(mu-se)/sd**2,하프켈리=mu/sd**2/2))
B=pd.DataFrame(rows); print(B.round(3).to_string())

print('\n### C. 지금과 비슷한 상태(GC ON, 200일선 +0~+12%, 12개월 수익 >0) 이후 수익 분포 (월말 샘플, 겹침 최소화)')
rows=[]
for t,st in SETS:
    df=yh(t); c=df['adj']; ma50=c.rolling(50).mean(); ma200=c.rolling(200).mean()
    d200=c/ma200-1; m12=c/c.shift(252)-1
    s=pd.Series(df.index,df.index); me=(s.groupby(df.index.to_period('M')).transform('max')==s)&(df.index>=st)
    sim=(ma50>ma200)&(d200>0)&(d200<0.12)&(m12>0)
    for h,hl in [(63,'3개월'),(126,'6개월'),(252,'12개월')]:
        f=c.shift(-h)/c-1
        for lab,mask in [('무조건',me),('유사상태',me&sim)]:
            x=f[mask].dropna(); w=x[x>0]; l=x[x<=0]
            rows.append(dict(대상=t,기간=hl,조건=lab,표본=len(x),평균=x.mean(),중앙=x.median(),승률=len(w)/len(x),
                    손익비=w.mean()/abs(l.mean()),하위5=x.quantile(.05),최악=x.min(),
                    이산켈리=(len(w)/len(x))-(1-len(w)/len(x))/(w.mean()/abs(l.mean()))))
C=pd.DataFrame(rows); print(C.round(3).to_string())

print('\n### D. 매매 단위 켈리: 이산공식 W-(1-W)/R vs 실제 매매수익분포의 로그성장 최대화')
rows=[]
for t,st in [('SPY','1994-03-01'),('QQQ','2000-03-01'),('GSPC','1971-01-01'),('NDX','1986-11-01')]:
    df=yh(t); S=strategies(df,0.2)
    for k in ['골든크로스 50/200','200일선','12개월 시계열모멘텀']:
        r,pos=run_single(df,S[k],st); tr=trades(r,pos); w=tr[tr>0]; l=tr[tr<=0]
        W=len(w)/len(tr); R=w.mean()/abs(l.mean())
        fs=np.linspace(0,min(20,0.999/abs(tr.min())),4000); g=[np.log1p(f*tr).sum() for f in fs]
        class _R: pass
        res=_R(); res.x=fs[int(np.argmax(g))]
        rows.append(dict(대상=t,전략=k,매매수=len(tr),승률=W,손익비=R,이산켈리=W-(1-W)/R,최악매매=tr.min(),경험적켈리=res.x))
print(pd.DataFrame(rows).round(3).to_string())

print('\n### E. 실현 경로에서 레버리지별 성과 (골든크로스 ON일 때 f배, OFF면 현금; 차입비용=단기금리+1%)')
def levpath(t,st,en=None,filt=True):
    df=yh(t); c=df['adj']; cd=cash_daily(df.index); r=c.pct_change()
    gc=(c.rolling(50).mean()>c.rolling(200).mean()).shift(1).fillna(False) if filt else pd.Series(True,df.index)
    m=(df.index>=st)&((df.index<=en) if en else True)
    out=[]
    for f in [0.5,1,1.25,1.5,2,2.5,3]:
        rr=np.where(gc,f*r-(f-1)*(cd+0.01/252)*(f>1)+(1-f)*cd*(f<1),cd)
        rr=pd.Series(rr,df.index)[m].fillna(0)
        # 전환 비용
        sw=gc.astype(int).diff().abs()[m].fillna(0)*f*0.0008; rr=rr-sw
        eq=(1+rr).cumprod(); n=len(rr)/252
        out.append(dict(f=f,CAGR=eq.iloc[-1]**(1/n)-1,MDD=(eq/eq.cummax()-1).min(),
                        Sharpe=(rr-cd[m]).mean()/(rr-cd[m]).std()*np.sqrt(252)))
    return pd.DataFrame(out)
for t,st,en in [('QQQ','2000-03-01',None),('QQQ','2010-01-01',None),('NDX','1986-11-01',None),('SPY','1994-03-01',None),('GSPC','1971-01-01',None)]:
    a=levpath(t,st,en); b=levpath(t,st,en,False)
    print(f'-- {t} {st[:4]}~  [GC필터] / [단순보유]')
    print(pd.concat([a.set_index('f'),b.set_index('f').add_prefix('보유_')],axis=1).round(3).to_string())

print('\n### F. 워크포워드 켈리: 매년 초 과거 데이터(ON 상태)만으로 μ/σ² 추정 → 다음 1년 적용')
def wf(t,st,frac,cap):
    df=yh(t); c=df['adj']; cd=cash_daily(df.index); r=c.pct_change(); ex=r-cd
    gc=(c.rolling(50).mean()>c.rolling(200).mean()).shift(1).fillna(False)
    rv=r.rolling(60).std().shift(1)*np.sqrt(252)
    yrs=sorted(set(df.index.year)); res=[]
    lev=pd.Series(np.nan,df.index)
    for y in yrs:
        past=(df.index.year<y)&gc.values
        if past.sum()<252*8: continue
        x=ex[past]; mu=x.mean()*252
        lev[df.index.year==y]=mu  # 연초 μ 고정, σ는 직전 60일 실현변동성으로 매일 갱신(변동성타기팅형 켈리)
    f=(lev/rv**2*frac).clip(0,cap)
    rr=np.where(gc,f*r-(f-1).clip(lower=0)*(cd+0.01/252)+(1-f).clip(lower=0)*cd,cd)
    rr=pd.Series(rr,df.index); ok=lev.notna()&(df.index>=st); rr=rr[ok].fillna(0)
    eq=(1+rr).cumprod(); n=len(rr)/252
    return dict(대상=t,시작=rr.index[0].date(),켈리비율=frac,상한=cap,평균비중=f[ok&gc].mean(),CAGR=eq.iloc[-1]**(1/n)-1,MDD=(eq/eq.cummax()-1).min(),
                Sharpe=(rr-cd[rr.index]).mean()/(rr-cd[rr.index]).std()*np.sqrt(252))
rows=[]
for t in ['NDX','GSPC']:
    for frac,cap in [(1,10),(0.5,10),(0.5,2),(0.5,1),(0.25,1),(0.25,2)]:
        rows.append(wf(t,'1900-01-01',frac,cap))
print(pd.DataFrame(rows).round(3).to_string())
