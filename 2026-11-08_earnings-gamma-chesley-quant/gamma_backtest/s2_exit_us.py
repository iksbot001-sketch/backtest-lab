"""미국 S2 '꺾일 때까지 보유' 청산 규칙(롱온리, 비용 반영, 거래 단위). 입력 events_us_s2_{mode}.parquet.
진입: 신호 상위 10분위(직전 분기 컷). 청산: F63/F126/F252 고정, A = 다음 발표에서 신호 ≤0, B = 신호 2회 연속 하락. 최대 252거래일.
비용: 편도 0.015% + $0.01. 초과수익 = 종목 - SPY. t = 진입 분기 군집. 사용: python s2_exit_us.py [safe|fast] [EA|ORA|REV]"""
import sys, glob, json, time
import numpy as np, pandas as pd
from pathlib import Path
S = Path.home() / 'agent-fund-data'
mode = sys.argv[1] if len(sys.argv) > 1 else 'safe'; sig = sys.argv[2] if len(sys.argv) > 2 else 'EA'
ev = pd.read_parquet(S / f'events_us_s2_{mode}.parquet')
ev = ev[np.isfinite(ev[sig])].sort_values(['tk', 'T']).reset_index(drop=True)
cut = {tq: np.nanpercentile(g[sig], 90) for tq, g in ev.groupby('tq') if len(g) >= 50}
ev['top'] = [(t - 1) in cut and v > cut[t - 1] for t, v in zip(ev.tq, ev[sig])]
px = {}
for f in glob.glob(str(S / 'prices/us/*.parquet')):
    d = pd.read_parquet(f); d = d[d.close > 0]
    if len(d): px[Path(f).stem] = d.set_index('date').close
px = pd.DataFrame(px).sort_index(); px.index = pd.to_datetime(px.index); px = px[px.index >= '2016-06-01']
last = px.apply(lambda c: c.last_valid_index()); px = px.ffill()
for c, d in last.items():
    if d is not None and not pd.isna(d): px.loc[px.index > d, c] = np.nan
spy = px['SPY'].values; N = len(px)
def lastok(s, i0, i1):
    seg = s[i0:i1 + 1]; ok = np.where(np.isfinite(seg))[0]; return i0 + ok[-1] if len(ok) else i0
res = []
for rule in ['F63', 'F126', 'F252', 'A', 'B']:
    tr = []
    for tk, g in ev.groupby('tk'):
        s = px[tk].values; g = g.reset_index(drop=True); k = 0
        while k < len(g):
            if not g.top[k]: k += 1; continue
            i0 = int(g.i0[k]); p0 = s[i0] if i0 < N else np.nan
            if not np.isfinite(p0) or p0 < 5: k += 1; continue
            i1 = min(i0 + 252, N - 1); kk = k + 1
            if rule.startswith('F'): i1 = min(i0 + int(rule[1:]), N - 1)
            else:
                prev, drops = g[sig][k], 0
                while kk < len(g) and g.i0[kk] <= i1:
                    v = g[sig][kk]
                    drops = drops + 1 if v < prev else 0; prev = v
                    if (rule == 'A' and v <= 0) or (rule == 'B' and drops >= 2): i1 = int(g.i0[kk]); break
                    kk += 1
            i1 = lastok(s, i0, i1); p1 = s[i1]
            cost = 2 * 0.00015 + 0.01 / p0 + 0.01 / p1
            tr.append(dict(tk=tk, tq=g.tq[k], d=i1 - i0, ex=p1 / p0 - 1 - (spy[i1] / spy[i0] - 1) - cost, yr=int(g.tq[k] // 4)))
            while kk < len(g) and g.i0[kk] <= i1: kk += 1   # 보유 중 신호는 건너뜀
            k = kk
    t = pd.DataFrame(tr); q = t.groupby('tq').ex.mean()
    tt = lambda s: s.mean() / s.std(ddof=1) * np.sqrt(len(s)) if len(s) > 2 else np.nan
    qi, qo = q[q.index // 4 <= 2021], q[q.index // 4 >= 2022]
    res.append(dict(rule=rule, n=len(t), hold=round(t.d.mean()), ex_net=round(t.ex.mean() * 100, 2), t=round(tt(q), 2),
                    IS=round(qi.mean() * 100, 2), t_IS=round(tt(qi), 2), OOS=round(qo.mean() * 100, 2), t_OOS=round(tt(qo), 2),
                    win=round((t.ex > 0).mean() * 100)))
r = pd.DataFrame(res); print(f'== {sig} / {mode} (거래당 비용 후 SPY 대비 초과수익 %)'); print(r.to_string(index=False))
r.to_csv(S / f'exit_results_us_s2_{sig}_{mode}.csv', index=False)
with open(Path.home() / 'agent-fund' / 'data' / 'trial_registry.jsonl', 'a') as f:
    for x in res:
        f.write(json.dumps({'ts': time.strftime('%Y-%m-%dT%H:%M:%S'), 'study': 'gamma_backtest', 'trial': f'S2_us_{sig}_{mode}_{x["rule"]}', **x}, ensure_ascii=False) + '\n')
