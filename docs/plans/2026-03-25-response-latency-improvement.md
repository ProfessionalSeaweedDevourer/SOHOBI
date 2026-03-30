# 응답속도 개선 계획

## Context

현재 최악 케이스에서 LLM 18회 순차 호출이 발생하여 응답이 느림.
목표: 최악 케이스를 6회 이하로 줄이고, 체감 속도 대폭 개선.

---

## 현황 정오표 (코드 실제 분석 결과)

| 방안 | 제안 내용 | 실제 현황 |
|------|-----------|-----------|
| 방안 2 | 도메인 분류 규칙 기반 전환 | **이미 구현됨** — domain_router.py:31–39에 키워드 매칭 존재. 2개+ 키워드 일치 시 LLM 생략 |
| 방안 3 | 스트리밍 응답 도입 | **이미 구현됨** — `/api/v1/stream` SSE 엔드포인트 존재 (api_server.py:175–258) |
| 방안 1 | Sign-off 내부 재시도 제거 | **유효** — signoff_agent.py:48 max_retries=2 (3회 호출) → 0으로 변경 |
| 방안 4 | Draft에 루브릭 주입 | **유효** — 각 도메인 에이전트 SYSTEM_PROMPT에 required code 기준 추가 |
| 방안 5 | 변수 추출 비동기화 | **유효** — api_server.py:121–129 순차 호출 → asyncio.create_task로 백그라운드 전환 |

---

## 구현 계획

### 작업 1: Sign-off 내부 재시도 제거 + 프롬프트 강화
**효과: 최악 18회 → 6회 (3배 개선)**
**파일**: `integrated_PARK/signoff/signoff_agent.py`

- `max_retries=2` → `max_retries=0` (line 48)
- Sign-off 시스템 프롬프트에 REQUIRED_CODES 목록을 명시적으로 포함
  - 모든 코드(C1–C5 + 도메인별)를 **반드시 passed/warnings/issues 중 하나에 분류**하도록 강제

### 작업 2: Draft 에이전트에 Sign-off 루브릭 주입
**효과: 오케스트레이터 재시도 횟수 감소**
**파일**: 4개 에이전트 (`legal_agent.py`, `admin_agent.py`, `finance_agent.py`, `location_agent.py`)

각 SYSTEM_PROMPT 하단에 체크리스트 추가:
```
[품질 체크리스트 — 반드시 충족]
- C1: 면책 조항 명시
- C2: 전문가 상담 권고
- C3: 정보 최신성 주의 문구
- C4: 사용자 상황 반영
- C5: 요약 또는 결론 포함
- (도메인별 추가 항목)
```

### 작업 3: 변수 추출 백그라운드 처리
**효과: 사용자 응답 즉시 반환**
**파일**: `integrated_PARK/api_server.py`

```python
# 변경 전 (line 121–129)
new_vars = await extract_financial_vars(result["draft"])

# 변경 후
asyncio.create_task(_extract_and_store(session_id, session, result["draft"]))
return JSONResponse(...)  # 즉시 반환
```

### 작업 4 (선택): 프론트엔드 스트리밍 연결
**파일**: `frontend/src/` (API 호출 부분)

- `/api/v1/query` → `/api/v1/stream`으로 전환
- SSE 이벤트 처리 (agent_start → agent_done → signoff_result → complete)
- 첫 글자 1–2초 내 표시로 체감 속도 대폭 개선

---

## 우선순위 및 효과 요약

| 순위 | 작업 | 난이도 | 효과 |
|------|------|--------|------|
| 1 | Sign-off max_retries=0 + 프롬프트 강화 | 쉬움 | 최악 18회 → 6회 |
| 2 | Draft에 루브릭 주입 | 쉬움 | 재시도 감소 |
| 3 | 변수 추출 백그라운드화 | 쉬움 | 응답 즉시 반환 |
| 4 | 프론트엔드 스트리밍 전환 | 보통 | 체감 속도 대폭 개선 |

---

## 수정 대상 파일

- `integrated_PARK/signoff/signoff_agent.py` (line 48, 시스템 프롬프트)
- `integrated_PARK/agents/legal_agent.py` (SYSTEM_PROMPT)
- `integrated_PARK/agents/admin_agent.py` (SYSTEM_PROMPT)
- `integrated_PARK/agents/finance_agent.py` (SYSTEM_PROMPT)
- `integrated_PARK/agents/location_agent.py` (SYSTEM_PROMPT)
- `integrated_PARK/api_server.py` (line 121–129)
- `frontend/src/` (스트리밍 전환, 선택)

---

## 검증 방법

```bash
# 1. API 응답 시간 측정
time curl -s -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"question": "강남구에서 카페 창업하려면 어떤 절차가 필요한가요?"}'

# 2. 스트리밍 확인
curl -s -X POST http://localhost:8000/api/v1/stream \
  -H "Content-Type: application/json" \
  -d '{"question": "테스트"}'

# 3. Sign-off 단독 테스트
curl -s -X POST http://localhost:8000/api/v1/signoff \
  -H "Content-Type: application/json" \
  -d '{"domain": "legal", "draft": "..."}'
```
