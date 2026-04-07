# 위치: p01_backEnd/DAO/seoulRtmsDAO.py
#
# 서울시 부동산 실거래가 통합 조회 DAO
#
# ① 서울 열린데이터광장 API (tbLnOpendataRtmsV)
#    - 아파트/연립/다세대 매매·전세·월세
#    - emd_cd(8자리) 기반 조회
#
# ② 국토교통부 오피스텔 전월세 (RTMSDataSvcOffiRent)
#    - umdNm(법정동명) → LAW_ADM_MAP LIKE 매핑
#
# ③ 국토교통부 상업·업무용 매매 (RTMSDataSvcNrgTrade)
#    - umdNm(법정동명) → LAW_ADM_MAP LIKE 매핑

import asyncio
import logging
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Optional
import os

import httpx
from .baseDAO import BaseDAO

logger = logging.getLogger(__name__)

# ── API 키 ───────────────────────────────────────────────────
SEOUL_RTMS_KEY = "4a656f6b4c7773743331707150564f"
SEOUL_RTMS_URL = (
    "http://openapi.seoul.go.kr:8088/{key}/xml/tbLnOpendataRtmsV/{start}/{end}/"
)


class SeoulRtmsDAO(BaseDAO):
    """서울시 부동산 실거래가 통합 조회 DAO"""

    def __init__(self):
        self._cache: dict = {}

    # ── DB: 법정동 조회 ──────────────────────────────────────────

    def get_emd_cd_by_adm_cd(self, adm_cd: str) -> Optional[str]:
        """하위호환용 - 첫 번째 emd_cd 반환"""
        emd_cds = self.get_emd_cds_by_adm_cd(adm_cd)
        return emd_cds[0] if emd_cds else None

    def get_emd_cds_by_adm_cd(self, adm_cd: str) -> list:
        """
        행정동코드 → emd_cd 목록 (1:N)
        하나의 행정동에 여러 법정동이 매핑될 수 있음
        """
        try:
            rows = self._query(
                "SELECT DISTINCT L.EMD_CD FROM LAW_ADM_MAP M "
                "JOIN LAW_DONG_SEOUL L ON M.LAW_CD = L.LAW_CD "
                "WHERE M.ADM_CD = :1 ORDER BY L.EMD_CD",
                [adm_cd],
            )
            return [str(r[0]) for r in rows if r[0]]
        except Exception as e:
            logger.error(f"[SeoulRtms] get_emd_cds_by_adm_cd: {e}")
            return []

    def get_law_cd_by_emd(self, emd_cd: str) -> Optional[str]:
        rows = self._query(
            "SELECT LAW_CD FROM LAW_DONG_SEOUL WHERE EMD_CD = :1", [emd_cd]
        )
        return str(rows[0][0]) if rows else None

    def get_law_cds_by_adm_cd(self, adm_cd: str) -> list:
        """행정동코드 → 법정동 목록"""
        rows = self._query(
            "SELECT DISTINCT M.LAW_CD, L.GU_NM, L.LAW_NM FROM LAW_ADM_MAP M "
            "JOIN LAW_DONG_SEOUL L ON M.LAW_CD = L.LAW_CD "
            "WHERE M.ADM_CD = :1",
            [adm_cd],
        )
        return [{"law_cd": r[0], "gu_nm": r[1], "law_nm": r[2]} for r in rows]

    def get_law_nms_by_adm_cd(self, adm_cd: str) -> list:
        """
        행정동코드 → 법정동명 목록 (국토부 API umdNm LIKE 매핑용)
        예: adm_cd=11680550 → ['삼성동', '대치동', ...]
        """
        rows = self._query(
            "SELECT DISTINCT L.LAW_NM FROM LAW_ADM_MAP M "
            "JOIN LAW_DONG_SEOUL L ON M.LAW_CD = L.LAW_CD "
            "WHERE M.ADM_CD = :1",
            [adm_cd],
        )
        return [r[0] for r in rows if r[0]]

    def get_gu_nm_by_adm_cd(self, adm_cd: str) -> str:
        """행정동코드 → 구이름"""
        rows = self._query(
            "SELECT DISTINCT L.GU_NM FROM LAW_ADM_MAP M "
            "JOIN LAW_DONG_SEOUL L ON M.LAW_CD = L.LAW_CD "
            "WHERE M.ADM_CD = :1 AND ROWNUM = 1",
            [adm_cd],
        )
        return rows[0][0] if rows else ""

    # ── ① 서울 열린데이터광장 API ────────────────────────────────

    async def _fetch_seoul_page(self, client, start, end, filters) -> list:
        url = SEOUL_RTMS_URL.format(key=SEOUL_RTMS_KEY, start=start, end=end)
        params = {k: v for k, v in filters.items() if v}
        try:
            r = await client.get(url, params=params, timeout=15)
            root = ET.fromstring(r.text)
            result = root.find(".//RESULT/CODE")
            if result is not None and result.text != "INFO-000":
                return []
            return root.findall(".//row")
        except Exception as e:
            logger.error(f"[SeoulRtms] _fetch_seoul_page: {e}")
            return []

    async def fetch_by_emd_cd(self, emd_cd: str, years_back: int = 3) -> dict:
        """
        서울 열린데이터광장: adm_cd → 여러 emd_cd 매핑 후 실거래 조회
        adm_cd 1개에 법정동 여러 개가 매핑될 수 있음
        """
        emd_cd = emd_cd.strip()
        # adm_cd → emd_cd 목록 조회 (1:N)
        emd_cds = self.get_emd_cds_by_adm_cd(emd_cd)
        if not emd_cds:
            emd_cds = [emd_cd]  # fallback
        cgg_cd = emd_cds[0][:5]
        years = [str(datetime.now().year - i) for i in range(years_back)]
        logger.info(f"[SeoulRtms] adm_cd={emd_cd} → emd_cds={emd_cds} cgg_cd={cgg_cd}")

        async with httpx.AsyncClient() as client:
            tasks = [
                self._fetch_seoul_page(
                    client, 1, 1000, {"CGG_CD": cgg_cd, "RCPT_YR": yr}
                )
                for yr in years
            ]
            results = await asyncio.gather(*tasks)

        all_rows = [r for rows in results for r in rows]

        def law_cd_8(r):
            return ((r.findtext("CGG_CD") or "") + (r.findtext("STDG_CD") or ""))[:8]

        emd_set = set(emd_cds)
        filtered = [r for r in all_rows if law_cd_8(r) in emd_set]
        logger.info(f"[SeoulRtms] 전체={len(all_rows)}건 → 필터={len(filtered)}건")
        return self._parse_seoul_rows(filtered)

    # ── 파싱 ────────────────────────────────────────────────────

    def _parse_seoul_rows(self, rows: list) -> dict:
        """서울 열린데이터광장 rows 파싱"""
        매매, 전세, 월세 = [], [], []
        for r in rows:

            def g(tag):
                return (r.findtext(tag) or "").strip()

            tpcd = g("RTMS_TPCD")
            thing_amt = g("THING_AMT").replace(",", "")
            rent_gtn = g("RENT_GTN").replace(",", "")
            rent_fe = g("RENT_FE").replace(",", "")
            ctrt_day = g("CTRT_DAY") or g("CNTRT_YMD")
            base = {
                "건물명": g("BLDG_NM"),
                "용도": g("BLDG_USG"),
                "면적": g("ARCH_AREA"),
                "층": g("FLR"),
                "계약일": ctrt_day,
            }
            if tpcd == "2" and rent_gtn:
                전세.append(
                    {**base, "보증금": rent_gtn, "보증금만원": self._to_int(rent_gtn)}
                )
            elif tpcd == "3":
                월세.append(
                    {
                        **base,
                        "보증금": rent_gtn,
                        "월세": rent_fe,
                        "보증금만원": self._to_int(rent_gtn),
                        "월세만원": self._to_int(rent_fe),
                    }
                )
            elif thing_amt:
                매매.append(
                    {
                        **base,
                        "거래금액": thing_amt,
                        "거래금액만원": self._to_int(thing_amt),
                    }
                )

        return {
            "has_data": len(매매) + len(전세) + len(월세) > 0,
            "매매": self._stats(매매, "거래금액만원", "거래금액"),
            "전세": self._stats(전세, "보증금만원", "보증금"),
            "월세": self._stats_monthly(월세),
        }

    def _stats(self, items, amt_key, display_key) -> dict:
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
            "평균가": int(sum(prices) / len(prices)),  # 숫자 반환 → 프론트 formatAmt
            "최저가": min(prices),
            "최고가": max(prices),
            "목록": sorted_items[:20],
        }

    def _stats_monthly(self, items: list) -> dict:
        """월세 전용 stats - 보증금 + 월세 평균 별도 계산"""
        if not items:
            return {
                "건수": 0,
                "평균가": None,
                "최저가": None,
                "최고가": None,
                "목록": [],
            }
        deposits = [x["보증금만원"] for x in items if x.get("보증금만원")]
        monthlys = [x["월세만원"] for x in items if x.get("월세만원")]
        sorted_items = sorted(items, key=lambda x: x.get("계약일", ""), reverse=True)
        return {
            "건수": len(items),
            "평균가": int(sum(deposits) / len(deposits)) if deposits else None,
            "최저가": min(deposits) if deposits else None,
            "최고가": max(deposits) if deposits else None,
            "평균보증금": int(sum(deposits) / len(deposits)) if deposits else None,
            "평균월세": int(sum(monthlys) / len(monthlys)) if monthlys else None,
            "목록": sorted_items[:10],
        }

    def _stats_monthly(self, items: list) -> dict:
        """월세 전용 stats"""
        if not items:
            return {
                "건수": 0,
                "평균가": None,
                "최저가": None,
                "최고가": None,
                "목록": [],
            }
        deposits = [x["보증금만원"] for x in items if x.get("보증금만원")]
        monthlys = [x["월세만원"] for x in items if x.get("월세만원")]
        sorted_items = sorted(items, key=lambda x: x.get("계약일", ""), reverse=True)
        return {
            "건수": len(items),
            "평균가": int(sum(deposits) / len(deposits)) if deposits else None,
            "최저가": min(deposits) if deposits else None,
            "최고가": max(deposits) if deposits else None,
            "평균보증금": int(sum(deposits) / len(deposits)) if deposits else None,
            "평균월세": int(sum(monthlys) / len(monthlys)) if monthlys else None,
            "목록": sorted_items[:10],
        }

    @staticmethod
    def _to_int(val) -> Optional[int]:
        try:
            return int(str(val).replace(",", "").strip())
        except:
            return None
