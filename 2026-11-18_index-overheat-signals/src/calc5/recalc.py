import json, numpy as np, pandas as pd
from pathlib import Path
R=Path(__file__).resolve().parent.parent; OUT=Path(__file__).resolve().parent/"out"
rng=np.random.default_rng(0)
# ---------- data
d=json.load(open(R/"data/yh_GSPC.json"))["chart"]["result"][0]
tz=d["meta"]["exchangeTimezoneName"]
px=pd.Series(d["indicators"]["quote"][0]["close"],index=pd.to_datetime(d["timestamp"],unit="s",utc=True).tz_convert(tz).tz_localize(None).normalize(),dtype=float).dropna()
px=px[~px.index.duplicated(keep="last")].sort_index()
ym=px.index.to_period("M")
m_last=px.groupby(ym).last(); m_first=px.groupby(ym).first()
LASTDATE=px.index[-1]
sh=pd.read_excel(R/"data/spdji/shiller_ie_data_2026.xls",sheet_name="Data",header=None,skiprows=8).iloc[:,:4]
sh.columns=["date","P","D","E"]
sh=sh[pd.to_numeric(sh["date"],errors="coerce").notna()].copy()
sh["date"]=sh["date"].astype(float)
yr=np.floor(sh["date"]+1e-9).astype(int); mo=np.round((sh["date"]-yr)*100).astype(int)
sh["per"]=[pd.Period(f"{y}-{m:02d}","M") for y,m in zip(yr,mo)]  # 2026.1 -> .10 -> month 10
sh=sh.set_index("per"); 
assert sh.index.is_unique and sh.loc[pd.Period("2026-10","M"),"P"]>7000
for c in "PE": sh[c]=pd.to_numeric(sh[c],errors="coerce")
# ---------- helpers
def applied_E(idx,lag):
    qe=sh[[p.month in (3,6,9,12) for p in sh.index]]["E"].dropna()
    s=pd.Series(qe.values,index=[p+lag for p in qe.index])
    return s.reindex(idx.union(s.index)).sort_index().ffill().reindex(idx)
def rz(v,win=120,mn=96):
    return (v-v.rolling(win,min_periods=mn).mean())/v.rolling(win,min_periods=mn).std(ddof=1)
def nw(y,x,L):
    X=np.column_stack([np.ones(len(x)),x]); b=np.linalg.solve(X.T@X,X.T@y); u=y-X@b
    Xu=X*u[:,None]; S=Xu.T@Xu
    for j in range(1,L+1):
        G=Xu[j:].T@Xu[:-j]; S+=(1-j/(L+1))*(G+G.T)
    A=np.linalg.inv(X.T@X); V=A@S@A
    return b[1],b[1]/np.sqrt(V[1,1])
def wmap(z):
    w=np.full(len(z),0.6); w[z<=-2]=1.0; w[(z>-2)&(z<=-1)]=0.8; w[(z>=1)&(z<2)]=0.4; w[z>=2]=0.2; return w
def sharpe(r): return r.mean()/r.std(ddof=1)*np.sqrt(12)
def cagr(r): return np.prod(1+r)**(12/len(r))-1
def mdd(r): c=np.cumprod(1+r); return (c/np.maximum.accumulate(c)-1).min()
def episodes(months,gap):
    if len(months)==0: return 0
    m=np.array([p.ordinal for p in months]); return 1+int((np.diff(m)>gap).sum())
