# 위치: p01_backEnd/realEstateController.py
# 실행: uvicorn realEstateController:app --host=0.0.0.0 --port=8682 --reload

import os, sys, asyncio, logging
from contextlib import asynccontextmanager
from typing import Optional

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(BASE_DIR, "DAO"))

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response

from DAO.sangkwonDAO    import SangkwonDAO
from DAO.dongMappingDAO import DongMappingDAO
from DAO.seoulRtmsDAO   import SeoulRtmsDAO
from DAO.landValueDAO   import LandValueDAO
from DAO.wfsDAO         import WfsDAO

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

skDAO   = SangkwonDAO()
dmDAO   = DongMappingDAO()
rtmsDAO = SeoulRtmsDAO()
lvDAO   = LandValueDAO()
wfsDAO  = WfsDAO(dmDAO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    skDAO.load()   # V_SANGKWON_LATEST → DataFrame
    dmDAO.load()   # V_LAW_TO_ADM     → emd_cd dict
    yield


app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://192.168.9.168:5173",
        "http://195.168.9.169:5173",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ════════════════════════════════════════════════════════════════
# 1. 실거래 - emd_cd(법정동코드 앞8자리) 기준
#    MapView: p.emd_cd 항상 전달
# ════════════════════════════════════════════════════════════════

@app.get("/realestate/seoul-rtms")
async def getSeoulRtms(
    emd_cd:     str           = Query(..., description="WFS emd_cd 8자리"),
    years_back: int           = Query(3),
    rtms_type:  Optional[str] = Query(None, description="1=매매 2=전세 3=월세"),
):
    """법정동(emd_cd) 기준 실거래 조회"""
    logger.info(f"[seoul-rtms] emd_cd={emd_cd}")
    return await rtmsDAO.fetch_by_emd_cd(emd_cd, years_back, rtms_type)


# ════════════════════════════════════════════════════════════════
# 2. 매출 - adm_cd(행정동코드) 기준
#    MapView: p.adm_cd 전달
# ════════════════════════════════════════════════════════════════

@app.get("/realestate/sangkwon")
async def getSangkwon(
    adm_cd: str = Query(..., description="행정동코드 8자리"),
):
    """행정동(adm_cd) 기준 매출 조회"""
    logger.info(f"[sangkwon] adm_cd={adm_cd}")
    row = skDAO.getSalesByCode(adm_cd)
    if not row:
        return {"data": None, "message": "데이터 없음"}
    return {"data": _format_sangkwon_row(row)}


@app.get("/realestate/sangkwon-gu")
async def getSangkwonByGu(
    gu: str = Query(..., description="자치구명"),
):
    rows = skDAO.getSalesByGu(gu)
    return {"gu": gu, "count": len(rows), "data": [_format_sangkwon_row(r) for r in rows]}


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


@app.get("/realestate/sangkwon-status")
async def getSangkwonStatus():
    return skDAO.getStatus()


# ════════════════════════════════════════════════════════════════
# 3. 공시지가
# ════════════════════════════════════════════════════════════════

@app.get("/realestate/land-value")
async def getLandValue(
    pnu:   str = Query(...),
    years: int = Query(5),
):
    return await lvDAO.fetch(pnu, years)


# ════════════════════════════════════════════════════════════════
# 4. WFS 프록시
# ════════════════════════════════════════════════════════════════

@app.get("/realestate/wfs-dong")
async def getWfsDong(
    sig_cd: str = Query("11"),
):
    try:
        import json
        gj = await wfsDAO.get_dong(sig_cd)
        return Response(
            content=json.dumps(gj, ensure_ascii=False).encode("utf-8"),
            media_type="application/json",
            headers={"Cache-Control": "no-cache"},
        )
    except Exception as e:
        logger.error(f"[wfs-dong] {e}")
        return JSONResponse(status_code=502, content={"error": str(e)})


# ════════════════════════════════════════════════════════════════
# 공통 포맷
# ════════════════════════════════════════════════════════════════

def _format_sangkwon_row(row: dict) -> dict:
    return {
        "dong":         row.get("행정동_코드_명", ""),
        "code":         row.get("행정동_코드", ""),
        "quarter":      row.get("기준_년분기_코드", ""),
        "sales":        row.get("tot_sales_amt"),
        "selng_co":     row.get("tot_selng_co"),
        "sales_male":   row.get("ml_sales_amt"),
        "sales_female": row.get("fml_sales_amt"),
        "sales_mdwk":   row.get("mdwk_sales_amt"),
        "sales_wkend":  row.get("wkend_sales_amt"),
        "age20":        row.get("age20_amt"),
        "age30":        row.get("age30_amt"),
        "age40":        row.get("age40_amt"),
        "age50":        row.get("age50_amt"),
    }