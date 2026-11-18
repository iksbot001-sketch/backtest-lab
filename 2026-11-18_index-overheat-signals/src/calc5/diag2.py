exec(open("recalc.py").read().split("rows=[]; extra")[0])
for lag in (3,2,4):
    per,z=build(lag,m_last,m_first); zs=z[z.index<m_last.index[-1]].dropna()
    ok=zs.index<=pd.Period("2025-10","M")
    for nm,c in [("hot",zs>=1),("cold",zs<=-1),("hot2",zs>=2),("cold2",zs<=-2)]:
        print(lag,nm,"confirmed",episodes(list(zs.index[c&ok]),6),"all",episodes(list(zs.index[c]),6),"all+now",episodes(list(z.dropna().index[(z.dropna()>=1) if nm=="hot" else (z.dropna()<=-1)]),6) if nm in("hot","cold") else "")
    print(zs[zs>=1].index[-12:].astype(str).tolist())
