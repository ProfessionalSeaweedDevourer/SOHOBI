# 세션 인수인계 — F1~F5 HIGH 항목 closure

## 개요

2026-04-12 signoff 재설계 이후 **"F1~F5 로컬 회귀 스위트"** 가 HIGH 이월 항목으로 5세션 이상 연속 propagate 되고 있었다. 본 문서로 이를 **공식 closure** 처리한다.

## 닫히는 이유

2026-04-14 signoff 방어 감사([2026-04-14-signoff-defense-audit-handoff.md](2026-04-14-signoff-defense-audit-handoff.md)) 에서 Azure 프로덕션 로그 147 rejection 샘플 기준:

- finance 쿼리 18건 중 **F1 8건 / F2 8건 / F3 8건 / F4 9건 / F5 10건 실발동** 확인
- 프로덕션 모델(gpt-5.4) 이 finance 극단값을 자체 생성하지 않는다는 가정은 **반증됨**
- 방어 프롬프트는 프로덕션 로그에서 **load-bearing** 입증 완료

즉, gpt-4.1-mini 재현 스위트를 로컬에서 별도 구축할 정당성이 소멸했다. 로컬 회귀가 증명하려던 **"프롬프트 방어가 의미 있는 레이어다"** 는 명제가 프로덕션 자연 트래픽에서 이미 증명됨.

## closure 대상 항목 원문

> HIGH F1~F5 로컬 회귀 스위트 — 프로덕션 gpt-5.4 가 finance 극단값을 자체 생성하지 않을 때 방어 프롬프트의 실효성을 gpt-4.1-mini 로 내려 증명하는 로컬 pytest 스위트 구축

## 결정

- **상태: CLOSED**
- **근거: 프로덕션 로그 증거로 대체**
- **재개 조건**: 프로덕션 모델이 교체되고, 신모델이 finance 극단값을 자체 생성하지 않음이 Azure 로그에서 명백히 관측될 때. 그 시점까지는 재개 불요.

## 후속 (이 문서 이후 handoff 체인에서 반영)

- 차기 handoff 의 `[unresolved]` 에 **F1~F5 HIGH 재기재 금지**
- 대신 `[decisions]` 에 `"F1~F5 HIGH closure — 2026-04-14 감사 근거, 본 문서 참조"` 한 줄로 맥락만 유지

## 병행 세션 작업

본 세션은 [2026-04-14-signoff-defense-audit-handoff.md](2026-04-14-signoff-defense-audit-handoff.md) 의 MED 항목 (severity 로깅 default 통일) 도 함께 처리하여 **PR #301** 로 제출했다.

- 브랜치: `fix/park-logger-severity-default`
- 수정: [backend/logger.py:176,200](../../backend/logger.py#L176) `issue.get("severity")` → `issue.get("severity", "high")`
- 테스트: 29 passed (기존 `test_severity_none_when_missing` → `test_severity_defaults_to_high_when_missing` 갱신)

---
<!-- CLAUDE_HANDOFF_START
branch: fix/park-logger-severity-default
pr: 301
prev: 2026-04-14-signoff-defense-audit-handoff.md

[unresolved]
- LOW location 도메인 S1~S5 80쿼리 중 26~29건 발동 — 프롬프트 기준 과엄격 or draft 품질 조사
- LOW admin rejection 43건 > queries 22건 — 스트림 경로 중복 기록 잔존 가능 (PR #296 이후 회귀 확인)
- LOW ChatAgent content_filter 재시도 Azure 로그 관측 이월
- LOW 자연 트래픽 medium/low severity 배지 실측 — PR #301 머지 + 자연 트래픽 누적 후
- LOW escalated/is_partial final_verdict=null 프로덕션 실측
- LOW "모든 검증 통과" 단문 UX 관찰
- LOW T-CA-INJ-03 prior_history 누적 인젝션 테스트

[decisions]
- CLOSED HIGH "F1~F5 로컬 회귀 스위트" — 2026-04-14 Azure 로그 감사로 프롬프트 방어 load-bearing 입증, 재현 스위트 불필요. 재개 조건: 프로덕션 모델 교체 후 극단값 자체생성 중단이 재관측될 때. 차기 handoff 체인에서 HIGH 재기재 금지
- PR #301 — logger severity default "high" 통일 (signoff_agent 와 일관성). 2줄 + 테스트 1건 기대값 갱신

[next]
1. PR #301 리뷰·머지 대기
2. 머지 후 Azure /logs?type=rejections 에서 severity None 비중 감소 확인 (post-merge TC)
3. location S1~S5 과도 발동 조사
4. admin rejection 중복 기록 원인 확인
5. ChatAgent content_filter Azure 로그 관측

[traps]
- F1~F5 closure 는 현 프로덕션 모델(gpt-5.4) 전제. 모델 변경 시 자연 트래픽 발동률 재측정 선행 필요
- severity default 통일은 logger 표면만 수정. signoff_agent.py:126 의 `_issue_severity()` 도 default "high" 유지 — 양쪽을 동시에 바꾸지 말 것 (한쪽만 바꾸면 grade 계산과 로깅이 다시 불일치)
CLAUDE_HANDOFF_END -->
