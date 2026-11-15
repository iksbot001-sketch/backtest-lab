"""Forward PER(연준 FSR, I/B/E/S 12개월 선행) 조건을 붙인 골든크로스 전략 분석"""
import sys; sys.path.insert(0,'~/work/quant_us/scripts')
import numpy as np, pandas as pd
from load import yh
from engine import run_single, cash_daily, trades
pd.set_option('display.width',250); pd.set_option('display.max_columns',40)
PE=pd.read_csv('~/work/quant_us/data/sp500_fwd_pe_fed_fsr202605.csv',parse_dates=['date']).set_index('date')['fpe']
NOW=19.2
def pe_daily(idx):
    # 월 라벨 값은 다음 달 첫 거래일부터 사용(미래 데이터 방지)
    s=PE.copy(); s.index=s.index+pd.offsets.MonthBegin(1)
    return s.reindex(idx.union(s.index)).ffill().reindex(idx)
print('### 0. Forward PER 분포 1990.1~2026.4')
print('전체 중앙 %.1f, 25%% %.1f, 75%% %.1f, 90%% %.1f, 최고 %.1f(%s)'%(PE.median(),PE.quantile(.25),PE.quantile(.75),PE.quantile(.9),PE.max(),PE.idxmax().strftime('%Y.%m')))
print('현재 %.1f의 백분위: 전체 %.0f%%, 2010~ %.0f%%, 2016~ %.0f%%'%(NOW,(PE<NOW).mean()*100,(PE[PE.index>='2010']<NOW).mean()*100,(PE[PE.index>='2016']<NOW).mean()*100))
for lo,hi in [(0,14),(14,16),(16,18),(18,20),(20,22),(22,30)]: print(f'  {lo}~{hi}: {((PE>=lo)&(PE<hi)).mean()*100:.0f}% 개월')
BANDS=[(0,16,'16 미만'),(16,18,'16~18'),(18,20.5,'18~20.5 (현재 19.2)'),(20.5,30,'20.5 이상')]
SETS=[('SPY','1994-03-01'),('QQQ','2000-03-01'),('GSPC','1991-01-01'),('NDX','1991-01-01')]
print('\n### 1. 골든크로스 매매(매수 GC → 매도 DC) 건별, 진입 시점 forward PER 구간별')
rows=[]; allT=[]
for t,st in SETS:
    df=yh(t); c=df['close']; gc=(c.rolling(50).mean()>c.rolling(200).mean())
    w=gc.astype(float); r,pos=run_single(df,w,st); pe=pe_daily(df.index)
    on=(pos>0).astype(int); start=on.diff().fillna(on.iloc[0])==1; g=start.cumsum()
    for k,seg in r[on==1].groupby(g[on==1]):
        d0=seg.index[0]; eq=(1+seg).cumprod()
        allT.append(dict(대상=t,진입=d0.date(),청산=seg.index[-1].date(),보유일=len(seg),PER=pe.loc[d0],수익=eq.iloc[-1]-1,MDD=(eq/eq.cummax()-1).min(),
                         진행중=seg.index[-1]>=r.index[-1]))
T=pd.DataFrame(allT); T.to_csv('out/pe_gc_trades.csv',index=False)
for t,_ in SETS:
    x=T[T.대상==t]
    for lo,hi,lab in BANDS:
        y=x[(x.PER>=lo)&(x.PER<hi)&(~x.진행중)]
        if len(y)==0: continue
        w_=y.수익[y.수익>0]; l_=y.수익[y.수익<=0]
        rows.append(dict(대상=t,PER=lab,매매=len(y),승률=len(w_)/len(y),평균수익=y.수익.mean(),중앙=y.수익.median(),손익비=(w_.mean()/abs(l_.mean())) if len(l_) else np.nan,
                         PF=(w_.sum()/abs(l_.sum())) if len(l_) else np.inf,평균보유월=y.보유일.mean()/21,연환산=((1+y.수익).prod())**(252/y.보유일.sum())-1,최악=y.수익.min(),보유중MDD평균=y.MDD.mean()))
print(pd.DataFrame(rows).round(3).to_string())
print('\n진행 중인 매매:'); print(T[T.진행중].round(3).to_string())
print('\nSPY·QQQ 건별 상세'); print(T[T.대상.isin(['SPY','QQQ'])].round(3).to_string())

