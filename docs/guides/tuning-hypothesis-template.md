# 튜닝 가설 제안 템플릿 가이드

프롬프트·규칙·임계값 등 파라미터 튜닝을 제안하기 전에 거쳐야 하는 3단 검증 절차. "로그를 봤더니 X 가 많아 보인다" 식의 인상 기반 가설이 실제로는 데이터와 모순인 경우가 반복 발견되어(2026-04-16 S1~S5 사례) 템플릿화.

## 언제 사용하는가

- 백엔드 규칙(예: signoff rubric, domain_router, location_agent 임계값) 의 튜닝 PR 초안을 쓰기 직전
- 로그에서 "과다 발동" / "과소 발동" / "분포 이상" 이 보인다고 판단하여 변경 제안을 준비할 때
- carry 항목이 "로그 기반 조사" 를 전제로 할 때 (조사 후 즉시 closure 판정이 필요할 수 있음)

## 워크플로우 요약

```
1. 실측 로그 수집  →  2. git 이력 크로스체크  →  3. 배포 전후 비교 및 판정
```

각 단계는 이전 단계 결과가 없으면 무의미하다. 특히 1단계 표본이 충분하지 않으면 2·3단계는 생략하고 조사 자체를 보류한다.

---

## 1단계: 실측 로그 수집

가설을 검증할 수 있을 만큼의 표본을 먼저 확보한다.

### 조회 명령

`/api/v1/logs` 엔드포인트 사용. 호출 방법·인증 키·엔드포인트 종류는 [backend-logs.md](backend-logs.md) 참조.

- `type=queries`: 도메인 라우팅·grade·status 분석용
- `type=rejections`: rejection_history·warnings·issues 분석용
- `type=errors`: 예외·실패 경로 분석용

### 집계 기준 체크리스트

| 항목 | 기준 |
|------|------|
| 기간 | 관심 구간 전체 + 비교 대조군(배포 전/후) 포함 |
| 표본 크기 | 최소 50건 이상. 미만이면 조사 보류 |
| 필드 누락 | `approved: null`, `grade: ""` 등 legacy 흔적 여부 |
| 도메인 편중 | 한 도메인에 편중되어 있다면 원인 별도 규명 |

### 주의

- `/api/v1/logs?type=rejections` 는 **rejection_history 보유 로그 전체**를 반환한다. "issues 발동 로그" 만이 아니다. warnings 만 있는 로그도 포함될 수 있음을 유의.
- Azure 로그 ts 보존은 **약 30일**. 과거 패턴 재조사는 시점 제약을 먼저 확인.

---

## 2단계: git 이력 크로스체크

로그에서 이상이 감지되면, 해당 필드/로직을 건드린 최근 커밋을 찾아 **현재 데이터가 legacy 잔재인지** 판단한다.

### 추적 명령

```bash
# 필드/함수 이름으로 커밋 검색
git log --oneline --all --grep="<키워드>"
git log -S"<함수명 또는 필드명>" --oneline

# 특정 파일의 변경 이력
git log --oneline -- backend/signoff/signoff_agent.py
git blame backend/signoff/signoff_agent.py | rg "<line 조건>"
```

### 확인 항목

| 항목 | 확인 방법 |
|------|-----------|
| 최근 수정일 | 이상 로그의 ts 가 수정 커밋 **이전**인가 **이후**인가 |
| 방어 로직 중첩 | 동일 이슈를 여러 파일에서 이중 방어하는지 (재발 불가 증거) |
| force-\* / override | `force-approve`, `override`, 무조건 분기 등 강제 경로 식별 |

시점이 수정 이전이라면 그 이상은 **이미 해결된 레거시** 가능성이 높다. 이 경우 3단계에서 배포 전후 비교로 확증한다.

---

## 3단계: 배포 전후 비교 및 판정

2단계에서 수정 커밋을 특정했으면, 해당 커밋의 **배포 시점 전/후** 동일 이상이 나타나는지 집계한다.

### 비교 템플릿

| 지표 | 배포 이전 | 배포 이후 | 판정 |
|------|-----------|-----------|------|
| 이상 로그 비율 | X% | Y% | Y ≪ X 면 해결됨 |
| 표본 크기 | N1 | N2 | 양쪽 모두 > 50 권장 |

### 판정 규칙

| 판정 | 조건 | 후속 |
|------|------|------|
| **확정** | 배포 후에도 이상이 유지·증가. 튜닝 제안 유효 | PR 초안 작성 |
| **기각** | 배포 후 이상이 사라짐. 가설은 legacy 데이터 기반 | INVALIDATED 마커 + 재조사 문서 링크 |
| **보류** | 표본 부족·기간 부족. 판단 불가 | carry 연장 또는 대기 |
| **CLOSED-POLICY** | 관측 수단 자체가 없어 carry 연장으로도 해결 불가 | 별도 트랙(예: 수동 QA, 외부 로그 시스템) 이관 |

