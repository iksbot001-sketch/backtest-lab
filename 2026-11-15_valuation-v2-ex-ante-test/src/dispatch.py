"""TASK.md 를 router.agy_task('bt_calc') 로 맡긴다. 착수 전 핑으로 잔여 한도를 확인하고, 한도에 걸리면 체인 다음 모델로 넘긴다."""
import sys, json
from pathlib import Path
RUN = Path(__file__).resolve().parent
sys.path.insert(0, str(RUN.parents[1]))
import router
prompt = f"실행 폴더 {RUN} 의 TASK.md 를 읽고 그대로 수행하라. 최종 응답: 만든 파일, 검증 관문 결과, H1~H3, 평균 IC."
res = router.agy_task('bt_calc', prompt, RUN)
print(json.dumps({'ok': res['ok'], 'model': res['model'], 'picked': res['picked_log'], 'tried': res['tried']}, ensure_ascii=False))
print(res['text'][:4000])
