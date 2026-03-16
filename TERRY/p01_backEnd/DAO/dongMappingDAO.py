# 위치: p01_backEnd/DAO/dongMappingDAO.py
#
# 역할:
#   1. load() → LAW_ADM_MAP에서 SUBSTR(LAW_CD,1,8)=emd_cd → adm_cd 딕셔너리 캐시
#   2. enrich_geojson() → lt_c_ademd_info feature에 adm_cd, gu_nm 주입

import logging
from typing import Optional
from .baseDAO import BaseDAO

logger = logging.getLogger(__name__)


class DongMappingDAO(BaseDAO):

    def __init__(self):
        self._emd: dict = {}
        self._loaded = False

    def load(self):
        """
        LAW_ADM_MAP → emd_cd(SUBSTR(LAW_CD,1,8)) → adm_cd 딕셔너리
        별도 컬럼 추가 없이 기존 테이블 그대로 사용
        """
        try:
            rows = self._query(
                "SELECT SUBSTR(M.LAW_CD,1,8) AS EMD_CD, "
                "       L.GU_NM, L.LAW_NM, M.LAW_CD, M.ADM_CD, M.ADM_NM "
                "FROM LAW_ADM_MAP M "
                "JOIN LAW_DONG_SEOUL L ON M.LAW_CD = L.LAW_CD "
                "ORDER BY SUBSTR(M.LAW_CD,1,8), M.CONFIDENCE DESC"
            )
            for emd_cd, gu_nm, law_nm, law_cd, adm_cd, adm_nm in rows:
                key = str(emd_cd).strip()
                if key not in self._emd:  # confidence 내림차순이므로 첫 번째가 최고값
                    self._emd[key] = {
                        "law_cd": str(law_cd).strip() if law_cd else None,
                        "adm_cd": str(adm_cd).strip() if adm_cd else None,
                        "adm_nm": str(adm_nm).strip() if adm_nm else None,
                        "gu_nm": str(gu_nm).strip() if gu_nm else None,
                        "law_nm": str(law_nm).strip() if law_nm else None,
                    }
            self._loaded = True
            logger.info(f"[DongMappingDAO] 로드 완료: {len(self._emd)}개 매핑")
        except Exception as e:
            logger.error(f"[DongMappingDAO] 로드 실패: {e}")

    def get_adm_by_emd(self, emd_cd: str) -> Optional[dict]:
        return self._emd.get(str(emd_cd).strip())

    def enrich_geojson(self, geojson: dict) -> dict:
        """
        lt_c_ademd_info feature에 adm_cd, gu_nm 주입
          - emd_cd → LAW_ADM_MAP → adm_cd
          - full_nm → gu_nm 파싱
        """
        matched = 0
        for feat in geojson.get("features", []):
            p = feat.get("properties", {})
            emd_cd = str(p.get("emd_cd", "")).strip()
            full = p.get("full_nm", "").strip()

            # gu_nm: "서울특별시 종로구 청운동" → "종로구"
            parts = full.split()
            p["gu_nm"] = parts[1] if len(parts) > 1 else ""

            info = self._emd.get(emd_cd)
            if info:
                p["adm_cd"] = info["adm_cd"]
                p["adm_nm"] = info["adm_nm"]
                matched += 1
            else:
                p["adm_cd"] = None
                p["adm_nm"] = None

        total = len(geojson.get("features", []))
        logger.info(f"[DongMappingDAO] enrich: {matched}/{total} 매칭")
        return geojson
