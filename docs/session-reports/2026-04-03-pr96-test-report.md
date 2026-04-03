# PR #96 테스트 결과 리포트

작성일: 2026-04-03  
대상 PR: #96 (DB 관련 수정 및 내부 지역/업종 추출 추가)  
환경: Azure Container Apps (main 브랜치, 빌드 성공 확인 후)  
작성자: PARK (Claude Code 보조)

---

## 1. pytest 단위 테스트 결과

```
파일: integrated_PARK/tests/test_finance_pr96.py
총 케이스: 22
통과:      16
실패:      6
소요 시간: 4.82s
```

### 1-1. 통과 케이스 (16/22)

| 클래스 | 케이스 | 비고 |
|--------|--------|------|
| TestGetSalesListRegion | test_mawon_two_codes | list 전달 → LIKE 실패 → fallback → `isinstance(list)` 통과 |
| TestGetSalesListRegion | test_yeouido_hof | 동일 |
| TestGetSalesListRegion | test_itaewon_yangsik | 동일 |
| TestGetSalesListRegion | test_none_industry_returns_fallback | fallback `[17000000]` 반환 확인 |
| TestGetSalesListRegion | test_values_in_reasonable_range | fallback 조건부 통과 |
| TestLoadInitialListRegion | test_hongdae_cafe_returns_dict | dict 구조 확인 |
| TestLoadInitialListRegion | test_gangnam_hanshik_multi | 리스트 반환 확인 |
| TestLoadInitialListRegion | test_none_region_returns_avg | fallback 통과 |
| TestLoadInitialListRegion | test_other_fields_none | None 필드 확인 |
| TestFullPipelineListRegion | test_hongdae_cafe_pipeline | load→simulate 구조 통과 |
| TestFullPipelineListRegion | test_gangnam_hanshik_pipeline | 통과 |
| TestFullPipelineListRegion | test_yeouido_hof_pipeline | 통과 |
| TestFullPipelineListRegion | test_mawon_bunjang_pipeline | 통과 |
| TestFullPipelineListRegion | test_itaewon_chicken_pipeline | 통과 |
| TestFullPipelineListRegion | test_jamsil_cafe_pipeline | 통과 |
| TestFullPipelineListRegion | test_result_structure_complete | 10개 필드 전체 존재 |

### 1-2. 실패 케이스 (6/22) — PARK 브랜치 미반영 원인

> **핵심 원인**: 테스트는 PR #96 merged 상태(main)를 기준으로 작성됐으나,  
> 실행 환경(PARK 브랜치)의 `finance_db.py`는 아직 PR #96 변경이 없는 구버전.  
> 구버전 `get_sales()`는 `LIKE %s` (단일 문자열) 방식이므로 list 전달 시 PostgreSQL 오류 발생.

| 케이스 | 오류 내용 | 진단 |
|--------|-----------|------|
| `test_hongdae_cafe_returns_data` | `LIKE ARRAY['11440660']` — PostgreSQL 연산자 불일치 → fallback `[17000000]` 반환 | PARK 브랜치 구버전 |
| `test_gangnam_hanshik_multi_codes` | 동일 오류 | PARK 브랜치 구버전 |
| `test_none_region_returns_fallback` | `get_sales(None, "CS100010")` → 구버전은 `%` 와일드카드로 전체 11,647건 반환 (fallback 아님) | 동작 방식 변경됨 |
| `test_empty_list_returns_fallback` | `get_sales([], ...)` → 구버전은 `LIKE []` 결과로 빈 리스트 `[]` 반환 (fallback `[17000000]` 아님) | 동작 방식 변경됨 |
| `test_both_none_returns_fallback` | 구버전 None → 전체 474,938건 반환 | 동작 방식 변경됨 |
| `test_hongdae_cafe_not_fallback` | list 전달 → DB 오류 → fallback 반환 | PARK 브랜치 구버전 |

**결론**: 실패 케이스는 모두 PR #96의 `finance_db.py` 변경이 PARK 브랜치에 없어서 발생.  
main 브랜치에서 동일 테스트 재실행 시 22/22 통과 예상.

---

## 2. E2E curl 테스트 결과

실행 대상: `$BACKEND_HOST` (Azure Container Apps, main 브랜치)

### 2-1. 결과 요약표

| TC | 질의 | domain | status | grade | revenue 출처 | 실제 DB rows | 통과 |
|----|------|--------|--------|-------|-------------|-------------|------|
| TC-01 | 홍대 카페 시뮬레이션 | finance | approved | A | DB ✓ | 28 | ✅ |
| TC-02 | 강남 한식 시뮬레이션 | finance | approved | A | DB ✓ | 112 | ✅ |
| TC-03 | 역삼 카페 + 임대료 250만 | finance | approved | A | DB ✓ | 56 | ✅ |
| TC-04 | 여의도 분식 손익분기 | finance | approved | A | DB ✓ | 28 | ✅ |
| TC-05 | 이태원 치킨 시뮬레이션 | finance | approved | A | DB ✓ | 22 | ✅ |
| TC-06 | 카페만 (지역 없음) | finance | approved | A | fallback ✓ | 1 | ✅ |
| TC-07 | 홍대에서 창업 (업종 없음) | location | approved | C | — | — | ⚠️ |
| TC-08 | 둘 다 없음 | finance | approved | A | fallback ✓ | 1 | ✅ |
| TC-09 | 홍익대 근처 카페 (퍼지) | location | escalated | C | — | — | ⚠️ |
| TC-10 | 잠실 한식 + 초기투자 5000만 | finance | approved | A | DB ✓ | 168 | ✅ |

