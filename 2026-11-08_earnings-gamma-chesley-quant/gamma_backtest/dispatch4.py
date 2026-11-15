"""체슬리 퀀트 분업(대표 지시 2026-11-09: 안티그래비티 Claude → 막히면 Gemini, 그리고 Gemini Flash. Claude Code는 설계·검증·판정만).
사용: python dispatch4.py <NOTE|CODE|COLLECT|AUDIT|DIGEST> [입력파일...]"""
import sys, time
from pathlib import Path
RUN = Path(__file__).resolve().parent
sys.path.insert(0, str(RUN.parents[1]))
import router  # noqa: E402
OUT = RUN / 'out'; OUT.mkdir(exist_ok=True)
router.CFG['routes'].update({'ch_code': 'agy_opus', 'ch_audit': 'agy_opus', 'ch_note': 'flash', 'ch_digest': 'flash'})
RULES = """규칙: 한국어. 파일 읽기·명령 실행 도구를 쓰지 말고 이 프롬프트와 [자료]에 첨부된 내용만으로 답한다. 확인 못 한 것은 '미확인'. 지어내지 않는다. 매매 주문·종목 추천은 쓰지 않는다. API 키·비밀값은 출력하지 않는다."""
SCHEMA = """[데이터 스키마(확인됨)]
- 가격: ~/agent-fund-data/prices/kr/<6자리코드>.parquet 와 ~/agent-fund-data/prices/kr_delisted/<코드>.parquet, 열 date, open, high, low, close, volume (수정주가). 상폐 파일은 마지막에 open=0·close 고정 행이 있을 수 있음(거래정지) → volume==0 & open==0 행은 거래 불가로 보고 그 직전 정상 종가로 청산.
- 종목 정보: ~/agent-fund-data/prices/meta/universe.parquet (code, name, mkt[KOSPI/KOSDAQ], kind, first, last). 상폐 종목 목록 ~/agent-fund-data/dart/kind_delisted.parquet (회사명, 폐지일자, code).
- 재무: ~/agent-fund-data/dart/panel_kr.parquet (corp_code, stock_code, fy, q[1~4], filed[공시일], sales, op[분기 단독, 4분기는 연간−9개월], tq). 같은 (stock_code, fy, q)에 여러 행이면 filed 가장 이른 행(최초 공시)을 쓴다.
- 발행주식수: ~/agent-fund-data/eodhd/fund/<코드>.KO.json.gz 또는 .KQ.json.gz, json['outstandingShares']['quarterly'] = {'0': {'dateFormatted': 'YYYY-MM-DD', 'shares': int}, ...}. 시점 t에는 dateFormatted + 60일 ≤ t 인 최신 값(공시 지연 가정).
- KODEX 200: prices/kr/069500.parquet.
- DART 키: ~/investment-bot/.env 의 DART_API_KEY (collect_dart.py 방식으로 읽고 출력 금지). CORPCODE: ~/earnings-tracker/cache/CORPCODE.xml (list 요소의 corp_code, stock_code).
- 분포 보고: sys.path.insert(0, str(Path.home()/'agent-fund/lib')); from dist_report import summary, text. 실행 파이썬 ~/agent-fund/venv (pandas, numpy, scipy, requests 있음)."""
TASK = {
 'NOTE': ('ch_note', 'editor', """[옵시디언 노트 초안] 아래 '원문 조건'을 옵시디언 전략 기록 노트로 정리하라. 첨부한 기존 노트(골든크로스_261022.md)의 frontmatter·구성(상위 링크, 규칙, 결과, 운영)을 따른다.
제목: '체슬리퀀트_261109 · 체슬리투자자문 퀀트 전략'. frontmatter: type 전략기록, 날짜 2026-11-09, 판정 '백테스트 중', 출처 '체슬리투자자문 강의(대표 제공 화면)'.
'규칙' 절에 원문 조건을 빠짐없이, 원문 표현을 최대한 그대로(요약·해석 금지) 적는다. '결과' 절은 '백테스트 진행 중 (CHESLEY_PREREG.md)'만. 예시 표(10월, 93종목 중 6개: 코웨이·가온전선·팬오션·안랩·디아이·오킨스전자, 시총·주가·PBR·PER·ROE·외인6개월)는 '강의 예시(2026년 10월)' 소절에 표로 옮긴다.
원문 조건:
[Q1 52주 신고가 퀀트] KOSPI, KOSDAQ 52주 신고가 종목 중 조건을 모두 충족하는 종목: YoY, QoQ 매출 및 영업이익 증가 / 최근5분기동안 매출 및 영업이익이 적자가 없는 기업 / 6개월 누적 외인 수급이 있는 기업 / 시가총액 5,000억 이상 / 최근 1년간 CB, BW 발행이 없으며, 대주주의 지분이 줄어들지 않은 기업 / 상장 이후 5분기가 지난 기업 / 편입하는 종목은 최대 13종목.
월별 퀀트종목이 13종목을 초과하는 경우의 선정 방법: 매출, 영업이익, 영업이익률의 QoQ, YoY, 그리고 외국인 6개월 수급까지 7개 항목에 점수를 부여하여 합산점수가 높은순으로 13위까지 편입. 동점이 나오는 경우 1. 영업이익률이 YoY나 QoQ로 하락하고 있는 종목을 제외 2. 영업이익률을 제외한 5개 항목의 점수가 낮은 종목을 제외 3. 매출, 영업이익의 성장률이 높은 종목을 편입.
편입 편출 기준: 52주 신고가를 기록한 익월 말일 종가로 매수하여 한 달 보유 후 매도.
[Q2 자사주 변형] 종목 선정 기준: 최근 5년간 자사주매입이나 소각 공시가 3회 이상인 경우 동일 비중으로 편입. 편입 편출 기준: 종목 선정 기준에 부합 시 편입하여 7개월 후 편출, 7개월이 지나기 전에 다시 자사주매입이나 소각 시 최종 공시시점으로부터 7개월 후 편출.
화면 제목: '10월 BM 0.26%, KOSPI, KOSDAQ 52주 신고가 93종목중 조건을 모두 충족하는 종목'.
마크다운 노트 본문만 출력하라."""),
 'CODE': ('ch_code', 'quant', """[코드 구현, 텍스트 출력] 첨부 CHESLEY_PREREG.md를 그대로 구현하는 `chesley.py` 전체를 하나의 ```python 코드 블록으로만 출력하라(설명은 블록 뒤 10줄 이내).
""" + SCHEMA + """
요구:
1) 모드 `python chesley.py candidates`: CB·BW·대주주·자사주 조건을 빼고 신고가·재무·시총·상장기간만으로 월별(2017-01~2026-10) 통과 종목을 계산해 ~/agent-fund-data/chesley/candidates.parquet(ym, code) 저장, 고유 종목 수 출력.
2) 모드 `python chesley.py run`: ~/agent-fund-data/chesley/disclosures.parquet(code, rcept_dt[YYYYMMDD], report_nm)를 읽어 CB/BW('전환사채권발행결정','신주인수권부사채권발행결정' 포함 문자열), '최대주주변경', 자사주('자기주식취득결정' 또는 '소각' 포함) 조건 적용. 정정 공시('[기재정정]' 등 접두)는 같은 사건으로 보고 중복 제거(같은 code·같은 report_nm 핵심어·30일 이내 하나로).
3) 13종목 초과 시 6개 항목(매출·영업이익·영업이익률의 QoQ·YoY 성장률) 월별 백분위 순위 합, 동점 규칙 ①~③ 구현.
4) Q1 시점 A·B, Q2(7개월·연장 규칙), 비교 기준(KODEX 200, 신고가 전체 동일비중 시점 A), 비용 편도 0.25%·2배. 월별 포트폴리오 수익률 시계열, CAGR·MDD·Sharpe·연변동성·베타·KODEX 200 대비 월별 초과수익 t, 2017~2021/2022~ 구간 출력. Q2는 일별 보유를 월말 기준으로 묶어 월 수익 계산(동일 비중, 신규 편입 시 재조정).
5) 편입 건별 수익(진입·청산 종가, 비용 차감, KODEX 200 대비 초과) 저장 ~/agent-fund-data/chesley/tr_<변형>.parquet, dist_report summary 출력, 무작위 대조(같은 달 신고가 종목에서 같은 수 무작위, 시드 고정).
6) 결과 CSV ~/agent-fund-data/chesley/chesley.csv, trial_registry(~/agent-fund/data/trial_registry.jsonl, study 'gamma_backtest', trial 'CHESLEY_<변형>') 기록.
7) 월별 통과 종목 수(필터 단계별) 출력.
우선주(코드 끝자리 0이 아닌 종목)·스팩(이름에 '스팩' 또는 '기업인수목적')·ETF/ETN/리츠(universe.kind 등)는 제외. 코드는 짧은 한국어 주석, 기존 refine.py 스타일."""),
 'COLLECT': ('ch_code', 'data', """[코드 구현, 텍스트 출력] DART 공시 목록 수집기 `collect_disclosures.py` 전체를 하나의 ```python 코드 블록으로만 출력하라.
""" + SCHEMA + """
요구: ~/agent-fund-data/chesley/candidates.parquet의 고유 code마다 CORPCODE.xml로 corp_code를 찾고(없으면 기록 후 건너뜀), OpenDART list.json(https://opendart.fss.or.kr/api/list.json, 파라미터 crtfc_key, corp_code, bgn_de=20110101, end_de=오늘, page_no, page_count=100)으로 전체 공시를 페이지 끝까지 받아, report_nm에 '전환사채권발행결정','신주인수권부사채권발행결정','최대주주변경','자기주식취득결정','소각' 중 하나가 들어간 행만 (code, corp_code, rcept_dt, report_nm, rcept_no)로 저장.
캐시: 종목별 ~/agent-fund-data/chesley/disc_raw/<code>.parquet(있으면 건너뜀, 이어받기). 상태 '013'(데이터 없음)은 빈 파일로 저장. '020'(한도 초과)이면 중단하고 진행 상황 출력. 호출 간 0.1초 대기, 재시도 3회. 끝에 전체를 ~/agent-fund-data/chesley/disclosures.parquet로 합치고 건수 출력. 키는 출력하지 않는다."""),
 'SHARES': ('ch_code', 'data', """[코드 구현, 텍스트 출력] DART 발행주식총수 수집기 `collect_shares.py` 전체를 하나의 ```python 코드 블록으로만 출력하라.
""" + SCHEMA + """
요구: ~/agent-fund-data/chesley/nosh.parquet의 고유 code마다 CORPCODE.xml로 corp_code를 찾고, OpenDART 주식의 총수 현황 API(https://opendart.fss.or.kr/api/stockTotqySttus.json, 파라미터 crtfc_key, corp_code, bsns_year, reprt_code)를 bsns_year 2015~2026 × reprt_code 11011(사업)·11012(반기)로 호출한다.
응답 list에서 se가 '보통주'인 행의 istc_totqy(발행주식총수, 쉼표 제거 후 정수)를 쓴다. 보통주 행이 없으면 '합계'. 기준일: 11011은 bsns_year-12-31, 11012는 bsns_year-06-30. 사용 가능일은 기준일+90일(사업)·+60일(반기)로 기록.
출력 열: code, corp_code, ref_date, avail_date, shares, reprt_code. 캐시 ~/agent-fund-data/chesley/shares_raw/<code>.parquet(있으면 건너뜀). 상태 '013'은 건너뜀, '020'은 중단, 호출 간 0.1초, 재시도 3회. 끝에 ~/agent-fund-data/chesley/shares_dart.parquet로 합치고 건수 출력. 키는 출력하지 않는다."""),
 'AUDIT': ('ch_audit', 'cro', """[감사] 너는 CRO다. 아래 체슬리 퀀트 코드와 결과를 반대 심문하라. (1) 미래 정보 누수(공시일·발행주식수·신고가 시점), (2) 생존·선택 편향(상폐 처리), (3) 다중검정·사후 변경, (4) 비용·체결, (5) 사전 등록과 구현의 불일치, (6) 원문 조건과의 차이(외국인 수급 누락 등). 각 항목: 문제 / 심각도 / 확인 방법 / 영향. 마지막에 통과·조건부·실패 판정."""),
 'DIGEST': ('ch_digest', 'editor', """[다이제스트] 아래 체슬리 퀀트 백테스트 결과를 투자 비전문가도 이해하게 10줄 이내로 요약하라. 숫자는 원문 그대로, 과장 금지, 결과에 없는 제안 금지. 마지막 2줄은 '그래서 내 투자에 무엇이 달라지나'."""),
}
key = sys.argv[1]; route, role, task = TASK[key]
ctx = '\n\n'.join(f'### {Path(f).name}\n' + Path(f).read_text()[:60000] for f in sys.argv[2:])
t0 = time.time()
try:
    r = router.run(route, RULES + '\n\n' + task + ('\n\n[자료]\n' + ctx if ctx else ''), role=role, tools=None, log_path=OUT / f'CH_{key}.log.json')
    text, model, sub = r['text'], r['model'], r['substituted']
except router.AllDown as e:
    text, model, sub = f'ALL DOWN: {e}', None, None
(OUT / f'CH_{key}.md').write_text(f'<!-- {key} · 모델 {model} · 대체 {sub} · {round((time.time()-t0)/60,1)}분 -->\n' + text)
print(key, model, sub, len(text))
