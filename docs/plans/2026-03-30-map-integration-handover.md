# 세션 인계 문서 — 지도 프론트엔드 통합 (2026-03-30)

## 현재 상태

- **브랜치**: `PARK`
- **PR**: ProfessionalSeaweedDevourer/SOHOBI#57 (main 머지 대기)
- **빌드 상태**: `vite build` 오류 없음 (431 모듈)

---

## 이번 세션에서 한 일

### 1. 검토 및 비교 분석

CHOI/locationAgent_DB (독립 실행형 에이전트)와 integrated_PARK/agents/location_agent.py를 비교 분석했습니다.

**핵심 발견:**
- DB 스키마·테이블 동일 (SANGKWON_SALES, SANGKWON_STORE, Oracle)
- CHOI가 앞선 점: DB 쿼리 병렬화(`asyncio.gather`), Similar Locations 가중치 스코어링(avg_sales 0.4 + close_rate 0.3 + volume 0.2 + open_rate 0.1)
- Integrated가 앞선 점: Sign-off 루브릭 재시도, Azure 콘텐츠 필터 처리, 대화 히스토리 주입
- 플랜 문서: `docs/plans/linked-bouncing-hearth.md`

### 2. TERRY 지도 → frontend/ Phase 1 이식 완료

TERRY/p02_frontEnd_React의 OpenLayers 지도를 `frontend/` SPA에 `/map` 경로로 통합했습니다.

**추가된 파일 구조:**

```
frontend/
├── public/
│   └── seoul_adm_dong.geojson       ← 서울 행정동 경계 (800KB)
├── src/
│   ├── constants/
│   │   └── categories.js            ← 업종 카테고리 10종 (I2/G2/S2...)
│   ├── hooks/map/
│   │   ├── useMap.js                ← OL Map 초기화 + VWorld 타일
│   │   ├── useDongLayer.js          ← 행정동 GeoJSON 폴리곤 레이어
│   │   ├── useMarkers.js            ← 소상공인 마커 + 반경원
│   │   └── useWmsClick.js           ← WMS GetFeatureInfo 클릭 처리
│   ├── components/map/
│   │   ├── MapView.jsx              ← 지도 메인 (771줄, TERRY 이식 + URL 수정)
│   │   ├── MapView.css
│   │   ├── ChatPanel.jsx            ← 지도 채팅 (sendChatMessage → streamQuery 교체)
│   │   ├── ChatPanel.css
│   │   ├── controls/
│   │   │   ├── MapControls.jsx      ← 상단 컨트롤 바 + 동 모드 버튼
│   │   │   └── DongTooltip.jsx      ← 동 호버 툴팁
│   │   ├── panel/
│   │   │   ├── CategoryPanel.jsx    ← 업종 필터 사이드바
│   │   │   ├── DongPanel.jsx        ← 동 클릭 시 상권/부동산 패널
│   │   │   └── Layerpanel.jsx       ← WMS 레이어 관리
│   │   └── popup/
│   │       ├── StorePopup.jsx       ← 소상공인 마커 팝업 + 카카오 연동
│   │       └── WmsPopup.jsx         ← WMS(지적도·관광지·전통시장) 팝업
│   └── pages/
│       └── MapPage.jsx              ← /map 경로 진입점 (MapView 래핑)
```

**수정된 기존 파일:**

| 파일 | 변경 내용 |
|------|----------|
| `frontend/package.json` | `ol@^10.8.0`, `@turf/turf@^7.3.4`, `axios@^1.13.6` 추가 |
| `frontend/vite.config.js` | 프록시 추가: `/kakao`→dapi.kakao.com, `/vworld`·`/wms`→api.vworld.kr, `/map-api`→8681, `/realestate`→8682 |
| `frontend/src/App.jsx` | `<Route path="/map" element={<MapPage />} />` 추가 |
| `frontend/src/pages/Home.jsx` | 지도 모드 카드 추가 (세 번째 모드, 에메랄드 색) |

---

## 현재 동작 상태

### 정상 동작
- VWorld 타일 지도 렌더링 (`VITE_VWORLD_API_KEY` 필요)
- 서울 행정동 경계 폴리곤 (`/seoul_adm_dong.geojson` → public/)
- 행정동 클릭 → 동 모드(매출/점포/실거래가) 패널 표시 UI
- 채팅 → 통합 백엔드 `streamQuery()` SSE 연결
- 카카오 지오코딩 ("강남역 보여줘" → 지도 이동)
- WMS 레이어(지적도·관광지·전통시장) 토글 + 팝업

### 미동작 (외부 서버 미연결)
- **반경 소상공인 마커** (`/map/nearby`): `FASTAPI_URL=/map-api` → 8681 포트. 서버 정체 불명.
- **동 매출/점포/실거래가 데이터** (`/realestate/*`): `REALESTATE_URL` → 8682 포트. 서버 정체 불명.
- 위 두 기능은 fetch 실패 시 조용히 빈 결과 처리 (앱 크래시 없음).

---

## 다음에 해야 할 일

### 즉시 (PR 머지 전 확인)
1. **포트 8681/8682 서버 정체 확인** — Terry에게 문의
   - 8681: 소상공인 SQLite DB 서버 (`/map/nearby` 엔드포인트)
   - 8682: 부동산 실거래가 API (`/realestate/*` 엔드포인트)
   - 확인 후 `VITE_MAP_API_URL` / `VITE_REALESTATE_URL` 환경변수 또는 Azure 배포 프록시 설정

2. **`.env` API 키 설정 확인**
   ```
   VITE_VWORLD_API_KEY=...
   VITE_KAKAO_API_KEY=...
   ```

3. **PR#57 테스트 체크리스트 통과 확인 후 머지**

### Phase 2 (다음 세션)
에이전트 응답에서 지역 딥링크 생성:
- `location_agent.py`의 `generate_draft()` 반환값에 `adm_cd` 포함
- `ResponseCard.jsx`에서 `[지도에서 보기](/map?adm_cd=XXXXXXXX)` 링크 렌더링
- `/map` 페이지가 `?adm_cd` 쿼리 파라미터를 받아 해당 행정동 자동 포커스

### Phase 3 (그 다음)
- CHOI locationAgent_DB cherry-pick: DB 쿼리 병렬화 + Similar Locations 스코어 알고리즘 → `integrated_PARK/agents/location_agent.py`에 적용

---

## 주요 기술 결정 사항

| 결정 | 내용 | 이유 |
|------|------|------|
| 채팅 방식 | `streamQuery()` SSE (기존 방식 통일) | TERRY의 단순 POST 대신 ProgressPanel 노출 가능, 일관성 |
| 하드코딩 URL 제거 | `FASTAPI_URL=/map-api`, `REALESTATE_URL=""` (proxy 경유) | 환경변수로 배포 유연성 확보 |
| CSS 전략 | Tailwind + CSS 모듈 혼용 유지 | OpenLayers 스타일이 섞인 MapView.css를 Tailwind 변환 시 사이드이펙트 위험 |
| GeoJSON | `frontend/public/` 직접 포함 | WFS 서버 의존성 제거, 오프라인 동작 |

---

## 관련 문서

- 통합 검토 플랜: `docs/plans/linked-bouncing-hearth.md`
- CLAUDE.md: 빌드/실행 명령, 디렉토리 구조
- PR: ProfessionalSeaweedDevourer/SOHOBI#57
