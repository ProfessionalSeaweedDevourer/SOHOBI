# 위치: SOHOBI/backend/DAO/sangkwonDAO.py
# PostgreSQL (Azure) 버전

import logging

from .baseDAO import BaseDAO

logger = logging.getLogger(__name__)

LATEST_QTR = "(SELECT MAX(base_yr_qtr_cd) FROM sangkwon_sales)"

SELECT_SALES_SUM = """
    SELECT
        adm_cd, adm_nm, base_yr_qtr_cd,
        SUM(tot_sales_amt)     AS tot_sales_amt,
        SUM(tot_selng_co)      AS tot_selng_co,
        SUM(ml_sales_amt)      AS ml_sales_amt,
        SUM(fml_sales_amt)     AS fml_sales_amt,
        SUM(mdwk_sales_amt)    AS mdwk_sales_amt,
        SUM(wkend_sales_amt)   AS wkend_sales_amt,
        SUM(mon_sales_amt)     AS mon_sales_amt,
        SUM(tue_sales_amt)     AS tue_sales_amt,
        SUM(wed_sales_amt)     AS wed_sales_amt,
        SUM(thu_sales_amt)     AS thu_sales_amt,
        SUM(fri_sales_amt)     AS fri_sales_amt,
        SUM(sat_sales_amt)     AS sat_sales_amt,
        SUM(sun_sales_amt)     AS sun_sales_amt,
        SUM(tm00_06_sales_amt) AS tm00_06_sales_amt,
        SUM(tm06_11_sales_amt) AS tm06_11_sales_amt,
        SUM(tm11_14_sales_amt) AS tm11_14_sales_amt,
        SUM(tm14_17_sales_amt) AS tm14_17_sales_amt,
        SUM(tm17_21_sales_amt) AS tm17_21_sales_amt,
        SUM(tm21_24_sales_amt) AS tm21_24_sales_amt,
        SUM(age10_amt) AS age10_amt,
        SUM(age20_amt) AS age20_amt,
        SUM(age30_amt) AS age30_amt,
        SUM(age40_amt) AS age40_amt,
        SUM(age50_amt) AS age50_amt,
        SUM(age60_amt) AS age60_amt
"""


