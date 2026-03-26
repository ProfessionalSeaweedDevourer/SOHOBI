# 재무 에이전트 차트 출력 및 state 누적 구현 (PARK-2)

## 수정 배경

PR #45 (CHANG)가 달성하려 했던 두 가지 목표:

1. **재무 파라미터 state 누적** — 여러 차례 질문을 이어가면서 이미 언급한 수치(매출, 임대료 등)가 다음 질문에도 유지되도록 한다.
2. **몬테카를로 결과 차트 출력** — 시뮬레이션 결과를 히스토그램으로 시각화해 응답에 포함한다.

PR #45는 이 목표들을 정확히 짚었지만, `finance_agent.generate_draft()`의 반환 타입을 `str → dict`로 바꾸면서 `orchestrator.py`를 수정하지 않아 서비스 전체가 크래시되는 구조적 문제가 있었다. 또한 `session_vars` / `current_params` 파라미터 명칭 불일치로 state가 실제로는 전달되지 않는 버그도 존재했다. PARK-2는 이 두 목표를 올바르게 구현한다.

---

## 변경 파일 및 수정 의도

### 1. `integrated_PARK/plugins/finance_simulation_plugin.py`

**수정 의도:** 시뮬레이션 결과를 숫자만이 아닌 시각적 형태로도 제공한다.

**실제 변경:**

- `_generate_chart(results, avg, p20, loss_prob)` 메서드 추가
  - matplotlib + numpy로 10,000회 결과 히스토그램 생성
  - 손실 구간(빨강), 평균선(초록), 하위 20% 기준선(주황) 표시
  - `matplotlib.use("Agg")`로 헤드리스 환경(컨테이너) 대응
  - matplotlib 미설치 환경에서는 `None` 반환 (try/import 방어 처리)
- `monte_carlo_simulation()` 반환 dict에 `"chart": base64_png_str | None` 추가

**변경 전 → 후:**
```
반환: {average_net_profit, loss_probability, p20, ...}
반환: {average_net_profit, loss_probability, p20, ..., chart: "<base64>"|null}
```

---

### 2. `integrated_PARK/agents/finance_agent.py`

**수정 의도:**
- 기존 `NameError` 버그를 수정한다.
- 차트와 파라미터 상태를 orchestrator까지 전달할 수 있도록 반환 구조를 변경한다.

**실제 변경:**

**① `is_multi` 미정의 변수 수정 (버그 수정)**

```python
# 변경 전 — is_multi가 정의된 적 없음, raw_loss == 0.0일 때 NameError 발생
if raw_loss == 0.0:
    range_desc = f"실제 매장 {len(rev)}개 데이터" if is_multi else "매출·원가 ±10%"

# 변경 후
is_multi = len(rev) > 1          # ← 추가
if raw_loss == 0.0:
    range_desc = f"실제 매장 {len(rev)}개 데이터" if is_multi else "매출·원가 ±10%"
```

**② `generate_draft()` 반환 타입 변경**

```python
# 변경 전
return draft                    # str

# 변경 후
return {
    "draft":          draft,            # str — signoff/응답용 텍스트
    "chart":          sim_result.get("chart"),  # base64 PNG 또는 None
    "updated_params": variables,        # 누적된 파라미터 dict (프론트 저장용)
}
```

finance 도메인만 dict를 반환한다. 다른 도메인(legal, admin, location)은 그대로 str을 반환한다.

---

### 3. `integrated_PARK/orchestrator.py`

**수정 의도:**
- `session_vars` → `current_params` 파라미터명 불일치 버그를 수정한다.
- finance 에이전트가 dict를 반환할 때 올바르게 분기 처리한다.
- `chart`와 `updated_params`를 최종 결과에 포함해 api_server까지 전달한다.

**실제 변경:**

**① 파라미터명 수정 — `run()` 및 `run_stream()` 양쪽**

```python
# 변경 전 (실제로는 finance_agent에 전달되지 않았음)
async def run(..., session_vars: dict | None = None):
    extra = {"session_vars": session_vars} if domain == "finance" ...

# 변경 후
async def run(..., current_params: dict | None = None):
    extra = {"current_params": current_params} if domain == "finance" ...
```

**② dict 반환 분기 처리**

```python
raw = await agent.generate_draft(...)
if isinstance(raw, dict):           # finance 에이전트
    draft = raw.get("draft", "")
    chart = raw.get("chart")
    updated_params = raw.get("updated_params")
else:                               # 나머지 도메인
    draft = raw
```

