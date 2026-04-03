# SOHOBI 지도 기능 명세서

## 📁 파일 구조

```
frontend/src/
├── components/map/
│   ├── MapView.jsx              # 지도 메인 컴포넌트
│   ├── MapView.css              # 지도 스타일
│   ├── controls/
│   │   └── MapControls.jsx      # 하단 좌측 버튼 (점포수/매출/부동산/상가검색)
│   ├── panel/
│   │   ├── Layerpanel.jsx       # 레이어 관리 패널
│   │   ├── CategoryPanel.jsx    # 업종 필터 패널 (좌측)
│   │   └── DongPanel.jsx        # 행정동 분석 패널 (우측)
│   └── popup/
│       ├── StorePopup.jsx       # 상가 정보 팝업
│       ├── WmsPopup.jsx         # 지적도/공시지가 팝업
│       └── LandmarkPopup.jsx    # 랜드마크 정보 팝업
├── hooks/map/
│   ├── useMap.js                # 지도 초기화 (VWorld 기반)
│   ├── useMarkers.js            # 클러스터 마커 관리
│   ├── useDongLayer.js          # 행정동 폴리곤 레이어
│   ├── useLandmarkLayer.js      # 랜드마크 레이어 (관광/문화/축제/학교)
│   └── useWmsClick.js           # WMS 레이어 클릭 처리
└── constants/
    └── categories.js            # 업종 대분류 정의 (CAT_CD 기준)
```

---

## 🗺️ 지도 초기화

- **엔진**: VWorld WMTS (Base 타일)
- **초기 위치**: 서울 종로구 종로코아빌딩 (126.9784, 37.5713)
- **초기 줌**: 16
- **줌 범위**: 5 ~ 19
- **줌 레벨 표시**: OL 기본 +/- 버튼 사이에 현재 줌 숫자 표시

---

## 🏪 상가 클러스터 마커

### 동작 방식
- 행정동 폴리곤 클릭 → `/map/stores-by-dong?adm_cd=` API 호출
- 해당 행정동 전체 상가를 OpenLayers `Cluster` 소스로 렌더링
- 거리 임계값: `distance: 40`

### 스타일
| 상태 | 설명 |
|------|------|
| 기본 | 업종 대분류 색상 원형 마커 |
| 클러스터 | 원형 + 개수 텍스트 |
| 선택(하이라이트) | 크기 확대 + 색 반전 |

### 업종 대분류 색상 (`categories.js`)
| CAT_CD | 업종 | 색상 |
|--------|------|------|
| I2 | 음식 | #FF6B6B |
| G2 | 소매 | #FF9800 |
| S2 | 수리·개인 | #4ecdc4 |
| L1 | 부동산 | #2196F3 |
| I1 | 숙박 | #9C27B0 |
| P1 | 교육 | #F59E0B |
| Q1 | 의료 | #E03131 |
| R1 | 스포츠 | #2F9E44 |
| M1 | 전문·기술 | #1971C2 |
| N1 | 시설관리 | #607D8B |

### zIndex
- 원형 레이어: 220
- 클러스터 레이어: 221 (지적도 200보다 위)

---

## 🗾 행정동 폴리곤 레이어

### 데이터
- GeoJSON: `public/seoul_adm_dong.geojson`
- 컬럼: `adm_cd` (8자리), `adm_nm`, `gu_nm`

### 스타일
| 상태 | 색상 |
|------|------|
| 기본 | 투명 + 회색 테두리 |
| 호버 | 연한 파랑 |
| 선택 | 파랑 + 진한 테두리 |

### 클릭 동작
1. 폴리곤 클릭 → 해당 `adm_cd`로 상가 전체 조회
2. 같은 폴리곤 재클릭 → 기존 마커 재사용 (재조회 안 함)
3. 다른 폴리곤 클릭 → 마커 초기화 후 새로 조회
4. 점포수/매출/부동산 모드 활성 시 → 동 패널도 함께 표시

---

## 📊 동 분석 패널 (DongPanel)

### 진입 방법
하단 좌측 **점포수 / 매출 / 부동산** 버튼 활성화 후 폴리곤 클릭

### 모드별 기능
| 모드 | API | 내용 |
|------|-----|------|
| 점포수 | `/realestate/sangkwon-store` | 업종별 점포수, 개폐업률 |
| 매출 | `/realestate/sangkwon` | 업종별 매출, 성별/연령/시간대 분석 |
| 부동산 | `/realestate/seoul-rtms` | 실거래가 이력 |

### 버튼 동작
- 활성 버튼 재클릭 → `none` 모드 전환 + 패널 닫힘
- `none` 모드에서도 폴리곤 클릭 → 클러스터 표시 (패널 없음)

### CategoryPanel 연동
- CategoryPanel 업종 이름 클릭 → 해당 대분류(`CAT_CD`) 기준 소분류 매출 그래프 전환
- 재클릭 → 전체 대분류 기준 복원
- API: `/realestate/sangkwon-svc-by-cat?adm_cd=&cat_cd=`

---

## 🏷️ 상가 팝업 (StorePopup)

### 진입 방법
- 단일 마커 클릭
- 클러스터 목록 → 상가 선택

