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

        all_features = []
        page = 0
        page_size = 1000

        async with httpx.AsyncClient(timeout=60, follow_redirects=True) as client:
            while True:
                start = page * page_size + 1
                url   = BASE_URL + f"&startIndex={start}&count={page_size}"
                logger.info(f"[WfsDAO] 페이지 {page+1} (startIndex={start})")
                r = await client.get(url)

                if r.status_code != 200:
                    raise RuntimeError(f"VWorld HTTP {r.status_code}: {r.text[:300]}")
                if r.text.strip().startswith("<"):
                    raise RuntimeError(f"VWorld XML 응답 (인증오류): {r.text[:300]}")

                gj       = r.json()
                features = gj.get("features", [])
                all_features.extend(features)
                logger.info(f"[WfsDAO] 페이지 {page+1}: {len(features)}개 (누적 {len(all_features)}개)")

                if len(features) < page_size:
                    break
                page += 1

        gj["features"] = all_features
        return self._dm.enrich_geojson(gj)