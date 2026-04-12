# 지도 백엔드 통합 가이드

> **대상**: WOO 팀원 (TerryBlackhoodWoo)
> **작성일**: 2026-04-03
> **목적**: `backend/` 폴더에서 개발한 지도·부동산 API를 `integrated_PARK`(라이브 서버)에 통합하는 전 과정 안내

---

## 1. 지금 상황 — 두 코드베이스가 병렬로 존재

PR#105가 main에 머지되어, 현재 저장소에는 **두 벌의 백엔드 코드**가 공존합니다.

```
SOHOBI/
├── backend/                   ← WOO가 만든 지도·부동산 백엔드 (방금 main에 들어온 것)
│   ├── mapController.py       (포트 8681, 독립 FastAPI 서버)
│   ├── realEstateController.py (포트 8682, 독립 FastAPI 서버)
│   └── DAO/                   (psycopg2 기반 PostgreSQL DAO)
│
└── integrated_PARK/           ← 현재 Azure에서 라이브 중인 통합 서버
    ├── api_server.py          (포트 8000, 단일 FastAPI 서버)
    ├── map_router.py          (지도·부동산 라우터, 일부 stub 상태)
    └── db/repository.py       (동일한 Azure PostgreSQL 연결)
```

**핵심 사실**: 두 폴더 모두 **같은 Azure PostgreSQL DB**를 바라봅니다. 테이블 구조도 같습니다.
따라서 통합은 "DB 이전" 없이, **코드 구조만 변경**하면 됩니다.

---

## 2. 왜 통합해야 하는가

`integrated_PARK`의 `map_router.py`에는 지도 관련 엔드포인트가 이미 있지만,
WOO가 만든 것보다 **기능이 적거나 일부는 빈 응답(stub)** 을 반환하고 있습니다.

| 엔드포인트 | integrated_PARK 현황 | backend/ 현황 |
|---|---|---|
| `/realestate/sangkwon` | 동작 중 | 동작 중 (더 풍부한 필드) |
| `/realestate/sangkwon-svc` | 동작 중 | 동작 중 |
| `/realestate/sangkwon-store` | 동작 중 | 동작 중 |
| `/realestate/sangkwon-svc-by-cat` | 동작 중 | 동작 중 |
| `/realestate/search-dong` | 동작 중 | 동작 중 |
| `/realestate/sangkwon-quarters` | 동작 중 | 동작 중 |
| `/realestate/seoul-rtms` | **빈 응답 (stub)** | 실데이터 반환 |
| `/map/stores-by-dong` | **빈 응답 (stub)** | 실데이터 반환 |
| `/map/nearby` | **빈 응답 (stub)** | 실데이터 반환 |
| `/map/stores-by-building` | **빈 응답 (stub)** | 실데이터 반환 |

**통합 후 새로 추가되는 엔드포인트** (현재 integrated_PARK에 아예 없음):

| 엔드포인트 | 설명 |
|---|---|
| `/map/categories` | 업종 대분류 목록 |
| `/map/landmarks` | 랜드마크(문화시설 등) |
| `/map/festivals` | 축제 (KTO 공공데이터 실시간) |
| `/map/schools` | 학교 목록 |
| `/map/sdot/sensors` | S-DoT 유동인구 센서 위치 |
| `/map/dong-density` | 행정동별 밀도 |
| `/map/nearby-bbox` | 폴리곤 내 점포 조회 |
| `/map/land-use` | 용도지역 (VWorld) |
| `/map/dong-centroids` | 동 중심좌표 (카카오 API) |
| `/realestate/sangkwon-induty` | 업종 대/소분류별 매출 |
| `/realestate/land-value` | 공시지가 (VWorld) |

---

## 3. 통합 절차 — 단계별 상세 안내

### Step 0. 브랜치 최신화

```bash
git checkout PARK        # (또는 WOO-clean2)
git fetch origin
git merge origin/main    # PR#105 포함한 최신 main 반영
```

---

### Step 1. DAO 파일 이전

`backend/DAO/` 안의 파일들을 `integrated_PARK/db/dao/` 폴더에 복사합니다.
`integrated_PARK/db/`에는 이미 `repository.py`가 있으므로, 그 옆에 `dao/` 서브폴더를 만듭니다.

