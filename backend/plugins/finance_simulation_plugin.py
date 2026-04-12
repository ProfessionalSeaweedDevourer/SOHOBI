"""
재무 시뮬레이션 플러그인
출처: CHANG/user_functions.py — FinanceSimulationSkill
"""

import asyncio
import concurrent.futures
import math
import random

from db.repository import INDUSTRY_CODE_MAP
from semantic_kernel.functions import kernel_function

try:
    from db.finance_db import DBWork

    _DBWORK_AVAILABLE = True
except Exception:
    _DBWORK_AVAILABLE = False

INDUSTRY_RATIO = {
    "CS100001": {  # 한식
        "cost": 0.35,
        "salary": 0.20,
        "rent": 0.10,
        "admin": 0.03,
        "fee": 0.03,
    },
    "CS100002": {  # 중식
        "cost": 0.40,
        "salary": 0.20,
        "rent": 0.10,
        "admin": 0.03,
        "fee": 0.03,
    },
    "CS100003": {  # 일식
        "cost": 0.45,
        "salary": 0.20,
        "rent": 0.10,
        "admin": 0.03,
        "fee": 0.03,
    },
    "CS100004": {  # 양식
        "cost": 0.45,
        "salary": 0.20,
        "rent": 0.10,
        "admin": 0.03,
        "fee": 0.03,
    },
    "CS100005": {  # 베이커리
        "cost": 0.55,
        "salary": 0.20,
        "rent": 0.08,
        "admin": 0.03,
        "fee": 0.03,
    },
    "CS100006": {  # 패스트푸드
        "cost": 0.40,
        "salary": 0.20,
        "rent": 0.10,
        "admin": 0.03,
        "fee": 0.05,
    },
    "CS100007": {  # 치킨
        "cost": 0.52,
        "salary": 0.20,
        "rent": 0.10,
        "admin": 0.03,
        "fee": 0.05,
    },
    "CS100008": {  # 분식
        "cost": 0.40,
        "salary": 0.20,
        "rent": 0.10,
        "admin": 0.03,
        "fee": 0.03,
    },
    "CS100009": {  # 호프/술집
        "cost": 0.40,
        "salary": 0.20,
        "rent": 0.10,
        "admin": 0.03,
        "fee": 0.03,
    },
    "CS100010": {  # 카페/커피
        "cost": 0.36,
        "salary": 0.20,
        "rent": 0.15,
        "admin": 0.03,
        "fee": 0.03,
    },
    "default": {
        "cost": 0.35,
        "salary": 0.20,
        "rent": 0.10,
        "admin": 0.03,
        "fee": 0.03,
    },
}


