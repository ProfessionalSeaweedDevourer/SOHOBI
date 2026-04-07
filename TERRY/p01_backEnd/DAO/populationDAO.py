# 위치: p01_backEnd/DAO/populationDAO.py
# 서울 실시간 도시데이터 인구 혼잡도 조회 DAO

import os, time, asyncio, logging
from typing import Optional
import xml.etree.ElementTree as ET
import httpx

logger = logging.getLogger(__name__)

SEOUL_POP_KEY = os.getenv("SEOUL_POP_API_KEY", "537a7a50717773743131306a49616d76")
BASE_URL = f"http://openapi.seoul.go.kr:8088/{SEOUL_POP_KEY}/xml/citydata_ppltn/1/1"
CACHE_TTL = 300  # 5분 캐시

# ── 서울 주요 장소 (장소명 + 좌표) ─────────────────────────────
PLACES = [
    # 종로/중구
    {"name": "광화문·덕수궁", "code": "POI009", "lat": 37.5706, "lng": 126.9769},
    {"name": "경복궁·서촌마을", "code": "POI010", "lat": 37.5796, "lng": 126.9770},
    {"name": "북촌한옥마을", "code": "POI011", "lat": 37.5826, "lng": 126.9831},
    {"name": "창덕궁·창경궁", "code": "POI012", "lat": 37.5792, "lng": 126.9910},
    {"name": "인사동·익선동", "code": "POI013", "lat": 37.5741, "lng": 126.9872},
    {"name": "혜화·대학로", "code": "POI014", "lat": 37.5823, "lng": 127.0017},
    {"name": "동대문", "code": "POI008", "lat": 37.5710, "lng": 127.0089},
    {"name": "명동", "code": "POI005", "lat": 37.5636, "lng": 126.9822},
    {"name": "남대문시장", "code": "POI006", "lat": 37.5581, "lng": 126.9764},
    {"name": "서울역", "code": "POI007", "lat": 37.5546, "lng": 126.9707},
    # 용산/마포/서대문
    {"name": "이태원·한남", "code": "POI001", "lat": 37.5345, "lng": 126.9940},
    {"name": "홍대입구역", "code": "POI002", "lat": 37.5573, "lng": 126.9245},
    {"name": "합정역·망원동", "code": "POI003", "lat": 37.5499, "lng": 126.9138},
    {"name": "신촌·이대", "code": "POI004", "lat": 37.5560, "lng": 126.9369},
    {"name": "연남동", "code": "POI116", "lat": 37.5611, "lng": 126.9226},
    {"name": "공덕역", "code": "POI117", "lat": 37.5441, "lng": 126.9515},
    # 강남/서초
    {"name": "강남역", "code": "POI015", "lat": 37.4979, "lng": 127.0276},
    {"name": "신사역·압구정", "code": "POI016", "lat": 37.5172, "lng": 127.0209},
    {"name": "역삼·선릉", "code": "POI017", "lat": 37.5000, "lng": 127.0361},
    {"name": "삼성역·코엑스", "code": "POI018", "lat": 37.5127, "lng": 127.0593},
    {"name": "양재역", "code": "POI118", "lat": 37.4845, "lng": 127.0343},
    {"name": "서초역", "code": "POI119", "lat": 37.4916, "lng": 127.0118},
    # 송파/강동
    {"name": "잠실·송파", "code": "POI019", "lat": 37.5133, "lng": 127.1028},
    {"name": "잠실한강공원", "code": "POI120", "lat": 37.5137, "lng": 127.0748},
    {"name": "천호역", "code": "POI121", "lat": 37.5384, "lng": 127.1237},
    # 성동/광진
    {"name": "건대입구역", "code": "POI020", "lat": 37.5401, "lng": 127.0694},
    {"name": "왕십리역", "code": "POI025", "lat": 37.5614, "lng": 127.0371},
    {"name": "성수동", "code": "POI122", "lat": 37.5447, "lng": 127.0557},
    # 여의도/영등포
    {"name": "여의도", "code": "POI021", "lat": 37.5245, "lng": 126.9249},
    {"name": "영등포·타임스퀘어", "code": "POI022", "lat": 37.5160, "lng": 126.9071},
    {"name": "여의도한강공원", "code": "POI123", "lat": 37.5283, "lng": 126.9332},
    # 노원/강북/도봉
    {"name": "수유리·강북", "code": "POI023", "lat": 37.6385, "lng": 127.0254},
    {"name": "노원역", "code": "POI024", "lat": 37.6551, "lng": 127.0565},
    {"name": "창동역", "code": "POI124", "lat": 37.6527, "lng": 127.0473},
    # 한강공원
    {"name": "뚝섬한강공원", "code": "POI026", "lat": 37.5300, "lng": 127.0665},
    {"name": "반포한강공원", "code": "POI027", "lat": 37.5101, "lng": 126.9946},
    {"name": "이촌한강공원", "code": "POI028", "lat": 37.5196, "lng": 126.9701},
    {"name": "망원한강공원", "code": "POI029", "lat": 37.5547, "lng": 126.9033},
]

