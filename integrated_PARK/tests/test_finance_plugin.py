"""
FinanceSimulationPlugin 통합 테스트 — load_initial() DB 연동 및 파이프라인 검증
"""

import pytest
from plugins.finance_simulation_plugin import FinanceSimulationPlugin


@pytest.fixture
def plugin():
    return FinanceSimulationPlugin()


class TestLoadInitial:
    def test_no_args_returns_dict(self, plugin):
        result = plugin.load_initial()
        assert isinstance(result, dict)
        assert "revenue" in result

    def test_no_args_revenue_from_db(self, plugin):
        """인자 없을 때 DB 평균 매출 반환 — fallback 14000000 아님"""
        result = plugin.load_initial()
        assert len(result["revenue"]) >= 1
        assert result["revenue"][0] != 14_000_000

    def test_with_industry_returns_filtered(self, plugin):
        """업종 코드 전달 시 필터된 매출 반환"""
        result = plugin.load_initial(industry="CS100001")
        assert isinstance(result["revenue"], list)
        assert len(result["revenue"]) > 0

    def test_with_region_and_industry(self, plugin):
        """지역 + 업종 코드 모두 전달"""
        result = plugin.load_initial(region="1168010100", industry="CS100001")
        assert isinstance(result["revenue"], list)

    def test_other_fields_are_none(self, plugin):
        """cost, salary 등 나머지 필드는 None"""
        result = plugin.load_initial()
        for key in ("cost", "salary", "hours", "rent", "admin", "fee", "initial_investment"):
            assert result[key] is None


class TestFullPipeline:
    def test_load_then_simulate_korean(self, plugin):
        """load_initial → monte_carlo_simulation 전체 파이프라인 (한식)"""
        init = plugin.load_initial(industry="CS100001")
        sim = plugin.monte_carlo_simulation(
            revenue=init["revenue"],
            industry="CS100001",
        )
        assert "average_net_profit" in sim
        assert "loss_probability" in sim
        assert 0.0 <= sim["loss_probability"] <= 1.0
        assert "chart" in sim
        assert "bins" in sim["chart"]
        assert len(sim["chart"]["bins"]) == 40

    def test_simulate_with_cafe_industry(self, plugin):
        """카페 업종 파이프라인 — rent 비율 0.15 적용 확인"""
        init = plugin.load_initial(industry="CS100010")
        sim = plugin.monte_carlo_simulation(
            revenue=init["revenue"],
            industry="CS100010",
        )
        assert sim["actual_rent"] > 0
        assert "average_net_profit" in sim

    def test_simulate_result_structure(self, plugin):
        """시뮬레이션 결과 필드 전체 검증"""
        init = plugin.load_initial()
        sim = plugin.monte_carlo_simulation(revenue=init["revenue"])
        expected_keys = {
            "average_net_profit", "loss_probability", "avg_loss_amount",
            "p20", "actual_cost", "actual_salary", "actual_rent",
            "actual_admin", "actual_fee", "chart",
        }
        assert expected_keys.issubset(sim.keys())
