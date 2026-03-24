# 위치: p01_backEnd/DAO/seoulRtmsDAO.py
#
# 서울시 부동산 실거래가 (서울 열린데이터광장)
# API: tbLnOpendataRtmsV
# END_POINT: http://openapi.seoul.go.kr:8088/{key}/xml/tbLnOpendataRtmsV/{start}/{end}/
#
# 주요 필드:
#   STDG_CD   : 법정동코드(10자리) → EMD_CD(앞 8자리) = WFS emd_cd
#   STDG_NM   : 법정동명
#   CGG_NM    : 자치구명
#   RTMS_TPCD : 1=매매 2=전세 3=월세
#   THING_AMT : 물건금액(만원, 매매)
#   RENT_GTN  : 보증금(만원, 전월세)
#   RENT_FE   : 월세(만원)
#   CNTRT_YMD : 계약일 (YYYYMMDD)
#   BLDG_NM   : 건물명
#   BLDG_USG  : 건물용도
#   ARCH_AREA : 전용면적(㎡)
#   FLR       : 층
#   ARCH_YR   : 건축년도
# ─────────────────────────────────────────────────────────────

import asyncio
import logging
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Optional

import httpx
from baseDAO import BaseDAO

logger = logging.getLogger(__name__)

SEOUL_RTMS_KEY = "4a656f6b4c7773743331707150564f"
SEOUL_RTMS_URL = "http://openapi.seoul.go.kr:8088/{key}/xml/tbLnOpendataRtmsV/{start}/{end}/"


