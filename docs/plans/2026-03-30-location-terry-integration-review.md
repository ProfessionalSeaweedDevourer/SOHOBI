# CHOI locationAgent_DB + TERRY 지도 프론트엔드 통합 리뷰 플랜

## Context

- **CHOI/locationAgent_DB**: 상권 분석 에이전트의 독립 실행형 버전. Oracle DB 쿼리 병렬화, 구조화된 JSON 반환, FastAPI REST 엔드포인트를 갖춤.
- **integrated_PARK/agents/location_agent.py**: 오케스트레이터 통합 버전. Sign-off 루브릭 재시도, Azure 콘텐츠 필터 처리, 대화 히스토리 주입이 추가되어 있음.
- **TERRY/p02_frontEnd_React**: OpenLayers + VWorld 기반 지도 프론트엔드. 별도 포트(8681)의 부동산 API + 메인 에이전트(8000) 동시 사용.
- **frontend/**: React Router v7 기반 채팅 전용 SPA. 지도 기능 없음.

목표: 두 자산을 통합본에 합치는 방안 검토 및 단계별 로드맵 수립.

---

## Part 1 — CHOI locationAgent_DB vs integrated location_agent.py 비교

### 공통점
- 동일한 Oracle DB 스키마 (SANGKWON_SALES, SANGKWON_STORE)
- 동일한 AREA_MAP(208개 지역), INDUSTRY_CODE_MAP(17개 업종)
- analyze() / compare() 메서드 구조 유사

### CHOI가 앞선 점 (cherry-pick 후보)
| 항목 | CHOI 구현 | Integrated 현황 |
|------|-----------|----------------|
| DB 쿼리 병렬화 | asyncio.gather + ThreadPoolExecutor(max_workers=4) — 지역별 sales/store 동시 쿼리 | 순차 실행 |
| Similar Locations 스코어링 | 가중치 알고리즘(avg_sales 0.4 + close_rate 0.3 + volume 0.2 + open_rate 0.1), 95th percentile 이상치 제거 | 별도 구현 없음 |
| 구조화된 JSON 반환 | `{location, analysis, sales_data(raw), store_data(raw), similar_locations[{score,...}]}` | 마크다운 텍스트만 반환 |
| Plugin 패턴 | `@kernel_function` + SK ChatCompletionAgent | `@kernel_function` 있음 (통합은 완료) |

### Integrated가 앞선 점 (유지 필수)
| 항목 | 설명 |
|------|------|
| Sign-off 루브릭 재시도 | generate_draft() → S1-S5 피드백 → retry_prompt로 재생성 |
| Azure 콘텐츠 필터 처리 | content_filter 예외 catch → 안전 접두어 붙여 재시도 |
| 대화 히스토리 주입 | prior_history 파라미터로 선행 맥락 참조 |
| 창업 프로필 컨텍스트 | _PROFILE_CONTEXT 주입 |

### 권장 액션 (백엔드)
**우선순위 높음 — 바로 반영 가치 있음:**
1. **DB 쿼리 병렬화** cherry-pick: CHOI의 `asyncio.gather()` 패턴을 `integrated_PARK/agents/location_agent.py`의 `_fetch_data()` 또는 동등 위치에 적용. 멀티 지역 비교 쿼리 속도 크게 개선.
2. **Similar Locations 스코어 알고리즘** cherry-pick: CHOI의 가중치 공식 + 이상치 제거 로직을 integrated에 추가 (현재 유사 상권 추천 로직 보강).

**우선순위 낮음 — 통합 시 구조 변경 필요:**
3. 구조화 JSON 반환: Integrated는 현재 오케스트레이터가 markdown 텍스트를 바로 사용하므로, 단기적으로는 변경 불필요. 지도 연동 단계(Phase 2)에서 좌표 추출 목적으로 필요해질 때 추가.

---

## Part 2 — TERRY 지도 프론트엔드 통합 방안

### TERRY 기술 스택 요약
- **지도**: OpenLayers 10.8.0 + VWorld WMTS 타일
- **행정동 경계**: `seoul_adm_dong.geojson` (GeoJSON, public/에 위치)
- **지오코딩**: Kakao REST API (`/kakao/v2/local/...`)
- **부동산/상권 데이터**: 별도 API 서버 포트 8681 (`/api/sangkwon`, `/api/seoul-rtms`, `/api/search-dong`)
- **AI 채팅**: `/agent/chat` POST (현재 통합 백엔드의 `/api/v1/query` SSE와 다름)
- **핵심 파일**: `MapView.jsx` (771줄) + 4개 훅 + 10개 UI 컴포넌트

### 통합 아키텍처 (권장)

```
frontend/ (React Router v7)
├── /          → Home.jsx (모드 선택 — 지도 링크 추가)
├── /user      → UserChat.jsx (기존)
├── /dev       → DevChat.jsx (기존)
└── /map       → MapPage.jsx (신규 — TERRY MapView 이식)
```

### 신규 파일 목록 (TERRY → frontend/ 이식)
```
frontend/src/pages/MapPage.jsx                   (신규, MapView 감싸는 페이지)
frontend/src/components/map/MapView.jsx          (TERRY MapView.jsx, API 설정 환경변수화)
frontend/src/components/map/MapView.css          (원본 유지)
frontend/src/components/map/ChatPanel.jsx        (TERRY ChatPanel — 엔드포인트 수정 필요)
frontend/src/components/map/ChatPanel.css
frontend/src/components/map/controls/           (MapControls, DongTooltip)
frontend/src/components/map/panel/              (DongPanel, Layerpanel, PopulationPanel, RoadviewPanel)
frontend/src/components/map/popup/              (StorePopup, WmsPopup)
frontend/src/hooks/map/useMap.js
frontend/src/hooks/map/useDongLayer.js
frontend/src/hooks/map/useMarkers.js
frontend/src/hooks/map/useWmsClick.js
frontend/src/constants/categories.js
frontend/src/api/agentApi.js                     (기존 api.js와 통합 또는 별도 유지)
frontend/public/seoul_adm_dong.geojson           (TERRY public/에서 복사)
```

### 주요 변경/조정 사항

#### A. 채팅 엔드포인트 조정 (필수)
TERRY ChatPanel → `/agent/chat` POST (단순 JSON)
현재 frontend → `/api/v1/query` SSE 스트리밍

단기 전략: **TERRY ChatPanel의 엔드포인트를 기존 `api.js`의 `sendQuery()`로 교체**. SSE 스트리밍은 지도 채팅에서도 그대로 사용 가능. ProgressPanel/SignoffPanel을 지도 채팅에 넣을지 여부는 선택.

#### B. vite.config.js 프록시 추가 (필수)
```js
'/kakao':  { target: 'https://dapi.kakao.com', ... }
'/vworld': { target: 'https://api.vworld.kr', ... }
'/wms':    { target: 'https://api.vworld.kr', ... }
// /api 프록시는 포트 8681 vs 8000 충돌 — 경로 분리 필요 (/api/map → 8681, /api/v1 → 8000)
```

#### C. 환경변수 추가 (필수)
```
VITE_KAKAO_API_KEY       (Kakao REST API — 지오코딩)
VITE_VWORLD_API_KEY      (VWorld 타일)
VITE_MAP_API_URL         (포트 8681 부동산 서버 또는 통합 백엔드 경유 여부 결정 필요)
```

#### D. 포트 8681 서버 처리 (검토 필요)
TERRY는 상권/부동산 데이터를 별도 서버(8681)에서 가져옴. 이 서버가 무엇인지(CHOI locationAgent_DB의 api_server.py일 가능성 높음) 확인 후:
- **옵션 A**: 통합 백엔드(8000)에 해당 엔드포인트 추가 (권장 — 서버 단일화)
- **옵션 B**: 별도 서버로 유지, vite proxy에서 경로 분기

#### E. CSS 전략
Tailwind와 CSS 모듈 혼용. 지도 관련 컴포넌트는 TERRY의 CSS 파일을 그대로 유지 (OpenLayers 스타일이 섞여 있어 Tailwind 변환 시 사이드 이펙트 위험).

---

## Part 3 — 장기 로드맵 (지도-에이전트 연동)

### Phase 1: 지도 페이지 독립 통합 (1~2일)
- TERRY 컴포넌트를 `/map` 경로로 이식
- 채팅은 기존 `/api/v1/query` 엔드포인트 재사용
- Home.jsx에 지도 모드 진입 링크 추가

### Phase 2: 에이전트 응답 → 지도 링크 (추후)
에이전트 응답 텍스트에서 지역명 + 행정동 코드(ADM_CD)를 추출하여
`/map?adm_cd=1168010800` 형태의 딥링크 생성 후 ResponseCard에 렌더링.

구현 포인트:
- `location_agent.py`의 JSON 반환 구조 확장 필요 (adm_cd 포함)
- 또는 응답 마크다운에 `[지도에서 보기](/map?adm_cd=XXXXXXXX)` 링크 삽입
- `/map` 페이지가 query param을 받아 해당 행정동을 자동 포커스

### Phase 3: 지도 채팅 고도화 (그 다음)
- 지도 클릭 → 해당 행정동 컨텍스트로 에이전트 질의
- 현재 통합 프론트엔드의 ProgressPanel/SignoffPanel을 MapPage ChatPanel에도 노출
- 세션 히스토리 공유 (지도에서의 질의가 대화 히스토리에 통합)

---

## 수정 대상 파일 요약

### 백엔드 (cherry-pick)
- `integrated_PARK/agents/location_agent.py` — DB 쿼리 병렬화, Similar Locations 스코어 알고리즘 보강
- (Phase 2) `integrated_PARK/api_server.py` — /api/map/* 엔드포인트 추가 (8681 통합 시)

### 프론트엔드 (신규 이식)
- `frontend/package.json` — `ol`, `@turf/turf`, `axios` 의존성 추가
- `frontend/vite.config.js` — Kakao, VWorld, WMS 프록시 추가, /api 경로 분기
- `frontend/src/App.jsx` — `/map` 라우트 추가
- `frontend/src/pages/Home.jsx` — 지도 모드 링크 추가
- `frontend/src/pages/MapPage.jsx` — 신규
- `frontend/src/components/map/` — TERRY 컴포넌트 일괄 이식
- `frontend/src/hooks/map/` — TERRY 훅 이식
- `frontend/public/seoul_adm_dong.geojson` — TERRY에서 복사
- `frontend/.env.example` — API 키 환경변수 문서화

---

## 검증 방법

```bash
# 1. 의존성 설치
cd frontend && npm install

# 2. 개발 서버 + 백엔드 동시 실행
cd integrated_PARK && .venv/bin/python3 api_server.py &
cd frontend && npm run dev

# 3. 지도 페이지 접속
open http://localhost:5173/map

# 4. 기능 확인 체크리스트
# - VWorld 타일 정상 렌더링
# - 서울 행정동 경계 표시
# - 동 클릭 → 상권 데이터 패널 표시
# - 채팅 질의 → 에이전트 응답 (SSE 스트리밍)
# - 기존 /user, /dev 페이지 정상 동작 (회귀 없음)

# 5. 기존 채팅 회귀 테스트
curl -s -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"question": "강남구 카페 상권 분석해줘"}'
```

---

## 확정된 결정 사항

| 질문 | 결정 |
|------|------|
| 포트 8681 서버 정체 | **모름 — 구현 전 TERRY 담당자 확인 필요.** Phase 1에서는 8681 의존 기능(DongPanel 상권 데이터, RoadviewPanel 등)을 임시 비활성화하거나 fallback 처리. |
| 지도 ChatPanel | **SSE 스트리밍 통일** — TERRY ChatPanel의 fetch를 `api.js`의 `streamQuery()`로 교체. ProgressPanel/SignoffPanel도 지도 채팅에 노출. |
| 작업 순서 | **프론트엔드 먼저** — Phase 1(지도 이식) 완료 후 백엔드 cherry-pick 진행. |

## 남은 미결 사항

- 포트 8681 서버 정체: TERRY 담당자(Terry) 확인 후 통합 방향 결정.
