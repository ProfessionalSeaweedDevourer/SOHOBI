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
            return [17000000]
        placeholders = ",".join(["%s"] * len(region))
        sql = (
            f"SELECT tot_sales_amt FROM sangkwon_sales"
            f" WHERE adm_cd IN ({placeholders}) AND svc_induty_cd = %s"
        )
        conn, cur = self._db_con()
        try:
            cur.execute(sql, region + [industry])
            rows = cur.fetchall()
            return [row["tot_sales_amt"] for row in rows] if rows else [17000000]
        except Exception as e:
            logger.warning(
                "DBWork.get_sales 실패 region=%s industry=%s: %s", region, industry, e
            )
            return [17000000]
        finally:
            self._close(conn, cur)

    def get_average_sales(self) -> list:
        sql = (
            "SELECT ROUND(AVG(tot_sales_amt)) AS avg"
            " FROM sangkwon_sales WHERE svc_induty_cd LIKE 'CS10%'"
        )
        conn, cur = self._db_con()
        try:
            cur.execute(sql)
            row = cur.fetchone()
            return [row["avg"]] if row and row["avg"] is not None else [170000000]
        except Exception as e:
            logger.warning("DBWork.get_average_sales 실패: %s", e)
            return [170000000]
        finally:
            self._close(conn, cur)
