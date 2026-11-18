import sys; sys.argv=['x']
exec(open('calc6/recalc.py').read().split("rows = []")[0])
ks=yh("KS11"); exy=mfirst(ks)
print("krx close start",krx.close.dropna().index[0],"ks11 start",ks.index[0], "krx last",krx.index[-1],"ks last",ks.index[-1])
cmp=pd.concat([ex_ks,exy],axis=1).dropna(); print("max rel diff first-close krx vs yahoo", (cmp.iloc[:,0]/cmp.iloc[:,1]-1).abs().max())
for nm in ["KOSPI PER","KOSPI PBR"]:
    v,_=SERIES[nm]
    for exn,exx in [("krx",ex_ks),("yahoo",exy)]:
        for mode,z in [("rolling",zroll(v)),("fixed",zfix(v)),("fixed_ex_partial",zfix(v,v[v.index<pd.Period('2026-11','M')]))]:
            r,_=run(z,exx); print(nm,exn,mode,round(r['nw_t'],4),round(r['t_second_half'],3),round(r['placebo_pct'],4),r['ep_hot'],r['ep_cold'])
