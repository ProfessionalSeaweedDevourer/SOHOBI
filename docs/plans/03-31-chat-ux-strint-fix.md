# 채팅 UX 개선 및 str/int 오류 수정 플랜

## Context
현재 채팅 UX의 두 가지 문제:
1. 사용자 질문이 API 완료 후에야 화면에 표시 → 최악의 경우 오류 발생 시 질문·응답 모두 사라짐
2. SSE `error` 이벤트와 네트워크 예외 모두 채팅 메시지가 아닌 별도 배너로만 표시(혹은 무시), UX 단절

추가로 로그에서 자주 등장하는 `str`/`int` 관련 TypeError는 seoul_commercial_plugin.py와 location_agent.py에서 DB/API 값을 직접 `int()`/`float()`로 변환하는 코드에서 발생.

---

## 변경 파일 목록

| 파일 | 변경 유형 |
|------|-----------|
| `frontend/src/pages/UserChat.jsx` | 수정 |
| `frontend/src/pages/DevChat.jsx` | 수정 |
| `frontend/src/components/ResponseCard.jsx` | 수정 |
| `frontend/src/utils/errorInterpreter.js` | 신규 |
| `integrated_PARK/plugins/seoul_commercial_plugin.py` | 수정 |
| `integrated_PARK/agents/location_agent.py` | 수정 |

---

## Task 1: 질문 즉시 표시 (UserChat.jsx, DevChat.jsx)

**`handleSubmit` 수정 (두 파일 동일 패턴):**

1. `pendingQuestion` 상태 추가: `const [pendingQuestion, setPendingQuestion] = useState(null);`
2. `handleSubmit` 시작 시 즉시: `setPendingQuestion(question);`
3. 완료·오류 모든 경로에서: `setPendingQuestion(null);`
4. JSX에서 loading spinner 바로 위에 pending bubble 렌더링:

```jsx
{pendingQuestion && (
  <div
    className="self-end max-w-[80%] text-white rounded-2xl rounded-br-sm px-4 py-3 text-sm leading-relaxed"
    style={{ background: "linear-gradient(135deg, var(--brand-blue), var(--brand-teal))" }}
  >
    {pendingQuestion}
  </div>
)}
```

---

## Task 2: 오류 메시지 채팅 버블 표시

### errorInterpreter.js (신규: `frontend/src/utils/errorInterpreter.js`)

```js
export function interpretError(msg) {
  if (!msg) return "오류가 발생했습니다.";
  const m = msg.toLowerCase();
  if (m.includes("content_filter") || m.includes("content filter"))
    return "콘텐츠 정책에 의해 처리할 수 없는 질문입니다. 표현을 바꿔 다시 시도해 주세요.";
  if (m.includes("429") || m.includes("rate limit") || m.includes("too many"))
    return "요청이 너무 많습니다. 잠시 후(30초~1분) 다시 시도해 주세요.";
  if (/http 5\d{2}/.test(m) || m.includes("server error") || m.includes("internal"))
    return "서버 내부 오류가 발생했습니다. 잠시 후 다시 시도해 주세요.";
  if (m.includes("'str'") || m.includes("'int'") || m.includes("unsupported operand") || m.includes("argument must be"))
    return "데이터 처리 중 형식 오류가 발생했습니다. 지역명 또는 수치를 정확히 입력해 주세요.";
  if (m.includes("빈 응답") || m.includes("empty"))
    return "AI가 응답을 생성하지 못했습니다. 잠시 후 다시 시도해 주세요.";
  if (m.includes("재무 시뮬레이션") || m.includes("수치가 질문에 포함"))
    return "재무 시뮬레이션을 위해 예상 매출·재료비·인건비 등 구체적인 금액을 포함해 주세요.";
  if (m.includes("timeout") || m.includes("network") || m.includes("fetch"))
    return "연결에 실패했습니다. 인터넷 연결을 확인하고 다시 시도해 주세요.";
  return `오류가 발생했습니다: ${msg}`;
}
```

### UserChat.jsx, DevChat.jsx 수정

