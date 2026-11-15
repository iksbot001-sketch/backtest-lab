"""추세 ON·고점권 상태(지금과 유사)에서 추가 낙폭 분포 → 일시매수 vs 분할매수 비교"""
import numpy as np, pandas as pd, sys
sys.path.insert(0,'~/work/quant_us/scripts')
from load import yh
from engine import cash_daily
pd.set_option('display.width',300); pd.set_option('display.max_columns',40)
FEE=0.0007
SETS=[('SPY','1994-03-01'),('QQQ','1999-12-01'),('GSPC','1971-01-01'),('NDX','1986-11-01')]
def prep(t,st):
    df=yh(t); c=df['adj']; ma50=c.rolling(50).mean(); ma200=c.rolling(200).mean()
    gc=(ma50>ma200); d200=c/ma200-1; m12=c/c.shift(252)-1
    sim=gc&(d200>0)&(d200<0.12)&(m12>0)
    s=pd.Series(df.index,df.index); me=(s.groupby(df.index.to_period('M')).transform('max')==s)&(df.index>=st)
    cd=cash_daily(df.index)
    ent=[i for i in np.where((me&sim).values)[0] if i+252<len(c)]
    return c.values,gc.values,cd.values,ent,df.index
# ---------- 1) 추가 낙폭 분포
print('### 1. 유사상태 진입 후 추가 낙폭(진입가 대비 최저점) 분포')
rows=[]
for t,st in SETS:
    c,gc,cd,ent,idx=prep(t,st)
    for h in [21,63,126,252]:
        mae=np.array([c[i:i+h+1].min()/c[i]-1 for i in ent])
        rows.append(dict(대상=t,기간=f'{h}일',표본=len(ent),중앙=np.median(mae),상위25=np.percentile(mae,25),상위10=np.percentile(mae,10),
            상위5=np.percentile(mae,5),최악=mae.min(),**{f'P(≤{k}%)':(mae<=-k/100).mean() for k in [3,5,8,10,15,20]}))
M=pd.DataFrame(rows); print(M.round(3).to_string()); M.to_csv('ladder/mae.csv',index=False)
# 데드크로스 전까지의 최대 낙폭 (매도 규칙 적용 시 실제로 맞는 낙폭)
print('\n데드크로스(50<200) 발생 전·1년 내 최저점, 그리고 데드크로스 시점 수익')
for t,st in SETS:
    c,gc,cd,ent,idx=prep(t,st); a=[];b=[]
    for i in ent:
        j=i+1
        while j<=i+252 and gc[j]: j+=1
        a.append(c[i:j+1].min()/c[i]-1); b.append(j<=i+252)
    a=np.array(a); print(t,'1년내 데드크로스 확률 %.0f%%'%(np.mean(b)*100),'| 매도 전까지 낙폭 중앙 %.1f%% 하위10%% %.1f%% 최악 %.1f%%'%(np.median(a)*100,np.percentile(a,10)*100,a.min()*100))

