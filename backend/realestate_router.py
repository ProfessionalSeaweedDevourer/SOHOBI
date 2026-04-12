"""
부동산·상권 데이터 API 라우터
origin: backend/realEstateController.py (WOO-clean2)

엔드포인트:
  GET /realestate/seoul-rtms         — 서울시 부동산 실거래가
  GET /realestate/sangkwon           — 행정동 전체 매출
  GET /realestate/sangkwon-svc       — 업종별 매출 (소분류)
  GET /realestate/sangkwon-svc-by-cat — 대분류 기준 소분류별 매출
  GET /realestate/sangkwon-store     — 업종별 점포수·개폐업률
  GET /realestate/sangkwon-induty    — 업종 대/소분류별 매출
  GET /realestate/sangkwon-quarters  — 이용 가능 분기 목록
  GET /realestate/search-dong        — 행정동명 검색
  GET /realestate/land-value         — 공시지가 (VWorld)
"""

import asyncio
import logging

from db.dao.dongMappingDAO import DongMappingDAO
from db.dao.landValueDAO import LandValueDAO
from db.dao.molitRtmsDAO import MolitRtmsDAO
from db.dao.sangkwonDAO import SangkwonDAO
from db.dao.sangkwonStoreDAO import SangkwonStoreDAO
from db.dao.seoulRtmsDAO import SeoulRtmsDAO
from fastapi import APIRouter, Query

logger = logging.getLogger(__name__)
router = APIRouter()

skDAO = SangkwonDAO()
dmDAO = DongMappingDAO()
rtmsDAO = SeoulRtmsDAO()
molitDAO = MolitRtmsDAO()
lvDAO = LandValueDAO()
storeDAO = SangkwonStoreDAO()


def _format_sangkwon_row(row: dict) -> dict:
    if not row:
        return None
    return {
        "dong": row.get("adm_nm", ""),
        "code": row.get("adm_cd", ""),
        "quarter": row.get("base_yr_qtr_cd", ""),
        "sales": row.get("tot_sales_amt"),
        "sales_male": row.get("ml_sales_amt"),
        "sales_female": row.get("fml_sales_amt"),
        "sales_mdwk": row.get("mdwk_sales_amt"),
        "sales_wkend": row.get("wkend_sales_amt"),
        "age20": row.get("age20_amt"),
        "age30": row.get("age30_amt"),
        "age40": row.get("age40_amt"),
        "age50": row.get("age50_amt"),
    }


# ── 부동산 실거래 ─────────────────────────────────────────────────


@router.get("/realestate/seoul-rtms")
async def getSeoulRtms(adm_cd: str = Query(...)):
    logger.info(f"[seoul-rtms] adm_cd={adm_cd}")
    try:
        seoul, officetel, commercial = await asyncio.gather(
            rtmsDAO.fetch_by_emd_cd(adm_cd),
            asyncio.to_thread(molitDAO.fetch_officetel_rent, adm_cd),
            asyncio.to_thread(molitDAO.fetch_commercial_trade, adm_cd),
        )
        return {
            "has_data": seoul.get("has_data")
            or officetel.get("has_data")
            or commercial.get("has_data"),
            "매매": seoul.get("매매", {"건수": 0}),
            "전세": seoul.get("전세", {"건수": 0}),
            "월세": seoul.get("월세", {"건수": 0}),
            "오피스텔전세": officetel.get("전세", {"건수": 0}),
            "오피스텔월세": officetel.get("월세", {"건수": 0}),
            "상업용매매": commercial.get("매매", {"건수": 0}),
        }
    except Exception as e:
        logger.error(f"[seoul-rtms] {e}")
        return {"has_data": False, "error": str(e)}


# ── 상권 매출 ─────────────────────────────────────────────────────


@router.get("/realestate/sangkwon")
def getSangkwon(
    adm_cd: str = Query(""),
    dong: str = Query(""),
    gu: str = Query(""),
    quarter: str = Query(""),
):
    if adm_cd:
        logger.info(f"[sangkwon] adm_cd={adm_cd} quarter={quarter or '최신'}")
        row = (
            skDAO.getSalesByCodeAndQuarter(adm_cd, quarter)
            if quarter
            else skDAO.getSalesByCode(adm_cd)
        )
    else:
        logger.info(f"[sangkwon] dong={dong} gu={gu}")
        results = skDAO.searchDong(dong)
        row = skDAO.getSalesByCode(results[0]["adm_cd"]) if results else None
    if not row:
        return {"data": None, "avg": None, "message": "데이터 없음"}
    avg = skDAO.getSalesAvgByCode(adm_cd) if adm_cd else None
    return {
        "data": _format_sangkwon_row(row),
        "avg": _format_sangkwon_row(avg) if avg else None,
    }


@router.get("/realestate/sangkwon-svc")
def getSangkwonBySvc(
    adm_cd: str = Query(...),
    quarter: str = Query(""),
):
    logger.info(f"[sangkwon-svc] adm_cd={adm_cd} quarter={quarter or '최신'}")
    rows = skDAO.getSalesBySvcCd(adm_cd, quarter)
    return {"adm_cd": adm_cd, "count": len(rows), "data": rows}


@router.get("/realestate/sangkwon-svc-by-cat")
def getSangkwonSvcByCat(
    adm_cd: str = Query(...),
    cat_cd: str = Query(...),
    quarter: str = Query(""),
):
    logger.info(f"[sangkwon-svc-by-cat] adm_cd={adm_cd} cat_cd={cat_cd}")
    try:
        rows = skDAO.getSalesByCatCd(adm_cd, cat_cd, quarter)
        return {"adm_cd": adm_cd, "cat_cd": cat_cd, "count": len(rows), "data": rows}
    except Exception as e:
        logger.error(f"[sangkwon-svc-by-cat] {e}")
        return {"adm_cd": adm_cd, "cat_cd": cat_cd, "count": 0, "data": []}


@router.get("/realestate/sangkwon-store")
def getSangkwonStore(
    adm_cd: str = Query(...),
    quarter: str = Query(""),
    svc_cd: str = Query(""),
):
    logger.info(f"[sangkwon-store] adm_cd={adm_cd} svc_cd={svc_cd or '전체'}")
    if svc_cd:
        rows = storeDAO.getStoreByInduty(adm_cd, svc_cd, quarter)
    else:
        rows = storeDAO.getStoreBySvcCd(adm_cd, quarter)
    return {"adm_cd": adm_cd, "count": len(rows), "data": rows}


@router.get("/realestate/sangkwon-induty")
def getSangkwonByInduty(
    code: str = Query(...),
    induty: str = Query(""),
):
    rows = skDAO.getSalesByInduty(code, induty)
    return {"code": code, "count": len(rows), "data": rows}


@router.get("/realestate/sangkwon-quarters")
def getSangkwonQuarters():
    quarters = skDAO.getQuarters()
    return {"quarters": quarters, "latest": quarters[-1] if quarters else None}


# ── 검색 ─────────────────────────────────────────────────────────


@router.get("/realestate/search-dong")
def searchDong(q: str = Query(...)):
    logger.info(f"[search-dong] q={q}")
    try:
        rows = skDAO.searchDong(q)
        return {"count": len(rows), "data": rows}
    except Exception as e:
        logger.error(f"[search-dong] {e}")
        return {"count": 0, "data": []}


# ── 공시지가 ──────────────────────────────────────────────────────


@router.get("/realestate/land-value")
async def getLandValue(
    pnu: str = Query(...),
    years: int = Query(5),
):
    return await lvDAO.fetch(pnu, years)
