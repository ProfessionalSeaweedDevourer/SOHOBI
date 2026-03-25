# PR #45 머지 가능성 분석

## Context

PR #45 (CHANG → main): 재무 에이전트 state 누적 + 차트 출력 통합.
현재 integrated_PARK/ 구조와 호환성 여부를 검토한다.

---

## 검토 대상 파일 (main 기준 현재 코드)

| 파일 | 역할 |
|------|------|
| `orchestrator.py` | `draft = await agent.generate_draft(...)` → **문자열** 반환을 전제 |
| `finance_agent.py` | `generate_draft()` → `return draft` (str, line 228) |
| `finance_simulation_plugin.py` | 차트 없음, `monte_carlo_simulation()` → dict 반환 |
| `api_server.py` | `QueryRequest`에 `current_params` 없음 |

---

## PR #45가 제안하는 변경

1. **finance_agent.py** — `generate_draft()` 반환값을 `str` → `dict`로 변경
   ```python
   return {"draft": draft_text, "chart": chart_b64, "updated_params": variables}
   ```
2. **finance_simulation_plugin.py** — matplotlib 기반 히스토그램 차트 생성 추가
3. **api_server.py** — `QueryRequest`에 `current_params` 필드 추가, 커널 설정 간소화

---

## 문제점 분석

### 🔴 CRITICAL — orchestrator.py가 dict를 받으면 즉시 크래시

`orchestrator.py`는 `generate_draft()`가 `str`을 반환한다고 전제한다.
PR #45는 orchestrator 수정 없이 반환형을 바꾸므로 3곳에서 깨진다:

| 위치 | 코드 | 문제 |
|------|------|------|
| `orchestrator.py:61` | `if draft == prev_draft:` | dict 비교는 동작하지만 의도 불명 |
| `orchestrator.py:67` | `run_signoff(..., draft=draft)` | `run_signoff`는 str 기대 → `json.dumps(dict)` 같은 문자열이 전달되거나 TypeError |
| `orchestrator.py:89` | `"draft": draft` (응답 반환) | 프론트엔드가 dict를 받으면 화면 출력 불가 |

**finance 도메인 질문 시 500 에러 또는 signoff가 dict 내용을 그대로 평가하는 오동작 발생.**

---

### 🟠 HIGH — session_vars vs current_params 파라미터 불일치 (기존 버그)

현재 `orchestrator.py:51`:
```python
extra = {"session_vars": session_vars} if domain == "finance" and session_vars else {}
draft = await agent.generate_draft(..., **extra)
```

`finance_agent.generate_draft()` 시그니처:
```python
async def generate_draft(self, question, current_params=None, retry_prompt="", profile="")
```

`session_vars` 키는 시그니처에 없으므로 세션에 추출 변수가 존재할 때
`TypeError: generate_draft() got an unexpected keyword argument 'session_vars'` 발생.

이는 PR #45 이전부터 존재하는 버그다. **PR #45 병합과 무관하게 별도 수정 필요.**

---

### 🟠 HIGH — current_params가 orchestrator까지 전달되지 않음

PR #45가 `api_server.py`의 `QueryRequest`에 `current_params`를 추가해도,
`orchestrator.run()` 호출부에 이를 넘기는 코드가 없으면 실제로 사용되지 않는다.
`orchestrator.run()` 시그니처 자체도 `current_params`를 받지 않는다.

→ **state 누적 기능이 실제로 작동하지 않는 반쪽짜리 구현이 된다.**

---

### 🟡 MEDIUM — matplotlib 의존성 누락

`finance_simulation_plugin.py`에 matplotlib import 추가 시
`requirements.txt`에 없으면 Container Apps 배포 시 `ModuleNotFoundError`.

확인 필요:
```bash
grep matplotlib integrated_PARK/requirements.txt
```

---

### 🟡 MEDIUM — `is_multi` 미정의 변수 (현재 코드 버그)

`finance_agent.py:196` (현재 PARK branch):
```python
range_desc = f"실제 매장 {len(rev)}개 데이터" if is_multi else "매출·원가 ±10%"
```
`is_multi`가 이 스코프 어디에도 정의되지 않음 → `raw_loss == 0.0`인 케이스에서 `NameError`.
PR #45와 무관하지만 병합 전 수정 필요.

---

## 결론

**현재 상태로는 머지 불가.**

PR #45를 머지하려면 최소한 아래 두 가지가 선행되어야 한다:

1. **`orchestrator.py` 수정** — `generate_draft()` 반환값이 dict인 경우 처리:
   ```python
   raw = await agent.generate_draft(...)
   if isinstance(raw, dict):
       draft = raw.get("draft", "")
       chart  = raw.get("chart")
       updated_params = raw.get("updated_params")
   else:
       draft = raw
   ```

2. **`orchestrator.py` 파라미터 일치** — `session_vars` → `current_params`로 통일:
   ```python
   extra = {"current_params": session_vars} if domain == "finance" and session_vars else {}
   ```

추가 권장:
- `requirements.txt`에 `matplotlib` 추가 (차트 기능 포함 시)
- `finance_agent.py:196` `is_multi` 버그 수정
- PR #45에 orchestrator 수정 커밋 추가 후 재검토
