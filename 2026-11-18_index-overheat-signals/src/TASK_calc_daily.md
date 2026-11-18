# TASK_calc_daily — 일간·단기 독립 재계산 (Antigravity)
목적: out/daily_events_test.csv, out/daily_strategy.csv, out/daily_pbr_approx_check.csv 를 **src/ 를 읽지 않고** PREREG.md 3·9절 정의만으로 재계산·대조. 코드 calc4/, 결과 calc4/out/ 에만. 다른 파일 수정 금지.
데이터: data/yh_{GSPC,NDX,SOX,KS11,KQ11}.json, data/kospi_per_pbr_krx.csv(일간, '-' 결측), data/agy/kosdaq_per_pbr.csv(월말).
정의 요약: 이격도 = 종가/200일 SMA − 1. KOSPI PBR = KRX 일간(>0), 가격은 Yahoo KS11. KOSDAQ PBR 일간 = 직전 월말(PBR/KRX 종가) × 당일 Yahoo KQ11 종가. z = 직전 2,520거래일 롤링(최소 2,000, ddof=1, 당일 포함).
이벤트: −1 하향 돌파(z[t−1] > −1 ≥ z[t]) 매수, +1 상향 돌파 매도, 2차 ±2. 같은 종류 직전 60거래일 이내면 제외(직전 '채택된' 이벤트 기준). 수익 = log(P[t+1+h]/P[t+1]), h=5·20·60. 초과 = 이벤트 평균 − 전체 유효일 평균. 무작위 날짜 동일 개수 10,000회 → 한쪽 p(매수: 귀무 ≥ 관측 비율). 후반부 = 이벤트 시간순 뒤 절반의 초과수익.
일간 전략: 비중표(z≤−2 1.0/−2~−1 0.8/중립 0.6/+1~+2 0.4/≥+2 0.2), w_t 는 t+1 종가 체결 → t+2 일간수익에 적용, 비용 |Δw|×5bp(10bp 민감도). 상수 = 평균 비중 × 지수수익. Sharpe √252. 플라시보 = w 순환 이동 k=252..N−252 (21일 간격) Sharpe 중 전략 미만 비율. 연 회전율 = Σ|Δw| / 연수.
판정(D1~D4, 한쪽 p < 0.0036, 이벤트 ≥ 8)을 독립적으로 내려 비교. 산출: calc4/out/recalc_events.csv, recalc_strategy.csv, diff.md(|Δ| > 0.2%p 수익, > 0.02 p, > 0.05 Sharpe, 이벤트 수 차이 → 원인).
