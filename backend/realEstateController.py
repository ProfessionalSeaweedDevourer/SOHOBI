# 위치: SOHOBI/backend/realEstateController.py
# PostgreSQL (Azure) 버전
# 실행: uvicorn realEstateController:app --host=0.0.0.0 --port=8682 --reload

import os, asyncio, logging
from contextlib import asynccontextmanager
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response

from DAO.sangkwonDAO import SangkwonDAO
from DAO.dongMappingDAO import DongMappingDAO
from DAO.molitRtmsDAO import MolitRtmsDAO
from DAO.seoulRtmsDAO import SeoulRtmsDAO
from DAO.landValueDAO import LandValueDAO
from DAO.sangkwonStoreDAO import SangkwonStoreDAO

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

skDAO    = SangkwonDAO()
dmDAO    = DongMappingDAO()
rtmsDAO  = SeoulRtmsDAO()
molitDAO = MolitRtmsDAO()
lvDAO    = LandValueDAO()
storeDAO = SangkwonStoreDAO()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("[startup] PostgreSQL 연결 확인...")
    try:
        dmDAO.load()  # law_adm_map → emd_cd 딕셔너리 캐시
        logger.info("[startup] DB 연결 정상")
    except Exception as e:
        logger.warning(f"[startup] DB 연결 확인 실패: {e}")
    yield
    logger.info("[shutdown] 서버 종료")


app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 운영 환경에서는 실제 도메인으로 제한
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── 공통 포맷 ────────────────────────────────────────────────────

def _format_sangkwon_row(row: dict) -> dict:
    if not row:
        return None
    return {
        "dong":         row.get("adm_nm", ""),
        "code":         row.get("adm_cd", ""),
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


# ── 부동산 실거래 ─────────────────────────────────────────────────

@app.get("/realestate/seoul-rtms")
async def getSeoulRtms(adm_cd: str = Query(...)):
    logger.info(f"[seoul-rtms] adm_cd={adm_cd}")
    try:
        seoul      = await rtmsDAO.fetch_by_emd_cd(adm_cd)
        officetel  = molitDAO.fetch_officetel_rent(adm_cd)
        commercial = molitDAO.fetch_commercial_trade(adm_cd)
        return {
            "has_data":    seoul.get("has_data") or officetel.get("has_data") or commercial.get("has_data"),
            "매매":        seoul.get("매매",   {"건수": 0}),
            "전세":        seoul.get("전세",   {"건수": 0}),
            "월세":        seoul.get("월세",   {"건수": 0}),
            "오피스텔전세": officetel.get("전세", {"건수": 0}),
            "오피스텔월세": officetel.get("월세", {"건수": 0}),
            "상업용매매":  commercial.get("매매", {"건수": 0}),
        }
    except Exception as e:
        logger.error(f"[seoul-rtms] {e}")
        return {"has_data": False, "error": str(e)}


# ── 상권 매출 ─────────────────────────────────────────────────────

@app.get("/realestate/sangkwon")
async def getSangkwon(
    adm_cd:  str = Query(""),
    dong:    str = Query(""),
    gu:      str = Query(""),
    quarter: str = Query(""),
):
    if adm_cd:
        logger.info(f"[sangkwon] adm_cd={adm_cd} quarter={quarter or '최신'}")
        row = (
            skDAO.getSalesByCodeAndQuarter(adm_cd, quarter)
            if quarter else skDAO.getSalesByCode(adm_cd)
        )
    else:
        logger.info(f"[sangkwon] dong={dong} gu={gu}")
        # dong/gu 검색 → adm_cd 찾기
        results = skDAO.searchDong(dong)
        row = skDAO.getSalesByCode(results[0]["adm_cd"]) if results else None
    if not row:
        return {"data": None, "avg": None, "message": "데이터 없음"}
    avg = skDAO.getSalesAvgByCode(adm_cd) if adm_cd else None
    return {
        "data": _format_sangkwon_row(row),
        "avg":  _format_sangkwon_row(avg) if avg else None,
    }


@app.get("/realestate/sangkwon-svc")
async def getSangkwonBySvc(
    adm_cd:  str = Query(...),
    quarter: str = Query(""),
):
    logger.info(f"[sangkwon-svc] adm_cd={adm_cd} quarter={quarter or '최신'}")
    rows = skDAO.getSalesBySvcCd(adm_cd, quarter)
    return {"adm_cd": adm_cd, "count": len(rows), "data": rows}


@app.get("/realestate/sangkwon-svc-by-cat")
async def getSangkwonSvcByCat(
    adm_cd:  str = Query(...),
    cat_cd:  str = Query(...),
    quarter: str = Query(""),
):
    logger.info(f"[sangkwon-svc-by-cat] adm_cd={adm_cd} cat_cd={cat_cd}")
    try:
        rows = skDAO.getSalesByCatCd(adm_cd, cat_cd, quarter)
        return {"adm_cd": adm_cd, "cat_cd": cat_cd, "count": len(rows), "data": rows}
    except Exception as e:
        logger.error(f"[sangkwon-svc-by-cat] {e}")
        return {"adm_cd": adm_cd, "cat_cd": cat_cd, "count": 0, "data": []}


@app.get("/realestate/sangkwon-store")
async def getSangkwonStore(
    adm_cd:  str = Query(...),
    quarter: str = Query(""),
    svc_cd:  str = Query(""),
):
    logger.info(f"[sangkwon-store] adm_cd={adm_cd} svc_cd={svc_cd or '전체'}")
    if svc_cd:
        rows = storeDAO.getStoreByInduty(adm_cd, svc_cd, quarter)
    else:
        rows = storeDAO.getStoreBySvcCd(adm_cd, quarter)
    return {"adm_cd": adm_cd, "count": len(rows), "data": rows}


@app.get("/realestate/sangkwon-induty")
async def getSangkwonByInduty(
    code:   str = Query(...),
    induty: str = Query(""),
):
    rows = skDAO.getSalesByInduty(code, induty)
    return {"code": code, "count": len(rows), "data": rows}


@app.get("/realestate/sangkwon-quarters")
async def getSangkwonQuarters():
    quarters = skDAO.getQuarters()
    return {"quarters": quarters, "latest": quarters[-1] if quarters else None}


# ── 검색 ─────────────────────────────────────────────────────────

@app.get("/realestate/search-dong")
async def searchDong(q: str = Query(...)):
    logger.info(f"[search-dong] q={q}")
    try:
        rows = skDAO.searchDong(q)
        return {"count": len(rows), "data": rows}
    except Exception as e:
        logger.error(f"[search-dong] {e}")
        return {"count": 0, "data": []}


# ── 공시지가 ──────────────────────────────────────────────────────

@app.get("/realestate/land-value")
async def getLandValue(
    pnu:   str = Query(...),
    years: int = Query(5),
):
    return await lvDAO.fetch(pnu, years)