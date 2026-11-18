# TASK_calc_hindsight — 고정 방식(미래 정보 미제거) 비교 독립 재계산 (Antigravity)
목적: out/hindsight_compare.csv 의 밸류에이션 6행(KOSPI PER/PBR, SP500 PER/PBR, KOSDAQ PER/PBR)을 **src/ 를 읽지 않고** 재계산·대조. 코드 calc6/, 결과 calc6/out/. 다른 파일 수정 금지.
데이터: data/kospi_per_pbr_krx.csv(월말 PER/PBR, '-' 결측), data/agy/kosdaq_per_pbr.csv(PER은 2010-08 이후만), data/spdji/shiller_ie_data_2026.xls(S&P PER: 분기 말 E만, 분기 말 + 3개월 뒤부터, Yahoo 월말 종가 ÷ E), data/spx_pbr_q.csv(+3개월 지연, 직전 값 유지), data/yh_*.json.
두 방식: rolling = 직전 120개월 평균/σ(최소 96), fixed = 그 지표 전체 표본 평균/σ(ddof=1). 나머지는 PREREG 3·4절: 월말 신호 → 다음 달 첫 거래일 종가, NW t(log 12개월, lag 12), 후반부 t(12개월 확정 월만 반으로), 비중표 전략 편도 5bp Sharpe vs 상수 60%, 순환 플라시보(12..N−12), 확정 에피소드(6개월 간격), 판정(J1 t≤−2 & |t|≥2.73, J2 확정 에피소드 과열/저평가 각 ≥3, J3 Sharpe>상수 & 플라시보≥90%, J4 후반부 음수; J1·J4만 & J2 실패 = 판정 보류).
특히 확인: fixed에서 KOSPI PBR이 J1~J4 모두 통과(시그널)하는지, 그 이유가 미래 정보인지 표본 기간 차이(고정은 워밍업 없음)인지 — fixed를 rolling과 같은 시작월로 잘라서도 계산.
산출: calc6/out/recalc.csv, calc6/out/diff.md.
