"""DART company.json 로 시장 구분(corp_cls: Y=유가증권, K=코스닥, N=코넥스, E=기타)과 업종코드(induty_code)를 받는다. 이어받기 가능."""
import time, requests, pandas as pd
from pathlib import Path
S = Path.home() / 'agent-fund-data' / 'dart'
env = {}
for l in (Path.home() / 'investment-bot' / '.env').read_text().splitlines():
    if '=' in l and not l.startswith('#'):
        k, v = l.split('=', 1); env[k.strip()] = v.strip().strip('"\'')
KEY = env['DART_API_KEY']
corps = sorted(pd.read_parquet(S / 'panel_kr.parquet').corp_code.unique())
f = S / 'company.parquet'
done = pd.read_parquet(f) if f.exists() else pd.DataFrame(columns=['corp_code', 'corp_name', 'stock_code', 'corp_cls', 'induty_code', 'est_dt'])
seen = set(done.corp_code); rows = done.to_dict('records')
for i, c in enumerate(corps):
    if c in seen: continue
    for a in range(3):
        try:
            r = requests.get('https://opendart.fss.or.kr/api/company.json', params={'crtfc_key': KEY, 'corp_code': c}, timeout=30).json(); break
        except Exception: time.sleep(2); r = {}
    if r.get('status') == '020': print('한도'); break
    rows.append({k: r.get(k) for k in ['corp_code', 'corp_name', 'stock_code', 'corp_cls', 'induty_code', 'est_dt']} | {'corp_code': c})
    if i % 300 == 0: pd.DataFrame(rows).to_parquet(f, index=False); print(i, flush=True)
    time.sleep(0.1)
pd.DataFrame(rows).to_parquet(f, index=False); print('DONE', len(rows))
