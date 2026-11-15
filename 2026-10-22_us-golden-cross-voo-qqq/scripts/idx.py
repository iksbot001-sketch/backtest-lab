import numpy as np, pandas as pd, sys
sys.path.insert(0,'~/work/quant_us/scripts')
from load import yh
from engine import *
def rsi(c,n):
    d=c.diff(); up=d.clip(lower=0).ewm(alpha=1/n,adjust=False).mean(); dn=(-d.clip(upper=0)).ewm(alpha=1/n,adjust=False).mean()
    return 100-100/(1+up/dn)
def month_end_flag(idx):
    s=pd.Series(idx,index=idx); return s.groupby(idx.to_period('M')).transform('max')==s

def strategies(df, tgt_vol):
    c=df['adj']; idx=df.index; S={}
    S['Buy&Hold']=pd.Series(1.0,idx)
    # 1 Faber(2007) 10개월 이평: 월말 종가 > 10개월 이평이면 보유, 월 1회 판단
    me=month_end_flag(idx); mc=c[me]; sig=(mc>mc.rolling(10).mean()).astype(float)
    S['Faber 10개월선']=sig.reindex(idx).ffill().fillna(0)
    # 2 200일선 (일간)
    S['200일선']=(c>c.rolling(200).mean()).astype(float)
    # 3 골든크로스 50/200
    S['골든크로스 50/200']=(c.rolling(50).mean()>c.rolling(200).mean()).astype(float)
    # 4 12개월 시계열 모멘텀 (Moskowitz-Ooi-Pedersen 2012), 월간
    cd=cash_daily(idx); cash_idx=(1+cd).cumprod()
    m12=(mc/mc.shift(12)) > (cash_idx[me]/cash_idx[me].shift(12))
    S['12개월 시계열모멘텀']=m12.astype(float).reindex(idx).ffill().fillna(0)
    # 5 변동성 타기팅 (Moreira-Muir 2017): 20일 실현변동성 역수, 최대 1배, 주 1회(금) 조정
    rv=c.pct_change().rolling(20).std()*np.sqrt(252)
    w=(tgt_vol/rv).clip(upper=1.0)
    fri=pd.Series(idx.dayofweek==4,idx)
    S[f'변동성타기팅 {int(tgt_vol*100)}%']=w.where(fri).ffill().fillna(0)
    # 6 변동성타기팅 + 200일선
    S['변동성타기팅+200일선']=S[f'변동성타기팅 {int(tgt_vol*100)}%']*S['200일선']
    # 7 Connors RSI(2) 평균회귀 (Connors & Alvarez 2009): 200일선 위 & RSI2<10 매수, 종가>5일선 청산
    r2=rsi(c,2); ma200=c.rolling(200).mean(); ma5=c.rolling(5).mean()
    pos=np.zeros(len(c)); h=0
    for i in range(len(c)):
        if h==0 and c.iloc[i]>ma200.iloc[i] and r2.iloc[i]<10: h=1
        elif h==1 and c.iloc[i]>ma5.iloc[i]: h=0
        pos[i]=h
    S['RSI(2) 평균회귀']=pd.Series(pos,idx)
    # 8 IBS 평균회귀: IBS=(C-L)/(H-L)<0.2 매수, >0.8 청산 (200일선 필터 없음)
    ibs=(df['close']-df['low'])/(df['high']-df['low']).replace(0,np.nan)
    pos=np.zeros(len(c)); h=0
    for i in range(len(c)):
        v=ibs.iloc[i]
        if h==0 and v<0.2: h=1
        elif h==1 and v>0.8: h=0
        pos[i]=h
    S['IBS 평균회귀']=pd.Series(pos,idx)
    # 9 월말월초 효과 (Ariel 1987, Lakonishok-Smidt 1988): 월 마지막 거래일 전날 종가 매수→ 새 달 3번째 거래일 종가 매도
    s=pd.Series(np.arange(len(idx)),idx); per=idx.to_period('M')
    rank_from_end=s.groupby(per).transform(lambda x: len(x)-1-np.arange(len(x)))
    rank_from_start=s.groupby(per).transform(lambda x: np.arange(len(x)))
    # 종가 t에 결정된 비중이 t+1 시가부터 적용 → 보유 원하는 날 하루 전 종가에 1
    hold=(rank_from_end<=0)|(rank_from_start<=2)   # 보유일: 말일, 1~3일차
    S['월말월초 효과']=hold.shift(-1).fillna(False).astype(float)
    # 10 터틀 돈치안 55/20 (Dennis, Faith 2007) 롱온리
    hi55=df['ahigh'].rolling(55).max().shift(1); lo20=df['alow'].rolling(20).min().shift(1)
    pos=np.zeros(len(c)); h=0
    for i in range(len(c)):
        if h==0 and c.iloc[i]>hi55.iloc[i]: h=1
        elif h==1 and c.iloc[i]<lo20.iloc[i]: h=0
        pos[i]=h
    S['돈치안 55/20 돌파']=pd.Series(pos,idx)
    return S

if __name__=='__main__':
    res=[]
    for t,tv,start in [('SPY',0.15,'1994-03-01'),('QQQ',0.22,'2000-03-01')]:
        df=yh(t); S=strategies(df,tv)
        bench,_=run_single(df,S['Buy&Hold'],start)
        for k,w in S.items():
            r,pos=run_single(df,w,start)
            d=metrics(r,bench,pos,k); d['대상']=t; res.append(d)
            kk=k.replace('/','-'); r.to_pickle(f'out/r_{t}_{kk}.pkl'); pos.to_pickle(f'out/p_{t}_{kk}.pkl')
    R=pd.DataFrame(res); R.to_csv('out/idx_metrics.csv',index=False)
    pd.set_option('display.width',250); pd.set_option('display.max_columns',30)
    cols=['대상','전략','CAGR','MDD','Sharpe','Sortino','연변동성','베타','Calmar','시장노출','매매횟수','승률','손익비','PF','월손익비','월PF']
    print(R[cols].round(3).to_string())
