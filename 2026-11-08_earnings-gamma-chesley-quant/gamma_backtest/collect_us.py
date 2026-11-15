"""미국 S1 수집: S&P 500 편입 이력(2008~)의 티커 중 SEC CIK가 잡히는 것만.
① SEC companyfacts(EPS·순이익·매출, 공시일 filed 포함) ② submissions(8-K Item 2.02 실적 발표일) ③ yfinance 수정주가.
SEC 요청 헤더는 대표가 earnings-tracker에 설정해 둔 sec_user_agent를 그대로 쓴다(출력하지 않음). 초당 10건 한도 → 0.15초 간격.
상장폐지·인수 종목 대부분은 CIK·가격이 없어 빠진다(생존편향, 결과에 명시)."""
import json, time, requests
from pathlib import Path
import pandas as pd
S = Path.home() / 'agent-fund-data'
UA = json.load(open(Path.home() / 'earnings-tracker' / 'config.json'))['sec_user_agent']
H = {'User-Agent': UA}
m = json.load(open(S / 'us_ticker_cik.json'))
ciks = sorted({v for v in m.values() if v})
print('CIK', len(ciks), flush=True)
def get(url, f):
    if f.exists(): return
    for a in range(4):
        r = requests.get(url, headers=H, timeout=60)
        if r.status_code == 200: f.write_bytes(r.content); return
        if r.status_code == 404: f.write_text('{}'); return
        time.sleep(2 * (a + 1))
    print('fail', url, r.status_code, flush=True)
for i, c in enumerate(ciks):
    get(f'https://data.sec.gov/api/xbrl/companyfacts/CIK{c:010d}.json', S / 'sec' / 'facts' / f'{c}.json'); time.sleep(0.15)
    get(f'https://data.sec.gov/submissions/CIK{c:010d}.json', S / 'sec' / 'subs' / f'{c}.json'); time.sleep(0.15)
    if i % 100 == 0: print('sec', i, flush=True)
import yfinance as yf
tick = sorted({t.split('-')[0] for t, v in m.items() if v})
print('prices', len(tick), flush=True)
for i in range(0, len(tick), 50):
    b = [t.replace('.', '-') for t in tick[i:i + 50]]
    d = yf.download(b + (['SPY', 'RSP'] if i == 0 else []), start='2007-06-01', auto_adjust=True, progress=False, threads=True)['Close']
    for t in d.columns:
        s = d[t].dropna()
        if len(s): s.rename('close').to_frame().reset_index().rename(columns={'Date': 'date'}).to_parquet(S / 'prices' / 'us' / f'{t}.parquet', index=False)
    print('px', i, flush=True)
print('DONE', flush=True)
