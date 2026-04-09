# 보안 강화 작업 인수인계 — 2026-04-05

## 브랜치 / PR 현황

| 항목 | 상태 |
|------|------|
| 브랜치 | `PARK` |
| PR #55 | MERGED — `auth.py` 생성, CORS 화이트리스트, `/api/v1/*` 인증 적용 |
| PR #136 | MERGED — SWA 프록시 시도 (Free 티어 미지원으로 장애 유발) |
| PR #137 | MERGED — SWA 프록시 제거, 서비스 복구 |
| PARK 미머지 커밋 | `862681d feat: 인라인 피드백 위젯 구현 (계층 2)` — main 미반영 |

## 현재 프로덕션 보안 상태

| 조치 | 상태 | 비고 |
|------|------|------|
| CORS 화이트리스트 | ✅ 적용 | `sohobi.net`, `azurestaticapps.net`만 허용 |
| `/api/v1/*` API Key 인증 | ✅ 적용 | Container Apps `API_SECRET_KEY` 환경변수 활성화 |
| `VITE_API_KEY` 빌드 주입 | ✅ 적용 | GitHub Secret → Vite 빌드 번들에 포함 |
| SWA 보안 헤더 | ✅ 적용 | HSTS, X-Frame-Options, X-Content-Type-Options |
| `/map/*`, `/realestate/*`, `/api/feedback` 인증 | ❌ **미적용** | 완전 개방 상태 — 1순위 수정 필요 |
| `/map/load-csv` 경로 탐색 방어 | ❌ **미적용** | 서버 경로 노출 가능 — 2순위 |
| `logs/export` 헤더 인증 전환 | ❌ **미적용** | URL에 시크릿 노출 중 — 3순위 |
| Container Apps 인그레스 IP 제한 | ❌ **미적용** | Phase 5 미완 |
| SWA 역방향 프록시 (URL 은폐) | ❌ **보류** | SWA Free 티어 미지원 — Standard 업그레이드 시 재검토 |

---

## 다음 세션 즉시 수행 작업

### 1순위 — `include_router`에 API Key 인증 추가

**파일:** [integrated_PARK/api_server.py](../../integrated_PARK/api_server.py), 58~61행

**현재:**
```python
app.include_router(map_router)
app.include_router(map_data_router)
app.include_router(realestate_router)
app.include_router(feedback_router)
```

**수정 후:**
```python
app.include_router(map_router)
app.include_router(map_data_router,   dependencies=[Depends(verify_api_key)])
app.include_router(realestate_router, dependencies=[Depends(verify_api_key)])
app.include_router(feedback_router,   dependencies=[Depends(verify_api_key)])
```

> `map_router`는 빈 라우터이므로 그대로 유지해도 무방하나, 일관성을 위해 추가해도 됨.

**영향 받는 엔드포인트 (현재 무인증 개방 상태):**

`/map/*` (18개):
`/map/nearby`, `/map/stores-by-dong`, `/map/stores-by-building`, `/map/nearby-bbox`,
`/map/categories`, `/map/landmarks`, `/map/festivals`, `/map/schools`, `/map/sdot/sensors`,
`/map/dong-density`, `/map/csv-list`, `/map/load-csv`, `/map/load-all-csv`,
`/map/status`, `/map/reload-cache`, `/map/cache-status`, `/map/land-use`, `/map/dong-centroids`

`/realestate/*` (9개):
`/realestate/seoul-rtms`, `/realestate/sangkwon`, `/realestate/sangkwon-svc`,
`/realestate/sangkwon-svc-by-cat`, `/realestate/sangkwon-store`, `/realestate/sangkwon-induty`,
`/realestate/sangkwon-quarters`, `/realestate/search-dong`, `/realestate/land-value`

`/api/feedback` (1개): Cosmos DB에 임의 데이터 무제한 삽입 가능

**프론트엔드 영향:** `MapView.jsx`가 `VITE_MAP_URL`과 `VITE_REALESTATE_URL`로 이 엔드포인트들을 호출함.
현재 `MapView.jsx`는 `X-API-Key` 헤더를 전송하지 않으므로, 인증 추가 후 즉시 수정 필요.

**`MapView.jsx` 수정 필요 위치:** [frontend/src/components/map/MapView.jsx](../../frontend/src/components/map/MapView.jsx)

`fetch()` 직접 호출부에 헤더 추가:
```javascript
// 파일 상단에 추가
const _API_KEY = import.meta.env.VITE_API_KEY || "";
const _mapHeaders = _API_KEY ? { "X-API-Key": _API_KEY } : {};

// 모든 fetch() 호출을 아래 패턴으로 변경
fetch(`${FASTAPI_URL}/map/stores-by-dong?adm_cd=${admCd}`, { headers: _mapHeaders })
fetch(`${REALESTATE_URL}/realestate/sangkwon?...`, { headers: _mapHeaders })
```

`useLandmarkLayer.js`도 동일 처리 필요: [frontend/src/hooks/map/useLandmarkLayer.js](../../frontend/src/hooks/map/useLandmarkLayer.js)

