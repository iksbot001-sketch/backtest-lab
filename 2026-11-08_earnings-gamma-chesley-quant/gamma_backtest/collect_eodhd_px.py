"""EODHD 일별 주가(수정주가 포함) 수집. 사용: python collect_eodhd_px.py KR|SP|US
KR = 코스피·코스닥 보통주(상장·상폐) + 지수, SP = 2008년 이후 S&P 500 편입 + SPY·RSP·지수, US = 나머지 미국 보통주.
저장 ~/agent-fund-data/prices/eodhd/<code>.parquet. 하루 한도 보호: 사용량 99,000 넘으면 중단(초기화 후 재실행하면 이어서)."""
import sys, time, json
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import pandas as pd
import eod
D = Path.home() / 'agent-fund-data'; OUT = D / 'prices/eodhd'; OUT.mkdir(parents=True, exist_ok=True)
M = D / 'eodhd/meta'; LOG = open(D / 'eodhd/collect_px.log', 'a', buffering=1)
log = lambda *a: LOG.write(time.strftime('%m-%d %H:%M:%S ') + ' '.join(map(str, a)) + '\n')
which = sys.argv[1]
if which == 'KR':
    fr = []
    for ex in ('KO', 'KQ'):
        for k in ('active', 'delisted'):
            d = pd.read_parquet(M / f'{ex}_{k}.parquet'); d = d[d.Type == 'Common Stock']; fr += (d.Code + '.' + ex).tolist()
    codes = ['KS11.INDX', 'KQ11.INDX'] + sorted(set(fr))
elif which == 'SP':
    C = pd.read_csv(D / 'sp500_components.csv'); C = C[C.date >= '2008-01-01']
    codes = ['SPY.US', 'RSP.US', 'QQQ.US', 'VOO.US', 'GSPC.INDX', 'NDX.INDX', 'SOXX.US', 'SMH.US'] + sorted({t.replace('.', '-') + '.US' for s in C.tickers for t in s.split(',')})
elif which == 'UT':
    codes = (M / 'us_trend_codes.txt').read_text().split()
else:
    act, dl = pd.read_parquet(M / 'us_active.parquet'), pd.read_parquet(M / 'us_delisted.parquet')
    cm = lambda df: df[(df.Type == 'Common Stock') & df.Exchange.isin(['NYSE', 'NASDAQ', 'NYSE ARCA', 'NYSE MKT', 'BATS', 'AMEX'])]
    codes = sorted(set((cm(act).Code + '.US').tolist() + (cm(dl).Code + '.US').tolist()))
todo = [c for c in codes if not (OUT / f'{c}.parquet').exists() and not (OUT / f'{c}.empty').exists()]
log(which, 'todo', len(todo), 'of', len(codes))
stop = [False]
def run(c):
    if stop[0]: return
    for k in range(3):
        try:
            d = eod.get(f'eod/{c}', **{'from': '1990-01-01'}); break
        except Exception as e:
            if 'HTTP 404' in str(e): d = None; break
            if 'HTTP 402' in str(e) or 'HTTP 429' in str(e): stop[0] = True; log('LIMIT', str(e)[:80]); return
            time.sleep(2 * (k + 1)); d = None
    if d: pd.DataFrame(d).to_parquet(OUT / f'{c}.parquet', index=False)
    else: (OUT / f'{c}.empty').touch()
with ThreadPoolExecutor(10) as ex:
    for i, _ in enumerate(ex.map(run, todo)):
        if i % 300 == 0:
            u = eod.usage(); log(which, i, '/', len(todo), u.get('apiRequests'))
            if (u.get('apiRequests') or 0) > 99000: stop[0] = True; log('BUDGET STOP'); break
log(which, 'END', eod.usage())
