# 위치: p01_backEnd/DAO/dongMappingDAO.py
#
# 역할: VWorld WFS emd_cd(법정동 8자리) → SANGKWON_SALES 행정동_코드(10자리) 매핑
#
# 매핑 흐름:
#   WFS emd_cd (8자리)
#     → BUBJUNGDONG_CODE.EMD_CD → DONG_NM (법정동명)
#     → 법정동명 정규화 → sangkwon_df 행정동_코드_명 퍼지 매칭
#     → 행정동_코드(10자리), 행정동명
#
# DB 적재: create_bubjungdong.sql 실행 필요
#   DBeaver → 해당 DB → SQL 편집기 → create_bubjungdong.sql 실행
# ────────────────────────────────────────────────────────────────

import logging
import re
import pandas as pd
from typing import Optional

logger = logging.getLogger(__name__)

DB_INFO = "fable/1@//195.168.9.168:1521/xe"


class DongMappingDAO:
    """
    법정동코드(WFS) ↔ 행정동코드(SANGKWON_SALES) 매핑
    - 서버 시작 시 load() 호출 → 메모리 dict 캐시
    - get_adm_by_emd(emd_cd) → (행정동코드, 행정동명) 반환
    """

    def __init__(self):
        # emd_cd(8) → (bjdong_cd, gu_nm, dong_nm)
        self._emd_map: dict = {}
        # 행정동명 → (행정동코드, 행정동명) - sangkwonDAO df와 결합
        self._adm_map: dict = {}
        self._loaded = False

    def _db_con(self):
        from fable.oracleDBConnect import OracleDBConnect
        return OracleDBConnect.makeConCur(DB_INFO)

    # ════════════════════════════════════════════════════════════
    # 1. 로드
    # ════════════════════════════════════════════════════════════

    def load(self, sangkwon_df: pd.DataFrame = None):
        """
        서버 시작 시 호출
        - BUBJUNGDONG_CODE → emd_cd 매핑 dict
        - sangkwon_df 제공 시 → 행정동명 매핑 dict 추가 구성
        """
        self._load_bjd()
        if sangkwon_df is not None and not sangkwon_df.empty:
            self._build_adm_map(sangkwon_df)
        logger.info(f"[DongMappingDAO] 로드 완료: emd={len(self._emd_map)}, adm={len(self._adm_map)}")

    def _load_bjd(self):
        """BUBJUNGDONG_CODE 테이블 로드"""
        try:
            con, cur = self._db_con()
            try:
                cur.execute(
                    "SELECT EMD_CD, GU_NM, DONG_NM FROM BUBJUNGDONG_CODE"
                )
                for emd_cd, gu_nm, dong_nm in cur.fetchall():
                    self._emd_map[str(emd_cd)] = (str(gu_nm), str(dong_nm))
            finally:
                from fable.oracleDBConnect import OracleDBConnect
                OracleDBConnect.closeConCur(con, cur)
        except Exception as e:
            logger.error(f"[DongMappingDAO] DB 로드 실패: {e}")

    def _build_adm_map(self, df: pd.DataFrame):
        """
        sangkwon_df의 행정동명 → dict
        키: 정규화된 행정동명
        값: (행정동코드, 행정동명)
        """
        for _, row in df.iterrows():
            nm  = str(row.get("행정동_코드_명", ""))
            cd  = str(row.get("행정동_코드", ""))
            key = self._normalize(nm)
            self._adm_map[key] = (cd, nm)

    # ════════════════════════════════════════════════════════════
    # 2. 핵심 매핑 함수
    # ════════════════════════════════════════════════════════════

    def get_adm_by_emd(self, emd_cd: str) -> Optional[tuple]:
        """
        WFS emd_cd(8자리) → (행정동코드, 행정동명, 구명)
        반환 없으면 None
        """
        if not self._emd_map:
            return None
        entry = self._emd_map.get(str(emd_cd))
        if not entry:
            return None
        gu_nm, dong_nm = entry
        adm = self._match_adm(dong_nm, gu_nm)
        if adm:
            return (adm[0], adm[1], gu_nm)
        return None

    def get_adm_by_name(self, dong_nm: str, gu_nm: str = "") -> Optional[tuple]:
        """
        동명 + 구명 → (행정동코드, 행정동명)
        클릭 패널에서 직접 이름으로 조회 시 사용
        """
        return self._match_adm(dong_nm, gu_nm)

    def _match_adm(self, dong_nm: str, gu_nm: str = "") -> Optional[tuple]:
        """
        법정동명 → 행정동명 퍼지 매칭
        전략:
          1. 정규화 후 완전 일치
          2. 행정동명이 법정동명을 포함하는지 (예: 청운동 → 청운효자동)
          3. 법정동명 앞부분이 행정동명에 포함되는지
        """
        norm = self._normalize(dong_nm)

        # 1. 완전 일치
        if norm in self._adm_map:
            return self._adm_map[norm]

        # 구 코드 prefix로 후보 범위 좁히기
        GU_CODE = {
            "종로구":"11110","중구":"11140","용산구":"11170","성동구":"11200",
            "광진구":"11215","동대문구":"11230","중랑구":"11260","성북구":"11290",
            "강북구":"11305","도봉구":"11320","노원구":"11350","은평구":"11380",
            "서대문구":"11410","마포구":"11440","양천구":"11470","강서구":"11500",
            "구로구":"11530","금천구":"11545","영등포구":"11560","동작구":"11590",
            "관악구":"11620","서초구":"11650","강남구":"11680","송파구":"11710",
            "강동구":"11740",
        }
        gu_prefix = GU_CODE.get(gu_nm, "")
        candidates = {
            k: v for k, v in self._adm_map.items()
            if not gu_prefix or v[0].startswith(gu_prefix)
        }

        # 2. 법정동명이 행정동명에 포함 (청운동 → 청운효자동)
        root = re.sub(r'[0-9·\.가나다라마바사아자차카타파하]', '', norm).strip()
        if root:
            for k, v in candidates.items():
                if root in k:
                    return v

        # 3. 행정동명 앞부분이 법정동명에 포함 (종로1·2·3·4가동 → 종로1가)
        for k, v in candidates.items():
            k_root = re.sub(r'[0-9·\.가나다라마바사아자차카타파하]', '', k).strip()
            if k_root and k_root in norm:
                return v

        return None

    @staticmethod
    def _normalize(name: str) -> str:
        """행정동/법정동명 정규화: 공백제거, 가운뎃점 통일"""
        return name.strip().replace(" ", "").replace(".", "·")

    # ════════════════════════════════════════════════════════════
    # 3. WFS GeoJSON에 행정동코드 주입 (wfs-dong 엔드포인트용)
    # ════════════════════════════════════════════════════════════

    def enrich_geojson(self, geojson: dict) -> dict:
        """
        WFS GeoJSON features에 adm_cd, adm_nm 필드 추가
        프론트에서 feature.properties.adm_cd로 매출 데이터 즉시 lookup
        """
        matched = 0
        for feat in geojson.get("features", []):
            p = feat.get("properties", {})
            emd_cd = str(p.get("emd_cd", ""))
            gu_nm  = p.get("sig_kor_nm") or p.get("sig_nm") or ""
            result = self.get_adm_by_emd(emd_cd)
            if result:
                p["adm_cd"] = result[0]
                p["adm_nm"] = result[1]
                p["gu_nm"]  = result[2] or gu_nm
                matched += 1
            else:
                p["adm_cd"] = None
                p["adm_nm"] = None
                p["gu_nm"]  = gu_nm
        logger.info(f"[DongMappingDAO] enrich: {matched}/{len(geojson.get('features',[]))} 매칭")
        return geojson