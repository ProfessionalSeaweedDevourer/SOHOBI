# 재설계 세션 A 입력물 — 검증·조사 결과

**작성일**: 2026-04-12
**목적**: Signoff 재설계 A/B/C 세션 진입 전 프로덕션 상태 스냅샷 확보
**기반 PR**: #277 (결정론 SEC1 정규식), #279 (에이전트 템플릿 라벨 제거) — 둘 다 main 머지 완료

---

## 1. Azure 프로덕션 TC3 결과 (gpt-5.4 추론 모델)

목적: PR #279 머지 후 프로덕션에서 `detect_sec1_leakage` 패턴 재발 여부 확인.

엔드포인트: `POST $BACKEND_HOST/api/v1/query` (X-API-Key 인증, rate limit 10/min)

| # | 의도 도메인 | 질문 요약 | 라우팅 결과 | 응답 길이 | SEC1 누출 | 결과 |
|---|-------------|-----------|-------------|-----------|-----------|------|
| Q1 | legal | 식품위생법 영업신고 절차·처벌 | **admin** ⚠ | 957 | NONE | ✅ PASS (누출) / ⚠ 라우팅 오분류 |
| Q2 | legal | 주 15시간 미만 근로자 주휴수당·4대보험 | legal | 1991 | NONE | ✅ PASS |
| Q3 | finance | 월매출 3000만·임대료·인건비 손익분기 | finance | 1051 | NONE | ✅ PASS |
| Q4 | finance | 초기투자 1억2천·대출 이자 5.5% 회수기간 | finance | 1220 | NONE | ✅ PASS |

탐지 정규식: `[사용자 질문]`, `[에이전트 응답]`, `<<<DRAFT_{START|END}>>>`, `{{$var}}`, `<message role=`, `skprompt.txt` — 4건 모두 미탐지.

**결론**: 프로덕션 SEC1 회귀 없음. 단 domain_router가 legal 질문을 admin으로 라우팅하는 문제가 표본 1건에서 관찰됨 → 아래 3절.

---

## 2. 로그 덤프 (최근 200건)

- **파일**: [2026-04-12-query-log-dump.json](./2026-04-12-query-log-dump.json) (404KB)
- **수집 명령**: `GET $BACKEND_HOST/api/v1/logs?type=queries&limit=200` (2026-04-12 수집)
- **도메인 분포**: `location 111 / finance 46 / admin 17 / chat 15 / legal 11`
- 재설계 세션 A 회귀 픽스쳐 후보군 — 도메인×3건 선정 시 이 덤프에서 샘플링한다.

주의: location 편중은 프론트 지도 페이지에서 자동 호출되는 상권 분석 질의가 다수 포함된 결과이며, 사용자 창업 Q&A 대표성과 다르다.

---

## 3. domain_router 오분류 케이스

200건 중 키워드 휴리스틱으로 확인된 오분류 6건 (모두 라우팅 결과 ≠ 질문 내용).

| # | 타임스탬프 | 질문 | 라우팅 | 기대 | 패턴 |
|---|-----------|------|--------|------|------|
| 1 | 2026-04-12T13:13 | 카페 창업 시 식품위생법상 영업신고 절차와 위반 시 처벌 규정 | admin | legal | **법령+처벌** 키워드도 admin로 흡수 |
| 2 | 2026-04-12T12:40 | 음식점 영업신고할 때 임대차보호법 관련 주의사항 | admin | legal | 동일 — "신고" 어휘가 admin로 과적합 |
| 3 | 2026-04-09T15:15 | 일반음식점과 휴게음식점의 차이와 신고 방법 | admin | legal | 동일 |
| 4 | 2026-04-09T08:47 | 임대차 계약 조심할 점과 받을 수 있는 지원금 | legal | admin | 복합 질문 — 지원금(admin) 놓침 |
| 5 | 2026-04-09T08:45 | 홍대에서 카페 창업 뭐부터 해야 할까요 | admin | location | 지역명 무시, 막연 질문을 admin로 기본값 처리 |
| 6 | 2026-04-09T08:41 | (Case 5 중복 질의) | admin | location | 동일 패턴 반복 |

**공통 원인 가설**:
- "신고·절차" 어휘가 admin 프롬프트에 과적합 → 법률 근거 조회(legal) 의도 상실
- 지역명이 포함된 막연 질문(Case 5)은 location으로 가지 않고 기본값 admin로 떨어짐
- 복합 질문(Case 4)은 앞부분 키워드 하나로 결정됨

재설계 세션 A에서 domain_router의 라우팅 신호를 재설계할 때 위 6건을 회귀 픽스쳐로 편입한다.

---

## 4. 세션 A 진입 전 남은 차단 요인

- `.env` (로컬 `gpt-4.1-mini`) ↔ 프로덕션 (`gpt-5.4 추론`) 모델 불일치 — 로컬 재현 테스트의 프로덕션 전이 보장 없음. 세션 A 착수 전 `.env.prod` 샘플 또는 Azure 쉐도우 테스트 환경 요구.
- Legal/Finance E2E PASS는 4건 표본 — 세션 A에서 도메인×3건 픽스쳐로 확장 시 재측정 필요.

---
<!-- CLAUDE_HANDOFF_START
branch: chore/park-specify-command
pr: none (Part 1 `/specify` 커맨드만 PR 예정)
prev: 2026-04-12-signoff-redesign-handoff.md

[unresolved]
- HIGH domain_router legal↔admin 오분류 재현 6건 확보 — 세션 A 픽스쳐로 편입 대기
- HIGH `.env` 로컬(gpt-4.1-mini) ↔ 프로덕션(gpt-5.4) 모델 불일치 미해소
- MED 프로덕션 TC3 표본이 4건에 그침 — 도메인×3건 확장 필요

[decisions]
- TC3 검증 결과 SEC1 회귀 없음 → PR #277·#279 롤백 불필요, 이중 방어 유지
- domain_router 오분류는 signoff 우회(축 4)와 독립 문제로 판정 — 세션 A의 축 3 전에 라우팅 재설계 선행 고려

[next]
1. `/specify` 커맨드 PR 생성·머지 (Part 1)
2. `.env.prod` 샘플 커밋 또는 Azure 쉐도우 환경 요청
3. 세션 A 개시 — 6건 오분류 픽스쳐 + 축 1 severity 스키마 초안
4. 세션 B: orchestrator.py `is_partial`·chat 분기 signoff 우회 봉인
5. 세션 C: frontend LogTable/ChatPanel grade 표시 + 배포 후 24h 재측정

[traps]
- `[1. 가정 조건]`, `[2. 시뮬레이션 결과]` 같은 finance 섹션 마커는 SEC1 패턴이 아닌 의도된 사용자 대면 구조 — 탐지 정규식 확장 시 오탐 주의
- domain_router 휴리스틱 판정은 표본 편향 가능 — location 111/200은 프론트 자동호출 결과이므로 사용자 질의 분포가 아님
CLAUDE_HANDOFF_END -->
