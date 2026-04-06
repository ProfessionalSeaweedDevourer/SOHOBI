# 플랜: Signoff 평가 기준 최신화

## Context

각 에이전트의 실제 출력 형식과 signoff 평가 프롬프트(skprompt.txt) 간에 구조적 gap이 존재하여,
정상적인 에이전트 응답이 signoff에서 오탐 fail(approved=false)을 받을 가능성이 있다.
특히 location agent의 compare 모드와 admin agent의 GovSupport 플러그인 응답이 현재 기준에 맞지 않는다.

---

## 발견된 Gap 및 수정 범위

### P1 — 즉시 수정 (오탐 발생 확실)

#### [Location] S3 — compare 모드의 `창업 추천 순위` 미인식
- **원인**: `_COMPARE_INSTRUCTIONS`는 `✅ 기회 요인` 대신 `✅ 창업 추천 순위`, `⚠️ 리스크 요인` 대신 `⚠️ 유의사항` 섹션을 사용함
- S3는 핵심 항목 → issues 시 approved=false → compare 쿼리 전체가 통과 불가
- **파일**: `signoff_location/evaluate/skprompt.txt`

#### [Admin] A5 — GovSupport 비정형 기한 표현 미인식
- **원인**: `GovSupportPlugin`의 `apply_deadline` 필드에 "상시 접수", "예산 소진 시 마감", "연중 모집" 등이 반환됨
- 현재 A5 기준에 이 표현들이 유효 목록으로 없어 LLM 판단이 불안정
- **파일**: `signoff_admin/evaluate/skprompt.txt`

### P2 — 단기 수정 (간헐적 오탐)

#### [Location] S4 — compare 모드의 헤더/표 구조 미명시
- **원인**: compare 모드에서 업종은 헤더(`📅 데이터 기준: YYYY년 Q분기 / 업종: {business_type}`)에, 지역명은 비교표 열 제목에 위치하는 구조
- S4 기준이 이 구조를 명시적으로 인정하지 않아 LLM 판단이 불안정
- **파일**: `signoff_location/evaluate/skprompt.txt`

#### [Admin] A2 — GovSupport 응답의 서식 번호 부재
- **원인**: `GovSupportPlugin` 반환 포맷에 `[별지 제X호서식]` 같은 정형 서식 번호가 없음
- 지원사업에 따라 `신청방법` 필드가 "-"일 경우 A2 fail 가능
- **파일**: `signoff_admin/evaluate/skprompt.txt`

### P3 — 문서화 (실제 fail 거의 없음)

#### [Finance] F3 — `매출·원가 ±10%` 표현 유효 목록 미포함
- **원인**: 단일 revenue 시나리오에서 loss_prob=0이면 `"이번 시뮬레이션(매출·원가 ±10%) 범위 내에서는..."` 표현 사용
- `[1. 가정 조건]` 섹션에 항상 "월매출: X원" 등이 있으므로 실제로는 F3 통과됨 — 문서 정합성 수정
- **파일**: `signoff_finance/evaluate/skprompt.txt`

### 변경 불필요
- `signoff_legal/evaluate/skprompt.txt` — G1~G4 모두 시스템 프롬프트 강제 조건과 정렬됨
- `signoff_agent.py` REQUIRED_CODES — 코드 집합 변경 없음 (내용만 변경)

---

## 구체적 수정 내용

### 1. signoff_location/evaluate/skprompt.txt

**S3 수정** (현재 52~55번 라인):

```
기존:
- S3 기회·리스크 언급 존재 여부: 응답에 기회 요인과 리스크 요인이 각각 하나 이상 언급되어 있으면 통과.
  기회 또는 리스크 중 어느 한쪽이 전혀 없는 경우에만 issues로 분류한다.
  유효한 기회 표현 예시: '성장 가능성', '유동 인구', '수요 증가', '매출 상위권', '낮은 폐업률' 등.
  유효한 리스크 표현 예시: '높은 폐업률', '경쟁 포화', '임대료 부담', '수요 감소', '계절성' 등.

추가:
  중요: 복수 지역 비교(compare) 응답에서 '✅ 창업 추천 순위' 섹션은 기회 요인에 해당하고,
  '⚠️ 유의사항' 섹션은 리스크 요인에 해당한다. 이 두 섹션이 모두 존재하면 S3 통과로 분류한다.
  섹션 제목이 '기회 요인', '리스크 요인'이라는 정확한 레이블을 사용하지 않더라도
  기회·리스크에 해당하는 내용이 존재하면 통과로 분류한다.
  유효한 기회 표현 추가: '창업 추천', '1순위', '점포당 평균매출 높음', '개업률 적정', '추천 이유'.
  유효한 리스크 표현 추가: '유의사항', '주의', '리스크'.
```

