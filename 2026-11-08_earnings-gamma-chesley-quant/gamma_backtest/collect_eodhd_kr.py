"""EODHD 한국(KO=KOSPI, KQ=KOSDAQ) 전망 추세·실적 발표 수집. 상장·상폐 보통주. 저장 위치·형식은 collect_eodhd.py와 같다."""
import gzip, json, time, threading
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import pandas as pd
import eod
D = Path.home() / 'agent-fund-data/eodhd'
LOG = open(D / 'collect_kr.log', 'a', buffering=1)
log = lambda *a: LOG.write(time.strftime('%H:%M:%S ') + ' '.join(map(str, a)) + '\n')


def call(path, **p):
    for k in range(4):
        time.sleep(0.25)
        try: return eod.get(path, **p)
        except Exception as e:
            if 'HTTP 404' in str(e): return None
            if 'HTTP 40' in str(e): log('ERR', str(e)[:100]); return None
            time.sleep(2 * (k + 1))


frames = []
for ex in ('KO', 'KQ'):
    for dl in (0, 1):
        f = D / f'meta/{ex}_{"delisted" if dl else "active"}.parquet'
        if not f.exists():
            pd.DataFrame(call(f'exchange-symbol-list/{ex}', **({'delisted': 1} if dl else {})) or []).to_parquet(f)
        df = pd.read_parquet(f); df['ex'] = ex; frames.append(df)
S = pd.concat(frames)
log('KR symbols', len(S), S.Type.value_counts().to_dict() if 'Type' in S else '')
codes = sorted(set((S[S.Type == 'Common Stock'].Code + '.' + S[S.Type == 'Common Stock'].ex).tolist()))
log('KR common', len(codes))
for sub, path, key, extra in (('trends', 'calendar/trends', 'trends', {}),
                              ('earnings', 'calendar/earnings', 'earnings', {'from': '2000-01-01', 'to': '2027-12-31'})):
    todo = [c for c in codes if not (D / sub / f'{c}.json.gz').exists()]
    chunks = [todo[i:i + 20] for i in range(0, len(todo), 20)]

    def run(ch):
        d = call(path, symbols=','.join(ch), **extra); rows = []
        if d:
            v = d.get(key) or []
            rows = [r for g in v for r in g] if v and isinstance(v[0], list) else v
        by = {c: [] for c in ch}
        for r in rows:
            if r.get('code') in by: by[r['code']].append(r)
        for c, rs in by.items():
            with gzip.open(D / sub / f'{c}.json.gz', 'wt') as f: json.dump(rs, f)
    with ThreadPoolExecutor(4) as ex:
        list(ex.map(run, chunks))
    log(sub, 'done', len(todo))
log('KR DONE', eod.usage())
