import logging

from db.dao.baseDAO import BaseDAO

logger = logging.getLogger(__name__)


class DBWork(BaseDAO):
    """
    재무 시뮬레이션용 DB 조회 클래스.
    baseDAO._pool(ThreadedConnectionPool)을 공유하여
    매 호출마다 raw 커넥션을 생성하는 문제를 해결한다.
    """

    def get_sales(self, region: list, industry: str) -> list:
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
        conn, cur = self._db_con()
        try:
            cur.execute(sql, region + [industry])
            rows = cur.fetchall()
            if not rows:
                return self.get_average_sales()
            results = [float(r["avg_sales_per_store"]) for r in rows if r["avg_sales_per_store"] is not None]
            return results if results else self.get_average_sales()
        except Exception as e:
            logger.warning(
                "DBWork.get_sales 실패 region=%s industry=%s: %s", region, industry, e
            )
            return [170_000_000]
        finally:
            self._close(conn, cur)

    def get_average_sales(self) -> list:
        """
        CS10%(=FnB 업종) 업종 전체 기준 업장별 평균 월매출을 조회한다.

        sangkwon_store의 분기 평균 stor_co로 tot_sales_amt를 나눠
        단일 업장 매출을 산출 후 전체 평균을 반환한다.

        Returns:
            list[float]: 전체 평균 매출 단일값 리스트.
                         조회 실패 또는 NULL 반환 시 [170_000_000] 반환.
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
                ) AS avg_sales_per_store
            FROM sangkwon_sales s
            WHERE s.svc_induty_cd LIKE 'CS10%'
            AND   s.tot_sales_amt IS NOT NULL
        """
        conn, cur = self._db_con()
        try:
            cur.execute(sql)
            row = cur.fetchone()
            avg = row["avg_sales_per_store"] if row else None
            return [float(avg)] if avg is not None else [170_000_000]
        except Exception as e:
            logger.warning("DBWork.get_average_sales 실패: %s", e)
            return [170_000_000]
        finally:
            self._close(conn, cur)