### 표시 정보
- 상호명, 중분류(MID_CAT_NM) 배지 (대분류 색상 기준)
- 도로명 주소, 층/호 정보
- 카카오맵 상세 정보 (비동기 조회)
- 같은 건물 상가 목록 (ROAD_ADDR 기준)
- 같은 상호명 다른 지점 목록

### 버튼
| 버튼 | 동작 |
|------|------|
| 카카오맵 → | 카카오맵 장소 페이지 외부 링크 |
| 🏷️ 공시지가 | WmsPopup으로 전환 (지적도 ON 시 PNU 자동 조회) |
| ← 뒤로가기 | 클러스터 목록으로 복귀 |

### 위치
- DongPanel 없을 때: 우측 하단 (`right: 16`)
- DongPanel 열렸을 때: 좌측 하단 (`left: 16`)

---

## 📋 지적도 / 공시지가 팝업 (WmsPopup)

### 진입 방법
1. 레이어 패널에서 **지적도** ON → 지도 클릭
2. StorePopup의 **🏷️ 공시지가** 버튼 클릭

### 표시 정보
- 주소, PNU, 지번, 용도지역
- 연도별 공시지가 이력 (최근 5년)

### 버튼
| 버튼 | 동작 |
|------|------|
| ← 뒤로가기 | StorePopup에서 진입한 경우만 표시, StorePopup으로 복귀 |
| ✕ 닫기 | 팝업 닫기 |

---

## 🏛️ 랜드마크 레이어 (useLandmarkLayer)

### 타입별 스타일
| 타입 | content_type_id | 색상 | 레이블 |
|------|----------------|------|--------|
| 관광지 | 12 | #f59e0b | 관광 |
| 문화시설 | 14 | #8b5cf6 | 문화 |
| 축제 | 15 | #ef4444 | 축제 |
| 학교 | school | #10b981 | 학교 |

### zIndex
- 관광지·문화: 210
- 축제: 211
- 학교: 212

### 가시성
- `minZoom: 12` → 줌 12 미만이면 자동 숨김

---

## 🗂️ 레이어 패널 (Layerpanel)

### 레이어 목록 및 기본값
| 레이어 | 기본값 | zIndex | 비고 |
|--------|--------|--------|------|
| 지적도 | **ON** | 200 | VWorld WMS |
| 관광안내소 | **ON** | 215 | VWorld WMS |
| 관광지·문화시설 | ON | 210 | KTO DB 마커 |
| 축제 | ON | 211 | 공공데이터 API |
| 학교 | ON | 212 | DB 마커 |

---

## 🔍 검색 기능 (CategoryPanel)

### 검색 범위
- **행정동명** (SANGKWON_SALES.adm_nm)
- **법정동명** (STORE_SEOUL.법정동명)

### 동작
1. 검색어 입력 → DB LIKE 검색 + GeoJSON 매칭
2. 단일 결과 → 폴리곤 자동 선택 + 클러스터 마커 표시
3. 복수 결과 → 모든 매칭 폴리곤 하이라이트 + 전체 범위로 지도 이동
4. 복수 결과 클러스터 → 모든 행정동 병렬 조회 후 합산 표시

---

## 🔄 팝업 상호 배타 규칙

- StorePopup / WmsPopup / LandmarkPopup / ClusterPopup 동시에 표시 불가
- 각 팝업 열 때 나머지 모두 닫힘
- 예외: StorePopup + DongPanel 동시 표시 가능 (위치 자동 조정)

---

## 🌐 API 엔드포인트 요약

### mapController (port 8681)
| 엔드포인트 | 설명 |
|-----------|------|
| `GET /map/stores-by-dong?adm_cd=` | 행정동 전체 상가 (제한 없음) |
| `GET /map/stores-by-building?road_addr=&store_nm=&exclude_id=` | 같은 건물 상가 + 동일 상호 다른 지점 |
| `GET /map/landmarks?types=12,14` | 관광지/문화시설 |
| `GET /map/schools` | 학교 목록 |
| `GET /map/land-use?pnu=` | 용도지역 조회 |

### realEstateController (port 8682)
| 엔드포인트 | 설명 |
|-----------|------|
| `GET /realestate/sangkwon?adm_cd=` | 매출 분석 |
| `GET /realestate/sangkwon-store?adm_cd=` | 점포수/개폐업률 |
| `GET /realestate/seoul-rtms?adm_cd=` | 실거래가 |
| `GET /realestate/sangkwon-svc-by-cat?adm_cd=&cat_cd=` | 대분류별 소분류 매출 |
| `GET /realestate/land-value?pnu=&years=5` | 공시지가 이력 |
| `GET /realestate/search-dong?q=` | 행정동/법정동 검색 |

---

## ⚠️ 알려진 이슈 및 TODO

- [ ] 같은 건물 상가 조회를 `ROAD_ADDR` → `BLDG_MGT_NO` 기준으로 전환 필요
- [ ] 랜드마크 마커 이미지 교체 예정 (`CircleStyle` → `Icon`)
- [ ] CategoryPanel-DongPanel 연동 최종 확인 필요
- [ ] Nginx 프록시 설정 필요 (운영 환경)
- [ ] `.env` GitHub Secrets 연동 필요