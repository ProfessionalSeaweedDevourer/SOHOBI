# 위치: p01_backEnd/realEstateController.py
# 실행: uvicorn realEstateController:app --host=0.0.0.0 --port=8682 --reload

import os, asyncio, logging
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response

from DAO.sangkwonDAO    import SangkwonDAO
from DAO.dongMappingDAO import DongMappingDAO
from DAO.seoulRtmsDAO   import SeoulRtmsDAO
from DAO.landValueDAO   import LandValueDAO
from DAO.wfsDAO         import WfsDAO

# ── 서버 로그 설정 ───────────────────────────────────────────────
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
    adm_cd:     str           = Query(..., description="행정동코드 8자리 (lt_c_cademd)"),
    years_back: int           = Query(3),
    rtms_type:  Optional[str] = Query(None, description="1=매매 2=전세 3=월세"),
):
    """행정동(adm_cd) → 법정동(emd_cd) 변환 후 실거래 조회"""
    logger.info(f"[seoul-rtms] adm_cd={adm_cd}")

    # adm_cd → LAW_ADM_MAP → emd_cd 목록
    emd_cds = rtmsDAO.get_emd_cd_by_adm_cd(adm_cd)
    if not emd_cds:
        logger.warning(f"[seoul-rtms] adm_cd={adm_cd} → emd_cd 매핑 없음")
        return {"has_data": False, "매매": {"건수":0,"목록":[]}, "전세": {"건수":0,"목록":[]}, "월세": {"건수":0,"목록":[]}}

    logger.info(f"[seoul-rtms] emd_cds={emd_cds}")
    results = await asyncio.gather(*[
        rtmsDAO.fetch_by_emd_cd(emd_cd, years_back, rtms_type)
        for emd_cd in emd_cds
    ])

    # 결과 합산
    all_매매, all_전세, all_월세 = [], [], []
    for res in results:
        all_매매.extend(res.get("매매", {}).get("목록", []))
        all_전세.extend(res.get("전세", {}).get("목록", []))
        all_월세.extend(res.get("월세", {}).get("목록", []))

    return {
        "has_data": bool(all_매매 or all_전세 or all_월세),
        "매매": rtmsDAO._stats(all_매매, "거래금액만원", "거래금액"),
        "전세": rtmsDAO._stats(all_전세, "보증금만원",   "보증금"),
        "월세": {"건수": len(all_월세), "목록": sorted(all_월세, key=lambda x: x.get("계약일",""), reverse=True)[:10]},
    }


# ════════════════════════════════════════════════════════════════
# 2. 매출 - adm_cd(행정동코드) 기준
#    MapView: p.adm_cd 전달
# ════════════════════════════════════════════════════════════════

@app.get("/realestate/sangkwon")
async def getSangkwon(
    adm_cd:  str = Query("", description="행정동코드 (enrich 주입값, 우선)"),
    dong:    str = Query("", description="행정동명 (fallback)"),
    gu:      str = Query("", description="구이름"),
    quarter: str = Query("", description="분기코드 (예: 20253) 비우면 최신"),
):
    """행정동코드(adm_cd) 우선, 없으면 동이름으로 매출 조회 + 분기 선택 + 전체 평균"""
    if adm_cd:
        logger.info(f"[sangkwon] adm_cd={adm_cd} quarter={quarter or '최신'}")
        row = skDAO.getSalesByCodeAndQuarter(adm_cd, quarter) if quarter else skDAO.getSalesByCode(adm_cd)
    else:
        logger.info(f"[sangkwon] dong={dong} gu={gu}")
        row = skDAO.getSalesByDong(dong, gu)
    if not row:
        return {"data": None, "avg": None, "message": "데이터 없음"}
    avg = skDAO.getSalesAvgByCode(adm_cd) if adm_cd else None
    return {
        "data": _format_sangkwon_row(row),
        "avg":  _format_sangkwon_row(avg) if avg else None,
    }


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