class FinanceSimulationPlugin:
    """몬테카를로 시뮬레이션 기반 재무 분석 플러그인

    월매출 데이터를 기반으로 순이익 분포, 손실 확률, 손익분기점,
    투자 회수 기간을 산출한다. 업종별 비용 비율은 INDUSTRY_RATIO 참조.
    """

    def __init__(self) -> None:
        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=4)

    def _calculate_salary(self, salary: float, hours: float = None) -> float:
        return salary if hours is None else salary * hours

    def get_industry_ratio(self, industry: str = None) -> dict:
        """
        업종 코드에 대응하는 비용 비율 dict를 반환한다.

        Args:
            industry: 서비스 업종 코드 (예: "CS100010"). 미입력 시 default 비율 반환.

        Returns:
            dict: cost, salary, rent, admin, fee 비율 포함.
        """
        return INDUSTRY_RATIO.get(industry, INDUSTRY_RATIO["default"])

    def _generate_chart(self, results: list, avg: float, p20: float) -> dict:
        """몬테카를로 결과를 프론트엔드 chart.js용 JSON bins로 반환."""
        min_val, max_val = min(results), max(results)
        bin_count = 40
        bin_size = (max_val - min_val) / bin_count if max_val != min_val else 1

        bins = []
        for i in range(bin_count):
            left = min_val + i * bin_size
            right = left + bin_size
            count = sum(1 for r in results if left <= r < right)
            bins.append(
                {
                    "left": round(left),
                    "right": round(right),
                    "count": count,
                    "type": "loss" if left < 0 else "p20" if left < p20 else "profit",
                }
            )

        return {
            "bins": bins,
            "avg": round(avg),
            "p20": round(p20),
            "min": round(min_val),
            "max": round(max_val),
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
        """
        10,000회 몬테카를로 시뮬레이션으로 순이익 분포를 산출한다.

        미입력 비용 항목은 업종 비율(INDUSTRY_RATIO) 기반으로 자동 산출.
        revenue가 단일값이면 ±10% 정규분포, 복수값이면 실데이터 샘플링 방식 적용.

        Args:
            revenue (list[float]): 월매출 리스트 (원 단위)
            cost (float | None): 월 원가
            salary (float | None): 급여 (시급 시 hours와 함께 사용)
            hours (float | None): 월 근무시간 (시급 계산용)
            rent (float | None): 임대료
            admin (float | None): 관리비
            fee (float | None): 수수료
            industry (str | None): 업종 코드

        Returns:
            dict:
                - average_net_profit: 평균 순이익
                - loss_probability: 손실 발생 확률 (0~1)
                - avg_loss_amount: 손실 발생 시 평균 손실액
                - p20: 하위 20% 순이익 (비관 시나리오)
                - actual_cost/salary/rent/admin/fee: 실제 적용된 비용
                - chart: 히스토그램 bins 데이터
        """
        iterations = 10_000
        results = []

        avg_sales = sum(revenue) / len(revenue)
        ratio = self.get_industry_ratio(industry)

        if cost is None:
            cost = avg_sales * ratio["cost"]
        if salary is None:
            salary = avg_sales * ratio["salary"]
        if rent is None:
            rent = avg_sales * ratio["rent"]
        if admin is None:
            admin = avg_sales * ratio["admin"]
        if fee is None:
            fee = avg_sales * ratio["fee"]

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
        chart["total_cost"] = round(cost + salary_cost + rent + admin + fee)

        return {
            "average_net_profit": round(avg),
            "loss_probability": round(loss_prob, 4),
            "avg_loss_amount": avg_loss,
            "p20": round(p20),
            "actual_cost": round(cost),
            "actual_salary": round(salary_cost),
            "actual_rent": round(rent),
            "actual_admin": round(admin),
            "actual_fee": round(fee),
            "chart": chart,
        }

    async def monte_carlo_simulation_async(self, **kwargs) -> dict:
        """monte_carlo_simulation의 비동기 래퍼 — 10,000회 루프를 스레드 풀에서 실행."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            self._executor,
            lambda: self.monte_carlo_simulation(**kwargs),
        )

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

    def breakeven_analysis_mc(
        self,
        avg_revenue: float,
        avg_net_profit: float,
        variable_cost: float,
    ) -> dict:
        """
        몬테카를로 결과 기반 손익분기점 및 안전마진을 산출한다.

        계산 불가 조건:
            - avg_revenue <= 0: 매출이 0 이하
            - variable_cost_ratio >= 1: 원가율이 매출을 초과

        Args:
            avg_revenue: 평균 월매출
            avg_net_profit: 평균 순이익
            variable_cost: 변동비 (원가)

        Returns:
            dict:
                - breakeven_revenue: 손익분기 월매출. 계산 불가 시 None.
                - breakeven_daily: 손익분기 일매출. 계산 불가 시 None.
                - safety_margin: 안전마진 비율. 계산 불가 시 None.
        """
        if avg_revenue <= 0:
            return {
                "breakeven_revenue": None,
                "breakeven_daily": None,
                "safety_margin": None,
            }

        avg_total_cost = avg_revenue - avg_net_profit
        variable_cost_ratio = variable_cost / avg_revenue
        fixed_cost = avg_total_cost - variable_cost

        if variable_cost_ratio >= 1:
            return {
                "breakeven_revenue": None,
                "breakeven_daily": None,
                "safety_margin": None,
            }

        breakeven_revenue = fixed_cost / (1 - variable_cost_ratio)
        safety_margin = (avg_revenue - breakeven_revenue) / avg_revenue
        return {
            "breakeven_revenue": round(breakeven_revenue),
            "breakeven_daily": round(breakeven_revenue / 30),
            "safety_margin": round(safety_margin, 4),
        }

    def load_initial(self, region: list = None, industry: str = None) -> dict:
        """
        지역/업종 기반 초기 매출 데이터를 로드한다.

        DB 조회 실패 또는 미입력 시 DEFAULT_REVENUE_FALLBACK 반환.

        Args:
            region: 행정동 코드 리스트
            industry: 업종명 (INDUSTRY_CODE_MAP 키값)

        Returns:
            dict: revenue 및 나머지 비용 항목(None) 포함한 초기 파라미터 dict.
        """
        if isinstance(region, int):
            region = [str(region)]
        elif isinstance(region, list):
            region = [str(r) for r in region] if region else None

        industry_cd = INDUSTRY_CODE_MAP.get(industry)
        if _DBWORK_AVAILABLE:
            try:
                dbwork = DBWork()
                if region is None and industry is None:
                    result = dbwork.get_average_sales()
                    revenue = (
                        [float(v) for v in result]
                        if hasattr(result, "__iter__")
                        else [float(result)]
                    )
                else:
                    revenue = [float(v) for v in dbwork.get_sales(region, industry_cd)]
            except Exception:
                revenue = [float(46_000_000)]
        else:
            revenue = [float(46_000_000)]

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
        """
        기존 파라미터 dict에 새 입력값을 병합한다.

        current의 None이 아닌 값만 previous를 덮어쓴다.

        Args:
            previous: 누적된 기존 파라미터
            current: 새로 입력된 파라미터

        Returns:
            dict: 병합된 파라미터 dict.
        """
        merged = previous.copy()
        for key, value in current.items():
            if value is not None:
                merged[key] = value
        return merged