```
integrated_PARK/db/
├── repository.py          ← 기존 파일 (건드리지 않음)
├── finance_db.py          ← 기존 파일 (건드리지 않음)
└── dao/                   ← 신규 폴더
    ├── __init__.py        ← 빈 파일로 생성
    ├── baseDAO.py         ← backend/DAO/baseDAO.py 복사
    ├── mapInfoDAO.py
    ├── landmarkDAO.py
    ├── sangkwonDAO.py
    ├── sangkwonStoreDAO.py
    ├── seoulRtmsDAO.py
    ├── molitRtmsDAO.py
    ├── dongMappingDAO.py
    └── landValueDAO.py
```

**주의**: 각 DAO 파일 상단의 `sys.path.insert(...)` 구문은 제거합니다.
`from DAO.baseDAO import BaseDAO` → `from db.dao.baseDAO import BaseDAO` 로 import 경로 수정.

**`baseDAO.py`는 그대로 사용 가능합니다.** 환경변수 이름이 `integrated_PARK`의 `repository.py`와 동일합니다:

```
PG_HOST, PG_PORT, PG_DB, PG_USER, PG_PASSWORD, PG_SSL_MODE
```

---

### Step 2. 컨트롤러를 APIRouter로 변환

`integrated_PARK`은 **FastAPI의 `APIRouter`** 방식을 사용합니다.
`backend/`의 두 컨트롤러는 `FastAPI` 앱 전체로 되어 있으므로, 형식만 바꿔주면 됩니다.

#### 변경 전 (backend/mapController.py 현재 형태)
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(lifespan=lifespan)
app.add_middleware(CORSMiddleware, ...)

@app.get("/map/nearby")
async def get_nearby(...):
    ...
```

#### 변경 후 (integrated_PARK에 들어갈 형태)
```python
from fastapi import APIRouter

router = APIRouter()

@router.get("/map/nearby")
async def get_nearby(...):
    ...
```

**제거할 것**:
- `app = FastAPI(lifespan=lifespan)` — api_server.py가 이미 가짐
- `app.add_middleware(CORSMiddleware, ...)` — api_server.py가 이미 처리
- `@asynccontextmanager async def lifespan(app)` 블록 — startup 로직은 api_server.py의 lifespan에 합칠 것

**변환 결과 파일 이름** (임의로 정하면 됨):
- `mapController.py` → `integrated_PARK/map_data_router.py`
- `realEstateController.py` → `integrated_PARK/realestate_router.py`

---

### Step 3. api_server.py에 router 등록

`integrated_PARK/api_server.py` 상단 import 부분에 추가:

```python
from map_data_router import router as map_data_router
from realestate_router import router as realestate_router
```

그리고 `app.include_router(map_router)` 라인 근처에 추가:

```python
app.include_router(map_router)         # 기존
app.include_router(map_data_router)    # 신규 (mapController 변환)
app.include_router(realestate_router)  # 신규 (realEstateController 변환)
```

---

### Step 4. 기존 map_router.py 정리

`integrated_PARK/map_router.py`에는 지금 **stub(빈 응답)** 으로 작성된 엔드포인트 4개가 있습니다:

```python
@router.get("/realestate/seoul-rtms")
async def get_seoul_rtms(...):
    return []   ← 빈 응답

@router.get("/map/stores-by-dong")
async def get_stores_by_dong(...):
    return []   ← 빈 응답

@router.get("/map/nearby")
@router.get("/map/stores-by-building")
```

이 4개는 WOO의 DAO를 연결한 버전으로 **교체**하거나, `map_router.py`에서 **삭제**하고 새 router 파일에서 처리합니다.
(같은 경로가 두 router에 동시에 존재하면 FastAPI가 먼저 등록된 것을 우선 사용하므로, 반드시 하나만 남겨야 합니다.)

---

### Step 5. 환경변수 추가

`integrated_PARK/.env`에 다음 키를 추가합니다 (Azure Container Apps 환경변수에도 동일하게 추가 필요):

```bash
# VWorld API (지도/지적도/공시지가)
VWORLD_API_KEY=BE3AF33A-...

# Kakao REST API (상가 상세정보)
KAKAO_REST_KEY=064e455e...

