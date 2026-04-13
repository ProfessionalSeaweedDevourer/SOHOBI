# 세션 인수인계 — signoff_chat 도메인 추가

## 개요

Step 2 TC-14 회귀(SEC 인젝션 → chat 라우팅 → signoff 우회)를 구조적으로 해결. 질의-레벨 패턴 가드 대신 chat 도메인을 `run_signoff` 루프에 편입. `detect_sec1_leakage`(도메인 무관)가 자동 적용되고, 신규 CH1~CH5 루브릭이 '잘못된 안내'(존재하지 않는 기능 환각, 전문 도메인 월권 답변)까지 검증.

사용자 지적 수용: CH 루브릭은 `ChatAgent.SYSTEM_PROMPT`(서비스 기능 README 성격)와 동기화되어야 하며, 이를 위한 주간 체크리스트 문서를 함께 추가.

## 브랜치 & PR

- 브랜치: `feat/park-signoff-chat-domain` (origin/main 기반)
- PR: #290 https://github.com/ProfessionalSeaweedDevourer/SOHOBI/pull/290

## 수정 파일

| 파일 | 변경 |
|------|------|
| `backend/prompts/signoff_chat/evaluate/skprompt.txt` | 신규 — L1(C1~5) + L2 chat(CH1~5) + SEC1~3 + RJ1~3 |
| `backend/prompts/signoff_chat/README.md` | 신규 — ChatAgent SYSTEM_PROMPT ↔ CH 동기화 체크리스트 |
| `backend/signoff/signoff_agent.py` | REQUIRED_CODES["chat"] 추가 |
| `backend/orchestrator.py` | chat 분기 2곳 제거, AGENT_MAP에 ChatAgent 편입 |
| `backend/tests/test_signoff_chat.py` | 신규 — REQUIRED_CODES 커버리지, SEC1 enforce, 프롬프트/README 존재 검증 |

## 검증 상태

- pytest 48건 PASS (신규 chat 10건 + 회귀 sec1_leak/severity/legal)
- ruff check + format PASS
- **미수행**: 로컬 curl TC-14/15/R5, 프로덕션 재현 (컨텍스트 제약으로 다음 세션 이관)

## 주의 — 이전 세션 untracked 파일

브랜치 시작 시 origin/main 기반으로 체크아웃했으나, 작업 트리에 이전 세션이 남긴 untracked 파일 13개(SurveyBanner.jsx, docs/session-reports/2026-04-12-*.md 다수, docs/plans/2026-04-13-sec-chat-bypass-seal.md)가 공존. 이번 커밋에는 포함 안 됨. 이 파일들은 별도 세션에서 정리 필요.

## 다음 세션 인수 요약

1. PR #290 로컬 curl E2E 검증(TC-14/15/R5) → 결과 PR 코멘트
2. merge 후 프로덕션 재현 — TC-14가 rejected+SEC1 high로 기록되는지 확인
3. handoff에서 밀어낸 HIGH 항목(low severity 로깅, F1~F5 로컬 스위트, domain_router SCOPE1) 우선순위 재평가
4. 이전 세션 untracked 13파일 정리 — 원 세션 담당자 확인

---
<!-- CLAUDE_HANDOFF_START
branch: feat/park-signoff-chat-domain
pr: 290
prev: 2026-04-13-step2-tc-results-handoff.md

[unresolved]
- HIGH PR #290 로컬 curl TC-14/15/R5 미수행 — 컨텍스트 제약으로 이관. 다음 세션 첫 작업
- HIGH 프로덕션 재현 미수행 — 머지 후 $BACKEND_HOST에서 TC-14 rejected+SEC1 high 확인 필요
- HIGH chat 레이턴시 +500ms 예상 (signoff LLM 추가 호출) — 프로덕션 TC에서 체감 측정 필요
- MED ChatAgent가 retry_prompt를 system prompt에 반영하지 않음 — retry 시 동일 draft → draft 동일 조기 종료로 완화되나, retry 가치 부족. 향후 ChatAgent.generate_draft 개선 고려
- MED 이전 세션 untracked 파일 13개 (SurveyBanner.jsx, docs/session-reports/2026-04-12-*.md, docs/plans/2026-04-13-sec-chat-bypass-seal.md) 잔존 — 원 세션 소유라 이번 PR에 포함 안 함
- (이전 세션 계승) CRIT→해결 SEC chat 우회는 본 PR로 구조적 봉인. 그러나 domain_router 오분류(SCOPE1·reroute_to·hop≤1)는 별도 세션 대상으로 미해결
- (이전 세션 계승) HIGH low severity 로깅, F1~F5 로컬 스위트, frontend severity 배지 — 미착수

[decisions]
- 질의-레벨 패턴 가드(밴드에이드) 대신 chat 도메인 전체를 signoff 루프에 편입. Why: ChatAgent draft가 detect_sec1_leakage를 아예 거치지 않아 패턴 외 SEC 누설·환각 안내 무방비. 구조 봉인이 장기적으로 정답
- CH 루브릭을 ChatAgent.SYSTEM_PROMPT와 동기화 명시. Why: SYSTEM_PROMPT가 사실상 서비스 기능 명세이며, 루브릭이 이와 어긋나면 '잘못된 안내' 검증 실효 없음. 주간 체크리스트 문서로 운영 절차화
- AGENT_MAP에 ChatAgent 편입 시 chat의 max_retries도 기본 3 유지. Why: ChatAgent가 retry_prompt를 무시해도 draft 동일 시 조기 종료 로직이 있어 무한 루프 없음. 별도 분기 불필요

[next]
1. PR #290 로컬 curl TC-14/15/R5 실행 → 결과 PR 코멘트
2. PR #290 머지 → 프로덕션 배포 → $BACKEND_HOST TC 재집행
3. domain_router 오분류 세션 착수 (SCOPE1 + reroute_to + hop≤1)
4. low severity 로깅 보존 PR (final verdict.issues 보존)
5. 이전 세션 untracked 파일 정리 — 원 세션 담당자 확인 후 결정

[traps]
- ChatAgent.generate_draft는 시그니처상 retry_prompt/previous_draft를 받지만 실제로는 무시 — retry 루프가 무의미할 수 있음. 프로덕션 관찰 시 retry_count=0 고착 주의
- chat 도메인 signoff는 LLM 호출 1회 추가 → signoff_ms 0에서 ~500ms로 증가. 기존 '즉시 응답' 기대치와 충돌 가능
- signoff_chat 프롬프트의 CH 항목은 현재 ChatAgent.SYSTEM_PROMPT의 4개 에이전트 역할 설명을 그대로 미러링 — SYSTEM_PROMPT가 변경되면 루브릭이 과거 명세로 남아 false-positive 발생
- REQUIRED_CODES 확장에도 기존 테스트(test_signoff_sec1_leak 등)는 통과. 그러나 프로덕션에서 chat 도메인이 REQUIRED_CODES 미달로 max_retries 초과 escalate할 가능성 — LLM이 17개 코드 전부 커버하는지 실측 필요
- 브랜치는 origin/main 기반이나 작업 트리에 이전 세션 untracked 파일 공존 — git add 시 와일드카드 금지, 파일 단위로 지정
CLAUDE_HANDOFF_END -->
