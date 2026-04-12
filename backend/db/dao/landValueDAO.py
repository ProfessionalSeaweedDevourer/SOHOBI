# 위치: backend/db/dao/landValueDAO.py
# VWorld API 대신 PostgreSQL land_value 테이블 직접 조회
# 반환 형식: {"pnu", "count", "data": [{"year", "price", "price_str"}]}

import logging

from .baseDAO import BaseDAO

logger = logging.getLogger(__name__)


class LandValueDAO(BaseDAO):
    def fetch_sync(self, pnu: str, years: int = 5) -> dict:
        """PNU 기반 최근 N년 공시지가 이력 (동기 버전)"""
        if not pnu or len(pnu) < 15:
            return {"pnu": pnu, "count": 0, "data": [], "unit": "원/㎡"}
        try:
            rows = self._query(
                """
                SELECT year, price
                FROM land_value
                WHERE pnu = %(pnu)s
                ORDER BY year DESC
                LIMIT %(years)s
            """,
                {"pnu": pnu, "years": years},
            )

            data = []
            for r in rows:
                price = r.get("price")
                if price:
                    data.append(
                        {
                            "year": str(r["year"]),
                            "price": price,
                            "price_str": f"{price:,}원/㎡",
                        }
                    )
            return {"pnu": pnu, "count": len(data), "data": data, "unit": "원/㎡"}
        except Exception as e:
            logger.error(f"[LandValueDAO] fetch_sync error pnu={pnu} e={e}")
            return {"pnu": pnu, "count": 0, "data": [], "unit": "원/㎡"}

    async def fetch(self, pnu: str, years: int = 5) -> dict:
        """async 래퍼 (기존 호출 코드 호환)"""
        return self.fetch_sync(pnu, years)
