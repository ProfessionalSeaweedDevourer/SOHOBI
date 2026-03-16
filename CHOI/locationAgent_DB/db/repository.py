"""
repository.py (Oracle 버전)
DB 조회 레이어 - LocationAgent가 이 클래스만 바라봄

[연결 설정]
- DB: Oracle (SANGKWON_SALES 테이블)
- 지역 기준: 행정동 단위 (ADM_CD, ADM_NM)
- 업종 기준: 서비스 업종 코드 (SVC_INDUTY_CD)

[환경변수 필요]
ORACLE_USER=...
ORACLE_PASSWORD=...
ORACLE_DSN=...   # host:port/service_name
"""
import oracledb as cx_Oracle
import os
from typing import Optional

# 행정동 코드 기반 지역 매핑 (208개 키워드)
AREA_MAP = {
    # 홍대/마포권
    "홍대":       ["11440660"],
    "합정":       ["11440680"],
    "연남동":     ["11440710"],
    "망원":       ["11440690", "11440700"],
    "상암":       ["11440740"],
    "공덕":       ["11440565"],
    "마포":       ["11440565", "11440585", "11440600", "11440590", "11440655", "11440610", "11440630", "11440555"],
    "대흥":       ["11440600"],
    "아현":       ["11440555"],

    # 강남권
    "강남":       ["11680640", "11680650", "11680521", "11680531"],
    "역삼":       ["11680640", "11680650"],
    "논현":       ["11680521", "11680531"],
    "압구정":     ["11680545"],
    "청담":       ["11680565"],
    "삼성":       ["11680580", "11680590"],
    "대치":       ["11680600", "11680610", "11680630"],
    "도곡":       ["11680655", "11680656"],
    "개포":       ["11680660", "11680670", "11680690"],
    "일원":       ["11680730", "11680740", "11680720"],
    "수서":       ["11680750"],
    "세곡":       ["11680700"],

    # 서초/사당권
    "서초":       ["11650510", "11650520", "11650530", "11650531"],
    "반포":       ["11650560", "11650570", "11650580", "11650581", "11650550"],
    "잠원":       ["11650540"],
    "방배":       ["11650600", "11650610", "11650620", "11650621", "11650590"],
    "양재":       ["11650651", "11650652"],
    "내곡":       ["11650660"],
    "사당":       ["11590620", "11590630", "11590640", "11590650", "11590651"],

    # 여의도/영등포권
    "여의도":     ["11560540"],
    "영등포":     ["11560515", "11560535"],
    "당산":       ["11560550", "11560560"],
    "문래":       ["11560605"],
    "양평":       ["11560610", "11560620"],
    "신길":       ["11560630", "11560650", "11560660", "11560670", "11560680", "11560690"],
    "대림":       ["11560700", "11560710", "11560720"],
    "도림":       ["11560585"],

    # 이태원/용산권
    "이태원":     ["11170650", "11170660"],
    "한남":       ["11170685"],
    "용산":       ["11170520", "11170625"],
    "이촌":       ["11170630", "11170640"],
    "서빙고":     ["11170690"],
    "보광":       ["11170700"],
    "효창":       ["11170580"],
    "청파":       ["11170555"],
    "원효로":     ["11170560", "11170570"],
    "후암":       ["11170510"],

    # 건대/성수권
    "건대":       ["11215710"],
    "성수":       ["11200650", "11200660", "11200670", "11200690"],
    "뚝섬":       ["11200650", "11200660"],
    "자양":       ["11215820", "11215830", "11215840", "11215847"],
    "구의":       ["11215850", "11215860", "11215870"],
    "광장":       ["11215810"],
    "군자":       ["11215730"],
    "능동":       ["11215780"],

    # 신촌/서대문권
    "신촌":       ["11410585"],
    "연희":       ["11410615"],
    "홍제":       ["11410620", "11410655", "11410640"],
    "홍은":       ["11410660", "11410685"],
    "북가좌":     ["11410710", "11410720"],
    "남가좌":     ["11410690", "11410700"],
    "천연":       ["11410520"],
    "충현":       ["11410565"],
    "북아현":     ["11410555"],

    # 잠실/송파권
    "잠실":       ["11710650", "11710670", "11710680", "11710690", "11710710", "11710720"],
    "송파":       ["11710580", "11710590"],
    "석촌":       ["11710600"],
    "삼전":       ["11710610"],
    "방이":       ["11710561", "11710562"],
    "오금":       ["11710570"],
    "가락":       ["11710620", "11710631", "11710632"],
    "문정":       ["11710641", "11710642"],
    "장지":       ["11710646"],
    "위례":       ["11710647"],
    "마천":       ["11710540", "11710550"],
    "거여":       ["11710531", "11710532"],
    "풍납":       ["11710510", "11710520"],

    # 강동권
    "강동":       ["11740600", "11740610", "11740620"],
    "천호":       ["11740600", "11740610", "11740620"],
    "길동":       ["11740685"],
    "둔촌":       ["11740690", "11740700"],
    "성내":       ["11740640", "11740650", "11740660"],
    "암사":       ["11740570", "11740580", "11740590"],
    "명일":       ["11740530", "11740540"],
    "고덕":       ["11740550", "11740560"],
    "상일":       ["11740520"],
    "강일":       ["11740515"],

    # 노원/도봉/강북권
    "노원":       ["11350630", "11350640", "11350665", "11350670", "11350695", "11350700", "11350710", "11350720"],
    "상계":       ["11350630", "11350640", "11350665", "11350670", "11350695", "11350700", "11350710", "11350720"],
    "중계":       ["11350619", "11350621", "11350625", "11350624"],
    "하계":       ["11350611", "11350612"],
    "공릉":       ["11350595", "11350600"],
    "월계":       ["11350560", "11350570", "11350580"],
    "도봉":       ["11320521", "11320522"],
    "방학":       ["11320690", "11320700", "11320710"],
    "쌍문":       ["11320660", "11320670", "11320680", "11320681"],
    "창동":       ["11320511", "11320512", "11320513", "11320514", "11320515"],
    "수유":       ["11305615", "11305625", "11305635"],
    "미아":       ["11305535"],
    "삼양":       ["11305534"],
    "삼각산":     ["11305575"],
    "번동":       ["11305595", "11305603", "11305608"],
    "우이":       ["11305645"],
    "인수":       ["11305660"],
    "길음":       ["11290660", "11290685"],

    # 관악/동작권
    "관악":       ["11620695", "11620585"],
    "신림":       ["11620695"],
    "낙성대":     ["11620585"],
    "봉천":       ["11620615", "11620595", "11620565", "11620575", "11620605", "11620645",
                   "11620665", "11620775", "11620715", "11620765", "11620625", "11620630",
                   "11620735", "11620745", "11620525"],
    "노량진":     ["11590510", "11590520"],
    "대방":       ["11590660"],
    "신대방":     ["11590670", "11590680"],
    "흑석":       ["11590605"],
    "동작":       ["11590530", "11590540", "11590550", "11590560"],
    "상도":       ["11590530", "11590540", "11590550", "11590560"],

    # 강서/양천권
    "강서":       ["11500540", "11500550", "11500560", "11500570", "11500591", "11500593", "11500590"],
    "화곡":       ["11500540", "11500550", "11500560", "11500570", "11500591", "11500593", "11500590"],
    "방화":       ["11500630", "11500640", "11500641"],
    "가양":       ["11500603", "11500604", "11500605"],
    "등촌":       ["11500520", "11500530", "11500535"],
    "염창":       ["11500510"],
    "발산":       ["11500611"],
    "공항":       ["11500620"],
    "우장산":     ["11500615"],
    "마곡":       ["11500611"],
    "신월":       ["11470560", "11470570", "11470580", "11470590", "11470600", "11470610", "11470611"],
    "신정":       ["11470620", "11470630", "11470640", "11470650", "11470670", "11470680"],
    "목동":       ["11470510", "11470520", "11470530", "11470540", "11470550"],

    # DMC/은평권
    "DMC":        ["11440740"],
    "은평":       ["11380520", "11380530", "11380510", "11380570", "11380560",
                   "11380551", "11380552", "11380580", "11380590", "11380600",
                   "11380625", "11380640", "11380650", "11380690"],
    "불광":       ["11380520", "11380530"],
    "녹번":       ["11380510"],
    "응암":       ["11380580", "11380590", "11380600"],
    "역촌":       ["11380625"],
    "수색":       ["11380650"],
    "진관":       ["11380690"],

    # 종로/도심권
    "종로":       ["11110615", "11110630"],
    "광화문":     ["11110515", "11110530"],
    "인사동":     ["11110615"],
    "명동":       ["11140550"],
    "을지로":     ["11140605"],
    "동대문":     ["11230705", "11230545", "11230560", "11230570"],
    "청량리":     ["11230705"],
    "회현":       ["11140540"],
    "소공":       ["11140520"],
    "장충":       ["11140580"],
    "신당":       ["11140615", "11140650"],
    "다산":       ["11140625"],
    "약수":       ["11140635"],
    "청구":       ["11140645"],
    "황학":       ["11140670"],
    "중림":       ["11140680"],
    "광희":       ["11140590"],
    "교남":       ["11110580"],
    "평창":       ["11110560"],
    "부암":       ["11110550"],
    "혜화":       ["11110650"],
    "이화":       ["11110640"],
    "창신":       ["11110670", "11110680", "11110690"],
    "숭인":       ["11110700", "11110710"],
    "삼청":       ["11110540"],
    "가회":       ["11110600"],
    "무악":       ["11110570"],

    # 성북/강북권
    "성북":       ["11290525"],
    "삼선":       ["11290555"],
    "동선":       ["11290575"],
    "보문":       ["11290610"],
    "안암":       ["11290600"],
    "돈암":       ["11290580", "11290590"],
    "종암":       ["11290705"],
    "월곡":       ["11290715", "11290725"],
    "장위":       ["11290760", "11290770", "11290780"],
    "석관":       ["11290810"],
    "정릉":       ["11290620", "11290630", "11290640", "11290650"],

    # 중랑권
    "중랑":       ["11260600", "11260610", "11260620", "11260630", "11260680", "11260690",
                   "11260565", "11260520", "11260575", "11260540", "11260550", "11260570",
                   "11260655", "11260660", "11260580", "11260590"],
    "면목":       ["11260565", "11260520", "11260575", "11260540", "11260550", "11260570"],
    "망우":       ["11260655", "11260660"],
    "상봉":       ["11260580", "11260590"],
    "신내":       ["11260680", "11260690"],
    "중화":       ["11260600", "11260610"],
    "묵동":       ["11260620", "11260630"],

    # 동대문구
    "장안":       ["11230650", "11230660"],
    "답십리":     ["11230600", "11230610"],
    "전농":       ["11230560", "11230570"],
    "이문":       ["11230740", "11230750"],
    "휘경":       ["11230720", "11230730"],
    "회기":       ["11230710"],
    "용신":       ["11230536"],
    "제기":       ["11230545"],

    # 왕십리/성동권
    "왕십리":     ["11200520", "11200535"],
    "행당":       ["11200560", "11200570"],
    "응봉":       ["11200580"],
    "금호":       ["11200590", "11200615", "11200620"],
    "옥수":       ["11200645"],
    "마장":       ["11200540"],
    "사근":       ["11200550"],
    "송정":       ["11200720"],
    "용답":       ["11200790"],

    # 구로권
    "구로":       ["11530520", "11530530", "11530540", "11530550", "11530560"],
    "가산":       ["11545510"],
    "가리봉":     ["11530595"],
    "신도림":     ["11530510"],
    "개봉":       ["11530740", "11530750", "11530760"],
    "오류":       ["11530770", "11530780"],
    "고척":       ["11530720", "11530730"],
    "수궁":       ["11530790"],
    "항동":       ["11530800"],
    "독산":       ["11545610", "11545620", "11545630", "11545640"],
    "시흥":       ["11545670", "11545680", "11545690", "11545700", "11545710"],
}

