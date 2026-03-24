# 상권분석 에이전트 (LocationAgent) - Oracle DB 버전

Azure OpenAI + Semantic Kernel + Oracle DB를 활용한 F&B 창업 지원 상권분석 에이전트입니다.
오케스트레이터(부모 에이전트)에 SK Plugin으로 연결되는 자식 에이전트입니다.

> **데이터 단위 변경**: 기존 버전은 상권 단위, 현재 버전은 **행정동 단위** 데이터 사용

---

## 폴더 구조

```
locationAgent_DB/
├── agent/
│   └── location_agent.py           # 상권분석 에이전트 본체 (DB 조회 → 사전계산 → LLM 분석)
├── db/
│   └── repository.py               # DB 조회 레이어 (Oracle 커넥션 풀 기반)
├── plugin/
│   └── location_plugin.py          # 오케스트레이터 연결용 SK Plugin 래퍼
├── test/
│   └── test_location.py            # 단독 테스트
├── .env                            # API 키 설정 (Git 미포함)
├── .env.example                    # 환경변수 예시
└── requirements.txt                # 패키지 의존성
```

---

## 시스템 구조

```
[오케스트레이터]
    ↓ SK Plugin 직접 연결
[LocationAgent]
    ↓ oracledb 조회 (커넥션 풀)
[Oracle DB - SANGKWON_SALES / SANGKWON_STORE 테이블]
    ↓ 사전 계산 (금액 변환, 비율, 피크타임, 주요 고객층)
    ↓ LLM 분석 (gpt-4.1-mini)
행정동별 매출/점포 분석 결과 반환
```

---

## 성능 최적화

기존 대비 **응답 시간 약 30초 → 6~8초**로 개선 (약 4~5배 향상)

### 적용된 최적화 항목

| # | 최적화 항목 | 설명 | 효과 |
|---|------------|------|------|
| 1 | **모델 변경** | gpt-5-nano → gpt-4.1-mini | Thinking 오버헤드 제거, 30초 → 8~10초 |
| 2 | **DB 쿼리 병렬화** | get_sales + get_store_count를 asyncio.gather로 동시 실행 | DB 대기시간 ~50% 감소 |
| 3 | **LLM + 유사상권 동시 실행** | _run_agent()와 get_similar_locations()를 asyncio.gather로 동시 실행 | ~300ms 절약 |
| 4 | **compare() 병렬화** | 모든 지역의 DB 쿼리를 한번에 병렬 실행 | 3개 지역 비교 시 ~80% 단축 |
| 5 | **Kernel 싱글턴** | Kernel + AzureChatCompletion 객체를 한 번만 생성하여 재사용 | 객체 생성 오버헤드 제거 |
| 6 | **DB 커넥션 풀링** | oracledb.create_pool(min=2, max=5)로 커넥션 재사용 | 쿼리당 ~50~100ms 절약 |
| 7 | **LLM 토큰 절약** | 불필요 필드 제거 (30개 → 15개) | 입력 토큰 ~45% 감소 |
| 8 | **수치 사전 계산** | 금액 변환(억/만원), 비율, 피크타임, 주요 고객층을 미리 계산하여 전달 | 토큰 추가 절약 + 계산 오류 방지 |

### 모델 선택 근거

| 모델 | Thinking | 이 작업 적합도 | 비고 |
|------|----------|--------------|------|
| gpt-5-nano (이전) | 자동 실행 (~25초) | 과잉 | 구조화 작업에 불필요한 추론 오버헤드 |
| **gpt-4.1-mini (현재)** | **없음** | **최적** | instruction following 특화, 정형 출력에 최적 |

### 병렬 처리 구조

```
analyze() 실행 흐름:

[DB 커넥션 풀에서 acquire]
    ├── get_sales()         ──┐
    └── get_store_count()   ──┤ asyncio.gather (병렬)
                              ↓
                    [사전 계산 (Python)]
                              ↓
    ├── _run_agent()        ──┐
    └── get_similar_locations() ┤ asyncio.gather (병렬)
                              ↓
                        [결과 반환]
```

### 사전 계산 함수

| 함수 | 역할 | 예시 |
|------|------|------|
| `_format_krw()` | 원 → 억/만원 변환 | `2028280000` → `"20억 2,828만원"` |
| `_calc_pct()` | 비율 계산 (0 나누기 방지) | `(1350850000, 2028280000)` → `67` |
| `_find_peak_time()` | 시간대 6개 비교 → 피크타임 판별 | → `"14~17시"` |
| `_find_top_age()` | 연령대 6개 비교 → 주요 고객층 | → `("20대", 43)` |
| `_precompute_summary()` | 합산 요약 사전 계산 | 위 함수 조합 |
| `_precompute_breakdown()` | 상권별 데이터 사전 계산 | 위 함수 조합 |

---

## Oracle DB 테이블 구조

### SANGKWON_SALES (매출 데이터)

| 컬럼명                           | 설명                         |
| -------------------------------- | ---------------------------- |
| BASE_YR_QTR_CD                   | 기준 년분기 코드 (예: 20244) |
| ADM_CD                           | 행정동 코드                  |
| ADM_NM                           | 행정동 명                    |
| SVC_INDUTY_CD                    | 서비스 업종 코드             |
| SVC_INDUTY_NM                    | 서비스 업종 명               |
| TOT_SALES_AMT                    | 월 추정 매출                 |
| MDWK_SALES_AMT / WKEND_SALES_AMT | 주중/주말 매출               |
| TM00_06 ~ TM21_24_SALES_AMT      | 시간대별 매출                |
| ML_SALES_AMT / FML_SALES_AMT     | 남성/여성 매출               |
| AGE10_AMT ~ AGE60_AMT            | 연령대별 매출                |

