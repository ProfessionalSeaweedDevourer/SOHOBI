# 플랜: FinanceAgent 불필요한 입력값 검사 제거

## Context

**문제:** "매출 기본값으로 시뮬레이션", "기본값으로 재무 시뮬레이션" 등의 질문에서
"재무 시뮬레이션을 위한 수치(매출, 원가, 임대료 등)가 질문에 포함되어 있지 않습니다."라는
안내 메시지가 반환되어 시뮬레이션이 실행되지 않는다.

**설계 의도와 충돌:** `FinanceSimulationPlugin.load_initial()`은 DB 평균 매출(또는 1,400만원 폴백)을
기본값으로 제공하도록 설계되어 있고, `monte_carlo_simulation()`도 revenue를 제외한
모든 파라미터를 업종 비율 기반 기본값으로 자동 계산한다.

## 원인 분석

`integrated_PARK/agents/finance_agent.py:197–206`에 있는 가드 조건:

```python
has_user_financials = any(extracted.get(k) is not None for k in sim_keys)
if not has_user_financials and current_params is None:
    return { "draft": "재무 시뮬레이션을 위한 수치...", ... }
```

이 조건은 두 가지 경우 모두 시뮬레이션을 차단한다:

1. **"기본값으로 시뮬레이션"** — LLM이 revenue=null을 추출 (숫자가 없으므로). `current_params=None`. → 차단
2. **"자본금 2억으로 시뮬레이션"** — LLM이 `initial_investment=200000000`을 추출하지만,
   `sim_keys`에 `initial_investment`가 없으므로 `has_user_financials=False`. → 차단

그러나 이 시점에서 `variables`에는 이미 `load_initial()`의 기본 revenue가 포함되어 있으며
시뮬레이션을 실행할 수 있는 상태다. 가드 조건이 불필요하게 차단한다.

## 수정 방법

**파일:** `integrated_PARK/agents/finance_agent.py`

**Lines 195–206** 블록 전체 제거:

```python
# 제거 대상
has_user_financials = any(extracted.get(k) is not None for k in sim_keys)
if not has_user_financials and current_params is None:
    return {
        "draft": (
            "재무 시뮬레이션을 위한 수치(매출, 원가, 임대료 등)가 질문에 포함되어 있지 않습니다. "
            "예상 월매출, 원가 비율, 임대료 등을 알려주시면 시뮬레이션을 수행할 수 있습니다."
        ),
        "updated_params": None,
        "chart": None,
    }
```

제거 후 흐름:
- `variables`에는 항상 `load_initial()` 기본값(DB 평균 매출) + 사용자 입력이 병합됨
- `sim_input = {k: variables[k] for k in sim_keys if variables.get(k) is not None}` 로 전달
- `monte_carlo_simulation(revenue=...)` 실행 → 기본값 기반 시뮬레이션 결과 반환
- `[1. 가정 조건]` 하단에 "입력되지 않은 항목은 지역/업종/상권 평균치를 적용하였으며" 안내가 이미 있음

## 수정 범위

| 파일 | 변경 내용 |
|------|-----------|
| `integrated_PARK/agents/finance_agent.py:195–206` | 가드 블록 7줄 제거 |

signoff 프롬프트, orchestrator, plugin은 변경 불필요.

## 검증

```bash
# 기본값 시뮬레이션 요청
curl -s -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"question": "기본값으로 재무 시뮬레이션"}'

# 자본금만 입력
curl -s -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"question": "자본금 2억으로 시뮬레이션"}'
```

기대 결과: `final_draft`에 `[1. 가정 조건]`, `[2. 시뮬레이션 결과]`, `[3. 외부 리스크 경고]` 섹션이 포함된
정상 시뮬레이션 응답이 반환되어야 한다.
