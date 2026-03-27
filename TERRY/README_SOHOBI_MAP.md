# SOHOBI - 상권 지도 분석 모듈

> **우태희 (데이터 엔지니어)** | 상권 지도 에이전트 담당  
> 전체 프로젝트: MS SAY 2-2 | 2026년 2월 25일 ~ 2026년 4월

---

## 모듈 개요

소상공인 창업 지원 AI 시스템의 **상권 지도 에이전트** 컴포넌트입니다.  
서울 행정동 단위 매출·점포수·실거래가·소상공인 분포를 지도 위에 시각화합니다.

---

## 폴더 구조

```
SOHOBI/
├── p01_backEnd/                    ← FastAPI 백엔드
│   ├── mapController.py            포트 8681: 소상공인 반경검색, 랜드마크
│   ├── realEstateController.py     포트 8682: 매출/점포수/실거래가
│   └── DAO/
│       ├── fable/                  Oracle DB 연결 유틸
│       ├── baseDAO.py              공통 베이스
│       ├── mapInfoDAO.py           소상공인 반경검색, DataFrame 캐시
│       ├── sangkwonDAO.py          SANGKWON_SALES 매출 조회
│       ├── sangkwonStoreDAO.py     SANGKWON_STORE 점포수/개폐업률
│       ├── seoulRtmsDAO.py         서울 열린데이터광장 실거래가 API
│       ├── molitRtmsDAO.py         국토부 오피스텔/상업용 DB 조회
│       ├── landmarkDAO.py          관광지/문화시설/학교 DB 조회
│       ├── landValueDAO.py         공시지가 API
│       ├── dongMappingDAO.py       LAW_ADM_MAP emd_cd↔adm_cd 매핑
│       └── wfsDAO.py               VWorld WFS 하위호환
│
├── p02_frontEnd_React/             ← React + OpenLayers 프론트
│   ├── public/
│   │   └── seoul_adm_dong.geojson  서울 행정동 경계 (427개)
│   └── src/
│       ├── components/
│       │   ├── MapView.jsx          메인 지도 컴포넌트
│       │   ├── panel/
│       │   │   ├── DongPanel.jsx    행정동 클릭 패널 (매출/점포수/실거래가)
│       │   │   ├── DongPanel/       패널 서브 컴포넌트
│       │   │   │   ├── formatHelpers.js
│       │   │   │   ├── RealEstatePanel.jsx
│       │   │   │   ├── StorePanel.jsx
│       │   │   │   ├── SvcPanel.jsx
│       │   │   │   ├── SalesDetail.jsx
│       │   │   │   ├── SalesSummary.jsx
│       │   │   │   ├── GenderDonut.jsx
│       │   │   │   ├── BarRow.jsx
│       │   │   │   └── constants.js
│       │   │   ├── CategoryPanel.jsx 업종 필터 사이드바
│       │   │   └── LayerPanel.jsx    레이어 패널
│       │   ├── controls/
│       │   │   └── MapControls.jsx  상단 버튼 (점포수/매출/실거래가)
│       │   └── popup/
│       │       ├── StorePopup.jsx   소상공인 클릭 팝업
│       │       └── WmsPopup.jsx     WMS 지적도 팝업
│       ├── hooks/
│       │   ├── useDongLayer.js      행정동 폴리곤 로드
│       │   ├── useMarkers.js        소상공인 마커 (CAT_CD 색상/하이라이트)
│       │   └── useWmsClick.js       WMS GetFeatureInfo
│       └── constants/
│           └── categories.js        업종 SVC_CD 기준 정의
│
├── p03_OracleDB_Script/            ← DB 생성 스크립트
│   ├── MS2_PROJECT_STORE.sql        STORE_SEOUL 등 17개 테이블
│   ├── MS2_PROJECT_VWORLD_SangKwon.sql  SANGKWON_SALES + 뷰
│   ├── MS2_PROJECT_SANGKWON_STORE.sql   SANGKWON_STORE
│   ├── MS2_PROJECT_MOLIT_RTMS.sql   RTMS_OFFICETEL, RTMS_COMMERCIAL
│   ├── MS2_PROJECT_LANDMARK.sql     LANDMARK, SCHOOL_SEOUL
│   └── MS2_SVC_INDUSTRY_MAP.sql     SVC_INDUTY_MAP
│
└── p04_DataLoader/                 ← 데이터 수집/적재
    ├── load_store_csv.py            소상공인 CSV → STORE_SEOUL
    ├── load_sangkwon_sales_csv.py   매출 CSV → SANGKWON_SALES
    ├── load_sangkwon_store_csv.py   점포수 CSV → SANGKWON_STORE
    ├── insert_law_adm.py            법정동↔행정동 매핑 INSERT
    ├── insert_svc_induty_map.py     업종코드 매핑 INSERT
    ├── filter_seoul_adm_dong.py     GeoJSON 서울 필터
    ├── collector/
    │   ├── collect_sangkwon_sales.py  매출 API 수집 (연도별, append/quarter)
    │   ├── collect_molit_rtms.py      국토부 실거래가 수집 (서울 25구)
    │   └── collect_landmark.py        관광지/문화시설 수집 (1회)
    └── csv/
        ├── mapping/                 GitHub 포함
        │   ├── law_adm_map_new.csv  법정동↔행정동 467건
        │   └── svc_induty_map.csv   업종코드 100건
        ├── sangkwon_sales/          gitignore
        ├── sangkwon_store/          gitignore
        └── location_csv/            gitignore
```

