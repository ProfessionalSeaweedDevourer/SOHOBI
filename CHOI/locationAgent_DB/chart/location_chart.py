"""
location_chart.py
상권분석 결과를 matplotlib 차트로 시각화하여 base64 PNG로 반환
각 도표를 개별 이미지로 생성
"""

import base64
import io
import os

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.font_manager as fm
    from matplotlib.ticker import FuncFormatter
    import numpy as np

    # 한글 폰트 설정
    _BUNDLED_FONT = os.path.join(os.path.dirname(__file__), "..", "..", "..", "NAM", "malgun.ttf")
    if os.path.exists(_BUNDLED_FONT):
        fm.fontManager.addfont(_BUNDLED_FONT)
        _ko_font = fm.FontProperties(fname=_BUNDLED_FONT).get_name()
    else:
        _KO_FONT_CANDIDATES = [
            "Malgun Gothic", "Apple SD Gothic Neo", "Nanum Gothic",
            "NanumGothic", "Noto Sans CJK KR",
        ]
        _available = {f.name for f in fm.fontManager.ttflist}
        _ko_font = next((f for f in _KO_FONT_CANDIDATES if f in _available), None)

    if _ko_font:
        matplotlib.rcParams["font.family"] = _ko_font
    matplotlib.rcParams["axes.unicode_minus"] = False

    _MATPLOTLIB_AVAILABLE = True
except ImportError:
    _MATPLOTLIB_AVAILABLE = False


# ── 색상 팔레트 ──────────────────────────────────────────────
_BAR_COLOR = "#4e8cff"
_BAR_HIGHLIGHT = "#e67e22"
_LINE_COLOR = "#2ecc71"
_AGE_COLORS = ["#a78bfa", "#6366f1", "#0ea5e9", "#10b981", "#f59e0b", "#ef4444"]
_GENDER_COLORS = ["#2563eb", "#ec4899"]
_COMPARE_COLORS = ["#4e8cff", "#e74c3c", "#2ecc71", "#e67e22", "#9b59b6"]


def _억만_label(v: float) -> str:
    if v >= 100_000_000:
        return f"{v / 100_000_000:.1f}억"
    if v >= 10_000:
        return f"{v / 10_000:,.0f}만"
    return f"{v:,.0f}"


def _억만_formatter(x, _):
    if x == 0:
        return "0"
    return _억만_label(x)


def _fig_to_base64(fig) -> str:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=130, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode("utf-8")


# ── 개별 차트 함수들 ─────────────────────────────────────────

def _chart_day(sales_summary: dict, title_prefix: str = "") -> str | None:
    """요일별 매출 막대 차트"""
    try:
        fig, ax = plt.subplots(figsize=(9, 5))
        if title_prefix:
            fig.suptitle(f"{title_prefix}", fontsize=13, fontweight="bold")

        day_labels = ["월", "화", "수", "목", "금", "토", "일"]
        day_keys = [
            "mon_sales_krw", "tue_sales_krw", "wed_sales_krw",
            "thu_sales_krw", "fri_sales_krw", "sat_sales_krw", "sun_sales_krw",
        ]
        day_vals = [sales_summary.get(k, 0) / 4 for k in day_keys]

        bar_colors = [_BAR_COLOR] * 7
        if max(day_vals) > 0:
            bar_colors[day_vals.index(max(day_vals))] = _BAR_HIGHLIGHT

        bars = ax.bar(day_labels, day_vals, color=bar_colors, width=0.55, edgecolor="none")
        ax.set_title("📅 요일별 평균 매출(일단위)", fontsize=13, fontweight="bold", pad=8)
        ax.yaxis.set_major_formatter(FuncFormatter(_억만_formatter))
        ax.spines[["top", "right"]].set_visible(False)
        ax.tick_params(axis="x", labelsize=12)

        for bar, val in zip(bars, day_vals):
            if val > 0:
                ax.text(
                    bar.get_x() + bar.get_width() / 2, bar.get_height(),
                    _억만_label(val), ha="center", va="bottom", fontsize=9, color="#475569",
                )

        plt.tight_layout()
        return _fig_to_base64(fig)
    except Exception:
        return None


