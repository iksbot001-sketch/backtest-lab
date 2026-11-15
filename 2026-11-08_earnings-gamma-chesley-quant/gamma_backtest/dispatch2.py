"""EODHD 결제 후 후속 연구 분업. 사용: python dispatch2.py <과제> [입력파일...]
분업(대표 지시 2026-11-09): Claude Code = 데이터·코드·숫자 / Antigravity Claude(agy_opus) = 코드·결과 감사(누수·편향·반대 심문)
/ Antigravity Gemini(argon) = 문헌·배경 조사, 결론 반박 / Gemini Flash(flash) = 쉬운 말 요약·최종 다이제스트.
텍스트 업무(tools=None). 결과는 out/에 저장."""
import sys, time
from pathlib import Path
RUN = Path(__file__).resolve().parent
sys.path.insert(0, str(RUN.parents[1]))
import router  # noqa: E402
OUT = RUN / 'out'; OUT.mkdir(exist_ok=True)
router.CFG['routes'].update({'g2_audit': 'agy_opus', 'g2_lit': 'argon', 'g2_digest': 'flash'})
RULES = """규칙: 한국어. 결론 먼저, 근거는 숫자·출처로. 확인 못 한 것은 '미확인', 기억에만 의존한 서지는 '기억' 표시. 지어내지 않는다.
매매 주문·종목 추천은 쓰지 않는다. 대표 원칙: 초과수익이 확인돼도 같은 데이터 소스로 실전 투자가 가능해야 채택한다."""
TASK = {
 'L1': ('g2_lit', 'researcher', """[문헌 조사 L1] 아래 세 연구의 설계에 쓸 1차 문헌을 찾아 표로 정리하라(저자·연도·저널, 데이터·기간, 신호 정의, 핵심 수치, 한계, URL).
(1) 산업·섹터 단위 애널리스트 이익 전망 수정(상향/하향 비율, revision breadth, diffusion)이 이후 산업 수익률을 예측하는가. 반도체처럼 경기순환 산업에서의 증거, 한국 증거 포함.
(2) S&P 500·나스닥100 50/200일 이동평균 골든크로스(추세추종) 규칙의 장기 성과: 단순 보유 대비 수익·최대낙폭·위험조정 성과, 거래비용·세금 반영 여부, 과최적화 비판.
(3) 실적 발표일 주변 변동성(발표일 주가 변동폭의 예측 가능성, 과거 발표일 변동폭의 지속성), 포트폴리오 위험 관리에 쓰는 방법.
끝에 각 연구의 '사전 등록할 가설·반증 조건' 제안 3줄씩."""),
 'A': ('g2_audit', 'cro', """[감사] 너는 CRO다. 아래 연구의 코드와 결과를 반대 심문하라. (1) 미래 정보 누수(시점), (2) 생존·선택 편향, (3) 다중검정·사후 변경,
(4) 비용·체결 가정, (5) 데이터 소스의 실전 사용 가능성(약관). 각 항목: 문제 / 심각도(상중하) / 확인 방법 / 결론에 미치는 영향. 마지막에 통과·조건부·실패 판정."""),
 'D': ('g2_digest', 'editor', """[다이제스트] 아래 연구 결과를 투자 비전문가도 이해할 수 있게 10줄 이내로 요약하라. 숫자는 원문 그대로, 과장하지 말 것.
'그래서 내 포트폴리오에 무엇이 달라지나'를 마지막 2줄에."""),
}
key = sys.argv[1]; route, role, task = TASK[key[0]] if key[0] in 'AD' else TASK[key]
ctx = '\n\n'.join(f'### {Path(f).name}\n' + Path(f).read_text()[:60000] for f in sys.argv[2:])
t0 = time.time()
try:
    r = router.run(route, RULES + '\n\n' + task + ('\n\n[자료]\n' + ctx if ctx else ''), role=role, tools=None, log_path=OUT / f'G2_{key}.log.json')
    text, model, sub = r['text'], r['model'], r['substituted']
except router.AllDown as e:
    text, model, sub = f'ALL DOWN: {e}', None, None
(OUT / f'G2_{key}.md').write_text(f'<!-- {key} · 모델 {model} · 대체 {sub} · {round((time.time()-t0)/60,1)}분 -->\n' + text)
print(key, model, sub, len(text))
