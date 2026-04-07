# 위치: SOHOBI/backend/DAO/landValueDAO.py
# PostgreSQL 불필요 - VWorld 외부 API 직접 호출 (DB 무관)
# Oracle 버전과 동일

import os
import logging
import httpx
from datetime import datetime

logger = logging.getLogger(__name__)


class LandValueDAO:
    """VWorld 개별공시지가 조회 (DB 불필요)"""

    def __init__(self):
        self._key = os.getenv("VWORLD_API_KEY", "BE3AF33A-202E-3D5F-A8AD-63D9EE291ABF")

    async def fetch(self, pnu: str, years: int = 5) -> dict:
        """PNU 기반 최근 N년 공시지가 이력"""
        current_year = datetime.now().year
        results = []

        _logged_vworld_err = False  # VWorld 인증/네트워크 오류는 첫 번째만 로깅
        async with httpx.AsyncClient(timeout=15) as client:
            for i in range(years):
                year = str(current_year - i)
                try:
                    url = (
                        f"https://api.vworld.kr/req/data"
                        f"?service=data&version=2.0&request=GetFeature"
                        f"&format=json&errorFormat=json&data=LP_PA_CBND_BUBUN"
                        f"&key={self._key}&attrFilter=pnu:=:{pnu}"
                        f"&columns=pnu,pblntfPclnd,stdrYear&size=1&page=1"
                    )
                    res = await client.get(url)
                    raw = res.text.strip()
                    if not raw or raw.startswith("<"):
                        if not _logged_vworld_err:
                            logger.error(
                                f"[LandValueDAO] VWorld HTML/빈응답 (HTTP {res.status_code}) "
                                f"pnu={pnu} year={year} — IP 미등록 또는 네트워크 차단 의심"
                            )
                            _logged_vworld_err = True
                        continue
                    d = res.json()
                    if d.get("response", {}).get("status") != "OK":
                        if not _logged_vworld_err:
                            err = d.get("response", {}).get("error", {})
                            logger.error(
                                f"[LandValueDAO] VWorld ERROR code={err.get('code')} "
                                f"text={err.get('text')} pnu={pnu} year={year}"
                            )
                            _logged_vworld_err = True
                        continue
                    features = (
                        d.get("response", {})
                        .get("result", {})
                        .get("featureCollection", {})
                        .get("features", [])
                    )
                    for feat in (features or []):
                        props = feat.get("properties", {})
                        price = props.get("pblntfPclnd")
                        stdr = props.get("stdrYear", year)
                        if price and str(price).strip() not in ("", "0", "null"):
                            results.append({
                                "year":      str(stdr),
                                "price":     int(str(price).replace(",", "")),
                                "price_str": f"{int(str(price).replace(',','')):,}원/㎡",
                            })
                            break
                except Exception as e:
                    logger.error(f"[LandValueDAO] {year} error={e}")

        results.sort(key=lambda x: x["year"], reverse=True)
        return {"pnu": pnu, "count": len(results), "data": results, "unit": "원/㎡"}