"""기존 한국 가격 DB(네이버 출처)와 EODHD 수정주가 대조. 출력 ~/agent-fund-data/prices/meta/eodhd_validation.parquet
판정(종목별): OK = 겹치는 날 95% 이상이 종가 0.5% 이내 & EODHD 시작일이 기존보다 20거래일 이상 늦지 않음 / SHORT = 일치하나 EODHD 이력이 짧음 / DIFF = 불일치 / NONE = EODHD 없음."""
import glob, sys
import numpy as np, pandas as pd
from pathlib import Path
sys.path.insert(0, '~/agent-fund/lib')
import eodhd
D = Path.home() / 'agent-fund-data/prices'; E = D / 'eodhd'
rows = []
for sub in ('kr', 'kr_delisted'):
    for f in glob.glob(str(D / sub / '*.parquet')):
        code = Path(f).stem; a = pd.read_parquet(f, columns=['date', 'close']); a['date'] = pd.to_datetime(a.date)
        ef = next((E / f'{code}.{x}.parquet' for x in ('KO', 'KQ') if (E / f'{code}.{x}.parquet').exists()), None)
        r = dict(code=code, src=sub, n_old=len(a), first_old=a.date.min(), last_old=a.date.max())
        if ef is None: rows.append({**r, 'verdict': 'NONE'}); continue
        b = eodhd.adjusted(pd.read_parquet(ef))[['date', 'close']]
        m = a.merge(b, on='date', suffixes=('_o', '_e'))
        rel = (m.close_e / m.close_o - 1).abs()
        r.update(ex=ef.stem.split('.')[1], n_new=len(b), first_new=b.date.min(), last_new=b.date.max(), n_overlap=len(m),
                 within=(rel < 0.005).mean() if len(m) else np.nan, med_diff=rel.median() if len(m) else np.nan)
        late = len(a[(a.date < r['first_new'])])
        r['verdict'] = 'DIFF' if not len(m) or r['within'] < 0.95 else ('SHORT' if late > 20 else 'OK')
        r['days_missing_early'] = late
        rows.append(r)
V = pd.DataFrame(rows); V.to_parquet(D / 'meta/eodhd_validation.parquet', index=False)
print(V.groupby(['src', 'verdict']).size().unstack(fill_value=0))
print('일치율 중앙값', V.within.median().round(4), '| 중앙 상대오차', V.med_diff.median())
print(V[V.verdict == 'SHORT'][['code', 'first_old', 'first_new', 'days_missing_early']].head(8).to_string())
print(V[V.verdict == 'DIFF'][['code', 'n_overlap', 'within', 'med_diff']].head(8).to_string())
