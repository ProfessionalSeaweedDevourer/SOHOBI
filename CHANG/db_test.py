def load_defaults() -> dict:
    """
    모든 변수에 평균치 또는 None 기본값을 부여한 초기 JSON 반환
    """
    return {
        "revenue": 17000000,
        "cost": 6120000,
        "salary": 3400000,
        "hours": None,
        "rent": 2550000,
        "admin": 510000,
        "fee": 510000,
        "initial_investment": None
    }
# 카페-평균치 기준 기본값, 해당 값을 DB 등을 불러오는 형태로 추후 업데이트 상정중



from oracledb import connect
from difflib import get_close_matches
class DBWork:
    def __init__(self):
        # 세션 시작 시 업종 목록을 DB에서 한 번만 불러와 캐싱
        try:
            con = connect("fable/1@//195.168.9.5:1521/xe")
            cur = con.cursor()
            cur.execute("SELECT DISTINCT SVC_INDUTY_NM FROM SANGKWON_SALES")
            rows = cur.fetchall()
            self.industry_list = [row[0] for row in rows]
        finally:
            cur.close()
            con.close()

    def get_sales(self,region, industry):
        try:
            con = connect("fable/1@//195.168.9.5:1521/xe")
            cur = con.cursor()

            # 사직 > 사직동 등 걸리게
            region = region + "%"
            matches = get_close_matches(industry, self.industry_list, n=1, cutoff=0.0)
            industry = matches[0] if matches else industry
            # >> 추후 데이터에 따라 코드 사용 고려
            sql = (
                "SELECT TOT_SALES_AMT "
                "FROM SANGKWON_SALES "
                "WHERE ADM_NM LIKE '%s' "
                "AND SVC_INDUTY_NM = '%s'"
                % (region, industry)
            )

            cur.execute(sql)

            sales_list = []
            for (amt,) in cur:
                sales_list.append(amt)

            return sales_list

        except Exception as e:
            print(e)
            return {"result": "err"}
        finally:
            cur.close()
            con.close()



# 예정 : 기본값을 불러올 때 > 기존 정보(부모 에이전트가 넘겨주는)가 있으면 그 정보를 우선하는 기능 > 이 정보가 넘어오는 시점은 언제 어디인지? 지역은 코드로 넘길건지?(행정동-법정동이슈관련)
#        

if __name__ == "__main__":
    dbw = DBWork()

    result = dbw.get_sales("사직", "카페")
    print("검색 결과:", result)