print('\n### 2. 골든크로스 상태 월말 진입 → 데드크로스에 매도(최대 12개월) 경로, forward PER 구간별')
rows=[]
for t,st in SETS:
    df=yh(t); a=df['adj']; c=df['close']; gc=(c.rolling(50).mean()>c.rolling(200).mean()).values; cd=cash_daily(df.index).values
    pe=pe_daily(df.index); s=pd.Series(df.index,df.index); me=((s.groupby(df.index.to_period('M')).transform('max')==s)&(df.index>=st)).values
    av=a.values; out=[]
    for i in np.where(me & gc)[0]:
        if i+253>=len(av) or np.isnan(pe.iloc[i]): continue
        v=1.0; peak=1.0; mdd=0; held=True; path=[]
        for k in range(1,253):
            j=i+k
            if held: v*=av[j]/av[j-1]
            else: v*=(1+cd[j])
            peak=max(peak,v); mdd=min(mdd,v/peak-1)
            if held and not gc[j]: held=False; v*=(1-0.0008)
            if k==126: v6=v
        out.append((pe.iloc[i],v6-1,v-1,mdd))
    O=pd.DataFrame(out,columns=['PER','r6','r12','mdd'])
    for lo,hi,lab in BANDS+[(0,99,'전체')]:
        y=O[(O.PER>=lo)&(O.PER<hi)]
        if len(y)<5: continue
        for h in ['r12']:
            x=y[h]; w_=x[x>0]; l_=x[x<=0]
            rows.append(dict(대상=t,PER=lab,표본=len(y),평균12m=x.mean(),중앙=x.median(),승률=(x>0).mean(),손익비=w_.mean()/abs(l_.mean()) if len(l_) else np.nan,
                             하위5=x.quantile(.05),평균6m=y.r6.mean(),평균MDD=y.mdd.mean(),하위5MDD=y.mdd.quantile(.05)))
P2=pd.DataFrame(rows); P2.to_csv('out/pe_gc_paths.csv',index=False); print(P2.round(3).to_string())

print('\n### 3. 전략 변형: 골든크로스 + forward PER 상한 필터 (PER > X면 신규 진입·보유 안 함)')
rows=[]
for t,st in SETS:
    df=yh(t); c=df['close']; gc=(c.rolling(50).mean()>c.rolling(200).mean()); pe=pe_daily(df.index)
    for X in [99,24,22,20,18]:
        w=(gc&(pe<X)).astype(float)
        r,pos=run_single(df,w,st); eq=(1+r).cumprod(); n=len(r)/252; cd=cash_daily(r.index); ex=r-cd
        tr=trades(r,pos); w_=tr[tr>0]; l_=tr[tr<=0]
        rows.append(dict(대상=t,PER상한=('없음' if X==99 else X),CAGR=eq.iloc[-1]**(1/n)-1,MDD=(eq/eq.cummax()-1).min(),Sharpe=ex.mean()/ex.std()*np.sqrt(252),
                         노출=(pos>0).mean(),매매=len(tr),승률=len(w_)/len(tr),손익비=w_.mean()/abs(l_.mean()) if len(l_) else np.nan))
print(pd.DataFrame(rows).round(3).to_string())

print('\n### 4. Forward PER과 이후 수익률 (월말, S&P500 지수 배당 제외)')
g=yh('GSPC')['close']; m=g.resample('ME').last(); pe=PE.copy(); pe.index=pe.index+pd.offsets.MonthEnd(0)
D=pd.DataFrame({'pe':pe,'p':m}).dropna()
for h,lab in [(12,'1년'),(36,'3년'),(60,'5년')]:
    D[lab]=(m.shift(-h)/m).reindex(D.index)**(12/h)-1
print(D[['1년','3년','5년']].corrwith(D.pe).round(2).to_string())
for lo,hi,lab in BANDS:
    y=D[(D.pe>=lo)&(D.pe<hi)]; print(lab, len(y), (y[['1년','3년','5년']].mean()*100).round(1).to_dict(), '1년 손실확률 %.0f%%'%((y['1년']<0).mean()*100))