INDUSTRY_CODE_MAP = {
    "한식":       "CS100001",
    "중식":       "CS100002",
    "일식":       "CS100003",
    "양식":       "CS100004",
    "베이커리":   "CS100005",
    "제과점":     "CS100005",
    "패스트푸드": "CS100006",
    "치킨":       "CS100007",
    "분식":       "CS100008",
    "호프":       "CS100009",
    "술집":       "CS100009",
    "카페":       "CS100010",
    "커피":       "CS100010",
    "미용실":     "CS200028",
    "네일":       "CS200029",
    "노래방":     "CS200037",
    "편의점":     "CS300002",
}


class CommercialRepository:
    def _connect(self):
        return cx_Oracle.connect(
            user=os.getenv("ORACLE_USER"),
            password=os.getenv("ORACLE_PASSWORD"),
            dsn=os.getenv("ORACLE_DSN"),
        )

    def _get_adm_codes(self, location: str) -> list:
        return AREA_MAP.get(location, [])

    def _get_industry_code(self, business_type: str) -> str:
        return INDUSTRY_CODE_MAP.get(business_type, "")

    def get_sales(self, location: str, business_type: str,
                  quarter: str = "20244") -> Optional[dict]:
        """
        행정동별 매출 조회 + 합산
        반환: {summary(합산), breakdown(행정동별 분리)}
        """
        adm_codes     = self._get_adm_codes(location)
        industry_code = self._get_industry_code(business_type)

        if not adm_codes or not industry_code:
            return None

        placeholders = ",".join(f":{i+1}" for i in range(len(adm_codes)))
        sql = f"""
            SELECT ADM_CD, ADM_NM, SVC_INDUTY_NM,
                   TOT_SALES_AMT, TOT_SELNG_CO,
                   MDWK_SALES_AMT, WKEND_SALES_AMT,
                   MON_SALES_AMT, TUE_SALES_AMT, WED_SALES_AMT,
                   THU_SALES_AMT, FRI_SALES_AMT, SAT_SALES_AMT, SUN_SALES_AMT,
                   TM00_06_SALES_AMT, TM06_11_SALES_AMT, TM11_14_SALES_AMT,
                   TM14_17_SALES_AMT, TM17_21_SALES_AMT, TM21_24_SALES_AMT,
                   ML_SALES_AMT, FML_SALES_AMT,
                   AGE10_AMT, AGE20_AMT, AGE30_AMT,
                   AGE40_AMT, AGE50_AMT, AGE60_AMT
            FROM SANGKWON_SALES
            WHERE BASE_YR_QTR_CD = :qtr
              AND ADM_CD IN ({placeholders})
              AND SVC_INDUTY_CD = :induty
        """
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, [quarter] + adm_codes + [industry_code])
            columns = [d[0].lower() for d in cursor.description]
            rows = [dict(zip(columns, row)) for row in cursor.fetchall()]

        if not rows:
            return None

        breakdown = []
        for r in rows:
            breakdown.append({
                "adm_name":          r["adm_nm"],
                "monthly_sales_krw": r["tot_sales_amt"] or 0,
                "monthly_tx_count":  r["tot_selng_co"] or 0,
                "weekday_sales_krw": r["mdwk_sales_amt"] or 0,
                "weekend_sales_krw": r["wkend_sales_amt"] or 0,
                "mon_sales_krw":     r["mon_sales_amt"] or 0,
                "tue_sales_krw":     r["tue_sales_amt"] or 0,
                "wed_sales_krw":     r["wed_sales_amt"] or 0,
                "thu_sales_krw":     r["thu_sales_amt"] or 0,
                "fri_sales_krw":     r["fri_sales_amt"] or 0,
                "sat_sales_krw":     r["sat_sales_amt"] or 0,
                "sun_sales_krw":     r["sun_sales_amt"] or 0,
                "time_00_06_krw":    r["tm00_06_sales_amt"] or 0,
                "time_06_11_krw":    r["tm06_11_sales_amt"] or 0,
                "time_11_14_krw":    r["tm11_14_sales_amt"] or 0,
                "time_14_17_krw":    r["tm14_17_sales_amt"] or 0,
                "time_17_21_krw":    r["tm17_21_sales_amt"] or 0,
                "time_21_24_krw":    r["tm21_24_sales_amt"] or 0,
                "male_sales_krw":    r["ml_sales_amt"] or 0,
                "female_sales_krw":  r["fml_sales_amt"] or 0,
                "age_10s_krw":       r["age10_amt"] or 0,
                "age_20s_krw":       r["age20_amt"] or 0,
                "age_30s_krw":       r["age30_amt"] or 0,
                "age_40s_krw":       r["age40_amt"] or 0,
                "age_50s_krw":       r["age50_amt"] or 0,
                "age_60s_krw":       r["age60_amt"] or 0,
            })

        def _sum(key): return sum(b[key] for b in breakdown)

        summary = {
            "location":          location,
            "business_type":     rows[0]["svc_induty_nm"],
            "quarter":           quarter,
            "adm_count":         len(breakdown),
            "monthly_sales_krw": _sum("monthly_sales_krw"),
            "monthly_tx_count":  _sum("monthly_tx_count"),
            "weekday_sales_krw": _sum("weekday_sales_krw"),
            "weekend_sales_krw": _sum("weekend_sales_krw"),
            "mon_sales_krw":     _sum("mon_sales_krw"),
            "tue_sales_krw":     _sum("tue_sales_krw"),
            "wed_sales_krw":     _sum("wed_sales_krw"),
            "thu_sales_krw":     _sum("thu_sales_krw"),
            "fri_sales_krw":     _sum("fri_sales_krw"),
            "sat_sales_krw":     _sum("sat_sales_krw"),
            "sun_sales_krw":     _sum("sun_sales_krw"),
            "time_00_06_krw":    _sum("time_00_06_krw"),
            "time_06_11_krw":    _sum("time_06_11_krw"),
            "time_11_14_krw":    _sum("time_11_14_krw"),
            "time_14_17_krw":    _sum("time_14_17_krw"),
            "time_17_21_krw":    _sum("time_17_21_krw"),
            "time_21_24_krw":    _sum("time_21_24_krw"),
            "male_sales_krw":    _sum("male_sales_krw"),
            "female_sales_krw":  _sum("female_sales_krw"),
            "age_10s_krw":       _sum("age_10s_krw"),
            "age_20s_krw":       _sum("age_20s_krw"),
            "age_30s_krw":       _sum("age_30s_krw"),
            "age_40s_krw":       _sum("age_40s_krw"),
            "age_50s_krw":       _sum("age_50s_krw"),
            "age_60s_krw":       _sum("age_60s_krw"),
            "source":            "상권분석 DB (SANGKWON_SALES)",
        }

        return {"summary": summary, "breakdown": breakdown}

    def get_store_count(self, location: str, business_type: str,
                        quarter: str = "20244") -> Optional[dict]:
        """
        점포수/개폐업률 조회 - 추후 테이블 추가 시 구현
        현재는 None 반환
        """
        return None

    def get_similar_locations(self, business_type: str, quarter: str = "20244",
                               exclude_location: str = None, top_n: int = 3) -> list:
        """
        업종 기준 유사 상권 추천 (복합 점수)
        점수 = 점포당평균매출(0.4) + 매출규모(0.3) + 주중비율(0.2) + 여성비율(0.1)
        (점포수/개폐업률 없으므로 가용 지표로 대체)
        """
        industry_code = self._get_industry_code(business_type)
        if not industry_code:
            return []

        exclude_codes = self._get_adm_codes(exclude_location) if exclude_location else []

        sql = """
            SELECT ADM_CD, ADM_NM,
                   SUM(TOT_SALES_AMT)  AS monthly_sales,
                   COUNT(*)            AS dong_count,
                   SUM(MDWK_SALES_AMT) AS weekday_sales,
                   SUM(FML_SALES_AMT)  AS female_sales
            FROM SANGKWON_SALES
            WHERE BASE_YR_QTR_CD = :1
              AND SVC_INDUTY_CD   = :2
            GROUP BY ADM_CD, ADM_NM
        """
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, [quarter, industry_code])
            columns = [d[0].lower() for d in cursor.description]
            rows = [dict(zip(columns, row)) for row in cursor.fetchall()]

        if not rows:
            return []

        # 제외 코드 필터링
        rows = [r for r in rows if r["adm_cd"] not in exclude_codes]

        # 지표 계산
        for r in rows:
            monthly = r["monthly_sales"] or 0
            r["avg_sales"]     = monthly  # 행정동 단위라 점포수 없음 → 총매출 사용
            r["weekday_ratio"] = (r["weekday_sales"] or 0) / monthly if monthly else 0
            r["female_ratio"]  = (r["female_sales"] or 0) / monthly if monthly else 0

        # 이상치 제거 (상위 5%)
        avg_list = [r["avg_sales"] for r in rows]
        threshold = sorted(avg_list)[int(len(avg_list) * 0.95)]
        rows = [r for r in rows if r["avg_sales"] <= threshold]

        # 정규화
        def normalize(values, inverse=False):
            mn, mx = min(values), max(values)
            if mx == mn:
                return [0.5] * len(values)
            normed = [(v - mn) / (mx - mn) for v in values]
            return [1 - n for n in normed] if inverse else normed

        avg_norm     = normalize([r["avg_sales"] for r in rows])
        wkday_norm   = normalize([r["weekday_ratio"] for r in rows])
        female_norm  = normalize([r["female_ratio"] for r in rows])

        scored = []
        for i, r in enumerate(rows):
            score = avg_norm[i] * 0.5 + wkday_norm[i] * 0.3 + female_norm[i] * 0.2
            scored.append({
                "adm_cd":            r["adm_cd"],
                "adm_name":          r["adm_nm"],
                "monthly_sales_krw": r["monthly_sales"],
                "score":             round(score, 4),
            })

        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:top_n]

    def get_supported_locations(self) -> list:
        return list(AREA_MAP.keys())

    def get_supported_industries(self) -> list:
        return list(INDUSTRY_CODE_MAP.keys())