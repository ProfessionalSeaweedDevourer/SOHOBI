# 위치: p01_backEnd/DAO/sangkwonDAO.py
#
# ── 전략 ────────────────────────────────────────────────────────
#  매출 (SANGKWON_SALES 테이블):
#    19~25년 CSV를 DBeaver로 Oracle import
#    서버 시작 시 V_SANGKWON_LATEST 뷰 → pandas DataFrame 메모리 로드
#    조회: DataFrame 필터링 (1~5ms)
#
#  유동인구:
#    추후 구현
# ────────────────────────────────────────────────────────────────

import os
import logging
import pandas as pd

logger = logging.getLogger(__name__)

DB_INFO = "fable/1@//195.168.9.168:1521/xe"


class SangkwonDAO:

    def __init__(self):
        self._df: pd.DataFrame = None  # V_SANGKWON_LATEST 전체 캐시
        self._loaded = False
        logger.info("[SangkwonDAO] 초기화")

    # ── DB 연결 ──────────────────────────────────────────────────
    def _db_con(self):
        from fable.oracleDBConnect import OracleDBConnect

        return OracleDBConnect.makeConCur(DB_INFO)

    # ════════════════════════════════════════════════════════════
    # 1. 서버 시작 시 DB → DataFrame 로드
    # ════════════════════════════════════════════════════════════

    def load(self):
        """
        서버 시작 시 호출
        V_SANGKWON_LATEST 뷰 → 메모리 DataFrame
        """
        sql = """
            SELECT
                행정동_코드,
                행정동_코드_명,
                기준_년분기_코드,
                TOT_SALES_AMT,
                TOT_SELNG_CO,
                ML_SALES_AMT,
                FML_SALES_AMT,
                MDWK_SALES_AMT,
                WKEND_SALES_AMT,
                AGE20_AMT,
                AGE30_AMT,
                AGE40_AMT,
                AGE50_AMT
            FROM V_SANGKWON_LATEST
        """
        try:
            con, cur = self._db_con()
            try:
                cur.execute(sql)
                cols = [d[0].lower() for d in cur.description]
                rows = cur.fetchall()
                self._df = pd.DataFrame(rows, columns=cols)
                self._loaded = True
                logger.info(f"[SangkwonDAO] DB 로드 완료: {len(self._df)}개 행정동")
            finally:
                from fable.oracleDBConnect import OracleDBConnect

                OracleDBConnect.closeConCur(con, cur)
        except Exception as e:
            logger.error(f"[SangkwonDAO] DB 로드 실패: {e}")
            self._df = pd.DataFrame()

    # ════════════════════════════════════════════════════════════
    # 2. 매출 조회 (DataFrame 필터링)
    # ════════════════════════════════════════════════════════════

    def getSalesByGu(self, gu: str) -> list:
        """
        구 내 전체 행정동 매출 반환
        - gu: 자치구명 (예: 마포구)
        - ADSTRD_CD 앞 5자리로 구 필터링
        """
        if self._df is None or self._df.empty:
            return []

        # 구코드 앞 5자리 매핑
        GU_CODE = {
            "종로구": "11110",
            "중구": "11140",
            "용산구": "11170",
            "성동구": "11200",
            "광진구": "11215",
            "동대문구": "11230",
            "중랑구": "11260",
            "성북구": "11290",
            "강북구": "11305",
            "도봉구": "11320",
            "노원구": "11350",
            "은평구": "11380",
            "서대문구": "11410",
            "마포구": "11440",
            "양천구": "11470",
            "강서구": "11500",
            "구로구": "11530",
            "금천구": "11545",
            "영등포구": "11560",
            "동작구": "11590",
            "관악구": "11620",
            "서초구": "11650",
            "강남구": "11680",
            "송파구": "11710",
            "강동구": "11740",
        }
        code_prefix = GU_CODE.get(gu)
        if not code_prefix:
            return []

        df_gu = self._df[
            self._df["행정동_코드"].astype(str).str.startswith(code_prefix)
        ]
        return df_gu.to_dict("records")

    def getSalesByDong(self, dong: str, gu: str = "") -> dict:
        """
        행정동 단건 매출 반환
        - dong: 행정동명 (예: 공덕동)
        - gu: 자치구명 (중복 행정동명 구분용)
        """
        if self._df is None or self._df.empty:
            return None

        df = self._df[self._df["행정동_코드_명"] == dong]

        # 구로 추가 필터
        if gu and len(df) > 1:
            GU_CODE = {
                "종로구": "11110",
                "중구": "11140",
                "용산구": "11170",
                "성동구": "11200",
                "광진구": "11215",
                "동대문구": "11230",
                "중랑구": "11260",
                "성북구": "11290",
                "강북구": "11305",
                "도봉구": "11320",
                "노원구": "11350",
                "은평구": "11380",
                "서대문구": "11410",
                "마포구": "11440",
                "양천구": "11470",
                "강서구": "11500",
                "구로구": "11530",
                "금천구": "11545",
                "영등포구": "11560",
                "동작구": "11590",
                "관악구": "11620",
                "서초구": "11650",
                "강남구": "11680",
                "송파구": "11710",
                "강동구": "11740",
            }
            prefix = GU_CODE.get(gu)
            if prefix:
                df = df[df["행정동_코드"].astype(str).str.startswith(prefix)]

        if df.empty:
            return None
        return df.iloc[0].to_dict()

    def getSalesByCode(self, adstrd_cd: str) -> dict:
        """행정동 코드로 단건 조회"""
        if self._df is None or self._df.empty:
            return None
        df = self._df[self._df["행정동_코드"].astype(str) == str(adstrd_cd)]
        if df.empty:
            return None
        return df.iloc[0].to_dict()

    def getSalesByInduty(self, adstrd_cd: str, induty_cd: str = "") -> list:
        """
        특정 행정동 업종별 매출 (DB 직접 조회)
        - 업종 분석 패널용
        """
        sql = """
            SELECT
                서비스_업종_코드,
                서비스_업종_코드_명,
                당월_매출_금액,
                당월_매출_건수,
                남성_매출_금액,
                여성_매출_금액,
                주중_매출_금액,
                주말_매출_금액,
                연령대_20_매출_금액,
                연령대_30_매출_금액,
                연령대_40_매출_금액,
                연령대_50_매출_금액
            FROM SANGKWON_SALES
            WHERE 행정동_코드 = :cd
              AND 기준_년분기_코드 = (SELECT MAX(기준_년분기_코드) FROM SANGKWON_SALES)
        """
        if induty_cd:
            sql += " AND 서비스_업종_코드 = :ind"

        try:
            con, cur = self._db_con()
            try:
                params = {"cd": adstrd_cd}
                if induty_cd:
                    params["ind"] = induty_cd
                cur.execute(sql, params)
                cols = [d[0].lower() for d in cur.description]
                rows = cur.fetchall()
                return [dict(zip(cols, r)) for r in rows]
            finally:
                from fable.oracleDBConnect import OracleDBConnect

                OracleDBConnect.closeConCur(con, cur)
        except Exception as e:
            logger.error(f"[SangkwonDAO] 업종별 조회 실패: {e}")
            return []

    def getQuarters(self) -> list:
        """DB에 있는 분기 목록 조회"""
        try:
            con, cur = self._db_con()
            try:
                cur.execute(
                    "SELECT DISTINCT 기준_년분기_코드 FROM SANGKWON_SALES ORDER BY 기준_년분기_코드"
                )
                return [r[0] for r in cur.fetchall()]
            finally:
                from fable.oracleDBConnect import OracleDBConnect

                OracleDBConnect.closeConCur(con, cur)
        except Exception as e:
            logger.error(f"[SangkwonDAO] 분기목록 조회 실패: {e}")
            return []

    def getStatus(self) -> dict:
        cnt = len(self._df) if self._df is not None else 0
        quarter = ""
        if self._df is not None and not self._df.empty:
            quarter = str(self._df["기준_년분기_코드"].max())
        return {
            "loaded": self._loaded,
            "dong_count": cnt,
            "latest_quarter": quarter,
        }