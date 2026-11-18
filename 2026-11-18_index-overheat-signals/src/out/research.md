요청하신 4개 지표의 무료 공개 시계열 데이터 확보 가능 여부 및 상세 명세입니다.

---

### 결론 요약
1. **코스닥(KOSDAQ) 지수 PER·PBR**: **확보 가능 (단, 2025년 이후 KRX 회원가입·로그인 세션 또는 Open API 키 필수)** — `data.krx.co.kr` `[11007]` 화면 내부 JSON/OTP 엔드포인트.
2. **나스닥 100 / 나스닥 종합 PER·PBR (2000년대~ 월별)**: **무료 직접 다운로드(CSV/JSON/HTML 표) 확보 불가** — 상용 라이선스 제약으로 2000년대 이후 전체 시계열을 비로그인 무료 배포하는 원본·공식 소스가 없음(최근 일부 구간 또는 유료 구독만 존재).
3. **S&P 500 및 KOSPI 12개월 선행(Forward) PER (2000년대~ 월별)**:
   - **S&P 500 12M Forward PE**: **차트 PDF는 무료 확보 가능(Yardeni), 정형 수치(CSV/JSON/HTML 표)는 확보 불가** (Multpl·GitHub 공개본은 모두 Trailing/Shiller PE임).
   - **KOSPI 12M Forward PER**: **확보 불가** (FnGuide·Bloomberg 유료 컨센서스 영역).
4. **CNN Fear & Greed Index 일별 시계열**: **확보 가능** — GitHub 오픈소스 아카이브(`whit3rabbit/fear-greed-data` 등)에서 Raw CSV 직접 다운로드 가능.

---

### 1. KOSDAQ 종합지수 PER · PBR 시계열

* **URL**:
  * **화면 URL**: `http://data.krx.co.kr/contents/MDC/MDI/mdiLoader/index.cmd?menuId=MDC0201010107` (메뉴 `[11007] 통계 > 기본통계 > 지수 > 주가지수 > PER/PBR/배당수익률`)
  * **JSON 데이터 요청 URL (POST)**: `http://data.krx.co.kr/comm/bldAttendant/getJsonData.cmd`
  * **CSV/Excel 다운로드 URL**:
    1. OTP 발급 (POST): `http://data.krx.co.kr/comm/fileDn/GenerateOTP/generate.cmd`
    2. 파일 수신 (POST): `http://data.krx.co.kr/comm/fileDn/download_csv/download.cmd` (파라미터 `code=<발급받은 OTP>`)
* **POST Form 파라미터 (개별지수 추이 기준)**:
  * `bld`: `dbms/MDC/STAT/standard/MDCSTAT00702` (전 지수 일자별 조회는 `MDCSTAT00701`)
  * `locale`: `ko_KR`
  * `searchType`: `P` (개별추이) / `A` (전체지수)
  * `indIdx`: `2` (코스닥 시장 구분 코드; 코스피는 `1`, KRX는 `5`)
  * `indIdx2`: `001` (코스닥 종합지수 세부 코드; `pykrx` 티커로는 `2001`에 해당)
  * `strtDd`: `YYYYMMDD` (예: `20000104`)
  * `endDd`: `YYYYMMDD` (예: `20261118`)
  * `share`: `1`, `money`: `1`, `csvxls_isNo`: `false`
* **수록 기간 및 주기**: **2000년 1월 ~ 현재 / 일별(Daily)**
* **산출 정의**:
  * 확정 실적(직전 사업연도 정기주주총회 확정 재무제표 기준, 매년 5월 초 일괄 반영) 기반 **Trailing(후행) 지수 PER · PBR**.
  * 지수 편입 종목의 시가총액 합계를 당기순이익 합계(PER) 및 자본총계 합계(PBR)로 나눈 값(적자 기업·자본잠식 기업은 산출 기준에 따라 합산에서 제외되거나 0 처리될 수 있음).
