# 위치: p01_backEnd/DAO/mapInfoDAO.py
import math
import logging
import pandas as pd
from .baseDAO import BaseDAO

logger = logging.getLogger(__name__)

# 위LNG 바운딩 박스로 시도 테이블 자동 선택
SIDO_BOUNDS = {
    "STORE_SEOUL": (37.42, 37.72, 126.73, 127.27),
    "STORE_INCHEON": (37.25, 37.63, 126.36, 126.84),
    "STORE_GYEONGGI": (36.93, 38.30, 126.36, 127.87),
    "STORE_GANGWON": (37.00, 38.62, 127.70, 129.38),
    "STORE_CHUNGBUK": (36.40, 37.32, 127.42, 128.52),
    "STORE_CHUNGNAM": (35.90, 37.07, 125.97, 127.55),
    "STORE_SEJONG": (36.40, 36.65, 127.18, 127.46),
    "STORE_DAEJEON": (36.18, 36.50, 127.27, 127.57),
    "STORE_JEONBUK": (35.49, 36.22, 126.30, 127.72),
    "STORE_JEONNAM": (34.17, 35.50, 125.90, 127.63),
    "STORE_GWANGJU": (35.04, 35.27, 126.73, 127.02),
    "STORE_GYEONGBUK": (35.57, 37.19, 127.94, 129.58),
    "STORE_GYEONGNAM": (34.60, 35.67, 127.60, 129.46),
    "STORE_BUSAN": (35.01, 35.38, 128.74, 129.32),
    "STORE_ULSAN": (35.42, 35.72, 128.97, 129.46),
    "STORE_DAEGU": (35.74, 36.02, 128.40, 128.76),
    "STORE_JEJU": (33.10, 33.65, 126.10, 126.98),
}

SIDO_NAME_MAP = {
    k.replace("소상공인_", ""): k for k in SIDO_BOUNDS
}  # "서울" → "STORE_SEOUL"

_DF_CACHE: dict = {}  # { table_name: pd.DataFrame }


def getTableByCoord(lat: float, lng: float) -> list:
    matched = [
        t
        for t, (la, lb, lna, lnb) in SIDO_BOUNDS.items()
        if la <= lat <= lb and lna <= lng <= lnb
    ]
    return matched or ["STORE_SEOUL"]


