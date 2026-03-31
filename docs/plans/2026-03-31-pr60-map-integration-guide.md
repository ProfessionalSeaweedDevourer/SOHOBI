# PR #60 지도 기능 통합 가이드 — frontend/ 작업 지시서

**작성일:** 2026-03-31
**대상:** 인터랙티브 지도 담당 팀원 (WOO)
**목적:** PR #60에서 추가된 기능들을 TERRY 개인 폴더가 아닌 `frontend/` 통합 폴더에서 작업하도록 전환

---

## 배경

현재 지도 관련 코드는 두 곳에 나뉘어 있다:

| 위치 | 설명 |
|------|------|
| `TERRY/p02_frontEnd_React/` | WOO 팀원 개인 개발 폴더 (독립 React 앱) |
| `frontend/src/components/map/` | 팀 전체 통합 프론트엔드 (실제 배포 앱) |

PR #60이 `TERRY/` 폴더에 새 기능들을 추가했지만, 이 내용은 **통합 `frontend/`에 아직 반영되지 않았다.** 앞으로는 `frontend/`에서 직접 작업한다.

---

## 1부: TERRY → frontend/ 파일 매핑

TERRY의 각 파일이 `frontend/` 어디에 해당하는지 전체 매핑이다.

### 1.1 컴포넌트

| TERRY 경로 (`p02_frontEnd_React/src/`) | `frontend/src/` 경로 | 현재 상태 |
|---|---|---|
| `components/MapView.jsx` | `components/map/MapView.jsx` | ✅ 존재 — 수정 필요 |
| `components/ChatPanel.jsx` | `components/map/ChatPanel.jsx` | ✅ 존재 — 동일 |
| `components/controls/MapControls.jsx` | `components/map/controls/MapControls.jsx` | ✅ 존재 — 수정 필요 |
| `components/controls/DongTooltip.jsx` | `components/map/controls/DongTooltip.jsx` | ✅ 존재 — 동일 |
| `components/panel/CategoryPanel.jsx` | `components/map/panel/CategoryPanel.jsx` | ✅ 존재 — 동일 |
| `components/panel/DongPanel.jsx` | `components/map/panel/DongPanel.jsx` | ✅ 존재 — 동일 |
| `components/panel/Layerpanel.jsx` | `components/map/panel/Layerpanel.jsx` | ✅ 존재 — 동일 |
| `components/panel/PopulationPanel.jsx` | `components/map/panel/PopulationPanel.jsx` | ❌ **없음 — 새로 생성 필요** |
| `components/panel/RoadviewPanel.jsx` | `components/map/panel/RoadviewPanel.jsx` | ❌ **없음 — 새로 생성 필요** |
| `components/popup/StorePopup.jsx` | `components/map/popup/StorePopup.jsx` | ✅ 존재 — 동일 |
| `components/popup/WmsPopup.jsx` | `components/map/popup/WmsPopup.jsx` | ✅ 존재 — 동일 |
| *(WOO 로컬)* `components/popup/LandmarkPopup.jsx` | `components/map/popup/LandmarkPopup.jsx` | ❌ **없음 — WOO가 직접 추가** |

### 1.2 훅 (Hooks)

