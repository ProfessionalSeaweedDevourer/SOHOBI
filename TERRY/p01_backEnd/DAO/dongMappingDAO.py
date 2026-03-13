# 위치: p01_backEnd/DAO/dongMappingDAO.py
#
# DB 테이블: ADMIN_DONG, LAW_DONG, V_SEOUL_DONG_MAP
# create_dong_tables.sql 실행 후 사용
#
# 역할:
#   1. load() → V_SEOUL_DONG_MAP을 메모리 dict 캐시
#   2. get_adm_by_emd(emd_cd) → 행정동코드/명 반환
#   3. enrich_geojson(gj) → WFS feature에 adm_cd, adm_nm, gu_nm 주입

import logging
from typing import Optional
from baseDAO import BaseDAO

logger = logging.getLogger(__name__)


class DongMappingDAO(BaseDAO):

    def __init__(self):
        self._emd: dict = {}
        self._loaded = False

    def load(self):
        """서버 시작 시 V_LAW_TO_ADM → 메모리 dict"""
        try:
            rows = self._query(
                "SELECT EMD_CD, GU_NM, LAW_NM, LAW_CD, ADM_CD, ADM_NM "
                "FROM V_LAW_TO_ADM"
            )
            for emd_cd, gu_nm, law_nm, law_cd, adm_cd, adm_nm in rows:
                key = str(emd_cd).strip()
                # emd_cd 1:N 이면 confidence 높은 순으로 이미 정렬된 첫 번째 유지
                if key not in self._emd:
                    self._emd[key] = {
                        'law_cd': str(law_cd).strip()  if law_cd  else None,
                        'adm_cd': str(adm_cd).strip()  if adm_cd  else None,
                        'adm_nm': str(adm_nm).strip()  if adm_nm  else None,
                        'gu_nm' : str(gu_nm).strip()   if gu_nm   else None,
                        'law_nm': str(law_nm).strip()   if law_nm  else None,
                    }
            self._loaded = True
            logger.info(f"[DongMappingDAO] 로드 완료: {len(self._emd)}개 법정동 매핑")
        except Exception as e:
            logger.error(f"[DongMappingDAO] 로드 실패: {e}")

    # ── 조회 ─────────────────────────────────────────────────────

    def get_adm_by_emd(self, emd_cd: str) -> Optional[dict]:
        """WFS emd_cd → {'adm_cd','adm_nm','gu_nm','law_nm'}"""
        return self._emd.get(str(emd_cd).strip())

    # ── WFS GeoJSON 보강 ─────────────────────────────────────────

    def enrich_geojson(self, geojson: dict) -> dict:
        """
        WFS feature.properties에 행정동 정보 주입
          adm_cd  : 행정동코드 (SANGKWON_SALES 매칭용)
          adm_nm  : 행정동명
          gu_nm   : 자치구명
          law_nm  : 원본 법정동명 (표시용)
        """
        features = geojson.get("features", [])
        matched = 0
        for feat in features:
            p = feat.get("properties", {})
            emd_cd = str(p.get("emd_cd", "")).strip()
            info   = self._emd.get(emd_cd)
            if info:
                p["adm_cd"] = info["adm_cd"]
                p["adm_nm"] = info["adm_nm"]
                p["gu_nm"]  = info["gu_nm"]
                p["law_nm"] = info["law_nm"]  # 원본 법정동명 보존
                matched += 1
            else:
                p["adm_cd"] = None
                p["adm_nm"] = None
                p["gu_nm"]  = p.get("sig_kor_nm") or p.get("sig_nm") or ""
                p["law_nm"] = p.get("emd_kor_nm") or ""
        logger.info(f"[DongMappingDAO] enrich: {matched}/{len(features)} 매칭")
        return geojson

    def status(self) -> dict:
        return {"loaded": self._loaded, "emd_count": len(self._emd)}