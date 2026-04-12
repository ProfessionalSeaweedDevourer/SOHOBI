# 인수인계 — 2026-04-07 지도 리팩터 4차 (PARK 브랜치)

## 브랜치 / PR 상태

- **작업 브랜치:** `PARK`
- **PR #178** — MERGED (clickHandler useCallback 이전 + ref 제거 + selectedQtr 수정)
- **PR #179** — open, main 머지 대기

---

## 이번 세션 완료 항목

### PR #178 머지 확인

이전 세션에서 push된 PR #178이 이번 세션 시작 시 이미 머지 완료 상태로 확인됨.

---

### WOO-clean2(PR #177) 선별 검토

PR #177은 **머지 금지** 결정. 코드 신뢰도가 낮으므로 실제 버그가 확인된 항목만 독립적으로 수정.

검토 결과 반영/스킵 목록:

| 항목 | 결정 | 이유 |
|------|------|------|
| zIndex 재조정 | ✅ 반영 | 지적도(200)가 마커(100) 위에 렌더링되는 실제 버그 |
| vite /map 프록시 세분화 | ✅ 반영 | React Router /map 라우트와 hard-refresh 충돌 |
| commercial.db 삭제 | ✅ 반영 | DB는 Azure 일원화, 로컬 SQLite 불필요 |
| DongPanel 통합 (9 파일→1) | ❌ 스킵 | 모듈 구조 파괴 |
| useMapSetup.js 신규 훅 | ❌ 스킵 | 불필요한 복잡성 |
| 지적도 minZoom 19 | ❌ 스킵 | UI "줌 17+ 필요" 텍스트와 모순 |
| limit 500→2000 | ❌ 스킵 | 서버 부하 감안 |
| StorePopup other_branches | ❌ 스킵 | 백엔드 응답 구조 변경 미확인 |

---

### [A] zIndex 레이어 스택 재조정 ✅

**파일:** `Layerpanel.jsx`, `useMarkers.js`, `useLandmarkLayer.js`

수정 전 스택 (버그):
- 클러스터/마커: 100 → 지적도(200) 아래에 가려짐

수정 후 스택:
```
클러스터/마커      zIndex 200  ← 최상단
랜드마크·축제·학교 zIndex 55~57
원형 범위          zIndex 90
지적도             zIndex 50   ← 배경 수준
```

지적도 minZoom은 17 그대로 유지 (UI "줌 17+ 필요" 명시).

---

### vite.config.js 프록시 세분화 ✅

**파일:** `frontend/vite.config.js`

광역 `/map` 프록시 → `/map/stores-by-dong`, `/map/stores-by-building` 세분화.
`App.jsx:30`에 `<Route path="/map">` 존재 → hard-refresh 시 충돌 방지.

---

### commercial.db 삭제 ✅

**파일:** `integrated_PARK/db/commercial.db` (git rm), `CLAUDE.md` 업데이트

로컬 SQLite 제거. DB는 Azure 백엔드로 일원화. 이후 SQLite 직접 작업 금지.

---

## PR #179 TC 검증 현황

| TC | 항목 | 결과 |
|----|------|------|
| TC1 | 줌 17+ 지적도 활성 → 마커가 지적도 위 표시 | 수동 확인 필요 |
| TC2 | 줌 14~16 클러스터 → 모든 레이어 최상단 표시 | 수동 확인 필요 |
| TC3 | 줌 16+ 랜드마크 → 마커 아래, 지적도 위 표시 | 수동 확인 필요 |
| TC4 | `/map` hard-refresh → React 앱 정상 로드 | ✅ PASS (curl 확인) |
| TC5 | 동 클릭 → stores-by-dong API 정상 | 수동 확인 필요 (로컬 백엔드 미기동) |

TC1~TC3, TC5는 브라우저에서 직접 확인 후 PR #179 머지 가능.

---

## 다음 세션 작업 (우선순위순)

### [10] PR #179 TC 수동 검증 후 머지

위 TC 체크리스트 기준으로 브라우저 확인.

### [9] loading state 파편화 정리

**파일:** `frontend/src/components/map/MapView.jsx`

현재 3개 독립 state:
```js
const [loading, setLoading] = useState(false)       // 일반 로딩
const [dongLoading, setDongLoading] = useState(false)  // 동 패널 fetch
const [loadingDetail, setLoadingDetail] = useState(false) // Kakao 상세
```

`useDongPanel` 훅 또는 통합 로딩 컨텍스트로 정리 검토.
MapView.jsx가 ~960줄로 여전히 크므로, 로딩 로직 분리가 가독성 향상에 유효.

---

## 핵심 파일 경로

```
frontend/src/components/map/MapView.jsx         ← ~960줄, 로딩 state 3개 잔존
frontend/src/components/map/panel/Layerpanel.jsx ← zIndex 50 (지적도)
frontend/src/hooks/map/useMarkers.js             ← zIndex 90/200 (범위/클러스터)
frontend/src/hooks/map/useLandmarkLayer.js       ← zIndex 55~57 (랜드마크)
frontend/vite.config.js                          ← /map 프록시 세분화
```
