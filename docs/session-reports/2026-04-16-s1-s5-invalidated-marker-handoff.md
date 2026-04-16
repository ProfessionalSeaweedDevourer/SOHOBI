# 세션 인수인계 — S1~S5 플랜 INVALIDATED 마커 부착 + survey banner 업데이트

## 개요

2026-04-16 후속 세션. 직전 handoff ([2026-04-16-rejection-log-reinvestigation-handoff.md](2026-04-16-rejection-log-reinvestigation-handoff.md)) 의 `[next]` 2순위("S1~S5 튜닝 플랜 INVALIDATED 마커 추가")를 단일 PR 로 완결. 로컬에 남아 있던 `SurveyBanner.jsx` 참여 수 카운터 업데이트(`79 → 83`)를 동일 PR 에 묶어 함께 머지.

## 작업 내역

### 1. INVALIDATED 배너 부착

`docs/plans/2026-04-14-s1-s5-warn-tuning.md` 제목 직하단에 블록쿼트 배너 1줄 삽입. 배너는 무효화 사유(warn 실측 0%, Grade C=75.5%/A=17.7%/B=4.8%)와 2026-04-16 재조사 문서로의 상대 링크를 포함. 단독 열람 시에도 전제 붕괴 사실을 즉시 인지 가능하도록 함.

### 2. SurveyBanner 참여 수 업데이트

`frontend/src/components/SurveyBanner.jsx` 의 `CURRENT` 상수를 `79 → 83` 으로 갱신. 단순 콘텐츠 업데이트.

### 3. 이전 [unresolved] 재판정

| 원 항목 | 판정 | 근거 |
|---------|------|------|
| MED (carry:2) content_filter / final summary 실측 경로 설계 | **carried → carry:3** | 이번 세션에서 착수 못함. carry:3 closure 가능성 검토 결과: Azure App Insights 접근 권한 자체가 선행 차단이므로 closure 불가, 진입 시점 판단 보류. 다음 세션에서 Azure 접근 가능성부터 확인 필요 |

### 4. 이전 [next] 재판정

| 원 항목 | 판정 | 근거 |
|---------|------|------|
| 1. content_filter / final summary 실측 경로 설계 | **carried** | 미착수 (carry:3) |
| 2. S1~S5 튜닝 플랜 INVALIDATED 주석 추가 | **resolved** | PR #304 로 반영 |
| 3. 튜닝 가설 제안 템플릿화 | **carried** | 미착수, 우선순위 재평가 필요 |

## 수정 파일

| 파일 | 변경 |
|------|------|
| `docs/plans/2026-04-14-s1-s5-warn-tuning.md` | 제목 직하단에 INVALIDATED 블록쿼트 배너 1줄 추가 |
| `frontend/src/components/SurveyBanner.jsx` | `CURRENT` 상수 `79 → 83` |

## 다음 세션 인수 요약

1. **content_filter / final summary 실측 경로 (carry:3)** — Azure App Insights 접근 가능성 확인을 최우선 게이트로. 접근 불가 판정이면 closure 판단.
2. **튜닝 가설 제안 템플릿 가이드** — `docs/guides/` 에 (a) 실측 로그 조회 → (b) git 이력 크로스체크 → (c) 배포 전후 비교 3단 절차 문서화. 2026-04-16 재조사를 케이스 스터디로 인용. 약 1시간, 독립 세션 권장.
3. 향후 플랜 무효화 시 본 세션의 INVALIDATED 배너 패턴을 재사용 (제목 직하단 블록쿼트 + 재조사 문서 상대 링크).

---
<!-- CLAUDE_HANDOFF_START
branch: main
pr: 304 (merged)
prev: 2026-04-16-rejection-log-reinvestigation-handoff.md

[unresolved]
- MED (carry:3) content_filter / final summary 실측 경로 설계 — Azure App Insights 접근 가능성이 선행 차단. 다음 세션에서 접근 가능성 확인 후 불가 판정 시 closure 검토

[decisions]
- CLOSED S1~S5 튜닝 플랜 INVALIDATED 마커 부착 — PR #304 머지로 반영. 제목 직하단 블록쿼트 배너 + 2026-04-16 재조사 문서 상대 링크 패턴 확립
- 플랜 무효화 시 본문 삭제·수정 대신 상단 배너 부착 방식 채택 — 이유: 원 플랜의 고민 흐름을 보존하면서 단독 열람자에게 무효 사실을 즉시 전달

[next]
1. content_filter / final summary 실측 경로 설계 재개 — Azure App Insights 접근부터 (carry:3, closure 검토 필요)
2. 튜닝 가설 제안 템플릿 가이드 작성 — docs/guides/ 에 신규 1건. 2026-04-16 재조사를 케이스 스터디로 활용
3. 향후 플랜 무효화 발생 시 본 세션의 INVALIDATED 배너 패턴 재사용

[traps]
- docs/* 브랜치에 frontend 변경을 섞어 squash merge 했으므로 branch 타입·PR 범위 일관성 기준으로는 약간의 위반. 단발성 콘텐츠 업데이트(상수 1개)라 허용했으나 기능 변경 규모에서는 분리 권장
- INVALIDATED 배너는 링크 텍스트에 절대 경로가 아닌 상대 경로(`2026-04-16-...md`)를 사용해야 함 — `docs/plans/` 내부 렌더와 GitHub 렌더 모두 정상. 다른 디렉토리에서 참조 시에는 `docs/plans/` 접두가 필요
- content_filter 실측 경로 항목은 이미 carry:3 에 도달. 다음 세션에서 Azure 접근 불가 확정 시 CLOSED-POLICY 처리 필요 (2026-04-14 carry:3 closure 선례 참조)
CLAUDE_HANDOFF_END -->
