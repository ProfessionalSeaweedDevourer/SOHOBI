# 위치: p01_backEnd/DAO/wfsDAO.py
#
# 역할:
#   VWorld WFS 프록시 (CORS 우회 + API 키 노출 방지)
#   lt_c_ademd_info (읍면동 경계) 서울 전체 1회 로드 → 메모리 캐시
#   서버 시작 시 preload → 이후 요청 즉시 반환

import logging
import httpx

logger = logging.getLogger(__name__)

VWORLD_KEY = "BE3AF33A-202E-3D5F-A8AD-63D9EE291ABF"


class WfsDAO:
    """VWorld WFS 프록시 — 서울 전체 폴리곤 1회 캐시"""

    def __init__(self, dong_mapping_dao):
        self._dm    = dong_mapping_dao
        self._cache = None  # 서울 전체 GeoJSON 캐시

    async def get_dong(self, sig_cd: str = "11") -> dict:
        """
        서울 행정동 경계 GeoJSON 반환
        - 최초 1회만 VWorld 호출 후 메모리 캐시
        - 이후 요청은 즉시 반환 (딜레이 없음)
        """
        if self._cache is not None:
            logger.info(f"[WfsDAO] 캐시 반환: {len(self._cache.get('features',[]))}개")
            return self._cache

        # ── 서울 전체 1회 로드 ──────────────────────────────────────
        url = (
            f"https://api.vworld.kr/req/wfs"
            f"?SERVICE=WFS&VERSION=2.0.0&REQUEST=GetFeature"
            f"&TYPENAME=lt_c_ademd_info"
            f"&SRSNAME=EPSG:3857"
            f"&CQL_FILTER=sig_cd+LIKE+%27{sig_cd}%25%27"
            f"&outputFormat=application%2Fjson"
            f"&count=1000"
            f"&KEY={VWORLD_KEY}"
            f"&DOMAIN=localhost"
        )
        logger.info(f"[WfsDAO] VWorld API 호출 (서울 전체)")

        async with httpx.AsyncClient(timeout=60, follow_redirects=True) as client:
            r = await client.get(url)

        if r.status_code != 200:
            raise RuntimeError(f"VWorld HTTP {r.status_code}: {r.text[:300]}")
        if r.text.strip().startswith("<"):
            raise RuntimeError(f"VWorld XML 오류: {r.text[:300]}")

        gj = r.json()
        logger.info(f"[WfsDAO] features: {len(gj.get('features', []))}개")

        gj = self._dm.enrich_geojson(gj)
        self._cache = gj
        return gj