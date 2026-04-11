"""
지도 상가·랜드마크·외부 API 라우터
origin: backend/mapController.py (WOO-clean2)

엔드포인트:
  GET  /map/nearby           — 반경 내 점포
  GET  /map/stores-by-dong   — 행정동 전체 점포
  GET  /map/stores-by-building — 같은 건물/상호 점포
  GET  /map/nearby-bbox      — bbox 내 점포
  GET  /map/categories       — 업종 대분류
  GET  /map/landmarks        — 랜드마크
  GET  /map/festivals        — 축제 (KTO 실시간)
  GET  /map/schools          — 학교
  GET  /map/sdot/sensors     — S-DoT 센서
  GET  /map/dong-density     — 행정동 밀도
  GET  /map/csv-list         — CSV 파일 목록
  GET  /map/load-csv         — CSV 적재
  GET  /map/load-all-csv     — 전체 CSV 적재
  GET  /map/status           — 캐시 상태
  POST /map/reload-cache     — 캐시 재로드
  GET  /map/cache-status     — 캐시 상태
  GET  /map/land-use         — 용도지역 (VWorld)
  GET  /map/dong-centroids   — 동 중심좌표 (카카오)
"""

import asyncio
import csv
import logging
import math as _math
import os

import httpx
from cachetools import TTLCache
from db.dao.landmarkDAO import LandmarkDAO
from db.dao.mapInfoDAO import MapInfoDAO
from fastapi import APIRouter

logger = logging.getLogger(__name__)
router = APIRouter()

VWORLD_KEY = os.getenv("VWORLD_API_KEY", "")
KAKAO_REST_KEY = os.getenv("KAKAO_REST_KEY", "")

# 동 중심좌표 캐시 — 좌표는 변하지 않으므로 24시간 TTL
_centroid_cache: TTLCache = TTLCache(maxsize=500, ttl=86400)

SIDO_BOUNDS = {"store_seoul": (33.0, 38.7, 124.5, 132.0)}
SIDO_TABLE_MAP = {k.replace("STORE_", ""): k for k in SIDO_BOUNDS}
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_DIR = os.path.join(BASE_DIR, "csv")

LAND_USE_COLORS = {
    "중심상업지역": {"bg": "#DBEAFE", "text": "#1D4ED8", "level": 3},
    "일반상업지역": {"bg": "#DBEAFE", "text": "#2563EB", "level": 3},
    "근린상업지역": {"bg": "#EFF6FF", "text": "#3B82F6", "level": 2},
    "유통상업지역": {"bg": "#EFF6FF", "text": "#3B82F6", "level": 2},
    "준주거지역": {"bg": "#F0F9FF", "text": "#0284C7", "level": 2},
    "제1종전용주거지역": {"bg": "#F5F5F5", "text": "#888", "level": 0},
    "제2종전용주거지역": {"bg": "#F5F5F5", "text": "#888", "level": 0},
    "제1종일반주거지역": {"bg": "#F5F5F5", "text": "#777", "level": 0},
    "제2종일반주거지역": {"bg": "#F5F5F5", "text": "#777", "level": 0},
    "제3종일반주거지역": {"bg": "#F5F5F5", "text": "#777", "level": 0},
    "전용공업지역": {"bg": "#FFF7ED", "text": "#C2410C", "level": 1},
    "일반공업지역": {"bg": "#FFF7ED", "text": "#EA580C", "level": 1},
    "준공업지역": {"bg": "#FFF7ED", "text": "#F97316", "level": 1},
    "보전녹지지역": {"bg": "#F0FDF4", "text": "#16A34A", "level": 0},
    "생산녹지지역": {"bg": "#F0FDF4", "text": "#16A34A", "level": 0},
    "자연녹지지역": {"bg": "#F0FDF4", "text": "#22C55E", "level": 1},
}

mDAO = MapInfoDAO()
lmDAO = LandmarkDAO()


