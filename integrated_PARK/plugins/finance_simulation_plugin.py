"""
재무 시뮬레이션 플러그인
출처: CHANG/user_functions.py — FinanceSimulationSkill
"""

import base64
import io
import math
import os
import random
from semantic_kernel.functions import kernel_function

# [PR#51 수정] from CHANG.db_test import DBWork 제거
#   CHANG/은 팀원 개인 폴더로 integrated_PARK에서 직접 임포트 불가
#   (Azure 배포 환경에 CHANG 패키지 존재하지 않음 → ModuleNotFoundError)
#   DB 연동은 integrated_PARK 내부 모듈로 분리 후 재통합 예정

# [PR#51 수정] Windows 전용 폰트 하드코딩 3줄 제거
#   fontF = "C:\Windows\Fonts\gulim.ttc" 는 Linux(Azure) 환경에서 크래시 발생
#   commit 8a1daaa 에서 번들 폰트(nam/malgun.ttf) + fallback 방식으로 이미 수정됨
#   아래 try 블록이 그 수정사항을 담당함

try:
    import matplotlib
    matplotlib.use("Agg")  # 헤드리스 환경 (서버/컨테이너)
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    import matplotlib.font_manager as fm
    import numpy as np

    # 한글 폰트 설정
    # 1순위: 프로젝트 번들 폰트 (nam/malgun.ttf) — 배포 환경에서도 항상 사용 가능
    _BUNDLED_FONT = os.path.join(os.path.dirname(__file__), "..", "nam", "malgun.ttf")
    if os.path.exists(_BUNDLED_FONT):
        fm.fontManager.addfont(_BUNDLED_FONT)
        _ko_font = fm.FontProperties(fname=_BUNDLED_FONT).get_name()
    else:
        # 2순위: 시스템 설치 폰트 (로컬 개발 환경 등)
        _KO_FONT_CANDIDATES = [
            "Apple SD Gothic Neo", "Nanum Gothic", "AppleGothic",
            "Malgun Gothic", "NanumGothic", "Noto Sans CJK KR",
        ]
        _available = {f.name for f in fm.fontManager.ttflist}
        _ko_font = next((f for f in _KO_FONT_CANDIDATES if f in _available), None)

    if _ko_font:
        matplotlib.rcParams["font.family"] = _ko_font
    matplotlib.rcParams["axes.unicode_minus"] = False  # 마이너스 기호 깨짐 방지

    _MATPLOTLIB_AVAILABLE = True
except ImportError:
    _MATPLOTLIB_AVAILABLE = False


