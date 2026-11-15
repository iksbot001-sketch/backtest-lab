"""Independent re-implementation of V(h) (no engine import) to cross-check panel.csv."""
import pandas as pd

def V(row, r, h, tax=0.21, lag=0.75, G=0.04, N=40):
    rev = [row.rev0, row.rev1, row.rev2, row.rev3]; m = [row.m1, row.m2, row.m3]; sc = row.sc
    hg = h / 2
    hf = lambda x0, xT, k, hh: xT + (x0 - xT) * 0.5 ** (k / hh)
    nm = [x * (1 - tax) for x in m]
    g0 = rev[3] / rev[2] - 1
    ronic0 = nm[2] * sc
    fc = []; nop = []
    for k in (1, 2, 3):
        n = rev[k] * nm[k - 1]
        nxt = rev[k + 1] if k < 3 else rev[3] * (1 + hf(g0, G, 1, hg))
        fc.append(n - max(nxt - rev[k], 0) / sc); nop.append(n)
    rv = rev[3]
    for k in range(1, N + 1):
        rv *= 1 + hf(g0, G, k, hg)
        n = rv * nm[2]
        gn = hf(g0, G, k + 1, hg)
        ro = hf(ronic0, r, k, h) if ronic0 > r else ronic0
        re = n * gn / ro if (gn > 0 and ro > 0 and n > 0) else 0
        fc.append(n - re); nop.append(n)
    nT = nop[-1] * (1 + G)
    roe = hf(ronic0, r, N, h) if ronic0 > r else max(ronic0, 1e-9)
    tv = nT * (1 - G / roe) / (r - G) if nT > 0 else nT / (r - G)
    n = 3 + N
    pv = sum(fc[i] / (1 + r) ** (i + 1 - lag) for i in range(n))
    return pv + tv / (1 + r) ** (n - lag) + row.net_cash

p = pd.read_csv("out/panel.csv")
s = p.sample(5, random_state=7)
for row in s.itertuples():
    v = V(row, 0.09, 4) / row.mktcap
    print(row.ticker, row.t, f"inputs rev={row.rev0:.4g},{row.rev1:.4g},{row.rev2:.4g},{row.rev3:.4g} m={row.m1:.4f},{row.m2:.4f},{row.m3:.4f} sc={row.sc:.3f} nc={row.net_cash:.4g} mc={row.mktcap:.4g}",
          f"VP4_indep={v:.6f} panel={row.VP4:.6f} diff={abs(v-row.VP4):.2e}")
