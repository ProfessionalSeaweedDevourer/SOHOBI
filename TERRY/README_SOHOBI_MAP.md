# SOHOBI - 상권 지도 분석 모듈

> **우태희 (데이터 엔지니어)** | 상권 지도 에이전트 담당  
> 전체 프로젝트: MS SAY 2-2 | 2026년 2월 25일 ~ 2026년 4월

---

## 모듈 개요

소상공인 창업 지원 AI 시스템의 **상권 지도 에이전트** 컴포넌트입니다.  
서울 행정동 단위 매출·점포수·실거래가·소상공인 분포·유동인구를 지도 위에 시각화합니다.

---

## 폴더 구조

```
SOHOBI/
├── p01_backEnd/                        ← FastAPI 백엔드
│   ├── mapController.py                포트 8681
│   ├── realEstateController.py         포트 8682
│   └── DAO/
│       ├── baseDAO.py
│       ├── mapInfoDAO.py               소상공인 반경검색, DataFrame 캐시
│       ├── sangkwonDAO.py              SANGKWON_SALES 매출 조회
│       ├── sangkwonStoreDAO.py         SANGKWON_STORE 점포수/개폐업률
│       ├── seoulRtmsDAO.py             서울 열린데이터광장 실거래가 API
│       ├── molitRtmsDAO.py             국토부 오피스텔/상업용 DB 조회
│       ├── landmarkDAO.py              관광지/문화시설/학교 DB 조회
│       ├── populationDAO.py            서울 실시간 도시데이터 유동인구
│       ├── landValueDAO.py             공시지가 API
│       ├── dongMappingDAO.py           LAW_ADM_MAP emd_cd↔adm_cd 매핑
│       └── wfsDAO.py                   VWorld WFS 하위호환
│
├── p02_frontEnd_React/                 ← React + OpenLayers 프론트
│   ├── public/
│   │   └── seoul_adm_dong.geojson      서울 행정동 경계 (427개)
│   └── src/
│       ├── components/
│       │   ├── MapView.jsx             메인 지도 컴포넌트
│       │   ├── panel/
│       │   │   ├── DongPanel.jsx       행정동 클릭 패널
│       │   │   ├── DongPanel/          패널 서브 컴포넌트
│       │   │   │   ├── formatHelpers.js    formatAmt(원), formatManwon(만원)
│       │   │   │   ├── RealEstatePanel.jsx 실거래가 (매매/전세/월세/오피스텔/상업용)
│       │   │   │   ├── StorePanel.jsx      점포수/개폐업률
│       │   │   │   ├── SvcPanel.jsx        업종별 매출
│       │   │   │   ├── SalesDetail.jsx     성별/연령대/주중주말
│       │   │   │   ├── SalesSummary.jsx    총매출 요약
│       │   │   │   ├── GenderDonut.jsx     SVG 도넛차트
│       │   │   │   ├── BarRow.jsx          막대차트
│       │   │   │   └── constants.js        SVC_COLOR, SVC_LABEL
│       │   │   ├── Layerpanel.jsx      레이어 관리 (지적도/관광안내소/랜드마크/학교/유동인구)
│       │   │   ├── PopulationPanel.jsx 유동인구 범례 패널
│       │   │   ├── CategoryPanel.jsx   업종 필터 사이드바
│       │   │   └── RoadviewPanel.jsx   카카오 로드뷰
│       │   ├── controls/
│       │   │   ├── MapControls.jsx     상단 버튼 (반경분석/로드뷰/유동인구/점포수/매출/부동산)
│       │   │   └── DongTooltip.jsx     행정동 호버 툴팁
│       │   └── popup/
│       │       ├── StorePopup.jsx      소상공인 클릭 팝업 (카카오 연동)
│       │       ├── LandmarkPopup.jsx   랜드마크/학교 팝업 (카카오 연동)
│       │       └── WmsPopup.jsx        VWorld WMS 지적도 팝업
│       ├── hooks/
│       │   ├── useDongLayer.js         행정동 폴리곤 로드
│       │   ├── useMarkers.js           소상공인 마커 (CAT_CD 색상/하이라이트)
│       │   ├── useLandmarkLayer.js     관광지/문화시설/축제/학교 마커
│       │   ├── usePopulationLayer.js   유동인구 히트맵 레이어
│       │   └── useWmsClick.js          VWorld WMS GetFeatureInfo
│       └── constants/
│           └── categories.js           업종 SVC_CD 기준 정의
│
├── p03_OracleDB_Script/                ← DB 생성 스크립트
│   ├── MS2_PROJECT_STORE.sql           STORE_SEOUL 등
│   ├── MS2_PROJECT_VWORLD_SangKwon.sql SANGKWON_SALES + 뷰
│   ├── MS2_PROJECT_SANGKWON_STORE.sql  SANGKWON_STORE
│   ├── MS2_PROJECT_MOLIT_RTMS.sql      RTMS_OFFICETEL, RTMS_COMMERCIAL
│   ├── MS2_PROJECT_LANDMARK.sql        LANDMARK
│   ├── MS2_PROJECT_SCHOOL.sql          SCHOOL_SEOUL (28컬럼 + 좌표)
│   └── MS2_SVC_INDUSTRY_MAP.sql        SVC_INDUTY_MAP
│
└── p04_DataLoader/                     ← 데이터 수집/적재
    ├── load_store_csv.py               소상공인 CSV → STORE_SEOUL
    ├── load_sangkwon_sales_csv.py       매출 CSV → SANGKWON_SALES
    ├── load_sangkwon_store_csv.py       점포수 CSV → SANGKWON_STORE
    ├── insert_law_adm.py               법정동↔행정동 매핑 INSERT
    ├── insert_svc_induty_map.py        업종코드 매핑 INSERT
    └── collecter/
        ├── collect_sangkwon_sales.py   매출 API 수집 (연도별, append/quarter)
        ├── collect_molit_rtms.py       국토부 실거래가 수집 (서울 25구)
        ├── collect_landmark.py         관광지/문화시설 수집 (1회, --no-detail)
        └── collect_school.py           학교 수집 + 카카오 좌표 변환
```

