# 위치: p01_backEnd/DAO/mapInfoDAO.py
import math
from fable.oracleDBConnect import OracleDBConnect

DB_INFO = "fable/1@//195.168.9.168:1521/xe"

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


def getTableByCoord(lat: float, lng: float) -> list:
    """위경도로 해당 시도 테이블명 반환 (복수 가능 - 경계지역 대비)"""
    matched = []
    for table, (lat_min, lat_max, lng_min, lng_max) in SIDO_BOUNDS.items():
        if lat_min <= lat <= lat_max and lng_min <= lng <= lng_max:
            matched.append(table)
    return matched if matched else ["소상공인_서울"]  # 기본값


class MapInfoDAO:

    # ── 공통: 캐시 DataFrame에서 반경 필터링 ──────────────────────
    def _query_cache(
        self, lat: float, lng: float, radius: float, limit: int, category: str = None
    ):
        """
        서버 시작 시 올려둔 _DF_CACHE에서 pandas로 바운딩박스 필터링
        캐시 미적재 테이블은 DB 직접 조회로 폴백
        """
        tables = getTableByCoord(lat, lng)
        lat_delta = radius / 111000.0
        lng_delta = radius / (111000.0 * abs(math.cos(math.radians(lat))) or 1)
        lat_min, lat_max = lat - lat_delta, lat + lat_delta
        lng_min, lng_max = lng - lng_delta, lng + lng_delta

        all_rows = []
        for table in tables:
            if table in _DF_CACHE:
                # ── 캐시 히트: pandas 필터링 (매우 빠름) ──
                df = _DF_CACHE[table]
                mask = (
                    (df["위도"] >= lat_min)
                    & (df["위도"] <= lat_max)
                    & (df["경도"] >= lng_min)
                    & (df["경도"] <= lng_max)
                )
                if category:
                    mask &= df["상권업종대분류명"] == category
                chunk = df[mask].head(limit)
                all_rows.extend(chunk.to_dict(orient="records"))
            else:
                # ── 캐시 미스: DB 직접 조회 폴백 ──
                con, cur = OracleDBConnect.makeConCur(DB_INFO)
                try:
                    where_cat = "AND 상권업종대분류명 = :category" if category else ""
                    sql = f"""
                        SELECT 상가업소번호, 상호명,
                               상권업종대분류명, 상권업종중분류명, 상권업종소분류명,
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
                        lat_min=lat_min,
                        lat_max=lat_max,
                        lng_min=lng_min,
                        lng_max=lng_max,
                        limit=limit,
                    )
                    if category:
                        params["category"] = category
                    cur.execute(sql, params)
                    cols = [d[0] for d in cur.description]
                    all_rows.extend([dict(zip(cols, r)) for r in cur.fetchall()])
                finally:
                    OracleDBConnect.closeConCur(con, cur)

        return all_rows[:limit]

    # ── 1. 반경 내 상권 전체 조회 ──────────────────────────────────
    def getNearbyStores(
        self, lat: float, lng: float, radius: float = 500, limit: int = 500
    ):
        return self._query_cache(lat, lng, radius, limit)

    # ── 2. 업종 대분류 필터 조회 ───────────────────────────────────
    def getNearbyByCategory(
        self,
        lat: float,
        lng: float,
        category: str,
        radius: float = 500,
        limit: int = 1000,
    ):
        return self._query_cache(lat, lng, radius, limit, category=category)

    # ── 3. 업종 대분류 목록 ────────────────────────────────────────
    def getCategories(self):
        con, cur = OracleDBConnect.makeConCur(DB_INFO)
        try:
            sql = """
                SELECT DISTINCT 상권업종대분류명
                FROM 소상공인_서울
                WHERE 상권업종대분류명 IS NOT NULL
                ORDER BY 상권업종대분류명
            """
            cur.execute(sql)
            return [row[0] for row in cur.fetchall()]
        finally:
            OracleDBConnect.closeConCur(con, cur)

    # ── 4. 테이블별 적재 현황 ──────────────────────────────────────
    def getStatus(self):
        results = {}
        total = 0
        for table in SIDO_BOUNDS.keys():
            con, cur = OracleDBConnect.makeConCur(DB_INFO)
            try:
                cur.execute(f"SELECT COUNT(*) FROM {table}")
                count = cur.fetchone()[0]
                results[table] = count
                total += count
            except Exception:
                results[table] = "테이블 없음"
            finally:
                OracleDBConnect.closeConCur(con, cur)
        return {"grand_total": total, "by_table": results}

    # ── 5. CSV 배치 MERGE  ─────────────────────────────────────────
    def insertBatch(self, records: list, table_name: str):
        con, cur = OracleDBConnect.makeConCur(DB_INFO)
        try:
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
            cur.executemany(sql, records)
            con.commit()
        except Exception as e:
            con.rollback()
            raise e
        finally:
            OracleDBConnect.closeConCur(con, cur)

    # ── 6. 동별 소상공인 밀집도 ───────────────────────────────────
    def getDongDensity(self, sido: str, sigg: str, dong: str) -> dict:
        """
        행정동 클릭 시 소상공인 밀집도 + 업종 분포 반환
        sido/sigg 로 테이블 선택, dong 으로 필터
        """
        # 시도명 → 테이블 매핑 (SIDO_BOUNDS 키 기준)
        SIDO_NAME_MAP = {
            "서울": "소상공인_서울",
            "경기": "소상공인_경기",
            "인천": "소상공인_인천",
            "부산": "소상공인_부산",
            "대구": "소상공인_대구",
            "광주": "소상공인_광주",
            "대전": "소상공인_대전",
            "울산": "소상공인_울산",
            "세종": "소상공인_세종",
            "강원": "소상공인_강원",
            "충북": "소상공인_충북",
            "충남": "소상공인_충남",
            "전북": "소상공인_전북",
            "전남": "소상공인_전남",
            "경북": "소상공인_경북",
            "경남": "소상공인_경남",
            "제주": "소상공인_제주",
        }
        table = next(
            (v for k, v in SIDO_NAME_MAP.items() if k in sido), "소상공인_서울"
        )

        con, cur = OracleDBConnect.makeConCur(DB_INFO)
        try:
            sql = f"""
                SELECT 상권업종대분류명, COUNT(*) AS cnt
                FROM {table}
                WHERE 행정동명 = :dong
                GROUP BY 상권업종대분류명
                ORDER BY cnt DESC
            """
            cur.execute(sql, dong=dong)
            rows = cur.fetchall()
        finally:
            OracleDBConnect.closeConCur(con, cur)

        cat_counts = {r[0]: r[1] for r in rows if r[0]}
        total = sum(cat_counts.values())

        # 밀집도 등급 0~3
        if total >= 500:
            level = 3
        elif total >= 200:
            level = 2
        elif total >= 50:
            level = 1
        else:
            level = 0

        return {
            "sido": sido,
            "sigg": sigg,
            "dong": dong,
            "total": total,
            "level": level,
            "cat_counts": cat_counts,
            "table": table,
        }

    # ── 7. 캐시 강제 갱신 ─────────────────────────────────────────
    def reloadCache(self, table: str = None) -> dict:
        """
        메모리 DataFrame 캐시 강제 갱신
        table 지정 시 해당 테이블만, None 이면 로드된 전체 갱신
        """
        targets = [table] if table else list(_DF_CACHE.keys())
        results = {}
        for t in targets:
            try:
                _get_df(t, force=True)
                results[t] = "갱신 완료"
            except Exception as e:
                results[t] = f"실패: {e}"
        return {"reloaded": results}


# ════════════════════════════════════════════════════════════════════
# DataFrame 메모리 캐시 (_get_df)
# mapController 의 lifespan / _preload_caches 에서 사용
# ════════════════════════════════════════════════════════════════════

import pandas as pd

_DF_CACHE: dict = {}  # { table_name: pd.DataFrame }


def _get_df(table: str, force: bool = False) -> pd.DataFrame:
    """
    Oracle 테이블 → pandas DataFrame 캐시 (메모리 상주)
    force=True 이면 기존 캐시를 무시하고 재조회
    """
    if not force and table in _DF_CACHE:
        return _DF_CACHE[table]

    con, cur = OracleDBConnect.makeConCur(DB_INFO)
    try:
        cur.execute(
            f"""
            SELECT 상가업소번호, 상호명,
                   상권업종대분류명, 상권업종중분류명, 상권업종소분류명,
                   시도명, 시군구명, 행정동명, 도로명주소,
                   층정보, 호정보, 경도, 위도
            FROM {table}
            WHERE 위도 IS NOT NULL AND 경도 IS NOT NULL
        """
        )
        cols = [d[0] for d in cur.description]
        rows = cur.fetchall()
    finally:
        OracleDBConnect.closeConCur(con, cur)

    df = pd.DataFrame(rows, columns=cols)
    _DF_CACHE[table] = df
    print(f"[_get_df] {table} → {len(df):,}행 캐시 완료")
    return df
