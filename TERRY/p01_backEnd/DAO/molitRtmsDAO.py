# 위치: p01_backEnd/DAO/molitRtmsDAO.py
#
# 국토교통부 실거래가 DB 조회 DAO
# - RTMS_OFFICETEL  : 오피스텔 전월세
# - RTMS_COMMERCIAL : 상업·업무용 매매
#
# 수집: p04_DataLoader/collector/collect_molit_rtms.py

import logging
from typing import Optional

try:
    from baseDAO import BaseDAO
except ImportError:
    from DAO.baseDAO import BaseDAO

logger = logging.getLogger(__name__)


class MolitRtmsDAO(BaseDAO):
    """국토부 실거래가 DB 조회 DAO"""

    def get_law_nms_by_adm_cd(self, adm_cd: str) -> list:
        """행정동코드 → 법정동명 목록"""
        try:
            rows = self._query(
                "SELECT DISTINCT L.LAW_NM FROM LAW_ADM_MAP M "
                "JOIN LAW_DONG_SEOUL L ON M.LAW_CD = L.LAW_CD "
                "WHERE M.ADM_CD = :1",
                [adm_cd],
            )
            return [r[0] for r in rows if r[0]]
        except Exception as e:
            logger.error(f"[MolitRtmsDAO] get_law_nms: {e}")
            return []

    # ── 오피스텔 전월세 ───────────────────────────────────────────

    def fetch_officetel_rent(self, adm_cd: str, months_back: int = 12) -> dict:
        """
        오피스텔 전월세 DB 조회
        adm_cd → 법정동명 → RTMS_OFFICETEL WHERE UMD_NM IN (...)
        """
        law_nms = self.get_law_nms_by_adm_cd(adm_cd)
        sgg_cd = adm_cd[:5]

        if not law_nms:
            logger.info(f"[MolitRtmsDAO] 오피스텔: adm_cd={adm_cd} 법정동명 없음")
            return {"has_data": False, "전세": {"건수": 0}, "월세": {"건수": 0}}

        # 최근 N개월 YYYYMM
        from datetime import datetime

        now = datetime.now()
        ymds = []
        for i in range(months_back):
            m = now.month - i
            y = now.year
            while m <= 0:
                m += 12
                y -= 1
            ymds.append(f"{y}{m:02d}")

        placeholders = ",".join([f":{i+1}" for i in range(len(law_nms))])
        ymd_holders = ",".join([f":{i+1+len(law_nms)}" for i in range(len(ymds))])

        try:
            sql = f"""
                SELECT OFFI_NM, UMD_NM, FLOOR, EXCLU_USE_AR,
                       DEAL_YMD, DEAL_DAY, DEPOSIT, MONTHLY_RENT,
                       BUILD_YEAR, SGG_NM
                FROM RTMS_OFFICETEL
                WHERE UMD_NM IN ({placeholders})
                  AND DEAL_YMD IN ({ymd_holders})
                ORDER BY DEAL_YMD DESC, DEAL_DAY DESC
            """
            rows = self._query(sql, law_nms + ymds)
            logger.info(f"[MolitRtmsDAO] 오피스텔: adm_cd={adm_cd} → {len(rows)}건")
        except Exception as e:
            logger.error(f"[MolitRtmsDAO] 오피스텔 조회 오류: {e}")
            return {"has_data": False, "전세": {"건수": 0}, "월세": {"건수": 0}}

        전세, 월세 = [], []
        for r in rows:
            base = {
                "건물명": r[0],
                "법정동": r[1],
                "층": r[2],
                "면적": r[3],
                "계약일": f"{r[4]}{str(r[5]).zfill(2) if r[5] else ''}",
                "건축년도": r[8],
                "구": r[9],
            }
            deposit = r[6]
            monthly = r[7]
            if not monthly or monthly == 0:
                전세.append(
                    {
                        **base,
                        "보증금만원": deposit,
                        "보증금": f"{deposit:,}" if deposit else "-",
                    }
                )
            else:
                월세.append(
                    {
                        **base,
                        "보증금만원": deposit,
                        "월세만원": monthly,
                        "보증금": f"{deposit:,}" if deposit else "-",
                        "월세": f"{monthly:,}" if monthly else "-",
                    }
                )

        return {
            "has_data": len(전세) + len(월세) > 0,
            "전세": self._stats(전세, "보증금만원"),
            "월세": self._stats_monthly(월세),
        }

    # ── 상업·업무용 매매 ──────────────────────────────────────────

    def fetch_commercial_trade(self, adm_cd: str, months_back: int = 12) -> dict:
        """
        상업·업무용 매매 DB 조회
        adm_cd → 법정동명 → RTMS_COMMERCIAL WHERE UMD_NM IN (...)
        """
        law_nms = self.get_law_nms_by_adm_cd(adm_cd)
        sgg_cd = adm_cd[:5]

        if not law_nms:
            logger.info(f"[MolitRtmsDAO] 상업용: adm_cd={adm_cd} 법정동명 없음")
            return {"has_data": False, "매매": {"건수": 0}}

        from datetime import datetime

        now = datetime.now()
        ymds = []
        for i in range(months_back):
            m = now.month - i
            y = now.year
            while m <= 0:
                m += 12
                y -= 1
            ymds.append(f"{y}{m:02d}")

        placeholders = ",".join([f":{i+1}" for i in range(len(law_nms))])
        ymd_holders = ",".join([f":{i+1+len(law_nms)}" for i in range(len(ymds))])

        try:
            sql = f"""
                SELECT UMD_NM, FLOOR, DEAL_AMOUNT, BUILDING_USE,
                       BUILDING_AR, LAND_USE, DEAL_YMD, DEAL_DAY,
                       BUILD_YEAR, SGG_NM
                FROM RTMS_COMMERCIAL
                WHERE UMD_NM IN ({placeholders})
                  AND DEAL_YMD IN ({ymd_holders})
                ORDER BY DEAL_YMD DESC, DEAL_DAY DESC
            """
            rows = self._query(sql, law_nms + ymds)
            logger.info(f"[MolitRtmsDAO] 상업용: adm_cd={adm_cd} → {len(rows)}건")
        except Exception as e:
            logger.error(f"[MolitRtmsDAO] 상업용 조회 오류: {e}")
            return {"has_data": False, "매매": {"건수": 0}}

        매매 = []
        for r in rows:
            amt = r[2]
            if not amt:
                continue
            매매.append(
                {
                    "법정동": r[0],
                    "층": r[1],
                    "거래금액만원": amt,
                    "거래금액": f"{amt:,}만원",
                    "용도": r[3],
                    "면적": r[4],
                    "용도지역": r[5],
                    "계약일": f"{r[6]}{str(r[7]).zfill(2) if r[7] else ''}",
                    "건축년도": r[8],
                    "구": r[9],
                }
            )

        return {
            "has_data": len(매매) > 0,
            "매매": self._stats(매매, "거래금액만원"),
        }

    # ── 공통 유틸 ─────────────────────────────────────────────────

    def _stats(self, items: list, amt_key: str) -> dict:
        prices = [x[amt_key] for x in items if x.get(amt_key)]
        if not prices:
            return {
                "건수": 0,
                "평균가": None,
                "최저가": None,
                "최고가": None,
                "목록": [],
            }
        sorted_items = sorted(items, key=lambda x: x.get("계약일", ""), reverse=True)
        return {
            "건수": len(prices),
            "평균가": int(sum(prices) / len(prices)),  # 숫자로 반환 → 프론트 formatAmt
            "최저가": min(prices),
            "최고가": max(prices),
            "목록": sorted_items[:20],
        }

    def _stats_monthly(self, items: list) -> dict:
        """월세 전용 stats - 보증금 + 월세 평균 별도 계산"""
        if not items:
            return {"건수": 0, "평균보증금": None, "평균월세": None, "목록": []}
        deposits = [x["보증금만원"] for x in items if x.get("보증금만원")]
        monthlys = [x["월세만원"] for x in items if x.get("월세만원")]
        sorted_items = sorted(items, key=lambda x: x.get("계약일", ""), reverse=True)
        return {
            "건수": len(items),
            "평균보증금": int(sum(deposits) / len(deposits)) if deposits else None,
            "평균월세": int(sum(monthlys) / len(monthlys)) if monthlys else None,
            "목록": sorted_items[:10],
        }
