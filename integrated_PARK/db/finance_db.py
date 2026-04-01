import os
from dotenv import load_dotenv
from oracledb import connect

load_dotenv()  # .env 파일 로드

class DBWork:
    def _get_connection(self):
        return connect(
            user=os.getenv("ORACLE_USER"),
            password=os.getenv("ORACLE_PASSWORD"),
            host=os.getenv("ORACLE_HOST"),
            port=int(os.getenv("ORACLE_PORT", "1521")),
            sid=os.getenv("ORACLE_SID"),
        )

    def get_sales(self, region, industry):
        try:
            con = self._get_connection()
            cur = con.cursor()

            region = "%" if region is None else region
            industry = "%" if industry is None else industry

            sql = """
                SELECT TOT_SALES_AMT
                FROM SANGKWON_SALES
                WHERE ADM_CD LIKE :region
                AND SVC_INDUTY_CD LIKE :industry
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
            cur.execute("SELECT AVG(TOT_SALES_AMT) FROM SANGKWON_SALES")
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
