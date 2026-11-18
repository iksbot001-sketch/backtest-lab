"""PREREG.md 정의 그대로의 핵심 계산 (Claude). 월간 기준.
신호 = 월말 t 값 → 체결 = t+1월 첫 거래일 종가. 수익률 = 가격지수(배당 제외)."""
import json, sys
from pathlib import Path
import numpy as np, pandas as pd

R = Path(__file__).resolve().parents[1]; D = R / 'data'; O = R / 'out'; O.mkdir(exist_ok=True)
DELAY = int(sys.argv[1]) if len(sys.argv) > 1 else 0   # +n개월 지연 민감도

def yh(name):
    j = json.loads((D / f'yh_{name}.json').read_text())['chart']['result'][0]
    s = pd.Series(j['indicators']['quote'][0]['close'], index=pd.to_datetime(j['timestamp'], unit='s').normalize())
    return s.dropna().groupby(level=0).last()

def first_td_close(px):
    """월별 첫 거래일 종가 (index = 그 달 월초 Period)."""
    return px.groupby(px.index.to_period('M')).first()

def month_end(s):
    return s.groupby(s.index.to_period('M')).last()

# ---------- 데이터 ----------
def load_val():
    out = {}
    k = pd.read_csv(D / 'kospi_per_pbr_krx.csv', parse_dates=['date'], na_values=['-', '']).set_index('date')
    ext = D / 'agy' / 'kospi_per_pbr_ext.csv'
    if ext.exists():
        e = pd.read_csv(ext, parse_dates=['date']).set_index('date'); k = pd.concat([k, e[~e.index.isin(k.index)]]).sort_index()
    out['KOSPI'] = dict(px=yh('KS11'), PER=month_end(k['per'].dropna()), PBR=month_end(k['pbr'].dropna()))
    pe = pd.read_csv(D / 'spx_pe_m.csv', parse_dates=['date']).set_index('date')['pe']
    pe.index = pe.index.to_period('M'); pe = pe.groupby(level=0).last().shift(1, freq='M')           # 1개월 지연
    pb = pd.read_csv(D / 'spx_pbr_q.csv', parse_dates=['date']).set_index('date')['pbr']
    pb.index = pb.index.to_period('M'); pb = pb.groupby(level=0).last()
    pb = pb.shift(3, freq='M')                                                 # 분기말 +3개월 지연
    pbm = pb.reindex(pd.period_range(pb.index.min(), pe.index.max(), freq='M')).ffill()
    out['SP500'] = dict(px=yh('GSPC'), PER=pe, PBR=pbm)
    kq = D / 'agy' / 'kosdaq_per_pbr.csv'
    if kq.exists():
        q = pd.read_csv(kq, parse_dates=['date']).set_index('date')
        qper = pd.to_numeric(q['per'], errors='coerce').dropna(); qper = qper[qper.index >= '2010-08-01']  # 이전은 결측·수백배 왜곡(합산이익≈0)
        out['KOSDAQ'] = dict(px=yh('KQ11'), PER=month_end(qper),
                             PBR=month_end(pd.to_numeric(q['pbr'], errors='coerce').dropna()))
    nd = D / 'agy' / 'ndx_valuation.csv'
    if nd.exists():
        q = pd.read_csv(nd, parse_dates=['date']).set_index('date')
        d = dict(px=yh('NDX'))
        for c, n in [('per_ttm', 'PER'), ('pbr', 'PBR'), ('per_fwd', 'FPER')]:
            if c in q and q[c].notna().sum() > 60: d[n] = month_end(pd.to_numeric(q[c], errors='coerce').dropna())
        out['NASDAQ100'] = d
    for m in ['SP500', 'KOSPI']:
        f = D / 'agy' / f'fwd_pe_{m.lower()}.csv'
        if f.exists():
            q = pd.read_csv(f, parse_dates=['date']).set_index('date')['fwd_pe']; out[m]['FPER'] = month_end(q.dropna())
    return out

