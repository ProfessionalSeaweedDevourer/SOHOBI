# 위치: p01_backEnd/DAO/landmarkDAO.py
# 한국관광공사 랜드마크 DB 조회

import logging

try:
    from baseDAO import BaseDAO
except ImportError:
    from DAO.baseDAO import BaseDAO

logger = logging.getLogger(__name__)

TYPE_NAME = {"12": "관광지", "14": "문화시설", "15": "축제"}


class LandmarkDAO(BaseDAO):

    def get_by_adm_cd(self, adm_cd: str, content_types: list = None) -> list:
        """
        행정동 반경 내 랜드마크 조회
        adm_cd 기반으로 시군구코드 매핑 후 조회
        """
        # adm_cd 앞 5자리 = 시군구코드
        sgg_cd = adm_cd[:5] if adm_cd else None

        type_filter = ""
        params = []
        if content_types:
            placeholders = ",".join([f":{i+1}" for i in range(len(content_types))])
            type_filter = f"AND CONTENT_TYPE_ID IN ({placeholders})"
            params = content_types + ([sgg_cd] if sgg_cd else [])
        else:
            params = [sgg_cd] if sgg_cd else []

        sgg_param = f":{len(params)}"

        try:
            sql = f"""
                SELECT CONTENT_ID, CONTENT_TYPE_ID, TITLE,
                       ADDR1, MAP_X, MAP_Y, FIRST_IMAGE, TEL, HOMEPAGE
                FROM LANDMARK
                WHERE SIGUNGU_CODE = {sgg_param}
                {type_filter}
                ORDER BY TITLE
            """
            rows = self._query(sql, params)
            result = []
            for r in rows:
                result.append(
                    {
                        "content_id": r[0],
                        "content_type_id": r[1],
                        "type_name": TYPE_NAME.get(str(r[1]), "기타"),
                        "title": r[2],
                        "addr": r[3],
                        "lng": float(r[4]) if r[4] else None,
                        "lat": float(r[5]) if r[5] else None,
                        "image": r[6],
                        "tel": r[7],
                        "homepage": r[8],
                    }
                )
            logger.info(f"[LandmarkDAO] sgg_cd={sgg_cd} → {len(result)}건")
            return result
        except Exception as e:
            logger.error(f"[LandmarkDAO] get_by_adm_cd: {e}")
            return []

    def get_nearby(self, lat: float, lng: float, radius_km: float = 1.0) -> list:
        """좌표 기반 반경 조회"""
        try:
            sql = """
                SELECT CONTENT_ID, CONTENT_TYPE_ID, TITLE,
                       ADDR1, MAP_X, MAP_Y, FIRST_IMAGE, TEL,
                       SQRT(POWER((MAP_X - :1) * 88.74, 2) + POWER((MAP_Y - :2) * 111.32, 2)) AS DIST_KM
                FROM LANDMARK
                WHERE MAP_X IS NOT NULL AND MAP_Y IS NOT NULL
                  AND ABS(MAP_X - :1) < :3
                  AND ABS(MAP_Y - :2) < :3
                ORDER BY DIST_KM
            """
            rows = self._query(sql, [lng, lat, radius_km])
            result = []
            for r in rows:
                dist = float(r[8]) if r[8] else 999
                if dist <= radius_km:
                    result.append(
                        {
                            "content_id": r[0],
                            "content_type_id": r[1],
                            "type_name": TYPE_NAME.get(str(r[1]), "기타"),
                            "title": r[2],
                            "addr": r[3],
                            "lng": float(r[4]) if r[4] else None,
                            "lat": float(r[5]) if r[5] else None,
                            "image": r[6],
                            "tel": r[7],
                            "dist_km": round(dist, 3),
                        }
                    )
            logger.info(f"[LandmarkDAO] 반경 {radius_km}km → {len(result)}건")
            return result
        except Exception as e:
            logger.error(f"[LandmarkDAO] get_nearby: {e}")
            return []

    def get_all(self, content_types: list = None) -> list:
        """서울 전체 랜드마크 조회"""
        try:
            type_filter = ""
            params = []
            if content_types:
                placeholders = ",".join([f":{i+1}" for i in range(len(content_types))])
                type_filter = f"WHERE CONTENT_TYPE_ID IN ({placeholders})"
                params = content_types
            sql = f"""
                SELECT CONTENT_ID, CONTENT_TYPE_ID, TITLE,
                       ADDR1, MAP_X, MAP_Y, FIRST_IMAGE, TEL, HOMEPAGE
                FROM LANDMARK
                {type_filter}
                ORDER BY CONTENT_TYPE_ID, TITLE
            """
            rows = self._query(sql, params)
            result = [
                {
                    "content_id": r[0],
                    "content_type_id": r[1],
                    "type_name": TYPE_NAME.get(str(r[1]), "기타"),
                    "title": r[2],
                    "addr": r[3],
                    "lng": float(r[4]) if r[4] else None,
                    "lat": float(r[5]) if r[5] else None,
                    "image": r[6],
                    "tel": r[7],
                    "homepage": r[8],
                }
                for r in rows
            ]
            logger.info(f"[LandmarkDAO] get_all → {len(result)}건")
            return result
        except Exception as e:
            logger.error(f"[LandmarkDAO] get_all: {e}")
            return []

    def get_schools_by_sgg(self, sgg_nm: str, school_type: str = None) -> list:
        """시군구명 기준 학교 조회"""
        try:
            params = []
            where = []
            if sgg_nm:
                # SGG_NM 없음 → ROAD_ADDR에서 구이름 검색
                where.append("ROAD_ADDR LIKE '%' || :1 || '%'")
                params.append(sgg_nm)
            if school_type:
                where.append(f"SCHOOL_TYPE = :{len(params)+1}")
                params.append(school_type)
            where_clause = "WHERE " + " AND ".join(where) if where else ""
            sql = f"""
                SELECT SCHOOL_ID, SCHOOL_NM, SCHOOL_TYPE,
                       SGG_NM, ROAD_ADDR, MAP_X, MAP_Y, TEL, HOMEPAGE
                FROM SCHOOL_SEOUL
                {where_clause}
                ORDER BY SCHOOL_TYPE, SCHOOL_NM
            """
            rows = self._query(sql, params)
            return [
                {
                    "school_id": r[0],
                    "school_nm": r[1],
                    "school_type": r[2],
                    "sgg_nm": r[3],
                    "addr": r[4],
                    "lng": float(r[5]) if r[5] else None,
                    "lat": float(r[6]) if r[6] else None,
                    "tel": r[7],
                    "homepage": r[8],
                }
                for r in rows
            ]
        except Exception as e:
            logger.error(f"[LandmarkDAO] get_schools_by_sgg: {e}")
            return []
