# 플랜: 지도 마커 미출력 — Uvicorn 단일 워커 블로킹 수정

## Context

PR#120에서 CORS + Proxy 수정 완료. 그러나 sohobi.net 프로덕션에서 여전히 마커가 미출력됨.
Azure 컨테이너 로그 확인 결과: 앱 시작(04:28:20 UTC) 후 요청 1건(04:28:43 POST /api/v1/stream)만 처리되고 이후 무응답.
`/map/landmarks` → HTTP 504, `/map/schools` → HTTP 504.

## 진짜 원인 (프로덕션)

`useLandmarkLayer.js`는 지도 마운트 시 두 요청을 동시 발사:
```js
fetch("/map/landmarks?types=12,14")   // → get_all() — 서울 전체 full table scan
fetch("/map/schools")                  // → get_schools() — 서울 전체 full table scan
```

두 쿼리 모두 geographic filter 없이 ORDER BY → **느린 full scan** → uvicorn 단일 워커 점유 → 후속 모든 요청이 큐에서 대기 → 30초 후 Azure 504.

**Dockerfile 확인**:
```dockerfile
CMD ["sh", "-c", "uvicorn api_server:app --host 0.0.0.0 --port ${PORT:-8000} --workers ${UVICORN_WORKERS:-1}"]
```
`UVICORN_WORKERS` 환경변수 미설정 → 워커 1개.

## 수정 계획

### Fix 1 (즉시 효과, 코드 변경 없음): Azure 환경변수 설정

```bash
az containerapp update \
  --name sohobi-backend \
  --resource-group rg-ejp-9638 \
  --set-env-vars UVICORN_WORKERS=4
```

효과: 워커 4개 → 느린 쿼리 1개가 워커 하나를 점유해도 나머지 3개로 `/map/stores-by-dong` 처리 가능.

단점: 메모리 사용량 4배 증가. Azure Container Apps 기본 0.5Gi → 필요시 상향.

### Fix 2 (근본적): landmark/school endpoint에 LIMIT 추가

**`integrated_PARK/map_data_router.py` (line 185)**:
```python
# Before
result = lmDAO.get_all(type_list)

# After — 최대 500건으로 제한 (전체 서울 표시 불필요, 뷰포트 기반으로 전환 권장)
result = lmDAO.get_all(type_list, limit=500)
```

**`integrated_PARK/db/dao/landmarkDAO.py` `get_all()` (line 76-103)**:
```python
def get_all(self, content_types: list = None, limit: int = 500) -> list:
    ...
    sql = f"""
        {SELECT_LANDMARK}
        FROM landmark
        WHERE content_type_id IN ({placeholders})
        ORDER BY content_type_id, title
        LIMIT %(limit)s
    """
    params[...]["limit"] = limit
```

**`integrated_PARK/map_data_router.py` `getSchools()` (line 261)**:
```python
# Before
result = lmDAO.get_schools(school_type or None)

# After
result = lmDAO.get_schools(school_type or None, limit=500)
```

**`integrated_PARK/db/dao/landmarkDAO.py` `get_schools()` (line 105-156)**:
```python
def get_schools(self, school_type: str = None, limit: int = 500) -> list:
    ...
    sql += " LIMIT %(limit)s"
    params["limit"] = limit
```

## 수정 파일

| 파일 | 변경 내용 |
| --- | --- |
| Azure 환경변수 (az CLI) | `UVICORN_WORKERS=4` 추가 |
| `integrated_PARK/db/dao/landmarkDAO.py` | `get_all()`, `get_schools()` — `limit` 파라미터 추가 |
| `integrated_PARK/map_data_router.py` | `getLandmarks()`, `getSchools()` — `limit=500` 전달 |

## 검증

1. `az containerapp update ... --set-env-vars UVICORN_WORKERS=4` 실행
2. 1분 후 sohobi.net 접속
3. 브라우저 DevTools Network 탭: `/map/landmarks` → 200, `/map/schools` → 200 확인
4. 동 폴리곤 클릭 → `/map/stores-by-dong` → 200, 마커 클러스터 출력 확인
5. Azure 로그 확인: 여러 요청이 순차 처리되는지 확인
