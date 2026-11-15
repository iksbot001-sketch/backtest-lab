"""OpenDART 주식의 총수 현황(stockTotqySttus) 수집기 — collect_shares.py
대상: ~/agent-fund-data/chesley/nosh.parquet 의 고유 종목코드(code)
범위: bsns_year 2015~2026 × reprt_code 11011(사업), 11012(반기)
캐시: ~/agent-fund-data/chesley/shares_raw/<code>.parquet (있으면 건너뜀)
출력: ~/agent-fund-data/chesley/shares_dart.parquet (열: code, corp_code, ref_date, avail_date, shares, reprt_code)
키는 ~/investment-bot/.env 의 DART_API_KEY 를 읽으며 절대 출력하지 않는다.
"""
from __future__ import annotations
import sys
import time
import argparse
from pathlib import Path
import xml.etree.ElementTree as ET
import requests
import pandas as pd


def load_api_key() -> str:
    env_path = Path.home() / 'investment-bot' / '.env'
    env = {}
    for line in env_path.read_text(encoding='utf-8').splitlines():
        if '=' in line and not line.lstrip().startswith('#'):
            k, v = line.split('=', 1)
            env[k.strip()] = v.strip().strip('"\'')
    if 'DART_API_KEY' not in env or not env['DART_API_KEY']:
        raise RuntimeError('DART_API_KEY not found in ~/investment-bot/.env')
    return env['DART_API_KEY']


def load_corp_map() -> dict[str, str]:
    """CORPCODE.xml 에서 stock_code -> corp_code 매핑을 생성한다.
    동일 stock_code가 여러 개일 경우 modify_date가 가장 늦은(또는 마지막) 항목을 사용한다.
    """
    xml_path = Path.home() / 'earnings-tracker' / 'cache' / 'CORPCODE.xml'
    root = ET.parse(xml_path).getroot()
    mapping: dict[str, tuple[str, str]] = {}
    for elem in root.iter('list'):
        sc = (elem.findtext('stock_code') or '').strip()
        cc = (elem.findtext('corp_code') or '').strip()
        md = (elem.findtext('modify_date') or '').strip()
        if sc and cc:
            prev = mapping.get(sc)
            if prev is None or md >= prev[0]:
                mapping[sc] = (md, cc)
    return {sc: cc for sc, (_, cc) in mapping.items()}


def parse_int_shares(val) -> int | None:
    if val is None:
        return None
    s = str(val).strip().replace(',', '')
    if not s or s == '-':
        return None
    try:
        n = int(s)
        return n if n > 0 else None
    except ValueError:
        return None


def extract_shares(items: list[dict]) -> int | None:
    """응답 list에서 se == '보통주' 인 행의 istc_totqy를 우선 추출하고,
    없으면 se == '합계' 인 행의 istc_totqy를 추출한다.
    """
    if not items:
        return None
    for target_se in ('보통주', '합계'):
        for row in items:
            se = str(row.get('se') or '').strip()
            if se == target_se:
                val = parse_int_shares(row.get('istc_totqy'))
                if val is not None:
                    return val
    return None


def fetch_stock_totqy(session: requests.Session, api_key: str, corp_code: str, year: int, reprt_code: str) -> dict:
    url = 'https://opendart.fss.or.kr/api/stockTotqySttus.json'
    params = {
        'crtfc_key': api_key,
        'corp_code': corp_code,
        'bsns_year': str(year),
        'reprt_code': reprt_code,
    }
    last_err = None
    for attempt in range(3):
        try:
            resp = session.get(url, params=params, timeout=30)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            last_err = type(e).__name__
            if attempt < 2:
                time.sleep(1.0 * (attempt + 1))
    return {'status': 'ERR', 'message': f'request_failed:{last_err}'}