class SangkwonDAO(BaseDAO):
    def __init__(self):
        self._ensure_search_indexes()

    def _ensure_search_indexes(self):
        """searchDong prefix LIKE 성능을 위한 B-tree 인덱스 생성 (없으면 생성)"""
        sqls = [
            "CREATE INDEX IF NOT EXISTS idx_sangkwon_adm_nm ON sangkwon_sales (adm_nm text_pattern_ops)",
            "CREATE INDEX IF NOT EXISTS idx_store_legal_nm ON store_seoul (legal_nm text_pattern_ops)",
        ]
        try:
            for sql in sqls:
                self._execute(sql)
            logger.debug("[SangkwonDAO] search 인덱스 확인 완료")
        except Exception as e:
            logger.warning("[SangkwonDAO] 인덱스 생성 실패 (무시): %s", e)

    def getQuarters(self) -> list:
        try:
            rows = self._query(
                "SELECT DISTINCT base_yr_qtr_cd FROM sangkwon_sales ORDER BY base_yr_qtr_cd"
            )
            return [r["base_yr_qtr_cd"] for r in rows]
        except Exception as e:
            logger.error(f"[SangkwonDAO] getQuarters 실패: {e}")
            return []

    def getSalesByCode(self, adstrd_cd: str) -> dict:
        sql = f"""
            {SELECT_SALES_SUM}
            FROM sangkwon_sales
            WHERE adm_cd = %(cd)s
              AND base_yr_qtr_cd = {LATEST_QTR}
            GROUP BY adm_cd, adm_nm, base_yr_qtr_cd
        """
        try:
            rows = self._query(sql, {"cd": adstrd_cd})
            return rows[0] if rows else None
        except Exception as e:
            logger.error(f"[SangkwonDAO] getSalesByCode 실패: {e}")
            return None

    def getSalesByCodeAndQuarter(self, adstrd_cd: str, quarter: str) -> dict:
        sql = f"""
            {SELECT_SALES_SUM}
            FROM sangkwon_sales
            WHERE adm_cd = %(cd)s
              AND base_yr_qtr_cd = %(qtr)s
            GROUP BY adm_cd, adm_nm, base_yr_qtr_cd
        """
        try:
            rows = self._query(sql, {"cd": adstrd_cd, "qtr": quarter})
            return rows[0] if rows else None
        except Exception as e:
            logger.error(f"[SangkwonDAO] getSalesByCodeAndQuarter 실패: {e}")
            return None

    def getSalesAvgByCode(self, adstrd_cd: str) -> dict:
        sql = """
            SELECT
                COUNT(DISTINCT base_yr_qtr_cd) AS qtr_cnt,
                SUM(tot_sales_amt)   AS tot_sales_sum,
                SUM(tot_selng_co)    AS tot_selng_sum,
                SUM(ml_sales_amt)    AS ml_sales_sum,
                SUM(fml_sales_amt)   AS fml_sales_sum,
                SUM(mdwk_sales_amt)  AS mdwk_sales_sum,
                SUM(wkend_sales_amt) AS wkend_sales_sum,
                SUM(age20_amt) AS age20_sum,
                SUM(age30_amt) AS age30_sum,
                SUM(age40_amt) AS age40_sum,
                SUM(age50_amt) AS age50_sum
            FROM sangkwon_sales
            WHERE adm_cd = %(cd)s
        """
        try:
            rows = self._query(sql, {"cd": adstrd_cd})
            if not rows:
                return None
            d = rows[0]
            cnt = d["qtr_cnt"] or 1
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
        except Exception as e:
            logger.error(f"[SangkwonDAO] getSalesAvgByCode 실패: {e}")
            return None

    def getSalesBySvcCd(self, adstrd_cd: str, quarter: str = "") -> list:
        qtr_cond = "= %(qtr)s" if quarter else f"= {LATEST_QTR}"
        sql = f"""
            SELECT
                m.svc_cd,
                m.svc_nm,
                SUM(s.tot_sales_amt)   AS tot_sales_amt,
                SUM(s.ml_sales_amt)    AS ml_sales_amt,
                SUM(s.fml_sales_amt)   AS fml_sales_amt,
                SUM(s.mdwk_sales_amt)  AS mdwk_sales_amt,
                SUM(s.wkend_sales_amt) AS wkend_sales_amt,
                SUM(s.age20_amt) AS age20_amt,
                SUM(s.age30_amt) AS age30_amt,
                SUM(s.age40_amt) AS age40_amt,
                SUM(s.age50_amt) AS age50_amt,
                COUNT(DISTINCT s.svc_induty_cd) AS induty_cnt
            FROM sangkwon_sales s
            JOIN svc_induty_map m ON s.svc_induty_cd = m.svc_induty_cd
            WHERE s.adm_cd = %(cd)s
              AND s.base_yr_qtr_cd {qtr_cond}
            GROUP BY m.svc_cd, m.svc_nm
            ORDER BY tot_sales_amt DESC NULLS LAST
        """
        try:
            params = {"cd": adstrd_cd}
            if quarter:
                params["qtr"] = quarter
            result = self._query(sql, params)
            logger.info(
                f"[SangkwonDAO] getSalesBySvcCd: adm_cd={adstrd_cd} → {len(result)}개 업종"
            )
            return result
        except Exception as e:
            logger.error(f"[SangkwonDAO] getSalesBySvcCd 실패: {e}")
            return []

    def getSalesByCatCd(self, adstrd_cd: str, cat_cd: str, quarter: str = "") -> list:
        qtr_cond = (
            "AND ss.base_yr_qtr_cd = %(qtr)s"
            if quarter
            else f"AND ss.base_yr_qtr_cd = {LATEST_QTR}"
        )
        sql = f"""
            SELECT
                ss.svc_induty_cd,
                m.svc_nm AS svc_induty_nm,
                SUM(ss.tot_sales_amt)   AS tot_sales_amt,
                SUM(ss.ml_sales_amt)    AS ml_sales_amt,
                SUM(ss.fml_sales_amt)   AS fml_sales_amt,
                SUM(ss.mdwk_sales_amt)  AS mdwk_sales_amt,
                SUM(ss.wkend_sales_amt) AS wkend_sales_amt,
                SUM(ss.age20_amt) AS age20_amt,
                SUM(ss.age30_amt) AS age30_amt,
                SUM(ss.age40_amt) AS age40_amt,
                SUM(ss.age50_amt) AS age50_amt
            FROM sangkwon_sales ss
            JOIN svc_induty_map m ON ss.svc_induty_cd = m.svc_induty_cd
            WHERE ss.adm_cd = %(cd)s
              AND m.svc_cd = %(cat_cd)s
              {qtr_cond}
            GROUP BY ss.svc_induty_cd, m.svc_nm
            ORDER BY tot_sales_amt DESC NULLS LAST
        """
        try:
            params = {"cd": adstrd_cd, "cat_cd": cat_cd}
            if quarter:
                params["qtr"] = quarter
            return self._query(sql, params)
        except Exception as e:
            logger.error(f"[SangkwonDAO] getSalesByCatCd 실패: {e}")
            return []

    def getSalesByInduty(self, adstrd_cd: str, induty_cd: str = "") -> list:
        qtr_cond = f"AND base_yr_qtr_cd = {LATEST_QTR}"
        induty_cond = "AND svc_induty_cd = %(ind)s" if induty_cd else ""
        sql = f"""
            SELECT
                svc_induty_cd, svc_induty_nm,
                tot_sales_amt, ml_sales_amt, fml_sales_amt,
                mdwk_sales_amt, wkend_sales_amt,
                age20_amt, age30_amt, age40_amt, age50_amt
            FROM sangkwon_sales
            WHERE adm_cd = %(cd)s
              {qtr_cond}
              {induty_cond}
        """
        try:
            params = {"cd": adstrd_cd}
            if induty_cd:
                params["ind"] = induty_cd
            return self._query(sql, params)
        except Exception as e:
            logger.error(f"[SangkwonDAO] getSalesByInduty 실패: {e}")
            return []

    def searchDong(self, q: str) -> list:
        try:
            sql_adm = """
                SELECT DISTINCT adm_cd, adm_nm,
                       NULL::text AS legal_nm, '행정동' AS type
                FROM sangkwon_sales
                WHERE adm_nm LIKE %(q)s
                ORDER BY adm_nm
                LIMIT 20
            """
            rows = self._query(sql_adm, {"q": f"{q}%"})

            sql_legal = """
                SELECT DISTINCT adm_cd, adm_nm, legal_nm, '법정동' AS type
                FROM store_seoul
                WHERE legal_nm LIKE %(q)s
                  AND adm_cd IS NOT NULL
                ORDER BY adm_nm
                LIMIT 20
            """
            rows_legal = self._query(sql_legal, {"q": f"{q}%"})
            existing = {r["adm_cd"] for r in rows}
            for r in rows_legal:
                if r["adm_cd"] not in existing:
                    rows.append(r)
                    existing.add(r["adm_cd"])

            logger.info(f"[SangkwonDAO] searchDong: '{q}' → {len(rows)}개")
            return rows
        except Exception as e:
            logger.error(f"[SangkwonDAO] searchDong 실패: {e}")
            return []