---

## DB 구성

| 테이블              | 내용                       | 건수      |
| ------------------- | -------------------------- | --------- |
| `STORE_SEOUL`       | 서울 소상공인 상권정보     | 534,978건 |
| `STORE_GYEONGGI`    | 경기 소상공인              | 650,081건 |
| `STORE_INCHEON`     | 인천 소상공인              | 132,895건 |
| `STORE_BUSAN`       | 부산 소상공인              | 154,725건 |
| `STORE_DAEGU`       | 대구 소상공인              | 115,238건 |
| `SANGKWON_SALES`    | 행정동별 추정매출 (분기별) | 19~25년   |
| `SANGKWON_STORE`    | 행정동별 점포수/개폐업률   | 분기별    |
| `V_SANGKWON_LATEST` | 최신분기 매출 뷰           | -         |
| `SVC_INDUTY_MAP`    | 업종코드 매핑              | 100건     |
| `LAW_ADM_MAP`       | 법정동↔행정동 매핑         | 467건     |
| `LAW_DONG_SEOUL`    | 서울 법정동                | 467건     |
| `RTMS_OFFICETEL`    | 오피스텔 전월세 (국토부)   | 수집분    |
| `RTMS_COMMERCIAL`   | 상업용 매매 (국토부)       | 수집분    |
| `LANDMARK`          | 관광지/문화시설 (KTO)      | 965건     |
| `SCHOOL_SEOUL`      | 전국 학교 (28컬럼 + 좌표)  | 3,923건   |

**DB 접속:** `shobi/8680@//10.1.92.119:1521/xe`

---

## API 서버

### mapController (포트 8681)

```bash
python -m uvicorn mapController:app --host=0.0.0.0 --port=8681 --reload
```

| 엔드포인트                   | 설명                                |
| ---------------------------- | ----------------------------------- |
| `GET /map/nearby`            | 좌표 반경 소상공인 검색             |
| `GET /map/nearby-bbox`       | BBox 소상공인 검색                  |
| `GET /map/landmarks`         | 관광지/문화시설 DB 조회             |
| `GET /map/festivals`         | 축제 실시간 KTO API (3개월 이내)    |
| `GET /map/schools`           | 학교 정보 DB 조회                   |
| `GET /map/population/all`    | 유동인구 전체 (38개 장소, 5분 캐시) |
| `GET /map/population/place`  | 단일 장소 유동인구 + 예측           |
| `GET /map/population/places` | 장소 목록 + 좌표                    |

