# 세션 인수인계 — 튜닝 가설 제안 템플릿 가이드 + content_filter carry:3 CLOSED-POLICY 확정

## 개요

2026-04-16 3차 세션. 직전 handoff ([2026-04-16-s1-s5-invalidated-marker-handoff.md](2026-04-16-s1-s5-invalidated-marker-handoff.md)) 의 `[next]` 1·2순위를 단일 docs PR 로 묶어 처리.

1. **content_filter / final summary 실측 경로 (carry:3, MED)** — 선행 게이트인 Azure Application Insights 접근 가능성을 조사한 결과 레포 전반에 통합 흔적 0건. 2026-04-14 carry:3 closure 선례(항목 2)와 동일하므로 **재-closure 확정** (CLOSED-POLICY).
2. **튜닝 가설 제안 템플릿 가이드** — `docs/guides/tuning-hypothesis-template.md` 신규 작성. 2026-04-16 rejection 재조사(기각 사례)와 이번 세션의 content_filter CLOSED-POLICY 판정을 2대 케이스 스터디로 수록.

## 작업 내역

### 1. Azure App Insights 접근 가능성 조사

| 확인 항목 | 상태 | 근거 |
|-----------|------|------|
| `backend/.env` / `backend/.env.example` | ❌ 관련 키 없음 | `APPLICATIONINSIGHTS_CONNECTION_STRING`, `APPINSIGHTS_INSTRUMENTATIONKEY` 부재. Azure OpenAI·Cosmos DB·Blob·AI Search 키는 모두 있으나 App Insights 만 빠져 있음 |
| backend 코드 import | ❌ 없음 | `appinsights`, `applicationinsights`, `TelemetryClient`, `azure-monitor` 등 import·사용 흔적 0건 |
| `requirements.txt` 패키지 | ❌ 없음 | `azure-monitor`, `applicationinsights` 패키지 미설치 |
| `/api/v1/logs` 엔드포인트 기반 | 로컬 JSONL 파일 | Azure App Insights 기반 아님. `backend/logs/{queries,rejections,errors}.jsonl` 을 `load_entries_json()` 로 파싱 |

결론: **관측 수단 자체 부재**. carry 연장으로는 해결 불가능. 2026-04-14 선례에서 동일 근거로 CLOSED-POLICY 처리되었던 이슈가 carry:3 상태로 재부상한 상태이므로 **재-closure 확정**.

재개 조건: 프로덕션 Container Apps 에 App Insights 리소스 부착 + SDK 통합 + KQL 쿼리 권한 확보. 모두 조직·인프라 결정 영역이므로 별도 트랙으로 이관.

### 2. 튜닝 가설 제안 템플릿 가이드 작성

- 파일: `docs/guides/tuning-hypothesis-template.md` (신규)
- 명명: 기존 `docs/guides/` 영문 kebab-case 컨벤션 준수
- 구조: [routing-debug.md](../guides/routing-debug.md) 의 "5단계 워크플로우 + 실제 사례" 패턴을 3단계 버전으로 차용
- 포함 섹션: 언제 사용 / 워크플로우 요약 / 1단계 실측 / 2단계 git 이력 / 3단계 배포 전후 비교 / 판정 규칙 / 결정 트리 / 실제 사례 2건 / 함정
- 케이스 스터디 2건:
  - 사례 1: 2026-04-16 S1~S5 재조사 → **기각(INVALIDATED)**
  - 사례 2: content_filter 실측 경로 → **CLOSED-POLICY**

## 수정 파일

| 파일 | 변경 |
|------|------|
| `docs/guides/tuning-hypothesis-template.md` | 신규 (3단 절차 + 판정 규칙 + 결정 트리 + 케이스 스터디 2건 + traps) |
| `docs/session-reports/2026-04-16-tuning-guide-and-cf-closure-handoff.md` | 신규 (본 문서) |

코드 변경 없음. 순수 docs PR.

## 직전 handoff `[unresolved]` 재판정

| 원 항목 | 판정 | 근거 |
|---------|------|------|
| MED (carry:3) content_filter / final summary 실측 경로 설계 | **resolved (CLOSED-POLICY)** | Azure App Insights 통합 0건 실증. 2026-04-14 선례 재사용. 재개 조건은 App Insights 조직적 도입 |

