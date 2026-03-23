"""
repository.py
DB 조회 레이어 — LocationAgent가 이 클래스만 바라봄

출처: CHOI/locationAgent_sang/db/repository.py
변경: DB_PATH를 COMMERCIAL_DB_PATH 환경변수로 오버라이드 가능하게 수정
     (Railway 볼륨 마운트 시 경로 주입용)

[SQLite → Oracle 전환 시 변경 포인트]
1. import sqlite3           →  import cx_Oracle
2. sqlite3.connect(DB_PATH) →  cx_Oracle.connect(user, pw, dsn)
3. 플레이스홀더: ?           →  :1 또는 :변수명
"""

import os
import sqlite3
from typing import Optional

_DEFAULT_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "commercial.db")
DB_PATH = os.getenv("COMMERCIAL_DB_PATH", _DEFAULT_DB_PATH)

# 사용자 키워드 → 상권명 매핑
AREA_MAP = {
    # 홍대/마포권
    "홍대":       ["홍대입구역(홍대)", "서교동(홍대)", "연남동(홍대)", "상수역(홍대)"],
    "합정":       ["합정역"],
    "연남동":     ["연남동(홍대)"],
    "상수":       ["상수역(홍대)"],
    "망원":       ["망원역"],
    "공덕":       ["공덕역(공덕오거리)"],
    "마포":       ["마포역"],
    "월드컵":     ["월드컵경기장역(월드컵경기장)"],

    # 강남권
    "강남":       ["강남역", "강남구청역", "강남을지병원", "강남구청(청담역_8번, 강남세무서)"],
    "강남역":     ["강남역"],
    "신논현":     ["신논현역", "신논현역 1번"],
    "역삼":       ["역삼역"],
    "선릉":       ["선릉역"],
    "선정릉":     ["선정릉역"],
    "삼성":       ["삼성역", "삼성중앙역"],
    "코엑스":     ["코엑스"],
    "봉은사":     ["봉은사역"],
    "압구정":     ["압구정역", "압구정로데오역(압구정로데오)"],
    "청담":       ["청담사거리(청담동명품거리)", "강남구청(청담역_8번, 강남세무서)"],
    "논현":       ["논현역", "논현역 4번", "논현역 5번"],
    "신사":       ["신사역"],
    "가로수길":   ["가로수길"],
    "도산공원":   ["도산공원교차로"],
    "학동":       ["학동역", "학동사거리"],
    "언주":       ["언주역(차병원)"],
    "대치":       ["대치역", "대치사거리"],
    "한티":       ["한티역"],
    "매봉":       ["매봉역"],
    "양재":       ["양재역", "양재천카페거리", "양재시민의숲역(양재동꽃시장, aT센터)"],
    "뱅뱅":       ["뱅뱅사거리"],
    "도곡":       ["도곡1동"],

    # 서초/사당권
    "교대":       ["교대역(법원.검찰청)", "교대입구교차로"],
    "서초":       ["서초역", "서초3동사거리"],
    "사당":       ["사당역(사당)", "사당역 11번(사당역먹자골목)"],
    "방배":       ["방배역", "방배동카페골목", "방배동가구거리(사당동가구거리)"],
    "남부터미널": ["남부터미널역"],
    "고속터미널": ["고속터미널(고속터미널역)"],
    "총신대":     ["총신대입구역(이수, 총신대)", "총신대학교"],
    "서래마을":   ["서래마을카페거리(서래마을)"],

    # 여의도/영등포권
    "여의도":     ["여의도역(여의도)"],
    "영등포":     ["영등포역(영등포)", "영등포구청역", "영등포청과시장교차로"],
    "당산":       ["당산역", "당산2동(영등포우체국)"],
    "문래":       ["문래역(문래로데오거리)", "문래동주민센터"],
    "신도림":     ["신도림역"],
    "대림":       ["대림역", "대림3동사거리"],
    "구로":       ["구로역", "구로구청", "구로디지털단지", "구로디지털단지역", "구로전화국"],
    "가산":       ["가산디지털단지"],
    "오목교":     ["오목교역"],
    "목동":       ["목동사거리", "목동신시가지", "목동역 8번출구"],
    "양평":       ["양평역"],
    "63빌딩":     ["63빌딩"],
    "국회":       ["국회의사당역(국회의사당)"],

    # 종로/도심권
    "종각":       ["종각역"],
    "종로3가":    ["종로3가역"],
    "종로4가":    ["종로4가"],
    "종로5가":    ["종로5가역"],
    "종로6가":    ["종로6가"],
    "종로구청":   ["종로구청"],
    "광화문":     ["광화문역"],
    "인사동":     ["인사동"],
    "북촌":       ["북촌(안국역)"],
    "삼청동":     ["삼청동"],
    "서촌":       ["서촌(경복궁역)"],
    "명동":       ["명동(명동거리)", "명동역(명동재미로)"],
    "시청":       ["서울시청", "시청역_1번", "시청역_8번", "롯데백화점(시청광장 지하쇼핑센터)"],
    "북창동":     ["북창동(시청역_6번)"],
    "을지로":     ["을지로입구역", "을지로2가", "을지로3가역", "을지로4가역"],
    "충무로":     ["충무로역"],
    "충정로":     ["충정로역"],
    "중림동":     ["중림동"],
    "서울역":     ["서울역"],
    "남영동":     ["남영동 먹자골목", "숙대입구역(남영역, 남영동)"],
    "회현":       ["회현역"],
    "퇴계로":     ["퇴계로5가"],
    "중구청":     ["중구청(퇴계로4가)"],
    "장충동":     ["장충동족발거리(남소영길)"],
    "대학로":     ["대학로(혜화역)"],
    "원남동":     ["원남동사거리"],

    # 이태원/용산권
    "이태원":     ["이태원(이태원역)"],
    "한남":       ["한남오거리"],
    "삼각지":     ["삼각지역"],
    "용산":       ["신용산역(용산역)", "용산전자상가(용산역)"],
    "약수":       ["약수역"],
    "금호":       ["금호역"],

    # 건대/성수/왕십리권
    "건대":       ["건대입구역(건대)"],
    "성수":       ["성수역", "성수대교남단", "서울숲역"],
    "뚝섬":       ["뚝섬역"],
    "왕십리":     ["왕십리역(왕십리)"],
    "군자":       ["군자역"],
    "아차산":     ["아차산역"],
    "구의":       ["구의역", "구의사거리"],
    "강변":       ["강변역(테크노마트)"],

    # 신촌/서대문권
    "신촌":       ["신촌역(신촌역, 신촌로터리)"],
    "이대":       ["이화여대(이대역, 이대)", "이화사거리"],
    "서대문":     ["서대문역"],
    "홍제":       ["홍제역"],
    "연희동":     ["연희동"],
    "불광":       ["불광역"],
    "응암":       ["응암역"],
    "구산":       ["구산역"],
    "구파발":     ["구파발역"],
    "연신내":     ["연신내역"],

    # 잠실/송파권
    "잠실":       ["잠실역", "잠실새내역(신천)"],
    "잠실역":     ["잠실역"],
    "석촌":       ["석촌역(석촌호수)", "석촌고분역"],
    "방이":       ["방이역", "방이동먹자골목"],
    "송파":       ["송파사거리(송파역)", "송파나루역"],
    "가락":       ["가락시장", "가락시장역"],
    "문정":       ["문정역"],
    "장지":       ["장지역(가든파이브)"],
    "몽촌":       ["몽촌토성역"],
    "오금":       ["오금역"],
    "거여":       ["거여역"],
    "개롱":       ["개롱역"],
    "굽은다리":   ["굽은다리역"],

    # 강동권
    "강동구청":   ["강동구청역"],
    "천호":       ["천호역"],
    "암사":       ["암사역"],
    "명일":       ["명일역"],
    "고덕":       ["고덕역"],
    "길동":       ["길동역"],
    "둔촌":       ["둔촌역"],

    # 노원/도봉/강북권
    "노원":       ["노원역"],
    "창동":       ["창동역"],
    "수유":       ["수유역"],
    "미아":       ["미아역", "미아사거리역", "미아사거리"],
    "월곡":       ["월곡역"],
    "성북구청":   ["성북구청"],
    "성신여대":   ["성신여대"],
    "한성대":     ["한성대입구역"],
    "안암":       ["안암역"],
    "회기":       ["회기역"],
    "경희대":     ["경희대학교(경희대)"],
    "태릉":       ["태릉입구역"],
    "공릉":       ["공릉역"],
    "마들":       ["마들역"],
    "사가정":     ["사가정역"],
    "상봉":       ["상봉역"],
    "장안동":     ["장안동사거리"],
    "장한평":     ["장한평역(장한평)"],
    "신설동":     ["신설동역"],
    "동대문":     ["동대문역", "동대문역사문화공원역"],
    "신당":       ["신당역"],

    # 관악/동작권
    "신림":       ["신림역(신림)"],
    "서울대":     ["서울대입구역"],
    "녹두거리":   ["녹두거리(대학동)"],
    "보라매":     ["보라매역", "보라매공원"],
    "신대방":     ["신대방삼거리역"],
    "노량진":     ["노량진역(노량진)"],
    "내방":       ["내방역"],
    "독산":       ["독산동"],

    # 강서/양천권
    "마곡":       ["마곡역(마곡)", "발산역(마곡)"],
    "강서구청":   ["강서구청"],
    "화곡":       ["화곡역"],
    "까치산":     ["까치산역"],
    "신정":       ["신정네거리역"],
    "오류동":     ["오류동역"],
    "등촌":       ["등촌역"],
    "송정":       ["송정역"],
    "김포공항":   ["김포공항역(김포공항)"],

    # DMC/은평권
    "DMC":            ["DMC(디지털미디어시티)"],
    "디지털미디어시티": ["DMC(디지털미디어시티)"],

    # 기타
    "포스코":     ["포스코사거리"],
    "경찰병원":   ["경찰병원역"],
    "수서":       ["수서역"],
    "청량리":     ["청량리역(청량리)"],
    "동묘":       ["동묘앞역(동묘)"],
}