- `import { interpretError } from "../utils/errorInterpreter";` 추가
- **예외(catch 블록):** `setError()` 대신 `setMessages(prev => [...prev, { question, status: "error", draft: interpretError(e.message) }])`
- **SSE error 이벤트:** `onEvent` 콜백 내 `if (eventName === "error")` 분기 추가 → `setMessages()`에 error 메시지 추가 + `setPendingQuestion(null)`
- `error` 상태 변수(`useState(null)`)와 JSX 오류 배너(`{error && <div>...`) 삭제
- `setError(null)` 호출 삭제

### ResponseCard.jsx 수정

`const isEscalated = ...` 아래에 `const isError = status === "error";` 추가.
응답 카드 섹션(`self-start max-w-[90%]`)을 조건부로:

```jsx
{isError ? (
  <div
    className="glass rounded-2xl rounded-tl-sm px-5 py-4 shadow-elevated text-sm border"
    style={{ background: "rgba(239,68,68,0.08)", borderColor: "rgba(239,68,68,0.3)" }}
  >
    <div className="font-semibold mb-1" style={{ color: "var(--grade-c)" }}>⚠ 오류가 발생했습니다</div>
    <div className="text-sm text-foreground">{draft}</div>
  </div>
) : (
  /* 기존 showMeta + glass card + grade-B 배너 코드 그대로 */
)}
```

### DevChat.jsx SignoffPanel 가드

DevChat.jsx에서 `<SignoffPanel .../>` 렌더링 시 `{msg.status !== "error" && <SignoffPanel .../>}` 조건 추가.

---

## Task 3: str/int TypeError 수정

### seoul_commercial_plugin.py

모듈 최상단(imports 직후)에 헬퍼 함수 추가:

```python
def _safe_int(val, default: int = 0) -> int:
    if val is None or val == "":
        return default
    try:
        return int(str(val).replace(",", "").strip())
    except (ValueError, TypeError):
        return default

def _safe_float(val, default: float = 0.0) -> float:
    if val is None or val == "":
        return default
    try:
        return float(str(val).replace(",", "").strip())
    except (ValueError, TypeError):
        return default
```

`get_estimated_sales` (lines 93–98)의 6개 `int()` 호출을 `_safe_int()`로 교체.
`get_store_count` (lines 144–146)의 `int()` → `_safe_int()`, `float()` → `_safe_float()` 교체.

### location_agent.py

`analyze()` 내 lines 256–270:

```python
# 변경 전
monthly_sales = (sales_data.get("summary", {}).get("monthly_sales_krw", 0) if sales_data else 0)
store_count = (store_data.get("summary", {}).get("store_count", 0) if store_data else 0)

# 변경 후 (float/int 강제 변환으로 문자열 방어)
monthly_sales = float(sales_data.get("summary", {}).get("monthly_sales_krw", 0) if sales_data else 0)
store_count = int(store_data.get("summary", {}).get("store_count", 0) if store_data else 0)
```

breakdown 루프 (line 268–270):

```python
s_count = int(store_map.get(s["trdar_name"], {}).get("store_count", 0))
s_sales = float(s.get("monthly_sales_krw", 0))
s["avg_sales_per_store_krw"] = int(s_sales / s_count) if s_count > 0 else 0
```

`compare()` lines 336–338:

```python
monthly = float(ss.get("monthly_sales_krw", 0))
cnt = int(st.get("store_count", 0))
avg = int(monthly / cnt) if cnt > 0 else 0
```

---

## 커밋 순서

1. `integrated_PARK/plugins/seoul_commercial_plugin.py` + `integrated_PARK/agents/location_agent.py`
2. `frontend/src/utils/errorInterpreter.js` (신규)
3. `frontend/src/pages/UserChat.jsx` + `frontend/src/pages/DevChat.jsx` + `frontend/src/components/ResponseCard.jsx`

---

## 검증

```bash
# 백엔드: 오류 유발 쿼리로 SSE error 이벤트 확인
curl -s -N -X POST http://localhost:8000/api/v1/stream \
  -H "Content-Type: application/json" \
  -d '{"question": "테스트", "max_retries": 0}'

# 프론트엔드: npm run dev 후
# 1. 질문 입력 → 즉시 질문 버블 표시 확인
# 2. 서버 종료 상태에서 질문 → 오류 버블 표시 확인
# 3. 상권 질문 (홍대 카페) → str/int 오류 없이 정상 응답 확인
```

---

*작성일: 2026-03-31*
