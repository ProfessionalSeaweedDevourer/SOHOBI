# 재무 시뮬레이션 차트 프론트엔드 통합 계획

## Context
백엔드(finance_agent, orchestrator, api_server)는 이미 `chart` (base64 PNG)와 `updated_params`를 반환하도록 완성되어 있다.
프론트엔드만 아직 이 데이터를 받아서 렌더링하지 않고 있다. 작업 범위는 순수 프론트엔드 3개 파일 수정이다.

## 현재 상태 (탐색 결과)

### 백엔드 — 이미 완료
- `integrated_PARK/plugins/finance_simulation_plugin.py` → `monte_carlo_simulation()` returns `chart` (base64 PNG or None)
- `integrated_PARK/agents/finance_agent.py` → `generate_draft()` returns `{draft, chart, updated_params}`
- `integrated_PARK/orchestrator.py` → `chart`, `updated_params` 추출해서 최종 dict에 포함
- `integrated_PARK/api_server.py` → 응답에 `chart`, `updated_params` 포함

### 프론트엔드 — 미완료
- `frontend/src/api.js` → `streamQuery`/`sendQuery`가 `current_params`를 받지 않음
- `frontend/src/pages/UserChat.jsx` → `finalResult`에서 `chart`, `updated_params` 미추출, 메시지 state에 미포함
- `frontend/src/pages/DevChat.jsx` → 동일
- `frontend/src/components/ResponseCard.jsx` → `chart` prop 없음, 이미지 렌더링 로직 없음

---

## 구현 계획

### Step 1 — `frontend/src/api.js`
`streamQuery`와 `sendQuery` 함수에 `currentParams` 파라미터 추가, body에 `current_params` 포함.

```js
// streamQuery signature 변경
export async function streamQuery(question, maxRetries = 3, sessionId = null, onEvent, currentParams = null)

// body에 추가
if (currentParams) body.current_params = currentParams;
```

### Step 2 — `frontend/src/pages/UserChat.jsx`

1. `latestParams` state 추가 (`useState(null)`)
2. `handleSubmit`에서 `streamQuery` 호출 시 `currentParams = latestParams` 전달
3. `finalResult`에서 `chart`, `updated_params` 추출 후 메시지 state에 포함
4. `updated_params`가 있으면 `latestParams` 업데이트

```js
// 추가할 state
const [latestParams, setLatestParams] = useState(null);

// streamQuery 호출 변경
await streamQuery(question, 3, sessionId, (eventName, data) => { ... }, latestParams);

// finalResult 처리 변경
setMessages(prev => [...prev, {
  ...기존필드,
  chart: finalResult.chart || null,
}]);
if (finalResult.updated_params) setLatestParams(finalResult.updated_params);
```

### Step 3 — `frontend/src/pages/DevChat.jsx`
UserChat과 동일한 패턴으로 `chart`, `updated_params`, `current_params` 처리 추가.

### Step 4 — `frontend/src/components/ResponseCard.jsx`

`chart` prop 추가, ReactMarkdown 아래에 이미지 렌더링:

```jsx
// props에 chart 추가
function ResponseCard({ question, domain, status, grade, confidenceNote, draft, retryCount, showMeta, chart }) {

// draft 렌더링 이후에 조건부 chart 출력
{chart && (
  <div className="mt-3">
    <img
      src={`data:image/png;base64,${chart}`}
      alt="시뮬레이션 결과 그래프"
      className="rounded-lg max-w-full"
    />
  </div>
)}
```

---

## 수정 파일 목록

| 파일 | 변경 내용 |
|------|-----------|
| `frontend/src/api.js` | `currentParams` 파라미터 추가, body에 포함 |
| `frontend/src/pages/UserChat.jsx` | `latestParams` state, chart/params 추출, ResponseCard에 chart 전달 |
| `frontend/src/pages/DevChat.jsx` | 동일 |
| `frontend/src/components/ResponseCard.jsx` | `chart` prop 추가, img 태그 렌더링 |

---

## 검증

```bash
# 백엔드 실행
cd integrated_PARK && .venv/bin/python3 api_server.py

# 프론트엔드 실행
cd frontend && npm run dev

# curl로 finance 도메인 확인 (chart 필드 존재 여부)
curl -s -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"question": "월 매출 500만원, 임대료 80만원, 인건비 150만원으로 창업 시 수익성은?"}' \
  | python3 -c "import json,sys; d=json.load(sys.stdin); print('chart:', bool(d.get('chart')), 'len:', len(d.get('chart','')))"
```

브라우저에서 `/user` 접속 후 재무 질문 입력 → 답변 아래 히스토그램 이미지 출력 확인.