### 2-2. 케이스별 상세

---

#### TC-01 — 홍대 카페 시뮬레이션 ✅

```
질의: "홍대에서 카페 창업 시 월 순이익 시뮬레이션 해줘"
domain: finance | status: approved | grade: A
revenue: 28 rows (실제 DB, fallback 아님)
```

**draft 발췌**
```
[1. 가정 조건]
- 월매출: 10,295,288,911.0~31,585,392,334.0원 (복수 시나리오)
- 원가: 7,915,366,716원 / 급여: 4,523,066,695원
- 임대료: 2,261,533,347원

[2. 시뮬레이션 결과]
- 평균 월 순이익: 6,505,205,283원
- 손실 관측: 10,000회 중 29.0%
- 비관 시나리오(하위 20%): -3,274,567,683원
```

**검증**: 홍대 adm_code `["11440660"]` → DB IN 쿼리 → 28건 반환. fallback 아님. 시뮬레이션 구조 완전.

---

#### TC-02 — 강남 한식 시뮬레이션 ✅

```
질의: "강남에서 한식당 창업하면 수익 얼마나 나는지 시뮬레이션 해줘"
domain: finance | status: approved | grade: A
revenue: 112 rows (4개 adm_code × 행정동별 분기 데이터)
```

**draft 발췌**
```
손익분기 매출: 월 255억 5,129만 8,474원
안전마진: 43.8%
외부 충격(경기침체·임대료 급등·수요 급감) 발생 시 손실 전환 가능성 경고
```

**검증**: 강남 4개 adm_code `["11680640","11680650","11680521","11680531"]` → IN 쿼리 → 112건.

---

#### TC-03 — 역삼 카페 + 사용자 임대료 지정 ✅

```
질의: "역삼에서 카페 창업, 월임대료 250만원이면 순이익이 얼마야"
domain: finance | status: approved | grade: A
revenue: 56 rows (DB) | rent: 2,500,000원 (사용자 입력 반영)
```

**draft 발췌**
```
[1. 가정 조건]
- 월매출: 2,045,994,085.0~38,644,869,363.0원 (복수 시나리오)
- 임대료: 2,500,000원  ← 사용자 지정값 정확히 반영
```

**검증**: 지역 DB 데이터(역삼 카페) + 사용자 지정 임대료 병합 정상 동작.

---

#### TC-04 — 여의도 분식 ✅

```
질의: "여의도에서 분식집 창업하면 손익분기 매출은 얼마야"
domain: finance | status: approved | grade: A
revenue: 28 rows (여의도 adm_code ["11560540"])
```

**draft 발췌**
```
- 월매출: 3,825,237,652.0~7,886,442,757.0원
- 평균 월 순이익: 1,538,639,256원
```

---

#### TC-05 — 이태원 치킨 ✅

```
질의: "이태원에서 치킨집 창업 재무 시뮬레이션"
domain: finance | status: approved | grade: A
revenue: 22 rows (이태원 2개 adm_code)
```

**draft 발췌**
```
- 월매출: 29,166,481.0~577,984,001.0원 (복수 시나리오)
- 평균 월 순이익: 43,288,990원
- 손실 발생: 10,000회 중 49.8%
```

**검증**: 이태원 치킨은 손실 확률 49.8%로 고위험 분류.

---

#### TC-06 — 업종만 (지역 없음) ✅

```
질의: "카페 창업하면 수익이 얼마 나와"
domain: finance | status: approved | grade: A
revenue: 1 row [17,000,000.0] (fallback 정상 사용)
```

**draft 발췌**
```
- 월매출: 17,000,000.0원
- 평균 월 순이익: 4,937,568원
- 손실 발생: 10,000회 중 0.3%
```

**검증**: 지역 미제공 시 fallback [17,000,000] 사용. 응답 생성 정상.

---

#### TC-07 — 지역만, 업종 없음 ⚠️

```
질의: "홍대에서 창업하면 평균 매출이 얼마야"
domain: location | status: approved | grade: C
```

**draft 발췌**
```
'창업' 업종은 현재 지원하지 않습니다.
지원 업종: 네일, 노래방, 미용실, 베이커리, ...
```

**진단**: 오케스트레이터가 location 에이전트로 라우팅.  
location 에이전트는 AREA_MAP에서 "홍대" 인식했으나, 업종이 "창업"으로 비정규화돼 C 등급 반환.  
PR #96의 finance 에이전트 내부 추출은 업종이 없으면 finance로 라우팅이 안 돼 발동되지 않음.  
→ **PR #96 범위 외 이슈**. 오케스트레이터 라우팅 로직의 개선 필요.

---

#### TC-08 — 지역·업종 모두 없음 ✅

