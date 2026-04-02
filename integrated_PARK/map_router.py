"""
지도 데이터 API 라우터
- /realestate/* 엔드포인트: DongPanel 매출·점포수 데이터
- /map/* 엔드포인트: 상가 팝업 데이터

PostgreSQL (Azure) sangkwon_sales, sangkwon_store 테이블 기반.
개별 상가 목록 (/map/*)은 현재 DB 미지원 → 빈 응답 반환.
"""

import logging
from contextlib import contextmanager
from typing import Optional

from fastapi import APIRouter, Query

from db.repository import CommercialRepository

logger = logging.getLogger(__name__)
router = APIRouter()

_repo = CommercialRepository()


@contextmanager
def _db():
    conn = _repo._connect()
    try:
        yield conn
    finally:
        _repo._release(conn)


def _latest_qtr_cond(quarter: str) -> tuple[str, list]:
    """quarter 파라미터 처리: 비어있으면 최신 분기 서브쿼리, 있으면 직접 비교"""
    if quarter:
        return "AND base_yr_qtr_cd = %s", [quarter]
    return "AND base_yr_qtr_cd = (SELECT MAX(base_yr_qtr_cd) FROM sangkwon_sales)", []


def _latest_store_qtr_cond(quarter: str) -> tuple[str, list]:
    if quarter:
        return "AND base_yr_qtr_cd = %s", [quarter]
    return "AND base_yr_qtr_cd = (SELECT MAX(base_yr_qtr_cd) FROM sangkwon_store)", []


def _fmt_row(row: dict) -> dict:
    """Oracle _format_sangkwon_row 와 동일한 키 구조로 변환"""
    return {
        "dong":         row.get("adm_nm", ""),
        "code":         str(row.get("adm_cd", "")),
        "quarter":      row.get("base_yr_qtr_cd", ""),
        "sales":        row.get("tot_sales_amt"),
        "sales_male":   row.get("ml_sales_amt"),
        "sales_female": row.get("fml_sales_amt"),
        "sales_mdwk":   row.get("mdwk_sales_amt"),
        "sales_wkend":  row.get("wkend_sales_amt"),
        "age20":        row.get("age20_amt"),
        "age30":        row.get("age30_amt"),
        "age40":        row.get("age40_amt"),
        "age50":        row.get("age50_amt"),
    }


# ════════════════════════════════════════════════════════════════
# /realestate 엔드포인트
# ════════════════════════════════════════════════════════════════

