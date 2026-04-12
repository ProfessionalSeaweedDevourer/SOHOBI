# 라우팅 오분류 디버깅 가이드

도메인 라우터(`domain_router.py`)가 질문을 잘못 분류한다는 의심이 들 때 사용하는 로그 기반 분석 워크플로우.

## 워크플로우 요약

```
1. 증상 수집  →  2. 로그 조회  →  3. 오분류 추출  →  4. 코드 추적  →  5. 수정·검증
```

---

## 1단계: 증상 수집

사용자 리포트 또는 재현 가능한 쿼리 사례를 확보한다.

- 어떤 질문이 문제인가?
- 어떤 에이전트가 답했는가 (실제)?
- 어떤 에이전트가 답해야 했는가 (기대)?

---

## 2단계: 로그 조회

```bash
source backend/.env

# 최근 N건 — [domain] [status/grade] 질문 형태로 파싱
curl -s -H "X-API-Key: $API_SECRET_KEY" \
  "$BACKEND_HOST/api/v1/logs?type=queries&limit=50" | python3 -c "
import json, sys
data = json.load(sys.stdin)
for e in data.get('entries', []):
    q = e.get('question', '')
    d = e.get('domain', '')
    status = e.get('status', '')
    grade = e.get('grade', '')
    print(f'[{d}] [{status}/{grade}] {q[:80]}')
"
```

> **인증 키**: `backend/.env`의 `API_SECRET_KEY`

---

## 3단계: 오분류 추출

로그 출력에서 기대 도메인과 실제 도메인이 다른 항목을 찾는다.

```bash
# 예: chat으로 잘못 분류된 행정·지원사업 관련 질문 필터
curl -s -H "X-API-Key: $API_SECRET_KEY" \
  "$BACKEND_HOST/api/v1/logs?type=queries&limit=100" | python3 -c "
import json, sys
data = json.load(sys.stdin)
suspects = []
for e in data.get('entries', []):
    q = e.get('question', '')
    d = e.get('domain', '')
    # 지원금·보조금 키워드 포함인데 chat으로 분류된 항목
    if d == 'chat' and any(kw in q for kw in ['지원', '보조금', '정책자금', '시뮬레이션', '상권분석']):
        suspects.append((e['ts'], d, q[:80]))
for ts, dom, q in suspects:
    print(f'{ts}  [{dom}]  {q}')
"
```

---

## 4단계: 코드 추적

`backend/domain_router.py`의 분류 경로를 따라간다.

### 4a. 키워드 분류 통과 여부 확인

`_keyword_classify` 함수는 두 가지 조건에서 `None`을 반환하고 LLM으로 넘긴다:
- 최고 점수 도메인 키워드 매칭 수 < 2
- 동점인 도메인이 2개 이상

```python
# 로컬에서 직접 테스트:
cd backend
.venv/bin/python3 -c "
from domain_router import _keyword_classify
q = '여기에 오분류된 질문 붙여넣기'
print(_keyword_classify(q))
"
```

`None`이 반환되면 LLM 분류 단계로 넘어간 것이다.

### 4b. LLM 분류 결과 확인

`_SYSTEM_PROMPT` 안의 규칙이 문제인 경우:
- `chat` 정의에 포함된 예시가 너무 광범위한지 확인
- disambiguation 규칙 번호 순서로 훑으며 해당 질문이 어느 규칙에 걸리는지 추적

```python
# LLM 분류만 단독 실행:
cd backend
.venv/bin/python3 -c "
import asyncio
from domain_router import _llm_classify
q = '여기에 오분류된 질문 붙여넣기'
print(asyncio.run(_llm_classify(q)))
"
```

### 4c. ChatAgent 도달 후 동작 확인

라우터가 `chat`으로 분류했어도 ChatAgent 내부에서 전문 영역을 직접 답하는 경우:
- `agents/chat_agent.py`의 `_detect_specialist()` 함수가 해당 키워드를 포함하는지 확인
- `_USAGE_PATTERNS` 예외 처리가 오발동하는지 확인

---

## 5단계: 수정·검증

| 원인 | 수정 위치 | 수정 내용 |
|------|-----------|-----------|
| 키워드 매칭 수 부족 | `domain_router.py` `KEYWORDS` | 해당 도메인 키워드 추가 |
| LLM 오판단 | `domain_router.py` `_SYSTEM_PROMPT` | disambiguation 규칙 추가·수정 |
| ChatAgent가 직접 답변 | `agents/chat_agent.py` `_SPECIALIST_PATTERNS` | 해당 도메인 키워드 추가 |

수정 후 검증:

```bash
source backend/.env

# 오분류됐던 질문 재테스트 (배포 후)
curl -s -X POST "$BACKEND_HOST/api/v1/query" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_SECRET_KEY" \
  -d '{"question": "오분류됐던 질문"}' \
  | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('domain'), d.get('draft','')[:80])"
```

---

## 실제 사례: 2026-04-08 IT 스타트업 지원금 오분류

**증상**: `"26세 남성인데 IT 스타트업 관련해서 지원받을 수 있는 거 있어?"` → `[chat]` 분류, ChatAgent가 직접 답변

**추적 결과**:
1. 키워드 매칭 0개 → LLM 분류 진입
2. LLM이 "IT 스타트업"을 `chat` 예시 "지원하지 않는 업종 문의"로 판단
3. ChatAgent가 시스템 프롬프트 리디렉션 지시를 무시하고 직접 답변

**수정**:
- `domain_router.py` `KEYWORDS["admin"]` — `"지원받"`, `"지원 신청"` 등 8개 추가
- `domain_router.py` `_SYSTEM_PROMPT` — admin 주석에 "업종 무관" 명시, disambiguation 규칙 #6 추가, chat 예시를 상권분석 DB 커버리지 문의로 한정
- `agents/chat_agent.py` — `_detect_specialist()` 추가 (Layer 2 방어)

**PR**: ProfessionalSeaweedDevourer/SOHOBI#220
