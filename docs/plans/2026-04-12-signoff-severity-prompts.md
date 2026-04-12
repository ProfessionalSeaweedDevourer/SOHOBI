# 플랜 — Signoff 도메인 프롬프트 severity 출력 지시 (세션 A-2)

## Context

- 선행: PR #283 (`c8908e6`)이 `_issue_severity` + severity 기반 `_derive_grade`를 도입. 현재 기본값이 `high`라 모든 issue가 C로 계산됨 → grade B가 실제로 발생하지 않음 (후방호환 only).
- 목표: 4개 도메인의 `skprompt.txt`가 issue별로 `severity` 필드를 출력하도록 지시를 추가. severity 할당 기준을 루브릭별로 명문화하여, 경미한 결함은 B, 중대한 결함은 C로 분기되게 한다.
- 추가: finance 프롬프트의 F1~F5 루브릭이 "수치 존재/단위 유무" 수준만 본다 — 극단값(음수 수익률 누락, 100% 초과 확률, 비현실적 금리 등)을 감지하고 issue로 올리도록 가이드를 추가.

## 브랜치

- `feat/park-signoff-severity-prompts` (origin/main 기반 신규)
- 현재 `chore/park-specify-command`는 PR #283 미포함 → 반드시 main에서 새 브랜치로 분기

## 변경 파일

| 파일 | 변경 |
|------|------|
| `backend/prompts/signoff_legal/evaluate/skprompt.txt` | severity 할당 규칙 + 출력 스키마에 `severity` 필드 추가 |
| `backend/prompts/signoff_admin/evaluate/skprompt.txt` | 동일 |
| `backend/prompts/signoff_finance/evaluate/skprompt.txt` | 동일 + F1~F5 극단값 가이드 |
| `backend/prompts/signoff_location/evaluate/skprompt.txt` | 동일 |
| `docs/plans/2026-04-12-signoff-severity-prompts.md` | 본 문서 |

## severity 할당 설계

LLM이 각 issue에 `severity: "high"|"medium"|"low"`를 판단해 출력하도록 규칙을 명문화한다. `signoff_agent._FORCED_HIGH_CODES` (SEC*·RJ*)는 출력값과 무관하게 강제 high이므로 프롬프트에서는 권고 수준으로 둔다.

- **high** (C 등급 — 차단): C1(질문 응답성), C2(물리적 절단), C3(모순), SEC*, RJ*, G4 조항 미인용, F4 손실확률 수치 누락
- **medium** (C 등급 — 차단): C4 톤, G1 면책, G2 시점, G3 상담권고, F3 가정전제, F5 리스크경고
- **low** (B 등급 — 경고 수준): C5 할루시네이션 경계, F1 수치 제시 수준, F2 단위, 도메인 보조 항목

→ 극단적으로 엄격히 분류하면 B가 아예 안 나옴. "저수준 스타일·완결성 보조 결함" 정도는 low 허용.

## F1~F5 극단값 가이드 (finance 전용)

기존 루브릭에 "다음 극단값은 반드시 issues(F1~F5 해당 코드, severity=high)로 분류" 를 명시:

- 연 수익률 >50% / <-100% / 원금초과 손실 확률 없이 "손실 0%" 단언
- 확률 표기가 100% 초과 또는 음수
- 금리가 0% 또는 50% 초과인데 근거 가정 없음
- 월 단위와 연 단위 혼용으로 수치 2배 이상 괴리

## 재사용되는 기존 구조

- `_issue_severity` (`backend/signoff/signoff_agent.py:118`) — severity 파싱
- `_FORCED_HIGH_CODES` (`backend/signoff/signoff_agent.py:114`) — SEC*·RJ* 강제 high
- `_derive_grade` (`backend/signoff/signoff_agent.py:125`) — grade 계산
- `tests/test_signoff_severity.py` — 이미 severity 분기 22건 커버 (프롬프트 변경 후 기존 테스트가 여전히 통과해야 함)

## 검증

1. **pytest**: `cd integrated_PARK && .venv/bin/pytest tests/test_signoff_severity.py tests/test_signoff_sec1_leak.py` — 프롬프트 변경이 signoff_agent 계약(필수 코드 커버리지)을 깨지 않는지 확인. 35/35 PASS 유지.
2. **린트**: `ruff check --fix backend/` (프롬프트 수정만이라 영향 적음)
3. **프로덕션 E2E (선택)**: `BACKEND_HOST` curl로 각 도메인 1건씩 정상 질의 → severity 필드가 verdict에 출력되는지 logs 확인. 단, 로컬 ↔ 프로덕션 모델 불일치(traps) 때문에 재현 어려울 수 있음. 관찰만 하고 실패 시 다음 세션으로 이월.

## 세션 외로 이월

- F1~F5 루브릭 본문 자체 재설계 (현재 "존재 유무"만 봄 → 정확성 검증은 별도 세션)
- 도메인 라우터 오분류 6건 픽스쳐 편입
- Part 2 산출물 커밋/폐기
- orchestrator signoff 우회 봉인 (세션 B)
- frontend LogTable/ChatPanel (세션 C)

### 세션 B로 묶어 이월 — 도메인 오수신 필터링·재라우팅

- **배경**: 안내(admin) 에이전트가 법률/재무 질의를 성실히 답해버리는 케이스는 현재 RJ 루브릭으로 못 잡음. admin skprompt에 `SCOPE1`(도메인 스코프 위반) issue 코드를 추가하고, signoff verdict 스키마에 `reroute_to` 필드를 도입해 orchestrator가 지정 도메인으로 재디스패치하도록 확장 필요.
- **이번 세션에 넣지 않는 이유**: severity 축(경미/중대)과 도메인 축(재라우팅)은 직교. 한 PR에 섞으면 회귀 원인 분리 불가. 또한 재라우팅은 hop 카운트·폴백 등 orchestrator 변경을 요구하므로 세션 B(orchestrator signoff 우회 봉인)와 함께 다루는 것이 구조적으로 자연스러움.
- **세션 B 착수 시 선결 조건**: SCOPE1 코드 정의, reroute 루프 방지 가드(hop≤1 + 마지막 도메인 결과 채택 폴백), domain_router와의 권위 충돌 정책.

## 커밋 구조

- 커밋 1: 4개 skprompt.txt severity 지시 추가
- 커밋 2: finance F1~F5 극단값 가이드 추가
- PR 제목: `refactor: signoff 도메인 프롬프트 severity 출력 지시 추가`
