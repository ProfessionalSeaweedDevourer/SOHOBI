# 2026-04-20 userchat 점검 배너 + Phase 2 전략 문서 handoff

Phase 1 절단 handoff 의 HIGH 미해결 (사용자 노출 대응) 을 **조용한 수리 + userchat 내부 배너** 수위로 확정하여 해소하고, Phase 2 (`sohobi-search-kr` koreacentral Basic 프로비저닝) 을 기획 문서 수준까지 완성.

## 브랜치·PR

- 본 세션의 작업 브랜치는 머지 후 자동 삭제됨. `main` 직접 작업 중.
- PR #322 `fix: userchat 법무·정부지원 점검 안내 배너 추가` — admin squash merged (`57ba23b`)
- PR #323 `docs: Phase 2 sohobi-search-kr koreacentral 프로비저닝 전략 문서 추가` — admin squash merged (`c54ebd4`)

## 수정 파일 요약

| 파일 | 변경 | PR |
| --- | --- | --- |
| `frontend/src/components/MaintenanceNotice.jsx` | 신규. 온보딩 팁 스타일 인라인 배너 + `useDismissible("sohobi_maintenance_2026_04_20", local)` + trackEvent view/dismiss | #322 |
| `frontend/src/pages/UserChat.jsx` | import 1줄 + `<MaintenanceNotice />` 를 `<main>` 최상단 (온보딩 팁보다 위) 삽입 | #322 |
| `docs/plans/strategic/sohobi-search-kr-provisioning.md` | 신규. cost (~$75/월), 인덱스 스키마 역산, decision gates, traps. "왜·무엇을·얼마에" 관점 (CLI 절차는 `~/.claude/plans/rg-ejp-imperative-newell.md` 가 source-of-truth) | #323 |

## 검증 결과 (PR #322)

로컬 `npm run dev` (:3000) + Playwright 자동화:

1. ✅ **TC1** — `/user` 진입 시 `role=status aria-label="서비스 점검 안내"` 배너가 대화 영역 최상단, 온보딩 팁 위에 노출
2. ✅ **TC2** — 닫기 클릭 → `localStorage.sohobi_maintenance_2026_04_20="1"` + 새로고침 후 배너 부재
3. ✅ **TC3** — 법무 질문 실행 후 main scrollHeight 정상, 배너 상단 유지
4. ✅ **TC4** — 법무 질문 응답(`A 통과`) + 배너 동시 노출 (기존 guard 흐름 회귀 없음)

백엔드 `/api/v1/query` 는 인증 필요 (401) 이지만 UI 흐름은 익명 세션으로 성공. TC 는 UI layer 에서 완료.

PR #323 은 문서 전용 — 런타임 TC 해당 없음.

## 이전 handoff unresolved 재판정

이전 handoff [2026-04-20-external-sub-phase1-cutoff-handoff.md](2026-04-20-external-sub-phase1-cutoff-handoff.md) 의 각 항목:

