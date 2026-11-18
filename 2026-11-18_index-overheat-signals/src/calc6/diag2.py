exec(open('calc6/recalc.py').read().split("rows = []")[0])
v,ex=SERIES["KOSPI PBR"]; z=zroll(v).dropna(); idx=z.index[z.index<ex.index[-1]]
e=lambda t,k: ex.get(t+k,np.nan)
r1=np.array([e(t,2)/e(t,1)-1 for t in idx]); sok=~np.isnan(r1); w=wmap(z.loc[idx].values[sok]); r1=r1[sok]; N=len(w); print("N",N)
def sh_(ww,pre,first): 
    d=np.abs(np.diff(ww,prepend=pre if pre is not None else ww[0])); return sharpe(ww*r1-d*0.0005)
for nm,pre in [("w0",None),("zero",0.0)]:
    S=sh_(w,pre,0)
    for rng in [range(12,N-12+1),range(12,N-12),range(12,N-11),range(1,N)]:
        ps=np.array([sh_(np.roll(w,k),pre,0) for k in rng]); print(nm,rng,len(ps),round((ps<S).mean(),6),round((ps<=S).mean(),6),round(S,4))
# compare: 0.697143
print('---')
def cost(ww,mode):
    if mode=="entry": d=np.abs(np.diff(ww,prepend=0.0))
    elif mode=="none": d=np.r_[0,np.abs(np.diff(ww))]
    elif mode=="wrap": d=np.abs(ww-np.roll(ww,1))
    elif mode=="w0": d=np.abs(np.diff(ww,prepend=ww[0]))
    return d*0.0005
for mode in ["entry","none","wrap","w0"]:
    S=sharpe(w*r1-cost(w,mode))
    for nm,rng in [("12..N-12",range(12,N-12+1)),("excl",range(12,N-12))]:
        ps=np.array([sharpe(np.roll(w,k)*r1-cost(np.roll(w,k),mode)) for k in rng])
        print(mode,nm,len(ps),round((ps<S).mean(),6),round(S,4))
