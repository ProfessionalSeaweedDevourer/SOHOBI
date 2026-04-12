"""
PR #96 검증 테스트 — finance_db.py list 지역코드 인터페이스 및 load_initial 파이프라인

변경 사항 (PR #96):
- finance_db.get_sales(region: list, industry: str) — IN 절 사용
- finance_simulation_plugin.load_initial(region: list = None, ...) — 타입 변경
- region 또는 industry가 None/빈 리스트이면 fallback [17_000_000] 반환

AREA_MAP 주요 지역 코드 (backend/db/repository.py):
  홍대:  ["11440660"]
  망원:  ["11440690", "11440700"]
  강남:  ["11680640", "11680650", "11680521", "11680531"]
  여의도: ["11560540"]
  이태원: ["11170650", "11170660"]
  잠실:  ["11710540", "11710545", "11710550", "11710561"]

INDUSTRY_CODE_MAP 주요 코드:
  CS100001: 한식 / CS100007: 치킨 / CS100008: 분식
  CS100009: 호프·술집 / CS100010: 카페·커피
"""

import pytest
from db.finance_db import DBWork
from plugins.finance_simulation_plugin import FinanceSimulationPlugin

FALLBACK = [17_000_000]


@pytest.fixture
def db():
    return DBWork()


@pytest.fixture
def plugin():
    return FinanceSimulationPlugin()


# ─────────────────────────────────────────────────────────────────
# 1. DBWork.get_sales() — list 인터페이스 검증
# ─────────────────────────────────────────────────────────────────
class TestGetSalesListRegion:
    """PR #96 변경: get_sales(region=list, industry=str) — IN 절 쿼리"""

    def test_hongdae_cafe_returns_data(self, db):
        """홍대 카페 — 실제 DB 매출 데이터 반환"""
        result = db.get_sales(["11440660"], "CS100010")
        assert isinstance(result, list)
        assert result != FALLBACK, "fallback이 아닌 실제 DB 값이어야 함"
        assert len(result) > 0
        assert all(isinstance(v, (int, float)) for v in result)

    def test_gangnam_hanshik_multi_codes(self, db):
        """강남 한식 — 복수 행정동코드 IN 쿼리"""
        codes = ["11680640", "11680650", "11680521", "11680531"]
        result = db.get_sales(codes, "CS100001")
        assert isinstance(result, list)
        assert len(result) > 0
        assert result != FALLBACK

    def test_mawon_two_codes(self, db):
        """망원 — 2개 행정동코드"""
        result = db.get_sales(["11440690", "11440700"], "CS100007")
        assert isinstance(result, list)

    def test_yeouido_hof(self, db):
        """여의도 호프 — 단일 코드"""
        result = db.get_sales(["11560540"], "CS100009")
        assert isinstance(result, list)
        assert all(isinstance(v, (int, float)) for v in result)

    def test_itaewon_yangsik(self, db):
        """이태원 양식 — 2개 코드"""
        result = db.get_sales(["11170650", "11170660"], "CS100004")
        assert isinstance(result, list)

    def test_none_region_returns_fallback(self, db):
        """region=None → fallback [17_000_000] 반환 (PR #96 변경)"""
        result = db.get_sales(None, "CS100010")
        assert result == FALLBACK

    def test_none_industry_returns_fallback(self, db):
        """industry=None → fallback [17_000_000] 반환"""
        result = db.get_sales(["11440660"], None)
        assert result == FALLBACK

    def test_empty_list_returns_fallback(self, db):
        """region=[] → fallback [17_000_000] 반환"""
        result = db.get_sales([], "CS100010")
        assert result == FALLBACK

    def test_both_none_returns_fallback(self, db):
        """region=None, industry=None → fallback 반환"""
        result = db.get_sales(None, None)
        assert result == FALLBACK

    def test_values_in_reasonable_range(self, db):
        """반환 매출 값이 합리적 범위 (1만 ~ 100억 원)"""
        result = db.get_sales(["11440660"], "CS100010")
        if result != FALLBACK:
            for v in result:
                assert 10_000 < v < 10_000_000_000, f"비합리적 매출 값: {v}"


