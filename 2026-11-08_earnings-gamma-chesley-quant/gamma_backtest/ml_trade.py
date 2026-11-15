"""예측 모델 상위 10분위 롱온리 매매 시험(비용 반영, 거래 단위). 사용: python ml_trade.py <pred_tag> <dec_col|feature> [cost_mult]
규칙: F63·F126 고정 / N1 = 다음 실적 발표 후 진입일까지(1분기) / A = 이후 발표에서 예측이 중앙값 아래(분위 ≤5)면 청산 / B = 분위 2회 연속 하락. 최대 252거래일.
특징 이름을 주면 직전 분기 컷으로 10분위를 만들어 같은 방식으로 시험(서프라이즈 sur0, 발표 반응 ear 등 기존 이상현상 기준선)."""
import sys, json, time, glob, warnings
import numpy as np, pandas as pd
from pathlib import Path
warnings.filterwarnings('ignore')
S = Path.home() / 'agent-fund-data'
tag, dcol = sys.argv[1], sys.argv[2]; CM = float(sys.argv[3]) if len(sys.argv) > 3 else 1.0
entry = 'fast' if 'fast' in tag else 'safe'
T = pd.read_parquet(S / f'ml_pred_{tag}.parquet').sort_values(['tk', 'T']).reset_index(drop=True)
if not dcol.startswith('dec_'):
    cut = {tq: np.nanpercentile(g[dcol], np.arange(10, 100, 10)) for tq, g in T.groupby('tq') if g[dcol].notna().sum() >= 50}
    T['dec_x'] = [int(np.searchsorted(cut[t - 1], v)) + 1 if (t - 1) in cut and np.isfinite(v) else np.nan for t, v in zip(T.tq, T[dcol])]
    dname = dcol; dcol = 'dec_x'
else: dname = dcol
SM = tag.endswith('_sm')
px = {}
if SM:   # 중소형주: EODHD 수정주가, 시장 = IWM, 패널과 같은 거래일 달력
    mk = pd.read_parquet(S / 'prices/eodhd/IWM.US.parquet'); mk['date'] = pd.to_datetime(mk.date); mk = mk.set_index('date').adjusted_close
    cal = mk.index[mk.index >= '2005-01-01']
    for tk in T.tk.unique():
        d = pd.read_parquet(S / f'prices/eodhd/{tk}.US.parquet'); d['date'] = pd.to_datetime(d.date)
        px[tk] = d.set_index('date').adjusted_close
    px = pd.DataFrame(px).reindex(cal); px['MKT'] = mk.reindex(cal)
else:
    for f in glob.glob(str(S / 'prices/us/*.parquet')):
        d = pd.read_parquet(f); d = d[d.close > 0]
        if len(d): px[Path(f).stem] = d.set_index('date').close
    px = pd.DataFrame(px).sort_index(); px.index = pd.to_datetime(px.index); px['MKT'] = px['SPY']
last = px.apply(lambda c: c.last_valid_index()); px = px.ffill()
for c, d in last.items():
    if d is not None and not pd.isna(d): px.loc[px.index > d, c] = np.nan
spy = px['MKT'].values; N = len(px); ie = f'i_{entry}'
split = 2019 if tag.startswith('M1') else 2022
tt = lambda s: s.mean() / s.std(ddof=1) * np.sqrt(len(s)) if len(s) > 2 else np.nan
res = []
for rule in ['F63', 'F126', 'N1', 'A', 'B']:
    tr = []
    for tk, g in T.groupby('tk'):
        s = px[tk].values; g = g.reset_index(drop=True); k = 0
        while k < len(g):
            if g[dcol][k] != 10: k += 1; continue
            i0 = int(g[ie][k]); p0 = s[i0] if i0 < N else np.nan
            if not np.isfinite(p0) or p0 < 5: k += 1; continue
            i1 = min(i0 + 252, N - 1); kk = k + 1
            if rule.startswith('F'): i1 = min(i0 + int(rule[1:]), N - 1)
            elif rule == 'N1': i1 = min(int(g[ie][kk]), N - 1) if kk < len(g) else min(i0 + 63, N - 1)
            else:
                prev, drops = g[dcol][k], 0
                while kk < len(g) and g[ie][kk] <= i1:
                    v = g[dcol][kk]
                    if not np.isfinite(v): kk += 1; continue
                    drops = drops + 1 if v < prev else 0; prev = v
                    if (rule == 'A' and v <= 5) or (rule == 'B' and drops >= 2): i1 = int(g[ie][kk]); break
                    kk += 1
            seg = s[i0:i1 + 1]; ok = np.where(np.isfinite(seg))[0]; i1 = i0 + ok[-1]; p1 = s[i1]
            cost = CM * (2 * (0.001 if g.liq[k] == 'H' else 0.003) if SM else 2 * 0.00015 + 0.01 / p0 + 0.01 / p1)
            tr.append(dict(tk=tk, tq=g.tq[k], d=i1 - i0, liq=g.liq[k] if 'liq' in g else '', ex=p1 / p0 - 1 - (spy[i1] / spy[i0] - 1) - cost))
            while kk < len(g) and g[ie][kk] <= i1: kk += 1
            k = kk
    t = pd.DataFrame(tr); t.to_parquet(S / f'trades_ml_{tag}_{dname}_{rule}_x{CM:g}.parquet', index=False); q = t.groupby('tq').ex.mean(); qi, qo = q[q.index // 4 < split], q[q.index // 4 >= split]
    res.append(dict(rule=rule, n=len(t), hold=round(t.d.mean()), ex=round(t.ex.mean() * 100, 2), t=round(tt(q), 2),
                    pre=round(qi.mean() * 100, 2), t_pre=round(tt(qi), 2), post=round(qo.mean() * 100, 2), t_post=round(tt(qo), 2), win=round((t.ex > 0).mean() * 100)))
r = pd.DataFrame(res)
print(f'== {tag} / {dname} / 비용 ×{CM:g}' + (' (편도 유동성 상 0.10%·하 0.30%, 시장 IWM)' if SM else '') + f' (거래당 SPY 대비 순초과 %, 이전 <{split} / 이후 ≥{split})'); print(r.to_string(index=False))
with open(Path.home() / 'agent-fund' / 'data' / 'trial_registry.jsonl', 'a') as f:
    for x in res:
        f.write(json.dumps({'ts': time.strftime('%Y-%m-%dT%H:%M:%S'), 'study': 'gamma_backtest', 'trial': f'ML_{tag}_{dname}_x{CM:g}_{x["rule"]}', **x}, ensure_ascii=False) + '\n')
