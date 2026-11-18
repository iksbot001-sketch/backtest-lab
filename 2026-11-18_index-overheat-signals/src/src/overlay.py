"""조건3(VIX 결합)·조건4(기준금리) — PREREG 정의 그대로. 월간, t 신호 → t+1 첫 거래일 체결."""
import sys
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).parent)); import core
O = core.O

vix = core.yh('VIX'); P = vix.index.to_period('M')
vmax = vix.groupby(P).max(); vavg = vix.groupby(P).mean()
dff = pd.read_csv(core.D / 'fred_DFF.csv', parse_dates=[0], index_col=0).iloc[:, 0]
dff = pd.to_numeric(dff, errors='coerce').dropna(); ff = dff.groupby(dff.index.to_period('M')).mean()
ff_d12 = ff - ff.shift(12); ff_gap = ff - ff.rolling(120, min_periods=96).mean()

PX = {'SP500': core.yh('GSPC'), 'NASDAQ100': core.yh('NDX'), 'KOSPI': core.yh('KS11'), 'KOSDAQ': core.yh('KQ11')}

def fwd(px):
    ent = core.first_td_close(px); e1 = ent.shift(-1)
    f = pd.DataFrame({f'r{h}': ent.shift(-1 - h) / e1 - 1 for h in (3, 6, 12)})
    dd = {}
    for t in f.index:
        s = px[(px.index >= (t + 1).start_time) & (px.index < (t + 13).start_time)]
        dd[t] = (s / s.iloc[0]).min() - 1 if len(s) > 200 else np.nan
    f['dd12'] = pd.Series(dd); return f

def summ(f, mask, label, mkt):
    s = f[mask.reindex(f.index).fillna(False).astype(bool)]
    return dict(market=mkt, cond=label, months=len(s), episodes=len(core.episodes(mask.reindex(f.index).fillna(False))),
                r3=s.r3.mean(), r6=s.r6.mean(), r12=s.r12.mean(), r12_med=s.r12.median(), up12=(s.r12.dropna() > 0).mean() if s.r12.notna().any() else np.nan, n12=int(s.r12.notna().sum()),
                dd12_med=s.dd12.median(), dd12_worst=s.dd12.min())

rows, reg = [], []
for mkt, px in PX.items():
    f = fwd(px); f = f[f.index >= pd.Period('1991-01', 'M')]
    rows.append(summ(f, pd.Series(True, index=f.index), 'ALL', mkt))
    rows.append(summ(f, vmax >= 30, 'VIXmax>=30', mkt)); rows.append(summ(f, vavg <= 14, 'VIXavg<=14', mkt))
    for ind in ('PER', 'PBR'):
        p = O / f'panel_{mkt}_{ind}.csv'
        if not p.exists(): continue
        z = pd.read_csv(p, index_col=0)['z']; z.index = pd.PeriodIndex(z.index, freq='M')
        rows.append(summ(f, (z <= -1) & (vmax.reindex(z.index) >= 30), f'{ind}z<=-1 & VIXmax>=30', mkt))
        rows.append(summ(f, (z <= -1), f'{ind}z<=-1 (단독)', mkt))
        rows.append(summ(f, (z >= 1) & (vavg.reindex(z.index) <= 14), f'{ind}z>=1 & VIXavg<=14', mkt))
        rows.append(summ(f, (z >= 1), f'{ind}z>=1 (단독)', mkt))
        rows.append(summ(f, (z >= 1) & (vmax.reindex(z.index) >= 30), f'{ind}z>=1 & VIXmax>=30', mkt))
    # 금리
    for lo, hi in [(-1, 1), (1, 3), (3, 5), (5, 99)]:
        rows.append(summ(f, (ff >= lo) & (ff < hi), f'FF {max(lo,0)}~{hi if hi<99 else ""}%', mkt))
    rows.append(summ(f, ff_d12 >= 1, 'FF 12m Δ>=+1%p (인상기)', mkt))
    rows.append(summ(f, ff_d12 <= -1, 'FF 12m Δ<=-1%p (인하기)', mkt))
    rows.append(summ(f, ff_gap >= 1, 'FF-10y평균>=+1%p', mkt))
    rows.append(summ(f, ff_gap <= -1, 'FF-10y평균<=-1%p', mkt))
    y = np.log1p(f.r12)
    for nm, x in [('FF level', ff), ('FF Δ12m', ff_d12), ('FF gap10y', ff_gap), ('VIX avg', vavg)]:
        b, t, n = core.nw_t(y.values, x.reindex(f.index).values.astype(float), 12); reg.append(dict(market=mkt, x=nm, beta=b, nw_t=t, n=n))

pd.set_option('display.width', 250)
R = pd.DataFrame(rows); R.to_csv(O / 'overlay.csv', index=False); G = pd.DataFrame(reg); G.to_csv(O / 'overlay_reg.csv', index=False)
print(R.round(3).to_string()); print(G.round(3).to_string())
print('now: VIXmax', vmax.iloc[-1].round(1), 'VIXavg', vavg.iloc[-1].round(1), '| FF', ff.iloc[-1].round(2), 'Δ12m', ff_d12.iloc[-1].round(2), 'gap', ff_gap.iloc[-1].round(2))

# ---- F&G (2011~, whit3rabbit/fear-greed-data 아카이브) ----
fg = pd.read_csv(core.D / 'ext_fg' / 'fear-greed.csv', parse_dates=['Date']).set_index('Date')['Fear Greed'].dropna()
FP = fg.index.to_period('M'); fmin = fg.groupby(FP).min(); favg = fg.groupby(FP).mean()
fr = []
for mkt, px in PX.items():
    f = fwd(px); f = f[f.index >= pd.Period('2011-01', 'M')]
    fr.append(summ(f, pd.Series(True, index=f.index), 'ALL(2011~)', mkt))
    fr.append(summ(f, fmin <= 25, 'FGmin<=25', mkt)); fr.append(summ(f, favg >= 75, 'FGavg>=75', mkt))
    fr.append(summ(f, (fmin <= 25) & (vmax >= 30), 'FGmin<=25 & VIXmax>=30', mkt))
    for ind in ('PER', 'PBR'):
        p = O / f'panel_{mkt}_{ind}.csv'
        if not p.exists(): continue
        z = pd.read_csv(p, index_col=0)['z']; z.index = pd.PeriodIndex(z.index, freq='M')
        fr.append(summ(f, (z <= -1) & (fmin.reindex(z.index) <= 25), f'{ind}z<=-1 & FGmin<=25', mkt))
        fr.append(summ(f, (z >= 1) & (favg.reindex(z.index) >= 75), f'{ind}z>=1 & FGavg>=75', mkt))
F = pd.DataFrame(fr); F.to_csv(O / 'overlay_fg.csv', index=False); print(F.round(3).to_string())
print('now FG min', fmin.iloc[-1].round(1), 'avg', favg.iloc[-1].round(1), '| FG avg>=75 months:', [str(m) for m in favg[favg>=75].index][-12:])
