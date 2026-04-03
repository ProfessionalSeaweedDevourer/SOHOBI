# PR #96 검증 계획

## Context

PR #96은 `finance_agent.py`에 지역/업종 추출 기능을 추가하고, 지역 코드(`adm_codes`)를 finance DB 쿼리에 연동하는 변경이다. PR 작성자는 `adm_codes`가 `list`인지 단일 `str`인지 불확실하여 `finance_db.py` / `finance_simulation_plugin.py` 변경 포함 여부를 판단하지 못한 상태로 PR을 열었다.

## 핵심 판단: adm_codes 타입 확인 결과

**`adm_codes`는 항상 `list[str]`이다. → `finance_db.py` / `finance_simulation_plugin.py` 변경 포함해야 함.**

근거:

| 위치 | 증거 |
|------|------|
| `integrated_PARK/db/repository.py` | `AREA_MAP = {"홍대": ["11440660"], ...}` — 모든 값이 리스트 |
| `repository.py` `_get_adm_codes()` | 반환 타입 `-> list`, 기본값 `return []` |
| `orchestrator.py` L80 | `adm_codes: list = []` 타입 주석 |
| `session_store.py` L103 | `_EMPTY_CONTEXT = {"adm_codes": [], ...}` |
| `location_agent.py` L387 | `all_adm_codes = []; all_adm_codes.extend(...)` |
| `tests/test_location_agent.py` | `MagicMock(return_value=["11440660"])` |

단일 `str`로 처리하는 코드 경로 없음.

## PR #96 변경 파일별 판단

### 1. `integrated_PARK/agents/finance_agent.py` ✅ 포함
- `_PARAM_EXTRACT_PROMPT`에 `location`, `business_type` 추출 추가
- `_extract_params()` 반환 타입을 `dict` → `tuple[dict, dict]`으로 변경
  - 두 번째 요소: `{"adm_codes": list | None, "business_type": str | None}`
  - `AREA_MAP.get(location_normalized)` → 리스트 또는 None 반환 (타입 일치)
- `generate_draft()`에서 context에 추출된 지역/업종 병합 후 `load_initial()` 호출

### 2. `integrated_PARK/db/finance_db.py` ✅ 포함
- 기존: `LIKE %s` (단일 str 허용)
- 변경: `IN ({placeholders})` + `region + [industry]` 파라미터 바인딩
- `adm_codes`가 리스트임이 확인되었으므로 포함 타당

### 3. `integrated_PARK/plugins/finance_simulation_plugin.py` ✅ 포함
- `load_initial(region: str = None)` → `load_initial(region: list = None)`
- 타입 힌트만 변경, `adm_codes`가 리스트임이 확인되었으므로 포함 타당

## 데이터 흐름 검증

```
질문 입력
  └→ finance_agent._extract_params()
       ├→ LLM으로 location (str) 추출
       ├→ AREA_MAP.get(location) → list[str] 또는 None (adm_codes)
       └→ context = {"adm_codes": list|None, "business_type": str|None}
            └→ generate_draft()가 ctx에 병합
                 └→ load_initial(region=list|None, industry=str|None)
                      └→ finance_db.get_sales(region=list, industry=str)
                           └→ IN (?,?) 쿼리로 PostgreSQL 조회
```

## 검증 방법 (로컬 테스트 불가 전제)

### Step 1: 코드 리뷰로 타입 정합성 확인 (완료)
- [x] `adm_codes`가 항상 `list[str]`임 확인
- [x] PR diff에서 list 처리 로직 정합성 확인

### Step 2: PR 머지 후 Azure 배포 환경에서 curl 테스트

```bash
source integrated_PARK/.env

# 지역 포함 질문 — adm_codes 리스트로 DB 쿼리되어야 함
curl -s -X POST "$BACKEND_HOST/api/v1/query" \
  -H "Content-Type: application/json" \
  -d '{"question": "홍대에서 카페 창업하면 예상 매출이 얼마야?"}' | python3 -m json.tool

# 지역 미포함 질문 — fallback 17000000 반환 확인
curl -s -X POST "$BACKEND_HOST/api/v1/query" \
  -H "Content-Type: application/json" \
  -d '{"question": "카페 창업하면 예상 매출이 얼마야?"}' | python3 -m json.tool
```

### Step 3: 로그로 실제 adm_codes 값 확인

```bash
curl -s "$BACKEND_HOST/api/v1/logs?type=queries&limit=20" | python3 -m json.tool
```

## 확인 기준

| 항목 | 기대값 |
|------|--------|
| 지역 포함 질문 응답 | 실제 DB 매출 데이터 (≈1.4억 원대) |
| 지역 미포함 질문 응답 | fallback 17,000,000 또는 오류 없이 처리 |
| 에러 없음 | `TypeError`, `AttributeError` 없음 |

## 결론

PR 코드 자체 수정 불필요. 세 파일 모두 그대로 포함하여 머지 가능.

단, `_extract_params()` 반환 타입이 tuple로 바뀌었으므로, 호출부 (`generate_draft()`) 에서 언패킹을 정확히 하는지 PR diff에서 한번 더 확인 권장.