**검증 (인증 적용 후):**
```bash
# 인증 없이 → 401
curl -s -o /dev/null -w "%{http_code}" \
  "<BACKEND_HOST>/map/stores-by-dong?adm_cd=1100000"

# 인증 포함 → 200
curl -s -o /dev/null -w "%{http_code}" \
  -H "X-API-Key: <API_SECRET_KEY>" \
  "<BACKEND_HOST>/map/stores-by-dong?adm_cd=1100000"
```

---

### 2순위 — `/map/load-csv` 경로 탐색 취약점 수정

**파일:** [integrated_PARK/map_data_router.py](../../integrated_PARK/map_data_router.py), 346~353행

**현재 코드 (취약):**
```python
@router.get("/map/load-csv")
def loadCSV(filename: str):
    filepath = os.path.join(CSV_DIR, filename)
    if not os.path.exists(filepath):
        return {"error": f"파일 없음: {filepath}"}   # ← 서버 절대경로 노출
```

**수정 후:**
```python
@router.get("/map/load-csv")
def loadCSV(filename: str):
    # 경로 탐색 방어: 정규화 후 CSV_DIR 내부인지 확인
    safe_dir = os.path.realpath(CSV_DIR)
    filepath  = os.path.realpath(os.path.join(CSV_DIR, filename))
    if not filepath.startswith(safe_dir + os.sep):
        return {"error": "잘못된 파일명"}
    if not os.path.exists(filepath):
        return {"error": "파일을 찾을 수 없습니다"}   # 경로 비공개
```

> `load-all-csv` 엔드포인트는 `os.listdir(CSV_DIR)`에서 `.csv` 확장자만 필터링하므로 별도 수정 불필요.

---

### 3순위 — `logs/export` 쿼리 파라미터 인증 → 헤더 인증 전환

**파일:** [integrated_PARK/api_server.py](../../integrated_PARK/api_server.py), 522행 부근

**현재:** `GET /api/v1/logs/export?key=SECRET` — URL에 시크릿 노출

**수정 후:**
```python
# 기존 key 파라미터 제거, verify_api_key 의존성 추가
@app.get("/api/v1/logs/export", dependencies=[Depends(verify_api_key)])
async def export_logs(
    type: str = Query("queries", description="queries | rejections | errors"),
):
    # key 파라미터 검증 로직 전부 제거 (verify_api_key가 처리)
    try:
        path = _get_log_path(type)
        ...
```

> `EXPORT_SECRET` 환경변수와 관련 검증 코드 삭제. `API_SECRET_KEY` 하나로 통합.
>
> 이 엔드포인트를 호출하는 코드(프론트엔드 또는 curl 스크립트)가 있다면 `?key=` 파라미터 제거하고 `-H "X-API-Key: ..."` 방식으로 변경 필요.

---

### Phase 5 (미완) — Container Apps 인그레스 IP 제한

```bash
# SWA Free 티어는 프록시 미지원이므로 SWA IP 화이트리스트 효과 없음.
# 대신 팀원 공인 IP + 개발 서버 IP만 등록하여 외부 무차별 접근 차단.

# 내 공인 IP 확인
curl -s ifconfig.me

# 각 IP 등록
az containerapp ingress access-restriction set \
  --name sohobi-backend \
  --resource-group <RESOURCE_GROUP> \
  --rule-name "allow-dev-PARK" \
  --ip-address <공인IP>/32 \
  --action Allow
```

> 팀원 각자 IP를 등록해야 하며, 동적 IP(WiFi 변경 등) 시 재등록 필요.
> 현재 API Key 인증이 1차 방어선이므로 Phase 5는 우선순위가 낮음.

---

## Azure 리소스 정보

| 리소스 | 이름 | 리소스 그룹 |
|--------|------|-------------|
| Container Apps | `sohobi-backend` | `<RESOURCE_GROUP>` |
| Static Web Apps | `sohobi-frontend` | `<RESOURCE_GROUP>` |
| Subscription | `<AZURE_SUBSCRIPTION_ID>` | — |

## 주요 환경변수 (Container Apps에 설정됨)

| 변수 | 상태 | 용도 |
|------|------|------|
| `API_SECRET_KEY` | ✅ 활성 | `/api/v1/*` 인증 |
| `CORS_EXTRA_ORIGINS` | ✅ 빈 값 | 추가 origin 없음 (운영 모드) |
| `ALLOWED_IPS` | ⬜ 미설정 | IP 필터 비활성 |
| `EXPORT_SECRET` | ⚠️ 구버전 | 3순위 조치 후 삭제 예정 |

## GitHub Secrets (현재 설정 값)

| Secret | 상태 |
|--------|------|
| `VITE_API_KEY` | ✅ 설정됨 (API_SECRET_KEY와 동일 값) |
| `VITE_MAP_URL` | ✅ Container Apps URL 복원됨 |
| `VITE_REALESTATE_URL` | ✅ Container Apps URL 복원됨 |

## 작업 순서 권장

1. **먼저 `MapView.jsx` 수정** (1순위 인증 추가 시 지도 기능 중단 방지)
2. `api_server.py` `include_router` 인증 추가
3. `map_data_router.py` 경로 탐색 수정
4. `api_server.py` `logs/export` 헤더 인증 전환
5. 커밋 → PARK 브랜치 push → PR → main 머지
6. 빌드 완료 확인 후 소크벌렸? 확인