* **접근 제한 (로그인 필수 여부)**:
  * **현재 로그인 필수**: KRX 정보데이터시스템이 회원제(Data Marketplace)로 개편되면서, 비로그인 상태로 `getJsonData.cmd`나 `GenerateOTP`를 호출하면 응답으로 `"LOGOUT"` 또는 `401/403`을 반환합니다.
  * 무료 회원가입 후 로그인 세션 쿠키(`JSESSIONID`)와 `Referer: http://data.krx.co.kr/contents/MDC/MDI/mdiLoader/index.cmd?menuId=MDC0201010107`, `User-Agent` 헤더를 포함해야 호출 가능하며, 과도한 단기 반복 요청 시 IP가 차단됩니다.
* **신뢰도 주의사항**:
  * KRX 공식 확정치이나, 분기 실적(TTM)이 아닌 **연간 사업보고서 확정 실적 기준**이므로 매년 5월 초 재무제표 교체일에 PER·PBR 수치가 계단식으로 급변(불연속 점프)하는 왜곡이 있습니다.

---

### 2. NASDAQ-100 (또는 NASDAQ Composite) PER · PBR (2000년대~ 월별)

* **확보 여부**: **확보 불가** (2000년대부터 이어지는 무료·비로그인 CSV/JSON/고정 HTML 테이블 없음)
* **대안 소스별 현황 및 한계**:
  * **Siblis Research** (`https://siblisresearch.com/data/nasdaq-100-pe-ratio/`): 웹페이지 HTML 표로 일부 요약 수치만 공개하며, 2000년대 이후 전체 월별/분기별 시계열(Trailing/Forward PE, CAPE, PBR) 원본 엑셀/CSV는 유료 구독 전용입니다.
  * **World PE Ratio** (`https://worldperatio.com/index/nasdaq-100/`): 최근 수치와 단기 밴드 요약만 무료 표시하며, 20년 이상 장기 시계열 테이블이나 무료 CSV 다운로드 기능은 로그인/유료 플랜으로 제한됩니다.
  * **GuruFocus / MacroMicro**:
    * GuruFocus (`https://www.gurufocus.com/economic_indicators/6778/nasdaq-100-pe-ratio`): 시계열 다운로드 및 장기 데이터 열람에 유료 멤버십·로그인 필요.
    * MacroMicro (`https://en.macromicro.me/series/22223/nasdaq-100-pe-ratio`): 차트 열람 및 CSV 다운로드를 위해 회원가입·로그인이 필요함.
* **산출 정의 (제공처별 차이 주의)**:
  * 공식 지수 산출기관(Nasdaq / Bloomberg) 기준은 편입 종목 전체의 시가총액 합계를 TTM(직전 12개월) 순이익 합계(적자 기업 포함 합산, 즉 Aggregate Market Cap / Aggregate Net Income)로 나눈 **시가총액 가중 조화평균(Aggregate) 방식**입니다.
  * 반면 무료 웹 트래커(GuruFocus, 일부 ETF 페이지 등)는 `QQQ` ETF 기준 **흑자 기업만 필터링(Negative earnings 제외)**하여 가중평균을 내므로, 닷컴버블(2000~2002년)이나 적자 기술주 비중이 높을 때 공식 지수 PER과 20~50% 이상 괴리가 발생합니다.

---

### 3. S&P 500 및 KOSPI 12개월 선행(12M Forward) PER (2000년대~ 월별)

#### ① S&P 500 12-Month Forward P/E
* **확보 여부**:
  * **정형 데이터(CSV / JSON / HTML 테이블)**: **확보 불가** (무료·비로그인 공개본 없음)
  * **시각화 차트(PDF)**: **확보 가능 (Yardeni Research)**
* **URL**:
  * **Yardeni Research 차트북 PDF (무료·비로그인)**:
    * `https://yardeni.com/pub/stockmktperatio.pdf` (S&P 500 Forward P/E長期 추이 차트 수록)
    * `https://yardeni.com/pub/sp500earns.pdf` (S&P 500 12M Forward Consensus Operating EPS 시계열 차트)
  * **참고 (Trailing P/E만 필요한 경우 — Forward 아님)**:
    * Multpl HTML 표: `https://www.multpl.com/s-p-500-pe-ratio/table/by-month`
    * GitHub Raw CSV (Robert Shiller 데이터 미러): `https://raw.githubusercontent.com/datasets/s-and-p-500/main/data/data.csv`
