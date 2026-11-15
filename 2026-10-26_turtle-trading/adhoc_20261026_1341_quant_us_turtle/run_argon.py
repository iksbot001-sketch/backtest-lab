import sys, json; sys.path.insert(0, '~/agent-fund'); import router
spec = router.CFG['tiers']['argon']
task = ("너는 GF's AI Hedge Fund의 퀀트다. 대표가 직접 맡긴 일이다. 지시서 ~/agent-fund/runs/adhoc_20261026_1341_quant_us_turtle/BRIEF.md 를 먼저 읽고 그대로 수행하라. "
        "모든 산출물은 ~/agent-fund/runs/adhoc_20261026_1341_quant_us_turtle 안에 저장하고, 끝나면 무엇을 했고 결론이 무엇인지 5줄 이내로 보고하라.")
r = router._agy(spec, task, 'quant', ['Bash'], '~/agent-fund/runs/adhoc_20261026_1341_quant_us_turtle', '~/agent-fund/runs/adhoc_20261026_1341_quant_us_turtle/agy_log.json')
print(json.dumps({'ok': r['ok'], 'text': r['text']}, ensure_ascii=False, indent=1))