PLACE_MAP = {p["name"]: p for p in PLACES}


class PopulationDAO:
    """서울 실시간 도시데이터 인구 혼잡도 DAO"""

    def __init__(self):
        self._cache: dict = {}  # name → {data, ts}

    # ── 캐시 ────────────────────────────────────────────────────
    def _get_cache(self, name: str):
        c = self._cache.get(name)
        if c and time.time() - c["ts"] < CACHE_TTL:
            return c["data"]
        return None

    def _set_cache(self, name: str, data: dict):
        self._cache[name] = {"data": data, "ts": time.time()}

    def clear_cache(self):
        self._cache.clear()

    # ── 단일 장소 조회 ───────────────────────────────────────────
    async def fetch_place(
        self, client: httpx.AsyncClient, place_name: str
    ) -> Optional[dict]:
        cached = self._get_cache(place_name)
        if cached:
            return cached
        try:
            r = await client.get(f"{BASE_URL}/{place_name}", timeout=8)
            root = ET.fromstring(r.text)
            node = root.find(".//SeoulRtd.citydata_ppltn")
            if node is None:
                return None

            data = {
                "name": node.findtext("AREA_NM", ""),
                "code": node.findtext("AREA_CD", ""),
                "혼잡도": node.findtext("AREA_CONGEST_LVL", ""),
                "혼잡메시지": node.findtext("AREA_CONGEST_MSG", ""),
                "인구_최소": node.findtext("AREA_PPLTN_MIN", ""),
                "인구_최대": node.findtext("AREA_PPLTN_MAX", ""),
                "남성비율": node.findtext("MALE_PPLTN_RATE", ""),
                "여성비율": node.findtext("FEMALE_PPLTN_RATE", ""),
                "거주민비율": node.findtext("RESNT_PPLTN_RATE", ""),
                "비거주비율": node.findtext("NON_RESNT_PPLTN_RATE", ""),
                "기준시각": node.findtext("PPLTN_TIME", ""),
                "연령대": {
                    "0대": node.findtext("PPLTN_RATE_0", ""),
                    "10대": node.findtext("PPLTN_RATE_10", ""),
                    "20대": node.findtext("PPLTN_RATE_20", ""),
                    "30대": node.findtext("PPLTN_RATE_30", ""),
                    "40대": node.findtext("PPLTN_RATE_40", ""),
                    "50대": node.findtext("PPLTN_RATE_50", ""),
                    "60대": node.findtext("PPLTN_RATE_60", ""),
                    "70대+": node.findtext("PPLTN_RATE_70", ""),
                },
                "예측": [
                    {
                        "시각": fcst.findtext("FCST_TIME", ""),
                        "혼잡도": fcst.findtext("FCST_CONGEST_LVL", ""),
                        "최소": fcst.findtext("FCST_PPLTN_MIN", ""),
                        "최대": fcst.findtext("FCST_PPLTN_MAX", ""),
                    }
                    for fcst in node.findall(".//FCST_PPLTN/FCST_PPLTN")
                ],
            }
            self._set_cache(place_name, data)
            logger.info(f"[PopulationDAO] {place_name} → {data['혼잡도']}")
            return data
        except Exception as e:
            logger.error(f"[PopulationDAO] {place_name}: {e}")
            return None

    # ── 전체 장소 병렬 조회 ──────────────────────────────────────
    async def fetch_all(self) -> list:
        async with httpx.AsyncClient() as client:
            tasks = [self.fetch_place(client, p["name"]) for p in PLACES]
            results = await asyncio.gather(*tasks)

        data = []
        for place, result in zip(PLACES, results):
            if result:
                data.append({**place, **result})
            else:
                data.append({**place, "혼잡도": None})
        return data

    # ── 단일 장소 조회 (외부 호출용) ────────────────────────────
    async def fetch_one(self, name: str) -> Optional[dict]:
        async with httpx.AsyncClient() as client:
            result = await self.fetch_place(client, name)
        if not result:
            return None
        place = PLACE_MAP.get(name, {})
        return {**place, **result}

    # ── 장소 목록 ───────────────────────────────────────────────
    def get_places(self) -> list:
        return PLACES
