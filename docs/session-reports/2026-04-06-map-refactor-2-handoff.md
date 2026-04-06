# 인수인계 — 2026-04-06 지도 구조 개선 2차 (PARK 브랜치)

## 브랜치 / PR 상태

- **작업 브랜치:** `PARK`
- **PR:** #176 (open, 미머지) — main 머지 대기
- **커밋 상태:** 전부 커밋·push 완료

---

## 이번 세션 완료 항목

이전 인수인계(`2026-04-06-map-perf-refactor-handoff.md`)의 우선순위 [3]~[6] 실행.

### [3] fetchDongPanel 함수 추출 ✅

**파일:** `frontend/src/components/map/MapView.jsx` (~L362)

`handleDongMode`와 `clickHandler` 폴리곤 분기에 중복됐던 sales/realestate/store fetch 로직을 `fetchDongPanel(admCd, dongNm, guNm, admNm, mode, qtr)` 단일 함수로 통합.

- 두 호출부에서 ~130줄 제거
- `handleDongMode`에 누락됐던 `sangkwon-svc` fetch가 통합으로 자동 추가됨
- `handleDongMode`에서 `loadFestivals` 호출은 `fetchDongPanel` 완료 후 별도 유지

### [4] useDongCache 훅 신규 ✅

**파일:** `frontend/src/hooks/map/useDongCache.js` (신규)

```js
// key: `${admCd}:${mode}:${qtr}`
const cache = useRef(new Map());
```

- 같은 동 재클릭 시 sangkwon/svc/sangkwon-store API 재요청 차단
- `sangkwon-svc`는 fire-and-forget 유지 → 패널 표시 블로킹 없음, 완료 후 캐시 저장
- MapView에서 `const dongCache = useDongCache()` 선언 후 `fetchDongPanel` 내부에서 사용

### [5] clickHandler 분리 ✅

**파일:** `frontend/src/components/map/MapView.jsx` (useEffect 내부)

298줄 단일 함수 → 3개 내부 함수로 분리:

```js
const handleMarkerClick = async (e) => { ... }; // ~70줄, true/false 반환
const handlePolygonClick = async (e) => { ... }; // ~100줄, true/false 반환
const clickHandler = async (e) => {
  if (await handleMarkerClick(e)) return;
  if (await handlePolygonClick(e)) return;
  // WMS 3순위 fallback (~15줄)
};
```

### [6] storeSearchOnRef 제거 ✅

`handleSearch`는 컴포넌트 레벨 함수(매 렌더 재생성)이므로 ref 불필요.
`storeSearchOnRef` 선언 + 동기화 useEffect 제거, `storeSearchOn` state 직접 참조로 교체.

---

## 다음 세션 필수 작업 (우선순위순)

### [6-속편] dongModeRef / visibleCatsRef 제거

**선행조건:** `handleMarkerClick`, `handlePolygonClick`을 useEffect 밖으로 이전.

**문제:** 두 함수가 아직 `useEffect([], [])` 내부에 정의되어 있어 클로저 캡처 문제가 남아 있음.
- `dongModeRef.current` — `handlePolygonClick` L673
- `visibleCatsRef.current` — useEffect 내 `drawMarkers` 호출 4곳 (L338, L461, L466, L690, L830 근방)

**해결 방향:**
```js
// useEffect 밖에서 useCallback으로 정의
const handlePolygonClick = useCallback(async (e) => {
   // dongModeRef.current → dongMode (state)
   // visibleCatsRef.current → visibleCats (state)
}, [dongMode, visibleCats, ...other_deps]);

// 이벤트 등록 useEffect는 콜백 변경 시 재등록
useEffect(() => {
   const map = mapInstance.current;
   if (!map) return;
   map.on("click", clickHandler);
   return () => map.un("click", clickHandler);
}, [clickHandler]);
```

이후 `dongModeRef` + `visibleCatsRef` + 동기화 useEffect 제거 가능.

> ⚠️ `visibleCatsRef`는 `handleToggleCat` (L196), `handleShowAll` (L203), `handleHideAll` (L207) 에서도 직접 동기화하므로 useCallback deps에 `visibleCats`를 포함해야 함.

### [7] selectedQtr useEffect 의존성 누락

**위치:** `MapView.jsx` ~L108

```js
useEffect(() => {
   if (!selectedQtr || !dongPanel || ...) return;
   fetch(...sangkwon...);
}, [selectedQtr]); // eslint-disable-line  ← dongPanel 의존성 누락
```

`dongPanel`이 deps에 없어 stale closure 위험. `dongPanel.admCd`를 별도 state로 분리하거나 `useRef`로 관리 필요.

### [8] 전역 silent catch 정리

**현황:** `.catch(() => {})` 빈 핸들러 추정 20개 이상 (MapView.jsx 내 집중)

```bash
grep -n '\.catch(() => {})' frontend/src/components/map/MapView.jsx
```

각 catch에 `console.error("[위치] 오류:", e)` 최소 로깅 추가.

### [9] loading state 파편화

현재 3개 로딩 state (`loading`, `dongLoading`, `loadingDetail`)가 독립적으로 관리됨.
`useDongPanel` 훅 또는 통합 로딩 컨텍스트로 정리 검토.

---

## 캐시 주의사항

`useDongCache`는 **세션 내 인메모리 캐시**임 (페이지 새로고침 시 초기화).

현재 캐시가 무효화되지 않는 케이스:
- `selectedQtr` 변경 시 → `selectedQtr` useEffect가 `setDongPanel`을 직접 호출하므로 캐시 미갱신. 이후 같은 동 재클릭 시 구 분기 데이터 캐시가 히트될 수 있음.
- 해결: `dongCache.clear()` 또는 특정 키 무효화를 `selectedQtr` useEffect에 추가.

---

## 핵심 파일 경로

```
frontend/src/components/map/MapView.jsx          ← ~1100줄 (전회 대비 ~100줄 감소)
frontend/src/hooks/map/useDongCache.js           ← 신규 (21줄)
frontend/src/hooks/map/                          ← 7훅 총계
```

## PR

- **#176** — open, main 머지 대기
- Test Plan: 동 패널 6가지 TC + MyReport TC 확인 후 머지
