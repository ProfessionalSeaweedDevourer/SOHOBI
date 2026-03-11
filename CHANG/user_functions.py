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