### realEstateController (포트 8682)

```bash
python -m uvicorn realEstateController:app --host=0.0.0.0 --port=8682 --reload
```

| 엔드포인트                          | 설명                                           |
| ----------------------------------- | ---------------------------------------------- |
| `GET /realestate/seoul-rtms`        | 실거래가 통합 (매매/전세/월세/오피스텔/상업용) |
| `GET /realestate/sangkwon`          | 행정동별 매출                                  |
| `GET /realestate/sangkwon-svc`      | 업종별 매출                                    |
| `GET /realestate/sangkwon-store`    | 점포수/개폐업률                                |
| `GET /realestate/sangkwon-quarters` | 수집 분기 목록                                 |
| `GET /realestate/search-dong`       | 행정동명 검색                                  |
| `GET /realestate/land-value`        | 공시지가                                       |

---

## 프론트엔드 실행

```bash
cd p02_frontEnd_React
npm install
npm run dev   # http://localhost:5173
```

### 주요 기능

- 서울 행정동 폴리곤 클릭 → 매출/점포수/실거래가 패널
- 소상공인 마커 반경검색 + 업종 필터 + 클릭 하이라이트
- 업종별 매출 막대차트 (SVC_CD 기준)
- 실거래가: 아파트/오피스텔/상업용 통합 (만원 단위 자동 포맷)
- 관광지·문화시설·축제 마커 (KTO DB + 실시간 API)
- 학교 마커 (카카오 좌표 변환 적재)
- 유동인구 히트맵 (38개 장소, 온도색 표현)
- 카카오 로드뷰 (버튼 ON → 지도 클릭)
- VWorld 레이어: 지적도, 관광안내소
- 행정동명 검색 (GeoJSON 1차 → DB LIKE fallback)

---

## 데이터 적재 순서 (초기 셋업)

```bash
cd p04_DataLoader

# 1. DB 테이블 생성 (DBeaver에서 SQL 실행)
#    p03_OracleDB_Script/ 폴더의 SQL 파일들

# 2. 매핑 데이터
python insert_law_adm.py
python insert_svc_induty_map.py

# 3. 소상공인
python load_store_csv.py

# 4. 상권 매출
python load_sangkwon_sales_csv.py --year=2024
python load_sangkwon_sales_csv.py --year=2025

# 5. 점포수
python load_sangkwon_store_csv.py --year=2024

# 6. 국토부 실거래가 (서울 25구)
cd collecter
python collect_molit_rtms.py --year=2024

# 7. 랜드마크 (1회, 상세 조회 생략)
python collect_landmark.py --no-detail

# 8. 학교 + 카카오 좌표 변환
python collect_school.py
```

---

## 환경변수 (.env)

```dotenv
# VWorld
VITE_VWORLD_API_KEY=BE3AF33A-202E-3D5F-A8AD-63D9EE291ABF

# 카카오
VITE_KAKAO_API_KEY=064e455e57b72a7665be2ff5515aead2
VITE_KAKAO_JS_KEY=4f588577d41ff38695f0daa513b5bef7

# 백엔드 URL
VITE_MAP_URL=http://10.1.92.119:8681
VITE_REALESTATE_URL=http://10.1.92.119:8682

# 서울 열린데이터광장
SEOUL_MOLIT_API_KEY=4a656f6b4c7773743331707150564f
SEOUL_POP_API_KEY=537a7a50717773743131306a49616d76
SEOUL_SCHOOL_API_KEY=6e626d744d777374373748684e7575
SEOUL_SANGKWON_API_KEY=754877586377737436326350494f4c

# 국토부 실거래가
MOLIT_OP_API_KEY=b7906dd729da8d6d4f67bd6bed484f032f9f586abc7b382b41b93a003949385e
MOLIT_NRG_API_KEY=b7906dd729da8d6d4f67bd6bed484f032f9f586abc7b382b41b93a003949385e

# 한국관광공사
KTO_GW_INFO_KEY=b7906dd729da8d6d4f67bd6bed484f032f9f586abc7b382b41b93a003949385e
```

---

## 메인앱 통합 방법 (frontend/)

### 1. 파일 복사

```
# src 전체 복사
p02_frontEnd_React/src/  →  frontend/src/pages/map/

# GeoJSON 복사
p02_frontEnd_React/public/seoul_adm_dong.geojson  →  frontend/public/seoul_adm_dong.geojson
```

