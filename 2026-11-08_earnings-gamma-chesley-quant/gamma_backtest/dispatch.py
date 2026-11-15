"""이익 가속도 백테스트 P1(문헌)·P2(데이터 가용성) 위임. 사용: python dispatch.py P1|P2
P1 = Antigravity의 Claude(lit_scan 경로), P2 = Gemini Argon. 텍스트 업무(tools=None): 결과는 이 스크립트가 out/에 저장."""
import sys, time
from pathlib import Path
RUN = Path(__file__).resolve().parent
sys.path.insert(0, str(RUN.parents[1]))
import router  # noqa: E402

OUT = RUN / 'out'
router.CFG['routes']['gamma_gemini'] = 'argon'   # 이 실행에만 적용(설정 파일은 건드리지 않음)

RULES = """규칙
- 한국어. 결론 먼저, 표 중심. 모든 사실에 출처 URL을 붙인다. 확인하지 못한 것은 '미확인'이라고 쓰고 추측으로 채우지 않는다.
- 기억에만 의존한 서지·수치는 '기억'으로 표시한다. 웹 검색·URL 읽기로 직접 확인한 것은 '확인'으로 표시한다.
- 투자 조언이 아니라 연구 설계용 자료 조사다. 매매 주문·종목 추천은 쓰지 않는다.
- 가격·요금은 페이지에서 직접 본 것만 쓴다. 못 봤으면 '미확인'.
"""

GOAL = """배경: 대표는 '이익(또는 이익 전망)의 2차 미분(= 성장률의 변화, 가속도)이 양(+)으로 높아지고 지속되는 종목을 사서, 그 가속도가 꺾일 때까지 보유'하는 전략을
S&P 500과 코스피에서 최대 30년간 백테스트하려 한다. 1단계는 애널리스트 전망치 없이 '실현된 분기 이익'만으로 한다(He & Narayanamoorthy, JAE 2020 방식: 분기 EPS 계절차분 = 성장률, 그 분기간 변화 = 가속도).
"""

TASKS = {
 'P1': ('lit_scan', 'researcher', GOAL + """
[업무 P1 문헌 정독] 아래 문헌의 1차 출처(논문 원문 PDF나 저자 공개본)를 직접 열어 읽고, 문헌마다 다음을 표로 정리하라.
열: 이익 신호의 원천(실현 이익 / 애널리스트 전망 / 둘 다, 정확한 변수 정의), 데이터베이스(Compustat, I/B/E/S 등)와 표본 기간·유니버스·필터, 포트폴리오 구성(분위수·보유기간·리밸런싱), 핵심 수치(수익률·알파·t값), 청산 방식(고정 보유인가, 신호 반전 시 청산을 시험했나), 거래비용·소형주 제외 결과, 확인 수준.
문헌: (1) Bernard & Thomas 1989 JAR (2) Chan, Jegadeesh & Lakonishok 1996 JF (3) Stickel 1991 JAR (4) Givoly & Lakonishok 1979 JAE (5) Gleason & Lee 2003 TAR (6) Livnat & Mendenhall 2006 JAR (7) Bouchaud, Krüger, Landier & Thesmar 2019 JF (8) Rangan & Sloan 1998 (9) Barber, Lehavy, McNichols & Trueman 2001 JF.
추가 조사: ① '선행 이익 성장률의 변화', '전망 곡선의 가속도', 'earnings revisions의 변화율'을 신호로 쓴 논문이 있는지 ② '신호가 약해질 때까지 보유'(가변 보유기간) 방식을 시험한 이익 모멘텀 연구가 있는지 ③ 한국 시장(KOSPI/KOSDAQ)에서 이익 모멘텀·애널리스트 전망 수정을 다룬 KCI 등재 논문이 있는지(제목·저자·연도·사용한 컨센서스 출처).
끝에 '이 백테스트 설계에 주는 시사점' 5줄 이내."""),
 'P2': ('gamma_gemini', 'data', GOAL + """
[업무 P2 데이터 가용성 감사 — 전망치 불필요 항목만] 아래 각 항목에 대해 표로 답하라.
열: 데이터 원천, 제공 시작 연도, 공시일(발표일) 기준 시점 정보 포함 여부(point-in-time인지, 사후 수정 값인지), 접근 방식(API/일괄 파일/웹), 비용, 개인 이용 약관·호출 한도, 샘플 한 건을 확인하는 방법(URL이나 엔드포인트), 확인 수준.
항목:
 US-1 미국 상장사 분기 EPS·매출·순이익과 공시일: SEC EDGAR XBRL(companyfacts, frames, Financial Statement Data Sets)의 시작 연도와 한계, 2009년 이전을 메우는 무료 또는 저가 대안
 US-2 S&P 500 시점별 구성종목(편입·편출 날짜): 무료로 구할 수 있는 이력과 시작 연도, 한계
 US-3 상장폐지·인수합병 종목을 포함한 미국 가격 이력(생존편향 없는): 무료/저가 대안(Stooq, Tiingo, Sharadar 등)과 한계
 US-4 Fama-French 요인(Ken French Data Library): 제공 범위
 KR-1 한국 상장사 분기 EPS·순이익·영업이익과 공시일: OpenDART 재무제표 API(fnlttSinglAcntAll 등)가 제공하는 시작 연도(보고서 연도 기준), 그 이전(1999~2014)은 어떻게 구하는지(공시 원문 파싱, 다른 무료 원천), 연결/별도 구분, 정정공시 처리
 KR-2 한국 상장폐지 종목 목록과 폐지 사유·날짜: KRX KIND, 공공데이터포털 금융위원회 API, data.krx.co.kr(정보데이터시스템). 로그인 필요 여부, 가격 이력 포함 여부
 KR-3 한국 상장폐지 종목의 과거 주가: 무료로 구할 수 있는 원천(네이버, KRX 등)이 있는지
 KR-4 한국 시장 요인(Fama-French형: 시장, 규모, 가치, 모멘텀) 무료 제공처
 KR-5 pykrx가 최근 KRX 로그인 요구로 막히는 문제: 무료 대체 경로
마지막에 '무료로 가능한 최대 기간' 한 줄 요약표(미국/한국 × 가격, 실현 이익, 구성종목/상폐, 요인)와 가장 위험한 병목 3가지."""),
}

stage = sys.argv[1]
route, role, task = TASKS[stage]
t0 = time.time()
try:
    r = router.run(route, RULES + '\n' + task, role=None, tools=None, log_path=OUT / f'{stage}.log.json')
    text, model, sub = r['text'], r['model'], r['substituted']
except router.AllDown as e:
    text, model, sub = f'ALL DOWN: {e}', None, None
(OUT / f'{stage}.md').write_text(f"<!-- {stage} · 모델 {model} · 대체 {sub} · {round((time.time()-t0)/60,1)}분 -->\n" + text)
print(stage, model, sub, len(text), flush=True)
