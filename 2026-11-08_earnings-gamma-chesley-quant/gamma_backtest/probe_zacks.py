"""Nasdaq Data Link ZACKS 무료 샘플 구조 점검. 키는 investment-bot/.env에서 읽고 출력하지 않는다."""
import sys, json, requests
from pathlib import Path
import pandas as pd
KEY = next(l.split('=', 1)[1].strip() for l in Path('~/investment-bot/.env').expanduser().read_text().splitlines()
           if l.split('=', 1)[0] == 'NASDAQ_DATA_LINK_API_KEY')
BASE = 'https://data.nasdaq.com/api/v3/datatables/'
OUT = Path.home() / 'agent-fund-data/zacks'


def get(path, **params):
    r = requests.get(BASE + path, params={**params, 'api_key': KEY}, timeout=60)
    if r.status_code != 200:
        return None, f'HTTP {r.status_code}: {r.text[:300].replace(KEY, "***")}'
    return r.json(), None


for tbl in sys.argv[1:]:
    meta, err = get(f'{tbl}/metadata.json')
    print(f'== {tbl} metadata:', err or [c['name'] for c in meta['datatable']['columns']])
    rows, cols, cursor = [], None, None
    for _ in range(20):
        p = {'ticker': 'AAPL,MSFT,IBM,BA,GE', 'qopts.per_page': 10000}
        if cursor: p['qopts.cursor_id'] = cursor
        d, err = get(f'{tbl}.json', **p)
        if err: print('  data:', err); break
        cols = [c['name'] for c in d['datatable']['columns']]
        rows += d['datatable']['data']
        cursor = d['meta'].get('next_cursor_id')
        if not cursor: break
    if cols:
        df = pd.DataFrame(rows, columns=cols)
        df.to_parquet(OUT / f'sample_{tbl.replace("/", "_")}.parquet')
        print('  rows', len(df), 'tickers', df['ticker'].unique().tolist() if 'ticker' in df else '-')
