import logging

from db.dao.baseDAO import BaseDAO

logger = logging.getLogger(__name__)


class DBWork:
    """
    PostgreSQL 연결 및 상권 매출 데이터 조회 클래스.

    환경변수(PG_HOST, PG_PORT, PG_DB, PG_USER, PG_PASSWORD, PG_SSLMODE)로
    연결 정보를 관리하며, 조회 실패 시 fallback 값을 반환한다.
    """
    def _get_connection(self):
        """환경변수 기반 PostgreSQL 연결 객체를 반환한다."""
        return psycopg2.connect(
            host=os.getenv("PG_HOST"),
            port=int(os.getenv("PG_PORT", "5432")),
            dbname=os.getenv("PG_DB"),
            user=os.getenv("PG_USER"),
            password=os.getenv("PG_PASSWORD"),
            sslmode=os.getenv("PG_SSLMODE", "require"),
        )

    def _execute_query(self, sql: str, params: list = None):
        """
        SQL 쿼리를 실행하고 전체 결과를 반환한다.

        Args:
            sql: 실행할 SQL 문자열
            params: 바인딩 파라미터 리스트 (기본값: None)

        Returns:
            list[tuple]: 쿼리 결과 행 목록. 조회 실패 시 None 반환.
        """
        con, cur = None, None
        try:
            con = self._get_connection()
            cur = con.cursor()
            cur.execute(sql, params or [])
            return cur.fetchall()
        except Exception as e:
            print("DB 조회 실패:", e)
            return None
        finally:
            if cur: cur.close()
            if con: con.close()

    def get_sales(self, region, industry):
        """
        행정동 코드 및 업종 코드 기준 업장별 평균 월매출을 조회한다.

        sangkwon_store의 분기 평균 stor_co로 tot_sales_amt를 나눠
        단일 업장 매출을 산출한다. stor_co 매칭 불가 시 평균치로 fallback.

        Args:
            region: 행정동 코드 리스트 (예: ["11440660", "11440670"])
            industry: 서비스 업종 코드 (예: "CS100010")

        Returns:
            list[float]: 분기별 업장 평균 매출 리스트.
                         region/industry 미입력 또는 조회 결과 없을 시
                         get_average_sales() 반환값으로 대체.
        """
        if not region or not industry:
            return self.get_average_sales()

        placeholders = ",".join(["%s"] * len(region))
        sql = f"""
            SELECT
                ROUND(
                    s.tot_sales_amt::numeric
                    / NULLIF(
                        COALESCE(
                            (SELECT ROUND(AVG(st.stor_co))
                            FROM sangkwon_store st
                            WHERE st.adm_cd        = s.adm_cd
                            AND   st.svc_induty_cd = s.svc_induty_cd
                            AND   st.stor_co > 0),
                        1),
                    0)
                ) AS avg_sales_per_store
            FROM sangkwon_sales s
            WHERE s.adm_cd IN ({placeholders})
            AND   s.svc_induty_cd = %s
            AND   s.tot_sales_amt IS NOT NULL
        """
        rows = self._execute_query(sql, region + [industry])

        if not rows:
            return self.get_average_sales()

        results = [float(val) for (val,) in rows if val is not None]
        return results if results else self.get_average_sales()

    def get_average_sales(self) -> list:
        """
        CS10%(=FnB 업종) 업종 전체 기준 업장별 평균 월매출을 조회한다.

        sangkwon_store의 분기 평균 stor_co로 tot_sales_amt를 나눠
        단일 업장 매출을 산출 후 전체 평균을 반환한다.

        Returns:
            list[float]: 전체 평균 매출 단일값 리스트.
                         조회 실패 또는 NULL 반환 시 [float(46_000_000)] 반환.
        """
        sql = """
            SELECT
                ROUND(
                    AVG(
                        s.tot_sales_amt::numeric
                        / NULLIF(
                            COALESCE(
                                (SELECT ROUND(AVG(st.stor_co))
                                FROM sangkwon_store st
                                WHERE st.adm_cd        = s.adm_cd
                                AND   st.svc_induty_cd = s.svc_induty_cd
                                AND   st.stor_co > 0),
                            1),
                        0)
                    )
                )
            FROM sangkwon_sales s
            WHERE s.svc_induty_cd LIKE 'CS10%'
            AND   s.tot_sales_amt IS NOT NULL
        """
        conn, cur = self._db_con()
        try:
            cur.execute(sql)
            row = cur.fetchone()
            avg = row["avg_sales_per_store"] if row else None
            return [float(avg)] if avg is not None else [float(46_000_000)]
        except Exception as e:
            logger.warning("DBWork.get_average_sales 실패: %s", e)
            return [float(46_000_000)]
        finally:
            self._close(conn, cur)
