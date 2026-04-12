# PR #96 테스트 계획서

작성일: 2026-04-03
대상 PR: #96 (DB 관련 수정 및 내부 지역/업종 추출 추가)
작성자: PARK

---

## 1. 개요

PR #96 머지 후 아래 두 계층을 모두 검증한다.

| 계층 | 방법 | 파일 |
|------|------|------|
| DB/플러그인 유닛 | pytest (Azure PostgreSQL 직접 연결) | `tests/test_finance_pr96.py` |
| E2E 엔드포인트 | curl (Azure Container Apps) | 본 문서 §3 |

---

## 2. pytest 단위 테스트

### 실행 방법

```bash
cd integrated_PARK
source .env  # PG_HOST, PG_PORT, PG_DB, PG_USER, PG_PASSWORD 로드
.venv/bin/python3 -m pytest tests/test_finance_pr96.py -v
```

### 테스트 구성 (3개 클래스, 22개 케이스)

#### `TestGetSalesListRegion` — `finance_db.get_sales()` list 인터페이스 (10개)
| 케이스 | 입력 | 기대 결과 |
|--------|------|-----------|
| `test_hongdae_cafe_returns_data` | `["11440660"]`, `"CS100010"` | 실제 DB 데이터, fallback 아님 |
| `test_gangnam_hanshik_multi_codes` | `["11680640","11680650","11680521","11680531"]`, `"CS100001"` | 복수코드 IN 쿼리 |
| `test_mawon_two_codes` | `["11440690","11440700"]`, `"CS100007"` | 리스트 반환 |
| `test_yeouido_hof` | `["11560540"]`, `"CS100009"` | 숫자형 리스트 |
| `test_itaewon_yangsik` | `["11170650","11170660"]`, `"CS100004"` | 리스트 반환 |
| `test_none_region_returns_fallback` | `None`, `"CS100010"` | `[17_000_000]` |
| `test_none_industry_returns_fallback` | `["11440660"]`, `None` | `[17_000_000]` |
| `test_empty_list_returns_fallback` | `[]`, `"CS100010"` | `[17_000_000]` |
| `test_both_none_returns_fallback` | `None`, `None` | `[17_000_000]` |
| `test_values_in_reasonable_range` | `["11440660"]`, `"CS100010"` | 1만~100억 범위 |

#### `TestLoadInitialListRegion` — `load_initial()` list region (5개)
| 케이스 | 입력 | 기대 결과 |
|--------|------|-----------|
| `test_hongdae_cafe_returns_dict` | `region=["11440660"]`, `industry="CS100010"` | dict + revenue 포함 |
| `test_hongdae_cafe_not_fallback` | 동일 | fallback 17_000_000 아님 |
| `test_gangnam_hanshik_multi` | 강남 4개 코드, 한식 | 리스트 반환 |
| `test_none_region_returns_avg` | `region=None`, 카페 | 리스트 반환 |
| `test_other_fields_none` | 홍대, 카페 | cost/salary/rent 등 None |

#### `TestFullPipelineListRegion` — load → simulate 전체 파이프라인 (7개)
| 케이스 | 지역 | 업종 | 검증 포인트 |
|--------|------|------|------------|
| `test_hongdae_cafe_pipeline` | 홍대 | 카페 | 결과 구조 + chart 40 bins |
| `test_gangnam_hanshik_pipeline` | 강남 4개 | 한식 | 복수코드 파이프라인 |
| `test_yeouido_hof_pipeline` | 여의도 | 호프 | 단일코드 |
| `test_mawon_bunjang_pipeline` | 망원 2개 | 분식 | loss_probability float |
| `test_itaewon_chicken_pipeline` | 이태원 2개 | 치킨 | 파이프라인 통과 |
| `test_jamsil_cafe_pipeline` | 잠실 4개 | 카페 | rent 비율 0.15 적용 |
| `test_result_structure_complete` | 홍대 | 카페 | 10개 필드 전체 존재 |

---

## 3. E2E curl 테스트 (Azure 배포 환경)

### 실행 전 준비

```bash
source integrated_PARK/.env
# BACKEND_HOST 확인
echo $BACKEND_HOST
```

### 테스트 케이스 (10개 질의)

아래 명령을 순서대로 실행하고 §4 리포트에 결과를 기록한다.

---

#### TC-01. 지역 + 업종 (홍대, 카페)

```bash
curl -s -X POST "$BACKEND_HOST/api/v1/query" \
  -H "Content-Type: application/json" \
  -d '{"question": "홍대에서 카페 창업하면 예상 매출이 얼마야?"}' \
  | python3 -m json.tool
```

**검증 포인트**
- `draft`에 "홍대" 또는 관련 지역 언급
- `updated_params.revenue` 값이 `[17000000]` 아님 (실제 홍대 카페 DB 데이터)
- `chart.bins` 40개

---

#### TC-02. 지역 + 업종 (강남, 한식)

```bash
curl -s -X POST "$BACKEND_HOST/api/v1/query" \
  -H "Content-Type: application/json" \
  -d '{"question": "강남에서 한식 창업 비용 시뮬레이션 해줘"}' \
  | python3 -m json.tool
```

**검증 포인트**
- `updated_params.revenue` 강남 한식 지역 데이터 반영
- `average_net_profit` 계산 정상

---

#### TC-03. 지역 + 업종 + 금액 (역삼, 카페, 임대료 지정)

```bash
curl -s -X POST "$BACKEND_HOST/api/v1/query" \
  -H "Content-Type: application/json" \
  -d '{"question": "역삼에서 카페 창업, 월임대료 250만원이면 수익이 얼마야?"}' \
  | python3 -m json.tool
```

