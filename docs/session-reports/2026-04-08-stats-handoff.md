# 세션 인수인계 — 2026-04-08 (성능 모니터링 인프라)

## 완료된 작업

### Phase E-deep (PR #229, MERGED)

**브랜치**: `PARK-perf-E-deep`

- `finance_agent.py`, `location_agent.py`에 명시적 `asyncio.TimeoutError` 핸들러 추가 (기존 generic except 흡수 문제 수정)
- `FinanceSimulationPlugin.monte_carlo_simulation_async()` 추가 — ThreadPoolExecutor 기반 10,000회 루프 비동기화
- `session_store.py` 인메모리 폴백 FIFO dict → OrderedDict LRU 교체

### 성능 통계 API + 분석 스크립트 (PR #244, OPEN)

**브랜치**: `PARK-perf-stats`

수정 파일:
- `integrated_PARK/api_server.py` — `GET /api/v1/stats?hours=N` 라우트 추가
  - 에이전트별 latency (p50/p90/max), 등급/상태 분포, 에러율 집계
  - `load_entries_json()` 재사용, 기존 60초 TTL 캐시 활용
  - `verify_api_key` 인증, 기본 rate limit 60/min

- `integrated_PARK/scripts/analyze_logs.py` — 터미널 기반 심층 분석
  - `--remote`: `/api/v1/logs` API에서 직접 조회
  - `--since / --until`: 기간 필터
  - `--compare YYYY-MM-DD`: before/after 비교 리포트
  - 시간대별 추이, 느린 요청 TOP 5

### 성능 베이스라인 리포트

- `docs/test-reports/2026-04-08-perf-baseline.md` — 최적화 Phase 전체 before/after 데이터 기록

---

## 전체 성능 최적화 Phase 현황

| Phase | PR | 상태 | 내용 |
|-------|-----|------|------|
| E-backend | #216 | ✅ MERGED | GZip·DB캐시·응답시간 헤더 |
| A-bundle | #224 | ✅ MERGED | React.lazy·manualChunks |
| B-network | #227 | ✅ MERGED | fetch 타임아웃·에러 파싱 |
| CD-api-ux | #228 | ✅ MERGED | 중복 제거·UX 개선 |
| E-deep | #229 | ✅ MERGED | TimeoutError 핸들러·Monte Carlo async·LRU |
| **stats** | **#244** | **🔄 OPEN** | stats API + analyze_logs.py |

### 전체 최적화 효과 (analyze_logs.py --compare 2026-04-03 결과)

| 지표 | Before (n=532) | After (n=416) | 변화 |
|------|-------|------|------|
| 전체 avg | 32.7s | 11.9s | **-63.6%** |
| 전체 p90 | 68.2s | 21.2s | **-68.9%** |
| 전체 max | 612.0s | 64.2s | **-89.5%** |
| location avg | 46.5s | 11.2s | **-75.9%** |

---

## 다음 세션 — 프론트엔드 모니터 페이지 (`/dev/stats`)

### 개요

stats API가 머지·배포되면, 개발자 모드에서 성능 현황을 시각화하는 페이지를 추가한다.

### 진입 경로

`/dev/stats` — 기존 `RequireDevAuth` 보호 (LogViewer와 동급).

라우트: `App.jsx`에 `<Route path="/dev/stats" element={<RequireDevAuth><StatsPage /></RequireDevAuth>} />`

### 데이터 소스

`GET /api/v1/stats?hours=N` → 응답 JSON 그대로 사용.
`api.js`에 `fetchStats(hours)` 추가 (`fetchLogs` 패턴).

### 화면 구성

```
┌─────────────────────────────────────────┐
│  기간 선택: [6h] [24h] [48h] [7d]       │
├─────────────────────────────────────────┤
│  요약 카드 4장                           │
│  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐   │
│  │총 요청│ │avg   │ │p90   │ │에러율│   │
│  │ 100  │ │11.0s │ │19.0s │ │ 2.0% │   │
│  └──────┘ └──────┘ └──────┘ └──────┘   │
├─────────────────────────────────────────┤
│  에이전트별 latency 막대 차트 (Chart.js) │
│  ▓▓▓▓▓▓▓▓ admin   17.7s                │
│  ▓▓▓ chat          6.6s                │
│  ▓▓▓▓▓▓▓▓▓▓▓ finance 29.0s             │
│  ▓▓▓▓ location      8.8s               │
├─────────────────────────────────────────┤
│  등급 분포 (도넛) │ 상태 분포 (도넛)     │
└─────────────────────────────────────────┘
```

### 재사용 가능 자산

| 자산 | 경로 | 활용 |
|------|------|------|
| Chart.js 4.5.1 | package.json | 막대·도넛 차트 |
| AgentUsageChart.jsx | components/report/ | 막대 차트 패턴 참조 |
| SimulationChart.jsx | components/ | 히스토그램 패턴 참조 |
| devAuth.js | utils/ | RequireDevAuth 인증 |
| fetchLogs 패턴 | api.js | fetchStats 함수 추가 |

### 예상 파일

| 파일 | 작업 |
|------|------|
| `frontend/src/pages/StatsPage.jsx` | 신규 (~120줄) |
| `frontend/src/api.js` | `fetchStats()` 추가 (~5줄) |
| `frontend/src/App.jsx` | 라우트 1줄 추가 |

### 브랜치

```bash
git fetch origin
git checkout -b PARK-dev-stats origin/main
```

---

## 주의사항

- PR #244 머지 전에는 `/api/v1/stats`가 404 — 배포 후 `curl` 확인 필요
- `analyze_logs.py`는 `logs/remote/` 디렉토리를 기본 참조 — `pull_logs.py`로 미리 동기화하거나 `--remote` 플래그 사용
- LogViewer (`/dev/logs`)에 "성능" 탭 추가도 가능하나, 별도 페이지가 화면 공간·UX 측면에서 나음
