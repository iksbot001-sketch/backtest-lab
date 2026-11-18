# diff: 독립 재계산(calc2) vs Claude(out/disp_stats.csv, disp_zones.csv)

가정: 월별 비중=월말 z, 다음달 첫거래일 종가→그 다음달 첫거래일 종가 보유, 비용 편도5bp×|Δw|(초기 진입 포함), 현금 0%, Sharpe=월수익 평균/σ×√12. 절반=신호월 수//2 이후. 플라시보=비중열 순환이동(|이동|≥12개월) 후 Sharpe 분포 중 strat 미만 비율. NW=Bartlett, 소표본 보정 없음, 절편 포함.

비교 10행×17지표, 허용오차 초과 20건

|시장|모드|지표|재계산|Claude|차이|
|--|--|--|--|--|--|
|SP500|rolling|n_months|338.0000|337.0000|+1.0000|
|SP500|fixed|t_first_half|2.1456|2.1159|+0.0297|
|SP500|fixed|t_second_half|-4.3675|-4.2916|-0.0759|
|SP500|fixed|t3_second_half|-0.7083|-1.2205|+0.5122|
|SP500|fixed|n_months|433.0000|432.0000|+1.0000|
|NASDAQ100|rolling|n_months|338.0000|337.0000|+1.0000|
|NASDAQ100|fixed|t_first_half|1.1777|1.0699|+0.1078|
|NASDAQ100|fixed|t_second_half|-2.9753|-2.8001|-0.1752|
|NASDAQ100|fixed|t3_second_half|-0.9691|-1.3303|+0.3612|
|NASDAQ100|fixed|n_months|433.0000|432.0000|+1.0000|
|SOX|rolling|n_months|286.0000|285.0000|+1.0000|
|SOX|fixed|t_first_half|-1.3239|-1.3384|+0.0145|
|SOX|fixed|t_second_half|-1.8215|-1.7821|-0.0393|
|SOX|fixed|n_months|381.0000|380.0000|+1.0000|
|KOSPI|rolling|n_months|252.0000|251.0000|+1.0000|
|KOSPI|fixed|n_months|349.0000|348.0000|+1.0000|
|KOSDAQ|rolling|t_first_half|-4.4066|-4.4943|+0.0876|
|KOSDAQ|rolling|n_months|206.0000|205.0000|+1.0000|
|KOSDAQ|fixed|t_first_half|-2.6700|-2.6559|-0.0141|
|KOSDAQ|fixed|n_months|303.0000|302.0000|+1.0000|

## 구간표 (months/episodes 정수차, 수익률·확률 1%p)
비교 60행, 초과 23건

|시장|모드|구간|지표|재계산|Claude|차이|
|--|--|--|--|--|--|--|
|SP500|rolling|neutral|months|237.0000|238.0000|-1.0000|
|SP500|rolling|ALL|months|338.0000|339.0000|-1.0000|
|SP500|fixed|neutral|months|326.0000|327.0000|-1.0000|
|SP500|fixed|ALL|months|433.0000|434.0000|-1.0000|
|NASDAQ100|rolling|-2<Z<=-1|months|25.0000|26.0000|-1.0000|
|NASDAQ100|rolling|-2<Z<=-1|episodes|9.0000|10.0000|-1.0000|
|NASDAQ100|rolling|ALL|months|338.0000|339.0000|-1.0000|
|NASDAQ100|fixed|neutral|months|350.0000|351.0000|-1.0000|
|NASDAQ100|fixed|ALL|months|433.0000|434.0000|-1.0000|
|SOX|rolling|-2<Z<=-1|months|23.0000|24.0000|-1.0000|
|SOX|rolling|-2<Z<=-1|episodes|9.0000|10.0000|-1.0000|
|SOX|rolling|ALL|months|286.0000|287.0000|-1.0000|
|SOX|fixed|neutral|months|283.0000|284.0000|-1.0000|
|SOX|fixed|ALL|months|381.0000|382.0000|-1.0000|
|KOSPI|rolling|-2<Z<=-1|months|28.0000|29.0000|-1.0000|
|KOSPI|rolling|ALL|months|252.0000|253.0000|-1.0000|
|KOSPI|fixed|-2<Z<=-1|months|30.0000|31.0000|-1.0000|
|KOSPI|fixed|-2<Z<=-1|episodes|8.0000|9.0000|-1.0000|
|KOSPI|fixed|ALL|months|349.0000|350.0000|-1.0000|
|KOSDAQ|rolling|Z<=-2|months|4.0000|5.0000|-1.0000|
|KOSDAQ|rolling|ALL|months|206.0000|207.0000|-1.0000|
|KOSDAQ|fixed|Z<=-2|months|9.0000|10.0000|-1.0000|
|KOSDAQ|fixed|ALL|months|303.0000|304.0000|-1.0000|

## SOX 차트 검증 (1995-10-16~2026-11-09)
{
 "mean": 0.058172291469437434,
 "sd": 0.1850713153732256,
 "plus1": 0.24324360684266305,
 "minus1": -0.12689902390378816,
 "D_1109": -0.07448795369839267,
 "D_last": -0.11531697182702605,
 "last_date": "2026-11-17",
 "n": 7818.0
}
## 요약·원인 추정
- **핵심 수치 일치**: 12개월 NW t(nw_t), 3개월 NW t(nw_t3), 전략 CAGR/Sharpe/MDD, c60·B&H, 평균 비중, 플라시보 비율은 10개 시장×모드 전부 허용오차(t·Sharpe 0.1, 수익률 1%p) 이내. 판정(J1~J4)에 영향 없음.
- **초과 20건은 전부 '표본 경계 1개월' 문제**: 재계산은 z가 처음 산출되는 달(월말 값)부터 포함(예: SP500 rolling 1998-09), Claude는 다음 달(1998-10)부터. 그 결과 (a) n_months +1, (b) 표본 절반 분할 월이 1개월 어긋나 t_first/second_half·t3_second_half가 흔들림(최대 0.51, SP500 fixed t3 후반 −0.71 vs −1.22; 부호·결론 불변). 구간표 months 1개 차이도 같은 원인(또는 Claude 구간표가 2026-11 미완결 월을 포함한 듯: ALL이 n_months보다 2 큼 — 확인 필요).
- 첫 달 제외 변형(v2_*, 참고)으로 맞춰봐도 완전 일치하지 않음 → Claude의 경계 규칙이 문서화돼 있지 않음. PREREG에 '최초 z 산출월 포함 여부·절반 분할 기준(신호월 수//2 vs 수익률 보유월)'을 명시 권장.
- 모호 가정: NW는 소표본 보정 없는 Bartlett, 절반=신호월 수//2, 플라시보 shift는 |12|개월 이상, 비용은 초기 진입 포함.
- **SOX 차트 검증(7번)**: 1995-10-16~2026-11-09 D 평균 +5.8%(차트 5.8), +1σ +24.3%(24.3), −1σ −12.7%(−12.7), 2026-11-09 D −7.4%(차트 −7.5; 반올림 오차 0.05%p 수준 −7.449). 차트 완전 재현. 최신(2026-11-17) D = −11.5%.
- 산출: recalc.csv, recalc_zones.csv, ret_*.csv(일이 아닌 월 전략수익), sox_check.json, v2_*(첫달 제외 변형, 참고).
