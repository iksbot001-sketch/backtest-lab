"""거래 수익 분포 분석: 표본 수·모양(정규성)·꼬리 종목의 특징·무작위 대조군. 출력 ~/agent-fund-data/refine/dist_*.csv, dist.json"""
import json, warnings
import numpy as np, pandas as pd
from scipy import stats
from pathlib import Path
from pxclean import clean
warnings.filterwarnings('ignore')
S = Path.home() / 'agent-fund-data'; O = S / 'refine'
sets = {'KR 실현 감마': None, 'S&P 실현 감마': 'tr_sp_acc0_V0', '중소형 실현 감마': 'tr_sm_acc0_V0', '중소형 서프라이즈 예측': 'tr_sm_p_ridge_V0'}
out = {}; prof = []
for name, f in sets.items():
    if f is None:
        t = pd.read_parquet(S / 'trades_a_op_A.parquet'); t['lr'] = np.log((1 + t.net) / (1 + t.mkt))
    else:
        t = pd.read_parquet(O / f'{f}.parquet'); t['lr'] = np.log(np.clip(1 + t.rs - t.cost, 1e-3, None) / (1 + t.rm))
    x = t.ex.values; n = len(x); srt = np.sort(x)[::-1]; tot = x.sum()
    jb = stats.jarque_bera(x); jbl = stats.jarque_bera(t.lr)
    df_, loc_, sc_ = stats.t.fit(x)
    q = np.percentile(x, [1, 5, 10, 25, 50, 75, 90, 95, 99])
    sd = x.std(ddof=1); nrm = {k: float(np.mean(np.abs(x - x.mean()) > k * sd)) for k in (2, 3)}
    r = dict(n=n, mean=x.mean(), median=np.median(x), sd=sd, skew=stats.skew(x), exkurt=stats.kurtosis(x), jb_p=jb.pvalue,
             lr_skew=stats.skew(t.lr), lr_exkurt=stats.kurtosis(t.lr), lr_jb_p=jbl.pvalue, t_df=df_,
             q=dict(zip(['p1', 'p5', 'p10', 'p25', 'p50', 'p75', 'p90', 'p95', 'p99'], q.tolist())),
             beyond2sd=nrm[2], beyond3sd=nrm[3], win=float((x > 0).mean()),
             top10_share=srt[:10].sum() / tot if tot > 0 else None, top1pct_share=srt[:max(1, n // 100)].sum() / tot if tot > 0 else None,
             mean_ex_top10=srt[10:].mean(), mean_ex_top1pct=srt[max(1, n // 100):].mean(),
             avg_win=x[x > 0].mean(), avg_loss=x[x <= 0].mean())
    if 'vol63' in t:
        z = t.ex / (t.vol63.clip(lower=0.005) * np.sqrt(t.d.clip(lower=1))); z = z[np.isfinite(z)]
        r.update(z_skew=stats.skew(z), z_exkurt=stats.kurtosis(z))
        lo, hi = t.ex.quantile(0.1), t.ex.quantile(0.9)
        t['grp'] = np.where(t.ex <= lo, '좌측 10%', np.where(t.ex >= hi, '우측 10%', '가운데 80%'))
        for g, s in t.groupby('grp'):
            prof.append(dict(set=name, grp=g, n=len(s), ex_med=s.ex.median(), px=s.px.median(), dvol_m=s.dvol.median() / 1e6 if s.dvol.notna().any() else np.nan,
                             vol_ann=s.vol63.median() * np.sqrt(252), mom=s.mom.median(), ear=s.ear.median(), gR0=s.gR0.median(), acc0=s.acc0.median(),
                             sur0=s.sur0.median(), gvol8=s.gvol8.median(), n_an=s.n_an.median(), hold=s.d.median(),
                             delist=(s.why == 'delist').mean(), exitA=(s.why == 'A').mean(), maxhold=(s.why == 'max').mean(), liqH=(s.liq == 'H').mean() if 'liq' in s else np.nan))
    out[name] = r
    print(name, {k: (round(v, 3) if isinstance(v, float) else v) for k, v in r.items() if k != 'q'}); print('  q', [round(v, 3) for v in q])
pd.DataFrame(prof).to_csv(O / 'dist_profile.csv', index=False)
print(pd.DataFrame(prof).round(3).to_string(index=False))

# 무작위 대조군: 중소형 서프라이즈 예측 거래와 같은 분기·같은 보유일로, 같은 패널에서 아무 종목이나 산 경우
T = pd.read_parquet(S / 'ml_pred_M1fast_SURP_sm.parquet')
mk = pd.read_parquet(S / 'prices/eodhd/IWM.US.parquet'); mk['date'] = pd.to_datetime(mk.date); mk = mk.set_index('date').adjusted_close
cal = mk.index[mk.index >= '2005-01-01']; M = mk.reindex(cal).ffill().values
tr = pd.read_parquet(O / 'tr_sm_p_ridge_V0.parquet'); rng = np.random.default_rng(7)
need = T[T.tq.isin(tr.tq.unique())]; cache = {}
def px(tk):
    if tk not in cache:
        d = pd.read_parquet(S / f'prices/eodhd/{tk}.US.parquet'); d['date'] = pd.to_datetime(d.date); s = clean(d.set_index('date').adjusted_close)[0].reindex(cal)
        lv = s.last_valid_index(); s = s.ffill()
        if lv is not None: s[s.index > lv] = np.nan
        cache[tk] = s.values
    return cache[tk]
rnd = []
by = {tq: g for tq, g in need.groupby('tq')}
for r in tr.itertuples():
    g = by[r.tq]; pick = g.iloc[rng.integers(0, len(g), 5)]
    for p in pick.itertuples():
        s = px(p.tk); i0 = int(p.i_fast)
        if i0 >= len(s) or not np.isfinite(s[i0]) or s[i0] < 5: continue
        i1 = min(i0 + r.d, len(s) - 1); seg = s[i0:i1 + 1]; ok = np.where(np.isfinite(seg))[0]; i1 = i0 + ok[-1]
        c = 2 * (0.001 if p.liq == 'H' else 0.003)
        rnd.append(s[i1] / s[i0] - 1 - (M[i1] / M[i0] - 1) - c)
rnd = np.array(rnd); srt = np.sort(rnd)[::-1]
out['무작위 대조군'] = dict(n=len(rnd), mean=rnd.mean(), median=np.median(rnd), sd=rnd.std(), skew=stats.skew(rnd), exkurt=stats.kurtosis(rnd),
                        q=dict(zip(['p1', 'p5', 'p10', 'p25', 'p50', 'p75', 'p90', 'p95', 'p99'], np.percentile(rnd, [1, 5, 10, 25, 50, 75, 90, 95, 99]).tolist())),
                        win=float((rnd > 0).mean()), top1pct_share=srt[:len(rnd) // 100].sum() / rnd.sum() if rnd.sum() > 0 else None)
print('무작위', {k: (round(v, 3) if isinstance(v, float) else v) for k, v in out['무작위 대조군'].items() if k != 'q'}, [round(v, 3) for v in out['무작위 대조군']['q'].values()])
np.save(O / 'dist_random.npy', rnd)
json.dump(out, open(O / 'dist.json', 'w'), ensure_ascii=False, indent=1, default=float)
