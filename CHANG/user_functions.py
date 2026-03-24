import random
import math
from semantic_kernel.functions import kernel_function


class FinanceSimulationSkill:
    def _calculate_salary(self, salary: float, hours: float | None = None) -> float:
        if hours is None:
            return salary
        else:
            return salary * hours

    @kernel_function(
        name="monte_carlo_simulation",
        description="월매출, 원가, 급여, 임대료, 관리비, 수수료를 고려한 몬테카를로 시뮬레이션"
    )
    def monte_carlo_simulation(
        self,
        revenue: list[float],
        cost: float,
        salary: float,
        hours: float | None = None,
        rent: float = 0,
        admin: float = 0,
        fee: float = 0,
    ) -> dict[str, float]:
        iterations = 10000
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

        if len(revenue) == 1:
            for _ in range(iterations):
                simulated_revenue = random.gauss(revenue[0], revenue[0] * 0.1)
                simulated_cost = random.gauss(cost, cost * 0.1)
                gross_profit = simulated_revenue - simulated_cost - salary_cost - rent - admin - fee
                results.append(gross_profit)
        else:
            for _ in range(iterations):
                simulated_revenue = random.choice(revenue)
                simulated_cost = random.gauss(cost, cost * 0.1)
                gross_profit = simulated_revenue - simulated_cost - salary_cost - rent - admin - fee
                results.append(gross_profit)

        avg_profit = sum(results) / iterations
        loss_probability = sum(1 for r in results if r < 0) / iterations

        return {
            "average_net_profit": avg_profit,
            "loss_probability": loss_probability
        }

    @kernel_function(
        name="investment_recovery",
        description="초기 투자비용 회수 가능성 평가"
    )
    def investment_recovery(self, initial_investment: float, avg_profit: float) -> dict[str, object]:
        if avg_profit <= 0:
            return {"recoverable": False, "months": None}
        return {"recoverable": True, "months": math.ceil(initial_investment / avg_profit)}


    def load_initial(self, region: str = None, industry: str = None) -> dict:
        base_revenue = 17000000
        revenue = None

        if region and industry:
            sales_list = self.dbwork.get_sales(region, industry)
            if isinstance(sales_list, list) and sales_list:
                revenue = sales_list

        if revenue is None:
            revenue = base_revenue

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
    # DB에서 매출 값만 불러오게됩니다, 해당 base_revenue는 카페 기준으로 추후 수정될 수 있습니다.
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



