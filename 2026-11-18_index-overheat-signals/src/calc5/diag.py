exec(open("recalc.py").read().split("rows=[]; extra")[0])
per,z=build(3,m_last,m_first); zs=z[z.index<m_last.index[-1]]
print("first valid z:",zs.dropna().index[0], "per first:",per.index[0],"count per before first z:",len(per))
a=run("a","a",zs,m_first)
b=run("b","b",zs[zs.index>=pd.Period("1998-01","M")],m_first)
for k in ["start","n_months","n","nw_beta","strat_sharpe","strat_cagr","placebo_pct","n_placebo","half"]: print(k,a[k],b[k])
