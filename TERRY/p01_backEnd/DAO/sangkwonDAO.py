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


from .baseDAO import BaseDAO


class SangkwonDAO(BaseDAO):

    def __init__(self):
        self._df: pd.DataFrame = None  # V_SANGKWON_LATEST 전체 캐시
        self._loaded = False
        logger.info("[SangkwonDAO] 초기화")

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
                adm_cd,
                adm_nm,
                base_yr_qtr_cd,
                tot_sales_amt,
                ml_sales_amt,
                fml_sales_amt,
                mdwk_sales_amt,
                wkend_sales_amt,
                age20_amt,
                age30_amt,
                age40_amt,
                age50_amt
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
                self._close(con, cur)
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

        df_gu = self._df[self._df["adm_cd"].astype(str).str.startswith(code_prefix)]
        return df_gu.to_dict("records")

    def getSalesByDong(self, dong: str, gu: str = "") -> dict:
        """
        행정동 단건 매출 반환
        - dong: 행정동명 (예: 공덕동)
        - gu: 자치구명 (중복 행정동명 구분용)
        """
        if self._df is None or self._df.empty:
            return None

        df = self._df[self._df["adm_nm"] == dong]

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
                df = df[df["adm_cd"].astype(str).str.startswith(prefix)]

        if df.empty:
            return None
        return df.iloc[0].to_dict()

    def getSalesByCode(self, adstrd_cd: str) -> dict:
        """행정동 코드로 단건 조회 (8자리 또는 10자리, float형 모두 대응)"""
        if self._df is None or self._df.empty:
            return None
        adstrd_cd = str(adstrd_cd).strip()
        # Oracle NUMBER → float → '1115051000.0' 형태 정리
        db_codes = self._df["adm_cd"].apply(
            lambda x: str(int(float(x))) if str(x).endswith(".0") else str(x)
        )
        df = self._df[db_codes == adstrd_cd]
        if df.empty and len(adstrd_cd) == 8:
            df = self._df[db_codes.str[:8] == adstrd_cd]
        if df.empty and len(adstrd_cd) == 10:
            df = self._df[db_codes == adstrd_cd[:8]]
        sample = db_codes.unique()[:5].tolist()
        logger.info(
            f"[SangkwonDAO] getSalesByCode: adstrd_cd={adstrd_cd} → {'있음' if not df.empty else '없음'} / DB코드샘플={sample}"
        )
        if df.empty:
            return None
        return df.iloc[0].to_dict()

    def getSalesByCodeAndQuarter(self, adstrd_cd: str, quarter: str) -> dict:
        """특정 분기 단건 조회 (DB 직접)"""
        sql = """
            SELECT
                adm_cd, adm_nm, base_yr_qtr_cd,
                SUM(tot_sales_amt)   AS tot_sales_amt,
                SUM(tot_selng_co)    AS tot_selng_co,
                SUM(ml_sales_amt)    AS ml_sales_amt,
                SUM(fml_sales_amt)   AS fml_sales_amt,
                SUM(mdwk_sales_amt)  AS mdwk_sales_amt,
                SUM(wkend_sales_amt) AS wkend_sales_amt,
                SUM(age20_amt)       AS age20_amt,
                SUM(age30_amt)       AS age30_amt,
                SUM(age40_amt)       AS age40_amt,
                SUM(age50_amt)       AS age50_amt
            FROM SANGKWON_SALES
            WHERE adm_cd = :cd
              AND base_yr_qtr_cd = :qtr
            GROUP BY adm_cd, adm_nm, base_yr_qtr_cd
        """
        try:
            con, cur = self._db_con()
            try:
                cur.execute(sql, {"cd": adstrd_cd, "qtr": quarter})
                cols = [d[0].lower() for d in cur.description]
                row = cur.fetchone()
                return dict(zip(cols, row)) if row else None
            finally:
                self._close(con, cur)
        except Exception as e:
            logger.error(f"[SangkwonDAO] 분기조회 실패: {e}")
            return None

    def getSalesAvgByCode(self, adstrd_cd: str) -> dict:
        """전체 분기 평균 매출 (19~25년 DB 직접)"""
        sql = """
            SELECT
                COUNT(DISTINCT base_yr_qtr_cd)  AS qtr_cnt,
                SUM(tot_sales_amt)               AS tot_sales_sum,
                SUM(tot_selng_co)                AS tot_selng_sum,
                SUM(ml_sales_amt)                AS ml_sales_sum,
                SUM(fml_sales_amt)               AS fml_sales_sum,
                SUM(mdwk_sales_amt)              AS mdwk_sales_sum,
                SUM(wkend_sales_amt)             AS wkend_sales_sum,
                SUM(age20_amt)                   AS age20_sum,
                SUM(age30_amt)                   AS age30_sum,
                SUM(age40_amt)                   AS age40_sum,
                SUM(age50_amt)                   AS age50_sum
            FROM SANGKWON_SALES
            WHERE adm_cd = :cd
        """
        try:
            con, cur = self._db_con()
            try:
                cur.execute(sql, {"cd": adstrd_cd})
                cols = [d[0].lower() for d in cur.description]
                row = cur.fetchone()
                if not row:
                    return None
                d = dict(zip(cols, row))
                cnt = d["qtr_cnt"] or 1
                # 분기 수로 나눠서 평균
                return {
                    "adm_cd": adstrd_cd,
                    "quarter": "avg",
                    "qtr_cnt": cnt,
                    "tot_sales_amt": round((d["tot_sales_sum"] or 0) / cnt),
                    "tot_selng_co": round((d["tot_selng_sum"] or 0) / cnt),
                    "ml_sales_amt": round((d["ml_sales_sum"] or 0) / cnt),
                    "fml_sales_amt": round((d["fml_sales_sum"] or 0) / cnt),
                    "mdwk_sales_amt": round((d["mdwk_sales_sum"] or 0) / cnt),
                    "wkend_sales_amt": round((d["wkend_sales_sum"] or 0) / cnt),
                    "age20_amt": round((d["age20_sum"] or 0) / cnt),
                    "age30_amt": round((d["age30_sum"] or 0) / cnt),
                    "age40_amt": round((d["age40_sum"] or 0) / cnt),
                    "age50_amt": round((d["age50_sum"] or 0) / cnt),
                }
            finally:
                self._close(con, cur)
        except Exception as e:
            logger.error(f"[SangkwonDAO] 평균조회 실패: {e}")
            return None

    def getSalesByInduty(self, adstrd_cd: str, induty_cd: str = "") -> list:
        """
        특정 행정동 업종별 매출 (DB 직접 조회)
        - 업종 분석 패널용
        """
        sql = """
            SELECT
                svc_induty_cd,
                svc_induty_nm,
                tot_sales_amt,
                ml_sales_amt,
                fml_sales_amt,
                mdwk_sales_amt,
                wkend_sales_amt,
                age20_amt,
                age30_amt,
                age40_amt,
                age50_amt
            FROM SANGKWON_SALES
            WHERE adm_cd = :cd
              AND base_yr_qtr_cd = (SELECT MAX(base_yr_qtr_cd) FROM SANGKWON_SALES)
        """
        if induty_cd:
            sql += " AND svc_induty_cd = :ind"

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
                self._close(con, cur)
        except Exception as e:
            logger.error(f"[SangkwonDAO] 업종별 조회 실패: {e}")
            return []

    def getSalesBySvcCd(self, adstrd_cd: str, quarter: str = "") -> list:
        """
        행정동 SVC_CD(대분류) 기준 매출 합산
        - SVC_INDUTY_MAP JOIN → SVC_CD 그룹핑
        - quarter 없으면 최신 분기
        """
        qtr_cond = (
            "= :qtr"
            if quarter
            else "= (SELECT MAX(base_yr_qtr_cd) FROM SANGKWON_SALES)"
        )
        sql = f"""
            SELECT
                m.svc_cd,
                m.svc_nm,
                SUM(s.tot_sales_amt)  AS tot_sales_amt,
                SUM(s.ml_sales_amt)   AS ml_sales_amt,
                SUM(s.fml_sales_amt)  AS fml_sales_amt,
                SUM(s.mdwk_sales_amt) AS mdwk_sales_amt,
                SUM(s.wkend_sales_amt)AS wkend_sales_amt,
                SUM(s.age20_amt)      AS age20_amt,
                SUM(s.age30_amt)      AS age30_amt,
                SUM(s.age40_amt)      AS age40_amt,
                SUM(s.age50_amt)      AS age50_amt,
                COUNT(DISTINCT s.svc_induty_cd) AS induty_cnt
            FROM SANGKWON_SALES s
            JOIN SVC_INDUTY_MAP m ON s.svc_induty_cd = m.svc_induty_cd
            WHERE s.adm_cd = :cd
              AND s.base_yr_qtr_cd {qtr_cond}
            GROUP BY m.svc_cd, m.svc_nm
            ORDER BY tot_sales_amt DESC NULLS LAST
        """
        try:
            con, cur = self._db_con()
            try:
                params = {"cd": adstrd_cd}
                if quarter:
                    params["qtr"] = quarter
                cur.execute(sql, params)
                cols = [d[0].lower() for d in cur.description]
                rows = cur.fetchall()
                result = [dict(zip(cols, r)) for r in rows]
                logger.info(
                    f"[SangkwonDAO] getSalesBySvcCd: adm_cd={adstrd_cd} → {len(result)}개 업종"
                )
                return result
            finally:
                self._close(con, cur)
        except Exception as e:
            logger.error(f"[SangkwonDAO] getSalesBySvcCd 실패: {e}")
            return []

    def searchDong(self, q: str) -> list:
        """
        행정동 이름 LIKE 검색
        - SANGKWON_SALES에서 adm_cd, adm_nm 검색
        - q: 검색어 (부분 일치)
        """
        try:
            sql = """
                SELECT DISTINCT adm_cd, adm_nm
                FROM SANGKWON_SALES
                WHERE adm_nm LIKE :q
                ORDER BY adm_nm
            """
            rows = self._query(sql, {"q": f"%{q}%"})
            result = [{"adm_cd": r[0], "adm_nm": r[1]} for r in rows]
            logger.info(f"[SangkwonDAO] searchDong: '{q}' → {len(result)}개")
            return result
        except Exception as e:
            logger.error(f"[SangkwonDAO] searchDong 실패: {e}")
            return []

    def getQuarters(self) -> list:
        """DB에 있는 분기 목록 조회"""
        try:
            rows = self._query(
                "SELECT DISTINCT base_yr_qtr_cd FROM SANGKWON_SALES ORDER BY base_yr_qtr_cd"
            )
            return [r[0] for r in rows]
        except Exception as e:
            logger.error(f"[SangkwonDAO] 분기목록 조회 실패: {e}")
            return []

    def getStatus(self) -> dict:
        cnt = len(self._df) if self._df is not None else 0
        quarter = ""
        if self._df is not None and not self._df.empty:
            quarter = str(self._df["base_yr_qtr_cd"].max())
        return {
            "loaded": self._loaded,
            "dong_count": cnt,
            "latest_quarter": quarter,
        }
