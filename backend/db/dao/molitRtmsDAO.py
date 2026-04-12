# 위치: SOHOBI/backend/DAO/molitRtmsDAO.py
# PostgreSQL (Azure) 버전

import logging
from datetime import datetime

from .baseDAO import BaseDAO

logger = logging.getLogger(__name__)


def _ymds(months_back: int) -> list:
    """최근 N개월 YYYYMM 목록"""
    now = datetime.now()
    result = []
    for i in range(months_back):
        m = now.month - i
        y = now.year
        while m <= 0:
            m += 12
            y -= 1
        result.append(f"{y}{m:02d}")
    return result


class MolitRtmsDAO(BaseDAO):
    def get_law_nms_by_adm_cd(self, adm_cd: str) -> list:
        try:
            rows = self._query(
                """
                SELECT DISTINCT l.law_nm
                FROM law_adm_map m
                JOIN law_dong_seoul l ON m.law_cd = l.law_cd
                WHERE m.adm_cd = %(adm_cd)s
            """,
                {"adm_cd": adm_cd},
            )
            return [r["law_nm"] for r in rows if r["law_nm"]]
        except Exception as e:
            logger.error(f"[MolitRtmsDAO] get_law_nms: {e}")
            return []

    # ── 오피스텔 전월세 ───────────────────────────────────────────

    def fetch_officetel_rent(self, adm_cd: str, months_back: int = 12) -> dict:
        law_nms = self.get_law_nms_by_adm_cd(adm_cd)
        if not law_nms:
            return {"has_data": False, "전세": {"건수": 0}, "월세": {"건수": 0}}

        ymds = _ymds(months_back)
        # PostgreSQL: ANY(array) 방식
        try:
            sql = """
                SELECT offi_nm, umd_nm, floor, exclu_use_ar,
                       deal_ymd, deal_day, deposit, monthly_rent,
                       build_year, sgg_nm
                FROM rtms_officetel
                WHERE umd_nm = ANY(%(law_nms)s)
                  AND deal_ymd = ANY(%(ymds)s)
                ORDER BY deal_ymd DESC, deal_day DESC
            """
            rows = self._query(sql, {"law_nms": law_nms, "ymds": ymds})
            logger.info(f"[MolitRtmsDAO] 오피스텔: adm_cd={adm_cd} → {len(rows)}건")
        except Exception as e:
            logger.error(f"[MolitRtmsDAO] 오피스텔 조회 오류: {e}")
            return {"has_data": False, "전세": {"건수": 0}, "월세": {"건수": 0}}

        전세, 월세 = [], []
        for r in rows:
            base = {
                "건물명": r["offi_nm"],
                "법정동": r["umd_nm"],
                "층": r["floor"],
                "면적": r["exclu_use_ar"],
                "계약일": f"{r['deal_ymd']}{str(r['deal_day']).zfill(2) if r['deal_day'] else ''}",
                "건축년도": r["build_year"],
                "구": r["sgg_nm"],
            }
            deposit = r["deposit"]
            monthly = r["monthly_rent"]
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
        law_nms = self.get_law_nms_by_adm_cd(adm_cd)
        if not law_nms:
            return {"has_data": False, "매매": {"건수": 0}}

        ymds = _ymds(months_back)
        try:
            sql = """
                SELECT umd_nm, floor, deal_amount, building_use,
                       building_ar, land_use, deal_ymd, deal_day,
                       build_year, sgg_nm
                FROM rtms_commercial
                WHERE umd_nm = ANY(%(law_nms)s)
                  AND deal_ymd = ANY(%(ymds)s)
                ORDER BY deal_ymd DESC, deal_day DESC
            """
            rows = self._query(sql, {"law_nms": law_nms, "ymds": ymds})
            logger.info(f"[MolitRtmsDAO] 상업용: adm_cd={adm_cd} → {len(rows)}건")
        except Exception as e:
            logger.error(f"[MolitRtmsDAO] 상업용 조회 오류: {e}")
            return {"has_data": False, "매매": {"건수": 0}}

        매매 = []
        for r in rows:
            amt = r["deal_amount"]
            if not amt:
                continue
            매매.append(
                {
                    "법정동": r["umd_nm"],
                    "층": r["floor"],
                    "거래금액만원": amt,
                    "거래금액": f"{amt:,}만원",
                    "용도": r["building_use"],
                    "면적": r["building_ar"],
                    "용도지역": r["land_use"],
                    "계약일": f"{r['deal_ymd']}{str(r['deal_day']).zfill(2) if r['deal_day'] else ''}",
                    "건축년도": r["build_year"],
                    "구": r["sgg_nm"],
                }
            )

        return {"has_data": len(매매) > 0, "매매": self._stats(매매, "거래금액만원")}

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
            "평균가": int(sum(prices) / len(prices)),
            "최저가": min(prices),
            "최고가": max(prices),
            "목록": sorted_items[:20],
        }

    def _stats_monthly(self, items: list) -> dict:
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
