# 세션 인수인계 — SEC1 템플릿 라벨 누출 근본 원인 확인

## 요약

루브릭 오버홀 축 2(SEC1 토큰 누출)의 결정론적 정규식 선행 검사 PR(#277)을 열고 단위 테스트·실제 프로덕션 draft 탐지를 완료했다. 이후 사용자 지적으로 **누출의 근본 원인이 Sign-off 프롬프트가 아니라 하위 에이전트 자체의 프롬프트 설계**에 있음을 Explore 조사로 확인했다. 프롬프트 수정 조치는 본 세션에서 실행하지 않고 인수인계한다.

## 작업 브랜치·PR

- 브랜치: `feat/park-signoff-sec1-leak` (워크트리 `../SOHOBI-feat/park-signoff-sec1-leak`)
- PR: [#277](https://github.com/ProfessionalSeaweedDevourer/SOHOBI/pull/277) — security: Sign-off SEC1 결정론적 템플릿 라벨 누출 탐지
- 이전 인수인계: `2026-04-12-rubric-overhaul-handoff.md`

## 수정 파일

| 파일 | 변경 |
| ---- | ---- |
| `integrated_PARK/signoff/signoff_agent.py` | `detect_sec1_leakage()`, `_enforce_sec1_issue()` 추가, `run_signoff`에서 호출 |
| `integrated_PARK/tests/test_signoff_sec1_leak.py` | 단위 테스트 13건 (신규) |

## 검증 결과 (PR #277)

- TC1 단위 13건 PASS
- TC2 실제 프로덕션 draft 누출 2건 탐지 PASS
- TC4 Ruff lint·format PASS
- TC3 Azure E2E 회귀(일반 쿼리 200 응답) — 사용자 판단으로 보류 중. 재개 시 다음 커맨드:
  ```bash
  source integrated_PARK/.env
  curl -s -m 120 -X POST "$BACKEND_HOST/api/v1/query" \
    -H "Content-Type: application/json" -H "X-API-Key: $API_SECRET_KEY" \
    -d '{"question": "카페 창업 시 필요한 자금 규모는?"}'
  ```

## 근본 원인 조사 결과

| 도메인 | 라벨 출력 지시 | 위치 |
| ------ | -------------- | ---- |
| Legal | **예** | `integrated_PARK/agents/legal_agent.py:44-49` |
| Finance | **예** | `integrated_PARK/agents/finance_agent.py:66-69` |
| Admin | 아니오 ("별도 섹션 헤더 없이 자연스럽게 서술") | `integrated_PARK/agents/admin_agent.py:55` |
| Location | 아니오 (이모지/섹션 헤더만 지시) | `integrated_PARK/agents/location_agent.py:186-239` |

Legal/Finance 프롬프트의 "응답 형식" 블록이 `[사용자 질문]`·`[에이전트 응답]` 라벨을 출력하라고 지시하고 있다. 이것이 draft에 그대로 에코되어 Sign-off로 전달된다. Admin/Location은 처음부터 이런 지시가 없어 문제가 없다.

**이전 인수인계의 오기재 정정**: `2026-04-12-rubric-overhaul-handoff.md`의 `[unresolved]`는 "prompts/signoff_legal 계열이 템플릿 라벨을 누출"로 기록되어 있으나, 실제 원인 위치는 **signoff 프롬프트가 아니라 `integrated_PARK/agents/legal_agent.py` 및 `finance_agent.py`의 에이전트 프롬프트**다.

## 다음 세션 인수 작업

1. **Legal/Finance 에이전트 프롬프트 재작성** — `[사용자 질문]`/`[에이전트 응답]` 형식 블록 제거 (Admin 스타일 참고)
2. 로컬 기동 후 E2E로 draft 선두에 라벨이 없는지 확인
3. `detect_sec1_leakage`가 빈 리스트를 반환하여 SEC1 강제 issue 경로가 비활성화되는지 확인
4. PR #277 Test Plan의 TC3(Azure E2E) 결과 기록 및 머지 판단
5. 축 1(`_derive_grade` severity 가중)·축 3(도메인 Sign-off 프롬프트 재작성)·축 4(orchestrator chat 분기 sign-off)·축 5(프론트 grade 표시) 후속 진행

상세 계획은 `~/.claude/plans/binary-hatching-sun.md` 참조.

---
<!-- CLAUDE_HANDOFF_START
branch: feat/park-signoff-sec1-leak
pr: 277
prev: 2026-04-12-rubric-overhaul-handoff.md

[unresolved]
- HIGH agents/legal_agent.py:44-49 응답 형식 블록이 [사용자 질문]/[에이전트 응답] 라벨 출력을 명시 지시 — 블록 제거 또는 Admin 스타일로 교체
- HIGH agents/finance_agent.py:66-69 동일 패턴 — 동일 조치
- MED PR #277 TC3 (Azure E2E 정상 쿼리 회귀) 사용자 판단으로 보류 중 — 재개 필요
- (이전 handoff의 [unresolved] 항목들 유효. 단 "prompts/signoff_legal 계열 템플릿 라벨 누출"은 원인 위치 오기재였음 — 실제는 agents/*_agent.py)

[decisions]
- PR #277 SEC1 정규식은 방어 계층으로 유지 (프롬프트 수정 후에도 회귀 방지 가치 있음)
- 근본 원인 수정(Legal/Finance 프롬프트)은 본 세션에서 미실행 — 사용자 지시로 인수인계
- Admin 에이전트의 "섹션 헤더 없이 자연스럽게 서술" 패턴을 Legal/Finance에 적용

[next]
1. Legal/Finance 에이전트 프롬프트 응답 형식 블록 제거 (Admin 스타일 참고)
2. 로컬 기동 E2E로 draft 라벨 부재 검증, detect_sec1_leakage 빈 리스트 확인
3. PR #277 TC3 재개 및 머지 판단
4. 축 1·3·4·5 후속 (이전 handoff의 [next] 참조)

[traps]
- Legal/Finance 프롬프트 수정 시 G1-G4 루브릭 요건(법령 조항 인용, 면책 조항, 전문가 상담 권고)은 유지해야 함 — 형식만 제거, 내용 지시는 유지
- Admin/Location은 이미 라벨 없음 — 동일 수정 불필요
- 이전 handoff의 signoff_legal 프롬프트 관련 [unresolved]는 원인 오기재였으므로 맹목 추종 금지
CLAUDE_HANDOFF_END -->