# 한국관광공사 API (랜드마크/축제)
KTO_GW_INFO_KEY=b7906dd7...
```

실제 키 값은 `backend/.env.example`에서 확인하세요.
**Azure Container Apps 환경변수 등록은 PARK 팀원에게 요청합니다.**

---

### Step 6. requirements.txt 확인

`backend/requirements.txt`:
```
fastapi>=0.111.0
uvicorn[standard]>=0.29.0
httpx>=0.27.0
psycopg2-binary==2.9.9
python-dotenv>=1.0.0
```

`integrated_PARK/requirements.txt`에는 `psycopg2-binary==2.9.9`가 이미 있습니다.
`httpx`가 있는지 확인하고 없으면 추가합니다:

```bash
grep httpx integrated_PARK/requirements.txt
```

---

## 4. 통합 후 WOO 코드 변경 시 반영 방법

통합이 완료되면 **`integrated_PARK/db/dao/`가 진실의 원천(source of truth)** 이 됩니다.

### 시나리오 A — 새 DAO를 추가하는 경우

1. `backend/DAO/`에 새 DAO 파일 개발 (로컬 테스트 가능)
2. 완성되면 `integrated_PARK/db/dao/`에 복사
3. import 경로 수정 (`from DAO.xxx` → `from db.dao.xxx`)
4. 해당 router 파일에 엔드포인트 추가
5. WOO-clean2 브랜치에서 main으로 PR

### 시나리오 B — 기존 DAO 로직 수정하는 경우

1. `backend/DAO/`에서 수정 후 로컬 테스트
2. 동일 변경을 `integrated_PARK/db/dao/`에도 반영
3. PR

### 시나리오 C — 새 엔드포인트만 추가하는 경우

1. `backend/mapController.py` (또는 `realEstateController.py`)에 엔드포인트 추가
2. 동일 엔드포인트를 `integrated_PARK/map_data_router.py` (또는 `realestate_router.py`)에 추가
3. PR

> **팁**: `backend/` 폴더는 **로컬 개발·테스트용**으로 계속 유지할 수 있습니다.
> `python -m uvicorn mapController:app --reload` 로 독립 실행하여 빠르게 확인한 뒤,
> 검증된 코드만 `integrated_PARK`에 반영하는 워크플로우가 효율적입니다.

---

## 5. 검증 방법

통합 완료 후 로컬에서:

```bash
cd integrated_PARK
.venv/bin/python3 api_server.py
```

아래 curl로 각 항목 확인:

```bash
# 기존 기능 회귀 없는지
curl http://localhost:8000/realestate/sangkwon?adm_cd=11440660

# stub → 실데이터 전환 확인
curl http://localhost:8000/realestate/seoul-rtms?adm_cd=11440660
curl "http://localhost:8000/map/nearby?lat=37.5658&lng=126.9894&radius=300"
curl http://localhost:8000/map/stores-by-dong?adm_cd=11440660

# 신규 엔드포인트 확인
curl http://localhost:8000/map/categories
curl "http://localhost:8000/map/landmarks?lat=37.5&lng=127.0"
curl "http://localhost:8000/map/schools?sgg_nm=마포구"
curl "http://localhost:8000/realestate/land-value?pnu=1168010100&year=2024"
```

---

## 6. 파일 변경 요약

| 파일 | 작업 | 담당 |
|---|---|---|
| `integrated_PARK/db/dao/__init__.py` | 신규 (빈 파일) | PARK or WOO |
| `integrated_PARK/db/dao/baseDAO.py` | `backend/DAO/baseDAO.py` 복사 + import 수정 | WOO |
| `integrated_PARK/db/dao/mapInfoDAO.py` | 동일 | WOO |
| `integrated_PARK/db/dao/landmarkDAO.py` | 동일 | WOO |
| `integrated_PARK/db/dao/sangkwonDAO.py` | 동일 | WOO |
| `integrated_PARK/db/dao/sangkwonStoreDAO.py` | 동일 | WOO |
| `integrated_PARK/db/dao/seoulRtmsDAO.py` | 동일 | WOO |
| `integrated_PARK/db/dao/molitRtmsDAO.py` | 동일 | WOO |
| `integrated_PARK/db/dao/dongMappingDAO.py` | 동일 | WOO |
| `integrated_PARK/db/dao/landValueDAO.py` | 동일 | WOO |
| `integrated_PARK/map_data_router.py` | `mapController.py` → APIRouter 변환 | WOO |
| `integrated_PARK/realestate_router.py` | `realEstateController.py` → APIRouter 변환 | WOO |
| `integrated_PARK/map_router.py` | stub 4개 제거 또는 DAO로 교체 | PARK or WOO 협의 |
| `integrated_PARK/api_server.py` | `include_router` 2개 추가 | PARK |
| `integrated_PARK/.env` / Azure 환경변수 | VWORLD, KAKAO, KTO 키 추가 | PARK |
