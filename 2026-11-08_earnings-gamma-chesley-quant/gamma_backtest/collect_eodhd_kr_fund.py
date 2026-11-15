"""EODHD 한국 재무(fundamentals, 10콜/종목): 전망 추세 데이터가 있는 KO·KQ 종목. 하루 한도 보호(92,000)."""
import gzip, json, glob, time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import eod
D = Path.home() / 'agent-fund-data/eodhd'
LOG = open(D / 'collect_kr_fund.log', 'a', buffering=1)
log = lambda *a: LOG.write(time.strftime('%H:%M:%S ') + ' '.join(map(str, a)) + '\n')
codes = [Path(f).name[:-8] for f in sorted(glob.glob(str(D / 'trends/*.K[OQ].json.gz'))) if json.load(gzip.open(f, 'rt'))]
codes = sorted(codes, key=lambda c: (not c.endswith('KO'), c))   # KOSPI 먼저
todo = [c for c in codes if not (D / 'fund' / f'{c}.json.gz').exists()]
log('todo', len(todo))
def run(c):
    time.sleep(0.1)
    try: d = eod.get(f'fundamentals/{c}')
    except Exception as e: log('ERR', c, str(e)[:80]); return
    with gzip.open(D / 'fund' / f'{c}.json.gz', 'wt') as f: json.dump(d, f)
with ThreadPoolExecutor(8) as ex:
    for i, _ in enumerate(ex.map(run, todo)):
        if i % 200 == 0:
            u = eod.usage(); log(i, '/', len(todo), u)
            if (u.get('apiRequests') or 0) > 92000: log('BUDGET STOP'); break
log('DONE', eod.usage())
