# 세션 인수인계 — T-CA-INJ-03 회귀 테스트 + /hand 자동 push

## 개요

2026-04-14 세션. 직전 handoff ([2026-04-14-post-merge-tc-and-legacy-rejection-audit-handoff.md](2026-04-14-post-merge-tc-and-legacy-rejection-audit-handoff.md)) 의 `[next] #4` 처리 + 워크플로 개선 2건.

1. **[next] #4** — T-CA-INJ-03 prior_history 누적 인젝션 pytest 추가 (PR #303 머지)
2. 워크플로 — `/hand` 커맨드가 `main` 브랜치에서 호출되면 신규 handoff 문서를 main 에 직접 push 하도록 자동화
3. 검증 — [docs/guides/2026-04-08-workflow-revision-instructions-for-future.md](../guides/2026-04-08-workflow-revision-instructions-for-future.md) 전 항목 이미 반영 상태 확인

## 브랜치 / PR

- 브랜치: `main` (작업 브랜치 `test/park-ca-inj-03` 는 squash merge 후 자동 삭제)
- 관련 PR: #303 (머지 완료, post-merge TC ALL PASS 코멘트 포함)

## 수정 파일

| 경로 | 변경 |
|------|------|
| [backend/tests/test_chat_injection.py](../../backend/tests/test_chat_injection.py) | `test_inj_03_retry_drops_prior_history` 추가 (69 insertions) |
| [.claude/commands/hand.md](../../.claude/commands/hand.md) | 단계 7 신설 — main 브랜치일 때 handoff 문서만 골라 자동 push |
| [docs/guides/claude-code-guide.md](../guides/claude-code-guide.md) | `/hand` 설명에 main 자동 push 동작 한 줄 추가 |

## 핵심 발견

### T-CA-INJ-03 회귀 방어선 추가

