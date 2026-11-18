# TASK_calc_spx — S&P500 PER(쉴러 분기 말 이익) 독립 재계산 (Antigravity)
목적: out/spx_pe_shiller_stats.csv 를 **src/ 를 읽지 않고** PREREG.md 3·4·10절만으로 재계산·대조. 코드 calc5/, 결과 calc5/out/. 다른 파일 수정 금지.
데이터: data/spdji/shiller_ie_data_2026.xls (시트 Data, 8행부터: 날짜(1871.01 형식, 2026.1 = 10월 주의), P, D, E ...), data/yh_GSPC.json.
정의: 분기 말 달(3·6·9·12)의 E만 사용, 분기 말 + 3개월 뒤 월부터 적용(중간 직전 값 유지). PER = Yahoo 월말 종가 ÷ 적용 E. z = 직전 120개월 롤링(최소 96, ddof=1). 월말 신호 → 다음 달 첫 거래일 종가 체결. NW t(log 12개월, lag 12), 후반부 t(12개월 수익률 확정 월만 반으로), 비중표 전략(편도 5bp) Sharpe·상수 60%·순환 플라시보, 확정 에피소드, +1개월 지연, 지연 2·4개월 변형. 판정(J1~J4, |t|≥2.73)도 독립적으로.
산출: calc5/out/recalc.csv, diff.md (|Δ| > 0.1 t·Sharpe, > 1%p 수익률 → 원인).
