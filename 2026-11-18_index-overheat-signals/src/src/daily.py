"""PREREG 9절 — 일간·단기 검증. 사용: python src/daily.py"""
import sys
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).parent)); import core
O = core.O; D = core.D; RNG = np.random.default_rng(20261118)
H = (5, 20, 60); GAP = 60; NBOOT = 10000; W = core.W

def zroll(s): return (s - s.rolling(2520, min_periods=2000).mean()) / s.rolling(2520, min_periods=2000).std()

def approx_daily_pbr(me_close, me_pbr, px):
    """직전 월말 PBR/종가 비율 × 당일 종가 (미래 정보 없음)."""
    ratio = (me_pbr / me_close).dropna(); ratio.index = ratio.index.to_period('M')
    pm = px.index.to_period('M') - 1
    return pd.Series(ratio.reindex(pm).values * px.values, index=px.index).dropna()

def load():
    out = {}
    for mkt, tk in [('SP500', 'GSPC'), ('NASDAQ100', 'NDX'), ('SOX', 'SOX'), ('KOSPI', 'KS11'), ('KOSDAQ', 'KQ11')]:
        px = core.yh(tk); out[f'{mkt}_DISP'] = (px, px / px.rolling(200, min_periods=200).mean() - 1)
    k = pd.read_csv(D / 'kospi_per_pbr_krx.csv', parse_dates=['date'], na_values=['-', '']).set_index('date')
    kp = core.yh('KS11'); kpbr = k['pbr'].dropna(); kpbr = kpbr[kpbr > 0]
    out['KOSPI_PBR'] = (kp, kpbr.reindex(kp.index).dropna())
    # 근사 검증: KOSPI 실제 일간 PBR vs 근사
    me = k.dropna(subset=['pbr']).groupby(k.dropna(subset=['pbr']).index.to_period('M')).last()
    me.index = me.index.to_timestamp('M')
    ap = approx_daily_pbr(me['close'], me['pbr'], kp)
    j = pd.concat([kpbr, ap], axis=1, keys=['true', 'approx']).dropna()
    err = (j.approx / j.true - 1)
    zt, za = zroll(j.true), zroll(j.approx); zz = pd.concat([zt, za], axis=1).dropna()
    approx_chk = dict(n=len(j), mape=err.abs().mean(), p95=err.abs().quantile(.95), z_corr=zz.corr().iloc[0, 1], z_mae=(zz.iloc[:, 0] - zz.iloc[:, 1]).abs().mean())
    q = pd.read_csv(D / 'agy' / 'kosdaq_per_pbr.csv', parse_dates=['date']).set_index('date').dropna(subset=['pbr'])
    qp = core.yh('KQ11'); out['KOSDAQ_PBR'] = (qp, approx_daily_pbr(q['close'], q['pbr'], qp))
    return out, approx_chk

def fwd(px, h):
    p = px.values; n = len(p); r = np.full(n, np.nan)
    for i in range(n - 1 - h): r[i] = np.log(p[i + 1 + h] / p[i + 1])
    return pd.Series(r, index=px.index)

def events(z, lvl, up):
    zp = z.shift(1)
    hit = ((zp > lvl) & (z <= lvl)) if not up else ((zp < lvl) & (z >= lvl))
    idx = list(z.index[hit.fillna(False)]); ev = []; pos = {d: i for i, d in enumerate(z.index)}
    for d in idx:
        if not ev or pos[d] - pos[ev[-1]] > GAP: ev.append(d)
    return ev

