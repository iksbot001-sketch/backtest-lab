"""CAN SLIM 분업(대표 지시 2026-11-09: 안티그래비티 Claude → 막히면 Gemini, 그리고 Gemini Flash. Claude Code는 설계·검증·판정만).
사용: python dispatch3.py <LIT|CODE|AUDIT|DIGEST> [입력파일...]"""
import sys, time
from pathlib import Path
RUN = Path(__file__).resolve().parent
sys.path.insert(0, str(RUN.parents[1]))
import router  # noqa: E402
OUT = RUN / 'out'; OUT.mkdir(exist_ok=True)
router.CFG['routes'].update({'cs_code': 'agy_opus', 'cs_audit': 'agy_opus', 'cs_lit': 'argon', 'cs_digest': 'flash'})
RULES = """규칙: 한국어. 결론 먼저, 근거는 숫자·출처로. 확인 못 한 것은 '미확인', 기억에만 의존한 서지는 '기억' 표시. 지어내지 않는다.
매매 주문·종목 추천은 쓰지 않는다. API 키·비밀값은 출력하지 않는다."""
TASK = {
 'LIT': ('cs_lit', 'researcher', None, """[문헌 조사] 윌리엄 오닐 CAN SLIM의 실증 검증을 찾아 표로 정리하라(저자·연도·출처, 시장·기간, 기준을 어떻게 기계화했나, 핵심 수치(초과수익·MDD·회전율), 비용 반영, 한계, URL).
포함할 것: 학술 논문(예: CAN SLIM·IBD 지표·신고가 근처 매수(George & Hwang 2004 52주 고가 모멘텀)·상대강도·실적 가속), AAII 스크린 장기 성과, 오닐 손절 −7~8% 규칙의 검증, 시장 방향(M) 필터 검증.
끝에 (1) 우리 기계화 정의(CANSLIM_PREREG.md 첨부)에서 문헌과 다른 점·빠진 점, (2) 결과가 나쁘게 나올 때 예상되는 이유 3가지."""),
 'CODE': ('cs_code', 'quant', ['edit'], """[코드 구현] 이 폴더(research/gamma_backtest)에서 CANSLIM_PREREG.md를 그대로 구현하는 `canslim.py`를 작성하라. 실행은 하지 말고 파일만 만든다(실행·검증은 Claude Code).
참고할 기존 코드: refine.py(거래 루프 run(), 달력 포트폴리오 calendar(), 비용, 저장), wfeat.py(진입 전날 기술적 특징 계산: 52주 고가 대비 hi, 거래량 비율 vr, shift(1)), pxclean.py(clean), ../../lib/dist_report.py(summary, text), dist.py(무작위 대조군).
요구:
1) 패널 ~/agent-fund-data/ml_pred_M1fast_SURP_sm.parquet 전체 이벤트에 대해 C·A·N·S·L·M 플래그 계산. N·S는 이벤트의 i_fast 전날 기준(wfeat.py 방식, 모든 종목). L은 mom의 직전 분기(tq−1) 80분위 컷. M은 IWM 종가 > 200일선(전날).
2) S1 E1/E2/E3, 글자 빼기 6종(E1), 비용 2배(E1)를 refine.py의 run()과 같은 구조(종목별 비중복, 다음 발표에서 청산 판정, 최대 252일, 상폐 시 마지막 가격)로 구현. E2 손절 −8%는 진입가 대비 종가 기준, 다음 날 청산. E3 익절 +25% 동일.
3) S2: ~/agent-fund-data/refine/tr_sm_acc0_V0.parquet, tr_sm_p_ridge_V0.parquet 거래를 (tk,i0)로 이벤트와 맞춰 S1 기준 통과 여부로 나눠 비교.
4) 각 변형마다 거래 저장(~/agent-fund-data/canslim/), dist_report 요약, 달력 기준(연환산·IR·t·MDD·구간별) 출력, CSV 저장, trial_registry(~/agent-fund/data/trial_registry.jsonl)에 기록.
5) 기준별 통과 이벤트 수와 전체 통과 수를 연도별로 출력(표본 부족 확인용).
코드 스타일은 refine.py와 맞추고 주석은 짧은 한국어로. 끝에 작성한 파일 목록과 확인이 필요한 가정을 보고하라."""),
 'CODET': ('cs_code', 'quant', None, """[코드 구현, 텍스트 출력] 첨부한 CANSLIM_PREREG.md를 그대로 구현하는 파이썬 파일 `canslim.py` 전체를 하나의 ```python 코드 블록으로만 출력하라(설명은 블록 뒤 10줄 이내).
첨부 코드(refine.py, wfeat.py, pxclean.py, dist_report.py)의 함수·경로·스타일을 그대로 따른다. 실행 환경: ~/agent-fund/venv, 실행 위치 research/gamma_backtest, `from pxclean import clean`, `sys.path.insert(0, str(Path.home() / 'agent-fund/lib')); from dist_report import summary, text`.
요구:
1) 패널 ~/agent-fund-data/ml_pred_M1fast_SURP_sm.parquet 전체 이벤트에 C·A·N·S·L·M 플래그. 가격은 refine.py SM 로더처럼 clean() 후 IWM 달력(2005~)에 맞춤. 거래량은 prices/eodhd/<tk>.US.parquet의 volume. N(hi = 종가/252일 최고, min_periods 200)·S(vr = 20일 평균 거래량/120일 평균)는 i_fast 전날 값(shift(1) 후 i_fast 위치). L은 mom(inf→NaN)의 직전 분기(tq−1) 80분위 컷. M은 IWM 종가 > 200일선(전날). C: gR0 ≥ 0.22 & acc0 > 0. A: gR1,gR2,gR3 > 0 & mean(gR0..gR3) ≥ 0.22.
2) 거래 루프는 refine.py run()과 같은 구조: 종목별 비중복, 진입 i_fast·진입가 ≥ $5, 이후 발표 행(같은 종목 다음 이벤트)에서 청산 판정(E1: 그 행의 C 또는 A가 False면 그 행의 i_fast에 청산), 최대 252일, 상폐 시 마지막 유효 가격. E2: E1 + 진입가 대비 종가 −8% 이하인 첫날의 다음 날 청산. E3: E2 + 종가 +25% 이상인 첫날의 다음 날 청산. 비용 편도 liq H 0.10%, L 0.30%, cm 배수.
3) 변형: S1_E1, S1_E2, S1_E3, 글자 빼기 noC·noA·noN·noS·noL·noM(E1), S1_E1_x2(비용 2배). 각 변형: 거래 저장 ~/agent-fund-data/canslim/tr_<v>.parquet, refine.py calendar()와 같은 달력 포트폴리오 지표(연환산, IR, t, MDD, 2019 전후), dist_report summary 텍스트 출력, 결과 CSV ~/agent-fund-data/canslim/canslim.csv, trial_registry(~/agent-fund/data/trial_registry.jsonl) 기록(study 'gamma_backtest', trial 'CANSLIM_<v>').
4) S2: ~/agent-fund-data/refine/tr_sm_acc0_V0.parquet, tr_sm_p_ridge_V0.parquet 거래를 패널과 (tk, i_fast==i0)로 맞춰, 진입 이벤트가 S1 전 기준 통과인 거래 vs 나머지의 summary(groups=tq) 출력.
5) 연도별 각 글자 통과 이벤트 수와 전체 통과 수 표 출력."""),
 'AUDIT': ('cs_audit', 'cro', None, """[감사] 너는 CRO다. 아래 CAN SLIM 코드와 결과를 반대 심문하라. (1) 미래 정보 누수(시점, 컷 계산), (2) 생존·선택 편향, (3) 다중검정·사후 변경, (4) 비용·체결(손절 체결가 포함), (5) 사전 등록과 구현의 불일치.
각 항목: 문제 / 심각도(상중하) / 확인 방법 / 결론에 미치는 영향. 마지막에 통과·조건부·실패 판정."""),
 'DIGEST': ('cs_digest', 'editor', None, """[다이제스트] 아래 CAN SLIM 연구 결과를 투자 비전문가도 이해할 수 있게 10줄 이내로 요약하라. 숫자는 원문 그대로, 과장 금지. 마지막 2줄은 '그래서 내 투자에 무엇이 달라지나'."""),
}
key = sys.argv[1]; route, role, tools, task = TASK[key]
ctx = '\n\n'.join(f'### {Path(f).name}\n' + Path(f).read_text()[:60000] for f in sys.argv[2:])
t0 = time.time()
try:
    r = router.run(route, RULES + '\n\n' + task + ('\n\n[자료]\n' + ctx if ctx else ''), role=role, tools=tools, workdir=RUN if tools else None, log_path=OUT / f'CS_{key}.log.json')
    text, model, sub = r['text'], r['model'], r['substituted']
except router.AllDown as e:
    text, model, sub = f'ALL DOWN: {e}', None, None
(OUT / f'CS_{key}.md').write_text(f'<!-- {key} · 모델 {model} · 대체 {sub} · {round((time.time()-t0)/60,1)}분 -->\n' + text)
print(key, model, sub, len(text))
