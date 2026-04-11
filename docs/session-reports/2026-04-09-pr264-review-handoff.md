# PR #264 리뷰 인수인계

- **날짜**: 2026-04-09
- **브랜치**: `WOO-css-fix` (origin/main 기반)
- **PR**: #264 — "fix: MapControls 위치 왼쪽 고정 및 챗봇 버튼 겹침 해소"
- **작성자**: TerryBlackhoodWoo (WOO)
- **리뷰 커밋**: `16e805c` (PARK이 이슈 1차 수정 push 완료)

## 현재 상태

WOO의 원래 커밋(`3e79573`) + 리뷰 수정 커밋(`16e805c`)이 `WOO-css-fix`에 올라가 있다. 1차 리뷰에서 발견한 dead code/무효 className/CSS 중복은 `16e805c`에서 해결 완료. 그러나 2차 리뷰(시니어 관점)에서 추가 이슈 발견 — **머지 전 아래 이슈 해결 필요**.

## 수정된 파일

| 파일 | 변경 요약 |
|------|----------|
| `frontend/src/components/map/ChatPanel.css` | indent 2→3 space 통일, `width: fit-content` 추가, CSS 중복 제거 |
| `frontend/src/components/map/ChatPanel.jsx` | indent 통일, dead code `isOpen` 제거 |
| `frontend/src/components/map/MapView.css` | 토글 버튼 `right→left`, WMS 팝업 chat-open 룰 추가 |
| `frontend/src/components/map/MapView.jsx` | MapControls 미사용 prop 제거, StorePopup/WmsPopup에 `chatOpen` 전달 |
| `frontend/src/components/map/controls/MapControls.css` | `right→left` 고정, `bottom: 120→170px`, gu-badge 제거 |
| `frontend/src/components/map/controls/MapControls.jsx` | 미사용 prop 제거, className 단순화 |
| `frontend/src/components/map/popup/StorePopup.css` | `--chat-open` 룰 추가 |
| `frontend/src/components/map/popup/StorePopup.jsx` | `chatOpen` prop 추가 |
| `frontend/src/components/map/popup/WmsPopup.jsx` | `chatOpen` prop 추가 |
| `integrated_PARK/agents/finance_agent.py` | 프롬프트 문구 수정 (PR 범위 밖) |

---

## 미해결 이슈 (머지 차단)

### 이슈 1: `.mv-chat-toggle` CSS 위치 2곳 충돌 [High]

**문제**: 동일 클래스 `.mv-chat-toggle`이 두 CSS 파일에서 서로 다른 위치를 선언.

| 파일 | 선언 |
|------|------|
| `ChatPanel.css:2-6` | `bottom: 20px; right: 14px; z-index: 450` |
| `MapView.css:3-6` | `bottom: 80px; left: 12px; z-index: 290` |

CSS 로드 순서에 따라 어느 쪽이 적용되는지 비결정적. 번들러 설정 의존.

**해결 방향**: 한 곳에서만 선언. `ChatPanel.css`가 토글 버튼의 소유 파일이므로 거기서 최종 위치를 결정하고, `MapView.css`의 `.mv-chat-toggle` 룰은 삭제.

### 이슈 7: 모바일 반응형 토글 위치 모순 [Medium]

`ChatPanel.css:499-502` 모바일 미디어쿼리에서 `right: 12px`로 다시 오른쪽 배치. 데스크톱은 왼쪽, 모바일은 오른쪽이 의도인지 확인 필요. 이슈 1 해결 시 같이 정리.

---

## 미해결 이슈 (후속 PR 가능)

### 이슈 2: `416px` 매직 넘버 [Medium]

`StorePopup.css`, `MapView.css`에서 `right: 416px` 하드코딩 (= chat panel 400px + 16px margin). `--dong-panel-width`처럼 `--chat-panel-width` CSS 변수로 관리 권장.

**관련 파일**:
- `frontend/src/components/map/popup/StorePopup.css` → `.sp-popup--chat-open`
- `frontend/src/components/map/MapView.css` → `.mv-wms-popup--chat-open`
- `frontend/src/components/map/ChatPanel.css:57` → `.mv-chat-panel { width: 400px }`

### 이슈 3: `.sp-popup--chat-open.sp-popup--dong-open` dead/wrong [Medium]

`StorePopup.css`에서 compound 선택자의 `right` 값이 `.sp-popup--dong-open` 단독과 동일 → chat+dong 동시 열림 시 겹칠 수 있음. `right: calc(var(--dong-panel-width) + var(--chat-panel-width) + 16px)` 같은 합산이 필요할 수 있음.

### 이슈 4: `onHighlightArea` useCallback deps 누락 [Low]

`ChatPanel.jsx:385` — `handleSend` deps array에 `onHighlightArea` 없음. 콜백 내부(332행)에서 사용하므로 stale closure 가능.

### 이슈 5: `BIZ_LIST` 모듈 스코프 이동 [Nit]

`ChatPanel.jsx:341-358` — `handleSend` 안에서 매번 배열 생성. `AREA_NAMES`처럼 모듈 최상단으로 이동.

### 이슈 6: `finance_agent.py` PR 범위 밖 [Nit]

백엔드 프롬프트 수정이 CSS fix PR에 섞여 있음. squash merge 시 커밋 히스토리 오염. 별도 PR 분리 권장.

---

## 다음 세션 작업 순서

1. **이슈 1+7 해결** — `.mv-chat-toggle` 위치 선언을 `ChatPanel.css` 한 곳으로 통합. `MapView.css`의 `.mv-chat-toggle` 블록 삭제. 모바일 반응형 의도 확인 후 정리.
2. **로컬 검증** — `npm run dev`로 데스크톱/모바일 뷰포트에서 토글 위치 확인.
3. **이슈 2+3 해결** — `--chat-panel-width` CSS 변수 도입, compound 선택자 `right` 값 수정.
4. **빌드 확인** — `npm run build` 에러/경고 없음 확인.
5. **커밋 & push** — 같은 `WOO-css-fix` 브랜치에 커밋 추가.
6. **PR #264 머지 가능 보고**.

## 검증 체크리스트

- [ ] 데스크톱: 토글 버튼 왼쪽 하단 고정
- [ ] 데스크톱: 챗패널 열림 → 팝업/WMS팝업이 챗패널과 겹치지 않음
- [ ] 데스크톱: 챗패널 + 동패널 동시 열림 → StorePopup 위치 정상
- [ ] 모바일 (640px 이하): 토글 버튼 위치 의도대로
- [ ] 모바일: 챗패널 전체 너비 표시
- [ ] `npm run build` 경고/에러 없음
- [ ] `localhost` 하드코딩 없음 (`grep -r "localhost" --include="*.jsx" --include="*.css" frontend/src/components/map/`)
