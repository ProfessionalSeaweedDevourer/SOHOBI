# 위치: p01_backEnd/realEstateController.py
# FastAPI 라우터 - 비즈니스 로직은 DAO/realEstateDAO.py 에 위임
# python -m uvicorn realEstateController:app --host=0.0.0.0 --port=8682 --reload

import os
import sys
import asyncio
import logging
from contextlib import asynccontextmanager

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(BASE_DIR, "DAO"))

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional

from DAO.realEstateDAO import RealEstateDAO, SEOUL_PLACES, SEOUL_GU_GROUPS
from DAO.sangkwonDAO import SangkwonDAO

logger = logging.getLogger(__name__)
dao = RealEstateDAO()
skDAO = SangkwonDAO()


# ── APScheduler: 미구현(유동인구/collect_all) ─ 추후 활성화 ─────
_HAS_SCHEDULER = False  # TODO: sangkwonDAO.collect_all/collectPopulation 구현 후 활성화


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("[Startup] SangkwonDAO 로드...")
    skDAO.load()  # V_SANGKWON_LATEST → DataFrame 캐시
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


# ── 1. 실거래가 ─────────────────────────────────────────────────────


@app.get("/realestate/commercial")
async def getCommercialTrade(
    sigungu: str = Query(..., description="시군구명 (예: 강남구)"),
    yearmonth: str = Query(..., description="계약년월 (예: 202501)"),
):
    return await dao.fetchCommercialTrade(sigungu, yearmonth)


@app.get("/realestate/officetel")
async def getOfficetelRent(
    sigungu: str = Query(..., description="시군구명 (예: 강남구)"),
    yearmonth: str = Query(..., description="계약년월 (예: 202501)"),
):
    return await dao.fetchOfficetelRent(sigungu, yearmonth)


@app.get("/realestate/analysis")
async def getAnalysis(
    sigungu: str = Query(..., description="시군구명 (예: 강남구)"),
    dong: Optional[str] = Query(None, description="법정동명 (예: 북창동)"),
    lat: Optional[float] = Query(None),
    lng: Optional[float] = Query(None),
    jibun: Optional[str] = Query(None, description="지번 (예: 158-1)"),
):
    return await dao.fetchAnalysis(sigungu, dong, jibun)


# ── 2. 서울 실시간 유동인구 (TODO: sangkwonDAO 구현 후 활성화) ──────
# getPopulation / getPopulationByGu / getPopulationBulk 미구현
# places-list는 참조용으로 유지

@app.get("/realestate/places-list")
async def getPlacesList():
    return {
        "places": SEOUL_PLACES,
        "gu_groups": SEOUL_GU_GROUPS,
        "gu_list": sorted(SEOUL_GU_GROUPS.keys()),
    }


# ── 3. 한국관광공사 관광정보 (TODO: 프론트 구현 후 활성화) ──────────
# tour-nearby / tour-db / tour-photos 엔드포인트 보류


# ── 4. 서울 골목상권 분석 ────────────────────────────────────────────


@app.get("/realestate/sangkwon")
async def getSangkwon(
    dong: str = Query(..., description="행정동명 (예: 공덕동)"),
    gu: str = Query("", description="자치구명 (예: 마포구, 중복동명 구분용)"),
):
    """행정동 매출 조회 (V_SANGKWON_LATEST DataFrame)"""
    row = skDAO.getSalesByDong(dong, gu)
    if not row:
        return {"data": None, "message": "데이터 없음"}
    return {
        "data": {
            "dong": row.get("행정동_코드_명", dong),
            "code": row.get("행정동_코드", ""),
            "quarter": row.get("기준_년분기_코드", ""),
            "sales": row.get("tot_sales_amt"),
            "selng_co": row.get("tot_selng_co"),
            "sales_male": row.get("ml_sales_amt"),
            "sales_female": row.get("fml_sales_amt"),
            "sales_mdwk": row.get("mdwk_sales_amt"),
            "sales_wkend": row.get("wkend_sales_amt"),
            "age20": row.get("age20_amt"),
            "age30": row.get("age30_amt"),
            "age40": row.get("age40_amt"),
            "age50": row.get("age50_amt"),
            "source": "db",
        }
    }


@app.get("/realestate/sangkwon-induty")
async def getSangkwonByInduty(
    code: str = Query(..., description="행정동 코드 (예: 11440520)"),
    induty: str = Query("", description="업종 코드 (비우면 전체)"),
):
    """행정동 업종별 매출 조회"""
    rows = skDAO.getSalesByInduty(code, induty)
    return {"code": code, "count": len(rows), "data": rows}


# ── 5. 개별공시지가 ─────────────────────────────────────────────────


