# 위치: p01_backEnd/DAO/mapInfoDAO.py
# PostgreSQL (Azure) 버전

import math
import logging
from .baseDAO import BaseDAO

logger = logging.getLogger(__name__)

# ── 컬럼 목록 (store_seoul 소문자 기준) ─────────────────────────
STORE_COLS = [
    "store_id", "store_nm",
    "cat_cd", "cat_nm", "mid_cat_nm", "sub_cat_nm",
    "sido_nm", "sgg_nm", "adm_nm", "road_addr",
    "floor_info", "unit_info", "lng", "lat",
]

def _clean_store(row: dict) -> dict:
    """None 값 제거 - CSV NULL로 적재된 경우 대비"""
    return {k: v for k, v in row.items() if v is not None and v != "NULL"}


SELECT_STORE = """
    SELECT store_id   AS "STORE_ID",
           store_nm   AS "STORE_NM",
           cat_cd     AS "CAT_CD",
           cat_nm     AS "CAT_NM",
           mid_cat_nm AS "MID_CAT_NM",
           sub_cat_nm AS "SUB_CAT_NM",
           sido_nm    AS "SIDO_NM",
           sgg_nm     AS "SGG_NM",
           adm_nm     AS "ADM_NM",
           road_addr  AS "ROAD_ADDR",
           floor_info AS "FLOOR_INFO",
           unit_info  AS "UNIT_INFO",
           lng        AS "LNG",
           lat        AS "LAT"
"""


class MapInfoDAO(BaseDAO):

    def __init__(self):
        self._ensure_search_indexes()

    def _ensure_search_indexes(self):
        """searchDong prefix LIKE 성능을 위한 B-tree 인덱스 생성 (없으면 생성)"""
        sqls = [
            "CREATE INDEX IF NOT EXISTS idx_store_adm_nm ON store_seoul (adm_nm text_pattern_ops)",
            "CREATE INDEX IF NOT EXISTS idx_store_legal_nm ON store_seoul (legal_nm text_pattern_ops)",
        ]
        try:
            for sql in sqls:
                self._execute(sql)
            logger.debug("[MapInfoDAO] search 인덱스 확인 완료")
        except Exception as e:
            logger.warning("[MapInfoDAO] 인덱스 생성 실패 (무시): %s", e)

    # ── 반경 조회 ─────────────────────────────────────────────────
    def getNearbyStores(self, lat: float, lng: float, radius: float = 500, limit: int = 500) -> list:
        lat_delta = radius / 111000.0
        lng_delta = radius / (111000.0 * abs(math.cos(math.radians(lat))) or 1)
        sql = f"""
            {SELECT_STORE}
            FROM store_seoul
            WHERE lat BETWEEN %(lat_min)s AND %(lat_max)s
              AND lng BETWEEN %(lng_min)s AND %(lng_max)s
              AND lat IS NOT NULL AND lng IS NOT NULL
            LIMIT %(limit)s
        """
        return [_clean_store(r) for r in self._query(sql, {
            "lat_min": lat - lat_delta, "lat_max": lat + lat_delta,
            "lng_min": lng - lng_delta, "lng_max": lng + lng_delta,
            "limit": limit,
        })]

    def getNearbyByCategory(self, lat: float, lng: float, category: str,
                             radius: float = 500, limit: int = 1000) -> list:
        lat_delta = radius / 111000.0
        lng_delta = radius / (111000.0 * abs(math.cos(math.radians(lat))) or 1)
        sql = f"""
            {SELECT_STORE}
            FROM store_seoul
            WHERE lat BETWEEN %(lat_min)s AND %(lat_max)s
              AND lng BETWEEN %(lng_min)s AND %(lng_max)s
              AND cat_cd = %(cat_cd)s
              AND lat IS NOT NULL AND lng IS NOT NULL
            LIMIT %(limit)s
        """
        return [_clean_store(r) for r in self._query(sql, {
            "lat_min": lat - lat_delta, "lat_max": lat + lat_delta,
            "lng_min": lng - lng_delta, "lng_max": lng + lng_delta,
            "cat_cd": category, "limit": limit,
        })]

    # ── 행정동코드(adm_cd) 기준 전체 스토어 ──────────────────────
    def getStoresByAdmCd(self, adm_cd: str) -> list:
        sql = f"""
            {SELECT_STORE}
            FROM store_seoul
            WHERE adm_cd = %(adm_cd)s
              AND lng IS NOT NULL AND lat IS NOT NULL
            LIMIT 1500
        """
        rows = self._query(sql, {"adm_cd": adm_cd})
        result = [_clean_store(r) for r in rows]
        logger.info(f"[MapInfoDAO] getStoresByAdmCd: adm_cd={adm_cd} → {len(result)}건")
        return result

    # ── 같은 건물 상가 + 같은 상호명 다른 지점 ────────────────────
    def getStoresByBuilding(self, road_addr: str, store_nm: str = None,
                             exclude_store_id: str = None) -> list:
        if not road_addr:
            return []

        sql_bldg = f"""
            {SELECT_STORE}
            FROM store_seoul
            WHERE road_addr = %(road_addr)s
              AND lng IS NOT NULL AND lat IS NOT NULL
            LIMIT 50
        """
        results = self._query(sql_bldg, {"road_addr": road_addr})

        if store_nm:
            sql_nm = f"""
                {SELECT_STORE}
                FROM store_seoul
                WHERE store_nm = %(store_nm)s
                  AND road_addr != %(road_addr)s
                  AND lng IS NOT NULL AND lat IS NOT NULL
                LIMIT 20
            """
            results += self._query(sql_nm, {"store_nm": store_nm, "road_addr": road_addr})

        if exclude_store_id:
            results = [r for r in results if r.get("store_id") != exclude_store_id]
        return results

    # ── 행정동/법정동 검색 ────────────────────────────────────────
    def searchDong(self, q: str) -> list:
        """행정동명 + 법정동명 prefix LIKE 검색 (B-tree 인덱스 활용)"""
        try:
            # 1. 행정동 검색 (store_seoul 기준)
            sql_adm = """
                SELECT DISTINCT adm_cd, adm_nm, NULL AS legal_nm, '행정동' AS type
                FROM store_seoul
                WHERE adm_nm LIKE %(q)s
                  AND adm_cd IS NOT NULL
                ORDER BY adm_nm
                LIMIT 20
            """
            rows_adm = self._query(sql_adm, {"q": f"{q}%"})

            # 2. 법정동 검색
            sql_legal = """
                SELECT DISTINCT adm_cd, adm_nm, legal_nm, '법정동' AS type
                FROM store_seoul
                WHERE legal_nm LIKE %(q)s
                  AND adm_cd IS NOT NULL
                ORDER BY adm_nm
                LIMIT 20
            """
            rows_legal = self._query(sql_legal, {"q": f"{q}%"})

            existing = {r["adm_cd"] for r in rows_adm}
            for r in rows_legal:
                if r["adm_cd"] not in existing:
                    rows_adm.append(r)
                    existing.add(r["adm_cd"])

            logger.info(f"[MapInfoDAO] searchDong: '{q}' → {len(rows_adm)}개")
            return rows_adm
        except Exception as e:
            logger.error(f"[MapInfoDAO] searchDong 실패: {e}")
            return []

    # ── 업종 목록 ─────────────────────────────────────────────────
    def getCategories(self) -> list:
        rows = self._query("""
            SELECT DISTINCT cat_nm FROM store_seoul
            WHERE cat_nm IS NOT NULL ORDER BY cat_nm
        """)
        return [r["cat_nm"] for r in rows]