# 위치: SOHOBI/backend/DAO/sangkwonStoreDAO.py
# PostgreSQL (Azure) 버전

import logging

from .baseDAO import BaseDAO

logger = logging.getLogger(__name__)

LATEST_QTR = "(SELECT MAX(base_yr_qtr_cd) FROM sangkwon_store)"


class SangkwonStoreDAO(BaseDAO):
    def getStoreBySvcCd(self, adm_cd: str, quarter: str = "") -> list:
        """SVC_CD(대분류) 기준 점포수 합산"""
        qtr_cond = "= %(qtr)s" if quarter else f"= {LATEST_QTR}"
        sql = f"""
            SELECT
                m.svc_cd,
                m.svc_nm,
                SUM(s.stor_co)               AS stor_co,
                SUM(s.similr_induty_stor_co) AS similr_stor_co,
                SUM(s.frc_stor_co)           AS frc_stor_co,
                ROUND(AVG(s.opbiz_rt), 1)    AS opbiz_rt,
                SUM(s.opbiz_stor_co)         AS opbiz_stor_co,
                ROUND(AVG(s.clsbiz_rt), 1)   AS clsbiz_rt,
                SUM(s.clsbiz_stor_co)        AS clsbiz_stor_co
            FROM sangkwon_store s
            JOIN svc_induty_map m ON s.svc_induty_cd = m.svc_induty_cd
            WHERE s.adm_cd = %(cd)s
              AND s.base_yr_qtr_cd {qtr_cond}
            GROUP BY m.svc_cd, m.svc_nm
            ORDER BY stor_co DESC NULLS LAST
        """
        try:
            params = {"cd": adm_cd}
            if quarter:
                params["qtr"] = quarter
            result = self._query(sql, params)
            logger.info(f"[SangkwonStoreDAO] adm_cd={adm_cd} → {len(result)}개 업종")
            return result
        except Exception as e:
            logger.error(f"[SangkwonStoreDAO] getStoreBySvcCd 실패: {e}")
            return []

    def getStoreByInduty(
        self, adm_cd: str, svc_cd: str = "", quarter: str = ""
    ) -> list:
        """소분류(svc_induty_cd) 기준 점포수"""
        qtr_cond = "= %(qtr)s" if quarter else f"= {LATEST_QTR}"
        svc_cond = "AND m.svc_cd = %(svc)s" if svc_cd else ""
        sql = f"""
            SELECT
                s.svc_induty_cd,
                s.svc_induty_nm,
                s.stor_co,
                s.frc_stor_co,
                s.opbiz_rt,
                s.clsbiz_rt
            FROM sangkwon_store s
            JOIN svc_induty_map m ON s.svc_induty_cd = m.svc_induty_cd
            WHERE s.adm_cd = %(cd)s
              AND s.base_yr_qtr_cd {qtr_cond}
              {svc_cond}
            ORDER BY s.stor_co DESC NULLS LAST
        """
        try:
            params = {"cd": adm_cd}
            if quarter:
                params["qtr"] = quarter
            if svc_cd:
                params["svc"] = svc_cd
            return self._query(sql, params)
        except Exception as e:
            logger.error(f"[SangkwonStoreDAO] getStoreByInduty 실패: {e}")
            return []
