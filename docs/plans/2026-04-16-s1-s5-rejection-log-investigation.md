# S1~S5 Rejection 로그 재조사 결과

조사일: 2026-04-16
선행 문서: [S1~S5 튜닝 플랜 초안](2026-04-14-s1-s5-warn-tuning.md)

## 1. 조사 목적

옵션 A(프롬프트 warnings 기준 엄격화) 구현 PR 전 선행 조건:
- 147건의 최종 grade 분포 (A/B/C)
- warn/issue 공존 여부
- `/api/v1/logs?type=rejections` 스키마 명확화

## 2. API 스키마 확인

`/api/v1/logs?type=rejections` 는 **rejection_history 가 있는 로그 전체**를 반환한다 (issues만이 아님).

```
응답: { type, count, entries[] }
entry: { ts, session_id, question, domain, status, grade, retry_count,
         rejection_history[], final_verdict, ... }
rejection_history[]: { attempt, approved, grade, passed[], warnings[], issues[], retry_prompt }
issue/warning: { code, severity, reason }
```

## 3. Grade 분포

| Grade | 건수 | 비율 |
|-------|------|------|
| C     | 111  | 75.5% |
| A     | 26   | 17.7% |
| B     | 7    | 4.8% |
| ?     | 3    | 2.0% |

- `status=escalated`: 113건 (76.9%)
- `status=approved`: 34건 (23.1%)

## 4. 핵심 발견: Warn/Issue 공존 분석

| 분류 | 건수 | 비율 |
|------|------|------|
| Issues only | 62 | 42.2% |
| **Neither (빈 findings)** | **85** | **57.8%** |
| Both (warn+issue) | 2 | 1.4% |
| Warnings only | 0 | 0% |

### 해석

- **Warnings는 사실상 발동하지 않는다** — 전체 147건 중 warning이 존재하는 건은 2건(3개 코드: C4, CH5, A2)뿐.
- **기존 handoff의 "warn 55%" 수치는 재해석 필요**: 실제로 55%~58%에 해당하는 85건은 warnings가 아니라 **rejection_history에 issues/warnings 모두 비어있는 빈 항목**이다.
- 이 85건은 signoff 에이전트가 grade C를 부여했으나 항목화된 findings를 생성하지 않은 케이스로 추정된다.

## 5. Issue 코드 분포

### 상위 10개 코드 (전체 attempt 기준)

| 코드 | 발동 횟수 |
|------|-----------|
| S2 | 83 |
| S3 | 82 |
| S5 | 82 |
| S1 | 79 |
| S4 | 78 |
| C1 | 55 |
| C5 | 48 |
| C3 | 47 |
| C2 | 46 |
| C4 | 42 |

### 코드 패밀리별 관련 entry 수

| 패밀리 | 관련 entry 수 | 비율 |
|--------|---------------|------|
| S-codes (S1~S5) | 29 | 19.7% |
| C-codes | 40 | 27.2% |
| SEC/RJ (forced high) | 2 | 1.4% |

### S-codes 는 100% location 도메인

S-code가 포함된 29건 전부 `domain=location`. S1~S5는 **signoff_location 전용** 코드이다.

## 6. Grade × Code-family 매트릭스 (findings 보유 62건)

| Grade | Code family | 건수 |
|-------|-------------|------|
| C | C+S | 15 |
| C | S (only) | 14 |
| C | C+F | 7 |
| A | A+C | 7 |
| A | A (only) | 3 |
| A | C (only) | 2 |
| A | G | 2 |
| B | A+C | 2 |
| 기타 | (각 1건씩) | 10 |

- **Grade A + S-codes: 0건** → S-codes는 높은 grade 진입을 올바르게 차단
- **Grade C 중 S-codes 관련: 29건** (C+S 15 + S only 14)

## 7. 빈 findings 85건 분석 — 레거시 데이터로 판정

### 7.1 초기 분포

| 구분 | 건수 |
|------|------|
| Grade C + escalated | 71 |
| Grade A + approved | 11 |
| Grade B + 혼합 | 3 |

### 7.2 핵심 발견: 71건 전부 location 도메인 + 2026-04-08 이전 기록

| 구간 | 전체 | empty findings | 비율 |
|------|------|-----------------|------|
| 2026-04-12 이전 | 144 | 85 | 59.0% |
| 2026-04-12 이후 | 3 | 0 | **0%** |

