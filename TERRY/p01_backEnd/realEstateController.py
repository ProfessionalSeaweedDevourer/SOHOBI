# 위치: p01_backEnd/realEstateController.py
# 실행: python -m uvicorn realEstateController:app --host=0.0.0.0 --port=8682 --reload

import os, asyncio, logging
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response

from DAO.sangkwonDAO import SangkwonDAO
from DAO.dongMappingDAO import DongMappingDAO
from DAO.molitRtmsDAO import MolitRtmsDAO
from DAO.seoulRtmsDAO import SeoulRtmsDAO
from DAO.landValueDAO import LandValueDAO
from DAO.wfsDAO import WfsDAO  # WFS 엔드포인트 하위호환용 유지
from DAO.sangkwonStoreDAO import SangkwonStoreDAO

# ── 서버 로그 설정 ───────────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

skDAO = SangkwonDAO()
dmDAO = DongMappingDAO()
rtmsDAO = SeoulRtmsDAO()
molitDAO = MolitRtmsDAO()
lvDAO = LandValueDAO()
wfsDAO = WfsDAO(dmDAO)  # WFS 엔드포인트 하위호환용
storeDAO = SangkwonStoreDAO()


@asynccontextmanager
async def lifespan(app: FastAPI):
    skDAO.load()  # SANGKWON_SALES → DataFrame 캐시
    dmDAO.load()  # LAW_ADM_MAP    → emd_cd dict 캐시
    # wfsDAO 프리로드 제거 (프론트에서 public/seoul_adm_dong.geojson 직접 로드)
    yield


app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://10.1.92.100:3000",
        "http://192.168.9.4:5173",
        "http://195.168.9.5:5173",
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
    adm_cd: str = Query(..., description="행정동코드"),
):
    """
    서울시 부동산 실거래가 통합 조회
    - 서울 열린데이터광장: 아파트/연립 매매·전세·월세
    - 국토부 오피스텔 전월세
    - 국토부 상업·업무용 매매
    """
    logger.info(f"[seoul-rtms] adm_cd={adm_cd}")
    try:
        seoul = await rtmsDAO.fetch_by_emd_cd(adm_cd)  # 내부에서 adm_cd→emd_cd 변환
        officetel = molitDAO.fetch_officetel_rent(adm_cd)
        commercial = molitDAO.fetch_commercial_trade(adm_cd)
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


@app.get("/realestate/sangkwon")
async def getSangkwon(
    adm_cd: str = Query("", description="행정동코드 (enrich 주입값, 우선)"),
    dong: str = Query("", description="행정동명 (fallback)"),
    gu: str = Query("", description="구이름"),
    quarter: str = Query("", description="분기코드 (예: 20253) 비우면 최신"),
):
    """행정동코드(adm_cd) 우선, 없으면 동이름으로 매출 조회 + 분기 선택 + 전체 평균"""
    if adm_cd:
        logger.info(f"[sangkwon] adm_cd={adm_cd} quarter={quarter or '최신'}")
        row = (
            skDAO.getSalesByCodeAndQuarter(adm_cd, quarter)
            if quarter
            else skDAO.getSalesByCode(adm_cd)
        )
    else:
        logger.info(f"[sangkwon] dong={dong} gu={gu}")
        row = skDAO.getSalesByDong(dong, gu)
    if not row:
        return {"data": None, "avg": None, "message": "데이터 없음"}
    avg = skDAO.getSalesAvgByCode(adm_cd) if adm_cd else None
    return {
        "data": _format_sangkwon_row(row),
        "avg": _format_sangkwon_row(avg) if avg else None,
    }


@app.get("/realestate/sangkwon-svc")
async def getSangkwonBySvc(
    adm_cd: str = Query(..., description="행정동코드"),
    quarter: str = Query("", description="분기코드 (비우면 최신)"),
):
    """SVC_CD(대분류) 기준 업종별 매출 합산"""
    logger.info(f"[sangkwon-svc] adm_cd={adm_cd} quarter={quarter or '최신'}")
    rows = skDAO.getSalesBySvcCd(adm_cd, quarter)
    return {"adm_cd": adm_cd, "count": len(rows), "data": rows}


@app.get("/realestate/search-dong")
async def searchDong(q: str = Query(..., description="동이름 검색어")):
    """행정동 이름 LIKE 검색 → adm_cd, adm_nm, gu_nm 반환"""
    logger.info(f"[search-dong] q={q}")
    try:
        rows = skDAO.searchDong(q)
        return {"count": len(rows), "data": rows}
    except Exception as e:
        logger.error(f"[search-dong] {e}")
        return {"count": 0, "data": []}


@app.get("/realestate/sangkwon-store")
async def getSangkwonStore(
    adm_cd: str = Query(..., description="행정동코드"),
    quarter: str = Query("", description="분기코드 (비우면 최신)"),
    svc_cd: str = Query("", description="업종 대분류 코드 (비우면 전체)"),
):
    """SVC_CD 기준 점포수/개폐업률 조회"""
    logger.info(
        f"[sangkwon-store] adm_cd={adm_cd} quarter={quarter or '최신'} svc_cd={svc_cd or '전체'}"
    )
    if svc_cd:
        rows = storeDAO.getStoreByInduty(adm_cd, svc_cd, quarter)
    else:
        rows = storeDAO.getStoreBySvcCd(adm_cd, quarter)
    return {"adm_cd": adm_cd, "count": len(rows), "data": rows}


@app.get("/realestate/sangkwon-gu")
async def getSangkwonByGu(
    gu: str = Query(..., description="자치구명"),
):
    rows = skDAO.getSalesByGu(gu)
    return {
        "gu": gu,
        "count": len(rows),
        "data": [_format_sangkwon_row(r) for r in rows],
    }


@app.get("/realestate/sangkwon-induty")
async def getSangkwonByInduty(
    code: str = Query(...),
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
    pnu: str = Query(...),
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
