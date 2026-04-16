# 플랜 — Signoff location S1~S5 warn 과다 발동 튜닝 초안

> ⚠️ **INVALIDATED (2026-04-16)** — 본 플랜의 전제("warn ~55% 과다 발동")가 실측 데이터와 모순. 147건 재조사 결과 **warnings 실측 0%**, Grade C=75.5%/A=17.7%/B=4.8% 로 S1~S5 는 location 도메인의 정상 issue 코드로 작동 (Grade A 에 S-code 0건). 옵션 A(프롬프트 §4 개정) 구현 불필요. 상세: [2026-04-16 재조사](2026-04-16-s1-s5-rejection-log-investigation.md)

## Context

- 2026-04-14 carry:3 closure 조사 결과: 프로덕션 rejection 로그 147건 중 S1~S5 warnings 발동률 ~55% 실증 (S1=79, S2=83, S3=82, S4=78, S5=82).
- warnings 배열은 `approved` 에 영향을 주지 않으므로(`backend/prompts/signoff_location/evaluate/skprompt.txt:21-22`) 이들은 모두 최종 approved=true 로 종결된 케이스일 가능성이 높다. 즉 **정상 응답의 절반 이상이 warn 으로 기록**되고 있다.
- 본 플랜은 코드·프롬프트 수정 전 단계의 **설계 초안**이다. 실제 구현 PR 은 별도 세션에서 진행한다.

## 현 상태 재확인 필요 사항

실제 프롬프트 개정 PR 전에 다음 데이터 검증이 선행되어야 한다:

1. 147건이 "rejection 로그" 인지 "warnings 포함 전체 로그" 인지 확인 — `/api/v1/logs?type=rejections` 스키마상 rejection_history 가 어떤 조건으로 기록되는지 (warnings 존재만으로 기록되는지 issues 있을 때만인지).
2. warn 발동 ~55% 케이스의 최종 grade 분포 — A(warnings 0개)·B(warnings≥1 or low issues)·C(high/medium issues) 분포. B 가 과다하면 프롬프트 튜닝, C 과다면 issues 분류가 민감.
3. S1~S5 별로 warn 과 issues 의 공존 여부 — 예: S1 warn 79건 중 동일 응답에 S1 issue 가 같이 있는 케이스는 없는지 (프롬프트 §21: "반드시 한 배열에만 포함" 위반 검증).

이 데이터는 `/api/v1/logs` 확장 또는 ad-hoc SQL 조회로 획득.

## 튜닝 옵션 비교

### 옵션 A: warnings 분류 기준 엄격화 (권장)

[skprompt.txt:24-28](../../backend/prompts/signoff_location/evaluate/skprompt.txt#L24-L28) 의 §4 "판단이 애매한 경우" 조항을 개정:

- 기존: "보조 항목 ... 사용자 확인이 권장되는 경우 warnings로 분류할 수 있다" — **허용형 조항**이라 LLM 이 기본 warn 으로 기운다.
- 제안: "S1~S5 루브릭은 명시된 issue 조건에 해당하지 않으면 **반드시 passed** 로 분류한다. warnings 는 S2(기준 시점이 존재하나 분기가 아닌 연도 단위일 때) 등 명시된 조건에서만 사용한다." — **제한형 조항**으로 전환.
- S2·S3·S5 루브릭 본문에 warnings 트리거를 명시적으로 허용된 케이스만 열거.

**장점**: 프롬프트 수정만으로 가능, 백엔드 스키마·집계·UI 불변.
**단점**: LLM 튜닝 효과가 결정적이지 않음 → 발동률 절대 수치는 A/B 테스트 필요.

### 옵션 B: warn → info 강등 (신설 레벨)

- `backend/signoff/signoff_agent.py` 스키마에 `info` 배열 도입. S1~S5 "경미한 교차 확인 권장" 케이스를 info 로 분리.
- 배지·UI(`frontend/src/components/signoff/`)가 info 를 warnings 와 다르게 렌더.
- grade 파생 로직 (`_derive_grade`) 에 info 미반영.

**장점**: 데이터 구조 측면에서 명확. "경고는 진짜 경고만" 원칙 회복.
**단점**: 프롬프트·백엔드 스키마·프런트 UI 3축 동시 수정. 회귀 범위 큼. 기존 147건 로그의 warnings 재해석 이슈.

### 옵션 C: 루브릭 자체 완화

- S1 "수치 하나 이상 존재하면 통과" 처럼 현 루브릭은 이미 느슨함. 이 이상 완화하면 도메인 품질 보장 기능 약화.
- **비권장**.

## 권장 경로

1. **옵션 A 단일 PR 로 선행**. 프롬프트 문구 수정(4개 signoff 도메인 모두 유사 구조 확인 필요) → 프로덕션 배포 → 2주 관측.
2. 관측 결과 warn 발동률이 20% 미만으로 내려가면 종결.
3. 여전히 40%+ 면 옵션 B 재고.

## 변경 파일 (구현 PR 단계 예상)

| 파일 | 변경 |
|------|------|
| `backend/prompts/signoff_location/evaluate/skprompt.txt` | §4 판단 애매 조항 재작성, S2·S3·S5 warnings 트리거 열거 |
| `backend/prompts/signoff_legal/evaluate/skprompt.txt` | 동일 패턴 점검 (G1~G4) |
| `backend/prompts/signoff_finance/evaluate/skprompt.txt` | 동일 (F1~F5) |
| `backend/prompts/signoff_admin/evaluate/skprompt.txt` | 동일 |

본 플랜 자체는 `docs/plans/2026-04-14-s1-s5-warn-tuning.md` 1건 추가 (본 문서).

## 검증 절차 (구현 PR 단계)

1. 기존 147건 rejection 샘플 중 S1~S5 warn 다발 10건을 추출 → 수정된 프롬프트로 재평가 (로컬 또는 staging) → warn 감소 확인
2. `backend/tests/test_signoff_chat.py` 에 "정상 응답 → warnings 0개" 회귀 케이스 추가
3. 프로덕션 배포 후 24h 간 `/api/v1/logs?type=rejections` 로 S1~S5 warn 발동률 측정 → 튜닝 전/후 비교표 handoff 에 기록

## 세션 외로 밀어낸 항목

- 실제 프롬프트 수정 PR — 본 플랜 승인 후 별도 세션
- 옵션 B(info 레벨 신설) 설계 세부 — 옵션 A 결과 측정 후
- 다른 도메인(legal/finance/admin) warn 발동률 실측 — 이번 147건 조사는 location 만 대상이었으므로 확장 필요

## 트랩 / 주의

- 프롬프트 수정은 **Azure OpenAI 평가 일관성** 에 영향. 롤백 경로(브랜치 revert)를 미리 준비.
- `_FORCED_HIGH_CODES` (SEC\*·RJ\*) 는 엔진이 강제 high → 프롬프트 튜닝과 무관. 개정 범위에서 제외.
- S1 "수치 제시" 의 "수치" 정의가 프롬프트에 불분명함. warn 원인이 루브릭 해석 모호성이라면 문구 수정만으로는 해결 안 될 가능성.
- Azure 로그 ts 보존 ~30일 — 비교 측정은 동일 30일 윈도우에서 수행해야 bias 없음.