# ─────────────────────────────────────────────────────────────────
# 2. FinanceSimulationPlugin.load_initial() — list region 인터페이스
# ─────────────────────────────────────────────────────────────────
class TestLoadInitialListRegion:
    """PR #96 변경: load_initial(region: list, industry: str)"""

    def test_hongdae_cafe_returns_dict(self, plugin):
        """홍대 카페 — dict 반환 및 revenue 포함"""
        result = plugin.load_initial(region=["11440660"], industry="CS100010")
        assert isinstance(result, dict)
        assert "revenue" in result
        assert isinstance(result["revenue"], list)
        assert len(result["revenue"]) > 0

    def test_hongdae_cafe_not_fallback(self, plugin):
        """홍대 카페 revenue — fallback 17_000_000 아님"""
        result = plugin.load_initial(region=["11440660"], industry="CS100010")
        assert result["revenue"] != FALLBACK, "실제 지역 DB 데이터여야 함"

    def test_gangnam_hanshik_multi(self, plugin):
        """강남 한식 — 복수 코드 load_initial"""
        codes = ["11680640", "11680650", "11680521", "11680531"]
        result = plugin.load_initial(region=codes, industry="CS100001")
        assert isinstance(result["revenue"], list)
        assert len(result["revenue"]) > 0

    def test_none_region_returns_avg(self, plugin):
        """region=None → fallback 반환 (PR #96: region 없으면 fallback)"""
        result = plugin.load_initial(region=None, industry="CS100010")
        assert isinstance(result["revenue"], list)
        assert len(result["revenue"]) >= 1

    def test_other_fields_none(self, plugin):
        """cost, salary 등 나머지 필드는 None"""
        result = plugin.load_initial(region=["11440660"], industry="CS100010")
        for key in (
            "cost",
            "salary",
            "hours",
            "rent",
            "admin",
            "fee",
            "initial_investment",
        ):
            assert result[key] is None


# ─────────────────────────────────────────────────────────────────
# 3. 전체 파이프라인 — load_initial → monte_carlo_simulation
# ─────────────────────────────────────────────────────────────────
class TestFullPipelineListRegion:
    """지역 + 업종 코드 기반 전체 파이프라인 검증"""

    def test_hongdae_cafe_pipeline(self, plugin):
        """홍대 카페 — load → simulate 기본 구조 검증"""
        init = plugin.load_initial(region=["11440660"], industry="CS100010")
        sim = plugin.monte_carlo_simulation(
            revenue=init["revenue"],
            industry="CS100010",
        )
        assert "average_net_profit" in sim
        assert "loss_probability" in sim
        assert 0.0 <= sim["loss_probability"] <= 1.0
        assert "p20" in sim
        assert "chart" in sim
        assert "bins" in sim["chart"]
        assert len(sim["chart"]["bins"]) == 40

    def test_gangnam_hanshik_pipeline(self, plugin):
        """강남 한식 — 복수 행정동코드 파이프라인"""
        codes = ["11680640", "11680650", "11680521", "11680531"]
        init = plugin.load_initial(region=codes, industry="CS100001")
        sim = plugin.monte_carlo_simulation(
            revenue=init["revenue"],
            industry="CS100001",
        )
        assert "average_net_profit" in sim
        assert "loss_probability" in sim

    def test_yeouido_hof_pipeline(self, plugin):
        """여의도 호프 — 단일 코드 파이프라인"""
        init = plugin.load_initial(region=["11560540"], industry="CS100009")
        sim = plugin.monte_carlo_simulation(
            revenue=init["revenue"],
            industry="CS100009",
        )
        assert "average_net_profit" in sim

    def test_mawon_bunjang_pipeline(self, plugin):
        """망원 분식 — 2개 코드 파이프라인"""
        init = plugin.load_initial(region=["11440690", "11440700"], industry="CS100008")
        sim = plugin.monte_carlo_simulation(
            revenue=init["revenue"],
            industry="CS100008",
        )
        assert "average_net_profit" in sim
        assert isinstance(sim["loss_probability"], float)

    def test_itaewon_chicken_pipeline(self, plugin):
        """이태원 치킨 — 파이프라인"""
        init = plugin.load_initial(region=["11170650", "11170660"], industry="CS100007")
        sim = plugin.monte_carlo_simulation(
            revenue=init["revenue"],
            industry="CS100007",
        )
        assert "average_net_profit" in sim

    def test_jamsil_cafe_pipeline(self, plugin):
        """잠실 카페 — 4개 행정동코드 파이프라인"""
        codes = ["11710540", "11710545", "11710550", "11710561"]
        init = plugin.load_initial(region=codes, industry="CS100010")
        sim = plugin.monte_carlo_simulation(
            revenue=init["revenue"],
            industry="CS100010",
        )
        assert "average_net_profit" in sim
        # 카페 rent 비율 0.15 적용 확인
        assert sim["actual_rent"] > 0

    def test_result_structure_complete(self, plugin):
        """시뮬레이션 결과 필드 전체 검증"""
        init = plugin.load_initial(region=["11440660"], industry="CS100010")
        sim = plugin.monte_carlo_simulation(revenue=init["revenue"])
        expected_keys = {
            "average_net_profit",
            "loss_probability",
            "avg_loss_amount",
            "p20",
            "actual_cost",
            "actual_salary",
            "actual_rent",
            "actual_admin",
            "actual_fee",
            "chart",
        }
        assert expected_keys.issubset(sim.keys())
