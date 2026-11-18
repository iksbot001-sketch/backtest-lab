exec(open('calc6/recalc.py').read().split("rows = []")[0])
v,ex=SERIES["KOSPI PBR"]; zr=zroll(v); zf=zfix(v); r0=zr.dropna().index[0]
print("PBR n",len(v),v.index[0],v.index[-1],"mean",round(v.mean(),3),"sd",round(v.std(ddof=1),3),"min",v.min(),"max",v.max())
print("mean/sd on >=rolling start:",round(v[v.index>=r0].mean(),3),round(v[v.index>=r0].std(ddof=1),3), "| mean/sd pre-start:",round(v[v.index<r0].mean(),3),round(v[v.index<r0].std(ddof=1),3))
d=pd.DataFrame({'v':v,'zr':zr,'zf':zf,'ze':zexp(v)}); print(d.dropna().corr().round(3))
print("z_now: roll",round(zr.iloc[-1],2),"fixed",round(zf.iloc[-1],2),"exp",round(zexp(v).iloc[-1],2), "v_now",v.iloc[-1],v.index[-1])
print("rolling mean at start/end", round(v.rolling(120).mean().dropna().iloc[0],3), round(v.rolling(120).mean().iloc[-1],3))
# hot/cold months and episodes
def eps(z,cond,okset):
    m=[p for p in z.index if p in okset and cond(z[p])]
    out=[];last=None
    for p in m:
        if last is None or p.ordinal-last.ordinal>6: out.append([p,p])
        else: out[-1][1]=p
        last=p
    return [(str(a),str(b)) for a,b in out]
lastm=ex.index[-1]
ok=set(p for p in zf.dropna().index if p<lastm and not np.isnan(ex.get(p+13,np.nan)))
for nm,z in [("fixed",zf.dropna()),("fixed_cut",zf[zf.index>=r0].dropna()),("expanding",zexp(v).dropna()),("rolling",zr.dropna())]:
    okz=set(p for p in z.index if p in ok)
    print(nm,"HOT>=1 eps",eps(z,lambda x:x>=1,okz)); print(nm,"COLD<=-1 eps",eps(z,lambda x:x<=-1,okz))
# t on sub-periods, fixed z, by 12m-return-resolved months
def tsub(z,a,b):
    idx=[p for p in z.dropna().index if p<lastm and a<=p<=b and not np.isnan(ex.get(p+13,np.nan))]
    y=np.log1p([ex[p+13]/ex[p+1]-1 for p in idx]); x=z.loc[idx].values; return len(idx),round(nw(y,x,12)[1],2)
P=pd.Period
for a,b in [("2002-04","2009-12"),("2010-03","2026-10"),("2002-04","2014-12"),("2015-01","2026-10")]:
    print("fixed z t",a,b,tsub(zf,P(a),P(b)),"| rolling z t",tsub(zr,P(a),P(b)) if P(a)>=r0 else "n/a")
# early-year (2002-04..2010-02) contribution: fixed-z t using only that period
# leave-2025-out-ish robustness
for yr in [2008,2009,2025]:
    idx=[p for p in zf.dropna().index if p<lastm and p.year!=yr and not np.isnan(ex.get(p+13,np.nan))]
    y=np.log1p([ex[p+13]/ex[p+1]-1 for p in idx]); print("fixed LOYO",yr,round(nw(y,zf.loc[idx].values,12)[1],2))
