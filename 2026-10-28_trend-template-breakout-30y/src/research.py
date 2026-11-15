"""웹 코멘트 조사를 Antigravity(텍스트 모드, 파일 쓰기·셸 없음)에 맡긴다. Claude → Gemini(Argon) 순."""
import sys
from pathlib import Path
RUN = Path(__file__).resolve().parent
sys.path.insert(0, str(RUN.parents[1]))
import router  # noqa: E402

PROMPT = """웹 검색으로 조사해 한국어로 정리하라(출처 URL 필수, 2,500자 이내).
주제: 미너비니 트렌드 템플릿(SEPA/VCP) + 52주 신고가 돌파 매수(-7% 손절, +15%에 본절 스탑, +25% 절반 익절, 20일선 이탈 청산) 같은 모멘텀 돌파 전략을
한국 주식(코스피·코스닥)에 체계적으로 적용했을 때의 실증·백테스트 결과와 실전 트레이더 코멘트.
1) 돌파 매매가 실패하는 대표 원인(가짜 돌파, 시장 국면, 갭, 유동성, 한국 시장의 상한가·테마 특성 등) — 근거·수치가 있는 것 위주
2) 미너비니·오닐(CAN SLIM)·스탠 와인스태인 본인이 강조한 조건 중 단순 기계 규칙에 빠지기 쉬운 것(시장 방향 M, 베이스/수축 패턴, 거래량 동반, 피벗 위치, 진입가와 피벗 거리 5% 이내 등)
3) 한국 시장에서 52주 신고가·모멘텀 효과에 대한 학술/퀀트 블로그 결과(모멘텀 붕괴, 단기 반전 등)
4) 개선 방법으로 제시된 것들과 그 근거
추측은 추측이라고 표시하라."""

for name, model in [('agy_claude', 'claude-sonnet-5-5-medium'), ('agy_gemini', 'gemini-4-argon-medium')]:
    if router.down(name):
        continue
    res = router._agy({'model': model}, PROMPT, None, False, None, RUN / f'research_{name}.log.json')
    if res['ok']:
        (RUN / 'WEB_RESEARCH.md').write_text(f'<!-- by {name} {model} -->\n' + res['text'])
        print('ok', name); break
    print('fail', name, res['text'][:300])
    if router.is_limit(res['text']):
        router.mark_down(name, res['text'][:200])
