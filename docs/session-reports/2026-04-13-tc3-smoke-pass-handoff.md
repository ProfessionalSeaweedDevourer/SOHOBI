# 세션 인수인계 — PR #295 TC-3 프로덕션 smoke 완료

## 개요

직전 핸도프(`2026-04-13-logs-schema-signoff-handoff`)의 unresolved MED "TC-3 프로덕션 smoke 미실행" 이행. Azure Container Apps 배포 반영 후(머지 직후 run 2분 완료) `/api/v1/query` 3건 유발 → `/api/v1/logs?type=queries`에서 `signoff_ms`·`final_verdict` 스키마 실노출 확인. 코드 변경 없음 · 검증만.

## 브랜치 & PR

- 브랜치: `main` (작업 브랜치 없음 — 검증만)
- PR: #295 (MERGED, TC-3 코멘트 추가)

## 수행 내역

| 항목 | 결과 |
|------|------|
| Azure 배포 반영 확인 | `gh run list` 로 PR #295 merge 직후 `Deploy Backend to Azure Container Apps` success 확인 |
| 신규 쿼리 유발 3건 | location 1 + chat 2 (경계선 포함). 모두 first-pass approved |
| 스키마 실노출 (signoff_ms) | 3/3 양수값 (2193 / 1910 / 3784 ms) |
| 스키마 실노출 (final_verdict) | 3/3 `approved/grade/passed/warnings/issues` 객체 정상 |
| PR 코멘트 | `gh pr comment 295` 로 결과 기록 |

## 미해결 · 관측

- first-pass approved 3건 모두 `issues=[]` — low severity 포착은 이번 smoke에서 관측 안 됨. 자연 트래픽 축적 필요 (스키마 채널 자체는 정상 동작)
- escalated / is_partial 케이스는 이번 smoke에서 유발 안 됨 — `final_verdict=null` 실측 미완
- 이전 핸도프의 다른 unresolved(ChatAgent 인젝션 pytest, F1~F5 회귀, 스트림 rejection_history 이중 포맷 버그)는 그대로 이월

## 다음 세션 인수 요약

1. ChatAgent 인젝션 pytest 신규 (`backend/tests/test_chat_injection.py`, Azure content filter stub 설계)
2. F1~F5 로컬 회귀 스위트 (gpt-4.1-mini)
3. frontend severity 배지 (세션 C) — 본 TC-3 PASS로 선결조건 충족
4. 스트림 경로 `rejection_history` 이중 포맷 버그 수정 (LOW, `backend/api_server.py` 스트림 핸들러)
5. 자연 트래픽에서 `final_verdict.issues[].severity == "low"` 포착 여부 재관측

---
<!-- CLAUDE_HANDOFF_START
branch: main (작업 브랜치 없음, 검증 세션)
pr: 295 (MERGED, TC-3 완료 코멘트 추가)
prev: 2026-04-13-logs-schema-signoff-handoff.md

[unresolved]
- MED ChatAgent 인젝션 거절 pytest 부재 — Azure content filter stub 필요 (이전 핸도프에서 이월)
- HIGH F1~F5 로컬 회귀 스위트(gpt-4.1-mini) 대기 (이전 핸도프에서 이월)
- LOW 스트림 경로 log_query가 포맷된 rejection_history를 재-포맷하는 기존 버그 (이전 핸도프에서 이월)
- LOW escalated/is_partial 프로덕션 실측 미완 — 자연 유발 대기 (final_verdict=null 경로 확인 필요)
- LOW first-pass approved low severity 포착 실측 미완 — smoke 쿼리 3건 전부 issues=[], 자연 트래픽 축적 필요

[decisions]
- TC-3는 스키마 실노출(채널 정상 동작) 확인으로 PASS 판정. issues 실값은 확률적 이벤트이므로 smoke 범위에 포함 안 함

[next]
1. ChatAgent 인젝션 pytest 추가 (backend/tests/test_chat_injection.py)
2. F1~F5 로컬 회귀 스위트
3. frontend severity 배지 (세션 C) — 선결조건 충족됨, 바로 착수 가능
4. 스트림 경로 rejection_history 재-포맷 버그 수정
5. 자연 트래픽에서 low severity · escalated final_verdict=null 재관측

[traps]
- "안녕하세요"류 trivially approved 쿼리는 issues 유발 안 함 — low severity 관찰 목적으로는 경계선 쿼리 필요하나 유도도 보장 안 됨 (자연 트래픽 대기가 현실적)
- 배포 반영 확인은 `gh run list --branch main` 의 "Deploy Backend to Azure Container Apps" success 여부로만 판단 가능 (health endpoint에 배포 시각 노출 안 됨)
- TC-3 실측 직전의 최신 queries 로그 ts는 머지 이전이라 "배포 반영 안 됨"으로 오판하기 쉬움 — 신규 쿼리 유발 후 ts > merged_at 인지로 판정해야 함
CLAUDE_HANDOFF_END -->
