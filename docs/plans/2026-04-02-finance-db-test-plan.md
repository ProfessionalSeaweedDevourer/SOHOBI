# 재무 시뮬레이션 Azure DB 연결 테스트 계획

## Context

`finance_simulation_plugin.py`의 `load_initial()` 메서드가 Azure PostgreSQL(`sangkwon_sales` 테이블)에서 매출 데이터를 정상적으로 가져오는지 검증한다. Azure DB가 새로 연결되었으나 `FinanceSimulationPlugin` 전용 테스트가 없으므로 DB 레이어부터 전체 파이프라인까지 단계별 테스트를 신규 작성한다.

---

## 신규 테스트 파일

| 파일 | 내용 |
|------|------|
| `integrated_PARK/tests/test_finance_db.py` | `DBWork` 단위 테스트 (연결, get_average_sales, get_sales) |
| `integrated_PARK/tests/test_finance_plugin.py` | `load_initial` + 파이프라인 통합 테스트 |

---

## 테스트 항목

### DBWork 단위 테스트 (`test_finance_db.py`)

| 테스트 | 검증 내용 |
|--------|-----------|
| `test_connection_success` | Azure PG 연결 성공 |
| `test_returns_list` | `get_average_sales()` → `list` 반환 |
| `test_value_is_positive` | 평균 매출이 양수 |
| `test_value_is_reasonable_range` | 1만 ~ 1억 범위 (실제 DB 값 확인) |
| `test_no_filter_returns_list` | `get_sales(None, None)` → 리스트 반환 |
| `test_industry_filter_korean` | CS100001(한식) 필터 → 비어있지 않음 |
| `test_industry_filter_cafe` | CS100010(카페) 필터 → 비어있지 않음 |
| `test_invalid_codes_return_empty` | 잘못된 코드 → 빈 리스트 (예외 아님) |
| `test_values_are_numeric` | 반환 값이 숫자형 |

### 플러그인 통합 테스트 (`test_finance_plugin.py`)

| 테스트 | 검증 내용 |
|--------|-----------|
| `test_no_args_returns_dict` | `load_initial()` → dict 반환 |
| `test_no_args_revenue_from_db` | revenue가 fallback(14000000) 아님 |
| `test_with_industry_returns_filtered` | 업종 코드 전달 시 필터된 매출 |
| `test_with_region_and_industry` | 지역 + 업종 코드 조합 |
| `test_other_fields_are_none` | cost, salary 등 나머지 필드 None |
| `test_load_then_simulate_korean` | load_initial → monte_carlo 전체 파이프라인 |
| `test_simulate_with_cafe_industry` | 카페 업종 rent 비율(0.15) 적용 |
| `test_simulate_result_structure` | 결과 딕셔너리 필드 전체 검증 |

---

## 실행 명령

```bash
cd integrated_PARK

# DB 연결 단위 테스트
.venv/bin/python -m pytest tests/test_finance_db.py -v

# 플러그인 통합 테스트
.venv/bin/python -m pytest tests/test_finance_plugin.py -v

# 전체 finance 테스트
.venv/bin/python -m pytest tests/test_finance_db.py tests/test_finance_plugin.py -v
```

---

## 주의 사항

- `conftest.py`가 `.env` 로드 처리 → `PG_*` 환경변수 별도 설정 불필요
- Azure DB 방화벽에 로컬 IP가 허용되어 있어야 연결 가능
- `DBWork`는 연결 풀 미사용 → 테스트마다 새 연결 생성 (느릴 수 있음)
- `get_sales(None, None)`은 전체 테이블 조회 → 리스트 길이만 확인
