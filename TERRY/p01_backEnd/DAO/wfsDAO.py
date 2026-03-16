# 위치: p01_backEnd/DAO/wfsDAO.py
import logging
import httpx

logger = logging.getLogger(__name__)

VWORLD_KEY = "BE3AF33A-202E-3D5F-A8AD-63D9EE291ABF"


class WfsDAO:
    """VWorld WFS 프록시 (CORS 우회)"""

    def __init__(self, dong_mapping_dao):
        self._dm = dong_mapping_dao

    async def get_dong(self, sig_cd: str = "11") -> dict:
        """
        lt_c_ademd_info (읍면동 경계) 조회 + enrich
        - 1000개 제한 → 페이징으로 전체 수집
        - enrich: emd_cd → adm_cd, gu_nm 주입
        """
        BASE_URL = (
            f"https://api.vworld.kr/req/wfs"
            f"?SERVICE=WFS&VERSION=2.0.0&REQUEST=GetFeature"
            f"&TYPENAME=lt_c_ademd_info"
            f"&SRSNAME=EPSG:3857"
            f"&CQL_FILTER=sig_cd+LIKE+%27{sig_cd}%25%27"
            f"&outputFormat=application%2Fjson"
            f"&KEY={VWORLD_KEY}"
            f"&DOMAIN=localhost"
        )

        # VWorld WFS는 1000개 페이징 미지원 → count=1000 단일 요청
        url = BASE_URL + "&count=1000"
        logger.info(f"[WfsDAO] 요청: {url[:120]}...")

        async with httpx.AsyncClient(timeout=60, follow_redirects=True) as client:
            r = await client.get(url)

        if r.status_code != 200:
            raise RuntimeError(f"VWorld HTTP {r.status_code}: {r.text[:300]}")
        if r.text.strip().startswith("<"):
            raise RuntimeError(f"VWorld XML 응답 (인증오류): {r.text[:300]}")

        gj = r.json()
        logger.info(f"[WfsDAO] features: {len(gj.get('features', []))}개")
        return self._dm.enrich_geojson(gj)