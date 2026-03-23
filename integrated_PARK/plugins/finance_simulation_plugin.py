"""
재무 시뮬레이션 플러그인
출처: CHANG/user_functions.py — FinanceSimulationSkill
"""

import math
import random
from semantic_kernel.functions import kernel_function


class FinanceSimulationPlugin:
    """몬테카를로 시뮬레이션 기반 재무 분석 플러그인"""
    # def __init__(self):
        # self.dbwork = DBWork()

    def _calculate_salary(self, salary: float, hours: float = None) -> float:
        return salary if hours is None else salary * hours

    @kernel_function(
        name="monte_carlo_simulation",
        description=(
            "월매출, 원가, 급여, 임대료, 관리비, 수수료를 입력받아 "
            "10,000회 몬테카를로 시뮬레이션으로 평균 순이익과 손실 확률을 계산합니다. "
            "revenue는 [단일값] 또는 [임의의 복수 값] 형태의 숫자 목록(원 단위)입니다."
        ),
    )
    def monte_carlo_simulation(
        self,
        revenue: list[float],
        cost: float | None = None,
        salary: float | None = None,
        hours: float | None = None,
        rent: float | None = None,
        admin: float | None = None,
        fee: float | None = None,
    ) -> dict:
        iterations = 10_000
        results = []

        avg_sales = sum(revenue) / len(revenue)
        if cost is None:
            cost = avg_sales * 0.36
        if salary is None:
            salary = avg_sales * 0.20
        if rent is None:
            rent = avg_sales * 0.15
        if admin is None:
            admin = avg_sales * 0.03
        if fee is None:
            fee = avg_sales * 0.03
        # None 값만 % 기반 연산, 추후 업종 별 % list 고려중(현재 카페 기준)

        salary_cost = self._calculate_salary(salary, hours)
        # 시급 관련 연산

        if len(revenue) == 1:
            for _ in range(iterations):
                sim_rev = random.gauss(revenue[0], revenue[0] * 0.1)
                sim_cost = random.gauss(cost, cost * 0.1)
                net = sim_rev - sim_cost - salary_cost - rent - admin - fee
                results.append(net)
        else:
            for _ in range(iterations):
                sim_rev = random.choice(revenue)* random.gauss(1.0, 0.1)
                sim_cost = random.gauss(cost, cost * 0.1)
                net = sim_rev - sim_cost - salary_cost - rent - admin - fee
                results.append(net)

        avg = sum(results) / iterations
        loss_prob = sum(1 for r in results if r < 0) / iterations
        
        sorted_results = sorted(results)
        loss_results = [r for r in results if r < 0]
        avg_loss = round(sum(loss_results) / len(loss_results)) if loss_results else 0

        p20 = sorted_results[int(iterations * 0.20)]

        return {
            "average_net_profit": round(avg),
            "loss_probability":   round(loss_prob, 4),
            "avg_loss_amount":    avg_loss,
            "p20":                round(p20),
            "actual_cost":        round(cost),      # 결과값 세분화용 변수 추가
            "actual_salary":      round(salary_cost),  # 결과값 세분화용 변수 추가
            "actual_rent":        round(rent),      # 결과값 세분화용 변수 추가
            "actual_admin":       round(admin),     # 결과값 세분화용 변수 추가
            "actual_fee":         round(fee),       # 결과값 세분화용 변수 추가
        }

    @kernel_function(
        name="investment_recovery",
        description=(
            "초기 투자비용과 월 평균 순이익을 입력받아 "
            "투자금 회수 가능 여부와 예상 회수 기간(개월)을 반환합니다."
        ),
    )
    def investment_recovery(self, initial_investment: float, avg_profit: float) -> dict:
        if avg_profit <= 0:
            return {"recoverable": False, "months": None}
        months = math.ceil(initial_investment / avg_profit)
        return {"recoverable": True, "months": months}

    # 누적 정보 반영을 위한 JSON 상태 관리용
    def load_initial(self, region: str = None, industry: str = None) -> dict:
        # if region is None and industry is None:
        #     # 지역/업종 입력 없는 경우 전체 평균
        #     revenue = self.dbwork.get_average_sales()
        # else:
        #     # 하나라도 있으면 리스트 반환
        #     sales_list = self.dbwork.get_sales(region, industry)
        #     revenue = sales_list
        
        # DB 제외용 단순초기값
        revenue = [14000000]

        return {
            "revenue": revenue,
            "cost": None,
            "salary": None,
            "hours": None,
            "rent": None,
            "admin": None,
            "fee": None,
            "initial_investment": None
        }
    # DB에서 매출 값만 불러오게됩니다(.dbwork.get_sales(region, industry))
    # base_revenue는 카페 기준으로 추후 수정될 수 있습니다.(industry 기반 평균치)
    # region and industry의 경우 부모 에이전트에게서 받을 임시 정보입니다(지역 및 업종). 필요 시 변수 명 및 구조 수정.

    def merge_json(self, previous: dict, current: dict) -> dict:
        """
        기존 JSON(previous)에 새 입력(current)을 병합.
        current에 값이 있으면 덮어쓰고, 없으면 previous 유지.
        """
        merged = previous.copy()
        for key, value in current.items():
            if value is not None:
                merged[key] = value
        return merged



