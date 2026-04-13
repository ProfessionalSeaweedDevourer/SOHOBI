# 세션 인수인계 — Signoff severity 로그 보존 + Production QA 침투 플랜

## 개요

PR #287 (4개 도메인 signoff 프롬프트 severity 출력 지시) 실효화를 막던 로깅 단 severity 필드 누락을 수정. QA 침투 플랜을 수립하여 프로덕션 관찰 준비까지 완료했으나, 플랜의 Step 2 (TC-1~16 실제 프로덕션 실행) 는 다음 세션으로 이관.

## 브랜치·PR 상태

- 작업 브랜치: `fix/park-signoff-severity-log-preserve` (MERGED)
- PR: #288 MERGED (2026-04-12 16:27 UTC)
- 선행 PR: #287 (도메인 프롬프트 severity 출력 지시, merged)
- 워크트리: `SOHOBI-fix/park-signoff-severity-log-preserve` (정리 대상)

## 변경 요약

| 파일 | 변경 |
|------|------|
| `backend/logger.py` | `_format_rejection_history()` issues 평탄화 시 severity 필드 보존 (+1 라인) |
| `backend/tests/test_logger_rejection_history.py` | 신규 — severity 보존 / 누락 시 None / 세 레벨 round-trip 3종 |

## 검증

- `pytest tests/test_logger_rejection_history.py tests/test_signoff_severity.py tests/test_signoff_sec1_leak.py` — 38/38 PASS
- `ruff check backend/` — clean
- 프로덕션 TC4 (`/api/v1/logs` severity 필드 실제 출력) 는 머지 직후 미실행 — 다음 세션에서 Step 2 TC 실행과 함께 검증

## QA 침투 플랜 (세션 내 수립)

플랜 파일: `/Users/eric.j.park/.claude/plans/glowing-watching-book.md`

16개 TC 설계 완료:
- 2-A (4TC): 4개 도메인 severity 출력 시그널 (legal C4 / admin A2 / finance F1-F5 / location S2)
- 2-B (5TC): Finance F1~F5 극단값 침투 (연 100% ROI / 단위 혼용 / 가정 누락 / "손실 0%" / "원금 보장")
- 2-C (3TC): Grade=B 경계값 (low-only issue 시 approved=False·grade=B 조합)
- 2-D (2TC): SEC1 인젝션 시 `_FORCED_HIGH_CODES` override 검증
- 2-E (2TC): chat / is_partial signoff 우회 현재 동작 확인 (세션 B 선행 관찰)

## 다음 세션 인수 요약

1. **Step 2 TC 실행** — `$BACKEND_HOST` 대상 curl + `/api/v1/logs` 조회로 16 TC 집행. 결과를 플랜 Step 3 양식에 기록
2. **성공 기준** — 4개 도메인 모두 verdict.issues에 severity 필드 존재, F1~F5 극단값 중 ≥3/5 high 기록, grade=B 최소 1회, SEC1 강제 high 확인
3. 결과에 따라 프롬프트 조정 PR 또는 세션 B (orchestrator signoff 우회 봉인 + 재라우팅) 착수
4. 워크트리 정리: `git worktree remove ../SOHOBI-fix/park-signoff-severity-log-preserve`

---
<!-- CLAUDE_HANDOFF_START
branch: main (PR #288 merged, 작업 브랜치 삭제됨)
pr: 288 (merged)
prev: 2026-04-12-signoff-severity-prompts-handoff.md

[unresolved]
- HIGH 프로덕션 TC4 (`/api/v1/logs` rejection_history[].issues[].severity 필드 실제 출력) 미검증
- HIGH Step 2 16 TC 프로덕션 미실행 — 플랜은 `~/.claude/plans/glowing-watching-book.md`
- HIGH 로컬 gpt-4.1-mini ↔ 프로덕션 gpt-5.4 모델 불일치 지속 (로컬 TC는 근사치)
- HIGH orchestrator `is_partial`·`chat` 분기 signoff 우회 (세션 B 대상)
- HIGH 도메인 오수신(admin이 법률/재무 답) 미차단 — 세션 B에서 SCOPE1 + reroute_to 로 묶음 처리 예정
- HIGH domain_router legal↔admin 오분류 6건 픽스쳐 대기 (정리 세션)
- MED F1~F5 루브릭 본문 재설계 (이번 PR은 극단값 감지 가이드만)
- MED Part 2 산출물 (redesign-inputs.md, query-log-dump.json) 커밋 여부 미결
- MED frontend LogTable/ChatPanel severity 배지 미추가 (세션 C — PR #288로 선결 조건 해제됨)

[decisions]
- severity 로그 보존은 PR #287 관찰 목적의 일시 수정이 아니라 정당한 원복 — frontend severity 배지 작업의 선결 조건이므로 별도 1-파일 PR 로 분리함 (shadow 로깅/로컬 pytest 대안 기각)
- `_format_rejection_history`에서 severity 미지정 시 None 유지 — 기본값 "high" 주입은 엔진 `_issue_severity`의 책임이므로 로깅 단에서 덧씌우지 않음 (관찰 시 None 나오면 프롬프트 미준수 시그널로 활용)
- QA 플랜은 침투 TC 16개로 유계화 — 무제한 프로덕션 curl 남발 방지, 도메인×쟁점 교차 매트릭스 기반 최소 커버리지 우선

[next]
1. Step 2 TC 집행: curl $BACKEND_HOST/api/v1/query (4도메인×1 + finance 극단값×5 + grade=B×3 + SEC1×2 + 우회×2) → /api/v1/logs severity 관찰
2. Step 3 결과 문서화: 성공/실패 기준 미달 시 프롬프트 조정 PR (fix/park-signoff-prompt-tuning)
3. 세션 B 착수: orchestrator is_partial·chat 분기 signoff 우회 봉인 + SCOPE1 코드 + verdict.reroute_to + hop≤1 가드
4. 세션 C frontend: LogTable ITEM_LABELS + severity 배지 + ChatPanel grade 표시
5. 정리 세션: 오분류 6건 픽스쳐 + Part 2 산출물 커밋/폐기

[traps]
- SEC*·RJ*는 _FORCED_HIGH_CODES 로 엔진이 프롬프트 severity 덮어씀 → TC-14 검증 시 LLM 출력값이 아니라 엔진 override 후 값을 확인해야 함
- low severity only 이슈 시 approved=False 이지만 grade=B — 프론트/오케스트레이터가 approved 로 분기하면 retry 루프 진입. grade 분기와 의미 불일치 가능 (세션 C frontend 작업 시 재확인)
- F1~F5 극단값은 LLM 판단 의존 — 결정론적 탐지기 없음. LLM이 질의 거절/수정 권유로 응답하면 극단값 자체가 생성 안 되어 TC-5~9 질의 재설계 필요
- finance 프롬프트 472줄 — L4/L5 재설계 시 토큰 한도 확인
- .venv 는 backend/ 리네이밍 후 재생성 필요 — 신규 워크트리에서 pytest 실행 시 `pip install pytest` 선행
- logger.py severity 보존은 신규 로그에만 적용 — 과거 로그는 severity 없음 (백필 불가)
CLAUDE_HANDOFF_END -->
