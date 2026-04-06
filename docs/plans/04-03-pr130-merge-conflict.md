# PR #130 (CHANG) Merge Conflict 해소 계획

## Context

PR #130은 CHANG 브랜치가 `b281524` (PR #74)를 기준으로 분기하여 작성됨:

- 목표: `finance_db.py` DB 연결/해제 공통 메소드 분리 + 전 파일 docstring 추가

오늘 PARK 브랜치 PR #131, #132가 main에 **이미 머지됨** (현재 `origin/main` = 최신):

- `DBWork`를 `BaseDAO` 상속으로 전환 (커넥션 풀 공유)
- `asyncio.wait_for` timeout 적용 (LLM 호출, 여러 곳)
- `logger.warning` 교체 (print 제거)
- `breakeven_analysis_mc` None guard 추가
- `_call_llm` 서비스명 `sign_off` → `finance` 수정
- `bin_size` ZeroDivision 수정
- `_extract_params` 반환 타입 `dict` → `tuple[dict, dict]` (adm_codes + business_type 분리)

## 충돌 구조 분석

### CHANG이 가져오는 고유 가치

1. 모든 클래스/메서드 docstring (팀 전체 가독성)
2. `_execute_query` 헬퍼 패턴 (DB 보일러플레이트 감소)

### PARK이 가져오는 고유 가치 (서버 안정성 필수, 이미 main에 있음)

1. `BaseDAO` 상속 → 커넥션 풀 공유 (`_execute_query`를 대체·상위호환)
2. LLM 타임아웃, 예외 로깅, None guard
3. `_extract_params` 시그니처: `dict` → `tuple[dict, dict]`

### 파일별 충돌 핵심

| 파일 | CHANG 기여 | 충돌 원인 |
| --- | --- | --- |
| `finance_db.py` | `_execute_query` + docstring | main이 BaseDAO로 전면 교체 |
| `finance_agent.py` | 클래스/메서드 docstring만 추가 | main이 시그니처·로직 변경, docstring 자리 이동 |
| `finance_simulation_plugin.py` | 클래스/메서드 docstring만 추가 | main이 `breakeven_analysis` 제거, None guard 추가 |

## 해소 전략

### 순서

1. **CHANG 브랜치를 현재 main으로 rebase** (PARK PRs 이미 머지됨)
2. **충돌 3개 파일 수동 해소** (아래 규칙 적용)
3. **force-push 후 PR #130 재검토**

### `finance_db.py` 해소 규칙

- **main(PARK) 버전 전면 채택** (BaseDAO 상속, `_db_con()` / `_close()`, logger)
- `_execute_query` **폐기** — BaseDAO가 상위호환 대체
- CHANG의 docstring을 main 코드 위에 이식:
  - `DBWork` 클래스 docstring → BaseDAO 풀 공유 사실 반영하도록 업데이트
  - `get_sales`, `get_average_sales` 메서드 docstring 그대로 이식

### `finance_agent.py` 해소 규칙

- **main(PARK) 버전 전면 채택** (asyncio import, wait_for timeout, 서비스명 `finance`)
- CHANG의 docstring 이식:
  - `FinanceAgent` 클래스 docstring → 그대로
  - `_extract_params` docstring → PARK 시그니처 `tuple[dict, dict]` 반영 (CHANG이 이미 올바르게 작성함)
  - `generate_draft` docstring → 그대로

### `finance_simulation_plugin.py` 해소 규칙

- **main(PARK) 버전 전면 채택** (None guard, ZeroDivision 수정, `breakeven_analysis` 메서드 제거됨)
- CHANG의 docstring 이식:
  - `FinanceSimulationPlugin` 클래스 docstring → 그대로
  - `get_industry_ratio`, `monte_carlo_simulation`, `breakeven_analysis_mc`, `load_initial`, `merge_json` → main 코드 위에 이식
  - `breakeven_analysis` (구 메서드) docstring은 **이식 불필요** — 메서드 자체가 삭제됨

## 실행 절차 (rebase 방식)

```bash
git fetch origin
git checkout CHANG
git rebase origin/main

# 충돌 발생 시 각 파일 규칙대로 해소 후:
git push --force-with-lease origin CHANG
```

## 검증

- `python3 -c "from db.finance_db import DBWork; print('OK')"` → 임포트 성공
- `curl -X POST http://localhost:8000/api/v1/query -d '{"question":"홍대 카페 창업 시뮬레이션"}'` → 재무 분석 응답 정상
- 서버 로그에 `logger.warning` 포맷 확인 (`print(` 없음)

## 수정 대상 파일

- `integrated_PARK/db/finance_db.py`
- `integrated_PARK/agents/finance_agent.py`
- `integrated_PARK/plugins/finance_simulation_plugin.py`
