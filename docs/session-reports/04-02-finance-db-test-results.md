# 재무 시뮬레이션 Azure DB 연결 테스트 결과 리포트

**날짜**: 2026-04-02
**브랜치**: PARK
**대상**: `integrated_PARK/db/finance_db.py` (DBWork), `integrated_PARK/plugins/finance_simulation_plugin.py` (FinanceSimulationPlugin)

---

## 1. 테스트 목적

Azure PostgreSQL DB가 새로 연결된 이후, `FinanceSimulationPlugin.load_initial()`이 `DBWork`를 통해 `sangkwon_sales` 테이블에서 매출 데이터를 정상적으로 조회하는지 검증한다.

---

## 2. 테스트 환경

| 항목 | 내용 |
|------|------|
| Python | 3.12.0 |
| pytest | 9.0.2 |
| DB | Azure PostgreSQL Flexible Server (`sohobi-db-prod.postgres.database.azure.com`) |
| DB명 | `sohobi` |
| 테이블 | `sangkwon_sales` |
| 실행 환경 | 로컬 (integrated_PARK/.venv) |

---

## 3. 테스트 파일

| 파일 | 항목 수 | 설명 |
|------|---------|------|
| `integrated_PARK/tests/test_finance_db.py` | 9 | DBWork 단위 테스트 |
| `integrated_PARK/tests/test_finance_plugin.py` | 8 | load_initial + 파이프라인 통합 테스트 |

---

## 4. 테스트 결과 요약

```
============================== 17 passed in 4.17s ==============================
```

| 파일 | 결과 | 통과 | 실패 |
|------|------|------|------|
| test_finance_db.py | PASS | 9 | 0 |
| test_finance_plugin.py | PASS | 8 | 0 |
| **합계** | **PASS** | **17** | **0** |

---

## 5. 세부 테스트 결과

### 5-1. DBWork 단위 테스트 (`test_finance_db.py`)

| 테스트 | 결과 | 비고 |
|--------|------|------|
| `test_connection_success` | PASS | Azure PG SSL 연결 성공 |
| `test_returns_list` | PASS | `get_average_sales()` → `list` 반환 확인 |
| `test_value_is_positive` | PASS | 반환 값 양수 확인 |
| `test_value_is_reasonable_range` | PASS | 실제 평균 매출 약 14억 원 (1만 ~ 100억 범위) |
| `test_no_filter_returns_list` | PASS | 필터 없이 전체 조회 |
| `test_industry_filter_korean` | PASS | CS100001(한식) 필터 → 데이터 존재 |
| `test_industry_filter_cafe` | PASS | CS100010(카페/커피) 필터 → 데이터 존재 |
| `test_invalid_codes_return_empty` | PASS | 잘못된 코드 → 빈 리스트 (예외 없음) |
| `test_values_are_numeric` | PASS | 반환 값 숫자형 확인 |

### 5-2. FinanceSimulationPlugin 통합 테스트 (`test_finance_plugin.py`)

| 테스트 | 결과 | 비고 |
|--------|------|------|
| `test_no_args_returns_dict` | PASS | `load_initial()` dict 반환 |
| `test_no_args_revenue_from_db` | PASS | revenue가 fallback(14,000,000) 아닌 DB 실제 값 |
| `test_with_industry_returns_filtered` | PASS | CS100001 업종 필터 적용 매출 반환 |
| `test_with_region_and_industry` | PASS | 지역 + 업종 코드 복합 필터 |
| `test_other_fields_are_none` | PASS | cost, salary 등 나머지 필드 None |
| `test_load_then_simulate_korean` | PASS | load_initial → monte_carlo 전체 파이프라인 |
| `test_simulate_with_cafe_industry` | PASS | 카페 rent 비율(0.15) 적용 확인 |
| `test_simulate_result_structure` | PASS | 결과 딕셔너리 10개 필드 전체 존재 확인 |

---

## 6. 주요 발견 사항

### DB 연결 확인
Azure PostgreSQL (SSL `require` 모드) 연결이 로컬 환경에서 정상 동작한다.

### 실제 DB 데이터 확인
`get_average_sales()` 반환값이 약 **1,413,253,753원 (약 14억 원)** 으로, `load_initial()` fallback 값(14,000,000)과 명확히 구분된다. DB 데이터는 분기 또는 연간 단위 매출로 추정된다.

> **참고**: `FinanceAgent`는 `monte_carlo_simulation()`에서 이 값을 월 매출 기준으로 사용한다. DB의 `tot_sales_amt` 단위가 월 단위인지 추가 확인 필요.

### 업종 필터 동작 확인
- CS100001 (한식), CS100010 (카페/커피) 모두 `sangkwon_sales` 테이블에서 데이터 조회 성공
- 잘못된 코드 입력 시 예외 없이 빈 리스트 반환 (안전한 폴백)

### 전체 파이프라인 정상 동작
`load_initial()` → `monte_carlo_simulation()` 파이프라인이 4.17초 내에 17개 테스트 전부 통과. `chart.bins` (40개 구간) 포함 시뮬레이션 결과 정상 생성.

---

## 7. 후속 검토 사항

| 항목 | 내용 |
|------|------|
| `tot_sales_amt` 단위 확인 | 월/분기/연간 단위인지 스키마 또는 데이터 원천 문서 확인 |
| `DBWork` 연결 풀링 | 현재 매 호출마다 새 연결 생성 — 고부하 시 병목 가능 |
| `get_sales(None, None)` 성능 | 전체 테이블 조회로 데이터 많을 경우 응답 지연 가능 |
| Azure 방화벽 규칙 | 배포 환경(Container Apps)에서 PG 연결 허용 여부 확인 |

---

## 8. 실행 명령

```bash
cd integrated_PARK
.venv/bin/python -m pytest tests/test_finance_db.py tests/test_finance_plugin.py -v
```
