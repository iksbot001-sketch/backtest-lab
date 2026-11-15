<!-- COLLECT · 모델 gemini-4-argon-medium · 대체 True · 1.1분 -->
```python
"""OpenDART 공시 목록(list.json) 수집기 — 체슬리(Chesley) 전략용 이벤트 공시 필터링.
입력: ~/agent-fund-data/chesley/candidates.parquet (고유 code)
매핑: ~/earnings-tracker/cache/CORPCODE.xml (stock_code -> corp_code)
캐시: ~/agent-fund-data/chesley/disc_raw/<code>.parquet (있으면 건너뜀, 이어받기)
출력: ~/agent-fund-data/chesley/disclosures.parquet (code, corp_code, rcept_dt, report_nm, rcept_no)
키: ~/investment-bot/.env 의 DART_API_KEY (출력 금지)"""
import sys
import time
from datetime import date
from pathlib import Path
import xml.etree.ElementTree as ET
import pandas as pd
import requests

BASE_DIR = Path.home() / 'agent-fund-data' / 'chesley'
CAND_PATH = BASE_DIR / 'candidates.parquet'
RAW_DIR = BASE_DIR / 'disc_raw'
OUT_PATH = BASE_DIR / 'disclosures.parquet'
CORP_XML = Path.home() / 'earnings-tracker' / 'cache' / 'CORPCODE.xml'
ENV_PATH = Path.home() / 'investment-bot' / '.env'

KEYWORDS = (
    '전환사채권발행결정',
    '신주인수권부사채권발행결정',
    '최대주주변경',
    '자기주식취득결정',
    '소각',
)
KEEP = ['code', 'corp_code', 'rcept_dt', 'report_nm', 'rcept_no']
 API_URL = 'https://opendart.fss.or.kr/api/list.json'


def load_api_key(env_path: Path) -> str:
    env = {}
    for line in env_path.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if '=' in line and not line.startswith('#'):
            k, v = line.split('=', 1)
            env[k.strip()] = v.strip().strip('"\'')
    if 'DART_API_KEY' not in env or not env['DART_API_KEY']:
        raise RuntimeError('DART_API_KEY not found in .env')
    return env['DART_API_KEY']


def load_corp_map(xml_path: Path) -> dict[str, str]:
    """stock_code(6자리) -> corp_code(8자리) 매핑. 동일 stock_code 중복 시 최신 modify_date 우선."""
    root = ET.parse(xml_path).getroot()
    mapping: dict[str, tuple[str, str]] = {}
    for elem in root.iter('list'):
        sc = (elem.findtext('stock_code') or '').strip()
        cc = (elem.findtext('corp_code') or '').strip()
        md = (elem.findtext('modify_date') or '').strip()
        if sc and cc:
            sc = sc.zfill(6)
            if sc not in mapping or md >= mapping[sc][0]:
                mapping[sc] = (md, cc)
    return {sc: cc for sc, (_, cc) in mapping.items()}


def fetch_page(key: str, corp_code: str, bgn_de: str, end_de: str, page_no: int) -> dict:
    params = {
        'crtfc_key': key,
        'corp_code': corp_code,
        'bgn_de': bgn_de,
        'end_de': end_de,
        'page_no': page_no,
        'page_count': 100,
    }
    last_err = None
    for attempt in range(4):  # 최초 1회 + 재시도 3회
        try:
            resp = requests.get(API_URL, params=params, timeout=30)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            last_err = e
            if attempt < 3:
                time.sleep(1.0 * (attempt + 1))
    return {'status': 'ERR', 'message': repr(last_err)[:120]}


def filter_rows(items: list[dict], code: str, corp_code: str) -> pd.DataFrame:
    if not items:
        return pd.DataFrame(columns=KEEP)
    df = pd.DataFrame(items)
    if 'report_nm' not in df.columns:
        return pd.DataFrame(columns=KEEP)
    mask = df['report_nm'].fillna('').apply(lambda nm: any(kw in nm for kw in KEYWORDS))
    df = df.loc[mask].copy()
    if df.empty:
        return pd.DataFrame(columns=KEEP)
    df['code'] = code
    df['corp_code'] = corp_code
    for col in KEEP:
        if col not in df.columns:
            df[col] = ''
    return df[KEEP].drop_duplicates(subset=['rcept_no']).reset_index(drop=True)


def merge_cached(raw_dir: Path, out_path: Path) -> pd.DataFrame:
    files = sorted(raw_dir.glob('*.parquet'))
    frames = []
    for f in files:
        try:
            df = pd.read_parquet(f)
            if not df.empty:
                frames.append(df[KEEP])
        except Exception as e:
            print(f'[경고] 캐시 파일 읽기 실패 ({f.name}): {e}', flush=True)
    if frames:
        merged = pd.concat(frames, ignore_index=True)
        merged = merged.drop_duplicates(subset=['code', 'rcept_no']).sort_values(
            ['rcept_dt', 'code', 'rcept_no']
        ).reset_index(drop=True)
    else:
        merged = pd.DataFrame(columns=KEEP)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    merged.to_parquet(out_path, index=False)
    return merged


def main():
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    key = load_api_key(ENV_PATH)
    corp_map = load_corp_map(CORP_XML)

    cand_df = pd.read_parquet(CAND_PATH)
    if 'code' not in cand_df.columns:
        raise KeyError("candidates.parquet에 'code' 열이 없습니다.")
    codes = sorted({str(c).strip().zfill(6) for c in cand_df['code'].dropna().unique()})

    end_de = date.today().strftime('%Y%m%d')
    bgn_de = '20110101'

    missing_corp = []
    skipped_cache = 0
    processed = 0
    empty_cnt = 0
    api_calls = 0
    quota_exceeded = False

    print(
        f'대상 종목: {len(codes)}개 | CORPCODE 매핑 보유: {len(corp_map)}개 | 조회기간: {bgn_de}~{end_de}',
        flush=True,
    )

    for idx, code in enumerate(codes, 1):
        cache_file = RAW_DIR / f'{code}.parquet'
        if cache_file.exists():
            skipped_cache += 1
            continue

        corp_code = corp_map.get(code)
        if not corp_code:
            missing_corp.append(code)
            print(f'[건너뜀] ({idx}/{len(codes)}) code={code}: CORPCODE.xml 매핑 없음', flush=True)
            continue

        page_no = 1
        all_items: list[dict] = []
        failed_stock = False

        while True:
            res = fetch_page(key, corp_code, bgn_de, end_de, page_no)
            api_calls += 1
            time.sleep(0.1)

            st = res.get('status')
            if st == '020':
                print(
                    f'[한도 초과 020] 중단 — 진행: {idx}/{len(codes)}번째 종목(code={code}, page={page_no}), '
                    f'완료={processed}, 캐시건너뜀={skipped_cache}, 미매핑={len(missing_corp)}, 총호출={api_calls}',
                    flush=True,
                )
                quota_exceeded = True
                break

            if st == '013':
                # 조회된 데이타가 없음
                break

            if st != '000':
                print(
                    f'[오류] code={code} corp_code={corp_code} page={page_no} '
                    f'status={st} msg={res.get("message")}',
                    flush=True,
                )
                failed_stock = True
                break

            items = res.get('list') or []
            all_items.extend(items)

            total_page = int(res.get('total_page') or 1)
            if page_no >= total_page:
                break
            page_no += 1

        if quota_exceeded:
            break

        if failed_stock:
            continue

        df_filtered = filter_rows(all_items, code, corp_code)
        if df_filtered.empty:
            empty_cnt += 1
        df_filtered.to_parquet(cache_file, index=False)
        processed += 1

        if processed % 50 == 0:
            print(
                f'[진행] 신규처리={processed}, 캐시건너뜀={skipped_cache}, '
                f'미매핑={len(missing_corp)}, 누적호출={api_calls}',
                flush=True,
            )

    if missing_corp:
        print(f'CORPCODE 미매핑 종목 ({len(missing_corp)}개): {missing_corp}', flush=True)

    merged = merge_cached(RAW_DIR, OUT_PATH)
    print(
        f'수집 완료(한도중단={quota_exceeded}) | 신규저장={processed}, 캐시유지={skipped_cache}, '
        f'결과없음/필터0건(신규중)={empty_cnt}, 미매핑={len(missing_corp)}, API호출={api_calls}',
        flush=True,
    )
    print(
        f'최종 저장: {OUT_PATH} | 총 공시 건수={len(merged):,}건 | 고유 종목수={merged["code"].nunique() if not merged.empty else 0}개',
        flush=True,
    )
    if not merged.empty:
        for kw in KEYWORDS:
            cnt = int(merged['report_nm'].fillna('').str.contains(kw, regex=False).sum())
            print(f'  - {kw}: {cnt:,}건', flush=True)


if __name__ == '__main__':
    main()
```
