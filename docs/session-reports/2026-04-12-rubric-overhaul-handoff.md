# 응답 검증 루브릭 전면 개편 — 기획 세션 인수인계

## 개요

이 세션은 **코드 변경 없이 기획만 수행**했다. 현재 Sign-off 루브릭이 사실상 "무차별 통과" 상태(최근 300건 중 A=297, B=2, C=1)인 것을 확인하고, 전면 개편 플랜을 작성했다. 구현은 아직 시작하지 않았다.

## 브랜치 / PR

| 항목 | 값 |
| ---- | -- |
| 브랜치 | `main` (작업 브랜치 아직 미생성) |
| 열린 PR | 없음 |
| 커밋 | 없음 (기획만) |

## 수정 파일

없음. 플랜 문서만 생성.

| 파일 | 위치 | 성격 |
| --- | --- | --- |
| `swift-bubbling-clarke.md` | `~/.claude/plans/` | Claude Code 내부 플랜 |
| `2026-04-12-rubric-overhaul-handoff.md` | `docs/session-reports/` | 본 인수인계 |

> CLAUDE.md는 플랜 문서를 `docs/plans/YYYY-MM-DD-*.md`로도 저장하라고 지시하지만, 이번 세션은 Claude Code 플랜 모드 파일만 생성했다. 다음 세션에서 `docs/plans/2026-04-12-rubric-overhaul.md`로 복제 필요.

## 핵심 발견 (백엔드 로그 분석)

최근 300건 로그(`GET /api/v1/logs?type=queries&limit=300`) 기준:

- Grade 분포: **A=297, B=2, C=1** → 루브릭이 품질 신호 생성 실패
- Retry ≥ 1: 1건뿐 → 교정 피드백 루프 미작동

### 오탐 (괜찮은데 B)
- `admin` "AI 창업 지원금" (2026-04-09T08:02) — 장문·구조 충실한데 A2(서식 번호) 누락으로 B
- `finance` 임대료 400만 시뮬 (2026-04-09T07:19) — 완전한 시뮬레이션인데 단일 코드 누락으로 B

### 미탐 (문제 있는데 A)
1. **Sign-off 우회**: `location` "종로1·2·3·4가동 상권 분석" → 응답이 "어떤 업종을 분석할까요?" 한 줄인데 A. `orchestrator.py` L106-L132의 `is_partial=True` 분기가 sign-off 스킵
2. **수치 심각도 무시**: `finance` 임대료 500만 시뮬 → 손실확률 **41.6%**(파산 신호)인데 0.4% 사례와 동일 A. F4는 "수치 명시" 이분법만 판정
3. **거부 응답 자동 통과**: admin "ㄱㄱ" → 사전 판정 거부면 도메인 코드·RJ 모두 자동 passed, 거부 정당성 미검증
4. **법률 프롬프트 누출**: `legal` 응답들이 `[사용자 질문] ... [에이전트 응답]` 내부 라벨을 그대로 사용자에게 노출 → SEC1 위반인데 A

## 플랜 구조 (5축)

1. **축 1 — Severity 가중**: `blocker|major|minor|info` 도입, `_derive_grade` 재설계
2. **축 2 — Binary → Graded**: 맥락 조건부 활성화, F4 수치 해석, SEC1 토큰 누출 정규식 사전 검사
3. **축 3 — 우회 봉쇄**: `is_partial`/`chat` 용 `run_signoff_minimal()` 신설
4. **축 4 — 거부 정당성 재검증**: 부당 거부 시 RJ1 blocker
5. **축 5 — 프론트엔드 확장**: UserChat·MapView ChatPanel·LogViewer 3곳에 새 verdict 반영
   - `map/ChatPanel.jsx`는 **grade뿐 아니라 domain(어떤 에이전트가 응답했는지)도 전혀 미표시** — 어시스턴트 메시지 객체에 domain 자체가 저장되지 않음. GradeChip·DomainBadge·ConfidenceHint 신설 필요
   - `LogTable.jsx`의 `ITEM_LABELS`가 백엔드와 **실제로 어긋남** (A1~A5가 "지역 정보"로 매핑되어 있으나 백엔드는 "법령 조항 인용") — 병행 정정

