# 세션 인수인계 — Signoff severity 스키마 도입 (세션 A-1)

## 개요

재설계 세션 A의 첫 조각. `_derive_grade`에 severity 가중치를 반영해 low severity issue는 grade B, high/medium은 C로 세분화. 핸드오프 MED "F1~F5 루브릭 극단 수치 둔감"의 구조적 기반 마련.

## 브랜치·PR 상태

- 작업 브랜치: `feat/park-signoff-severity-schema` (머지 완료)
- PR: #283 MERGED (2026-04-12, 머지 커밋 `c8908e6`)
- 워크트리: `/Users/eric.j.park/Documents/GitHub/SOHOBI-feat/park-signoff-severity-schema` (정리 대기)

## 변경 요약

| 파일 | 변경 |
|------|------|
| `integrated_PARK/signoff/signoff_agent.py` | `_issue_severity` 신설, `_derive_grade` severity 분기, `validate_verdict` grade 일관성 재작성, `run_signoff`가 LLM grade 무시하고 항상 재계산 |
| `integrated_PARK/tests/test_signoff_severity.py` | 22건 신규 단위 테스트 (severity 분기·SEC1 override·후방호환) |
| `docs/plans/2026-04-12-signoff-severity-schema.md` | 플랜 문서 |

## 검증

- `pytest tests/test_signoff_severity.py tests/test_signoff_sec1_leak.py` — 35/35 PASS
- 프로덕션 grade B 출현 확인은 세션 A-2(프롬프트 severity 출력 지시) 이후 가능

## 다음 세션 인수 요약

1. **세션 A-2 착수 권장** — 4개 도메인 `prompts/signoff_*/evaluate/skprompt.txt`에 severity 출력 지시 추가. 현재는 LLM이 severity를 출력하지 않아 모든 issue가 기본 high로 평가되어 실제 grade B가 발생하지 않음 (후방호환만 작동).
2. 정리 세션(domain_router 오분류 6건 픽스쳐, Part 2 산출물 커밋) 미진행.
3. 축 4 orchestrator signoff 우회 봉인, 축 5 frontend LogTable/ChatPanel 미진행.
4. 워크트리 `SOHOBI-feat/park-signoff-severity-schema` 제거 가능.

---
<!-- CLAUDE_HANDOFF_START
branch: feat/park-signoff-severity-schema
pr: 283 (merged)
prev: 2026-04-12-specify-and-redesign-inputs-handoff.md

[unresolved]
- HIGH 세션 A-2 미진행 — 도메인 프롬프트에 severity 출력 지시 없어 실제 grade B 미발생, 후방호환만 작동
- HIGH domain_router legal↔admin 오분류 6건 — 픽스쳐 편입 대기
- HIGH 로컬 gpt-4.1-mini ↔ 프로덕션 gpt-5.4 모델 불일치
- HIGH orchestrator.py is_partial·chat 분기 signoff 우회 (축 4, 세션 B)
- MED F1~F5 루브릭 극단 수치 둔감 — severity 스키마 기반 확보됨, 프롬프트 개편에서 소화
- MED RJ1 blocker 필수화 미반영 (severity 강제 high로 부분 해소, 커버리지는 프롬프트에서)
- MED Part 2 산출물(redesign-inputs.md, query-log-dump.json) 커밋 여부 미결
- MED TC3 표본 4건 → 도메인×3건 확장 필요
- MED frontend/LogTable.jsx ITEM_LABELS 백엔드 의미 어긋남 (축 5)
- LOW frontend map/ChatPanel.jsx grade 표시 전무 (축 5)

[decisions]
- issue severity 기본값 "high" 고정 — 기존 verdict와 후방호환, 명시적 "low" 선언해야만 B 등급 허용
- SEC*·RJ* 코드는 severity 값과 무관하게 강제 high로 평가 — 안전·거절 신호가 소프트 다운그레이드되지 않도록 보장
- run_signoff에서 LLM이 제공한 grade를 무시하고 _derive_grade로 항상 재계산 — severity 기반 계산을 단일 권위로 유지
- approved 로직은 변경하지 않음 — issues 존재 시 approved=False 불변 유지 (low severity도 retry 대상, 등급만 완화)

[next]
1. 세션 A-2: 4개 도메인 skprompt.txt에 severity 출력 지시 + F1~F5 극단값 가이드
2. 정리 세션: Part 2 산출물 커밋/폐기 + 오분류 6건 픽스쳐 편입
3. 세션 B: orchestrator is_partial·chat 분기 signoff 우회 봉인
4. 세션 C: frontend LogTable ITEM_LABELS + ChatPanel grade 표시 + 24h 재측정

[traps]
- severity 필드 누락 시 high로 평가되므로, 프롬프트에서 severity를 출력하지 않으면 이번 PR은 no-op — A-2 전 grade B 관찰 시도 금지
- validate_verdict grade 일관성 assertion이 _derive_grade와 커플됨 — _derive_grade 수정 시 기존 grade 필드가 있는 verdict 모두 영향
- SEC1 _enforce는 grade="C" 하드코딩 + _derive_grade도 SEC1을 강제 C로 계산 → 이중 보장이지만, 강제 코드 집합(_FORCED_HIGH_CODES) 변경 시 동시 검토 필요
- approved=False + grade=B 조합 등장 가능 (low-only issue) — 프론트/오케스트레이터가 grade 기반 분기 시 retry 흐름과 불일치 위험, UI 작업(세션 C)에서 확인 필수
CLAUDE_HANDOFF_END -->