def _clean(obj):
    """NaN/Inf/NULL 문자열 → None 변환"""
    if isinstance(obj, str) and obj.strip().upper() == "NULL":
        return None
    if isinstance(obj, float) and (_math.isnan(obj) or _math.isinf(obj)):
        return None
    if isinstance(obj, dict):
        return {k: _clean(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_clean(v) for v in obj]
    return obj


# ════════════════════════════════════════════════════════════════
# 1. 상권 조회
# ════════════════════════════════════════════════════════════════


@router.get("/map/nearby")
def getNearbyStores(
    lat: float,
    lng: float,
    radius: float = 500,
    limit: int = 500,
    category: str | None = None,
):
    try:
        result = (
            mDAO.getNearbyByCategory(lat, lng, category, radius, limit)
            if category
            else mDAO.getNearbyStores(lat, lng, radius, limit)
        )
        return {"count": len(result), "stores": _clean(result)}
    except Exception as e:
        return {"error": str(e), "count": 0, "stores": []}


@router.get("/map/stores-by-dong")
def getStoresByDong(adm_cd: str):
    """행정동코드 기준 전체 스토어 조회 (폴리곤 클릭용)"""
    try:
        result = mDAO.getStoresByAdmCd(adm_cd)
        logger.info(f"[stores-by-dong] adm_cd={adm_cd} → {len(result)}건")
        return {"count": len(result), "stores": _clean(result)}
    except Exception as e:
        logger.error(f"[stores-by-dong] {e}")
        return {"error": str(e), "count": 0, "stores": []}


@router.get("/map/stores-by-building")
def getStoresByBuilding(road_addr: str, store_nm: str = "", exclude_id: str = ""):
    """같은 건물 상가 + 같은 상호명 다른 지점 조회"""
    try:
        result = mDAO.getStoresByBuilding(
            road_addr, store_nm or None, exclude_id or None
        )
        return {"count": len(result), "stores": _clean(result)}
    except Exception as e:
        logger.error(f"[stores-by-building] {e}")
        return {"error": str(e), "count": 0, "stores": []}


@router.get("/map/nearby-bbox")
def getNearbyInBbox(
    min_lng: float,
    min_lat: float,
    max_lng: float,
    max_lat: float,
    limit: int = 1000,
):
    """폴리곤 bbox(EPSG:4326) 내 소상공인 조회"""
    try:
        import math

        center_lat = (min_lat + max_lat) / 2
        center_lng = (min_lng + max_lng) / 2
        lat_r = (max_lat - min_lat) / 2 * 111320
        lng_r = (max_lng - min_lng) / 2 * 111320 * math.cos(math.radians(center_lat))
        radius = max(lat_r, lng_r)
        result = mDAO.getNearbyStores(center_lat, center_lng, radius, limit)
        filtered = [
            s
            for s in result
            if s.get("경도")
            and s.get("위도")
            and min_lng <= float(s["경도"]) <= max_lng
            and min_lat <= float(s["위도"]) <= max_lat
        ]
        logger.info(
            f"[nearby-bbox] 반경={radius:.0f}m 전체={len(result)} bbox필터={len(filtered)}"
        )
        return {"count": len(filtered), "stores": filtered}
    except Exception as e:
        logger.error(f"[nearby-bbox] {e}")
        return {"error": str(e), "count": 0, "stores": []}


@router.get("/map/categories")
def getCategories():
    try:
        return {"categories": mDAO.getCategories()}
    except Exception as e:
        return {"error": str(e), "categories": []}


@router.get("/map/landmarks")
def getLandmarks(
    lat: float = None,
    lng: float = None,
    adm_cd: str = None,
    radius: float = 1.0,
    types: str = "",
):
    """랜드마크 DB 조회 — 좌표/행정동코드/전체(서울)"""
    try:
        type_list = (
            [t.strip() for t in types.split(",") if t.strip()] if types else None
        )
        if lat and lng:
            result = lmDAO.get_nearby(lat, lng, radius)
        elif adm_cd:
            result = lmDAO.get_by_adm_cd(adm_cd, type_list)
        else:
            result = lmDAO.get_all(type_list, limit=500)
        if type_list and adm_cd:
            result = [r for r in result if str(r["content_type_id"]) in type_list]
        return {"count": len(result), "landmarks": result}
    except Exception as e:
        logger.error(f"[landmarks] {e}")
        return {"count": 0, "landmarks": [], "error": str(e)}


@router.get("/map/festivals")
async def getFestivals(
    adm_cd: str = None,
    lat: float = None,
    lng: float = None,
):
    """축제 실시간 KTO searchFestival2 조회 (서울 + 90일 이내)"""
    KTO_KEY = os.getenv("KTO_GW_INFO_KEY", "")
    sgg_cd = adm_cd[:5] if adm_cd else None
    try:
        from datetime import datetime

        today = datetime.now()
        date_from = today.strftime("%Y%m%d")
        params = {
            "serviceKey": KTO_KEY,
            "numOfRows": 100,
            "pageNo": 1,
            "MobileOS": "ETC",
            "MobileApp": "SOHOBI",
            "areaCode": "1",
            "eventStartDate": date_from,
            "_type": "xml",
        }
        if sgg_cd:
            params["sigunguCode"] = sgg_cd
        async with httpx.AsyncClient() as client:
            r = await client.get(
                "https://apis.data.go.kr/B551011/KorService2/searchFestival2",
                params=params,
                timeout=10,
            )
        import xml.etree.ElementTree as ET

        root = ET.fromstring(r.text)
        items = root.findall(".//item")
        result = [
            {
                "content_id": (item.findtext("contentid") or "").strip(),
                "title": (item.findtext("title") or "").strip(),
                "addr": (item.findtext("addr1") or "").strip(),
                "lng": float(item.findtext("mapx") or 0) or None,
                "lat": float(item.findtext("mapy") or 0) or None,
                "image": (item.findtext("firstimage") or "").strip() or None,
                "start_date": (item.findtext("eventstartdate") or "").strip(),
                "end_date": (item.findtext("eventenddate") or "").strip(),
            }
            for item in items
        ]
        return {"count": len(result), "festivals": result}
    except Exception as e:
        logger.error(f"[festivals] {e}")
        return {"count": 0, "festivals": [], "error": str(e)}


@router.get("/map/schools")
def getSchools(
    adm_cd: str = None,
    sgg_nm: str = "",
    school_type: str = "",
):
    """학교 정보 조회"""
    try:
        if adm_cd and not sgg_nm:
            gu = (
                mDAO.get_gu_nm_by_adm_cd(adm_cd)
                if hasattr(mDAO, "get_gu_nm_by_adm_cd")
                else ""
            )
            sgg_nm = gu or ""
        result = lmDAO.get_schools(school_type or None, limit=500)
        return {"count": len(result), "schools": result}
    except Exception as e:
        logger.error(f"[schools] {e}")
        return {"count": 0, "schools": [], "error": str(e)}


@router.get("/map/sdot/sensors")
def getSdotSensors():
    """S-DoT 유동인구 센서 위치 목록"""
    try:
        from db.dao.baseDAO import BaseDAO

        class _DAO(BaseDAO):
            pass

        dao = _DAO()
        rows = dao._query(
            "SELECT SEQ, SENSOR_CD, SERIAL_NO, ADDR, LAT, LNG FROM SDOT_SENSOR ORDER BY SEQ"
        )
        data = [
            {
                "seq": r.get("seq"),
                "sensor_cd": r.get("sensor_cd"),
                "serial_no": r.get("serial_no"),
                "addr": r.get("addr"),
                "lat": float(r["lat"]) if r.get("lat") else None,
                "lng": float(r["lng"]) if r.get("lng") else None,
            }
            for r in rows
            if r.get("lat") and r.get("lng")
        ]
        logger.info(f"[sdot/sensors] {len(data)}건")
        return {"count": len(data), "sensors": data}
    except Exception as e:
        logger.error(f"[sdot/sensors] {e}")
        return {"count": 0, "sensors": []}


@router.get("/map/dong-density")
def getDongDensity(sido: str, sigg: str, dong: str):
    try:
        return mDAO.getDongDensity(sido=sido, sigg=sigg, dong=dong)
    except Exception as e:
        return {"error": str(e), "total": 0, "level": 0, "cat_counts": {}}


# ════════════════════════════════════════════════════════════════
# 2. CSV 적재 (운영 도구)
# ════════════════════════════════════════════════════════════════


def _open_csv(filepath):
    for enc in ["utf-8-sig", "cp949", "euc-kr"]:
        try:
            f = open(filepath, encoding=enc)
            f.read(512)
            f.seek(0)
            return f, enc
        except Exception:
            try:
                f.close()
            except Exception:
                pass
    return open(filepath, encoding="cp949", errors="ignore"), "cp949(fallback)"


@router.get("/map/csv-list")
def getCsvList():
    if not os.path.exists(CSV_DIR):
        return {"error": f"csv 폴더 없음: {CSV_DIR}", "files": []}
    files = sorted(f for f in os.listdir(CSV_DIR) if f.endswith(".csv"))
    return {
        "count": len(files),
        "files": [
            {
                "filename": f,
                "target_table": SIDO_TABLE_MAP.get(
                    next((k for k in SIDO_TABLE_MAP if k in f), ""), "❌ 매핑 없음"
                ),
            }
            for f in files
        ],
    }


@router.get("/map/load-csv")
def loadCSV(filename: str):
    # 경로 탐색 방어: 정규화 후 CSV_DIR 내부인지 확인
    safe_dir = os.path.realpath(CSV_DIR)
    filepath = os.path.realpath(os.path.join(CSV_DIR, filename))
    if not filepath.startswith(safe_dir + os.sep):
        return {"error": "잘못된 파일명"}
    if not os.path.exists(filepath):
        return {"error": "파일을 찾을 수 없습니다"}
    table_name = next((v for k, v in SIDO_TABLE_MAP.items() if k in filename), None)
    if not table_name:
        return {"error": f"시도 매핑 실패: {filename}"}

    total, skip, batch = 0, 0, []
    BATCH = 2000
    try:
        f, enc = _open_csv(filepath)
        with f:
            reader = csv.reader(f)
            next(reader)
            for row in reader:
                if len(row) < 39:
                    skip += 1
                    continue
                try:
                    record = (
                        *[row[i].strip() for i in range(37)],
                        float(row[37]) if row[37].strip() else None,
                        float(row[38]) if row[38].strip() else None,
                    )
                    batch.append(record)
                    if len(batch) >= BATCH:
                        mDAO.insertBatch(batch, table_name)
                        total += len(batch)
                        batch = []
                except (ValueError, IndexError):
                    skip += 1
        if batch:
            mDAO.insertBatch(batch, table_name)
            total += len(batch)
        return {
            "message": "완료",
            "file": filename,
            "table": table_name,
            "encoding": enc,
            "inserted": total,
            "skipped": skip,
        }
    except Exception as e:
        return {"error": str(e), "file": filename}


@router.get("/map/load-all-csv")
def loadAllCSV():
    if not os.path.exists(CSV_DIR):
        return {"error": f"csv 폴더 없음: {CSV_DIR}"}
    files = sorted(f for f in os.listdir(CSV_DIR) if f.endswith(".csv"))
    results = [loadCSV(f) for f in files]
    return {
        "message": f"전체 완료: {sum(r.get('inserted', 0) for r in results)}건",
        "files_processed": len(files),
        "results": results,
    }


# ════════════════════════════════════════════════════════════════
# 3. 캐시 관리
# ════════════════════════════════════════════════════════════════


@router.get("/map/status")
def getStatus():
    try:
        return mDAO.getStatus()
    except Exception as e:
        return {"error": str(e)}


@router.post("/map/reload-cache")
async def reloadCache(table: str | None = None):
    return mDAO.reloadCache(table)


@router.get("/map/cache-status")
async def cacheStatus():
    return mDAO.getStatus()


# ════════════════════════════════════════════════════════════════
# 4. 외부 API 프록시
# ════════════════════════════════════════════════════════════════


@router.get("/map/pnu-by-coord")
async def getPnuByCoord(lng: float, lat: float):
    """좌표 → PNU 조회 (VWorld LP_PA_CBND_BUBUN 지적도 필지 경계)"""
    url = (
        "https://api.vworld.kr/req/data"
        "?service=data&request=GetFeature&data=LP_PA_CBND_BUBUN"
        f"&key={VWORLD_KEY}&format=json&size=1"
        f"&geomFilter=point({lng} {lat})&geometry=false&attribute=true"
        "&columns=pnu,pblntfPclnd,stdrYear"
    )
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            res = await client.get(url)
        features = (
            res.json()
            .get("response", {})
            .get("result", {})
            .get("featureCollection", {})
            .get("features", [])
        )
        if not features:
            return {"pnu": ""}
        props = features[0].get("properties", {})
        return {"pnu": props.get("pnu", "")}
    except Exception as e:
        return {"pnu": "", "error": str(e)}


@router.get("/map/land-use")
async def getLandUse(pnu: str):
    """PNU로 용도지역 조회 (VWorld LURIS)"""
    url = (
        "https://api.vworld.kr/req/data"
        "?service=data&request=GetFeature&data=LT_C_UQ111"
        f"&attrFilter=pnu:=:{pnu}"
        "&columns=pnu,jibun,prpos_area_dstrc_nm,prpos_area_dstrc_cd,prpos_zone_nm,prpos_regn_nm"
        f"&key={VWORLD_KEY}&format=json&size=1"
    )
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            res = await client.get(url)
        features = (
            res.json()
            .get("response", {})
            .get("result", {})
            .get("featureCollection", {})
            .get("features", [])
        )
        if not features:
            return {
                "용도지역명": "정보 없음",
                "level": 0,
                "color_bg": "#f5f5f5",
                "color_text": "#aaa",
            }
        props = features[0].get("properties", {})
        name = props.get("prpos_area_dstrc_nm", "") or "정보 없음"
        style = LAND_USE_COLORS.get(name, {"bg": "#f5f5f5", "text": "#666", "level": 1})
        return {
            "용도지역명": name,
            "용도지역코드": props.get("prpos_area_dstrc_cd", ""),
            "용도지구명": props.get("prpos_zone_nm", "") or None,
            "용도구역명": props.get("prpos_regn_nm", "") or None,
            "level": style["level"],
            "color_bg": style["bg"],
            "color_text": style["text"],
        }
    except Exception as e:
        return {
            "error": str(e),
            "용도지역명": "조회 실패",
            "level": 0,
            "color_bg": "#f5f5f5",
            "color_text": "#aaa",
        }


@router.get("/map/dong-centroids")
async def getDongCentroids(gu: str, dongs: str):
    """동 중심좌표 (카카오 주소/키워드 검색) — asyncio.gather 병렬 호출"""
    dong_list = [d.strip() for d in dongs.split(",") if d.strip()]

    async def _fetch_one(client: httpx.AsyncClient, dong: str):
        query = f"서울 {gu} {dong}"
        try:
            r = await client.get(
                "https://dapi.kakao.com/v2/local/search/address.json",
                params={"query": query, "size": 1},
                headers={"Authorization": f"KakaoAK {KAKAO_REST_KEY}"},
            )
            docs = r.json().get("documents", [])
            if not docs:
                r2 = await client.get(
                    "https://dapi.kakao.com/v2/local/search/keyword.json",
                    params={"query": query, "size": 1},
                    headers={"Authorization": f"KakaoAK {KAKAO_REST_KEY}"},
                )
                docs = r2.json().get("documents", [])
            if docs:
                return {
                    "dong": dong,
                    "lng": float(docs[0]["x"]),
                    "lat": float(docs[0]["y"]),
                }
        except Exception as e:
            logger.warning(f"[dong-centroids] {dong} 실패: {e}")
        return None

    # 캐시 히트/미스 분리
    cached_results = []
    to_fetch = []
    for dong in dong_list:
        hit = _centroid_cache.get((gu, dong))
        if hit is not None:
            cached_results.append(hit)
        else:
            to_fetch.append(dong)

    # 미캐시 동만 Kakao API 병렬 호출
    fetched = []
    if to_fetch:
        async with httpx.AsyncClient(timeout=10) as client:
            raw = await asyncio.gather(*[_fetch_one(client, d) for d in to_fetch])
        for r in raw:
            if r is not None:
                _centroid_cache[(gu, r["dong"])] = r
                fetched.append(r)

    results = cached_results + fetched
    return {"gu": gu, "count": len(results), "data": results}
