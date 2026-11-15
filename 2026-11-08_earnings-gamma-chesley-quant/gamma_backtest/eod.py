"""EODHD 공용 헬퍼. 키는 investment-bot/.env의 EODHD_API_KEY, 출력하지 않는다."""
from pathlib import Path
import requests
KEY = next(l.split('=', 1)[1].strip() for l in Path('~/investment-bot/.env').expanduser().read_text().splitlines()
           if l.split('=', 1)[0] == 'EODHD_API_KEY')
BASE = 'https://eodhd.com/api/'


def get(path, **params):
    r = requests.get(BASE + path, params={**params, 'api_token': KEY, 'fmt': 'json'}, timeout=90)
    if r.status_code != 200:
        raise RuntimeError(f'{path} HTTP {r.status_code}: {r.text[:200].replace(KEY, "***")}')
    return r.json()


def usage():
    u = get('user')
    return {k: u.get(k) for k in ('subscriptionType', 'apiRequests', 'dailyRateLimit', 'extraLimit')}