* **수록 기간 및 주기**: Yardeni PDF 내 차트 기준 **1980년대 후반(2000년대 전체 포함) ~ 현재 / 주별·월별**
* **산출 정의**: S&P 500 지수 종가 ÷ I/B/E/S(LSEG/Refinitiv) 산출 S&P 500 향후 12개월(Time-weighted 52-week forward) 컨센서스 영업이익(Operating EPS) 합산치.
* **접근 제한 및 신뢰도 주의사항**:
  * I/B/E/S 및 FactSet의 과거 시점별(Point-in-Time) 컨센서스 추정치 원시 수치 데이터는 엄격한 유료 라이선스 대상이어서, Yardeni나 FactSet Earnings Insight(`https://advantage.factset.com/hubfs/Website/Resources%20Section/Research%20Desk/Earnings%20Insight/` 하위 주간 PDF) 모두 **PDF 이미지/벡터 차트 형태**로만 무료 공개하며 수치 테이블(CSV/XLS)은 배포하지 않습니다.
  * `multpl.com` 및 `datasets/s-and-p-500` GitHub 저장소는 **12개월 후행(Trailing GAAP) PER 및 10년 CAPE**만 수록하고 있으며, 선행(Forward) PER은 없습니다.

#### ② KOSPI 12-Month Forward PER
* **확보 여부**: **확보 불가**
* **사유 및 한계**:
  * 국내 지수 12개월 선행 PER은 에프앤가이드(FnGuide DataGuide), 와이즈리포트(WiseReport), 블룸버그(Bloomberg) 등이 국내 증권사 컨센서스(향후 4개 분기 가중 지배주주순이익 합계)를 집계해 산출하는 **유료 독점 데이터**입니다.
  * KRX 정보데이터시스템(`data.krx.co.kr`)이나 공공데이터포털은 확정 실적 기반 후행(Trailing) PER만 제공하며, 선행 PER 시계열을 무료 CSV/JSON/HTML 표로 제공하는 합법적 공개 URL은 존재하지 않습니다.

---

### 4. CNN Fear & Greed Index 일별 시계열 (공개 데이터셋)

* **URL (GitHub Raw CSV 직접 다운로드)**:
  * **통합 시계열 (2011~2023 아카이브)**: `https://raw.githubusercontent.com/whit3rabbit/fear-greed-data/main/fear-greed-2011-2023.csv`
  * **저장소 메인 (파일 목록 및 최신 갱신본 확인)**: `https://github.com/whit3rabbit/fear-greed-data`
  * **보조 저장소 (2020년~현재 일별 자동 수집)**: `https://github.com/Aaylen/cnn-fear-and-greed-data`
* **수록 기간 및 주기**: **2011년 1월 3일 ~ 현재 / 일별(Daily, 미국 증시 영업일 기준)**
* **산출 정의**:
  * CNN Business가 미국 주식시장의 7가지 지표(① S&P 500 모멘텀[125일 이평선 대비], ② 주가 강도[52주 신고가/신저가 비율], ③ 주가 폭[McClellan Volume Summation Index], ④ 풋/콜 옵션 비율[5일 평균], ⑤ 정크본드 수요[투자적격 대비 스프레드], ⑥ 시장 변동성[VIX 및 50일 이평선], ⑦ 안전자산 수요[주식 대비 국채 20일 수익률 차이])를 동일 가중치로 종합하여 **0(극단적 공포) ~ 100(극단적 탐욕)**으로 표준화한 지수.
* **접근 제한**:
  * GitHub Raw URL을 통해 **로그인·API 키·봇 차단 없이 무료 즉시 다운로드** 가능.
* **신뢰도 주의사항**:
  * CNN 공식 API는 약 **2020년 중반~2021년 2월 이후**의 일별 공식 JSON 데이터만 완전하게 보존하고 있습니다.
  * 따라서 GitHub 데이터셋의 **2011년 ~ 2020년 구간**은 과거 웹 아카이브 및 서드파티 기록을 병합·복원한 것이며, 2021년 2월 이후 구간만 CNN 공식 백엔드 수치와 1:1로 일치합니다(일부 과거 일자 결측치 또는 소수점 반올림 차이가 존재함).
