"""탐색: 미래 정보 없는 '누적(expanding) 평균/σ' vs 10년 롤링 vs 전체 고정. 이격도 5 + 선행 PER 3."""
import sys
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).parent)); import core
O = core.O; core.DELAY = 0
def an(name, px, v, zm):
    orig = core.rolling_z; core.rolling_z = lambda s, *a, **k: zm.reindex(s.index)
    try: res, zt, st = core.analyze(name, px, 'x', v.reindex(zm.index))
    finally: core.rolling_z = orig
    t3 = core.nw_t(np.log1p(res.r3.values), res.z.values, 3)[1]
    return st['nw_t'], t3, st['placebo_pct'], f"{st['strat_sharpe']:.2f}/{st['c60_sharpe']:.2f}", str(res.index[0])
rows = []
for mkt, tk in [('SP500', 'GSPC'), ('NASDAQ100', 'NDX'), ('SOX', 'SOX'), ('KOSPI', 'KS11'), ('KOSDAQ', 'KQ11')]:
    px = core.yh(tk); D = (px / px.rolling(200, min_periods=200).mean() - 1).dropna(); Dm = core.month_end(D)
    zr = core.month_end(((D - D.rolling(2520, min_periods=2000).mean()) / D.rolling(2520, min_periods=2000).std()).dropna())
    ze = core.month_end(((D - D.expanding(2000).mean()) / D.expanding(2000).std()).dropna())
    zf = core.month_end((D - D.mean()) / D.std()); zfc = zf[zf.index >= zr.index[0]]
    for nm, z in [('rolling', zr), ('expanding', ze), ('fixed_same', zfc), ('fixed_full', zf)]:
        rows.append((f'{mkt} 이격도', nm) + an(mkt, px, Dm, z))
for mkt, fn, tk in [('SOX', 'fwdpe_img1_sox.csv', 'SOX'), ('NDX', 'fwdpe_img2.csv', 'NDX'), ('SPX', 'fwdpe_img3.csv', 'GSPC')]:
    w = pd.read_csv(core.D / 'agy' / fn, parse_dates=['date']).set_index('date')['fwd_pe']; px = core.yh(tk); vm = core.month_end(w)
    zr = core.month_end(((w - w.rolling(260, min_periods=156).mean()) / w.rolling(260, min_periods=156).std()).dropna())
    ze = core.month_end(((w - w.expanding(156).mean()) / w.expanding(156).std()).dropna())
    zf = core.month_end((w - w.mean()) / w.std()); zfc = zf[zf.index >= zr.index[0]]
    for nm, z in [('rolling5y', zr), ('expanding', ze), ('fixed_same', zfc), ('fixed_full', zf)]:
        rows.append((f'{mkt} 선행PER', nm) + an(mkt, px, vm, z))
D = pd.DataFrame(rows, columns=['combo', 'mode', 't12', 't3', 'placebo', 'sharpe', 'start']); D.to_csv(O / 'expanding_compare.csv', index=False)
pd.set_option('display.width', 200); print(D.round(2).to_string())
