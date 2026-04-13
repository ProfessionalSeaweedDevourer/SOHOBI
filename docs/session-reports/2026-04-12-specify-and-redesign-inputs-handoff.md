# 세션 인수인계 — `/specify` 커맨드 신설 + 재설계 A 입력물 확보

## 개요

본 세션에서 두 가지를 완료했다.

1. **`/specify` 커맨드 신설** — `/boot` 다음 단계인 "인수인계 블록 기반 세션 범위 선정·기획" 흐름을 커맨드화. IDE에서 현재 열린 handoff 파일을 `ls -t` 최신보다 우선 참조하는 것이 핵심 설계.
2. **Signoff 재설계 세션 A 입력물 확보** — PR #277·#279 머지 후 프로덕션 회귀 검증(TC3 4건), 최근 200건 로그 덤프, domain_router 오분류 6건 특정.

## 브랜치·PR 상태

- 작업 브랜치: `chore/park-specify-command`
- 열린 PR: #281 (`chore: /specify 커맨드 추가 — 세션 범위 선정·기획 자동화`)
- 머지 대기. Test plan의 수동 검증 TC는 후속 세션에서 수행해야 체크 가능

## 산출물

| 파일 | 상태 | 설명 |
|------|------|------|
| `.claude/commands/specify.md` | 커밋 (PR #281) | `/specify` 커맨드 정의 |
| `docs/session-reports/2026-04-12-redesign-inputs.md` | 미커밋 | TC3 결과 + domain_router 오분류 6건 리포트 |
| `docs/session-reports/2026-04-12-query-log-dump.json` | 미커밋 | 200건 쿼리 로그 덤프 (404KB) |

## TC3 검증 요약

| # | 의도 | 라우팅 | SEC1 누출 | 결과 |
|---|------|--------|-----------|------|
| Q1 | legal | **admin** ⚠ | 없음 | 누출은 PASS, 라우팅 오분류 포착 |
| Q2 | legal | legal | 없음 | PASS |
| Q3 | finance | finance | 없음 | PASS |
| Q4 | finance | finance | 없음 | PASS |

→ PR #277·#279 SEC1 회귀 없음. 롤백 불필요.

## domain_router 오분류 패턴

6건 중 3건이 "영업신고·식품위생법" → legal 기대 → 실제 admin 오적재. "신고" 어휘가 admin 프롬프트에 과적합된 것으로 추정. 재설계 세션 A에서 이 6건을 회귀 픽스쳐로 편입할 것.

## 다음 세션 인수 요약

1. PR #281 머지 필요 (리뷰 또는 admin squash)
2. Part 2 산출물(`2026-04-12-redesign-inputs.md`, `2026-04-12-query-log-dump.json`) 커밋 여부 사용자 판단 필요
3. `.env.prod` 샘플 또는 Azure 쉐도우 환경 요청 (로컬 gpt-4.1-mini ↔ 프로덕션 gpt-5.4 불일치)
4. 재설계 세션 A 착수 — 축 1 severity 스키마 + 축 3 도메인 프롬프트 재작성 + 오분류 6건 픽스쳐

---
<!-- CLAUDE_HANDOFF_START
branch: chore/park-specify-command
pr: 281 (open)
prev: 2026-04-12-signoff-redesign-handoff.md

[unresolved]
- HIGH domain_router legal↔admin 오분류 6건 — 세션 A 픽스쳐로 편입 대기, 라우팅 재설계 선행 여부 결정 필요
- HIGH 로컬 .env(gpt-4.1-mini) ↔ 프로덕션(gpt-5.4) 모델 불일치 — 재설계 세션 신뢰도 기반 미확보
- HIGH signoff/signoff_agent.py _derive_grade severity 가중 미반영 (축 1, 세션 A 소속)
- HIGH orchestrator.py is_partial·chat 분기가 signoff 우회 (축 4, 세션 B 소속)
- MED 재설계-inputs 리포트와 로그 덤프 커밋 여부 미결 — 사용자 판단 대기
- MED 프로덕션 TC3 표본 4건 — 도메인×3건 확장 필요
- MED F1~F5 루브릭 극단 수치 둔감 (세션 A 소속)
- MED RJ1 blocker 필수화 미반영
- MED frontend/LogTable.jsx ITEM_LABELS 백엔드 의미 어긋남 (축 5)
- LOW frontend map/ChatPanel.jsx grade 표시 전무 (축 5)

[decisions]
- /specify 커맨드의 handoff 참조 우선순위: IDE 열린 파일 > ls -t 최신. 사용자가 특정 handoff를 열어둔 행위를 의도 신호로 간주
- 커밋 범위 분리: 커맨드 정의(Part 1)만 PR화, 조사 산출물(Part 2)은 사용자 판단 후 별도 커밋 — 리뷰 집중도 보존
- TC3 PASS로 PR #277(결정론 SEC1 정규식) 유지 확정 — #279 근본 원인 제거 후에도 이중 방어 필요

[next]
1. PR #281 머지
2. Part 2 산출물 커밋 또는 폐기 결정
3. .env.prod 샘플 커밋 또는 Azure 쉐도우 환경 요청
4. 재설계 세션 A 개시 — 축 1 severity 스키마 + 오분류 6건 픽스쳐 + 축 3 도메인 프롬프트 재작성
5. 세션 B: orchestrator.py 우회 봉인 + signoff_minimal
6. 세션 C: frontend LogTable/ChatPanel + 24h 재측정

[traps]
- `[1. 가정 조건]`·`[2. 시뮬레이션 결과]` 같은 finance 섹션 마커는 의도된 사용자 대면 구조 — SEC1 탐지 정규식 확장 시 오탐 금지
- 로그 덤프 도메인 분포 location 111/200은 프론트 지도 자동호출 결과 — 사용자 질의 대표성과 다름
- TC3 Q1 라우팅이 admin으로 떨어진 것은 SEC1 문제가 아닌 domain_router 문제 — 두 축 혼동 금지
- /specify 커맨드는 Plan mode 진입 전제 — 미진입 상태 호출 시 계획만 제시하고 코드 변경 금지 (본문 명시)
- 미커밋 untracked 파일 다수 존재 (이전 세션의 SurveyBanner.jsx, 다른 handoff 4건) — 이번 세션에서 만들지 않았음, 건드리지 말 것
CLAUDE_HANDOFF_END -->
