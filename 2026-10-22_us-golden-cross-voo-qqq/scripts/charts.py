import pandas as pd, numpy as np, matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
fm.fontManager.addfont('/System/Library/Fonts/AppleSDGothicNeo.ttc')
plt.rcParams.update({'font.family':'Apple SD Gothic Neo','axes.unicode_minus':False,'axes.spines.top':False,'axes.spines.right':False,
  'axes.edgecolor':'#9a9890','axes.labelcolor':'#52514e','xtick.color':'#52514e','ytick.color':'#52514e','figure.facecolor':'#fcfcfb','axes.facecolor':'#fcfcfb'})
P=['#2a78d6','#eb6834','#1baf7a','#eda100','#e87ba4']
# 1. QQQ 누적 & 낙폭
names=['Buy&Hold','골든크로스 50-200','변동성타기팅 22%','12개월 시계열모멘텀','RSI(2) 평균회귀']
lab=['Buy&Hold','골든크로스 50/200','변동성 타기팅 22%','12개월 시계열 모멘텀','RSI(2) 평균회귀']
fig,ax=plt.subplots(2,1,figsize=(11,7.5),sharex=True,gridspec_kw={'height_ratios':[2.2,1]})
for i,(n,l) in enumerate(zip(names,lab)):
    r=pd.read_pickle(f'out/r_QQQ_{n}.pkl'); eq=(1+r).cumprod(); dd=eq/eq.cummax()-1
    ax[0].plot(eq,color=P[i],lw=2 if i==0 else 1.6,label=l); ax[1].plot(dd*100,color=P[i],lw=1.2)
    ax[0].annotate(f'{l}  {eq.iloc[-1]:.1f}배',(eq.index[-1],eq.iloc[-1]),xytext=(6,0),textcoords='offset points',color='#0b0b0b',fontsize=9,va='center')
ax[0].set_yscale('log'); ax[0].set_ylabel('누적 자산 (시작=1, 로그)'); ax[0].grid(axis='y',color='#e6e5e0',lw=.6)
ax[0].legend(frameon=False,loc='upper left',fontsize=9); ax[1].set_ylabel('고점 대비 낙폭 (%)'); ax[1].grid(axis='y',color='#e6e5e0',lw=.6)
ax[0].set_title('QQQ 2000.3~2026.10 : 대표 퀀트 전략 vs 보유 (비용 차감, 현금은 단기국채 금리)',loc='left',fontsize=12,color='#0b0b0b')
ax[0].set_xlim(right=pd.Timestamp('2032-01-01'))
fig.tight_layout(); fig.savefig('charts/01_qqq_equity_dd.png',dpi=160)
# 2. 승률 vs 손익비
R=pd.read_csv('out/idx_metrics.csv'); R=R[R['손익비'].notna()]
OFF={('SPY','200일선'):(6,-12),('SPY','변동성타기팅+200일선'):(6,4),('QQQ','200일선'):(4,-26),('QQQ','변동성타기팅+200일선'):(6,4),
 ('QQQ','12개월 시계열모멘텀'):(-6,6),('SPY','Faber 10개월선'):(6,-10),('QQQ','월말월초 효과'):(-6,8),('SPY','월말월초 효과'):(-8,-14),
 ('QQQ','IBS 평균회귀'):(-6,-10),('SPY','IBS 평균회귀'):(-4,-28),('QQQ','RSI(2) 평균회귀'):(6,4),('SPY','RSI(2) 평균회귀'):(6,-10),
 ('QQQ','돈치안 55/20 돌파'):(6,-10),('SPY','골든크로스 50/200'):(-6,8)}
fig,ax=plt.subplots(figsize=(11,7))
for i,t in enumerate(['SPY','QQQ']):
    s=R[R['대상']==t]; ax.scatter(s['승률']*100,s['손익비'],s=60,color=P[i],label=t,edgecolor='#fcfcfb',lw=2,zorder=3)
    for _,x in s.iterrows():
        off=OFF.get((t,x['전략']),(6,3))
        ax.annotate(f"{t} {x['전략']} (PF {x['PF']:.1f})",(x['승률']*100,x['손익비']),xytext=off,textcoords='offset points',fontsize=8,color='#52514e',
                    ha='right' if off[0]<0 else 'left')
w=np.linspace(15,80,200); ax.plot(w,(100-w)/w,color='#9a9890',ls='--',lw=1); ax.text(78,0.35,'손익분기선 (PF=1)',fontsize=8,color='#52514e',ha='right')
ax.set_yscale('log'); ax.set_xlabel('매매 승률 (%)'); ax.set_ylabel('손익비 = 평균 이익 ÷ 평균 손실 (로그)')
ax.set_title('손익비가 높은 전략은 승률이 낮다 — 추세추종 vs 평균회귀',loc='left',fontsize=12,color='#0b0b0b')
ax.grid(color='#e6e5e0',lw=.6); ax.legend(frameon=False); fig.tight_layout(); fig.savefig('charts/02_winrate_payoff.png',dpi=160)
# 3. 빅테크 생존편향
A=pd.read_csv('out/tech_metrics_today8.csv').set_index('전략'); B=pd.read_csv('out/tech_metrics_exante2013.csv').set_index('전략')
ks=['동일가중 B&H(월 리밸런싱)','모멘텀 12-1 상위2','모멘텀 12-1 상위3','모멘텀 6-1 상위3','저변동성 상위4','종목별 200일선 필터(1-8씩)'.replace('1-8','1/8'),'단기반전 주간 하위3']
ks=[k for k in ks if k in A.index]
y=np.arange(len(ks)); fig,ax=plt.subplots(figsize=(10,5.5))
ax.barh(y-0.2,A.loc[ks,'CAGR']*100,0.36,color=P[0],label='오늘의 빅테크 8 (사후 선정)')
ax.barh(y+0.2,B.loc[ks,'CAGR']*100,0.36,color=P[1],label='2013년 당시 대형 기술주 10 (사전 선정)')
for i,k in enumerate(ks):
    ax.text(A.loc[k,'CAGR']*100+0.5,i-0.2,f"{A.loc[k,'CAGR']*100:.0f}%",va='center',fontsize=8,color='#0b0b0b')
    ax.text(B.loc[k,'CAGR']*100+0.5,i+0.2,f"{B.loc[k,'CAGR']*100:.0f}%",va='center',fontsize=8,color='#0b0b0b')
ax.axvline(19.9,color='#9a9890',ls='--',lw=1); ax.text(20.3,len(ks)-0.5,'QQQ 보유 19.9%',fontsize=8,color='#52514e')
ax.set_yticks(y); ax.set_yticklabels([k.replace('1/8씩','1/N씩') for k in ks]); ax.invert_yaxis(); ax.set_xlabel('CAGR (%), 2013.7~2026.10')
ax.set_title('빅테크 모멘텀의 고수익은 종목 선정의 사후확신 효과',loc='left',fontsize=12,color='#0b0b0b'); ax.legend(frameon=False,loc='lower right')
fig.tight_layout(); fig.savefig('charts/03_bigtech_survivorship.png',dpi=160)
