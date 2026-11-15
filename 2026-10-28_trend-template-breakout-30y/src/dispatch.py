"""SPEC.md 구현을 펀드 표준 경로(router._agy, --sandbox: 쓰기는 이 실행 폴더만)로 맡긴다.
순서: Antigravity Claude → Antigravity Gemini(Argon)."""
import sys
from pathlib import Path

RUN = Path(__file__).resolve().parent
sys.path.insert(0, str(RUN.parents[1]))
import router  # noqa: E402  (읽기·호출만)

PROMPT = f"""실행 폴더 {RUN} 의 SPEC.md 를 읽고 그대로 구현·실행하라.
- 코드는 src/bt.py, 산출물은 out/, 기록은 RUNLOG.md. 이 폴더 밖에는 쓰지 마라.
- 파이썬은 ~/agent-fund/venv/bin/python. 실행이 오래 걸리면 먼저 5년 기간 변형 A만 돌려 검증한 뒤 전체를 돌려라.
- 샌드박스 때문에 ~/agent-fund-data 를 읽지 못하거나 네트워크가 막히면, 코드만 완성하고 RUNLOG.md 에 'BLOCKED: 이유'를 적고 끝내라.
- 명세와 다르게 구현한 곳이 있으면 RUNLOG.md 에 전부 적어라.
- 최종 응답: 무엇을 만들었고, 무엇을 돌렸고, summary.csv 요약, 자체 검증 결과, 막힌 것."""

for name, spec in [('agy_claude', {'model': 'claude-sonnet-5-5-medium'}),
                   ('agy_gemini', {'model': 'gemini-4-argon-medium'})]:
    if router.down(name):
        print(name, '한도 상태로 건너뜀'); continue
    res = router._agy(spec, PROMPT, None, True, RUN, RUN / f'agent_{name}.log.json')
    print(f'== {name} ok={res["ok"]}\n{res["text"][:6000]}', flush=True)
    if res['ok']:
        break
    if router.is_limit(res['text']):
        router.mark_down(name, res['text'][:200])
