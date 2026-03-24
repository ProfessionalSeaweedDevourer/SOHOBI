"""
몬테카를로 시뮬레이션 단독 테스트 파일
실행: python simulation_test.py
의존성: pip install matplotlib
"""

import math
import random
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.font_manager as fm

fontF = "C:\Windows\Fonts\gulim.ttc"
fontN = fm.FontProperties(fname=fontF, size= 10).get_name() # 폰트명
plt.rc("font", family=fontN) # mpl 기본톤프 바꾸기
plt.rcParams["axes.unicode_minus"]=False # - 안깨지게... 

# ── 입력값 (load_defaults 기준) ──────────────────────────────────────────
DEFAULTS = {
    "revenue":  [27591265, 41168021, 38878505, 33918153, 29204105,
                 46292398, 55761635, 38853690, 33976696, 53177942,
                 53646589, 29447719, 39657499],
    "cost":     40121094 * 0.4,
    "salary":   1400000,
    "hours":    None,
    "rent":     1800000,
    "admin":    40121094 * 0.03,
    "fee":      40121094 * 0.03,
}


# ── 시뮬레이션 ────────────────────────────────────────────────────────────
def calculate_salary(salary: float, hours: float = None) -> float:
    return salary if hours is None else salary * hours


def monte_carlo_simulation(
    revenue: list,
    cost: float = None,
    salary: float = None,
    hours: float = None,
    rent: float = None,
    admin: float = None,
    fee: float = None,
) -> dict:
    iterations = 10_000
    results = []

    avg_sales = sum(revenue) / len(revenue)
    if cost   is None: cost   = avg_sales * 0.36
    if salary is None: salary = avg_sales * 0.20
    if rent   is None: rent   = avg_sales * 0.15
    if admin  is None: admin  = avg_sales * 0.03
    if fee    is None: fee    = avg_sales * 0.03

    salary_cost = calculate_salary(salary, hours)

    if len(revenue) == 1:
        for _ in range(iterations):
            sim_rev  = random.gauss(revenue[0], revenue[0] * 0.1)
            sim_cost = random.gauss(cost, cost * 0.1)
            results.append(sim_rev - sim_cost - salary_cost - rent - admin - fee)
    else:
        for _ in range(iterations):
            base     = random.choice(revenue)
            sim_rev  = base * random.gauss(1.0, 0.1)
            sim_cost = random.gauss(cost, cost * 0.1)
            results.append(sim_rev - sim_cost - salary_cost - rent - admin - fee)

    results.sort()

    avg       = sum(results) / iterations
    loss_prob = sum(1 for r in results if r < 0) / iterations

    loss_results = [r for r in results if r < 0]
    avg_loss  = round(sum(loss_results) / len(loss_results)) if loss_results else 0

    p20 = results[int(iterations * 0.20)]

    return {
        "results":            results,
        "average_net_profit": round(avg),
        "loss_probability":   round(loss_prob, 4),
        "avg_loss_amount":    avg_loss,
        "p20":                round(p20),
        "actual_cost":        round(cost),
        "actual_salary":      round(salary_cost),
        "actual_rent":        round(rent),
        "actual_admin":       round(admin),
        "actual_fee":         round(fee),
    }


# ── 그래프 출력 ───────────────────────────────────────────────────────────
def plot_simulation(sim: dict, revenue: list) -> None:
    results = sim["results"]
    avg     = sim["average_net_profit"]
    p20     = sim["p20"]

    fig, ax = plt.subplots(figsize=(10, 5))
    fig.patch.set_facecolor("#FAFAFA")
    ax.set_facecolor("#FAFAFA")

    bin_count = 40
    n, bins, patches = ax.hist(results, bins=bin_count, edgecolor="none")

    for patch, left_edge in zip(patches, bins[:-1]):
        if left_edge < 0:
            patch.set_facecolor("#E24B4A")   # 손실
        elif left_edge < p20:
            patch.set_facecolor("#EF9F27")   # 하위 20%
        else:
            patch.set_facecolor("#378ADD")   # 수익

    ax.axvline(x=0,   color="#E24B4A", linestyle="--", linewidth=1.2, alpha=0.8)
    ax.axvline(x=avg, color="#378ADD", linestyle="--", linewidth=1.2, alpha=0.8)
    ax.axvline(x=p20, color="#EF9F27", linestyle="--", linewidth=1.2, alpha=0.8)

    legend_handles = [
        mpatches.Patch(color="#E24B4A", label="손실 구간 (0원 미만)"),
        mpatches.Patch(color="#EF9F27", label=f"하위 20% 기준선: {round(p20/10000):,}만원"),
        mpatches.Patch(color="#378ADD", label=f"평균 순이익: {round(avg/10000):,}만원"),
    ]
    ax.legend(handles=legend_handles, fontsize=9, framealpha=0.85)

    ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{int(x/10000):,}만"))
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{int(x):,}"))
    ax.set_xlabel("월 순이익 (만원)", fontsize=10)
    ax.set_ylabel("빈도 (회)", fontsize=10)
    ax.set_title("몬테카를로 시뮬레이션 순이익 분포 (10,000회)", fontsize=12, pad=14)

    # 요약 텍스트
    summary = (
        f"평균 순이익:  {round(avg/10000):,}만원\n"
        f"손실 확률:    {sim['loss_probability']*100:.2f}%\n"
        f"하위 20% 기준: {round(p20/10000):,}만원"
    )
    ax.text(
        0.98, 0.97, summary,
        transform=ax.transAxes,
        fontsize=9, verticalalignment="top", horizontalalignment="right",
        bbox=dict(boxstyle="round,pad=0.5", facecolor="white", alpha=0.8, edgecolor="#cccccc"),
    )

    plt.tight_layout()
    plt.show()


# ── 실행 ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    params = {k: v for k, v in DEFAULTS.items() if k != "revenue"}
    sim_result = monte_carlo_simulation(revenue=DEFAULTS["revenue"], **params)

    print("=" * 45)
    print("  몬테카를로 시뮬레이션 결과")
    print("=" * 45)
    print(f"  평균 월 순이익  : {round(sim_result['average_net_profit']/10000):,}만원")
    print(f"  손실 확률       : {sim_result['loss_probability']*100:.2f}%")
    print(f"  하위 20% 기준   : {round(sim_result['p20']/10000):,}만원")
    print(f"  손실 시 평균    : {round(sim_result['avg_loss_amount']/10000):,}만원")
    print("-" * 45)
    print(f"  [가정 조건]")
    print(f"  원가   : {sim_result['actual_cost']//10000:,}만원")
    print(f"  급여   : {sim_result['actual_salary']//10000:,}만원")
    print(f"  임대료 : {sim_result['actual_rent']//10000:,}만원")
    print(f"  관리비 : {sim_result['actual_admin']//10000:,}만원")
    print(f"  수수료 : {sim_result['actual_fee']//10000:,}만원")
    print("=" * 45)

    plot_simulation(sim_result, DEFAULTS["revenue"])