## 직전 handoff `[next]` 재판정

| 원 항목 | 판정 | 근거 |
|---------|------|------|
| 1. content_filter / final summary 실측 경로 재개 | **resolved (CLOSED-POLICY)** | 본 세션 처리 |
| 2. 튜닝 가설 제안 템플릿 가이드 | **resolved** | `docs/guides/tuning-hypothesis-template.md` 신규 반영 |
| 3. INVALIDATED 배너 패턴 재사용 | **carried** | 발생 시점 대응이므로 선제 작업 없음. 다음 플랜 무효화 시 적용 |

## 다음 세션 인수 요약

1. **App Insights 도입 검토** (선택) — content_filter 실측이 다시 필요해지는 시점에 인프라 팀과 리소스 부착 논의. SDK 통합 시 가이드의 "관측 수단" 가정을 갱신해야 함
2. **가이드 실사용 피드백 수집** — 다음 튜닝 가설 PR 초안을 쓸 때 3단 절차를 적용한 뒤 누락된 항목·불편한 단계가 있으면 가이드 갱신
3. 향후 플랜 무효화 시 [2026-04-14 carry3 closure](2026-04-14-carry3-closure-handoff.md) 와 [본 세션의 CLOSED-POLICY 재-closure](2026-04-16-tuning-guide-and-cf-closure-handoff.md) 의 두 패턴 중 상황에 맞는 것을 선택 적용

---
<!-- CLAUDE_HANDOFF_START
branch: docs/park-tuning-guide-and-cf-closure
pr: TBD
prev: 2026-04-16-s1-s5-invalidated-marker-handoff.md

[decisions]
- CLOSED-POLICY content_filter / final summary 실측 경로 — Azure App Insights 통합 0건 실증(env·requirements·import 전 영역 부재). 2026-04-14 carry:3 closure 선례(항목 2) 와 동일 근거로 재-closure. 재개 조건은 프로덕션 App Insights 리소스 부착 + SDK 통합 + KQL 권한 확보
- CLOSED 튜닝 가설 제안 템플릿 가이드 — docs/guides/tuning-hypothesis-template.md 신규. 3단 절차(실측 → git 이력 → 배포 전후) + 판정 규칙(확정/기각/보류/CLOSED-POLICY) + 케이스 스터디 2건 수록
- 가이드 구조는 routing-debug.md 의 "워크플로우 + 실제 사례" 패턴 차용. 1단계 로그 조회는 backend-logs.md 링크로 위임하여 중복 서술 회피

[next]
1. App Insights 도입 필요성 재평가 — content_filter 실측 재개 시점 또는 다른 Azure 로그 요구가 생길 때
2. 튜닝 가설 PR 초안 작성 시 본 가이드 3단 절차 적용 → 누락·불편 항목 있으면 가이드 갱신
3. 향후 플랜 무효화 시 INVALIDATED 배너(PR #304 패턴) 또는 CLOSED-POLICY(carry:3 패턴) 중 상황에 맞게 선택

[traps]
- CLOSED-POLICY 는 영구 폐기가 아님 — 재개 조건(App Insights 도입)을 handoff 산문에 명시. 다음 세션이 "완전 종결" 로 오독하면 재개 기회를 놓침
- 가이드의 "표본 크기 ≥ 50" 기준은 경험칙. 예외 케이스(프로덕션 긴급 이상 등)는 기준 적용 보류 가능 — 기계적 적용 금지
- 가이드 내 상대 링크는 `docs/guides/` 기준. 다른 디렉토리에서 재참조 시 접두 필요 (2026-04-16 INVALIDATED 배너 세션 trap 과 동일 패턴)
- 2026-04-14 carry:3 closure handoff 에서 이미 동일 이슈가 CLOSED-POLICY 처리되었음에도 carry:3 으로 재부상한 경위 주의 — handoff 간 decisions 누락으로 인한 재발. 앞으로 CLOSED-POLICY 판정은 decisions 에 반드시 명시
CLAUDE_HANDOFF_END -->