이로써 `run_signoff(draft=draft)`에는 항상 str이 전달된다.

**③ 최종 결과 dict에 `chart`, `updated_params` 추가**

approved / escalated 양쪽 모두 포함. finance 외 도메인에서는 두 필드가 `None`으로 반환된다.

---

### 4. `integrated_PARK/api_server.py`

**수정 의도:**
- 클라이언트가 이전 응답의 `updated_params`를 다음 요청에 그대로 실어 보낼 수 있도록 한다.
- 응답에 `chart`와 `updated_params`를 포함해 프론트엔드가 활용할 수 있게 한다.

**실제 변경:**

**① `QueryRequest`에 `current_params` 필드 추가**

```python
current_params: dict | None = Field(
    default=None,
    description="재무 에이전트 누적 파라미터. 이전 응답의 updated_params를 그대로 전달한다.",
)
```

**② orchestrator 호출 — 클라이언트 전달값 우선, 서버 세션 폴백**

```python
# 변경 전
session_vars=session["extracted"] if session["extracted"] else None

# 변경 후
params = req.current_params or (session["extracted"] if session["extracted"] else None)
current_params=params
```

클라이언트가 `current_params`를 보내면 그것을 쓰고, 없으면 서버 세션에 누적된 값을 사용한다.

**③ 응답에 `chart`, `updated_params` 추가** (`/api/v1/query` 엔드포인트)

`/api/v1/stream`은 orchestrator가 이미 complete 이벤트에 포함하므로 별도 처리 불필요.

---

## 변경 전 → 후 전체 데이터 흐름

```
[변경 전]
클라이언트 → api_server → orchestrator.run(session_vars=...)
                                ↓
                         finance_agent.generate_draft()
                         (current_params 파라미터 있지만 session_vars로 잘못 전달 → 미사용)
                                ↓
                         return draft: str
                                ↓
                         run_signoff(draft=str) ✅
                                ↓
                         응답: {draft: str}
                         (차트 없음, updated_params 없음)

[변경 후]
클라이언트 → api_server(current_params 수신) → orchestrator.run(current_params=...)
                                ↓
                         finance_agent.generate_draft(current_params=...)
                         (base = current_params or load_initial())
                         (merged = merge_json(base, 새로 추출한 값))
                                ↓
                         return {"draft": str, "chart": b64, "updated_params": merged}
                                ↓
                         orchestrator: draft = raw["draft"]
                         run_signoff(draft=str) ✅
                                ↓
                         응답: {draft: str, chart: b64|null, updated_params: {...}}
                                ↓
                         클라이언트: updated_params 저장 → 다음 요청의 current_params로 전달
```

---

## 최종 상태

| 항목 | 상태 |
|------|------|
| 재무 파라미터 state 누적 | ✅ 동작 — 이전 응답 `updated_params`를 다음 요청 `current_params`로 전달하면 누락 수치가 유지됨 |
| 몬테카를로 차트 | ✅ 동작 — 응답 `chart` 필드에 base64 PNG (~17KB) 포함 |
| 다른 도메인 영향 | ✅ 없음 — legal/admin/location은 str 반환 그대로, chart/updated_params는 null |
| `is_multi` 버그 | ✅ 수정 — `len(rev) > 1`로 정의 추가 |
| `session_vars` 파라미터 버그 | ✅ 수정 — `current_params`로 통일 |
| signoff 호환성 | ✅ — orchestrator에서 dict 분기 후 str만 전달 |
| matplotlib 미설치 환경 | ✅ — `chart: null` 반환 (크래시 없음) |

---

## 검증

```bash
# 1차 질문 — updated_params 확인
curl -s -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"question": "초기 투자금 3000만원, 월매출 700만원으로 카페를 열고 싶습니다", "domain": "finance"}'

# 2차 질문 — current_params에 1차 updated_params 전달, state 누적 확인
curl -s -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"question": "임대료가 월 150만원입니다", "domain": "finance", "current_params": <1차_updated_params>}'
```

**확인 항목:**
- `chart` 필드 존재 (base64 문자열)
- 2차 응답 `updated_params.rent == 1500000`
- 2차 응답 `updated_params.revenue == [7000000]` (1차 값 유지)
- 2차 응답 `updated_params.initial_investment == 30000000` (1차 값 유지)
