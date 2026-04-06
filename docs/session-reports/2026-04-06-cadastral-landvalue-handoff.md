# 세션 인수인계 — 2026-04-06 (지적도·공시지가 미작동 분석)

## 브랜치
`PARK` → PR #165 (지적도 STYLES 버그 수정, main 머지 대기)

---

## 이번 세션 완료 작업

| 파일 | 수정 내용 |
|------|-----------|
| `frontend/src/components/map/panel/Layerpanel.jsx` | `makeWmsLayer` STYLES `""` 수정, `makeCadastralLayer` 팩토리 추출 (STYLES `","`), zoom indicator |
| `frontend/src/hooks/map/useWmsClick.js` | `CADASTRAL_MIN_ZOOM=17` zoom guard 삽입 |
| `frontend/src/components/map/MapView.jsx` | `currentZoom` prop 전달 |

---

## 미완료 — 공시지가 미작동 원인 분석 결과

### 분석 요약

직접 테스트(curl)로 확인한 사실:

```bash
# lp_pa_cbnd_bubun GetFeatureInfo → jiga 정상 반환
curl "https://api.vworld.kr/req/wms?KEY=BE3AF33A-...&SERVICE=WMS&VERSION=1.3.0
     &REQUEST=GetFeatureInfo&LAYERS=lp_pa_cbnd_bubun,lp_pa_cbnd_bonbun
     &QUERY_LAYERS=lp_pa_cbnd_bubun,lp_pa_cbnd_bonbun&STYLES=,
     &INFO_FORMAT=application/json..."

# 응답 properties:
{
  "pnu": "1120011500108430000",
  "jiga": "8578000",         ← 공시지가 있음
  "gosi_year": "2025",
  "gosi_month": "01",
  "addr": "서울특별시 성동구 성수동2가 843"
}
```

VWorld WMS GetFeatureInfo는 `jiga`, `gosi_year`를 정상 반환한다. 단, STYLES가 잘못된 구버전 코드에서도 GetFeatureInfo 응답은 동일함(STYLES는 GetFeatureInfo에 무관).

---

### 근본 원인 3가지

#### 원인 1 (HIGH) — 프로덕션 환경의 `/wms` 프록시 부재

**위치:** `frontend/public/staticwebapp.config.json`

```json
// 현재: /wms/* 프록시 규칙 없음
{
  "navigationFallback": { "rewrite": "/index.html", ... }
}
```

`/wms/req/wms?...` 요청이 로컬 dev에서는 Vite 프록시(`vite.config.js:38`)를 통해 VWorld로 전달되지만, Azure SWA 프로덕션에는 동일한 프록시 규칙이 없다. SWA는 `/wms/*` 경로에 대해 404 또는 `index.html`을 반환한다.

결과:
- WMS 타일(GetMap): 브라우저가 `<img src="/wms/req/wms?...REQUEST=GetMap">` → SWA 404 → 타일 표시 안됨
- WMS GetFeatureInfo: `fetch("/wms/req/wms?...REQUEST=GetFeatureInfo")` → SWA 404/HTML → `JSON.parse` 실패 → `feat=null` → `landValue=null`

**수정 방향:**

Option A — `staticwebapp.config.json`에 백엔드 프록시 추가 (백엔드가 `/wms` 프록시 역할)
```json
{
  "routes": [
    {
      "route": "/wms/*",
      "rewrite": "https://api.vworld.kr/*"
    }
  ]
}
```
단, Azure SWA는 외부 URL로의 직접 rewrite를 지원하지 않음 → 백엔드(FastAPI)에 `/wms` 프록시 엔드포인트 추가 후 SWA에서 백엔드로 라우팅해야 함.

Option B — 백엔드(FastAPI)에 VWorld WMS 프록시 엔드포인트 추가
```python
# integrated_PARK/api_server.py
import httpx

@app.get("/wms/{path:path}")
async def vworld_wms_proxy(path: str, request: Request):
    url = f"https://api.vworld.kr/{path}"
    params = dict(request.query_params)
    async with httpx.AsyncClient() as client:
        r = await client.get(url, params=params)
    return Response(content=r.content, media_type=r.headers.get("content-type"))
```

그 후 SWA config에서 `/wms/*` → 백엔드 Container Apps URL로 라우팅.

---