INDUSTRY_CODE_MAP = {
    "한식":       "CS100001",
    "중식":       "CS100002",
    "일식":       "CS100003",
    "양식":       "CS100004",
    "베이커리":   "CS100005",
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
    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn

    def _get_trdar_names(self, location: str) -> list:
        return AREA_MAP.get(location, [])

    def _get_industry_code(self, business_type: str) -> str:
        return INDUSTRY_CODE_MAP.get(business_type, "")

    def get_sales(self, location: str, business_type: str,
                  quarter: str = "20244",
                  trdar_types: list = None) -> Optional[dict]:
        """상권별 매출 조회 + 합산."""
        if trdar_types is None:
            trdar_types = ["발달상권"]

        trdar_names   = self._get_trdar_names(location)
        industry_code = self._get_industry_code(business_type)

        if not trdar_names or not industry_code:
            return None

        name_placeholders = ",".join("?" * len(trdar_names))
        type_placeholders = ",".join("?" * len(trdar_types))
        sql = f"""
            SELECT * FROM commercial_sales
            WHERE quarter = ?
              AND trdar_name IN ({name_placeholders})
              AND industry_code = ?
              AND trdar_type IN ({type_placeholders})
        """
        with self._connect() as conn:
            rows = conn.execute(
                sql, (quarter, *trdar_names, industry_code, *trdar_types)
            ).fetchall()

        if not rows:
            return None

        breakdown = []
        for r in rows:
            breakdown.append({
                "trdar_name":        r["trdar_name"],
                "trdar_type":        r["trdar_type"],
                "monthly_sales_krw": r["monthly_sales"],
                "monthly_tx_count":  r["monthly_tx"],
                "weekday_sales_krw": r["weekday_sales"],
                "weekend_sales_krw": r["weekend_sales"],
                "mon_sales_krw":     r["mon_sales"],
                "tue_sales_krw":     r["tue_sales"],
                "wed_sales_krw":     r["wed_sales"],
                "thu_sales_krw":     r["thu_sales"],
                "fri_sales_krw":     r["fri_sales"],
                "sat_sales_krw":     r["sat_sales"],
                "sun_sales_krw":     r["sun_sales"],
                "time_00_06_krw":    r["time_00_06"],
                "time_06_11_krw":    r["time_06_11"],
                "time_11_14_krw":    r["time_11_14"],
                "time_14_17_krw":    r["time_14_17"],
                "time_17_21_krw":    r["time_17_21"],
                "time_21_24_krw":    r["time_21_24"],
                "male_sales_krw":    r["male_sales"],
                "female_sales_krw":  r["female_sales"],
                "age_10s_krw":       r["age_10s"],
                "age_20s_krw":       r["age_20s"],
                "age_30s_krw":       r["age_30s"],
                "age_40s_krw":       r["age_40s"],
                "age_50s_krw":       r["age_50s"],
                "age_60s_krw":       r["age_60s"],
            })

        def _sum(key): return sum(b[key] for b in breakdown)

        summary = {
            "location":          location,
            "business_type":     rows[0]["industry_name"],
            "quarter":           quarter,
            "trdar_count":       len(breakdown),
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
            "source":            "상권분석 DB (commercial_sales)",
        }

        return {"summary": summary, "breakdown": breakdown}

    def get_store_count(self, location: str, business_type: str,
                        quarter: str = "20244",
                        trdar_types: list = None) -> Optional[dict]:
        """점포수/개폐업률 조회 + 합산."""
        if trdar_types is None:
            trdar_types = ["발달상권"]

        trdar_names   = self._get_trdar_names(location)
        industry_code = self._get_industry_code(business_type)

        if not trdar_names or not industry_code:
            return None

        name_placeholders = ",".join("?" * len(trdar_names))
        type_placeholders = ",".join("?" * len(trdar_types))
        sql = f"""
            SELECT * FROM commercial_store
            WHERE quarter = ?
              AND trdar_name IN ({name_placeholders})
              AND industry_code = ?
              AND trdar_type IN ({type_placeholders})
        """
        with self._connect() as conn:
            rows = conn.execute(
                sql, (quarter, *trdar_names, industry_code, *trdar_types)
            ).fetchall()

        if not rows:
            return None

        breakdown = [
            {
                "trdar_name":     r["trdar_name"],
                "trdar_type":     r["trdar_type"],
                "store_count":    r["store_count"],
                "open_rate_pct":  r["open_rate"],
                "close_rate_pct": r["close_rate"],
            }
            for r in rows
        ]

        total_stores = sum(b["store_count"] for b in breakdown)
        avg_open     = sum(b["open_rate_pct"]  for b in breakdown) / len(breakdown)
        avg_close    = sum(b["close_rate_pct"] for b in breakdown) / len(breakdown)

        summary = {
            "location":        location,
            "business_type":   rows[0]["industry_name"],
            "quarter":         quarter,
            "trdar_count":     len(breakdown),
            "store_count":     total_stores,
            "open_rate_pct":   round(avg_open, 2),
            "close_rate_pct":  round(avg_close, 2),
            "source":          "상권분석 DB (commercial_store)",
        }

        return {"summary": summary, "breakdown": breakdown}

    def get_similar_locations(self, business_type: str, quarter: str = "20244",
                               exclude_location: str = None, top_n: int = 3) -> list:
        """업종 기준 유사 상권 추천 (복합 점수)."""
        import math

        industry_code = self._get_industry_code(business_type)
        if not industry_code:
            return []

        exclude_names = self._get_trdar_names(exclude_location) if exclude_location else []

        sql = """
            SELECT s.trdar_name,
                   s.monthly_sales,
                   t.store_count,
                   t.open_rate,
                   t.close_rate
            FROM commercial_sales s
            JOIN commercial_store t
              ON s.trdar_name = t.trdar_name
             AND s.quarter    = t.quarter
             AND s.industry_code = t.industry_code
            WHERE s.quarter = ?
              AND s.industry_code = ?
              AND s.trdar_type = '발달상권'
        """
        with self._connect() as conn:
            rows = conn.execute(sql, (quarter, industry_code)).fetchall()

        if not rows:
            return []

        rows = [r for r in rows if r["trdar_name"] not in exclude_names]
        rows = [r for r in rows
                if r["store_count"] >= 3
                and (r["monthly_sales"] / r["store_count"]) <= 80_000_000]

        if not rows:
            return []

        def normalize(values, inverse=False):
            min_v, max_v = min(values), max(values)
            if max_v == min_v:
                return [0.5] * len(values)
            normed = [(v - min_v) / (max_v - min_v) for v in values]
            return [1 - n for n in normed] if inverse else normed

        def open_rate_score(rate):
            if 3 <= rate <= 5:
                return 1.0
            elif rate < 3:
                return rate / 3
            else:
                return max(0, 1 - (rate - 5) / 10)

        avg_sales_list     = [r["monthly_sales"] / r["store_count"] if r["store_count"] > 0 else 0 for r in rows]
        monthly_sales_list = [r["monthly_sales"] for r in rows]
        close_rate_list    = [r["close_rate"] for r in rows]

        norm_avg   = normalize(avg_sales_list)
        norm_sales = normalize(monthly_sales_list)
        norm_close = normalize(close_rate_list, inverse=True)
        norm_open  = [open_rate_score(r["open_rate"]) for r in rows]

        scored = []
        for i, r in enumerate(rows):
            score = (
                norm_avg[i]   * 0.4 +
                norm_close[i] * 0.3 +
                norm_sales[i] * 0.2 +
                norm_open[i]  * 0.1
            )
            scored.append({
                "trdar_name":              r["trdar_name"],
                "monthly_sales_krw":       r["monthly_sales"],
                "store_count":             r["store_count"],
                "avg_sales_per_store_krw": int(avg_sales_list[i]),
                "open_rate_pct":           r["open_rate"],
                "close_rate_pct":          r["close_rate"],
                "score":                   round(score, 4),
            })

        trdar_to_keyword = {}
        for keyword, names in AREA_MAP.items():
            for name in names:
                if name not in trdar_to_keyword:
                    trdar_to_keyword[name] = keyword

        scored.sort(key=lambda x: x["score"], reverse=True)
        result = []
        seen_keywords = set()
        for item in scored:
            keyword = trdar_to_keyword.get(item["trdar_name"], item["trdar_name"])
            if keyword in seen_keywords:
                continue
            seen_keywords.add(keyword)
            item["keyword"] = keyword
            result.append(item)
            if len(result) >= top_n:
                break

        return result

    def get_supported_locations(self) -> list:
        return list(AREA_MAP.keys())

    def get_supported_industries(self) -> list:
        return list(INDUSTRY_CODE_MAP.keys())