**S4 수정** (현재 56~57번 라인):

```
기존:
- S4 지역·업종 명시 여부: 응답에 분석 대상 지역명과 업종명이 모두 명시되어 있으면 통과.
  둘 중 하나라도 없는 경우에만 issues로 분류한다.

추가:
  중요: 지역명과 업종명이 응답의 어느 위치에 있어도 인정한다.
  복수 지역 비교(compare) 응답에서 업종은 헤더(예: '업종: 카페')에,
  지역명은 비교표의 열 제목에 포함될 수 있으며 이 구조도 S4 통과로 분류한다.
```

### 2. signoff_admin/evaluate/skprompt.txt

**A2 수정** (현재 54번 라인):

```
기존:
- A2 서식 번호 언급 존재 여부: 응답에 관련 서식 번호 또는 양식명이 하나 이상 명시되어 있으면 통과. 해당 서식의 사실적 정확성은 이 항목의 평가 대상이 아니다.

추가:
  중요: 응답이 정부지원사업·보조금 정보를 다루는 경우, 신청 방법이나 지원 내용에
  '신청서', '신청양식', '온라인 신청', '신청서류' 등의 표현이 하나라도 있으면 A2 통과로 분류한다.
  정부지원사업 응답에서 별지 서식 번호가 없는 것은 정상이며 이를 이유로 A2 issues로 분류하지 않는다.
  신청 관련 표현이 전혀 없는 경우에만 A2 issues로 분류한다.
```

**A5 수정** (현재 57번 라인):

```
기존:
- A5 기한 정보 언급 존재 여부: 응답에 처리 기한, 신고 기한, 유효 기간 등 기한 관련 정보가 하나라도 언급되어 있으면 통과. 기한 정보가 전혀 없는 경우에만 issues로 분류한다.

추가:
  유효한 기한 표현:
  - 행정 절차형: '3~7영업일 이내', '신고 후 X일', '유효기간 X년'
  - 지원사업형: '상시 접수', '예산 소진 시 마감', '연중 모집', '선착순', '신청기한: ○○까지'
  정부지원사업 응답에서 '신청기한' 항목이 존재하면(값이 비어있지 않으면) A5 통과로 분류한다.
  '상시', '연중', '선착순'은 기한 정보로 인정한다.
```

### 3. signoff_finance/evaluate/skprompt.txt

**F3 수정** (현재 68~71번 라인 유효 표현 목록):

```
기존:
  - 입력값 기반: '월매출', '원가', '급여', '임대료' 등 시뮬레이션 입력 수치 언급
  - 실제 데이터 기반: '실제 매장', 'n개 데이터', 'DB 데이터', '실제 매출 데이터', '매장 데이터 기반' 등

추가:
  - 시뮬레이션 범위 기반: '매출·원가 ±10%', '±10%', '시뮬레이션 범위' 등 변동 범위 표현
```

---

## 수정 대상 파일 경로

| 파일 | 수정 항목 | 우선순위 |
|------|-----------|----------|
| `integrated_PARK/prompts/signoff_location/evaluate/skprompt.txt` | S3, S4 | P1, P2 |
| `integrated_PARK/prompts/signoff_admin/evaluate/skprompt.txt` | A2, A5 | P1, P2 |
| `integrated_PARK/prompts/signoff_finance/evaluate/skprompt.txt` | F3 | P3 |

---

## 검증 방법

수정 후 다음 시나리오로 실제 API 호출 테스트:

```bash
# Location — compare 모드 (S3, S4 검증)
curl -s -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"question": "홍대와 강남 카페 상권 비교해줘"}'
# → approved: true, grade: A 또는 B 확인

# Admin — GovSupport 쿼리 (A2, A5 검증)
curl -s -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"question": "소상공인 창업 지원 보조금 어떤 게 있어요?"}'
# → approved: true 확인, A2/A5 issues 없음 확인

# Finance — 단일 시나리오 손실 0% 케이스 (F3 검증)
curl -s -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"question": "월매출 2000만, 원가 500만, 임대료 200만으로 수익 분석해줘"}'
# → F3 passed 확인

# 스트리밍으로 각 에이전트 signoff 결과 확인
curl -s -X POST http://localhost:8000/api/v1/stream \
  -H "Content-Type: application/json" \
  -d '{"question": "홍대 강남 카페 비교"}' | grep signoff_result
```

SSE 스트림의 `signoff_result` 이벤트에서 `passed`, `issues`, `warnings` 배열을 확인하여
S3, S4, A2, A5 코드가 모두 `passed`에 있는지 검증한다.