@router.get("/realestate/sangkwon")
def get_sangkwon(
    adm_cd:  str = Query("", description="행정동코드 (우선)"),
    dong:    str = Query("", description="행정동명 (fallback)"),
    gu:      str = Query("", description="구이름"),
    quarter: str = Query("", description="분기코드 (비우면 최신)"),
):
    """행정동 전체 매출 합산 (업종 무관)"""
    logger.info("[sangkwon] adm_cd=%s dong=%s quarter=%s", adm_cd, dong, quarter or "최신")

    qtr_cond, qtr_params = _latest_qtr_cond(quarter)

    if adm_cd:
        sql = f"""
            SELECT adm_cd, adm_nm, base_yr_qtr_cd,
                   SUM(tot_sales_amt)   AS tot_sales_amt,
                   SUM(ml_sales_amt)    AS ml_sales_amt,
                   SUM(fml_sales_amt)   AS fml_sales_amt,
                   SUM(mdwk_sales_amt)  AS mdwk_sales_amt,
                   SUM(wkend_sales_amt) AS wkend_sales_amt,
                   SUM(age20_amt)       AS age20_amt,
                   SUM(age30_amt)       AS age30_amt,
                   SUM(age40_amt)       AS age40_amt,
                   SUM(age50_amt)       AS age50_amt
            FROM sangkwon_sales
            WHERE adm_cd = %s {qtr_cond}
            GROUP BY adm_cd, adm_nm, base_yr_qtr_cd
            LIMIT 1
        """
        params = [adm_cd] + qtr_params
    elif dong:
        gu_cond = "AND adm_nm LIKE %s" if gu else ""
        sql = f"""
            SELECT adm_cd, adm_nm, base_yr_qtr_cd,
                   SUM(tot_sales_amt)   AS tot_sales_amt,
                   SUM(ml_sales_amt)    AS ml_sales_amt,
                   SUM(fml_sales_amt)   AS fml_sales_amt,
                   SUM(mdwk_sales_amt)  AS mdwk_sales_amt,
                   SUM(wkend_sales_amt) AS wkend_sales_amt,
                   SUM(age20_amt)       AS age20_amt,
                   SUM(age30_amt)       AS age30_amt,
                   SUM(age40_amt)       AS age40_amt,
                   SUM(age50_amt)       AS age50_amt
            FROM sangkwon_sales
            WHERE adm_nm = %s {gu_cond} {qtr_cond}
            GROUP BY adm_cd, adm_nm, base_yr_qtr_cd
            LIMIT 1
        """
        params = [dong]
        if gu:
            params.append(f"%{gu}%")
        params += qtr_params
    else:
        return {"data": None, "avg": None, "message": "adm_cd 또는 dong 파라미터 필요"}

    try:
        with _db() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, params)
                cols = [d[0] for d in cur.description]
                row = cur.fetchone()
    except Exception as e:
        logger.error("[sangkwon] 쿼리 실패: %s", e)
        return {"data": None, "avg": None, "message": str(e)}

    if not row:
        return {"data": None, "avg": None, "message": "데이터 없음"}

    data = _fmt_row(dict(zip(cols, row)))

    # 전체 분기 평균 계산
    avg = None
    try:
        cd = data["code"]
        avg_sql = """
            WITH qtr_agg AS (
                SELECT base_yr_qtr_cd,
                       SUM(tot_sales_amt)   AS tot_sales_amt,
                       SUM(ml_sales_amt)    AS ml_sales_amt,
                       SUM(fml_sales_amt)   AS fml_sales_amt,
                       SUM(mdwk_sales_amt)  AS mdwk_sales_amt,
                       SUM(wkend_sales_amt) AS wkend_sales_amt,
                       SUM(age20_amt)       AS age20_amt,
                       SUM(age30_amt)       AS age30_amt,
                       SUM(age40_amt)       AS age40_amt,
                       SUM(age50_amt)       AS age50_amt
                FROM sangkwon_sales WHERE adm_cd = %s
                GROUP BY base_yr_qtr_cd
            )
            SELECT
                AVG(tot_sales_amt)   AS tot_sales_amt,
                AVG(ml_sales_amt)    AS ml_sales_amt,
                AVG(fml_sales_amt)   AS fml_sales_amt,
                AVG(mdwk_sales_amt)  AS mdwk_sales_amt,
                AVG(wkend_sales_amt) AS wkend_sales_amt,
                AVG(age20_amt)       AS age20_amt,
                AVG(age30_amt)       AS age30_amt,
                AVG(age40_amt)       AS age40_amt,
                AVG(age50_amt)       AS age50_amt
            FROM qtr_agg
        """
        with _db() as conn:
            with conn.cursor() as cur:
                cur.execute(avg_sql, [cd])
                avg_cols = [d[0] for d in cur.description]
                avg_row = cur.fetchone()
        if avg_row:
            avg_dict = dict(zip(avg_cols, avg_row))
            avg_dict["adm_nm"]         = dict(zip(cols, row))["adm_nm"]
            avg_dict["adm_cd"]         = cd
            avg_dict["base_yr_qtr_cd"] = "avg"
            avg = _fmt_row(avg_dict)
    except Exception as e:
        logger.warning("[sangkwon] 평균 계산 실패: %s", e)

    return {"data": data, "avg": avg}


@router.get("/realestate/sangkwon-quarters")
def get_sangkwon_quarters():
    """이용 가능한 분기 목록"""
    try:
        with _db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT DISTINCT base_yr_qtr_cd FROM sangkwon_sales ORDER BY base_yr_qtr_cd"
                )
                quarters = [r[0] for r in cur.fetchall()]
        return {"quarters": quarters, "latest": quarters[-1] if quarters else None}
    except Exception as e:
        logger.error("[sangkwon-quarters] %s", e)
        return {"quarters": [], "latest": None}