#### 원인 2 (MEDIUM) — zoom guard가 building-popup→공시지가 flow를 차단

**위치:** `frontend/src/hooks/map/useWmsClick.js:127-129` (이번 세션에서 추가됨)

```javascript
// 현재 코드 (PR #165에 포함)
if (wmsLayer.get("name") === "cadastral") {
   if ((map.getView().getZoom() ?? 0) < CADASTRAL_MIN_ZOOM) continue;  // ← 문제
}
```

**문제 상황:**

MapView.jsx:1098-1104의 "건물 마커 클릭 → 공시지가 표시" 흐름:
```javascript
// MapView.jsx:1098 — 현재 줌이 17 미만이면 zoom guard에 의해 cadastral 스킵
handleWmsClick(map, coord).then((result) => {
   if (result) {
      setWmsPopup(result.parsed);
      setLandValue(result.landValue || null);
   }
});
```

건물 마커 클릭은 줌 레벨에 무관하게 발생한다. zoom 14에서 건물을 클릭하면 `handleWmsClick`이 호출되지만 zoom guard가 cadastral 레이어를 스킵 → `result=null` → landValue 미설정.

VWorld GetFeatureInfo는 ZOOM과 무관하게 좌표 기반으로 필지 데이터를 반환하므로(테스트 확인), zoom guard가 이 흐름을 막을 이유가 없다.

**수정 방향:**
- zoom guard를 "직접 지도 클릭" 이벤트에서만 적용
- "프로그래매틱 호출"(건물 마커 → 좌표 조회)에는 zoom guard 미적용
- `handleWmsClick` 함수 시그니처에 `{ skipZoomGuard: boolean }` 옵션 파라미터 추가

```javascript
// useWmsClick.js
export async function handleWmsClick(map, coordinate, { skipZoomGuard = false } = {}) {
   ...
   if (!skipZoomGuard && wmsLayer.get("name") === "cadastral") {
      if ((map.getView().getZoom() ?? 0) < CADASTRAL_MIN_ZOOM) continue;
   }
   ...
}
```

MapView.jsx:1099에서 건물 마커 흐름은 `skipZoomGuard: true`로 호출:
```javascript
handleWmsClick(map, coord, { skipZoomGuard: true }).then(...);
```

---

#### 원인 3 (LOW) — `lp_pa_cbnd_bonbun` 레이어의 jiga 필드 없음

`lp_pa_cbnd_bonbun` GetFeatureInfo 응답에는 jiga/gosi_year 필드가 없음(테스트 확인):
```
'col_adm_se': '11200'
'bonbun': '843'
```

현재 QUERY_LAYERS 순서(`bubun,bonbun`)에서는 bubun이 우선 반환되어 jiga가 포함되지만, 특정 좌표 클릭 시 bonbun이 먼저 반환될 경우 jiga 없는 응답이 나올 가능성 있음.

**수정 방향:**
- LAYERS/QUERY_LAYERS에서 bonbun 제거하고 bubun만 사용 (공시지가·PNU 모두 bubun에 있음)
- 또는 `feat.id`가 `lp_pa_cbnd_bubun.*`인 경우만 jiga 파싱

---

### 관련 파일

```
frontend/
├── src/
│   ├── components/map/
│   │   ├── MapView.jsx (line 1098-1104: building popup→공시지가 흐름)
│   │   └── panel/Layerpanel.jsx (지적도 레이어 정의)
│   └── hooks/map/
│       └── useWmsClick.js (line 127-129: zoom guard)
├── public/staticwebapp.config.json (프록시 룰 부재)
└── vite.config.js (line 38-42: 개발 전용 /wms 프록시)

integrated_PARK/
├── api_server.py (VWorld 프록시 엔드포인트 추가 대상)
└── db/dao/landValueDAO.py (PNU 기반 공시지가 조회 — 이미 구현됨)
```

---

## 작업 우선순위

```
1. 원인 1 (프로덕션 /wms 프록시) — FastAPI에 /wms 프록시 추가 + SWA config 라우팅
2. 원인 2 (zoom guard 범위 축소) — skipZoomGuard 옵션 파라미터 추가
3. 원인 3 (bonbun 레이어 제거) — LAYERS를 bubun 단독으로 변경
```

원인 1이 프로덕션 환경의 근본 원인. 원인 2는 이번 세션 zoom guard가 도입한 회귀.
