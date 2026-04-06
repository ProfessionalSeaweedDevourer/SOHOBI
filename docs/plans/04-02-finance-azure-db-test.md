# 재무 시뮬레이션 Azure DB 연결 테스트 계획

## Context

`finance_simulation_plugin.py`의 `load_initial()` 메서드가 Azure PostgreSQL(`sangkwon_sales` 테이블)에서 매출 데이터를 정상적으로 가져오는지 검증해야 한다. 최근 Azure DB가 새로 연결되었으나 `FinanceSimulationPlugin` 전용 테스트가 전혀 없는 상태이므로, DB 레이어부터 전체 파이프라인까지 단계별 테스트를 신규 작성한다.

기존 테스트 패턴: `integrated_PARK/tests/conftest.py`가 `.env` 자동 로드 + `sys.path` 세팅을 처리하므로 동일 패턴 재사용.

---

## 핵심 파일

| 파일 | 역할 |
|------|------|
| `integrated_PARK/db/finance_db.py` | `DBWork` 클래스 — Azure PG 직접 연결 |
| `integrated_PARK/plugins/finance_simulation_plugin.py` | `load_initial()` → `DBWork` 호출 |
| `integrated_PARK/tests/conftest.py` | pytest 공통 설정 (`.env` 로드, sys.path) |
| `integrated_PARK/tests/test_legal_agent.py` | 기존 테스트 패턴 참조 |

**신규 생성 파일:**
- `integrated_PARK/tests/test_finance_db.py` — DBWork 단위 테스트
- `integrated_PARK/tests/test_finance_plugin.py` — load_initial + 파이프라인 통합 테스트

---

## 구현 계획

### 1단계: `test_finance_db.py` — DBWork 단위 테스트

```python
# integrated_PARK/tests/test_finance_db.py
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

    def test_value_is_not_fallback(self):
        """기본값 17000000이 아닌 실제 DB 값인지 확인"""
        result = DBWork().get_average_sales()
        # 실제 DB가 연결됐다면 17000000과 다를 가능성이 높음
        # (테스트는 값이 유효한 범위인지 확인: 1만 ~ 1억)
        val = float(result[0])
        assert 10_000 < val < 100_000_000

class TestGetSales:
    def test_no_filter_returns_list(self):
        """필터 없이 전체 조회"""
        result = DBWork().get_sales(None, None)
        assert isinstance(result, list)

    def test_industry_filter_korean(self):
        """업종 코드 CS100001(한식) 필터링"""
        result = DBWork().get_sales(None, "CS100001")
        assert isinstance(result, list)
        # 서울 전체 한식 데이터가 있어야 함
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
        # 빈 리스트여야 함

    def test_values_are_numeric(self):
        """반환 값이 숫자형인지 확인"""
        result = DBWork().get_sales(None, "CS100001")
        if result:
            assert all(isinstance(v, (int, float)) for v in result)
```

### 2단계: `test_finance_plugin.py` — load_initial + 파이프라인 통합 테스트

```python
# integrated_PARK/tests/test_finance_plugin.py
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
        """인자 없을 때 DB 평균 매출 반환"""
        result = plugin.load_initial()
        assert len(result["revenue"]) >= 1
        assert result["revenue"][0] != 14_000_000  # fallback 아님

    def test_with_industry_returns_filtered(self, plugin):
        """업종 코드 전달 시 필터된 매출 반환"""
        result = plugin.load_initial(industry="CS100001")
        assert len(result["revenue"]) > 0

    def test_with_region_and_industry(self, plugin):
        """지역 + 업종 코드 모두 전달"""
        result = plugin.load_initial(region="1168010100", industry="CS100001")
        # 강남구 일원동 한식 — 데이터 있을 수 있음
        assert isinstance(result["revenue"], list)

    def test_other_fields_are_none(self, plugin):
        """cost, salary 등 나머지 필드는 None 이어야 함"""
        result = plugin.load_initial()
        for key in ("cost", "salary", "hours", "rent", "admin", "fee", "initial_investment"):
            assert result[key] is None

class TestFullPipeline:
    def test_load_then_simulate(self, plugin):
        """load_initial → monte_carlo_simulation 전체 파이프라인"""
        init = plugin.load_initial()
        sim = plugin.monte_carlo_simulation(
            revenue=init["revenue"],
            industry="CS100001",
        )
        assert "average_net_profit" in sim
        assert "loss_probability" in sim
        assert 0.0 <= sim["loss_probability"] <= 1.0
        assert "chart" in sim
        assert "bins" in sim["chart"]

    def test_simulate_with_cafe_industry(self, plugin):
        """카페 업종으로 파이프라인 실행"""
        init = plugin.load_initial(industry="CS100010")
        sim = plugin.monte_carlo_simulation(
            revenue=init["revenue"],
            industry="CS100010",
        )
        # 카페는 rent 비율이 높음 (0.15)
        assert sim["actual_rent"] > 0
        assert "average_net_profit" in sim
```

### 3단계: 실행 명령

```bash
cd integrated_PARK

# DB 연결 단위 테스트만 먼저 확인
.venv/bin/python -m pytest tests/test_finance_db.py -v

# 플러그인 통합 테스트
.venv/bin/python -m pytest tests/test_finance_plugin.py -v

# 전체 finance 테스트
.venv/bin/python -m pytest tests/test_finance_db.py tests/test_finance_plugin.py -v

# API end-to-end (백엔드 실행 중일 때)
curl -s -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"question": "강남구 한식당 월 매출 기반으로 재무 시뮬레이션 해줘", "domain": "finance"}'
```

### 4단계: docs/plans 저장

`docs/plans/2026-04-02-finance-db-test-plan.md`에 동일 내용 저장 (CLAUDE.md 규칙).

---

## 검증 기준

| 항목 | 기대 결과 |
|------|-----------|
| `DBWork._get_connection()` | 예외 없이 연결 성공 |
| `get_average_sales()` | `[양수 float]` 반환, 기본값 17000000과 다름 |
| `get_sales(None, "CS100001")` | 비어있지 않은 숫자 리스트 반환 |
| `load_initial()` | revenue 필드에 DB 값, 나머지 None |
| `load_initial(industry="CS100001")` | 업종 필터 적용된 revenue 반환 |
| 전체 파이프라인 | `average_net_profit`, `loss_probability`, `chart.bins` 모두 존재 |

---

## 주의 사항

- `conftest.py`가 `.env` 로드를 처리하므로 `PG_*` 환경변수는 별도 설정 불필요
- `DBWork`는 연결 풀 미사용 — 테스트마다 새 연결 생성 (느릴 수 있음)
- `get_sales(None, None)` 은 전체 테이블 조회이므로 데이터가 많으면 느림 — 테스트에서 리스트 길이만 확인
- Azure DB 방화벽 설정으로 로컬 IP가 허용되어 있어야 연결 가능
