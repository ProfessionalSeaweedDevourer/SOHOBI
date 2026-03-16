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

from DAO.sangkwonDAO   import SangkwonDAO
from DAO.dongMappingDAO import DongMappingDAO
from DAO.seoulRtmsDAO  import SeoulRtmsDAO
from DAO.landValueDAO  import LandValueDAO
from DAO.wfsDAO        import WfsDAO

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# ── DAO 인스턴스 ──────────────────────────────────────────────────────
skDAO   = SangkwonDAO()
dmDAO   = DongMappingDAO()
rtmsDAO = SeoulRtmsDAO()
lvDAO   = LandValueDAO()
wfsDAO  = WfsDAO(dmDAO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    skDAO.load()   # V_SANGKWON_LATEST → DataFrame 캐시
    dmDAO.load()   # V_WFS_DONG_MAP    → emd_cd dict 캐시
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
# 1. 서울시 부동산 실거래가 (서울 열린데이터)
# ════════════════════════════════════════════════════════════════

@app.get("/realestate/seoul-rtms")
async def getSeoulRtms(
    emd_cd:     str            = Query(..., description="WFS emd_cd 8자리 (예: 11110134)"),
    years_back: int            = Query(3,   description="최근 N년"),
    rtms_type:  Optional[str]  = Query(None, description="1=매매 2=전세 3=월세 None=전체"),
):
    """emd_cd(8자리) 기준 실거래 조회 - 코드 직접 매칭"""
    return await rtmsDAO.fetch_by_emd_cd(emd_cd, years_back, rtms_type)


@app.get("/realestate/seoul-rtms-adm")
async def getSeoulRtmsAdm(
    adm_cd:     str = Query(..., description="행정동코드 8자리"),
    gu_nm:      str = Query(..., description="자치구명"),
    years_back: int = Query(3),
):
    """행정동 기준 실거래 조회 (소속 법정동 합산)"""
    law_list = rtmsDAO.get_law_cds_by_adm_cd(adm_cd)
    if not law_list:
        return {"has_data": False, "message": f"행정동코드 {adm_cd} 매핑 없음"}

    results = await asyncio.gather(*[
        rtmsDAO.fetch_by_dong(r["gu_nm"], r["law_nm"], years_back)
        for r in law_list
    ])

    all_매매, all_전세, all_월세 = [], [], []
    for res in results:
        all_매매.extend(res.get("매매", {}).get("목록", []))
        all_전세.extend(res.get("전세", {}).get("목록", []))
        all_월세.extend(res.get("월세", {}).get("목록", []))

    return {
        "has_data":  bool(all_매매 or all_전세 or all_월세),
        "adm_cd":    adm_cd,
        "law_count": len(law_list),
        "매매":  rtmsDAO._stats(all_매매, "거래금액만원", "거래금액"),
        "전세":  rtmsDAO._stats(all_전세, "보증금만원",   "보증금"),
        "월세":  {"건수": len(all_월세), "목록": sorted(all_월세, key=lambda x: x.get("계약일",""), reverse=True)[:10]},
    }


# ════════════════════════════════════════════════════════════════
# 2. 서울 골목상권 매출
# ════════════════════════════════════════════════════════════════

@app.get("/realestate/sangkwon")
async def getSangkwon(
    adm_cd: str = Query("",  description="행정동코드 8자리 (우선)"),
    dong:   str = Query("",  description="행정동명 (adm_cd 없을 때)"),
    gu:     str = Query("",  description="자치구명 (중복동명 구분용)"),
):
    # adm_cd 있으면 코드 기반 조회 (이름 불일치 문제 없음)
    if adm_cd:
        logger.info(f"[sangkwon] 코드 조회: adm_cd='{adm_cd}'")
        row = skDAO.getSalesByCode(adm_cd)
    else:
        logger.info(f"[sangkwon] 이름 조회: dong='{dong}' gu='{gu}' / DF loaded={skDAO._loaded} rows={len(skDAO._df) if skDAO._df is not None else 0}")
        row = skDAO.getSalesByDong(dong, gu)
        if not row and skDAO._df is not None and not skDAO._df.empty:
            sample = skDAO._df["행정동_코드_명"].dropna().unique()[:10].tolist()
            logger.info(f"[sangkwon] 매칭실패 - DF 행정동명 샘플: {sample}")
    if not row:
        return {"data": None, "message": "데이터 없음"}
    return {"data": _format_sangkwon_row(row)}


@app.get("/realestate/sangkwon-gu")
async def getSangkwonByGu(
    gu: str = Query(..., description="자치구명 (예: 마포구)"),
):
    """구 내 전체 행정동 매출 (코로플레스용)"""
    rows = skDAO.getSalesByGu(gu)
    return {
        "gu":    gu,
        "count": len(rows),
        "data":  [_format_sangkwon_row(r) for r in rows],
    }


@app.get("/realestate/sangkwon-induty")
async def getSangkwonByInduty(
    code:   str = Query(..., description="행정동코드 (예: 11440520)"),
    induty: str = Query("",  description="업종코드 (비우면 전체)"),
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
# 3. 개별공시지가
# ════════════════════════════════════════════════════════════════

@app.get("/realestate/land-value")
async def getLandValue(
    pnu:   str = Query(..., description="필지고유번호 19자리"),
    years: int = Query(5,   description="조회 연수"),
):
    return await lvDAO.fetch(pnu, years)


# ════════════════════════════════════════════════════════════════
# 4. VWorld WFS 프록시 (CORS 우회)
# ════════════════════════════════════════════════════════════════

@app.get("/realestate/wfs-dong")
async def getWfsDong(
    sig_cd: str = Query("11", description="시도코드 (서울=11)"),
):
    try:
        gj = await wfsDAO.get_dong(sig_cd)
        import json
        return Response(
            content=json.dumps(gj, ensure_ascii=False).encode("utf-8"),
            media_type="application/json",
            headers={"Cache-Control": "no-cache"},
        )
    except Exception as e:
        logger.error(f"[wfs-dong] {e}")
        return JSONResponse(status_code=502, content={"error": str(e)})


# ════════════════════════════════════════════════════════════════
# 공통 포맷 헬퍼
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