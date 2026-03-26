# 상권분석 에이전트 (LocationAgent) - Oracle DB 버전

Azure OpenAI + Semantic Kernel + Oracle DB를 활용한 F&B 창업 지원 상권분석 에이전트입니다.
오케스트레이터(부모 에이전트)에 SK Plugin으로 연결되거나, **FastAPI 서버를 통해 지도 프론트엔드와 직접 연동**됩니다.

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
├── api_server.py                    # ★ FastAPI REST 서버 (프론트엔드 연동용)
├── .env                            # API 키 설정 (Git 미포함)
├── .env.example                    # 환경변수 예시
└── requirements.txt                # 패키지 의존성
```

---

## 시스템 구조

### SK Plugin 연결 (오케스트레이터 경유)

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

### FastAPI 서버 연결 (지도 프론트엔드 직접 연동)

```
[React 지도 프론트 (ChatPanel)]
    ↓ POST /agent/chat (Vite 프록시)
    ↓ admCd 직접 전달 또는 자연어 질문
[api_server.py — FastAPI :8000]
    ├── admCd가 있으면 → AREA_MAP 임시 등록 → 직접 DB 조회
    └── admCd가 없으면 → 자연어 → 파라미터 추출 (Azure OpenAI)
    ↓ analyze() 또는 compare() 자동 분기
[LocationAgent]
    ↓ Oracle DB + LLM 분석
    ↓
[JSON 응답 → ChatPanel 렌더링]
```

---

## 지도 프론트엔드 연동

### 연동 구조

```
┌──────────────────────────────────────────────────────────────────┐
│  React + OpenLayers (TERRY/p02_frontEnd_React)                    │
│                                                                    │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────────────┐   │
│  │ CategoryPanel │  │   MapView    │  │  ChatPanel (400px)    │   │
│  │ (좌측 사이드) │  │ (OpenLayers)  │  │  우측 슬라이드 패널   │   │
│  │ - 카테고리    │  │              │  │  - 채팅 입력/응답     │   │
│  │ - 구/동 검색  │  │              │  │  - 지도 네비게이션    │   │
│  │ - ON/OFF 토글 │  │              │  │  - 컨텍스트 자동 주입 │   │
│  └──────────────┘  │              │  │  - 컨텍스트 해제 가능 │   │
│                     │  행정동 클릭  │  └───────────────────────┘   │
│                     │      ↓       │              ↑               │
│                     │  ┌────────┐  │     admCd 직접 전달          │
│                     │  │DongPanel│──┼── 🤖 AI 버튼 ──────────────│
│                     │  │(점포/  │  │                              │
│                     │  │ 매출/  │  │                              │
│                     │  │ 실거래)│  │                              │
│                     │  └────────┘  │                              │
│                     └──────────────┘                              │
│                            │                                      │
│         Vite Proxy (/agent → localhost:8000)                      │
└────────────────────────────┼──────────────────────────────────────┘
                             │
                             ▼
┌──────────────────────────────────────────────────────────────────┐
│  FastAPI (api_server.py :8000)                                    │
│  POST /chat — 자연어 분석 또는 admCd 직접 조회                    │
│  GET  /locations — 지원 지역 목록 (208개)                         │
│  GET  /industries — 지원 업종 목록 (14개)                         │
│  GET  /health — 서버 상태 확인                                    │
└──────────────────────────────────────────────────────────────────┘
```

### 양방향 상호작용

| 방향 | 트리거 | 동작 |
|------|--------|------|
| **지도 → DongPanel** | 행정동 폴리곤 클릭 | 점포수/매출/실거래가 패널 표시 |
| **DongPanel → 채팅** | 🤖 AI 버튼 클릭 | `{guName, dongName, admCd}` 컨텍스트 전달 → ChatPanel 오픈 |
| **채팅 → 에이전트 (admCd)** | 컨텍스트 상태에서 업종만 입력 | admCd 직접 DB 조회 → AREA_MAP 우회 |
| **채팅 → 에이전트 (텍스트)** | `"홍대 카페 상권 분석해줘"` | 자연어 파라미터 추출 → AREA_MAP 매핑 |
| **채팅 → 지도** | `"강남역 보여줘"`, `"홍대 이동"` | Kakao 키워드 검색 → 좌표 → `map.getView().animate()` |
| **컨텍스트 해제** | 📍 옆 ✕ 버튼 클릭 | admCd 해제 → 자유 텍스트 입력 모드 |

### 지역 전환 로직

ChatPanel은 사용자 입력에 지역명이 포함되었는지 자동 판별합니다:

```
사용자 입력: "카페"
  → 컨텍스트 있음 (종로구 사직동, admCd: 1111062)
  → admCd로 직접 DB 조회 (사직동 카페 분석)

