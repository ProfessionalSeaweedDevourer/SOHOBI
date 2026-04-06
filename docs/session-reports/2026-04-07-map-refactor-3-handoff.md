# 인수인계 — 2026-04-07 지도 리팩터 3차 (PARK 브랜치)

## 브랜치 / PR 상태

- **작업 브랜치:** `PARK`
- **PR:** #178 (open, 미머지) — main 머지 대기
- **커밋 상태:** 전부 커밋·push 완료

---

## 이번 세션 완료 항목

이전 인수인계(`2026-04-06-map-refactor-2-handoff.md`)의 [6-속편]~[8] 실행.

### [6-속편] dongModeRef / visibleCatsRef 완전 제거 ✅

**파일:** `frontend/src/components/map/MapView.jsx`

- `dongModeRef` 선언(L95) + 동기화 useEffect 삭제
- `visibleCatsRef` 선언 + 전체 `.current` 참조 삭제 (8곳 → state 직접 참조)
- `handleToggleCat` / `handleShowAll` / `handleHideAll` 내 불필요한 ref 대입 제거

**handleMarkerClick / handlePolygonClick / clickHandler → useCallback 이전:**

```js
// useEffect([]) 외부로 이전
const handleMarkerClick = useCallback(async (e) => { ... }, []);
const handlePolygonClick = useCallback(async (e) => { ... }, [dongMode, visibleCats, selectedQtr]);
const clickHandler = useCallback(async (e) => { ... }, [handleMarkerClick, handlePolygonClick]);

// click 이벤트 등록 전용 useEffect 추가
useEffect(() => {
  const map = mapInstance.current;
  if (!map) return;
  map.on("click", clickHandler);
  return () => map.un("click", clickHandler);
}, [clickHandler]);
```

`fetchDongPanel`은 `fetchDongPanelRef` 패턴으로 useCallback 내 stale closure 방지.

### [7] selectedQtr useEffect 의존성 수정 ✅

**파일:** `frontend/src/components/map/MapView.jsx` L105~

`dongPanelRef` 추가 + 동기화 useEffect:
```js
const dongPanelRef = useRef(null);
useEffect(() => { dongPanelRef.current = dongPanel; }, [dongPanel]);
```
`selectedQtr` useEffect 내 `dongPanel` 직접 참조 → `dongPanelRef.current` 교체. `eslint-disable-line` 주석 제거.

### [C] useDongCache clearAll + selectedQtr 캐시 무효화 ✅

**파일:** `frontend/src/hooks/map/useDongCache.js`

`clearAll()` 메서드 추가. `selectedQtr` useEffect 첫 줄에 `dongCache.clearAll()` 호출 — 분기 변경 시 구 분기 캐시 히트 방지.

### [8] silent catch 6곳 정리 ✅

**파일:** `frontend/src/components/map/MapView.jsx`

`.catch(() => {})` 6곳 → `console.error("[MapView] 위치: ...", e)` 로 교체.

---

## 다음 세션 작업 (우선순위순)

### [9] loading state 파편화 정리

현재 3개 로딩 state (`loading`, `dongLoading`, `loadingDetail`)가 독립적으로 관리됨.
`useDongPanel` 훅 또는 통합 로딩 컨텍스트로 정리 검토.

### [10] PR #178 TC 수동 검증 후 머지

TC:
1. 동 클릭 → 패널 표시 정상
2. 같은 동 재클릭 → 캐시 히트, API 재요청 없음 (Network 탭)
3. selectedQtr 변경 → 패널 데이터 갱신, 캐시 무효화 확인
4. 카테고리 토글 후 동 클릭 → 마커 필터 정상 적용
5. 마커 클릭 → 팝업 정상 표시
6. 콘솔 에러 없음 확인

---

## 핵심 파일 경로

```
frontend/src/components/map/MapView.jsx     ← ~960줄 (전회 대비 ~120줄 감소)
frontend/src/hooks/map/useDongCache.js      ← clearAll 추가
```

## PR

- **#178** — open, main 머지 대기
- playwright TC 실행 미완 (로컬 브라우저 타임아웃) → 수동 검증 필요