def run(name,var,zser,ex,delay=0,gap=6,h12mode="spec"):
    """zser: z by signal month (month-end), ex: exec price by month (price of month t+1 used for signal t)"""
    z=zser.dropna()
    if delay: z=zser.shift(delay).dropna()
    idx=z.index; z=z.values
    last_ex=ex.index[-1]
    # signal month t -> exec price ex[t+1]
    e=lambda t,k: ex.get(t+k,np.nan)
    ret12=np.array([e(t,13)/e(t,1)-1 for t in idx]); 
    if h12mode=="alt": ret12=np.array([e(t,12)/e(t,0)-1 if False else np.nan for t in idx])
    ok=~np.isnan(ret12)
    y=np.log1p(ret12[ok]); zz=z[ok]; n=ok.sum()
    beta,t=nw(y,zz,12)
    h=n//2; _,t1=nw(y[:h],zz[:h],12); _,t2=nw(y[h:],zz[h:],12); half=str(idx[ok][h-1])
    # strategy
    ret1=np.array([e(t,2)/e(t,1)-1 for t in idx]); sok=~np.isnan(ret1)
    w=wmap(z[sok]); r1=ret1[sok]
    def net(w): dw=np.abs(np.diff(w,prepend=w[0])); return w*r1-dw*0.0005
    rs=net(w); S=sharpe(rs); aw=w.mean(); rc=0.6*r1; rb=r1
    ps=[]
    N=len(w)
    for k in range(12,N-12+1): ps.append(sharpe(net(np.roll(w,k))))
    ps=np.array(ps); pct=float((ps<S).mean())
    zv=z[ok]; mi=idx[ok]
    ep=lambda cond: episodes(list(mi[cond]),gap)
    zlast=zser.index[-1]
    row=dict(market="SP500",ind=name,start=str(idx[0]),end=str(idx[-1]),n_months=len(idx),nw_beta=beta,nw_t=t,n=int(n),
      t_first_half=t1,t_second_half=t2,half=half,strat_cagr=cagr(rs),strat_sharpe=S,strat_mdd=mdd(rs),avg_w=aw,
      c60_cagr=cagr(rc),c60_sharpe=sharpe(rc),c60_mdd=mdd(rc),bh_cagr=cagr(rb),bh_sharpe=sharpe(rb),bh_mdd=mdd(rb),
      placebo_pct=pct,n_placebo=len(ps),ep_hot=ep(zv>=1),ep_cold=ep(zv<=-1),ep_hot2=ep(zv>=2),ep_cold2=ep(zv<=-2),
      variant=var,delay=delay)
    # J
    J1=(t<=-2.0) and (abs(t)>=2.73); J2=(row["ep_hot"]>=3 and row["ep_cold"]>=3)
    J3=(S>row["c60_sharpe"]) and pct>=0.9; J4=(t2<0)
    row.update(J1=J1,J2=J2,J3=J3,J4=J4,verdict="시그널" if (J1 and J2 and J3 and J4) else ("참고지표" if (J1 and J4) else "기각"),
       ep_hot_gap7=episodes(list(mi[zv>=1]),7),ep_cold_gap7=episodes(list(mi[zv<=-1]),7),
       ep_hot_allmonths=episodes(list(idx[z>=1]),6),ep_cold_allmonths=episodes(list(idx[z<=-1]),6))
    return row
def build(lag,pxm_last,pxm_first,start=None):
    E=applied_E(pxm_last.index,lag)
    per=(pxm_last/E).dropna()
    if start is not None: per=per[per.index>=start]
    return per,rz(per)
rows=[]; extra={}
lastm=m_last.index[-1]  # 2026-11 partial
exg=m_first
def now_vals(per,z,price_now,Ereg):
    return z.iloc[-1],per.iloc[-1]
for lag,var,delay in [(3,"lag3",0),(3,"lag3",1),(2,"lag2",0),(4,"lag4",0)]:
    per,z=build(lag,m_last,m_first)
    # signal months: exclude partial last month (2026-11) but record it as 'now'
    zsig=z[z.index<lastm]
    r=run(f"PER_SH_{var}",var,zsig,exg,delay=delay)
    r.update(z_now=z.iloc[-1],v_now=per.iloc[-1],now=str(lastm)); rows.append(r)
# long: Shiller P monthly average, 1900~
Pm=sh["P"]; Pm=Pm[Pm.index>=pd.Period("1900-01","M")]
Eapp=applied_E(Pm.index,3); per=(Pm/Eapp).dropna(); z=rz(per)
lastP=Pm.index[-1]
zs=z[z.index<lastP]
r=run("PER_SH_long","long1900_shillerP",zs,Pm,delay=0); r.update(z_now=z.iloc[-1],v_now=per.iloc[-1],now=str(lastP)); rows.append(r)
df=pd.DataFrame(rows); df.to_csv(OUT/"recalc.csv",index=False)
pd.set_option("display.width",250,"display.max_columns",60); print(df.T)
# diagnostics: save Yahoo coverage
print(px.index[0],px.index[-1],lastm)