def rolling_z(v, win=120, minp=96):
    mu = v.rolling(win, min_periods=minp).mean(); sd = v.rolling(win, min_periods=minp).std()
    return (v - mu) / sd

ZONES = [(-np.inf, -2, 'Z<=-2'), (-2, -1, '-2<Z<=-1'), (-1, 1, 'neutral'), (1, 2, '1<=Z<2'), (2, np.inf, 'Z>=2')]
W = {'Z<=-2': 1.0, '-2<Z<=-1': .8, 'neutral': .6, '1<=Z<2': .4, 'Z>=2': .2}
def zone(z):
    if pd.isna(z): return np.nan
    if z <= -2: return 'Z<=-2'
    if z <= -1: return '-2<Z<=-1'
    if z < 1: return 'neutral'
    if z < 2: return '1<=Z<2'
    return 'Z>=2'

def nw_t(y, x, lag):
    m = ~(np.isnan(y) | np.isnan(x)); y, x = y[m], x[m]; n = len(y)
    X = np.column_stack([np.ones(n), x]); b = np.linalg.lstsq(X, y, rcond=None)[0]; u = y - X @ b
    XtXi = np.linalg.inv(X.T @ X); S = (X * u[:, None]).T @ (X * u[:, None])
    for L in range(1, lag + 1):
        w = 1 - L / (lag + 1); G = (X[L:] * u[L:, None]).T @ (X[:-L] * u[:-L, None]); S += w * (G + G.T)
    V = XtXi @ S @ XtXi; return b[1], b[1] / np.sqrt(V[1, 1]), n

def episodes(mask, gap=6):
    idx = np.flatnonzero(mask.values); eps = []; last = -99
    for i in idx:
        if i - last > gap: eps.append(mask.index[i])
        last = i
    return eps

def sharpe(r): r = r.dropna(); return r.mean() / r.std() * np.sqrt(12) if r.std() > 0 else np.nan
def mdd(r): c = (1 + r.fillna(0)).cumprod(); return (c / c.cummax() - 1).min()
def cagr(r): r = r.dropna(); return (1 + r).prod() ** (12 / len(r)) - 1

