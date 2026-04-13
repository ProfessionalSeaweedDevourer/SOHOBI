# 세션 인수인계 — SEC1 근본 원인 제거 완료 + Signoff 재설계 기획

## 브랜치 / PR 상태

- 작업 브랜치: `fix/park-legal-finance-label-leak` → **PR #279 MERGED** (2026-04-12 12:47 UTC)
- 현재 체크아웃: `main` (b93cdb6 → 025d74e 반영됨)
- 연관 병합 PR:
  - #277 — Sign-off SEC1 결정론적 템플릿 라벨 누출 탐지 (방어 계층)
  - #279 — Legal·Finance 에이전트 프롬프트 응답 형식 블록 제거 (근본 원인)

## 이번 세션에서 한 일

| 영역 | 내용 |
| --- | --- |
| [integrated_PARK/agents/legal_agent.py](integrated_PARK/agents/legal_agent.py) | `SYSTEM_PROMPT` 말미의 `응답 형식: [사용자 질문]/[에이전트 응답]` 블록 삭제 → Admin 스타일 "자연스럽게 서술" 지시로 교체. `{question}` 미렌더 토큰도 함께 제거 |
| [integrated_PARK/agents/finance_agent.py](integrated_PARK/agents/finance_agent.py) | `_EXPLAIN_PROMPT` 상단 `[사용자 질문]`·`[에이전트 응답]` 헤더 삭제. 사용자 질문은 괄호 힌트로 전달. `[1]/[2]/[3]/[안내]` 섹션 구조는 유지 |
| 로컬 E2E | TC1 Legal(권리금): `approved/grade=A`, 라벨 미탐지. TC2 Finance(홍대 카페): `approved/grade=A`, 라벨 미탐지. 단 로컬 `.env`는 `gpt-4.1-mini` 구세대값이라 프로덕션 `gpt-5.4` 계열과 다름 — 아래 traps 참조 |
| 기획 문서 | `/Users/eric.j.park/.claude/plans/peaceful-sparking-meteor.md` — Signoff 재설계 현실성 평가 + 6개 검토 축 + 3개 세션 분할 안 |

## 미완료 / 보류

- PR #277 TC3 (Azure E2E 정상 쿼리 회귀): 이전 세션부터 보류, 머지 후 Azure 배포에서 재검증 미실시.
- 로컬 `.env`의 모델 deployment 값이 구세대 (`gpt-4.1-mini`) — 프로덕션(`gpt-5.4` 도메인 / `gpt-5.4` signoff / `gpt-5.4-mini` chat·router)과 불일치. `docs/session-reports/2026-04-07-handoff.md` 참조.
- Rubric overhaul 5축 플랜 중 축 1·3·4·5는 모두 미착수.

## 다음 세션 인수 요약

PR #279 머지로 SEC1 근본 원인(Legal/Finance 프롬프트의 `[사용자 질문]`/`[에이전트 응답]` 출력 명시)은 제거 완료. Rubric overhaul 5축 중 축 2만 종결됐고 축 1·3·4·5(severity 가중, 도메인 프롬프트 재작성, `signoff_minimal` 신설, orchestrator 우회 봉인, 프론트 grade 연동)가 남아 있음. 재설계 방향·현실성은 `~/.claude/plans/peaceful-sparking-meteor.md`에 정리 완료 — 사용자 승인 완료. 다음 세션에서는 **프로덕션 환경(Azure `gpt-5.4` 계열)에서 PR #277·#279 회귀 검증**과 **재설계 세션 선결 과제(로그 덤프 수집 + 도메인 라우터 오분류 케이스 캡처)** 중 하나로 분기.

---

<!-- CLAUDE_HANDOFF_START
branch: main
pr: 279 (merged), 277 (merged)
prev: 2026-04-12-sec1-leak-rootcause-handoff.md
plan: ~/.claude/plans/peaceful-sparking-meteor.md

[unresolved]
- HIGH 로컬 .env(gpt-4.1-mini)와 프로덕션(gpt-5.4) deployment 불일치 — 로컬 TC는 구세대 모델에서만 검증됨, Azure E2E 미검증
- HIGH PR #277·#279 Azure 배포 회귀(TC3) 미실시 — G1-G4 루브릭이 gpt-5.4 추론 모델에서도 충족되는지 미확인
- HIGH signoff/signoff_agent.py _derive_grade — severity 가중 미반영 (축 1)
- HIGH orchestrator.py is_partial·chat 분기가 signoff 우회 (축 4)
- MED F1~F5 루브릭 극단 수치 둔감 — severity 해석 추가 필요
- MED 거부 응답 부당 자동 통과 — RJ1 blocker 필수
- MED domain_router 오분류(행정 에이전트가 법무 질문 수용) — 장기 리팩터링 필요, 로그에서 케이스 특정 선행
- MED frontend/LogTable.jsx ITEM_LABELS 백엔드 의미 어긋남 (축 5)
- LOW frontend map/ChatPanel.jsx grade 표시 전무 (축 5)

[decisions]
- PR #277(결정론 SEC1 정규식 방어)은 #279(근본 원인 제거) 이후에도 이중 방어로 유지 — 프롬프트 재회귀 대비
- Legal/Finance 프롬프트 수정은 G1-G4 내용 지시는 유지, 형식 지시만 제거하는 원칙으로 진행 (Admin 스타일 답습)
- Signoff 재설계는 단일 세션 불가 — 3세션 분할 확정 (A: 축1+축3, B: 축4+signoff_minimal, C: 축5+24h 재측정)
- 모델 분화는 재설계 범위 밖 — 전 도메인이 동일 deployment 공유

[next]
1. Azure 배포된 main에서 TC3 재검증 (Legal·Finance 프로덕션 모델 라벨 누출 및 G1-G4 충족 여부)
2. 로컬 .env를 프로덕션 값과 동기화하거나 .env.prod 샘플 커밋 — 재설계 세션의 모델 신뢰 기반
3. 최근 로그 덤프 수집 (/api/v1/logs?type=queries&limit=200) — 재설계 세션 입력물
4. domain_router 오분류 케이스 로그에서 특정 → 별도 트래킹 항목
5. 재설계 세션 A 시작: 회귀 픽스쳐 초안(도메인×3건) → 축 1 severity 스키마 → 축 3 4개 도메인 프롬프트 재작성
6. 재설계 세션 B: 축 4 우회 봉인 + signoff_minimal 신설
7. 재설계 세션 C: 축 5 프론트 연동 + 배포 후 24h 로그 재측정

[traps]
- 로컬 E2E의 "PASS"는 gpt-4.1-mini 기준 — 프로덕션 gpt-5.4 추론 모델에서 프롬프트 지시 이해·토큰 분포가 달라 루브릭 충족이 다르게 나올 수 있음
- Legal SYSTEM_PROMPT의 "별도 섹션 헤더([사용자 질문], [에이전트 응답] 등) 없이 자연스럽게 서술" 문장은 `detect_sec1_leakage` 정규식에 탐지되지만 이는 Admin과 동일한 출력 금지 지시 패턴 — 실제 draft 출력에는 나타나지 않으므로 의도된 상태. 맹목 수정 금지
- 로컬 backend 기동 시 Azure PostgreSQL 타임아웃 로그가 정상적으로 나오며 무시됨 — DB 관련 TC는 로컬에서 재현 불가
- 이전 handoff(sec1-leak-rootcause)의 signoff_legal 프롬프트 라벨 누출 지적은 원인 오기재 — 실제는 agents/*_agent.py였음 (PR #279로 확정)
CLAUDE_HANDOFF_END -->
