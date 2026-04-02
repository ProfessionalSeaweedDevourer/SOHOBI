# PR #85 코드 리뷰 — CHANG 브랜치 수정 요청

**작성일**: 2026-04-02  
**대상 PR**: #85 — "#79 변수 활용 및 DB활성화" (`CHANG` → `main`)  
**작성자**: 리뷰 담당  
**수신**: CHANG

---

## 요약

PR #85의 의도(지역코드·업종 기반 DB 조회, INDUSTRY_CODE_MAP 연동)는 올바르나,  
**Oracle → PostgreSQL 이전 과정에서 발생한 API 호환성 문제 2건**이 확인되었습니다.  
아래 수정 후 재푸시해 주세요.

---

## 배경: Oracle vs PostgreSQL cursor.execute() 차이

프로젝트는 `949d10a` 커밋에서 Oracle(`oracledb`) → Azure PostgreSQL(`psycopg2`)로 이전되었습니다.  
두 라이브러리는 `cursor.execute()` 반환값이 다릅니다:

| 라이브러리 | `execute()` 반환값 | 결과 조회 방법 |
|-----------|-------------------|--------------|
| `oracledb` (Oracle) | Cursor 객체 (체이닝 가능) | `cur.execute(sql).fetchone()` |
| `psycopg2` (PostgreSQL) | **`None`** | `cur.execute(sql)` 후 `cur.fetchone()` 별도 호출 |

CHANG 브랜치는 `psycopg2` 환경에서 Oracle 스타일 패턴을 사용하고 있어 런타임 오류가 발생합니다.

---

## 수정 필요 사항 (필수)

### 오류 1 — `integrated_PARK/db/finance_db.py` (약 L50)

**현상**: `cur.execute()`는 `psycopg2`에서 `None`을 반환하므로 `avg = None`이 되어 `[None]`을 반환합니다.

```python
# ❌ 현재 코드 (런타임 시 [None] 반환 — 재무 시뮬레이션 전체 오작동)
avg = cur.execute(
    "SELECT ROUND(AVG(tot_sales_amt)) FROM sangkwon_sales WHERE svc_induty_cd LIKE 'CS10%'"
)
return [avg]

# ✅ 수정 코드
cur.execute(
    "SELECT ROUND(AVG(tot_sales_amt)) FROM sangkwon_sales WHERE svc_induty_cd LIKE 'CS10%'"
)
avg = cur.fetchone()[0]
return [avg]
```

---

### 오류 2 — `integrated_PARK/plugins/finance_simulation_plugin.py` (약 L201)

**현상**: `INDUSTRY_CODE_MAP.get(industry, "")` 는 항상 `str`을 반환하므로 `industry_cd is None` 조건은 절대 `True`가 되지 않습니다. 결과적으로 `region`이 `None`이어도 항상 `get_sales()` 경로로 빠져 DB 오류가 발생합니다.

```python
# ❌ 현재 코드 (조건문 항상 False — get_average_sales() 경로 도달 불가)
industry_cd = INDUSTRY_CODE_MAP.get(industry, "")
if region is None and industry_cd is None:
    revenue = dbwork.get_average_sales()
else:
    revenue = dbwork.get_sales(region, industry_cd)

# ✅ 수정 코드
industry_cd = INDUSTRY_CODE_MAP.get(industry, "")
if region is None and not industry_cd:
    revenue = dbwork.get_average_sales()
else:
    revenue = dbwork.get_sales(region, industry_cd)
```

---

## 확인 요청 사항 (선택)

### fallback 기본값 변경 여부 확인

`finance_db.py`의 DB 조회 실패 시 fallback 기본값이 **10배** 증가해 있습니다.  
의도적 변경인지, 오타인지 확인해 주세요:

```python
# main 브랜치 (기존)
return [17000000]   # 1,700만 원

# CHANG 브랜치 (변경 후)
return [170000000]  # 1억 7,000만 원  ← 의도?
```

### import 경로 동작 확인

```python
from db.repository import INDUSTRY_CODE_MAP
```

`integrated_PARK/` 루트에서 실행 시 해당 import가 정상 동작하는지 로컬 환경에서 확인 후 푸시해 주세요.

---

## 수정 후 검증 방법

```bash
cd integrated_PARK

# 1. import 오류 없는지 확인
.venv/bin/python3 -c "from plugins.finance_simulation_plugin import FinanceSimulationPlugin; print('OK')"

# 2. DB 평균 조회 함수 단독 테스트
.venv/bin/python3 -c "
from db.finance_db import DBWork
db = DBWork()
print(db.get_average_sales())  # 숫자가 담긴 리스트여야 함
"

# 3. API 통합 테스트
curl -s -X POST http://localhost:8000/api/v1/query \
  -H 'Content-Type: application/json' \
  -d '{"question": "홍대 카페 창업 재무 시뮬레이션 해줘"}'
```

---

## PR 재진행 절차

1. CHANG 브랜치에서 위 2건 수정
2. 로컬 검증 후 `git push origin CHANG`
3. PR #85에 코멘트로 수정 완료 알림

수정 완료 확인 후 main 머지 진행하겠습니다.