> `index.html`, `vite.config.js`는 복사가 아니라 **기존 파일에 내용 병합**

---

### 2. index.html 병합

`frontend/index.html`의 `<head>` 안에 추가:

```html
<!-- 카카오맵 SDK (SOHOBI 지도용) -->
<script>
   window.ENV_KAKAO_JS_KEY = "%VITE_KAKAO_JS_KEY%";
</script>
```

> SOHOBI는 JS SDK를 `App.jsx`에서 동적 로드하므로 스크립트 태그 직접 삽입 불필요.  
> `window.ENV_KAKAO_JS_KEY` 설정만 추가하면 됨.

---

### 3. vite.config.js 병합

`frontend/vite.config.js`의 `proxy` 블록에 추가:

```js
// 기존 proxy에 아래 항목 추가
"/vworld": {
  target: "https://api.vworld.kr",
  changeOrigin: true,
  rewrite: (path) => path.replace(/^\/vworld/, ""),
},
"/wms": {
  target: "https://api.vworld.kr",
  changeOrigin: true,
  rewrite: (path) => path.replace(/^\/wms/, ""),
},
"/kakao": {
  target: "https://dapi.kakao.com",
  changeOrigin: true,
  rewrite: (path) => path.replace(/^\/kakao/, ""),
},
```

최종 `vite.config.js` 예시:

```js
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
   plugins: [react()],
   server: {
      proxy: {
         // 기존 메인앱 proxy
         "/api": {
            target: "http://localhost:8000",
            changeOrigin: true,
         },
         // SOHOBI 지도 proxy 추가
         "/vworld": {
            target: "https://api.vworld.kr",
            changeOrigin: true,
            rewrite: (path) => path.replace(/^\/vworld/, ""),
         },
         "/wms": {
            target: "https://api.vworld.kr",
            changeOrigin: true,
            rewrite: (path) => path.replace(/^\/wms/, ""),
         },
         "/kakao": {
            target: "https://dapi.kakao.com",
            changeOrigin: true,
            rewrite: (path) => path.replace(/^\/kakao/, ""),
         },
      },
   },
});
```

---

### 4. App.jsx 라우트 추가

`frontend/src/App.jsx`에 추가:

```jsx
import MapApp from "./pages/map/App"; // SOHOBI App.jsx

// 기존 Route 목록에 추가
<Route path="/map/*" element={<MapApp />} />;
```

---

### 5. .env 병합

`frontend/.env`에 SOHOBI 환경변수 추가:

```dotenv
VITE_KAKAO_JS_KEY=4f588577d41ff38695f0daa513b5bef7
VITE_KAKAO_API_KEY=064e455e57b72a7665be2ff5515aead2
VITE_VWORLD_API_KEY=BE3AF33A-202E-3D5F-A8AD-63D9EE291ABF
VITE_MAP_URL=http://10.1.92.119:8681
VITE_REALESTATE_URL=http://10.1.92.119:8682
```

---

### 6. package.json 의존성 확인

SOHOBI에서 사용하는 패키지가 메인앱에 없으면 추가:

```bash
cd frontend
npm install ol        # OpenLayers (지도)
npm install axios     # (사용 시)
```

---

### 통합 체크리스트

- [ ] `src/` → `frontend/src/pages/map/` 복사
- [ ] `public/seoul_adm_dong.geojson` → `frontend/public/` 복사
- [ ] `index.html` → `window.ENV_KAKAO_JS_KEY` 추가
- [ ] `vite.config.js` → proxy 4개 항목 추가
- [ ] `App.jsx` → `/map/*` 라우트 추가
- [ ] `.env` → SOHOBI 환경변수 추가
- [ ] `npm install ol` 확인

---

## PENDING

- [ ] 유동인구 250M 격자 생활인구 연동 (좌표 변환 + 히트맵)
- [ ] 오피스텔 전월세 API 승인 후 수집
- [ ] 25년 4분기 매출 수집
- [ ] Nginx 설치 및 프록시 설정
- [ ] 메인앱 통합 (frontend/ 폴더)
- [ ] vite.config.js 카카오 프록시 추가 (현재 500 오류)
- [ ] VWorld 타임아웃 원인 파악