사용자 입력: "홍대 카페 분석"
  → 지역명 "홍대" 감지 → 현재 컨텍스트와 다른 지역
  → admCd 무시 → 텍스트 기반 파라미터 추출 (홍대 카페 분석)

사용자 입력: "강남 vs 잠실 한식 비교"
  → 복수 지역 감지 → admCd 무시 → compare() 호출
```

- **AREA_KEYWORDS**: 50개+ 서울 주요 지역 키워드 (강남, 홍대, 잠실, 이태원 등)
- 현재 컨텍스트와 동일 지역 입력 시에는 admCd 유지

### admCd 직접 조회 메커니즘

DongPanel의 🤖 AI 버튼 → ChatPanel → api_server.py 경로로 행정동 코드가 직접 전달됩니다.
이를 통해 AREA_MAP에 등록되지 않은 개별 행정동도 정확히 조회할 수 있습니다.

```python
# api_server.py — admCd 직접 조회 흐름
if req.adm_cd and business_type:
    temp_key = f"__adm_{req.adm_cd}"
    AREA_MAP[temp_key] = [req.adm_cd]        # 임시 등록
    result = await _agent.analyze(temp_key, business_type, quarter)
    AREA_MAP.pop(temp_key, None)              # 정리
```

- AREA_MAP은 구 단위("종로", "강남")로 매핑 → 개별 동("사직동") 미지원
- admCd 직접 전달로 이 한계를 우회하여 **모든 행정동** 분석 가능

### 프론트엔드 파일 구성 (TERRY/p02_frontEnd_React)

| 파일 | 설명 |
|------|------|
| `src/api/agentApi.js` | API 클라이언트 (sendChatMessage, getLocations, getIndustries) |
| `src/components/ChatPanel.jsx` | 채팅 패널 (세션 관리, 네비게이션, 컨텍스트 주입/해제, 지역 자동 감지) |
| `src/components/ChatPanel.css` | 채팅 UI 스타일 (슬라이드 패널, 컨텍스트 표시, 메시지 버블, 로딩 애니메이션) |
| `src/components/panel/DongPanel.jsx` | 행정동 데이터 패널 (점포/매출/실거래 + 🤖 AI 분석 버튼) |
| `src/components/panel/CategoryPanel.jsx` | 좌측 카테고리 사이드바 (업종 필터, 구/동 검색) |
| `src/components/MapView.jsx` | 메인 지도 컴포넌트 (모든 패널 통합, 상태 관리) |
| `vite.config.js` | `/agent` 프록시 설정 (→ `http://localhost:8000`) |

### ChatPanel 주요 기능

- **admCd 직접 조회**: DongPanel 🤖 AI 버튼 → admCd 전달 → AREA_MAP 우회 DB 조회
- **지역명 자동 감지**: 입력에 다른 지역명 포함 시 admCd 무시 → 텍스트 기반 분석 전환
- **컨텍스트 표시/해제**: 📍 표시 + ✕ 버튼으로 선택 해제 → 자유 입력 모드 복귀
- **네비게이션 패턴 감지**: `/(.+?)\s*(보여줘|이동|찾아줘|어디)/` → Kakao 키워드 검색 → 지도 이동
- **업종 자동 감지**: 카페, 한식, 치킨 등 입력 시 현재 선택된 행정동을 자동 주입
- **로딩 타이머**: 분석 소요 시간 실시간 표시 (초 단위)
- **세션 관리**: UUID 기반 session_id로 다회차 대화 유지

### z-index 계층 구조

