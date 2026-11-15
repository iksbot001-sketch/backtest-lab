"""분포 보완: 분기 묶음 부트스트랩 평균 구간, 절사평균, 보유 종목 수별 '시장을 이길 확률', 무작위 대조군과 분위수 차이."""
import json, numpy as np, pandas as pd
from pathlib import Path
O = Path.home() / 'agent-fund-data/refine'; rng = np.random.default_rng(11); out = {}
rnd = np.load(O / 'dist_random.npy')
for nm, f in [('중소형 서프라이즈 예측 V0', 'tr_sm_p_ridge_V0'), ('중소형 실현 감마 V0', 'tr_sm_acc0_V0'), ('중소형 실현 감마 정교화(V6r_noSL)', 'tr_sm_acc0_V6r_noSL'), ('S&P 실현 감마 V0', 'tr_sp_acc0_V0')]:
    t = pd.read_parquet(O / f'{f}.parquet'); x = t.ex.values; g = t.groupby('tq').ex.apply(list); qs = list(g.index)
    bs = []
    for _ in range(2000):
        pick = rng.choice(len(qs), len(qs)); v = np.concatenate([g.iloc[i] for i in pick]); bs.append(v.mean())
    lo, hi = np.percentile(bs, [2.5, 97.5]); s = np.sort(x); k = int(len(s) * 0.01)
    p = {}
    for n in (10, 30, 100, 300):
        m = np.array([rng.choice(x, n).mean() for _ in range(5000)]); p[n] = dict(beat=float((m > 0).mean()), p10=float(np.percentile(m, 10)), p50=float(np.median(m)), p90=float(np.percentile(m, 90)))
    out[nm] = dict(n=len(x), mean=x.mean(), ci=[lo, hi], trim1=s[k:-k].mean(), median=np.median(x), port=p)
    print(nm, 'n', len(x), 'mean %.2f%% CI [%.2f, %.2f] trim1 %.2f%% med %.2f%%' % (x.mean() * 100, lo * 100, hi * 100, s[k:-k].mean() * 100, np.median(x) * 100))
    for n, d in p.items(): print('   보유', n, '종목: 시장 이길 확률 %.0f%%, 10/50/90분위 %.1f / %.1f / %.1f%%' % (d['beat'] * 100, d['p10'] * 100, d['p50'] * 100, d['p90'] * 100))
x = pd.read_parquet(O / 'tr_sm_p_ridge_V0.parquet').ex.values; ps = [1, 5, 10, 25, 50, 75, 90, 95, 99]
out['vs_random'] = dict(p=ps, strat=np.percentile(x, ps).tolist(), rnd=np.percentile(rnd, ps).tolist())
print('분위수 전략 vs 무작위', [(p, round(a * 100), round(b * 100)) for p, a, b in zip(ps, out['vs_random']['strat'], out['vs_random']['rnd'])])
json.dump(out, open(O / 'dist2.json', 'w'), ensure_ascii=False, indent=1, default=float)