### SANGKWON_STORE (점포 데이터)

| 컬럼명                     | 설명                  |
| -------------------------- | --------------------- |
| BASE_YR_QTR_CD             | 기준 년분기 코드      |
| ADM_CD                     | 행정동 코드           |
| ADM_NM                     | 행정동 명             |
| SVC_INDUTY_CD              | 서비스 업종 코드      |
| SVC_INDUTY_NM              | 서비스 업종 명        |
| STOR_CO                    | 점포 수               |
| SIMILR_INDUTY_STOR_CO      | 유사 업종 점포 수     |
| OPBIZ_RT / OPBIZ_STOR_CO   | 개업률 / 개업 점포 수 |
| CLSBIZ_RT / CLSBIZ_STOR_CO | 폐업률 / 폐업 점포 수 |
| FRC_STOR_CO                | 프랜차이즈 점포 수    |

---

## 주요 기능

### 1. 단일 지역 분석 (`analyze`)

지역 + 업종 + 분기 입력 → 상권 분석 결과 반환

**출력 항목:**

- 전체 합산 요약 (월매출, 점포수, 점포당 평균매출, 주중/주말 비율, 피크타임, 주요 고객층)
- 행정동별 분리 분석 (매출, 점포수, 개폐업률 포함)
- 기회 요인 / 리스크 요인
- 유사 상권 추천 TOP 3 (점포당 평균매출, 폐업률 기반 복합 점수)

### 2. 복수 지역 비교 (`compare`)

여러 지역 동시 비교 → 창업 추천 순위 제공

---

## SK Plugin 함수 목록

| 함수명                     | 설명                | 파라미터                                     |
| -------------------------- | ------------------- | -------------------------------------------- |
| `analyze_commercial_area`  | 단일 지역 상권 분석 | location, business_type, quarter             |
| `compare_commercial_areas` | 복수 지역 비교 분석 | locations(쉼표 구분), business_type, quarter |

### 오케스트레이터 등록 방법

```python
from plugin.location_plugin import LocationPlugin
kernel.add_plugin(LocationPlugin(), plugin_name="LocationAnalysis")
```

---

## 유사 상권 추천 알고리즘

복합 점수 기반 TOP 3 추천:

```
점수 = 점포당 평균매출(0.4) + 폐업률 낮음(0.3) + 매출 규모(0.2) + 개업률 적정(0.1)
```

- 개업률 적정 기준: 3~5% 구간 최고점
- 이상치 필터: 점포당 평균매출 상위 5% 제외, 점포수 2개 이하 제외

---

## 지역 매핑 구조 (AREA_MAP)

- **208개 키워드 → 행정동 코드** 매핑
- 권역별 분류: 홍대/마포, 강남, 서초/사당, 여의도/영등포, 이태원/용산, 건대/성수, 신촌/서대문, 잠실/송파, 강동, 노원/도봉/강북, 관악/동작, 강서/양천, DMC/은평, 종로/도심, 성북/강북, 중랑, 동대문구, 왕십리/성동, 구로

---

## 지원 업종

한식, 중식, 일식, 양식, 베이커리/제과점, 패스트푸드, 치킨, 분식, 호프/술집, 카페/커피, 미용실, 네일, 노래방, 편의점

---

## 에러 처리

```
'부산' 은(는) 지원하지 않는 지역입니다. 서울 내 지역만 조회 가능합니다.
'피자' 은(는) 지원하지 않는 업종입니다.
```

---

## 사용 모델

| 환경        | 모델             | 비고                                    |
| ----------- | ---------------- | --------------------------------------- |
| 개발/테스트 | `gpt-4.1-mini`  | instruction following 특화, 빠른 응답    |
| 서비스      | `gpt-4.1-mini`  | 구조화 출력 최적, Thinking 오버헤드 없음 |

> **모델 선택 기준**: 이 에이전트의 작업은 "구조화된 데이터 → 정형 한국어 텍스트 변환"으로, 깊은 추론보다 instruction following과 포맷 준수가 중요합니다. GPT-4.1 계열이 이 특성에 가장 적합합니다.

---

## 데이터 출처

- 매출: 서울시 상권분석서비스 추정매출-행정동 (VwsmAdstrdSelngQq)
- 점포: 서울시 상권분석서비스 점포-행정동 (VwsmAdstrdStorW)
- 기준 분기: 2019년 1분기 ~ 2025년 3분기

---

## 실행 방법

```bash
# 1. 가상환경 생성 및 활성화
py -3.12 -m venv .venv
.venv\Scripts\activate

# 2. 패키지 설치
pip install -r requirements.txt

# 3. .env 설정
copy .env.example .env
# .env 파일에 API 키 및 Oracle 연결 정보 입력

# 4. 테스트 실행
python test/test_location.py
```

---

## 환경변수 (.env)

```
# Azure OpenAI
AZURE_OPENAI_ENDPOINT=...
AZURE_OPENAI_CHAT_DEPLOYMENT_NAME=gpt-4.1-mini
AZURE_OPENAI_API_KEY=...
AZURE_OPENAI_API_VERSION=2024-05-01-preview

# Oracle DB
ORACLE_USER=...
ORACLE_PASSWORD=...
ORACLE_DSN=host:port/service_name
```