---

## DB 구성

| 테이블 | 내용 | 건수 |
|--------|------|------|
| `STORE_SEOUL` | 서울 소상공인 상권정보 | 534,978건 |
| `SANGKWON_SALES` | 행정동별 추정매출 (분기별) | 19~25년 |
| `SANGKWON_STORE` | 행정동별 점포수/개폐업률 | 분기별 |
| `V_SANGKWON_LATEST` | 최신분기 매출 뷰 | - |
| `SVC_INDUTY_MAP` | 업종코드 매핑 | 100건 |
| `LAW_ADM_MAP` | 법정동↔행정동 매핑 | 467건 |
| `LAW_DONG_SEOUL` | 서울 법정동 | 467건 |
| `RTMS_OFFICETEL` | 오피스텔 전월세 (국토부) | 수집분 |
| `RTMS_COMMERCIAL` | 상업용 매매 (국토부) | 수집분 |
| `LANDMARK` | 관광지/문화시설 (한국관광공사) | 수집분 |
| `SCHOOL_SEOUL` | 서울 학교 정보 | 수집분 |

**DB 접속:** `shobi/8680@//10.1.92.119:1521/xe`

---

## API 서버

### mapController (포트 8681)
```bash
uvicorn mapController:app --host=0.0.0.0 --port=8681 --reload
```

| 엔드포인트 | 설명 |
|-----------|------|
| `GET /map/nearby` | 좌표 반경 소상공인 검색 |
| `GET /map/nearby-bbox` | BBox 소상공인 검색 |
| `GET /map/landmarks` | 관광지/문화시설 조회 |
| `GET /map/festivals` | 축제 실시간 API |
| `GET /map/schools` | 학교 정보 조회 |
| `GET /map/land-use` | 용도지역 (VWorld) |

### realEstateController (포트 8682)
```bash
uvicorn realEstateController:app --host=0.0.0.0 --port=8682 --reload
```

| 엔드포인트 | 설명 |
|-----------|------|
| `GET /realestate/seoul-rtms` | 실거래가 통합 조회 |
| `GET /realestate/sangkwon` | 행정동별 매출 |
| `GET /realestate/sangkwon-svc` | 업종별 매출 |
| `GET /realestate/sangkwon-store` | 점포수/개폐업률 |
| `GET /realestate/sangkwon-quarters` | 수집 분기 목록 |
| `GET /realestate/search-dong` | 행정동명 검색 |
| `GET /realestate/land-value` | 공시지가 |

---

## 프론트엔드 실행

```bash
cd p02_frontEnd_React
npm install
npm run dev   # http://localhost:5173
```

### 주요 기능
- 서울 행정동 폴리곤 클릭 → 매출/점포수/실거래가 패널
- 소상공인 마커 반경검색 + 업종 필터
- 업종별 매출 막대차트 (SVC_CD 기준)
- 실거래가: 아파트/오피스텔/상업용 통합
- 행정동명 검색 (DB LIKE 검색 fallback)

---

## 데이터 적재 순서 (초기 셋업)

```bash
cd p04_DataLoader

# 1. DB 테이블 생성 (DBeaver에서 SQL 실행)
#    p03_OracleDB_Script/ 폴더의 SQL 파일들

# 2. 매핑 데이터 적재
python insert_law_adm.py
python insert_svc_induty_map.py

# 3. 소상공인 데이터
python load_store_csv.py "csv/location_csv/소상공인_서울_202512.csv" STORE_SEOUL

# 4. 상권 매출 (연도별)
python load_sangkwon_sales_csv.py --year=2024
python load_sangkwon_sales_csv.py --year=2025

# 5. 점포수
python load_sangkwon_store_csv.py --year=2024

# 6. 실거래가 (국토부)
cd collector
python collect_molit_rtms.py --year=2024

# 7. 랜드마크 (1회)
python collect_landmark.py
```

---

## 통합 방법 (메인 앱 연동)

메인 React 앱(`frontend/`)에 통합 시:

```
frontend/src/pages/map/   ← p02_frontEnd_React/src/ 내용 복사
frontend/public/           ← seoul_adm_dong.geojson 복사
```

`frontend/vite.config.js`:
```js
base: '/map/',
proxy: {
  '/map-api': 'http://10.1.92.119:8681',
  '/re-api':  'http://10.1.92.119:8682',
}
```

`frontend/src/App.jsx`:
```jsx
import MapApp from "./pages/map/MapApp";
<Route path="/map/*" element={<MapApp />} />
```

---

## 환경변수 (.env)

```dotenv
VITE_MAP_URL=http://10.1.92.119:8681
VITE_REALESTATE_URL=http://10.1.92.119:8682
MOLIT_OP_API_KEY=...       # 국토부 오피스텔 전월세
MOLIT_NRG_API_KEY=...      # 국토부 상업용 매매
KTO_GW_INFO_KEY=...        # 한국관광공사
SEOUL_MOLIT_API_KEY=...    # 서울 열린데이터광장
```