@router.get("/realestate/search-dong")
def search_dong(q: str = Query(..., description="동이름 검색어")):
    """행정동명 LIKE 검색"""
    logger.info("[search-dong] q=%s", q)
    try:
        with _db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT DISTINCT adm_cd, adm_nm FROM sangkwon_sales "
                    "WHERE adm_nm LIKE %s ORDER BY adm_nm LIMIT 30",
                    [f"%{q}%"],
                )
                rows = [
                    {"adm_cd": str(r[0]), "adm_nm": r[1], "type": "행정동"}
                    for r in cur.fetchall()
                ]
        return {"count": len(rows), "data": rows}
    except Exception as e:
        logger.error("[search-dong] %s", e)
        return {"count": 0, "data": []}


@router.get("/realestate/sangkwon-svc")
def get_sangkwon_svc(
    adm_cd:  str = Query(..., description="행정동코드"),
    quarter: str = Query("", description="분기코드 (비우면 최신)"),
):
    """행정동 업종별 매출 (소분류 기준 — SVC_INDUTY_MAP 미사용)"""
    logger.info("[sangkwon-svc] adm_cd=%s quarter=%s", adm_cd, quarter or "최신")
    qtr_cond, qtr_params = _latest_qtr_cond(quarter)
    sql = f"""
        SELECT svc_induty_cd        AS svc_cd,
               svc_induty_nm        AS svc_nm,
               SUM(tot_sales_amt)   AS tot_sales_amt,
               SUM(ml_sales_amt)    AS ml_sales_amt,
               SUM(fml_sales_amt)   AS fml_sales_amt,
               SUM(mdwk_sales_amt)  AS mdwk_sales_amt,
               SUM(wkend_sales_amt) AS wkend_sales_amt,
               SUM(age20_amt)       AS age20_amt,
               SUM(age30_amt)       AS age30_amt,
               SUM(age40_amt)       AS age40_amt,
               SUM(age50_amt)       AS age50_amt
        FROM sangkwon_sales
        WHERE adm_cd = %s {qtr_cond}
        GROUP BY svc_induty_cd, svc_induty_nm
        ORDER BY tot_sales_amt DESC NULLS LAST
    """
    try:
        with _db() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, [adm_cd] + qtr_params)
                cols = [d[0] for d in cur.description]
                rows = [dict(zip(cols, r)) for r in cur.fetchall()]
        return {"adm_cd": adm_cd, "count": len(rows), "data": rows}
    except Exception as e:
        logger.error("[sangkwon-svc] %s", e)
        return {"adm_cd": adm_cd, "count": 0, "data": []}


@router.get("/realestate/sangkwon-svc-by-cat")
def get_sangkwon_svc_by_cat(
    adm_cd:  str = Query(..., description="행정동코드"),
    cat_cd:  str = Query(..., description="대분류코드"),
    quarter: str = Query("", description="분기코드"),
):
    """대분류 기준 소분류별 매출 (SVC_INDUTY_MAP 미지원 → cat_cd LIKE 필터 대체)"""
    logger.info("[sangkwon-svc-by-cat] adm_cd=%s cat_cd=%s", adm_cd, cat_cd)
    qtr_cond, qtr_params = _latest_qtr_cond(quarter)
    sql = f"""
        SELECT svc_induty_cd        AS svc_cd,
               svc_induty_nm        AS svc_nm,
               SUM(tot_sales_amt)   AS tot_sales_amt,
               SUM(ml_sales_amt)    AS ml_sales_amt,
               SUM(fml_sales_amt)   AS fml_sales_amt,
               SUM(mdwk_sales_amt)  AS mdwk_sales_amt,
               SUM(wkend_sales_amt) AS wkend_sales_amt,
               SUM(age20_amt)       AS age20_amt,
               SUM(age30_amt)       AS age30_amt,
               SUM(age40_amt)       AS age40_amt,
               SUM(age50_amt)       AS age50_amt
        FROM sangkwon_sales
        WHERE adm_cd = %s
          AND svc_induty_cd LIKE %s
          {qtr_cond}
        GROUP BY svc_induty_cd, svc_induty_nm
        ORDER BY tot_sales_amt DESC NULLS LAST
    """
    try:
        with _db() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, [adm_cd, f"{cat_cd}%"] + qtr_params)
                cols = [d[0] for d in cur.description]
                rows = [dict(zip(cols, r)) for r in cur.fetchall()]
        return {"adm_cd": adm_cd, "cat_cd": cat_cd, "count": len(rows), "data": rows}
    except Exception as e:
        logger.error("[sangkwon-svc-by-cat] %s", e)
        return {"adm_cd": adm_cd, "cat_cd": cat_cd, "count": 0, "data": []}