# ---------- 2) 분할 방식 시뮬레이션
# 단계: ('now',w) 즉시 / ('px',lv,w) 진입가 대비 lv 이하 지정가 / ('day',d,w) d거래일 후 / 미체결 처리 fallback: None=현금유지, d=그날 시장가
S={
 '일시 100%':dict(steps=[('now',1)]),
 '3개월 시간분할(1/3씩)':dict(steps=[('now',1/3),('day',21,1/3),('day',42,1/3)]),
 '6개월 시간분할(1/6씩)':dict(steps=[('now',1/6)]+[('day',21*k,1/6) for k in range(1,6)]),
 '50/25/25 @0/-5/-10% (6개월 후 잔량매수)':dict(steps=[('now',.5),('px',-.05,.25),('px',-.10,.25)],fb=126),
 '50/25/25 @0/-5/-10% (잔량 현금유지)':dict(steps=[('now',.5),('px',-.05,.25),('px',-.10,.25)],fb=None),
 '70/30 @0/-5% (3개월 후 잔량매수)':dict(steps=[('now',.7),('px',-.05,.3)],fb=63),
 '60/20/20 @0/-3/-7% (3개월 후 잔량매수)':dict(steps=[('now',.6),('px',-.03,.2),('px',-.07,.2)],fb=63),
 '40/30/30 @0/-5/-10% (6개월 후 잔량매수)':dict(steps=[('now',.4),('px',-.05,.3),('px',-.10,.3)],fb=126),
 '혼합: 50% 지금+잔량 3개월 분할, -5%면 즉시':dict(steps=[('now',.5),('daypx',21,-.05,1/6),('daypx',42,-.05,1/6),('daypx',63,-.05,1/6)]),
}
def sim(c,gc,cd,i,spec,H,exit_rule):
    steps=spec['steps']; fb=spec.get('fb'); filled=[False]*len(steps)
    units=0.0; cash=1.0; p0=c[i]; out=False; worst=0.0; peak=1.0; mdd=0.0; dep=0.0
    def buy(w,px):
        nonlocal units,cash,dep
        amt=min(w,cash); units+=amt*(1-FEE)/px; cash-=amt; dep+=amt
    for t in range(0,H+1):
        px=c[i+t]
        if t>0: cash*=(1+cd[i+t])
        if not out:
            if exit_rule and t>0 and not gc[i+t]:      # 데드크로스: 전량 매도, 미체결 취소
                cash+=units*px*(1-FEE); units=0; out=True
            else:
                for k,s in enumerate(steps):
                    if filled[k]: continue
                    if s[0]=='now' and t==0: buy(s[1],px); filled[k]=True
                    elif s[0]=='day' and t==s[1]: buy(s[2],px); filled[k]=True
                    elif s[0]=='px' and px<=p0*(1+s[1]): buy(s[2],px); filled[k]=True
                    elif s[0]=='daypx' and (t==s[1] or px<=p0*(1+s[2])): buy(s[3],px); filled[k]=True
                if fb is not None and t==fb:
                    for k,s in enumerate(steps):
                        if not filled[k]: buy(s[-1],px); filled[k]=True
        v=cash+units*px; peak=max(peak,v); mdd=min(mdd,v/peak-1)
    return v-1, mdd, dep
print('\n### 2. 분할 방식 비교 (자금 100 기준, 미투입 현금은 단기국채 금리)')
allrows=[]
for exit_rule in [True,False]:
    for H in [126,252]:
        for t,st in SETS:
            c,gc,cd,ent,idx=prep(t,st)
            base=np.array([sim(c,gc,cd,i,S['일시 100%'],H,exit_rule)[0] for i in ent])
            for name,spec in S.items():
                R=np.array([sim(c,gc,cd,i,spec,H,exit_rule) for i in ent]); r=R[:,0]
                allrows.append(dict(매도규칙=exit_rule,기간=H,대상=t,방식=name,평균=r.mean(),중앙=np.median(r),하위5=np.percentile(r,5),최악=r.min(),
                    평균MDD=R[:,1].mean(),최악MDD=R[:,1].min(),평균투입=R[:,2].mean(),일시대비승률=(r>base+1e-9).mean(),일시대비평균차=(r-base).mean(),
                    하락장차=(r-base)[base<0].mean() if (base<0).any() else np.nan))
A=pd.DataFrame(allrows); A.to_csv('ladder/scheme_compare.csv',index=False)
for (er,H),g in A.groupby(['매도규칙','기간']):
    print(f'\n--- 매도규칙(데드크로스 청산)={er}, 보유기간 {H}일 : 4개 데이터 평균')
    print(g.groupby('방식',sort=False)[['평균','중앙','하위5','최악','평균MDD','최악MDD','평균투입','일시대비승률','일시대비평균차','하락장차']].mean().round(4).to_string())
