import json, numpy as np, pandas as pd
M={'SP500':'GSPC','NASDAQ100':'NDX','SOX':'SOX','KOSPI':'KS11','KOSDAQ':'KQ11'}
def load(t):
    r=json.load(open(f'data/yh_{t}.json'))['chart']['result'][0]
    s=pd.Series(r['indicators']['quote'][0]['close'],index=pd.to_datetime(r['timestamp'],unit='s').normalize(),dtype=float)
    s=s.dropna(); s=s[~s.index.duplicated(keep='last')].sort_index(); return s
def nw(y,x,L):
    y=np.asarray(y);x=np.asarray(x);n=len(y);X=np.c_[np.ones(n),x]
    b=np.linalg.solve(X.T@X,X.T@y);e=y-X@b;u=X*e[:,None]
    S=u.T@u
    for l in range(1,L+1):
        w=1-l/(L+1);G=u[l:].T@u[:-l];S+=w*(G+G.T)
    A=np.linalg.inv(X.T@X);V=A@S@A
    return b[1],b[1]/np.sqrt(V[1,1])
def zone(z):
    return 'Z<=-2' if z<=-2 else '-2<Z<=-1' if z<=-1 else 'neutral' if z<1 else '1<=Z<2' if z<2 else 'Z>=2'
W={'Z<=-2':1.0,'-2<Z<=-1':.8,'neutral':.6,'1<=Z<2':.4,'Z>=2':.2}
def perf(r):
    r=np.asarray(r);n=len(r);g=np.prod(1+r)
    return g**(12/n)-1, r.mean()/r.std(ddof=1)*np.sqrt(12)