class SeoulRtmsDAO(BaseDAO):
    """서울시 부동산 실거래가 조회 DAO"""

    def __init__(self):
        self._cache: dict = {}

    # ── 1. 법정동코드 조회 (DB) ──────────────────────────────────

    def get_law_cd_by_emd(self, emd_cd: str) -> Optional[str]:
        """WFS emd_cd(8자리) → 법정동코드(10자리)"""
        rows = self._query("SELECT LAW_CD FROM LAW_DONG_SEOUL WHERE EMD_CD = :1", [emd_cd])
        return str(rows[0][0]) if rows else None

    def get_adm_by_law_cd(self, law_cd: str) -> list:
        """법정동코드 → 행정동 목록 (1:N, confidence 내림차순)"""
        rows = self._query(
            "SELECT ADM_CD, ADM_NM, CONFIDENCE FROM LAW_ADM_MAP "
            "WHERE LAW_CD = :1 ORDER BY CONFIDENCE DESC",
            [law_cd]
        )
        return [{"adm_cd": r[0], "adm_nm": r[1], "confidence": r[2]} for r in rows]

    def get_law_cds_by_adm_cd(self, adm_cd: str) -> list:
        """행정동코드 → 법정동 목록 (adm 기준 실거래 합산용)"""
        rows = self._query(
            "SELECT DISTINCT M.LAW_CD, L.GU_NM, L.LAW_NM FROM LAW_ADM_MAP M "
            "JOIN LAW_DONG_SEOUL L ON M.LAW_CD = L.LAW_CD "
            "WHERE M.ADM_CD = :1",
            [adm_cd]
        )
        return [{"law_cd": r[0], "gu_nm": r[1], "law_nm": r[2]} for r in rows]

    # ── 2. API 조회 ─────────────────────────────────────────────

    async def _fetch_page(self, client: httpx.AsyncClient,
                          start: int, end: int, filters: dict) -> list:
        """단일 페이지 조회"""
        url = SEOUL_RTMS_URL.format(
            key=SEOUL_RTMS_KEY, start=start, end=end
        )
        params = {k: v for k, v in filters.items() if v}
        try:
            r = await client.get(url, params=params, timeout=15)
            root = ET.fromstring(r.text)
            # 에러 체크
            result = root.find('.//RESULT/CODE')
            if result is not None and result.text != 'INFO-000':
                msg = root.findtext('.//RESULT/MESSAGE', '')
                logger.warning(f"[SeoulRtms] API 응답: {result.text} - {msg}")
                return []
            return root.findall('.//row')
        except Exception as e:
            logger.error(f"[SeoulRtms] _fetch_page error: {e}")
            return []

    async def fetch_by_gu(
        self,
        gu_nm: str,
        year: Optional[str] = None,
        rtms_type: Optional[str] = None,  # '1'=매매 '2'=전세 '3'=월세 None=전체
        page_size: int = 1000,
        max_pages: int = 5,
    ) -> dict:
        """
        자치구 기준 실거래 조회
        year: 4자리 연도 (None이면 최근 2년)
        """
        if not year:
            year = str(datetime.now().year)

        filters = {"CGG_NM": gu_nm, "RCPT_YR": year}
        if rtms_type:
            filters["RTMS_TPCD"] = rtms_type

        async with httpx.AsyncClient() as client:
            all_rows = []
            for page in range(max_pages):
                start = page * page_size + 1
                end   = (page + 1) * page_size
                rows  = await self._fetch_page(client, start, end, filters)
                all_rows.extend(rows)
                if len(rows) < page_size:
                    break

        return self._parse_rows(all_rows)

    async def fetch_by_emd_cd(
        self,
        emd_cd: str,
        years_back: int = 3,
        rtms_type: Optional[str] = None,
    ) -> dict:
        """
        WFS emd_cd(8자리) 기준 실거래 조회
        emd_cd[:5] = CGG_CD(구코드) → API 호출
        API 응답에서 (CGG_CD+STDG_CD)[:8] == emd_cd 로 필터
        이름 불일치 문제 없음, DB 매핑 테이블 불필요
        """
        emd_cd  = emd_cd.strip()
        cgg_cd  = emd_cd[:5]          # '11110'
        now     = datetime.now()
        years   = [str(now.year - i) for i in range(years_back)]

        logger.info(f"[SeoulRtms] fetch_by_emd_cd: emd_cd={emd_cd}, cgg_cd={cgg_cd}, years={years}")

        async with httpx.AsyncClient() as client:
            tasks = []
            for yr in years:
                filters = {"CGG_CD": cgg_cd, "RCPT_YR": yr}
                if rtms_type:
                    filters["RTMS_TPCD"] = rtms_type
                tasks.append(self._fetch_page(client, 1, 1000, filters))
            results = await asyncio.gather(*tasks)

        all_rows = []
        for rows in results:
            all_rows.extend(rows)

        logger.info(f"[SeoulRtms] 전체 수신: {len(all_rows)}건")

        # (CGG_CD + STDG_CD) 앞 8자리 == emd_cd
        def law_cd_8(r):
            return ((r.findtext('CGG_CD') or '') + (r.findtext('STDG_CD') or ''))[:8]

        filtered = [r for r in all_rows if law_cd_8(r) == emd_cd]
        logger.info(f"[SeoulRtms] emd_cd={emd_cd} 필터 후: {len(filtered)}건")
        return self._parse_rows(filtered)

    # ── 3. 파싱 ─────────────────────────────────────────────────

    def _parse_rows(self, rows: list) -> dict:
        """
        XML rows → 분석 결과 dict
        tbLnOpendataRtmsV API 특성:
          - RTMS_TPCD 없음 → 전부 매매 데이터
          - 계약일 필드: CTRT_DAY (CNTRT_YMD 아님)
          - STDG_CD: 5자리 (CGG_CD 5자리 + STDG_CD 5자리 = 10자리 → [:8] = emd_cd)
        """
        매매, 전세, 월세 = [], [], []

        for r in rows:
            def g(tag): return (r.findtext(tag) or '').strip()

            tpcd      = g('RTMS_TPCD')          # 있으면 사용, 없으면 아래에서 매매 처리
            cgg_cd    = g('CGG_CD')              # 5자리 구코드
            stdg_cd   = g('STDG_CD')             # 5자리 법정동코드
            emd_cd    = (cgg_cd + stdg_cd)[:8]   # 8자리 emd_cd
            thing_amt = g('THING_AMT').replace(',', '')
            rent_gtn  = g('RENT_GTN').replace(',', '')
            rent_fe   = g('RENT_FE').replace(',', '')
            # API마다 날짜 필드명 다름: CTRT_DAY 우선, 없으면 CNTRT_YMD
            ctrt_day  = g('CTRT_DAY') or g('CNTRT_YMD')

            base = {
                "법정동코드": stdg_cd,
                "emd_cd":    emd_cd,
                "법정동":    g('STDG_NM'),
                "구":        g('CGG_NM'),
                "건물명":    g('BLDG_NM'),
                "용도":      g('BLDG_USG'),
                "면적":      g('ARCH_AREA'),
                "층":        g('FLR'),
                "건축년도":  g('ARCH_YR'),
                "계약일":    ctrt_day,
                "년":        ctrt_day[:4] if ctrt_day else '',
                "월":        ctrt_day[4:6] if len(ctrt_day) >= 6 else '',
            }

            if tpcd == '2' and rent_gtn:
                전세.append({**base, "보증금": rent_gtn, "보증금만원": self._to_int(rent_gtn)})
            elif tpcd == '3':
                월세.append({**base, "보증금": rent_gtn, "월세": rent_fe,
                             "보증금만원": self._to_int(rent_gtn), "월세만원": self._to_int(rent_fe)})
            elif thing_amt:
                # TPCD==1 이거나 TPCD 없는 경우 모두 매매 처리
                매매.append({**base, "거래금액": thing_amt, "거래금액만원": self._to_int(thing_amt)})

        logger.info(f"[SeoulRtms] _parse_rows: 입력={len(rows)}건 → 매매={len(매매)} 전세={len(전세)} 월세={len(월세)}")

        return {
            "has_data": len(매매) + len(전세) + len(월세) > 0,
            "매매":  self._stats(매매,  "거래금액만원", "거래금액"),
            "전세":  self._stats(전세,  "보증금만원",   "보증금"),
            "월세":  {"건수": len(월세), "목록": sorted(월세, key=lambda x: x.get("계약일",""), reverse=True)[:10]},
        }

    def _stats(self, items: list, amt_key: str, display_key: str) -> dict:
        prices = [x[amt_key] for x in items if x.get(amt_key)]
        if not prices:
            return {"건수": 0, "평균가": None, "최저가": None, "최고가": None, "목록": []}
        sorted_items = sorted(items, key=lambda x: x.get("계약일", ""), reverse=True)
        return {
            "건수":  len(prices),
            "평균가": f"{int(sum(prices)/len(prices)):,}만원",
            "최저가": f"{min(prices):,}만원",
            "최고가": f"{max(prices):,}만원",
            "목록":  sorted_items[:20],
        }

    @staticmethod
    def _to_int(val: str) -> Optional[int]:
        try:
            return int(str(val).replace(',', '').strip())
        except:
            return None