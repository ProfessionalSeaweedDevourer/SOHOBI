# 위치: p01_backEnd/DAO/mapInfoDAO.py
import math
import logging
import pandas as pd
from .baseDAO import BaseDAO

logger = logging.getLogger(__name__)

# 위경도 바운딩 박스로 시도 테이블 자동 선택
SIDO_BOUNDS = {
    "소상공인_서울": (37.42, 37.72, 126.73, 127.27),
    "소상공인_인천": (37.25, 37.63, 126.36, 126.84),
    "소상공인_경기": (36.93, 38.30, 126.36, 127.87),
    "소상공인_강원": (37.00, 38.62, 127.70, 129.38),
    "소상공인_충북": (36.40, 37.32, 127.42, 128.52),
    "소상공인_충남": (35.90, 37.07, 125.97, 127.55),
    "소상공인_세종": (36.40, 36.65, 127.18, 127.46),
    "소상공인_대전": (36.18, 36.50, 127.27, 127.57),
    "소상공인_전북": (35.49, 36.22, 126.30, 127.72),
    "소상공인_전남": (34.17, 35.50, 125.90, 127.63),
    "소상공인_광주": (35.04, 35.27, 126.73, 127.02),
    "소상공인_경북": (35.57, 37.19, 127.94, 129.58),
    "소상공인_경남": (34.60, 35.67, 127.60, 129.46),
    "소상공인_부산": (35.01, 35.38, 128.74, 129.32),
    "소상공인_울산": (35.42, 35.72, 128.97, 129.46),
    "소상공인_대구": (35.74, 36.02, 128.40, 128.76),
    "소상공인_제주": (33.10, 33.65, 126.10, 126.98),
}

SIDO_NAME_MAP = {
    k.replace("소상공인_", ""): k for k in SIDO_BOUNDS
}  # "서울" → "소상공인_서울"

_DF_CACHE: dict = {}  # { table_name: pd.DataFrame }