rows=[];zrows=[]
for mk,t in M.items():
    P=load(t);D=(P/P.rolling(200).mean()-1).dropna()
    for mode in ['rolling','fixed']:
        if mode=='rolling':
            z=((D-D.rolling(2520,min_periods=2000).mean())/D.rolling(2520,min_periods=2000).std(ddof=1)).dropna()
        else: z=(D-D.mean())/D.std(ddof=1)
        # month-end z
        zm=z.groupby(z.index.to_period('M')).last()
        # fill date: first trading day of each month (price series, whole history)
        fd=P.groupby(P.index.to_period('M')).apply(lambda s:s.index[0])
        fp=P.groupby(P.index.to_period('M')).first()*0+P.groupby(P.index.to_period('M')).apply(lambda s:s.iloc[0])
        # month-end z only valid if month is complete (last obs is last trading day) - latest partial month kept as 'now'
        last_month=P.index[-1].to_period('M')
        zm_now=zm.iloc[-1];z_now_month=zm.index[-1]
        zmc=zm[zm.index<last_month]   # completed months
        months=list(zmc.index)[1:];zmc=zmc.iloc[1:];n=len(months)
        pm=fp.to_dict()
        def pr(h,m): # price at fill of month m+1+h
            k=m+1+h; return pm.get(k,np.nan)
        r={h:np.array([pr(h,m)/pr(0,m)-1 for m in months]) for h in (3,6,12)}
        zv=zmc.values
        ok12=~np.isnan(r[12]);ok3=~np.isnan(r[3])
        b12,t12=nw(np.log1p(r[12][ok12]),zv[ok12],12)
        b3,t3=nw(np.log1p(r[3][ok3]),zv[ok3],3)
        half=n//2
        sh=np.arange(n)>=half
        _,t12h=nw(np.log1p(r[12][ok12&sh]),zv[ok12&sh],12)
        _,t12f=nw(np.log1p(r[12][ok12&~sh]),zv[ok12&~sh],12)
        _,t3h=nw(np.log1p(r[3][ok3&sh]),zv[ok3&sh],3)
        zones=np.array([zone(v) for v in zv])
        # zone table
        for zn in list(W)+['ALL']:
            idx=np.where(np.ones(n,bool) if zn=='ALL' else zones==zn)[0]
            ep=np.nan
            if zn!='ALL':
                ep=0;prev=-99
                for i in idx:
                    if i-prev>6: ep+=1
                    prev=i
            a12=r[12][idx];a12=a12[~np.isnan(a12)]
            dd=[]
            for i in idx:
                m=months[i];s=P[(P.index>=fd[m+1])&(P.index<=fd[m+13])] if (m+13) in fd.index else None
                if s is not None and len(s)>1: dd.append((s/s.iloc[0]).cummin().iloc[-1]-1)
            zrows.append(dict(market=mk,ind='DISP',zone=zn,months=len(idx),episodes=ep,
                r3=np.nanmean(r[3][idx]) if len(idx) else np.nan,r6=np.nanmean(r[6][idx]) if len(idx) else np.nan,
                r12=a12.mean() if len(a12) else np.nan,r12_med=np.median(a12) if len(a12) else np.nan,
                up12=(a12>0).mean() if len(a12) else np.nan,dd12_med=np.median(dd) if dd else np.nan,dd12_worst=min(dd) if dd else np.nan,mode=mode))
        # strategy: weight from month m applied fill(m+1)->fill(m+2)
        mr=np.array([pr(1,m)/pr(0,m)-1 for m in months]);okm=~np.isnan(mr)
        w=np.array([W[x] for x in zones])[okm];mrr=mr[okm]
        wprev=np.r_[0,w[:-1]];cost=0.0005*np.abs(w-wprev)
        sr=w*mrr-cost
        cg,sp=perf(sr);c6g,c6s=perf(0.6*mrr);bg,bs=perf(mrr)
        def mdd(x): c=np.cumprod(1+x);return (c/np.maximum.accumulate(c)-1).min()
        pl=[]
        nn=len(w)
        for s in range(12,nn-12):
            ww=np.roll(w,s);pl.append(perf(ww*mrr-0.0005*np.abs(ww-np.r_[0,ww[:-1]]))[1])
        pl=np.array(pl)
        pd.DataFrame({'date':[fd[m+1].date() for m in np.array(months)[okm]],'ret':sr}).to_csv(f'calc2/out/v2_ret_{mk}_{mode}.csv',index=False)
        rows.append(dict(market=mk,mode=mode,start=str(months[0]),end=str(months[-1]),n_months=n,nw_t=t12,nw_beta=b12,n=int(ok12.sum()),
            t_first_half=t12f,t_second_half=t12h,half=str(months[half]),nw_t3=t3,t3_second_half=t3h,
            strat_cagr=cg,strat_sharpe=sp,strat_mdd=mdd(sr),avg_w=w.mean(),c60_cagr=c6g,c60_sharpe=c6s,c60_mdd=mdd(0.6*mrr),
            bh_cagr=bg,bh_sharpe=bs,bh_mdd=mdd(mrr),placebo_pct=(pl<sp).mean(),n_placebo=len(pl),
            ep_hot=zrows[-2]['episodes'] if False else None,
            D_now=D.iloc[-1],z_daily_now=z.iloc[-1],D_mean_full=D.mean(),D_sd_full=D.std(ddof=1),D_start=str(D.index[0].date()),D_end=str(D.index[-1].date())))
        zz=[x for x in zrows if x['market']==mk and x['mode']==mode]
        rows[-1]['ep_hot']=zz[3]['episodes'];rows[-1]['ep_cold']=zz[1]['episodes'];rows[-1]['ep_hot2']=zz[4]['episodes'];rows[-1]['ep_cold2']=zz[0]['episodes']
        if mk=='SOX' and mode=='fixed':
            x=D[(D.index>='1995-10-16')&(D.index<='2026-11-09')]
            mu,sd=x.mean(),x.std(ddof=1)
            sox=dict(mean=mu,sd=sd,plus1=mu+sd,minus1=mu-sd,D_1109=D.loc['2026-11-09'] if pd.Timestamp('2026-11-09') in D.index else np.nan,D_last=D.iloc[-1],last_date=str(D.index[-1].date()),n=len(x))
            print(sox);json.dump({k:(float(v) if not isinstance(v,str) else v) for k,v in sox.items()},open('calc2/out/v2_sox_check.json','w'),indent=1)
pd.DataFrame(rows).to_csv('calc2/out/v2_recalc.csv',index=False)
pd.DataFrame(zrows).to_csv('calc2/out/v2_recalc_zones.csv',index=False)