def _chart_time(sales_summary: dict, title_prefix: str = "") -> str | None:
    """시간대별 매출 라인 차트 (데이터 없으면 주중/주말 막대로 대체)"""
    try:
        fig, ax = plt.subplots(figsize=(9, 5))
        if title_prefix:
            fig.suptitle(f"{title_prefix}", fontsize=13, fontweight="bold")

        time_keys = [
            "time_00_06_krw", "time_06_11_krw", "time_11_14_krw",
            "time_14_17_krw", "time_17_21_krw", "time_21_24_krw",
        ]
        time_vals = [sales_summary.get(k, 0) for k in time_keys]
        has_time_data = max(time_vals) > 0

        if has_time_data:
            time_labels = ["00-06", "06-11", "11-14", "14-17", "17-21", "21-24"]
            ax.plot(
                time_labels, time_vals,
                color=_LINE_COLOR, linewidth=2.5, marker="o", markersize=8, zorder=3,
            )
            ax.fill_between(range(len(time_labels)), time_vals, alpha=0.12, color=_LINE_COLOR)
            ax.set_xticks(range(len(time_labels)))
            ax.set_xticklabels(time_labels, fontsize=11)

            peak_idx = time_vals.index(max(time_vals))
            ax.plot(peak_idx, time_vals[peak_idx], "o", color=_BAR_HIGHLIGHT, markersize=11, zorder=4)
            ax.annotate(
                _억만_label(time_vals[peak_idx]),
                (peak_idx, time_vals[peak_idx]),
                textcoords="offset points", xytext=(0, 12),
                ha="center", fontsize=10, fontweight="bold", color=_BAR_HIGHLIGHT,
            )
            ax.set_title("⏰ 시간대별 매출", fontsize=13, fontweight="bold", pad=8)
            ax.yaxis.set_major_formatter(FuncFormatter(_억만_formatter))
        else:
            wkday = sales_summary.get("weekday_sales_krw", 0) / 4
            wkend = sales_summary.get("weekend_sales_krw", 0) / 4
            if wkday + wkend > 0:
                wd_bars = ax.bar(
                    ["주중", "주말"], [wkday, wkend],
                    color=[_BAR_COLOR, _BAR_HIGHLIGHT], width=0.4, edgecolor="none",
                )
                for bar, val in zip(wd_bars, [wkday, wkend]):
                    if val > 0:
                        ax.text(
                            bar.get_x() + bar.get_width() / 2, bar.get_height(),
                            _억만_label(val), ha="center", va="bottom",
                            fontsize=11, fontweight="bold", color="#475569",
                        )
                ax.yaxis.set_major_formatter(FuncFormatter(_억만_formatter))
                ax.set_title("📊 주중 / 주말 평균 매출(일단위)", fontsize=13, fontweight="bold", pad=8)
            else:
                ax.text(0.5, 0.5, "시간대 / 주중주말 데이터 없음",
                        transform=ax.transAxes, ha="center", va="center",
                        fontsize=12, color="#94a3b8")
                ax.set_title("⏰ 시간대별 매출", fontsize=13, fontweight="bold", pad=8)
                ax.axis("off")

        ax.spines[["top", "right"]].set_visible(False)
        plt.tight_layout()
        return _fig_to_base64(fig)
    except Exception:
        return None


def _chart_age(sales_summary: dict, title_prefix: str = "") -> str | None:
    """연령대별 매출 도넛 차트"""
    try:
        fig, ax = plt.subplots(figsize=(7, 7))
        if title_prefix:
            fig.suptitle(f"{title_prefix}", fontsize=13, fontweight="bold")

        age_labels_full = ["10대", "20대", "30대", "40대", "50대", "60대+"]
        age_keys = [
            "age_10s_krw", "age_20s_krw", "age_30s_krw",
            "age_40s_krw", "age_50s_krw", "age_60s_krw",
        ]
        age_vals_full = [sales_summary.get(k, 0) for k in age_keys]

        age_labels, age_vals, age_colors = [], [], []
        for lbl, val, col in zip(age_labels_full, age_vals_full, _AGE_COLORS):
            if val > 0:
                age_labels.append(lbl)
                age_vals.append(val)
                age_colors.append(col)

        if age_vals:
            wedges, texts, autotexts = ax.pie(
                age_vals, labels=age_labels, colors=age_colors,
                autopct="%1.1f%%", pctdistance=0.78,
                wedgeprops=dict(width=0.42, edgecolor="white", linewidth=2),
                textprops={"fontsize": 13},
                startangle=90,
            )
            for at in autotexts:
                at.set_fontsize(11)
                at.set_color("#1e293b")
        else:
            ax.text(0.5, 0.5, "데이터 없음", transform=ax.transAxes,
                    ha="center", va="center", fontsize=12, color="#94a3b8")

        ax.set_title("🎂 연령대별 매출", fontsize=13, fontweight="bold", pad=8)
        ax.set_aspect("equal")
        plt.tight_layout()
        return _fig_to_base64(fig)
    except Exception:
        return None


def _chart_gender(sales_summary: dict, title_prefix: str = "") -> str | None:
    """성별 매출 도넛 차트"""
    try:
        fig, ax = plt.subplots(figsize=(7, 7))
        if title_prefix:
            fig.suptitle(f"{title_prefix}", fontsize=13, fontweight="bold")

        male = sales_summary.get("male_sales_krw", 0)
        female = sales_summary.get("female_sales_krw", 0)

        if male + female > 0:
            wedges, texts, autotexts = ax.pie(
                [male, female], labels=["남성", "여성"], colors=_GENDER_COLORS,
                autopct="%1.1f%%", pctdistance=0.78,
                wedgeprops=dict(width=0.42, edgecolor="white", linewidth=2),
                textprops={"fontsize": 14},
                startangle=90,
            )
            for at in autotexts:
                at.set_fontsize(12)
                at.set_fontweight("bold")
                at.set_color("white")

            total = male + female
            ax.text(0, 0, _억만_label(total),
                    ha="center", va="center", fontsize=15, fontweight="bold", color="#1e293b")
        else:
            ax.text(0.5, 0.5, "데이터 없음", transform=ax.transAxes,
                    ha="center", va="center", fontsize=12, color="#94a3b8")

        ax.set_title("👤 성별 매출", fontsize=13, fontweight="bold", pad=8)
        ax.set_aspect("equal")
        plt.tight_layout()
        return _fig_to_base64(fig)
    except Exception:
        return None