def analyze(mkt, px, ind, v):
    ent = first_td_close(px)                                       # 체결가: 월 첫 거래일 종가
    z = rolling_z(v).shift(DELAY, freq='M')
    # 신호월 t → 체결 t+1. fwd h개월 = ent[t+1+h]/ent[t+1]-1
    e1 = ent.shift(-1); res = pd.DataFrame({'v': v.shift(DELAY, freq='M'), 'z': z}).dropna(subset=['z'])
    res = res[res.index.isin(ent.index)]
    for h in (3, 6, 12):
        res[f'r{h}'] = (ent.shift(-1 - h) / e1).reindex(res.index) - 1
    # 12개월 내 최대 추가하락 (일간 종가)
    dd = []
    for t in res.index:
        s = px[(px.index >= (t + 1).start_time) & (px.index < (t + 13).start_time)]
        dd.append((s / s.iloc[0]).min() - 1 if len(s) > 200 else np.nan)
    res['dd12'] = dd; res['zone'] = res['z'].map(zone)
    b, t, n = nw_t(np.log1p(res['r12'].values), res['z'].values, 12)
    rv = res[res.r12.notna()]; half = rv.index[len(rv) // 2]                # 확정 12개월 수익률 기준 절반(레드팀 2·3차)
    b2, t2, _ = nw_t(np.log1p(rv.loc[half:, 'r12'].values), rv.loc[half:, 'z'].values, 12)
    b1, t1, _ = nw_t(np.log1p(rv.loc[:half, 'r12'].values)[:-1], rv.loc[:half, 'z'].values[:-1], 12)
    zt = []
    for _, _, zn in ZONES:
        s = res[res.zone == zn]
        mask = (res.zone == zn)
        zt.append(dict(market=mkt, ind=ind, zone=zn, months=len(s), episodes=len(episodes(mask)),
                       r3=s.r3.mean(), r6=s.r6.mean(), r12=s.r12.mean(), r12_med=s.r12.median(),
                       up12=(s.r12.dropna() > 0).mean() if s.r12.notna().any() else np.nan, dd12_med=s.dd12.median(), dd12_worst=s.dd12.min()))
    zt.append(dict(market=mkt, ind=ind, zone='ALL', months=len(res), episodes=np.nan, r3=res.r3.mean(), r6=res.r6.mean(),
                   r12=res.r12.mean(), r12_med=res.r12.median(), up12=(res.r12.dropna() > 0).mean(), dd12_med=res.dd12.median(), dd12_worst=res.dd12.min()))
    # 비중 전략: 월 t 신호 → t+1월 첫날~t+2월 첫날 보유
    mret = (ent.shift(-1) / ent - 1)                               # 기간 [t, t+1) 수익률(월초 기준)
    w = res['zone'].map(W); w.index = w.index + 1                  # t+1 월초부터 적용
    rr = mret.reindex(w.index)
    cost = w.diff().abs().fillna(0) * 0.0005
    strat = (w * rr - cost).dropna(); bh = rr.reindex(strat.index); c60 = (0.6 * bh)
    # 순환 이동 플라시보
    wv = w.reindex(strat.index).values; rv = bh.values; N = len(wv); ps = []
    for k in range(12, N - 12):
        ws = np.roll(wv, k); s = ws * rv - np.abs(np.diff(ws, prepend=ws[0])) * .0005; ps.append(s.mean() / s.std() * np.sqrt(12))
    sS = sharpe(strat); pct = (np.array(ps) < sS).mean() if ps else np.nan
    st = dict(market=mkt, ind=ind, start=str(strat.index[0]), end=str(strat.index[-1]), n_months=len(strat),
              nw_beta=b, nw_t=t, n=n, t_first_half=t1, t_second_half=t2, half=str(half),
              strat_cagr=cagr(strat), strat_sharpe=sS, strat_mdd=mdd(strat), avg_w=w.reindex(strat.index).mean(),
              c60_cagr=cagr(c60), c60_sharpe=sharpe(c60), c60_mdd=mdd(c60), bh_cagr=cagr(bh), bh_sharpe=sharpe(bh), bh_mdd=mdd(bh),
              placebo_pct=pct, n_placebo=len(ps),
              ep_hot=len(episodes(res.z >= 1)), ep_cold=len(episodes(res.z <= -1)),
              ep_hot2=len(episodes(res.z >= 2)), ep_cold2=len(episodes(res.z <= -2)),
              z_now=res.z.iloc[-1], v_now=res.v.iloc[-1], now=str(res.index[-1]))
    return res, zt, st

def main():
    V = load_val(); rows, stats, panels = [], [], {}
    for mkt, d in V.items():
        for ind in ('PER', 'PBR', 'FPER'):
            if ind not in d: continue
            v = d[ind]; v = v[v > 0]
            res, zt, st = analyze(mkt, d['px'], ind, v); rows += zt; stats.append(st); panels[f'{mkt}_{ind}'] = res
            res.to_csv(O / f'panel_{mkt}_{ind}{"_d%d" % DELAY if DELAY else ""}.csv')
    sfx = f'_d{DELAY}' if DELAY else ''
    pd.DataFrame(rows).to_csv(O / f'zones{sfx}.csv', index=False); pd.DataFrame(stats).to_csv(O / f'stats{sfx}.csv', index=False)
    pd.set_option('display.width', 250); pd.set_option('display.max_columns', 40)
    print(pd.DataFrame(stats).round(3).T.to_string())
    print(pd.DataFrame(rows).round(3).to_string())

if __name__ == '__main__':
    main()
