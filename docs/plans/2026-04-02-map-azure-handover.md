# 지도 파트 Azure 연결 — 담당자 인수인계 문서

**작성일:** 2026-04-02  
**대상:** 지도 파트 담당자 (WOO/TERRY)  
**목적:** 지도 기능이 Azure 프로덕션에서 동작하기 위해 필요한 작업 목록 정리

---

## 1. 현재 적용 완료된 사항

### GitHub Actions 워크플로우 (`.github/workflows/azure-static-web-apps-delightful-rock-0de6c000f.yml`)

아래 환경변수가 Azure Static Web Apps 빌드 시 자동 주입되도록 설정됨:

```yaml
env:
  VITE_KAKAO_JS_KEY: 4f588577d41ff38695f0daa513b5bef7
  VITE_KAKAO_API_KEY: 064e455e57b72a7665be2ff5515aead2
  VITE_VWORLD_API_KEY: BE3AF33A-202E-3D5F-A8AD-63D9EE291ABF
  VITE_MAP_URL: ${{ secrets.VITE_MAP_URL }}
  VITE_REALESTATE_URL: ${{ secrets.VITE_REALESTATE_URL }}
```

### 로컬 개발 (`frontend/.env.local`)

지도 관련 환경변수 5개 추가 완료. 로컬에서 `npm run dev` 시 8681/8682 포트 서버와 정상 연결됨.

---

## 2. GitHub Secrets 등록 필요 (백엔드 Azure 배포 후)

아래 두 값은 현재 GitHub Secrets에 **미등록** 상태. 지도 백엔드가 Azure Container App에 배포된 후 등록해야 프로덕션에서 지도 데이터가 표시됨.

| Secret 이름 | 등록할 값 |
| --- | --- |
| `VITE_MAP_URL` | `https://<지도백엔드>.koreacentral.azurecontainerapps.io` |
| `VITE_REALESTATE_URL` | `https://<부동산백엔드>.koreacentral.azurecontainerapps.io` |

**등록 경로:** GitHub 저장소 → Settings → Secrets and variables → Actions → New repository secret

---

## 3. 프론트엔드 코드 수정 필요 사항

아래 3건은 현재 버그 또는 Azure 배포 시 문제를 일으키는 사항. 담당자가 직접 수정 필요.

### 3-1. `useRealEstate.js` 하드코딩 제거

**파일:** `frontend/src/hooks/map/useRealEstate.js:6`

```javascript
// 현재 (버그 — 환경변수 무시됨)
const REALESTATE_URL = "http://localhost:8682";

// 수정 후
const REALESTATE_URL = import.meta.env.VITE_REALESTATE_URL || "http://localhost:8682";
```

### 3-2. VWorld WMS DOMAIN 동적화

**파일:** `frontend/src/components/map/Layerpanel.jsx` (DOMAIN=localhost 사용 위치 전체)

Azure Static Web Apps 도메인에서는 VWorld가 `DOMAIN=localhost`를 거부함.

```javascript
// 현재 (Azure 배포 시 WMS 레이어 동작 안 함)
url: `/wms/req/wms?KEY=${vworldKey}&DOMAIN=localhost`

// 수정 후
const currentDomain = window.location.hostname;
url: `/wms/req/wms?KEY=${vworldKey}&DOMAIN=${currentDomain}`
```

> **추가 조치:** VWorld API 계정에서 Azure SWA 도메인(`delightful-rock-0de6c000f.azurestaticapps.net`)을 허용 도메인으로 등록해야 함.

### 3-3. Kakao Maps JS SDK 동적 로드 추가

**파일:** `frontend/src/components/map/MapView.jsx` 또는 전용 훅

현재 `index.html`에 Kakao Maps SDK 스크립트 태그가 없어 `RoadviewPanel.jsx`에서 `window.kakao.maps`가 undefined 오류 발생.

```javascript
// MapView.jsx 최상단 useEffect 추가 (또는 별도 useKakaoSdk 훅으로 분리)
useEffect(() => {
  if (window.kakao?.maps) return; // 이미 로드된 경우 skip
  const script = document.createElement('script');
  script.src = `https://dapi.kakao.com/v2/maps/sdk.js?appkey=${
    import.meta.env.VITE_KAKAO_JS_KEY
  }&libraries=services,clusterer`;
  script.async = true;
  document.head.appendChild(script);
}, []);
```

> **추가 조치:** Kakao Developers 콘솔에서 JavaScript 앱 키 설정의 허용 도메인에 Azure SWA 도메인 추가 필요.

---

## 4. 백엔드 Azure 배포 경로

### 선행 조건

- [ ] TERRY 지도 백엔드(mapController.py, realEstateController.py)의 Oracle DB 의존성을 Azure PostgreSQL로 교체
- `TERRY/p01_backEnd/DAO/fable/oracleDBConnect.py` → PostgreSQL 드라이버(`asyncpg` 또는 `psycopg2`)로 교체
- Oracle 전용 SQL 문법 → PostgreSQL 문법으로 변경 (`ROWNUM` → `LIMIT`, `SYSDATE` → `CURRENT_DATE` 등)

### 배포 순서

1. `TERRY/p01_backEnd/` 에 `Dockerfile` 작성 (mapController / realEstateController 각각 또는 단일)
2. Azure Container Registry에 이미지 빌드 & 푸시
3. Azure Container App 생성 (지도용 8681, 부동산용 8682)
4. Container App 외부 URL 확보 후 GitHub Secrets(`VITE_MAP_URL`, `VITE_REALESTATE_URL`) 등록
5. `main` 브랜치 push → GitHub Actions 자동 빌드 → 프로덕션 반영 확인

### 이전 작업에 참고할 파일

- `integrated_PARK/Dockerfile` — 메인 백엔드 컨테이너화 참고
- `.github/workflows/deploy-backend.yml` — Azure Container App CD 파이프라인 참고
- `integrated_PARK/.env` — PostgreSQL 연결 정보 참고 (`DB_HOST`, `DB_PORT` 등)

---

## 5. 현재 아키텍처 요약

```
[Azure Static Web Apps]
  └─ /map 라우트 → MapView.jsx
       ├─ VITE_MAP_URL ──────────────→ [미배포] mapController.py (8681)
       │                                └─ Oracle DB (10.1.92.119) ← Azure 도달 불가
       ├─ VITE_REALESTATE_URL ───────→ [미배포] realEstateController.py (8682)
       │                                └─ Oracle DB (동일)
       ├─ Kakao REST API ────────────→ dapi.kakao.com (vite proxy 경유, SWA에서는 직접 호출)
       ├─ VWorld WMS ────────────────→ api.vworld.kr (DOMAIN=localhost 문제 있음)
       └─ VWorld WMTS (타일) ─────────→ api.vworld.kr (환경변수 정상 주입됨)
```
