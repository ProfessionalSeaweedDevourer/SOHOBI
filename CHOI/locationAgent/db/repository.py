"""
repository.py
DB 조회 레이어 - LocationAgent가 이 클래스만 바라봄

[SQLite → Oracle 전환 시 변경 포인트]
1. import sqlite3           →  import cx_Oracle
2. sqlite3.connect(DB_PATH) →  cx_Oracle.connect(user, pw, dsn)
3. SQL: LIMIT N             →  WHERE ROWNUM <= N
4. 플레이스홀더: ?           →  :1 또는 :변수명
"""
import sqlite3
import os
from typing import Optional

DB_PATH = os.path.join(os.path.dirname(__file__), "commercial.db")

# 상권 코드 매핑 (발달상권 위주 핵심 상권만)
TRDAR_CODE_MAP = {
    "홍대":   ["3120103", "3120102", "3120104", "3120105"],
    "합정":   ["3120101"],
    "연남동":  ["3120104", "3110562"],
    "망원":   ["3120100"],
    "신촌":   ["3120094"],
    "강남":   ["3120189"],
    "이태원":  ["3120046", "3001491"],
    "건대":   ["3120053"],
    "잠실":   ["3120227", "3120225"],
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

    def _get_trdar_codes(self, location: str) -> list:
        return TRDAR_CODE_MAP.get(location, [])

    def _get_industry_code(self, business_type: str) -> str:
        return INDUSTRY_CODE_MAP.get(business_type, "")

    def get_sales(self, location: str, business_type: str,
                  quarter: str = "20253") -> Optional[dict]:
        """
        상권별 매출 조회 + 합산
        반환: {summary(합산), breakdown(상권별 분리)}
        """
        trdar_codes   = self._get_trdar_codes(location)
        industry_code = self._get_industry_code(business_type)

        if not trdar_codes or not industry_code:
            return None

        placeholders = ",".join("?" * len(trdar_codes))
        sql = f"""
            SELECT * FROM commercial_sales
            WHERE quarter = ?
              AND trdar_code IN ({placeholders})
              AND industry_code = ?
        """
        with self._connect() as conn:
            rows = conn.execute(sql, (quarter, *trdar_codes, industry_code)).fetchall()

        if not rows:
            return None

        # 상권별 분리
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

        # 합산
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
                        quarter: str = "20253") -> Optional[dict]:
        """점포수/개폐업률 조회 + 합산"""
        trdar_codes   = self._get_trdar_codes(location)
        industry_code = self._get_industry_code(business_type)

        if not trdar_codes or not industry_code:
            return None

        placeholders = ",".join("?" * len(trdar_codes))
        sql = f"""
            SELECT * FROM commercial_store
            WHERE quarter = ?
              AND trdar_code IN ({placeholders})
              AND industry_code = ?
        """
        with self._connect() as conn:
            rows = conn.execute(sql, (quarter, *trdar_codes, industry_code)).fetchall()

        if not rows:
            return None

        breakdown = [
            {
                "trdar_name":    r["trdar_name"],
                "trdar_type":    r["trdar_type"],
                "store_count":   r["store_count"],
                "open_rate_pct": r["open_rate"],
                "close_rate_pct":r["close_rate"],
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

    def get_supported_locations(self) -> list:
        return list(TRDAR_CODE_MAP.keys())

    def get_supported_industries(self) -> list:
        return list(INDUSTRY_CODE_MAP.keys())