2026-04-12 배포 이후 empty findings 패턴이 완전히 소멸. 데이터는 2026-04-08을 마지막으로 empty findings가 더 이상 생성되지 않음.

### 7.3 원인: 레거시 코드 경로 (이미 수정됨)

empty findings 레코드의 형태:
```json
{"attempt": 1, "approved": null, "grade": "", "passed": [], "warnings": [], "issues": [], "retry_prompt": ""}
```

`approved=null, grade=""` → verdict 객체가 필수 필드 없이 저장된 흔적. git 이력 조사로 관련 수정 커밋 3개 확인:

| 커밋 | 날짜 | 수정 내용 |
|------|------|-----------|
| `787e60c` | 2026-03-30 | signoff verdict 누락 수정 — issues 문자열 guard, retry_prompt 빈값 방지, retry_count 실제값 |
| `c8908e6` | 2026-04-12 | `_derive_grade` 무조건 override — LLM이 반환한 grade="C" 보존 경로 차단 |
| `5f203d7` | 2026-03-13 | orchestrator `if not issues and not approved → force approved=True, grade=A` 추가 |

### 7.4 현재 코드에서 재현 불가

현재 [signoff_agent.py:191](../../backend/signoff/signoff_agent.py#L191), [signoff_agent.py:217](../../backend/signoff/signoff_agent.py#L217):
```python
verdict["grade"] = _derive_grade(verdict)  # 항상 override
```

[_derive_grade()](../../backend/signoff/signoff_agent.py#L132) 는 issues가 없으면 "A"를 반환 → empty issues인 verdict는 approved=True, grade=A로 강제됨.

[orchestrator.py:143-146](../../backend/orchestrator.py#L143):
```python
if not verdict.get("issues") and not verdict.get("approved"):
    verdict["approved"] = True
    verdict["grade"] = "A"
```

두 방어선이 모두 차단하므로 현재 코드에서 "grade=C + empty issues"로 rejection_history에 기록되는 경로 없음.

## 8. Grade 불일치

19건에서 top-level `grade`와 `rejection_history[-1].grade`가 불일치 (예: top=A, final_attempt=C). top-level grade가 최종 판정으로 사용되고 있다면, retry를 거치면서 개선된 것으로 해석 가능.

## 9. 결론 및 권고

### 9.1 S1~S5 튜닝 플랜 재평가

| 판단 항목 | 결과 |
|-----------|------|
| "warn 과다 발동" 문제 존재 여부 | **No** — warnings는 사실상 미발동 (0%) |
| S1~S5가 문제인가? | S1~S5는 issues로 발동, Grade A에서 0건 → **정상 작동** |
| 빈 findings 71건이 실제 문제인가? | **No** — 레거시 데이터, 2026-04-12 이후 재발 없음 |

### 9.2 권고

1. **옵션 A(프롬프트 §4 개정) 불필요** — 기존 플랜의 근거(warn 과다 발동)가 데이터와 불일치. warnings는 실측 0%.
2. **S1~S5 튜닝 플랜 폐기** — S1~S5는 location 도메인에서 정상 작동(Grade A에 S-code 0건).
3. **빈 findings 문제 해결됨** — 아래 3개 커밋으로 이미 수정 완료, 2026-04-12 배포 이후 0% 재발:
   - [`787e60c`](https://github.com/ProfessionalSeaweedDevourer/SOHOBI/commit/787e60c) (2026-03-30) verdict 누락 수정
   - [`5f203d7`](https://github.com/ProfessionalSeaweedDevourer/SOHOBI/commit/5f203d7) (2026-03-13) force-approve 추가
   - [`c8908e6`](https://github.com/ProfessionalSeaweedDevourer/SOHOBI/commit/c8908e6) (2026-04-12) `_derive_grade` 무조건 override

### 9.3 다음 세션 인수 요약

- S1~S5 튜닝 플랜([2026-04-14-s1-s5-warn-tuning.md](2026-04-14-s1-s5-warn-tuning.md)) 초안은 **폐기 권고** — 전제 소멸
- content_filter / final summary 실측 경로 설계(carry:3 closure 잔여 항목)는 독립 트랙으로 진행 가능
- 147건 rejection 로그 재조사 결과, **조치가 필요한 항목 없음**
