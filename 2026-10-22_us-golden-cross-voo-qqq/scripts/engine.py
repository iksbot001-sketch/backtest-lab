import numpy as np, pandas as pd, sys
sys.path.insert(0,'~/work/quant_us/scripts')
from load import yh
FEE=0.0007      # 편도 수수료 0.07% (국내 증권사 해외주식 온라인 우대 수준)
TICK=0.01       # 슬리피지 1틱 = $0.01
irx=yh('IRX')['close']
def cash_daily(idx):
    r=irx.reindex(idx).ffill().bfill()/100
    return (1+r)**(1/252)-1

def run_single(df, w, start=None, end=None):
    """w: 목표 비중(0~1+) 시리즈, 종가 t에 결정 → t+1 시가에 체결."""
    idx=df.index; w=w.reindex(idx).fillna(0)
    if start: m=(idx>=pd.Timestamp(start))
    else: m=np.ones(len(idx),bool)
    if end: m&=(idx<=pd.Timestamp(end))
    c=df['adj']; o=df['aopen']; po=df['open']
    wp=w.shift(1).fillna(0)          # t일 시가에 바뀐 비중 (t-1 종가 신호)
    wpp=w.shift(2).fillna(0)         # t-1 종가~t 시가 구간 비중
    on=o/c.shift(1)-1; intr=c/o-1
    cd=cash_daily(idx)
    gross=wpp*on+wp*intr + (1-wpp)*cd*0.0 + (1-wp)*cd   # 현금은 일 단위 단기채 금리
    cost=(wp-wpp).abs()*(FEE+TICK/po)
    r=(gross-cost)[m]
    r.iloc[0]=0
    pos=wp[m]
    return r, pos

def run_multi(px, W, start=None):
    """px: dict ticker->df, W: DataFrame 목표비중(종가 결정) → 다음날 시가 체결"""
    idx=W.index
    C=pd.DataFrame({t:px[t]['adj'] for t in W.columns}).reindex(idx)
    O=pd.DataFrame({t:px[t]['aopen'] for t in W.columns}).reindex(idx)
    PO=pd.DataFrame({t:px[t]['open'] for t in W.columns}).reindex(idx)
    Wp=W.shift(1).fillna(0); Wpp=W.shift(2).fillna(0)
    on=(O/C.shift(1)-1).fillna(0); intr=(C/O-1).fillna(0)
    cd=cash_daily(idx)
    gross=(Wpp*on).sum(1)+(Wp*intr).sum(1)+(1-Wp.sum(1)).clip(lower=0)*cd
    cost=((Wp-Wpp).abs()*(FEE+TICK/PO.fillna(1e9))).sum(1)
    r=gross-cost
    if start: r=r[r.index>=pd.Timestamp(start)]; Wp=Wp.loc[r.index]
    r.iloc[0]=0
    return r, Wp.sum(1)

def trades(r,pos):
    """비중>0 연속 구간 = 1회 매매. 구간 누적수익(비용 포함)"""
    on=(pos>0).astype(int); g=(on.diff().fillna(on.iloc[0])==1).cumsum()
    out=[]
    for k,seg in r[on==1].groupby(g[on==1]):
        out.append((1+seg).prod()-1)
    return np.array(out)

def metrics(r, bench=None, pos=None, name=''):
    eq=(1+r).cumprod(); n=len(r)/252
    cagr=eq.iloc[-1]**(1/n)-1; roi=eq.iloc[-1]-1
    mdd=(eq/eq.cummax()-1).min()
    cd=cash_daily(r.index); ex=r-cd
    sd=r.std()*np.sqrt(252)
    sharpe=ex.mean()/ex.std()*np.sqrt(252)
    dn=np.sqrt((np.minimum(ex,0)**2).mean())*np.sqrt(252)
    sortino=ex.mean()*252/dn
    beta=np.nan
    if bench is not None:
        b=bench.reindex(r.index).fillna(0); beta=np.cov(r,b)[0,1]/b.var()
    mo=(1+r).resample('ME').prod()-1
    pw=mo[mo>0]; nl=mo[mo<0]
    d=dict(전략=name,CAGR=cagr,ROI=roi,MDD=mdd,Sharpe=sharpe,Sortino=sortino,연변동성=sd,베타=beta,
           Calmar=cagr/abs(mdd),월승률=(mo>0).mean(),월손익비=pw.mean()/abs(nl.mean()),월PF=pw.sum()/abs(nl.sum()))
    if pos is not None:
        d['시장노출']=(pos>0).mean()
        t=trades(r,pos)
        if len(t)>0 and (pos>0).mean()<0.97:
            w=t[t>0]; l=t[t<=0]
            d.update(매매횟수=len(t),승률=len(w)/len(t),손익비=(w.mean()/abs(l.mean())) if len(l) else np.inf,
                     PF=w.sum()/abs(l.sum()) if len(l) else np.inf,평균매매=t.mean())
    return d
