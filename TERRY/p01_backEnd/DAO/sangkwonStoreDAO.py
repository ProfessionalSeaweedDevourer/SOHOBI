# 위치: p01_backEnd/DAO/sangkwonStoreDAO.py
#
# 역할:
#   SANGKWON_STORE 테이블 조회
#   행정동별 업종 점포수, 개폐업률 제공
#
# 테이블 구조:
#   BASE_YR_QTR_CD  - 기준 년분기 코드
#   ADM_CD          - 행정동 코드
#   SVC_INDUTY_CD   - 서비스 업종 코드 (CS100001 등)
#   STOR_CO         - 점포수
#   SIMILR_INDUTY_STOR_CO - 유사업종 점포수
#   OPBIZ_RT        - 개업률
#   OPBIZ_STOR_CO   - 개업수
#   CLSBIZ_RT       - 폐업률
#   CLSBIZ_STOR_CO  - 폐업수
#   FRC_STOR_CO     - 프랜차이즈 점포수

import logging
from .baseDAO import BaseDAO

logger = logging.getLogger(__name__)


class SangkwonStoreDAO(BaseDAO):

    def getStoreBySvcCd(self, adm_cd: str, quarter: str = "") -> list:
        """
        행정동 SVC_CD(대분류) 기준 점포수 합산
        - SVC_INDUTY_MAP JOIN → SVC_CD 그룹핑
        - quarter 없으면 최신 분기
        """
        qtr_cond = (
            "= :qtr"
            if quarter
            else "= (SELECT MAX(BASE_YR_QTR_CD) FROM SANGKWON_STORE)"
        )
        sql = f"""
            SELECT
                m.SVC_CD,
                m.SVC_NM,
                SUM(s.STOR_CO)               AS stor_co,
                SUM(s.SIMILR_INDUTY_STOR_CO) AS similr_stor_co,
                SUM(s.FRC_STOR_CO)           AS frc_stor_co,
                ROUND(AVG(s.OPBIZ_RT), 1)    AS opbiz_rt,
                SUM(s.OPBIZ_STOR_CO)         AS opbiz_stor_co,
                ROUND(AVG(s.CLSBIZ_RT), 1)   AS clsbiz_rt,
                SUM(s.CLSBIZ_STOR_CO)        AS clsbiz_stor_co
            FROM SANGKWON_STORE s
            JOIN SVC_INDUTY_MAP m ON s.SVC_INDUTY_CD = m.SVC_INDUTY_CD
            WHERE s.ADM_CD = :cd
              AND s.BASE_YR_QTR_CD {qtr_cond}
            GROUP BY m.SVC_CD, m.SVC_NM
            ORDER BY stor_co DESC NULLS LAST
        """
        try:
            params = {"cd": adm_cd}
            if quarter:
                params["qtr"] = quarter
            rows = self._query(sql, params)
            cols = [
                "svc_cd",
                "svc_nm",
                "stor_co",
                "similr_stor_co",
                "frc_stor_co",
                "opbiz_rt",
                "opbiz_stor_co",
                "clsbiz_rt",
                "clsbiz_stor_co",
            ]
            result = [dict(zip(cols, r)) for r in rows]
            logger.info(f"[SangkwonStoreDAO] adm_cd={adm_cd} → {len(result)}개 업종")
            return result
        except Exception as e:
            logger.error(f"[SangkwonStoreDAO] getStoreBySvcCd 실패: {e}")
            return []

    def getStoreByInduty(
        self, adm_cd: str, svc_cd: str = "", quarter: str = ""
    ) -> list:
        """
        행정동 소분류(SVC_INDUTY_CD) 기준 점포수
        - svc_cd 지정 시 해당 대분류만 필터
        """
        qtr_cond = (
            "= :qtr"
            if quarter
            else "= (SELECT MAX(BASE_YR_QTR_CD) FROM SANGKWON_STORE)"
        )
        svc_cond = "AND m.SVC_CD = :svc" if svc_cd else ""
        sql = f"""
            SELECT
                s.SVC_INDUTY_CD,
                s.SVC_INDUTY_NM,
                s.STOR_CO,
                s.FRC_STOR_CO,
                s.OPBIZ_RT,
                s.CLSBIZ_RT
            FROM SANGKWON_STORE s
            JOIN SVC_INDUTY_MAP m ON s.SVC_INDUTY_CD = m.SVC_INDUTY_CD
            WHERE s.ADM_CD = :cd
              AND s.BASE_YR_QTR_CD {qtr_cond}
              {svc_cond}
            ORDER BY s.STOR_CO DESC NULLS LAST
        """
        try:
            params = {"cd": adm_cd}
            if quarter:
                params["qtr"] = quarter
            if svc_cd:
                params["svc"] = svc_cd
            rows = self._query(sql, params)
            cols = [
                "svc_induty_cd",
                "svc_induty_nm",
                "stor_co",
                "frc_stor_co",
                "opbiz_rt",
                "clsbiz_rt",
            ]
            return [dict(zip(cols, r)) for r in rows]
        except Exception as e:
            logger.error(f"[SangkwonStoreDAO] getStoreByInduty 실패: {e}")
            return []
