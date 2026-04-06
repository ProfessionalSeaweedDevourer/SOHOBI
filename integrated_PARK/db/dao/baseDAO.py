# 위치: backend/DAO/baseDAO.py
# PostgreSQL (Azure) 버전 - psycopg2 기반

import os
import logging
import psycopg2
import psycopg2.pool
import psycopg2.extras

logger = logging.getLogger(__name__)

# ── 연결 풀 (모듈 레벨 싱글톤) ──────────────────────────────────
_pool: psycopg2.pool.ThreadedConnectionPool | None = None


def _get_pool() -> psycopg2.pool.ThreadedConnectionPool:
    global _pool
    if _pool is None:
        _pool = psycopg2.pool.ThreadedConnectionPool(
            minconn=2,
            maxconn=10,
            host=os.environ["PG_HOST"],
            port=int(os.environ.get("PG_PORT", 5432)),
            dbname=os.environ["PG_DB"],
            user=os.environ["PG_USER"],
            password=os.environ["PG_PASSWORD"],
            sslmode=os.environ.get("PG_SSL_MODE", "require"),
            connect_timeout=10,
            options="-c statement_timeout=15000",
        )
        logger.info("[BaseDAO] PostgreSQL 연결 풀 생성 완료")
    return _pool


class BaseDAO:

    def _db_con(self):
        """풀에서 커넥션 획득 → (conn, cursor) 반환"""
        conn = _get_pool().getconn()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        return conn, cur

    def _close(self, conn, cur):
        """커서 닫고 커넥션 반납"""
        try:
            cur.close()
        except Exception as e:
            logger.warning("[BaseDAO] 커서 닫기 실패: %s", e)
        try:
            _get_pool().putconn(conn)
        except Exception as e:
            logger.warning("[BaseDAO] 커넥션 풀 반납 실패 — 누수 가능성: %s", e)

    def _query(self, sql: str, params: dict | None = None) -> list:
        """SELECT → list[dict] 반환 (RealDictCursor 사용)"""
        conn, cur = self._db_con()
        try:
            cur.execute(sql, params or {})
            rows = cur.fetchall()
            return [dict(r) for r in rows]
        finally:
            self._close(conn, cur)

    def _execute(self, sql: str, params: dict | None = None) -> int:
        """INSERT/UPDATE/DELETE → rowcount 반환"""
        conn, cur = self._db_con()
        try:
            cur.execute(sql, params or {})
            cnt = cur.rowcount
            conn.commit()
            return cnt
        except Exception:
            conn.rollback()
            raise
        finally:
            self._close(conn, cur)