@router.get("/realestate/sangkwon-store")
def get_sangkwon_store(
    adm_cd:  str = Query(..., description="행정동코드"),
    quarter: str = Query("", description="분기코드 (비우면 최신)"),
    svc_cd:  str = Query("", description="업종 대분류 코드 (비우면 전체)"),
):
    """행정동 업종별 점포수·개폐업률"""
    logger.info("[sangkwon-store] adm_cd=%s quarter=%s", adm_cd, quarter or "최신")
    qtr_cond, qtr_params = _latest_store_qtr_cond(quarter)
    svc_cond = "AND svc_induty_cd LIKE %s" if svc_cd else ""
    sql = f"""
        SELECT svc_induty_cd               AS svc_cd,
               svc_induty_nm               AS svc_nm,
               SUM(stor_co)                AS stor_co,
               SUM(similr_induty_stor_co)  AS similr_stor_co,
               SUM(frc_stor_co)            AS frc_stor_co,
               ROUND(AVG(opbiz_rt), 1)     AS opbiz_rt,
               SUM(opbiz_stor_co)          AS opbiz_stor_co,
               ROUND(AVG(clsbiz_rt), 1)    AS clsbiz_rt,
               SUM(clsbiz_stor_co)         AS clsbiz_stor_co
        FROM sangkwon_store
        WHERE adm_cd = %s {qtr_cond} {svc_cond}
        GROUP BY svc_induty_cd, svc_induty_nm
        ORDER BY stor_co DESC NULLS LAST
    """
    params = [adm_cd] + qtr_params
    if svc_cd:
        params.append(f"{svc_cd}%")
    try:
        with _db() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, params)
                cols = [d[0] for d in cur.description]
                rows = [dict(zip(cols, r)) for r in cur.fetchall()]
        return {"adm_cd": adm_cd, "count": len(rows), "data": rows}
    except Exception as e:
        logger.error("[sangkwon-store] %s", e)
        return {"adm_cd": adm_cd, "count": 0, "data": []}


@router.get("/realestate/seoul-rtms")
async def get_seoul_rtms(
    adm_cd: str = Query(..., description="행정동코드"),
):
    """
    서울 실거래가 조회.
    Oracle LAW_ADM_MAP 매핑 테이블 미지원 → 빈 응답 반환.
    """
    logger.info("[seoul-rtms] adm_cd=%s (Oracle 매핑 미지원 — 빈 응답)", adm_cd)
    empty = {"건수": 0, "평균가": None, "최저가": None, "최고가": None, "목록": []}
    return {
        "has_data": False,
        "매매":        empty,
        "전세":        empty,
        "월세":        empty,
        "오피스텔전세": empty,
        "오피스텔월세": empty,
        "상업용매매":   empty,
    }


# ════════════════════════════════════════════════════════════════
# /map 엔드포인트 (개별 상가 목록 — STORE_SEOUL 미지원)
# ════════════════════════════════════════════════════════════════

@router.get("/map/stores-by-dong")
def stores_by_dong(adm_cd: str = Query(..., description="행정동코드")):
    """행정동 내 상가 목록 (STORE_SEOUL 테이블 미지원 → 빈 응답)"""
    return {"stores": []}


@router.get("/map/nearby")
def nearby_stores(
    lat:    float = Query(...),
    lng:    float = Query(...),
    radius: float = Query(500),
    limit:  int   = Query(500),
):
    """반경 내 상가 (STORE_SEOUL 테이블 미지원 → 빈 응답)"""
    return {"stores": [], "count": 0}


@router.get("/map/stores-by-building")
def stores_by_building(
    road_addr:  str = Query(...),
    store_nm:   str = Query(""),
    exclude_id: str = Query(""),
):
    """같은 건물 상가 (STORE_SEOUL 테이블 미지원 → 빈 응답)"""
    return {"stores": []}