- [backend/agents/chat_agent.py:208-220](../../backend/agents/chat_agent.py#L208-L220) 의 content_filter 재시도 분기는 `safe_history` 를 새로 만들며 prior_history 를 **의도적으로 드롭** (system + 현재 user 메시지만 포함)
- 신규 테스트는 prior_history 에 인젝션 payload + prior assistant 메시지를 넣고 1차 호출에서 content_filter 예외를 발생시킨 뒤, retry history 의 `.messages.content` 에 두 prior 항목이 **없음** 을 assert
- safe prefix ("합법적인 창업 상담 요청입니다") 의 system 메시지 존재도 함께 검증
- 로컬 + post-merge main 둘 다 3/3 PASS

### /hand 자동 push 정책

- `main` 브랜치에서 호출된 경우에만 `docs/session-reports/` 하위 untracked/수정 `.md` 만 모아 커밋·push
- 코드 파일이 섞여 있으면 중단하고 경고 (사고 방지)
- 작업 브랜치에서 호출되면 push 하지 않고 "PR 에 포함시키라" 고 안내
- admin bypass 로 main 직접 push 허용 (현재 워크플로상 관리자 계정 전용)

### 워크플로 지시서 상태 점검

- [docs/guides/2026-04-08-workflow-revision-instructions-for-future.md](../guides/2026-04-08-workflow-revision-instructions-for-future.md) §2.1~2.5, §3.1~3.2, §4 전부 반영 확인
- archive tag (`archive/CHANG-2026-04-11`, `archive/NAM-2026-04-11`, `archive/CHOI*-2026-04-11` 다수) 원격에 아직 존재 — §4 회고 후 정리 단계 미실행. 클린업 필요 여부는 사용자 판단 대기

## 다음 세션 인수 요약

- 자연 트래픽 rejection ≥ 5건 누적 대기 항목은 이번에도 진전 없음 (post-PR#301 유입 0건 확인도 이번 세션에서 안 함)
- 워크플로 지시서 §4 archive tag 정리는 선택 작업으로 후보
- `/hand` 신규 동작은 이 handoff 가 첫 실사용 케이스 — main 자동 push 동작 확인 필요

## 직전 handoff `[unresolved]` 재판정

| 원 항목 | 판정 | 근거 |
|---------|------|------|
| LOW (carry:2, 조건부) location S1~S5 과도 발동 | **carried (carry:3)** | 자연 트래픽 누적 없음. carry 3 도달 — 다음 세션에서 closure 검토 필수 |
| LOW (carry:2) ChatAgent content_filter 재시도 Azure 로그 관측 | carried (carry:3) | 트래픽 대기. carry 3 — closure 검토 |
| LOW (carry:2) 자연 트래픽 medium/low severity 배지 실측 | carried (carry:3) | 트래픽 대기. carry 3 — closure 검토 |
| LOW (carry:2) escalated/is_partial final_verdict=null 프로덕션 실측 | carried (carry:3) | 미관측. carry 3 — closure 검토 |
| LOW (carry:2) "모든 검증 통과" 단문 UX 관찰 | carried (carry:3) | 미관측. carry 3 — closure 검토 |
| LOW (carry:2) T-CA-INJ-03 prior_history 누적 인젝션 pytest | **resolved** | PR #303 머지, post-merge 3/3 PASS |

---
<!-- CLAUDE_HANDOFF_START
branch: main
pr: none
prev: 2026-04-14-post-merge-tc-and-legacy-rejection-audit-handoff.md

[unresolved]
- LOW (carry:3) location S1~S5 과도 발동 — 자연 트래픽 rejection 누적 없음. 다음 세션 closure 검토
- LOW (carry:3) ChatAgent content_filter 재시도 Azure 로그 관측 — 트래픽 대기. 다음 세션 closure 검토
- LOW (carry:3) 자연 트래픽 medium/low severity 배지 실측 — 트래픽 대기. 다음 세션 closure 검토
- LOW (carry:3) escalated/is_partial final_verdict=null 프로덕션 실측 — 미관측. 다음 세션 closure 검토
- LOW (carry:3) "모든 검증 통과" 단문 UX 관찰 — 미관측. 다음 세션 closure 검토
- LOW (new) archive/*-2026-04-11 원격 태그 정리 — 워크플로 지시서 §4 회고 후 정리 단계 미실행. 사용자 판단 대기

[decisions]
- CLOSED LOW T-CA-INJ-03 — PR #303 머지, prior_history 드롭 회귀 방어 테스트 추가, post-merge 3/3 PASS
- /hand 는 main 브랜치에서 호출 시 docs/session-reports/*.md 만 모아 main 자동 push (admin bypass). 코드 파일 섞이면 중단. 작업 브랜치에서는 push 생략
- 2026-04-08 워크플로 개정 지시서는 §2.1~2.5, §3.1~3.2, §4 전량 반영 완료 상태로 확인. 잔여는 archive tag 정리뿐

[next]
1. carry:3 항목들 일괄 closure 검토 (자연 트래픽 의존 항목 5건)
2. archive/*-2026-04-11 원격 태그 정리 여부 결정
3. 자연 트래픽 rejection 누적 상태 확인 — Azure `/api/v1/logs?type=rejections` ts ≥ 2026-04-14T05:19:33Z 필터

[traps]
- Azure /api/v1/logs 호출 시 Authorization: Bearer $API_SECRET_KEY 헤더 필수
- rejection_history 집계 시 empty-verdict (approved=null, passed=[], issues=[]) 엔트리 필터 필수
- /hand 자동 push 는 main 브랜치 + 문서 전용 전제. 코드 파일이 섞인 상태에서 호출하면 중단되므로 작업 브랜치로 복귀 후 재호출
- carry:3 항목은 "트래픽 대기" 공통 원인이므로 개별 closure 보다 일괄 정책 판단이 효율적일 가능성
CLAUDE_HANDOFF_END -->
