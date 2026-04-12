# 세션 인수인계 — 2026-04-06 (지도 마커 / 백엔드 성능)

## 브랜치
`PARK` → main (PR 진행 중)

---

## 이번 세션 완료 작업

### 지도 마커 버그 수정

| 파일 | 수정 내용 |
|------|-----------|
| `frontend/src/hooks/map/useLandmarkLayer.js` | `loadFestivals()`: `adm_cd` 없을 때 `?adm_cd=undefined` URL 버그 수정 |
| `frontend/src/components/map/MapView.jsx` | 지도 초기화 시 `loadFestivals()` 자동 호출 누락 수정 (축제 마커 초기 미출력 원인) |
| `frontend/src/components/map/panel/Layerpanel.jsx` | 지적도 TileLayer `minZoom: 17` 추가 + LayerRow 설명 업데이트 |

### KTO API 키 로컬 .env 추가 (커밋 제외)
- `integrated_PARK/.env`에 `KTO_GW_INFO_KEY` 추가 완료 (팀원 제공)
- **⚠️ Azure Container Apps 환경 변수에도 동일하게 추가 필요**
  - Azure Portal > sohobi-backend > 컨테이너 앱 > 환경 변수 > `KTO_GW_INFO_KEY` 추가

---

## 현재 지도 기능 상태

| 레이어 | 상태 | 비고 |
|--------|------|------|
| 관광지·문화시설 | ✅ 정상 | |
| 학교 | ✅ 정상 | |
| 관광안내소 (WMS) | ✅ 정상 | |
| 지적도 (WMS) | ✅ 수정됨 | zoom 17+ 에서만 표시 (VWorld 사양) |
| 축제 | ✅ 코드 수정됨 | Azure 환경변수 추가 후 프로덕션 정상 동작 예정 |
| 상가/점포/매출/부동산 | ✅ 정상 | 동 클릭 시 로드 |

---

## 미완료 — 다음 세션 인계: 백엔드 성능 이슈

아래 항목은 이번 세션에서 발굴했으나 미수정 상태.

### ① HIGH — `getDongCentroids` 순차 Kakao API 호출

**파일**: `integrated_PARK/map_data_router.py:481-504`
**문제**: dong_list를 순차 루프로 처리. 5개 동 요청 시 잠재적 50초 응답 지연.
**수정**: `asyncio.gather()`로 병렬화

```python
# 현재 (순차)
for dong in dong_list:
    result = await client.get(kakao_url, params=...)

# 목표 (병렬)
async def _fetch_one(client, dong):
    ...
results = await asyncio.gather(*[_fetch_one(client, d) for d in dong_list])
```

---

### ② HIGH — `get_logs` 전체 로드 + N+1 쿼리

**파일**: `integrated_PARK/api_server.py:587-605`
**문제**: `load_entries_json(limit=0)` → 전체 로그 메모리 로드 후, session/user별 개별 DB 쿼리 (N+1).
**수정**: limit 파라미터를 enrichment 이전에 적용, user_id 일괄 조회로 배치화.

---

### ③ MEDIUM — `searchDong` LIKE 풀스캔

**파일**: `integrated_PARK/db/dao/mapInfoDAO.py:132, 143`
**문제**: `WHERE adm_nm LIKE '%q%'` — 전체 테이블 스캔. 키 입력마다 실행.
**수정**:
- 가능하면 prefix LIKE: `LIKE 'q%'` 로 변경 (B-tree 인덱스 활용)
- `adm_nm`, `legal_nm` 컬럼에 B-tree 인덱스 추가
- 미드-스트링 검색 필요 시 PostgreSQL trigram index (`pg_trgm`) 사용

```sql
CREATE INDEX idx_dong_adm_nm ON dong_seoul (adm_nm text_pattern_ops);
CREATE INDEX idx_dong_legal_nm ON dong_seoul (legal_nm text_pattern_ops);
```

---

### ④ MEDIUM — VWorld/Kakao 외부 API 캐싱 없음

**파일**: `integrated_PARK/map_data_router.py:437-505`
**문제**: 동일 PNU/동 요청마다 외부 API 재호출. 레이트 제한 위험 + 불필요한 지연.
**수정**: TTL 캐시 적용 (Redis 또는 `functools.lru_cache` / `cachetools.TTLCache`)

```python
from cachetools import TTLCache
_land_cache = TTLCache(maxsize=1000, ttl=3600)  # 1시간 캐시

async def getLandUse(pnu: str):
    if pnu in _land_cache:
        return _land_cache[pnu]
    ...
    _land_cache[pnu] = result
    return result
```

---

### ⑤ MEDIUM — 오케스트레이터 재시도 시 전체 에이전트 재실행

**파일**: `integrated_PARK/orchestrator.py:85-150`
**문제**: signoff 실패 시 LLM + DB 전체 재실행 (최대 3회 × 풀 비용).
**수정**: 중간 결과 캐싱 + signoff 피드백 기반 부분 재생성.

---

## 작업 순서 권장

```
1. ③ searchDong 인덱스 추가 (마이그레이션 SQL 한 줄, 위험도 낮음)
2. ① getDongCentroids asyncio.gather 병렬화 (코드 10줄 수정)
3. ② get_logs N+1 개선
4. ④ 캐싱 레이어 추가
5. ⑤ 오케스트레이터 리팩터링 (범위 큼, 별도 세션 권장)
```
