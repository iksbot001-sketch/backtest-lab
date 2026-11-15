<!-- by agy_gemini gemini-4-argon-medium -->
**결론 요약**
미너비니 트렌드 템플릿(MTT)과 52주 신고가 돌파 전략을 한국 증시(코스피·코스닥)에 단순 기계적 규칙(이평선 정배열+신고가 매수+고정 손절/익절)으로만 적용하면 **승률 저하(30~40%대)와 잦은 손절(Whipsaw)로 포트폴리오가 우하향하기 쉽다.** 한국 시장은 **개인 투자자 중심의 단기 과열 후 반전(Short-Term Reversal), ±30% 상한가 제도에 따른 갭 왜곡, 테마주 설거지**가 빈번하기 때문이다. 반면, **마켓 타이밍(지수 이평선 필터), 유동성/실적 필터, 기관·외인 수급, 변동성 수축(VCP) 및 피벗 5% 이내 진입 규칙**을 결합한 백테스트(젠포트·퀀터스 등)에서는 **승률 40~50%, 연평균 수익률(CAGR) 20~25%, MDD -20~-25% 내외**의 유의미한 우상향 성과가 확인된다.

---

### 1. 한국 시장에서 돌파 매매가 실패하는 대표 원인 (근거·수치)
* **낮은 기본 승률과 가짜 돌파(Fakeout):** 추세추종 돌파 전략은 본래 승률이 **40~50% 미만**이며 손익비로 수익을 내는 구조다. 특히 코스닥 중소형주는 돌파 당일 대량 거래량과 함께 윗꼬리 장대음봉을 만드는 ‘설거지(고점 물량 떠넘기기)’가 빈번해 단순 고가 돌파 진입 시 손절(-7%) 도달 확률이 급증한다.
* **상한가 제도(±30%)와 시초가 갭(Gap) 왜곡:** 미국과 달리 가격제한폭(±30%)이 있어 호재 발생 시 매수세가 장중 건전한 수축 없이 상한가나 익일 대규모 **시초가 갭상승**으로 직행한다. 백테스트상 종가/돌파가 매수 가정과 실전 체결가 사이의 슬리피지(Slippage) 및 거래비용(수수료·거래세)이 수익률을 크게 훼손한다.
* **수급의 질적 차이(개인 단타·테마주):** 기관 뮤추얼펀드가 수개월간 매집하는 미국 성장주와 달리, 한국은 개인 신용·단타 자금이 주도하는 단발성 테마주 순환매가 빠르다. 외인·기관 수급이 없는 돌파는 직후 급락할 확률이 높다.

---

### 2. 대가들이 강조했으나 단순 기계 규칙에서 누락되기 쉬운 핵심 조건
* **시장 방향(CAN SLIM의 ‘M’, 와인스태인 Stage):** 오닐은 **“개별 종목 방향의 75%는 전체 시장(M)이 결정한다”**고 했고, 와인스태인과 미너비니 역시 지수가 하락(Stage 4) 또는 50일/200일선 아래일 때 돌파 매매 중단을 원칙으로 삼았다. 기계적 백테스트에서 시장 필터를 빼면 하락장 연속 손절로 MDD가 **-35~-40% 이상** 벌어진다.
* **베이스 내부의 변동성 수축(VCP)과 거래량 고갈(Dry-up):** 단순히 52주 신고가를 치는 것이 아니라, 돌파 직전 조정 폭이 단계적으로 줄어들고(예: **-20% → -10% → -5%**) 조정 구간에서 **거래량이 극도로 말라야(매도 물량 소진)** 한다.
* **돌파 시 거래량 폭발과 피벗(Pivot) 5% 이내 원칙:** 피벗 돌파 시 평소(50일 평균) 대비 **40~50% 이상 거래량이 폭증**해야 기관 유입으로 인정한다. 또한 오닐과 미너비니 모두 **피벗 포인트 대비 +5% 이상 급등(Extended)한 종목은 추격 매수를 엄격히 금지**한다(시초가 갭상승 추격 매수 시 -7% 손절선에 즉시 노출됨).
* **베이스 형성 단계(Base Count):** 상승 초기 1~2번째 베이스 돌파가 아닌, 이미 대중에게 노출된 3~4번째 후기 베이스 돌파는 실패 확률이 높다.

---

