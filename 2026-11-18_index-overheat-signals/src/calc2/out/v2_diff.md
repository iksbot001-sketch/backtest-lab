# diff: 독립 재계산(calc2) vs Claude(out/disp_stats.csv, disp_zones.csv)

가정: 월별 비중=월말 z, 다음달 첫거래일 종가→그 다음달 첫거래일 종가 보유, 비용 편도5bp×|Δw|(초기 진입 포함), 현금 0%, Sharpe=월수익 평균/σ×√12. 절반=신호월 수//2 이후. 플라시보=비중열 순환이동(|이동|≥12개월) 후 Sharpe 분포 중 strat 미만 비율. NW=Bartlett, 소표본 보정 없음, 절편 포함.

비교 10행×17지표, 허용오차 초과 20건

|시장|모드|지표|재계산|Claude|차이|
|--|--|--|--|--|--|
|SP500|rolling|nw_t3|0.9002|0.7594|+0.1408|
|SP500|rolling|t_first_half|1.0593|1.0127|+0.0466|
|SP500|rolling|n|325.0000|326.0000|-1.0000|
|SP500|fixed|t_first_half|2.3227|2.1159|+0.2068|
|SP500|fixed|n|420.0000|421.0000|-1.0000|
|NASDAQ100|rolling|n|325.0000|326.0000|-1.0000|
|NASDAQ100|fixed|nw_t3|1.1936|1.0718|+0.1218|
|NASDAQ100|fixed|t_first_half|1.2134|1.0699|+0.1435|
|NASDAQ100|fixed|n|420.0000|421.0000|-1.0000|
|SOX|rolling|t_first_half|0.0537|-0.0841|+0.1378|
|SOX|rolling|n|273.0000|274.0000|-1.0000|
|SOX|fixed|n|368.0000|369.0000|-1.0000|
|KOSPI|rolling|t_first_half|-2.1668|-2.1313|-0.0355|
|KOSPI|rolling|n|239.0000|240.0000|-1.0000|
|KOSPI|fixed|bh_cagr|0.0979|0.0877|+0.0102|
|KOSPI|fixed|n|336.0000|337.0000|-1.0000|
|KOSDAQ|rolling|t_first_half|-4.4070|-4.4943|+0.0873|
|KOSDAQ|rolling|n|193.0000|194.0000|-1.0000|
|KOSDAQ|fixed|t_first_half|-2.6740|-2.6559|-0.0181|
|KOSDAQ|fixed|n|290.0000|291.0000|-1.0000|

## 구간표 (months/episodes 정수차, 수익률·확률 1%p)
비교 60행, 초과 46건

|시장|모드|구간|지표|재계산|Claude|차이|
|--|--|--|--|--|--|--|
|SP500|rolling|-2<Z<=-1|months|38.0000|39.0000|-1.0000|
|SP500|rolling|-2<Z<=-1|episodes|9.0000|10.0000|-1.0000|
|SP500|rolling|-2<Z<=-1|up12|0.4595|0.4737|-0.0142|
|SP500|rolling|neutral|months|237.0000|238.0000|-1.0000|
|SP500|rolling|ALL|months|337.0000|339.0000|-2.0000|
|SP500|fixed|-2<Z<=-1|months|40.0000|41.0000|-1.0000|
|SP500|fixed|-2<Z<=-1|episodes|9.0000|10.0000|-1.0000|
|SP500|fixed|neutral|months|326.0000|327.0000|-1.0000|
|SP500|fixed|ALL|months|432.0000|434.0000|-2.0000|
|NASDAQ100|rolling|-2<Z<=-1|months|25.0000|26.0000|-1.0000|
|NASDAQ100|rolling|-2<Z<=-1|episodes|9.0000|10.0000|-1.0000|
|NASDAQ100|rolling|neutral|months|249.0000|250.0000|-1.0000|
|NASDAQ100|rolling|ALL|months|337.0000|339.0000|-2.0000|
|NASDAQ100|fixed|-2<Z<=-1|months|22.0000|23.0000|-1.0000|
|NASDAQ100|fixed|-2<Z<=-1|r3|0.0047|0.0200|-0.0153|
|NASDAQ100|fixed|-2<Z<=-1|r6|0.0348|0.0563|-0.0215|
|NASDAQ100|fixed|-2<Z<=-1|r12|0.1336|0.1572|-0.0236|
|NASDAQ100|fixed|-2<Z<=-1|up12|0.7273|0.7391|-0.0119|
|NASDAQ100|fixed|neutral|months|350.0000|351.0000|-1.0000|
|NASDAQ100|fixed|ALL|months|432.0000|434.0000|-2.0000|
|SOX|rolling|-2<Z<=-1|months|22.0000|24.0000|-2.0000|
|SOX|rolling|-2<Z<=-1|episodes|8.0000|10.0000|-2.0000|
|SOX|rolling|-2<Z<=-1|r6|0.2136|0.2241|-0.0105|
|SOX|rolling|-2<Z<=-1|r12|0.3981|0.4187|-0.0205|
|SOX|rolling|ALL|months|285.0000|287.0000|-2.0000|
|SOX|fixed|neutral|months|282.0000|284.0000|-2.0000|
|SOX|fixed|ALL|months|380.0000|382.0000|-2.0000|
|KOSPI|rolling|-2<Z<=-1|months|28.0000|29.0000|-1.0000|
|KOSPI|rolling|neutral|months|189.0000|190.0000|-1.0000|
|KOSPI|rolling|ALL|months|251.0000|253.0000|-2.0000|
|KOSPI|fixed|Z<=-2|months|8.0000|9.0000|-1.0000|
|KOSPI|fixed|Z<=-2|r6|0.2072|0.1581|+0.0490|
|KOSPI|fixed|Z<=-2|r12|0.6113|0.5201|+0.0912|
|KOSPI|fixed|Z<=-2|up12|0.8750|0.7778|+0.0972|
|KOSPI|fixed|-2<Z<=-1|months|30.0000|31.0000|-1.0000|
|KOSPI|fixed|-2<Z<=-1|episodes|8.0000|9.0000|-1.0000|
|KOSPI|fixed|ALL|months|348.0000|350.0000|-2.0000|
|KOSDAQ|rolling|Z<=-2|months|4.0000|5.0000|-1.0000|
|KOSDAQ|rolling|neutral|months|148.0000|149.0000|-1.0000|
|KOSDAQ|rolling|ALL|months|205.0000|207.0000|-2.0000|
|KOSDAQ|fixed|Z<=-2|months|9.0000|10.0000|-1.0000|
|KOSDAQ|fixed|-2<Z<=-1|months|30.0000|31.0000|-1.0000|
|KOSDAQ|fixed|-2<Z<=-1|episodes|8.0000|9.0000|-1.0000|
|KOSDAQ|fixed|-2<Z<=-1|r6|0.0501|0.0608|-0.0107|
|KOSDAQ|fixed|-2<Z<=-1|up12|0.6667|0.6429|+0.0238|
|KOSDAQ|fixed|ALL|months|302.0000|304.0000|-2.0000|

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