@app.get("/realestate/land-value")
async def getLandValue(
    pnu: str = Query(..., description="필지고유번호 19자리"),
    years: int = Query(5, description="조회 연수 (기본 5년)"),
):
    return await dao.fetchLandValue(pnu, years)


# ── 6. 상권 코로플레스용 - 구 내 전체 행정동 상권 데이터 (DB 캐시) ──


@app.get("/realestate/sangkwon-gu")
async def getSangkwonByGu(
    gu: str = Query(..., description="자치구명 (예: 마포구)"),
):
    """구 내 전체 행정동 매출 (코로플레스 히트맵용)"""
    rows = skDAO.getSalesByGu(gu)
    if not rows:
        return {"gu": gu, "count": 0, "data": [], "source": "empty"}
    data = [
        {
            "dong": r.get("행정동_코드_명", ""),
            "code": r.get("행정동_코드", ""),
            "quarter": r.get("기준_년분기_코드", ""),
            "sales": r.get("tot_sales_amt"),
            "selng_co": r.get("tot_selng_co"),
            "sales_male": r.get("ml_sales_amt"),
            "sales_female": r.get("fml_sales_amt"),
            "sales_mdwk": r.get("mdwk_sales_amt"),
            "sales_wkend": r.get("wkend_sales_amt"),
            "age20": r.get("age20_amt"),
            "age30": r.get("age30_amt"),
            "age40": r.get("age40_amt"),
            "age50": r.get("age50_amt"),
        }
        for r in rows
    ]
    return {"gu": gu, "count": len(data), "data": data, "source": "db"}


@app.get("/realestate/sangkwon-quarters")
async def getSangkwonQuarters():
    """DB에 있는 분기 목록 조회"""
    quarters = skDAO.getQuarters()
    return {"quarters": quarters, "latest": quarters[-1] if quarters else None}


@app.get("/realestate/sangkwon-status")
async def getSangkwonStatus():
    """캐시 상태 확인"""
    return skDAO.getStatus()


# ── 7. VWorld WFS 프록시 (CORS 우회) ────────────────────────────────
# VWorld WFS는 브라우저에서 직접 호출 시 CORS 차단 → 백엔드에서 중계

import httpx as _httpx
from fastapi import Response as _Response
from fastapi.responses import JSONResponse as _JSONResponse

VWORLD_KEY_LOCAL = "BE3AF33A-202E-3D5F-A8AD-63D9EE291ABF"  # realEstateDAO에서 가져온 키


@app.get("/realestate/wfs-dong")
async def getWfsDong(
    sig_cd: str = Query("11", description="시도코드 (서울=11, 기본값)"),
):
    """
    VWorld WFS lt_c_ademd_info (행정동 경계 폴리곤) 프록시
    - sig_cd LIKE '11%' → 서울 전체 행정동 폴리곤
    - GeoJSON(EPSG:3857) 반환
    """
    # VWorld WFS: URL에 KEY/DOMAIN을 쿼리스트링으로 포함해야 인증됨
    # CQL_FILTER는 URL 인코딩 없이 직접 전달
    url = (
        f"https://api.vworld.kr/req/wfs"
        f"?SERVICE=WFS&VERSION=2.0.0&REQUEST=GetFeature"
        f"&TYPENAME=lt_c_ademd_info"
        f"&SRSNAME=EPSG:3857"
        f"&CQL_FILTER=sig_cd+LIKE+%27{sig_cd}%25%27"
        f"&outputFormat=application%2Fjson"
        f"&KEY={VWORLD_KEY_LOCAL}"
        f"&DOMAIN=localhost"
    )
    logger.info(f"[WFS proxy] → {url[:120]}...")
    try:
        async with _httpx.AsyncClient(timeout=60, follow_redirects=True) as client:
            r = await client.get(url)
            logger.info(f"[WFS proxy] status={r.status_code}, ct={r.headers.get('content-type','')}, len={len(r.content)}")
            body_preview = r.text[:500]
            if r.status_code != 200:
                logger.error(f"[WFS proxy] VWorld error body: {body_preview}")
                return _JSONResponse(status_code=502,
                    content={"error": f"VWorld HTTP {r.status_code}", "body": body_preview})
            if r.text.strip().startswith("<"):
                logger.error(f"[WFS proxy] VWorld returned XML: {body_preview}")
                return _JSONResponse(status_code=502,
                    content={"error": "VWorld returned XML (인증오류 또는 파라미터 오류)", "body": body_preview})
            return _Response(
                content=r.content,
                media_type="application/json",
                headers={"Cache-Control": "public, max-age=86400"},
            )
    except Exception as e:
        logger.error(f"[WFS proxy] exception: {e}")
        return _JSONResponse(status_code=500, content={"error": str(e)})