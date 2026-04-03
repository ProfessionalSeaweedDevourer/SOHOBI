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
                return self.get_average_sales()

            placeholders = ",".join(["%s"] * len(region))
            sql = f"""
                SELECT
                    ROUND(
                        s.tot_sales_amt::numeric
                        / NULLIF(
                            COALESCE(
                                (SELECT st.stor_co
                                FROM sangkwon_store st
                                WHERE st.adm_cd         = s.adm_cd
                                AND   st.svc_induty_cd  = s.svc_induty_cd
                                AND   st.base_yr_qtr_cd = s.base_yr_qtr_cd
                                AND   st.stor_co > 0
                                LIMIT 1),
                            1),
                        0)
                    ) AS avg_sales_per_store
                FROM sangkwon_sales s
                WHERE s.adm_cd IN ({placeholders})
                AND   s.svc_induty_cd = %s
                AND   s.tot_sales_amt IS NOT NULL
            """
            cur.execute(sql, region + [industry])
            rows = cur.fetchall()

            if not rows:
                return self.get_average_sales()

            results = [float(val) for (val,) in rows if val is not None]
            return results if results else self.get_average_sales()

        except Exception as e:
            print("DB 조회 실패:", e)
            return [170_000_000]
        finally:
            if 'cur' in locals(): cur.close()
            if 'con' in locals(): con.close()
                    
    def get_average_sales(self) -> list:
        try:
            con = self._get_connection()
            cur = con.cursor()
            sql = """
                SELECT
                    ROUND(
                        AVG(
                            s.tot_sales_amt::numeric
                            / NULLIF(
                                COALESCE(
                                    (SELECT st.stor_co
                                    FROM sangkwon_store st
                                    WHERE st.adm_cd         = s.adm_cd
                                    AND   st.svc_induty_cd  = s.svc_induty_cd
                                    AND   st.base_yr_qtr_cd = s.base_yr_qtr_cd
                                    AND   st.stor_co > 0
                                    LIMIT 1),
                                1),
                            0)
                        )
                    )
                FROM sangkwon_sales s
                WHERE s.svc_induty_cd LIKE 'CS10%'
                AND   s.tot_sales_amt IS NOT NULL
            """
            cur.execute(sql)
            row = cur.fetchone()
            avg = row[0] if row and row[0] is not None else None
            return [float(avg)] if avg is not None else [170_000_000]

        except Exception as e:
            print("DB 평균 조회 실패:", e)
            return [170_000_000]
        finally:
            if 'cur' in locals(): cur.close()
            if 'con' in locals(): con.close()