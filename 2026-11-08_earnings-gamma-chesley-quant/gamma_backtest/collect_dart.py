"""OpenDART 주요계정(fnlttMultiAcnt) 분기 수집 — 이익 가속도 S1용 (전망치 불필요).
상장 코드가 있는 전 기업(CORPCODE.xml) × 2015~올해 × 4개 보고서(1분기·반기·3분기·사업) × 100개사 배치.
한 보고서에 전년 동기 값(frmtrm)이 같이 오므로 계절차분(t vs t-4)을 한 공시에서 얻는다.
캐시: ~/agent-fund-data/dart/raw/{year}_{rc}_{batch}.parquet (있으면 건너뜀 → 이어받기 가능)
한도: 일 20,000건. 전체 약 2,000건. 키는 investment-bot/.env 의 DART_API_KEY (출력하지 않음).
사용: python collect_dart.py [--years 2015 2026]"""
import sys, time, argparse
from pathlib import Path
import requests, pandas as pd
import xml.etree.ElementTree as ET

OUT = Path.home() / 'agent-fund-data' / 'dart' / 'raw'
OUT.mkdir(parents=True, exist_ok=True)
env = {}
for l in (Path.home() / 'investment-bot' / '.env').read_text().splitlines():
    if '=' in l and not l.startswith('#'):
        k, v = l.split('=', 1); env[k.strip()] = v.strip().strip('"\'')
KEY = env['DART_API_KEY']
KEEP = ['rcept_no', 'reprt_code', 'bsns_year', 'corp_code', 'stock_code', 'fs_div', 'sj_div', 'account_nm',
        'thstrm_dt', 'thstrm_amount', 'thstrm_add_amount', 'frmtrm_amount', 'frmtrm_add_amount']
ACC = {'매출액', '영업이익', '당기순이익(손실)', '법인세차감전 순이익', '자산총계', '자본총계'}

ap = argparse.ArgumentParser(); ap.add_argument('--years', nargs=2, type=int, default=[2015, 2026]); a = ap.parse_args()
root = ET.parse(Path.home() / 'earnings-tracker' / 'cache' / 'CORPCODE.xml').getroot()
codes = sorted({e.findtext('corp_code') for e in root.iter('list') if (e.findtext('stock_code') or '').strip()})
batches = [codes[i:i + 100] for i in range(0, len(codes), 100)]
print('corp', len(codes), 'batches', len(batches), flush=True)
calls = empty = 0
for yr in range(a.years[0], a.years[1] + 1):
    for rc in ('11013', '11012', '11014', '11011'):
        for bi, b in enumerate(batches):
            f = OUT / f'{yr}_{rc}_{bi:02d}.parquet'
            if f.exists(): continue
            for attempt in range(4):
                try:
                    r = requests.get('https://opendart.fss.or.kr/api/fnlttMultiAcnt.json',
                                     params={'crtfc_key': KEY, 'corp_code': ','.join(b), 'bsns_year': yr, 'reprt_code': rc}, timeout=90).json()
                    break
                except Exception as e:
                    time.sleep(3 * (attempt + 1)); r = {'status': 'ERR', 'message': repr(e)[:100]}
            calls += 1
            st = r.get('status')
            if st == '020': print('일일 한도 도달 — 중단. 내일 이어받기', flush=True); sys.exit(0)
            if st not in ('000', '013'):
                print('실패', yr, rc, bi, st, r.get('message'), flush=True); continue
            df = pd.DataFrame(r.get('list', []))
            if df.empty: empty += 1; df = pd.DataFrame(columns=KEEP)
            else: df = df[df.account_nm.isin(ACC)].reindex(columns=KEEP)
            df.to_parquet(f, index=False)
            time.sleep(0.15)
    print(yr, 'done, calls', calls, 'empty', empty, flush=True)
print('ALL DONE', calls, flush=True)