| z-index | 컴포넌트 | 비고 |
|---------|----------|------|
| 500 | ChatPanel (채팅 패널) | 최상위 오버레이 |
| 450 | ChatPanel 토글 버튼 | 채팅 열기 버튼 |
| 400 | 행정동 로딩 오버레이 | 데이터 로딩 중 표시 |
| 350 | DongPanel (행정동 패널) | 점포/매출/실거래 데이터 |
| 300 | WmsPopup / 좌표바 | 지도 팝업 |
| 200 | CategoryPanel / MapControls | 기본 UI 레이어 |

---

## 성능 최적화

기존 대비 **응답 시간 약 30초 → 6~8초**로 개선 (약 4~5배 향상)

### 적용된 최적화 항목

| #   | 최적화 항목                  | 설명                                                                 | 효과                                  |
| --- | ---------------------------- | -------------------------------------------------------------------- | ------------------------------------- |
| 1   | **모델 변경**                | gpt-5-nano → gpt-4.1-mini                                            | Thinking 오버헤드 제거, 30초 → 8~10초 |
| 2   | **DB 쿼리 병렬화**           | get_sales + get_store_count를 asyncio.gather로 동시 실행             | DB 대기시간 ~50% 감소                 |
| 3   | **LLM + 유사상권 동시 실행** | \_run_agent()와 get_similar_locations()를 asyncio.gather로 동시 실행 | ~300ms 절약                           |
| 4   | **compare() 병렬화**         | 모든 지역의 DB 쿼리를 한번에 병렬 실행                               | 3개 지역 비교 시 ~80% 단축            |
| 5   | **Kernel 싱글턴**            | Kernel + AzureChatCompletion 객체를 한 번만 생성하여 재사용          | 객체 생성 오버헤드 제거               |
| 6   | **DB 커넥션 풀링**           | oracledb.create_pool(min=2, max=5)로 커넥션 재사용                   | 쿼리당 ~50~100ms 절약                 |
| 7   | **LLM 토큰 절약**            | 불필요 필드 제거 (30개 → 15개)                                       | 입력 토큰 ~45% 감소                   |
| 8   | **수치 사전 계산**           | 금액 변환(억/만원), 비율, 피크타임, 주요 고객층을 미리 계산하여 전달 | 토큰 추가 절약 + 계산 오류 방지       |

### 모델 선택 근거

| 모델                    | Thinking          | 이 작업 적합도 | 비고                                         |
| ----------------------- | ----------------- | -------------- | -------------------------------------------- |
| gpt-5-nano (이전)       | 자동 실행 (~25초) | 과잉           | 구조화 작업에 불필요한 추론 오버헤드         |
| **gpt-4.1-mini (현재)** | **없음**          | **최적**       | instruction following 특화, 정형 출력에 최적 |

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

| 함수                      | 역할                            | 예시                              |
| ------------------------- | ------------------------------- | --------------------------------- |
| `_format_krw()`           | 원 → 억/만원 변환               | `2028280000` → `"20억 2,828만원"` |
| `_calc_pct()`             | 비율 계산 (0 나누기 방지)       | `(1350850000, 2028280000)` → `67` |
| `_find_peak_time()`       | 시간대 6개 비교 → 피크타임 판별 | → `"14~17시"`                     |
| `_find_top_age()`         | 연령대 6개 비교 → 주요 고객층   | → `("20대", 43)`                  |
| `_precompute_summary()`   | 합산 요약 사전 계산             | 위 함수 조합                      |
| `_precompute_breakdown()` | 상권별 데이터 사전 계산         | 위 함수 조합                      |

---

## API 서버 (api_server.py)

### 엔드포인트

| Method | Path | 설명 | 요청 | 응답 |
|--------|------|------|------|------|
| `POST` | `/chat` | 자연어 상권 분석 또는 admCd 직접 조회 | `{question, session_id?, adm_cd?}` | `{session_id, type, analysis, ...}` |
| `GET` | `/locations` | 지원 지역 목록 | — | `{locations: [...]}` |
| `GET` | `/industries` | 지원 업종 목록 | — | `{industries: [...]}` |
| `GET` | `/health` | 서버 상태 확인 | — | `{status: "ok"}` |

### POST /chat 요청/응답

