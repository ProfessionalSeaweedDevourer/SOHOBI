import os

import psycopg2
from dotenv import load_dotenv

load_dotenv()


class DBWork:
    def _get_connection(self):
        return psycopg2.connect(
            host=os.getenv("PG_HOST"),
            port=int(os.getenv("PG_PORT", "5432")),
            dbname=os.getenv("PG_DB"),
            user=os.getenv("PG_USER"),
            password=os.getenv("PG_PASSWORD"),
            sslmode=os.getenv("PG_SSLMODE", "require"),
        )

    def get_sales(self, region, industry):
        try:
            con = self._get_connection()
            cur = con.cursor()

            if not region or not industry:
                return [170000000]

            placeholders = ",".join(["%s"] * len(region))
            sql = f"""
                SELECT tot_sales_amt
                FROM sangkwon_sales
                WHERE adm_cd IN ({placeholders})
                AND svc_induty_cd = %s
            """
            cur.execute(sql, region + [industry])
            return [amt for (amt,) in cur]

        except Exception as e:
            print("DB 조회 실패:", e)
            return [170000000]
        finally:
            if 'cur' in locals():
                cur.close()
            if 'con' in locals():
                con.close()

    def get_average_sales(self) -> float:
        try:
            con = self._get_connection()
            cur = con.cursor()
            cur.execute("SELECT ROUND(AVG(tot_sales_amt)) FROM sangkwon_sales WHERE svc_induty_cd LIKE 'CS10%'")
            # fetchone() 자체가 None이거나 AVG() 결과가 NULL인 경우 모두 fallback으로 처리
            row = cur.fetchone()
            avg = row[0] if row and row[0] is not None else None
            return [avg] if avg is not None else [170000000]
        except Exception as e:
            print("DB 평균 조회 실패:", e)
            return [170000000]
        finally:
            if 'cur' in locals():
                cur.close()
            if 'con' in locals():
                con.close()