class FinanceSimulationPlugin:
    """몬테카를로 시뮬레이션 기반 재무 분석 플러그인"""
    def _calculate_salary(self, salary: float, hours: float = None) -> float:
        return salary if hours is None else salary * hours

    def _generate_chart(self, results: list, avg: float, p20: float, loss_prob: float) -> str | None:
        """몬테카를로 결과 히스토그램을 base64 PNG로 반환. matplotlib 없으면 None."""
        if not _MATPLOTLIB_AVAILABLE:
            return None
        try:
            fig, ax = plt.subplots(figsize=(7, 4))
            arr = np.array(results)

            ax.hist(arr, bins=60, color="#4e8cff", alpha=0.7, edgecolor="none")

            # 손실 구간 강조
            loss_vals = arr[arr < 0]
            if len(loss_vals):
                ax.hist(loss_vals, bins=30, color="#e74c3c", alpha=0.6, edgecolor="none")

            ax.axvline(avg,  color="#2ecc71", linewidth=1.8, linestyle="--", label=f"평균: {avg/10000:,.0f}만원")
            ax.axvline(p20,  color="#e67e22", linewidth=1.8, linestyle=":",  label=f"하위 20%: {p20/10000:,.0f}만원")
            ax.axvline(0,    color="#e74c3c", linewidth=1.2, linestyle="-",  alpha=0.5)

            ax.set_xlabel("월 순이익 (원)", fontsize=10)
            ax.set_ylabel("빈도", fontsize=10)
            ax.set_title(f"몬테카를로 시뮬레이션 (10,000회) — 손실 확률 {loss_prob:.1%}", fontsize=11)
            ax.legend(fontsize=9)
            ax.yaxis.set_visible(False)
            plt.tight_layout()

            buf = io.BytesIO()
            fig.savefig(buf, format="png", dpi=100)
            plt.close(fig)
            buf.seek(0)
            return base64.b64encode(buf.read()).decode("utf-8")
        except Exception:
            return None

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
        # [PR#51 수정] chart_b64 dead-code 호출 제거
        #   아래의 chart = self._generate_chart(results, avg, p20, loss_prob) 가 실제 사용됨
        chart = self._generate_chart(results, avg, p20, loss_prob)
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
            "chart":              chart,  # base64 PNG 또는 None
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
        # [PR#51 수정] DBWork(CHANG.db_test) 임포트 제거에 따라 DB 조회 임시 비활성화
        #   DB 연동 로직은 integrated_PARK 내부 모듈 분리 후 재통합 예정
        #   (PR#51 원본 의도: region/industry 코드 기반 매출 조회 → 통합 시 아래 주석 복원)
        #
        # if region is None and industry is None:
        #     revenue = dbwork.get_average_sales()
        # else:
        #     revenue = dbwork.get_sales(region, industry)

        # DB 제외용 임시 기본값 (카페 기준, 업종별 평균치로 추후 수정 예정)
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
    # region and industry의 경우 부모 에이전트에게서 받을 임시 정보입니다(지역 및 업종). 각 단일 코드 기반으로 변경

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


    # [PR#51 수정] 아래 _generate_chart 정의 주석 처리
    #   이유: 클래스 상단(line ~52)에 이미 동일 메서드가 정의되어 있음
    #   Python은 마지막 정의를 사용하므로 이 버전이 덮어쓰면
    #   기존 4인수 호출 self._generate_chart(results, avg, p20, loss_prob) 이 TypeError 발생
    #   인수 순서도 (results, p20, avg) vs 기존 (results, avg, p20, loss_prob) 로 불일치
    #   색상·레전드 개선은 추후 상단 메서드와 통합하여 반영 예정
    #
    # def _generate_chart(self, results: list, p20: float, avg: float) -> str:
    #     fig, ax = plt.subplots(figsize=(8, 4))
    #     n, bins, patches = ax.hist(results, bins=40, edgecolor="none")
    #     for patch, left_edge in zip(patches, bins[:-1]):
    #         if left_edge < 0:
    #             patch.set_facecolor("#E24B4A")   # 손실
    #         elif left_edge < p20:
    #             patch.set_facecolor("#EF9F27")   # 하위 20%
    #         else:
    #             patch.set_facecolor("#378ADD")   # 수익
    #     ax.axvline(x=0,   color="#E24B4A", linestyle="--", linewidth=1.2, alpha=0.8)
    #     ax.axvline(x=avg, color="#378ADD", linestyle="--", linewidth=1.2, alpha=0.8)
    #     ax.axvline(x=p20, color="#EF9F27", linestyle="--", linewidth=1.2, alpha=0.8)
    #     legend_handles = [
    #         mpatches.Patch(color="#E24B4A", label="손실 구간"),
    #         mpatches.Patch(color="#EF9F27", label=f"하위 20% 기준: {round(p20/10000):,}만원"),
    #         mpatches.Patch(color="#378ADD", label=f"평균: {round(avg/10000):,}만원"),
    #     ]
    #     ax.legend(handles=legend_handles, fontsize=9)
    #     ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{int(x/10000):,}만"))
    #     ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{int(x):,}"))
    #     ax.set_xlabel("월 순이익 (만원)", fontsize=10)
    #     ax.set_ylabel("빈도 (회)", fontsize=10)
    #     plt.tight_layout()
    #     buf = io.BytesIO()
    #     fig.savefig(buf, format="png", dpi=120)
    #     plt.close(fig)
    #     buf.seek(0)
    #     return base64.b64encode(buf.read()).decode("utf-8")

