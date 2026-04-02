# 지도 "데이터 없음" 수정

**날짜:** 2026-04-02  
**브랜치:** PARK

## 근본 원인

`MapView.jsx`는 두 개의 별도 API 서버를 참조:
- `VITE_MAP_URL` → TERRY `mapController.py` (포트 8681)
- `VITE_REALESTATE_URL` → TERRY `realEstateController.py` (포트 8682)

이 서버들은 Azure에 배포된 적 없음. `frontend/.env.production`에 해당 변수 없음 → 프론트엔드가 `localhost:8681` / 빈 URL 호출 → 404 → `apiData = null` → "데이터 없음".

TERRY DAOs는 사내 Oracle DB(`10.1.92.119:1521`)를 사용하므로 Azure에서 접근 불가.

## 수정 내용

### 1. `integrated_PARK/map_router.py` (신규)
FastAPI `APIRouter`로 모든 지도 API 엔드포인트 구현.  
기존 Azure PostgreSQL(`sangkwon_sales`, `sangkwon_store`)에서 데이터 조회.  
`CommercialRepository` connection pool 재사용.

구현된 엔드포인트:
- `GET /realestate/sangkwon` — 행정동 전체 매출 합산 + 분기 평균
- `GET /realestate/sangkwon-quarters` — 이용 가능한 분기 목록
- `GET /realestate/search-dong` — 행정동명 검색
- `GET /realestate/sangkwon-svc` — 업종별 매출 (소분류 기준)
- `GET /realestate/sangkwon-svc-by-cat` — 대분류 필터 업종 매출
- `GET /realestate/sangkwon-store` — 업종별 점포수·개폐업률
- `GET /realestate/seoul-rtms` — 실거래가 (Oracle 매핑 미지원 → 빈 응답)
- `GET /map/stores-by-dong` — 상가 목록 (STORE_SEOUL 미지원 → 빈 응답)
- `GET /map/nearby` — 반경 검색 (STORE_SEOUL 미지원 → 빈 응답)
- `GET /map/stores-by-building` — 건물 내 상가 (STORE_SEOUL 미지원 → 빈 응답)

### 2. `integrated_PARK/api_server.py`
```python
from map_router import router as map_router
app.include_router(map_router)
```

### 3. `frontend/.env.production`
`VITE_MAP_URL`, `VITE_REALESTATE_URL`을 Azure API URL과 동일하게 설정.

## 한계

- `/realestate/sangkwon-svc`는 소분류(`svc_induty_cd`) 기준으로 반환 (Oracle `SVC_INDUTY_MAP` 대분류 그루핑 미지원)
- `/realestate/seoul-rtms` 실거래가 빈 응답 (Oracle `LAW_ADM_MAP` 매핑 미지원)
- `/map/stores-by-dong` 빈 응답 (Oracle `STORE_SEOUL` 테이블 미지원)

## 검증 결과

로컬 테스트 (역삼1동 `adm_cd=11680640`):
```
GET /realestate/sangkwon-quarters  → 28개 분기 (2019Q1 ~ 2025Q4)
GET /realestate/sangkwon           → 매출 5,193억 / 평균 4,943억 ✅
GET /realestate/sangkwon-store     → 99개 업종 점포 데이터 ✅
GET /realestate/search-dong?q=역삼  → 역삼1동·역삼2동 ✅
GET /realestate/sangkwon-svc       → 57개 업종 매출 ✅
```

## Azure 배포 후 추가 작업

Azure Container Apps 빌드 환경변수 확인:
- `VITE_MAP_URL` = Azure API URL
- `VITE_REALESTATE_URL` = Azure API URL
