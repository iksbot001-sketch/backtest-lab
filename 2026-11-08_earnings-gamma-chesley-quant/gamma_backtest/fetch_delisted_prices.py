"""KIND 상장폐지 목록(2016년 이후 폐지분)의 일봉을 네이버 siseJson에서 받아 보관. 되는 종목만 저장, 안 되는 종목은 기록.
저장: ~/agent-fund-data/prices/kr_delisted/{code}.parquet (date, open, high, low, close, volume) + meta/delisted_fetch.csv
기존 가격 DB(kr/)에 이미 있는 코드는 건너뜀. 같은 코드가 코스닥 이전상장 등으로 계속 거래되면 기존 DB를 쓴다."""
import ast, time, requests
import pandas as pd
from pathlib import Path
S = Path.home() / 'agent-fund-data'
OUT = S / 'prices' / 'kr_delisted'; OUT.mkdir(parents=True, exist_ok=True)
d = pd.read_parquet(S / 'dart' / 'kind_delisted.parquet')
d = d[d['폐지일자'] >= '2012-01-01']
have = {p.stem for p in (S / 'prices' / 'kr').glob('*.parquet')}
log = []
for _, r in d.iterrows():
    c = r['code']
    if c in have: log.append((c, r['회사명'], 'in_main_db', 0)); continue
    f = OUT / f'{c}.parquet'
    if f.exists(): continue
    try:
        t = requests.get(f'https://api.finance.naver.com/siseJson.naver?symbol={c}&requestType=1&startTime=19900101&endTime=20261108&timeframe=day',
                         headers={'User-Agent': 'Mozilla/5.0'}, timeout=30).text.strip()
        rows = ast.literal_eval(t.replace('\n', '').replace('null', 'None')) if len(t) > 5 else []
    except Exception as e:
        log.append((c, r['회사명'], 'err ' + repr(e)[:40], 0)); time.sleep(1); continue
    if len(rows) > 1:
        df = pd.DataFrame([x[:6] for x in rows[1:]], columns=['date', 'open', 'high', 'low', 'close', 'volume'])
        df['date'] = pd.to_datetime(df['date'].astype(str)); df = df[['date', 'open', 'high', 'low', 'close', 'volume']]
        df.to_parquet(f, index=False); log.append((c, r['회사명'], 'ok', len(df)))
    else: log.append((c, r['회사명'], 'empty', 0))
    time.sleep(0.3)
pd.DataFrame(log, columns=['code', 'name', 'status', 'rows']).to_csv(S / 'prices' / 'delisted_fetch.csv', index=False)
print(pd.DataFrame(log, columns=['code', 'name', 'status', 'rows']).status.value_counts())
