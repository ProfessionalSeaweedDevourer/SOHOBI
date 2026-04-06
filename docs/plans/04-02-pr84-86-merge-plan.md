# PR #84, #85, #86 순차 main 머지 계획

## Context

세 PR 모두 main 브랜치 대상 OPEN 상태. git 충돌은 없으나, **코드 기능 점검** 결과 PR #85에 런타임 오류가 확인되어 머지 전 수정 필요. #84, #86은 머지 가능.

---

## 점검 결과 요약

### PR #84 — CHOI2 (버그 8건 수정) ✅ 머지 가능

수정된 8건 모두 기능적으로 올바름:

| 버그 | 수정 내용 | 상태 |
|------|----------|------|
| Bug-1: Plugin dict→SK 직렬화 오류 | `json.dumps(result)` 반환으로 변경 | ✅ |
| Bug-2: content_filter 재시도 메시지 누락 | `safe_history.add_user_message(user_msg)` 추가 | ✅ |
| Bug-3: breakdown 키 오류 (trdar_name→adm_name) | DB 스키마와 일치하도록 수정 | ✅ |
| Issue-4: psycopg2 이벤트 루프 블로킹 | `asyncio.to_thread()` 비동기화 | ✅ |
| Issue-5: LLM JSON 파싱 실패 | non-greedy regex로 코드블록 내부만 추출 | ✅ |
| Issue-6: get_similar_locations() IndexError | `if not rows: return []` 가드 추가 | ✅ |
| Issue-7: _get_pool() 레이스 컨디션 | Double-checked locking (`threading.Lock()`) | ✅ |
| Issue-8&9: DB 풀 고갈/HTTP 500 노출 | 3단계 예외 처리, 안전한 메시지 반환 | ✅ |

새로운 버그 없음. import, 비동기 처리, 예외 처리 모두 정확.

---

### PR #85 — CHANG (재무 에이전트 DB 활성화) ❌ 수정 후 머지

`integrated_PARK/db/finance_db.py`와 `finance_simulation_plugin.py`에 **런타임 오류 2건** 확인:

**오류 1 — SQL execute() 반환값 오용** (finance_db.py:50)
```python
# ❌ 현재 (TypeError 발생: None을 리스트에 담음)
avg = cur.execute("SELECT ROUND(AVG(tot_sales_amt)) FROM ...")
return [avg]

# ✅ 수정 필요
cur.execute("SELECT ROUND(AVG(tot_sales_amt)) FROM ...")
avg = cur.fetchone()[0]
return [avg]
```

**오류 2 — 조건문 로직 오류** (finance_simulation_plugin.py:201)
```python
# ❌ 현재 (industry_cd는 항상 str, None이 될 수 없어 조건 항상 False)
industry_cd = INDUSTRY_CODE_MAP.get(industry, "")
if region is None and industry_cd is None:  # 절대 True 아님

# ✅ 수정 필요
if region is None and not industry_cd:
```

**추가 확인 사항:**
- finance_db.py:57 기본값 17000000 → 170000000 (10배 증가, 의도 여부 확인 필요)
- `from db.repository import INDUSTRY_CODE_MAP` import 경로 실행 환경에서 동작 확인 필요

---

### PR #86 — WOO-clean2 (맵 UI 개선) ✅ 머지 가능 (조건부)

전반적으로 JSX 문법, import, props 처리 모두 정상. 백엔드(TERRY/) 변경도 정확.

⚠️ **확인 사항**: MapView.jsx에서 클러스터 클릭 처리 코드가 제거됨 → useMarkers.js의 `styleFunction` + StorePopup으로 대체됨. 실제 클러스터 클릭이 팝업을 여는지 수동 테스트 권장 (머지 전 개발자 확인).

---

## 실행 순서

### Step 1 — PR #84 머지

```bash
gh pr merge 84 --squash --subject "fix: location/legal 에이전트 버그 8건 수정 (비동기 처리, DB 키, JSON 파싱 등)"
```

### Step 2 — PR #85 수정 요청

**CHANG 브랜치에 아래 2개 수정이 필요함:**

1. `integrated_PARK/db/finance_db.py` L50 — `cur.fetchone()[0]`으로 수정
2. `integrated_PARK/plugins/finance_simulation_plugin.py` L201 — `not industry_cd`로 조건 수정

수정 후:
```bash
gh pr merge 85 --squash --subject "feat: 재무 에이전트 지역코드/업종 DB 활성화"
```

### Step 3 — PR #86 머지

개발자(WOO)에게 클러스터 클릭→팝업 동작 확인 요청 후:
```bash
gh pr merge 86 --squash --subject "feat: 맵 UI 개선 (클러스터 스타일, CategoryPanel, WmsPopup 뒤로가기)"
```

---

## 수정 대상 파일

- [integrated_PARK/db/finance_db.py](integrated_PARK/db/finance_db.py) — PR #85 수정 필요
- [integrated_PARK/plugins/finance_simulation_plugin.py](integrated_PARK/plugins/finance_simulation_plugin.py) — PR #85 수정 필요