### 3. 한국 시장 52주 신고가·모멘텀에 대한 학술/퀀트 실증 결과
* **52주 신고가 모멘텀(PTH)의 우위:** George & Hwang(2004) 방법론을 한국 증시에 적용한 국내 재무학회 및 신한투자증권·KAIST 연구에 따르면, 단순 과거 누적 수익률 모멘텀보다 **‘52주 최고가 근접 비율(PTH)’**이 모멘텀 크래시(급락) 방어와 미래 초과수익 예측에서 통계적으로 더 우수하다. 특히 기관·외인 비중이 높은 **코스피(KOSPI) 대·중형주**에서 견고하다.
* **단기 반전(Short-Term Reversal)과 회전율의 역설:** 한국 주식시장 학술 연구(부산대·서울시립대 재무관리연구, KAIST 금융공학 논문 등)에 따르면 한국은 **직전 1개월 급등주가 익월 하락하는 ‘단기 반전’ 현상**이 매우 강하다. 특히 **거래회전율(Turnover)이 비정상적으로 과열된 종목**은 개인 투자자의 과잉반응과 유동성 압력으로 인해 돌파 직후 강한 되돌림(반전)이 발생한다.

---

### 4. 실전 트레이더 및 퀀트에서 검증된 개선 방법과 근거
1. **펀더멘털·수급·거래대금 필터 결합:** 단순 가격 돌파가 아닌 **영업이익/매출 성장(흑자)**, **외인·기관 순매수**, **최소 일평균 거래대금(예: 50억~100억 원 이상)** 조건을 결합하면 테마주 가짜 돌파가 걸러지며 연복리 수익률(CAGR)이 개선된다(국내 젠포트·퀀터스 백테스트 기준 CAGR 20%대, MDD -20%대 방어).
2. **코스피/코스닥 마켓 타이밍(MT) 적용:** 지수가 20일·60일 이동평균선 위에 있을 때만 진입하거나 하락장 현금 비중을 늘리면 횡보·하락장 연속 손절을 피할 수 있다.
3. **단기 과열 배제 및 돌파 후 눌림목(Pullback) 진입:** 한국 특유의 시초가 갭상승 후 음봉 및 단기 반전을 피하기 위해, 돌파 당일 추격 매수 대신 **피벗 돌파 후 거래량이 줄며 돌파선(또는 10일·20일선)을 지지하는 첫 눌림목에 진입**하는 방식이 실전 승률을 높인다는 트레이더 코멘트가 지배적이다(이 중 ‘눌림목 진입이 돌파 진입보다 구체적으로 승률을 몇 %p 개선하는지’에 대한 단일 표준 수치는 조건마다 달라 정량화하기 어렵다 — *추측/일반론 구분*).

---

