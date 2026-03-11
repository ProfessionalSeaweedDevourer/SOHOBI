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
        tax_rate: float = 0.2,
    ) -> dict[str, float]:
        iterations = 10000
        results = []

        salary_cost = self._calculate_salary(salary, hours)

        if len(revenue) == 1:
            for _ in range(iterations):
                simulated_revenue = random.gauss(revenue[0], revenue[0] * 0.1)
                simulated_cost = random.gauss(cost, cost * 0.1)
                gross_profit = simulated_revenue - simulated_cost - salary_cost - rent - admin - fee
                net_profit = gross_profit * (1 - tax_rate)
                results.append(net_profit)
        else:
            for _ in range(iterations):
                simulated_revenue = random.choice(revenue)
                simulated_cost = random.gauss(cost, cost * 0.1)
                gross_profit = simulated_revenue - simulated_cost - salary_cost - rent - admin - fee
                net_profit = gross_profit * (1 - tax_rate)
                results.append(net_profit)

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


    # 누적 정보 반영을 위한 JSON 상태 관리용 함수 2종 추가
    def load_defaults(self) -> dict:
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



