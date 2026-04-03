# 위치: p01_backEnd/DAO/landmarkDAO.py
# PostgreSQL (Azure) 버전

import logging
try:
    from baseDAO import BaseDAO
except ImportError:
    from DAO.baseDAO import BaseDAO

logger = logging.getLogger(__name__)

TYPE_NAME = {"12": "관광지", "14": "문화시설", "15": "축제"}

SELECT_LANDMARK = """
    SELECT content_id, content_type_id, title,
           addr1, map_x, map_y, first_image, tel, homepage
"""

def _clean(v):
    """NULL 문자열/빈값 → None"""
    if v is None:
        return None
    if isinstance(v, str) and v.strip().upper() in ("NULL", ""):
        return None
    return v


def _row_to_dict(r: dict) -> dict:
    return {k: v for k, v in {
        "content_id":      _clean(r["content_id"]),
        "content_type_id": _clean(r["content_type_id"]),
        "type_name":       TYPE_NAME.get(str(r["content_type_id"]), "기타"),
        "title":           _clean(r["title"]),
        "addr":            _clean(r["addr1"]),
        "lng":             float(r["map_x"]) if r["map_x"] else None,
        "lat":             float(r["map_y"]) if r["map_y"] else None,
        "image":           _clean(r["first_image"]),
        "tel":             _clean(r["tel"]),
        "homepage":        _clean(r["homepage"]),
    }.items() if v is not None}


class LandmarkDAO(BaseDAO):

    def get_by_adm_cd(self, adm_cd: str, content_types: list = None) -> list:
        """행정동코드 → 시군구코드(앞5자리) 기준 랜드마크 조회"""
        sgg_cd = adm_cd[:5] if adm_cd else None
        if not sgg_cd:
            return []
        try:
            if content_types:
                placeholders = ",".join([f"%(t{i})s" for i in range(len(content_types))])
                params = {f"t{i}": v for i, v in enumerate(content_types)}
                params["sgg_cd"] = sgg_cd
                sql = f"""
                    {SELECT_LANDMARK}
                    FROM landmark
                    WHERE sigungu_code = %(sgg_cd)s
                      AND content_type_id IN ({placeholders})
                    ORDER BY title
                """
            else:
                sql = f"""
                    {SELECT_LANDMARK}
                    FROM landmark
                    WHERE sigungu_code = %(sgg_cd)s
                    ORDER BY title
                """
                params = {"sgg_cd": sgg_cd}

            rows = self._query(sql, params)
            result = [_row_to_dict(r) for r in rows]
            logger.info(f"[LandmarkDAO] sgg_cd={sgg_cd} → {len(result)}건")
            return result
        except Exception as e:
            logger.error(f"[LandmarkDAO] get_by_adm_cd: {e}")
            return []

    def get_all(self, content_types: list = None) -> list:
        """서울 전체 랜드마크 조회"""
        try:
            if content_types:
                # content_type_id는 varchar → 문자열로 캐스트
                placeholders = ",".join([f"%(t{i})s" for i in range(len(content_types))])
                params = {f"t{i}": str(v) for i, v in enumerate(content_types)}
                sql = f"""
                    {SELECT_LANDMARK}
                    FROM landmark
                    WHERE content_type_id IN ({placeholders})
                    ORDER BY content_type_id, title
                """
            else:
                sql = f"""
                    {SELECT_LANDMARK}
                    FROM landmark
                    ORDER BY content_type_id, title
                """
                params = {}

            rows = self._query(sql, params)
            result = [_row_to_dict(r) for r in rows]
            logger.info(f"[LandmarkDAO] get_all → {len(result)}건")
            return result
        except Exception as e:
            logger.error(f"[LandmarkDAO] get_all: {e}")
            return []

    def get_schools(self, school_type: str = None) -> list:
        """서울 전체 학교 조회 (좌표 있는 것만)"""
        try:
            if school_type:
                sql = """
                    SELECT sd_schul_code, schul_nm, schul_knd_sc_nm,
                           lctn_sc_nm, org_rdnma, org_rdnda, map_x, map_y,
                           org_telno, hmpg_adres, fond_sc_nm,
                           atpt_ofcdc_sc_nm, fond_ymd, foas_memrd,
                           coedu_sc_nm, dght_sc_nm
                    FROM school_seoul
                    WHERE map_x IS NOT NULL AND map_y IS NOT NULL
                      AND schul_knd_sc_nm = %(school_type)s
                    ORDER BY schul_knd_sc_nm, schul_nm
                """
                params = {"school_type": school_type}
            else:
                sql = """
                    SELECT sd_schul_code, schul_nm, schul_knd_sc_nm,
                           lctn_sc_nm, org_rdnma, org_rdnda, map_x, map_y,
                           org_telno, hmpg_adres, fond_sc_nm,
                           atpt_ofcdc_sc_nm, fond_ymd, foas_memrd,
                           coedu_sc_nm, dght_sc_nm
                    FROM school_seoul
                    WHERE map_x IS NOT NULL AND map_y IS NOT NULL
                    ORDER BY schul_knd_sc_nm, schul_nm
                """
                params = {}

            rows = self._query(sql, params)
            logger.info(f"[LandmarkDAO] get_schools → {len(rows)}건")
            return [{
                "school_id":   r["sd_schul_code"],
                "school_nm":   r["schul_nm"],
                "school_type": r["schul_knd_sc_nm"],
                "sido_nm":     r["lctn_sc_nm"],
                "addr":        r["org_rdnma"],
                "addr2":       r["org_rdnda"],
                "lng":         float(r["map_x"]) if r["map_x"] else None,
                "lat":         float(r["map_y"]) if r["map_y"] else None,
                "tel":         r["org_telno"],
                "homepage":    r["hmpg_adres"],
                "found_type":  r["fond_sc_nm"],
                "edu_office":  r["atpt_ofcdc_sc_nm"],
                "found_date":  r["fond_ymd"],
                "anniversary": r["foas_memrd"],
                "coedu":       r["coedu_sc_nm"],
                "day_night":   r["dght_sc_nm"],
            } for r in rows]
        except Exception as e:
            logger.error(f"[LandmarkDAO] get_schools: {e}")
            return []