### 참고 및 출처 URL
* KAIST 금융공학/경영공학 52주 고가 비율(PTH) 및 거래회전율·모멘텀 실증 논문:
  * [kaist.ac.kr 논문 리포지터리 1](https://vertexaisearch.cloud.google.com/grounding-api-redirect/AUZIYQFIGeSFfMYJukreC4nMlnBb3xVs5xtubUqgnaKsqYczOfjixY37tLrhU94IMT0UvnynW3h2n5NFB2enJmvTiTMnIsPJLHwvBWz1Ut9WkdVQC-3UR4ASdV-086HiENBcuNmTUig_)
  * [kaist.ac.kr 논문 리포지터리 2](https://vertexaisearch.cloud.google.com/grounding-api-redirect/AUZIYQGaI6vXVW2pSnlHiSw6LdjXhhTdmcbDlsmCDLhIcapasDEZCMaqpozfiZoQhldhyWVMIpYuPEnROCoqpPLRZHKCR060nBRMqnN386nSybqN-lWbwDYFJx8qCK25hzQDU6AXoTo=)
* 한국 주식시장 52주 최고가·단기반전 학술 연구(DBpia / 신한투자증권 리서치):
  * [dbpia.co.kr 단기반전 현상 연구](https://vertexaisearch.cloud.google.com/grounding-api-redirect/AUZIYQGna7XqxmlLGfCWyIUtvu2BmkPsCLNWsxYzbgb5bTsre_eb4R4xbt-ErkItfQHC4pzASDLzoyqtJQy4cSIoSX_OV755v8oB_SDXuxYNs9VmfrXNdjRCfAk_0A5Om_IU_g6IHXIk_RuW-IZltBNmm7ecOxuLS_AXgw==)
  * [dbpia.co.kr 52주 최고가 모멘텀 연구](https://vertexaisearch.cloud.google.com/grounding-api-redirect/AUZIYQF7lOjjt7ERpxnXluqXLn5Hs_MIMxMHjZs7ffYLf94QAzLm2Jceqadq9E1BgAIvrJ-onCa7Gbf5Ttr71xRjx7jwFNW-14I2d7B2YeLWBM2eUzRETO0297i6zwHLRbhlILxh6RYo1zVElQkhgEUZpK6knbaAdHAe)
  * [sks.co.kr 52주 신고가 퀀트 리포트](https://vertexaisearch.cloud.google.com/grounding-api-redirect/AUZIYQGsjYpSKV4NYye9tlkBxA9dCiaxeTcVsNzdDEzBudRopLA2H2A_d5s2RC7755ck9UKK2XOwaXtDahqNzvnfdPuoBboz9Ph4wP6SKZIlnMkqdmgM--T18Qul0r0rVP7U1ut4W-opPU9g428XRGv9t6Ypvj24_MHfiSQ0jri9QsQ=)
* 국내 퀀트 플랫폼(퀀터스·젠포트) 트렌드 템플릿 및 신고가 백테스트 분석:
  * [quantus.kr 미너비니 트렌드 템플릿 가이드](https://vertexaisearch.cloud.google.com/grounding-api-redirect/AUZIYQHhHtXYJ2rH_6hQpbzF9y8OFpeKIxe_LcdKvRdVsu6p9rNuRx4uXSFo8_XoTfukYXpv1hsv6sessMjNRvwxL6RSYEzYeZIVziWceiqOb1ypPF7kHzIt6iXGDYirfNSVXY-RzPvVgA==)
  * [tistory.com 젠포트 트렌드 템플릿 백테스트](https://vertexaisearch.cloud.google.com/grounding-api-redirect/AUZIYQEj7vDMdCK1MsIw0LnqZS_S1ydH7y6vbL4KwS69GdkOfnquhtRmBrnCxuS9cyqA2GB9jN-R4ueK_DDXBIjTMXFpIsLtn6dEWbjdUoZmC8pL26hoxYTBnw==)
  * [tistory.com 한국 시장 52주 신고가 백테스트](https://vertexaisearch.cloud.google.com/grounding-api-redirect/AUZIYQG5UK92Tzmcsxdb6PozzmUYW-fJDJEsbF-ZwKy0IEOHqFo2yBTtVMQg8M_3162EGCr0GfsDOTrdsTMYXmSI4Rx6ZhRWzTgYunczhmJa1NQDXN3p12PQWXCBsnAmNr8gK9-Z7GPRADUDrzaE9SK_KEGd4W10L_yDVC0S6H4ieCOnzXhNh39bT_Tcj7vKMOz44_7vWXW7vjcSmqoCHjltlNTcIhLFrg1ZvIvonD286NE5vNQUBVQS_e0qzBGIHy6vfjPITuEE4yZSBnJCdIaJKDXykVe2lKxcbu5CpwSeWIExR_MQ-_elU2UcfXySAQKc9kc-v3cUd343GF0dWXiWiEqPG2cwvUDLX20jC4fz63XAs7HoCZu3Q02KjhyTR033rUq9KClU8MmHMQoHjAerfJGYZJCwv6wM8L4bs-QfdsSKeRrEduJET-MaYfv3zKcYsZgLKQ65g-2pbfzMhVDna-iN5jVXT1NRdMn2Rj5g4Es_qhHghriOp8JAV7eQUjcWyw==)
* 미너비니 VCP / CAN SLIM / 와인스태인 원칙 정리:
  * [traderlion.com VCP & CAN SLIM Guide](https://vertexaisearch.cloud.google.com/grounding-api-redirect/AUZIYQFJrQEc5C7yNrOy5SxjoaQfEkRMuRsyijQCVU82exwZQ-kWIX3Y5ur7MerFB3DBJXBdZ3VTY__o0SlBraMtud-quNt0bXJmuuMZsAK79uOUg914sBmapGG-GXc11FLqwom9bJV6ZIGcB7q6_zwU34vo46hpVrmJb4WfTuN9iaH1)
  * [finermarketpoints.com VCP Volume & Contraction](https://vertexaisearch.cloud.google.com/grounding-api-redirect/AUZIYQHn-MlKbXSVi0V9qHoDVomRiesaK5hmboVroo7pBdL2MiTJE5Wa-NOVzaLNFeui1BjKrRpDf-TpRec_GjDMxXEBMsGpZF0aOP5YDchbeBEzrE8NArRgOEodT1uPrjD85i-v_jXoLC5eBe9sBjMZIFPsF_Jxg-YeMCIjQDoetl770L2ahtHYNV_kPR94O714uMu7XxfUHAPKoHDHKzDUtjpG4_yh9nn4ecA_jz_i)