def merge_and_report(raw_dir: Path, out_file: Path, cols: list[str]) -> None:
    files = sorted(raw_dir.glob('*.parquet'))
    dfs = []
    for p in files:
        try:
            d = pd.read_parquet(p)
            if not d.empty:
                dfs.append(d)
        except Exception as e:
            print(f'캐시 읽기 실패 ({p.name}): {type(e).__name__}', flush=True)

    if dfs:
        merged = pd.concat(dfs, ignore_index=True)
        merged = merged.reindex(columns=cols)
        merged['shares'] = merged['shares'].astype('int64')
        merged = (
            merged.sort_values(['code', 'ref_date', 'reprt_code'])
            .drop_duplicates(subset=['code', 'ref_date', 'reprt_code'], keep='last')
            .reset_index(drop=True)
        )
    else:
        merged = pd.DataFrame(columns=cols)

    out_file.parent.mkdir(parents=True, exist_ok=True)
    merged.to_parquet(out_file, index=False)
    print(
        f'병합 완료: {out_file} | 총 {len(merged):,}건 '
        f'(고유 종목 {merged["code"].nunique():,}개, 캐시 파일 {len(files):,}개)',
        flush=True,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description='OpenDART 발행주식총수(stockTotqySttus) 수집기')
    parser.add_argument('--years', nargs=2, type=int, default=[2015, 2026], help='수집 연도 범위 (기본: 2015 2026)')
    args = parser.parse_args()

    base_dir = Path.home() / 'agent-fund-data' / 'chesley'
    nosh_path = base_dir / 'nosh.parquet'
    raw_dir = base_dir / 'shares_raw'
    out_file = base_dir / 'shares_dart.parquet'
    raw_dir.mkdir(parents=True, exist_ok=True)

    cols = ['code', 'corp_code', 'ref_date', 'avail_date', 'shares', 'reprt_code']

    key = load_api_key()
    corp_map = load_corp_map()

    nosh_df = pd.read_parquet(nosh_path)
    codes = sorted({str(c).strip().zfill(6) for c in nosh_df['code'].dropna().unique() if str(c).strip()})

    unmapped = [c for c in codes if c not in corp_map]
    mapped_codes = [c for c in codes if c in corp_map]
    print(
        f'대상 종목: 총 {len(codes):,}개 (CORPCODE 매핑: {len(mapped_codes):,}개, 미매핑: {len(unmapped):,}개)',
        flush=True,
    )

    years = range(args.years[0], args.years[1] + 1)
    reprt_codes = ('11012', '11011')  # 11012: 반기보고서, 11011: 사업보고서

    session = requests.Session()
    calls = 0
    skipped_cache = 0
    limit_reached = False

    for idx, code in enumerate(mapped_codes, 1):
        cache_file = raw_dir / f'{code}.parquet'
        if cache_file.exists():
            skipped_cache += 1
            continue

        corp_code = corp_map[code]
        rows = []
        aborted_code = False

        for yr in years:
            for rc in reprt_codes:
                res = fetch_stock_totqy(session, key, corp_code, yr, rc)
                calls += 1
                time.sleep(0.1)

                st = res.get('status')
                if st == '020':
                    print(f'일일 한도 도달(020) — 중단 ({code}, {yr}, {rc}). 누적 호출: {calls:,}건', flush=True)
                    limit_reached = True
                    aborted_code = True
                    break
                if st == '013':
                    continue
                if st != '000':
                    msg = res.get('message', '')
                    print(f'응답 오류: code={code} corp={corp_code} yr={yr} rc={rc} status={st} msg={msg}', flush=True)
                    continue

                shares = extract_shares(res.get('list', []))
                if shares is None:
                    continue

                if rc == '11011':
                    ref_dt = pd.Timestamp(year=yr, month=12, day=31)
                    avail_dt = ref_dt + pd.Timedelta(days=90)
                else:  # '11012'
                    ref_dt = pd.Timestamp(year=yr, month=6, day=30)
                    avail_dt = ref_dt + pd.Timedelta(days=60)

                rows.append({
                    'code': code,
                    'corp_code': corp_code,
                    'ref_date': ref_dt.strftime('%Y-%m-%d'),
                    'avail_date': avail_dt.strftime('%Y-%m-%d'),
                    'shares': int(shares),
                    'reprt_code': rc,
                })

            if aborted_code:
                break

        if limit_reached:
            break

        df_code = pd.DataFrame(rows, columns=cols) if rows else pd.DataFrame(columns=cols)
        if not df_code.empty:
            df_code['shares'] = df_code['shares'].astype('int64')
        df_code.to_parquet(cache_file, index=False)

        if idx % 50 == 0 or idx == len(mapped_codes):
            print(
                f'진행: {idx:,}/{len(mapped_codes):,} (캐시 건너뜀: {skipped_cache:,}, API 호출: {calls:,})',
                flush=True,
            )

    merge_and_report(raw_dir, out_file, cols)
    if limit_reached:
        sys.exit(0)


if __name__ == '__main__':
    main()
