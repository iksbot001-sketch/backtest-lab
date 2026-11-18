"""PREREG 7절 H6 — 사진 차트 디지털화 선행 PER. 서술 통계만(판정 안 함). 차트 방식(전체 고정 평균·σ)."""
import sys
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).parent)); import core
O = core.O; A = core.D / 'agy'
SRC = {'SOX': ('fwdpe_img1_sox.csv', 'SOX'), 'NASDAQ100(추정)': ('fwdpe_img2.csv', 'NDX'), 'SP500(추정)': ('fwdpe_img3.csv', 'GSPC')}
rows, ev_rows = [], []
for mkt, (fn, tk) in SRC.items():
    if not (A / fn).exists(): print('없음', fn); continue
    v = pd.read_csv(A / fn, parse_dates=['date']).set_index('date')['fwd_pe'].dropna()
    vm = core.month_end(v); z = (vm - vm.mean()) / vm.std()
    px = core.yh(tk); ent = core.first_td_close(px); e1 = ent.shift(-1)
    f = pd.DataFrame({f'r{h}': (ent.shift(-1 - h) / e1 - 1).reindex(z.index) for h in (3, 6, 12)}); f['z'] = z
    b, t, n = core.nw_t(np.log1p(f.r12.values), f.z.values, 12)
    for lab, m in [('ALL', f.z.notna()), ('z<=-1', f.z <= -1), ('-1<z<1', (f.z > -1) & (f.z < 1)), ('z>=1', f.z >= 1)]:
        s = f[m]
        rows.append(dict(market=mkt, cond=lab, months=len(s), episodes=len(core.episodes(m)) if lab != 'ALL' else np.nan,
                         r3=s.r3.mean(), r6=s.r6.mean(), r12=s.r12.mean(), up12=(s.r12.dropna() > 0).mean(), n12=int(s.r12.notna().sum()),
                         nw_t12=t if lab == 'ALL' else np.nan, mean=vm.mean(), sd=vm.std(), now=v.iloc[-1], z_now=z.iloc[-1]))
    for lab, m in [('z<=-1', f.z <= -1), ('z>=1', f.z >= 1)]:
        for e in core.episodes(m):
            ev_rows.append(dict(market=mkt, cond=lab, start=str(e), pe=vm[e], z=z[e], r3=f.r3[e], r12=f.r12[e]))
R = pd.DataFrame(rows); E = pd.DataFrame(ev_rows)
R.to_csv(O / 'fwdpe_desc.csv', index=False); E.to_csv(O / 'fwdpe_events.csv', index=False)
pd.set_option('display.width', 250); print(R.round(3).to_string()); print(E.round(3).to_string())
