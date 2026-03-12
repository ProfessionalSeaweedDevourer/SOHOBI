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


# ── APScheduler: 분기 1회 매출 자동 갱신 ─────────────────────────
try:
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    from apscheduler.triggers.cron import CronTrigger

    _scheduler = AsyncIOScheduler()
    # 분기 1회: 매출 수집 (1/4/7/10월 1일 03:00)
    _scheduler.add_job(
        lambda: asyncio.create_task(skDAO.collect_all(force=True)),
        CronTrigger(month="1,4,7,10", day=1, hour=3, minute=0),
        id="sangkwon_quarterly",
        replace_existing=True,
    )
    # 15분마다: 유동인구 수집 → DB upsert
    from apscheduler.triggers.interval import IntervalTrigger

    _scheduler.add_job(
        lambda: asyncio.create_task(skDAO.collectPopulation(SEOUL_PLACES)),
        IntervalTrigger(minutes=15),
        id="flpop_15min",
        replace_existing=True,
    )
    _HAS_SCHEDULER = True
    logger.info("[Scheduler] 분기 매출 + 15분 유동인구 스케줄 등록")
except ImportError:
    _HAS_SCHEDULER = False
    logger.warning("[Scheduler] apscheduler 미설치 → pip install apscheduler")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── 시작 ──
    logger.info("[Startup] SangkwonDAO 초기화...")
    skDAO.load()  # SANGKWON_SALES → V_SANGKWON_LATEST → DataFrame 로드
    if _HAS_SCHEDULER:
        _scheduler.start()
    yield
    # ── 종료 ──
    if _HAS_SCHEDULER:
        _scheduler.shutdown(wait=False)


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


@app.get("/realestate/price-overlay")
async def getPriceOverlay(
    level: str = Query(..., description="sigungu | dong"),
    sigungu: Optional[str] = Query(
        None, description="시군구명 (level=dong 일 때 필수)"
    ),
    months_back: int = Query(6, description="조회 개월 수"),
):
    return await dao.fetchPriceOverlay(level, sigungu, months_back)


# ── 2. 서울 실시간 유동인구 ─────────────────────────────────────────


@app.get("/realestate/places-list")
async def getPlacesList():
    return {
        "places": SEOUL_PLACES,
        "gu_groups": SEOUL_GU_GROUPS,
        "gu_list": sorted(SEOUL_GU_GROUPS.keys()),
    }


@app.get("/realestate/population")
async def getPopulation(
    place_code: str = Query(..., description="장소코드 (예: POI001)"),
):
    """15분 TTL 캐시 → 서울 실시간 도시데이터 API"""
    data = await skDAO.getPopulation(place_code)
    place = SEOUL_PLACES.get(place_code, {})
    return {**place, **data}


@app.get("/realestate/population-by-gu")
async def getPopulationByGu(
    gu: str = Query(..., description="구명 (예: 강남구)"),
):
    """구 내 POI 유동인구 (캐시 활용)"""
    results = await skDAO.getPopulationByGu(gu, SEOUL_PLACES)
    return {"gu": gu, "count": len(results), "data": results}


@app.get("/realestate/nearby-population")
async def getNearbyPopulation(
    lat: float = Query(...),
    lng: float = Query(...),
    radius_km: float = Query(1.0),
):
    """반경 내 POI 유동인구 (캐시 활용)"""
    nearby = dao.getNearbyPlaces(lat, lng, radius_km)
    codes = [p["code"] for p in nearby[:5]]
    pops = await skDAO.getPopulationBulk(codes)
    return {
        "count": len(codes),
        "data": [{**nearby[i], **pops[i]} for i in range(len(codes))],
    }


# ── 3. 한국관광공사 관광정보 ────────────────────────────────────────


@app.get("/realestate/tour-nearby")
async def getTourNearby(
    mapX: float = Query(..., description="경도 (예: 126.9780)"),
    mapY: float = Query(..., description="위도 (예: 37.5665)"),
    radius: int = Query(1000, description="반경(m)"),
    contentTypeId: Optional[str] = Query(None, description="관광타입 ID"),
):
    return await dao.fetchTourNearby(mapX, mapY, radius, contentTypeId)


@app.get("/realestate/tour-db")
async def getTourFromDB(
    mapX: float = Query(..., description="경도"),
    mapY: float = Query(..., description="위도"),
    radius: int = Query(1000, description="반경(m)"),
    contentTypeId: Optional[str] = Query(None, description="관광타입"),
    limit: int = Query(50, description="최대 건수"),
):
    return await dao.fetchTourFromDB(mapX, mapY, radius, contentTypeId, limit)


@app.get("/realestate/tour-photos")
async def getTourPhotos(
    keyword: str = Query(..., description="검색 키워드 (관광지명)"),
    numOfRows: int = Query(5, description="사진 수"),
):
    return await dao.fetchTourPhotos(keyword, numOfRows)


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
