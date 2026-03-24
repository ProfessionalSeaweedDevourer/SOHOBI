import os
from dotenv import load_dotenv
from oracledb import connect
from difflib import get_close_matches

load_dotenv()

class DBWork:
    def __init__(self):
        # 세션 시작 시 업종 목록을 DB에서 한 번만 불러와 캐싱
        
        try:
            con = connect(os.getenv("DB_DSN"))
            cur = con.cursor()

            cur.execute("SELECT DISTINCT SVC_INDUTY_NM FROM SANGKWON_SALES")
            rows = cur.fetchall()
            self.industry_list = [row[0] for row in rows]

            cur.execute("SELECT DISTINCT ADM_NM FROM SANGKWON_SALES")
            rows = cur.fetchall()
            self.region_list = [row[0] for row in rows]

        finally:
            cur.close()
            con.close()

    def get_sales(self,region, industry):
        try:
            con = connect(os.getenv("DB_DSN"))
            cur = con.cursor()

            matches_industry = get_close_matches(industry, self.industry_list, n=1, cutoff=0.0)
            industry = matches_industry[0]
            matches_region = get_close_matches(region, self.region_list, n=1, cutoff=0.0)
            region = matches_region[0]
            # >> 추후 데이터에 따라 코드 사용 고려

            sql = """
                SELECT TOT_SALES_AMT
                FROM SANGKWON_SALES
                WHERE ADM_NM = :region
                AND SVC_INDUTY_NM = :industry
            """

            cur.execute(sql, {"region": region, "industry": industry})

            sales_list = [amt for (amt,) in cur]
            return sales_list

        except Exception as e:
            print(e)
            return {"result": "err"}
        finally:
            cur.close()
            con.close()

    def get_average_sales(self) -> float:
        try:
            con = connect(os.getenv("DB_DSN"))
            cur = con.cursor()
            cur.execute("SELECT AVG(TOT_SALES_AMT) FROM SANGKWON_SALES")
            (avg,) = cur.fetchone()
            return [avg]
        except Exception as e:
            print("DB 평균 조회 실패:", e)
            return None
        finally:
            if 'cur' in locals():
                cur.close()
            if 'con' in locals():
                con.close()


# 예정 : 기본값을 불러올 때 > 기존 정보(부모 에이전트가 넘겨주는)가 있으면 그 정보를 우선하는 기능 > 이 정보가 넘어오는 시점은 언제 어디인지? 지역은 코드로 넘길건지?(행정동-법정동이슈관련)
#        

if __name__ == "__main__":
    dbw = DBWork()

    result = dbw.get_sales("효창", "양식음식점")
    print("검색 결과:", result)
    result = dbw.get_average_sales()
    print("검색 결과:", result)

# 검색 결과: [301130046, 255637953, 227431883, 223551859, 176126286, 219825355, 171908319, 168178635, 272431538, 349692881, 256827441, 302105463, 288239621, 360002618, 242079213, 351627941, 290905228, 288516694, 189415725, 360682997, 301504600, 275036096, 210369798, 316022178, 195830394, 274107572, 252679561]
# 의도대로의 출력 확인