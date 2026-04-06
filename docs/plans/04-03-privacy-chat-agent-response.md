# 개인정보처리방침 질문 → 안내 에이전트 하드코딩 응답 처리

## Context

현재 개인정보처리방침 관련 질문이 들어오면 `domain_router.py`의 LLM 분류기가 "법" 관련 키워드로 인식해 legal 에이전트로 라우팅되는 경우가 있음. 개인정보처리방침은 이미 `/privacy` 페이지로 별도 운영 중이므로, LLM 호출 없이 ChatAgent가 즉시 링크를 반환하는 것이 적절함.

## 변경 파일

- `integrated_PARK/domain_router.py`
- `integrated_PARK/agents/chat_agent.py`

## 구현 계획

### 1. `domain_router.py` — 개인정보 관련 질문 우선 chat으로 라우팅

`classify()` 함수 맨 앞에 **privacy 조기 반환 로직** 추가 (키워드 매칭·LLM 호출 모두 건너뜀):

```python
_PRIVACY_KEYWORDS = ["개인정보처리방침", "개인정보 처리방침", "개인정보보호정책", "프라이버시 정책", "privacy policy"]

async def classify(question: str) -> dict:
    lower = question
    if any(kw in lower for kw in _PRIVACY_KEYWORDS):
        return {"domain": "chat", "confidence": 1.0, "reasoning": "개인정보처리방침 질문 — 안내 에이전트로 라우팅"}
    result = _keyword_classify(question)
    return result if result else await _llm_classify(question)
```

### 2. `agents/chat_agent.py` — `generate_draft()` 상단에 하드코딩 응답 삽입

LLM 호출 전, 질문에 개인정보처리방침 키워드가 있으면 즉시 고정 문자열 반환:

```python
_PRIVACY_KEYWORDS = ["개인정보처리방침", "개인정보 처리방침", "개인정보보호정책", "프라이버시 정책", "privacy policy"]

_PRIVACY_RESPONSE = (
    "SOHOBI 개인정보처리방침은 아래 링크에서 확인하실 수 있습니다.\n\n"
    "👉 [개인정보처리방침 보기](/privacy)\n\n"
    "추가로 궁금하신 점이 있으시면 말씀해 주세요!"
)

class ChatAgent:
    async def generate_draft(self, question, retry_prompt="", profile="", prior_history=None) -> str:
        if any(kw in question for kw in _PRIVACY_KEYWORDS):
            return _PRIVACY_RESPONSE
        # ... 기존 LLM 호출 로직 ...
```

## 검증

1. 백엔드 실행: `cd integrated_PARK && .venv/bin/python3 api_server.py`
2. 개인정보 관련 질문 테스트:
   ```bash
   curl -s -X POST http://localhost:8000/api/v1/query \
     -H "Content-Type: application/json" \
     -d '{"question": "개인정보처리방침 어디서 볼 수 있나요?"}' | python3 -m json.tool
   ```
   - 예상: `domain: "chat"`, `draft`에 `/privacy` 링크 포함, LLM 호출 없음 (빠른 응답)
3. 정상 법무 질문이 여전히 legal 에이전트로 가는지 확인:
   ```bash
   curl -s -X POST http://localhost:8000/api/v1/query \
     -H "Content-Type: application/json" \
     -d '{"question": "임대차 계약서 보증금 조항 어떻게 써요?"}' | python3 -m json.tool
   ```
   - 예상: `domain: "legal"`
