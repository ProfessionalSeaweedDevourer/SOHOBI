# PR #131 Merge Conflict 해결 계획

## Context
PR #131 (PARK → main)은 백엔드 안정성 2차 수정 (DB 풀 통합, LLM 타임아웃, 예외 로깅)을 담고 있다.
그러나 main에 먼저 머지된 커밋들(주로 PR #128)이 같은 파일을 수정하여 3개 파일에서 충돌이 발생하고 있다.
baseDAO.py, api_server.py, location_agent.py, legal_agent.py, chat_agent.py, domain_router.py는 main에서 merge base 이후 변경되지 않아 자동 머지 가능.

---

## 충돌 파일 분석

### 1. `integrated_PARK/db/finance_db.py` — 아키텍처 충돌
| 구분 | PARK 브랜치 | main |
|------|------------|------|
| 연결 방식 | BaseDAO 상속 (풀 공유) | raw psycopg2 커넥션 (매 호출 생성) |
| SQL | 단순 `SELECT tot_sales_amt` | 점포 수 기반 매출 평균 계산 쿼리 (subquery 포함) |
| fallback | 17,000,000 (잘못됨) | 170,000,000 |

**해결안**: PARK의 BaseDAO 구조를 유지하면서 main의 정교한 per-store 평균 SQL을 채택.
- `get_sales()`: `_query(sql, params)` 사용 → `[row["avg_sales_per_store"] for row in rows]` 반환
- `get_average_sales()`: 같은 방식으로 per-store avg SQL 적용
- fallback 값 모두 `170_000_000`으로 통일 (main 기준)

### 2. `integrated_PARK/agents/finance_agent.py` — 두 독립적 변경 충돌
| 구분 | PARK 브랜치 | main |
|------|------------|------|
| LLM 타임아웃 | asyncio.wait_for(60초) 3곳 추가 | 없음 |
| breakeven 처리 | None 미처리, 포맷 `{:,}원` | None 조건 분기, 평문 `{breakeven_revenue}` |

**해결안**: 두 변경 모두 채택 (orthogonal).
- `_EXPLAIN_PROMPT`: main의 `{breakeven_revenue}`, `{safety_margin}` 형식 (평문 string) 유지
- `generate_draft()`: main의 `breakeven_revenue_str`/`safety_margin_str` 조건 분기 유지
- `_call_llm()`, `_call_llm_with_history()`: PARK의 asyncio.wait_for 유지

### 3. `integrated_PARK/agents/admin_agent.py` — SYSTEM_PROMPT + 타임아웃 충돌
| 구분 | PARK 브랜치 | main |
|------|------------|------|
| SYSTEM_PROMPT | `[사용자 질문]/{question}/[에이전트 응답]` 섹션 헤더 포함 | 헤더 없이 자연스럽게 서술하는 형식 |
| LLM 타임아웃 | asyncio.wait_for(60초) 추가 | 없음 |

**해결안**: 두 변경 모두 채택.
- SYSTEM_PROMPT: main의 새 형식 (섹션 헤더 제거) 채택
- `generate_draft()`: PARK의 asyncio.wait_for(60초) 유지

---

## 수행 절차

### Step 1 — PARK 브랜치를 main 위로 rebase
```bash
git checkout origin/PARK -b PARK-rebase
git rebase origin/main
```
충돌 3개 파일을 수동으로 해결:

### Step 2 — `integrated_PARK/db/finance_db.py` 해결
BaseDAO 상속 유지 + main의 per-store 평균 SQL 결합:

```python
# get_sales()
sql = f"""
    SELECT
        ROUND(
            s.tot_sales_amt::numeric
            / NULLIF(
                COALESCE(
                    (SELECT ROUND(AVG(st.stor_co))
                    FROM sangkwon_store st
                    WHERE st.adm_cd = s.adm_cd
                    AND st.svc_induty_cd = s.svc_induty_cd
                    AND st.stor_co > 0), 1), 0)
        ) AS avg_sales_per_store
    FROM sangkwon_sales s
    WHERE s.adm_cd IN ({placeholders})
    AND s.svc_induty_cd = %s
    AND s.tot_sales_amt IS NOT NULL
"""
rows = self._query(sql, region + [industry])
results = [float(r["avg_sales_per_store"]) for r in rows if r["avg_sales_per_store"]]
return results if results else self.get_average_sales()
```
- fallback 반환값: `[170_000_000]`
- `get_average_sales()`도 동일한 per-store avg SQL 패턴 적용, `_query()` 사용

### Step 3 — `integrated_PARK/agents/finance_agent.py` 해결
- `_EXPLAIN_PROMPT` 81~82줄: `{breakeven_revenue:,}원 (일 기준: ...)` → `{breakeven_revenue}` / `{safety_margin}` (main 형식)
- `generate_draft()` breakeven 조건 분기 블록: main 버전으로 교체
- `_call_llm()`, `_call_llm_with_history()`: asyncio.wait_for는 이미 main에 없으므로 PARK 버전 유지

### Step 4 — `integrated_PARK/agents/admin_agent.py` 해결
- `SYSTEM_PROMPT` 마지막 블록: main의 `응답은 창업자에게 직접 말하는 형식...` 채택
- `generate_draft()` LLM 호출부: PARK의 asyncio.wait_for(60초) + TimeoutError 처리 유지

### Step 5 — force-push & PR 확인
```bash
git push origin PARK-rebase:PARK --force
gh pr list --head PARK --state open
```

---

## 검증

1. 백엔드 기동: `cd integrated_PARK && .venv/bin/python3 api_server.py`
2. 재무 에이전트 쿼리: `curl -X POST .../api/v1/query -d '{"question":"강남 카페 월매출 500만원 재무 시뮬레이션"}'`
3. breakeven None 케이스 확인 (매출=0 입력)
4. 행정 에이전트 섹션 헤더 없는 응답 확인

---

## 수정 파일 목록
- `integrated_PARK/db/finance_db.py` (충돌 해결)
- `integrated_PARK/agents/finance_agent.py` (충돌 해결)
- `integrated_PARK/agents/admin_agent.py` (충돌 해결)
