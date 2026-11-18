import json, numpy as np, pandas as pd
D='data/'
def yh(f):
    r=json.load(open(D+f))['chart']['result'][0]
    s=pd.Series(r['indicators']['quote'][0]['close'],index=pd.to_datetime(r['timestamp'],unit='s').normalize()).dropna()
    return s[~s.index.duplicated(keep='last')]
def per_m(s): s=s.copy(); s.index=s.index.to_period('M'); return s
def firstclose(s):
    g=s.groupby(s.index.to_period('M')).first(); return g
def lastv(s): return s.groupby(s.index.to_period('M')).last()
def nw(y,X,L):
    X=np.column_stack([np.ones(len(X)),X]); b=np.linalg.lstsq(X,y,rcond=None)[0]; e=y-X@b; n=len(y)
    Xe=X*e[:,None]; S=Xe.T@Xe
    for l in range(1,L+1):
        w=1-l/(L+1); G=Xe[l:].T@Xe[:-l]; S+=w*(G+G.T)
    XtXi=np.linalg.inv(X.T@X); V=XtXi@S@XtXi
    return b[1],b[1]/np.sqrt(V[1,1]),n
def zscore(v,excl=False):
    m=v.rolling(120,min_periods=96).mean(); s=v.rolling(120,min_periods=96).std(ddof=1)
    if excl: m=m.shift(1); s=s.shift(1)
    return (v-m)/s
def zone(z):
    return pd.cut(z,[-np.inf,-2,-1,1,2,np.inf],labels=['Z<=-2','-2<Z<=-1','neutral','1<=Z<2','Z>=2'],right=True) # placeholder
def zone(z):
    o=pd.Series(index=z.index,dtype=object)
    o[z>=2]='Z>=2'; o[(z>=1)&(z<2)]='1<=Z<2'; o[(z>-1)&(z<1)]='neutral'; o[(z>-2)&(z<=-1)]='-2<Z<=-1'; o[z<=-2]='Z<=-2'
    return o
W={'Z<=-2':1,'-2<Z<=-1':.8,'neutral':.6,'1<=Z<2':.4,'Z>=2':.2}
def episodes(mask):
    idx=[i for i,x in enumerate(mask) if x]; ep=0; last=None
    for i in idx:
        if last is None or i-last>6: ep+=1   # 6개월 초과 공백 후 재진입=새 에피소드
        last=i
    return ep
def mdd(r): c=(1+r).cumprod(); return (c/c.cummax()-1).min()
def perf(r):
    n=len(r); c=(1+r).prod(); return c**(12/n)-1, r.mean()/r.std(ddof=1)*np.sqrt(12), mdd(r)
krx=pd.read_csv(D+'kospi_per_pbr_krx.csv',parse_dates=['date']).set_index('date').replace('-',np.nan)
for c in ['per','pbr']: krx[c]=pd.to_numeric(krx[c])
gs=yh('yh_GSPC.json')
pe=pd.read_csv(D+'spx_pe_m.csv',parse_dates=['date']); pe=pe.groupby(pe.date.dt.to_period('M')).pe.last()
pb=pd.read_csv(D+'spx_pbr_q.csv',parse_dates=['date']); pb=pb.groupby(pb.date.dt.to_period('M')).pbr.last()
def reidx(s): return s.reindex(pd.period_range(s.index.min(),'2026-11',freq='M'))
pe=reidx(pe).ffill().shift(1)
pb=reidx(pb).ffill().shift(3)
series={'KOSPI_PER':(lastv(krx.per.dropna()),firstclose(krx.close)),
        'KOSPI_PBR':(lastv(krx.pbr.dropna()),firstclose(krx.close)),
        'SP500_PER':(pe,firstclose(gs)),'SP500_PBR':(pb,firstclose(gs))}
