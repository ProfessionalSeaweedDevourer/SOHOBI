# 인수인계 — 2026-04-06 지도 성능·구조 개선 (PARK 브랜치)

## 브랜치 / 작업 상태

- **작업 브랜치:** `PARK`
- **미커밋 상태:** 아래 변경사항 전체 uncommitted. 커밋 후 PR 필요.

---

## 이번 세션 완료 항목

### WOO-clean2 관찰 및 선별 반영

WOO-clean2 00e878f, 6b755d9 리뷰 후 유익한 부분만 PARK에 독립 구현.
WOO-clean2는 merge 금지, 관찰 전용.

| 파일 | 변경 내용 |
|------|----------|
| `Layerpanel.jsx` | 지적도 LAYERS bonbun 추가, cadastral/tourist_info 토글 → `setVisible()` 전환 |
| `DongPanel/SvcPanel.jsx` | `lbl` 폴백 `|| r.svc_cd || "기타"` 추가 |
| `DongPanel/StorePanel.jsx` | 동일 |

### 지도 성능·구조 즉시 개선

| 파일 | 변경 내용 |
|------|----------|
| `useRealEstate.js` | 하드코딩 `"http://localhost:8682"` → `import.meta.env.VITE_REALESTATE_URL || ""` |
| `hooks/map/useMapZoom.js` | **신규 훅** — 줌 레벨 추적 + OL 버튼 배지 렌더링 |
| `MapView.jsx` | zoom useState·useEffect 제거 → `useMapZoom` 교체, 카테고리 fetch 200ms debounce 추가 |

---

## 다음 세션 필수 작업 (우선순위순)

### [3] 동 패널 로드 함수 통합

**문제:** 동 클릭 fetch 패턴이 두 곳 중복.
- `handleDongMode` (MapView.jsx ~L420)
- `clickHandler` 폴리곤 분기 (~L760)

**해결:** `fetchDongPanel(admCd, dongNm, guNm, mode, qtr)` 단일 함수로 통합.
이후 [4] 캐시 적용 진입점이 됨.

### [4] adm_cd 인메모리 캐시

**문제:** 같은 동 재클릭 시 stores-by-dong, sangkwon, sangkwon-svc 매번 재요청.

**해결:** `hooks/map/useDongCache.js` 신규.
```js
const cache = useRef(new Map()); // key: `${admCd}:${qtr}`
```
[3] 완료 후 `fetchDongPanel` 내부에 캐시 히트 분기 삽입.

### [5] clickHandler 분리 (대형)

**문제:** MapView.jsx L577–875, 단일 함수 298줄.

**해결:**
```js
const clickHandler = async (e) => {
  if (await handleMarkerClick(e)) return;   // ~80줄
  if (await handlePolygonClick(e)) return;  // ~170줄
  handleWmsClick(e);                        // ~30줄
};
```

### [6] State/Ref 이중 관리 해소

**선행조건:** [5] 완료 후 진행.

| state | ref |
|-------|-----|
| `storeSearchOn` | `storeSearchOnRef` |
| `dongMode` | `dongModeRef` |
| `visibleCats` | `visibleCatsRef` |

clickHandler가 useEffect 외부로 나오면 ref 없이 state만으로 해결 가능.

---

## 추가 발견 기술 부채 (미착수)

- `selectedQtr` useEffect에 `dongPanel` 의존성 누락 (MapView.jsx ~L130)
- 전역 silent `.catch(() => {})` 23개 이상 — 에러 로깅 없음
- `loading` / `dongLoading` / `loadingDetail` 파편화

---

## 핵심 파일 경로

```
frontend/src/components/map/MapView.jsx          ← ~1200줄, 핵심
frontend/src/components/map/panel/Layerpanel.jsx
frontend/src/hooks/map/                          ← 기존 6훅 + 신규 useMapZoom.js
frontend/src/components/map/panel/DongPanel/
```
