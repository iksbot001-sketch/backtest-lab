# TASK_calc — 독립 재계산 (Antigravity)

목적: Claude 결과(out/stats.csv, out/zones.csv, out/overlay.csv)를 **src/ 코드를 읽지 않고** PREREG.md 정의만으로 다시 계산해 대조한다.
코드는 `calc/` 에만 쓰고, 결과는 `calc/out/` 에만 쓴다. 다른 파일 수정 금지. 인터넷 불필요(data/ 만 사용).

## 데이터
- data/kospi_per_pbr_krx.csv (date,close,per,pbr; '-'는 결측) — 월말 값 사용
- data/spx_pe_m.csv (date,pe; 같은 달 중복 행은 마지막 값) — **1개월 추가 지연**
- data/spx_pbr_q.csv — 월 단위로 바꾼 뒤 **3개월 지연**, 그 사이 월은 직전 값 유지
- data/yh_GSPC.json, yh_KS11.json, yh_VIX.json (Yahoo chart JSON: timestamp, indicators.quote[0].close)
- data/fred_DFF.csv

## 계산 (PREREG 2~3절 그대로)
1. z = (V − 직전 120개월 평균)/직전 120개월 표준편차(최소 96개월). 표준편차는 표본표준편차(ddof=1).
2. 체결가 = 각 월 첫 거래일 종가. 신호월 t의 h개월 수익률 = 체결가[t+1+h]/체결가[t+1] − 1.
3. 12개월 로그수익률 ~ z 회귀, Newey-West(Bartlett, lag 12) t값.
4. 구간별(PREREG 구간) 월 수, 12개월 평균수익률, 상승확률.
5. 비중 전략(PREREG 비중표, 편도 5bp) CAGR·Sharpe·MDD, B&H 대비.
6. VIX 월 최고 ≥30 인 달의 12개월 평균수익률(S&P500, KOSPI).

대상: KOSPI PER, KOSPI PBR, SP500 PER, SP500 PBR.

## 산출
`calc/out/recalc.csv`(지표별 값) 와 `calc/out/diff.md`: Claude 값과 비교표, |차이| > 1%p(수익률) 또는 > 0.1(t·Sharpe) 항목은 원인 추정.
모호한 점은 임의로 정하지 말고 QUESTIONS_calc.md 에 적고 가정을 명시한다.
