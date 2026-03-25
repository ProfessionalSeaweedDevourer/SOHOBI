# 위치: p01_backEnd/DAO/baseDAO.py
# 모든 DAO가 상속 - DB 연결/해제 공통 처리

from .fable.oracleDBConnect import OracleDBConnect


class BaseDAO:

    def _db_con(self):
        return OracleDBConnect.makeConCur()

    def _close(self, con, cur):
        OracleDBConnect.closeConCur(con, cur)

    def _query(self, sql: str, params=None) -> list:
        """단순 SELECT → rows 반환"""
        con, cur = self._db_con()
        try:
            cur.execute(sql, params or [])
            return cur.fetchall()
        finally:
            self._close(con, cur)

    def _execute(self, sql: str, params=None) -> int:
        """INSERT/UPDATE/DELETE → rowcount 반환"""
        con, cur = self._db_con()
        try:
            cur.execute(sql, params or [])
            cnt = cur.rowcount
            con.commit()
            return cnt
        finally:
            self._close(con, cur)
