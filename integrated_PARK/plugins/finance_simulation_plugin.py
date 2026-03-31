"""
재무 시뮬레이션 플러그인
출처: CHANG/user_functions.py — FinanceSimulationSkill
"""

import math
import os
import random
from semantic_kernel.functions import kernel_function

try:
    from db.finance_db import DBWork
    _DBWORK_AVAILABLE = True
except Exception:
    _DBWORK_AVAILABLE = False

INDUSTRY_RATIO = {
    "CS100001": {  # 한식
        "cost": 0.35, "salary": 0.20, "rent": 0.10, "admin": 0.03, "fee": 0.03,
    },
    "CS100002": {  # 중식
        "cost": 0.40, "salary": 0.20, "rent": 0.10, "admin": 0.03, "fee": 0.03,
    },
    "CS100003": {  # 일식
        "cost": 0.45, "salary": 0.20, "rent": 0.10, "admin": 0.03, "fee": 0.03,
    },
    "CS100004": {  # 양식
        "cost": 0.45, "salary": 0.20, "rent": 0.10, "admin": 0.03, "fee": 0.03,
    },
    "CS100005": {  # 베이커리
        "cost": 0.55, "salary": 0.20, "rent": 0.08, "admin": 0.03, "fee": 0.03,
    },
    "CS100006": {  # 패스트푸드
        "cost": 0.40, "salary": 0.20, "rent": 0.10, "admin": 0.03, "fee": 0.05,
    },
    "CS100007": {  # 치킨
        "cost": 0.52, "salary": 0.20, "rent": 0.10, "admin": 0.03, "fee": 0.05,
    },
    "CS100008": {  # 분식
        "cost": 0.40, "salary": 0.20, "rent": 0.10, "admin": 0.03, "fee": 0.03,
    },
    "CS100009": {  # 호프/술집
        "cost": 0.40, "salary": 0.20, "rent": 0.10, "admin": 0.03, "fee": 0.03,
    },
    "CS100010": {  # 카페/커피
        "cost": 0.36, "salary": 0.20, "rent": 0.15, "admin": 0.03, "fee": 0.03,
    },
    "default": {
        "cost": 0.35, "salary": 0.20, "rent": 0.10, "admin": 0.03, "fee": 0.03,
    },
}


class FinanceSimulationPlugin:
    """몬테카를로 시뮬레이션 기반 재무 분석 플러그인"""

    def _calculate_salary(self, salary: float, hours: float = None) -> float:
        return salary if hours is None else salary * hours

    def get_industry_ratio(self, industry: str = None) -> dict:
        return INDUSTRY_RATIO.get(industry, INDUSTRY_RATIO["default"])

    def _generate_chart(self, results: list, avg: float, p20: float) -> dict:
        """몬테카를로 결과를 프론트엔드 chart.js용 JSON bins로 반환."""
        min_val, max_val = min(results), max(results)
        bin_count = 40
        bin_size = (max_val - min_val) / bin_count

        bins = []
        for i in range(bin_count):
            left = min_val + i * bin_size
            right = left + bin_size
            count = sum(1 for r in results if left <= r < right)
            bins.append({
                "left":  round(left),
                "right": round(right),
                "count": count,
                "type":  "loss" if left < 0 else "p20" if left < p20 else "profit",
            })

        return {
            "bins": bins,
            "avg":  round(avg),
            "p20":  round(p20),
            "min":  round(min_val),
            "max":  round(max_val),
        }

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
        industry: str = None,
    ) -> dict:
        iterations = 10_000
        results = []

        avg_sales = sum(revenue) / len(revenue)
        ratio = self.get_industry_ratio(industry)

        if cost   is None: cost   = avg_sales * ratio["cost"]
        if salary is None: salary = avg_sales * ratio["salary"]
        if rent   is None: rent   = avg_sales * ratio["rent"]
        if admin  is None: admin  = avg_sales * ratio["admin"]
        if fee    is None: fee    = avg_sales * ratio["fee"]

        salary_cost = self._calculate_salary(salary, hours)

        if len(revenue) == 1:
            for _ in range(iterations):
                sim_rev = random.gauss(revenue[0], revenue[0] * 0.1)
                sim_cost = random.gauss(cost, cost * 0.1)
                net = sim_rev - sim_cost - salary_cost - rent - admin - fee
                results.append(net)
        else:
            for _ in range(iterations):
                sim_rev = random.choice(revenue) * random.gauss(1.0, 0.1)
                sim_cost = random.gauss(cost, cost * 0.1)
                net = sim_rev - sim_cost - salary_cost - rent - admin - fee
                results.append(net)

        avg = sum(results) / iterations
        loss_prob = sum(1 for r in results if r < 0) / iterations

        sorted_results = sorted(results)
        loss_results = [r for r in results if r < 0]
        avg_loss = round(sum(loss_results) / len(loss_results)) if loss_results else 0

        p20 = sorted_results[int(iterations * 0.20)]
        chart = self._generate_chart(results, avg, p20)

        return {
            "average_net_profit": round(avg),
            "loss_probability":   round(loss_prob, 4),
            "avg_loss_amount":    avg_loss,
            "p20":                round(p20),
            "actual_cost":        round(cost),
            "actual_salary":      round(salary_cost),
            "actual_rent":        round(rent),
            "actual_admin":       round(admin),
            "actual_fee":         round(fee),
            "chart":              chart,
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

    def breakeven_analysis(self, fixed_cost: float, variable_cost_ratio: float) -> dict:
        breakeven_revenue = fixed_cost / (1 - variable_cost_ratio)
        return {
            "breakeven_revenue": round(breakeven_revenue),
            "breakeven_daily":   round(breakeven_revenue / 30),
        }

    def breakeven_analysis_mc(
        self,
        avg_revenue: float,
        avg_net_profit: float,
        variable_cost: float,
    ) -> dict:
        avg_total_cost = avg_revenue - avg_net_profit
        variable_cost_ratio = variable_cost / avg_revenue
        fixed_cost = avg_total_cost - variable_cost
        breakeven_revenue = fixed_cost / (1 - variable_cost_ratio)
        safety_margin = (avg_revenue - breakeven_revenue) / avg_revenue
        return {
            "breakeven_revenue": round(breakeven_revenue),
            "breakeven_daily":   round(breakeven_revenue / 30),
            "safety_margin":     round(safety_margin, 4),
        }

    def load_initial(self, region: str = None, industry: str = None) -> dict:
        """지역/업종 코드를 받아 매출 데이터를 불러옵니다."""
        if _DBWORK_AVAILABLE:
            try:
                dbwork = DBWork()
                if region is None and industry is None:
                    revenue = dbwork.get_average_sales()
                else:
                    revenue = dbwork.get_sales(region, industry)
            except Exception:
                revenue = [14000000]
        else:
            revenue = [14000000]

        return {
            "revenue": revenue,
            "cost": None,
            "salary": None,
            "hours": None,
            "rent": None,
            "admin": None,
            "fee": None,
            "initial_investment": None,
        }

    def merge_json(self, previous: dict, current: dict) -> dict:
        """기존 JSON(previous)에 새 입력(current)을 병합."""
        merged = previous.copy()
        for key, value in current.items():
            if value is not None:
                merged[key] = value
        return merged