| TERRY 경로 (`p02_frontEnd_React/src/hooks/`) | `frontend/src/hooks/map/` | 현재 상태 |
|---|---|---|
| `useDongLayer.js` | `useDongLayer.js` | ✅ 존재 |
| `useMap.js` | `useMap.js` | ✅ 존재 |
| `useMarkers.js` | `useMarkers.js` | ✅ 존재 |
| `useWmsClick.js` | `useWmsClick.js` | ✅ 존재 |
| *(WOO 로컬)* `useLandmarkLayer.js` | `useLandmarkLayer.js` | ❌ **없음 — WOO가 직접 추가** |
| *(PR #60 신규)* `usePopulationLayer.js` | `usePopulationLayer.js` | ❌ **없음 — 아래 코드 참고** |

### 1.3 기타

| TERRY 경로 | `frontend/src/` 경로 | 현재 상태 |
|---|---|---|
| `constants/categories.js` | `constants/categories.js` | ✅ 존재 |
| `public/seoul_adm_dong.geojson` | `public/seoul_adm_dong.geojson` | ✅ 존재 |
| `api/agentApi.js` | *(메인앱 api.js 사용, 불필요)* | — |

---

## 2부: import 경로 변환 규칙

TERRY와 frontend/는 디렉토리 구조가 다르다. 파일 복사 시 아래 규칙으로 경로를 일괄 수정한다.

### 훅 경로 (`components/map/` 기준)

```
TERRY:    ../hooks/useMap
frontend: ../../hooks/map/useMap

TERRY:    ../hooks/useMarkers
frontend: ../../hooks/map/useMarkers

TERRY:    ../hooks/useDongLayer
frontend: ../../hooks/map/useDongLayer

TERRY:    ../hooks/useWmsClick
frontend: ../../hooks/map/useWmsClick

TERRY:    ../hooks/useLandmarkLayer
frontend: ../../hooks/map/useLandmarkLayer

TERRY:    ../hooks/usePopulationLayer
frontend: ../../hooks/map/usePopulationLayer
```

### PopulationPanel 안의 경로 (`components/map/panel/` 기준)

```
TERRY:    ../../hooks/usePopulationLayer
frontend: ../../../hooks/map/usePopulationLayer
```

### 백엔드 API URL

TERRY는 하드코딩 IP를 사용하지만, frontend/는 환경변수 + Vite 프록시를 사용한다:

```js
// TERRY (하드코딩 — frontend에서는 사용하지 말 것)
const FASTAPI_URL = "http://localhost:8681";
const REALESTATE_URL = "http://localhost:8682";

// frontend/ (올바른 방식)
const FASTAPI_URL = import.meta.env.VITE_MAP_API_URL || "/map-api";
const REALESTATE_URL = import.meta.env.VITE_REALESTATE_URL || "";
```

`usePopulationLayer.js` 안의 URL도 동일하게 수정:
```js
// 수정 전 (TERRY)
const POP_URL = import.meta.env.VITE_MAP_URL || "http://localhost:8681";

// 수정 후 (frontend)
const POP_URL = import.meta.env.VITE_MAP_API_URL || "/map-api";
```

---

## 3부: PR #60이 추가한 기능 — 적용 방법

PR #60은 세 가지 기능을 추가했다:
1. **서울 실시간 유동인구 히트맵** — `usePopulationLayer` + `PopulationPanel`
2. **카카오 로드뷰** — `RoadviewPanel`
3. **랜드마크 팝업 카카오 연동 강화** — `LandmarkPopup` 업데이트

### 중요 사전 조건

PR #60은 이미 WOO가 로컬에서 개발했지만 **git에 올리지 않은** 두 파일을 전제로 한다:
- `useLandmarkLayer.js`
- `LandmarkPopup.jsx` (기본 버전)

이 두 파일은 git 히스토리에 없으므로 **WOO가 직접 자신의 로컬에서** `frontend/`로 복사해야 한다.

---

### 단계 1: WOO 로컬에서 미커밋 파일 복사

WOO의 로컬 환경에서 아래 두 파일을 `frontend/`의 올바른 위치에 복사한다:

```bash
# WOO 로컬에서 실행

# 1. useLandmarkLayer.js
cp TERRY/p02_frontEnd_React/src/hooks/useLandmarkLayer.js \
   frontend/src/hooks/map/useLandmarkLayer.js

# 2. LandmarkPopup.jsx (기본 버전)
cp TERRY/p02_frontEnd_React/src/components/popup/LandmarkPopup.jsx \
   frontend/src/components/map/popup/LandmarkPopup.jsx
```

복사 후, 각 파일의 import 경로를 2부의 규칙에 따라 수정한다.

**`frontend/src/hooks/map/useLandmarkLayer.js`** — 수정이 필요한 부분:
```js
// 수정 전 (TERRY)
const MAP_URL = "http://localhost:8681";

// 수정 후 (frontend)
const MAP_URL = import.meta.env.VITE_MAP_API_URL || "/map-api";
```

---

### 단계 2: 신규 파일 생성

#### 2-A. `frontend/src/hooks/map/usePopulationLayer.js` (신규)

PR #60에서 새로 추가된 유동인구 히트맵 훅이다. 아래 내용으로 파일을 생성한다.

```js
// frontend/src/hooks/map/usePopulationLayer.js
// 서울 실시간 유동인구 히트맵 레이어 (citydata_ppltn API)

import { useRef } from "react";
import HeatmapLayer from "ol/layer/Heatmap";
import VectorLayer from "ol/layer/Vector";
import VectorSource from "ol/source/Vector";
import Feature from "ol/Feature";
import Point from "ol/geom/Point";
import { fromLonLat } from "ol/proj";
import { Style, Circle as CircleStyle, Fill, Stroke, Text } from "ol/style";

// ★ TERRY와 다른 부분: VITE_MAP_API_URL 사용
const POP_URL = import.meta.env.VITE_MAP_API_URL || "/map-api";

// 혼잡도 → 히트맵 강도 (0~1)
const CONGEST_WEIGHT = {
   붐빔: 1.0,
   "약간 붐빔": 0.65,
   보통: 0.35,
   여유: 0.1,
};

// 혼잡도별 색상 (범례용 — PopulationPanel이 import함)
export const CONGEST_STYLE = {
   붐빔: { color: "#E03131", bg: "#FFF0F0", emoji: "🔴", label: "붐빔" },
   "약간 붐빔": { color: "#FF9800", bg: "#FFF8F0", emoji: "🟠", label: "약간 붐빔" },
   보통: { color: "#2196F3", bg: "#F0F4FF", emoji: "🔵", label: "보통" },
   여유: { color: "#2F9E44", bg: "#F0FFF4", emoji: "🟢", label: "여유" },
};

export function usePopulationLayer(mapInstance) {
   const heatLayerRef = useRef(null);
   const dotLayerRef = useRef(null);
   const sourceRef = useRef(null);

   const loadPopulation = async () => {
      const map = mapInstance.current;
      if (!map) return 0;
      try {
         const res = await fetch(`${POP_URL}/map/population/all`);
         const data = await res.json();
         const places = data.places || [];

         const features = places.map((p) => {
            const f = new Feature({
               geometry: new Point(fromLonLat([p.lng, p.lat])),
               weight: CONGEST_WEIGHT[p.혼잡도] ?? 0.1,
               popData: p,
            });
            return f;
         });

         const source = new VectorSource({ features });
         sourceRef.current = source;

         if (heatLayerRef.current) map.removeLayer(heatLayerRef.current);
         const heatLayer = new HeatmapLayer({
            source,
            blur: 40,
            radius: 30,
            weight: (f) => f.get("weight"),
            gradient: ["#0000ff", "#00ffff", "#00ff00", "#ffff00", "#ff0000"],
            zIndex: 215,
            opacity: 0.75,
         });
         map.addLayer(heatLayer);
         heatLayerRef.current = heatLayer;

         if (dotLayerRef.current) map.removeLayer(dotLayerRef.current);
         const dotLayer = new VectorLayer({
            source,
            minZoom: 13,
            style: (f) => {
               const d = f.get("popData");
               const cs = CONGEST_STYLE[d?.혼잡도];
               return new Style({
                  image: new CircleStyle({
                     radius: 5,
                     fill: new Fill({ color: cs?.color || "#888" }),
                     stroke: new Stroke({ color: "#fff", width: 1.5 }),
                  }),
                  text: new Text({
                     text: d?.name || "",
                     font: "bold 11px sans-serif",
                     offsetY: -14,
                     fill: new Fill({ color: "#222" }),
                     stroke: new Stroke({ color: "#fff", width: 3 }),
                  }),
               });
            },
            zIndex: 216,
         });
         map.addLayer(dotLayer);
         dotLayerRef.current = dotLayer;

         return features.length;
      } catch (e) {
         console.error("[usePopulationLayer]", e);
         return 0;
      }
   };

   const setPopVisible = (v) => {
      heatLayerRef.current?.setVisible(v);
      dotLayerRef.current?.setVisible(v);
   };

   const clearPop = () => {
      const map = mapInstance.current;
      if (!map) return;
      [heatLayerRef, dotLayerRef].forEach((ref) => {
         if (ref.current) {
            map.removeLayer(ref.current);
            ref.current = null;
         }
      });
   };

   return { heatLayerRef, dotLayerRef, loadPopulation, setPopVisible, clearPop };
}
```

#### 2-B. `frontend/src/components/map/panel/PopulationPanel.jsx` (신규)

PR #60에서 기존 310줄 패널을 대폭 단순화한 범례 패널이다.

```jsx
// frontend/src/components/map/panel/PopulationPanel.jsx
// 유동인구 마커 범례 패널 (실제 마커는 usePopulationLayer에서 지도에 표시)

// ★ TERRY와 다른 부분: 경로가 ../../../hooks/map/usePopulationLayer
import { CONGEST_STYLE } from "../../../hooks/map/usePopulationLayer";

export default function PopulationPanel({ onClose, visible, onToggle, count }) {
   return (
      <div style={S.panel}>
         <div style={S.header}>
            <span style={S.title}>👥 실시간 유동인구</span>
            <button style={S.closeBtn} onClick={onClose}>✕</button>
         </div>

         {/* ON/OFF 토글 */}
         <div style={S.toggleRow}>
            <span style={{ fontSize: 12, color: "#555" }}>마커 표시</span>
            <button
               onClick={onToggle}
               style={{
                  ...S.toggleBtn,
                  background: visible ? "#2563EB" : "#e0e0e0",
                  color: visible ? "#fff" : "#555",
               }}
            >
               {visible ? "ON" : "OFF"}
            </button>
            {count > 0 && <span style={S.count}>{count}개 스팟</span>}
         </div>

         <div style={S.divider} />

         {/* 범례 */}
         <div style={S.legendTitle}>혼잡도 기준</div>
         {Object.entries(CONGEST_STYLE).map(([key, val]) => (
            <div key={key} style={S.legendRow}>
               <div style={{ ...S.dot, background: val.color }} />
               <span style={S.emoji}>{val.emoji}</span>
               <span style={S.levelLabel}>{key}</span>
               <span style={S.levelDesc}>
                  {key === "붐빔" && "매우 혼잡"}
                  {key === "약간 붐빔" && "다소 혼잡"}
                  {key === "보통" && "적정 수준"}
                  {key === "여유" && "한산함"}
               </span>
            </div>
         ))}

         <div style={S.footer}>💡 서울 주요 장소 기준 · 실시간 갱신</div>
      </div>
   );
}

const S = {
   panel: {
      position: "absolute", bottom: 50, right: 14, zIndex: 300,
      width: 220, background: "#fff", borderRadius: 16,
      boxShadow: "0 8px 32px rgba(0,0,0,0.18)", overflow: "hidden",
   },
   header: {
      display: "flex", justifyContent: "space-between", alignItems: "center",
      padding: "12px 14px 8px", borderBottom: "1px solid #f0f0f0",
   },
   title: { fontSize: 13, fontWeight: 700, color: "#111" },
   closeBtn: { background: "transparent", border: "none", color: "#bbb", cursor: "pointer", fontSize: 15 },
   toggleRow: { display: "flex", alignItems: "center", gap: 8, padding: "10px 14px" },
   toggleBtn: { border: "none", borderRadius: 6, padding: "4px 12px", fontSize: 12, fontWeight: 700, cursor: "pointer", transition: "all 0.2s" },
   count: { fontSize: 11, color: "#888" },
   divider: { height: 1, background: "#f0f0f0", margin: "0 14px" },
   legendTitle: { fontSize: 11, fontWeight: 700, color: "#aaa", padding: "10px 14px 4px", textTransform: "uppercase", letterSpacing: 1 },
   legendRow: { display: "flex", alignItems: "center", gap: 8, padding: "7px 14px" },
   dot: { width: 10, height: 10, borderRadius: "50%", flexShrink: 0 },
   emoji: { fontSize: 13 },
   levelLabel: { fontSize: 12, fontWeight: 700, color: "#333", width: 55 },
   levelDesc: { fontSize: 11, color: "#888" },
   footer: { fontSize: 10, color: "#bbb", padding: "8px 14px", borderTop: "1px solid #f0f0f0", textAlign: "center" },
};
```

#### 2-C. `frontend/src/components/map/panel/RoadviewPanel.jsx` (신규)

TERRY의 `p02_frontEnd_React/src/components/panel/RoadviewPanel.jsx` 파일을 그대로 복사한다. 외부 의존성이 없어 경로 수정 불필요.

```bash
cp TERRY/p02_frontEnd_React/src/components/panel/RoadviewPanel.jsx \
   frontend/src/components/map/panel/RoadviewPanel.jsx
```

> 주의: `index.html`의 카카오 SDK 스크립트에 `roadview` 라이브러리가 포함되어 있어야 한다. 현재 `frontend/index.html`에 이미 카카오 JS SDK 로드 설정이 있다면 `&libraries=services,clusterer,roadview`를 추가해야 할 수 있다.

---

### 단계 3: LandmarkPopup.jsx에 PR #60 변경 적용

단계 1에서 복사한 `frontend/src/components/map/popup/LandmarkPopup.jsx`는 기본 버전이다.
PR #60에서 추가된 카카오 연동 코드를 아래와 같이 반영한다.

**3-A. props 추가**
```jsx
// 수정 전
export default function LandmarkPopup({ popup, onClose }) {

// 수정 후
export default function LandmarkPopup({ popup, onClose, kakaoDetail, loadingDetail }) {
```

**3-B. 학교 판별 로직 수정**
```jsx
// 수정 전
const isSchool = popup._type === "school";

// 수정 후
const isSchool = !!(popup.school_nm || popup._type === "school");
```

**3-C. 학교 태그 표시 개선 + `Tag` 컴포넌트 추가**

학교 타입 표시 부분을 Tag 컴포넌트로 교체하고, 파일 하단에 Tag 함수를 추가한다:

```jsx
// 학교 태그 섹션 교체
{isSchool && (
   <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginBottom: 4 }}>
      {popup.school_type && <Tag text={popup.school_type} color="#10b981" />}
      {popup.found_type && <Tag text={popup.found_type} color="#6b7280" />}
      {popup.coedu && <Tag text={popup.coedu} color="#6b7280" />}
      {popup.day_night && <Tag text={popup.day_night} color="#6b7280" />}
   </div>
)}

// Row 함수 위에 Tag 함수 추가
function Tag({ text, color }) {
   return (
      <span style={{
         fontSize: 11, fontWeight: 700, padding: "2px 8px", borderRadius: 20,
         background: `${color}22`, color, border: `1px solid ${color}55`,
      }}>
         {text}
      </span>
   );
}
```

**3-D. 카카오맵 정보 섹션 추가**

팝업 본문 하단, 닫는 `</div>` 전에 카카오맵 섹션을 추가한다:

```jsx
{/* 카카오맵 추가정보 */}
{loadingDetail && (
   <div style={{ marginTop: 10, fontSize: 12, color: "#999", textAlign: "center", padding: "8px 0" }}>
      📱 카카오맵 정보 조회 중...
   </div>
)}
{!loadingDetail && kakaoDetail && (
   <>
      <div style={{
         marginTop: 10, padding: "10px 12px", background: "#fffde7",
         borderRadius: 10, display: "flex", flexDirection: "column", gap: 6,
      }}>
         <div style={{ fontSize: 11, fontWeight: 700, color: "#b8860b", marginBottom: 2 }}>
            📱 카카오맵 추가정보
         </div>
         {kakaoDetail.phone && (
            <Row icon="📞" text={
               <a href={`tel:${kakaoDetail.phone}`} style={{ color: "#2563eb", textDecoration: "none" }}>
                  {kakaoDetail.phone}
               </a>
            } />
         )}
         {kakaoDetail.category_name && <Row icon="🏷️" text={kakaoDetail.category_name} />}
      </div>
      <a href={kakaoDetail.place_url} target="_blank" rel="noreferrer"
         style={{
            marginTop: 12, display: "flex", justifyContent: "center", alignItems: "center",
            background: "#fee500", borderRadius: 10, padding: "9px",
            fontSize: 13, fontWeight: 700, color: "#111", textDecoration: "none",
         }}>
         카카오맵에서 보기 →
      </a>
   </>
)}
```

---

### 단계 4: MapView.jsx 수정

`frontend/src/components/map/MapView.jsx`를 수정한다.

**4-A. import 블록 상단에 추가**

```jsx
// 기존 import 블록 끝에 추가
import LandmarkPopup from "./popup/LandmarkPopup";
import PopulationPanel from "./panel/PopulationPanel";
import RoadviewPanel from "./panel/RoadviewPanel";
import { useLandmarkLayer } from "../../hooks/map/useLandmarkLayer";
import { usePopulationLayer } from "../../hooks/map/usePopulationLayer";
```

**4-B. state 추가** (기존 `[clickMode, setClickMode]` 선언 근처에 추가)

```jsx
// 랜드마크 관련
const [landmarkLoaded, setLandmarkLoaded] = useState(false);
const [festivalLoaded, setFestivalLoaded] = useState(false);
const [schoolLoaded, setSchoolLoaded] = useState(false);
const [landmarkPopup, setLandmarkPopup] = useState(null);
const [lmKakao, setLmKakao] = useState(null);
const [lmKakaoLoading, setLmKakaoLoading] = useState(false);

// 유동인구 관련
const [showPopPanel, setShowPopPanel] = useState(false);
const [popVisible, setPopVisible] = useState(true);
const [popCount, setPopCount] = useState(0);

// 로드뷰 관련
const [roadviewMode, setRoadviewMode] = useState(false);
const [roadviewPos, setRoadviewPos] = useState(null);
```

**4-C. hook 호출 추가** (기존 `useMarkers` 호출 아래에 추가)

```jsx
const { loadPopulation, setPopVisible: _setPopVis } = usePopulationLayer(mapInstance);

const {
   landmarkLayerRef, festivalLayerRef, schoolLayerRef,
   loadLandmarks, loadFestivals, loadSchools, selectLandmark,
} = useLandmarkLayer(mapInstance);
```

**4-D. 초기화 useEffect 추가** (기존 `useEffect(() => { clickModeRef.current = clickMode; ...` 앞에 추가)

```jsx
// 초기 랜드마크·학교·유동인구 전체 로드 (마운트 1회)
const landmarkInitRef = useRef(false);
useEffect(() => {
   if (!mapInstance.current || landmarkInitRef.current) return;
   landmarkInitRef.current = true;
   loadLandmarks().then(() => setLandmarkLoaded(true));
   loadSchools().then(() => setSchoolLoaded(true));
   loadPopulation().then((n) => setPopCount(n || 0));
}, [mapInstance.current]); // eslint-disable-line
```

**4-E. 클릭 핸들러 수정**

`clickHandler` 함수 안에서 `setWmsPopup(null)` 이후에 로드뷰 분기를 추가한다:

```jsx
// WMS 처리 후, feature 클릭 처리 전에 삽입
if (roadviewMode) {
   const [lng, lat] = toLonLat(e.coordinate);
   setRoadviewPos({ lat, lng });
   return;
}
```

랜드마크 클릭 처리 (`feature?.get("lmData")` 블록) — **기존 코드를 아래로 교체**:

```jsx
if (feature?.get("lmData")) {
   selectLandmark(feature);
   const lmData = feature.get("lmData");
   setLandmarkPopup(lmData);
   setPopup(null);
   setKakaoDetail(null);
   // 카카오 검색
   setLmKakao(null);
   setLmKakaoLoading(true);
   fetchKakaoDetail(
      lmData.title || lmData.school_nm,
      lmData.addr || lmData.road_addr,
   ).then((d) => {
      setLmKakao(d);
      setLmKakaoLoading(false);
   });
   return;
}
```

소상공인 마커 클릭 처리 (`feature?.get("store")` 블록) — **`setPopup(store)` 앞에 추가**:

```jsx
if (feature?.get("store")) {
   const store = feature.get("store");
   selectMarker(feature);       // 기존 코드에 없으면 추가
   setLandmarkPopup(null);      // ← 추가
   selectLandmark(null);        // ← 추가
   setPopup(store);
   // ... 이후 기존 코드 유지
}
```

**4-F. JSX 렌더 수정**

`<MapControls>` 컴포넌트에 prop 추가:

```jsx
<MapControls
   clickMode={clickMode}
   setClickMode={setClickMode}
   nearbyCount={nearbyCount}
   loading={loading}
   onClear={clearAll}
   dongMode={dongMode}
   onDongMode={handleDongMode}
   dongLoading={dongLoading}
   currentGuNm={currentGuNmRef.current}
   roadviewMode={roadviewMode}                        // ← 추가
   onRoadviewToggle={() => setRoadviewMode((v) => !v)} // ← 추가
   onPopPanel={() => setShowPopPanel((v) => !v)}       // ← 추가
/>
```

레이어 패널 토글 버튼(`🗂️`) 아래에 새 컴포넌트들을 추가한다:

```jsx
{showPopPanel && (
   <PopulationPanel
      onClose={() => setShowPopPanel(false)}
      visible={popVisible}
      onToggle={() => {
         const next = !popVisible;
         setPopVisible(next);
         _setPopVis(next);
      }}
      count={popCount}
   />
)}
{roadviewPos && (
   <RoadviewPanel
      lat={roadviewPos.lat}
      lng={roadviewPos.lng}
      onClose={() => {
         setRoadviewPos(null);
         setRoadviewMode(false);
      }}
   />
)}
<LandmarkPopup
   popup={landmarkPopup}
   kakaoDetail={lmKakao}
   loadingDetail={lmKakaoLoading}
   onClose={() => {
      setLandmarkPopup(null);
      setLmKakao(null);
      selectLandmark(null);
   }}
/>
```

---

### 단계 5: MapControls.jsx 수정

`frontend/src/components/map/controls/MapControls.jsx`의 props와 JSX를 수정한다.

**5-A. props 추가**

```jsx
export default function MapControls({
   clickMode,
   setClickMode,
   nearbyCount,
   loading,
   onClear,
   dongMode,
   onDongMode,
   dongLoading,
   currentGuNm,
   roadviewMode,      // ← 추가
   onRoadviewToggle,  // ← 추가
   onPopPanel,        // ← 추가
}) {
```

**5-B. 상단 컨트롤 바에 버튼 추가**

기존 로딩 스피너(`{loading && ...}`) 앞에 두 버튼을 삽입한다:

```jsx
<button
   className={`mv-ctrl-btn ${roadviewMode ? "mv-ctrl-btn--on" : "mv-ctrl-btn--off"}`}
   onClick={onRoadviewToggle}
   title="로드뷰 모드 ON/OFF"
>
   {roadviewMode ? "🚶 로드뷰 ON" : "🚶 로드뷰 OFF"}
</button>
<button
   className="mv-ctrl-btn mv-ctrl-btn--off"
   onClick={onPopPanel}
   title="유동인구 패널"
>
   👥 유동인구
</button>
```

---

## 4부: 체크리스트

모든 단계를 마친 후 아래를 확인한다.

### 파일 생성/수정

- [ ] `frontend/src/hooks/map/useLandmarkLayer.js` — WOO 로컬에서 복사 + URL 수정
- [ ] `frontend/src/components/map/popup/LandmarkPopup.jsx` — WOO 로컬에서 복사 + 경로 수정 + PR #60 변경 적용
- [ ] `frontend/src/hooks/map/usePopulationLayer.js` — 신규 생성 (3부 단계 2-A 코드)
- [ ] `frontend/src/components/map/panel/PopulationPanel.jsx` — 신규 생성 (3부 단계 2-B 코드)
- [ ] `frontend/src/components/map/panel/RoadviewPanel.jsx` — TERRY에서 복사
- [ ] `frontend/src/components/map/MapView.jsx` — 수정 (3부 단계 4)
- [ ] `frontend/src/components/map/controls/MapControls.jsx` — 수정 (3부 단계 5)

### 동작 검증

```bash
cd frontend
npm run dev
```

브라우저에서 `http://localhost:3000/map` 접속 후:

- [ ] 상단 버튼 바에 "🚶 로드뷰 OFF" 버튼 표시
- [ ] 상단 버튼 바에 "👥 유동인구" 버튼 표시
- [ ] "👥 유동인구" 클릭 → 우측 하단에 범례 패널 표시 + 지도에 히트맵 레이어
- [ ] "🚶 로드뷰 OFF" 클릭 → ON 상태로 전환 → 지도 클릭 시 우측에 로드뷰 패널
- [ ] 랜드마크/학교 마커 클릭 → 팝업 하단에 카카오맵 정보 표시

---

## 5부: 앞으로의 작업 방향

**이제부터 지도 기능 개발은 `frontend/` 폴더에서 한다.**

- 새 기능 → `frontend/src/components/map/` 또는 `frontend/src/hooks/map/`에 추가
- 백엔드 API URL → `import.meta.env.VITE_MAP_API_URL || "/map-api"` 패턴 사용
- `TERRY/` 폴더는 참고용으로만 유지 (직접 수정 불필요)
- PR은 `frontend/` 변경사항만 포함하여 올린다

TERRY 백엔드(`p01_backEnd/`)는 독립적으로 운영되며, 향후 `integrated_PARK/agents/`와 통합 예정이다. 백엔드 쪽 변경사항(예: `populationDAO.py` 추가)은 별도 PR로 진행한다.
