# 세션 인수인계 — 147건 rejection 로그 재조사 + S1~S5 튜닝 플랜 무효화

## 개요

2026-04-16 세션. 직전 handoff ([2026-04-14-archive-cleanup-and-s1-s5-plan-handoff.md](2026-04-14-archive-cleanup-and-s1-s5-plan-handoff.md)) 의 `[next]` 1순위 항목인 "147건 rejection 로그 재조사"를 완결. 조사 결과 S1~S5 튜닝 플랜의 전제(warn 55% 과다 발동)가 잘못되었음이 확인되어 후속 구현 PR은 불필요로 판정.

## 작업 내역

### 1. /api/v1/logs?type=rejections 스키마 확인

- `API_SECRET_KEY` 헤더로 인증 (X-API-Key)
- 응답 구조: `{ type, count, entries[] }`
- `rejection_history[]` 의 각 attempt 는 `{ attempt, approved, grade, passed, warnings, issues, retry_prompt }` 포맷
- "warnings 포함 로그" 전체를 반환 (issues만이 아님)

### 2. Grade 분포 및 warn/issue 공존 분석

147건 기준:
- Grade C: 111 (75.5%), A: 26 (17.7%), B: 7 (4.8%)
- **Warnings 실측 0%** (147건 중 warning 발동 건은 2건뿐, 코드 3개만)
- Issues only: 62 (42.2%), 빈 findings: 85 (57.8%)

### 3. 빈 findings 85건 원인 규명 (carry:3 closure 잔여 실측)

- 71건 전부 `domain=location`, `grade=C`, `status=escalated`, empty rejection_history
- rejection_history 엔트리가 `approved: null, grade: ""` — verdict 필드 누락 흔적
- **수정 커밋 3개 추적**:
  - `5f203d7` (2026-03-13) orchestrator force-approve 추가
  - `787e60c` (2026-03-30) signoff verdict 누락 수정
  - `c8908e6` (2026-04-12) `_derive_grade` 무조건 override
- 배포 전후 검증: 2026-04-12 이전 59% → 이후 **0%** (완전 소멸)

### 4. S1~S5 튜닝 플랜 판정

- 기존 플랜의 전제("warn 과다 발동")가 데이터와 불일치
- S1~S5 는 location 도메인의 정상 issue 코드로 작동 (Grade A에 S-code 0건)
- 옵션 A(프롬프트 §4 개정) 불필요 → **2026-04-14 플랜 초안 폐기 권고**

## 수정 파일

| 파일 | 변경 |
|------|------|
| `docs/plans/2026-04-16-s1-s5-rejection-log-investigation.md` | 신규 (9개 섹션, 재조사 결과·근본 원인·폐기 권고) |
| `docs/session-reports/2026-04-16-rejection-log-reinvestigation-handoff.md` | 신규 (본 문서) |

코드 변경 없음. 조사·문서화만 수행.

## 직전 handoff `[next]` 재판정

| 원 항목 | 판정 | 근거 |
|---------|------|------|
| 1. 147건 rejection 로그 재조사 | **resolved** | 이번 세션에서 Azure 로그 조회·grade 분포·warn/issue 공존 분석 완료 |
| 2. signoff §4 조항 개정 PR (옵션 A) | **invalidated** | 전제(warn 과다 발동)가 실측 데이터(warn 0%)와 모순. 구현 불필요 |
| 3. content_filter / final summary 실측 경로 | **carried** | carry:2 — 독립 트랙으로 분리 필요. S1~S5 종결로 우선순위 재평가 |

## 다음 세션 인수 요약

1. content_filter / final summary 실측 경로 설계 — Azure App Insights 접근 방법부터. carry:2, 우선순위 중간
2. S1~S5 튜닝 플랜 초안 ([2026-04-14-s1-s5-warn-tuning.md](../plans/2026-04-14-s1-s5-warn-tuning.md))의 본문에 "INVALIDATED" 마커 추가 고려 (또는 2026-04-16 조사 문서 링크 추가)
3. 이번 조사로 rejection 로그 조사 루틴이 확립되었으므로, 향후 튜닝 가설 제안 전 동일 패턴(로그 조회 → git 이력 크로스체크)을 템플릿화 가능

---
<!-- CLAUDE_HANDOFF_START
branch: main
pr: none
prev: 2026-04-14-archive-cleanup-and-s1-s5-plan-handoff.md

[unresolved]
- MED (carry:2) content_filter / final summary 실측 경로 설계 — Azure App Insights 접근 방법부터 미정. carry:3 closure 에서 CLOSED-POLICY 처리된 후 독립 트랙으로 대기

[decisions]
- CLOSED 147건 rejection 로그 재조사 — grade C=75.5%/A=17.7%/B=4.8%, warnings 실측 0%, 빈 findings 85건은 2026-04-12 배포 후 0% 재발로 레거시 판정
- INVALIDATED S1~S5 warn 튜닝 옵션 A — "warn 과다 발동" 전제 자체가 데이터와 모순 (warnings 실측 0%). 프롬프트 §4 개정 불필요
- 빈 findings 71건 원인: 수정 커밋 3개(5f203d7, 787e60c, c8908e6)로 이미 해결. 현재 signoff_agent.py:191/217 + orchestrator.py:143-146 이중 방어로 재현 불가
- /api/v1/logs?type=rejections 스키마: rejection_history 보유 로그 전체 반환 (issues만이 아님). X-API-Key 헤더로 API_SECRET_KEY 인증

[next]
1. content_filter / final summary 실측 경로 설계 재개 — Azure App Insights 접근부터 (carry:2)
2. 2026-04-14 S1~S5 튜닝 플랜 문서에 INVALIDATED 주석 추가 또는 2026-04-16 조사 문서 교차 링크
3. 향후 튜닝 가설 제안 시: (a) 실측 로그 조회 → (b) git 이력 크로스체크 → (c) 배포 전후 비교 순서를 템플릿화

[traps]
- rejection 로그의 retry_count 와 rejection_history 길이가 불일치 가능 — 구 코드의 `max_retries` 하드코딩 흔적. 최신 코드는 `len(rejection_history)` 로 일관됨
- Azure 로그 ts 보존 ~30일 → 2026-03 중순 이전 데이터는 이미 소실. 과거 패턴 재조사 시 시점 제약
- _FORCED_HIGH_CODES (SEC*·RJ*) 는 severity 무시하고 강제 high 처리 — 프롬프트/루브릭 튜닝 시 이 코드들은 범위 제외해야 회귀 방지
- 147건 empty findings 는 "legacy 잔재"이므로 이후 동일 데이터를 근거로 한 튜닝 가설은 모두 무효. 신규 가설 제안 시 2026-04-12 이후 데이터로만 판단할 것
CLAUDE_HANDOFF_END -->