rows=[];zrows=[]
res={}
for k,(v,px) in series.items():
  for var,(excl,delay) in {'base':(False,0),'excl_cur':(True,0),'delay1':(False,1)}.items():
    mk,ind=k.split('_')
    z=zscore(v.dropna(),excl).dropna()
    if delay: z=z.shift(delay).dropna()
    pxm=px.reindex(pd.period_range(px.index.min(),px.index.max(),freq='M'))
    ex=pxm.shift(-1)  # exec price month t+1
    def fr(h): return pxm.shift(-(1+h))/ex-1
    dfm=pd.DataFrame({'z':z}); 
    for h in(3,6,12): dfm[f'r{h}']=fr(h).reindex(dfm.index)
    dfm['lr12']=np.log1p(dfm.r12); dfm['zone']=zone(dfm.z); dfm['nxt']=(pxm.shift(-2)/ex-1).reindex(dfm.index)
    dfm=dfm[(dfm.index<=px.index.max())&(dfm.index>=px.index.min())]
    a=dfm.dropna(subset=['r12'])
    b,t,n=nw(a.lr12.values,a.z.values,12)
    half=a.index[len(a)//2]
    t1=nw(a.lr12.values[:len(a)//2],a.z.values[:len(a)//2],12)[1]; t2=nw(a.lr12.values[len(a)//2:],a.z.values[len(a)//2:],12)[1]
    # strategy
    s=dfm.dropna(subset=['nxt']); w=s.zone.map(W).astype(float); gr=w*s.nxt
    cost=w.diff().abs().fillna(w.iloc[0])*0.0005; sr=gr-cost
    cagr,sh,dd=perf(sr); c60=perf(0.6*s.nxt-0*s.nxt); bh=perf(s.nxt)
    cr=perf(0.6*s.nxt)
    rows.append(dict(market=mk,ind=ind,variant=var,start=str(dfm.index[0]),end=str(dfm.index[-1]),n_months=len(dfm),nw_beta=b,nw_t=t,n=n,t_first_half=t1,t_second_half=t2,
      strat_cagr=cagr,strat_sharpe=sh,strat_mdd=dd,avg_w=w.mean(),c60_cagr=cr[0],c60_sharpe=cr[1],bh_cagr=bh[0],bh_sharpe=bh[1],bh_mdd=bh[2],z_now=dfm.z.iloc[-1]))
    if var=='base':
      for zn in ['Z<=-2','-2<Z<=-1','neutral','1<=Z<2','Z>=2']:
        g=dfm[dfm.zone==zn]; zrows.append(dict(market=mk,ind=ind,zone=zn,months=len(g),episodes=episodes((dfm.zone==zn).values),
          r3=g.r3.mean(),r6=g.r6.mean(),r12=g.r12.mean(),r12_med=g.r12.median(),up12=(g.r12.dropna()>0).mean() if g.r12.notna().any() else np.nan))
      zrows.append(dict(market=mk,ind=ind,zone='ALL',months=len(dfm),r3=dfm.r3.mean(),r6=dfm.r6.mean(),r12=dfm.r12.mean(),r12_med=dfm.r12.median(),up12=(dfm.r12.dropna()>0).mean()))
# VIX>=30
vix=yh('yh_VIX.json'); vm=vix.groupby(vix.index.to_period('M')).max()
orows=[]
for mk,px in [('SP500',gs),('KOSPI',yh('yh_KS11.json'))]:
    fc=firstclose(px); pxm=fc.reindex(pd.period_range(fc.index.min(),fc.index.max(),freq='M')); ex=pxm.shift(-1)
    r12=(pxm.shift(-13)/ex-1)
    for nm,m in [('ALL',vm.index>=vm.index[0]),('VIXmax>=30',(vm>=30).values)]:
        idx=vm.index[m]; x=r12.reindex(idx).dropna()
        orows.append(dict(market=mk,cond=nm,months=len(idx),n12=len(x),r12=x.mean(),r12_med=x.median(),up12=(x>0).mean(),episodes=episodes([i in set(idx) for i in vm.index]) if nm!='ALL' else np.nan))
pd.DataFrame(rows).to_csv('calc/out/recalc.csv',index=False)
pd.DataFrame(zrows).to_csv('calc/out/recalc_zones.csv',index=False)
pd.DataFrame(orows).to_csv('calc/out/recalc_overlay.csv',index=False)
