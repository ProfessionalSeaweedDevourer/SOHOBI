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