| 이전 항목 | 판정 | 근거 |
| --- | --- | --- |
| HIGH (carry:2) 법무+gov 에이전트 사용자 노출 대응 | **CLOSED** | 본 세션에서 "조용한 수리 + userchat 내부 배너" 수위로 결정·구현. PR #322 머지 완료 |
| MED (carry:2) legal-index + gov-programs-index 원본 데이터 확보 경로 | carried (carry:3) | 다른 팀원에게 이관됨. 본 세션 스코프 아님. carry 3회째 — 임계 경로이므로 closure 보류, 이관 작업자 진척 추적 필요 |
| MED (carry:2) sohobi9638logs Blob 아카이브 RAG 원본 단서 탐색 | **INVALIDATED** | carry 3회째. 시점 특정 목적은 이전 handoff 에서 이미 소실, 원본 데이터 확보 경로가 본 이슈와 분리되어 MED 항목 1로 수렴 — 중복 관리 불필요 |
| MED Phase 2 sohobi-search-kr go/no-go | carried (carry:1, 범위 축소) | 기획 측면 **CLOSED** (PR #323). 실행 go/no-go 만 남음 — data·cost·quota gate 3건 중 미해결 |
| LOW (carry:2) `_available` placeholder 감지 가드 | carried (carry:3) | 3회째. 현 시점 공격 표면 0 이나 `.env.example` 재주입 회귀 방지 가치 유지. 긴급도 낮으므로 여유 세션에서 처리. 다음 carry 시 closure 재검토 |

## 다음 세션 인수 요약

1. **복구 timeline 의 임계 경로는 원본 데이터 확보** — 이관 팀원 진척 확인 후 Phase 2 실행 go 결정. 배너 문구가 "약 1주" 를 약속하므로 지연 시 배너 버전 교체 필요
2. **Phase 2 go 시 승인된 플랜** (`~/.claude/plans/rg-ejp-imperative-newell.md`) 의 CLI 절차 + 신규 전략 문서의 스키마/쿼터 체크 병행
3. 복구 완료 시 [frontend/src/components/MaintenanceNotice.jsx](../../frontend/src/components/MaintenanceNotice.jsx) 컴포넌트 제거 + `UserChat.jsx` import/usage 제거 (version key 교체로 재고지도 가능)
4. placeholder 가드 PR 은 여유 시점 처리 (carry:3, LOW)

---

<!-- CLAUDE_HANDOFF_START
branch: main
pr: none
prev: 2026-04-20-external-sub-phase1-cutoff-handoff.md

[unresolved]
- MED (carry:3) legal-index + gov-programs-index 원본 데이터 확보 경로 미확정 — 이관 팀원 작업. 임계 경로이므로 closure 보류, 진척 추적 필요
- MED (carry:1) Phase 2 sohobi-search-kr 실행 go/no-go — 기획 완료, data·cost·quota gate 3건 미해결 (strategic 문서 §6)
- LOW (carry:3) gov_support_plugin + legal_search_plugin `_available` placeholder 감지 가드. 현 공격 표면 0, `.env.example` 재주입 회귀 방지 가치만 유지. 다음 carry 시 closure 재검토

[decisions]
- CLOSED: HIGH 법무+gov 사용자 노출 대응 — 조용한 수리 + userchat 내부 배너 수위로 확정. 랜딩·기능 페이지 등 외부 노출 없음. 복구 예정 약 1주 내 고지
- CLOSED: Phase 2 기획 (planning portion) — strategic 문서 완성. 실행 부분만 carry
- INVALIDATED: sohobi9638logs Blob 아카이브 RAG 원본 단서 탐색 — carry 3회째, 시점 특정 목적 소실, 원본 데이터 확보 MED 항목과 중복 관리 불필요
- 배너 dismiss key 에 날짜 버전 (`sohobi_maintenance_2026_04_20`) 포함 — 복구 후 새 고지 필요 시 version 교체만으로 전체 사용자 재노출 가능. 컴포넌트 완전 제거 전까지 유지
- 백엔드 수정 0건 원칙 — 배너는 프론트 정적 고지. 서버-driven 제어는 과도하다고 판단 (복구 timeline 1주 단기)
- gov-programs-index 벡터 필드명 `embedding` 과 legal-index `content_vector` 불일치 — 플러그인 하드코딩 기반 의도적 분리. 스키마 작성 시 필드명 대조 필수 (strategic 문서 §3-2, §7)

[next]
1. 이관 팀원의 원본 데이터 확보 진척 확인 — Phase 2 실행 go 트리거
2. 약 1주 경과 시 복구 timeline 재평가. 지연 시 배너 version key 교체 또는 문구 수정 PR
3. Phase 2 go 시: `az search service create` (승인 플랜 §Phase 2) → `text-embedding-3-large` koreacentral 쿼터 확인
4. Phase 4 `scripts/ingest_gov_programs.py` 작성 (원본 데이터 확보 후 스키마 확정되면)
5. 복구 완료 시 `MaintenanceNotice.jsx` 제거 + UserChat import/usage 제거
6. (여유 시) placeholder `_is_placeholder` 가드 PR — 재주입 회귀 방지

[traps]
- `/api/v1/query` 는 인증 필요 (401 "인증 필요"). 로컬 curl 로 검증 시 JWT 필요 또는 UI 흐름 (Playwright) 통해 익명 세션으로 검증
- 배너 dismiss 는 localStorage 기반 — 도메인·브라우저별 독립. 사용자가 여러 브라우저 접근 시 각각 닫아야 함 (알려진 한계)
- UserChat.jsx 기존 ESLint 경고 2건 (`motion` unused, `regeneratingIndex` unused) 존재 — 본 PR 과 무관. 후속 PR 에서 정리 가능하나 본 세션 스코프 아님
- strategic 문서의 CLI 명령은 예시. 실제 실행 전 `~/.claude/plans/rg-ejp-imperative-newell.md` 를 source-of-truth 로 참조 (두 문서 불일치 시 승인된 플랜 우선)
CLAUDE_HANDOFF_END -->