def test_events(ev, r, side):
    pool = r.dropna(); ev = [e for e in ev if e in pool.index]; n = len(ev)
    if n == 0: return dict(n=0)
    obs = pool[ev].mean(); base = pool.mean()
    sims = pool.values[RNG.integers(0, len(pool), size=(NBOOT, n))].mean(1)
    p = (sims >= obs).mean() if side == 'buy' else (sims <= obs).mean()
    half = ev[n // 2:]; ex2 = pool[half].mean() - base if half else np.nan
    return dict(n=n, mean=obs, base=base, excess=obs - base, hit=(pool[ev] > 0).mean(), p=p, excess_2nd=ex2,
                first=str(ev[0].date()), last=str(ev[-1].date()))

def strategy(px, z, cost=0.0005):
    zz = z.dropna(); pxx = px.reindex(zz.index)
    w = zz.map(lambda v: W[core.zone(v)]).astype(float)
    r = pxx.pct_change().shift(-2)                    # w_t 는 t+1 종가 체결 → t+2 수익
    tc = w.diff().abs().fillna(0).shift(-1) * cost
    s = (w * r - tc).dropna(); bh = r.reindex(s.index); avgw = w.reindex(s.index).mean(); c = avgw * bh
    sh = lambda x: x.mean() / x.std() * np.sqrt(252)
    wv = w.reindex(s.index).values; rv = bh.values; ps = []
    for k in range(252, len(wv) - 252, 21):
        ws = np.roll(wv, k); x = ws * rv - np.abs(np.diff(ws, prepend=ws[0])) * cost; ps.append(x.mean() / x.std() * np.sqrt(252))
    turn = w.diff().abs().sum() / (len(w) / 252)
    return dict(sharpe=sh(s), const_sharpe=sh(c), bh_sharpe=sh(bh), cagr=(1 + s).prod() ** (252 / len(s)) - 1,
                const_cagr=(1 + c).prod() ** (252 / len(c)) - 1, avg_w=avgw, placebo=(np.array(ps) < sh(s)).mean(), turnover=turn,
                cost_yr=turn * cost, start=str(s.index[0].date()), end=str(s.index[-1].date()))

if __name__ == '__main__':
    data, chk = load(); print('KOSPI PBR 근사 검증', {k: round(v, 4) for k, v in chk.items()})
    E, S, EV = [], [], []
    for name, (px, v) in data.items():
        z = zroll(v.dropna()).dropna(); pxz = px.reindex(z.index).dropna(); z = z.reindex(pxz.index)
        R = {h: fwd(pxz, h) for h in H}
        st = strategy(pxz, z); st10 = strategy(pxz, z, 0.001); st.update(name=name, sharpe_10bp=st10['sharpe'], placebo_10bp=st10['placebo'], z_now=z.iloc[-1], z_date=str(z.index[-1].date()))
        S.append(st)
        for lvl, up, side, tier in [(-1, False, 'buy', 1), (1, True, 'sell', 1), (-2, False, 'buy', 2), (2, True, 'sell', 2)]:
            ev = events(z, lvl, up)
            for e in ev: EV.append(dict(name=name, lvl=lvl, date=str(e.date()), z=z[e], **{f'r{h}': R[h].get(e) for h in H}))
            for h in H:
                t = test_events(ev, R[h], side)
                E.append(dict(name=name, lvl=lvl, side=side, h=h, primary=(tier == 1 and h == 20), **t))
    E = pd.DataFrame(E); S = pd.DataFrame(S)
    E.to_csv(O / 'daily_events_test.csv', index=False); S.to_csv(O / 'daily_strategy.csv', index=False); pd.DataFrame(EV).to_csv(O / 'daily_events.csv', index=False)
    pd.Series(chk).to_csv(O / 'daily_pbr_approx_check.csv')
    pd.set_option('display.width', 250)
    print(E[E.primary][['name', 'side', 'n', 'mean', 'base', 'excess', 'hit', 'p', 'excess_2nd']].round(4).to_string())
    print(S[['name', 'start', 'sharpe', 'const_sharpe', 'bh_sharpe', 'cagr', 'const_cagr', 'avg_w', 'placebo', 'turnover', 'cost_yr', 'sharpe_10bp', 'z_now']].round(3).to_string())
