import json, numpy as np, pandas as pd
O='out/'
P={'KOSPI PER':('panel_KOSPI_PER','KS11'),'KOSPI PBR':('panel_KOSPI_PBR','KS11'),
'S&P500 PER':('panel_SP500_PER_SH_lag3','GSPC'),'S&P500 PBR':('panel_SP500_PBR','GSPC'),
'KOSDAQ PER':('panel_KOSDAQ_PER','KQ11'),'KOSDAQ PBR':('panel_KOSDAQ_PBR','KQ11'),
'S&P500 이격도':('panel_SP500_DISP_rolling','GSPC'),'NASDAQ100 이격도':('panel_NASDAQ100_DISP_rolling','NDX'),
'SOX 이격도':('panel_SOX_DISP_rolling','SOX'),'KOSPI 이격도':('panel_KOSPI_DISP_rolling','KS11'),
'KOSDAQ 이격도':('panel_KOSDAQ_DISP_rolling','KQ11'),'SOX 선행PER':('panel_FPE_SOX_rolling5y','SOX'),
'NASDAQ100 선행PER':('panel_FPE_NDX_rolling5y','NDX'),'S&P500 선행PER':('panel_FPE_GSPC_rolling5y','GSPC')}
def px(sym):
    r=json.load(open(f'data/yh_{sym}.json'))['chart']['result'][0]
    s=pd.Series(r['indicators']['quote'][0]['close'],index=pd.to_datetime(r['timestamp'],unit='s')+pd.Timedelta(seconds=r['meta'].get('gmtoffset',0)))
    s=s.dropna(); s.index=s.index.normalize()
    return s.groupby(s.index.to_period('M')).first()  # first trading day close
def ols(y,x):
    X=np.c_[np.ones(len(x)),x]; b=np.linalg.lstsq(X,y,rcond=None)[0]; e=y-X@b
    return b,e,X
def nw(y,x,L):
    b,e,X=ols(y,x); n=len(y); XtXi=np.linalg.inv(X.T@X); u=X*e[:,None]
    S=u.T@u
    for l in range(1,L+1):
        w=1-l/(L+1); G=u[l:].T@u[:-l]; S+=w*(G+G.T)
    V=XtXi@S@XtXi; return b[1],b[1]/np.sqrt(V[1,1])
def ols_t(y,x):
    b,e,X=ols(y,x); n=len(y); s2=e@e/(n-2); V=s2*np.linalg.inv(X.T@X); return b[1]/np.sqrt(V[1,1])
def eps(flag,gap=6):
    idx=np.where(flag)[0]; c=0; last=None
    for i in idx:
        if last is None or i-last>gap: c+=1
        last=i
    return c
rows=[]
for name,(f,sym) in P.items():
    d=pd.read_csv(O+f+'.csv',index_col=0); d.index=pd.PeriodIndex(d.index,freq='M'); z=d['z'].dropna()
    p=px(sym)
    for h in (1,3,6,9,12):
        zs,rs=[],[]
        for t in z.index:
            a,b=t+1,t+1+h
            if a in p.index and b in p.index: zs.append(z[t]); rs.append(p[b]/p[a]-1); 
        zz=np.array(zs); y=np.log1p(np.array(rs)); n=len(y)
        # confirmed months are contiguous from first t
        beta,t=nw(y,zz,h)
        k=n//2; _,t2=nw(y[n-k:],zz[n-k:],h) if k>h+3 else (None,np.nan)
        ts=[]
        for o in range(h):
            yy,xx=y[o::h],zz[o::h]
            if len(yy)>=8: ts.append(ols_t(yy,xx))
        nov=np.median(ts) if ts else np.nan
        eh=eps(zz>=1); ec=eps(zz<=-1)
        j1=(t<=-2) and abs(t)>=3.32; j2=eh>=3 and ec>=3; j4=t2<0
        if h==12: v='(비교용)'
        elif j1 and j4 and j2: v='시그널'
        elif j1 and j4: v='판정 보류'
        else: v='기각'
        rows.append(dict(combo=name,h=h,n=n,start=str(z.index[0]),end=str(z.index[n-1]),beta=beta,nw_t=t,t_second_half=t2,nov_t=nov,ep_hot=eh,ep_cold=ec,j1=j1,j2=j2,j4=j4,verdict=v))
R=pd.DataFrame(rows); R.to_csv('calc7/out/recalc.csv',index=False)
S=pd.read_csv(O+'horizons_stats.csv').merge(R,on=['combo','h'],suffixes=('_o','_n'))
L=['# diff: recalc vs horizons_stats.csv\n']
for _,r in S.iterrows():
    m=[]
    for c in('nw_t','t_second_half','nov_t'):
        if not(abs(r[c+'_o']-r[c+'_n'])<=0.05) : m.append(f"{c} {r[c+'_o']:.3f}→{r[c+'_n']:.3f} (Δ{r[c+'_n']-r[c+'_o']:.3f})")
    for c in('n','ep_hot','ep_cold','verdict'):
        if r[c+'_o']!=r[c+'_n']: m.append(f"{c} {r[c+'_o']}→{r[c+'_n']}")
    if m: L.append(f"- {r['combo']} h={r['h']}: "+'; '.join(m))
L.append(f"\n총 {len(S)}행, 차이 행 {len(L)-1}")
open('calc7/out/diff.md','w').write('\n'.join(L))
print('\n'.join(L))