## 다음 세션 인수 요약

- 루브릭 전면 개편 기획 완료, 구현 미착수
- 착수점 질문 대기 중 (축 1 스키마부터 순차 vs 축 2 토큰 누출 정규식 pre-check 단독 먼저)
- 백엔드 로그는 `X-API-Key: $API_SECRET_KEY` 헤더로 `$BACKEND_HOST/api/v1/logs?type=queries` 조회 (EXPORT_SECRET 아님)
- 플랜 파일: `~/.claude/plans/swift-bubbling-clarke.md` — 전체 읽기 권장

---
<!-- CLAUDE_HANDOFF_START
branch: main
pr: none
prev: none

[unresolved]
- HIGH signoff/signoff_agent.py _derive_grade — issues 1건=C의 이분법이 양질 응답 강등 유발. severity 가중으로 교체 필요
- HIGH orchestrator.py is_partial·chat 분기가 sign-off 완전 우회 — 최소 SEC·완결성 검증도 못함
- HIGH prompts/signoff_legal 계열이 `[사용자 질문]`·`[에이전트 응답]` 템플릿 라벨을 실제 응답에 누출시킴 — SEC1 의미 있는 검사로 전환 필요
- MED F1~F5 루브릭이 손실확률 41.6% 같은 극단 수치에 둔감 — existence 외 severity 해석 추가
- MED 거부 응답 사전 판정 후 도메인·RJ 자동 passed — 부당 거부가 A 통과
- MED frontend/LogTable.jsx ITEM_LABELS가 백엔드 코드 의미와 실제로 어긋남 — 동기화 메커니즘 필요
- LOW frontend map/ChatPanel.jsx는 grade를 아예 표시하지 않음 — 사용자가 B/C 구분 불가

[decisions]
- verdict JSON에 `info` 필드 신규·`severity` optional로 하위호환 유지 (기존 파서 영향 없음)
- Grade는 _derive_grade가 덮어쓰므로 LLM의 grade 필드는 참조용만 유지
- 루브릭 코드 라벨은 백엔드 단일 소스(codes.py 또는 /api/v1/signoff/codes)로 통합, 프론트는 소비자
- 축 2의 토큰 누출 검사는 LLM 판정 전에 결정론적 정규식으로 선행 (신뢰성)

[next]
1. 축 1 스키마 확장 (signoff_agent.py _derive_grade·validate_verdict, info 필드, severity 파싱) — 하위호환 필수
2. 축 2 SEC1 토큰 누출 정규식 pre-check — 즉시 효과 큰 단일 변경, 단독 PR 가능
3. 4개 도메인 프롬프트 재작성 + signoff_minimal 신규
4. orchestrator is_partial/chat 분기에 run_signoff_minimal 연결
5. 회귀 픽스쳐 테스트 (본 세션 발견 draft 6개 고정)
6. 프론트 축 5 — useStreamQuery 패스스루 → ResponseCard·ChatPanel·LogTable 순
7. 배포 후 24h 로그 분포 재측정 (목표 A<90%, retry_count>0 >5%)

[traps]
- /api/v1/logs 인증은 EXPORT_SECRET이 아니라 API_SECRET_KEY (`X-API-Key` 헤더). export 엔드포인트는 별도 키.
- chat 도메인은 orchestrator에서 sign-off 바이패스 → 보안 취약 가능성. 경량 SEC 검사도 필수.
- 프론트 grade 칩은 `ResponseCard.jsx`의 `effectiveGrade` 로직이 `grade || (isEscalated ? "C" : "A")`로 폴백 — 새 A- 상태 추가 시 이 폴백 경로 점검
- Sign-off도 LLM 기반 → 프롬프트 세밀 변경 시 회귀 가능. 결정론적 사전 검사(정규식)를 최대한 앞단에 두어 LLM 의존 최소화
CLAUDE_HANDOFF_END -->
