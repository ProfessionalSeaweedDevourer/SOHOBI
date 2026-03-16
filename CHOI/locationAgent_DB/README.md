# 상권분석 에이전트 (LocationAgent)

Azure OpenAI + Semantic Kernel + SQLite를 활용한 F&B 창업 지원 상권분석 에이전트입니다.  
오케스트레이터(부모 에이전트)에 SK Plugin으로 연결되는 자식 에이전트입니다.

---

## 폴더 구조
```
locationAgent_sang/
├── agent/
│   └── location_agent.py       # 상권분석 에이전트 본체 (DB 조회 → LLM 분석)
├── db/
│   ├── commercial.db           # SQLite DB (load_csv.py 실행 시 생성)
│   ├── load_csv.py             # CSV → DB 적재 스크립트 (실제 데이터)
│   ├── mock_db.py              # 샘플 데이터 생성 (테스트용)
│   └── repository.py           # DB 조회 레이어 (Oracle 전환 시 이 파일만 수정)
├── plugin/
│   └── location_plugin.py      # 오케스트레이터 연결용 SK Plugin 래퍼
├── test/
│   └── test_location.py        # 단독 테스트
├── .env                        # API 키 설정 (Git 미포함)
├── .env.example                # 환경변수 예시
└── requirements.txt            # 패키지 의존성
```

---

## 시스템 구조
```
[오케스트레이터]
    ↓ SK Plugin 직접 연결
[LocationAgent]
    ↓ SQL 조회
[SQLite DB] ← CSV 데이터 적재 (서울시 상권분석 API)
    ↓
상권별 매출/점포수 분석 결과 반환
```

---

## 주요 기능

### 1. 단일 지역 분석 (`analyze`)
지역 + 업종 + 분기를 입력받아 상권 분석 결과 반환

**출력 항목:**
- 전체 합산 요약 (월매출, 점포수, 주중/주말 비율, 피크타임, 주요 고객층, 점포당 평균매출)
- 상권별 분리 분석 (개폐업률, 점포당 평균매출 포함)
- 기회 요인 / 리스크 요인
- 유사 상권 추천 TOP 3 (복합 점수 기반)

### 2. 복수 지역 비교 (`compare`)
여러 지역을 동시에 비교하여 창업 추천 순위 제공

**출력 항목:**
- 지역별 비교표 (월매출, 점포수, 점포당 평균매출, 주중/주말, 개폐업률, 주요 성별)
- 창업 추천 순위 (점포당 평균매출 > 폐업률 낮음 > 개업률 적정 기준)
- 지역별 유의사항

---

## SK Plugin 함수 목록

| 함수명 | 설명 | 파라미터 |
|--------|------|---------|
| `analyze_commercial_area` | 단일 지역 상권 분석 | location, business_type, quarter |
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
- 이상치 필터: 점포당 평균매출 8,000만원 초과 및 점포수 2개 이하 제외

---

## 지역 매핑 구조 (AREA_MAP)

- **172개 키워드 → 227개 상권명** 매핑
- 권역별 분류: 홍대/마포, 강남, 서초/사당, 여의도/영등포, 종로/도심, 이태원/용산, 건대/성수, 신촌/서대문, 잠실/송파, 강동, 노원/도봉/강북, 관악/동작, 강서/양천, DMC/은평

---

## 지원 업종

한식, 중식, 일식, 양식, 베이커리, 패스트푸드, 치킨, 분식, 호프/술집, 카페/커피, 미용실, 네일, 노래방, 편의점

---

## 에러 처리

```
❌ '부산' 은(는) 지원하지 않는 지역입니다. 서울 내 지역만 조회 가능합니다.
❌ '피자' 은(는) 지원하지 않는 업종입니다.
```

---

## 사용 모델

| 환경 | 모델 | 비고 |
|------|------|------|
| 개발/테스트 | `gpt-5-nano` | 저비용, 빠른 응답 |
| 서비스 | `gpt-5-mini` 이상 권장 | 품질 우선 |

---

## 데이터 출처

- 매출: 서울시 상권분석서비스 추정매출-상권 (VwsmTrdarSelngQq)
- 점포: 서울시 상권분석서비스 점포 (VwsmTrdarStorQq)
- 기준 분기: 2024년 1~4분기

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
# .env 파일에 API 키 입력

# 4. DB 적재 (서울시 CSV 파일 필요, data/ 폴더에 위치)
python db/load_csv.py

# 5. 테스트 실행
python test/test_location.py
```

---

## 환경변수 (.env)

```
AZURE_OPENAI_ENDPOINT=...
AZURE_OPENAI_CHAT_DEPLOYMENT_NAME=gpt-5-nano
AZURE_OPENAI_API_KEY=...
AZURE_OPENAI_API_VERSION=2024-05-01-preview
```

---

## Oracle 전환 시

`db/repository.py` 파일만 수정하면 됩니다 (agent/plugin 코드 수정 불필요):

| 항목 | SQLite | Oracle |
|------|--------|--------|
| import | `import sqlite3` | `import cx_Oracle` |
| 연결 | `sqlite3.connect(DB_PATH)` | `cx_Oracle.connect(user, pw, dsn)` |
| 플레이스홀더 | `?` | `:1` 또는 `:변수명` |
| 페이징 | `LIMIT N` | `WHERE ROWNUM <= N` |