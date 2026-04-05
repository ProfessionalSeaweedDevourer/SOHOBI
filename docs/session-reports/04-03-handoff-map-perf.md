# 세션 인수인계 — 2026-04-03 (지도 성능 & 백엔드 다운 수정)

## 브랜치
- 작업 브랜치: `PARK`
- 베이스: `main`

---

## 이번 세션에서 한 일

### 1. 백엔드 다운 원인 조사
- Azure Container App `sohobi-backend` (revision `--0000078`) 가 `04:28 UTC` 이후 무응답 상태
- TLS 연결은 성립되나 HTTP 응답 미반환 → event loop 블로킹 패턴 확인
- 로컬 import 테스트, Azure 로그 확인, 리비전 상태 확인으로 코드 원인 특정

### 2. 수정 완료 — PR #122 (오픈, 미머지)
**파일:** `integrated_PARK/realestate_router.py`, `integrated_PARK/map_data_router.py`

**문제:** `async def` 핸들러 내에서 동기 psycopg2 직접 호출 → uvicorn event loop 전체 블로킹  
**수정 내용:**
- `realestate_router.py` 7개 핸들러: `async def` → `def` (FastAPI thread pool 자동 실행)
- `getSeoulRtms`: async DAO + sync DAO 혼재 → `asyncio.gather + asyncio.to_thread` 병렬화
- `map_data_router.py` `getDongDensity`: `async def` → `def`

### 3. 성능 부하 전수 조사 완료 (수정 미완료)
아래 [P1]~[P6] 항목 참조

---

## 다음 세션에서 할 일 (우선순위 순)

### [P1] 백엔드 — `getStoresByAdmCd` LIMIT 없음
**파일:** `integrated_PARK/db/dao/mapInfoDAO.py:81`

현재 LIMIT 없이 전 행 반환. 명동·홍대 등 밀집 동은 3000~5000건 반환 가능.

```python
# 현재
WHERE adm_cd = %(adm_cd)s
  AND lng IS NOT NULL AND lat IS NOT NULL

# 수정: LIMIT 1500 추가
WHERE adm_cd = %(adm_cd)s
  AND lng IS NOT NULL AND lat IS NOT NULL
LIMIT 1500
```

---

### [P2] 프론트엔드 — `sales` 모드 폴리곤 클릭 시 `stores-by-dong` 이중 요청
**파일:** `frontend/src/components/map/MapView.jsx`

- `L756`: 동 클릭 시 `stores-by-dong` 1차 fetch
- `L799`: `sales` 모드 분기 내 동일 `stores-by-dong` 2차 fetch (`limit=9999`)

동일 adm_cd에 대해 같은 쿼리 2번 발사. 두 번째 fetch(L799) 제거하고 첫 번째 결과 재사용.

---

### [P3] 프론트엔드 — 검색 핸들러 레이스 컨디션
**파일:** `frontend/src/components/map/MapView.jsx:L283~412`

`handleSearch` 내에서:
1. `L343-362`: `stores-by-dong` 병렬 → `allStoresRef` 쓰기 + `drawMarkers`
2. `L388-412`: 마커 clear 후 `nearby` 반경 검색 → `allStoresRef` 덮어씌우기

두 요청의 완료 순서에 따라 표시 결과가 달라지는 race condition. 검색 시 `nearby`는 불필요하므로 `L388-412` 블록 전체 삭제.

---

### [P4] 프론트엔드 — `pointermove` throttle 미적용
**파일:** `frontend/src/components/map/MapView.jsx:L552`

마우스 이동마다 서울 전체 동 폴리곤 레이어 hit-test 실행. 50ms throttle 추가:

```js
let _lastMove = 0;
const moveHandler = (e) => {
  if (Date.now() - _lastMove < 50) return;
  _lastMove = Date.now();
  // 기존 로직
};
```

---

### [P5] 백엔드 — `store_seoul` 테이블 인덱스 확인 (조사 필요)
`getNearbyStores`는 `lat/lng BETWEEN` 쿼리. 복합 인덱스 없으면 full scan.

```sql
-- PostgreSQL에서 확인
SELECT indexname FROM pg_indexes WHERE tablename = 'store_seoul';
-- 없으면
CREATE INDEX idx_store_lat_lng ON store_seoul(lat, lng);
```

---

### [P6] 프론트엔드 — `drawMarkers` 전체 레이어 재생성 최적화
**파일:** `frontend/src/hooks/map/useMarkers.js:L87`

매 호출마다 OL Layer 삭제 후 재생성. `VectorSource.clear() + addFeatures()`로 소스만 교체하는 방식으로 최적화.  
복잡도가 있어 [P1]~[P4] 완료 후 진행 권장.

---

## PR 상태

| PR | 제목 | 상태 |
|----|------|------|
| #122 | fix: realestate_router async def → def, event loop 블로킹 수정 | **오픈 (머지 필요)** |

---

## 참고: Azure 배포 정보
- Container App: `sohobi-backend` / resource group: `rg-ejp-9638`
- 배포 자동화 없음 (GitHub Actions는 프론트엔드만)
- 환경변수 `PG_HOST`, `PG_DB`, `PG_USER`, `PG_PASSWORD`, `VWORLD_API_KEY`, `KAKAO_REST_KEY` 모두 설정됨

---

## 다음 세션 시작 방법
1. 이 파일 읽기
2. `gh pr view 122` — PR #122 머지 여부 확인
3. [P1] `integrated_PARK/db/dao/mapInfoDAO.py:81` LIMIT 추가부터 시작
4. 수정 후 `.venv/bin/python3 -c "import api_server; print('OK')"` import 검증
