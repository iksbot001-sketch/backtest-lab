"""EODHD 대량 수집(재개 가능). 단계: 심볼 목록 → S&P 500 지수 구성 이력 → U1(2015년 이후 S&P 500 편입 종목) 전망 추세·실적 발표·일별 주가·재무
→ U2(그 외 미국 보통주, 상장·상폐) 전망 추세·실적 발표·일별 주가. 하루 호출 한도(10만) 보호: 사용량 92,000 넘으면 중단.
저장: ~/agent-fund-data/eodhd/{trends,earnings,eod,fund}/<CODE>.json.gz (빈 응답도 저장해 재요청 방지). 키는 출력하지 않는다."""
import gzip, json, time, threading, sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import pandas as pd
import eod

D = Path.home() / 'agent-fund-data/eodhd'
for sub in ('trends', 'earnings', 'eod', 'fund', 'meta'):
    (D / sub).mkdir(parents=True, exist_ok=True)
LOG = open(D / 'collect.log', 'a', buffering=1)
BUDGET = 92000
lock = threading.Lock(); last = [0.0]


def log(*a):
    LOG.write(time.strftime('%H:%M:%S ') + ' '.join(map(str, a)) + '\n')


def throttle(rate=14.0):
    with lock:
        w = last[0] + 1 / rate - time.time()
        if w > 0: time.sleep(w)
        last[0] = time.time()


def call(path, **p):
    for k in range(4):
        throttle()
        try:
            return eod.get(path, **p)
        except Exception as e:
            msg = str(e)
            if 'HTTP 404' in msg: return None
            if 'HTTP 402' in msg or 'HTTP 403' in msg: raise
            time.sleep(2 * (k + 1))
    log('FAIL', path, p.get('symbols', '')[:60]); return None


def save(sub, code, obj):
    with gzip.open(D / sub / f'{code}.json.gz', 'wt') as f: json.dump(obj, f)


def done(sub, code):
    return (D / sub / f'{code}.json.gz').exists()


def over_budget():
    u = eod.usage(); return (u.get('apiRequests') or 0) > BUDGET


def batch_job(sub, path, key, codes, size=20, **extra):
    todo = [c for c in codes if not done(sub, c)]
    log(sub, 'todo', len(todo), 'of', len(codes))
    chunks = [todo[i:i + size] for i in range(0, len(todo), size)]

    def run(ch):
        d = call(path, symbols=','.join(ch), **extra)
        rows = []
        if d:
            v = d.get(key) or []
            rows = [r for grp in v for r in grp] if v and isinstance(v[0], list) else v
        by = {c: [] for c in ch}
        for r in rows:
            c = r.get('code')
            if c in by: by[c].append(r)
        for c, rs in by.items(): save(sub, c, rs)
    with ThreadPoolExecutor(10) as ex:
        for i, _ in enumerate(ex.map(run, chunks)):
            if i % 50 == 0:
                log(sub, 'chunk', i, '/', len(chunks))
                if over_budget(): log('BUDGET STOP'); sys.exit(0)


def single_job(sub, codes, fn):
    try:
        fn(codes[0])
    except Exception as e:
        log(sub, 'SKIP (권한 없음)', str(e)[:80]); return
    todo = [c for c in codes if not done(sub, c)]
    log(sub, 'todo', len(todo), 'of', len(codes))

    def run(c):
        save(sub, c, fn(c))
    with ThreadPoolExecutor(12) as ex:
        for i, _ in enumerate(ex.map(run, todo)):
            if i % 200 == 0:
                log(sub, i, '/', len(todo))
                if over_budget(): log('BUDGET STOP'); sys.exit(0)


# 0. 심볼 목록·지수 구성 이력
if not (D / 'meta/us_active.parquet').exists():
    pd.DataFrame(call('exchange-symbol-list/US')).to_parquet(D / 'meta/us_active.parquet')
    pd.DataFrame(call('exchange-symbol-list/US', delisted=1)).to_parquet(D / 'meta/us_delisted.parquet')
if not done('fund', 'GSPC.INDX'):
    save('fund', 'GSPC.INDX', call('fundamentals/GSPC.INDX'))
act = pd.read_parquet(D / 'meta/us_active.parquet'); dl = pd.read_parquet(D / 'meta/us_delisted.parquet')
log('symbols active', len(act), 'delisted', len(dl), 'types', act.Type.value_counts().head(5).to_dict())

# U1: 2015년 이후 한 번이라도 S&P 500에 있었던 종목(+ 지수 구성 이력)
C = pd.read_csv(Path.home() / 'agent-fund-data/sp500_components.csv'); C['date'] = pd.to_datetime(C.date)
u1 = set()
for s in C[C.date >= '2015-01-01'].tickers: u1 |= set(s.split(','))
g = json.load(gzip.open(D / 'fund/GSPC.INDX.json.gz', 'rt')) or {}
for v in (g.get('HistoricalTickerComponents') or {}).values():
    if (v.get('EndDate') or '9999') >= '2015-01-01': u1.add(v.get('Code'))
for v in (g.get('Components') or {}).values(): u1.add(v.get('Code'))
U1 = sorted({t.replace('.', '-') + '.US' for t in u1 if t})
log('U1', len(U1))
common = lambda df: df[(df.Type == 'Common Stock') & df.Exchange.isin(['NYSE', 'NASDAQ', 'NYSE ARCA', 'NYSE MKT', 'BATS', 'AMEX'])]
U2 = sorted(set((common(act).Code + '.US').tolist() + (common(dl).Code + '.US').tolist()) - set(U1))
log('U2', len(U2))

batch_job('trends', 'calendar/trends', 'trends', U1)
batch_job('earnings', 'calendar/earnings', 'earnings', U1, **{'from': '2000-01-01', 'to': '2027-12-31'})
single_job('eod', U1 + ['SPY.US', 'RSP.US', 'GSPC.INDX'], lambda c: call(f'eod/{c}', **{'from': '1995-01-01'}))
single_job('fund', U1, lambda c: call(f'fundamentals/{c}'))
batch_job('trends', 'calendar/trends', 'trends', U2)
batch_job('earnings', 'calendar/earnings', 'earnings', U2, **{'from': '2000-01-01', 'to': '2027-12-31'})
single_job('eod', U2, lambda c: call(f'eod/{c}', **{'from': '1995-01-01'}))
log('ALL DONE', eod.usage())
