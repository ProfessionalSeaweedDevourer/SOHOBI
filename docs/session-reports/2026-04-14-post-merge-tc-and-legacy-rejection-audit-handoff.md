# 세션 인수인계 — PR #301 post-merge TC + legacy rejection 감사

## 개요

2026-04-14 세션. 직전 handoff ([2026-04-14-f1-f5-high-closure-handoff.md](2026-04-14-f1-f5-high-closure-handoff.md)) 의 `[next]` 를 순서대로 처리.

1. **`[next] #2`** — PR #301 (logger severity default "high") post-merge TC
2. **`[next] #3 / #4`** — location S1~S5 과도 발동 조사 + admin rejection 43 > queries 22 중복 기록 조사 (동일 원인으로 수렴)

코드 변경 없음. 브랜치는 `main`. 결과는 PR #301 코멘트로 기록.

## 브랜치 / PR

- 브랜치: `main` (읽기 전용 검증 세션)
- 관련 PR: #301 (이미 머지됨, post-merge TC 코멘트 추가)

## 수정 파일

없음. 분석 결과물만:

| 항목 | 위치 |
|------|------|
| post-merge TC 결과 | [PR #301 comment](https://github.com/ProfessionalSeaweedDevourer/SOHOBI/pull/301#issuecomment-4241491415) |
| 분석 샘플 | `/tmp/rej_post.json` (500건 rejection 로그, 로컬 일회용) |

## 핵심 발견

### PR #301 post-merge TC — ⚠️ 부분 PASS

- 머지 시각: 2026-04-14T05:19:33Z
- Azure `/api/v1/logs?type=rejections&limit=500` 조회: 총 147건, **post-merge 0건**
- Pre-merge baseline: severity=null 97.2% (138/142 issues) — PR #301 수정 타겟 실재 확인
- 자연 트래픽 누적 전이라 PR 효과 실측 불가, 재측정 대기

### location S1~S5 조사 — **전제 무효화**

- location 51 rejection rows 중 **49건이 "empty-verdict" 엔트리** (`approved=null, passed=[], issues=[]`)
- 원인: PR #296 이전 스트림 경로 double-format 버그 ([backend/tests/test_logger_rejection_history.py:42](../../backend/tests/test_logger_rejection_history.py#L42) 회귀 테스트가 정확히 문서화)
- PR #296 머지 (2026-04-13T07:58:28Z) 이후 empty 엔트리 추가 생성 0건 — **회귀 없음**
- "80쿼리 중 26~29건" 수치는 별도 테스트 스위트 산출물로 추정, 현 rejection 로그로 재현 불가

### admin rejection 43 > queries 22 — **PR #296 으로 해소**

- pre-PR#296 admin 39건 (26 empty + 13 populated) — queries 로그와의 불일치는 empty 엔트리 장기 잔존이 기여
- post-PR#296 admin rejection 유입 0건. 중복 기록 회귀 없음 확인

## 다음 세션 인수 요약

- PR #301 효과 실측은 자연 트래픽 rejection ≥ 5건 확보 후 재측정
- location S1~S5 과도 발동도 동일 — post-PR#296 rejection 샘플 누적 전까지 분석 불가
- admin 중복 기록은 클로즈 가능 (회귀 확인됨)
- Azure 로그에 pre-PR#296 empty 엔트리 영구 잔존 — 향후 집계 시 `ts ≥ 2026-04-13T07:58:28Z` 필터 필수

## 직전 handoff `[unresolved]` 재판정

| 원 항목 | 판정 | 근거 |
|---------|------|------|
| LOW location S1~S5 80쿼리 중 26~29건 발동 | **carried (carry:2, 조건부)** | 현 rejection 로그에서 재현 불가. 자연 트래픽 누적 후 재측정. carry 3 도달 시 closure 검토 |
| LOW admin rejection 43 > queries 22 중복 기록 | **resolved** | PR #296 이후 empty 엔트리 신규 유입 0건 확인. 회귀 없음 |
| LOW ChatAgent content_filter 재시도 Azure 로그 관측 | carried (carry:2) | 자연 트래픽 누적 대기 |
| LOW 자연 트래픽 medium/low severity 배지 실측 | carried (carry:2) | post-merge 트래픽 0건 |
| LOW escalated/is_partial final_verdict=null 프로덕션 실측 | carried (carry:2) | 미관측 |
| LOW "모든 검증 통과" 단문 UX 관찰 | carried (carry:2) | 미관측 |
| LOW T-CA-INJ-03 prior_history 누적 인젝션 테스트 | carried (carry:2) | 이번 세션 scope 외 |

---
<!-- CLAUDE_HANDOFF_START
branch: main
pr: none
prev: 2026-04-14-f1-f5-high-closure-handoff.md

[unresolved]
- LOW (carry:2, 조건부) location S1~S5 과도 발동 — post-PR#296 rejection 샘플 누적 전까지 분석 불가. 자연 트래픽 rejection ≥ 5건 확보 후 재측정. carry 3 도달 시 closure
- LOW (carry:2) ChatAgent content_filter 재시도 Azure 로그 관측 — 자연 트래픽 대기
- LOW (carry:2) 자연 트래픽 medium/low severity 배지 실측 — PR #301 효과 측정 포함
- LOW (carry:2) escalated/is_partial final_verdict=null 프로덕션 실측
- LOW (carry:2) "모든 검증 통과" 단문 UX 관찰
- LOW (carry:2) T-CA-INJ-03 prior_history 누적 인젝션 pytest

[decisions]
- CLOSED LOW "admin rejection 43 > queries 22 중복 기록" — PR #296 (2026-04-13T07:58:28Z) 이후 empty-verdict 엔트리 신규 유입 0건. 불일치는 pre-PR#296 legacy 엔트리 잔존 효과로 확정
- PR #301 post-merge TC = 부분 PASS (머지 후 rejection 0건, 실효 검증 불가). pre-merge baseline severity=null 97.2% 확인으로 수정 타겟은 실재했음
- location S1~S5 조사 전제("26~29건 발동") 는 현 rejection 로그로 재현 불가 — 별도 스위트 산출물 추정. carried 유지하되 후속 조사는 자연 트래픽 기반
- Azure 로그 집계 시 ts ≥ 2026-04-13T07:58:28Z 필터 필수 (pre-PR#296 empty 엔트리 영구 잔존)

[next]
1. 자연 트래픽 rejection ≥ 5건 누적 후 severity 분포 재측정 (PR #301 실효 검증)
2. 동일 샘플에서 location S1~S5 발동률 재측정
3. ChatAgent content_filter Azure 로그 관측
4. T-CA-INJ-03 prior_history 누적 인젝션 pytest 추가

[traps]
- Azure `/api/v1/logs?type=rejections` 호출 시 `Authorization: Bearer $API_SECRET_KEY` 헤더 필수. 누락 시 401 "인증 필요"
- rejection_history 집계 시 empty-verdict (approved=null, passed=[], issues=[]) 엔트리 필터 필수 — pre-PR#296 legacy 엔트리를 유효 데이터로 오집계 주의
- PR #301 효과 측정은 ts ≥ 2026-04-14T05:19:33Z 필터 후 severity=null 비중으로 판정. merged 전 baseline 과 직접 비교 금지 (PR #296 double-format 혼합 위험)
CLAUDE_HANDOFF_END -->
