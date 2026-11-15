"""매일 전망 스냅샷 적재(시점 정보 확보용). 전망 추세가 있는 미국 보통주 전체(약 8,300) + 향후 90일 실적 발표 일정.
저장 ~/agent-fund-data/eodhd/snapshots/trends_YYYYMMDD.parquet, earnings_YYYYMMDD.parquet. 호출 약 8,400콜/일(한도 10만).
예약 실행: com.example.gamma-snapshot.plist(같은 폴더)를 대표가 launchd에 등록. 키는 출력하지 않는다."""
import sys, time, glob, gzip, json
from pathlib import Path
from datetime import date, timedelta
from concurrent.futures import ThreadPoolExecutor
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent))
import eod
E = Path.home() / 'agent-fund-data/eodhd'; S = E / 'snapshots'; S.mkdir(exist_ok=True)
day = date.today().strftime('%Y%m%d')
out = S / f'trends_{day}.parquet'
if out.exists():
    sys.exit(0)
codes = sorted(Path(f).name[:-8] for f in glob.glob(str(E / 'trends/*.US.json.gz')) if json.load(gzip.open(f, 'rt')))
chunks = [codes[i:i + 20] for i in range(0, len(codes), 20)]


def run(ch):
    d = None
    for k in range(3):
        try:
            d = eod.get('calendar/trends', symbols=','.join(ch)); break
        except Exception:
            time.sleep(3 * (k + 1))
    rows = []
    for g in (d or {}).get('trends') or []:
        rows += [r for r in g if r.get('period') in ('0q', '+1q', '0y', '+1y')]
    return rows


with ThreadPoolExecutor(6) as ex:
    rows = [r for rs in ex.map(run, chunks) for r in rs]
df = pd.DataFrame(rows); df['snap_date'] = day
df.to_parquet(out, index=False)
e = eod.get('calendar/earnings', **{'from': date.today().isoformat(), 'to': (date.today() + timedelta(days=90)).isoformat()})
pd.DataFrame((e or {}).get('earnings') or []).assign(snap_date=day).to_parquet(S / f'earnings_{day}.parquet', index=False)
print(day, 'trend rows', len(df), 'codes', df.code.nunique() if len(df) else 0, eod.usage())
