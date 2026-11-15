# 아이디어: 연기금 리밸런싱 선행매매 (월말 주식-채권 리밸런싱 압력)

- 출처: Campbell Harvey, Michele Mazzoleni, Alessandro Melone, "The Unintended Consequences of Rebalancing", NBER Working Paper 33554 (2025). https://www.nber.org/papers/w33554
  - EDHEC 발표 슬라이드(2026-03): https://www.edhec.edu/sites/default/files/2026-03/slides_EDHEC_Michele%20Mazzoleni%20%281%29.pdf
  - CFA Institute 블로그 요약(2025): https://rpc.cfainstitute.org/blogs/enterprising-investor/2025/rebalancings-hidden-cost-how-predictable-trades-cost-pension-funds-billions
- 요지(2차 자료 기준): 약 20조 달러의 연기금·TDF가 고정 목표비중 리밸런싱(월말/분기말 달력 방식, 임계치 방식). 주식이 과체중이면 매도 → 다음날 주식 수익률 -17bp, 압력은 2주 내 대부분 해소. 모멘텀·반전으로 설명 안 됨. 연간 비용 약 160억 달러(8bp).
- 개인 투자자 적용 질문: 월(또는 분기) 중 주식이 채권보다 많이 오른 경우 월말 직전~직후 주식 비중을 줄이고(채권/현금), 반대면 늘리는 규칙이 SPY 보유 대비 위험조정 수익을 높이는가?
- 데이터: fund.us('SPY'), fund.us('TLT'), fund.us('IEF') (2002-07 이후). 원문 신호 정의(주식-채권 상대 성과 측정 구간, 진입·청산 일자)는 원문에서 확인해 그대로 쓸 것.
- 제안자 메모: 월말 효과(turn-of-the-month) 와 겹칠 수 있으니 분리해서 볼 것.