`CLOSED-POLICY` 정의 및 선례는 [../session-reports/2026-04-14-carry3-closure-handoff.md](../session-reports/2026-04-14-carry3-closure-handoff.md) 참조.

---

## 결정 트리

```
[가설 착안]
    │
    ▼
1단계: 실측 로그 조회
    │
    ├─ 표본 < 50  ─────────────────▶ 보류 (조사 중단)
    │
    ▼
2단계: git 이력 크로스체크
    │
    ├─ 관측 수단 없음  ─────────────▶ CLOSED-POLICY (별도 트랙)
    │
    ▼
3단계: 배포 전후 비교
    │
    ├─ 배포 후 이상 지속  ──────────▶ 확정 (튜닝 PR 초안)
    ├─ 배포 후 이상 소멸  ──────────▶ 기각 (INVALIDATED)
    └─ 표본·기간 부족    ──────────▶ 보류 (carry 연장)
```

---

## 실제 사례

### 사례 1: 2026-04-16 S1~S5 rejection 재조사 — 가설 기각 (INVALIDATED)

**최초 가설**: S1~S5 location 규칙이 과다 발동(warn 55%)되어 signoff §4 조항 개정 필요

**3단계 적용 결과**:

1. **실측**: 147건 rejection 로그 조회. 결과 — warnings 실측 **0%**, issues-only 42.2%, 빈 findings 57.8%. 초기 가설("warn 55%")과 완전 불일치
2. **git 이력**: 빈 findings 71건이 전부 `domain=location`, `grade=C`, empty rejection_history. 관련 수정 커밋 3건 식별 — `5f203d7` (2026-03-13), `787e60c` (2026-03-30), `c8908e6` (2026-04-12)
3. **배포 전후 비교**: 2026-04-12 이전 빈 findings 59% → 이후 **0%**. 현재 signoff_agent.py + orchestrator.py 이중 방어로 재현 불가

**판정**: 기각(INVALIDATED). 2026-04-14 S1~S5 튜닝 플랜에 배너 부착(PR #304)

**원본 문서**: [../session-reports/2026-04-16-rejection-log-reinvestigation-handoff.md](../session-reports/2026-04-16-rejection-log-reinvestigation-handoff.md)

### 사례 2: content_filter / final summary 실측 경로 — CLOSED-POLICY

**최초 의도**: Azure content_filter 재시도 분포 및 final summary 필드 실측 후 UX 개선 여부 판단

**3단계 적용 결과**:

1. **실측 시도**: `/api/v1/logs?type=rejections` 는 `final_verdict` / `summary` / `escalated` 필드를 **미노출**. content_filter 재시도 건도 147건 중 retry_count>0 은 1건뿐 (2026-04-13, approved)
2. **관측 수단 점검**: Azure Application Insights 통합을 확인 — `backend/.env`·`requirements.txt`·import 전반에 관련 흔적 0건. SDK 미설치, 연결 문자열 미설정
3. **결론**: 배포 전후 비교 자체가 불가. carry 연장으로 해결 불가능

**판정**: CLOSED-POLICY. 별도 트랙(Azure App Insights 도입 검토) 으로 이관. App Insights 연동 시 재개 가능

**선례 기록**: [../session-reports/2026-04-14-carry3-closure-handoff.md](../session-reports/2026-04-14-carry3-closure-handoff.md) (항목 2, 5)

---

## 함정 (Traps)

- **표본 부족 상태의 조기 판정 금지** — 50건 미만이거나 비교 대조군 부재일 때는 보류. 인상 기반 가설의 80% 가 여기서 무효화된다
- **git 이력만으로 인과관계 단정 금지** — 커밋 존재는 "수정 시도" 증거일 뿐, 실효성은 3단계 배포 전후 비교로 확증해야 함
- **관측 수단 자체 부재 시 carry 연장 금지** — carry:3 에 도달해도 관측 수단이 없으면 영원히 closure 불가. 즉시 CLOSED-POLICY 로 이관
- **legacy 데이터 기반 가설 재제출 금지** — 2026-04-12 이전 데이터는 empty findings legacy 를 포함. 동일 구간을 근거로 한 신규 가설은 무효
- **`_FORCED_HIGH_CODES` (SEC\*·RJ\*) 제외** — severity 무시 강제 high 처리 코드. 튜닝 가설 범위에서 제외하지 않으면 회귀 유발
- **Azure 로그 ts 30일 한계** — 2026-03 중순 이전 데이터는 이미 소실. 과거 패턴 조사 시 기간부터 확인