**검증 포인트**
- `updated_params.rent` ≈ 2_500_000
- 지역 기반 revenue + 사용자 지정 rent 병합

---

#### TC-04. 지역 + 업종 (여의도, 분식)

```bash
curl -s -X POST "$BACKEND_HOST/api/v1/query" \
  -H "Content-Type: application/json" \
  -d '{"question": "여의도에서 분식집 차리면 한 달 얼마 벌어?"}' \
  | python3 -m json.tool
```

---

#### TC-05. 지역 + 업종 (이태원, 치킨)

```bash
curl -s -X POST "$BACKEND_HOST/api/v1/query" \
  -H "Content-Type: application/json" \
  -d '{"question": "이태원에서 치킨집 창업 시뮬레이션"}' \
  | python3 -m json.tool
```

---

#### TC-06. 업종만 있음 (카페, 지역 없음)

```bash
curl -s -X POST "$BACKEND_HOST/api/v1/query" \
  -H "Content-Type: application/json" \
  -d '{"question": "카페 창업하면 수익이 얼마 나와?"}' \
  | python3 -m json.tool
```

**검증 포인트**
- `adm_codes` 추출 안 됨 → DB 전체 평균 또는 fallback 사용
- `draft` 정상 생성

---

#### TC-07. 지역만 있음 (홍대, 업종 없음)

```bash
curl -s -X POST "$BACKEND_HOST/api/v1/query" \
  -H "Content-Type: application/json" \
  -d '{"question": "홍대에서 창업하면 평균 매출이 얼마야?"}' \
  | python3 -m json.tool
```

**검증 포인트**
- `business_type` 추출 안 됨 → fallback 또는 전체 평균 사용
- 에러 없이 응답 생성

---

#### TC-08. 둘 다 없음 (지역·업종 미언급)

```bash
curl -s -X POST "$BACKEND_HOST/api/v1/query" \
  -H "Content-Type: application/json" \
  -d '{"question": "창업하면 보통 얼마나 벌어?"}' \
  | python3 -m json.tool
```

**검증 포인트**
- fallback 사용
- 에러 없이 기본 응답 생성

---

#### TC-09. 퍼지 매칭 (비표준 지역명)

```bash
curl -s -X POST "$BACKEND_HOST/api/v1/query" \
  -H "Content-Type: application/json" \
  -d '{"question": "홍익대 근처에서 카페 창업하면?"}' \
  | python3 -m json.tool
```

**검증 포인트**
- "홍익대" → fuzzy match → "홍대" 정규화 가능 여부
- 또는 정규화 실패 시 fallback graceful 처리

---

#### TC-10. 초기투자 포함 (잠실, 한식, 투자금)

```bash
curl -s -X POST "$BACKEND_HOST/api/v1/query" \
  -H "Content-Type: application/json" \
  -d '{"question": "잠실에서 한식 창업, 초기 투자비용 5000만원이면 몇 달 만에 회수해?"}' \
  | python3 -m json.tool
```

**검증 포인트**
- `updated_params.initial_investment` ≈ 50_000_000
- `[투자 회수 전망]` 섹션 draft에 포함

---

## 4. 테스트 결과 리포트 (실행 후 기록)

> 실행일: ___________
> 실행자: ___________
> 환경: Azure Container Apps (main 브랜치)

### 4-1. pytest 결과

```
테스트 파일: tests/test_finance_pr96.py
총 케이스: 22
통과:      ___
실패:      ___
에러:      ___
소요 시간: ___s
```

실패 케이스 상세:
```
(없으면 "없음"으로 기록)
```

---

### 4-2. E2E curl 결과

| TC | 질의 요약 | revenue 출처 | draft 생성 | 투자회수 | 통과 |
|----|-----------|-------------|-----------|---------|------|
| TC-01 | 홍대 카페 | DB / fallback | ✓ / ✗ | — | □ |
| TC-02 | 강남 한식 | DB / fallback | ✓ / ✗ | — | □ |
| TC-03 | 역삼 카페 + 임대료 | DB / fallback | ✓ / ✗ | — | □ |
| TC-04 | 여의도 분식 | DB / fallback | ✓ / ✗ | — | □ |
| TC-05 | 이태원 치킨 | DB / fallback | ✓ / ✗ | — | □ |
| TC-06 | 카페만 | fallback | ✓ / ✗ | — | □ |
| TC-07 | 홍대만 | fallback | ✓ / ✗ | — | □ |
| TC-08 | 둘 다 없음 | fallback | ✓ / ✗ | — | □ |
| TC-09 | 홍익대 퍼지 | DB / fallback | ✓ / ✗ | — | □ |
| TC-10 | 잠실 한식 + 투자금 | DB / fallback | ✓ / ✗ | ✓ / ✗ | □ |

**revenue 출처 판단 기준**: `updated_params.revenue[0] != 17000000` 이면 실제 DB 데이터

---

### 4-3. 로그 확인

```bash
curl -s "$BACKEND_HOST/api/v1/logs?type=queries&limit=20" | python3 -m json.tool
```

```
(로그 출력 붙여넣기)
```

---

### 4-4. 최종 판정

- [ ] pytest 22/22 통과
- [ ] E2E TC-01~05 (지역+업종): revenue가 실제 DB 데이터
- [ ] E2E TC-06~08 (fallback): 에러 없이 응답 생성
- [ ] E2E TC-09 (퍼지): 정상 처리 확인
- [ ] E2E TC-10 (투자회수): draft에 투자 회수 섹션 포함

**결론**: 통과 / 조건부 통과 / 실패
**비고**:
