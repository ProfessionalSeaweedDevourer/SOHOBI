# 대화 히스토리 에이전트 주입 구현 계획

## Context

현재 `session["history"]`(Semantic Kernel ChatHistory)에 매 턴마다 user/assistant 메시지가 누적되지만,
`orchestrator.run()` → `agent.generate_draft()` 호출 시 이 히스토리가 전달되지 않는다.
결과적으로 "아까 그 얘기에 대해 재무 시뮬레이션 해줘" 같은 선행 맥락 참조 질의가 에이전트에게
무의미한 빈 문맥으로 도달한다.

**목표**: 최근 N 턴을 각 에이전트의 ChatHistory에 주입해 멀티턴 맥락 참조를 가능하게 한다.

---

## 구현 방침

### 슬라이딩 윈도우 (마지막 6개 메시지 = 최대 3턴)

히스토리 전체를 주입하면 토큰 폭발 위험이 있다. 세션 TTL 24시간 동안 누적 시
수십 턴이 쌓일 수 있으므로, **직전 3턴(user+assistant 쌍 3개, 메시지 6개)** 만 잘라 주입한다.

### 주입 형태: ChatHistory 메시지로 직접 삽입

기존에 `profile`, `retry_prompt`는 텍스트로 prepend한다.
히스토리는 LLM의 멀티턴 대화 포맷(user/assistant 교번)을 그대로 활용하는 것이
자연스럽고 효과적이다.

각 에이전트 내부 ChatHistory 구성 순서:

```
system: [에이전트 시스템 프롬프트]
user:   [턴 N-2 질문]
assistant: [턴 N-2 응답]
user:   [턴 N-1 질문]
assistant: [턴 N-1 응답]
user:   [현재 질문]   ← 기존 코드
```

---

## 수정 대상 파일 (6개)

| 파일 | 수정 내용 |
|------|----------|
| `integrated_PARK/session_store.py` | `get_recent_history(history, n=6)` 헬퍼 추가 |
| `integrated_PARK/api_server.py` | `orchestrator.run()` 호출 시 `history=session["history"]` 전달 |
| `integrated_PARK/orchestrator.py` | `run()` 시그니처에 `history` 추가, `agent.generate_draft()` 전달 |
| `integrated_PARK/agents/admin_agent.py` | `generate_draft()` 히스토리 주입 |
| `integrated_PARK/agents/legal_agent.py` | `generate_draft()` 히스토리 주입 |
| `integrated_PARK/agents/location_agent.py` | `generate_draft()` 히스토리 주입 |
| `integrated_PARK/agents/finance_agent.py` | 최종 explanation 단계에만 주입 (파라미터 추출 단계 제외) |

Sign-off 에이전트는 수정 불필요 (draft 품질 평가 목적, 히스토리 무관).

---

## 세부 구현

### 1. `session_store.py` — 헬퍼 함수 추가

```python
def get_recent_history(history: ChatHistory, n: int = 6) -> list[dict]:
    """히스토리에서 최근 n개 메시지(user/assistant만)를 [{role, content}] 형태로 반환."""
    msgs = [
        {"role": m.role.value.lower(), "content": str(m.content)}
        for m in history.messages
        if m.role.value.lower() in ("user", "assistant")
    ]
    return msgs[-n:]  # 마지막 n개
```

### 2. `api_server.py` — orchestrator 호출 시 history 전달

```python
# 기존 (line ~160)
result = await orchestrator.run(
    domain=domain,
    question=req.question,
    profile=session["profile"],
    session_id=sid,
    max_retries=req.max_retries,
    current_params=params,
)

# 변경 후
from session_store import get_recent_history

result = await orchestrator.run(
    domain=domain,
    question=req.question,
    profile=session["profile"],
    session_id=sid,
    prior_history=get_recent_history(session["history"]),  # ← 추가
    max_retries=req.max_retries,
    current_params=params,
)
```

> 타이밍 주의: `session["history"].add_user_message(req.question)`은 orchestrator 호출 **전** 이 아니라 **후**에 실행되므로, 전달되는 히스토리에는 현재 질문이 포함되지 않는다 (중복 없음).

### 3. `orchestrator.py` — 시그니처 및 전달

```python
async def run(
    domain: ...,
    question: str,
    profile: str = "",
    session_id: str = "",
    prior_history: list[dict] | None = None,  # ← 추가
    max_retries: int = 3,
    current_params: dict | None = None,
) -> dict:
    ...
    raw = await agent.generate_draft(
        question=question,
        retry_prompt=retry_prompt,
        profile=profile,
        prior_history=prior_history,  # ← 추가
        **extra,
    )
```

### 4. 일반 에이전트 3종 (admin, legal, location) — 공통 패턴

```python
async def generate_draft(
    self,
    question: str,
    retry_prompt: str = "",
    profile: str = "",
    prior_history: list[dict] | None = None,  # ← 추가
) -> str:
    ch = ChatHistory()
    ch.add_system_message(SYSTEM_PROMPT)

    # 히스토리 주입 (선행 턴)
    for msg in (prior_history or []):
        if msg["role"] == "user":
            ch.add_user_message(msg["content"])
        elif msg["role"] == "assistant":
            ch.add_assistant_message(msg["content"])

    # 현재 질문 (기존 로직 유지)
    user_msg = question
    if profile:
        user_msg = _PROFILE_CONTEXT.format(profile=profile) + user_msg
    if retry_prompt:
        user_msg = _RETRY_PREFIX.format(retry_prompt=retry_prompt) + user_msg
    ch.add_user_message(user_msg)

    response = await service.get_chat_message_content(ch, ...)
    return str(response)
```

### 5. `finance_agent.py` — explanation 단계에만 주입

재무 에이전트는 내부에 3단계 LLM 파이프라인이 있다:
1. **파라미터 추출** (단일 질문 → JSON): 히스토리 불필요 (수치 추출 목적)
2. **시뮬레이션 계산** (Python 로직): LLM 아님
3. **결과 설명 생성**: 히스토리 주입 적합

3단계 explanation 프롬프트 조합 시 `prior_history`를 동일 방식으로 주입한다.

---

## 검증 방법

```bash
# 1. 백엔드 실행
cd integrated_PARK && .venv/bin/python3 api_server.py

# 2. 1턴: 창업자 프로필 설정 질문
curl -s -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"question": "서울 마포구에 테이크아웃 카페를 창업하려고 해. 초기 자본금은 5000만원이야."}' \
  | python3 -m json.tool | grep session_id

# 3. 2턴: 선행 맥락 참조 질문 (session_id 이어서)
curl -s -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"question": "아까 그 카페 기준으로 재무 시뮬레이션 해줘", "session_id": "<위 ID>"}' \
  | python3 -m json.tool

# 기대 결과: 재무 에이전트가 마포구·테이크아웃·5000만원을 맥락으로 활용한 응답 반환
```

---

## 주의 사항

- `prior_history`가 `None`일 때(첫 질문, 세션 없음)는 기존 동작과 동일 — 하위 호환성 유지
- 슬라이딩 윈도우 `n=6`은 상수로 관리, 추후 조정 용이하게 `session_store.py` 상단에 `HISTORY_WINDOW = 6` 정의
- 재시도(retry) 루프에서는 히스토리가 반복 주입되지 않도록 orchestrator의 retry 루프 내 `prior_history`를 첫 호출에서만 전달하고 retry 시는 그대로 유지 (이미 LLM이 맥락을 가진 상태이므로 문제 없음)
