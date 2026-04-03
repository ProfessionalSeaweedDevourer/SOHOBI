# 위치: SOHOBI/backend/DAO/dongMappingDAO.py
# PostgreSQL (Azure) 버전

import logging
from typing import Optional
from .baseDAO import BaseDAO

logger = logging.getLogger(__name__)


class DongMappingDAO(BaseDAO):

    def __init__(self):
        self._emd: dict = {}
        self._loaded = False

    def load(self):
        """law_adm_map → emd_cd(law_cd 앞8자리) → adm_cd 딕셔너리 캐시"""
        try:
            rows = self._query("""
                SELECT SUBSTRING(m.law_cd, 1, 8) AS emd_cd,
                       l.gu_nm, l.law_nm, m.law_cd, m.adm_cd, m.adm_nm
                FROM law_adm_map m
                JOIN law_dong_seoul l ON m.law_cd = l.law_cd
                ORDER BY SUBSTRING(m.law_cd, 1, 8), m.confidence DESC
            """)
            for r in rows:
                key = str(r["emd_cd"]).strip()
                if key not in self._emd:
                    self._emd[key] = {
                        "law_cd": r["law_cd"],
                        "adm_cd": r["adm_cd"],
                        "adm_nm": r["adm_nm"],
                        "gu_nm":  r["gu_nm"],
                        "law_nm": r["law_nm"],
                    }
            self._loaded = True
            logger.info(f"[DongMappingDAO] 로드 완료: {len(self._emd)}개 매핑")
        except Exception as e:
            logger.error(f"[DongMappingDAO] 로드 실패: {e}")

    def get_adm_by_emd(self, emd_cd: str) -> Optional[dict]:
        return self._emd.get(str(emd_cd).strip())

    def enrich_geojson(self, geojson: dict) -> dict:
        matched = 0
        for feat in geojson.get("features", []):
            p = feat.get("properties", {})
            emd_cd = str(p.get("emd_cd", "")).strip()
            full = p.get("full_nm", "").strip()
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