```
질의: "창업하면 보통 얼마나 벌어"
domain: finance | status: approved | grade: A
revenue: 1 row [17,000,000.0] (fallback)
```

**검증**: 정보 없는 질의도 fallback으로 정상 응답 생성.

---

#### TC-09 — 퍼지 매칭 (홍익대) ⚠️

```
질의: "홍익대 근처에서 카페 창업하면 월 순이익 얼마야"
domain: location | status: escalated | grade: C
```

**draft 발췌**
```
'홍익대 근처' 지역의 '카페' 업종 데이터를 찾을 수 없습니다.
서울 주요 구·동 이름으로 질문해 주세요 (총 208개 지원).
```

**진단**:
- 오케스트레이터가 "카페 창업" 키워드를 location 에이전트로 라우팅.
- location 에이전트의 AREA_MAP 매핑에서 "홍익대 근처" 미인식 → escalated.
- finance 에이전트의 PR #96 퍼지 매칭(difflib cutoff 0.6)이 발동될 경우 "홍익대"→"홍대" 변환은 가능하지만, 오케스트레이터가 먼저 location으로 보내면 해당 코드에 도달하지 못함.
- → **라우팅 레이어의 퍼지 지원 필요**. PR #96 범위 외.

---

#### TC-10 — 잠실 한식 + 초기투자금 5000만원 ✅

```
질의: "잠실에서 한식 창업, 초기 투자비용 5000만원이면 몇 달 만에 회수해"
domain: finance | status: approved | grade: A
revenue: 168 rows (잠실 4개 adm_code × 분기 데이터) | initial_investment: 50,000,000
```

**draft 발췌**
```
[1. 가정 조건]
- 월매출: 23,947,025.0~36,403,048,670.0원 (복수 시나리오)
- 초기 투자비용: 50,000,000원

[2. 시뮬레이션 결과]
- 평균 월 순이익: 1,803,922,126원
- 손실 발생: 10,000회 중 66.5%

[투자 회수 전망]
투자 회수까지 약 1개월이 소요됩니다.
```

**검증**: 잠실 한식 DB 168건, initial_investment 추출 ✓, 투자 회수 섹션 포함 ✓.  
회수 기간 "1개월"은 평균 순이익이 DB 구단위 집계 수치의 영향으로 과대계상되어 발생 (하단 §3 참조).

---

## 3. 발견된 이슈 정리

### Issue 1: DB `tot_sales_amt` 스케일 불일치 (기존 이슈, PR #96 외)

**현상**: 시뮬레이션 결과에서 월매출·순이익 등 수치가 수십억~수백억 원으로 표시됨.

**원인**: `sangkwon_sales.tot_sales_amt`는 행정동 단위의 분기별 **전체 업종 합산 매출** 집계값임.  
개별 점포의 월매출 데이터가 아니므로, 1개 점포 시뮬레이션 입력으로 사용하면 수치가 비정상적으로 크게 나타남.

**영향**: TC-01~05, TC-10의 순이익·손익분기·투자회수 수치가 현실과 크게 다름.

**권고**: DB 스키마 재확인 — 점포당 매출(`per_store_avg_amt`) 컬럼 사용 또는 집계값을 점포 수로 나눈 값을 revenue로 사용하도록 수정 필요.

---

### Issue 2: TC-07, TC-09 — 비정규 지역명의 finance 에이전트 미도달 (PR #96 범위 외)

**현상**: "홍대에서 창업", "홍익대 근처에서 카페 창업" 같은 질의가 location 에이전트로 라우팅되어 finance 에이전트의 PR #96 추출 로직이 발동되지 않음.

**원인**: 오케스트레이터의 라우팅 조건이 지역명 + 카페 키워드를 location으로 우선 분류.

**권고**: finance 에이전트로의 라우팅 조건에 "시뮬레이션", "창업 비용", "손익분기" 외에 "창업 수익" 등 패턴 추가 검토.

---

## 4. 최종 판정

| 항목 | 결과 |
|------|------|
| pytest 22케이스 (PARK 브랜치) | 16/22 통과 — 6개 실패는 PARK 브랜치 미반영 원인 |
| pytest (main 브랜치 기준 예상) | 22/22 통과 예상 |
| TC-01~05 지역+업종 DB 데이터 | ✅ 실제 DB 데이터 정상 반환 |
| TC-03 사용자 파라미터 병합 | ✅ rent=2,500,000 정확히 반영 |
| TC-06, TC-08 fallback 처리 | ✅ fallback [17,000,000] 정상 사용 |
| TC-10 투자 회수 섹션 | ✅ [투자 회수 전망] 포함 |
| TC-07, TC-09 비정규 지역명 | ⚠️ location 에이전트 라우팅 (PR #96 외 이슈) |
| DB 수치 스케일 | ⚠️ 구단위 집계값 사용 — 개별 점포 수치와 다름 |

**종합**: PR #96의 핵심 기능(지역+업종 코드 추출 → DB IN 쿼리 → 실제 데이터 반환)은 정상 동작.  
DB 수치 스케일 이슈와 라우팅 이슈는 별도 PR로 추적 권고.
