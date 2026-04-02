"""
DBWork 단위 테스트 — Azure PostgreSQL 연결 및 매출 조회 검증
"""

import pytest
from db.finance_db import DBWork


class TestDBWorkConnection:
    def test_connection_success(self):
        """Azure PG 연결이 성공하는지 확인"""
        db = DBWork()
        conn = db._get_connection()
        assert conn is not None
        conn.close()


class TestGetAverageSales:
    def test_returns_list(self):
        result = DBWork().get_average_sales()
        assert isinstance(result, list)
        assert len(result) == 1

    def test_value_is_positive(self):
        result = DBWork().get_average_sales()
        assert float(result[0]) > 0

    def test_value_is_reasonable_range(self):
        """실제 DB 값인지 확인 (1만 ~ 100억 범위 — 분기/연간 매출 포함)"""
        result = DBWork().get_average_sales()
        val = float(result[0])
        assert 10_000 < val < 10_000_000_000


class TestGetSales:
    def test_no_filter_returns_list(self):
        """필터 없이 전체 조회 — 리스트 반환"""
        result = DBWork().get_sales(None, None)
        assert isinstance(result, list)

    def test_industry_filter_korean(self):
        """업종 코드 CS100001(한식) 필터링 — 서울 한식 데이터 존재"""
        result = DBWork().get_sales(None, "CS100001")
        assert isinstance(result, list)
        assert len(result) > 0

    def test_industry_filter_cafe(self):
        """업종 코드 CS100010(카페/커피) 필터링"""
        result = DBWork().get_sales(None, "CS100010")
        assert isinstance(result, list)
        assert len(result) > 0

    def test_invalid_codes_return_empty(self):
        """존재하지 않는 코드 → 빈 리스트 반환 (예외 아님)"""
        result = DBWork().get_sales("INVALID_REGION", "INVALID_INDUSTRY")
        assert isinstance(result, list)
        assert len(result) == 0

    def test_values_are_numeric(self):
        """반환 값이 숫자형인지 확인"""
        result = DBWork().get_sales(None, "CS100001")
        if result:
            assert all(isinstance(v, (int, float)) for v in result)
