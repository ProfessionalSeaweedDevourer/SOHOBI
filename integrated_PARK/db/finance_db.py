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

            region = "%" if region is None else region
            industry = "%" if industry is None else industry

            sql = """
                SELECT tot_sales_amt
                FROM sangkwon_sales
                WHERE adm_cd LIKE %(region)s
                AND svc_induty_cd LIKE %(industry)s
            """
            cur.execute(sql, {"region": region, "industry": industry})
            return [amt for (amt,) in cur]

        except Exception as e:
            print("DB 조회 실패:", e)
            return [17000000]
        finally:
            if 'cur' in locals():
                cur.close()
            if 'con' in locals():
                con.close()

    def get_average_sales(self) -> float:
        try:
            con = self._get_connection()
            cur = con.cursor()
            cur.execute("SELECT AVG(tot_sales_amt) FROM sangkwon_sales")
            (avg,) = cur.fetchone()
            return [avg]
        except Exception as e:
            print("DB 평균 조회 실패:", e)
            return [17000000]
        finally:
            if 'cur' in locals():
                cur.close()
            if 'con' in locals():
                con.close()
