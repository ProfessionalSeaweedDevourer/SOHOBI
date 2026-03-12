# 위치: p01_backEnd/mapController.py
# python -m uvicorn mapController:app --host=0.0.0.0 --port=8681 --reload

import csv
import os
import sys
import httpx
import asyncio
import logging

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(BASE_DIR, "DAO"))

from contextlib import asynccontextmanager
from typing import Optional
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from DAO.mapInfoDAO import MapInfoDAO, SIDO_BOUNDS, _get_df

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# ── 서버 시작 시 캐시 자동 로드 ─────────────────────────────────────
# 서울만 즉시 로드, 나머지는 백그라운드에서 순차 로드
PRELOAD_TABLES = [
    "소상공인_서울",  
    "소상공인_경기",
    "소상공인_인천",
    "소상공인_부산",
    "소상공인_대구",
]


async def _preload_caches():
    """서버 시작 후 백그라운드에서 순차 캐시 로드"""
    for table in PRELOAD_TABLES:
        try:
            await asyncio.get_event_loop().run_in_executor(None, _get_df, table)
            logger.info(f"[startup] 캐시 완료: {table}")
        except Exception as e:
            logger.warning(f"[startup] 캐시 실패 ({table}): {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 서울 즉시 로드 (첫 요청 전에 준비)
    logger.info("[startup] 소상공인_서울 캐시 로드 시작...")
    try:
        await asyncio.get_event_loop().run_in_executor(None, _get_df, "소상공인_서울")
        logger.info("[startup] 소상공인_서울 캐시 완료 ✓")
    except Exception as e:
        logger.warning(f"[startup] 서울 캐시 실패: {e}")
    # 나머지 시도는 백그라운드에서 로드 (서비스 지연 없음)
    asyncio.create_task(_preload_caches())
    yield  # 서버 실행
    logger.info("[shutdown] 서버 종료")


app = FastAPI(lifespan=lifespan)
mDAO = MapInfoDAO()

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

CSV_DIR = os.path.join(BASE_DIR, "csv")

# ── 시도명 → 테이블명 매핑 ──────────────────────────────────────
SIDO_TABLE_MAP = {
    "서울": "소상공인_서울",
    "경기": "소상공인_경기",
    "인천": "소상공인_인천",
    "부산": "소상공인_부산",
    "대구": "소상공인_대구",
    "광주": "소상공인_광주",
    "대전": "소상공인_대전",
    "울산": "소상공인_울산",
    "세종": "소상공인_세종",
    "강원": "소상공인_강원",
    "충북": "소상공인_충북",
    "충남": "소상공인_충남",
    "전북": "소상공인_전북",
    "전남": "소상공인_전남",
    "경북": "소상공인_경북",
    "경남": "소상공인_경남",
    "제주": "소상공인_제주",
}


def getTableName(filename: str):
    for key, table in SIDO_TABLE_MAP.items():
        if key in filename:
            return table
    return None


# ── 인코딩 자동 감지 ────────────────────────────────────────────
def open_csv(filepath):
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


# ── 1. 반경 내 상권 조회 ────────────────────────────────────────
@app.get("/map/nearby")
def getNearbyStores(
    lat: float,
    lng: float,
    radius: float = 500,
    limit: int = 500,
    category: Optional[str] = None,
):
    try:
        if category:
            result = mDAO.getNearbyByCategory(lat, lng, category, radius, limit)
        else:
            result = mDAO.getNearbyStores(lat, lng, radius, limit)
        return {"count": len(result), "stores": result}
    except Exception as e:
        return {"error": str(e), "count": 0, "stores": []}


# ── 2. 업종 대분류 목록 ─────────────────────────────────────────
@app.get("/map/categories")
def getCategories():
    try:
        return {"categories": mDAO.getCategories()}
    except Exception as e:
        return {"error": str(e), "categories": []}


# ── 3. CSV 파일 목록 + 대상 테이블 확인 ────────────────────────
@app.get("/map/csv-list")
def getCsvList():
    if not os.path.exists(CSV_DIR):
        return {"error": f"csv 폴더 없음: {CSV_DIR}", "files": []}
    files = sorted([f for f in os.listdir(CSV_DIR) if f.endswith(".csv")])
    return {
        "count": len(files),
        "files": [
            {"filename": f, "target_table": getTableName(f) or "❌ 매핑 없음"}
            for f in files
        ],
    }


# ── 4. 단일 CSV → 시도 테이블 자동 적재 ────────────────────────
@app.get("/map/load-csv")
def loadCSV(filename: str):
    filepath = os.path.join(CSV_DIR, filename)
    if not os.path.exists(filepath):
        return {"error": f"파일 없음: {filepath}"}

    table_name = getTableName(filename)
    if not table_name:
        return {"error": f"시도 매핑 실패 - 파일명에 시도명 포함 필요: {filename}"}

    total = 0
    skip = 0
    batch = []
    BATCH_SIZE = 2000

    try:
        f, enc = open_csv(filepath)
        print(f"\n[적재 시작] {filename} → {table_name} ({enc})")

        with f:
            reader = csv.reader(f)
            header = next(reader)
            print(f"  컬럼 수: {len(header)}개")

            for row in reader:
                if len(row) < 39:
                    skip += 1
                    continue
                try:
                    record = (
                        row[0].strip(),  # 상가업소번호
                        row[1].strip(),  # 상호명
                        row[2].strip(),  # 지점명
                        row[3].strip(),  # 상권업종대분류코드
                        row[4].strip(),  # 상권업종대분류명
                        row[5].strip(),  # 상권업종중분류코드
                        row[6].strip(),  # 상권업종중분류명
                        row[7].strip(),  # 상권업종소분류코드
                        row[8].strip(),  # 상권업종소분류명
                        row[9].strip(),  # 표준산업분류코드
                        row[10].strip(),  # 표준산업분류명
                        row[11].strip(),  # 시도코드
                        row[12].strip(),  # 시도명
                        row[13].strip(),  # 시군구코드
                        row[14].strip(),  # 시군구명
                        row[15].strip(),  # 행정동코드
                        row[16].strip(),  # 행정동명
                        row[17].strip(),  # 법정동코드
                        row[18].strip(),  # 법정동명
                        row[19].strip(),  # 지번코드
                        row[20].strip(),  # 대지구분코드
                        row[21].strip(),  # 대지구분명
                        row[22].strip(),  # 지번본번지
                        row[23].strip(),  # 지번부번지
                        row[24].strip(),  # 지번주소
                        row[25].strip(),  # 도로명코드
                        row[26].strip(),  # 도로명
                        row[27].strip(),  # 건물본번지
                        row[28].strip(),  # 건물부번지
                        row[29].strip(),  # 건물관리번호
                        row[30].strip(),  # 건물명
                        row[31].strip(),  # 도로명주소
                        row[32].strip(),  # 구우편번호
                        row[33].strip(),  # 신우편번호
                        row[34].strip(),  # 동정보
                        row[35].strip(),  # 층정보
                        row[36].strip(),  # 호정보
                        float(row[37]) if row[37].strip() else None,  # 경도
                        float(row[38]) if row[38].strip() else None,  # 위도
                    )
                    batch.append(record)

                    if len(batch) >= BATCH_SIZE:
                        mDAO.insertBatch(batch, table_name)
                        total += len(batch)
                        batch = []
                        print(f"  → {total}건 적재 중...")

                except (ValueError, IndexError):
                    skip += 1
                    continue

        if batch:
            mDAO.insertBatch(batch, table_name)
            total += len(batch)

        print(f"[완료] {table_name}: {total}건 적재 / {skip}건 스킵")
        return {
            "message": "적재 완료",
            "file": filename,
            "table": table_name,
            "encoding": enc,
            "inserted": total,
            "skipped": skip,
        }

    except Exception as e:
        return {"error": str(e), "file": filename}


# ── 5. 전체 CSV 일괄 적재 ───────────────────────────────────────
@app.get("/map/load-all-csv")
def loadAllCSV():
    if not os.path.exists(CSV_DIR):
        return {"error": f"csv 폴더 없음: {CSV_DIR}"}

    files = sorted([f for f in os.listdir(CSV_DIR) if f.endswith(".csv")])
    if not files:
        return {"error": "csv 폴더에 .csv 파일 없음"}

    results = []
    grand_total = 0
    for filename in files:
        result = loadCSV(filename)
        results.append(result)
        grand_total += result.get("inserted", 0)

    return {
        "message": f"전체 적재 완료: {grand_total}건",
        "files_processed": len(files),
        "grand_total": grand_total,
        "results": results,
    }


# ── 6. 테이블별 적재 현황 ────────────────────────────────────────
@app.get("/map/status")
def getStatus():
    try:
        return mDAO.getStatus()
    except Exception as e:
        return {"error": str(e)}


# ── 7. VWorld WFS 프록시 (CORS 우회) ────────────────────────────
# 브라우저에서 api.vworld.kr 직접 호출 시 CORS 차단 → 백엔드가 대신 요청
VWORLD_KEY = os.getenv("VWORLD_API_KEY", "BE3AF33A-202E-3D5F-A8AD-63D9EE291ABF")


@app.get("/map/wfs-dong")
async def getWfsDong(dong: str):
    """
    법정동명으로 VWorld WFS 경계 폴리곤 조회 (CORS 우회 프록시)
    → 프론트에서 http://localhost:8681/map/wfs-dong?dong=관훈동 으로 호출
    """
    url = (
        f"https://api.vworld.kr/req/wfs"
        f"?SERVICE=WFS&VERSION=2.0.0&REQUEST=GetFeature"
        f"&TYPENAME=lt_c_ademd_info&OUTPUTFORMAT=application/json"
        f"&CQL_FILTER=emd_kor_nm='{dong}'"
        f"&KEY={VWORLD_KEY}"
    )
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            res = await client.get(url)
        return res.json()
    except Exception as e:
        return {"error": str(e), "features": []}


@app.get("/map/wfs-gu")
async def getWfsGu(gu: str):
    """
    자치구명으로 해당 구 전체 행정동 경계 폴리곤 일괄 조회
    → 코로플레스 렌더링용 (구 내 모든 행정동 한 번에)
    VWorld lt_c_ademd: sig_kor_nm(시군구명) 필드로 필터
    """
    url = (
        f"https://api.vworld.kr/req/wfs"
        f"?SERVICE=WFS&VERSION=2.0.0&REQUEST=GetFeature"
        f"&TYPENAME=lt_c_ademd&OUTPUTFORMAT=application/json"
        f"&COUNT=100"
        f"&CQL_FILTER=sig_kor_nm='{gu}'"
        f"&KEY={VWORLD_KEY}"
    )
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            res = await client.get(url)
        data = res.json()
        # features 수 로그
        cnt = len(data.get("features", []))
        print(f"[wfs-gu] {gu} → {cnt}개 행정동 경계")
        return data
    except Exception as e:
        print(f"[wfs-gu] 오류: {e}")
        return {"error": str(e), "features": []}


# ── 8. 동(洞)별 소상공인 밀집도 ─────────────────────────────────
@app.get("/map/dong-density")
async def getDongDensity(
    sido: str,
    sigg: str,
    dong: str,
):
    """
    지적도 클릭 시 해당 동의 소상공인 밀집도 조회
    → 건수 + 업종별 분포 + 밀집도 등급(0~3)
    """
    try:
        result = mDAO.getDongDensity(sido=sido, sigg=sigg, dong=dong)
        return result
    except Exception as e:
        return {"error": str(e), "total": 0, "level": 0, "cat_counts": {}}


# ── 8-1. 행정동 중심좌표 일괄 조회 (카카오 키워드 검색 활용) ─────
KAKAO_REST_KEY = os.getenv("KAKAO_REST_KEY", "")


@app.get("/map/dong-centroids")
async def getDongCentroids(gu: str, dongs: str):
    """
    구명 + 쉼표구분 동명 목록 → 각 동 중심 경위도 반환
    예: /map/dong-centroids?gu=마포구&dongs=공덕동,합정동,망원동
    """
    dong_list = [d.strip() for d in dongs.split(",") if d.strip()]
    results = []
    async with httpx.AsyncClient(timeout=10) as client:
        for dong in dong_list:
            query = f"서울 {gu} {dong}"
            try:
                r = await client.get(
                    "https://dapi.kakao.com/v2/local/search/address.json",
                    params={"query": query, "size": 1},
                    headers={"Authorization": f"KakaoAK {KAKAO_REST_KEY}"},
                )
                docs = r.json().get("documents", [])
                if docs:
                    results.append(
                        {
                            "dong": dong,
                            "lng": float(docs[0]["x"]),
                            "lat": float(docs[0]["y"]),
                        }
                    )
                else:
                    # keyword 검색으로 fallback
                    r2 = await client.get(
                        "https://dapi.kakao.com/v2/local/search/keyword.json",
                        params={"query": query, "size": 1},
                        headers={"Authorization": f"KakaoAK {KAKAO_REST_KEY}"},
                    )
                    docs2 = r2.json().get("documents", [])
                    if docs2:
                        results.append(
                            {
                                "dong": dong,
                                "lng": float(docs2[0]["x"]),
                                "lat": float(docs2[0]["y"]),
                            }
                        )
            except Exception as e:
                logger.warning(f"[dong-centroids] {dong} 실패: {e}")
    return {"gu": gu, "count": len(results), "data": results}


# ── 9. 용도지역 조회 프록시 (VWorld LURIS API) ───────────────────
# 용도지역: 상업지역/주거지역/공업지역/녹지지역 등
LAND_USE_COLORS = {
    # 상업지역 계열 → 파란색
    "중심상업지역": {"bg": "#DBEAFE", "text": "#1D4ED8", "level": 3},
    "일반상업지역": {"bg": "#DBEAFE", "text": "#2563EB", "level": 3},
    "근린상업지역": {"bg": "#EFF6FF", "text": "#3B82F6", "level": 2},
    "유통상업지역": {"bg": "#EFF6FF", "text": "#3B82F6", "level": 2},
    # 준주거 → 연파랑
    "준주거지역": {"bg": "#F0F9FF", "text": "#0284C7", "level": 2},
    # 주거지역 계열 → 회색
    "제1종전용주거지역": {"bg": "#F5F5F5", "text": "#888", "level": 0},
    "제2종전용주거지역": {"bg": "#F5F5F5", "text": "#888", "level": 0},
    "제1종일반주거지역": {"bg": "#F5F5F5", "text": "#777", "level": 0},
    "제2종일반주거지역": {"bg": "#F5F5F5", "text": "#777", "level": 0},
    "제3종일반주거지역": {"bg": "#F5F5F5", "text": "#777", "level": 0},
    # 공업지역 → 주황
    "전용공업지역": {"bg": "#FFF7ED", "text": "#C2410C", "level": 1},
    "일반공업지역": {"bg": "#FFF7ED", "text": "#EA580C", "level": 1},
    "준공업지역": {"bg": "#FFF7ED", "text": "#F97316", "level": 1},
    # 녹지지역 → 초록
    "보전녹지지역": {"bg": "#F0FDF4", "text": "#16A34A", "level": 0},
    "생산녹지지역": {"bg": "#F0FDF4", "text": "#16A34A", "level": 0},
    "자연녹지지역": {"bg": "#F0FDF4", "text": "#22C55E", "level": 1},
}


@app.get("/map/land-use")
async def getLandUse(pnu: str):
    """
    PNU(필지고유번호)로 용도지역 조회
    VWorld LURIS 토지이용계획정보 API 프록시
    """
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
        data = res.json()
        features = (
            data.get("response", {})
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


# ── 캐시 관리 엔드포인트 ─────────────────────────────────────────────


@app.post("/map/reload-cache")
async def reloadCache(table: Optional[str] = None):
    """
    메모리 캐시 강제 갱신 (Oracle 재조회 → CSV 덮어쓰기)
    table 없으면 현재 로드된 테이블 전체 갱신
    예: POST /map/reload-cache?table=소상공인_서울
    """
    result = mDAO.reloadCache(table)
    return result


@app.get("/map/cache-status")
async def cacheStatus():
    """캐시 현황 조회 (어떤 테이블이 메모리에 올라와있는지)"""
    return mDAO.getStatus()
