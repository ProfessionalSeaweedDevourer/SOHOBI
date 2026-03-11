"""
재무 시뮬레이션 플러그인
출처: CHANG/user_functions.py — FinanceSimulationSkill
"""

import math
import random
from semantic_kernel.functions import kernel_function


class FinanceSimulationPlugin:
    """몬테카를로 시뮬레이션 기반 재무 분석 플러그인"""

    def _calculate_salary(self, salary: float, hours: float = None) -> float:
        return salary if hours is None else salary * hours

    @kernel_function(
        name="monte_carlo_simulation",
        description=(
            "월매출, 원가, 급여, 임대료, 관리비, 수수료, 세율을 입력받아 "
            "10,000회 몬테카를로 시뮬레이션으로 평균 순이익과 손실 확률을 계산합니다. "
            "revenue는 [단일값] 또는 [최소값, 최대값, ...] 형태의 숫자 목록(원 단위)입니다."
        ),
    )
    def monte_carlo_simulation(
        self,
        revenue: list,
        cost: float,
        salary: float,
        hours: float = None,
        rent: float = 0,
        admin: float = 0,
        fee: float = 0,
        tax_rate: float = 0.2,
    ) -> dict:
        iterations = 10_000
        results = []
        salary_cost = self._calculate_salary(salary, hours)

        if len(revenue) == 1:
            for _ in range(iterations):
                sim_rev = random.gauss(revenue[0], revenue[0] * 0.1)
                sim_cost = random.gauss(cost, cost * 0.1)
                net = (sim_rev - sim_cost - salary_cost - rent - admin - fee) * (1 - tax_rate)
                results.append(net)
        else:
            for _ in range(iterations):
                sim_rev = random.choice(revenue)
                sim_cost = random.gauss(cost, cost * 0.1)
                net = (sim_rev - sim_cost - salary_cost - rent - admin - fee) * (1 - tax_rate)
                results.append(net)

        avg = sum(results) / iterations
        loss_prob = sum(1 for r in results if r < 0) / iterations
        return {"average_net_profit": round(avg), "loss_probability": round(loss_prob, 4)}

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
