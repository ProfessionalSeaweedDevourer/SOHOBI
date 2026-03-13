# 위치: p01_backEnd/DAO/landValueDAO.py
import logging
import httpx
from datetime import datetime
from DAO.baseDAO import BaseDAO

logger = logging.getLogger(__name__)

VWORLD_KEY = "BE3AF33A-202E-3D5F-A8AD-63D9EE291ABF"


class LandValueDAO(BaseDAO):
    """VWorld 개별공시지가 조회"""

    async def fetch(self, pnu: str, years: int = 5) -> dict:
        """PNU 기반 최근 N년 공시지가 이력"""
        current_year = datetime.now().year
        results = []

        async with httpx.AsyncClient(timeout=15) as client:
            for i in range(years):
                year = str(current_year - i)
                try:
                    url = (
                        f"https://api.vworld.kr/req/data"
                        f"?service=data&version=2.0&request=GetFeature"
                        f"&format=json&errorFormat=json&data=LP_PA_CBND_BUBUN"
                        f"&key={VWORLD_KEY}&attrFilter=pnu:=:{pnu}"
                        f"&columns=pnu,pblntfPclnd,stdrYear&size=1&page=1"
                    )
                    res = await client.get(url)
                    raw = res.text.strip()
                    if not raw or raw.startswith("<"):
                        continue
                    d      = res.json()
                    if d.get("response", {}).get("status") != "OK":
                        continue
                    features = (
                        d.get("response", {}).get("result", {})
                         .get("featureCollection", {}).get("features", [])
                    )
                    for feat in (features or []):
                        props = feat.get("properties", {})
                        price = props.get("pblntfPclnd")
                        stdr  = props.get("stdrYear", year)
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