def getTableByCoord(lat: float, lng: float) -> list:
    matched = [
        t
        for t, (la, lb, lna, lnb) in SIDO_BOUNDS.items()
        if la <= lat <= lb and lna <= lng <= lnb
    ]
    return matched or ["소상공인_서울"]


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
                SELECT 상가업소번호, 상호명,
                       상권업종대분류코드, 상권업종대분류명, 상권업종중분류명, 상권업종소분류명,
                       시도명, 시군구명, 행정동명, 도로명주소,
                       층정보, 호정보, 경도, 위도
                FROM {table}
                WHERE 위도 IS NOT NULL AND 경도 IS NOT NULL
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

    # ── 반경 조회 (캐시 우선, 캐시 미스 시 DB 직접) ──────────────

    def _query_cache(self, lat, lng, radius, limit, category=None):
        tables = getTableByCoord(lat, lng)
        lat_delta = radius / 111000.0
        lng_delta = radius / (111000.0 * abs(math.cos(math.radians(lat))) or 1)
        la_min, la_max = lat - lat_delta, lat + lat_delta
        ln_min, ln_max = lng - lng_delta, lng + lng_delta

        all_rows = []
        for table in tables:
            if table in _DF_CACHE:
                df = _DF_CACHE[table]
                mask = (
                    (df["위도"] >= la_min)
                    & (df["위도"] <= la_max)
                    & (df["경도"] >= ln_min)
                    & (df["경도"] <= ln_max)
                )
                if category:
                    mask &= df["상권업종대분류명"] == category
                all_rows.extend(df[mask].head(limit).to_dict(orient="records"))
            else:
                where_cat = "AND 상권업종대분류명 = :category" if category else ""
                sql = f"""
                    SELECT 상가업소번호, 상호명,
                           상권업종대분류코드, 상권업종대분류명, 상권업종중분류명, 상권업종소분류명,
                           시도명, 시군구명, 행정동명, 도로명주소,
                           층정보, 호정보, 경도, 위도
                    FROM {table}
                    WHERE 위도 BETWEEN :lat_min AND :lat_max
                      AND 경도 BETWEEN :lng_min AND :lng_max
                      AND 위도 IS NOT NULL AND 경도 IS NOT NULL
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
                all_rows.extend(rows)

        return all_rows[:limit]

    def getNearbyStores(self, lat, lng, radius=500, limit=500):
        return self._query_cache(lat, lng, radius, limit)

    def getNearbyByCategory(self, lat, lng, category, radius=500, limit=1000):
        return self._query_cache(lat, lng, radius, limit, category=category)

    # ── 업종 목록 ────────────────────────────────────────────────

    def getCategories(self) -> list:
        rows = self._query(
            """
            SELECT DISTINCT 상권업종대분류명
            FROM 소상공인_서울
            WHERE 상권업종대분류명 IS NOT NULL
            ORDER BY 상권업종대분류명
        """
        )
        return [r[0] for r in rows]

    # ── 동별 밀집도 ──────────────────────────────────────────────

    def getDongDensity(self, sido: str, sigg: str, dong: str) -> dict:
        table = next(
            (v for k, v in SIDO_NAME_MAP.items() if k in sido), "소상공인_서울"
        )
        rows = self._query(
            f"SELECT 상권업종대분류명, COUNT(*) FROM {table} "
            "WHERE 행정동명 = :1 GROUP BY 상권업종대분류명 ORDER BY 2 DESC",
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
                :1 AS 상가업소번호, :2 AS 상호명, :3 AS 지점명,
                :4 AS 상권업종대분류코드, :5 AS 상권업종대분류명,
                :6 AS 상권업종중분류코드, :7 AS 상권업종중분류명,
                :8 AS 상권업종소분류코드, :9 AS 상권업종소분류명,
                :10 AS 표준산업분류코드, :11 AS 표준산업분류명,
                :12 AS 시도코드, :13 AS 시도명,
                :14 AS 시군구코드, :15 AS 시군구명,
                :16 AS 행정동코드, :17 AS 행정동명,
                :18 AS 법정동코드, :19 AS 법정동명,
                :20 AS 지번코드, :21 AS 대지구분코드, :22 AS 대지구분명,
                :23 AS 지번본번지, :24 AS 지번부번지, :25 AS 지번주소,
                :26 AS 도로명코드, :27 AS 도로명,
                :28 AS 건물본번지, :29 AS 건물부번지,
                :30 AS 건물관리번호, :31 AS 건물명, :32 AS 도로명주소,
                :33 AS 구우편번호, :34 AS 신우편번호,
                :35 AS 동정보, :36 AS 층정보, :37 AS 호정보,
                :38 AS 경도, :39 AS 위도
            FROM DUAL) s
            ON (t.상가업소번호 = s.상가업소번호)
            WHEN MATCHED THEN UPDATE SET
                t.상호명=s.상호명, t.지점명=s.지점명,
                t.상권업종대분류코드=s.상권업종대분류코드, t.상권업종대분류명=s.상권업종대분류명,
                t.상권업종중분류코드=s.상권업종중분류코드, t.상권업종중분류명=s.상권업종중분류명,
                t.상권업종소분류코드=s.상권업종소분류코드, t.상권업종소분류명=s.상권업종소분류명,
                t.표준산업분류코드=s.표준산업분류코드, t.표준산업분류명=s.표준산업분류명,
                t.시도코드=s.시도코드, t.시도명=s.시도명,
                t.시군구코드=s.시군구코드, t.시군구명=s.시군구명,
                t.행정동코드=s.행정동코드, t.행정동명=s.행정동명,
                t.법정동코드=s.법정동코드, t.법정동명=s.법정동명,
                t.지번코드=s.지번코드, t.대지구분코드=s.대지구분코드, t.대지구분명=s.대지구분명,
                t.지번본번지=s.지번본번지, t.지번부번지=s.지번부번지, t.지번주소=s.지번주소,
                t.도로명코드=s.도로명코드, t.도로명=s.도로명,
                t.건물본번지=s.건물본번지, t.건물부번지=s.건물부번지,
                t.건물관리번호=s.건물관리번호, t.건물명=s.건물명, t.도로명주소=s.도로명주소,
                t.구우편번호=s.구우편번호, t.신우편번호=s.신우편번호,
                t.동정보=s.동정보, t.층정보=s.층정보, t.호정보=s.호정보,
                t.경도=s.경도, t.위도=s.위도
            WHEN NOT MATCHED THEN INSERT (
                상가업소번호, 상호명, 지점명,
                상권업종대분류코드, 상권업종대분류명,
                상권업종중분류코드, 상권업종중분류명,
                상권업종소분류코드, 상권업종소분류명,
                표준산업분류코드, 표준산업분류명,
                시도코드, 시도명, 시군구코드, 시군구명,
                행정동코드, 행정동명, 법정동코드, 법정동명,
                지번코드, 대지구분코드, 대지구분명,
                지번본번지, 지번부번지, 지번주소,
                도로명코드, 도로명, 건물본번지, 건물부번지,
                건물관리번호, 건물명, 도로명주소,
                구우편번호, 신우편번호, 동정보, 층정보, 호정보,
                경도, 위도
            ) VALUES (
                s.상가업소번호, s.상호명, s.지점명,
                s.상권업종대분류코드, s.상권업종대분류명,
                s.상권업종중분류코드, s.상권업종중분류명,
                s.상권업종소분류코드, s.상권업종소분류명,
                s.표준산업분류코드, s.표준산업분류명,
                s.시도코드, s.시도명, s.시군구코드, s.시군구명,
                s.행정동코드, s.행정동명, s.법정동코드, s.법정동명,
                s.지번코드, s.대지구분코드, s.대지구분명,
                s.지번본번지, s.지번부번지, s.지번주소,
                s.도로명코드, s.도로명, s.건물본번지, s.건물부번지,
                s.건물관리번호, s.건물명, s.도로명주소,
                s.구우편번호, s.신우편번호, s.동정보, s.층정보, s.호정보,
                s.경도, s.위도
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
