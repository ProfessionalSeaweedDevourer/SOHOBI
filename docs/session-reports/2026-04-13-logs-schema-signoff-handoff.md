# 세션 인수인계 — queries 로그 스키마 확장 (PR #295)

## 개요

handoff `2026-04-13-tc14-rerun` next#1 (MED) 이행. `/api/v1/logs?type=queries` 엔트리에 `signoff_ms`·`final_verdict` 필드 추가해 first-pass approved 케이스의 low severity issues 관찰 채널 확보. PR #295 머지 완료.

## 브랜치 & PR

- 브랜치: `fix/park-logs-schema-signoff` (머지 후 자동 삭제)
- PR: #295 (MERGED 2026-04-13)
- 커밋: 1개 — "feat: queries 로그에 signoff_ms·final_verdict 필드 추가"

## 수정 파일

| 파일 | 변경 |
|------|------|
| `backend/logger.py` | `log_query`에 `signoff_ms`·`final_verdict` kwarg 추가. `_format_verdict` 헬퍼 신설 |
| `backend/orchestrator.py` | approved 반환 2곳(비스트림·스트림)에 `final_verdict=verdict` 포함 |
| `backend/api_server.py` | `log_query` 호출 2곳에서 `signoff_ms`·`final_verdict` 전달 |
| `backend/tests/test_logger_signoff_schema.py` | 신규 3케이스 |
| `docs/plans/2026-04-13-logs-schema-expand.md` | 본 PR 플랜 |
| `docs/plans/2026-04-13-tc14-rerun-post-290.md`, `docs/session-reports/2026-04-13-tc14-rerun-handoff.md` | 이전 세션 미커밋 동봉 |

## 부수 작업

- 워크트리 5개 제거 (`SOHOBI-feat/park-signoff-sec1-leak`, `-severity-schema`, `-survey-banner`, `-userchat-nav-redesign`, `SOHOBI-fix/park-signoff-severity-log-preserve`)
- 머지된 로컬 브랜치 18개 삭제 (park PR #277~#294 계열)

## 검증

- TC-1/2 pytest: `tests/test_logger_signoff_schema.py` 3케이스 + `test_logger_rejection_history.py` 3케이스 전부 PASS
- TC-4 ruff check/format: 통과
- TC-3 로컬 API smoke: **미실행** (백엔드 미기동 — 프로덕션 머지 후 실측으로 대체 필요)

## 스키마

```json
{
  "signoff_ms": 891,
  "final_verdict": {
    "approved": true, "grade": "A", "passed": ["F1"],
    "warnings": [{"code": "W1", "reason": "..."}],
    "issues": [{"code": "F2", "severity": "low", "reason": "..."}]
  }
}
```

- signoff 생략(is_partial): `signoff_ms=0`, `final_verdict=null`
- escalated: `final_verdict=null` (마지막 verdict은 `rejection_history[-1]`)

## 다음 세션 인수 요약

1. **TC-3 프로덕션 검증**: Azure 배포 반영 후 `curl /api/v1/logs?type=queries&limit=1`로 `signoff_ms`·`final_verdict` 실노출 확인
2. chat 쿼리로 first-pass approved 유도 후 `final_verdict.issues`에 low severity 포착 여부 관찰 (step2 트랩 해제 확인)
3. handoff `tc14-rerun` next#2 남음 — ChatAgent 인젝션 pytest (Azure stub)
4. 세션 C frontend severity 배지 — 이번 스키마 노출로 선결조건 충족

---
<!-- CLAUDE_HANDOFF_START
branch: main (fix/park-logs-schema-signoff 머지 완료)
pr: 295 (MERGED)
prev: 2026-04-13-tc14-rerun-handoff.md

[unresolved]
- MED TC-3 프로덕션 smoke 미실행 — Azure 배포 후 queries 로그에 signoff_ms·final_verdict 실노출 확인 필요
- MED ChatAgent 인젝션 거절 pytest 부재 (tc14-rerun에서 이관, Azure content filter stub 필요)
- HIGH F1~F5 로컬 회귀 스위트(gpt-4.1-mini) 대기 (tc14-rerun에서 이관)
- LOW 스트림 경로 log_query 호출이 이미 포맷된 rejection_history를 재-포맷하는 기존 버그 (api_server.py 스트림 핸들러) — 이번 PR 범위 외, 별도 정리 필요

[decisions]
- final_verdict 스키마는 _format_rejection_history 엔트리와 동일한 필드셋(approved/grade/passed/warnings/issues)으로 통일. retry_prompt·confidence_note 제외 — 최종 승인 건에 불필요
- escalated 경로는 final_verdict=null로 두고 rejection_history[-1]이 최종 verdict 역할. 중복 저장 회피
- signoff_ms는 orchestrator 최종 호출값 그대로 전달(round). is_partial 등 signoff 생략 시 0

[next]
1. Azure 배포 후 프로덕션 queries 로그 실노출 확인 (PR #295 TC-3 이행)
2. first-pass approved chat 쿼리로 final_verdict.issues low severity 포착 실측 (step2 트랩 해제 확인)
3. ChatAgent 인젝션 pytest 추가 — backend/tests/test_chat_injection.py
4. F1~F5 로컬 회귀 스위트 (gpt-4.1-mini)
5. frontend severity 배지 (세션 C) — 이번 스키마 노출로 선결조건 충족

[traps]
- api_server.py 스트림 경로: ev["rejection_history"]가 L537에서 이미 _format_rejection_history로 포맷된 뒤, log_query 내부에서 재-포맷됨. 재-포맷은 verdict 서브키 없는 엔트리를 빈 dict로 만듦 — 스트림 엔드포인트의 queries 로그는 rejection_history가 비어 보일 수 있음. 본 PR 범위 외
- pytest 전체 실행 시 Azure/DB 의존 테스트 53개 FAIL — env 문제, 코드 회귀 아님
- PR #295 머지 시점 TC-3 미실행 상태로 머지됨 — 프로덕션 실측이 사실상 TC-3
CLAUDE_HANDOFF_END -->