```json
// 요청 1: 자연어 질문
{
  "question": "홍대에서 카페 창업하려는데 분석해줘",
  "session_id": "optional-uuid"
}

// 요청 2: admCd 직접 조회 (DongPanel 🤖 AI 버튼 경유)
{
  "question": "카페 상권 분석",
  "session_id": "optional-uuid",
  "adm_cd": "1111062"
}

// 응답 (analyze)
{
  "session_id": "uuid",
  "type": "analyze",
  "analysis": "📅 데이터 기준: ...",
  "similar_locations": [...],
  "location": "홍대",
  "business_type": "카페",
  "quarter": "20253"
}

// 응답 (compare)
{
  "session_id": "uuid",
  "type": "compare",
  "analysis": "📊 비교 분석 결과...",
  "locations": ["강남", "홍대"],
  "business_type": "카페",
  "quarter": "20253",
  "data": [...]
}
```

### 파라미터 추출 (자연어 → 구조화)

`POST /chat`에 `adm_cd`가 없을 경우, 자연어를 Azure OpenAI로 파싱하여 에이전트 파라미터로 변환합니다.

```
"강남에서 카페 창업하려는데 분석해줘"
    ↓ _extract_params()
{
    "mode": "analyze",
    "locations": ["강남"],
    "business_type": "카페",
    "quarter": "20253"
}
```

- **mode**: `analyze` (단일 지역) 또는 `compare` (복수 지역 비교) 자동 분기
- **adm_cd 우선**: `adm_cd`가 전달되면 파라미터 추출은 `business_type`만 사용
- **quarter**: 미지정 시 최근 분기 자동 적용

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
- **한계**: 구 단위 키워드만 지원 → 개별 행정동("사직동") 직접 검색 불가
- **보완**: admCd 직접 전달 방식으로 모든 행정동 분석 가능

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

| 환경        | 모델           | 비고                                     |
| ----------- | -------------- | ---------------------------------------- |
| 개발/테스트 | `gpt-4.1-mini` | instruction following 특화, 빠른 응답    |
| 서비스      | `gpt-4.1-mini` | 구조화 출력 최적, Thinking 오버헤드 없음 |

> **모델 선택 기준**: 이 에이전트의 작업은 "구조화된 데이터 → 정형 한국어 텍스트 변환"으로, 깊은 추론보다 instruction following과 포맷 준수가 중요합니다. GPT-4.1 계열이 이 특성에 가장 적합합니다.

---

## 데이터 출처

- 매출: 서울시 상권분석서비스 추정매출-행정동 (VwsmAdstrdSelngQq)
- 점포: 서울시 상권분석서비스 점포-행정동 (VwsmAdstrdStorW)
- 기준 분기: 2019년 1분기 ~ 2025년 3분기

---

## 실행 방법

### 에이전트 단독 테스트

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

### API 서버 + 프론트엔드 연동 실행

```bash
# 터미널 1: 지도 데이터 서버 (포트 8681, 8682)
# 점포 데이터 서버와 상권/실거래 서버가 각각 실행되어야 합니다

# 터미널 2: 상권분석 에이전트 API 서버
cd CHOI/locationAgent_DB
.venv\Scripts\activate
python api_server.py
# → http://localhost:8000 에서 서버 실행

# 터미널 3: React 프론트엔드
cd TERRY/p02_frontEnd_React
npm install
npm run dev
# → http://localhost:5173 에서 프론트 실행
# → /agent/* 요청은 Vite 프록시로 localhost:8000 으로 전달
```

### 사용 흐름

```
1. 채팅 직접 입력
   💬 토글 버튼 클릭 → "홍대 카페 상권 분석해줘" 입력 → 분석 결과 수신

2. 지도 연동 입력
   좌하단 점포수/매출/실거래 버튼 클릭 → 지도에서 행정동 클릭 →
   DongPanel 표시 → 🤖 AI 버튼 클릭 → ChatPanel 오픈 (컨텍스트 자동 설정) →
   "카페" 입력 → 해당 행정동 카페 분석 결과 수신

3. 지역 전환
   컨텍스트 설정된 상태에서 "잠실 치킨 분석" 입력 →
   지역명 자동 감지 → admCd 무시 → 잠실 치킨 분석 실행
   또는 📍 옆 ✕ 클릭 → 컨텍스트 해제 → 자유 입력
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