# ── 공개 API ────────────────────────────────────────────────

def generate_analyze_charts(
    sales_summary: dict,
    location: str = "",
    business_type: str = "",
) -> list[str]:
    """
    단일 지역 상권 분석 — 차트 4개를 개별 base64 PNG 리스트로 반환
      [0] 요일별 매출 막대
      [1] 시간대별 매출 라인 (데이터 없으면 주중/주말 막대)
      [2] 연령대별 매출 도넛
      [3] 성별 매출 도넛
    """
    if not _MATPLOTLIB_AVAILABLE or not sales_summary:
        return []

    title_prefix = f"{location} 전체 {business_type} 기준".strip()
    charts = []
    for fn in [_chart_day, _chart_time, _chart_age, _chart_gender]:
        result = fn(sales_summary, title_prefix)
        if result:
            charts.append(result)
    return charts


def generate_compare_charts(
    compare_data: list[dict],
    business_type: str = "",
) -> list[str]:
    """
    다중 지역 비교 — 차트 2개를 개별 base64 PNG 리스트로 반환
      [0] 매출 비교 그룹 막대
      [1] 점포 지표 비교 그룹 막대
    """
    if not _MATPLOTLIB_AVAILABLE or not compare_data:
        return []

    try:
        n = len(compare_data)
        locations = [d["location"] for d in compare_data]
        x = np.arange(n)
        w = 0.35
        loc_colors = _COMPARE_COLORS[:n]
        title = f"{business_type} 지역 비교" if business_type else "지역 비교"
        charts = []

        # ── 차트1: 매출 비교 ────────────────────────────────
        try:
            fig, ax = plt.subplots(figsize=(9, 5))
            fig.suptitle(title, fontsize=13, fontweight="bold")

            monthly = [d.get("monthly_sales_raw", 0) for d in compare_data]
            avg_store = [d.get("avg_per_store_raw", 0) for d in compare_data]

            bars1 = ax.bar(x - w / 2, monthly, w, label="월매출", color=loc_colors, alpha=0.85)
            bars2 = ax.bar(x + w / 2, avg_store, w, label="점포당 평균",
                           color=loc_colors, alpha=0.45, hatch="//")

            ax.set_xticks(x)
            ax.set_xticklabels(locations, fontsize=13)
            ax.yaxis.set_major_formatter(FuncFormatter(_억만_formatter))
            ax.set_title("💰 매출 비교", fontsize=13, fontweight="bold", pad=8)
            ax.legend(fontsize=10)
            ax.spines[["top", "right"]].set_visible(False)

            for bars in [bars1, bars2]:
                for bar in bars:
                    h = bar.get_height()
                    if h > 0:
                        ax.text(
                            bar.get_x() + bar.get_width() / 2, h,
                            _억만_label(h), ha="center", va="bottom", fontsize=9, color="#475569",
                        )

            plt.tight_layout()
            charts.append(_fig_to_base64(fig))
        except Exception:
            pass

        # ── 차트2: 점포 지표 비교 ────────────────────────────
        try:
            open_rates = [d.get("open_rate_pct", 0) for d in compare_data]
            close_rates = [d.get("close_rate_pct", 0) for d in compare_data]
            has_store = any(r > 0 for r in open_rates + close_rates)

            if has_store:
                fig, ax = plt.subplots(figsize=(9, 5))
                fig.suptitle(title, fontsize=13, fontweight="bold")

                bars3 = ax.bar(x - w / 2, open_rates, w, label="개업률", color="#2ecc71", alpha=0.85)
                bars4 = ax.bar(x + w / 2, close_rates, w, label="폐업률", color="#e74c3c", alpha=0.85)

                ax.set_xticks(x)
                ax.set_xticklabels(locations, fontsize=13)
                ax.set_title("🏪 점포 지표 비교", fontsize=13, fontweight="bold", pad=8)
                ax.set_ylabel("%", fontsize=11)
                ax.legend(fontsize=10)
                ax.spines[["top", "right"]].set_visible(False)

                for bars in [bars3, bars4]:
                    for bar in bars:
                        h = bar.get_height()
                        if h > 0:
                            ax.text(
                                bar.get_x() + bar.get_width() / 2, h,
                                f"{h:.1f}%", ha="center", va="bottom", fontsize=10, color="#475569",
                            )

                plt.tight_layout()
                charts.append(_fig_to_base64(fig))
        except Exception:
            pass

        return charts

    except Exception:
        return []
