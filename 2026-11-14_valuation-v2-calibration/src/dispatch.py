"""TASK_A(가치평가 엔진 v2 보정 백테스트)를 Antigravity에 맡긴다. 사용: venv/bin/python runs/adhoc_20261114_val2_calibration/dispatch.py"""
import sys
from pathlib import Path
RUN = Path(__file__).resolve().parent
sys.path.insert(0, str(RUN.parents[1]))
import router  # noqa: E402
prompt = (f"실행 폴더 {RUN} 의 TASK_A.md 를 읽고 그대로 수행하라. 이 폴더 밖은 읽지도 쓰지도 마라(데이터는 data/inputs.csv 에 있다). src/engine.py 는 고치지 마라. "
          "막히면 RUNLOG.md 에 BLOCKED: 이유. 최종 응답: 만든 파일, 검증 관문 결과, 관측 수, T1 합계 행.")
for name, spec in [('agy_argon', {'model': 'gemini-4-argon-medium'}), ('agy_sonnet', {'model': 'claude-sonnet-5-5-medium'})]:
    res = router._agy(spec, prompt, None, True, RUN, RUN / f'agent_A_{name}.log.json')
    print('A', name, res['ok'], res['text'][:3000], flush=True)
    if res['ok'] and (RUN / 'out/panel.csv').exists() and (RUN / 'REPORT.md').exists(): break
