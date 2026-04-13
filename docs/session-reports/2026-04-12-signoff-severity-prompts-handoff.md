# 세션 인수인계 — Signoff 도메인 프롬프트 severity 출력 지시 (세션 A-2)

## 개요

PR #283 (`_derive_grade` severity 반영)의 실효화. 4개 도메인 signoff skprompt.txt에 issue severity 출력 규칙을 추가하여, 이제 low severity issue만 있는 경우 grade=B로 완화되도록 프롬프트 계약을 맞췄다. finance 프롬프트에는 F1~F5 극단값 가이드를 추가.

## 브랜치·PR 상태

- 작업 브랜치: `feat/park-signoff-severity-prompts` (origin/main 기반)
- PR: #287 OPEN (2026-04-12 생성)
- 선행 PR: #283 (severity schema, merged `c8908e6`), #285 (integrated_PARK → backend 리네이밍), #286 (CI checkout v5)

## 변경 요약

| 파일 | 변경 |
|------|------|
| `backend/prompts/signoff_legal/evaluate/skprompt.txt` | severity 할당 규칙 + 출력 스키마 severity 필드 + 등급 기준 재정의 |
| `backend/prompts/signoff_admin/evaluate/skprompt.txt` | 동일 (A1/A3/A4 = high, A2/A5 = medium) |
| `backend/prompts/signoff_finance/evaluate/skprompt.txt` | 동일 + F1~F5 극단값 가이드 (>50% 수익률, 100% 초과 확률, 월/연 혼용 등) |
| `backend/prompts/signoff_location/evaluate/skprompt.txt` | 동일 (S1/S4 = high, S2/S3/S5 = medium) |
| `docs/plans/2026-04-12-signoff-severity-prompts.md` | 플랜 문서 |

## 검증

- `pytest tests/test_signoff_severity.py tests/test_signoff_sec1_leak.py` — 35/35 PASS
- `ruff check backend/` — clean
- 프로덕션 E2E는 로컬(gpt-4.1-mini) ↔ 프로덕션(gpt-5.4) 모델 불일치로 관찰 신뢰도 낮아 미실행 — 머지 후 production 로그 관찰 예정

## 다음 세션 인수 요약

1. **PR #287 머지 후 관찰** — production 로그에서 verdict에 `severity` 필드 실제 출력 여부, grade B 발생 빈도 확인
2. **세션 B 착수 권장** — orchestrator signoff 우회 봉인 + (묶음) 도메인 오수신 필터링·재라우팅. admin이 법률/재무 질의를 답해버리는 케이스에 대해 SCOPE1 issue 코드 + verdict에 `reroute_to` 필드 도입
3. 정리 세션(오분류 6건 픽스쳐, Part 2 산출물 커밋) 미진행
4. 세션 C frontend LogTable/ChatPanel 미진행

---
<!-- CLAUDE_HANDOFF_START
branch: feat/park-signoff-severity-prompts
pr: 287 (open)
prev: 2026-04-12-signoff-severity-schema-handoff.md

[unresolved]
- HIGH PR #287 머지 후 production 관찰 필요 — verdict에 severity 필드 실제 출력, grade B 발생 여부
- HIGH 로컬 gpt-4.1-mini ↔ 프로덕션 gpt-5.4 모델 불일치 지속
- HIGH orchestrator.py is_partial·chat 분기 signoff 우회 (축 4, 세션 B)
- HIGH 도메인 오수신(admin이 법률/재무 답변) 미차단 — 세션 B에 묶기로 결정
- HIGH domain_router legal↔admin 오분류 6건 픽스쳐 대기
- MED F1~F5 루브릭 본문 재설계(정확성 검증) — 이번 PR은 극단값 감지 가이드만 추가
- MED Part 2 산출물(redesign-inputs.md, query-log-dump.json) 커밋 여부 미결
- MED TC3 표본 4건 → 도메인×3건 확장 필요
- MED frontend/LogTable.jsx ITEM_LABELS 백엔드 의미 어긋남 (축 5)
- LOW frontend ChatPanel.jsx grade 표시 전무 (축 5)

[decisions]
- severity 축 설계: high=안전·답변가능성 직결, medium=형식·보조 요건, low=스타일. 극소수 코드(C5, F2)만 low에 배정 — 지나치게 low를 풀면 B 남발로 차단력 약화 우려
- F1~F5 극단값 가이드는 "존재 여부 통과 기준"을 우선하지 않도록 명시 — 수치가 있어도 극단값이면 issues로 끌어올림
- 도메인 오수신 재라우팅은 severity 축과 직교이므로 이 PR에 섞지 않음 — 세션 B에 SCOPE1 코드 + reroute_to 필드로 묶어 처리
- approved는 issues 배열 비어 있을 때만 true 유지 — low severity issue도 approved=False (등급만 완화, retry 경로는 유지)

[next]
1. PR #287 admin squash merge + production 로그 관찰 (severity 출력·grade B 발생)
2. 세션 B: orchestrator is_partial·chat signoff 우회 봉인 + 도메인 재라우팅(SCOPE1 issue + verdict.reroute_to + hop≤1 가드)
3. 정리 세션: Part 2 산출물 커밋/폐기 + 오분류 6건 픽스쳐 편입
4. 세션 C: frontend LogTable ITEM_LABELS + ChatPanel grade 표시 + 24h 재측정

[traps]
- SEC*·RJ*는 _FORCED_HIGH_CODES로 엔진이 강제 high 덮어씀 — 프롬프트가 출력한 severity는 해당 코드에서 무시됨. 프롬프트 지시는 일관성 유지 목적
- low severity issue만 있어도 approved=False — 프론트/오케스트레이터가 approved 기반으로 분기하면 retry 루프 진입. grade 기반 분기(B=완화 통과)와 의미 불일치 가능
- F1~F5 극단값 가이드는 LLM 판단에 의존 — 결정론적 탐지기 없음. 회귀 시 프로덕션 로그로만 검증 가능
- finance 프롬프트는 이제 450→472줄 — 추가 L4/L5 섹션 시 토큰 한도 확인 필요
- .venv는 backend/ 리네이밍 후 재생성 필요 (기존 integrated_PARK/.venv 경로가 shim에 박혀 있음)
CLAUDE_HANDOFF_END -->