## DB파트 로컬기준 정상 작동되는것 확인하였으나 우선 주석처리 해둡니다(처리방안 고민중)

# # 아래 class를 따로 파일분리하는 방안 혹은 상권분석쪽과 기준을 맞추는 방안도 고려중, 우선 같은 파일에 작엄.
# import os
# from dotenv import load_dotenv
# from oracledb import connect
# from difflib import get_close_matches

# load_dotenv()  # .env 파일 로드

# class DBWork:
#     def __init__(self):
#         self.industry_list = []
#         self.region_list = []
#         try:
#             con = self._get_connection()
#             cur = con.cursor()

#             cur.execute("SELECT DISTINCT SVC_INDUTY_NM FROM SANGKWON_SALES")
#             rows = cur.fetchall()
#             self.industry_list = [row[0] for row in rows]

#             cur.execute("SELECT DISTINCT ADM_NM FROM SANGKWON_SALES")
#             rows = cur.fetchall()
#             self.region_list = [row[0] for row in rows]
#             print(self.industry_list[0], self.region_list[0])
#         except Exception as e:
#             print(f"DBWork 초기화 실패 (리스트 비어있음): {e}")
#         finally:
#             if 'cur' in locals():
#                 cur.close()
#             if 'con' in locals():
#                 con.close()

#     def _get_connection(self):
#         dsn = os.getenv("DB_DSN")
#         return connect(dsn)

#     def get_sales(self, region, industry):
#         try:
#             con = self._get_connection()
#             cur = con.cursor()

#             # 해당 매칭 지금은 문자열 기반인데, 이후 벡터 임베딩 + LLM 선택 고려중
#             # but 넘겨받는 두 요소에 따라 달라질 수 있음
#             region = "%" if region is None else get_close_matches(region, self.region_list, n=1, cutoff=0.0)[0]
#             industry = "%" if industry is None else get_close_matches(industry, self.industry_list, n=1, cutoff=0.0)[0]

#             sql = """
#                 SELECT TOT_SALES_AMT
#                 FROM SANGKWON_SALES
#                 WHERE ADM_NM LIKE :region
#                 AND SVC_INDUTY_NM LIKE :industry
#             """
#             cur.execute(sql, {"region": region, "industry": industry})
#             return [amt for (amt,) in cur]

#         except Exception as e:
#             print("DB 조회 실패:", e)
#             return [17000000]
#         finally:
#             if 'cur' in locals():
#                 cur.close()
#             if 'con' in locals():
#                 con.close()

#     def get_average_sales(self) -> float:
#         try:
#             con = self._get_connection()
#             cur = con.cursor()
#             cur.execute("SELECT AVG(TOT_SALES_AMT) FROM SANGKWON_SALES")
#             (avg,) = cur.fetchone()
#             return [avg]
#         except Exception as e:
#             print("DB 평균 조회 실패:", e)
#             return [17000000]
#         finally:
#             if 'cur' in locals():
#                 cur.close()
#             if 'con' in locals():
#                 con.close()
