import numpy as np, pandas as pd
from pathlib import Path
R = Path(__file__).resolve().parent.parent
src = open(R / "calc8/recalc8.py").read().split("rows = []\ndef add")[0].replace("R = Path(__file__).resolve().parent.parent", "R = Path('%s')" % R).replace("Path(__file__).resolve().parent / \"out\"", "R / 'calc8' / 'out'")
exec(src)
a = pd.read_csv(R / "out/windows_stats.csv")
def pl(zm, ex, lo, off):
    zm = zm.dropna(); idx, zz, r1, ok = horizon(zm, ex, 1); w = wmap(zz[ok]); r1 = r1[ok]; N = len(w)
    net = lambda ww: ww * r1 - np.abs(np.diff(ww, prepend=ww[0])) * 0.0005
    S = sharpe(net(w)); ps = np.array([sharpe(net(np.roll(w, k))) for k in range(lo, N - off)])
    return round(float((ps < S).mean()), 4), round(float((ps <= S).mean()), 4), len(ps)
for nm in ["KOSPI PBR", "SOX 이격도"]:
    if nm in VAL:
        v, sym = VAL[nm]; z = rz(v.dropna(), 120, 96)
        print(nm, "src", a[(a.combo == nm) & (a.window == "10y")].placebo.values)
        for lo, off in [(12, 11), (12, 12), (12, 13), (13, 12), (12, 0), (1, 0)]:
            print(lo, off, pl(z, EX[sym], lo, off))
