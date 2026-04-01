# 세션 컨텍스트 전달 구현 — adm_codes + business_type

**날짜:** 2026-04-01
**브랜치:** PARK
**작성자:** PARK (EJP)

---

## 배경 및 목적

재무 팀원 제안: 에이전트 응답 생성에 사용된 지역·업종 코드를 JSON으로 세션에 보관하고, 이후 모든 도메인 에이전트에 전달하여 재파싱 없이 일관된 DB 호출을 가능하게 한다.

기존 finance agent의 `current_params → updated_params` 패턴을 지역·업종으로 확장하는 것이 핵심이다.

**설계 결정:**
- 프론트엔드는 stateless 원칙을 유지하고, `adm_codes` / `business_type` / `location_name`은 서버 세션(Cosmos DB)에만 저장한다.
- `db/repository.py`는 변경하지 않는다 — 기존 `get_sales(location_name, ...)` API가 내부적으로 O(1) dict lookup으로 adm_codes 변환을 처리하므로, `location_name` 문자열도 함께 보관하여 기존 API를 그대로 활용한다.
- "지역 변경 감지"를 별도 로직으로 구현하지 않는다 — location agent가 호출될 때 LLM 추출값이 있으면 갱신, 없으면 세션값 fallback으로 자연스럽게 처리된다.

---

## 변경 파일 및 내용

### session_store.py

`session["context"]` 필드 신설:

```python
_EMPTY_CONTEXT = {"adm_codes": [], "business_type": "", "location_name": ""}

def _empty_query_session() -> dict:
    return {
        "profile":   "",
        "history":   ChatHistory(),
        "extracted": {},
        "context":   dict(_EMPTY_CONTEXT),  # 신규
    }
```

- `get_query_session()`: Cosmos 문서에 `context` 키 없을 경우(구형 세션) 빈 기본값으로 복원
- `save_query_session()`: `context` 필드를 Cosmos DB에 함께 저장

### orchestrator.py

`run()` 및 `run_stream()` 양쪽에 동일하게 적용:

- 시그니처에 `context: dict | None = None` 추가
- 에이전트 호출 시 `extra["context"] = context` 주입 (모든 도메인)
- location agent 결과에서 `updated_context` 빌드:
  ```python
  if domain == "location" and adm_codes:
      updated_context = dict(context) if context else {}
      updated_context["adm_codes"]     = adm_codes
      updated_context["business_type"] = raw.get("business_type", ...)
      updated_context["location_name"] = raw.get("location_name", ...)
  ```
- 모든 반환 dict에 `"updated_context": updated_context` 포함

### api_server.py

비스트리밍(`/api/v1/query`) 및 스트리밍(`/api/v1/stream`) 양쪽:

- orchestrator 호출 시 `context=session.get("context", {})` 전달
- 응답 후 `session["context"].update(result["updated_context"])` 반영
- `save_query_session()` 에 context가 자동 포함되어 저장

`QueryRequest` 스키마 변경 없음 — context는 순수 서버 관리.

### agents/location_agent.py ★

`generate_draft()`에 context fallback 로직 추가:

```python
ctx = context or {}
locations     = params["locations"] or ([ctx["location_name"]] if ctx.get("location_name") else [])
business_type = params["business_type"] or ctx.get("business_type") or ""
```

반환값 확장:
```python
return {
    "draft":         draft,
    "adm_codes":     adm_codes,
    "type":          mode,
    "business_type": business_type,   # 신규
    "location_name": locations[0] if locations else "",  # 신규
}
```

### agents/finance_agent.py

`generate_draft()`에 `context: dict | None = None` 추가.

explain 프롬프트 앞에 context 블록 주입:
```
[현재 세션 컨텍스트] 분석 지역: 강남구, 업종: 카페
```

효과: "강남구 카페 기준 월매출 목표" 등 구체적 표현을 LLM이 자동 활용.

### agents/legal_agent.py

`generate_draft()`에 `context: dict | None = None` 추가.

시스템 메시지에 context 주입:
```
[창업자 현재 컨텍스트] 지역: 강남구, 업종: 카페
위 컨텍스트를 고려하여 해당 지역·업종에 적합한 법령 정보를 우선 제공하십시오.
```

### agents/admin_agent.py

`generate_draft()`에 `context: dict | None = None` 추가 (세션에서 수행됨).

시스템 메시지에 context 주입 — SeoulCommercial/AdminProcedure/GovSupport 플러그인 호출 시 지역·업종 파라미터 정확도 향상.

---

## 데이터 흐름

```
요청 수신
 → session["context"] 로드 (adm_codes, business_type, location_name)
 → orchestrator.run(context=...)
     ├─ location agent: LLM 추출 → fallback 적용 → DB 쿼리 → context 갱신
     ├─ finance agent:  context를 explain 프롬프트 앞에 주입
     ├─ legal agent:    context를 시스템 메시지에 주입
     └─ admin agent:    context를 시스템 메시지에 주입
 ← result["updated_context"] 반환
 → session["context"] 갱신 후 Cosmos 저장
```

---

## 검증 시나리오

```bash
# 1단계: 상권 질문으로 context 생성
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"question": "강남구 카페 창업 어떤가요?", "session_id": "test-ctx-001"}'
# → result.adm_codes, result.updated_context 확인

# 2단계: 같은 세션에서 재무 질문 (지역/업종 언급 없음)
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"question": "초기 투자 3천만원이면 몇 달 안에 회수 가능한가요?", "session_id": "test-ctx-001"}'
# → 응답에 "강남구 카페" 컨텍스트 반영 확인

# 3단계: 같은 세션에서 법령 질문
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"question": "영업 허가 절차 알려주세요", "session_id": "test-ctx-001"}'
# → 카페·강남구 관련 법령 응답 확인

# 4단계: 지역 변경 테스트
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"question": "마포구로 바꾸면 어떤가요?", "session_id": "test-ctx-001"}'
# → context가 마포구로 갱신되었는지 확인
```

---

## 구현 중 이슈

최초 적용 후 대부분의 파일이 롤백됨(`admin_agent.py` 제외). 동일 변경사항을 재적용하여 완성.

---

## 변경 파일 목록

| 파일 | 변경 유형 |
|------|----------|
| `integrated_PARK/session_store.py` | `context` 필드 추가 |
| `integrated_PARK/orchestrator.py` | `context` 파라미터 추가, `updated_context` 빌드 및 반환 |
| `integrated_PARK/api_server.py` | `context` 전달 및 갱신 (non-stream + stream) |
| `integrated_PARK/agents/location_agent.py` | fallback 로직, 반환값 확장 |
| `integrated_PARK/agents/finance_agent.py` | `context` 파라미터, 프롬프트 주입 |
| `integrated_PARK/agents/legal_agent.py` | `context` 파라미터, 시스템 메시지 주입 |
| `integrated_PARK/agents/admin_agent.py` | `context` 파라미터, 시스템 메시지 주입 |
| `db/repository.py` | 변경 없음 |