class MapInfoDAO(BaseDAO):

    # ── DataFrame 캐시 로드 ───────────────────────────────────────

    def loadCache(self, table: str, force: bool = False) -> pd.DataFrame:
        """Oracle 테이블 → pandas DataFrame 캐시 (메모리 상주)"""
        if not force and table in _DF_CACHE:
            return _DF_CACHE[table]

        con, cur = self._db_con()
        try:
            cur.execute(
                f"""
                SELECT STORE_ID, STORE_NM,
                       CAT_CD, CAT_NM, MID_CAT_NM, SUB_CAT_NM,
                       SIDO_NM, SGG_NM, ADM_NM, ROAD_ADDR,
                       FLOOR_INFO, UNIT_INFO, LNG, LAT
                FROM {table}
                WHERE LAT IS NOT NULL AND LNG IS NOT NULL
            """
            )
            cols = [d[0] for d in cur.description]
            rows = cur.fetchall()
        finally:
            self._close(con, cur)

        df = pd.DataFrame(rows, columns=cols)
        _DF_CACHE[table] = df
        logger.info(f"[MapInfoDAO] {table} → {len(df):,}행 캐시")
        return df

    def reloadCache(self, table: str = None) -> dict:
        targets = [table] if table else list(_DF_CACHE.keys())
        results = {}
        for t in targets:
            try:
                self.loadCache(t, force=True)
                results[t] = "갱신 완료"
            except Exception as e:
                results[t] = f"실패: {e}"
        return {"reloaded": results}

    # ── 반경 조회 (DB 직접, IDX_SEOUL_LATLON 인덱스 활용) ──────────

    COLS = [
        "STORE_ID",
        "STORE_NM",
        "CAT_CD",
        "CAT_NM",
        "MID_CAT_NM",
        "SUB_CAT_NM",
        "SIDO_NM",
        "SGG_NM",
        "ADM_NM",
        "ROAD_ADDR",
        "FLOOR_INFO",
        "UNIT_INFO",
        "LNG",
        "LAT",
    ]

    def _query_db(self, lat, lng, radius, limit, category=None):
        tables = getTableByCoord(lat, lng)
        lat_delta = radius / 111000.0
        lng_delta = radius / (111000.0 * abs(math.cos(math.radians(lat))) or 1)
        la_min, la_max = lat - lat_delta, lat + lat_delta
        ln_min, ln_max = lng - lng_delta, lng + lng_delta

        all_rows = []
        for table in tables:
            where_cat = "AND CAT_CD = :category" if category else ""
            sql = f"""
                SELECT STORE_ID, STORE_NM,
                       CAT_CD, CAT_NM, MID_CAT_NM, SUB_CAT_NM,
                       SIDO_NM, SGG_NM, ADM_NM, ROAD_ADDR,
                       FLOOR_INFO, UNIT_INFO, LNG, LAT
                FROM {table}
                WHERE LAT BETWEEN :lat_min AND :lat_max
                  AND LNG BETWEEN :lng_min AND :lng_max
                  {where_cat}
                FETCH FIRST :limit ROWS ONLY
            """
            params = dict(
                lat_min=la_min,
                lat_max=la_max,
                lng_min=ln_min,
                lng_max=ln_max,
                limit=limit,
            )
            if category:
                params["category"] = category
            rows = self._query(sql, params)
            # tuple → dict 변환
            all_rows.extend([dict(zip(self.COLS, r)) for r in rows])

        return all_rows[:limit]

    def getNearbyStores(self, lat, lng, radius=500, limit=500):
        return self._query_db(lat, lng, radius, limit)

    def getNearbyByCategory(self, lat, lng, category, radius=500, limit=1000):
        return self._query_db(lat, lng, radius, limit, category=category)

    # ── ADM_CD(adm_cd) 기준 전체 스토어 조회 ─────────────────
    def getStoresByAdmCd(self, adm_cd: str, limit: int = 99999) -> list:
        sql = """
            SELECT STORE_ID, STORE_NM,
                   CAT_CD, CAT_NM, MID_CAT_NM, SUB_CAT_NM,
                   SIDO_NM, SGG_NM, ADM_NM, ROAD_ADDR,
                   FLOOR_INFO, UNIT_INFO, LNG, LAT
            FROM STORE_SEOUL
            WHERE ADM_CD = :adm_cd
              AND LNG IS NOT NULL AND LAT IS NOT NULL
        """
        rows = self._query(sql, {"adm_cd": adm_cd})
        return [dict(zip(self.COLS, r)) for r in rows]

    # ── 같은 건물 상가 조회 (ROAD_ADDR 기준) + 같은 상호명 다른 지점 ──
    def getStoresByBuilding(self, road_addr: str, store_nm: str = None, exclude_store_id: str = None) -> list:
        if not road_addr:
            return []
        # 같은 건물 상가
        sql_bldg = """
            SELECT STORE_ID, STORE_NM,
                   CAT_CD, CAT_NM, MID_CAT_NM, SUB_CAT_NM,
                   SIDO_NM, SGG_NM, ADM_NM, ROAD_ADDR,
                   FLOOR_INFO, UNIT_INFO, LNG, LAT
            FROM STORE_SEOUL
            WHERE ROAD_ADDR = :road_addr
              AND LNG IS NOT NULL AND LAT IS NOT NULL
            FETCH FIRST 50 ROWS ONLY
        """
        rows = self._query(sql_bldg, {"road_addr": road_addr})
        results = [dict(zip(self.COLS, r)) for r in rows]

        # 같은 상호명 다른 지점
        if store_nm:
            sql_nm = """
                SELECT STORE_ID, STORE_NM,
                       CAT_CD, CAT_NM, MID_CAT_NM, SUB_CAT_NM,
                       SIDO_NM, SGG_NM, ADM_NM, ROAD_ADDR,
                       FLOOR_INFO, UNIT_INFO, LNG, LAT
                FROM STORE_SEOUL
                WHERE STORE_NM = :store_nm
                  AND ROAD_ADDR != :road_addr
                  AND LNG IS NOT NULL AND LAT IS NOT NULL
                FETCH FIRST 20 ROWS ONLY
            """
            rows2 = self._query(sql_nm, {"store_nm": store_nm, "road_addr": road_addr})
            results += [dict(zip(self.COLS, r)) for r in rows2]

        if exclude_store_id:
            results = [r for r in results if r.get("STORE_ID") != exclude_store_id]
        return results

    # ── 업종 목록 ────────────────────────────────────────────────

    def getCategories(self) -> list:
        rows = self._query(
            """
            SELECT DISTINCT CAT_NM
            FROM STORE_SEOUL
            WHERE CAT_NM IS NOT NULL
            ORDER BY CAT_NM
        """
        )
        return [r[0] for r in rows]

    # ── 동별 밀집도 ──────────────────────────────────────────────

    def getDongDensity(self, sido: str, sigg: str, dong: str) -> dict:
        table = next((v for k, v in SIDO_NAME_MAP.items() if k in sido), "STORE_SEOUL")
        rows = self._query(
            f"SELECT CAT_NM, COUNT(*) FROM {table} "
            "WHERE ADM_NM = :1 GROUP BY CAT_NM ORDER BY 2 DESC",
            [dong],
        )
        cat_counts = {r[0]: r[1] for r in rows if r[0]}
        total = sum(cat_counts.values())
        level = 3 if total >= 500 else 2 if total >= 200 else 1 if total >= 50 else 0
        return {
            "sido": sido,
            "sigg": sigg,
            "dong": dong,
            "total": total,
            "level": level,
            "cat_counts": cat_counts,
            "table": table,
        }

    # ── 적재 현황 ────────────────────────────────────────────────

    def getStatus(self) -> dict:
        results = {}
        total = 0
        for table in SIDO_BOUNDS:
            try:
                rows = self._query(f"SELECT COUNT(*) FROM {table}")
                cnt = rows[0][0]
            except Exception:
                cnt = "테이블 없음"
            results[table] = cnt
            if isinstance(cnt, int):
                total += cnt
        return {"grand_total": total, "by_table": results}

    # ── CSV 배치 MERGE ───────────────────────────────────────────

    def insertBatch(self, records: list, table_name: str):
        con, cur = self._db_con()
        sql = f"""
            MERGE INTO {table_name} t
            USING (SELECT
                :1 AS STORE_ID, :2 AS STORE_NM, :3 AS 지점명,
                :4 AS CAT_CD, :5 AS CAT_NM,
                :6 AS 상권업종중분류코드, :7 AS MID_CAT_NM,
                :8 AS 상권업종소분류코드, :9 AS SUB_CAT_NM,
                :10 AS 표준산업분류코드, :11 AS 표준산업분류명,
                :12 AS 시도코드, :13 AS SIDO_NM,
                :14 AS 시군구코드, :15 AS SGG_NM,
                :16 AS ADM_CD, :17 AS ADM_NM,
                :18 AS 법정동코드, :19 AS 법정동명,
                :20 AS 지번코드, :21 AS 대지구분코드, :22 AS 대지구분명,
                :23 AS 지번본번지, :24 AS 지번부번지, :25 AS 지번주소,
                :26 AS 도로명코드, :27 AS 도로명,
                :28 AS 건물본번지, :29 AS 건물부번지,
                :30 AS 건물관리번호, :31 AS 건물명, :32 AS ROAD_ADDR,
                :33 AS 구우편번호, :34 AS 신우편번호,
                :35 AS 동정보, :36 AS FLOOR_INFO, :37 AS UNIT_INFO,
                :38 AS LNG, :39 AS LAT
            FROM DUAL) s
            ON (t.STORE_ID = s.STORE_ID)
            WHEN MATCHED THEN UPDATE SET
                t.STORE_NM=s.STORE_NM, t.지점명=s.지점명,
                t.CAT_CD=s.CAT_CD, t.CAT_NM=s.CAT_NM,
                t.상권업종중분류코드=s.상권업종중분류코드, t.MID_CAT_NM=s.MID_CAT_NM,
                t.상권업종소분류코드=s.상권업종소분류코드, t.SUB_CAT_NM=s.SUB_CAT_NM,
                t.표준산업분류코드=s.표준산업분류코드, t.표준산업분류명=s.표준산업분류명,
                t.시도코드=s.시도코드, t.SIDO_NM=s.SIDO_NM,
                t.시군구코드=s.시군구코드, t.SGG_NM=s.SGG_NM,
                t.ADM_CD=s.ADM_CD, t.ADM_NM=s.ADM_NM,
                t.법정동코드=s.법정동코드, t.법정동명=s.법정동명,
                t.지번코드=s.지번코드, t.대지구분코드=s.대지구분코드, t.대지구분명=s.대지구분명,
                t.지번본번지=s.지번본번지, t.지번부번지=s.지번부번지, t.지번주소=s.지번주소,
                t.도로명코드=s.도로명코드, t.도로명=s.도로명,
                t.건물본번지=s.건물본번지, t.건물부번지=s.건물부번지,
                t.건물관리번호=s.건물관리번호, t.건물명=s.건물명, t.ROAD_ADDR=s.ROAD_ADDR,
                t.구우편번호=s.구우편번호, t.신우편번호=s.신우편번호,
                t.동정보=s.동정보, t.FLOOR_INFO=s.FLOOR_INFO, t.UNIT_INFO=s.UNIT_INFO,
                t.LNG=s.LNG, t.LAT=s.LAT
            WHEN NOT MATCHED THEN INSERT (
                STORE_ID, STORE_NM, 지점명,
                CAT_CD, CAT_NM,
                상권업종중분류코드, MID_CAT_NM,
                상권업종소분류코드, SUB_CAT_NM,
                표준산업분류코드, 표준산업분류명,
                시도코드, SIDO_NM, 시군구코드, SGG_NM,
                ADM_CD, ADM_NM, 법정동코드, 법정동명,
                지번코드, 대지구분코드, 대지구분명,
                지번본번지, 지번부번지, 지번주소,
                도로명코드, 도로명, 건물본번지, 건물부번지,
                건물관리번호, 건물명, ROAD_ADDR,
                구우편번호, 신우편번호, 동정보, FLOOR_INFO, UNIT_INFO,
                LNG, LAT
            ) VALUES (
                s.STORE_ID, s.STORE_NM, s.지점명,
                s.CAT_CD, s.CAT_NM,
                s.상권업종중분류코드, s.MID_CAT_NM,
                s.상권업종소분류코드, s.SUB_CAT_NM,
                s.표준산업분류코드, s.표준산업분류명,
                s.시도코드, s.SIDO_NM, s.시군구코드, s.SGG_NM,
                s.ADM_CD, s.ADM_NM, s.법정동코드, s.법정동명,
                s.지번코드, s.대지구분코드, s.대지구분명,
                s.지번본번지, s.지번부번지, s.지번주소,
                s.도로명코드, s.도로명, s.건물본번지, s.건물부번지,
                s.건물관리번호, s.건물명, s.ROAD_ADDR,
                s.구우편번호, s.신우편번호, s.동정보, s.FLOOR_INFO, s.UNIT_INFO,
                s.LNG, s.LAT
            )
        """
        try:
            cur.executemany(sql, records)
            con.commit()
        except Exception as e:
            con.rollback()
            raise e
        finally:
            self._close(con, cur)


# ── 하위 호환: mapController의 _get_df(table) 호출 지원 ────────────
# mapController lifespan / _preload_caches 에서 사용
_dao_instance = None


def _get_df(table: str, force: bool = False):
    global _dao_instance
    if _dao_instance is None:
        _dao_instance = MapInfoDAO()
    return _dao_instance.loadCache(table, force=force)